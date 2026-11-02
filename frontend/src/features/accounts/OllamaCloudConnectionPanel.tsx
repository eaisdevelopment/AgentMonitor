import { ollamaCloudConnectionAction, ollamaCloudConnectionCopy } from "./ollamaCloudConnection";

type Props = Readonly<{
  state: string;
  canVerify: boolean;
  busy: boolean;
  onVerify: () => void;
}>;

/** Renders only a server-reported status; it never accepts a credential. */
export function OllamaCloudConnectionPanel({ state, canVerify, busy, onVerify }: Props) {
  const copy = ollamaCloudConnectionCopy(state);
  const action = ollamaCloudConnectionAction(state, canVerify);
  return <section className="account-secondary" aria-label="Ollama cloud connection">
    <h2>{copy.title}</h2>
    <p>{copy.description}</p>
    {action !== null && <button type="button" disabled={busy} onClick={onVerify}>{action}</button>}
  </section>;
}
