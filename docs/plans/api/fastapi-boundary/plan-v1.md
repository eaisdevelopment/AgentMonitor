# PLAN-P01 — FastAPI boundary and OpenAPI v1 plan

Status: Draft; contract synchronization, dependency approval, and executable automation are not complete

Plan ID: PLAN-P01

Plan version: 0.2.0-draft

Owning module: API boundary

Target release: V1 local Linux-first release, macOS-compatible

Planning only: this document authorizes no production-code or dependency change

## 1. Purpose and completion claim

This plan defines the authenticated HTTP boundary that maps AgentMonitor's versioned application contracts to `/api/v1` resources through FastAPI and publishes the canonical OpenAPI document.

The boundary is deliberately thin. It authenticates and authorizes requests, validates transport data, invokes one or more explicitly approved application ports, maps safe results to versioned response schemas, and emits transport telemetry. It does not implement business rules, query the database, inspect processes or provider files, invoke provider SDKs or CLIs, or own provider behavior.

This plan is complete only as a planning artifact after the repository-wide synchronized planning gate accepts it. It is not an implementation-complete or implementation-ready claim. Production work remains blocked until every readiness item in section 25 is satisfied.

## 2. Governing sources

Implementers must reread the current versions of these sources before starting an increment:

- `AGENTS.md` and `.agents/skills/agentmonitor-engineering/SKILL.md`.
- `docs/product/requirements.md` and `docs/product/v1-acceptance-criteria.md`.
- `docs/product/dashboard-specification.md`.
- `docs/api/api-standards.md`.
- `docs/architecture/system-architecture.md`, `modules.md`, `contracts-and-versioning.md`, `security.md`, `deployment.md`, and `data-model.md`.
- ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0006, ADR-0007, ADR-0008, ADR-0009, ADR-0010, and ADR-0011.
- `docs/engineering/sdlc.md`, `testing-strategy.md`, `coding-standards.md`, `configuration-standard.md`, `dependency-and-license-policy.md`, `documentation-standard.md`, `review-checklists.md`, `completion-and-automation-gates.md`, and `subagent-runbook.md`.
- `docs/plans/foundation/plan-v1.md` and module plans M01 through M08.
- `docs/plans/contract-register.md`, `planning-backlog.md`, `planning-catalog.toml`, and the integration synchronization review current at implementation time.
- `docs/plans/integration/contract-alignment-audit.md` and `docs/plans/integration/requirement-coverage-audit.md`; their completed read-only findings are adopted where this revision cites CAA decisions and deferred guards, but the audits do not approve implementation.

If this plan conflicts with an approved ADR, contract register entry, or governing source, the governing source wins and this plan must be revised before code changes continue.

## 3. Requirement and acceptance coverage

### 3.1 Primary requirements

- NFR-API-001: a versioned API-first backend with published OpenAPI 3.x.
- NFR-API-002: the UI consumes the versioned API rather than backend internals.
- FR-IAM-003, FR-IAM-004, FR-IAM-006, and FR-IAM-007: browser session, API token, permission, and security-event behavior at the boundary.
- FR-SAFE-001 and FR-SAFE-002: V1 remains read-mostly and cannot control, restart, kill, route, or mutate running agent processes.
- NFR-ARCH-001 and NFR-ARCH-002: module isolation and explicit versioned contracts.
- NFR-SEC-001, NFR-PRIV-001, and NFR-PRIV-002: local security, metadata-only collection, and safe disclosure.
- NFR-TEST-001 and NFR-TEST-002: real-system TDD with no prohibited doubles.
- NFR-DOC-001 and NFR-LIC-001: developer documentation and approved dependency licensing.
- NFR-PERF-001, NFR-RES-001, NFR-OBS-001, NFR-COMP-001, and NFR-PLAT-001: response performance, resilience, observability, compatibility, and Linux/macOS behavior.

### 3.2 Supported product workflows

The API boundary exposes only approved application capabilities needed to satisfy:

- FR-ORG-001 through FR-ORG-003.
- FR-ACC-001 through FR-ACC-006.
- FR-AUTH-001 through FR-AUTH-006.
- FR-QUOTA-001 through FR-QUOTA-006.
- FR-BUDGET-001 through FR-BUDGET-006.
- FR-DISC-001 through FR-DISC-008.
- FR-STATE-001 through FR-STATE-004.
- FR-COL-001 through FR-COL-008.
- FR-HIST-001 through FR-HIST-005.
- FR-ALERT-001 through FR-ALERT-006.
- FR-UI-001 through FR-UI-007.
- FR-OPS-001 through FR-OPS-006.

The seven deferred requirements are explicit V1 non-capabilities: FR-ALERT-007, FR-ALERT-008, FR-ROUTE-001, FR-ROUTE-002, FR-CONTENT-001, FR-REMOTE-001, and FR-PROVIDER-EXT-001. They are not supported workflows, test-credit ranges, permissions, configuration surfaces, dependencies, routes, schemas, or generated-client operations. Their deferred status must remain visible in public documentation and is protected by the exact negative checks in section 20.10.

### 3.3 Acceptance criteria

The boundary contributes evidence to AC-V1-001 through AC-V1-008, AC-LIVE-001 through AC-LIVE-007, AC-PROC-001 through AC-PROC-005, AC-HIST-001 and AC-HIST-002, AC-ALERT-001 through AC-ALERT-003, AC-UI-001 through AC-UI-006, AC-OPS-001 through AC-OPS-006, and AC-TEST-001 through AC-TEST-006.

No HTTP-only result may be presented as satisfying a live-provider, live-process, browser, backup/restore, or endurance criterion whose governing acceptance criterion requires a different real boundary.

## 4. Scope

### 4.1 In scope

- FastAPI application-boundary integration through the foundation application factory.
- Versioned `/api/v1` routers, request and response schemas, transport dependencies, and middleware.
- Browser session-cookie, CSRF, and bearer-token transport for M01 IAM contracts.
- Permission enforcement before application-port invocation.
- Strict Host, Origin, request-size, content-type, pagination, sort, filter, correlation, concurrency, and idempotency transport policies.
- RFC 9457-compatible safe problem responses through `SafeProblemV1`.
- Resource APIs for IAM, account and organization registry, provider/capability status, collection, capacity, runtime observation, alerting, and operations.
- Authenticated OpenAPI JSON, Swagger UI, and ReDoc in an initialized installation.
- Stable OpenAPI operation IDs, named schemas, documented security requirements, error responses, headers, examples, and deprecations.
- Deterministic OpenAPI generation and handoff to the generated frontend client pipeline.
- Real running-server, generated-client, browser, security, and performance verification.

### 4.2 Explicitly out of scope

- Business policy or domain calculations.
- SQL, SQLAlchemy models, repositories, migrations, database sessions, or database inspection.
- Direct calls to provider adapters, provider SDKs, provider APIs, CLIs, local profile files, or operating-system process APIs.
- Password hashing, session/token persistence, CSRF truth, authorization policy truth, or audit persistence; M01 owns them.
- Collection scheduling, leases, deduplication, budgets, backoff, adapter invocation, or freshness calculations; M04 owns them.
- Capacity normalization, forecast calculation, aggregation, or confidence rules; M05 owns them.
- Process/session discovery or correlation logic; M06 owns them.
- Alert evaluation, cooldown, acknowledgement, snooze, or notification-domain rules; M07 owns them.
- Backup creation, verification, restore, export construction, or diagnostic redaction; M08 owns them.
- UI layout, state management, or hand-written HTTP calls; PLAN-P02 owns the UI.
- Native desktop notifications, email, messengers, prompt/response/tool-content capture, remote multi-user operation, agent routing, and automatic account switching.
- Gemini, Grok, Muse, or any additional-provider implementation under FR-PROVIDER-EXT-001.
- Any HTTP endpoint that kills, pauses, resumes, restarts, logs out, logs in, reroutes, or modifies a running agent process.
- A generic database administration endpoint, generic settings mutation endpoint, debug endpoint, metrics dump, raw log endpoint, or arbitrary file download.
- Public restore execution. Restore remains a local, explicit, runbook-controlled operation.

## 5. Module boundary and import law

### 5.1 Planned owned paths

The P01 implementation owns only these planned source areas:

```text
backend/src/agentmonitor/api/__init__.py
backend/src/agentmonitor/api/contracts.py
backend/src/agentmonitor/api/errors.py
backend/src/agentmonitor/api/openapi.py
backend/src/agentmonitor/api/pagination.py
backend/src/agentmonitor/api/security_headers.py
backend/src/agentmonitor/api/transport.py
backend/src/agentmonitor/api/v1/__init__.py
backend/src/agentmonitor/api/v1/router.py
backend/src/agentmonitor/api/v1/dependencies.py
backend/src/agentmonitor/api/v1/routers/iam.py
backend/src/agentmonitor/api/v1/routers/registry.py
backend/src/agentmonitor/api/v1/routers/providers.py
backend/src/agentmonitor/api/v1/routers/collection.py
backend/src/agentmonitor/api/v1/routers/capacity.py
backend/src/agentmonitor/api/v1/routers/runtime.py
backend/src/agentmonitor/api/v1/routers/alerts.py
backend/src/agentmonitor/api/v1/routers/operations.py
backend/src/agentmonitor/api/v1/schemas/common.py
backend/src/agentmonitor/api/v1/schemas/iam.py
backend/src/agentmonitor/api/v1/schemas/registry.py
backend/src/agentmonitor/api/v1/schemas/providers.py
backend/src/agentmonitor/api/v1/schemas/collection.py
backend/src/agentmonitor/api/v1/schemas/capacity.py
backend/src/agentmonitor/api/v1/schemas/runtime.py
backend/src/agentmonitor/api/v1/schemas/alerts.py
backend/src/agentmonitor/api/v1/schemas/operations.py
backend/tests/api/
backend/tests/contract/api/
backend/tests/integration/api/
docs/api/http-boundary.md
docs/api/resources/
docs/test-evidence/api/
```

The implementation plan must adjust paths if the approved foundation layout differs, before the first red test. It must not create a parallel package root.

These are shared or generator-owned paths and require a named single writer for each integration change:

```text
backend/src/agentmonitor/composition/**
backend/src/agentmonitor/contracts/**                 # producer-owned; P01 consumes only
backend/tests/contract/**                             # shared contract-test registration
contracts/openapi/agentmonitor-v1.json                # generated by FND mechanism; integration steward is sole writer
frontend/src/generated/api/**                         # generated by FND mechanism; integration steward is sole writer
frontend/src/shared/api/**                            # P02-owned
frontend/tests/browser/api/**                         # P01/P02 test allocation required
tooling/**                                            # canonical automation owner required
docs/traceability.md
docs/plans/contract-register.md
docs/plans/planning-backlog.md
```

P01 route-family agents must not edit any shared path until the integration steward allocates the exact file. This plan itself does not allocate those shared files.

### 5.2 Allowed imports

- FastAPI, Starlette, Pydantic, and approved standard-library transport utilities inside `agentmonitor.api` only.
- Common stable IDs, time values, page values, `SafeProblemV1`, and correlation types from approved common contracts.
- Application-port interfaces and immutable DTOs published by M01 through M08.
- Foundation composition, configuration, logging, build metadata, and clock abstractions through CTR-FND contracts.

The planned exact public contract import roots are:

```text
agentmonitor.contracts.common_v1
agentmonitor.contracts.configuration_v1
agentmonitor.contracts.foundation_v1
agentmonitor.contracts.identity_access_v1
agentmonitor.contracts.registry_v1
agentmonitor.contracts.provider_system_v1
agentmonitor.contracts.collection_control_v1
agentmonitor.contracts.capacity_v1
agentmonitor.contracts.runtime_observation_v1
agentmonitor.contracts.alerting_v1
agentmonitor.contracts.operations_v1
agentmonitor.contracts.deployment_v1
agentmonitor.contracts.integration_v1
agentmonitor.contracts.application_v1
```

Shared primitives may be imported only from the frozen one-file convention
`agentmonitor.contracts.<family>_v<major>`, backed by
`backend/src/agentmonitor/contracts/<family>_v<major>.py`. P01 uses only the
producer-owned published files and may not add package-per-version paths or
compatibility re-exports. FastAPI/Pydantic imports stay below
`agentmonitor.api`; application contract files must not import them.

Imports from `agentmonitor.contracts.provider_system_v1` are symbol-allowlisted to the two synchronized safe capability/compatibility query protocols, their request DTOs, and their safe result DTOs. A static boundary check rejects provider resolution, invocation, discovery/outcome, reauthentication-protocol, extension-registry, typed port-reference, registration command, or adapter symbols. Reauthentication routes import only the M02-owned CTR-REG-008 application workflow from `agentmonitor.contracts.registry_v1`.

The provider-extension exception to the one-file family layout is the
producer-owned versioned namespace under
`backend/src/agentmonitor/contracts/providers/<provider>/<capability>/v1/**`.
P01 never imports that namespace or an extension registry; M03/application
ports map approved safe fields into P01's one-file API contract boundary.

### 5.3 Forbidden imports and access

- Any `infrastructure`, `persistence`, `repository`, `database`, `migration`, `provider_adapter`, `platform`, `process`, or UI package.
- SQLAlchemy, SQLite drivers, provider SDKs, CLI libraries, `subprocess`, `psutil`, or direct filesystem/profile readers.
- Module-private domain entities or services not listed in a published application contract.
- Another route handler, another route schema as a business DTO, or the generated UI client.
- Global mutable service locators or import-time runtime configuration.

The automated architecture check must fail closed if a route imports a prohibited layer. Application ports are injected at composition; a handler never constructs an implementation.

### 5.4 Handler and lifecycle shape

- The foundation application factory supplies an immutable `ApiV1Dependencies` bundle of approved port protocols and validated settings; route modules do not use globals or lookup strings.
- A handler performs structural mapping, universal security dependencies, one named application use case (or the explicitly documented authentication/authorization plus resource chain), exhaustive typed-outcome mapping, and response serialization.
- Cross-module orchestration such as reauthentication, product audit, health, or export must arrive as an application port owned by a module. A handler does not coordinate transactions or compensate partial module work.
- Application results are immutable detached DTOs. Lazy ORM objects, generators tied to a database session, provider handles, and internal exceptions cannot cross into response serialization.
- Async handlers await async application ports. Blocking filesystem, database, subprocess, provider, and CPU work is forbidden in P01 and cannot be hidden in an event-loop handler.
- Request cancellation ends only uncommitted boundary work. Once an application command is accepted, its owner defines commit and durable-job behavior; disconnect does not imply cancellation.
- Startup validates dependencies, route/permission registration, settings, and schema generation before readiness. Shutdown rejects new work, allows bounded response drain, and delegates job lifecycle to the owning module.
- Typed outcomes are matched exhaustively. An unknown outcome/version fails closed as a generic 500/503 and a safe compatibility event; it is not serialized through `str()`.

## 6. Published and consumed contracts

### 6.1 Contracts published by P01

- CTR-API-001 v1: canonical OpenAPI contract for `/api/v1`, including operation IDs, schemas, security, errors, headers, and compatibility rules.
- CTR-API-002 v1: browser session-cookie and CSRF HTTP transport contract.
- CTR-API-003 v1: bearer-token HTTP transport contract.
- CTR-COMMON-005 v1: `SafeProblemV1`, owned here unless contract synchronization assigns a different owner.
- CTR-UI-001 v1: generated TypeScript client boundary semantics derived from
  CTR-API-001; PLAN-FND owns generator mechanics, PLAN-INT is the allocated
  generated-artifact writer, and P02 consumes the wrapper.

All five are Draft until the contract register, module plans, OpenAPI artifact,
and generated client agree. No implementer may silently promote their status.

### 6.2 Contracts consumed

- Common/configuration/foundation: `CTR-COMMON-001`, `CTR-COMMON-002`,
  `CTR-COMMON-003`, `CTR-COMMON-004`, `CTR-COMMON-007`, `CTR-CONFIG-001`,
  `CTR-FND-001`, `CTR-FND-002`, `CTR-FND-003`, `CTR-FND-004`, `CTR-FND-005`,
  `CTR-FND-007`, and `CTR-FND-008`.
- IAM: `CTR-IAM-001`, `CTR-IAM-002`, `CTR-IAM-003`, `CTR-IAM-004`,
  `CTR-IAM-005`, `CTR-IAM-006`, `CTR-IAM-007`, and the M2 safe security-event
  projection `CTR-IAM-008`.
- Registry: `CTR-REG-001`, `CTR-REG-002`, `CTR-REG-003`, `CTR-REG-004`,
  `CTR-REG-005`, `CTR-REG-006`, `CTR-REG-008`, `CTR-REG-009`, and
  `CTR-REG-010`. P01 starts/gets/cancels only the M02-owned CTR-REG-008 durable
  reauthentication workflow; CTR-REG-009/010 are safe projected scope/auth
  semantics and never authorize direct event or table access.
