import { AccountPage } from "../accounts/AccountPage";
import { CollectionRunPanel } from "../collectors/CollectionRunPanel";
import { ProviderPage } from "../providers/ProviderPage";
import { SessionPanel } from "../sessions/SessionPanel";

export function OverviewPage({
  onExpired,
  onOpenAccount,
  onTogglePassword,
}: Readonly<{
  onExpired: () => void;
  onOpenAccount: (accountId: string) => void;
  onTogglePassword: () => void;
}>) {
  return (
    <div className="operations-console" data-monitoring-state="api">
      <section className="command-deck" aria-labelledby="page-title">
        <div>
          <p className="eyebrow">Mission control · local node</p>
          <h1 id="page-title" tabIndex={-1}>AgentMonitor</h1>
          <p className="console-summary">Authenticated operational views from the versioned AgentMonitor API. Unknown, unavailable, and unresolved observations remain explicit.</p>
        </div>
        <div className="link-state" aria-label="Dashboard service link"><span className="status-light" aria-hidden="true" /><span><strong>Dashboard API</strong><small>Authenticated · local</small></span></div>
      </section>
      <div className="command-grid">
        <AccountPage displayMode="panel" onExpired={onExpired} onOpenAccount={onOpenAccount} />
        <ProviderPage displayMode="panel" onExpired={onExpired} />
        <CollectionRunPanel displayMode="panel" onExpired={onExpired} />
        <SessionPanel displayMode="panel" onExpired={onExpired} />
      </div>
      <section className="account-security" aria-labelledby="security-title">
        <div><p className="panel-code">LOCAL CONTROL</p><h2 id="security-title">Dashboard security</h2></div>
        <button type="button" className="quiet-button" onClick={onTogglePassword}>Change password</button>
      </section>
    </div>
  );
}
