// Immutable genuine model history only: no collection, configuration or replay.
import { chromium, expect } from "@playwright/test";

const origin = process.argv[2];
let page, stage = "private_origin", passed = false, mutations = 0, forecastReads = 0;
let rows = 0, costs = 0, usage = 0, models = 0, remainders = 0, seriesCount = 0, continued = false, reloadVerified = false;
let failureLine = null, errorKind = null;
const check = value => { if (!value) throw new Error(); };
const instant = value => value.replace("+00:00", "Z").replace(/(?:\.(\d{1,6}))?Z$/, (_, digits) => `.${(digits ?? "").padEnd(6, "0")}Z`);
const exact = amount => {
  const coefficient = BigInt(amount.coefficient);
  const digits = (coefficient < 0n ? -coefficient : coefficient).toString().padStart(amount.scale + 1, "0");
  return `${coefficient < 0n ? "-" : ""}${amount.scale === 0 ? digits : `${digits.slice(0, -amount.scale)}.${digits.slice(-amount.scale)}`} ${amount.currency ?? amount.unit}`;
};
const periodText = period => `${period.start.slice(0, 10)} to ${period.end.slice(0, 10)} UTC (end exclusive)`;
try {
  check(/^http:\/\/127\.0\.0\.1:\d+$/.test(origin) && new URL(origin).port !== "43110");
  let input = "";
  for await (const part of process.stdin) input += part;
  const selection = JSON.parse(input);
  check(["self_requests_and_cost", "team_requests_and_cost"].includes(selection.source_category));
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9225", { timeout: 15000 });
  const context = browser.contexts().find(value => value.pages().some(tab => tab.url().startsWith("http://127.0.0.1:43110/")));
  check(context !== undefined);
  page = await context.newPage(); page.setDefaultTimeout(10000);
  page.on("request", request => {
    if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) mutations++;
    const url = new URL(request.url());
    if (url.pathname.endsWith("/forecast") && url.searchParams.get("report_id") === selection.report_id) forecastReads++;
  });
  const query = new URLSearchParams({ budget_resource: selection.resource_id, budget_report: selection.report_id,
    budget_scope: selection.source_category === "self_requests_and_cost" ? "self" : "team", budget_grouping: "model",
    budget_start: selection.period_start.replace("+00:00", "Z"), budget_end: selection.period_end.replace("+00:00", "Z"),
    budget_as_of: selection.as_of.replace("+00:00", "Z") });
  const url = `${origin}/accounts/${encodeURIComponent(selection.account_id)}?${query}`;
  const path = `/api/v1/budgets/${encodeURIComponent(selection.resource_id)}`;
  const matches = response => new URL(response.url()).pathname === `${path}/history` && response.request().method() === "GET";
  const firstResponse = page.waitForResponse(matches).then(response => ({ response }), error => ({ error }));
  stage = "genuine_model_history";
  await page.goto(url, { waitUntil: "domcontentloaded" });
  const first = await firstResponse; if (first.error) throw first.error;
  stage = "immutable_model_report";
  const selectedQuery = new URLSearchParams({ account_id: selection.account_id, report_id: selection.report_id,
    period_start: query.get("budget_start"), period_end: query.get("budget_end"), as_of: query.get("budget_as_of") });
  const response = await context.request.get(`${origin}${path}?${selectedQuery}`, { headers: { Origin: origin } });
  check(response.ok());
  const full = await response.json(), report = full.report;
  const matchesReport = value => value?.provider_key === "ollama" && value.account_id === selection.account_id &&
    value.resource_id === selection.resource_id && value.report_id === selection.report_id &&
    value.source_id === selection.source_id && value.source_category === selection.source_category &&
    JSON.stringify(value.grouping) === '["model"]' &&
    instant(value.requested_period.start) === instant(selection.period_start) &&
    instant(value.requested_period.end) === instant(selection.period_end);
  check(matchesReport(report) && instant(full.as_of) === instant(selection.as_of));
  check(full.reported_spend.report_id === selection.report_id && full.reported_spend.total === null);
  const facts = [...report.cost_buckets.map(bucket => ({ kind: "cost", bucket, amount: bucket.amount })),
    ...report.usage_buckets.map(bucket => ({ kind: "usage", bucket, amount: bucket.quantity }))];
  check(facts.length > 0);
  const factIdentity = value => `${value.kind}:${value.bucket.bucket_key}`;
  const expected = new Map(facts.map(value => [factIdentity(value), value]));
  check(expected.size === facts.length);
  const history = page.locator('[data-budget-history]');
  const readPage = async (response, cursor) => {
    check(response.ok());
    const params = new URL(response.url()).searchParams;
    check(params.get("account_id") === selection.account_id && params.get("report_id") === selection.report_id &&
      params.get("limit") === "50" && params.get("cursor") === cursor);
    for (const key of ["period_start", "period_end", "as_of"]) check(instant(params.get(key)) === instant(selection[key]));
    const data = await response.json();
    check(matchesReport(data.report) && instant(data.as_of) === instant(selection.as_of) &&
      data.reported_spend.report_id === selection.report_id && data.reported_spend.total === null);
    check(data.page.has_more === (data.page.next_cursor !== null));
    for (const item of data.items) {
      const bucket = item.kind === "cost" ? item.cost : item.usage;
      check(JSON.stringify(expected.get(`${item.kind}:${bucket.bucket_key}`)?.bucket) === JSON.stringify(bucket));
    }
    return data;
  };
  const verify = async initial => {
    stage = "model_history_page_identity";
    let data = await readPage(initial, null), items = [...data.items], pages = 1;
    await expect(history).toHaveAttribute("data-budget-history", selection.report_id);
    await expect(history).toHaveAttribute("aria-busy", "false");
    while (data.page.has_more) {
      check(pages < 40);
      const nextResponse = page.waitForResponse(matches).then(response => ({ response }), error => ({ error }));
      await history.getByRole("button", { name: "Load more history", exact: true }).click();
      const next = await nextResponse; if (next.error) throw next.error;
      data = await readPage(next.response, data.page.next_cursor);
      items.push(...data.items); pages++; continued = true;
      await expect(history.locator('[data-bucket-key]')).toHaveCount(items.length);
      await expect(history).toHaveAttribute("aria-busy", "false");
    }
    check(items.length === facts.length && new Set(items.map(item => `${item.kind}:${(item.cost ?? item.usage).bucket_key}`)).size === facts.length);
    await expect(history.locator('[data-bucket-key]')).toHaveCount(facts.length);
    stage = "model_exact_table";
    for (const fact of facts) {
      check(fact.bucket.dimensions.length === 1 && fact.bucket.dimensions[0].kind === "model");
      const dimension = fact.bucket.dimensions[0];
      check(dimension.is_remainder === true ? dimension.value === null : typeof dimension.value === "string");
      const key = await page.evaluate(value => CSS.escape(value), fact.bucket.bucket_key);
      const row = history.locator(`[data-bucket-kind="${fact.kind}"][data-bucket-key="${key}"]`);
      await expect(row).toHaveCount(1);
      check(await row.getByRole("cell").nth(0).textContent() === periodText(fact.bucket.period));
      check(await row.getByRole("cell").nth(1).textContent() === exact(fact.amount));
      check(await row.getByRole("cell").last().textContent() === `Model: ${dimension.is_remainder === true ? "Provider-reported remainder" : dimension.value}`);
    }
    stage = "model_chart_series";
    const series = new Map(), dimensionsBySeries = new Map(), seriesByDimensions = new Map();
    for (const item of items) {
      if (item.chart == null) continue;
      const bucket = item.cost ?? item.usage, amount = item.cost?.amount ?? item.usage.quantity;
      const dimension = bucket.dimensions[0];
      const identity = JSON.stringify([item.kind, amount.currency ?? amount.unit, dimension.value, dimension.is_remainder === true]);
      check(!dimensionsBySeries.has(item.chart.series_key) || dimensionsBySeries.get(item.chart.series_key) === identity);
      check(!seriesByDimensions.has(identity) || seriesByDimensions.get(identity) === item.chart.series_key);
      dimensionsBySeries.set(item.chart.series_key, identity); seriesByDimensions.set(identity, item.chart.series_key);
      series.set(item.chart.series_key, item.chart.label);
    }
    const selector = history.getByRole("combobox", { name: "History chart series", exact: true });
    if (series.size) {
      await expect(selector.locator("option")).toHaveCount(series.size);
      for (const [key, label] of series) {
        await selector.selectOption(key);
        check(await selector.locator("option:checked").textContent() === label);
        const points = items.filter(item => item.chart?.series_key === key);
        await expect(history.locator('[data-chart-bucket-key]')).toHaveCount(points.length);
        for (const item of points) {
          const bucket = item.cost ?? item.usage;
          const escaped = await page.evaluate(value => CSS.escape(value), bucket.bucket_key);
          const point = history.locator(`[data-chart-kind="${item.kind}"][data-chart-bucket-key="${escaped}"]`);
          await expect(point).toHaveAttribute("data-chart-direction", item.chart.direction);
          await expect(point).toHaveAttribute("data-chart-magnitude", String(item.chart.magnitude_basis_points));
          check((await point.getAttribute("aria-label")).includes(label));
        }
      }
    } else await expect(selector).toHaveCount(0);
    seriesCount = series.size;
    await expect(history.getByRole("region", { name: "Observed spending rate", exact: true })).toHaveCount(0);
    check(!(await history.textContent()).includes("Reported spend:") && forecastReads === 0 && mutations === 0);
    check(page.url() === url);
  };
  await verify(first.response);
  stage = "model_reload";
  const reloadedResponse = page.waitForResponse(matches).then(response => ({ response }), error => ({ error }));
  await page.reload({ waitUntil: "domcontentloaded" });
  const reloaded = await reloadedResponse; if (reloaded.error) throw reloaded.error;
  await verify(reloaded.response);
  reloadVerified = true;
  rows = facts.length; costs = report.cost_buckets.length; usage = report.usage_buckets.length;
  models = new Set(facts.map(fact => fact.bucket.dimensions[0]).filter(dimension => dimension.is_remainder !== true).map(dimension => dimension.value)).size;
  remainders = facts.filter(fact => fact.bucket.dimensions[0].is_remainder === true).length;
  passed = true;
} catch (error) {
  // Own source line and closed class only; no financial values or identifiers.
  const locations = [...String(error?.stack ?? "").matchAll(/model_history\.mjs:(\d+):\d+/g)];
  failureLine = locations.length ? Number(locations[Math.min(1, locations.length - 1)][1]) : null;
  errorKind = error?.name === "TimeoutError" ? "timeout" : "assertion_or_runtime";
}
finally { if (page) await page.close().catch(() => { passed = false; }); }
console.log(JSON.stringify({ status: passed ? "passed" : "failed", stage, rows, costs, usage, named_models: models,
  failure_line: failureLine, error_kind: errorKind,
  remainder_rows: remainders, chart_series: seriesCount, continuation_exercised: continued,
  monetary_mapping: costs > 0 ? "observed" : "not_observed", remainder_mapping: remainders > 0 ? "observed" : "not_observed",
  reload_verified: reloadVerified, mutations }));
process.stdout.write("", () => process.exit(passed ? 0 : 1));
