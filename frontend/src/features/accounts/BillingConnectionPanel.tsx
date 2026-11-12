import { useEffect, useRef, useState, type FormEvent } from "react";

import { CsrfUnavailableError, registry, type AccountBillingConnectionsV1, type AccountViewV1, type BillingConnectionViewV1, type BudgetRunStatusV1, type BillingMonitoringStatusV1 } from "../../shared/api/client";
import { checkEligibility, matchesCheckRun, pendingRun, restoreCheckIntent, currentCheckEvidence, monitoringReason, restoreMonitoringIntent, buildMonitoringIntent, monitoringStatusCurrent, type BillingCheckIntent, type BillingMonitoringIntent } from "./billingCheckPresentation";
import { FinancialPoolPanel } from "./FinancialPoolPanel";

type BillingState =
  | Readonly<{ kind: "loading" }>
  | Readonly<{ kind: "error"; message: string }>
  | Readonly<{ kind: "ready"; status: AccountBillingConnectionsV1 }>;

const credentialStateLabels = {
  missing: "Credential required",
  pending: "Credential entry pending",
  stored: "Credential stored",
  cleanup_required: "Credential cleanup required",
} as const;

function unavailableReason(reason: string): string {
  if (reason === "existing_cloud_connection_required") return "Ollama Cloud billing uses this account's existing cloud connection and shared balance.";
  if (reason === "provider_unsupported") return "API billing setup is unsupported for this provider.";
  if (reason === "account_unavailable") return "Restore or enable this account before adding a billing connection.";
  return "A billing connection cannot be added in the current account state. Refresh its status before trying again.";
}

