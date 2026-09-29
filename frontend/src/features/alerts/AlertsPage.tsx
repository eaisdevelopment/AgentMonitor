import { useCallback, useEffect, useState } from "react";

import {
  alerts, CsrfUnavailableError, registry,
  type AccountViewV1, type AlertCommandWireV1,
  type AlertHistoryPageV1, type AlertNotificationCountsWireV1,
  type AlertNotificationPageV1, type AlertWireV1, type ClientResult,
  type OrganizationViewV1,
} from "../../shared/api/client";

type ReadyState = Readonly<{
  kind: "ready";
  notifications: AlertNotificationPageV1;
  counts: AlertNotificationCountsWireV1;
  organizations: readonly OrganizationViewV1[];
  accounts: readonly AccountViewV1[];
}>;
type PageState = ReadyState | Readonly<{ kind: "loading" | "error" }>;

const conditionNames: Readonly<Record<AlertWireV1["condition_type"], string>> = {
  capacity_remaining: "Capacity running low",
  capacity_exhausted: "Capacity exhausted",
  capacity_unavailable: "Capacity unavailable",
  forecasted_exhaustion: "Capacity may run out",
  authentication_attention: "Sign-in needs attention",
  data_stale: "Reading is stale",
  collector_failure: "Collector failed",
  possible_stall: "Agent may be stalled",
};

function remaining(alert: AlertWireV1): string | null {
  if (alert.remaining_basis_points === null) return null;
  const percent = Number(alert.remaining_basis_points) / 100;
  if (!Number.isFinite(percent) || percent < 0 || percent > 100) return null;
  return `${Number(percent.toFixed(2))}% left`;
}

function accountName(alert: AlertWireV1, accounts: readonly AccountViewV1[]): string {
  if (alert.account_id === null) return "Account unresolved";
  return accounts.find((item) => item.account_id === alert.account_id)?.friendly_name ?? "Account unavailable";
}

function time(value: string): string {
  return new Date(value).toLocaleString();
}

