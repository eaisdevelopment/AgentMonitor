# Dashboard product-family promotion — focused change plan

Status: Approved by owner on 31 October 2026. The owner's request is to integrate the
existing promotion into the application before publication, test it, and open
product links in new browser tabs. This plan describes how that approved change will be implemented.

- Owner: P02 dashboard; consumes no new backend contract. Existing API v1,
  provider integrations, database, authentication, and running agents remain
  unchanged. No new dependency is required.
- Place a compact product-family promotion below the Overview account quota
  table, keeping account information first. Adapt the existing self-contained
  `frontend/adv` content to the dashboard's existing React/CSP model rather
  than weakening content security or loading a third-party frame.
- Rotate the nine available family products, with readable descriptions,
  previous/next and pause controls, reduced-motion handling, and no tracking.
  Exclude the current AgentMonitor project from its own dashboard promotion.
  Every product link opens a separate tab with `noopener noreferrer`.
- Use the built frontend against the real local authenticated dashboard for
  browser verification: ensure account overview remains present before the
  promotion, test rotation and pause, desktop/mobile rendering and an actual
  product link opening a new tab. Record a meaningful failing test before
  implementation and the passing result after it. Exercise required build,
  quality and documentation checks. Never fabricate provider information.
- Deployment is limited to updating the local dashboard service, preserving
  its configuration and data, with a working rollback. Do not restart or
  control Claude or Codex agent processes. Keep the GitHub project private;
  publication is a separate later step.
- Rollback: remove the promotion component and restore the prior frontend
  build/service revision. No data migration, contract change, or provider
  credential handling is involved.

## Owner-requested company attribution

On 31 October 2026 the owner requested a footer naming the company that
develops and delivers the application, consistent with the other products.
Add a compact link to Essential AI Solutions Ltd throughout the authenticated
dashboard, with no changes to provider data or authentication. Verify the
rendered footer and destination in the real dashboard.
