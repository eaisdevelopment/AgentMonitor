# Module plan: M04 — Collection control

- Status: **Draft — approval pending; implementation is not authorized**
- Plan version: 0.2.0-draft
- Proposed module contract: `collection-control.v1` (unapproved)
- Owner: M04 collection-control implementation role (unassigned)
- Required reviewers: root/integration steward, M02 Registry owner, M03 Provider-system owner, M05 Capacity owner, M06 Runtime-observation owner, M07 Alerting owner, M08 Operations owner, P01 API owner, persistence/migration owner, security reviewer, test-integrity reviewer, dependency/license reviewer
- Requirements: FR-COL-001..008; supporting FR-AUTH-001, FR-HIST-001/003/005, FR-OPS-002/005/006, FR-SAFE-001/002; NFR-ARCH-001/002, NFR-API-001/002, NFR-DATA-001, NFR-TEST-001/002, NFR-SEC-001, NFR-PRIV-001/002, NFR-DOC-001, NFR-LIC-001, NFR-PLAT-001, NFR-PERF-001, NFR-RES-001, NFR-OBS-001, NFR-COMP-001
- Acceptance criteria: AC-V1-001..008, AC-LIVE-004/005/007, AC-UI-002/005/006, AC-ALERT-003, AC-HIST-001, AC-OPS-002/003/005/006, AC-TEST-001..006
- Primary project risks: R-001, R-002, R-004, R-005, R-006, R-007, R-009, R-010, R-011, R-018, R-019, R-023, R-024
- Dependencies: accepted ADRs 0001, 0003, 0004, 0005, 0006, 0007, 0008, 0009, 0010, and 0011; approved M0 M04 handoff; synchronized common/M02/M03/M05/M06/M07/M08 contracts; repository foundation; centrally allocated migration chain; persistence adapter; P01 transport mapping
- Target milestone: M2 observation domains and collection; synchronization gate CS-2
- Approved by/date: pending

This plan is governed by the [product requirements](../../../product/requirements.md), [V1 acceptance criteria](../../../product/v1-acceptance-criteria.md), [module boundaries](../../../architecture/modules.md), [provider-adapter contract](../../../architecture/provider-adapter-contract.md), [data model](../../../architecture/data-model.md), [security architecture](../../../architecture/security.md), [API standards](../../../api/api-standards.md), [testing strategy](../../../engineering/testing-strategy.md), [SDLC](../../../engineering/sdlc.md), [M0 execution plan](../../discovery/m0-execution-plan.md), and [proposed contract register](../../contract-register.md). External constraints in this draft are contract requirements, not claims about current providers. Values that depend on provider behavior remain blocked until the M0 handoff supplies evidence for the exact source, version, account class, and credential role.

## CS-1 Draft-alignment addendum

This `0.2.0-draft` revision adopts contract-baseline `0.2.0` and the parallel-ownership manifest as its concrete CS-1 review position. It remains Draft; M0/provider evidence and every planned scenario remain `Not Run`.

- M04 is the sole semantic producer of CTR-COL-001..007. CTR-COL-006 `CollectionOutcomeCommitPortV1` is no longer an unallocated private proposal: M04 defines the typed commit request and receipt protocol, while M05 and M06 implement their separate payload commits. CTR-COL-007 `CollectorHealthChangedAndCurrentAlertInputsV1` publishes ordered current health generations and explicit active/recovery transitions for M07/M08.
- A collection run cannot become completed until the appropriate M05/M06 production commit returns a durable receipt for the same run ID, target generation, payload schema/version, and canonical digest. M04 commits the run terminal state, opaque observation references, schedule/lease changes, and its completion/failure outbox atomically after receipt validation. Repeated identical commits return the same receipt; a different digest conflicts and preserves the first commit. M04 never writes or queries M05/M06 tables.
- Provider `reauthentication_required` is a no-time-retry state. M04 consumes the newer verified CTR-REG-010 authentication-health generation to resume exactly one eligible run; a later generic success, stale event, silence, or dashboard authentication change cannot clear the block. CTR-COL-007 carries the explicit collection recovery generation M07 needs.
- All collection DTOs use CTR-COMMON-007 and all M04 events use CTR-COMMON-006 plus CTR-EVT-001 outbox/receipt/checkpoint/replay semantics. M04 implements M08-owned CTR-OPS-006 and CTR-OPS-007 participant ports with bounded, table-private behavior.
- M04 adopts CTR-EVT-TOPOLOGY-001: it owns `collection_event_outbox` and any producer-side `collection_event_delivery` rows; consumers own processing receipts/checkpoints. The shared dispatcher uses only M04's published event-storage port, never cross-module SQL.
- The V1 public contract file is `backend/src/agentmonitor/contracts/collection_control_v1.py`; SQLite implementation files are only under `backend/src/agentmonitor/adapters/persistence/collection_control/sqlite/**`. M04 owns `collection_` tables and `v1_0400..v1_0499`; PLAN-DB serializes the migration head.
- Alignment is verified by existing scenarios M04-PURE-011/014/020/021/027/028, M04-DB-014..017, M04-DB-024/025, M04-HTTP-007, M04-LIVE-006/009/012/014, M04-OPS-001..010, and M04-ARCH-001..004. All are presently `Not Run`.

## 1. Outcome and boundaries

### Outcome

M04 turns approved, enabled collection targets into bounded read-only work without over-polling a provider or allowing one failed collector to stop unrelated collection or the dashboard. It durably schedules active targets at approximately one-minute cadence and idle targets at approximately five-minute cadence by default, accepts coalesced manual and observable-event refreshes, acquires fenced leases, enforces source-specific request/rate/cost and concurrency budgets, invokes only compatible read-only provider/platform ports, and records a complete sanitized lifecycle for each run.

The outcome is measurable when:

- every enabled target/capability has one durable schedule with a visible next-eligible time and collection state;
- active and idle cadence decisions are based on a versioned activity signal rather than M04 guessing agent state;
- manual/event refresh can advance eligible work but cannot bypass authentication blocks, provider rate limits, unknown cost, protected-profile rules, source approval, deadlines, or concurrency limits;
- concurrent schedulers cannot dispatch the same due generation twice, and a stale lease holder cannot commit a terminal result;
- duplicate manual requests and repeated internal events return or join the same pending/running work under documented idempotency rules;
- provider outcomes remain distinct, including success, partial, unsupported, unverified version, authentication required, authorization insufficient, rate limited, unavailable, invalid data, deadline exceeded, blocked user action, and internal adapter error;
- authentication/user-action failures are never retried until a later verified recovery signal changes the block generation;
- completed observation payloads are committed through the owning M05/M06 port; M04 stores only opaque committed observation references and never owns quota/session meaning;
- collection-run history, warnings, affected capabilities, provenance summary, duration, retry decision, and sanitized errors remain queryable for 365 days;
- restart, crash, downstream failure, shutdown, and clock movement recover without duplicated unsafe calls, invented current values, or process/profile mutation;
- browser closure does not stop the scheduler, and stopping AgentMonitor never signals, terminates, pauses, restarts, or injects input into a monitored agent;
- real SQLite, real application/service, real provider/platform adapters, and owner-coordinated live accounts demonstrate the boundary claims without mocks, fakes, stubs, emulators, recordings, demo accounts, seeded telemetry, or placeholder values.

### In scope

- Target schedule projection from synchronized registry/provider capability contracts.
- Active, idle, and unknown activity classes and their default cadence policy.
- Manual, scheduled, observable-request, observable-error, authentication-recovered, registry-change, and re-auth-verification trigger intake where an approved producer can supply them.
- Durable request coalescing and idempotency.
- Due selection, deterministic schedule jitter, fairness, queue bounds, deadlines, and admission decisions.
- Per-target exclusivity, global/provider/account/profile/capability concurrency limits, persistent fenced leases, and in-process task supervision.
- Source-specific request-count, rate, retry, and nonzero/unknown-cost admission budgets derived from M0-approved policy.
- Provider/platform dispatch through versioned ports and capability negotiation; no concrete adapter imports.
- Outcome classification, no-retry authentication handling, retry/backoff scheduling, partial-result handling, and unsupported/unverified suspension.
- Idempotent handoff of typed safe results to M05/M06-owned commit ports and opaque observation-reference receipt.
- Collection run/request/lease/budget/outbox state, migrations, repositories, retention, health, diagnostics, and recovery.
- `CollectionRequestV1`, `CollectionRunViewV1`, `CollectionCompletedV1`, `CollectionFailedV1`, and `CollectorHealthV1`, plus the additional result-commit seam proposed in section 4.
- Cooperative cancellation of AgentMonitor-owned collection work during service shutdown or deadline expiry.

### Out of scope

- Provider-specific API, CLI, filesystem, parsing, authentication, or version logic. A01–A03 and A04 own those adapters.
- Account identity, organizations, resources, installations, profile protection, monitoring enablement, or re-authentication workflows. M02/M03 own them.
- Quota, budget, cost, token, process, session, health-normalization, forecast, stall, or alert business interpretation. M05–M07 own those meanings.
- Storing raw provider responses, CLI output, local provider-file content, observation payload copies, prompts, responses, tool activity, source code, arbitrary environment values, or credentials.
- Starting login, logout, account switching, profile creation, re-authentication, or blindly retrying authentication failures.
- Sending provider requests directly from an HTTP handler; manual refresh only creates/joins background work.
- Killing, restarting, pausing, signaling, attaching to, routing, switching credentials inside, or injecting input into a running agent.
- General-purpose worker queues, distributed scheduling, multi-host leases, remote collectors, or exactly-once delivery. The contracts preserve a future separate-worker seam without pretending V1 is distributed.
- Email, native desktop, messenger delivery, or near-real-time browser streaming.
- Final operator command names. They remain `TBD` until implemented and verified.

### Ownership

M04 owns:

- `CollectionTargetKey`, `CollectionSchedule`, `ActivityClass`, `CollectionTrigger`, `CollectionRequest`, `CollectionRun`, `CollectionLease`, `DispatchAdmission`, `RequestBudget`, `RetryDisposition`, `BackoffState`, `CollectorHealth`, and M04 event-outbox concepts;
- the invariant that one target/capability has at most one active fenced run generation;
- the scheduling, coalescing, fairness, admission, lease, deadline, retry, backoff, and shutdown policies;
- all `collection_*` tables, constraints, indexes, repositories, and centrally allocated M04 migration revisions;
- its module configuration definitions and validation, but not global configuration loading;
- safe run/error/warning vocabularies and collection-health calculation;
- M04 ports, views, events, compatibility promises, and event-stream ordering rules after synchronization;
- collection-specific module documentation, test matrix, health/diagnostic definitions, and recovery instructions.

M04 does not own the validity of an account/profile/capability, adapter implementation, typed observation contents, observation persistence, capacity/runtime freshness, or alert lifecycle. Those facts enter or leave through synchronized contracts.

### Allowed paths for a future implementation agent

These paths are proposed and require root allocation before implementation:

```text
backend/src/agentmonitor/modules/collection_control/**
backend/src/agentmonitor/adapters/persistence/collection_control/sqlite/**
backend/tests/collection_control/**
backend/tests/integration/collection_control/**
docs/modules/collection-control.md
docs/test-evidence/collection-control/**       # sanitized records only, if approved
```

The following shared paths require an explicit per-change allocation:

```text
backend/src/agentmonitor/contracts/collection_control_v1.py
backend/migrations/versions/<allocated-collection-revision>.py
backend/src/agentmonitor/composition/**
backend/src/agentmonitor/contracts/provider_system_v1.py       # M03 owner only
backend/src/agentmonitor/contracts/registry_v1.py              # M02 owner only
backend/src/agentmonitor/contracts/capacity_v1.py              # M05 owner only
backend/src/agentmonitor/contracts/runtime_observation_v1.py   # M06 owner only
openapi/generated artifacts                                   # P01 owner only
configuration registry, dependency manifests, and lockfiles
```

### Allowed and forbidden dependencies

M04 domain code may import only Python standard-library types and approved stable common/M04 contract primitives. M04 application code may consume published M01/M02/M03/M05/M06/M08 contracts through typed ports. Persistence implementations may import admitted SQLAlchemy/Alembic packages and M04 repository ports. Composition injects compatible provider/platform executors and result sinks.

The M04 implementation agent must not:

- import another module's internals, ORM models, repositories, tables, migrations, or private types;
- import concrete Claude, Codex, Ollama, Linux, or macOS adapters, provider SDKs, CLI packages, filesystem/process APIs, FastAPI, React, or UI code into domain/application logic;
- query M02/M05/M06/M07/M08 tables, duplicate their views, or persist their observation payloads;
- invoke provider operations not declared compatible/read-only by the M03 capability contract;
- read credentials, provider profile contents, `.env`, arbitrary environment variables, prompts/responses/tools/source, or raw output;
- create a generic worker/framework abstraction outside M04 or a shared `utils` package;
- add an in-process fake adapter, fake clock, fake repository, simulated provider, replay response, test-only endpoint, or seeded telemetry to make tests run;
- edit provider, platform, API, UI, migration-chain, generated, dependency, or configuration-registry shared files without explicit allocation.

## 2. Requirements and traceability

