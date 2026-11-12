import { useEffect, useRef, useState } from "react";

import { CsrfUnavailableError, cloudUsage, type AccountViewV1, type CloudUsageEligibilityWireV1,
  type CloudUsageContextV1, type CloudUsageRunStatusV1 } from "../../shared/api/client";
import { pendingRun } from "./billingCheckPresentation";
import { cloudUsageReadRequired, cloudUsageReason, cloudUsageRetryAllowed, cloudUsageRequestRefused, matchesCloudUsageEligibility, matchesCloudUsageRun,
  restoreCloudUsageIntent, sameCloudUsageContext, type CloudUsageIntent } from "./cloudUsageCollectPresentation";

/** The parent keys this control by account, resource, scope and exact selected interval. */
export function CloudUsageCollectControl({ account, resourceId, reportContext, onExpired, onCollected }: Readonly<{
  account: AccountViewV1; resourceId: string; reportContext: CloudUsageContextV1;
  onExpired: () => void; onCollected: () => void;
}>) {
  const storageKey = `agentmonitor.cloud-usage-collect.${account.account_id}.${resourceId}`;
  const [intent, setIntent] = useState<CloudUsageIntent | null>(() => {
    try { return restoreCloudUsageIntent(sessionStorage.getItem(storageKey), account.account_id, resourceId); }
    catch { return null; }
  });
  const [eligibility, setEligibility] = useState<CloudUsageEligibilityWireV1 | null>(null);
  const [run, setRun] = useState<CloudUsageRunStatusV1 | null>(null);
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

  function retain(next: CloudUsageIntent | null): boolean {
    try {
      if (next === null) sessionStorage.removeItem(storageKey);
      else sessionStorage.setItem(storageKey, JSON.stringify(next));
      setIntent(next);
      return true;
    } catch {
      setMessage("Browser session storage is unavailable. Collection cannot start or reconcile safely; restore session storage and refresh usage status.");
      return false;
    }
  }

  async function readEligibility(signal: AbortSignal, requestedContext = reportContext): Promise<CloudUsageEligibilityWireV1 | null> {
    const result = await cloudUsage.eligibility(account.account_id, resourceId, requestedContext, signal);
    if (signal.aborted) return null;
    if (!result.ok) {
      setEligibility(null);
      if (result.problem.code === "dashboard_authentication_required") callbacks.current.onExpired();
      else setMessage("Collection eligibility could not be read. Refresh usage status to try again.");
      return null;
    }
    const value = result.data;
    if (value.account_id !== account.account_id || value.resource_id !== resourceId ||
        value.account_record_version !== account.record_version || !Number.isSafeInteger(value.target_record_version) || value.target_record_version < 1 || !sameCloudUsageContext(requestedContext, value.report_context)) {
      setEligibility(null);
      setMessage("The account, cloud target or selected interval changed. Refresh view before collecting.");
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
        setMessage("The collection result is not confirmed. Refresh usage status to reconcile the existing request.");
        return;
      }
      if (reads > 0 && document.visibilityState !== "visible") {
        timer = setTimeout(() => { void poll(); }, 2000);
        return;
      }
      reads += 1;
      try {
        const current = await readEligibility(controller.signal, intent !== null && !intent.handled ? intent.reportContext : reportContext);
        if (!current || controller.signal.aborted) return;
        if (intent !== null && !intent.handled && !matchesCloudUsageEligibility(intent, current)) {
          retain(null);
          setRun(null);
          setMessage("The account, credential or cloud target changed. The previous collection cannot update this view.");
          return;
        }
        if (intent !== null && !intent.handled && cloudUsageRequestRefused(current.reason_code, intent.retryRequiresEligibility)) {
          retain(null);
          setMessage(cloudUsageReason(current.reason_code));
          return;
        }
        if (!intent?.runId || intent.handled) return;
        const result = await cloudUsage.status(account.account_id, resourceId, intent.runId, controller.signal);
        if (controller.signal.aborted) return;
        if (!result.ok) {
          if (result.problem.code === "dashboard_authentication_required") callbacks.current.onExpired();
          else setMessage("Collection status could not be read. Refresh usage status; do not start a duplicate request.");
          return;
        }
        if (!matchesCloudUsageRun(intent, result.data)) {
          setMessage("Collection status did not match this account, resource and interval. No financial reading was changed.");
          return;
        }
        setRun(result.data);
        setMessage(null);
        if (pendingRun(result.data.state)) timer = setTimeout(() => { void poll(); }, 2000);
        else if (!intent.handled) {
          const latest = await readEligibility(controller.signal, intent.reportContext);
          if (!latest || controller.signal.aborted) return;
          if (!matchesCloudUsageEligibility(intent, latest)) {
            retain(null);
            setRun(null);
            setMessage("The credential or cloud target changed. No financial reading was changed.");
            return;
          }
          const advance = cloudUsageReadRequired(intent, result.data, reportContext);
          if (retain({ ...intent, handled: true }) && advance) callbacks.current.onCollected();
        }
      } catch {
        if (!controller.signal.aborted) { setEligibility(null); setMessage("The local service is unavailable. Refresh usage status to reconcile the existing request."); }
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
      if (next !== null && !matchesCloudUsageEligibility(next, current)) {
        retain(null); setRun(null);
        setMessage("The account, credential or cloud target changed. Review refreshed collection status before collecting.");
        return;
      }
      if (next !== null && !cloudUsageRetryAllowed(next, current)) return;
      if (next === null) {
        if (!current.can_collect || current.binding_generation === null) return;
        next = { accountId: account.account_id, resourceId: resourceId,
          accountVersion: current.account_record_version, targetVersion: current.target_record_version,
          bindingGeneration: current.binding_generation,
          reportContext, idempotencyKey: crypto.randomUUID().replaceAll("-", ""), runId: null, deadlineAt: null, handled: false, retryRequiresEligibility: false };
      }
      next = { ...next, retryRequiresEligibility: false };
      if (!retain(next)) return;
      setRun(null);
      const result = await cloudUsage.collect(next.accountId, next.resourceId, next.accountVersion, next.targetVersion, next.reportContext, next.idempotencyKey, controller.signal);
      if (controller.signal.aborted || !mounted.current) return;
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") callbacks.current.onExpired();
        if (cloudUsageRequestRefused(result.problem.code)) {
          retain(null);
          setMessage(cloudUsageReason(result.problem.code));
          await readEligibility(controller.signal);
          return;
        }
        if (result.problem.status === 429) {
          retain({ ...next, retryRequiresEligibility: true });
          setMessage("Collection was rate limited. Refresh usage status; retry is available only when the server permits it.");
          await readEligibility(controller.signal, next.reportContext);
          return;
        }
        setMessage(result.problem.code === "csrf_validation_failed"
          ? "Session proof is unavailable. Reload or sign in again, then explicitly retry the same collection request."
          : "Collection outcome is not confirmed. Retry usage request uses its original identity; it does not create a new request.");
        return;
      }
      const admitted = restoreCloudUsageIntent(JSON.stringify({ ...next, runId: result.data.run_id, deadlineAt: result.data.deadline_at }), account.account_id, resourceId);
      if (admitted === null || !matchesCloudUsageRun(admitted, result.data)) {
        setMessage("Collection acceptance was incomplete. Retry usage request to reconcile its original identity.");
        return;
      }
      if (retain(admitted)) setMessage("Collection accepted. Reading its actual result; acceptance does not confirm provider access.");
    } catch (error) {
      if (!controller.signal.aborted && mounted.current) setMessage(error instanceof CsrfUnavailableError
        ? "Session proof is unavailable. Reload or sign in again, then explicitly retry the same collection request."
        : "Collection outcome is unknown. Retry usage request uses its original identity.");
    } finally {
      mutating.current = false;
      if (mounted.current) setSubmitting(false);
    }
  }

  const unresolved = intent !== null && !intent.handled;
  const eligibleIntent = intent !== null && eligibility !== null && cloudUsageRetryAllowed(intent, eligibility);
  return <section aria-label="Collect cloud usage" data-cloud-collect-resource={resourceId}>
    <p>Collect {reportContext.scope} usage for {reportContext.interval_start.slice(0, 10)} to {reportContext.interval_end.slice(0, 10)} UTC (end exclusive). Usage collection does not change balance or monitoring settings.</p>
    {unresolved && !sameCloudUsageContext(reportContext, intent.reportContext) && <p role="status">A {intent.reportContext.scope} usage request for {intent.reportContext.interval_start.slice(0, 10)} to {intent.reportContext.interval_end.slice(0, 10)} UTC (end exclusive) remains unresolved. The controls below reconcile that original interval. A new collection for the selected window is blocked until it is resolved.</p>}
    <div role="group" aria-label="Cloud usage collection actions">
      <button type="button" disabled={submitting || reading || unresolved || eligibility?.can_collect !== true} onClick={() => { void collect(); }}>Collect usage</button>
      <button type="button" className="quiet-button" disabled={submitting || reading} onClick={() => { setMessage(null); setRevision(value => value + 1); }}>Refresh usage status</button>
      {unresolved && intent.runId === null && <button type="button" disabled={submitting || reading || !eligibleIntent} onClick={() => { void collect(); }}>Retry usage request</button>}
    </div>
    {reading && <p role="status">Reading usage status…</p>}
    {eligibility !== null && (!unresolved || !eligibility.can_collect) && <p>{cloudUsageReason(eligibility.reason_code)}</p>}
    {eligibility?.next_allowed_at != null && <p>Next allowed collection: <time dateTime={eligibility.next_allowed_at}>{new Date(eligibility.next_allowed_at).toLocaleString(undefined, { timeZoneName: "short" })}</time>.</p>}
    {run !== null && intent !== null && <p role="status">{intent.reportContext.scope} usage collection for {intent.reportContext.interval_start.slice(0, 10)} to {intent.reportContext.interval_end.slice(0, 10)} UTC: {run.state.replaceAll("_", " ")}.{run.error_code !== null && ` ${cloudUsageReason(run.error_code)}`}</p>}
    {unresolved && intent.runId === null && <p>The previous request is unconfirmed. Retry it explicitly to resolve its original identity.</p>}
    {message !== null && <p role="status">{message}</p>}
  </section>;
}
