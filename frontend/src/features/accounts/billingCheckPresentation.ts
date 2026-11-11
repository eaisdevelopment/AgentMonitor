import type { AccountBillingConnectionsV1, BillingConnectionViewV1, BudgetRunStatusV1, BillingMonitoringStatusV1 } from "../../shared/api/client";

export type BillingCheckIntent = Readonly<{
  accountId: string;
  resourceId: string;
  accountVersion: number;
  connectionVersion: number;
  scopeGeneration: number;
  credentialGeneration: number;
  idempotencyKey: string;
  runId: string | null;
  deadlineAt: string | null;
}>;

export type BillingMonitoringIntent = Readonly<{
  accountId: string;
  resourceId: string;
  accountVersion: number;
  connectionVersion: number;
  scopeGeneration: number;
  bindingGeneration: number | null;
  verifiedRunId: string | null;
  preference: "enabled" | "disabled";
  idempotencyKey: string;
}>;

export function buildMonitoringIntent(status: BillingMonitoringStatusV1, preference: "enabled" | "disabled", idempotencyKey: string): BillingMonitoringIntent {
  return { accountId: status.account_id, resourceId: status.resource_id,
    accountVersion: status.account_record_version, connectionVersion: status.connection_record_version,
    scopeGeneration: status.scope_generation, bindingGeneration: status.binding_generation,
    verifiedRunId: preference === "enabled" ? status.verified_run_id : null, preference, idempotencyKey };
}

export function monitoringStatusCurrent(status: BillingMonitoringStatusV1 | null, account: AccountBillingConnectionsV1, connection: BillingConnectionViewV1): boolean {
  return status !== null && status.account_id === account.account_id && status.account_id === connection.account_id &&
    status.resource_id === connection.resource_id && status.account_record_version === account.account_record_version &&
    status.connection_record_version === connection.record_version && status.scope_generation === connection.scope_generation &&
    (account.credential_status == null || status.binding_generation === account.credential_status.active_generation);
}

export function currentCheckEvidence(
  evidence: Pick<BillingCheckIntent, "accountId" | "resourceId" | "scopeGeneration" | "credentialGeneration"> | null,
  status: Pick<AccountBillingConnectionsV1, "account_id" | "account_lifecycle" | "credential_status">,
  connection: Pick<BillingConnectionViewV1, "account_id" | "resource_id" | "scope_generation" | "lifecycle">,
): boolean {
  return evidence !== null && evidence.accountId === status.account_id && evidence.accountId === connection.account_id &&
    evidence.resourceId === connection.resource_id && evidence.scopeGeneration === connection.scope_generation &&
    status.credential_status?.state === "stored" && evidence.credentialGeneration === status.credential_status.active_generation &&
    ["pending", "active"].includes(status.account_lifecycle) && ["pending", "active"].includes(connection.lifecycle);
}

export function monitoringReason(code: string): string {
  const reasons: Readonly<Record<string, string>> = {
    billing_monitoring_credential_required: "Store a credential locally, then Check connection before enabling API monitoring.",
    billing_monitoring_verification_required: "Complete Check connection for the current credential and billing scope before enabling API monitoring.",
    billing_monitoring_runtime_unavailable: "The billing collector is unavailable. Refresh monitoring status to check again.",
    billing_monitoring_verified: "A successful Check confirms access for the current credential and billing scope.",
    billing_monitoring_account_unavailable: "This account or billing connection is unavailable for monitoring.",
    billing_monitoring_target_unavailable: "This billing connection is no longer available. Refresh its status.",
    billing_monitoring_version_conflict: "The connection changed. Review refreshed status before changing monitoring.",
    registry_version_conflict: "The account changed. Review refreshed status before changing monitoring.",
    billing_monitoring_target_changed: "The credential or billing scope changed. Review refreshed status before changing monitoring.",
    registry_replay_stale: "Monitoring changed after this request. Review the current server setting.",
  };
  return reasons[code] ?? "API monitoring status is unavailable. Refresh to try again.";
}

