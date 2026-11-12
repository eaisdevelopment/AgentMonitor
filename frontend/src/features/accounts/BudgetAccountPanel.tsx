import { useEffect, useRef, useState } from "react";

import {
  budgets,
  type AccountBudgetSummaryWireV1,
  type AccountViewV1,
  type BudgetCloudResourceSummaryWireV1,
  type BudgetResourceSummaryWireV1,
} from "../../shared/api/client";
import { completedPeriod, displayMoney, exactMoneyText } from "./budgetPresentation";
import { BudgetDailyHistory } from "./BudgetDailyHistory";
import { BillingCollectControl } from "./BillingCollectControl";
import { collectionContext } from "./billingCollectPresentation";
import { CloudUsageCollectControl } from "./CloudUsageCollectControl";
import { cloudUsageContext, cloudUsageScope } from "./cloudUsageCollectPresentation";
import { budgetWindowDays, budgetWindowSearch, latestBudgetWindow, resizeBudgetWindow, shiftBudgetWindow, type BudgetWindow } from "./budgetWindowNavigation";
import { advanceFinancialRead } from "./billingCheckPresentation";
import { canRetainFinancialReading, selectedFinancialReport, type FinancialReadContext } from "./financialReadPresentation";

const readable = (value: string) => value.replaceAll("_", " ");
const instant = (value: string) => new Date(value).toLocaleString(undefined, { timeZoneName: "short" });
const bounds = (start: string, end: string) => `${start.slice(0, 10)} to ${end.slice(0, 10)} UTC (end exclusive)`;

type Funds = NonNullable<AccountBudgetSummaryWireV1["funds"]>;
type FundComponent = Funds["components"][number];
const fundLabels: Readonly<Record<FundComponent["kind"], string>> = {
  balance: "Balance", included_credits: "Included credits", purchased_credits: "Purchased credits",
  soft_limit: "Soft budget", hard_limit: "Hard limit",
};

function FundMoney({ field }: Readonly<{ field: FundComponent["remaining"] }>) {
  return <>{field.value === null ? readable(field.reason_code ?? field.availability) : <>
    <span title={exactMoneyText(field.value)}>{displayMoney(field.value)}</span>
    {field.availability !== "available" && ` · ${readable(field.availability)}`}
  </>}</>;
}

function FundsReading({ funds }: Readonly<{ funds: Funds }>) {
  return <section aria-label="Available funds and limits">
    <h3>Available funds and limits</h3>
    {funds.availability.state !== "available" && <p role="status">Funds {funds.availability.state}: {readable(funds.availability.reason_code)}.</p>}
    {funds.components.map((component) => <article key={`${component.subject.resource_id}:${component.component_id}`} data-fund-resource={component.subject.resource_id} data-fund-component={component.component_id}>
      <h4>{fundLabels[component.kind]}</h4>
      <p><strong>{component.kind === "soft_limit" || component.kind === "hard_limit" ? "Remaining headroom" : "Remaining"}: </strong><FundMoney field={component.remaining} /></p>
      {component.limit.value !== null && <p>Limit: <FundMoney field={component.limit} /></p>}
      <p>{component.observed_at === null ? "Collected" : `Current ${fundLabels[component.kind].toLowerCase()} as of`} <time dateTime={component.observed_at ?? component.collected_at}>{instant(component.observed_at ?? component.collected_at)}</time>
        {` · ${readable(component.freshness)} · ${readable(component.completeness)}`}</p>
      <p>{component.scope_evidence === "unresolved" ? "Scope unresolved" : `Scope ${readable(component.scope_evidence)}`}.</p>
      {component.is_constraining === false && <p>This component does not determine account availability.</p>}
      {component.is_constraining === null && <p>Whether this component limits account availability is unknown.</p>}
      {component.kind === "soft_limit" && <p>A soft budget is a warning threshold, not available cash or an enforced stop.</p>}
      {component.period !== null && <p>Funds period: {bounds(component.period.start, component.period.end)}</p>}
      {component.renewal_at !== null && <p>Renewal: <time dateTime={component.renewal_at}>{instant(component.renewal_at)}</time></p>}
      {component.expires_at !== null && <p>Expiry: <time dateTime={component.expires_at}>{instant(component.expires_at)}</time></p>}
      <details><summary>Funds source details</summary>
        <dl className="telemetry-readouts">
          <div><dt>Source</dt><dd>{component.provenance.source_id}</dd></div>
          <div><dt>Observation</dt><dd>{component.observation_id}</dd></div>
          <div><dt>Collected</dt><dd>{instant(component.collected_at)}</dd></div>
          <div><dt>Value meaning</dt><dd>{readable(component.remaining.value_kind)}</dd></div>
          <div><dt>Precision</dt><dd>{component.remaining.precision}</dd></div>
          <div><dt>Confidence</dt><dd>{component.remaining.confidence}</dd></div>
          {component.remaining.value !== null && <div><dt>Exact remaining</dt><dd>{exactMoneyText(component.remaining.value)}</dd></div>}
          <div><dt>Adapter version</dt><dd>{component.provenance.adapter_version}</dd></div>
        </dl>
      </details>
    </article>)}
  </section>;
}

