# Independent module planning packet catalog

## Owner-directed future-version work

The [local Ollama backlog](integration/future-local-ollama-backlog-v1.json) records FUT-OLL-LOCAL-001..004 under the [4 November decision](integration/m6-local-ollama-deferral-2026-11-04.md). All local Ollama discovery, model/process/resource monitoring, UI and validation is deferred and unscheduled. It does not block M6 or reappear as a requirement of M7/M8. The module-planning packets below remain historical architecture references where they describe that deferred scope.


- Status: Synchronized reusable task-packet catalog; all listed plan artifacts exist
- Owner: integration steward
- Use with: sub-agent runbook, module-plan template, V1 planning program, and contract register
- Implementation authorization: none

## Universal planning-agent instructions

Every planning assignment must:

- invoke the repository-local `agentmonitor-engineering` skill and read its routed documents itself;
- create exactly the assigned plan artifact and avoid shared-spec edits;
- map exact requirement and acceptance IDs, not only families;
- define owned invariants/data/configuration plus allowed and forbidden imports/paths;
- define published/consumed contracts by contract-register ID and proposed version;
- allocate real test/scenario IDs with expected initial Red behavior;
- preserve Passed/Failed/Blocked/Not Run distinctions;
- propose dependencies only as Candidate/Pending admission;
- identify security/privacy/operations/migration/recovery/documentation effects;
- expose unresolved decisions and stop rather than invent external facts;
- leave status Draft and approval pending.

Every assignment forbids production code, manifests, migrations, `.env`, dependency installation, provider/account mutation, live authentication, GitLab changes, and unassigned file edits.

## PLAN-FND — Engineering foundation

- Artifact: `docs/plans/foundation/plan-v1.md`
- Entry: specification baseline owner-reviewed.
- Objective: reproducible repository, module boundaries, build/test/OpenAPI/client/config/logging/CI primitives with no provider or business claims.
- Requirements: NFR-ARCH-001/002, NFR-API-001/002, NFR-DATA-001, NFR-TEST-001/002, NFR-SEC-001, NFR-PRIV-002, NFR-DOC-001, NFR-LIC-001, NFR-PLAT-001, NFR-RES-001, NFR-OBS-001, NFR-COMP-001; support AC-V1-003..008 and AC-TEST-001..003/006.
- Contracts: CTR-COMMON-001..006, CTR-CONFIG-001, CTR-DB-001, CTR-UI-001.
- Must resolve: topology, runtime selection gates, package/lock strategy, generated artifact ownership, CI evidence states, real local-stack harness, import checks, command registry, shared-file ownership.
- Must not: define business tables/routes/provider DTOs or claim candidate packages/versions approved.

## PLAN-M01 — Identity and access

- Artifact: `docs/plans/modules/m01-identity-access/plan-v1.md`
- Entry: baseline plus foundation contract proposal.
- Objective: single-administrator authentication, server-side browser sessions, CSRF, explicit permissions, scoped API tokens, and IAM audit behavior.
- Requirements: FR-IAM-001..007, supporting FR-SAFE-001/002, NFR-SEC-001, NFR-PRIV-002, NFR-OBS-001, NFR-COMP-001; AC-UI-001, AC-V1-005/007, AC-TEST-001..003/006.
- Contracts: CTR-IAM-001..008; consumes CTR-COMMON-001/002/006 and CTR-CONFIG-001; synchronizes CTR-API-002/003 with P01.
- Must resolve: bootstrap, password hash policy, rate limits, session/CSRF lifecycle, token plaintext-once behavior, permissions, tables/retention, safe errors, rotation/recovery.
- Must not: own provider authentication/account profiles, host/origin transport enforcement, or generic application configuration.

## PLAN-M02 — Registry

