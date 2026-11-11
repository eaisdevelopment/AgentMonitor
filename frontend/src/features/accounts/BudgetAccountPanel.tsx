import { useEffect, useRef, useState } from "react";

import {
  budgets,
  type AccountBudgetCurrentWireV1,
  type AccountViewV1,
  type BudgetCloudResourceCurrentWireV1,
  type BudgetReportWireV1,
  type BudgetResourceCurrentWireV1,
  type BudgetSelectedReportWireV1,
} from "../../shared/api/client";
import { completedPeriod, displayMoney, exactMoneyText, exactUsageText } from "./budgetPresentation";
import { advanceFinancialRead } from "./billingCheckPresentation";
import { canRetainFinancialReading, selectedFinancialReport, type FinancialReadContext } from "./financialReadPresentation";

const readable = (value: string) => value.replaceAll("_", " ");
const instant = (value: string) => new Date(value).toLocaleString(undefined, { timeZoneName: "short" });
const bounds = (start: string, end: string) => `${start.slice(0, 10)} to ${end.slice(0, 10)} UTC (end exclusive)`;

type Funds = NonNullable<AccountBudgetCurrentWireV1["funds"]>;
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

function CostHistory({ report }: Readonly<{ report: BudgetReportWireV1 }>) {
  const [limit, setLimit] = useState(50);
  if (report.cost_buckets.length === 0) return <p>No reported cost buckets in this interval.</p>;
  return <>
    <div className="table-scroll" tabIndex={0} role="region" aria-label="Exact cost history">
      <table><caption>Cost history · source intervals, exact amounts</caption>
        <thead><tr><th scope="col">Period (UTC)</th><th scope="col">Amount</th><th scope="col">Kind</th></tr></thead>
        <tbody>{report.cost_buckets.slice(0, limit).map((row) => <tr key={row.bucket_key}>
          <td>{bounds(row.period.start, row.period.end)}</td><td>{exactMoneyText(row.amount)}</td><td>{row.kind}</td>
        </tr>)}</tbody>
      </table>
    </div>
    {limit < report.cost_buckets.length && <button type="button" className="quiet-button" onClick={() => setLimit((value) => value + 50)}>Show more cost rows</button>}
  </>;
}

function UsageHistory({ report }: Readonly<{ report: BudgetReportWireV1 }>) {
  const [limit, setLimit] = useState(50);
  if (report.usage_buckets.length === 0) return null;
  return <>
    <div className="table-scroll" tabIndex={0} role="region" aria-label="Exact usage history">
      <table><caption>Usage history · source intervals, exact quantities</caption>
        <thead><tr><th scope="col">Period (UTC)</th><th scope="col">Usage</th></tr></thead>
        <tbody>{report.usage_buckets.slice(0, limit).map((row) => <tr key={row.bucket_key} data-usage-bucket={row.bucket_key}>
          <td>{bounds(row.period.start, row.period.end)}</td><td>{exactUsageText(row.quantity)}</td>
        </tr>)}</tbody>
      </table>
    </div>
    {limit < report.usage_buckets.length && <button type="button" className="quiet-button" onClick={() => setLimit((value) => value + 50)}>Show more usage rows</button>}
  </>;
}

