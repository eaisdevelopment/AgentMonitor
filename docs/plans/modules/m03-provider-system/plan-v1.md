# PLAN-M03: provider system and adapter protocol

- Status: **Draft — blocked by Milestone 0 and contract synchronization; implementation is not authorized**
- Plan version: `0.2.0-draft`
- Proposed module contract bundle: `provider-system.v1`
- Provider protocol: current architecture draft `1.0.0-draft.2`; proposed synchronized target `1.0.0`
- Primary owner: M03 Provider system
- Reviewers: integration/architecture, M02 Registry, M04 Collection control, M05 Capacity, M06 Runtime observation, M08 Operations, A01/A02/A03 provider-adapter, security/privacy, test-integrity, persistence, and dependency/license owners
- Primary requirements: FR-AUTH-001, FR-AUTH-006, FR-QUOTA-006, FR-BUDGET-006, FR-DISC-008, FR-COL-004, FR-COL-006, FR-COL-007, FR-COL-008, NFR-RES-001, NFR-COMP-001
- Supporting requirements: FR-AUTH-002, FR-AUTH-004, FR-AUTH-005, FR-SAFE-001, FR-SAFE-002, NFR-ARCH-001, NFR-ARCH-002, NFR-DATA-001, NFR-TEST-001, NFR-TEST-002, NFR-SEC-001, NFR-PRIV-001, NFR-PRIV-002, NFR-DOC-001, NFR-LIC-001, NFR-PLAT-001, NFR-PERF-001, NFR-OBS-001
- Acceptance contribution: AC-V1-002, AC-V1-004, AC-V1-005, AC-V1-006, AC-V1-007, AC-V1-008, AC-LIVE-004, AC-LIVE-005, AC-LIVE-006, AC-LIVE-007, AC-PROC-004, AC-OPS-003, AC-OPS-004, AC-OPS-006, AC-TEST-001, AC-TEST-002, AC-TEST-003, AC-TEST-004, AC-TEST-005, AC-TEST-006
- Entry dependency: approved M0 capability matrices and M03 handoff; synchronized common, registry, collection, capacity, runtime, operations, persistence, and safe-execution contracts
- Accepted architecture decisions: ADR-0005 capability-driven versioned provider adapters and ADR-0007 secret/provider-profile model
- Target milestone: M1/M2 protocol foundation, before provider-adapter implementation
- Approved by/date: pending

## CS-1 Draft-alignment addendum

This `0.2.0-draft` revision adopts contract-baseline `0.2.0` and the parallel-ownership manifest as its concrete CS-1 review position. It remains Draft and evidence-blocked: M0 and every provider-boundary scenario are `Not Run`, and no capability is promoted to Supported by this alignment.

- M03 remains sole semantic producer of CTR-PROV-001..008, provider-owned CTR-COMMON-004 semantics, and CTR-BOUNDARY-002 `SafeProviderHttpExecutionV1`. CTR-BOUNDARY-002 fixes allowlisted provider hosts, verified TLS, redirect/body/page/deadline/cancellation/rate bounds, credential-to-host binding, and typed sanitized failures; A01–A03 implement/use it without exposing raw responses.
- The normalized provider authentication state in CTR-PROV-006 is exactly `reauthentication_required`. Adapter-native `reauthorization_required` or generic `authentication_required` is mapped at the adapter boundary. M03 produces provider observation/protocol truth; M02 alone persists account/profile authentication truth through CTR-REG-010 and coordinates the durable workflow through CTR-REG-008.
- Every provider observation and outcome uses CTR-COMMON-007 for explicit field availability and carries a complete CTR-COMMON-004 evidence block: source class/ID, adapter/provider/tool versions when known, stability, value kind, observed/collected times, freshness/expiry, precision, confidence, experimental flag, derivation/input references when applicable, and bounded warnings. Missing evidence invalidates success rather than becoming an implicit known value.
- M03 events use CTR-COMMON-006 with CTR-EVT-001 atomic outbox, per-stream generation, consumer receipt/checkpoint, replay, incompatible-major rejection, poison/backlog, and retention semantics. It implements the M08-owned CTR-OPS-006 and CTR-OPS-007 leaf participant ports without allowing M08 to read M03 tables.
- M03 adopts CTR-EVT-TOPOLOGY-001: it owns `provider_system_event_outbox` and its atomic producer append. PLAN-DB's shared dispatcher uses the published M03 event-storage port; each consumer owns its receipt/checkpoint. No central event table or cross-module SQL is permitted.
- The V1 public contract file is `backend/src/agentmonitor/contracts/provider_system_v1.py`; provider extensions use only `backend/src/agentmonitor/contracts/providers/<provider>/<capability>/v1/**`; SQLite implementation files are only under `backend/src/agentmonitor/adapters/persistence/provider_system/sqlite/**`. M03 owns `provider_system_` tables and `v1_0300..v1_0399`.
- Alignment is verified by existing scenarios M03-PURE-021..034, M03-CONF-001..010, M03-SEC-001..010, M03-DB-001..013, M03-ARCH-001..004, and M03-LIVE-001..010. Their required real boundaries and `Not Run` status are unchanged.

## 0. Authority, evidence state, and planning constraints

This document is the independent implementation plan for M03 only. It does not authorize production code, dependency installation, database migration, provider access, account access, authentication, profile changes, or live verification.

Milestone 0 has not executed. No Claude, Codex, Ollama, Anthropic API, OpenAI API, provider-version, source-shape, rate-limit, authentication-role, file, command, or account behavior is treated here as known. Exact provider facts enter this plan only through an approved M0 handoff containing scoped capability decisions and sanitized evidence references. Until that handoff exists:

- `CTR-COMMON-004` and `CTR-PROV-001..008` remain Proposed/Concept, not Approved;
- every provider-dependent test is `Not Run`, not Passed;
- capability payload schemas, verified provider-version ranges, and source fallback chains remain approval-blocking synchronization decisions;
- no provider adapter may claim conformance to this draft;
- provider-specific behavior must not be added to M03 to unblock another module.

Structural examples in this plan are contract shapes, not provider observations or test fixtures. Constructed values may be used only by pure, no-I/O policy tests. No fake adapter, fake provider, recorded response, demo account, seeded telemetry, placeholder observation, or test-only production path is permitted.

## 1. Outcome and boundaries

### 1.1 Outcome

After approved implementation, AgentMonitor has one provider-neutral, capability-driven protocol through which statically admitted Claude, Codex, and Ollama adapters can declare exactly what they implement; be registered and compatibility-checked; expose source, version, freshness, precision, confidence, privacy, and side-effect metadata; and return typed success, partial, unavailable, unsupported, authentication, authorization, version-drift, rate-limit, deadline, and safe-failure outcomes.

The module is successful when:

1. M02, M04, M05, M06, and M08 consume versioned M03 contracts without importing provider SDKs or provider-adapter internals.
2. A01, A02, and A03 can implement capabilities independently without adding provider conditionals to M03 or downstream domains.
3. Unsupported, Unknown, Experimental, Deferred, temporarily unavailable, and unverified-version conditions remain distinct end to end.
4. An adapter cannot silently downgrade its source, guess identity, return an unvalidated extension, or leak raw provider output through a public result.
5. Protocol or provider-version incompatibility is detected before unsafe collection.
6. One adapter failure is contained and represented as a sanitized typed outcome without taking down other adapters or dashboard queries.
7. Every conformance claim is backed by the real production adapter against its real approved provider/system boundary.

### 1.2 In scope

- Provider-adapter protocol vocabulary and protocol-version negotiation.
- Stable provider, adapter, capability, operation, source, outcome, compatibility, and schema-reference value objects.
- Capability manifest schema, validation, decision/stability metadata, and manifest fingerprinting.
- Static adapter registration through the composition root; deterministic lookup; duplicate/conflict rejection.
- Capability and source negotiation, including explicit Experimental opt-in and source-downgrade rules.
- Provider-neutral operation envelopes and capability-specific typed port families.
- Typed operation outcomes and sanitized error/retry dispositions.
- Provider discovery, identity verification, authentication health, and reauthentication protocol contracts.
- Provenance fields required at the provider boundary and their mapping into `ObservationProvenanceV1`.
- Provider-extension schema registration, privacy metadata, validation rules, and compatibility governance.
- Adapter/provider/capability compatibility assessments and their history.
- Adapter availability/compatibility events and safe component-health projection.
- The invocation gateway that validates requests/results, enforces protocol policy, contains adapter failures, and records compatibility outcomes.
- Contract conformance suites that run against real A01/A02/A03 production adapters and real approved provider/system boundaries.

### 1.3 Out of scope

- Claude, Codex, Ollama, Anthropic API, OpenAI API, or any other provider parsing, command, path, endpoint, SDK, authentication, quota, or billing logic.
- Dynamic third-party plugin loading, arbitrary Python imports, entry-point scanning, downloaded adapters, or user-supplied executable code.
- Organization, account, resource, installation, monitoring-profile, alias, or owner-confirmation persistence; M02 owns these.
- Poll schedules, leases, concurrency, retries, backoff, manual refresh, and collection-run history; M04 owns these.
- Quota, cost, budget, credits, token aggregates, capacity health, forecasts, and capacity history; M05 owns these.
- Process/session facts, hierarchy, runtime state, account correlation decisions, possible-stall policy, and runtime history; M06 owns these.
- Alert rules/lifecycle and dashboard notifications; M07 owns these.
- Product-wide health, backup, export, restore, diagnostic bundles, and audit aggregation; M08 owns these.
- REST/OpenAPI routes, authentication transport, UI, generated client, and database access by consumers.
- Provider credential storage or secret resolution. Provider credentials remain provider-managed and are represented only by opaque approved references.
- Automatic routing, running-agent control, credential switching inside a running agent, or in-flight session recovery.

### 1.4 Ownership and handoff matrix

| Concern | M03 owns | Explicit handoff/non-owner |
|---|---|---|
| Protocol | Provider protocol version, negotiation, manifest and outcome semantics | A01/A02/A03 implement; composition wires; consumers invoke through ports |
| Capabilities | Vocabulary, identifiers, declaration/decision/runtime-availability distinctions | M0 proves provider support; adapters declare only evidenced rows |
| Sources | Source class and explicit approved selection/fallback semantics | Each adapter defines evidenced source IDs and implementation |
| Payloads | Generic validated envelope and schema-reference rules | M05/M06 own normalized business payload contracts; adapters own safe extension schemas |
| Discovery/auth | Provider-neutral request/outcome/auth-state and CTR-PROV-007 protocol semantics only | M02 owns CTR-REG-008 application orchestration/persistence and CTR-REG-010 registry truth; P01 owns transport mapping and P02 owns presentation |
| Compatibility | Registration and protocol/capability/provider-version assessment policy and records | M02 owns installation record; M08 consumes health/version summaries |
| Execution | Invocation policy gateway and safe boundary requirements | Safe subprocess/network/filesystem ports are separately owned; adapters execute provider calls |
| Persistence | `provider_system_*` compatibility/event records only | No M02/M04/M05/M06 table access |
| Events | Adapter compatibility/availability event schemas | M04 and M08 consume; common event delivery/outbox is synchronized centrally |
| Conformance | Protocol suite definition and evidence aggregation | Every adapter owner runs it against the real production adapter/provider |

### 1.5 Proposed implementation paths

Allowed after plan and contract approval:

```text
backend/src/agentmonitor/modules/provider_system/**
backend/src/agentmonitor/adapters/persistence/provider_system/sqlite/**
backend/tests/provider_system/**
backend/tests/integration/provider_system/**
docs/modules/provider-system.md
docs/test-evidence/provider-system/**       # sanitized evidence records only, if allocated
```

Shared paths require explicit root allocation for each change:

```text
backend/src/agentmonitor/contracts/provider_system_v1.py
backend/src/agentmonitor/contracts/common_provenance_v1.py
backend/migrations/versions/<allocated-m03-revision>.py
backend/src/agentmonitor/composition/**
configuration registry
event/outbox registry
dependency manifests and lockfiles
```

