# Cross-plan contract and ownership alignment audit

- Audit ID: `CAA-2026-09-18-01`
- Status: **Complete as a read-only audit of the stated snapshot**
- Synchronization decision: **BLOCK**
- Snapshot date: 2026-09-18, Europe/London
- Scope: all 20 artifacts in `planning-catalog.toml`, the planning registry,
  backlog and program, contract register, architecture/module boundaries,
  product requirements and acceptance criteria, API/contract standards, SDLC,
  testing rules, and completion/automation standard
- Authority: advisory input to CS-1; this audit does not synchronize, approve, or
  version a contract and does not authorize implementation
- External/live evidence: **Not Run**; no provider, account, process, profile,
  credential, service, database, browser, GitLab, or macOS boundary was accessed

## 1. Executive decision

The 20 required planning artifacts exist and are substantial Drafts. Their
module boundaries are broadly viable. They are **not yet a synchronized,
implementation-ready plan set**.

CS-1 must remain blocked because:

1. the central contract register omits contracts already required or proposed by
   the detailed plans;
2. several contracts have multiple or ambiguous semantic producers;
3. authentication, field-state, time, exact-quantity, idempotency, event
   delivery, retention, and activation semantics are not consistently frozen;
4. M07 names upstream events and queries that no producer currently publishes;
5. database restore, deployment maintenance, readiness, and artifact/database
   activation responsibilities overlap;
6. the integration implementation DAG permits implementation before the full
   planning-readiness gate described by the SDLC and planning program;
7. shared files, migrations, generated artifacts, configuration names, live
   accounts, and evidence outputs have no executable per-wave allocation
   manifest; and
8. `AUTO-PLAN-CHECK` currently proves structural presence only. It cannot prove
   the semantic synchronization claimed by CS-1.

The provider-specific unknowns are legitimate evidence-gated uncertainties.
They are not excuses to leave provider-independent contracts ambiguous.

## 2. Audit method and evidence

The audit compared:

- every cataloged plan's owner, produced/consumed contracts, paths, tables,
  configuration, tests, evidence, Definition of Ready, and open decisions;
- every entry in `docs/plans/contract-register.md` against its producer and known
  consumers;
- the module ownership rules in `docs/architecture/modules.md`;
- requirement and acceptance ownership in `docs/product/requirements.md` and
  `docs/product/v1-acceptance-criteria.md`;
- the versioning rules in `docs/architecture/contracts-and-versioning.md` and
  transport rules in `docs/api/api-standards.md`; and
- the mandatory automation claims in
  `docs/engineering/completion-and-automation-gates.md`.

Canonical structural gate evidence at the final audit snapshot:

```text
python3 tools/planning/validate_plans.py --stage synchronized
exit 1: missing docs/plans/integration/cs1-full-plan-synchronization.md

python3 -m unittest tools/planning/test_validate_plans.py
exit 1: the real-repository synchronized-plan test fails for the same reason
```

The checkout is not a Git repository. Per the automation standard this is a
visible Git/GitLab **Blocked** condition, not authority to initialize Git.

### Severity and decision vocabulary

- **Critical**: could violate security/privacy, corrupt/lose state, or authorize
  implementation on contradictory contracts.
- **Major**: prevents independent implementation or truthful integration.
- **Moderate**: creates likely drift, duplicate work, or ambiguous evidence.
- **Minor**: documentation/currentness issue that does not alone alter behavior.
- **PASS-DRAFT**: ownership/direction is coherent enough to carry into CS-1;
  this is not contract synchronization.
- **BLOCK**: the interface or plan cannot be approved for implementation.
- **EVIDENCE-BLOCKED**: architecture can be synchronized, but provider/platform
  capability approval needs real evidence.

## 3. Module, adapter, and boundary inventory

| Unit | Sole semantic ownership | Publishes/implements | Must remain outside | Audit decision |
|---|---|---|---|---|
| PLAN-FND | repository/tooling/composition mechanisms and stable technical primitives | CTR-FND-001..008; mechanisms underlying common/config contracts | business policy, provider semantics, API resource meaning | BLOCK: shared-file and generator stewardship not frozen |
| M01 | dashboard administrator, authorization, session/CSRF, API-token and IAM audit semantics | CTR-IAM-001..008 | provider authentication/profile mechanics | BLOCK: transport, permission, one-time-secret, recovery decisions open |
| M02 | organizations, accounts, installations, monitoring profiles/resources, provider identity decisions | CTR-REG-001..007 | collection, quota health, runtime correlation | BLOCK: reauth coordination and alert-scope/current-input ports missing |
| M03 | provider protocol, capability/source vocabulary, adapter registration and compatibility | CTR-PROV-001..008 | provider implementation and observed business data | EVIDENCE-BLOCKED plus boundary/event contracts missing |
| M04 | schedules, collection admission, leases, retries/backoff, run lifecycle and collector health | CTR-COL-001..005; proposed COL-006 | capacity/runtime interpretation | BLOCK: result-commit and collector-health event gaps |
| M05 | quota/budget observations, exact values, normalized capacity health, forecast/history | CTR-CAP-001..007 | provider fetches and alert lifecycle | BLOCK: health policy and forecast/availability event gaps |
| M06 | process/session observations, hierarchy, runtime state/stall, session correlation | CTR-RUN-001..007 semantic side | OS inspection implementation and provider-specific parsing | BLOCK: RUN-006 ownership and activity/commit inputs unresolved |
| M07 | alert rules, precedence, alert lifecycle and dashboard-notification truth | CTR-ALERT-001..005 | email/messenger delivery and upstream metric truth | BLOCK: six upstream/durability gaps prevent real lifecycle recovery |
| M08 | application health/readiness, backup catalog, restore orchestration, retention/export/diagnostics and product audit | CTR-OPS-001..006 | native service mechanics, SQLite implementation, IAM security audit | BLOCK: module participant ports and maintenance/activation split unresolved |
| A01 | Claude/Anthropic provider-specific mapping behind M03 ports | implements CTR-PROV; provider extensions | core domain policy, account ownership decisions | EVIDENCE-BLOCKED: M0 and live account/version facts absent |
| A02 | Codex/OpenAI provider-specific mapping behind M03 ports | implements CTR-PROV; provider extensions | core domain policy, account ownership decisions | EVIDENCE-BLOCKED: M0 and live account/version facts absent |
| A03 | Ollama local/cloud/API-specific mapping behind M03 ports | implements CTR-PROV; provider extensions | core domain policy, local/cloud identity guesses | EVIDENCE-BLOCKED: M0 and taxonomy/source facts absent |
| A04-LINUX | Linux implementations of process/filesystem/service primitives | implements RUN-006/DEP-001 portions; platform primitive family | runtime/domain semantics and deployment policy | EVIDENCE-BLOCKED; PLAT semantic owner ambiguous |
| A04-MAC | macOS implementations of the portable platform boundary | implements RUN-006/DEP-001 portions; macOS platform extension | Linux acceptance credit and unverified source claims | EVIDENCE-BLOCKED: real Mac absent; common platform family unresolved |
| P01 | HTTP/security transport and OpenAPI mapping | CTR-API-001..003; API side of UI-001 | domain orchestration, provider calls, direct persistence | BLOCK: source ports, code vocabularies and idempotency conflict open |
| P02 | browser application, accessibility/responsive behavior, generated-client wrapper | consumes CTR-UI/API only | backend internals, direct DB/provider/filesystem access | BLOCK: generated client/OpenAPI and auth-state distinction unresolved |
| PLAN-DB | SQLite implementation, schema compatibility, linear migration and physical DB lifecycle mechanics | CTR-DB-001..003 implementation family | business table/retention semantics | BLOCK: DB-003 absent from register and activation/event decisions open |
| PLAN-DEP | native installed release, service lifecycle, quiescence and artifact rollback | CTR-DEP-001 | DB semantics, app readiness truth, module maintenance policy | BLOCK: maintenance/readiness/activation split unresolved |
| PLAN-INT | release baselines, evidence/gate aggregation and serial shared-artifact stewardship | proposed CTR-INT-001..006 | redefining module behavior or bypassing readiness | BLOCK: contracts absent and DAG contradicts program/SDLC gate order |
| PLAN-M0-DISCOVERY | evidence custody and capability decisions, not production behavior | reviewed evidence handoffs | contract approval or implementation | BLOCK for execution until G0/G1 approvals; architecture handoff is coherent |

