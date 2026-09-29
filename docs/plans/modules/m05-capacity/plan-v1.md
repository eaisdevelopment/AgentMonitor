# Module plan: M05 — Capacity

- Status: **Draft — M0 evidence and contract synchronization pending; implementation is not authorized**
- Plan version: 0.2.0-draft
- Proposed module contract: `capacity.v1` (unapproved)
- Contract-register baseline: 0.2.0 Draft-aligned (`CTR-CAP-001` through `CTR-CAP-009`); not synchronized or approved
- Owner: M05 capacity implementation role (unassigned)
- Required reviewers: owner, root/integration steward, M02 Registry owner, M03 Provider-system owner, M04 Collection-control owner, M07 Alerting owner, M08 Operations owner, P01 API owner, P02 UI owner, persistence/migration owner, security/privacy reviewer, test-integrity reviewer, dependency/license reviewer
- Requirements: FR-ORG-003; FR-QUOTA-001..006; FR-BUDGET-001..006; capacity-owned portions of FR-HIST-001..005; supporting FR-COL-004/006/008, FR-OPS-002/005/006, FR-SAFE-001/002; NFR-ARCH-001/002, NFR-API-001/002, NFR-DATA-001, NFR-TEST-001/002, NFR-SEC-001, NFR-PRIV-001/002, NFR-DOC-001, NFR-LIC-001, NFR-PLAT-001, NFR-PERF-001, NFR-RES-001, NFR-OBS-001, NFR-COMP-001
- Acceptance criteria: AC-V1-001..008; AC-LIVE-004/005/007; AC-UI-002/003/004/005/006; AC-HIST-001/002; AC-OPS-003/004/005; AC-TEST-001..006
- Primary project risks: R-001, R-002, R-005, R-007, R-008, R-009, R-010, R-011, R-012, R-014, R-018, R-019, R-020, R-024
- Dependencies: accepted ADRs 0001, 0003, 0005, 0006, 0008, 0010, and 0011; technically validated M0 Capacity handoff; approved common contracts; synchronized M02/M03/M04/M07/M08 contracts; repository foundation; centrally allocated migration chain; persistence adapter; P01/P02 query presentation
- Target milestone: M2 capacity history/current state, expanded through M6 API-budget support; synchronization gate CS-2
- Approved by/date: pending

This plan is governed by the [product requirements](../../../product/requirements.md), [V1 acceptance criteria](../../../product/v1-acceptance-criteria.md), [module boundaries](../../../architecture/modules.md), [contracts and versioning](../../../architecture/contracts-and-versioning.md), [data model](../../../architecture/data-model.md), [provider-adapter contract](../../../architecture/provider-adapter-contract.md), [security architecture](../../../architecture/security.md), [API standards](../../../api/api-standards.md), [testing strategy](../../../engineering/testing-strategy.md), [SDLC](../../../engineering/sdlc.md), [completion and automation gates](../../../engineering/completion-and-automation-gates.md), [M0 execution plan](../../discovery/m0-execution-plan.md), and [contract register](../../contract-register.md). Structural examples are contract design, not provider observations, sample telemetry, fixtures, or evidence.

## CS-1 Draft-alignment addendum

M4 focused synchronization, 2026-09-29: the separately approved
[capacity increment](../../integration/m4-capacity-change.md) consumes the
published `CTR-REG-009` revisioned scope query for fleet completeness. Its
explicitly allocated additive `v1_0703` metadata revision follows the three
M07 revisions and remains M05-owned by table/filename/write allocation.
The serial root-owned catalog fixes order; no existing revision is edited.
This focused authority does not approve this whole Draft plan.

This `0.2.0-draft` revision adopts contract-baseline `0.2.0` and the parallel-ownership manifest as its concrete CS-1 review position. It remains Draft and evidence-blocked; M0, provider reconciliation, and all scenarios remain `Not Run`.

- M05 is the sole semantic producer of CTR-CAP-001..009. It owns normalized capacity-health classification, including state priority, constraining-window selection, freshness and uncertainty. M07 owns alert thresholds and alert lifecycle; M05 never consumes an M07 threshold or alert state, removing the prior M05↔M07 policy cycle.
- CTR-CAP-008 `CapacityForecastChangedV1` emits ordered generation changes, invalidation, insufficient-input, unavailable, and explicit recovery evidence for M07/M08. CTR-CAP-009 `CapacityAvailabilityChangedV1` preserves supported/unsupported, available/unavailable, unknown, stale, withheld, and provider-reauthentication distinctions; it never treats a later collection success or missing event as recovery.
- M05 implements the capacity side of M04-owned CTR-COL-006: it atomically persists immutable observations/current projections/derivations, its producer outbox, and an idempotent commit receipt keyed by run ID, schema version, target generation, and canonical payload digest. It returns only opaque committed observation references. Same input returns the same receipt; digest/schema/generation conflict preserves the first commit.
- All exact values use CTR-COMMON-003; all availability is CTR-COMMON-007; provenance is CTR-COMMON-004. M05 events use CTR-COMMON-006 plus CTR-EVT-001 outbox/receipt/checkpoint/replay semantics. M05 implements the M08-owned CTR-OPS-006 leaf health and CTR-OPS-007 retention/export/consistency participant ports.
- M05 adopts CTR-EVT-TOPOLOGY-001: it owns `capacity_event_outbox` and producer-side `capacity_event_delivery`; consumers own processing receipts/checkpoints. PLAN-DB's reusable dispatcher reaches M05 rows only through the published M05 event-storage port, never cross-module SQL.
- The V1 public contract file is `backend/src/agentmonitor/contracts/capacity_v1.py`; SQLite implementation files are only under `backend/src/agentmonitor/adapters/persistence/capacity/sqlite/**`. M05 owns `capacity_` tables and `v1_0500..v1_0599`; PLAN-DB serializes the migration head.
- Alignment is verified by existing scenarios M05-PURE-014..021, M05-PURE-031..048, M05-DB-002/008..010, M05-DB-017..026, M05-DB-034..036, M05-CONTRACT-001..004, M05-OPS-001..010, and M05-ARCH-001..005. They remain `Not Run`; provider-valued scenarios still require real data.

## 0. Authority, evidence state, and planning gate

This document is the detailed independent implementation plan for M05. It authorizes no production code, manifest, dependency, migration, configuration key, provider access, live collection, or shared-file edit while Draft.

Milestone 0 has not established the provider-specific quota, usage, cost, credit, limit, billing, reset, resource-pool, latency, or reconciliation facts required by M05. No such fact is invented here. The following M0 outputs are mandatory inputs before this plan can be approved for a provider capability:

- exact provider/product/account-plan/credential-role/version/source scope;
- native resource-pool and window identity, nesting, overlap, and aggregation semantics;
- every observable field with meaning, unit, currency, nullability, unsupported behavior, and safe identifier scope;
- used-versus-remaining semantics, reset/renewal timezone and precision, enforcement status, and any provider status vocabulary;
- observation/data-through time, source latency, freshness evidence, precision, confidence, and reconciliation tolerance;
- authoritative/provider-reported/derived boundary and provider-extension allowlist;
- pagination, grouping, request/rate/cost constraints, and safe live comparison method;
- explicit Supported, Experimental, Deferred, Unsupported, or Unknown decision with sanitized evidence.

Until those inputs exist, provider-dependent schemas and scenario rows are `Not Run`; facts remain `Unknown`; unsupported is never asserted merely because a field was absent once; and no forecast, total, denominator, reset, resource relationship, or health class is manufactured.

Planning readiness is checked only through the repository's canonical planning gate once M05 is added to its catalog. This document alone is not a green gate and must not be described as implementation-ready until the full synchronized command passes.

## 1. Outcome and boundaries

### Outcome

M05 turns typed, approved, real provider capacity inputs into immutable truthful history and reproducible current projections. It preserves every provider-native quota/billing window and independently constrained resource pool; records exact quantities and money; exposes provenance, freshness, precision, confidence, and derivation; classifies normalized health without inventing totals; and computes burn rate or projected exhaustion only when sufficient compatible inputs exist.

The outcome is measurable when:

- every accepted subscription quota window remains individually visible with its native identity, scope, unit, used/remaining/limit field states, reset semantics, provider status, and source;
- subscription allowance, API organization/project budget, prepaid credit, and other distinct pools never collapse into one balance or double-count through a parent/child rollup;
- money and exact ratios survive collection, storage, aggregation, API serialization, export, and restore without binary floating-point loss;
- zero, missing, Unknown, Unsupported, Not Applicable, stale, unavailable, and authentication-required remain distinct;
- a repeated M04 commit for the same run and payload is idempotent, while a different payload for that run is rejected as an integrity conflict;
- late or lower-quality observations cannot silently replace a newer current projection;
- account, organization, provider, and global views report honest inventories, state counts, and only mathematically compatible aggregates, with completeness and omitted-reason metadata;
- normalized health identifies the constraining native window and policy inputs rather than exposing a fabricated cross-provider total;
- burn/forecast results identify method version and input observation IDs, quantify or classify uncertainty, and return `insufficient_input` instead of guessing;
- last known capacity remains visible as stale when appropriate and never becomes cached-as-current after failed collection;
- capacity history is bounded, queryable, exportable through M08, retained for 365 days, and purged in auditable batches without deleting a current source fact accidentally;
- one malformed or unavailable provider source cannot corrupt another source's history, projection, or API availability;
- real provider observations reconcile to the provider's authoritative UI/command under the exact M0-approved tolerance, with owner acknowledgement;
- real SQLite, real running service, real built browser, real provider accounts, and real operations verify their claimed boundaries without mocks, fakes, stubs, emulators, recordings, demo accounts, seeded telemetry, or placeholder values.

### In scope

- Typed provider-input schemas for subscription quota, API usage, API cost, API budget, credit, token/request breakdown, and approved provider extensions.
- Native quota-window identity, definitions, observations, lifecycle, scope, reset/renewal semantics, and current projection.
- Account-resource/pool references and explicit aggregation semantics.
- Exact quantity, ratio, token/request count, and money validation and arithmetic.
- Immutable quota, budget/cost, and usage observations with complete provenance.
- M05 implementation of the M04 result-commit/status seam for capacity capabilities.
- Observation/run idempotency, conflict detection, out-of-order handling, current-state selection, and projection rebuild.
- Freshness/staleness, field-state/completeness, normalized health, constraining-window selection, and health-transition events.
- Organization/provider/global capacity projections using M02 scope snapshots without importing registry state.
- Burn-rate and forecast methods, sufficient-input policy, uncertainty, invalidation, and history.
- Capacity current/history/forecast/aggregation query ports and bounded pagination/bucketing.
- Capacity-owned tables, migrations, repositories, transactions, event outbox, retention selection/purge, and consistency checks.
- Safe component health and diagnostics supplied to M08.

### Out of scope

- Calling providers, CLIs, SDKs, filesystems, browsers, or provider network endpoints. A01–A03 and M03 own those boundaries.
- Scheduling, leases, retries, deadlines, rate/request/cost admission, manual refresh, or collection-run lifecycle. M04 owns them.
- Organization/account/profile/resource identity, grouping mutations, resource relationship truth, or owner confirmation. M02 owns them.
- Provider capability/source/compatibility decisions and extension-schema registration. M03 owns them.
- Alert thresholds, alert fingerprints, acknowledgement, snooze, recovery, unread state, or dashboard notification lifecycle. M07 owns them.
- Public REST routes, OpenAPI generation, authorization transport, UI rendering, charts, or generated client. P01/P02 own them.
- Product backup/restore, operational export artifacts, scheduling retention jobs, or diagnostic bundles. M08 owns orchestration and consumes M05 ports.
- Treating estimated model pricing as provider spend unless an approved requirement, M0 decision, and method contract explicitly classify it as derived rather than provider-reported.
- Currency conversion, tax estimation, invoice prediction, universal token equivalence, or cross-currency grand totals in V1.
- Email/native/messenger notifications, remote/multi-user operation, additional providers, agent control/routing, or prompt/response/tool/source capture.

### Ownership

M05 owns:

- `CapacitySubject`, `ResourcePoolRef`, `NativeQuotaWindow`, `QuotaObservation`, `BudgetObservation`, `UsageObservation`, `ExactMetricField`, `CapacityProjection`, `CapacityHealth`, `BurnRate`, `CapacityForecast`, `CapacityAggregation`, `DerivationRecord`, `CapacityCommitReceipt`, and capacity retention concepts;
- semantic validation of typed capacity payloads after M03 envelope validation;
- current selection, freshness, aggregation, health, burn, forecast, and retention policies;
- all `capacity_*` tables, constraints, indexes, repository ports, and centrally allocated M05 migration revisions;
- `capacity.v1`, including CTR-CAP-001..009 and M05-owned payload schemas consumed by M03 provider ports;
- the M05 side of synchronized CTR-COL-006 commit/status semantics;
- capacity events, health contribution, configuration declarations, documentation, tests, and evidence.

M05 does not own provider facts, provider collection, provider authentication, registry labels/relationships, alert behavior, public HTTP transport, UI state, or physical backup files.

### Allowed paths for a future implementation agent

These paths require root allocation after approval:

```text
backend/src/agentmonitor/modules/capacity/**
backend/src/agentmonitor/adapters/persistence/capacity/sqlite/**
backend/tests/capacity/**
backend/tests/integration/capacity/**
docs/modules/capacity.md
docs/test-evidence/capacity/**                 # sanitized evidence only, if approved
```

Shared paths require explicit single-owner allocation for each change:

```text
backend/src/agentmonitor/contracts/capacity_v1.py
backend/src/agentmonitor/contracts/common_quantity_v1.py
backend/src/agentmonitor/contracts/common_provenance_v1.py
backend/migrations/versions/<allocated-capacity-revision>.py
backend/src/agentmonitor/composition/**
backend/tests/contract/**
configuration registry
OpenAPI and generated-client source/output
traceability, risk, runbook, dependency manifest, lockfile, SBOM, and notices
```

### Allowed dependencies and imports

- M05 domain code may import only the Python standard library, approved `CTR-COMMON-001..004/006`, and its own domain/contracts.
- M05 application code may consume synchronized M02 scope/resource views, M03 typed envelopes/provenance/extension descriptors, M04 commit/run/event contracts, M01 authorization decisions where invoked directly, and M08 health/export/retention orchestration ports.
- Persistence adapters may import the admitted SQLAlchemy/Alembic stack and M05 repository/unit-of-work ports.
- Composition may route typed M03 outcomes from M04 to the M05 commit implementation and M05 events/queries to M07/M08/P01.
- P01/M07/M08 consume only published M05 contracts; P02 consumes only P01-generated API contracts.

### Forbidden dependencies and imports

M05 domain/application code must not import FastAPI, Starlette, Pydantic transport models, SQLAlchemy, Alembic, SQLite APIs, provider SDKs/CLIs, provider or platform adapters, OS/filesystem/process/network APIs, React/UI code, or another module's implementation. An implementation agent must not:

- read or write `reg_*`, `collection_*`, `provider_system_*`, `alert_*`, `runtime_*`, or operations tables;
- import another module's ORM/repository/private DTO or copy its public schema;
- contain Claude/Codex/Ollama conditionals or parse a provider response;
- fetch a provider, read a profile, inspect credentials, or trigger collection from a capacity query;
- store raw provider payloads, raw extensions, raw errors, paths, credentials, emails, prompts, responses, tools, source code, or arbitrary environment values;
- calculate a denominator/reset/credit/limit from absence, merge incompatible windows/pools, convert currencies, or label cached data current;
- own an alert threshold/lifecycle or emit a dashboard notification directly;
- use a fake repository/clock/provider/HTTP service, replay, fixture telemetry, seeded observation, demo account, or test-only production path;
- edit any unallocated shared path, `.env`, provider state, operator database, or external resource.

## 2. Requirements and traceability

