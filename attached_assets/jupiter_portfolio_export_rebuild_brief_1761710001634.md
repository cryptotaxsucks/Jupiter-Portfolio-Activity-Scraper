# Rebuild Brief: Jupiter Portfolio “Full CSV Export” (v5 from v3)

## Goal
Rebuild the **working v3** Chrome extension (Manifest V3) that exports **all** Jupiter Portfolio → Transactions to CSV, **keeping the original UI/UX**, while fixing the specific issues that caused failures in later builds (manifest keys, blocking APIs, popup lifecycle, download from service worker, and header capture reliability).

---

## What we now know about the Jupiter Activity endpoint

1) **Endpoint & pagination**
- Base: `https://portfolio-api-jup.sonar.watch/v1/transactions/fetch`
- Required query params:  
  - `address=<Solana_address>`  
  - `limit<=100` (server returns **400** if `limit > 100`)
  - Optional cursor: `before=<last_signature_from_previous_page>`
- Response shape:
  ```json
  {
    "transactions": [ /* array of tx objects */ ],
    "tokenInfo": { /* map: mint -> { symbol, ... } OR nested network maps */ }
  }
  ```
- Cursoring rule: for the next page, set `before = lastTransaction.signature`.

2) **Headers (must be captured from the page)**
- The site sends and expects **both**:  
  - `authorization: Bearer <token>`  
  - `x-turnstile-token: <token>`
- With `credentials: "omit"` we avoid the CORS wildcard issue. Replay of captured headers **works (200)** and can be reused at least twice (we verified 200 + 200).  
- If capture is missing or stale, endpoint returns **401** (Unauthorized).

3) **Rate limits & errors**
- 400 → “limit must not be greater than 100”
- 429 / 5xx → implement exponential backoff (e.g., 250ms → 500 → 1s → 2s → max 5s; up to ~6–7 attempts)

4) **CSV columns (match site’s export)**
```
signature,owner,isSigner,blockTime,platformId,serviceName,fees,success,ticker,address,preBalance,postBalance,balanceChange
```
- Deduplicate rows keyed by `signature|owner`.
- `blockTime` → ISO string if present.
- `ticker` can be looked up from `tokenInfo` (mint → symbol), best effort.

---

## Problems in v3+ builds that must be fixed (and how)

1) **Manifest errors**
- **“Unrecognized manifest key 'offscreen_pages'.”**  
  - MV3 does **not** support a static `offscreen_pages` manifest key.  
  - **Fix:** keep `"offscreen"` in `"permissions"`, and at runtime call:
    ```js
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['BLOBS'],
      justification: 'Create Blob URL and trigger file download outside the service worker.'
    });
    ```
  - Remember to stop it when done:
    ```js
    await chrome.offscreen.closeDocument();
    ```

- **“'webRequestBlocking' requires manifest version of 2 or lower.”**  
  - v3 must **not** use `chrome.webRequest`/`webRequestBlocking`.  
  - **Fix:** remove all `webRequest` usage. We will **not** proxy or modify network requests at the browser level.

2) **CSP / inline script warnings**
- Keep **all** scripts in external files; no inline JS in HTML.  
- Same for popup and offscreen docs. This eliminates CSP errors we saw earlier.

3) **Popup lifecycle / long-running job**
- We saw: *“A listener indicated an asynchronous response… but the message channel closed…”* when the popup closed mid-run.  
- **Fix:** The **service worker** owns the export run. The popup only sends a `start` message and can be closed immediately. Status is communicated via:
  - `chrome.notifications` (safe, persists without popup), **or**
  - an optional badge (`chrome.action.setBadgeText`) and a “Diagnostics” page in the popup that subscribes to `chrome.runtime.onMessage`.
- Do **not** rely on `sendMessage` expecting a reply from the long task; use a **Port** or **fire-and-forget** request and notify completion via notifications.