function BillingMonitoringControls({ accountStatus, connection, onExpired, onProofUnavailable, onChanged }: Readonly<{
  accountStatus: AccountBillingConnectionsV1;
  connection: BillingConnectionViewV1;
  onExpired: () => void;
  onProofUnavailable: () => void;
  onChanged: () => void;
}>) {
  const [status, setStatus] = useState<BillingMonitoringStatusV1 | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(false);
  const storageKey = `agentmonitor.billing-monitoring.${connection.account_id}.${connection.resource_id}`;
  const [intent, setIntent] = useState<BillingMonitoringIntent | null>(() => {
    try { return restoreMonitoringIntent(sessionStorage.getItem(storageKey), connection.account_id, connection.resource_id); }
    catch { return null; }
  });
  const mounted = useRef(false);
  const mutating = useRef(false);
  const request = useRef<AbortController | null>(null);
  const callbacks = useRef({ onExpired, onProofUnavailable, onChanged });
  callbacks.current = { onExpired, onProofUnavailable, onChanged };
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; request.current?.abort(); };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setStatus(null);
    setError(null);
    void (async () => {
      try {
        const result = await registry.billingMonitoring(connection.account_id, connection.resource_id, controller.signal);
        if (controller.signal.aborted) return;
        if (!result.ok) {
          if (result.problem.code === "dashboard_authentication_required") callbacks.current.onExpired();
          else setError(monitoringReason(result.problem.code));
          return;
        }
        if (result.data.account_id !== connection.account_id || result.data.resource_id !== connection.resource_id || result.data.scope_generation !== connection.scope_generation) {
          setError("The connection changed. Refresh billing status before changing monitoring.");
          return;
        }
        setStatus(result.data);
      } catch {
        if (!controller.signal.aborted) setError("The local monitoring service is unavailable. Refresh to try again.");
      }
    })();
    return () => controller.abort();
  }, [accountStatus, connection.account_id, connection.resource_id, connection.scope_generation, revision]);

  function retain(value: BillingMonitoringIntent | null): boolean {
    try {
      if (value === null) sessionStorage.removeItem(storageKey);
      else sessionStorage.setItem(storageKey, JSON.stringify(value));
    } catch {
      if (value !== null) {
        setMessage("This tab cannot retain the monitoring request safely. Allow tab storage before changing monitoring.");
        return false;
      }
    }
    setIntent(value);
    return true;
  }

  async function submit(value: BillingMonitoringIntent) {
    if (mutating.current || !retain(value)) return;
    mutating.current = true;
    setBusy(true);
    setMessage(null);
    const controller = new AbortController();
    request.current = controller;
    try {
      const result = await registry.setBillingMonitoring(value, controller.signal);
      if (!mounted.current || controller.signal.aborted) return;
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") callbacks.current.onExpired();
        else if (result.problem.code === "csrf_validation_failed") callbacks.current.onProofUnavailable();
        else {
          const knownRejected = ["registry_version_conflict", "billing_monitoring_version_conflict", "billing_monitoring_target_changed", "billing_monitoring_verification_required", "billing_monitoring_credential_required", "billing_monitoring_account_unavailable", "billing_monitoring_target_unavailable", "registry_replay_stale"].includes(result.problem.code);
          if (knownRejected) retain(null);
          setMessage(`${monitoringReason(result.problem.code)}${knownRejected ? "" : " Resolve this request before making another monitoring change."}`);
          setRevision((current) => current + 1);
          if (knownRejected) callbacks.current.onChanged();
        }
        return;
      }
      if (result.data.account_id !== value.accountId || result.data.resource_id !== value.resourceId || result.data.scope_generation !== value.scopeGeneration || result.data.monitoring_preference !== value.preference) {
        setMessage("The monitoring response did not match this request. Resolve its outcome before changing monitoring again.");
        setRevision((current) => current + 1);
        return;
      }
      retain(null);
      setStatus(null);
      setMessage("Monitoring change recorded. Reading its current server status.");
      setRevision((current) => current + 1);
      callbacks.current.onChanged();
    } catch (caught) {
      if (!mounted.current || controller.signal.aborted) return;
      if (caught instanceof CsrfUnavailableError) callbacks.current.onProofUnavailable();
      else {
        setMessage("The monitoring change outcome is unknown. Resolve this request with its original identity before changing it again.");
        setRevision((current) => current + 1);
      }
    } finally {
      mutating.current = false;
      if (mounted.current) setBusy(false);
    }
  }

  const currentStatus = monitoringStatusCurrent(status, accountStatus, connection) ? status : null;
  const preference = currentStatus?.monitoring_preference === "enabled" ? "disabled" : "enabled";
  const allowed = currentStatus !== null && (preference === "enabled" ? currentStatus.can_enable : currentStatus.can_disable);
  const disabled = busy || intent !== null || !allowed;
  const helpId = `billing-monitoring-help-${connection.resource_id}`;
  function change() {
    if (disabled || currentStatus === null) return;
    void submit(buildMonitoringIntent(currentStatus, preference,
      Array.from(crypto.getRandomValues(new Uint8Array(16)), (byte) => byte.toString(16).padStart(2, "0")).join("")));
  }
  return <div>
    {currentStatus !== null ? <>
      <p>{currentStatus.monitoring_preference === "enabled" ? "API monitoring is on." : "API monitoring is off."}</p>
      <p>{currentStatus.verified_run_id === null ? "Access has not been verified." : "Access is confirmed for the current credential and billing scope."}</p>
    </> : <p role="status">{error ?? (status === null ? "Reading current API monitoring eligibility…" : "The account or connection changed. Refresh billing status before changing monitoring.")}</p>}
    <p id={helpId}>{currentStatus === null ? "Refresh monitoring status before changing this setting." : monitoringReason(currentStatus.reason_code)}</p>
    <button type="button" aria-disabled={disabled} aria-describedby={helpId} onClick={change}>{preference === "enabled" ? "Enable API monitoring" : "Disable API monitoring"}</button>
    {message !== null && <p role="status">{message}</p>}
    {intent !== null && <button type="button" className="quiet-button" disabled={busy} onClick={() => { void submit(intent); }}>Resolve monitoring outcome</button>}
    <button type="button" className="quiet-button" disabled={busy} onClick={() => setRevision((current) => current + 1)}>Refresh monitoring status</button>
  </div>;
}