The intended dependency direction is viable when restricted to published ports:
registry/provider/collection/platform inputs feed capacity/runtime; capacity,
runtime, collection, registry and auth-domain events feed alerting; all modules
publish narrow health/retention/export/consistency ports to operations; P01 maps
application ports; P02 consumes only generated HTTP contracts. The exceptions
and cycles are listed below.

## 4. Plan-by-plan approval decision

| Plan ID | Artifact state | Interface decision | Exact blocker before approval |
|---|---|---|---|
| PLAN-M0-DISCOVERY | detailed Draft | BLOCK execution | G0/G1 safety/evidence custody, exact operation review, owner approval; all scenarios Not Run |
| PLAN-FND | detailed Draft | BLOCK | tool/dependency admission, ownership manifest, generated-artifact writer and executable routines |
| PLAN-M01 | detailed Draft | BLOCK | IAM/API/UI contract review; permission catalog; one-time secret; restore invalidation; crypto admission |
| PLAN-M02 | detailed Draft | BLOCK | identity facts, reauth workflow owner, alert-scope/auth events, table/config/port freeze |
| PLAN-M03 | detailed Draft | EVIDENCE-BLOCKED and BLOCK | M0 matrices, safe external boundary ports, event/outbox ownership, adapter compatibility targets |
| PLAN-M04 | detailed Draft | BLOCK | COL-006, activity-class source, rate/cost evidence, durable events and config allocation |
| PLAN-M05 | detailed Draft | BLOCK | exact quantity/unit policy, health-policy owner, COL-006, forecast/availability events and event durability |
| PLAN-M06 | detailed Draft | BLOCK | Linux/provider evidence, RUN-006 sole producer, process identity/activity semantics, COL-006 |
| PLAN-M07 | detailed Draft | BLOCK | CAP-G01/G02, COL-G01, AUTH-G01, REG-G01, EVT-G01 and recovery semantics |
| PLAN-M08 | detailed Draft | BLOCK | every module's health/retention/export/consistency ports, maintenance split, DB/DEP restore protocol |
| PLAN-A01 | detailed Draft | EVIDENCE-BLOCKED | Claude/Anthropic M0/live matrix, safe execution/network ports, assigned API-budget lane |
| PLAN-A02 | detailed Draft | EVIDENCE-BLOCKED | Codex/OpenAI M0/live matrix, safe execution/network ports, assigned API-budget lane |
| PLAN-A03 | detailed Draft | EVIDENCE-BLOCKED | Ollama local/cloud/API identity/source matrix, safe network/process ports, assigned API-budget lane |
| PLAN-A04-LINUX | detailed Draft | EVIDENCE-BLOCKED | M0 Linux facts, portable platform contract, service/process implementation review |
| PLAN-A04-MAC | detailed Draft | EVIDENCE-BLOCKED | real Mac and approved commands/sources; cannot satisfy Linux-specific acceptance |
| PLAN-P01 | detailed Draft | BLOCK | application port inventory, permission/problem/idempotency contract, OpenAPI tool admission |
| PLAN-P02 | detailed Draft | BLOCK | synchronized OpenAPI/client generator/runtime validation and real browser dependency admission |
| PLAN-DB | detailed Draft | BLOCK | module repository ports, DB-003 registration, outbox architecture, migration/shared-file stewardship |
| PLAN-DEP | detailed Draft | BLOCK | target inventory, native service contract, maintenance/readiness split and canonical deployment routines |
| PLAN-INT | detailed Draft | BLOCK | register INT contracts; repair gate order; freeze ownership/evidence/release manifests and routine contracts |

No plan has an owner approval record. No plan may move to implementation on the
basis of artifact length or scenario count.

## 5. Registered contract producer/consumer ledger

Every registered ID is listed below. `BLOCK` means the current Draft mapping is
useful but not synchronized. Consumers shown are the union of the register and
detailed plans where the latter adds an explicit consumer.

### 5.1 Common, configuration, and schema compatibility

| Contract | Producer | Consumers | Decision and required resolution |
|---|---|---|---|
| CTR-COMMON-001 `OpaqueIdV1` | FND/common contracts | all modules, API, UI | BLOCK: freeze generation/serialization/order and prohibit semantic parsing |
| CTR-COMMON-002 `TimestampAndDurationV1` | FND/common contracts | all | BLOCK: resolve offset-vs-`Z`, precision, wall/monotonic and duration units |
| CTR-COMMON-003 `ExactQuantityV1` | FND/common contracts | M05, P01, P02 | BLOCK: choose canonical decimal/minor-unit/ratio representation and bounds |
| CTR-COMMON-004 `ObservationProvenanceV1` | register says M03 + FND | M04/M05/M06/P01/P02 | BLOCK: assign one semantic producer; separate generic schema from domain derivation |
| CTR-COMMON-005 `SafeProblemV1` | P01 | P02/external API clients | BLOCK: distinguish dashboard auth from provider reauth; freeze safe extensions |
| CTR-COMMON-006 `EventEnvelopeV1` | FND/common contracts | every event producer/consumer | BLOCK: envelope direction is sound; durable receipt/outbox/replay is missing |
| CTR-CONFIG-001 `ConfigurationRegistryV1` | FND mechanism + key-owning modules | M08/P01/diagnostics/DEP/all configured components | BLOCK: key namespace, precedence, reload, visibility and single writer not allocated |
| CTR-DB-001 `SchemaCompatibilityV1` | PLAN-DB | composition/DEP/M08 | BLOCK: exact range/status/startup behavior and build binding not frozen |

### 5.2 Foundation

| Contract | Producer | Consumers | Decision and required resolution |
|---|---|---|---|
| CTR-FND-001 repository layout/ownership manifest | PLAN-FND/architecture steward | every plan | BLOCK: executable path/import/shared-writer manifest does not exist |
| CTR-FND-002 application factory | PLAN-FND | P01/DEP/composition/real-stack tests | BLOCK: lifecycle and typed startup outcomes require consumer sign-off |
| CTR-FND-003 bootstrap configuration | PLAN-FND mechanism; modules own keys | all modules/adapters/M08/DEP | BLOCK: synchronize with CONFIG-001 and allocate exact keys |
| CTR-FND-004 correlation/safe log | PLAN-FND | all components/M08 | BLOCK: align ID/event fields and allowlist enforcement with COMMON-001/006 |
| CTR-FND-005 OpenAPI/generated client | ambiguous API/integration generator steward | P01/P02/external clients | BLOCK: split API semantic owner, generator mechanism owner and sole artifact writer |
| CTR-FND-006 migration metadata | migration integration steward | table owners/DB/M08/DEP | BLOCK: catalog location/writer/checksum/status rules require approval |
| CTR-FND-007 build metadata | PLAN-FND | M08/P01/P02/release | BLOCK: exact safe identities/digests and artifact binding not frozen |
| CTR-FND-008 test evidence summary | test/integration steward | every handoff/release gate | BLOCK: align with proposed INT evidence/routine schemas and executable reporters |

