import { useCallback, useEffect, useRef, useState } from "react";
import { metricAvailability, remainingPercentage } from "./quotaPresentation";

import {
  appendCapacityHistoryPage,
  capacity,
  capacityHistoryContinuation,
  type AccountCapacityViewV1,
  type CapacityHistoryPageV1,
  type CapacityHistoryPointV1,
  type ExactMetricFieldWireV1,
  type QuotaWindowPageV1,
} from "../../shared/api/client";

type CapacityHistoryQuery = Readonly<{
  accountId: string;
  rangeFrom: string;
  before: string;
  metric: "remaining_ratio";
  seriesKind: "poll_snapshot";
}>;

type CapacityState =
  | Readonly<{ kind: "loading" }>
  | Readonly<{ kind: "error"; message: string }>
  | Readonly<{
      kind: "ready";
      account: AccountCapacityViewV1;
      quotas: QuotaWindowPageV1;
      historyPages: readonly CapacityHistoryPageV1[] | null;
      historyQuery: CapacityHistoryQuery;
      historyMessage: string | null;
      historyPageMessage: string | null;
      historyLoadingMore: boolean;
      refreshMessage: string | null;
    }>;

function exactMetricValue(field: ExactMetricFieldWireV1): string {
  if (field.availability !== "available" || field.value === null) {
    return field.reason_code ?? field.availability.replaceAll("_", " ");
  }
  const { coefficient, scale, unit } = field.value;
  if (scale === 0) return `${coefficient} ${unit}`;
  return scale > 0
    ? `${coefficient} × 10^-${scale} ${unit}`
    : `${coefficient} × 10^${Math.abs(scale)} ${unit}`;
}

function ExactMetric({ field }: Readonly<{ field: ExactMetricFieldWireV1 }>) {
  return <>{exactMetricValue(field)}<small>{field.availability.replaceAll("_", " ")} · {field.precision} · {field.confidence} · {field.value_kind.replaceAll("_", " ")}</small></>;
}

function chartNumber(point: CapacityHistoryPointV1): number | null {
  const exact = point.value.value;
  if (point.value.availability !== "available" || exact === null) return null;
  const coefficient = Number(exact.coefficient);
  const value = coefficient * (10 ** -exact.scale);
  return Number.isFinite(value) ? value : null;
}