| Requirement/AC | Planned M05 behavior | Proposed contract | Test/scenario IDs | Evidence gate |
|---|---|---|---|---|
| FR-ORG-003 | Aggregate capacity and budget health by M02 global/organization/provider/account/resource scope without double-counting | CTR-CAP-003, CTR-REG-001/002/005 | M05-PURE-026..030, M05-DB-022/023, M05-HTTP-005, M05-BROWSER-003 | Pure aggregation plus real scope/DB/API/browser |
| FR-QUOTA-001 | Preserve every approved provider-native quota window, values, units, reset/status/source separately | CTR-CAP-001 | M05-PURE-001..005, M05-DB-002..006, M05-LIVE-001..003 | Typed policy, real DB, live reconciliation |
| FR-QUOTA-002 | Retain approved provider-specific fields only through versioned extension schema; never force a universal total | CTR-CAP-001, CTR-PROV-008 | M05-PURE-006/007, M05-DB-007, M05-SEC-003, M05-LIVE-004 | Contract/privacy/live review |
| FR-QUOTA-003 | Derive Available/Constrained/Critical/Exhausted/Authentication Required/Unknown with constraining window and completeness | CTR-CAP-003 | M05-PURE-014..021, M05-DB-017..019, M05-LIVE-005 | Pure policy, real projection, live state when available |
| FR-QUOTA-004 | Expose authoritative/reported/derived/heuristic/experimental/stale/unknown distinctions with precision/confidence | CTR-COMMON-004, CTR-CAP-001/003 | M05-PURE-008..013, M05-DB-008/016, M05-HTTP-002, M05-BROWSER-001 | Provenance/freshness contract and real stack |
| FR-QUOTA-005 | Compute burn and exhaustion forecast only from sufficient compatible observations; disclose uncertainty and inputs | CTR-CAP-007 | M05-PURE-031..042, M05-DB-024..026, M05-HTTP-006, M05-LIVE-006 | Pure/mutation, real history, live comparison |
| FR-QUOTA-006 | Enable exact Claude/Codex/Ollama quota payload shapes only after M0 evidence | CTR-CAP-001 consuming CTR-PROV-002/004 | M05-CONTRACT-001..003, M05-LIVE-001..006 | M0 matrix and current production adapter |
| FR-BUDGET-001 | Persist/query real Anthropic/OpenAI/Ollama API account usage/budget capabilities exactly as supported | CTR-CAP-002 | M05-DB-009..015, M05-LIVE-007..010 | Real configured billing accounts and authoritative source |
| FR-BUDGET-002 | Represent spend, available spend, credits, soft/hard limits, period/reset, enforcement, and forecast as distinct field states | CTR-CAP-002/007 | M05-PURE-043..048, M05-DB-011/012, M05-HTTP-003, M05-LIVE-008/009 | Exact domain/DB/API/live reconciliation |
| FR-BUDGET-003 | Preserve supported organization/account/project/workspace/key-safe/model/token/time-bucket dimensions without inventing unavailable breakdowns | CTR-CAP-002/006 | M05-PURE-049..052, M05-DB-013..015, M05-HTTP-004, M05-LIVE-010/011 | Typed dimensions and live provider comparison |
| FR-BUDGET-004 | Use exact decimal or currency minor units; prohibit binary float end to end | CTR-COMMON-003, CTR-CAP-002 | M05-PURE-053..058, M05-DB-016, M05-HTTP-007, M05-SEC-004 | Arithmetic, storage, transport, export inspection |
| FR-BUDGET-005 | Keep subscription and pay-as-you-go/API resources as distinct pools | CTR-CAP-001/002/003 | M05-PURE-027..030, M05-DB-022/023, M05-BROWSER-003 | Aggregation invariants and real UI |
| FR-BUDGET-006 | Expose Supported/Experimental/Deferred/Unsupported/Unknown per provider capability/role with no invented values | CTR-PROV-002/004, CTR-CAP-001/002 | M05-PURE-009/010, M05-CONTRACT-001..003, M05-LIVE-012 | M0 evidence and contract/live matrix |
| FR-COL-004 | Reject capacity success/partial inputs without required source, time, versions, freshness, precision, confidence, and value kind | CTR-COMMON-004, CTR-CAP-004 | M05-PURE-008..013, M05-DB-008, M05-CONTRACT-004 | Domain/commit contract validation |
| FR-COL-006/008 | Preserve unavailable/unsupported/unknown separately; failure never creates zero/new observation or freshens current state | CTR-CAP-003/004 and CTR-COL-003/004 | M05-PURE-009/018/023, M05-DB-019/020, M05-HTTP-008 | Real event/application/database path |
| FR-HIST-001 | Retain capacity observations, derivations, health changes, and retention audit for 365 days | CTR-CAP-006 | M05-PURE-059, M05-DB-027..029 | Pure cutoff plus real aged DB evidence |
| FR-HIST-002 | Query raw trends and explicit UTC buckets/timelines without merging native windows or units | CTR-CAP-006/007 | M05-PURE-060..064, M05-DB-030..032, M05-HTTP-009, M05-BROWSER-002 | Real history/API/chart/table |
| FR-HIST-003 | Purge only expired non-current capacity history in bounded auditable batches | M05 retention ports | M05-PURE-059/065, M05-DB-027..029, M05-OPS-004 | Real DB and M08 orchestration |
| FR-HIST-004 | Expose bounded machine-readable capacity export pages and retention preview through M08, never direct table access | CTR-CAP-006, CTR-OPS-005 | M05-DB-033, M05-OPS-005, M05-SEC-005 | Real export/secret scan |
| FR-HIST-005 | Store UTC instants and leave configured-timezone rendering to P01/P02 | CTR-COMMON-002, all contracts | M05-PURE-066, M05-DB-034, M05-BROWSER-004 | Pure/DB round trip and browser timezone |
| FR-OPS-002/005/006 | Publish safe capacity health/version/consistency summaries; exclude secrets/content from operations artifacts | CTR-OPS-006 | M05-OPS-001..007, M05-SEC-001..007 | Real health/diagnostics/backup/export scans |
| FR-SAFE-001/002 | Query/recompute/purge through authorized orchestration only; no provider or process-control operation exists | full `capacity.v1` surface | M05-ARCH-001..004, M05-SEC-008 | Contract/import/API absence review |
| NFR-ARCH-001/002 | Framework-free isolated domain, typed versioned contracts, one owner for capacity state/tables | `capacity.v1` | M05-ARCH-001..005 | Import and ownership gates |
| NFR-API-001/002 | P01 maps typed current/history/forecast resources; P02 uses generated client only | CTR-API-001/CTR-UI-001 consuming CTR-CAP | M05-HTTP-001..010, M05-BROWSER-001..005 | Real server/OpenAPI/client/browser |
| NFR-DATA-001 | Real file SQLite repositories/migrations preserve exact values and PostgreSQL-portable semantics | CTR-DB-001/002 | M05-DB-001..036 | Fresh/upgrade/concurrency/query-plan/restore evidence |
| NFR-TEST-001/002; AC-TEST-001..006 | Meaningful R/G/R at correct boundaries; no doubles/seeded telemetry; explicit live states | evidence contracts | all M05 scenarios | Independent test-integrity and mutation review |
| NFR-SEC-001, NFR-PRIV-001/002 | Strict payload/extension allowlists, exact bounds, minimized storage/log/API, no analytics | capacity schemas | M05-SEC-001..010 | DB/WAL/log/API/browser/export/backup/network review |
| NFR-DOC-001 | Contracts, algorithms, limitations, operations, live reconciliation, and evidence remain current | documentation outputs | M05-DOC-001/002 | Documentation and canonical gate |
| NFR-LIC-001 | No M05 dependency without exact admission; SBOM/notices stay current | dependency gate | M05-DEP-001/002 | Actual locked graph review |
| NFR-PLAT-001 | Capacity core remains OS-neutral; Linux/macOS differences cannot enter its domain | boundary contract | M05-ARCH-005, M05-OPS-008 | Import check; actual platform matrix |
| NFR-PERF-001 | Bounded indexed current/history queries and projections support 100 accounts and planned observation scale | repository/query contracts | M05-PERF-001..005 | Real AgentMonitor-owned structure plus real observation volume |
| NFR-RES-001; AC-OPS-003 | One malformed input/source/projection failure is isolated and existing safe queries remain available | commit/projection outcomes | M05-DB-020/021/035, M05-LIVE-013, M05-OPS-009 | Real provider/application failure isolation |
| NFR-OBS-001 | Safe structured correlation and bounded health events contain no metric values or identities unless explicitly authorized | events/health | M05-SEC-002/006, M05-OPS-002 | Real logs/events/diagnostics |
| NFR-COMP-001 | DTO/event/schema/derivation methods and persisted exact representations obey versioning policy | CTR-CAP-001..009 | M05-ARCH-002/003, M05-DB-001/036, M05-CONTRACT-001..004 | Compatibility/migration/consumer review |
| AC-V1-001..008 | M05 traceability, approval, API/schema, migration, security/license/docs/secret/simulation gates contribute truthfully | all | M05-DOC-001/002, M05-ARCH-001..005, M05-SEC-001..010 | Integrated release gate; M05 alone cannot pass release |
| AC-LIVE-004/005/007 | Real adapters deliver supported typed capacity data; displayed values reconcile; rare states stay Blocked when unavailable | CTR-PROV/CTR-CAP live matrix | M05-LIVE-001..013 | Owner-coordinated T6 evidence |
| AC-UI-002..006 | Dashboard receives real capacity/budget/freshness/history/derivation states and accessible explanations | P01 mappings of CTR-CAP | M05-BROWSER-001..005, M05-LIVE-005/008 | Real backend, built UI, real observations |
| AC-HIST-001/002 | Real collection-to-history-to-chart path and real 365-day deletion behavior | CTR-COL-006/CTR-CAP-006 | M05-LIVE-014, M05-DB-027..033, M05-BROWSER-002 | Full real vertical slice; aged data may remain Blocked |
| AC-OPS-004/005 | Backup/restore/upgrade preserve exact capacity history/projections or recover safely | schema/consistency ports | M05-OPS-003/006/007/010 | Real database and installed procedures |

### Approved interpretations and synchronization proposals

- Approved: each provider-native quota window and subscription/API pool remains separate; no universal capacity total exists.
- Approved: exact money never uses binary floating point, and every derived value exposes inputs and explanation.
- Proposed: `Unsupported` belongs to an evidenced capability/field decision, while `Unavailable` belongs to an attempted collection/runtime dependency. Neither becomes numeric zero.
- Proposed: organization/global aggregation always reports subject and health counts. Numeric totals are optional and emitted only for an M0/M02-approved additive set with identical unit/currency, interval, semantic role, and no rollup overlap.
- Proposed: normalized health uses the worst known independently constraining native window without summing windows. An Unknown window prevents an `Available` aggregate but does not erase definitive Exhausted/Critical evidence; completeness remains explicit.
- Draft-aligned: M05 owns versioned normalized capacity-health classification policy. M07's account > provider > organization > global alert-threshold resolution is separate and is never supplied to M05.
- Draft-aligned: M05 consumes CTR-REG-010 and CTR-COL-007 as narrowly scoped, ordered auth/collector inputs and produces CTR-CAP-009; provider `reauthentication_required` is never inferred from a generic completion/failure.
- Proposed: provider-returned historic buckets are immutable observations with provider data-through time, not synthetic poll snapshots. Poll snapshots and provider history use distinct observation kinds.
- Proposed: the most recent source observation may remain retained as the active stale basis beyond the ordinary 365-day history cutoff until replaced or the resource is retired; history listings still apply the approved retention window. This requires product/data-owner approval.

## 3. Domain design

### 3.1 Identities, scopes, and resource pools

`CapacitySubjectV1` contains opaque provider, installation, account, resource, and optional project/workspace/key-safe/model scope IDs exactly as approved by M02/M0. It never contains a display label, email, profile path, credential, or provider-specific untyped map.

`ResourcePoolRefV1` identifies one independently constrained or billed pool through M02 `AccountResourceViewV1`. Pool kinds include only synchronized normalized values such as subscription, API organization, API project, workspace, or prepaid balance; provider-specific kinds remain a versioned extension until normalized by ADR. Subscription and API pools are never interchangeable.

Each relationship used for aggregation has an explicit evidence-backed semantic:

- `independent`: constrains separately and is never numerically combined with siblings by default;
- `additive`: values may be summed only within an approved aggregation group and compatible units/intervals;
- `rollup_parent`: overlaps its declared children and must not be counted with them;
- `informational`: displayed but not constraining or aggregateable;
- `unknown`: no numeric aggregation is permitted.

M02 owns the relationship itself. M05 stores the referenced relationship/policy version with each projection so a registry change triggers rebuild rather than retroactively changing observation facts.

### 3.2 Native quota-window identity and lifecycle

`NativeQuotaWindowV1` is keyed by provider/resource/capability plus an M0-approved identity scheme and opaque native window key. It includes safe label field-state, scope dimensions, native unit, semantic role, optional window start/end, reset/renewal instant with precision/timezone evidence, and lifecycle.

Rules:

- window identity never derives from a mutable display label alone;
- if no stable identity scheme is approved, the capability cannot maintain a current native-window projection and remains Unknown/Blocked rather than merging snapshots heuristically;
- window start/end/reset are independent fields; one is not inferred from another;
- reset can be exact, rounded, range, estimated, or Unknown and retains provider timezone evidence when supplied;
- a changed provider window definition creates a new definition version; old observations retain their original version;
- disappeared windows become `not_observed_currently` only after an approved complete collection proves absence; a partial/failing run cannot retire them;
- one window never overwrites another because scope/label looks similar.

### 3.3 Exact fields, units, and field states

Every optional metric uses `ExactMetricFieldV1` with exactly one state:

- `value`: canonical exact value plus unit/currency and precision;
- `unknown`: source/capability exists but a trustworthy value is unavailable or meaning is unresolved;
- `unsupported`: M0 capability evidence establishes the field is not exposed for the exact scope/version/role;
- `not_applicable`: the field has no semantic meaning for that resource kind;
- `withheld`: provider indicates a value exists but the credential role cannot access it, if M0 proves this distinct state.

`Unavailable` is not a field value; it is a collection/dependency condition. `Missing` in an input is accepted only when the typed schema declares its field state explicitly. Zero is a real value only when the source reports zero with valid provenance.

`ExactQuantityV1` is a bounded canonical decimal coefficient plus scale and unit identifier. Integral token/request counts require scale zero. Ratios use an exact decimal in `[0,1]` or basis points according to one frozen representation. Percent display is derived; it is not stored as binary float. Money is either currency plus signed/unsigned integer minor units with the exact currency exponent used, or currency plus canonical exact decimal when M0 establishes that minor units are unsuitable. Currency conversion is absent.

Arithmetic rejects unit/currency/semantic mismatch, non-canonical encodings, NaN/infinity, negative values where the specific metric forbids them, precision beyond approved bounds, and values above configured serialization/storage bounds. Rounding occurs only at an explicitly versioned presentation/derivation step and records its mode.

### 3.4 Provider input contracts

M05 owns four typed value families used inside M03 `CollectionOutcomeV1[T]`:

- `ProviderQuotaInputV1`: one complete collection batch containing target/resource/window definitions and quota observations;
- `ProviderUsageInputV1`: provider-native time buckets and approved grouping dimensions with exact token/request/quantity components;
- `ProviderCostInputV1`: provider-native cost buckets with exact money, billing/data-through interval, and grouping dimensions;
- `ProviderBudgetInputV1`: budget/credit/limit/enforcement observations for one billed resource and period.

Each batch declares capability/schema version, completeness (`complete_scope` or `partial_scope`), exact target/scope, observation/data-through interval, item count, stable item ordinals or source IDs, and approved extension schema references. A partial batch lists explicit missing scopes/fields and can update only included items; it cannot retire an omitted window or zero an omitted bucket.

M03 validates the outer outcome, source, version, and extension registration. M05 validates capacity semantics, exact values, compatible dimensions, window/resource identity, and derivation eligibility. A generic dictionary, raw JSON, arbitrary grouping key, raw model name, or unknown extension never reaches persistence.

### 3.5 Immutable observations and idempotent ingestion

Every accepted observation is immutable and records:

- observation ID and observation kind (`poll_snapshot` or `provider_history_bucket`);
- account/resource/window/budget/usage scope IDs and definition versions;
- exact field states and values;
- provider status/enforcement code only through an approved mapping/extension;
- `observed_at`, optional data-through start/end, `collected_at`, and M05 `stored_at` in UTC;
- complete `ObservationProvenanceV1`, provider/adapter/schema versions, run ID, payload digest, and safe warning codes;
- optional provider observation ID only when classified safe and stable by M0;
- no raw source payload or free-form error.

Within one commit, item order is canonicalized by typed identity, not provider response order. The idempotency key is `(collection_run_id, capacity_capability, payload_digest)`. The first valid commit persists observations, projections, derived facts/events, receipt, and outbox atomically. An exact replay returns the same receipt. The same run/capability with a different digest returns `capacity_commit_conflict`, preserves the first commit, blocks projection mutation for that run, and raises an integrity diagnostic.

Separate collection runs normally produce separate poll snapshots even if values are equal. A stable provider observation ID may deduplicate the same provider-history fact across pagination/runs only under an M0-approved identity scheme. Equality of values alone never proves duplication.

### 3.6 Current selection, freshness, and conflict policy

Current selection occurs independently for each resource/window/budget field scope. Candidate precedence is based on semantic time and approved source policy, never database insertion order alone:

1. compatible, accepted schema/definition and non-invalidated observation;
2. greatest provider data-through end when available, otherwise greatest observed-at;
3. approved source priority only for sources declared interchangeable for that exact capability/field;
4. greatest collected-at when the prior dimensions are equal and values do not conflict.

An older late-arriving observation is retained in history but cannot replace a newer projection. Two observations at the same semantic position with incompatible values/source claims create `projection_conflict`; the last projection is retained as stale/conflicted or becomes Unknown according to approved policy, and no arbitrary winner is selected.

Freshness is evaluated at an explicit `as_of` using the observation's source-policy freshness deadline and data latency evidence. Equality at the deadline is stale. A missing/Unknown freshness policy prevents a `fresh` classification. States are `fresh`, `stale`, `freshness_unknown`, `conflicted`, or `no_observation`. Provider failure never advances the freshness deadline or creates a new observation.

### 3.7 Normalized capacity health

`CapacityHealthV1` has exactly the required normalized states:

- `available`
- `constrained`
- `critical`
- `exhausted`
- `reauthentication_required`
- `unknown`

It additionally carries completeness (`complete`, `partial`, `unknown`), freshness, constraining resource/window ID, policy ID/version, input observation/event IDs, evaluated-at time, stable explanation codes, and derivation provenance.

Proposed deterministic precedence is owned by M05 and is synchronized only with the M02/M04 input semantics; M07 alert policy is not an input:

