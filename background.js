const API_BASE = "https://portfolio-api-jup.sonar.watch/v1/transactions/fetch";
const NOTIF_ID = "jup-export-progress";
let keepaliveCreated = false;

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

function clampLimit(n) {
  if (!Number.isFinite(n)) return 100;
  return Math.max(30, Math.min(100, Math.floor(n)));
}

async function ensureOffscreen() {
  if (keepaliveCreated) return;
  try {
    const has = await chrome.offscreen.hasDocument?.();
    if (!has) {
      await chrome.offscreen.createDocument({
        url: "offscreen.html",
        reasons: [chrome.offscreen.Reason.BLOBS],
        justification: "Keep service worker alive and support long-running export with Blob API"
      });
      console.log("[bg] Offscreen document created");
    }
    keepaliveCreated = true;
  } catch (e) {
    console.warn("[bg] Offscreen not available:", e);
  }
}

async function closeOffscreen() {
  if (!keepaliveCreated) return;
  try {
    await chrome.offscreen.closeDocument();
    keepaliveCreated = false;
    console.log("[bg] Offscreen document closed");
  } catch (e) {
    console.warn("[bg] Error closing offscreen:", e);
  }
}

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
    await chrome.notifications.create(NOTIF_ID, {
      type: "basic",
      iconUrl: "icons/icon128.png",
      title: "Jupiter Export",
      message: "Started…"
    });
  }
}

async function updateProgressNotification(percent, subtitle) {
  try {
    await chrome.notifications.update(NOTIF_ID, {
      type: "progress",
      iconUrl: "icons/icon128.png",
      title: "Jupiter Export",
      message: subtitle || "Fetching…",
      progress: Math.max(0, Math.min(100, Math.round(percent)))
    });
  } catch (e) {
    await chrome.notifications.update(NOTIF_ID, {
      type: "basic",
      iconUrl: "icons/icon128.png",
      title: "Jupiter Export",
      message: subtitle || "Fetching…"
    });
  }
}

async function completeNotification(filename) {
  try { await chrome.notifications.clear(NOTIF_ID); } catch {}
  try {
    await chrome.notifications.create("", {
      type: "basic",
      iconUrl: "icons/icon128.png",
      title: "Jupiter Export Complete",
      message: `CSV ready: ${filename}`
    });
  } catch {}
}

async function errorNotification(msg) {
  try { await chrome.notifications.clear(NOTIF_ID); } catch {}
  try {
    await chrome.notifications.create("", {
      type: "basic",
      iconUrl: "icons/icon128.png",
      title: "Jupiter Export – Error",
      message: msg.slice(0, 200)
    });
  } catch {}
}

async function withBackoff(fn, maxAttempts = 7) {
  let attempt = 0;
  while (true) {
    try {
      return await fn();
    } catch (e) {
      attempt++;
      if (attempt >= maxAttempts) throw e;
      const wait = Math.min(250 * Math.pow(2, attempt), 5000);
      console.log(`[bg] Backoff attempt ${attempt}, waiting ${wait}ms`);
      await sleep(wait);
    }
  }
}

