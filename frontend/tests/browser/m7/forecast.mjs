const origin = process.argv[2], expectedRevision = process.argv[3];
const installed = origin === "http://127.0.0.1:43110";
let page, denialSession, stage = "origin", mutations = 0, forecastReads = 0, historyPages = 0, rateAvailable = false;
let status = "failed";
const renderedPaths = [];
const requestDiagnostics = [];
let errorKind = null;
let detailDiagnostic = null;
let paginationDiagnostic = null;
let denialDiagnostic = null;
const check = condition => { if (!condition) throw new Error(); };
const instant = value => value.replace(/(?:\.(\d{1,6}))?Z$/, (_, fraction) => `.${(fraction ?? "").padEnd(6, "0")}Z`);
const exact = value => {
  const number = BigInt(value.coefficient), digits = (number < 0n ? -number : number).toString().padStart(value.scale + 1, "0");
  return `${number < 0n ? "-" : ""}${value.scale === 0 ? digits : `${digits.slice(0, -value.scale)}.${digits.slice(-value.scale)}`} ${value.currency}`;
};
const atoms = value => BigInt(value.coefficient) * 10n ** BigInt(18 - value.scale);
try {
  check(/^http:\/\/127\.0\.0\.1:\d+$/.test(origin ?? ""));
  check(expectedRevision === undefined || (installed && /^[a-f0-9]{40}$/.test(expectedRevision)));
  let selection;
  if (!installed) {
    let input = "";
    for await (const part of process.stdin) input += part;
    selection = JSON.parse(input);
  }
  let playwright;
  try { playwright = await import("@playwright/test"); }
  catch (error) {
    if (error?.code !== "ERR_MODULE_NOT_FOUND") throw error;
    playwright = await import("/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules/@playwright/test/index.mjs");
  }
  stage = "browser_connect";
  const browser = await playwright.chromium.connectOverCDP("http://127.0.0.1:9225", { timeout: 15000 });
  stage = "browser_context";
  const context = browser.contexts().find(value => value.pages().some(tab => tab.url().startsWith("http://127.0.0.1:43110/")));
  check(context !== undefined);
  stage = "browser_page";
  page = await context.newPage(); page.setDefaultTimeout(10000);
  page.on("request", request => {
    if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) mutations++;
    if (request.method() === "GET") {
      const path = new URL(request.url()).pathname;
      renderedPaths.push(path);
      if (/\/budgets\/[^/]+\/forecast$/.test(path)) forecastReads++;
    }
  });
  async function read(path) {
    const started = Date.now();
    const family = /\/forecast(?:\?|$)/.test(path) ? "forecast"
      : /\/reports(?:\?|$)/.test(path) ? "report_list"
      : path.startsWith("/api/v1/operations/") ? "version"
      : /^\/api\/v1\/budgets\?/.test(path) ? "overview" : "selected_report";
    let response;
    try {
      response = await page.request.get(origin + path, { headers: { Origin: origin }, timeout: 10000 });
      requestDiagnostics.push({ family, status: response.status(), elapsed_ms: Date.now() - started });
    } catch (error) {
      requestDiagnostics.push({ family, status: null, elapsed_ms: Date.now() - started });
      throw error;
    }
    if (response.status() === 401) { stage = "authentication_required"; throw new Error(); }
    check(response.ok()); return response.json();
  }
  if (installed) {
    stage = "installed_revision";
    const version = await read("/api/v1/operations/versions");
    if (expectedRevision !== undefined) check(version.source_revision?.value === expectedRevision);
    stage = "genuine_monetary_selection";
    const now = new Date(), end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
    const query = new URLSearchParams({ period_start: new Date(end.getTime() - 7 * 86400000).toISOString(), period_end: end.toISOString(), as_of: now.toISOString(), limit: "200" });
    const cursors = new Set();
    let revision;
    for (let index = 0; index < 100; index++) {
      const overview = await read(`/api/v1/budgets?${query}`);
      revision ??= overview.registry_revision;
      check(revision === overview.registry_revision);
      for (const row of overview.items) {
        const report = row.contexts.find(value => value.spend !== null && value.currency !== null && value.completeness === "complete");
        if (report) { selection = { account_id: report.report_account_id ?? row.account.account_id, resource_id: report.report_resource_id ?? row.resource_id,
          report_id: report.report_id, period_start: overview.period.start, period_end: overview.period.end, as_of: overview.as_of }; break; }
      }
      if (selection || !overview.page.has_more) break;
      check(typeof overview.page.next_cursor === "string" && !cursors.has(overview.page.next_cursor));
      cursors.add(overview.page.next_cursor); query.set("cursor", overview.page.next_cursor);
    }
    check(selection?.resource_id != null);
  }
  const resource = encodeURIComponent(selection.resource_id);
  const query = new URLSearchParams(selection); query.delete("resource_id");
  if (!selection.report_id) {
    stage = "genuine_report_discovery";
    const cursors = new Set();
    const discoveryQuery = new URLSearchParams(query); discoveryQuery.set("limit", "50");
    for (let index = 0; index < 200; index++) {
      const batch = await read(`/api/v1/budgets/${resource}/reports?${discoveryQuery}`);
      const found = batch.items.find(report => report.currency !== null && report.cost_bucket_count > 0 && report.completeness === "complete" && report.grouping.length === 0);
      if (found) { query.set("report_id", found.report_id); break; }
      if (!batch.page.has_more) break;
      check(typeof batch.page.next_cursor === "string" && !cursors.has(batch.page.next_cursor));
      cursors.add(batch.page.next_cursor); discoveryQuery.set("cursor", batch.page.next_cursor);
    }
  }
  check(query.has("report_id"));
  stage = "genuine_monetary_report";
  const selected = await read(`/api/v1/budgets/${resource}?${query}`);
  check(selected.report.report_id === query.get("report_id") && selected.report.cost_buckets.length > 0 && selected.report.currency !== null);
  const search = new URLSearchParams({ budget_resource: selection.resource_id, budget_report: selected.report.report_id,
    budget_start: selection.period_start, budget_end: selection.period_end, budget_as_of: selection.as_of });
  await page.goto(`${origin}/accounts/${encodeURIComponent(selection.account_id)}?${search}`, { waitUntil: "domcontentloaded" });
  const section = page.getByRole("region", { name: "Selected financial report", exact: true });
  await section.locator('[data-budget-history][aria-busy="false"]').waitFor();
  check(await section.getByRole("region", { name: "Exact cost history", exact: true }).locator("tbody tr").count() > 0);
  stage = "observed_rate_missing";
  const rate = section.getByRole("region", { name: "Observed spending rate", exact: true });
  await rate.waitFor();
  stage = "forecast_api";
  const expected = await read(`/api/v1/budgets/${resource}/forecast?${query}`);
  check(expected.report.account_id === selection.account_id && expected.report.resource_id === selection.resource_id && expected.report.report_id === selected.report.report_id);
  check(instant(expected.as_of) === instant(selection.as_of));
  for (const field of ["scope_id", "scope_generation", "scope_evidence", "source_id", "source_category", "cost_basis", "currency"]) check(expected.report[field] === selected.report[field]);
  check(instant(expected.report.requested_period.start) === instant(selection.period_start) && instant(expected.report.requested_period.end) === instant(selection.period_end));
  check(!("cost_buckets" in expected.report) && !("usage_buckets" in expected.report));
  stage = "qualified_numeric_rate_required";
  check(expected.rate !== null);
  check(selected.report.completeness === "complete" && selected.report.covered_period !== null);
  check(instant(selected.report.covered_period.start) === instant(selected.report.requested_period.start) && instant(selected.report.covered_period.end) === instant(selected.report.requested_period.end));
  check(JSON.stringify(expected.rate.input_report_ids) === JSON.stringify([selected.report.report_id]));
  check(expected.rate.cost.currency === selected.report.currency);
  const facts = expected.rate.input_bucket_keys.map(key => selected.report.cost_buckets.find(bucket => bucket.bucket_key === key));
  check(facts.length > 0 && facts.every(Boolean) && new Set(expected.rate.input_bucket_keys).size === facts.length);
  check(facts.every(bucket => bucket.amount.currency === expected.rate.cost.currency && bucket.kind !== "adjustment" && BigInt(bucket.amount.coefficient) >= 0n));
  stage = "qualified_consecutive_daily_coverage";
  const DAY = 86400000;
  const midnight = value => /^\d{4}-\d{2}-\d{2}T00:00:00(?:\.0{1,6})?Z$/.test(value) && Number.isFinite(Date.parse(value));
  check(facts.every(bucket => midnight(bucket.period.start) && midnight(bucket.period.end) && Date.parse(bucket.period.end) - Date.parse(bucket.period.start) === DAY));
  const days = [...new Set(facts.map(bucket => Date.parse(bucket.period.start)))].sort((a, b) => a - b);
  check(days.length >= 3 && days.length <= 7 && days.every((day, index) => index === 0 || day - days[index - 1] === DAY));
  check(midnight(expected.rate.period.start) && midnight(expected.rate.period.end));
  check(Date.parse(expected.rate.period.start) === days[0] && Date.parse(expected.rate.period.end) === days[days.length - 1] + DAY);
  check(expected.rate.day_count === days.length && expected.rate.covered_seconds === days.length * 86400);
  check(Date.parse(expected.rate.period.start) >= Date.parse(selected.report.covered_period.start) && Date.parse(expected.rate.period.end) <= Date.parse(selected.report.covered_period.end));
  // All source facts inside the reported sample must contribute; checking the
  // returned numerator alone could conceal an omitted same-day cost entry.
  const sampleFacts = selected.report.cost_buckets.filter(bucket => Date.parse(bucket.period.start) >= days[0] && Date.parse(bucket.period.end) <= days[days.length - 1] + DAY);
  check(sampleFacts.length === facts.length && sampleFacts.every(bucket => expected.rate.input_bucket_keys.includes(bucket.bucket_key)));
  check(facts.reduce((sum, bucket) => sum + atoms(bucket.amount), 0n) === atoms(expected.rate.cost));
  rateAvailable = true;
  async function verifyRate() {
    stage = "forecast_render_settle";
    await section.locator('[data-budget-rate][aria-busy="false"]').waitFor();
    stage = "forecast_context";
    check(await rate.getAttribute("data-budget-rate") === expected.report.report_id && instant(await rate.getAttribute("data-rate-as-of")) === instant(expected.as_of));
    const text = await rate.textContent();
    stage = "forecast_exact_display";
    check(text.includes(expected.rate.display_text ?? `${exact(expected.rate.cost)} / ${expected.rate.covered_seconds} seconds`));
    check(text.includes(expected.rate.period.start.slice(0, 10)) && text.includes(expected.rate.period.end.slice(0, 10)));
    const details = rate.locator("details");
    stage = "forecast_details_open";
    if ((await details.getAttribute("open")) === null) await details.locator("summary").click();
    stage = "forecast_details_visible";
    detailDiagnostic = { count: await details.count(), open: await details.getAttribute("open") !== null, visible: await details.locator("dl").isVisible() };
    await details.locator("dl").waitFor({ state: "visible" });
    stage = "forecast_details_values";
    check((await details.textContent()).includes(exact(expected.rate.cost)) && (await details.textContent()).includes(`${expected.rate.covered_seconds} seconds`));
    check((await details.textContent()).includes(expected.method_id) && (await details.textContent()).includes(expected.method_version));
    stage = "forecast_exhaustion_display";
    detailDiagnostic = { ...detailDiagnostic, expected_exhaustion_present: Object.hasOwn(expected, "exhaustion_at"), expected_exhaustion_null: expected.exhaustion_at === null, expected_exhaustion_type: typeof expected.exhaustion_at, exhaustion_elements: await rate.locator("time[data-exhaustion-at]").count() };
    check(expected.exhaustion_at === null ? text.includes(expected.exhaustion_reason.replaceAll("_", " "))
      : await rate.locator("time[data-exhaustion-at]").getAttribute("datetime") === expected.exhaustion_at);
  }
  await verifyRate();
  check(forecastReads === 1);
  const readsBeforePages = forecastReads;
  for (let index = 0; index < 200; index++) {
    const more = section.getByRole("button", { name: "Load more history", exact: true });
    if (await more.count() === 0) break;
    stage = "forecast_history_pagination_click";
    const beforeRows = await section.locator("[data-bucket-key]").count();
    const continuation = page.waitForResponse(response => {
      const address = new URL(response.url());
      return response.request().method() === "GET" && address.pathname === `/api/v1/budgets/${resource}/history` &&
        address.searchParams.get("report_id") === selected.report.report_id && address.searchParams.has("cursor");
    }).then(response => ({ response }), error => ({ error }));
    paginationDiagnostic = { count: await more.count(), visible: await more.isVisible(), enabled: await more.isEnabled() };
    await more.click();
    stage = "forecast_history_pagination_response";
    const continued = await continuation;
    if (continued.error) throw continued.error;
    check(continued.response.ok());
    const next = await continued.response.json();
    check(next.report.report_id === selected.report.report_id && instant(next.as_of) === instant(selection.as_of));
    stage = "forecast_history_pagination_settle";
    // React's loading effect can run after click resolves. Wait for the actual
    // continuation's rows, not the previous render's transient aria-busy=false.
    await playwright.expect(section.locator("[data-bucket-key]")).toHaveCount(beforeRows + next.items.length);
    await section.locator('[data-budget-history][aria-busy="false"]').waitFor(); historyPages++;
    check(index < 199);
  }
  check(forecastReads === readsBeforePages); await verifyRate();
  stage = "forecast_reload";
  await page.reload({ waitUntil: "domcontentloaded" }); await verifyRate();
  const reloaded = await read(`/api/v1/budgets/${resource}/forecast?${query}`);
  check(JSON.stringify(reloaded) === JSON.stringify(expected));
  check(!renderedPaths.includes(`/api/v1/budgets/${resource}`));
  // Deny one real browser transport request only on this disposable probe tab.
  // No response is supplied and no provider failure is simulated. The existing
  // installed service and all other tabs continue serving ordinary reads.
  stage = "forecast_read_error_baseline";
  const history = section.locator('[data-budget-history]');
  await section.locator('[data-budget-history][aria-busy="false"]').waitFor();
  async function retainedFinancialState() {
    return history.evaluate(node => ({
      report: node.getAttribute("data-budget-history"),
      summary: [...node.children].filter(child => child.tagName === "P").map(child => ({
        text: child.textContent, exact: [...child.querySelectorAll('[title]')].map(value => value.getAttribute("title")),
      })),
      rows: [...node.querySelectorAll('[data-bucket-key]')].map(row => ({
        key: row.getAttribute("data-bucket-key"), kind: row.getAttribute("data-bucket-kind"),
        cells: [...row.querySelectorAll('td')].map(cell => cell.textContent),
      })),
    }));
  }
  const retained = await retainedFinancialState(), pinnedUrl = page.url();
  check(retained.report === selected.report.report_id && retained.rows.length > 0);
  const costRows = retained.rows.filter(row => row.kind === "cost");
  check(costRows.length > 0 && costRows.every(row => {
    const source = selected.report.cost_buckets.find(value => value.bucket_key === row.key);
    return source !== undefined && row.cells[1] === exact(source.amount);
  }));
  check(selected.reported_spend.total !== null && retained.summary.some(value => value.exact.includes(exact(selected.reported_spend.total))));
  function matchesForecastAddress(url, method) {
    const address = new URL(url);
    return method === "GET" && address.origin === origin &&
      address.pathname === `/api/v1/budgets/${resource}/forecast` &&
      ["account_id", "report_id"].every(key => address.searchParams.get(key) === query.get(key)) &&
      ["period_start", "period_end", "as_of"].every(key => address.searchParams.get(key) !== null &&
        instant(address.searchParams.get(key)) === instant(query.get(key)));
  }
  const matchesForecast = request => matchesForecastAddress(request.url(), request.method());
  denialSession = await context.newCDPSession(page);
  const deniedRequestIds = new Set();
  let transportFailure = null;
  denialSession.on("Network.requestWillBeSent", event => {
    if (matchesForecastAddress(event.request.url, event.request.method)) deniedRequestIds.add(event.requestId);
  });
  denialSession.on("Network.loadingFailed", event => {
    if (deniedRequestIds.has(event.requestId)) transportFailure = {
      error: event.errorText, blocked_reason: event.blockedReason ?? null,
    };
  });
  await denialSession.send("Network.enable");
  await denialSession.send("Network.setBlockedURLs", { urls: [`${origin}/api/v1/budgets/${resource}/forecast?*`] });
  stage = "forecast_browser_request_denied";
  const deniedRead = page.waitForEvent("requestfailed", { predicate: matchesForecast })
    .then(request => ({ request }), error => ({ error }));
  await page.reload({ waitUntil: "domcontentloaded" });
  stage = "forecast_denied_request_event";
  const denied = await deniedRead;
  if (denied.error) throw denied.error;
  stage = "forecast_denied_transport_event";
  await playwright.expect.poll(() => transportFailure).not.toBeNull();
  denialDiagnostic = { playwright_error: denied.request.failure()?.errorText ?? null,
    transport: transportFailure, exact_context: matchesForecast(denied.request) };
  // CDP identifies this failure by blockedReason; this Chrome build leaves
  // errorText empty. Require the matched failed request and inspector denial.
  check(transportFailure.blocked_reason === "inspector" && denialDiagnostic.exact_context);
  stage = "forecast_read_error_retains_financial_state";
  await rate.getByRole("alert").waitFor();
  check((await rate.getByRole("alert").textContent()).includes("Spend, balances and history remain unchanged."));
  await section.locator('[data-budget-rate][aria-busy="false"]').waitFor();
  await section.locator('[data-budget-history][aria-busy="false"]').waitFor();
  check(page.url() === pinnedUrl && JSON.stringify(await retainedFinancialState()) === JSON.stringify(retained));
  check(await rate.getAttribute("data-budget-rate") === selected.report.report_id &&
    instant(await rate.getAttribute("data-rate-as-of")) === instant(selection.as_of));
  stage = "forecast_retry_same_selection";
  await denialSession.send("Network.setBlockedURLs", { urls: [] });
  const readsBeforeRetry = forecastReads;
  const retriedRead = page.waitForResponse(response => matchesForecast(response.request()))
    .then(response => ({ response }), error => ({ error }));
  await rate.getByRole("button", { name: "Retry analysis", exact: true }).click();
  const retried = await retriedRead;
  if (retried.error) throw retried.error;
  check(retried.response.ok() && JSON.stringify(await retried.response.json()) === JSON.stringify(expected));
  await playwright.expect(rate.getByRole("button", { name: "Retry analysis", exact: true })).toHaveCount(0);
  await verifyRate();
  check(forecastReads === readsBeforeRetry + 1 && await rate.getByRole("alert").count() === 0);
  check(await rate.getByRole("button", { name: "Retry analysis", exact: true }).count() === 0);
  check(page.url() === pinnedUrl && JSON.stringify(await retainedFinancialState()) === JSON.stringify(retained));
  stage = "read_only"; check(mutations === 0);
  status = "passed";
  console.log(`M7 FORECAST BROWSER: PASSED rate_available=${rateAvailable} history_continuations=${historyPages} read_error_retry=passed error_boundary=browser_request_denial`);
} catch (error) {
  errorKind = error?.name === "TimeoutError" || /timeout/i.test(error?.message ?? "") ? "timeout" : "assertion_or_error";
  console.log(`M7 FORECAST BROWSER: FAILED — ${stage}`);
  console.log(JSON.stringify({ error_kind: errorKind, details: detailDiagnostic, pagination: paginationDiagnostic, denial: denialDiagnostic, actionability: { intercepted: /intercepts pointer events/.test(error?.message ?? ""), unstable: /not stable/.test(error?.message ?? ""), outside_viewport: /outside of the viewport/.test(error?.message ?? ""), hidden: /not visible/.test(error?.message ?? "") }, requests: requestDiagnostics.slice(-10) }));
} finally {
  if (denialSession) {
    await denialSession.send("Network.setBlockedURLs", { urls: [] }).catch(() => { status = "failed"; });
    await denialSession.detach().catch(() => { status = "failed"; });
  }
  if (page) await page.close().catch(() => { status = "failed"; });
}
process.stdout.write("", () => process.exit(status === "passed" ? 0 : 1));
