"use strict";

import assert from "node:assert/strict";
import { capacityHistoryMetric, readableUsd } from "../../src/features/command/quotaPresentation.ts";

// Pure presentation inputs only: no provider, database, clock or browser boundary.
const field = (unit, coefficient, scale = 0, availability = "available") => ({
  availability, value: coefficient === null ? null : { unit, coefficient, scale },
});
const ratio = { remaining_ratio: field("ratio", "75", 2), remaining: field("unknown", null) };
const credit = { remaining_ratio: field("ratio", null, 0, "unknown"), remaining: field("usd", "19898266", 5) };
assert.equal(readableUsd(credit.remaining), "$198.98266");
assert.equal(readableUsd(field("usd", "0")), "$0.00");
assert.equal(readableUsd(field("usd", "9007199254740993123", 5)), "$90071992547409.93123");
assert.equal(readableUsd(field("usd", "32", 2, "stale")), "$0.32");
assert.equal(readableUsd(field("usd", "32", 2, "unavailable")), null);
assert.equal(readableUsd(field("ratio", "50", 2)), null);
assert.equal(capacityHistoryMetric([credit]), "remaining");
assert.equal(capacityHistoryMetric([ratio]), "remaining_ratio");
assert.equal(capacityHistoryMetric([ratio, credit]), "remaining");
assert.equal(capacityHistoryMetric([{ ...credit, remaining: field("usd", "0", 0, "stale") }]), "remaining");
assert.equal(capacityHistoryMetric([]), "remaining_ratio");
console.log("NATIVE USD CAPACITY PURE: PASSED");
