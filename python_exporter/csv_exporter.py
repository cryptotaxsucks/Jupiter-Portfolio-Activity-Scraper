import pandas as pd
from datetime import datetime
from typing import List, Dict

class CSVExporter:
    COLUMNS = [
        "signature", "owner", "isSigner", "blockTime", "platformId", 
        "serviceName", "fees", "success", "ticker", "address", 
        "preBalance", "postBalance", "balanceChange"
    ]
    
    def __init__(self, token_symbols: Dict[str, str]):
        self.token_symbols = token_symbols
    
    def transactions_to_rows(self, transactions: List[Dict]) -> List[Dict]:
        rows = []
        
        for tx in transactions:
            signature = tx.get("signature", "")
            owner = tx.get("owner", "")
            is_signer = tx.get("isSigner", False)
            
            block_time = tx.get("blockTime")
            block_time_iso = ""
            if block_time:
                try:
                    block_time_iso = datetime.utcfromtimestamp(block_time).isoformat() + "Z"
                except:
                    pass
            
            service = tx.get("service", {}) or {}
            platform_id = service.get("platformId", "")
            service_name = service.get("name", "")
            
            fees = tx.get("fees", "")
            success = tx.get("success", "")
            
            balance_changes = tx.get("balanceChanges", [])
            if not balance_changes:
                balance_changes = [{}]
            
            for bc in balance_changes:
                mint = bc.get("address", "")
                ticker = self.token_symbols.get(mint, "")
                pre_balance = bc.get("preBalance", "")
                post_balance = bc.get("postBalance", "")
                balance_change = bc.get("change", "")
                
                row = {
                    "signature": signature,
                    "owner": owner,
                    "isSigner": is_signer,
                    "blockTime": block_time_iso,
                    "platformId": platform_id,
                    "serviceName": service_name,
                    "fees": fees,
                    "success": success,
                    "ticker": ticker,
                    "address": mint,
                    "preBalance": pre_balance,
                    "postBalance": post_balance,
                    "balanceChange": balance_change
                }
                rows.append(row)
        
        return rows
    
    def export_to_csv(self, transactions: List[Dict], filename: str):
        print(f"\nGenerating CSV...")
        rows = self.transactions_to_rows(transactions)
        
        df = pd.DataFrame(rows, columns=self.COLUMNS)
        
        df.to_csv(filename, index=False)
        print(f"✓ CSV exported to {filename}")
        print(f"  Total rows: {len(df):,}")
        print(f"  Unique transactions: {len(transactions):,}")
        
        return filename