- Provider system: `CTR-PROV-002` only, through side-effect-free
  capability/compatibility query DTOs. Provider authentication and
  reauthentication reach P01 through M02 CTR-REG-008/010 application
  projections. P01 imports no provider invocation gateway, capability port
  reference, adapter registry, provider auth-health/auth-flow protocol,
  provider extension registry/schema namespace, discovery/collection
  outcome, or adapter implementation.
- Collection: `CTR-COL-001`, `CTR-COL-002`, `CTR-COL-005`, and `CTR-COL-006`.
- Capacity: `CTR-CAP-001`, `CTR-CAP-002`, `CTR-CAP-003`, `CTR-CAP-006`, and
  `CTR-CAP-007`.
- Runtime observation: `CTR-RUN-001`, `CTR-RUN-002`, `CTR-RUN-003`, and
  `CTR-RUN-007`.
- Alerting: `CTR-ALERT-001`, `CTR-ALERT-002`, `CTR-ALERT-003`,
  `CTR-ALERT-004`, and `CTR-ALERT-005`.
- Operations/application: `CTR-OPS-001`, `CTR-OPS-002`, `CTR-OPS-003`,
  `CTR-OPS-004`, `CTR-OPS-005`, and `CTR-APP-001`.
- Deployment/integration evidence: `CTR-DEP-001`, `CTR-INT-001`,
  `CTR-INT-002`, `CTR-INT-003`, `CTR-INT-005`, and `CTR-INT-006`.
This list is exact for contract-baseline 0.2.0. P01 does not consume
`CTR-PROV-001`, `CTR-PROV-003..005`, any repository/UoW contract, DB contract,
platform/process-inspection port, durable-event transport, provider operation
context, or module-private type.

### 6.3 Invocation rule

Each endpoint row in section 12 names exactly one Draft-aligned resource
application port. An endpoint cannot be implemented while its named port is
ambiguous or unapproved. The universal M01
credential/CSRF/authorization chain is transport security and does not give a
route a second resource use case. A transport handler may perform
authentication, authorization, structural validation, header handling, safe
mapping, and serialization only. Any decision depending on persisted or domain
state belongs to the named application port.

## 7. Versioning and compatibility

- The public prefix is exactly `/api/v1`.
- A response schema name ends in `V1`; an input schema name ends in `InputV1`; page envelopes end in `PageV1`.
- Stable enum wire values use documented lowercase snake case and never Python member names implicitly.
- IDs are opaque strings. Clients cannot infer type, order, timestamp, provider, or organization from an ID.
- UTC instants are RFC 3339 strings with an explicit `Z`; public API durations are integer milliseconds unless a named field explicitly defines a different unit.
- Missing and JSON `null` have distinct meanings. No implicit null-to-default conversion is allowed.
- Additive optional fields and additive enum values are the only normally compatible V1 schema changes. Clients must preserve unknown enum handling where the generated target permits it.
- Removing or renaming a route, operation ID, property, security requirement, documented status, or enum value is breaking.
- Making an optional property required, narrowing a value, changing pagination order, or changing a permission is contract-impacting and requires review even when the JSON shape is unchanged.
- A breaking public change requires a new versioned route/schema, migration window, ADR, contract-register update, compatibility evidence, and UI client migration.
- Deprecated operations remain functional for the documented window, contain OpenAPI `deprecated: true`, return `Deprecation` and `Sunset` headers, and link to migration documentation. A route may not be removed merely because the UI stopped calling it.
- The committed OpenAPI artifact is generated, never hand-edited. The generated TypeScript client is also generated, never hand-edited.
- A compatibility diff against the last approved OpenAPI artifact must fail closed on an unapproved breaking change.

## 8. Common HTTP representation

### 8.1 Media and request rules

- JSON operations consume and produce `application/json`; problem responses use `application/problem+json`.
- Artifact downloads declare their exact media type and `Content-Disposition: attachment` with a server-generated safe filename.
- Unsupported content types return 415. Unsupported methods return 405 through `SafeProblemV1`.
- JSON bodies are bounded before parsing. Oversize bodies return 413 without logging the body.
- Unknown request properties are rejected. Response models exclude no documented property silently.
- Empty success uses 204 with no response body.
- Creation uses 201 and a `Location` header when the resource is immediately materialized.
- M2 exception for `iam_create_api_token_v1` and `iam_rotate_api_token_v1`: the approved 13-route shell has no token-by-ID retrieval route. Their 201 responses carry the one-time issue representation and safe token ID but omit `Location` rather than advertise an unavailable URI. Revisit when a token-detail route is separately approved.
- Accepted long work uses 202 and a `Location` header to the durable request/job resource.

### 8.2 Common response schemas

`ResourceMetaV1` contains `version`, `created_at`, and `updated_at` only where the application contract supplies them. The boundary does not invent timestamps or versions.

`PageMetaV1` contains:

- `limit`: accepted page size.
- `next_cursor`: opaque nullable cursor.
- `has_more`: boolean derived by the owning application query, not guessed in the route.

Every list response is a named resource-specific page with `items` and `page`; anonymous arrays are forbidden.

`AcceptedOperationV1` contains the durable resource `id`, `status`, `submitted_at`, and safe `links`. It is used only when the owning contract returns those values.

### 8.3 ETag and concurrency

- Mutable resource GET responses expose a strong ETag derived from the application DTO version through a single documented encoder.
- Mutations of an existing resource require `If-Match` unless the module contract explicitly proves that the operation is commutative.
- Missing precondition returns 428; stale precondition returns 412.
- The route decodes the ETag to `expected_version` and supplies it to the application command. It does not compare persisted versions itself.
- Bodies do not duplicate `expected_version`. If an upstream contract still requires a body field, contract synchronization must define one canonical mapping before implementation.

## 9. Pagination, filtering, and sorting

- Cursor pagination is required for every unbounded list.
- `limit` defaults to 50 and has a proposed maximum of 200; exact values require configuration and performance synchronization before approval.
- A cursor is opaque, URL-safe, versioned, query-bound, tamper-evident if it contains material client-controlled state, and never contains secrets.
- Reusing a cursor with a different filter, sort, scope, or principal returns 400 `cursor_query_mismatch`.
- Expired or structurally invalid cursors return 400 `invalid_cursor`; they never produce 500.
- Sort is a comma-separated allowlisted sequence. Prefix `-` means descending. Every order ends with an opaque ID tie-breaker.
- Default sort is documented per resource and stable across pages.
- Filters are explicit named query parameters. There is no free-form SQL-like filter syntax.
- Repeated filter values mean logical OR within a field and logical AND across fields unless the endpoint documents a stricter rule.
- Unknown filters and sort keys return 400 rather than being ignored.
- Search terms have an approved maximum length and are normalized only by the owning application contract.
- Page cursors, filters, and search values are never logged verbatim.

### 9.1 Proposed exact query profiles

These query profiles are part of CTR-API-001 and must be reconciled with the owning application query before approval. `id` below means the resource's opaque ID field. Time ranges are half-open `[from, before)` UTC ranges. A blank filter is not equivalent to omission unless explicitly documented.

| List operation | Allowed filters | Default sort; allowed alternatives |
|---|---|---|
| `iam_list_sessions_v1` | `state`, `created_from`, `created_before` | `-last_seen_at,-id`; `created_at,id` |
| `iam_list_api_tokens_v1` | `state`, repeated `scope`, `expires_before` | `-created_at,-id`; `name,id`, `expires_at,id` |
| `iam_list_security_events_v1` | `event_type`, `outcome`, `occurred_from`, `occurred_before` | `-occurred_at,-id` only |
| `registry_list_organizations_v1` | `lifecycle` | `order_index,id`; `name,id`, `-updated_at,-id` |
| `registry_list_accounts_v1` | `organization_id`, `provider_key`, `lifecycle`, `monitoring_state` | `friendly_name,id`; `-updated_at,-id`, `provider_key,id` |
| `registry_list_provider_installations_v1` | `provider_key`, `state`, `compatibility_state` | `provider_key,id`; `-last_seen_at,-id` |
| `registry_list_discovery_candidates_v1` | `provider_key`, `installation_id`, `state`, `requires_owner_action` | `-last_seen_at,-id`; `provider_key,id` |
| `registry_list_account_profiles_v1` | path-scoped `account_id`, `lifecycle`, `protected` | `created_at,id`; `-updated_at,-id` |
| `registry_list_account_resources_v1` | path-scoped `account_id`, `resource_kind`, `lifecycle`, `parent_resource_id` | `resource_kind,id`; `-updated_at,-id` |
| `registry_list_events_v1` | `subject_kind`, `subject_id`, `change_kind`, `occurred_from`, `occurred_before` | `-occurred_at,-id` only |
| `provider_get_capabilities_v1` | path-scoped `provider_key`, `capability_key`, `support_state` | `capability_key,id` only |
| `collection_list_runs_v1` | `provider_key`, `account_id`, `capability_key`, `state`, `requested_from`, `requested_before` | `-requested_at,-id` only |
| `capacity_list_quota_windows_v1` | path-scoped `account_id`, `pool_id`, `window_kind`, `freshness`, `field_state` | `pool_id,window_kind,id`; `reset_at,id` |
| `capacity_list_budgets_v1` | path-scoped `account_id`, `pool_id`, `resource_id`, `currency`, `freshness`, `field_state` | `pool_id,resource_id,id`; `renewal_at,id` |
| `capacity_list_usage_breakdowns_v1` | path-scoped `budget_id`, `dimension_kind`, `interval_from`, `interval_before` | `dimension_kind,id`; `-interval_end,-id` |
| `capacity_list_history_v1` | required `subject_id`, `metric`, `series_kind`, `from`, `before`; optional `resource_id`, `window_id`, `bucket_method`, `bucket_seconds` | `observed_at,id` only |
| `capacity_list_health_history_v1` | `subject_id`, `state`, `from`, `before` | `observed_at,id` only |
| `capacity_list_forecasts_v1` | `subject_id`, `resource_id`, `state`, `valid_at` | `subject_id,resource_id,id`; `exhaustion_at,id` |
| `runtime_list_processes_v1` | `provider_key`, `installation_id`, `presence_state`, `freshness`, `observed_from`, `observed_before` | `-last_observed_at,-id`; `provider_key,id` |
| `runtime_list_process_history_v1` | path-scoped `process_id`, `from`, `before`, `state` | `observed_at,id` only |
| `runtime_list_sessions_v1` | `organization_id`, `provider_key`, `account_id`, `runtime_state`, `correlation_state`, `freshness` | `-last_activity_at,-id`; `started_at,id` |
| `runtime_list_session_history_v1` | path-scoped `session_id`, `from`, `before`, `runtime_state` | `observed_at,id` only |
| `runtime_list_session_roots_v1` | `scope_kind`, `scope_id`, `runtime_state`, `as_of` | `-last_activity_at,-id` only |
| `runtime_list_state_history_v1` | required `session_id`, `from`, `before`; optional `runtime_state`, `certainty` | `occurred_at,id` only |
| `runtime_list_correlation_decisions_v1` | `session_id`, `account_id`, `state`, `automatic`, `valid_at` | `-decided_at,-id` only |
| `alerts_list_rules_v1` | `scope_kind`, `scope_id`, `condition_type`, `enabled`, `lifecycle` | `condition_type,scope_kind,id`; `-updated_at,-id` |
| `alerts_list_alerts_v1` | `organization_id`, `provider_key`, `account_id`, `condition_type`, `severity`, `lifecycle`, `unread`, `acknowledged`, `snoozed` | `-last_seen_at,-id`; `severity,-last_seen_at,-id` |
| `alerts_list_alert_history_v1` | path-scoped `alert_id`, `transition`, `from`, `before` | `occurred_at,id` only |
| `alerts_list_notifications_v1` | `organization_id`, `provider_key`, `account_id`, `severity`, `lifecycle`, `unread`, `acknowledged`, `snoozed` | `-latest_at,-id` only |
| `operations_list_backups_v1` | `trigger`, `lifecycle`, `integrity_state`, `requested_from`, `requested_before` | `-requested_at,-id` only |
| `operations_list_audit_events_v1` | `event_type`, `outcome`, `actor_kind`, `occurred_from`, `occurred_before` | `-occurred_at,-id` only |
| `operations_list_exports_v1` | `purpose`, `state`, `format`, `requested_from`, `requested_before` | `-requested_at,-id` only |

`registry_list_providers_v1` uses a bounded noncursor list ordered by `provider_key`; notification counts, health, aggregate, and other singular projections are not page resources. Tree endpoints accept bounded `depth_limit` and `node_limit` instead of pagination. The exact maximum time span, bucket values, and tree limits are configuration/owner-contract synchronization items; absence of approved bounds stops implementation.

Singular query selectors are also closed: `capacity_get_aggregate_v1` accepts `scope_kind=global|organization|provider|account`, the required opaque `scope_id` for nonglobal scope, and `as_of`; `capacity_get_health_v1` accepts one approved subject selector and `as_of`; session tree accepts one root/scope, `as_of`, `depth_limit`, and `node_limit`; alert-rule resolution accepts condition type plus one approved scope; notification counts accepts the same authorized hierarchy filters as notification list; health/readiness/version accept only their approved disclosure selector. Organization-level capacity responses include owner-supplied child coverage/counts and aggregate status, never a boundary-calculated total.

History APIs must remain capable of traversing the approved one-year retained history through bounded pages or approved buckets. P01 does not silently cap product retention to a shorter interval, load an entire year into memory, or calculate a roll-up. Large owner-requested extracts use M08 export jobs.

## 10. Correlation, idempotency, and long work

### 10.1 Correlation

- The request header is `X-Correlation-ID`.
- An accepted value is 1–64 printable ASCII characters from `[A-Za-z0-9._:-]`; other values return 400 `invalid_correlation_id`.
- If absent, the boundary creates a cryptographically unpredictable opaque value using the foundation correlation contract.
- Every response, including errors, 401, 403, 404, 413, 429, and 500, returns `X-Correlation-ID`.
- The value enters the structured logging context and approved application command metadata.
- It is not used as an idempotency key and does not reveal a session, token, account, process, or provider identifier.

### 10.2 Idempotency

- Every POST that can duplicate a durable mutation requires `Idempotency-Key`.
- PUT, PATCH, or DELETE also requires it where the matrix names idempotency because the owning command creates secondary durable work/events or accepts a command ID; HTTP method semantics alone do not replace owner-command deduplication.
- The accepted key is 16–128 visible ASCII characters and is scoped to stable principal and operation ID. A safe canonical request fingerprint is additionally compared where the operation permits one; password change retains or compares no password/body-derived fingerprint.
- Each operation declares exactly one replay policy in the operation registry: `safe_query_repeat`, `fresh_credential_issue`, `replay_safe_representation`, `conditional_set_transition`, `terminal_idempotent_transition`, `one_time_secret_non_replayable`, or `join_durable_job`.
- Under `replay_safe_representation`, the same key and canonical request returns the original safe status, headers, and representation without repeating the application command.
- `iam_change_password_v1`, `iam_create_api_token_v1`, and `iam_rotate_api_token_v1` use replay policy `one_time_secret_non_replayable`. After the original success commits, a retry that first passes current authentication and authorization returns 409 problem code `one_time_secret_not_replayable` with only safe resource ID/version/committed-state metadata. The old cookie revoked by password change instead gets 401 `dashboard_authentication_required` before receipt lookup; a fresh authorized session with the same administrator principal and key can receive 409 before stale `If-Match` or old-password checks. It never returns, reconstructs, caches, logs, or persists the session, CSRF, or bearer plaintext.
- Long submissions use `join_durable_job`: a retry returns or links to the same durable request/job according to the owner contract, never a second job.
- Same key and different safe canonical metadata returns 409 `idempotency_key_reused` for operations that retain that fingerprint. An authenticated password-change repeat is always `one_time_secret_not_replayable` regardless of submitted password fields; an unauthenticated repeat is rejected before receipt lookup.
- A concurrent duplicate returns the committed result only for replay policies that permit representation replay, or 409 `idempotency_in_progress` with `Retry-After` while work remains active; it never performs duplicate work. After a one-time-secret command commits, a still-authenticated and authorized loser receives only the safe 409 `one_time_secret_not_replayable` outcome, never the original secret-bearing result. If that commit revoked the loser's credential, authentication fails with 401 before receipt lookup.
- Idempotency truth and retention are owned by the application module that owns the command unless synchronization establishes a common application service. An in-memory API cache is forbidden.
- Failed authentication, authorization, Origin, CSRF, and structural validation do not reserve a key.
- Keys and request fingerprints are never logged in full.

### 10.3 Long-running operations

- Collection requests, reauthentication preparation where approved, manual backup, diagnostic bundle creation, and export creation return 202.
- The response includes `Location` for an authorized durable status resource and may include bounded `Retry-After`.
- Status resources expose only queued/running/succeeded/failed/cancelled/blocked states supported by the owner contract.
- Failure detail is a safe code and bounded summary; raw exception text, command lines, paths, provider bodies, and credentials are forbidden.
- HTTP connection lifetime is never used as job state.
- Cancellation exists only if the owning module publishes an approved cancellation command. P01 does not invent it.
- Backup verification uses the status and representation approved for M08 `VerifyBackupV1`; P01 cannot recast it as a durable asynchronous job unless M08 first publishes that job contract.