M03 does not own and must not edit:

```text
backend/src/agentmonitor/adapters/providers/claude/**
backend/src/agentmonitor/adapters/providers/codex/**
backend/src/agentmonitor/adapters/providers/ollama/**
backend/src/agentmonitor/modules/registry/**
backend/src/agentmonitor/modules/collection_control/**
backend/src/agentmonitor/modules/capacity/**
backend/src/agentmonitor/modules/runtime_observation/**
backend/src/agentmonitor/modules/alerting/**
backend/src/agentmonitor/modules/operations/**
backend/src/agentmonitor/api/**
frontend/**
```

### 1.6 Allowed and forbidden imports

M03 domain/application code may import only the standard library and approved cross-module contracts: `CTR-COMMON-001/002/004/006`, synchronized capability payload contracts, and narrowly scoped safe-execution port contracts. It must remain independent of FastAPI, Starlette, Pydantic transport models, SQLAlchemy, Alembic, provider SDKs/CLIs, operating-system APIs, UI code, and concrete adapters.

Persistence implementations may import the approved persistence stack and M03 repository ports. Composition may import M03 registration ports and concrete A01/A02/A03 adapter factories. Provider adapters import M03 contracts; M03 never imports a provider adapter. Consumers import the published M03 contract package, never M03 internals or its tables.

Adapters may not bypass approved context ports for filesystem, subprocess, HTTP, cancellation, or credential/profile resolution. If a provider SDK makes that impossible, its admission and boundary are separately reviewed; the SDK never enters M03.

## 2. Requirements and traceability

| Requirement/AC | Planned M03 behavior | Contract | Test/scenario IDs | Evidence gate |
|---|---|---|---|---|
| FR-AUTH-001 | Preserve the complete provider auth-health vocabulary with evidence and Unknown semantics | CTR-PROV-006 | M03-PURE-021..024, M03-LIVE-006 | Pure state contract plus real provider observation |
| FR-AUTH-002 | Define official managed-profile reauthentication protocol without accepting credentials | CTR-PROV-007 | M03-PURE-025..027, M03-LIVE-007 | M0 isolated-profile decision and owner-run real flow |
| FR-AUTH-004/005 | Prohibit credential values and reject protected/unknown profile mutation before adapter invocation | CTR-PROV-001/007 | M03-SEC-001..004, M03-LIVE-008 | Contract/security review and real no-modification evidence |
| FR-AUTH-006 | Gate reauthentication and profile-dependent capability claims on exact provider/version evidence | CTR-PROV-002/007 | M03-PURE-010/025, M03-CONF-003, M03-LIVE-007 | Approved M0 matrix and adapter live matrix |
| FR-QUOTA-006 | Represent exact discovered subscription-quota capability decisions without assuming support | CTR-PROV-002/004 | M03-PURE-006/016, M03-CONF-004 | M0 quota matrix and real adapter conformance |
| FR-BUDGET-006 | Represent exact API usage/cost/budget capability decisions and credential-role constraints | CTR-PROV-002/004 | M03-PURE-006/016, M03-CONF-005 | M0 API matrices and real adapter conformance |
| FR-DISC-008 | Require parser/source schema and provider CLI/service version in every local parsing result | CTR-PROV-003/004; CTR-COMMON-004 | M03-PURE-019/020, M03-CONF-006 | Pure validation plus real local-source observation |
| FR-COL-004 | Require source, observed/collected time, adapter/provider version, freshness, precision, and confidence | CTR-COMMON-004; CTR-PROV-003/004 | M03-PURE-017..020, M03-CONF-001 | Contract validation and real observations |
| FR-COL-006 | Make Unsupported and runtime Unavailable explicit and non-interchangeable | CTR-PROV-002/004 | M03-PURE-003/014..016, M03-LIVE-004 | Pure union checks plus real unsupported/unavailable evidence where available |
| FR-COL-007 | Encode documented API > supported CLI > approved local metadata > approved Experimental source, without implicit downgrade | CTR-PROV-003 | M03-PURE-011..013, M03-CONF-002 | Policy tests and M0-approved source chains |
| FR-COL-008 | Reject invented, unproven, stale-as-current, or unapproved fallback results | CTR-PROV-004 | M03-PURE-013/018, M03-SEC-005, M03-LIVE-005 | Validation, source/provenance review, real adapter evidence |
| FR-SAFE-001/002 | Expose read/refresh/managed-reauth only; publish no process-control/routing capability | Full M03 surface | M03-ARCH-001/002, M03-SEC-006 | API/import/surface absence review |
| NFR-ARCH-001/002 | Isolated module, typed contracts, one-way adapter dependency, owned data | `provider-system.v1` | M03-ARCH-001..004 | Import-boundary and ownership checks |
| NFR-DATA-001; AC-V1-004; AC-OPS-004 | Own only compatibility records, use real portable SQLite migrations, and participate in verified backup/restore | M03 repository ports; CTR-FND-006; CTR-DB-002 | M03-DB-001..013, M03-OPS-004/005 | Fresh/upgrade migration and real backup/restore evidence |
| NFR-TEST-001/002; AC-TEST-001/002/006 | Red-green-refactor, real boundaries, no doubles, truthful Blocked/Not Run | Evidence contract | All M03 scenarios; M03-TEST-001/002 | Independent evidence and prohibited-pattern review |
| AC-TEST-003/004/005 | Execute pure, real DB/service, and real provider suites; retain sanitized live records; mutation-test critical policies | Test/evidence contracts | M03-PURE-001..034, M03-DB-001..013, M03-INT-001..005, M03-LIVE-001..010 | Required boundary results and approved mutation target |
| NFR-SEC-001; NFR-PRIV-001/002 | Validate untrusted adapter output, minimize data, prohibit raw/content/secret fields and outbound analytics | CTR-PROV-003/004/008 | M03-SEC-001..010 | Security review and DB/log/artifact/network inspection |
| NFR-DOC-001; AC-V1-006 | Publish protocol, compatibility, extension, conformance, and operations documentation | Documentation outputs | M03-DOC-001/002 | Documentation and link review |
| NFR-LIC-001 | Add no provider SDK/protocol utility without dependency admission | Dependency record | M03-DEP-001/002 | Direct/transitive license/security review |
| NFR-PLAT-001 | Keep the protocol platform-neutral and record platform scope without Linux imports | Manifest/platform scope | M03-ARCH-001, M03-CONF-003, M03-LIVE-002 | Real Linux evidence; macOS stays explicit Passed or Blocked |
| NFR-PERF-001 | Use bounded manifests/extensions and indexed deterministic lookup; no per-account redesign | Catalog/persistence ports | M03-PERF-001/002 | AgentMonitor-owned load measurement; no provider simulation claim |
| NFR-RES-001; AC-OPS-003 | Contain adapter exception/malformed result and keep unrelated adapters/service available | CTR-PROV-004; health/events | M03-INT-005, M03-LIVE-009 | Real production-adapter failure when safely/naturally available |
| NFR-OBS-001 | Correlation-aware safe codes and bounded structured events, no raw provider output | CTR-PROV-004; events | M03-SEC-007/008, M03-OPS-003 | Log/event/diagnostic inspection |
| NFR-COMP-001 | Enforce protocol, capability, extension, event, and DB compatibility rules | CTR-PROV-001..008 | M03-PURE-004..010, M03-DB-001/010, M03-CONF-003 | Compatibility suite and migration evidence |
| AC-LIVE-004 | Every A01/A02/A03 adapter completes the protocol conformance/live matrix | CTR-PROV-001..008 | M03-LIVE-001..010 | Real current adapter/provider versions |
| AC-LIVE-005 | Boundary preserves identity/scope/unit/time/precision/source for downstream reconciliation | CTR-PROV-004; CTR-COMMON-004 | M03-CONF-001, M03-LIVE-003 | Provider-authoritative comparison owned with M05/adapters |
| AC-LIVE-006/007 | Reauth and naturally occurring auth/exhaustion/unavailable/recovery states remain truthful | CTR-PROV-006/007 | M03-LIVE-006..008/010 | Owner-coordinated real scenarios; unavailable states remain Blocked |
| AC-PROC-004 | Provider local/session outcomes contain only allowlisted operational metadata | CTR-PROV-004/008 | M03-SEC-002/005/009, M03-LIVE-002 | Parser allowlist review and real artifact scan |
| AC-OPS-006 | Manifest carries evidence-backed collection constraints; M04 remains scheduler owner | CTR-PROV-002/004 | M03-PURE-007, M03-CONF-007 | M0 rate/cost evidence plus M04 integration |
| AC-V1-002/005/007/008 | Approved plan/contracts, security review, no secret or simulated data | Entire module | M03-DOC-001, M03-SEC-010, M03-TEST-001/002 | Release review |

M03 contributes to these criteria but cannot pass provider reconciliation, reauthentication, process privacy, polling-rate, or failure-isolation criteria alone.

## 3. Domain design

### 3.1 Core identifiers and value objects

All identifiers are opaque, bounded strings and use `OpaqueIdV1` where internal identity is required. No consumer derives provider/account semantics from an identifier.

- `ProviderKeyV1`: stable AgentMonitor provider-product key, not a display name.
- `AdapterIdV1`: stable implementation identity; distinct from provider key and package/module path.
- `AdapterVersionV1`: semantic implementation version. Any parser/source behavior change changes this version according to compatibility impact.
- `ProviderProtocolVersionV1`: semantic protocol version; initial proposed host version `1.0.0` after synchronization.
- `CapabilityIdV1`: namespaced dotted identifier. Core V1 identifiers are listed in section 3.2; unknown identifiers are preserved for diagnostics but are not invokable without a registered schema.
- `CapabilitySchemaVersionV1`: integer major plus non-breaking minor. Major changes are incompatible.
- `SourceIdV1`: adapter-owned stable, non-secret source identifier scoped to one provider/capability.
- `ExtensionSchemaRefV1`: provider, capability, schema name, major, and minor; never an arbitrary media-type string.
- `ProviderOperationIdV1`: caller-generated idempotency/correlation identity; it is not a provider request ID.
- `ProviderTargetV1`: opaque installation/account/profile/resource references plus provider key and profile protection classification. It contains no credential, email, display name, path, or arbitrary map.
- `CompatibilityAssessmentIdV1`: immutable M03 assessment identity.

String sizes, allowed character sets, list cardinalities, nesting depth, and serialized-size bounds are synchronized before implementation and enforced at every external/adapter boundary.

### 3.2 Capability vocabulary

The proposed core identifiers are:

```text
installation.discovery
account.discovery
identity.verification
authentication.health
authentication.reauthenticate
subscription.quota
api.usage
api.cost
api.budget
project.discovery
model.catalog
local.session.discovery
local.session.metrics
local.process.correlation
provider.diagnostics
```

M0 may prove that a capability needs subdivision or clearer semantics. A compatible new capability can be added after producer/consumer review. Renaming, reinterpreting, or merging an existing capability is breaking and requires a new contract major plus ADR.

Every capability has three separate dimensions:

1. **Discovery decision:** `supported`, `experimental`, `deferred`, `unsupported`, or temporary pre-M0 `unknown`.
2. **Registration compatibility:** whether host protocol, capability schema, extension schema, platform, and provider version can safely interoperate.
3. **Runtime outcome:** what happened during one invocation.

No mapping collapses one dimension into another. `Unsupported` is an evidenced capability decision; `provider_unavailable` is a temporary invocation result; `unknown` is absence of trustworthy knowledge; `unverified_provider_version` is a compatibility result; `partial` is a successful observation with declared omissions.

Only `supported` declarations are enabled by default. `experimental` declarations are disabled by default and require an explicit, scoped policy grant recorded outside M03 by the owning configuration/profile workflow. `deferred`, `unsupported`, and `unknown` declarations expose status but cannot resolve to an invocation port.

### 3.3 Capability declaration and manifest invariants

`CapabilityManifestV1` contains an adapter descriptor and one declaration per provider/capability/context decision tuple. Required fields are:

