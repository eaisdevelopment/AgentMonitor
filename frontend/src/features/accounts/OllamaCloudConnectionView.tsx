import { useCallback, useEffect, useState } from "react";

import { CsrfUnavailableError, providers, type AccountViewV1, type OllamaCloudConnectionStatusV1 } from "../../shared/api/client";
import { OllamaCloudConnectionPanel } from "./OllamaCloudConnectionPanel";

/** Account-scoped versioned API view; credentials are never entered here. */
export function OllamaCloudConnectionView({ account, onExpired, onProofUnavailable, onAccountReload }: Readonly<{
  account: AccountViewV1;
  onExpired: () => void;
  onProofUnavailable: () => void;
  onAccountReload: () => void;
}>) {
  const [connection, setConnection] = useState<OllamaCloudConnectionStatusV1 | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (signal?: AbortSignal) => {
    try {
      const result = await providers.ollamaCloudConnection(account.account_id, signal);
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        else setError("Connection status is unavailable.");
        return;
      }
      setConnection(result.data);
      setError(null);
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === "AbortError") return;
      setError("Connection status is unavailable.");
    }
  }, [account.account_id, onExpired]);

  useEffect(() => {
    const controller = new AbortController();
    void refresh(controller.signal);
    return () => controller.abort();
  }, [refresh]);

  useEffect(() => {
    if (connection?.state !== "pending" || connection.can_verify) return;
    const timer = window.setTimeout(() => { void refresh(); }, 15000);
    return () => window.clearTimeout(timer);
  }, [connection, refresh]);

  const verify = async () => {
    if (busy || !connection?.can_verify) return;
    setBusy(true);
    try {
      const result = await providers.initiateOllamaCloudConnection(account);
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        else if (result.problem.code === "csrf_validation_failed") onProofUnavailable();
        else if (result.problem.status === 412) {
          setError("The account changed. Its current version is being refreshed.");
          onAccountReload();
        } else setError("The connection check could not be started.");
        return;
      }
      setConnection(result.data);
      setError(null);
      onAccountReload();
    } catch (cause) {
      if (cause instanceof CsrfUnavailableError) onProofUnavailable();
      else setError("The connection check could not be started.");
    } finally {
      setBusy(false);
    }
  };

  if (error) return <section className="account-secondary" aria-label="Ollama cloud connection"><h2>Connection status unavailable</h2><p>{error}</p><button type="button" className="quiet-button" onClick={() => void refresh()}>Try again</button></section>;
  if (!connection) return <section className="account-secondary" aria-label="Ollama cloud connection"><p>Checking connection status…</p></section>;
  return <OllamaCloudConnectionPanel state={connection.state} canVerify={connection.can_verify} busy={busy} checkedAt={connection.observed_at} onVerify={() => void verify()} />;
}
