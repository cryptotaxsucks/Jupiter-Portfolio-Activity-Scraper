# Jupiter Portfolio Python Exporter

A Python script that exports all Jupiter Portfolio transactions to CSV format. Faster and more reliable than the Chrome extension for large datasets.

## Quick Start (Easiest Method)

**For environments without browser support (like Replit) or the simplest experience:**

```bash
cd python_exporter
pip install requests pandas
python simple_export.py
```

You'll be prompted to:
1. Enter your wallet address
2. Paste your authorization token
3. Paste your x-turnstile-token

Then it automatically exports everything to CSV!

### How to Get Your Tokens (30 seconds)

1. Open `https://jup.ag/portfolio/YOUR_WALLET_ADDRESS` in your browser
2. Press **F12** to open Developer Tools
3. Click the **Network** tab
4. Click **Load more** on Jupiter's page
5. Find a request to `portfolio-api-jup.sonar.watch` 
6. Click it → **Headers** tab → **Request Headers**
7. Copy the `authorization` and `x-turnstile-token` values

That's it!

---

## Advanced: Automatic Mode (Requires Browser Dependencies)

If you're on a local machine with full browser support, you can use automatic header capture:

### Requirements

- Python 3.11+
- Playwright with Chromium browser

### Installation

1. Install dependencies:
   ```bash
   cd python_exporter
   pip install -r requirements.txt
   ```

2. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```

## Usage

### Basic Export

```bash
python main.py YOUR_WALLET_ADDRESS
```

This will:
1. Open a browser window to Jupiter Portfolio
2. Automatically capture authentication headers
3. Fetch all transactions via API
4. Export to `all-activities-YOUR_WALLET_ADDRESS.csv`

### Options

```bash
# Use smaller page size (if having issues)
python main.py YOUR_WALLET_ADDRESS --limit 50

# Run browser in headless mode (no visible window)
python main.py YOUR_WALLET_ADDRESS --headless

# Reuse previously captured headers (faster for multiple wallets)
python main.py YOUR_WALLET_ADDRESS --reuse-headers

# Custom output filename
python main.py YOUR_WALLET_ADDRESS --output my-export.csv
```

### Exporting Multiple Wallets

The `--reuse-headers` flag is useful when exporting multiple wallets:

```bash
# First wallet: capture headers
python main.py WALLET_1

# Subsequent wallets: reuse headers (much faster)
python main.py WALLET_2 --reuse-headers
python main.py WALLET_3 --reuse-headers
```

**Note**: Headers typically expire after some time. If you get authentication errors, recapture by removing the `--reuse-headers` flag.

## Speed Comparison

The Python script should be **significantly faster** than the Chrome extension for large datasets because:

1. No browser rendering overhead
2. Direct API calls via Python's requests library
3. No service worker lifecycle limitations
4. Better memory management

## How It Works

1. **Header Capture** (`header_capture.py`):
   - Launches Chromium browser via Playwright
   - Navigates to Jupiter Portfolio page
   - Intercepts network requests using CDP (Chrome DevTools Protocol)
   - Captures `authorization` and `x-turnstile-token` headers
   - Saves headers to `captured_headers.json`

2. **API Client** (`api_client.py`):
   - Uses captured headers to make authenticated API requests
   - Paginates through all transactions (100 per page)
   - Deduplicates by `signature|owner` key
   - Tracks token symbols from API responses

3. **CSV Export** (`csv_exporter.py`):
   - Converts transactions to CSV rows
   - Expands balance changes into individual rows
   - Matches Jupiter's official CSV format
   - Exports using pandas for reliability

## Troubleshooting

### "Failed to capture authentication headers"

- Make sure the browser window loads completely
- Try manually clicking "Load more" in the browser window
- Run without `--headless` to see what's happening
- Check your internet connection

### "Authentication failed. Headers may have expired"

- Remove `--reuse-headers` flag to recapture fresh headers
- Delete `captured_headers.json` and try again

### Browser installation issues

If Playwright can't find browsers:
```bash
playwright install chromium
```

## CSV Format

The exported CSV matches Jupiter's format:

```
signature,owner,isSigner,blockTime,platformId,serviceName,fees,success,ticker,address,preBalance,postBalance,balanceChange
```

Each row represents a balance change within a transaction.

## Files

- `main.py` - Command-line entry point
- `header_capture.py` - Browser automation for header capture
- `api_client.py` - Jupiter API client with pagination
- `csv_exporter.py` - CSV generation logic
- `captured_headers.json` - Saved authentication headers (gitignored)