- Artifact: `docs/plans/modules/m02-registry/plan-v1.md`
- Entry: owner-reviewed M0 identity/resource/profile findings and CS-1 provider primitives.
- Objective: organizations, accounts, resources, installations, profiles, identity evidence, lifecycle/history, and manual confirmation without guessing.
- Requirements: FR-ORG-001..003, FR-ACC-001..006, FR-AUTH-002..006 where registry-owned, FR-SAFE-001/002; supports AC-LIVE-001..003/006, AC-PROC-003, AC-UI-002/005.
- Contracts: CTR-REG-001..007; consumes CTR-PROV-002/005..007 and common contracts.
- Must resolve: stable identity and aliases, rename/move history, ungrouped behavior, resource-pool taxonomy, protected default profiles, correlation confirmation, archive/disable semantics.
- Must not: collect telemetry, inspect credential contents, decide health, or encode provider-specific secrets.

## PLAN-M03 — Provider system

- Artifact: `docs/plans/modules/m03-provider-system/plan-v1.md`
- Entry: complete M0 capability matrices and source decisions.
- Objective: capability-driven adapter protocol, compatibility negotiation, source/outcome vocabulary, registration, and safe extension governance.
- Requirements: FR-AUTH-001/006, FR-QUOTA-006, FR-BUDGET-006, FR-DISC-008, FR-COL-004/006..008, NFR-RES-001, NFR-COMP-001; supports AC-LIVE-004..007 and AC-OPS-003/006.
- Contracts: CTR-PROV-001..008 and CTR-COMMON-004; consumes safe execution/network/platform primitives only.
- Must resolve: protocol method semantics, manifest/outcome unions, version ranges, partial/unsupported/unverified distinctions, source downgrade policy, extension privacy/versioning.
- Must not: contain Claude/Codex/Ollama behavior or persist capacity/runtime facts.

## PLAN-M04 — Collection control

- Artifact: `docs/plans/modules/m04-collection-control/plan-v1.md`
- Entry: approved M02/M03 contract proposals and M0 rate/cost/auth-failure evidence.
- Objective: adaptive scheduling, refresh, leases, concurrency, deadlines, idempotency, retry/backoff, run history, and collector health.
- Requirements: FR-COL-001..008, relevant FR-AUTH-001, FR-SAFE-001/002, NFR-RES-001, NFR-OBS-001; supports AC-OPS-002/003/006, AC-ALERT-003.
- Contracts: CTR-COL-001..005; consumes CTR-REG-002..005, CTR-PROV-001..006; publishes events to M05/M06/M07/M08.
- Must resolve: active vs idle determination, one-minute/five-minute policy, clock/lease ownership, duplicate manual refresh, authentication no-retry, rate-limit backoff, crash/restart recovery.
- Must not: interpret quota/session business meaning or call provider implementations directly outside protocol.

## PLAN-M05 — Capacity

- Artifact: `docs/plans/modules/m05-capacity/plan-v1.md`
- Entry: M0 quota/budget semantics, approved registry/collection/provider observation contracts.
- Objective: immutable quota/budget observations, native windows, exact cost, current projections, health, history, burn rate, and uncertainty-aware forecasts.
- Requirements: FR-ORG-003, FR-QUOTA-001..006, FR-BUDGET-001..006, FR-HIST-001..005, relevant FR-COL-004/006/008; supports AC-LIVE-005/007, AC-UI-002/005/006, AC-HIST-001/002.
- Contracts: CTR-CAP-001..007; consumes CTR-REG-001/002/005, CTR-COL-003, CTR-PROV-004/008, common quantity/provenance.
- Must resolve: provider-native window identity, exact arithmetic, deduplication, freshness/staleness, health constraint selection, insufficient forecast inputs, history buckets/retention.
- Must not: fetch providers, merge incompatible pools, own alert lifecycle, or invent denominator/reset/budget values.

## PLAN-M06 — Runtime observation

