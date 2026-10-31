"use strict";

const unsafeMethods = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function csrfCookie() {
  const entry = document.cookie.split(";").map((item) => item.trim()).find(
    (item) => item.startsWith("agentmonitor_csrf="),
  );
  return entry ? entry.slice("agentmonitor_csrf=".length) : null;
}

window.ui = SwaggerUIBundle({
  url: "/openapi.json",
  dom_id: "#swagger-ui",
  presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
  layout: "StandaloneLayout",
  persistAuthorization: false,
  requestInterceptor: (request) => {
    const headers = request.headers || {};
    const bearer = Object.entries(headers).some(
      ([name, value]) => name.toLowerCase() === "authorization" &&
        /^Bearer\s+\S+$/i.test(String(value)),
    );
    request.credentials = bearer ? "omit" : "same-origin";
    if (bearer) {
      for (const name of Object.keys(headers)) {
        if (name.toLowerCase() === "x-csrf-token") delete headers[name];
      }
    } else if (unsafeMethods.has(String(request.method || "GET").toUpperCase())) {
      const csrf = csrfCookie();
      if (csrf) headers["X-CSRF-Token"] = csrf;
    }
    return request;
  },
});
