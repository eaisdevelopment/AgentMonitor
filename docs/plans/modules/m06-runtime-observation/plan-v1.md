# Module plan: M06 — Runtime observation

- Status: **Draft; planning only; not approved for implementation**
- Plan version: 0.2.0-draft
- Module contract version: `runtime-observation.v1` proposed; CTR-RUN-001..007 remain unsynchronized
- Owner: M06 runtime-observation module owner
- Reviewers: integration/contract, M02, M03, M04, M07, A01–A04, P01, P02, DB, security/privacy, test-integrity, and operations owners
- Requirements: FR-DISC-001..008; FR-STATE-001..004; runtime-owned FR-HIST-001..005; FR-SAFE-002; NFR-ARCH-001/002; NFR-DATA-001; NFR-TEST-001/002; NFR-SEC-001; NFR-PRIV-001/002; NFR-DOC-001; NFR-LIC-001; NFR-PLAT-001; NFR-PERF-001; NFR-RES-001; NFR-OBS-001; NFR-COMP-001
- Acceptance criteria: AC-V1-001/002/005/007/008; AC-LIVE-004; AC-UI-002/005/006; AC-PROC-001..005; AC-HIST-001/002; AC-OPS-003; AC-TEST-001..006
- Published contracts: CTR-RUN-001..007, proposed V1 schemas defined in this plan
- Consumed contracts: CTR-COMMON-001/002/004/006/007; CTR-EVT-001; CTR-FND-004/006/008; CTR-IAM-001/002; CTR-REG-001/002/004/006/007; CTR-PROV-002/003/004/008; CTR-COL-002/003/006; CTR-DB-002; CTR-OPS-006/007; CTR-PLAT-001
- Target milestone: M3 after Milestone 0 and contract synchronization
- Approved by/date: pending

This plan is governed by the [product requirements](../../../product/requirements.md), [V1 acceptance criteria](../../../product/v1-acceptance-criteria.md), [module boundaries](../../../architecture/modules.md), [contracts and versioning](../../../architecture/contracts-and-versioning.md), [data model](../../../architecture/data-model.md), [provider-adapter contract](../../../architecture/provider-adapter-contract.md), [security architecture](../../../architecture/security.md), [API standards](../../../api/api-standards.md), [testing strategy](../../../engineering/testing-strategy.md), [SDLC](../../../engineering/sdlc.md), [completion and automation gates](../../../engineering/completion-and-automation-gates.md), [M0 execution plan](../../discovery/m0-execution-plan.md), and [contract register](../../contract-register.md). Structural schemas and examples are planning constructs, not provider observations, sample telemetry, fixtures, or live evidence.

## CS-1 Draft-alignment addendum

This `0.2.0-draft` revision adopts contract-baseline `0.2.0` and the parallel-ownership manifest as its concrete CS-1 review position. It remains Draft and evidence-blocked; Linux/provider/macOS observations and all scenarios remain `Not Run` or, where the real platform is absent, visibly Blocked.

- M06 is the sole semantic producer of CTR-RUN-001..007, including CTR-RUN-006 `ProcessInspectionPortV1`. A04-LINUX and A04-MAC implement CTR-RUN-006; they do not co-own or redefine its PID/start identity, safe field, hierarchy, error, deadline, cancellation, or no-control semantics. OS extensions require M06 contract review and versioning.
- The runtime public contract path is exactly `backend/src/agentmonitor/contracts/runtime_observation_v1.py`, matching the V1 file convention. SQLite implementations are only under `backend/src/agentmonitor/adapters/persistence/runtime_observation/sqlite/**`. M06 owns `runtime_` tables and `v1_0600..v1_0699`; PLAN-DB serializes the migration head.
- M06 implements the runtime side of M04-owned CTR-COL-006 with atomic snapshot/session/history/correlation changes, producer outbox, and a durable receipt keyed by run ID, target generation, schema version, and canonical digest. It returns opaque references only; same input is idempotent and conflicting input cannot overwrite the first commit.
- Provider/session optional fields use CTR-COMMON-007 and carry CTR-COMMON-004 provenance/evidence blocks. Runtime events use CTR-COMMON-006 plus CTR-EVT-001 durable outbox, aggregate generation/order, receipt/checkpoint, deduplication, replay, and explicit recovery. Possible-stall recovery requires newer progress/current-state evidence; silence, unknown, waiting, and a later generic collection success are not recovery.
- M06 implements M08-owned CTR-OPS-006 and CTR-OPS-007 leaf participant ports, exposing safe bounded health/retention/export/consistency behavior without table access by M08. M02 account identity decisions remain immutable inputs; M06 alone owns session-to-account correlation decisions.
- Alignment is verified by existing scenarios M06-PURE-001..027, M06-DB-001..015, M06-LNX-001..010, M06-MAC-001..004, M06-OPS-001..008, M06-ARCH-001..003, and M06-LIVE-001..008. None is promoted to Passed by plan alignment.

## Planning gate and evidence dependency

This plan is intentionally detailed enough for an isolated implementation assignment, but it does not assert that any Claude, Codex, Ollama, Linux, or macOS field/source is available. The Milestone 0 process/session handoff required by `docs/plans/discovery/m0-execution-plan.md` has not been executed. All provider- and platform-dependent input fields in this plan are therefore conditional schema slots, not supported capability claims.

Implementation is blocked until all of the following are true:

1. M0-LNX-001..013 and applicable M0-CLA/CDX/OLL local-session scenarios have terminal, reviewed results.
2. The Linux handoff identifies approved sources, units, permissions, PID/start-time semantics, race behavior, safe field allowlists, and prohibited sources.
3. Each provider handoff identifies whether session ID, model, project/task label, token/context counts, activity, errors, wait state, hierarchy, and account evidence are Supported, Experimental, Deferred, or Unsupported for the exact observed versions.
4. A04-LINUX, A01–A03, M02, M03, M04, M07, DB, P01, and P02 review their consumed portions of CTR-RUN-001..007.
5. The root steward allocates the runtime ingest/commit contract, migration revisions, generated contract paths, and configuration names.
6. The canonical planning gate passes for the synchronized planning set. This artifact alone cannot make that gate green.

Unknown evidence does not permit a permissive implementation. It removes the affected field or capability from the supported manifest and leaves it explicitly `unknown`, `unsupported`, `unavailable`, or `unverified` as warranted.

## 1. Outcome and boundaries

### 1.1 Outcome

M06 will turn approved, read-only process and provider-session observations into a truthful current runtime view and 365-day operational history. The owner will be able to see real agent processes and sessions, their safe operational metadata, evidence-based account association, parent/subagent structure, state, activity, and possible-stall inference without changing the existing launch workflow or controlling an agent.

Measurable outcomes are:

- a process is never treated as the same process solely because its PID matches;
- a session is never associated with an account from a label, timing, current-login assumption, or other weak evidence;
- parent/child and aggregate information exposes evidence, gaps, conflicts, and double-counting limitations;
- definitive and inferred states remain distinguishable in storage, contracts, events, API, and UI;
- the default possible-stall threshold is exactly 600 seconds and observable waiting-for-input or waiting-for-permission excludes the session;
- every persisted field is on an approved operational-metadata allowlist and carries source/time/version/availability semantics where applicable;
- runtime history expires after 365 days through an auditable real-database operation without deleting active/current state accidentally;
- no M06 path can signal, attach to, inject into, pause, kill, restart, route, or switch credentials for a running process.

### 1.2 In scope

- Validate and ingest M06-owned typed process, session, metric, hierarchy, activity, state-evidence, and correlation-evidence payloads.
- Maintain immutable observations separately from current projections.
- Model process identity using PID plus an approved start identity and executable identity.
- Model provider session identity only where M0 establishes a safe, scoped identifier and lifetime.
- Preserve safe operational model, project/repository label, task label, token/context counts, last activity, and safe error codes only when the exact source/field/version has been approved.
- Represent OS process ancestry separately from provider session parent/subagent relationships.
- Build bounded session trees with explicit orphan, conflict, inferred, and cycle-rejected states.
- Produce parent-level state counts, attention summary, and only provably non-overlapping usage aggregates.
- Own runtime-state classification and possible-stall inference.
- Own global/organization/provider/account stall-duration policy and precedence because that policy changes runtime inference, not M07 alert severity/lifecycle.
- Own runtime session/account correlation decisions and their evidence/history; consume but do not rewrite M02 identity facts.
- Publish current, history, tree, correlation, state-change, and possible-stall contracts.
- Implement the M06 result-commit side of the synchronized M04 collection commit seam.
- Own runtime tables, repository ports, migrations, retention deletion, and runtime outbox records.
- Publish safe component health to M08.

### 1.3 Out of scope

- Process discovery mechanics, `/proc`, `sysctl`, platform APIs, filesystem traversal, service management, or native path resolution; A04 owns these.
- Claude, Codex, or Ollama parsing, CLI invocation, local-file allowlists, version detection, and provider-specific correlation extraction; A01–A03 own these.
- Scheduling, polling, provider invocation, retries, backoff, leases, and collector run lifecycle; M04 owns these.
- Provider capability negotiation and generic outcomes; M03 owns these.
- Organization/account/profile lifecycle or provider identity truth; M02 owns these.
- Quota, budget, billing, capacity, or capacity-based availability; M05 owns these.
- Alert rule/severity/lifecycle, notification state, acknowledgement, or snooze; M07 owns these.
- REST routes, HTTP status mapping, authorization transport, pagination transport, or OpenAPI generation; P01 owns these.
- UI composition or client state; P02 owns these.
- Backup scheduling, export orchestration, restore, and global retention scheduling; M08 owns these.
- Reading prompts, responses, tool calls/arguments, source-code content, terminal contents/output, process memory, arbitrary process environment values, cookies, credentials, or raw provider payloads.
- Agent control, credential switching, account routing, or session recovery. Those are post-V1 work requiring new architecture and threat review.

### 1.4 Ownership

M06 exclusively owns:

- `AgentProcess`, `AgentSession`, `ProcessSnapshot`, `SessionObservation`, `RuntimeMetricObservation`, `SessionProcessLink`, `SessionRelationship`, `RuntimeStateTransition`, `RuntimeCorrelationEvidence`, `SessionCorrelationDecision`, `RuntimeStallPolicy`, and runtime current projections;
- runtime ingest receipts and runtime event-outbox facts;
- the normalized runtime-state vocabulary and certainty/evidence rules;
- process/session merge and deduplication rules after adapter validation;
- hierarchy validation and aggregation eligibility;
- runtime history query/retention behavior;
- CTR-RUN-001..007 schema sources and compatibility notes;
- M06 module documentation, test matrices, sanitized live-evidence references, and operational notes.

M06 stores M02/M03/M04/A04 identifiers only as scalar contract references. It neither declares foreign keys to another module's tables nor queries those tables.

### 1.5 Proposed paths for a future implementation agent

Allowed production paths, subject to PLAN-FND synchronization:

```text
backend/src/agentmonitor/contracts/runtime_observation_v1.py
backend/src/agentmonitor/modules/runtime_observation/
  domain/
  application/
  ports/
backend/src/agentmonitor/adapters/persistence/runtime_observation/sqlite/
backend/migrations/versions/<centrally-allocated-m06-revisions>.py
backend/tests/runtime_observation/pure/
backend/tests/runtime_observation/persistence/
backend/tests/runtime_observation/contract/
backend/tests/runtime_observation/integration/
backend/tests/runtime_observation/live/
docs/modules/runtime-observation.md
docs/contracts/runtime-observation-v1.md
docs/operations/runtime-observation.md
```

P01/P02/A01–A04/DB owners write their own route, UI, provider/platform, and shared persistence artifacts. The M06 agent may propose a contract change but may not edit another owner's path or a centrally shared generated artifact without reassignment.

Forbidden paths/imports include:

- `agentmonitor.modules.registry.*`, `provider_system.*`, `collection_control.*`, `capacity.*`, `alerting.*`, or `operations.*` internals;
- provider adapter implementations or provider SDK/CLI packages;
- platform adapter implementations, `psutil`, `/proc` readers, `subprocess`, terminal APIs, debuggers, or process-control libraries;
- FastAPI, SQLAlchemy, Alembic, Pydantic transport models, OS APIs, and React inside `domain/`;
- other modules' ORM models, repositories, migrations, or tables;
- generic `dict[str, Any]` telemetry payloads or arbitrary extension bags;
- test-double, fixture-response, replay, demo-data, or seeded-telemetry frameworks.

Allowed imports are Python standard-library pure primitives, foundation common contract primitives, M06-owned domain/application ports, and explicitly synchronized cross-module contract packages. Persistence adapters may use the admitted SQLAlchemy/Alembic versions after foundation/DB approval.

### 1.6 Parallel-development isolation

After CS synchronization, M06 domain/state/hierarchy/correlation work can proceed independently from A01–A04 implementations because adapters target versioned M06 input contracts. Persistence can proceed against M06 repository ports after migration revision allocation. P01/P02 can proceed against frozen query/command views. M07 can proceed against frozen state/stall events. Work stops if any party needs a semantic or required-field change rather than an additive optional field.

