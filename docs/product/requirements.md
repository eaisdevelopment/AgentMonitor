# Product requirements

## Status vocabulary

- **Approved:** agreed requirement for V1.
- **Discovery:** outcome required, but the supported collection mechanism must be established in Milestone 0.
- **Deferred:** explicitly outside V1.

## Functional requirements

### Organizations and accounts

- **FR-ORG-001 (Approved):** Create, rename, order, and archive organization/group records.
- **FR-ORG-002 (Approved):** Assign each provider account to one primary organization/group and support an Ungrouped state.
- **FR-ORG-003 (Approved):** Aggregate health, capacity, budgets, alerts, and running sessions by organization and globally.
- **FR-ACC-001 (Approved):** Register Claude, Codex, Ollama, and API billing accounts using stable internal identifiers independent of email or provider display-name changes.
- **FR-ACC-002 (Approved):** Assign a friendly name to every account and retain history when it is renamed or moved.
- **FR-ACC-003 (Approved):** Enable or disable monitoring without deleting history.
- **FR-ACC-004 (Approved):** Distinguish subscription resources, API resources, projects/workspaces, and authentication profiles belonging to the same identity.
- **FR-ACC-005 (Approved):** Auto-discover installed V1 providers and the currently observable account/profile information.
- **FR-ACC-006 (Approved):** Allow manual confirmation or association when account ownership cannot be proven. Never guess.

### Authentication lifecycle

- **FR-AUTH-001 (Approved):** Report provider authentication as healthy, refreshing, expiring, re-authentication required, revoked/disabled, wrong-account detected, or unknown.
- **FR-AUTH-002 (Approved):** Guide the user through official browser/device/CLI login flows for AgentMonitor-managed profiles.
- **FR-AUTH-003 (Approved):** Re-authentication must update an existing account without losing its name, grouping, history, alerts, or configuration.
- **FR-AUTH-004 (Approved):** Never collect provider passwords, social-login passwords, email OTP values, MFA values, or recovery codes.
- **FR-AUTH-005 (Approved):** Never log out, rewrite, relocate, or otherwise modify a default provider profile.
- **FR-AUTH-006 (Discovery):** Verify isolated-profile behavior for each installed provider version using real accounts before relying on it.

### Subscription quotas

- **FR-QUOTA-001 (Approved):** Display every observable provider-defined quota window separately, including its scope, used/remaining value, unit, reset time, status, and source.
- **FR-QUOTA-002 (Approved):** Preserve provider-specific quota fields without forcing incompatible limits into a universal total.
- **FR-QUOTA-003 (Approved):** Derive a normalized account health state: Available, Constrained, Critical, Exhausted, Authentication Required, or Unknown.
- **FR-QUOTA-004 (Approved):** Show whether a value is authoritative, provider-reported, locally derived, heuristic, experimental, stale, or unknown.
- **FR-QUOTA-005 (Approved):** Calculate consumption rate and projected exhaustion only when inputs are sufficient; label projections as derived and include uncertainty.
- **FR-QUOTA-006 (Discovery):** Establish exact supported quota data for Claude, Codex, and Ollama using official interfaces first.

### API usage and budgets

- **FR-BUDGET-001 (Approved):** Monitor Anthropic, OpenAI, and Ollama API usage for all configured real billing accounts.
- **FR-BUDGET-002 (Approved):** Display available spend, current spend, prepaid credits when exposed, soft/hard limits, billing period, reset/renewal time, and forecasted exhaustion.
- **FR-BUDGET-003 (Approved):** Break down usage by organization, account, project/workspace, API key identifier when safely exposed, model, token category, and time bucket when the provider supports it.
- **FR-BUDGET-004 (Approved):** Store money as currency plus integer minor units or exact decimal representation; never binary floating point.
- **FR-BUDGET-005 (Approved):** Treat subscription allowance and pay-as-you-go/API budget as different resource pools.
- **FR-BUDGET-006 (Discovery):** Determine the official/experimental capability set per provider and credential role.

### Local process and session discovery

