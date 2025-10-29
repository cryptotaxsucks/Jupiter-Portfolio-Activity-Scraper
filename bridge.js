console.log("[bridge] Jupiter Export bridge script loaded (page world)");

const originalFetch = window.fetch;
let captured = false;

window.fetch = function(...args) {
  const [resource, init] = args;
  const url = typeof resource === "string" ? resource : resource?.url;

  // Debug: Log every portfolio API call
  if (url && url.includes("portfolio-api-jup.sonar.watch")) {
    console.log("[bridge] 🔍 Portfolio API fetch detected!");
    console.log("[bridge] URL:", url);
    console.log("[bridge] Raw init object:", init);
    console.log("[bridge] init type:", typeof init);
    console.log("[bridge] init?.headers:", init?.headers);
    console.log("[bridge] headers type:", typeof init?.headers);
    
    if (init?.headers) {
      if (init.headers instanceof Headers) {
        console.log("[bridge] Headers is a Headers object");
        const entries = [...init.headers.entries()];
        console.log("[bridge] Headers entries:", entries);
      } else {
        console.log("[bridge] Headers is a plain object:", init.headers);
      }
    } else {
      console.log("[bridge] ⚠️ No headers found in init object!");
    }
  }

  if (url && url.includes("portfolio-api-jup.sonar.watch/v1/transactions/fetch")) {
    const headers = init?.headers || {};
    const headerMap = headers instanceof Headers ? 
      Object.fromEntries([...headers.entries()]) : 
      (headers || {});

    console.log("[bridge] Converted headerMap:", headerMap);

    const auth = headerMap["authorization"] || headerMap["Authorization"];
    const turnstile = headerMap["x-turnstile-token"] || headerMap["X-Turnstile-Token"];
    const accept = headerMap["accept"] || headerMap["Accept"];

    console.log("[bridge] Extracted - auth:", auth ? "✅ FOUND" : "❌ MISSING");
    console.log("[bridge] Extracted - turnstile:", turnstile ? "✅ FOUND" : "❌ MISSING");

    if (auth && turnstile && !captured) {
      console.log("[bridge] ✅ Captured headers from fetch");
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
    } else if (!captured) {
      console.log("[bridge] ❌ Headers incomplete, not capturing");
    }
  }

  return originalFetch.apply(this, args);
};

console.log("[bridge] Fetch wrapper armed");
