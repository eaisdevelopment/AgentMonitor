# Engineering review checklists

These checklists guide reviews; they do not replace evidence, professional judgment, or the Definition of Done. Reviewers record `Pass`, `Fail`, `Blocked`, or `Not applicable` with a reason and artifact reference.

## Requirements and planning review

- Requirement and acceptance IDs identify an owner-visible outcome.
- Scope, non-goals, failure behavior, and deferred behavior are explicit.
- Assumptions are separated from verified provider/platform facts.
- One module owns every invariant, table, setting, and public contract.
- Consumed and published contracts/versions are listed.
- Privacy, security, retention, migration, performance, resilience, operations, and license effects are addressed.
- Test cases were designed before production implementation and identify real boundaries.
- Live-provider/platform prerequisites and owner participation are known.
- Rollback/recovery and documentation outputs are specified.
- Unresolved questions cannot lead to materially different implementations.

## Architecture and module-boundary review

- Dependency direction matches the system architecture.
- Domain code is free of FastAPI, SQLAlchemy, provider SDK/CLI, OS, and UI dependencies.
- No module reads another module's tables or private code.
- Cross-module DTOs/events live in versioned contract packages.
- Provider and platform details are confined to adapters.
- No shared `utils` package hides domain coupling.
- State ownership, transactions, idempotency, concurrency, and failure isolation are explicit.
- Physical SQLite sharing has not erased logical table/migration ownership.
- Future PostgreSQL/remote seams remain credible without speculative abstraction.
- Any deliberate exception has an approved ADR and exit plan.

## Contract and API review

- Contract name/version, owner, consumers, compatibility promise, and status are recorded.
- Optional/nullable/unknown/unavailable/unsupported semantics are distinct.
- Money, percentages, counts, durations, units, timestamps, precision, freshness, confidence, and provenance are unambiguous.
- Commands define authorization, idempotency, conflicts, and error behavior.
- Events define delivery, ordering, deduplication, replay, and evolution rules.
- REST resources, methods, status codes, RFC 9457 problems, pagination, filtering, and correlation IDs follow API standards.
- OpenAPI changed intentionally and generated client/schema checks pass.
- Breaking change has version/migration/deprecation plans and an ADR.
- No provider-specific unversioned field leaks into the stable domain API.

## Data and migration review

- Exactly one module owns every table and migration.
- Constraints enforce material invariants; indexes reflect measured/query needs.
- UTC/time-zone, exact decimal/money, identifiers, and retention semantics are correct.
- Sensitive/prohibited data is absent; provenance and confidence are preserved.
- Migration is forward-safe, transactional where possible, idempotent where required, and tested on a real database.
- Destructive/irreversible work has explicit approval, backup, restore, and rollback/forward-fix strategy.
- Fresh install and supported upgrade paths pass.
- Backup/restore/integrity evidence covers the changed schema.
- SQLite-specific behavior is isolated/documented and PostgreSQL portability assessed.

## Test-integrity review

- Each changed behavior has meaningful expected Red, Green, and post-refactor evidence.
- The red failure was behavioral, not setup/syntax/credential failure.
- Tests exercise the boundary they claim: real SQLite, HTTP server, built browser, OS/process, or provider/account.
- Pure tests have no I/O and constructed values represent domain facts.
- No mocks, fakes, stubs, emulators, recordings/replays, seeded telemetry, demo accounts, placeholder values, disabled assertions, or test-only production branches exist.
- Dynamic live values are reconciled by identity/unit/range/freshness/source rather than hardcoded.
- Failure, timeout, stale, auth, concurrency, restart, migration, and recovery scenarios are covered as applicable.
- Failed, Blocked, and Not Run cases remain visible.
- Logs, screenshots, artifacts, and reports contain no secrets/content/identifiers.
- A meaningful regression would make the test fail.

## Security and privacy review

- Trust boundaries, threats, least privilege, and allowed side effects match the threat model.
- Dashboard session, CSRF, API token scope/rotation/revocation, host/origin, and loopback restrictions are correct.
- Secret values never enter source, arguments, logs, errors, database, browser bundle, OpenAPI examples, backups, exports, diagnostics, screenshots, or reports.
- Subprocesses avoid shells and untrusted interpolation; timeouts/output limits/exit handling are enforced.
- Filesystem access validates roots, ownership, permissions, symlinks, size, and file type as applicable.
- Parsers are allowlist-based and fail safely on unknown versions/shapes.
- Prompt, response, tool, source, arbitrary environment, and credential content is neither read nor retained.
- Default provider profiles remain unmodified.
- Security events are auditable without identifying/sensitive payloads.
- New threats/controls are reflected in security docs and tests.

## Provider/platform adapter review

- Capability is supported by evidence for the precise provider plan/version/platform scope.
- Official documented API/CLI is preferred; weaker sources are visibly classified.
- Capability manifest reports unsupported/unavailable honestly.
- Authentication-required, wrong-account, revoked, permission-denied, throttled, network/provider failure, malformed output, and version drift are distinct.
- Observations include source, timestamps, adapter/provider version, freshness, precision, and confidence.
- Identity/account correlation never guesses.
- Parser path/field allowlists exclude secret/content fields.
- Timeouts, retry/backoff, concurrency limits, collection cost, and rate limits are safe.
- Live evidence used a real account/system and confirms no provider/default-profile/running-agent mutation.
- An adapter failure cannot take down unrelated providers or dashboard queries.

## UI and accessibility review

- UI consumes only the generated versioned API client.
- No invented/demo/placeholder metric is rendered as real.
- Source, freshness, uncertainty, unsupported/unknown/stale/error states are visible.
- Critical warnings and total health are understandable without color alone.
- Keyboard navigation, focus, landmarks, labels, contrast, reduced motion, zoom, and screen-reader names are verified.
- Dense 1920×1080 layout and documented responsive breakpoints are exercised in a real browser.
- Loading, empty, partial, stale, offline/error, permission, and auth-expiry states are usable.
- Tables/charts expose equivalent textual values and meaningful units/time ranges.
- State-changing operations require appropriate confirmation/CSRF/idempotency behavior.
- No secret/account-sensitive information leaks through URL, browser storage, source maps, console, or error UI.

## Dependency and license review

- The dependency solves a documented need not reasonably met by the current stack/standard library.
- Direct/transitive licenses are compatible with the current all-rights-reserved project.
- Maintenance, provenance, release cadence, vulnerabilities, package ownership, and compromise history are reviewed.
- Exact version constraints and integrity/lockfile policy are defined.
- Runtime/development/optional scope is minimal.
- SBOM and third-party notices are updated.
- Removal/replacement cost and alternatives are documented.
- No install script or telemetry violates security/privacy rules.

## Operations and release review

- Native install/upgrade/service lifecycle is documented and exercised on the target platform.
- Health/readiness and failure diagnostics are actionable and sanitized.
- Collection continues with the browser closed.
- Backups, rotation, checksum, integrity, restore, and retention pass on real storage.
- Resource use and support targets are measured under AgentMonitor-owned load.
- Configuration changes/defaults/migrations are documented.
- Release notes list provider compatibility, contract/schema changes, security impact, known limitations, and Blocked/Not Run live scenarios.
- Rollback/forward recovery and post-release checks are executable.
- Traceability and acceptance matrices reflect actual evidence, not intent.
- All required reviewers sign off; a green hosted pipeline does not substitute for live-provider/platform gates.