4) **Downloads from service worker**
- We saw: **`URL.createObjectURL is not a function`** in SW.  
- MV3 service workers are DOM-less; you can’t directly create object URLs reliably.  
- Two robust options:
  - **(A) Offscreen document**: pass the CSV string to `offscreen.html`, have it build the Blob + `URL.createObjectURL` and call `chrome.downloads.download({ url, filename })`.  
  - **(B) Data URL** (no offscreen): build a `data:text/csv;charset=utf-8,<encoded>` and pass to `chrome.downloads.download`. Works, but huge CSVs can hit data-URL size limits; **prefer (A)** for large exports.

5) **Notifications API misuse**
- We saw: **“The progress value should not be specified for non-progress notification.”**  
  - **Fix:** When including `progress`, `type` must be `"progress"`. Otherwise, omit `progress` field.

6) **Header capture reliability**
- Content scripts run in an **isolated world**; `window.fetch` patched there **does not** affect the page’s own fetch.  
- **Fix:** inject a **page-world** bridge script (via `chrome.scripting.executeScript` or by adding a `web_accessible_resources` loader) that:
  - Patches **page** `window.fetch`.
  - Captures headers **the next time the page calls** the target endpoint (user clicks “Load more” once).
  - Stores headers on `window.__jupCaptured` and/or posts a `window.postMessage` back to the content script.
- Popup should show **clear instructions**: “Open wallet transactions → Click **Load more once** → then click **Start**.”

---

## Architecture to implement (keep original UI)

**Files (as in v3, plus the bridge):**
- `manifest.json` (MV3)
- `background.js` (service worker; owns the export loop)
- `content.js` (isolated; injects **page-world** bridge, relays postMessage)
- `bridge.js` (page-world, patches `window.fetch` to capture headers; simple)
- `popup.html`, `popup.js`, `popup.css` (original UI; Start, Diagnostics)
- `offscreen.html`, `offscreen.js` (only if using Blob route for downloads)
- Icons unchanged

**Flow:**
1) User opens Jupiter **transactions** page.  
2) User clicks **Load more** once.  
   - `bridge.js` (page-world) **captures** headers for the next fetch to the endpoint and posts `{authorization, x-turnstile-token, accept}` to the content script, which stores them in `chrome.storage.local`.  
3) User opens popup and clicks **Start**.  
   - Popup sends `{cmd:"startExport", address, limit: 100}` to `background.js`.  
4) Background:
   - Loads headers from `chrome.storage.local`. If missing, returns error message to popup: “Missing headers—click Load more once…”.  
   - Starts pagination loop with backoff, dedupe, and CSV assembly (in memory).  
   - Emits **progress notifications** (type `"progress"`) every N pages or M seconds.  
   - When done, either:
     - (A) creates **offscreen** doc to build Blob + download, then closes offscreen, **or**
     - (B) uses a **data URL** for small CSVs.
   - Sends a final “done” notification and clears any runtime state.

**Key Implementation Points:**
- **No `webRequest`** API.  
- Manifest must include:
  ```json
  {
    "manifest_version": 3,
    "permissions": ["downloads", "storage", "notifications", "scripting", "activeTab", "offscreen"],
    "host_permissions": [
      "https://jup.ag/*",
      "https://*.jup.ag/*",
      "https://portfolio-api-jup.sonar.watch/*"
    ],
    "background": { "service_worker": "background.js", "type": "module" },
    "action": { "default_popup": "popup.html" },
    "web_accessible_resources": [{
      "matches": ["https://jup.ag/*", "https://*.jup.ag/*"],
      "resources": ["bridge.js"]
    }]
  }
  ```
- **Popup is optional** during run. Do **not** hold a response channel open.

---

## Minimal changes to v3 codebase

