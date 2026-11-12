import assert from "node:assert/strict";
import { appendHistoryItems, historyContextKey, historyPageMatches } from "../../src/features/accounts/budgetHistoryPagination.ts";

// Constructed inputs exercise only pure context and pagination decisions.
const context = { accountId: "account", resourceId: "resource", reportId: "report", periodStart: "2026-11-01T00:00:00Z", periodEnd: "2026-11-08T00:00:00Z", asOf: "2026-11-08T01:00:00.123456Z" };
const report = { account_id: "account", resource_id: "resource", report_id: "report", requested_period: { start: context.periodStart, end: context.periodEnd } };
assert.equal(historyPageMatches(context, report, context.asOf), true);
assert.equal(historyPageMatches(context, report, "2026-11-08T01:00:00.123Z"), false);
assert.equal(historyPageMatches(context, { ...report, report_id: "other" }, context.asOf), false);
assert.equal(historyPageMatches(context, { ...report, account_id: "other" }, context.asOf), false);
assert.equal(historyPageMatches(context, { ...report, resource_id: "other" }, context.asOf), false);
assert.equal(historyPageMatches(context, { ...report, requested_period: { ...report.requested_period, end: "2026-11-09T00:00:00Z" } }, context.asOf), false);
assert.equal(historyContextKey({ ...context, periodStart: "2026-11-01T00:00:00.000000Z" }), historyContextKey(context));
const key = historyContextKey(context);
const cost = { kind: "cost", cost: { bucket_key: "same-key" }, usage: null };
const usage = { kind: "usage", cost: null, usage: { bucket_key: "same-key" } };
const first = appendHistoryItems(null, key, [cost], null, "cursor-one", true);
assert.deepEqual(first.items, [cost]);
const next = appendHistoryItems(first, key, [usage], "cursor-one", null, false);
assert.deepEqual(next.items, [cost, usage]);
assert.equal(next.nextCursor, null);
assert.throws(() => appendHistoryItems(first, key, [cost], "cursor-one", null, false), /duplicate/);
assert.throws(() => appendHistoryItems(first, key, [usage], "wrong-cursor", null, false), /cursor/);
assert.throws(() => appendHistoryItems(first, key, [usage], "cursor-one", "cursor-one", true), /cursor/);
assert.throws(() => appendHistoryItems(first, key, [], "cursor-one", "cursor-two", true), /page/);
assert.throws(() => appendHistoryItems(first, "different-context", [usage], "cursor-one", null, false), /context/);
assert.throws(() => appendHistoryItems(null, key, [{ ...cost, usage: usage.usage }], null, null, false), /item/);
assert.throws(() => appendHistoryItems(null, key, [cost], null, "cursor", false), /page/);
assert.deepEqual(first.items, [cost]); // A rejected later page cannot discard existing facts.
assert.equal(first.nextCursor, "cursor-one");
assert.deepEqual(appendHistoryItems(first, "new-context", [usage], null, null, false).items, [usage]);
assert.deepEqual(appendHistoryItems(null, key, [], null, null, false).items, []);
console.log("budget-history-pagination: passed");
