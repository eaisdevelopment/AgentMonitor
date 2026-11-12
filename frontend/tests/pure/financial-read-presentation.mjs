"use strict";

import assert from "node:assert/strict";
import * as financial from "../../src/features/accounts/financialReadPresentation.ts";
const { billingReportCollectable, canRetainFinancialReading, selectedFinancialReport } = financial;

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
assert.equal(canRetainFinancialReading(context, { ...context, authorityRevision: 1 }), false,
  "Changing billing scope must invalidate old current values even when the account version is unchanged");
const selection = new URLSearchParams({ budget_resource: "resource-1", budget_report: "report-1", budget_start: context.periodStart, budget_end: context.periodEnd, budget_as_of: "2026-11-11T12:00:00.123456Z" });
const selected = selectedFinancialReport(selection.toString());
assert.equal(selected.kind, "selected");
assert.equal(selected.query.as_of, "2026-11-11T12:00:00.123456Z", "An immutable cutoff must not lose microseconds");
const connection = { resource_id: "resource-1", account_id: "account", provider_key: "claude", scope_id: "current-scope", scope_generation: 2 };
const report = { ...connection, report_id: "report-1" };
const resource = { connection, reports: [{ current: report, latest_attempt: report }] };
assert.equal(billingReportCollectable(selected, resource), true);
assert.equal(billingReportCollectable(selected, { ...resource, reports: [] }), false,
  "A historical report absent from the current scope must not collect using new authority");
assert.equal(billingReportCollectable(selected, { ...resource, reports: [{ current: { ...report, scope_generation: 1 }, latest_attempt: null }] }), false);
assert.equal(billingReportCollectable(selected, { ...resource, reports: [{ current: { ...report, scope_id: "other-scope" }, latest_attempt: null }] }), false);
assert.equal(billingReportCollectable({ ...selected, reportId: null }, resource), true);
assert.equal(billingReportCollectable({ kind: "none" }, resource), true);
assert.equal(billingReportCollectable({ kind: "invalid" }, resource), false);
assert.equal(typeof financial.cloudReportCollectable, "function", "Historical cloud report selections need a current-authority collection guard");
const cloudReport = { ...report, provider_key: "ollama", source_category: "team_requests_and_cost" };
const cloud = { account_id: "account", resource_id: "resource-1", reports: [{ current: cloudReport, latest_attempt: cloudReport }] };
assert.equal(financial.cloudReportCollectable(selected, cloud), true);
assert.equal(financial.cloudReportCollectable(selected, { ...cloud, reports: [] }), false, "A retained old report does not establish current cloud authority");
assert.equal(financial.cloudReportCollectable(selected, { ...cloud, account_id: "another-account" }), false);
assert.equal(financial.cloudReportCollectable(selected, { ...cloud, reports: [{ current: { ...cloudReport, source_category: "unknown" }, latest_attempt: null }] }), false);
assert.equal(financial.cloudReportCollectable({ ...selected, reportId: null }, cloud), true);
assert.equal(financial.cloudReportCollectable({ kind: "none" }, cloud), true);
assert.equal(financial.cloudReportCollectable({ kind: "invalid" }, cloud), false);
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
