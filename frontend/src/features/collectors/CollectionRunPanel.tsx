import { useCallback, useEffect, useState } from "react";

import { collections, type CollectionRunPageV1 } from "../../shared/api/client";

type RunState =
  | Readonly<{ kind: "loading" }>
  | Readonly<{ kind: "error"; message: string }>
  | Readonly<{ kind: "ready"; data: CollectionRunPageV1 }>;

export function CollectionRunPanel({
  displayMode = "page",
  onExpired,
}: Readonly<{ displayMode?: "page" | "panel"; onExpired: () => void }>) {
  const [state, setState] = useState<RunState>({ kind: "loading" });
  const titleId = displayMode === "page" ? "page-title" : "runs-panel-title";
  const Heading = displayMode === "page" ? "h1" : "h2";

  const load = useCallback(async (signal?: AbortSignal) => {
    setState({ kind: "loading" });
    try {
      const result = await collections.runs(signal);
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        else setState({ kind: "error", message: "Collection runs could not be loaded." });
        return;
      }
      setState({ kind: "ready", data: result.data });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setState({ kind: "error", message: "The local collection service is unavailable." });
    }
  }, [onExpired]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  if (state.kind === "loading") return (
    <section className="telemetry-panel" aria-labelledby={titleId} aria-busy="true"><div className="panel-heading"><div><p className="panel-code">COLLECTION</p><Heading id={titleId} tabIndex={displayMode === "page" ? -1 : undefined}>Collection runs</Heading></div></div><p className="skeleton-copy" role="status">Reading collection history…</p></section>
  );
  if (state.kind === "error") return (
    <section className="telemetry-panel" aria-labelledby={titleId}><div className="panel-heading"><div><p className="panel-code">COLLECTION</p><Heading id={titleId} tabIndex={displayMode === "page" ? -1 : undefined}>Collection runs</Heading></div><span className="state-chip state-warning">Unavailable</span></div><p role="alert">{state.message}</p><button type="button" className="quiet-button" onClick={() => { void load(); }}>Retry runs</button></section>
  );

  return (
    <section className="telemetry-panel" aria-labelledby={titleId}>
      <div className="panel-heading"><div><p className="panel-code">COLLECTION / HISTORY</p><Heading id={titleId} tabIndex={displayMode === "page" ? -1 : undefined}>Collection runs</Heading></div><span className={`state-chip state-${state.data.availability.state}`}>{state.data.availability.state}</span></div>
      <p className="provenance-line">{state.data.availability.reason_code.replaceAll("_", " ")} · as of {new Date(state.data.availability.as_of).toLocaleString()}</p>
      {state.data.items.length === 0 && state.data.availability.state === "available" ? (
        <div className="empty-telemetry"><div><strong>No collection runs have been recorded.</strong><p>Runs appear after a real provider or platform collection is executed.</p></div></div>
      ) : state.data.items.length === 0 ? (
        <div className="empty-telemetry"><div><strong>Collection history {state.data.availability.state}.</strong><p>{state.data.availability.reason_code.replaceAll("_", " ")}.</p></div></div>
      ) : (
        <div className="timeline-list">{state.data.items.map((run) => (
          <article className="timeline-row" data-collection-run="true" key={run.run_id}>
            <span className={`state-chip state-${run.state}`}>{run.state}</span>
            <div><strong>{run.provider_key} · {run.capability_id}</strong>
              <dl className="run-provenance">
                <div><dt>Run</dt><dd className="collection-run-id">{run.run_id}</dd></div>
                <div><dt>Source</dt><dd>{run.source_id}</dd></div>
                <div><dt>Adapter version</dt><dd>{run.adapter_version}</dd></div>
                <div><dt>Provider version</dt><dd>{run.provider_version ?? "Unavailable"}</dd></div>
                <div><dt>Requested</dt><dd>{new Date(run.requested_at).toLocaleString()}</dd></div>
                <div><dt>Started</dt><dd>{run.started_at === null ? "Not reported" : new Date(run.started_at).toLocaleString()}</dd></div>
                <div><dt>Completed</dt><dd>{run.completed_at === null ? "Not reported" : new Date(run.completed_at).toLocaleString()}</dd></div>
                <div><dt>Observations</dt><dd className="collection-observation-ids">{run.observation_ids.length === 0 ? "None reported" : run.observation_ids.join(", ")}</dd></div>
              </dl>
            </div>
            <div className="timeline-result"><span>{run.duration_ms === null ? "Duration unavailable" : `${run.duration_ms} ms`}</span><small>{run.error_code ?? run.outcome_code ?? "Outcome pending"}</small></div>
          </article>
        ))}</div>
      )}
      {state.data.page.has_more && <p className="pagination-note" role="status">More collection runs are available beyond this page.</p>}
    </section>
  );
}