- adapter ID/version, provider key, protocol version range, manifest schema version, and build identity;
- capability ID and schema version range;
- decision and stability classification with safe reason code and M0 decision/evidence reference;
- supported platform scope and provider-product/version rule identifier;
- declared typed capability port and output payload schema reference;
- one or more ordered source declarations;
- credential-role category and whether owner interaction is required, never credential values;
- expected freshness/data-latency class when evidence supports it;
- collection cost/rate/concurrency facts when evidenced, otherwise Unknown;
- side-effect class and whether the operation can write only an AgentMonitor-managed profile;
- provider-extension schema references and privacy classification;
- compatibility expiry/review trigger and exact observed scope.

Manifest invariants:

- the provider key and adapter ID are immutable for an adapter lineage;
- provider/capability/source tuple keys are unique;
- every `supported` or `experimental` declaration names a known typed schema and concrete port;
- `deferred`, `unsupported`, and `unknown` declarations expose no invokable port;
- a declaration cannot claim a broader provider-version, account/plan/role, or platform scope than its M0 evidence;
- a reauthentication declaration must state managed-profile-only and must reject protected-default or unknown profile classification;
- a local parser declaration must include parser/schema version and provider CLI/service version requirements;
- every source and extension schema is registered before the manifest is accepted;
- raw command/API/file shapes and credentials are never embedded;
- manifest order is canonicalized for a reproducible safe fingerprint; the fingerprint is not a security signature.

### 3.4 Source model and downgrade policy

`ProviderSourceV1` classifies exactly one source as:

1. `documented_api`
2. `supported_cli`
3. `approved_local_metadata`
4. `experimental_private_or_browser`

It also carries source ID, provider/capability scope, documentation/evidence reference, stability, mechanism/schema version, credential-role category, version range, expected freshness/latency, and side-effect class.

Source priority is a preference, not permission to fall back. The caller and manifest negotiate one exact source or one evidence-approved ordered chain. A source transition is allowed only when:

- both source IDs and transition order are present in the approved manifest;
- the request explicitly permits that chain;
- an Experimental source has a separate scoped opt-in;
- the first source's typed outcome permits fallback;
- the returned provenance identifies the actual source and prior safe failure code;
- no missing/stale/cached value is presented as a fresh live result.

No adapter may silently use an undocumented/private source because an official source failed. A policy-disabled capability is non-invokable at resolution time. If an invalid caller nevertheless attempts invocation, M03 returns the existing outer `unsupported` outcome with a stable `capability_disabled` reason code; provider unavailability returns `provider_unavailable` rather than weakening policy.

### 3.5 Protocol and compatibility negotiation

Registration and resolution use this deterministic sequence:

1. Validate bounded adapter descriptor and canonical manifest.
2. Require the host protocol version to fall within the adapter-declared range and the major versions to match.
3. Reject duplicate adapter/provider registration unless the descriptor, factory identity, version, and manifest fingerprint are identical; an exact replay is idempotent.
4. Validate capability identifiers, decisions, schema majors, source registrations, extension registrations, and privacy classifications.
5. Mark unknown capability/schema majors non-invokable without discarding their safe descriptor.
6. Evaluate platform and provider-version compatibility using the approved version scheme/rule from M0.
7. Enforce Experimental policy and target/profile protection.
8. Resolve exactly one typed port and approved source policy or return a typed resolution failure before external I/O.

Protocol minor versions may add optional fields and capability identifiers when older hosts can ignore them safely. Protocol major mismatch is rejected. Capability/extension schema major mismatch is rejected for that capability without disabling unrelated compatible capabilities. Adapter implementation versions follow semantic versioning, but provider-product versions are treated according to their evidenced version scheme: semantic range only when the provider actually uses it; otherwise exact/date/opaque rules are used. M03 never guesses version ordering.

Proposed compatibility states are:

- `compatible_verified`
- `protocol_incompatible`
- `manifest_invalid`
- `capability_schema_incompatible`
- `extension_schema_incompatible`
- `provider_version_unverified`
- `provider_version_unknown`
- `platform_unsupported`
- `disabled_by_policy`
- `registration_conflict`

`provider_version_unverified` and `provider_version_unknown` do not mean unsupported. They block invocation of version-sensitive sources until live review expands the verified range. One incompatible capability does not remove unrelated compatible capabilities.

### 3.6 Provider operation context

Every invocation receives `ProviderOperationContextV1`, created by the application orchestration layer and containing only:

- operation and correlation IDs;
- UTC request time and a monotonic remaining-deadline budget;
- cancellation port;
- exact negotiated source policy;
- opaque approved path, subprocess, network, and profile/credential access grants;
- safe output/response size bounds;
- owner-interaction authorization where applicable;
- an Experimental policy grant reference when applicable.

The context never contains a raw secret, arbitrary environment map, unrestricted filesystem root, shell string, cookie, bearer value, password, OTP/MFA value, prompt/content, or provider response. Safe executor/network/path/profile interfaces require separate producer ownership and synchronization before M03 implementation.

### 3.7 Operation outcome algebra

`CollectionOutcomeV1[T]` is a closed discriminated union. Exactly one variant is present:

- `success`: complete typed value plus provenance;
- `partial`: usable typed value, explicit missing field/capability codes, warnings, and provenance;
- `unsupported`: evidenced unsupported decision and safe reason;
- `unverified_provider_version`: provider version is unknown or outside the evidenced range;
- `reauthentication_required`;
- `authorization_insufficient`;
- `provider_unavailable`;
- `rate_limited` with optional provider-supported retry-after precision;
- `invalid_provider_data` with schema/parser reason code and no raw value;
- `deadline_exceeded`;
- `blocked_user_action_required`;
- `internal_adapter_error` with a stable safe code and correlation ID.

Capability-disabled is a resolution/manifest state, not an outer operation
outcome. A wrong-account decision is a typed `IdentityVerificationOutcomeV1`
or `ReauthFlowV1` result carried by an outer `success` after the approved
verification operation completes. Caller cancellation publishes no completed
provider outcome: M04 owns the cancelled collection-run state. An operation
whose approved deadline expires still returns `deadline_exceeded`.

`T` is a published typed capability payload, never a generic dictionary or raw provider object. M03 owns envelope validation; M05/M06 or another synchronized producer owns normalized business payload meaning. Provider-specific safe fields appear only in `SafeProviderExtensionV1`.

Every non-success result includes a stable safe code and retry disposition: `never`, `after_delay`, `after_reauthentication`, `after_user_action`, `after_version_review`, or `unknown`. Optional retry time has explicit precision. Free-form exception messages and raw stdout/stderr/HTTP bodies do not cross the adapter boundary.

Expected external states return outcomes rather than exceptions. The invocation gateway catches an adapter boundary exception, preserves protected local diagnostic causality, and returns `internal_adapter_error` after redaction. Contract/programmer invariant violations fail the affected registration or operation visibly; they are never relabeled provider failure.

### 3.8 Provenance

The M03 portion of `ObservationProvenanceV1` requires:

- provider key, capability ID/schema version, adapter ID/version, and provider protocol version;
- actual source descriptor and source/mechanism/parser version;
- provider product/CLI/service version or explicit Unknown;
- provider-reported observation/data-through time when available;
- AgentMonitor collection start/end time and downstream stored time when persistence occurs;
- freshness deadline or explicit Unknown plus the policy identifier used downstream;
- precision: `exact`, `rounded`, `range`, `estimated`, or `unknown`;
- confidence category and stable explanation code;
- value kind: `authoritative`, `provider_reported`, `derived`, `heuristic`, or `unknown`;
- Experimental flag, fallback lineage, sanitized warnings, operation/correlation ID, and M0 decision reference;
- derivation method/input observation IDs only when a downstream domain creates a derived value.

An adapter cannot set `stored_at`; the consuming persistence module adds it. Derived domain results cannot reuse provider-reported provenance without adding derivation metadata. Missing provenance required for the capability changes a purported success into `invalid_provider_data` or an explicitly permitted `partial` result.

### 3.9 Authentication health and identity semantics

`AuthHealthObservationV1` has exactly these Draft-aligned normalized states:

- `healthy`
- `refreshing`
- `expiring`
- `reauthentication_required`
- `revoked_or_disabled`
- `wrong_account_detected`
- `unknown`

It includes observation provenance, optional expiry/precision, safe reason code, and an identity comparison result. Temporary provider unavailability is an outer operation outcome, not an auth-health state.

`IdentityVerificationOutcomeV1` reports `matched`, `mismatched`, or `unresolved` against an opaque expected identity assertion. Stable provider IDs may be carried only when M0 and M02 approve their classification. Email/display text is not identity proof. A mismatch stops reauthentication and cannot mutate M02 state.

`ReauthFlowV1` proposes the lifecycle:

```text
requested -> awaiting_owner_action -> verifying -> succeeded
                                      -> wrong_account_detected
                                      -> failed
requested/awaiting/verifying -> cancelled | expired
```

The lifecycle's `wrong_account_detected` and `cancelled` states are typed
reauthentication/coordinator states. They do not extend the closed
`CollectionOutcomeV1` operation-outcome algebra.

Start is allowed only for an AgentMonitor-managed profile with a known protection classification and a caller authorized through M02 CTR-REG-008. Credentials, passwords, OTP/MFA values, codes, cookies, or secret-bearing URLs never enter a request/result. Instructions are typed safe action categories plus an opaque local flow reference, not captured terminal output. M02 owns durable workflow coordination, persistence, idempotency, restart/cancel truth, and CTR-REG-010 reconciliation; M03 owns only the provider flow protocol. No reauthentication implementation starts before synchronization and M0 approval.

### 3.10 Discovery contracts

`DiscoveryOutcomeV1` uses the same operation-outcome algebra and returns typed, bounded candidates:

- `DiscoveredInstallationV1`: provider key, installation kind, opaque executable/service reference, safe version evidence, platform, compatibility summary, provenance;
- `DiscoveredAccountCandidateV1`: scoped stable provider ID only when approved, resource/identity kind, masked display identity only when approved, evidence strength, owner-confirmation requirement, provenance;
- `DiscoveredProjectCandidateV1`: provider-scoped opaque project/workspace reference and relation evidence;
- `IdentityEvidenceV1`: evidence kind/strength/lifetime/scope and conflict state, never a raw field bag.

M02 validates, confirms, and persists resulting registry concepts. Discovery never creates or links an account directly and never guesses from weak evidence.

### 3.11 Safe provider extensions

`SafeProviderExtensionV1` contains only schema reference and a value that has been validated against an adapter-owned, M03-registered allowlist. An extension schema declares:

- provider/capability/schema identity and version;
- every field name, type, unit, nullability, cardinality, maximum length, and nesting depth;
- privacy classification and proof that the field cannot contain credentials, personal identity beyond approval, prompt/response/tool/source content, arbitrary environment, or raw output;
- compatibility rules and consumer list;
- live evidence and parser version scope.

Allowed value primitives are explicitly bounded null, boolean, integer, exact decimal text, enum, RFC 3339 timestamp, duration, unit-labelled quantity, and approved safe text/opaque identifier. Binary values, arbitrary HTML/Markdown, free-form logs/errors, paths unless explicitly approved, unbounded objects, and unknown fields are rejected.

Adapters own extension schemas under their approved contract paths; M03 governs registration and compatibility. Downstream consumers may expose only schemas they understand. Unknown extension major versions remain visible as unsupported metadata and are neither persisted as opaque JSON nor rendered.

### 3.12 Idempotency, concurrency, and failure isolation

- Registration is single-writer during composition startup. Exact repeated registration is idempotent; conflicting reuse of provider/adapter keys fails startup readiness for that adapter only and is visible to M08.
- Compatibility assessments deduplicate on a canonical input fingerprint while retaining immutable history when inputs change.
- Read-only operation IDs support audit/deduplication but do not authorize automatic retries. M04 owns retry policy.
- Reauthentication is state-changing and is never blindly retried. M02's CTR-REG-008 coordinator defines durable idempotency, active-workflow reuse, conflict, cancellation, restart, and expiry behavior; M03 only validates the protocol transition and returns a typed safe outcome.
- M03 catalog reads are concurrency-safe. One adapter invocation cannot mutate another adapter registration.
- Deadlines/cancellation are explicit. M03 does not extend a caller deadline or retry after rate limit/auth/version failure.
- An adapter exception, invalid result, or compatibility failure is contained to its provider/capability invocation.