## 2. Requirements and traceability

The table uses exact IDs. A supporting row does not transfer ownership from the named owner module.

| Requirement/AC | Planned M06 behavior | Contract | Planned scenarios | Evidence gate |
|---|---|---|---|---|
| FR-DISC-001 | Accept real discovered Claude/Codex/Ollama processes without launch-flow change | CTR-RUN-001/006 | M06-LNX-001, M06-LIVE-001..003 | M0 + real Linux/provider processes |
| FR-DISC-002 | Preserve allowlisted executable/provider, PID/parent, safe directory label, start/duration, CPU/memory, process state | CTR-RUN-001/006 | M06-PURE-001..003, M06-LNX-002..006 | M0 units/permission/source evidence |
| FR-DISC-003 | Accept only approved local-session metadata fields; reject raw/unknown/content-bearing fields | CTR-RUN-002 | M06-PURE-026/027, M06-SEC-001..004, M06-LIVE-004 | Provider M0 field allowlists |
| FR-DISC-004 | Correlate only from approved evidence; otherwise Unresolved | CTR-RUN-007 | M06-PURE-018..021, M06-DB-009, M06-UI-002, M06-LIVE-005 | M0 identity/correlation handoff |
| FR-DISC-005 | Expose evidence-qualified hierarchy and safe aggregates | CTR-RUN-003 | M06-PURE-004/005/014..017, M06-LNX-007, M06-LIVE-006 | real representative trees |
| FR-DISC-006 | Expose model/project/task/session/token/context/activity/error only when safe and source-supported | CTR-RUN-002 | M06-PURE-016/024..027, M06-LIVE-004/007 | per-provider capability decision |
| FR-DISC-007 | No arbitrary process-environment input, read, persistence, or contract field | CTR-RUN-006 | M06-SEC-001/002, M06-LNX-008 | static boundary + real inspection proof |
| FR-DISC-008 | Require parser/adapter/provider version and schema identity on local inputs | CTR-RUN-002; CTR-COMMON-004 | M06-PURE-024, M06-DB-003, M06-LIVE-004 | M03/A01–A03 versioned input |
| FR-STATE-001 | Represent all approved normalized runtime states, including unknown and terminal states | CTR-RUN-002/004 | M06-PURE-006/007, M06-LIVE-008 | state-evidence matrix |
| FR-STATE-002 | Keep definitive, inferred, and unknown certainty separate | CTR-RUN-004 | M06-PURE-006..008, M06-API-003 | contract/pure/live evidence |
| FR-STATE-003 | Apply effective 600-second default and scoped override precedence | CTR-RUN-005 | M06-PURE-009..013, M06-DB-010, M06-API-004 | real observations plus policy DB |
| FR-STATE-004 | Current observable user/permission waits prevent possible-stall classification | CTR-RUN-005 | M06-PURE-010/011, M06-LIVE-008 | real waiting state when naturally available |
| FR-HIST-001 | Retain runtime/process/session history for 365 days | CTR-RUN-001/002 | M06-PURE-023, M06-DB-012, M06-OPS-003 | real SQLite deletion evidence |
| FR-HIST-002 | Provide bounded current/history/tree timelines with provenance | CTR-RUN-001..003 | M06-DB-011, M06-API-002, M06-UI-003 | real DB/API/browser |
| FR-HIST-003 | Purge only expired eligible runtime history in auditable batches | M06 retention port | M06-DB-012, M06-OPS-003 | real SQLite transaction |
| FR-HIST-004 | Expose runtime history through query ports for M08 export | CTR-RUN-001/002 | M06-OPS-004 | M08 export integration; no table access |
| FR-HIST-005 | Store UTC and let P02 render configured timezone | CTR-COMMON-002; CTR-RUN views | M06-PURE-025, M06-API-002, M06-UI-003 | contract/API/browser |
| FR-SAFE-002 | Publish no control, signal, input, credential-switch, or routing operation | all CTR-RUN contracts | M06-SEC-005/006, M06-LNX-009 | API/import/schema/static review |
| NFR-ARCH-001 | One-way ports/contracts with no module cycles | module boundary | M06-ARCH-001/002 | import-boundary automation |
| NFR-ARCH-002 | Typed contracts and exclusive table/invariant ownership | CTR-RUN-001..007 | M06-ARCH-002/003 | contract and migration ownership checks |
| NFR-DATA-001 | Real SQLite adapter behind portable repositories | CTR-DB-002 | M06-DB-001..015 | real file SQLite/Alembic |
| NFR-TEST-001 | Red-Green-Refactor per increment | test-evidence contract | all scenarios | retained command/evidence packet |
| NFR-TEST-002 | No doubles, recordings, seeded telemetry, or placeholder runtime data | test policy | M06-SEC-007, M06-OPS-006 | source/test scan and review |
| NFR-SEC-001 | Least privilege, bounded input, sanitized errors, no control | CTR-RUN-006/007 | M06-SEC-001..008 | security and live review |
| NFR-PRIV-001 | Persist operational allowlist only | CTR-RUN-001/002 | M06-SEC-001..004, M06-LIVE-004 | schema/data/log/export inspection |
| NFR-PRIV-002 | No outbound product telemetry | module operations | M06-SEC-008 | dependency/network review |
| NFR-DOC-001 | Module/contracts/tests/runbook/evidence documented | documentation outputs | M06-OPS-007 | docs gate |
| NFR-LIC-001 | No dependency before full admission | dependency section | M06-OPS-008 | lock/SBOM/license gate |
| NFR-PLAT-001 | Linux verified; macOS contract preserved and verified only on real macOS | CTR-RUN-006/CTR-PLAT-001 | M06-LNX-001..010, M06-MAC-001..004 | real platforms; macOS may be Blocked |
| NFR-PERF-001 | Query/ingest design supports 200 current processes without redesign | CTR-RUN queries | M06-PERF-001/002 | measured real-process/DB workload |
| NFR-RES-001 | Adapter/input failure affects only its batch/subject and not unrelated queries | ingest contracts | M06-DB-006/007, M06-OPS-001/002 | real failure isolation |
| NFR-OBS-001 | Structured safe events/correlation IDs and component health | CTR-FND-004; CTR-OPS-006 | M06-OPS-001/002, M06-SEC-003 | protected-log/diagnostic inspection |
| NFR-COMP-001 | Version contracts/events/schema and reject incompatible majors | CTR-RUN-001..007 | M06-PURE-024, M06-ARCH-003 | compatibility gate |
| AC-PROC-001 | Discover real running provider processes read-only on Linux | CTR-RUN-001/006 | M06-LNX-001/009 | owner-observed workstation |
| AC-PROC-002 | Correct representative parent/subagent trees | CTR-RUN-003 | M06-LNX-007, M06-LIVE-006 | owner comparison |
| AC-PROC-003 | No silent account guess; manual confirmation available | CTR-RUN-007 | M06-LIVE-005, M06-API-005, M06-UI-002 | owner confirmation flow |
| AC-PROC-004 | Prove prohibited content/environment/secrets are not persisted | all runtime storage | M06-SEC-001..004, M06-LNX-008 | schema/log/DB/export inspection |
| AC-PROC-005 | Real ten-minute stall behavior and wait exclusions | CTR-RUN-005 | M06-LIVE-008, M06-PURE-009..012 | real observation window/owner check |
| AC-UI-002 | Supply real session/process data to UI through API only | CTR-RUN-001..003 | M06-API-001/002, M06-UI-001 | real service/built browser |
| AC-UI-005 | Expose empty/partial/stale/unsupported/unauthorized/failed truthfully | views/errors | M06-API-003, M06-UI-004 | real API/browser states |
| AC-UI-006 | Expose source/time/confidence/explanation for runtime derivations | CTR-RUN-001..005 | M06-UI-003, M06-LIVE-007 | generated client/browser |
| AC-HIST-001 | Real collection-to-runtime-history-to-chart path | CTR-RUN-002 | M06-LIVE-007, M06-UI-003 | live provider + real DB/API/UI |
| AC-HIST-002 | 365-day calculation and real deletion transaction | retention port | M06-PURE-023, M06-DB-012 | pure cutoff + real DB |
| AC-OPS-003 | A failed provider/runtime batch leaves other data and API available | ingest isolation | M06-DB-007, M06-OPS-002 | real service and real failure when available |
| AC-TEST-001 | Every implemented behavior retains expected Red/Green/refactor evidence | evidence plan | all implementation increments | evidence review |
| AC-TEST-002 | Repository scan rejects prohibited test-double/fixture frameworks | quality gate | M06-SEC-007 | automated scan + review |
| AC-TEST-003 | Required real DB/HTTP/browser suites pass | T2/T3/T4 | M06-DB-*, M06-API-*, M06-UI-* | exact real boundaries |
| AC-TEST-004 | Live reports identify safe aliases/versions/times and owner acknowledgement | T5/T6 | M06-LNX-*, M06-LIVE-* | live runbook |
| AC-TEST-005 | Critical state/stall/correlation/retention mutations meet synchronized target | T1/T2 | M06-PURE-*, M06-DB-* | admitted mutation tool |
| AC-TEST-006 | Blocked/Not Run platform/provider rows remain visible | evidence status | M06-MAC-*, M06-LIVE-* | fail-closed report |

### 2.1 Interpretation requiring synchronization

- “Parent-level aggregated usage” means state counts and only usage values proven to be non-overlapping and unit-compatible. It never sums a parent's inclusive provider total with child totals.
- “Project/repository” is an approved safe display label or opaque project reference, not source content. Raw repository content is never read.
- “Errors” means allowlisted stable error/state codes and occurrence/timestamp metadata, never arbitrary exception, stderr, transcript, or terminal text.
- “Definitive” means the synchronized source contract proves the state directly for its stated scope/version. High CPU or silence alone is not definitive working/stuck evidence.
- The 600-second default is a runtime inference threshold. M07 separately decides whether a resulting event opens an alert and with what severity.
- A session may be visible with no account. `account_id = null` plus correlation state `unresolved` is a valid result, not an error.

## 3. Domain design

### 3.1 Core identities and value objects

| Type | Required semantics |
|---|---|
| `ProcessIdentityV1` | platform source/boot scope, positive PID, approved non-null start identity, safe executable identity/fingerprint; all components are required before cross-poll merge |
| `ProcessObservationId` | opaque immutable observation identity; not derived by clients |
| `SessionIdentityV1` | provider key, installation ID, provider-session identity kind/value fingerprint, scope and version; only admitted when M0 proves safe lifetime/collision semantics |
| `RuntimeField[T]` | `known(value)` or exactly one of `withheld`, `unknown`, `unsupported`, `unavailable`, `unverified`; non-known states carry no value and only a safe reason code |
| `RuntimeStateEvidenceV1` | evidence code, source reference, observed time, expiry/freshness, certainty, adapter/parser/provider versions; no raw evidence value |
| `RuntimeMetricV1` | metric kind, exact integer/decimal value, unit, scope, interval/cumulative semantics, observed time, provenance, overlap/aggregation classification |
| `CorrelationEvidenceRefV1` | opaque evidence reference, class, source/schema/version, validity interval, safe reason; no email/path/raw identity |
| `HierarchyEvidenceV1` | relationship kind, source/evidence class, confidence, observed/valid times, safe conflict reason |
| `RuntimeRevision` | monotonically increasing M06 revision for query invalidation; not a global causal sequence |

No caller infers provider, account, or session from an opaque internal ID. PID is never a database primary key. A path label, display name, process order, recent login, parent PID alone, or observation timing is never an account identity.

### 3.2 Process identity and snapshots

One `AgentProcess` represents one validated `(platform scope, PID, process start identity, executable identity)` tuple. The A04 contract determines the exact start-identity representation and precision after platform evidence. M06 rules are:

1. Same PID with different start identity or executable identity is a different process instance.
2. Missing/unreadable/conflicting start identity prevents cross-observation merge; the observation remains an explicitly unresolved one-shot process fact.
3. Parent PID without the parent's start identity creates only an unresolved ancestry candidate, not a durable parent edge.
4. Process exit between enumeration and detail inspection returns a typed race outcome; it is not converted into a current running snapshot.
5. A late snapshot may enter history but cannot regress the current projection.
6. Duration is derived from approved start time and explicit `as_of`; negative/ambiguous values are unknown, never clamped silently.

Allowlisted process snapshot categories are PID, parent PID, start identity/time and precision, safe executable/provider identity, safe working-directory/project label when approved, observed OS state, CPU measurement with stated semantics, memory bytes with stated semantics, and observation/provenance/version metadata. Command line, terminal, memory, open-file content, network payload, and environment are absent from the contract.

### 3.3 Session observations and safe metadata

A provider session is created across collection runs only when an approved `SessionIdentityV1` is present. If a source lacks a stable safe session identity, M06 may show process-only observations or a collection-scoped unresolved session candidate; it must not merge candidates across time heuristically.

Each optional metadata field is independently stateful:

