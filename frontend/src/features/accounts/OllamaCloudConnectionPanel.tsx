import { ollamaCloudConnectionAction, ollamaCloudConnectionCopy, ollamaMonitoringCopy } from "./ollamaCloudConnection";

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
  const copy = ollamaCloudConnectionCopy(state);
  const action = ollamaCloudConnectionAction(state, canVerify);
  return <section className="account-secondary" aria-label="Ollama cloud connection">
    <h2>{copy.title}</h2>
    <p>{copy.description}</p>
    <p>{ollamaMonitoringCopy(monitoringState, monitoringReason)}</p>
    {checkedAt !== null && ["stale", "retry_available", "access_valid_owner_confirmed", "access_valid_identity_unresolved"].includes(state) && <p>Last check: {new Date(checkedAt).toLocaleString()}</p>}
    {action !== null && <button type="button" disabled={busy} onClick={onVerify}>{action}</button>}
  </section>;
}