### 5.3 Identity and access

| Contract | Producer | Consumers | Decision and required resolution |
|---|---|---|---|
| CTR-IAM-001 principal/permission | M01 | P01/application authorization/M08 audit | BLOCK: one route-to-permission/scope catalog required |
| CTR-IAM-002 authorization decision/port | M01 | P01/application orchestrators | BLOCK: denial, subject context and audit behavior not frozen |
| CTR-IAM-003 browser session/CSRF | M01 semantics | P01/P02 transport | BLOCK: cookie/header/expiry/touch/rotation contract open |
| CTR-IAM-004 bootstrap/authenticate/password recovery | M01 | P01/local operator/P02 | BLOCK: authority, Argon2 policy, recovery effects and problems open |
| CTR-IAM-005 logout/session query/revocation | M01 | P01/P02 | BLOCK: target/all/idempotent result and disclosure behavior open |
| CTR-IAM-006 API-token lifecycle | M01 | P01/P02/API clients | BLOCK: format/scopes/attenuation/expiry/one-time replay contract open |
| CTR-IAM-007 sensitive issue/safe summary DTOs | M01 | P01/P02/Swagger guidance | BLOCK: boundary lifetime/redaction and no-serialization enforcement needed |
| CTR-IAM-008 IAM security event/retention/restore | M01 | M08 | BLOCK: event allowlist, retention and restore invalidation transaction open |

### 5.4 Registry

| Contract | Producer | Consumers | Decision and required resolution |
|---|---|---|---|
| CTR-REG-001 organization view | M02 | M05/M06/M07/P01/P02 | BLOCK: archive/order/Ungrouped and aggregate-reference semantics |
| CTR-REG-002 account view | M02 | M04/M05/M06/M07/P01/P02 | EVIDENCE-BLOCKED: stable provider identity/masking/resource distinction |
| CTR-REG-003 monitoring profile view | M02 | M03/M04/adapters/P01 | EVIDENCE-BLOCKED: opaque locator/default protection/purpose/state |
| CTR-REG-004 provider installation view | M02 | M03/M04/M08/P01/A04 | EVIDENCE-BLOCKED: executable/version/platform/capability identity |
| CTR-REG-005 account resource view | M02 | M04/M05/P01 | EVIDENCE-BLOCKED: subscription/API/project/workspace/pool taxonomy |
| CTR-REG-006 identity correlation decision | M02 | M06/adapters/P01/P02 | EVIDENCE-BLOCKED: evidence/confidence/manual confirmation/mismatch |
| CTR-REG-007 registry changed event | M02 | M04/M05/M06/M07/M08 | BLOCK: granularity, revision, redaction, replay/durability |

### 5.5 Provider system

| Contract | Producer | Consumers | Decision and required resolution |
|---|---|---|---|
| CTR-PROV-001 `ProviderAdapterV1` | M03 | A01/A02/A03/M04/composition | EVIDENCE-BLOCKED: operations, async/deadline/cancel and compatibility |
| CTR-PROV-002 capability manifest | M03 | adapters/M04/M08/P01 | EVIDENCE-BLOCKED: source/credential/version/rate/cost declarations |
| CTR-PROV-003 provider source | M03 | adapters/M04/M05/M06 | EVIDENCE-BLOCKED: priority, stability and no-silent-fallback policy |
| CTR-PROV-004 collection outcome | M03 | adapters/M04/M05/M06 | EVIDENCE-BLOCKED: union, partial/auth/rate/deadline/version states |
| CTR-PROV-005 discovery outcome | M03 | adapters/M02/M08 | EVIDENCE-BLOCKED: identity/install evidence and owner confirmation |
| CTR-PROV-006 auth health outcome | M03 | adapters/M02/M04/M07/P01/P02 indirectly | BLOCK plus evidence: canonical auth vocabulary and domain event bridge missing |
| CTR-PROV-007 reauth flow | M03 protocol | adapters/M02/P01/P02; M04 only observes recovery | BLOCK plus evidence: durable coordinator/official flow/profile safety absent |
| CTR-PROV-008 provider extensions | each adapter, governed by M03 | M05/M06/P01/P02 | EVIDENCE-BLOCKED: schema IDs, allowlists, unknown/privacy handling |

### 5.6 Collection control

| Contract | Producer | Consumers | Decision and required resolution |
|---|---|---|---|
| CTR-COL-001 collection request | M04 | P01/scheduler/internal triggers | BLOCK: authorization, target, coalescing, deadline and idempotency |
| CTR-COL-002 collection run view | M04 | M05/M06/M07/M08/P01/P02 | BLOCK: terminal/partial/cancel vocabulary and observation refs |
| CTR-COL-003 collection completed event | M04 | M05/M06/M07/M08 | BLOCK: commit acknowledgement, occurrence/record time and replay |
| CTR-COL-004 collection failed event | M04 | M07/M08 | BLOCK: retry/auth/no-retry/recovery semantics |
| CTR-COL-005 collector health | M04 | M08/P01/P02 | BLOCK: current query semantics exist only conceptually; change event absent |

### 5.7 Capacity

| Contract | Producer | Consumers | Decision and required resolution |
|---|---|---|---|
| CTR-CAP-001 quota window | M05 | M07/P01/P02/M08 export | EVIDENCE-BLOCKED: native scope/unit/reset/value states |
| CTR-CAP-002 budget | M05 | M07/P01/P02/M08 export | EVIDENCE-BLOCKED: money/credit/limit/period semantics |
| CTR-CAP-003 capacity health | M05 | M07/P01/P02 | BLOCK: exact policy owner, state priority and constraining-window rules |
| CTR-CAP-004 observation recorded event | M05 | M07/M08 | BLOCK: dedupe/generation/event payload and durability |
| CTR-CAP-005 health changed event | M05 | M07/M08 | BLOCK: transition/recovery/order/event durability |
| CTR-CAP-006 history query | M05 | P01/P02/M08 export | BLOCK: time bounds/buckets/pagination/native-derived rules |
| CTR-CAP-007 forecast | M05 | M07/P01/P02 | BLOCK: union/uncertainty/invalidation; change event is missing |

### 5.8 Runtime observation

| Contract | Producer | Consumers | Decision and required resolution |
|---|---|---|---|
| CTR-RUN-001 process view | M06 | P01/P02/M08 export/M07 | EVIDENCE-BLOCKED: PID+start identity, units, safe cwd/state |
| CTR-RUN-002 session view | M06 | P01/P02/M08 export/M07 | EVIDENCE-BLOCKED: session/account/model/token/activity field availability |
| CTR-RUN-003 session tree | M06 | P01/P02 | BLOCK plus evidence: proven edges, cycles/orphans and aggregate usage |
| CTR-RUN-004 runtime state changed event | M06 | M07/M08 | BLOCK: definitive/inferred transition/recovery/durability |
| CTR-RUN-005 possible stall event | M06 | M07/M08 | BLOCK: progress evidence, waiting exclusions and recovery |
| CTR-RUN-006 process inspection port | M06 semantic owner; A04 implementations | A04 Linux/macOS implement; M06 consumes | BLOCK: register incorrectly names M06/A04 jointly as producer |
| CTR-RUN-007 session correlation decision | M06 | M02/P01/P02 | EVIDENCE-BLOCKED: proof/conflict/manual confirmation/invalidation |

### 5.9 Alerting

