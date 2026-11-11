"use strict";

// Reads the actual authenticated dashboard. No provider collection, account
// mutation, credentials, screenshots, or financial values in probe output.
const origin = "http://127.0.0.1:43110";
let page;
let status = "blocked";
let reason = "browser_unavailable";
let mutations = 0;
let sourceRevision = null;
let rowsVerified = 0;
const checks = { authentication: "not_run", overview: "not_run", filters: "not_run", navigation: "not_run", responsive: "not_run", read_only: "not_run" };
function stop(outcome, code) { status = outcome; reason = code; throw new Error("probe_stopped"); }
function requireEvidence(condition, code) { if (!condition) stop("failed", code); }
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
  page.setDefaultTimeout(10000);
  page.on("request", request => { if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) mutations += 1; });
  await page.goto(origin, { waitUntil: "domcontentloaded", timeout: 10000 });
  const signIn = page.getByRole("heading", { name: "Sign in", exact: true });
  await signIn.or(page.getByRole("button", { name: "Accounts", exact: true })).first().waitFor();
  if (await signIn.isVisible()) stop("blocked", "authentication_required");
  checks.authentication = "passed";
  const versions = await page.request.get(`${origin}/api/v1/operations/versions`, { headers: { Origin: origin } });
  if (versions.ok()) {
    const value = (await versions.json())?.source_revision?.value;
    if (/^[a-f0-9]{40}$/.test(value ?? "")) sourceRevision = value;
  }
  const quota = page.getByRole("table", { name: "Account quota overview", exact: true });
  await quota.waitFor();
  const financial = page.getByRole("region", { name: "API usage & spend", exact: true });
  requireEvidence(await financial.count() === 1, "financial_overview_missing");
  await financial.getByRole("button", { name: "Refresh view", exact: true }).waitFor();
  requireEvidence(await page.getByRole("combobox", { name: "Resources", exact: true }).count() === 1, "resource_filter_missing");
  async function read(path) {
    const response = await page.request.get(`${origin}${path}`, { headers: { Origin: origin }, timeout: 10000 });
    if (response.status() === 401) stop("blocked", "authentication_required");
    requireEvidence(response.ok(), "overview_api_unavailable");
    return response.json();
  }
  async function allPages(path, base, identity) {
    let cursor;
    const items = [], seen = new Set(), cursors = new Set();
    let first;
    for (let index = 0; index < 100; index += 1) {
      const query = new URLSearchParams(base);
      query.set("limit", "200");
      if (cursor !== undefined) query.set("cursor", cursor);
      const result = await read(`${path}?${query}`);
      requireEvidence(Array.isArray(result.items) && typeof result.page?.has_more === "boolean", "overview_page_invalid");
      if (first === undefined) first = result;
      if (first.registry_revision !== result.registry_revision) stop("blocked", "inventory_changed_during_probe");
      for (const item of result.items) {
        const key = identity(item);
        if (seen.has(key)) stop("blocked", "inventory_changed_during_pagination");
        seen.add(key); items.push(item);
      }
      if (!result.page.has_more) {
        requireEvidence(result.page.next_cursor === null, "terminal_cursor_invalid");
        return { ...first, items };
      }
      cursor = result.page.next_cursor;
      requireEvidence(typeof cursor === "string" && cursor.length > 0 && !cursors.has(cursor), "overview_cursor_invalid");
      cursors.add(cursor);
    }
    stop("blocked", "pagination_bound_exceeded");
  }
  function money(value) {
    const coefficient = BigInt(value.coefficient);
    const digits = (coefficient < 0n ? -coefficient : coefficient).toString().padStart(value.scale + 1, "0");
    return `${coefficient < 0n ? "-" : ""}${value.scale === 0 ? digits : `${digits.slice(0, -value.scale)}.${digits.slice(-value.scale)}`} ${value.currency}`;
  }
  async function selector(attribute, value) { return page.evaluate(({ attribute, value }) => `[${attribute}="${CSS.escape(value)}"]`, { attribute, value }); }
  async function settled() { await page.locator(".financial-overview[aria-busy=false]").waitFor(); }
  async function reconcile() {
    await settled();
    const address = new URL(page.url());
    const query = new URLSearchParams();
    for (const key of ["period_start", "period_end", "as_of", "organization_ids", "include_ungrouped", "provider_key"]) {
      const value = address.searchParams.get(key);
      if (value !== null) query.set(key, value);
    }
    const expected = await allPages("/api/v1/budgets", query, row => row.row_id);
    for (let index = 0; index < 100; index += 1) {
      const more = financial.getByRole("button", { name: "Load more financial rows", exact: true });
      if (await more.count() === 0) break;
      requireEvidence(await more.isEnabled(), "financial_pagination_blocked");
      const response = page.waitForResponse(response => new URL(response.url()).pathname === "/api/v1/budgets" && new URL(response.url()).searchParams.has("cursor"));
      await more.click();
      requireEvidence((await response).status() === 200, "financial_next_page_failed");
      await settled();
      if (index === 99) stop("blocked", "dom_pagination_bound_exceeded");
    }
    requireEvidence(await financial.locator("[data-financial-row]").count() === expected.items.length, "financial_row_set_mismatch");
    for (const row of expected.items) {
      const dom = financial.locator(await selector("data-financial-row", row.row_id));
      requireEvidence(await dom.count() === 1, "financial_row_missing");
      requireEvidence(await dom.getAttribute("data-account-id") === row.account.account_id, "financial_row_account_mismatch");
      requireEvidence((await dom.textContent()).includes(row.state_code.replaceAll("_", " ")), "financial_state_mismatch");
      requireEvidence(await dom.locator("[data-overview-fund]").count() === row.funds.length, "fund_component_set_mismatch");
      for (const fund of row.funds) {
        const node = dom.locator(await selector("data-overview-fund", fund.component_id));
        requireEvidence(await node.count() === 1, "overview_fund_missing");
        if (fund.remaining.value !== null) requireEvidence(await node.getByTitle(money(fund.remaining.value), { exact: true }).count() > 0, "overview_funds_amount_mismatch");
        requireEvidence(await node.locator("time").getAttribute("datetime") === (fund.observed_at ?? fund.collected_at), "overview_funds_time_mismatch");
        requireEvidence((await node.getAttribute("class") ?? "").includes("overview-fund-low") === (fund.is_low === true), "overview_low_flag_mismatch");
      }
      requireEvidence(await dom.locator("[data-overview-report]").count() === row.contexts.length, "overview_context_set_mismatch");
      for (const context of row.contexts) {
        const node = dom.locator(await selector("data-overview-report", context.report_id));
        requireEvidence(await node.count() === 1, "overview_context_missing");
        if (context.spend === null) requireEvidence((await node.textContent()).includes("Spend not reported"), "unreported_spend_hidden");
        else requireEvidence(await node.getByTitle(money(context.spend), { exact: true }).count() === 1, "overview_spend_mismatch");
      }
      if (row.contexts.length === 0) requireEvidence((await dom.textContent()).includes("No spending report"), "missing_report_not_explained");
    }
    if (expected.summary_reason !== null) requireEvidence((await financial.textContent()).includes(`Spend totals unavailable: ${expected.summary_reason.replaceAll("_", " ")}`), "unavailable_totals_hidden");
    const visibleQuotaIds = await quota.locator("tbody tr").evaluateAll(rows => rows.map(row => row.dataset.accountId));
    requireEvidence(visibleQuotaIds.every(id => expected.subscription_account_ids.includes(id)), "api_only_account_in_subscription_table");
    rowsVerified = Math.max(rowsVerified, expected.items.length);
    return expected;
  }
  let expected = await reconcile();
  if (!expected.items.some(row => row.funds.length > 0 || row.contexts.length > 0)) stop("blocked", "real_financial_readings_required");
  checks.overview = "passed";
  const registry = await allPages("/api/v1/accounts", new URLSearchParams(), row => row.account_id);
  const organizations = await allPages("/api/v1/organizations", new URLSearchParams(), row => row.organization_id);
  const provider = page.getByRole("combobox", { name: "Provider", exact: true });
  const resources = page.getByRole("combobox", { name: "Resources", exact: true });
  const orgControls = page.getByRole("group", { name: "Organizations", exact: true });
  requireEvidence(await provider.count() === 1 && await orgControls.count() === 1, "shared_filters_duplicated");
  for (const organization of organizations.items) requireEvidence(await orgControls.getByRole("button", { name: organization.name, exact: true }).count() > 0, "organization_option_omitted");
  for (const key of new Set(registry.items.filter(row => row.lifecycle !== "archived").map(row => row.provider_key))) requireEvidence(await provider.locator(`option[value="${key}"]`).count() === 1, "provider_option_omitted");
  const chosenProvider = expected.items.find(row => row.funds.length > 0 || row.contexts.length > 0).account.provider_key;
  const providerRead = page.waitForResponse(response => new URL(response.url()).pathname === "/api/v1/budgets");
  await provider.selectOption(chosenProvider);
  requireEvidence((await providerRead).status() === 200, "provider_filter_read_failed");
  expected = await reconcile();
  requireEvidence(expected.items.every(row => row.account.provider_key === chosenProvider), "shared_provider_filter_mismatch");
  await resources.selectOption("api");
  requireEvidence(!(await quota.isVisible()) && await financial.isVisible(), "resource_api_filter_mismatch");
  await resources.selectOption("subscriptions");
  requireEvidence(!(await financial.isVisible()), "resource_subscription_filter_mismatch");
  await resources.selectOption("all");
  const organizationId = expected.items.find(row => row.account.organization_id !== null)?.account.organization_id;
  if (organizationId !== undefined) {
    const organization = organizations.items.find(item => item.organization_id === organizationId);
    requireEvidence(organization !== undefined, "financial_organization_lookup_missing");
    const organizationRead = page.waitForResponse(response => new URL(response.url()).pathname === "/api/v1/budgets");
    await orgControls.getByRole("button", { name: organization.name, exact: true }).click();
    requireEvidence((await organizationRead).status() === 200, "organization_filter_read_failed");
    expected = await reconcile();
    requireEvidence(expected.items.every(row => row.account.organization_id === organizationId), "shared_organization_filter_mismatch");
  }
  await resources.selectOption("api");
  checks.filters = "passed";
  const row = expected.items.find(item => item.contexts.length > 0) ?? expected.items.find(item => item.funds.length > 0);
  if (row === undefined) stop("blocked", "filtered_financial_link_unavailable");
  const before = new URL(page.url());
  const dom = financial.locator(await selector("data-financial-row", row.row_id));
  await dom.getByRole("button").first().click();
  await page.waitForURL(url => url.pathname === `/accounts/${encodeURIComponent(row.account.account_id)}`);
  const detail = new URL(page.url());
  requireEvidence(detail.searchParams.get("budget_resource") === row.resource_id, "detail_resource_selector_lost");
  requireEvidence(detail.searchParams.get("budget_report") === (row.contexts[0]?.report_id ?? null), "detail_report_selector_lost");
  requireEvidence(detail.searchParams.get("budget_start") === expected.period.start || Date.parse(detail.searchParams.get("budget_start")) === Date.parse(expected.period.start), "detail_period_lost");
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("region", { name: "API usage & spend", exact: true }).waitFor();
  requireEvidence(new URL(page.url()).search === detail.search, "detail_selectors_lost_on_reload");
  if (row.contexts[0] !== undefined) await page.locator(await selector("data-report-id", row.contexts[0].report_id)).waitFor();
  await page.goBack({ waitUntil: "domcontentloaded" });
  await financial.waitFor();
  requireEvidence(new URL(page.url()).search === before.search, "overview_filters_lost_on_back");
  await page.reload({ waitUntil: "domcontentloaded" });
  await financial.waitFor();
  await reconcile();
  requireEvidence(new URL(page.url()).search === before.search && await resources.inputValue() === "api" && await provider.inputValue() === chosenProvider, "overview_filters_lost_on_reload");
  checks.navigation = "passed";
  for (const viewport of [{ width: 1920, height: 1080 }, { width: 1366, height: 768 }, { width: 768, height: 1024 }]) {
    await page.setViewportSize(viewport);
    requireEvidence(await resources.isVisible() && await provider.isVisible(), "overview_filters_hidden");
    requireEvidence(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), "overview_horizontal_overflow");
  }
  checks.responsive = "passed";
  requireEvidence(mutations === 0, "unexpected_mutation_request");
  status = "passed";
  reason = "real_overview_api_dom_navigation_verified";
} catch (error) {
  if (error?.message !== "probe_stopped" && checks.authentication === "passed") { status = "failed"; reason = "overview_probe_boundary_failed"; }
} finally {
  if (page !== undefined) await page.close().catch(() => { status = "failed"; reason = "probe_page_cleanup_failed"; });
  checks.read_only = page === undefined ? "not_run" : mutations === 0 ? "passed" : "failed";
  if (mutations !== 0) { status = "failed"; reason = "unexpected_mutation_request"; }
}
process.stdout.write(JSON.stringify({ record_type: "agentmonitor.m7_overview_probe.v1", status, reason_code: reason, source_revision: sourceRevision, checks, rows_verified: rowsVerified, unsafe_requests: mutations, observed_at: new Date().toISOString() }) + "\n", () => process.exit(status === "passed" ? 0 : status === "failed" ? 1 : 3));
