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
    
    def fetch_all_transactions(self, address: str, limit: int = 100, progress_callback=None):
        all_transactions = []
        seen_signatures = set()
        token_symbols = {}
        before = None
        page = 0
        last_fetch_time = 0
        
        print(f"\nFetching transactions for {address}...")
        print(f"Using page size: {limit}")
        print("-" * 80)
        
        while True:
            page += 1
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
            
            for tx in transactions:
                sig = tx.get("signature")
                owner = tx.get("owner")
                key = f"{sig}|{owner}"
                
                if key not in seen_signatures:
                    seen_signatures.add(key)
                    all_transactions.append(tx)
                else:
                    duplicates += 1
            
            new_count = len(all_transactions) - before_count
            
            print(f"Page {page:3d}: {len(transactions):3d} returned, {new_count:3d} new, "
                  f"{duplicates:3d} dupes, total={len(all_transactions):5d}, "
                  f"fetch={fetch_time:6.0f}ms")
            
            if new_count == 0:
                print(f"\n✓ All transactions were duplicates. Export complete.")
                break
            
            before = transactions[-1].get("signature")
            
            if progress_callback:
                progress_callback(page, len(all_transactions), new_count)
        
        print("-" * 80)
        print(f"✓ Export complete: {len(all_transactions)} unique transactions across {page} pages")
        
        return all_transactions, token_symbols