- **FR-DISC-001 (Approved):** Discover running Claude, Codex, and Ollama agent processes without changing the owner's existing launch workflow.
- **FR-DISC-002 (Approved):** Collect read-only process metadata: executable/provider, PID, parent PID, working directory when permitted, start time, duration, CPU, memory, and observable process state.
- **FR-DISC-003 (Approved):** Read allowlisted metadata from standard provider state/session directories without persisting prompt, response, tool, source-code, or secret content.
- **FR-DISC-004 (Approved):** Relate processes and sessions to accounts only when supported by evidence; otherwise report Unresolved account.
- **FR-DISC-005 (Approved):** Present subagents and child processes as an expandable hierarchy with parent-level aggregated status and usage.
- **FR-DISC-006 (Approved):** Identify observable model, project/repository, session ID, token totals, context usage, activity time, and errors when safely available.
- **FR-DISC-007 (Approved):** Do not read arbitrary process environment values. Any proposed allowlisted environment metadata requires a security review and ADR.
- **FR-DISC-008 (Approved):** Version local-file parsers and record provider CLI version with every parsing result.

### Agent state and stall detection

- **FR-STATE-001 (Approved):** Represent working, waiting for input, waiting for permission, idle, quota/rate limited, authentication required, provider/network error, possibly stuck, exited successfully, crashed, and unknown states.
- **FR-STATE-002 (Approved):** Report definitive states only from definitive evidence; distinguish inferred states.
- **FR-STATE-003 (Approved):** Mark an apparently active agent possibly stuck after 10 minutes without observable progress, subject to configurable threshold precedence.
- **FR-STATE-004 (Approved):** Do not mark waiting-for-user or waiting-for-permission sessions stuck when that state is observable.

### Collection and provenance

- **FR-COL-001 (Approved):** Poll active accounts approximately every minute and idle accounts approximately every five minutes by default.
- **FR-COL-002 (Approved):** Refresh after observable requests, errors, logins, and explicit manual refresh when possible.
- **FR-COL-003 (Approved):** Back off on provider throttling and failures.
- **FR-COL-004 (Approved):** Attach source, observed-at time, collected-at time, adapter version, provider version, freshness, precision, and confidence to every metric.
- **FR-COL-005 (Approved):** Preserve collection-run status, duration, warnings, sanitized errors, and affected capabilities.
- **FR-COL-006 (Approved):** Expose unavailable and unsupported capabilities explicitly.
- **FR-COL-007 (Approved):** Use source priority: documented API, supported CLI output, read-only local metadata, then explicit opt-in experimental browser/private endpoint.
- **FR-COL-008 (Approved):** Never silently fall back from live collection to invented, cached-as-current, or simulated values.

### History, forecasting, and retention

- **FR-HIST-001 (Approved):** Retain quota snapshots, budget observations, session/process metadata, alerts, auth events, and collector events for 365 days.
- **FR-HIST-002 (Approved):** Display trends and reset/exhaustion timelines at useful time ranges.
- **FR-HIST-003 (Approved):** Automatically purge expired history using a documented, auditable retention job.
- **FR-HIST-004 (Approved):** Export operational data before deletion in documented machine-readable formats.
- **FR-HIST-005 (Approved):** Store timestamps in UTC and render them in the user's configured timezone.

### Alerts and dashboard notifications

- **FR-ALERT-001 (Approved):** Support global thresholds overridden by organization, provider, and account in that order of specificity.
- **FR-ALERT-002 (Approved):** Default warnings at 30% remaining and critical alerts at 15%, with user configuration.
- **FR-ALERT-003 (Approved):** Alert on exhausted/unavailable capacity, predicted exhaustion, re-authentication required, stale data, collector failure, possible stall, and recovery/reset.
- **FR-ALERT-004 (Approved):** Deduplicate repeated conditions and model alert lifecycle rather than emit polling noise.
- **FR-ALERT-005 (Approved):** Provide dashboard notification severity, unread state, acknowledgement, snoozing, recovery, and history.
- **FR-ALERT-006 (Approved):** V1 notification delivery is dashboard-only.
- **FR-ALERT-007 (Deferred):** Email follows a fully validated V1 dashboard and requires user-supplied credentials.
- **FR-ALERT-008 (Deferred):** Messenger integrations are later work. Native Linux notifications are not required.

### Dashboard

- **FR-UI-001 (Approved):** Provide a dense, responsive mission-control experience optimized for 1920x1080 while adapting to smaller and larger screens.
- **FR-UI-002 (Approved):** Provide global, organization, account, provider, agent/session, history, alert, authentication, collector, and settings views.
- **FR-UI-003 (Approved):** Make critical warnings, overall capacity, data freshness, and active sessions visible without deep navigation.
- **FR-UI-004 (Approved):** Use text and iconography as well as color for state.
- **FR-UI-005 (Approved):** Do not show decorative gauges without meaningful real data.
- **FR-UI-006 (Approved):** Show the source and explanation behind normalized or derived values.
- **FR-UI-007 (Approved):** Never render sample accounts or invented telemetry in production or test deployments.

