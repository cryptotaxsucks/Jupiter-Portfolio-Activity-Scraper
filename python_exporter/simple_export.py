#!/usr/bin/env python3
"""
Simple Jupiter Portfolio Exporter
Just paste your auth tokens and get a CSV - no browser automation needed!
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from api_client import JupiterAPIClient
from csv_exporter import CSVExporter

def parse_headers_block(headers_text):
    """Parse the entire request headers block from DevTools into a dict.
    
    Chrome DevTools formats headers as alternating lines:
    Line 1: header name
    Line 2: header value
    Line 3: next header name
    Line 4: next header value
    etc.
    """
    headers = {}
    
    # Split into lines and remove empty ones
    lines = [line.strip() for line in headers_text.strip().split('\n') if line.strip()]
    
    # Process pairs of lines: name, value, name, value, ...
    for i in range(0, len(lines) - 1, 2):
        header_name = lines[i].lower()
        header_value = lines[i + 1]
        headers[header_name] = header_value
    
    return headers

def save_progress(wallet_address, last_signature):
    """Save resume progress to a file."""
    progress_file = f".resume-{wallet_address}.json"
    with open(progress_file, 'w') as f:
        json.dump({"last_signature": last_signature, "timestamp": datetime.now().isoformat()}, f)

def load_progress(wallet_address):
    """Load resume progress from file if it exists."""
    progress_file = f".resume-{wallet_address}.json"
    if Path(progress_file).exists():
        with open(progress_file, 'r') as f:
            return json.load(f)
    return None

def clear_progress(wallet_address):
    """Clear resume progress file."""
    progress_file = f".resume-{wallet_address}.json"
    if Path(progress_file).exists():
        Path(progress_file).unlink()

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Export Jupiter Portfolio transactions to CSV')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD) - only export transactions after this date')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD) - only export transactions before this date')
    parser.add_argument('--resume', action='store_true', help='Resume from last saved progress')
    args = parser.parse_args()
    
    print("="*80)
    print("Jupiter Portfolio CSV Exporter (Simple Mode)")
    print("="*80)
    print()
    
    # Get wallet address
    print("Step 1: Enter your Solana wallet address")
    wallet_address = input("Wallet address: ").strip()
    
    if not wallet_address:
        print("Error: Wallet address is required")
        sys.exit(1)
    
    # Check for resume
    resume_from = None
    if args.resume:
        progress = load_progress(wallet_address)
        if progress:
            resume_from = progress.get('last_signature')
            print(f"\n✓ Found saved progress from {progress.get('timestamp')}")
            print(f"  Resuming from signature: {resume_from[:20]}...")
        else:
            print("\n⚠ No saved progress found, starting from beginning")
    
    print()
    print("Step 2: Copy Request Headers from Jupiter")
    print()
    print("How to find these:")
    print("1. Open https://jup.ag/portfolio/" + wallet_address)
    print("2. Press F12 to open Developer Tools")
    print("3. Click the 'Network' tab")
    print("4. Click 'Activity' tab, then click 'Load more' on the Jupiter page")
    print("5. Look for a request to 'portfolio-api-jup.sonar.watch'")
    print("6. Click it, then click 'Headers' tab")
    print("7. Scroll to 'Request Headers' section")
    print("8. Select ALL the request headers text and copy it")
    print()
    print("Step 3: Paste ALL the request headers below")
    print("(Right-click to paste, then press Enter, then Ctrl+Z + Enter when done)")
    print()
    print("Paste headers here:")
    
    # Read multiple lines until EOF (Ctrl+D on Unix, Ctrl+Z on Windows)
    headers_lines = []
    try:
        while True:
            line = input()
            headers_lines.append(line)
    except EOFError:
        pass
    
    headers_text = '\n'.join(headers_lines)
    
    if not headers_text.strip():
        print("\nError: No headers provided")
        sys.exit(1)
    
    # Parse the headers
    parsed_headers = parse_headers_block(headers_text)
    
    # Filter out pseudo-headers (those starting with :) - they're not real HTTP headers
    # and the requests library handles them automatically
    headers = {k: v for k, v in parsed_headers.items() if not k.startswith(':')}
    
    # Verify we have the critical headers
    auth_token = headers.get('authorization', '')
    turnstile_token = headers.get('x-turnstile-token', '')
    user_agent = headers.get('user-agent', '')
    
    if not auth_token:
        print("\nError: Could not find 'authorization' header in the pasted text")
        sys.exit(1)
    
    if not turnstile_token:
        print("\nError: Could not find 'x-turnstile-token' header in the pasted text")
        sys.exit(1)
    
    if not user_agent:
        print("\nError: Could not find 'user-agent' header in the pasted text")
        sys.exit(1)
    
    print()
    print("="*80)
    print("✓ Headers parsed successfully!")
    print(f"  Total headers captured: {len(headers)}")
    print(f"  Authorization: {auth_token[:30]}...")
    print(f"  Turnstile: {turnstile_token[:30]}...")
    print(f"  User-Agent: {user_agent[:50]}...")
    print("="*80)
    print()
    
    # Display date filter if provided
    if args.start_date or args.end_date:
        print("Date Filter:")
        if args.start_date:
            print(f"  Start: {args.start_date}")
        if args.end_date:
            print(f"  End: {args.end_date}")
        print()
    
    print("Starting Export...")
    print("="*80)
    print()
    
    # Setup auto-save callback
    output_filename = f"all-activities-{wallet_address}.csv"
    backup_filename = f"all-activities-{wallet_address}.backup.csv"
    
    def auto_save_callback(transactions, token_symbols, last_sig):
        """Auto-save callback called every 10 pages."""
        try:
            exporter = CSVExporter(token_symbols)
            exporter.export_to_csv(transactions, backup_filename)
            save_progress(wallet_address, last_sig)
            print(f"  💾 Auto-saved {len(transactions)} transactions to {backup_filename}")
        except Exception as e:
            print(f"  ⚠ Auto-save failed: {e}")
    
    # Fetch transactions with graceful interrupt handling
    transactions = []
    token_symbols = {}
    interrupted = False
    
    client = JupiterAPIClient(headers)
    try:
        transactions, token_symbols = client.fetch_all_transactions(
            wallet_address, 
            limit=100,
            start_date=args.start_date,
            end_date=args.end_date,
            resume_from=resume_from,
            auto_save_callback=auto_save_callback
        )
    except KeyboardInterrupt:
        print("  Saving progress...")
        interrupted = True
        # Retrieve partial data from the client
        if hasattr(client, '_interrupted_data'):
            transactions, token_symbols = client._interrupted_data
        else:
            transactions, token_symbols = [], {}
    except Exception as e:
        print(f"\n✗ Error: {e}")
        # Try to save what we have
        if transactions:
            print("  Attempting to save partial data...")
        else:
            sys.exit(1)
    
    # Export to CSV (final or partial)
    if not transactions:
        print("\n✗ No transactions to export")
        sys.exit(1)
    
    try:
        exporter = CSVExporter(token_symbols)
        final_file = output_filename if not interrupted else f"all-activities-{wallet_address}.partial.csv"
        exporter.export_to_csv(transactions, final_file)
        
        # Clean up backup and progress files if complete
        if not interrupted:
            clear_progress(wallet_address)
            if Path(backup_filename).exists():
                Path(backup_filename).unlink()
    except Exception as e:
        print(f"\n✗ Error exporting: {e}")
        sys.exit(1)
    
    print()
    print("="*80)
    if interrupted:
        print("⚠ EXPORT INTERRUPTED - PARTIAL DATA SAVED")
        print("="*80)
        print(f"\nPartial CSV file: {final_file}")
        print(f"Transactions saved: {len(transactions):,}")
        print(f"\nTo resume later, run: python simple_export.py --resume")
    else:
        print("✓ EXPORT COMPLETE")
        print("="*80)
        print(f"\nYour CSV file: {final_file}")
        print(f"Total transactions: {len(transactions):,}")
    print()

if __name__ == "__main__":
    main()
