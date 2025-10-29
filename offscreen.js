console.log("[offscreen] Offscreen document loaded");

let port = chrome.runtime.connect({ name: "keepalive" });
port.onDisconnect.addListener(() => {
  try {
    port = chrome.runtime.connect({ name: "keepalive" });
  } catch (e) {
    console.warn("[offscreen] Cannot reconnect:", e);
  }
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.cmd === "download") {
    console.log("[offscreen] Received download request");
    
    try {
      const blob = new Blob([msg.csvText], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      
      chrome.downloads.download({
        url: url,
        filename: msg.filename,
        saveAs: true
      }).then(() => {
        console.log("[offscreen] Download started");
        URL.revokeObjectURL(url);
        sendResponse({ ok: true });
      }).catch((err) => {
        console.error("[offscreen] Download failed:", err);
        sendResponse({ ok: false, error: err.message });
      });
      
      return true;
    } catch (e) {
      console.error("[offscreen] Error creating blob:", e);
      sendResponse({ ok: false, error: e.message });
    }
  }
});
