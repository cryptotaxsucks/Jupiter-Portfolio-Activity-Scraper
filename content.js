console.log("[content] Jupiter Export content script loaded");

chrome.runtime.sendMessage({ cmd: "injectBridge" }).catch(() => {});

window.addEventListener("message", (e) => {
  if (e.source !== window) return;
  const msg = e.data;
  
  if (msg?.source === "jup-export" && msg.type === "captured") {
    console.log("[content] Headers captured from bridge");
    chrome.storage.local.set({
      jupHeaders: {
        authorization: msg.headers.authorization,
        xturnstile: msg.headers.xturnstile,
        accept: msg.headers.accept,
        capturedAt: Date.now(),
        hasBridge: true
      }
    });
    chrome.runtime.sendMessage({ cmd: "headersCaptured" }).catch(() => {});
  }
});