| Contract | Producer | Consumers | Decision and required resolution |
|---|---|---|---|
| CTR-ALERT-001 alert rule/resolution | M07 | P01/P02/M08 | BLOCK: fixed condition catalog, scope queries and default policy approval |
| CTR-ALERT-002 alert/history view | M07 | P01/P02/M08 export | BLOCK: evidence disclosure, coalescing and recovery dependencies |
| CTR-ALERT-003 alert opened event | M07 | M08/P01 hint/future delivery | BLOCK: common durable event contract absent |
| CTR-ALERT-004 alert state changed event | M07 | M08/P01/P02 hint/future delivery | BLOCK: transition/coalescing/delivery contract absent |
| CTR-ALERT-005 dashboard notification query | M07 | P01/P02 | BLOCK: ordering/count/read semantics need consumer approval |

### 5.10 Operations

| Contract | Producer | Consumers | Decision and required resolution |
|---|---|---|---|
| CTR-OPS-001 health view | M08 | P01/P02/service tooling | BLOCK: disclosure and aggregation precedence |
| CTR-OPS-002 readiness view | M08 | P01/DEP service manager | BLOCK: prevent readiness recursion and freeze degraded-vs-unready |
| CTR-OPS-003 backup view | M08 | P01/P02/operator | BLOCK: checksum/integrity/expiry/ref disclosure and GFS policy |
| CTR-OPS-004 diagnostic summary | M08 | P01/P02/export | BLOCK: strict field allowlist/config/version/error visibility |
| CTR-OPS-005 export job view | M08 | P01/P02 | BLOCK: module query ports, format/expiry/download authorization |
| CTR-OPS-006 component health port | M08 schema owner; each module produces | M08 aggregator and diagnostics | BLOCK: per-module implementations, timeout and safe unknown rules missing |

### 5.11 Transport, UI, persistence, deployment, and platform

| Contract | Producer | Consumers | Decision and required resolution |
|---|---|---|---|
| CTR-API-001 OpenAPI `/api/v1` | P01 | generated client/external clients | BLOCK: application-port inventory, field/problem/pagination/idempotency semantics |
| CTR-API-002 browser session/CSRF transport | P01 transport + M01 semantics | P02 shared client | BLOCK: cookie/origin/CSRF/session-expiry contract |
| CTR-API-003 bearer scheme | P01 transport + M01 semantics | Swagger/API clients | BLOCK: scope catalog, failure and one-time-token guidance |
| CTR-UI-001 generated TypeScript client | P01 schema + FND generator; integration sole writer | P02 | BLOCK: three roles are conflated; tool/output/wrapper/drift not approved |
| CTR-DB-002 repository/UoW family | each domain owns semantic ports; PLAN-DB implements | PLAN-DB plus owning domain | BLOCK: enumerate exact port packages/transactions/error mappings |
| CTR-DEP-001 native service lifecycle | PLAN-DEP | M08/operator/DB/A04 mappings | BLOCK: maintenance/quiescence/readiness/start modes and platform mapping |
| CTR-PLAT-001 platform primitives | portable semantic owner not assigned; A04 implementations | M06/M08/DB/DEP | BLOCK: Linux and macOS cannot each redefine one ID |

### 5.12 Family-level interface decision

| Interface family | Draft direction | CS-1 decision |
|---|---|---|
| COMMON/CONFIG | useful base conventions | BLOCK |
| FND | useful mechanisms | BLOCK |
| IAM | detailed semantic proposal | BLOCK |
| REG | detailed schema proposal | BLOCK + provider evidence |
| PROV | detailed protocol proposal | BLOCK + provider evidence |
| COL | detailed lifecycle proposal | BLOCK |
| CAP | detailed exact-value proposal | BLOCK + provider evidence |
| RUN | detailed runtime proposal | BLOCK + Linux/provider evidence |
| ALERT | detailed lifecycle proposal | BLOCK |
| OPS | detailed orchestration proposal | BLOCK |
| API/UI | detailed operation and workflow proposal | BLOCK |
| DB | detailed physical persistence proposal | BLOCK |
| DEP/PLAT | detailed boundary proposals | BLOCK + platform evidence |
| INT | detailed release proposal | BLOCK |

No registered interface is `Synchronized` or `Approved`. That is consistent with
the register, even where a producer plan is detailed enough for review.

## 6. Proposed contract gaps not in the register

IDs below are **provisional audit labels**, not allocations. The root steward
must accept, rename, split, or reject them and update producers/consumers
atomically.

| Provisional ID/name | Required producer | Required consumers | Why the current set is insufficient | Severity |
|---|---|---|---|---|
| CTR-COL-006 `CollectionOutcomeCommitPortV1` | M04 defines acknowledgement; M05/M06 implement typed commits | M04, M05, M06, P01 status | M04 must not write observation tables; plans already require an atomic receipt/ack seam | Critical |
| CTR-DB-003 `DatabaseSnapshotActivationV1` | PLAN-DB | M08/DEP/A04/M01 consistency flow | DB plan and INT consume it, but central register omits it | Critical |
| CTR-INT-001 `GateResultV1` | PLAN-INT/test steward | all automation/handoffs/release | INT proposal absent from register | Major |
| CTR-INT-002 `EvidenceReferenceV1` | PLAN-INT | every plan/AUTO-RELEASE | common sanitized locator/status semantics absent | Major |
| CTR-INT-003 `ContractBaselineV1` | PLAN-INT from producer approvals | composition/build/release | no machine-readable frozen contract set | Critical |
| CTR-INT-004 `ReleaseCandidateManifestV1` | PLAN-INT | DEP/operator/release | candidate identity/digests/targets need one schema | Major |
| CTR-INT-005 `AcceptanceEvidenceIndexV1` | PLAN-INT | owner/reviewer/release notes | release trace cannot be prose-only | Major |
| CTR-INT-006 `AutomationRoutineResultV1` | FND/PLAN-INT | CI/operators/handoffs | Passed/Failed/Blocked/Not Run needs one executable result format | Critical |
| CTR-EVT-001 durable event delivery/receipt/replay | integration technical owner with DB implementation | M02–M08 event producers/consumers | COMMON-006 defines envelope, not atomic outbox, acknowledgement, checkpoint, replay or retention | Critical |
| CTR-BOUNDARY-001 safe subprocess execution | FND/platform semantic owner | A01/A02/A03/A04/DEP | every CLI plan needs deadlines/output bounds/redaction/cancel without duplicating wrappers | Critical |
| CTR-BOUNDARY-002 safe provider HTTP execution | M03/FND boundary owner | A01/A02/A03 | network timeout/pagination/rate/TLS/redirect/body/redaction semantics are duplicated | Critical |
| CTR-BOUNDARY-003 approved root/file read | portable platform semantic owner | adapters/M06/M08/DB/DEP | allowlisted roots, symlink/race/size/atime outcomes need one port family | Critical |
| CTR-REG-008 reauthentication request/workflow | M02 application coordinator, using M03 flow protocol | P01/P02/M03/adapters/M07 auth bridge | P01 already defines routes with an explicit sync gap | Critical |
| CTR-REG-009 alert scope/current-subject query | M02 | M07 | REG views do not supply bounded re-evaluation and precedence inputs safely | Major |
| CTR-COL-007 collector health changed/current alert inputs | M04 | M07/M08 | COL-004 plus later completion cannot prove freshness recovery | Critical |
| CTR-CAP-008 forecast changed | M05 | M07/M08 | CAP-007 is query-only; alert activation/recovery needs generation ordering | Critical |
| CTR-CAP-009 capacity availability changed | M05 | M07/M08 | Unknown cannot be reinterpreted as provider unavailable/auth recovery | Critical |
| CTR-REG-010 authentication health changed | M02 recommended after M03 observation reconciliation | M04/M05/M07/M08/P01 | no domain event converts PROV-006 into durable account/profile auth truth | Critical |
| CTR-COMMON-007 field availability/state | FND technical schema, domain-owned mappings | M03–M08/P01/P02 | missing/null/unknown/unsupported/unavailable/not-applicable/withheld/stale/zero are not centrally mapped | Major |
| CTR-APP-001 dashboard overview/application projection | one application owner selected by root, recommended M08 aggregation layer without domain truth | P01/P02 | global command view otherwise forces P01 or P02 to invent cross-domain aggregation | Major |
| CTR-OPS-007 retention/export/consistency participant family | M08 protocol; each M01–M07 implements | M08/DB | M08 may not query module tables, and required module ports are not registered | Critical |

