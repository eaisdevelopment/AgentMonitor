import { useEffect, useRef, useState, type FormEvent } from "react";

import { CsrfUnavailableError, registry, type AccountBillingConnectionsV1, type BillingConnectionViewV1 } from "../../shared/api/client";

const unknownOutcome = "The scope change outcome is unknown. Refresh billing status before another change.";

export function BillingScopeControls({ accountStatus, connection, disabled, refreshRevision, statusReadRevision, onBusyChange, onExpired, onProofUnavailable, onChanged, onScopeMutation }: Readonly<{
  accountStatus: AccountBillingConnectionsV1;
  connection: BillingConnectionViewV1;
  disabled: boolean;
  refreshRevision: number;
  statusReadRevision: number;
  onBusyChange: (busy: boolean) => void;
  onExpired: () => void;
  onProofUnavailable: () => void;
  onChanged: () => void;
  onScopeMutation?: () => void;
}>) {
  const [scope, setScope] = useState(connection.scope_id ?? "");
  const [busy, setBusy] = useState(false);
  const [blockedRevision, setBlockedRevision] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const mounted = useRef(false);
  const submitting = useRef(false);
  const latestRevision = useRef(refreshRevision);
  latestRevision.current = refreshRevision;
  const callbacks = useRef({ onBusyChange, onExpired, onProofUnavailable, onChanged, onScopeMutation });
  callbacks.current = { onBusyChange, onExpired, onProofUnavailable, onChanged, onScopeMutation };

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      if (submitting.current) callbacks.current.onBusyChange(false);
    };
  }, []);
  useEffect(() => { setScope(connection.scope_id ?? ""); }, [connection.scope_id, connection.record_version]);
  useEffect(() => {
    // Only a read started after this outcome can reconcile it. An earlier GET
    // finishing late must not re-enable a mutation with uncertain authority.
    if (blockedRevision !== null && statusReadRevision > blockedRevision) {
      setBlockedRevision(null);
      setScope(connection.scope_id ?? "");
      setMessage((current) => current === "Scope saved. Check connection before enabling API monitoring." ? current : null);
    }
  }, [blockedRevision, statusReadRevision, connection.scope_id]);

  const normalizedScope = scope.trim() || null;
  const unavailable = !["pending", "active"].includes(accountStatus.account_lifecycle) || connection.lifecycle === "disconnected";
  const blocked = disabled || busy || blockedRevision !== null || unavailable;
  const unchanged = normalizedScope === connection.scope_id;
  const inputId = `billing-scope-change-${connection.resource_id}`;
  const helpId = `${inputId}-help`;

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (blocked || unchanged || submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setMessage(null);
    callbacks.current.onBusyChange(true);
    callbacks.current.onScopeMutation?.();
    try {
      const result = await registry.changeBillingScope(accountStatus, connection, normalizedScope);
      if (!mounted.current) return;
      setBlockedRevision(latestRevision.current);
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") callbacks.current.onExpired();
        setMessage(result.problem.status >= 500 ? unknownOutcome : "The scope change was not confirmed. Refresh billing status before another change.");
        return;
      }
      const saved = result.data;
      if (saved.account_id !== accountStatus.account_id || saved.account_id !== connection.account_id
        || saved.resource_id !== connection.resource_id || saved.provider_key !== connection.provider_key
        || saved.provider_key !== accountStatus.provider_key || saved.scope_id !== normalizedScope
        || saved.scope_generation !== connection.scope_generation + 1
        || saved.record_version <= connection.record_version || saved.registry_revision <= connection.registry_revision
        || saved.scope_evidence !== (normalizedScope === null ? "unresolved" : "owner_asserted")
        || saved.lifecycle !== "pending" || saved.monitoring_preference !== "disabled") {
        setMessage(unknownOutcome);
        return;
      }
      setMessage("Scope saved. Check connection before enabling API monitoring.");
      callbacks.current.onChanged();
    } catch (error) {
      if (!mounted.current) return;
      if (error instanceof CsrfUnavailableError) {
        setMessage("Refresh your dashboard session before changing billing scope.");
        callbacks.current.onProofUnavailable();
      } else {
        setBlockedRevision(latestRevision.current);
        setMessage(unknownOutcome);
      }
    } finally {
      submitting.current = false;
      if (mounted.current) {
        callbacks.current.onScopeMutation?.();
        setBusy(false);
        callbacks.current.onBusyChange(false);
      }
    }
  }

  return <details className="account-secondary" data-billing-scope="true">
    <summary>Change provider billing scope</summary>
    <p id={helpId}>Saving a different scope stops API monitoring and unlinks the old billing pool. Stored history is kept. This owner setting does not verify provider access. Enter a nonsecret provider organization or workspace identifier, or leave blank when unknown.</p>
    <form onSubmit={(event) => { void save(event); }} aria-busy={busy}>
      <label htmlFor={inputId}>New provider billing scope</label>
      <input id={inputId} value={scope} onChange={(event) => setScope(event.target.value)} maxLength={128} pattern="[A-Za-z0-9][A-Za-z0-9_.:\-]*" autoComplete="off" disabled={blocked} aria-describedby={helpId} />
      <button type="submit" disabled={blocked || unchanged}>Save scope</button>
    </form>
    {unavailable && <p>Restore or reconnect this account before changing its billing scope.</p>}
    {message !== null && <p role="status">{message}</p>}
  </details>;
}
