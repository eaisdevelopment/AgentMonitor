import { useEffect, useState } from "react";

import {
  capacity, providers, registry,
  type AccountCapacityViewV1, type AccountPageV1, type AccountViewV1,
  type ObservedAccountIdentityViewV1, type OrganizationPageV1,
} from "../../shared/api/client";
import { metricAvailability, remainingPercentage } from "../command/quotaPresentation";

type AccountReading = Readonly<{
  account: AccountViewV1;
  quota: AccountCapacityViewV1 | null;
  identity: ObservedAccountIdentityViewV1 | null;
  refreshFailed: boolean;
}>;
type OverviewState =
  | Readonly<{ kind: "loading" }>
  | Readonly<{ kind: "error" }>
  | Readonly<{ kind: "ready"; accounts: AccountPageV1; organizations: OrganizationPageV1 | null; readings: readonly AccountReading[]; refreshFailed: boolean }>;
type OverviewSortKey = "organization" | "state" | "quota";
type OverviewSortDirection = "ascending" | "descending";
type OverviewSort = Readonly<{ key: OverviewSortKey; direction: OverviewSortDirection }>;
type ConnectionGroup = Readonly<{ primary: AccountReading; additional: readonly AccountReading[] }>;

const sortOptions: readonly Readonly<{ value: string; label: string; sort: OverviewSort }>[] = [
  { value: "quota:ascending", label: "Quota left · lowest first", sort: { key: "quota", direction: "ascending" } },
  { value: "quota:descending", label: "Quota left · highest first", sort: { key: "quota", direction: "descending" } },
  { value: "organization:ascending", label: "Organization · A to Z", sort: { key: "organization", direction: "ascending" } },
  { value: "organization:descending", label: "Organization · Z to A", sort: { key: "organization", direction: "descending" } },
  { value: "state:ascending", label: "State · A to Z", sort: { key: "state", direction: "ascending" } },
  { value: "state:descending", label: "State · Z to A", sort: { key: "state", direction: "descending" } },
];

function organizationFilterKey(account: AccountViewV1, organizations: OrganizationPageV1 | null): string {
  if (account.organization_id === null) return "ungrouped";
  return organizations?.items.some(item => item.organization_id === account.organization_id)
    ? `organization:${account.organization_id}` : "unavailable";
}

function lowestRemainingPercentage(reading: AccountReading): number {
  return Math.min(Infinity, ...(reading.quota?.items.flatMap(item => item.windows) ?? [])
    .map(window => remainingPercentage(window.allowance?.remaining_percentage ?? window.remaining_ratio)?.value ?? Infinity));
}

function verifiedIdentity(reading: AccountReading): ObservedAccountIdentityViewV1 | null {
  const { account, quota, identity, refreshFailed } = reading;
  const windows = quota?.items.flatMap(item => item.windows) ?? [];
  return !refreshFailed && ["matched", "owner_confirmed"].includes(account.identity_state) && quota?.availability.state === "available" && identity?.state === "verified" && identity.account_id === account.account_id && identity.email !== null && windows.length > 0 && windows.every(window => window.freshness === "fresh" && window.collection_run_id === identity.collection_run_id) ? identity : null;
}

function groupConnections(readings: readonly AccountReading[]): readonly ConnectionGroup[] {
  const groups = new Map<string, AccountReading[]>();
  for (const reading of readings) {
    const identity = verifiedIdentity(reading);
    const key = identity !== null && identity.provider_organization !== null
      ? JSON.stringify([reading.account.provider_key, reading.account.organization_id, identity.email, identity.provider_organization])
      : JSON.stringify([reading.account.account_id]);
    groups.set(key, [...(groups.get(key) ?? []), reading]);
  }
  return [...groups.values()].map(group => {
    const ordered = [...group].sort((left, right) => {
      const leftMatches = left.account.friendly_name === verifiedIdentity(left)?.email;
      const rightMatches = right.account.friendly_name === verifiedIdentity(right)?.email;
      return Number(rightMatches) - Number(leftMatches) || left.account.account_id.localeCompare(right.account.account_id);
    });
    return { primary: ordered[0]!, additional: ordered.slice(1) };
  });
}

