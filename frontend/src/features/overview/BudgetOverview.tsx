import { useEffect, useRef, useState } from "react";

import { budgets, type BudgetOverviewWireV1, type BudgetOverviewRowWireV1, type OrganizationViewV1 } from "../../shared/api/client";
import { completedPeriod, displayMoney, exactMoneyText } from "../accounts/budgetPresentation";
import { billingProviderDisplayName } from "../accounts/providerPresentation";
import { changeOverviewSearch, overviewSelection, safeOverviewSearch } from "./overviewSelection";
import { canReplaceFinancialOverview, financialAccountSelectors, financialReportDestination } from "./budgetOverviewPresentation";

const readable = (value: string) => value.replaceAll("_", " ");
const instant = (value: string) => new Date(value).toLocaleString(undefined, { timeZoneName: "short" });
const bounds = (start: string, end: string) => `${start.slice(0, 10)} to ${end.slice(0, 10)} UTC (end exclusive)`;
const fundLabels = { balance: "Balance", included_credits: "Included credits", purchased_credits: "Purchased credits", soft_limit: "Soft budget", hard_limit: "Hard limit" };

type Snapshot = Readonly<{ context: string; query: string; value: BudgetOverviewWireV1 }>;

export function BudgetOverview({ search, onSearchChange, onExpired, onOpenAccount, organizations, onSubscriptions }: Readonly<{
  search: string;
  onSearchChange: (search: string) => void;
  onExpired: () => void;
  onOpenAccount: (accountId: string, search?: string) => void;
  organizations: readonly OrganizationViewV1[];
  onSubscriptions: (ids: readonly string[] | null) => void;
}>) {
  const selection = overviewSelection(search);
  const [initialTime] = useState(() => new Date());
  const fallback = completedPeriod(selection.days, initialTime);
  const params = new URLSearchParams(safeOverviewSearch(search));
  const periodStart = params.get("period_start") ?? fallback.period_start;
  const periodEnd = params.get("period_end") ?? fallback.period_end;
  const asOf = params.get("as_of") ?? fallback.as_of;
  const query = {
    period_start: periodStart, period_end: periodEnd, as_of: asOf,
    ...(selection.organizationIds === null ? {} : { organization_ids: selection.organizationIds.join(",") }),
    include_ungrouped: selection.includeUngrouped,
    ...(selection.provider === null ? {} : { provider_key: selection.provider }),
    limit: 50,
  };
  const queryKey = JSON.stringify(query);
  const contextKey = JSON.stringify({ ...query, as_of: null });
  const [pageRequest, setPageRequest] = useState<Readonly<{ query: string; cursor: string; attempt: number }> | null>(null);
  const cursor = pageRequest?.query === queryKey ? pageRequest.cursor : undefined;
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const snapshotRef = useRef(snapshot);
  snapshotRef.current = snapshot;
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const callbacks = useRef({ onExpired, onSubscriptions, onSearchChange });
  callbacks.current = { onExpired, onSubscriptions, onSearchChange };
  const data = snapshot?.context === contextKey ? snapshot.value : null;

  useEffect(() => {
    if (params.get("period_start") === null || params.get("period_end") === null || params.get("as_of") === null) {
      callbacks.current.onSearchChange(changeOverviewSearch(search, { period_start: periodStart, period_end: periodEnd, as_of: asOf }));
    }
  }, [search, periodStart, periodEnd, asOf]);

  useEffect(() => {
    const controller = new AbortController();
    setBusy(true);
    setError(null);
    callbacks.current.onSubscriptions(null);
    void (async () => {
      try {
        const result = await budgets.overview({ ...query, ...(cursor === undefined ? {} : { cursor }) }, controller.signal);
        if (controller.signal.aborted) return;
        if (!result.ok) {
          if (result.problem.code === "dashboard_authentication_required") callbacks.current.onExpired();
          else setError("Financial overview could not be refreshed. Previous readings retain their original times; subscription quotas remain available.");
          return;
        }
        const value = result.data;
        if (!canReplaceFinancialOverview(value.availability.state)) {
          setError(`Financial overview ${value.availability.state}: ${readable(value.availability.reason_code)}. Previous readings retain their original times; subscription quotas remain available.`);
          return;
        }
        if (Date.parse(value.period.start) !== Date.parse(periodStart) || Date.parse(value.period.end) !== Date.parse(periodEnd) || Date.parse(value.as_of) !== Date.parse(asOf)) throw new Error("financial_context_mismatch");
        const previous = snapshotRef.current;
        let items = value.items;
        if (cursor !== undefined) {
          if (previous?.query !== queryKey || previous.value.registry_revision !== value.registry_revision || previous.value.page.next_cursor !== cursor) throw new Error("financial_inventory_changed");
          const seen = new Set(previous.value.items.map(row => row.row_id));
          if (items.some(row => seen.has(row.row_id))) throw new Error("financial_page_duplicate");
          items = [...previous.value.items, ...items];
        }
        setSnapshot({ context: contextKey, query: queryKey, value: { ...value, items } });
        callbacks.current.onSubscriptions(value.subscription_account_ids);
      } catch {
        if (!controller.signal.aborted) setError("Financial readings are unavailable or changed during pagination. Refresh view to retry; previous values have not been refreshed.");
      } finally {
        if (!controller.signal.aborted) setBusy(false);
      }
    })();
    return () => controller.abort();
  }, [queryKey, cursor, pageRequest?.attempt]);

  const organizationName = (id: string | null) => id === null ? "Ungrouped" : organizations.find(item => item.organization_id === id)?.name ?? "Organization unavailable";
  const [sortKey = "state", direction = "ascending"] = selection.financialSort.split(":");
  const rows = [...(data?.items ?? [])].sort((left, right) => {
    const primary = sortKey === "state" ? left.state_rank - right.state_rank : sortKey === "organization"
      ? organizationName(left.pool_id ? left.primary_organization_id ?? null : left.account.organization_id).localeCompare(organizationName(right.pool_id ? right.primary_organization_id ?? null : right.account.organization_id))
      : left.account.friendly_name.localeCompare(right.account.friendly_name);
    return (direction === "descending" ? -primary : primary)
      || organizationName(left.pool_id ? left.primary_organization_id ?? null : left.account.organization_id).localeCompare(organizationName(right.pool_id ? right.primary_organization_id ?? null : right.account.organization_id))
      || left.account.friendly_name.localeCompare(right.account.friendly_name) || left.row_id.localeCompare(right.row_id);
  });
  const sort = (key: string) => callbacks.current.onSearchChange(changeOverviewSearch(search, { financial_sort: `${key}:${sortKey === key && direction === "ascending" ? "descending" : "ascending"}` }));
  function refresh(days: 7 | 30) {
    setPageRequest(null);
    callbacks.current.onSearchChange(changeOverviewSearch(search, { range: String(days), ...completedPeriod(days, new Date()) }));
  }
  function open(row: BudgetOverviewRowWireV1, reportId?: string) {
    const context = reportId === undefined ? undefined : row.contexts.find(item => item.report_id === reportId);
    if (reportId !== undefined && context === undefined) return;
    const destination = financialReportDestination(row.account.account_id, row.resource_id, context);
    if (destination === null) return;
    const link = new URLSearchParams(safeOverviewSearch(search));
    for (const [key, value] of Object.entries(financialAccountSelectors(destination.resourceId, destination.reportId, { start: periodStart, end: periodEnd }, data?.as_of ?? asOf))) link.set(key, value);
    onOpenAccount(destination.accountId, safeOverviewSearch(link.toString(), true));
  }
  return <section className="fleet-overview financial-overview" aria-labelledby="overview-budget-title" aria-busy={busy}>
    <div className="fleet-overview-heading">
      <div><h2 id="overview-budget-title">API usage &amp; spend</h2><p>{bounds(periodStart, periodEnd)}</p></div>
      <label className="overview-provider-filter"><span>Report range</span><select value={selection.days} onChange={event => refresh(event.target.value === "30" ? 30 : 7)}><option value="7">Last 7 completed UTC days</option><option value="30">Last 30 completed UTC days</option></select></label>
      <button className="quiet-button" type="button" disabled={busy} title="Reload stored readings; collect a new report from account detail" onClick={() => refresh(selection.days)}>Refresh view</button>
    </div>
    {busy && <p className="fleet-overview-notice" role="status">Reading stored financial overview…</p>}
    {error !== null && <p className="fleet-overview-notice" role="alert">{error}</p>}
    {data !== null && <>
      <div className="financial-summary" aria-label="Reported spend summaries">
        {data.summaries.map((summary, index) => <p key={`${summary.scope_kind}:${summary.organization_id}:${summary.currency}:${summary.cost_basis}:${summary.source_category}:${index}`}>
          <strong>{summary.scope_kind === "global" ? "Filtered inventory" : organizationName(summary.organization_id)}: </strong>
          <span title={exactMoneyText(summary.total)}>{displayMoney(summary.total)}</span> · {readable(summary.cost_basis)} · {readable(summary.source_category)}
          {` · ${summary.included_pool_count} included pools · ${summary.excluded_resource_count} excluded resources`}
        </p>)}
        {data.summary_reason !== null && <p>{data.summaries.length === 0 ? "Spend totals unavailable" : "Spend subtotals are partial"}: {readable(data.summary_reason)}.</p>}
        {data.exclusions.map(item => <p key={item.reason_code}>{item.count} excluded: {readable(item.reason_code)}.</p>)}
      </div>
      <div className="fleet-overview-heading"><p>{rows.length} financial resource rows loaded · {data.inventory_count} accounts in selected scope</p>
        <label className="overview-provider-filter"><span>Sort financial rows</span><select value={selection.financialSort} onChange={event => onSearchChange(changeOverviewSearch(search, { financial_sort: event.target.value }))}>
          <option value="state:ascending">State · action required first</option><option value="state:descending">State · current first</option>
          <option value="organization:ascending">Organization · A to Z</option><option value="organization:descending">Organization · Z to A</option>
          <option value="account:ascending">Account · A to Z</option><option value="account:descending">Account · Z to A</option>
        </select></label>
      </div>
      {rows.length === 0 ? <p className="fleet-overview-notice">No API billing resources match these filters.</p> : <table className="fleet-overview-table financial-overview-table" aria-label="API billing overview">
        <thead><tr>
          <th scope="col" aria-sort={sortKey === "account" ? direction === "descending" ? "descending" : "ascending" : undefined}><button type="button" className="overview-sort-button" onClick={() => sort("account")}>Billing account</button></th>
          <th scope="col" aria-sort={sortKey === "organization" ? direction === "descending" ? "descending" : "ascending" : undefined}><button type="button" className="overview-sort-button" onClick={() => sort("organization")}>Organization</button></th>
          <th scope="col" aria-sort={sortKey === "state" ? direction === "descending" ? "descending" : "ascending" : undefined}><button type="button" className="overview-sort-button" onClick={() => sort("state")}>State</button></th>
          <th scope="col">Reported spend</th><th scope="col">Available</th><th scope="col">Data through</th>
        </tr></thead>
        <tbody>{rows.map(row => <tr key={row.row_id} data-financial-row={row.row_id} data-account-id={row.account.account_id} data-resource-id={row.resource_id ?? undefined}>
          <th scope="row" data-label="Billing account"><button type="button" className="overview-account-link" onClick={() => open(row, row.contexts[0]?.report_id)}>{row.pool_name ?? row.account.friendly_name}</button><small>{billingProviderDisplayName(row.account.provider_key)}{row.pool_selector ? ` · ${row.pool_selector}` : ""}</small>
            {row.pool_id && <small>Shared billing pool · {readable(row.association_evidence ?? "owner asserted")}</small>}
            {(row.access_paths?.length ?? 0) > 0 && <details><summary>{row.access_paths!.length} connected {row.access_paths!.length === 1 ? "account" : "accounts"}</summary>
              <ul>{row.access_paths!.map(path => <li key={`${path.account.account_id}:${path.resource_id}`}>
                <button type="button" className="overview-account-link" onClick={() => onOpenAccount(path.account.account_id, safeOverviewSearch(search))}>{path.account.friendly_name}</button>
                <small>{organizationName(path.account.organization_id)} · {readable(path.state_code)} · Monitoring {path.monitoring_enabled ? "on" : "off"}{path.collection_error ? ` · ${readable(path.collection_error)}` : ""}</small>
              </li>)}</ul>
            </details>}
          </th>
          <td data-label="Organization"><span>{organizationName(row.pool_id ? row.primary_organization_id ?? null : row.account.organization_id)}</span>
            {row.pool_id && <small>Counted under this organization{row.counted_in_selection === false ? " · Outside selected totals" : ""}</small>}
          </td>
          <td data-label="State"><span>{readable(row.state_code)}</span><small>API monitoring {row.monitoring_enabled ? "on" : "off"}</small>{row.collection_state !== null && <small>Collection: {readable(row.collection_state)}{row.collection_error !== null && ` · ${readable(row.collection_error)}`}</small>}</td>
          <td data-label="Reported spend">{row.contexts.length === 0 ? <span>No spending report</span> : row.contexts.map(context => <div key={context.report_id} data-overview-report={context.report_id}>
            {context.spend === null ? <span>Spend not reported · {readable(context.spend_reason)}</span> : <span title={exactMoneyText(context.spend)}>{displayMoney(context.spend)}</span>}
            <small>{readable(context.source_category)} · {readable(context.cost_basis)} · {readable(context.completeness)}</small>
            <small>Provider scope: {context.scope_id ?? "Not established"} · {readable(context.scope_evidence)}</small>
            <button type="button" className="quiet-button" onClick={() => open(row, context.report_id)}>View report</button>
          </div>)}</td>
          <td data-label="Available">{row.funds.length === 0 ? <span>Funds not reported{row.funds_reason_code === null ? "" : ` · ${readable(row.funds_reason_code)}`}</span> : row.funds.map(fund => <div key={fund.component_id} data-overview-fund={fund.component_id} className={fund.is_low === true ? "overview-fund-low" : undefined}>
            <strong>{fundLabels[fund.kind]}: </strong>{fund.remaining.value === null ? <span>{readable(fund.remaining.reason_code ?? fund.remaining.availability)}</span> : <span title={exactMoneyText(fund.remaining.value)}>{displayMoney(fund.remaining.value)}</span>}
            {fund.limit.value !== null && <small>Limit: <span title={exactMoneyText(fund.limit.value)}>{displayMoney(fund.limit.value)}</span></small>}
            {fund.percentage_text !== null && <small title={[fund.percentage_method, fund.percentage_rounding, fund.percentage_decimal_places === null ? null : `${fund.percentage_decimal_places} decimal places`].filter(value => value !== null).join(" · ")}>{fund.percentage_text}% remaining{fund.is_low === true ? " · Low" : ""}</small>}
            {row.pool_id && fund.source_account_id && <small>Funds from {row.access_paths?.find(path => path.account.account_id === fund.source_account_id)?.account.friendly_name ?? row.account.friendly_name}</small>}
            <small>Current as of <time dateTime={fund.observed_at ?? fund.collected_at}>{instant(fund.observed_at ?? fund.collected_at)}</time> · {readable(fund.freshness)}</small>
            {fund.is_constraining === false && <small>Does not determine account availability.</small>}
          </div>)}</td>
          <td data-label="Data through">{row.contexts.length === 0 ? <span>No spending report</span> : row.contexts.map(context => <div key={context.report_id}><span>{context.source_data_through === null ? "Not reported" : <time dateTime={context.source_data_through}>{instant(context.source_data_through)}</time>}</span><small>Collected <time dateTime={context.collected_at}>{instant(context.collected_at)}</time></small></div>)}</td>
        </tr>)}</tbody>
      </table>}
      {data.page.has_more && <div className="financial-summary"><p>Sorting applies to loaded rows. Summaries cover the filtered inventory.</p><button type="button" className="quiet-button" disabled={busy || data.page.next_cursor === null} onClick={() => { if (data.page.next_cursor !== null) setPageRequest(current => ({ query: queryKey, cursor: data.page.next_cursor!, attempt: (current?.attempt ?? 0) + 1 })); }}>Load more financial rows</button></div>}
      {data.availability.state !== "available" && <p className="fleet-overview-notice" role="status">Financial coverage {data.availability.state}: {readable(data.availability.reason_code)}.</p>}
    </>}
  </section>;
}
