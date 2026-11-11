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