- model identifier/label;
- safe project/repository label or opaque project reference;
- safe task label, only if M0 proves it is an operational label rather than prompt/response content;
- provider session ID display form only when separately approved; internal fingerprint can remain non-displayable;
- input/output/cached/total token counts and context-used/context-limit only with exact provider scope/unit semantics;
- last activity/progress time and activity class;
- safe error category/code and occurrence time;
- provider-reported/raw-safe state code under a versioned allowlist.

An unknown or unapproved field is not parsed “best effort.” Free-form task/error/provider text, arbitrary JSON, and unregistered provider-extension members are rejected before persistence. A provider extension is accepted only when CTR-PROV-008 marks every member safe and M06 explicitly opts into that schema major.

### 3.4 Process/session linking

Process/session is many-to-many over time because wrappers, subprocesses, and provider session lifecycles may not align one-to-one. A link includes validity interval, source/evidence, confidence, and conflict state.

- An exact M0-approved join key may create an automatic link.
- A PID-only, working-directory-only, timing-only, or executable-only match remains unresolved evidence.
- Conflicting links invalidate the current link and preserve history.
- A session can continue after one observed process exits only if provider evidence supports the session independently.
- A process can exist without a provider session and remains visible as process-only.

### 3.5 Hierarchy, orphans, cycles, and wrappers

M06 keeps two graph meanings separate:

- OS process ancestry from validated process identities;
- provider session parent/subagent relationship from approved provider evidence or explicit owner confirmation.

OS ancestry alone is not relabeled as provider subagent hierarchy unless M0 approves that rule for the exact provider/version. Every active session has at most one active parent. A proposed self-edge or edge that creates a cycle is rejected from the active tree, recorded as a safe hierarchy conflict, and leaves the child as a flagged root/orphan. Missing, expired, filtered, or inaccessible parents yield an `orphan_reason`, not an invented parent.

Tree queries are bounded by requested root/scope, maximum synchronized depth, page/node limit, and snapshot `as_of`. If the bound is reached, the response is `partial` with a continuation or safe truncation reason. It never silently drops descendants.

### 3.6 Parent-level aggregation

`SessionTreeViewV1` provides:

- direct and descendant counts by normalized state and certainty;
- active, terminal, unresolved-account, and hierarchy-conflict counts;
- an `attention_summary` derived from a synchronized ranking without changing any node's own state;
- newest/oldest observation and freshness range;
- CPU/memory aggregates only for snapshots with compatible units/semantics and an approved co-observation tolerance;
- token/context aggregates only where all included metrics declare compatible scope and `disjoint` aggregation eligibility;
- `partial`, `unknown`, `not_aggregatable`, and excluded-input reasons.

An inclusive parent token total plus child totals is never summed. Unknown overlap makes the aggregate unknown/partial even if every numeric value is present. Context-window occupancy is not summed across sessions. CPU percentages with different sample windows are not added. These rules are domain-tested independently of provider availability.

### 3.7 Account correlation state machine

Proposed states are:

```text
unresolved
  -> automatic_matched       (approved Strong rule only, or CS-approved Corroborated rule)
  -> confirmation_required   (safe candidate exists but proof is insufficient)
  -> unsupported             (scoped capability decision proves no safe mechanism)

confirmation_required -> owner_confirmed
automatic_matched/owner_confirmed -> conflict | invalidated | unresolved
conflict -> owner_confirmed | unresolved
```

Rules:

- Weak evidence can be displayed as safe reason codes but never selects an account.
- Conflicting evidence never resolves by score or “most recent login.”
- One session has at most one current account decision; past decisions are immutable history.
- Owner confirmation records authenticated principal ID, UTC time, session/account IDs, safe evidence-set hash, evidence generation, and decision version; no raw identity values.
- New contradictory provider/registry evidence invalidates the current decision and emits a safe state change. Historical observations keep their then-current decision reference.
- Moving/renaming an M02 account does not change M06 session identity or history.
- Archived, identity-conflicted, or invalidated accounts cannot receive new automatic mappings. Existing history remains readable.
- M02's `IdentityCorrelationDecisionV1` is provider/account identity evidence. M06's `SessionCorrelationDecisionV1` is a runtime-session relationship. Neither module writes the other's record.

### 3.8 Runtime state model

Normalized states are:

- `working`;
- `waiting_for_input`;
- `waiting_for_permission`;
- `idle`;
- `quota_or_rate_limited` with a safe reason subtype when known;
- `reauthentication_required`;
- `provider_or_network_error` with a safe reason subtype when known;
- `possibly_stuck`;
- `exited_successfully`;
- `crashed`;
- `unknown`.

Each classification carries `certainty = definitive | inferred | unknown`, evidence codes/references, policy/classifier version, `observed_at`, `evaluated_at`, freshness deadline, and safe explanation code. Provider raw state is never stored outside an approved versioned safe code.

The synchronized evidence-precedence policy must follow these invariants:

1. A current definitive terminal/wait/auth/quota/error state is not overridden by a weaker CPU/activity heuristic.
2. Definitive evidence of waiting for input or permission excludes possible stall while that evidence remains current.
3. `working` is definitive only where the source defines it; observed progress/activity may support an inferred working state.
4. Silence alone is never an error and is insufficient for possible stall without evidence that the session/process remains apparently active.
5. Stale state evidence cannot be reported current; it degrades to unknown or another classification supported by current evidence.
6. A state change is emitted only when normalized state, certainty, or material explanation changes for the current observation generation.
7. Late observations enter history but do not emit a current-state regression.

Exact source-to-state mappings remain an M0/A01–A04 synchronization table. M06 never hardcodes a provider-specific raw code in domain policy.

### 3.9 Possible-stall policy

The V1 default effective threshold is 600 seconds. Override specificity is:

```text
account > provider > organization > global default
```

An unresolved session cannot use account/organization policy and falls back to provider then global. Equal-specificity conflicts are configuration errors, not last-write-wins. Policies are versioned, use whole seconds, have optimistic concurrency, and record author/time without free-form notes.

A session becomes `possibly_stuck` only when all conditions are true at explicit `as_of`:

1. it has a current non-terminal process/session presence signal;
2. it has an approved progress/activity watermark;
3. elapsed time since that watermark is greater than or equal to the effective threshold;
4. current evidence does not show waiting for input or permission;
5. current evidence does not already prove quota/auth/provider/network error or a terminal state;
6. required inputs are fresh enough for the classifier version;
7. the condition was evaluated using one coherent policy and evidence generation.

Missing inputs result in unknown/not-evaluable, not possible stall. New progress, a definitive excluded state, session end, or a policy/evidence reevaluation transitions away from `possibly_stuck`. M07 treats `PossibleStallDetectedV1` as an opening signal and the corresponding `RuntimeStateChangedV1` transition away as recovery evidence; no separate M06 “alert recovered” event is published because alert lifecycle belongs to M07.

### 3.10 History, time, and retention

- `observed_at` is when the external fact applied according to its source.
- `collected_at` is when the adapter collected it.
- `stored_at` is database commit time.
- `evaluated_at` is when M06 derived a state/projection.
- Durations use monotonic measurement during a running operation where available and integer milliseconds at contracts; wall-clock UTC remains the persisted event time.
- All persisted instants are timezone-aware UTC. P02 alone renders configured local time.
- Immutable observations and state transitions are retained for 365 days.
- Active session/process identities and current projections are retained while active even if their first observation is older than 365 days.
- Ended aggregate shells may be deleted only after all retained observations/links/decisions no longer require them.
- Correlation confirmation/security-relevant history is retained at least 365 days; exact alignment with audit policy is a CS decision.
- Retention calculates a pure cutoff and deletes through bounded real-database transactions. It records counts, cutoff, run ID, duration, and safe failures.

### 3.11 Idempotency, ordering, and concurrency

- Ingest deduplicates by M04 run ID, typed payload digest, consumer contract version, and source observation IDs where present.
- Same run/digest returns the original commit receipt. Same run/different digest is `runtime_commit_conflict`, blocks M04 success, and emits an incident-safe health signal.
- One transaction writes observations, current projections, transitions, outbox events, and commit receipt.
- Current projection ordering is `(observed_at, source_sequence if supported, collection_run_id, observation_id)` under synchronized source rules. A provider sequence is never invented.
- At-least-once events deduplicate by event ID. Ordering is guaranteed only by monotonically increasing `runtime_stream_sequence` within one session stream.
- Concurrent owner-confirmation commands use expected decision/session version plus an idempotency key; exactly one conflicting update commits.
- Current process/session revisions use optimistic concurrency. SQLite busy/unavailable maps to a typed failure; retries are owned by M04/operation orchestration, not hidden in the repository.

### 3.12 Degradation and recovery

- Invalid or privacy-unsafe input rejects the affected batch before persistence and does not erase prior current data.
- A partial provider/platform result stores only independently valid, allowlisted facts and retains explicit missing states if the synchronized input contract permits partial commit.
- One provider/session batch failure does not roll back unrelated committed batches or make read queries unavailable.
- Last known data may remain visible as stale, never current.
- Missing registry data leaves account correlation unresolved/stale but does not delete runtime observations.
- Outbox failure rolls back the state change and receipt atomically.
- Restart reconciles M04 commit status through the synchronized commit-status port and reuses the stored receipt without duplicate observations/events.
- Restore can move history backward. Before readiness, M06 validates schema, receipts, current projections, graph acyclicity, and outbox consistency. It performs no provider call and no automatic remapping during restore.

## 4. Public contracts

All contracts below are M06-owned proposals. They become `Proposed` in the central register only after root review and cannot become `Synchronized` until M0 and every named consumer review are complete.

### 4.1 CTR-RUN-001 — `AgentProcessViewV1`

Published schema family:

- `ProcessIdentityV1`;
- `ProcessFieldV1[T]` using the shared field-state rules;
- `ProcessSnapshotInputV1` for the approved A04-to-M06 boundary;
- `AgentProcessViewV1`;
- `ProcessHistoryEntryV1`;
- `GetAgentProcessV1`, `ListAgentProcessesV1`, and `ListProcessHistoryV1` queries.

`AgentProcessViewV1` includes internal process ID, provider/installation references when known, PID, parent PID field, parent process ID field, start time/identity and precision, safe executable identity/label, safe working-directory/project label field, OS process state field, CPU measurement and semantics field, memory bytes/semantics field, linked session IDs, first/last observed times, exit/presence state, freshness, provenance, current runtime revision, and explicit partial/unknown reasons.

It never includes command line, environment, terminal, memory, raw path unless separately approved for authenticated owner display, raw executable arguments, provider output, or arbitrary labels. Queries are read-only, authorized, bounded, cursor-paginated, and do not trigger inspection.

Compatibility: PID/start/executable identity meaning, measurement units, field-state meanings, and privacy class cannot change within V1. Additive optional fields require safe absence semantics. Weakening path/content restrictions is breaking and requires security review/ADR.

### 4.2 CTR-RUN-002 — `AgentSessionViewV1`

Published schema family:

- `LocalSessionObservationInputV1`;
- `RuntimeMetricObservationInputV1`;
- `AgentSessionViewV1`;
- `RuntimeHistoryEntryV1` and bounded history query/page;
- `GetAgentSessionV1`, `ListAgentSessionsV1`, and `ListRuntimeHistoryV1`.

`AgentSessionViewV1` includes session ID, provider/installation, safe provider-session display field, linked process IDs, parent relationship summary, correlation state and nullable account ID/decision ID, model/project/task fields, typed metric fields, start/end/last-activity times, normalized state/certainty/explanation, safe error field, freshness/provenance/version, current revision, and explicit missing/unsupported/unavailable/unverified states.

Input objects are closed typed schemas with `extra = forbid` or equivalent. They contain no generic metadata map. Safe provider extensions use CTR-PROV-008 and require an M06 opt-in registry entry.

Compatibility: a formerly optional field cannot become required; token/context unit or inclusion semantics cannot change within the major; task/error fields cannot broaden from code/approved label to arbitrary text.

### 4.3 CTR-RUN-003 — `SessionTreeViewV1`

Published types/queries:

- `SessionRelationshipV1` with child/parent IDs, relationship kind, evidence/certainty, validity, and conflict/orphan state;
- `SessionTreeNodeV1` with one `AgentSessionViewV1`, direct children, node depth, and safe local aggregate;
- `SessionAggregateV1` with state/certainty counts, attention summary, activity/freshness range, eligible metric aggregates, excluded input counts/reasons, and completeness;
- `GetSessionTreeV1(root_or_scope, as_of, depth_limit, node_limit)`;
- `ListSessionRootsV1(scope, as_of, cursor, page_size)`.

Preconditions: authorized telemetry read; scope is global, organization, provider, account, or session and is validated through M02 contracts. Errors distinguish not found, forbidden, invalid scope/cursor, tree conflict, snapshot unavailable, and repository unavailable.

Hierarchy edges are side-effect free on query. Cycles never appear in a successful tree. Orphans and rejected conflicts remain visible. Tree aggregation never guesses overlap or substitutes zero for unknown.

### 4.4 CTR-RUN-004 — `RuntimeStateChangedV1`

Published state contract family:

- `NormalizedRuntimeStateV1` and `RuntimeStateCertaintyV1`;
- `RuntimeStateEvidenceSummaryV1`;
- `RuntimeStateChangedV1` event;
- proposed `RuntimeActivityClassChangedV1` event for M04 cadence input;
- `GetRuntimeStateHistoryV1` query.

`RuntimeStateChangedV1` uses `EventEnvelopeV1`. Envelope `subject_id` is the M06 session ID. Payload contains prior/current normalized state, prior/current certainty, classifier/policy versions, safe explanation/evidence codes and references, effective observed/evaluated times, freshness deadline, session stream sequence, provider key, installation ID when known, nullable account ID plus correlation-decision ID when currently valid, and current runtime revision. Organization is not copied into the event; consumers resolve current membership through M02.

Delivery is at least once. Consumers deduplicate event ID. Ordering is guaranteed only within the session stream. Reprocessing the same input generation emits no duplicate transition. A late observation cannot emit a transition that regresses the current generation.

`RuntimeActivityClassChangedV1` is proposed because M04 needs activity class/expiry without importing M06 internals. It contains session/approved target references, previous/current `active | idle | waiting | terminal | unknown`, observed/expires times, evidence code, stream sequence, event/correlation IDs, and no metrics/content. M04 may translate it to `NotifyActivityV1`; it is not a command to collect. Root must either allocate this as part of CTR-RUN-004 or replace it with an equivalent synchronized port before approval.

### 4.5 CTR-RUN-005 — `PossibleStallDetectedV1`

Published contract family:

- `RuntimeStallPolicyViewV1`;
- `SetRuntimeStallPolicyV1`, `DeleteRuntimeStallPolicyOverrideV1`, and `GetEffectiveRuntimeStallPolicyV1`;
- `PossibleStallDetectedV1` event.

Policy view fields are policy ID/version, scope kind and scalar scope ID, threshold seconds, enabled state, created/updated times, safe actor ID, and compatibility version. It contains no label or free-form note. Global effective default is 600 seconds. Precedence is account > provider > organization > global. Mutation requires synchronized M01 permission, CSRF/idempotency at P01, optimistic version, and a bounded approved duration range. The exact permission name and allowed override range are approval blockers.

`PossibleStallDetectedV1` uses the session as envelope subject and includes condition fingerprint, detected/effective-since/evaluated times, elapsed seconds, effective threshold/policy ID/version/scope kind, state certainty (`inferred`), safe evidence references, waiting-exclusion evaluation result, provider/installation and nullable valid account/correlation IDs, runtime revision, and session stream sequence. It contains no task/path/error text.

Stall recovery is represented by `RuntimeStateChangedV1` whose prior state is `possibly_stuck` and current state differs, with the reason/evidence generation. M07 owns alert recovery and must not require a separate M06 alert-lifecycle event. REST current state remains authoritative if an event consumer recovers after interruption.

### 4.6 CTR-RUN-006 — `ProcessInspectionPortV1`

M06 defines the semantic process-input port; A04-LINUX and A04-MAC implement it. Proposed operations/types are:

- `InspectProcessesV1(PlatformInspectionRequestV1) -> PlatformInspectionOutcomeV1`;
- `ProcessInspectionBatchV1` of bounded `ProcessSnapshotInputV1` entries;
- `PlatformProcessErrorV1` safe outcome union.

Request fields are operation/correlation IDs, platform source, approved executable/provider selectors, approved root/access-grant references, observation deadline, maximum candidate/result counts, and requested allowlisted field set. It never contains a shell string, process-control intent, credential, environment-field request, arbitrary path, or “all metadata” switch.

Allowed outcome states distinguish success, partial, unsupported, permission denied, process exited during inspection, identity conflict/PID reuse, source unavailable, unverified platform version, deadline exceeded, invalid platform data, and internal adapter error. Partial output identifies safe missing field codes per process.

Side effects are read-only process metadata observation. The port has no signal, attach, pause, kill, restart, stdin, terminal, memory, environment, or credential operation. A04 records source/platform/adapter version, observed time, units/precision, and permission outcome. M04 may schedule/invoke the port after synchronization; M06 validates/commits its typed result.

Compatibility: adding a readable field requires M0 evidence, privacy classification, source/version scope, and consumer review. Adding any control or environment-read operation is breaking, conflicts with V1, and requires a future ADR/threat model rather than a V1 minor change.

### 4.7 CTR-RUN-007 — `SessionCorrelationDecisionV1`

Published types/ports:

- `SessionCorrelationDecisionV1` view;
- `CorrelationEvidenceSummaryV1`;
- `EvaluateSessionCorrelationV1` internal command;
- `ConfirmSessionAccountCorrelationV1` owner command;
- `InvalidateSessionAccountCorrelationV1` internal/owner-reviewed command;
- `Get/ListSessionCorrelationDecisionsV1`;
- `SessionCorrelationChangedV1` event proposed within the CTR-RUN-007 family.

The view contains decision ID/version/state, session ID, nullable account ID, applicable M02 identity-decision references, evidence classes and opaque safe references, automatic/owner-confirmed flag, safe actor ID/time for confirmation, validity interval, safe conflict/invalidation reason, provider/source/schema versions, and runtime revision. It never includes email, raw provider identity, path, credential/profile locator, or raw evidence values.

Owner confirmation requires an authenticated principal, synchronized write permission, session/decision expected versions, selected M02 account ID, current safe evidence-set hash/generation, and an idempotency key. Same key/fingerprint returns the decision; a different fingerprint conflicts. Automatic match is allowed only by an approved versioned rule. New conflict creates an immutable decision transition and clears the current account projection without deleting history.

`SessionCorrelationChangedV1` is at-least-once, session-stream ordered, and contains safe IDs/states/reasons only. M02 may consume it as a reference but does not absorb runtime ownership. M07/P01/UI use current correlation state; no alert is implied automatically.

### 4.8 Runtime ingest and M04 commit synchronization

M03 expects M06-owned typed payloads for local session discovery, metrics, and process correlation. M04 owns Draft-aligned CTR-COL-006 `CollectionOutcomeCommitPortV1`. M06 implements its runtime payload side:

- `RuntimeObservationBatchV1`, a closed discriminated union of process snapshots, session observations, metrics, relationship evidence, state evidence, and correlation evidence;
- M06 implementation of M04-owned `CollectionOutcomeCommitPortV1[RuntimeObservationBatchV1]`;
- `GetRuntimeCommitStatusV1(run_id)` returning `not_committed | committed(receipt) | conflict | unavailable`.

M06 receives the validated CTR-PROV-004 outer outcome and M06 payload through composition. It does not import M04/M03 internals. M04 receives only observation IDs, stored-at range, payload digest, consumer/contract version, target generation, and event IDs in the durable commit receipt. CTR-COL-006 ownership is fixed at M04; implementation cannot invent a direct call or store a generic JSON payload.

### 4.9 Consumed contracts and degradation

| Contract | Owner/status required | M06 use | Failure/degradation |
|---|---|---|---|
| CTR-COMMON-001/002 | `proposed_aligned` 1.0.0 | IDs, UTC, duration | malformed/non-UTC input rejected |
| CTR-COMMON-004 | `evidence_blocked` 1.0.0 | source/version/precision/confidence/freshness | success without mandatory provenance rejected |
| CTR-COMMON-006 | `proposed_aligned` 1.0.0 | immutable event envelopes | state transaction cannot commit without event record |
| CTR-COMMON-007 | Draft-aligned V1 | optional/availability field states | exact zero/unknown/unavailable/unsupported/withheld/stale/not-applicable remain distinct |
| CTR-EVT-001 | Draft-aligned V1 | durable outbox, receipts/checkpoints, replay and retention | explicit incompatible/poison/backlog state; no in-memory-only delivery |
| CTR-FND-004/006/008 | `proposed_aligned` 1.0.0 | safe correlation/log, migration metadata, evidence reporting | fail closed on incompatible contract |
| CTR-IAM-001/002 | `proposed_aligned` 1.0.0 | query and correlation/policy authorization | deny when unknown/unavailable; no implicit admin bypass |
| CTR-REG-001/002 | mixed: CTR-REG-001 `proposed_aligned`; CTR-REG-002 `evidence_blocked` (1.0.0) | organization/account scope and policy precedence | unresolved scope uses only safely known broader policy |
| CTR-REG-004 | `evidence_blocked` 1.0.0 | installation/provider association | unknown installation leaves provider field unresolved |
| CTR-REG-006 | `evidence_blocked` 1.0.0 | provider/account identity evidence and candidate validation | conflict/unknown never auto-maps |
| CTR-REG-007 | `proposed_aligned` 1.0.0 | invalidate/re-evaluate scope/account decisions | deduplicate event; stale registry revision visible |
| CTR-PROV-002/003 | `evidence_blocked` 1.0.0 | capability/source/version/side-effect validation | unsupported/unverified/unsafe source blocks ingest |
| CTR-PROV-004 | `evidence_blocked` 1.0.0 | typed outcome envelope | invalid union is safe failed batch, never partial success by guess |
| CTR-PROV-008 | `evidence_blocked` 1.0.0 | explicit safe provider extension | unknown schema/member rejected |
| CTR-COL-002/003 | `proposed_aligned` 1.0.0 | run/reference/history context | missing committed run prevents successful receipt |
| CTR-COL-006 | M04-owned Draft-aligned V1 | idempotent outcome commit/status | conflict/unavailable returned; no M04 payload storage |
| CTR-DB-002 | `proposed_aligned` 1.0.0 | repositories/UoW | typed conflict/unavailable/corrupt; no direct SQL outside adapter |
| CTR-PLAT-001 | `evidence_blocked` 1.0.0 | safe platform source/access primitives | platform unavailable stays explicit |
| CTR-OPS-006 | `proposed_aligned` 1.0.0 | publish bounded component health | M08 unavailability does not affect ingest/query |
| CTR-OPS-007 | M08-owned Draft-aligned V1 | runtime retention/export/post-restore consistency participant | typed bounded failure; no M08 table access |

No fallback reads another module's table, raw provider file, `/proc`, environment, or cached value as current.

### 4.10 Safe error vocabulary

Proposed stable errors include:

- `runtime_process_identity_incomplete`, `runtime_process_identity_conflict`, `runtime_process_exited_during_observation`;
- `runtime_session_identity_incomplete`, `runtime_session_identity_conflict`, `runtime_hierarchy_cycle`, `runtime_hierarchy_conflict`;
- `runtime_input_schema_incompatible`, `runtime_input_field_prohibited`, `runtime_extension_unapproved`, `runtime_provenance_invalid`;
- `runtime_correlation_unresolved`, `runtime_correlation_confirmation_required`, `runtime_correlation_conflict`, `runtime_correlation_evidence_stale`;
- `runtime_policy_invalid`, `runtime_policy_conflict`, `runtime_policy_stale_version`;
- `runtime_commit_conflict`, `runtime_observation_duplicate`, `runtime_repository_unavailable`, `runtime_schema_incompatible`;
- `runtime_query_invalid`, `runtime_cursor_invalid`, `runtime_subject_not_found`, `runtime_dependency_unavailable`.

Errors contain a code, correlation ID, authorized safe subject ID, and safe remediation category. They contain no path, label, task, model, identity, command, SQL, provider payload, traceback, or exception text. P01 owns RFC 9457 mapping.

### 4.11 Contract-impact assessment

This plan defines the first detailed CTR-RUN-001..007 proposals and does not change implemented behavior. Before approval the root must:

1. freeze M06-owned provider/platform input payloads and the M04-owned CTR-COL-006 commit/status contract;
2. reconcile M02 identity evidence versus M06 runtime correlation ownership and authorization;
3. freeze M03 capability result types and provider-extension opt-in rules;
4. freeze A04 process identity/start marker, measurement units, permission, and race outcomes;
5. approve M04 activity signal semantics and whether `RuntimeActivityClassChangedV1` belongs under CTR-RUN-004;
6. approve M07 subject scope, transition/stall recovery, event ordering, deduplication, and unknown/confidence handling;
7. freeze P01 query/action routes, permissions, pagination, ETags/idempotency, and safe path-label disclosure;
8. freeze P02 tree/partial/unknown/provenance requirements;
9. allocate DB migration revisions/outbox infrastructure and M08 retention/export/health ports;
10. update the central contract register and add an ADR if any synchronized result weakens the read-only/privacy boundary or changes event durability.

## 5. Data and persistence

M06 owns all `runtime_*` tables and migrations below. Names are proposed and require DB revision allocation. There are no cross-module database foreign keys.

### 5.1 Proposed tables

#### `runtime_session`

- `session_id` primary key;
- provider/installation scalar references;
- approved provider-session identity fingerprint, identity kind/scope/schema version, and display field-state;
- first/last observed, ended time/state, current observation/state/correlation/parent references;
- current revision and row version;
- uniqueness only for the M0-approved provider/session identity scope.

No prompt/title/free-form transcript field exists. If a provider session ID is not approved for storage, only a keyed/non-reversible or opaque adapter-issued reference approved by security may be stored; exact method requires synchronization and must not become a home-grown credential hash.

#### `runtime_process_instance`

