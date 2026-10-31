"use strict";

import assert from "node:assert/strict";

import { quotaResetPresentation } from "../../src/features/command/quotaPresentation.ts";

assert.deepEqual(quotaResetPresentation("2026-10-07T12:34:56Z", "exact"), {
  dateTime: "2026-10-07T12:34:56Z",
  label: "Resets",
  precision: "exact",
});
assert.deepEqual(quotaResetPresentation(null, "unknown"), {
  dateTime: null,
  label: "Reset not reported",
  precision: "unknown",
});
assert.deepEqual(quotaResetPresentation("not-a-timestamp", "estimated"), {
  dateTime: null,
  label: "Reset not reported",
  precision: "estimated",
});

console.log("QUOTA RESET PRESENTATION PURE: PASSED");
