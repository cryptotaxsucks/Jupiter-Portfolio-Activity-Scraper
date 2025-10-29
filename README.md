# Jupiter Portfolio Full CSV Export (v5)

Chrome extension to export all Jupiter Portfolio transactions to CSV without manual clicking.

## Features

- Export **all** transaction history (10k+ transactions) without clicking "Load more"
- Runs in background - popup can be closed during export
- Progress notifications
- Automatic header capture from page
- MV3 compliant (no deprecated APIs)

## Installation

1. Download or clone this repository
2. Open Chrome and navigate to `chrome://extensions/`
3. Enable "Developer mode" (top right toggle)
4. Click "Load unpacked"
5. Select the folder containing this extension

## Usage

### First Time Setup

1. **Navigate** to Jupiter Portfolio page: `https://jup.ag/portfolio/[your-wallet-address]`
2. **Click "Load more"** button once on the transactions page
   - This allows the extension to capture authentication headers
3. **Open the extension popup** (click the extension icon)
4. **Click "Export Full CSV"**
5. The popup can be closed - export runs in background
6. You'll receive a notification when complete

### Diagnostics

Click the "Diagnostics" button in the popup to check:
- `hasBridge`: Bridge script is injected
- `headersReady`: Authentication headers captured
- `capturedAt`: When headers were last captured

If headers aren't ready, click "Load more" once on the Jupiter site.

## How It Works

1. **Content script** (`content.js`) injects a **bridge script** into the page
2. **Bridge script** (`bridge.js`) wraps `window.fetch` in page context to capture auth headers
3. **Background service worker** (`background.js`) handles the export:
   - Paginates through all transactions (limit=100 per page)
   - Deduplicates by signature|owner
   - Assembles CSV with columns matching Jupiter's format
   - Downloads via offscreen document (or data URL fallback)

## CSV Format

```
signature,owner,isSigner,blockTime,platformId,serviceName,fees,success,ticker,address,preBalance,postBalance,balanceChange
```

Each row represents a balance change within a transaction.

## Troubleshooting

**"Missing headers" error**
- Click "Load more" once on the Jupiter transactions page
- Wait 1-2 seconds, then try export again

**"Auth failed" error**
- Headers expired - click "Load more" again to refresh

**Export stops mid-way**
- Check browser console for errors
- Ensure stable internet connection
- Extension will retry on 429/5xx errors with backoff

**Download doesn't start**
- Check Chrome's download permissions
- Look for notification in system tray

## Technical Notes

- Uses Manifest V3 (no deprecated APIs like `webRequestBlocking`)
- Page-world bridge captures headers without CORS issues
- Offscreen document for Blob API in service worker context
- Exponential backoff for rate limits (up to 7 retries)
- Progress notifications with type="progress"

## Development

Files:
- `manifest.json` - Extension manifest (MV3)
- `background.js` - Service worker (export logic)
- `content.js` - Content script (bridge injector)
- `bridge.js` - Page-world script (header capture)
- `popup.html/js/css` - Extension popup UI
- `offscreen.html/js` - Offscreen document (Blob API)

## Console Test Script

To verify header capture before export, paste this in the **page console** (not extension console):

```javascript
// Test header capture
const testUrl = 'https://portfolio-api-jup.sonar.watch/v1/transactions/fetch?address=YOUR_ADDRESS&limit=10';

// Capture headers from the first fetch
const originalFetch = window.fetch;
let capturedHeaders = null;

window.fetch = async function(...args) {
  const [resource, init] = args;
  const url = typeof resource === 'string' ? resource : resource?.url;
  
  if (url?.includes('portfolio-api-jup.sonar.watch')) {
    capturedHeaders = init?.headers;
    console.log('Captured headers:', capturedHeaders);
  }
  
  return originalFetch.apply(this, args);
};

// Trigger by clicking "Load more", then check console for captured headers
```

## License

MIT

## Version History

- v5.0.0 - MV3 rebuild with page-world bridge, offscreen downloads
- v3.0.0 - Original working version (had MV2 dependencies)
