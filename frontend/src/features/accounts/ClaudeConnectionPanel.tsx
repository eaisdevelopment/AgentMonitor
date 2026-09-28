import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import {
  CsrfUnavailableError,
  providers,
  type AccountViewV1,
  type ClientResult,
  type ProviderConnectionViewV1,
} from "../../shared/api/client";

const activeStates = new Set<ProviderConnectionViewV1["state"]>([
  "requested", "awaiting_sign_in", "verifying",
]);

const stateLabels: Readonly<Record<ProviderConnectionViewV1["state"], string>> = {
  idle: "Ready to connect",
  requested: "Opening Claude sign-in",
  awaiting_sign_in: "Waiting for your sign-in",
  verifying: "Verifying the account",
  connected: "Claude connected",
  wrong_account: "Different Claude account detected",
  expired: "Sign-in expired",
  failed: "Connection unsuccessful",
  cancelled: "Connection cancelled",
  setup_required: "Claude setup required",
};

const stateDescriptions: Readonly<Record<ProviderConnectionViewV1["state"], string>> = {
  idle: "Confirm the email, then open Claude's official sign-in in a separate browser window.",
  requested: "Keep this page open. Claude's official sign-in window is being opened.",
  awaiting_sign_in: "Complete sign-in in Claude's browser window using the email below. This page will update after verification.",
  verifying: "Sign-in finished. Checking that Claude reports the account you selected before enabling monitoring.",
  connected: "Identity verified and monitoring enabled. Quota will appear after a successful scheduled reading.",
  wrong_account: "Claude reported a different identity from the selected email. Monitoring was not enabled by this attempt. Review the selected account before trying again.",
  expired: "The browser sign-in was not completed in time. Start a new connection when you are ready.",
  failed: "The connection did not finish. Check connection status and try again.",
  cancelled: "This sign-in attempt was cancelled. You can start a new connection when you are ready.",
  setup_required: "Claude sign-in succeeded, but its first-use setup still needs attention. Monitoring has not started. Check status after completing Claude setup.",
};

function isEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

