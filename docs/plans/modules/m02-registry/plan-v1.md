# Module plan: M02 — Registry

- Status: **Draft — M0 inputs and contract synchronization pending; implementation is not authorized**
- Plan version: 0.2.0-draft
- Proposed module contract: `registry.v1` (unapproved)
- Contract-register baseline: 0.2.0 Draft-aligned (`CTR-REG-001` through `CTR-REG-010`); not synchronized or approved
- Owner: M02 registry implementation role (unassigned)
- Required reviewers: owner, root/integration steward, M03 provider-system owner, M04 collection owner, M05 capacity owner, M06 runtime owner, M07 alert owner, M08 operations owner, P01 API owner, P02 UI owner, persistence/migration owner, security/privacy reviewer, test-integrity reviewer
- Requirements: FR-ORG-001..003; FR-ACC-001..006; registry-owned portions of FR-AUTH-002..006; FR-SAFE-001/002; supporting FR-HIST-005; NFR-ARCH-001/002, NFR-API-001/002, NFR-DATA-001, NFR-TEST-001/002, NFR-SEC-001, NFR-PRIV-001/002, NFR-DOC-001, NFR-LIC-001, NFR-PLAT-001, NFR-PERF-001, NFR-RES-001, NFR-OBS-001, NFR-COMP-001
- Acceptance criteria: AC-V1-001..008; AC-LIVE-001/002/003/004/006; AC-UI-002/003/004/005; AC-PROC-003/004; AC-OPS-003/004/005; AC-TEST-001..006
- Primary project risks: R-002, R-003, R-004, R-005, R-007, R-009, R-010, R-011, R-014, R-019, R-020, R-021, R-023, R-024
- Dependencies: accepted ADRs 0001, 0003, 0005, 0006, 0007, and 0008; approved foundation/common contracts; centrally allocated migration chain; M0 identity/resource/profile findings; synchronized M03 discovery/auth contracts; M01 authorization; persistence adapter; M08 backup/restore/retention orchestration
- Target milestones: M1 registry foundation, M2 first real Claude enrollment, M3–M6 remaining provider/account/resource enrollment
- Approved by/date: pending

This plan is governed by the [product requirements](../../../product/requirements.md), [V1 acceptance criteria](../../../product/v1-acceptance-criteria.md), [module boundaries](../../../architecture/modules.md), [contracts and versioning](../../../architecture/contracts-and-versioning.md), [data model](../../../architecture/data-model.md), [security architecture](../../../architecture/security.md), [testing strategy](../../../engineering/testing-strategy.md), [SDLC](../../../engineering/sdlc.md), and [M0 execution plan](../../discovery/m0-execution-plan.md). Structural examples in this plan are proposed schemas, never live data or evidence.

## CS-1 Draft-alignment addendum

This `0.2.0-draft` revision adopts contract-baseline `0.2.0` and the parallel-ownership manifest as its concrete CS-1 review position. It remains Draft, unapproved, and blocked by the named M0 evidence; all scenarios remain `Not Run`.

- M02 is the sole semantic producer of CTR-REG-008 `ReauthenticationRequestWorkflowV1`, CTR-REG-009 `AlertScopeAndSubjectQueryV1`, and CTR-REG-010 `AuthenticationHealthChangedV1`, in addition to CTR-REG-001..007.
- CTR-REG-008 is the durable reauthentication coordinator. P01 may start/get/cancel only this M02 workflow; M02 validates the account/profile and protected-default preconditions, preserves stable identity/history, delegates the provider operation through M03 CTR-PROV-007, persists progress/idempotency/restart truth, reconciles the sanitized post-flow identity, and emits the resulting state. M02 never receives a credential, OTP, MFA value, browser cookie, token, or raw provider response.
- The normalized provider state carried by CTR-REG-010 is exactly `reauthentication_required`. Adapter-native `reauthorization_required` or generic `authentication_required` values are mapped by M03/adapters before durable registry truth. CTR-REG-010 is distinct from dashboard `dashboard_authentication_required`; it cannot invalidate the dashboard principal. A wrong verified identity becomes `wrong_account_detected`, preserves the original account/profile relationship and history, and requires owner review.
- CTR-REG-009 supplies M07 with a bounded current scope/subject snapshot, including registry revision, lifecycle, provider/account/organization chain, eligible resources, and explicit incomplete/unavailable state. M07 never reads registry tables or infers membership from labels.
- All M02 events use CTR-COMMON-006 plus CTR-EVT-001 atomic outbox/receipt/replay rules. All provider-derived optional fields use CTR-COMMON-007; exact zero, unknown, unavailable, unsupported, withheld, stale, and not-applicable remain distinct. M02 implements M08-owned CTR-OPS-006 and CTR-OPS-007 participant ports without transferring registry ownership.
- M02 adopts CTR-EVT-TOPOLOGY-001: it owns `reg_event_outbox` and the atomic producer append; consumers own their receipts/checkpoints. PLAN-DB's shared dispatcher reaches M02 rows only through the published M02 event-storage port. There is no central event table or cross-module SQL.
- The V1 public contract file is `backend/src/agentmonitor/contracts/registry_v1.py`; SQLite implementation files are only under `backend/src/agentmonitor/adapters/persistence/registry/sqlite/**`. M02 owns `reg_*` tables and `v1_0200..v1_0299`; PLAN-DB serializes the shared migration head.
- Alignment is verified by existing scenarios M02-PURE-021..023, M02-DB-023/024, M02-HTTP-010, M02-BROWSER-006, M02-LIVE-007..010, M02-SYNC-001..025, M02-ARCH-001..005, and M02-OPS-001..005. These remain `Not Run`; live cases require owner-controlled real profiles and cannot be simulated.

## Planning gate and evidence dependency

This is a complete implementation design for the stable registry responsibilities. It is intentionally not implementation-ready until M0 supplies the provider-specific facts listed below and contract synchronization approves them. The implementation agent may build generic state machines only after approval; it may not fill an M0 gap with a guessed provider identifier, profile layout, resource type, or correlation rule.

Required M0 handoff inputs are:

- provider-scoped stable identity candidates, their scope, lifetime, reuse behavior, sensitivity classification, and evidence strength;
- account/profile/resource multiplicity for each observed product and credential role;
- safe installation identity and version evidence;
- default-profile detection and protection evidence;
- nullable, unavailable, prohibited, or owner-confirmed identity fields;
- explicit results for M0-CLA-007..009, M0-CDX-007..009, M0-OLL-003/007..009, M0-ANT-002, M0-OAI-002/006, M0-OAPI-002, and M0-LNX-007..008;
- separate approval and evidence for any later profile-isolation or re-authentication experiment.

Until those inputs exist, provider-derived fields use `unknown` or remain unassociated. `Unsupported` may be recorded only after the scoped M0 capability decision supports that conclusion. No provider-specific identity, path, or resource semantics in this plan are asserted as fact.

## 1. Outcome and boundaries

### Outcome

M02 gives every organization, provider installation, provider account, monitoring profile, and independently constrained resource a durable AgentMonitor identity while preserving uncertainty and history. It is the authoritative directory for grouping and for evidence-backed relationships; it is not a telemetry collector.

The outcome is measurable when:

- organizations can be created, renamed, explicitly ordered, and archived without silently moving or deleting accounts;
- every registered account has an immutable internal ID and mutable friendly name, primary organization or explicit Ungrouped state, lifecycle, and monitoring setting;
- renames, organization moves, monitoring changes, identity decisions, profile changes, resource changes, and archive/restore operations retain auditable history;
- subscription, API, project/workspace, local-runtime, profile, and provider identity concepts are not collapsed into one record;
- auto-discovery stages safe candidates and never guesses an account association;
- an owner can explicitly confirm a safe ambiguous identity relationship, with the confirmation distinguished from provider verification;
- conflicting evidence blocks automatic reassociation and produces a truthful conflict decision;
- default provider profiles are protected before any mutation-capable auth flow can begin;
- successful re-authentication updates the existing profile/account relationship and preserves account ID, name, group, resources, configuration references, history, and downstream subject IDs;
- consumers resolve organization/account/resource scope through versioned query contracts and never read `reg_*` tables;
- real SQLite, real service/API, real built-browser, and owner-coordinated real-provider scenarios verify the relevant boundary without mocks, fakes, recordings, seeded telemetry, or invented accounts.

### In scope

- Organization/group identity, display metadata, explicit ordering, lifecycle, and Ungrouped semantics.
- Provider definitions admitted from synchronized M03 manifests and installed-provider instances admitted from sanitized discovery outcomes.
- Account internal identity, provider association, friendly name, lifecycle, monitoring intent, primary organization membership, and change history.
- Versioned non-secret account-configuration references owned by an explicitly registered module/adapter namespace; M02 stores references, never another module's configuration values.
- Safe provider identity claims and evidence, including provider-verified, owner-confirmed, unresolved, conflicting, invalidated, and unknown decisions.
- Staged discovery candidates that require review before association.
- Monitoring profiles, purpose, opaque provider-owned locator/reference, protected-default flag, lifecycle, and last identity-verification decision.
- Account resources and parent relationships needed to distinguish subscription, API organization/project, workspace, and other independently constrained pools.
- Registry scope snapshots and change events for downstream aggregation, invalidation, scheduling, alerting, and diagnostics.
- Registry-owned tables, migrations, repositories, optimistic concurrency, idempotency receipts, and history retention.
- Registry application ports for CRUD-like metadata actions, discovery reconciliation, identity confirmation, profile-safety checks, and re-authentication result reconciliation.
- Safe registry health/consistency summary for M08.

### Out of scope

- Collecting quota, budget, spend, token, process, session, or runtime data.
- Computing capacity or account health from usage, budget, authentication, session, or process telemetry.
- Provider protocol ownership, capability negotiation, provider-specific parsing, network/CLI/filesystem access, or direct adapter invocation.
- Provider passwords, OAuth tokens, API keys, browser cookies, email OTP, MFA, recovery codes, credential-file contents, or any credential copy.
- Deciding whether a provider source is supported, authoritative, experimental, or compatible. M03 owns those decisions from M0 evidence.
- Runtime session-to-account evidence collection and the `SessionCorrelationDecisionV1` state machine. M06 owns runtime evidence and may consume registry identity decisions.
- Implementing a provider login UI/CLI or handling credentials. M02 owns the durable reauthentication workflow and invokes the official, bounded M03/provider operation through CTR-PROV-007; M03/provider adapters own protocol execution while M02 owns authorization, progress, restart reconciliation, cancellation, and the verified registry result.
- Aggregating health, capacity, budgets, alerts, or sessions. Owning modules aggregate over an M02 scope snapshot.
- Deleting provider state, deleting historical accounts, switching a running agent, or controlling a process.
- Email, native notifications, remote/multi-user access, additional providers, content capture, and agent routing.

### Ownership

M02 owns:

- `Organization`, `ProviderDefinition`, `ProviderInstallation`, `Account`, `AccountConfigurationReference`, `ProviderIdentityClaim`, `DiscoveryCandidate`, `MonitoringProfile`, `AccountResource`, `RegistryChange`, and `RegistryCommandReceipt` concepts;
- all `reg_*` tables, constraints, indexes, repository ports, and centrally allocated M02 migration revisions;
- organization, account, installation, profile, identity, resource, and registry-revision invariants;
- safe registry field-state vocabulary and distinction between provider verification and owner confirmation;
- the proposed `registry.v1` contracts under `CTR-REG-001..010`;
- module-specific configuration declaration, which is intentionally empty for environment keys in V1 unless synchronization approves a real need;
- registry documentation, evidence matrix, migration notes, and operator troubleshooting guidance.

M02 does not own the common event envelope/dispatcher, global migration allocator, HTTP routes, generated client, provider credentials, adapter manifests, runtime correlation records, or consumer projections.

### Allowed paths for a future implementation agent

These paths are proposed and require root allocation before implementation:

```text
backend/src/agentmonitor/modules/registry/**
backend/src/agentmonitor/adapters/persistence/registry/sqlite/**
backend/tests/registry/**
backend/tests/integration/registry/**
docs/modules/registry.md
docs/test-evidence/registry/**                  # sanitized evidence only, if approved
```

Shared paths require explicit per-change ownership from the integration steward:

```text
backend/src/agentmonitor/contracts/registry_v1.py
backend/migrations/versions/<allocated-registry-revision>.py
backend/src/agentmonitor/composition/**
backend/tests/contract/**
OpenAPI/generated-client sources and generated artifacts
configuration registry, manifests, lockfiles, traceability, and runbooks
```

### Allowed dependencies and imports

- M02 domain/application code may import only approved standard-library primitives, `CTR-COMMON-001/002/006`, its own public/internal types, and explicit outbound port protocols.
- Application orchestration may consume synchronized `CTR-PROV-002`, `CTR-PROV-005`, `CTR-PROV-006`, and `CTR-PROV-007` DTOs without importing M03 implementation.
- Persistence adapters may import approved SQLAlchemy/Alembic packages and M02 repository/unit-of-work ports.
- Composition may wire M01 authorization, M03 outcomes, persistence, and event publication through published ports.
- P01, M04–M08, and adapters consume only published `registry.v1` contracts.

### Forbidden dependencies and imports

M02 domain/application code must not import FastAPI, Starlette, Pydantic transport models, SQLAlchemy, Alembic, provider SDKs/CLIs, OS/process/filesystem/network APIs, React/UI code, or another module's implementation. The implementation agent must not:

- query/write another module's tables or expose `reg_*` models;
- import provider/platform adapters or contain `if provider == ...` business branches;
- open provider files, resolve executable paths, call provider APIs, or read process environments;
- store or log raw discovery/provider responses, credential locators in display DTOs, personal email, full paths, or secret-bearing values;
- add a generic `utils`, shared provider model, shared repository, handwritten frontend DTO, or test-only endpoint;
- edit another module, `.env`, provider state, or operator data.

## 2. Requirements and traceability