| Requirement/AC | Planned behavior | Proposed contract | Test/scenario IDs | Evidence gate |
|---|---|---|---|---|
| FR-COL-001 | Active targets use a 60-second default and idle/unknown targets use a 300-second default, adjusted only by bounded jitter and stricter source constraints | `CollectionPolicyV1`, `CollectionScheduleV1` | M04-PURE-001..005, M04-DB-002/003, M04-LIVE-001/002 | Pure policy, real DB schedule, real provider elapsed observation |
| FR-COL-002 | Accepted manual/observable-event triggers advance eligible work and coalesce with pending/running work without bypassing safety gates | CTR-COL-001, `NotifyCollectionTriggerV1` | M04-PURE-006/007, M04-DB-007..010, M04-HTTP-001..004, M04-LIVE-003/004 | Real persistence/HTTP and supported live event source |
| FR-COL-003 | Typed outcome-to-retry rules apply source-approved backoff/jitter/Retry-After and suspend non-retryable/auth cases | `RetryDispositionV1`, CTR-COL-004 | M04-PURE-008..014, M04-DB-013/014, M04-LIVE-005..008 | Pure mapping plus naturally available live outcomes |
| FR-COL-004 | Run/result contracts carry source, observed/collected times, versions, freshness inputs, precision/confidence references without M04 inventing them | CTR-COL-002/003 and CTR-COMMON-004 | M04-PURE-015, M04-DB-015/016, M04-LIVE-009 | Contract checks, DB inspection, live observation reconciliation |
| FR-COL-005 | Every attempted run records status, timing, warnings, safe error, affected capabilities, and retry/backoff decision | CTR-COL-002/004 | M04-PURE-016/017, M04-DB-011/012/017, M04-HTTP-005 | Real DB/run query via real service |
| FR-COL-006 | Unsupported, unavailable, unverified, disabled, auth-blocked, and unknown-cost conditions are explicit and not rendered as success/current | CTR-COL-002/004/005 | M04-PURE-010..013/018, M04-DB-018, M04-HTTP-006, M04-LIVE-006/010 | Outcome/health contracts plus live manifests |
| FR-COL-007 | Dispatch admits only the active M0-approved source; no silent downgrade to weaker sources | CTR-PROV-002/003 and `DispatchAdmissionV1` | M04-PURE-019, M04-LIVE-011, M04-ARCH-002 | Pure source policy and real adapter manifest/result |
| FR-COL-008 | Last stored observation is never presented by M04 as a live fallback; a failed run records failure while consumers retain stale data under their own policy | CTR-COL-002/004/005 | M04-PURE-020, M04-DB-019, M04-HTTP-007 | Real failed/naturally blocked run and API view |
| FR-AUTH-001 | Authentication-required/revoked/wrong/unknown outcomes suspend automatic retries; only verified recovery generation clears the block | CTR-PROV-006, CTR-COL-004/005 | M04-PURE-011/021, M04-DB-014/018, M04-LIVE-006/012 | Real auth state where naturally available; otherwise Blocked |
| FR-HIST-001/003/005 | Run/request/collector-event history uses UTC, retains 365 days, and purges in audited bounded batches | `PurgeCollectionHistoryV1` | M04-PURE-022, M04-DB-020..022 | Pure cutoff plus real SQLite deletion/restart |
| FR-OPS-002/005/006 | M04 publishes safe health/version/run diagnostics without provider payloads or secrets | CTR-COL-005, CTR-OPS-006 | M04-OPS-001..004, M04-SEC-001/002 | Real service/log/diagnostic inspection |
| FR-SAFE-001/002 | Refresh is the only exposed provider action; cancellation targets only AgentMonitor-owned collection execution, never monitored agents | CTR-COL-001 and executor context | M04-PURE-023, M04-ARCH-001/003, M04-OPS-005 | Contract/import/real shutdown inspection |
| NFR-ARCH-001/002 | Framework-free isolated module, typed V1 contracts, one owner for state/tables, no circular imports | `collection-control.v1` | M04-ARCH-001..004 | Automated boundary/contract ownership checks |
| NFR-API-001/002 | P01 maps background refresh/query to `/api/v1` and generated UI client without embedding collection rules | CTR-API-001 and CTR-COL-001/002/005 | M04-HTTP-001..007, M04-ARCH-004 | Real HTTP/OpenAPI/generated-client checks |
| NFR-DATA-001 | Real file SQLite, short transactions, fenced leases, bounded queries, and portable repository contracts | M04 repository ports/CTR-DB-002 | M04-DB-001..025 | Fresh migration, concurrency, restart, query-plan evidence |
| NFR-TEST-001/002; AC-TEST-001..006 | Meaningful Red/Green/refactor at each claimed real boundary; unavailable live states remain Blocked | evidence records | All M04 scenarios | Independent test-integrity review |
| NFR-SEC-001 | Read-only capability admission, opaque profile refs, bounded manual abuse, sanitized errors, safe cancellation | dispatch/executor contracts | M04-SEC-001..008 | Security review plus real artifact/process inspection |
| NFR-PRIV-001/002 | Store collection metadata only; no raw result/content/credential values and no external product telemetry | persistence/log allowlists | M04-SEC-001..004/009 | DB/WAL/log/network/diagnostic inspection |
| NFR-DOC-001 | Contracts, scheduler policy, recovery, evidence, limitations, and runbook are maintained | documentation outputs | M04-DOC-001 | Documentation/link/runbook review |
| NFR-LIC-001 | Any scheduler/concurrency/test dependency passes admission before import | dependency record | M04-DEP-001 | License/security/SBOM gate |
| NFR-PLAT-001 | Core scheduling is platform-neutral; actual provider/platform work is injected through contracts | executor ports | M04-ARCH-002, M04-OPS-006 | Linux real evidence; macOS status explicit |
| NFR-PERF-001 | Indexed due selection and bounded workers support 100 schedule targets without redesign; no fake provider claim | schedule/repository policy | M04-PERF-001..004 | Real AgentMonitor-owned load + live provider limits separately |
| NFR-RES-001 | One adapter, result sink, event consumer, or run failure is isolated; unrelated scheduling/API remain available | supervisor/outbox contracts | M04-DB-023..025, M04-LIVE-013, M04-OPS-007 | Real component/provider failure evidence |
| NFR-OBS-001 | Structured correlation-aware logs and health use safe codes/IDs only | CTR-COL-002/005 | M04-SEC-002/005, M04-OPS-003 | Real log/diagnostic review |
| NFR-COMP-001 | Collection DTOs/events/database revisions are versioned; incompatible semantics require major/ADR | CTR-COL-001..006 | M04-ARCH-003/004, M04-DB-001 | Compatibility and migration gates |
| AC-V1-001 | M04 requirements, contracts, scenarios, and sanitized evidence update individual release traceability | `test-evidence-summary.v1` | M04-DOC-001, all executed M04 scenarios | Integration traceability review |
| AC-V1-002 | M04 cannot enter implementation until this plan, its boundaries, contracts, tests, and operations are approved | `collection-control.v1` | M04-ARCH-001..004, M04-DOC-001 | Plan/contract approval record |
| AC-V1-003 | Collection request/run/health routes conform to generated OpenAPI and the generated client | CTR-COL-001/002/005, CTR-API-001 | M04-HTTP-001..007, M04-ARCH-004 | Running OpenAPI compatibility/client gate |
| AC-V1-004 | Fresh and supported upgrade migrations, recovery, and safe rollback cover every M04 table | M04 schema revisions | M04-DB-001, M04-OPS-009/010 | Real SQLite migration/recovery evidence |
| AC-V1-005 | Security, privacy, dependency, and threat reviews have no unresolved M04 release blocker | dispatch/data/dependency policies | M04-SEC-001..009, M04-DEP-001 | Independent review and artifact scans |
| AC-V1-006 | Developer/operator/recovery/diagnostic/upgrade documentation is current and exercised | documentation outputs | M04-DOC-001, M04-OPS-001..010 | Documentation and runbook exercise |
| AC-V1-007/AC-V1-008 | No secret/content enters artifacts and no simulated provider/account/telemetry evidence is represented as real | evidence/data allowlists | M04-SEC-001..009, all M04-LIVE scenarios | Secret/content scan and test-integrity review |
| AC-LIVE-004/005/007 | Every supported adapter executes the M04 lifecycle; values reconcile downstream; rare live states remain truthfully classified | synchronized adapter matrices | M04-LIVE-001..015 | T6 owner-coordinated evidence |
| AC-UI-002/005/006 | Real run/health/freshness states are available to UI, including partial/stale/blocked/unsupported explanations | CTR-COL-002/005 via P01 | M04-HTTP-005..007, M04-BROWSER-001/002 | Running stack and built browser |
| AC-ALERT-003 | Collector failure, stale, re-authentication-required, and recovery facts reach M07 without polling noise | CTR-COL-003/004/005 | M04-DB-015..017/024, M04-LIVE-006/014 | Real outbox/delivery and live condition |
| AC-HIST-001 | A real provider result is committed to M05/M06, linked to a run, and queryable through history | CTR-COL-003/006 | M04-LIVE-009, M04-HTTP-007 | Full real collection-to-history path |
| AC-OPS-002 | Browser close does not stop scheduler/background collection | native service/M04 lifecycle | M04-OPS-008 | Real installed service and browser closure |
| AC-OPS-003 | A real adapter failure does not interrupt other adapters or API/UI | isolation contract | M04-LIVE-013 | Naturally/safely available real failure; no simulation |
| AC-OPS-005 | Restart/upgrade/failure-recovery procedures preserve schedules, histories, and safe lease recovery | persistence/lifecycle contracts | M04-OPS-005/009/010 | Real installed-service exercises |
| AC-OPS-006 | Dispatch stays within M0-approved provider rate/request/cost/concurrency constraints | budget/admission contracts | M04-PURE-024/025, M04-DB-005/006, M04-LIVE-015 | Policy evidence plus real request ledger/provider comparison |
| AC-TEST-001/AC-TEST-002 | Every behavior has recorded Red/Green/refactor evidence and the repository contains no prohibited doubles/provider fixtures | evidence policy | All M04 scenarios, M04-ARCH-001 | Test-evidence and prohibited-pattern review |
| AC-TEST-003 | Required pure, real SQLite, real HTTP, built-browser, platform, and provider boundaries execute separately and truthfully | layer-specific contracts | M04-PURE-001..028, M04-DB-001..028, M04-HTTP-001..007, M04-BROWSER-001/002, M04-LIVE-001..015, M04-OPS-001..010 | Per-layer evidence summary |
| AC-TEST-004 | Live reports identify opaque aliases, exact versions/times, request-cost budgets, safety checks, and owner acknowledgement | live-report contract | M04-LIVE-001..015 | Owner-countersigned sanitized T6 records |
| AC-TEST-005 | Critical pure scheduling/admission/lifecycle/retry/fencing/retention policy reaches the approved mutation score | mutation evidence | M04-PURE-001..028 | Independent mutation review |
| AC-TEST-006 | Failed, Blocked, and Not Run scenarios remain separate from deterministic pipeline success | evidence/status contract | All live/operations scenarios | Pipeline/release matrix review |

### Approved interpretation versus discovery-dependent proposal

- Approved: approximately one minute for active accounts and five minutes for idle accounts are defaults, not promises to violate provider limits. A stricter source minimum always wins.
- Proposed: `active` means a fresh, contract-valid activity signal for the target/account from M06 or another approved producer; absent/stale evidence is `unknown` and uses the idle cadence. M04 never infers activity from quota use or process ordering.
- Proposed: schedule jitter is deterministic and bounded around the base due time so restart does not create a thundering herd. Its approved range is a CS-2 decision.
- Proposed: manual and event refresh bypass only the ordinary cadence due time. They never bypass source compatibility, monitoring disabled, protected-profile read-only rules, auth/user-action block, backoff/Retry-After, request/cost budget, lease, deadline, or concurrency admission.
- Proposed: each actual provider/platform invocation is one `CollectionRun`; delayed retries create a new run in a durable retry chain rather than hiding multiple network/CLI attempts inside one record.
- Proposed: outcome payloads are committed synchronously through a consumer-owned idempotent sink before M04 emits completion. M04 retains only payload digest metadata and opaque observation references.
- Discovery-dependent: exact deadlines, source minimum intervals, rate windows, request units, cost classification, retry eligibility, and concurrency ceilings. Unknown values block automated dispatch for that source.

## 3. Domain design

### Core identities and value objects

#### CollectionTargetKey

- Contains opaque `provider_key`, `provider_installation_id`, optional `account_id`, optional `monitoring_profile_id`, optional `account_resource_id`, `capability_key`, and endpoint kind (`provider` or `platform`).
- The exact required/nullable combination is supplied by M02/M03 contract synchronization per capability. M04 does not derive provider identity from display labels or profile paths.
- A canonical versioned serialization is hashed for uniqueness; clients never construct or parse this hash.
- Registry IDs are scalar references, not cross-module database foreign keys.
- A changed stable identity creates or migrates a target only through an explicit registry event/version; M04 never silently associates accounts.

#### CollectionSchedule

- Exactly one current schedule exists per canonical target/capability.
- State is `enabled`, `paused_monitoring_disabled`, `blocked_authentication`, `blocked_user_action`, `blocked_compatibility`, `blocked_unknown_constraints`, `unsupported`, or `retired`.
- Stores policy version, activity class/evidence time, base interval, effective minimum interval, jitter band, next nominal due, next eligible time, consecutive retriable failure count, backoff reason/until, last attempted/successful run references, and optimistic record version.
- `next_due_at` expresses normal cadence. `not_before_at` expresses a safety constraint. A run is eligible only when both are satisfied and every current admission check passes.
- Disabled/retired/blocked schedules remain visible and retain history; they do not produce provider calls.

#### ActivityClass

- Values are `active`, `idle`, and `unknown`.
- `active` requires a producer, subject, observed time, expiry time, evidence kind, and event ID. A stale active signal becomes `unknown`, not idle evidence.
- `idle` may be supplied only by an approved definitive producer. Otherwise lack of activity is `unknown`.
- Proposed V1 cadence maps `active` to 60 seconds and both `idle` and `unknown` to 300 seconds before stricter source constraints.
- An activity update changes the next nominal due prospectively. It never causes a burst of catch-up runs.

#### CollectionTrigger and CollectionRequest

- Trigger kinds are `scheduled`, `manual`, `observable_request`, `observable_error`, `authentication_recovered`, `registry_changed`, and `reauth_verification`.
- Trigger evidence contains only safe IDs, occurrence time, producer/version, correlation/causation IDs, and subject/capability. Free-form payloads and provider output are prohibited.
- A manual request has an authorized principal ID, bounded idempotency-key digest, canonical request fingerprint, request time, optional user-safe reason code, status, and linked run ID. It never stores raw authorization credentials or raw idempotency text.
- A repeated internal trigger uses its event ID for deduplication.
- Multiple eligible requests for one target/capability coalesce into one queued/running run. Every request remains queryable and points to that run.

#### CollectionLease

