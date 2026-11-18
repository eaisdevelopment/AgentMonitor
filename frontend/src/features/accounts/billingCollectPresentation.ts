import type { BillingCollectionEligibilityWireV2, BillingReportContextV2, BudgetRunStatusV2 } from "../../shared/api/client";

export type BillingCollectIntent = Readonly<{
  accountId: string; resourceId: string; accountVersion: number; connectionVersion: number;
  scopeGeneration: number; bindingGeneration: number; idempotencyKey: string;
  reportContext: BillingReportContextV2; runId: string | null; deadlineAt: string | null; handled: boolean;
  retryRequiresEligibility: boolean;
}>;

/** Collection admits only exact completed UTC day windows, never a report-derived range. */
export function collectionContext(start: string, end: string, sourceCategory = "cost", grouping: NonNullable<BillingReportContextV2["grouping"]> = []): BillingReportContextV2 {
  if (!/^[a-z][a-z0-9_]{0,63}$/.test(sourceCategory) || !Array.isArray(grouping) || grouping.length > 1 || grouping.some(value => !["workspace", "project", "api_key_id", "model", "token_category"].includes(value))) throw new Error("billing_collect_context_invalid");
  for (const value of [start, end]) {
    if (!/^\d{4}-\d{2}-\d{2}T00:00:00(?:\.0{1,6})?Z$/.test(value) ||
        !Number.isFinite(Date.parse(value)) || new Date(value).toISOString().slice(0, 10) !== value.slice(0, 10)) throw new Error("billing_collect_context_invalid");
  }
  const days = (Date.parse(end) - Date.parse(start)) / 86400000;
  if (days !== 7 && days !== 30) throw new Error("billing_collect_context_invalid");
  return { source_category: sourceCategory, range_key: days === 7 ? "7d" : "30d", interval_start: start, interval_end: end, grouping };
}

export function sameCollectionContext(left: BillingReportContextV2, right: BillingReportContextV2 | null | undefined): boolean {
  if (!right) return false;
  try {
    const actual = collectionContext(right.interval_start, right.interval_end, right.source_category, right.grouping ?? []);
    return right.range_key === actual.range_key && left.range_key === right.range_key &&
      left.source_category === right.source_category && JSON.stringify(left.grouping ?? []) === JSON.stringify(right.grouping ?? []) &&
      Date.parse(left.interval_start) === Date.parse(right.interval_start) && Date.parse(left.interval_end) === Date.parse(right.interval_end);
  } catch { return false; }
}

export function matchesCollectionEligibility(intent: BillingCollectIntent, value: Pick<BillingCollectionEligibilityWireV2,
  "account_id" | "resource_id" | "account_record_version" | "connection_record_version" | "scope_generation" | "binding_generation" | "report_context">): boolean {
  return intent.accountId === value.account_id && intent.resourceId === value.resource_id &&
    intent.accountVersion === value.account_record_version && intent.connectionVersion === value.connection_record_version &&
    intent.scopeGeneration === value.scope_generation && intent.bindingGeneration === value.binding_generation &&
    sameCollectionContext(intent.reportContext, value.report_context);
}

export function matchesCollectionRun(intent: BillingCollectIntent, run: Pick<BudgetRunStatusV2, "account_id" | "resource_id" | "run_id" | "report_context">): boolean {
  return intent.runId !== null && intent.runId === run.run_id && intent.accountId === run.account_id &&
    intent.resourceId === run.resource_id && sameCollectionContext(intent.reportContext, run.report_context);
}

export function collectionReadRequired(intent: BillingCollectIntent, run: BudgetRunStatusV2, selected: BillingReportContextV2): boolean {
  return !intent.handled && sameCollectionContext(selected, intent.reportContext) && matchesCollectionRun(intent, run) && (run.state === "succeeded" || run.state === "partial");
}

export function collectionRetryAllowed(intent: BillingCollectIntent, eligibility: BillingCollectionEligibilityWireV2): boolean {
  return !intent.handled && intent.runId === null && matchesCollectionEligibility(intent, eligibility) &&
    (!intent.retryRequiresEligibility || eligibility.can_collect);
}