## 4. Public contracts

All contracts below are Proposed and require CS synchronization. The producer owns meaning; consumers cannot redefine fields or status mappings.

### 4.1 CTR-PROV-001 — `ProviderAdapterV1` target `1.0.0`

The current architecture artifact is `1.0.0-draft.2`. The contract baseline
proposes `1.0.0`; that target is not Approved until M0 evidence and the named
producer/consumer review complete.

Published contracts/ports:

- `ProviderAdapterV1`: exposes immutable descriptor/manifest and typed capability-port resolution; it has no general-purpose `execute(dict)` escape hatch.
- `RegisterProviderAdapterV1`: composition-only command; validates and registers a statically supplied admitted production adapter.
- `ListProviderAdaptersV1` / `GetProviderAdapterV1`: safe descriptor/registration/compatibility queries for M04/M08.
- `ResolveProviderCapabilityV1`: resolves provider, target, capability schema, source policy, platform, provider version, and Experimental grant before I/O.
- `InvokeProviderCapabilityV1[TRequest,TResult]`: gateway for an already resolved typed port.
- capability-specific ports: installation discovery, account/project discovery, identity verification, auth health, managed reauthentication, telemetry collection, local-session discovery/metrics/correlation, model catalog, and diagnostics.

Preconditions: registered compatible adapter, validated typed request, known deadline, approved target/source/access grants, caller orchestration authorization, and no protected-profile mutation. Postconditions: one validated outcome, bounded safe diagnostics, compatibility/health update as specified, and no cross-adapter effect.

`RegisterProviderAdapterV1` is idempotent only for an exact same descriptor/fingerprint/factory registration. Provider operations are observational unless the declared, authorized managed-profile reauthentication capability says otherwise. M03 has no public user authorization endpoint; P01/M01 and the M02-owned CTR-REG-008 workflow authorize callers before these internal ports.

#### Application port signatures and behavior

The names below are language-neutral contract names. Exact Python signatures follow these fields and do not add untyped keyword bags.

| Port | Input | Success result | Typed M03 errors | Idempotency/authorization |
|---|---|---|---|---|
| `RegisterProviderAdapterV1` | admitted production `ProviderAdapterV1` instance, descriptor, manifest, registration correlation | `AdapterRegistrationViewV1` with registration ID, fingerprint, protocol/capability states | `invalid_manifest`, `protocol_incompatible`, `registration_conflict`, `extension_schema_incompatible` | Composition-only; exact same registration is idempotent, different reuse conflicts |
| `ListProviderAdaptersV1` | bounded status/provider/capability filters and page request | bounded page of `AdapterRegistrationViewV1` | `invalid_query`, `persistence_unavailable` where assessment enrichment is required | Authorized internal/read-status query; no side effect |
| `GetProviderAdapterV1` | registration ID | one safe registration view | `not_found`, `persistence_unavailable` | Authorized internal/read-status query; no existence detail beyond caller permission |
| `ResolveProviderCapabilityV1` | target, capability/schema, provider/platform version evidence, requested source policy, Experimental grant reference | `CapabilityResolutionV1` containing exact registration, typed port reference, source policy, compatibility assessment | `not_registered`, `capability_not_declared`, `unsupported`, `capability_disabled`, `protocol_incompatible`, `schema_incompatible`, `provider_version_unverified`, `unsafe_profile` | Read-only deterministic resolution; same inputs/fingerprint yield same decision |
| `AssessProviderCompatibilityV1` | registration, optional installation scalar ID, provider/platform version evidence, capability/source | immutable `CompatibilityAssessmentViewV1` | `invalid_version_evidence`, `registration_not_found`, `persistence_unavailable`, `conflict` | Authorized orchestration/operations; canonical identical input deduplicates |
| `InvokeProviderCapabilityV1[TRequest,TResult]` | prior resolution, typed request, `ProviderOperationContextV1` | exactly one `CollectionOutcomeV1[TResult]` | Pre-I/O M03 validation errors only; all external outcomes use CTR-PROV-004 | Authorized application orchestrator only; operation ID records identity but M04 decides retry |
| `GetProviderSystemHealthV1` | correlation and disclosure scope | bounded M03 component-health projection | `persistence_unavailable` represented as degraded health | M08/internal read-status; no provider invocation |

`ProviderSystemErrorV1` is a closed M03 application-error union with stable code, correlation ID, safe contract subject, and optional retry disposition. It contains no free-form provider message. Programmer misuse such as passing a result type that does not match the resolved capability is an invariant violation and fails the affected operation visibly.

#### Capability port requests and results

Every request begins with `ProviderOperationRequestHeaderV1`: operation ID, correlation ID, provider/capability/schema identity, `ProviderTargetV1`, request time, bounded deadline, resolved source-policy reference, and approved access-grant references. It contains no credential, arbitrary query map, environment, raw path, or raw provider identifier not approved by the target contract.

| Capability port | Capability-specific request | Typed value in `CollectionOutcomeV1[T]` | Primary consumer/semantic owner |
|---|---|---|---|
| `InstallationDiscoveryPortV1` | provider/platform scope and approved discovery-root grants | bounded list of `DiscoveredInstallationV1` | M02 Registry |
| `AccountDiscoveryPortV1` | installation target and approved profile scope | bounded list of `DiscoveredAccountCandidateV1` | M02 Registry |
| `ProjectDiscoveryPortV1` | confirmed account/profile target and provider-supported page/window request | bounded list of `DiscoveredProjectCandidateV1` | M02 Registry |
| `IdentityVerificationPortV1` | target plus opaque expected-identity assertion | `IdentityVerificationResultV1` | M02 Registry |
| `AuthenticationHealthPortV1` | target and expected-identity assertion when known | `AuthHealthObservationV1` | M02 Registry; M04 outcome policy |
| `ReauthenticationPortV1` | typed start/status/verify/cancel request, managed target, flow ID, expected identity | `ReauthFlowV1`/`ReauthResultV1` | M02 CTR-REG-008 coordinator; adapters implement protocol operations |
| `SubscriptionQuotaPortV1` | target and provider-supported observation scope only | M05-owned `ProviderQuotaInputV1` proposal | M05 Capacity |
| `ApiUsagePortV1` | target plus bounded provider-supported time/group/page request | M05-owned `ProviderUsageInputV1` proposal | M05 Capacity |
| `ApiCostPortV1` | target plus bounded provider-supported time/group/page request | M05-owned `ProviderCostInputV1` proposal | M05 Capacity |
| `ApiBudgetPortV1` | target and provider-supported billing resource scope | M05-owned `ProviderBudgetInputV1` proposal | M05 Capacity |
| `ModelCatalogPortV1` | confirmed provider/account/project scope and page request | synchronized typed model-catalog input contract | Owner resolved at CS; M03 does not invent catalog semantics |
| `LocalSessionDiscoveryPortV1` | installation/profile scope and approved local-source grants | M06-owned bounded session-input collection | M06 Runtime observation |
| `LocalSessionMetricsPortV1` | confirmed safe session reference and approved local-source grants | M06-owned runtime-metric input | M06 Runtime observation |
| `LocalProcessCorrelationPortV1` | safe process/session references and evidence only | M06-owned correlation-evidence input | M06 Runtime observation |
| `ProviderDiagnosticsPortV1` | installation/profile reference and disclosure scope | `SanitizedProviderDiagnosticsV1` | M08 Operations |

Time grouping, pagination, account/project scope, quota fields, money, model, session, and process payloads are defined by their semantic owners after M0. Their names above are planning proposals and must be replaced by the exact synchronized contract IDs before approval. Absence of such a typed payload blocks that capability; it never permits a dictionary result.

### 4.2 CTR-PROV-002 — `CapabilityManifestV1`

Publishes `AdapterDescriptorV1`, `CapabilityManifestV1`, `CapabilityDeclarationV1`, `CapabilityDecisionV1`, `ProtocolVersionRangeV1`, `ProviderVersionRuleV1`, `CollectionConstraintV1`, `SideEffectClassV1`, and compatibility summaries.

The M0 discovery evidence record is `M0CapabilityDecisionV1`; it is evidence consumed through its approved provider or platform decision set, not the same contract type as the M03-owned production `CapabilityDecisionV1`. Direct re-export, aliasing, and identity transformation are forbidden. Before CTR-PROV-002 approval, M03 must publish and review an explicit `M0ToM03CapabilityMappingV1` transformation that preserves the approved M0 decision, evidence lineage, confidence, gaps, and applicability while translating only into fields whose production semantics are owned here. The mapping binds the exact M0 schema-bundle digest and the exact CTR-PROV-002 version, schema digest, and complete normative contract-bundle digest; any change supersedes the mapping and requires a new review and approvals.

The terminal M0-to-M03 gate is a current technical `M0HandoffAcceptanceV1`
for `PLAN-M03` binding the unique evidence ledger, provider/platform decision
sets, authoritative scenario status, and exact mapping ID, version, and digest.
Detached owner, security/privacy, test-integrity, and root-integration records
remain advisory governance evidence and are not an executable prerequisite.
Stale or technically incomplete mappings still block capability synchronization;
the local technical preflight is the sole prerequisite for claiming
CTR-PROV-002 conformance.

Compatibility promise: optional fields may be added in V1 minor revisions only with safe absence behavior. Capability meaning, source class, decision meaning, credential role, side-effect class, or version interpretation cannot change without a new major/ADR.

### 4.3 CTR-PROV-003 — `ProviderSourceV1`

Publishes source classes, source descriptor, explicit source chain, stability, credential role, side-effect, and fallback lineage. The order above is normative. Adding a new source class is contract review; moving an existing mechanism to a weaker class is a security/provider review, not a compatible editorial change.

### 4.4 CTR-PROV-004 — `CollectionOutcomeV1[T]`

Publishes the closed outcome union, `SafeProviderErrorV1`, `RetryDispositionV1`, `MissingFieldV1`, `SanitizedWarningV1`, `ProviderOperationContextV1`, and provenance link. It never exposes provider exception instances, raw payloads, stdout/stderr, or generic dictionaries.

Consumer allocation:

- M04 owns run scheduling, retries, and run-state mapping.
- M05/M06 own validation and persistence of the typed business payload.
- M07 consumes domain events, not raw provider outcomes.
- M08 consumes safe component/compatibility health, not provider raw data.

### 4.5 CTR-PROV-005 — `DiscoveryOutcomeV1`

Publishes typed installation/account/project/identity-evidence candidates. Discovery is read-only, may require owner confirmation, and never persists/link accounts. M02 is the authoritative consumer and may reject or leave candidates unresolved.

### 4.6 CTR-PROV-006 — `AuthHealthOutcomeV1`

Publishes the outer operation outcome plus `AuthHealthObservationV1` and `IdentityComparisonV1`. `unknown`, provider unavailability, `reauthentication_required`, revoked/disabled, and wrong-account are distinct. M02 consumes identity/profile state and produces CTR-REG-010; M04 consumes retry/no-retry semantics; M07 consumes CTR-REG-010 and CTR-COL-007 rather than invoking M03.

### 4.7 CTR-PROV-007 — `ReauthFlowV1`

Publishes start/status/verify/cancel typed protocol semantics, flow state, expected-identity assertion, protected-profile rejection, owner-action category, expiry, and safe outcomes. It does not define REST routes, accept credentials, or own workflow persistence. M02 CTR-REG-008 owns coordination, persistence, idempotency, lifecycle, restart/cancel recovery, and P01 handoff; M04 only consumes approved recovery state.

### 4.8 CTR-PROV-008 — provider extension schemas