### 10.4 Rate and abuse controls

- Login, token create/rotate, manual collection, reauthentication start, backup, diagnostic bundle, and export have separately configured principal/target/operation limits.
- Authentication throttling truth belongs to M01. Collection admission and provider-cost limits belong to M04. Backup/export admission belongs to M08. P01 maps typed decisions and never maintains a second in-memory policy truth.
- Pre-authentication limiting uses only the trustworthy local source class established by the deployment contract; forwarded client-address headers are ignored.
- A limit rejection returns 429 `rate_limited` with a bounded `Retry-After` when the owner contract supplies it. Capacity/dependency admission can instead return the owner's safe 409 or 503 outcome.
- Limits apply before expensive body processing or application work where possible, without reserving idempotency keys for rejected unauthenticated requests.
- Limit counters, current thresholds, attempt counts, target identifiers, and account existence are not disclosed in error details.

## 11. Error contract

`SafeProblemV1` implements RFC 9457 with these required fields:

- `type`: the stable same-origin relative `/problems/{closed_safe_code}` URI. The code is selected only from the reviewed safe problem catalog, never copied from submitted input. Its authenticated local HTML documentation transport is not a versioned resource operation; an unauthenticated caller can follow a 401 type after signing in. No placeholder domain or external request is permitted.
- `title`: stable non-sensitive summary.
- `status`: HTTP status.
- `code`: stable machine-readable lowercase snake-case code.
- `correlation_id`: the response correlation ID.

Optional fields are `detail`, `instance`, `errors`, and safe retry metadata. `detail` is bounded and selected from an allowlist or domain-safe problem contract. `errors` contains safe field locations and codes, never rejected secret values.

`SafeFieldErrorV1` contains a bounded JSON-pointer-like `path`, stable `code`, and optional allowlisted `message`. It never contains `input`, `ctx`, stack information, regular-expression internals, or a stringified submitted value. The error list is capped and adds a safe truncation flag when further errors exist.

Required mappings include:

- 400 for malformed headers, filters, sorts, cursors, or structurally invalid action combinations.
- 401 `invalid_dashboard_credentials` for a bounded failed login, without revealing account or password state.
- 401 `dashboard_authentication_required` when a protected operation has a missing, invalid, expired, revoked, or otherwise unusable dashboard session/bearer credential, with a safe `WWW-Authenticate` challenge where applicable.
- 403 for valid credentials without permission and for Origin/CSRF rejection after safe normalization.
- 404 for an authorized request whose resource is absent. Unauthorized callers do not receive existence oracles.
- 405, 406, 413, 415, and 422 for method, representation, size, media, and schema failures.
- 409 `provider_reauthentication_required` when an authenticated dashboard principal requests a resource whose provider-managed profile needs reauthentication; this never clears or invalidates the dashboard session.
- 409 `one_time_secret_not_replayable` for a committed one-time-secret command retry, with safe resource metadata and no secret replay.
- 409 for other state and idempotency conflicts under their distinct stable codes.
- 412 and 428 for optimistic-concurrency failures.
- 429 for boundary throttling with `Retry-After` when known.
- 500 for an unexpected boundary failure, always with a generic problem detail.
- 503 for unavailable required application services/readiness, with a safe dependency class rather than a raw cause.

FastAPI/Pydantic validation failures, Starlette HTTP errors, uncaught exceptions, and middleware rejections must all use the same safe representation. No default framework traceback or validation object may escape.

`dashboard_authentication_required` and `provider_reauthentication_required` are disjoint contract states. The former starts dashboard-login recovery and is never used for provider health. The latter preserves the dashboard principal and links only to an authorized CTR-REG-008 workflow or safe guidance; it is never mapped to 401 and never starts provider work inside P01.

## 12. Endpoint, permission, and application-contract matrix

All entries are authenticated except the two explicitly pre-authentication initialization/login rows. `cookie` means a valid M01 browser session; `bearer` means CTR-API-003. Mutating cookie requests additionally require Origin and CSRF. Every row also requires strict Host checking, correlation handling, safe errors, and audit behavior defined later.

For every authenticated row, the complete invocation chain is M01 `ResolveBrowserSessionV1` or `ResolveBearerTokenV1`, M01 `VerifyCsrfV1` for an unsafe cookie request, M01 `AuthorizePrincipalV1` with the matrix permission/subject, and only then the resource contract named in the last column. The resource column does not imply an authentication shortcut. Pre-authentication rows invoke only their named M01 port after perimeter controls.

### 12.0 Normative operation-policy registry

The tables in sections 12.1–12.8 and 12.9 form one normalized operation registry. Every operation record has exactly one operation ID, method/path, auth profile, M01 permission, resource application port, replay policy, success schema, and error schema. The implementation materializes these fields explicitly; it does not infer authorization from a router prefix.

Auth profiles are assigned exhaustively:

- `preauth_loopback`: only `iam_get_initialization_v1` and `iam_login_v1`; permission is exactly `none` and their named M01 policy port is the sole use case.
- `browser_cookie_only`: `iam_get_current_session_v1`, `iam_logout_v1`, `iam_change_password_v1`, `iam_list_sessions_v1`, `iam_revoke_session_v1`, and `iam_revoke_other_sessions_v1`; bearer is rejected even if it holds another scope.
- `cookie_or_bearer`: every other matrix operation. Cookie mutations require exact Origin plus M01 CSRF verification; bearer requests require the permission as an admitted token scope and never use CSRF.

Replay policy is assigned exhaustively by the following top-to-bottom rules:

- Every GET uses `safe_query_repeat`; an incidental audit fact does not make the resource query a command.
- `iam_login_v1` uses `fresh_credential_issue`, accepts no `Idempotency-Key`, and intentionally creates one fresh session on each successful authentication.
- `iam_change_password_v1`, `iam_create_api_token_v1`, and `iam_rotate_api_token_v1` use `one_time_secret_non_replayable`.
- Reauthentication start, manual collection, manual backup, diagnostic bundle, and export creation use `join_durable_job`.
- A matrix mutation marked `idempotency` and not listed above uses `replay_safe_representation` through the owning application receipt.
- A remaining PUT/PATCH or reversible DELETE with `If-Match` uses `conditional_set_transition`.
- Logout plus session/API-token revocation use `terminal_idempotent_transition` where the owner contract declares replay-safe terminal behavior. Archive restoration, policy-override deletion, and unsnooze are reversible conditional transitions and therefore use `conditional_set_transition` unless their matrix row explicitly requires an idempotency receipt.

Every operation's error schema is exactly `SafeProblemV1` for every app/framework non-success response. Malformed HTTP framing that Uvicorn/h11 rejects before ASGI—including duplicate `Host` headers—must be denied but cannot carry an app-generated problem or correlation header; this is a narrowly scoped parser-level exception, not an exception for any routed request. The generated OpenAPI record carries `x-agentmonitor-auth-profile`, `x-agentmonitor-required-permission`, `x-agentmonitor-application-port`, `x-agentmonitor-replay-policy`, and `x-agentmonitor-error-schema`. AUTO-QUALITY fails if any operation lacks one value, has more than one resource port or permission, names a provider invocation/orchestration port, or disagrees with the matrix/schema catalog. Every row maps to one 0.2.0 Draft-aligned application contract; no runtime route is registered before that contract and permission are approved.

### 12.1 IAM and documentation

| Method and path | Operation ID | Permission / transport | Application contract or status |
|---|---|---|---|
| GET `/api/v1/iam/initialization` | `iam_get_initialization_v1` | no permission; pre-auth local-loopback policy; exact Origin when present; rate limited | M01 `GetIamInitializationStateV1` |
| POST `/api/v1/session` | `iam_login_v1` | no permission; pre-auth exact-Origin policy; rate limited; no CSRF before session | M01 `AuthenticateAdministratorV1` |
| GET `/api/v1/session` | `iam_get_current_session_v1` | proposed `read:self`; browser cookie only; permission sync required | M01 `ResolveBrowserSessionV1` |
| DELETE `/api/v1/session` | `iam_logout_v1` | proposed `write:self` + browser cookie + CSRF + current session ETag; permission sync required | M01 `LogoutSessionV1` |
| PATCH `/api/v1/session/password` | `iam_change_password_v1` | proposed `write:self` + browser cookie + CSRF + idempotency + `If-Match`; permission sync required | M01 `ChangeAdministratorPasswordV1` |
| GET `/api/v1/iam/sessions` | `iam_list_sessions_v1` | proposed `write:sessions`; browser cookie only; bearer excluded; permission sync required | M01 `ListSessionsV1` |
| DELETE `/api/v1/iam/sessions/{session_id}` | `iam_revoke_session_v1` | proposed `write:sessions` + browser cookie + CSRF + `If-Match`; permission sync required | M01 `RevokeSessionV1` |
| POST `/api/v1/iam/session-revocations` | `iam_revoke_other_sessions_v1` | proposed `write:sessions` + browser cookie + idempotency + CSRF; permission sync required | M01 `RevokeAllSessionsV1` |
| GET `/api/v1/api-tokens` | `iam_list_api_tokens_v1` | `write:tokens` | M01 `ListApiTokensV1` |
| POST `/api/v1/api-tokens` | `iam_create_api_token_v1` | `write:tokens` + idempotency + CSRF for cookie | M01 `CreateApiTokenV1`; plaintext appears once; `no-store` |
| POST `/api/v1/api-tokens/{token_id}/rotations` | `iam_rotate_api_token_v1` | `write:tokens` + idempotency + CSRF for cookie + `If-Match` | M01 `RotateApiTokenV1`; replay is 409, never plaintext replay |
| DELETE `/api/v1/api-tokens/{token_id}` | `iam_revoke_api_token_v1` | `write:tokens` + CSRF for cookie + `If-Match` | M01 `RevokeApiTokenV1` |
| GET `/api/v1/iam/security-events` | `iam_list_security_events_v1` | `read:diagnostics` | M01 `ListIamSecurityEventsV1` |

The login response uses 204 and sets cookies; it never returns the password, password hash, session secret, or CSRF truth. Token create/rotate responses are `Cache-Control: no-store, private` and must not be retrievable again.

There is no HTTP administrator bootstrap or password-recovery operation. An uninitialized installation exposes only the approved coarse initialization state and directs the local owner to the protected native runbook. Bootstrap and recovery stay local, exclusive, and outside P01.

Runtime documentation transports `GET /docs`, `GET /redoc`, `GET /openapi.json`, and `GET /problems/{closed_safe_code}` are protected by cookie or bearer authentication after initialization. They are framework transports, not CTR-API-001 resource operations, do not receive OpenAPI operation IDs, and are excluded from the generated resource client. The problem page renders only allowlisted local code/title text with a restrictive CSP; unknown codes return a safe 404 without reflecting the path segment.

### 12.2 Organization, account, discovery, profile, and resource registry

| Method and path | Operation ID | Permission | Application contract or status |
|---|---|---|---|
| GET `/api/v1/organizations` | `registry_list_organizations_v1` | `read:accounts` | M02 `ListOrganizationsV1` |
| POST `/api/v1/organizations` | `registry_create_organization_v1` | `write:accounts` + idempotency | M02 `CreateOrganizationV1` |
| GET `/api/v1/organizations/{organization_id}` | `registry_get_organization_v1` | `read:accounts` | M02 `GetOrganizationV1` |
| PATCH `/api/v1/organizations/{organization_id}` | `registry_rename_organization_v1` | `write:accounts` + `If-Match` | M02 `RenameOrganizationV1`; body is name-only |
| POST `/api/v1/organization-orderings` | `registry_reorder_organizations_v1` | `write:accounts` + idempotency | M02 `ReorderOrganizationsV1` |
| POST `/api/v1/organizations/{organization_id}/archivals` | `registry_archive_organization_v1` | `write:accounts` + idempotency + `If-Match` | M02 `ArchiveOrganizationV1` |
| DELETE `/api/v1/organizations/{organization_id}/archival` | `registry_restore_organization_v1` | `write:accounts` + `If-Match` | M02 `RestoreOrganizationV1` |
| GET `/api/v1/accounts` | `registry_list_accounts_v1` | `read:accounts` | M02 `ListAccountsV1` |
| POST `/api/v1/accounts` | `registry_register_account_v1` | `write:accounts` + idempotency | M02 `RegisterAccountV1` |
| GET `/api/v1/accounts/{account_id}` | `registry_get_account_v1` | `read:accounts` | M02 `GetAccountV1` |
| PATCH `/api/v1/accounts/{account_id}` | `registry_rename_account_v1` | `write:accounts` + `If-Match` | M02 `RenameAccountV1`; body is friendly-name-only |
| PUT `/api/v1/accounts/{account_id}/organization` | `registry_assign_account_organization_v1` | `write:accounts` + `If-Match` | M02 `AssignAccountOrganizationV1` |
| PUT `/api/v1/accounts/{account_id}/monitoring` | `registry_set_account_monitoring_v1` | `write:accounts` + `If-Match` | M02 `SetAccountMonitoringV1` |
| POST `/api/v1/accounts/{account_id}/archivals` | `registry_archive_account_v1` | `write:accounts` + idempotency + `If-Match` | M02 `ArchiveAccountV1` |
| DELETE `/api/v1/accounts/{account_id}/archival` | `registry_restore_account_v1` | `write:accounts` + `If-Match` | M02 `RestoreAccountV1` |
| GET `/api/v1/providers` | `registry_list_providers_v1` | `read:accounts` | M03 CTR-PROV-002 `ListProviderCapabilitiesV1`; safe provider-definition projection only |
| GET `/api/v1/providers/{provider_key}` | `registry_get_provider_v1` | `read:accounts` | M03 CTR-PROV-002 `GetProviderCapabilitiesV1`; safe provider-definition projection only |
| GET `/api/v1/provider-installations` | `registry_list_provider_installations_v1` | `read:accounts` | M02 `ListProviderInstallationsV1` |
| GET `/api/v1/provider-installations/{installation_id}` | `registry_get_provider_installation_v1` | `read:accounts` | M02 `GetProviderInstallationV1` |
| GET `/api/v1/discovery-candidates` | `registry_list_discovery_candidates_v1` | `read:accounts` | M02 `ListDiscoveryCandidatesV1` |
| GET `/api/v1/discovery-candidates/{candidate_id}` | `registry_get_discovery_candidate_v1` | `read:accounts` | M02 `GetDiscoveryCandidateV1` |
| POST `/api/v1/discovery-candidates/{candidate_id}/confirmations` | `registry_confirm_discovery_candidate_v1` | `write:accounts` + idempotency + current candidate/evidence version | M02 `ConfirmIdentityAssociationV1` |
| POST `/api/v1/identity-associations/{decision_id}/invalidations` | `registry_invalidate_identity_association_v1` | `write:accounts` + idempotency + `If-Match` | M02 `InvalidateIdentityAssociationV1` |
| GET `/api/v1/accounts/{account_id}/profiles` | `registry_list_account_profiles_v1` | `read:accounts` | M02 CTR-REG-003 `ListMonitoringProfilesV1` |
| GET `/api/v1/accounts/{account_id}/profiles/{profile_id}` | `registry_get_account_profile_v1` | `read:accounts` | M02 CTR-REG-003 `GetMonitoringProfileV1` |
| PUT `/api/v1/accounts/{account_id}/profiles/{profile_id}/lifecycle` | `registry_set_profile_lifecycle_v1` | `write:accounts` + `If-Match` | M02 `SetMonitoringProfileLifecycleV1` |
| GET `/api/v1/accounts/{account_id}/resources` | `registry_list_account_resources_v1` | `read:accounts` | M02 `ListAccountResourcesV1` |
| GET `/api/v1/accounts/{account_id}/resources/{resource_id}` | `registry_get_account_resource_v1` | `read:accounts` | M02 `GetAccountResourceV1` |
| GET `/api/v1/registry-events` | `registry_list_events_v1` | `read:diagnostics`; permission sync required | M02 `ListRegistryChangesV1` |

No registry response contains raw file locators, provider credential material, OAuth tokens, authentication codes, arbitrary environment values, or discovery evidence that could disclose them.

### 12.3 Provider capabilities and reauthentication

| Method and path | Operation ID | Permission | Application contract or status |
|---|---|---|---|
| GET `/api/v1/providers/{provider_key}/capabilities` | `provider_get_capabilities_v1` | `read:status` | M03 CTR-PROV-002 `GetProviderCapabilitiesV1`; side-effect-free safe projection only |
| GET `/api/v1/provider-installations/{installation_id}/compatibility` | `provider_get_compatibility_v1` | `read:status` | M03 CTR-PROV-002 `GetProviderCompatibilityV1`; side-effect-free safe projection only |
| POST `/api/v1/accounts/{account_id}/profiles/{profile_id}/reauthentication-requests` | `provider_request_reauthentication_v1` | `write:reauth` + idempotency | M02 CTR-REG-008 `StartReauthenticationRequestV1` |
| GET `/api/v1/reauthentication-requests/{request_id}` | `provider_get_reauthentication_request_v1` | `write:reauth` | M02 CTR-REG-008 `GetReauthenticationRequestV1` |
| DELETE `/api/v1/reauthentication-requests/{request_id}` | `provider_cancel_reauthentication_request_v1` | `write:reauth` + idempotency + `If-Match` | M02 CTR-REG-008 `CancelReauthenticationRequestV1` |

