import test from "node:test";
import assert from "node:assert/strict";

import {
  buildFleetWitnessV1,
  isFreshCollectionLineageV1,
} from "./m4_fleet_policy.mjs";

const records = Array.from({ length: 6 }, (_, index) => ({
  accountId: `account-${index + 1}`,
  organizationId: index < 4 ? "organization-one" : "organization-two",
  administratorName: `owner${index + 1}@example.test`,
  observedEmail: `OWNER${index + 1}@example.test`,
  providerOrganization: `provider-organization-${index + 1}`,
  collectionRunId: `collection-run-${index + 1}`,
  currentHistoryMatched: true,
  freshAfterRestart: true,
  providerKey: "claude",
  lifecycle: "active",
  monitoringPreference: "enabled",
  effectiveMonitoringEnabled: true,
  effectiveMonitoringReason: "enabled",
  identityState: "owner_confirmed",
  accountRecordVersion: 1,
  accountRegistryRevision: index + 1,
  organizationRecordVersion: 1,
  organizationRegistryRevision: index < 4 ? 1 : 2,
}));

test("six expected distinct identities produce digest-only witness", () => {
  const witness = buildFleetWitnessV1(records, { event: "m4_fleet_witness" });

  assert.equal(witness.account_count, 6);
  assert.equal(witness.organization_count, 2);
  assert.equal(witness.distinct_identity_count, 6);
  assert.equal(witness.current_history_count, 6);
  assert.equal(witness.fresh_after_restart_count, 6);
  assert.match(witness.fleet_metadata_digest, /^[0-9a-f]{64}$/);
  assert.match(witness.identity_set_digest, /^[0-9a-f]{64}$/);
  assert.match(witness.collection_run_set_digest, /^[0-9a-f]{64}$/);
  assert.doesNotMatch(JSON.stringify(witness), /@example\.test/);
});

test("duplicate and wrong reported identities are rejected", () => {
  assert.throws(
    () => buildFleetWitnessV1(
      records.map((record, index) => index === 5
        ? { ...record, observedEmail: records[4].observedEmail, administratorName: records[4].administratorName }
        : record),
      { event: "m4_fleet_preflight" },
    ),
    /duplicate_reported_provider_identity/,
  );
  assert.throws(
    () => buildFleetWitnessV1(
      records.map((record, index) => index === 0
        ? { ...record, observedEmail: "unexpected@example.test" }
        : record),
      { event: "m4_fleet_preflight" },
    ),
    /registered_observed_identity_mismatch/,
  );
});

test("fresh lineage requires the exact post-restart successful run and observations", () => {
  const candidate = {
    accountId: "account-1",
    identity: { account_id: "account-1", collection_run_id: "run-new" },
    run: {
      run_id: "run-new", account_id: "account-1", state: "succeeded",
      source_id: "claude.usage.ax-screen-reader.v1",
      requested_at: "2026-10-03T10:00:01Z",
      completed_at: "2026-10-03T10:00:02Z",
      observation_ids: ["observation-new"],
    },
    windows: [{
      subject: { account_id: "account-1" }, freshness: "fresh",
      collection_run_id: "run-new", current_observation_id: "observation-new",
      provenance: { source_id: "claude.usage.ax-screen-reader.v1" },
    }],
    history: {
      availability: { state: "available" },
      items: [{
        subject: { account_id: "account-1" }, collection_run_id: "run-new",
        observation_id: "observation-new",
        provenance: { source_id: "claude.usage.ax-screen-reader.v1" },
      }],
    },
  };

  assert.equal(isFreshCollectionLineageV1(candidate, "2026-10-03T10:00:00.500Z"), true);
  assert.equal(isFreshCollectionLineageV1({
    ...candidate,
    run: { ...candidate.run, requested_at: "2026-10-03T09:59:59Z" },
  }, "2026-10-03T10:00:00.500Z"), false);
  assert.equal(isFreshCollectionLineageV1({
    ...candidate,
    windows: [{ ...candidate.windows[0], current_observation_id: "observation-old" }],
  }, "2026-10-03T10:00:00.500Z"), false);
  for (const run of [
    { ...candidate.run, completed_at: "2026-10-03T09:59:59Z" },
    { ...candidate.run, account_id: "account-other" },
    { ...candidate.run, source_id: "unexpected.source" },
    { ...candidate.run, state: "partial" },
  ]) {
    assert.equal(isFreshCollectionLineageV1({ ...candidate, run }, "2026-10-03T10:00:00.500Z"), false);
  }
  assert.equal(isFreshCollectionLineageV1({
    ...candidate,
    history: {
      ...candidate.history,
      items: [{ ...candidate.history.items[0], observation_id: "observation-old" }],
    },
  }, "2026-10-03T10:00:00.500Z"), false);
});

test("a post-restart witness rejects even one account without fresh lineage", () => {
  assert.throws(
    () => buildFleetWitnessV1(
      records.map((record, index) => index === 5
        ? { ...record, freshAfterRestart: false }
        : record),
      { event: "m4_fleet_witness" },
    ),
    /fresh_post_restart_fleet_collection_required/,
  );
});

test("registry version drift changes the fleet metadata digest", () => {
  const before = buildFleetWitnessV1(records, { event: "m4_fleet_preflight" });
  const after = buildFleetWitnessV1(
    records.map((record, index) => index === 0
      ? { ...record, accountRecordVersion: record.accountRecordVersion + 1 }
      : record),
    { event: "m4_fleet_preflight" },
  );
  assert.notEqual(before.fleet_metadata_digest, after.fleet_metadata_digest);
});