Publishes `ExtensionSchemaDescriptorV1`, `ExtensionFieldDescriptorV1`, `SafeProviderExtensionV1`, validation errors, privacy approval state, and compatibility rules. Each adapter is schema producer; M03 owns registry/governance; M05/M06/API/UI explicitly opt in as consumers.

### 4.9 Compatibility and availability events

Proposed M03 events using `EventEnvelopeV1`:

- `ProviderAdapterAvailabilityChangedV1`: adapter registration key, previous/current safe availability, reason code, adapter/protocol/manifest versions, occurred/recorded times.
- `ProviderCompatibilityAssessedV1`: assessment ID, installation/capability/source scalar references, previous/current compatibility state, safe version evidence, manifest fingerprint, reason code.

Delivery follows CTR-EVT-001: the M03 state change and producer-owned outbox append atomically; consumers own receipts/checkpoints, deduplicate by event ID, reject incompatible majors, and support bounded restart/replay and poison/backlog visibility. Ordering is guaranteed only per adapter-registration or installation-capability assessment stream. Events contain no account identity, profile path, credential, raw provider data, extension payload, or arbitrary error text. M04 and M08 are known consumers. Registration-at-startup emits a durable event only when the registered compatibility state actually changes.

### 4.10 Consumed contracts and failure behavior

| Contract | Owner | Use | Failure/degradation |
|---|---|---|---|
| CTR-COMMON-001 `OpaqueIdV1` | Foundation/contracts | All internal IDs | Invalid input rejected before adapter call |
| CTR-COMMON-002 `TimestampAndDurationV1` | Foundation/contracts | Observation/deadline/duration semantics | Invalid/naive time rejected; monotonic vs wall time kept distinct |
| CTR-COMMON-004 `ObservationProvenanceV1` | M03 + foundation primitives | Every provider result | Missing mandatory provenance invalidates success |
| CTR-COMMON-006 `EventEnvelopeV1` | Foundation/contracts | M03 events | Event publication failure follows synchronized outbox policy; not hidden |
| CTR-COMMON-007 `FieldAvailabilityV1` | Foundation/contracts | Every optional provider field and capability result | Invalid state/value combination rejects the result; absence never becomes zero |
| CTR-EVT-001 | PLAN-INT governance/PLAN-DB infrastructure | Durable event outbox, consumer receipt/checkpoint, replay | Consumer outage never rolls back provider-system state; backlog stays visible |
| CTR-FND-004 correlation/safe-log | Foundation | Correlation and logs | Operation continues only if safe required context exists |
| CTR-FND-006 migration metadata | Foundation/DB | M03 migration allocation | Writable startup refuses incompatible schema |
| CTR-REG-003/004 or mapped target contract | M02 | Profile protection and installation identity | Missing/unknown protection blocks mutation; collection target unresolved |
| CTR-DB-002 repository/UoW | Domain/DB | Compatibility records/outbox | Typed unavailable/conflict; unrelated adapters remain queryable |
| CTR-BOUNDARY-001/003 | Foundation portable-boundary steward | Restricted subprocess and approved-root/file access supplied to adapters | Missing grant returns disabled/blocked before provider I/O |
| CTR-BOUNDARY-002 | M03 | Restricted provider HTTP execution policy implemented by provider adapters | TLS/host/redirect/body/deadline/rate or redaction violation fails closed |
| M05/M06 typed provider-input payload contracts | M05/M06 | Generic outcome payload `T` | Unknown schema is non-invokable, not opaque fallback |
| CTR-OPS-006 component health | M08 | Safe health projection | M08 timeout must not reach into M03 tables |
| CTR-OPS-007 participant family | M08 | M03 retention/export/consistency implementation | Bounded typed failure; no M08 table access or provider call |

M03 must not import full M02 views merely to obtain provider targets if a narrower target/protection contract is sufficient. The exact narrow contract is a CS decision.

### 4.11 Contract impact assessment

This plan proposes all CTR-PROV contracts and the provider-owned portion of CTR-COMMON-004. It does not change an implemented contract because none exists. Before approval, the root must:

1. reconcile generic outcome envelopes with M05/M06-owned payload types;
2. allocate safe execution/network/path/profile ports and owners;
3. reconcile provider target/protection data with M02 without cyclic imports;
4. decide M03 compatibility persistence and event/outbox ownership;
5. verify the aligned split: M02 owns CTR-REG-008/010 coordination and durable truth, M03 owns CTR-PROV-007 protocol, P01 maps CTR-REG-008 only, and M04 consumes recovery;
6. update the central register from Concept to synchronized Proposed/Approved states;
7. add an ADR only if the synchronized design departs from ADR-0005/0007 or introduces dynamic plugin/private-browser behavior.

## 5. Data and persistence

### 5.1 Owned data

M03 proposes one immutable compatibility-history table. Runtime registration and extension-schema registries are built from statically admitted code at startup and are not user-editable database plugin catalogs.

#### `provider_system_compatibility_assessments`

- `assessment_id`: opaque primary key;
- `registration_id`: deterministic runtime registration reference;
- `provider_key`, `adapter_id`, `adapter_version`, `protocol_version`;
- nullable scalar `installation_id` owned by M02, with no cross-module foreign key unless an ADR approves it;
- capability ID/schema version and nullable source ID;
- safe provider-version value, version-scheme identifier, and version-rule ID, each nullable/Unknown-aware;
- compatibility state and stable reason code;
- manifest schema version/fingerprint;
- assessed-at UTC, optional valid-until UTC, superseded assessment ID, correlation ID;
- safe M0/live evidence reference identifier only, never a local path or raw output.

No account/profile credential reference, provider payload, quota/budget/process/session fact, extension value, path, prompt/content, personal identity, or free-form provider error is stored.

Proposed indexes:

- `(provider_key, adapter_id, installation_id, capability_id, assessed_at DESC)` for latest assessment;
- `(compatibility_state, assessed_at DESC)` for health review;
- `(manifest_fingerprint, provider_version_value, capability_id)` for safe deduplication;
- `(assessed_at)` for retention.

Constraints enforce bounded enums/strings, UTC timestamps, required version/fingerprint relationships, valid supersession, and capability/source nullability. Exact DDL and indexes require PLAN-DB review and real query plans.

#### M03 event outbox

CTR-EVT-TOPOLOGY-001 allocates `provider_system_event_outbox` and its migration to M03. A changed compatibility assessment and its outbox row commit or roll back together. PLAN-DB provides reusable claim/delivery persistence mechanics and reaches the rows only through M03's published event-storage port; consumers commit their own receipts/checkpoints under their own prefixes. A central event journal and direct writes to another module's table are prohibited. Owner approval of this Draft allocation still blocks event implementation, while pure protocol work remains separately gated.

### 5.2 Transactions and concurrency

- Registration is in-memory startup composition and performs no hidden DDL.
- A compatibility assessment and its changed-state event are committed atomically when an outbox is used.
- An unchanged canonical input fingerprint returns/reuses the current assessment without duplicating history.
- Conflicting concurrent assessments use optimistic version/current-row selection or a DB-supported uniqueness rule defined with PLAN-DB.
- Provider calls do not run inside database transactions.
- M03 never joins M02/M04/M05/M06 tables; cross-module IDs are scalar references validated through ports.

### 5.3 Migration, retention, backup, and restore

- One centrally allocated expand-only M03 migration creates its owned table(s).
- Fresh install and every supported prior schema are tested with a real file-backed SQLite database.
- No application startup `create_all` is permitted.
- Compatibility history is proposed for 365-day retention, while the latest active assessment per registration/capability is retained until superseded/adapter removal. This policy requires M08/data-owner review because FR-HIST does not explicitly name M03 compatibility history.
- Purge uses a pure cutoff calculation and a real bounded transaction; it cannot remove the current assessment.
- Backup/restore is exercised by M08 against the real DB. M03 post-restore validation rebuilds the runtime catalog from code and reassesses restored compatibility records without invoking a provider until normal approved collection.
- Downgrade is provided only if real and safe. Otherwise rollback is prior binary plus verified backup; forward-fix is preferred after shared migration use.
- PostgreSQL portability review covers enum representation, timestamp precision, unique indexes, canonical fingerprint, and transaction conflict mapping.

## 6. External and platform boundaries

M03 performs no provider-specific I/O itself. It defines and enforces the boundary through which admitted adapters receive restricted capabilities.

### 6.1 Boundary requirements

| Boundary | Required port behavior | M03 enforcement | Real verification |
|---|---|---|---|
| Provider API | HTTPS allowlist, verified TLS, bounded method/host/redirect/body/time, credential bound to host | Context contains approved network grant; outcome/provenance validation | Real adapter/provider request under M0/live packet |
| Provider CLI | Absolute executable identity, argument vector, minimal environment, no secret args, deadline/output bound, process-group cancellation | Manifest/source/side-effect checks before grant; raw output cannot cross result | Real installed CLI and owner-approved command |
| Provider local metadata | Approved root/path/file/field allowlist, symlink/type/owner/size/time bounds | Context exposes scoped path grant; extension/result validator rejects unknown fields | Real approved local file/version |
| Provider profile | Opaque reference, provider-owned credentials, protected-default classification | Reauth rejected for protected/unknown; no credential accessor in result | Owner-coordinated managed-profile flow after M0 |
| Platform process/session | Safe platform port, no environment/memory/terminal/control | Capability and payload schema prohibit unsafe fields | Real Linux process/session via A04/M06/adapters |

### 6.2 Timeouts, retries, rate limits, and cost

- M04 selects schedule, deadline, concurrency, retry, and backoff within M0-proven constraints.
- M03 validates a finite deadline and passes cancellation; it never retries or extends the deadline.
- Adapters report provider retry hints without deciding global scheduling.
- Authentication, authorization, wrong-account, invalid-data, unverified-version, and protected-profile outcomes are no-retry until the owning state changes.
- Rate-limit/request/cost fields in a manifest are Unknown until supported by official evidence. Unknown cost/rate blocks automated polling for that source at M04 approval.
- Provider calls cannot create billable model generations merely to collect telemetry unless a separately approved product requirement and cost plan later permits it.

### 6.3 Provider conformance matrix

Each A01/A02/A03 adapter has a separate matrix keyed by:

```text
provider product + capability + source + adapter version
+ provider/tool version + plan/account/resource class
+ credential role + platform + extension schema version
```

The matrix records manifest decision, real scenario IDs, status, side effects, source/field scope, and evidence reference. Passing one provider/version tuple never establishes another. M03 aggregates statuses but does not generalize them.

## 7. Security and privacy

### 7.1 Trust boundaries and controls

- Concrete adapters and their provider inputs are untrusted at the M03 validation boundary even though adapter packages are admitted code.
- V1 uses static composition only. Dynamic plugin discovery/import requires a new threat model, signature/sandbox/update design, ADR, and owner approval.
- Requests/results use typed allowlists and strict bounds. Unknown fields, capability schema majors, extension fields, and status values fail safely.
- Profile references and access grants are opaque. Secret values never enter manifests, DTOs, events, compatibility records, logs, diagnostics, OpenAPI, or tests.
- The adapter invocation gateway emits only stable safe codes, IDs, versions, timings, and bounded classifications.
- Raw provider bodies/stdout/stderr/provider objects are discarded inside the owning adapter after allowlisted extraction and never retained for replay.
- Default profiles are always protected against mutation; unknown protection is treated as protected.
- No M03 contract authorizes process signaling, restart, injection, terminal access, memory access, arbitrary environment access, routing, or account switching in a running agent.

### 7.2 Data-minimization proof

The module's persisted schema contains only code/provider version compatibility metadata and safe references. A field inventory must demonstrate absence of:

- passwords, API/OAuth/session tokens, cookies, auth headers, OTP/MFA/recovery values;
- full email or unnecessary personal identity;
- prompt, response, tool, terminal, source-code, or arbitrary provider payload content;
- arbitrary environment values, process memory, or provider profile contents;
- quota, money, budget, token, process, session, or alert observations owned elsewhere.

Safe IDs are not automatically non-sensitive; UI/API disclosure remains permissioned by P01/M08. Diagnostics expose versions and safe reason codes, not local paths or account identity.

