// Real metadata changes occur in the isolated server; no response interception.
const origin = process.argv[2], changes = Number(process.argv[3]);
let browser, page, stage = "origin", passed = false;
const reads = [];
const check = value => { if (!value) throw new Error(); };
try {
  check(/^http:\/\/127\.0\.0\.1:\d+$/.test(origin) && [1, 2].includes(changes));
  let playwright;
  try { playwright = await import("@playwright/test"); }
  catch (error) {
    if (error?.code !== "ERR_MODULE_NOT_FOUND") throw error;
    playwright = await import("/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules/@playwright/test/index.mjs");
  }
  browser = await playwright.chromium.connectOverCDP("http://127.0.0.1:9225");
  page = await browser.contexts()[0].newPage();
  page.setDefaultTimeout(10000);
  page.on("response", response => {
    if (new URL(response.url()).pathname !== "/api/v1/budgets") return;
    reads.push(response);
  });
  const now = new Date(), end = new Date(now);
  end.setUTCHours(0, 0, 0, 0);
  const query = new URLSearchParams({ period_start: new Date(+end - 7 * 86400000).toISOString(), period_end: end.toISOString(), as_of: now.toISOString() });
  await page.goto(origin + "/?" + query, { waitUntil: "domcontentloaded" });
  const panel = page.locator(".financial-overview");
  await page.locator(".financial-overview[aria-busy=false]").waitFor();
  if (reads.length === 1) {
    const value = await reads[0].json();
    const reason = value.availability?.reason_code;
    stage = typeof reason === "string" && /^[a-z_]+$/.test(reason) ? "single_read_" + reason : "single_read_without_availability";
    check(false);
  }
  stage = reads.length < 2 ? "too_few_reads" : "too_many_reads";
  check(reads.length === 2);
  stage = "read_http_status";
  check(reads.every(value => value.status() === 200));
  stage = "retry_query_changed";
  check(reads[0].url() === reads[1].url());
  const first = await reads[0].json(), second = await reads[1].json();
  stage = "first_read_not_registry_race";
  check(first.availability.state === "unavailable" && first.availability.reason_code === "budget_overview_registry_changed");
  if (changes === 1) {
    stage = "recovered_rows_mismatch";
    check(second.availability.state === "available" && second.items.length > 0);
    const actual = await panel.locator("[data-financial-row]").evaluateAll(rows => rows.map(row => row.dataset.financialRow));
    check(JSON.stringify(actual) === JSON.stringify(second.items.map(row => row.row_id)));
    check(await panel.getByRole("alert").count() === 0);
  } else {
    stage = "retry_not_bounded";
    check(second.availability.state === "unavailable" && second.availability.reason_code === "budget_overview_registry_changed");
    check(await panel.getByRole("alert").isVisible());
    check(await panel.locator("[data-financial-row]").count() === 0);
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    check(reads.length === 2);
  }
  passed = true;
  console.log(`M7 REGISTRY RACE BROWSER: PASSED changes=${changes} reads=2`);
} catch {
  console.log(`M7 REGISTRY RACE BROWSER: FAILED ${stage}`);
} finally {
  await page?.close();
  await browser?.close();
}
process.exitCode = passed ? 0 : 1;
