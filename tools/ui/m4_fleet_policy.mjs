import { createHash } from "node:crypto";

const sha256 = (value) => createHash("sha256").update(JSON.stringify(value)).digest("hex");
const text = (value, maximum = 512) => typeof value === "string"
  && value.length > 0 && value.length <= maximum;
const normalizeIdentity = (value) => {
  if (!text(value, 320)) throw new Error("registered_observed_identity_mismatch");
  const normalized = value.normalize("NFKC").trim().toLocaleLowerCase("en-US");
  if (!normalized.includes("@") || normalized.startsWith("@") || normalized.endsWith("@")) {
    throw new Error("registered_observed_identity_mismatch");
  }
  return normalized;
};

export function isFreshCollectionLineageV1(candidate, serviceStartedAt) {
  const lowerBound = Date.parse(serviceStartedAt);
  const requestedAt = Date.parse(candidate?.run?.requested_at);
  const completedAt = Date.parse(candidate?.run?.completed_at);
  const observationIds = candidate?.run?.observation_ids;
  const windows = candidate?.windows;
  const history = candidate?.history;
  if (!Number.isFinite(lowerBound) || !Number.isFinite(requestedAt)
      || !Number.isFinite(completedAt) || requestedAt < lowerBound
      || completedAt < requestedAt || candidate?.run?.run_id !== candidate?.identity?.collection_run_id
      || candidate?.run?.account_id !== candidate?.accountId
      || candidate?.identity?.account_id !== candidate?.accountId
      || candidate?.run?.state !== "succeeded"
      || candidate?.run?.source_id !== "claude.usage.ax-screen-reader.v1"
      || !Array.isArray(observationIds) || observationIds.length === 0
      || !Array.isArray(windows) || windows.length === 0
      || !windows.every(window => window?.subject?.account_id === candidate.accountId
        && window.freshness === "fresh"
        && window.collection_run_id === candidate.run.run_id
        && text(window.current_observation_id, 128)
        && observationIds.includes(window.current_observation_id)
        && window.provenance?.source_id === "claude.usage.ax-screen-reader.v1")
      || history?.availability?.state !== "available" || !Array.isArray(history.items)) {
    return false;
  }
  const currentObservationIds = new Set(windows.map(window => window.current_observation_id));
  return history.items.some(point => point?.subject?.account_id === candidate.accountId
    && point.collection_run_id === candidate.run.run_id
    && currentObservationIds.has(point.observation_id)
    && observationIds.includes(point.observation_id)
    && point.provenance?.source_id === "claude.usage.ax-screen-reader.v1");
}

export function buildFleetWitnessV1(records, { event }) {
  if (!Array.isArray(records) || records.length !== 6
      || !["m4_fleet_preflight", "m4_fleet_witness"].includes(event)) {
    throw new Error("six_owner_outcomes_required");
  }
  const normalized = records.map((record) => {
    if (!record || !text(record.accountId, 64) || !text(record.organizationId, 64)
        || !text(record.collectionRunId, 128)
        || ![true, false].includes(record.currentHistoryMatched)
        || ![true, false].includes(record.freshAfterRestart)
        || !(record.providerOrganization === null || text(record.providerOrganization))
        || record.providerKey !== "claude" || record.lifecycle !== "active"
        || record.monitoringPreference !== "enabled"
        || record.effectiveMonitoringEnabled !== true
        || !text(record.effectiveMonitoringReason, 128)
        || !["matched", "owner_confirmed"].includes(record.identityState)
        || !Number.isInteger(record.accountRecordVersion) || record.accountRecordVersion < 1
        || !Number.isInteger(record.accountRegistryRevision) || record.accountRegistryRevision < 1
        || !Number.isInteger(record.organizationRecordVersion) || record.organizationRecordVersion < 1
        || !Number.isInteger(record.organizationRegistryRevision) || record.organizationRegistryRevision < 1) {
      throw new Error("fleet_witness_record_invalid");
    }
    const administratorName = normalizeIdentity(record.administratorName);
    const observedEmail = normalizeIdentity(record.observedEmail);
    if (administratorName !== observedEmail) {
      throw new Error("registered_observed_identity_mismatch");
    }
    return {
      accountId: record.accountId,
      organizationId: record.organizationId,
      administratorName,
      observedEmail,
      providerOrganization: record.providerOrganization?.normalize("NFKC").trim() ?? null,
      collectionRunId: record.collectionRunId,
      currentHistoryMatched: record.currentHistoryMatched,
      freshAfterRestart: record.freshAfterRestart,
      providerKey: record.providerKey,
      lifecycle: record.lifecycle,
      monitoringPreference: record.monitoringPreference,
      effectiveMonitoringEnabled: record.effectiveMonitoringEnabled,
      effectiveMonitoringReason: record.effectiveMonitoringReason,
      identityState: record.identityState,
      accountRecordVersion: record.accountRecordVersion,
      accountRegistryRevision: record.accountRegistryRevision,
      organizationRecordVersion: record.organizationRecordVersion,
      organizationRegistryRevision: record.organizationRegistryRevision,
    };
  });
  if (new Set(normalized.map((record) => record.accountId)).size !== 6
      || new Set(normalized.map((record) => record.organizationId)).size !== 2) {
    throw new Error("owner_outcomes_membership_invalid");
  }
  const identities = normalized.map((record) => record.observedEmail);
  if (new Set(identities).size !== 6) {
    throw new Error("duplicate_reported_provider_identity");
  }
  const ordered = [...normalized].sort((left, right) => left.accountId.localeCompare(right.accountId));
  const currentHistoryCount = normalized.filter((record) => record.currentHistoryMatched).length;
  const freshAfterRestartCount = normalized.filter((record) => record.freshAfterRestart).length;
  if (event === "m4_fleet_witness"
      && (currentHistoryCount !== 6 || freshAfterRestartCount !== 6)) {
    throw new Error("fresh_post_restart_fleet_collection_required");
  }
  return {
    event,
    fleet_metadata_digest: sha256(ordered.map((record) => [
      record.accountId,
      record.organizationId,
      record.administratorName,
      record.providerKey,
      record.lifecycle,
      record.monitoringPreference,
      record.effectiveMonitoringEnabled,
      record.effectiveMonitoringReason,
      record.identityState,
      record.accountRecordVersion,
      record.accountRegistryRevision,
      record.organizationRecordVersion,
      record.organizationRegistryRevision,
    ])),
    identity_set_digest: sha256(ordered.map((record) => [
      record.observedEmail,
      record.providerOrganization,
    ])),
    collection_run_set_digest: sha256(ordered.map((record) => record.collectionRunId)),
    account_count: 6,
    organization_count: 2,
    distinct_identity_count: 6,
    current_history_count: currentHistoryCount,
    fresh_after_restart_count: freshAfterRestartCount,
  };
}