/** Local custody metadata and bounded collection actions remain separate facts. */
export function BillingConnectionPanel({ account, onExpired, onProofUnavailable, onAccountReload, onFinancialRead }: Readonly<{
  account: AccountViewV1;
  onExpired: () => void;
  onProofUnavailable: () => void;
  onAccountReload: () => void;
  onFinancialRead: () => void;
}>) {
  const [state, setState] = useState<BillingState>({ kind: "loading" });
  const [revision, setRevision] = useState(0);
  const [scopeId, setScopeId] = useState("");
  const [busy, setBusy] = useState(false);
  const [copyStatus, setCopyStatus] = useState("");
  const storageKey = `agentmonitor.billing-check.${account.account_id}`;
  const [checkIntent, setCheckIntent] = useState<BillingCheckIntent | null>(() => {
    try { return restoreCheckIntent(sessionStorage.getItem(storageKey), account.account_id); }
    catch { return null; }
  });
  const [checkRun, setCheckRun] = useState<BudgetRunStatusV1 | null>(null);
  const [checkEvidence, setCheckEvidence] = useState<BillingCheckIntent | null>(null);
  const [checkMessage, setCheckMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [pollRevision, setPollRevision] = useState(0);
  const checkBusy = useRef(false);
  const checkRequest = useRef<AbortController | null>(null);
  const panel = useRef<HTMLElement>(null);
  const financialRead = useRef(onFinancialRead);
  financialRead.current = onFinancialRead;
  const mutating = useRef(false);
  const reading = useRef(false);
  const mounted = useRef(false);
  const expiredHandler = useRef(onExpired);
  expiredHandler.current = onExpired;
  const credentialStatus = state.kind === "ready" ? state.status.credential_status : null;
  const localSetup = state.kind === "ready" ? state.status.local_setup : null;

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; checkRequest.current?.abort(); };
  }, []);

  function retainIntent(intent: BillingCheckIntent | null): boolean {
    try {
      if (intent === null) sessionStorage.removeItem(storageKey);
      else sessionStorage.setItem(storageKey, JSON.stringify(intent));
    } catch {
      if (intent !== null) {
        setCheckMessage("This tab cannot retain the check request safely. Allow tab storage before checking.");
        return false;
      }
    }
    setCheckIntent(intent);
    return true;
  }

  useEffect(() => {
    const controller = new AbortController();
    reading.current = true;
    setState((current) => current.kind === "ready" ? current : { kind: "loading" });
    void (async () => {
      try {
        const result = await registry.billingConnections(account.account_id, controller.signal);
        if (controller.signal.aborted) return;
        if (!result.ok) {
          if (result.problem.code === "dashboard_authentication_required") expiredHandler.current();
          else setState({ kind: "error", message: "Billing connection status could not be loaded. Refresh to try again." });
          return;
        }
        if (result.data.account_id !== account.account_id || result.data.provider_key !== account.provider_key) {
          setState({ kind: "error", message: "Billing connection status did not match this account. Refresh to try again." });
          return;
        }
        setState({ kind: "ready", status: result.data });
      } catch {
        if (!controller.signal.aborted) setState({ kind: "error", message: "The local billing registry is unavailable. Refresh to try again." });
      } finally {
        if (!controller.signal.aborted) reading.current = false;
      }
    })();
    return () => controller.abort();
  }, [account.account_id, account.provider_key, account.record_version, revision]);

  useEffect(() => {
    if (state.kind !== "ready") return;
    const onReturn = () => {
      if (document.visibilityState !== "visible" || mutating.current || reading.current) return;
      reading.current = true;
      setRevision((current) => current + 1);
    };
    window.addEventListener("focus", onReturn);
    document.addEventListener("visibilitychange", onReturn);
    return () => {
      window.removeEventListener("focus", onReturn);
      document.removeEventListener("visibilitychange", onReturn);
    };
  }, [state.kind]);

  const checkIsCurrent = state.kind === "ready" && checkEvidence !== null && state.status.connections.some((connection) => currentCheckEvidence(checkEvidence, state.status, connection));
  useEffect(() => {
    if (state.kind === "ready" && checkEvidence !== null && !checkIsCurrent) {
      setCheckRun(null);
      setCheckEvidence(null);
      setCheckMessage("The credential or billing scope changed. Previous Check success is no longer current.");
    }
  }, [state.kind, checkEvidence, checkIsCurrent]);

  useEffect(() => {
    if (checkIntent?.runId == null || state.kind !== "ready") return;
    const connection = state.status.connections.find((value) => value.resource_id === checkIntent.resourceId);
    if (!connection || connection.scope_generation !== checkIntent.scopeGeneration || state.status.credential_status?.active_generation !== checkIntent.credentialGeneration || !["pending", "active"].includes(connection.lifecycle) || !["pending", "active"].includes(state.status.account_lifecycle)) {
      retainIntent(null);
      setCheckRun(null);
      setCheckMessage("The connection or credential changed. The previous check will not update this account view.");
      return;
    }
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let reads = 0;
    const stopAt = Math.min(Date.parse(checkIntent.deadlineAt!), Date.now() + 125000) + 5000;
    const poll = async () => {
      if (controller.signal.aborted) return;
      if (reads > 0 && Date.now() > stopAt) {
        setCheckMessage("Check result is not confirmed. Refresh check status to reconcile the existing run.");
        return;
      }
      if (document.visibilityState !== "visible" || panel.current?.getClientRects().length === 0) {
        if (Date.now() <= stopAt) timer = setTimeout(() => { void poll(); }, 2000);
        return;
      }
      reads += 1;
      try {
        const result = await registry.billingRun(checkIntent.runId!, controller.signal);
        if (controller.signal.aborted) return;
        if (!result.ok) {
          if (result.problem.code === "dashboard_authentication_required") expiredHandler.current();
          else setCheckMessage("Check status could not be read. Refresh check status; do not start a duplicate check.");
          return;
        }
        if (!matchesCheckRun(checkIntent, result.data)) {
          setCheckMessage("Check status did not match this account and resource. No financial reading was changed.");
          return;
        }
        setCheckRun(result.data);
        setCheckEvidence(checkIntent);
        setCheckMessage(null);
        if (pendingRun(result.data.state)) timer = setTimeout(() => { void poll(); }, 2000);
        else {
          retainIntent(null);
          setRevision((value) => value + 1);
          financialRead.current();
        }
      } catch {
        if (!controller.signal.aborted) setCheckMessage("The local service is unavailable. Refresh check status to reconcile the existing run.");
      }
    };
    void poll();
    return () => { controller.abort(); if (timer !== undefined) clearTimeout(timer); };
  }, [checkIntent, pollRevision, state]);

  async function submitCheck(intent: BillingCheckIntent) {
    if (checkBusy.current || !retainIntent(intent)) return;
    checkBusy.current = true;
    setSubmitting(true);
    setCheckMessage(null);
    const controller = new AbortController();
    checkRequest.current = controller;
    try {
      const result = await registry.checkBillingConnection(intent, controller.signal);
      if (!mounted.current || controller.signal.aborted) return;
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") expiredHandler.current();
        else if (result.problem.code === "csrf_validation_failed") onProofUnavailable();
        else if (["billing_check_version_conflict", "billing_check_target_changed", "billing_check_target_unavailable", "billing_check_authority_unavailable"].includes(result.problem.code)) {
          retainIntent(null);
          setRevision((value) => value + 1);
          setCheckMessage("The check was not admitted because this connection changed. Review refreshed status before checking again.");
        }
        else setCheckMessage(result.problem.status === 503
          ? "Collection runtime is unavailable. Credential storage has not changed. Resolve this check outcome before trying a new check."
          : "Check outcome is not confirmed. Resolve this request with its original identity before starting another check.");
        return;
      }
      if (!retainIntent({ ...intent, runId: result.data.run_id, deadlineAt: result.data.deadline_at })) return;
      setCheckMessage("Check accepted. Reading its actual run status; acceptance is not verified access.");
    } catch (error) {
      if (!mounted.current || controller.signal.aborted) return;
      if (error instanceof CsrfUnavailableError) onProofUnavailable();
      else setCheckMessage("Check outcome is unknown. Resolve this request before starting another check.");
    } finally {
      checkBusy.current = false;
      if (mounted.current) setSubmitting(false);
    }
  }

  function startCheck(connection: BillingConnectionViewV1) {
    if (state.kind !== "ready" || checkIntent !== null || checkBusy.current || !checkEligibility(state.status, connection).allowed) return;
    const generation = state.status.credential_status?.active_generation;
    if (generation == null) return;
    setCheckRun(null);
    setCheckEvidence(null);
    void submitCheck({
      accountId: account.account_id, resourceId: connection.resource_id,
      accountVersion: state.status.account_record_version,
      connectionVersion: connection.record_version,
      scopeGeneration: connection.scope_generation,
      credentialGeneration: generation,
      idempotencyKey: Array.from(crypto.getRandomValues(new Uint8Array(16)), (byte) => byte.toString(16).padStart(2, "0")).join(""),
      runId: null, deadlineAt: null,
    });
  }

  async function copyCommand() {
    if (localSetup == null) return;
    try {
      if (!navigator.clipboard) throw new Error("clipboard_unavailable");
      await navigator.clipboard.writeText(localSetup.command);
      if (mounted.current) setCopyStatus("Command copied.");
    } catch {
      if (mounted.current) setCopyStatus("Select the command to copy it manually.");
    }
  }

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (mutating.current || state.kind !== "ready" || !state.status.can_add_connection) return;
    mutating.current = true;
    setBusy(true);
    try {
      const result = await registry.createBillingConnection(state.status, scopeId.trim() || null);
      if (!mounted.current) return;
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") expiredHandler.current();
        else if (result.problem.code === "csrf_validation_failed") onProofUnavailable();
        else setState({ kind: "error", message: result.problem.status === 412
          ? "The account changed. Refresh billing status before adding the connection."
          : "The billing connection could not be saved. Refresh its status before trying again." });
        return;
      }
      if (result.data.account_id !== account.account_id) {
        setState({ kind: "error", message: "The saved billing connection did not match this account. Refresh its status." });
        return;
      }
      setState({ kind: "loading" });
      setRevision((current) => current + 1);
      onAccountReload();
    } catch (error) {
      if (!mounted.current) return;
      if (error instanceof CsrfUnavailableError) onProofUnavailable();
      else setState({ kind: "error", message: "The save outcome is unknown. Refresh billing status before trying again." });
    } finally {
      mutating.current = false;
      if (mounted.current) setBusy(false);
    }
  }

  return <section ref={panel} className="telemetry-panel" aria-labelledby="api-billing-setup-title" aria-busy={busy || submitting || state.kind === "loading"}>
    <div className="panel-heading"><h2 id="api-billing-setup-title">API billing setup</h2></div>
    {state.kind === "loading" && <p role="status">Reading billing connection status…</p>}
    {state.kind === "error" && <p role="alert">{state.message}</p>}
    {state.kind === "ready" && <>
      {state.status.connections.length === 0 && <>
        <p>API billing is not set up.</p>
        {!state.status.can_add_connection && <p>{unavailableReason(state.status.reason_code)}</p>}
      </>}
      {state.status.connections.map((connection) => <div key={connection.resource_id}>
        <FinancialPoolPanel account={account} resourceId={connection.resource_id} selector="billing" onExpired={onExpired} onProofUnavailable={onProofUnavailable} onChanged={() => { onAccountReload(); financialRead.current(); }} />
        <p><span className="state-chip state-unavailable">Connection {connection.lifecycle}</span></p>
        <BillingMonitoringControls accountStatus={state.status} connection={connection} onExpired={onExpired} onProofUnavailable={onProofUnavailable}
          onChanged={() => { setRevision((value) => value + 1); onAccountReload(); financialRead.current(); }} />
        <dl className="telemetry-readouts">
          <div><dt>Provider billing scope</dt><dd>{connection.scope_id ?? "Provider billing scope has not been specified."}</dd></div>
          <div><dt>Scope evidence</dt><dd>{connection.scope_evidence.replaceAll("_", " ")}</dd></div>
        </dl>
        <p id={`billing-check-help-${connection.resource_id}`}>{checkEligibility(state.status, connection).reason}</p>
        <button type="button" disabled={busy || submitting || checkIntent !== null || !checkEligibility(state.status, connection).allowed}
          aria-describedby={`billing-check-help-${connection.resource_id}`} onClick={() => startCheck(connection)}>Check connection</button>
      </div>)}
      {checkRun !== null && checkIsCurrent && <p role="status">Check {checkRun.state.replaceAll("_", " ")}{checkRun.error_code !== null && ` · ${checkRun.error_code.replaceAll("_", " ")}`}. Check status does not change the API monitoring preference.</p>}
      {checkMessage !== null && <p role="status">{checkMessage}</p>}
      {checkIntent?.runId === null && <button type="button" className="quiet-button" disabled={submitting} onClick={() => { void submitCheck(checkIntent); }}>Resolve check outcome</button>}
      {checkIntent?.runId != null && <button type="button" className="quiet-button" onClick={() => setPollRevision((value) => value + 1)}>Refresh check status</button>}
      {credentialStatus != null && <>
        <p><span className="state-chip state-unavailable">{credentialStateLabels[credentialStatus.state]}</span>{credentialStatus.state === "stored" && " Storage does not verify provider access."}</p>
        {credentialStatus.cleanup_required && <p className="connection-warning" role="status">Cleanup required: local credential removal has not been confirmed.</p>}
      </>}
      {localSetup != null && <details className="account-secondary" data-billing-local-setup="true">
        <summary>Set up or replace local key</summary>
        <p>Run this command on <strong>{localSetup.host_label}</strong>, the computer hosting AgentMonitor, as the user running its service.</p>
        <code className="ollama-setup-command" aria-label="Local credential setup command" tabIndex={0} onFocus={(event) => {
          const selection = window.getSelection();
          const range = document.createRange();
          range.selectNodeContents(event.currentTarget);
          selection?.removeAllRanges();
          selection?.addRange(range);
        }}>{localSetup.command}</code>
        <button type="button" className="quiet-button" onClick={() => { void copyCommand(); }}>Copy setup command</button>
        {copyStatus && <p role="status">{copyStatus}</p>}
      </details>}
      {state.status.can_add_connection && <form onSubmit={(event) => { void create(event); }}>
        <label htmlFor="billing-scope">Provider billing scope (optional)</label>
        <input id="billing-scope" value={scopeId} onChange={(event) => setScopeId(event.target.value)} maxLength={128} pattern="[A-Za-z0-9][A-Za-z0-9_.:\-]*" autoComplete="off" disabled={busy} aria-describedby="billing-scope-help" />
        <p id="billing-scope-help">Enter a nonsecret provider organization or workspace identifier if known. Leave blank when unknown. The dashboard organization does not establish provider ownership.</p>
        <button type="submit" disabled={busy}>{busy ? "Saving billing connection…" : "Add API billing connection"}</button>
      </form>}
    </>}
    <p>Credentials are configured on the computer hosting AgentMonitor, as the user running its service. This page does not accept API keys.</p>
    <button type="button" className="quiet-button" disabled={busy || state.kind === "loading"} onClick={() => setRevision((current) => current + 1)}>Refresh billing status</button>
  </section>;
}
