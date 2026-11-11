import { useEffect, useRef, useState } from "react";

import {
  budgets,
  type AccountBudgetCurrentWireV1,
  type AccountViewV1,
  type BudgetReportWireV1,
  type BudgetResourceCurrentWireV1,
} from "../../shared/api/client";
import { completedPeriod, displayMoney, exactMoneyText } from "./budgetPresentation";
import { advanceFinancialRead } from "./billingCheckPresentation";
import { canRetainFinancialReading, type FinancialReadContext } from "./financialReadPresentation";

const readable = (value: string) => value.replaceAll("_", " ");
const instant = (value: string) => new Date(value).toLocaleString(undefined, { timeZoneName: "short" });
const bounds = (start: string, end: string) => `${start.slice(0, 10)} to ${end.slice(0, 10)} UTC (end exclusive)`;

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

function ResourceReading({ resource }: Readonly<{ resource: BudgetResourceCurrentWireV1 }>) {
  const run = resource.latest_collection;
  return <article>
    <p><strong>Provider billing scope:</strong> {resource.connection.scope_id ?? "Not established"} · {readable(resource.connection.scope_evidence)}</p>
    <p>API monitoring: {resource.connection.monitoring_preference === "enabled" ? "on" : "off"}.</p>
    {run !== null && <p role={run.state === "failed" || run.state === "blocked" ? "status" : undefined}>
      Latest collection: {readable(run.state)} · {instant(run.completed_at ?? run.started_at ?? run.requested_at)}
      {run.error_code !== null && ` · ${readable(run.error_code)}`}
    </p>}
    {run === null && <p>{resource.collection_availability.reason_code === "budget_collection_not_started"
      ? "No collection has started." : "Collection status is unavailable."}</p>}
    {resource.reports.length === 0 && <p>{resource.report_availability.reason_code === "budget_current_reports_absent"
      ? "No report for this interval." : `Reports unavailable: ${readable(resource.report_availability.reason_code)}.`}</p>}
    {resource.reports.map((selection) => {
      const report = selection.current;
      const attempt = selection.latest_attempt;
      const key = report?.report_id ?? attempt?.report_id ?? "no-report";
      const spend = resource.reported_spend.find((value) => value.report_id === report?.report_id);
      return <section key={key}>
        {report === null ? <p>No complete report for this financial context.</p> : <>
          <p><strong>Reported spend: </strong>{spend?.total != null ? <span title={exactMoneyText(spend.total)}>{displayMoney(spend.total)}</span>
            : `Unavailable · ${readable(spend?.reason_code ?? "reported_spend_unavailable")}`}</p>
          <p>{bounds(report.requested_period.start, report.requested_period.end)} · {readable(report.cost_basis)} · {readable(report.source_category)}</p>
          <p>Data through: {report.source_data_through === null ? "Not reported" : instant(report.source_data_through)} · Collected: {instant(report.collected_at)}</p>
          {report.cost_buckets.length === 0 && report.usage_buckets.length === 0 && <p>No reported usage in this interval.</p>}
          {report.grouping.length === 0 && <CostHistory key={report.report_id} report={report} />}
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
    <p>Remaining funds not reported.</p>
  </article>;
}

export function BudgetAccountPanel({ account, showUnconfigured, onExpired, readRevision }: Readonly<{
  account: AccountViewV1;
  showUnconfigured: boolean;
  onExpired: () => void;
  readRevision: number;
}>) {
  const [days, setDays] = useState<7 | 30>(7);
  const [query, setQuery] = useState(() => completedPeriod(7, new Date()));
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
  }

  if (!showUnconfigured && !error && (data === null || data.resources.length === 0)) return null;
  return <section className="telemetry-panel" aria-labelledby="budget-account-title" aria-busy={busy} style={{ minWidth: 0, overflowWrap: "anywhere" }}>
    <div className="panel-heading"><h2 id="budget-account-title">API usage &amp; spend</h2>
      <button type="button" className="quiet-button" disabled={busy} onClick={() => refresh(days)}>Refresh readings</button>
    </div>
    <label htmlFor="budget-report-range">Report range</label>
    <select id="budget-report-range" value={days} onChange={(event) => refresh(event.target.value === "30" ? 30 : 7)}>
      <option value="7">Last 7 completed UTC days</option><option value="30">Last 30 completed UTC days</option>
    </select>
    <p>{bounds(query.period_start, query.period_end)}</p>
    {busy && <p role="status">Reading stored financial reports…</p>}
    {error && <p role="alert">{error}</p>}
    {data !== null && <>
      {data.availability.state !== "available" && <p role="status">Financial data {data.availability.state}: {readable(data.availability.reason_code)}.</p>}
      {data.resources.length === 0 && data.availability.reason_code === "billing_not_configured" && <p>API billing is not set up.</p>}
      {data.resources.map((resource) => <ResourceReading key={`${resource.connection.resource_id}.${resource.connection.scope_generation}`} resource={resource} />)}
    </>}
  </section>;
}