- `process_id` primary key;
- platform source/boot-scope reference, PID, start identity/time/precision, safe executable identity/fingerprint;
- provider/installation scalar refs when known;
- first/last observed, ended/presence state, current snapshot reference, row version;
- unique approved process identity tuple;
- unresolved one-shot identities are explicitly marked and not merged.

#### `runtime_process_snapshot`

- immutable snapshot ID and process ID;
- M04 run/source observation IDs and observation generation;
- observed/collected/stored UTC times;
- parent PID and validated parent process ID field-state;
- safe working-directory/project label field-state;
- OS state, CPU/memory typed values and semantics;
- provenance/version/freshness/confidence fields;
- uniqueness/deduplication key for source observation identity.

#### `runtime_session_observation`

- immutable observation ID/session ID/run/source IDs;
- start/end/activity times and field-states;
- model/project/task/error/provider-state allowlisted fields;
- normalized state/certainty/evidence-set reference and policy/classifier version;
- provenance/version/freshness and observation generation;
- no provider raw payload or unbounded text.

#### `runtime_metric_observation`

- immutable metric ID/session/process optional refs;
- kind, exact value representation, unit, scope, interval/cumulative semantics;
- overlap/aggregation classification;
- observed/collected/stored times and provenance;
- constraints prevent negative counts where semantics prohibit them and require known unit/scope.

#### `runtime_session_process_link`

- link ID, session/process IDs, relationship kind, evidence ref/class/certainty;
- validity start/end and current flag;
- source/schema/version, conflict state, created time;
- one current exact link per synchronized identity rule, while allowing documented multiplicity.

#### `runtime_session_relationship`

- relationship ID, child/parent session IDs, kind, evidence/certainty;
- validity interval/current flag, conflict/orphan reason, source/version;
- child != parent;
- one active parent per child;
- cycle prevention in domain transaction plus post-write invariant verification.

SQLite cannot enforce arbitrary graph acyclicity with a simple constraint; the repository performs a bounded recursive check in the same transaction and the real DB tests verify concurrent conflict handling. PostgreSQL portability is reviewed before relying on SQLite-specific recursive behavior.

#### `runtime_correlation_evidence`

- evidence ID/session ID, evidence class/code/source/schema/version;
- opaque safe reference/hash, observed/expiry times, validity/conflict state;
- optional M02 decision/account candidate scalar refs;
- no raw evidence, email, display identity, path, profile locator, or arbitrary text.

#### `runtime_session_correlation_decision`

- decision ID/session ID, state, nullable account ID, M02 decision ref;
- automatic/owner-confirmed flag, safe actor ID/time;
- evidence-set hash/generation, validity interval/current flag, reason code;
- decision/row/runtime revision;
- partial unique constraint for one current decision per session.

#### `runtime_stall_policy`

- policy ID, scope kind and scalar scope ID, threshold seconds, enabled/current state;
- version, safe actor ID, created/updated times;
- unique current policy per scope;
- no free-form description or copied organization/account label.

The 600-second global default is a versioned domain default. Whether a row is created at bootstrap or only on first override is a DB/config synchronization decision; no telemetry is seeded.

#### `runtime_state_transition`

- transition/event ID, session ID, session stream sequence;
- prior/current state and certainty, safe explanation/evidence refs;
- observed/evaluated times, classifier/policy version, runtime revision;
- immutable and unique per session/sequence and effective generation.

#### `runtime_ingest_receipt`

- M04 run ID, payload digest, consumer/contract version;
- stored observation IDs or bounded join rows, stored-at range, event IDs;
- status, created time;
- same run/digest is replay-safe; different digest is conflict.

#### `runtime_event_outbox`

- standard event envelope, session stream/sequence, allowlisted canonical payload;
- CTR-EVT-TOPOLOGY-001 makes `runtime_event_outbox` an M06-owned transactional producer table; availability and producer-side delivery metadata use its published event-storage port;
- no labels, raw evidence, paths, or provider extensions unless explicitly approved in that event schema.

PLAN-DB supplies reusable claim/delivery persistence mechanics without owning a central event table. Consumers own their receipt/checkpoint rows and commit them with their domain effect; neither the dispatcher nor M06 uses cross-module SQL.

### 5.2 Indexes and query shapes

Proposed indexes are justified by contract queries and must be verified with real SQLite query plans:

- process: `(presence_state, last_observed_at, process_id)`, `(provider_key, last_observed_at)`, and unique process identity tuple;
- process history: `(process_id, observed_at desc, snapshot_id desc)`;
- session: `(current_state, last_observed_at, session_id)`, `(provider_key, last_observed_at)`, nullable account correlation projection, and identity uniqueness;
- session history/metrics: `(session_id, observed_at desc, id desc)` plus bounded metric kind/time;
- hierarchy: current child and current parent indexes;
- correlation: current session decision and bounded account/time history;
- policies: unique scope kind/scope ID and version;
- state transitions: `(session_id, stream_sequence)` and `(occurred_at, event_id)`;
- receipts/outbox: unique run ID and delivery-state/availability indexes;
- retention scans: stored/ended time plus active/current protection fields.

No unbounded “all history” query is exposed. Actual index choice is measured; unused speculative indexes are removed only through a migration.

### 5.3 Transaction boundaries

- One batch commit validates the complete typed input before opening a write transaction.
- The transaction writes deduplicated immutable observations, relationship/correlation changes, current projection, state transition, outbox records, and receipt atomically.
- Registry queries and external adapter calls occur outside the M06 write transaction; their revision/evidence generation is carried into validation to detect staleness.
- Policy mutation writes policy plus reevaluation requests/events atomically; reevaluation of many sessions is bounded background work, not one long transaction.
- Manual correlation confirmation writes decision history/current projection/event/idempotency receipt atomically.
- Retention deletes bounded eligible batches and emits an auditable result; it never mixes provider collection or export in the same transaction.

### 5.4 Migration sequence

Proposed expand-only order, subject to central revision allocation:

1. identity/current shell tables and immutable process/session observation tables;
2. metrics, links, relationships, and correlation evidence/decisions;
3. stall policies, state transitions, ingest receipts, and runtime outbox;
4. indexes and measured query-plan adjustments.

Every revision records M06 ownership, requirement IDs, expected volume, lock/downtime expectation, backup prerequisite, upgrade validation, and recovery. Fresh database and every supported prior schema are tested using the real Alembic chain. No installed startup `create_all` is permitted. A destructive contract migration requires a new plan/ADR/backup-restore evidence; downgrade exists only if real and safe.

### 5.5 Retention, deletion, backup, restore, and export

- Retention eligibility is derived from explicit UTC cutoff and active/reference invariants.
- The M06 purge port takes cutoff, bounded batch size, operation/correlation IDs, and returns counts by record class plus completion cursor/status.
- M08 owns scheduling and operator-facing retention/export; it calls M06 ports and never reads M06 tables.
- Export queries return versioned safe views, not ORM rows. M08 owns file creation/redaction/download lifecycle.
- SQLite backup/restore is DB/M08-owned. M06 supplies schema compatibility and post-restore invariant checks.
- A restored older current projection is truthful for the restored point in time and stale until new real observations arrive. M06 does not fabricate catch-up data.

### 5.6 PostgreSQL portability

Repository contracts do not expose SQLite row IDs, PRAGMAs, lock codes, partial-index syntax, or recursive-query syntax. Exact quantities, UTC instants, enum strings, uniqueness, graph validation, outbox ordering, and optimistic versions receive an explicit portability review. Any SQLite-specific optimization stays in the persistence adapter and has an alternative/limitation note.

### 5.7 Prohibited fields proof

The schema inventory contains no column for prompt, response, transcript/title derived from content, tool input/output, source content, terminal output, command line, process environment, process memory, OAuth/API credential, cookie, OTP/MFA, raw provider payload, raw exception, arbitrary JSON, or free-form diagnostic text. Migration review and real DB schema inspection enforce this negative contract.

## 6. External and platform boundaries

### 6.1 Linux platform boundary

A04-LINUX is the only component that reads Linux process/filesystem primitives. M06 sees only CTR-RUN-006 typed observations. Before support, M0/A04 must establish:

- exact process start identity, boot scope, precision, and PID reuse/race treatment;
- safe executable/provider identification;
- parent ancestry/wrapper/reparent behavior;
- CPU/memory/state units and sampling semantics;
- working-directory access, symlink/privacy behavior, and safe label derivation;
- permission-denied/partial/source-unavailable outcomes;
- proof that environment, memory, terminal, content, signal, attach, and provider-file mutation paths are absent.

No production M06 behavior imports Linux APIs. Real T5 evidence is required on the target workstation.

### 6.2 macOS boundary

The same CTR-RUN-006 semantics must be implementable by A04-MAC without Linux fields leaking into domain types. Exact start identity, process state, resource units, working-directory permissions, hierarchy, and launchd behavior require a real macOS plan/environment. Until then M06-MAC scenarios are Blocked, not simulated or passed by Linux equivalence.

### 6.3 Provider adapter boundary

A01–A03 implement M03 local-session/metrics/correlation capabilities and return M06-owned closed payloads only for M0-approved sources and versions. Adapters perform file/path/CLI/API parsing and content discard before constructing an input. M06 revalidates schema/provenance/field allowlist but never receives a raw body/file/output for secondary parsing.

Unsupported fields remain unsupported at the field/capability level. A provider adapter failure cannot clear current M06 facts; collection freshness eventually makes them stale.

### 6.4 Registry boundary

M06 queries M02 views/snapshots for valid account/provider/organization scope, identity decision references, and lifecycle. It does not cache friendly names as identity. RegistryChangedV1 may request reevaluation of policies/correlations. A registry outage makes account/scope data stale/unresolved while process/session facts remain queryable.

### 6.5 Collection boundary

M04 owns when and whether inspection/session collection runs. M06 owns semantic validation/persistence. A run is not `succeeded` until M06 returns an idempotent receipt. M06 never retries the provider/platform call. Invalid input returns a stable safe failure for M04 scheduling/backoff classification. Collection cancellation cannot signal a monitored agent; it applies only to collector work owned by M04/adapters.

### 6.6 API coordination

P01 is expected to map frozen M06 ports to authenticated, bounded resources such as:

- `/api/v1/processes` and item/history reads;
- `/api/v1/sessions`, item/history/tree/root reads;
- runtime correlation review/confirmation/invalidation actions;
- runtime stall-policy reads/mutations;
- runtime provenance/explanation detail through safe typed resources.

Exact paths remain P01-owned. Read operations require `read:telemetry`. Correlation and policy write permissions require M01/P01/root decision. Browser mutations require CSRF plus idempotency/expected version. GET never triggers process/provider inspection. P01 cannot serialize internal evidence values, raw path, profile locator, or ORM rows.

### 6.7 UI coordination

P02 consumes only generated API types. Required runtime UI states are real empty, loading, partial, stale, unsupported, unavailable, unverified, unresolved account, correlation conflict, orphan, hierarchy conflict, permission denied, and failed. The tree shows node state and aggregate attention separately, exposes excluded aggregate reasons, and labels inferred state/confidence. Manual confirmation displays only safe evidence summaries and requires an explicit owner action.

No design sample or seeded telemetry may enter the running UI/browser test. Browser acceptance uses real collected/persisted state or truthful empty/error state.

## 7. Security and privacy

### 7.1 Trust boundaries and controls

| Boundary/threat | Required control |
|---|---|
| PID reuse/race misattributes process | PID + approved start identity + executable identity; unknown on conflict |
| Provider/local field contains content or secret | adapter discard, closed typed schema, `extra=forbid`, M06 opt-in extension allowlist |
| Process environment/memory/terminal exposure | no request/response field or dependency path; static/import/API/schema review; real inspection proof |
| Weak evidence maps wrong account | evidence class policy; weak/conflicting stays unresolved; owner confirmation |
| Working directory reveals sensitive path | approved safe label, authenticated disclosure, no logs/events; exact raw-path policy requires M0/security approval |
| Error/task label contains content | stable codes/bounded approved operational label only; raw/free-form text rejected |
| Malformed huge batch exhausts service | M03/M04/A04 bounds plus M06 item/field/size/depth limits and deadline-aware validation |
| Cycle/deep tree exhausts query | transactional cycle rejection, depth/node/page bounds, deterministic truncation |
| Event/log leaks metadata | allowlisted IDs/codes only, structured safe logging, no object serialization |
| Correlation command races/new evidence | expected version/evidence generation/idempotency; conflict fails closed |
| Hidden process control is added | forbidden dependency/API scan, contract review, no control verbs/ports |
| Restore reactivates stale mapping | readiness invariant check; stale/unresolved until new evidence; no automatic provider action |

### 7.2 Authorization

- Process/session/tree/history/provenance queries require M01 authorization and owner-level telemetry read.
- Manual correlation confirmation/invalidation and stall-policy mutation require explicit write permissions; the existing candidate scopes are `write:accounts` and `write:configuration`, but a dedicated runtime scope may be clearer. Root/M01/P01 must decide before approval.
- Internal ingest accepts only a composition-bound M04 authority, not an API principal or provider-controlled identity.
- Retention/export/health ports accept only synchronized M08/internal authorities.
- Single-user deployment never bypasses authorization checks.