function ResourceReading({ resource, accountId, asOf, onExpired }: Readonly<{ resource: BudgetResourceSummaryWireV1 | BudgetCloudResourceSummaryWireV1; accountId: string; asOf: string; onExpired: () => void }>) {
  const run = resource.latest_collection;
  return <article>
    {"connection" in resource ? <>
      <p><strong>Provider billing scope:</strong> {resource.connection.scope_id ?? "Not established"} · {readable(resource.connection.scope_evidence)}</p>
      <p>API monitoring: {resource.connection.monitoring_preference === "enabled" ? "on" : "off"}.</p>
    </> : <p><strong>Cloud usage</strong> · {readable(resource.lifecycle)}</p>}
    {run !== null && <p role={run.state === "failed" || run.state === "blocked" ? "status" : undefined}>
      Latest collection: {readable(run.state)} · {instant(run.completed_at ?? run.started_at ?? run.requested_at)}
      {run.error_code !== null && ` · ${readable(run.error_code)}`}
    </p>}
    {run === null && <p>{resource.collection_availability.reason_code === "budget_collection_not_started"
      ? "No collection has started." : "Collection status is unavailable."}</p>}
    {resource.reports.length === 0 && <p>{resource.report_availability.reason_code === "budget_current_reports_absent"
      ? "No retained report for this interval." : `Reports unavailable: ${readable(resource.report_availability.reason_code)}.`}</p>}
    {resource.reports.map((selection) => {
      const report = selection.current ?? selection.latest_attempt;
      const attempt = selection.latest_attempt;
      const key = report?.report_id ?? attempt?.report_id ?? "no-report";
      const spend = resource.reported_spend.find((value) => value.report_id === report?.report_id);
      return <section key={key} data-report-id={report?.report_id}>
        {selection.current === null && report !== null && <p>Partial evidence only. No complete-period total is available.</p>}
        {report === null ? <p>No complete report for this financial context.</p> : <>
          {report.currency === null && report.cost_bucket_count === 0 && report.usage_bucket_count > 0
            ? <p>Provider did not report costs.</p>
            : <p><strong>Reported spend: </strong>{spend?.total != null ? <span title={exactMoneyText(spend.total)}>{displayMoney(spend.total)}</span>
              : `Unavailable · ${readable(spend?.reason_code ?? "reported_spend_unavailable")}`}</p>}
          {!("connection" in resource) && <p><strong>Provider billing scope:</strong> {report.scope_id ?? "Not established"} · {readable(report.scope_evidence)}</p>}
          <p>{bounds(report.requested_period.start, report.requested_period.end)} · {readable(report.cost_basis)} · {readable(report.source_category)}</p>
          <p>Data through: {report.source_data_through === null ? "Not reported" : instant(report.source_data_through)} · Collected: {instant(report.collected_at)}</p>
          {report.grouping.length > 0 && report.cost_bucket_count === 0 && report.usage_bucket_count === 0 && <p>No reported usage in this interval.</p>}
          {report.grouping.length === 0 && <BudgetDailyHistory context={{ accountId,
            resourceId: "connection" in resource ? resource.connection.resource_id : resource.resource_id,
            reportId: report.report_id, periodStart: report.requested_period.start,
            periodEnd: report.requested_period.end, asOf }} onExpired={onExpired} />}
          <details><summary>Source details</summary>
            <dl className="telemetry-readouts">
              <div><dt>Source</dt><dd>{report.source_id}</dd></div>
              <div><dt>Report</dt><dd style={{ overflowWrap: "anywhere" }}>{report.report_id}</dd></div>
              <div><dt>Coverage</dt><dd>{report.covered_period === null ? "Not reported" : bounds(report.covered_period.start, report.covered_period.end)}</dd></div>
              <div><dt>Completeness</dt><dd>{report.completeness}</dd></div>
              {spend?.total != null && <div><dt>Exact reported spend</dt><dd style={{ overflowWrap: "anywhere" }}>{exactMoneyText(spend.total)}</dd></div>}
            </dl>
          </details>
        </>}
        {attempt !== null && attempt.report_id !== report?.report_id && <p>
          Latest report attempt: {attempt.completeness} · {instant(attempt.collected_at)}
          {attempt.omission_codes.length > 0 && ` · ${attempt.omission_codes.map(readable).join(", ")}`}
          {report !== null && ". The complete report remains shown with its original times."}
        </p>}
      </section>;
    })}
  </article>;
}

