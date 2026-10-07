import { useEffect, useState } from "react";

import {
  capacity,
  runtime,
  providers,
  type AccountCapacityViewV1,
  type AccountViewV1,
  type AgentSessionPageV1,
  type LiveProcessLocationPageV1,
  type ObservedAccountIdentityViewV1,
} from "../../shared/api/client";
import { metricAvailability, remainingPercentage } from "../command/quotaPresentation";
import { providerDisplayName } from "./providerPresentation";

type SummaryState =
  | Readonly<{ kind: "loading" }>
  | Readonly<{ kind: "error" }>
  | Readonly<{ kind: "ready"; accountId: string; capacity: AccountCapacityViewV1 | null; sessions: AgentSessionPageV1 | null; identity: ObservedAccountIdentityViewV1 | null; refreshFailed: boolean }>;

export function AccountWorkspaceSummary({ account, organizationName, liveProcesses, onExpired, onIdentity }: Readonly<{
  account: AccountViewV1;
  organizationName: string;
  liveProcesses: LiveProcessLocationPageV1 | null;
  onExpired: () => void;
  onIdentity: (email: string | null) => void;
}>) {
  const [state, setState] = useState<SummaryState>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    let refreshing = false;
    const refresh = async () => {
      if (refreshing) return;
      refreshing = true;
      try {
        const [quota, sessions, identity] = await Promise.all([
          capacity.account(account.account_id, controller.signal),
          runtime.sessions({ accountId: account.account_id, signal: controller.signal }),
          providers.observedAccountIdentity(account.account_id, controller.signal),
        ]);
        if (controller.signal.aborted) return;
        if ((!quota.ok && quota.problem.code === "dashboard_authentication_required") ||
            (!sessions.ok && sessions.problem.code === "dashboard_authentication_required") ||
            (!identity.ok && identity.problem.code === "dashboard_authentication_required")) {
          onExpired();
          return;
        }
        setState((current) => ({
          kind: "ready",
          accountId: account.account_id,
          capacity: quota.ok ? quota.data : current.kind === "ready" && current.accountId === account.account_id ? current.capacity : null,
          sessions: sessions.ok ? sessions.data : current.kind === "ready" && current.accountId === account.account_id ? current.sessions : null,
          identity: identity.ok ? identity.data : current.kind === "ready" && current.accountId === account.account_id ? current.identity : null,
          refreshFailed: !quota.ok || !sessions.ok || !identity.ok,
        }));
      } catch {
        if (controller.signal.aborted) return;
        setState((current) => current.kind === "ready" ? { ...current, refreshFailed: true } : { kind: "error" });
      } finally {
        refreshing = false;
      }
    };
    void refresh();
    const interval = window.setInterval(() => { void refresh(); }, 30_000);
    return () => {
      controller.abort();
      window.clearInterval(interval);
    };
  }, [account.account_id, onExpired]);

  const scoped = state.kind === "ready" && state.accountId === account.account_id ? state : null;
  const capacityItems = scoped?.capacity?.items ?? [];
  const readings = capacityItems.flatMap((item) => {
    const constraining = item.windows.find((window) => window.window_id === item.health?.constraining_window_id);
    return constraining === undefined ? item.windows : [constraining];
  });
  const receipt = scoped?.identity ?? null;
  const verified = receipt?.state === "verified" && receipt.account_id === account.account_id && receipt.email !== null && readings.length > 0 &&
    readings.every((window) => window.collection_run_id === receipt.collection_run_id);
  const email = verified ? receipt.email : null;
  useEffect(() => { onIdentity(email); }, [email, onIdentity]);
  const hasMoreSessions = scoped?.sessions?.page.has_more;
  const sessionCount = scoped?.sessions?.items.length;
  const linked = liveProcesses?.availability.state === "available" ? liveProcesses.items.filter(item => item.account_association?.account_id === account.account_id) : [];
  const paths = [...new Set(linked.flatMap(item => item.working_directory === null ? [] : [item.working_directory]))];
  const status = account.lifecycle === "archived" ? "Archived"
    : account.lifecycle === "pending" ? "Not connected"
    : !account.is_effective_monitoring_enabled ? "Monitoring paused"
    : linked.length > 0 ? "Running" : "Activity unknown";
  const monitoring = account.is_effective_monitoring_enabled ? "Monitoring on" : "Monitoring off";
  const updatedAt = readings.length === 0 ? null : readings.map((window) => window.collected_at).sort()[0]!;
  const provider = providerDisplayName(account.provider_key);

  return (
    <section className="account-workspace" aria-labelledby="account-activity-title" aria-busy={state.kind === "loading"}>
      <div className="workspace-heading">
        <div><h2 id="account-activity-title">Account activity</h2><p>{verified ? "Account identified with the latest quota reading." : "Waiting for a verified quota reading."}</p></div>
        <span className="workspace-updated">{updatedAt === null ? "No quota reading yet" : <>Quota updated <time dateTime={updatedAt}>{new Date(updatedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time></>}</span>
      </div>
      <div className="workspace-table-scroll">
        <table className="workspace-table" aria-label="Account activity">
          <thead><tr><th scope="col">Account</th><th scope="col">State</th><th scope="col">Left</th><th scope="col">Path</th></tr></thead>
          <tbody><tr>
            <th scope="row" data-label="Account"><strong className="workspace-account-name">{email ?? account.friendly_name}</strong><span className="workspace-account-meta"><span className="organization-tag">{organizationName}</span><span className="provider-name">{account.provider_key}</span></span><small>{email === null ? (account.lifecycle === "pending" ? "Not connected to a provider profile" : "Admin account name · awaiting verified quota") : `Account reported by ${provider}`}</small></th>
            <td data-label="State"><span className={`activity-state ${account.is_effective_monitoring_enabled ? "activity-unknown" : "activity-paused"}`}><span aria-hidden="true">{account.is_effective_monitoring_enabled ? "◌" : "○"}</span>{status}</span><small>{monitoring}</small></td>
            <td data-label="Left" className="workspace-remaining">
              <div className="workspace-readings">
              {state.kind === "loading" ? <span role="status">Reading quota…</span> : readings.length === 0 ? <strong>Unavailable</strong> : readings.map((window) => {
                const percentage = remainingPercentage(window.allowance?.remaining_percentage ?? window.remaining_ratio);
                return <div className="workspace-reading" key={window.window_id}>
                  <strong>{percentage?.label ?? metricAvailability(window.remaining_ratio)}</strong>
                  <small>{window.safe_label ?? window.window_key}{window.freshness !== "fresh" ? ` · ${window.freshness.replaceAll("_", " ")}` : ""}</small>
                  {window.allowance !== null && window.allowance !== undefined && <small className="calculated-label">Calculated{window.allowance.remaining_percentage.precision === "rounded" ? " · rounded" : ""}</small>}
                  {percentage !== null && <div className="allowance-track" aria-hidden="true"><span style={{ width: `${percentage.value}%` }} /></div>}
                </div>;
              })}
              </div>
            </td>
            <td data-label="Path" className="workspace-path">{paths.length > 0 ? <>{paths.map(path => <code key={path}>{path}</code>)}<small>Owner-confirmed terminals · working directories</small></> : <><strong>Not reported</strong><small>No linked terminal location available</small></>}</td>
          </tr></tbody>
        </table>
      </div>
      <div className="workspace-footnote">
        <span>{sessionCount === undefined ? "Session data unavailable" : `${sessionCount}${hasMoreSessions ? "+" : ""} linked session ${sessionCount === 1 ? "record" : "records"}`}</span>
        <span>{liveProcesses?.availability.state !== "available" ? "Live agent links unavailable" : linked.length > 0 ? linked.length + " running " + (linked.length === 1 ? "agent" : "agents") + " · Owner confirmed" : "No running agents linked to this account."}{liveProcesses?.truncated ? " · Partial scan" : ""}</span>
      </div>
      {email !== null && <details className="workspace-identity-details"><summary>How this account was identified</summary><p className="workspace-identity-note">{provider} reported this identity before and after this quota check.<span>{provider} organization: <strong>{receipt?.provider_organization ?? "Not reported"}</strong></span><span>Dashboard group: {organizationName} · Record: {account.friendly_name}</span><span>Quota collection: {receipt?.collection_run_id}</span></p></details>}
      {(state.kind === "error" || (state.kind === "ready" && state.refreshFailed)) && <p className="workspace-notice" role="status">Some readings could not be refreshed. Check the displayed update time.</p>}
    </section>
  );
}
