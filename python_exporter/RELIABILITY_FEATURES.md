# Reliability Features Guide

This document explains all the features that make the Jupiter Portfolio exporter reliable for large datasets and long-running exports.

## Features Overview

The exporter now includes four major reliability features:
1. **Auto-save** - Automatic backup every page
2. **Graceful Interrupt** - Safe Ctrl+C handling that saves progress
3. **Resume Capability** - Continue interrupted exports from where you left off
4. **Date Range Filtering** - Export only transactions within a specific date range

---

## 1. Auto-Save

**What it does:** Automatically saves your progress after every page of transactions is fetched.

**How it works:**
- Creates a `.backup.csv` file in the same directory as your export
- Updates the backup after every page (100 transactions)
- Also creates a `.resume-<wallet>.json` file with the last transaction signature

**Why it's useful:**
- If the script crashes unexpectedly, you don't lose your data
- The backup file contains all transactions fetched so far
- You can use the resume feature to continue from where it left off

**Files created:**
```
python_exporter/
  └─ jupiter_transactions_2025-11-19.backup.csv    (auto-saved progress)
  └─ .resume-ABC123.json                           (resume checkpoint)
```

---

## 2. Graceful Interrupt (Ctrl+C)

**What it does:** Lets you safely stop the export at any time and save your progress.

**How to use:**
- Press **Ctrl+C** while the export is running
- The script will immediately stop and save all collected transactions
- Creates a file with `.partial` in the name to indicate it's incomplete

**What happens when you interrupt:**
1. Script stops fetching new pages
2. Saves all collected transactions to CSV with `.partial` suffix
3. Keeps the `.backup.csv` and `.resume-*.json` files for later resuming
4. Shows you how many transactions were saved

**Example output:**
```
⚠ Export interrupted by user at page 47
✓ Returning 4,700 transactions collected so far
  Saving progress...

✓ Exported 4,700 transactions to jupiter_transactions_2025-11-19.partial.csv
💾 Backup saved: jupiter_transactions_2025-11-19.backup.csv
📍 Resume file: .resume-ABC123.json
```

---

## 3. Resume Capability

**What it does:** Continue an interrupted export from exactly where it left off.

**How to use:**
```powershell
# First run - gets interrupted
python simple_export.py ABC123

# Resume the export later
python simple_export.py ABC123 --resume
```

**How it works:**
- The `.resume-<wallet>.json` file stores the last transaction signature
- When you use `--resume`, the script starts from that transaction
- Deduplicates any overlapping transactions automatically
- Merges new data with your previous export

**Resume file example:**
```json
{
  "wallet_address": "ABC123...",
  "last_signature": "5XYZ789...",
  "timestamp": "2025-11-19T15:30:00",
  "transactions_count": 4700
}
```

**Important notes:**
- Resume files are cleaned up automatically when an export completes successfully
- If you want to start fresh, delete the `.resume-*.json` file or don't use `--resume`
- The script will ask for confirmation before resuming

---

## 4. Date Range Filtering

**What it does:** Export only transactions within a specific date range.

**How to use:**
```powershell
# Export only transactions from 2024
python simple_export.py ABC123 --start-date 2024-01-01 --end-date 2024-12-31

# Export transactions since March 2024
python simple_export.py ABC123 --start-date 2024-03-01

# Export transactions up to June 2024
python simple_export.py ABC123 --end-date 2024-06-30
```

**Date format:** `YYYY-MM-DD` (e.g., `2024-03-15`)

**How it works:**
- Filters transactions based on their `blockTime` timestamp
- Stops early when it reaches the start date (oldest transaction you want)
- Skips pages that are entirely outside your date range for efficiency
- Shows filtered count in the progress output

**Example output:**
```
Page   1: 100 returned, 100 new,   0 dupes, total=  100, fetch=  850ms
Page   2: 100 returned,  85 new,   0 dupes, total=  185, fetch=  920ms, 15 filtered by date
Page   3: 100 returned,  72 new,   0 dupes, total=  257, fetch=  890ms, 28 filtered by date

✓ Reached start date limit. Stopping.
```

---

## Complete Usage Examples