function readingState(reading: AccountReading): Readonly<{ label: string; icon: string; tone: string }> {
  const { account, quota, refreshFailed } = reading;
  const windows = quota?.items.flatMap(item => item.windows) ?? [];
  if (["wrong_account", "conflict", "invalidated"].includes(account.identity_state)) return { label: "Check identity", icon: "!", tone: "warning" };
  if (account.lifecycle === "pending") return { label: "Not connected", icon: "○", tone: "unavailable" };
  if (account.lifecycle === "disabled") return { label: "Disabled", icon: "○", tone: "unavailable" };
  if (!account.is_effective_monitoring_enabled) return { label: "Monitoring off", icon: "○", tone: "unavailable" };
  if (refreshFailed) return { label: "Refresh failed", icon: "!", tone: "warning" };
  if (quota === null || quota.availability.state === "unavailable") return { label: "Unavailable", icon: "?", tone: "unavailable" };
  if (quota.availability.state === "unsupported") return { label: "Unsupported", icon: "?", tone: "unavailable" };
  if (quota.availability.state === "unknown") return { label: "Unknown", icon: "?", tone: "unavailable" };
  if (windows.length === 0) return { label: "No quota yet", icon: "○", tone: "unavailable" };
  if (windows.some(window => window.freshness === "conflicted")) return { label: "Conflicting readings", icon: "!", tone: "warning" };
  if (windows.some(window => window.freshness === "stale")) return { label: "Stale", icon: "!", tone: "warning" };
  if (windows.some(window => window.freshness !== "fresh")) return { label: "Unknown freshness", icon: "?", tone: "unavailable" };
  if (quota.availability.state === "partial") return { label: "Partial readings", icon: "!", tone: "warning" };
  return { label: "Current", icon: "✓", tone: "live" };
}

function organizationName(account: AccountViewV1, organizations: OrganizationPageV1 | null): string {
  if (account.organization_id === null) return "Ungrouped";
  return organizations?.items.find(item => item.organization_id === account.organization_id)?.name ?? "Unavailable";
}

function compareConnectionGroups(
  left: ConnectionGroup,
  right: ConnectionGroup,
  sort: OverviewSort,
  organizations: OrganizationPageV1 | null,
): number {
  let primary = 0;
  if (sort.key === "quota") {
    const leftPercentage = lowestRemainingPercentage(left.primary);
    const rightPercentage = lowestRemainingPercentage(right.primary);
    const leftAvailable = Number.isFinite(leftPercentage);
    const rightAvailable = Number.isFinite(rightPercentage);
    if (leftAvailable !== rightAvailable) return leftAvailable ? -1 : 1;
    if (leftAvailable && leftPercentage !== rightPercentage) primary = leftPercentage < rightPercentage ? -1 : 1;
  } else {
    const leftValue = sort.key === "organization"
      ? organizationName(left.primary.account, organizations)
      : readingState(left.primary).label;
    const rightValue = sort.key === "organization"
      ? organizationName(right.primary.account, organizations)
      : readingState(right.primary).label;
    primary = leftValue.localeCompare(rightValue);
  }
  if (primary !== 0) return sort.direction === "ascending" ? primary : -primary;
  return left.primary.account.friendly_name.localeCompare(right.primary.account.friendly_name)
    || left.primary.account.account_id.localeCompare(right.primary.account.account_id);
}

function sortDescription(sort: OverviewSort): string {
  if (sort.key === "quota") return `Quota left · ${sort.direction === "ascending" ? "lowest" : "highest"} first`;
  const label = sort.key === "organization" ? "Organization" : "State";
  return `${label} · ${sort.direction === "ascending" ? "A to Z" : "Z to A"}`;
}

