// background.js (MV3, module)
const API_BASE = "https://portfolio-api-jup.sonar.watch/v1/transactions/fetch";
const NOTIF_ID = "jup-export-progress";
let keepaliveCreated = false;

// In-memory header cache
const headerCache = {
  authorization: null,
  turnstile: null,
  lastSeen: 0
};

// Create offscreen document to help keep SW alive during long fetches
async function ensureOffscreen() {
  if (keepaliveCreated) return;
  const has = await chrome.offscreen.hasDocument?.();
  if (!has) {
    await chrome.offscreen.createDocument({
      url: "offscreen.html",
      reasons: [chrome.offscreen.Reason.BLOBS],
      justification: "Keep service worker alive and support long-running export"
    });
    console.log("[bg] Offscreen document created");
  }
  keepaliveCreated = true;
}

// Passive capture of auth headers from real site traffic
chrome.webRequest.onBeforeSendHeaders.addListener(
  (details) => {
    try {
      const url = new URL(details.url);
      if (url.hostname.endsWith("sonar.watch") && url.pathname.includes("/v1/transactions/fetch")) {
        for (const h of details.requestHeaders || []) {
          const n = h.name.toLowerCase();
          if (n === "authorization" && h.value) headerCache.authorization = h.value;
          if (n === "x-turnstile-token" && h.value) headerCache.turnstile = h.value;
        }
        headerCache.lastSeen = Date.now();
      }
    } catch {}
    return { requestHeaders: details.requestHeaders };
  },
  { urls: ["https://portfolio-api-jup.sonar.watch/*"] },
  ["requestHeaders"]
);

// Utilities
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

function clampLimit(n) {
  if (!Number.isFinite(n)) return 100;
  return Math.max(30, Math.min(100, Math.floor(n)));
}

// Notifications
async function createProgressNotification() {
  try {
    await chrome.notifications.create(NOTIF_ID, {
      type: "progress",
      iconUrl: "icons/icon128.png",
      title: "Jupiter Export",
      message: "Fetching…",
      progress: 0
    });
  } catch (e) {
    // Older Chrome variants or permission issues
    // Fallback to basic without progress
    await chrome.notifications.create(NOTIF_ID, {
      type: "basic",
      iconUrl: "icons/icon128.png",
      title: "Jupiter Export",
      message: "Started…"
    });
  }
}

async function updateProgressNotification(percent, subtitle) {
  // If we created as "basic", DO NOT include progress (causes lastError)
  try {
    await chrome.notifications.update(NOTIF_ID, {
      type: "progress",
      iconUrl: "icons/icon128.png",
      title: "Jupiter Export",
      message: subtitle || "Fetching…",
      progress: Math.max(0, Math.min(100, Math.round(percent)))
    });
  } catch (e) {
    // fallback: basic without progress
    await chrome.notifications.update(NOTIF_ID, {
      type: "basic",
      iconUrl: "icons/icon128.png",
      title: "Jupiter Export",
      message: subtitle || "Fetching…"
    });
  }
}

async function completeNotification(filename) {
  // Clear progress and show completion
  try { await chrome.notifications.clear(NOTIF_ID); } catch {}
  try {
    await chrome.notifications.create("", {
      type: "basic",
      iconUrl: "icons/icon128.png",
      title: "Jupiter Export",
      message: `CSV ready: ${filename}`
    });
  } catch {}
}

