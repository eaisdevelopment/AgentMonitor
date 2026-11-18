import { useEffect, useRef, useState } from "react";

import {
  budgets,
  type AccountBudgetSummaryWireV1,
  type AccountViewV1,
  type BillingReportContextV2,
  type BudgetCloudResourceSummaryWireV1,
  type BudgetResourceSummaryWireV1,
} from "../../shared/api/client";
import { completedPeriod, displayMoney, exactMoneyText } from "./budgetPresentation";
import { BudgetDailyHistory } from "./BudgetDailyHistory";
import { BudgetFundsHistory } from "./BudgetFundsHistory";
import { BudgetSourceHistory } from "./BudgetSourceHistory";
import { BillingReportSelector } from "./BillingReportSelector";
import { BillingCollectControl } from "./BillingCollectControl";
import { billingContextForView, type BillingReportSelection } from "./billingCollectPresentation";
import { CloudUsageCollectControl } from "./CloudUsageCollectControl";
import { cloudUsageContext, cloudUsageScope, cloudUsageGrouping } from "./cloudUsageCollectPresentation";
import { budgetWindowDays, budgetWindowSearch, latestBudgetWindow, resizeBudgetWindow, shiftBudgetWindow, type BudgetWindow } from "./budgetWindowNavigation";
import { advanceFinancialRead } from "./billingCheckPresentation";
import { billingReportCollectable, cloudReportCollectable, canRetainFinancialReading, selectedFinancialReport, type FinancialReadContext } from "./financialReadPresentation";

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

function FundsReading({ funds, periodStart, periodEnd, onExpired }: Readonly<{ funds: Funds; periodStart: string; periodEnd: string; onExpired: () => void }>) {
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
      {(component.remaining.value?.currency ?? component.limit.value?.currency) !== undefined && component.subject.resource_id !== null && <BudgetFundsHistory
        accountId={funds.account_id} resourceId={component.subject.resource_id} windowId={component.component_id}
        sourceId={component.provenance.source_id} currency={(component.remaining.value?.currency ?? component.limit.value?.currency)!}
        asOf={funds.as_of} periodStart={periodStart} periodEnd={periodEnd} onExpired={onExpired} />}
      {(component.remaining.value?.currency ?? component.limit.value?.currency) === undefined && <p>Balance history cannot be displayed until this source establishes the currency. Older observations may still be retained.</p>}
      {component.subject.resource_id === null && <p>Balance history is unavailable because this reading has no resource identity.</p>}
    </article>)}
  </section>;
}