### 7.3 Data minimization and privacy proof

For every proposed field, approval requires a field register containing purpose, exact source, provider/platform/version scope, type/unit, privacy class, storage/display/log/event/export permissions, retention, aggregation behavior, and M0 evidence reference. A field without a complete register entry is not admitted.

Safe labels are not automatically non-sensitive. Project/task/path labels are visible only to the authenticated owner, excluded from logs/events/diagnostics by default, and exportable only through M08's explicit safe schema. Email and full provider display identity remain M02 concerns and are not copied into M06.

### 7.4 Logging, diagnostics, and incidents

Allowed structured log fields are event name, component, correlation/run/observation/session/process internal IDs, provider key, safe outcome/error code, counts, bounded durations, and contract/schema versions. Disallowed fields include PID where not needed, account label, path, task/model label, evidence value, raw exception argument, input object dump, provider extension, or raw SQL.

Unexpected prohibited data stops the affected path, quarantines evidence outside Git, triggers the secret/content incident runbook where applicable, and invalidates any “Passed” privacy evidence. No redaction-after-persistence strategy makes raw capture acceptable.

### 7.5 No-control proof

The implementation gate must verify:

- no M06 production import of subprocess/process-control/terminal/debugger/platform modules;
- no public/internal M06 operation named or typed for signal, kill, pause, resume, restart, stdin, attach, route, or credential switch;
- no API route generated from M06 permits those actions;
- no adapter request uses a monitored PID as a cancellation/process-group target;
- live inspection leaves real agent process identity/start/state and provider files unchanged within the approved verification method.

## 8. Configuration and operations

### 8.1 Configuration ownership

M06 proposes no secret or provider-specific environment variable. It never reads `.env` or provider credentials directly.

The 600-second stall default is a versioned domain policy. User overrides are persisted through authorized M06 application commands with account/provider/organization/global scope. Candidate configuration registry entry:

| Setting | Owner/source | Type/default | Validation | Reload/visibility |
|---|---|---|---|---|
| `runtime.possible_stall_threshold_seconds` | M06 persisted scoped policy | integer seconds; effective global default 600 | positive bounded range pending safety/UX review; scope unique; precedence fixed | new evaluations use new version; safe value/source visible to authorized user |

History retention is 365 days by approved requirement and is not lowered through an environment key in V1. M08 may schedule purge frequency/batch size, but it passes an explicit cutoff/bound through the M06 port. Poll intervals belong to M04. API page limits belong to P01. Path/provider settings belong to M02/A01–A04.

No exact external key is allocated until CTR-CONFIG-001 synchronization. Renaming or changing threshold meaning is a configuration-contract change.

### 8.2 Health and readiness

M06 implements CTR-OPS-006 with safe fields:

- module/schema/contract/classifier versions;
- repository/outbox compatibility state;
- last successful ingest/commit time and safe outcome;
- current/active/stale/unresolved/conflict counts;
- oldest unprocessed outbox/retention work age;
- last retention result/count/time;
- invariant-check result and safe error code;
- provider/platform input capability counts by supported/unavailable/unverified category, not identities.

M06 is not ready for writes when schema/contract/invariant checks fail. A provider/platform capability failure degrades that subject/capability but does not make the whole API unready. M08 timeout cannot cause M06 ingest/query failure.

### 8.3 Operator procedures

`docs/operations/runtime-observation.md` must eventually contain verified procedures for:

- investigate missing/stale process/session data;
- inspect unresolved/conflicting account correlation and perform owner confirmation;
- investigate possible stall without controlling the process;
- diagnose provider/platform schema/version incompatibility;
- run/verify runtime retention through M08;
- validate M06 after backup restore/upgrade;
- respond to prohibited content/secret capture or wrong-account mapping.

Command names remain TBD until repository-owned automation exists and is real-tested.

### 8.4 Canonical automation obligations

M06 does not create a private ad hoc script. The implementation must register selectors with the repository canonical routines from the completion standard:

- `AUTO-TEST`: T1/T2/T3/T4/T5/T6/T7 M06 matrices with Passed/Failed/Blocked/Not Run split;
- `AUTO-QUALITY`: formatting/type/import-boundary/security/secret/prohibited-double/contract/schema checks;
- `AUTO-DOCS-CHECK`: requirement/contract/scenario links and field register;
- `AUTO-MIGRATE`: allocated M06 revisions, fresh/supported-upgrade/integrity evidence;
- `AUTO-BACKUP`/`AUTO-RESTORE`: M06 schema/invariant verification through DB/M08;
- `AUTO-BUILD`: generated contract/OpenAPI/client compatibility once P01/P02 integrate.

The M06 module cannot be called implementation-ready until the exact fail-closed commands/selectors are implemented and tested against their real boundaries. A local shell recipe or prose list is not the gate. Missing macOS/provider resources remain Blocked and visible even if deterministic suites are green.

### 8.5 Local operational measurements

AgentMonitor may store bounded operational counts/durations for M06's own ingest/query/retention health. It sends no analytics or crash reports. Performance measurements exclude content/identity/path values and are local only.

## 9. Test design before implementation

### 9.1 Evidence state at planning time

Every scenario below is **Not Run**. No test, production code, migration, provider/platform observation, or live account action is authorized by this plan. Red means a future behavioral test executed against the correct boundary and failed for the expected missing/incorrect behavior; missing dependency, syntax failure, absent credentials, or absent provider state is not Red.

### 9.2 Pure domain tests (T1)

Pure tests construct only side-effect-free domain values, pass `as_of` explicitly, and perform no filesystem/network/database/clock/environment I/O.

| Test ID | Requirement | Initial behavioral Red | Pass condition |
|---|---|---|---|
| M06-PURE-001 | FR-DISC-002 | PID alone merges two process observations | different start identity/executable yields distinct process identity |
| M06-PURE-002 | FR-DISC-002 | missing start identity is treated as stable | identity is unresolved and cannot merge across observations |
| M06-PURE-003 | FR-DISC-002 | negative/ambiguous duration is clamped | result is explicit unknown with reason |
| M06-PURE-004 | FR-DISC-005 | self/cyclic session edge enters tree | edge rejected and safe hierarchy conflict returned |
| M06-PURE-005 | FR-DISC-005 | missing parent is silently dropped | child is visible as orphan with reason/evidence |
| M06-PURE-006 | FR-STATE-001/002 | weaker activity overrides definitive wait/error/terminal state | synchronized evidence precedence selects definitive current state |
| M06-PURE-007 | FR-STATE-001/002 | inferred/definitive classifications collapse | certainty remains distinct in equality/view/transition |
| M06-PURE-008 | FR-STATE-002 | stale evidence remains current | classification degrades according to policy with explicit reason |
| M06-PURE-009 | FR-STATE-003 | elapsed 599 seconds triggers default stall | no stall before 600 seconds |
| M06-PURE-010 | FR-STATE-003/004 | elapsed 600 seconds always stalls | only complete eligible evidence produces inferred possibly_stuck |
| M06-PURE-011 | FR-STATE-004 | current waiting-for-input/permission can stall | waiting states exclude stall |
| M06-PURE-012 | FR-STATE-003 | new progress leaves stall active | transition leaves possibly_stuck with recovery evidence |
| M06-PURE-013 | FR-STATE-003 | threshold selection ignores specificity/conflict | account > provider > organization > global; equal conflict fails |
| M06-PURE-014 | FR-DISC-005 | tree aggregate changes node state | aggregate attention is separate and state counts are exact |
| M06-PURE-015 | FR-DISC-005 | inclusive/unknown token inputs are summed | only compatible disjoint inputs aggregate; exclusions reported |
| M06-PURE-016 | FR-DISC-006 | incompatible metric units/scopes aggregate | result is not_aggregatable/partial with reasons |
| M06-PURE-017 | FR-DISC-005/006 | missing metric becomes zero | missing remains unknown/unsupported/unavailable as supplied |
| M06-PURE-018 | FR-DISC-004 | approved Strong unique rule remains unresolved | automatic match occurs only for exact approved rule/version |
| M06-PURE-019 | FR-DISC-004 | weak timing/path/display evidence chooses account | decision stays unresolved/confirmation_required |
| M06-PURE-020 | FR-DISC-004 | conflicting evidence uses score/recency | decision becomes conflict and clears current account |
| M06-PURE-021 | FR-DISC-004 | owner confirmation rewrites history | new immutable current decision preserves prior decision |
| M06-PURE-022 | NFR-COMP-001 | duplicate/late generation emits repeated/regressive transition | same generation dedups; late fact does not regress current state |
| M06-PURE-023 | FR-HIST-001/003 | retention cutoff includes active/current records | only eligible ended history before explicit UTC cutoff selected |
| M06-PURE-024 | FR-DISC-008 | missing/unknown schema/version/provenance is accepted | input is rejected with stable safe code |
| M06-PURE-025 | FR-HIST-005 | naive/local timestamp is stored | input rejected or normalized only by approved boundary; domain holds UTC |
| M06-PURE-026 | FR-DISC-003/006 | unapproved/free-form field enters metadata | closed field registry rejects it |
| M06-PURE-027 | FR-DISC-003/006 | raw error/task content is accepted as safe code/label | only registered bounded code/operational label passes |

Critical state, stall, correlation, aggregation, and retention policies require branch/mutation coverage targets set by the test steward. Surviving meaningful mutants block handoff; percentage alone is not proof.

### 9.3 Real SQLite and migration tests (T2)

These tests use a real temporary SQLite file, real Alembic chain, production repositories/UoW, and production inputs obtained from real platform/provider collection where telemetry is needed. They do not seed invented telemetry. Reusing one freshly captured real observation through the production commit port is allowed to prove idempotency; it is not provider-integration evidence or a recorded fixture. Expiry deletion uses naturally aged real runtime history and the real current cutoff; if no eligible history exists, that scenario is Blocked rather than backdated or seeded.

| Test ID | Requirement | Real dependencies | Initial behavioral Red | Pass condition |
|---|---|---|---|---|
| M06-DB-001 | NFR-DATA-001 | real SQLite/Alembic | fresh migration lacks runtime schema/constraints | full chain creates exactly owned schema |
| M06-DB-002 | NFR-DATA-001 | real DB + live process input | process tuple uniqueness permits PID-only duplicate | approved identity uniqueness enforced |
| M06-DB-003 | FR-DISC-008 | real DB + production ingest | provenance/version omitted yet commits | transaction rejects and stores nothing |
| M06-DB-004 | NFR-TEST-001 | real DB + one live batch | same run/digest duplicates rows/events | same receipt/IDs returned, no duplicate facts |
| M06-DB-005 | NFR-RES-001 | real DB + one live batch | same run/different digest overwrites/duplicates | hard commit conflict, original preserved |
| M06-DB-006 | NFR-RES-001 | real DB concurrent clients | concurrent identical ingest creates divergent current state | one commit/replay-safe receipt |
| M06-DB-007 | AC-OPS-003 | real DB + valid/invalid real batches | failed batch erases/blocks unrelated runtime query | prior/unrelated data remains available |
| M06-DB-008 | NFR-COMP-001 | real DB | observation/current/event/receipt partially commit | atomic all-or-none transaction/outbox |
| M06-DB-009 | FR-DISC-004 | real DB + real session/account refs | two current account decisions commit | one current decision; conflict/history preserved |
| M06-DB-010 | FR-STATE-003 | real DB | duplicate same-scope policy/current versions persist | unique current policy and optimistic conflict |
| M06-DB-011 | FR-HIST-002 | real DB with freshly collected real history | unbounded/unstable pagination repeats or misses rows | deterministic bounded cursor and measured index plan |
| M06-DB-012 | FR-HIST-001/003 | real DB + naturally aged real history + current UTC cutoff | purge deletes active/current or misses eligible history | bounded eligible deletion, audit result, referential integrity; Blocked until eligible data exists |
| M06-DB-013 | NFR-COMP-001 | real DB | late observation regresses projection/emits transition | history accepts it; current/outbox do not regress |
| M06-DB-014 | NFR-DATA-001 | real DB/backup adapter | restored DB violates runtime invariants unnoticed | schema/receipt/graph/current invariant check gates readiness |
| M06-DB-015 | NFR-DATA-001 | real supported prior DB artifacts | upgrade loses/reinterprets runtime values | approved migrations preserve semantics/recover safely |

### 9.4 Real Linux platform tests (T5)

Linux tests use actual OS processes and current production A04/M06 code. Provider-specific claims require real Claude/Codex/Ollama processes. A separately approved AgentMonitor-owned harmless process workload may prove generic PID/race/performance mechanics but cannot count as provider/session evidence or impersonate a provider.

