#!/usr/bin/env python3
import argparse
import sys
import os
from header_capture import HeaderCapture
from api_client import JupiterAPIClient
from csv_exporter import CSVExporter

def main():
    parser = argparse.ArgumentParser(
        description="Export Jupiter Portfolio transactions to CSV"
    )
    parser.add_argument(
        "wallet_address",
        help="Solana wallet address to export"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Page size (max 100, default: 100)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )
    parser.add_argument(
        "--reuse-headers",
        action="store_true",
        help="Reuse previously captured headers instead of recapturing"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output CSV filename (default: all-activities-{address}.csv)"
    )
    
    args = parser.parse_args()
    
    headers_file = "captured_headers.json"
    headers = None
    
    if args.reuse_headers:
        print("Attempting to reuse previously captured headers...")
        headers = HeaderCapture.load_headers(headers_file)
        
        if not headers:
            print("⚠ No saved headers found. Will capture new ones.")
    
    if not headers:
        print("\n" + "="*80)
        print("STEP 1: Capturing Authentication Headers")
        print("="*80)
        
        capturer = HeaderCapture()
        try:
            headers = capturer.capture(args.wallet_address, headless=args.headless)
            capturer.save_headers(headers_file)
        except KeyboardInterrupt:
            print("\n\n⚠ Interrupted by user")
            capturer.close()
            sys.exit(1)
        except Exception as e:
            print(f"\n✗ Error: {e}")
            capturer.close()
            sys.exit(1)
        finally:
            capturer.close()
    
    print("\n" + "="*80)
    print("STEP 2: Fetching Transactions from API")
    print("="*80)
    
    try:
        client = JupiterAPIClient(headers)
        transactions, token_symbols = client.fetch_all_transactions(
            args.wallet_address, 
            limit=min(args.limit, 100)
        )
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("STEP 3: Exporting to CSV")
    print("="*80)
    
    output_filename = args.output or f"all-activities-{args.wallet_address}.csv"
    
    try:
        exporter = CSVExporter(token_symbols)
        exporter.export_to_csv(transactions, output_filename)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("✓ EXPORT COMPLETE")
    print("="*80)
    print(f"\nYour CSV file is ready: {output_filename}")

if __name__ == "__main__":
    main()
