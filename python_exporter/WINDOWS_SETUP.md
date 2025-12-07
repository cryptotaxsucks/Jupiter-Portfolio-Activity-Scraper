# Windows Installation Guide

Quick setup guide for running the Jupiter Portfolio exporter on Windows.

## Step 1: Install Python

Open **PowerShell** and run:

```powershell
winget install Python.Python.3.12
```

After installation completes, **close and reopen PowerShell**, then verify:

```powershell
python --version
```

You should see: `Python 3.12.x`

### Troubleshooting: "Python was not found"

If you see "Python was not found" after installing:

1. Open **Settings** → **Apps** → **App execution aliases**
2. Toggle **OFF** both:
   - `python.exe`
   - `python3.exe`
3. Close and reopen PowerShell
4. Try `python --version` again

## Step 2: Download the Exporter Files

1. Download all files from the `python_exporter` folder
2. Save them to a folder like: `C:\Users\YOUR_NAME\Downloads\python_exporter`

## Step 3: Install Dependencies

Open **PowerShell** and navigate to the folder:

```powershell
cd C:\Users\YOUR_NAME\Downloads\python_exporter
```

Install the required packages:

```powershell
pip install -r requirements.txt
```

This installs `curl_cffi` which handles the Chrome-like browser fingerprinting needed for Jupiter's API.

---

## Running the Exporter

### First: Open PowerShell and Navigate to the Folder

1. Press **Windows key**, type **PowerShell**, and press Enter
2. Navigate to the folder where you saved the exporter files:

```powershell
cd C:\Users\YOUR_NAME\Downloads\python_exporter
```

Replace `YOUR_NAME` with your actual Windows username. For example:
```powershell
cd C:\Users\matth\Downloads\python_exporter
```

### Single Wallet: `simple_export.py`

For exporting one wallet at a time:

```powershell
python simple_export.py
```

You'll be prompted to:
1. Enter your wallet address
2. Paste the request headers from Chrome DevTools

### Multiple Wallets: `multi_export.py`

For exporting multiple wallets in parallel:

```powershell
python multi_export.py WALLET1 WALLET2 WALLET3
```

Replace `WALLET1`, `WALLET2`, `WALLET3` with your actual wallet addresses, separated by spaces.

---

## How to Get Request Headers from Chrome

This is the critical step - you need to copy headers from your browser:

1. Open Chrome and go to: `https://jup.ag/portfolio/YOUR_WALLET_ADDRESS`
2. Press **F12** to open Developer Tools
3. Click the **Network** tab at the top
4. On the Jupiter page, click the **Activity** tab
5. Click **"Load more"** to trigger a request
6. In the Network panel, look for a request to `portfolio-api-jup.sonar.watch`
7. Click on that request
8. Click the **Headers** tab on the right
9. Scroll down to **Request Headers**
10. Select ALL the request headers text (from the first line to the last)
11. **Right-click → Copy**

### Pasting Headers in PowerShell

1. **Right-click** in the PowerShell window to paste
2. Press **Enter** after pasting
3. Press **Ctrl+Z** then **Enter** to signal you're done

**Note:** Don't worry about "pseudo-headers" (lines starting with `:` like `:authority`, `:method`, `:path`). The script automatically filters these out - just copy everything and paste it.

---

## Command Options

### Date Filtering

Export only transactions within a specific date range:

```powershell
# Single wallet with date range
python simple_export.py --start-date 2024-01-01 --end-date 2024-12-31

# Multiple wallets with date range
python multi_export.py WALLET1 WALLET2 --start-date 2024-01-01 --end-date 2024-12-31

# Just a start date (everything from that date onward)
python simple_export.py --start-date 2024-01-01

# Just an end date (everything up to that date)
python simple_export.py --end-date 2024-06-30
```

**Date format:** `YYYY-MM-DD` (year-month-day)

### Resume Interrupted Exports

If an export gets interrupted, you can resume where you left off:

```powershell
# Resume single wallet (will prompt for wallet address)
python simple_export.py --resume

# Resume multiple wallets (MUST provide the same wallet list)
python multi_export.py WALLET1 WALLET2 --resume
```

**Important:** When resuming multi-wallet exports, you must provide the same wallet addresses you used before. The script looks for `.resume-WALLET.json` files to know where to continue.

### Parallel Processing (Multi-Wallet Only)

Control how many wallets export simultaneously:

```powershell
# Export 3 wallets with 2 running in parallel (default)
python multi_export.py WALLET1 WALLET2 WALLET3

# Export with 3 parallel workers
python multi_export.py WALLET1 WALLET2 WALLET3 --parallel 3
```

**Recommended:** 2-3 parallel max to avoid rate limiting.

### Load Wallets from File

Create a text file with one wallet address per line:

```
# wallets.txt
ABC123...first_wallet
DEF456...second_wallet
GHI789...third_wallet
```

Then run:

```powershell
python multi_export.py --wallets-file wallets.txt
```

---

## Output Files

### Normal Export
```
all-activities-YOUR_WALLET.csv
```

### Interrupted Export
```
all-activities-YOUR_WALLET.partial.csv   (incomplete data)
all-activities-YOUR_WALLET.backup.csv    (same as partial)
.resume-YOUR_WALLET.json                 (resume checkpoint)
```

---

## Common Issues

### "ModuleNotFoundError: No module named 'curl_cffi'"

Run:
```powershell
pip install curl_cffi
```

### "Could not find 'authorization' header"

Make sure you:
1. Copied ALL the request headers (not just a few lines)
2. Copied from the correct request (must be to `portfolio-api-jup.sonar.watch`)
3. Clicked "Load more" on Jupiter before copying headers

### "Headers expired"

The authentication tokens expire after about 30 minutes. Copy fresh headers and try again.

### Export is very slow

This is normal! Jupiter's API takes 30-40 seconds per page for historical data. For a wallet with 10,000 transactions:
- 100 pages needed
- ~1 hour total export time

Use date filtering to speed things up if you don't need the full history.

### Ctrl+C to Stop

You can safely press **Ctrl+C** at any time to stop the export. Your progress will be saved and you can resume later with `--resume`.

---

## Complete Examples

### Export 2024 transactions for tax purposes
```powershell
python simple_export.py --start-date 2024-01-01 --end-date 2024-12-31
```

### Export multiple wallets for 2024
```powershell
python multi_export.py WALLET1 WALLET2 WALLET3 --start-date 2024-01-01 --end-date 2024-12-31
```

### Resume an interrupted multi-wallet export
```powershell
python multi_export.py WALLET1 WALLET2 WALLET3 --resume
```

### Full history export (may take hours for large wallets)
```powershell
python simple_export.py
```

---

## Need Help?

- **RELIABILITY_FEATURES.md** - Detailed documentation on auto-save, resume, and all reliability features
- The script will guide you through each step when you run it