### Example 1: Basic export with auto-save
```powershell
python simple_export.py ABC123
```
- Exports all transactions
- Auto-saves progress every page
- Press Ctrl+C if you need to stop

### Example 2: Resume interrupted export
```powershell
python simple_export.py ABC123 --resume
```
- Continues from last saved position
- Merges with previous partial export

### Example 3: Export specific year
```powershell
python simple_export.py ABC123 --start-date 2024-01-01 --end-date 2024-12-31
```
- Only gets 2024 transactions
- Stops automatically at date boundaries

### Example 4: Resume with date filter
```powershell
python simple_export.py ABC123 --start-date 2024-01-01 --resume
```
- Continues from last position
- Still applies date filter to new data

---

## Files Created During Export

### Normal completion:
```
jupiter_transactions_2025-11-19.csv          Final export
```

### During export (auto-save enabled):
```
jupiter_transactions_2025-11-19.backup.csv   Auto-saved progress
.resume-ABC123.json                          Resume checkpoint
```

### After interruption (Ctrl+C):
```
jupiter_transactions_2025-11-19.partial.csv  Incomplete export
jupiter_transactions_2025-11-19.backup.csv   Same data as partial
.resume-ABC123.json                          Resume checkpoint
```

### After successful resume:
```
jupiter_transactions_2025-11-19.csv          Complete export
```
(The `.backup.csv` and `.resume-*.json` files are automatically deleted)

---

## Tips for Large Exports

**For 10,000+ transaction wallets:**

1. **Start the export and let it run overnight**
   ```powershell
   python simple_export.py YOUR_WALLET
   ```
   - Jupiter's API is slow (30-40 seconds per page)
   - 10,000 transactions = 100 pages = ~1 hour
   - Auto-save protects your progress

2. **If you need to stop:**
   - Press **Ctrl+C** (Windows PowerShell)
   - Your progress is saved automatically
   - You won't lose any data

3. **Resume later:**
   ```powershell
   python simple_export.py YOUR_WALLET --resume
   ```
   - Picks up exactly where you left off
   - No duplicate transactions

4. **Export specific time periods:**
   ```powershell
   python simple_export.py YOUR_WALLET --start-date 2024-01-01
   ```
   - Much faster than exporting everything
   - Great for tax year exports

---

## Troubleshooting

### "Resume file found but --resume not specified"
- The script found a previous incomplete export
- Add `--resume` to continue, or delete the `.resume-*.json` file to start fresh

### "Resume file is from a different wallet"
- You're trying to resume with the wrong wallet address
- Delete the `.resume-*.json` file or use the correct wallet address

### "Headers expired - please capture fresh headers"
- Authentication headers are older than 30 minutes
- Copy new headers from Chrome DevTools and run again

### Export is very slow
- This is normal - Jupiter's API takes 30-40 seconds per page
- The API is genuinely slow for historical data (confirmed by Jupiter team)
- Use date filters to export only what you need

---

## Complete Command Reference

```powershell
# Basic export
python simple_export.py <wallet_address>

# Resume interrupted export
python simple_export.py <wallet_address> --resume

# Export with date range
python simple_export.py <wallet_address> --start-date YYYY-MM-DD --end-date YYYY-MM-DD

# Export since specific date
python simple_export.py <wallet_address> --start-date YYYY-MM-DD

# Export up to specific date
python simple_export.py <wallet_address> --end-date YYYY-MM-DD

# Resume with date filter
python simple_export.py <wallet_address> --resume --start-date YYYY-MM-DD
```

---

## How the Features Work Together

All four features work seamlessly together:

1. **Auto-save** runs continuously in the background
2. **Date filtering** stops the export efficiently when date limits are reached
3. **Graceful interrupt** lets you stop anytime and saves progress
4. **Resume** picks up where you left off, respecting date filters

**Example scenario:**
- Start exporting 2024 transactions: `python simple_export.py ABC123 --start-date 2024-01-01`
- Script auto-saves after every page
- Need to close laptop - press Ctrl+C
- Progress saved with `.partial` suffix
- Next day: `python simple_export.py ABC123 --start-date 2024-01-01 --resume`
- Continues from last transaction, merges with previous data
- Completes export and cleans up temporary files