export function BudgetAccountPanel({ account, showUnconfigured, onExpired, readRevision, financialSearch = "" }: Readonly<{
  account: AccountViewV1;
  showUnconfigured: boolean;
  onExpired: () => void;
  readRevision: number;
  financialSearch?: string;
}>) {
  const selection = selectedFinancialReport(financialSearch);
  const [days, setDays] = useState<7 | 30>(() => (selection.kind === "selected" || selection.kind === "period") ? selection.days : 7);
  const [query, setQuery] = useState(() => (selection.kind === "selected" || selection.kind === "period") ? selection.query : completedPeriod(7, new Date()));
  const [snapshot, setSnapshot] = useState<Readonly<{ context: FinancialReadContext; data: AccountBudgetSummaryWireV1 }> | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const expired = useRef(onExpired);
  const lastReadRevision = useRef(readRevision);
  const lastFinancialSearch = useRef(financialSearch);
  expired.current = onExpired;
  const context: FinancialReadContext = { account, periodStart: query.period_start, periodEnd: query.period_end, readRevision };
  // Fence the heading during render too, before an obsolete request's effect is cleaned up.
  const data = snapshot !== null && canRetainFinancialReading(snapshot.context, context) ? snapshot.data : null;

  useEffect(() => {
    const changed = lastFinancialSearch.current !== financialSearch;
    lastFinancialSearch.current = financialSearch;
    if (selection.kind === "none" && changed) {
      setDays(7);
      setQuery(completedPeriod(7, new Date()));
    } else if (selection.kind === "selected" || selection.kind === "period") {
      setDays(selection.days);
      setQuery((current) => current.period_start === selection.query.period_start && current.period_end === selection.query.period_end && current.as_of === selection.query.as_of ? current : selection.query);
    }
  }, [financialSearch]);

  useEffect(() => {
    if (lastReadRevision.current === readRevision) return;
    lastReadRevision.current = readRevision;
    setQuery((current) => advanceFinancialRead(current, new Date()));
  }, [readRevision]);

  useEffect(() => {
    const controller = new AbortController();
    setSnapshot((current) => current !== null && canRetainFinancialReading(current.context, context) ? current : null);
    setBusy(true);
    setError(null);
    void (async () => {
      try {
        const result = await budgets.accountSummary(account.account_id, query, controller.signal);
        if (controller.signal.aborted) return;
        if (!result.ok) {
          if (result.problem.code === "dashboard_authentication_required") expired.current();
          else setError("Financial readings could not be refreshed. Any previous reading below retains its original times.");
          return;
        }
        if (result.data.account_id !== account.account_id || Date.parse(result.data.period.start) !== Date.parse(query.period_start) || Date.parse(result.data.period.end) !== Date.parse(query.period_end)) {
          setError("Financial readings did not match this account and interval. Refresh to try again.");
          return;
        }
        setSnapshot({ context, data: result.data });
      } catch {
        if (!controller.signal.aborted) setError("The local service is unavailable. Previous readings have not been refreshed.");
      } finally {
        if (!controller.signal.aborted) setBusy(false);
      }
    })();
    return () => controller.abort();
  }, [account, query]);

  function selectWindow(next: BudgetWindow) {
    setDays(budgetWindowDays(next));
    setQuery(next);
    const search = budgetWindowSearch(window.location.search, next, selection.kind === "selected" ? selection.resourceId : null);
    window.history.replaceState(null, "", `${window.location.pathname}${search}`);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }

  const previousWindow = shiftBudgetWindow(query, -1);
  const nextWindow = shiftBudgetWindow(query, 1);

  const funds = data?.funds;
  const cloudResources = data?.cloud_resources ?? [];
  const hasFunds = funds !== null && funds !== undefined && funds.components.length > 0;
  if (selection.kind === "none" && !showUnconfigured && !error && !hasFunds && cloudResources.length === 0 && (data === null || data.resources.length === 0)) return null;
  return <section className="telemetry-panel" aria-labelledby="budget-account-title" aria-busy={busy} style={{ minWidth: 0, overflowWrap: "anywhere" }}>
    <div className="panel-heading"><h2 id="budget-account-title">API usage &amp; spend</h2>
      <button type="button" className="quiet-button" title="Reload stored readings" disabled={busy} onClick={() => selectWindow(advanceFinancialRead(query, new Date()))}>Refresh view</button>
    </div>
    <label htmlFor="budget-report-range">Report range</label>
    <select id="budget-report-range" value={days} disabled={busy} onChange={(event) => selectWindow(resizeBudgetWindow(query, event.target.value === "30" ? 30 : 7))}>
      <option value="7">7 completed UTC days</option><option value="30">30 completed UTC days</option>
    </select>
    <p data-budget-window data-period-start={query.period_start} data-period-end={query.period_end} data-read-as-of={query.as_of}>{bounds(query.period_start, query.period_end)}</p>
    <div role="group" aria-label="Stored history windows">
      <button type="button" className="quiet-button" disabled={busy || selection.kind === "invalid" || previousWindow === null} onClick={() => { if (previousWindow !== null) selectWindow(previousWindow); }}>Previous window</button>
      <button type="button" className="quiet-button" disabled={busy || selection.kind === "invalid" || nextWindow === null} onClick={() => { if (nextWindow !== null) selectWindow(nextWindow); }}>Next window</button>
      <button type="button" className="quiet-button" disabled={busy} onClick={() => selectWindow(latestBudgetWindow(days, new Date().toISOString()))}>Latest completed window</button>
    </div>
    <p>Stored readings as of <time dateTime={query.as_of}>{instant(query.as_of)}</time>. Window navigation does not collect provider data.</p>
    {busy && <p role="status">Reading stored financial reports…</p>}
    {error && <p role="alert">{error}</p>}
    {selection.kind === "invalid" && <p role="alert">This financial link is incomplete or invalid. Refresh view to select current stored data.</p>}
    {selection.kind === "selected" && selection.reportId !== null && <section aria-label="Selected financial report" data-report-id={selection.reportId}>
      <h3>Selected report</h3>
      <p>This is the report opened from Overview. Refresh view selects current stored readings.</p>
      <BudgetDailyHistory context={{ accountId: account.account_id, resourceId: selection.resourceId,
        reportId: selection.reportId, periodStart: selection.query.period_start,
        periodEnd: selection.query.period_end, asOf: selection.query.as_of }} onExpired={onExpired} showSummary />
    </section>}
    {data !== null && selection.kind !== "invalid" && <>
      {hasFunds && funds !== null && funds !== undefined ? <FundsReading funds={funds} /> : <p>Remaining funds not reported{funds === null || funds === undefined ? "." : `: ${readable(funds.availability.reason_code)}.`}</p>}
      {data.availability.state !== "available" && !(hasFunds && data.availability.reason_code === "billing_not_configured") && <p role="status">Spend data {data.availability.state}: {readable(data.availability.reason_code)}.</p>}
      {data.resources.length === 0 && cloudResources.length === 0 && data.availability.reason_code === "billing_not_configured" && <p>{hasFunds ? "No usage report for this interval." : "API billing is not set up."}</p>}
      {data.resources.filter(resource => selection.kind !== "selected" || resource.connection.resource_id === selection.resourceId).map(resource => <BillingCollectControl
        key={`${account.account_id}.${account.record_version}.${resource.connection.resource_id}.${resource.connection.record_version}.${resource.connection.scope_generation}.${query.period_start}.${query.period_end}`}
        account={account} connection={resource.connection} reportContext={collectionContext(query.period_start, query.period_end)}
        onExpired={onExpired} onCollected={() => selectWindow(advanceFinancialRead(query, new Date()))} />)}
      {cloudResources.filter(resource => selection.kind !== "selected" || resource.resource_id === selection.resourceId).map(resource => {
        const selectedReport = selection.kind === "selected" && selection.reportId !== null
          ? resource.reports.flatMap(value => [value.current, value.latest_attempt]).find(report => report?.report_id === selection.reportId) : undefined;
        const scope = cloudUsageScope(selectedReport?.source_category);
        return <CloudUsageCollectControl key={`${account.account_id}.${account.record_version}.${resource.resource_id}.${scope}.${query.period_start}.${query.period_end}`}
          account={account} resourceId={resource.resource_id} reportContext={cloudUsageContext(query.period_start, query.period_end, scope)}
          onExpired={onExpired} onCollected={() => selectWindow(advanceFinancialRead(query, new Date()))} />;
      })}
      {selection.kind === "selected" && selection.reportId !== null &&
        [...data.resources, ...cloudResources].filter(resource => ("connection" in resource ? resource.connection.resource_id : resource.resource_id) === selection.resourceId).map(resource => {
          const run = resource.latest_collection;
          return <p key="selected-collection-status" role="status">Collection status for this interval: {run === null ? readable(resource.collection_availability.reason_code) : <>
            {readable(run.state)} · {instant(run.completed_at ?? run.started_at ?? run.requested_at)}
            {run.error_code !== null && ` · ${readable(run.error_code)}`}
          </>}. The selected report remains unchanged.</p>;
        })}
      {!(selection.kind === "selected" && selection.reportId !== null) && <>
        {data.resources.filter(resource => selection.kind !== "selected" || resource.connection.resource_id === selection.resourceId).map((resource) => <ResourceReading key={`${resource.connection.resource_id}.${resource.connection.scope_generation}`} resource={resource} accountId={account.account_id} asOf={data.as_of} onExpired={onExpired} />)}
        {cloudResources.filter(resource => selection.kind !== "selected" || resource.resource_id === selection.resourceId).map((resource) => <ResourceReading key={resource.resource_id} resource={resource} accountId={account.account_id} asOf={data.as_of} onExpired={onExpired} />)}
      </>}
    </>}
  </section>;
}