| Requirement/AC | Planned registry behavior | Proposed contract | Test/scenario IDs | Evidence gate |
|---|---|---|---|---|
| FR-ORG-001 | Create, rename, reorder, archive, restore, and query durable organizations with optimistic concurrency | CTR-REG-001 | M02-PURE-001..004, M02-DB-001..006, M02-HTTP-001..003, M02-BROWSER-001 | Pure policy plus real SQLite/HTTP/browser |
| FR-ORG-002 | Each non-archived account has exactly one primary organization ID or explicit `null = ungrouped`; archived organizations reject new assignments | CTR-REG-001/002 | M02-PURE-005, M02-DB-007/008, M02-HTTP-004, M02-BROWSER-002 | Real database constraints and workflow |
| FR-ORG-003 | Publish consistent global/organization membership snapshots; M05/M06/M07 aggregate their own facts over those subjects | CTR-REG-001/002/005/007 | M02-PURE-006, M02-DB-009, M02-HTTP-005, M02-ARCH-001 | Contract and real query evidence; no telemetry aggregation claim |
| FR-ACC-001 | Register provider accounts using immutable opaque internal IDs independent of mutable external labels | CTR-REG-002/006 | M02-PURE-007/008, M02-DB-010/011, M02-LIVE-001..003 | Real DB plus owner-confirmed real accounts |
| FR-ACC-002 | Friendly name required; rename and group-move history append without changing account ID | CTR-REG-002/007 | M02-PURE-009, M02-DB-012/013, M02-HTTP-006, M02-BROWSER-003 | Real DB/API/browser |
| FR-ACC-003 | Monitoring enable/disable is reversible, versioned, and history-preserving; archive disables effective collection without deleting history | CTR-REG-002/007 | M02-PURE-010/011, M02-DB-014, M02-HTTP-007 | Pure lifecycle plus real database/API |
| FR-ACC-004 | Profiles, provider identities, resources, projects/workspaces, and subscription/API pools remain distinct linked records | CTR-REG-002/003/005 | M02-PURE-012..014, M02-DB-015..018, M02-LIVE-004 | Pure taxonomy plus real discovery/enrollment |
| FR-ACC-005 | Reconcile sanitized real discovery outcomes into installation/candidate records; never auto-enroll ambiguous identities | CTR-REG-004/006 consuming CTR-PROV-005 | M02-PURE-015/016, M02-DB-019/020, M02-HTTP-008, M02-LIVE-005 | M0-approved source and real provider discovery |
| FR-ACC-006 | Owner can confirm an ambiguous candidate; conflicts remain visible and automatic association never guesses | CTR-REG-006 | M02-PURE-017..020, M02-DB-021/022, M02-HTTP-009, M02-BROWSER-004/005, M02-LIVE-006 | Pure decision policy plus owner-coordinated real condition |
| FR-AUTH-002 | Authorize only an AgentMonitor-managed, non-protected target for an official adapter-owned auth flow | CTR-REG-003/006 consuming CTR-PROV-007 | M02-PURE-021/022, M02-DB-023, M02-HTTP-010, M02-BROWSER-006, M02-LIVE-007 | Contract test then separately approved live flow |
| FR-AUTH-003 | Re-auth result reconciles into the existing profile/account and preserves all durable registry relationships/history | CTR-REG-002/003/006/007 | M02-PURE-023, M02-DB-024, M02-LIVE-008 | Real transaction plus live provider re-auth |
| FR-AUTH-004 | Registry contracts accept no password, OTP, MFA, recovery code, or credential content | Entire registry.v1 surface | M02-ARCH-002, M02-SEC-001/002 | Schema/source/artifact review and secret scan |
| FR-AUTH-005 | Protected default profile rejects every mutation-capable auth preparation before adapter invocation | CTR-REG-003 | M02-PURE-021, M02-DB-023, M02-HTTP-010, M02-LIVE-009 | Pure/DB/HTTP plus live non-modification proof |
| FR-AUTH-006 | Profile isolation and safe stable identity remain capability-gated by scoped M0/live evidence | CTR-REG-003/006 consuming CTR-PROV-002/005/007 | M02-LIVE-005/007..010 | Required M0 and real-version evidence; otherwise Blocked |
| FR-HIST-005 | Every registry instant is UTC; rendering timezone belongs to P01/P02 | CTR-COMMON-002, all registry views/events | M02-PURE-024, M02-DB-025 | Pure time rules and real DB round trip |
| FR-SAFE-001 | Allow registry metadata/group/profile guidance mutations, manual confirmation, and explicit refresh-trigger association only | Registry command surface | M02-ARCH-003, M02-HTTP-001..010 | Contract/route absence and real API evidence |
| FR-SAFE-002 | No process-control, running-agent credential switching, provider logout, or routing command exists | Entire module surface | M02-ARCH-003/004, M02-SEC-003 | Import/API/schema/command absence review |
| NFR-ARCH-001/002 | Isolated module, owned tables, typed contracts, non-secret account configuration references, no private/circular imports | registry.v1 | M02-PURE-026, M02-DB-028, M02-ARCH-001..005 | Import-boundary and ownership checks |
| NFR-API-001/002 | P01 maps registry contracts under `/api/v1`; P02 consumes only the generated client | CTR-API-001, CTR-UI-001 consuming CTR-REG | M02-HTTP-012, M02-BROWSER-001..008 | Real HTTP/OpenAPI/generated-client/browser |
| NFR-DATA-001 | Real SQLite migrations/repositories preserve PostgreSQL-compatible domain semantics | CTR-DB-001/002 | M02-DB-001/026/027, M02-OPS-001 | Fresh/upgrade real file DB and portability review |
| NFR-TEST-001/002 | Meaningful R/G/R at real claimed boundaries; prohibited-double scan remains clean | Test/evidence contracts | Every M02 test ID; M02-SEC-004 | Evidence review and repository scan |
| NFR-SEC-001, NFR-PRIV-001/002 | Least privilege, opaque references, allowlisted fields, no secrets/content, no product telemetry | registry.v1 | M02-SEC-001..006, M02-LIVE-009 | Security/privacy review and real artifacts |
| NFR-DOC-001, NFR-COMP-001 | Module/contracts/migrations/runbooks/compatibility documented and versioned | CTR-REG-001..010 | M02-DOC-001..003, M02-ARCH-001 | Documentation/contract checks |
| NFR-LIC-001 | No M02-specific dependency without admission; release inventories remain current | Dependency gate | M02-DEP-001 | Lock/SBOM/notices review |
| NFR-PLAT-001 | Registry domain remains OS-neutral; provider/platform locators are opaque | CTR-REG-003/004 | M02-ARCH-004, M02-LIVE-005 | Boundary check; Linux live, macOS visibly Blocked if unavailable |
| NFR-PERF-001 | Indexed registry/query design supports 100 accounts without redesign; no invented provider accounts used as evidence | Query contracts | M02-OPS-002/003 | Real measured approved load; unresolved policy blocks claim |
| NFR-RES-001 | Malformed/failed discovery cannot corrupt current registry or prevent unrelated reads | ReconcileDiscoveryOutcomeV1 | M02-PURE-016, M02-DB-020, M02-HTTP-011, M02-OPS-004 | Real transaction/service failure isolation |
| NFR-OBS-001 | Structured events/logs use safe IDs/codes/correlation only | CTR-REG-007, CTR-FND-004 | M02-PURE-025, M02-SEC-005 | Log/event/diagnostic inspection |
| AC-V1-001..008 | Complete traceability, approved contracts/OpenAPI/migrations/security/docs, and no simulated claim | All | M02-DOC-001..003, M02-HTTP-012, M02-DB-026/027, M02-SEC-001..006 | Release review; planning is Not Run evidence |
| AC-LIVE-001/002/003 | Enroll or owner-document the exact intended Claude/Codex/Ollama account set | CTR-REG-002/003/005/006 | M02-LIVE-001..006 | Owner-coordinated real accounts; unavailable stays Blocked |
| AC-LIVE-004/006 | Registry/provider adapter contract and re-auth continuity pass against current real versions | CTR-REG-003/006 and CTR-PROV-005/007 | M02-LIVE-005/007..010 | Real provider/version matrix |
| AC-UI-002/003/004/005 | Real organizations/accounts/resources are visible; responsive/accessibility and empty/unknown/conflict/unsupported states are truthful | API mapping of CTR-REG views | M02-BROWSER-001..008 | Built UI, real backend, real registry data |
| AC-PROC-003/004 | Registry identity never causes M06 to guess; no content/secret fields cross correlation boundary | CTR-REG-006 with CTR-RUN-007 | M02-PURE-017..020, M02-SEC-001, M02-LIVE-006 | Contract/security/live evidence |
| AC-OPS-003/004/005 | Discovery failure isolation and real backup/restore/upgrade preserve registry | Registry health/query ports | M02-OPS-001/004/005 | Real application/database/operations |
| AC-TEST-001..006 | R/G/R, real boundaries, mutation quality, explicit Blocked/Not Run | Test evidence | Entire inventory | Independent test-integrity review |

### Proposed interpretations requiring synchronization

1. `organization_id = null` has exactly one meaning: Ungrouped. It never means unknown or unavailable.
2. Organization archival is explicit and non-destructive. It is rejected while any active account is assigned; moving accounts to Ungrouped is a separate visible operation.
3. Account archival is reversible in V1, preserves all history/relationships, and forces `effective_monitoring_enabled = false` without erasing the owner's stored monitoring preference.
4. Manual/owner confirmation is valid evidence but is never relabeled provider-verified.
5. No external identity field is sufficient for automatic association until M0 has approved its scope/stability and the current evidence is unique and non-conflicting.
6. Runtime session correlation remains owned by M06. M02 publishes identity facts/decisions and accepts owner confirmation of provider identity/account association, not arbitrary PID/session mappings.
7. Friendly names are proposed unique after Unicode normalization and case folding across non-archived accounts to prevent operator ambiguity. Archived names do not block reuse, and every event/query uses the opaque account ID. This requires owner approval.
8. Registry change history is retained for 365 days after occurrence; current entities and current identity/profile/resource links are not retention-purged. This requires M08 synchronization.

## 3. Domain design

### 3.1 Entities and aggregates

| Aggregate/entity | Identity and mutable state | Primary invariants |
|---|---|---|
| `Organization` | opaque ID; name/description; display order; active/archived; record version | Name valid; active order unique/deterministic; archived receives no new active accounts |
| `ProviderDefinition` | stable provider key; safe display name; lifecycle; admitted manifest reference | Created only from synchronized M03 provider registration; no adapter code or credentials |
| `ProviderInstallation` | opaque ID; provider key; installation fingerprint/reference; platform; reported version field-state; discovery state/times | No raw executable path in public view; identity semantics M0-approved; missing is not deleted |
| `Account` | opaque ID; provider key; friendly name; org/null; lifecycle; monitoring preference; record version | ID immutable; one provider; one org/null; rename/move never changes ID; archived is not effectively monitored |
| `AccountConfigurationReference` | account ID; approved owner namespace/kind; opaque non-secret reference ID; lifecycle/version | Contains no setting value/secret; owner namespace is registered; one current reference per account/owner/kind unless contract permits multiplicity |
| `ProviderIdentityClaim` | opaque claim ID; provider/scope; approved safe subject key/fingerprint; evidence class; state; account link; validity times | One current non-conflicting account association per scoped stable subject; evidence class preserved |
| `DiscoveryCandidate` | opaque ID; source outcome reference; candidate kind; safe fields; association state; first/last seen | Never becomes account/profile/resource association through heuristic or display-label equality |
| `MonitoringProfile` | opaque profile ID; account; purpose; opaque locator; protected-default; lifecycle; identity decision/version | Protected default can never enter mutation-capable auth target state; locator never public/logged |
| `AccountResource` | opaque resource ID; account; kind; optional parent; approved provider resource key; lifecycle | Same account as parent; no cycles; subscription/API pools stay distinct; unknown is not duplicate |
| `RegistryChange` | change ID; aggregate ID/version; kind; actor class/ID; UTC time; safe correlation/command ID; protected owner-facing prior/new metadata where required | Append-only and allowlisted; internal event/log projections omit mutable labels, locators, identities, and provider payloads |
| `RegistryCommandReceipt` | command/key digest; principal; operation; request fingerprint; outcome ID/version; created/expiry | Same key+same fingerprint replays safe outcome; different fingerprint is conflict; no secrets/raw request |

### 3.2 Organization and account lifecycle

```text
Organization
  active --archive (no active accounts)--> archived
  archived --restore (name/order conflict check)--> active

Account
  pending_identity --owner/provider confirmation--> active
  pending_identity --conflicting evidence--> identity_conflict
  active --conflicting identity evidence--> identity_conflict
  identity_conflict --explicit reviewed resolution--> active or pending_identity
  pending_identity/active/identity_conflict --archive--> archived
  archived --restore--> pending_identity, active, or identity_conflict according to retained identity state
```

- Hard deletion of organizations/accounts is not a V1 use case.
- An account's `monitoring_preference` is `enabled` or `disabled`; its effective state is disabled when archived, identity-conflicted, or lacking an eligible synchronized profile/resource. M04 receives both intent and eligibility reason.
- Restoring an account never silently enables collection. The retained preference and current eligibility are returned for an explicit owner decision.
- `pending_identity` accounts may be named/grouped but cannot be effectively monitored.
- A provider definition cannot be deleted while any installation/account exists; V1 uses lifecycle state.

### 3.3 Installation and discovery-candidate lifecycle

```text
Installation: discovered -> present -> missing -> present
                              |             |
                              +-----------> incompatible/unverified (M03 decision reference)

Candidate: discovered -> owner_review_required -> associated
                                     |-> dismissed
                                     |-> conflict
             stale <- not seen within synchronized source policy
```

M02 does not decide source freshness duration or compatibility. It receives the source result/state and timestamps from M03. Reconciliation is idempotent by an M0-approved stable installation/candidate identity. If no stable key is approved, the result is stored as an unassociated review candidate and never merged by path, email, or display name.

### 3.4 Profile safety and re-authentication

Profile lifecycle is `pending`, `active`, `disabled`, or `archived`; identity verification is an orthogonal state: `unknown`, `owner_confirmed`, `provider_verified`, `conflict`, `wrong_account`, `invalidated`, or `unavailable`.

Rules:

1. A discovered default profile is persisted with `protected_default_profile = true` before being exposed to any auth preparation port.
2. The protected flag may move from false to true when stronger evidence identifies a default profile. No automated path changes true to false. Correcting an erroneous protected flag requires a separately reviewed owner operation and evidence; the first V1 plan proposes no such public operation.
3. `PrepareProfileAuthenticationV1` rejects protected, archived, disabled, unresolved, wrong-account, and incompatible targets before returning an internal opaque locator handle.
4. M03/provider adapter starts the official flow. M02 never receives password, OTP, MFA, browser cookie, OAuth token, or provider response body.
5. `ReconcileProfileIdentityV1` receives only a sanitized verified identity outcome. Matching evidence updates verification/history on the existing profile/account in one transaction.
6. Mismatching evidence records `wrong_account`, keeps the prior account association and all history, blocks effective monitoring for that profile, and never rewrites the locator/account link.
7. Re-authentication success cannot create a second account for the same approved stable scoped identity. A conflict stops reconciliation for owner review.

### 3.5 Identity/correlation policy

Evidence classes are:

- `provider_verified`: a synchronized adapter reports a safe, scoped, M0-approved stable identity from a supported source;
- `owner_confirmed`: the authenticated owner deliberately associated a displayed candidate with an account;
- `corroborated`: multiple safe signals agree but none alone is provider-verified; this can request owner confirmation but cannot auto-associate unless M0 explicitly approves the combined rule;
- `weak`: label, path adjacency, process order, or other non-unique signal; never auto-associates;
- `conflicting`: safe signals disagree or a stable identity is already associated elsewhere;
- `unknown`/`unavailable`/`unsupported`: truthful scoped absence states.

`IdentityCorrelationDecisionV1` states are `matched`, `owner_confirmation_required`, `owner_confirmed`, `unresolved`, `conflict`, `wrong_account`, `invalidated`, `unsupported`, and `unknown`. Every non-unknown decision includes evidence-class codes and safe evidence references; it never contains raw provider values. `matched` is allowed only for an approved unique stable rule. `owner_confirmed` records actor, UTC time, candidate/account IDs, and the exact safe evidence set shown to the owner.

### 3.6 Resource taxonomy and hierarchy

The normalized resource kinds proposed for V1 are:

- `subscription_pool`;
- `api_organization`;
- `api_project`;
- `workspace`;
- `prepaid_credit_pool`;
- `local_runtime_pool`;
- `provider_specific`;
- `unknown`.

These are relationship categories, not assertions that any provider exposes them. M0 decides which are used per provider/account class. A `provider_specific` resource requires an allowlisted versioned kind code from the adapter contract. `unknown` is never merged with a known resource and is never treated as zero capacity.

Resource rules:

- a resource belongs to exactly one account;
- an optional parent belongs to the same account and cannot form a cycle;
- profile-to-resource access is many-to-many through an owned link, because one profile may access multiple resources and a resource may be visible through more than one managed profile;
- provider resource IDs remain separate from AgentMonitor resource IDs and never become primary keys;
- deduplication requires an M0-approved scoped provider key or explicit owner confirmation; matching labels are insufficient;
- resources retire rather than delete, preserving historical capacity subject IDs;
- M02 returns membership/reference data only. M05 owns limits, spend, capacity, and aggregation.

### 3.7 Unknown, null, empty, unsupported, and unavailable rules

- `null organization_id` means Ungrouped and only Ungrouped.
- `null parent_resource_id` means a root resource.
- A nullable provider-derived value is paired with `RegistryFieldStateV1`: `known`, `withheld`, `unknown`, `unsupported`, or `unavailable`. `known` requires a value; all other states require `value = null` and a safe reason code.
- `withheld` means the value exists but privacy/security policy intentionally prevents disclosure; it is not unknown.
- `unsupported` requires scoped discovery evidence. Lack of observation is `unknown` or `unavailable`, not unsupported.
- An empty list means the completed query found no records in the requested scope. Partial/unavailable queries return a typed non-success outcome, never a misleading empty list.
- Zero applies only to actual counts. Missing accounts/resources are never represented as zero usage or zero capacity.
- A timestamp is nullable only when the event has not occurred; its companion state explains this. Every stored instant is UTC.
- Public views never expose raw opaque profile locators, full provider identities, full paths, emails, or evidence payloads.

### 3.8 Ordering, identity, idempotency, and concurrency

- Internal IDs use `OpaqueIdV1`; clients do not parse provider, type, or organization from them.
- Organization display order is a contiguous deterministic integer sequence among active organizations. Reorder submits the complete active ID sequence and expected registry revision in one transaction.
- Every mutable aggregate has `record_version`; mutation commands require the expected version except idempotent create/reconcile operations.
- Mutations carry a validated command/idempotency key. M02 stores its digest, canonical safe request fingerprint, outcome subject/version, principal, and expiry for 365 days. Same key/same fingerprint returns the safe outcome; same key/different fingerprint returns `registry_idempotency_conflict`.
- Discovery reconciliation additionally deduplicates by source outcome ID and approved external identity key.
- Each transaction increments a monotonic `registry_revision` and appends the change/outbox fact atomically. Consumers can re-query a consistent scope snapshot at or after that revision.
- Ordering is guaranteed only per aggregate version. `registry_revision` provides invalidation/watermark semantics, not causal ordering of provider observations.
- Concurrent attempts to associate one scoped provider identity with different accounts yield exactly one commit and one typed conflict. They never produce two active links.
- SQLite busy/lock results are typed unavailable/retryable outcomes according to the DB plan; they are never converted into mutation success.

### 3.9 Degradation and recovery

- A malformed, partial, unverified-version, or failed discovery outcome is rejected or staged as unresolved without changing current confirmed links.
- If M03 is unavailable, existing registry reads remain available and discovery/auth preparation returns a typed dependency-unavailable outcome.
- If the registry repository/schema is unavailable, M02 health is not ready and mutations fail closed. Consumers may continue using their last registry revision only if they label it stale under their own policy.
- Event publication failure keeps the registry mutation uncommitted unless the approved transactional outbox persists both atomically.
- Restore may roll back registry changes. Before readiness, M08 checks schema and invokes a registry reconciliation/health check; no provider call or automatic reassociation occurs during restore.
- Conflicting identity after restore or later discovery disables effective monitoring for the affected profile/account path and requests owner review without deleting history.

## 4. Public contracts

All names and schemas are proposals under `registry.v1`. They move from Concept to Proposed only after root review and remain blocked from synchronization where M0 evidence is required.

### 4.1 Published views

| Contract ID / view | Required fields and semantic rules | Known consumers | Compatibility promise |
|---|---|---|---|
| CTR-REG-001 `OrganizationViewV1` | `organization_id`, name, optional description, display order, lifecycle, record version, created/updated/archived UTC instants, safe active/archived account counts, registry revision | M05/M06/M07/P01/P02 | Null/ordering/lifecycle meanings fixed; additive optional fields only within V1 |
| CTR-REG-002 `AccountViewV1` | `account_id`, provider key, friendly name, organization ID nullable only for Ungrouped, lifecycle, monitoring preference, effective monitoring state/reason, identity decision, masked identity field-state, record version/times/revision | M04/M05/M06/M07/P01/P02 | Internal ID immutable; no raw provider identity; enum growth requires unknown handling |
| CTR-REG-003 `MonitoringProfileViewV1` | profile ID, account ID, purpose, lifecycle, protected-default flag, identity-verification decision/time, safe locator-state (not value), applicable resource IDs, version/revision | M03/M04/adapters/P01/P02 | Locator value is never public; protected semantics cannot weaken compatibly |
| CTR-REG-004 `ProviderInstallationViewV1` | installation ID, provider key, platform key, safe installation label, version field-state, discovery/presence state, first/last seen, compatibility-reference state, version/revision | M03/M04/M08/P01/P02 | No executable/full path in public contract; provider fields remain versioned |
| CTR-REG-005 `AccountResourceViewV1` | resource ID, account ID, kind, optional parent ID, safe label, provider identity field-state/masked value, lifecycle, linked profile IDs, version/times/revision | M04/M05/P01/P02 | Resource kind meaning stable; unknown/provider-specific remain explicit |
| CTR-REG-006 `IdentityCorrelationDecisionV1` | decision ID/state, account/candidate/profile safe IDs, evidence-class codes and safe references, verification source class, owner-confirmed flag/actor safe ID/time, conflict/reason code, validity/version/revision | M06/provider adapters/P01/P02 | Never raw evidence or personal identity; owner confirmation never reclassified |
| `RegistryScopeSnapshotV1` under CTR-REG-001/002/005 | registry revision; requested global/org/provider/account scope; ordered organization/account/resource IDs; lifecycle and eligibility flags; completeness outcome | M04/M05/M06/M07/M08 | Point-in-time membership only; no telemetry or health values |
| `DiscoveryCandidateViewV1` under CTR-REG-006 | candidate ID/kind/provider/installation, masked safe label field-state, association state, evidence classes, first/last seen, owner-action requirement | P01/P02/provider enrollment | Strict allowlist; no raw discovery payload/locator |
| `AccountConfigurationReferenceViewV1` under CTR-REG-002 | account ID, approved owner namespace/kind, opaque reference ID, lifecycle, record version/revision | owning module/adapter, M04, M08 safe export | No setting value/secret; namespace/kind meanings versioned and allowlisted |
| CTR-REG-008 `ReauthenticationRequestWorkflowV1` | workflow/request ID, account/profile, state/generation, eligibility, started/updated/completed times, safe action/reason, idempotency and M03 operation refs | P01/P02/M03/M04 | Durable M02 workflow; no credential, OTP, cookie, locator, or provider payload |
| CTR-REG-009 `AlertScopeAndSubjectQueryV1` | bounded scope snapshot, registry revision, organization/provider/account/resource chain, lifecycle/eligibility, completeness and cursor | M07 | Read-only current registry truth; no telemetry, alert state, or table access |
| CTR-REG-010 `AuthenticationHealthChangedV1` | account/profile/provider, previous/current normalized state, source generation, identity comparison, observed/recorded time, safe evidence refs, explicit newer recovery | M04/M05/M07/M08 | Canonical state is `reauthentication_required`; delivery/replay via CTR-EVT-001 |

### 4.2 Internal sensitive handle

`ResolvedMonitoringTargetV1` is an application-boundary handle, not an API/event DTO. It contains profile/account/provider IDs, protected flag, expected safe identity reference, and an opaque non-displayable `profile_locator_ref`. Only composition/M03 adapter invocation may receive it after authorization and safety checks. Its representation and structured logging serialize the locator as redacted. It cannot be persisted in command receipts, events, diagnostics, OpenAPI examples, or browser responses.

### 4.3 Published command/query ports

| Port | Input/output | Preconditions/authorization | Typed errors/outcomes | Idempotency/concurrency |
|---|---|---|---|---|
| `CreateOrganizationV1` | name/description/order intent, command ID → view | M01 `write:accounts`; valid name; active-name policy | invalid/name conflict/unavailable | command receipt; atomic order shift |
| `RenameOrganizationV1` | ID/version/new name → view | `write:accounts`; active or archived target | not found/invalid/conflict/stale version | set-to-value replay safe |
| `ReorderOrganizationsV1` | complete active ID sequence/expected revision → ordered views | `write:accounts`; exact current set | invalid set/stale revision/unavailable | one atomic revision |
| `ArchiveOrganizationV1` | ID/version → archived view | `write:accounts`; no active assigned account | not found/not empty/stale version | terminal set, replay safe |
| `RestoreOrganizationV1` | ID/version/order → active view | `write:accounts`; name/order valid | name conflict/stale version | one transition |
| `Get/ListOrganizationsV1` | ID or bounded cursor/filter/sort → view/page | `read:accounts` | not found/invalid cursor/unavailable | side-effect free |
| `RegisterAccountV1` | provider key/friendly name/org/optional reviewed candidate/command ID → view | `write:accounts`; provider admitted; real identity association rules | provider unknown, alias conflict, candidate conflict, confirmation required | command receipt; DB identity uniqueness |
| `RenameAccountV1` | ID/version/name → view | `write:accounts` | not found/alias conflict/stale version | set-to-value replay safe |
| `AssignAccountOrganizationV1` | account/version/org or null → view | `write:accounts`; destination active | org/account not found, org archived, stale version | one change/history fact |
| `SetAccountMonitoringV1` | account/version/preference → view | `write:accounts`; enabling requires eligible identity/profile/resource | not eligible/conflict/archived/stale version | set-to-value replay safe |
| `Archive/RestoreAccountV1` | account/version → view | `write:accounts`; restore rechecks identity eligibility | not found/stale/conflict | terminal/reversible explicit transition |
| `Get/ListAccountsV1` | ID or bounded filters/cursor/sort → view/page | `read:accounts` | invalid filter/cursor/unavailable | side-effect free |
| `Set/InvalidateAccountConfigurationReferenceV1` | account/version + approved owner namespace/kind + opaque reference → safe reference view | authorized owning module orchestration; owner configuration permission where user-initiated | owner not admitted, invalid/dangling reference, stale version, unavailable | set-to-value, optimistic version, no value copy |
| `GetRegistryScopeSnapshotV1` | global/org/provider/account scope + optional minimum revision → snapshot | authorized internal consumer or `read:accounts` API mapping | invalid scope/revision unavailable | consistent query |
| `RegisterProviderDefinitionV1` | synchronized safe M03 manifest identity → definition | composition/internal authority only | incompatible manifest/provider conflict | idempotent provider key/version |
| `ReconcileDiscoveryOutcomeV1` | sanitized CTR-PROV-005 outcome/source ID → installation/candidate changes | internal M03/M04 authority; accepted schema/version/source | malformed/unverified/incompatible/dependency unavailable | source ID + approved identity dedup |
| `Get/ListProviderInstallationsV1` | bounded query → views/page | `read:accounts` | invalid cursor/unavailable | side-effect free |
| `ConfirmIdentityAssociationV1` | candidate/account/version/safe evidence-set hash/command ID → decision | authenticated owner with `write:accounts`; reviewed candidate | conflict/stale evidence/not found/unsafe evidence | command receipt; unique association |
| `ConfirmProviderIdentityFingerprintV1` | exact existing account/version + provider identity scheme/scope/version + approved SHA-256 fingerprint + immutable source/parser tuple + observation reference/digest + principal/idempotency → resolution | authenticated owner; account already active and owner-confirmed; provider composition validated its approved source tuple | not found/stale/conflict/unavailable | command receipt binds all evidence fields; scoped identity uniqueness; never selects a sole account |
| `ResolveProviderIdentityFingerprintV1` | provider identity scheme/scope/version + approved SHA-256 fingerprint → exact active account, unresolved, or conflict | authorized internal consumer; approved fingerprint classification | unresolved/conflict/unavailable | side-effect free; no account guessing |
| `InvalidateIdentityAssociationV1` | decision/version/reason → decision | `write:accounts`; explicit reviewed reason | not found/stale/already terminal | idempotent terminal transition |
| `Get/ListDiscoveryCandidatesV1` | filters/cursor → views/page | `read:accounts` | invalid cursor/unavailable | no auto-association side effect |
| `EnrollMonitoringProfileV1` | account/purpose/opaque adapter-approved locator handle/protection evidence/command ID → view | internal enrollment orchestration + owner `write:accounts`; M0-approved profile mode | protected/default conflict, identity unresolved, locator conflict | locator identity dedup; no locator in receipt |
| `SetMonitoringProfileLifecycleV1` | profile/version/desired lifecycle → view | `write:accounts`; cannot weaken protected flag | not found/protected/stale | set-to-state |
| CTR-REG-008 `StartReauthenticationRequestV1` | profile/version/expected account/idempotency key → durable workflow | `write:reauth`; profile managed, unprotected, compatible | protected, unresolved, wrong account, archived, incompatible, unavailable | same fingerprint returns same workflow; conflict is typed |
| CTR-REG-008 `Get/CancelReauthenticationRequestV1` | workflow/version → current state or cancellation receipt | authorized owner; cancellation only in synchronized cancellable states | not found, forbidden, stale, not cancellable, unavailable | durable generation; restart-safe |
| `PrepareProfileAuthenticationV1` | workflow/profile/version/expected account → sensitive target handle | internal CTR-REG-008 coordinator only; protected/default checks repeated | protected, unresolved, wrong account, archived, incompatible, unavailable | preparation ID; no provider side effect |
| `ReconcileProfileIdentityV1` | workflow/preparation ID + sanitized CTR-PROV identity outcome → CTR-REG-010 state + decision/profile view | internal M03 result; identity proof scope/version matches preparation | mismatch/conflict/stale/invalid result | operation/result ID unique; atomic with workflow/outbox |
| `Upsert/RetireAccountResourceV1` | sanitized resource evidence/account/parent/command → view | internal discovery or reviewed owner action; approved resource semantics | duplicate/conflict/cycle/unknown parent | source ID/key dedup, optimistic version |
| `Get/ListAccountResourcesV1` | account/scope/filter/cursor → page | `read:accounts` | invalid cursor/unavailable | side-effect free |
| `ListRegistryChangesV1` | subject/time/kind bounded query → page | diagnostic/account-history permission agreed with M01/P01 | forbidden/invalid range/cursor | append-only read |
| `PurgeExpiredRegistryHistoryV1` | explicit UTC cutoff/batch limit → counts/change ID | M08 internal operation; cutoff cannot affect current records | unsafe cutoff/unavailable | repeated batch deletes only eligible rows |
| `GetRegistryHealthV1` | no provider input → safe state | M08/internal/P01 safe mapping | repository unavailable/incompatible | repeatable safe query |

### 4.4 Event contract: CTR-REG-007 `RegistryChangedV1`

The event uses approved `EventEnvelopeV1`: opaque event ID, type `registry.changed.v1`, occurred/recorded UTC times, producer/version, correlation/causation IDs, subject ID, aggregate version, and registry revision.

Allowlisted `change_kind` values are:

- organization: `created`, `renamed`, `reordered`, `archived`, `restored`;
- account: `registered`, `renamed`, `organization_assigned`, `monitoring_preference_changed`, `configuration_reference_changed`, `archived`, `restored`;
- installation: `discovered`, `presence_changed`, `version_state_changed`;
- identity: `provider_verified`, `owner_confirmed`, `confirmation_required`, `conflict_detected`, `invalidated`, `wrong_account_detected`;
- profile: `enrolled`, `lifecycle_changed`, `protection_strengthened`, `identity_verification_changed`, `reauthentication_reconciled`;
- resource: `registered`, `relationship_changed`, `retired`, `restored`.

Payload contains only safe subject IDs, provider key where needed, old/new lifecycle or membership IDs, safe reason code, aggregate version, and registry revision. It does not include names, descriptions, labels, provider identities, profile locators, executable paths, evidence values, or raw outcomes. Delivery is at least once through the approved transactional outbox; consumers deduplicate by event ID and re-query views. Ordering is per aggregate version. New change kinds are additive only for unknown-tolerant consumers; meaning changes require a new major.

CTR-REG-008 workflow changes and CTR-REG-010 authentication-health changes use the same CTR-EVT-001 durability rules. A terminal M03 operation is not itself healthy recovery: M02 emits recovery only after a newer verified identity/authentication generation establishes `healthy`. Silence, dashboard login, stale completion, or a generic later collection success cannot recover the provider-auth condition.

### 4.5 Consumed contracts

| Owner/contract | Required version/status | M02 use | Failure/degradation behavior |
|---|---|---|---|
| CTR-COMMON-001 `OpaqueIdV1` | `proposed_aligned` 1.0.0 | all internal identities | reject malformed; never parse semantics |
| CTR-COMMON-002 time contract | `proposed_aligned` 1.0.0 | UTC instants/durations | reject non-aware/non-UTC storage input |
| CTR-COMMON-006 `EventEnvelopeV1` | `proposed_aligned` 1.0.0 | registry events/outbox | mutation cannot commit without atomic event record |
| CTR-COMMON-007 field-state contract | Draft-aligned V1 | provider-derived optional values | absent/unknown/unavailable/unsupported/withheld/stale/not-applicable never collapse |
| CTR-EVT-001 durable event transport | Draft-aligned V1 | producer outbox, consumer receipts/checkpoints, replay and retention | incompatible/poison/backlog state is explicit; no in-memory-only delivery |
| CTR-FND-004 correlation/safe log | `proposed_aligned` 1.0.0 | command/evidence correlation | generate/validate safe ID; no raw fallback |
| CTR-FND-006 migration metadata | `proposed_aligned` 1.0.0 | M02 migration ownership/recovery metadata | startup refuses incompatible schema |
| CTR-DB-002 repository/UoW | `proposed_aligned` 1.0.0 | production persistence adapters | typed conflict/unavailable/corrupt; fail closed |
| CTR-IAM-001/002 | `proposed_aligned` 1.0.0 | permissions and actor identity | mutation denied/fails closed when authorization unavailable |
| CTR-PROV-002 `CapabilityManifestV1` | `evidence_blocked` 1.0.0 | provider definition/profile/resource eligibility | unknown/incompatible remains blocked, not guessed |
| CTR-PROV-005 `DiscoveryOutcomeV1` | `evidence_blocked` 1.0.0 | installations/candidates/safe identity evidence | invalid/partial/unverified result cannot overwrite confirmed links |
| CTR-PROV-006 `AuthHealthOutcomeV1` | `evidence_blocked` 1.0.0 | safe reference for profile visibility only | M02 does not own/normalize auth health; unavailable remains external state |
| CTR-PROV-007 `ReauthFlowV1` | `evidence_blocked` 1.0.0 | preparation/result correlation | protected/default/unverified targets rejected; failure preserves registry |
| CTR-RUN-007 `SessionCorrelationDecisionV1` | `evidence_blocked` 1.0.0 | optional M06 reference to M02 identity facts; no M02 runtime ownership | runtime ambiguity stays in M06; no direct table sharing |
| CTR-OPS-006 component health | `proposed_aligned` 1.0.0 | safe health publisher | return degraded/unavailable without identity disclosure |
| CTR-OPS-007 participant family | Draft-aligned V1 | registry retention/export/post-restore consistency implementation | bounded typed failure; no M08 access to registry tables |

### 4.6 Typed error vocabulary

Stable M02 error codes proposed for P01 mapping are:

- validation: `registry_invalid_name`, `registry_invalid_order`, `registry_invalid_filter`, `registry_invalid_cursor`, `registry_invalid_relationship`;
- existence/state: `registry_subject_not_found`, `registry_subject_archived`, `registry_organization_not_empty`, `registry_stale_version`;
- identity: `registry_alias_conflict`, `registry_identity_confirmation_required`, `registry_identity_conflict`, `registry_identity_evidence_stale`, `registry_wrong_account_detected`;
- profile/resource: `registry_profile_protected`, `registry_profile_not_eligible`, `registry_profile_locator_conflict`, `registry_resource_conflict`, `registry_resource_cycle`;
- dependency/compatibility: `registry_provider_not_admitted`, `registry_provider_version_unverified`, `registry_discovery_outcome_invalid`, `registry_dependency_unavailable`;
- infrastructure: `registry_idempotency_conflict`, `registry_repository_unavailable`, `registry_schema_incompatible`, `registry_internal_error`.

Errors contain safe codes, correlation ID, and safe subject ID only when disclosure is authorized. They never echo a submitted label, identity, locator, path, provider payload, SQL, or exception argument. P01 owns HTTP status/problem mapping.

### 4.7 Contract change assessment and synchronization blockers

This plan adds the first proposed `registry.v1` surface; it changes no implemented contract. Before approval, the root steward must:

1. resolve all M0-blocked identity, installation, profile, and resource semantics;
2. reconcile M02 `IdentityCorrelationDecisionV1` with M06 `SessionCorrelationDecisionV1` so neither owns the other's records;
3. approve CTR-REG-008 durable M02 coordination, CTR-PROV-007 execution, and CTR-REG-010 reconciliation/recovery semantics;
4. approve safe profile-locator handling and which internal boundary may resolve it;
5. review every CTR-REG field with M04–M08, P01, and P02 consumers;
6. approve global revision, event payload, outbox ownership, history retention, and command-idempotency semantics;
7. decide normalized friendly-name uniqueness and organization archive behavior;
8. allocate migration revisions/shared contract files and decide whether any proposal requires a new ADR.

No implementation agent may compensate for an unresolved contract through adapter imports, direct table access, duplicate DTOs, or provider-specific columns.

## 5. Data and persistence

### 5.1 Table ownership

Exact DDL and migration identifiers require the persistence review. All names below are proposed and exclusively owned by M02.

#### `reg_registry_state`

- singleton key;
- monotonic `registry_revision`;
- schema/domain policy version;
- created/updated UTC instants.

The row is locked/updated in each registry mutation transaction. It is not a substitute for database schema revision.

#### `reg_organization`

- `organization_id` primary business ID;
- normalized-name key, display name, optional bounded description;
- lifecycle, display order, record version;
- created/updated/archived UTC instants;
- creation command ID digest.

Constraints enforce non-empty bounded normalized name, non-negative order, valid lifecycle/timestamp combinations, and record version greater than zero. Friendly text is user-owned metadata, not logged or emitted in internal events.

#### `reg_provider_definition`

- stable provider key primary business key and safe display name;
- admitted adapter/protocol/manifest identity references, not manifest payload;
- lifecycle and first/last admitted UTC instants;
- record version.

This table contains no provider-specific credentials, settings, capability data, or SDK objects.

#### `reg_provider_installation`

- `provider_installation_id` primary business ID and provider key;
- approved installation identity key/fingerprint and identity scheme version;
- platform key; safe label; reported-version value plus field-state;
- discovery/presence state; first/last seen UTC instants;
- last discovery outcome ID, provider/version compatibility reference, record version;
- optional private opaque installation-locator reference only if M0/security approve it.

Public queries never return the locator or raw identity key. M0 decides whether a safe stable installation key exists. Without it, records remain review candidates and are not automatically merged.

#### `reg_account`

- `account_id` primary business ID, provider key, friendly name and normalized-name key;
- nullable `organization_id` scalar reference to an M02-owned organization;
- lifecycle and identity-decision state;
- monitoring preference; record version;
- created/updated/archived UTC instants and creation command ID digest.

`organization_id` is an ordinary within-module FK; null is Ungrouped. There is no provider credential, quota, auth-health, budget, token, or process field.

#### `reg_account_configuration_reference`

- reference ID and account ID;
- approved owning module/adapter namespace and versioned reference kind;
- opaque non-secret referenced-record ID, lifecycle, record version;
- created/updated/invalidated UTC instants and safe correlation/command IDs.

It stores no configuration value, provider locator, secret, threshold, polling rule, or provider-specific payload. The owning module validates/owns the referenced record through its published port; there is no cross-module FK or table lookup. Exact namespaces, multiplicity, invalidation, and dangling-reference recovery are a contract-synchronization decision.

#### `reg_registry_change`

- immutable change ID, subject type/ID, aggregate version, registry revision;
- allowlisted change kind and versioned typed detail shape;
- required prior/new AgentMonitor-owned metadata for owner-facing history, including account/organization friendly names, organization IDs, lifecycle, monitoring preference, and ordering where applicable;
- authenticated actor class and opaque actor ID; correlation/command IDs;
- occurred/recorded UTC instants and expiry UTC instant.

Friendly-name and organization-move history is required by FR-ACC-002 and is retained in this protected table. It is available only through authorized bounded history queries. Provider identity values, masked provider labels, profile locators, descriptions that are not required to explain the change, evidence payloads, and arbitrary free-form maps are prohibited. `RegistryChangedV1` and structured-log projections deliberately omit friendly names and other mutable display data.

#### `reg_provider_identity_claim`

- claim ID, provider key, identity scheme/scope/version;
- approved safe external subject key or keyed fingerprint, never an unreviewed email;
- account ID nullable until association; evidence class and decision state;
- source/evidence reference IDs, not raw evidence;
- valid-from/invalidated/last-verified UTC instants; record version;
- owner-confirmation actor/time fields when applicable.

The M0 handoff decides whether an external subject can be stored directly, only as a fingerprint, or not at all. Schema approval is blocked until that classification exists for the first provider.

#### `reg_discovery_candidate`

- candidate ID, provider/installation IDs, candidate kind;
- source outcome ID/schema/source classification and safe evidence reference;
- allowlisted masked label plus field-state when approved;
- association state, associated subject ID nullable, reason code;
- first/last seen, reviewed/dismissed/stale UTC instants; record version and expiry.

No raw outcome, provider JSON, CLI text, full identity, path, prompt, response, source, or secret-bearing field is stored.

#### `reg_monitoring_profile`

- profile ID, account ID, provider/installation IDs;
- purpose and lifecycle;
- private opaque locator reference plus locator scheme/version and non-reversible deduplication fingerprint when approved;
- `protected_default_profile` boolean;
- identity verification state, safe expected-identity claim ID nullable, last-verification result reference/time;
- record version and created/updated/archived UTC instants.

The opaque locator may identify provider-owned state; it is treated as sensitive operational metadata. It is inaccessible to generic queries, logs, exports, browser DTOs, and events. Credential contents are prohibited.

#### `reg_account_resource`

- resource ID, account ID, normalized kind and optional provider-specific kind/version;
- optional parent resource ID within the same account;
- safe label and approved provider resource identity key/fingerprint with scheme/version;
- lifecycle, first/last verified UTC instants, record version;
- creation source/command ID.

#### `reg_profile_resource_link`

- profile ID and resource ID composite key;
- relationship evidence class/reference, owner-confirmed flag/time;
- valid-from/invalidated UTC instants and record version.

Both subjects must belong to the same account. Invalidated links remain historical or produce a retained history fact; they are never silently reassigned.

#### `reg_identity_decision`

- decision ID, optional candidate/claim/profile IDs, account ID nullable;
- decision/evidence classes; safe reason/evidence-reference set digest;
- source/contract/schema versions;
- owner actor/time when confirmed; validity/invalidation; aggregate/registry revisions.

This is not M06 runtime correlation storage. It contains no session ID/PID unless a later synchronized contract proves an opaque runtime subject reference is necessary; that change requires M06 review.

#### `reg_command_receipt`

- principal safe ID, operation key, idempotency-key digest composite uniqueness;
- canonical safe request fingerprint; outcome subject/type/version and registry revision;
- created/expiry UTC instants.

No raw idempotency key, raw request, label, description, identity, locator, or error detail is retained.

#### Registry outbox ownership

CTR-EVT-TOPOLOGY-001 fixes the physical direction: M02 owns `reg_event_outbox`, its migration, event rows, producer sequence, and atomic append with `RegistryChangedV1`. PLAN-DB implements the reusable claim/delivery mechanics, but the dispatcher accesses these rows only through M02's published event-storage port. M02 never writes another module's table; consumers own and atomically commit their own receipt/checkpoint with their domain effect. This Draft allocation still requires owner approval before implementation, but a central event journal is not an implementation option.

### 5.2 Keys, constraints, and indexes

Proposed indexes are derived from required query shapes and must be verified with real SQLite query plans:

- unique active organization normalized name and `(lifecycle, display_order, organization_id)`;
- accounts by `(organization_id, lifecycle, friendly_name_normalized, account_id)` and `(provider_key, lifecycle, account_id)`;
- account configuration references by `(account_id, owner_namespace, reference_kind, lifecycle)` with synchronized multiplicity uniqueness;
- proposed unique active account normalized friendly name, conditional on the decision in section 13;
- identity claim by `(provider_key, identity_scheme, identity_scope, subject_key_or_fingerprint)` with one current non-conflicting association;
- installations by `(provider_key, platform_key, installation_identity_scheme, installation_identity_key)` and presence/last-seen;
- discovery candidate by `(provider_key, association_state, last_seen_at, candidate_id)` and unique source outcome identity;
- profiles by `(account_id, lifecycle, profile_id)`, `(provider_installation_id, lifecycle)`, and approved locator fingerprint uniqueness;
- resources by `(account_id, lifecycle, kind, resource_id)`, parent ID, and approved scoped provider-resource identity;
- profile-resource links by both profile and resource;
- decisions/history by `(account_id, occurred_at, decision/change_id)` and expiry;
- command receipts by expiry and their composite uniqueness;
- `reg_event_outbox` rows by delivery state/time and event ID.

SQLite partial indexes or JSON semantics cannot enter the repository contract merely for convenience. The persistence plan must document equivalent PostgreSQL behavior or isolate the implementation detail.

### 5.3 Transactions and repository ports

One application use case owns one short transaction. The following operations are atomic:

- organization reorder including all affected record versions and one change/event set;
- account create plus initial identity decision/change/event/command receipt;
- account move/rename/lifecycle/monitoring mutation plus history/event/receipt;
- account configuration-reference set/invalidation plus history/event/receipt;
- unique identity association/confirmation and conflict decision;
- profile enrollment plus protection/identity/resource links;
- re-authentication reconciliation plus verification decision, history, and events;
- resource upsert/relationship change plus history/event;
- eligible history purge batch plus audit/change summary.

Repository ports are aggregate-specific and expose typed queries; there is no generic repository. Domain/application code does not expose SQLAlchemy sessions. Transactions never wrap provider/network/CLI operations. A provider result is collected first, validated at the application boundary, then reconciled in a bounded DB transaction.

