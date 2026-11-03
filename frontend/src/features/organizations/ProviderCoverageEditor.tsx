import { useCallback, useEffect, useId, useState, type FormEvent } from "react";

import {
  CsrfUnavailableError, registry,
  type AccountViewV1, type OrganizationViewV1,
  type OrganizationCoverageResourceV1, type SetOrganizationCoverageInputV1,
} from "../../shared/api/client";

const reasons = {
  account_unavailable: "No account available",
  subscription_unavailable: "No subscription available",
  access_unavailable: "Access unavailable",
  owner_unavailable: "Account owner unavailable",
} as const;

type Outcome = SetOrganizationCoverageInputV1["outcome"];
type Reason = keyof typeof reasons;
type Props = Readonly<{
  organization: OrganizationViewV1;
  organizations: readonly OrganizationViewV1[];
  organizationsComplete: boolean;
  onExpired: () => void;
  onProofUnavailable: () => void;
}>;

/** Owner metadata only; saving never connects, polls, or duplicates an account. */
export function ProviderCoverageEditor(props: Props) {
  const [open, setOpen] = useState(false);
  return <details onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary>Provider coverage</summary>
    {open && <CoverageForm {...props} />}
  </details>;
}

function CoverageForm({ organization, organizations, organizationsComplete, onExpired, onProofUnavailable }: Props) {
  const id = useId();
  const [provider, setProvider] = useState("ollama");
  const [accounts, setAccounts] = useState<readonly AccountViewV1[]>([]);
  const [resource, setResource] = useState<OrganizationCoverageResourceV1 | null>(null);
  const [outcome, setOutcome] = useState<Outcome>("account");
  const [accountId, setAccountId] = useState("");
  const [reason, setReason] = useState<Reason | "">("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setResource(null);
    try {
      const coverage = await registry.coverage(organization.organization_id, provider, signal);
      if (!coverage.ok) {
        if (coverage.problem.code === "dashboard_authentication_required") onExpired();
        throw new Error("coverage_unavailable");
      }
      const collected: AccountViewV1[] = [];
      const cursors = new Set<string>();
      let cursor: string | undefined;
      for (;;) {
        const page = await registry.accounts(signal, cursor);
        if (!page.ok) {
          if (page.problem.code === "dashboard_authentication_required") onExpired();
          throw new Error("account_list_unavailable");
        }
        if (page.data.availability.state !== "available") throw new Error("account_list_incomplete");
        collected.push(...page.data.items);
        if (!page.data.page.has_more) break;
        const next = page.data.page.next_cursor;
        if (!next || cursors.has(next) || cursors.size >= 20) throw new Error("account_list_incomplete");
        cursors.add(next);
        cursor = next;
      }
      if (signal?.aborted) return false;
      setAccounts(collected);
      setResource(coverage.data);
      setOutcome(coverage.data.coverage?.outcome ?? "account");
      setAccountId(coverage.data.coverage?.account_id ?? "");
      setReason(coverage.data.coverage?.unavailable_reason ?? "");
      return true;
    } catch (error) {
      if (signal?.aborted) return false;
      if (error instanceof DOMException && error.name === "AbortError") return false;
      setMessage("Coverage or account choices could not be loaded. Refresh to try again.");
      return false;
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [organization.organization_id, provider, onExpired]);

  useEffect(() => {
    const controller = new AbortController();
    setMessage(null);
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const knownOrganization = (account: AccountViewV1) => organizations.find(item => item.organization_id === account.organization_id);
  const candidates = accounts.filter(account => account.provider_key === provider && account.lifecycle !== "archived"
    && knownOrganization(account)?.lifecycle === "active"
    && (outcome === "account" ? account.organization_id === organization.organization_id : account.organization_id !== organization.organization_id));
  const selected = candidates.find(account => account.account_id === accountId);
  const providers = [...new Set(["ollama", ...accounts.map(account => account.provider_key)])].sort();
  const recorded = accounts.find(account => account.account_id === resource?.coverage?.account_id);

  async function mutate(remove: boolean) {
    if (!resource || busy || loading) return;
    if (!remove && (outcome === "unavailable" ? !reason : !selected)) return;
    if (!remove && outcome === "shared" && !organizationsComplete) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = remove ? await registry.revokeCoverage(resource) : await registry.setCoverage(resource, {
        outcome,
        account_id: outcome === "unavailable" ? null : selected?.account_id ?? null,
        expected_account_record_version: outcome === "unavailable" ? null : selected?.record_version ?? null,
        unavailable_reason: outcome === "unavailable" && reason ? reason : null,
      });
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        else if (result.problem.code === "csrf_validation_failed") onProofUnavailable();
        else if (result.problem.status === 412 || result.problem.status === 409) {
          const refreshed = await load();
          setMessage(refreshed
            ? "The coverage or selected account changed. Review the refreshed choices before saving again."
            : "The change was rejected and current choices could not be loaded. Refresh before trying again.");
        } else setMessage("Coverage could not be saved. Refresh and try again.");
        return;
      }
      const refreshed = await load();
      const committed = remove ? "Coverage declaration removed. The account connection is unchanged." : "Coverage saved as an owner declaration.";
      setMessage(refreshed ? committed : `${committed} The updated view could not be loaded. Refresh to see it.`);
    } catch (error) {
      if (error instanceof CsrfUnavailableError) onProofUnavailable();
      else setMessage("The service is unavailable. Refresh to check whether the change was saved.");
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void mutate(false);
  }

  return <div>
    <p>Choose the account this organization uses, or record why access is unavailable.</p>
    <label htmlFor={`${id}-provider`}>Provider</label>
    <select id={`${id}-provider`} value={provider} disabled={busy || loading} onChange={event => setProvider(event.target.value)}>
      {providers.map(value => <option key={value} value={value}>{value === "ollama" ? "Ollama" : value === "claude" ? "Claude" : value === "codex" ? "Codex" : value}</option>)}
    </select>
    {loading && <p role="status">Reading coverage and account choices…</p>}
    {!loading && resource && <>
      {resource.coverage ? <p>
        Owner declared · {resource.coverage.invalidated_at ? `Needs review: ${resource.coverage.invalidation_reason?.replaceAll("_", " ")}` : "Current declaration"}
        {recorded && <> · <a href={`/accounts/${recorded.account_id}`}>{recorded.friendly_name}</a></>}
        {resource.coverage.unavailable_reason && <> · {reasons[resource.coverage.unavailable_reason]}</>}
      </p> : <p>No coverage declared yet.</p>}
      <form onSubmit={submit}>
        <fieldset disabled={busy || organization.lifecycle !== "active"}>
          <legend>Account arrangement</legend>
          <label htmlFor={`${id}-outcome`}>Coverage arrangement</label>
          <select id={`${id}-outcome`} value={outcome} onChange={event => { setOutcome(event.target.value as Outcome); setAccountId(""); }}>
            <option value="account">Own account</option>
            <option value="shared" disabled={!organizationsComplete}>Shared account from another organization</option>
            <option value="unavailable">Unavailable</option>
          </select>
          {!organizationsComplete && <p>The organization list is incomplete. Shared-account choices are unavailable until the full list can be loaded.</p>}
          {outcome === "unavailable" ? <>
            <label htmlFor={`${id}-reason`}>Why unavailable</label>
            <select id={`${id}-reason`} value={reason} required onChange={event => setReason(event.target.value as Reason | "")}>
              <option value="">Choose a reason</option>
              {Object.entries(reasons).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </> : <>
            <label htmlFor={`${id}-account`}>Account</label>
            <select id={`${id}-account`} disabled={outcome === "shared" && !organizationsComplete} value={selected?.account_id ?? ""} required onChange={event => setAccountId(event.target.value)}>
              <option value="">Choose an existing account</option>
              {candidates.map(account => <option key={account.account_id} value={account.account_id}>{account.friendly_name} · {knownOrganization(account)?.name}</option>)}
            </select>
            {candidates.length === 0 && (outcome !== "shared" || organizationsComplete) && <p>No eligible account is registered. <a href="/accounts">Open Accounts</a> to add one.</p>}
            {outcome === "shared" && <p>This declares use of the selected account. It does not verify a shared provider balance.</p>}
          </>}
          <button type="submit" disabled={(outcome === "shared" && !organizationsComplete) || (outcome === "unavailable" ? !reason : !selected)}>Save coverage</button>
          {resource.coverage && !resource.coverage.invalidated_at && <button type="button" className="quiet-button" onClick={() => { void mutate(true); }}>Remove declaration</button>}
        </fieldset>
      </form>
    </>}
    {message && <p role="status">{message}</p>}
    <button type="button" className="quiet-button" disabled={busy || loading} onClick={() => { setMessage(null); void load(); }}>Refresh coverage</button>
  </div>;
}