### Dashboard identity and API access

- **FR-IAM-001 (Approved):** Require login for the local V1 dashboard using one administrator identity and no default password.
- **FR-IAM-002 (Approved):** Store password verification material using an approved memory-hard password hash.
- **FR-IAM-003 (Approved):** Use HTTP-only browser sessions and CSRF protection for state-changing operations.
- **FR-IAM-004 (Approved):** Support named, scoped API bearer tokens that can be created, rotated, and revoked and are shown in plaintext only once.
- **FR-IAM-005 (Approved):** Store API-token hashes, never token plaintext.
- **FR-IAM-006 (Approved):** Allow Swagger UI to authorize with API tokens.
- **FR-IAM-007 (Approved):** Bind local V1 to loopback and enforce strict host/origin policy.

### Operations and recovery

- **FR-OPS-001 (Approved):** Install and run natively, with a user-level service that starts at Linux login and collects while the browser is closed.
- **FR-OPS-002 (Approved):** Provide health, readiness, collector health, database health, version, and sanitized diagnostic information.
- **FR-OPS-003 (Approved):** Create safe automatic backups: seven daily, four weekly, and twelve monthly, with checksums and integrity checks.
- **FR-OPS-004 (Approved):** Provide documented manual backup, restore, and validation procedures.
- **FR-OPS-005 (Approved):** Exclude secrets from exports, backups, logs, and diagnostics.
- **FR-OPS-006 (Approved):** Provide visible schema, adapter, and application version information.

### V1 action boundary

- **FR-SAFE-001 (Approved):** V1 may refresh telemetry, manage account metadata/groups, guide re-authentication, manage alerts/configuration, and export diagnostics/data.
- **FR-SAFE-002 (Approved):** V1 must not kill, restart, pause, interrupt, inject input into, switch credentials inside, or route a running agent.

## Non-functional requirements

- **NFR-ARCH-001:** Use a modular monolith with enforceable one-way dependencies and no circular module imports.
- **NFR-ARCH-002:** Every module publishes typed contracts and owns its data and invariants.
- **NFR-API-001:** FastAPI is the backend framework; the public API is described by OpenAPI 3.x and exposed under `/api/v1`.
- **NFR-API-002:** The frontend uses a client generated from the committed/generated OpenAPI artifact; no handwritten parallel schema.
- **NFR-DATA-001:** SQLite is the local V1 database; schema and repository design must avoid unnecessary SQLite-only coupling and preserve a PostgreSQL migration path.
- **NFR-TEST-001:** Follow strict red-green-refactor TDD and the real-system testing policy.
- **NFR-TEST-002:** No mocks, fakes, stubs, emulators, simulated provider data, seeded telemetry, or placeholder metric values.
- **NFR-SEC-001:** Apply least privilege, data minimization, secret redaction, safe subprocess execution, and dependency/supply-chain controls.
- **NFR-PRIV-001:** Store operational metadata only in V1. Do not store prompt/response/tool/source content.
- **NFR-PRIV-002:** No external AgentMonitor analytics or automatic crash reporting in V1.
- **NFR-DOC-001:** Contracts, decisions, runbooks, modules, tests, and operations must be documented for developers and agents.
- **NFR-LIC-001:** Admit dependencies only after direct and transitive license review; maintain SBOM and third-party notices.
- **NFR-PLAT-001:** Linux is the primary fully verified platform. macOS must remain architecturally supported and be verified on real macOS when available. Windows is deferred.
- **NFR-PERF-001:** Support at least 100 registered accounts and 200 simultaneously discovered processes without redesign; current expected load is much lower.
- **NFR-RES-001:** A provider outage or malformed provider file must not take down unrelated collectors or the dashboard.
- **NFR-OBS-001:** Use structured local logs and correlation IDs without secrets or content.
- **NFR-COMP-001:** Public APIs, provider contracts, internal events, and database schemas follow the versioning policy.

## Deferred requirements

- **FR-ROUTE-001:** Recommend and automatically select accounts for new agent sessions.
- **FR-ROUTE-002:** Checkpoint and recover an interrupted session under another account/provider.
- **FR-CONTENT-001:** Opt-in storage of full prompts, responses, and tool activity with separate encryption and retention design.
- **FR-REMOTE-001:** Remote deployment with HTTPS and multi-user authorization.
- **FR-PROVIDER-EXT-001:** Gemini, Grok, Muse, and additional major providers.
