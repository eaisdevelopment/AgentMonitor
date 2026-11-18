import assert from "node:assert/strict";
import { safeOverviewSearch } from "../../src/features/overview/overviewSelection.ts";
import * as presentation from "../../src/features/accounts/financialReadPresentation.ts";

assert.equal(typeof presentation.selectedFinancialReport, "function", "pinned financial selection missing");
const valid = "?budget_resource=resource&budget_report=report&budget_start=2026-11-04T00%3A00%3A00Z&budget_end=2026-11-11T00%3A00%3A00Z&budget_as_of=2026-11-11T01%3A00%3A00Z";
const parsed = presentation.selectedFinancialReport(valid);
assert.equal(parsed.kind, "selected");
assert.equal(parsed.reportId, "report");
assert.equal(parsed.resourceId, "resource");
assert.equal(parsed.query.period_start, "2026-11-04T00:00:00Z");
const precise = presentation.selectedFinancialReport(valid.replace("01%3A00%3A00Z", "01%3A00%3A00.123456Z"));
assert.equal(precise.kind, "selected");
assert.equal(precise.query.as_of, "2026-11-11T01:00:00.123456Z");
assert.equal(presentation.selectedFinancialReport("").kind, "none");
assert.equal(presentation.selectedFinancialReport("?budget_report=report").kind, "invalid");
assert.equal(presentation.selectedFinancialReport(valid + "&budget_report=other").kind, "invalid");
assert.equal(presentation.selectedFinancialReport(valid.replace("2026-11-04", "2026-11-05")).kind, "invalid");
assert.equal(presentation.selectedFinancialReport(valid.replace("budget_as_of=2026-11-11", "budget_as_of=2026-11-10")).kind, "invalid");
const fundsOnly = presentation.selectedFinancialReport(valid.replace("&budget_report=report", ""));
assert.equal(fundsOnly.kind, "selected");
assert.equal(fundsOnly.reportId, null);
// The router sanitizer is on every popstate/reload path. A valid admitted
// report view must survive it before the account's selection parser runs.
const reportView = new URLSearchParams(valid);
reportView.delete("budget_report");
reportView.set("budget_as_of", "2026-11-11T01:00:00.123456Z");
reportView.set("budget_category", "cost");
reportView.set("budget_grouping", "workspace");
const sanitizedView = new URLSearchParams(safeOverviewSearch(reportView.toString(), true));
assert.equal(sanitizedView.get("budget_category"), "cost", "router discarded valid report category");
assert.equal(sanitizedView.get("budget_grouping"), "workspace", "router discarded valid report grouping");
assert.equal(sanitizedView.get("budget_resource"), "resource");
assert.equal(sanitizedView.get("budget_as_of"), "2026-11-11T01:00:00.123456Z");
assert.equal(presentation.selectedFinancialReport(sanitizedView.toString()).kind, "selected");
for (const grouping of [null, "workspace", "project", "api_key_id", "model", "token_category"]) {
  const query = new URLSearchParams(reportView);
  query.set("budget_category", grouping === "token_category" ? "usage_tokens" : "usage");
  if (grouping === null) query.delete("budget_grouping");
  else query.set("budget_grouping", grouping);
  const selected = new URLSearchParams(safeOverviewSearch(query.toString(), true));
  assert.equal(selected.get("budget_category"), query.get("budget_category"));
  assert.equal(selected.get("budget_grouping"), grouping);
  for (const name of ["budget_resource", "budget_start", "budget_end", "budget_as_of"]) assert.equal(selected.get(name), query.get(name));
  assert.equal(presentation.selectedFinancialReport(selected.toString()).kind, "selected");
  assert.equal(safeOverviewSearch(selected.toString(), true), safeOverviewSearch(query.toString(), true));
}
for (const mutation of [
  query => query.append("budget_category", "usage"),
  query => query.append("budget_grouping", "model"),
  query => query.set("budget_scope", "self"),
  query => query.set("budget_grouping", "unreviewed"),
  query => query.set("budget_category", "Invalid category"),
  query => query.set("budget_category", "a".repeat(65)),
  query => query.set("budget_unknown", "unreviewed"),
  query => query.delete("budget_category"),
  query => query.delete("budget_resource"),
]) {
  const query = new URLSearchParams(reportView);
  mutation(query);
  const rejected = new URLSearchParams(safeOverviewSearch(query.toString(), true));
  assert.equal(rejected.get("budget_selection"), "invalid");
  assert.equal(rejected.has("budget_category"), false);
  assert.equal(rejected.has("budget_grouping"), false);
  assert.equal(presentation.selectedFinancialReport(rejected.toString()).kind, "invalid");
}
assert.equal(new URLSearchParams(safeOverviewSearch(reportView.toString())).has("budget_category"), false, "detail selector leaked onto overview");
console.log("BUDGET SELECTION PURE: PASSED");