1) **Remove any** `chrome.webRequest` / `webRequestBlocking` usage.  
2) **Inject page-world `bridge.js`** from the content script:
   ```js
   // content.js
   const s = document.createElement('script');
   s.src = chrome.runtime.getURL('bridge.js');
   s.onload = () => s.remove();
   (document.documentElement || document.head).appendChild(s);

   // Listen for page → extension messages
   window.addEventListener('message', (e) => {
     if (e.source !== window) return;
     const msg = e.data;
     if (msg?.source === 'jup-export' && msg.type === 'captured') {
       chrome.storage.local.set({ jupHeaders: msg.headers });
       chrome.runtime.sendMessage({ cmd: 'headersCaptured' });
     }
   });
   ```
3) **bridge.js** (page-world):
   - Patch `window.fetch` to watch the target URL and capture headers on the **next** call from the site.
   - When captured, post back:
     ```js
     window.postMessage({
       source: 'jup-export',
       type: 'captured',
       headers: {
         authorization,
         xturnstile: xTurnstile,
         accept
       }
     }, '*');
     ```
4) **background.js**
   - On `startExport`:
     - Read `jupHeaders` from storage; if absent, error out.
     - Run the export loop: `limit=100`, apply `before`, handle 429/5xx with backoff.
     - Deduplicate, assemble CSV, then download via **offscreen document** (preferred) or **data URL** fallback.
   - Notifications:
     - Use `type: "progress"` when setting `progress`, else omit `progress`.  
     - Set badge text optionally.

5) **offscreen.html/js** (optional but preferred for big CSV)
   - Receives CSV via message from SW, builds Blob, `createObjectURL`, and calls `chrome.downloads.download`.
   - Returns completion to SW; SW closes offscreen.

6) **Popup (unchanged visually)**  
   - Add a **Diagnostics** button that prints:
     - `capturedCount`, `headersReady` (existence in storage), `hasBridge` (content confirmed its injection), last captured status code, last replay status (optional).
   - Popup must **not** depend on a live message channel to the background for the run; only to kick it off and read status from storage/notifications.

---

## Developer Test Plan (before handing back)

1) **Header capture test (page console)**
   - Run the helper (we already used this) to ensure clicking **Load more** produces a capture and that **two replays return 200**.
   - If 2nd replay fails, ensure the extension captures **per page** and fetches with minimal delay.

2) **Diagnostics**
   - With the extension installed, click **Load more** once.
   - Open popup → Diagnostics, confirm:
     ```
     hasBridge: true
     headersReady: true
     capturedCount: >= 1
     lastStatus: 200
     ```
3) **Full export**
   - Start export; close popup; keep watching notifications/badge.
   - Ensure CSV downloads when complete.
   - Smoke test with an address with **>10,000** txs (ensure pagination runs to completion; no UI clicking required; no CSV truncation).

4) **Edge cases**
   - limit > 100 → ensure we never exceed 100 (avoid 400).
   - intermittent 429/5xx → verify backoff and eventual completion.
   - tokenInfo symbol resolution works “best effort”; CSV still valid if missing.

---

## Acceptance Criteria

- Original v3 **UI preserved** (visuals + user flow).  
- **No** MV2-only APIs (`webRequest`, `webRequestBlocking`).  
- **No** inline scripts (CSP-clean).  
- Export runs **to completion** without the popup open.  
- CSV downloaded reliably for large histories.  
- Error messages are actionable:
  - Missing headers → “Click **Load more** once, then Start again.”  
  - 401/403 → “Auth/Turnstile token expired. Click **Load more** again to refresh headers.”

---

## Optional: Helpful snippets

**Backoff helper**
```js
async function withBackoff(fn, max=7) {
  let attempt = 0;
  while (true) {
    try { return await fn(); }
    catch (e) {
      attempt++;
      if (attempt >= max) throw e;
      const wait = Math.min(250 * 2 ** attempt, 5000);
      await new Promise(r => setTimeout(r, wait));
    }
  }
}
```

**Download via data URL (small files)**
```js
const dataUrl = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvString);
chrome.downloads.download({ url: dataUrl, filename: `all-activities-${address}.csv` });
```