P01 consumes only the two safe M03 query ports and the three M02 CTR-REG-008
workflow ports above. It never imports or invokes
`ResolveProviderCapabilityV1`, `AssessProviderCompatibilityV1`,
`InvokeProviderCapabilityV1`, `ReauthenticationPortV1`, an auth-flow registry,
an extension registry, an adapter registry object, or an adapter implementation.
M02 coordinates reauthentication, M03 owns the provider flow protocol, and the
adapter executes the official managed-profile flow. P01 only maps transport. No
flow may overwrite, relocate, log out, or rewrite a user's protected/default
profile. The contract IDs are registered and Draft-aligned; implementation still
requires their explicit approval and the normal plan gate.

### 12.4 Collection control

| Method and path | Operation ID | Permission | Application contract or status |
|---|---|---|---|
| POST `/api/v1/collection-requests` | `collection_request_manual_run_v1` | proposed `write:collection` + idempotency | M04 `RequestManualCollectionV1`; 202 and `Location` |
| GET `/api/v1/collection-requests/{request_id}` | `collection_get_request_v1` | `read:telemetry` | M04 `GetCollectionRequestV1` |
| GET `/api/v1/collection-runs` | `collection_list_runs_v1` | `read:telemetry` | M04 `ListCollectionRunsV1` |
| GET `/api/v1/collection-runs/{run_id}` | `collection_get_run_v1` | `read:telemetry` | M04 `GetCollectionRunV1` |
| GET `/api/v1/accounts/{account_id}/latest-collection` | `collection_get_latest_account_run_v1` | `read:telemetry` | M04 `GetLatestCollectionRunV1` |
| GET `/api/v1/collection-health` | `collection_get_health_v1` | `read:status` | M04 `GetCollectorHealthV1` |

There is no public lease, cancellation, retry, scheduler, budget-counter, or run-state mutation route in V1. `write:collection` and CTR-COL-006 require contract-register approval before implementation.

### 12.5 Capacity, quota, budget, history, and forecast

| Method and path | Operation ID | Permission | Application contract or status |
|---|---|---|---|
| GET `/api/v1/accounts/{account_id}/capacity` | `capacity_get_account_v1` | `read:telemetry` | M05 `GetAccountCapacityV1` |
| GET `/api/v1/accounts/{account_id}/quotas` | `capacity_list_quota_windows_v1` | `read:telemetry` | M05 `ListQuotaWindowsV1` |
| GET `/api/v1/quotas/{quota_window_id}` | `capacity_get_quota_window_v1` | `read:telemetry` | M05 `GetQuotaWindowV1` |
| GET `/api/v1/accounts/{account_id}/budgets` | `capacity_list_budgets_v1` | `read:telemetry` | M05 `ListBudgetsV1` |
| GET `/api/v1/budgets/{budget_id}` | `capacity_get_budget_v1` | `read:telemetry` | M05 `GetBudgetV1` |
| GET `/api/v1/budgets/{budget_id}/usage-breakdowns` | `capacity_list_usage_breakdowns_v1` | `read:telemetry` | M05 `ListUsageBreakdownsV1` |
| GET `/api/v1/accounts/{account_id}/api-capacity` | `capacity_get_account_api_budget_v1` | `read:telemetry` | M05 `GetAccountApiCapacityV1` |
| GET `/api/v1/capacity/health` | `capacity_get_health_v1` | `read:status` | M05 `GetCapacityHealthV1` |
| GET `/api/v1/capacity/aggregate` | `capacity_get_aggregate_v1` | `read:telemetry` | M05 `GetCapacityAggregateV1` |
| GET `/api/v1/capacity/history` | `capacity_list_history_v1` | `read:telemetry` | M05 `ListCapacityHistoryV1` |
| GET `/api/v1/capacity/health-history` | `capacity_list_health_history_v1` | `read:telemetry` | M05 `ListCapacityHealthHistoryV1` |
| GET `/api/v1/capacity/forecasts` | `capacity_list_forecasts_v1` | `read:telemetry` | M05 `ListCapacityForecastsV1` |
| GET `/api/v1/capacity/forecasts/{forecast_id}` | `capacity_get_forecast_v1` | `read:telemetry` | M05 `GetCapacityForecastV1` |

The API cannot ingest samples, rebuild aggregates, purge history, or calculate normalization or forecasts. Confidence, provenance, staleness, unknown values, and source time are explicit response fields supplied by M05.

### 12.6 Runtime observation

| Method and path | Operation ID | Permission | Application contract or status |
|---|---|---|---|
| GET `/api/v1/processes` | `runtime_list_processes_v1` | `read:telemetry` | M06 `ListAgentProcessesV1` |
| GET `/api/v1/processes/{process_id}` | `runtime_get_process_v1` | `read:telemetry` | M06 `GetAgentProcessV1` |
| GET `/api/v1/processes/{process_id}/history` | `runtime_list_process_history_v1` | `read:telemetry` | M06 `ListProcessHistoryV1` |
| GET `/api/v1/sessions` | `runtime_list_sessions_v1` | `read:telemetry` | M06 `ListAgentSessionsV1` |
| GET `/api/v1/sessions/{session_id}` | `runtime_get_session_v1` | `read:telemetry` | M06 `GetAgentSessionV1` |
| GET `/api/v1/sessions/{session_id}/history` | `runtime_list_session_history_v1` | `read:telemetry` | M06 `ListRuntimeHistoryV1` filtered to session |
| GET `/api/v1/sessions/{session_id}/tree` | `runtime_get_session_tree_v1` | `read:telemetry` | M06 `GetSessionTreeV1` |
| GET `/api/v1/session-roots` | `runtime_list_session_roots_v1` | `read:telemetry` | M06 `ListSessionRootsV1` |
| GET `/api/v1/runtime-state-history` | `runtime_list_state_history_v1` | `read:telemetry` | M06 `GetRuntimeStateHistoryV1` bounded history query |
| GET `/api/v1/correlation-decisions` | `runtime_list_correlation_decisions_v1` | `read:diagnostics` | M06 `ListSessionCorrelationDecisionsV1` |
| GET `/api/v1/correlation-decisions/{decision_id}` | `runtime_get_correlation_decision_v1` | `read:diagnostics` | M06 `GetSessionCorrelationDecisionV1` |
| POST `/api/v1/correlation-decisions/{decision_id}/confirmations` | `runtime_confirm_correlation_decision_v1` | proposed `write:configuration` + idempotency + `If-Match` | M06 `ConfirmSessionAccountCorrelationV1`; permission sync required |
| POST `/api/v1/correlation-decisions/{decision_id}/invalidations` | `runtime_invalidate_correlation_decision_v1` | proposed `write:configuration` + idempotency + `If-Match` | M06 `InvalidateSessionAccountCorrelationV1`; permission sync required |
| GET `/api/v1/runtime-stall-policies/effective` | `runtime_get_effective_stall_policy_v1` | `read:telemetry` | M06 `GetEffectiveRuntimeStallPolicyV1` |
| PUT `/api/v1/runtime-stall-policies/{scope}` | `runtime_set_stall_policy_v1` | proposed `write:configuration` + idempotency + `If-Match` | M06 `SetRuntimeStallPolicyV1`; scope grammar is contract-owned |
| DELETE `/api/v1/runtime-stall-policies/{scope}` | `runtime_delete_stall_policy_v1` | proposed `write:configuration` + idempotency + `If-Match` | M06 `DeleteRuntimeStallPolicyOverrideV1` |

There is no process scan trigger, signal, kill, restart, pause, resume, input injection, terminal control, or session switch route.

### 12.7 Alert rules, alerts, and dashboard notifications

| Method and path | Operation ID | Permission | Application contract or status |
|---|---|---|---|
| GET `/api/v1/alert-rules` | `alerts_list_rules_v1` | proposed `read:status`; permission sync required | M07 `ListAlertRulesV1` |
| POST `/api/v1/alert-rules` | `alerts_create_rule_v1` | `write:alerts` + idempotency | M07 `CreateAlertRuleV1` |
| GET `/api/v1/alert-rules/{rule_id}` | `alerts_get_rule_v1` | proposed `read:status`; permission sync required | M07 `GetAlertRuleV1` |
| PUT `/api/v1/alert-rules/{rule_id}` | `alerts_update_rule_v1` | `write:alerts` + `If-Match` | M07 `UpdateAlertRuleV1` |
| POST `/api/v1/alert-rules/{rule_id}/archivals` | `alerts_archive_rule_v1` | `write:alerts` + idempotency + `If-Match` | M07 `ArchiveAlertRuleOverrideV1` |
| GET `/api/v1/alert-rule-resolution` | `alerts_get_effective_rule_v1` | proposed `read:status`; permission sync required | M07 `ResolveEffectiveAlertRuleV1` |
| GET `/api/v1/alerts` | `alerts_list_alerts_v1` | proposed `read:status`; permission sync required | M07 `ListAlertsV1` |
| GET `/api/v1/alerts/{alert_id}` | `alerts_get_alert_v1` | proposed `read:status`; permission sync required | M07 `GetAlertV1` |
| GET `/api/v1/alerts/{alert_id}/history` | `alerts_list_alert_history_v1` | proposed `read:status`; permission sync required | M07 `ListAlertHistoryV1` |
| POST `/api/v1/alerts/{alert_id}/acknowledgements` | `alerts_acknowledge_v1` | `write:alerts` + idempotency + `If-Match` | M07 `AcknowledgeAlertV1` |
| PUT `/api/v1/alerts/{alert_id}/snooze` | `alerts_snooze_v1` | `write:alerts` + `If-Match` | M07 `SnoozeAlertV1` |
| DELETE `/api/v1/alerts/{alert_id}/snooze` | `alerts_unsnooze_v1` | `write:alerts` + `If-Match` | M07 `UnsnoozeAlertV1` |
| GET `/api/v1/notifications` | `alerts_list_notifications_v1` | proposed `read:status`; permission sync required | M07 `ListDashboardNotificationsV1` |
| GET `/api/v1/notification-counts` | `alerts_get_notification_counts_v1` | proposed `read:status`; permission sync required | M07 `GetDashboardNotificationCountsV1` |
| POST `/api/v1/notifications/{notification_id}/read-receipts` | `alerts_mark_notification_read_v1` | `write:alerts` + idempotency + `If-Match` | M07 `MarkAlertReadV1` |
| DELETE `/api/v1/notifications/{notification_id}/read-receipt` | `alerts_mark_notification_unread_v1` | `write:alerts` + idempotency + `If-Match` | M07 CTR-ALERT-005 `MarkAlertUnreadV1`; optional Draft-aligned workflow |
| POST `/api/v1/notification-read-batches` | `alerts_mark_visible_notifications_read_v1` | `write:alerts` + idempotency | M07 `MarkVisibleNotificationsReadV1` |

V1 exposes dashboard notifications only. It does not send native Linux notifications, email, or messenger messages.

### 12.8 Operations, backup, diagnostics, and export

| Method and path | Operation ID | Permission | Application contract or status |
|---|---|---|---|
| GET `/api/v1/health` | `operations_get_health_v1` | `read:status` | M08 `GetHealthV1` |
| GET `/api/v1/liveness` | `operations_get_liveness_v1` | `read:status` | M08 `GetLivenessV1` through authenticated V1 transport |
| GET `/api/v1/readiness` | `operations_get_readiness_v1` | `read:status` | M08 `GetReadinessV1` |
| GET `/api/v1/version` | `operations_get_version_v1` | `read:status` | M08 `GetVersionInventoryV1`; M08 consumes build metadata behind its port |
| GET `/api/v1/settings` | `operations_get_safe_settings_v1` | `read:diagnostics` | M08 CTR-OPS-004 `GetSafeSettingsV1`; safe read-only projection, no generic mutation |
| GET `/api/v1/backups` | `operations_list_backups_v1` | `read:status` | M08 `ListBackupsV1` |
| POST `/api/v1/backups` | `operations_create_backup_v1` | `write:backup` + idempotency | M08 `RequestManualBackupV1`; 202 and `Location` |
| GET `/api/v1/backups/{backup_id}` | `operations_get_backup_v1` | `read:status` | M08 `GetBackupV1` |
| POST `/api/v1/backups/{backup_id}/verifications` | `operations_verify_backup_v1` | proposed `write:backup` + idempotency; transport approval required | M08 `VerifyBackupV1`; response timing/status must synchronize; no invented job resource |
| GET `/api/v1/diagnostics` | `operations_get_diagnostics_v1` | `read:diagnostics` | M08 `GetDiagnosticSummaryV1` |
| POST `/api/v1/diagnostic-bundles` | `operations_create_diagnostic_bundle_v1` | `read:diagnostics` + idempotency | M08 `RequestDiagnosticBundleV1`; 202 and `Location` |
| GET `/api/v1/diagnostic-bundles/{bundle_id}` | `operations_get_diagnostic_bundle_v1` | `read:diagnostics` | M08 `GetDiagnosticBundleJobV1` |
| GET `/api/v1/operations/audit-events` | `operations_list_audit_events_v1` | `read:diagnostics` | M08 `GetProductAuditPageV1`; merged safe M08/M01 view |
| GET `/api/v1/exports` | `operations_list_exports_v1` | `read:diagnostics` | M08 `ListExportJobsV1` |
| POST `/api/v1/exports` | `operations_create_export_v1` | proposed `write:exports` + idempotency | M08 `RequestOperationalExportV1`; 202 and `Location`; permission sync required |
| GET `/api/v1/exports/{export_id}` | `operations_get_export_v1` | `read:diagnostics` | M08 `GetExportJobV1` |
| GET `/api/v1/artifacts/{artifact_id}/content` | `operations_download_artifact_v1` | `read:diagnostics` | M08 `OpenArtifactDownloadV1`; the port authorizes type/subject/state and returns a bounded stream handle |
| DELETE `/api/v1/exports/{export_id}` | `operations_expire_export_v1` | proposed `write:exports` + idempotency + `If-Match` | M08 `ExpireArtifactV1` |

There is no HTTP restore endpoint, retention-policy execution endpoint, raw backup-file path, arbitrary download path, or deletion endpoint for backup material in V1.

### 12.9 Success status and schema catalog

The following are the proposed exact CTR-API-001 component names. They are transport schemas mapped field-for-field from the named application DTOs; they are not substitutes for those contracts. A name containing an unresolved upstream concept remains Draft until section 24 synchronization. Every operation also declares the applicable `SafeProblemV1` responses and common headers.

