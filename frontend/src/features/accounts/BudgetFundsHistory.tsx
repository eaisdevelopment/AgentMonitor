import { useEffect, useRef, useState, type CSSProperties } from "react";

import { capacity } from "../../shared/api/client";
import { exactUsageText } from "./budgetPresentation";
import {
  appendFundsHistoryPage, fundsHistoryContextKey, fundsHistoryGapReason, fundsHistoryPlot,
  FUNDS_HISTORY_PAGE_SIZE,
  type FundsHistoryContext, type FundsHistoryProgress,
} from "./budgetFundsHistoryPresentation";
import "./BudgetHistoryChart.css";

type Props = FundsHistoryContext & Readonly<{ onExpired: () => void }>;
const readable = (value: string) => value.replaceAll("_", " ");

function LoadedFundsHistory({ onExpired, ...context }: Props) {
  const key = fundsHistoryContextKey(context);
  const [progress, setProgress] = useState<FundsHistoryProgress | null>(null);
  const current = useRef(progress); current.current = progress;
  const expired = useRef(onExpired); expired.current = onExpired;
  const [request, setRequest] = useState<{ cursor: string | null; attempt: number }>({ cursor: null, attempt: 0 });
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [partial, setPartial] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setBusy(true); setError(null);
    void (async () => {
      try {
        const result = await capacity.history({ accountId: context.accountId, resourceId: context.resourceId,
          windowId: context.windowId, asOf: context.asOf, rangeFrom: context.periodStart, before: context.periodEnd,
          metric: "remaining", seriesKind: "poll_snapshot", limit: FUNDS_HISTORY_PAGE_SIZE,
          ...(request.cursor === null ? {} : { cursor: request.cursor }), signal: controller.signal });
        if (controller.signal.aborted) return;
        if (!result.ok) {
          if (result.problem.code === "dashboard_authentication_required") expired.current();
          setError("Balance history could not be read. Loaded observations remain unchanged. Retry this page; if the selection has expired, refresh the account view.");
          return;
        }
        const next = appendFundsHistoryPage(current.current, context, result.data, request.cursor);
        if (controller.signal.aborted) return;
        setProgress(next);
        setPartial(previous => previous || result.data.availability.state === "partial");
      } catch {
        if (!controller.signal.aborted) setError("Balance history could not be read consistently. Loaded observations retain their original values and times. Retry this page or refresh the account view.");
      } finally {
        if (!controller.signal.aborted) setBusy(false);
      }
    })();
    return () => controller.abort();
  }, [key, request.cursor, request.attempt]);

  const points = progress?.items ?? [];
  const plot = fundsHistoryPlot(points);
  const selected = plot.find(item => item.point.observation_id === selectedId);
  const text = (item: typeof plot[number]) => `${item.point.observed_at} · ${item.gap !== null || item.point.value.value === null
    ? `Gap: ${item.gap ?? "Amount not reported"}` : exactUsageText(item.point.value.value)} · Observation ${item.point.observation_id}`;
  const hasMore = progress?.nextCursor != null;

  return <section className="budget-history-chart" aria-label="Stored balance observations" aria-busy={busy}
    data-funds-history={context.windowId} data-funds-history-resource={context.resourceId} data-funds-history-window={context.windowId}>
    <p>Actual {context.currency} balance readings for this component only. Observations, not spending or daily totals. Gaps are not filled.</p>
    <p>From <time dateTime={context.periodStart}>{context.periodStart}</time> to <time dateTime={context.periodEnd}>{context.periodEnd}</time> (end exclusive).
      {" "}Stored as of <time dateTime={context.asOf}>{context.asOf}</time>.</p>
    {busy && <p role="status">Reading stored balance history… Loaded observations remain unchanged.</p>}
    {error !== null && <p role="alert">{error}</p>}
    {partial && <p role="status">The source returned partial history; missing observations are unknown.</p>}
    {progress !== null && points.length === 0 && <p>No stored balance observations in this interval. This does not mean a zero balance.</p>}
    {points.length > 0 && <>
      <p>Scale uses only the {points.length} loaded observations and may change when more are loaded. Positive and negative balances remain distinct; no lines are interpolated.</p>
      <ul className="budget-history-chart-entries" aria-label="Balance observations">
        {plot.map(item => {
          const style: CSSProperties & { "--chart-magnitude": number } = { "--chart-magnitude": item.magnitudeBasisPoints ?? 0 };
          return <li key={item.point.observation_id}>
            <button type="button" className="budget-history-chart-entry" aria-pressed={selectedId === item.point.observation_id}
              onClick={() => setSelectedId(item.point.observation_id)} aria-label={text(item)} title={text(item)}
              data-funds-observation={item.point.observation_id} data-funds-observed-at={item.point.observed_at}
              data-balance-point={item.direction === null ? undefined : item.point.observation_id}
              data-funds-direction={item.direction ?? "gap"} data-funds-magnitude={item.magnitudeBasisPoints ?? undefined}>
              <span className="budget-history-chart-track" aria-hidden="true">
                {item.direction !== null && <span className={`budget-history-chart-bar budget-history-chart-bar-${item.direction}`} style={style} />}
              </span>
              <span className="budget-history-chart-entry-label" aria-hidden="true">{item.point.observed_at.slice(5, 10)} {item.direction === null ? "Gap" : item.direction === "zero" ? "0" : item.direction === "negative" ? "−" : "+"}</span>
            </button>
          </li>;
        })}
      </ul>
      <p aria-live="polite">{selected === undefined ? "Select an observation for its exact value, UTC time and identity." : text(selected)}</p>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Exact balance observations">
        <table><caption>Exact balance history · {context.currency} · this component only</caption>
          <thead><tr><th scope="col">Observed (UTC)</th><th scope="col">Remaining</th><th scope="col">Quality</th><th scope="col">Observation</th><th scope="col">Collected / stored (UTC)</th></tr></thead>
          <tbody>{points.map(point => {
            const gap = fundsHistoryGapReason(point);
            return <tr key={point.observation_id} data-funds-history-observation={point.observation_id} data-balance-observation={point.observation_id}>
              <td><time dateTime={point.observed_at}>{point.observed_at}</time></td>
              <td data-balance-amount>{gap !== null || point.value.value === null ? `Gap · ${gap ?? "Amount not reported"}` : exactUsageText(point.value.value)}</td>
              <td>{readable(point.value.availability)} · {readable(point.value.precision)} · {readable(point.freshness)} · {readable(point.completeness)}</td>
              <td>{point.observation_id}</td>
              <td><time dateTime={point.collected_at}>{point.collected_at}</time><br /><time dateTime={point.stored_at}>{point.stored_at}</time></td>
            </tr>;
          })}</tbody>
        </table>
      </div>
    </>}
    {hasMore && <p>More history available; unloaded observations are unknown.</p>}
    {error !== null ? <button type="button" className="quiet-button" disabled={busy}
      onClick={() => setRequest(value => ({ ...value, attempt: value.attempt + 1 }))}>Retry balance history page</button>
      : hasMore && <button type="button" className="quiet-button" disabled={busy}
        onClick={() => setRequest(value => ({ cursor: progress?.nextCursor ?? null, attempt: value.attempt + 1 }))}>Load more balance history</button>}
  </section>;
}

function ExpandableFundsHistory(props: Props) {
  const [expanded, setExpanded] = useState(false);
  return <details onToggle={event => setExpanded(event.currentTarget.open)}>
    <summary>Balance history</summary>
    {expanded && <LoadedFundsHistory {...props} />}
  </details>;
}

export function BudgetFundsHistory(props: Props) {
  let key: string;
  try { key = fundsHistoryContextKey(props); }
  catch { return <p>Balance history is unavailable for this selection.</p>; }
  return <ExpandableFundsHistory key={key} {...props} />;
}
