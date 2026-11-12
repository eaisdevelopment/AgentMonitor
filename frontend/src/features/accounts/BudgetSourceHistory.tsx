import { useEffect, useRef, useState } from "react";

import { budgets, type BudgetReportListWireV1, type BudgetReportSummaryWireV1 } from "../../shared/api/client";
import { historyPageMatches } from "./budgetHistoryPagination";
import type { BudgetWindow } from "./budgetWindowNavigation";

type Props = Readonly<{
  accountId: string;
  resourceId: string;
  query: BudgetWindow;
  onExpired: () => void;
  reportHref: (reportId: string) => string;
  onSelect: (reportId: string) => void;
}>;
type Snapshot = Readonly<{
  items: readonly BudgetReportSummaryWireV1[];
  nextCursor: string | null;
  cursors: readonly string[];
  availability: BudgetReportListWireV1["availability"];
}>;
const readable = (value: string) => value.replaceAll("_", " ");
const instant = (value: string) => new Date(value).toLocaleString(undefined, { timeZoneName: "short" });
const bounds = (start: string, end: string) => `${start.slice(0, 10)} to ${end.slice(0, 10)} UTC (end exclusive)`;
function sameInstant(left: string, right: string): boolean {
  const normalized = (value: string) => {
    const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?Z$/.exec(value);
    if (match === null) throw new Error("source_history_timestamp_invalid");
    return `${match[1]}.${(match[2] ?? "").padEnd(6, "0")}Z`;
  };
  return normalized(left) === normalized(right);
}

