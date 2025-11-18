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

Install the Chromium browser for automation:

```powershell
playwright install chromium
```

## Step 4: Run the Exporter

### Option A: Automatic Mode (Recommended)

The script will open a browser, capture your authentication automatically:

```powershell
python main.py YOUR_WALLET_ADDRESS
```

Example:
```powershell
python main.py 3ShJGgszdh6M8VDxLeWqv2EyESNSxnnhopKq3V3vgnqT
```

The browser will:
1. Open Jupiter Portfolio
2. Click the "Activity" tab automatically
3. Capture your authentication tokens
4. Download all transactions to CSV

### Option B: Simple Mode (Manual Token Input)

If the automatic mode doesn't work, use simple mode:

```powershell
python simple_export.py
```

You'll be prompted to:
1. Enter wallet address
2. Paste authorization token (from browser DevTools)
3. Paste turnstile token (from browser DevTools)

See the main README.md for instructions on finding these tokens.

## Common Issues

### "ModuleNotFoundError: No module named 'requests'"

Run:
```powershell
pip install requests
```

### Browser doesn't open or crashes

Try running in visible mode (not headless):
```powershell
python main.py YOUR_WALLET --no-headless
```

### Headers not captured

The script now automatically clicks the "Activity" tab. If it still fails:
1. When the browser window opens, manually click "Activity" tab
2. The script will wait 30 seconds for you to trigger a request

### Exporting multiple wallets

After capturing headers once, reuse them for other wallets:

```powershell
# First wallet - captures headers
python main.py WALLET_1

# Other wallets - reuses saved headers (faster)
python main.py WALLET_2 --reuse-headers
python main.py WALLET_3 --reuse-headers
```

## Output

Your CSV file will be saved as:
```
all-activities-YOUR_WALLET_ADDRESS.csv
```

This matches Jupiter's official export format and can be imported directly into your accounting tools.
