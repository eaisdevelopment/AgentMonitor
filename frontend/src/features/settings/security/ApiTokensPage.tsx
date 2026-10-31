import { useEffect, useRef, useState, type FormEvent } from "react";

import {
  CsrfUnavailableError,
  iam,
  safeProblemMessage,
  type ApiTokenCredentialIssueV1,
  type ApiTokenPageV1,
  type ApiTokenSummaryV1,
  type SafeProblemV1,
} from "../../../shared/api/client";

type ApiTokensPageProps = Readonly<{
  onExpired: () => void;
  onProofUnavailable: () => void;
}>;

const AVAILABLE_SCOPES = [
  { value: "read:diagnostics", label: "Read diagnostics", description: "Read IAM security events in M2." },
  { value: "write:tokens", label: "Manage API tokens", description: "List, issue, rotate, and revoke API tokens, subject to this token’s own scopes and expiry." },
  { value: "write:accounts", label: "Manage accounts", description: "Create and update account and organization records." },
  { value: "read:alerts", label: "Read alerts", description: "Read alerts, rules, and notifications." },
  { value: "write:alerts", label: "Manage alerts", description: "Create rules and update alert state." },
] as const;

function OneTimeTokenDialog({ issue, onClose }: Readonly<{
  issue: ApiTokenCredentialIssueV1;
  onClose: () => void;
}>) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [copyMessage, setCopyMessage] = useState<string | null>(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) dialog.showModal();
    return () => { if (dialog?.open) dialog.close(); };
  }, []);

  async function copy() {
    try {
      await navigator.clipboard.writeText(issue.bearer_credential);
      setCopyMessage("Copied after your explicit request. Clear your clipboard when finished.");
    } catch {
      setCopyMessage("Clipboard access was denied. Select and copy the credential manually.");
    }
  }

  return (
    <dialog ref={dialogRef} aria-labelledby="one-time-title" onClose={onClose} className="secret-dialog">
      <h2 id="one-time-title">One-time API token</h2>
      <p>This credential is shown once. Store it securely now; AgentMonitor cannot display it again.</p>
      <label htmlFor="issued-credential">New API token credential</label>
      <input id="issued-credential" value={issue.bearer_credential} readOnly autoComplete="off" onFocus={(event) => event.currentTarget.select()} />
      {copyMessage && <p role="status">{copyMessage}</p>}
      <div className="dialog-actions">
        <button type="button" onClick={() => { void copy(); }}>Copy token</button>
        <button type="button" className="quiet-button" onClick={onClose}>Done</button>
      </div>
    </dialog>
  );
}

function tokenStateLabel(state: string): string {
  switch (state) {
    case "active": return "Active";
    case "expired": return "Expired";
    case "revoked": return "Revoked";
    case "rotated": return "Rotated";
    default: return "Unknown";
  }
}

