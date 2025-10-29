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
