"use strict";

import assert from "node:assert/strict";
import { canRetainFinancialReading, selectedFinancialReport } from "../../src/features/accounts/financialReadPresentation.ts";

// Pure presentation contexts only, with no telemetry or simulated I/O.
const context = {
  account: { account_id: "account", provider_key: "claude", record_version: 2 },
  periodStart: "2026-11-04T00:00:00Z", periodEnd: "2026-11-11T00:00:00Z", readRevision: 0,
};
assert.equal(canRetainFinancialReading(context, context), true,
  "Refreshing the same stored interval must keep its last successful reading");
assert.equal(canRetainFinancialReading(context, { ...context, readRevision: 1 }), true,
  "Check completion must retain the prior same-context reading until its replacement succeeds");
assert.equal(canRetainFinancialReading(context, { ...context, account: { ...context.account } }), true,
  "Rereading unchanged account metadata must not erase financial history");
assert.equal(canRetainFinancialReading(context, { ...context, account: { ...context.account, record_version: 3 } }), false,
  "A changed account generation conservatively invalidates the financial context");
assert.equal(canRetainFinancialReading(context, { ...context, account: { ...context.account, account_id: "different" } }), false,
  "A previous account's reading cannot appear under another account");
assert.equal(canRetainFinancialReading(context, { ...context, account: { ...context.account, provider_key: "codex" } }), false);
assert.equal(canRetainFinancialReading(context, { ...context, periodStart: "2026-10-12T00:00:00Z" }), false,
  "Seven-day readings cannot appear under a thirty-day heading");
assert.equal(canRetainFinancialReading(context, { ...context, periodEnd: "2026-11-12T00:00:00Z" }), false,
  "Moving the UTC cutoff invalidates the old interval");
assert.equal(canRetainFinancialReading(context, { ...context, periodStart: "2026-11-04T00:00:00.000Z", periodEnd: "2026-11-11T00:00:00.000Z" }), true);
const selection = new URLSearchParams({ budget_resource: "resource-1", budget_report: "report-1", budget_start: context.periodStart, budget_end: context.periodEnd, budget_as_of: "2026-11-11T12:00:00.123456Z" });
const selected = selectedFinancialReport(selection.toString());
assert.equal(selected.kind, "selected");
assert.equal(selected.query.as_of, "2026-11-11T12:00:00.123456Z", "An immutable cutoff must not lose microseconds");
for (const invalid of ["2026-11-04T00:00:00.000001Z", "2026-02-30T00:00:00Z", "2026-11-03T24:00:00Z"]) {
  const query = new URLSearchParams(selection); query.set("budget_start", invalid);
  assert.equal(selectedFinancialReport(query.toString()).kind, "invalid");
}
const periodSelection = new URLSearchParams(selection);
periodSelection.delete("budget_resource"); periodSelection.delete("budget_report");
assert.equal(selectedFinancialReport(periodSelection.toString()).kind, "period");
for (const missing of ["budget_start", "budget_end", "budget_as_of"]) {
  const invalid = new URLSearchParams(periodSelection); invalid.delete(missing);
  assert.equal(selectedFinancialReport(invalid.toString()).kind, "invalid");
}
const reportWithoutResource = new URLSearchParams(periodSelection); reportWithoutResource.set("budget_report", "report");
assert.equal(selectedFinancialReport(reportWithoutResource.toString()).kind, "invalid");
console.log("FINANCIAL READ PRESENTATION PURE: PASSED");
