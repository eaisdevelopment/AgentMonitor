"use strict";

import { chromium } from "@playwright/test";

const [endpoint, origin, accountId, mode = "existing"] = process.argv.slice(2);
if (!endpoint || !origin || !accountId || !["existing", "new"].includes(mode)) {
  throw new Error("usage: native_usd_account.mjs CDP_ENDPOINT ORIGIN ACCOUNT_ID [existing|new]");
}
const browser = await chromium.connectOverCDP(endpoint);
const url = `${origin}/accounts/${encodeURIComponent(accountId)}`;
const context = browser.contexts()[0];
const page = mode === "new" ? await context.newPage() : context.pages().find(item => item.url() === url);
const failures = [];
const requireTruth = (condition, code) => { if (!condition) failures.push(code); };
const usd = ({ coefficient, scale }) => {
  const digits = coefficient.padStart(scale + 1, "0");
  return `$${digits.slice(0, digits.length - scale)}.${(scale ? digits.slice(-scale) : "").padEnd(2, "0")}`;
};
try {
  if (!page) throw new Error("signed_in_account_page_required");
  if (mode === "new") await page.goto(url);
  await page.locator(".allowance-card").first().waitFor();
  const quotas = await page.evaluate(async (id) => {
    const response = await fetch(`/api/v1/accounts/${encodeURIComponent(id)}/quotas/v2?limit=200`);
    if (!response.ok) throw new Error("actual_quota_api_unavailable");
    return response.json();
  }, accountId);
  const money = quotas.items.filter(window => window.remaining.availability === "available" && window.remaining.value?.unit === "usd");
  requireTruth(money.length > 0, "actual_native_usd_reading_required");
  for (const window of money) {
    const card = page.locator(".allowance-card").filter({ has: page.locator(`h3`, { hasText: window.safe_label ?? window.window_key }) });
    const text = await card.textContent();
    requireTruth(text.includes(usd(window.remaining.value)), "native_usd_missing_from_allowance_card");
    requireTruth(!text.includes("Unknownleft"), "unknown_left_despite_native_usd");
    if (window.limit.availability === "available" && window.limit.value?.unit === "usd") {
      requireTruth(text.includes(usd(window.limit.value)), "native_usd_allowance_missing");
    }
    if (window.remaining_ratio.value === null && !window.allowance) {
      requireTruth(await card.getByRole("meter").count() === 0, "invented_percentage_meter");
    }
  }
  const summary = await page.locator(".account-workspace").textContent();
  requireTruth(!summary.includes("Waiting for a verified quota reading"), "real_balance_shown_as_waiting");
  requireTruth(!summary.includes("awaiting verified quota"), "owner_identity_conflated_with_quota");
  requireTruth(summary.includes("Owner-provided account name"), "owner_asserted_identity_not_explicit");
  const history = page.locator(".quota-history");
  const historyText = await history.textContent();
  requireTruth(historyText.includes("USD"), "native_usd_history_unit_missing");
  requireTruth(await history.locator("tbody tr[data-window-key]").count() > 0, "native_usd_history_missing");
  const retained = await page.evaluate(async (id) => {
    const now = Date.now();
    const query = new URLSearchParams({ subject_id: id, from: new Date(now - 86400000).toISOString(), before: new Date(now).toISOString(), metric: "remaining", series_kind: "poll_snapshot", limit: "200" });
    const response = await fetch(`/api/v1/capacity/history/v2?${query}`);
    if (!response.ok) throw new Error("actual_history_api_unavailable");
    return response.json();
  }, accountId);
  const historyRows = await history.locator("tbody tr[data-window-key]").evaluateAll(rows => rows.map(row => ({
    id: row.querySelector(".history-observation-id")?.textContent,
    text: row.textContent,
  })));
  const realMoneyPoints = retained.items.filter(point => point.value.availability === "available" && point.value.value?.unit === "usd");
  requireTruth(realMoneyPoints.length > 0, "actual_native_usd_history_required");
  requireTruth(realMoneyPoints.some(point => historyRows.some(row => row.id === point.observation_id && row.text.includes(usd(point.value.value)))), "native_usd_history_not_reconciled_to_actual_api");
  if (mode === "new") {
    const summaryToggle = history.locator("summary");
    await summaryToggle.focus();
    await page.keyboard.press("Enter");
    requireTruth(await history.getAttribute("open") !== null, "history_keyboard_expansion_failed");
    requireTruth(await page.getByLabel("History metric").inputValue() === "remaining", "native_usd_history_not_selected");
    for (const [width, height] of [[1920, 1080], [390, 844]]) {
      await page.setViewportSize({ width, height });
      requireTruth(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), "horizontal_document_overflow");
    }
  }
  console.log(JSON.stringify({ outcome: failures.length ? "failed" : "passed", native_usd_windows: money.length, failures }));
  process.exitCode = failures.length ? 1 : 0;
} catch (error) {
  console.error(error instanceof Error ? error.message : "native_usd_browser_check_failed");
  process.exitCode = 1;
} finally {
  if (mode === "new" && page) await page.close();
  await browser.close();
}
