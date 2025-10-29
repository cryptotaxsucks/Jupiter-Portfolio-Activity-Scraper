const addrEl = document.getElementById("addr");
const limitEl = document.getElementById("limit");
const goBtn = document.getElementById("go");
const diagnosticsBtn = document.getElementById("diagnostics");
const statusEl = document.getElementById("status");

function log(line) {
  statusEl.textContent += (statusEl.textContent ? "\n" : "") + line;
  statusEl.scrollTop = statusEl.scrollHeight;
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

function addressFromUrl(url) {
  try {
    const u = new URL(url);
    const parts = u.pathname.split("/").filter(Boolean);
    const i = parts.indexOf("portfolio");
    if (i >= 0 && parts[i + 1]) return decodeURIComponent(parts[i + 1]);
  } catch {}
  return "";
}

(async () => {
  const tab = await getActiveTab();
  addrEl.value = addressFromUrl(tab?.url) || "";
})();

let progressListener = null;

goBtn.addEventListener("click", async () => {
  statusEl.textContent = "";
  const tab = await getActiveTab();
  if (!tab?.id) {
    log("No active tab.");
    return;
  }

  let address = addrEl.value.trim();
  if (!address) address = addressFromUrl(tab.url);
  if (!address) {
    log("Enter a wallet address or open a Jupiter portfolio page.");
    return;
  }

  const limit = Math.max(30, Math.min(100, Number(limitEl.value || 100)));

  log("Starting export… (you can close this popup)");

  if (progressListener) chrome.runtime.onMessage.removeListener(progressListener);
  progressListener = (msg) => {
    if (msg?.cmd === "progress" && msg.tabId === tab.id) {
      const parts = [];
      if (msg.page) parts.push(`page ${msg.page}`);
      if (msg.fetched != null) parts.push(`+${msg.fetched}`);
      if (msg.total != null) parts.push(`total=${msg.total}`);
      log(parts.join(" "));
    }
    if (msg?.cmd === "done" && msg.tabId === tab.id) {
      log("Done. CSV downloading…");
    }
    if (msg?.cmd === "error" && msg.tabId === tab.id) {
      log("Error: " + msg.error);
    }
  };
  chrome.runtime.onMessage.addListener(progressListener);

  const resp = await chrome.runtime.sendMessage({
    cmd: "export",
    tabId: tab.id,
    address,
    limit
  });
  
  if (!resp?.ok) {
    log("Could not start: " + (resp?.error || "Unknown"));
  }
});

diagnosticsBtn.addEventListener("click", async () => {
  statusEl.textContent = "";
  log("Running diagnostics…");
  
  try {
    const diag = await chrome.runtime.sendMessage({ cmd: "getDiagnostics" });
    log(`hasBridge: ${diag.hasBridge}`);
    log(`headersReady: ${diag.headersReady}`);
    if (diag.capturedAt) {
      const ago = Math.floor((Date.now() - diag.capturedAt) / 1000);
      log(`capturedAt: ${ago}s ago`);
    }
    
    if (!diag.headersReady) {
      log("\n⚠ Click 'Load more' once on Jupiter, then try again.");
    } else {
      log("\n✓ Ready to export!");
    }
  } catch (e) {
    log("Error: " + e.message);
  }
});