### 7.3 Threat/control matrix

| Threat | Control | Tests |
|---|---|---|
| Malicious/changed provider output injects content | Typed bounded payload and extension allowlists; reject unknown fields; no raw persistence | M03-SEC-002/005/009, M03-CONF-006 |
| Adapter leaks secret in error/log | Stable error codes, bounded gateway redaction, artifact scan | M03-SEC-001/007/010 |
| Source silently downgrades | Exact negotiated source/chain and actual-source provenance | M03-PURE-011..013, M03-CONF-002 |
| Default profile modified during auth flow | Protected/unknown rejection before invocation, managed-only contract, real pre/post verification | M03-SEC-003/004, M03-LIVE-008 |
| Wrong account linked | Expected identity assertion and mismatch outcome; M02 state unchanged | M03-PURE-023/026, M03-LIVE-007 |
| Arbitrary adapter/plugin executes | Static composition/admission; no runtime import path | M03-ARCH-003, M03-SEC-006 |
| Provider-version drift parsed as known | Version gate and unverified outcome | M03-PURE-008..010, M03-CONF-003 |
| One adapter crashes service | Boundary containment and per-adapter health | M03-INT-005, M03-LIVE-009 |
| Extension becomes covert raw payload | Schema/privacy registration, size/type bounds, known-consumer opt-in | M03-PURE-028..030, M03-SEC-009 |
| Outcome/log captures prohibited content | Allowlisted serialization and real DB/log/diagnostic scans | M03-SEC-008/010 |

Security stop conditions appear in section 13.4.

## 8. Configuration and operations

### 8.1 Configuration ownership

M03 requires no provider credential, endpoint, path, polling interval, or profile secret in its own configuration. Those belong to provider adapters, registry profiles, collection control, safe boundary adapters, or deployment.

Potential M03 settings are intentionally not allocated yet:

| Proposed policy | Owner/status | Rule |
|---|---|---|
| Experimental capability opt-in | Likely M02 profile/runtime configuration; unresolved | Explicit per provider/profile/capability/source, default false, audited |
| Manifest/extension size bounds | M03 code policy, not necessarily operator configurable | Secure defaults; changes versioned and tested |
| Compatibility review/expiry policy | M03/M08; unresolved | Cannot silently expand provider-version support |
| Compatibility-history retention | M03/M08; proposed 365 days | Must preserve current assessment |

No `AGENTMONITOR_*` key is created until the configuration registry assigns owner, type, default, visibility, reload behavior, and compatibility version. M03 diagnostics report only safe effective policy and secret presence is not relevant.

### 8.2 Health and readiness

M03 publishes a bounded component-health projection through CTR-OPS-006 containing:

- protocol/catalog initialized state;
- count of registered/compatible/incompatible/disabled adapters and capabilities;
- safe adapter/protocol/manifest/provider-version summaries;
- latest compatibility assessment time/status;
- persistence availability and last safe event publication status;
- stable reason codes and correlation IDs.

Readiness fails for an invalid M03 schema/migration or a registration conflict affecting a required adapter. A single optional adapter incompatibility degrades provider-specific readiness but must not make unrelated API/dashboard queries unavailable. Exact global readiness aggregation belongs to M08.

### 8.3 Logging and local metrics

Structured events may include component, event name, correlation/operation ID, provider key, adapter/capability/source IDs, safe versions, outcome code, duration, retry disposition, and compatibility state. They exclude target account/profile identity unless an approved opaque internal ID is required, plus all raw arguments/output and exception messages.

Local operational metrics may count invocation outcomes/durations by adapter/capability/source and compatibility states. Metric labels are bounded and contain no account aliases, paths, credentials, provider values, or dynamic raw errors. There is no external telemetry or crash reporting.

### 8.4 Operator procedures

The module documentation must eventually provide verified procedures for:

- list registered adapter/capability/compatibility summaries through authenticated diagnostics;
- identify version drift and required live reverification;
- distinguish Unsupported, disabled Experimental, auth-required, unavailable, and invalid-data outcomes;
- retire/upgrade an adapter without deleting registry or telemetry history;
- restore database then rebuild/reassess the runtime catalog;
- execute the real adapter conformance/live matrix with the owner;
- respond to a secret/content or default-profile safety incident.

No command is documented as executable until it exists and is verified. Until then all commands are `TBD`.

## 9. Test design before implementation

### 9.1 Integrity rules

- Pure M03 tests construct manifests, version descriptors, capability declarations, outcomes, timestamps, and extension values only to test deterministic domain policy. They perform no I/O and instantiate no fake adapter.
- A fake/stub adapter is prohibited even for catalog or exception tests. Pure catalog policy accepts immutable descriptor/manifest values. Adapter-object/conformance behavior is tested only with real A01/A02/A03 production adapters.
- Persistence tests use the production repository, real Alembic chain, and a real temporary SQLite file.
- Service/API/operations integration uses the real application server and production composition; direct route calls do not count.
- Provider/platform claims use real installed providers/accounts/processes under the live-verification runbook. No response recordings or provider fixtures are retained.
- Naturally unavailable auth, rate-limit, exhaustion, version-drift, or outage cases remain Blocked. They are not manufactured by revoking credentials, spending credits, editing provider files, or installing old versions.
- Every behavior records expected behavioral Red, Green, and post-refactor evidence. Missing dependencies, missing credentials, syntax errors, or unavailable providers do not satisfy Red.

### 9.2 Pure domain and contract inventory

| Test ID | Behavior and initial Red | Pass condition |
|---|---|---|
| M03-PURE-001 | Capability ID validation absent | Known/valid names accepted; malformed/unbounded rejected |
| M03-PURE-002 | Discovery-decision states not modeled | Supported/Experimental/Deferred/Unsupported/Unknown remain distinct |
| M03-PURE-003 | Runtime availability conflates Unsupported/Unavailable/Unknown | Every distinction survives mapping |
| M03-PURE-004 | Protocol same-major compatibility not enforced | Approved same-major range resolves deterministically |
| M03-PURE-005 | Protocol major mismatch accepted | Registration rejects incompatible major with safe reason |
| M03-PURE-006 | Manifest accepts duplicate/missing capability declarations | Canonical uniqueness/completeness rules enforced |
| M03-PURE-007 | Manifest permits missing constraint/side-effect classifications | Required known-or-Unknown fields enforced |
| M03-PURE-008 | Provider opaque versions are ordered as semantic versions | Only declared evidenced version scheme is used |
| M03-PURE-009 | Capability schema major mismatch resolves | Only mutually supported major/minor resolves |
| M03-PURE-010 | Out-of-range/unknown provider version invokes parser | Resolution returns unverified before I/O |
| M03-PURE-011 | Source priority/fallback absent | Higher-class exact source selected only from approved candidates |
| M03-PURE-012 | Experimental source runs without grant | Resolution returns capability disabled |
| M03-PURE-013 | Failed source silently downgrades | Unapproved transition is rejected and provenance cannot claim another source |
| M03-PURE-014 | Outcome allows multiple/no variants | Closed union enforces exactly one variant |
| M03-PURE-015 | Partial result lacks missing-field/provenance evidence | Partial requires value, omissions, warnings, provenance |
| M03-PURE-016 | Unsupported/unavailable/auth/version errors collapse | Exact typed outcome and retry disposition preserved |
| M03-PURE-017 | Provenance lacks source/version/timestamps | Mandatory fields or explicit Unknown enforced |
| M03-PURE-018 | Stale/unknown freshness appears current | Freshness state remains explicit; no default zero/current |
| M03-PURE-019 | Local result omits parser/provider version | Result invalid or permitted partial per capability schema |
| M03-PURE-020 | Time/precision/confidence/value-kind semantics invalid | UTC/enum/relationship invariants enforced |
| M03-PURE-021 | Auth state vocabulary incomplete | All seven required states round-trip distinctly |
| M03-PURE-022 | Provider unavailable mapped to auth Unknown | Outer failure remains separate from auth observation |
| M03-PURE-023 | Identity mismatch accepted as match | Mismatch/unresolved stop automatic association |
| M03-PURE-024 | Auth expiry without precision is implied exact | Expiry and precision/Unknown relationship enforced |
| M03-PURE-025 | Reauth permits protected/unknown profile | Rejected before adapter resolution |
| M03-PURE-026 | Wrong account completes reauth | Flow transitions to mismatch terminal state |
| M03-PURE-027 | Invalid/replayed reauth transitions accepted | State machine and idempotency/conflict rules enforced |
| M03-PURE-028 | Extension accepts unknown/unbounded field | Field/type/cardinality/size allowlist enforced |
| M03-PURE-029 | Unknown extension major is persisted/renderable | Marked incompatible and payload rejected |
| M03-PURE-030 | Extension privacy classification missing | Registration fails closed |
| M03-PURE-031 | Duplicate exact registration conflicts | Exact replay is idempotent |
| M03-PURE-032 | Different adapter reuses a registration key | Conflict returned; existing registration unchanged |
| M03-PURE-033 | One incompatible capability disables all | Compatible capabilities remain resolvable |
| M03-PURE-034 | Retry disposition contradicts outcome | Cross-field policy rejects invalid retry advice |

### 9.3 Real persistence inventory

| Test ID | Real dependency and initial Red | Pass condition |
|---|---|---|
| M03-DB-001 | Empty real SQLite file lacks M03 schema | Full real Alembic chain creates owned schema/constraints |
| M03-DB-002 | Compatibility assessment cannot round-trip exact fields | Production repository preserves IDs/versions/states/times |
| M03-DB-003 | Duplicate canonical input creates duplicate current record | Deduplication is atomic and deterministic |
| M03-DB-004 | Changed manifest/provider version overwrites history | Immutable new assessment supersedes prior record |
| M03-DB-005 | Concurrent assessments lose/conflict silently | One documented current result, typed conflict/retry behavior |
| M03-DB-006 | Latest-assessment query crosses tables/unbounded scan | Bounded indexed query returns correct current assessment |
| M03-DB-007 | Purge deletes current assessment | Expired non-current history only is removed in real transaction |
| M03-DB-008 | Invalid enum/time/fingerprint rows persist | DB constraints reject material invalid state |
| M03-DB-009 | Repository outage leaks generic exception | Typed safe failure; unrelated catalog reads remain available |
| M03-DB-010 | Schema newer/older incompatibility accepted | Startup compatibility policy refuses unsafe writable service |
| M03-DB-011 | Backup/restore loses compatibility state | Real restored DB passes integrity and repository queries |
| M03-DB-012 | SQLite-specific repository behavior enters domain | Portability review and alternate-dialect-safe mappings pass |
| M03-DB-013 | Assessment/event can split across commits | Real transaction commits both or neither when outbox selected |

### 9.4 Architecture, integration, and conformance inventory

