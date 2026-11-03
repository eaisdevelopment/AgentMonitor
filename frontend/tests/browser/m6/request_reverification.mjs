// Explicit live operator test: enqueue one connection check through the real API.
// Browser authentication stays in the existing browser; no credential is returned.
import { chromium } from "@playwright/test";

const [accountId] = process.argv.slice(2);
if (!/^[A-Za-z0-9_-]{1,64}$/.test(accountId ?? "")) throw Error("account_required");
const browser = await chromium.connectOverCDP("http://127.0.0.1:9225");
try {
  const page = browser.contexts().flatMap(context => context.pages())
    .find(item => item.url().startsWith("http://127.0.0.1:43110/"));
  if (!page) throw Error("signed_in_dashboard_required");
  const status = await page.evaluate(async id => {
    const current = await fetch(`/api/v1/accounts/${encodeURIComponent(id)}`);
    if (!current.ok) throw Error("account_read_failed");
    const account = await current.json();
    if (account.account_id !== id || account.provider_key !== "ollama") throw Error("account_mismatch");
    const cookie = document.cookie.split(";").map(part => part.trim())
      .find(part => part.startsWith("agentmonitor_csrf="));
    if (!cookie) throw Error("browser_csrf_unavailable");
    const response = await fetch(`/api/v1/accounts/${encodeURIComponent(id)}/ollama-cloud-connection`, {
      method: "POST",
      headers: {
        "X-CSRF-Token": decodeURIComponent(cookie.slice("agentmonitor_csrf=".length)),
        "If-Match": `"${id}.${account.record_version}"`,
        "Idempotency-Key": crypto.randomUUID().replaceAll("-", ""),
      },
    });
    return response.status;
  }, accountId);
  if (status !== 202) throw Error(`connection_request_http_${status}`);
  console.log("connection_verification_enqueued");
} finally {
  await browser.close();
}
