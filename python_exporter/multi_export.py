#!/usr/bin/env python3
"""
Multi-Wallet Jupiter Portfolio Exporter
Export transactions from multiple wallets simultaneously with parallel processing.
"""

import sys
import json
import argparse
import threading
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from api_client import JupiterAPIClient
from csv_exporter import CSVExporter

class WalletExportStatus:
    """Track export status for a single wallet."""
    def __init__(self, wallet_address):
        self.wallet_address = wallet_address
        self.short_address = f"{wallet_address[:4]}...{wallet_address[-4:]}"
        self.status = "pending"
        self.transactions = 0
        self.pages = 0
        self.error = None
        self.start_time = None
        self.end_time = None
        
    def elapsed_time(self):
        if not self.start_time:
            return 0
        end = self.end_time or time.time()
        return end - self.start_time

class MultiWalletExporter:
    """Handle parallel export of multiple wallets."""
    
    def __init__(self, headers, parallel=2, start_date=None, end_date=None, resume=False):
        self.headers = headers
        self.parallel = parallel
        self.start_date = start_date
        self.end_date = end_date
        self.resume = resume
        self.statuses = {}
        self.lock = threading.Lock()
        self.interrupted = False
        self.stop_event = threading.Event()
        
    def parse_headers_block(self, headers_text):
        """Parse the entire request headers block from DevTools into a dict."""
        headers = {}
        lines = [line.strip() for line in headers_text.strip().split('\n') if line.strip()]
        for i in range(0, len(lines) - 1, 2):
            header_name = lines[i].lower()
            header_value = lines[i + 1]
            headers[header_name] = header_value
        return headers
    
    def save_progress(self, wallet_address, last_signature):
        """Save resume progress to a file."""
        progress_file = f".resume-{wallet_address}.json"
        with open(progress_file, 'w') as f:
            json.dump({"last_signature": last_signature, "timestamp": datetime.now().isoformat()}, f)
    
    def load_progress(self, wallet_address):
        """Load resume progress from file if it exists."""
        progress_file = f".resume-{wallet_address}.json"
        if Path(progress_file).exists():
            with open(progress_file, 'r') as f:
                return json.load(f)
        return None
    
    def clear_progress(self, wallet_address):
        """Clear resume progress file."""
        progress_file = f".resume-{wallet_address}.json"
        if Path(progress_file).exists():
            Path(progress_file).unlink()
    
    def print_status(self):
        """Print current status of all wallets."""
        with self.lock:
            print("\n" + "=" * 80)
            print("WALLET EXPORT STATUS")
            print("=" * 80)
            for wallet, status in self.statuses.items():
                elapsed = f"{status.elapsed_time():.0f}s" if status.start_time else "-"
                if status.status == "completed":
                    print(f"  ✓ {status.short_address}: {status.transactions:,} txns in {elapsed}")
                elif status.status == "running":
                    print(f"  ⏳ {status.short_address}: {status.transactions:,} txns, page {status.pages} ({elapsed})")
                elif status.status == "error":
                    print(f"  ✗ {status.short_address}: {status.error}")
                elif status.status == "interrupted":
                    print(f"  ⚠ {status.short_address}: {status.transactions:,} txns (interrupted)")
                else:
                    print(f"  ⋯ {status.short_address}: waiting")
            print("=" * 80)
    
    def export_wallet(self, wallet_address):
        """Export a single wallet - runs in a thread."""
        status = self.statuses[wallet_address]
        status.status = "running"
        status.start_time = time.time()
        
        output_filename = f"all-activities-{wallet_address}.csv"
        backup_filename = f"all-activities-{wallet_address}.backup.csv"
        
        resume_from = None
        if self.resume:
            progress = self.load_progress(wallet_address)
            if progress:
                resume_from = progress.get('last_signature')
        
        def auto_save_callback(transactions, token_symbols, last_sig):
            try:
                exporter = CSVExporter(token_symbols)
                exporter.export_to_csv(transactions, backup_filename)
                self.save_progress(wallet_address, last_sig)
                with self.lock:
                    status.transactions = len(transactions)
                    status.pages += 1
            except Exception:
                pass
        
        client = JupiterAPIClient(self.headers)
        transactions = []
        token_symbols = {}
        wallet_interrupted = False
        
        try:
            if self.stop_event.is_set():
                status.status = "interrupted"
                return
                
            transactions, token_symbols = client.fetch_all_transactions(
                wallet_address,
                limit=100,
                start_date=self.start_date,
                end_date=self.end_date,
                resume_from=resume_from,
                auto_save_callback=auto_save_callback,
                stop_event=self.stop_event
            )
        except KeyboardInterrupt:
            wallet_interrupted = True
            if hasattr(client, '_interrupted_data'):
                transactions, token_symbols = client._interrupted_data
        except Exception as e:
            status.status = "error"
            status.error = str(e)[:50]
            status.end_time = time.time()
            return
        
        if self.interrupted or wallet_interrupted:
            status.status = "interrupted"
        
        if transactions:
            try:
                exporter = CSVExporter(token_symbols)
                if status.status == "interrupted":
                    final_file = f"all-activities-{wallet_address}.partial.csv"
                else:
                    final_file = output_filename
                    self.clear_progress(wallet_address)
                    if Path(backup_filename).exists():
                        Path(backup_filename).unlink()
                
                exporter.export_to_csv(transactions, final_file)
                status.transactions = len(transactions)
            except Exception as e:
                status.error = str(e)[:50]
        
        if status.status != "interrupted" and status.status != "error":
            status.status = "completed"
        status.end_time = time.time()
    
    def run(self, wallets):
        """Run parallel export for all wallets."""
        import signal
        
        for wallet in wallets:
            self.statuses[wallet] = WalletExportStatus(wallet)
        
        print(f"\nStarting export of {len(wallets)} wallet(s) with {self.parallel} parallel workers...")
        self.print_status()
        
        executor = ThreadPoolExecutor(max_workers=self.parallel)
        futures = {}
        
        def signal_handler(signum, frame):
            print("\n\n⚠ INTERRUPT RECEIVED - Stopping all exports...")
            self.interrupted = True
            self.stop_event.set()
            for wallet, status in self.statuses.items():
                if status.status == "pending":
                    status.status = "interrupted"
        
        original_handler = signal.signal(signal.SIGINT, signal_handler)
        
        try:
            futures = {executor.submit(self.export_wallet, wallet): wallet for wallet in wallets}
            
            for future in as_completed(futures):
                if self.interrupted:
                    break
                wallet = futures[future]
                try:
                    future.result()
                except Exception as e:
                    self.statuses[wallet].status = "error"
                    self.statuses[wallet].error = str(e)[:50]
                
                self.print_status()
        
        finally:
            signal.signal(signal.SIGINT, original_handler)
            if self.interrupted:
                print("  Waiting for active exports to save progress...")
                executor.shutdown(wait=True, cancel_futures=True)
                time.sleep(1)
            else:
                executor.shutdown(wait=True)
            self.print_status()
        
        return self.statuses