### 5.4 Migration sequence

Proposed expand-only initial sequence, subject to central revision allocation:

1. Registry state, organization, provider definition, account, and safe history foundations.
2. Installation, discovery candidate, identity claim/decision.
3. Monitoring profile and profile/resource relationships.
4. Account resource hierarchy and query indexes.
5. Command receipt and approved outbox integration.

Every revision records owner M02, requirements, estimated rows, lock/downtime behavior, backup prerequisite, validation queries, recovery path, and compatibility range. Tests apply the real complete Alembic chain to a real temporary SQLite file from empty and from every supported prior artifact. No implicit `create_all` or hidden startup DDL is allowed.

No downgrade is claimed safe until it is implemented and executed against a real database. Before shared data exists, a failed additive initial migration may be repaired forward or the isolated empty test database recreated. After owner data exists, recovery uses a verified backup plus prior compatible binary or an approved forward fix; destructive table/column contraction requires an ADR and explicit approval.

### 5.5 Retention, archival, backup, and export

- Current organizations, accounts, provider definitions/installations, profiles, resources, current identity claims, and relationships persist while registered, including archived state.
- Registry change, decision, discovery-candidate, and command-receipt records are proposed for 365-day retention, subject to owner/M08 approval.
- Purge takes an explicit UTC cutoff, deletes only eligible immutable history in bounded real transactions, records safe counts, and never deletes current links or active subjects.
- M08 backs up the physical database. M02 supplies schema/version/consistency validation and never accesses M08 backup tables.
- M08 exports registry data through M02 query ports. Export omits private locators, full external identities, evidence payloads, command fingerprints, and internal protection details that would create risk.
- Restore validation checks table constraints, current identity uniqueness, resource cycles, profile/account consistency, registry revision monotonicity relative to the restored database, and outbox integrity before normal readiness.

### 5.6 Sensitive and prohibited fields

Allowed stored data is limited to account-friendly metadata, safe provider keys/IDs or reviewed fingerprints, masked labels, relationship/lifecycle/history metadata, opaque profile locators, and evidence references. Prohibited in every `reg_*` row:

- passwords, API/OAuth tokens, refresh state, cookies, OTP/MFA/recovery values, credential-file contents;
- prompts, responses, tool arguments/results, source code, arbitrary terminal/CLI/provider output;
- arbitrary process environments, process memory, browser data, or raw provider payloads;
- quota/budget/usage/process observations owned by M05/M06;
- full email/personal identity unless a future explicit requirement, privacy review, schema change, and migration approve it.

## 6. External, provider, platform, API, and UI boundaries

### 6.1 Provider discovery boundary

M02 has no direct external I/O. M03/adapters publish a sanitized `DiscoveryOutcomeV1` containing only allowlisted candidate records, source/outcome IDs, scoped identity scheme/version, provider/adapter/provider-version metadata, evidence references, and field states. M02 validates contract/schema compatibility before any transaction.

| Boundary result | Registry behavior |
|---|---|
| Success with unique M0-approved stable identity | Idempotently reconcile installation/candidate; automatic association only if the approved rule and existing unique link permit it |
| Partial | Store only valid allowlisted candidates and explicit missing-field states; never infer omitted values |
| Unsupported | Record candidate/capability state only when scoped evidence says unsupported |
| Unverified version/invalid data | Preserve current registry; record sanitized failed/staged result reference; request review |
| Authentication/authorization required | Do not retry or change identity; expose owner-action requirement through M03/M04 |
| Provider unavailable/rate limited/deadline | Preserve current registry; no missing/deleted inference |
| Conflicting identity | Record conflict decision, block automatic association/effective target, preserve prior links |

Timeouts, network retries, rate limits, command execution, path validation, output limits, and provider version parsing remain M03/adapter/platform responsibilities.

### 6.2 Re-authentication boundary

```text
P01 authorized CTR-REG-008 start/get/cancel
  -> M02 durable workflow + PrepareProfileAuthenticationV1
  -> M03/provider adapter CTR-PROV-007 official operation (owner handles secrets)
  -> sanitized verified identity outcome
  -> M02 ReconcileProfileIdentityV1 + CTR-REG-010
  -> M04 safe post-auth read-only verification/collection
```

M02 preparation has no provider side effect. The returned opaque locator handle is internal only. A flow is not reported successful until M02 reconciles the expected stable identity and the downstream safe verification completes according to the synchronized workflow. Wrong-account or unverifiable outcomes preserve prior registry relationships and history.

### 6.3 Runtime-correlation boundary

M06 owns process/session observations, correlation evidence, owner confirmation of a runtime session relationship, and `SessionCorrelationDecisionV1`. M02 supplies account/profile/identity candidates and decision facts. M06 may store an M02 account ID as a scalar only after its own policy accepts evidence; M02 never queries M06 tables. If M06 asks the owner to confirm a runtime mapping, it may reference a provider identity decision or account candidate through contracts, but M02 does not absorb the runtime aggregate.

### 6.4 Proposed P01 resource mapping

P01 owns exact routes, transport schemas, permissions, HTTP codes, ETags, pagination, and OpenAPI. The synchronized mapping is expected to cover:

- `/api/v1/organizations`: list/create, item get/patch/archive/restore, explicit reorder action;
- `/api/v1/accounts`: list/register/get/patch/archive/restore, organization assignment, monitoring preference;
- `/api/v1/providers` and `/api/v1/provider-installations`: safe read-only views and discovery-status visibility;
- `/api/v1/accounts/{id}/profiles`: safe profile views, enrollment guidance, lifecycle, and explicit re-auth start through orchestration;
- `/api/v1/accounts/{id}/resources`: safe resource/relationship views;
- review/confirmation resources for discovery candidates and identity decisions;
- bounded account/registry change history.

P01 must not serialize `ResolvedMonitoringTargetV1`, profile locator values, raw identity keys, ORM rows, or discovery payloads. State-changing operations require M01 authorization, browser CSRF, ETag/version or idempotency key as appropriate, and safe problem mapping.

### 6.5 P02 workflow contract

P02 consumes only the generated API client. Required truthful registry UI states include:

- no organizations/accounts yet;
- Ungrouped accounts as a real scope, not a fake organization record;
- discovery candidate awaiting review;
- identity unknown, owner-confirmed, provider-verified, conflict, wrong account, unavailable, or unsupported;
- protected default profile with no mutation action;
- managed-profile re-auth action only when the API marks it eligible;
- archived/disabled/monitoring-ineligible distinctions;
- partial provider discovery without a misleading empty state;
- version/conflict error requiring refresh;
- masked/withheld identity fields without revealing raw values.

The UI never imports M02 code, reads SQLite/provider files, invents sample accounts, or aggregates telemetry from registry membership itself.

### 6.6 Consumer matrix

| Consumer | Contract use | Forbidden coupling |
|---|---|---|
| M03/adapters | resolve protected approved target; submit discovery/identity outcomes | direct registry tables; raw locator in manifest/log |
| M04 | list eligible account/profile/resource collection targets and react to registry changes | infer eligibility from tables; mutate registry |
| M05 | resolve organization/account/resource membership for capacity aggregation | store registry labels as identity; query tables |
| M06 | resolve account/profile identity candidates and preserve unresolved correlation | make M02 own PIDs/sessions; guess from aliases |
| M07 | resolve scopes/labels through query ports for alert rules/views | copy membership truth or consume table rows |
| M08 | health, safe history/export, retention invocation, restore consistency | bypass query ports or export locators/identity keys |
| P01 | map typed commands/views/errors to `/api/v1` | own registry business rules or ORM access |
| P02 | generated-client workflows | handwritten DTOs/direct fetch/database/provider reads |

## 7. Security and privacy

### 7.1 Authorization

- Queries exposing account/organization metadata require the synchronized M01 `read:accounts` permission.
- Metadata, organization, enrollment, association, monitoring, and archive mutations require `write:accounts` or a more narrowly approved permission if M01/P01 split it.
- Auth preparation requires `write:reauth` and still enforces M02 profile safety.
- Discovery reconciliation and auth-result reconciliation use an internal service authority wired by composition, not a bearer scope available to arbitrary API clients.
- M02 never treats V1 single-user status as implicit authorization.

### 7.2 Trust boundaries and abuse cases

| Threat/abuse | Required M02 control |
|---|---|
| Duplicate/wrong account enrollment | immutable internal IDs, approved scoped identity keys, uniqueness, explicit owner confirmation, conflict state |
| Display-name/email guess creates association | labels are display-only; weak evidence cannot auto-associate |
| Malicious discovery payload | typed schema/version check, field/size allowlist, no raw storage, transaction rollback |
| Default profile targeted for login | persisted protected flag plus fail-closed preparation check before adapter invocation |
| Opaque locator leaks | private handle/type, redacted representation, no API/event/log/export/diagnostic serialization |
| Provider identity exposes personal data | safe ID/fingerprint classification from M0, masked display, full email prohibited by default |
| Stale evidence overwrites current link | evidence version/time plus optimistic concurrency and explicit conflict |
| CSRF/local malicious site mutates grouping | M01/P01 session, Origin, CSRF, explicit permission; M02 still validates actor/command |
| Event/log leaks label or locator | strict event/log allowlists and artifact scans |
| Restore resurrects unsafe association | pre-readiness registry consistency and identity-conflict review; no automatic provider mutation |
| Cross-module table use bypasses policy | import/table ownership checks and contract tests |
| Archive/delete destroys history | no V1 hard delete; lifecycle and retained history |

### 7.3 Data-minimization proof

The schema and contract review must produce an allowlist mapping each stored/public field to an approved requirement. Review separately proves:

- no registry schema accepts prompt, response, tool, source, arbitrary environment, raw provider response, or credential content;
- external identity keys are stored only in the approved safe representation for the exact provider/scope/version;
- profile locators cannot appear in generic serialization, logs, errors, events, exports, diagnostics, screenshots, OpenAPI examples, or browser state;
- public DTOs expose masked/withheld fields and internal IDs only;
- account labels/descriptions are excluded from structured logs and internal events;
- no external analytics/crash reporting path exists.

### 7.4 Logging, audit, and errors

Structured logs may contain module/event name, correlation ID, safe internal subject ID, provider key, outcome/error code, aggregate version, registry revision, and duration. They must not contain user labels, descriptions, email, external identity, locator/fingerprint, raw evidence, paths, request bodies, provider output, SQL parameters, or exception arguments before redaction review.

`RegistryChange` is product history, not M01 security audit. M01 records authentication/authorization security events; M02 records domain changes with actor safe IDs. P01/M08 decide the owner-facing combined audit presentation through queries, never by joining tables directly.

### 7.5 Stop conditions

Implementation or live verification stops immediately if:

- M0 does not prove the proposed identity/profile/resource semantic;
- a locator/identity field appears to contain a credential, personal email, content, full path not approved, or arbitrary provider data;
- a default-profile target cannot be distinguished safely;
- a command/provider flow would log out, move, rewrite, or otherwise alter a default profile;
- account evidence conflicts or could associate two accounts;
- another module/table/private import is required;
- a destructive migration or unapproved dependency appears necessary;
- the real test needs login/credits/account mutation beyond its owner-approved packet;
- evidence output may contain a secret or user content.

The agent records a sanitized Blocked/Failed result and escalates; it does not weaken the invariant.

## 8. Configuration and operations

### 8.1 Configuration ownership

M02 proposes **no environment variables or `.env` secrets** for V1. Organization/account/profile/resource metadata is persisted only through authorized use cases. Provider executable/profile/state paths, discovery intervals, auth credentials, API keys, and provider-specific options belong to adapters, M03/M04, or deployment—not M02.

If implementation reveals a real M02 setting need, work stops for a configuration-contract proposal. The key must follow `AGENTMONITOR_REGISTRY_<SETTING>`, document type/range/default/source/reload/security/migration/test behavior, and receive approval before use. A hidden constant that changes public behavior is not an alternative.

Proposed bounded validation values such as maximum label length are contract constants, not operator configuration. Exact limits require P01/UI review and become part of `registry.v1` compatibility.

### 8.2 Health and readiness

`GetRegistryHealthV1` reports only:

- repository reachable/unavailable;
- schema/domain-policy compatible/incompatible;
- current registry revision;
- consistency check state and last completed UTC time;
- pending/conflicting candidate counts as coarse bounded counts only if security approves disclosure;
- retention/outbox backlog health as safe states, not row contents.

Readiness fails for schema incompatibility, repository unavailability, broken core constraints, or inability to atomically publish registry changes. Provider discovery/auth degradation does not make registry reads unready; it is component/capability degradation owned by M03/M04.

### 8.3 Operator procedures to document and exercise

- create/rename/order/archive/restore organization;
- register, rename, group, disable, archive, and restore account;
- review/confirm/dismiss a discovery candidate without guessing;
- identify and resolve a conflicting/wrong-account state safely;
- identify a protected default profile and explain why re-auth is unavailable;
- re-authenticate an eligible managed profile through the official flow while preserving history;
- inspect sanitized registry health/change history;
- back up, restore, upgrade, and validate registry consistency;
- diagnose missing/stale discovery without modifying provider state;
- export safe registry metadata and verify excluded sensitive fields.

Commands remain `TBD` until implemented and verified in the command registry. This plan invents no executable command.

### 8.4 Operational measurements

Local structured measurements may include command duration/outcome, repository query duration, page size, reconciliation candidate count by state, conflict count, outbox age/count, retention deletion count, and consistency-check duration. They contain no names, external identities, locators, provider payloads, or content and are not sent externally.

### 8.5 Backup/recovery and failure isolation

- M08 performs SQLite backup/restore; M02 provides validation queries and post-restore consistency use case.
- No restore validation contacts a provider or changes profile/account state automatically.
- An adapter/discovery failure is committed, if at all, only as a sanitized candidate/outcome reference; confirmed current registry remains intact.
- A registry failure must not terminate running agents or provider collectors already executing; M04 receives typed unavailable and applies its own safe behavior.
- Diagnostics expose IDs/codes/counts/versions only and pass secret/privacy scanning before release.

## 9. Test design before implementation

### 9.1 Evidence status at planning time

All scenarios below are **Not Run**. No test file, production code, migration, real account enrollment, provider observation, or evidence report was created by this planning task. The table defines expected behavioral Red and Green outcomes; missing dependencies, syntax/setup failures, unavailable credentials, or a blocked M0 input do not count as Red.

### 9.2 Pure domain scenarios (T1)

Constructed organization/account/profile/resource values are permitted here only because these scenarios are deterministic, side-effect-free domain rules with no database, filesystem, environment, clock, network, or provider claim. Production time is supplied explicitly as `as_of`.