async function runExport({ tabId, address, limit = 100 }) {
  const LIMIT = clampLimit(limit);
  console.log(`[bg] Starting export for ${address}, limit=${LIMIT}, tabId=${tabId}`);

  await ensureOffscreen();
  await createProgressNotification();

  const { jupHeaders } = await chrome.storage.local.get("jupHeaders");
  if (!jupHeaders?.authorization || !jupHeaders?.xturnstile) {
    throw new Error("Missing headers. Click 'Load more' once on the site, then try again.");
  }

  console.log("[bg] Headers loaded from storage");

  const headers = {
    "accept": "application/json",
    "authorization": jupHeaders.authorization,
    "x-turnstile-token": jupHeaders.xturnstile
  };

  async function safeFetch(url) {
    return withBackoff(async () => {
      const res = await fetch(url, {
        headers,
        credentials: "omit",
        mode: "cors"
      });

      if (!res.ok) {
        if (res.status === 400) {
          const txt = await res.text().catch(() => "");
          if (/limit must not be greater than 100/i.test(txt)) {
            throw new Error("Server rejected page size > 100. Use 100 or smaller.");
          }
        }
        if (res.status === 401 || res.status === 403) {
          throw new Error("Auth failed. Refresh headers by clicking 'Load more' on the site.");
        }
        if (res.status === 429 || res.status >= 500) {
          throw new Error(`HTTP ${res.status} - retrying...`);
        }
        throw new Error(`HTTP ${res.status}`);
      }
      return res;
    });
  }

  function buildUrl(beforeSig) {
    const u = new URL(API_BASE);
    u.searchParams.set("address", address);
    u.searchParams.set("limit", String(LIMIT));
    if (beforeSig) u.searchParams.set("before", beforeSig);
    return u.toString();
  }

  const allTxs = [];
  const seen = new Set();
  const tokenSymbols = new Map();
  let before = null;
  let page = 0;
  let lastNotifAt = 0;

  async function reportProgress(subtitle) {
    const now = Date.now();
    if (now - lastNotifAt > 500) {
      lastNotifAt = now;
      const percent = Math.min(99, Math.floor((page % 200) / 200 * 100));
      await updateProgressNotification(percent, subtitle);
    }
  }

  while (true) {
    page++;
    console.log(`[bg] Fetching page ${page}, before=${before || 'null'}`);
    
    const res = await safeFetch(buildUrl(before));
    const data = await res.json().catch(() => ({}));
    const txs = Array.isArray(data) ? data : (data?.transactions || []);
    
    if (!txs.length) {
      console.log(`[bg] No more transactions, stopping at page ${page}`);
      break;
    }

    const ti = data?.tokenInfo || {};
    for (const [mint, info] of Object.entries(ti)) {
      let sym = info?.symbol;
      if (!sym && info && typeof info === "object") {
        for (const v of Object.values(info)) {
          if (v?.symbol) {
            sym = v.symbol;
            break;
          }
        }
      }
      if (sym) tokenSymbols.set(mint, sym);
    }

    for (const tx of txs) {
      const key = `${tx.signature}|${tx.owner}`;
      if (!seen.has(key)) {
        seen.add(key);
        allTxs.push(tx);
      }
    }

    before = txs[txs.length - 1].signature;

    chrome.runtime.sendMessage({
      cmd: "progress",
      tabId,
      page,
      fetched: txs.length,
      total: allTxs.length
    }).catch(() => {});

    await reportProgress(`Fetched page ${page} (+${txs.length}, total ${allTxs.length})`);
    await sleep(120);
  }

  console.log(`[bg] Export complete: ${allTxs.length} transactions across ${page} pages`);

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

  const csvText = lines.join("\n");
  const filename = `all-activities-${address}.csv`;

  console.log(`[bg] CSV generated: ${lines.length} lines`);

  try {
    await chrome.runtime.sendMessage({
      cmd: "download",
      csvText,
      filename
    });
    await sleep(500);
  } catch (e) {
    console.warn("[bg] Offscreen download failed, using data URL fallback:", e);
    const dataUrl = "data:text/csv;charset=utf-8," + encodeURIComponent(csvText);
    await chrome.downloads.download({ url: dataUrl, filename, saveAs: true });
  }

  await closeOffscreen();
  chrome.runtime.sendMessage({ cmd: "done", tabId }).catch(() => {});
  await completeNotification(filename);
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.cmd === "export") {
    sendResponse({ ok: true, started: true });
    runExport({ tabId: msg.tabId, address: msg.address, limit: msg.limit }).catch(err => {
      console.error("[bg] export failed", err);
      chrome.runtime.sendMessage({
        cmd: "error",
        tabId: msg.tabId,
        error: err?.message || String(err)
      }).catch(() => {});
      errorNotification(err?.message || String(err));
    });
    return true;
  }

  if (msg?.cmd === "getDiagnostics") {
    chrome.storage.local.get("jupHeaders").then(({ jupHeaders }) => {
      sendResponse({
        headersReady: !!(jupHeaders?.authorization && jupHeaders?.xturnstile),
        capturedAt: jupHeaders?.capturedAt || null,
        hasBridge: jupHeaders?.hasBridge || false
      });
    });
    return true;
  }

  if (msg?.cmd === "injectBridge" && sender?.tab?.id) {
    chrome.scripting.executeScript({
      target: { tabId: sender.tab.id },
      world: "MAIN",
      func: () => {
        console.log("[bridge] Jupiter Export bridge script loaded (page world)");

        const originalFetch = window.fetch;
        let captured = false;

        window.fetch = function(...args) {
          const [resource, init] = args;
          const url = typeof resource === "string" ? resource : resource?.url;

          if (url && url.includes("portfolio-api-jup.sonar.watch/v1/transactions/fetch")) {
            const headers = init?.headers || {};
            const headerMap = headers instanceof Headers ? 
              Object.fromEntries([...headers.entries()]) : 
              (headers || {});

            const auth = headerMap["authorization"] || headerMap["Authorization"];
            const turnstile = headerMap["x-turnstile-token"] || headerMap["X-Turnstile-Token"];
            const accept = headerMap["accept"] || headerMap["Accept"];

            if (auth && turnstile && !captured) {
              console.log("[bridge] Captured headers from fetch");
              captured = true;
              
              window.postMessage({
                source: "jup-export",
                type: "captured",
                headers: {
                  authorization: auth,
                  xturnstile: turnstile,
                  accept: accept || "application/json"
                }
              }, "*");
            }
          }

          return originalFetch.apply(this, args);
        };

        console.log("[bridge] Fetch wrapper armed");
      }
    }).then(() => {
      console.log(`[bg] Bridge injected into tab ${sender.tab.id} via chrome.scripting`);
    }).catch(err => {
      console.error("[bg] Failed to inject bridge:", err);
    });
    sendResponse({ ok: true });
    return true;
  }
});

console.log("[bg] Background service worker initialized");
