import type { CloudUsageEligibilityWireV1, CloudUsageContextV1, CloudUsageRunStatusV1 } from "../../shared/api/client";

export type CloudUsageIntent = Readonly<{
  accountId: string; resourceId: string; accountVersion: number; targetVersion: number;
  bindingGeneration: number; idempotencyKey: string;
  reportContext: CloudUsageContextV1; runId: string | null; deadlineAt: string | null; handled: boolean;
  retryRequiresEligibility: boolean;
}>;

/** Collection admits only exact completed UTC day windows, never a report-derived range. */
export function cloudUsageContext(start: string, end: string, scope: "self" | "team" = "self"): CloudUsageContextV1 {
  for (const value of [start, end]) {
    if (!/^\d{4}-\d{2}-\d{2}T00:00:00(?:\.0{1,6})?Z$/.test(value) ||
        !Number.isFinite(Date.parse(value)) || new Date(value).toISOString().slice(0, 10) !== value.slice(0, 10)) throw new Error("cloud_usage_context_invalid");
  }
  const days = (Date.parse(end) - Date.parse(start)) / 86400000;
  if (days !== 7 && days !== 30) throw new Error("cloud_usage_context_invalid");
  return { scope, range_key: days === 7 ? "7d" : "30d", interval_start: start, interval_end: end };
}

export function sameCloudUsageContext(left: CloudUsageContextV1, right: CloudUsageContextV1 | null | undefined): boolean {
  if (!right) return false;
  try {
    const actual = cloudUsageContext(right.interval_start, right.interval_end);
    return (right.scope === "self" || right.scope === "team") &&
      right.range_key === actual.range_key && left.range_key === right.range_key &&
      left.scope === right.scope &&
      Date.parse(left.interval_start) === Date.parse(right.interval_start) && Date.parse(left.interval_end) === Date.parse(right.interval_end);
  } catch { return false; }
}

export function matchesCloudUsageEligibility(intent: CloudUsageIntent, value: Pick<CloudUsageEligibilityWireV1,
  "account_id" | "resource_id" | "account_record_version" | "target_record_version" | "binding_generation" | "report_context">): boolean {
  return intent.accountId === value.account_id && intent.resourceId === value.resource_id &&
    intent.accountVersion === value.account_record_version && intent.targetVersion === value.target_record_version &&
    intent.bindingGeneration === value.binding_generation &&
    sameCloudUsageContext(intent.reportContext, value.report_context);
}

export function matchesCloudUsageRun(intent: CloudUsageIntent, run: Pick<CloudUsageRunStatusV1, "account_id" | "resource_id" | "run_id" | "report_context">): boolean {
  return intent.runId !== null && intent.runId === run.run_id && intent.accountId === run.account_id &&
    intent.resourceId === run.resource_id && sameCloudUsageContext(intent.reportContext, run.report_context);
}

export function cloudUsageReadRequired(intent: CloudUsageIntent, run: CloudUsageRunStatusV1, selected: CloudUsageContextV1): boolean {
  return !intent.handled && sameCloudUsageContext(selected, intent.reportContext) && matchesCloudUsageRun(intent, run) && (run.state === "succeeded" || run.state === "partial");
}

export function cloudUsageRetryAllowed(intent: CloudUsageIntent, eligibility: CloudUsageEligibilityWireV1): boolean {
  return !intent.handled && intent.runId === null && matchesCloudUsageEligibility(intent, eligibility) &&
    (!intent.retryRequiresEligibility || eligibility.can_collect);
}

/** Session storage contains safe command identity only; restored commands are never auto-posted. */
export function restoreCloudUsageIntent(raw: string | null, accountId: string, resourceId: string): CloudUsageIntent | null {
  if (!raw || raw.length > 4096) return null;
  try {
    const value: unknown = JSON.parse(raw);
    if (value === null || typeof value !== "object" || Array.isArray(value)) return null;
    const data = value as Record<string, unknown>;
    const keys = ["accountId", "resourceId", "accountVersion", "targetVersion", "bindingGeneration", "idempotencyKey", "reportContext", "runId", "deadlineAt", "handled", "retryRequiresEligibility"];
    if (Object.keys(data).length !== keys.length || Object.keys(data).some(key => !keys.includes(key))) return null;
    const safeId = /^[A-Za-z0-9._:-]{1,256}$/;
    if (data.accountId !== accountId || data.resourceId !== resourceId || !safeId.test(accountId) || !safeId.test(resourceId)) return null;
    if (![data.accountVersion, data.targetVersion, data.bindingGeneration].every(value => typeof value === "number" && Number.isSafeInteger(value) && value > 0)) return null;
    if (typeof data.idempotencyKey !== "string" || !/^[a-f0-9]{32}$/.test(data.idempotencyKey) || typeof data.handled !== "boolean" || typeof data.retryRequiresEligibility !== "boolean") return null;
    if (data.runId === null ? data.deadlineAt !== null || data.handled : typeof data.runId !== "string" || !safeId.test(data.runId) || typeof data.deadlineAt !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$/.test(data.deadlineAt) || !Number.isFinite(Date.parse(data.deadlineAt))) return null;
    if (data.runId !== null && data.retryRequiresEligibility) return null;
    if (data.reportContext === null || typeof data.reportContext !== "object" || Array.isArray(data.reportContext) || Object.keys(data.reportContext).some(key => !["scope", "range_key", "interval_start", "interval_end"].includes(key))) return null;
    const reportContext = data.reportContext as CloudUsageContextV1;
    if (!sameCloudUsageContext(reportContext, reportContext)) return null;
    return data as CloudUsageIntent;
  } catch { return null; }
}

/** Only the published selected report category establishes a team action. */
export function cloudUsageScope(sourceCategory: string | undefined): "self" | "team" {
  return sourceCategory === "team_requests_and_cost" ? "team" : "self";
}

/** These explicit refusals cannot retarget an old intent; unknown outcomes retain it. */
export function cloudUsageRequestRefused(code: string, confirmedUnadmitted = true): boolean {
  return confirmedUnadmitted && ["cloud_usage_interval_unavailable", "cloud_usage_target_changed", "cloud_usage_version_conflict"].includes(code);
}

export function cloudUsageReason(code: string): string {
  const reasons: Readonly<Record<string, string>> = {
    cloud_usage_ready: "Ready to collect this usage interval. Balance and monitoring settings will not change.",
    cloud_usage_monitoring_disabled: "Enable monitoring in the existing cloud connection controls, then refresh usage status.",
    cloud_usage_credential_required: "Complete local credential setup in the existing cloud connection controls, then refresh usage status.",
    cloud_usage_authority_unavailable: "Cloud access is unavailable for the current credential. Review the existing cloud connection controls.",
    cloud_usage_target_unavailable: "This cloud resource is unavailable. Review the existing cloud connection controls.",
    cloud_usage_interval_unavailable: "This source collects only its current native window. Choose Latest completed window; older stored reports remain readable.",
    cloud_usage_request_unresolved: "An earlier provider request remains unresolved. Refresh usage status before another collection.",
    cloud_usage_rate_limited: "Usage and balance share a provider cooldown. Refresh usage status after the server time below.",
    cloud_usage_service_unavailable: "The usage collector is unavailable. Refresh usage status when the service is available.",
    cloud_usage_target_changed: "The cloud target or credential changed. Refresh usage status before collecting.",
    cloud_usage_version_conflict: "The account or cloud target changed. Refresh view before collecting.",
  };
  return reasons[code] ?? "Usage collection is unavailable. Refresh usage status or review the existing cloud connection controls.";
}
