import { useCallback, useEffect, useState } from "react";

import { CapacityPanel } from "../command/CapacityPanel";
import { SessionPanel } from "../sessions/SessionPanel";
import { registry, type AccountPageV1 } from "../../shared/api/client";

type AccountState =
  | Readonly<{ kind: "loading" }>
  | Readonly<{ kind: "error"; message: string }>
  | Readonly<{ kind: "ready"; data: AccountPageV1 }>;

export function AccountPage({
  accountId,
  displayMode = "page",
  onExpired,
  onOpenAccount,
}: Readonly<{
  accountId?: string;
  displayMode?: "page" | "panel";
  onExpired: () => void;
  onOpenAccount: (accountId: string) => void;
}>) {
  const [state, setState] = useState<AccountState>({ kind: "loading" });
  const titleId = displayMode === "page" ? "page-title" : "accounts-panel-title";

  const load = useCallback(async (signal?: AbortSignal) => {
    setState({ kind: "loading" });
    try {
      const result = await registry.accounts(signal);
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        else setState({ kind: "error", message: "Accounts could not be loaded from the local service." });
        return;
      }
      setState({ kind: "ready", data: result.data });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setState({ kind: "error", message: "The local account registry is unavailable." });
    }
  }, [onExpired]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const Heading = displayMode === "page" ? "h1" : "h2";
  if (state.kind === "loading") return (
    <section className="telemetry-panel" aria-labelledby={titleId} aria-busy="true">
      <div className="panel-heading"><div><p className="panel-code">REGISTRY / ACCOUNTS</p><Heading id={titleId} tabIndex={displayMode === "page" ? -1 : undefined}>Accounts</Heading></div></div>
      <p className="skeleton-copy" role="status">Reading monitored accounts…</p>
    </section>
  );
  if (state.kind === "error") return (
    <section className="telemetry-panel" aria-labelledby={titleId}>
      <div className="panel-heading"><div><p className="panel-code">REGISTRY / ACCOUNTS</p><Heading id={titleId} tabIndex={displayMode === "page" ? -1 : undefined}>Accounts</Heading></div><span className="state-chip state-warning">Unavailable</span></div>
      <p role="alert">{state.message}</p><button type="button" className="quiet-button" onClick={() => { void load(); }}>Retry accounts</button>
    </section>
  );

  const selected = accountId === undefined ? undefined : state.data.items.find((account) => account.account_id === accountId);
  if (accountId !== undefined && selected === undefined) return (
    <section className="telemetry-panel" aria-labelledby={titleId}>
      <p className="panel-code">REGISTRY / ACCOUNT</p><h1 id={titleId} tabIndex={-1}>Account unavailable</h1>
      <p>The requested account was not returned by the authenticated registry query.</p>
    </section>
  );

  if (selected !== undefined) return (
    <div className="feature-page">
      <section className="command-deck" aria-labelledby={titleId}>
        <div><p className="eyebrow">{selected.provider_key} · monitored account</p><h1 id={titleId} tabIndex={-1}>{selected.friendly_name}</h1><p className="console-summary">Identity {selected.identity_state.replaceAll("_", " ")} · monitoring {selected.is_effective_monitoring_enabled ? "enabled" : "disabled"}</p></div>
        <span className={`state-chip state-${selected.lifecycle}`}>{selected.lifecycle}</span>
      </section>
      <section className="telemetry-panel identity-panel" aria-labelledby="identity-title">
        <div className="panel-heading"><div><p className="panel-code">IDENTITY</p><h2 id="identity-title">Account identity</h2></div><span className="state-chip state-unavailable">{selected.masked_identity.state.replaceAll("_", " ")}</span></div>
        <dl className="telemetry-readouts">
          <div><dt>Provider</dt><dd>{selected.provider_key}</dd></div>
          <div><dt>Organization</dt><dd>{selected.organization_id ?? "Ungrouped"}</dd></div>
          <div><dt>Identity</dt><dd>{selected.masked_identity.masked_value ?? selected.masked_identity.reason_code.replaceAll("_", " ")}</dd></div>
          <div><dt>Registry updated</dt><dd>{new Date(selected.updated_at).toLocaleString()}</dd></div>
        </dl>
      </section>
      <div className="account-observation-grid">
        <CapacityPanel accountId={selected.account_id} onExpired={onExpired} />
        <SessionPanel accountId={selected.account_id} displayMode="panel" heading="Running sessions" onExpired={onExpired} />
      </div>
    </div>
  );

  return (
    <section className="telemetry-panel" aria-labelledby={titleId}>
      <div className="panel-heading">
        <div><p className="panel-code">REGISTRY / ACCOUNTS</p><Heading id={titleId} tabIndex={displayMode === "page" ? -1 : undefined}>Accounts</Heading></div>
        <span className={`state-chip state-${state.data.availability.state}`}>{state.data.availability.state}</span>
      </div>
      <p className="provenance-line">{state.data.availability.reason_code.replaceAll("_", " ")} · as of {new Date(state.data.availability.as_of).toLocaleString()}</p>
      {state.data.items.length === 0 && state.data.availability.state === "available" ? (
        <div className="empty-telemetry"><div><strong>No monitored accounts are registered.</strong><p>Accounts will appear only after real registry enrollment.</p></div></div>
      ) : state.data.items.length === 0 ? (
        <div className="empty-telemetry"><div><strong>Account registry {state.data.availability.state}.</strong><p>{state.data.availability.reason_code.replaceAll("_", " ")}.</p></div></div>
      ) : (
        <div className="record-grid">{state.data.items.map((account) => (
          <article className="record-card" key={account.account_id}>
            <div><span className={`provider-light ${account.is_effective_monitoring_enabled ? "active" : ""}`} aria-hidden="true" /><strong>{account.friendly_name}</strong></div>
            <p>{account.provider_key} · {account.organization_id ?? "Ungrouped"}</p>
            <p className="record-meta">{account.identity_state.replaceAll("_", " ")} · {account.lifecycle}</p>
            <button type="button" className="quiet-button" onClick={() => onOpenAccount(account.account_id)}>Open account</button>
          </article>
        ))}</div>
      )}
      {state.data.page.has_more && <p className="pagination-note" role="status">More accounts are available beyond this page.</p>}
    </section>
  );
}