- A lease is identified by schedule ID, opaque scheduler-instance ID, monotonically increasing fencing token, acquired/heartbeat/expiry instants, and run ID.
- Atomic acquisition succeeds for one claimant only. Renewal requires the current owner and fencing token.
- A terminal run update, result commit acknowledgment, or outbox creation requires the current fencing token. An expired/stale worker cannot commit.
- Lease expiry allows recovery; it is not proof that an external request did not occur.
- Lease duration is greater than the admitted execution deadline plus commit margin; heartbeat is no more than one-third of the lease duration. Exact values are derived from approved configuration/constraints.

#### RequestBudget and DispatchAdmission

- Every dispatch requires an atomic admission decision after the lease is acquired and before the provider/platform port is invoked.
- Constraint scopes may include global, endpoint kind, provider, installation, credential/profile, account/resource, capability, and provider-defined rate scope. The effective limit is the most restrictive applicable approved constraint.
- Constraint dimensions are maximum concurrent runs, minimum interval, maximum request units in a documented time window, retry allowance, response/output bound, deadline bound, and cost classification/budget.
- Units are integers with explicit names; M04 never interprets request units as money. If a source has a possible monetary cost, the exact currency/limit policy must be separately approved. Unknown/non-approved cost blocks automatic and manual dispatch.
- A budget reservation is consumed when the adapter invocation begins because the request may have reached the provider even if the response is lost. A crash never refunds it speculatively.
- A reservation cancelled before any adapter invocation is released transactionally.

#### CollectionRun

Proposed lifecycle:

```text
requested -> queued -> running -> committing -> succeeded
                                     |       -> partial
requested/queued/running/committing --------> failed
requested/queued ----------------------------> blocked
requested/queued/running --------------------> cancelled
requested/queued ----------------------------> unsupported
```

- `requested`, `queued`, `running`, and `committing` are non-terminal. Terminal states are `succeeded`, `partial`, `failed`, `blocked`, `cancelled`, and `unsupported`.
- Only M04 may transition a run. Terminal states never reactivate.
- `running` begins immediately before the approved executor is invoked. `committing` begins after a typed success/partial outcome passes protocol validation and before the consumer result sink is called.
- A run snapshots the target/profile/capability/source/adapter/provider version, trigger set, deadline, request-budget reservation, lease/fencing token, correlation/causation IDs, and retry-chain ordinal used for that invocation.
- Run duration is measured with a monotonic clock in process and stored as non-negative integer milliseconds alongside UTC started/completed instants. After crash, duration may be unknown and is explicitly nullable.
- A run stores only typed safe warning/error codes and opaque committed observation references. It never stores raw payloads or content.

### Scheduling policy

1. Reconcile enabled targets from M02/M03 through versioned query/events.
2. Compute base cadence from activity class.
3. Apply the stricter of base cadence and every approved source minimum.
4. Add deterministic, bounded target/policy/generation jitter that cannot schedule earlier than the source minimum.
5. Set `next_eligible_at = max(next_due_at, backoff_until, retry_after_at, rate_window_available_at, auth/user block)`; a non-time block has no eligible instant.
6. Select due schedules in bounded batches ordered by `next_eligible_at`, oldest pending trigger, trigger priority, and opaque target ID for deterministic ties.
7. Enforce a fairness ceiling so repeated manual/event requests from one scope cannot starve ordinary due targets. Exact lane weights are synchronized and performance-tested.
8. Acquire lease, re-read registry/manifest/policy, reserve concurrency/request budget, create run, then dispatch. Any changed prerequisite aborts without external call.
9. On terminal success/partial, compute the next cadence from completion time; missed intervals are not replayed.
10. On retryable failure, compute a new backoff generation and later new run. No tight in-call retry loop is allowed unless M0 explicitly proves and the contract separately approves one; V1 proposal is zero hidden retries.

Manual/event priority never means immediate external I/O. It means “eligible as soon as every safety gate permits.” The returned request/run view must explain a blocked or delayed decision.

### Retry and backoff policy

| M03 outcome | M04 terminal state | Automatic retry | Schedule effect |
|---|---|---|---|
| `success` | `succeeded` after result commit | normal cadence only | clear retriable backoff/failure count |
| `partial` | `partial` after available result commit | only if M03/M0 explicitly classifies missing portion retryable; otherwise normal cadence | preserve affected capabilities/warnings; never invent missing fields |
| `unsupported` | `unsupported` | no | suspend until manifest/version/registry generation changes |
| `unverified_provider_version` | `blocked` / compatibility | no | suspend; require discovery/adapter verification |
| `reauthentication_required` | `blocked` / provider authentication | no | require newer verified CTR-REG-010 healthy recovery generation |
| `authorization_insufficient` | `blocked` / authorization | no | require credential-role/profile/manifest change |
| `blocked_user_action_required` | `blocked` / user action | no | require explicit verified completion event |
| `rate_limited` | `failed` / rate limited | delayed only | honor provider `retry_after_at` and stricter approved backoff/budget window |
| `provider_unavailable` | `failed` / unavailable | delayed if approved | source-approved capped backoff with bounded jitter |
| `deadline_exceeded` | `failed` / deadline | delayed if approved and budget remains | no same-run repeat; increase backoff |
| `invalid_provider_data` | `failed` / invalid data | no by default | compatibility block until reviewed; do not guess parsing |
| `internal_adapter_error` | `failed` / adapter internal | delayed only if approved | isolate adapter; capped backoff; health degraded |

Backoff takes an explicit outcome, prior failure generation, approved minimum/maximum, provider retry time, and deterministic jitter input. It uses no implicit wall clock in pure policy. On success, only retriable failure state clears; auth/compatibility blocks clear only from their authoritative recovery source.

### Freshness and truthfulness

- M04 owns collection freshness: last attempt, last successful commit, cadence lateness, block/backoff status, and schedule overdue state.
- M05/M06 own metric/session freshness and whether an older observation remains usable. M04 supplies run/provenance references but does not mark an older value current.
- A cached prior observation is never emitted as a new completion and no failure becomes a zero observation.
- A schedule is `overdue` only under an approved policy that accounts for base interval, expected source latency, active backoff, service downtime, and explicit blocks. Overdue is not the same as provider unavailable.
- `observed_at` originates at the adapter/source, `collected_at` is adapter completion, and `stored_at` belongs to the consumer repository. M04 preserves, never rewrites, their meanings.

### Concurrency and failure isolation

- One run per target/capability at a time.
- Effective concurrency is the minimum of all approved scoped limits. A missing source-specific ceiling blocks concurrency above one and may block collection entirely when M0 cannot approve even a single request.
- Worker tasks are supervised independently. An exception is converted once at the adapter/application boundary to a safe outcome; it cannot terminate the scheduler loop.
- Database transactions do not remain open across provider/platform I/O.
- Provider calls occur only after durable run/admission state exists. Results are committed by consumer ports idempotently using `run_id` and payload digest.
- Failure of event delivery does not recollect from the provider. The durable outbox retries delivery at least once.
- Failure before result commit records failure and may schedule a later bounded recollection. Failure after a consumer committed is reconciled through `GetCollectionCommitStatusV1(run_id)`; M04 does not duplicate the observation.

### Clock semantics

- Persist all instants as timezone-aware UTC. Public form is RFC 3339; durations are integer milliseconds.
- Pure policies accept explicit `as_of` and jitter input. Production captures one UTC wall instant and monotonic instant per decision/execution boundary.
- Backward wall-clock movement never extends a persisted provider Retry-After or lease without a new validated calculation. Forward jumps do not enqueue all missed intervals.
- A detected material wall/monotonic anomaly pauses new dispatch, records a safe health condition, recomputes due state from persisted instants, and resumes only under the approved clock-recovery policy.
- The machine clock is never changed for tests.

### Shutdown and cancellation

1. Enter `stopping`; refuse new manual/event requests with a safe retryable outcome and stop acquiring leases.
2. Allow running collection tasks to finish within the configured shutdown grace and their earlier individual deadlines.
3. Send cooperative cancellation only through the M04 execution context to work launched and tracked by AgentMonitor.
4. A safe subprocess executor may terminate only its own verified child inspection process group according to the adapter/platform contract. It never uses discovered agent PIDs or process-tree relationships as cancellation targets.
5. Finalize safely cancellable runs as `cancelled/service_shutdown`; otherwise leave durable running/committing state for lease-expiry recovery.
6. Flush terminal/outbox transactions and instance heartbeat, then stop. Hard termination relies on fenced lease expiry and conservative budget accounting.

V1 exposes no user “cancel collection” API. This avoids confusing collector cancellation with control of monitored agents.

## 4. Public contracts

All contracts are proposals pending M0 and CS-2 producer/consumer review. Examples, if later added, are structural only and never live telemetry.

### Published contract summary

| Register ID | Proposed name/version | Producer | Consumers | Compatibility promise |
|---|---|---|---|---|
| CTR-COL-001 | `CollectionRequestV1` family | M04 | P01, scheduler, approved internal trigger producers | Additive optional fields only in V1; target/trigger/idempotency meaning stable |
| CTR-COL-002 | `CollectionRunViewV1` / query family | M04 | P01/UI, M05/M06 references, M07, M08 | State/error/time meanings stable; new unknown-tolerant codes additive |
| CTR-COL-003 | `CollectionCompletedV1` | M04 | M05/M06/M07/M08 | Immutable at-least-once event; committed refs only; per-schedule sequence |
| CTR-COL-004 | `CollectionFailedV1` | M04 | M07/M08 | Safe outcome/retry/block semantics never broaden silently |
| CTR-COL-005 | `CollectorHealthV1` / query | M04 | M08, P01/UI | Aggregate/detail disclosure and freshness semantics stable |
| CTR-COL-006 | `CollectionOutcomeCommitPortV1` / `CollectionCommitReceiptV1` | M04 semantic producer; M05/M06 implementations through composition router | M04 executor, M05/M06 and P01 status | Idempotent by run ID + generation + schema + payload digest; no raw payload retention by M04 |
| CTR-COL-007 | `CollectorHealthChangedAndCurrentAlertInputsV1` | M04 | M07/M08 | Current health query plus ordered active/recovery generations; silence/later success is not recovery |

CTR-COL-006 and CTR-COL-007 are allocated in Draft contract-baseline `0.2.0` with M04 as sole semantic producer. They remain unapproved until producer/consumer review. Implementers cannot replace either with direct table access, a generic JSON blob, direct M05/M06 imports, or inferred recovery.

### CTR-COL-001 — request and trigger ports

| Port/type | Input/output | Preconditions/authorization | Outcomes | Idempotency/side effects |
|---|---|---|---|---|
| `RequestManualCollectionV1` | target selector, capability set, principal, idempotency key, correlation ID -> `CollectionRequestAcceptedV1` | authenticated permission selected at CS-3; target visible/enabled; bounded request | accepted/joins run/delayed/blocked/unsupported/not found/conflict/stopping | Same key+fingerprint returns same request; different fingerprint conflicts; background provider call only after admission |
| `NotifyCollectionTriggerV1` | trusted producer/version, event ID/type, target, occurred time, correlation/causation -> request summary | registered producer and supported trigger; no caller-supplied raw payload | accepted/coalesced/stale event/duplicate/blocked | Event ID deduplicates; cannot bypass gates |
| `NotifyActivityV1` | target/account, activity class, observed/expires time, evidence code, event ID -> schedule summary | approved M06/producer contract | applied/duplicate/stale/conflict/unknown target | Newer valid generation wins; no external call by itself unless event refresh approved |
| `ReconcileCollectionTargetsV1` | registry/manifest generation refs -> reconciliation summary | internal composition/M02/M03 producer | created/updated/paused/retired/blocked; typed dependency unavailable | Idempotent for same source generations |
| `GetCollectionRequestV1` | request ID + principal -> request/run link | authorized read | found/not found/forbidden | Read-only |

The manual permission name is unresolved. This draft recommends a dedicated `write:collection` permission/scope because refresh can consume provider request/cost budget; reusing read-only telemetry authority would be misleading. M01/P01/root must approve it.

### CTR-COL-002 — run view and query ports

`CollectionRunViewV1` fields:

- run/request/retry-chain IDs and ordinal;
- safe target IDs: provider key, installation/account/profile/resource IDs as authorized opaque references, capability key;
- trigger set, run state, typed outcome code, affected capability keys;
- requested/queued/started/completed UTC instants and nullable duration milliseconds;
- deadline, source identifier/class, adapter/protocol/provider version, policy version;
- retry disposition, backoff/next-eligible time, auth/user/compatibility block code;
- safe warning codes, sanitized error code, correlation/causation IDs;
- committed opaque observation IDs and event IDs, never observation values or raw output;
- freshness state of the collection run itself.

Published queries:

- `GetCollectionRunV1(run_id)`;
- `ListCollectionRunsV1(filters, cursor, page_size)` with bounded provider/account/capability/state/time filters;
- `GetLatestCollectionRunV1(target)`;
- `ListPendingCollectionRequestsV1` for authorized diagnostics.

Ordering is `(requested_at desc, run_id desc)` or another synchronized deterministic cursor. Null/unknown/unsupported/block states are explicit. Queries never trigger collection.

### CTR-COL-003/004 — events

Both events use `EventEnvelopeV1`, immutable event IDs, correlation/causation IDs, at-least-once delivery, and ordering only by monotonically increasing sequence within one schedule stream. Consumers deduplicate `event_id`. There is no global ordering guarantee.

`CollectionCompletedV1` contains run ID, target references, terminal state (`succeeded` or `partial`), committed observation IDs grouped only by consumer/capability, observed/collected/stored time range, source/adapter/provider/policy versions, safe warning codes, affected capabilities, and schedule sequence. It is created only after an idempotent commit receipt exists.

`CollectionFailedV1` contains run ID, target references, terminal state (`failed`, `blocked`, `cancelled`, or `unsupported`), safe outcome/error code, affected capabilities, retry disposition, consecutive-failure generation, provider Retry-After when valid, next-eligible time or non-time block, source/adapter/provider/policy versions, and schedule sequence. It contains no exception text, raw response, command, path, or credentials.

`CollectionCompletedV1` alone does not mean collector recovery. M04 publishes CTR-COL-007 only when a newer health generation explicitly transitions the same target/capability condition to recovered/current. M07 consumes that transition and owns alert recovery/deduplication. M04 does not emit alert commands.

### CTR-COL-005 — health

`CollectorHealthV1` has two authorized projections:

- aggregate: scheduler lifecycle, heartbeat age, database/lease/outbox state, due/queued/running/committing/overdue counts, blocked/backoff/unsupported counts by safe category, oldest due age, last successful completion, worker/concurrency saturation, policy/schema/module version;
- subject detail: schedule state, last attempt/success, next due/eligible, current lease/run, backoff/block reason, source/version, recent safe outcomes for one authorized target.

It excludes raw provider identities, credentials, output, payload values, exception strings, filesystem paths, and unbounded account labels. Health values distinguish `healthy`, `degraded`, `blocked`, `stopping`, and `unavailable`; a provider auth block does not make the whole API process unready.

Published ports are `GetCollectorHealthV1`, `GetCollectorHealthForTargetV1`, and M04's implementation of M08 `ComponentHealthPortV1` after synchronization.

CTR-COL-007 adds `GetCurrentCollectorAlertInputsV1(scope, minimum_generation)` and `CollectorHealthChangedV1`. Both carry target/capability, previous/current safe health state, condition generation, observed/recorded time, causal run/event references, retry/block category, and explicit `active | recovered | not_evaluable` truth. They never expose provider payloads or infer recovery from silence.

### CTR-COL-006 — result commit seam

`CollectionOutcomeCommitPortV1.commit` receives:

- run ID, target/capability, typed M03 `CollectionOutcomeV1` success/partial payload, payload digest, source/provenance, and collection timestamps;
- a deadline/cancellation context no later than the run deadline;
- no raw provider response and no credential/profile implementation detail beyond opaque refs.

It returns `CollectionCommitReceiptV1`: run ID, payload digest, consumer key/version, committed opaque observation IDs, stored-at range, and receipt version. Calling again with the same run ID/digest returns the same receipt; a different digest is a hard conflict and incident signal.

`GetCollectionCommitStatusV1(run_id)` supports crash reconciliation and returns `not_committed`, `committed(receipt)`, `conflict`, or `unavailable`. M05/M06 own storage and validation of observation contents. Composition routes each capability to exactly one owning sink. M04 treats unknown routing as a contract/configuration block and never stores the payload itself.

### Consumed contracts

| Owner/contract | Required version/status | M04 use | Failure/degradation behavior |
|---|---|---|---|
| CTR-COMMON-001/002/004/006/007 | proposed-aligned V1 | IDs, UTC/duration, provenance references, event envelopes, field availability | incompatible common major or invalid field-state combination blocks startup/dispatch |
| CTR-EVT-001 | proposed-aligned V1 | atomic outbox plus consumer receipts/checkpoints/replay | consumer outage leaves visible backlog and never rolls back a committed run |
| CTR-CONFIG-001 / foundation configuration | `proposed_aligned` 1.0.0 | validated M04 settings and source tracking | invalid safety setting blocks collection readiness |
| CTR-DB-002 | `proposed_aligned` 1.0.0 | M04 repository/unit-of-work implementations | typed unavailable/conflict/corrupt; no provider dispatch without durable admission |
| CTR-IAM-001/002 | `proposed_aligned` 1.0.0 | authorized principal/decision for manual query/action | deny on unavailable/unknown permission; no implicit admin bypass |
| CTR-REG-002/003/004/005 | `evidence_blocked` 1.0.0 | account, profile, installation, resource, monitoring/protection state | target blocked/retired; never guess identity or use stale protected-profile permission |
| CTR-REG-007 | `proposed_aligned` 1.0.0 | idempotent target reconciliation trigger | retain last safe schedule state and report registry sync stale |
| CTR-REG-010 | evidence-blocked V1 | durable provider authentication block/recovery generation | stale/mismatched recovery is ignored; dashboard auth is unrelated |
| CTR-PROV-001 | `evidence_blocked` 1.0.0 | compatible adapter resolution and collection call | incompatible/missing adapter blocks target only |
| CTR-PROV-002/003 | `evidence_blocked` 1.0.0 | capability/source/side-effect/version/rate-cost declarations | unknown/unsupported/unverified/unsafe source blocks dispatch |
| CTR-PROV-004 | `evidence_blocked` 1.0.0 | typed collection outcome and retry hints | invalid union becomes non-retryable safe failure |
| CTR-PROV-006 | `evidence_blocked` 1.0.0 | auth block and verified recovery generation | auth failure never time-retries; stale recovery ignored |
| CTR-RUN-004 or synchronized activity contract | `evidence_blocked` 1.0.0 | active/idle evidence and optional event refresh | absent/stale means unknown/idle cadence; no failure cascade |
| M05/M06 result-commit implementations | Draft; exact IDs require contract review | persist typed capacity/runtime results and return receipt | do not complete success before receipt; isolate sink failures |
| CTR-OPS-006 | `proposed_aligned` 1.0.0 | publish component health to M08 | M04 remains operational if M08 query consumer is unavailable |
| CTR-OPS-007 | proposed-aligned V1 | implement collection retention/export/consistency participant | typed bounded failure; no M08 access to collection tables |

Although the backlog listed `CTR-PROV-001..006`, M04 has no direct need to consume `DiscoveryOutcomeV1` (CTR-PROV-005); M02 reconciles discovery into registry views. CS-2 must confirm this correction or document a concrete read-only use. M04 will not assume a dependency merely to match a range shorthand.

### Error and outcome vocabulary

Stable safe M04 errors include:

- `collection_target_not_found`, `collection_target_disabled`, `collection_capability_unsupported`;
- `collection_source_unverified`, `collection_constraints_unknown`, `collection_source_not_read_only`;
- `collection_authentication_required`, `collection_authorization_insufficient`, `collection_user_action_required`;
- `collection_rate_budget_deferred`, `collection_cost_budget_blocked`, `collection_concurrency_deferred`;
- `collection_already_running`, `collection_idempotency_conflict`, `collection_request_expired`;
- `collection_deadline_exceeded`, `collection_provider_unavailable`, `collection_provider_rate_limited`;
- `collection_invalid_provider_data`, `collection_adapter_internal`, `collection_result_sink_unavailable`;
- `collection_commit_conflict`, `collection_lease_lost`, `collection_service_stopping`;
- `collection_repository_unavailable`, `collection_policy_incompatible`, `collection_clock_anomaly`.

P01 maps these to RFC 9457 responses. A blocked/deferred background run is normally represented by its resource rather than treating the original `202` response as synchronous provider success.

### Contract-impact assessment

This plan defines new contracts rather than changing implemented behavior. Before approval, CS-2 must:

1. freeze common target/provenance/time/event primitives;
2. synchronize target/profile/resource/protection semantics with M02;
3. synchronize capability/source/outcome/deadline/cancellation/rate-cost semantics with M03 and each adapter plan;
4. allocate the activity signal and its producer/expiry/conflict semantics with M06;
5. freeze Draft-aligned CTR-COL-006 jointly with M05/M06 without direct persistence coupling;
6. freeze completed/failed event payloads with M07/M08 and confirm at-least-once ordering/deduplication;
7. freeze M04 manual permission, API request/run behavior, idempotency, and problem mapping with M01/P01;
8. allocate configuration names, table/migration names, outbox infrastructure ownership, and event delivery responsibility;
9. decide whether lease/outbox/result-commit semantics need an ADR due to their cross-module durability consequences;
10. update the shared contract register before any implementation assignment.

## 5. Data and persistence

Names below are proposed. Exact DDL and revision IDs require the persistence owner and central migration allocation.

### `collection_schedule`

- `schedule_id` primary key and canonical `target_key_hash` unique;
- scalar provider/installation/account/profile/resource IDs plus capability/endpoint kind;
- schedule state, activity class/evidence event/observed/expires timestamps;
- base/effective interval seconds, policy/manifest/registry generations;
- `next_due_at`, nullable `not_before_at`, backoff kind/generation, consecutive retriable failure count;
- last attempted/successful run IDs and timestamps, last terminal outcome code;
- optimistic `record_version`, created/updated timestamps.

No provider label, email, credential, profile path, raw source field, or observation value is stored.

### `collection_request`

- request ID, trigger kind, schedule/target reference, requested capability set/version;
- authorized principal ID/auth method for manual requests or producer/event ID for internal triggers;
- idempotency-key digest and canonical request fingerprint;
- requested/expiry/completed timestamps, request state, linked run ID, correlation/causation IDs;
- safe block/delay code; no free-form reason or credential.

Unique constraints cover manual `(principal_id, operation_family, idempotency_digest)` and internal `(producer, event_id)`. A second request may link to an existing run without duplicating dispatch.

### `collection_lease`

- one row per schedule with schedule ID primary key;
- owner scheduler-instance ID, fencing token integer, run ID;
- acquired/heartbeat/expiry timestamps and lease policy version;
- database constraint that fencing token only increases through the repository operation.

### `collection_run`

- run ID, schedule ID, target identity snapshot, capability, retry-chain ID/ordinal;
- run state/outcome/error/retry disposition and affected capability set represented through normalized child rows where querying requires it;
- trigger summary and primary request ID;
- requested/queued/started/completed timestamps, nullable duration milliseconds, deadline;
- source identifier/class, adapter/protocol/provider/manifest/policy versions;
- lease fencing token, budget reservation ID, payload digest after validated outcome;
- next eligible/retry-after times, correlation/causation IDs, record version;
- no raw payload, exception message, command output, path, auth material, or observation values.

### `collection_run_warning` and `collection_run_observation_ref`

- warning row: run ID, ordinal, allowlisted warning code, affected capability, schema version;
- observation reference row: run ID, consumer key/version, opaque observation ID, commit-receipt version;
- unique `(run_id, ordinal)` and `(run_id, consumer_key, observation_id)` constraints;
- no unrestricted text or copied capacity/runtime fields.

### `collection_budget_reservation`

- reservation ID, run ID, approved constraint-policy ID/version, scope-key hash, dimension/unit;
- window start/end, integer units, state (`reserved`, `dispatched`, `released`, `expired_conservative`), timestamps;
- unique `(run_id, constraint_policy_id, dimension)`;
- reservations remain counted after uncertain dispatch until the real provider window expires.

### `collection_scheduler_instance`

- opaque instance ID, service/build version, started/heartbeat/stopping/completed timestamps;
- lifecycle state and safe last-health code;
- no hostname, username, process environment, or command line unless a later safe operations contract approves a bounded value.

### `collection_event_outbox` and `collection_event_delivery`

- outbox: event ID/type/schema, producer/schedule stream/sequence, correlation/causation IDs, subject ID, allowlisted canonical payload, occurred/recorded times, availability time;
- delivery: event ID, registered consumer key/version, state, attempt count, next attempt time, last safe error code, delivered/acknowledged time;
- unique schedule stream sequence and `(event_id, consumer_key)`;
- payload is limited to CTR-COL-003/004 fields and cannot contain provider result bodies.

Shared outbox dispatcher code, if approved by foundation, remains infrastructure; M04 owns its event rows, schema, and producer transaction.

### Indexes and query plans

Planned indexes, validated against real query plans:

- `collection_schedule(state, next_due_at, schedule_id)` for bounded due selection;
- `collection_schedule(provider_key, account_id, capability_key)` and profile/resource variants used by authorized queries;
- `collection_lease(expires_at)` and unique schedule ownership;
- `collection_request(status, requested_at, request_id)`, manual idempotency, and internal event dedupe indexes;
- `collection_run(schedule_id, requested_at desc, run_id)`, `(state, requested_at)`, `(provider_key, account_id, capability_key, requested_at)` and correlation ID;
- `collection_budget_reservation(scope_key_hash, dimension, window_end, state)`;
- `collection_event_outbox(available_at, recorded_at)` and delivery `(consumer_key, state, next_attempt_at)`;
- history purge indexes on terminal/completed timestamps.

All list/history queries are bounded and cursor-paginated. Performance evidence must prove the due query does not scan all retained runs.

### Transaction boundaries

- Target reconciliation changes schedules in a short transaction, one bounded batch at a time.
- Manual/event request acceptance, idempotency decision, coalescing, and request row creation are one transaction.
- Lease acquisition, fresh prerequisite check, budget reservation, queued/run creation, and schedule generation update are one transaction before external I/O.
- Provider/platform I/O and result-sink I/O run outside database transactions.
- Transition to `committing` stores only the payload digest/summary, never payload content.
- Commit receipt, terminal run state, schedule update, request completion, lease release, and outbox event are one M04 transaction after the consumer commit succeeds.
- Event delivery/ack uses independent short transactions and never reopens a terminal run or recollects.
- Retention uses bounded batches and its own auditable run; it never deletes active schedules, leases, non-terminal runs, undelivered events, or current health references.

### Restart and crash reconciliation

1. Register a new scheduler instance and stop dispatch until schema/config/policy checks pass.
2. Find expired leases/non-terminal runs whose owner heartbeat is stale.
3. For `committing`, query the correct consumer `GetCollectionCommitStatusV1(run_id)`.
4. If a matching receipt exists, finalize terminal state and event idempotently under a new fencing token.
5. If no receipt exists, mark `failed/collector_interrupted` and apply conservative request-budget/backoff policy; never replay a missing in-memory payload.
6. For `running`, assume the external request may have occurred, keep budget consumed, mark interruption, and schedule only under approved retry policy.
7. Requeue still-valid accepted requests by normal admission; expire old ones visibly.
8. Resume outbox deliveries at least once; consumers deduplicate event IDs.

### Retention, backup, and migration

- Terminal runs, requests, warnings, observation references, scheduler events, and delivery history are retained 365 days under FR-HIST-001 unless a stricter security decision is approved.
- Current schedules, active leases, policy state, non-terminal requests/runs, and undelivered outbox records are not age-purged.
- Expiry uses a pure cutoff policy and real SQLite batch deletion; counts and cutoff are audited through an M04 retention result consumed by M08.
- M04 data contains no provider credential or raw observation, but backups still contain account/profile IDs and operational metadata and remain owner-protected.
- Migrations follow expand/migrate/switch/contract. No implicit create-all or destructive downgrade is allowed.
- Before an incompatible or destructive migration, M08 verifies a backup; recovery uses verified backup plus prior compatible binary when downgrade is unsafe.
- SQLite-specific locking/upsert behavior is isolated in the adapter. Repository contracts preserve a PostgreSQL implementation path.

## 6. External and platform boundaries

