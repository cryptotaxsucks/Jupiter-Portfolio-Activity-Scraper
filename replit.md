# Jupiter Portfolio Full CSV Export - Chrome Extension

## Overview

A Chrome extension (Manifest V3) that exports complete Jupiter Portfolio transaction history to CSV format. The extension handles large datasets (10,000+ transactions) without requiring manual pagination, running the export process in the background even when the popup is closed. It captures authentication headers from the Jupiter website and uses them to paginate through the Portfolio API, deduplicating transactions and formatting them into a CSV file.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Chrome Extension Architecture (MV3)

**Problem**: Need to export large transaction datasets from Jupiter Portfolio without manual intervention while maintaining Chrome MV3 compliance.

**Solution**: Multi-component architecture with page-world bridge for header capture and background service worker for data processing.

**Components**:
- **Popup UI** (`popup.html`, `popup.js`, `popup.css`): User interface for initiating exports and displaying diagnostics
- **Content Script** (`content.js`): Injects bridge script into page context
- **Bridge Script** (`bridge.js`): Runs in page world, intercepts `fetch()` calls to capture authentication headers
- **Background Service Worker** (`background.js`): Orchestrates the export process, handles API pagination, and manages downloads
- **Offscreen Document** (`offscreen.html`, `offscreen.js`): Keeps service worker alive during long-running operations and handles blob creation for downloads

**Rationale**: MV3 service workers have limited lifetime, and content scripts cannot access page-level authentication. The bridge pattern solves both issues by running code in the page's JavaScript context while maintaining secure communication with the extension.

### Authentication Header Capture

**Problem**: Jupiter Portfolio API requires two authentication headers (`authorization` bearer token and `x-turnstile-token`) that are only available in the page's fetch requests.

**Solution**: Wrapper pattern around `window.fetch` in page world that intercepts API calls and extracts headers.

**Implementation**:
1. Content script injects `bridge.js` into page's JavaScript context
2. Bridge wraps `window.fetch` and monitors requests to `portfolio-api-jup.sonar.watch`
3. When target request detected, headers are extracted and sent via `postMessage` to content script
4. Content script stores headers in `chrome.storage.local` with timestamp

**Alternatives considered**: 
- WebRequest API blocking (deprecated in MV3, removed from implementation)
- Declarative Net Request (cannot capture dynamic tokens)

**Pros**: Works with dynamic tokens, MV3 compliant, minimal permissions
**Cons**: Requires user to trigger at least one "Load more" action to capture headers

### Background Export Process

**Problem**: Export must continue running even if popup closes, service worker may terminate during long operations.

**Solution**: Offscreen document for keepalive + stateless pagination using API cursor.

**Flow**:
1. Popup sends export request to background worker with wallet address and page limit
2. Background worker validates headers are captured and fresh
3. Creates offscreen document to maintain service worker alive
4. Paginates through API using `before` cursor (last transaction signature)
5. Deduplicates transactions by `signature|owner` composite key
6. Accumulates CSV rows in memory
7. On completion, triggers download via offscreen document or data URL fallback
8. Sends progress notifications and messages to popup

**API Pagination**:
- Endpoint: `GET https://portfolio-api-jup.sonar.watch/v1/transactions/fetch`
- Parameters: `address`, `limit` (capped at 100), `before` (cursor)
- Cursor strategy: Use last transaction's `signature` field as next page's `before` parameter
- Rate limiting: Exponential backoff on 429/5xx errors (not fully visible in truncated code)

**Data Processing**:
- Flattens `balanceChanges` array into individual CSV rows
- Deduplication key: `${signature}|${owner}`
- CSV columns: `signature, owner, isSigner, blockTime, platformId, serviceName, fees, success, ticker, address, preBalance, postBalance, balanceChange`

**Pros**: Handles unlimited transaction counts, survives popup closure, MV3 compliant
**Cons**: Memory-bound by total CSV size (acceptable for transaction data)

### Download Mechanism

**Problem**: Service worker cannot directly create Blob URLs, downloads must work reliably.

**Solution**: Offscreen document with Blob API, data URL fallback.

**Primary path**: Offscreen document receives CSV text, creates Blob, generates object URL, triggers `chrome.downloads.download`
**Fallback**: Data URL encoding if offscreen API unavailable

### Progress Tracking

**Problem**: User needs feedback during long-running exports, popup may be closed.

**Solution**: Dual-channel progress reporting via Chrome notifications and runtime messages.

**Channels**:
- Chrome notifications API for system-level progress updates (survives popup closure)
- Runtime messages for popup UI updates (when popup is open)

## External Dependencies

### Third-party APIs

**Jupiter Portfolio API**
- Base URL: `https://portfolio-api-jup.sonar.watch/v1/transactions/fetch`
- Authentication: Bearer token + Turnstile token (captured from page)
- Response format: JSON with `transactions` array and `tokenInfo` map
- Rate limits: Server-enforced 100 transaction limit per request
- CORS: Supports wildcard origin when credentials omitted

### Chrome Extension APIs

- `chrome.storage.local`: Persist captured authentication headers
- `chrome.runtime`: Message passing between components
- `chrome.notifications`: Display export progress to user
- `chrome.downloads`: Trigger CSV file download
- `chrome.offscreen`: Create background document for service worker keepalive
- `chrome.scripting`: Inject content scripts (via manifest declaration)

### Browser Features

- `window.fetch`: Wrapped for header interception in page context
- `postMessage`: Communication between page world and content script
- `Blob` / `URL.createObjectURL`: CSV file creation in offscreen context

### Domains

- `https://jup.ag/*`: Jupiter Portfolio website (header capture source)
- `https://portfolio-api-jup.sonar.watch/*`: Transaction data API