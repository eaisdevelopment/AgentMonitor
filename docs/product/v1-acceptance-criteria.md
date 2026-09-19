# V1 acceptance criteria

V1 is releasable only when every mandatory criterion below is Passed. A Blocked, Not Run, Skipped, Unsupported, or Unknown result is not a pass. Unsupported provider metrics may be honestly displayed as unsupported only when the relevant provider capability discovery and evidence are complete.

## Release-wide gates

- **AC-V1-001:** All approved V1 requirements are mapped to implementation evidence, tests, and documentation in the traceability matrix.
- **AC-V1-002:** Every module has an approved implementation plan, contract version, dependency boundary, test plan, and operational notes.
- **AC-V1-003:** The OpenAPI artifact validates, generated UI client is current, and incompatible API drift checks pass.
- **AC-V1-004:** All database migrations apply from an empty database and from every supported prior release, and rollback/recovery procedures are verified where rollback is safe.
- **AC-V1-005:** Security, privacy, dependency-license, threat-model, and secret-leak reviews have no unresolved release-blocking finding.
- **AC-V1-006:** User, developer, contributor/agent, installation, operation, backup, restore, diagnostics, and upgrade documentation is current.
- **AC-V1-007:** No repository, build artifact, test artifact, log, diagnostic bundle, export, or backup contains a real secret.
- **AC-V1-008:** No production view or test claims simulated provider/account/telemetry data as real.

## Real account and provider gates

- **AC-LIVE-001:** All 6 intended Claude accounts are enrolled or explicitly documented as unavailable by the owner; account identity is confirmed by the owner.
- **AC-LIVE-002:** All 4 intended Codex accounts are enrolled or explicitly documented as unavailable by the owner.
- **AC-LIVE-003:** Both intended Ollama account/workspace identities are enrolled or their actual provider relationship is documented.
- **AC-LIVE-004:** Every provider adapter completes its approved live scenario matrix against real accounts and current installed provider versions.
- **AC-LIVE-005:** Displayed quota/budget values are reconciled with the provider's own authoritative UI/command within the documented polling delay and precision.
- **AC-LIVE-006:** Re-authentication is completed live for at least one account per provider without damaging the default profile or losing AgentMonitor history.
- **AC-LIVE-007:** Provider unavailable, exhausted, authentication-required, and recovery states are observed live when naturally available; unavailable scenarios remain Blocked rather than simulated.

## Dashboard and workflow gates

- **AC-UI-001:** A user can log in, log out, recover from an expired session, and rotate an API token using real backend persistence.
- **AC-UI-002:** The dashboard shows real global, organization, provider, account, quota, budget, session/process, alert, and freshness information with no placeholder telemetry.
- **AC-UI-003:** Layout is usable at 1920x1080 and defined responsive checkpoints, with no loss of critical status meaning.
- **AC-UI-004:** Keyboard navigation, focus visibility, accessible names, contrast, and non-color status cues meet the accessibility checklist.
- **AC-UI-005:** Empty, loading, partial, stale, unsupported, unauthorized, and failed states are truthful and actionable.
- **AC-UI-006:** Every normalized/derived value exposes its inputs, source, timestamp, confidence, and explanation.

## Process and session gates

- **AC-PROC-001:** Running provider processes are discovered on the real Linux workstation without changing the launch workflow or injecting terminal input.
- **AC-PROC-002:** Parent/subagent hierarchy is correct for representative real Claude, Codex, and Ollama process trees.
- **AC-PROC-003:** Account-session correlation never silently guesses. Unresolved mappings are visible and can be confirmed manually.
- **AC-PROC-004:** Metadata-only extraction has been reviewed to prove prompts, responses, source content, arbitrary environment values, and secrets are not persisted.
- **AC-PROC-005:** Ten-minute possible-stall logic operates on real observations and does not classify an observable user/permission wait as stuck.

## Alerts and history gates

- **AC-ALERT-001:** Threshold precedence works as account > provider > organization > global using pure deterministic domain tests and real persisted configuration.
- **AC-ALERT-002:** Dashboard alerts deduplicate, transition, acknowledge, snooze, recover, and retain history using the running application and real database.
- **AC-ALERT-003:** Stale collector and re-authentication-required alerts are verified against real conditions.
- **AC-HIST-001:** A full collection-to-history-to-chart path is verified with real observations.
- **AC-HIST-002:** 365-day retention and expiry behavior is verified without changing the machine clock; pure retention calculations may use constructed timestamps, while deletion is tested against a real database.

## Reliability and operations gates

- **AC-OPS-001:** Native install, start, stop, restart, status, and auto-start-at-login behavior are verified on the target Linux machine.
- **AC-OPS-002:** Closing the browser does not stop collection.
- **AC-OPS-003:** One provider adapter failure does not interrupt other adapters or API/UI availability.
- **AC-OPS-004:** Daily/weekly/monthly backup creation, checksum, integrity validation, restore, and post-restore startup are exercised with the real database.
- **AC-OPS-005:** Upgrade and failure-recovery runbooks are exercised before release.
- **AC-OPS-006:** Data collection remains within provider rate limits under the approved polling configuration.

## Test integrity gates

- **AC-TEST-001:** Every behavior change has recorded red-green-refactor evidence.
- **AC-TEST-002:** The repository contains no prohibited mock/fake/stub/emulator/provider-fixture framework.
- **AC-TEST-003:** Pure domain, real database, real HTTP server, built frontend, and real browser suites pass.
- **AC-TEST-004:** Live tests identify provider/account aliases, versions, timestamps, and sanitized results and are countersigned by the owner where authentication was interactive.
- **AC-TEST-005:** Mutations of critical quota, threshold, forecast, retention, authentication, and authorization logic are killed at the target score defined in the module plan.
- **AC-TEST-006:** Tests that cannot run are reported separately as Blocked/Not Run and cannot be hidden by the main pipeline success state.

## Explicit post-V1 items

The following do not block V1: email, native desktop notifications, messenger integrations, remote hosting, multi-user authorization, additional providers, full transcript storage, or agent control/routing.