### Provider execution

M04 resolves an adapter only through approved M03 registration/compatibility contracts. Each dispatch context includes run/correlation IDs, target/profile opaque references, exact capability/source, deadline, cancellation token, request/output budget, and approved side-effect class. It never carries a credential value or arbitrary environment.

Before invocation M04 verifies:

- target is still enabled and identities/generations agree with M02;
- profile/default-profile protection permits the declared read-only operation;
- adapter protocol, capability schema, provider version, source, and credential role are compatible;
- source is M0-approved and no lower-priority fallback has been selected silently;
- operation side effect is `read_only` and request/cost/rate/concurrency constraints are known;
- a current fenced lease, deadline, and budget reservation exist.

M04 does not inspect HTTP/CLI/file behavior. A01–A03 enforce hosts, arguments, paths, output sizes, parsing, credential resolution, and redaction.

### Platform execution

Platform collection uses a separately synchronized `PlatformCollectionPortV1` or an approved M03-compatible endpoint registration. M04 supplies scheduling/deadline/cancellation only. A04/M06 own OS APIs, PID identity, filesystem safety, and process/session meaning.

Cancellation is never implemented with a monitored PID from a result. Only the execution adapter/safe subprocess service may cancel the exact child work it created and positively owns.

### Consumer result boundary

Typed safe adapter results go directly from M03 contract objects to the registered M05 or M06 commit implementation. M04 may validate the outer outcome/capability/source/version envelope and compute a canonical payload digest, but it does not branch on quota, money, token, process, session, or provider-extension fields.

### Timeouts, redirects, retries, and cost

- Exact per-source call deadline and output bound come from the approved capability policy and M0 evidence.
- M04 never supplies an “infinite” timeout.
- Provider HTTP redirect/host policy belongs to adapters; an unexpected redirect is a typed adapter failure.
- Hidden SDK/HTTP retries must be disabled or included explicitly in request-budget accounting and live evidence. Unknown library retries block admission.
- No billable inference/generation request is authorized for monitoring in V1. A source requiring one is unsupported/deferred unless the owner approves a new requirement, cost policy, threat review, and contract.
- Authentication, authorization, wrong-account, and user-action outcomes have zero automatic retry budget.

### Live verification

Each supported provider/source supplies a live M04 row containing source/version/account alias, effective interval/minimum, deadline, concurrency, request/rate/cost budget, observed outcome, run/event IDs, default-profile side-effect check, authoritative comparison, and owner acknowledgement. Rare failure states not safely/naturally observed remain Blocked and cannot be replaced by a constructed adapter response.

## 7. Security and privacy

### Trust boundaries and controls

| Threat | Required M04 control | Evidence |
|---|---|---|
| Manual refresh DoS/provider hammering | authentication/permission, idempotency, coalescing, per-principal/target limit, safety admission | M04-HTTP-001..004, M04-SEC-006 |
| Duplicate schedulers exceed rate limits | atomic fenced lease, budget reservation, stale-holder rejection | M04-DB-004..006/012 |
| Auth failure loops | non-time auth block; only newer verified recovery generation clears | M04-PURE-011/021, M04-DB-014, M04-LIVE-006 |
| Unknown/private source used silently | manifest/source compatibility and source-priority check; unknown blocks | M04-PURE-019, M04-LIVE-011 |
| Default provider profile modified | admit read-only side-effect class only; profile protection rechecked; adapter live side-effect proof | M04-SEC-007, M04-LIVE-009/011 |
| Raw payload/content/secret leaks | no raw-result persistence; allowlisted codes/events/logs; artifact scans | M04-SEC-001..005 |
| Stale worker commits wrong result | fencing token checked at every terminal/receipt transaction | M04-DB-004/012 |
| Crash causes uncounted repeated request | durable pre-dispatch run/reservation and conservative crash accounting | M04-DB-006/019, M04-OPS-009 |
| Shutdown kills monitored agent | cancellation port bound only to AgentMonitor-owned execution; no PID/process-control import | M04-ARCH-001, M04-OPS-005 |
| Result sink/event consumer cascades failure | idempotent receipt, durable outbox, independent consumer delivery | M04-DB-015..017/023/024 |
| Provider-derived error injects logs/UI | adapter outcome enum plus M04 safe-code allowlist; no free-form text | M04-SEC-002/003 |
| Collection metadata leaks identity/path | opaque IDs and authorized projection; no labels/paths in logs/health | M04-SEC-004/005 |

### Authorization

- Schedule execution and registered internal triggers use an application system principal scoped to the exact operation; they do not inherit an all-powerful browser identity.
- Manual refresh requires an explicit M01 authorization decision and P01 CSRF for browser sessions.
- Run/health queries require read telemetry/status authority and apply subject visibility rules at P01/application composition.
- Internal trigger registration is static/versioned at composition. Provider input cannot forge an AgentMonitor event producer.
- No public API mutates leases, budgets, run states, scheduler heartbeat, or outbox delivery.

### Secret handling and minimization proof

- M04 receives opaque `profile_ref`, never credential values.
- No secret belongs in M04 configuration.
- Idempotency keys are bounded by P01 and stored only as digests; trigger payloads are allowlisted.
- Database rows contain collection metadata and opaque cross-module IDs only.
- Logs contain timestamp, severity, module/event, run/schedule/correlation IDs, safe state/code, and duration/count values. They exclude raw URLs with query strings, headers, request/response bodies, CLI output, commands, filesystem paths, profile values, exception messages, labels/emails, prompts/responses/tools/source, and arbitrary environment.
- Outbox payloads are schema-validated allowlists. Diagnostics aggregate safe categories/counts and do not dump rows.
- No AgentMonitor analytics or crash data leaves the machine.

### Abuse and invariant responses

- A commit receipt digest mismatch stops the affected target, records `collection_commit_conflict`, and triggers security/integrity review; it is never overwritten.
- An impossible state transition, lower fencing token, negative duration, clock anomaly, or unknown outcome is a programmer/data-integrity failure, not provider unavailable.
- A secret/content finding stops affected integration, quarantines contaminated artifacts outside version control, and follows the incident runbook.
- Repeated manual refresh never creates enough pending rows to grow unbounded; coalescing, expiry, and per-principal/account limits are enforced.

## 8. Configuration and operations

No key is approved or may be added to `.env` by this draft. All proposed keys are non-secret and owned by M04; final names/defaults/ranges require the configuration registry and CS-2 approval.

| Proposed external key | Internal name/type | Proposed default/range | Reload | Consequence |
|---|---|---|---|---|
| `AGENTMONITOR_COLLECTION_ACTIVE_INTERVAL_SECONDS` | `active_interval_seconds: int` | default 60; minimum cannot undercut source constraint | validated restart or authorized runtime policy, decision pending | active cadence |
| `AGENTMONITOR_COLLECTION_IDLE_INTERVAL_SECONDS` | `idle_interval_seconds: int` | default 300; must be >= active | same | idle/unknown cadence |
| `AGENTMONITOR_COLLECTION_JITTER_BASIS_POINTS` | `jitter_basis_points: int` | exact default TBD; bounded 0..approved maximum | restart | spreads due work without violating minimum |
| `AGENTMONITOR_COLLECTION_SCHEDULER_TICK_MILLISECONDS` | `scheduler_tick_ms: int` | measured safe default TBD | restart | due-query cadence only, not provider polling |
| `AGENTMONITOR_COLLECTION_DUE_BATCH_COUNT` | `due_batch_count: int` | measured bounded default TBD | restart | memory/DB work bound |
| `AGENTMONITOR_COLLECTION_GLOBAL_CONCURRENCY_COUNT` | `global_concurrency_count: int` | conservative default and maximum chosen after M0/performance; effective source min wins | restart | total collection workers |
| `AGENTMONITOR_COLLECTION_QUEUE_CAPACITY_COUNT` | `queue_capacity_count: int` | bounded measured default TBD | restart | protects service; excess remains durable due work |
| `AGENTMONITOR_COLLECTION_LEASE_SECONDS` | `lease_seconds: int` | derived to exceed maximum admitted deadline + commit margin | restart | crash recovery/fencing |
| `AGENTMONITOR_COLLECTION_LEASE_HEARTBEAT_SECONDS` | `lease_heartbeat_seconds: int` | <= one-third lease; exact TBD | restart | stale detection |
| `AGENTMONITOR_COLLECTION_SHUTDOWN_GRACE_SECONDS` | `shutdown_grace_seconds: int` | bounded and no greater than service manager stop window; exact TBD | restart | safe shutdown |
| `AGENTMONITOR_COLLECTION_MANUAL_REQUEST_TTL_SECONDS` | `manual_request_ttl_seconds: int` | exact TBD | restart | pending request expiry |
| `AGENTMONITOR_COLLECTION_HISTORY_RETENTION_DAYS` | `history_retention_days: int` | 365 in V1; weakening requires requirement review | authorized config migration | run/event retention |

Provider/source constraints are not free-form environment variables. They originate in versioned M0/M03 capability policy with evidence provenance. Operator settings can make collection less frequent or less concurrent within approved ranges; they cannot raise a provider/source safety ceiling without new evidence and review.

### Lifecycle and health

Scheduler lifecycle is `starting`, `reconciling`, `running`, `degraded`, `stopping`, or `stopped`.

- Startup readiness for collection requires compatible schema/config/contracts, M04 repository access, a registered scheduler instance, and completion of expired-lease reconciliation.
- Missing/blocked individual providers degrade only those targets; they do not make the dashboard/API liveness fail.
- A stale scheduler heartbeat, permanently held lease, growing due lag, outbox delivery backlog, commit conflicts, or database failure appears in M04 health and M08 aggregation.
- Browser state is irrelevant to the scheduler. The native service owns it.

### Structured logs and local operational measurements

Allowlisted events include scheduler start/stop, target reconciliation counts, lease acquired/lost/reclaimed, run state changes, admission deferred/blocked category, outcome category, backoff generation, outbox delivery state, clock anomaly, and retention result.

Local bounded measurements include:

- due/queued/running/committing counts and oldest due age;
- run duration by provider/capability safe key and outcome category;
- admission deferral count by reason;
- active leases and reclaimed leases;
- request-budget utilization by hashed/safe scope;
- outbox backlog/delivery age;
- scheduler loop duration and worker saturation.

These are local health data, not external analytics. Cardinality and retention are bounded; no raw account labels or paths enter logs/metrics.

### Operator procedures to document and verify

- inspect overall/target collector health and last safe outcome;
- request one manual refresh and understand delayed/blocked/unsupported results;
- investigate stale/missing telemetry without repeated hammering;
- respond to authentication/user-action/compatibility blocks through owning workflows;
- restart/service shutdown and verify lease/run recovery;
- diagnose an overdue/stuck lease, outbox backlog, or clock anomaly;
- purge expired collection history through M08 orchestration;
- verify post-upgrade schedules, policy/adapter versions, and real current collection;
- handle secret/content contamination or suspected default-profile mutation.

Commands remain TBD until implementation and live verification.

## 9. Test design before implementation

No scenario below is implemented or Passed by this plan. Pure tests use constructed schedule/outcome values only to prove deterministic M04 policies and never claim a provider behaves that way. Persistence tests use real temporary SQLite files and the full real migration chain. HTTP tests use a running production application on loopback. Any successful provider/platform dispatch uses a real approved adapter, real owner-controlled account/system, and current version. Naturally unavailable error states remain Blocked.

### Pure domain and contract tests

| Test ID | Layer | Requirement | Real dependencies | Meaningful initial Red expected | Pass condition | Owner/coordination |
|---|---|---|---|---|---|---|
| M04-PURE-001 | T1 pure | FR-COL-001 | None; explicit instants | active target gets idle interval | active base interval is exactly approved 60 seconds | M04 |
| M04-PURE-002 | T1 pure | FR-COL-001 | None | idle/unknown schedules too frequently | idle and unknown default to approved 300 seconds | M04 |
| M04-PURE-003 | T1 pure | FR-COL-001 | None | source minimum is ignored | effective cadence is never below stricter source minimum | M03/M04 |
| M04-PURE-004 | T1 pure | FR-COL-001 | None | jitter schedules early/outside bound | deterministic jitter is bounded and respects minimum | M04/test reviewer |
| M04-PURE-005 | T1 pure | FR-COL-001 | None | stale active evidence remains active | expired signal becomes unknown and uses idle cadence | M06/M04 |
| M04-PURE-006 | T1 pure | FR-COL-002 | None | manual refresh bypasses safety not-before | manual advances cadence only and remains delayed by safety gates | M04/security |
| M04-PURE-007 | T1 pure | FR-COL-002 | None | repeated triggers create separate runnable work | canonical target/capability triggers coalesce deterministically | M04 |
| M04-PURE-008 | T1 pure | FR-COL-003 | None | provider Retry-After is shortened | next eligible is no earlier than valid provider time and local policy | M03/M04 |
| M04-PURE-009 | T1 pure | FR-COL-003 | None | backoff fails to increase/cap or jitters outside policy | approved generation algorithm and cap hold at boundaries | M04 |
| M04-PURE-010 | T1 pure | FR-COL-003/006 | None | unsupported becomes retryable failure | unsupported suspends until manifest generation changes | M03/M04 |
| M04-PURE-011 | T1 pure | FR-AUTH-001 | None | auth outcome gets time retry | auth/user/authorization outcomes produce non-time block | M03/M04 |
| M04-PURE-012 | T1 pure | FR-COL-003/006 | None | invalid data/unverified version retries blindly | non-retry compatibility block is selected | M03/M04 |
| M04-PURE-013 | T1 pure | FR-COL-003 | None | provider unavailable retries without approved policy | retry only when source policy explicitly permits it | M03/M04 |
| M04-PURE-014 | T1 pure | FR-COL-003 | None | success leaves retriable backoff active | success resets only retriable failure generation | M04 |
| M04-PURE-015 | T1 contract | FR-COL-004 | None | observed/collected/stored time meaning is conflated | envelope preserves distinct nullable semantics/provenance | M03/M05/M06 |
| M04-PURE-016 | T1 pure | FR-COL-005 | None | invalid run transition reactivates terminal state | every valid/invalid transition follows state machine | M04 |
| M04-PURE-017 | T1 pure | FR-COL-005 | None | negative/guessed duration is emitted after clock anomaly | duration remains non-negative or explicit unknown | M04 |
| M04-PURE-018 | T1 pure | FR-COL-006 | None | unknown/blocked/unavailable maps to success or zero | all state categories remain distinct | M04/UI reviewer |
| M04-PURE-019 | T1 pure | FR-COL-007 | None | weaker source silently replaces approved source | downgrade is denied and explained | M03/security |
| M04-PURE-020 | T1 pure | FR-COL-008 | None | failed run emits prior refs as new completion | only new commit receipt creates completion | M04/M05/M06 |
| M04-PURE-021 | T1 pure | FR-AUTH-001 | None | stale auth recovery clears newer block | only matching/newer verified generation clears block | M02/M03/M04 |
| M04-PURE-022 | T1 pure | FR-HIST-003 | None; explicit UTC | retention boundary removes too early/late | exactly eligible terminal history is selected | M04/M08 |
| M04-PURE-023 | T1 pure | FR-SAFE-002 | None | cancellation target can contain monitored PID | policy accepts only owned execution handle | security/platform |
| M04-PURE-024 | T1 pure | AC-OPS-006 | None | least restrictive concurrent/rate limit wins | most restrictive applicable constraint wins | M03/M04 |
| M04-PURE-025 | T1 pure | AC-OPS-006 | None | unknown/nonzero unapproved cost is admitted | admission blocks until exact approved budget exists | owner/security |
| M04-PURE-026 | T1 pure | NFR-RES-001 | None | one manual lane starves scheduled work | approved fairness rule selects bounded ordinary work | performance reviewer |
| M04-PURE-027 | T1 pure | NFR-OBS-001 | None | collector health hides overdue/block reason | health calculation exposes distinct safe states | M04/M08 |
| M04-PURE-028 | T1 pure | NFR-COMP-001 | None | unknown event/outcome major is accepted | incompatible major blocks; additive known-major field tolerated | integration |