1. a current matching provider-auth signal yields `reauthentication_required` until a later verified CTR-REG-010 recovery generation clears it;
2. definitive fresh exhausted evidence on any independently constraining window yields `exhausted`;
3. the lowest trustworthy remaining ratio among fresh independently constraining windows is evaluated by the versioned M05 capacity-health classification rules and yields `critical`, `constrained`, or `available`; those classification rules are not M07's 30/15 alert activation thresholds;
4. an explicit provider status may participate only through an M0-approved mapping with provenance and cannot override contradictory exact values silently;
5. `available` requires all expected constraining pools/windows to be complete, fresh, non-conflicting, and classifiable;
6. known critical/constrained evidence may be returned with `partial` completeness when an additional window is Unknown, because the unknown window could be worse; the explanation exposes that uncertainty;
7. if no trustworthy classifiable constraint exists, or only available evidence exists alongside an unresolved constraining window, the state is `unknown`;
8. stale facts never yield a fresh Available state. The view may retain the last derived state only with stale status and an `as_of` explanation, or return Unknown according to the synchronized policy.

Used/remaining/limit ratios are derived only when numerator, denominator, units, and semantics are compatible. A zero limit, contradictory values, or an inferred denominator creates a validation/Unknown outcome. Health chooses a constraining window; it does not sum native windows.

### 3.8 Organization and global aggregation

An aggregate is calculated over one immutable M02 `RegistryScopeSnapshotV1` revision and one M05 `as_of`. Each subject/resource appears once. Archived/disabled rules come from the snapshot and are exposed in completeness counts.

Every aggregate includes:

- total/included/excluded/unknown/stale/conflicted subject and resource counts;
- normalized health counts and worst definitive known health;
- separate resource-pool/window inventories;
- source/freshness coverage and snapshot/projection versions;
- omitted-reason counts and no-data/partial flags.

Numeric aggregation is allowed only when all members share an approved additive aggregation group, identical unit or currency, compatible billing/window interval and semantic role, and no parent/child rollup overlap. Otherwise the numeric result is absent with a stable reason such as `incompatible_unit`, `mixed_currency`, `overlapping_rollup`, `unknown_relationship`, `different_window`, or `incomplete_input`. No conversion or universal percentage is invented.

### 3.9 Burn rate and forecast

Burn and forecast are pure versioned derivations over immutable input observation IDs. The initial method is selected at synchronization; this plan does not freeze a statistical algorithm before data shape/precision evidence exists.

Any approved method must require:

- one exact resource/window/field identity, unit, source-compatibility set, and reset segment;
- a configured minimum count and elapsed span of ordered observations;
- positive usable consumption change under the field's monotonic semantics;
- no unresolved reset, source/schema change, projection conflict, or gap above the approved limit;
- a current exact/appropriately bounded remaining value for exhaustion time;
- explicit treatment of provider rounding and data latency.

Resets split series and never appear as negative consumption. Corrections/refunds/decreasing cumulative use either start a new evidenced segment or make the method insufficient; they are not silently clamped. Missing/unsupported fields, a flat/negative rate, too few points, mixed units, stale current input, or excessive uncertainty returns a typed `insufficient_input`/`not_applicable` result with reasons.

`CapacityForecastV1` contains method/version, generated-at, source window/segment, input observation IDs, exact rate with unit/time basis, estimate or bounded earliest/latest exhaustion instants, reset-before-exhaustion relationship when known, precision/confidence/uncertainty explanation, validity deadline, and invalidation reason. It never claims provider authority.

### 3.10 History, buckets, and retention

- Raw history is ordered deterministically by semantic time then observation ID and is cursor-paginated.
- A history query selects one explicit subject/resource/window/metric/unit/currency; it cannot mix incompatible series.
- Server-side buckets align to UTC boundaries and identify method (`last`, `min_max`, `sum_delta`, or another approved semantic). A method is valid only for the metric kind; the raw series remains available.
- UI timezone changes presentation only and never rebuckets persisted facts without an explicit query timezone contract approved by P01/P02.
- Derived series include method/version and input IDs. Provider-returned buckets remain provider observations rather than AgentMonitor rollups.
- The ordinary history retention cutoff is 365 days from an explicit UTC `as_of`. Current source observations, open integrity investigations, and undelivered event references are protected until their owning condition clears.
- Purge is bounded, idempotent, auditable, and coordinated by M08. It never deletes definitions, current projections, current-source observations, active commit receipts required for M04 crash reconciliation, or undelivered events.
- M05 provides a retention preview/export cursor so M08 can create the approved machine-readable export before deletion when required by the synchronized export policy.

### 3.11 Concurrency, ordering, and degradation

- One transaction serializes commit/projection change for the affected resource/window scopes; unrelated resources can commit concurrently.
- Optimistic projection versions and the receipt uniqueness rule prevent lost updates.
- Events are at least once and consumers deduplicate by event ID. Ordering is guaranteed only per capacity projection stream/version.
- A registry relationship change schedules a projection rebuild using the new scope revision; immutable observations are not rewritten.
- A health-policy change recomputes projections from retained inputs with a new policy version and emits events only for real state changes.
- A projection/forecast failure after observations are safely committed is recorded as degraded and retried from stored facts; it does not roll back or duplicate the immutable observations.
- An invalid item in an otherwise declared complete batch rejects the batch atomically unless the provider payload schema explicitly permits independent items and the M03 outcome is `partial` with the failed item declared. No silent partial commit occurs.
- Failure in one account/resource projection cannot block reads for unrelated capacity subjects or the dashboard.

## 4. Public contracts

All contracts are **Proposed**. M0-dependent fields cannot become Approved before evidence and producer/consumer synchronization. DTO examples, if later added, must be structural and explicitly not live telemetry.

### 4.1 Published contract summary

| Register ID | Proposed name/version | Producer | Consumers | Compatibility promise |
|---|---|---|---|---|
| CTR-CAP-001 | `ProviderQuotaInputV1`, `QuotaWindowViewV1`, current/query ports | M05 | M03 adapters/M04 commit route; M07/P01/UI/M08 export | Window/scope/unit/field-state/reset meanings fixed; additive optional fields only |
| CTR-CAP-002 | `ProviderUsageInputV1`, `ProviderCostInputV1`, `ProviderBudgetInputV1`, `BudgetViewV1` | M05 | M03 adapters/M04; M07/P01/UI/M08 export | Money, period, pool, dimension, field-state meanings fixed |
| CTR-CAP-003 | `CapacityHealthViewV1`, `CapacityAggregateViewV1`, health/query/rebuild ports | M05 | M07/P01/UI/M08 | State precedence, completeness, constraining-source semantics versioned |
| CTR-CAP-004 | `CapacityObservationRecordedV1`, M05 commit/status/receipt contracts | M05 | M04/M07/M08 | Immutable observation refs; run+digest idempotency; no raw values in event |
| CTR-CAP-005 | `CapacityHealthChangedV1` | M05 | M07/M08 | Immutable transition event, per-projection ordering, derivation refs |
| CTR-CAP-006 | `CapacityHistoryQueryV1`, history/export/retention ports | M05 | P01/UI/M08 | Bounded ranges/cursors, explicit buckets, raw-vs-derived meaning stable |
| CTR-CAP-007 | `CapacityForecastV1`, forecast query/recompute ports | M05 | M07/P01/UI/M08 | Method/version/input/uncertainty and insufficient-input semantics stable |
| CTR-CAP-008 | `CapacityForecastChangedV1` | M05 | M07/M08 | Per-forecast generation, explicit invalidation/recovery and input references; silence is not recovery |
| CTR-CAP-009 | `CapacityAvailabilityChangedV1` | M05 | M07/M08 | Supported/unsupported, available/unavailable, unknown, stale and provider-reauth states remain distinct |

### 4.2 CTR-CAP-001 — quota inputs, views, and queries

`ProviderQuotaInputV1` contains the batch header from section 3.4 and bounded `ProviderQuotaItemV1` values. Each item contains approved subject/resource/window identity, definition version fields, exact used/remaining/limit/ratio field states, provider status field-state, reset/renewal fields, provenance link, stable item ordinal/source ID, and optional registered `SafeProviderExtensionV1`.

`QuotaWindowViewV1` contains only authorized opaque subject IDs, safe label field-state, pool/window scope, exact fields, reset/period, provider status, freshness, completeness, provenance summary, current observation ID, collection run ID, projection version, and explanation codes. It never contains profile refs, credential roles, raw provider data, or a fabricated combined total.

Published ports:

| Port | Input/output | Preconditions/authorization | Errors/outcomes | Idempotency/side effects |
|---|---|---|---|---|
| `GetQuotaWindowV1` | authorized window ID + `as_of` -> view | `read:telemetry`; subject visible | not found/forbidden/dependency unavailable | read-only; no collection |
| `ListQuotaWindowsV1` | scope snapshot/filter/cursor/page/`as_of` -> bounded page | authorized scope; compatible registry revision | invalid filter/cursor/stale scope/unavailable | read-only |
| `GetAccountCapacityV1` | account ID + `as_of` -> native windows plus health summary | authorized account | not found/partial/unavailable | read-only; no refresh |
| `RebuildQuotaProjectionV1` | affected subject/window IDs + source/policy generations | internal authorized orchestrator | stale generation/conflict/repository unavailable | same generation is idempotent |

### 4.3 CTR-CAP-002 — API usage, cost, budget, and credits

`ProviderUsageInputV1`, `ProviderCostInputV1`, and `ProviderBudgetInputV1` use closed, versioned dimension vocabularies. Every supported dimension has a safe opaque identifier and field state. An API key dimension, if supported, is a provider-safe opaque/key-prefix identifier explicitly approved by M0; secret key values and reversible fingerprints are prohibited.

`BudgetViewV1` contains pool/resource/project scope, billing/data-through interval, exact spend/available/credit/soft-limit/hard-limit field states, currency, enforcement status, reset/renewal, token/request/cost breakdown availability, freshness/provenance/completeness, current observation and projection versions, and forecast reference. `available_spend` is provider-reported or derived only when an approved equation and compatible exact inputs exist; its value kind makes the distinction explicit.

Published ports are `GetBudgetV1`, `ListBudgetsV1`, `ListUsageBreakdownsV1`, and `GetAccountApiCapacityV1`. All are bounded, authorized, read-only, and never start provider work. Unsupported dimensions appear as capability metadata, not rows of zeros.

### 4.4 CTR-CAP-003 — normalized health and aggregation

`CapacityHealthViewV1` fields are subject/pool scope, state, completeness, freshness, constraining window/resource, M05 classification-policy ID/version and authorized classification explanation, evaluated/generated times, input observation/availability-event IDs, source/value-kind/precision/confidence, stable explanation/omitted-reason codes, projection version, and derivation ID. It carries no M07 rule or alert-threshold snapshot.

`CapacityAggregateViewV1` adds immutable registry scope revision, included/excluded subject counts, health counts, worst definitive health, freshness/source coverage, pool inventories, compatible numeric aggregate groups, omitted reasons, and generated time. It never returns one global percentage or money total when inputs are incompatible.

Ports:

- `GetCapacityHealthV1(subject, as_of)`;
- `GetCapacityAggregateV1(registry_scope_snapshot, as_of)`;
- `ApplyCapacityAvailabilitySignalV1(signal)` for the exact synchronized M04-derived capacity scope/generation;
- `ApplyCapacityHealthClassificationPolicyV1(m05_policy_snapshot)` and `RecalculateCapacityHealthV1(scope, policy_generation)` through internal M05-authorized orchestration; no M07 contract supplies this input;
- `GetCapacityComponentHealthV1` as M05's bounded contribution to CTR-OPS-006.

Application mutations require trusted internal principals and generation/idempotency fields. M05 never pulls M07 settings or M04 tables.

### 4.5 CTR-CAP-004 — commit, receipt, and observation event

M05 implements the synchronized capacity specialization of `CollectionOutcomeCommitPortV1`:

```text
CommitCapacityCollectionOutcomeV1(
  run_id, target, capability, success_or_partial_typed_payload,
  payload_digest, provenance, collection_times, deadline_context
) -> CapacityCommitReceiptV1
```

Preconditions: supported capacity capability/schema, M03-validated success/partial envelope, target/resource identity compatible with M02 snapshot, current fencing/authorization supplied by M04 contract, bounded payload, and required provenance. The commit never invokes a provider.

`CapacityCommitReceiptV1` contains run ID, payload digest, consumer key/version, observation IDs, affected projection IDs/versions, stored-at range, emitted event IDs, and receipt version. `GetCapacityCommitStatusV1(run_id, capability)` returns `not_committed`, `committed(receipt)`, `conflict`, or `unavailable`.

`CapacityObservationRecordedV1` uses `EventEnvelopeV1` and contains observation IDs, subject/resource/window IDs, capability, observation kind, observed/data-through/stored time ranges, provenance/definition/schema versions, projection IDs/versions, completeness, and safe warning codes. It contains no numeric value, currency amount, provider extension value, account label, or raw payload. Consumers re-query authorized views.

Delivery is at least once; event ID deduplicates. Ordering is per subject/resource/window projection stream. A semantic change to idempotency, receipt digest, or event contents is breaking.

### 4.6 CTR-CAP-005 — health-change event

`CapacityHealthChangedV1` contains projection ID/version, subject/resource scope, old/new normalized state and completeness/freshness, constraining window ID, policy ID/version, input observation/availability references, stable reason codes, evaluated time, and derivation reference. It emits only when the canonical state/completeness/freshness tuple changes, not on every poll.

M07 consumes the event idempotently and owns fingerprints/lifecycle. M08 consumes it only for safe audit/diagnostic summaries. Event payload contains no M07 alert thresholds or numeric usage unless synchronization proves the numeric facts are necessary; consumers query M05 under authorization.

### 4.7 CTR-CAP-006 — history, export, and retention

`CapacityHistoryQueryV1` requires subject/resource/window/metric selection, explicit UTC start/end, series kind (`raw_provider`, `poll_snapshot`, `derived`), optional approved bucket method/size, deterministic cursor, bounded page size, and authorized disclosure scope. Response points include exact field state/value, unit/currency, semantic interval, provenance/freshness at observation time, and observation/derivation IDs.

Additional ports:

- `ListCapacityHistoryV1` and `ListCapacityHealthHistoryV1`;
- `ListCapacityExportRecordsV1` for M08's allowlisted machine-readable export;
- `PreviewExpiredCapacityHistoryV1(as_of, batch_limit)` returning opaque eligible IDs/counts/range only;
- `PurgeExpiredCapacityHistoryV1(as_of, batch_limit, expected_preview_digest, export_checkpoint_ref)` returning counts and audit ID;
- `ValidateCapacityConsistencyV1` for restore/upgrade readiness.

Purge is internal, requires exact preview/generation agreement, and is idempotent for an audit/batch key. Whether `export_checkpoint_ref` is mandatory for every automatic purge is an approval decision; it can never contain a path supplied by provider data.

### 4.8 CTR-CAP-007 — burn and forecast

`CapacityForecastV1` is a discriminated union:

- `available`: exact burn rate, time basis, exhaustion estimate/range, uncertainty/confidence, reset relationship, validity, method/version, derivation/input IDs;
- `insufficient_input`: stable reason set and input coverage summary;
- `not_applicable`: metric/resource semantics do not permit forecast;
- `stale`: a prior forecast remains explainable but is no longer valid;
- `conflicted`: input facts cannot support a single derivation.

Ports are `GetCapacityForecastV1`, `ListCapacityForecastsV1`, and internal `RecomputeCapacityForecastV1`. Recompute is idempotent for canonical input set + method/policy version. A new input, reset, schema/source policy, or method version invalidates the old current forecast without rewriting its history.

CTR-CAP-008 is emitted when the canonical forecast union or its current generation changes. It carries forecast/subject/resource IDs, prior/current union state, generation, method/input references, validity interval, occurred/recorded times, explicit `active | invalidated | recovered | not_evaluable` truth, and safe reason codes. It contains no raw metric or money value; M07 re-queries the authorized view when explanation values are needed.

CTR-CAP-009 is the current availability signal/query family for capacity alerting. It carries the exact supported/unsupported, available/unavailable, unknown, withheld, stale, and provider `reauthentication_required` states, subject/capability/source generation, evidence refs, and explicit newer recovery. A collection completion, missing event, or stale observation cannot clear the state.

### 4.9 Consumed contracts and failure behavior

