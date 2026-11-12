import { useEffect, useRef, useState } from "react";

import { CsrfUnavailableError, registry, type AccountBillingConnectionsV1, type BillingConnectionViewV1 } from "../../shared/api/client";

const unknownOutcome = "The reconnect outcome is unknown. Refresh billing status before trying again.";
const success = "API billing reconnected. Set up a local key and check connection before enabling monitoring.";

export function BillingReconnectControl({ accountStatus, connection, disabled, refreshRevision, statusReadRevision, onBusyChange, onExpired, onProofUnavailable, onChanged, onScopeMutation }: Readonly<{
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
  const [busy, setBusy] = useState(false);
  const [blockedRevision, setBlockedRevision] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const mounted = useRef(false);
  const submitting = useRef(false);
  const latestRevision = useRef(refreshRevision);
  latestRevision.current = refreshRevision;
  const authority = JSON.stringify([accountStatus.account_id, accountStatus.account_record_version,
    accountStatus.account_lifecycle, connection.resource_id, connection.record_version, connection.scope_generation, connection.lifecycle]);
  const currentAuthority = useRef(authority);
  currentAuthority.current = authority;
  const previousLifecycle = useRef(connection.lifecycle);
  const callbacks = useRef({ onBusyChange, onExpired, onProofUnavailable, onChanged, onScopeMutation });
  callbacks.current = { onBusyChange, onExpired, onProofUnavailable, onChanged, onScopeMutation };

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      if (submitting.current) callbacks.current.onBusyChange(false);
    };
  }, []);
  useEffect(() => {
    if (blockedRevision !== null && statusReadRevision > blockedRevision) {
      setBlockedRevision(null);
      setMessage(current => current === success && connection.lifecycle === "pending" ? current : null);
    }
    if (previousLifecycle.current !== "disconnected" && connection.lifecycle === "disconnected") {
      setMessage(current => current === success ? null : current);
    }
    previousLifecycle.current = connection.lifecycle;
  }, [blockedRevision, statusReadRevision, connection.lifecycle]);

  const disconnected = connection.lifecycle === "disconnected";
  const accountUnavailable = !["pending", "active"].includes(accountStatus.account_lifecycle);
  const blocked = disabled || busy || blockedRevision !== null || accountUnavailable || !disconnected;

  async function reconnect() {
    if (blocked || submitting.current || accountStatus.account_id !== connection.account_id || accountStatus.provider_key !== connection.provider_key) return;
    submitting.current = true;
    setBusy(true);
    setMessage(null);
    callbacks.current.onBusyChange(true);
    callbacks.current.onScopeMutation?.();
    try {
      const result = await registry.reconnectBillingConnection(accountStatus, connection);
      if (!mounted.current) return;
      setBlockedRevision(latestRevision.current);
      if (currentAuthority.current !== authority) {
        setMessage("The account or connection changed. Refresh billing status before trying again.");
        return;
      }
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") callbacks.current.onExpired();
        setMessage(result.problem.status >= 500 ? unknownOutcome : "Reconnection was not confirmed. Refresh billing status before trying again.");
        return;
      }
      const saved = result.data;
      if (saved.account_id !== accountStatus.account_id || saved.resource_id !== connection.resource_id
        || saved.provider_key !== connection.provider_key || saved.scope_id !== connection.scope_id
        || saved.scope_generation !== connection.scope_generation || saved.scope_evidence !== connection.scope_evidence
        || saved.record_version !== connection.record_version + 1 || saved.registry_revision <= connection.registry_revision
        || saved.lifecycle !== "pending" || saved.monitoring_preference !== "disabled") {
        setMessage(unknownOutcome);
        return;
      }
      setMessage(success);
      callbacks.current.onChanged();
    } catch (error) {
      if (!mounted.current) return;
      if (error instanceof CsrfUnavailableError) {
        setMessage("Refresh your dashboard session before reconnecting API billing.");
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

  if (!disconnected && message === null) return null;
  return <div data-billing-reconnect={connection.resource_id} aria-busy={busy}>
    {disconnected && <>
      <p>Stored history is preserved. Reconnecting keeps this billing resource and scope, with monitoring off. Set up a local key and check connection again; old credentials and access checks are not reactivated.</p>
      {accountUnavailable && <p>{accountStatus.account_lifecycle === "archived" ? "Restore this account before reconnecting API billing." : "Enable or restore this account before reconnecting API billing."}</p>}
      <button type="button" disabled={blocked} onClick={() => { void reconnect(); }}>Reconnect API billing</button>
    </>}
    {message !== null && <p role="status">{message}</p>}
  </div>;
}
