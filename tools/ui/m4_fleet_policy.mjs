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
const opaque = (value) => typeof value === "string"
  && /^[A-Za-z0-9_-]{1,64}$/.test(value);
const timestamp = (value) => typeof value === "string"
  && Number.isFinite(Date.parse(value));
const quotaProvenanceV1 = Object.freeze({
  source_id: "claude.usage.ax-screen-reader.v1",
  adapter_id: "agentmonitor.claude",
  adapter_version: "1.0.3",
  parser_version: "1.0.3",
  provider_version: "2.1.289",
  decision_reference: "A01-M03-CLAUDE-2-1-289-001",
});
const exactQuotaProvenanceV1 = (provenance) => Object.entries(quotaProvenanceV1)
  .every(([field, expected]) => provenance?.[field] === expected);

export function isExactRenderedQuotaProvenanceV1(fields) {
  return fields?.Source === quotaProvenanceV1.source_id
    && fields?.Adapter === `${quotaProvenanceV1.adapter_id} · ${quotaProvenanceV1.adapter_version}`
    && fields?.["Provider version"] === quotaProvenanceV1.provider_version;
}

export function isFreshCollectionLineageV1(candidate, serviceStartedAt) {
  const lowerBound = Date.parse(serviceStartedAt);
  const requestedAt = Date.parse(candidate?.run?.requested_at);
  const completedAt = Date.parse(candidate?.run?.completed_at);
  const observationIds = candidate?.run?.observation_ids;
  const windows = candidate?.windows;
  const history = candidate?.history;
  const windowKeys = new Set(Array.isArray(windows)
    ? windows.map(window => window?.window_key)
    : []);
  const allowedPartialWindowKeys = new Set([
    "current_session", "current_week_all_models", "current_week_sonnet_only",
  ]);
  const currentObservationIds = new Set(Array.isArray(windows)
    ? windows.map(window => window?.current_observation_id)
    : []);
  const currentHistoryPoints = Array.isArray(history?.items)
    ? history.items.filter(point => point?.subject?.account_id === candidate?.accountId
      && point.collection_run_id === candidate?.run?.run_id
      && candidate?.run?.observation_ids?.includes(point.observation_id)
      && currentObservationIds.has(point.observation_id))
    : [];
  const historyMatches = (window) => currentHistoryPoints.filter(point =>
    point.observation_id === window?.current_observation_id
    && point.window_key === window?.window_key);
  const historyLineageComplete = Array.isArray(windows) && windows.length > 0
    && currentObservationIds.size === windows.length
    && currentHistoryPoints.length === windows.length
    && windows.every(window => {
      const matches = historyMatches(window);
      return matches.length === 1 && exactQuotaProvenanceV1(matches[0].provenance);
    });
  const allowedWindowSet = Array.isArray(windows) && windows.length > 0
    && windowKeys.has("current_session")
    && windowKeys.has("current_week_all_models")
    && windows.length === windowKeys.size
    && currentObservationIds.size === windows.length
    && [...windowKeys].every(key => allowedPartialWindowKeys.has(key));
  const completeHistoryComplete = allowedWindowSet && historyLineageComplete
    && currentHistoryPoints.every(point => point.completeness === "complete");
  const partialHistoryComplete = allowedWindowSet && historyLineageComplete
    && currentHistoryPoints.every(point => point.completeness === "partial");
  const exactCollectionVersion = candidate?.run?.adapter_version === quotaProvenanceV1.adapter_version
    && candidate?.run?.provider_version === quotaProvenanceV1.provider_version;
  const acceptedTerminalState = exactCollectionVersion && allowedWindowSet
    && ((candidate?.run?.state === "succeeded"
      && candidate.run.outcome_code === "succeeded"
      && candidate.run.error_code === null
      && completeHistoryComplete)
    || (candidate?.run?.state === "partial"
      && candidate.run.outcome_code === "partial"
      && candidate.run.error_code === null
      && partialHistoryComplete));
  if (!Number.isFinite(lowerBound) || !Number.isFinite(requestedAt)
      || !Number.isFinite(completedAt) || requestedAt < lowerBound
      || completedAt < requestedAt || candidate?.run?.run_id !== candidate?.identity?.collection_run_id
      || candidate?.run?.account_id !== candidate?.accountId
      || candidate?.identity?.account_id !== candidate?.accountId
      || !acceptedTerminalState
      || candidate?.run?.source_id !== "claude.usage.ax-screen-reader.v1"
      || !Array.isArray(observationIds) || observationIds.length === 0
      || !Array.isArray(windows) || windows.length === 0
      || !windows.every(window => window?.subject?.account_id === candidate.accountId
        && window.freshness === "fresh"
        && window.collection_run_id === candidate.run.run_id
        && text(window.current_observation_id, 128)
        && observationIds.includes(window.current_observation_id)
        && exactQuotaProvenanceV1(window.provenance))
      || history?.availability?.state !== "available" || !Array.isArray(history.items)
      || !historyLineageComplete) {
    return false;
  }
  return true;
}

export function buildFleetRuntimeWitnessV1(locations, selectedAccountIds) {
  if (!Array.isArray(selectedAccountIds) || selectedAccountIds.length !== 6
      || new Set(selectedAccountIds).size !== 6
      || !selectedAccountIds.every(opaque)) {
    throw new Error("six_owner_outcomes_required");
  }
  const selected = new Set(selectedAccountIds);
  const items = locations?.availability?.state === "available"
      && [true, false].includes(locations?.truncated)
      && Array.isArray(locations?.items)
    ? locations.items
    : [];
  const linked = items.filter((item) => {
    const association = item?.account_association;
    const observedAt = Date.parse(item?.observed_at);
    const confirmedAt = Date.parse(association?.confirmed_at);
    return item?.provider_key === "claude"
      && item.state === "running"
      && item.account_correlation === "unresolved"
      && Number.isInteger(item.pid) && item.pid > 0
      && Number.isInteger(item.start_time_ticks) && item.start_time_ticks > 0
      && text(item.platform_scope_id, 128)
      && /^[0-9a-f]{64}$/.test(item.association_key ?? "")
      && Number.isInteger(item.association_record_version)
      && item.association_record_version >= 1
      && association?.state === "owner_confirmed"
      && opaque(association.account_id)
      && selected.has(association.account_id)
      && opaque(association.principal_id)
      && Number.isInteger(association.record_version)
      && association.record_version === item.association_record_version
      && timestamp(item.observed_at)
      && timestamp(association.confirmed_at)
      && confirmedAt <= observedAt;
  });
  if (linked.length === 0) {
    throw new Error("owner_confirmed_selected_live_process_required");
  }
  return {
    owner_confirmed_live_process_count: linked.length,
    owner_confirmed_live_account_count: new Set(
      linked.map(item => item.account_association.account_id),
    ).size,
  };
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
