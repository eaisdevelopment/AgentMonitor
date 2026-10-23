"use strict";

import assert from "node:assert/strict";

import { appendAlertHistoryPageV1 } from "../../src/shared/api/alertHistoryPagination.ts";

const alertId = "alert-owner-live";
const availability = Object.freeze({
  as_of: "2026-10-23T10:00:00Z",
  reason_code: "alert_history_available",
  state: "available",
});

function entry(sequence, selectedAlertId = alertId, eventId = `event-${sequence}`) {
  return Object.freeze({
    aggregate_sequence: sequence,
    alert_id: selectedAlertId,
    current_lifecycle: sequence === 1 ? "open" : "recovered",
    current_severity: sequence === 1 ? "warning" : "information",
    event_id: eventId,
    occurred_at: new Date(Date.UTC(2026, 9, 23, 10, 0, sequence)).toISOString(),
    previous_lifecycle: sequence === 1 ? null : "open",
    previous_severity: sequence === 1 ? null : "warning",
    reason_code: "capacity_remaining",
    source_event_id: `source-${sequence}`,
    transition: sequence === 1 ? "opened" : "recovered",
  });
}

function entries(from, through) {
  return Array.from({ length: through - from + 1 }, (_, index) => entry(from + index));
}

function page(items, { hasMore = false, nextCursor = null, limit = 200 } = {}) {
  return Object.freeze({
    availability,
    items: Object.freeze(items),
    page: Object.freeze({ has_more: hasMore, limit, next_cursor: nextCursor }),
  });
}

function append(current, document, cursor = null) {
  return appendAlertHistoryPageV1(current, document, { alertId, cursor });
}

const terminal192 = append(null, page(entries(1, 192)));
assert.equal(terminal192.ok, true);
if (terminal192.ok) {
  assert.equal(terminal192.state.entries.length, 192);
  assert.equal(terminal192.state.pageCount, 1);
  assert.equal(terminal192.state.terminal, true);
  assert.equal(terminal192.state.nextCursor, null);
}

const terminal200 = append(null, page(entries(1, 200)));
assert.equal(terminal200.ok, true);
if (terminal200.ok) {
  assert.equal(terminal200.state.entries.length, 200);
  assert.equal(terminal200.state.entries.at(-1)?.aggregate_sequence, 200);
  assert.equal(terminal200.state.terminal, true);
}

const first201 = append(null, page(entries(1, 200), {
  hasMore: true,
  nextCursor: "opaque-page-two",
}));
assert.equal(first201.ok, true);
if (!first201.ok) throw new Error("first_page_expected");
const terminal201 = append(
  first201.state,
  page([entry(201)]),
  "opaque-page-two",
);
assert.equal(terminal201.ok, true);
if (terminal201.ok) {
  assert.equal(terminal201.state.entries.length, 201);
  assert.strictEqual(terminal201.state.entries[0], first201.state.entries[0]);
  assert.equal(terminal201.state.entries.at(-1)?.aggregate_sequence, 201);
  assert.equal(terminal201.state.pageCount, 2);
  assert.equal(terminal201.state.terminal, true);
}

const invalidInitialDocuments = [
  page([entry(1)], { limit: 199 }),
  { ...page([entry(1)]), availability: { ...availability, state: "unavailable" } },
  page(entries(1, 201)),
  page([entry(1, "another-alert")]),
  page([entry(1), entry(2, alertId, "event-1")]),
  page([entry(1), entry(1, alertId, "event-2")]),
  page([entry(2), entry(1)]),
  page([], { hasMore: true, nextCursor: "next" }),
  page([entry(1)], { hasMore: true, nextCursor: null }),
  page([entry(1)], { hasMore: true, nextCursor: "" }),
  page([entry(1)], { hasMore: true, nextCursor: "bad\ncursor" }),
  page([entry(1)], { hasMore: true, nextCursor: "x".repeat(1025) }),
  page([entry(1)], { hasMore: false, nextCursor: "unexpected" }),
];
for (const document of invalidInitialDocuments) {
  assert.equal(append(null, document).ok, false);
}
assert.equal(appendAlertHistoryPageV1(null, page([entry(1)]), {
  alertId,
  cursor: "unexpected-first-cursor",
}).ok, false);

const progressing = append(null, page([entry(1)], {
  hasMore: true,
  nextCursor: "cursor-one",
}));
assert.equal(progressing.ok, true);
if (!progressing.ok) throw new Error("progressing_page_expected");
const invalidLaterPages = [
  [page([entry(2)]), "wrong-request-cursor"],
  [page([entry(2)], { hasMore: true, nextCursor: "cursor-one" }), "cursor-one"],
  [page([entry(2)], { hasMore: true, nextCursor: "bad\tcursor" }), "cursor-one"],
  [page([entry(2)], { hasMore: false, nextCursor: "cursor-two" }), "cursor-one"],
  [page([entry(1, alertId, "event-two")]), "cursor-one"],
  [page([entry(2, alertId, "event-1")]), "cursor-one"],
  [page([entry(2, "another-alert")]), "cursor-one"],
];
for (const [document, cursor] of invalidLaterPages) {
  assert.equal(append(progressing.state, document, cursor).ok, false);
}

let bounded = null;
let boundedCursor = null;
for (let sequence = 1; sequence <= 199; sequence += 1) {
  const nextCursor = `cursor-${sequence}`;
  const decision = append(
    bounded,
    page([entry(sequence)], { hasMore: true, nextCursor }),
    boundedCursor,
  );
  assert.equal(decision.ok, true);
  if (!decision.ok) throw new Error("bounded_page_expected");
  bounded = decision.state;
  boundedCursor = nextCursor;
}
assert.notEqual(bounded, null);
assert.equal(append(
  bounded,
  page([entry(200)], { hasMore: true, nextCursor: "cursor-200" }),
  boundedCursor,
).ok, false);
assert.equal(append(bounded, page([entry(200)]), boundedCursor).ok, true);

console.log("ALERT HISTORY PAGINATION PURE: PASSED");
