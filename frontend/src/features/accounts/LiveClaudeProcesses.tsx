import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
  CsrfUnavailableError, runtime,
  type AccountViewV1, type OrganizationViewV1,
  type LiveProcessLocationPageV1, type LiveProcessLocationViewV1,
} from "../../shared/api/client";
import { providerDisplayName } from "./providerPresentation";

function time(value: string) {
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function ProcessDetails({ item }: Readonly<{ item: LiveProcessLocationViewV1 }>) {
  return <details className="agent-details">
    <summary>Details</summary>
    <dl>
      <div><dt>PID</dt><dd>{item.pid}</dd></div>
      <div><dt>Parent PID</dt><dd>{item.parent_pid ?? "Unavailable"}</dd></div>
      <div><dt>Start identity</dt><dd>{item.start_time_ticks} ticks</dd></div>
      <div><dt>{providerDisplayName(item.provider_key)} version</dt><dd>{item.provider_version ?? "Unavailable"}</dd></div>
      <div><dt>Memory</dt><dd>{item.resident_memory_bytes == null ? "Unavailable" : (item.resident_memory_bytes / 1048576).toFixed(1) + " MiB"}</dd></div>
      <div><dt>CPU time</dt><dd>{item.cpu_time_seconds == null ? "Unavailable" : item.cpu_time_seconds + " seconds · cumulative"}</dd></div>
      <div><dt>OS state</dt><dd>{item.kernel_state ?? "Unavailable"}</dd></div>
      <div><dt>Observed</dt><dd>{time(item.observed_at)}</dd></div>
      {item.account_association && <div><dt>Account confirmed</dt><dd>{new Date(item.account_association.confirmed_at).toLocaleString()}</dd></div>}
    </dl>
    <p>Session, model and tokens: Not reported for this process.</p>
  </details>;
}

export function LiveProviderProcesses({
  account, accounts, organizations, onExpired, onProofUnavailable, onRead,
}: Readonly<{
  account: AccountViewV1;
  accounts: readonly AccountViewV1[];
  organizations: readonly OrganizationViewV1[];
  onExpired: () => void;
  onProofUnavailable: () => void;
  onRead: (data: LiveProcessLocationPageV1 | null) => void;
}>) {
  const [data, setData] = useState<LiveProcessLocationPageV1 | null>(null);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [selectedAccount, setSelectedAccount] = useState(account.account_id);
  const [confirmed, setConfirmed] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async (signal?: AbortSignal) => {
    try {
      const result = await runtime.processLocations(signal);
      if (signal?.aborted) return;
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        setFailed(true);
        setData(null);
        onRead(null);
        return;
      }
      setData(result.data);
      onRead(result.data);
      setFailed(false);
    } catch {
      if (!signal?.aborted) { setFailed(true); setData(null); onRead(null); }
    }
  }, [onExpired, onRead]);

  useEffect(() => {
    const controller = new AbortController();
    let refreshing = false;
    const read = async () => {
      if (refreshing) return;
      refreshing = true;
      try { await refresh(controller.signal); } finally { refreshing = false; }
    };
    void read();
    const interval = window.setInterval(() => { void read(); }, 30_000);
    return () => { controller.abort(); window.clearInterval(interval); };
  }, [refresh]);

  async function save(item: LiveProcessLocationViewV1, accountId: string | null) {
    if (busy) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await runtime.setProcessAccount(item, accountId);
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        else if (result.problem.code === "csrf_validation_failed") onProofUnavailable();
        else setMessage(result.problem.status === 412
          ? "This link changed. Review the refreshed terminal before trying again."
          : "The link was rejected. Check that the terminal is still running and the account is active.");
        await refresh();
        return;
      }
      setEditing(null);
      setConfirmed(false);
      await refresh();
      setMessage(accountId === null ? "Account link removed." : "Account link saved · Owner confirmed.");
    } catch (error) {
      if (error instanceof CsrfUnavailableError) onProofUnavailable();
      else setMessage("The account link could not be saved. Refresh and try again.");
    } finally { setBusy(false); }
  }

  function edit(item: LiveProcessLocationViewV1) {
    setEditing(item.association_key ?? null);
    setSelectedAccount(item.account_association?.account_id ?? account.account_id);
    setConfirmed(false);
    setMessage(null);
  }

  function form(item: LiveProcessLocationViewV1) {
    const key = item.association_key!;
    const submit = (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (confirmed && selectedAccount) void save(item, selectedAccount);
    };
    return <form className="agent-link-form" onSubmit={submit}>
      <p>Open <code>/status</code> in this terminal and check its account email. Match the terminal to PID {item.pid}; several terminals can share a path.</p>
      <label htmlFor={"agent-account-" + key}>Account</label>
      <select id={"agent-account-" + key} value={selectedAccount} disabled={busy} onChange={event => { setSelectedAccount(event.target.value); setConfirmed(false); }}>
        <option value="">Choose an account</option>
        {accounts.filter(value => value.lifecycle === "active" && value.provider_key === item.provider_key).map(value =>
          <option key={value.account_id} value={value.account_id}>{value.friendly_name + " · " + (organizations.find(org => org.organization_id === value.organization_id)?.name ?? "Ungrouped")}</option>,
        )}
      </select>
      <label className="agent-confirmation"><input type="checkbox" checked={confirmed} disabled={busy} onChange={event => setConfirmed(event.target.checked)} />I checked this terminal’s /status and confirmed this account.</label>
      <div className="agent-link-actions">
        <button type="submit" disabled={busy || !confirmed || !selectedAccount}>Confirm account link</button>
        <button type="button" className="quiet-button" disabled={busy} onClick={() => { setEditing(null); setConfirmed(false); }}>Cancel</button>
      </div>
    </form>;
  }

  const unavailable = failed || (data !== null && data.availability.state !== "available");
  const current = unavailable ? [] : (data?.items ?? []).filter(item => item.provider_key === account.provider_key);
  const linked = current.filter(item => item.account_association?.account_id === account.account_id);
  const unlinked = current.filter(item => !item.account_association);
  const provider = providerDisplayName(account.provider_key);

  function table(items: readonly LiveProcessLocationViewV1[], label: string, isLinked: boolean) {
    return <div className="workspace-table-scroll"><table className="workspace-table account-agent-table" aria-label={label}>
      <thead><tr><th scope="col">Agent</th><th scope="col">State</th><th scope="col">Path</th><th scope="col">Details</th></tr></thead>
      <tbody>{items.map(item => <tr key={item.association_key} data-association-key={item.association_key}>
        <th scope="row" data-label="Agent"><strong>{providerDisplayName(item.provider_key)} · PID {item.pid}</strong>
          <small>{isLinked ? "Owner confirmed" : "Account unknown"}</small>
          {item.account_association && <small>{time(item.account_association.confirmed_at)}</small>}
        </th>
        <td data-label="State"><span className="activity-state activity-running"><span aria-hidden="true">●</span>Running</span><small>Activity unknown</small></td>
        <td data-label="Path" className="workspace-path"><code>{item.working_directory ?? "Unavailable"}</code>
          {editing === item.association_key ? form(item) : <div className="agent-link-actions">
            <button type="button" className="quiet-button" disabled={busy || !item.association_key} onClick={() => edit(item)}>{isLinked ? "Change account" : "Link account"}</button>
            {isLinked && <button type="button" className="quiet-button" disabled={busy} onClick={() => { void save(item, null); }}>Unlink account</button>}
          </div>}
        </td>
        <td data-label="Details"><ProcessDetails item={item} /></td>
      </tr>)}</tbody>
    </table></div>;
  }

  return <section className="account-workspace live-processes" aria-labelledby="live-processes-title">
    <div className="workspace-heading">
      <div><h2 id="live-processes-title">Agents using this account</h2><p>Current terminals with an account link you confirmed.</p></div>
      <div className="agent-heading-actions"><span className="process-count">{linked.length} linked</span>
        <button type="button" className="quiet-button" disabled={busy} onClick={() => { void refresh(); }}>Refresh agents</button>
      </div>
    </div>
    {data === null && !failed ? <p role="status">Reading running {provider} processes…</p>
      : unavailable ? <p role="status">Live process information could not be refreshed. Current account links are unavailable.</p>
      : linked.length === 0 ? <p>No agents linked to this account yet.</p>
      : table(linked, "Agents using this account", true)}
    {!unavailable && data !== null && unlinked.length > 0 && <details className="unlinked-agents" data-unlinked-agents="true">
      <summary>Identify other {provider} terminals <span>{unlinked.length} unlinked</span></summary>
      <p>These terminals have no confirmed account. Check each terminal’s <code>/status</code> before linking it.</p>
      {table(unlinked, `Unlinked ${provider} terminals`, false)}
    </details>}
    {message && <p role="status">{message}</p>}
    {data !== null && <p className="live-process-note">Updated {time(data.availability.as_of)} · Running means present; working or waiting is unknown. Reconfirm the link if you change the account inside a terminal.</p>}
    {data?.truncated && <p className="live-process-note">This scan is partial; some processes may be missing.</p>}
  </section>;
}
