"use strict";

import { chromium } from "@playwright/test";

const [endpoint, origin, accountId] = process.argv.slice(2);
if (!endpoint || !origin || !accountId) {
  throw new Error("usage: source_period_start.mjs CDP_ENDPOINT ORIGIN ACCOUNT_ID");
}
const browser = await chromium.connectOverCDP(endpoint);
const context = browser.contexts()[0];
const page = await context.newPage();
const failures = [];
const requireTruth = (condition, code) => { if (!condition) failures.push(code); };
try {
  const receivedHistory = page.waitForResponse(response => {
    const url = new URL(response.url());
    return url.origin === origin && url.pathname === "/api/v1/capacity/history/v2"
      && url.searchParams.get("subject_id") === accountId;
  });
  await page.goto(`${origin}/accounts/${encodeURIComponent(accountId)}`);
  const response = await receivedHistory;
  if (!response.ok()) throw new Error("actual_history_api_unavailable");
  const history = await response.json();
  await page.locator(".quota-history tbody tr").first().waitFor({ state: "attached" });
  const supplied = history.items.filter(point => point.source_period_start != null);
  requireTruth(supplied.length > 0, "actual_source_period_start_required");
  const rows = await page.locator(".quota-history tbody tr").evaluateAll(items => items.map(row => ({
    id: row.querySelector(".history-observation-id")?.textContent,
    start: row.querySelector(".quota-period-start time")?.getAttribute("datetime") ?? null,
    label: row.querySelector(".quota-period-start")?.textContent ?? null,
  })));
  requireTruth(rows.length === history.items.length, "history_rows_not_reconciled");
  for (const point of history.items) {
    const row = rows.find(item => item.id === point.observation_id);
    if (point.source_period_start != null) {
      requireTruth(row?.start === point.source_period_start, "source_period_start_missing_or_changed");
    } else {
      requireTruth(row?.start === null && row?.label === "Not reported", "unknown_period_start_not_explicit");
    }
  }
  await page.locator(".quota-history summary").click();
  requireTruth(await page.getByRole("columnheader", { name: "Period start", exact: true }).isVisible(), "period_start_header_not_visible");
  for (const [width, height] of [[1920, 1080], [390, 844]]) {
    await page.setViewportSize({ width, height });
    requireTruth(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), "horizontal_document_overflow");
  }
  console.log(JSON.stringify({ outcome: failures.length ? "failed" : "passed", observations: rows.length, supplied_period_starts: supplied.length, failures: [...new Set(failures)] }));
  process.exitCode = failures.length ? 1 : 0;
} catch {
  console.error("SOURCE PERIOD START: BLOCKED — real browser or authenticated history unavailable");
  process.exitCode = 2;
} finally {
  await page.close();
  await browser.close();
}
