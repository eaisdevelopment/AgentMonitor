import type { AccountViewV1 } from "../../shared/api/client";

export type FinancialReadContext = Readonly<{
  account: Pick<AccountViewV1, "account_id" | "provider_key" | "record_version">;
  periodStart: string;
  periodEnd: string;
  readRevision: number;
}>;

/** Refresh triggers do not change financial identity; configuration generations do. */
export function canRetainFinancialReading(previous: FinancialReadContext, next: FinancialReadContext): boolean {
  return previous.account.account_id === next.account.account_id &&
    previous.account.provider_key === next.account.provider_key &&
    previous.account.record_version === next.account.record_version &&
    Date.parse(previous.periodStart) === Date.parse(next.periodStart) &&
    Date.parse(previous.periodEnd) === Date.parse(next.periodEnd);
}

type SelectedFinancialReport =
  | Readonly<{ kind: "none" | "invalid" }>
  | Readonly<{ kind: "period"; days: 7 | 30; query: { period_start: string; period_end: string; as_of: string } }>
  | Readonly<{ kind: "selected"; resourceId: string; reportId: string | null;
      days: 7 | 30; query: { period_start: string; period_end: string; as_of: string } }>;

/** Only nonsecret immutable selections are accepted; malformed links never select latest. */
export function selectedFinancialReport(search: string): SelectedFinancialReport {
  const params = new URLSearchParams(search);
  if (params.has("budget_selection")) return { kind: "invalid" };
  const keys = ["budget_resource", "budget_report", "budget_start", "budget_end", "budget_as_of"];
  if (!keys.some(key => params.has(key))) return { kind: "none" };
  if (keys.some(key => params.getAll(key).length > 1)) return { kind: "invalid" };
  const resourceId = params.get("budget_resource");
  const reportId = params.get("budget_report");
  const safeId = /^[A-Za-z0-9._:-]{1,256}$/;
  if ((resourceId !== null && !safeId.test(resourceId)) || (reportId !== null && (resourceId === null || !safeId.test(reportId)))) return { kind: "invalid" };
  const readTime = (key: string) => {
    const value = params.get(key);
    if (value === null || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$/.test(value)) return NaN;
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) && new Date(parsed).toISOString().slice(0, 19) === value.slice(0, 19) ? parsed : NaN;
  };
  const start = readTime("budget_start"), end = readTime("budget_end"), asOf = readTime("budget_as_of");
  const days = (end - start) / 86_400_000;
  if (![start, end, asOf].every(Number.isFinite) || (days !== 7 && days !== 30) ||
      !/T00:00:00(?:\.0{1,6})?Z$/.test(params.get("budget_start") ?? "") ||
      !/T00:00:00(?:\.0{1,6})?Z$/.test(params.get("budget_end") ?? "") ||
      start % 86_400_000 !== 0 || end % 86_400_000 !== 0 || end > asOf) return { kind: "invalid" };
  const query = { period_start: params.get("budget_start")!, period_end: params.get("budget_end")!, as_of: params.get("budget_as_of")! };
  return resourceId === null ? { kind: "period", days, query } : { kind: "selected", resourceId, reportId, days, query };
}
