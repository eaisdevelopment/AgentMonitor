import { useCallback, useEffect, useState } from "react";

import {
  capacity,
  type AccountCapacityViewV1,
  type ExactMetricFieldWireV1,
  type QuotaWindowPageV1,
} from "../../shared/api/client";

type CapacityState =
  | Readonly<{ kind: "loading" }>
  | Readonly<{ kind: "error"; message: string }>
  | Readonly<{ kind: "ready"; account: AccountCapacityViewV1; quotas: QuotaWindowPageV1 }>;

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

export function CapacityPanel({
  accountId,
  onExpired,
}: Readonly<{ accountId: string; onExpired: () => void }>) {
  const [state, setState] = useState<CapacityState>({ kind: "loading" });

  const load = useCallback(async (signal?: AbortSignal) => {
    setState({ kind: "loading" });
    try {
      const [account, quotas] = await Promise.all([
        capacity.account(accountId, signal),
        capacity.quotaWindows(accountId, signal),
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
      setState({ kind: "ready", account: account.data, quotas: quotas.data });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setState({ kind: "error", message: "The local capacity service is unavailable." });
    }
  }, [accountId, onExpired]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  if (state.kind === "loading") return (
    <section className="telemetry-panel" aria-labelledby="quota-title" aria-busy="true">
      <div className="panel-heading"><div><p className="panel-code">CAPACITY</p><h2 id="quota-title">Quota windows</h2></div></div>
      <p className="skeleton-copy" role="status">Reading account capacity…</p>
    </section>
  );
  if (state.kind === "error") return (
    <section className="telemetry-panel" aria-labelledby="quota-title">
      <div className="panel-heading"><div><p className="panel-code">CAPACITY</p><h2 id="quota-title">Quota windows</h2></div><span className="state-chip state-warning">Unavailable</span></div>
      <p role="alert">{state.message}</p>
      <button type="button" className="quiet-button" onClick={() => { void load(); }}>Retry capacity</button>
    </section>
  );

  const healthRows = state.account.items.filter((item) => item.health !== null);
  return (
    <section className="telemetry-panel" aria-labelledby="quota-title">
      <div className="panel-heading">
        <div><p className="panel-code">CAPACITY</p><h2 id="quota-title">Quota windows</h2></div>
        <span className={`state-chip state-${state.quotas.availability.state}`}>
          {state.quotas.availability.state}
        </span>
      </div>
      <p className="provenance-line">
        {state.quotas.availability.reason_code.replaceAll("_", " ")} · as of {new Date(state.quotas.availability.as_of).toLocaleString()}
      </p>
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
                  <div><dt>Observation</dt><dd>{window.current_observation_id}</dd></div>
                  <div><dt>Collection run</dt><dd>{window.collection_run_id}</dd></div>
                  <div><dt>Collected</dt><dd>{new Date(window.collected_at).toLocaleString()}</dd></div>
                  <div><dt>Stored</dt><dd>{new Date(window.stored_at).toLocaleString()}</dd></div>
                  <div><dt>Source/version</dt><dd>Unavailable in API v1</dd></div>
                </dl></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      {state.quotas.page.has_more && <p className="pagination-note" role="status">More quota windows are available beyond this page.</p>}
    </section>
  );
}
