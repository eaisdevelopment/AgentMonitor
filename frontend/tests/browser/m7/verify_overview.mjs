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
const renderedReadPaths = [];
const checks = { authentication: "not_run", overview: "not_run", filters: "not_run", navigation: "not_run", responsive: "not_run", pool_controls: "not_run", read_only: "not_run" };
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
  page.on("request", request => {
    if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) mutations += 1;
    if (request.method() === "GET") renderedReadPaths.push(new URL(request.url()).pathname);
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
      if (!["available", ...(path === "/api/v1/budgets" ? ["partial"] : [])].includes(result.availability?.state)) stop("blocked", "comparison_source_unavailable");
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
    await settled();
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
  let expected = await reconcile();
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
    requireEvidence(expected.items.every(row => row.account.organization_id === organizationId || row.primary_organization_id === organizationId || row.access_paths?.some(path => path.account.organization_id === organizationId)), "shared_organization_filter_mismatch");
  }
  await resources.selectOption("api");
  checks.filters = "passed";
  const row = expected.items.find(item => item.contexts.length > 0) ?? expected.items.find(item => item.funds.length > 0);
  if (row === undefined) stop("blocked", "filtered_financial_link_unavailable");
  const before = new URL(page.url());
  const dom = financial.locator(await selector("data-financial-row", row.row_id));
  const reportAccount = row.contexts[0]?.report_account_id ?? row.account.account_id;
  const reportResource = row.contexts[0]?.report_resource_id ?? row.resource_id;
  await dom.getByRole("button").first().click();
  await page.waitForURL(url => url.pathname === `/accounts/${encodeURIComponent(reportAccount)}`);
  const detail = new URL(page.url());
  requireEvidence(detail.searchParams.get("budget_resource") === reportResource, "detail_resource_selector_lost");
  requireEvidence(detail.searchParams.get("budget_report") === (row.contexts[0]?.report_id ?? null), "detail_report_selector_lost");
  requireEvidence(microseconds(detail.searchParams.get("budget_start")) === microseconds(expected.period.start) && microseconds(detail.searchParams.get("budget_end")) === microseconds(expected.period.end), "detail_period_lost");
  requireEvidence(microseconds(detail.searchParams.get("budget_as_of")) === microseconds(expected.as_of), "detail_cutoff_lost");
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("region", { name: "API usage & spend", exact: true }).waitFor();
  requireEvidence(new URL(page.url()).search === detail.search, "detail_selectors_lost_on_reload");
  if (row.contexts[0] !== undefined) {
    const context = row.contexts[0];
    const query = new URLSearchParams({ account_id: reportAccount, report_id: context.report_id, period_start: detail.searchParams.get("budget_start"), period_end: detail.searchParams.get("budget_end"), as_of: detail.searchParams.get("budget_as_of") });
    const selected = await read(`/api/v1/budgets/${encodeURIComponent(reportResource)}?${query}`);
    requireEvidence(selected.report.report_id === context.report_id && selected.report.account_id === reportAccount && selected.report.resource_id === reportResource && microseconds(selected.as_of) === microseconds(expected.as_of), "selected_report_context_mismatch");
    requireEvidence(JSON.stringify(selected.reported_spend.total) === JSON.stringify(context.spend), "overview_detail_spend_mismatch");
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
    for (const fact of expectedFacts) requireEvidence(JSON.stringify(paged.find(row => factKey(row) === factKey(fact))) === JSON.stringify(fact), "history_exact_fact_mismatch");
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
  let poolsVerified = 0;
  for (const candidate of allFinancialRows.filter(item => item.resource_id !== null)) {
    await page.goto(`${origin}/accounts/${encodeURIComponent(candidate.account.account_id)}`, { waitUntil: "domcontentloaded" });
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
  reason = "real_overview_api_dom_navigation_verified";
} catch (error) {
  if (error?.message !== "probe_stopped" && checks.authentication === "passed") { status = "failed"; reason = "overview_probe_boundary_failed"; }
} finally {
  if (page !== undefined) await page.close().catch(() => { status = "failed"; reason = "probe_page_cleanup_failed"; });
  checks.read_only = page === undefined ? "not_run" : mutations === 0 ? "passed" : "failed";
  if (mutations !== 0) { status = "failed"; reason = "unexpected_mutation_request"; }
}
process.stdout.write(JSON.stringify({ record_type: "agentmonitor.m7_overview_probe.v1", status, reason_code: reason, source_revision: sourceRevision, checks, rows_verified: rowsVerified, unsafe_requests: mutations, observed_at: new Date().toISOString() }) + "\n", () => process.exit(status === "passed" ? 0 : status === "failed" ? 1 : 3));
