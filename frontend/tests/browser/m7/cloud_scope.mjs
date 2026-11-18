// Existing genuine resources, GET-only eligibility and stored readings. Never collects.
const origin = process.argv[2] ?? "http://127.0.0.1:43110", expectedRevision = process.argv[3];
let page, stage = "origin", passed = false, mutations = 0, firstTeam = false;
const check = condition => { if (!condition) throw new Error(); };
const sameTime = (left, right) => typeof left === "string" && typeof right === "string" &&
  left.replace(/(?:\.(\d{1,6}))?Z$/, (_, digits) => `.${(digits ?? "").padEnd(6, "0")}Z`) ===
  right.replace(/(?:\.(\d{1,6}))?Z$/, (_, digits) => `.${(digits ?? "").padEnd(6, "0")}Z`);
try {
  check(/^http:\/\/127\.0\.0\.1:\d+$/.test(origin));
  check(expectedRevision === undefined || /^[a-f0-9]{40}$/.test(expectedRevision));
  let playwright;
  try { playwright = await import("@playwright/test"); }
  catch (error) {
    if (error?.code !== "ERR_MODULE_NOT_FOUND") throw error;
    playwright = await import("/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules/@playwright/test/index.mjs");
  }
  stage = "browser";
  const browser = await playwright.chromium.connectOverCDP("http://127.0.0.1:9225", { timeout: 5000 });
  const context = browser.contexts().find(value => value.pages().some(tab => tab.url().startsWith("http://127.0.0.1:43110/")));
  check(context !== undefined);
  page = await context.newPage(); page.setDefaultTimeout(10000);
  page.on("request", request => { if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) mutations++; });
  async function read(path) {
    const response = await page.request.get(origin + path, { headers: { Origin: origin }, timeout: 10000 });
    if (response.status() === 401) { stage = "authentication_required"; throw new Error(); }
    check(response.ok()); return response.json();
  }
  if (expectedRevision !== undefined) {
    stage = "revision";
    check((await read("/api/v1/operations/versions")).source_revision?.value === expectedRevision);
  }
  stage = "genuine_resource";
  const now = new Date(), end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  const period = { period_start: new Date(end.getTime() - 7 * 86400000).toISOString(), period_end: end.toISOString(), as_of: now.toISOString() };
  const accounts = [], cursors = new Set();
  const inventoryQuery = new URLSearchParams({ provider_key: "ollama", limit: "200" });
  for (let index = 0; index < 100; index++) {
    const inventory = await read(`/api/v1/accounts?${inventoryQuery}`);
    check(inventory.availability.state === "available"); accounts.push(...inventory.items);
    if (!inventory.page.has_more) break;
    check(index < 99 && typeof inventory.page.next_cursor === "string" && !cursors.has(inventory.page.next_cursor));
    cursors.add(inventory.page.next_cursor); inventoryQuery.set("cursor", inventory.page.next_cursor);
  }
  check(new Set(accounts.map(value => value.account_id)).size === accounts.length);
  let chosen, fallback;
  for (const account of accounts.filter(value => value.lifecycle === "active")) {
    const summary = await read(`/api/v1/accounts/${encodeURIComponent(account.account_id)}/budgets?${new URLSearchParams(period)}`);
    for (const resource of summary.cloud_resources ?? []) {
      if (resource.lifecycle !== "active") continue;
      const candidate = { account, resource };
      fallback ??= candidate;
      if (!resource.reports.some(value => [value.current, value.latest_attempt].some(report => report?.source_category === "team_requests_and_cost"))) { chosen = candidate; break; }
    }
    if (chosen) break;
  }
  firstTeam = chosen !== undefined; chosen ??= fallback; check(chosen !== undefined);
  const { account, resource } = chosen;
  const accountPath = `/accounts/${encodeURIComponent(account.account_id)}`;
  const eligibilityPath = `/api/v1${accountPath}/cloud-usage/${encodeURIComponent(resource.resource_id)}/collection-eligibility`;
  const query = new URLSearchParams({ budget_resource: resource.resource_id, budget_start: period.period_start, budget_end: period.period_end, budget_as_of: period.as_of });
  await page.goto(`${origin}${accountPath}?${query}`, { waitUntil: "domcontentloaded" });
  const panel = page.locator('[aria-labelledby="budget-account-title"]');
  await panel.locator(':scope[aria-busy="false"]').waitFor();
  await panel.getByRole("region", { name: "Collect cloud usage", exact: true }).waitFor();
  stage = "cloud_scope_selector_missing";
  const scope = panel.getByRole("combobox", { name: "Usage scope", exact: true });
  await scope.waitFor();
  check(await scope.locator('option[value="self"]').count() === 1 && await scope.locator('option[value="team"]').count() === 1);
  async function eligibilityAfter(action, selectedScope, range) {
    const responsePromise = page.waitForResponse(response => {
      const url = new URL(response.url());
      return response.request().method() === "GET" && url.pathname === eligibilityPath &&
        url.searchParams.get("scope") === selectedScope && url.searchParams.get("range_key") === range;
    }).then(response => ({ response }), error => ({ error }));
    await action();
    const observed = await responsePromise; if (observed.error) throw observed.error;
    check(observed.response.ok());
    const result = await observed.response.json(), url = new URL(page.url());
    check(result.account_id === account.account_id && result.resource_id === resource.resource_id);
    check(result.report_context.scope === selectedScope && result.report_context.range_key === range);
    check(sameTime(result.report_context.interval_start, url.searchParams.get("budget_start")) && sameTime(result.report_context.interval_end, url.searchParams.get("budget_end")));
    check(url.searchParams.get("budget_scope") === selectedScope && url.searchParams.get("budget_resource") === resource.resource_id);
    check(!url.searchParams.has("budget_report") && !url.searchParams.has("budget_selection"));
    check(await scope.inputValue() === selectedScope);
    check((await panel.getByRole("region", { name: "Collect cloud usage", exact: true }).textContent()).includes(`Collect ${selectedScope} usage`));
  }
  stage = "team_eligibility";
  await eligibilityAfter(() => scope.selectOption("team"), "team", "7d");
  stage = "team_reports";
  async function verifyReports() {
    await panel.locator(':scope[aria-busy="false"]').waitFor();
    const current = new URL(page.url()).searchParams;
    const summary = await read(`/api/v1${accountPath}/budgets?${new URLSearchParams({ period_start: current.get("budget_start"), period_end: current.get("budget_end"), as_of: current.get("budget_as_of") })}`);
    const actual = summary.cloud_resources.find(value => value.resource_id === resource.resource_id); check(actual !== undefined);
    const reports = actual.reports.map(value => value.current ?? value.latest_attempt).filter(value => value?.source_category === "team_requests_and_cost");
    const reading = panel.locator('[data-cloud-reading][data-usage-scope="team"]');
    await reading.waitFor();
    const ids = await reading.locator("section[data-report-id]").evaluateAll(nodes => nodes.map(node => node.getAttribute("data-report-id")));
    check(JSON.stringify(ids.sort()) === JSON.stringify(reports.map(value => value.report_id).sort()));
    if (reports.length === 0) check((await reading.textContent()).includes("No retained team report for this interval."));
  }
  await verifyReports();
  stage = "team_reload";
  await eligibilityAfter(() => page.reload({ waitUntil: "domcontentloaded" }), "team", "7d"); await verifyReports();
  stage = "team_thirty_days";
  await eligibilityAfter(() => panel.getByRole("combobox", { name: "Report range", exact: true }).selectOption("30"), "team", "30d"); await verifyReports();
  stage = "team_refresh";
  await panel.getByRole("button", { name: "Refresh view", exact: true }).click();
  await panel.locator(':scope[aria-busy="false"]').waitFor();
  check(new URL(page.url()).searchParams.get("budget_scope") === "team"); await verifyReports();
  stage = "read_only"; check(mutations === 0);
  passed = true; console.log(`M7 CLOUD SCOPE BROWSER: PASSED first_team=${firstTeam} mutations=0`);
} catch {
  console.log(`M7 CLOUD SCOPE BROWSER: FAILED — ${stage}`);
} finally {
  if (page) await page.close().catch(() => { passed = false; });
}
process.stdout.write("", () => process.exit(passed ? 0 : 1));
