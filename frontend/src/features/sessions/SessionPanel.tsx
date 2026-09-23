import { useCallback, useEffect, useState } from "react";

import {
  runtime,
  type AgentProcessPageV1,
  type AgentSessionPageV1,
  type AgentSessionViewV1,
} from "../../shared/api/client";

type RuntimeState =
  | Readonly<{ kind: "loading" }>
  | Readonly<{ kind: "error"; message: string }>
  | Readonly<{
      kind: "ready";
      processes: AgentProcessPageV1 | null;
      sessions: AgentSessionPageV1;
      selected: AgentSessionViewV1 | null;
      detailMessage: string | null;
    }>;

function Provenance({ item }: Readonly<{ item: AgentSessionViewV1["provenance"] }>) {
  return (
    <dl className="provenance-grid">
      <div><dt>Source</dt><dd>{item.source_id}</dd></div>
      <div><dt>Collected</dt><dd>{new Date(item.collected_at).toLocaleString()}</dd></div>
      <div><dt>Freshness</dt><dd>{item.freshness_availability.state.replaceAll("_", " ")}</dd></div>
      <div><dt>Version</dt><dd>{item.provider_version ?? item.provider_version_availability.state.replaceAll("_", " ")}</dd></div>
      <div><dt>Confidence</dt><dd>{item.confidence} · {item.confidence_reason_code.replaceAll("_", " ")}</dd></div>
      <div><dt>Value kind</dt><dd>{item.value_kind.replaceAll("_", " ")}</dd></div>
    </dl>
  );
}

