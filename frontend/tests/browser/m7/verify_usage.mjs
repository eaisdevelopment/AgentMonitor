"use strict";

// Existing authenticated browser and retained API reports only. No collection,
// configuration, credentials, screenshots or financial/account values in output.
const origin = "http://127.0.0.1:43110";
let page;
let status = "blocked";
let reason = "browser_unavailable";
let mutations = 0;
let accountCount = 0;
let bucketCount = 0;
let sourceRevision = null;
const checks = { authentication: "not_run", cloud_api: "not_run", usage_dom: "not_run", reload: "not_run", read_only: "not_run" };
function stop(outcome, code) { status = outcome; reason = code; throw new Error("probe_stopped"); }
function requireEvidence(condition, code) { if (!condition) stop("failed", code); }
function quantity(value) {
  const coefficient = BigInt(value.coefficient);
  const digits = (coefficient < 0n ? -coefficient : coefficient).toString().padStart(value.scale + 1, "0");
  return `${coefficient < 0n ? "-" : ""}${value.scale === 0 ? digits : `${digits.slice(0, -value.scale)}.${digits.slice(-value.scale)}`} ${value.unit}`;
}
try {
  let playwright;
  try { playwright = await import("@playwright/test"); }
  catch (error) {
    if (error?.code !== "ERR_MODULE_NOT_FOUND") throw error;
    playwright = await import("/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules/@playwright/test/index.mjs");
  }
  const browser = await playwright.chromium.connectOverCDP("http://127.0.0.1:9225", { timeout: 5000 });
  const context = browser.contexts()[0];
  if (context === undefined) stop("blocked", "browser_context_unavailable");
  page = await context.newPage();
  page.setDefaultTimeout(7000);
  page.on("request", request => { if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) mutations += 1; });
  await page.goto(origin, { waitUntil: "domcontentloaded", timeout: 10000 });
  const signIn = page.getByRole("heading", { name: "Sign in", exact: true });
  await signIn.or(page.getByRole("button", { name: "Accounts", exact: true })).first().waitFor();
  if (await signIn.isVisible()) stop("blocked", "authentication_required");
  checks.authentication = "passed";
  async function read(path) {
    const response = await page.request.get(`${origin}${path}`, { headers: { Origin: origin }, timeout: 7000 });
    if (response.status() === 401) stop("blocked", "authentication_required");
    if (response.status() !== 200) stop("blocked", "existing_api_unavailable");
    return response.json();
  }
  async function readAllAccounts() {
    const items = [];
    const identities = new Set();
    const cursors = new Set();
    let cursor;
    for (let index = 0; index < 20; index += 1) {
      const query = new URLSearchParams({ limit: "200", ...(cursor === undefined ? {} : { cursor }) });
      const result = await read(`/api/v1/accounts?${query}`);
      requireEvidence(Array.isArray(result.items) && typeof result.page?.has_more === "boolean", "inventory_page_invalid");
      for (const item of result.items) {
        if (identities.has(item.account_id)) stop("blocked", "inventory_changed_during_pagination");
        identities.add(item.account_id);
        items.push(item);
      }
      if (!result.page.has_more) {
        requireEvidence(result.page.next_cursor === null, "inventory_terminal_cursor_invalid");
        return items;
      }
      cursor = result.page.next_cursor;
      if (typeof cursor !== "string" || cursor.length === 0 || cursors.has(cursor)) stop("blocked", "inventory_cursor_unavailable");
      cursors.add(cursor);
    }
    stop("blocked", "inventory_pagination_bound_exceeded");
  }
  const versions = await read("/api/v1/operations/versions");
  if (/^[a-f0-9]{40}$/.test(versions?.source_revision?.value ?? "")) sourceRevision = versions.source_revision.value;
  const inventory = (await readAllAccounts()).filter(item => item.provider_key === "ollama" && item.lifecycle !== "archived");
  if (inventory.length === 0) stop("blocked", "existing_ollama_account_unavailable");
  async function inspect(account, reload, priorIds) {
    const path = `/api/v1/accounts/${encodeURIComponent(account.account_id)}/api-capacity`;
    const responsePromise = page.waitForResponse(response => new URL(response.url()).pathname === path && response.request().method() === "GET");
    if (reload) await page.reload({ waitUntil: "domcontentloaded" });
    else await page.goto(`${origin}/accounts/${encodeURIComponent(account.account_id)}`, { waitUntil: "domcontentloaded" });
    const response = await responsePromise;
    if (response.status() === 401) stop("blocked", "authentication_required");
    requireEvidence(response.status() === 200, "financial_api_failed");
    const financial = await response.json();
    requireEvidence(financial.account_id === account.account_id, "financial_account_mismatch");
    requireEvidence(Array.isArray(financial.cloud_resources), "cloud_usage_projection_missing");
    const reports = financial.cloud_resources.flatMap(resource => resource.reports.map(selection => ({ resource, report: selection.current })))
      .filter(item => item.report?.source_id === "ollama.cloud.usage.v1");
    const ids = reports.map(item => item.report.report_id).sort();
    if (priorIds !== undefined && JSON.stringify(ids) !== JSON.stringify(priorIds)) stop("blocked", "report_changed_during_probe");
    if (reports.length === 0) return ids;
    checks.cloud_api = "passed";
    const panel = page.getByRole("region", { name: "API usage & spend", exact: true });
    await panel.waitFor();
    await panel.getByRole("button", { name: "Refresh view", exact: true }).waitFor();
    for (const { resource, report } of reports) {
      requireEvidence(resource.account_id === account.account_id && report.account_id === account.account_id && report.resource_id === resource.resource_id, "report_resource_mismatch");
      requireEvidence(report.usage_buckets.length > 0, "genuine_usage_buckets_absent");
      const selector = await page.evaluate(id => `[data-report-id="${CSS.escape(id)}"]`, report.report_id);
      const section = panel.locator(selector);
      await section.waitFor();
      requireEvidence(await section.count() === 1, "report_not_independently_rendered");
      requireEvidence(await section.locator("[data-usage-bucket]").count() === report.usage_buckets.length, "usage_bucket_set_mismatch");
      for (const bucket of report.usage_buckets) {
        const bucketSelector = await page.evaluate(id => `[data-usage-bucket="${CSS.escape(id)}"]`, bucket.bucket_key);
        const row = section.locator(bucketSelector);
        requireEvidence(await row.count() === 1, "usage_bucket_missing");
        requireEvidence(await row.getByRole("cell", { name: quantity(bucket.quantity), exact: true }).count() === 1, "exact_usage_quantity_mismatch");
        requireEvidence((await row.textContent()).includes(`${bucket.period.start.slice(0, 10)} to ${bucket.period.end.slice(0, 10)} UTC (end exclusive)`), "usage_period_mismatch");
      }
      if (report.currency === null && report.cost_buckets.length === 0) requireEvidence((await section.textContent()).includes("Provider did not report costs"), "counts_only_cost_absence_hidden");
      if (!reload) bucketCount += report.usage_buckets.length;
    }
    if ((financial.funds?.components.length ?? 0) > 0) await panel.getByRole("region", { name: "Available funds and limits", exact: true }).waitFor();
    requireEvidence(!(await panel.textContent()).includes("No usage report for this interval."), "populated_usage_reported_missing");
    checks.usage_dom = "passed";
    return ids;
  }
  for (const account of inventory) {
    const ids = await inspect(account, false);
    if (ids.length === 0) continue;
    await inspect(account, true, ids);
    accountCount += 1;
  }
  if (accountCount === 0) stop("blocked", "retained_ollama_usage_unavailable");
  checks.reload = "passed";
  requireEvidence(mutations === 0, "unexpected_mutation_request");
  status = "passed";
  reason = "real_usage_api_dom_verified";
} catch (error) {
  if (error?.message !== "probe_stopped" && checks.authentication === "passed") { status = "failed"; reason = "usage_probe_boundary_failed"; }
} finally {
  if (page !== undefined) await page.close().catch(() => { status = "failed"; reason = "probe_page_cleanup_failed"; });
  checks.read_only = page === undefined ? "not_run" : mutations === 0 ? "passed" : "failed";
  if (mutations !== 0) { status = "failed"; reason = "unexpected_mutation_request"; }
}
process.stdout.write(JSON.stringify({ record_type: "agentmonitor.m7_usage_probe.v1", status, reason_code: reason, source_revision: sourceRevision, checks, accounts_verified: accountCount, usage_buckets_verified: bucketCount, unsafe_requests: mutations, observed_at: new Date().toISOString() }) + "\n", () => process.exit(status === "passed" ? 0 : status === "failed" ? 1 : 3));
