import assert from "node:assert/strict";
let presentation;
try { presentation = await import("./budgetOverviewPresentation.ts"); }
catch (error) { if (error.code !== "ERR_MODULE_NOT_FOUND") throw error; throw new Error("financial_overview_replacement_policy_missing"); }
const { canReplaceFinancialOverview, financialAccountSelectors } = presentation;
for (const state of ["unavailable", "unknown", "unsupported"]) assert.equal(canReplaceFinancialOverview(state), false);
for (const state of ["available", "partial"]) assert.equal(canReplaceFinancialOverview(state), true);
const period = { start: "2026-11-04T00:00:00Z", end: "2026-11-11T00:00:00Z" };
assert.deepEqual(financialAccountSelectors(null, undefined, period, period.end), {});
assert.deepEqual(financialAccountSelectors("resource-a", undefined, period, period.end), {
  budget_resource: "resource-a", budget_start: period.start, budget_end: period.end, budget_as_of: period.end,
});
assert.equal(financialAccountSelectors("resource-a", "report-a", period, period.end).budget_report, "report-a");
console.log("FINANCIAL OVERVIEW PRESENTATION PURE: PASSED");