- Artifact: `docs/plans/modules/m06-runtime-observation/plan-v1.md`
- Entry: M0 process/session/local-source evidence plus registry/provider/platform contracts.
- Objective: safe process/session observations, parent/subagent hierarchy, evidence-based account correlation, runtime states, history, and possible-stall inference.
- Requirements: FR-DISC-001..008, FR-STATE-001..004, FR-HIST-001..005 where runtime-owned, FR-SAFE-002, NFR-PRIV-001, NFR-PLAT-001; supports AC-PROC-001..005, AC-UI-002/005/006.
- Contracts: CTR-RUN-001..007; consumes CTR-REG-002..006, CTR-PROV-004/008, CTR-PLAT-001, common provenance.
- Must resolve: PID/start identity, session IDs, ancestry/orphans/cycles, safe path labels, definitive vs inferred state, progress evidence, ten-minute threshold, waiting exclusions, aggregate semantics.
- Must not: read arbitrary environments/content, attach to processes, control them, or guess account ownership.

## PLAN-M07 — Alerting

- Artifact: `docs/plans/modules/m07-alerting/plan-v1.md`
- Entry: synchronized capacity/runtime/collection event contracts.
- Objective: threshold precedence, alert fingerprints/state machine, deduplication, acknowledgement, snooze, recovery, history, and dashboard notifications.
- Requirements: FR-ALERT-001..006, FR-HIST-001..005 where alert-owned, FR-SAFE-001/002; supports AC-ALERT-001..003 and AC-UI-002/005/006.
- Contracts: CTR-ALERT-001..005; consumes CTR-CAP-003..005/007, CTR-RUN-004/005, CTR-COL-004/005, registry scopes.
- Must resolve: account > provider > organization > global precedence, 30%/15% defaults, fingerprint/version changes, repeated/reopened/recovered transitions, snooze expiry, stale/unknown inputs.
- Must not: send email, recollect providers, alter observations, or suppress uncertainty.

## PLAN-M08 — Operations

- Artifact: `docs/plans/modules/m08-operations/plan-v1.md`
- Entry: DB/deployment/config plus module health/query port proposals.
- Objective: health/readiness, version/diagnostics, backup catalog/rotation/restore, retention orchestration, sanitized exports/diagnostics, and product audit.
- Requirements: FR-OPS-002..006, FR-HIST-003/004, NFR-OBS-001, NFR-RES-001; supports AC-OPS-002..005, AC-V1-004/006/007.
- Contracts: CTR-OPS-001..006; consumes CTR-COL-005, CTR-DB-001, configuration registry and module query ports.
- Must resolve: health aggregation, disclosure, backup validity/rotation, restore maintenance state, export formats, diagnostic allowlist/scanning, failure visibility.
- Must not: bypass module ports, include secrets/content, implement provider rules, or silently repair corruption.

## PLAN-A01 — Claude provider adapter

- Artifact: `docs/plans/adapters/claude/plan-v1.md`
- Entry: Claude M0 matrix plus synchronized provider/registry/capacity/runtime contracts.
- Objective: implement only Claude capabilities proven Supported/approved Experimental, including safe source parsing and managed-profile guidance.
- Requirements: provider-scoped FR-ACC-005/006, FR-AUTH-001..006, FR-QUOTA-001..006, FR-DISC-001/003/004/006/008, FR-COL-004..008; supports AC-LIVE-001/004..007 and Claude portions of AC-PROC.
- Contracts: implements CTR-PROV-001..008; maps into registry/capacity/runtime input contracts.
- Must resolve from evidence: `/usage`/other supported sources, fields/windows, version detection, local allowlists, identity/correlation, auth health, isolated-profile feasibility, rate/cost.
- Must not: use private/browser source without separate approval, mutate default profile, capture content, or assume all plans expose identical fields.

## PLAN-A02 — Codex provider adapter

