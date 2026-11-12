// Read-only built UI over a private genuine-data service. Metadata setup belongs
// to the isolated Python harness; this probe never writes accounts or telemetry.
const origin = process.argv[2];
let page, stage = "isolated_origin", mutations = 0, filters = 0, continuations = 0, links = 0;
const check = value => { if (!value) throw new Error(); };
const instant = value => value.replace("+00:00", "Z").replace(/(?:\.(\d{1,6}))?Z$/, (_, fraction) => `.${(fraction ?? "").padEnd(6, "0")}Z`);
const atoms = value => {
  check(value !== null && /^-?\d+$/.test(value.coefficient) && Number.isInteger(value.scale) && value.scale >= 0 && value.scale <= 18);
  return BigInt(value.coefficient) * 10n ** BigInt(18 - value.scale);
};
const exact = value => {
  const number = BigInt(value.coefficient), digits = (number < 0n ? -number : number).toString().padStart(value.scale + 1, "0");
  return `${number < 0n ? "-" : ""}${value.scale === 0 ? digits : `${digits.slice(0, -value.scale)}.${digits.slice(-value.scale)}`} ${value.currency}`;
};
try {
  check(/^http:\/\/127\.0\.0\.1:\d+$/.test(origin ?? "") && origin !== "http://127.0.0.1:43110");
  let input = "";
  for await (const part of process.stdin) input += part;
  const packet = JSON.parse(input);
  check(["distinct", "shared", "unlinked"].includes(packet.phase) && packet.sources.length === 2);
  let playwright;
  try { playwright = await import("@playwright/test"); }
  catch (error) {
    if (error?.code !== "ERR_MODULE_NOT_FOUND") throw error;
    playwright = await import("/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules/@playwright/test/index.mjs");
  }
  stage = "authenticated_context";
  const browser = await playwright.chromium.connectOverCDP("http://127.0.0.1:9225", { timeout: 5000 });
  const context = browser.contexts().find(item => item.pages().some(tab => tab.url().startsWith("http://127.0.0.1:43110/")));
  check(context !== undefined);
  page = await context.newPage(); page.setDefaultTimeout(10000);
  page.on("request", request => { if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) mutations++; });
  async function read(path) {
    const response = await page.request.get(`${origin}${path}`, { headers: { Origin: origin } });
    check(response.ok()); return response.json();
  }
  const base = { period_start: packet.period_start, period_end: packet.period_end, as_of: packet.as_of };
  const reports = new Map();
  stage = "genuine_exact_sources";
  for (const source of packet.sources) {
    const query = new URLSearchParams({ ...base, account_id: source.account_id, report_id: source.report_id });
    const selected = await read(`/api/v1/budgets/${encodeURIComponent(source.resource_id)}?${query}`);
    const report = selected.report;
    check(report.report_id === source.report_id && report.account_id === source.account_id && report.resource_id === source.resource_id);
    check(report.completeness === "complete" && report.grouping.length === 0 && (report.cost_buckets.length > 0 || report.usage_buckets.length > 0));
    for (const period of [report.requested_period, report.covered_period]) check(period !== null && instant(period.start) === instant(base.period_start) && instant(period.end) === instant(base.period_end));
    check(instant(selected.as_of) === instant(base.as_of));
    const sum = report.cost_buckets.reduce((total, bucket) => { check(bucket.amount.currency === report.currency); return total + atoms(bucket.amount); }, 0n);
    if (report.currency !== null && report.cost_buckets.length > 0) check(sum === atoms(selected.reported_spend.total));
    else check(report.currency === null && report.cost_buckets.length === 0 && selected.reported_spend.total === null && selected.reported_spend.reason_code === "cost_not_reported");
    reports.set(source.report_id, { source, report, sum, total: selected.reported_spend.total });
  }
  check([...reports.values()].some(item => item.sum !== 0n));
  const selectedSources = [...reports.values()].filter(item => item.source.included);
  check(selectedSources.length === (packet.phase === "distinct" ? packet.monetary_resources : 1));
  const measure = selectedSources[0].report;
  check([...reports.values()].every(item => ["cost_basis", "source_category", "source_id"].every(key => item.report[key] === measure[key])));
  const expectedSum = selectedSources.reduce((sum, item) => sum + item.sum, 0n);
  for (const groups of [[packet.primary], [packet.secondary], [packet.primary, packet.secondary]]) {
    const counted = groups.includes(packet.primary), excluded = packet.phase === "unlinked" ? (groups.includes(packet.secondary) ? packet.excluded : 0) : (counted ? 2 - packet.monetary_resources : 0);
    const query = new URLSearchParams({ ...base, organization_ids: groups.join(","), include_ungrouped: "false", provider_key: "ollama", sort_by: packet.sort_by, sort_direction: packet.sort_direction, limit: "1" });
    const rows = [], cursors = new Set(); let first, cursor;
    stage = "full_filtered_exact_totals";
    for (let index = 0; index < 1000; index++) {
      if (cursor) query.set("cursor", cursor);
      const result = await read(`/api/v1/budgets?${query}`);
      check(result.availability.state === "available" && instant(result.as_of) === instant(base.as_of));
      if (!first) first = result;
      check(JSON.stringify(result.summaries) === JSON.stringify(first.summaries) && JSON.stringify(result.exclusions) === JSON.stringify(first.exclusions) && result.registry_revision === first.registry_revision);
      rows.push(...result.items);
      if (!result.page.has_more) { check(result.page.next_cursor === null); break; }
      cursor = result.page.next_cursor;
      check(typeof cursor === "string" && !cursors.has(cursor) && index < 999); cursors.add(cursor); continuations++;
    }
    check(new Set(rows.map(row => row.row_id)).size === rows.length);
    if (packet.phase === "distinct") {
      check(first.page.has_more);
      if (packet.monetary_resources === 1) check(!first.items.some(row => row.contexts.some(item => item.spend !== null && atoms(item.spend) !== 0n)));
    }
    const canonical = rows.filter(row => row.pool_id !== null);
    check(canonical.length === (packet.phase === "distinct" ? 2 : 1) && canonical.every(row => row.counted_in_selection === counted && row.primary_organization_id === packet.primary));
    check(new Set(canonical.flatMap(row => row.access_paths.map(path => path.resource_id))).size === (packet.phase === "unlinked" ? 1 : 2));
    if (counted) {
      check(first.summaries.length === 2 && new Set(first.summaries.map(item => item.scope_kind)).size === 2);
      for (const summary of first.summaries) {
        check(summary.scope_kind === "global" || summary.scope_kind === "organization" && summary.organization_id === packet.primary);
        check(atoms(summary.total) === expectedSum && summary.total.currency === measure.currency && summary.cost_basis === measure.cost_basis && summary.source_category === measure.source_category);
        check(summary.included_pool_count === selectedSources.length && summary.excluded_resource_count === (packet.phase === "unlinked" && summary.scope_kind === "organization" ? 0 : excluded));
      }
    } else check(first.summaries.length === 0);
    check(first.exclusions.reduce((count, item) => count + item.count, 0) === excluded);
    check(first.exclusions.every(item => item.reason_code === (packet.phase === "unlinked" ? "unresolved_overlap" : "currency_unavailable")));
    if (!excluded) check(first.summary_reason === null);
    stage = "filtered_totals_dom";
    query.delete("cursor"); query.delete("limit"); query.delete("sort_by"); query.delete("sort_direction");
    query.set("financial_sort", `${packet.sort_by}:${packet.sort_direction}`); query.set("resource_type", "api");
    await page.goto(`${origin}/?${query}`, { waitUntil: "domcontentloaded" });
    const panel = page.locator(".financial-overview[aria-busy=false]");
    await panel.waitFor(); check(await panel.getByRole("alert").count() === 0);
    for (let index = 0; index < 1000; index++) {
      const more = panel.getByRole("button", { name: "Load more financial rows", exact: true });
      if (await more.count() === 0) break;
      await more.click(); await panel.waitFor(); check(index < 999);
    }
    check(JSON.stringify(await panel.locator("tr[data-financial-row]").evaluateAll(nodes => nodes.map(node => node.dataset.financialRow))) === JSON.stringify(rows.map(row => row.row_id)));
    const summary = panel.locator('[aria-label="Reported spend summaries"]');
    check(await summary.locator("span[title]").count() === first.summaries.length);
    for (const [index, item] of first.summaries.entries()) {
      const line = summary.locator("p").nth(index);
      check(await line.getByTitle(exact(item.total), { exact: true }).count() === 1);
      check((await line.textContent()).includes(`${item.included_pool_count} included pools · ${item.excluded_resource_count} excluded resources`));
    }
    if (excluded) check((await summary.textContent()).includes(packet.phase === "unlinked" ? "unresolved overlap" : "currency unavailable"));
    for (const row of canonical) {
      const node = panel.locator("tr[data-financial-row]").filter({ has: page.getByRole("button", { name: row.pool_name, exact: true }) });
      check(await node.count() === 1);
      if (!counted) check((await node.textContent()).includes("Outside selected totals"));
      for (const reportContext of row.contexts) {
        const source = reports.get(reportContext.report_id);
        if (reportContext.spend === null) {
          check(source !== undefined && source.report.currency === null && reportContext.spend_reason === "cost_not_reported");
          check((await node.textContent()).includes("Spend not reported · cost not reported")); continue;
        }
        check(source?.source.included && reportContext.report_account_id === source.source.account_id && reportContext.report_resource_id === source.source.resource_id);
        check(atoms(reportContext.spend) === source.sum);
        const reading = node.locator("[data-overview-report]").filter({ has: page.getByTitle(exact(reportContext.spend), { exact: true }) });
        check(await reading.count() === 1);
      }
    }
    filters++;
    // Both-group view proves the canonical money link uses its contributor,
    // not necessarily the display account chosen for the shared row.
    if (groups.length === 2) {
      for (const row of canonical) {
        const reportContext = row.contexts.find(item => reports.get(item.report_id)?.source.included);
        if (reportContext === undefined) continue;
        const source = reports.get(reportContext.report_id); check(source !== undefined);
        stage = "contributing_report_link";
        const node = panel.locator("tr[data-financial-row]").filter({ has: page.getByRole("button", { name: row.pool_name, exact: true }) });
        const reading = node.locator("[data-overview-report]").filter({ has: page.getByTitle(exact(reportContext.spend), { exact: true }) });
        await reading.getByRole("button", { name: "View report", exact: true }).click();
        await page.waitForURL(url => url.pathname === `/accounts/${source.source.account_id}`);
        const detail = new URL(page.url());
        check(detail.searchParams.get("budget_resource") === source.source.resource_id && detail.searchParams.get("budget_report") === source.source.report_id);
        for (const [key, value] of [["budget_start", base.period_start], ["budget_end", base.period_end], ["budget_as_of", base.as_of]]) check(instant(detail.searchParams.get(key)) === instant(value));
        check(detail.searchParams.get("organization_ids") === [...groups].sort().join(","));
        const selected = page.getByRole("region", { name: "Selected financial report", exact: true });
        await selected.locator('[data-budget-history][aria-busy="false"]').waitFor();
        check(await selected.getAttribute("data-report-id") === source.source.report_id);
        check(await selected.getByTitle(exact(source.total), { exact: true }).count() > 0);
        await page.reload(); await selected.locator('[data-budget-history][aria-busy="false"]').waitFor();
        check(new URL(page.url()).search === detail.search);
        await page.goBack(); await panel.waitFor();
        check(new URL(page.url()).searchParams.get("organization_ids") === [...groups].sort().join(",")); links++;
      }
    }
  }
  stage = "read_only"; check(mutations === 0 && filters === 3 && links > 0);
  console.log(`M7 POOL TOTALS BROWSER: PASSED monetary_resources=${packet.monetary_resources} filters=${filters} continuations=${continuations} links=${links}`);
} catch {
  console.log(`M7 POOL TOTALS BROWSER: FAILED — ${stage}`); process.exitCode = 1;
} finally {
  await page?.close().catch(() => {});
}

process.stdout.write("", () => process.exit(process.exitCode ?? 0));
