"use strict";

// Real installed browser/API. --collect permits exactly one official usage read;
// no account, key, monitoring or provider-profile configuration is submitted.
const origin = "http://127.0.0.1:43110";
const collect = process.argv.includes("--collect");
const rangeKey = process.argv.includes("--range=7d") ? "7d" : "30d";
const days = rangeKey === "7d" ? 7 : 30;
let page, status = "blocked", reason = "browser_unavailable", revision = null;
let stage = "browser", posts = 0, unsafe = 0;
let errorKind = null, renderDiagnostic = null;
const responseDiagnostics = [], failedRequests = [];
const networkErrors = new Set(["net::ERR_NETWORK_CHANGED", "net::ERR_INTERNET_DISCONNECTED", "net::ERR_CONNECTION_REFUSED", "net::ERR_CONNECTION_RESET", "net::ERR_CONNECTION_CLOSED", "net::ERR_TIMED_OUT", "net::ERR_ABORTED", "net::ERR_FAILED"]);
function pathFamily(url) {
  const path = new URL(url).pathname;
  if (path === "/api/v1/accounts") return "accounts";
  if (path === "/api/v1/organizations") return "organizations";
  if (/^\/api\/v1\/accounts\/[^/]+\/budgets$/.test(path)) return "budget_summary";
  if (/^\/api\/v1\/accounts\/[^/]+$/.test(path)) return "account_detail";
  if (/^\/api\/v1\/accounts\/[^/]+\/cloud-usage\/[^/]+\/collection-eligibility$/.test(path)) return "cloud_eligibility";
  if (/^\/api\/v1\/accounts\/[^/]+\/cloud-usage\/[^/]+\/runs\/[^/]+$/.test(path)) return "cloud_run";
  return "other";
}
function sameInstant(left, right) {
  const canonical = value => typeof value === "string" ? value.replace(/(?:\.(\d{1,6}))?Z$/, (_, fraction) => `.${(fraction ?? "").padEnd(6, "0")}Z`) : null;
  return canonical(left) !== null && canonical(left) === canonical(right);
}
const checks = { authentication: false, controls: false, eligibility: false, reload: false, collection: false, report: false, balance_continuity: false };
function stop(state, code) { status = state; reason = code; throw new Error("probe_stopped"); }
function requireEvidence(value, code) { if (!value) stop("failed", code); }
try {
  const { chromium } = await import("/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules/@playwright/test/index.mjs");
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9225", { timeout: 5000 });
  const context = browser.contexts()[0];
  if (!context) stop("blocked", "browser_context_unavailable");
  page = await context.newPage();
  page.setDefaultTimeout(10000);
  page.on("response", response => {
    responseDiagnostics.push({ family: pathFamily(response.url()), status: response.status() });
    if (responseDiagnostics.length > 40) responseDiagnostics.shift();
  });
  page.on("requestfailed", request => {
    failedRequests.push({ family: pathFamily(request.url()), error: networkErrors.has(request.failure()?.errorText) ? request.failure().errorText : "network_error_other" });
    if (failedRequests.length > 40) failedRequests.shift();
  });
  page.on("request", request => {
    if (["GET", "HEAD", "OPTIONS"].includes(request.method())) return;
    if (collect && request.method() === "POST" && /^\/api\/v1\/accounts\/[^/]+\/cloud-usage\/[^/]+\/collections$/.test(new URL(request.url()).pathname)) posts += 1;
    else unsafe += 1;
  });
  await page.goto(origin, { waitUntil: "domcontentloaded" });
  const signIn = page.getByRole("heading", { name: "Sign in", exact: true });
  await signIn.or(page.getByRole("button", { name: "Accounts", exact: true })).first().waitFor();
  if (await signIn.isVisible()) stop("blocked", "authentication_required");
  checks.authentication = true;
  async function read(path) {
    const response = await page.request.get(origin + path, { headers: { Origin: origin }, timeout: 10000 });
    if (response.status() === 401) stop("blocked", "authentication_required");
    requireEvidence(response.ok(), "cloud_read_failed");
    return response.json();
  }
  const version = await read("/api/v1/operations/versions");
  revision = version.source_revision?.value ?? null;
  requireEvidence(/^[a-f0-9]{40}$/.test(revision ?? ""), "revision_unavailable");
  const inventory = await read("/api/v1/accounts?provider_key=ollama&limit=200");
  requireEvidence(inventory.page?.has_more === false, "account_selection_requires_paging");
  const now = new Date(), end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  const start = new Date(end.getTime() - days * 86400000);
  const period = { period_start: start.toISOString(), period_end: end.toISOString(), as_of: now.toISOString() };
  let selected, fallback;
  for (const account of inventory.items.filter(value => value.lifecycle === "active" && value.is_effective_monitoring_enabled)) {
    const summary = await read(`/api/v1/accounts/${encodeURIComponent(account.account_id)}/budgets?${new URLSearchParams(period)}`);
    const resource = summary.cloud_resources?.find(value => value.lifecycle === "active");
    if (resource) {
      const candidate = { account, resource, summary };
      fallback ??= candidate;
      if (!collect) { selected = candidate; break; }
      const eligibility = await read(`/api/v1/accounts/${encodeURIComponent(account.account_id)}/cloud-usage/${encodeURIComponent(resource.resource_id)}/collection-eligibility?${new URLSearchParams({ scope: "self", range_key: rangeKey, interval_start: period.period_start, interval_end: period.period_end })}`);
      if (eligibility.can_collect) { selected = candidate; break; }
    }
  }
  selected ??= fallback;
  if (!selected) stop("blocked", "active_cloud_resource_required");
  const { account, resource, summary } = selected;
  const path = `/api/v1/accounts/${encodeURIComponent(account.account_id)}/cloud-usage/${encodeURIComponent(resource.resource_id)}`;
  const reportContext = { scope: "self", range_key: rangeKey, interval_start: period.period_start, interval_end: period.period_end };
  const query = new URLSearchParams({ budget_resource: resource.resource_id, budget_start: period.period_start, budget_end: period.period_end, budget_as_of: period.as_of });
  const address = `${origin}/accounts/${encodeURIComponent(account.account_id)}?${query}`;
  // Scope directly by the published resource marker, not by any other account's control.
  const resourceSelector = await page.evaluate(value => `[data-cloud-collect-resource="${CSS.escape(value)}"]`, resource.resource_id);
  const selectedControl = page.getByRole("region", { name: "Collect cloud usage", exact: true }).and(page.locator(resourceSelector));
  async function renderedSummary(target, action, phase) {
    stage = "rendered_summary";
    const targetQuery = new URL(target).searchParams;
    const summaryPath = `/api/v1/accounts/${encodeURIComponent(account.account_id)}/budgets`;
    renderDiagnostic = { phase, summary_status: null, resource_present: false, panel_settled: false };
    // One existing ten-second readiness budget: staging must not hide latency
    // behind successive longer waits or retry failed reads.
    const deadline = Date.now() + 10000;
    const remaining = () => Math.max(1, deadline - Date.now());
    const responsePromise = page.waitForResponse(response => {
      const url = new URL(response.url());
      return response.request().method() === "GET" && url.pathname === summaryPath &&
        [["period_start", "budget_start"], ["period_end", "budget_end"], ["as_of", "budget_as_of"]]
          .every(([wire, selector]) => sameInstant(url.searchParams.get(wire), targetQuery.get(selector)));
    }, { timeout: 10000 }).then(response => ({ response }), error => ({ error }));
    await action();
    const observed = await responsePromise;
    if (observed.error) throw observed.error;
    const response = observed.response;
    renderDiagnostic.summary_status = response.status();
    if (response.status() === 401) stop("blocked", "authentication_required");
    requireEvidence(response.ok(), "rendered_summary_http_failed");
    const actual = await response.json();
    requireEvidence(actual.account_id === account.account_id &&
      sameInstant(actual.period?.start, targetQuery.get("budget_start")) &&
      sameInstant(actual.period?.end, targetQuery.get("budget_end")) &&
      sameInstant(actual.as_of, targetQuery.get("budget_as_of")), "rendered_summary_context_mismatch");
    renderDiagnostic.resource_present = actual.cloud_resources?.some(value => value.resource_id === resource.resource_id) === true;
    requireEvidence(renderDiagnostic.resource_present, "rendered_cloud_resource_absent");
    stage = "financial_panel_settle";
    await page.locator('[aria-labelledby="budget-account-title"][aria-busy="false"]').waitFor({ timeout: remaining() });
    renderDiagnostic.panel_settled = true;
    requireEvidence(!new URL(page.url()).searchParams.has("budget_selection"), "cloud_financial_selection_invalid");
    stage = "controls";
    try { await selectedControl.waitFor({ timeout: remaining() }); }
    catch (error) { errorKind = error?.name === "TimeoutError" ? "timeout" : "assertion_or_error"; stop("failed", "cloud_collect_control_missing"); }
    requireEvidence(await selectedControl.getAttribute("aria-label") === "Collect cloud usage", "cloud_collect_region_mismatch");
  }
  await renderedSummary(address, () => page.goto(address, { waitUntil: "domcontentloaded", timeout: 10000 }), "entry");
  const button = selectedControl.getByRole("button", { name: "Collect usage", exact: true });
  await selectedControl.getByRole("button", { name: "Refresh usage status", exact: true }).waitFor();
  requireEvidence(await button.getAttribute("type") === "button", "cloud_collect_button_not_explicit");
  checks.controls = true;
  stage = "eligibility";
  let eligibility = await read(path + "/collection-eligibility?" + new URLSearchParams(reportContext));
  requireEvidence(eligibility.account_id === account.account_id && eligibility.resource_id === resource.resource_id && eligibility.report_context.scope === "self" && eligibility.report_context.range_key === rangeKey, "cloud_eligibility_context_mismatch");
  requireEvidence(Date.parse(eligibility.report_context.interval_start) === start.getTime() && Date.parse(eligibility.report_context.interval_end) === end.getTime(), "cloud_eligibility_interval_mismatch");
  checks.eligibility = true;
  await renderedSummary(page.url(), () => page.reload({ waitUntil: "domcontentloaded", timeout: 10000 }), "reload");
  requireEvidence(page.url() === address && posts === 0 && unsafe === 0, "cloud_reload_changed_intent");
  checks.reload = true;
  if (collect) {
    stage = "collection";
    const waitUntil = Date.now() + 130000;
    while (!eligibility.can_collect && eligibility.reason_code === "cloud_usage_rate_limited" && eligibility.next_allowed_at !== null && Date.parse(eligibility.next_allowed_at) <= waitUntil && Date.now() < waitUntil) {
      await page.waitForTimeout(2000);
      eligibility = await read(path + "/collection-eligibility?" + new URLSearchParams(reportContext));
    }
    if (!eligibility.can_collect) stop("blocked", eligibility.reason_code);
    await selectedControl.getByRole("button", { name: "Refresh usage status", exact: true }).click();
    await button.waitFor();
    await page.waitForFunction(() => [...document.querySelectorAll('button')].some(button => button.textContent === 'Collect usage' && !button.disabled));
    const accepted = page.waitForResponse(response => new URL(response.url()).pathname === path + "/collections" && response.request().method() === "POST");
    await button.click();
    const response = await accepted;
    if (response.status() === 429) stop("blocked", "concurrent_provider_cooldown");
    requireEvidence(response.status() === 202, "cloud_collection_not_accepted");
    const admitted = await response.json();
    requireEvidence(admitted.account_id === account.account_id && admitted.resource_id === resource.resource_id && admitted.report_context.range_key === rangeKey, "cloud_run_context_mismatch");
    await renderedSummary(page.url(), () => page.reload({ waitUntil: "domcontentloaded", timeout: 10000 }), "collection_reload");
    stage = "collection";
    let run = admitted;
    const stopAt = Math.min(Date.parse(run.deadline_at) + 10000, Date.now() + 140000);
    while (["queued", "running", "committing"].includes(run.state) && Date.now() < stopAt) {
      await page.waitForTimeout(2000);
      run = await read(path + "/runs/" + encodeURIComponent(admitted.run_id));
    }
    requireEvidence(posts === 1 && unsafe === 0, "cloud_action_replayed_or_configured");
    if (!["succeeded", "partial"].includes(run.state)) stop("failed", "cloud_collection_" + run.state);
    checks.collection = true;
    requireEvidence(run.report_id !== null, "cloud_success_report_missing");
    const after = await read(`/api/v1/accounts/${encodeURIComponent(account.account_id)}/budgets?${new URLSearchParams({ ...period, as_of: new Date().toISOString() })}`);
    const actual = after.cloud_resources.find(value => value.resource_id === resource.resource_id);
    requireEvidence(actual?.reports.some(value => [value.current, value.latest_attempt].some(report => report?.report_id === run.report_id)), "collected_report_not_readable");
    const reportSelector = await page.evaluate(id => `[data-report-id="${CSS.escape(id)}"]`, run.report_id);
    await page.locator(reportSelector).first().waitFor();
    const currentAddress = new URL(page.url());
    requireEvidence(Date.parse(currentAddress.searchParams.get("budget_start")) === start.getTime() && Date.parse(currentAddress.searchParams.get("budget_end")) === end.getTime(), "collection_changed_selected_interval");
    checks.report = true;
    if (summary.funds?.components.length > 0) {
      requireEvidence(after.funds?.components.length > 0, "balance_disappeared_after_usage");
      requireEvidence(await page.locator("[data-fund-component]").count() > 0, "balance_not_rendered_after_usage");
      checks.balance_continuity = true;
    } else stop("blocked", "balance_comparison_unavailable");
  }
  requireEvidence(unsafe === 0 && posts === (collect ? 1 : 0), "unexpected_mutation");
  status = "passed"; reason = null;
} catch (error) {
  errorKind ??= error?.name === "TimeoutError" ? "timeout" : "assertion_or_error";
  if (error?.message !== "probe_stopped") { status = "failed"; reason = stage === "rendered_summary" ? "rendered_summary_unavailable" : stage === "financial_panel_settle" ? "financial_panel_not_settled" : "probe_execution_failed"; }
} finally {
  if (page && status !== "passed") {
    const state = await page.evaluate(() => ({
      signed_out: [...document.querySelectorAll("h1,h2")].some(node => node.textContent === "Sign in"),
      financial_panel_present: document.getElementById("budget-account-title") !== null,
      financial_panel_busy: document.querySelector('[aria-labelledby="budget-account-title"]')?.getAttribute("aria-busy") === "true",
      alert_visible: document.querySelector('[role="alert"]') !== null,
      invalid_selection: new URL(location.href).searchParams.has("budget_selection"),
    })).catch(() => null);
    renderDiagnostic = { ...renderDiagnostic, page_state: state };
  }
  if (page) await page.close().catch(() => {});
}
console.log(JSON.stringify({ status, reason, stage, error_kind: errorKind, render_diagnostic: renderDiagnostic, response_diagnostics: responseDiagnostics, failed_requests: failedRequests, revision, scope: collect ? "one_real_cloud_usage_action" : "cloud_usage_read_only_controls", range: rangeKey, checks, posts, unsafe }));
process.exit(status === "passed" ? 0 : status === "blocked" ? 3 : 1);
