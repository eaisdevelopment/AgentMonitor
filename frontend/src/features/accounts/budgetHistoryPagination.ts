/** Immutable history pagination decisions; no reads or financial calculations. */
export type HistoryContext = Readonly<{
  accountId: string; resourceId: string; reportId: string;
  periodStart: string; periodEnd: string; asOf: string;
}>;
type ReportIdentity = Readonly<{
  account_id: string; resource_id: string; report_id: string;
  requested_period: Readonly<{ start: string; end: string }>;
}>;
type HistoryItem = Readonly<{
  kind: "cost" | "usage";
  cost: Readonly<{ bucket_key: string }> | null;
  usage: Readonly<{ bucket_key: string }> | null;
}>;
export type HistoryProgress<T extends HistoryItem> = Readonly<{
  context: string; items: readonly T[]; nextCursor: string | null; cursors: readonly string[];
}>;

function instant(value: string): string {
  const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?Z$/.exec(value);
  if (match === null) throw new Error("history_time_invalid");
  return `${match[1]}.${(match[2] ?? "").padEnd(6, "0")}Z`;
}

export function historyContextKey(context: HistoryContext): string {
  return JSON.stringify([context.accountId, context.resourceId, context.reportId,
    instant(context.periodStart), instant(context.periodEnd), instant(context.asOf)]);
}

export function historyPageMatches(context: HistoryContext, report: ReportIdentity, asOf: string): boolean {
  try {
    return historyContextKey(context) === historyContextKey({ accountId: report.account_id,
      resourceId: report.resource_id, reportId: report.report_id,
      periodStart: report.requested_period.start, periodEnd: report.requested_period.end, asOf });
  } catch { return false; }
}

function identity(item: HistoryItem): string {
  const bucket = item.kind === "cost" && item.usage === null ? item.cost
    : item.kind === "usage" && item.cost === null ? item.usage : null;
  if (bucket === null || typeof bucket.bucket_key !== "string" || bucket.bucket_key.length === 0) throw new Error("history_item_invalid");
  return `${item.kind}:${bucket.bucket_key}`;
}

export function appendHistoryItems<T extends HistoryItem>(
  previous: HistoryProgress<T> | null, context: string, items: readonly T[],
  cursor: string | null, nextCursor: string | null, hasMore: boolean,
): HistoryProgress<T> {
  if (hasMore ? items.length === 0 || typeof nextCursor !== "string" || nextCursor.length === 0 : nextCursor !== null) throw new Error("history_page_invalid");
  if (cursor !== null && (previous === null || previous.context !== context)) throw new Error("history_context_changed");
  if (cursor !== null && previous?.nextCursor !== cursor) throw new Error("history_cursor_mismatch");
  const retained = cursor === null ? [] : previous?.items ?? [];
  const cursors = cursor === null ? [] : [...(previous?.cursors ?? []), cursor];
  if (nextCursor !== null && cursors.includes(nextCursor)) throw new Error("history_cursor_repeated");
  const seen = new Set(retained.map(identity));
  for (const item of items) {
    const key = identity(item);
    if (seen.has(key)) throw new Error("history_item_duplicate");
    seen.add(key);
  }
  return { context, items: [...retained, ...items], nextCursor, cursors };
}