If root declines a shared boundary contract, each adapter may own a private
implementation, but every plan must still consume one approved semantic policy
and the duplication/security review must be explicit. Shared infrastructure
must never become a domain-import shortcut.

## 7. Actual contradictions requiring root resolution

These are present-document contradictions or incompatible claims, not facts that
must wait for M0.

| Finding | Severity | Contradiction | Exact root resolution |
|---|---|---|---|
| CAA-C01 gate order | Critical | The planning program/SDLC requires CS-4/full plan readiness before implementation; PLAN-INT's DAG starts W0/W1 after CS-1 and calls CS-4 a late evidence gate after W7 | Establish one full-plan synchronization/approval gate before W0. Rename later CS gates as implementation integration checkpoints; they may not retroactively authorize earlier work |
| CAA-C02 provider vs dashboard auth code | Critical | M01/P02 use `authentication_required` for dashboard credential expiry, while M03/M04/M05/M06 and API standards use it for provider auth | Reserve `dashboard_authentication_required` for HTTP 401/session recovery and `provider_reauthentication_required` for provider state. Map distinct HTTP statuses and UI flows; never clear dashboard session for provider failure |
| CAA-C03 auth spelling | Major | requirements say `re-authentication required`; M03/A01/A03 use `reauthorization_required`; collection outcome uses `authentication_required` | Freeze canonical normalized state `reauthentication_required`; retain operation-specific provider outcome only with explicit mapping. Version any changed enum |
| CAA-C04 one-time-secret retry | Critical | P01 says same key/request returns original representation; M01 forbids replay of token plaintext and returns a safe 409 | Add operation `replay_policy`: normal replay-safe representation versus `one_time_secret_non_replayable`. P01 returns 409 plus safe resource metadata; no secret is cached |
| CAA-C05 RUN-006 producer | Major | register lists M06/A04 as joint producer, but module rules require one semantic producer | M06 owns `ProcessInspectionPortV1`; A04 Linux/macOS implement it. A04 can propose extensions only through M06 review |
| CAA-C06 PLAT-001 producer | Major | Linux and macOS plans both publish differently named platform families under one ID | Assign a platform-neutral semantic owner; make Linux/macOS implementations or versioned extensions. One ID cannot mean `linux-platform.v1` and `macos-platform.v1` independently |
| CAA-C07 OpenAPI/client ownership | Major | FND, P01 and integration are all described as generator owners; UI contract lists P01/FND | P01 owns API semantics/source schemas, FND owns generator mechanism, integration steward is sole generated-artifact writer per wave, P02 owns wrapper consumption |
| CAA-C08 DB vs release activation wording | Critical | DB owns prepared DB activation; DEP owns artifact/unit activation and quiescence; INT says DEP owns “activation” without distinguishing them | Name three phases: DEP artifact/unit activation, PLAN-DB database activation, M08 restore/workflow authority. Every receipt and rollback target must be typed separately |
| CAA-C09 maintenance ownership | Critical | M08 proposes operations maintenance while DEP publishes deployment maintenance; each can stop work | M08 owns application maintenance intent/state; DEP owns fenced service quiescence execution/receipt. No independent competing state machines |
| CAA-C10 readiness recursion | Critical | M08 aggregates readiness, DEP status may consume it, and M08 consumes DEP/platform health | M08 readiness consumes a narrow non-composite service-state receipt. DEP composite status may consume M08 readiness, never vice versa. Liveness remains cycle-free |
| CAA-C11 normalized health thresholds | Major | M05 says health-policy owner is unresolved with M07; M07 explicitly rejects supplying M05 policy while consuming M05 | Freeze separate policies: M05 owns normalized capacity-health classification; M07 owns 30%/15% alert activation and precedence. M07 never feeds M05 |
| CAA-C12 API provider consumption | Major | P01 claims broad PROV consumption, but it must never invoke providers or orchestrate reauth | Restrict P01 to provider capability/compatibility query ports and REG-008 application workflow. It must not consume invocation gateway/adapter internals |
| CAA-C13 performance object | Major | requirements require 100 registered accounts and 200 simultaneous processes; INT refers to “100 records” in places | Use exact NFR-PERF-001 subjects everywhere. No seeded accounts/processes; absent real scale remains Blocked or requirement must be formally changed |
| CAA-C14 persistence paths | Moderate | domain plans propose `adapters/persistence/<module>/**`; DB standardizes `adapters/persistence/<module>/sqlite/**` | Adopt the DB adapter path across every plan and make import-boundary tests enforce it |
| CAA-C15 contract package layout | Moderate | most plans use contract files while M06 proposes `contracts/runtime_observation/v1/` package layout | Freeze one package/file convention in CTR-FND-001 before parallel scaffolding |
| CAA-C16 provider extension paths | Moderate | adapter plans use inconsistent extension documentation/package locations | Adopt one producer-owned pattern, e.g. `contracts/providers/<provider>/<capability>/v1`, with M03 governance and no core provider imports |
| CAA-C17 API lane ownership | Major | A01/A02 phrase Anthropic/OpenAI budget lanes as “if assigned” although V1 requires all three API providers | Assign Anthropic to A01, OpenAI to A02, and supported Ollama API to A03 now. M0 decides capability state, not ownership |

### 7.1 Currentness defects

These do not redefine behavior but must not be used as current synchronization
evidence:

- CS-0 reviewed only M0/FND/M01/control artifacts. It is historical P0 evidence,
  not a review of the present 20-plan set.
- CS-0 reports 49 FND and 73 M01 scenario IDs; the current files contain 52 and
  76 under the canonical parser. The historical counts must not be copied into
  CS-1.
- The planning register is now current and links all 20 artifacts. Earlier gate
  output showing missing links was overtaken by that update and is not a current
  finding.
- The contract register remains version `0.1.0` and does not reflect COL-006,
  DB-003, INT-001..006, or the M07 gap interfaces. It therefore cannot yet serve
  as the CS-1 frozen baseline.

## 8. Evidence-gated uncertainties, not contradictions

The following must remain Unknown/Blocked until real M0 or live evidence. Root
may freeze the containing typed union and safe failure behavior, but must not
claim support:

| Evidence question | Affected plans/contracts | Required real decision |
|---|---|---|
| Claude observable subscription windows, identity/profile isolation, CLI/file/API shapes and auth flow | M0/A01, REG/PROV/CAP/RUN | Supported/Experimental/Deferred/Unsupported per installed version, plan and account |
| Codex subscription windows, session files/CLI, `/logout`/restart login isolation and OpenAI billing roles | M0/A02 | same capability matrix and safe profile result |
| Ollama local versus cloud identities, subscription/API relationship, daemon/session/model metadata and auth need | M0/A03 | explicit resource taxonomy and source priority |
| Anthropic/OpenAI/Ollama API usage, cost, credits, budget, currency, pagination, rate and credential role | M0/A01-A03/M05 | exact official source, unit/scope/period/precision and permissions |
| Linux process identity, CPU/memory/state units, PID reuse, ancestry, cwd permissions, safe file roots and systemd behavior | M0/A04-LINUX/M06/DEP | supported source and typed field/error outcomes |
| macOS process/file/launchd behavior | A04-MAC | real supported Mac evidence; Linux cannot substitute |
| naturally occurring exhausted, provider-unavailable, auth-required, wrong-account and recovery states | adapters/M04-M07 | real observation or remain Blocked; never synthesize |
| provider request/rate/cost budgets | M03/M04/adapters | evidence-scoped numeric limits or collection remains disabled/conservative |
| exact performance thresholds beyond 100 accounts/200 processes | INT/all | measure real environment before freezing numeric budgets |
| 365-day purge and 7/4/12 real operational horizon | M01/M03-M08 | pure policy can pass; real elapsed-time evidence remains Blocked until it exists |