| Owner/contract | Required version/status | M05 use | Failure/degradation behavior |
|---|---|---|---|
| CTR-COMMON-001 `OpaqueIdV1` | `proposed_aligned` 1.0.0 | all identities | malformed IDs rejected; never parsed for meaning |
| CTR-COMMON-002 `TimestampAndDurationV1` | `proposed_aligned` 1.0.0 | UTC instants/durations | non-aware/non-UTC input rejected; no local-time storage |
| CTR-COMMON-003 `ExactQuantityV1` | `proposed_aligned` 1.0.0 | exact quantity/ratio/money primitives | incompatible/non-canonical/float input rejected |
| CTR-COMMON-004 `ObservationProvenanceV1` | `evidence_blocked` 1.0.0 | every observation/derivation | missing required provenance invalidates success/partial item |
| CTR-COMMON-006 `EventEnvelopeV1` | proposed-aligned V1 | M05 events/outbox | state mutation cannot claim event completion without durable outbox |
| CTR-COMMON-007 `FieldAvailabilityV1` | proposed-aligned V1 | every optional/current value state | invalid state/value combination rejects input; exact zero never substitutes for absence |
| CTR-EVT-001 | proposed-aligned V1 | durable event outbox, consumer receipt/checkpoint and replay | consumer outage does not roll back observations; backlog and incompatible major remain visible |
| CTR-FND-004/006/008 | `proposed_aligned` 1.0.0 | safe logs/correlation, migrations, evidence | incompatible foundation blocks writable readiness |
| CTR-CONFIG-001 | `proposed_aligned` 1.0.0 | declared M05 policies/settings | invalid or weakened invariant fails closed |
| CTR-DB-001/002 | `proposed_aligned` 1.0.0 | schema compatibility and repository/UoW | typed unavailable/conflict/corrupt; no direct DB escape |
| CTR-IAM-001/002 | `proposed_aligned` 1.0.0 | query/internal-operation authorization | deny on unavailable/unknown decision |
| CTR-REG-001/002/005/007 | mixed: CTR-REG-001/007 `proposed_aligned`; CTR-REG-002/005 `evidence_blocked` (1.0.0) | scope snapshot, account/resource pool identity, relationship revisions | unresolved/unknown relationship blocks numeric aggregation; history retained |
| CTR-PROV-002/003/004/008 | `evidence_blocked` 1.0.0 | capability/schema/source/outcome/provenance/extension validation | unsupported/unverified/invalid cannot become observation |
| CTR-COL-002/003/006 | `proposed_aligned` 1.0.0 | run refs, commit/status/receipt, completion ordering | no current update before receipt; sink failure isolated |
| CTR-REG-010 and CTR-COL-007 | evidence-blocked/proposed-aligned V1 | provider-auth and collector-health inputs used to derive CTR-CAP-009 | missing/stale generation cannot clear state; M05 never owns retry |
| M05-owned normalized health policy | CTR-CAP-003 V1 | capacity classification only; M07 thresholds are not an input | invalid/absent policy yields Unknown, never hidden defaults |
| CTR-OPS-005/006/007 | proposed-aligned V1 | export orchestration, health publication, and M05 participant implementation | M08 unavailability does not block M05 read queries; purge/export rules fail closed |

### 4.10 Error and outcome vocabulary

Stable safe M05 codes proposed for P01/application mapping:

- validation: `capacity_invalid_quantity`, `capacity_invalid_money`, `capacity_unit_mismatch`, `capacity_currency_mismatch`, `capacity_invalid_time_range`, `capacity_invalid_field_state`;
- identity/schema: `capacity_subject_unresolved`, `capacity_resource_unresolved`, `capacity_window_identity_unknown`, `capacity_schema_incompatible`, `capacity_extension_unapproved`;
- provenance/current state: `capacity_provenance_incomplete`, `capacity_observation_out_of_order`, `capacity_projection_conflict`, `capacity_freshness_unknown`, `capacity_observation_stale`;
- aggregation: `capacity_aggregation_incompatible`, `capacity_rollup_overlap`, `capacity_relationship_unknown`, `capacity_incomplete_scope`;
- derivation: `capacity_derivation_insufficient_input`, `capacity_derivation_conflict`, `capacity_method_incompatible`;
- commit/persistence: `capacity_commit_conflict`, `capacity_commit_deadline_exceeded`, `capacity_repository_unavailable`, `capacity_schema_storage_incompatible`, `capacity_event_unavailable`;
- query/retention: `capacity_not_found`, `capacity_invalid_cursor`, `capacity_range_too_large`, `capacity_retention_preview_changed`, `capacity_export_checkpoint_required`;
- dependency: `capacity_collection_unavailable`, `capacity_reauthentication_required`, `capacity_capability_unsupported`, `capacity_provider_version_unverified`.

Errors contain stable code, correlation ID, and authorized opaque subject ID only. They never echo metric values, money, labels, raw extensions, SQL, provider messages, paths, or exception arguments.

### 4.11 Contract-impact assessment

This plan proposes the first detailed CTR-CAP-001..009 schema set and changes no implemented contract. Before approval, root synchronization must:

1. freeze CTR-COMMON-003 exact numeric/money/ratio encoding and bounds;
2. reconcile M05-owned provider-input payloads with M03 capability ports and every A01–A03 producer;
3. confirm the Draft-aligned CTR-COL-006 commit seam and align receipts/status/generation/schema/digest/fencing with M04;
4. approve CTR-REG-010/CTR-COL-007 inputs and M05-produced CTR-CAP-008/009 explicit availability/forecast recovery signals;
5. confirm M05 ownership of normalized capacity-health classification and M07 ownership of alert thresholds, with no reverse dependency;
6. freeze M02 resource-pool/relationship/scope snapshot semantics needed to prevent double-counting;
7. freeze event/outbox owner, ordering, consumer acknowledgement, replay, and retention semantics;
8. approve API/export disclosure and derived-input detail with P01/P02/M08;
9. allocate M05 migration revisions and shared contract files;
10. update the central register statuses and create an ADR if any synchronized decision changes architecture, aggregation ownership, or event durability.

## 5. Data and persistence

All names and physical representations are proposed. Exact DDL, revision IDs, batch sizes, and SQLite settings require PLAN-DB review and central migration allocation. Every `capacity_*` table is owned exclusively by M05. Cross-module IDs are scalar values validated through contracts; no cross-module foreign key or join is introduced without an ADR.

### 5.1 Definitions and resource semantics

#### `capacity_resource_policy`

- internal policy row ID and M02 account/resource IDs;
- provider/capability, resource kind, relationship/aggregation semantic, parent resource scalar ID nullable;
- aggregation-group ID nullable, unit/currency/interval restrictions, constraining flag;
- M02 registry revision, M0 decision/evidence reference, policy schema version;
- effective-from/invalidated UTC instants and optimistic version.

This is an M05 projection of versioned facts needed to reproduce aggregation; it is not an identity registry. A registry change appends/updates policy state but never rewrites historical observation scope.

#### `capacity_quota_window_definition`

- window definition ID, provider/account/resource IDs, capability, identity-scheme version, native-window-key fingerprint/approved safe key;
- definition version and lifecycle;
- approved safe label field-state/value, semantic role, scope/model/feature safe IDs where supported;
- native unit, reset/renewal semantics, provider timezone/precision field-state;
- extension schema reference only, never an unvalidated extension payload;
- first/last observed UTC instants, M0 decision reference, created/updated instants.

Unique current identity is `(provider_key, resource_id, capability_id, identity_scheme_version, native_window_key)`. A changed semantic definition creates a higher definition version; it is not silently updated in place.

#### `capacity_budget_definition`

- budget definition ID, account/resource/project/workspace safe scope IDs;
- billing/resource semantic, provider budget key identity scheme/key when approved;
- currency field-state, billing interval semantics, enforcement vocabulary/mapping version;
- aggregation relationship/group policy reference;
- definition version/lifecycle/effective times/M0 decision reference.

Definitions contain no amount, credential, billing contact, invoice, tax data, payment details, or API-key secret.

### 5.2 Immutable observations

#### `capacity_quota_observation`

- observation ID primary business key;
- quota-window definition ID/version and scalar account/resource IDs;
- observation kind and completeness;
- observed/data-through start/end/collected/stored UTC instants;
- provider status safe code and field state;
- provenance row/reference, run ID, payload digest, capability/schema versions;
- provider observation identity scheme/key nullable when approved;
- current-candidate eligibility, invalidation reason nullable, created time.

#### `capacity_quota_measure`

- observation ID plus metric kind (`used`, `remaining`, `limit`, `remaining_ratio`) composite key;
- field state, canonical exact coefficient/scale or ratio representation, unit;
- precision/confidence/value-kind and derivation ID nullable;
- stable reason code nullable.

Database checks require value columns only for `value`, forbid float storage, enforce bounded canonical numeric text/scale, ratio range, required unit, and permitted sign per metric. Cross-field semantic validation remains domain-owned and is repeated before commit.

#### `capacity_budget_observation`

- observation ID, budget definition/version, account/resource/project/workspace scalar IDs;
- observation kind/completeness and billing/data-through interval;
- enforcement status field-state/code;
- observed/collected/stored instants, provenance/run/digest/schema versions;
- current-candidate eligibility/invalidation reason.

#### `capacity_budget_measure`

- observation ID plus metric kind (`current_spend`, `available_spend`, `prepaid_credit`, `soft_limit`, `hard_limit`) composite key;
- field state, exact money representation kind, currency, integer minor units nullable, canonical decimal coefficient/scale nullable;
- precision/confidence/value-kind, derivation ID/reason nullable.

Checks prohibit simultaneous minor-unit and decimal representations, missing currency for a value, float storage, invalid signs, and inconsistent field-state/value columns.

#### `capacity_usage_bucket`

- usage observation/bucket ID, account/resource/project/workspace IDs;
- bucket start/end UTC, provider data-through time, observation/collection/storage times;
- safe grouping dimension set ID and completeness;
- exact request/input-token/output-token/cache/other approved quantity fields through normalized measure rows;
- optional exact cost link when the provider exposes authoritative/reported cost for the same bucket;
- provenance/run/digest/schema/extension references.

#### `capacity_usage_dimension`

- bucket ID, dimension kind, safe opaque dimension ID or approved bounded enum value;
- field state and schema/version;
- composite uniqueness by bucket/dimension kind.

Allowed kinds are frozen per contract. No free-form model name, API key, user email, request body, endpoint payload, or arbitrary provider tag is persisted.

#### `capacity_observation_provenance`

- provenance ID and required CTR-COMMON-004 fields;
- provider/capability/adapter/protocol/source/parser/provider-version data;
- value kind, stability, precision, confidence, Experimental flag, freshness deadline/policy;
- fallback lineage and bounded warning codes;
- derivation method/input-set reference nullable;
- M0 decision reference and correlation/operation IDs.

It contains no documentation URL with secrets, raw warning text, request URL/query, response, stdout/stderr, or provider object. A canonical provenance may be referenced by multiple items in one batch only when every field is truly identical.

#### `capacity_provider_extension_value`

This table exists only if synchronization approves persistence of specific registered extension fields. It stores observation ID, registered schema reference, field key, bounded typed scalar/exact value, and privacy classification. Unknown fields or schema majors are rejected and never stored as opaque JSON. If no V1 consumer needs a field, it is not persisted merely because a provider returns it.

### 5.3 Current and derived projections

#### `capacity_current_projection`

- projection ID and unique projection key for subject/resource/window/budget/metric scope;
- current observation ID/definition version;
- exact field-state/value snapshot only when necessary for bounded queries, with source observation remaining authoritative;
- freshness state/deadline, completeness, conflict state;
- source/registry/policy generations and projection version;
- evaluated/updated UTC instants.

Projection rows are rebuildable and cannot modify observation rows. Any denormalized exact value repeats the same canonical encoding and is verified against the source observation during consistency checks.

#### `capacity_health_projection`

- projection ID, subject/resource scope, normalized state, completeness, freshness;
- constraining window/resource IDs nullable;
- M05 capacity-health classification-policy ID/version and exact classification-boundary representation; no M07 rule or alert-threshold snapshot;
- availability-signal ID/generation nullable;
- input-set/derivation ID, explanation code set, projection version;
- evaluated/valid-until/updated UTC instants.

#### `capacity_aggregate_projection`

- aggregate projection ID, scope kind/ID, registry revision, `as_of` policy bucket;
- health counts, inclusion/completeness counts, worst definitive health;
- numeric aggregate-group references, not a universal total;
- input projection set digest, policy version, projection version, generated time.

Detailed numeric groups are stored in `capacity_aggregate_value` with exact unit/currency/interval/semantic key and omitted-reason counts.

#### `capacity_derivation`

- derivation ID, kind (`ratio`, `health`, `aggregate`, `burn_rate`, `forecast`, `history_bucket`), method ID/version;
- generated/valid-until/invalidated UTC instants and stable invalidation reason;
- exact result type/value when applicable, unit/time basis, precision/confidence/uncertainty classification;
- policy/schema/source generations, canonical input-set digest, explanation codes.

#### `capacity_derivation_input`

- derivation ID, ordinal, observation/projection/availability-event ID and version;
- input role and semantic time;
- uniqueness by derivation/role/reference.

#### `capacity_forecast_projection`

- subject/resource/window/metric unique current key;
- forecast state, current derivation ID, previous derivation ID nullable;
- projection version, updated time.

### 5.4 Commit, availability, events, and retention records

#### `capacity_commit_receipt`

- run ID plus capacity capability composite primary identity;
- payload digest, consumer/module/schema version, receipt version;
- canonical observation ID set digest and stored-at range;
- created UTC instant and conflict flag/reason nullable.

Observation IDs are stored in `capacity_commit_receipt_observation` with deterministic ordinal. The receipt is retained at least as long as M04 can reconcile that run and is exempt from normal purge until M04 confirms terminal retention eligibility.

#### `capacity_availability_signal`

- signal ID/event ID unique, target/subject/resource/capability scope;
- generation/stream sequence, state (`reauthentication_required`, `unavailable`, `blocked`, `recovered`, or synchronized narrower vocabulary);
- occurred/recorded UTC instants, safe reason code, source contract/version;
- invalidated/cleared-by event reference nullable.

No retry, provider error text, credential, or alert state is stored. M05 uses the signal only for capacity truth/freshness/health projection.

#### `capacity_event_outbox` and `capacity_event_delivery`

- event envelope fields, projection-stream key/sequence, event type/schema, allowlisted payload, availability time;
- per-consumer delivery/ack state, attempt count, next attempt, safe last error, timestamps;
- unique event ID and `(event_id, consumer_key)`.

CTR-EVT-TOPOLOGY-001 fixes these as M05-owned tables in the `capacity_*` migration namespace. PLAN-DB supplies reusable claim/delivery persistence mechanics through M05's event-storage port; it owns no central event table. `capacity_event_delivery` tracks producer-side attempts and acknowledgements and is not the consumer's processing receipt. M05 never writes another owner's table directly.

#### `capacity_retention_run`

- retention audit ID, explicit cutoff/as-of, policy version, preview digest;
- optional export checkpoint safe reference, batch count and deleted counts by record class;
- started/completed UTC, result state, safe error code, correlation ID;
- no exported content or path from an untrusted source.

### 5.5 Keys, constraints, and indexes

Planned indexes, validated by real SQLite query plans at representative real volume:

- quota definition unique current native identity and `(account_id, resource_id, lifecycle, definition_id)`;
- quota observations by `(window_definition_id, observed_at DESC, observation_id DESC)`, `(resource_id, stored_at DESC)`, run ID, provider source observation identity, and retention eligibility;
- quota measures by `(observation_id, metric_kind)` and unit/field-state where current queries require it;
- budget definitions by account/resource/project/lifecycle;
- budget observations by `(budget_definition_id, data_through_end DESC, observation_id DESC)`, billing interval, run ID, and retention eligibility;
- usage buckets by `(resource_id, bucket_start, bucket_end, bucket_id)`, project/model-safe dimension lookup, and run ID;
- current projections unique by canonical projection key and indexed by account/resource/freshness/conflict;
- health projections by `(subject_scope_kind, subject_scope_id)`, normalized state/freshness, and updated time;
- aggregate projections by `(scope_kind, scope_id, registry_revision, generated_at DESC)`;
- derivations by subject/kind/generated time and input references by observation ID;
- commit receipts by run/capability and retention eligibility;
- availability by scope/sequence and current uncleared state;
- outbox/delivery by available/delivery state/time;
- retention audit by completed time/status.

All history/list queries are cursor-paginated. Indexes are not accepted from design alone; query plans and measured behavior against real schemas/data are evidence.

### 5.6 Transaction boundaries and repositories

One application use case owns each short transaction:

- commit: validate all typed input before transaction; insert immutable observations/provenance/measures, update affected projections, create derivations/receipt/events/outbox atomically;
- availability signal: deduplicate event/sequence, update matching health projection, and append changed event atomically;
- policy/registry rebuild: read immutable facts, compare expected generations, update bounded projections/events atomically per batch;
- forecast recompute: insert derivation/input rows and swap current forecast projection atomically;
- retention: verify preview/export generation, delete one eligible bounded batch, and record/update audit atomically;
- event delivery: independent short transaction; delivery failure never recollects or changes observations.

Provider calls, M02 scope queries, M04 execution, M07 evaluation, M08 export writing, and API serialization never run inside an M05 database transaction. Repositories are aggregate-specific; no generic repository exposes SQLAlchemy sessions.

### 5.7 Migration sequence, compatibility, and portability

Proposed expand-only sequence, centrally allocated:

1. resource/window/budget definitions, provenance, quota/budget/usage immutable facts;
2. commit receipt/idempotency and current projections;
3. health/aggregate/availability and event outbox;
4. derivation/forecast history and indexes;
5. retention audit and export cursor support.

Every revision records owner M05, requirement IDs, expected row volume, table/index changes, lock/downtime behavior, backup prerequisite, validation query, compatibility range, PostgreSQL notes, and tested recovery. No implicit `create_all` or hidden startup DDL is allowed.

Portability review covers canonical decimal text versus database numeric types, integer ranges, enum/check constraints, UTC precision, partial/unique indexes, upsert/concurrency mapping, JSON avoidance, pagination cursors, and query plans. SQLite-specific implementation stays in the adapter. A destructive contraction requires an ADR, verified backup, consumer migration, and explicit owner approval.

### 5.8 Retention, backup, restore, and consistency