| Operation ID or operation set | Request component | Success status and response component |
|---|---|---|
| `iam_get_initialization_v1` | none | 200 `IamInitializationStateV1` |
| `iam_login_v1` | `LoginInputV1` | 204, session and CSRF cookies, no body |
| `iam_get_current_session_v1` | none | 200 `CurrentSessionViewV1` + ETag |
| `iam_logout_v1` | none | 204, cookies cleared |
| `iam_change_password_v1` | `ChangeAdministratorPasswordInputV1` | 204, rotated cookies, no body |
| `iam_list_sessions_v1` | query only | 200 `BrowserSessionPageV1` |
| `iam_revoke_session_v1` | none | 204 |
| `iam_revoke_other_sessions_v1` | `RevokeSessionsInputV1` | 200 `SessionRevocationSummaryV1` |
| `iam_list_api_tokens_v1` | query only | 200 `ApiTokenPageV1` |
| `iam_create_api_token_v1` | `CreateApiTokenInputV1` | 201 `ApiTokenCredentialIssueV1` + no-store; M2 no-`Location` exception in §8.1 |
| `iam_rotate_api_token_v1` | `RotateApiTokenInputV1` | 201 `ApiTokenCredentialIssueV1` + no-store; M2 no-`Location` exception in §8.1 |
| `iam_revoke_api_token_v1` | none | 204 |
| `iam_list_security_events_v1` | query only | 200 `IamSecurityEventPageV1` |
| `registry_list_organizations_v1` | query only | 200 `OrganizationPageV1` |
| `registry_create_organization_v1` | `CreateOrganizationInputV1` | 201 `OrganizationViewV1` + Location + ETag |
| `registry_get_organization_v1`, `registry_rename_organization_v1` | none / `RenameOrganizationInputV1` | 200 `OrganizationViewV1` + ETag |
| `registry_reorder_organizations_v1` | `ReorderOrganizationsInputV1` | 200 `OrganizationOrderingViewV1` + ETag |
| `registry_archive_organization_v1`, `registry_restore_organization_v1` | `ArchiveOrganizationInputV1` / none | 200 `OrganizationViewV1` + ETag |
| `registry_list_accounts_v1` | query only | 200 `AccountPageV1` |
| `registry_register_account_v1` | `RegisterAccountInputV1` | 201 `AccountViewV1` + Location + ETag |
| `registry_get_account_v1`, `registry_rename_account_v1` | none / `RenameAccountInputV1` | 200 `AccountViewV1` + ETag |
| `registry_assign_account_organization_v1` | `AssignAccountOrganizationInputV1` | 200 `AccountViewV1` + ETag |
| `registry_set_account_monitoring_v1` | `SetAccountMonitoringInputV1` | 200 `AccountViewV1` + ETag |
| `registry_archive_account_v1`, `registry_restore_account_v1` | `ArchiveAccountInputV1` / none | 200 `AccountViewV1` + ETag |
| `registry_list_providers_v1` | query only | 200 `ProviderDefinitionPageV1` |
| `registry_get_provider_v1` | none | 200 `ProviderDefinitionViewV1` |
| `registry_list_provider_installations_v1` | query only | 200 `ProviderInstallationPageV1` |
| `registry_get_provider_installation_v1` | none | 200 `ProviderInstallationViewV1` + ETag |
| `registry_list_discovery_candidates_v1` | query only | 200 `DiscoveryCandidatePageV1` |
| `registry_get_discovery_candidate_v1` | none | 200 `DiscoveryCandidateViewV1` + ETag |
| `registry_confirm_discovery_candidate_v1` | `ConfirmIdentityAssociationInputV1` | 201 `IdentityAssociationDecisionViewV1` + Location + ETag |
| `registry_invalidate_identity_association_v1` | `InvalidateIdentityAssociationInputV1` | 200 `IdentityAssociationDecisionViewV1` + ETag |
| `registry_list_account_profiles_v1` | query only | 200 `MonitoringProfilePageV1` |
| `registry_get_account_profile_v1`, `registry_set_profile_lifecycle_v1` | none / `SetMonitoringProfileLifecycleInputV1` | 200 `MonitoringProfileViewV1` + ETag |
| `registry_list_account_resources_v1` | query only | 200 `AccountResourcePageV1` |
| `registry_get_account_resource_v1` | none | 200 `AccountResourceViewV1` + ETag |
| `registry_list_events_v1` | query only | 200 `RegistryChangePageV1` |
| `provider_get_capabilities_v1` | query only | 200 `ProviderCapabilityDeclarationPageV1` |
| `provider_get_compatibility_v1` | query only | 200 `ProviderCompatibilityAssessmentViewV1` |
| `provider_request_reauthentication_v1` | `RequestReauthenticationInputV1` | 202 `ReauthenticationRequestViewV1` + Location |
| `provider_get_reauthentication_request_v1` | none | 200 `ReauthenticationRequestViewV1` |
| `provider_cancel_reauthentication_request_v1` | none | 200 `ReauthenticationRequestViewV1` + ETag |
| `collection_request_manual_run_v1` | `RequestManualCollectionInputV1` | 202 `CollectionRequestAcceptedV1` + Location |
| `collection_get_request_v1` | none | 200 `CollectionRequestViewV1` |
| `collection_list_runs_v1` | query only | 200 `CollectionRunPageV1` |
| `collection_get_run_v1`, `collection_get_latest_account_run_v1` | none / query only | 200 `CollectionRunViewV1` |
| `collection_get_health_v1` | query only | 200 `CollectorHealthV1` |
| `capacity_get_account_v1` | query only | 200 `AccountCapacityViewV1` |
| `capacity_list_quota_windows_v1` | query only | 200 `QuotaWindowPageV1` |
| `capacity_get_quota_window_v1` | query only | 200 `QuotaWindowViewV1` |
| `capacity_list_budgets_v1` | query only | 200 `BudgetPageV1` |
| `capacity_get_budget_v1` | query only | 200 `BudgetViewV1` |
| `capacity_list_usage_breakdowns_v1` | query only | 200 `UsageBreakdownPageV1` |
| `capacity_get_account_api_budget_v1` | query only | 200 `AccountApiCapacityViewV1` |
| `capacity_get_health_v1` | query only | 200 `CapacityHealthViewV1` |
| `capacity_get_aggregate_v1` | query only | 200 `CapacityAggregateViewV1` |
| `capacity_list_history_v1` | query only | 200 `CapacityHistoryPageV1` |
| `capacity_list_health_history_v1` | query only | 200 `CapacityHealthHistoryPageV1` |
| `capacity_list_forecasts_v1` | query only | 200 `CapacityForecastPageV1` |
| `capacity_get_forecast_v1` | query only | 200 `CapacityForecastV1` |
| `runtime_list_processes_v1` | query only | 200 `AgentProcessPageV1` |
| `runtime_get_process_v1` | none | 200 `AgentProcessViewV1` |
| `runtime_list_process_history_v1` | query only | 200 `ProcessHistoryPageV1` |
| `runtime_list_sessions_v1` | query only | 200 `AgentSessionPageV1` |
| `runtime_get_session_v1` | none | 200 `AgentSessionViewV1` |
| `runtime_list_session_history_v1`, `runtime_list_state_history_v1` | query only | 200 `RuntimeHistoryPageV1` |
| `runtime_get_session_tree_v1` | query only | 200 `SessionTreeViewV1` |
| `runtime_list_session_roots_v1` | query only | 200 `SessionRootPageV1` |
| `runtime_list_correlation_decisions_v1` | query only | 200 `SessionCorrelationDecisionPageV1` |
| `runtime_get_correlation_decision_v1` | none | 200 `SessionCorrelationDecisionV1` + ETag |
| `runtime_confirm_correlation_decision_v1` | `ConfirmSessionCorrelationInputV1` | 200 `SessionCorrelationDecisionV1` + ETag |
| `runtime_invalidate_correlation_decision_v1` | `InvalidateSessionCorrelationInputV1` | 200 `SessionCorrelationDecisionV1` + ETag |
| `runtime_get_effective_stall_policy_v1` | query only | 200 `RuntimeStallPolicyViewV1` + ETag |
| `runtime_set_stall_policy_v1`, `runtime_delete_stall_policy_v1` | `SetRuntimeStallPolicyInputV1` / none | 200 `RuntimeStallPolicyViewV1` + ETag |
| `alerts_list_rules_v1` | query only | 200 `AlertRulePageV1` |
| `alerts_create_rule_v1` | `CreateAlertRuleInputV1` | 201 `AlertRuleViewV1` + Location + ETag |
| `alerts_get_rule_v1`, `alerts_update_rule_v1` | none / `UpdateAlertRuleInputV1` | 200 `AlertRuleViewV1` + ETag |
| `alerts_archive_rule_v1` | `ArchiveAlertRuleInputV1` | 200 `EffectiveAlertRuleResolutionV1` |
| `alerts_get_effective_rule_v1` | query only | 200 `EffectiveAlertRuleResolutionV1` |
| `alerts_list_alerts_v1` | query only | 200 `AlertPageV1` |
| `alerts_get_alert_v1` | none | 200 `AlertViewV1` + ETag |
| `alerts_list_alert_history_v1` | query only | 200 `AlertHistoryPageV1` |
| `alerts_acknowledge_v1`, `alerts_snooze_v1`, `alerts_unsnooze_v1` | action-specific closed input / none | 200 `AlertViewV1` + ETag |
| `alerts_list_notifications_v1` | query only | 200 `DashboardNotificationPageV1` |
| `alerts_get_notification_counts_v1` | query only | 200 `DashboardNotificationCountsV1` |
| `alerts_mark_notification_read_v1` | none | 200 `DashboardNotificationViewV1` + ETag |
| `alerts_mark_notification_unread_v1` | none | 200 `DashboardNotificationViewV1` + ETag |
| `alerts_mark_visible_notifications_read_v1` | `MarkVisibleNotificationsReadInputV1` | 200 `NotificationMutationSummaryV1` |
| `operations_get_health_v1` | query only | 200 `HealthViewV1` |
| `operations_get_liveness_v1` | none | 200 `LivenessViewV1` |
| `operations_get_readiness_v1` | query only | 200 `ReadinessViewV1`; unavailable readiness can use 503 with a safe problem and typed extension only if synchronized |
| `operations_get_version_v1` | query only | 200 `VersionInventoryViewV1` |
| `operations_get_safe_settings_v1` | query only | 200 `SafeSettingPageV1` |
| `operations_list_backups_v1` | query only | 200 `BackupPageV1` |
| `operations_create_backup_v1` | `RequestManualBackupInputV1` | 202 `BackupViewV1` + Location |
| `operations_get_backup_v1` | none | 200 `BackupViewV1` + ETag |
| `operations_verify_backup_v1` | `VerifyBackupInputV1` | synchronized M08 status, provisionally 200 `BackupViewV1` + ETag |
| `operations_get_diagnostics_v1` | query only | 200 `DiagnosticSummaryV1` |
| `operations_create_diagnostic_bundle_v1` | `RequestDiagnosticBundleInputV1` | 202 `DiagnosticBundleJobViewV1` + Location |
| `operations_get_diagnostic_bundle_v1` | none | 200 `DiagnosticBundleJobViewV1` |
| `operations_list_audit_events_v1` | query only | 200 `ProductAuditEventPageV1` |
| `operations_list_exports_v1` | query only | 200 `ExportJobPageV1` |
| `operations_create_export_v1` | `RequestOperationalExportInputV1` | 202 `ExportJobViewV1` + Location |
| `operations_get_export_v1` | none | 200 `ExportJobViewV1` + ETag |
| `operations_expire_export_v1` | `ExpireArtifactInputV1` | 200 `ExportJobViewV1` + ETag |
| `operations_download_artifact_v1` | none | 200 bounded M08-authorized artifact stream; approved media type, `Content-Disposition`, no-store, ETag |

An action-specific input may contain only the fields accepted by its application command. A combined “patch anything” schema, generic metadata dictionary, arbitrary setting key/value, or arbitrary action name is forbidden.

### 12.10 FR-SAFE-001 positive allowed-action inventory

This is the exact V1 unsafe-method allowlist. It is positive proof of what AgentMonitor may do, not merely an absence statement. The OpenAPI/source/runtime route set may contain no other POST, PUT, PATCH, or DELETE operation. Each listed route remains constrained to the single application port in sections 12.1–12.8 and cannot mutate a running agent.

| Allowed effect | Exact unsafe routes |
|---|---|
| Dashboard credential administration | POST `/api/v1/session`; DELETE `/api/v1/session`; PATCH `/api/v1/session/password`; DELETE `/api/v1/iam/sessions/{session_id}`; POST `/api/v1/iam/session-revocations`; POST `/api/v1/api-tokens`; POST `/api/v1/api-tokens/{token_id}/rotations`; DELETE `/api/v1/api-tokens/{token_id}` |
| Organization grouping metadata | POST `/api/v1/organizations`; PATCH `/api/v1/organizations/{organization_id}`; POST `/api/v1/organization-orderings`; POST `/api/v1/organizations/{organization_id}/archivals`; DELETE `/api/v1/organizations/{organization_id}/archival` |
| Account metadata and grouping | POST `/api/v1/accounts`; PATCH `/api/v1/accounts/{account_id}`; PUT `/api/v1/accounts/{account_id}/organization`; PUT `/api/v1/accounts/{account_id}/monitoring`; POST `/api/v1/accounts/{account_id}/archivals`; DELETE `/api/v1/accounts/{account_id}/archival` |
| Reviewed identity/profile metadata | POST `/api/v1/discovery-candidates/{candidate_id}/confirmations`; POST `/api/v1/identity-associations/{decision_id}/invalidations`; PUT `/api/v1/accounts/{account_id}/profiles/{profile_id}/lifecycle` |
| Guide managed-profile reauthentication through CTR-REG-008 | POST `/api/v1/accounts/{account_id}/profiles/{profile_id}/reauthentication-requests`; DELETE `/api/v1/reauthentication-requests/{request_id}` |
| Refresh telemetry through collection admission | POST `/api/v1/collection-requests` |
| Manage reviewed runtime correlation/configuration metadata | POST `/api/v1/correlation-decisions/{decision_id}/confirmations`; POST `/api/v1/correlation-decisions/{decision_id}/invalidations`; PUT `/api/v1/runtime-stall-policies/{scope}`; DELETE `/api/v1/runtime-stall-policies/{scope}` |
| Manage alert rules and dashboard-notification state | POST `/api/v1/alert-rules`; PUT `/api/v1/alert-rules/{rule_id}`; POST `/api/v1/alert-rules/{rule_id}/archivals`; POST `/api/v1/alerts/{alert_id}/acknowledgements`; PUT `/api/v1/alerts/{alert_id}/snooze`; DELETE `/api/v1/alerts/{alert_id}/snooze`; POST `/api/v1/notifications/{notification_id}/read-receipts`; DELETE `/api/v1/notifications/{notification_id}/read-receipt`; POST `/api/v1/notification-read-batches` |
| Local operational backup, diagnostics, and data export | POST `/api/v1/backups`; POST `/api/v1/backups/{backup_id}/verifications`; POST `/api/v1/diagnostic-bundles`; POST `/api/v1/exports`; DELETE `/api/v1/exports/{export_id}` |

AUTO-QUALITY and API-SAFE-001 compare this literal allowlist with both the source route registry and generated OpenAPI. A missing listed operation, an extra unsafe operation, or an operation whose application port/permission/auth/replay/error record differs is a release-blocking failure. FR-SAFE-002 remains the separate negative proof that kill, restart, pause, interrupt, input injection, in-process credential switching, and agent routing are absent from API, UI, CLI, permissions, configuration, dependencies, and runtime behavior.

## 13. Authentication, authorization, and browser security

### 13.1 Credential resolution

- M01 is the sole source of credential validity and permission decisions.
- A request may use exactly one credential class: browser session cookie or `Authorization: Bearer` token.
- Supplying both returns 400 `ambiguous_credentials`; the boundary never chooses one silently.
- Basic, Digest, query-string tokens, form tokens, URL credentials, and API keys in custom headers are unsupported.
- `LoginInputV1` contains one bounded `password` field only; the single-user V1 dashboard has no username or email login field.
- Bearer values, cookies, passwords, CSRF values, and one-time token plaintext are never logged.
- Authentication runs before resource lookup to prevent existence disclosure.
- Authorization uses the operation's exact matrix permission, not route-prefix inference.
- An endpoint with multiple permission alternatives must declare the alternatives explicitly in code and OpenAPI.

### 13.2 Browser session cookie

Proposed CTR-API-002 attributes, pending M01 synchronization:

- Session cookie: opaque, `HttpOnly`, `SameSite=Strict`, `Path=/`, no `Domain`.
- CSRF cookie: opaque, not `HttpOnly`, `SameSite=Strict`, `Path=/`, no `Domain`.
- In verified loopback plain-HTTP local mode, `Secure=false` is permitted only by the approved local deployment profile.
- Any TLS/remote profile requires `Secure=true`; remote deployment requires a separate threat-model and deployment approval.
- Logout and expiry clear cookies with attributes identical to those used when setting them.
- Responses that set, rotate, or clear authentication state use `Cache-Control: no-store`.

The exact cookie names, session idle and absolute limits, rotation behavior, and local-HTTP naming constraints remain owned by M01 and must be frozen before API implementation.

### 13.3 CSRF and Origin

- Cookie-authenticated POST, PUT, PATCH, and DELETE require a CSRF cookie plus equal `X-CSRF-Token` header, verified by M01 using constant-time comparison where applicable.
- Bearer-only requests do not require CSRF.
- Login has no pre-session CSRF token but requires exact canonical Origin and throttling.
- Unsafe cookie requests with absent, opaque, `null`, malformed, or noncanonical Origin fail.
- Cookie-authenticated GET/HEAD with an Origin header also requires the exact canonical Origin. A pure bearer request is Origin-independent, still requires the canonical Host and a valid scoped token, and never receives a CORS grant; this is the M2 Task 6 perimeter contract.
- State-changing requests using a simple content type are rejected; JSON content type remains required.
- CSRF failure is audited safely and returns a generic 403 without indicating which half failed.

### 13.4 Swagger, ReDoc, and OpenAPI

- Runtime `/docs`, `/redoc`, and `/openapi.json` require a valid browser session or bearer credential after initialization.
- Swagger advertises CTR-API-003 bearer authorization for API calls.
- Swagger `persistAuthorization` is false; no token is prepopulated or written to local storage.
- The locally pinned Swagger request transport is explicit: without an entered bearer token it includes the browser session and copies the CSRF cookie into `X-CSRF-Token` for unsafe calls; with a bearer token it sets fetch credentials to `omit` so the session cookie is not sent and the request is not rejected as ambiguous credentials.
- This Swagger transport behavior must pass real-browser tests. If a pinned Swagger version cannot omit cookies for bearer “Try it out”, select an approved compatible version or implement a small reviewed local request transport; disabling working bearer authorization is not an M2 acceptance substitute.
- Documentation HTML uses pinned local assets; no CDN scripts, fonts, telemetry, or external requests are permitted.
- Content Security Policy for documentation permits only the minimum local script/style assets and must not weaken normal UI policy globally.
- Build-time OpenAPI generation uses the production application factory in a controlled command and does not create a hidden unauthenticated runtime route.

