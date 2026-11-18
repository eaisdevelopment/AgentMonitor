"use strict";

// Real installed browser/API. --collect permits exactly one official usage read;
// no account, key, monitoring or provider-profile configuration is submitted.
const origin = "http://127.0.0.1:43110";
const collect = process.argv.includes("--collect");
const expectedArgument = process.argv.find(value => value.startsWith("--expected-revision="));
const expectedRevision = expectedArgument?.slice("--expected-revision=".length) ?? null;
const rangeKey = process.argv.includes("--range=7d") ? "7d" : "30d";
const days = rangeKey === "7d" ? 7 : 30;
const grouping = process.argv.includes("--grouping=model") ? ["model"] : [];
const sameGrouping = value => JSON.stringify(value ?? []) === JSON.stringify(grouping);
const usageScope = process.argv.includes("--scope=team") ? "team" : "self";
let page, status = "blocked", reason = "browser_unavailable", revision = null;
let stage = "browser", posts = 0, unsafe = 0;
let errorKind = null, renderDiagnostic = null, readFailure = null;
let modelFacts = null, runWitness = null, reportWitness = null;
const responseDiagnostics = [], failedRequests = [];
// A runner timeout may close only this probe's page; never the shared browser.
process.once("SIGTERM", () => {
  const deadline = setTimeout(() => process.exit(3), 8000);
  Promise.resolve(page?.close()).catch(() => {}).finally(() => {
    clearTimeout(deadline); process.exit(3);
  });
});
const networkErrors = new Set(["net::ERR_NETWORK_CHANGED", "net::ERR_INTERNET_DISCONNECTED", "net::ERR_CONNECTION_REFUSED", "net::ERR_CONNECTION_RESET", "net::ERR_CONNECTION_CLOSED", "net::ERR_TIMED_OUT", "net::ERR_ABORTED", "net::ERR_FAILED"]);
function pathFamily(url) {
  const path = new URL(url).pathname;
  if (path === "/api/v1/iam/initialization") return "iam_initialization";
  if (path === "/api/v1/session") return "iam_session";
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
  if (expectedRevision !== null && !/^[a-f0-9]{40}$/.test(expectedRevision)) stop("failed", "expected_revision_invalid");
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
    if (!response.ok()) {
      readFailure = { family: pathFamily(origin + path), status: response.status() };
    }
    if (response.status() === 401) stop("blocked", "authentication_required");
    requireEvidence(response.ok(), "cloud_read_failed");
    return response.json();
  }
  const version = await read("/api/v1/operations/versions");
  revision = version.source_revision?.value ?? null;
  requireEvidence(/^[a-f0-9]{40}$/.test(revision ?? ""), "revision_unavailable");
  if (expectedRevision !== null) requireEvidence(revision === expectedRevision, "installed_revision_mismatch");
  const inventory = await read("/api/v1/accounts?provider_key=ollama&limit=200");
  requireEvidence(inventory.page?.has_more === false, "account_selection_requires_paging");
  const now = new Date(), end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  const start = new Date(end.getTime() - days * 86400000);
  const period = { period_start: start.toISOString(), period_end: end.toISOString(), as_of: now.toISOString() };
  // The existing per-report allowance is one request per fifteen-minute window.
  // Wait for an actual fair turn before choosing one account and submitting once.
  // This is read-only readiness, never a retry of an accepted collection.
  const eligibilityDeadline = Date.now() + 1000000;
  const candidates = [];
  for (const account of inventory.items.filter(value => value.lifecycle === "active" && value.is_effective_monitoring_enabled)) {
    const summary = await read(`/api/v1/accounts/${encodeURIComponent(account.account_id)}/budgets?${new URLSearchParams(period)}`);
    const resource = summary.cloud_resources?.find(value => value.lifecycle === "active");
    if (resource) candidates.push({ account, resource, summary });
  }
  let selected = collect ? undefined : candidates[0];
  const fallback = candidates[0];
  while (collect && !selected && candidates.length && Date.now() < eligibilityDeadline) {
    let waiting = false;
    for (const candidate of candidates) {
      const { account, resource } = candidate;
      const eligibility = await read(`/api/v1/accounts/${encodeURIComponent(account.account_id)}/cloud-usage/${encodeURIComponent(resource.resource_id)}/collection-eligibility?${new URLSearchParams({ scope: usageScope, range_key: rangeKey, interval_start: period.period_start, interval_end: period.period_end, ...(grouping.length ? { grouping: "model" } : {}) })}`);
      if (eligibility.can_collect) { selected = candidate; break; }
      if (eligibility.reason_code === "cloud_usage_rate_limited" &&
        (eligibility.next_allowed_at === null || Date.parse(eligibility.next_allowed_at) <= eligibilityDeadline)) waiting = true;
    }
    if (selected || !waiting) break;
    await page.waitForTimeout(2000);
  }
  selected ??= fallback;
  if (!selected) stop("blocked", "active_cloud_resource_required");
  const { account, resource, summary } = selected;
  const path = `/api/v1/accounts/${encodeURIComponent(account.account_id)}/cloud-usage/${encodeURIComponent(resource.resource_id)}`;
  const reportContext = { scope: usageScope, range_key: rangeKey, interval_start: period.period_start, interval_end: period.period_end, ...(grouping.length ? { grouping: "model" } : {}) };
  const query = new URLSearchParams({ budget_scope: usageScope, budget_resource: resource.resource_id, budget_start: period.period_start, budget_end: period.period_end, budget_as_of: period.as_of });
  if (grouping.length) query.set("budget_grouping", "model");
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
  requireEvidence(eligibility.account_id === account.account_id && eligibility.resource_id === resource.resource_id && eligibility.report_context.scope === usageScope && eligibility.report_context.range_key === rangeKey && sameGrouping(eligibility.report_context.grouping), "cloud_eligibility_context_mismatch");
  requireEvidence(Date.parse(eligibility.report_context.interval_start) === start.getTime() && Date.parse(eligibility.report_context.interval_end) === end.getTime(), "cloud_eligibility_interval_mismatch");
  checks.eligibility = true;
  await renderedSummary(page.url(), () => page.reload({ waitUntil: "domcontentloaded", timeout: 10000 }), "reload");
  stage = "reload_intent";
  const reloadedAddress = new URL(page.url()), expectedAddress = new URL(address);
  reloadedAddress.searchParams.sort(); expectedAddress.searchParams.sort();
  requireEvidence(reloadedAddress.href === expectedAddress.href && posts === 0 && unsafe === 0, "cloud_reload_changed_intent");
  checks.reload = true;
  if (collect) {
    stage = "collection";
    const waitUntil = eligibilityDeadline;
    while (!eligibility.can_collect && eligibility.reason_code === "cloud_usage_rate_limited" && (eligibility.next_allowed_at === null || Date.parse(eligibility.next_allowed_at) <= waitUntil) && Date.now() < waitUntil) {
      await page.waitForTimeout(2000);
      eligibility = await read(path + "/collection-eligibility?" + new URLSearchParams(reportContext));
    }
    if (!eligibility.can_collect) stop("blocked", eligibility.reason_code);
    await selectedControl.getByRole("button", { name: "Refresh usage status", exact: true }).click();
    stage = "collection_button_ready";
    await button.waitFor();
    await page.waitForFunction(() => [...document.querySelectorAll('button')].some(button => button.textContent === 'Collect usage' && !button.disabled));
    stage = "collection_submission";
    const accepted = page.waitForResponse(response => new URL(response.url()).pathname === path + "/collections" && response.request().method() === "POST");
    await button.click();
    const response = await accepted;
    if (response.status() === 429) stop("blocked", "concurrent_provider_cooldown");
    requireEvidence(response.status() === 202, "cloud_collection_not_accepted");
    const admitted = await response.json();
    const matchingRun = run => run.account_id === account.account_id && run.resource_id === resource.resource_id &&
      run.report_context?.scope === usageScope && run.report_context?.range_key === rangeKey && sameGrouping(run.report_context?.grouping) &&
      sameInstant(run.report_context?.interval_start, period.period_start) && sameInstant(run.report_context?.interval_end, period.period_end);
    requireEvidence(matchingRun(admitted), "cloud_run_context_mismatch");
    await renderedSummary(page.url(), () => page.reload({ waitUntil: "domcontentloaded", timeout: 10000 }), "collection_reload");
    stage = "collection";
    let run = admitted;
    const stopAt = Math.min(Date.parse(run.deadline_at) + 10000, Date.now() + 140000);
    while (["queued", "running", "committing"].includes(run.state) && Date.now() < stopAt) {
      await page.waitForTimeout(2000);
      run = await read(path + "/runs/" + encodeURIComponent(admitted.run_id));
    }
    requireEvidence(posts === 1 && unsafe === 0, "cloud_action_replayed_or_configured");
    requireEvidence(run.run_id === admitted.run_id && matchingRun(run), "cloud_terminal_context_mismatch");
    runWitness = { account_id: run.account_id, resource_id: run.resource_id, run_id: run.run_id, state: run.state,
      report_id: run.report_id, report_context: { scope: run.report_context.scope, range_key: run.report_context.range_key,
        interval_start: run.report_context.interval_start, interval_end: run.report_context.interval_end, grouping: run.report_context.grouping ?? [] } };
    if (run.state !== "succeeded") stop("failed", "cloud_collection_" + run.state);
    checks.collection = true;
    requireEvidence(run.report_id !== null, "cloud_success_report_missing");
    stage = "collected_report_read";
    const after = await read(`/api/v1/accounts/${encodeURIComponent(account.account_id)}/budgets?${new URLSearchParams({ ...period, as_of: new Date().toISOString() })}`);
    const actual = after.cloud_resources.find(value => value.resource_id === resource.resource_id);
    const collectedReport = actual?.reports.flatMap(value => [value.current, value.latest_attempt]).find(report => report?.report_id === run.report_id);
    requireEvidence(collectedReport !== undefined, "collected_report_not_readable");
    reportWitness = Object.fromEntries(["account_id", "resource_id", "report_id", "provider_key", "source_id", "source_category", "completeness", "grouping", "requested_period", "covered_period"].map(key => [key, collectedReport[key]]));
    requireEvidence(collectedReport.account_id === account.account_id && collectedReport.resource_id === resource.resource_id &&
      collectedReport.provider_key === "ollama" && collectedReport.source_id === "ollama.cloud.usage.v1" &&
      collectedReport.source_category === `${usageScope}_requests_and_cost` && sameGrouping(collectedReport.grouping), "collected_report_context_mismatch");
    requireEvidence(collectedReport.completeness === "complete" &&
      sameInstant(collectedReport.requested_period?.start, period.period_start) && sameInstant(collectedReport.requested_period?.end, period.period_end) &&
      sameInstant(collectedReport.covered_period?.start, period.period_start) && sameInstant(collectedReport.covered_period?.end, period.period_end), "collected_report_incomplete");
    const reportSelector = await page.evaluate(id => `[data-report-id="${CSS.escape(id)}"]`, run.report_id);
    stage = "collected_report_render";
    await page.locator(reportSelector).first().waitFor();
    const currentAddress = new URL(page.url());
    requireEvidence(Date.parse(currentAddress.searchParams.get("budget_start")) === start.getTime() && Date.parse(currentAddress.searchParams.get("budget_end")) === end.getTime(), "collection_changed_selected_interval");
    if (grouping.length) {
      stage = "model_exact_history";
      const selector = await page.evaluate(id => `[data-budget-history="${CSS.escape(id)}"]`, run.report_id);
      const history = page.locator(selector).first();
      await history.locator(':scope[aria-busy="false"]').waitFor();
      const selectedQuery = new URLSearchParams({ account_id: account.account_id, report_id: run.report_id,
        period_start: period.period_start, period_end: period.period_end,
        as_of: currentAddress.searchParams.get("budget_as_of") });
      const full = await read(`/api/v1/budgets/${encodeURIComponent(resource.resource_id)}?${selectedQuery}`);
      requireEvidence(full.report?.report_id === run.report_id && sameGrouping(full.report.grouping), "model_report_context_mismatch");
      const facts = [...full.report.cost_buckets.map(bucket => ({ kind: "cost", bucket, amount: bucket.amount })),
        ...full.report.usage_buckets.map(bucket => ({ kind: "usage", bucket, amount: bucket.quantity }))];
      for (let index = 0; index < 40; index++) {
        const more = history.getByRole("button", { name: "Load more history", exact: true });
        if (await more.count() === 0) break;
        const loaded = history.locator('[data-bucket-key]');
        const before = await loaded.count();
        await more.click();
        await page.waitForFunction(({ selector, before }) => {
          const root = document.querySelector(selector);
          return root?.getAttribute("aria-busy") === "false" && root.querySelectorAll('[data-bucket-key]').length > before;
        }, { selector, before });
        requireEvidence(index < 39, "model_history_bound_exceeded");
      }
      requireEvidence(await history.locator('[data-bucket-key]').count() === facts.length, "model_history_count_mismatch");
      const exact = amount => {
        const coefficient = BigInt(amount.coefficient), digits = (coefficient < 0n ? -coefficient : coefficient).toString().padStart(amount.scale + 1, "0");
        return `${coefficient < 0n ? "-" : ""}${amount.scale === 0 ? digits : `${digits.slice(0, -amount.scale)}.${digits.slice(-amount.scale)}`} ${amount.currency ?? amount.unit}`;
      };
      for (const fact of facts) {
        requireEvidence(fact.bucket.dimensions.length === 1 && fact.bucket.dimensions[0].kind === "model", "model_dimension_missing");
        const dimension = fact.bucket.dimensions[0];
        requireEvidence(dimension.is_remainder === true ? dimension.value === null : typeof dimension.value === "string", "model_remainder_ambiguous");
        const key = await page.evaluate(value => CSS.escape(value), fact.bucket.bucket_key);
        const row = history.locator(`[data-bucket-kind="${fact.kind}"][data-bucket-key="${key}"]`);
        requireEvidence(await row.getByRole("cell").nth(1).textContent() === exact(fact.amount), "model_exact_amount_mismatch");
        requireEvidence((await row.getByRole("cell").last().textContent()) === `Model: ${dimension.is_remainder === true ? "Provider-reported remainder" : dimension.value}`, "model_dimension_label_mismatch");
      }
      modelFacts = { rows: facts.length, costs: full.report.cost_buckets.length, usage: full.report.usage_buckets.length,
        named_models: new Set(facts.flatMap(fact => fact.bucket.dimensions).filter(d => !d.is_remainder).map(d => d.value)).size,
        remainder_rows: facts.filter(fact => fact.bucket.dimensions[0].is_remainder === true).length };
      requireEvidence(currentAddress.searchParams.get("budget_grouping") === "model", "model_selection_lost_after_collection");
      requireEvidence(!(await history.textContent()).includes("Reported spend:"), "model_invented_total");
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.locator(selector).first().locator(':scope[aria-busy="false"]').waitFor();
      requireEvidence(new URL(page.url()).searchParams.get("budget_grouping") === "model" && posts === 1, "model_reload_changed_or_replayed");
    }
    checks.report = true;
    if (summary.funds?.components.length > 0) {
      requireEvidence(after.funds?.components.length > 0, "balance_disappeared_after_usage");
      requireEvidence(await page.locator("[data-fund-component]").count() > 0, "balance_not_rendered_after_usage");
      checks.balance_continuity = true;
    } else stop("blocked", "balance_comparison_unavailable");
  }
  requireEvidence(unsafe === 0 && posts === (collect ? 1 : 0), "unexpected_mutation");
  if (expectedRevision !== null) {
    const finalVersion = await read("/api/v1/operations/versions");
    requireEvidence(finalVersion.source_revision?.value === expectedRevision, "installed_revision_changed");
  }
  status = "passed"; reason = null;
} catch (error) {
  errorKind ??= error?.name === "TimeoutError" ? "timeout" : "assertion_or_error";
  if (error?.message !== "probe_stopped") { status = "failed"; reason = stage === "rendered_summary" ? "rendered_summary_unavailable" : stage === "financial_panel_settle" ? "financial_panel_not_settled" : "probe_execution_failed"; }
} finally {
  if (page && status !== "passed") {
    const state = await page.evaluate(() => ({
      signed_out: [...document.querySelectorAll("h1,h2")].some(node => node.textContent === "Sign in"),
      visibility: document.visibilityState,
      local_service_unavailable: [...document.querySelectorAll("h1")].some(node => node.textContent === "Local service unavailable"),
      connecting: document.querySelector("main.auth-stage[role=status]") !== null,
      account_loading: [...document.querySelectorAll("p[role=status]")].some(node => node.textContent === "Reading monitored accounts…"),
      account_error: [...document.querySelectorAll("p[role=alert]")].some(node => ["Accounts could not be loaded from the local service.", "The local account registry is unavailable."].includes(node.textContent)),
      financial_panel_present: document.getElementById("budget-account-title") !== null,
      financial_panel_busy: document.querySelector('[aria-labelledby="budget-account-title"]')?.getAttribute("aria-busy") === "true",
      alert_visible: document.querySelector('[role="alert"]') !== null,
      invalid_selection: new URL(location.href).searchParams.has("budget_selection"),
      cloud_collect_buttons: [...document.querySelectorAll("[data-cloud-collect-resource] button")]
        .filter(node => ["Collect usage", "Refresh usage status", "Retry usage request"].includes(node.textContent))
        .map(node => ({ label: node.textContent, disabled: node.disabled })),
      cloud_context_changed: document.body.textContent.includes("The account, cloud target or selected interval changed. Refresh view before collecting."),
      cloud_previous_authority_changed: document.body.textContent.includes("The account, credential or cloud target changed. The previous collection cannot update this view."),
      cloud_result_unconfirmed: document.body.textContent.includes("The collection result is not confirmed. Refresh usage status to reconcile the existing request."),
    })).catch(() => null);
    renderDiagnostic = { ...renderDiagnostic, page_state: state };
  }
  if (page) await page.close().catch(() => { status = "failed"; reason = "probe_page_cleanup_failed"; });
}
console.log(JSON.stringify({ record_type: "agentmonitor.m7_cloud_collect_probe.v1", expected_revision: expectedRevision, run: runWitness, report: reportWitness, status, reason, stage, error_kind: errorKind, read_failure: readFailure, render_diagnostic: renderDiagnostic, response_diagnostics: responseDiagnostics, failed_requests: failedRequests, revision, scope: collect ? "one_real_cloud_usage_action" : "cloud_usage_read_only_controls", range: rangeKey, grouping, model_facts: modelFacts, usage_scope: usageScope, checks, posts, unsafe }));
process.exit(status === "passed" ? 0 : status === "blocked" ? 3 : 1);