- Ordinary capacity observation/derivation/event history is retained for 365 days.
- Definitions/current projections/current source facts/active receipts/undelivered events remain until safe retirement rules allow deletion.
- M08 invokes M05 preview/export/purge ports; it never queries `capacity_*` tables.
- M08 physical backup contains capacity metadata and is owner-protected even though secrets/content are prohibited.
- Restore readiness invokes `ValidateCapacityConsistencyV1`: foreign-within-module references, canonical exact encodings, projection/source equality, definition versions, receipt observation sets, input derivations, stream sequence, and outbox integrity.
- After restore, provider collection remains paused until schema/consistency and M04 receipt reconciliation pass. Projections may rebuild from restored observations without provider I/O.
- Downgrade is claimed only after real safe execution. Otherwise recovery is verified backup plus prior compatible binary or approved forward fix.

### 5.9 Sensitive and prohibited fields

Allowed storage is limited to operational capacity metadata, exact usage/cost/budget values, safe opaque subject/dimension IDs, provenance, versions, derivations, and safe codes. Prohibited from every capacity row, WAL-derived artifact, event, log, diagnostic, export metadata, and test report:

- passwords, API/OAuth/session tokens, auth headers, cookies, OTP/MFA/recovery values, provider credential/profile contents;
- raw API/CLI/file responses, free-form provider errors, URLs with secret/query data, executable/file paths;
- prompts, responses, tool calls/results, source code, terminal contents, arbitrary process environment values or memory;
- billing contact/payment-card/bank/tax/invoice content and unapproved personal identity;
- unregistered arbitrary provider extension objects or display data not needed for capacity semantics.

## 6. External, provider, API, and UI boundaries

### Provider boundary

M05 performs no provider I/O. A01–A03 map approved real sources into M05-owned provider-input types inside M03 `CollectionOutcomeV1`. M03 proves capability/source/schema/version compatibility; M04 proves admission/run/fencing/deadline; M05 proves capacity semantics and stores the result.

For every provider capability the M0/adaptor handoff must define:

- typed payload version and exact field-state matrix;
- source class, authoritative/value-kind meaning, version scope, credential role, and Experimental state;
- native resource/window/billing identity and any overlap/rollup relationship;
- units/currency, decimal/rounding behavior, provider status mapping, time/reset precision/timezone;
- observation/data-through latency/freshness and reconciliation tolerance;
- safe extension schema and prohibited fields;
- pagination/bucket completeness and stable provider observation identity if any.

An absent or incompatible handoff returns Unsupported/Unknown/Blocked through the owning contracts. It never activates a permissive parser or default mapping.

### M04 commit boundary

M04 routes a validated capacity success/partial outcome to exactly one M05 commit port. M05 does not accept a failed outer outcome as numeric observation input. M04 retains run scheduling/status; M05 returns only the receipt and owns the observation.

If M05 rejects the typed payload, the commit fails with a safe M05 code and M04 records a result-sink/invalid-data failure under synchronized mapping. M05 may record a bounded integrity diagnostic but never persist the rejected raw payload. A timeout after commit is resolved through the receipt status port, not by recollecting or replaying an in-memory payload.

### Registry and aggregation boundary

M05 consumes immutable M02 scope snapshots and resource relationship/version facts. It never stores registry friendly names as identity and never queries registry tables. A stale/unknown scope revision can serve an explicitly stale prior aggregate or fail the aggregate query; it cannot silently include/exclude accounts.

### M07 alert boundary

M05 publishes observation, health, forecast, and availability change events. M07 may query exact M05 views for an authorized alert evaluation but cannot alter observations/health. M05 does not open, acknowledge, snooze, recover, or deduplicate alerts. M05's normalized health policy and M07's alert-threshold policy are separate one-way contracts.

### P01/P02/M08 boundaries

- P01 maps query ports to authorized `/api/v1` resources, pagination, RFC 9457 problems, and OpenAPI; it never queries persistence or recomputes capacity.
- P02 consumes only the generated client and must display source, age, precision, confidence, completeness, uncertainty, input explanation, and Unknown/Unsupported/stale states without placeholder telemetry.
- M08 requests bounded export pages, retention actions, health, and consistency through ports. It does not bypass M05 to read the database.

### Real verification

Live reconciliation follows the runbook: one real collection; exact opaque account/project/resource/window match; nearest provider authoritative UI/command observation; M0-documented latency/rounding tolerance only; reset timezone/precision check; source/version/time/units recorded; owner acknowledgement; no manual DB correction. A mismatch fails and returns capability mapping to discovery/design.

## 7. Security and privacy

### Trust boundaries and controls

| Threat | M05 control | Planned evidence |
|---|---|---|
| Provider value injects malformed/huge number | Typed bounded exact parser, no float, transactional reject | M05-PURE-053..058, M05-SEC-003/004 |
| Missing value becomes zero/available | Explicit field state and completeness, zero requires observed value | M05-PURE-009/018, M05-DB-019 |
| Incompatible pools/windows double-count | Resource semantic/version and aggregation proof | M05-PURE-026..030, M05-DB-022/023 |
| Late/conflicting fact replaces current | semantic ordering and conflict state | M05-PURE-022..025, M05-DB-017/018/020 |
| Raw provider/secret/content persists | allowlisted typed schema; rejected raw payload discarded | M05-SEC-001..003/005 |
| API leaks budgets/account detail | M01 decision + P01 subject disclosure; no direct repository | M05-HTTP-001, M05-SEC-007 |
| Forecast implies false accuracy | sufficient-input gate, method/input IDs, uncertainty, expiry | M05-PURE-031..042, M05-BROWSER-005 |
| Commit replay corrupts history | run+capability+digest receipt and hard conflict | M05-DB-008..010 |
| Purge deletes current/unexported facts | preview digest, protected refs, optional required export checkpoint | M05-DB-027..029/033 |
| Logs/events expose spend or identity | safe IDs/codes/counts; event values omitted | M05-SEC-002/006 |
| Restore revives inconsistent projection | consistency gate and deterministic rebuild | M05-OPS-003/006 |
| Query triggers provider activity | read-only query ports; no adapter imports | M05-ARCH-001/004 |

### Authorization

- Current/history/forecast/budget queries require the synchronized `read:telemetry` permission and P01 scope visibility.
- Exact API cost/budget disclosure remains administrator-only in V1 even though there is one user; future multi-user semantics are preserved by explicit checks.
- Projection rebuild, availability-signal intake, and retention are system-principal operations scoped to exact contracts and generations.
- Export authorization belongs to M08/P01 and obtains records only through an M05 authorized export port.
- No public route creates observations, supplies provider payloads, changes health directly, edits history, or invokes purge without M08 orchestration.

### Input, output, and extension validation

- All lists, strings, decimal sizes/scales, dimension counts, history ranges, bucket counts, extension depth, and serialized payload sizes are bounded.
- Provider extensions must match an exact registered schema major and approved consumer list; unknown fields are rejected.
- Safe model/project/key identifiers remain opaque and bounded. A model display label is not stored unless M0/privacy approve it separately.
- Query filters/sorts are allowlisted; cursors are opaque and authenticated/validated according to P01 contract.
- Derived explanations use stable codes, not concatenated provider content.

### Logging, audit, and incident behavior

Structured logs may contain UTC time, module/event, correlation/run/observation/projection IDs, safe provider/capability/source keys, state/reason, duration, item count, and schema/method versions. They omit values, money, labels, resource external IDs, raw errors, payloads, paths, credentials, and content.

A conflicting receipt, impossible exact encoding, projection/source mismatch, unregistered extension, secret/content finding, or cross-pool double-counting stops the affected integration. Contaminated artifacts are quarantined outside version control, the security incident runbook applies, and no value is manually edited to appear correct.

### Data-minimization proof

Before approval and each schema change, reviewers enumerate every persisted/API/event/log/export field and trace it to an approved requirement/contract. Unused provider fields are discarded. Evidence must inspect the real SQLite database and WAL, logs, HTTP responses, built-browser storage/console, export, diagnostic bundle, backup, and test artifacts after a real live collection.

## 8. Configuration and operations

No key below is approved or may be added to `.env` by this Draft. All proposed M05 settings are non-secret. Final names/defaults/ranges/source/reload semantics require configuration-registry, M07, M08, P01/P02, and root approval.

| Proposed external key/policy | Internal type | Proposed rule | Reload | Consequence |
|---|---|---|---|---|
| `AGENTMONITOR_CAPACITY_HISTORY_RETENTION_DAYS` | positive integer days | V1 fixed/default 365; lower value requires requirement review | controlled config migration/restart | eligible history cutoff |
| `AGENTMONITOR_CAPACITY_RETENTION_BATCH_COUNT` | bounded positive count | measured safe default TBD | restart | purge transaction bound |
| `AGENTMONITOR_CAPACITY_HISTORY_PAGE_MAX_COUNT` | bounded positive count | exact maximum TBD | restart | query response/resource bound |
| `AGENTMONITOR_CAPACITY_HISTORY_RANGE_MAX_DAYS` | bounded days | exact maximum TBD; export may use paging | restart | ordinary history request bound |
| forecast method/policy version | versioned code/runtime policy, not necessarily env | exact method, minimum samples/span, maximum gap/horizon TBD from evidence | explicit policy change + recompute | forecast eligibility/meaning |
| normalized capacity-health classification policy | M05-owned synchronized persisted policy snapshot | classification state priority, constraining-window semantics, and any M05 classification boundaries; never sourced from M07 and excludes M07 alert thresholds | M05-authorized versioned update | health projections/events |
| per-capability freshness policy | M03/M0 evidence, not free env override | cannot be weakened without new evidence | capability-policy generation | stale/current status |
| exact numeric serialization bounds | versioned code policy | fixed secure bounds | application upgrade | input/storage compatibility |

Operator configuration cannot make an Unsupported/Unknown value numeric, merge incompatible pools, widen provider capability scope, weaken source freshness, change currency, or override raw observations.

### Lifecycle and readiness

M05 component states are `starting`, `rebuilding`, `ready`, `degraded`, `read_only`, and `unavailable`.

- Writable readiness requires compatible schema/contracts/policies, repository access, exact representation support, and successful bounded consistency preflight.
- Projection lag/conflict, stale data, one provider capability gap, or unavailable forecast degrades the affected scope but does not make historical reads or unrelated dashboard scopes unavailable.
- Schema incompatibility, commit-receipt inconsistency, or database corruption blocks writes and provider-result commits.
- M05 has no independent polling loop. Retention/rebuild jobs are orchestrated by approved application/M08 scheduling while M05 owns their behavior.

### Health and local measurements

CTR-OPS-006 contribution may expose only safe bounded summaries:

- module/schema/contract/health-policy/forecast-method versions;
- repository and projection-rebuild status;
- latest successful commit/retention times;
- counts of fresh/stale/unknown/conflicted projections by safe category;
- projection/event backlog age/count;
- commit conflicts, consistency failures, retention eligible count/age;
- bounded query/commit/derivation durations and item counts.

It excludes metric/money values, account labels, external IDs, paths, provider payloads, and free-form errors. These are local measurements; no external telemetry or crash reporting exists.

### Operator procedures to document and verify

- inspect why a capacity field is Unknown/Unsupported/stale/conflicted and identify its source/version without exposing secrets;
- compare one real quota/budget observation to provider authority;
- diagnose unit/currency/window/resource mismatch or projection lag;
- rebuild projections from immutable facts after a policy/registry/application upgrade;
- investigate a commit conflict without recollection or data overwrite;
- preview/export/purge expired capacity history safely;
- validate capacity consistency after backup restore;
- handle provider/schema version drift and disable affected capability rather than guess;
- respond to secret/content contamination or inaccurate spend/forecast;
- verify exact-value integrity and application/schema/method versions after upgrade.

Commands remain `TBD` until implemented, included in canonical repository automation, and verified against the real boundary.

### Canonical automation ownership

M05 implementation must register module suites under `AUTO-TEST`, schema/contract/import/exact-value checks under `AUTO-QUALITY`, its migration revisions under `AUTO-MIGRATE`, and retention/restore validations under the M08-owned `AUTO-BACKUP`/`AUTO-RESTORE` workflows. No personal shell sequence counts. Each command must fail closed, preserve Passed/Failed/Blocked/Not Run, and never read the operator `.env` or provider profile outside its approved live checkpoint.

## 9. Test design before implementation

No scenario in this inventory is implemented or Passed by this plan. Each future behavior begins with a meaningful failing test after the approved toolchain works. A missing package, syntax error, unavailable credential, or broken setup is not Red evidence.

### Test-data and evidence integrity

- T1 pure tests may construct clearly labeled domain examples for exact arithmetic, state policy, aggregation, forecast, time, and retention calculations. They perform no filesystem, database, network, environment, clock, provider, or subprocess I/O and accept `as_of` explicitly.
- T2 persistence tests use a real temporary SQLite file, the full real Alembic chain, and production repositories. Empty-schema/mechanism tests need no telemetry. Any test asserting observation persistence/projection/history uses a freshly collected real provider observation in that run or an owner-approved copy of a real AgentMonitor database; it never inserts invented/seeded telemetry.
- A real observation is not converted into a committed fixture or replay. Sanitized evidence may record metadata/results but cannot feed another test as a provider substitute.
- Edge conditions that cannot be obtained naturally at the required real boundary remain Blocked there. The corresponding pure policy test does not turn that DB/live scenario into Passed.
- T3 starts the production FastAPI service on an ephemeral loopback port with real IAM and real SQLite. Provider-backed responses originate from real committed observations.
- T4 builds the production frontend and drives a real supported browser against the real service/database. No sample account or placeholder metric is allowed.
- T6 uses current production adapters and owner-controlled real accounts. The owner handles provider UI/login and authoritative comparison. Dynamic values are never hardcoded.
- Retention deletion at 365 days uses naturally aged real capacity history or a live provider's authoritative historic data. Backdating, patching clocks, changing the machine clock, or seeding old rows is prohibited; the DB deletion scenario remains Blocked until valid data exists.
- All logs, screenshots, traces, videos, HTTP captures, reports, databases, backups, exports, and evidence are allowlist-sanitized and secret/content scanned.
- Each result is Passed, Failed, Blocked, or Not Run. An aggregate gate cannot hide the latter three.

### 9.1 Pure domain and contract scenarios (T1)

