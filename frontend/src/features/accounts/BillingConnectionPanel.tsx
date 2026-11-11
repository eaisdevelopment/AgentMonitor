import { useEffect, useRef, useState, type FormEvent } from "react";

import { CsrfUnavailableError, registry, type AccountBillingConnectionsV1, type AccountViewV1 } from "../../shared/api/client";

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
  if (reason === "existing_cloud_connection_required") return "Ollama Cloud billing uses the existing cloud connection flow. API-only setup is not available yet.";
  if (reason === "provider_unsupported") return "API billing setup is unsupported for this provider.";
  if (reason === "account_unavailable") return "Restore or enable this account before adding a billing connection.";
  return "A billing connection cannot be added in the current account state. Refresh its status before trying again.";
}

/** Registry metadata only: access verification and credential custody are separate. */
export function BillingConnectionPanel({ account, onExpired, onProofUnavailable, onAccountReload }: Readonly<{
  account: AccountViewV1;
  onExpired: () => void;
  onProofUnavailable: () => void;
  onAccountReload: () => void;
}>) {
  const [state, setState] = useState<BillingState>({ kind: "loading" });
  const [revision, setRevision] = useState(0);
  const [scopeId, setScopeId] = useState("");
  const [busy, setBusy] = useState(false);
  const [copyStatus, setCopyStatus] = useState("");
  const mutating = useRef(false);
  const reading = useRef(false);
  const mounted = useRef(false);
  const expiredHandler = useRef(onExpired);
  expiredHandler.current = onExpired;
  const credentialStatus = state.kind === "ready" ? state.status.credential_status : null;
  const localSetup = state.kind === "ready" ? state.status.local_setup : null;

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

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

  return <section className="telemetry-panel" aria-labelledby="api-billing-setup-title" aria-busy={busy || state.kind === "loading"}>
    <div className="panel-heading"><h2 id="api-billing-setup-title">API billing setup</h2></div>
    {state.kind === "loading" && <p role="status">Reading billing connection status…</p>}
    {state.kind === "error" && <p role="alert">{state.message}</p>}
    {state.kind === "ready" && <>
      {state.status.connections.length === 0 && <>
        <p>API billing is not set up.</p>
        {!state.status.can_add_connection && <p>{unavailableReason(state.status.reason_code)}</p>}
      </>}
      {state.status.connections.map((connection) => <div key={connection.resource_id}>
        <p><span className="state-chip state-unavailable">Connection {connection.lifecycle}</span></p>
        <p>{connection.lifecycle === "pending" ? "Access has not been verified." : "Credential access status is not available in this view."}</p>
        <p>{connection.monitoring_preference === "disabled" ? "API monitoring is off." : "API monitoring preference is enabled."}</p>
        <dl className="telemetry-readouts">
          <div><dt>Provider billing scope</dt><dd>{connection.scope_id ?? "Provider billing scope has not been specified."}</dd></div>
          <div><dt>Scope evidence</dt><dd>{connection.scope_evidence.replaceAll("_", " ")}</dd></div>
        </dl>
        <p>{localSetup == null ? "Credential setup and access verification are not available in this step yet." : "Access verification is not available in this step yet."}</p>
      </div>)}
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