| Test ID | Requirement | Real dependencies/boundary | Expected initial Red | Green/pass condition | Coordination |
|---|---|---|---|---|---|
| M02-PURE-001 | FR-ORG-001 | Pure organization-name policy | Invalid empty/control/overlong name is accepted or valid Unicode is corrupted | Valid bounded name retained; unsafe forms rejected by stable reason | None |
| M02-PURE-002 | FR-ORG-001 | Pure lifecycle policy | Invalid archive/restore transition is accepted | Only documented active/archived transitions succeed | None |
| M02-PURE-003 | FR-ORG-001/002 | Pure archive precondition | Organization with active accounts can archive | Archive returns `organization_not_empty` with no state change | None |
| M02-PURE-004 | FR-ORG-001 | Pure reorder policy | Missing/duplicate/extra IDs form an order | Only exact active set produces contiguous deterministic order | None |
| M02-PURE-005 | FR-ORG-002 | Pure membership value | Null is classified unknown or a synthetic organization | Null maps only to Ungrouped; unknown cannot occupy the field | None |
| M02-PURE-006 | FR-ORG-003 | Pure scope projection | Archived/wrong-scope account leaks or account is double-counted | Each included account/resource occurs once in the exact scope | M05/M06/M07 review |
| M02-PURE-007 | FR-ACC-001 | Pure identity transition | Rename/move changes internal account ID | Opaque account ID remains identical across metadata changes | None |
| M02-PURE-008 | FR-ACC-001 | Pure provider/internal identity model | Provider external key becomes primary ID or alias identity | Internal ID, provider key, external identity, and friendly name stay distinct | M03 review |
| M02-PURE-009 | FR-ACC-002 | Pure change/history/event projections | Rename/move loses prior value/version or broadcasts the label in an event/log | Protected history preserves prior/new metadata; event/log projection omits labels | Privacy review |
| M02-PURE-010 | FR-ACC-003 | Pure monitoring eligibility | Pending/conflicting account becomes effectively enabled | Preference retained but effective state is disabled with exact reason | M04 review |
| M02-PURE-011 | FR-ACC-003 | Pure account lifecycle | Archive deletes preference/links or remains effectively monitored | Archive preserves metadata/intent and disables effective monitoring | None |
| M02-PURE-012 | FR-ACC-004 | Pure relationship taxonomy | Account, profile, identity, and resource collapse into one type | Each concept keeps an independent ID and typed relationship | M03/M05 review |
| M02-PURE-013 | FR-ACC-004 | Pure resource graph | Cross-account parent or self/cyclic path is accepted | Parent must share account and graph remains acyclic | M05 review |
| M02-PURE-014 | FR-ACC-004 | Pure resource identity policy | Same label merges pools or unknown merges known | Only approved scoped identity deduplicates; labels/unknown never do | M0/M05 review |
| M02-PURE-015 | FR-ACC-005 | Pure approved-identity rule | Weak/non-unique evidence auto-associates | Only synchronized unique stable rule can yield `matched` | M0/M03 input |
| M02-PURE-016 | FR-ACC-005, NFR-RES-001 | Pure discovery-reconcile policy | Partial/malformed/unverified outcome removes confirmed state | Current confirmed links remain; typed unresolved/rejected result returned | M03 review |
| M02-PURE-017 | FR-ACC-006, AC-PROC-003 | Pure correlation policy | Ambiguous evidence chooses an account | Decision is `owner_confirmation_required` or `unresolved` | M06 review |
| M02-PURE-018 | FR-ACC-006 | Pure conflict policy | Conflicting identity overwrites an association | Conflict is terminal pending review; prior association/history retained | Security review |
| M02-PURE-019 | FR-ACC-006 | Pure owner-confirmation policy | Confirmation loses actor/evidence class or becomes provider-verified | Owner-confirmed state retains safe actor/time/evidence distinction | Security review |
| M02-PURE-020 | FR-ACC-006 | Pure invalidation policy | Invalidated decision still qualifies for monitoring | It becomes ineligible and cannot silently re-activate | M04/M06 review |
| M02-PURE-021 | FR-AUTH-002/005 | Pure profile-safety policy | Protected default yields auth target | Preparation returns `profile_protected` before locator resolution | M03/security review |
| M02-PURE-022 | FR-AUTH-002/006 | Pure auth-target policy | Unknown/incompatible/archived profile yields target | Only active, managed, unprotected, verified compatible profile is eligible | M0/M03 review |
| M02-PURE-023 | FR-AUTH-003 | Pure re-auth reconcile policy | Mismatch relinks account or success changes durable account ID | Mismatch preserves link and marks wrong account; match preserves identity/history | M03/security review |
| M02-PURE-024 | FR-HIST-005 | Pure UTC/time policy | Naive/non-UTC time or inconsistent event order is accepted | UTC-aware instants and documented null/order rules enforced | None |
| M02-PURE-025 | NFR-OBS-001 | Pure event/log projection | Name/identity/locator/evidence enters safe payload | Only allowlisted IDs/codes/versions/times remain | Security/privacy review |
| M02-PURE-026 | NFR-ARCH-002 | Pure account-configuration reference policy | A setting/secret or unregistered namespace is accepted | Only an approved owner/kind and opaque non-secret reference are valid | Owning-module/security review |

### 9.3 Real persistence and migration scenarios (T2)

Every DB scenario uses a real temporary SQLite file, the production Alembic chain, production repositories, and production transactions. Organization-only test records are created through real production use cases and are explicitly AgentMonitor-owned temporary data. Provider account/profile/resource scenarios use owner-approved real discovery/enrollment inputs; they do not use invented accounts, provider fixtures, recorded outcomes, or direct row seeding.

| Test ID | Requirement | Real dependencies/boundary | Expected initial Red | Green/pass condition | Coordination |
|---|---|---|---|---|---|
| M02-DB-001 | FR-ORG-001, AC-V1-004 | Real SQLite file + full migrations | Registry tables/revision absent after migrate | Fresh chain creates exact owned schema and compatibility metadata | DB owner |
| M02-DB-002 | FR-ORG-001 | Real DB + CreateOrganization port | Create not persisted or constraints bypassed | View round-trips with version/revision/change/outbox atomically | None |
| M02-DB-003 | FR-ORG-001 | Real DB rename transaction | Rename lacks version/history/event or changes ID | Same ID, incremented version/revision, one safe history/event | None |
| M02-DB-004 | FR-ORG-001 | Real DB concurrent reorder | Partial/duplicate order or lost update commits | One full order commits; stale contender gets typed conflict | None |
| M02-DB-005 | FR-ORG-001/002 | Real DB org/account relationship | Non-empty organization archives | Constraint/use case rejects with zero data/event change | Real account input |
| M02-DB-006 | FR-ORG-001 | Real DB restore/name conflict | Restore creates duplicate active name/order | Conflict typed; valid restore assigns deterministic order | None |
| M02-DB-007 | FR-ORG-002 | Real DB account creation/ungroup | Null is rejected or synthetic row created | Null persists/queries exactly as Ungrouped | Real account enrollment |
| M02-DB-008 | FR-ORG-002 | Real DB assign transaction | Assignment to archived/missing org succeeds or history lost | Invalid rejected; valid move is atomic and historical | Real account enrollment |
| M02-DB-009 | FR-ORG-003 | Real DB scope query/revision | Snapshot duplicates/misses members or crosses revisions | Deterministic complete membership at returned revision | Consumer review |
| M02-DB-010 | FR-ACC-001 | Real DB account lifecycle | Rename/move/archive changes ID or provider association | ID/provider invariant and history survive every mutation | Real account enrollment |
| M02-DB-011 | FR-ACC-001/006 | Real DB concurrent identity association | Same scoped identity links to two accounts | Exactly one association commits; other is conflict | Two reviewed real candidates if available |
| M02-DB-012 | FR-ACC-002 | Real DB account rename | Friendly name absent/ambiguous or prior version overwritten | Required approved name policy and safe history enforced | Real account enrollment |
| M02-DB-013 | FR-ACC-002 | Real DB account move | Move loses old org reference/history | One atomic new membership and change fact | Real account enrollment |
| M02-DB-014 | FR-ACC-003 | Real DB monitoring/archive/restore | Archive deletes data or keeps effective monitoring | All links/history persist; effective eligibility is safe | Real account enrollment |
| M02-DB-015 | FR-ACC-004 | Real DB normalized records | Profile/resource/project is stored on account row | Separate owned rows/IDs/constraints persist | Real discovery/enrollment |
| M02-DB-016 | FR-ACC-004 | Real DB resource graph | Cross-account/cyclic resource commits | Transaction rejects and leaves graph unchanged | Real resource discovery |
| M02-DB-017 | FR-ACC-004 | Real DB profile-resource links | Cross-account/duplicate active link commits | Same-account unique link constraint enforced | Real profile/resource data |
| M02-DB-018 | FR-ACC-004 | Real DB resource reconciliation | Same label deduplicates or stable key duplicates | Only approved identity key deduplicates; conflict safe | M0-approved real resource |
| M02-DB-019 | FR-ACC-005 | Real DB discovery reconciliation | Same real outcome creates duplicate installation/candidate | Repeated outcome is idempotent at one current subject | M03 + real discovery |
| M02-DB-020 | FR-ACC-005, NFR-RES-001 | Real DB invalid/partial outcome transaction | Invalid result partially mutates current confirmed data | Transaction rolls back/stages safe unresolved record only | M03 real naturally invalid result or contract rejection |
| M02-DB-021 | FR-ACC-006 | Real DB owner-confirmation use case | Confirmation is not durable/auditable or leaks evidence | Decision, actor/time, association, revision, event commit atomically | Owner action |
| M02-DB-022 | FR-ACC-006 | Real DB conflict/invalidation | Conflict overwrites prior claim or disappears on restart | Prior claim/history retained; conflict remains visible/ineligible | Real conflicting condition if safely available |
| M02-DB-023 | FR-AUTH-002/005 | Real DB profile + auth preparation | Protected profile locator can be resolved | Protected state survives restart and fails before resolution | Real profile evidence |
| M02-DB-024 | FR-AUTH-003 | Real DB re-auth reconciliation | Success creates duplicate account/profile or mismatch relinks | Match updates same records; mismatch preserves them atomically | Owner-coordinated real re-auth result |
| M02-DB-025 | FR-HIST-005 | Real DB UTC round trip | Offset/precision changes meaning or naive time persists | UTC instant round-trips with documented precision | None |
| M02-DB-026 | AC-V1-004 | Real prior schema artifact + Alembic | Upgrade fails/loses relationships or compatibility is hidden | Every supported path migrates and validates; failure recovery proven | DB/operations owner |
| M02-DB-027 | NFR-DATA-001/NFR-PERF-001 | Real SQLite query plans and constraints | Required query is unindexed/unbounded or relies on portable-leaking SQL | Approved pages/scopes use intended indexes and portable repository semantics | DB/performance review |
| M02-DB-028 | NFR-ARCH-002 | Real DB + owning-module reference validation | Configuration value is copied, cross-table FK used, or invalid reference persists | Only validated opaque reference/version persists and invalidation is historical | Owning module/DB review |

### 9.4 Real HTTP service scenarios (T3)

Each scenario starts the production FastAPI application on an ephemeral loopback port with real configuration, real M01 authentication/CSRF or bearer token, real file-backed SQLite, real migrations, and P01 mappings. Route-function calls and replaced repositories do not qualify.

| Test ID | Requirement | Real dependencies/boundary | Expected initial Red | Green/pass condition | Coordination |
|---|---|---|---|---|---|
| M02-HTTP-001 | FR-ORG-001 | Real HTTP/DB/session/CSRF | Organization create/list absent or bypasses auth | Authorized create/list conforms to generated schema | P01/M01 |
| M02-HTTP-002 | FR-ORG-001 | Real HTTP versioned reorder | Stale/unvalidated reorder partially succeeds | Full valid order succeeds; stale/invalid gets safe problem | P01 |
| M02-HTTP-003 | FR-ORG-001/002 | Real HTTP archive/restore | Non-empty archive succeeds or exposes internals | Safe conflict; explicit move then archive/restore works | P01/P02 |
| M02-HTTP-004 | FR-ORG-002 | Real HTTP account grouping | Ungrouped is fake row/unknown or archived destination accepted | Null Ungrouped and active destination semantics match contract | P01 |
| M02-HTTP-005 | FR-ORG-003 | Real HTTP pagination/scope | Unbounded/duplicate/inconsistent scope response | Bounded deterministic page/snapshot with revision | P01/consumers |
| M02-HTTP-006 | FR-ACC-002 | Real HTTP rename/move/history | ID changes, ETag ignored, or history missing | Same account, version conflict enforced, safe history visible | P01 |
| M02-HTTP-007 | FR-ACC-003 | Real HTTP monitoring/archive | Ineligible enabling succeeds or archive deletes | Safe problem/effective reason; history preserved | M04/P01 |
| M02-HTTP-008 | FR-ACC-005 | Real provider discovery through running stack | Raw provider result leaks or ambiguous candidate auto-enrolls | Only safe candidate appears and requires review | M03/M04/live provider |
| M02-HTTP-009 | FR-ACC-006 | Real HTTP owner confirmation | Missing CSRF/permission succeeds or conflict is hidden | Authorized explicit confirmation works; conflict truthfully returned | M01/P01/owner |
| M02-HTTP-010 | FR-AUTH-002/005 | Real HTTP re-auth start | Protected/default profile starts adapter action | Request fails before adapter invocation with safe code | M03/P01/security |
| M02-HTTP-011 | NFR-RES-001 | Real service with failed discovery input | Failure corrupts registry or makes unrelated list fail | Confirmed data/list stay available; affected state typed | M03/P01 |
| M02-HTTP-012 | NFR-API-001/002, NFR-COMP-001 | Running OpenAPI + generated client | Schema lacks field-state/permissions/problems or client drifts | OpenAPI validates, compatibility passes, generated client calls real routes | P01/P02 |

### 9.5 Real built-browser scenarios (T4)

The production frontend is built and served with the real backend, generated client, M01 login, and real database. Provider-backed views use actual enrolled account data; no screenshot/demo/seeded telemetry is permitted.

| Test ID | Requirement/AC | Real dependencies/boundary | Expected initial Red | Green/pass condition | Coordination |
|---|---|---|---|---|---|
| M02-BROWSER-001 | FR-ORG-001 | Built UI/browser/backend/DB | Organization workflow absent/inaccessible | Keyboard-accessible create/rename/order/archive/restore works | P02/accessibility |
| M02-BROWSER-002 | FR-ORG-002 | Built UI with real account | Ungrouped hidden/mislabeled or move meaning unclear | Ungrouped and one-primary-group state are explicit and correct | P02/owner |
| M02-BROWSER-003 | FR-ACC-002 | Built UI with real account history | Rename/move loses identity or history inaccessible | Same account view updates and safe change history remains | P02 |
| M02-BROWSER-004 | FR-ACC-005/006 | Built UI + real candidate | Candidate auto-enrolls or shows unsafe identity | Masked evidence/review action displayed; no guess | M03/P02/owner |
| M02-BROWSER-005 | FR-ACC-006, AC-UI-005 | Built UI conflict/unknown state | Unknown/conflict appears healthy/empty | Text/icon/action distinguish unknown, confirmation, conflict | P02/accessibility |
| M02-BROWSER-006 | FR-AUTH-002/005 | Built UI real profiles | Protected default offers auth action or managed state unclear | Protected action absent/disabled; eligible managed flow explicit | M03/P02/owner |
| M02-BROWSER-007 | AC-UI-005 | Built UI real service states | Loading/empty/partial/unavailable collapse to same view | Each state is truthful, accessible, actionable, and non-placeholder | P02 |
| M02-BROWSER-008 | AC-UI-002/003/004 | Real browser viewports/zoom | Registry controls/status disappear or rely on color | Usable at approved responsive checkpoints with keyboard/non-color cues | P02/accessibility |

### 9.6 Live provider/account scenarios (T6)

These execute only after M0, deterministic stack completion, an owner-reviewed operation packet, and owner participation. They record opaque aliases, versions, timestamps, result/status, and sanitized evidence references. Authentication secrets remain owner-controlled. Naturally unavailable conditions are Blocked, never simulated.

