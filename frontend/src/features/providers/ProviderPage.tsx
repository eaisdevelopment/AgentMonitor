import { useCallback, useEffect, useState } from "react";

import {
  providers,
  registry,
  type ProviderCapabilityDeclarationPageV1,
  type ProviderInstallationPageV1,
} from "../../shared/api/client";

type ProviderState =
  | Readonly<{ kind: "loading" }>
  | Readonly<{ kind: "error"; message: string }>
  | Readonly<{
      kind: "ready";
      installations: ProviderInstallationPageV1;
      capabilities: ReadonlyMap<string, ProviderCapabilityDeclarationPageV1 | null>;
    }>;

export function ProviderPage({
  displayMode = "page",
  onExpired,
}: Readonly<{ displayMode?: "page" | "panel"; onExpired: () => void }>) {
  const [state, setState] = useState<ProviderState>({ kind: "loading" });
  const titleId = displayMode === "page" ? "page-title" : "providers-panel-title";
  const Heading = displayMode === "page" ? "h1" : "h2";
  const InstallationHeading = displayMode === "page" ? "h2" : "h3";

  const load = useCallback(async (signal?: AbortSignal) => {
    setState({ kind: "loading" });
    try {
      const installations = await registry.providerInstallations(signal);
      if (!installations.ok) {
        if (installations.problem.code === "dashboard_authentication_required") onExpired();
        else setState({ kind: "error", message: "Provider installations could not be loaded." });
        return;
      }
      const providerKeys = [...new Set(installations.data.items.map((item) => item.provider_key))];
      const entries = await Promise.all(providerKeys.map(async (providerKey) => {
        const result = await providers.capabilities(providerKey, signal);
        if (!result.ok && result.problem.code === "dashboard_authentication_required") onExpired();
        return [providerKey, result.ok ? result.data : null] as const;
      }));
      setState({ kind: "ready", installations: installations.data, capabilities: new Map(entries) });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setState({ kind: "error", message: "The local provider registry is unavailable." });
    }
  }, [onExpired]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  if (state.kind === "loading") return (
    <section className="telemetry-panel" aria-labelledby={titleId} aria-busy="true">
      <div className="panel-heading"><div><p className="panel-code">PROVIDERS</p><Heading id={titleId} tabIndex={displayMode === "page" ? -1 : undefined}>Providers</Heading></div></div>
      <p className="skeleton-copy" role="status">Reading provider installations…</p>
    </section>
  );
  if (state.kind === "error") return (
    <section className="telemetry-panel" aria-labelledby={titleId}>
      <div className="panel-heading"><div><p className="panel-code">PROVIDERS</p><Heading id={titleId} tabIndex={displayMode === "page" ? -1 : undefined}>Providers</Heading></div><span className="state-chip state-warning">Unavailable</span></div>
      <p role="alert">{state.message}</p><button type="button" className="quiet-button" onClick={() => { void load(); }}>Retry providers</button>
    </section>
  );

  return (
    <section className="telemetry-panel" aria-labelledby={titleId}>
      <div className="panel-heading">
        <div><p className="panel-code">PROVIDERS / INSTALLATIONS</p><Heading id={titleId} tabIndex={displayMode === "page" ? -1 : undefined}>Providers</Heading></div>
        <span className={`state-chip state-${state.installations.availability.state}`}>{state.installations.availability.state}</span>
      </div>
      <p className="provenance-line">{state.installations.availability.reason_code.replaceAll("_", " ")} · as of {new Date(state.installations.availability.as_of).toLocaleString()}</p>
      {state.installations.items.length === 0 && state.installations.availability.state === "available" ? (
        <div className="empty-telemetry"><div><strong>No provider installations were discovered.</strong><p>Only real discovered installations are shown.</p></div></div>
      ) : state.installations.items.length === 0 ? (
        <div className="empty-telemetry"><div><strong>Provider discovery {state.installations.availability.state}.</strong><p>{state.installations.availability.reason_code.replaceAll("_", " ")}.</p></div></div>
      ) : (
        <div className="provider-stack">{state.installations.items.map((installation) => {
          const capability = state.capabilities.get(installation.provider_key);
          return (
            <article className="provider-card" key={installation.provider_installation_id}>
              <div className="record-card-heading"><div><span className={`provider-light ${installation.presence_state === "present" ? "active" : ""}`} aria-hidden="true" /><InstallationHeading>{installation.provider_key}</InstallationHeading></div><span className={`state-chip state-${installation.presence_state}`}>{installation.presence_state}</span></div>
              <p>{installation.platform_key} · version {installation.version.masked_value ?? installation.version.state.replaceAll("_", " ")}</p>
              <p className="record-meta">Last seen {new Date(installation.last_seen_at).toLocaleString()}</p>
              {capability === undefined ? <p>Reading capability manifest…</p> : capability === null ? (
                <p role="status">Capability manifest unavailable.</p>
              ) : (
                <div className="capability-grid" aria-label={`${installation.provider_key} capabilities`}>
                  {capability.items.map((item) => (
                    <div key={item.capability_id}>
                      <span>{item.capability_id}</span>
                      <strong className={`state-chip state-${item.support_state}`}>{item.support_state}</strong>
                      <small>{item.stability.replaceAll("_", " ")} · {item.side_effect_class.replaceAll("_", " ")}</small>
                    </div>
                  ))}
                </div>
              )}
            </article>
          );
        })}</div>
      )}
      {state.installations.page.has_more && <p className="pagination-note" role="status">More provider installations are available beyond this page.</p>}
    </section>
  );
}