| Test ID | Requirement | Meaningful initial Red expected | Pass condition | Reviewer |
|---|---|---|---|---|
| M05-PURE-001 | FR-QUOTA-001 | Two native windows collapse by label | Distinct approved native identities remain separate | M05/M0 |
| M05-PURE-002 | FR-QUOTA-001 | Window reset is inferred from period end | Start/end/reset remain independent field states | M05 |
| M05-PURE-003 | FR-QUOTA-001 | Renamed label changes identity | Mutable safe label does not change window identity | M02/M05 |
| M05-PURE-004 | FR-QUOTA-001 | Unknown window key is heuristically merged | Unknown identity blocks current projection | test integrity |
| M05-PURE-005 | FR-QUOTA-001 | Partial scope retires omitted window | Only approved complete-scope absence can change lifecycle | M03/M05 |
| M05-PURE-006 | FR-QUOTA-002 | Unknown extension field is retained | Only registered allowlisted schema fields survive | M03/security |
| M05-PURE-007 | FR-QUOTA-002 | Incompatible window percentages become a total | No cross-window numeric total is produced | M05/UI |
| M05-PURE-008 | FR-COL-004 | Observation without required provenance validates | Missing source/version/time/precision/confidence is rejected | M03/M05 |
| M05-PURE-009 | FR-COL-006 | Unknown/Unsupported/Unavailable/zero collapse | Every state remains distinct | M03/M04/UI |
| M05-PURE-010 | FR-BUDGET-006 | One absent field marks capability Unsupported | Unsupported requires matching evidence decision | M0/M03 |
| M05-PURE-011 | FR-QUOTA-004 | Derived ratio inherits provider-reported kind | Derivation gets method/input IDs and derived provenance | M05 |
| M05-PURE-012 | FR-QUOTA-004 | Freshness deadline equality is current | Equality is stale; Unknown policy is freshness_unknown | M05 |
| M05-PURE-013 | FR-QUOTA-004 | Failed run extends freshness | No failure/cached value advances observation deadline | M04/M05 |
| M05-PURE-014 | FR-QUOTA-003 | Known zero remaining maps Available | Exact evidenced zero maps Exhausted | M05 |
| M05-PURE-015 | FR-QUOTA-003 | Lowest ratio window is not constraining | Worst compatible constraining window is referenced | M05 |
| M05-PURE-016 | FR-QUOTA-003 | Auth-required signal loses to old quota | Matching current auth requirement has precedence | M04/M07 |
| M05-PURE-017 | FR-QUOTA-003 | Stale recovery clears newer auth block | Only matching/newer verified generation clears it | M04/M05 |
| M05-PURE-018 | FR-QUOTA-003 | Available plus unknown window yields Available | Aggregate becomes Unknown/incomplete, not falsely Available | M05/UI |
| M05-PURE-019 | FR-QUOTA-003 | Critical known plus unknown becomes Unknown only | Critical remains visible with partial completeness | M05/M07 |
| M05-PURE-020 | FR-QUOTA-003 | Contradictory provider status silently wins | Conflict is explicit and policy does not guess | M0/M05 |
| M05-PURE-021 | FR-QUOTA-003 | M05 classification-boundary equality/precedence is inconsistent | Approved exact classification boundary and M05 policy version are deterministic; M07 thresholds are absent | M05; M07 consumer review |
| M05-PURE-022 | NFR-RES-001 | Late older fact replaces current | Semantic time ordering retains it as history only | M05 |
| M05-PURE-023 | FR-COL-008 | Failed input produces zero observation | No observation/current update occurs | M04/M05 |
| M05-PURE-024 | NFR-RES-001 | Equal semantic time conflict picks insertion order | Projection becomes conflicted; no arbitrary winner | M05 |
| M05-PURE-025 | NFR-COMP-001 | Definition/schema change rewrites old meaning | Old observations retain original definition/version | contract reviewer |
| M05-PURE-026 | FR-ORG-003 | Scope includes duplicate account/resource | Each scalar subject appears once | M02/M05 |
| M05-PURE-027 | FR-BUDGET-005 | Subscription and API pools merge | Pools remain separate | M02/M05 |
| M05-PURE-028 | FR-ORG-003 | Parent rollup and child are double-counted | Rollup overlap omits numeric total with reason | M02/M05 |
| M05-PURE-029 | FR-ORG-003 | Mixed currencies/units sum | Numeric group absent; separate inventories remain | M05 |
| M05-PURE-030 | FR-ORG-003 | Unknown relationship defaults additive | Unknown blocks numeric aggregation | M02/M05 |
| M05-PURE-031 | FR-QUOTA-005 | Forecast accepts mixed windows/units | Method rejects incompatible series | M05 |
| M05-PURE-032 | FR-QUOTA-005 | Too few points produces estimate | `insufficient_input` with reason | M05 |
| M05-PURE-033 | FR-QUOTA-005 | Too-short span produces false precision | Insufficient span blocks forecast | M05 |
| M05-PURE-034 | FR-QUOTA-005 | Reset appears as negative burn | Reset splits the series | M05 |
| M05-PURE-035 | FR-QUOTA-005 | Correction/refund is silently clamped | Evidenced segment or insufficient/conflict result | M05 |
| M05-PURE-036 | FR-QUOTA-005 | Flat use predicts arbitrary exhaustion | No exhaustion estimate; typed reason | M05 |
| M05-PURE-037 | FR-QUOTA-005 | Stale current remaining supports forecast | Forecast is stale/insufficient | M05 |
| M05-PURE-038 | FR-QUOTA-005 | Excessive observation gap is ignored | Approved gap limit invalidates segment | M05 |
| M05-PURE-039 | FR-QUOTA-005 | Provider rounding is treated exact | Uncertainty reflects input precision | M05/M0 |
| M05-PURE-040 | FR-QUOTA-005 | Reset-before-exhaustion is hidden | Relationship is explicit/Unknown | M05/UI |
| M05-PURE-041 | FR-QUOTA-005 | New input leaves old forecast current | Canonical input generation invalidates/recomputes | M05 |
| M05-PURE-042 | AC-UI-006 | Forecast lacks explanation/input IDs | Method/version/inputs/uncertainty are complete | P02/M07 |
| M05-PURE-043 | FR-BUDGET-002 | Available spend inferred from absent limit | Field remains Unknown | M05 |
| M05-PURE-044 | FR-BUDGET-002 | Soft and hard limits collapse | Separate field states/enforcement remain | M05 |
| M05-PURE-045 | FR-BUDGET-002 | Credit equals budget or negative spend | Semantics remain distinct and validation applies | M0/M05 |
| M05-PURE-046 | FR-BUDGET-002 | Billing reset inferred from collection time | Only provider/evidenced reset is represented | M05 |
| M05-PURE-047 | FR-BUDGET-002 | Derived available spend is provider-reported | Derived kind/equation/input IDs are exposed | M05 |
| M05-PURE-048 | FR-BUDGET-002 | Mixed billing intervals compare as one budget | Incompatible intervals remain separate | M05 |
| M05-PURE-049 | FR-BUDGET-003 | Unsupported dimension emits `unknown` row | Capability state is shown; no invented bucket | M03/M05 |
| M05-PURE-050 | FR-BUDGET-003 | Key identifier accepts secret/reversible value | Only approved safe opaque/key-prefix form passes | security/M0 |
| M05-PURE-051 | FR-BUDGET-003 | Overlapping group buckets sum twice | Completeness/rollup semantics prevent double-counting | M05 |
| M05-PURE-052 | FR-BUDGET-003 | Arbitrary provider tag enters dimension map | Closed vocabulary rejects it | M03/security |
| M05-PURE-053 | FR-BUDGET-004 | Binary float is accepted | Float input is rejected at contract boundary | M05 |
| M05-PURE-054 | FR-BUDGET-004 | Canonically equal decimals compare unequal | Exact canonicalization preserves equality | M05 |
| M05-PURE-055 | FR-BUDGET-004 | Scale/precision overflow is accepted | Bounded representation rejects it | security |
| M05-PURE-056 | FR-BUDGET-004 | Different currencies add | Arithmetic returns incompatible-currency outcome | M05 |
| M05-PURE-057 | FR-BUDGET-004 | Minor-unit exponent is guessed | Currency representation requires approved exponent/evidence | M0/M05 |
| M05-PURE-058 | FR-BUDGET-004 | Rounding occurs silently | Versioned mode records exact pre/post semantics | M05/API |
| M05-PURE-059 | FR-HIST-001/003 | Retention cutoff deletes boundary/current fact | Exact cutoff and protected-reference rules hold | M08/M05 |
| M05-PURE-060 | FR-HIST-002 | Bucket mixes native window IDs | Query rejects incompatible series | M05 |
| M05-PURE-061 | FR-HIST-002 | UTC bucket boundaries vary by host timezone | Explicit UTC yields deterministic boundaries | M05 |
| M05-PURE-062 | FR-HIST-002 | Cumulative metric is summed incorrectly | Only approved metric-specific bucket method is allowed | M05 |
| M05-PURE-063 | FR-HIST-002 | Raw/provider/derived series are conflated | Series kind and method remain explicit | M05/P02 |
| M05-PURE-064 | FR-HIST-002 | Cursor ordering duplicates/skips equal times | Time+opaque ID order is stable | persistence |
| M05-PURE-065 | FR-HIST-003 | Purge preview digest ignores protected refs | Generation/digest changes before unsafe purge | M08/M05 |
| M05-PURE-066 | FR-HIST-005 | Naive/local instant enters domain | Non-aware/non-UTC persistence input is rejected | M05 |

### 9.2 Real SQLite, migration, event, and application scenarios (T2/T6 where data is required)

| Test ID | Requirement | Real dependencies | Meaningful initial Red expected | Pass condition | Coordination/status rule |
|---|---|---|---|---|---|
| M05-DB-001 | AC-V1-004 | Real file SQLite/full Alembic chain | M05 schema absent/incompatible | Fresh and supported upgrade paths validate | Persistence; empty DB allowed |
| M05-DB-002 | FR-QUOTA-001 | Fresh real quota collection + production commit | Window definition/observation not persisted | Exact real native window is stored/queryable | Owner/T6 |
| M05-DB-003 | FR-QUOTA-001 | Fresh real multi-window account if available | Windows overwrite each other | Each evidenced window remains independent | Blocked if source exposes one only |
| M05-DB-004 | FR-QUOTA-001 | Two real collections | History/current ordering wrong | Both immutable; current is semantically newest | Owner/T6 |
| M05-DB-005 | FR-QUOTA-001 | Real reset/renewal field if exposed | Precision/timezone is lost | DB round trip matches source semantics | Blocked if unavailable |
| M05-DB-006 | FR-QUOTA-001 | Real partial outcome if naturally available | Omitted window is retired/zeroed | Existing window remains; partial recorded | Blocked until natural/real partial |
| M05-DB-007 | FR-QUOTA-002 | Real approved provider extension | Extension raw/unknown field persists | Only registered typed field persists | Blocked if none approved |
| M05-DB-008 | FR-COL-004/CTR-CAP-004 | Fresh real outcome committed twice | Duplicate rows/events are created | Same run/digest returns identical receipt | M04/M05/T6 |
| M05-DB-009 | CTR-CAP-004 | Two distinct fresh real outcomes under controlled reconciliation | Different digest for same run overwrites | Hard conflict preserves first commit | Owner; no fabricated payload |
| M05-DB-010 | CTR-CAP-004 | Real concurrent production commit calls | Race creates duplicate observation/projection versions | One receipt/commit wins idempotently | M04/persistence |
| M05-DB-011 | FR-BUDGET-001/002 | Fresh real API budget/cost collection | Exact fields fail round trip | Real source fields/states persist exactly | Owner/T6 |
| M05-DB-012 | FR-BUDGET-002 | Real provider budget with exposed limits/credits | Limit/credit/enforcement semantics collapse | Separate exact states survive | Blocked per unsupported fields |
| M05-DB-013 | FR-BUDGET-003 | Real provider grouped usage | Dimensions/buckets lose scope | Approved dimensions and completeness persist | Owner/T6 |
| M05-DB-014 | FR-BUDGET-003 | Real pagination/multiple provider buckets | Page overlap duplicates source fact | Approved provider IDs/dedupe preserve facts | Blocked if no stable identity |
| M05-DB-015 | FR-BUDGET-003 | Real unsupported/withheld dimension state | Missing becomes zero row | Capability/field state remains explicit | Owner/M0 |
| M05-DB-016 | FR-BUDGET-004 | Real exact money/quantity through DB | SQLite coercion/float changes value | Byte-for-semantic exact round trip passes | Persistence/security |
| M05-DB-017 | FR-QUOTA-003 | Fresh real capacity plus approved policy | Health projection absent/wrong ref | State, constraining window, inputs/version stored | M05/M07 |
| M05-DB-018 | NFR-RES-001 | Naturally conflicting real facts, if observed | Conflict picks last writer | Explicit conflict and prior fact retained | Blocked until real condition |
| M05-DB-019 | FR-COL-006/008 | Real failed run after prior successful observation | Failure creates/freshens observation | No new observation; prior view becomes stale by policy | M04/owner |
| M05-DB-020 | NFR-RES-001 | Real malformed typed result from changed production adapter | Bad item partially corrupts DB | Commit rejects atomically; other accounts query | No constructed adapter; Blocked until real |
| M05-DB-021 | NFR-RES-001 | Real isolated DB lock/permission failure | Failure corrupts projection or service | Typed unavailable; unrelated read path remains safe | Approved isolated resource |
| M05-DB-022 | FR-ORG-003/BUDGET-005 | Real M02 scope/resources + real observations | Pool/account counted twice | Scope aggregate counts each once | M02/M05/T6 |
| M05-DB-023 | FR-ORG-003 | Real parent/child or mixed pools when present | Numeric aggregation double-counts/mixes | Only approved groups aggregate; reasons persist | Blocked if topology unavailable |
| M05-DB-024 | FR-QUOTA-005 | Naturally accumulated real series | Forecast/derivation cannot reproduce | Stored method/input set reproduces exact result | Requires sufficient live history |
| M05-DB-025 | FR-QUOTA-005 | Real new observation/reset | Old forecast remains current | Invalidation/current swap is atomic | Blocked until sufficient condition |
| M05-DB-026 | FR-QUOTA-005 | Real projection failure/restart | Observation rolls back or duplicates | Fact commits once; derivation recovers from DB | Operations/M05 |
| M05-DB-027 | FR-HIST-001/003 | Naturally aged real capacity DB | Eligible rows remain | 365-day rows purge in bounded transaction | Blocked until valid aged data |
| M05-DB-028 | FR-HIST-003 | Aged real DB with current/protected refs | Purge deletes current/receipt/event input | Protected facts remain; only eligible removed | Blocked until valid data |
| M05-DB-029 | FR-HIST-003 | Aged real DB + concurrent real collection | Purge blocks/corrupts new commit | Bounded transactions coexist safely | Blocked until aged data |
| M05-DB-030 | FR-HIST-002 | Real retained observation series | History ordering/page is unstable | Deterministic cursor returns each point once | Owner/T6 |
| M05-DB-031 | FR-HIST-002 | Real series/query plan | History performs unbounded/full unrelated scan | Approved index/bounds used | Persistence/performance |
| M05-DB-032 | FR-HIST-002 | Real provider history plus poll snapshots | Series kinds/buckets conflate | Raw/provider/derived paths remain explicit | Owner/T6 |
| M05-DB-033 | FR-HIST-004 | Real M08 export over real capacity history | Export bypasses port/misses exact semantics | Bounded machine-readable export reconciles to views | M08/security |
| M05-DB-034 | FR-HIST-005 | Fresh real observation across DB restart | Timestamp loses UTC/precision | Exact contract round trip passes | Persistence |
| M05-DB-035 | NFR-RES-001 | Real outbox consumer unavailable | Commit/query blocks or event is lost | Commit durable; consumer backlog isolated/retried | M07/M08 |
| M05-DB-036 | NFR-COMP-001 | Real supported prior DB with capacity data | Migration changes exact meaning or cannot recover | Upgrade validates; rollback/recovery truthful | Operations/persistence |

### 9.3 Real HTTP and built-browser scenarios (T3/T4)

| Test ID | Layer | Requirement | Real dependencies | Initial Red expected | Pass condition | Coordination |
|---|---|---|---|---|---|---|
| M05-HTTP-001 | T3 | NFR-API-001/SEC | Real server/IAM/DB | Unauthorized telemetry/budget is disclosed | Explicit permission and subject scope enforced | M01/P01 |
| M05-HTTP-002 | T3+T6 | FR-QUOTA-001/004 | Real committed quota | Schema omits native/provenance/freshness fields | Exact real view conforms to OpenAPI | Owner/P01 |
| M05-HTTP-003 | T3+T6 | FR-BUDGET-002 | Real committed budget | Money/field states serialize ambiguously | Exact string/minor-unit/currency schema reconciles | Owner/P01 |
| M05-HTTP-004 | T3+T6 | FR-BUDGET-003 | Real breakdowns | Unsupported dimensions appear as zeros | Real supported buckets only; capability state explicit | Owner/P01 |
| M05-HTTP-005 | T3+T6 | FR-ORG-003 | Real M02 scope/capacity | Global/org response double-counts | Counts/groups reconcile to child views | M02/P01 |
| M05-HTTP-006 | T3+T6 | FR-QUOTA-005 | Real sufficient/insufficient series | API invents estimate or hides uncertainty | Correct union/method/inputs/uncertainty | P01/M05 |
| M05-HTTP-007 | T3 | FR-BUDGET-004 | Real exact value in DB | JSON number loses exactness | Contract representation round-trips exactly | P01 |
| M05-HTTP-008 | T3+T6 | FR-COL-006/008 | Real stale/unsupported/failed state | Response reports current/zero/generic null | Distinct actionable state and last-known age | M04/P01 |
| M05-HTTP-009 | T3+T6 | FR-HIST-002 | Real history | Unbounded/mixed series response | Cursor/range/bucket/unit constraints hold | P01 |
| M05-HTTP-010 | T3 | FR-SAFE-002 | Real OpenAPI/server | Capacity route exposes ingestion/control/provider call | Only approved read/resource operations exist | Security/P01 |
| M05-BROWSER-001 | T4+T6 | FR-QUOTA-004/AC-UI-006 | Built UI, real quota | Source/age/precision/confidence hidden | Explanation is accessible without placeholder | P02/owner |
| M05-BROWSER-002 | T4+T6 | FR-HIST-002/AC-HIST-001 | Real history end-to-end | Chart invents points or lacks table | Real series/chart/table reconcile exactly | P02/owner |
| M05-BROWSER-003 | T4+T6 | FR-ORG-003/BUDGET-005 | Real organizations/pools | UI shows misleading grand total | Pools/groups/completeness remain separate | P02/M02 |
| M05-BROWSER-004 | T4 | FR-HIST-005/AC-UI-003/004 | Built UI, real data, configured timezone/viewports | Time/meaning lost responsively or by color | UTC-derived local rendering and accessible cues pass | P02 |
| M05-BROWSER-005 | T4+T6 | FR-QUOTA-005/AC-UI-005/006 | Real forecast or insufficient state | UI hides uncertainty or fabricates gauge | Estimate/range/reasons/inputs visible truthfully | P02/M07 |

### 9.4 Contract, live-provider, reconciliation, and failure scenarios

