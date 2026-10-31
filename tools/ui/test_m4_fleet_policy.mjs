import test from "node:test";
import assert from "node:assert/strict";

import {
  buildFleetWitnessV1,
  buildFleetRuntimeWitnessV1,
  isExactRenderedQuotaProvenanceV1,
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

const quotaProvenance = Object.freeze({
  source_id: "claude.usage.ax-screen-reader.v1",
  adapter_id: "agentmonitor.claude",
  adapter_version: "1.0.3",
  parser_version: "1.0.3",
  provider_version: "2.1.289",
  decision_reference: "A01-M03-CLAUDE-2-1-289-001",
});

const liveLocations = {
  availability: { state: "available" },
  truncated: false,
  items: [{
    pid: 1234,
    start_time_ticks: 5678,
    platform_scope_id: "a".repeat(64),
    provider_key: "claude",
    state: "running",
    account_correlation: "unresolved",
    observed_at: "2026-10-06T10:00:01Z",
    association_key: "b".repeat(64),
    association_record_version: 3,
    account_association: {
      state: "owner_confirmed",
      account_id: "account-1",
      principal_id: "dashboard-owner",
      confirmed_at: "2026-10-06T09:00:00Z",
      record_version: 3,
    },
  }],
};

test("rendered quota provenance requires the exact approved Claude version tuple", () => {
  const rendered = {
    Source: "claude.usage.ax-screen-reader.v1",
    Adapter: "agentmonitor.claude · 1.0.3",
    "Provider version": "2.1.289",
  };

  assert.equal(isExactRenderedQuotaProvenanceV1(rendered), true);
  for (const [field, value] of [
    ["Source", "claude.usage.ax.v1"],
    ["Adapter", "agentmonitor.claude · 1.0.2"],
    ["Provider version", "2.1.290"],
  ]) {
    assert.equal(isExactRenderedQuotaProvenanceV1({
      ...rendered,
      [field]: value,
    }), false);
  }
});

test("a current owner-confirmed process supplies the selected-fleet runtime witness", () => {
  const witness = buildFleetRuntimeWitnessV1(
    liveLocations,
    records.map(record => record.accountId),
  );

  assert.deepEqual(witness, {
    owner_confirmed_live_process_count: 1,
    owner_confirmed_live_account_count: 1,
  });
});

test("runtime witness rejects unavailable, unselected, or unguarded process links", () => {
  const selectedAccountIds = records.map(record => record.accountId);
  const rejected = [
    { ...liveLocations, availability: { state: "unavailable" } },
    { ...liveLocations, items: [] },
    {
      ...liveLocations,
      items: liveLocations.items.map(item => ({
        ...item,
        account_association: { ...item.account_association, account_id: "account-other" },
      })),
    },
    {
      ...liveLocations,
      items: liveLocations.items.map(item => ({
        ...item,
        association_record_version: item.association_record_version + 1,
      })),
    },
    {
      ...liveLocations,
      items: liveLocations.items.map(item => ({
        ...item,
        account_association: null,
      })),
    },
  ];

  for (const candidate of rejected) {
    assert.throws(
      () => buildFleetRuntimeWitnessV1(candidate, selectedAccountIds),
      /owner_confirmed_selected_live_process_required/,
    );
  }
});

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

test("fresh lineage requires the exact post-restart committed run and observations", () => {
  const candidate = {
    accountId: "account-1",
    identity: { account_id: "account-1", collection_run_id: "run-new" },
    run: {
      run_id: "run-new", account_id: "account-1", state: "succeeded",
      outcome_code: "succeeded", error_code: null,
      source_id: "claude.usage.ax-screen-reader.v1",
      adapter_version: "1.0.3", provider_version: "2.1.289",
      requested_at: "2026-10-03T10:00:01Z",
      completed_at: "2026-10-03T10:00:02Z",
      observation_ids: ["observation-new", "observation-week"],
    },
    windows: [{
      window_key: "current_session",
      subject: { account_id: "account-1" }, freshness: "fresh",
      collection_run_id: "run-new", current_observation_id: "observation-new",
      provenance: { ...quotaProvenance },
    }, {
      window_key: "current_week_all_models",
      subject: { account_id: "account-1" }, freshness: "fresh",
      collection_run_id: "run-new", current_observation_id: "observation-week",
      provenance: { ...quotaProvenance },
    }],
    history: {
      availability: { state: "available" },
      items: [{
        subject: { account_id: "account-1" }, collection_run_id: "run-new",
        observation_id: "observation-new", window_key: "current_session",
        completeness: "complete",
        provenance: { ...quotaProvenance },
      }, {
        subject: { account_id: "account-1" }, collection_run_id: "run-new",
        observation_id: "observation-week", window_key: "current_week_all_models",
        completeness: "complete",
        provenance: { ...quotaProvenance },
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
  assert.equal(isFreshCollectionLineageV1({
    ...candidate,
    history: {
      ...candidate.history,
      items: candidate.history.items.map((point, index) => index === 0
        ? { ...point, window_key: "current_week_all_models" }
        : point),
    },
  }, "2026-10-03T10:00:00.500Z"), false);
  assert.equal(isFreshCollectionLineageV1({
    ...candidate,
    windows: candidate.windows.map((window, index) => index === 1
      ? { ...window, current_observation_id: "observation-new" }
      : window),
  }, "2026-10-03T10:00:00.500Z"), false);
  assert.equal(isFreshCollectionLineageV1({
    ...candidate,
    windows: candidate.windows.slice(0, 1),
  }, "2026-10-03T10:00:00.500Z"), false);
  assert.equal(isFreshCollectionLineageV1({
    ...candidate,
    history: {
      ...candidate.history,
      items: candidate.history.items.map(point => ({
        ...point, completeness: "partial",
      })),
    },
  }, "2026-10-03T10:00:00.500Z"), false);
  for (const [field, value] of [
    ["source_id", "unexpected.source"],
    ["adapter_id", "unexpected.adapter"],
    ["adapter_version", "1.0.2"],
    ["parser_version", "1.0.2"],
    ["provider_version", "2.1.288"],
    ["decision_reference", "A01-M03-CLAUDE-2-1-288-001"],
  ]) {
    const staleProvenance = { ...quotaProvenance, [field]: value };
    assert.equal(isFreshCollectionLineageV1({
      ...candidate,
      windows: candidate.windows.map((window, index) => index === 0
        ? { ...window, provenance: staleProvenance }
        : window),
    }, "2026-10-03T10:00:00.500Z"), false);
    assert.equal(isFreshCollectionLineageV1({
      ...candidate,
      history: {
        ...candidate.history,
        items: candidate.history.items.map((point, index) => index === 0
          ? { ...point, provenance: staleProvenance }
          : point),
      },
    }, "2026-10-03T10:00:00.500Z"), false);
  }
  assert.equal(isFreshCollectionLineageV1({
    ...candidate,
    run: { ...candidate.run, state: "partial", outcome_code: "partial" },
    history: {
      ...candidate.history,
      items: candidate.history.items.map(point => ({
        ...point, completeness: "partial",
      })),
    },
  }, "2026-10-03T10:00:00.500Z"), true);
  assert.equal(isFreshCollectionLineageV1({
    ...candidate,
    run: { ...candidate.run, state: "partial", outcome_code: "partial" },
    history: {
      ...candidate.history,
      items: candidate.history.items.map((point, index) => ({
        ...point,
        completeness: "partial",
        provenance: { source_id: index === 0
          ? "claude.usage.ax-screen-reader.v1"
          : "unexpected.source" },
      })),
    },
  }, "2026-10-03T10:00:00.500Z"), false);
  assert.equal(isFreshCollectionLineageV1({
    ...candidate,
    run: {
      ...candidate.run, state: "partial", outcome_code: "partial",
      provider_version: "2.1.290",
    },
    history: {
      ...candidate.history,
      items: candidate.history.items.map(point => ({
        ...point, completeness: "partial",
      })),
    },
  }, "2026-10-03T10:00:00.500Z"), false);
  assert.equal(isFreshCollectionLineageV1({
    ...candidate,
    run: { ...candidate.run, state: "partial", outcome_code: "partial" },
    windows: candidate.windows.slice(0, 1),
    history: {
      ...candidate.history,
      items: candidate.history.items.map(point => ({
        ...point, completeness: "partial",
      })),
    },
  }, "2026-10-03T10:00:00.500Z"), false);
  assert.equal(isFreshCollectionLineageV1({
    ...candidate,
    run: { ...candidate.run, state: "partial", outcome_code: "partial" },
    history: {
      ...candidate.history,
      items: [{ ...candidate.history.items[0], completeness: "partial" }],
    },
  }, "2026-10-03T10:00:00.500Z"), false);
  for (const run of [
    { ...candidate.run, completed_at: "2026-10-03T09:59:59Z" },
    { ...candidate.run, account_id: "account-other" },
    { ...candidate.run, source_id: "unexpected.source" },
    { ...candidate.run, adapter_version: "1.0.2" },
    { ...candidate.run, provider_version: "2.1.290" },
    {
      ...candidate.run, state: "partial", outcome_code: "partial",
      adapter_version: "1.0.2",
    },
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