function SourceHistory({ accountId, resourceId, query, onExpired, reportHref, onSelect }: Props) {
  const [opened, setOpened] = useState(false);
  const [request, setRequest] = useState<Readonly<{ cursor: string | null; attempt: number }>>({ cursor: null, attempt: 0 });
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const previous = useRef(snapshot);
  previous.current = snapshot;
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const expired = useRef(onExpired);
  expired.current = onExpired;

  useEffect(() => {
    if (!opened) return;
    const controller = new AbortController();
    setBusy(true);
    setError(null);
    void (async () => {
      try {
        const result = await budgets.reports(resourceId, { account_id: accountId, ...query, limit: 50,
          ...(request.cursor === null ? {} : { cursor: request.cursor }) }, controller.signal);
        if (controller.signal.aborted) return;
        if (!result.ok) {
          if (result.problem.code === "dashboard_authentication_required") expired.current();
          else setError(result.problem.status === 410
            ? "The source history continuation expired. Loaded reports are unchanged. Refresh source history to restart this list."
            : "Source history could not be loaded. Loaded reports are unchanged. Retry source history or refresh this list.");
          return;
        }
        const value = result.data;
        const context = { accountId, resourceId, periodStart: query.period_start, periodEnd: query.period_end, asOf: query.as_of };
        // Reuse exact timestamp comparison, including the API's microseconds.
        if (!["available", "partial"].includes(value.availability.state)
          || value.account_id !== accountId || value.resource_id !== resourceId
          || !sameInstant(value.period.start, query.period_start) || !sameInstant(value.period.end, query.period_end)
          || !sameInstant(value.as_of, query.as_of)
          || value.items.some(report => !historyPageMatches({ ...context, reportId: report.report_id }, report, value.as_of))) {
          throw new Error("source_history_context_mismatch");
        }
        const prior = previous.current;
        if (request.cursor !== null && (prior === null || request.cursor !== prior.nextCursor)) throw new Error("source_history_cursor_changed");
        const retained = request.cursor === null ? [] : prior?.items ?? [];
        const cursors = request.cursor === null ? [] : [...(prior?.cursors ?? []), request.cursor];
        const next = value.page.next_cursor;
        if (value.page.has_more ? value.items.length === 0 || typeof next !== "string" || next.length === 0 || cursors.includes(next) : next !== null) {
          throw new Error("source_history_page_invalid");
        }
        const seen = new Set(retained.map(report => report.report_id));
        for (const report of value.items) {
          if (!report.report_id || seen.has(report.report_id)) throw new Error("source_history_report_duplicate");
          seen.add(report.report_id);
        }
        setSnapshot({ items: [...retained, ...value.items], nextCursor: next, cursors, availability: value.availability });
      } catch {
        if (!controller.signal.aborted) setError("Source history could not be loaded consistently. Loaded reports are unchanged. Retry source history or refresh this list.");
      } finally {
        if (!controller.signal.aborted) setBusy(false);
      }
    })();
    return () => controller.abort();
  }, [opened, accountId, resourceId, query.period_start, query.period_end, query.as_of, request]);

  return <details className="account-secondary" data-source-history={resourceId} onToggle={(event) => { if (event.currentTarget.open) setOpened(true); }}>
    <summary>Source history</summary>
    {opened && <div data-source-history-content aria-busy={busy}>
      <p>Retained reports for {bounds(query.period_start, query.period_end)}. Original scopes are preserved; selecting a report does not collect data.</p>
      <p>Stored snapshot as of <time dateTime={query.as_of}>{instant(query.as_of)}</time>.</p>
      {busy && <p role="status">Reading source history…</p>}
      {error !== null && <p role="alert">{error}</p>}
      {snapshot !== null && <>
        {snapshot.availability.state !== "available" && <p role="status">Source history {snapshot.availability.state}: {readable(snapshot.availability.reason_code)}.</p>}
        {snapshot.items.length === 0 ? <p>No retained report for this interval.</p> : <>
          <p>{snapshot.items.length} retained reports loaded.{snapshot.nextCursor !== null && " More history available."}</p>
          <div className="table-scroll" role="region" aria-label="Retained source reports" tabIndex={0}>
            <table><caption>Original report scopes and collection times</caption>
              <thead><tr><th scope="col">Provider billing scope</th><th scope="col">Source</th><th scope="col">Collected</th><th scope="col">Coverage</th><th scope="col">Report</th></tr></thead>
              <tbody>{snapshot.items.map(report => <tr key={report.report_id} data-source-report={report.report_id}>
                <td>{report.scope_id ?? "Not established"}<br />Scope generation {report.scope_generation}<br />{readable(report.scope_evidence)}</td>
                <td>{report.source_id}<br />{readable(report.source_category)}<br />{readable(report.cost_basis)}
                  <br />{report.grouping.length === 0 ? "No grouping" : `Grouped by ${report.grouping.map(readable).join(", ")}`}
                  {report.currency !== null && <><br />Currency: {report.currency}</>}</td>
                <td><time data-source-collected dateTime={report.collected_at}>{instant(report.collected_at)}</time><br />Data through: {report.source_data_through === null ? "Not reported" : <time dateTime={report.source_data_through}>{instant(report.source_data_through)}</time>}</td>
                <td>{readable(report.completeness)}<br />{report.covered_period === null ? "Coverage not reported" : bounds(report.covered_period.start, report.covered_period.end)}</td>
                <td><a href={reportHref(report.report_id)} onClick={(event) => {
                  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
                  event.preventDefault(); onSelect(report.report_id);
                }}>View report</a></td>
              </tr>)}</tbody>
            </table>
          </div>
        </>}
      </>}
      {error !== null ? <button type="button" disabled={busy} onClick={() => { setBusy(true); setRequest(current => ({ ...current, attempt: current.attempt + 1 })); }}>Retry source history</button>
        : snapshot?.nextCursor != null && <button type="button" disabled={busy} onClick={() => { setBusy(true); setRequest(current => ({ cursor: snapshot.nextCursor, attempt: current.attempt + 1 })); }}>Load more reports</button>}
      <button type="button" className="quiet-button" disabled={busy} onClick={() => { setBusy(true); setRequest(current => ({ cursor: null, attempt: current.attempt + 1 })); }}>Refresh source history</button>
    </div>}
  </details>;
}

export function BudgetSourceHistory(props: Props) {
  return <SourceHistory key={JSON.stringify([props.accountId, props.resourceId, props.query.period_start, props.query.period_end, props.query.as_of])} {...props} />;
}