export function AlertsPage({
  onExpired, onProofUnavailable, onOpenAccount, onOpenRules,
}: Readonly<{
  onExpired: () => void;
  onProofUnavailable: () => void;
  onOpenAccount: (accountId: string) => void;
  onOpenRules: () => void;
}>) {
  const [selectedOrganization, setSelectedOrganization] = useState("");
  const [state, setState] = useState<PageState>({ kind: "loading" });
  const [history, setHistory] = useState<Readonly<Record<string, AlertHistoryPageV1>>>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const scope = selectedOrganization
    ? { kind: "organization" as const, id: selectedOrganization } : undefined;
  const load = useCallback(async (signal?: AbortSignal) => {
    try {
      const [notificationResult, countResult, organizationResult, accountResult] =
        await Promise.all([
          alerts.notifications(scope, undefined, signal), alerts.counts(scope, signal),
          registry.organizations(signal), registry.accounts(signal),
        ]);
      if (!notificationResult.ok || !countResult.ok || !organizationResult.ok || !accountResult.ok) {
        const results = [notificationResult, countResult, organizationResult, accountResult];
        if (results.some((item) => !item.ok && item.problem.code === "dashboard_authentication_required")) onExpired();
        else setState({ kind: "error" });
        return;
      }
      setState({ kind: "ready", notifications: notificationResult.data,
        counts: countResult.data, organizations: organizationResult.data.items,
        accounts: accountResult.data.items });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setState({ kind: "error" });
    }
  }, [onExpired, selectedOrganization]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function act(
    action: () => Promise<ClientResult<AlertCommandWireV1>>, success: string,
  ) {
    if (busy) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await action();
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        else if (result.problem.code === "csrf_validation_failed") onProofUnavailable();
        else if (result.problem.status === 412) {
          setMessage("This alert changed. Its current state is being loaded.");
          await load();
        } else setMessage("The alert change was rejected. Refresh its current state and try again.");
        return;
      }
      await load();
      setMessage(success);
    } catch (error) {
      if (error instanceof CsrfUnavailableError) onProofUnavailable();
      else setMessage("The local service is unavailable. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function loadHistory(alertId: string) {
    if (history[alertId] !== undefined) return;
    try {
      const result = await alerts.history(alertId);
      if (result.ok) setHistory((current) => ({ ...current, [alertId]: result.data }));
      else if (result.problem.code === "dashboard_authentication_required") onExpired();
      else setMessage("Alert history could not be loaded.");
    } catch {
      setMessage("Alert history could not be loaded.");
    }
  }

  async function loadMore() {
    if (state.kind !== "ready" || !state.notifications.page.next_cursor || busy) return;
    setBusy(true);
    try {
      const result = await alerts.notifications(scope, state.notifications.page.next_cursor);
      if (result.ok) {
        setState({ ...state, notifications: { ...result.data,
          items: [...state.notifications.items, ...result.data.items] } });
      } else if (result.problem.code === "dashboard_authentication_required") onExpired();
      else setMessage("More alerts could not be loaded.");
    } catch {
      setMessage("More alerts could not be loaded.");
    } finally {
      setBusy(false);
    }
  }

  const items = state.kind === "ready" ? state.notifications.items : [];
  return <section className="telemetry-panel alerts-page" aria-labelledby="page-title" aria-busy={state.kind === "loading"}>
    <div className="panel-heading"><h1 id="page-title" tabIndex={-1}>Alerts</h1>
      <div className="alert-heading-actions">
        <button type="button" className="quiet-button" onClick={onOpenRules}>Alert rules</button>
        <button type="button" className="quiet-button" onClick={() => { void load(); }}>Refresh alerts</button>
      </div>
    </div>
    {message && <p role="status" className="form-status">{message}</p>}
    {state.kind === "loading" && <p role="status">Loading alerts…</p>}
    {state.kind === "error" && <p role="alert">Alerts could not be loaded. Refresh to try again.</p>}
    {state.kind === "ready" && <>
      <div className="alert-summary" aria-label="Alert counts">
        <strong>{state.counts.active_critical} critical</strong>
        <span>{state.counts.active_warning} warning</span>
        <span>{state.counts.visible_unread} unread</span>
        <span>{state.counts.snoozed} snoozed</span>
      </div>
      <label className="alert-filter">Organization
        <select value={selectedOrganization} onChange={(event) => setSelectedOrganization(event.target.value)}>
          <option value="">All organizations</option>
          {state.organizations.filter((item) => item.lifecycle === "active").map((item) =>
            <option key={item.organization_id} value={item.organization_id}>{item.name}</option>)}
        </select>
      </label>
      {items.length === 0 ? <p>No active alerts.</p> :
        <ul className="alert-list">{items.map(({ alert, rank }) => {
          const account = accountName(alert, state.accounts);
          const quota = remaining(alert);
          const alertHistory = history[alert.alert_id];
          const snoozed = alert.snoozed_until !== null && new Date(alert.snoozed_until).getTime() > Date.now();
          return <li key={alert.alert_id} className={`alert-card alert-rank-${rank}`}>
            <div className="alert-card-heading"><div>
              <span className={`state-chip state-${alert.severity}`}>{alert.severity}</span>
              <h2>{conditionNames[alert.condition_type]}</h2>
              <p>{account}{quota ? ` · ${quota}` : ""}</p>
            </div><time dateTime={alert.last_seen_at}>{time(alert.last_seen_at)}</time></div>
            <p className="alert-explanation">{alert.decision_reason_code.replaceAll("_", " ")}
              {alert.lifecycle !== "open" ? ` · ${alert.lifecycle.replaceAll("_", " ")}` : ""}
              {snoozed ? ` · Snoozed until ${time(alert.snoozed_until!)}` : ""}
            </p>
            <div className="alert-actions">
              {alert.account_id && <button type="button" onClick={() => onOpenAccount(alert.account_id!)}>Open account</button>}
              {alert.lifecycle === "open" && alert.acknowledged_at === null &&
                <button type="button" disabled={busy} onClick={() => { void act(() => alerts.acknowledge(alert), "Alert acknowledged."); }}>Acknowledge</button>}
              {alert.lifecycle === "open" && (snoozed
                ? <button type="button" disabled={busy} onClick={() => { void act(() => alerts.unsnooze(alert), "Snooze ended."); }}>Unsnooze</button>
                : <button type="button" disabled={busy} onClick={() => { void act(() => alerts.snooze(alert, 900), "Alert snoozed for 15 minutes."); }}>Snooze 15 minutes</button>)}
              {alert.unread && <button type="button" disabled={busy} onClick={() => { void act(() => alerts.markRead(alert), "Alert marked read."); }}>Mark read</button>}
            </div>
            <details onToggle={(event) => { if (event.currentTarget.open) void loadHistory(alert.alert_id); }}>
              <summary>Details and history</summary>
              <dl className="alert-facts"><div><dt>Account</dt><dd>{account}</dd></div>
                <div><dt>Source state</dt><dd>{alert.truth_state.replaceAll("_", " ")}</dd></div>
                <div><dt>Source recorded</dt><dd>{time(alert.source_recorded_at)}</dd></div>
                <div><dt>Rule scope</dt><dd>{alert.rule_scope_kind}{alert.rule_scope_id ? ` · ${alert.rule_scope_id}` : ""}</dd></div>
              </dl>
              <h3>History</h3>
              {alertHistory === undefined ? <p role="status">Loading history…</p> :
                <ol>{alertHistory.items.map((entry) =>
                  <li key={entry.event_id}>{entry.transition.replaceAll("_", " ")} · <time dateTime={entry.occurred_at}>{time(entry.occurred_at)}</time></li>)}</ol>}
            </details>
          </li>;
        })}</ul>}
      {state.notifications.page.has_more && <button type="button" disabled={busy} onClick={() => { void loadMore(); }}>Load more alerts</button>}
    </>}
  </section>;
}