No provider-dependent contract may move beyond Proposed merely because its
closed type has been drafted.

## 9. Semantic alignment decisions required

### 9.1 Null, missing, unknown, and field availability

The plans collectively use: absent, JSON `null`, missing, unknown, unsupported,
unavailable, not applicable, denied/withheld, stale, unresolved, zero, and
insufficient input. They are not interchangeable.

Root must freeze a field-state algebra or explicit per-family mappings with these
minimum rules:

- absent means the contract version does not supply a field, never zero;
- `null` is allowed only where the schema documents a semantic empty/unknown
  value and accompanying state/precision explains it;
- `unsupported` means approved evidence says the capability is not supported;
- `unavailable` means a supported source cannot currently yield the value;
- `unknown` means truth cannot be established;
- `withheld`/permission denied must not be collapsed into missing;
- `stale` preserves the last observation as history but not current truth;
- zero is a real exact value and never a fallback; and
- `not_applicable` is not `unsupported`.

M02's null organization means the approved `Ungrouped` state and must not be
reused as unknown identity. P01 OpenAPI required/nullability and P02 presentation
states must be generated from the same mapping.

### 9.2 Units, ratios, and money

- Freeze one `ExactQuantityV1` representation: coefficient plus scale and unit,
  or exact decimal string, with canonical formatting, sign/range and comparison.
- Money needs currency plus integer minor units only when the verified currency
  exponent is known; otherwise use an exact decimal representation.
- Pick one canonical ratio form for storage/API. Plans currently allow decimal
  strings or basis points. Alert thresholds are explicitly basis points; any
  conversion must be exact and versioned.
- CPU utilization, context usage, quota remaining, credit and token quantities
  require distinct unit codes; a generic percentage must not erase denominator
  or interval semantics.
- `available_spend` is emitted only when a synchronized equation and all exact
  inputs exist; otherwise it is Unknown/Unsupported, never inferred from labels.

### 9.3 Time

Architecture permits explicit `Z` or offset; P01 and DB propose canonical `Z`,
and DB proposes fixed microsecond precision. Freeze:

- aware UTC internally;
- one canonical API spelling and precision;
- one fixed persistence spelling/precision;
- comparison/truncation/rounding rules;
- reset `exact | estimated | unknown` precision; and
- monotonic elapsed measurement separate from wall timestamps.

Generated JavaScript clients must retain timestamp strings where microsecond
identity/order matters; `Date` conversion cannot silently lose precision.
Durations are integer milliseconds by default. Configuration fields expressed
in seconds must include `_seconds` and must not be passed as the common duration
type without explicit conversion.

### 9.4 Authentication and authorization

Use three separate concepts:

1. dashboard principal authentication (`dashboard_authentication_required`);
2. provider/profile authentication health
   (`provider_reauthentication_required`, `revoked_or_disabled`, etc.); and
3. account identity mismatch (`wrong_account_detected`) mapped explicitly to
   M02's identity-decision state.

M02 should own durable reauthentication request/workflow identity and preservation
of account history; M03 owns the provider flow protocol; the adapter executes the
official flow against an AgentMonitor-managed profile; P01 maps transport; M04
only blocks/resumes collection from approved state. This keeps reauth out of the
API and scheduler and preserves default-profile protection.

Every API operation must map to exactly one M01 permission plus bearer scope
rules. Single-user deployment does not remove authorization.

### 9.5 Idempotency and optimistic concurrency

Freeze a common command envelope with operation ID, principal/authority,
idempotency key digest scope, canonical request fingerprint, expected resource
version when applicable, and replay policy. Distinguish:

- safe query repeat;
- replayable command result;
- terminal idempotent transition;
- one-time-secret non-replayable success; and
- long-running job join/status behavior.

`ETag`/`If-Match` is P01 transport for a domain expected version; P01 must not
strip or reinterpret the version without passing it through the approved port.
Each operation must state receipt retention. A universal 365-day idempotency
retention is neither required nor desirable; M01 currently proposes 24 hours.

### 9.6 Events and recovery

COMMON-006 is only an envelope. CS-1 must also freeze:

- producer-owned event semantics and aggregate sequence;
- atomic domain change plus producer-owned outbox record;
- shared dispatcher implementation without cross-module table writes;
- consumer-owned receipt/checkpoint and deduplication;
- incompatible-major rejection;
- per-stream order and stale generation behavior;
- restart/replay, backlog and poison-event behavior;
- retention rules for event, outbox, receipt and evidence references; and
- health/readiness impact without blocking producer commits.

M07 cannot infer recovery from a later successful collection or missing event.
It needs explicit newer recovery/current-state evidence from each source.

### 9.7 Retention and backup

FR-HIST-001 fixes one year for operational history. CS-1 must enumerate each
table/object class and distinguish:

- immutable operational history subject to 365-day purge;
- active/current projections retained while active;
- idempotency receipts retained for replay windows;
- pending jobs/outbox/checkpoints retained until terminal and safely aged;
- security audit and compatibility records;
- export/diagnostic artifacts with shorter expiry;
- backup catalog rows versus backup files; and
- recovery-held/preserved-current databases exempt from ordinary rotation.

The GFS proposal means the union of newest valid backups for 7 UTC dates, 4 ISO
weeks and 12 UTC months, not necessarily 23 files. Freeze schedule timezone,
slot boundaries, validity, retirement grace and failed-slot behavior.

## 10. Circular dependency and workflow risks

| Cycle/risk | Current path | Required acyclic form | Severity |
|---|---|---|---|
| Capacity health/alert policy | M05 may consume M07 thresholds; M07 consumes M05 | M05 owns normalized health; M07 consumes values/health and owns alert thresholds | Critical |
| Readiness/service status | M08 readiness ↔ DEP composite status | A04/DEP emit narrow service facts → M08 readiness; DEP may display M08 result | Critical |
| Reauth coordination | M02/M03/M04/P01 each imply coordination | P01 → M02 workflow → M03 protocol → adapter; events back to M02/M04/M07 | Critical |
| Restore/maintenance | M08 and DEP both enter maintenance; DB activates | M08 authority → DEP quiescence receipt → DB activation → DEP restricted start → M08 validation | Critical |
| Event delivery | producers may depend on central dispatcher that depends on producer state | producer commits outbox without dispatcher availability; dispatcher and consumer receipts are infrastructure adapters | Major |
| Operations health | every module produces OPS-006 while M08 health could be consumed during module startup | component health queries are bounded leaf ports; M08 aggregation never enters module business initialization | Major |
| API aggregation | P01 may query many domains and accidentally orchestrate | one approved application projection or documented read-only fan-out with no business decisions/transaction coupling | Major |
| Registry/runtime correlation | M02 identity decision and M06 session correlation reference each other | M02 owns account/profile identity evidence; M06 owns session association and references immutable M02 decisions | Major |

## 11. Duplicated and missing ownership

### 11.1 Duplicated/ambiguous ownership

