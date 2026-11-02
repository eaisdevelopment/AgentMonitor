import { useCallback, useEffect, useRef, useState } from "react";

import { CsrfUnavailableError, providers, type AccountViewV1, type OllamaCloudConnectionStatusV1 } from "../../shared/api/client";
import { OllamaCloudConnectionPanel } from "./OllamaCloudConnectionPanel";

/** Account-scoped versioned API view; credentials are never entered here. */
export function OllamaCloudConnectionView({ account, onExpired, onProofUnavailable, onAccountReload }: Readonly<{
  account: AccountViewV1;
  onExpired: () => void;
  onProofUnavailable: () => void;
  onAccountReload: () => void;
}>) {
  const accountKey = `${account.account_id}:${account.record_version}`;
  const expiredHandler = useRef(onExpired);
  expiredHandler.current = onExpired;
  const [connectionState, setConnectionState] = useState<{ accountId: string; value: OllamaCloudConnectionStatusV1 } | null>(null);
  const [busyAccount, setBusyAccount] = useState<string | null>(null);
  const [errorState, setErrorState] = useState<{ accountId: string; message: string } | null>(null);
  const currentAccount = useRef(accountKey);
  currentAccount.current = accountKey;
  const requestGeneration = useRef(0);
  const refreshController = useRef<AbortController | null>(null);
  const verifyingAccount = useRef<string | null>(null);
  const connection = connectionState?.accountId === accountKey ? connectionState.value : null;
  const error = errorState?.accountId === accountKey ? errorState.message : null;
  const busy = busyAccount === accountKey;

  const refresh = useCallback(async () => {
    if (verifyingAccount.current === accountKey) return;
    refreshController.current?.abort();
    const controller = new AbortController();
    refreshController.current = controller;
    const generation = ++requestGeneration.current;
    const isCurrent = () => !controller.signal.aborted && generation === requestGeneration.current && currentAccount.current === accountKey;
    try {
      const result = await providers.ollamaCloudConnection(account.account_id, controller.signal);
      if (!isCurrent()) return;
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") expiredHandler.current();
        else setErrorState({ accountId: accountKey, message: "Connection status is unavailable." });
        return;
      }
      if (result.data.account_id !== account.account_id) {
        setErrorState({ accountId: accountKey, message: "Connection status did not match this account." });
        return;
      }
      setConnectionState({ accountId: accountKey, value: result.data });
      setErrorState(null);
    } catch (cause) {
      if (!isCurrent() || (cause instanceof DOMException && cause.name === "AbortError")) return;
      setErrorState({ accountId: accountKey, message: "Connection status is unavailable." });
    }
  }, [account.account_id, accountKey]);

  useEffect(() => {
    void refresh();
    return () => {
      requestGeneration.current++;
      refreshController.current?.abort();
      refreshController.current = null;
    };
  }, [refresh]);

  useEffect(() => {
    const onReturn = () => { if (document.visibilityState === "visible") void refresh(); };
    window.addEventListener("focus", onReturn);
    document.addEventListener("visibilitychange", onReturn);
    return () => { window.removeEventListener("focus", onReturn); document.removeEventListener("visibilitychange", onReturn); };
  }, [refresh]);

  useEffect(() => {
    if (busy || !connection || connection.can_verify || !["not_configured", "pending", "stale", "retry_available", "rate_limited"].includes(connection.state)) return;
    const timer = window.setTimeout(() => { void refresh(); }, 15000);
    return () => window.clearTimeout(timer);
  }, [busy, connection, refresh]);

  const verify = async () => {
    if (busy || !connection?.can_verify) return;
    refreshController.current?.abort();
    const generation = ++requestGeneration.current;
    const isCurrent = () => generation === requestGeneration.current && currentAccount.current === accountKey;
    verifyingAccount.current = accountKey;
    setBusyAccount(accountKey);
    try {
      const result = await providers.initiateOllamaCloudConnection(account);
      if (!isCurrent()) return;
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") expiredHandler.current();
        else if (result.problem.code === "csrf_validation_failed") onProofUnavailable();
        else if (result.problem.status === 412) {
          setErrorState({ accountId: accountKey, message: "The account changed. Its current version is being refreshed." });
          onAccountReload();
        } else setErrorState({ accountId: accountKey, message: "The connection check could not be started." });
        return;
      }
      if (result.data.account_id !== account.account_id) {
        setErrorState({ accountId: accountKey, message: "Connection status did not match this account." });
        return;
      }
      setConnectionState({ accountId: accountKey, value: result.data });
      setErrorState(null);
      onAccountReload();
    } catch (cause) {
      if (!isCurrent()) return;
      if (cause instanceof CsrfUnavailableError) onProofUnavailable();
      else setErrorState({ accountId: accountKey, message: "The connection check could not be started." });
    } finally {
      if (verifyingAccount.current === accountKey) verifyingAccount.current = null;
      setBusyAccount((previous) => previous === accountKey ? null : previous);
    }
  };

  if (error) return <section className="account-secondary" aria-label="Ollama cloud connection"><h2>Connection status unavailable</h2><p>{error}</p><button type="button" className="quiet-button" onClick={() => void refresh()}>Try again</button></section>;
  if (!connection) return <section className="account-secondary" aria-label="Ollama cloud connection"><p>Checking connection status…</p></section>;
  return <OllamaCloudConnectionPanel state={connection.state} canVerify={connection.can_verify} busy={busy} checkedAt={connection.observed_at} monitoringState={connection.monitoring_state} monitoringReason={connection.monitoring_reason} onVerify={() => void verify()} />;
}
