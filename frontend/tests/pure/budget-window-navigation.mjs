import assert from "node:assert/strict";
import { budgetWindowDays, shiftBudgetWindow, resizeBudgetWindow, latestBudgetWindow, budgetWindowSearch } from "../../src/features/accounts/budgetWindowNavigation.ts";
import { advanceFinancialRead } from "../../src/features/accounts/billingCheckPresentation.ts";
import { selectedFinancialReport } from "../../src/features/accounts/financialReadPresentation.ts";

// Pure date/URL decisions only; no constructed I/O responses or telemetry.
const query = { period_start: "2026-11-05T00:00:00Z", period_end: "2026-11-12T00:00:00Z", as_of: "2026-11-12T23:59:59.123456Z" };
assert.equal(budgetWindowDays(query), 7);
assert.equal(shiftBudgetWindow(query, 1), null);
const previous = shiftBudgetWindow(query, -1);
assert.equal(previous.period_start, "2026-10-29T00:00:00.000Z");
assert.equal(previous.period_end, "2026-11-05T00:00:00.000Z");
assert.equal(previous.as_of, query.as_of);
assert.equal(shiftBudgetWindow(previous, 1).period_end, "2026-11-12T00:00:00.000Z");
assert.equal(shiftBudgetWindow(previous, 1).as_of, query.as_of);
const thirty = resizeBudgetWindow(previous, 30);
assert.equal(budgetWindowDays(thirty), 30);
assert.equal(thirty.period_end, previous.period_end);
assert.equal(thirty.as_of, query.as_of);
assert.equal(shiftBudgetWindow(thirty, 1), null, "Next cannot overshoot pinned cutoff after width change");
assert.equal(shiftBudgetWindow(thirty, -1).period_end, thirty.period_start);
const latest = latestBudgetWindow(30, "2026-11-13T00:00:00.000001Z");
assert.equal(latest.period_end, "2026-11-13T00:00:00.000Z");
assert.equal(latest.as_of, "2026-11-13T00:00:00.000001Z");
for (const invalid of [
  { ...query, period_start: "2026-11-05T00:00:00.000001Z" },
  { ...query, period_start: "2026-11-04T00:00:00Z" },
  { ...query, period_end: "2026-11-13T00:00:00Z" },
  { ...query, period_start: "2026-02-30T00:00:00Z" },
  { ...query, as_of: "2026-11-12T24:00:00Z" },
]) assert.throws(() => budgetWindowDays(invalid), /budget_window_invalid/);
const selectedUrl = budgetWindowSearch("?provider_key=ollama&financial_sort=state:descending&budget_resource=resource&budget_report=old", previous, "resource");
const selected = selectedFinancialReport(selectedUrl);
assert.equal(selected.kind, "selected");
assert.equal(selected.resourceId, "resource");
assert.equal(selected.reportId, null);
assert.equal(new URLSearchParams(selectedUrl).get("provider_key"), "ollama");
const period = selectedFinancialReport(budgetWindowSearch("?budget_selection=invalid", previous, null));
assert.equal(period.kind, "period");
assert.deepEqual(period.query, previous);
assert.equal(period.days, 7);
assert.equal(selectedFinancialReport(budgetWindowSearch("", thirty, null)).days, 30);
const refreshed = advanceFinancialRead(previous, new Date("2026-11-13T12:00:00Z"));
assert.equal(refreshed.period_start, previous.period_start);
assert.equal(refreshed.period_end, previous.period_end);
assert.equal(refreshed.as_of, "2026-11-13T12:00:00.000Z");
assert.notEqual(latestBudgetWindow(7, refreshed.as_of).period_end, refreshed.period_end);
const refreshedSelection = selectedFinancialReport(budgetWindowSearch(selectedUrl, refreshed, "resource"));
assert.equal(refreshedSelection.resourceId, "resource");
assert.equal(refreshedSelection.reportId, null);
console.log("budget-window-navigation: passed");