### Real persistence, concurrency, and recovery tests

| Test ID | Layer | Requirement | Real dependencies | Meaningful initial Red expected | Pass condition | Owner/coordination |
|---|---|---|---|---|---|---|
| M04-DB-001 | T2 migration | AC-V1-004 | real file SQLite/full Alembic chain | M04 schema absent/incompatible | fresh and every supported upgrade migration validates | persistence/M04 |
| M04-DB-002 | T2 DB | FR-COL-001 | real DB/repository | duplicate target schedules persist | one canonical schedule per target/capability | M04 |
| M04-DB-003 | T2 query plan | FR-COL-001 | real DB with AgentMonitor-owned load records | due selection scans run history/unbounded rows | due index and bounded batch plan are used | persistence/performance |
| M04-DB-004 | T2 concurrency | R-006 | real SQLite and concurrent production repositories | two claimants acquire same due generation | exactly one fenced lease/run wins | M04/persistence |
| M04-DB-005 | T2 concurrency | AC-OPS-006 | real DB | concurrent dispatch exceeds scoped slots | atomic effective-concurrency admission holds | M04 |
| M04-DB-006 | T2 budget | AC-OPS-006 | real DB | request reservations oversubscribe or crash-refund | window units never exceed policy; uncertain dispatch remains counted | M04 |
| M04-DB-007 | T2 idempotency | FR-COL-002 | real DB | same manual key creates two requests/runs | same fingerprint returns same request/run | M04/P01 |
| M04-DB-008 | T2 idempotency | FR-COL-002 | real DB | same key with different target is accepted | conflict with no second dispatch | M04/P01 |
| M04-DB-009 | T2 concurrency | FR-COL-002 | real DB/concurrent production use case | different manual keys dispatch same target twice | requests coalesce to one pending/running run | M04 |
| M04-DB-010 | T2 event | FR-COL-002 | real DB | duplicate event ID advances schedule twice | one accepted trigger; duplicate returns existing result | M04 |
| M04-DB-011 | T2 DB | FR-COL-005 | real DB | invalid lifecycle transition commits | database/domain constraints preserve terminality/order | M04 |
| M04-DB-012 | T2 fencing | FR-COL-005 | real DB/concurrent owners | expired old worker commits terminal state | stale fencing token is rejected | M04/persistence |
| M04-DB-013 | T2 DB | FR-COL-003 | real DB | backoff/Retry-After disappears across restart | exact block generation and next eligible survive | M04 |
| M04-DB-014 | T2 DB | FR-AUTH-001 | real DB | restart/time passage retries auth-blocked schedule | block persists until approved recovery event | M04/M03 |
| M04-DB-015 | T2 transaction | CTR-COL-003 | real DB and real consumer repository contract in composition | terminal success exists without receipt/outbox | receipt refs, terminal state, schedule, lease release, event commit atomically | M04/M05 or M06 |
| M04-DB-016 | T2 idempotency | CTR-COL-006 | real DB and production consumer repository | repeated same run creates duplicate observations | same digest returns same receipt/refs | M05/M06 |
| M04-DB-017 | T2 integrity | CTR-COL-006 | real DB | same run/different digest overwrites result | conflict blocks target and preserves first commit | M04/security |
| M04-DB-018 | T2 DB | FR-COL-006 | real DB | unsupported/auth/compatibility state is lost or merged | distinct schedule/run states persist/query correctly | M04 |
| M04-DB-019 | T2 restart | FR-COL-008 | real DB/process restart | interrupted running run is repeated as if no request occurred | interruption recorded; budget conservative; stale data not re-emitted | M04/operations |
| M04-DB-020 | T2 retention | FR-HIST-001/003 | real DB populated through production M04 use cases | expired terminal history remains or current state deleted | bounded purge removes only eligible rows | M04/M08 |
| M04-DB-021 | T2 retention concurrency | FR-HIST-003 | real DB and concurrent new run | purge locks scheduler or deletes active row | short batches coexist and preserve active work | persistence |
| M04-DB-022 | T2 UTC | FR-HIST-005 | real DB | local-time text/ambiguous instant persists | every persisted instant is UTC with exact contract mapping | M04 |
| M04-DB-023 | T2 resilience | NFR-RES-001 | real isolated SQLite lock/permission failure | repository failure dispatches provider or kills service | no external call; typed degraded state; unrelated liveness remains | operations |
| M04-DB-024 | T2 outbox | AC-ALERT-003 | real DB and production event dispatcher | crash loses event or makes provider recollect | durable at-least-once delivery; same event ID on retry | M04/M07/M08 |
| M04-DB-025 | T2 delivery isolation | NFR-RES-001 | real DB and real registered consumers | one unavailable consumer blocks other delivery/run queries | per-consumer state isolates failure and retains backlog | integration |
| M04-DB-026 | T2 recovery | AC-OPS-005 | real DB/process restart | expired lease cannot be reclaimed or two owners commit | new fencing token recovers exactly once | operations/M04 |
| M04-DB-027 | T2 reconciliation | FR-COL-001/002 | real M02/M03 contract implementations + DB | disabled/retired target continues due work | schedule pauses/retires without history loss | M02/M03/M04 |
| M04-DB-028 | T2 pagination | FR-COL-005 | real DB at planned history volume | run query is unbounded/unstable | deterministic cursor and approved indexes pass | P01/persistence |

### Real HTTP, browser, provider, platform, operations, and quality tests

| Test ID | Layer | Requirement | Real dependencies | Meaningful initial Red expected | Pass condition | Owner/live coordination |
|---|---|---|---|---|---|---|
| M04-HTTP-001 | T3 HTTP | FR-COL-002 | real server/DB/M01/P01 | unauthorized or CSRF-less refresh is accepted | explicit permission and browser CSRF enforced | M01/P01 |
| M04-HTTP-002 | T3 HTTP | FR-COL-002 | real server/DB | manual action holds request open for provider I/O | returns 202/current run link promptly; background only | P01/M04 |
| M04-HTTP-003 | T3 HTTP | FR-COL-002 | real server/DB | same Idempotency-Key creates duplicate work | same request/run or safe conflict per fingerprint | P01/M04 |
| M04-HTTP-004 | T3+T6 | FR-COL-002 | real enrolled target and adapter | concurrent manual refresh invokes provider twice | requests join one real run | owner/provider/M04 |
| M04-HTTP-005 | T3 HTTP | FR-COL-005 | real server/DB | run list omits timing/outcome/retry/warnings or leaks internals | schema-complete sanitized bounded views | P01/M04 |
| M04-HTTP-006 | T3 HTTP | FR-COL-006 | real persisted states from production flows | unsupported/blocked/unavailable collapse to generic success | distinct truthful views/problems | P01/UI |
| M04-HTTP-007 | T3+T6 | FR-COL-008/AC-HIST-001 | real provider, DB, API | failure appears current or success lacks history link | real run links committed real observation/history; failure stays failure | owner/M05/M06/P01 |
| M04-BROWSER-001 | T4 browser | AC-UI-002/005 | built UI/real server/DB | collection status needs placeholder or hides partial/blocked state | real run/health states render truthfully | P02/M04 |
| M04-BROWSER-002 | T4 browser | AC-UI-006 | built UI with real observation/run | source/time/version/retry explanation is inaccessible | user can inspect source/freshness/why delayed/blocked | P02/M04 |
| M04-LIVE-001 | T6 provider | FR-COL-001 | real approved active account/source | active cadence violates 60-second/default/source bound | elapsed dispatches follow effective policy | owner/provider adapter |
| M04-LIVE-002 | T6 provider | FR-COL-001 | real approved idle/unknown account/source | idle cadence violates 300-second/default/source bound | elapsed dispatches follow effective policy | owner/provider adapter |
| M04-LIVE-003 | T6 provider | FR-COL-002 | real supported observable request/error event | event is ignored or causes unsafe immediate call | one eligible coalesced refresh occurs, or capability honestly Unsupported | owner/adapter |
| M04-LIVE-004 | T6 provider | FR-COL-002 | owner-approved real manual refresh | refresh bypasses provider constraint or fails to run | real bounded call occurs at eligible time and is queryable | owner |
| M04-LIVE-005 | T6 provider | FR-COL-003 | naturally rate-limited real source | repeated calls hammer provider/ignore Retry-After | one failure, respected delay, no hidden retries | owner; Blocked until natural state |
| M04-LIVE-006 | T6 provider | FR-AUTH-001/AC-ALERT-003 | naturally auth-required account then approved recovery | scheduler retries auth or fails to recover correctly | block with zero retry; verified recovery enables one run | owner; interactive recovery separately approved |
| M04-LIVE-007 | T6 provider | FR-COL-003 | naturally unavailable provider/source | tight retry or cross-provider failure occurs | approved backoff and unrelated collectors continue | owner; Blocked until safe state |
| M04-LIVE-008 | T6 provider | FR-COL-003 | real deadline-capable source | timeout leaves running forever/retries invisibly | bounded deadline, safe outcome, approved later retry only | owner/provider |
| M04-LIVE-009 | T6 end-to-end | FR-COL-004/AC-HIST-001 | real account/source/M05 or M06 | provenance/run link/default-profile side effects wrong | receipt/observation/run reconcile and protected profile unchanged | owner/all vertical-slice owners |
| M04-LIVE-010 | T6 provider | FR-COL-006 | real unsupported/unverified capability/version | system invents value or dispatches anyway | explicit unsupported/blocked manifest/run/health state | owner/M03/adapter |
| M04-LIVE-011 | T6 provider | FR-COL-007 | provider with more than one declared source if available | adapter silently downgrades source | only approved source used; otherwise Blocked | owner/M03/adapter |
| M04-LIVE-012 | T6 provider | FR-AUTH-001 | real stale/wrong recovery event where safely observable | stale event clears block | generation/identity mismatch stays blocked | owner; never manufacture wrong-account login |
| M04-LIVE-013 | T6 integration | AC-OPS-003 | one real failing adapter/source and one real healthy source | failure stops scheduler/API/healthy source | healthy collection and API continue; failure isolated | owner; natural/safe failure required |
| M04-LIVE-014 | T6 integration | AC-ALERT-003 | real collector failure and recovery | duplicate/no recovery alert facts | M04 events allow M07 lifecycle exactly once per event | owner/M07 |
| M04-LIVE-015 | T6 provider | AC-OPS-006 | real provider/source with approved ledger | actual requests/concurrency exceed M0 policy | ledger and provider observation remain within ceiling | owner/provider |
| M04-OPS-001 | T7 operations | FR-OPS-002 | real installed service | health says healthy with stale heartbeat/stuck lease | truthful degraded state and actionable safe code | operations |
| M04-OPS-002 | T7 operations | FR-OPS-005 | real diagnostic bundle | raw provider/account/path/payload/secret enters bundle | strict safe allowlist and scan pass | security/M08 |
| M04-OPS-003 | T7 logging | NFR-OBS-001 | real successful/failed runs/log sink | raw errors/output/identities appear | safe structured IDs/codes only | security/operations |
| M04-OPS-004 | T7 versions | FR-OPS-006 | real service/API | module/policy/adapter/schema version is absent/misleading | exact safe versions visible | M08/P01 |
| M04-OPS-005 | T7 shutdown | FR-SAFE-002/AC-OPS-005 | real installed service, real running collection and agents | shutdown signals agent or loses unrecoverable run state | only owned task cancelled; agents unchanged; recovery valid | owner/platform/operations |
| M04-OPS-006 | T5/T7 platform | NFR-PLAT-001 | real Linux; real macOS when available | core imports OS-specific scheduling behavior | Linux passes; macOS passes or is visibly Blocked | platform owner |
| M04-OPS-007 | T7 resilience | NFR-RES-001 | real service and safe component failure | scheduler crash takes API/dashboard down | supervised degraded state; unrelated API remains | operations |
| M04-OPS-008 | T7 operations | AC-OPS-002 | real user service/browser/provider | closing browser stops due collection | background service records later real run | owner |
| M04-OPS-009 | T7 restart | AC-OPS-005 | real service restart during/after real collection | duplicate unsafe call or stuck lease/run | conservative reconciled state and safe later schedule | owner/operations |
| M04-OPS-010 | T7 upgrade | AC-OPS-005 | real supported prior/current install | upgrade loses schedules/backoff/history/outbox | migration/restart/post-check pass or verified recovery | operations |
| M04-PERF-001 | T1/T2 performance | NFR-PERF-001 | real SQLite; 100 AgentMonitor-owned schedule load records, not accounts/telemetry | due policy/query needs redesign or unbounded scan | measured bounded selection meets approved budget | performance/persistence |
| M04-PERF-002 | T2 performance | NFR-PERF-001 | real DB/outbox at planned one-year modeled metadata volume | run/health queries exceed approved latency/resource budget | indexed bounded measurements pass | performance |
| M04-PERF-003 | T3/T6 performance | NFR-PERF-001 | real current accounts/adapters only | worker saturation breaks API/fairness | measured real workload stays responsive within source ceilings | owner; no invented accounts |
| M04-PERF-004 | T2 concurrency | R-011 | real SQLite concurrent run/outbox/query workload | busy failures corrupt/drop state | measured transactions remain safe or plan is revised | persistence |
| M04-SEC-001 | T2 artifact | NFR-PRIV-001 | real DB/WAL/backups after live run | raw provider payload/observation/credential/content persists | only allowed metadata/refs exist | security |
| M04-SEC-002 | T3/T7 artifact | NFR-OBS-001 | real errors/logs/diagnostics | secret/content/free-form provider error appears | secret/content scans clean | security |
| M04-SEC-003 | T2 event | NFR-SEC-001 | real outbox/delivery | event stores raw outcome or unbounded text | schema allowlist only | security/M07/M08 |
| M04-SEC-004 | T3 HTTP | NFR-PRIV-001 | real API | unauthorized health/run view leaks IDs/detail | permission/subject filtering and safe aggregate | M01/P01/security |
| M04-SEC-005 | T7 logging | NFR-OBS-001 | real multiple accounts/providers | mutable labels/emails/paths enter logs | opaque IDs/safe keys only | security |
| M04-SEC-006 | T3+T6 abuse | NFR-SEC-001 | real clients and enrolled target | refresh burst exceeds coalescing/rate budget | bounded accepted work; no provider hammering | owner/P01 |
| M04-SEC-007 | T6 safety | FR-SAFE-002 | real protected default profile | dispatch invokes non-read-only operation/modifies state | admission rejects unsafe operation; approved reads leave state unchanged | owner/adapter/security |
| M04-SEC-008 | source/contract review | FR-SAFE-002 | repository/OpenAPI/contracts | route/port exposes login/logout/process control/cancel agent | prohibited surface absent | architecture/security |
| M04-SEC-009 | outbound observation | NFR-PRIV-002 | running service/network observation | AgentMonitor analytics/crash traffic exists | outbound traffic limited to approved collection calls | security/operations |
| M04-ARCH-001 | boundary | NFR-ARCH-001/002 | repository checks | M04 imports framework/concrete adapter/other tables | boundary check and review pass | architecture |
| M04-ARCH-002 | provider/platform boundary | NFR-PLAT-001 | repository/contracts | provider/OS conditionals appear in M04 core | only typed ports and capability keys exist | M03/platform |
| M04-ARCH-003 | compatibility | NFR-COMP-001 | contract/event/schema diff tools | breaking semantic change passes as V1 additive | compatible diff or approved major/ADR | integration |
| M04-ARCH-004 | API direction | NFR-API-002 | OpenAPI/generated client/source checks | UI/manual schema duplicates domain or reads DB | generated client and one-way API contract pass | P01/P02 |
| M04-DEP-001 | dependency | NFR-LIC-001 | lockfile/SBOM/scanners | unapproved package enters graph | admission, reproducibility, notices, scan pass | dependency reviewer |
| M04-DOC-001 | documentation | NFR-DOC-001 | maintained docs/runbook | independent developer cannot implement/operate boundary | plan/module/contracts/runbook/evidence links pass review | docs/operations |

