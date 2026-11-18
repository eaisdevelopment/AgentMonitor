const origin = process.argv[2];
const expectedRevision = process.argv[3];
const installed = origin === "http://127.0.0.1:43110";
let stage = "selected_origin", page;
let mutations = 0;
const check = condition => { if (!condition) throw new Error(); };
const exact = value => {
  const coefficient = BigInt(value.coefficient);
  const digits = (coefficient < 0n ? -coefficient : coefficient).toString().padStart(value.scale + 1, "0");
  return `${coefficient < 0n ? "-" : ""}${value.scale === 0 ? digits : `${digits.slice(0, -value.scale)}.${digits.slice(-value.scale)}`} ${value.currency ?? value.unit}`;
};
try {
  check(/^http:\/\/127\.0\.0\.1:\d+$/.test(origin ?? ""));
  check(installed ? /^[a-f0-9]{40}$/.test(expectedRevision ?? "") : expectedRevision === undefined);
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
  const { chromium } = playwright;
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9225", { timeout: 5000 });
  const context = browser.contexts().find(item => item.pages().some(tab => tab.url().startsWith("http://127.0.0.1:43110/")));
  check(context !== undefined);
  page = await context.newPage();
  page.setDefaultTimeout(10000);
  page.on("request", request => { if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) mutations++; });
  async function read(path) {
    const response = await page.request.get(`${origin}${path}`, { headers: { Origin: origin } });
    check(response.ok());
    return response.json();
  }
  if (installed) {
    stage = "installed_revision";
    check((await read("/api/v1/operations/versions")).source_revision?.value === expectedRevision);
    stage = "installed_genuine_report";
    const now = new Date();
    const end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
    const overviewQuery = new URLSearchParams({ provider_key: "ollama", limit: "200", as_of: now.toISOString(),
      period_start: new Date(end.getTime() - 7 * 86400000).toISOString(), period_end: end.toISOString() });
    let row, current, overview;
    const seen = new Set();
    for (let index = 0; index < 100; index++) {
      overview = await read(`/api/v1/budgets?${overviewQuery}`);
      row = overview.items.find(item => item.resource_id != null && item.contexts.some(value => value.spend != null && value.currency != null && value.completeness === "complete"));
      if (row) { current = row.contexts.find(value => value.spend != null && value.currency != null && value.completeness === "complete"); break; }
      if (!overview.page.has_more) break;
      check(typeof overview.page.next_cursor === "string" && !seen.has(overview.page.next_cursor));
      seen.add(overview.page.next_cursor); overviewQuery.set("cursor", overview.page.next_cursor);
    }
    check(row !== undefined && current !== undefined);
    selection = { account_id: current.report_account_id ?? row.account.account_id,
      resource_id: current.report_resource_id ?? row.resource_id, as_of: overview.as_of,
      period_start: overview.period.start, period_end: overview.period.end, report_id: current.report_id };
  }
  const query = new URLSearchParams(selection);
  query.delete("resource_id");
  stage = "genuine_report_metadata";
  const resource = encodeURIComponent(selection.resource_id);
  check(typeof selection.report_id === "string");
  const report = { report_id: selection.report_id };
  const full = await read(`/api/v1/budgets/${resource}?${query}`);
  check(full.report.report_id === report.report_id);
  const search = new URLSearchParams({ budget_resource: selection.resource_id, budget_report: report.report_id,
    budget_start: selection.period_start, budget_end: selection.period_end, budget_as_of: selection.as_of });
  await page.goto(`${origin}/accounts/${encodeURIComponent(selection.account_id)}?${search}`, { waitUntil: "domcontentloaded" });
  stage = "authentication";
  const section = page.getByRole("region", { name: "Selected financial report", exact: true });
  const settled = () => section.locator('[data-budget-history][aria-busy="false"]').waitFor();
  await settled();
  check(await section.locator("tr[data-bucket-key]").count() > 0);
  if (full.report.usage_buckets.length > 0) {
    stage = "optional_usage_coverage_explanation_missing";
    check(await section.getByText("Usage quantities appear only where the provider reported them. Missing quantities are unknown, not zero; report completeness does not imply complete token coverage.", { exact: true }).count() === 1);
  }
  stage = "history_chart_missing";
  const chart = section.getByRole("region", { name: "History chart", exact: true });
  await chart.waitFor();

  stage = "daily_totals_missing";
  const dailyRegion = section.getByRole("region", { name: "Daily cost totals", exact: true });
  await dailyRegion.waitFor();
  stage = "daily_totals_api";
  const dailyResponse = await read(`/api/v1/budgets/${resource}/history?${query}&limit=1`);
  const daily = dailyResponse.daily_costs;
  check(daily?.state === "available" && daily.items.length > 0 && daily.items.length <= 30);
  const actualSums = new Map();
  for (const bucket of full.report.cost_buckets) {
    const day = bucket.period.start;
    const current = actualSums.get(day) ?? { atoms: 0n, count: 0, adjustment: false };
    current.atoms += BigInt(bucket.amount.coefficient) * 10n ** BigInt(18 - bucket.amount.scale);
    current.count++;
    current.adjustment ||= bucket.kind === "adjustment";
    actualSums.set(day, current);
  }
  check(daily.items.filter(row => !row.derived_zero).length === actualSums.size);
  const largest = [...actualSums.values()].reduce((value, row) => {
    const absolute = row.atoms < 0n ? -row.atoms : row.atoms;
    return absolute > value ? absolute : value;
  }, 0n);
  for (const row of daily.items) {
    const source = actualSums.get(row.period.start);
    if (row.derived_zero) {
      check(source === undefined && row.source_entry_count === 0 && row.has_adjustment === false);
      check(BigInt(row.amount.coefficient) === 0n && row.chart.direction === "zero");
      check(full.report.completeness === "complete" && daily.policy_id != null && daily.policy_version != null);
    } else {
      check(source !== undefined && row.source_entry_count === source.count && row.has_adjustment === source.adjustment);
      check(BigInt(row.amount.coefficient) * 10n ** BigInt(18 - row.amount.scale) === source.atoms);
    }
    const atoms = source?.atoms ?? 0n;
    const absolute = atoms < 0n ? -atoms : atoms;
    const magnitude = largest === 0n ? 0n : (absolute * 10000n + largest - 1n) / largest;
    check(BigInt(row.chart.magnitude_basis_points) === magnitude);
  }
  async function verifyDaily() {
    stage = "daily_totals_exact_dom";
    const disclosure = dailyRegion.locator("details");
    if (await disclosure.getAttribute("open") === null) {
      await disclosure.locator("summary").focus();
      await page.keyboard.press("Enter");
    }
    const rows = dailyRegion.locator("tr[data-daily-start]");
    const bars = dailyRegion.locator("button[data-daily-start]");
    const table = await rows.evaluateAll(nodes => nodes.map(node => ({
      start: node.getAttribute("data-daily-start"), amount: node.querySelectorAll("td")[1]?.textContent,
    })));
    const plotted = await bars.evaluateAll(nodes => nodes.map(node => ({
      magnitude: node.getAttribute("data-chart-magnitude"), label: node.getAttribute("aria-label"),
    })));
    check(table.length === daily.items.length && plotted.length === daily.items.length);
    for (const [index, row] of daily.items.entries()) {
      check(table[index].start === row.period.start);
      check(table[index].amount === exact(row.amount));
      check(plotted[index].magnitude === String(row.chart.magnitude_basis_points));
      check(plotted[index].label.includes(exact(row.amount)));
      check(plotted[index].label.includes(row.period.start.slice(0, 10)));
    }
    stage = "daily_totals_keyboard";
    await bars.first().focus();
    await page.keyboard.press("Enter");
    check(await bars.first().getAttribute("aria-pressed") === "true");
    check(await dailyRegion.locator("[data-chart-selection]").textContent() === await bars.first().getAttribute("aria-label"));
    check(await dailyRegion.evaluate(node => node.scrollWidth <= node.clientWidth + 1));
  }
  await verifyDaily();

  const expected = [], seenCursors = new Set();
  let cursor;
  stage = "history_chart_actual_api";
  for (let index = 0; index < 2000; index++) {
    const current = new URLSearchParams(query);
    current.set("limit", "50");
    if (cursor !== undefined) current.set("cursor", cursor);
    const result = await read(`/api/v1/budgets/${resource}/history?${current}`);
    check(result.report.report_id === report.report_id && result.report.account_id === selection.account_id && result.report.resource_id === selection.resource_id);
    expected.push(...result.items);
    if (!result.page.has_more) { check(result.page.next_cursor === null); break; }
    cursor = result.page.next_cursor;
    check(typeof cursor === "string" && !seenCursors.has(cursor) && index < 1999);
    seenCursors.add(cursor);
  }
  const fullFacts = new Map([
    ...full.report.cost_buckets.map(item => [`cost:${item.bucket_key}`, item]),
    ...full.report.usage_buckets.map(item => [`usage:${item.bucket_key}`, item]),
  ]);
  check(expected.length === fullFacts.size && expected.some(row => row.chart != null));
  const keys = new Set();
  for (const item of expected) {
    const bucket = item.cost ?? item.usage;
    const key = `${item.kind}:${bucket.bucket_key}`;
    check(!keys.has(key)); keys.add(key);
    check(JSON.stringify(bucket) === JSON.stringify(fullFacts.get(key)));
  }

  async function verifyLoaded() {
    await verifyDaily();
    const rows = section.locator("tr[data-bucket-key]");
    const table = await rows.evaluateAll(nodes => nodes.map(node => ({
      key: `${node.dataset.bucketKind}:${node.dataset.bucketKey}`, amount: node.querySelectorAll("td")[1]?.textContent,
    })));
    const loaded = table.map(row => row.key), loadedKeys = new Set(loaded);
    const tableAmounts = new Map(table.map(row => [row.key, row.amount]));
    const facts = expected.filter(item => loadedKeys.has(`${item.kind}:${(item.cost ?? item.usage).bucket_key}`));
    check(facts.length === loaded.length && new Set(loaded).size === loaded.length);
    const series = [...new Map(facts.filter(item => item.chart != null).map(item => [item.chart.series_key, item.chart.label])).entries()];
    const selector = chart.getByRole("combobox", { name: "History chart series", exact: true });
    stage = "history_chart_series_label";
    check(await selector.evaluate(node => {
      const range = document.createRange();
      range.selectNodeContents(node.closest("label").firstChild);
      return range.getClientRects().length === 1;
    }));
    check(await selector.locator("option").count() === series.length);
    for (const [key, label] of series) {
      stage = "history_chart_series";
      await selector.selectOption(key);
      check(await selector.locator("option:checked").textContent() === label);
      const points = facts.filter(item => item.chart?.series_key === key);
      const bars = chart.locator("button[data-chart-bucket-key]");
      // React may render after selectOption resolves; await these exact series
      // identities before taking one real DOM snapshot of every visible point.
      await playwright.expect.poll(() => bars.evaluateAll(nodes => nodes.map(node =>
        `${node.getAttribute("data-chart-kind")}:${node.getAttribute("data-chart-bucket-key")}`
      ))).toEqual(points.map(item => `${item.kind}:${(item.cost ?? item.usage).bucket_key}`));
      const plotted = await bars.evaluateAll(nodes => nodes.map(node => {
        const track = node.querySelector(".budget-history-chart-track").getBoundingClientRect();
        const barNode = node.querySelector("[data-chart-bar]");
        const bar = barNode.getBoundingClientRect();
        return {
          key: node.getAttribute("data-chart-bucket-key"), kind: node.getAttribute("data-chart-kind"),
          direction: node.getAttribute("data-chart-direction"), magnitude: node.getAttribute("data-chart-magnitude"),
          label: node.getAttribute("aria-label"), text: node.textContent,
          styleMagnitude: barNode.style.getPropertyValue("--chart-magnitude"),
          geometry: { trackHeight: track.height, trackWidth: track.width, barHeight: bar.height,
            barWidth: bar.width, top: bar.top - track.top, bottom: bar.bottom - track.top },
        };
      }));
      check(plotted.length === points.length);
      for (const [index, item] of points.entries()) {
        stage = "history_chart_exact_point";
        const bucket = item.cost ?? item.usage, point = plotted[index];
        check(point.key === bucket.bucket_key);
        check(point.kind === item.kind);
        check(point.direction === item.chart.direction);
        check(point.magnitude === String(item.chart.magnitude_basis_points));
        const text = point.label;
        check(text.includes(exact(item.cost?.amount ?? item.usage.quantity)) && text.includes(bucket.period.start.slice(0, 10)) && text.includes(bucket.period.end.slice(0, 10)));
        check(point.text.includes(bucket.period.start.slice(5, 10)));
        check(point.styleMagnitude === String(item.chart.magnitude_basis_points));
        stage = "history_chart_rendered_geometry";
        const geometry = point.geometry;
        check(geometry.trackHeight > 0 && geometry.trackWidth > 0 && geometry.barWidth > 0);
        const baseline = geometry.trackHeight / 2;
        const expectedHeight = item.chart.direction === "zero" ? 2 : baseline * item.chart.magnitude_basis_points / 10000;
        check(Math.abs(geometry.barHeight - expectedHeight) <= 1);
        check(Math.abs((item.chart.direction === "positive" ? geometry.bottom : geometry.top) - baseline) <= 1);
        if (item.chart.direction === "zero" || item.chart.magnitude_basis_points === 10000) check(geometry.barHeight > 0);
        check(tableAmounts.get(`${item.kind}:${bucket.bucket_key}`) === exact(item.cost?.amount ?? item.usage.quantity));
        if (index === 0) {
          stage = "history_chart_keyboard";
          const button = bars.nth(index);
          await button.focus(); await page.keyboard.press("Enter");
          check(await button.getAttribute("aria-pressed") === "true");
          check(await chart.locator("[data-chart-selection]").textContent() === text);
        }
      }
    }
    stage = "history_chart_bounded_plot";
    check(await chart.locator("[data-chart-plot]").evaluate(node => {
      const bounds = node.getBoundingClientRect();
      return bounds.height > 0 && bounds.height <= 180 && bounds.width > 0;
    }));
    if (facts.length < expected.length) check((await chart.textContent()).includes("More history available"));
  }
  await verifyLoaded();
  for (let index = 0; index < 2000; index++) {
    const more = section.getByRole("button", { name: "Load more history", exact: true });
    if (await more.count() === 0) break;
    const beforeRows = await section.locator("tr[data-bucket-key]").count();
    const continuation = page.waitForResponse(response => {
      const address = new URL(response.url());
      return response.request().method() === "GET" && address.origin === origin &&
        address.pathname === `/api/v1/budgets/${resource}/history` &&
        address.searchParams.get("report_id") === report.report_id && address.searchParams.has("cursor");
    }).then(response => ({ response }), error => ({ error }));
    stage = "history_chart_pagination_click";
    await more.click();
    stage = "history_chart_pagination_response";
    const continued = await continuation;
    if (continued.error) throw continued.error;
    check(continued.response.ok());
    const next = await continued.response.json();
    check(next.report.report_id === report.report_id && next.report.account_id === selection.account_id &&
      next.report.resource_id === selection.resource_id && Date.parse(next.as_of) === Date.parse(selection.as_of));
    stage = "history_chart_pagination_settle";
    await playwright.expect(section.locator("tr[data-bucket-key]")).toHaveCount(beforeRows + next.items.length);
    await settled(); await verifyLoaded(); check(index < 1999);
  }
  check(await section.locator("tr[data-bucket-key]").count() === expected.length);
  stage = "history_chart_reload";
  await page.reload({ waitUntil: "domcontentloaded" }); await settled(); await verifyLoaded();
  stage = "history_chart_narrow";
  await page.setViewportSize({ width: 390, height: 844 });
  check(await chart.evaluate(node => node.scrollWidth <= node.clientWidth + 1));
  await verifyLoaded();
  stage = "read_only"; check(mutations === 0);
  console.log(`M7 HISTORY CHART BROWSER: PASSED facts=${expected.length} charted=${expected.filter(item => item.chart != null).length} api_pages=${seenCursors.size + 1} boundary=${installed ? "installed" : "isolated"}${installed ? ` revision=${expectedRevision}` : ""}`);
} catch {
  console.log(`M7 HISTORY CHART BROWSER: FAILED — ${stage}`);
  process.exitCode = 1;
} finally {
  if (page) await page.close().catch(() => {});
}
process.stdout.write("", () => process.exit(process.exitCode ?? 0));