export function AccountQuotaOverview({ onExpired, onOpenAccount }: Readonly<{
  onExpired: () => void;
  onOpenAccount: (accountId: string) => void;
}>) {
  const [state, setState] = useState<OverviewState>({ kind: "loading" });
  const [refreshKey, setRefreshKey] = useState(0);
  const [busy, setBusy] = useState(false);
  const [selectedOrganizations, setSelectedOrganizations] = useState<readonly string[] | null>(null);
  const [sort, setSort] = useState<OverviewSort>({ key: "quota", direction: "ascending" });

  useEffect(() => {
    const controller = new AbortController();
    let inFlight = false;
    const refresh = async () => {
      if (inFlight) return;
      inFlight = true;
      setBusy(true);
      try {
        const [accounts, organizations] = await Promise.all([
          registry.accounts(controller.signal), registry.organizations(controller.signal),
        ]);
        if (controller.signal.aborted) return;
        if ((!accounts.ok && accounts.problem.code === "dashboard_authentication_required") || (!organizations.ok && organizations.problem.code === "dashboard_authentication_required")) {
          onExpired();
          return;
        }
        if (!accounts.ok) throw new Error("account_list_unavailable");
        const visible = accounts.data.items.filter(account => account.lifecycle !== "archived");
        const readings: AccountReading[] = [];
        let expired = false;
        // Bound simultaneous requests while retaining every returned account.
        for (let offset = 0; offset < visible.length; offset += 6) {
          const batch = await Promise.all(visible.slice(offset, offset + 6).map(async account => {
            try {
              const [quota, identity] = await Promise.all([
                capacity.account(account.account_id, controller.signal),
                providers.observedAccountIdentity(account.account_id, controller.signal),
              ]);
              if ((!quota.ok && quota.problem.code === "dashboard_authentication_required") || (!identity.ok && identity.problem.code === "dashboard_authentication_required")) expired = true;
              return { account, quota: quota.ok ? quota.data : null, identity: identity.ok ? identity.data : null, refreshFailed: !quota.ok || !identity.ok };
            } catch {
              return { account, quota: null, identity: null, refreshFailed: true };
            }
          }));
          if (controller.signal.aborted) return;
          if (expired) { onExpired(); return; }
          readings.push(...batch);
        }
        setState(current => ({
          kind: "ready", accounts: accounts.data,
          organizations: organizations.ok ? organizations.data : current.kind === "ready" ? current.organizations : null,
          readings: readings.map(reading => {
            const previous = current.kind === "ready" ? current.readings.find(item => item.account.account_id === reading.account.account_id) : undefined;
            return { ...reading, quota: reading.quota ?? previous?.quota ?? null, identity: reading.identity ?? previous?.identity ?? null };
          }),
          refreshFailed: !organizations.ok || readings.some(reading => reading.refreshFailed),
        }));
      } catch {
        if (!controller.signal.aborted) setState(current => current.kind === "ready"
          ? { ...current, refreshFailed: true, readings: current.readings.map(reading => ({ ...reading, refreshFailed: true })) }
          : { kind: "error" });
      } finally {
        inFlight = false;
        if (!controller.signal.aborted) setBusy(false);
      }
    };
    void refresh();
    const interval = window.setInterval(() => { void refresh(); }, 30_000);
    return () => { controller.abort(); window.clearInterval(interval); };
  }, [onExpired, refreshKey]);

  const organizationOptions = state.kind === "ready" ? [
    ...(state.organizations?.items.map(item => ({ key: `organization:${item.organization_id}`, name: item.name })) ?? []),
    ...(state.readings.some(reading => reading.account.organization_id === null) ? [{ key: "ungrouped", name: "Ungrouped" }] : []),
    ...(state.readings.some(reading => organizationFilterKey(reading.account, state.organizations) === "unavailable") ? [{ key: "unavailable", name: "Unavailable organization" }] : []),
  ] : [];
  const visibleReadings = state.kind === "ready" ? state.readings.filter(reading => selectedOrganizations === null || selectedOrganizations.includes(organizationFilterKey(reading.account, state.organizations))) : [];
  const visibleConnections = state.kind === "ready"
    ? [...groupConnections(visibleReadings)].sort((left, right) => compareConnectionGroups(left, right, sort, state.organizations))
    : [];
  const toggleOrganization = (key: string) => setSelectedOrganizations(current => current === null ? [key] : current.includes(key) ? current.filter(item => item !== key) : [...current, key]);
  const selectSort = (key: OverviewSortKey) => setSort(current => ({
    key,
    direction: current.key === key && current.direction === "ascending" ? "descending" : "ascending",
  }));
  const selectSortOption = (value: string) => {
    const option = sortOptions.find(item => item.value === value);
    if (option !== undefined) setSort(option.sort);
  };

  return (
    <section className="fleet-overview" aria-labelledby="overview-accounts-title" aria-busy={busy}>
      <div className="fleet-overview-heading">
        <div><h2 id="overview-accounts-title">Accounts</h2><p id="overview-quota-order" aria-live="polite">{sortDescription(sort)} · low ≤20%</p></div>
        {state.kind === "ready" && organizationOptions.length > 0 && <div className="overview-organization-filters" role="group" aria-labelledby="overview-organizations-label">
          <span id="overview-organizations-label">Organizations</span>
          <button type="button" aria-pressed={selectedOrganizations === null} onClick={() => setSelectedOrganizations(null)}>All organizations</button>
          {organizationOptions.map(option => <button key={option.key} type="button" aria-pressed={selectedOrganizations?.includes(option.key) ?? false} onClick={() => toggleOrganization(option.key)}>{option.name}</button>)}
        </div>}
        <div className="fleet-overview-controls">
          {state.kind === "ready" && <span>{visibleConnections.length} account rows · {visibleReadings.length} of {state.readings.length} connections listed</span>}
          {state.kind === "ready" && <label className="overview-mobile-sort"><span>Sort accounts</span><select aria-label="Sort accounts" value={`${sort.key}:${sort.direction}`} onChange={(event) => selectSortOption(event.target.value)}>{sortOptions.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>}
          <button className="quiet-button" type="button" disabled={busy} onClick={() => setRefreshKey(key => key + 1)}>{busy ? "Refreshing…" : "Refresh overview"}</button>
        </div>
      </div>
      {state.kind === "loading" && <p className="fleet-overview-notice" role="status">Reading accounts and quota…</p>}
      {state.kind === "error" && <p className="fleet-overview-notice" role="alert">Account readings are unavailable. Refresh to try again.</p>}
      {state.kind === "ready" && <>
        {state.readings.length === 0 ? <p className="fleet-overview-notice">No accounts are registered. Add an account from Accounts.</p> : visibleReadings.length === 0 ? <p className="fleet-overview-notice" role="status">{selectedOrganizations?.length === 0 ? "No organizations selected. Choose an organization or All organizations." : "No accounts in the selected organizations. Choose another organization or All organizations."}</p> : (
          <table className="fleet-overview-table" aria-label="Account quota overview" aria-describedby="overview-quota-order">
            <thead><tr><th scope="col">Account</th>
              <th scope="col" aria-sort={sort.key === "organization" ? sort.direction : undefined}><button type="button" className="overview-sort-button" onClick={() => selectSort("organization")}>Organization<span aria-hidden="true">{sort.key === "organization" ? sort.direction === "ascending" ? "↑" : "↓" : "↕"}</span></button></th>
              <th scope="col" aria-sort={sort.key === "state" ? sort.direction : undefined}><button type="button" className="overview-sort-button" onClick={() => selectSort("state")}>State<span aria-hidden="true">{sort.key === "state" ? sort.direction === "ascending" ? "↑" : "↓" : "↕"}</span></button></th>
              <th scope="col" aria-sort={sort.key === "quota" ? sort.direction : undefined}><button type="button" className="overview-sort-button" onClick={() => selectSort("quota")}>Quota left<span aria-hidden="true">{sort.key === "quota" ? sort.direction === "ascending" ? "↑" : "↓" : "↕"}</span></button></th>
              <th scope="col">Updated</th></tr></thead>
            <tbody>{visibleConnections.map(({ primary: reading, additional }) => {
              const { account, quota, identity } = reading;
              const windows = quota?.items.flatMap(item => item.windows) ?? [];
              const verified = verifiedIdentity(reading) !== null;
              const displayedName = verified ? identity?.email ?? account.friendly_name : account.friendly_name;
              const status = readingState(reading);
              const organization = organizationName(account, state.organizations);
              const updatedAt = windows.map(window => window.collected_at).sort()[0];
              return <tr key={account.account_id} data-account-id={account.account_id}>
                <th scope="row" data-label="Account"><button type="button" className="overview-account-link" aria-label={`Open account ${displayedName}`} onClick={() => onOpenAccount(account.account_id)}>{displayedName}</button><small>{account.provider_key} · {verified ? "Identity verified" : "Admin name"}</small>
                  {verified && account.friendly_name !== identity?.email && <small className="connection-warning">Registered as {account.friendly_name}</small>}
                  {additional.length > 0 && <div className="additional-connections"><strong>{additional.length + 1} connected profiles · one quota balance</strong>{additional.map(other => <button key={other.account.account_id} type="button" className="quiet-button" onClick={() => onOpenAccount(other.account.account_id)}>Review {other.account.friendly_name} connection</button>)}</div>}
                </th>
                <td data-label="Organization"><span className="organization-tag">{organization}</span></td>
                <td data-label="State"><span className={`overview-reading-state overview-state-${status.tone}`}><span aria-hidden="true">{status.icon}</span><span>{status.label}</span></span><small>Monitoring {account.is_effective_monitoring_enabled ? "on" : "off"}</small></td>
                <td data-label="Quota left"><div className="overview-quota-list">
                  {windows.length === 0 ? <span>{quota === null ? "Unavailable" : "No reading yet"}</span> : windows.map(window => {
                    const percentage = remainingPercentage(window.allowance?.remaining_percentage ?? window.remaining_ratio);
                    const low = percentage !== null && percentage.value <= 20;
                    const calculated = window.allowance !== null && window.allowance !== undefined;
                    const precision = calculated && window.allowance?.remaining_percentage.precision === "rounded" ? " · rounded" : "";
                    return <div className={`overview-quota${low ? " overview-quota-low" : ""}`} key={window.window_id} data-window-id={window.window_id}>
                      <div className="overview-quota-label"><span>{window.safe_label ?? window.window_key}</span><span className="overview-quota-value">{low && <span className="overview-quota-warning">Low</span>}<strong title={calculated ? `${window.allowance?.calculation === "100_minus_used_percent" ? "Calculated: 100% minus reported usage" : "Calculated from reported remaining ratio"}${precision}.` : "Provider-reported remaining allowance."}>{percentage?.label ?? metricAvailability(window.remaining_ratio)}</strong></span></div>
                      {percentage !== null && <div className="overview-quota-meter" role="meter" aria-label={`${window.safe_label ?? window.window_key} remaining allowance`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percentage.value} aria-valuetext={`${percentage.label} left${low ? " · low" : ""}${calculated ? " · calculated" : ""}${precision}`}><span style={{ width: `${percentage.value}%` }} /></div>}
                      {window.freshness !== "fresh" && <small>{window.freshness.replaceAll("_", " ")}</small>}
                    </div>;
                  })}
                </div>{windows.some(window => window.allowance != null) && <small>Calculated{windows.some(window => window.allowance?.remaining_percentage.precision === "rounded") ? " · rounded" : ""}</small>}</td>
                <td data-label="Updated">{updatedAt === undefined ? <span>No reading yet</span> : <time dateTime={updatedAt} title={new Date(updatedAt).toLocaleString()}>{new Date(updatedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time>}</td>
              </tr>;
            })}</tbody>
          </table>
        )}
        {(state.refreshFailed || state.accounts.availability.state !== "available") && <p className="fleet-overview-notice" role="status">Some readings could not be refreshed. Check each account's state and update time.</p>}
        {state.accounts.page.has_more && <p className="fleet-overview-notice" role="status">This is a bounded account page; additional accounts are available in Accounts.</p>}
      </>}
    </section>
  );
}
