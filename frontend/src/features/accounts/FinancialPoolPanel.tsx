import { useEffect, useRef, useState } from "react";

import { budgets, CsrfUnavailableError, financialPools, registry, type AccountViewV1, type FinancialPoolConfigurationV1, type FinancialPoolViewV1, type OrganizationViewV1 } from "../../shared/api/client";
import { completedPeriod } from "./budgetPresentation";
import { compatiblePoolChoices, organizationLabel, poolReason, restorePoolIntent, type PoolContext, type PoolIntent, type PoolSelector } from "./financialPoolPresentation";

type Props = Readonly<{
  account: AccountViewV1;
  resourceId: string;
  selector: PoolSelector;
  onExpired: () => void;
  onProofUnavailable: () => void;
  onChanged: () => void;
}>;
type Loaded = Readonly<{ configuration: FinancialPoolConfigurationV1; organizations: readonly OrganizationViewV1[]; pools: readonly FinancialPoolViewV1[] }>;

function PoolControls({ account, resourceId, selector, onExpired, onProofUnavailable, onChanged }: Props) {
  const context: PoolContext = { accountId: account.account_id, resourceId, selector };
  const storageKey = `agentmonitor.financial-pool.${context.accountId}.${resourceId}.${selector}`;
  const [open, setOpen] = useState(false);
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [organizationId, setOrganizationId] = useState("");
  const [poolId, setPoolId] = useState("");
  const [busy, setBusy] = useState(false);
  const [reviewRequired, setReviewRequired] = useState(false);
  const [intent, setIntent] = useState<PoolIntent | null>(() => {
    try { return restorePoolIntent(sessionStorage.getItem(storageKey), context); }
    catch { return null; }
  });
  const mounted = useRef(false);
  const mutating = useRef(false);
  const request = useRef<AbortController | null>(null);
  const read = useRef<AbortController | null>(null);
  const callbacks = useRef({ onExpired, onProofUnavailable, onChanged });
  callbacks.current = { onExpired, onProofUnavailable, onChanged };
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; request.current?.abort(); read.current?.abort(); };
  }, []);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    read.current = controller;
    setLoading(true);
    setError(null);
    void (async () => {
      try {
        const configuration = await financialPools.configuration(account.account_id, resourceId, selector, controller.signal);
        if (!configuration.ok) {
          if (configuration.problem.code === "dashboard_authentication_required") callbacks.current.onExpired();
          throw new Error("pool_status_unavailable");
        }
        const current = configuration.data;
        if (current.account_id !== account.account_id || current.resource_id !== resourceId || current.selector !== selector) throw new Error("pool_status_mismatch");
        const organizations: OrganizationViewV1[] = [];
        const groupIds = new Set<string>();
        const cursors = new Set<string>();
        let cursor: string | undefined;
        do {
          const page = await registry.organizations(controller.signal, cursor);
          if (!page.ok) {
            if (page.problem.code === "dashboard_authentication_required") callbacks.current.onExpired();
            throw new Error("pool_groups_unavailable");
          }
          if (page.data.availability.state !== "available") throw new Error("pool_groups_unavailable");
          for (const item of page.data.items) {
            if (groupIds.has(item.organization_id) || item.registry_revision !== current.registry_revision) throw new Error("pool_registry_changed");
            groupIds.add(item.organization_id);
            organizations.push(item);
          }
          cursor = page.data.page.has_more ? page.data.page.next_cursor ?? undefined : undefined;
          if (page.data.page.has_more && (cursor === undefined || cursors.has(cursor) || cursors.size >= 100)) throw new Error("pool_groups_incomplete");
          if (cursor !== undefined) cursors.add(cursor);
        } while (cursor !== undefined);
        if (!["claude", "codex", "ollama"].includes(account.provider_key)) throw new Error("pool_provider_invalid");
        const provider = account.provider_key as "claude" | "codex" | "ollama";
        const pools: FinancialPoolViewV1[] = [];
        const ids = new Set<string>();
        const poolCursors = new Set<string>();
        let after: string | undefined;
        do {
          const page = await financialPools.list(provider, current.registry_revision, after, controller.signal);
          if (!page.ok) {
            if (page.problem.code === "dashboard_authentication_required") callbacks.current.onExpired();
            throw new Error("pool_choices_unavailable");
          }
          if (page.data.registry_revision !== current.registry_revision) throw new Error("pool_registry_changed");
          for (const item of page.data.items) {
            if (ids.has(item.pool_id) || item.provider_key !== provider) throw new Error("pool_registry_changed");
            ids.add(item.pool_id);
            pools.push(item);
          }
          after = page.data.next_pool_id ?? undefined;
          if (after !== undefined && (poolCursors.has(after) || poolCursors.size >= 100)) throw new Error("pool_choices_incomplete");
          if (after !== undefined) poolCursors.add(after);
        } while (after !== undefined);
        const final = await financialPools.configuration(account.account_id, resourceId, selector, controller.signal);
        if (!final.ok || final.data.registry_revision !== current.registry_revision) throw new Error("pool_registry_changed");
        if (controller.signal.aborted) return;
        setLoaded({ configuration: final.data, organizations, pools: compatiblePoolChoices(pools, provider, selector) });
        setOrganizationId(final.data.pool?.primary_organization_id ?? (final.data.pool === null ? account.organization_id ?? "" : ""));
        setPoolId("");
      } catch {
        if (!controller.signal.aborted) setError("Pool status or choices could not be loaded completely. Refresh pool status before changing them.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();
    return () => controller.abort();
  }, [account.account_id, account.provider_key, account.organization_id, account.record_version, resourceId, selector, open, revision]);

  function retain(value: PoolIntent | null): boolean {
    try {
      if (value === null) sessionStorage.removeItem(storageKey);
      else sessionStorage.setItem(storageKey, JSON.stringify(value));
    } catch {
      setMessage("This tab cannot retain the request safely. Allow tab storage and refresh pool status before changing it.");
      return false;
    }
    setIntent(value);
    return true;
  }

  async function submit(value: PoolIntent) {
    if (mutating.current || !retain(value)) return;
    mutating.current = true;
    read.current?.abort();
    setLoading(false);
    setBusy(true);
    setMessage(null);
    setReviewRequired(false);
    const controller = new AbortController();
    request.current = controller;
    try {
      const result = value.kind === "assign"
        ? await financialPools.assign(value.accountId, value.resourceId, value.selector, { action: value.action, pool_id: value.poolId, primary_organization_id: value.organizationId }, value.revision, value.idempotencyKey, controller.signal)
        : await financialPools.edit(value.poolId, { expected_record_version: value.recordVersion, primary_organization_id: value.organizationId }, value.revision, value.idempotencyKey, controller.signal);
      if (!mounted.current || controller.signal.aborted) return;
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") callbacks.current.onExpired();
        else if (result.problem.code === "csrf_validation_failed") callbacks.current.onProofUnavailable();
        else {
          setMessage(poolReason(result.problem.code));
          // A conflict may follow an earlier committed request. Reread and let
          // the owner explicitly accept current state instead of making a new write.
          setReviewRequired([400, 404, 409, 412, 422].includes(result.problem.status));
        }
        setRevision((number) => number + 1);
        return;
      }
      const matching = value.kind === "assign"
        ? "account_id" in result.data && result.data.account_id === value.accountId && result.data.resource_id === value.resourceId && result.data.selector === value.selector &&
          (value.action === "unlink" ? result.data.pool === null : result.data.pool !== null && (value.action !== "join" || result.data.pool.pool_id === value.poolId))
        : "pool_id" in result.data && result.data.pool_id === value.poolId && result.data.primary_organization_id === value.organizationId;
      if (!matching) {
        setMessage("The response did not match this pool change. Refresh its status and resolve the previous change.");
        setRevision((number) => number + 1);
        return;
      }
      if (!retain(null)) return;
      setMessage("Billing pool change saved.");
      setRevision((number) => number + 1);
      callbacks.current.onChanged();
    } catch (caught) {
      if (!mounted.current || controller.signal.aborted) return;
      if (caught instanceof CsrfUnavailableError) callbacks.current.onProofUnavailable();
      else setMessage("The pool change outcome is unknown. Refresh pool status, then resolve the previous change with its original request identity.");
      setRevision((number) => number + 1);
    } finally {
      mutating.current = false;
      if (mounted.current) setBusy(false);
    }
  }

  const configuration = loaded?.configuration;
  const pool = configuration?.pool ?? null;
  const selectedOrganizationValid = organizationId === "" || loaded?.organizations.some((organization) => organization.organization_id === organizationId && organization.lifecycle === "active") === true;
  const ready = !loading && !busy && error === null && configuration !== undefined;
  const canChange = ready && configuration.can_assign && intent === null;
  const key = () => Array.from(crypto.getRandomValues(new Uint8Array(16)), (byte) => byte.toString(16).padStart(2, "0")).join("");
  function assign(action: "create" | "join" | "unlink") {
    if (!canChange || configuration === undefined || (action === "create" && !selectedOrganizationValid) || (action === "join" && !loaded?.pools.some((choice) => choice.pool_id === poolId))) return;
    void submit({ ...context, kind: "assign", revision: configuration.registry_revision, idempotencyKey: key(), action, poolId: action === "join" ? poolId : null, organizationId: action === "create" ? organizationId || null : null });
  }
  function edit() {
    if (!canChange || configuration === undefined || pool === null || !selectedOrganizationValid) return;
    void submit({ ...context, kind: "edit", revision: configuration.registry_revision, idempotencyKey: key(), poolId: pool.pool_id, recordVersion: pool.record_version, organizationId: organizationId || null });
  }
  const title = selector === "billing" ? "Manage billing pool" : `Manage billing pool · ${selector === "self" ? "Self usage" : "Team usage"}`;
  const primaryId = `pool-primary-${resourceId}-${selector}`;
  const choiceId = `pool-choice-${resourceId}-${selector}`;
  return <details className="account-secondary" data-financial-pool={selector} onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary>{title}</summary>
    <div aria-busy={loading || busy}>
      {loading && <p role="status">Reading pool status and all choices…</p>}
      {error !== null && <p role="alert">{error}</p>}
      {configuration !== undefined && <>
        {pool === null ? <p>No billing pool association.</p> : <>
          <p><strong>{pool.display_name}</strong></p>
          <p>Primary dashboard organization: {organizationLabel(pool.primary_organization_id, loaded?.organizations ?? [])}</p>
          <p>Changing the primary organization affects every account linked to this pool.</p>
        </>}
        <p>Provider scope: {configuration.provider_scope_id ?? "Unresolved"}{selector !== "billing" && ` · ${selector === "self" ? "Self usage" : "Team usage"}`}</p>
        <p>{poolReason(configuration.reason_code)}</p>
        <p>Pool associations describe financial ownership; they do not verify provider access or change monitoring. Self and team reports remain separate.</p>
        <label htmlFor={primaryId}>Primary dashboard organization</label>
        <select id={primaryId} value={organizationId} disabled={!canChange} onChange={(event) => setOrganizationId(event.target.value)}>
          <option value="">Ungrouped</option>
          {organizationId !== "" && !selectedOrganizationValid && <option value={organizationId} disabled>{organizationLabel(organizationId, loaded?.organizations ?? [])}</option>}
          {loaded?.organizations.filter((organization) => organization.lifecycle === "active").map((organization) => <option key={organization.organization_id} value={organization.organization_id}>{organization.name}</option>)}
        </select>
        {pool !== null && <button type="button" disabled={!canChange || !selectedOrganizationValid || (organizationId || null) === pool.primary_organization_id} onClick={edit}>Save primary organization</button>}
        <button type="button" disabled={!canChange || !selectedOrganizationValid} onClick={() => assign("create")}>Create distinct billing pool</button>
        <label htmlFor={choiceId}>Existing billing pool</label>
        <select id={choiceId} value={poolId} disabled={!canChange} onChange={(event) => setPoolId(event.target.value)}>
          <option value="">Choose a compatible pool</option>
          {loaded?.pools.map((choice) => <option key={choice.pool_id} value={choice.pool_id}>{choice.display_name} · {organizationLabel(choice.primary_organization_id, loaded.organizations)} · {choice.created_at}</option>)}
        </select>
        {loaded?.pools.length === 0 && !loading && error === null && <p>No compatible billing pools exist yet.</p>}
        <button type="button" disabled={!canChange || poolId === ""} onClick={() => assign("join")}>Use existing billing pool</button>
        {pool !== null && <button type="button" disabled={!canChange} onClick={() => assign("unlink")}>Unlink billing pool</button>}
      </>}
      {message !== null && <p role="status">{message}</p>}
      {intent !== null && <>
        <p>A previous pool change needs reconciliation. Its original request is retained; it will not retry automatically.</p>
        <button type="button" disabled={!ready} onClick={() => { void submit(intent); }}>Resolve previous change</button>
        {reviewRequired && <button type="button" disabled={!ready} onClick={() => {
          if (retain(null)) { setReviewRequired(false); setMessage("Current pool status accepted. Review it before making another change."); }
        }}>Use current pool status</button>}
      </>}
      <button type="button" className="quiet-button" disabled={busy || loading} onClick={() => setRevision((number) => number + 1)}>Refresh pool status</button>
    </div>
  </details>;
}