function CapacityHistory({
  pages,
  message,
  pageMessage,
  loadingMore,
  onLoadMore,
}: Readonly<{
  pages: readonly CapacityHistoryPageV1[] | null;
  message: string | null;
  pageMessage: string | null;
  loadingMore: boolean;
  onLoadMore: () => void;
}>) {
  if (pages === null || pages.length === 0) return (
    <section className="history-panel" aria-labelledby="capacity-history-title">
      <h3 id="capacity-history-title">Capacity history</h3>
      <p role="status">{message ?? "Capacity history is unavailable."}</p>
    </section>
  );

  const history = pages[0]!;
  const lastPage = pages[pages.length - 1]!;
  const items = pages.flatMap((page) => page.items);
  const continuation = capacityHistoryContinuation(lastPage.page);
  const plotted = items.flatMap((point, index) => {
    const value = chartNumber(point);
    const observed = Date.parse(point.observed_at);
    return value === null || !Number.isFinite(observed) ? [] : [{ point, index, value, observed }];
  });
  const times = plotted.map((entry) => entry.observed);
  const values = plotted.map((entry) => entry.value);
  const minTime = Math.min(...times);
  const maxTime = Math.max(...times);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const x = (value: number, index: number) => plotted.length === 1 || minTime === maxTime
    ? 50 + (index * 28)
    : 24 + (((value - minTime) / (maxTime - minTime)) * 552);
  const y = (value: number) => minValue === maxValue
    ? 64
    : 112 - (((value - minValue) / (maxValue - minValue)) * 88);

  return (
    <section className="history-panel" aria-labelledby="capacity-history-title">
      <div className="panel-heading">
        <div><p className="panel-code">365-DAY BOUNDED RANGE</p><h3 id="capacity-history-title">Capacity history</h3></div>
        <span className={`state-chip state-${history.availability.state}`}>{history.availability.state}</span>
      </div>
      {items.length === 0 ? (
        <div className="empty-telemetry"><div><strong>No retained observations in this range.</strong><p>{history.availability.reason_code.replaceAll("_", " ")}.</p></div></div>
      ) : <>
        <svg
          className="history-chart"
          viewBox="0 0 600 140"
          role="img"
          aria-label="Capacity history trend"
          data-observation-ids={items.map((point) => point.observation_id).join(" ")}
        >
          <title>Provider-reported capacity points over time; exact values follow in the table.</title>
          <line x1="24" y1="112" x2="576" y2="112" />
          <line x1="24" y1="24" x2="24" y2="112" />
          {plotted.map((entry, index) => (
            <g key={entry.point.observation_id}>
              <circle cx={x(entry.observed, index)} cy={y(entry.value)} r="5" />
              <title>{entry.point.safe_label ?? entry.point.window_key}: {exactMetricValue(entry.point.value)} at {new Date(entry.point.observed_at).toLocaleString()}</title>
            </g>
          ))}
        </svg>
        <p className="provenance-line">Points are not interpolated. Exact values, units, timestamps, and lineage are listed below.</p>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Capacity history table">
          <table aria-label="Capacity history exact values">
            <caption>Real retained capacity observations matching the visible trend points</caption>
            <thead><tr><th scope="col">Window</th><th scope="col">Exact value</th><th scope="col">Observed</th><th scope="col">State</th><th scope="col">Source</th><th scope="col">Trace</th></tr></thead>
            <tbody>{items.map((point) => (
              <tr key={point.observation_id}>
                <th scope="row">{point.safe_label ?? point.window_key}<small>{point.semantic_role} · definition {point.definition_version}</small></th>
                <td className="history-exact-value"><ExactMetric field={point.value} /></td>
                <td>{new Date(point.observed_at).toLocaleString()}<small>Stored {new Date(point.stored_at).toLocaleString()}</small></td>
                <td>{point.freshness}<small>{point.completeness} · {point.series_kind.replaceAll("_", " ")}</small></td>
                <td>{point.provenance.source_id}<small>{point.provenance.source_class.replaceAll("_", " ")} · {point.provenance.precision} · {point.provenance.confidence}</small></td>
                <td><span className="history-observation-id">{point.observation_id}</span><small>Run {point.collection_run_id}</small></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </>}
      <p className="pagination-note" role="status">
        Showing {items.length} retained {items.length === 1 ? "observation" : "observations"} from {pages.length} bounded {pages.length === 1 ? "page" : "pages"}.{" "}
        {continuation.kind === "available"
          ? "Additional pages remain for this 365-day range."
          : continuation.kind === "complete"
            ? "No additional pages remain for this 365-day range."
            : "The service reported additional history without a usable continuation cursor."}
      </p>
      {continuation.kind === "available" && (
        <button type="button" className="quiet-button" disabled={loadingMore} onClick={onLoadMore}>
          {loadingMore ? "Loading next history page…" : "Load next history page"}
        </button>
      )}
      {pageMessage !== null && <p role="alert">{pageMessage}</p>}
    </section>
  );
}

export function CapacityPanel({
  accountId,
  onExpired,
}: Readonly<{ accountId: string; onExpired: () => void }>) {
  const [state, setState] = useState<CapacityState>({ kind: "loading" });
  const historyPageController = useRef<AbortController | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    historyPageController.current?.abort();
    historyPageController.current = null;
    setState({ kind: "loading" });
    try {
      const now = Date.now();
      const historyQuery: CapacityHistoryQuery = {
        accountId,
        rangeFrom: new Date(now - (365 * 24 * 60 * 60 * 1000)).toISOString(),
        before: new Date(now).toISOString(),
        metric: "remaining_ratio",
        seriesKind: "poll_snapshot",
      };
      const [account, quotas, history] = await Promise.all([
        capacity.account(accountId, signal),
        capacity.quotaWindows(accountId, signal),
        capacity.history({
          ...historyQuery,
          signal,
        }),
      ]);
      if (!account.ok) {
        if (account.problem.code === "dashboard_authentication_required") onExpired();
        else setState({ kind: "error", message: "Capacity data is unavailable from the local service." });
        return;
      }
      if (!quotas.ok) {
        if (quotas.problem.code === "dashboard_authentication_required") onExpired();
        else setState({ kind: "error", message: "Quota windows are unavailable from the local service." });
        return;
      }
      if (!history.ok && history.problem.code === "dashboard_authentication_required") {
        onExpired();
        return;
      }
      setState({
        kind: "ready",
        account: account.data,
        quotas: quotas.data,
        historyPages: history.ok ? [history.data] : null,
        historyQuery,
        historyMessage: history.ok ? null : "Capacity history is unavailable from the local service.",
        historyPageMessage: null,
        historyLoadingMore: false,
        refreshMessage: null,
      });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setState({ kind: "error", message: "The local capacity service is unavailable." });
    }
  }, [accountId, onExpired]);

  const refreshCurrent = useCallback(async (signal: AbortSignal) => {
    try {
      const [account, quotas] = await Promise.all([
        capacity.account(accountId, signal), capacity.quotaWindows(accountId, signal),
      ]);
      if ((!account.ok && account.problem.code === "dashboard_authentication_required") ||
          (!quotas.ok && quotas.problem.code === "dashboard_authentication_required")) {
        onExpired();
        return;
      }
      if (!account.ok || !quotas.ok) {
        setState((current) => current.kind === "ready"
          ? { ...current, refreshMessage: "Quota refresh failed. Displayed observations are from the previous read." }
          : current);
        return;
      }
      setState((current) => current.kind === "ready"
        ? { ...current, account: account.data, quotas: quotas.data, refreshMessage: null }
        : current);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setState((current) => current.kind === "ready"
        ? { ...current, refreshMessage: "Quota refresh failed. Displayed observations are from the previous read." }
        : current);
    }
  }, [accountId, onExpired]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    let refreshing = false;
    const interval = window.setInterval(() => {
      if (refreshing) return;
      refreshing = true;
      void refreshCurrent(controller.signal).finally(() => { refreshing = false; });
    }, 30_000);
    return () => {
      window.clearInterval(interval);
      controller.abort();
      historyPageController.current?.abort();
    };
  }, [load, refreshCurrent]);

  const loadMoreHistory = async () => {
    if (
      state.kind !== "ready" ||
      state.historyPages === null ||
      state.historyPages.length === 0 ||
      state.historyLoadingMore
    ) return;
    const lastPage = state.historyPages[state.historyPages.length - 1]!;
    const continuation = capacityHistoryContinuation(lastPage.page);
    if (continuation.kind !== "available") return;

    const query = state.historyQuery;
    const requestedCursor = continuation.cursor;
    const controller = new AbortController();
    historyPageController.current?.abort();
    historyPageController.current = controller;
    setState({ ...state, historyLoadingMore: true, historyPageMessage: null });

    try {
      const result = await capacity.history({
        ...query,
        cursor: requestedCursor,
        signal: controller.signal,
      });
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") {
          onExpired();
          return;
        }
        setState((current) => current.kind === "ready" && current.historyQuery === query
          ? {
              ...current,
              historyLoadingMore: false,
              historyPageMessage: "The next history page is unavailable. Existing observations remain visible.",
            }
          : current);
        return;
      }
      setState((current) => {
        if (
          current.kind !== "ready" ||
          current.historyQuery !== query ||
          current.historyPages === null ||
          current.historyPages.length === 0
        ) return current;
        const currentLastPage = current.historyPages[current.historyPages.length - 1]!;
        const currentContinuation = capacityHistoryContinuation(currentLastPage.page);
        if (
          currentContinuation.kind !== "available" ||
          currentContinuation.cursor !== requestedCursor
        ) return current;
        const appended = appendCapacityHistoryPage(current.historyPages, result.data);
        if (!appended.ok) return {
          ...current,
          historyLoadingMore: false,
          historyPageMessage: "The next history page was incompatible and was not displayed.",
        };
        return {
          ...current,
          historyPages: appended.pages,
          historyLoadingMore: false,
          historyPageMessage: null,
        };
      });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setState((current) => current.kind === "ready" && current.historyQuery === query
        ? {
            ...current,
            historyLoadingMore: false,
            historyPageMessage: "The next history page could not be read. Existing observations remain visible.",
          }
        : current);
    } finally {
      if (historyPageController.current === controller) historyPageController.current = null;
    }
  };

  if (state.kind === "loading") return (
    <section className="telemetry-panel" aria-labelledby="quota-title" aria-busy="true">
      <div className="panel-heading"><div><h2 id="quota-title">Usage allowance</h2></div></div>
      <p className="skeleton-copy" role="status">Reading account capacity…</p>
    </section>
  );
  if (state.kind === "error") return (
    <section className="telemetry-panel" aria-labelledby="quota-title">
      <div className="panel-heading"><div><h2 id="quota-title">Usage allowance</h2></div><span className="state-chip state-warning">Unavailable</span></div>
      <p role="alert">{state.message}</p>
      <button type="button" className="quiet-button" onClick={() => { void load(); }}>Retry capacity</button>
    </section>
  );

  const healthRows = state.account.items.filter((item) => item.health !== null);
  return (
    <section className="telemetry-panel usage-allowance" aria-labelledby="quota-title">
      <div className="panel-heading">
        <div><h2 id="quota-title">Usage allowance</h2><p className="section-description">Each allowance window belongs to this account.</p></div>
        <span className="workspace-updated">Latest provider readings</span>
      </div>
      {state.refreshMessage !== null && <p role="status">{state.refreshMessage}</p>}
      {state.quotas.items.length > 0 && <div className="allowance-cards">{state.quotas.items.map((window) => {
        const percentage = remainingPercentage(window.allowance?.remaining_percentage ?? window.remaining_ratio);
        return <article className="allowance-card" key={window.window_id}>
          <div className="allowance-card-heading"><h3>{window.safe_label ?? window.window_key}</h3><span className={`reading-freshness reading-${window.freshness}`}>{window.freshness === "fresh" ? "Up to date" : window.freshness.replaceAll("_", " ")}</span></div>
          <p className="allowance-value"><strong>{percentage?.label ?? metricAvailability(window.remaining_ratio)}</strong><span>left</span></p>
          {percentage !== null && <div className="allowance-track" role="meter" aria-label={`${window.safe_label ?? window.window_key} remaining allowance`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percentage.value} aria-valuetext={`${percentage.label} left`}><span style={{ width: `${percentage.value}%` }} /></div>}
          <p className="allowance-time">Updated <time dateTime={window.collected_at}>{new Date(window.collected_at).toLocaleString()}</time></p>
          {window.allowance && <p className="allowance-time">{window.allowance.calculation === "100_minus_used_percent" ? "Calculated: 100% minus reported usage." : "Calculated from reported remaining ratio."}{window.allowance.remaining_percentage.precision === "rounded" ? " Source is rounded." : ""}</p>}
        </article>;
      })}</div>}
      {state.quotas.items.length === 0 && <p className="workspace-notice">{state.quotas.availability.state === "available" ? "No quota readings for this account yet." : "Quota readings are unavailable."}</p>}
      <details className="account-secondary quota-technical">
      <summary>Technical details <span>Exact quota values and collection source</span></summary>
      <h3>Quota windows</h3>
      <p className="provenance-line">{state.quotas.availability.reason_code.replaceAll("_", " ")} · as of {new Date(state.quotas.availability.as_of).toLocaleString()}</p>
      {healthRows.length > 0 && (
        <div className="health-strip" aria-label="Capacity health">
          {healthRows.map((item) => item.health && (
            <div key={item.subject.resource_id}>
              <strong>{item.health.state}</strong>
              <span>{item.health.completeness} · {item.health.freshness}</span>
              <span>Policy {item.health.policy_id} · version {item.health.policy_version}</span>
              <span>Constraining window {item.health.constraining_window_id ?? "not reported"}</span>
              <span>Explanation {item.health.explanation_codes.length === 0 ? "not reported" : item.health.explanation_codes.join(", ").replaceAll("_", " ")}</span>
            </div>
          ))}
        </div>
      )}
      {state.quotas.items.length === 0 && state.quotas.availability.state === "available" ? (
        <div className="empty-telemetry"><div><strong>No quota windows are available.</strong><p>The API reported no capacity observations for this account.</p></div></div>
      ) : state.quotas.items.length === 0 ? (
        <div className="empty-telemetry"><div><strong>Quota observations {state.quotas.availability.state}.</strong><p>{state.quotas.availability.reason_code.replaceAll("_", " ")}.</p></div></div>
      ) : (
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Quota windows table">
          <table>
            <caption>Provider-reported windows with exact values and freshness</caption>
            <thead><tr><th scope="col">Window</th><th scope="col">Used</th><th scope="col">Remaining</th><th scope="col">Limit</th><th scope="col">Remaining ratio</th><th scope="col">Freshness</th><th scope="col">Observed</th><th scope="col">Trace and provenance</th></tr></thead>
            <tbody>{state.quotas.items.map((window) => (
              <tr key={window.window_id}>
                <th scope="row">{window.safe_label ?? window.window_key}<small>{window.subject.provider_key}</small></th>
                <td><ExactMetric field={window.used} /></td>
                <td><ExactMetric field={window.remaining} /></td>
                <td><ExactMetric field={window.limit} /></td>
                <td><ExactMetric field={window.remaining_ratio} /></td>
                <td><span className={`state-chip state-${window.freshness}`}>{window.freshness.replaceAll("_", " ")}</span></td>
                <td>{window.observed_at === null ? "Unknown" : new Date(window.observed_at).toLocaleString()}</td>
                <td><dl className="quota-provenance">
                  <div><dt>Provider</dt><dd>{window.subject.provider_key}</dd></div>
                  <div><dt>Observation</dt><dd className="quota-observation-id">{window.current_observation_id}</dd></div>
                  <div><dt>Collection run</dt><dd className="quota-collection-run-id">{window.collection_run_id}</dd></div>
                  <div><dt>Observed</dt><dd>{window.observed_at === null ? "Unknown" : new Date(window.observed_at).toLocaleString()}</dd></div>
                  <div><dt>Collected</dt><dd>{new Date(window.collected_at).toLocaleString()}</dd></div>
                  <div><dt>Stored</dt><dd>{new Date(window.stored_at).toLocaleString()}</dd></div>
                  {window.provenance === null || window.provenance === undefined ? (
                    <div><dt>Source</dt><dd>Provenance unavailable</dd></div>
                  ) : <>
                    <div><dt>Source</dt><dd>{window.provenance.source_id}</dd></div>
                    <div><dt>Source class</dt><dd>{window.provenance.source_class.replaceAll("_", " ")}</dd></div>
                    <div><dt>Adapter</dt><dd>{window.provenance.adapter_id} · {window.provenance.adapter_version}</dd></div>
                    <div><dt>Mechanism version</dt><dd>{window.provenance.mechanism_version}</dd></div>
                    <div><dt>Provider version</dt><dd>{window.provenance.provider_version ?? "Not reported"}</dd></div>
                    <div><dt>Freshness deadline</dt><dd>{window.provenance.freshness_deadline === null ? "Unknown" : new Date(window.provenance.freshness_deadline).toLocaleString()}</dd></div>
                    <div><dt>Freshness policy</dt><dd>{window.provenance.freshness_policy_id}</dd></div>
                    <div><dt>Precision</dt><dd>{window.provenance.precision}</dd></div>
                    <div><dt>Confidence</dt><dd>{window.provenance.confidence} · {window.provenance.confidence_reason_code.replaceAll("_", " ")}</dd></div>
                  </>}
                </dl></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      {state.quotas.page.has_more && <p className="pagination-note" role="status">More quota windows are available beyond this page.</p>}
      </details>
      <details className="account-secondary quota-history">
      <summary>Usage history <span>Previous allowance readings</span></summary>
      <CapacityHistory
        pages={state.historyPages}
        message={state.historyMessage}
        pageMessage={state.historyPageMessage}
        loadingMore={state.historyLoadingMore}
        onLoadMore={() => { void loadMoreHistory(); }}
      />
      </details>
    </section>
  );
}