function ResourceReading({ resource, accountId, asOf, onExpired, cloudScope, cloudGrouping = [], billingContext }: Readonly<{ resource: BudgetResourceSummaryWireV1 | BudgetCloudResourceSummaryWireV1; accountId: string; asOf: string; onExpired: () => void; cloudScope?: "self" | "team"; cloudGrouping?: readonly "model"[]; billingContext?: BillingReportContextV2 }>) {
  const run = resource.latest_collection;
  const billingReports = billingContext === undefined ? resource.reports : resource.reports.map(value => ({
    current: value.current?.source_category === billingContext.source_category && JSON.stringify(value.current.grouping) === JSON.stringify(billingContext.grouping ?? []) ? value.current : null,
    latest_attempt: value.latest_attempt?.source_category === billingContext.source_category && JSON.stringify(value.latest_attempt.grouping) === JSON.stringify(billingContext.grouping ?? []) ? value.latest_attempt : null,
  })).filter(value => value.current !== null || value.latest_attempt !== null);
  const reports = cloudScope === undefined ? billingReports : resource.reports.map(value => ({
    current: value.current?.source_category === `${cloudScope}_requests_and_cost` && JSON.stringify(value.current.grouping) === JSON.stringify(cloudGrouping) ? value.current : null,
    latest_attempt: value.latest_attempt?.source_category === `${cloudScope}_requests_and_cost` && JSON.stringify(value.latest_attempt.grouping) === JSON.stringify(cloudGrouping) ? value.latest_attempt : null,
  })).filter(value => value.current !== null || value.latest_attempt !== null);
  return <article data-cloud-reading={"connection" in resource ? undefined : resource.resource_id} data-usage-scope={cloudScope} data-usage-grouping={cloudScope === undefined ? undefined : cloudGrouping[0] ?? "all"}>
    {"connection" in resource ? <>
      <p><strong>Provider billing scope:</strong> {resource.connection.scope_id ?? "Not established"} · {readable(resource.connection.scope_evidence)}</p>
      <p>API monitoring: {resource.connection.monitoring_preference === "enabled" ? "on" : "off"}.</p>
    </> : <p><strong>Cloud usage</strong> · {readable(resource.lifecycle)}</p>}
    {run !== null && <p role={run.state === "failed" || run.state === "blocked" ? "status" : undefined}>
      {"connection" in resource ? "Ungrouped cost collection" : "Self · All usage collection"}: {readable(run.state)} · {instant(run.completed_at ?? run.started_at ?? run.requested_at)}
      {run.error_code !== null && ` · ${readable(run.error_code)}`}
    </p>}
    {run === null && <p>{"connection" in resource ? resource.collection_availability.reason_code === "budget_collection_not_started"
      ? "No ungrouped cost collection has started." : "Ungrouped cost collection status is unavailable." : "Self · All usage collection status is unavailable."}</p>}
    {reports.length === 0 && cloudScope !== undefined && <p>{resource.report_availability.state === "available" || resource.report_availability.reason_code === "budget_current_reports_absent"
      ? `No retained ${cloudScope}${cloudGrouping.length > 0 ? " model breakdown" : " report"} for this interval.` : `Reports unavailable: ${readable(resource.report_availability.reason_code)}.`}</p>}
    {reports.length === 0 && cloudScope === undefined && <p>{resource.report_availability.state === "available" || resource.report_availability.reason_code === "budget_current_reports_absent"
      ? "No retained report for this view and interval." : `Reports unavailable: ${readable(resource.report_availability.reason_code)}.`}</p>}
    {reports.map((selection) => {
      const report = selection.current ?? selection.latest_attempt;
      const attempt = selection.latest_attempt;
      const key = report?.report_id ?? attempt?.report_id ?? "no-report";
      const spend = resource.reported_spend.find((value) => value.report_id === report?.report_id);
      const modelBreakdown = report?.provider_key === "ollama" && report.grouping.includes("model");
      return <section key={key} data-report-id={report?.report_id}>
        {selection.current === null && report !== null && <p>Partial evidence only. No complete-period total is available.</p>}
        {report === null ? <p>No complete report for this financial context.</p> : <>
          {modelBreakdown ? <><p>Model breakdown · report totals remain in All usage.</p>{report.currency === null && report.cost_bucket_count === 0 && report.usage_bucket_count > 0 && <p>Provider did not report costs.</p>}</> : report.currency === null && report.cost_bucket_count === 0 && report.usage_bucket_count > 0
            ? <p>Provider did not report costs.</p>
            : <p><strong>{report.source_category === "cost_tokens" ? "Token charges only (excludes other costs): " : "Reported spend: "}</strong>{spend?.total != null ? <span title={exactMoneyText(spend.total)}>{displayMoney(spend.total)}</span>
              : `Unavailable · ${readable(spend?.reason_code ?? "reported_spend_unavailable")}`}</p>}
          {!("connection" in resource) && <p><strong>Provider billing scope:</strong> {report.scope_id ?? "Not established"} · {readable(report.scope_evidence)}</p>}
          <p>{bounds(report.requested_period.start, report.requested_period.end)} · {readable(report.cost_basis)} · {readable(report.source_category)}</p>
          <p>Data through: {report.source_data_through === null ? "Not reported" : instant(report.source_data_through)} · Collected: {instant(report.collected_at)}</p>
          {report.grouping.length > 0 && report.cost_bucket_count === 0 && report.usage_bucket_count === 0 && <p>No reported usage in this interval.</p>}
          {<BudgetDailyHistory context={{ accountId,
            resourceId: "connection" in resource ? resource.connection.resource_id : resource.resource_id,
            reportId: report.report_id, periodStart: report.requested_period.start,
            periodEnd: report.requested_period.end, asOf }} onExpired={onExpired} />}
          <details><summary>Source details</summary>
            <dl className="telemetry-readouts">
              <div><dt>Source</dt><dd>{report.source_id}</dd></div>
              <div><dt>Report</dt><dd style={{ overflowWrap: "anywhere" }}>{report.report_id}</dd></div>
              <div><dt>Coverage</dt><dd>{report.covered_period === null ? "Not reported" : bounds(report.covered_period.start, report.covered_period.end)}</dd></div>
              <div><dt>Completeness</dt><dd>{report.completeness}</dd></div>
              {!modelBreakdown && spend?.total != null && <div><dt>Exact reported spend</dt><dd style={{ overflowWrap: "anywhere" }}>{exactMoneyText(spend.total)}</dd></div>}
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

export function BudgetAccountPanel({ account, showUnconfigured, onExpired, readRevision, authorityRevision = 0, financialSearch = "" }: Readonly<{
  account: AccountViewV1;
  showUnconfigured: boolean;
  onExpired: () => void;
  readRevision: number;
  authorityRevision?: number;
  financialSearch?: string;
}>) {
  const selection = selectedFinancialReport(financialSearch);
  const [days, setDays] = useState<7 | 30>(() => (selection.kind === "selected" || selection.kind === "period") ? selection.days : 7);
  const [query, setQuery] = useState(() => (selection.kind === "selected" || selection.kind === "period") ? selection.query : completedPeriod(7, new Date()));
  const [snapshot, setSnapshot] = useState<Readonly<{ context: FinancialReadContext; data: AccountBudgetSummaryWireV1 }> | null>(null);
  const [pinnedMetadata, setPinnedMetadata] = useState<Readonly<{ identity: string; report: BillingReportSelection }> | null>(null);
  const pinnedIdentity = selection.kind === "selected" && selection.reportId !== null ? JSON.stringify([account.account_id, selection.resourceId, selection.reportId, selection.query]) : null;
  const pinnedReport = pinnedMetadata !== null && pinnedMetadata.identity === pinnedIdentity ? pinnedMetadata.report : null;
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const expired = useRef(onExpired);
  const lastReadRevision = useRef(readRevision);
  const lastFinancialSearch = useRef(financialSearch);
  expired.current = onExpired;
  const context: FinancialReadContext = { account, periodStart: query.period_start, periodEnd: query.period_end, readRevision, authorityRevision };
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
    setQuery((current) => advanceFinancialRead(current, new Date(), selection));
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
  }, [account, query, authorityRevision]);

  function selectWindow(next: BudgetWindow) {
    setDays(budgetWindowDays(next));
    setQuery(next);
    const current = new URLSearchParams(window.location.search);
    if (selection.kind === "selected" && selection.reportId !== null) {
      const cloudResource = data?.cloud_resources?.find(resource => resource.resource_id === selection.resourceId);
      const report = cloudResource === undefined ? undefined : pinnedReport ?? cloudResource.reports
        .flatMap(value => [value.current, value.latest_attempt]).find(value => value?.report_id === selection.reportId);
      if (report !== null && report !== undefined && ["self_requests_and_cost", "team_requests_and_cost"].includes(report.source_category)) {
        current.set("budget_scope", cloudUsageScope(report.source_category)!);
        current.delete("budget_grouping");
        if (report.grouping.length === 1 && report.grouping[0] === "model") current.set("budget_grouping", "model");
      }
    }
    if (selection.kind === "selected" && selection.reportId !== null) {
      const resource = data?.resources.find(value => value.connection.resource_id === selection.resourceId);
      const report = resource === undefined ? undefined : pinnedReport ?? resource.reports.flatMap(value => [value.current, value.latest_attempt]).find(value => value?.report_id === selection.reportId);
      if (report != null) {
        current.set("budget_category", report.source_category); current.delete("budget_grouping");
        if (report.grouping[0] !== undefined) current.set("budget_grouping", report.grouping[0]);
      }
    }
    const search = budgetWindowSearch(current.toString(), next, selection.kind === "selected" ? selection.resourceId : null);
    window.history.replaceState(null, "", `${window.location.pathname}${search}`);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }

  function reportHref(resourceId: string, reportId: string): string {
    const search = new URLSearchParams(budgetWindowSearch(window.location.search, query, resourceId));
    // Source history can select another scope; the immutable report keeps its own identity.
    search.delete("budget_scope");
    search.delete("budget_category"); search.delete("budget_grouping");
    search.set("budget_report", reportId);
    return `${window.location.pathname}?${search}`;
  }

  function selectReport(resourceId: string, reportId: string) {
    window.history.pushState(null, "", reportHref(resourceId, reportId));
    window.dispatchEvent(new PopStateEvent("popstate"));
  }

  function billingContextForResource(resource: BudgetResourceSummaryWireV1): BillingReportContextV2 | null {
    const pinned = selection.kind === "selected" && selection.resourceId === resource.connection.resource_id && selection.reportId !== null
      ? resource.reports.flatMap(value => [value.current, value.latest_attempt]).find(value => value?.report_id === selection.reportId) : undefined;
    const params = new URLSearchParams(financialSearch);
    const selected = selection.kind === "selected" && selection.resourceId === resource.connection.resource_id;
    const explicit = selected && params.has("budget_category") ? { source_category: params.get("budget_category")!, grouping: params.has("budget_grouping") ? [params.get("budget_grouping")!] : [] } : null;
    return billingContextForView(query.period_start, query.period_end,
      selection.kind === "selected" && selection.reportId !== null,
      pinnedReport ?? pinned ?? null, explicit);

  }

  function selectBillingReport(resourceId: string, category: string, grouping: readonly string[]) {
    const search = new URLSearchParams(budgetWindowSearch(window.location.search, query, resourceId));
    search.delete("budget_scope"); search.delete("budget_grouping");
    search.set("budget_category", category);
    if (grouping[0] !== undefined) search.set("budget_grouping", grouping[0]);
    window.history.pushState(null, "", `${window.location.pathname}?${search}`);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }

  function selectCloudScope(resourceId: string, scope: "self" | "team", grouping: readonly "model"[]) {
    const search = new URLSearchParams(budgetWindowSearch(window.location.search, query, resourceId));
    search.delete("budget_category"); search.delete("budget_grouping");
    search.set("budget_scope", scope);
    if (grouping[0] === "model") search.set("budget_grouping", "model");
    window.history.pushState(null, "", `${window.location.pathname}?${search}`);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }

  function scopeForResource(resource: BudgetCloudResourceSummaryWireV1): "self" | "team" | null {
    const report = selection.kind === "selected" && selection.reportId !== null
      ? resource.reports.flatMap(value => [value.current, value.latest_attempt]).find(value => value?.report_id === selection.reportId) : undefined;
    const explicit = selection.kind === "selected" && selection.resourceId === resource.resource_id ? new URLSearchParams(financialSearch).get("budget_scope") : null;
    const known = selection.kind === "selected" && selection.resourceId === resource.resource_id && selection.reportId !== null ? pinnedReport ?? report : report;
    if (selection.kind === "selected" && selection.reportId !== null && known == null) return null;
    return cloudUsageScope(known?.source_category, explicit);
  }

  function groupingForResource(resource: BudgetCloudResourceSummaryWireV1): readonly "model"[] | null {
    const selected = selection.kind === "selected" && selection.resourceId === resource.resource_id;
    const report = selected && selection.reportId !== null ? pinnedReport ?? resource.reports
      .flatMap(value => [value.current, value.latest_attempt]).find(value => value?.report_id === selection.reportId) : undefined;
    if (selected && selection.reportId !== null && report == null) return null;
    return cloudUsageGrouping(report?.grouping, selected ? new URLSearchParams(financialSearch).get("budget_grouping") : null);
  }

  const pinnedContextPending = pinnedIdentity !== null && pinnedReport === null && (
    data?.resources.some(resource => resource.connection.resource_id === (selection.kind === "selected" ? selection.resourceId : null)) === true ||
    data?.cloud_resources?.some(resource => resource.resource_id === (selection.kind === "selected" ? selection.resourceId : null)) === true);
  const previousWindow = shiftBudgetWindow(query, -1);
  const nextWindow = shiftBudgetWindow(query, 1);

  const funds = data?.funds;
  const cloudResources = data?.cloud_resources ?? [];
  const scopeResourceUnavailable = data !== null && selection.kind === "selected" && new URLSearchParams(financialSearch).has("budget_scope") &&
    !cloudResources.some(resource => resource.resource_id === selection.resourceId);
  const hasFunds = funds !== null && funds !== undefined && funds.components.length > 0;
  if (selection.kind === "none" && !showUnconfigured && !error && !hasFunds && cloudResources.length === 0 && (data === null || data.resources.length === 0)) return null;
  return <section className="telemetry-panel" aria-labelledby="budget-account-title" aria-busy={busy} style={{ minWidth: 0, overflowWrap: "anywhere" }}>
    <div className="panel-heading"><h2 id="budget-account-title">API usage &amp; spend</h2>
      <button type="button" className="quiet-button" title="Reload stored readings" disabled={busy || pinnedContextPending} onClick={() => selectWindow(advanceFinancialRead(query, new Date()))}>Refresh view</button>
    </div>
    <label htmlFor="budget-report-range">Report range</label>
    <select id="budget-report-range" value={days} disabled={busy || pinnedContextPending} onChange={(event) => selectWindow(resizeBudgetWindow(query, event.target.value === "30" ? 30 : 7))}>
      <option value="7">7 completed UTC days</option><option value="30">30 completed UTC days</option>
    </select>
    <p data-budget-window data-period-start={query.period_start} data-period-end={query.period_end} data-read-as-of={query.as_of}>{bounds(query.period_start, query.period_end)}</p>
    <div role="group" aria-label="Stored history windows">
      <button type="button" className="quiet-button" disabled={busy || pinnedContextPending || selection.kind === "invalid" || previousWindow === null} onClick={() => { if (previousWindow !== null) selectWindow(previousWindow); }}>Previous window</button>
      <button type="button" className="quiet-button" disabled={busy || pinnedContextPending || selection.kind === "invalid" || nextWindow === null} onClick={() => { if (nextWindow !== null) selectWindow(nextWindow); }}>Next window</button>
      <button type="button" className="quiet-button" disabled={busy} onClick={() => selectWindow(latestBudgetWindow(days, new Date().toISOString()))}>Latest completed window</button>
    </div>
    <p>Stored readings as of <time dateTime={query.as_of}>{instant(query.as_of)}</time>. Window navigation does not collect provider data.</p>
    {busy && <p role="status">Reading stored financial reports…</p>}
    {error && <p role="alert">{error}</p>}
    {selection.kind === "invalid" && <p role="alert">This financial link is incomplete or invalid. Refresh view to select current stored data.</p>}
    {scopeResourceUnavailable && <p role="alert">The selected usage scope does not match an available cloud resource. Return to the account to select current stored data.</p>}
    {selection.kind === "selected" && selection.reportId !== null && <section aria-label="Selected financial report" data-report-id={selection.reportId}>
      <h3>Selected report</h3>
      <p>This report is pinned to its original scope and stored snapshot. Refresh view selects current stored readings.</p>
      <BudgetDailyHistory context={{ accountId: account.account_id, resourceId: selection.resourceId,
        reportId: selection.reportId, periodStart: selection.query.period_start,
        periodEnd: selection.query.period_end, asOf: selection.query.as_of }} onExpired={onExpired} showSummary onReport={report => {
          if (pinnedIdentity !== null) setPinnedMetadata(current => current?.identity === pinnedIdentity ? current : { identity: pinnedIdentity, report });
        }} />
    </section>}
    {data !== null && selection.kind !== "invalid" && !scopeResourceUnavailable && <>
      {hasFunds && funds !== null && funds !== undefined ? <FundsReading funds={funds} periodStart={query.period_start} periodEnd={query.period_end} onExpired={onExpired} /> : <p>Remaining funds not reported{funds === null || funds === undefined ? "." : `: ${readable(funds.availability.reason_code)}.`}</p>}
      {data.availability.state !== "available" && !(hasFunds && data.availability.reason_code === "billing_not_configured") && <p role="status">Spend data {data.availability.state}: {readable(data.availability.reason_code)}.</p>}
      {data.resources.length === 0 && cloudResources.length === 0 && data.availability.reason_code === "billing_not_configured" && <p>{hasFunds ? "No usage report for this interval." : "API billing is not set up."}</p>}
      {selection.kind === "selected" && selection.reportId !== null && data.resources
        .filter(resource => resource.connection.resource_id === selection.resourceId && !billingReportCollectable(selection, resource))
        .map(resource => <div key={`historical-${resource.connection.resource_id}`} data-historical-scope="true">
          <button type="button" disabled>Collect now</button>
          <p role="status">Historical or unconfirmed scope — return to current scope to collect. Use Latest completed window.</p>
        </div>)}
      {data.resources.filter(resource => selection.kind !== "selected" || resource.connection.resource_id === selection.resourceId).map(resource => <BillingReportSelector
        key={`${account.account_id}.${resource.connection.resource_id}.${resource.connection.record_version}`}
        account={account} connection={resource.connection} context={billingContextForResource(resource)} periodStart={query.period_start} periodEnd={query.period_end} onExpired={onExpired}
        onSelect={option => selectBillingReport(resource.connection.resource_id, option.source_category, option.grouping)} />)}
      {data.resources.filter(resource => billingReportCollectable(selection, resource) && billingContextForResource(resource) !== null).map(resource => <BillingCollectControl
        key={`${account.account_id}.${account.record_version}.${resource.connection.resource_id}.${resource.connection.record_version}.${resource.connection.scope_generation}.${query.period_start}.${query.period_end}.${JSON.stringify(billingContextForResource(resource))}`}
        account={account} connection={resource.connection} reportContext={billingContextForResource(resource)!}
        onExpired={onExpired} onCollected={() => selectWindow(advanceFinancialRead(query, new Date()))} />)}
      {cloudResources.filter(resource => selection.kind !== "selected" || resource.resource_id === selection.resourceId).map(resource => {
        const scope = scopeForResource(resource);
        const grouping = groupingForResource(resource);
        return <div key={`scope-${resource.resource_id}`}>
          <label>Usage scope <select aria-label="Usage scope" value={scope ?? ""} disabled={busy} onChange={event => {
            if (event.target.value === "self" || event.target.value === "team") selectCloudScope(resource.resource_id, event.target.value, grouping ?? []);
          }}>
            {scope === null && <option value="" disabled>Choose scope for a new request</option>}
            <option value="self">Self</option><option value="team">Team</option>
          </select></label>
          <label>Usage breakdown <select aria-label="Usage breakdown" value={grouping === null ? "" : grouping[0] ?? "all"} disabled={busy || scope === null} onChange={event => {
            if (scope !== null && (event.target.value === "all" || event.target.value === "model")) selectCloudScope(resource.resource_id, scope, event.target.value === "model" ? ["model"] : []);
          }}>
            {grouping === null && <option value="" disabled>Choose a breakdown</option>}
            <option value="all">All usage</option><option value="model">Model</option>
          </select></label>
          {grouping === null && scope !== null && <p role="status">The selected report does not establish this breakdown. Choose All usage or Model to leave the pinned report; no collection starts automatically.</p>}
          {scope === null && <p role="status">The selected report does not establish this collection scope. Choose Self or Team to leave the pinned report; no collection starts automatically.</p>}
        </div>;
      })}
      {selection.kind === "selected" && selection.reportId !== null && cloudResources
        .filter(resource => resource.resource_id === selection.resourceId && !cloudReportCollectable(selection, resource))
        .map(resource => <div key={`historical-${resource.resource_id}`} data-historical-scope="true">
          <button type="button" disabled>Collect usage</button>
          <p role="status">Historical or unconfirmed scope — return to current scope to collect. Use Latest completed window.</p>
        </div>)}
      {cloudResources.filter(resource => cloudReportCollectable(selection, resource)).map(resource => {
        const scope = scopeForResource(resource);
        const grouping = groupingForResource(resource);
        if (scope === null || grouping === null) return null;
        return <CloudUsageCollectControl key={`${account.account_id}.${account.record_version}.${resource.resource_id}.${scope}.${grouping[0] ?? "all"}.${query.period_start}.${query.period_end}`}
          account={account} resourceId={resource.resource_id} reportContext={cloudUsageContext(query.period_start, query.period_end, scope, grouping)}
          onExpired={onExpired} onCollected={() => selectWindow(advanceFinancialRead(query, new Date()))} />;
      })}
      {selection.kind === "selected" && selection.reportId !== null &&
        [...data.resources, ...cloudResources].filter(resource => ("connection" in resource ? resource.connection.resource_id : resource.resource_id) === selection.resourceId).map(resource => {
          const run = resource.latest_collection;
          return <p key="selected-collection-status" role="status">{"connection" in resource ? "Ungrouped cost collection for this interval" : "Resource collection status"}: {run === null ? readable(resource.collection_availability.reason_code) : <>
            {readable(run.state)} · {instant(run.completed_at ?? run.started_at ?? run.requested_at)}
            {run.error_code !== null && ` · ${readable(run.error_code)}`}
          </>}. The selected report remains unchanged.</p>;
        })}
      {!(selection.kind === "selected" && selection.reportId !== null) && <>
        {data.resources.filter(resource => selection.kind !== "selected" || resource.connection.resource_id === selection.resourceId).map((resource) => <ResourceReading key={`${resource.connection.resource_id}.${resource.connection.scope_generation}`} resource={resource} accountId={account.account_id} asOf={data.as_of} onExpired={onExpired} billingContext={billingContextForResource(resource) ?? undefined} />)}
        {cloudResources.filter(resource => selection.kind !== "selected" || resource.resource_id === selection.resourceId).map((resource) => <ResourceReading key={resource.resource_id} resource={resource} accountId={account.account_id} asOf={data.as_of} onExpired={onExpired} cloudScope={scopeForResource(resource) ?? "self"} cloudGrouping={groupingForResource(resource) ?? []} />)}
      </>}
      {[...new Set([...data.resources.map(resource => resource.connection.resource_id), ...cloudResources.map(resource => resource.resource_id)])]
        .filter(resourceId => selection.kind !== "selected" || resourceId === selection.resourceId)
        .map(resourceId => <BudgetSourceHistory key={resourceId} accountId={account.account_id} resourceId={resourceId} query={query} onExpired={onExpired}
          reportHref={reportId => reportHref(resourceId, reportId)} onSelect={reportId => selectReport(resourceId, reportId)} />)}
    </>}
  </section>;
}
