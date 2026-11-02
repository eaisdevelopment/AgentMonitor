import { useState } from "react";

import { ollamaCloudConnectionAction, ollamaCloudConnectionCopy, ollamaLocalSetupCommand, ollamaMonitoringCopy } from "./ollamaCloudConnection";

type Props = Readonly<{
  state: string;
  canVerify: boolean;
  busy: boolean;
  checkedAt: string | null;
  monitoringState: string;
  monitoringReason: string;
  onVerify: () => void;
}>;

/** Renders only a server-reported status; it never accepts a credential. */
export function OllamaCloudConnectionPanel({ state, canVerify, busy, checkedAt, monitoringState, monitoringReason, onVerify }: Props) {
  const [copyStatus, setCopyStatus] = useState("");
  const copyCommand = async () => {
    try {
      if (!navigator.clipboard) throw new Error("clipboard unavailable");
      await navigator.clipboard.writeText(ollamaLocalSetupCommand);
      setCopyStatus("Command copied.");
    } catch {
      setCopyStatus("Select the command above to copy it.");
    }
  };
  const copy = ollamaCloudConnectionCopy(state);
  const action = ollamaCloudConnectionAction(state, canVerify);
  return <section className="account-secondary" aria-label="Ollama cloud connection">
    <h2>{copy.title}</h2>
    <p>{copy.description}</p>
    <details open={state === "not_configured"}>
      <summary>Set up or replace the local key</summary>
      <p>Run this command in a terminal on the AgentMonitor computer as the same Linux user that runs AgentMonitor. Select this account and enter the key at the hidden prompt.</p>
      <code className="ollama-setup-command">{ollamaLocalSetupCommand}</code>
      <button type="button" className="quiet-button" onClick={() => { void copyCommand(); }}>Copy setup command</button>
      {copyStatus && <p role="status">{copyStatus}</p>}
    </details>
    <p>{ollamaMonitoringCopy(monitoringState, monitoringReason)}</p>
    {checkedAt !== null && ["stale", "retry_available", "access_valid_owner_confirmed", "access_valid_identity_unresolved"].includes(state) && <p>Last check: {new Date(checkedAt).toLocaleString()}</p>}
    {action !== null && <button type="button" disabled={busy} onClick={onVerify}>{action}</button>}
  </section>;
}
