"use strict";

import assert from "node:assert/strict";

import {
  appendCapacityHistoryPage,
  capacityHistoryContinuation,
} from "../../src/shared/api/client.ts";

const availability = Object.freeze({
  as_of: "2026-09-24T10:00:00Z",
  reason_code: "observations_available",
  state: "available",
});

function point(observationId, observedAt) {
  return Object.freeze({ observation_id: observationId, observed_at: observedAt });
}

function page({
  cursor,
  hasMore,
  items,
  metric = "remaining_ratio",
  seriesKind = "poll_snapshot",
  subjectId = "account-live-owner",
}) {
  return Object.freeze({
    availability,
    items: Object.freeze(items),
    metric,
    page: Object.freeze({ has_more: hasMore, limit: 200, next_cursor: cursor }),
    series_kind: seriesKind,
    subject_id: subjectId,
  });
}

const firstPoint = point("observation-001", "2026-09-24T10:00:00Z");
const secondPoint = point("observation-002", "2026-09-24T09:00:00Z");
const firstPage = page({ cursor: "opaque-next-page", hasMore: true, items: [firstPoint] });
const finalPage = page({ cursor: null, hasMore: false, items: [secondPoint] });

assert.deepEqual(capacityHistoryContinuation(firstPage.page), {
  kind: "available",
  cursor: "opaque-next-page",
});
assert.deepEqual(capacityHistoryContinuation(finalPage.page), { kind: "complete" });
assert.deepEqual(
  capacityHistoryContinuation({ has_more: true, limit: 200, next_cursor: null }),
  { kind: "invalid" },
);
assert.deepEqual(
  capacityHistoryContinuation({ has_more: false, limit: 200, next_cursor: "unexpected-cursor" }),
  { kind: "invalid" },
);

const merged = appendCapacityHistoryPage([firstPage], finalPage);
assert.equal(merged.ok, true);
if (merged.ok) {
  assert.equal(merged.pages.length, 2);
  assert.strictEqual(merged.pages[0], firstPage);
  assert.strictEqual(merged.pages[1], finalPage);
  assert.strictEqual(merged.pages[0].items[0], firstPoint);
  assert.strictEqual(merged.pages[1].items[0], secondPoint);
}

assert.deepEqual(
  appendCapacityHistoryPage([], finalPage),
  { ok: false, reason: "history_page_sequence_missing" },
);

const mismatched = appendCapacityHistoryPage(
  [firstPage],
  page({ cursor: null, hasMore: false, items: [secondPoint], metric: "used" }),
);
assert.deepEqual(mismatched, { ok: false, reason: "history_page_query_mismatch" });

const duplicate = appendCapacityHistoryPage(
  [firstPage],
  page({ cursor: null, hasMore: false, items: [firstPoint] }),
);
assert.deepEqual(duplicate, { ok: false, reason: "history_page_duplicate_observation" });

console.log("CAPACITY HISTORY PAGINATION PURE: PASSED");