### Test integrity and evidence rules

- Pure tests may construct target IDs, schedules, outcome enums, explicit UTC instants, policy values, and deterministic jitter inputs only for side-effect-free policy. They do not claim provider support, rate limits, or live failure behavior.
- SQLite tests use a real file, real Alembic chain, production repository/unit-of-work, and actual concurrent transactions. In-memory SQLite and fake repositories are prohibited.
- Service tests start the production FastAPI composition through its real server and use real IAM/database. Direct route invocation and simulated transports do not count.
- No “test collector,” fake adapter, local fake provider HTTP server, replay/cassette, monkeypatched executor, seeded telemetry, or handcrafted provider row may prove dispatch.
- Successful dispatch, deadline, concurrency, event refresh, failure isolation, and source-selection claims execute an approved current real adapter/system. Dynamic values are asserted by identity/unit/source/freshness/reconciliation, not hardcoded amounts.
- AgentMonitor-owned schedule/load metadata may be generated for repository/performance tests only when clearly labeled as internal workload and never presented as provider accounts or observations.
- Rare rate-limit/auth/wrong-account/unavailable states not naturally/safely present are `Blocked`, not induced by exhausting credits, revoking credentials, logging out, or damaging profiles.
- Every live record identifies opaque account/source aliases, versions, request/cost budget, timestamps, side effects, status, sanitized evidence, cleanup, and owner acknowledgement.
- A missing dependency, unavailable credential, syntax error, or environment setup failure is not meaningful Red. Every behavior gets expected behavioral Red, Green, and post-refactor evidence.
- Test traces, screenshots, videos, reports, logs, DB copies, and CI artifacts are scanned and cannot contain credentials, content, raw provider values, or personal identities.

### Mutation and coverage gate

- Every branch of due/admission, effective-constraint selection, lifecycle, fencing, idempotency, outcome-to-retry, auth recovery generation, retention eligibility, health, and cancellation-target policy receives meaningful coverage.
- Target: 100% of non-equivalent mutants killed in the pure scheduling/admission/state-transition package. Equivalent mutants require independent written classification.
- Adapter/persistence/API line coverage never substitutes for real database/service/provider evidence.

## 10. Implementation increments

Implementation starts only after section 15 is complete and the root changes this plan to Approved.

| Increment | Owned files/area | Failing test first | Minimum production change | Refactor/documentation | Exit evidence |
|---|---|---|---|---|---|
| M04-I00 Contract synchronization | shared contracts/register only under root allocation | M04-PURE-015/018/028, M04-ARCH-003 | freeze CTR-COL-001..006, consumers, errors, activity/result/health seams | contract register/traceability/ADR if required | Approved contracts; no module behavior |
| M04-I01 Pure policy | M04 domain | M04-PURE-001..028 | schedule/activity/jitter/admission/state/retry/backoff/health/retention policies | invariants and policy docs | Red/Green/refactor + mutation baseline |
| M04-I02 Persistence schema | M04 repository ports/adapter + allocated migration | M04-DB-001..003/011/018/022/028 | schedules, requests, runs, warnings/refs tables and repositories | schema/index/port docs | Real migration/query evidence |
| M04-I03 Leases and budgets | M04 domain/app/persistence | M04-DB-004..006/012/013 | fenced leases, scoped concurrency, budget reservations, backoff persistence | concurrency/recovery docs | Real SQLite concurrency evidence |
| M04-I04 Target/activity reconciliation | M04 app consuming frozen M02/M03/M06 contracts | M04-DB-014/027, M04-PURE-005/021 | durable target/policy/activity generation updates and blocks | consumer contract docs | Real composition/DB evidence; no adapter call |
| M04-I05 Manual/event request intake | M04 app/persistence | M04-DB-007..010, M04-HTTP-001..003 | authorized request/trigger idempotency, coalescing, queue state | API/error/idempotency docs | Real DB and real socket evidence |
| M04-I06 Scheduler and supervision | M04 app/composition allocation | M04-PURE-026/027, M04-DB-023/026, M04-PERF-001 | bounded due loop, fairness, instance heartbeat, independent task supervision | operations/health docs | Real service/DB/load evidence without provider claim |
| M04-I07 Real execution boundary | M04 app plus separately owned M03/A04 composition | M04-LIVE-001/002/004/008/010/011/015 | dispatch approved adapter/platform port with deadline/cancellation/admission | provider live matrix/runbook | T6 real-source evidence or explicit Blocked rows |
| M04-I08 Result commit and events | M04 app/persistence + M05/M06 consumer tasks | M04-DB-015..017/024/025, M04-LIVE-009/014 | idempotent receipt, terminal transaction, outbox/delivery | event/result/recovery docs | Real DB and real vertical-slice evidence |
| M04-I09 Retry and recovery | M04 app/persistence | M04-DB-013/014/019/026, M04-LIVE-005..007/012/013 | outcome mapping, durable retry chains, crash reconciliation, isolation | failure runbook/limitations | Pure+DB+available live evidence; rare states visible |
| M04-I10 Health/history/retention | M04 app/persistence | M04-DB-020/021/028, M04-HTTP-005..007, M04-OPS-001..004 | health/run queries, bounded purge, safe diagnostics | API/ops/module docs | Real DB/server/diagnostic evidence |
| M04-I11 P01/P02 integration | separately assigned API/UI/generated paths | M04-HTTP-004..007, M04-BROWSER-001/002 | refresh/run/health routes and generated-client UI | OpenAPI/user/accessibility docs | Real HTTP/build/browser with real data |
| M04-I12 Native lifecycle/hardening | M04 plus separately assigned M08/DEP/platform tasks | M04-OPS-005..010, M04-PERF-002..004, M04-SEC-001..009 | startup/shutdown/restart/upgrade/performance/security hardening | runbook/evidence/risk updates | Independent operations/security/test review |

### Ordering and parallel-development safety

- M04-I00 precedes all code. M04-I01 can then proceed independently because it consumes only frozen value contracts and performs no I/O.
- M04-I02/I03 share the M04 migration chain and are serial under one owner. A read-only reviewer may inspect in parallel.
- M02, M03, M05, M06, M07, and M08 implementations may proceed in parallel only against synchronized contracts. They do not edit M04 internals/tables.
- Provider adapters implement CTR-PROV independently; M04 never edits them. Live scenarios are scheduled to avoid account/request-budget collision.
- Only the central migration owner allocates Alembic order. Only P01 generates OpenAPI. Only P02 regenerates the client. Only root edits the shared contract register during synchronization.
- M04-I07 can run per provider independently after each adapter's capability row is approved, but common M04 executor files remain under one M04 owner.
- M04-I08 consumer implementations are owned by M05/M06. They may work in parallel on separate paths after CTR-COL-006 is frozen; composition wiring is a separately allocated integration edit.
- Any semantic contract gap stops affected work and returns to CS-2. Direct table reads, copied DTOs, generic JSON, concrete adapter imports, or test doubles are prohibited workarounds.

## 11. Documentation outputs

Future implementation must update/create under assigned ownership:

- M04 module document covering purpose, invariants, states, schedule/admission algorithms, contracts, tables, errors, health, and extension seams;
- synchronized collection contracts and shared contract-register/traceability entries;
- M0-to-M04 decision record for every provider/source rate, cost, latency, deadline, concurrency, retry, and auth-failure constraint;
- API/OpenAPI guidance for manual refresh, run/history, health, idempotency, permissions, errors, and units, generated rather than hand-patched;
- configuration registry entries with source/default/range/reload/security/compatibility data;
- migration/index/query-plan notes and PostgreSQL portability assessment;
- scheduler startup/shutdown/restart/clock-anomaly/lease recovery, stale-data, rate-limit, auth-block, outbox-backlog, and troubleshooting runbooks with verified commands only;
- live provider scenario matrix and real owner acknowledgements, including every Blocked/Not Run state;
- security/privacy review and data-minimization proof for DB/WAL/log/outbox/diagnostic/backup artifacts;
- dependency admission/SBOM/notices records, even if the module adds no direct dependency;
- sanitized Red/Green/refactor and DB/HTTP/browser/platform/provider/operations evidence;
- risk-register and known-limitations changes based on observed behavior;
- release notes for contract/schema/config/provider-policy changes and recovery requirements.

### Required implementation handoff packet

Every M04 implementation assignment returns the repository handoff template populated with:

- exact requirement/acceptance IDs and increment/scenario IDs addressed;
- plan, M04 contract, consumed contract, schema revision, configuration-policy, adapter, and provider/platform versions;
- all files changed, including centrally allocated shared/generated/migration files;
- meaningful Red command/time/failure, Green command/time/result, and post-refactor command/result for each behavior;
- real SQLite/HTTP/browser/platform/provider/operations evidence actually executed and every Failed, Blocked, or Not Run item;
- run/account aliases and evidence references sanitized under the live-verification rules, with owner acknowledgement where interactive;
- contract/API/schema/config compatibility classification and migration/backup/recovery evidence;
- security/privacy/secret/content/default-profile/process-control review and artifact-scan result;
- dependency/license/lock/SBOM/notices impact, including an explicit “no new dependency” statement when applicable;
- known limitations, residual risks, rollback state, and the exact next integration step.

Completion claims without inspectable evidence or with an unavailable boundary described as Passed are rejected.

## 12. Dependency and license impact

No dependency is approved or may be installed by this draft.

| Candidate | Purpose/scope | Preferred alternative | Admission status/requirements |
|---|---|---|---|
| Python standard-library async/task/time/hash primitives | scheduler loop, task supervision, monotonic time, deterministic hash-based jitter | use approved runtime directly | no package admission, but API/security/portability review required |
| SQLAlchemy/Alembic selected by foundation | M04 persistence/migrations only | project-wide selected persistence stack | Pending project admission; domain cannot import |
| FastAPI/uvicorn/Pydantic selected by P01/foundation | external HTTP mapping only | project-wide selected boundary | Pending project admission; no M04 core import |
| Foundation-selected test/property/mutation tools | T1/T2/T3/concurrency/mutation evidence | admitted equivalents with no mocking plugin | Pending development-dependency admission |
| Separate scheduler/queue library | none currently justified | standard library + durable M04 state | **Not proposed**; adding APScheduler/Celery/RQ/etc. needs a new necessity/distribution/telemetry/transitive review |

The module should add no direct runtime dependency solely for cron, retries, jitter, semaphores, leases, or a process-local queue. If measurement proves standard-library/task supervision insufficient, implementation stops and submits a dependency/architecture proposal. All actual selected packages require exact version, canonical license, transitive licenses, maintenance/security/provenance, platform/native component, install-script/telemetry, lock/SBOM/notices, alternatives, and removal-cost approval.

