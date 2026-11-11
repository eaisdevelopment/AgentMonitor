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