| Surface | Current owners | Resolution |
|---|---|---|
| observation provenance | FND + M03, with M04/M05/M06 additions | FND owns technical primitive; M03 owns provider observation facts; domain owner owns derivation/freshness policy |
| OpenAPI/generated client | FND/P01/integration | split semantics/mechanism/sole writer as CAA-C07 |
| process inspection contract | M06/A04 | M06 semantic producer; A04 implementation |
| platform primitive contract | A04 Linux/A04 Mac | portable semantic owner; platform implementations/extensions |
| repository ports | domain modules/DB | domain semantic producer; DB implementation, mapping and physical policy |
| component health | M08/every module | M08 owns schema/aggregation; each module implements a leaf producer |
| maintenance | M08/DEP | M08 intent; DEP execution/quiescence receipt |
| database activation | DB/M08/DEP/A04 | M08 authority/workflow; DB validity/prepared activation; A04 primitive; DEP quiescence/service phases |
| product/security audit | M08/M01 | M01 IAM security events only; M08 product operation audit; typed forwarding rather than shared tables |
| retention | each module/M08 | module owns eligibility/purge port; M08 schedules and audits; DB supplies transactions only |

### 11.2 Missing consumers or producer ports

- The register omits P01/P02 as indirect safe consumers of provider auth health.
- M08 needs a named health, consistency, retention-preview/purge and export-query
  port from every M01–M07 module; only some plans name them.
- M07 needs the six gap families in section 6 before it can evaluate and recover
  all FR-ALERT-003 conditions.
- P01 needs an approved application port for each operation in its route matrix.
  A schema name in P01 is not proof the producing module publishes the port.
- P02 global command view needs a cross-domain overview projection or an approved
  bounded composition; it cannot join client-side domain truth.
- DEP/DB need narrow module consistency validators for restricted post-migration
  and post-restore startup; operations cannot read private tables.
- M04 needs M05/M06 commit receipts before marking a provider outcome durably
  consumed.
- Adapters need safe subprocess/network/file/profile-reference/deadline ports;
  prose security rules are not executable boundaries.

## 12. Data, migration, configuration, and artifact collisions

### 12.1 Tables and migrations

The proposed linear revision allocation is coherent and preserves one owner per
business table prefix:

```text
v1_0000 FND
v1_0100 M01
v1_0200..0204 M02
v1_0300 M03
v1_0400 M04
v1_0500..0504 M05
v1_0600..0603 M06
v1_0700..0702 M07
v1_0800..0804 M08
```

It is still blocked because conditional outbox tables and the common delivery
implementation are unresolved. Reservations must not become empty migrations.
One migration steward must serialize catalog, head and revision-file writes.
No implementation lane may renumber, split, merge or create a competing head.

Potential collisions requiring a frozen allocation:

- module-owned outbox tables versus a shared event journal;
- M03 compatibility records versus M02 installation ownership;
- M04 delivery/commit receipt versus M05/M06 ingest receipts;
- M08 health snapshots versus module-owned health history;
- IAM security audit versus M08 product audit; and
- restore journals outside the active DB versus deployment journals.

### 12.2 Configuration

All plans correctly defer exact keys to CONFIG-001, but this means parallel
implementation cannot start. Root must produce a machine-readable registry with
key, semantic owner, type/unit, bounds/default, secret class, source/precedence,
reload behavior, diagnostics exposure and consumers. Colliding concepts include:

- active/idle collection cadence and jitter;
- provider request/rate/cost budgets and concurrency;
- capacity-health versus alert threshold values;
- stall threshold and activity freshness;
- retention batch/window values;
- session/token/idempotency expiry;
- DB busy timeout/pool/checkpoint policy;
- backup time/slots/grace;
- bind/host/origin/port; and
- filesystem/data/config/runtime roots.

Secrets belong in `.env` only when AgentMonitor manages them. Provider OAuth
credentials remain provider-managed references and must not be moved into
`.env`.

### 12.3 Shared and generated files

The following require exactly one allocated writer per wave:

- root dependency manifests and lockfiles;
- composition root/router registry;
- central contract package indices;
- configuration registry;
- migration catalog, head and Alembic environment;
- OpenAPI artifact and compatibility baseline;
- generated TypeScript client;
- build/version manifest, SBOM and notices;
- command/automation registry;
- CI configuration;
- planning/contract registry, traceability, risk and ADR indexes; and
- shared frontend application shell, route map and design tokens.

The sole-writer allocation must be executable input to start-sync, not a prose
promise. Generated outputs are never hand-edited.

### 12.4 Import and path collisions

- Freeze `backend/src/agentmonitor/modules/<module>/{domain,application,contracts}`
  and `backend/src/agentmonitor/adapters/persistence/<module>/sqlite/` or another
  single equivalent before scaffolding.
- Cross-module imports may target only the producer's published contract
  package. A global contract index may re-export stable DTOs but may not transfer
  ownership.
- Provider extensions live only under their adapter-owned namespace and are
  governed by M03. Domain code must not import provider packages.
- P01 imports application contracts, never repositories/ORM/provider/platform
  code. P02 imports only the generated-client wrapper.
- Composition is the only place allowed to wire implementations to outbound
  ports; it owns no business rule.

## 13. Parallel-lane conflict audit

| Lane | Safe independent scope after freeze | Must serialize/block |
|---|---|---|
| Domain M01–M08 | module-private pure policy and application contracts | any shared contract change, event protocol, repository path or config registry |
| Persistence | one module's DB implementation after port/revision allocation | migration catalog/head, shared Alembic env, outbox architecture, DB-003 |
| Provider adapter A01/A02/A03 | adapter-private mapper/source code after M0 and M03 DTO freeze | safe network/subprocess wrappers, shared provider registry, same live account/profile |
| Platform A04 | OS-private implementation after portable port freeze | CTR-PLAT/RUN-006/DEP semantics, shared native wrapper, same service/process evidence |
| P01 transport | route mapping after application port and permission freeze | OpenAPI generation, global problem/auth/idempotency semantics |
| P02 feature | feature-private UI after operation/client generation | generated client, shared shell/routes/tokens, API schema |
| Operations/deployment | M08 policy and DEP mechanics after receipts freeze | maintenance/readiness/activation, service target, backup/restore routines |
| Integration/quality | validators and evidence aggregation | cannot edit module semantics; shared artifacts use serial steward queue |

Start-sync must allocate exact paths, contract versions, migration slots, scenario
IDs, live aliases, commands and shared writers. Two agents must never use the
same provider account/profile or mutate the same real service/database during a
live scenario unless the approved scenario explicitly coordinates them.

## 14. Test and live-evidence collision audit

### 14.1 Valid evidence boundaries

- T1 may use constructed values only for pure deterministic policy/value
  behavior with no I/O.
- T2 uses a real file-backed SQLite database, production migrations and
  production repositories/use cases. No direct seeded telemetry rows.
- T3 uses a running FastAPI server over a real loopback socket.
- T4 uses the built UI in a real browser against the running API.
- T5 uses the real platform boundary; macOS remains Blocked without a Mac.
- T6 uses real provider/accounts and current installed versions.
- T7 uses the real native service/backup/restore/deployment boundary.

### 14.2 Collisions and false-credit risks

