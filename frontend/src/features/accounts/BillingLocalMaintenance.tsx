import { useEffect, useRef, useState } from "react";

import type { AccountBillingConnectionsV1 } from "../../shared/api/client";

type Maintenance = NonNullable<AccountBillingConnectionsV1["local_maintenance"]>;

function LocalCommand({ action, command }: Readonly<{ action: "disconnect" | "cleanup"; command: string }>) {
  const [message, setMessage] = useState<string | null>(null);
  const [copying, setCopying] = useState(false);
  const mounted = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  async function copy() {
    setCopying(true);
    setMessage(null);
    try {
      if (navigator.clipboard === undefined) throw new Error("clipboard_unavailable");
      await navigator.clipboard.writeText(command);
      if (mounted.current) setMessage("Command copied. Run it on the computer hosting AgentMonitor.");
    } catch {
      if (mounted.current) setMessage("Clipboard unavailable. Select and copy the command above.");
    } finally {
      if (mounted.current) setCopying(false);
    }
  }

  return <div>
    <p>{action === "disconnect"
      ? "Disconnect stops API monitoring and retires this connection's local credentials. Stored history is preserved."
      : "Cleanup removes only recorded retired credential entries. It does not disconnect an active key or enable monitoring."}</p>
    <code className="ollama-setup-command" aria-label={`Local ${action} command`} tabIndex={0} onFocus={(event) => {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(event.currentTarget);
      selection?.removeAllRanges();
      selection?.addRange(range);
    }}>{command}</code>
    <button type="button" className="quiet-button" disabled={copying} onClick={() => { void copy(); }}>Copy {action} command</button>
    {message !== null && <p role="status">{message}</p>}
  </div>;
}

export function BillingLocalMaintenance({ maintenance }: Readonly<{ maintenance: Maintenance }>) {
  if (maintenance.disconnect_command === null && maintenance.cleanup_command === null) return null;
  return <details className="account-secondary" data-billing-maintenance="true">
    <summary>Disconnect or clean up local credentials</summary>
    <p>Run the selected command on <strong>{maintenance.host_label}</strong>, the computer hosting AgentMonitor, as the user running its service. These are local actions; they do not revoke the key at the provider.</p>
    {maintenance.disconnect_command !== null && <LocalCommand key={`disconnect:${maintenance.disconnect_command}`} action="disconnect" command={maintenance.disconnect_command} />}
    {maintenance.cleanup_command !== null && <LocalCommand key={`cleanup:${maintenance.cleanup_command}`} action="cleanup" command={maintenance.cleanup_command} />}
    <p>Stored history is preserved. After running a command, use Refresh billing status to read its actual outcome. Displaying or copying a command does not confirm that it ran or that cleanup succeeded.</p>
  </details>;
}
