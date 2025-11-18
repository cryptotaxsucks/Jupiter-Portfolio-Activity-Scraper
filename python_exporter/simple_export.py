#!/usr/bin/env python3
"""
Simple Jupiter Portfolio Exporter
Just paste your auth tokens and get a CSV - no browser automation needed!
"""

import sys
from api_client import JupiterAPIClient
from csv_exporter import CSVExporter

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
    print("Step 2: Get your authentication tokens from Jupiter")
    print()
    print("How to find these:")
    print("1. Open https://jup.ag/portfolio/" + wallet_address)
    print("2. Press F12 to open Developer Tools")
    print("3. Click the 'Network' tab")
    print("4. Click 'Load more' on the Jupiter page")
    print("5. Look for a request to 'portfolio-api-jup.sonar.watch'")
    print("6. Click it, then click 'Headers' tab")
    print("7. Scroll to 'Request Headers' and copy the values below")
    print()
    
    # Get authorization token
    print("Step 3: Paste the 'authorization' token")
    print("(It should start with 'Bearer ...')")
    print("Tip: Right-click in PowerShell to paste")
    auth_token = input("authorization: ").strip()
    
    if not auth_token:
        print("Error: Authorization token is required")
        sys.exit(1)
    
    # Auto-prepend "Bearer " if missing
    if not auth_token.startswith("Bearer "):
        auth_token = "Bearer " + auth_token
    
    print()
    
    # Get turnstile token
    print("Step 4: Paste the 'x-turnstile-token'")
    print("(A long random string)")
    print("Tip: Right-click in PowerShell to paste")
    turnstile_token = input("x-turnstile-token: ").strip()
    
    if not turnstile_token:
        print("Error: Turnstile token is required")
        sys.exit(1)
    
    print()
    print("="*80)
    print("Starting Export...")
    print("="*80)
    print()
    
    # Build headers
    headers = {
        "authorization": auth_token,
        "x-turnstile-token": turnstile_token,
        "accept": "application/json"
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
