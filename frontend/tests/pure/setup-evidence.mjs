import assert from "node:assert/strict";
import { currentSetupProof, sameSetupAuthority } from "../browser/m7/setup_evidence.mjs";
const connection = { account_id: "account", resource_id: "resource", record_version: 3, scope_generation: 2, lifecycle: "active", monitoring_preference: "enabled" };
const status = { account_id: "account", account_record_version: 4, account_lifecycle: "active", credential_status: { state: "stored", active_generation: 5 } };
const monitoring = { account_id: "account", resource_id: "resource", account_record_version: 4, connection_record_version: 3, scope_generation: 2, binding_generation: 5, lifecycle: "active", monitoring_preference: "enabled", verified_run_id: "run", verified_at: "2026-11-12T12:00:00Z" };
const run = { account_id: "account", resource_id: "resource", run_id: "run", state: "succeeded", report_id: "report", completed_at: "2026-11-12T12:00:00.000000Z", error_code: null };
assert.equal(currentSetupProof(status, connection, monitoring, run), true);
for (const [key, value] of [["account_id", "other"], ["resource_id", "other"], ["binding_generation", 6], ["scope_generation", 3], ["connection_record_version", 4], ["account_record_version", 5], ["monitoring_preference", "disabled"], ["verified_run_id", "old-run"]]) {
  assert.equal(currentSetupProof(status, connection, { ...monitoring, [key]: value }, run), false, key);
}
for (const change of [{ state: "running" }, { state: "failed" }, { report_id: null }, { account_id: "other" }, { resource_id: "other" }, { completed_at: "2026-11-12T11:00:00Z" }]) assert.equal(currentSetupProof(status, connection, monitoring, { ...run, ...change }), false);
assert.equal(currentSetupProof({ ...status, credential_status: { state: "pending", active_generation: 5 } }, connection, monitoring, run), false);
assert.equal(currentSetupProof({ ...status, account_lifecycle: "archived" }, connection, monitoring, run), false);

const original = { ...status, connections: [connection] };
assert.equal(sameSetupAuthority(original, { ...original }, connection.resource_id), true);
assert.equal(sameSetupAuthority(original, { ...original, credential_status: { state: "stored", active_generation: 6 } }, connection.resource_id), false);
assert.equal(sameSetupAuthority(original, { ...original, connections: [{ ...connection, scope_generation: 3 }] }, connection.resource_id), false);
const nextRun = { ...run, run_id: "next-run", report_id: "next-report", completed_at: "2026-11-12T12:05:00Z" };
assert.equal(currentSetupProof(status, connection, { ...monitoring, verified_run_id: nextRun.run_id, verified_at: nextRun.completed_at }, nextRun), true);
assert.equal(run.report_id, "report");
console.log("M7 setup evidence pure checks passed");
