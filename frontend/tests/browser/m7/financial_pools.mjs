"use strict";

import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const credential = readFileSync(0, "utf8");
let browser;
let stage = "browser_launch";
try {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext({ baseURL: origin, viewport: { width: 1366, height: 900 } });
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  stage = "login";
  await page.goto("/login");
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("heading", { name: "AgentMonitor", exact: true }).waitFor();
  const call = (method, path, body = undefined, headers = {}) => page.evaluate(async ({ method, path, body, headers }) => {
    const csrf = decodeURIComponent(document.cookie.split("; ").find((part) => part.startsWith("agentmonitor_csrf=")).split("=")[1]);
    const response = await fetch(path, { method, headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf, ...headers }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
    return { status: response.status, etag: response.headers.get("etag"), body: await response.json() };
  }, { method, path, body, headers });
  const key = () => crypto.randomUUID();
  async function source(name) {
    const account = await call("POST", "/api/v1/accounts", { provider_key: "claude", friendly_name: name, organization_id: null, initial_connection_purpose: "api" }, { "Idempotency-Key": key() });
    assert.equal(account.status, 201);
    const billing = await call("POST", `/api/v1/accounts/${account.body.account_id}/billing-connections`, { scope_id: "isolated-owner-asserted-scope" }, { "If-Match": account.etag, "Idempotency-Key": key() });
    assert.equal(billing.status, 201);
    return { account: account.body, resource: billing.body, path: `/api/v1/accounts/${account.body.account_id}/financial-pools/${billing.body.resource_id}/billing` };
  }
  stage = "owner_metadata";
  const first = await source("Pool browser primary");
  const second = await source("Pool browser secondary");
  const organization = await call("POST", "/api/v1/organizations", { name: "Pool browser organization", description: null }, { "Idempotency-Key": key() });
  assert.equal(organization.status, 201);
  await page.goto(`/accounts/${first.account.account_id}`);
  await page.getByRole("heading", { name: first.account.friendly_name, exact: true }).waitFor();
  stage = "pool_controls_missing";
  const controls = page.locator("details[data-financial-pool]");
  await controls.locator("summary").waitFor();
  assert.equal(await controls.getAttribute("open"), null);
  await controls.locator("summary").click();
  stage = "create_pool";
  await controls.getByLabel("Primary dashboard organization", { exact: true }).selectOption(organization.body.organization_id);
  await controls.getByRole("button", { name: "Create distinct billing pool", exact: true }).click();
  await controls.getByText("Pool browser primary · billing", { exact: true }).first().waitFor();
  const created = await call("GET", first.path);
  assert.equal(created.status, 200);
  assert.equal(created.body.pool.primary_organization_id, organization.body.organization_id);
  stage = "join_pool";
  await page.goto(`/accounts/${second.account.account_id}`);
  await controls.locator("summary").click();
  await controls.getByLabel("Existing billing pool", { exact: true }).selectOption(created.body.pool.pool_id);
  await controls.getByRole("button", { name: "Use existing billing pool", exact: true }).click();
  await controls.getByText("Pool browser primary · billing", { exact: true }).first().waitFor();
  const joined = await call("GET", second.path);
  assert.equal(joined.body.pool.pool_id, created.body.pool.pool_id);
  stage = "shared_overview";
  const asOf = new Date();
  const end = new Date(asOf); end.setUTCHours(0, 0, 0, 0);
  const start = new Date(end.getTime() - 7 * 86400000);
  const query = new URLSearchParams({ period_start: start.toISOString(), period_end: end.toISOString(), as_of: asOf.toISOString(), organization_ids: organization.body.organization_id, include_ungrouped: "false", provider_key: "claude" });
  const overview = await call("GET", `/api/v1/budgets?${query}`);
  assert.equal(overview.status, 200);
  assert.equal(overview.body.page.has_more, false);
  assert.equal(overview.body.items.length, 1);
  const canonical = overview.body.items[0];
  assert.equal(canonical.pool_id, created.body.pool.pool_id);
  assert.equal(canonical.primary_organization_id, organization.body.organization_id);
  assert.equal(canonical.counted_in_selection, true);
  assert.deepEqual(canonical.access_paths.map((path) => path.account.account_id).sort(), [first.account.account_id, second.account.account_id].sort());
  assert.equal(canonical.contexts.length, 0);
  assert.equal(canonical.funds.length, 0);
  await page.goto(`/?${query}&resource_type=api`);
  await page.locator(".financial-overview[aria-busy=false]").waitFor();
  const row = page.locator("tr[data-financial-row]");
  assert.equal(await row.count(), 1);
  assert.equal(await row.getAttribute("data-financial-row"), canonical.row_id);
  await row.getByText(organization.body.name, { exact: true }).waitFor();
  await row.getByRole("button", { name: created.body.pool.display_name, exact: true }).waitFor();
  await row.getByText("2 connected accounts", { exact: true }).click();
  await row.getByRole("button", { name: first.account.friendly_name, exact: true }).waitFor();
  await row.getByRole("button", { name: second.account.friendly_name, exact: true }).click();
  await page.waitForURL((url) => url.pathname === `/accounts/${second.account.account_id}`);
  assert.equal(new URL(page.url()).searchParams.get("organization_ids"), organization.body.organization_id);
  assert.equal(new URL(page.url()).searchParams.has("budget_report"), false);
  await controls.locator("summary").click();
  stage = "edit_attribution";
  await controls.getByLabel("Primary dashboard organization", { exact: true }).selectOption("");
  await controls.getByRole("button", { name: "Save primary organization", exact: true }).click();
  await controls.getByText("Primary dashboard organization: Ungrouped", { exact: true }).waitFor();
  assert.equal((await call("GET", first.path)).body.pool.primary_organization_id, null);
  stage = "unlink_pool";
  await controls.getByRole("button", { name: "Unlink billing pool", exact: true }).click();
  await controls.getByText("No billing pool association.", { exact: true }).waitFor();
  assert.equal((await call("GET", second.path)).body.pool, null);
  assert.equal((await call("GET", first.path)).body.pool.pool_id, created.body.pool.pool_id);
  stage = "stale_revision";
  await controls.locator("div[aria-busy=false]").waitFor();
  assert.equal((await call("POST", "/api/v1/organizations", { name: "Concurrent pool group", description: null }, { "Idempotency-Key": key() })).status, 201);
  await controls.getByLabel("Existing billing pool", { exact: true }).selectOption(created.body.pool.pool_id);
  await controls.getByRole("button", { name: "Use existing billing pool", exact: true }).click();
  await controls.getByText("The account, scope or registry changed. Review its current pool status before making another change.", { exact: true }).waitFor();
  assert.equal((await call("GET", second.path)).body.pool, null);
  await controls.getByRole("button", { name: "Use current pool status", exact: true }).click();
  stage = "uncertain_outcome";
  const attempts = [];
  const observe = (request) => {
    if (["POST", "PUT"].includes(request.method()) && request.url().includes("/financial-pools/")) attempts.push(request.headers()["idempotency-key"]);
  };
  page.on("request", observe);
  await context.setOffline(true);
  await controls.getByRole("button", { name: "Create distinct billing pool", exact: true }).click();
  await controls.getByText("The pool change outcome is unknown. Refresh pool status, then resolve the previous change with its original request identity.", { exact: true }).waitFor();
  assert.equal(await controls.getByRole("button", { name: "Create distinct billing pool", exact: true }).isDisabled(), true);
  assert.equal(attempts.length, 1);
  await context.setOffline(false);
  await page.reload();
  await controls.locator("summary").click();
  await controls.getByText("A previous pool change needs reconciliation. Its original request is retained; it will not retry automatically.", { exact: true }).waitFor();
  assert.equal(attempts.length, 1);
  await controls.getByRole("button", { name: "Resolve previous change", exact: true }).click();
  await controls.getByText("Billing pool change saved.", { exact: true }).waitFor();
  assert.equal(attempts.length, 2);
  assert.ok(attempts[0]);
  assert.equal(attempts[0], attempts[1]);
  page.off("request", observe);
  const resolved = await call("GET", second.path);
  assert.ok(resolved.body.pool);
  assert.notEqual(resolved.body.pool.pool_id, created.body.pool.pool_id);
  stage = "pagination";
  // Genuine owner metadata created through the isolated service, not seeded telemetry.
  for (let index = 0; index < 201; index += 1) {
    assert.equal((await call("POST", "/api/v1/organizations", { name: `Paged pool group ${String(index).padStart(3, "0")}`, description: null }, { "Idempotency-Key": key() })).status, 201);
  }
  const pagedSource = await source("Paged owner pool choices");
  for (let index = 0; index < 50; index += 1) {
    const current = await call("GET", pagedSource.path);
    const saved = await call("POST", pagedSource.path, { action: "create", pool_id: null, primary_organization_id: null }, { "If-Match": current.etag, "Idempotency-Key": key() });
    assert.equal(saved.status, 200);
  }
  const groupIds = [];
  let groupCursor = null;
  do {
    const groups = await call("GET", `/api/v1/organizations?limit=200${groupCursor === null ? "" : `&cursor=${encodeURIComponent(groupCursor)}`}`);
    assert.equal(groups.status, 200);
    groupIds.push(...groups.body.items.filter((group) => group.lifecycle === "active").map((group) => group.organization_id));
    groupCursor = groups.body.page.has_more ? groups.body.page.next_cursor : null;
  } while (groupCursor !== null);
  const current = await call("GET", second.path);
  const poolIds = [];
  let after = null;
  do {
    const pools = await call("GET", `/api/v1/financial-pools?provider_key=claude&limit=50&expected_registry_revision=${current.body.registry_revision}${after === null ? "" : `&after_pool_id=${encodeURIComponent(after)}`}`);
    assert.equal(pools.status, 200);
    poolIds.push(...pools.body.items.filter((pool) => pool.selector === "billing").map((pool) => pool.pool_id));
    after = pools.body.next_pool_id;
  } while (after !== null);
  assert.ok(groupIds.length > 200 && poolIds.length > 50);
  await controls.getByRole("button", { name: "Refresh pool status", exact: true }).click();
  await controls.getByRole("button", { name: "Create distinct billing pool", exact: true }).waitFor({ state: "visible" });
  await page.waitForFunction(({ groups, pools }) => {
    const root = document.querySelector("details[data-financial-pool]");
    return root?.querySelectorAll("select")[0]?.options.length === groups + 1 && root?.querySelectorAll("select")[1]?.options.length === pools + 1;
  }, { groups: groupIds.length, pools: poolIds.length });
  assert.deepEqual((await controls.getByLabel("Primary dashboard organization", { exact: true }).locator("option").evaluateAll((options) => options.map((option) => option.value).filter(Boolean))).sort(), groupIds.sort());
  assert.deepEqual((await controls.getByLabel("Existing billing pool", { exact: true }).locator("option").evaluateAll((options) => options.map((option) => option.value).filter(Boolean))).sort(), poolIds.sort());
  stage = "reload_keyboard_narrow";
  await page.reload();
  await controls.locator("summary").focus();
  await controls.locator("summary").press("Enter");
  await controls.getByText(resolved.body.pool.display_name, { exact: true }).first().waitFor();
  await page.setViewportSize({ width: 768, height: 900 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  stage = "no_provider_work";
  assert.equal((await call("GET", `/api/v1/accounts/${first.account.account_id}/billing-connections`)).body.credential_status.state, "missing");
  assert.equal((await call("GET", `/api/v1/accounts/${second.account.account_id}/billing-connections`)).body.connections[0].monitoring_preference, "disabled");
  console.log("M7 FINANCIAL POOLS BROWSER: PASSED");
} catch {
  console.error(`M7 FINANCIAL POOLS BROWSER: FAILED — ${stage}`);
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
}
