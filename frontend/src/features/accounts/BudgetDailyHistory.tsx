import { useEffect, useRef, useState } from "react";

import { budgets, type BudgetHistoryWireV1 } from "../../shared/api/client";
import { displayMoney, exactMoneyText, exactUsageText } from "./budgetPresentation";
import { appendHistoryItems, historyContextKey, historyPageMatches, type HistoryContext, type HistoryProgress } from "./budgetHistoryPagination";
import { BudgetHistoryChart } from "./BudgetHistoryChart";
import { BudgetObservedRate } from "./BudgetObservedRate";

const readable = (value: string) => value.replaceAll("_", " ");
const instant = (value: string) => new Date(value).toLocaleString(undefined, { timeZoneName: "short" });
const bounds = (start: string, end: string) => `${start.slice(0, 10)} to ${end.slice(0, 10)} UTC (end exclusive)`;
type Props = Readonly<{ context: HistoryContext; onExpired: () => void; showSummary?: boolean }>;
type Snapshot = Readonly<{ value: BudgetHistoryWireV1; progress: HistoryProgress<BudgetHistoryWireV1["items"][number]> }>;

function History({ context, onExpired, showSummary = false }: Props) {
  const contextKey = historyContextKey(context);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const snapshotRef = useRef(snapshot);
  snapshotRef.current = snapshot;
  const [request, setRequest] = useState<Readonly<{ cursor: string | null; attempt: number }>>({ cursor: null, attempt: 0 });
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const expired = useRef(onExpired);
  expired.current = onExpired;

  useEffect(() => {
    const controller = new AbortController();
    setBusy(true);
    setError(null);
    void (async () => {
      try {
        const result = await budgets.history(context.resourceId, { account_id: context.accountId,
          report_id: context.reportId, period_start: context.periodStart, period_end: context.periodEnd,
          as_of: context.asOf, limit: 50, ...(request.cursor === null ? {} : { cursor: request.cursor }) }, controller.signal);
        if (controller.signal.aborted) return;
        if (!result.ok) {
          if (result.problem.code === "dashboard_authentication_required") expired.current();
          else if (result.problem.status === 404 || result.problem.status === 410) setError("The selected history is unavailable or no longer retained. Refresh view to select current stored data; previously loaded rows retain their original report.");
          else setError("History could not be loaded. Previously loaded rows remain unchanged. Retry this page or Refresh view to select current stored data.");
          return;
        }
        const value = result.data;
        if (!["available", "partial"].includes(value.availability.state) || !historyPageMatches(context, value.report, value.as_of) || value.reported_spend.report_id !== context.reportId) throw new Error("history_response_mismatch");
        const previous = snapshotRef.current;
        const progress = appendHistoryItems(previous?.progress ?? null, contextKey, value.items, request.cursor, value.page.next_cursor, value.page.has_more);
        if (request.cursor !== null && previous !== null &&
            (JSON.stringify(previous.value.report) !== JSON.stringify(value.report) || JSON.stringify(previous.value.reported_spend) !== JSON.stringify(value.reported_spend))) throw new Error("history_report_changed");
        setSnapshot({ value, progress });
      } catch {
        if (!controller.signal.aborted) setError("History could not be loaded consistently. Previously loaded rows retain their original report and times. Retry this page or Refresh view to select current stored data.");
      } finally {
        if (!controller.signal.aborted) setBusy(false);
      }
    })();
    return () => controller.abort();
  }, [contextKey, request.cursor, request.attempt]);

  const value = snapshot?.value;
  const report = value?.report;
  const items = snapshot?.progress.items ?? [];
  const costs = items.flatMap((item) => item.kind === "cost" && item.cost !== null ? [item.cost] : []);
  const usage = items.flatMap((item) => item.kind === "usage" && item.usage !== null ? [item.usage] : []);
  return <div data-budget-history={context.reportId} aria-busy={busy}>
    {busy && <p role="status">Reading stored history…</p>}
    {error !== null && <p role="alert">{error}</p>}
    {showSummary && report !== undefined && value !== undefined && <>
      {report.currency === null && report.cost_bucket_count === 0 && report.usage_bucket_count > 0 ? <p>Provider did not report costs.</p> :
        <p><strong>Reported spend: </strong>{value.reported_spend.total === null ? readable(value.reported_spend.reason_code) :
          <span title={exactMoneyText(value.reported_spend.total)}>{displayMoney(value.reported_spend.total)}</span>}</p>}
      <p>Provider billing scope: {report.scope_id ?? "Not established"} · {readable(report.scope_evidence)} · Scope generation {report.scope_generation}</p>
      <p>{bounds(report.requested_period.start, report.requested_period.end)} · {readable(report.cost_basis)} · {readable(report.source_category)}</p>
      <p>Data through: {report.source_data_through === null ? "Not reported" : instant(report.source_data_through)} · Collected: {instant(report.collected_at)} · {report.completeness}</p>
    </>}
    <BudgetObservedRate context={context} onExpired={onExpired} />
    {value !== undefined && value.availability.state !== "available" && <p role="status">History {value.availability.state}: {readable(value.availability.reason_code)}.</p>}
    {snapshot !== null && items.length === 0 && <p>No reported usage in this interval.</p>}
    {items.length > 0 && <BudgetHistoryChart items={items} hasMore={snapshot?.progress.nextCursor != null} busy={busy} failed={error !== null} />}
    {costs.length > 0 && <div className="table-scroll" tabIndex={0} role="region" aria-label="Exact cost history">
      <table><caption>Cost history · source intervals, exact amounts</caption>
        <thead><tr><th scope="col">Period (UTC)</th><th scope="col">Amount</th><th scope="col">Kind</th></tr></thead>
        <tbody>{costs.map((row) => <tr key={row.bucket_key} data-bucket-key={row.bucket_key} data-bucket-kind="cost">
          <td>{bounds(row.period.start, row.period.end)}</td><td>{exactMoneyText(row.amount)}</td><td>{row.kind}</td>
        </tr>)}</tbody>
      </table>
    </div>}
    {usage.length > 0 && <div className="table-scroll" tabIndex={0} role="region" aria-label="Exact usage history">
      <table><caption>Usage history · source intervals, exact quantities</caption>
        <thead><tr><th scope="col">Period (UTC)</th><th scope="col">Usage</th></tr></thead>
        <tbody>{usage.map((row) => <tr key={row.bucket_key} data-bucket-key={row.bucket_key} data-bucket-kind="usage" data-usage-bucket={row.bucket_key}>
          <td>{bounds(row.period.start, row.period.end)}</td><td>{exactUsageText(row.quantity)}</td>
        </tr>)}</tbody>
      </table>
    </div>}
    {error !== null ? <button type="button" className="quiet-button" disabled={busy} onClick={() => setRequest((current) => ({ ...current, attempt: current.attempt + 1 }))}>Retry history page</button>
      : snapshot?.progress.nextCursor != null && <button type="button" className="quiet-button" disabled={busy} onClick={() => setRequest((current) => ({ cursor: snapshot.progress.nextCursor, attempt: current.attempt + 1 }))}>Load more history</button>}
  </div>;
}

export function BudgetDailyHistory(props: Props) {
  return <History key={historyContextKey(props.context)} {...props} />;
}
