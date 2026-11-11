"use strict";

import assert from "node:assert/strict";
import { checkEligibility, pendingRun, matchesCheckRun, advanceFinancialRead, restoreCheckIntent } from "../../src/features/accounts/billingCheckPresentation.ts";

// Pure policy values only: never credentials or simulated external responses.
const connection = { provider_key: "claude", lifecycle: "pending", account_id: "account", resource_id: "resource" };
const status = { account_lifecycle: "pending", credential_status: { state: "missing", active_generation: null } };
assert.equal(checkEligibility(status, connection).allowed, false);
assert.match(checkEligibility(status, connection).reason, /Store a credential locally/);
assert.equal(checkEligibility({ ...status, credential_status: { state: "stored", active_generation: 1 } }, connection).allowed, true);
assert.equal(checkEligibility({ ...status, credential_status: { state: "pending", active_generation: 1 } }, connection).allowed, false);
assert.equal(checkEligibility({ ...status, account_lifecycle: "archived" }, connection).allowed, false);
assert.equal(checkEligibility(status, { ...connection, provider_key: "codex" }).allowed, false);
assert.doesNotMatch(checkEligibility(status, { ...connection, provider_key: "codex" }).reason, /unsupported/i);
assert.equal(checkEligibility({ ...status, credential_status: null }, connection).allowed, false);
assert.equal(pendingRun("committing"), true);
assert.equal(pendingRun("queued"), true);
assert.equal(pendingRun("succeeded"), false);
assert.equal(pendingRun("failed"), false);
const intent = { accountId: "account", resourceId: "resource", runId: "run" };
assert.equal(matchesCheckRun(intent, { account_id: "account", resource_id: "resource", run_id: "run" }), true);
assert.equal(matchesCheckRun(intent, { account_id: "different", resource_id: "resource", run_id: "run" }), false);
assert.equal(matchesCheckRun(intent, { account_id: "account", resource_id: "different", run_id: "run" }), false);
assert.equal(matchesCheckRun(intent, { account_id: "account", resource_id: "resource", run_id: "different" }), false);
const query = { period_start: "2026-11-03T00:00:00Z", period_end: "2026-11-10T00:00:00Z", as_of: "2026-11-10T23:59:00Z" };
assert.deepEqual(advanceFinancialRead(query, new Date("2026-11-11T00:01:00Z")), { ...query, as_of: "2026-11-11T00:01:00.000Z" });
const retained = { accountId: "account", resourceId: "resource", accountVersion: 1, connectionVersion: 2,
  scopeGeneration: 1, credentialGeneration: 1, idempotencyKey: "a".repeat(32), runId: null, deadlineAt: null };
assert.deepEqual(restoreCheckIntent(JSON.stringify(retained), "account"), retained);
assert.equal(restoreCheckIntent(JSON.stringify(retained), "different"), null);
assert.equal(restoreCheckIntent(JSON.stringify({ ...retained, unexpected: null }), "account"), null);
assert.equal(restoreCheckIntent(JSON.stringify({ ...retained, accountVersion: 0 }), "account"), null);
assert.equal(restoreCheckIntent(JSON.stringify({ ...retained, runId: "run" }), "account"), null);
assert.equal(restoreCheckIntent("not-json", "account"), null);
assert.equal(restoreCheckIntent(" ".repeat(4097), "account"), null);
console.log("BILLING CHECK PRESENTATION PURE: PASSED");
