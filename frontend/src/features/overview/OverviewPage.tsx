import { ProductPromotion } from "./ProductPromotion";
import { AccountQuotaOverview } from "./AccountQuotaOverview";
import { ProviderPage } from "../providers/ProviderPage";
import { SessionPanel } from "../sessions/SessionPanel";

export function OverviewPage({
  onExpired,
  onOpenAccount,
  onTogglePassword,
}: Readonly<{
  onExpired: () => void;
  onOpenAccount: (accountId: string) => void;
  onProofUnavailable: () => void;
  onTogglePassword: () => void;
}>) {
  return (
    <div className="operations-console" data-monitoring-state="api">
      <ProductPromotion />
      <header className="overview-heading">
        <h1 id="page-title" tabIndex={-1}>AgentMonitor</h1>
        <span className="overview-local-state"><span className="status-light" aria-hidden="true" />Local dashboard</span>
      </header>
      <AccountQuotaOverview onExpired={onExpired} onOpenAccount={onOpenAccount} />
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