/** Session storage contains safe command identity only; restored commands are never auto-posted. */
export function restoreCollectionIntent(raw: string | null, accountId: string, resourceId: string): BillingCollectIntent | null {
  if (!raw || raw.length > 4096) return null;
  try {
    const value: unknown = JSON.parse(raw);
    if (value === null || typeof value !== "object" || Array.isArray(value)) return null;
    const data = value as Record<string, unknown>;
    const keys = ["accountId", "resourceId", "accountVersion", "connectionVersion", "scopeGeneration", "bindingGeneration", "idempotencyKey", "reportContext", "runId", "deadlineAt", "handled", "retryRequiresEligibility"];
    if (Object.keys(data).length !== keys.length || Object.keys(data).some(key => !keys.includes(key))) return null;
    const safeId = /^[A-Za-z0-9._:-]{1,256}$/;
    if (data.accountId !== accountId || data.resourceId !== resourceId || !safeId.test(accountId) || !safeId.test(resourceId)) return null;
    if (![data.accountVersion, data.connectionVersion, data.scopeGeneration, data.bindingGeneration].every(value => typeof value === "number" && Number.isSafeInteger(value) && value > 0)) return null;
    if (typeof data.idempotencyKey !== "string" || !/^[a-f0-9]{32}$/.test(data.idempotencyKey) || typeof data.handled !== "boolean" || typeof data.retryRequiresEligibility !== "boolean") return null;
    if (data.runId === null ? data.deadlineAt !== null || data.handled : typeof data.runId !== "string" || !safeId.test(data.runId) || typeof data.deadlineAt !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$/.test(data.deadlineAt) || !Number.isFinite(Date.parse(data.deadlineAt))) return null;
    if (data.reportContext === null || typeof data.reportContext !== "object" || Array.isArray(data.reportContext) || Object.keys(data.reportContext).some(key => !["source_category", "range_key", "interval_start", "interval_end", "grouping"].includes(key))) return null;
    const reportContext = data.reportContext as BillingReportContextV2;
    if (!Array.isArray(reportContext.grouping) || !sameCollectionContext(reportContext, reportContext)) return null;
    return data as BillingCollectIntent;
  } catch { return null; }
}

export function collectionReason(code: string): string {
  const reasons: Readonly<Record<string, string>> = {
    openai_report_request_rejected: "OpenAI rejected this report request. Try another report or grouping; this selection has no new reading.",
    openai_cost_data_invalid: "OpenAI returned a report that could not be read. Previous readings retain their original times.",
    billing_collect_ready: "Ready to collect this interval. API monitoring will not change.",
    billing_collect_credential_required: "Store a billing credential in Manage connection, then refresh collection status.",
    billing_collect_context_unsupported: "This source does not admit the selected interval. Choose a supported completed window.",
    billing_check_provider_unsupported: "Manual billing collection is unavailable for this provider.",
    billing_check_target_unavailable: "This account or billing connection is unavailable. Review Manage connection.",
    billing_check_authority_unavailable: "Billing access is unavailable. Review the credential in Manage connection.",
    billing_check_rate_limited: "The provider collection cooldown is active. Refresh collection status after the time below.",
    billing_check_service_unavailable: "The billing collector is unavailable. Refresh collection status when the service is available.",
    billing_check_target_changed: "The connection changed. Refresh collection status before collecting.",
    billing_check_version_conflict: "The connection changed. Refresh collection status before collecting.",
  };
  return reasons[code] ?? "Collection is unavailable. Refresh collection status or review Manage connection.";
}


export type BillingReportSelection = Readonly<{ source_category: string; grouping: readonly string[] }>;

export function billingContextForView(start: string, end: string, pinnedSelected: boolean, pinned: BillingReportSelection | null, selected: BillingReportSelection | null): BillingReportContextV2 | null {
  if (pinnedSelected && pinned === null) return null;
  const view = pinnedSelected ? pinned : selected;
  return collectionContext(start, end, view?.source_category ?? "cost", (view?.grouping ?? []) as NonNullable<BillingReportContextV2["grouping"]>);
}