def load_wallets_from_file(filepath):
    """Load wallet addresses from a text file (one per line)."""
    wallets = []
    with open(filepath, 'r') as f:
        for line in f:
            wallet = line.strip()
            if wallet and not wallet.startswith('#'):
                wallets.append(wallet)
    return wallets


def main():
    parser = argparse.ArgumentParser(
        description='Export Jupiter Portfolio transactions for multiple wallets',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python multi_export.py WALLET1 WALLET2 WALLET3
  python multi_export.py --wallets wallets.txt --parallel 3
  python multi_export.py WALLET1 WALLET2 --start-date 2024-01-01 --resume
        """
    )
    parser.add_argument('wallets', nargs='*', help='Wallet addresses to export')
    parser.add_argument('--wallets-file', '-f', help='File containing wallet addresses (one per line)')
    parser.add_argument('--parallel', '-p', type=int, default=2, help='Number of parallel exports (default: 2)')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--resume', action='store_true', help='Resume from last saved progress')
    args = parser.parse_args()
    
    wallets = list(args.wallets) if args.wallets else []
    
    if args.wallets_file:
        try:
            file_wallets = load_wallets_from_file(args.wallets_file)
            wallets.extend(file_wallets)
        except Exception as e:
            print(f"Error reading wallets file: {e}")
            sys.exit(1)
    
    if not wallets:
        print("Error: No wallet addresses provided")
        print("Usage: python multi_export.py WALLET1 WALLET2 ...")
        print("   or: python multi_export.py --wallets-file wallets.txt")
        sys.exit(1)
    
    wallets = list(dict.fromkeys(wallets))
    
    print("=" * 80)
    print("Jupiter Portfolio Multi-Wallet CSV Exporter")
    print("=" * 80)
    print()
    print(f"Wallets to export: {len(wallets)}")
    for i, w in enumerate(wallets, 1):
        print(f"  {i}. {w[:8]}...{w[-8:]}")
    print(f"\nParallel workers: {args.parallel}")
    if args.start_date:
        print(f"Start date filter: {args.start_date}")
    if args.end_date:
        print(f"End date filter: {args.end_date}")
    if args.resume:
        print("Resume mode: enabled")
    print()
    
    print("Step: Copy Request Headers from Jupiter")
    print()
    print("How to find these:")
    print("1. Open https://jup.ag/portfolio/<any-wallet>")
    print("2. Press F12 to open Developer Tools")
    print("3. Click the 'Network' tab")
    print("4. Click 'Activity' tab, then click 'Load more' on the Jupiter page")
    print("5. Look for a request to 'portfolio-api-jup.sonar.watch'")
    print("6. Click it, then click 'Headers' tab")
    print("7. Scroll to 'Request Headers' section")
    print("8. Select ALL the request headers text and copy it")
    print()
    print("Paste ALL the request headers below")
    print("(Right-click to paste, then press Enter, then Ctrl+Z + Enter when done)")
    print()
    print("Paste headers here:")
    
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
    
    exporter_instance = MultiWalletExporter(
        headers={},
        parallel=args.parallel,
        start_date=args.start_date,
        end_date=args.end_date,
        resume=args.resume
    )
    parsed_headers = exporter_instance.parse_headers_block(headers_text)
    headers = {k: v for k, v in parsed_headers.items() if not k.startswith(':')}
    
    auth_token = headers.get('authorization', '')
    turnstile_token = headers.get('x-turnstile-token', '')
    user_agent = headers.get('user-agent', '')
    
    if not auth_token:
        print("\nError: Could not find 'authorization' header")
        sys.exit(1)
    if not turnstile_token:
        print("\nError: Could not find 'x-turnstile-token' header")
        sys.exit(1)
    if not user_agent:
        print("\nError: Could not find 'user-agent' header")
        sys.exit(1)
    
    print()
    print("=" * 80)
    print("✓ Headers parsed successfully!")
    print(f"  Total headers captured: {len(headers)}")
    print(f"  Authorization: {auth_token[:30]}...")
    print(f"  Turnstile: {turnstile_token[:30]}...")
    print("=" * 80)
    
    exporter_instance.headers = headers
    
    statuses = exporter_instance.run(wallets)
    
    print()
    print("=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    
    completed = sum(1 for s in statuses.values() if s.status == "completed")
    interrupted = sum(1 for s in statuses.values() if s.status == "interrupted")
    errors = sum(1 for s in statuses.values() if s.status == "error")
    total_txns = sum(s.transactions for s in statuses.values())
    
    print(f"\nCompleted: {completed}/{len(wallets)}")
    if interrupted:
        print(f"Interrupted: {interrupted}")
    if errors:
        print(f"Errors: {errors}")
    print(f"Total transactions exported: {total_txns:,}")
    
    print("\nOutput files:")
    for wallet, status in statuses.items():
        if status.status == "completed":
            print(f"  ✓ all-activities-{wallet}.csv")
        elif status.status == "interrupted":
            print(f"  ⚠ all-activities-{wallet}.partial.csv (incomplete)")
        elif status.status == "error":
            print(f"  ✗ {status.short_address}: {status.error}")
    
    if interrupted:
        print("\nTo resume interrupted exports, run with --resume flag")
    print()


if __name__ == "__main__":
    main()