| Test ID | Layer/real dependency | Initial failure expected | Pass condition |
|---|---|---|---|
| M03-ARCH-001 | Static architecture | Forbidden framework/provider/OS imports not checked | Boundary gate rejects them |
| M03-ARCH-002 | Contract review | M03 or consumer imports another module's internals/tables | Only public contracts/ports used |
| M03-ARCH-003 | Composition/static review | Dynamic plugin/import entry exists | Only statically admitted factories are loadable |
| M03-ARCH-004 | Contract compatibility | Contract diff not classified | Compatible/breaking diff and ADR rule enforced |
| M03-INT-001 | Real production composition | M03 catalog unavailable at startup | Production app registers admitted real adapters deterministically |
| M03-INT-002 | Real service/SQLite | M08 cannot query safe health via port | Safe bounded health available without table access |
| M03-INT-003 | Real service/event persistence | Compatibility change not delivered/idempotent | At-least-once event and dedup behavior verified |
| M03-INT-004 | Real consumer compilation | M04/M05/M06 contract assumptions diverge | All known consumers compile/test against same approved contracts |
| M03-INT-005 | Real production adapter failure | Failure escapes gateway or affects unrelated adapter/API | Typed contained failure; unrelated service remains available |
| M03-CONF-001 | Real adapter/provider | Production adapter omits required provenance | Every successful/partial result validates |
| M03-CONF-002 | Real adapter/provider | Actual source differs from negotiation | Actual source/fallback lineage matches approved policy |
| M03-CONF-003 | Real installed provider version | Manifest/version rule differs from M0 range | Correct compatible or unverified decision, never silent parse |
| M03-CONF-004 | Real subscription adapter | Capability declaration differs from M0 quota decision | Manifest/port/result match exact evidenced scope |
| M03-CONF-005 | Real API adapter/account | Capability declaration differs from M0 role/budget decision | Manifest/port/result match exact evidenced scope |
| M03-CONF-006 | Real CLI/file/service source | Parser/version/extension allowlist not enforceable | Only approved fields cross boundary; raw data absent |
| M03-CONF-007 | Real provider source | Rate/cost/deadline constraints missing or contradicted | Exact constraints/Unknown state match M0 evidence |
| M03-CONF-008 | Real adapter diagnostic | Diagnostic contains raw output/path/identity | Only safe bounded diagnostic contract returned |
| M03-CONF-009 | Real A01/A02/A03 adapters | Same protocol interpreted differently | Common outcome/source/auth/version semantics conform |
| M03-CONF-010 | Real composition restart | Registration/assessment behavior is unstable | Catalog rebuild is deterministic; history remains coherent |

M03-INT-005 and any conformance case requiring a naturally failing provider remain Blocked until an appropriate real state exists. No exception-throwing test adapter is allowed.

### 9.5 Security, operations, performance, and live inventory

| Test ID | Layer | Real dependencies | Pass condition |
|---|---|---|---|
| M03-SEC-001 | Security/real logs | Production logging | No credential/raw error enters logs |
| M03-SEC-002 | Security/real result | Real provider output path | Prompt/response/tool/source/raw fields absent |
| M03-SEC-003 | Pure boundary | Constructed protected target | Reauth rejected before port resolution |
| M03-SEC-004 | Live | Real default profile, owner-approved non-secret checks | Profile remains unchanged; no auth command invoked against it |
| M03-SEC-005 | Contract/security | Real outcome/provenance | No cached/invented/unapproved source presented current |
| M03-SEC-006 | Architecture | Real repository source | No control/routing/dynamic-plugin surface exists |
| M03-SEC-007 | Real service | Production gateway exception handling | Safe code/correlation only; cause protected locally |
| M03-SEC-008 | Real DB/events | Production persistence | No raw provider/error/identity payload persisted |
| M03-SEC-009 | Real extension result | Production adapter | Unknown/content-bearing fields rejected and absent |
| M03-SEC-010 | Artifact scan | Logs, DB, diagnostics, reports, backups | No secret/content/raw payload finding |
| M03-OPS-001 | Real startup | Production composition/DB | Invalid manifest degrades correct adapter and readiness visibly |
| M03-OPS-002 | Real restart | Production service | Catalog and current compatibility rebuild correctly |
| M03-OPS-003 | Real diagnostics | M08/P01 authenticated path | Versions/states visible with no sensitive fields |
| M03-OPS-004 | Real upgrade | Prior supported contract/schema artifacts | Compatible adapter/module upgrade succeeds |
| M03-OPS-005 | Real recovery | Verified backup/prior binary | Documented rollback/forward recovery works |
| M03-OPS-006 | Real retention | Production retention operation/DB | History purge is bounded/auditable/current-safe |
| M03-PERF-001 | AgentMonitor-owned load | Production catalog with admitted descriptors | Lookup/validation remains bounded at V1 scale; target approved before implementation |
| M03-PERF-002 | Real service/DB | Production compatibility history/query | Startup/query overhead meets approved budget without provider simulation claim |
| M03-LIVE-001 | T6 | Real A01/A02/A03 current versions | Each adapter registration/manifest is owner-reviewed and conformant |
| M03-LIVE-002 | T5/T6 | Real local provider sources | Safe fields only; prohibited content/environment absent |
| M03-LIVE-003 | T6 | Real usage/cost observation | Scope/unit/time/precision/provenance preserved for reconciliation |
| M03-LIVE-004 | T6 | Real known unsupported capability | Unsupported displayed as decision, not zero/error/unknown |
| M03-LIVE-005 | T6 | Natural source failure if available | No unapproved fallback/cached-as-current value |
| M03-LIVE-006 | T6 | Real auth-health states naturally available | State/outcome mapping agrees with authoritative provider evidence |
| M03-LIVE-007 | T6 | Owner-run managed reauth per provider | Expected identity succeeds or wrong-account stops; no secret capture |
| M03-LIVE-008 | T6 | Real default and managed profiles | Default profile unchanged; only approved managed profile may be written |
| M03-LIVE-009 | T6/integration | Natural real adapter/provider failure | Other adapters and dashboard/API remain available |
| M03-LIVE-010 | T6 | Natural unavailable/exhausted/recovery state | Exact outcome/recovery represented; absent state is Blocked |
| M03-TEST-001 | Review | Repository/test tree | No prohibited doubles/recordings/provider fixtures/test-only paths |
| M03-TEST-002 | Evidence | All executed tests | Red/Green/refactor and Passed/Failed/Blocked/Not Run are truthful |
| M03-DOC-001 | Documentation | Repository docs | Module/contracts/traceability/runbooks complete and linked |
| M03-DOC-002 | Documentation | Capability matrices | Every claim links scoped M0/live evidence; no overgeneralization |
| M03-DEP-001 | Dependency | Locked graph/SBOM/notices | Every direct/transitive dependency admitted and licensed |
| M03-DEP-002 | Dependency | Source/build review | No undeclared provider SDK/plugin/telemetry dependency |

### 9.6 Red/Green evidence record

Every test record names requirement/AC, contract version, test ID, layer, exact real dependency, UTC timestamp, sanitized command reference, expected Red behavior, actual Red result, production change, Green result, refactor result, environment/version, evidence reference, and live status. A test that cannot reach its real boundary is Blocked or Not Run and does not block pure work unless its gate is required for approval/release.

Critical pure protocol/compatibility/source/outcome/auth/extension branches require meaningful branch and mutation coverage. The exact mutation score and tool require foundation/dependency approval; surviving material mutants block completion. Line coverage alone cannot prove adapter conformance.

## 10. Implementation increments

Implementation begins only after section 15 is fully checked and the root issues a path/contract task packet.

| Increment | Scope | Failing tests first | Minimum production change | Exit evidence |
|---|---|---|---|---|
| M03-I00 | Contract synchronization only | No production test | Finalize CTR-PROV/common/consumer schemas, ownership, decisions | Signed CS record; still no code |
| M03-I01 | Core identifiers/capability/decision vocabularies | M03-PURE-001..003 | Pure immutable value objects and validation | Red/Green/refactor plus contract docs |
| M03-I02 | Manifest/source descriptors and validation | M03-PURE-006/007/011/012 | Canonical manifest and source policy | Deterministic validation/fingerprint evidence |
| M03-I03 | Protocol/version/capability negotiation | M03-PURE-004/005/008..010/031..033 | Pure registry/negotiation policies | Compatibility branch/mutation evidence |
| M03-I04 | Outcome/provenance/auth/identity contracts | M03-PURE-014..024/034 | Closed unions and cross-field validators | Contract serialization/semantics evidence |
| M03-I05 | Reauth and extension governance | M03-PURE-025..030, M03-SEC-003 | State policy and schema registry; no provider auth | Security/privacy review |
| M03-I06 | Compatibility persistence | M03-DB-001..012 | Real repository/migration for assessments | Real SQLite migration/query/concurrency evidence |
| M03-I07 | Events/outbox and health | M03-DB-013, M03-INT-002/003, M03-OPS-001..003 | Approved event/health implementation | Real service/DB delivery evidence |
| M03-I08 | Invocation gateway/safe context enforcement | M03-ARCH-001..003, M03-SEC-001/005..009 | Validated resolution/invocation/error containment | Real composition security evidence; no fake adapter |
| M03-I09 | First real production adapter conformance | Relevant M03-CONF/LIVE IDs | Integrate one approved adapter without changing M03 semantics | Real provider evidence; blocked cases explicit |
| M03-I10 | Remaining A01/A02/A03 conformance | M03-CONF-009, remaining LIVE IDs | Register additional real adapters against same protocol | Per-provider live matrices |
| M03-I11 | Upgrade/recovery/performance/hardening | M03-OPS-004..006, M03-PERF-001/002, M03-TEST/DOC/DEP | Minimum fixes/docs only | Full handoff and independent review |

### 10.1 Ordering and parallel safety

- I00 is mandatory and serial. No agent implements from this Draft.
- I01–I05 are owned by one M03 implementation agent unless the root allocates non-overlapping files; all share contract types, so casual parallel edits are prohibited.
- I06 can proceed in parallel with internal pure work only after table/migration ownership and DTOs are frozen; the migration file has one owner.
- A01/A02/A03 may implement in parallel after `ProviderAdapterV1`, their capability payload contracts, source rules, safe execution ports, and conformance matrix are Approved. They edit only their adapter paths.
- M02/M04/M05/M06/M08 may implement consumers in parallel after they countersign the exact contract versions. They must not edit M03 producer files or redefine DTOs.
- I09/I10 integrate one adapter at a time to preserve attributable real evidence and stop safely on contract drift.
- Generated artifacts, composition, migration ordering, dependency manifests, event registry, and configuration registry are shared files allocated only by the root.

### 10.2 Handoff required from each adapter

Each adapter supplies:

- exact implemented manifest and contract/schema versions;
- M0 decision rows and scoped real versions/plan/role/platform;
- commands/endpoints/path/field allowlists by approved operation ID, not raw data;
- Red/Green/refactor records and real conformance/live scenario statuses;
- side-effect/default-profile reconciliation;
- secret/content/artifact scan;
- Blocked/Not Run/naturally unavailable scenarios;
- dependency/license record and version-change triggers;
- sanitized diagnostics and rollback/disable procedure.

M03 rejects a conformance handoff that invents a provider fact, generalizes beyond evidence, hides Blocked cases, includes raw output, or requires M03 provider conditionals.

### 10.3 Implementation-agent return packet

Every separately authorized M03 increment returns exact requirement,
acceptance, scenario, plan, protocol and contract versions; files changed; and
the exact Red/Green/refactor commands and results. It reports every real
provider/database/platform boundary separately as Passed, Failed, Blocked, or
Not Run, and records security, privacy, migration/recovery,
dependency/license, compatibility, and documentation impact. The packet also
lists residual risks and the next integration step. Adapter handoffs in section
10.2 are inputs to this packet, not a substitute for it.

## 11. Documentation outputs

M03 implementation/change reviews update, as applicable:

- `docs/modules/provider-system.md`: purpose, invariants, ports, outcomes, compatibility, persistence, health, limitations;
- generated/maintained contract schema documentation for CTR-PROV-001..008 and CTR-COMMON-004;
- capability/source/outcome/auth-state/version/extension compatibility reference;
- real adapter conformance guide and evidence matrix;
- operations/troubleshooting for registration, version drift, incompatible/disabled/unsupported states, upgrade, recovery, and incident response;
- configuration registry entries if any are approved;
- migration metadata and schema ownership;
- security threat/data-flow updates if safe execution or reauth boundaries change;
- dependency admission, SBOM, and notices;
- central contract register, traceability, risk register, roadmap/planning registry, and release notes through root-owned synchronized edits;
- ADR for any breaking contract, dynamic plugin, private/browser source, new secret store, or default-profile policy change.

Commands remain Planned/TBD until implemented and exercised. Examples contain only structural constructed values clearly labelled as such and never claim live provider data.

## 12. Dependency and license impact

### 12.1 Dependency posture

M03 adds no provider SDK and should need no module-specific runtime dependency for core identifiers, manifests, outcomes, hashing, or pure negotiation beyond the approved Python/runtime foundation. It uses the centrally approved persistence/event stack only in infrastructure adapters.

