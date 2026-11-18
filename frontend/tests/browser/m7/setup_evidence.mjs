// Pure identity checks; no API, credential, filesystem or browser access.
export const setupInstant = value => typeof value === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)$/.test(value)
  ? value.replace("+00:00", "Z").replace(/(?:\.(\d{1,6}))?Z$/, (_, digits) => `.${(digits ?? "").padEnd(6, "0")}Z`) : null;
export function sameSetupAuthority(before, after, resourceId) {
  const previous = before.connections?.find(value => value.resource_id === resourceId);
  const current = after.connections?.find(value => value.resource_id === resourceId);
  return previous !== undefined && current !== undefined
    && ["account_id", "provider_key", "account_record_version", "account_lifecycle"].every(key => before[key] === after[key])
    && ["state", "active_generation", "pending_generation"].every(key => before.credential_status?.[key] === after.credential_status?.[key])
    && ["account_id", "resource_id", "provider_key", "record_version", "scope_generation", "scope_id", "scope_evidence", "lifecycle", "monitoring_preference"].every(key => previous[key] === current[key]);
}
export function currentSetupProof(status, connection, monitoring, run) {
  return ["pending", "active"].includes(status?.account_lifecycle)
    && status.credential_status?.state === "stored" && Number.isSafeInteger(status.credential_status.active_generation) && status.credential_status.active_generation > 0
    && connection.account_id === status.account_id && connection.lifecycle === "active" && connection.monitoring_preference === "enabled"
    && monitoring.account_id === status.account_id && monitoring.resource_id === connection.resource_id
    && monitoring.account_record_version === status.account_record_version && monitoring.connection_record_version === connection.record_version
    && monitoring.scope_generation === connection.scope_generation && monitoring.binding_generation === status.credential_status.active_generation
    && monitoring.lifecycle === "active" && monitoring.monitoring_preference === "enabled"
    && typeof monitoring.verified_run_id === "string" && monitoring.verified_run_id === run?.run_id
    && run.account_id === status.account_id && run.resource_id === connection.resource_id && run.state === "succeeded"
    && typeof run.report_id === "string" && run.report_id.length > 0 && run.error_code === null
    && setupInstant(run.completed_at) !== null && setupInstant(run.completed_at) === setupInstant(monitoring.verified_at);
}
