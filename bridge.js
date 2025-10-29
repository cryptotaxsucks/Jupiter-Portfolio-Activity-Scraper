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
    console.log("[bridge] resource type:", typeof resource);
    console.log("[bridge] resource instanceof Request:", resource instanceof Request);
    
    if (resource instanceof Request) {
      console.log("[bridge] ✅ Resource is a Request object!");
      console.log("[bridge] Request.headers:", resource.headers);
      const entries = [...resource.headers.entries()];
      console.log("[bridge] Request headers entries:", entries);
    }
    
    console.log("[bridge] Raw init object:", init);
    console.log("[bridge] init?.headers:", init?.headers);
  }

  if (url && url.includes("portfolio-api-jup.sonar.watch/v1/transactions/fetch")) {
    // Extract headers from Request object OR init parameter
    let headerMap = {};
    
    if (resource instanceof Request && resource.headers) {
      // Headers are in the Request object
      console.log("[bridge] Extracting headers from Request object");
      headerMap = Object.fromEntries([...resource.headers.entries()]);
    } else if (init?.headers) {
      // Headers are in init parameter
      console.log("[bridge] Extracting headers from init object");
      const headers = init.headers;
      headerMap = headers instanceof Headers ? 
        Object.fromEntries([...headers.entries()]) : 
        headers;
    }

    console.log("[bridge] Converted headerMap:", headerMap);

    const auth = headerMap["authorization"] || headerMap["Authorization"];
    const turnstile = headerMap["x-turnstile-token"] || headerMap["X-Turnstile-Token"];
    const accept = headerMap["accept"] || headerMap["Accept"];

    console.log("[bridge] Extracted - auth:", auth ? "✅ FOUND" : "❌ MISSING");
    console.log("[bridge] Extracted - turnstile:", turnstile ? "✅ FOUND" : "❌ MISSING");

    if (auth && turnstile && !captured) {
      console.log("[bridge] ✅✅✅ SUCCESSFULLY CAPTURED HEADERS! ✅✅✅");
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
