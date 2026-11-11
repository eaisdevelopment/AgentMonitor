import { useCallback, useState } from "react";
import { AccountQuotaOverview, type OverviewInventory } from "./AccountQuotaOverview";
import { BudgetOverview } from "./BudgetOverview";
import { changeOverviewSearch, overviewSelection } from "./overviewSelection";
import { providerDisplayName } from "../accounts/providerPresentation";
import { ProviderPage } from "../providers/ProviderPage";
import { SessionPanel } from "../sessions/SessionPanel";

export function OverviewPage({
  onExpired,
  onOpenAccount,
  onTogglePassword,
  search,
  onSearchChange,
}: Readonly<{
  search: string;
  onSearchChange: (search: string) => void;
  onExpired: () => void;
  onOpenAccount: (accountId: string, search?: string) => void;
  onProofUnavailable: () => void;
  onTogglePassword: () => void;
}>) {
  const selection = overviewSelection(search);
  const [inventory, setInventory] = useState<OverviewInventory | null>(null);
  const [subscriptionIds, setSubscriptionIds] = useState<readonly string[] | null>(null);
  const receiveInventory = useCallback((value: OverviewInventory) => setInventory(value), []);
  const receiveSubscriptions = useCallback((value: readonly string[] | null) => setSubscriptionIds(value), []);
  const organizations = inventory?.organizations?.items ?? [];
  const accountOrganizations = inventory?.accounts.items.flatMap(account => account.organization_id === null ? [] : [account.organization_id]) ?? [];
  const missingOrganizations = [...new Set(accountOrganizations)].filter(id => !organizations.some(item => item.organization_id === id));
  const providerOptions = [...new Set(inventory?.accounts.items.filter(account => account.lifecycle !== "archived").map(account => account.provider_key) ?? [])].sort();
  if (selection.provider !== null && !providerOptions.includes(selection.provider)) providerOptions.push(selection.provider);
  const change = (values: Readonly<Record<string, string | null>>) => onSearchChange(changeOverviewSearch(search, values));
  const toggleOrganization = (id: string) => {
    const current = selection.organizationIds;
    const next = current === null ? [id] : current.includes(id) ? current.filter(value => value !== id) : [...current, id];
    change({ organization_ids: next.join(","), include_ungrouped: current === null ? "false" : String(selection.includeUngrouped) });
  };
  return (
    <div className="operations-console" data-monitoring-state="api">
      <header className="overview-heading">
        <h1 id="page-title" tabIndex={-1}>AgentMonitor</h1>
        <span className="overview-local-state"><span className="status-light" aria-hidden="true" />Local dashboard</span>
      </header>
      <section className="overview-shared-filters" aria-label="Overview filters">
        <div className="overview-organization-filters" role="group" aria-labelledby="overview-organizations-label">
          <span id="overview-organizations-label">Organizations</span>
          <button type="button" aria-pressed={selection.organizationIds === null && selection.includeUngrouped} onClick={() => change({ organization_ids: null, include_ungrouped: null })}>All organizations</button>
          {organizations.map(item => <button key={item.organization_id} type="button" aria-pressed={selection.organizationIds?.includes(item.organization_id) ?? false} onClick={() => toggleOrganization(item.organization_id)}>{item.name}</button>)}
          {missingOrganizations.map(id => <button key={id} type="button" aria-pressed={selection.organizationIds?.includes(id) ?? false} onClick={() => toggleOrganization(id)}>Organization unavailable</button>)}
          <button type="button" aria-pressed={selection.organizationIds !== null && selection.includeUngrouped} onClick={() => change({ organization_ids: selection.organizationIds?.join(",") ?? "", include_ungrouped: String(selection.organizationIds === null || !selection.includeUngrouped) })}>Ungrouped</button>
        </div>
        <label className="overview-provider-filter"><span>Provider</span><select value={selection.provider ?? "all"} onChange={event => change({ provider_key: event.target.value === "all" ? null : event.target.value })}>
          <option value="all">All providers</option>{providerOptions.map(key => <option key={key} value={key}>{providerDisplayName(key)}</option>)}
        </select></label>
        <label className="overview-provider-filter"><span>Resources</span><select value={selection.resourceType} onChange={event => change({ resource_type: event.target.value })}>
          <option value="all">All</option><option value="subscriptions">Subscriptions</option><option value="api">API billing</option>
        </select></label>
        {inventory === null && <p role="status">Reading filter choices…</p>}
        {inventory !== null && (inventory.accounts.availability.state !== "available" || inventory.organizations?.availability.state !== "available") && <p role="status">Some filter choices could not be refreshed.</p>}
        {inventory !== null && inventory.organizations === null && <p role="status">Organization names are unavailable. Assigned accounts remain separate from Ungrouped.</p>}
      </section>
      <div hidden={selection.resourceType === "api"}>
        <AccountQuotaOverview onExpired={onExpired} onOpenAccount={onOpenAccount} selection={selection} onSortChange={value => change({ quota_sort: value })} onInventory={receiveInventory} subscriptionIds={subscriptionIds} />
      </div>
      <div hidden={selection.resourceType === "subscriptions"}>
        <BudgetOverview search={search} onSearchChange={onSearchChange} onExpired={onExpired} onOpenAccount={onOpenAccount} organizations={organizations} onSubscriptions={receiveSubscriptions} />
      </div>
      <div className="command-grid">
        <ProviderPage displayMode="panel" onExpired={onExpired} />
        <SessionPanel displayMode="panel" onExpired={onExpired} />
      </div>
      <section className="account-security" aria-labelledby="security-title">
        <div><p className="panel-code">LOCAL CONTROL</p><h2 id="security-title">Dashboard security</h2></div>
        <button type="button" className="quiet-button" onClick={onTogglePassword}>Change password</button>
      </section>
    </div>
  );
}
