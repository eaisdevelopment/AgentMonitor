import { useCallback, useEffect, useRef, useState } from "react";

import { ollamaReadingFreshness } from "./ollamaFreshness";
import { ollamaStatusMessage } from "./ollamaStatus";

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

type CatalogResult = Awaited<ReturnType<typeof providers.ollamaLocalCatalog>>;
type Catalog = Extract<CatalogResult, { ok: true }>["data"];
type CatalogState =
  | Readonly<{ kind: "loading" }>
  | Readonly<{ kind: "error" }>
  | Readonly<{ kind: "ready"; catalog: Catalog }>;

function OllamaLocalCatalog({ onExpired }: Readonly<{ onExpired: () => void }>) {
  const [state, setState] = useState<CatalogState>({ kind: "loading" });
  const [nowMs, setNowMs] = useState(() => Date.now());
  const activeRead = useRef<AbortController | null>(null);
  const onExpiredRef = useRef(onExpired);
  onExpiredRef.current = onExpired;
  const load = useCallback(async () => {
    if (activeRead.current !== null) return;
    const controller = new AbortController();
    activeRead.current = controller;
    let timedOut = false;
    const timeout = window.setTimeout(() => { timedOut = true; controller.abort(); }, 15_000);
    setState({ kind: "loading" });
    try {
      const result = await providers.ollamaLocalCatalog(controller.signal);
      if (controller.signal.aborted) {
        if (timedOut) setState({ kind: "error" });
        return;
      }
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpiredRef.current();
        else setState({ kind: "error" });
        return;
      }
      setNowMs(Date.now());
      setState({ kind: "ready", catalog: result.data });
    } catch (error) {
      if (controller.signal.aborted && !timedOut) return;
      setState({ kind: "error" });
    } finally {
      window.clearTimeout(timeout);
      if (activeRead.current === controller) activeRead.current = null;
    }
  }, []);
  useEffect(() => {
    void load();
    const refresh = () => {
      setNowMs(Date.now());
      if (!document.hidden) void load();
    };
    const interval = window.setInterval(refresh, 30_000);
    const visibilityChanged = () => { if (!document.hidden) refresh(); };
    document.addEventListener("visibilitychange", visibilityChanged);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", visibilityChanged);
      const controller = activeRead.current;
      activeRead.current = null;
      controller?.abort();
    };
  }, [load]);

  return <section className="ollama-catalog provider-card" aria-label="Ollama local models">
    <div className="record-card-heading">
      <h3>Ollama local models</h3>
      <button type="button" className="quiet-button" disabled={state.kind === "loading"} onClick={() => { void load(); }}>Refresh Ollama</button>
    </div>
    <p className="record-meta">Models reported by the local Ollama service. Other apps may use a different service.</p>
    {state.kind === "loading" ? <p role="status">Reading local Ollama…</p> : state.kind === "error" ? (
      <p role="status">Local Ollama information is unavailable.</p>
    ) : <>
      <p className="record-meta">{state.catalog.daemon_version ? `Service version ${state.catalog.daemon_version} · ` : "Service version unavailable · "}
        Observed {new Date(state.catalog.observed_at).toLocaleString()} · {state.catalog.source}</p>
      {state.catalog.outcome !== "success" && <p role="status">{ollamaStatusMessage(state.catalog.outcome, state.catalog.installed_reason, state.catalog.loaded_reason)}</p>}
      <div className="ollama-model-lists">
        <section aria-label="Installed models"><h4>Installed models</h4>
          {state.catalog.installed_observed_at && <p className="record-meta">Read {new Date(state.catalog.installed_observed_at).toLocaleString()} · {ollamaReadingFreshness(state.catalog.installed_observed_at, nowMs)}</p>}
          {!(state.catalog.outcome === "success" || state.catalog.outcome === "partial") || state.catalog.installed_state !== "available" || state.catalog.installed === null ? <p>Installed models unavailable</p> : state.catalog.installed.length === 0 ? <p>No installed models</p> :
            <ul>{state.catalog.installed.map(model => <li key={model.name}>{model.name}</li>)}</ul>}
        </section>
        <section aria-label="Loaded models"><h4>Loaded models</h4>
          {state.catalog.loaded_observed_at && <p className="record-meta">Read {new Date(state.catalog.loaded_observed_at).toLocaleString()} · {ollamaReadingFreshness(state.catalog.loaded_observed_at, nowMs)}</p>}
          {!(state.catalog.outcome === "success" || state.catalog.outcome === "partial") || state.catalog.loaded_state !== "available" || state.catalog.loaded === null ? <p>Loaded models unavailable</p> : state.catalog.loaded.length === 0 ? <p>No loaded models</p> :
            <ul>{state.catalog.loaded.map(model => <li key={model.name}>{model.name}</li>)}</ul>}
        </section>
      </div>
      <p className="record-meta">Loaded means held in memory; activity and account use are not established.</p>
    </>}
  </section>;
}

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

  return (
    <section className="telemetry-panel" aria-labelledby={titleId} aria-busy={state.kind === "loading"}>
      {state.kind === "loading" ? <>
      <div className="panel-heading"><div><p className="panel-code">PROVIDERS</p><Heading id={titleId} tabIndex={displayMode === "page" ? -1 : undefined}>Providers</Heading></div></div>
      <p className="skeleton-copy" role="status">Reading provider installations…</p>
      </> : state.kind === "error" ? <>
      <div className="panel-heading"><div><p className="panel-code">PROVIDERS</p><Heading id={titleId} tabIndex={displayMode === "page" ? -1 : undefined}>Providers</Heading></div><span className="state-chip state-warning">Unavailable</span></div>
      <p role="alert">{state.message}</p><button type="button" className="quiet-button" onClick={() => { void load(); }}>Retry providers</button>
      </> : <>
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
      </>}
      <OllamaLocalCatalog onExpired={onExpired} />
    </section>
  );
}