| Test ID | Requirement/AC | Initial behavioral Red | Pass condition/coordination |
|---|---|---|---|
| M06-LNX-001 | FR-DISC-001; AC-PROC-001 | real provider process absent/missed or launch affected | representative current processes discovered without workflow/input/state change; owner present |
| M06-LNX-002 | FR-DISC-002 | PID accepted without validated start identity | tuple verified against real process/source |
| M06-LNX-003 | FR-DISC-002 | process exits during inspection becomes wrong current row | typed race outcome and no misattribution |
| M06-LNX-004 | FR-DISC-002 | real CPU/memory/state units are mislabeled | values/semantics reconcile with approved OS source |
| M06-LNX-005 | FR-DISC-002 | working-directory permission/path is leaked or guessed | approved safe label/field-state only; owner reviews |
| M06-LNX-006 | FR-DISC-002 | wrapper/reparent ancestry becomes false durable edge | validated ancestry plus ambiguity state |
| M06-LNX-007 | FR-DISC-005; AC-PROC-002 | representative real hierarchy differs from UI tree | provider/OS evidence produces owner-confirmed correct tree or visible unresolved conflict |
| M06-LNX-008 | FR-DISC-007; AC-PROC-004 | inspection output/storage includes env/content/secret | schema/log/DB/artifact inspection proves absence |
| M06-LNX-009 | FR-SAFE-002 | process/profile state changes during observation | pre/post approved checks prove no signal/attach/input/restart/file mutation |
| M06-LNX-010 | NFR-PERF-001 | 200-process target exceeds measured latency/resource budget | real approved process workload meets synchronized budget without content capture |

### 9.5 Real macOS platform tests (T5)

| Test ID | Requirement | Pass condition | Current status |
|---|---|---|---|
| M06-MAC-001 | NFR-PLAT-001 | real macOS process identity/start tuple implements same semantic contract | Blocked until real supported macOS is available |
| M06-MAC-002 | NFR-PLAT-001 | real hierarchy/race/permission outcomes remain truthful | Blocked until real supported macOS is available |
| M06-MAC-003 | NFR-PLAT-001 | CPU/memory/state/working-label units and privacy verified | Blocked until real supported macOS is available |
| M06-MAC-004 | FR-DISC-007/FR-SAFE-002 | real inspection proves no environment/content/control path | Blocked until real supported macOS is available |

Linux success never changes these rows to Passed.

### 9.6 Live provider/session tests (T6)

Each scenario runs only after the exact provider/version/source capability is supported and the owner identifies real running sessions. Dynamic values are reconciled by identity/unit/range/freshness/source, never hardcoded. Naturally unavailable states are Blocked.

| Test ID | Requirement/AC | Real boundary | Pass condition |
|---|---|---|---|
| M06-LIVE-001 | FR-DISC-001 | real Claude agent/process | process/session presence is truthful and read-only |
| M06-LIVE-002 | FR-DISC-001 | real Codex agent/process | process/session presence is truthful and read-only |
| M06-LIVE-003 | FR-DISC-001 | real Ollama agent/process/runtime | supported process/session presence is truthful and read-only |
| M06-LIVE-004 | FR-DISC-003/006/008; AC-PROC-004 | supported local provider metadata | only approved fields/versions persist; DB/log/export scan finds no prohibited data |
| M06-LIVE-005 | FR-DISC-004; AC-PROC-003 | real ambiguous/provable session + registered account | strong rule or owner confirmation maps; weak case remains unresolved |
| M06-LIVE-006 | FR-DISC-005; AC-PROC-002 | real representative parent/subagent trees | owner and approved provider/OS evidence agree or conflict is visible |
| M06-LIVE-007 | FR-DISC-006; AC-HIST-001 | real supported metrics through DB/API/built UI | source/unit/time/confidence/history/chart reconcile; unsupported fields explicit |
| M06-LIVE-008 | FR-STATE-001..004; AC-PROC-005 | real ten-minute observation and naturally available waits/states | possible-stall threshold/evidence works; observable user/permission wait excluded |

The owner does not create, exhaust, interrupt, log out, switch, or damage work solely to manufacture a state. If a definitive wait/crash/rate-limit/auth state is not naturally available, the live row is Blocked while pure state policy may still pass.

### 9.7 Real HTTP and built-browser coordination (T3/T4)

P01/P02 own implementation, but M06 cannot claim integrated completion without these real-boundary rows. Tests start the production service on loopback, use real migrations/authentication, and for telemetry paths use real observations collected in the same environment—not seeded rows.

| Test ID | Layer | Requirement/AC | Initial behavioral Red | Pass condition |
|---|---|---|---|---|
| M06-API-001 | T3 HTTP | AC-UI-002 | route bypasses auth/port or leaks internal model | authorized generated schema returns safe M06 view only |
| M06-API-002 | T3 HTTP | FR-HIST-002/005 | history pagination/time/provenance differs from contract | bounded stable page, RFC3339 UTC, source metadata |
| M06-API-003 | T3 HTTP | FR-STATE-002; AC-UI-005 | unknown/stale/unsupported/partial collapse or GET triggers collection | distinct states; GET side-effect free |
| M06-API-004 | T3 HTTP | FR-STATE-003 | policy update lacks auth/CSRF/idempotency/version | correct guards and effective policy response |
| M06-API-005 | T3 HTTP | AC-PROC-003 | manual correlation guesses/races/leaks evidence | explicit confirmed decision or safe conflict |
| M06-UI-001 | T4 browser | AC-UI-002 | real sessions/tree cannot be navigated | built UI renders real current data from generated client |
| M06-UI-002 | T4 browser | AC-PROC-003 | unresolved mapping is hidden/auto-selected | unresolved/conflict shown; owner confirmation explicit |
| M06-UI-003 | T4 browser | AC-UI-006; AC-HIST-001 | aggregates/history omit sources/exclusions | provenance/confidence/times/aggregate exclusions accessible |
| M06-UI-004 | T4 browser | AC-UI-005 | empty/partial/stale/unsupported/permission/error misrepresented | truthful actionable states with no placeholder telemetry |

### 9.8 Architecture, security, operations, and performance gates

| Test ID | Layer | Requirement | Pass condition |
|---|---|---|---|
| M06-ARCH-001 | quality | NFR-ARCH-001 | automated imports show domain has only approved inward dependencies |
| M06-ARCH-002 | quality | NFR-ARCH-001/002 | no other module internal/table import and no cycle/direct DB access |
| M06-ARCH-003 | contract | NFR-COMP-001 | schemas/events/migrations match synchronized versions and compatibility diff |
| M06-SEC-001 | security | NFR-PRIV-001 | source/schema scan finds no prohibited runtime field |
| M06-SEC-002 | real platform/security | FR-DISC-007 | no arbitrary environment read/request/retention occurs |
| M06-SEC-003 | real DB/log | NFR-SEC-001/NFR-OBS-001 | logs/errors/outbox/diagnostics contain allowlisted safe fields only |
| M06-SEC-004 | real DB/export | AC-PROC-004 | DB/backup/export inspection contains no content/secret/raw payload |
| M06-SEC-005 | contract/API/static | FR-SAFE-002 | no process-control or routing operation exists |
| M06-SEC-006 | live platform | FR-SAFE-002 | observation leaves target processes/provider state unchanged |
| M06-SEC-007 | test-integrity | NFR-TEST-002 | automated scan/review finds no doubles/recordings/seeded telemetry/test-only path |
| M06-SEC-008 | dependency/network | NFR-PRIV-002 | no analytics/crash reporting/outbound M06 telemetry |
| M06-OPS-001 | T7/health | NFR-OBS-001 | real service exposes bounded safe M06 health and degraded states |
| M06-OPS-002 | T7/resilience | NFR-RES-001/AC-OPS-003 | one real failed/unavailable source leaves other queries/service available |
| M06-OPS-003 | T7/retention | FR-HIST-003 | canonical retention routine invokes real M06 bounded deletion and reports truthfully |
| M06-OPS-004 | T7/export | FR-HIST-004 | M08 export uses M06 port and includes only approved fields |
| M06-OPS-005 | T7/restart | NFR-RES-001 | restart reconciles receipt/outbox/current state without duplicates |
| M06-OPS-006 | automation | AC-TEST-006 | canonical report keeps T5/T6 Blocked/Not Run separate from deterministic green |
| M06-OPS-007 | docs | NFR-DOC-001 | automated docs/link/traceability/runbook gate passes |
| M06-OPS-008 | dependency | NFR-LIC-001 | exact lock/SBOM/notices/license/security admission passes |
| M06-PERF-001 | performance | NFR-PERF-001 | current/tree/history queries meet synchronized workstation budget with 200 real observed process records |
| M06-PERF-002 | performance | NFR-PERF-001 | ingest/retention remain bounded and API responsive under approved real workload |

### 9.9 Failure, migration, and recovery coverage

The test matrix covers incomplete identity, PID reuse/exit race, permission denial, malformed/unapproved input, unknown schema/version, partial source, duplicate/conflicting commit, late/out-of-order observations, hierarchy cycle/orphan, weak/conflicting account evidence, wait/stall transitions, concurrent policy/confirmation, database unavailable/busy, outbox failure, restart reconciliation, retention, upgrade, backup/restore, API authorization, provider/platform unavailable, and absence of macOS/rare provider states.

No test manufactures a provider failure response. Failure scenarios requiring a provider condition use a real naturally occurring condition or remain Blocked. Pure policy inputs prove only pure policy.

### 9.10 Test-integrity rules

- No mock, fake, stub, emulator, simulated provider/process, recorded/replayed response, provider fixture, demo account, seeded telemetry, placeholder metric, monkeypatch of a production collaborator, or test-only production branch is permitted.
- T1 may construct domain values only while remaining entirely free of database, filesystem, network, process, environment, provider, clock, and framework I/O.
- T2 uses a real SQLite file, real migrations, production repositories, and real telemetry obtained through production adapters when telemetry is required.
- T3 starts the production FastAPI service and sends real HTTP requests; direct route calls are not evidence.
- T4 builds/serves the production UI and drives a real supported browser; DOM-only rendering is not evidence.
- T5 uses an actual target OS. Linux results cannot pass macOS rows.
- T6 uses real owner-controlled accounts/current provider tools and records only sanitized evidence under the live runbook.
- T7 uses the real native/service/database/backup/restore boundary applicable to the claim.
- Passed, Failed, Blocked, and Not Run remain separate in every command and handoff. Skipped or unavailable is never Passed.
- Dynamic values are reconciled by identity, source, unit, precision, range, relationship, and freshness rather than copied into hardcoded assertions.
- A test must fail when the protected behavior regresses; source-text or constant assertions cannot replace behavior.

## 10. Implementation increments

Every increment begins with its listed behavioral test at the correct real boundary, records expected Red, implements the minimum Green, refactors while all relevant tests remain green, and updates contracts/docs/evidence in the same change.

| Increment | Scope/owned paths | Failing tests first | Minimum production outcome | Exit evidence |
|---|---|---|---|---|
| M06-I00 | automation/contract setup after synchronization | M06-ARCH-001..003, M06-OPS-006/007 | register M06 canonical selectors, contract/version sources, boundary rules; no behavior yet | real gate commands fail for missing module behavior, not setup |
| M06-I01 | pure identity/field policies | M06-PURE-001..003/024..027 | process/session/field/provenance value objects and validation | Red/Green/refactor + mutation review |
| M06-I02 | process persistence | M06-DB-001..004 | process identity/snapshot schema, repository, idempotent first commit | real SQLite/Alembic evidence |
| M06-I03 | session/metric persistence | M06-PURE-016/017; M06-DB-003/004/011 | safe session/metric observations and bounded history | real captured input + real DB evidence |
| M06-I04 | hierarchy | M06-PURE-004/005/014..017; M06-DB-006 | links, cycle/orphan policy, tree and aggregate queries | pure + real DB concurrency/query-plan evidence |
| M06-I05 | correlation | M06-PURE-018..021; M06-DB-009 | evidence/decision history, manual confirmation ports/events | real M02/DB integration; API remains separate |
| M06-I06 | state classifier | M06-PURE-006..008/022; M06-DB-008/013 | normalized current state and idempotent transitions/outbox | pure mutation + real DB atomicity |
| M06-I07 | stall policy | M06-PURE-009..013; M06-DB-010 | scoped 600-second inference policy and event | pure/DB evidence; M07 contract review |
| M06-I08 | collection commit/recovery | M06-DB-004..008, M06-OPS-005 | synchronized M04 commit/status receipt and restart reconciliation | real M04/M03/M06 stack |
| M06-I09 | Linux adapter integration | M06-LNX-001..009 | accept real A04 process observations and provider links | owner-coordinated real Linux evidence |
| M06-I10 | provider session integration | M06-LIVE-001..008 | enable only evidence-supported provider/session fields/capabilities | per-provider sanitized live reports; blocked rows visible |
| M06-I11 | retention/health/export | M06-DB-012/014/015, M06-OPS-001..005 | retention port, safe health, M08 query/export/restore validation | real DB/service/ops evidence |
| M06-I12 | API/UI integration | M06-API-001..005, M06-UI-001..004 | P01/P02 consume frozen ports through generated client | real HTTP and built-browser evidence |
| M06-I13 | performance/hardening | M06-LNX-010, M06-PERF-001/002, M06-SEC-001..008 | measured bounds, privacy/control/test-integrity gates | canonical quality/security/live evidence |
| M06-I14 | macOS compatibility | M06-MAC-001..004 | real A04-MAC integration without domain change | real macOS Passed or visible Blocked; no simulation |

