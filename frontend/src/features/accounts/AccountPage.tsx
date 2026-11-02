import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { CapacityPanel } from "../command/CapacityPanel";
import { SessionPanel } from "../sessions/SessionPanel";
import { AccountWorkspaceSummary } from "./AccountWorkspaceSummary";
import { ProviderConnectionPanel } from "./ClaudeConnectionPanel";
import { OllamaCloudConnectionView } from "./OllamaCloudConnectionView";
import { LiveProviderProcesses } from "./LiveClaudeProcesses";
import { providerDisplayName } from "./providerPresentation";
import {
  CsrfUnavailableError,
  registry,
  type AccountPageV1,
  type AccountViewV1,
  type ClientResult,
  type LiveProcessLocationPageV1,
  type OrganizationPageV1,
} from "../../shared/api/client";

type AccountState =
  | Readonly<{ kind: "loading" }>
  | Readonly<{ kind: "error"; message: string }>
  | Readonly<{
      kind: "ready";
      data: AccountPageV1;
      organizations: OrganizationPageV1;
      selected: AccountViewV1 | null;
    }>;

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
  const [paginationBusy, setPaginationBusy] = useState(false);
  const [paginationMessage, setPaginationMessage] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const settingsRef = useRef<HTMLDetailsElement>(null);
  const [liveProcesses, setLiveProcesses] = useState<LiveProcessLocationPageV1 | null>(null);
  const [observedIdentity, setObservedIdentity] = useState<Readonly<{ accountId: string | undefined; email: string | null }> | null>(null);
  const observedEmail = observedIdentity?.accountId === accountId ? observedIdentity?.email : null;
  const updateObservedIdentity = useCallback((email: string | null) => {
    setObservedIdentity({ accountId, email });
  }, [accountId]);
  const titleId = displayMode === "page" ? "page-title" : "accounts-panel-title";

  const load = useCallback(async (signal?: AbortSignal) => {
    setState((current) => current.kind === "ready" ? current : { kind: "loading" });
    try {
      const [result, organizations, detail] = await Promise.all([
        registry.accounts(signal), registry.organizations(signal),
        accountId === undefined ? null : registry.account(accountId, signal),
      ]);
      if (!result.ok || !organizations.ok || (detail !== null && !detail.ok)) {
        if ((!result.ok && result.problem.code === "dashboard_authentication_required") ||
            (!organizations.ok && organizations.problem.code === "dashboard_authentication_required") ||
            (detail !== null && !detail.ok && detail.problem.code === "dashboard_authentication_required")) onExpired();
        else if (result.ok && organizations.ok && detail !== null && !detail.ok && detail.problem.status === 404) {
          setState({ kind: "ready", data: result.data, organizations: organizations.data, selected: null });
        }
        else setState({ kind: "error", message: "Accounts could not be loaded from the local service." });
        return;
      }
      if (detail !== null && detail.data.account_id !== accountId) {
        setState({ kind: "error", message: "Account details did not match the requested account." });
        return;
      }
      setState({
        kind: "ready",
        data: result.data,
        organizations: organizations.data,
        selected: detail === null ? null : detail.data,
      });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setState({ kind: "error", message: "The local account registry is unavailable." });
    }
  }, [accountId, onExpired]);

  const reloadAccount = useCallback(() => { void load(); }, [load]);

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

  async function loadMoreAccounts(): Promise<void> {
    if (paginationBusy || state.kind !== "ready" || accountId !== undefined) return;
    const cursor = state.data.page.next_cursor;
    if (!state.data.page.has_more || cursor === null || cursor.trim().length === 0) {
      setPaginationMessage("More accounts could not be requested because the service did not provide a continuation.");
      return;
    }
    setPaginationBusy(true);
    setPaginationMessage(null);
    try {
      const result = await registry.accounts(undefined, cursor);
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        else setPaginationMessage("More accounts could not be loaded from the local service.");
        return;
      }
      const existingIds = new Set(state.data.items.map((account) => account.account_id));
      const nextIds = new Set<string>();
      const repeatsAccount = result.data.items.some((account) => {
        if (existingIds.has(account.account_id) || nextIds.has(account.account_id)) return true;
        nextIds.add(account.account_id);
        return false;
      });
      const repeatsCursor = result.data.page.has_more &&
        result.data.page.next_cursor === cursor;
      if (repeatsAccount || repeatsCursor) {
        setPaginationMessage("More accounts could not be loaded because the continuation was inconsistent.");
        return;
      }
      setState((current) => current.kind === "ready" &&
        current.data.page.next_cursor === cursor ? {
          ...current,
          data: {
            ...result.data,
            items: [...current.data.items, ...result.data.items],
          },
        } : current);
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        setPaginationMessage("The local account registry is unavailable.");
      }
    } finally {
      setPaginationBusy(false);
    }
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

  const selected = accountId === undefined ? undefined : state.selected ?? undefined;
  if (accountId !== undefined && selected === undefined) return (
    <section className="telemetry-panel" aria-labelledby={titleId}>
      <p className="panel-code">REGISTRY / ACCOUNT</p><h1 id={titleId} tabIndex={-1}>Account unavailable</h1>
      <p>The requested account was not returned by the authenticated registry query.</p>
    </section>
  );
  const detailAccounts = selected === undefined || state.data.items.some(
    (account) => account.account_id === selected.account_id,
  ) ? state.data.items : [...state.data.items, selected];

  if (selected !== undefined) return (
    <div className="feature-page account-page">
      <header className="account-page-heading" aria-labelledby={titleId}>
        <div>
          <nav className="account-breadcrumb" aria-label="Account breadcrumb"><a href="/accounts">Accounts</a><span aria-hidden="true">/</span><span>{state.organizations.items.find((item) => item.organization_id === selected.organization_id)?.name ?? "Ungrouped"}</span></nav>
          <h1 id={titleId} tabIndex={-1}>{observedEmail ?? selected.friendly_name}</h1>
          {observedEmail && observedEmail !== selected.friendly_name && <p className="connection-warning">Registered as {selected.friendly_name} · {providerDisplayName(selected.provider_key)} currently reports {observedEmail}. Review this connection before treating it as the registered account.</p>}
          <p className="account-subtitle"><span className="provider-name">{selected.provider_key}</span><span aria-hidden="true">·</span><span>{selected.provider_key === "ollama" ? (selected.is_effective_monitoring_enabled ? "Monitoring requested" : "Monitoring is off") : (selected.is_effective_monitoring_enabled ? "Quota monitoring is on" : "Quota monitoring is off")}</span></p>
        </div>
        <button className="quiet-button" type="button" onClick={() => {
          if (settingsRef.current) {
            settingsRef.current.open = true;
            settingsRef.current.querySelector("input")?.focus();
          }
        }}>Edit account</button>
      </header>
      {["claude", "codex"].includes(selected.provider_key) && selected.lifecycle !== "archived" && <ProviderConnectionPanel key={`connection-${selected.account_id}`} account={selected} onExpired={onExpired} onProofUnavailable={onProofUnavailable} onAccountReload={reloadAccount} />}
      {selected.provider_key === "ollama" && selected.lifecycle !== "archived" && <OllamaCloudConnectionView key={`ollama-cloud-${selected.account_id}`} account={selected} onExpired={onExpired} onProofUnavailable={onProofUnavailable} onAccountReload={reloadAccount} />}
      <AccountWorkspaceSummary key={selected.account_id} account={selected} organizationName={state.organizations.items.find((item) => item.organization_id === selected.organization_id)?.name ?? "Ungrouped"} liveProcesses={liveProcesses} onExpired={onExpired} onIdentity={updateObservedIdentity} />
      {["claude", "codex"].includes(selected.provider_key) && <LiveProviderProcesses key={`processes-${selected.account_id}`} account={selected} accounts={detailAccounts} organizations={state.organizations.items} onExpired={onExpired} onProofUnavailable={onProofUnavailable} onRead={setLiveProcesses} />}
      <CapacityPanel accountId={selected.account_id} onExpired={onExpired} />
      <details className="account-secondary" data-account-sessions="true">
        <summary>Session history <span>Previously observed session records</span></summary>
        <SessionPanel accountId={selected.account_id} displayMode="panel" heading="Session records" onExpired={onExpired} />
      </details>
      <details className="account-settings account-secondary" ref={settingsRef}>
        <summary>Account settings <span>Name, organization, and monitoring</span></summary>
      <section className="account-admin-content" aria-labelledby="account-admin-title">
        <div className="panel-heading"><h2 id="account-admin-title">Account administration</h2></div>
        <p className="account-settings-hint">Manage this dashboard record. {providerDisplayName(selected.provider_key)}'s detected account identity is shown above.</p>
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
        <p>The record can be grouped now. Monitoring starts after the account is connected.</p>
        <form onSubmit={create}>
          <label htmlFor="provider-key">Provider</label>
          <input id="provider-key" value={providerKey} onChange={(event) => setProviderKey(event.target.value)} maxLength={64} required autoComplete="off" list="provider-options" placeholder="e.g. ollama" aria-describedby="provider-help" />
          <datalist id="provider-options"><option value="ollama" /><option value="claude" /><option value="codex" /></datalist>
          <small id="provider-help">Enter the provider name, not an API key.</small>
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
            {["claude", "codex"].includes(account.provider_key) && account.lifecycle === "pending" && <button type="button" onClick={() => onOpenAccount(account.account_id)}>Connect {providerDisplayName(account.provider_key)}</button>}
            <button type="button" className="quiet-button" onClick={() => onOpenAccount(account.account_id)}>Open account</button>
          </article>
        ))}</div>
      )}
      {state.data.page.has_more && state.data.page.next_cursor !== null && (
        <div className="pagination-note">
          <button type="button" className="quiet-button" disabled={paginationBusy} onClick={() => { void loadMoreAccounts(); }}>
            {paginationBusy ? "Loading more accounts…" : "Load more accounts"}
          </button>
        </div>
      )}
      {state.data.page.has_more && state.data.page.next_cursor === null && (
        <p className="pagination-note" role="alert">More accounts are reported, but the service did not provide a continuation.</p>
      )}
      {paginationMessage && <p className="pagination-note" role="status">{paginationMessage}</p>}
    </section>
  );
}