// Export core
async function runExport({ tabId, address, limit = 100 }) {
  await ensureOffscreen();
  const LIMIT = clampLimit(limit);

  // Create progress notification
  await createProgressNotification();

  const headers = () => {
    if (!headerCache.authorization || !headerCache.turnstile) return null;
    return {
      "accept": "application/json",
      "authorization": headerCache.authorization,
      "x-turnstile-token": headerCache.turnstile
    };
  };

  // If no headers yet, try to gently nudge the page to fire a legit request
  async function tryNudgeAndWaitHeaders() {
    const start = Date.now();
    // Attempt to click a "Load more" (does nothing if not present)
    try {
      await chrome.scripting.executeScript({
        target: { tabId },
        world: "MAIN",
        func: () => {
          const btns = [...document.querySelectorAll("button,div,span")];
          const b = btns.find(b => /load\s*more/i.test(b.textContent || ""));
          if (b) b.click();
        }
      });
    } catch {}
    // wait up to 6s
    for (let i = 0; i < 12; i++) {
      if (headers()) return true;
      await sleep(500);
    }
    return !!headers();
  }

  if (!headers()) {
    chrome.runtime.sendMessage({ cmd: "progress", tabId, page: 0, fetched: 0, total: 0 });
    const ok = await tryNudgeAndWaitHeaders();
    if (!ok) throw new Error("Could not capture auth headers. Click “Load more” once, then try again.");
  }

  const allTxs = [];
  const seen = new Set();
  const tokenSymbols = new Map();

  let before = null;
  let page = 0;
  let lastNotifAt = 0;

  async function safeFetch(url) {
    const res = await fetch(url, {
      headers: headers(),
      credentials: "omit",
      mode: "cors"
    });
    if (!res.ok) {
      if (res.status === 400) {
        const txt = await res.text().catch(()=> "");
        if (/limit must not be greater than 100/i.test(txt)) {
          throw new Error("Server rejected page size > 100. Use 100 or smaller.");
        }
      }
      if (res.status === 401 || res.status === 403) {
        throw new Error("Auth failed. Refresh headers by clicking “Load more” on the site.");
      }
      if (res.status === 429 || res.status >= 500) {
        // backoff & retry up to a handful of times
        for (let a = 1; a <= 6; a++) {
          const wait = Math.min(250 * 2 ** a, 5000);
          await sleep(wait);
          const r2 = await fetch(url, { headers: headers(), credentials: "omit", mode: "cors" });
          if (r2.ok) return r2;
        }
      }
      throw new Error(`HTTP ${res.status}`);
    }
    return res;
  }

  function buildUrl(beforeSig) {
    const u = new URL(API_BASE);
    u.searchParams.set("address", address);
    u.searchParams.set("limit", String(LIMIT));
    if (beforeSig) u.searchParams.set("before", beforeSig);
    return u.toString();
  }

  // Progress notify helper (throttle to 500ms to reduce spam)
  async function reportProgress(subtitle) {
    const now = Date.now();
    if (now - lastNotifAt > 500) {
      lastNotifAt = now;
      const percent = Math.min(99, Math.floor((page % 200) / 200 * 100)); // unknown total; fake gentle progress
      await updateProgressNotification(percent, subtitle);
    }
  }

  // Fetch loop
  while (true) {
    page++;
    const res = await safeFetch(buildUrl(before));
    const data = await res.json().catch(()=> ({}));
    const txs = Array.isArray(data) ? data : (data?.transactions || []);
    if (!txs.length) break;

    const ti = data?.tokenInfo || {};
    for (const [mint, info] of Object.entries(ti)) {
      let sym = info?.symbol;
      if (!sym && info && typeof info === "object") {
        for (const v of Object.values(info)) { if (v?.symbol) { sym = v.symbol; break; } }
      }
      if (sym) tokenSymbols.set(mint, sym);
    }

    for (const tx of txs) {
      const key = `${tx.signature}|${tx.owner}`;
      if (!seen.has(key)) { seen.add(key); allTxs.push(tx); }
    }
    before = txs[txs.length - 1].signature;

    chrome.runtime.sendMessage({ cmd: "progress", tabId, page, fetched: txs.length, total: allTxs.length });
    await reportProgress(`Fetched page ${page} (+${txs.length})`);

    // polite pacing
    await sleep(120);
  }

  // Build CSV
  const esc = (v) => {
    let s = String(v ?? "");
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const header = "signature,owner,isSigner,blockTime,platformId,serviceName,fees,success,ticker,address,preBalance,postBalance,balanceChange";
  const lines = [header];

  for (const tx of allTxs) {
    const sig = tx.signature ?? "";
    const owner = tx.owner ?? "";
    const isSigner = !!tx.isSigner;
    const blockIso = tx.blockTime ? new Date(tx.blockTime * 1000).toISOString() : "";
    const platformId = tx.service?.platformId ?? "";
    const serviceName = tx.service?.name ?? "";
    const fees = tx.fees ?? "";
    const success = tx.success ?? "";
    const changes = Array.isArray(tx.balanceChanges) ? tx.balanceChanges : [];

    for (const bc of changes) {
      const mint = bc.address ?? "";
      const ticker = tokenSymbols.get(mint) || "";
      const pre = (bc.preBalance ?? "").toString();
      const post = (bc.postBalance ?? "").toString();
      const delta = (bc.change ?? "").toString();
      lines.push([
        esc(sig), esc(owner), esc(isSigner), esc(blockIso),
        esc(platformId), esc(serviceName), esc(fees), esc(success),
        esc(ticker), esc(mint), esc(pre), esc(post), esc(delta)
      ].join(","));
    }
  }

  // Download via data URL (no blob: URL in SW)
  const csvText = lines.join("\n");
  const filename = `all-activities-${address}.csv`;

  // Prefer FileReader to build data URL from Blob (handles large files more reliably)
  const dataUrl = await new Promise((resolve, reject) => {
    try {
      const blob = new Blob([csvText], { type: "text/csv;charset=utf-8" });
      const fr = new FileReader();
      fr.onerror = (e) => reject(e);
      fr.onloadend = () => resolve(fr.result);
      fr.readAsDataURL(blob);
    } catch (e) {
      // fallback: encodeURIComponent
      resolve("data:text/csv;charset=utf-8," + encodeURIComponent(csvText));
    }
  });

  await chrome.downloads.download({ url: dataUrl, filename, saveAs: true }).catch(()=>{});
  chrome.runtime.sendMessage({ cmd: "done", tabId });

  await completeNotification(filename);
}

// Message entrypoint
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.cmd === "export") {
    // Immediate ack
    sendResponse({ ok: true, started: true });
    // Fire-and-forget
    runExport({ tabId: msg.tabId, address: msg.address, limit: msg.limit }).catch(err => {
      console.error("[bg] export failed", err);
      chrome.runtime.sendMessage({ cmd: "error", tabId: msg.tabId, error: err?.message || String(err) });
      // failure notice
      chrome.notifications.create("", {
        type: "basic",
        iconUrl: "icons/icon128.png",
        title: "Jupiter Export – Error",
        message: (err?.message || String(err)).slice(0, 200)
      });
    });
    return true; // keep message channel for any async (though we already responded)
  }
});