## 14. Host, Origin, CORS, and transport split

### 14.1 Local V1 transport

- The deployment process binds only approved loopback addresses in local mode. P01 validates request authority; DEP/FND owns socket binding.
- `Host` must exactly match an approved host-and-port entry. Empty, multiple, malformed, user-info-bearing, Unicode-confusable, unexpected IPv6, and unapproved hosts fail before application invocation.
- The canonical browser Origin is one explicit configured origin, not a wildcard. Aliases are not inferred.
- `X-Forwarded-Host`, `X-Forwarded-Proto`, `Forwarded`, and client-IP forwarding headers are ignored in local mode; proxy trust is disabled.
- There is no permissive CORS middleware. Same-origin traffic needs no CORS headers; cross-origin preflight fails.
- WebSocket, server-sent event, HTTP/2 push, and unauthenticated LAN exposure are out of scope.
- Request timeouts, maximum body size, maximum header size/count, keep-alive limits, and concurrency protection require deployment-aligned bounded configuration.

### 14.2 Loopback probes versus authenticated API

The canonical product health, readiness, and version resources are authenticated `/api/v1` operations in section 12.8.

Unauthenticated `/livez` or `/readyz` endpoints outside `/api/v1` are not approved by this plan. API standards require an ADR for that exception, and even a minimal probe could disclose installation state. Until an ADR and security review approve the exact disclosure:

- native service supervision uses a local internal readiness mechanism from CTR-DEP/CTR-FND, not an undocumented HTTP bypass;
- P01 does not register public probe routes;
- browser UI and operator API clients use authenticated `/api/v1/health` and `/api/v1/readiness`.

Remote-server support is a later deployment profile. It requires TLS, proxy-boundary, trusted-forwarder, rate-limit, cookie, CORS, authentication, and multi-user threat-model decisions; toggling the bind host is not a supported remote deployment.

### 14.3 Response-header baseline