export function ClaudeConnectionPanel({
  account,
  onExpired,
  onProofUnavailable,
  onAccountReload,
}: Readonly<{
  account: AccountViewV1;
  onExpired: () => void;
  onProofUnavailable: () => void;
  onAccountReload: () => void;
}>) {
  const [connection, setConnection] = useState<ProviderConnectionViewV1 | null>(null);
  const [email, setEmail] = useState(() => isEmail(account.friendly_name) ? account.friendly_name.trim() : "");
  const [busy, setBusy] = useState(false);
  const [outcomeUnknown, setOutcomeUnknown] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reloadedFlow = useRef<string | null>(null);

  const accept = useCallback((result: ClientResult<ProviderConnectionViewV1>) => {
    if (!result.ok) {
      if (result.problem.code === "dashboard_authentication_required") onExpired();
      else if (result.problem.code === "csrf_validation_failed") onProofUnavailable();
      else if (result.problem.status === 412) {
        setError("The account changed. Its current version is being refreshed; review it before connecting again.");
        onAccountReload();
      } else if (result.problem.status === 409) {
        setError("Another connection is already in progress, or this account cannot be connected. Check its status before trying again.");
      } else setError("The connection request could not be completed. Check its status before trying again.");
      return;
    }
    setConnection(result.data);
    setError(null);
    setOutcomeUnknown(false);
    if (result.data.expected_email !== null) setEmail(result.data.expected_email);
    if (result.data.state === "connected" && result.data.flow_id !== null && reloadedFlow.current !== result.data.flow_id) {
      reloadedFlow.current = result.data.flow_id;
      onAccountReload();
    }
  }, [onExpired, onProofUnavailable, onAccountReload]);

  const read = useCallback(async (signal?: AbortSignal) => {
    try {
      accept(await providers.connection(account.account_id, signal));
    } catch (failure) {
      if (failure instanceof DOMException && failure.name === "AbortError") return;
      setError("Connection status is unavailable. Check the local service, then check status again.");
    }
  }, [account.account_id, accept]);

  useEffect(() => {
    const controller = new AbortController();
    void read(controller.signal);
    return () => controller.abort();
  }, [read]);

  useEffect(() => {
    if (connection === null || !activeStates.has(connection.state) || busy) return;
    const controller = new AbortController();
    let inFlight = false;
    const timer = window.setInterval(() => {
      if (inFlight) return;
      inFlight = true;
      void read(controller.signal).finally(() => { inFlight = false; });
    }, 2_000);
    return () => {
      window.clearInterval(timer);
      controller.abort();
    };
  }, [connection, busy, read]);

  async function change(operation: () => Promise<ClientResult<ProviderConnectionViewV1>>) {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      accept(await operation());
    } catch (failure) {
      if (failure instanceof CsrfUnavailableError) onProofUnavailable();
      else {
        setOutcomeUnknown(true);
        setError("The connection request has an unknown outcome. Check connection status before starting again.");
      }
    } finally {
      setBusy(false);
    }
  }

  function connect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!connection?.can_connect || activeStates.has(connection.state) || !isEmail(email) || busy || outcomeUnknown) return;
    void change(() => providers.connect(account, email.trim()));
  }

  async function checkStatus() {
    if (busy) return;
    setBusy(true);
    try {
      await read();
    } finally {
      setBusy(false);
    }
  }

  const active = connection !== null && activeStates.has(connection.state);
  const recovery = account.lifecycle === "active";
  const isConnectedReceipt = connection !== null && connection.state === "connected" && connection.flow_id !== null;
  const isMonitoringOn = account.is_effective_monitoring_enabled || (account.lifecycle === "pending" && isConnectedReceipt);
  const isRecoveryEmailFixed = recovery && connection !== null && connection.expected_email !== null && connection.state !== "wrong_account";
  const needsAttention = connection?.flow_id !== null && connection !== null && ["wrong_account", "failed", "expired", "setup_required"].includes(connection.state);
  const label = connection === null ? "Checking connection status" : stateLabels[connection.state];
  const description = connection === null
    ? "Reading this account's connection status from the local service."
    : isConnectedReceipt && !isMonitoringOn
      ? "Claude identity was verified by this connection. Monitoring is currently off."
      : recovery && connection.can_connect
        ? "Confirm the email of the same previously verified Claude identity, then finish connecting this account to monitoring. This continues the existing profile without a new sign-in."
        : stateDescriptions[connection.state];

  // Existing active/default profiles only expose a control for an eligible,
  // interrupted dashboard connection reported by the versioned API.
  if (recovery && !connection?.can_connect && !active && !needsAttention && !isConnectedReceipt) return null;

  if (isConnectedReceipt) return (
    <section className="claude-connection claude-connection-compact" aria-label="Claude connection" aria-busy={busy}>
      <div className="claude-connection-summary">
        <div className="claude-connection-summary-status" role="status" aria-live="polite">
          <strong><span className="claude-connected-mark" aria-hidden="true">✓</span><span>Claude connected</span></strong>
          <span className={`state-chip ${isMonitoringOn ? "state-live" : "state-unavailable"}`}>Monitoring {isMonitoringOn ? "on" : "off"}</span>
        </div>
        <button type="button" className="quiet-button" aria-label="Check status for Claude connection" disabled={busy} onClick={() => { void checkStatus(); }}>Check status</button>
      </div>
      {error !== null && <p className="form-status" role="alert">{error}</p>}
    </section>
  );

  return (
    <section className="claude-connection" aria-labelledby="claude-connection-title" aria-busy={busy}>
      <div className="claude-connection-heading">
        <div><p className="panel-code">ACCOUNT CONNECTION</p><h2 id="claude-connection-title">{isConnectedReceipt ? "Claude connection" : recovery ? "Finish Claude connection" : "Connect Claude"}</h2></div>
        <span className={`state-chip ${isMonitoringOn ? "state-live" : "state-unavailable"}`}>Monitoring {isMonitoringOn ? "on" : "off"}</span>
      </div>
      <div className="claude-connection-status" role="status" aria-live="polite">
        <strong>{label}</strong>
        <p>{description}</p>
      </div>
      {!isConnectedReceipt && <form className="claude-connection-form" onSubmit={connect}>
        <div>
          <label htmlFor="claude-connection-email">Claude account email</label>
          <input id="claude-connection-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" maxLength={256} required disabled={busy || active || isRecoveryEmailFixed || connection?.state === "connected"} aria-describedby="claude-connection-email-help" />
          <p id="claude-connection-email-help">{recovery ? "Confirm the email used for the previously verified Claude account. The service will check it again before continuing." : "Sign in with this email in Claude. Enter passwords and verification codes only on Claude's official page."}</p>
        </div>
        <button type="submit" disabled={busy || active || outcomeUnknown || !connection?.can_connect || !isEmail(email)}>{recovery ? "Finish connection" : "Connect Claude"}</button>
      </form>}
      <div className="claude-connection-actions">
        {active && connection.flow_id !== null && <button type="button" className="quiet-button" disabled={busy} onClick={() => {
          const flowId = connection.flow_id;
          if (flowId !== null) void change(() => providers.cancelConnection(account.account_id, flowId));
        }}>Cancel connection</button>}
        <button type="button" className="quiet-button" disabled={busy} onClick={() => { void checkStatus(); }}>Check connection status</button>
        {active && connection.expires_at !== null && <span>Sign-in expires {new Date(connection.expires_at).toLocaleTimeString()}</span>}
      </div>
      {connection !== null && !connection.can_connect && !active && connection.state === "idle" && <p className="claude-connection-note">This account cannot start a connection right now. Finish any other sign-in, then check status.</p>}
      {error !== null && <p className="form-status" role="alert">{error}</p>}
    </section>
  );
}