- Artifact: `docs/plans/adapters/codex/plan-v1.md`
- Entry: Codex M0 matrix plus synchronized provider/registry/capacity/runtime contracts.
- Objective/requirements/contracts: same adapter discipline as A01, scoped to Codex and AC-LIVE-002/004..007.
- Must resolve from evidence: supported `/status` or structured source, limit windows/credits, `CODEX_HOME` vs profile semantics, auth-store mode, session fields, identity/correlation, isolated managed-profile behavior.
- Must not: logout/default-profile switch during read-only discovery or claim in-flight account switching.

## PLAN-A03 — Ollama provider adapter

- Artifact: `docs/plans/adapters/ollama/plan-v1.md`
- Entry: Ollama local/cloud/API M0 matrices and synchronized provider/domain contracts.
- Objective: safely expose supported local runtime and cloud identity/quota/API capabilities without conflating local resources and cloud billing.
- Requirements: Ollama-scoped FR-ACC/AUTH/QUOTA/BUDGET/DISC/COL requirements; supports AC-LIVE-003..007 and Ollama portions of AC-PROC.
- Contracts: implements CTR-PROV-001..008; maps local/process via platform/runtime and cloud/API via capacity.
- Must resolve: personal/team/workspace identity, legacy/current plan, official billing API availability, daemon API/log safety, GPU/model-load semantics, per-request token/cost coverage.
- Must not: infer account totals from incomplete local requests or use private billing endpoints.

## PLAN-A04-LINUX — Linux platform adapter

- Artifact: `docs/plans/platform/linux/plan-v1.md`
- Entry: Linux M0 process/filesystem/service inventory.
- Objective: safe process identity/tree/resource inspection, XDG path resolution, bounded filesystem primitives, permissions, and user-service support.
- Requirements: FR-DISC-001/002/004/005/007, FR-OPS-001, NFR-PLAT-001, NFR-SEC-001; supports AC-PROC-001/002/004 and AC-OPS-001.
- Contracts: implements CTR-RUN-006/CTR-PLAT-001/CTR-DEP-001 portions.
- Must resolve: `/proc` race/PID reuse, executable/working-dir access, CPU/memory units, ancestry, permissions, symlinks, systemd user behavior and lingering decision.
- Must not: read process memory/arbitrary environments, signal/attach/restart agents, or run as root.

## PLAN-A04-MAC — macOS platform adapter

- Artifact: `docs/plans/platform/macos/plan-v1.md`
- Entry: access to a real supported macOS environment.
- Objective: implement the same platform contract using real macOS process/filesystem/launchd behavior.
- Requirements/contracts: NFR-PLAT-001 and applicable DISC/OPS requirements; CTR-RUN-006/CTR-PLAT-001/CTR-DEP-001.
- Current state: Blocked for detailed approval until a real macOS environment is available; architecture review still prevents Linux leakage.

## PLAN-P01 — FastAPI boundary

- Artifact: `docs/plans/api/fastapi-boundary/plan-v1.md`
- Entry: M01 plus relevant application query/command contracts synchronized.
- Objective: authenticated `/api/v1`, OpenAPI authority, request validation, permissions, sessions/CSRF/bearer transport, problem details, pagination, idempotency, jobs, and generated-client input.
- Requirements: NFR-API-001/002, FR-IAM-003/004/006/007, FR-SAFE-001/002 and transport support for all V1 resources; supports AC-V1-003 and AC-UI-001/002/005/006.
- Contracts: publishes CTR-API-001..003; consumes all application ports, never repositories/provider adapters.
- Must resolve: operation IDs, permission map, resource schemas, auth docs access, host/origin boundary, error codes, cursor/page limits, long-action resources, OpenAPI compatibility.
- Must not: own business rules, query SQLite, call providers, or hand-edit OpenAPI/client.

## PLAN-P02 — React mission-control UI