Potential version-range parsing is unresolved. Provider versions must not be forced into semantic versioning. If M0 proves a semantic-version parser is needed and the approved foundation does not already provide one, its package is Candidate/Pending and must complete the full admission gate before import. Hand-written incomplete semantic-version parsing is also prohibited.

No JSON-schema library, plugin framework, dynamic importer, telemetry client, retry package, provider SDK, HTTP client, subprocess wrapper, or cryptography package is approved by this plan. Existing approved safe boundary packages may be consumed only through their published ports.

### 12.2 Admission record required for any new package

Record exact purpose, upstream identity, current license, all transitive licenses, maintenance/security/provenance, release cadence, supported platforms, native/install scripts, telemetry/network behavior, pin/lock/integrity policy, size/performance, alternatives, removal cost, SBOM/notices change, and reviewer/date. Copyleft, unclear, source-available, telemetry-bearing, or opaque binary packages require explicit owner decision under policy.

## 13. Risks, unresolved decisions, and stop conditions

### 13.1 Linked project risks

| Risk | M03 treatment | Residual/blocking state |
|---|---|---|
| R-001 | Capability manifests accept honest Unsupported/Unknown; no universal quota assumption | M0 must decide every scoped capability |
| R-002 | Parser/provider versions and unverified-version behavior are mandatory | Verified ranges unknown until M0 |
| R-003 | Identity outcomes preserve unresolved/conflict; no guessing | M02/M06 correlation contracts must synchronize |
| R-004 | Protected/unknown profile rejects mutation before adapter invocation | Real default-profile regression evidence required |
| R-005 | Typed allowlists, bounded errors/extensions, raw-output prohibition | Real adapter/log/DB/artifact scan required |
| R-006 | Manifest exposes constraints; M04 owns safe concurrency/retry | Rate/cost facts unknown until M0 |
| R-007 | Provenance/freshness mandatory; unavailable/stale not current | M05 interpretation synchronized separately |
| R-009 | Naturally unavailable live states remain Blocked | Accepted limitation remains visible |
| R-010 | Zero-default side effects and owner-coordinated live calls | Each adapter live packet must set budget |
| R-018 | No dependency before admission | Version parser/safe boundary packages pending |
| R-019 | CI pure/DB/service evidence never substitutes for T5/T6 | Release matrix separates gates |
| R-021 | Reauth mismatch terminal; registry identity/history unchanged | M02-owned CTR-REG-008 coordination/persistence must be approved and verified with the M03 protocol; ownership is not open |
| R-024 | Private/browser source is Experimental only after threat/ADR/approval | No such source enabled by this plan |

### 13.2 Approval-blocking synchronization decisions

1. M0 must deliver a complete scoped capability matrix and accepted M03 handoff; currently Not Run.
2. Root and all consumers must approve exact CTR-PROV-001..008 schemas and CTR-COMMON-004 ownership.
3. M05/M06 must own and publish every typed business payload used as `CollectionOutcomeV1[T]`; a generic provider dictionary is rejected.
4. M02/M03 must define the narrow provider target, installation version, profile protection, expected identity, and Experimental-grant contract without a circular dependency.
5. M04/M03 must define who creates operation context, selects source, supplies deadlines/cancellation, and records the final collection run.
6. Safe filesystem, subprocess, network, cancellation, and provider-profile access port owners/versions must be allocated.
7. Approve the fixed split: M02 owns CTR-REG-008 orchestration, persistence, restart/cancel/idempotency, audit coordination, and P01/P02 handoff; M03 owns only CTR-PROV-007 protocol semantics and sanitized provider outcomes.
8. Provider-version schemes/rules and verified-range expansion workflow must be based on M0 evidence.
9. Capability/schema minor-version negotiation and unknown-capability behavior must be consumer-tested.
10. Extension descriptor storage location, validator ownership, API/UI exposure, and retention must be approved per adapter schema.
11. Compatibility table and 365-day retention proposal must be accepted by persistence/M08/data reviewers.
12. Approve CTR-EVT-TOPOLOGY-001, the `provider_system_event_outbox` schema/port details, retention, and registration-at-startup durability without changing its module-owned topology.
13. Experimental opt-in owner, persistence, audit, scope, and default-off behavior must be fixed.
14. Required versus optional adapter effect on global readiness must be defined by deployment/M08.
15. Exact serialization/size/cardinality/string/time bounds and safe error codes must be approved.
16. Exact mutation score/performance budgets and admitted tools must be approved.
17. The first real adapter used for I09 must have its own approved plan, dependency admission, and live resources.

No open item above may be resolved privately by an implementation agent.

### 13.3 Module-specific risks

| ID | Risk | Likelihood/impact | Mitigation | Trigger | Owner/status |
|---|---|---|---|---|---|
| M03-R01 | Generic outcome becomes an untyped raw-payload tunnel | Medium/Critical | Typed `T`, no dict/blob, extension registry and bounds | Arbitrary map/raw string proposed | M03/security Open |
| M03-R02 | Manifest claims support broader than live evidence | High/Critical | Tuple-scoped decision refs and conformance gate | Missing plan/version/role/platform evidence | Adapter/M03 Open |
| M03-R03 | Protocol abstraction becomes lowest-common-denominator or provider conditionals | Medium/Major | Capability ports/extensions; provider code outside M03 | `if provider ==` in M03/consumer | Architecture Open |
| M03-R04 | Version negotiation silently accepts drift | High/Major | Exact evidenced schemes, unverified fail-safe | Unknown/out-of-range version parsed | M03/adapters Open |
| M03-R05 | Reauth contract creates a credential/profile mutation path | Medium/Critical | Managed-only/protected rejection, owner action, separate flow review | Raw secret/default profile reaches call | Security Open |
| M03-R06 | Adapter failure containment is only tested with a fake | High/Major | Real production-adapter/natural failure evidence; Blocked otherwise | Test double proposed | Test owner Accepted constraint |
| M03-R07 | Static registration blocks future community providers | Low/Moderate | Stable protocol and composition seam; dynamic plugins deferred with ADR | Runtime plugin requested | Architecture Monitoring |
| M03-R08 | Compatibility history duplicates M02 installation truth | Medium/Major | M03 stores assessment only; M02 owns installation; scalar ref/ports | Adapter/install fields diverge | M02/M03 Open |

### 13.4 Stop and escalation conditions

Stop immediately and notify the root when:

- M0 evidence is absent, contradictory, broader/narrower than a proposed capability, or requires a private/browser source;
- a provider-specific conditional, SDK type, command, path, endpoint, field, or auth mechanic is requested inside M03;
- a consumer asks for a generic raw payload/dictionary or direct M03-table access;
- provider/account/profile identity would be guessed or a default/unknown profile could be mutated;
- secret/content/raw provider data appears in a result, log, database, diagnostic, event, evidence artifact, or chat;
- implementation requires an unapproved dependency, dynamic plugin, process control, arbitrary environment access, or source downgrade;
- a protocol/schema/enum/unit/time/identity meaning must change after synchronization;
- a migration may lose data or conflict with another owner;
- a live scenario requires login/MFA/OTP, credits, disruptive state, provider mutation, or naturally unavailable failure without owner coordination;
- another agent edits the same contract, migration, composition, manifest, or shared registry file.

## 14. Delivery, compatibility, and rollback

### 14.1 Delivery order

1. Complete and approve M0 M03 handoff.
2. Resolve section 13.2 through CS and publish Approved contract versions.
3. Implement pure protocol/policy increments with TDD.
4. Implement real persistence/events/health after PLAN-DB/FND synchronization.
5. Integrate one approved real provider adapter and complete its conformance/live gate.
6. Integrate remaining adapters independently without changing protocol meaning.
7. Integrate M02/M04/M05/M06/M08 consumers, P01 diagnostics, and release evidence.

### 14.2 Compatibility window

- M03 host and adapters declare protocol ranges; at least the current Approved protocol is supported through the V1 release.
- Breaking protocol/capability/extension/event changes require a new major, ADR, adapter/consumer migration, deprecation window, and dual-support plan where safe.
- New optional capabilities or schema-minor fields are compatible only when old hosts/consumers preserve Unknown/unsupported behavior.
- Expanding a verified provider-version range changes compatibility evidence and adapter version; it requires real live verification but not necessarily a protocol version change.
- Provider-version drift can disable only the affected capability/source while existing stored observations/history remain readable.

### 14.3 Rollback and recovery

- A newly incompatible adapter is disabled/removed from static composition without deleting M02 identity or M05/M06 history.
- Protocol rollback uses a prior compatible binary and, after a schema change, a verified pre-migration backup unless a real tested downgrade exists.
- Manifest/extension changes are rolled back with their adapter binary; persisted compatibility assessments remain immutable historical facts.
- After restore, start loopback-only, validate schema, rebuild static catalog, compare manifests/versions, expose safe readiness, and only then allow M04 to resume collection.
- M03 never resumes a flow after uncertain process restart on its own. M02's durable CTR-REG-008 workflow decides resume, cancel, expire, or owner-restart from synchronized evidence; M03 executes only the requested protocol operation.

### 14.4 Post-delivery checks

- All approved adapters register with expected protocol/manifest fingerprints.
- Incompatible/disabled/unsupported capabilities appear distinctly through health/API/UI consumers.
- Real provider results preserve scope, source, versions, time, precision, confidence, and freshness.
- No provider-specific code or SDK appears in M03; no consumer imports adapter internals/M03 tables.
- Logs, DB, events, diagnostics, backup, and evidence pass secret/content/raw-payload scans.
- One real adapter failure is contained or remains visibly Blocked in the release matrix.
- Migration/restore/current-assessment queries and event delivery pass.
- Every provider/version tuple has Passed/Failed/Blocked/Not Run live status; none is inferred from CI.

## 15. Definition of ready for implementation

- [ ] This plan and its scope/non-goals are owner and reviewer approved.
- [ ] Current M0 technical evidence and the M03 handoff/capability matrices
      validate; detached review records remain advisory.
- [ ] CTR-COMMON-001/002/004/006 and CTR-PROV-001..008 are synchronized, registered, versioned, and Approved.
- [ ] M02 target/profile/identity/Experimental-grant contract is Approved.
- [ ] M04 operation-context/source/deadline/collection-run allocation is Approved.
- [ ] M05/M06 typed capability payload contracts are Approved.
- [ ] Safe filesystem/subprocess/network/cancellation/profile-access port owners and versions are Approved.
- [ ] The fixed ownership split is Approved: M02 owns CTR-REG-008 coordination/persistence/audit/restart/idempotency and P01/P02 handoff; M03 owns only CTR-PROV-007 protocol semantics and typed provider outcomes.
- [ ] M03 persistence/outbox tables, migration allocation, retention, backup, and recovery are Approved.
- [ ] Security/privacy threat and extension-schema governance reviews pass.
- [ ] Exact dependency versions/locks and direct/transitive license/security admission pass.
- [ ] Test IDs, expected behavioral Red, commands/evidence custody, and mutation/performance targets are approved.
- [ ] The first real production adapter plan and required owner-controlled live resources are available.
- [ ] Shared-file/path ownership is allocated and no parallel agent conflicts.
- [ ] No unresolved decision permits materially different implementations.

## 16. Approval record

| Role | Decision | Conditions | Date |
|---|---|---|---|
| Owner | Pending | M0 and contract synchronization required |  |
| Root/integration steward | Pending |  |  |
| Architecture/contracts reviewer | Pending |  |  |
| M02 Registry owner | Pending |  |  |
| M04 Collection owner | Pending |  |  |
| M05 Capacity owner | Pending |  |  |
| M06 Runtime owner | Pending |  |  |
| M08 Operations owner | Pending |  |  |
| A01/A02/A03 adapter owners | Pending | M0-specific scopes required |  |
| Security/privacy reviewer | Pending |  |  |
| Test-integrity reviewer | Pending |  |  |
| Persistence/migration reviewer | Pending |  |  |
| Dependency/license reviewer | Pending |  |  |

Implementation remains prohibited while Status is Draft or any Definition-of-Ready item is unchecked.
