/** Read-only check: a settled Ollama connection must keep refreshing locally. */
import assert from "node:assert/strict";
import { chromium } from "@playwright/test";

const origin = "http://127.0.0.1:43110";
let browser;
let page;
let reason = "connection_refresh_unavailable";
try {
  browser = await chromium.connectOverCDP("http://127.0.0.1:9225");
  page = await browser.contexts()[0].newPage();
  await page.goto(`${origin}/accounts`, { waitUntil: "domcontentloaded" });
  const registry = await page.request.get(`${origin}/api/v1/accounts?limit=200`, { headers: { Origin: origin } });
  assert.equal(registry.status(), 200);
  const accounts = await registry.json();
  assert.equal(accounts.page.has_more, false);
  const account = accounts.items.find(item => item.provider_key === "ollama" && item.lifecycle === "active" && item.is_effective_monitoring_enabled);
  assert.ok(account);
  const path = `/api/v1/accounts/${encodeURIComponent(account.account_id)}/ollama-cloud-connection`;
  const responses = [];
  page.on("response", response => {
    const url = new URL(response.url());
    if (url.origin === origin && url.pathname === path && response.request().method() === "GET") responses.push(response);
  });
  let writes = 0;
  page.on("request", request => {
    if (new URL(request.url()).origin === origin && !["GET", "HEAD", "OPTIONS"].includes(request.method())) writes++;
  });
  await page.goto(`${origin}/accounts/${encodeURIComponent(account.account_id)}`, { waitUntil: "domcontentloaded" });
  await page.bringToFront();
  const connection = page.getByRole("region", { name: "Ollama cloud connection" });
  await connection.waitFor();
  await page.getByText("Checking connection status…", { exact: true }).waitFor({ state: "detached" });
  assert.ok(responses.length > 0);
  const initial = await responses.at(-1).json();
  assert.ok(["access_valid_owner_confirmed", "access_valid_identity_unresolved"].includes(initial.state));
  const baseline = responses.length;
  reason = "settled_connection_not_refreshed";
  await page.waitForResponse(response => {
    const url = new URL(response.url());
    return url.origin === origin && url.pathname === path && response.request().method() === "GET" && response.status() === 200;
  }, { timeout: 22_000 });
  assert.ok(responses.length > baseline);
  reason = "connection_refresh_mutated_state";
  assert.equal(writes, 0);
  console.log(JSON.stringify({ status: "passed", local_status_refresh: true, writes: 0 }));
} catch {
  console.log(JSON.stringify({ status: "failed", reason }));
  process.exitCode = 1;
} finally {
  if (page) await page.close();
  if (browser) await browser.close();
}
