import { useCallback, useEffect, useState } from "react";

import { apiClient, type OperationsDiagnosticsWireV1 } from "../../generated/api";

const componentNames: Readonly<Record<string, string>> = {
  foundation: "Service", configuration: "Configuration", database: "Database",
  identity_access: "Dashboard sign-in", registry: "Account registry",
  provider_system: "Provider connections", collection_control: "Quota collector",
  capacity: "Capacity", runtime_observation: "Agent activity", alerting: "Alerts",
  "provider.claude": "Claude",
};

function label(value: string): string {
  return value.replaceAll("_", " ");
}

function reason(code: string): string {
  const known: Readonly<Record<string, string>> = {
    operations_component_healthy: "Responding", operations_component_degraded: "Needs attention",
    operations_component_unavailable: "No health reading", operations_component_timeout: "Health check timed out",
    operations_component_incompatible: "Version incompatible", operations_setup_required: "Sign-in setup required",
    operations_schema_incompatible: "Database upgrade required", operations_database_locked: "Database busy",
    operations_database_unavailable: "Database unavailable", operations_component_stale: "Reading is stale",
    operations_required_component_missing: "Required health check unavailable",
    operations_readiness_unknown: "Readiness could not be confirmed",
  };
  return known[code] ?? label(code.replace(/^operations_/, ""));
}

type PageState =
  | Readonly<{ kind: "loading" }>
  | Readonly<{ kind: "error" }>
  | Readonly<{ kind: "ready"; data: OperationsDiagnosticsWireV1 }>;

export function OperationsPage({ onExpired }: Readonly<{ onExpired: () => void }>) {
  const [state, setState] = useState<PageState>({ kind: "loading" });
  const load = useCallback(async (signal?: AbortSignal) => {
    try {
      const result = await apiClient.operations_get_diagnostics_v1({ signal });
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        else setState({ kind: "error" });
        return;
      }
      setState({ kind: "ready", data: result.data });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setState({ kind: "error" });
    }
  }, [onExpired]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const data = state.kind === "ready" ? state.data : null;
  const versions = data === null ? [] : [
    ["Application", data.versions.application_version], ["Database", data.versions.schema_version],
    ["API", data.versions.api_version], ["OpenAPI", data.versions.openapi_version],
    ["Generated client", data.versions.client_version], ["Dashboard", data.versions.frontend_version],
  ] as const;

  return (
    <section className="telemetry-panel" aria-labelledby="page-title" aria-busy={state.kind === "loading"}>
      <div className="panel-heading">
        <h1 id="page-title" tabIndex={-1}>Operations</h1>
        <button className="quiet-button" type="button" onClick={() => { void load(); }}>Refresh status</button>
      </div>
      {state.kind === "loading" && <p role="status">Checking service health…</p>}
      {state.kind === "error" && <p role="alert">Service diagnostics could not be loaded. Refresh to check again.</p>}
      {data !== null && <>
        <div className="operations-summary" aria-label="Service status">
          <span>Service <strong className={`state-chip state-${data.health.state}`}>{label(data.health.state)}</strong></span>
          <span>Readiness <strong className={`state-chip state-${data.readiness.state}`}>{label(data.readiness.state)}</strong></span>
          <span>Checks <strong>{data.health.components.filter((item) => item.outcome === "available").length}/{data.health.components.length}</strong></span>
          <span>Updated <time dateTime={data.generated_at}>{new Date(data.generated_at).toLocaleTimeString()}</time></span>
        </div>
        {data.readiness.blocker_component_keys.length > 0 && <p role="status">
          Needs attention: {data.readiness.blocker_component_keys.map((key) => componentNames[key] ?? key).join(", ")}.
        </p>}
        <div className="operations-table-scroll">
          <table className="operations-table" aria-label="Component health">
            <thead><tr><th scope="col">Component</th><th scope="col">State</th><th scope="col">Details</th><th scope="col">Checked</th></tr></thead>
            <tbody>{data.health.components.map((item) => <tr key={item.component_key}>
              <th scope="row">{componentNames[item.component_key] ?? item.component_key}</th>
              <td><span className={`state-chip state-${item.sample?.state ?? item.outcome}`}>{label(item.sample?.state ?? item.outcome)}</span></td>
              <td>{(item.sample?.reason_codes ?? [item.reason_code]).map(reason).join(" · ")}
                {item.sample?.indicators.map((indicator) => <small key={indicator.key} className="operations-indicator">
                  {label(indicator.key.replace(/_count$/, ""))}: {indicator.value ?? "Not reported"}
                </small>)}
              </td>
              <td><time dateTime={item.checked_at}>{new Date(item.checked_at).toLocaleTimeString()}</time></td>
            </tr>)}</tbody>
          </table>
        </div>
        <details className="operations-details">
          <summary>Versions and configuration</summary>
          <dl className="operations-versions">{versions.map(([name, version]) => <div key={name}>
            <dt>{name}</dt><dd>{version.value ?? `Not reported (${label(version.availability)})`}</dd>
          </div>)}</dl>
          {data.configuration_presence.length > 0 && <ul>{data.configuration_presence.map((item) => <li key={item.key}>
            {item.key}: {label(item.presence)}
          </li>)}</ul>}
          <p className="record-meta">{data.availability.state === "available" ? "All diagnostics reported." : "Some diagnostics are unavailable."}</p>
        </details>
      </>}
    </section>
  );
}
