"use strict";

import assert from "node:assert/strict";
import { canRetainFinancialReading } from "../../src/features/accounts/financialReadPresentation.ts";

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
console.log("FINANCIAL READ PRESENTATION PURE: PASSED");
