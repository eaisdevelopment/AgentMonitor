/** An HTTP success can still carry an unusable financial query result. */
export function canReplaceFinancialOverview(state: string): boolean {
  return state === "available" || state === "partial";
}

/** Pending setup has an account destination but no financial resource selection. */
export function financialAccountSelectors(
  resourceId: string | null,
  reportId: string | undefined,
  period: Readonly<{ start: string; end: string }>,
  asOf: string,
): Readonly<Record<string, string>> {
  if (resourceId === null) return {};
  return {
    budget_resource: resourceId,
    ...(reportId === undefined ? {} : { budget_report: reportId }),
    budget_start: period.start,
    budget_end: period.end,
    budget_as_of: asOf,
  };
}

/** A shared pool's report belongs to its contributing access path. */
export function financialReportDestination(
  accountId: string,
  resourceId: string | null,
  context?: Readonly<{ report_id: string; report_account_id?: string | null; report_resource_id?: string | null }>,
): Readonly<{ accountId: string; resourceId: string | null; reportId: string | undefined }> | null {
  if (context === undefined) return { accountId, resourceId, reportId: undefined };
  const hasAccount = context.report_account_id != null;
  const hasResource = context.report_resource_id != null;
  if (hasAccount !== hasResource) return null;
  return {
    accountId: context.report_account_id ?? accountId,
    resourceId: context.report_resource_id ?? resourceId,
    reportId: context.report_id,
  };
}