## 13. Risks and unresolved decisions

### Risks

| Risk/question | Likelihood/impact | Mitigation or experiment | Owner | Trigger/deadline | Status |
|---|---|---|---|---|---|
| R-001/R-024 source has no stable authorized polling interface | High/Critical | M0 Supported/Unsupported decision; no automated polling when unknown/private source required | M03/adapter/security | Before CS-2 | Open/M0-blocked |
| R-002 provider format/version changes mid-run | High/Major | manifest generation recheck, versioned adapter, compatibility block, no parse guessing | M03/adapter/M04 | Every provider upgrade | Open |
| R-006 duplicate/concurrent collectors exceed rate limits | Medium/Major | fenced lease, scoped budget reservation, one run per target, real concurrency tests | M04/persistence | Before M04-I07 | Open |
| R-007 failure/stale data appears current | Medium/Critical | no cached-as-new completion; explicit run/health state and consumer freshness ownership | M04/M05/M06/UI | CS-2/API review | Open |
| R-009 rare states unavailable under no-simulation rule | High/Major | pure policy evidence plus visible Blocked T6 scenario; do not manufacture | test/integration/owner | Release matrix | Accepted project risk |
| R-010 collection consumes credits/disrupts development | Medium/Major | M0 request/cost budget, coalescing, owner schedule, zero billable generation | M04/live operator | Every live packet | Open |
| R-011 SQLite contention stalls scheduler | Medium/Major | short transactions, no I/O in transaction, indexed batches, real concurrency measurement | persistence/M04 | M04-I02..I12 | Open |
| Service crashes after provider call but before terminal commit | Medium/Major | durable pre-call state/budget, commit-status reconciliation, conservative retry | M04/M05/M06 | Before M04-I09 | Open |
| Consumer result sink unavailable loses an observation | Medium/Major | typed failure, no raw M04 storage, later bounded recollection, visible stale state | M04/M05/M06 | CS-2 decision | Open |
| Activity signal semantics cause one-minute over-polling | Medium/Major | versioned producer/evidence TTL, unknown -> idle cadence, M0 source minimum wins | M06/M04 | CS-2 | Open |
| Manual refresh permission too broad | Medium/Major | dedicated permission proposal, rate/coalescing, CSRF/idempotency | M01/P01/security | CS-3 | Open |
| Lease timing conflicts with long provider deadline | Medium/Major | formula validation, heartbeat/fencing, live timing evidence | M03/M04/operations | Before source approval | Open |
| Clock jump creates burst or indefinite delay | Medium/Major | dual-clock detection, pause/recompute, no missed-interval replay, T7 evidence | M04/operations | M04-I12 | Open |
| Shutdown cancellation affects monitored process | Low/Critical | owned execution handle only, no process-control imports, real pre/post verification | M04/A04/security | M04-I12 | Open |
| Outbox backlog grows or duplicates alerts | Medium/Major | per-consumer durable state, idempotent event IDs, bounded health/backoff | M04/M07/M08 | M04-I08/I10 | Open |
| Unknown provider SDK hidden retries violate budget | Medium/Critical | disable/prove/account every retry; block source if unknown | adapter/M03/dependency reviewer | Adapter approval | Open |
| Mac portability silently broken | Medium/Major | platform-neutral core and real macOS Blocked/Passed status | platform/M04 | V1 review | Open |
| Unapproved scheduling dependency enters graph | Medium/Critical | standard-library-first; admission gate/lock/SBOM/notices | dependency reviewer | Before import/install | Open |

### Contract decisions requiring root synchronization

These decisions can materially change other modules and block approval:

1. Freeze canonical target identity and required/optional account/profile/resource/installation combinations per capability.
2. Approve the `active`/`idle`/`unknown` definitions, M06 activity contract, evidence TTL, and event-refresh producers.
3. Approve exact cadence jitter range, due calculation anchor, missed-interval behavior, fairness rule, and manual/event trigger priority.
4. Freeze M03 deadline/cancellation context and prove whether provider SDKs/CLIs contain hidden retries.
5. Freeze source-policy fields for minimum interval, rate/request windows, cost classification, maximum concurrency, output size, and retry eligibility; unknown must block.
6. Approve one-invocation-per-run and zero hidden-retry V1 policy.
7. Freeze outcome-to-terminal/retry/block table, including partial, invalid data, unavailable, auth recovery, and Retry-After semantics.
8. Confirm Draft-aligned CTR-COL-006 and freeze idempotent result commit/status/run-generation/schema/digest/receipt behavior with M05/M06.
9. Freeze CTR-COL-003/004 and CTR-COL-007 event/query schemas, per-schedule ordering, explicit recovery generations, registered consumers, and CTR-EVT-001 outbox/receipt/checkpoint/retention behavior.
10. Freeze `CollectorHealthV1` aggregate/detail disclosure, CTR-COL-007 current-alert inputs, and M08 readiness/health aggregation behavior.
11. Approve manual refresh permission/scope, P01 202/idempotency/problem mapping, per-principal abuse limits, and UI request/run behavior.
12. Approve all run/schedule/request/error/state enum meanings and forward-unknown behavior.
13. Approve lease/fencing/heartbeat formula, crash interruption semantics, request-budget conservative accounting, and clock-anomaly policy.
14. Allocate table names, migration order, cross-module scalar IDs, outbox infrastructure, and repository transaction responsibilities.
15. Approve configuration key names, defaults/ranges/reload rules, especially concurrency, tick, queue, lease, shutdown, and jitter.
16. Approve retention interaction with undelivered events, active run references, backup/restore, and M08 purge orchestration.
17. Complete dependency/license/security review for foundation, persistence, server, and test/mutation packages; confirm M04 adds no scheduler library.
18. Decide whether durable commit/outbox/fencing or future worker extraction warrants a new ADR.

### M0 evidence required before approval

For every automated source M04 requires an accepted handoff row with:

- provider/product/source/capability and exact verified versions/account/plan/credential-role scope;
- source class/stability and proof the operation is read-only, including default-profile effects;
- exact request operation category and whether any hidden pagination/retry multiplies calls;
- minimum safe interval, rate window/scope/units, concurrency ceiling, provider Retry-After behavior;
- possible monetary/provider-credit cost and approved zero/maximum budget;
- latency distribution evidence sufficient for deadline/lease planning, response/output bound, and cancellation behavior;
- outcome/auth/authorization/unavailable/rate-limit distinctions observed or explicitly Blocked;
- owner interaction requirements and source downgrade prohibition;
- freshness/data-latency information needed by consumers;
- sanitized evidence references and capability decision.

Unknown rate/cost, side effects, credential role, retry multiplication, or source stability blocks automated polling for that source. It does not authorize a “safe-looking” default.

## 14. Delivery and rollback

### Delivery order

1. Complete M0 and accept the isolated M04 evidence handoff.
2. Synchronize CTR-COMMON/M02/M03/M04/M05/M06/M07/M08/M01/P01 contracts and update the register.
3. Approve configuration, schema/migration, dependency, threat, test, and this module plan.
4. Deliver pure policy and repository behavior without composing provider execution.
5. Deliver leases/budgets/reconciliation/request intake/scheduler health against real SQLite and real service.
6. Integrate one approved provider source as a real vertical slice through result commit/history/event/API.
7. Expand per-provider only after each capability policy/live matrix passes.
8. Deliver API/UI and operations/restart/shutdown/performance/security hardening.

### Compatibility and exposure

- Keep scheduler disabled for a source until its synchronized policy/capability is approved and the real adapter version is compatible.
- A new provider/capability/source adds a schedule policy and adapter registration; it does not add provider conditionals to M04.
- Additive nullable contract fields remain compatible only with safe defaults. State meaning, target identity, time/unit, idempotency, ordering, retry, delivery, or cost semantics require a new major/ADR and consumer migration.
- Old and new application binaries must not run concurrently against incompatible lease/event schema. Schema compatibility prevents unsafe startup.
- Manual refresh API exposure follows real scheduler readiness; it never exists as a synchronous direct provider route.

### Rollback and recovery

- Create and verify a real SQLite backup before M04 schema/config migrations.
- Prefer forward-fix for additive schema. Never run an unverified destructive downgrade against the only database.
- Disable new dispatch before rollback; let bounded work finish or follow shutdown policy.
- Preserve schedule/run/budget/outbox state. A prior binary may resume only if schema/contract/policy compatibility is explicitly verified.
- On restore, scheduler remains paused until M04 reconciles instance heartbeats, expires/re-fences leases, marks uncertain external requests conservatively, verifies consumer commit receipts, and resumes outbox delivery.
- Rollback never deletes provider profiles, changes authentication, or manipulates monitored agents.

### Post-deployment checks

- Scheduler lifecycle/heartbeat/database/outbox health is truthful.
- Every enabled target has one schedule and an approved current capability/source policy.
- Active/idle cadence, source minimum, concurrency, deadline, and request budget are effective as documented.
- Manual duplicate requests join one run and return quickly.
- A real successful run links to a real consumer observation and completion event.
- Blocked/unsupported/auth/failure states remain visible and do not fabricate current values.
- Restart recovers leases/runs/outbox without unsafe duplicate dispatch.
- Browser closure does not stop collection.
- Shutdown leaves representative running agents/default profiles unchanged.
- Logs, DB/WAL, backup, diagnostics, API, browser, and evidence contain no prohibited secrets/content/raw provider payload.

## 15. Definition of ready

Implementation remains blocked until every applicable item is checked by the named reviewers:

- [ ] M0 M04 handoff is complete, accepted, and contains exact rate/cost/auth/deadline/concurrency evidence for every source intended for implementation.
- [ ] Requirements, approved interpretations, non-goals, and one-invocation-per-run policy are owner-reviewed.
- [ ] This plan is approved and status/version updated by root/integration steward.
- [ ] Exact owned/allowed/shared/forbidden paths and implementation-agent assignments are allocated without overlap.
- [ ] CTR-COL-001..007 are synchronized, versioned, and entered in the contract register.
- [ ] Common target/provenance/time/event primitives are approved.
- [ ] M02 target/profile/resource/protection/monitoring and registry-change contracts are approved.
- [ ] M03 protocol/manifest/source/outcome/auth/deadline/cancellation/rate-cost contracts are approved for intended adapters.
- [ ] M06 activity signal/TTL and approved event trigger semantics are frozen.
- [ ] M05/M06 result-commit ownership/idempotency/reconciliation is approved without M04 observation persistence.
- [ ] M07/M08 event/health/outbox/retention consumers approve semantics and failure isolation.
- [ ] M01/P01 approve manual permission, authorization, CSRF, idempotency, 202/run resource, problem, and query-disclosure contracts.
- [ ] Schedule, lease, fencing, queue, fairness, budget, backoff, clock, shutdown, and crash-recovery decisions are approved.
- [ ] M04 tables/constraints/indexes/transactions/retention and shared migration order are approved; backup/recovery exists.
- [ ] Configuration names/defaults/ranges/reload/diagnostic visibility are allocated in the registry.
- [ ] Every scenario has the right real boundary, meaningful expected Red, safe cleanup/evidence handling, and assigned owner.
- [ ] Real SQLite/server/browser/Linux/provider accounts and owner coordination are scheduled; unavailable rare/macOS scenarios remain visible as Blocked.
- [ ] Security/privacy/threat/risk reviews resolve or explicitly accept every Critical item.
- [ ] Dependency/license admission and lock/SBOM/notices plan are complete before any package import/install.
- [ ] Any required ADR is accepted.
- [ ] No unresolved decision permits materially different implementations.

### Stop conditions during implementation

Stop and return to root synchronization if work would:

- change a contract state/unit/time/idempotency/retry/order/permission meaning;
- add a source/provider fact absent from the M0 handoff or expand a verified version/account scope without live evidence;
- call a source whose request/rate/cost/side-effect/deadline/retry behavior is unknown;
- import concrete provider/platform code, another module's internals/table, or edit an unallocated shared path;
- persist/copy raw provider outcomes or capacity/runtime fields in M04;
- add a dependency before admission or discover hidden SDK retries/telemetry/install behavior;
- need a mock/fake/stub/emulator/recording/demo account/seeded telemetry/test-only path to pass;
- retry authentication/user-action/wrong-account/invalid-version failure without authoritative recovery;
- make a provider call before durable lease/run/budget state exists;
- expose provider I/O synchronously in an HTTP handler;
- signal/kill/restart/attach/inject into a monitored agent or modify a protected/default profile;
- perform a destructive migration/restore without explicit approval and verified backup;
- expose a secret/content/raw provider response, which triggers immediate incident handling.

## 16. Approval record

| Reviewer | Decision | Conditions/findings | Date | Approved versions |
|---|---|---|---|---|
| Root/integration steward | Pending | Decisions 1–18, register update, and CS-2 required | — | — |
| Product owner | Pending | Cadence/activity/manual-refresh behavior and M0 limitations | — | — |
| M02 Registry owner | Pending | Target/profile/resource/protection/reconciliation contract | — | — |
| M03 Provider-system owner | Pending | Protocol/outcomes/source/rate-cost/deadline/cancellation evidence | — | — |
| M05 Capacity owner | Pending | Idempotent result commit/receipt and observation references | — | — |
| M06 Runtime-observation owner | Pending | Activity/result commit/platform scheduling contract | — | — |
| M07 Alerting owner | Pending | Failure/completion/recovery event semantics | — | — |
| M08 Operations owner | Pending | Health/outbox/retention/restart/diagnostics seams | — | — |
| M01/P01 owners | Pending | Permission, auth, idempotency, API/background resource mapping | — | — |
| Persistence/migration owner | Pending | DDL/index/fencing/concurrency/outbox/migration/recovery review | — | — |
| Security/privacy reviewer | Pending | Read-only admission, abuse, cancellation, secret/content proof | — | — |
| Test-integrity reviewer | Pending | Real-boundary scenario matrix and evidence-safety review | — | — |
| Dependency/license reviewer | Pending | Confirm no scheduler dependency and admit shared/test stack | — | — |

No production code, dependency installation, migration, `.env`, provider command, account access, live authentication, API route, generated artifact, frontend, service change, or external resource is authorized by this Draft plan.
