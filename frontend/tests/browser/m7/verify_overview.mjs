"use strict";

// Reads the actual authenticated dashboard. No provider collection, account
// mutation, credentials, screenshots, or financial values in probe output.
const origin = "http://127.0.0.1:43110";
const requireMoney = process.argv.includes("--require-money");
let page;
let status = "blocked";
let reason = "browser_unavailable";
let mutations = 0;
let sourceRevision = null;
let rowsVerified = 0;
let stage = "overview";
let errorKind = null;
let errorLine = null;
let errorClass = null;
let failureDom = null;
let periodOnlyDiagnostic = null;
const accountReadResponses = [];
const directReadDiagnostics = [];
const navigationReads = [];
const failedNavigationReads = [];
let registryReadRequests = 0;
let rowSetDiagnostic = null;
let entryDiagnostic = null;
let availabilityDiagnostic = null;
const overviewResponseStatuses = [];
const uiOverviewResponses = [];
const availabilityStates = new Set(["available", "partial", "unavailable", "stale", "unsupported", "unknown"]);
const safeReasonCode = value => typeof value === "string" && /^[a-z][a-z0-9_]{0,127}$/.test(value) ? value : null;
function matchesSelectedOverview(requestUrl, selectedUrl) {
  try {
    const request = new URL(requestUrl).searchParams, selected = new URL(selectedUrl).searchParams;
    const utc = value => typeof value === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$/.test(value)
      ? value.replace(/(?:\.(\d{1,6}))?Z$/, (_, fraction) => `.${(fraction ?? "").padEnd(6, "0")}Z`) : null;
    for (const key of ["period_start", "period_end", "as_of"]) {
      if (utc(request.get(key)) === null || utc(request.get(key)) !== utc(selected.get(key))) return false;
    }
    const organizations = value => value === null ? null : value.split(",").sort().join(",");
    const [sortBy, sortDirection] = (selected.get("financial_sort") ?? "state:ascending").split(":");
    return organizations(request.get("organization_ids")) === organizations(selected.get("organization_ids"))
      && request.get("provider_key") === selected.get("provider_key")
      && (request.get("include_ungrouped") !== "false") === (selected.get("organization_ids") === null || selected.get("include_ungrouped") !== "false")
      && (request.get("sort_by") ?? "state") === sortBy
      && (request.get("sort_direction") ?? "ascending") === sortDirection;
  } catch { return false; }
}
const renderedReadPaths = [];
const checks = { monetary: "not_run", authentication: "not_run", overview: "not_run", filters: "not_run", navigation: "not_run", financial_entry: "not_run", source_history: "not_run", balance_history: "not_run", history_windows: "not_run", responsive: "not_run", pool_controls: "not_run", read_only: "not_run" };
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
  page.on("requestfailed", request => {
    const path = new URL(request.url()).pathname;
    const kind = path === "/api/v1/accounts" ? "accounts" : path === "/api/v1/organizations" ? "organizations" : /^\/api\/v1\/accounts\/[^/]+$/.test(path) ? "account_detail" : null;
    if (kind !== null && failedNavigationReads.length < 100) failedNavigationReads.push({kind, aborted: request.failure()?.errorText === "net::ERR_ABORTED"});
  });
  page.on("response", async response => {
    const url = new URL(response.url());
    if (url.origin !== origin) return;
    let kind = url.pathname === "/api/v1/accounts" ? "accounts" : url.pathname === "/api/v1/organizations" ? "organizations" : /^\/api\/v1\/accounts\/[^/]+$/.test(url.pathname) ? "account_detail" : url.pathname.includes("session") ? "session" : null;
    if (kind !== null && navigationReads.length < 100) navigationReads.push({kind, status: response.status()});
    if (!/^\/api\/v1\/accounts\/[^/]+\/budgets$/.test(url.pathname)) return;
    const item = {status: response.status(), availability: null, reason_code: null};
    accountReadResponses.push(item);
    try { const body = await response.json(); item.availability = availabilityStates.has(body?.availability?.state) ? body.availability.state : null; item.reason_code = safeReasonCode(body?.availability?.reason_code); } catch {}
  });
  page.on("response", response => {
    if (new URL(response.url()).pathname !== "/api/v1/budgets") return;
    overviewResponseStatuses.push(response.status());
    const diagnostic = { http_status: response.status(), body_state: "pending", availability: null, reason_code: null, rows: null, query_matches_selected: matchesSelectedOverview(response.url(), page.url()) };
    uiOverviewResponses.push(diagnostic);
    if (uiOverviewResponses.length > 40) uiOverviewResponses.shift();
    // Inspect the already-issued UI response; no extra request or render wait.
    void response.json().then(body => {
      diagnostic.body_state = "read";
      diagnostic.availability = availabilityStates.has(body?.availability?.state) ? body.availability.state : null;
      diagnostic.reason_code = safeReasonCode(body?.availability?.reason_code);
      diagnostic.rows = Array.isArray(body?.items) ? body.items.length : null;
      diagnostic.query_matches_selected = matchesSelectedOverview(response.url(), page.url());
    }).catch(() => { diagnostic.body_state = "unreadable"; });
  });
  page.on("request", request => {
    if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) mutations += 1;
    if (request.method() === "GET") {
      const path = new URL(request.url()).pathname;
      renderedReadPaths.push(path);
      if (path === "/api/v1/accounts" || path === "/api/v1/organizations" || /^\/api\/v1\/accounts\/[^/]+$/.test(path)) registryReadRequests += 1;
    }
  });
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
  stage = "quota_table";
  await quota.waitFor();
  const financial = page.getByRole("region", { name: "API usage & spend", exact: true });
  requireEvidence(await financial.count() === 1, "financial_overview_missing");
  stage = "financial_refresh_control";
  await financial.getByRole("button", { name: "Refresh view", exact: true }).waitFor();
  requireEvidence(await page.getByRole("combobox", { name: "Resources", exact: true }).count() === 1, "resource_filter_missing");
  async function read(path) {
    const pathname = new URL(path, origin).pathname;
    const family = pathname.endsWith("/forecast") ? "forecast" : pathname.endsWith("/history") ? "report_history"
      : pathname.endsWith("/reports") ? "report_discovery" : pathname.startsWith("/api/v1/budgets/") ? "selected_report"
      : pathname === "/api/v1/budgets" ? "overview" : pathname.endsWith("/accounts") ? "accounts"
      : pathname.endsWith("/organizations") ? "organizations" : "other";
    const started = Date.now();
    let response;
    try { response = await page.request.get(`${origin}${path}`, { headers: { Origin: origin }, timeout: 10000 }); }
    catch (error) { directReadDiagnostics.push({family, status: null, elapsed_ms: Date.now() - started, timeout: error?.name === "TimeoutError"}); throw error; }
    const record = { family, status: response.status(), elapsed_ms: Date.now() - started, reason: null };
    directReadDiagnostics.push(record);
    if (directReadDiagnostics.length > 100) directReadDiagnostics.shift();
    if (!response.ok()) {
      try { const body = await response.json(); record.reason = safeReasonCode(body.code ?? body.reason_code ?? body.availability?.reason_code); } catch {}
    }
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
      if (!["available", ...(path === "/api/v1/budgets" ? ["partial"] : [])].includes(result.availability?.state)) {
        const safeCode = value => typeof value === "string" && /^[a-z0-9_]{1,128}$/.test(value) ? value : "unclassified";
        availabilityDiagnostic = { path, state: safeCode(result.availability?.state), reason_code: safeCode(result.availability?.reason_code) };
        stop("blocked", "comparison_source_unavailable");
      }
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
  const quantity = value => money({ ...value, currency: value.unit });
  const periodText = period => `${period.start.slice(0, 10)} to ${period.end.slice(0, 10)} UTC (end exclusive)`;
  function microseconds(value) {
    const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?Z$/.exec(value ?? "");
    requireEvidence(match !== null, "timestamp_invalid");
    return BigInt(Date.parse(match[1] + "Z")) * 1000n + BigInt((match[2] ?? "").padEnd(6, "0"));
  }
  async function selector(attribute, value) { return page.evaluate(({ attribute, value }) => `[${attribute}="${CSS.escape(value)}"]`, { attribute, value }); }
  async function settled() { await page.locator(".financial-overview[aria-busy=false]").waitFor(); }
  async function reconcile() {
    stage = "financial_settle";
    await settled();
    stage = "financial_reconcile";
    const address = new URL(page.url());
    const query = new URLSearchParams();
    for (const key of ["period_start", "period_end", "as_of", "organization_ids", "include_ungrouped", "provider_key"]) {
      const value = address.searchParams.get(key);
      if (value !== null) query.set(key, value);
    }
    const [sortBy, sortDirection] = (address.searchParams.get("financial_sort") ?? "state:ascending").split(":");
    query.set("sort_by", sortBy);
    query.set("sort_direction", sortDirection);
    const expected = await allPages("/api/v1/budgets", query, row => row.row_id);
    requireEvidence(microseconds(expected.as_of) === microseconds(query.get("as_of")), "overview_cutoff_mismatch");
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
    const actualRowIds = await financial.locator("[data-financial-row]").evaluateAll(rows => rows.map(row => row.getAttribute("data-financial-row")));
    if (actualRowIds.length !== expected.items.length) rowSetDiagnostic = {
      expected_rows: expected.items.length, rendered_rows: actualRowIds.length,
      refresh_error_visible: await financial.getByRole("alert").isVisible(),
      overview_response_statuses: overviewResponseStatuses,
    };
    requireEvidence(actualRowIds.length === expected.items.length, "financial_row_set_mismatch");
    requireEvidence(actualRowIds.every((id, index) => id === expected.items[index].row_id), "financial_server_order_mismatch");
    for (const row of expected.items) {
      const dom = financial.locator(await selector("data-financial-row", row.row_id));
      requireEvidence(await dom.count() === 1, "financial_row_missing");
      requireEvidence(await dom.getAttribute("data-account-id") === row.account.account_id, "financial_row_account_mismatch");
      requireEvidence(await dom.getAttribute("data-resource-id") === row.resource_id, "financial_row_resource_mismatch");
      requireEvidence((await dom.textContent()).includes(row.state_code.replaceAll("_", " ")), "financial_state_mismatch");
      requireEvidence(await dom.locator("[data-overview-fund]").count() === row.funds.length, "fund_component_set_mismatch");
      for (const fund of row.funds) {
        const node = dom.locator(await selector("data-overview-fund", fund.component_id));
        requireEvidence(await node.count() === 1, "overview_fund_missing");
        if (fund.remaining.value !== null) requireEvidence(await node.locator(":scope > span[title]").getAttribute("title") === money(fund.remaining.value), "overview_funds_amount_mismatch");
        if (fund.limit.value !== null) requireEvidence(await node.locator(":scope > small > span[title]").getAttribute("title") === money(fund.limit.value), "overview_funds_limit_mismatch");
        const labels = { balance: "Balance", included_credits: "Included credits", purchased_credits: "Purchased credits", soft_limit: "Soft budget", hard_limit: "Hard limit" };
        requireEvidence((await node.locator(":scope > strong").textContent()).trim() === `${labels[fund.kind]}:`, "overview_funds_kind_mismatch");
        if (fund.percentage_text !== null) requireEvidence(await node.getByText(`${fund.percentage_text}% remaining${fund.is_low === true ? " · Low" : ""}`, { exact: true }).count() === 1, "overview_percentage_mismatch");
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
      for (const [index, context] of row.contexts.entries()) {
        const times = dom.locator('td[data-label="Data through"] > div').nth(index);
        const collected = times.locator("small time");
        requireEvidence(await collected.getAttribute("datetime") === context.collected_at, "overview_collected_time_mismatch");
        if (context.source_data_through === null) requireEvidence((await times.locator(":scope > span").textContent()) === "Not reported", "overview_watermark_absence_hidden");
        else requireEvidence(await times.locator(":scope > span time").getAttribute("datetime") === context.source_data_through, "overview_watermark_mismatch");
      }
      if (row.contexts.length === 0) requireEvidence((await dom.textContent()).includes("No spending report"), "missing_report_not_explained");
    }
    if (expected.summary_reason !== null) requireEvidence((await financial.textContent()).includes(`${expected.summaries.length ? "Spend subtotals are partial" : "Spend totals unavailable"}: ${expected.summary_reason.replaceAll("_", " ")}`), "unavailable_totals_hidden");
    const summary = financial.locator('[aria-label="Reported spend summaries"]');
    for (const [index, item] of expected.summaries.entries()) {
      const line = summary.locator("p").nth(index);
      requireEvidence(await line.getByTitle(money(item.total), { exact: true }).count() === 1 && (await line.textContent()).includes(`${item.included_pool_count} included pools · ${item.excluded_resource_count} excluded resources`), "overview_summary_mismatch");
    }
    for (const item of expected.exclusions) requireEvidence(await summary.getByText(`${item.count} excluded: ${item.reason_code.replaceAll("_", " ")}.`, { exact: true }).count() === 1, "overview_exclusion_mismatch");
    const visibleQuotaIds = await page.getByRole("table", { name: "Account quota overview", exact: true, includeHidden: true }).locator("tbody tr").evaluateAll(rows => rows.map(row => row.dataset.accountId));
    requireEvidence(visibleQuotaIds.every(id => expected.subscription_account_ids.includes(id)), "api_only_account_in_subscription_table");
    if (expected.subscription_account_ids.length > 0) requireEvidence(visibleQuotaIds.length > 0, "working_subscription_rows_missing");
    rowsVerified = Math.max(rowsVerified, expected.items.length);
    return expected;
  }
  const monetaryContext = row => row.contexts.find(context => context.spend !== null && context.currency !== null && context.completeness === "complete");
  let expected = await reconcile();
  const monetaryRow = expected.items.find(row => monetaryContext(row) !== undefined);
  if (requireMoney && monetaryRow === undefined) stop("blocked", "genuine_complete_monetary_report_required");
  const allFinancialRows = expected.items;
  if (!expected.items.some(row => row.funds.length > 0 || row.contexts.length > 0)) stop("blocked", "real_financial_readings_required");
  checks.overview = "passed";
  const quotaSort = quota.getByRole("columnheader", { name: "Quota left", exact: true });
  await quotaSort.getByRole("button", { name: "Quota left", exact: true }).click();
  requireEvidence(await quotaSort.getAttribute("aria-sort") === "descending" && new URL(page.url()).searchParams.get("quota_sort") === "quota:descending", "quota_sort_not_retained_in_url");
  const registry = await allPages("/api/v1/accounts", new URLSearchParams(), row => row.account_id);
  const organizations = await allPages("/api/v1/organizations", new URLSearchParams(), row => row.organization_id);
  const provider = page.getByRole("combobox", { name: "Provider", exact: true });
  const resources = page.getByRole("combobox", { name: "Resources", exact: true });
  const orgControls = page.getByRole("group", { name: "Organizations", exact: true });
  requireEvidence(await provider.count() === 1 && await orgControls.count() === 1, "shared_filters_duplicated");
  for (const organization of organizations.items) requireEvidence(await orgControls.getByRole("button", { name: organization.name, exact: true }).count() > 0, "organization_option_omitted");
  for (const key of new Set(registry.items.filter(row => row.lifecycle !== "archived").map(row => row.provider_key))) requireEvidence(await provider.locator(`option[value="${key}"]`).count() === 1, "provider_option_omitted");
  const chosenProvider = (requireMoney ? monetaryRow : expected.items.find(row => row.funds.length > 0 || row.contexts.length > 0)).account.provider_key;
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
  const organizationId = requireMoney ? monetaryRow.primary_organization_id ?? monetaryRow.account.organization_id ?? undefined : expected.items.find(row => row.account.organization_id !== null)?.account.organization_id;
  if (organizationId !== undefined) {
    const organization = organizations.items.find(item => item.organization_id === organizationId);
    requireEvidence(organization !== undefined, "financial_organization_lookup_missing");
    const organizationRead = page.waitForResponse(response => new URL(response.url()).pathname === "/api/v1/budgets");
    await orgControls.getByRole("button", { name: organization.name, exact: true }).click();
    requireEvidence((await organizationRead).status() === 200, "organization_filter_read_failed");
    expected = await reconcile();
    requireEvidence(expected.items.every(row => row.account.organization_id === organizationId || row.primary_organization_id === organizationId || row.access_paths?.some(path => path.account.organization_id === organizationId)), "shared_organization_filter_mismatch");
  }
  await resources.selectOption("api");
  checks.filters = "passed";
  const mixedRows = expected.items.filter(item => registry.items.some(account => account.account_id === (item.contexts[0]?.report_account_id ?? item.account.account_id) && account.initial_connection_purpose !== "api"));
  const row = requireMoney ? expected.items.find(item => item.row_id === monetaryRow.row_id && monetaryContext(item) !== undefined)
    : mixedRows.find(item => item.contexts.length > 0) ?? mixedRows.find(item => item.funds.length > 0);
  if (row === undefined) stop("blocked", requireMoney ? "monetary_selection_unavailable" : "mixed_financial_account_required");
  const selectedContext = requireMoney ? monetaryContext(row) : row.contexts[0];
  const before = new URL(page.url());
  const dom = financial.locator(await selector("data-financial-row", row.row_id));
  const reportAccount = selectedContext?.report_account_id ?? row.account.account_id;
  const reportResource = selectedContext?.report_resource_id ?? row.resource_id;
  if (requireMoney) await dom.locator(await selector("data-overview-report", selectedContext.report_id)).getByRole("button", { name: "View report", exact: true }).click();
  else await dom.getByRole("button").first().click();
  await page.waitForURL(url => url.pathname === `/accounts/${encodeURIComponent(reportAccount)}`);
  const detail = new URL(page.url());
  requireEvidence(detail.searchParams.get("budget_resource") === reportResource, "detail_resource_selector_lost");
  requireEvidence(detail.searchParams.get("budget_report") === (selectedContext?.report_id ?? null), "detail_report_selector_lost");
  requireEvidence(microseconds(detail.searchParams.get("budget_start")) === microseconds(expected.period.start) && microseconds(detail.searchParams.get("budget_end")) === microseconds(expected.period.end), "detail_period_lost");
  requireEvidence(microseconds(detail.searchParams.get("budget_as_of")) === microseconds(expected.as_of), "detail_cutoff_lost");
  async function financialEntry() {
    await page.getByRole("heading", { name: "API usage & spend", exact: true }).waitFor();
    try { await page.waitForFunction(() => document.activeElement?.id === "budget-account-title", undefined, { timeout: 3000 }); }
    catch { stop("failed", "financial_entry_focus_missing"); }
    entryDiagnostic = await page.evaluate(() => {
      const heading = document.getElementById("budget-account-title");
      const activity = document.getElementById("account-activity-title");
      const quota = document.getElementById("quota-title");
      const box = heading.getBoundingClientRect();
      return { top: box.top, bottom: box.bottom, height: innerHeight,
        activity_present: activity !== null, quota_present: quota !== null,
        before_activity: activity !== null && Boolean(heading.compareDocumentPosition(activity) & Node.DOCUMENT_POSITION_FOLLOWING),
        before_quota: quota !== null && Boolean(heading.compareDocumentPosition(quota) & Node.DOCUMENT_POSITION_FOLLOWING) };
    });
    // scrollIntoView rounds to device pixels; allow the same one-CSS-pixel
    // tolerance used by the overflow checks, without relaxing focus/order.
    requireEvidence(entryDiagnostic.top >= -1 && entryDiagnostic.bottom <= entryDiagnostic.height + 1 && (requireMoney ? (!entryDiagnostic.activity_present || entryDiagnostic.before_activity) && (!entryDiagnostic.quota_present || entryDiagnostic.before_quota) : entryDiagnostic.before_activity && entryDiagnostic.before_quota), "financial_entry_not_visible_before_subscription");
  }
  stage = "financial_entry";
  await financialEntry();
  const selectedHadQuota = entryDiagnostic.quota_present;
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("region", { name: "API usage & spend", exact: true }).waitFor();
  await financialEntry();
  requireEvidence(!selectedHadQuota || entryDiagnostic.quota_present, "quota_section_lost_on_reload");
  requireEvidence(new URL(page.url()).search === detail.search, "detail_selectors_lost_on_reload");
  if (selectedContext !== undefined) {
    const context = selectedContext;
    const query = new URLSearchParams({ account_id: reportAccount, report_id: context.report_id, period_start: detail.searchParams.get("budget_start"), period_end: detail.searchParams.get("budget_end"), as_of: detail.searchParams.get("budget_as_of") });
    const selected = await read(`/api/v1/budgets/${encodeURIComponent(reportResource)}?${query}`);
    requireEvidence(selected.report.report_id === context.report_id && selected.report.account_id === reportAccount && selected.report.resource_id === reportResource && microseconds(selected.as_of) === microseconds(expected.as_of), "selected_report_context_mismatch");
    requireEvidence(JSON.stringify(selected.reported_spend.total) === JSON.stringify(context.spend), "overview_detail_spend_mismatch");
    if (requireMoney) {
      const report = selected.report;
      requireEvidence(report.cost_buckets.length > 0 && report.completeness === "complete" && report.grouping.length === 0 && report.currency !== null, "monetary_source_context_invalid");
      for (const key of ["scope_id", "scope_generation", "scope_evidence", "source_id", "source_category", "cost_basis", "currency", "source_data_through", "collected_at"]) requireEvidence(report[key] === context[key], "monetary_source_identity_mismatch");
      for (const period of [report.requested_period, report.covered_period]) requireEvidence(period !== null && microseconds(period.start) === microseconds(expected.period.start) && microseconds(period.end) === microseconds(expected.period.end), "monetary_coverage_mismatch");
      const atoms = value => {
        requireEvidence(value !== null && value.currency === report.currency && Number.isInteger(value.scale) && value.scale >= 0 && value.scale <= 18 && /^-?\d+$/.test(value.coefficient), "monetary_value_invalid");
        return BigInt(value.coefficient) * 10n ** BigInt(18 - value.scale);
      };
      // Test-local exact integer arithmetic, independent of the application's
      // aggregation and formatting helpers. Usage and balance never contribute.
      const total = report.cost_buckets.reduce((sum, bucket) => sum + atoms(bucket.amount), 0n);
      requireEvidence(total === atoms(context.spend) && total === atoms(selected.reported_spend.total), "monetary_bucket_sum_mismatch");
    }
    const section = page.locator(await selector("data-report-id", context.report_id));
    await section.waitFor();
    await section.locator('[data-budget-history][aria-busy="false"]').waitFor();
    if (context.spend !== null) requireEvidence(await section.getByTitle(money(context.spend), { exact: true }).count() > 0, "detail_spend_mismatch");
    else {
      const countsOnly = selected.report.currency === null && selected.report.cost_buckets.length === 0 && selected.report.usage_buckets.length > 0;
      requireEvidence((await section.textContent()).includes(countsOnly ? "Provider did not report costs." : selected.reported_spend.reason_code.replaceAll("_", " ")), "detail_spend_absence_hidden");
    }
    const summaryPath = `/api/v1/accounts/${encodeURIComponent(reportAccount)}/budgets`;
    const summaryQuery = new URLSearchParams(query);
    summaryQuery.delete("account_id"); summaryQuery.delete("report_id");
    const compactResponse = await page.request.get(`${origin}${summaryPath}?${summaryQuery}`, { headers: { Origin: origin } });
    requireEvidence(compactResponse.ok(), "compact_budget_summary_missing");
    const compact = await compactResponse.json();
    for (const resource of [...compact.resources, ...compact.cloud_resources]) {
      for (const selection of resource.reports) {
        for (const report of [selection.current, selection.latest_attempt].filter(Boolean)) {
          requireEvidence(!("cost_buckets" in report) && !("usage_buckets" in report) && Number.isInteger(report.cost_bucket_count) && Number.isInteger(report.usage_bucket_count), "summary_embeds_history_facts");
        }
      }
    }
    stage = "source_history";
    const sourceHistory = page.locator(await selector("data-source-history", reportResource));
    requireEvidence(await sourceHistory.count() === 1, "source_history_disclosure_missing");
    const sourcePath = `/api/v1/budgets/${encodeURIComponent(reportResource)}/reports`;
    const sourceQuery = new URLSearchParams(query);
    sourceQuery.delete("report_id"); sourceQuery.set("limit", "50");
    const sourcePage = await read(`${sourcePath}?${sourceQuery}`);
    requireEvidence(sourcePage.account_id === reportAccount && sourcePage.resource_id === reportResource && microseconds(sourcePage.as_of) === microseconds(selected.as_of), "source_history_context_mismatch");
    const sourceResponse = page.waitForResponse(response => new URL(response.url()).pathname === sourcePath);
    await sourceHistory.getByText("Source history", { exact: true }).click();
    requireEvidence((await sourceResponse).status() === 200, "source_history_read_failed");
    await sourceHistory.locator('[data-source-history-content][aria-busy="false"]').waitFor();
    const sourceRows = sourceHistory.locator("[data-source-report]");
    requireEvidence(JSON.stringify(await sourceRows.evaluateAll(nodes => nodes.map(node => node.getAttribute("data-source-report")))) === JSON.stringify(sourcePage.items.map(item => item.report_id)), "source_history_rows_mismatch");
    for (const report of sourcePage.items) {
      const entry = sourceHistory.locator(await selector("data-source-report", report.report_id));
      const text = await entry.textContent();
      requireEvidence(text.includes(report.scope_id ?? "Not established") && text.includes(`Scope generation ${report.scope_generation}`), "source_history_scope_mismatch");
      const link = new URL(await entry.getByRole("link", { name: "View report", exact: true }).getAttribute("href"), origin);
      requireEvidence(link.searchParams.get("budget_report") === report.report_id && link.searchParams.get("budget_resource") === reportResource && microseconds(link.searchParams.get("budget_as_of")) === microseconds(selected.as_of), "source_history_selection_mismatch");
    }
    checks.source_history = "passed";
    stage = "financial_entry";
    const historyPath = `/api/v1/budgets/${encodeURIComponent(reportResource)}/history`;
    const history = section.locator("[data-budget-history]");
    await history.waitFor();
    await section.locator('[data-budget-history][aria-busy="false"]').waitFor();
    for (let index = 0; index < 200; index += 1) {
      const more = history.getByRole("button", { name: "Load more history", exact: true });
      if (await more.count() === 0) break;
      requireEvidence(await more.isEnabled(), "history_continuation_disabled");
      const response = page.waitForResponse(response => new URL(response.url()).pathname === historyPath && new URL(response.url()).searchParams.has("cursor"));
      await more.click();
      requireEvidence((await response).status() === 200, "history_continuation_failed");
      await section.locator('[data-budget-history][aria-busy="false"]').waitFor();
      if (index === 199) stop("blocked", "history_pagination_bound_exceeded");
    }
    requireEvidence(renderedReadPaths.includes(summaryPath) && renderedReadPaths.includes(historyPath), "ui_not_using_compact_history_reads");
    requireEvidence(!renderedReadPaths.includes(`/api/v1/accounts/${encodeURIComponent(reportAccount)}/api-capacity`) && !renderedReadPaths.includes(`/api/v1/budgets/${encodeURIComponent(reportResource)}`), "ui_requested_unbounded_report");
    const paged = [];
    let cursor;
    const seenCursors = new Set();
    for (let index = 0; index < 10000; index += 1) {
      const continuation = new URLSearchParams(query);
      continuation.set("limit", "1");
      if (cursor !== undefined) continuation.set("cursor", cursor);
      const batch = await read(`${historyPath}?${continuation}`);
      requireEvidence(batch.report.report_id === selected.report.report_id && batch.report.account_id === reportAccount && batch.report.resource_id === reportResource && microseconds(batch.as_of) === microseconds(selected.as_of), "history_page_context_mismatch");
      requireEvidence(!("cost_buckets" in batch.report) && !("usage_buckets" in batch.report) && batch.items.length <= 1, "history_page_not_bounded");
      requireEvidence(JSON.stringify(batch.reported_spend) === JSON.stringify(selected.reported_spend), "history_spend_mismatch");
      paged.push(...batch.items);
      if (!batch.page.has_more) { requireEvidence(batch.page.next_cursor === null, "history_terminal_cursor_invalid"); break; }
      cursor = batch.page.next_cursor;
      requireEvidence(typeof cursor === "string" && !seenCursors.has(cursor), "history_cursor_invalid");
      seenCursors.add(cursor);
      if (index === 9999) stop("blocked", "history_page_bound_exceeded");
    }
    const expectedFacts = [
      ...selected.report.cost_buckets.map(cost => ({ kind: "cost", cost, usage: null })),
      ...selected.report.usage_buckets.map(usage => ({ kind: "usage", cost: null, usage })),
    ];
    const factKey = row => `${row.kind}:${(row.cost ?? row.usage).bucket_key}`;
    requireEvidence(paged.length === expectedFacts.length && new Set(paged.map(factKey)).size === expectedFacts.length, "history_fact_count_mismatch");
    for (const fact of expectedFacts) {
      const row = paged.find(row => factKey(row) === factKey(fact));
      requireEvidence(row !== undefined && JSON.stringify({ kind: row.kind, cost: row.cost, usage: row.usage }) === JSON.stringify(fact), "history_exact_fact_mismatch");
    }
    for (const [key, buckets] of [["cost", selected.report.cost_buckets], ["usage", selected.report.usage_buckets]]) {
      const table = history.getByRole("region", { name: key === "cost" ? "Exact cost history" : "Exact usage history", exact: true });
      requireEvidence(await table.locator("tbody tr").count() === buckets.length, "selected_bucket_set_mismatch");
      for (const bucket of buckets) {
        const rowSelector = await selector("data-bucket-key", bucket.bucket_key);
        const cells = table.locator(rowSelector).getByRole("cell");
        requireEvidence(await cells.nth(0).textContent() === periodText(bucket.period) && await cells.nth(1).textContent() === (key === "cost" ? money(bucket.amount) : quantity(bucket.quantity)), "selected_exact_bucket_mismatch");
      }
    }
  }
  if (requireMoney) checks.monetary = "passed";
  const accountBudget = page.getByRole("region", { name: "API usage & spend", exact: true });
  stage = "retained_refresh";
  const retainedPanel = await accountBudget.elementHandle();
  const refreshResponse = page.waitForResponse(response => new URL(response.url()).pathname === `/api/v1/accounts/${encodeURIComponent(reportAccount)}/budgets`);
  await accountBudget.getByRole("button", { name: "Refresh view", exact: true }).click();
  requireEvidence((await refreshResponse).ok(), "initial_refresh_request_failed");
  requireEvidence(await retainedPanel.evaluate(node => node.isConnected), "same_context_refresh_remounted_panel");
  requireEvidence(await page.evaluate(() => document.activeElement?.id !== "budget-account-title"), "financial_refresh_stole_focus");
  requireEvidence(await accountBudget.getByRole("group", { name: "Stored history windows", exact: true }).count() === 1, "stored_window_controls_missing");
  const windowMarker = accountBudget.locator("[data-budget-window]");
  const DAY = 86400000;
  async function windowState() {
    await page.waitForFunction(() => document.querySelector('[aria-labelledby="budget-account-title"]')?.getAttribute("aria-busy") === "false");
    return { start: await windowMarker.getAttribute("data-period-start"), end: await windowMarker.getAttribute("data-period-end"), asOf: await windowMarker.getAttribute("data-read-as-of") };
  }
  function sameWindow(actual, wanted, code) {
    requireEvidence(microseconds(actual.start) === microseconds(wanted.start) && microseconds(actual.end) === microseconds(wanted.end) && microseconds(actual.asOf) === microseconds(wanted.asOf), code);
  }
  async function changeWindow(action) {
    const response = page.waitForResponse(response => {
      const request = new URL(response.url()), selected = new URL(page.url());
      return request.pathname === `/api/v1/accounts/${encodeURIComponent(reportAccount)}/budgets` &&
        [["period_start", "budget_start"], ["period_end", "budget_end"], ["as_of", "budget_as_of"]].every(([wire, url]) =>
          request.searchParams.get(wire) !== null && selected.searchParams.get(url) !== null &&
          microseconds(request.searchParams.get(wire)) === microseconds(selected.searchParams.get(url)));
    });
    await action();
    const result = await response;
    requireEvidence(result.ok(), "window_summary_request_failed");
    const summary = await result.json();
    const current = await windowState();
    sameWindow(current, { start: summary.period.start, end: summary.period.end, asOf: summary.as_of }, "window_dom_api_mismatch");
    const url = new URL(page.url());
    requireEvidence(url.searchParams.get("budget_report") === null && url.searchParams.get("budget_resource") === reportResource, "window_selection_not_reset");
    sameWindow(current, { start: url.searchParams.get("budget_start"), end: url.searchParams.get("budget_end"), asOf: url.searchParams.get("budget_as_of") }, "window_url_mismatch");
    requireEvidence(await accountBudget.getByRole("alert").count() === 0, "window_read_error");
    return current;
  }
  stage = "initial_window";
  const initialWindow = await windowState();
  const registryReadsBeforeWindows = registryReadRequests;
  const initialDays = (Date.parse(initialWindow.end) - Date.parse(initialWindow.start)) / DAY;
  stage = "previous_window";
  const priorWindow = await changeWindow(() => accountBudget.getByRole("button", { name: "Previous window", exact: true }).click());
  requireEvidence(registryReadRequests === registryReadsBeforeWindows, "window_change_reloaded_account_registry");
  sameWindow(priorWindow, { start: new Date(Date.parse(initialWindow.start) - initialDays * DAY).toISOString(), end: initialWindow.start, asOf: initialWindow.asOf }, "previous_window_mismatch");
  await page.reload({ waitUntil: "domcontentloaded" });
  await windowMarker.waitFor();
  sameWindow(await windowState(), priorWindow, "previous_window_lost_on_reload");
  stage = "refresh_window";
  const refreshedWindow = await changeWindow(() => accountBudget.getByRole("button", { name: "Refresh view", exact: true }).click());
  requireEvidence(microseconds(refreshedWindow.asOf) > microseconds(priorWindow.asOf), "refresh_did_not_advance_read_snapshot");
  sameWindow(refreshedWindow, { ...priorWindow, asOf: refreshedWindow.asOf }, "refresh_changed_interval");
  stage = "next_window";
  const nextWindow = await changeWindow(() => accountBudget.getByRole("button", { name: "Next window", exact: true }).click());
  sameWindow(nextWindow, { ...initialWindow, asOf: refreshedWindow.asOf }, "next_window_mismatch");
  requireEvidence(await accountBudget.getByRole("button", { name: "Next window", exact: true }).isDisabled(), "next_crosses_completed_cutoff");
  stage = "wide_window";
  const wideWindow = await changeWindow(() => accountBudget.getByLabel("Report range", { exact: true }).selectOption("30"));
  sameWindow(wideWindow, { start: new Date(Date.parse(nextWindow.end) - 30 * DAY).toISOString(), end: nextWindow.end, asOf: nextWindow.asOf }, "resize_changed_cutoff");
  await changeWindow(() => accountBudget.getByRole("button", { name: "Previous window", exact: true }).click());
  stage = "latest_window";
  const latestWindow = await changeWindow(() => accountBudget.getByRole("button", { name: "Latest completed window", exact: true }).click());
  const latestEnd = Math.floor(Date.parse(latestWindow.asOf) / DAY) * DAY;
  sameWindow(latestWindow, { start: new Date(latestEnd - 30 * DAY).toISOString(), end: new Date(latestEnd).toISOString(), asOf: latestWindow.asOf }, "latest_window_mismatch");
  requireEvidence(await accountBudget.getByRole("button", { name: "Next window", exact: true }).isDisabled(), "latest_allows_future_window");
  // The same real account also supports a period-only deep link, without
  // inventing a resource/report selector or changing provider state.
  stage = "period_only_reload";
  const periodOnlyUrl = new URL(page.url());
  periodOnlyUrl.searchParams.delete("budget_resource");
  // Scope/category/grouping belong to a resource, not a period-only link.
  periodOnlyUrl.searchParams.delete("budget_scope");
  periodOnlyUrl.searchParams.delete("budget_category");
  periodOnlyUrl.searchParams.delete("budget_grouping");
  await page.evaluate(url => { history.replaceState(null, "", url); }, periodOnlyUrl.pathname + periodOnlyUrl.search);
  await page.reload({ waitUntil: "domcontentloaded" });
  await windowMarker.waitFor();
  sameWindow(await windowState(), latestWindow, "period_only_window_lost_on_reload");
  periodOnlyDiagnostic = await accountBudget.evaluate(node => ({
    resource_present: new URL(location.href).searchParams.has("budget_resource"),
    invalid_marker: new URL(location.href).searchParams.has("budget_selection"),
    alert_count: node.querySelectorAll('[role="alert"]').length,
    invalid_link: node.textContent.includes("This financial link is incomplete or invalid."),
    summary_read_failed: node.textContent.includes("Financial readings could not be refreshed."),
    service_unavailable: node.textContent.includes("The local service is unavailable."),
    busy: node.getAttribute("aria-busy") !== "false",
  }));
  requireEvidence(!periodOnlyDiagnostic.resource_present && !periodOnlyDiagnostic.invalid_marker && periodOnlyDiagnostic.alert_count === 0, "period_only_link_invalid");
  checks.history_windows = "passed";
  stage = "ordinary_account_entry";
  await page.goto(`${origin}/accounts/${encodeURIComponent(reportAccount)}`, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "API usage & spend", exact: true }).waitFor();
  if (!requireMoney || selectedHadQuota) requireEvidence(await page.locator("#quota-title").count() === 1, "ordinary_account_quota_missing");
  requireEvidence(await page.evaluate(() => {
    const heading = document.getElementById("budget-account-title");
    const quota = document.getElementById("quota-title");
    return document.activeElement !== heading && (quota === null || Boolean(quota.compareDocumentPosition(heading) & Node.DOCUMENT_POSITION_FOLLOWING));
  }), "ordinary_account_entry_reordered");
  const ordinaryPanel = await accountBudget.elementHandle();
  // The initial account read may finish while Playwright waits for Refresh to
  // become enabled. Bind this response to the window selected by the click,
  // rather than accepting the first response for the same endpoint.
  const ordinaryRefresh = page.waitForResponse(response => {
    const request = new URL(response.url()), selected = new URL(page.url());
    return request.pathname === `/api/v1/accounts/${encodeURIComponent(reportAccount)}/budgets` &&
      [["period_start", "budget_start"], ["period_end", "budget_end"], ["as_of", "budget_as_of"]].every(([wire, url]) =>
        request.searchParams.get(wire) !== null && selected.searchParams.get(url) !== null &&
        microseconds(request.searchParams.get(wire)) === microseconds(selected.searchParams.get(url)));
  });
  await accountBudget.getByRole("button", { name: "Refresh view", exact: true }).click();
  requireEvidence((await ordinaryRefresh).ok(), "ordinary_refresh_request_failed");
  await page.locator('.telemetry-panel[aria-labelledby="budget-account-title"][aria-busy="false"]').waitFor();
  if (!requireMoney || selectedHadQuota) requireEvidence(await page.locator("#quota-title").count() === 1, "ordinary_refresh_quota_missing");
  requireEvidence(await ordinaryPanel.evaluate(node => node.isConnected), "ordinary_refresh_remounted_panel");
  requireEvidence(await page.evaluate(() => document.activeElement?.id !== "budget-account-title" &&
    (document.getElementById("quota-title") === null || Boolean(document.getElementById("quota-title").compareDocumentPosition(document.getElementById("budget-account-title")) & Node.DOCUMENT_POSITION_FOLLOWING))), "ordinary_refresh_reordered_or_refocused");
  stage = "balance_history";
  const ordinarySummary = await (await ordinaryRefresh).json();
  let balancePointsVerified = 0;
  checks.balance_history_pagination = "not_run";
  for (const component of ordinarySummary.funds?.components ?? []) {
    const currency = component.remaining.value?.currency ?? component.limit.value?.currency;
    if (currency == null) continue;
    const card = page.locator(await selector("data-fund-component", component.component_id));
    const toggle = card.getByText("Balance history", {exact:true});
    requireEvidence(await toggle.count() === 1, "balance_history_control_missing");
    const incoming = page.waitForResponse(response => {
      const url = new URL(response.url());
      return response.request().method() === "GET" && url.origin === origin &&
        url.pathname === "/api/v1/capacity/history/v2" && url.searchParams.get("window_id") === component.component_id &&
        url.searchParams.get("resource_id") === component.subject.resource_id &&
        url.searchParams.get("subject_id") === reportAccount && !url.searchParams.has("cursor");
    });
    await toggle.click();
    const response = await incoming;
    requireEvidence(response.ok(), "balance_history_request_failed");
    let result = await response.json();
    const selected = new URL(response.url()).searchParams;
    requireEvidence(selected.get("resource_id") === component.subject.resource_id && selected.get("subject_id") === reportAccount &&
      selected.get("metric") === "remaining" && selected.get("series_kind") === "poll_snapshot" && selected.get("limit") === "50" &&
      microseconds(selected.get("as_of")) === microseconds(ordinarySummary.funds.as_of), "balance_history_selection_changed");
    const history = card.locator(await selector("data-funds-history", component.component_id));
    const points = [], identities = new Set();
    let nativeWindow = null;
    const validPoint = point => point.value.value !== null && ["available", "stale"].includes(point.value.availability) &&
      ["authoritative", "provider_reported"].includes(point.value.value_kind) && ["exact", "rounded"].includes(point.value.precision);
    async function reconcileBalance(batch) {
      const absent = batch.availability.state === "unavailable" && batch.availability.reason_code === "capacity_history_absent" && batch.items.length === 0;
      requireEvidence(batch.subject_id === reportAccount && batch.metric === "remaining" && batch.series_kind === "poll_snapshot" &&
        microseconds(batch.availability.as_of) === microseconds(selected.get("as_of")) &&
        (["available", "partial"].includes(batch.availability.state) || absent) &&
        batch.page.limit === 50 && batch.items.length <= 50, "balance_history_page_context_changed");
      requireEvidence(batch.page.has_more ? batch.items.length > 0 && typeof batch.page.next_cursor === "string" && batch.page.next_cursor.length > 0
        : batch.page.next_cursor === null, "balance_history_page_cursor_invalid");
      for (const point of batch.items) {
        requireEvidence(!identities.has(point.observation_id), "balance_history_duplicate_observation");
        identities.add(point.observation_id);
        requireEvidence(point.subject.account_id === reportAccount && point.subject.resource_id === component.subject.resource_id &&
          point.window_id === component.component_id && point.provenance.source_id === component.provenance.source_id &&
          point.metric === "remaining" && point.series_kind === "poll_snapshot", "balance_history_point_context_changed");
        nativeWindow ??= point.window_key;
        requireEvidence(typeof nativeWindow === "string" && nativeWindow.length > 0 && point.window_key === nativeWindow, "balance_history_native_window_changed");
        const cutoff = microseconds(selected.get("as_of")), observed = microseconds(point.observed_at);
        requireEvidence(observed >= microseconds(selected.get("from")) && observed < microseconds(selected.get("before")) && observed <= cutoff &&
          microseconds(point.collected_at) <= cutoff && microseconds(point.stored_at) <= cutoff, "balance_history_point_cutoff_changed");
        requireEvidence((point.native_unit === null || point.native_unit === currency.toLowerCase()) &&
          (point.value.value === null || point.value.value.unit === currency.toLowerCase()), "balance_history_native_unit_changed");
        points.push(point);
      }
      // A matching response can arrive before React appends it; wait for the
      // exact cumulative identity list, not a busy=false from the previous page.
      await playwright.expect.poll(() => history.locator("[data-balance-observation]").evaluateAll(nodes =>
        nodes.map(node => node.getAttribute("data-balance-observation")))).toEqual(points.map(point => point.observation_id));
      await playwright.expect(history).toHaveAttribute("aria-busy", "false");
      requireEvidence(await history.getByRole("alert").count() === 0, "balance_history_render_failed");
      requireEvidence(JSON.stringify(await history.locator("[data-balance-point]").evaluateAll(nodes =>
        nodes.map(node => node.getAttribute("data-balance-point")))) === JSON.stringify(points.filter(validPoint).map(point => point.observation_id)), "balance_history_plot_identities_mismatch");
      for (const point of points) {
        const row = history.locator(await selector("data-balance-observation", point.observation_id));
        requireEvidence(JSON.stringify(await row.locator("time").evaluateAll(nodes => nodes.map(node => node.getAttribute("datetime")))) ===
          JSON.stringify([point.observed_at, point.collected_at, point.stored_at]), "balance_history_time_mismatch");
        if (validPoint(point)) {
          requireEvidence(await row.locator("[data-balance-amount]").textContent() === quantity(point.value.value), "balance_history_amount_mismatch");
          const plotted = history.locator(await selector("data-balance-point", point.observation_id));
          const label = await plotted.getAttribute("aria-label");
          requireEvidence(label.includes(quantity(point.value.value)) && label.includes(point.observed_at) && label.includes(point.observation_id), "balance_history_plot_value_mismatch");
        } else {
          requireEvidence((await row.locator("[data-balance-amount]").textContent()).startsWith("Gap · "), "balance_history_gap_became_value");
        }
      }
      requireEvidence((await history.getByRole("button", {name:"Load more balance history",exact:true}).count() === 1) === batch.page.has_more, "balance_history_continuation_missing");
    }
    await reconcileBalance(result);
    // Exercise one actual continuation per component, at most 100 loaded points.
    // No continuation is manufactured when the genuine first page is terminal.
    if (result.page.has_more) {
      stage = "balance_history_continuation";
      const cursor = result.page.next_cursor;
      const nextResponse = page.waitForResponse(response => {
        const url = new URL(response.url());
        return response.request().method() === "GET" && url.origin === origin && url.pathname === "/api/v1/capacity/history/v2" &&
          url.searchParams.get("window_id") === component.component_id && url.searchParams.get("resource_id") === component.subject.resource_id &&
          url.searchParams.get("subject_id") === reportAccount && url.searchParams.get("cursor") === cursor;
      }).then(response => ({response}), error => ({error}));
      await history.getByRole("button", {name:"Load more balance history",exact:true}).click();
      const continued = await nextResponse;
      if (continued.error) throw continued.error;
      requireEvidence(continued.response.ok(), "balance_history_continuation_request_failed");
      const continuationQuery = new URL(continued.response.url()).searchParams;
      continuationQuery.delete("cursor");
      const queryEntries = query => [...query.entries()].sort(([a], [b]) => a.localeCompare(b));
      requireEvidence(JSON.stringify(queryEntries(continuationQuery)) === JSON.stringify(queryEntries(selected)), "balance_history_continuation_selection_changed");
      result = await continued.response.json();
      requireEvidence(result.items.length > 0 && result.page.next_cursor !== cursor, "balance_history_continuation_cursor_repeated");
      await reconcileBalance(result);
      checks.balance_history_pagination = "passed";
    }
    balancePointsVerified += points.filter(validPoint).length;
    await toggle.click();
  }
  if (balancePointsVerified > 0) checks.balance_history = "passed";
  await page.goBack({ waitUntil: "domcontentloaded" });
  await financialEntry();
  checks.financial_entry = "passed";
  stage = "overview_back";
  await page.goBack({ waitUntil: "domcontentloaded" });
  await financial.waitFor();
  requireEvidence(new URL(page.url()).search === before.search, "overview_filters_lost_on_back");
  await page.reload({ waitUntil: "domcontentloaded" });
  await financial.waitFor();
  await reconcile();
  requireEvidence(new URL(page.url()).search === before.search && await resources.inputValue() === "api" && await provider.inputValue() === chosenProvider, "overview_filters_lost_on_reload");
  requireEvidence(new URL(page.url()).searchParams.get("quota_sort") === "quota:descending", "quota_sort_lost_after_navigation");
  checks.navigation = "passed";
  for (const viewport of [{ width: 1920, height: 1080 }, { width: 1366, height: 768 }, { width: 768, height: 1024 }]) {
    await page.setViewportSize(viewport);
    requireEvidence(await resources.isVisible() && await provider.isVisible(), "overview_filters_hidden");
    requireEvidence(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), "overview_horizontal_overflow");
  }
  checks.responsive = "passed";
  stage = "pool_controls";
  let poolsVerified = 0;
  for (const candidate of allFinancialRows.filter(item => item.resource_id !== null)) {
    await page.goto(`${origin}/accounts/${encodeURIComponent(candidate.account.account_id)}`, { waitUntil: "domcontentloaded" });
    if (candidate.account.provider_key !== "ollama") {
      const billing = page.getByRole("region", { name: "API billing setup", exact: true, includeHidden: true });
      await billing.waitFor({ state: "attached" });
      // Subscription accounts keep API setup inside a collapsed disclosure;
      // API-only accounts expose it directly. Follow the actual user control.
      const disclosure = billing.locator("xpath=ancestor::details");
      for (const item of await disclosure.all()) if (!(await item.getAttribute("open"))) await item.locator(":scope > summary").click();
    }
    for (const scope of candidate.account.provider_key === "ollama" ? ["self", "team"] : ["billing"]) {
      const control = page.locator(`details[data-financial-pool="${scope}"]`).filter({ has: page.locator(`select[id="pool-primary-${candidate.resource_id}-${scope}"]`) });
      // Inputs mount only after expansion, so first locate by the stable
      // selector when there is exactly one resource on this account.
      const candidates = page.locator(`details[data-financial-pool="${scope}"]`);
      await candidates.first().waitFor();
      for (const item of await candidates.all()) if (!(await item.getAttribute("open"))) await item.locator("summary").click();
      await control.getByRole("button", { name: "Refresh pool status", exact: true }).waitFor();
      await page.waitForFunction(({ id }) => document.getElementById(id)?.closest("div[aria-busy]")?.getAttribute("aria-busy") === "false", { id: `pool-primary-${candidate.resource_id}-${scope}` });
      const configuration = await read(`/api/v1/accounts/${encodeURIComponent(candidate.account.account_id)}/financial-pools/${encodeURIComponent(candidate.resource_id)}/${scope}`);
      requireEvidence(configuration.account_id === candidate.account.account_id && configuration.resource_id === candidate.resource_id && configuration.selector === scope, "pool_context_mismatch");
      requireEvidence(await control.getByRole("alert").count() === 0, "pool_choices_unavailable");
      requireEvidence(await control.getByRole("button", { name: "Create distinct billing pool", exact: true }).isEnabled() === configuration.can_assign, "pool_create_eligibility_mismatch");
      requireEvidence(await control.locator("input[type=password], input[type=secret]").count() === 0, "unexpected_pool_secret_input");
      requireEvidence(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), "pool_horizontal_overflow");
      poolsVerified += 1;
    }
  }
  if (poolsVerified === 0) stop("blocked", "real_pool_controls_required");
  checks.pool_controls = "passed";
  requireEvidence(mutations === 0, "unexpected_mutation_request");
  status = "passed";
  requireEvidence(!requireMoney || checks.monetary === "passed", "monetary_journey_not_verified");
  reason = requireMoney ? "real_monetary_overview_detail_history_verified" : "real_overview_api_dom_navigation_verified";
} catch (error) {
  errorKind = error?.name === "TimeoutError" ? "timeout" : "assertion_or_error";
  const ownLine = /verify_overview\.mjs:(\d+):\d+/.exec(typeof error?.stack === "string" ? error.stack : "");
  errorLine = ownLine === null ? null : Number(ownLine[1]);
  const message = typeof error?.message === "string" ? error.message : "";
  errorClass = ["net::ERR_ABORTED", "net::ERR_CONNECTION_RESET", "net::ERR_CONNECTION_REFUSED", "Page crashed", "Target page, context or browser has been closed", "interrupted by another navigation", "Execution context was destroyed"].find(value => message.includes(value)) ?? null;
  if (error?.message !== "probe_stopped" && checks.authentication === "passed") { status = "failed"; reason = "overview_probe_boundary_failed"; }
} finally {
  if (status !== "passed" && page !== undefined) {
    failureDom = await page.evaluate(() => ({
      pathname_kind: location.pathname.startsWith("/accounts/") ? "account" : location.pathname === "/login" ? "login" : "other",
      sign_in: [...document.querySelectorAll("button")].some(node => node.textContent?.trim() === "Sign in"),
      financial_panel: document.querySelector('[aria-labelledby="budget-account-title"]') !== null,
      window_marker: document.querySelector("[data-budget-window]") !== null,
      alert_count: document.querySelectorAll('[role="alert"]').length,
      service_error: document.body.textContent.includes("The local service is unavailable"),
      no_context: document.body.textContent.includes("No financial resource"),
      account_read_failed: document.body.textContent.includes("Accounts could not be loaded from the local service."),
      registry_unavailable: document.body.textContent.includes("The local account registry is unavailable.")
    })).catch(() => null);
  }
  if (page !== undefined) await page.close().catch(() => { status = "failed"; reason = "probe_page_cleanup_failed"; });
  checks.read_only = page === undefined ? "not_run" : mutations === 0 ? "passed" : "failed";
  if (mutations !== 0) { status = "failed"; reason = "unexpected_mutation_request"; }
}
process.stdout.write(JSON.stringify({ record_type: "agentmonitor.m7_overview_probe.v1", status, reason_code: reason, stage, error_kind: errorKind, error_line: errorLine, error_class: errorClass, navigation_reads: navigationReads, failed_navigation_reads: failedNavigationReads, failure_dom: failureDom, period_only_diagnostic: periodOnlyDiagnostic, account_read_responses: accountReadResponses, direct_read_diagnostics: directReadDiagnostics, source_revision: sourceRevision, checks, rows_verified: rowsVerified, row_set_diagnostic: rowSetDiagnostic, ui_overview_responses: uiOverviewResponses, entry_diagnostic: entryDiagnostic, availability_diagnostic: availabilityDiagnostic, unsafe_requests: mutations, observed_at: new Date().toISOString() }) + "\n", () => process.exit(status === "passed" ? 0 : status === "failed" ? 1 : 3));