export function FinancialPoolPanel(props: Props) {
  return <PoolControls key={`${props.account.account_id}:${props.resourceId}:${props.selector}`} {...props} />;
}

/** Discover the existing cloud graph via stored financial API metadata only. */
export function CloudFinancialPoolPanels({ account, onExpired, onProofUnavailable, onChanged }: Omit<Props, "resourceId" | "selector">) {
  const [resources, setResources] = useState<Readonly<{ accountId: string; ids: readonly string[] }> | null>(null);
  const [failed, setFailed] = useState(false);
  const [revision, setRevision] = useState(0);
  const callbacks = useRef({ onExpired });
  callbacks.current = { onExpired };
  useEffect(() => {
    const controller = new AbortController();
    setFailed(false);
    void budgets.account(account.account_id, completedPeriod(7, new Date()), controller.signal).then((result) => {
      if (controller.signal.aborted) return;
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") callbacks.current.onExpired();
        setFailed(true);
      } else if (result.data.account_id !== account.account_id || result.data.availability.state === "unavailable") setFailed(true);
      else setResources({ accountId: account.account_id, ids: [...new Set((result.data.cloud_resources ?? []).map((resource) => resource.resource_id))] });
    }).catch(() => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, [account.account_id, account.record_version, revision]);
  if (failed) return <details className="account-secondary"><summary>Manage billing pool</summary><p>Existing cloud resources could not be read.</p><button type="button" onClick={() => setRevision((number) => number + 1)}>Refresh pool resources</button></details>;
  if (resources?.accountId !== account.account_id) return null;
  return <>{resources.ids.flatMap((resourceId) => (["self", "team"] as const).map((selector) => <FinancialPoolPanel key={`${resourceId}:${selector}`} account={account} resourceId={resourceId} selector={selector} onExpired={onExpired} onProofUnavailable={onProofUnavailable} onChanged={onChanged} />))}</>;
}
