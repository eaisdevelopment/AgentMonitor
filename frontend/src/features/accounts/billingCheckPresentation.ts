import type { AccountBillingConnectionsV1, BillingConnectionViewV1, BudgetRunStatusV1 } from "../../shared/api/client";

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
