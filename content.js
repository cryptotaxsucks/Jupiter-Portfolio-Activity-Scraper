console.log("[content] Jupiter Export content script loaded");

const script = document.createElement("script");
script.src = chrome.runtime.getURL("bridge.js");
script.onload = () => {
  script.remove();
  console.log("[content] Bridge script injected");
};
(document.documentElement || document.head).appendChild(script);

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