| Risk | Required control |
|---|---|
| constructed provider response mistaken for parser proof | Constructed typed domain DTOs may test pure mapping only. Provider file/CLI/API compatibility requires live T6; no stored provider payload fixture/recording |
| parser “sanitization” becomes replay fixture | Evidence may record allowlisted findings, not reusable raw/sanitized response bodies that simulate the provider |
| direct DB inserts used to create history/load | Create rows only through production use cases with real owner/module inputs; otherwise the acceptance item remains Blocked |
| empty UI claimed as full dashboard proof | Empty state can pass its own scenario; populated global/provider/capacity/runtime claims require real production paths |
| Linux result credited to macOS | Keep MAC scenarios Blocked; portable pure policies do not prove platform behavior |
| 100/200 scale invented | Use real registered accounts/processes, or record Blocked/fail. AgentMonitor-owned metadata may measure internal catalog mechanics but not provider support |
| rare auth/exhaustion/recovery synthesized | Wait for natural condition or Blocked; do not alter owner provider state solely to manufacture it without separate authority |
| long-horizon retention/backup backdated | Pure cutoff/slot policy may use constructed instants; deletion/rotation claims require real DB/files and actual elapsed horizon |
| parallel live account interference | central live-test schedule and alias reservation; one operator/checkpoint per account/profile and side-effect budget |
| test suite hides Blocked/Not Run | INT-006 result schema and AUTO-TEST must report each boundary separately; aggregate zero cannot convert them to Passed |

No provider or platform live test has run during this audit. No unavailable
scenario may be promoted by documentation review.

## 15. Automation contract audit

### 15.1 Current executable scope

`AUTO-PLAN-CHECK` exists as `tools/planning/validate_plans.py` and has a real
repository test. At this snapshot it correctly fails because CS-1 is absent.
The current validator checks catalog count/uniqueness, artifact presence,
minimum lines, substring content markers, numbered headings, scenario-ID count,
registry link presence, routine names, synchronization-file presence/status and
plan-ID mentions.

It does **not** validate:

- contract-register completeness, status, version, producer or consumer match;
- duplicate semantic producers or missing consumer review;
- null/unknown/unit/time/auth/idempotency/event/retention semantics;
- requirement/acceptance primary ownership and full traceability;
- approval/DoR blockers or M0 evidence status;
- table/config/path/import/generated/shared-file ownership;
- migration order/head/outbox decisions;
- global scenario-ID uniqueness or test-boundary validity;
- dependency/license decisions;
- shared-writer/live-account allocations; or
- whether a CS-1 decision row is resolved rather than merely mentioned.

Therefore a future green result from the current implementation would prove a
structural documentation gate, not semantic synchronization. The validator's
literal `Status: **Complete**` plus plan-ID mention rule is insufficient for a
CS-1 claim.

### 15.2 Required automation resolution

1. Split or explicitly name stages:
   `draft-structure`, `contract-aligned`, `owner-approved`, and
   `implementation-ready`.
2. Add a machine-readable contract baseline containing every registered and
   accepted-new contract, version, one producer, consumers, status and decision
   reference.
3. Make `contract-aligned` fail on an absent producer/consumer, Concept status,
   unresolved decision, ambiguous ownership, unreviewed version or missing
   semantic checklist.
4. Add machine-readable ownership manifests for paths, imports, tables,
   migrations, config keys, generated artifacts, shared files, scenario IDs and
   live aliases.
5. Add negative tests for each fail-closed rule. Pure parser/policy tests may use
   constructed values; filesystem/repository claims must inspect the real
   checkout per project policy.
6. Make CS-1 completion depend on the semantic validator result, not on the
   string `Complete`.

The remaining mandatory routines are specified only in prose and remain Not
Ready: `AUTO-DOCS-CHECK`, `AUTO-TEST`, `AUTO-QUALITY`, `AUTO-GIT-PREFLIGHT`,
`AUTO-BUILD`, `AUTO-MIGRATE`, `AUTO-DEPLOY`, `AUTO-BACKUP`, `AUTO-RESTORE`, and
`AUTO-RELEASE`. Their dependent lifecycle claims remain blocked until real
fail-closed commands and tests exist.

## 16. Exact root synchronization sequence

Root should resolve in this order; later steps depend on earlier meanings.

1. **Repair lifecycle gates.** Make full plan/contract synchronization and owner
   approval precede all W0 production/test implementation. Reclassify later
   integration gates.
2. **Normalize the register.** Add all accepted gaps; assign exactly one
   semantic producer and enumerate every consumer. Bump the register version.
3. **Freeze common primitives.** IDs, timestamps/durations, exact quantities,
   field states, provenance, problems, command/idempotency envelope, events,
   configuration and schema compatibility.
4. **Freeze security distinctions.** Dashboard auth versus provider reauth,
   permission/scope matrix, reauth coordinator, protected-profile rules,
   one-time secret behavior and audit routing.
5. **Freeze durable workflow infrastructure.** COL-006, event/outbox/receipt,
   recovery events, current-state query ports and producer/consumer generation
   semantics.
6. **Remove cycles.** Approve separate M05 health/M07 alert policies; M08/DEP
   readiness; M08/DEP/DB restore/maintenance/activation; M02/M03 reauth.
7. **Freeze ownership manifests.** Paths/imports, persistence layout, tables,
   revision chain, config keys, shared/generated files and single writers.
8. **Freeze boundary ports.** Safe subprocess/network/files/root/profile refs,
   process inspection and platform-neutral implementations.
9. **Reconcile P01.** Map every operation to one application port, permission,
   auth mode, problem, idempotency/replay behavior, ETag/version and response
   schema. Remove broad provider invocation consumption.
10. **Reconcile P02.** Generate only from the frozen OpenAPI; map field/auth
    states and global overview without client-side domain inference.
11. **Allocate test/evidence.** Exact scenario owner, boundary, live aliases,
    owner checkpoint, command and Blocked rules; no cross-platform/provider
    substitution.
12. **Upgrade automation.** Implement the semantic planning validator and its
    negative tests, then run it against the real checkout.
13. **Run CS-1 producer/consumer review.** Record each contract version,
    semantic checklist, reviewer and resolution. Provider facts can remain
    evidence-blocked only where the contract safely expresses Unknown/
    Unsupported and implementation is correspondingly gated.
14. **Owner approval.** Approve exact plan and contract versions, dependency
    decisions and M0 execution authority separately. Do not infer approval from
    a structural gate.

## 17. CS-1 pass criteria derived from this audit

CS-1 may be recorded Complete only when all of the following are true:

- [ ] all 20 PLAN IDs have a current decision row and exact reviewed version;
- [ ] every registered/accepted-new CTR ID has exactly one semantic producer,
  all consumers, one version/status and an approved decision reference;
- [ ] every contract records null/unknown, units/time, auth, side effects,
  idempotency, events, retention, errors and compatibility where applicable;
- [ ] CAA-C01 through CAA-C17 have an accepted resolution reflected in every
  affected plan, register and governing document;
- [ ] M07's upstream signal/query gaps and COL-006/DB-003/INT contracts are
  registered or explicitly replaced;
- [ ] no M05↔M07, M08↔DEP, reauth, restore, event or API orchestration cycle
  remains;
- [ ] the table/migration/config/path/import/generated/shared-file ownership
  manifests have one writer per wave;
- [ ] provider/API/platform unknowns are linked to exact M0 scenarios and cannot
  be mistaken for Supported;
- [ ] test/live scenario ownership prevents account/profile/service/evidence
  collisions and preserves Blocked/Not Run;
- [ ] dependency candidates remain unapproved until their license,
  maintenance, security, necessity and transitive impact review passes;
- [ ] the semantic `AUTO-PLAN-CHECK` stage and its real-checkout tests pass;
- [ ] all remaining failed/blocked/not-run items are reported separately; and
- [ ] owner approval records identify the exact plan/register/contract baseline.

Until then, the correct overall result is:

```text
Cross-plan structural drafting: present
Cross-plan contract alignment: BLOCKED
Implementation authorization: none
M0/live/provider/platform evidence: Not Run or Blocked as recorded by each plan
```

