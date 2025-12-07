from curl_cffi import requests
from curl_cffi.requests import RequestsError
import time
from typing import Optional, Dict, List

class JupiterAPIClient:
    API_BASE = "https://portfolio-api-jup.sonar.watch/v1/transactions/fetch"
    
    def __init__(self, headers: Dict[str, str]):
        self.headers = headers
        self.session = requests.Session()
        self.session.headers.update(headers)
        
    def fetch_page(self, address: str, limit: int = 100, before: Optional[str] = None, 
                    retry_attempt: int = 0, timeout: int = 30) -> Dict:
        """Fetch a page of transactions with adaptive timeout and retry logic.
        
        Args:
            timeout: Initial timeout in seconds (will increase on retries)
            retry_attempt: Current retry attempt number
        """
        params = {
            "address": address,
            "limit": min(limit, 100)
        }
        
        if before:
            params["before"] = before
        
        # Progressive timeout: 30s -> 45s -> 60s -> 90s -> 120s
        current_timeout = min(timeout + (retry_attempt * 15), 120)
        
        try:
            response = self.session.get(
                self.API_BASE,
                params=params,
                timeout=current_timeout,
                impersonate="chrome"
            )
            
            if response.status_code == 401 or response.status_code == 403:
                raise Exception("Authentication failed. Headers may have expired. Please recapture them.")
            
            if response.status_code == 429 or response.status_code >= 500:
                if retry_attempt < 6:
                    wait_time = min(0.25 * (2 ** retry_attempt), 5.0)
                    print(f"  Server error {response.status_code}, retrying in {wait_time:.1f}s... (attempt {retry_attempt + 1}/6)")
                    time.sleep(wait_time)
                    return self.fetch_page(address, limit, before, retry_attempt + 1, timeout)
                else:
                    raise Exception(f"Server error {response.status_code} after {retry_attempt} retries")
            
            response.raise_for_status()
            return response.json()
            
        except RequestsError as e:
            # Handle timeout errors specifically
            error_msg = str(e)
            if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
                if retry_attempt < 6:
                    new_timeout = current_timeout + 15
                    print(f"  Timeout after {current_timeout}s, retrying with {new_timeout}s timeout... (attempt {retry_attempt + 1}/6)")
                    time.sleep(1)
                    return self.fetch_page(address, limit, before, retry_attempt + 1, timeout)
                else:
                    raise Exception(f"Timeout after {retry_attempt} retries (max timeout: {current_timeout}s)")
            else:
                # Re-raise other connection errors
                raise
    
    def fetch_all_transactions(self, address: str, limit: int = 100, 
                                start_date: str = None, end_date: str = None,
                                resume_from: str = None, auto_save_callback=None,
                                progress_callback=None, stop_event=None):
        """Fetch all transactions with optional date filtering and auto-save.
        
        Args:
            address: Wallet address
            limit: Transactions per page (max 100)
            start_date: Start date in YYYY-MM-DD format (inclusive, transactions after this date)
            end_date: End date in YYYY-MM-DD format (inclusive, transactions before this date)
            resume_from: Transaction signature to resume from
            auto_save_callback: Callback function(transactions, token_symbols, last_sig) called every page
            progress_callback: Progress callback function
            stop_event: threading.Event to signal early stop (for multi-wallet mode)
        """
        from datetime import datetime as dt
        
        all_transactions = []
        seen_signatures = set()
        token_symbols = {}
        before = resume_from
        page = 0
        last_fetch_time = 0
        consecutive_dupe_pages = 0  # Track consecutive pages with all duplicates
        
        # Parse date filters if provided
        start_timestamp = None
        end_timestamp = None
        if start_date:
            start_timestamp = int(dt.strptime(start_date, "%Y-%m-%d").timestamp())
        if end_date:
            # Add one day to make it inclusive of the end date
            end_timestamp = int(dt.strptime(end_date, "%Y-%m-%d").timestamp()) + 86400
        
        print(f"\nFetching transactions for {address}...")
        print(f"Using page size: {limit}")
        if resume_from:
            print(f"Resuming from: {resume_from[:20]}...")
        print("-" * 80)
        
        try:
            while True:
                page += 1
                
                if stop_event and stop_event.is_set():
                    print(f"\n⚠ Stop signal received at page {page}")
                    self._interrupted_data = (all_transactions, token_symbols)
                    raise KeyboardInterrupt("Stop signal received")
                
                start_time = time.time()
                
                # Adaptive timeout: use 1.5x the previous page's fetch time, clamped to 30-120s
                adaptive_timeout = 30
                if last_fetch_time > 0:
                    adaptive_timeout = max(30, min(120, int(last_fetch_time * 1.5)))
                
                try:
                    data = self.fetch_page(address, limit, before, timeout=adaptive_timeout)
                except Exception as e:
                    print(f"\n✗ Error on page {page}: {e}")
                    raise
                
                fetch_time = (time.time() - start_time) * 1000
                last_fetch_time = fetch_time / 1000  # Convert to seconds for next iteration
                
                transactions = data.get("transactions", [])
                if not transactions:
                    print(f"\n✓ No more transactions. Stopping at page {page}")
                    break
                
                token_info = data.get("tokenInfo", {})
                for mint, info in token_info.items():
                    symbol = info.get("symbol")
                    if not symbol and isinstance(info, dict):
                        for value in info.values():
                            if isinstance(value, dict) and value.get("symbol"):
                                symbol = value["symbol"]
                                break
                    if symbol:
                        token_symbols[mint] = symbol
                
                before_count = len(all_transactions)
                duplicates = 0
                filtered_by_date = 0
                reached_date_limit = False
                
                # Check date filtering on first transaction of the page
                # Since transactions are newest-first, we can stop early
                if end_timestamp and transactions:
                    first_tx_time = transactions[0].get("blockTime", 0)
                    if first_tx_time > end_timestamp:
                        # All transactions on this page are too new, skip the page
                        before = transactions[-1].get("signature")
                        print(f"Page {page:3d}: Skipping (transactions too recent for date filter)")
                        continue
                
                for tx in transactions:
                    sig = tx.get("signature")
                    owner = tx.get("owner")
                    key = f"{sig}|{owner}"
                    tx_time = tx.get("blockTime", 0)
                    
                    # Apply date filters
                    if start_timestamp and tx_time < start_timestamp:
                        # Transactions are ordered newest-first, so we can stop here
                        print(f"\n✓ Reached start date limit. Stopping.")
                        reached_date_limit = True
                        break
                    
                    if end_timestamp and tx_time > end_timestamp:
                        filtered_by_date += 1
                        continue
                    
                    if key not in seen_signatures:
                        seen_signatures.add(key)
                        all_transactions.append(tx)
                    else:
                        duplicates += 1
                
                new_count = len(all_transactions) - before_count
                
                print(f"Page {page:3d}: {len(transactions):3d} returned, {new_count:3d} new, "
                      f"{duplicates:3d} dupes, total={len(all_transactions):5d}, "
                      f"fetch={fetch_time:6.0f}ms", end="")
                if filtered_by_date > 0:
                    print(f", {filtered_by_date} filtered by date", end="")
                print()
                
                # Track consecutive pages with all duplicates to detect infinite loop
                if new_count == 0:
                    consecutive_dupe_pages += 1
                    if consecutive_dupe_pages >= 3:
                        print(f"\n✓ {consecutive_dupe_pages} consecutive pages with no new transactions. Export complete.")
                        break
                else:
                    consecutive_dupe_pages = 0  # Reset counter when we get new transactions
                
                # Auto-save after every page
                if auto_save_callback:
                    last_sig = transactions[-1].get("signature") if transactions else None
                    if last_sig:
                        auto_save_callback(all_transactions, dict(token_symbols), last_sig)
                
                before = transactions[-1].get("signature")
                
                if reached_date_limit:  # Date filter triggered early exit
                    break
                
                if progress_callback:
                    progress_callback(page, len(all_transactions), new_count)
        
        except KeyboardInterrupt:
            print(f"\n\n⚠ Export interrupted by user at page {page}")
            print(f"✓ Returning {len(all_transactions)} transactions collected so far")
            # Store data in instance variable so caller can retrieve it
            self._interrupted_data = (all_transactions, token_symbols)
            raise
        
        print("-" * 80)
        print(f"✓ Export complete: {len(all_transactions)} unique transactions across {page} pages")
        
        return all_transactions, token_symbols