function ResourceReading({ resource }: Readonly<{ resource: BudgetResourceCurrentWireV1 | BudgetCloudResourceCurrentWireV1 }>) {
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
      ? "No report for this interval." : `Reports unavailable: ${readable(resource.report_availability.reason_code)}.`}</p>}
    {resource.reports.map((selection) => {
      const report = selection.current ?? selection.latest_attempt;
      const attempt = selection.latest_attempt;
      const key = report?.report_id ?? attempt?.report_id ?? "no-report";
      const spend = resource.reported_spend.find((value) => value.report_id === report?.report_id);
      return <section key={key} data-report-id={report?.report_id}>
        {selection.current === null && report !== null && <p>Partial evidence only. No complete-period total is available.</p>}
        {report === null ? <p>No complete report for this financial context.</p> : <>
          {report.currency === null && report.cost_buckets.length === 0 && report.usage_buckets.length > 0
            ? <p>Provider did not report costs.</p>
            : <p><strong>Reported spend: </strong>{spend?.total != null ? <span title={exactMoneyText(spend.total)}>{displayMoney(spend.total)}</span>
              : `Unavailable · ${readable(spend?.reason_code ?? "reported_spend_unavailable")}`}</p>}
          {!("connection" in resource) && <p><strong>Provider billing scope:</strong> {report.scope_id ?? "Not established"} · {readable(report.scope_evidence)}</p>}
          <p>{bounds(report.requested_period.start, report.requested_period.end)} · {readable(report.cost_basis)} · {readable(report.source_category)}</p>
          <p>Data through: {report.source_data_through === null ? "Not reported" : instant(report.source_data_through)} · Collected: {instant(report.collected_at)}</p>
          {report.cost_buckets.length === 0 && report.usage_buckets.length === 0 && <p>No reported usage in this interval.</p>}
          {report.grouping.length === 0 && <>
            {report.cost_buckets.length > 0 && <CostHistory key={`cost-${report.report_id}`} report={report} />}
            <UsageHistory key={`usage-${report.report_id}`} report={report} />
          </>}
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
  const [days, setDays] = useState<7 | 30>(() => selection.kind === "selected" ? selection.days : 7);
  const [query, setQuery] = useState(() => selection.kind === "selected" ? selection.query : completedPeriod(7, new Date()));
  const [pinned, setPinned] = useState<BudgetSelectedReportWireV1 | null>(null);
  const [pinnedError, setPinnedError] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<Readonly<{ context: FinancialReadContext; data: AccountBudgetCurrentWireV1 }> | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const expired = useRef(onExpired);
  const lastReadRevision = useRef(readRevision);
  expired.current = onExpired;
  const context: FinancialReadContext = { account, periodStart: query.period_start, periodEnd: query.period_end, readRevision };
  // Fence the heading during render too, before an obsolete request's effect is cleaned up.
  const data = snapshot !== null && canRetainFinancialReading(snapshot.context, context) ? snapshot.data : null;

  useEffect(() => {
    if (selection.kind !== "selected" || selection.reportId === null) return;
    const controller = new AbortController();
    const reportId = selection.reportId;
    setPinned(null);
    setPinnedError(null);
    void budgets.report(selection.resourceId, { account_id: account.account_id,
      report_id: reportId, ...selection.query }, controller.signal).then(result => {
      if (controller.signal.aborted) return;
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") expired.current();
        else setPinnedError("The selected report is unavailable or no longer retained. Refresh view to select current stored data.");
      } else if (result.data.report.report_id !== reportId || result.data.report.account_id !== account.account_id ||
          result.data.report.resource_id !== selection.resourceId) {
        setPinnedError("The selected report did not match this account and resource.");
      } else setPinned(result.data);
    }).catch(() => { if (!controller.signal.aborted) setPinnedError("The selected report could not be read. Try again when the service is available."); });
    return () => controller.abort();
  }, [account.account_id, financialSearch]);

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
        const result = await budgets.account(account.account_id, query, controller.signal);
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

  function refresh(nextDays: 7 | 30) {
    const next = completedPeriod(nextDays, new Date());
    setDays(nextDays);
    setQuery(next);
    if (selection.kind !== "none") {
      const search = new URLSearchParams(window.location.search);
      for (const key of ["budget_selection", "budget_resource", "budget_report", "budget_start", "budget_end", "budget_as_of"]) search.delete(key);
      if (selection.kind === "selected") {
        search.set("budget_resource", selection.resourceId);
        search.set("budget_start", next.period_start);
        search.set("budget_end", next.period_end);
        search.set("budget_as_of", next.as_of);
      }
      window.history.replaceState(null, "", `${window.location.pathname}${search.size ? `?${search}` : ""}`);
      window.dispatchEvent(new PopStateEvent("popstate"));
    }
  }

  const funds = data?.funds;
  const cloudResources = data?.cloud_resources ?? [];
  const hasFunds = funds !== null && funds !== undefined && funds.components.length > 0;
  if (selection.kind === "none" && !showUnconfigured && !error && !hasFunds && cloudResources.length === 0 && (data === null || data.resources.length === 0)) return null;
  return <section className="telemetry-panel" aria-labelledby="budget-account-title" aria-busy={busy} style={{ minWidth: 0, overflowWrap: "anywhere" }}>
    <div className="panel-heading"><h2 id="budget-account-title">API usage &amp; spend</h2>
      <button type="button" className="quiet-button" title="Reload stored readings" disabled={busy} onClick={() => refresh(days)}>Refresh view</button>
    </div>
    <label htmlFor="budget-report-range">Report range</label>
    <select id="budget-report-range" value={days} onChange={(event) => refresh(event.target.value === "30" ? 30 : 7)}>
      <option value="7">Last 7 completed UTC days</option><option value="30">Last 30 completed UTC days</option>
    </select>
    <p>{bounds(query.period_start, query.period_end)}</p>
    {busy && <p role="status">Reading stored financial reports…</p>}
    {error && <p role="alert">{error}</p>}
    {selection.kind === "invalid" && <p role="alert">This financial link is incomplete or invalid. Refresh view to select current stored data.</p>}
    {selection.kind === "selected" && selection.reportId !== null && <section aria-label="Selected financial report" data-report-id={pinned?.report.report_id}>
      <h3>Selected report</h3>
      <p>This is the report opened from Overview. Refresh view selects current stored readings.</p>
      {pinnedError !== null ? <p role="alert">{pinnedError}</p> : pinned === null ? <p role="status">Reading the selected report…</p> : <>
        <p><strong>Reported spend: </strong>{pinned.reported_spend.total === null ? readable(pinned.reported_spend.reason_code) :
          <span title={exactMoneyText(pinned.reported_spend.total)}>{displayMoney(pinned.reported_spend.total)}</span>}</p>
        <p>Provider billing scope: {pinned.report.scope_id ?? "Not established"} · {readable(pinned.report.scope_evidence)}</p>
        <p>{bounds(pinned.report.requested_period.start, pinned.report.requested_period.end)} · {readable(pinned.report.cost_basis)} · {readable(pinned.report.source_category)}</p>
        <p>Data through: {pinned.report.source_data_through === null ? "Not reported" : instant(pinned.report.source_data_through)} · Collected: {instant(pinned.report.collected_at)} · {pinned.report.completeness}</p>
        {pinned.report.cost_buckets.length > 0 && <CostHistory report={pinned.report} />}
        <UsageHistory report={pinned.report} />
      </>}
    </section>}
    {data !== null && selection.kind !== "invalid" && <>
      {hasFunds && funds !== null && funds !== undefined ? <FundsReading funds={funds} /> : <p>Remaining funds not reported{funds === null || funds === undefined ? "." : `: ${readable(funds.availability.reason_code)}.`}</p>}
      {data.availability.state !== "available" && !(hasFunds && data.availability.reason_code === "billing_not_configured") && <p role="status">Spend data {data.availability.state}: {readable(data.availability.reason_code)}.</p>}
      {data.resources.length === 0 && cloudResources.length === 0 && data.availability.reason_code === "billing_not_configured" && <p>{hasFunds ? "No usage report for this interval." : "API billing is not set up."}</p>}
      {selection.kind === "selected" && selection.reportId !== null &&
        [...data.resources, ...cloudResources].filter(resource => ("connection" in resource ? resource.connection.resource_id : resource.resource_id) === selection.resourceId).map(resource => {
          const run = resource.latest_collection;
          return <p key="selected-collection-status" role="status">Collection status for this interval: {run === null ? readable(resource.collection_availability.reason_code) : <>
            {readable(run.state)} · {instant(run.completed_at ?? run.started_at ?? run.requested_at)}
            {run.error_code !== null && ` · ${readable(run.error_code)}`}
          </>}. The selected report remains unchanged.</p>;
        })}
      {!(selection.kind === "selected" && selection.reportId !== null) && <>
        {data.resources.filter(resource => selection.kind !== "selected" || resource.connection.resource_id === selection.resourceId).map((resource) => <ResourceReading key={`${resource.connection.resource_id}.${resource.connection.scope_generation}`} resource={resource} />)}
        {cloudResources.filter(resource => selection.kind !== "selected" || resource.resource_id === selection.resourceId).map((resource) => <ResourceReading key={resource.resource_id} resource={resource} />)}
      </>}
    </>}
  </section>;
}
