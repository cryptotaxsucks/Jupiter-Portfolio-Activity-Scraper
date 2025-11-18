#!/usr/bin/env python3
"""
Simple Jupiter Portfolio Exporter
Just paste your auth tokens and get a CSV - no browser automation needed!
"""

import sys
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

def main():
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
    print("(Right-click to paste, then press Enter, then Ctrl+D when done)")
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
    
    # Extract required headers
    auth_token = parsed_headers.get('authorization', '')
    turnstile_token = parsed_headers.get('x-turnstile-token', '')
    origin = parsed_headers.get('origin', 'https://jup.ag')
    referer = parsed_headers.get('referer', 'https://jup.ag/')
    user_agent = parsed_headers.get('user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    if not auth_token:
        print("\nError: Could not find 'authorization' header in the pasted text")
        sys.exit(1)
    
    if not turnstile_token:
        print("\nError: Could not find 'x-turnstile-token' header in the pasted text")
        sys.exit(1)
    
    print()
    print("="*80)
    print("✓ Headers parsed successfully!")
    print(f"  Authorization: {auth_token[:30]}...")
    print(f"  Turnstile: {turnstile_token[:30]}...")
    print(f"  Origin: {origin}")
    print(f"  Referer: {referer}")
    print("="*80)
    print()
    print("Starting Export...")
    print("="*80)
    print()
    
    # Build headers with all required fields
    headers = {
        "authorization": auth_token,
        "x-turnstile-token": turnstile_token,
        "accept": "application/json",
        "origin": origin,
        "referer": referer,
        "user-agent": user_agent
    }
    
    # Fetch transactions
    try:
        client = JupiterAPIClient(headers)
        transactions, token_symbols = client.fetch_all_transactions(wallet_address, limit=100)
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    
    # Export to CSV
    output_filename = f"all-activities-{wallet_address}.csv"
    
    try:
        exporter = CSVExporter(token_symbols)
        exporter.export_to_csv(transactions, output_filename)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    
    print()
    print("="*80)
    print("✓ EXPORT COMPLETE")
    print("="*80)
    print(f"\nYour CSV file: {output_filename}")
    print(f"Total transactions: {len(transactions):,}")
    print()

if __name__ == "__main__":
    main()
