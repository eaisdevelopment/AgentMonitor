import { useCallback, useEffect, useState } from "react";

import {
  runtime,
  type AgentProcessMetricPageV1,
  type AgentProcessMetricViewV1,
  type AgentSessionPageV1,
  type AgentSessionViewV1,
} from "../../shared/api/client";

type RuntimeState =
  | Readonly<{ kind: "loading" }>
  | Readonly<{ kind: "error"; message: string }>
  | Readonly<{
      kind: "ready";
      processes: AgentProcessMetricPageV1 | null;
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

function words(value: string): string {
  return value.replaceAll("_", " ");
}

function unavailableMetric(
  field: Readonly<{ state: string; reason_code: string | null }> | null | undefined,
): string {
  if (field === null || field === undefined) return "unavailable — not reported by API v1";
  return `${words(field.state)}${field.reason_code === null ? "" : ` — ${words(field.reason_code)}`}`;
}

function integerMetric(
  field: AgentProcessMetricViewV1["parent_pid"],
): string {
  return field !== null && field !== undefined && field.state === "present" && field.value !== null
    ? String(field.value)
    : unavailableMetric(field);
}

function cpuMetric(process: AgentProcessMetricViewV1): string {
  const user = process.user_cpu_ticks;
  const system = process.system_cpu_ticks;
  if (user === null || user === undefined || user.state !== "present" || user.value === null) {
    return `user ${unavailableMetric(user)} · system ${system !== null && system !== undefined && system.state === "present" && system.value !== null ? `${system.value} ${system.unit ?? "ticks"}` : unavailableMetric(system)}`;
  }
  if (system === null || system === undefined || system.state !== "present" || system.value === null) {
    return `user ${user.value} ${user.unit ?? "ticks"} · system ${unavailableMetric(system)}`;
  }
  const totalTicks = user.value + system.value;
  const clockTicksPerSecond = process.clock_ticks_per_second;
  if (clockTicksPerSecond === null || clockTicksPerSecond === undefined) {
    return `${user.value} user + ${system.value} system ticks · ${totalTicks} total · rate unavailable`;
  }
  const cpuSeconds = totalTicks / clockTicksPerSecond;
  return `${user.value} user + ${system.value} system ticks · ${totalTicks} total · ${cpuSeconds.toFixed(2)} CPU s`;
}

function memoryMetric(process: AgentProcessMetricViewV1): string {
  const resident = process.resident_pages;
  const pageSizeBytes = process.page_size_bytes;
  if (resident === null || resident === undefined || resident.state !== "present" || resident.value === null) {
    return unavailableMetric(resident);
  }
  if (pageSizeBytes === null || pageSizeBytes === undefined) {
    return `${resident.value} pages · page size unavailable`;
  }
  const bytes = resident.value * pageSizeBytes;
  const units = ["B", "KiB", "MiB", "GiB"] as const;
  let displayed = bytes;
  let unitIndex = 0;
  while (displayed >= 1024 && unitIndex < units.length - 1) {
    displayed /= 1024;
    unitIndex += 1;
  }
  return `${resident.value} pages · ${displayed.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function elapsedLabel(milliseconds: number): string {
  const seconds = Math.max(0, Math.floor(milliseconds / 1000));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

function processFreshness(process: AgentProcessMetricViewV1): string {
  const now = Date.now();
  const observedAt = Date.parse(process.last_observed_at);
  const observationAge = Number.isFinite(observedAt)
    ? elapsedLabel(now - observedAt)
    : "unknown";
  const deadlineValue = process.provenance.freshness_deadline;
  if (deadlineValue === null) {
    return `Observed ${observationAge} ago · Freshness ${words(process.provenance.freshness_availability.state)}`;
  }
  const deadline = Date.parse(deadlineValue);
  if (!Number.isFinite(deadline)) {
    return `Observed ${observationAge} ago · Freshness unknown`;
  }
  const deadlineRelation = deadline <= now
    ? `passed ${elapsedLabel(now - deadline)} ago`
    : `in ${elapsedLabel(deadline - now)}`;
  return `Observed ${observationAge} ago · Freshness deadline ${deadlineRelation}`;
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
      const processes = accountId === undefined ? await runtime.processMetrics(signal) : null;
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
          <table><caption>Safe local process metadata with source freshness</caption><thead><tr><th scope="col">Provider</th><th scope="col">PID</th><th scope="col">Parent PID</th><th scope="col">Start marker</th><th scope="col">CPU</th><th scope="col">RSS memory</th><th scope="col">Threads</th><th scope="col">Kernel state</th><th scope="col">Presence</th><th scope="col">Label</th><th scope="col">Observed / freshness</th></tr></thead><tbody>{state.processes.items.map((process) => (
            <tr key={process.process_id} data-process-row="true"><th scope="row">{process.provider_key ?? "Unresolved"}</th><td>{process.identity.pid}</td><td className="process-parent-pid">{integerMetric(process.parent_pid)}</td><td className="process-start">{process.identity.start_time_ticks} ticks after boot · {process.clock_ticks_per_second === null || process.clock_ticks_per_second === undefined ? "clock rate unavailable" : `${process.clock_ticks_per_second} ticks/s`}</td><td className="process-cpu">{cpuMetric(process)}</td><td className="process-memory">{memoryMetric(process)}</td><td className="process-threads">{integerMetric(process.thread_count)}</td><td className="process-kernel-state">{process.kernel_state !== null && process.kernel_state !== undefined && process.kernel_state.state === "present" && process.kernel_state.value !== null ? process.kernel_state.value : unavailableMetric(process.kernel_state)}</td><td className="process-presence">{process.presence}</td><td>{process.executable_label.value ?? unavailableMetric(process.executable_label)}</td><td className="process-freshness"><span>{processFreshness(process)}</span><br /><span>{process.provenance.source_id}</span></td></tr>
          ))}</tbody></table>
        </div>
      )}
    </section>
  );
}