- Every response sets `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, a restrictive `Permissions-Policy`, and an approved same-origin resource policy.
- API JSON and problem responses use a CSP equivalent to `default-src 'none'; frame-ancestors 'none'` and cannot be framed.
- Swagger/ReDoc receive their own reviewed local-asset CSP, `frame-ancestors 'none'`, and `X-Frame-Options: DENY` for compatibility.
- Authentication/session/token responses and downloads use `Cache-Control: no-store, private`; other authenticated JSON uses the explicitly reviewed private-cache policy and never public caching.
- `Vary` is exact for any representation/auth behavior that actually varies; it never creates an Origin wildcard cache issue.
- The ASGI server suppresses product/framework version banners where supported. Application responses do not add a version-bearing `Server` header.
- HSTS is not emitted for plain-HTTP loopback V1 because it would be misleading. A future TLS deployment defines HSTS in its own approved transport profile.
- Redirects are absent from API operations except a separately documented fixed local documentation redirect. User-supplied redirect targets are forbidden.

## 15. OpenAPI contract quality

The generated OpenAPI document must:

- declare the approved OpenAPI 3.x version and `/api/v1` server/base behavior without embedding a machine-specific port;
- use every operation ID exactly once and preserve the matrix IDs;
- group operations by stable tags: `iam`, `registry`, `providers`, `collection`, `capacity`, `runtime`, `alerts`, and `operations`;
- declare bearer security globally or per operation and accurately document cookie transport without encouraging clients to send cookies as parameters;
- explicitly clear security only for approved pre-authentication initialization and login operations;
- define all request/response schemas under components with stable V1 names;
- document success status, `Location`, ETag, `If-Match`, `Idempotency-Key`, `Retry-After`, correlation header, cache policy, and relevant `SafeProblemV1` responses;
- distinguish nullable from optional properties;
- express bounds, formats, patterns, and enum values where they are public contract, without leaking secret-shaped examples;
- provide synthetic schema examples only, clearly non-live and never displayed as dashboard data;
- contain no local path, username, email address, hostname, account label, provider token, cookie, process command line, prompt, response, source content, or environment value;
- remain byte-for-byte deterministic for the same approved source and build metadata policy;
- pass schema validation, generated-client compilation, compatibility diff, and secrets/privacy scans.

Pydantic class names alone do not define the public contract. Schema aliases, validation, and serialization must be reviewed against CTR-API-001.

### 15.1 Exact OpenAPI security model

- `BearerTokenV1` is an HTTP `bearer` security scheme with `bearerFormat: opaque`; it never claims JWT semantics.
- `BrowserSessionCookieV1` is an `apiKey` security scheme in `cookie`. Its exact cookie `name` is frozen with M01 before generation.
- `BrowserCsrfHeaderV1` is an `apiKey` security scheme in `header` named `X-CSRF-Token`; it is used only in conjunction with `BrowserSessionCookieV1` on unsafe operations.
- Pre-authentication initialization and login declare `security: []` explicitly.
- Cookie-or-bearer reads declare two alternatives: browser session, or bearer token.
- Unsafe operations declare two alternatives: browser session plus CSRF as one combined requirement, or bearer token alone.
- OpenAPI HTTP-bearer requirement arrays remain empty as required by the format. The exact M01 permission appears in the operation description and machine-readable `x-agentmonitor-required-permission` extension; it is also checked against the matrix by AUTO-QUALITY.
- Cookie and CSRF schemes describe transport mechanics only. M01 remains the authority for session, proof, principal, and permission validity.
- `Idempotency-Key`, `If-Match`, `ETag`, `Location`, `Retry-After`, and `X-Correlation-ID` are reusable parameter/header components, not authentication schemes.
- The selected OpenAPI 3.x minor version is frozen by CTR-FND-005 after validator/generator compatibility evidence. P01 cannot change it locally to make a tool pass.

## 16. Generated-client ownership and handoff

- P01 owns API semantics and source route/schema definitions under CTR-API-001. It does not own or write the committed generated artifacts.
- Foundation owns only the deterministic OpenAPI/client generator mechanism, validation/diff plumbing, and artifact wiring through CTR-FND-005; it does not redefine API semantics.
- The integration steward is the sole writer of `contracts/openapi/agentmonitor-v1.json` and `frontend/src/generated/api/**` for an allocated integration wave. Neither P01, FND, route-family agents, nor P02 edits those generated outputs.
- P02 owns the wrapper/consumption layer under `frontend/src/shared/api/**` through CTR-UI-001 and may not hand-author a duplicate HTTP client or backend DTO.
- Generation occurs only after all route-family branches are integrated against one production composition root.
- The pipeline first verifies the existing artifacts are clean, generates to a temporary directory, validates, diffs, then atomically replaces approved artifacts. Failure leaves committed artifacts untouched.
- A clean regeneration must create no diff. Nondeterministic timestamps or machine paths are forbidden.
- The generated client must compile under the pinned frontend toolchain and make a real authenticated request to the running backend in contract tests.
- A UI build cannot pass against stale generated code: the embedded OpenAPI digest must match the generated-client digest.
- Exact output paths and generator selection remain CTR-FND-005 synchronization items; P01 must not invent an alternate generator.

## 17. Configuration contract

The following are proposed typed configuration concepts, not approved environment names until CTR-CONFIG synchronization:

| Concept | Validation and safe behavior |
|---|---|
| canonical public origin | Exactly one normalized loopback HTTP origin for local V1; no wildcard, path, query, fragment, or credentials |
| trusted hosts | Nonempty exact host-and-port allowlist consistent with the bind profile |
| API port | Integer 1–65535; nondefault value reflected consistently in Origin and service configuration |
| maximum JSON body bytes | Positive bounded integer; enforced before body parsing |
| default and maximum page size | Positive integers with default not exceeding maximum |
| request timeout | Positive bounded duration; long jobs must not raise it to job duration |
| concurrency ceiling | Positive bounded integer with documented overload response |
| documentation enabled | Boolean; disabling runtime docs does not disable artifact generation |
| local plain-HTTP cookie mode | Derived from approved deployment profile, not a casual boolean bypass |

Configuration loads once through the foundation configuration root and is injected. Invalid or inconsistent security configuration prevents startup with a safe diagnostic. No route reads `.env` directly, mutates `.env`, returns secret values, or exposes all configuration.

AgentMonitor-owned deployment secrets are supplied only through the approved foundation `.env` mechanism and represented as secret-presence state after loading. Provider OAuth/session credentials remain provider-managed and are never copied into `.env` by P01. Generated API tokens are shown once to the authorized caller and only their approved verifier form is persisted by M01; no endpoint writes plaintext tokens to `.env`.

## 18. Logging, audit, observability, and privacy

- Access logs contain timestamp, correlation ID, operation ID, method, normalized route template, safe outcome class, status, latency, response-size class, auth class, and principal category.
- Logs do not contain request/response bodies, query strings, raw paths with user-controlled identifiers, headers, cookies, bearer tokens, CSRF values, passwords, idempotency keys, emails, account labels, process command lines, provider payloads, prompts, responses, source content, local paths, or arbitrary environment data.
- Route-template logging occurs only after safe route matching. Unknown paths are logged as a constant category or bounded redacted form.
- Unexpected exceptions are logged through CTR-FND-004 with safe exception classification; stack traces remain restricted to approved local diagnostic sinks and are never returned.
- Security-relevant login, logout, token, session, CSRF, Origin, authorization, account mutation, alert mutation, collection request, backup, diagnostic, and export actions submit approved audit commands to their owning modules.
- Metrics, if later approved, use operation IDs and bounded outcome classes. IDs and labels are forbidden metric dimensions.
- Health/readiness outputs are safe typed projections. They cannot expose raw exception messages, paths, dependency URLs, secrets, or complete configuration.
- All API response projections remain operational metadata only. Prompt, response, tool activity, source code, arbitrary terminal content, and arbitrary process environment capture remain prohibited.

## 19. TDD implementation increments

Each increment follows red-green-refactor. The red command, expected failure, production change, green command, and evidence path are recorded before moving on. A test that did not fail for the intended missing behavior does not establish TDD evidence.

### API-I00 — contract and dependency synchronization

- Resolve every section 24 decision and contract-register gap.
- Adopt CAA-C02, CAA-C04, CAA-C07, and CAA-C12 in the synchronized contract baseline; this Draft text is not the approval record.
- Freeze the 43-operation positive action allowlist and seven deferred negative manifests before any route scaffolding.
- Freeze permission names, application port names, safe DTOs, config names, cookie attributes, output paths, and schema conventions.
- Obtain dependency/license approvals without installing anything during planning.
- Add executable architecture and planning checks before production routes.
- Exit: approved contracts and canonical commands exist; no production route yet.

### API-I01 — common problem, correlation, and representation core

- Red: real-server errors still use framework defaults; correlation is absent or malformed values pass.
- Green: `SafeProblemV1`, exception mapping, correlation validation/generation/response propagation, media rules, and security-neutral common schemas.
- Refactor only after all failure paths preserve correlation and safe bodies.

### API-I02 — transport perimeter

- Red: hostile Host/Origin, forwarded headers, oversize payloads, unsupported media, or cross-origin preflight reaches application code.
- Green: fail-closed Host/Origin/body/media/header policies and response security headers.
- Verify both IPv4 and available IPv6 loopback behavior on Linux; macOS evidence belongs to its platform plan.

### API-I03 — browser session and bearer transport

- Red: unauthenticated and ambiguous credential requests are accepted, or unsafe cookie requests bypass CSRF.
- Green: CTR-API-002/003 resolution, permission dependency, login/current session/logout/password routes, cookie attributes, CSRF, throttle integration, and safe auditing.
- No P01-owned credential validation or permission policy is allowed.

### API-I04 — API token and authenticated documentation flows

- Red: token plaintext is replayable/cacheable, docs are public, or Swagger persists authorization.
- Green: session/token administration routes, one-time-secret behavior, authenticated local docs assets, and exact OpenAPI security declarations.

### API-I05 — registry routes

- Red: real HTTP contract tests for organization, account, provider definition, installation, discovery candidate, profile, resource, and history routes fail because routes do not exist.
- Green: mapping-only handlers invoking M02 ports, with pagination, ETags, permissions, safe projections, and idempotency.

### API-I06 — provider capability and reauthentication routes

- Red only after the two Draft-aligned M03 safe query ports and M02 CTR-REG-008 are approved for implementation.
- Green: side-effect-free capability/compatibility query mappings and transport-only mapping of durable M02-owned reauthentication workflow resources.
- Stop if P01 would resolve/invoke a provider capability, assess compatibility through a command, import a provider flow/adapter, orchestrate M02/M03, or mutate a default provider profile.

### API-I07 — collection routes

- Red: manual request and run/status real-HTTP flows absent.
- Green: `write:collection` authorization, durable 202 resource mapping, collection histories, latest result, and health projection.
- Stop if idempotency ownership or CTR-COL-006 remains unapproved.

### API-I08 — capacity routes

- Red: quota, budget, aggregate, history, and forecast schemas fail contract checks.
- Green: read-only M05 query mappings with explicit unknown, stale, provenance, confidence, and time semantics.

### API-I09 — runtime routes

- Red: process/session/history/tree/correlation/stall-policy contract tests fail.
- Green: read-only observation projections and approved configuration mutations.
- Stop if any route would trigger scanning or process control.

### API-I10 — alert and notification routes

- Red: rule, alert lifecycle, notification counts, read state, ETag, and retry tests fail.
- Green: M07 mappings and dashboard-only notification surface.
- No email, desktop, or messenger delivery is added.

### API-I11 — operations routes

- Red: authenticated health/version/backup/diagnostic/audit/export real-HTTP contracts fail.
- Green: M08 mappings, safe artifact streaming, long-job resources, no-store downloads, and no restore endpoint.

### API-I12 — canonical OpenAPI and generated client

- Red: schema validation, operation-ID uniqueness, compatibility, deterministic regeneration, client compilation, or real client/server request fails.
- Green: integration steward uses the FND mechanism to write one canonical artifact/client pair from P01 semantics, then hands it to the P02 wrapper through CTR-FND-005/CTR-UI-001.

### API-I13 — browser, security, resilience, and performance closure

- Red: real browser CSRF/session/docs flows, adversarial cases, overload behavior, restart behavior, or latency criteria fail.
- Green: bounded fixes within P01; domain failures return to the owning module.
- Run the full canonical gate and create the required handoff and evidence documents.

## 20. Planned test inventory

All HTTP tests launch the production application through the production factory on an ephemeral loopback port and use a real HTTP client. They use a real migrated temporary SQLite database and real IAM/application services. No FastAPI `TestClient`, direct route invocation, dependency override, monkeypatch, mock, fake, stub, emulator, recorded response, seeded telemetry, demo account, or placeholder dashboard value qualifies.

Constructed input/output values are allowed only in pure tests without I/O. A real-boundary test may submit test-owned administrator passwords, organization names, and command inputs to production interfaces as the behavior under test, using an isolated real database; it may not inject constructed provider observations, capacity, processes, sessions, alerts, histories, or job results. Provider/runtime-derived data must come from the real authorized boundary. Test setup may not alter the user's real provider profiles or default AgentMonitor data.

Test expectations come from the approved contract/requirement and an independent client or validator. A test must not derive its expected operation ID, permission, JSON body, error code, or schema from the same production registry/serializer it is testing. Controlled negative changes prove architecture, compatibility, drift, secret, and skip detectors can fail. Coverage or a passing status without an observable behavioral assertion is not acceptance evidence.

Any `API-HTTP-*`, `API-BROWSER-*`, or `API-CLIENT-*` scenario that needs provider observations, runtime observations, generated alerts, history, backup artifacts, or export artifacts runs only after those values are produced by the real approved production path. In an environment without that prerequisite it is explicitly Not Run or Blocked and is completed in the owner-coordinated live phase; no fixture or seeded row substitutes for it.

### 20.1 Pure transport policy tests

- API-PURE-001: correlation validator accepts the exact allowed grammar and bounds.
- API-PURE-002: correlation validator rejects empty, oversized, control, whitespace, and Unicode values.
- API-PURE-003: cursor envelope rejects a query-binding mismatch.
- API-PURE-004: sort parser accepts only the endpoint allowlist and adds the documented tie-breaker.
- API-PURE-005: unknown filters fail rather than being ignored.
- API-PURE-006: ETag encoder/decoder round-trips approved versions and rejects weak/malformed values.
- API-PURE-007: SafeProblem mapping excludes exception strings and secret-shaped constructed values.
- API-PURE-008: response schema serialization preserves absent versus null semantics.
- API-PURE-009: operation registry has exactly one auth profile, permission, resource port, replay policy, success schema, and `SafeProblemV1` error schema for every matrix operation.
- API-PURE-010: import-policy graph rejects prohibited infrastructure and adapter imports.

### 20.2 Real running HTTP tests

- API-HTTP-001: initialization state is reachable under its exact pre-auth policy and leaks no detail.
- API-HTTP-002: login sets exact cookie/cache attributes and returns no credential body.
- API-HTTP-003: current session and logout work over a real cookie jar.
- API-HTTP-004: wrong password returns generic 401 `invalid_dashboard_credentials` and is safely throttled without colliding with either authentication-required code.
- API-HTTP-005: valid bearer token authorizes its allowed read operation.
- API-HTTP-006: insufficient bearer scope returns 403 and never invokes the target command.
- API-HTTP-007: cookie plus bearer returns `ambiguous_credentials`.
- API-HTTP-008: token creation/rotation returns plaintext once; a committed retry returns 409 `one_time_secret_not_replayable` with safe metadata and no secret.
- API-HTTP-009: session/token rotation or revocation is visible on the next real request.
- API-HTTP-010: organization create/get/list/rename/archive/restore maps status, ETag, and Location correctly.
- API-HTTP-011: account create/get/list/rename/assignment/monitoring/archive/restore maps M02 outcomes.
- API-HTTP-012: provider definitions and installation pages are deterministic and safe.
- API-HTTP-013: discovery confirmation conflict and stale ETag map to 409/412 safely.
- API-HTTP-014: profile and account-resource responses contain no raw locator or secret material.
- API-HTTP-015: the two capability/compatibility routes invoke only their single safe M03 query ports and return only approved projections; no assessment or provider invocation occurs.
- API-HTTP-016: reauthentication start/status/cancel invokes only CTR-REG-008, uses one durable M02-owned flow, handles restart truthfully, and never touches a protected/default profile from P01.
- API-HTTP-017: manual collection returns 202/Location and an idempotent retry does not duplicate work.
- API-HTTP-018: collection run pages and latest result preserve owner-supplied provenance and freshness.
- API-HTTP-019: quota and budget pages preserve unknown/unavailable values without coercing them to zero.
- API-HTTP-020: capacity aggregate/history/forecast filters, ordering, and cursors are deterministic.
- API-HTTP-021: process list/get/history returns approved operational metadata only.
- API-HTTP-022: session list/get/history/tree/root resources preserve safe hierarchy.
- API-HTTP-023: correlation confirmation/invalidation requires permission, idempotency, and current ETag.
- API-HTTP-024: stall-policy put/delete uses owner contract and stale writes return 412.
- API-HTTP-025: alert rule create/update/archive/effective resolution maps M07 outcomes.
- API-HTTP-026: alert acknowledge/snooze/unsnooze is idempotent and version-safe.
- API-HTTP-027: notification list/count/read/unread/batch flows are consistent after a real transaction.
- API-HTTP-028: authenticated health/readiness/version expose only the approved safe schema.
- API-HTTP-029: manual backup returns a durable 202 resource; backup verification uses the synchronized M08 status without inventing a job.
- API-HTTP-030: diagnostic bundle creation/status/download uses exact safe media and no-store headers.
- API-HTTP-031: audit-event pagination never exposes raw secret or request-body data.
- API-HTTP-032: export creation/status/download/expiry is authorized, bounded, and version-safe.
- API-HTTP-033: every list rejects invalid limit, cursor, filter, and sort with SafeProblem.
- API-HTTP-034: every response category includes the same valid correlation ID.
- API-HTTP-035: framework 404, 405, 413, 415, 422, and unexpected 500 use SafeProblem and security headers.
- API-HTTP-036: unsupported process-control and restore paths return 404 and no application mutation.
- API-HTTP-037: restart preserves durable idempotency results and invalidates only state the owner contract says is ephemeral.
- API-HTTP-038: artifact range/stream behavior, disconnect handling, and filenames remain bounded and safe.
- API-HTTP-039: absent/expired/revoked dashboard credentials return 401 `dashboard_authentication_required` and the approved dashboard-login recovery contract.
- API-HTTP-040: a real provider reauthentication-needed state returns 409 `provider_reauthentication_required`; the same dashboard session remains valid on the next authorized dashboard request.
- API-HTTP-041: a committed password-change retry with the revoked old cookie returns 401 `dashboard_authentication_required` before receipt lookup; after fresh login, a retry with current Origin/session/CSRF/permission and the same key returns 409 `one_time_secret_not_replayable` before stale precondition/password evaluation, never a replayed session/CSRF credential or retained password.

### 20.3 OpenAPI contract tests

- API-OAPI-001: generated OpenAPI validates against the approved OpenAPI schema.
- API-OAPI-002: every matrix path/method and only approved path/method pairs exist.
- API-OAPI-003: every operation ID is present, unique, and equal to the matrix value.
- API-OAPI-004: public initialization/login operations and authenticated operations declare exact security.
- API-OAPI-005: every operation declares exact auth profile, permission, application port, replay policy, precondition/idempotency headers, success schema, and `SafeProblemV1`; one-time-secret operations document their non-replayable 409.
- API-OAPI-006: all list operations use named page schemas with bounded limit/cursor/filter/sort documentation.
- API-OAPI-007: all errors reference `SafeProblemV1` with `application/problem+json`; dashboard-auth and provider-reauth problems have distinct documented codes/statuses.
- API-OAPI-008: long operations declare 202, Location, durable status schema, and safe failures.
- API-OAPI-009: artifact generation is byte-for-byte deterministic in a clean checkout.
- API-OAPI-010: compatibility diff rejects a deliberately breaking fixture and accepts an approved additive fixture.
- API-OAPI-011: artifact privacy scan finds no real machine, account, process, path, email, or secret material.
- API-OAPI-012: schemas distinguish required, optional, and nullable properties and preserve enum wire values.

### 20.4 Generated-client tests

- API-CLIENT-001: the pinned generator consumes the canonical artifact without warnings treated as ignorable.
- API-CLIENT-002: the generated TypeScript client compiles under the pinned frontend toolchain.
- API-CLIENT-003: clean regeneration produces no diff and matching OpenAPI/client digest.
- API-CLIENT-004: generated login/session client performs a real browser-compatible flow against the running server.
- API-CLIENT-005: generated paginated capacity client follows a real cursor without reordering or data loss.
- API-CLIENT-006: generated error typing decodes SafeProblem, preserves correlation ID, and distinguishes dashboard login recovery from provider reauthentication guidance.
- API-CLIENT-007: generated client sends bearer auth without CSRF and cookie mutation with CSRF.
- API-CLIENT-008: deprecated operation metadata is preserved by the selected generator.

### 20.5 Real browser tests

- API-BROWSER-001: a real browser logs in, receives cookies, and loads an authenticated API-backed shell.
- API-BROWSER-002: cookie mutation without CSRF fails; the same generated-client mutation with CSRF succeeds.
- API-BROWSER-003: logout clears cookies and protected navigation/request returns 401.
- API-BROWSER-004: Swagger, ReDoc, and OpenAPI are inaccessible before authentication.
- API-BROWSER-005: authenticated Swagger loads only local assets, supports session+CSRF calls, omits cookies for entered-bearer calls, and persists no bearer token after reload.
- API-BROWSER-006: a cross-origin browser page cannot read or mutate the API.
- API-BROWSER-007: browser history, URL, storage, console, and rendered errors contain no password/token/CSRF secret.
- API-BROWSER-008: 1920×1080 dashboard traffic uses only `/api/v1` and the generated client.
- API-BROWSER-009: narrow responsive traffic does not call alternate/private backend routes.
- API-BROWSER-010: simultaneous tabs observe session revocation and notification read state consistently.

### 20.6 Security and privacy tests

- API-SEC-001: unapproved Host values, duplicate Host, and host confusion are rejected before application invocation.
- API-SEC-002: foreign, absent-on-unsafe, `null`, and malformed Origin values are rejected.
- API-SEC-003: cross-origin OPTIONS receives no permissive CORS grant.
- API-SEC-004: forwarded authority/protocol headers cannot change trust decisions.
- API-SEC-005: CSRF mismatch, missing halves, rotation, and session binding fail generically.
- API-SEC-006: Basic/query/custom-header credentials are never accepted.
- API-SEC-007: authentication precedes object lookup and prevents existence enumeration.
- API-SEC-008: oversized headers/body, deeply nested JSON, huge page sizes, and long search terms fail within bounds.
- API-SEC-009: traversal, encoded separators, duplicate query keys, invalid Unicode, and content-type confusion cannot select files or routes.
- API-SEC-010: error and access logs contain none of the submitted secret canaries.
- API-SEC-011: schema/docs/generated-client artifacts contain none of the live-data canaries.
- API-SEC-012: response security headers cover success, error, docs, and download responses.
- API-SEC-013: artifact downloads cannot address arbitrary paths and use safe filenames.
- API-SEC-014: request smuggling-relevant duplicate content-length/transfer semantics are rejected by the deployed server stack.
- API-SEC-015: no registered route controls processes, executes restore, reads arbitrary files, or exposes prompts/responses/tool activity.
- API-SEC-016: local-mode startup rejects wildcard/non-loopback trust configuration.
- API-SEC-017: API token attenuation prevents a bearer token from escalating its own scope.
- API-SEC-018: idempotency keys are principal/operation/body-bound and do not cross accounts.
- API-SEC-019: P01 imports only safe provider capability/compatibility query symbols and CTR-REG-008; provider invocation, assessment commands, flow protocol, adapters, and orchestration symbols fail the source/import gate.
- API-SAFE-001: source registry, running route table, and generated OpenAPI unsafe-method sets equal the 43-entry section 12.10 allowlist exactly; no extra or missing action exists.
- API-SAFE-002: every allowed action has exactly one resource application port, M01 permission, auth profile, replay policy, success schema, and `SafeProblemV1` error schema; a controlled missing/duplicate mapping makes AUTO-QUALITY fail.
- API-SAFE-003: real authorized HTTP exercises every locally available allowed action through its production application port; a live-dependent action remains separately Blocked/Not Run rather than being simulated.
- API-SAFE-004: source/import/permission/config/OpenAPI/generated-client/runtime scans plus negative HTTP probes prove the FR-SAFE-002 kill/restart/pause/interrupt/input-injection/in-process-credential-switch/routing surface is absent.

### 20.7 Resilience and performance tests

- API-PERF-001: representative cached/local read endpoints meet NFR-PERF-001 under the approved machine/profile and record percentiles.
- API-PERF-002: bounded concurrent list and long-job submission load produces controlled 429/503 behavior, not corruption.
- API-PERF-003: disconnecting a client does not cancel committed application work or leak a task.
- API-PERF-004: slow download and slow request-body behavior respect timeouts and memory bounds.
- API-RES-001: database/application unavailability maps to safe readiness and 503 responses without credential leakage.
- API-RES-002: server restart during a long job preserves owner-defined durable status.
- API-RES-003: malformed application results fail closed rather than serializing partial unsafe data.

### 20.8 Automation tests

- API-AUTO-001: the API test command really starts and probes the production server.
- API-AUTO-002: the OpenAPI generation command fails without the required production composition/configuration.
- API-AUTO-003: compatibility enforcement fails for an unapproved breaking artifact.
- API-AUTO-004: generated-client drift makes the quality/build gate fail.
- API-AUTO-005: documentation checks fail on a missing operation, schema, permission, or contract link.
- API-AUTO-006: architecture checks fail on a deliberately prohibited API import fixture.
- API-AUTO-007: skipped or deselected required API tests make the completion gate fail.
- API-AUTO-008: evidence metadata records command, exit status, environment class, and artifact digest.
- API-AUTO-009: an attempted P01/FND/P02 write to generated OpenAPI/client outputs fails ownership validation; only the allocated integration steward may write them for the wave.

### 20.9 Owner-coordinated live-path tests

These tests traverse P01 through the real integrated modules to real user-authorized systems. P01 still calls only application contracts. The owner supplies credentials through the approved local mechanism, never source, fixtures, logs, evidence, screenshots, chat, or command-line arguments. An unavailable account or owner window is recorded as Blocked or Not Run, never simulated and never passed.

- API-LIVE-001: an enrolled real Claude subscription account is collected through the production path and its safe capacity state conforms to CTR-API-001.
- API-LIVE-002: an enrolled real Codex subscription account is collected through the production path and its safe capacity state conforms to CTR-API-001.
- API-LIVE-003: the real local Ollama installation/account path exposes only supported truthful capacity/runtime states and never invents subscription limits.
- API-LIVE-004: real API-budget data from authorized accounts in each configured organization appears under the correct account and parent aggregate without cross-organization disclosure.
- API-LIVE-005: a naturally occurring or owner-coordinated exhausted/auth-required/unavailable transition reaches collection, capacity, alert, and dashboard API resources with truthful provenance and recovery.
- API-LIVE-006: an owner-coordinated CTR-REG-008 managed-profile reauthentication start/status/cancel or completion follows M02 → M03 → adapter ownership without P01 orchestration, credential capture, or protected/default-profile mutation.
- API-LIVE-007: real active Claude, Codex, and Ollama processes/sessions, where present, appear through runtime endpoints without command line, environment, prompt, response, tool, source, or terminal content.
- API-LIVE-008: generated client and real browser render the same live account/aggregate/alert truth returned by direct authorized HTTP queries; no placeholder or seeded telemetry is present.

Provider/API limits, destructive exhaustion attempts, password changes, token rotation, reauthentication, and any live action that could interrupt work require an explicit owner test window under the live-verification runbook. The test stops rather than forcing a limit or mutating a default provider profile.

### 20.10 Deferred-requirement negative surface tests

These seven tests do not claim the deferred behavior works. Each is a fail-closed non-capability check across the real source route registry, running route table, OpenAPI, generated client, permission registry, configuration registry, direct/transitive locked dependency graph, and built UI. A matching route, configuration key, permission, package, adapter, schema, or UI action fails the test and blocks release.

- API-DEFER-001 — FR-ALERT-007: no email send/test/credential endpoint, SMTP/email setting or secret class, email permission, mail dependency, delivery adapter, generated method, or dashboard email action exists.
- API-DEFER-002 — FR-ALERT-008: no messenger, webhook, push, native Linux/macOS notification endpoint, setting, permission, dependency, adapter, generated method, or dashboard action exists.
- API-DEFER-003 — FR-ROUTE-001: no account recommendation, account selection, automatic fallback, routing score, or switch-suggestion endpoint, setting, permission, dependency, schema, or UI action exists.
- API-DEFER-004 — FR-ROUTE-002: no checkpoint-and-resume, recovery-under-another-account/provider, session migration, automatic reroute, or work-transfer endpoint, setting, permission, dependency, schema, or UI action exists.
- API-DEFER-005 — FR-CONTENT-001: no prompt, response, tool activity, source-code content, arbitrary terminal content, or full transcript capture/storage/search/export endpoint, setting, permission, dependency, schema/table field, generated method, or UI action exists; submitted canaries remain absent from API/log/diagnostic artifacts.
- API-DEFER-006 — FR-REMOTE-001: no remote/LAN bind, multi-user/tenant administration, proxy-trust shortcut, remote access toggle, remote TLS mode, remote permission, deployment dependency, generated method, or UI action exists; non-loopback startup/config remains rejected.
- API-DEFER-007 — FR-PROVIDER-EXT-001: no Gemini, Grok, Muse, or other additional-provider route, provider manifest, configuration namespace, permission, SDK/CLI dependency, adapter import, generated method, or UI action exists. Only the separately approved Claude, Codex, and Ollama V1 provider lanes may appear.

Future approval of any deferred requirement requires a new or revised approved plan, contracts, ADR/security/privacy/license review, and versioned API migration. P01 does not weaken these checks preemptively for speculative extensibility.

## 21. Test-to-requirement traceability

| Concern | Requirements / acceptance | Planned evidence |
|---|---|---|
| API-first/versioning | NFR-API-001, NFR-API-002, AC-V1-001, AC-UI-006 | API-OAPI-001..012, API-CLIENT-001..008 |
| IAM/session/token | FR-IAM-003, FR-IAM-004, FR-IAM-006, FR-IAM-007, NFR-SEC-001 | API-HTTP-001..009, API-BROWSER-001..007, API-SEC-002..007, API-SEC-017 |
| Accounts/providers | FR-ORG-001..003, FR-ACC-001..006, FR-AUTH-001..006, FR-DISC-001..008 | API-HTTP-010..016 |
| Collection/capacity | FR-COL-001..008, FR-QUOTA-001..006, FR-BUDGET-001..006, AC-LIVE-001..007 | API-HTTP-017..020, API-PERF-001..003, API-LIVE-001..006 |
| Runtime | FR-STATE-001..004, AC-PROC-001..005 | API-HTTP-021..024, API-SEC-015, API-LIVE-007 |
| Alert/dashboard | FR-ALERT-001..006, AC-ALERT-001..003, AC-UI-001..005 | API-HTTP-025..027, API-BROWSER-008..010 |
| History | FR-HIST-001..005, AC-HIST-001..002 | API-HTTP-018..024, API-HTTP-031, API-OAPI-006 |
| Operations | FR-OPS-001..006, AC-OPS-001..006 | API-HTTP-028..032, API-RES-001..003 |
| Read-only/privacy | FR-SAFE-001..002, NFR-PRIV-001..002, ADR-0006 | API-HTTP-014, API-HTTP-036, API-SEC-010..016 |
| Exact action boundary | FR-SAFE-001, FR-SAFE-002 | API-SAFE-001..004, API-HTTP-010..036, API-SEC-015 |
| Deferred non-capabilities only | FR-ALERT-007, FR-ALERT-008, FR-ROUTE-001, FR-ROUTE-002, FR-CONTENT-001, FR-REMOTE-001, FR-PROVIDER-EXT-001 | API-DEFER-001..007; negative surface evidence only, never V1 feature credit |
| Real testing | NFR-TEST-001..002, AC-TEST-001..006 | API-HTTP-001..041, API-BROWSER-001..010, API-AUTO-001..009, API-LIVE-001..008 |

Ranges in this table refer to individually defined scenarios above; they are not permission to omit individual evidence records.

## 22. Automation and canonical commands

P01 is not ready for implementation until these repeatable routines are executable, fail closed, documented by `--help`, and included in the repository's canonical automation registry:

| Routine ID | Required P01 behavior | Planned evidence |
|---|---|---|
| AUTO-TEST | Select all `API-*` tests, start real services, reject skips/deselection, preserve red/green reports | API-AUTO-001, API-AUTO-007 |
| AUTO-QUALITY | Format/lint/type-check API code; enforce one complete policy record per operation, the exact safe-action/deferred surface manifests, safe provider symbol allowlist, schemas, and secret scans | API-PURE-009..010, API-SAFE-001..004, API-DEFER-001..007, API-SEC-011/019, API-AUTO-006 |
| AUTO-BUILD | Through the CAA-C07 ownership split, have integration invoke the FND mechanism to validate/diff OpenAPI, generate/compile the client, and verify deterministic digest/sole-writer ownership | API-OAPI-001, API-OAPI-009..010, API-CLIENT-001..003, API-AUTO-004/009 |
| AUTO-DOCS-CHECK | Validate route documentation, contract links, policy registry, deferred guards, examples, and compatibility notes | API-AUTO-005, API-DEFER-001..007 |
| AUTO-GIT-PREFLIGHT | Run P01 test/quality/build/docs checks before commit/push and reject generated drift | API-AUTO-003..004 |
| AUTO-DEPLOY | Start local service with approved loopback, Host/Origin, migration, readiness, and rollback checks | API-SEC-001..004, API-SEC-016, API-RES-001 |
| AUTO-BACKUP | Invoke approved application/operations workflow, not API internals; report durable resource | API-HTTP-029 |
| AUTO-RESTORE | Remain local runbook-only; prove no public restore API is registered | API-HTTP-036, API-SEC-015 |
| AUTO-RELEASE | Enforce OpenAPI compatibility, artifact/client digest, licenses, docs, and evidence manifests | API-OAPI-009..012, API-AUTO-008 |

Exact command syntax and script paths are foundation/integration-owned. P01 must register selectors and checks with those commands rather than creating competing scripts. A written table, CI placeholder, or manual checklist does not satisfy this gate.

During planning, the canonical planning command is:

```bash
python3 tools/planning/validate_plans.py --stage synchronized
```

It validates the complete planning set, not P01 in isolation. P01 cannot claim repository planning completion while any other required plan or synchronization finding remains open.

## 23. Dependencies and license gate

No dependency is approved or installed by this plan. Candidate roles requiring an approved dependency decision are:

| Role | Candidate already implied by architecture | Review required before use |
|---|---|---|
| HTTP framework | FastAPI | exact version, license, maintenance, advisories, transitive Starlette/Pydantic impact |
| ASGI server | Uvicorn or approved equivalent | production suitability, limits, proxy defaults, shutdown behavior, license/transitives |
| schema/model library | Pydantic through FastAPI | public serialization semantics, compatibility, performance, license/transitives |
| real HTTP test client | approved maintained client | real socket behavior, async support, license/transitives |
| OpenAPI validation/diff | select after evaluation | OpenAPI-version coverage, breaking-change policy, maintenance, license/transitives |
| TypeScript client generator | select through CTR-FND-005 | deterministic output, nullable semantics, auth/headers, maintenance, generator/runtime licenses |
| real browser driver | repository-approved P02/FND tool | browsers, binary provenance, maintenance, license, CI/local operation |

Avoid adding packages for pagination, idempotency, CORS, JWT, sessions, authorization, rate limiting, or generic exception handling unless a recorded evaluation proves necessity. Authentication values are opaque; P01 does not require JWT semantics.

For every selected direct or transitive dependency, record SPDX license, copyright obligations, source, pinned version/range, maintenance signal, known-vulnerability review, data/telemetry behavior, alternatives, and removal/upgrade owner. Copyleft, source-available, telemetry-enabled, abandoned, or unclear-license components stop implementation pending owner approval.

## 24. Open contract and synchronization decisions

These are Draft approval and specialization decisions, not implementation discretion:

1. Approve CTR-API-001, CTR-API-002, CTR-API-003, and ownership/status of CTR-COMMON-005.
2. Freeze M01 cookie names/attributes, session limits, login throttling behavior, bearer challenges, token attenuation, local-HTTP cookie policy, and the proposed exact `read:self`, `write:self`, and `write:sessions` permissions or approved replacements.
3. Reconcile permission vocabulary across M01–M08, including proposed `write:collection` and `write:exports`, runtime configuration mutations, alert read permissions, and diagnostic-bundle creation; every operation must retain exactly one permission.
4. Approve the Draft-aligned CTR-PROV-002 side-effect-free provider-capability and installation-compatibility query ports and their symbol allowlist. No invocation, assessment command, adapter registration object, auth-flow protocol, or extension registry becomes a P01 dependency.
5. Approve M02-owned CTR-REG-008 with exact start/get/cancel reauthentication workflow ports and review projected CTR-REG-009/010 semantics. M03 remains protocol owner; P01 does no reauthentication orchestration.
6. Approve Draft-aligned CTR-COL-006 and durable idempotency ownership for collection submissions.
7. Freeze M05 query names, page contracts, filter/sort sets, unknown/stale/provenance/confidence fields, and history retention visibility.
8. Freeze M06 correlation and stall-policy command permissions, version semantics, and safe projections.
9. Reconcile M07 notification read/unread port names and alert-rule permissions.
10. Approve `write:exports`, safe artifact-reader ports, diagnostic-bundle authorization, and any read-only settings projection in M08.
11. Confirm that restore has no HTTP route and decide whether unauthenticated health probes remain absent or receive a new ADR.
12. Freeze default/max page sizes, request/body/header/time/concurrency limits, and rate-limit ownership.
13. Freeze schema names, ID format contract, time/duration format, cursor envelope, ETag encoding, receipt retention, all seven replay policies, `one_time_secret_non_replayable`, and the SafeProblem type URI base.
14. Choose and approve the OpenAPI validator/diff and generated-client toolchain; record the CAA-C07 split: P01 semantics/source, FND mechanism, integration sole generated-artifact writer per wave, P02 wrapper consumption.
15. Define the exact configuration keys through CTR-CONFIG; do not use the conceptual names in section 17 as ad hoc environment variables.
16. Resolve audit-command ownership and ensure boundary denial events do not depend on the denied application operation succeeding.
17. Freeze CAA-C02's distinct `dashboard_authentication_required` and `provider_reauthentication_required` codes/status/UI recovery meanings; no generic `authentication_required` remains in CTR-API-001.
18. Approve the exact FR-SAFE-001 positive unsafe-operation allowlist and the FR-SAFE-002/all-seven-deferred negative surface manifests.

Each resolution must update this plan, the owning module plan, contract register, backlog, traceability, and an ADR where the change is architectural.

## 25. Definition of ready for implementation

Implementation may begin only when all items are true:

- This plan passes the synchronized planning gate as part of the complete required plan set.
- The plan status and all consumed contract statuses are consistent with the contract register.
- Every endpoint has an approved application port and safe DTO; implementation-blocked rows are removed from the increment or their gaps are closed.
- The endpoint/permission matrix has security, M01, and owning-module approval.
- Every operation-policy record has exactly one approved auth profile, permission, resource application port, replay policy, success schema, and SafeProblem error schema.
- CAA-C02, CAA-C04, CAA-C07, and CAA-C12 are reflected in the synchronized register/baseline, not only in this Draft.
- The FR-SAFE-001 positive action allowlist and FR-SAFE-002/seven-deferred negative surface manifests pass their executable source/OpenAPI/config/permission/dependency/runtime checks.
- CTR-API-001..003 and CTR-COMMON-005 have approved schemas and version policy.
- Host, Origin, session cookie, CSRF, bearer, Swagger, loopback, and remote-defer decisions are approved.
- Exact config names, defaults, bounds, and startup validation are approved.
- Dependency/license/security reviews are recorded; selected versions are pinned by the foundation plan.
- Canonical AUTO-TEST, AUTO-QUALITY, AUTO-BUILD, AUTO-DOCS-CHECK, and AUTO-GIT-PREFLIGHT commands exist and are proven to fail on a controlled negative case.
- Real test prerequisites, isolated data paths, browsers, ports, and evidence directories are documented and runnable without touching user profiles.
- A clean baseline gate result is captured before the first red test.
- The integration owner allocates the central router, OpenAPI artifact, generated client, and composition-root files to one writer.

## 26. Parallel execution and file ownership

After API-I00 through API-I04 freeze the shared core, route-family increments API-I05 through API-I11 may proceed in parallel only with explicit path allocation:

- Registry agent: `routers/registry.py`, `schemas/registry.py`, and registry-scoped tests/docs.
- Provider agent: `routers/providers.py`, `schemas/providers.py`, and provider-scoped tests/docs.
- Collection agent: `routers/collection.py`, `schemas/collection.py`, and collection-scoped tests/docs.
- Capacity agent: `routers/capacity.py`, `schemas/capacity.py`, and capacity-scoped tests/docs.
- Runtime agent: `routers/runtime.py`, `schemas/runtime.py`, and runtime-scoped tests/docs.
- Alert agent: `routers/alerts.py`, `schemas/alerts.py`, and alert-scoped tests/docs.
- Operations agent: `routers/operations.py`, `schemas/operations.py`, and operations-scoped tests/docs.

Only the designated P01 source-integration owner may edit `router.py`, `dependencies.py`, shared schemas, middleware, exception registration, or `openapi.py`; the composition root still requires its separately allocated shared-file writer. The integration steward alone writes canonical OpenAPI/client generated outputs for the wave by invoking the FND mechanism. Route-family agents submit a declared registration descriptor or narrowly reviewed source patch; they do not race on central or generated files.

Every parallel assignment must state owned files, forbidden files, consumed contract versions, test IDs, integration assumptions, and stop conditions. Cross-family shared behavior is raised to the integration owner rather than duplicated.

## 27. Risks, mitigations, and mandatory stops

| Risk | Mitigation | Mandatory stop |
|---|---|---|
| Thin boundary absorbs business rules | exact port matrix, forbidden imports, architecture test | stop when a handler needs persistence/domain/provider/process logic |
| Permission drift across modules | one reviewed operation registry and OpenAPI check | stop on any unregistered or ambiguous permission |
| Cookie security incompatible with local HTTP | approved deployment-specific policy and browser evidence | stop if a secure attribute must be weakened without threat review |
| Origin/Host bypass | exact normalization, deployed-stack adversarial tests | stop on wildcard/alias/proxy ambiguity |
| Secret or operational-content leakage | allowlisted DTOs, body-free logs, canary scans | stop and treat as security incident on any leak |
| Framework default error leakage | global SafeProblem mapping, real failure tests | stop if any error path emits framework/internal detail |
| Dashboard auth and provider reauth conflated | distinct CAA-C02 codes/statuses and browser/client recovery tests | stop if provider state returns dashboard 401 or clears a session |
| One-time secret replay | CAA-C04 replay policy and 409 safe-metadata test | stop if any secret/result cache can replay plaintext |
| P01 provider orchestration creep | safe-query symbol allowlist plus CTR-REG-008-only reauth | stop on provider resolution/invocation/assessment/flow/adapter import |
| Stale OpenAPI/client | deterministic generation and digest gate | stop merge/release on drift |
| Generated-client semantic loss | compile plus real request tests for nullable/auth/header behavior | stop and change generator or mapping if semantics cannot be represented |
| Duplicate long work | durable module-owned idempotency | stop if only an in-memory boundary cache is available |
| Public process/restore mutation | explicit absence tests and route inventory | stop immediately if proposed or registered |
| Test-double substitution | real socket/database/browser gates and skip rejection | stop when evidence depends on mocks/fakes/stubs/recordings |
| Parallel merge conflict | one central writer and path allocation | stop concurrent edits to shared/generator files |
| Generated artifact ownership drift | CAA-C07 ownership manifest and writer gate | stop if P01/FND/P02 writes integration-owned generated output |
| Deferred feature leakage | seven exact route/config/permission/dependency/UI negative manifests | stop release on any deferred surface or dependency |
| Dependency/license surprise | pre-install dependency review | stop on unapproved or unclear license/transitive risk |
| Health-probe disclosure | authenticated V1 resource; ADR for exception | stop before adding an unauthenticated probe |
| Remote-mode shortcut | separate remote threat/deployment plan | stop if non-loopback exposure is enabled by config alone |

Any discovery of credentials, tokens, cookies, provider secrets, prompts, responses, source code, arbitrary environment values, or sensitive local paths in an API artifact, log, test evidence, screenshot, or response requires immediate stop, containment, secret rotation as applicable, artifact removal, and incident documentation before work resumes.

## 28. Rollback and recovery

- A route-family increment is reverted as a coherent source/schema/test/docs change; the integration steward regenerates artifacts through the FND mechanism from the restored P01 source, never manually patches them backward.
- Additive V1 storage/domain changes are owned and rolled back by their modules, not P01.
- A newly discovered breaking contract change is withheld behind the prior compatible V1 behavior or released under a new approved version. P01 does not silently revert persisted data.
- If a security control fails, disable the affected operation or service at the composition/deployment boundary, preserve safe audit evidence, and use the approved prior release.
- Failed OpenAPI/client generation leaves committed artifacts untouched.
- Failed local deployment returns to the previous approved package/config with database compatibility checked by DEP/DB automation.
- Restore execution remains the operations runbook's local workflow and is never introduced as an API rollback shortcut.

## 29. Documentation deliverables

Before implementation handoff, update through approved ownership:

- `docs/api/http-boundary.md` with transport, auth, pagination, errors, concurrency, idempotency, and examples.
- One resource document per stable API tag, generated or mechanically checked against OpenAPI.
- Swagger/ReDoc descriptions from safe source text with no live data.
- Configuration reference with exact environment keys, types, defaults, bounds, restart semantics, and secrecy classification.
- Local operations runbook for start, readiness, authentication bootstrap reference, OpenAPI/client generation, diagnostics, and rollback.
- Security documentation for Host/Origin, cookie/CSRF/bearer, docs access, artifact downloads, and deferred remote mode.
- Dependency/license inventory and notices.
- Traceability updates linking each requirement/criterion to scenario and evidence IDs.
- Contract register and planning backlog updates for every synchronized decision.

Examples may use constructed values only for documentation/schema clarity and must be visibly synthetic. They must never be loaded as application/dashboard/test telemetry.

## 30. Implementation handoff evidence

The final P01 implementation handoff must use `docs/templates/subagent-handoff-template.md` and name:

- PLAN-P01, requirement IDs, acceptance IDs, and all completed `API-*` scenario IDs.
- CTR-API-001, CTR-API-002, CTR-API-003, CTR-COMMON-005 and every consumed contract version/status.
- Exact files changed, including generated artifacts and their digests.
- Each red test command, expected failure, captured red evidence, green command, and green evidence.
- Real HTTP server, real database, real browser, generated-client, Linux environment, and any macOS evidence actually exercised.
- Tests blocked, skipped, unavailable, or still requiring the owner; none may be described as passed.
- API compatibility report, secrets/privacy scan, dependency/license review, security review, performance profile, migration impact, documentation updates, and rollback check.
- Canonical automation command outputs and proof that required test selection was not narrowed.
- Remaining risks, synchronization findings, and follow-up owners.

No handoff may use “done,” “ready,” “implemented,” or “validated” unless the canonical executable completion gate passes for the exact claimed scope against the real checkout/environment.

## 31. Exit criteria

P01 implementation is complete only when:

- every approved matrix operation exists and no unapproved route exists;
- all handlers obey the allowed-import/application-port boundary;
- every listed required test is implemented, first observed red for the intended reason, then green against real boundaries;
- OpenAPI is valid, deterministic, compatible, privacy-clean, and synchronized with the compiled generated client;
- browser session, CSRF, bearer, docs, Host, Origin, security-header, idempotency, correlation, concurrency, error, and long-job behavior has real evidence;
- no public process-control or restore execution surface exists;
- performance, resilience, Linux, documentation, license, security, privacy, and rollback evidence is approved;
- all relevant canonical automation routines pass without required skips or deselection;
- contract register, traceability, backlog, docs, and handoff are synchronized;
- the repository completion gate passes for the exact P01 scope.

Until then, the truthful state is intermediate work with named pending approvals and Not Run evidence.