| Test ID | Layer | Requirement | Real dependencies | Initial Red expected | Pass condition | Owner coordination |
|---|---|---|---|---|---|---|
| M05-CONTRACT-001 | Contract/T6 | FR-QUOTA-006 | Real Claude adapter/source/M0 row | Payload differs from M05 schema/meaning | Exact supported fields map; gaps explicit | Owner/A01 |
| M05-CONTRACT-002 | Contract/T6 | FR-QUOTA-006 | Real Codex adapter/source/M0 row | Same | Exact supported fields map; gaps explicit | Owner/A02 |
| M05-CONTRACT-003 | Contract/T6 | FR-QUOTA-006/BUDGET-006 | Real Ollama/cloud/API source/M0 row | Local/cloud/API semantics collapse | Each proven resource/capability maps separately | Owner/A03 |
| M05-CONTRACT-004 | Contract/T6 | FR-COL-004 | Each supported production adapter | Required provenance omitted/misclassified | M03 envelope and M05 payload validate end to end | Owner/adapters |
| M05-LIVE-001 | T6 | FR-QUOTA-001 | Real Claude account/source | Window/value/unit mismatch | AgentMonitor reconciles within documented tolerance | Owner/A01 |
| M05-LIVE-002 | T6 | FR-QUOTA-001 | Real Codex account/source | Same | Same, for exact verified Codex tuple | Owner/A02 |
| M05-LIVE-003 | T6 | FR-QUOTA-001 | Real Ollama product/source if supported | Same/local-cloud conflation | Exact supported scope reconciles or Unsupported evidenced | Owner/A03 |
| M05-LIVE-004 | T6 | FR-QUOTA-002 | Real provider-specific safe field | Field lost/leaks raw payload | Registered field visible with schema/provenance only | Owner/security |
| M05-LIVE-005 | T6 | FR-QUOTA-003 | Real naturally available capacity states | Normalized state/constraining window wrong | State reconciles to real inputs/policy | Owner; rare states Blocked |
| M05-LIVE-006 | T6 | FR-QUOTA-005 | Real accumulated usage | Burn/forecast contradicts observations/tolerance | Inputs/math/uncertainty reconcile | Owner; insufficient stays valid outcome |
| M05-LIVE-007 | T6 | FR-BUDGET-001 | Real Anthropic billing account/source | Scope/usage/cost mismatch | Exact supported values reconcile | Owner/API admin role |
| M05-LIVE-008 | T6 | FR-BUDGET-001/002 | Real OpenAI billing account/source | Scope/spend/budget mismatch | Exact supported values reconcile | Owner/API admin role |
| M05-LIVE-009 | T6 | FR-BUDGET-001/002 | Real Ollama API/cloud billing source | Unsupported data is inferred | Reconciles if Supported; otherwise evidenced Unsupported | Owner/A03 |
| M05-LIVE-010 | T6 | FR-BUDGET-003 | Real provider project/model grouping | Breakdown labels/totals mismatch | Same scope/time/group reconciles | Owner |
| M05-LIVE-011 | T6 | FR-BUDGET-003 | Real safe API-key dimension if exposed | Secret/key or wrong grouping leaks | Only approved safe ID and exact bucket appear | Owner/security; Blocked if absent |
| M05-LIVE-012 | T6 | FR-BUDGET-006/COL-006 | Real unsupported/unverified tuple | Value is invented or old value current | Explicit capability/current state | Owner/M03 |
| M05-LIVE-013 | T6 integration | NFR-RES-001/AC-OPS-003 | One real failed capacity source and healthy source | Failure corrupts/stops healthy capacity/API | Healthy source and queries continue | Natural/safe failure only |
| M05-LIVE-014 | T6 end-to-end | AC-HIST-001 | Real provider -> M03 -> M04 -> M05 -> P01 -> P02 | Link/source/history/chart mismatch | One observation reconciles through full path | All vertical owners/owner |

### 9.5 Architecture, security, operations, performance, and documentation scenarios

| Test ID | Layer | Requirement | Real dependencies | Initial Red expected | Pass condition | Reviewer |
|---|---|---|---|---|---|---|
| M05-ARCH-001 | Static/source | NFR-ARCH-001 | Real repository/checker | Forbidden framework/provider/private import passes | Boundary gate rejects it; clean graph passes | Architecture |
| M05-ARCH-002 | Contract | NFR-ARCH-002/COMP | Real contract catalog | DTO/version/owner/consumer unresolved | Exactly one owner and compatible version | Integration |
| M05-ARCH-003 | Event/schema | NFR-COMP-001 | Real schemas/generator | Breaking semantic change is unclassified | Compatibility gate blocks it | Contract reviewer |
| M05-ARCH-004 | Surface review | FR-SAFE-002 | Real code/OpenAPI | Provider/process control or direct collection exists | No prohibited operation/import | Security |
| M05-ARCH-005 | Platform | NFR-PLAT-001 | Real source plus Linux/macOS gates | Capacity core imports OS behavior | Core is neutral; macOS status truthful | Platform |
| M05-SEC-001 | Artifact | NFR-PRIV-001 | Real DB/WAL after live run | Prohibited raw/content/credential data persists | Allowlisted fields only | Security |
| M05-SEC-002 | Logs | NFR-OBS-001 | Real success/failure logs | Values/money/identity/raw error appears | Safe codes/IDs/counts only | Security |
| M05-SEC-003 | Extension | FR-QUOTA-002 | Real approved adapter extension | Unknown/unbounded field crosses boundary | Exact registered schema only | M03/security |
| M05-SEC-004 | Exact values | FR-BUDGET-004 | Real DB/API/export | Float/coercion/rounding changes value | End-to-end exact reconciliation | Security/persistence |
| M05-SEC-005 | Export/backup | FR-OPS-005 | Real export/backup after live run | Secret/content/raw provider data included | Scans clean; exact allowed data only | M08/security |
| M05-SEC-006 | Events | NFR-PRIV-001 | Real outbox/delivery | Numeric/account label/raw values emitted | Event allowlist only | M07/M08/security |
| M05-SEC-007 | HTTP/browser | NFR-SEC-001 | Real server/browser | Unauthorized budget or IDs leak | Permission/scope/browser-storage checks pass | M01/P01/P02 |
| M05-SEC-008 | Surface | FR-SAFE-002 | Real source/contracts | M05 can call provider/control agent | Absence proven | Security |
| M05-SEC-009 | Network/privacy | NFR-PRIV-002 | Real process/browser/dependency traffic | Analytics/crash telemetry emitted | No external product telemetry | Privacy |
| M05-SEC-010 | Evidence | AC-V1-007/008 | Actual test/build artifacts | Secret or simulated telemetry claim present | Scan/review clean; states truthful | Test/security |
| M05-OPS-001 | T7 health | FR-OPS-002 | Real service/DB | M05 reports healthy while repository/projection failed | Truthful bounded degradation | M08 |
| M05-OPS-002 | T7 diagnostics | FR-OPS-002/006 | Real diagnostics | Versions/methods absent or metric values leak | Safe exact versions/states present | M08/security |
| M05-OPS-003 | T7 restore | AC-OPS-004 | Real verified backup/isolated restore | Projection/receipt inconsistency missed | Consistency and startup pass or fail closed | M08/owner |
| M05-OPS-004 | T7 retention | FR-HIST-003 | Real naturally aged DB | Routine deletes unsafe rows/hides status | Canonical purge reports exact truthful result | M08; Blocked until data |
| M05-OPS-005 | T7 export | FR-HIST-004 | Real live history | Export cannot precede deletion/reconcile | Exact bounded export/checkpoint passes | M08 |
| M05-OPS-006 | T7 rebuild | AC-OPS-005 | Real service/DB | Rebuild changes immutable facts/results | Deterministic projections reconcile | Operations |
| M05-OPS-007 | T7 upgrade | AC-OPS-005 | Real prior/current install | Upgrade loses exact values/history | Migration/post-check or recovery passes | Operations |
| M05-OPS-008 | T5/T7 | NFR-PLAT-001 | Real Linux; real macOS if available | OS leakage prevents portability | Linux passes; macOS Passed or visible Blocked | Platform |
| M05-OPS-009 | T7 isolation | NFR-RES-001 | Real service and safe component failure | M05 failure takes dashboard/other modules down | Degraded capacity only; unrelated API alive | Integration |
| M05-OPS-010 | T7 backup | AC-OPS-004 | Real DB/checksum/integrity/restore | Backup excludes/corrupts M05 schema/data | Restored exact capacity passes consistency | M08 |
| M05-PERF-001 | T2 | NFR-PERF-001 | Real DB/current projections for real accounts | Current query scans history | Indexed bounded plan/latency passes approved budget | Performance |
| M05-PERF-002 | T2 | NFR-PERF-001 | Real accumulated observation history | History query exceeds budget/unbounded | Indexed cursor query passes | Blocked until volume exists |
| M05-PERF-003 | T2/T6 | NFR-PERF-001 | Real live concurrent commits | SQLite contention loses/duplicates facts | Safe measured commit throughput | Owner/persistence |
| M05-PERF-004 | T2 | NFR-PERF-001 | Real organization/resource graph and observations | Aggregate needs redesign/double-counts | Bounded recompute/query meets budget | Performance |
| M05-PERF-005 | T2 | system target | Real retained volume toward five-million target | Storage/query plan cannot scale | Measured result meets approved budget or design revised | No generated telemetry; Blocked until real volume |
| M05-DOC-001 | Docs | NFR-DOC-001 | Real documentation tree/gate | Broken links/IDs/status/commands pass | Canonical docs gate passes | Docs/integration |
| M05-DOC-002 | Traceability | AC-V1-001/002 | Real plan/contracts/evidence registry | Requirement/test/evidence gap hidden | Every scoped ID maps truthfully | Integration |
| M05-DEP-001 | Dependency | NFR-LIC-001 | Actual manifests/locks/SBOM | Unadmitted package enters graph | Every dependency approved/traced | Dependency reviewer |
| M05-DEP-002 | License/security | AC-V1-005 | Actual locked graph/advisories/notices | Blocking license/vulnerability hidden | No unresolved blocker; notices current | Owner/security |

### 9.6 Mutation, coverage, failure, and recovery gates

- Proposed mutation target: 100% of non-equivalent mutants for exact quantity/money operations, field-state transitions, current selection, normalized health, aggregation eligibility, forecast sufficiency/segmentation, and retention eligibility. Equivalent mutants require independent written classification; exclusions cannot hide a branch.
- Every documented branch of the above critical pure policies has a meaningful assertion. Coverage is diagnostic only.
- Real-boundary coverage includes malformed provider input only when a real production adapter/provider produces it; otherwise pure validation proves policy and the T6/T2 scenario remains Blocked.
- Restart points cover before commit, after observation insert but before transaction commit, after committed receipt before M04 acknowledgement, projection rebuild, outbox backlog, retention batch, migration, backup, and restore through real processes/SQLite where safe.
- No auto-retry turns a failure green. Flaky live results are defects or Blocked with evidence.

## 10. Implementation increments

Implementation starts only after section 15 is fully satisfied, the plan status is Approved, the synchronized planning gate passes for its claimed stage, and the root assigns non-overlapping files. Every behavioral increment records Red, Green, and post-refactor evidence using canonical automation.

| Increment | Owned files/area | Failing test first | Minimum production change | Refactor/documentation | Exit evidence |
|---|---|---|---|---|---|
| M05-I00 — evidence and contract freeze | M0 handoff/contract decisions only; root-owned shared files separately | M05-CONTRACT-001..004 remain Not Run until adapters exist; schema review checks | Freeze exact common quantity/provenance, capacity input/view/event/commit schemas and decisions | Contract register/traceability/ADR as needed | Approved versions and consumer signatures; no production code |
| M05-I01 — pure exact values/field states | M05 domain value objects | M05-PURE-008..013, 043..058, 066 | Exact quantity/money/ratio, field states, provenance/freshness validation | Domain invariants and structural examples | Meaningful pure R/G/R; mutation gate for delivered branches |
| M05-I02 — native window/resource model | M05 domain | M05-PURE-001..007, 026..030 | Window identity/lifecycle and pool/aggregation semantics | Resource/window decision docs | Pure R/G/R and M02/M03 review |
| M05-I03 — health/current policies | M05 domain | M05-PURE-014..025 | Current selection, freshness, availability generation, normalized health | State/precedence/explanation docs | Pure R/G/R, M04 input review, and M07 consumer review; no reverse policy input |
| M05-I04 — forecast/history policies | M05 domain | M05-PURE-031..042, 059..065 | Sufficient-input, segmentation, uncertainty, history buckets, retention eligibility | Method/limits/known limitations | Pure R/G/R and mutation evidence |
| M05-I05 — immutable schema/repositories | M05 persistence adapter + allocated migrations | M05-DB-001/016/034/036; observation tests wait for live input | Definitions, provenance, observation/measure/usage tables and repositories | DDL/portability/migration notes | Real empty DB migration plus exact real-value round trip when live input exists |
| M05-I06 — commit/receipt | M05 application/persistence | M05-DB-002/008..010 | Capacity commit/status, immutable observations, receipt/idempotency/conflict | CTR-COL-006/M03 handoff docs | Real provider result through production commit; no seeded telemetry |
| M05-I07 — current/health projection | M05 application/persistence | M05-DB-003..007/017..021 | Current selection, freshness, availability, health, projection rebuild | Health/consistency docs | Real SQLite/application evidence; naturally unavailable edges remain Blocked |
| M05-I08 — aggregation | M05 application/persistence | M05-DB-022/023 | M02 scope snapshot and compatible group aggregation | Double-count/omission explanation docs | Real registry/resource/observation evidence |
| M05-I09 — usage/budget | M05 application/persistence | M05-DB-011..015 | Exact API usage/cost/budget/credit persistence/current views | Provider capability limitations | One real approved API source vertical slice |
| M05-I10 — forecast/history | M05 application/persistence | M05-DB-024..026/030..032 | Derivations, forecast current/history, bounded series/buckets | Method/version/runbook docs | Real accumulated history; insufficient state is valid, not a pass for estimate |
| M05-I11 — events/retention/export | M05 application/persistence | M05-DB-027..029/033/035 | Outbox/delivery, retention preview/purge/audit, export/consistency ports | M07/M08 handoff/runbooks | Real event path; retention deletion stays Blocked until real aged data |
| M05-I12 — P01 API integration | Separately assigned P01/OpenAPI/generated artifacts | M05-HTTP-001..010 | Authorized current/aggregate/history/forecast resources/problems | Generated API guidance/compatibility report | Real server/SQLite/OpenAPI/client evidence |
| M05-I13 — P02 UI integration | Separately assigned P02 files/generated client | M05-BROWSER-001..005 | Mission-control capacity/budget/history/explanations | Accessibility/responsive/user docs | Built-browser evidence using only real observations |
| M05-I14 — provider expansion/live hardening | Adapter-owned files plus M05 contracts only under separate tasks | M05-LIVE-001..014, M05-SEC-001..010 | Enable only evidenced provider tuples; harden limits/privacy | Live matrix/security/risks | Owner-countersigned evidence; every Blocked/Not Run visible |
| M05-I15 — operations/performance/release handoff | M05 plus separately assigned M08/DB/DEP/integration tasks | M05-OPS-001..010, M05-PERF-001..005, M05-DOC/DEP | Restore/rebuild/upgrade/health/automation integration | Runbooks/evidence/SBOM/notices/traceability | Canonical gates and independent reviews; no broader completion claim |

### Ordering and parallel-development safety

- M05-I00 precedes every production/test implementation. Provider-specific rows
  remain blocked only until their exact M0 technical handoff validates; detached
  approval records do not block local execution.
- I01–I04 may be developed in separate M05-owned files only after the root allocates non-overlapping paths and the shared value contracts are frozen. One M05 owner integrates the domain package.
- I05–I11 share one M05 migration chain and repository/projector invariants; migrations and current-projection writer code are serialized under one owner. Read-only test/security reviewers may operate in parallel.
- M02, M03, M04, M07, M08, adapters, API, and UI can implement in parallel against synchronized contract versions only. None edits M05 internals/tables.
- Each provider adapter owns its mapping into M05 provider-input DTOs and live matrix. It cannot add provider conditionals or fields to M05 privately.
- M04 owns executor/commit routing; M05 owns the capacity sink. Composition wiring is a separately allocated integration edit.
- Only the migration steward allocates Alembic revisions. Only P01 generates OpenAPI. Only the generated-client owner regenerates the client. Only root edits the central contract register/traceability during synchronization.
- Live collection schedules are coordinated so test work cannot exhaust quota, exceed request budgets, or disrupt development agents.
- A contract gap stops the affected increment. It is never bypassed by generic JSON, direct table access, duplicated DTO, deep import, or a test double.

### Red-green-refactor evidence per increment

Each implementation handoff records:

1. requirement/acceptance, plan version, contract/schema/policy/method versions, increment, and exact test IDs;
2. canonical Red command ID, UTC time, real boundary, expected behavioral failure, and sanitized evidence reference;
3. minimum production change/files and migration revision if any;
4. canonical Green command ID, UTC time, environment/boundary, result, and statuses;
5. post-refactor command/result plus mutation/coverage diagnostics where applicable;
6. real provider/account aliases/versions and owner acknowledgement for T6, without identity/secret values;
7. every Failed, Blocked, and Not Run item explicitly;
8. security/privacy/license/migration/operations/documentation impact and next integration step.

## 11. Documentation outputs

Approved implementation increments must create/update, under assigned ownership:

- M05 module document: purpose, invariants, contracts, state/field vocabularies, data ownership, current selection, health, aggregation, forecast, retention, errors, health, and extension seams;
- synchronized CTR-CAP schemas plus common exact quantity/provenance and CTR-COL commit handoff documentation;
- one M0-to-M05 capability mapping for every provider/product/source/version/plan/credential-role tuple, with exact supported fields and Unknown/Unsupported gaps;
- human API guidance and generated OpenAPI/client for units, money, nullability, field states, freshness, precision, confidence, provenance, derivation, history, and pagination;
- configuration registry entries only after names/defaults/ranges/owners/reload semantics are approved;
- migration/index/query-plan/exact-storage/PostgreSQL-portability and backup/recovery notes;
- quota/budget reconciliation, mismatch, projection-conflict, forecast, history, retention/export, rebuild, restore, upgrade, and incident runbooks containing only verified commands;
- security/privacy field inventory and data-minimization proof for DB/WAL/log/API/browser/outbox/export/diagnostic/backup/test artifacts;
- live scenario matrix with owner acknowledgements and every Blocked/Not Run state;
- dependency admission, lock/SBOM/notices statements, even when M05 adds no dependency;
- individual requirement/acceptance/evidence traceability and risk/known-limitation updates;
- release notes for contract/schema/method/config/provider-compatibility and recovery changes.

### Required implementation handoff packet

The repository handoff template must include all items required by AGENTS.md plus:

