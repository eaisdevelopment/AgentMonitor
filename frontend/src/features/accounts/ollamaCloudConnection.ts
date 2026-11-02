/** Owner-readable copy for the versioned Ollama cloud connection status. */
export type OllamaCloudConnectionCopy = Readonly<{ title: string; description: string }>;

export function ollamaMonitoringCopy(state: string, reason: string): string {
  if (state === "off") return "Monitoring is off";
  if (state === "scheduled") return "Monitoring scheduled";
  if (state === "reading") return "Reading now";
  if (reason === "credential_unavailable") return "Waiting for a credential";
  if (reason === "source_not_admitted") return "Monitoring status unavailable";
  if (reason === "schedule_not_registered") return "Waiting for scheduling";
  return "Monitoring unavailable";
}

export function ollamaCloudConnectionCopy(state: string): OllamaCloudConnectionCopy {
  switch (state) {
    case "not_configured":
      return { title: "Ollama cloud not connected", description: "No credential is configured for this account." };
    case "pending":
      return { title: "Waiting for a connection check", description: "The balance check has not completed yet." };
    case "stale":
      return { title: "Last connection check is stale", description: "The last successful reading is too old to confirm current access." };
    case "retry_available":
      return { title: "Last connection check failed", description: "The service was temporarily unavailable. Check the connection again when ready." };
    case "access_valid_owner_confirmed":
    case "access_valid_identity_unresolved":
      return { title: "Ollama cloud access confirmed", description: "Ollama accepted the connection. The account name and organization are the ones you provided; Ollama has not verified them." };
    case "unauthorized":
      return { title: "Ollama rejected the connection", description: "Review the credential for this account and reconnect it locally." };
    case "rate_limited":
      return { title: "Ollama temporarily limited requests", description: "The next check must wait until Ollama's limit allows it." };
    case "store_locked":
      return { title: "Credential store locked", description: "Unlock the local credential store on the AgentMonitor computer, then check the connection again." };
    case "authorization_unavailable":
      return { title: "Credential unavailable", description: "Unlock the local credential store or reconnect the account on the AgentMonitor computer." };
    default:
      return { title: "Connection status unavailable", description: "AgentMonitor cannot currently confirm this account's connection." };
  }
}

/** Show an action only when the server explicitly permits a known retry state. */
export function ollamaCloudConnectionAction(state: string, canVerify: boolean): string | null {
  if (!canVerify) return null;
  if (["pending", "stale", "retry_available", "unauthorized", "rate_limited", "store_locked", "authorization_unavailable"].includes(state)) return "Check connection";
  return null;
}