| Test ID | Requirement/AC | Real dependencies/boundary | Expected initial Red | Green/pass condition | Owner/live coordination |
|---|---|---|---|---|---|
| M02-LIVE-001 | FR-ACC-001/006, AC-LIVE-001 | Six intended real Claude accounts or owner-declared unavailable entries | Account cannot be uniquely/explicitly associated or history breaks | Each available account has unique internal ID and owner-confirmed identity status | Owner required |
| M02-LIVE-002 | FR-ACC-001/006, AC-LIVE-002 | Four intended real Codex accounts or owner-declared unavailable entries | Same as above for Codex | Each available account is durably and truthfully registered | Owner required |
| M02-LIVE-003 | FR-ACC-001/004/006, AC-LIVE-003 | Two intended real Ollama identities/workspaces or documented actual relationship | Product/account/workspace relationship is guessed | Actual observed relationship is represented or explicitly unresolved | Owner required |
| M02-LIVE-004 | FR-ACC-004 | Real subscription/API/project/workspace/profile relationships | Distinct pools collapse/double-associate | Proven resources/profiles remain distinct with safe links | Owner + adapters |
| M02-LIVE-005 | FR-ACC-005, AC-LIVE-004 | Current installed provider versions and real read-only discovery | Install/candidate dedup or field states disagree with source | Safe observed installation/candidates reconcile once with scoped evidence | Owner + M03/adapters |
| M02-LIVE-006 | FR-ACC-006, AC-PROC-003 | Naturally ambiguous real identity/correlation if available | Product guesses or hides ambiguity | Unresolved/confirmation workflow preserves evidence distinction | Owner; Blocked if no safe condition |
| M02-LIVE-007 | FR-AUTH-002/006 | One approved managed profile per provider/version when supported | Unsafe/protected target starts flow or locator leaks | Official flow starts only for eligible target with no secret capture | Owner interactive; separate approval |
| M02-LIVE-008 | FR-AUTH-003, AC-LIVE-006 | Completed real re-auth on one account per provider when supported | New account/profile created or metadata/history lost | Same IDs/group/name/resources/history remain; verification updates | Owner interactive |
| M02-LIVE-009 | FR-AUTH-004/005 | Default-profile non-modification evidence around live flow | Default profile/state changes or secret appears | Approved non-secret comparison shows unchanged; artifacts clean | Owner/security |
| M02-LIVE-010 | FR-AUTH-006, AC-LIVE-004/006 | Current provider version/profile-isolation evidence | Unverified version/isolation is treated compatible | Exact scoped capability is supported or remains visible Blocked/unsupported | Owner + M0/live reviewer |

### 9.7 Operational, architecture, security, documentation, and dependency scenarios

| Test ID | Layer | Requirement/AC | Real dependencies | Expected initial Red | Green/pass condition |
|---|---|---|---|---|---|
| M02-OPS-001 | T7 operations | NFR-DATA-001, AC-OPS-004 | Real DB, M08 backup/checksum/integrity/restore | Restore loses registry or fails consistency | Restored app starts and exact relationships/history validate |
| M02-OPS-002 | Performance | NFR-PERF-001 | Real current enrolled registry and production queries | Current-set page/scope latency/query plan misses target | Measured bounded queries meet approved workstation target |
| M02-OPS-003 | Performance | NFR-PERF-001 | Owner-approved real/generated AgentMonitor-owned load method | 100-account claim requires invented accounts or redesign | 100-account structural target measured without fake provider claim; otherwise Blocked |
| M02-OPS-004 | T7 resilience | NFR-RES-001, AC-OPS-003 | Running service + one naturally/controlled failing adapter | Registry/API/unrelated adapter becomes unavailable | Failure stays scoped; registry/current reads remain usable |
| M02-OPS-005 | T7 upgrade/recovery | AC-OPS-005 | Real installed path, prior artifact, backup | Upgrade/failure procedure cannot recover registry | Exercised runbook restores compatible state with evidence |
| M02-ARCH-001 | Repository policy | NFR-ARCH-001/002, AC-V1-002 | Actual source/import/table manifest | Private/circular/cross-table dependency accepted | Only approved imports/contracts/table owner present |
| M02-ARCH-002 | Contract/schema policy | FR-AUTH-004 | Actual schemas/contracts/OpenAPI | Credential/content field is accepted or exposed | Prohibited-field scan/review clean |
| M02-ARCH-003 | Surface absence | FR-SAFE-001/002 | Actual ports/routes/OpenAPI | Process-control/routing/logout/default-profile mutation surface exists | Surface contains only approved V1 registry actions |
| M02-ARCH-004 | Portability boundary | NFR-PLAT-001 | Actual source/import graph | Provider/OS branch leaks into domain | Domain is provider/OS agnostic; adapters own details |
| M02-ARCH-005 | Configuration-reference boundary | NFR-ARCH-002 | Actual contracts/schema/import graph | M02 stores/reads another module's settings or secret | Only approved opaque scalar references cross published ports |
| M02-SEC-001 | Security/privacy | NFR-SEC-001/NFR-PRIV-001 | Real DB populated by approved real flows | Secret/content/raw identity/locator appears in rows | Allowlist inspection and secret/content scan clean |
| M02-SEC-002 | Security/privacy | FR-AUTH-004, AC-V1-007 | Actual contracts/OpenAPI/artifacts | Sensitive handle/field serializes | API/event/generated artifacts exclude all prohibited values |
| M02-SEC-003 | Safety | FR-SAFE-002 | Actual source/routes/dependency graph | Agent control/provider logout/default-profile writer reachable | No such dependency/path exists |
| M02-SEC-004 | Test integrity | NFR-TEST-002, AC-TEST-002 | Actual test/dependency repository | Mock/fake/stub/recording/seeded telemetry mechanism exists | Prohibited-double scan and human review clean |
| M02-SEC-005 | Observability privacy | NFR-OBS-001 | Real logs/diagnostic bundle from scenarios | Name/identity/locator/payload/exception data leaks | Only approved safe structured fields remain |
| M02-SEC-006 | Artifact privacy | AC-V1-007 | Real backup/export/test/browser artifacts | Secret/content/private locator/raw identity present | Automated scan plus manual allowlist review clean |
| M02-DOC-001 | Documentation | NFR-DOC-001, AC-V1-001/002 | Actual docs/traceability/contracts | Requirement/test/contract mapping missing | Every owned ID maps to current evidence/status |
| M02-DOC-002 | Documentation | NFR-COMP-001 | Markdown links/status/version references | Broken/stale/contradictory reference passes | Link/version/status validation and human review pass |
| M02-DOC-003 | Runbook integrity | AC-V1-006 | Actual implemented/verified commands only | Invented/unverified command shown as executable | All commands are command-registry verified or explicitly TBD |
| M02-DEP-001 | Dependency/license | NFR-LIC-001, AC-V1-005 | Actual manifests/lock/SBOM/notices | Undocumented M02 package/transitive license enters graph | No new package, or full approved admission evidence is current |

### 9.8 Integrity rules and test-data policy

- No mock, fake, stub, emulator, monkeypatch collaborator, recorded/replayed provider response, demo account, invented provider account, seeded telemetry, placeholder value, in-memory SQLite substitute, direct route call, DOM-only browser substitute, or test-only production path is permitted.
- Pure tests construct domain values only and make no external-boundary claim.
- Organization metadata created in isolated real-stack tests is actual temporary AgentMonitor-owned state produced through production commands and removed through approved cleanup; it is not provider telemetry.
- Provider account/profile/resource DB/API/browser scenarios enroll real owner-controlled subjects through the production discovery/confirmation flow. If unavailable, the scenario is Blocked/Not Run.
- Dynamic identities and counts are not hardcoded. Tests assert safe identity continuity, uniqueness, relationships, source/version, field state, and owner confirmation.
- Test output uses opaque aliases/IDs and sanitized evidence references. It never contains credentials, full identities, labels copied from provider sources, paths, content, or raw payloads.
- Cleanup archives/removes only isolated AgentMonitor test state according to an approved procedure; it never deletes/modifies provider state or the owner's production registry.
- `Failed`, `Blocked`, and `Not Run` remain separate from `Passed` in CI/handoff/release evidence.

### 9.9 Mutation quality target

Mutation testing is admitted only after its dependency gate. The target is 100% killed non-equivalent mutants for critical pure decisions M02-PURE-015..023 (identity association/conflict/profile protection/re-auth continuity) and at least 90% killed non-equivalent mutants across all M02 pure domain policies. Every surviving material mutant blocks completion; exclusions require test-integrity reviewer documentation. Mutation score never substitutes for real DB/API/browser/provider evidence.

### 9.10 Failure, migration, restart, and recovery coverage

The inventory covers malformed/partial/unverified discovery, ambiguity/conflict/wrong account, protected default, authorization/CSRF, stale versions, concurrent associations/reorder, SQLite busy/unavailable, event publication atomicity, service restart, schema upgrade, backup/restore, adapter failure isolation, current/100-account query behavior, retention, and secret/content artifact scanning. Provider outage/auth-expiry/rate-limit behavior is consumed through typed M03 outcomes; live states not naturally available remain Blocked rather than manufactured.

## 10. Implementation increments

Each behavior increment starts only after the plan/contracts on which it depends are approved. Each records a behaviorally meaningful Red using the listed scenario, the minimum Green production change, and post-refactor reruns. A migration, dependency, provider login, or missing test tool is a prerequisite/failure, not Red evidence.

| Increment | Files/area owned | Failing test first | Minimum production change | Refactor/documentation | Exit evidence |
|---|---|---|---|---|---|
| M02-I00 — synchronization only | Plan/contract review; no production code | Contract review findings, not TDD | Freeze CTR-REG-001..010, M0 decisions, permissions, migrations, outbox/locator boundary | Update approved schemas/traceability/ADR decisions | All section 13 implementation blockers resolved; owner approves |
| M02-I01 — organization domain | M02 domain/contracts | M02-PURE-001..005 | Organization values, lifecycle, Ungrouped/order policies, typed outcomes | Domain docs and invariant table | Pure R/G/R and contract review |
| M02-I02 — organization persistence | M02 repository/persistence/allocated migration | M02-DB-001..006 | Real tables/repositories/UoW for org/revision/history/event atomics | Query/index/migration notes | Real file SQLite R/G/R; fresh migration |
| M02-I03 — account identity/lifecycle | M02 domain/application/contracts | M02-PURE-006..011 | Account, membership snapshot, monitoring eligibility, rename/move/archive policies | Consumer semantics and error docs | Pure R/G/R; M04–M07 consumer review |
| M02-I04 — account persistence/use cases | M02 repository/persistence | M02-PURE-026, M02-DB-007..014/028 | Account/history/idempotency/configuration-reference persistence and atomic commands | Query plan/retention/reference-boundary docs | Real DB R/G/R using approved real inputs |
| M02-I05 — provider/install discovery staging | M02 domain/application/persistence | M02-PURE-015/016, M02-DB-019/020 | Provider definitions, installations, candidates, reconcile port with safe field states | M0 evidence references and privacy allowlist | Real discovery outcome R/G/R; malformed result isolation |
| M02-I06 — identity decisions | M02 domain/application/persistence | M02-PURE-017..020, M02-DB-011/021/022 | Identity claims, confirmation/conflict/invalidation policy and ports | Correlation boundary with M06 | Pure and real DB R/G/R; security review |
| M02-I07 — monitoring profiles | M02 domain/application/persistence | M02-PURE-021..023, M02-DB-023/024 | Profile state/protection, sensitive target handle, re-auth reconciliation | M03 workflow and threat notes | Pure/DB R/G/R; no live-success claim yet |
| M02-I08 — account resources | M02 domain/application/persistence | M02-PURE-012..014, M02-DB-015..018 | Resource taxonomy/graph/profile links and query ports | M05 scope/identity notes | Pure/DB R/G/R with real approved resources |
| M02-I09 — change/outbox/retention/health | M02 application/persistence/contracts | M02-PURE-024/025, M02-DB-009/025/027, M02-OPS-004 | Registry revision, safe events, history purge, scope/health ports | M08/consumer operational docs | Atomic event/query/retention R/G/R |
| M02-I10 — P01 contract integration | P01-owned files under separate shared allocation plus M02 contract tests | M02-HTTP-001..012 | Transport mappings only; no P01 business logic | OpenAPI/problem/permission/idempotency docs and generated client source | Real HTTP/OpenAPI/generated-client R/G/R |
| M02-I11 — P02 registry workflows | P02-owned files under separate task/allocation | M02-BROWSER-001..008 | Generated-client organization/account/discovery/profile/resource UI | Accessibility/responsive/user docs | Real built-browser R/G/R with real registry state |
| M02-I12 — live enrollment | Adapter/M03/M04 integration tasks plus M02 application, separately assigned | M02-LIVE-001..006 | Reconcile only Supported/approved scoped provider discovery and owner confirmation | Live matrix/known limitations | Sanitized Passed/Failed/Blocked reports, owner acknowledgement |
| M02-I13 — live re-auth continuity | M03/adapters/P01/P02/M02 integration, separately assigned | M02-LIVE-007..010 | Approved official managed-profile flow and reconciliation | Re-auth/default-profile runbook | Real provider/version evidence; default unchanged |
| M02-I14 — operations/hardening | M02 + M08/DB/deployment tasks by owner | M02-OPS-001..005, M02-SEC-001..006, M02-ARCH-001..004, M02-DOC-001..003, M02-DEP-001 | Backup/restore validation, performance/index fixes, scans/policies; no broadened scope | Complete handoff, traceability, release notes | Independent reviews and every status truthfully recorded |

### 10.1 Ordering and gates

```text
M02-I00
  -> I01 -> I02
  -> I03 -> I04
  -> I05 -> I06
  -> I07 and I08
  -> I09
  -> I10 -> I11
  -> I12 -> I13
  -> I14
```

- I01/I02 and I03/I04 may be prepared by separate assigned agents only after domain/repository contracts and migration ownership are frozen; they may not edit the same contract or migration chain concurrently.
- I05–I08 cannot begin from guessed provider behavior. Each requires the relevant M0/CS contract decision.
- P01 and P02 work is independently assigned; the M02 agent does not edit their modules unless the root explicitly changes ownership.
- M04–M08 may implement against synchronized CTR-REG contracts in parallel. Any semantic gap stops affected work and returns to contract synchronization.
- One agent owns each shared migration revision, registry contract file, OpenAPI source, and generated artifact at a time.
- I12/I13 require owner scheduling. Blocked provider scenarios do not delay unrelated deterministic increments but remain release-visible.

### 10.2 Red-green-refactor evidence per increment

Every increment handoff records:

- requirement/AC, scenario IDs, `registry.v1` and dependency contract versions;
- exact verified command-registry command, UTC timestamp, worktree reference, and sanitized Red reason;
- minimum production change and Green result at the same real boundary;
- broader post-refactor suite/result;
- real DB/HTTP/browser/platform/provider status as applicable;
- every Failed/Blocked/Not Run scenario;
- migration/API/event/generated/dependency/security/privacy/documentation diff;
- cleanup and evidence location, with no secrets/content/provider payloads.

## 11. Documentation outputs

Before M02 completion, the assigned owners produce or update through separately allocated paths:

