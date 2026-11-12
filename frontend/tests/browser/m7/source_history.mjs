import { chromium } from "@playwright/test";

const origin = process.argv[2];
let stage = "private_origin", page, transport;
let mutations = 0;
let uiPages = 0;
try {
  if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(origin ?? "") || new URL(origin).port === "43110") throw new Error();
  let input = "";
  for await (const part of process.stdin) input += part;
  const selection = JSON.parse(input);
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9225", { timeout: 5000 });
  const context = browser.contexts().find(item => item.pages().some(tab => tab.url().startsWith("http://127.0.0.1:43110/")));
  if (context === undefined) throw new Error();
  page = await context.newPage();
  page.setDefaultTimeout(10000);
  page.on("request", request => { if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) mutations++; });
  const query = new URLSearchParams(selection);
  query.delete("resource_id");
  const path = `/api/v1/budgets/${encodeURIComponent(selection.resource_id)}/reports`;
  const search = new URLSearchParams({ budget_resource: selection.resource_id, budget_start: selection.period_start, budget_end: selection.period_end, budget_as_of: selection.as_of });
  await page.goto(`${origin}/accounts/${encodeURIComponent(selection.account_id)}?${search}`, { waitUntil: "domcontentloaded" });
  stage = "authentication";
  await page.getByRole("heading", { name: "API usage & spend", exact: true }).waitFor();
  async function read(address) {
    const response = await page.request.get(`${origin}${address}`, { headers: { Origin: origin } });
    if (!response.ok()) throw new Error();
    return response.json();
  }
  const micro = value => {
    const match = /^(.*T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?Z$/.exec(value);
    if (match === null) throw new Error();
    return BigInt(Date.parse(`${match[1]}Z`)) * 1000n + BigInt((match[2] ?? "").padEnd(6, "0"));
  };
  const equal = (left, right) => { if (JSON.stringify(left) !== JSON.stringify(right)) throw new Error(); };
  const check = condition => { if (!condition) throw new Error(); };
  const expected = [], cursors = new Set();
  let cursor;
  stage = "genuine_report_metadata";
  for (let index = 0; index < 2000; index++) {
    const current = new URLSearchParams(query);
    current.set("limit", "1");
    if (cursor !== undefined) current.set("cursor", cursor);
    const batch = await read(`${path}?${current}`);
    check(batch.account_id === selection.account_id && batch.resource_id === selection.resource_id && micro(batch.as_of) === micro(selection.as_of));
    check(micro(batch.period.start) === micro(selection.period_start) && micro(batch.period.end) === micro(selection.period_end));
    check(batch.availability.state === "available" && batch.items.length <= 1);
    for (const report of batch.items) {
      check(!("cost_buckets" in report) && !("usage_buckets" in report));
      expected.push(report);
    }
    if (!batch.page.has_more) { check(batch.page.next_cursor === null); break; }
    cursor = batch.page.next_cursor;
    check(typeof cursor === "string" && !cursors.has(cursor));
    cursors.add(cursor);
    check(index < 1999);
  }
  check(expected.length > 0 && new Set(expected.map(item => item.report_id)).size === expected.length);
  stage = "source_history_disclosure_missing";
  const disclosure = page.locator("details[data-source-history]");
  await disclosure.waitFor();
  check(await disclosure.count() === 1 && await disclosure.getAttribute("data-source-history") === selection.resource_id);
  check(!(await disclosure.evaluate(node => node.open)));
  await disclosure.getByText("Source history", { exact: true }).click();
  const settled = () => disclosure.locator('[data-source-history-content][aria-busy="false"]').waitFor();
  await settled();
  stage = "source_history_rows";
  for (let index = 0; index < 200; index++) {
    const more = disclosure.getByRole("button", { name: "Load more reports", exact: true });
    if (await more.count() === 0) break;
    await more.click(); await settled(); uiPages++;
    check(index < 199);
  }
  const ids = () => disclosure.locator("[data-source-report]").evaluateAll(nodes => nodes.map(node => node.getAttribute("data-source-report")));
  equal(await ids(), expected.map(report => report.report_id));
  for (const [index, report] of expected.entries()) {
    const item = disclosure.locator("[data-source-report]").nth(index);
    check((await item.textContent()).includes(report.scope_id ?? "Not established"));
    check((await item.textContent()).includes(`Scope generation ${report.scope_generation}`));
    check(await item.locator('time[data-source-collected]').getAttribute("datetime") === report.collected_at);
  }
  stage = "source_history_offline_retention";
  const retained = await ids();
  transport = await context.newCDPSession(page);
  await transport.send("Network.enable");
  await transport.send("Network.emulateNetworkConditions", { offline: true, latency: 0, downloadThroughput: 0, uploadThroughput: 0 });
  await disclosure.getByRole("button", { name: "Refresh source history", exact: true }).click();
  await disclosure.getByRole("alert").waitFor();
  equal(await ids(), retained);
  await transport.send("Network.emulateNetworkConditions", { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
  await disclosure.getByRole("button", { name: "Retry source history", exact: true }).click();
  await settled();
  check(expected.length > 1);
  const chosen = expected[1];
  stage = "source_history_selection";
  await disclosure.locator("[data-source-report]").nth(1).getByRole("link", { name: "View report", exact: true }).click();
  stage = "source_history_selected_url";
  await page.waitForURL(url => url.searchParams.get("budget_report") === chosen.report_id);
  const chosenQuery = new URLSearchParams(query);
  chosenQuery.set("report_id", chosen.report_id);
  stage = "source_history_selected_api";
  const full = await read(`/api/v1/budgets/${encodeURIComponent(selection.resource_id)}?${chosenQuery}`);
  equal(full.report.report_id, chosen.report_id);
  equal(full.report.scope_generation, chosen.scope_generation);
  equal(full.report.scope_id, chosen.scope_id);
  const money = value => {
    const coefficient = BigInt(value.coefficient), digits = (coefficient < 0n ? -coefficient : coefficient).toString().padStart(value.scale + 1, "0");
    return `${coefficient < 0n ? "-" : ""}${value.scale === 0 ? digits : `${digits.slice(0, -value.scale)}.${digits.slice(-value.scale)}`} ${value.currency ?? value.unit}`;
  };
  async function selectedFacts() {
    stage = "source_history_selected_history_read";
    const section = page.getByRole("region", { name: "Selected financial report", exact: true });
    await section.locator('[data-budget-history][aria-busy="false"]').waitFor();
    stage = "source_history_selected_scope";
    check((await section.textContent()).includes(chosen.scope_id ?? "Not established") && (await section.textContent()).includes(`Scope generation ${chosen.scope_generation}`));
    const address = new URL(page.url());
    stage = "source_history_selected_cutoff";
    check(address.searchParams.get("budget_resource") === selection.resource_id && address.searchParams.get("budget_report") === chosen.report_id && micro(address.searchParams.get("budget_as_of")) === micro(selection.as_of));
    for (let index = 0; index < 200; index++) {
      const more = section.getByRole("button", { name: "Load more history", exact: true });
      if (await more.count() === 0) break;
      await more.click(); await section.locator('[data-budget-history][aria-busy="false"]').waitFor(); check(index < 199);
    }
    const facts = [...full.report.cost_buckets.map(bucket => ({ kind: "cost", bucket, value: bucket.amount })), ...full.report.usage_buckets.map(bucket => ({ kind: "usage", bucket, value: bucket.quantity }))];
    stage = "source_history_selected_fact_count";
    check(await section.locator("[data-bucket-key]").count() === facts.length);
    for (const fact of facts) {
      stage = "source_history_selected_exact_fact";
      const escaped = await page.evaluate(value => CSS.escape(value), fact.bucket.bucket_key);
      const cells = section.locator(`[data-bucket-kind="${fact.kind}"][data-bucket-key="${escaped}"]`).getByRole("cell");
      check(await cells.nth(1).textContent() === money(fact.value));
    }
  }
  await selectedFacts();
  stage = "source_history_reload_back";
  await page.reload({ waitUntil: "domcontentloaded" }); await selectedFacts();
  await page.goBack({ waitUntil: "domcontentloaded" });
  check(new URL(page.url()).searchParams.get("budget_report") === null);
  await page.goForward({ waitUntil: "domcontentloaded" }); await selectedFacts();
  stage = "read_only";
  check(mutations === 0);
  console.log(`M7 SOURCE HISTORY BROWSER: PASSED reports=${expected.length} api_pages=${expected.length} ui_continuations=${uiPages} original_scopes=${new Set(expected.map(report => report.scope_generation)).size}`);
} catch {
  console.log(`M7 SOURCE HISTORY BROWSER: FAILED — ${stage}`);
  process.exitCode = 1;
} finally {
  if (transport) await transport.detach().catch(() => {});
  if (page) await page.close().catch(() => {});
}
// Disconnect this probe without closing the owner's shared browser.
process.stdout.write("", () => process.exit(process.exitCode ?? 0));
