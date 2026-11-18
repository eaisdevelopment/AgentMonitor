import assert from "node:assert/strict";
import { appendFundsHistoryPage, fundsHistoryContextKey, fundsHistoryPlot } from "../../src/features/accounts/budgetFundsHistoryPresentation.ts";

// Constructed values only exercise pure validation and visual arithmetic, no I/O.
const context = { accountId: "account", resourceId: "included", windowId: "window", sourceId: "source", currency: "USD", asOf: "2026-11-12T12:00:00.123456Z", periodStart: "2026-11-05T00:00:00Z", periodEnd: "2026-11-12T12:00:00Z" };
const point = (id = "observation", coefficient = "900719925474099312345", scale = 3) => ({
  observation_id: id, subject: { account_id: "account", resource_id: "included" },
  window_id: "window", window_key: "included_balance", provenance: { source_id: "source" },
  metric: "remaining", series_kind: "poll_snapshot", native_unit: "usd",
  observed_at: "2026-11-12T10:00:00Z", collected_at: "2026-11-12T10:00:01Z", stored_at: "2026-11-12T10:00:02Z",
  value: { availability: "available", value: { coefficient, scale, unit: "usd" }, value_kind: "provider_reported", precision: "exact", reason_code: null },
});
const page = (items, next = null) => ({ subject_id: context.accountId, metric: "remaining", series_kind: "poll_snapshot", availability: { state: "available", as_of: context.asOf, reason_code: "history_available" }, items, page: { limit: 50, has_more: next !== null, next_cursor: next } });
const initial = point();
const first = appendFundsHistoryPage(null, context, page([initial], "page-two"), null);
assert.equal(first.items[0], initial);
const absent = { ...page([]), availability: { state: "unavailable", reason_code: "capacity_history_absent", as_of: context.asOf } };
assert.deepEqual(appendFundsHistoryPage(null, context, absent, null).items, []);
assert.throws(() => appendFundsHistoryPage(null, context, { ...absent, availability: { ...absent.availability, reason_code: "source_failed" } }, null), /page/);
assert.throws(() => appendFundsHistoryPage(null, context, { ...absent, items: [initial] }, null), /page/);
assert.equal(fundsHistoryContextKey(context), fundsHistoryContextKey({ ...context, periodStart: "2026-11-05T00:00:00.000000+00:00" }));
for (const changed of [
  { subject: { account_id: "another", resource_id: "included" } },
  { subject: { account_id: "account", resource_id: "purchased" } },
  { window_id: "other" }, { provenance: { source_id: "other" } },
  { metric: "used" }, { series_kind: "derived" }, { native_unit: "eur" },
  { value: { ...initial.value, value: { ...initial.value.value, unit: "eur" } } },
  { observed_at: "2026-11-12T12:00:00Z" }, { observed_at: "2026-11-04T23:59:59Z" },
  { stored_at: "2026-11-12T12:00:00.123457Z" }, { collected_at: "2026-11-12T12:00:00.123457Z" },
]) assert.throws(() => appendFundsHistoryPage(null, context, page([{ ...initial, ...changed }]), null), /funds_history/);
assert.throws(() => appendFundsHistoryPage(null, context, { ...page([]), subject_id: "other" }, null), /page/);
assert.throws(() => appendFundsHistoryPage(null, context, { ...page([]), availability: { ...page([]).availability, as_of: "2026-11-12T12:00:00.123Z" } }, null), /page/);
assert.throws(() => appendFundsHistoryPage(first, context, page([point("next")]), "wrong"), /cursor/);
assert.throws(() => appendFundsHistoryPage(first, context, page([point("next")], "page-two"), "page-two"), /cursor/);
assert.throws(() => appendFundsHistoryPage(first, { ...context, resourceId: "purchased" }, page([point("next")]), "page-two"), /context/);
assert.throws(() => appendFundsHistoryPage(first, context, page([initial]), "page-two"), /duplicate/);
assert.throws(() => appendFundsHistoryPage(first, context, page([{ ...point("next"), window_key: "changed" }]), "page-two"), /window/);
assert.throws(() => appendFundsHistoryPage(null, context, page([initial, initial]), null), /duplicate/);
assert.throws(() => appendFundsHistoryPage(null, context, page([], "cursor"), null), /page/);
assert.throws(() => appendFundsHistoryPage(null, context, page(Array.from({ length: 51 }, (_, i) => point(String(i)))), null), /page/);
const unknown = { ...point("unknown"), native_unit: null, value: { availability: "unknown", value: null, value_kind: "unknown", precision: "unknown", reason_code: "source_missing" } };
const unsupported = { ...point("unsupported"), value: { ...initial.value, availability: "unsupported" } };
const negative = point("negative", "-4503599627370496561725", 4);
const zero = point("zero", "0", 0);
const result = appendFundsHistoryPage(first, context, page([unknown, unsupported, negative, zero]), "page-two");
assert.equal(result.items.length, 5);
const plot = fundsHistoryPlot(result.items);
assert.deepEqual(plot.map(value => value.magnitudeBasisPoints), [10000, null, null, 5000, 0]);
assert.deepEqual(plot.map(value => value.direction), ["positive", null, null, "negative", "zero"]);
assert.equal(plot[0].point.observation_id, initial.observation_id);
assert.equal(plot[0].point.value.value.coefficient, initial.value.value.coefficient);
assert.equal(plot[1].point, unknown);
assert.deepEqual(first.items, [initial]); // A rejected/appended page never mutates retained facts.
for (const value of [
  { coefficient: "1e9", scale: 0, unit: "usd" },
  { coefficient: "1", scale: 19, unit: "usd" },
  { coefficient: "-0", scale: 0, unit: "usd" },
  { coefficient: "10", scale: 1, unit: "usd" },
]) assert.throws(() => appendFundsHistoryPage(null, context, page([{ ...initial, value: { ...initial.value, value } }]), null), /amount/);
let bounded = null;
for (let p = 0; p < 4; p++) bounded = appendFundsHistoryPage(bounded, context, page(Array.from({ length: 50 }, (_, i) => point(`p${p}-${i}`)), `page-${p + 1}`), p === 0 ? null : `page-${p}`);
assert.equal(bounded.items.length, 200);
assert.equal(appendFundsHistoryPage(bounded, context, page([point("older")]), "page-4").items.length, 201);
console.log("budget-funds-history: passed");