- exact real provider/resource/window/billing scope and reconciliation method for each live claim;
- observation/receipt/projection/derivation/event identifiers only in opaque sanitized form;
- exact numeric representation and migration compatibility classification;
- whether forecast/aggregation/retention live cases were available and what remains Blocked;
- confirmation that no provider source/profile/account/running agent was modified and no value was manually corrected;
- canonical automation command IDs/exit statuses and the claim scope they actually cover.

## 12. Dependency and license impact

No dependency is approved or may be installed by this Draft.

### Proposed dependency posture

M05 should introduce **no module-specific runtime dependency** initially:

- Python standard-library `decimal` supplies exact decimal arithmetic under an explicit local context; `datetime`/`zoneinfo` supply UTC/timezone primitives where approved.
- IDs/hashing/canonical serialization use approved foundation/common mechanisms.
- SQLAlchemy/Alembic, FastAPI/Pydantic, test/property/mutation tools, and frontend/chart packages belong to their already planned project-wide layers and remain Pending admission until exact versions/transitives are approved.
- Statistical/dataframe, money, currency-conversion, forecasting, time-series, or units libraries are not justified for the initial bounded methods.

Pandas, NumPy, SciPy, generic money/currency packages, automatic exchange-rate services, provider SDKs, ORMs in domain code, and forecasting services are **not proposed**. If an evidenced method cannot be implemented safely with admitted primitives, work stops for a necessity/alternatives/license/security/maintenance/performance/removal review rather than adding a convenience package.

### Admission evidence for any future package

Before manifest/import/install, record exact package/version/upstream, purpose, standard-library/current-stack insufficiency, direct/transitive licenses, maintenance/security/provenance, supported platforms/runtimes, binary/native/install behavior, network/telemetry, vulnerabilities, size/performance, pin/update/removal strategy, alternatives, SBOM/notices effect, reviewer, and approval date. A permissive headline license alone is insufficient.

## 13. Risks, unresolved decisions, and stop conditions

### Risks

| ID/risk | Likelihood/impact | Mitigation or experiment | Owner | Trigger/deadline | Status |
|---|---|---|---|---|---|
| R-001/R-024: no stable lawful quota/billing source | High/Critical | M0 official-first decision; Unsupported/Deferred is valid; no private source by implication | M03/adapters/security | Before provider contract approval | Open/M0-blocked |
| R-002: provider shape/version changes | High/Major | versioned payload/definition/parser, live compatibility, reject unverified version | M03/adapter/M05 | Every provider update | Open |
| R-005: secret/content/billing personal data leaks | Medium/Critical | typed allowlists, minimization proof, artifact scans, incident stop | Security/M05 | Every schema/live run | Open |
| R-007: stale/partial/unknown appears current | Medium/Critical | explicit field/freshness/completeness, no failure freshening | M05/P01/P02 | Contract/API review | Open |
| R-008: normalization/forecast implies false accuracy | Medium/Major | native windows, constraining ref, sufficiency/uncertainty/input IDs | M05/P02/M07 | Before health/forecast approval | Open |
| R-009: rare live states unavailable | High/Major | pure policy plus visible Blocked T6/T2; never manufacture | Test/integration/owner | Release matrix | Accepted project risk |
| R-010: verification consumes credits/disrupts work | Medium/Major | M0 cost/request budget, read-only observation, owner scheduling/stop | Live operator/M04 | Every live packet | Open |
| R-011: SQLite growth/locking | Medium/Major | short scoped transactions, indexes, bounded retention, real measurements | Persistence/M05 | I05 onward | Open |
| R-012: exact-value/SQL design blocks PostgreSQL | Medium/Major | domain canonical type, adapter mapping, portability review | Persistence/architecture | Before DDL approval | Open |
| R-014: pool overlap/double-counting | Medium/Major | explicit resource semantics/scope revision, numeric omission on unknown | M02/M05 | CS-2 | Open |
| Capacity and alert policies drift | Medium/Critical | M05 owns normalized health; M07 owns alert thresholds; contract tests enforce one-way M05 -> M07 dependency | Root/M05/M07 | CS-1 consumer review | Open until approval |
| Auth-required health input is stale or ambiguous | High/Critical | CTR-REG-010 plus CTR-COL-007 generations produce CTR-CAP-009; stale/missing input never clears state | Root/M02/M04/M05/M07 | CS-1/M0 review | Open/evidence-blocked |
| Commit contract ambiguity loses/duplicates observations | Medium/Critical | CTR-COL-006 receipt/status/digest/fencing freeze and crash tests | M04/M05 | CS-2 | Open/blocking |
| Provider resource/window identity is unstable | High/Critical | M0 identity scheme; Unknown blocks projection/aggregation | M0/M02/adapter | Per capability approval | Open/M0-blocked |
| Exact decimal storage exceeds SQLite constraints | Medium/Major | bounded canonical encoding, real round trips, query requirements, portability review | Persistence/M05 | Before I05 | Open |
| Retention deletes last explainable current fact | Medium/Major | protected current fact and explicit history/current distinction | M05/M08/product | CS-2 | Open |
| Real aged history unavailable for purge test | High/Major | keep DB test Blocked until natural/authoritative old data exists | Owner/test/M08 | AC-HIST-002 gate | Open/Blocked likely |
| Real-volume performance evidence arrives late | High/Major | measure actual growth continuously; do not seed telemetry; revise before V1 | Performance/M05 | Milestone reviews | Open |
| Currency exponent/semantics change | Low/Major | store representation/evidence/version; never infer or convert | M0/M05 | New currency/provider | Open |
| Event payload leaks sensitive amounts | Medium/Critical | no numeric values in default events; authorized re-query | Security/M07/M08 | Event approval | Open |
| Unapproved analytics/statistics dependency enters graph | Medium/Critical | standard-library-first and dependency admission stop | Dependency reviewer | Before import/install | Open |

### Approval-blocking synchronization decisions

1. Freeze `ExactQuantityV1`/money/ratio canonical wire and persistence representation, size/scale/sign bounds, rounding, and currency-exponent source.
2. Freeze native window/budget identity schemes, definition versioning, disappearance/complete-scope rules, and safe label/status mappings per provider M0 row.
3. Freeze M02 resource-pool kinds, parent/child relationship semantics, additive/rollup/independent/unknown vocabulary, and scope snapshot completeness.
4. Freeze all M05 provider-input DTOs, maximum cardinalities, pagination/bucket completeness, typed dimensions, and extension consumer allowlists with M03/A01–A03.
5. Freeze M04↔M05 CTR-COL-006 commit/status/receipt/digest/deadline/fencing/error/crash-reconciliation behavior and allocate the register ID.
6. Decide atomicity across M05 commit and M04 terminal transaction. This draft uses idempotent M05 commit followed by M04 receipt finalization, reconciled after crash, not a cross-module database transaction.
7. Freeze current selection/source interchangeability/out-of-order/conflict behavior and complete versus partial batch retirement semantics.
8. Resolve the authoritative ordered input for authentication-required/unavailable/recovered capacity health and whether CTR-COL-004/005 changes are required.
9. Freeze M05-owned normalized capacity-health classification rules, hierarchy resolution, M05 configuration API, and exact classification-boundary equality/precedence; enforce that M07 alert activation thresholds and precedence are never delivered to or consumed by M05.
10. Approve Unknown/incomplete precedence: definitive Exhausted/Critical may remain with partial completeness; Available requires complete fresh inputs.
11. Freeze aggregation eligibility, safe numeric group keys, overlap detection, and whether any V1 provider pools are evidenced additive.
12. Select and version the first burn/forecast method, exact sufficiency parameters, gap/reset/correction rules, uncertainty form, validity, and mutation target.
13. Freeze history series/bucket methods/range/cursor semantics and timezone responsibilities with P01/P02.
14. Approve 365-day retention exemptions for current source facts/receipts/events and whether an M08 export checkpoint is mandatory before each purge.
15. Freeze CTR-CAP-004/005 event schemas, stream sequencing, outbox ownership, M07/M08 consumer acknowledgements, replay, and retention.
16. Freeze P01 permissions, resource paths, disclosure, exact-number JSON schemas, problem codes, pagination, and generated-client representation.
17. Allocate tables/migration revisions, index/query budgets, SQLite exact representation, and backup/restore consistency contract.
18. Allocate configuration keys/policy owners/reload behavior; no provider freshness/capability rule may be weakened by user configuration.
19. Complete threat/privacy/dependency/license review and confirm no M05-specific runtime package is needed.
20. Decide whether exact-value persistence, M05 capacity-health classification-policy evolution, or cross-module commit/outbox durability requires a new ADR.

### M0 evidence required before provider-specific approval

For each intended subscription/API capability, the handoff must include exact provider/product/version/source/account-plan/credential-role/resource scope; window/pool identity; every field/state/unit/currency; time/reset/latency/precision/freshness; authoritative/derived boundary; history/pagination/completeness; rate/request/cost impact; extension allowlist; reconciliation UI/command/tolerance; unsupported gaps; and sanitized evidence reference. Any Unknown identity, semantics, unit, cost, role, or side effect blocks that capability's implementation rather than inviting a default.

### Stop and escalation conditions during implementation

Stop and return to root synchronization if work would:

- change a contract field/state/unit/currency/time/freshness/precision/confidence/idempotency/event/order meaning;
- add provider semantics absent from the approved M0 row or expand a verified version/plan/credential scope without live evidence;
- guess a window/resource identity, denominator, reset, currency exponent, limit, credit, provider status, or aggregation relationship;
- import another module's internals/table, a concrete provider/platform adapter, framework, OS/network/filesystem code, or edit an unallocated shared path;
- introduce a generic/raw provider dictionary, opaque extension blob, binary float, cross-currency conversion, cached-as-current fallback, or fabricated total;
- need a mock/fake/stub/emulator/replay/seeded telemetry, machine-clock change, backdated row, demo account, or test-only bypass;
- add/install a dependency without admission;
- expose a secret/content/personal billing field, raw provider output, or sensitive amount in logs/events/evidence unexpectedly;
- perform a destructive migration/purge/restore against owner data without explicit approval and verified backup;
- access provider credentials/profile/default profile, change provider budget/account, exhaust quota, or affect a running agent;
- encounter another agent editing the same M05 file, shared contract, migration head, composition root, generated artifact, manifest, or lockfile.

## 14. Delivery, compatibility, migration, and rollback

### Delivery order

1. Complete and accept M0 M05 handoffs for the first provider/resource tuple.
2. Synchronize common/M02/M03/M04/M05/M07/M08/P01/P02 contracts and update the central register.
3. Approve exact arithmetic, health/aggregation/forecast/retention methods, schema/migration, threat/privacy, dependency, tests, and this plan.
4. Deliver pure value/state/current/health policies with no I/O.
5. Deliver real SQLite schema/repositories/receipt/current projection using a real provider observation vertical slice.
6. Connect M04 commit routing and M05 events; prove crash/idempotency with real components.
7. Expose authorized P01 resources and P02 truthful views through generated artifacts.
8. Expand one provider/capability at a time only after its live matrix passes.
9. Accumulate real history, enable forecast only when sufficient, and keep unavailable derivations explicit.
10. Exercise retention/export/backup/restore/upgrade/performance/security gates and complete integration handoff.

### Compatibility and exposure

- No capacity capability is enabled until its exact M0 tuple, typed payload, adapter version, commit route, and live reconciliation are approved.
- New optional fields are compatible only with explicit safe absence/Unknown behavior. A new provider extension requires registered schema and consumer opt-in.
- Units, currency representation, field states, resource/window identity, normalized-health meaning, aggregation eligibility, forecast method semantics, event ordering/idempotency, or retention behavior changes require a new major/ADR and consumer/data migration.
- OpenAPI/client exposure follows real backend readiness; no sample/placeholder response is introduced for UI development.
- Old/new binaries may coexist only if schema and event/contract compatibility explicitly allows it. The application refuses writable startup against an incompatible schema.

### Rollback and recovery

- Before a capacity schema/representation/method migration, create and verify a real SQLite backup through M08.
- Pause new capacity commits at the M04 route before an incompatible migration or rollback; normal read access follows the approved maintenance policy.
- Prefer forward-fix for additive changes. Never run an unverified destructive downgrade against the only database.
- Preserve immutable observations, commit receipts, definitions, derivation inputs, and events. Rebuildable current/aggregate/forecast projections may be regenerated only after consistency validation.
- A prior binary may resume only against its declared schema/contract/method compatibility range. Otherwise restore the verified backup to a new path and retain the failed database for sanitized investigation.
- After restore, keep collection paused until receipt reconciliation, capacity consistency, projection rebuild, event outbox state, exact-value checks, and representative API views pass.
- Rollback never changes provider accounts/budgets/profiles or running agents.

### Post-deployment checks

- Module/schema/contract/health-policy/forecast-method versions match approved build metadata.
- Every enabled capacity capability has a compatible real adapter payload/commit route and no Unknown required semantics.
- One real quota and one configured API-budget observation reconcile end to end where supported.
- Native windows and subscription/API pools remain separate; aggregate counts reconcile to children without fabricated totals.
- Freshness, Unknown/Unsupported/auth/stale/conflict and forecast insufficiency are truthful.
- Duplicate commit returns the same receipt; conflict/late observation cannot overwrite current state.
- History/current/forecast/API/UI/event links resolve and exact money survives round trip.
- Retention/export/backup/restore/upgrade statuses reflect actual execution; unavailable aged/macOS/live states remain Blocked/Not Run.
- Logs, DB/WAL, backup, export, diagnostics, API, browser, and evidence contain no prohibited secret/content/raw provider data.

## 15. Definition of Ready for implementation

Implementation remains blocked until every applicable item is checked and recorded:

- [ ] Owner/root approves requirements, interpretations, non-goals, plan 0.2.0-draft, and changes status to Approved.
- [ ] The canonical synchronized planning gate includes M05 and passes against the real checkout.
- [ ] Exact owned/allowed/shared/forbidden paths and implementation/reviewer assignments are allocated without overlap.
- [ ] M0 M05 technical handoff is complete for each first-wave
      provider/resource/capability tuple; detached reviews are advisory.
- [ ] CTR-COMMON exact quantity/time/provenance/event contracts are Approved.
- [ ] CTR-CAP-001..009 schemas, ports, errors, events, compatibility promises, and consumer reviews are Approved.
- [ ] M02 account/resource/window relationship/scope snapshot contracts are Approved.
- [ ] M03 capability/source/outcome/provenance/extension contracts and M05 provider-input payload binding are Approved.
- [ ] M04 commit/status/receipt/fencing/crash and availability/recovery signals are Approved.
- [ ] M07 observation/health/forecast consumer semantics are Approved as one-way M05 -> M07 contracts; M07 alert-threshold policy is not delivered to M05.
- [ ] M08 health/export/retention/backup/restore/consistency ports are Approved.
- [ ] P01/P02 permissions, exact wire formats, routes, pagination, generated client, states, explanations, and accessibility responsibilities are synchronized.
- [ ] Current selection, freshness, Unknown/Unsupported, health, aggregation, forecast, history/bucket, and retention policies are approved with no materially variable decision left.
- [ ] M05 tables/constraints/indexes/transactions/retention and shared migration order are approved; exact storage and PostgreSQL portability are reviewed.
- [ ] Configuration/policy names, owners, defaults/ranges, source, reload, diagnostics, and compatibility are allocated.
- [ ] Every scenario has the correct real boundary, meaningful expected Red, safe evidence/cleanup, and assigned owner; no synthetic telemetry path exists.
- [ ] Real SQLite/service/browser/Linux/provider accounts/authoritative views and owner coordination are available for the first vertical slice; unavailable rare/aged/macOS cases are preclassified Blocked.
- [ ] Threat/privacy/data-minimization/risk review resolves or explicitly accepts every Critical item.
- [ ] Exact dependency/license/security admission and lock/SBOM/notices strategy are complete before import/install; M05-specific dependency need is confirmed absent or approved.
- [ ] Migration/backup/restore/forward-fix/rollback and event replay/rebuild procedures are reviewed.
- [ ] Any required ADR is Accepted.
- [ ] No unresolved decision in section 13 permits materially different implementations.

## 16. Approval record

| Reviewer | Decision | Conditions/findings | Date | Approved versions |
|---|---|---|---|---|
| Pavlo Sidelov / root integration steward | Pending | M0, synchronization decisions 1–20, canonical planning gate | — | — |
| M02 Registry owner | Pending | resource/window/scope/aggregation semantics | — | — |
| M03 + A01/A02/A03 owners | Pending | typed payloads, source/provenance/extensions, live matrices | — | — |
| M04 Collection owner | Pending | commit/receipt/fencing/recovery and availability signals | — | — |
| M07 Alerting owner | Pending | one-way capacity event/query consumer semantics; alert-threshold policy remains M07-local | — | — |
| M08 Operations owner | Pending | health/export/retention/backup/restore/consistency | — | — |
| P01/P02 owners | Pending | API/generated-client/UI exact-state/explanation contract | — | — |
| Persistence/migration reviewer | Pending | DDL, exact values, concurrency, indexes, portability, recovery | — | — |
| Security/privacy reviewer | Pending | minimization, extensions, amounts, artifacts, incident controls | — | — |
| Test-integrity reviewer | Pending | real-boundary design, no seeded telemetry, mutation target, Blocked policy | — | — |
| Dependency/license reviewer | Pending | exact project stack; confirm no M05-specific dependency | — | — |

No production implementation, test implementation, dependency installation, migration, configuration key, `.env`, API route, generated artifact, provider access, live collection, external resource, or shared-file edit is authorized by this Draft plan.