export function restoreMonitoringIntent(text: string | null, accountId: string, resourceId: string): BillingMonitoringIntent | null {
  if (text === null || text.length > 4096) return null;
  try {
    const item: unknown = JSON.parse(text);
    if (typeof item !== "object" || item === null || Array.isArray(item)) return null;
    const value = item as Record<string, unknown>;
    const keys = ["accountId", "resourceId", "accountVersion", "connectionVersion", "scopeGeneration", "bindingGeneration", "verifiedRunId", "preference", "idempotencyKey"];
    const opaque = (field: unknown) => typeof field === "string" && /^[A-Za-z0-9._:-]{1,256}$/.test(field);
    const positive = (field: unknown) => typeof field === "number" && Number.isSafeInteger(field) && field > 0;
    if (Object.keys(value).length !== keys.length || Object.keys(value).some((key) => !keys.includes(key)) || value.accountId !== accountId || value.resourceId !== resourceId || !opaque(value.accountId) || !opaque(value.resourceId)) return null;
    if (![value.accountVersion, value.connectionVersion, value.scopeGeneration].every(positive) || value.bindingGeneration !== null && !positive(value.bindingGeneration)) return null;
    if (value.verifiedRunId !== null && !opaque(value.verifiedRunId)) return null;
    if (value.preference !== "enabled" && value.preference !== "disabled") return null;
    if (value.preference === "enabled" && (value.bindingGeneration === null || value.verifiedRunId === null)) return null;
    if (value.preference === "disabled" && value.verifiedRunId !== null) return null;
    if (typeof value.idempotencyKey !== "string" || !/^[a-f0-9]{32}$/.test(value.idempotencyKey)) return null;
    return value as BillingMonitoringIntent;
  } catch { return null; }
}

export function checkEligibility(
  status: Pick<AccountBillingConnectionsV1, "account_lifecycle" | "credential_status">,
  connection: Pick<BillingConnectionViewV1, "provider_key" | "lifecycle">,
): Readonly<{ allowed: boolean; reason: string }> {
  if (connection.provider_key !== "claude") return { allowed: false, reason: "Connection checking is not yet available for this provider in this build." };
  if (!["pending", "active"].includes(status.account_lifecycle) || !["pending", "active"].includes(connection.lifecycle)) {
    return { allowed: false, reason: "This connection is not available for checking." };
  }
  const credential = status.credential_status;
  if (credential == null) return { allowed: false, reason: "Refresh credential status before checking connection." };
  if (credential.state !== "stored" || credential.active_generation === null) return { allowed: false, reason: "Store a credential locally before checking connection." };
  return { allowed: true, reason: "Checks the last 7 completed UTC days. A queued check is not verified access." };
}

export function pendingRun(state: string): boolean {
  return ["requested", "queued", "running", "committing"].includes(state);
}

export function matchesCheckRun(
  intent: Pick<BillingCheckIntent, "accountId" | "resourceId" | "runId">,
  run: Pick<BudgetRunStatusV1, "account_id" | "resource_id" | "run_id">,
): boolean {
  return run.account_id === intent.accountId && run.resource_id === intent.resourceId && run.run_id === intent.runId;
}

export function advanceFinancialRead<T extends Readonly<{ period_start: string; period_end: string; as_of: string }>>(query: T, now: Date) {
  return { ...query, as_of: now.toISOString() };
}

/** Allowlisted, nonsecret per-tab intent only; never restore arbitrary commands. */
export function restoreCheckIntent(text: string | null, accountId: string): BillingCheckIntent | null {
  if (text === null || text.length > 4096) return null;
  try {
    const item: unknown = JSON.parse(text);
    if (typeof item !== "object" || item === null || Array.isArray(item)) return null;
    const value = item as Record<string, unknown>;
    const keys = ["accountId", "resourceId", "accountVersion", "connectionVersion", "scopeGeneration", "credentialGeneration", "idempotencyKey", "runId", "deadlineAt"];
    const opaque = (field: unknown) => typeof field === "string" && /^[A-Za-z0-9._:-]{1,256}$/.test(field);
    if (Object.keys(value).length !== keys.length || Object.keys(value).some((key) => !keys.includes(key)) || value.accountId !== accountId || !opaque(value.accountId) || !opaque(value.resourceId)) return null;
    if ([value.accountVersion, value.connectionVersion, value.scopeGeneration, value.credentialGeneration].some((field) => typeof field !== "number" || !Number.isSafeInteger(field) || field < 1)) return null;
    if (typeof value.idempotencyKey !== "string" || !/^[a-f0-9]{32}$/.test(value.idempotencyKey)) return null;
    if (value.runId !== null && !opaque(value.runId)) return null;
    if (value.deadlineAt !== null && (typeof value.deadlineAt !== "string" || !Number.isFinite(Date.parse(value.deadlineAt)))) return null;
    if ((value.runId === null) !== (value.deadlineAt === null)) return null;
    return value as BillingCheckIntent;
  } catch { return null; }
}
