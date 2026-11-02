import { useCallback, useEffect, useState } from "react";

import {
  runtime,
  type AgentProcessMetricPageV1,
  type AgentProcessMetricViewV1,
  type AgentSessionPageV1,
  type AgentSessionViewV1,
  type SessionTreeNodeV1,
  type SessionTreeViewV1,
} from "../../shared/api/client";

type RuntimeState =
  | Readonly<{ kind: "loading" }>
  | Readonly<{ kind: "error"; message: string }>
  | Readonly<{
      kind: "ready";
      processes: AgentProcessMetricPageV1 | null;
      sessions: AgentSessionPageV1;
      trees: Readonly<Record<string, SessionTreeViewV1>>;
      treeMessage: string | null;
      selected: AgentSessionViewV1 | null;
      detailMessage: string | null;
    }>;

function Provenance({ item }: Readonly<{ item: AgentSessionViewV1["provenance"] }>) {
  return (
    <dl className="provenance-grid">
      <div><dt>Source</dt><dd>{item.source_id}</dd></div>
      <div><dt>Source class</dt><dd>{words(item.source_class)}</dd></div>
      <div><dt>Observed</dt><dd>{item.observed_at === null ? words(item.observed_at_availability.state) : new Date(item.observed_at).toLocaleString()}</dd></div>
      <div><dt>Collected</dt><dd>{new Date(item.collected_at).toLocaleString()}</dd></div>
      <div><dt>Freshness</dt><dd>{item.freshness_availability.state.replaceAll("_", " ")}</dd></div>
      <div><dt>Freshness deadline</dt><dd>{item.freshness_deadline === null ? "Unknown" : new Date(item.freshness_deadline).toLocaleString()}</dd></div>
      <div><dt>Freshness policy</dt><dd>{item.freshness_policy_id}</dd></div>
      <div><dt>Adapter</dt><dd>{item.adapter_id} · {item.adapter_version}</dd></div>
      <div><dt>Mechanism version</dt><dd>{item.mechanism_version}</dd></div>
      <div><dt>Parser version</dt><dd>{item.parser_version ?? "Not applicable"}</dd></div>
      <div><dt>Provider protocol</dt><dd>{item.provider_protocol_version}</dd></div>
      <div><dt>Provider version</dt><dd>{item.provider_version ?? item.provider_version_availability.state.replaceAll("_", " ")}</dd></div>
      <div><dt>Precision</dt><dd>{item.precision}</dd></div>
      <div><dt>Confidence</dt><dd>{item.confidence} · {item.confidence_reason_code.replaceAll("_", " ")}</dd></div>
      <div><dt>Value kind</dt><dd>{item.value_kind.replaceAll("_", " ")}</dd></div>
      <div><dt>Derivation method</dt><dd>{item.derivation_method ?? "None — provider reported"}</dd></div>
      <div><dt>Input observations</dt><dd>{item.input_observation_ids.length === 0 ? "None" : item.input_observation_ids.join(", ")}</dd></div>
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

function SessionTreeNode({
  node,
  nodes,
  seen,
}: Readonly<{
  node: SessionTreeNodeV1;
  nodes: ReadonlyMap<string, SessionTreeNodeV1>;
  seen: ReadonlySet<string>;
}>) {
  const sessionId = node.session.session_id;
  const nextSeen = new Set(seen);
  nextSeen.add(sessionId);
  const children = node.child_session_ids.flatMap((childId) => {
    const child = nodes.get(childId);
    return child === undefined || nextSeen.has(childId) ? [] : [child];
  });
  return (
    <li data-session-tree-node="true">
      <details open>
        <summary>{node.session.identity.provider_key} session · {children.length} direct {children.length === 1 ? "child" : "children"}</summary>
        <p>{words(node.session.correlation_state)} · {node.orphan_reason === null ? "parent evidence confirmed" : words(node.orphan_reason)}</p>
        {children.length > 0 && <ul>{children.map((child) => (
          <SessionTreeNode key={child.session.session_id} node={child} nodes={nodes} seen={nextSeen} />
        ))}</ul>}
      </details>
    </li>
  );
}

function SessionTree({ tree }: Readonly<{ tree: SessionTreeViewV1 }>) {
  const nodes = new Map(tree.nodes.map((node) => [node.session.session_id, node]));
  const root = nodes.get(tree.root_session_id);
  return (
    <section className="session-tree" data-session-tree="true" aria-labelledby={`session-tree-${tree.root_session_id}`}>
      <div className="session-tree-heading">
        <h3 id={`session-tree-${tree.root_session_id}`}>Session hierarchy</h3>
        <p>Included {tree.included_count} · Excluded {tree.excluded_count} · Unknown {tree.unknown_count}</p>
      </div>
      {root === undefined ? (
        <p role="status">The hierarchy root is unavailable.</p>
      ) : (
        <ul className="session-tree-list"><SessionTreeNode node={root} nodes={nodes} seen={new Set()} /></ul>
      )}
      {tree.partial && <p className="pagination-note">Partial hierarchy: {tree.reason_codes.map(words).join(", ")}.</p>}
    </section>
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
      const treeResults = await Promise.all(sessions.data.items.map(async (session) => ({
        sessionId: session.session_id,
        result: await runtime.sessionTree(session.session_id, signal),
      })));
      if (treeResults.some(({ result }) => !result.ok && result.problem.code === "dashboard_authentication_required")) {
        onExpired();
        return;
      }
      const trees = Object.fromEntries(treeResults.flatMap(({ sessionId, result }) => (
        result.ok ? [[sessionId, result.data] as const] : []
      )));
      setState({
        kind: "ready",
        processes: processes === null ? null : processes.data,
        sessions: sessions.data,
        trees,
        treeMessage: treeResults.some(({ result }) => !result.ok) ? "One or more session hierarchies are unavailable." : null,
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
          <div className="session-list" aria-label="Observed sessions">{state.sessions.items.map((session) => {
            const tree = state.trees[session.session_id];
            return (
              <article className="session-row" key={session.session_id}>
                <div className="session-row-main"><div><strong>{session.identity.provider_key}</strong><p>{session.correlation_state.replaceAll("_", " ")} · account {session.account_id === null ? "unresolved" : "correlated"}</p></div><button type="button" className="quiet-button" onClick={() => { void selectSession(session.session_id); }}>Inspect provenance</button></div>
                {tree !== undefined && <SessionTree tree={tree} />}
              </article>
            );
          })}</div>
          {state.treeMessage !== null && <p role="status">{state.treeMessage}</p>}
          {state.detailMessage !== null && <p role="status">{state.detailMessage}</p>}
          {state.selected !== null && (
            <aside className="session-detail" aria-labelledby="session-detail-title"><div className="panel-heading"><div><p className="panel-code">SESSION DETAIL</p>{displayMode === "page" ? <h2 id="session-detail-title">Observation provenance</h2> : <h3 id="session-detail-title">Observation provenance</h3>}</div><button type="button" className="quiet-button" onClick={() => setState((current) => current.kind === "ready" ? { ...current, selected: null } : current)}>Close</button></div><Provenance item={state.selected.provenance} /></aside>
          )}
        </div>
      )}
      {state.processes !== null && state.processes.items.length > 0 && (
        <div className="table-scroll runtime-processes" tabIndex={0} role="region" aria-label="Process observations table">
          <table><caption>Safe local process metadata with source freshness</caption><thead><tr><th scope="col">Provider</th><th scope="col">Relationships</th><th scope="col">PID</th><th scope="col">Parent PID</th><th scope="col">Start marker</th><th scope="col">CPU</th><th scope="col">RSS memory</th><th scope="col">Threads</th><th scope="col">Kernel state</th><th scope="col">Presence</th><th scope="col">Label</th><th scope="col">Observed / freshness</th></tr></thead><tbody>{state.processes.items.map((process) => (
            <tr key={process.process_id} data-process-row="true" data-process-id={process.process_id}><th scope="row">{process.provider_key ?? "Unresolved"}</th><td>{process.provider_key === "ollama" ? <><span>Account unresolved</span><br /><span>Model unresolved</span></> : "Not reported"}</td><td>{process.identity.pid}</td><td className="process-parent-pid">{integerMetric(process.parent_pid)}</td><td className="process-start">{process.identity.start_time_ticks} ticks after boot · {process.clock_ticks_per_second === null || process.clock_ticks_per_second === undefined ? "clock rate unavailable" : `${process.clock_ticks_per_second} ticks/s`}</td><td className="process-cpu">{cpuMetric(process)}</td><td className="process-memory">{memoryMetric(process)}</td><td className="process-threads">{integerMetric(process.thread_count)}</td><td className="process-kernel-state">{process.kernel_state !== null && process.kernel_state !== undefined && process.kernel_state.state === "present" && process.kernel_state.value !== null ? process.kernel_state.value : unavailableMetric(process.kernel_state)}</td><td className="process-presence">{process.presence}</td><td>{process.executable_label.value ?? unavailableMetric(process.executable_label)}</td><td className="process-freshness"><span>{processFreshness(process)}</span><br /><span>{process.provenance.source_id}</span></td></tr>
          ))}</tbody></table>
        </div>
      )}
    </section>
  );
}