export function ApiTokensPage({ onExpired, onProofUnavailable }: ApiTokensPageProps) {
  const [page, setPage] = useState<ApiTokenPageV1 | null>(null);
  const [isLoading, setLoading] = useState(true);
  const [isBusy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [issue, setIssue] = useState<ApiTokenCredentialIssueV1 | null>(null);
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<readonly string[]>([]);
  const [lifetimeSeconds, setLifetimeSeconds] = useState(7_776_000);

  function displayProblem(problem: SafeProblemV1) {
    if (problem.code === "dashboard_authentication_required") {
      setIssue(null);
      setPage(null);
      onExpired();
    } else if (problem.code === "csrf_validation_failed") {
      onProofUnavailable();
    } else {
      setMessage(safeProblemMessage(problem));
    }
  }

  async function refresh(cursor?: string, preserveMessage = false) {
    try {
      const result = await iam.listTokens(cursor);
      if (!result.ok) {
        displayProblem(result.problem);
        return;
      }
      setPage((current) => cursor && current
        ? { items: [...current.items, ...result.data.items], page: result.data.page }
        : result.data);
      if (!preserveMessage) setMessage(null);
    } catch {
      setMessage("The local service is unavailable. Try again.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, []);

  function toggleScope(value: string, checked: boolean) {
    setScopes((current) => checked
      ? [...current, value]
      : current.filter((existing) => existing !== value));
  }

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim() || scopes.length === 0 || isBusy) {
      setMessage("Enter a name and select at least one scope.");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const result = await iam.createToken(name.trim(), scopes, lifetimeSeconds);
      if (!result.ok) {
        displayProblem(result.problem);
        return;
      }
      setIssue(result.data);
      setName("");
      setScopes([]);
      await refresh();
    } catch (error) {
      if (error instanceof CsrfUnavailableError) onProofUnavailable();
      else {
        await refresh(undefined, true);
        setMessage("Token issuance outcome is unknown. The server may have committed it, but its one-time credential cannot be recovered. Review refreshed summaries before taking another action.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function rotate(existing: ApiTokenSummaryV1) {
    if (!window.confirm(
      `Rotate ${existing.name}? Current scopes: ${existing.scopes.join(", ")}. ` +
      `Current expiry: ${new Date(existing.expires_at).toLocaleString()}. ` +
      "The replacement keeps these scopes and the predecessor credential will stop working.",
    )) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await iam.rotateToken(existing);
      if (!result.ok) {
        displayProblem(result.problem);
        return;
      }
      setIssue(result.data);
      await refresh();
    } catch (error) {
      if (error instanceof CsrfUnavailableError) onProofUnavailable();
      else {
        await refresh(undefined, true);
        setMessage("Token rotation outcome is unknown. The server may have committed it, but its one-time credential cannot be recovered. Review refreshed summaries before taking another action.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function revoke(existing: ApiTokenSummaryV1) {
    if (!window.confirm(`Revoke ${existing.name} (${existing.safe_prefix})? This cannot be undone.`)) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await iam.revokeToken(existing);
      if (!result.ok) {
        displayProblem(result.problem);
        return;
      }
      await refresh();
    } catch (error) {
      if (error instanceof CsrfUnavailableError) onProofUnavailable();
      else {
        await refresh(undefined, true);
        setMessage("Token revocation outcome is unknown. Review refreshed summaries before taking another action.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="token-settings">
      <section aria-labelledby="page-title">
        <p className="eyebrow">Security settings</p>
        <h1 id="page-title" tabIndex={-1}>API tokens</h1>
        <p>Create narrowly scoped bearer credentials for API clients. Dashboard sign-in uses its own browser session.</p>
        <p>For interactive API exploration, open authenticated <a href="/docs">Swagger UI</a> and paste a scoped token manually. Swagger authorization persistence is disabled; AgentMonitor never transfers or stores a token for Swagger.</p>
      </section>
      {message && <p className="form-status" role="alert">{message}</p>}
      <div className="settings-grid">
        <section aria-labelledby="issue-title">
          <h2 id="issue-title">Issue a token</h2>
          <form className="token-form" onSubmit={(event) => { void create(event); }}>
            <label htmlFor="token-name">Token name</label>
            <input id="token-name" value={name} maxLength={80} required onChange={(event) => setName(event.target.value)} />
            <fieldset>
              <legend>Scopes</legend>
              {AVAILABLE_SCOPES.map((scope) => (
                <label key={scope.value} className="scope-choice">
                  <input type="checkbox" checked={scopes.includes(scope.value)} onChange={(event) => toggleScope(scope.value, event.target.checked)} />
                  <span><strong>{scope.label}</strong><small>{scope.description}</small></span>
                </label>
              ))}
            </fieldset>
            <label htmlFor="token-lifetime">Expires after</label>
            <select id="token-lifetime" value={lifetimeSeconds} onChange={(event) => setLifetimeSeconds(Number(event.target.value))}>
              <option value={3600}>1 hour</option>
              <option value={86400}>1 day</option>
              <option value={7_776_000}>90 days</option>
              <option value={31_536_000}>1 year</option>
            </select>
            <button type="submit" disabled={isBusy}>Create token</button>
          </form>
        </section>
        <section aria-labelledby="issued-title">
          <h2 id="issued-title">Issued tokens</h2>
          <button type="button" className="quiet-button" disabled={isBusy || isLoading} onClick={() => { setLoading(true); void refresh(); }}>Refresh summaries</button>
          {isLoading ? <p role="status">Loading token summaries…</p> : page === null ? (
            <p role="alert">Token summaries are unavailable.</p>
          ) : page.items.length === 0 ? (
            <p>No API tokens have been issued.</p>
          ) : (
            <div className="table-scroll">
              <table>
                <caption>Current and historical API-token summaries; credentials are never listed.</caption>
                <thead><tr><th scope="col">Name</th><th scope="col">State</th><th scope="col">Scopes</th><th scope="col">Expires</th><th scope="col">Actions</th></tr></thead>
                <tbody>{page.items.map((token) => (
                  <tr key={token.api_token_id}>
                    <th scope="row">{token.name}<small>Prefix {token.safe_prefix}</small></th>
                    <td>{tokenStateLabel(token.state)}</td>
                    <td>{token.scopes.join(", ")}</td>
                    <td><time dateTime={token.expires_at}>{new Date(token.expires_at).toLocaleString()}</time></td>
                    <td>{token.state === "active" && <div className="row-actions">
                      <button type="button" className="quiet-button" disabled={isBusy} onClick={() => { void rotate(token); }}>Rotate</button>
                      <button type="button" className="quiet-button" disabled={isBusy} onClick={() => { void revoke(token); }}>Revoke</button>
                    </div>}</td>
                  </tr>
                ))}</tbody>
              </table>
              {page.page.has_more && page.page.next_cursor && (
                <button type="button" onClick={() => { void refresh(page.page.next_cursor!); }}>Load more tokens</button>
              )}
            </div>
          )}
        </section>
      </div>
      {issue && <OneTimeTokenDialog issue={issue} onClose={() => setIssue(null)} />}
    </div>
  );
}