export function SessionPanel({
  accountId,
  displayMode = "page",
  heading = "Sessions",
  onExpired,
}: Readonly<{
  accountId?: string;
  displayMode?: "page" | "panel";
  heading?: string;
  onExpired: () => void;
}>) {
  const [state, setState] = useState<RuntimeState>({ kind: "loading" });
  const titleId = displayMode === "page" ? "page-title" : "sessions-panel-title";
  const Heading = displayMode === "page" ? "h1" : "h2";

  const load = useCallback(async (signal?: AbortSignal) => {
    setState({ kind: "loading" });
    try {
      const processes = accountId === undefined ? await runtime.processes(signal) : null;
      const sessions = await runtime.sessions({ accountId, signal });
      if (processes !== null && !processes.ok) {
        if (processes.problem.code === "dashboard_authentication_required") onExpired();
        else setState({ kind: "error", message: "Runtime observations could not be loaded." });
        return;
      }
      if (!sessions.ok) {
        if (sessions.problem.code === "dashboard_authentication_required") onExpired();
        else setState({ kind: "error", message: "Session observations could not be loaded." });
        return;
      }
      setState({
        kind: "ready",
        processes: processes === null ? null : processes.data,
        sessions: sessions.data,
        selected: null,
        detailMessage: null,
      });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setState({ kind: "error", message: "The local runtime observation service is unavailable." });
    }
  }, [accountId, onExpired]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function selectSession(sessionId: string) {
    try {
      const result = await runtime.session(sessionId);
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        else setState((current) => current.kind === "ready" ? { ...current, detailMessage: "Session provenance is unavailable." } : current);
        return;
      }
      setState((current) => current.kind === "ready" ? { ...current, selected: result.data, detailMessage: null } : current);
    } catch {
      setState((current) => current.kind === "ready" ? { ...current, detailMessage: "Session provenance could not be loaded from the local service." } : current);
    }
  }

  if (state.kind === "loading") return (
    <section className="telemetry-panel" aria-labelledby={titleId} aria-busy="true"><div className="panel-heading"><div><p className="panel-code">RUNTIME</p><Heading id={titleId} tabIndex={displayMode === "page" ? -1 : undefined}>{heading}</Heading></div></div><p className="skeleton-copy" role="status">Reading runtime observations…</p></section>
  );
  if (state.kind === "error") return (
    <section className="telemetry-panel" aria-labelledby={titleId}><div className="panel-heading"><div><p className="panel-code">RUNTIME</p><Heading id={titleId} tabIndex={displayMode === "page" ? -1 : undefined}>{heading}</Heading></div><span className="state-chip state-warning">Unavailable</span></div><p role="alert">{state.message}</p><button type="button" className="quiet-button" onClick={() => { void load(); }}>Retry runtime</button></section>
  );

  return (
    <section className="telemetry-panel" aria-labelledby={titleId}>
      <div className="panel-heading"><div><p className="panel-code">RUNTIME / OBSERVATIONS</p><Heading id={titleId} tabIndex={displayMode === "page" ? -1 : undefined}>{heading}</Heading></div><span className={`state-chip state-${state.sessions.availability.state}`}>{state.sessions.availability.state}</span></div>
      <p className="provenance-line">{state.sessions.availability.reason_code.replaceAll("_", " ")} · as of {new Date(state.sessions.availability.as_of).toLocaleString()}</p>
      <div className="runtime-summary" aria-label="Runtime observations shown">
        {state.processes !== null && <div><strong>{state.processes.availability.state === "available" || state.processes.availability.state === "partial" ? state.processes.items.length : state.processes.availability.state}</strong><span>processes shown</span></div>}
        <div><strong>{state.sessions.availability.state === "available" || state.sessions.availability.state === "partial" ? state.sessions.items.length : state.sessions.availability.state}</strong><span>sessions shown</span></div>
      </div>
      {((state.processes?.page.has_more ?? false) || state.sessions.page.has_more) && <p className="pagination-note" role="status">More {(state.processes?.page.has_more ?? false) && state.sessions.page.has_more ? "process and session observations are" : (state.processes?.page.has_more ?? false) ? "process observations are" : "session observations are"} available beyond this page.</p>}
      {state.sessions.items.length === 0 && state.sessions.availability.state === "available" ? (
        <div className="empty-telemetry"><div><strong>No observed sessions are available.</strong><p>Account correlation remains unresolved until supported evidence exists.</p></div></div>
      ) : state.sessions.items.length === 0 ? (
        <div className="empty-telemetry"><div><strong>Session observation {state.sessions.availability.state}.</strong><p>{state.sessions.availability.reason_code.replaceAll("_", " ")}.</p></div></div>
      ) : (
        <div className="session-layout">
          <div className="session-list" aria-label="Observed sessions">{state.sessions.items.map((session) => (
            <article className="session-row" key={session.session_id}><div><strong>{session.identity.provider_key}</strong><p>{session.correlation_state.replaceAll("_", " ")} · account {session.account_id === null ? "unresolved" : "correlated"}</p></div><button type="button" className="quiet-button" onClick={() => { void selectSession(session.session_id); }}>Inspect provenance</button></article>
          ))}</div>
          {state.detailMessage !== null && <p role="status">{state.detailMessage}</p>}
          {state.selected !== null && (
            <aside className="session-detail" aria-labelledby="session-detail-title"><div className="panel-heading"><div><p className="panel-code">SESSION DETAIL</p>{displayMode === "page" ? <h2 id="session-detail-title">Observation provenance</h2> : <h3 id="session-detail-title">Observation provenance</h3>}</div><button type="button" className="quiet-button" onClick={() => setState((current) => current.kind === "ready" ? { ...current, selected: null } : current)}>Close</button></div><Provenance item={state.selected.provenance} /></aside>
          )}
        </div>
      )}
      {state.processes !== null && state.processes.items.length > 0 && (
        <div className="table-scroll runtime-processes" tabIndex={0} role="region" aria-label="Process observations table">
          <table><caption>Safe local process metadata</caption><thead><tr><th scope="col">Provider</th><th scope="col">PID</th><th scope="col">Presence</th><th scope="col">Label</th><th scope="col">Source</th><th scope="col">Observed</th></tr></thead><tbody>{state.processes.items.map((process) => (
            <tr key={process.process_id}><th scope="row">{process.provider_key ?? "Unresolved"}</th><td>{process.identity.pid}</td><td>{process.presence}</td><td>{process.executable_label.value ?? process.executable_label.state.replaceAll("_", " ")}</td><td>{process.provenance.source_id}</td><td>{new Date(process.last_observed_at).toLocaleString()}</td></tr>
          ))}</tbody></table>
        </div>
      )}
    </section>
  );
}
