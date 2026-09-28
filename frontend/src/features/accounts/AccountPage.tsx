import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { CapacityPanel } from "../command/CapacityPanel";
import { SessionPanel } from "../sessions/SessionPanel";
import { AccountWorkspaceSummary } from "./AccountWorkspaceSummary";
import { LiveClaudeProcesses } from "./LiveClaudeProcesses";
import {
  CsrfUnavailableError,
  registry,
  type AccountPageV1,
  type AccountViewV1,
  type ClientResult,
  type OrganizationPageV1,
} from "../../shared/api/client";

type AccountState =
  | Readonly<{ kind: "loading" }>
  | Readonly<{ kind: "error"; message: string }>
  | Readonly<{ kind: "ready"; data: AccountPageV1; organizations: OrganizationPageV1 }>;

export function AccountPage({
  accountId,
  displayMode = "page",
  onExpired,
  onOpenAccount,
  onProofUnavailable,
}: Readonly<{
  accountId?: string;
  displayMode?: "page" | "panel";
  onExpired: () => void;
  onOpenAccount: (accountId: string) => void;
  onProofUnavailable: () => void;
}>) {
  const [state, setState] = useState<AccountState>({ kind: "loading" });
  const [providerKey, setProviderKey] = useState("");
  const [accountName, setAccountName] = useState("");
  const [organizationId, setOrganizationId] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const settingsRef = useRef<HTMLDetailsElement>(null);
  const [observedIdentity, setObservedIdentity] = useState<Readonly<{ accountId: string | undefined; email: string | null }> | null>(null);
  const observedEmail = observedIdentity?.accountId === accountId ? observedIdentity?.email : null;
  const updateObservedIdentity = useCallback((email: string | null) => {
    setObservedIdentity({ accountId, email });
  }, [accountId]);
  const titleId = displayMode === "page" ? "page-title" : "accounts-panel-title";

  const load = useCallback(async (signal?: AbortSignal) => {
    setState((current) => current.kind === "ready" ? current : { kind: "loading" });
    try {
      const [result, organizations] = await Promise.all([
        registry.accounts(signal), registry.organizations(signal),
      ]);
      if (!result.ok || !organizations.ok) {
        if ((!result.ok && result.problem.code === "dashboard_authentication_required") ||
            (!organizations.ok && organizations.problem.code === "dashboard_authentication_required")) onExpired();
        else setState({ kind: "error", message: "Accounts could not be loaded from the local service." });
        return;
      }
      setState({ kind: "ready", data: result.data, organizations: organizations.data });
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

  async function mutate(
    operation: () => Promise<ClientResult<AccountViewV1>>,
    successMessage: string,
  ): Promise<boolean> {
    if (busy) return false;
    setBusy(true);
    setMessage(null);
    try {
      const result = await operation();
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        else if (result.problem.code === "csrf_validation_failed") onProofUnavailable();
        else if (result.problem.status === 412) {
          setMessage("The account changed. Refresh its current version and try again.");
          await load();
        } else if (result.problem.code === "registry_monitoring_not_eligible") {
          setMessage("Monitoring requires a confirmed identity, compatible profile, and active resource.");
        } else setMessage("The account change was rejected. Check the values and try again.");
        return false;
      }
      await load();
      setMessage(successMessage);
      return true;
    } catch (error) {
      if (error instanceof CsrfUnavailableError) onProofUnavailable();
      else setMessage("The local service is unavailable. Try again.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!providerKey.trim() || !accountName.trim()) return;
    void mutate(
      () => registry.registerAccount(
        providerKey.trim(), accountName.trim(), organizationId || null,
      ),
      "Pending account added. Monitoring remains disabled until identity is confirmed.",
    ).then((created) => {
      if (created) setAccountName("");
    });
  }

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
    <div className="feature-page account-page">
      <header className="account-page-heading" aria-labelledby={titleId}>
        <div>
          <nav className="account-breadcrumb" aria-label="Account breadcrumb"><a href="/accounts">Accounts</a><span aria-hidden="true">/</span><span>{state.organizations.items.find((item) => item.organization_id === selected.organization_id)?.name ?? "Ungrouped"}</span></nav>
          <h1 id={titleId} tabIndex={-1}>{observedEmail ?? (selected.lifecycle === "pending" ? selected.friendly_name : `Connected ${selected.provider_key === "claude" ? "Claude" : selected.provider_key} profile`)}</h1>
          <p className="account-subtitle"><span className="provider-name">{selected.provider_key}</span><span aria-hidden="true">·</span><span>{selected.is_effective_monitoring_enabled ? "Quota monitoring is on" : "Quota monitoring is off"}</span></p>
        </div>
        <button className="quiet-button" type="button" onClick={() => {
          if (settingsRef.current) {
            settingsRef.current.open = true;
            settingsRef.current.querySelector("input")?.focus();
          }
        }}>Edit account</button>
      </header>
      <AccountWorkspaceSummary key={selected.account_id} account={selected} organizationName={state.organizations.items.find((item) => item.organization_id === selected.organization_id)?.name ?? "Ungrouped"} onExpired={onExpired} onIdentity={updateObservedIdentity} />
      {selected.provider_key === "claude" && <LiveClaudeProcesses onExpired={onExpired} />}
      <CapacityPanel accountId={selected.account_id} onExpired={onExpired} />
      <details className="account-secondary" data-account-sessions="true">
        <summary>Session details <span>Observed agents and their history</span></summary>
        <SessionPanel accountId={selected.account_id} displayMode="panel" heading="Running sessions" onExpired={onExpired} />
      </details>
      <details className="account-settings account-secondary" ref={settingsRef}>
        <summary>Account settings <span>Name, organization, and monitoring</span></summary>
      <section className="account-admin-content" aria-labelledby="account-admin-title">
        <div className="panel-heading"><h2 id="account-admin-title">Account administration</h2></div>
        <p className="account-settings-hint">Manage this dashboard record. Claude's detected account identity is shown above.</p>
        <p>Identity is {selected.identity_state.replaceAll("_", " ")}. Editing this record does not confirm provider identity.</p>
        <form key={`name-${selected.record_version}`} onSubmit={(event) => {
          event.preventDefault();
          const value = new FormData(event.currentTarget).get("friendly_name");
          if (typeof value === "string") void mutate(() => registry.renameAccount(selected, value.trim()), "Account name saved.");
        }}>
          <label htmlFor="rename-account">Rename account</label>
          <input id="rename-account" name="friendly_name" defaultValue={selected.friendly_name} maxLength={256} required />
          <button type="submit" disabled={busy}>Save account name</button>
        </form>
        <form key={`org-${selected.record_version}`} onSubmit={(event) => {
          event.preventDefault();
          const value = new FormData(event.currentTarget).get("organization_id");
          if (typeof value === "string") void mutate(() => registry.assignAccount(selected, value || null), "Account organization saved.");
        }}>
          <label htmlFor="assign-account-organization">Organization</label>
          <select id="assign-account-organization" name="organization_id" defaultValue={selected.organization_id ?? ""} disabled={selected.lifecycle === "archived"}>
            <option value="">Ungrouped</option>
            {state.organizations.items.filter((item) => item.lifecycle === "active").map((item) => (
              <option key={item.organization_id} value={item.organization_id}>{item.name}</option>
            ))}
          </select>
          <button type="submit" disabled={busy || selected.lifecycle === "archived"}>Save organization</button>
        </form>
        <div className="account-settings-actions">
        {selected.lifecycle === "archived" ? (
          <button type="button" className="quiet-button" disabled={busy} onClick={() => { void mutate(() => registry.restoreAccount(selected), "Account restored with monitoring disabled."); }}>Restore account</button>
        ) : (
          <button type="button" className="quiet-button" disabled={busy} onClick={() => { void mutate(() => registry.archiveAccount(selected), "Account archived."); }}>Archive account</button>
        )}
        {selected.lifecycle === "active" && ["owner_confirmed", "matched"].includes(selected.identity_state) && (
          <button type="button" disabled={busy} onClick={() => {
            const next = selected.monitoring_preference === "enabled" ? "disabled" : "enabled";
            void mutate(() => registry.setAccountMonitoring(selected, next), `Monitoring preference ${next}.`);
          }}>
            {selected.monitoring_preference === "enabled" ? "Disable monitoring" : "Enable monitoring"}
          </button>
        )}
        </div>
        {message && <p role="status">{message}</p>}
      </section>
      <section className="identity-panel account-identity-details" aria-labelledby="identity-title">
        <div className="panel-heading"><div><p className="panel-code">IDENTITY</p><h2 id="identity-title">Account identity</h2></div><span className="state-chip state-unavailable">{selected.masked_identity.state.replaceAll("_", " ")}</span></div>
        <dl className="telemetry-readouts">
          <div><dt>Provider</dt><dd>{selected.provider_key}</dd></div>
          <div><dt>Organization</dt><dd>{state.organizations.items.find((item) => item.organization_id === selected.organization_id)?.name ?? "Ungrouped"}</dd></div>
          <div><dt>Identity</dt><dd>{selected.masked_identity.state === "withheld" ? "Withheld from dashboard" : selected.masked_identity.masked_value ?? selected.masked_identity.reason_code.replaceAll("_", " ")}</dd></div>
          <div><dt>Registry updated</dt><dd>{new Date(selected.updated_at).toLocaleString()}</dd></div>
        </dl>
        {selected.masked_identity.state === "withheld" && <p>Account names and organization assignments are administrator managed.</p>}
      </section>
      </details>
    </div>
  );

  return (
    <section className="telemetry-panel" aria-labelledby={titleId}>
      <div className="panel-heading">
        <div><p className="panel-code">REGISTRY / ACCOUNTS</p><Heading id={titleId} tabIndex={displayMode === "page" ? -1 : undefined}>Accounts</Heading></div>
        <span className={`state-chip state-${state.data.availability.state}`}>{state.data.availability.state}</span>
      </div>
      <p className="provenance-line">{state.data.availability.reason_code.replaceAll("_", " ")} · as of {new Date(state.data.availability.as_of).toLocaleString()}</p>
      {displayMode === "page" && <section aria-labelledby="add-account-title">
        <h2 id="add-account-title">Add pending account</h2>
        <p>The record can be grouped now. Monitoring stays disabled until provider identity is confirmed.</p>
        <form onSubmit={create}>
          <label htmlFor="provider-key">Provider key</label>
          <input id="provider-key" value={providerKey} onChange={(event) => setProviderKey(event.target.value)} maxLength={64} required autoComplete="off" />
          <label htmlFor="account-name">Account name</label>
          <input id="account-name" value={accountName} onChange={(event) => setAccountName(event.target.value)} maxLength={256} required autoComplete="off" />
          <label htmlFor="account-organization">Organization</label>
          <select id="account-organization" value={organizationId} onChange={(event) => setOrganizationId(event.target.value)}>
            <option value="">Ungrouped</option>
            {state.organizations.items.filter((item) => item.lifecycle === "active").map((item) => (
              <option key={item.organization_id} value={item.organization_id}>{item.name}</option>
            ))}
          </select>
          <button type="submit" disabled={busy || !providerKey.trim() || !accountName.trim()}>Add account</button>
        </form>
      </section>}
      {message && <p role="status">{message}</p>}
      {state.data.items.length === 0 && state.data.availability.state === "available" ? (
        <div className="empty-telemetry"><div><strong>No accounts are registered.</strong><p>Add an account record to organize it while identity is pending.</p></div></div>
      ) : state.data.items.length === 0 ? (
        <div className="empty-telemetry"><div><strong>Account registry {state.data.availability.state}.</strong><p>{state.data.availability.reason_code.replaceAll("_", " ")}.</p></div></div>
      ) : (
        <div className="record-grid">{state.data.items.map((account) => (
          <article className="record-card" key={account.account_id}>
            <div><span className={`provider-light ${account.is_effective_monitoring_enabled ? "active" : ""}`} aria-hidden="true" /><strong>{account.friendly_name}</strong></div>
            <p>{account.provider_key} · {state.organizations.items.find((item) => item.organization_id === account.organization_id)?.name ?? "Ungrouped"}</p>
            <p className="record-meta">{account.lifecycle} · monitoring {account.is_effective_monitoring_enabled ? "enabled" : "disabled"}</p>
            <button type="button" className="quiet-button" onClick={() => onOpenAccount(account.account_id)}>Open account</button>
          </article>
        ))}</div>
      )}
      {state.data.page.has_more && <p className="pagination-note" role="status">More accounts are available beyond this page.</p>}
    </section>
  );
}