### 10.1 Ordering and parallel safety

I00–I01 follow contract synchronization. I02/I03 may proceed in separate owned files only after central migration allocation and may not edit the same revision/UoW. I04–I07 can proceed in parallel at the pure-domain level after shared value contracts freeze, but persistence/outbox integration is serialized through the M06 owner. A01–A04, M07, P01, and P02 work in parallel against frozen contracts and never edit M06 internals. I08 integrates M04; I09/I10 require real evidence; I11–I13 integrate operations/transport/UI; I14 is gated by real macOS access.

### 10.2 Stop points during implementation

Stop immediately and return to contract/discovery review if:

- a provider/platform field/source/version differs from M0 evidence;
- safe identity requires a raw path, email, credential, environment, memory, terminal, prompt/response/tool/source field;
- correlation would require guessing or a score threshold not approved by M0/CS;
- process control/injection/signal/restart/routing is requested;
- another module's table/internal code appears necessary;
- CTR-RUN meaning/required field/unit/privacy/event ordering changes;
- a migration can destroy/reinterpret existing data or cannot recover safely;
- a new dependency lacks full admission or introduces telemetry/native/privilege risk;
- live testing needs login/logout/account switch/agent interruption/cost without explicit owner authorization;
- real behavior contradicts the approved state/hierarchy/stall assumptions;
- a secret/content value appears in output, storage, logs, artifacts, screenshots, or chat.

## 11. Documentation outputs

M06 implementation must create/update in one reviewed change:

- `docs/modules/runtime-observation.md`: purpose, invariants, states, hierarchy, correlation, aggregation, data, ports, failures, extension points;
- `docs/contracts/runtime-observation-v1.md`: complete CTR-RUN-001..007 schemas, units, null/state semantics, events, compatibility;
- M06 field/privacy allowlist with M0 evidence references and provider/platform/version scope;
- generated OpenAPI and TypeScript client source changes through P01/FND only;
- API human guidance for process/session/tree/history/correlation/stall policy;
- `docs/operations/runtime-observation.md` verified operator procedures;
- migration/upgrade/recovery notes and schema compatibility range;
- sanitized test-evidence/live-test reports and Blocked/Not Run matrix;
- traceability, risk-register, planning/contract registry, capability matrices, and known limitations;
- dependency admission/SBOM/notices updates if any dependency is admitted;
- release notes describing supported provider/platform/runtime fields and limitations.

No documentation contains real account identity, local absolute paths, PIDs tied to identity, raw provider output, prompt/response/tool/source content, environment, or secret-bearing screenshots.

## 12. Dependency and license impact

### 12.1 Current proposal

M06 domain/application code proposes **no new direct runtime dependency**. It uses approved foundation contract primitives. The persistence adapter uses the centrally admitted SQLAlchemy/Alembic stack. M06 does not add `psutil`, provider SDKs, subprocess libraries, graph libraries, schedulers, analytics, or telemetry packages; platform/provider owners decide their own dependencies.

The standard library is sufficient for pure graph traversal, state policy, exact integer counters, and typed dataclasses once the foundation style is selected. Do not implement cryptography or secure keyed identity material in M06; if a non-reversible provider-session fingerprint is needed, the security/foundation owner must select the reviewed primitive and contract.

### 12.2 Test/tool dependencies

Test runner, property/mutation testing, type/lint/import/security/secret/license scanners, real browser, SBOM, and notices tools are foundation-owned candidates. M06 uses only admitted, locked versions. It does not install a convenience package independently.

### 12.3 Admission record

Any later proposed package must document exact purpose, upstream/package identity, exact version, direct/transitive licenses, maintenance/security/provenance, native components, install scripts/network/telemetry, platform support, lock/SBOM/notices effect, alternatives, removal plan, and reviewer/date. Copyleft/custom/unclear licenses require explicit owner approval. No manifest change precedes approval.

## 13. Risks and unresolved decisions

### 13.1 Risk register

| Risk/question | Likelihood/impact | Mitigation/evidence | Owner | Trigger | Status |
|---|---|---|---|---|---|
| R-003 process/session cannot prove account | High/Critical | unresolved/manual confirmation; no guess; M0/live matrix | M06/M02/adapters | weak/conflicting evidence | Open |
| R-004 default profile/process is disturbed | Low/Critical | read-only contracts, no control, live pre/post checks | A01–A04/security | mutation/prompt/state change | Open |
| R-005 content/secret/environment leaks | Medium/Critical | closed schemas, field register, negative storage/log/export tests | M06/security | unexpected field/output | Open |
| R-009 rare real states unavailable | High/Major | pure policy + visible Blocked live rows | test/integration | state cannot safely occur | Accepted project risk |
| R-010 live test interrupts work | Medium/Major | owner scheduling, existing agents, zero control | live operator | agent behavior/cost change | Open |
| R-011 SQLite growth/locking | Medium/Major | short transactions, indexes, retention, real measurement | M06/DB/M08 | busy/latency/storage growth | Open |
| R-012 SQLite coupling | Medium/Major | repository ports/portable types/query review | M06/DB | dialect leaks domain | Monitoring |
| R-015 PID reuse/hierarchy ambiguity | Medium/Major | start/executable identity, conflict unknown, real races | M06/A04 | reuse/exit/wrapper ambiguity | Open |
| R-016 stall false positives | High/Moderate | current positive evidence, wait exclusions, 600-second policy, live tuning | M06/M07 | noisy dismissals/mismatch | Open |
| R-019 CI mistaken for live evidence | Medium/Major | split T5/T6 status in canonical gate | integration | aggregate green hides Blocked | Open |
| R-023 macOS degrades | Medium/Major | portable contract + visible real-macOS Blocked gate | A04-MAC/M06 | Linux field leaks core | Open |
| Runtime aggregate double-counts | Medium/Critical | disjoint eligibility and explicit excluded inputs | M06/provider adapters | inclusive/unknown metric scope | Open |
| Late/out-of-order input regresses state | Medium/Major | observation generation/current ordering/idempotency | M06/M04 | provider timestamps/sequence conflict | Open |
| Policy change creates alert storm | Medium/Major | bounded reevaluation, event dedup, M07 sync | M06/M07 | mass transitions | Open |

### 13.2 Approval-blocking synchronization decisions

1. Exact M0-approved process identity/start marker per Linux and macOS, including boot scope and precision.
2. Exact approved process CPU/memory/state/working-directory fields and units per platform.
3. Exact provider session identity scope/lifetime and safe storage/display representation per provider/version.
4. Exact provider safe model/project/task/token/context/activity/error/wait/hierarchy fields and unsupported fields.
5. Which corroborated correlation rules, if any, may auto-match; otherwise automatic match is Strong-only.
6. Narrow M02 account/identity/scope contracts and runtime manual-confirmation permission.
7. Final M06 typed provider/platform input contracts and allocated contract IDs.
8. Final CTR-COL-006 commit/status semantics and payload-digest authority.
9. Process-session/session-parent multiplicity and provider-specific evidence mapping.
10. Aggregate attention ranking, co-observation tolerance, and overlap vocabulary.
11. State evidence precedence/freshness and safe raw-state code registry.
12. Stall override allowed range, authorization, mass reevaluation/event behavior, and M07 recovery consumption.
13. Whether `RuntimeActivityClassChangedV1` is added under CTR-RUN-004 for M04.
14. Whether authenticated UI may display a raw working directory or only a safe label; default proposal is safe label only.
15. Exact runtime query/filter/cursor/tree bounds and performance budgets.
16. Table/migration/outbox ownership and revision allocation.
17. Retention ordering across observations, correlation evidence, transitions, active shells, export, and backup.
18. Exact canonical automation selectors/commands under foundation routines.
19. Real macOS environment/version availability; absence remains Blocked.
20. Whether any changed finding requires an ADR, threat-model update, or requirement amendment.

No item above may be silently selected by an implementation agent if alternatives materially change behavior, privacy, compatibility, or tests.

## 14. Delivery and rollback

### 14.1 Delivery order

1. Complete M0 runtime/platform/provider evidence and capability decisions.
2. Synchronize common, registry, provider, collection, platform, runtime, alert, operations, API, UI, and DB contracts.
3. Approve this plan and dependency/field/privacy registers.
4. Implement pure contracts/policies and canonical automation selectors through TDD.
5. Apply expand-only schema and repository/commit behavior to real SQLite.
6. Integrate A04-LINUX and provider adapters one proven capability at a time, disabled unless capability/version/source is supported.
7. Integrate M07/P01/P02/M08 consumers through versioned ports/generated artifacts.
8. Run real Linux/provider/API/browser/operations/live matrices and keep macOS/rare state gaps visible.
9. Measure performance, exercise backup/restore/retention, complete security/privacy/license/docs reviews.

### 14.2 Compatibility and feature exposure

M06 starts with no enabled provider/platform capability until its exact manifest/source/version is approved and live verified. Additive optional contract fields require safe absence behavior. Changes to identity, units, field privacy, state/certainty meaning, correlation proof, aggregation, event ordering, or persistence interpretation require a new major/ADR/migration/consumer plan.

### 14.3 Rollback and recovery

- Before real data: remove disabled code only through normal version-control change; do not rewrite shared migration history.
- After an expand migration but before exposure: older binaries may run only if schema compatibility says safe; otherwise restore verified backup/prior artifact.
- Disable an affected capability/source through the approved manifest/config path when live evidence fails; preserve history and mark current data stale/unverified.
- Never roll back by deleting runtime history, editing observations, clearing correlation conflicts, or substituting cached/fake current data.
- A destructive/contracting migration requires a separate approved plan and verified backup/restore; no improvised downgrade.

### 14.4 Post-deployment checks

- schema/contract/app/adapter versions compatible;
- M06 readiness/invariants/outbox/receipt checks healthy;
- real current process/session observations fresh for enabled capabilities;
- account mappings evidence-qualified and unresolved cases visible;
- tree has no cycles and aggregate exclusions visible;
- state/stall threshold/evidence displayed correctly;
- no process/profile/provider state changed;
- logs/database/events/API/UI/exports/backups scan clean of prohibited data;
- retention/backup/restore evidence current;
- every T5/T6/T7 Blocked/Not Run row remains visible.

### 14.5 Implementation handoff contents

The M06 handoff must name exact requirement/AC IDs, plan/contract/schema versions, files and migrations changed, Red/Green/refactor commands/results per increment, real DB/API/browser/Linux/macOS/provider/operations status, owner acknowledgements, Failed/Blocked/Not Run rows, contract/API/migration diffs, security/privacy/no-control proof, dependency/license/SBOM/notices impact, performance results, rollback/recovery evidence, docs changed, known risks, and next integration step.

## 15. Definition of ready

- [ ] M0 runtime/provider/platform scenarios and handoff packets are reviewed and scoped to exact versions.
- [ ] Requirements, interpretations, outcome, non-goals, and V1 no-control/privacy boundary are approved.
- [ ] M06 paths/imports/table/migration/generated-file ownership is conflict-free.
- [ ] CTR-RUN-001..007 and runtime ingest/commit schemas are synchronized with all producers/consumers.
- [ ] PID/start identity, session identity, provider field allowlists, units, freshness, and version rules are evidence-backed.
- [ ] Correlation evidence/owner confirmation/conflict behavior is synchronized with M02/P01/P02.
- [ ] State precedence, certainty, activity, stall threshold/precedence/wait exclusions, and M07 recovery semantics are frozen.
- [ ] Hierarchy/orphan/cycle/aggregate overlap semantics are frozen.
- [ ] Database tables, revisions, transactions, indexes, retention, backup/restore, and portability are reviewed.
- [ ] Every scenario has correct real resources, owner coordination, expected behavioral Red, and truthful Blocked policy.
- [ ] Canonical fail-closed M06 automation commands/selectors exist and are tested at the real boundaries required before implementation handoff.
- [ ] Security/privacy field register, threat controls, no-control proof, and incident handling are approved.
- [ ] Dependency/license admission is complete for every selected package/tool/version.
- [ ] Documentation/runbook/handoff outputs and shared-file ownership are assigned.
- [ ] Planning catalog/registry and cross-plan synchronization review include PLAN-M06 and the canonical planning gate passes.
- [ ] No unresolved decision permits materially different implementation.
- [ ] Owner/root/integration/security/test/operations reviewers approve this exact plan and contract versions.

Until every applicable box is checked, the module is not implementation-ready.

## 16. Approval record

| Role | Decision | Conditions | Date |
|---|---|---|---|
| Owner | Pending |  |  |
| Root/integration steward | Pending |  |  |
| M02/M03/M04/M07/A01–A04 consumers/producers | Pending |  |  |
| DB/P01/P02/M08 reviewers | Pending |  |  |
| Security/privacy reviewer | Pending |  |  |
| Test-integrity/live-verification reviewer | Pending |  |  |
| Operations/dependency reviewer | Pending |  |  |

Approval authorizes an implementation task packet only after the canonical planning/readiness gates pass. It does not authorize provider access, authentication, installation, migration, deployment, process control, or live execution by itself.