- Artifact: `docs/plans/ui/react-dashboard/plan-v1.md`
- Entry: synchronized OpenAPI/resource contracts and generated-client process.
- Objective: responsive authenticated mission-control UI using only generated client/query layer, truthful states, source explanations, hierarchy, histories, alerts, diagnostics, settings, and accessibility.
- Requirements: FR-UI-001..007 plus presentation/workflow support for ORG/ACC/AUTH/QUOTA/BUDGET/DISC/STATE/ALERT/HIST/OPS; supports AC-UI-001..006 and relevant AC-LIVE/PROC/HIST/ALERT/OPS visibility.
- Contracts: consumes CTR-API-001..003 and CTR-UI-001 only.
- Must resolve: navigation/information priority, 1920×1080 and responsive breakpoints, accessible chart/table alternatives, loading/empty/partial/stale/unsupported/error/auth-expiry states, no-placeholder design workflow.
- Must not: call `fetch` from features, define backend DTOs, read database/files, or display design samples as telemetry.

## PLAN-DB — SQLite persistence and migrations

- Artifact: `docs/plans/persistence/sqlite/plan-v1.md`
- Entry: foundation plus first domain repository/table ownership proposals.
- Objective: production persistence adapter, unit-of-work conventions, module migration allocation, SQLite mode/concurrency, integrity/backup seam, and PostgreSQL portability.
- Requirements: NFR-DATA-001, NFR-COMP-001, applicable FR-HIST/OPS; supports AC-V1-004, AC-HIST-002, AC-OPS-004.
- Contracts: CTR-DB-001/002; implements repository ports owned by modules.
- Must resolve: path/mode/foreign keys/journal/synchronous settings, connection/transaction scope, migration naming/allocation/locking, cross-module FK policy, exact value mapping, real file DB tests.
- Must not: own domain tables/invariants, use implicit create-all in installed mode, or introduce cross-module repositories.

## PLAN-DEP — Native Linux deployment

- Artifact: `docs/plans/deployment/linux-native/plan-v1.md`
- Entry: foundation/config/DB/API/UI/M08 lifecycle proposals and Linux platform evidence.
- Objective: native install/upgrade/service/autostart/path/permission/recovery behavior for the developer workstation.
- Requirements: FR-OPS-001 and support for FR-OPS-002..006, FR-IAM-007, NFR-PLAT-001; supports AC-OPS-001/002/005.
- Contracts: CTR-DEP-001, CTR-DB-001, CTR-OPS-001/002, configuration registry.
- Must resolve: XDG paths, user systemd unit, login-start/lingering choice, artifact layout, explicit migrations, `.env` shell permissions, frontend assets, preflight, rollback.
- Must not: install/run as root, bind remotely, enable lingering silently, or bundle provider credentials.

## PLAN-INT — V1 integration and release

- Artifact: `docs/plans/integration/v1-plan.md`
- Entry: all module/adapter/boundary plans approved and contracts synchronized.
- Objective: integration order, end-to-end/live matrices, performance/resilience/security/license/accessibility/operations gates, release/rollback and evidence aggregation.
- Requirements: all approved V1 requirements; primary ownership of AC-V1-001..008 and coordination of every AC family.
- Contracts: consumes the complete Approved contract register; owns no domain semantics.
- Must resolve: implementation waves, exact shared-file/migration/generated ownership, environment matrix, evidence custody, 100-account/200-process safe load method, final blocked-scenario policy, release notes/artifacts/SBOM/notices.
- Must not: paper over module failures or treat CI as live-provider evidence.

## Assignment and review order

1. Run P0 drafts: M0, FND, M01, program/register.
2. Root performs `CS-0`; owner reviews the planning strategy and M0 interaction model.
3. Execute M0 in owner-coordinated read-only sessions; record evidence and decisions.
4. Assign P1 plans to independent agents with non-overlapping paths.
5. Perform `CS-1`; revise plans through their owners.
6. Repeat for P2–P4 and `CS-2`–`CS-4`.
7. Only after all Definition-of-Ready checks and explicit owner approval issue implementation task packets.