- `docs/modules/registry.md`: purpose, boundaries, invariants, state machines, ports, DTO/error semantics, consumers, health, limitations, extension points;
- the approved contract register entries for CTR-REG-001..010 and individual requirement traceability;
- generated OpenAPI plus human API guidance for organization/account/discovery/profile/resource workflows;
- data dictionary, table/index ownership, migration metadata, upgrade/recovery/portability notes;
- privacy allowlist for provider identity, candidate, locator, history, event, log, diagnostic, backup, and export fields;
- M0 handoff references and provider-specific known limitations without copying sensitive evidence;
- user guidance for grouping, Ungrouped, rename/move history, monitoring disable/archive, candidate confirmation/conflict, and protected profiles;
- operator procedures listed in section 8, using only verified command-registry commands;
- real test-evidence and live-test reports using repository templates and sanitized references;
- release notes for contract/schema/provider-compatibility/blocked-scenario changes;
- ADR for any breaking contract, profile-locator exception, sensitive identity retention, cross-module FK, or destructive migration decision.

Generated OpenAPI/client/schema/SBOM/notices are updated only through their generators/owners and never manually patched.

## 12. Dependency and license impact

### Current proposal

M02 proposes **no new direct dependency**. Domain/application behavior uses the approved foundation contract primitives and Python standard library. Persistence uses the centrally admitted SQLAlchemy/Alembic stack through adapters. HTTP/UI/provider behavior remains in P01/P02/M03/adapters and may not pull their dependencies into M02.

Unicode normalization/case folding uses the supported Python standard library unless a demonstrated requirement proves it insufficient. Identifier/fingerprint cryptography uses an already approved foundation/security primitive through a port; M02 does not implement cryptography or add a convenience package.

### Admission rule

If a package becomes necessary, implementation stops until an admission record covers exact purpose, alternatives, upstream identity/license, direct/transitive licenses, maintenance/security/provenance, supported runtimes/platforms, binaries/install scripts, telemetry/network behavior, size/performance, pin/update/removal, SBOM/notices, reviewer/date. Copyleft/custom/unclear licenses require explicit owner approval. No manifest or lockfile changes occur under this Draft plan.

## 13. Risks, unresolved decisions, and synchronization register

### 13.1 Module risks

| ID | Risk/question | Likelihood/impact | Mitigation/evidence | Owner | Trigger/deadline | Status |
|---|---|---|---|---|---|---|
| M02-R01 | Provider stable identity is absent, reused, scoped unexpectedly, or personal | High/Critical | M0 exact scope/lifetime/privacy evidence; owner confirmation; unresolved state | M03/M02/security | Before CTR-REG-002/006 approval | Open; links R-003/R-005 |
| M02-R02 | Account/resource/profile concepts are collapsed or double-counted | Medium/Major | Separate aggregates/IDs, M0 relationship maps, consumer review | M02/M05 | Before data schema approval | Open; links R-014 |
| M02-R03 | Discovery label/path heuristics enroll wrong account | High/Critical | No label/path auto-match; candidate review; uniqueness/conflict transaction | M02/M03 | Before I05 | Open; links R-003/R-021 |
| M02-R04 | Protected default profile is misidentified or becomes writable | Low/Critical | M0 proof, monotonic protection, prepare-before-adapter check, live non-modification | M02/adapters/security | Before I07/live auth | Open; links R-004 |
| M02-R05 | Re-auth creates duplicate/wrong identity or loses history | Medium/Critical | Expected identity, atomic reconcile, wrong-account state, real per-provider evidence | M02/M03/adapters | Before I13 | Open; links R-021 |
| M02-R06 | Opaque locator or identity leaks through serialization/artifacts | Medium/Critical | sensitive handle type, field allowlists, scans, no generic serialization | M02/P01/M08/security | Every increment/release | Open; links R-005/R-020 |
| M02-R07 | Registry revision/outbox transaction couples modules or loses events | Medium/Major | synchronize outbox ownership, atomic real DB tests, no foreign table writes | Integration/DB/M02 | Before I02/I09 | Open |
| M02-R08 | SQLite constraints/indexes impede portability or concurrency | Medium/Major | repository seam, portable schema review, real lock/query-plan tests | DB/M02 | Before migrations approved | Open; links R-011/R-012 |
| M02-R09 | 365-day owner-facing rename/move history leaks through events/logs/exports or grows without bound | Medium/Major | protected bounded history, authorization, restricted export, redacted event/log projections, retention/indexes | M02/M08/privacy | Before history schema approval | Open |
| M02-R10 | 100-account performance cannot be tested without invented accounts | Medium/Major | owner approves compliant AgentMonitor-owned structural load or evidence stays Blocked | Test/integration/owner | Before V1 performance claim | Open; no fake claim |
| M02-R11 | macOS/provider paths leak into registry domain | Medium/Major | opaque handles, boundary checks, real macOS remains Blocked if unavailable | Platform/M02 | Before platform support claim | Open; links R-023 |
| M02-R12 | Provider terms/policy prohibit candidate identity source | Medium/Critical | official-first discovery, no private/browser source without separate review | Product/security/M03 | At source review | Open; links R-024 |

### 13.2 Approval-blocking decisions

The following decisions must be recorded by the named contract owners. Defaults in this draft are proposals, not authority to implement:

1. **M02-SYNC-001:** exact safe stable identity scheme/scope/lifetime/privacy classification for each first provider/account class. Owner: M0/M03/security.
2. **M02-SYNC-002:** whether an external subject is stored directly, as a keyed fingerprint, or not stored, including rotation/migration behavior. Owner: security/M03/DB.
3. **M02-SYNC-003:** safe installation identity/dedup semantics and whether a private locator is required. Owner: M0/M03/platform.
4. **M02-SYNC-004:** normalized resource kinds and provider-specific extension rule supported by actual M0 findings. Owner: M02/M03/M05.
5. **M02-SYNC-005:** `IdentityCorrelationDecisionV1` versus M06 `SessionCorrelationDecisionV1` ownership and reference direction. Owner: M02/M06/root.
6. **M02-SYNC-006:** exact profile purpose values and profile-to-resource multiplicity. Owner: M02/M03/M04/M05.
7. **M02-SYNC-007:** default-profile detection proof, monotonic protection, and no public unprotect operation. Owner: M0/adapters/security/owner.
8. **M02-SYNC-008:** managed-profile isolation and official re-auth flow eligibility for each provider/version. Owner: M0/M03/adapters/owner.
9. **M02-SYNC-009:** preparation/result DTOs and orchestration split among M02, M03, M04, and P01. Owner: those producers/consumers.
10. **M02-SYNC-010:** whether account friendly names are globally unique after normalization; archived-name reuse semantics. Owner: owner/P01/P02/M02.
11. **M02-SYNC-011:** organization archive requires no active members versus explicit atomic move-to-Ungrouped option. Draft proposes the former. Owner: owner/P01/P02.
12. **M02-SYNC-012:** exact account lifecycle/identity states and monitoring preference versus effective eligibility contract. Owner: M02/M04/P01/P02.
13. **M02-SYNC-013:** `RegistryFieldStateV1` vocabulary and unknown/withheld/unsupported/unavailable transport mapping. Owner: M02/M03/P01/P02.
14. **M02-SYNC-014:** global registry revision consistency semantics and whether consumers can request a minimum revision. Owner: M02/M04–M08/DB.
15. **M02-SYNC-015:** transactional outbox table/port/dispatcher ownership and atomicity. Owner: foundation/integration/DB/all event consumers.
16. **M02-SYNC-016:** command idempotency receipt lifetime and exact replay outcome. Draft proposes 365 days. Owner: M02/P01/M08.
17. **M02-SYNC-017:** protected old/new friendly-name and membership history, 365-day retention, authorization, export behavior, and event/log exclusion. Owner: owner/privacy/M08/P01/P02.
18. **M02-SYNC-018:** M01 permission vocabulary for read/write accounts, re-auth, internal reconciliation, and history. Owner: M01/P01/M02.
19. **M02-SYNC-019:** P01 route/action/ETag/problem/pagination mapping and P02 workflow review. Owner: P01/P02/M02.
20. **M02-SYNC-020:** centrally allocated M02 migration revisions, cross-module FK prohibition, backup/recovery prerequisites. Owner: DB/integration/M08.
21. **M02-SYNC-021:** compliant method for NFR-PERF-001 100-account structural load without invented provider accounts or fake provider claims. Owner: owner/test/integration.
22. **M02-SYNC-022:** registry health disclosure, consistency checks, and export allowlist. Owner: M02/M08/P01/security.
23. **M02-SYNC-023:** exact string/page/description/label bounds as versioned API/domain constraints. Owner: M02/P01/P02/security.
24. **M02-SYNC-024:** whether any decision requires an ADR, particularly sensitive identity representation, locator handling, or outbox ownership. Owner: architecture/root.
25. **M02-SYNC-025:** approved account-configuration reference namespaces/kinds, multiplicity, owner-port validation, invalidation, and dangling-reference recovery without cross-module FKs. Owner: M02/configuration owners/DB/root.

Any unresolved item that permits materially different implementations keeps Definition of Ready unchecked.

## 14. Delivery, compatibility, migration, and rollback

### 14.1 Delivery order

1. Complete and approve M0 identity/resource/profile handoffs for the target vertical slice.
2. Synchronize CTR-COMMON, CTR-IAM permission, CTR-PROV, CTR-REG, CTR-RUN correlation, CTR-DB, CTR-OPS health, and P01/P02 transport expectations.
3. Approve M02 plan version and `registry.v1`; allocate paths/migrations/shared artifacts.
4. Implement I01–I09 using R/G/R and real SQLite where claimed.
5. Integrate real HTTP/OpenAPI/generated client, then built UI.
6. Enroll real accounts provider by provider only through approved discovery/confirmation flows.
7. Run separately approved managed-profile re-auth scenarios.
8. Exercise backup/restore/upgrade/failure/performance/security/privacy/documentation gates.
9. Update traceability and release evidence; do not mark M02 complete while mandatory scenarios are Failed/Blocked/Not Run.

### 14.2 Compatibility promise

- CTR-REG contracts begin at V1 after approval. Adding an optional field with safe documented default/field-state may be compatible; changing identity scope, null meaning, lifecycle, resource kind meaning, locator disclosure, evidence class, event delivery/order, unit/time, or ID semantics is breaking.
- Unknown-tolerant enum expansion is compatible only where every consumer proves unknown handling.
- Removing/renaming fields/ports/change kinds or reinterpreting owner confirmation requires V2, an ADR, migration/consumer plan, and compatibility window.
- Database evolution uses expand → optional backfill/reconcile → switch → contract. Older supported binaries must not read reinterpreted identity/resource rows.
- M0 findings that invalidate an unimplemented proposal revise this Draft. Findings that invalidate implemented behavior require a change plan and possibly a new major.

### 14.3 Exposure and rollout

- No provider/account UI is exposed before real source-to-registry evidence and P01/P02 truthful-state review.
- Unsupported/unavailable features remain visible as such; feature hiding cannot imply success.
- Account discovery may be enabled per synchronized provider/version. A failed provider is isolated and does not disable registry reads for others.
- Monitoring remains disabled for pending/conflicting identity until explicit safe resolution.
- No migration or rollout changes provider profiles or running agents.

### 14.4 Rollback and recovery

- Application rollback is permitted only within the documented schema compatibility range.
- Additive initial schema can remain unused if the new module is disabled, provided the prior binary safely ignores it.
- After owner data exists, never drop/recreate registry tables as rollback. Preserve the database and recover via verified backup/prior binary or approved forward fix.
- A failed provider enrollment/re-auth rolls back only the pending AgentMonitor registry transaction; it does not attempt to undo or mutate provider state. Any provider-side partial state follows the provider adapter's approved incident/runbook.
- Wrong-account detection preserves the prior registry association and disables the affected profile path pending review.
- Post-recovery checks include schema compatibility, constraint/identity/resource consistency, account/group/history continuity, event/outbox state, login/API/UI access, and one safe read-only provider verification when approved.

### 14.5 Handoff contents

Each implementation handoff uses the repository templates and states:

- exact requirements and acceptance criteria;
- M02 plan/module version and CTR-REG/common/consumed versions;
- files, migrations, generated artifacts, and ownership;
- test IDs with Red/Green/refactor commands/results and boundary status;
- real provider/account/version evidence or every Blocked/Not Run item;
- API/event/database/config compatibility and migration/recovery results;
- security/privacy/secret scan, dependency/license, operations, and documentation impact;
- risks/defects and exact next integration step;
- declaration that no secret/content was exposed, no prohibited test double was used, no default profile/running agent was changed, and no unassigned path/external state was modified.

## 15. Definition of Ready

- [ ] Owner approves this plan's outcomes, non-goals, organization archive, friendly-name, history, and enrollment interpretations.
- [ ] Required M0 scenarios have sanitized reviewed decisions for the first target provider/version/account class.
- [ ] M02 module boundary and allowed/forbidden paths/imports are approved.
- [ ] CTR-COMMON-001/002/006, CTR-FND-004/006, CTR-DB-002, and required M01 permissions are approved.
- [ ] CTR-PROV-002/005/006/007 inputs used by the first increment are synchronized with M02.
- [ ] CTR-REG-001..010 fields, unknown/null rules, commands, errors, events, authorization, idempotency, recovery, and compatibility are synchronized with all known consumers.
- [ ] M02/M06 identity-versus-runtime-correlation ownership is resolved.
- [ ] Sensitive locator and external-identity representation have security/privacy approval.
- [ ] Default-profile protection and managed-profile capability gates are evidence-backed.
- [ ] Registry table/index/retention/outbox ownership and centrally allocated migration sequence are approved.
- [ ] Account-configuration reference ownership, namespaces, validation, and recovery are synchronized without copying another module's settings.
- [ ] Every test scenario has a valid real boundary, cleanup/evidence path, and expected behavioral Red; no prohibited substitute is required.
- [ ] Owner participation and real accounts are scheduled for applicable live scenarios; unavailable scenarios are predeclared Blocked, not simulated.
- [ ] Dependency/tool versions needed to execute tests are admitted; M02 adds no unreviewed package.
- [ ] Backup/restore/upgrade/recovery and PostgreSQL-portability reviews are approved.
- [ ] P01/P02 route/generated-client/workflow ownership is allocated without overlapping files.
- [ ] No unresolved M02-SYNC item permits materially different implementation.
- [ ] Root/integration steward confirms worktree/path/migration/shared-file ownership immediately before implementation.

## 16. Approval record

| Reviewer | Decision | Conditions/findings | Date | Plan/contract version |
|---|---|---|---|---|
| Owner | Pending | Product behavior and live-account coordination | — | Plan 0.2.0-draft / registry.v1 proposed |
| Root/integration steward | Pending | Boundary, synchronization, path/migration allocation | — | — |
| M03/M04/M05/M06/M07/M08 consumers | Pending | Contract semantics and dependency direction | — | — |
| P01/P02 owners | Pending | Transport/generated-client/workflow compatibility | — | — |
| Persistence/migration reviewer | Pending | Tables/indexes/transactions/migration/recovery/portability | — | — |
| Security/privacy reviewer | Pending | Identity/locator/default-profile/data minimization | — | — |
| Test-integrity reviewer | Pending | Scenario validity, R/G/R, no prohibited doubles | — | — |
| Dependency/license reviewer | Pending | No M02 addition or approved admission | — | — |

Implementation remains unauthorized while this plan is Draft, any required contract is Concept/Proposed rather than Approved for the increment, any applicable M0 input is unresolved, or any Definition-of-Ready item remains unchecked.
