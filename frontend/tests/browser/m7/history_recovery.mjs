// Genuine history + a real private service restart. No intercepted responses.
import { createInterface } from "node:readline";
import { chromium, expect } from "@playwright/test";

const origin = process.argv[2], input = createInterface({ input: process.stdin });
const lines = input[Symbol.asyncIterator]();
let page, stage = "private_origin", mutations = 0, passed = false;
const check = value => { if (!value) throw new Error(); };
const instant = value => value.replace("+00:00", "Z").replace(/(?:\.(\d{1,6}))?Z$/, (_, digits) => `.${(digits ?? "").padEnd(6, "0")}Z`);
try {
  check(/^http:\/\/127\.0\.0\.1:\d+$/.test(origin) && new URL(origin).port !== "43110");
  const selection = JSON.parse((await lines.next()).value);
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9225", { timeout: 15000 });
  const context = browser.contexts().find(value => value.pages().some(tab => tab.url().startsWith("http://127.0.0.1:43110/")));
  check(context !== undefined);
  page = await context.newPage(); page.setDefaultTimeout(10000);
  page.on("request", request => { if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) mutations++; });
  const query = new URLSearchParams({ budget_resource: selection.resource_id, budget_report: selection.report_id,
    budget_start: selection.period_start.replace("+00:00", "Z"), budget_end: selection.period_end.replace("+00:00", "Z"),
    budget_as_of: selection.as_of.replace("+00:00", "Z") });
  const route = `/api/v1/budgets/${encodeURIComponent(selection.resource_id)}/history`;
  const matches = response => new URL(response.url()).pathname === route && response.request().method() === "GET";
  const firstResponse = page.waitForResponse(matches).then(response => ({ response }), error => ({ error }));
  stage = "genuine_first_page";
  await page.goto(`${origin}/accounts/${encodeURIComponent(selection.account_id)}?${query}`, { waitUntil: "domcontentloaded" });
  const first = await firstResponse; if (first.error) throw first.error;
  check(first.response.ok());
  const data = await first.response.json();
  check(data.page.has_more && data.items.length === 50 && data.page.next_cursor !== null);
  const firstQuery = new URL(first.response.url()).searchParams;
  check(firstQuery.get("account_id") === selection.account_id && firstQuery.get("report_id") === selection.report_id &&
    firstQuery.get("limit") === "50" && !firstQuery.has("cursor"));
  for (const key of ["period_start", "period_end", "as_of"]) check(instant(firstQuery.get(key)) === instant(selection[key]));
  check(data.report.account_id === selection.account_id && data.report.resource_id === selection.resource_id &&
    data.report.report_id === selection.report_id && data.reported_spend.report_id === selection.report_id &&
    instant(data.as_of) === instant(selection.as_of) &&
    instant(data.report.requested_period.start) === instant(selection.period_start) &&
    instant(data.report.requested_period.end) === instant(selection.period_end));
  const selectionUrl = page.url(), history = page.locator('[data-budget-history]');
  await expect(history.locator('[data-bucket-key]')).toHaveCount(50);
  await expect(history).toHaveAttribute("aria-busy", "false");
  const state = () => history.locator('[data-bucket-key]').evaluateAll(nodes => nodes.map(node => ({
    key: node.getAttribute('data-bucket-key'), kind: node.getAttribute('data-bucket-kind'), text: node.textContent,
  })));
  const retained = await state();
  const chartState = () => history.locator('[data-chart-bucket-key]').evaluateAll(nodes => nodes.map(node => ({
    key: node.getAttribute('data-chart-bucket-key'), kind: node.getAttribute('data-chart-kind'),
    magnitude: node.getAttribute('data-chart-magnitude'), direction: node.getAttribute('data-chart-direction'),
    label: node.getAttribute('aria-label'),
  })));
  const retainedChart = await chartState();
  check(retainedChart.length > 0);
  stage = "private_service_restart";
  console.log("RESTART PRIVATE HISTORY SERVICE");
  check((await lines.next()).value === "PRIVATE HISTORY SERVICE READY");
  const deniedResponse = page.waitForResponse(matches).then(response => ({ response }), error => ({ error }));
  await history.getByRole("button", { name: "Load more history", exact: true }).click();
  const denied = await deniedResponse; if (denied.error) throw denied.error;
  check(denied.response.status() === 400 && (await denied.response.json()).code === "invalid_cursor");
  check(new URL(denied.response.url()).searchParams.get("cursor") === data.page.next_cursor);
  stage = "rejected_cursor_restart_control";
  await history.getByRole("alert").waitFor();
  check(JSON.stringify(await state()) === JSON.stringify(retained) && page.url() === selectionUrl);
  check(JSON.stringify(await chartState()) === JSON.stringify(retainedChart));
  check((await history.getByRole("region", { name: "History chart", exact: true }).textContent()).includes("History read failed"));
  const restart = history.getByRole("button", { name: "Restart history pages", exact: true });
  await restart.waitFor();
  const replacementResponse = page.waitForResponse(matches).then(response => ({ response }), error => ({ error }));
  await restart.click();
  const replacement = await replacementResponse; if (replacement.error) throw replacement.error;
  check(replacement.response.ok());
  const beforeQuery = new URL(first.response.url()).searchParams, afterQuery = new URL(replacement.response.url()).searchParams;
  check(!afterQuery.has("cursor") && beforeQuery.toString() === afterQuery.toString());
  const fresh = await replacement.response.json();
  check(JSON.stringify(fresh.items) === JSON.stringify(data.items) && fresh.page.next_cursor !== data.page.next_cursor);
  await expect(history.getByRole("alert")).toHaveCount(0);
  await expect(history.locator('[data-bucket-key]')).toHaveCount(50);
  check(JSON.stringify(await state()) === JSON.stringify(retained));
  check(JSON.stringify(await chartState()) === JSON.stringify(retainedChart));
  stage = "fresh_cursor_continuation";
  const continuedResponse = page.waitForResponse(matches).then(response => ({ response }), error => ({ error }));
  await history.getByRole("button", { name: "Load more history", exact: true }).click();
  const continued = await continuedResponse; if (continued.error) throw continued.error;
  check(continued.response.ok() && new URL(continued.response.url()).searchParams.get("cursor") === fresh.page.next_cursor);
  const next = await continued.response.json();
  await expect(history.locator('[data-bucket-key]')).toHaveCount(50 + next.items.length);
  const finalRows = await state();
  check(new Set(finalRows.map(row => row.kind + ":" + row.key)).size === finalRows.length);
  check(page.url() === selectionUrl && mutations === 0);
  stage = "unavailable_pinned_report";
  // The genuine report was not yet stored at its provider collection instant.
  // This exercises actual missing-selection recovery, not fabricated deletion.
  const unavailableQuery = new URLSearchParams(query);
  unavailableQuery.set("budget_as_of", selection.unavailable_as_of.replace("+00:00", "Z"));
  const missingResponse = page.waitForResponse(matches).then(response => ({ response }), error => ({ error }));
  await page.goto(`${origin}/accounts/${encodeURIComponent(selection.account_id)}?${unavailableQuery}`, { waitUntil: "domcontentloaded" });
  const missing = await missingResponse; if (missing.error) throw missing.error;
  check(missing.response.status() === 404 && (await missing.response.json()).code === "budget_report_not_found");
  await expect(history.locator(':scope > [role="alert"]')).toContainText("selected history is unavailable or no longer retained");
  check(await history.getAttribute("data-budget-history") === selection.report_id);
  check(new URL(page.url()).searchParams.get("budget_report") === selection.report_id);
  check(await history.locator('[data-bucket-key]').count() === 0);
  stage = "unavailable_selection_latest_recovery";
  const latest = page.getByRole("button", { name: "Latest completed window", exact: true });
  await expect(latest).toBeEnabled();
  stage = "unavailable_selection_latest_navigation";
  await latest.click();
  await page.waitForURL(url => !url.searchParams.has("budget_report"));
  await expect(page.getByRole("region", { name: "Selected financial report", exact: true })).toHaveCount(0);
  await page.getByRole("region", { name: "Collect cloud usage", exact: true }).waitFor();
  check(new URL(page.url()).searchParams.get("budget_resource") === selection.resource_id && mutations === 0);
  passed = true;
  console.log("M7 HISTORY RECOVERY BROWSER: PASSED");
} catch (error) {
  console.log(`M7 HISTORY RECOVERY BROWSER: FAILED — ${stage}`);
  const diagnostic = { error_kind: error?.name === "TimeoutError" ? "timeout" : "assertion_or_runtime" };
  if (page && !page.isClosed()) {
    try {
      const latest = page.getByRole("button", { name: "Latest completed window", exact: true });
      diagnostic.latest_button_count = await latest.count();
      diagnostic.latest_button_enabled = diagnostic.latest_button_count === 1 ? await latest.isEnabled() : null;
      diagnostic.selected_report_present = new URL(page.url()).searchParams.has("budget_report");
      diagnostic.cloud_collect_count = await page.getByRole("region", { name: "Collect cloud usage", exact: true }).count();
    } catch { diagnostic.page_diagnostic_unavailable = true; }
  }
  console.log(JSON.stringify(diagnostic));
} finally {
  input.close();
  if (page) await page.close().catch(() => { passed = false; });
}
process.stdout.write("", () => process.exit(passed ? 0 : 1));
