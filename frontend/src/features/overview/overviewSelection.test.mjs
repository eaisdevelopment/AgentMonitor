import assert from "node:assert/strict";
import { registerHooks } from "node:module";
// Resolve the real source modules exactly as the bundler does; no I/O methods
// are invoked by these pure sanitizer/parser checks.
registerHooks({ resolve(specifier, context, nextResolve) {
  const paths = {
    "../shared/api/client": new URL("../../shared/api/client.ts", import.meta.url).href,
    "../features/overview/overviewSelection": new URL("./overviewSelection.ts", import.meta.url).href,
    "../../generated/api": new URL("../../generated/api/index.ts", import.meta.url).href,
  };
  return nextResolve(paths[specifier] ?? specifier, context);
} });
let selection;
try { selection = await import("./overviewSelection.ts"); }
catch (error) { if (error.code !== "ERR_MODULE_NOT_FOUND") throw error; throw new Error("overview_selection_missing"); }
const { safeOverviewSearch, overviewSelection } = selection;
assert.equal(safeOverviewSearch("?provider_key=ollama&resource_type=api&token=discard&organization_ids=org_b,org_a&include_ungrouped=true"), "?organization_ids=org_a%2Corg_b&include_ungrouped=true&provider_key=ollama&resource_type=api");
assert.equal(safeOverviewSearch("?organization_ids=&include_ungrouped=false"), "?organization_ids=&include_ungrouped=false");
assert.equal(overviewSelection("?organization_ids=&include_ungrouped=false").organizationIds.length, 0);
assert.equal(overviewSelection("").organizationIds, null);
assert.equal(safeOverviewSearch("?provider_key=unknown&resource_type=other&quota_sort=money:ascending&budget_report=https://bad&next=https://bad"), "");
assert.equal(safeOverviewSearch("?budget_resource=resource-1&budget_report=report-1"), "");
assert.equal(safeOverviewSearch("?period_start=2026-11-04T00:00:00Z&period_end=2026-11-11T00:00:00Z&as_of=2026-11-11T12:00:00Z"), "?period_start=2026-11-04T00%3A00%3A00.000Z&period_end=2026-11-11T00%3A00%3A00.000Z&as_of=2026-11-11T12%3A00%3A00.000Z");
assert.equal(safeOverviewSearch("?period_start=2026-11-10T00:00:00Z&period_end=2026-11-11T00:00:00Z"), "");
assert.equal(overviewSelection("?range=7&period_start=2026-10-12T00:00:00Z&period_end=2026-11-11T00:00:00Z").days, 30);
const { safeLocation } = await import("../../app/sessionBootstrap.ts");
const { selectedFinancialReport } = await import("../accounts/financialReadPresentation.ts");
const valid = "budget_resource=resource-1&budget_report=report-1&budget_start=2026-11-04T00:00:00Z&budget_end=2026-11-11T00:00:00Z&budget_as_of=2026-11-11T12:00:00Z";
for (const malformed of [
  valid.replace("report-1", "https://invalid.example/private"),
  valid + "&budget_report=other-report",
  valid + "&budget_resource=resource-1",
  valid + "&budget_start=2026-11-04T00:00:00Z",
  valid.replace("2026-11-04", "2026-11-05"),
  valid.replace("2026-11-11T12:00:00Z", "2026-11-10T12:00:00Z"),
  valid.replace("budget_resource=resource-1&", ""),
  valid.replace("budget_as_of=2026-11-11T12:00:00Z", "budget_as_of=not-a-time"),
  valid.replaceAll("2026-11-04", "2026-02-30").replaceAll("2026-11-11", "2026-03-09"),
  valid.replace("report-1", ""), valid + "&budget_unrecognized=value",
  "budget_selection=invalid", "budget_selection=other", "budget_report=report-1", "budget_start=2026-11-04T00:00:00Z",
]) {
  const location = safeLocation(`/accounts/account-1?${malformed}`);
  assert.equal(location.search, "?budget_selection=invalid");
  assert.equal(selectedFinancialReport(location.search).kind, "invalid");
  const login = new URLSearchParams({ next: location.route + location.search });
  const restored = safeLocation(login.get("next"));
  const reloaded = safeLocation(restored.route + restored.search);
  assert.equal(reloaded.search, "?budget_selection=invalid");
  assert.equal(selectedFinancialReport(reloaded.search).kind, "invalid");
}
const selected = safeLocation(`/accounts/account-1?${valid}`);
assert.equal(selectedFinancialReport(selected.search).kind, "selected");
const fundsOnly = safeLocation(`/accounts/account-1?${valid.replace("budget_report=report-1&", "")}`);
assert.equal(selectedFinancialReport(fundsOnly.search).kind, "selected");
assert.equal(selectedFinancialReport(safeLocation("/accounts/account-1?provider_key=ollama").search).kind, "none");
assert.equal(safeOverviewSearch("?quota_sort=quota:descending&financial_sort=state:ascending&budget_resource=resource-1&budget_report=report-1&range=30", true), "?range=30&quota_sort=quota%3Adescending&financial_sort=state%3Aascending&budget_selection=invalid");
console.log("OVERVIEW SELECTION PURE: PASSED");
