import { useEffect, useRef, useState } from "react";

import { CsrfUnavailableError, registry, type AccountViewV1, type BillingCollectionEligibilityWireV1,
  type BillingConnectionViewV1, type BillingReportContextV1, type BudgetRunStatusV1 } from "../../shared/api/client";
import { pendingRun } from "./billingCheckPresentation";
import { collectionReadRequired, collectionReason, collectionRetryAllowed, matchesCollectionEligibility, matchesCollectionRun,
  restoreCollectionIntent, sameCollectionContext, type BillingCollectIntent } from "./billingCollectPresentation";

/** The parent keys this control by account, connection version and exact selected interval. */
export function BillingCollectControl({ account, connection, reportContext, onExpired, onCollected }: Readonly<{
  account: AccountViewV1; connection: BillingConnectionViewV1; reportContext: BillingReportContextV1;
  onExpired: () => void; onCollected: () => void;
}>) {
  const storageKey = `agentmonitor.billing-collect.${account.account_id}.${connection.resource_id}`;
  const [intent, setIntent] = useState<BillingCollectIntent | null>(() => {
    try { return restoreCollectionIntent(sessionStorage.getItem(storageKey), account.account_id, connection.resource_id); }
    catch { return null; }
  });
  const [eligibility, setEligibility] = useState<BillingCollectionEligibilityWireV1 | null>(null);
  const [run, setRun] = useState<BudgetRunStatusV1 | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [reading, setReading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [revision, setRevision] = useState(0);
  const mounted = useRef(true), mutating = useRef(false);
  const request = useRef<AbortController | null>(null);
  const callbacks = useRef({ onExpired, onCollected });
  callbacks.current = { onExpired, onCollected };

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; request.current?.abort(); };
  }, []);

  function retain(next: BillingCollectIntent | null): boolean {
    try {
      if (next === null) sessionStorage.removeItem(storageKey);
      else sessionStorage.setItem(storageKey, JSON.stringify(next));
      setIntent(next);
      return true;
    } catch {
      setMessage("Browser session storage is unavailable. Collection cannot start or reconcile safely; restore session storage and refresh collection status.");
      return false;
    }
  }

  async function readEligibility(signal: AbortSignal, requestedContext = reportContext): Promise<BillingCollectionEligibilityWireV1 | null> {
    const result = await registry.billingCollectionEligibility(account.account_id, connection.resource_id, requestedContext, signal);
    if (signal.aborted) return null;
    if (!result.ok) {
      setEligibility(null);
      if (result.problem.code === "dashboard_authentication_required") callbacks.current.onExpired();
      else setMessage("Collection eligibility could not be read. Refresh collection status to try again.");
      return null;
    }
    const value = result.data;
    if (value.account_id !== account.account_id || value.resource_id !== connection.resource_id ||
        value.account_record_version !== account.record_version || value.connection_record_version !== connection.record_version ||
        value.scope_generation !== connection.scope_generation || !sameCollectionContext(requestedContext, value.report_context)) {
      setEligibility(null);
      setMessage("The account, connection or selected interval changed. Refresh view before collecting.");
      return null;
    }
    setEligibility(value);
    return value;
  }

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let reads = 0;
    const stopAt = Math.min(intent?.deadlineAt ? Date.parse(intent.deadlineAt) : Date.now(), Date.now() + 125000);
    setReading(true);
    const poll = async () => {
      if (controller.signal.aborted) return;
      if (reads > 0 && Date.now() >= stopAt) {
        setMessage("The collection result is not confirmed. Refresh collection status to reconcile the existing request.");
        return;
      }
      reads += 1;
      try {
        const current = await readEligibility(controller.signal, intent !== null && !intent.handled ? intent.reportContext : reportContext);
        if (!current || controller.signal.aborted) return;
        if (intent !== null && !intent.handled && !matchesCollectionEligibility(intent, current)) {
          retain(null);
          setRun(null);
          setMessage("The account, credential or billing scope changed. The previous collection cannot update this view.");
          return;
        }
        if (!intent?.runId || intent.handled) return;
        const result = await registry.billingRun(intent.runId, controller.signal);
        if (controller.signal.aborted) return;
        if (!result.ok) {
          if (result.problem.code === "dashboard_authentication_required") callbacks.current.onExpired();
          else setMessage("Collection status could not be read. Refresh collection status; do not start a duplicate request.");
          return;
        }
        if (!matchesCollectionRun(intent, result.data)) {
          setMessage("Collection status did not match this account, resource and interval. No financial reading was changed.");
          return;
        }
        setRun(result.data);
        setMessage(null);
        if (pendingRun(result.data.state)) timer = setTimeout(() => { void poll(); }, 2000);
        else if (!intent.handled) {
          const latest = await readEligibility(controller.signal, intent.reportContext);
          if (!latest || controller.signal.aborted) return;
          if (!matchesCollectionEligibility(intent, latest)) {
            retain(null);
            setRun(null);
            setMessage("The credential or billing scope changed. No financial reading was changed.");
            return;
          }
          const advance = collectionReadRequired(intent, result.data, reportContext);
          if (retain({ ...intent, handled: true }) && advance) callbacks.current.onCollected();
        }
      } catch {
        if (!controller.signal.aborted) { setEligibility(null); setMessage("The local service is unavailable. Refresh collection status to reconcile the existing request."); }
      } finally {
        if (!controller.signal.aborted) setReading(false);
      }
    };
    void poll();
    return () => { controller.abort(); if (timer !== undefined) clearTimeout(timer); };
  }, [intent, revision]);

  async function collect() {
    if (mutating.current || (intent !== null && !intent.handled && intent.runId !== null)) return;
    mutating.current = true;
    setSubmitting(true);
    setMessage(null);
    const controller = new AbortController();
    request.current = controller;
    try {
      const current = await readEligibility(controller.signal, intent !== null && !intent.handled ? intent.reportContext : reportContext);
      if (!current || controller.signal.aborted) return;
      let next = intent !== null && !intent.handled ? intent : null;
      if (next !== null && !matchesCollectionEligibility(next, current)) {
        retain(null); setRun(null);
        setMessage("The account, credential or billing scope changed. Review refreshed collection status before collecting.");
        return;
      }
      if (next !== null && !collectionRetryAllowed(next, current)) return;
      if (next === null) {
        if (!current.can_collect || current.binding_generation === null) return;
        next = { accountId: account.account_id, resourceId: connection.resource_id,
          accountVersion: current.account_record_version, connectionVersion: current.connection_record_version,
          scopeGeneration: current.scope_generation, bindingGeneration: current.binding_generation,
          reportContext, idempotencyKey: crypto.randomUUID().replaceAll("-", ""), runId: null, deadlineAt: null, handled: false, retryRequiresEligibility: false };
      }
      next = { ...next, retryRequiresEligibility: false };
      if (!retain(next)) return;
      setRun(null);
      const result = await registry.collectBilling(next, controller.signal);
      if (controller.signal.aborted || !mounted.current) return;
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") callbacks.current.onExpired();
        if (result.problem.status === 429) {
          retain({ ...next, retryRequiresEligibility: true });
          setMessage("Collection was rate limited. Refresh collection status; retry is available only when the server permits it.");
          await readEligibility(controller.signal, next.reportContext);
          return;
        }
        setMessage(result.problem.code === "csrf_validation_failed"
          ? "Session proof is unavailable. Reload or sign in again, then explicitly retry the same collection request."
          : "Collection outcome is not confirmed. Retry collection request uses its original identity; it does not create a new request.");
        return;
      }
      const admitted = restoreCollectionIntent(JSON.stringify({ ...next, runId: result.data.run_id, deadlineAt: result.data.deadline_at }), account.account_id, connection.resource_id);
      if (admitted === null) {
        setMessage("Collection acceptance was incomplete. Retry collection request to reconcile its original identity.");
        return;
      }
      if (retain(admitted)) setMessage("Collection accepted. Reading its actual result; acceptance does not confirm provider access.");
    } catch (error) {
      if (!controller.signal.aborted && mounted.current) setMessage(error instanceof CsrfUnavailableError
        ? "Session proof is unavailable. Reload or sign in again, then explicitly retry the same collection request."
        : "Collection outcome is unknown. Retry collection request uses its original identity.");
    } finally {
      mutating.current = false;
      if (mounted.current) setSubmitting(false);
    }
  }

  const unresolved = intent !== null && !intent.handled;
  const eligibleIntent = intent !== null && eligibility !== null && collectionRetryAllowed(intent, eligibility);
  return <section aria-label="Collect billing report" data-collect-resource={connection.resource_id}>
    <p>Billing scope: {connection.scope_id ?? "Not established"} · {connection.scope_evidence.replaceAll("_", " ")}.</p>
    <p>Collect costs for {reportContext.interval_start.slice(0, 10)} to {reportContext.interval_end.slice(0, 10)} UTC (end exclusive). Manual collection does not change API monitoring.</p>
    {unresolved && !sameCollectionContext(reportContext, intent.reportContext) && <p role="status">A collection request for {intent.reportContext.interval_start.slice(0, 10)} to {intent.reportContext.interval_end.slice(0, 10)} UTC (end exclusive) remains unresolved. The controls below reconcile that original interval. A new collection for the selected window is blocked until it is resolved.</p>}
    <div role="group" aria-label="Billing collection actions">
      <button type="button" disabled={submitting || reading || unresolved || eligibility?.can_collect !== true} onClick={() => { void collect(); }}>Collect now</button>
      <button type="button" className="quiet-button" disabled={submitting || reading} onClick={() => { setMessage(null); setRevision(value => value + 1); }}>Refresh collection status</button>
      {unresolved && intent.runId === null && <button type="button" disabled={submitting || reading || !eligibleIntent} onClick={() => { void collect(); }}>Retry collection request</button>}
    </div>
    {reading && <p role="status">Reading collection status…</p>}
    {eligibility !== null && (!unresolved || !eligibility.can_collect) && <p>{collectionReason(eligibility.reason_code)}</p>}
    {eligibility?.next_allowed_at != null && <p>Next allowed collection: <time dateTime={eligibility.next_allowed_at}>{new Date(eligibility.next_allowed_at).toLocaleString(undefined, { timeZoneName: "short" })}</time>.</p>}
    {run !== null && intent !== null && <p role="status">Collection for {intent.reportContext.interval_start.slice(0, 10)} to {intent.reportContext.interval_end.slice(0, 10)} UTC: {run.state.replaceAll("_", " ")}.{run.error_code !== null && ` ${collectionReason(run.error_code)}`}</p>}
    {unresolved && intent.runId === null && <p>The previous request is unconfirmed. Retry it explicitly to resolve its original identity.</p>}
    {message !== null && <p role="status">{message}</p>}
  </section>;
}
