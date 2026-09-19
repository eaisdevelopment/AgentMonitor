# Module plan: M07 — Alerting

- Status: **Draft — upstream event synchronization and approval pending; implementation is not authorized**
- Plan version: `0.2.0-draft`
- Proposed module contract bundle: `alerting.v1`
- Contract-register baseline: `0.2.0` Draft-aligned (`CTR-ALERT-001` through `CTR-ALERT-005` plus required upstream contracts); not synchronized or approved
- Primary owner: M07 alerting implementation role (unassigned)
- Required reviewers: owner, root/integration steward, M02 Registry, M03 Provider system, M04 Collection control, M05 Capacity, M06 Runtime observation, M08 Operations, P01 API, P02 UI, persistence/migration, security/privacy, test-integrity, and dependency/license owners
- Primary requirements: FR-ALERT-001..006; alert-owned portions of FR-HIST-001..005; FR-SAFE-001/002
- Supporting requirements: FR-ORG-003, FR-AUTH-001, FR-QUOTA-003..005, FR-BUDGET-002, FR-STATE-001..004, FR-COL-004..006/008, NFR-ARCH-001/002, NFR-API-001/002, NFR-DATA-001, NFR-TEST-001/002, NFR-SEC-001, NFR-PRIV-001/002, NFR-DOC-001, NFR-LIC-001, NFR-PLAT-001, NFR-PERF-001, NFR-RES-001, NFR-OBS-001, NFR-COMP-001
- Acceptance contribution: AC-V1-001..008, AC-UI-002..006, AC-PROC-005, AC-ALERT-001..003, AC-HIST-002, AC-OPS-003..006, AC-TEST-001..006
- Primary risks: R-005, R-007, R-008, R-009, R-011, R-014, R-016, R-017, R-018, R-019, R-020
- Dependencies: approved common/configuration/database contracts; synchronized M02 scope, M03 auth vocabulary, M04 collection, M05 capacity, and M06 runtime contracts; M01 authorization; persistence adapter; P01/P02 transport and presentation; M08 retention/export/health orchestration
- Target milestone: M3 after capacity/runtime/collection contracts, before final API/UI alert workflows
- Approved by/date: pending

This plan is governed by the [product requirements](../../../product/requirements.md), [V1 acceptance criteria](../../../product/v1-acceptance-criteria.md), [module boundaries](../../../architecture/modules.md), [contracts and versioning](../../../architecture/contracts-and-versioning.md), [data model](../../../architecture/data-model.md), [security architecture](../../../architecture/security.md), [testing strategy](../../../engineering/testing-strategy.md), [completion and automation gates](../../../engineering/completion-and-automation-gates.md), and [contract register](../../contract-register.md). Structural values and event shapes in this plan are design proposals, never provider observations, live evidence, seeded telemetry, or permission to implement.

## CS-1 Draft-alignment addendum

This `0.2.0-draft` revision adopts contract-baseline `0.2.0` and the parallel-ownership manifest as its concrete CS-1 review position. It remains Draft; upstream contracts are not Synchronized/Approved and all M07 scenarios remain `Not Run`.

- M07 consumes M02 CTR-REG-009 for bounded current scope/subject resolution and CTR-REG-010 for durable provider authentication-health changes. It consumes M04 CTR-COL-007 for current collector health and explicit recovery generations, M05 CTR-CAP-008/009 for forecast/availability transitions, and CTR-EVT-001 for durable delivery/receipt/checkpoint/replay. Raw CTR-PROV-006 outcomes never reach alert evaluation.
- M07 retains sole ownership of alert activation thresholds, specificity/precedence, fingerprinting, lifecycle, acknowledgement, snooze, recovery, and dashboard notification truth. M05 owns normalized capacity health and does not consume M07 policy, so no M05↔M07 cycle exists.
- Every upstream condition stream must supply a producer-owned generation and explicit newer inverse/current evidence. Recovery is forbidden on silence, event absence, later generic collection success, a stale/unknown/unsupported/unavailable value, consumer restart, or expired cache. After a missed/replayed delivery, M07 uses the producer's named current-state query, compares generation/checkpoint, then records one recovery or keeps the alert open/degraded.
- Field states use CTR-COMMON-007. Published and consumed events use CTR-COMMON-006 plus CTR-EVT-001; the M07 consumer receipt/checkpoint is committed atomically with alert state/history/outbox changes. M07 implements M08-owned CTR-OPS-006 and CTR-OPS-007 leaf participant ports.
- M07 adopts CTR-EVT-TOPOLOGY-001: it owns `alert_event_outbox` and its existing `alert_event_receipt`/checkpoint state under `alert_*`. PLAN-DB's dispatcher uses only published M07 event-storage ports; it owns no central event table and performs no cross-module SQL.
- The V1 public contract file is `backend/src/agentmonitor/contracts/alerting_v1.py`; SQLite implementation files are only under `backend/src/agentmonitor/adapters/persistence/alerting/sqlite/**`. M07 owns `alert_*` tables and `v1_0700..v1_0799`; PLAN-DB serializes the migration head.
- Alignment is verified by existing scenarios M07-PURE-012..047, M07-DB-006..025, M07-LIVE-001..011, M07-OPS-001..004, and M07-ARCH-001..006. Their real-boundary prerequisites and `Not Run` status are unchanged.

## 0. Authority, evidence state, and completion boundary

The current authority is planning only. This document does not authorize production code, dependency installation, a database migration, configuration changes, provider/account access, deployment, Git/GitLab mutation, or live testing.

M07 is not implementation-ready merely because its internal state machine is detailed. It depends on upstream events that must carry enough safe truth to open **and recover** an alert without M07 querying another module's tables or interpreting raw provider output. The synchronization items in section 13 therefore block approval.

At planning time:

- all M07 scenarios are `Not Run`;
- no alert contract is Approved or Implemented;
- no live provider, collection, runtime, HTTP, browser, database, or migration result is claimed;
- no email, native desktop, messenger, push, webhook, or remote notification behavior is planned for V1;
- no constructed capacity, account, session, collector, or provider observation may enter an I/O test;
- passing the future planning gate means only that plans are structurally synchronized, not that M07 works.

The canonical planning gate remains:

```bash
python3 tools/planning/validate_plans.py --stage synchronized
```

It must be run by the integration steward after this plan and all other catalog artifacts exist. This module plan alone cannot make that command green and must not be reported as a complete V1 planning set.

## 1. Outcome and boundaries

### 1.1 Outcome

M07 turns versioned capacity, authentication, collector, and runtime condition changes into a durable, low-noise dashboard alert lifecycle. It applies deterministic scope precedence, preserves uncertainty and evidence, deduplicates at-least-once input, and lets the authenticated owner read, acknowledge, snooze, and review alerts without changing the source observations.

The outcome is measurable when:

1. `account > provider > organization > global` policy precedence is exact and visible for every evaluated subject.
2. The built-in capacity fallback warns at 30% remaining and becomes critical at 15% remaining, using exact basis-point comparison rather than binary floating point.
3. Exhausted or explicitly unavailable capacity, predicted exhaustion, re-authentication required, stale data, collector failure, possible stall, and verified recovery/reset conditions have explicit non-overlapping rules.
4. Duplicate or out-of-order source events cannot produce polling noise, double-count occurrences, regress severity, or recover a newer active condition.
5. One stable fingerprint owns repeated, escalated, acknowledged, snoozed, recovered, and reopened history for one condition stream.
6. Unknown, unsupported, unavailable, stale, and zero remain distinct; no unknown or stale metric is treated as zero, exhausted, available, or recovered.
7. Dashboard notifications have durable unread, acknowledgement, snooze, recovery, and history behavior while REST remains authoritative.
8. A rule change or account move is re-evaluated through public query/event contracts and never by reading M02/M04/M05/M06 tables.
9. Real SQLite, real loopback HTTP, the real built UI/browser, and naturally available real provider/process conditions supply the evidence they claim; unavailable live conditions remain Blocked.
10. V1 emits no external notification and performs no provider, profile, collection, or running-process control action.

### 1.2 In scope

- Alert rule identity, scope, enablement, version, and typed configuration.
- Exact scope resolution across global, organization, provider, and account levels.
- Built-in global capacity fallback of warning `3000` basis points and critical `1500` basis points remaining.
- Alert signal validation and deterministic condition evaluation from synchronized upstream contracts.
- Alert condition types and fixed default severity policy.
- Stable fingerprint construction and collision-safe identity handling.
- At-least-once input-event receipt, ordering, idempotency, deduplication, and replay behavior.
- Alert lifecycle, occurrence generations, severity transition, repetition count, acknowledgement, snooze, unread state, recovery/reset, reopen, and close-by-configuration.
- Dashboard notification current/unread/history projection.
- Alert rules, alerts, evidence references, immutable state events, command receipts, deadlines, outbox records, migrations, retention, and repository ports.
- Bounded rule re-evaluation jobs after policy or registry-scope changes.
- M07 component health, sanitized diagnostics, retention participation, backup/restore validation, and structured local operational measurements.
- Published application ports/events under `CTR-ALERT-001..005`.

### 1.3 Out of scope

- Fetching quota, budget, authentication, collector, process, or session data.
- Calling provider adapters, provider APIs/CLIs, platform APIs, or credential/profile stores.
- Computing capacity health, burn rate, forecast, collector health, runtime state, stall evidence, or identity correlation.
- Modifying an upstream observation, freshness deadline, collection schedule, profile, account, or runtime session.
- Sending email, native Linux/macOS notifications, messenger messages, webhooks, push notifications, SMS, or third-party incidents in V1.
- Creating an `adapters/notifications` implementation in V1; published events are not permission to add a delivery adapter.
- Browser-local-only alert state or notification truth.
- Prompt, response, tool, source-code, terminal-output, arbitrary environment, credential, provider raw payload, or free-form external error capture.
- Killing, restarting, pausing, interrupting, injecting into, switching credentials inside, or routing a running agent.
- Near-real-time streaming as an availability requirement. A future SSE projection may carry M07 events, but REST stays authoritative and SSE is owned by P01.
- Remote hosting, multi-user authorization, or cross-user notification delivery.

### 1.4 Ownership

M07 owns:

- `AlertRule`, `Alert`, `AlertOccurrence`, `AlertEvidenceReference`, `AlertEvent`, `AlertEventReceipt`, `AlertCommandReceipt`, `AlertDeadline`, and `AlertReevaluationJob` concepts;
- rule precedence, threshold validation, condition-to-severity mapping, fingerprinting, state transitions, deduplication, acknowledgement, snooze, unread, recovery, and reopen invariants;
- the `alert_*` logical tables, indexes, repositories, migrations, and retention eligibility rules;
- the `alerting.v1` contract semantics and M07-owned event payloads;
- dashboard notification projection semantics, not UI rendering or transport;
- alerting component health and safe diagnostic fields;
- M07 test/evidence matrix and module/operator documentation.

M07 does not own upstream signal truth, registry membership, transport authentication, REST paths, generated clients, UI state components, the common event dispatcher, database engine configuration, backup orchestration, or future external delivery.

### 1.5 Allowed implementation paths

After approval, an M07 implementation agent may own only:

```text
backend/src/agentmonitor/modules/alerting/**
backend/src/agentmonitor/adapters/persistence/alerting/sqlite/**
backend/tests/alerting/**
backend/tests/integration/alerting/**
docs/modules/alerting.md
docs/test-evidence/alerting/**                 # sanitized evidence only, if allocated
```

Shared paths require explicit per-change allocation by the integration steward:

```text
backend/src/agentmonitor/contracts/alerting_v1.py
backend/migrations/versions/<allocated-m07-revision>.py
backend/src/agentmonitor/composition/**
backend/tests/contract/**
OpenAPI source/generation inputs and generated artifacts
configuration registry, event/outbox registry, traceability, and runbooks
```

M07 must not edit or import implementation internals from:

```text
backend/src/agentmonitor/modules/registry/**
backend/src/agentmonitor/modules/provider_system/**
backend/src/agentmonitor/modules/collection_control/**
backend/src/agentmonitor/modules/capacity/**
backend/src/agentmonitor/modules/runtime_observation/**
backend/src/agentmonitor/modules/operations/**
backend/src/agentmonitor/adapters/providers/**
backend/src/agentmonitor/adapters/platform/**
backend/src/agentmonitor/api/**
frontend/**
```

### 1.6 Allowed and forbidden dependencies

M07 domain/application code may import only the approved standard library, its own domain/application types, and synchronized contract packages for `CTR-COMMON-001/002/003/004/006`, `CTR-IAM-001/002`, `CTR-REG`, `CTR-PROV-006` vocabulary only as resolved in section 4, `CTR-COL`, `CTR-CAP`, `CTR-RUN`, `CTR-OPS-006`, and repository/UoW ports.

Persistence adapters may import the approved persistence stack and M07 repository ports. Composition may wire event consumers, rule re-evaluation query ports, P01 mappings, M08 health/retention, and the common dispatcher. P01/P02 consume only M07 published contracts.

The M07 domain must not import FastAPI, Starlette, Pydantic transport schemas, SQLAlchemy, Alembic, provider SDKs/CLIs, OS/process/filesystem/network code, React/UI code, another module's ORM entity, or a concrete event bus. It must not:

- query or write another module's table;
- import a provider adapter or branch on Claude/Codex/Ollama implementation details;
- deserialize generic provider dictionaries or raw event payload bags;
- calculate capacity forecasts, collection freshness, process progress, or auth health itself;
- contain a general `utils` package, test-only event injector, demo-alert endpoint, or notification-delivery switch;
- read `.env`, provider files, process environments, or owner operational data directly.

## 2. Requirements and traceability

| Requirement/AC | Planned M07 behavior | Contract | Test/scenario IDs | Evidence gate |
|---|---|---|---|---|
| FR-ALERT-001 | Resolve one whole rule by account > provider > organization > global, with explicit scope/revision evidence and no field-wise merge | CTR-ALERT-001; consumes CTR-REG-001/002/007 | M07-PURE-001..006, M07-DB-001..004, M07-HTTP-001/002 | Pure policy plus real persisted configuration/HTTP |
| FR-ALERT-002 | Built-in fallback uses warning 3000 bp and critical 1500 bp; authorized rules may override within validation bounds | CTR-ALERT-001 | M07-PURE-007..011, M07-DB-005, M07-HTTP-003, M07-BROWSER-001 | Exact pure boundaries plus real configuration workflow |
| FR-ALERT-003 | Model capacity exhaustion/unavailability, forecast exhaustion, auth attention, stale data, collector failure, possible stall, and source-proven recovery/reset | CTR-ALERT-002..004; consumed signal contracts | M07-PURE-012..021, M07-LIVE-001..009 | Pure evaluator plus naturally available real signals |
| FR-ALERT-004 | Canonical fingerprint, receipt dedupe, stream generation, repeat counting, ordering, and lifecycle suppress polling noise | CTR-ALERT-002..004 | M07-PURE-022..033, M07-DB-006..012, M07-LIVE-010 | Pure reducer plus real SQLite and real event path |
| FR-ALERT-005 | Durable severity, unread, acknowledge, snooze, recovery, reopen, and history projection | CTR-ALERT-002/004/005 | M07-PURE-034..044, M07-DB-013..018, M07-HTTP-004..009, M07-BROWSER-002..006, M07-LIVE-011 | Pure/real DB/HTTP/browser/live lifecycle |
| FR-ALERT-006 | Dashboard-only V1; no delivery adapter, credentials, external egress, or external-send command | CTR-ALERT-003/004/005 | M07-ARCH-001/002, M07-SEC-001/002, M07-BROWSER-007 | Surface/import/network/config review |
| FR-HIST-001 | Retain alert rules/revisions, alerts, evidence refs, events, receipts, and terminal history for at least 365 days | M07 persistence; CTR-ALERT-002/005 | M07-PURE-045, M07-DB-019/020, M07-OPS-001 | Pure cutoff plus real DB purge/backup |
| FR-HIST-002 | Provide bounded active/history ordering and transition timeline for useful ranges | CTR-ALERT-002/005 | M07-PURE-046, M07-DB-021/022, M07-HTTP-010, M07-BROWSER-006 | Real indexed DB/API/browser |
| FR-HIST-003 | M08-triggered idempotent batched purge removes only eligible terminal history and records safe results | retention port | M07-PURE-045, M07-DB-019/020, M07-OPS-001 | Pure cutoff plus real transaction |
| FR-HIST-004 | Export only through M08 query ports with bounded alert/rule/history data and no prohibited fields | CTR-ALERT-002/005 | M07-SEC-003, M07-OPS-002 | Real export/secret scan owned with M08 |
| FR-HIST-005 | Store UTC; P02 renders configured timezone while details expose UTC | CTR-COMMON-002, all M07 contracts | M07-PURE-047, M07-DB-023, M07-BROWSER-008 | Pure time rule, real DB round trip/browser |
| FR-SAFE-001 | Permit alert configuration, acknowledgement, read state, snooze, and explicit query only | M07 command surface | M07-ARCH-001/003, M07-HTTP-001..010 | Contract/API surface review |
| FR-SAFE-002 | Publish no provider/profile/process control, routing, credential switching, or input-injection command | Entire module | M07-ARCH-001..004, M07-SEC-002 | Import/API/schema absence checks |
| FR-ORG-003 | Resolve organization scope and expose organization/global alert projections without owning other aggregates | CTR-REG-001/002/007; CTR-ALERT-002/005 | M07-PURE-001..006, M07-DB-024, M07-HTTP-010 | Scope contract plus real persisted query |
| FR-AUTH-001 | Open auth-attention only from synchronized healthy/expiring/reauth/revoked/wrong/unknown transitions; unknown is not reauth-required | CTR-REG-010 using CTR-PROV-006 vocabulary | M07-PURE-016/017, M07-LIVE-004/005 | Pure mapping plus real auth condition |
| FR-STATE-003/004; AC-PROC-005 | Open possible-stall only from M06 evidence and recover from a newer CTR-RUN-004 transition away from `possibly_stuck`; observable user/permission waits do not signal stall | CTR-RUN-004/005 | M07-PURE-020/021/031, M07-LIVE-008/009 | M06 pure/platform/live plus M07 event path |
| FR-COL-004/005/006/008 | Preserve source/event/provenance refs and explicit stale/unavailable/unsupported meanings; never invent current telemetry | CTR-COL-003..005/007 | M07-PURE-014/018/019/029, M07-LIVE-006/007 | Contract validation and real event evidence |
| NFR-ARCH-001/002 | Isolated domain, owned tables, typed ports/events, one-way imports, no direct table access | alerting.v1 | M07-ARCH-001..006 | Automated boundary/ownership gate |
| NFR-API-001/002 | P01 maps contracts to `/api/v1`; P02 uses generated client only | CTR-API-001, CTR-UI-001 consuming CTR-ALERT | M07-HTTP-001..010, M07-BROWSER-001..008 | Real service/OpenAPI/client/browser |
| NFR-DATA-001 | Real SQLite migrations/repositories retain PostgreSQL-portable domain semantics | CTR-DB-001/002 | M07-DB-001..024, M07-OPS-003 | Fresh/upgrade/restore/query-plan real DB |
| NFR-TEST-001/002 | Strict R/G/R at claimed boundary, no doubles/recordings/seeded telemetry/placeholder alerts | Test evidence | Every M07 ID; M07-TEST-001/002 | Evidence review and prohibited-pattern scan |
| NFR-SEC-001, NFR-PRIV-001/002 | Authorized mutations, minimized typed facts, safe IDs/codes, no content/secrets/external telemetry | alerting.v1 | M07-SEC-001..008 | Source/schema/log/DB/API/artifact/network review |
| NFR-DOC-001 | Contracts, rule semantics, lifecycle, operations, migrations, tests, and limitations are maintained | Documentation outputs | M07-DOC-001..003 | Documentation automation/review |
| NFR-LIC-001 | No M07-specific dependency without admission; release SBOM/notices remain accurate | Dependency gate | M07-DEP-001 | Manifest/lock/SBOM/license review |
| NFR-PLAT-001 | M07 is OS-neutral; platform-specific evidence arrives only through M06 | Alerting contracts | M07-ARCH-005, M07-LIVE-008 | Boundary check; real Linux source evidence |
| NFR-PERF-001 | Indexed, bounded rule/event/notification paths support at least 100 registered accounts and 200 simultaneously discovered real processes without redesign | repositories/query contracts | M07-PERF-001/002 | Exact real account/process scale evidence or Blocked; session-only load is supplemental |
| NFR-RES-001 | Invalid/out-of-order event or one failed source consumer cannot stop unrelated evaluation/API reads | inbound ports/repositories | M07-PURE-028..033, M07-DB-010..012, M07-LIVE-010 | Pure/DB/real event isolation |
| NFR-OBS-001 | Structured logs/events contain safe IDs, versions, codes, counts, duration, correlation only | CTR-ALERT-003/004; CTR-FND-004 | M07-SEC-004/005, M07-OPS-004 | Log/diagnostic inspection |
| NFR-COMP-001 | Alert DTO/event/DB changes follow versioning; incompatible inputs fail visibly | CTR-ALERT-001..005 | M07-PURE-024/032, M07-DB-025, M07-ARCH-006 | Compatibility/migration/event tests |
| AC-ALERT-001 | Precedence is proved in pure tests and with real persisted rules | CTR-ALERT-001 | M07-PURE-001..011, M07-DB-001..005, M07-HTTP-001..003 | Required acceptance evidence |
| AC-ALERT-002 | Running application/database/browser exercises dedupe, transition, acknowledge, snooze, recover, and retained history | CTR-ALERT-002..005 | M07-DB-006..022, M07-HTTP-004..010, M07-BROWSER-002..006, M07-LIVE-011 | Real full-stack event condition; no synthetic alert |
| AC-ALERT-003 | Real stale collector and re-authentication-required conditions traverse the complete event path | consumed gaps plus CTR-ALERT | M07-LIVE-004..007 | Owner-coordinated natural/safe real conditions |
| AC-UI-002/005/006 | Real alerts and truthful empty/stale/unknown/recovered explanations appear with source/time/confidence | CTR-ALERT-002/005 | M07-BROWSER-002..008 | Built UI/real service/database/upstream state |
| AC-V1-001..008, AC-TEST-001..006 | Traceability/contracts/migrations/security/docs/no simulation/RGR/live-state truth are release-gated | Entire plan | M07-DOC-001..003, M07-TEST-001/002, M07-SEC-001..008 | Integration/release review |

## 3. Domain design

### 3.1 Core identifiers and value objects

- `AlertRuleId`, `AlertId`, `AlertEventId`, `OccurrenceGeneration`, and command/job IDs are opaque `CTR-COMMON-001` values.
- `AlertRuleTypeV1` is a closed V1 condition family with forward-unknown handling at transport boundaries.
- `AlertScopeV1` is exactly one of `global`, `organization(organization_id)`, `provider(provider_key)`, or `account(account_id)`.
- `AlertSubjectV1` identifies the condition owner: organization, provider, account, resource/window, monitoring profile, collection target/capability, or runtime session. It contains only safe scalar IDs.
- `SeverityV1` is `info`, `warning`, or `critical`; source modules do not choose M07 severity.
- `InputTruthStateV1` distinguishes `current`, `stale`, `unknown`, `unavailable`, and `unsupported`.
- `AlertConditionFactsV1` is a typed, bounded union of safe decision facts. It is not an arbitrary map and never contains raw upstream/provider data.
- Ratios use integer basis points in `0..10000`. Money is never interpreted by M07; forecast/source modules provide exact comparison facts.
- All instants are UTC. Wall time is explicit input to pure policies; monotonic time is used only for worker duration/deadline measurement.

### 3.2 Rule types and default condition policy

V1 defines these rule types:

| Rule type | Required synchronized input | Opens when | Default severity | Recovery proof |
|---|---|---|---|---|
| `capacity_remaining` | current CTR-CAP-001/002 window/resource facts with a real denominator and exact/rounded remaining bp | `remaining_bp <= warning_bp`; critical at `<= critical_bp` | warning/critical by threshold | newer current input above warning threshold or verified reset/current health |
| `capacity_exhausted` | M05 normalized Exhausted with constraining resource/window | explicitly exhausted | critical | newer non-exhausted current state/reset evidence |
| `capacity_unavailable` | explicit ordered M05 availability fact/reason, not normalized Unknown/Unsupported/Stale | source says a known capacity resource is runtime-unavailable | critical | newer explicit availability recovery generation |
| `forecasted_exhaustion` | M05 forecast with inputs, uncertainty, generated time, projected exhaustion and recovery boundary | forecast predicts exhaustion before reset/renewal boundary | warning | newer forecast no longer predicts before boundary, reset, or current capacity recovery |
| `authentication_attention` | CTR-REG-010 authentication-health change | expiring = warning; `reauthentication_required`/revoked/wrong-account = critical | warning/critical | newer verified `healthy`; `refreshing` remains active but non-escalating |
| `data_stale` | upstream-owned explicit stale transition/deadline | state becomes stale | warning | newer source marks current; Unknown does not recover |
| `collector_failure` | M04 failure/health change after retry/backoff classification | health says failed/degraded/blocked/unavailable for a real target | warning; critical for explicit blocked/unavailable infrastructure state | newer healthy/completed health generation |
| `possible_stall` | M06 stall state change with inference/evidence and waiting exclusions | M06 says possible stall active | warning, visibly inferred | newer cleared/progress/terminal evidence |

`recovery/reset` is a lifecycle transition of the same alert, not a separate rule/fingerprint. It creates an `info` dashboard notification while preserving the original condition severity in history.

The `capacity_remaining` built-in global fallback is normative product configuration:

```text
warning_remaining_basis_points = 3000
critical_remaining_basis_points = 1500
```

Validation requires `0 <= critical <= warning <= 10000`. Exact equality activates the corresponding severity. Above warning does not open the condition. A provider value with no real denominator/remaining percentage cannot enter this evaluator.

No exact time-horizon default is invented for forecast alerts. The condition is based on the M05-computed relationship `projected_exhaustion_at < recovery_boundary_at` with sufficient input state. If M05 cannot provide a recovery boundary or acceptable uncertainty classification, the forecast condition is `not_evaluable`, not false. CS-M07-004 must freeze this contract before approval.

M07 alert thresholds are intentionally separate from M05 normalized-health policy. M05 owns the meaning and calculation of `CapacityHealthViewV1`; M07 owns alert rule precedence/severity. M07 consumes CTR-CAP-008/009 plus exact current CTR-CAP-001/002/003/007 views and never pushes settings or alert state back into M05. This is a one-way M05 -> M07 dependency; M05 does not consume M07 policy.

### 3.3 Rule scope and precedence

For one rule type and evaluated subject, M07 resolves the first existing rule in this exact order:

```text
account -> provider -> organization -> global -> built-in product fallback
```

Rules are whole typed documents. Fields do not merge across levels. An explicitly disabled closest rule suppresses the condition and does not fall through. Provider outranks organization exactly as required, even though both can apply to an account. A subject with no proven account has no account/organization candidate; M07 never guesses one. A provider-only subject may resolve provider then global. Built-in fallback exists only for documented product defaults; an absent non-default rule type uses its documented built-in enabled/severity policy after CS approval.

Every evaluation stores the selected rule ID/version or built-in policy version, candidate scope IDs, registry revision, and reason code. Mutable friendly names are resolved for display by API composition and never enter rule identity or fingerprints.

Account move, provider reassociation, archive, monitoring disablement, or rule revision produces a bounded re-evaluation job. A policy change that makes an active condition no longer eligible yields `closed_by_configuration`, not `recovered`, because no source recovery was observed. A new source event can later reopen it under the then-current rule.

### 3.4 Rule configuration model

`AlertRuleConfigurationV1` is a closed discriminated union:

- `CapacityRemainingRuleV1`: warning/critical remaining basis points.
- `EnabledConditionRuleV1`: enabled flag for fixed-severity conditions.
- `DataStaleRuleV1`: enabled flag only; M07 consumes the upstream freshness decision and does not redefine its duration.
- `CollectorFailureRuleV1`: enabled flag and accepted synchronized health categories; it cannot reinterpret Retry-After or schedule timing.
- `PossibleStallRuleV1`: enabled flag only; the ten-minute default and waiting exclusions remain M06-owned.

Rule mutation uses optimistic version and an idempotency key. Removing a non-global override archives it and re-enables lower precedence after re-evaluation. The built-in fallback cannot be deleted. Configuration changes never rewrite history.

### 3.5 Signal contract and evaluation

M07 receives a typed `AlertSignalV1` through internal event consumers. Each signal contains:

- upstream immutable `event_id`, event type/major, producer/version, correlation/causation IDs;
- condition stream key and monotonically comparable generation/sequence owned by the producer;
- subject IDs and safe scope candidates, with registry revision where available;
- condition type and typed facts;
- `occurred_at`, `recorded_at`, source observation/event references, provenance/freshness/confidence references;
- truth state and transition (`active`, `recovered`, `not_evaluable`, or `configuration_invalid`);
- safe explanation/reason codes.

Composition adapters map synchronized CAP/RUN/COL/REG auth events to this internal application input. The mapper is schema-specific and contains no provider branch. A missing required field, unknown incompatible major, unsafe free text, or impossible state returns a typed rejection and does not mutate an existing alert.

`not_evaluable`, Unknown, Unsupported, and Stale never imply recovery. An explicit stale signal may open `data_stale`, while the stale capacity value itself cannot open, de-escalate, or recover a capacity threshold condition.

### 3.6 Fingerprint and deduplication

Fingerprint material is canonical, versioned, and consists of:

- fingerprint schema major;
- rule/condition type;
- primary subject kind and opaque subject ID;
- condition dimension: resource/window ID, forecast family, monitoring profile, collection target/capability, or runtime session ID as applicable;
- source semantic schema major where a meaning change requires separation.

Fingerprint material does **not** include severity, current threshold values, rule ID/version, organization membership, mutable labels, occurrence generation, timestamps, evidence IDs, or provider display text. Therefore escalation, acknowledgement, snooze, group moves, and compatible rule revisions remain one lifecycle.

The digest uses an approved canonical serialization plus a standard cryptographic hash; no new dependency is proposed. The database stores the digest and collision-check material. Same digest with different canonical material is a hard conflict/incident, never merged. Each upstream event ID is consumed at most once. Repeated equivalent active signals increment occurrence count only when their unique event is newer; byte-for-byte redelivery does nothing.

### 3.7 Lifecycle model

Lifecycle and user interaction are orthogonal rather than encoded in one combinatorial enum.

```text
no alert --active signal--> open
open --same condition--> repeated
open --higher severity--> escalated
open --lower severity/current but still active--> deescalated
open --explicit recovery/reset--> recovered
recovered --active signal--> reopened (occurrence generation +1)
open --rule/scope disables evaluation--> closed_by_configuration
closed_by_configuration --active eligible signal--> reopened
```

Invariants:

- `open` means the source condition remains active; acknowledgement/read/snooze never changes that truth.
- `recovered` requires newer explicit inverse evidence for the same condition stream.
- A stale, unknown, unsupported, unavailable dependency, older generation, or missing event cannot recover an alert.
- `repeated` retains severity, lifecycle, acknowledgement, and snooze and increments count/last-seen once.
- `escalated` clears current acknowledgement, ends snooze, sets unread, and increments notification revision.
- `deescalated` keeps the alert open and appends history; whether it sets unread is proposed `true` for visibility and must be synchronized with P02.
- `recovered` clears snooze, ends the active occurrence, sets a recovery timestamp and unread recovery notification, and retains acknowledgement history.
- `reopened` increments occurrence generation, resets occurrence count to one, clears current acknowledgement/snooze, and sets unread.
- `closed_by_configuration` clears active notification/snooze but remains in history; it does not pretend the source recovered.
- Events are immutable. Current alert projection is rebuilt/verifiable from events plus rule/source references.

### 3.8 Unread, acknowledgement, and snooze

- `is_unread` is dashboard presentation state owned by M07 and persisted server-side.
- `MarkAlertReadV1` changes only unread state and is idempotent.
- `AcknowledgeAlertV1` is allowed for an open alert, records principal/time/comment-free reason code, and also marks the current notification read. It does not suppress evaluation or claim resolution.
- No free-form acknowledgement note exists in V1, avoiding accidental content/secret capture.
- `SnoozeAlertV1` is allowed only for an open alert and stores a UTC expiry. Proposed bounds are 60 seconds through 30 days; final bounds are CS-M07-009 decisions.
- A same-severity repeat remains snoozed. Critical escalation ends snooze immediately. Recovery ends snooze and produces an unread recovery item.
- Snooze expiry is processed by an idempotent M07 deadline worker. If still open, it becomes visible and unread; if already terminal, expiry is a no-op receipt.
- Manual `UnsnoozeAlertV1` makes an open alert visible and unread.
- Read/ack/snooze commands require `write:alerts`; queries require the synchronized read permission. Browser mutations require P01 CSRF; bearer calls require scope authorization.

### 3.9 Dashboard notification projection

Dashboard notifications are projections of alert state/events, not a second source of truth and not browser-local storage.

Current ordering is deterministic:

1. unsnoozed open critical;
2. unsnoozed open warning;
3. unread recovered information;
4. remaining current items;
5. tie-break by latest notification time descending, then opaque alert ID descending.

Queries expose active, acknowledged, snoozed, recovered, closed-by-configuration, unread, severity, condition, scope, and bounded time filters. `visible_unread_count` excludes active snoozed items; `total_unread_count` includes them and is labeled. History is cursor-paginated and never unbounded.

No UI polling frequency becomes alert truth. REST queries rebuild the current projection after browser close/reopen. SSE, if later approved within P01 V1 scope, carries only event hints and forces REST reconciliation.

### 3.10 Ordering, concurrency, and re-evaluation

- Event processing is serialized per fingerprint/condition stream through a short database transaction and optimistic alert version.
- Cross-fingerprint evaluation may run concurrently.
- Duplicate `event_id` returns the existing processing result.
- A lower/equal producer generation that is not the same event is recorded as stale/ignored receipt and cannot regress state.
- Concurrent owner commands use expected alert version; stale commands return conflict rather than silently overwrite.
- Rule changes atomically write rule revision/outbox/job metadata, then bounded workers query public upstream current-state ports and reevaluate affected subjects.
- Registry changes deduplicate by event ID/revision and enqueue only affected scopes.
- A failed dependency query keeps the job pending/degraded with bounded backoff; it never closes an alert or uses cached-as-current input.
- Restart recovers expired job/deadline leases through fencing. M07 never invents an alert while replay position is uncertain.

## 4. Public contracts

All contracts are Proposed until producer/consumer synchronization and owner approval. DTOs are immutable typed values, never ORM entities or arbitrary dictionaries.

### 4.1 Published contract summary

| Register ID | Proposed name/version | Producer | Consumers | Compatibility promise |
|---|---|---|---|---|
| CTR-ALERT-001 | `AlertRuleViewV1` and rule command/query family | M07 | P01/P02/M08 | Scope, precedence, units, rule-type/config meaning and version semantics stable within V1 |
| CTR-ALERT-002 | `AlertViewV1` and alert/history query family | M07 | P01/P02/M08/export | State/severity/unread/ack/snooze/recovery/evidence meanings stable; fields additive only when safe |
| CTR-ALERT-003 | `AlertOpenedV1` | M07 | M08/P01 event projection/future post-V1 delivery | Immutable at-least-once event; no delivery side effect |
| CTR-ALERT-004 | `AlertStateChangedV1` | M07 | M08/P01/P02 hint/future post-V1 delivery | Transition/actor/evidence/idempotency semantics stable |
| CTR-ALERT-005 | `DashboardNotificationQueryV1` family | M07 | P01/P02 | REST-authoritative filters/order/count/read behavior stable |

### 4.2 CTR-ALERT-001 — rules and resolution

`AlertRuleViewV1` fields:

- rule ID, rule type, scope level and nullable scope ID;
- enabled state and typed `AlertRuleConfigurationV1` with schema major;
- optimistic version, created/updated UTC instants, actor safe ID;
- archived timestamp when an override is removed;
- whether it is built-in or persisted;
- compatibility/policy version; no secret or free-form content.

Published ports:

| Port | Input/output | Authorization/preconditions | Errors | Idempotency/side effects |
|---|---|---|---|---|
| `CreateAlertRuleV1` | typed rule/scope/config, command ID -> view | `write:alerts`; valid existing scope; no duplicate active rule | invalid config/scope, duplicate, dependency unavailable | command ID + canonical request; persists revision/event/job |
| `UpdateAlertRuleV1` | rule ID, expected version, typed config/enabled, command ID -> view | `write:alerts`; active persisted rule | not found, stale version, invalid config | replay-safe; revision/event/job |
| `ArchiveAlertRuleOverrideV1` | rule ID/version/command -> effective fallback summary | `write:alerts`; built-in cannot archive | protected built-in, not found, stale | replay-safe; archive/re-evaluate |
| `GetAlertRuleV1` | rule ID -> view | authorized read | not found/forbidden | read-only |
| `ListAlertRulesV1` | bounded scope/type/status cursor -> page | authorized read | invalid filter/cursor | read-only |
| `ResolveEffectiveAlertRuleV1` | rule type + subject scope snapshot -> resolution | internal/P01 explanation read | scope unresolved/dependency unavailable | deterministic, read-only |

Resolution result includes ordered candidates, selected scope/rule/version or built-in version, and safe explanation. It never returns another module's private labels.

### 4.3 CTR-ALERT-002 — alerts and history

`AlertViewV1` fields:

- alert ID; fingerprint schema version and safe digest (digest disclosure to UI remains a P01 review item);
- condition type, primary subject/dimension safe IDs, resolved organization/provider/account scope IDs;
- severity, lifecycle, occurrence generation/count, optimistic version;
- open/last-seen/recovered/closed/latest-notification UTC instants;
- unread, acknowledged principal/time, snoozed-until and snooze state;
- selected rule ID/version/scope or built-in policy version;
- bounded typed condition facts sufficient to explain the decision;
- input truth/freshness/confidence/precision/value-kind states and safe explanation codes;
- upstream source event/observation/provenance references, never raw values/payloads;
- links expressed as safe resource identifiers for P01 to map.

Published ports:

- `GetAlertV1(alert_id)`;
- `ListAlertsV1(filters, cursor, page_size)`;
- `ListAlertHistoryV1(alert_id, cursor, page_size)`;
- `ListAlertsForSubjectV1(subject, filters, cursor)`;
- `AcknowledgeAlertV1(alert_id, expected_version, command_id)`;
- `SnoozeAlertV1(alert_id, expected_version, until_utc, command_id)`;
- `UnsnoozeAlertV1(alert_id, expected_version, command_id)`;
- internal `ConsumeAlertSignalV1(signal)`;
- internal `ReevaluateAlertScopeV1(scope, source_revision, command_id)`;
- internal `PurgeExpiredAlertHistoryV1(cutoff_utc, batch_limit, command_id)`;
- `GetAlertingHealthV1()` implementing the synchronized M08 component-health shape.

Mutation outcomes distinguish not found, forbidden, not active, already in requested state, invalid snooze, stale version, idempotency conflict, dependency unavailable, and repository unavailable. P01 owns HTTP/problem mapping.

### 4.4 CTR-ALERT-003 — AlertOpenedV1

`AlertOpenedV1` uses `EventEnvelopeV1` and contains only:

- alert ID, occurrence generation, fingerprint version/digest;
- condition type, safe subject/dimension IDs and resolved scope IDs;
- severity, opened/last-seen time, rule/policy reference;
- input truth state, safe explanation/evidence reference IDs;
- notification revision and `is_unread=true`;
- alert aggregate sequence.

The event is emitted after the alert/event/outbox transaction commits atomically. Delivery is at least once, ordered only by alert aggregate sequence, and deduplicated by event ID. It does not send a notification outside AgentMonitor. Future external delivery requires a new approved module/plan, security/privacy/data-flow review, and V1 scope change.

### 4.5 CTR-ALERT-004 — AlertStateChangedV1

Fields:

- alert/event IDs, occurrence generation, aggregate sequence;
- transition: `repeated`, `escalated`, `deescalated`, `marked_read`, `acknowledged`, `snoozed`, `unsnoozed`, `snooze_expired`, `recovered`, `reopened`, or `closed_by_configuration`;
- previous/current lifecycle and severity;
- occurrence count, unread state, nullable acknowledgement/snooze/recovery fields;
- actor kind `system` or `administrator` and safe principal ID when authorized;
- cause source event ID or command ID, effective rule/policy version;
- safe reason/evidence refs and occurred/recorded UTC times.

Same-severity polling repetition may append an internal `repeated` history event according to bounded coalescing policy, but dashboard notification revision does not change. Exact coalescing must be synchronized so history remains truthful without unbounded noise. Events never contain labels, emails, profile paths, provider errors, notes, or raw metric values.

### 4.6 CTR-ALERT-005 — dashboard notification queries/actions

`DashboardNotificationViewV1` is a bounded projection of `AlertViewV1` with alert ID, condition, severity/lifecycle, unread/ack/snooze flags, safe subject/scope IDs, safe explanation, first/latest time, count, and source link references.

Published ports:

- `ListDashboardNotificationsV1(filters, cursor, page_size)` using section 3.9 ordering;
- `GetDashboardNotificationCountsV1(scope_filters)` returning active critical/warning, visible unread, total unread, acknowledged, snoozed, and recent recovered counts;
- `MarkAlertReadV1(alert_id, expected_notification_revision, command_id)`;
- `MarkAlertUnreadV1(alert_id, expected_notification_revision, command_id)` if P02 confirms a real workflow;
- `MarkVisibleNotificationsReadV1(explicit_alert_ids, command_id)` with a bounded explicit list, never an unbounded implicit update.

These ports do not expose browser delivery acknowledgement or claim the user saw a tab. UI rendering never mutates read state automatically merely because a list was fetched.

### 4.7 Consumed contracts and failure behavior

| Owner/contract | Required state | M07 use | Failure/degradation |
|---|---|---|---|
| CTR-COMMON-001/002/003/004/006/007 | Draft-aligned V1 | IDs, UTC/duration, basis-point/exact facts, provenance refs, event envelope, field states | incompatible/invalid inputs rejected; existing alerts unchanged; absence never becomes zero |
| CTR-EVT-001 | Draft-aligned V1 | atomic consumer receipt/checkpoint with alert transition/outbox, replay and retention | incompatible/poison/backlog stays explicit; no in-memory-only delivery |
| CTR-CONFIG-001 / CTR-FND-003/004/006/008 | `proposed_aligned` 1.0.0 | config registry, safe logging/correlation, migration metadata, evidence summaries | invalid config/schema blocks M07 readiness or affected worker |
| CTR-DB-002 | `proposed_aligned` 1.0.0 | M07 repositories/UoW | typed unavailable/conflict/corrupt; no partial transition |
| CTR-IAM-001/002 | `proposed_aligned` 1.0.0 | read/write alert authorization and safe actor | mutation fails closed if unavailable |
| CTR-REG-007 `RegistryChangedV1` | `proposed_aligned` 1.0.0 | enqueue scope/policy reevaluation after moves/archive/restore | dedupe event; failed dependency leaves job pending |
| CTR-REG-009 `AlertScopeAndSubjectQueryV1` | Draft-aligned V1 | bounded account > provider > organization scope, lifecycle, eligible resources, revision | incomplete/unavailable scope delays evaluation; no precedence-changing fallback |
| CTR-REG-010 `AuthenticationHealthChangedV1` | Draft-aligned V1 | normalized provider-auth active/recovery generations and identity comparison | raw provider outcome never reaches M07; stale/silence/generic success cannot recover |
| CTR-COL-003 `CollectionCompletedV1` | `proposed_aligned` 1.0.0 | source recovery reference where health generation proves recovery | completion alone cannot recover stale/failure without synchronized health meaning |
| CTR-COL-004 `CollectionFailedV1` | `proposed_aligned` 1.0.0 | safe collector failure/auth block evidence | unsupported/cancelled/rate-backoff are not silently treated as failure |
| CTR-COL-005 `CollectorHealthV1` | `proposed_aligned` 1.0.0 | re-evaluation/current explanation | query failure preserves alert and marks job degraded |
| CTR-COL-007 `CollectorHealthChangedAndCurrentAlertInputsV1` | Draft-aligned V1 | ordered current collector health plus explicit active/recovery generations | completion alone, silence, or stale generation cannot recover |
| CTR-CAP-001 `QuotaWindowViewV1` | `evidence_blocked` 1.0.0 | exact current remaining ratio/field state, native window/reset, provenance and freshness after an M05 event or rule reevaluation | absent denominator/ratio or stale/unknown field is not evaluable; no universal total |
| CTR-CAP-002 `BudgetViewV1` | `evidence_blocked` 1.0.0 | exact budget/credit/limit availability and renewal boundary where the provider supports them | unsupported/unknown amount is not zero or unavailable; M07 performs no money derivation |
| CTR-CAP-003 `CapacityHealthViewV1` | `evidence_blocked` 1.0.0 | current normalized health, constraining native window, truth/freshness | unknown/stale cannot open/recover threshold condition |
| CTR-CAP-004 `CapacityObservationRecordedV1` | `evidence_blocked` 1.0.0 | observation/evidence reference only where evaluation facts are published | M07 never reads observation rows/raw extension |
| CTR-CAP-005 `CapacityHealthChangedV1` | `evidence_blocked` 1.0.0 | open/escalate/deescalate/recover exhausted/remaining/unavailable conditions | insufficient facts become not evaluable |
| CTR-CAP-007 `CapacityForecastV1` | `evidence_blocked` 1.0.0 | forecast explanation and rule reevaluation | insufficient/unknown uncertainty does not predict exhaustion |
| CTR-CAP-008 `CapacityForecastChangedV1` | Draft-aligned V1 | ordered forecast activation/invalidation/recovery | missing/stale forecast generation leaves prior alert truth unchanged |
| CTR-CAP-009 `CapacityAvailabilityChangedV1` | Draft-aligned V1 | supported/available/auth/unavailable transitions and explicit recovery | Unknown is not unavailable or recovery; completion/silence cannot clear |
| CTR-RUN-004 `RuntimeStateChangedV1` | `evidence_blocked` 1.0.0 | recovery/progress/terminal signal and session scope | inferred/unknown state cannot be upgraded by M07 |
| CTR-RUN-005 `PossibleStallDetectedV1` | `evidence_blocked` 1.0.0 | open possible-stall with evidence/wait exclusion | duplicate/stale event deduped; no process action |
| CTR-OPS-006 component health | `proposed_aligned` 1.0.0 | publish safe M07 health to M08 | M08 failure cannot stop M07 queries/evaluation |
| CTR-OPS-007 participant family | Draft-aligned V1 | M07 retention/export/post-restore consistency implementation | bounded typed failure; no M08 table access |

### 4.8 Draft-aligned recovery contracts

The former consumed-contract gaps are allocated in baseline `0.2.0`: M02 owns CTR-REG-009/010, M04 owns CTR-COL-007, M05 owns CTR-CAP-008/009, M06 owns CTR-RUN-004/005, and PLAN-INT/PLAN-DB govern CTR-EVT-001. They remain Draft and evidence-blocked, but M07 does not invent aliases or workaround contracts.

For every alert stream, a duplicate or older source generation is idempotent and cannot regress state. Recovery requires the same condition fingerprint plus a newer producer generation carrying the producer's explicit recovered/current/healthy/non-triggering truth. Silence, missing data, Unknown, dashboard authentication, a collection completion alone, and a stale replay preserve the last alert state and surface degraded evaluation when applicable. Receipt/checkpoint, alert transition/history, and M07 producer outbox commit atomically; restart replays from the durable checkpoint and re-queries the appropriate current-state port before readiness.

M07 directly invoking `AuthenticationHealthPortV1`, a provider adapter, or M03's invocation gateway is rejected. M02 reconciles provider outcomes and publishes CTR-REG-010; M07 consumes only that sanitized domain event/query surface.

### 4.9 Error vocabulary

Stable safe M07 application error codes:

- rule: `alert_rule_not_found`, `alert_rule_duplicate`, `alert_rule_invalid_scope`, `alert_rule_scope_unavailable`, `alert_rule_invalid_configuration`, `alert_rule_builtin_protected`, `alert_rule_stale_version`;
- alert: `alert_not_found`, `alert_not_active`, `alert_already_recovered`, `alert_stale_version`, `alert_invalid_snooze`, `alert_notification_revision_conflict`;
- signal: `alert_signal_contract_incompatible`, `alert_signal_invalid`, `alert_signal_unsafe_field`, `alert_signal_duplicate`, `alert_signal_stale`, `alert_signal_scope_unresolved`, `alert_signal_not_evaluable`, `alert_fingerprint_conflict`;
- command/event: `alert_idempotency_conflict`, `alert_event_sequence_conflict`, `alert_replay_checkpoint_incompatible`;
- dependency/infrastructure: `alert_dependency_unavailable`, `alert_repository_unavailable`, `alert_schema_incompatible`, `alert_internal_error`.

Errors expose safe code, correlation ID, and authorized opaque subject ID only. They never echo labels, free-form input, SQL, provider errors, event payloads, paths, exception arguments, or credentials. P01 maps them to RFC 9457 problems.

### 4.10 Contract-impact assessment

This plan proposes the first `alerting.v1` contracts and changes no implemented behavior. Approval requires:

1. producer/consumer review of every field in sections 4.2–4.8;
2. synchronization of complete open **and recovery** event shapes;
3. explicit common event receipt/outbox/replay ownership;
4. P01 permission, route, ETag/idempotency, pagination, and problem mapping;
5. P02 notification ordering, unread/ack/snooze/recovery workflow review;
6. M08 retention/export/health/backup review;
7. centrally allocated migrations and shared contract paths;
8. an ADR if durable event semantics, generic outbox ownership, or compatibility rules differ from existing architecture.

## 5. Data and persistence

### 5.1 Owned tables

All names are proposals pending DB allocation. Cross-module IDs are scalar values validated through contracts; there are no cross-module foreign keys.

#### `alert_rule`

- rule ID primary key;
- rule type, scope level, nullable scope scalar ID;
- enabled, typed-configuration schema major and canonical validated representation;
- optimistic version, policy version, created/updated/archived UTC instants;
- safe actor principal ID and latest revision ID.

Active uniqueness is `(rule_type, scope_level, scope_id)` with a dedicated global-scope uniqueness rule. The typed configuration representation has a strict codec, exact allowlist, length bound, canonical serialization, and no raw provider fields. M07 never dynamically queries arbitrary JSON keys.

#### `alert_rule_revision`

Immutable rule revision ID, rule ID/version, prior/new canonical typed configuration, enabled/scope state, change kind, safe actor/command/correlation IDs, and recorded UTC time. Retained while referenced by retained alert history and for at least 365 days.

#### `alert_alert`

- alert ID primary key;
- fingerprint version, digest, and bounded collision-check material;
- condition type; primary subject/dimension kind and scalar IDs;
- resolved organization/provider/account scalar IDs plus registry revision;
- selected rule/policy reference and version;
- lifecycle, severity, input truth state, occurrence generation/count;
- opened, last-seen, recovered, closed, latest-notification timestamps;
- unread and notification revision;
- current acknowledgement principal/time/generation;
- snoozed-until and deadline generation;
- upstream producer/stream/latest sequence/event refs;
- typed bounded latest condition facts/evidence refs;
- aggregate sequence and optimistic row version.

Unique fingerprint digest plus collision material prevents duplicate current rows. No label, email, path, free-form note, raw provider response, or source content is stored.

#### `alert_evidence_reference`

Alert/occurrence/event IDs, upstream producer/contract major/event/observation/provenance scalar refs, safe evidence/reason code, occurred/recorded times, and source generation. It does not copy metric/provider payloads.

#### `alert_event`

Immutable M07 event ID, alert ID, occurrence generation, aggregate sequence, transition, previous/current lifecycle/severity/unread/ack/snooze summary, system/admin actor safe ID, cause source event or command ID, rule/policy reference, safe reason/evidence refs, occurred/recorded times. Unique `(alert_id, aggregate_sequence)`.

#### `alert_event_receipt`

Producer, event ID/type/major, condition stream key, producer generation/sequence, payload fingerprint, processed time, disposition (`applied`, `duplicate`, `stale`, `not_evaluable`, `rejected`), alert/event/result IDs, safe reason code. It never stores the source payload.

#### `alert_command_receipt`

Command ID/idempotency key digest, principal safe ID, command kind, target ID, canonical request fingerprint, result alert/rule/event ID, created/expiry times. Same ID/different request conflicts.

#### `alert_deadline`

Deadline ID, alert ID, kind `snooze_expiry`, deadline generation, due time, lease/fence owner/expiry, state, attempt/result code, created/completed times. It contains no arbitrary scheduled action.

#### `alert_reevaluation_job`

Job ID, trigger event/rule/registry revision, scope/rule filters, source-module checkpoint cursors, state, lease/fence, attempts, bounded safe error code, created/started/completed times. Each source query remains through its public port.

#### `alert_event_outbox`

CTR-EVT-TOPOLOGY-001 fixes `alert_event_outbox` as an M07-owned table: outbox ID, M07 event ID/type/major, aggregate stream/sequence, canonical typed payload reference or bounded payload, state, attempts, next due, created/published time. Alert transition, consumed-event receipt/checkpoint, and resulting M07 outbox append commit atomically. PLAN-DB provides reusable mechanics through published ports; ownership cannot move to common infrastructure.

### 5.2 Indexes and query plans

Required indexes, verified with real query plans and measured data:

- active unique rule by type/scope;
- rules by scope/status/type;
- alerts unique fingerprint;
- alerts by `(lifecycle, severity, latest_notification_at desc, alert_id desc)`;
- alerts by `(is_unread, lifecycle, snoozed_until, severity)`;
- alerts by organization/provider/account/subject plus latest time;
- alert events by `(alert_id, aggregate_sequence)` and `(recorded_at, event_id)`;
- evidence by upstream event/observation and alert occurrence;
- event receipts unique producer/event ID and by stream/generation;
- command receipts unique principal/command ID and expiry;
- due deadlines and pending re-evaluation jobs by state/due/lease;
- outbox by state/next due/sequence.

Every list query is cursor-paginated with a maximum page size approved by P01. History/time filters are bounded. No UI/API query scans event history without an index.

### 5.3 Constraints and transaction boundaries

Database/domain constraints enforce valid scope/null combinations, threshold bounds/order, enum storage, nonnegative occurrence/sequence, recovery time ordering, snooze/lifecycle compatibility, event uniqueness, and receipt uniqueness.

Transactions:

1. **Rule mutation:** command receipt check, rule/revision write, re-evaluation job, M07 event/outbox, and receipt commit atomically.
2. **Signal consumption:** receipt reservation, scope/rule resolution reference validation, alert lock/version check, projection transition, evidence/history, outbox, and receipt result commit atomically.
3. **Owner command:** idempotency/version check, alert projection/history/outbox/receipt atomically.
4. **Deadline:** fenced due-row claim followed by idempotent transition/history/outbox/result.
5. **Retention:** explicit cutoff/batch deletes only eligible terminal unreferenced records and writes an auditable safe result.

External query-port calls occur before the short write transaction using a revisioned snapshot. If required revisions change before commit, the transaction conflicts and reevaluation retries; it never holds a SQLite write lock during another module call.

### 5.4 Migrations

Proposed centrally allocated sequence:

1. M07 schema metadata, rule/current/revision tables and constraints.
2. Alert/evidence/event/receipt/command tables and indexes.
3. Deadline/re-evaluation/outbox integration after common durability ownership is synchronized.

Migrations use Alembic, apply to a real file SQLite database from empty and supported prior revisions, and include owner, requirements, lock/data-volume expectations, backup prerequisite, validation query, and recovery strategy. Startup never creates tables implicitly.

No product telemetry or demo alert is inserted. The 30%/15% fallback is a versioned domain default visible through CTR-ALERT-001 until the user persists an override; it is not seeded telemetry.

### 5.5 Retention, deletion, backup, and restore

- Active alerts and their evidence needed for explanation are never purged by age.
- Terminal alerts become eligible 365 days after their latest terminal transition; keeping them longer while referenced is safe.
- Alert events/evidence/rule revisions/receipts required by an active or retained alert remain retained.
- Expiry is a pure cutoff policy; deletion is a real, batched, auditable SQLite transaction orchestrated by M08.
- Purge never deletes active rules, open alerts, pending outbox, pending jobs/deadlines, or evidence required by a retained alert.
- Backup/restore is owned by M08/DB. M07 supplies post-restore invariants: fingerprint uniqueness, event sequence continuity, no orphan current references, deadlines/jobs safely reclaimed, and outbox replay idempotency.
- Restore does not contact a provider, close/recover alerts, or resend any external notification. V1 has no external delivery.

### 5.6 PostgreSQL portability

Domain contracts use no SQLite row IDs, JSON query semantics, implicit booleans, local timezone, or SQLite-specific conflict meaning. Persistence isolates partial-index/check/locking implementation. Lease fencing, optimistic versions, exact ratio values, cursors, and uniqueness have explicit repository semantics suitable for PostgreSQL mapping later.

## 6. External and platform boundaries

M07 has no direct provider, OS, process, filesystem, email, messenger, desktop, or internet boundary.

Its external boundaries are:

- versioned internal events/queries from M02–M06;
- real SQLite through the persistence adapter;
- M01 authorization through contracts;
- P01 real HTTP transport and P02 real built browser;
- M08 health/retention/export/backup orchestration.

All producer events are untrusted structured input. Schema major, bounds, enum, required fields, sequence, subject IDs, timestamps, and prohibited-field absence are validated before domain evaluation. An invalid event affects only its stream, reports sanitized degraded health, and cannot crash unrelated query/evaluation paths.

No outbound network client, OS notification call, SMTP library, messenger SDK, webhook URL, provider SDK, subprocess, or platform branch belongs in M07 V1. A future delivery adapter consumes approved alert events only after a separate requirement, plan, threat/data review, dependency review, retry/idempotency/privacy design, and owner approval.

## 7. Security and privacy

### 7.1 Authorization and trust boundaries

- All rule/read/ack/read-state/snooze ports receive an M01 principal/authorization decision.
- Single-user deployment does not bypass permission checks.
- Proposed permissions are synchronized existing `write:alerts` plus an approved read permission; M07 does not create IAM policy privately.
- P01 owns cookie, CSRF, bearer, Host/Origin, request-size, and abuse controls.
- Internal event producers are allowlisted by contract/version; caller-supplied HTTP cannot invoke `ConsumeAlertSignalV1`.
- M08 export/diagnostic access uses its own authorization and M07 bounded query ports.

### 7.2 Data minimization

Allowed M07 data is limited to opaque IDs, condition/state/severity, exact safe threshold/evaluation facts, UTC times, versions, counts, source references, freshness/precision/confidence categories, and safe reason codes.

Prohibited everywhere: provider credential/profile locator, password, API/OAuth/session token, OTP/MFA/recovery code, email/display identity, raw provider/CLI/HTTP response, stdout/stderr, prompt, response, tool argument, source code, arbitrary path/environment/terminal content, arbitrary free-form note, and screenshot data.

M07 stores upstream references instead of copying raw observations. Logs never serialize DTOs/events. API schemas have no generic extensions. Database, logs, diagnostics, exports, backups, test artifacts, and browser console/source maps are independently scanned.

### 7.3 Abuse and integrity controls

- Rule names are enumerated; no expression language, user script, regex engine, template, or dynamic code exists.
- Scope IDs and cursor/page/command sizes are bounded.
- Snooze duration and batch mark-read list are bounded.
- Repeated rule updates, commands, and events are idempotent and rate-limited at P01 where applicable.
- A malicious/compromised producer cannot choose M07 severity directly or recover another fingerprint.
- Digest collision, conflicting sequence, incompatible major, and impossible transition fail closed and raise a safe local incident signal.
- Acknowledgement has no note field, preventing sensitive text leakage.
- No product analytics or crash reporting is added.

### 7.4 Audit and redaction

Rule/ack/snooze/read mutations create immutable M07 events with safe actor ID and correlation. Logs contain timestamp, module/event name, correlation, safe subject/alert ID, outcome code, duration, and bounded counts only. Exception details remain protected/redacted locally and never appear in HTTP/events/UI.

## 8. Configuration and operations

### 8.1 Persisted user configuration

Alert rules are persisted authorized runtime configuration. Their precedence and versions are exposed through CTR-ALERT-001. Environment variables cannot silently override them.

Normative built-in defaults:

| Setting | Value | Owner/source | Secret | Reload/migration |
|---|---:|---|---|---|
| capacity warning remaining | 3000 basis points (30%) | FR-ALERT-002 / M07 policy V1 | no | immediate via persisted override; policy versioned |
| capacity critical remaining | 1500 basis points (15%) | FR-ALERT-002 / M07 policy V1 | no | immediate via persisted override; policy versioned |
| alert history minimum | 365 days | FR-HIST-001 | no | weakening requires requirement change; purge via M08 |

Proposed technical M07 keys, unapproved until configuration synchronization:

| Proposed key | Type/default/range | Reload | Consequence |
|---|---|---|---|
| `AGENTMONITOR_ALERTING_DEADLINE_SCAN_INTERVAL_SECONDS` | integer, proposed 30, range 5..300 | restart | snooze-expiry worker cadence, not condition truth |
| `AGENTMONITOR_ALERTING_WORK_BATCH_COUNT` | integer, proposed 100, range 1..1000 | restart | deadline/reevaluation bounded batch |
| `AGENTMONITOR_ALERTING_LEASE_SECONDS` | integer, formula must exceed bounded job step | restart | crash/fencing recovery |

All are non-secret. Exact names/defaults/formulas require CTR-CONFIG-001 review. No SMTP, desktop, messenger, webhook, remote URL, or provider setting exists in M07 V1.

### 8.2 Health and readiness

M07 component health exposes safe states only:

- schema/repository compatibility;
- inbound consumer state and oldest unprocessed/retry age;
- invalid/incompatible event counts by code;
- pending/overdue re-evaluation and deadline counts;
- outbox backlog/oldest age;
- last successful event/job/deadline/retention time;
- fingerprint/sequence conflict state;
- module/policy/schema versions.

Repository/schema incompatibility or inability to atomically record transitions makes M07 unready for mutation. One upstream producer unavailable degrades that condition family but does not make alert history/API reads or unrelated families unavailable.

### 8.3 Structured operational measurements

Local bounded measurements include evaluation/transaction/query duration, input disposition counts, opens/transitions by condition/severity, dedupe/stale counts, pending jobs/deadlines/outbox, page sizes, retention counts, and rule-resolution scope counts. Cardinality uses safe enum/hashed IDs; values remain local and are not external analytics.

### 8.4 Operator procedures to document and verify

- inspect effective rule and precedence explanation for a subject;
- configure global/organization/provider/account override safely;
- distinguish open, unread, acknowledged, snoozed, recovered, reopened, and closed-by-configuration;
- diagnose duplicate/stale/incompatible upstream event without editing another module's data;
- diagnose stale collector/auth/stall alert through safe source links;
- recover expired job/deadline leases after restart;
- inspect M07 health/outbox/retention without dumping payloads;
- back up, restore, upgrade, and validate alert invariants;
- export sanitized alert history through M08;
- respond to suspected secret/content contamination.

Final commands remain TBD until repository automation is implemented and verified. Personal shell history is not an operational command.

### 8.5 Canonical automation obligations

Before an implementation handoff can be ready, repository automation must provide and document fail-closed selectors for:

- `AUTO-TEST` M07 T1/T2/T3/T4 and separate live T5/T6/T7 statuses;
- `AUTO-QUALITY` type/import/security/secret/dependency/contract checks for M07;
- `AUTO-DOCS-CHECK` identifiers, links, plan/module/API/runbook synchronization;
- `AUTO-MIGRATE` fresh/supported-upgrade/validation/recovery for allocated M07 revisions;
- `AUTO-BACKUP`/`AUTO-RESTORE` post-restore M07 invariants;
- `AUTO-BUILD` OpenAPI/client/UI alignment;
- `AUTO-GIT-PREFLIGHT` before commit/push, without mutating Git;
- `AUTO-DEPLOY` and `AUTO-RELEASE` only after their separately owned plans/gates.

The owning foundation/integration plans choose actual command syntax. M07 must not invent a command and call it executable evidence.

## 9. Test design before implementation

### 9.1 Integrity rules

- Every scenario begins `Not Run` and records meaningful Red, Green, and post-refactor evidence when implemented.
- Pure tests may construct typed domain rule/signal/state values and perform no I/O, clock patching, environment mutation, or collaborator substitution.
- SQLite tests use a real temporary file, production migrations/repositories/UoW, and no invented provider/account/session/telemetry rows.
- HTTP tests start the production FastAPI application through a real server with real migrations/database/auth/CSRF or bearer transport.
- Browser tests build/serve the production UI and use a real supported browser.
- Alert lifecycle I/O tests receive events produced by real production upstream modules from real observations/conditions. There is no test-only event injection endpoint, fake adapter, seeded alert, recorded event, or fabricated telemetry.
- Naturally unavailable exhaustion/auth/stale/recovery/stall states remain Blocked. Pure reducer coverage does not turn a live scenario Passed.
- Dynamic values are checked by identity, relationship, source, freshness, transition, and authoritative comparison rather than hardcoding live metric values.
- Evidence includes scenario ID, requirement/AC, exact command, boundary/environment, Red/Green/refactor result, sanitized refs, and every Blocked/Not Run item.

### 9.2 Pure domain scenarios (T1)

| Test ID | Requirement | Initial Red expectation | Pass condition |
|---|---|---|---|
| M07-PURE-001 | FR-ALERT-001 | Resolver has no global behavior | Global rule selected when no narrower rule exists |
| M07-PURE-002 | FR-ALERT-001 | Organization override ignored/wrongly merged | Organization replaces whole global rule |
| M07-PURE-003 | FR-ALERT-001 | Provider/organization order wrong | Provider wins over organization |
| M07-PURE-004 | FR-ALERT-001 | Account rule not most specific | Account wins over provider/organization/global |
| M07-PURE-005 | FR-ALERT-001 | Disabled closest rule falls through | Disabled closest rule suppresses without fallback |
| M07-PURE-006 | FR-ALERT-001 | Unresolved account guessed | Only proven scope candidates participate and explanation is explicit |
| M07-PURE-007 | FR-ALERT-002 | Default warning boundary absent | 3000 bp is warning |
| M07-PURE-008 | FR-ALERT-002 | Default critical boundary absent | 1500 bp is critical |
| M07-PURE-009 | FR-ALERT-002 | Above-warning input alerts | 3001 bp does not activate threshold |
| M07-PURE-010 | FR-ALERT-002 | Invalid threshold order accepted | `critical <= warning` and 0..10000 enforced |
| M07-PURE-011 | FR-ALERT-002 | Float/rounding ambiguity exists | Exact basis-point boundaries are deterministic |
| M07-PURE-012 | FR-ALERT-003 | Exhausted can be diluted by threshold | Explicit exhausted opens critical condition |
| M07-PURE-013 | FR-ALERT-003 | Unknown becomes unavailable/exhausted | Unknown/unsupported are not unavailable/exhausted |
| M07-PURE-014 | FR-ALERT-003 | Stale capacity changes threshold alert | Stale value cannot open/deescalate/recover capacity threshold; stale signal is separate |
| M07-PURE-015 | FR-ALERT-003 | Forecast without boundary/input alerts | Only sufficient forecast-before-boundary activates |
| M07-PURE-016 | FR-AUTH-001 | Unknown auth opens reauth | Healthy/refreshing/expiring/required/revoked/wrong/unknown map distinctly |
| M07-PURE-017 | FR-ALERT-003 | Auth recovery inferred | Only newer healthy state recovers auth alert |
| M07-PURE-018 | FR-ALERT-003 | Any collection terminal state alerts | Unsupported/cancelled/normal backoff excluded from collector failure |
| M07-PURE-019 | FR-ALERT-003 | Completion alone recovers collector | Explicit newer collector-health recovery required |
| M07-PURE-020 | FR-STATE-003/004 | Waiting session becomes stall | M06 waiting exclusion prevents active stall signal |
| M07-PURE-021 | FR-ALERT-003 | Older progress clears stall | Only newer clear/progress/terminal generation recovers |
| M07-PURE-022 | FR-ALERT-004 | Same condition changes fingerprint with severity | Severity/rule version/timestamp excluded from fingerprint |
| M07-PURE-023 | FR-ALERT-004 | Distinct window/session collides | Resource/window/session dimension separates fingerprints |
| M07-PURE-024 | NFR-COMP-001 | Canonical order changes digest | Canonical fingerprint is stable across field order/serialization |
| M07-PURE-025 | FR-ALERT-004 | Group move creates new alert | Organization membership is excluded from fingerprint |
| M07-PURE-026 | FR-ALERT-004 | Same digest/different material merges | Collision mismatch is hard conflict |
| M07-PURE-027 | FR-ALERT-004 | Redelivery increments count | Same event ID is no-op with same result |
| M07-PURE-028 | FR-ALERT-004 | New repeated event opens duplicate | Newer same-condition event increments one occurrence |
| M07-PURE-029 | FR-ALERT-004 | Out-of-order event regresses projection | Older generation is ignored visibly |
| M07-PURE-030 | FR-ALERT-004 | Escalation opens a second alert | Same alert escalates and notification revision advances |
| M07-PURE-031 | FR-ALERT-003/004 | Unknown/stale event recovers alert | Non-evaluable input preserves active truth |
| M07-PURE-032 | NFR-COMP-001 | Unknown incompatible event is accepted | Incompatible major rejects without mutation |
| M07-PURE-033 | NFR-RES-001 | Invalid one stream affects another | Reducer failure is isolated by fingerprint/stream |
| M07-PURE-034 | FR-ALERT-005 | Read changes condition state | Mark-read affects only notification state |
| M07-PURE-035 | FR-ALERT-005 | Ack resolves alert | Ack records owner action and leaves condition open |
| M07-PURE-036 | FR-ALERT-005 | Same repeat clears ack | Same-severity repeat retains ack/snooze |
| M07-PURE-037 | FR-ALERT-005 | Critical escalation remains snoozed/acked | Escalation clears current ack/snooze and sets unread |
| M07-PURE-038 | FR-ALERT-005 | Invalid/past/overlong snooze accepted | Bounds and lifecycle preconditions enforced |
| M07-PURE-039 | FR-ALERT-005 | Snooze expiry stays hidden/read | Active expiry becomes visible and unread once |
| M07-PURE-040 | FR-ALERT-005 | Recovery is silent | Recovery clears snooze and creates unread info transition |
| M07-PURE-041 | FR-ALERT-005 | Reopen preserves old occurrence controls | Reopen increments generation and resets ack/snooze/count |
| M07-PURE-042 | FR-ALERT-005 | Rule disable reports recovery | Rule disable yields closed-by-configuration |
| M07-PURE-043 | FR-ALERT-005 | Fetching notifications marks read | Query is side-effect free |
| M07-PURE-044 | FR-ALERT-005 | Ordering is unstable | Critical/warning/recovered/time/ID ordering is deterministic |
| M07-PURE-045 | FR-HIST-001/003 | Cutoff deletes active/recent rows | Only terminal history older than 365 days is eligible |
| M07-PURE-046 | FR-HIST-002 | Cursor ordering duplicates/omits ties | Deterministic cursor covers equal timestamps |
| M07-PURE-047 | FR-HIST-005 | Naive/local time accepted | UTC-aware instants required and ordering preserved |

### 9.3 Real SQLite/migration scenarios (T2)

These use AgentMonitor-owned rule configuration or naturally produced real upstream events. They do not insert invented provider/account/session/alert telemetry directly.

| Test ID | Requirement | Real dependencies | Initial Red expectation | Pass condition |
|---|---|---|---|---|
| M07-DB-001 | FR-ALERT-001 | real file SQLite/migrations/rule use case | No rule schema | Global rule persists and resolves |
| M07-DB-002 | FR-ALERT-001 | real DB/rule ports | Duplicate scope allowed | Active uniqueness enforced through production outcome |
| M07-DB-003 | FR-ALERT-001 | real DB/optimistic UoW | Concurrent edits overwrite | One succeeds, stale version conflicts |
| M07-DB-004 | FR-ALERT-001 | real DB/restart | Scope/revision lost | Precedence and revision survive restart |
| M07-DB-005 | FR-ALERT-002 | real DB/rule use case | Invalid threshold persists | Bounds/order rejected; valid override round-trips exactly |
| M07-DB-006 | FR-ALERT-004 | real upstream event path + DB | Duplicate event creates duplicate alert | One fingerprint/current alert/receipt/event sequence |
| M07-DB-007 | FR-ALERT-004 | real event redelivery + DB | Count increments twice | Same event ID returns prior disposition |
| M07-DB-008 | FR-ALERT-004 | real newer repeated source event | Repeat opens second row | One row, one append event, count increments once |
| M07-DB-009 | FR-ALERT-004 | real severity transition | Escalation non-atomic | projection/history/outbox agree after commit |
| M07-DB-010 | NFR-RES-001 | real DB/concurrent consumer processes/tasks | Two opens race | uniqueness/version retry yields one lifecycle |
| M07-DB-011 | NFR-RES-001 | real DB transaction interruption | Partial state remains | transaction rolls back; replay applies once |
| M07-DB-012 | NFR-COMP-001 | real DB/restart/replay | Older sequence regresses | receipt records stale and projection stays newer |
| M07-DB-013 | FR-ALERT-005 | real open alert from real event + command ports | Ack lost after restart | Ack/history persist without resolving condition |
| M07-DB-014 | FR-ALERT-005 | real alert/deadline worker | Snooze expiry applies twice | Fenced deadline produces one transition |
| M07-DB-015 | FR-ALERT-005 | real concurrent commands | Stale read/ack overwrites escalation | expected version/revision conflict |
| M07-DB-016 | FR-ALERT-005 | real recovery source event | Recovery loses occurrence history | terminal projection and immutable history retained |
| M07-DB-017 | FR-ALERT-005 | real recurrence source event | Reopen creates unrelated alert | stable ID/fingerprint, next generation, reset controls |
| M07-DB-018 | FR-ALERT-005 | real rule archive/re-evaluation | Config close says recovered | closed-by-configuration event persists distinctly |
| M07-DB-019 | FR-HIST-001/003 | real DB with naturally aged retained records or approved elapsed evidence | Purge deletes ineligible rows | only eligible terminal batch deleted |
| M07-DB-020 | FR-HIST-003 | real DB/repeated purge command | Retry deletes/reports differently | idempotent receipt/counts and referential integrity |
| M07-DB-021 | FR-HIST-002 | real accumulated alert history | Query unbounded/unstable | bounded deterministic cursor page |
| M07-DB-022 | FR-HIST-002 | real query-plan inspection | Full scan on core filters | approved indexes used at measured shape |
| M07-DB-023 | FR-HIST-005 | real DB driver | Timestamp precision/timezone changes | UTC round-trip and order are exact |
| M07-DB-024 | FR-ORG-003 | real registry rules/events + DB | Group move duplicates alert | same fingerprint, new resolution revision/history |
| M07-DB-025 | AC-V1-004 | real empty/supported-prior DB and Alembic | Migration/validation fails | upgrade applies, validates; safe recovery path proven |

If a scenario requires elapsed 365-day real records unavailable in the lifecycle, the cutoff calculation passes only T1 while the actual deletion scenario remains Blocked. The machine clock is never changed and timestamp fields are not hand-seeded to claim retention behavior.

### 9.4 Real HTTP service scenarios (T3)

| Test ID | Requirement | Real dependencies | Initial Red expectation | Pass condition |
|---|---|---|---|---|
| M07-HTTP-001 | FR-ALERT-001 | real server/SQLite/login or bearer | Rule routes absent | Authorized create/list/get through P01/contracts |
| M07-HTTP-002 | FR-ALERT-001 | real registry scopes | Effective-resolution endpoint wrong | Account/provider/org/global explanation matches persisted rules |
| M07-HTTP-003 | FR-ALERT-002 | real server/rule storage | Threshold units/validation drift | OpenAPI and behavior use basis points/exact schema |
| M07-HTTP-004 | FR-ALERT-005 | real alert from real upstream event | Ack route/state absent | CSRF/bearer-authorized ack persists and returns view |
| M07-HTTP-005 | FR-ALERT-005 | real active alert | Snooze action unsafe/non-idempotent | bounds/version/idempotency/problem outcomes conform |
| M07-HTTP-006 | FR-ALERT-005 | real alert projection | List fetch mutates unread | GET is safe and unread unchanged |
| M07-HTTP-007 | FR-ALERT-005 | real alert projection | Read action races | notification revision conflict is RFC 9457-safe |
| M07-HTTP-008 | NFR-SEC-001 | real browser session/token scopes | Unauthorized caller mutates | permission/CSRF/bearer denial with no state change |
| M07-HTTP-009 | NFR-COMP-001 | real OpenAPI/running response | Schema/client drift | response conforms; compatibility/client gate passes |
| M07-HTTP-010 | FR-HIST-002/FR-ORG-003 | real history/scope data | Filters/page order leak or drift | authorized bounded filters/cursor/counts are stable |

### 9.5 Real built-browser scenarios (T4)

| Test ID | Requirement | Real dependencies | Initial Red expectation | Pass condition |
|---|---|---|---|---|
| M07-BROWSER-001 | FR-ALERT-001/002 | built UI/real server/DB | Precedence/threshold editor unclear | Effective source/default/units visible and editable accessibly |
| M07-BROWSER-002 | FR-ALERT-005 | real current alert | Severity/state relies on color | text/icon/severity/source/freshness displayed |
| M07-BROWSER-003 | FR-ALERT-005 | real current alert | Ack/snooze workflow missing | keyboard/CSRF-backed actions update real state |
| M07-BROWSER-004 | FR-ALERT-005 | real snoozed/recovered alert | Filters/counts wrong | active/ack/snooze/recovery/unread filters truthful |
| M07-BROWSER-005 | AC-UI-005 | real empty/partial/dependency failure state | Placeholder telemetry appears | truthful empty/loading/partial/stale/failed states, no sample alert |
| M07-BROWSER-006 | FR-HIST-002 | real alert history | Timeline loses events/evidence | transition chronology and bounded paging visible |
| M07-BROWSER-007 | FR-ALERT-006 | built bundle/network inspection | External notification/egress exists | dashboard-only, no external send/config/network path |
| M07-BROWSER-008 | AC-UI-003/004/006 | real browser/viewports | Critical meaning/focus/time fails | 1920x1080 plus responsive, zoom, keyboard, names, contrast, UTC/local explanation pass |

### 9.6 Real live-event integration scenarios (T5/T6/T7 as applicable)

These require production upstream modules and actual owner-controlled conditions. They never revoke credentials, exhaust paid credits, stop active work, alter provider budgets, or force a stall merely to make a test pass without explicit owner approval of the exact action.

| Test ID | Requirement/AC | Real condition | Pass condition | Owner coordination |
|---|---|---|---|---|
| M07-LIVE-001 | FR-ALERT-003 | real capacity window naturally below configured warning | one warning alert with real source/provenance | owner confirms account/window/value in provider UI |
| M07-LIVE-002 | FR-ALERT-003 | real capacity window naturally below critical | same lifecycle escalates critical, no duplicate | owner comparison; otherwise Blocked |
| M07-LIVE-003 | FR-ALERT-003 | real exhausted/unavailable or forecast-before-reset state | correct distinct condition/severity/explanation | naturally available; otherwise Blocked |
| M07-LIVE-004 | AC-ALERT-003 | real managed profile requires reauth/revoked/wrong account | auth alert opens with no credential data | owner performs no secret sharing; natural/safe state only |
| M07-LIVE-005 | FR-ALERT-003 | same real profile later healthy through approved reauth | same auth alert recovers, history preserved | owner controls official reauth; default profile unchanged |
| M07-LIVE-006 | AC-ALERT-003 | real collector becomes stale under approved safe condition | stale/collector alert opens once | exact interruption/wait approved; otherwise Blocked |
| M07-LIVE-007 | FR-ALERT-003 | real collector resumes and reports current | same alert recovers once | no provider hammering; real completion/health event |
| M07-LIVE-008 | FR-STATE-003 | real session meets M06 possible-stall evidence | one inferred stall alert, no process mutation | owner identifies session; no input/signal |
| M07-LIVE-009 | AC-PROC-005 | real waiting-for-user/permission session | no stall alert; evidence remains truthful | owner confirms visible wait |
| M07-LIVE-010 | FR-ALERT-004/NFR-RES-001 | real redelivery/restart of durable event path | receipt/outbox replay yields one lifecycle | service restart only under operations plan |
| M07-LIVE-011 | AC-ALERT-002 | real active condition through server/browser | acknowledge, snooze, real recovery/reopen, history persist | recovery/recurrence may remain Blocked until naturally available |

### 9.7 Architecture, security, operations, performance, dependency, and documentation scenarios

| Test ID | Gate | Pass condition |
|---|---|---|
| M07-ARCH-001 | boundary | Import/API scan finds no provider/platform/other-module internal/process-control/external-delivery path |
| M07-ARCH-002 | V1 delivery | No SMTP/desktop/messenger/webhook dependency, config, table, command, or network destination exists |
| M07-ARCH-003 | safe action | Published commands are limited to rule/query/read/ack/snooze/retention/internal signal handling |
| M07-ARCH-004 | table ownership | No cross-module table/ORM access or FK exists |
| M07-ARCH-005 | portability | Domain imports no Linux/macOS APIs and macOS absence creates no false pass |
| M07-ARCH-006 | compatibility | Contract/event/OpenAPI/DB compatibility diff classifies every change |
| M07-SEC-001 | secret/content | Source/schema/DB/log/API/export/artifact scans contain no prohibited data |
| M07-SEC-002 | action boundary | No provider/profile/process/routing mutation can be reached through M07 |
| M07-SEC-003 | export | Real M08 export contains only allowlisted M07 fields and passes secret scan |
| M07-SEC-004 | logs | Real failure/commands emit bounded structured safe codes, not DTO/payload dumps |
| M07-SEC-005 | diagnostics | M07 health/diagnostics reveal no labels, source payload, paths, or identities |
| M07-SEC-006 | authorization | Every public command/query has explicit permission and denial evidence |
| M07-SEC-007 | malicious input | Oversize/unknown/free-text/generic event fields fail before persistence |
| M07-SEC-008 | browser | No alert data leaks to URL/localStorage/console/source map or unauthenticated docs |
| M07-OPS-001 | retention | Real purge job is bounded/idempotent and reports truthful counts/status |
| M07-OPS-002 | export/history | Real bounded export and alert history agree after restart |
| M07-OPS-003 | backup/restore | Real SQLite backup/integrity/restore preserves M07 invariants and replay safety |
| M07-OPS-004 | health | Real repository/upstream/outbox/job failure is visible and sanitized |
| M07-PERF-001 | At least 100 registered accounts | Approved real registered-account scope measures rule resolution/query bounds without seeded/demo accounts; absent scale is Blocked |
| M07-PERF-002 | At least 200 simultaneously discovered real processes | Approved real A04/M06 process discovery plus M07 condition/query path measures bounds without fabricated processes or telemetry; absent scale is Blocked |
| M07-DEP-001 | dependency | Manifests/lock/SBOM/notices show no unapproved M07 dependency/license |
| M07-DOC-001 | documentation | Module/contracts/traceability/runbook links and status validate |
| M07-DOC-002 | lifecycle | Rule/condition/state/unknown/recovery semantics match contracts/tests/UI docs |
| M07-DOC-003 | operations | Commands are documented only after canonical automation exists and is exercised |
| M07-TEST-001 | TDD | Every changed behavior has expected behavioral Red, Green, and refactor evidence |
| M07-TEST-002 | integrity | Repository scan/review finds no mock/fake/stub/emulator/recording/seeded telemetry/test-only injector |

### 9.8 Mutation and coverage quality

All documented branches in precedence, threshold boundaries, fingerprinting, ordering, lifecycle, recovery, ack/snooze/unread, retention cutoff, and authorization decision logic require meaningful coverage. Mutation testing must kill changes to precedence order, `<=` threshold boundaries, unknown/stale guards, fingerprint members, event generation comparison, recovery preconditions, escalation ack/snooze reset, 365-day cutoff, and permission checks. The exact target/tool requires dependency admission; surviving meaningful mutants block handoff.

## 10. Implementation increments

Every increment begins with its listed meaningful Red, then minimum Green, then refactor/documentation with the suite green. No increment begins before plan/contracts/migration allocation and prerequisite automation are Approved.

| Increment | Owned files/area | Failing tests first | Production behavior | Exit evidence |
|---|---|---|---|---|
| M07-I00 | approved contract package/docs | M07-ARCH-001/006, contract checks | freeze typed alert rule/signal/view/event vocabulary only | synchronized contract diff and consumer sign-off |
| M07-I01 | domain rules | M07-PURE-001..011 | precedence, scope candidates, 30/15 exact thresholds, validation | T1 R/G/R and mutation evidence |
| M07-I02 | domain condition evaluators | M07-PURE-012..021 | typed capacity/auth/stale/collector/stall mappings | T1 R/G/R; no provider imports |
| M07-I03 | fingerprint/reducer | M07-PURE-022..033 | canonical fingerprint, ordering, dedupe, transition reducer | T1 R/G/R and collision review |
| M07-I04 | user-state policies | M07-PURE-034..047 | unread/ack/snooze/recovery/reopen/retention/cursor policies | T1 R/G/R and mutation evidence |
| M07-I05 | first allocated migration/repositories | M07-DB-001..005/023/025 | rule/revision schema, UoW, configuration persistence | real file SQLite fresh/upgrade evidence |
| M07-I06 | alert persistence/events | M07-DB-006..012 | alerts/evidence/events/receipts/outbox atomic flow | real DB concurrency/replay evidence |
| M07-I07 | command/deadline persistence | M07-DB-013..018 | owner commands, deadlines, re-evaluation jobs | real DB restart/fencing evidence |
| M07-I08 | history/retention/query | M07-DB-019..024 | bounded query, purge, scope change, query indexes | real DB/query-plan/retention evidence |
| M07-I09 | composition event consumers | M07-LIVE-001..010 relevant Red plus contract integration | map synchronized real CAP/RUN/COL/REG auth events and re-query CTR-CAP/RUN views; no generic bus payload | real event evidence or explicit Blocked |
| M07-I10 | P01 mapping (separately allocated shared paths) | M07-HTTP-001..010 | authenticated rules/alerts/notifications/history routes and OpenAPI | real server/OpenAPI/generated-client evidence |
| M07-I11 | P02 alert feature (separate P02 owner) | M07-BROWSER-001..008 | mission-control alert console using generated client | built-browser/accessibility/responsive evidence |
| M07-I12 | operations integration | M07-OPS-001..004, SEC/ARCH/DEP/DOC | health, retention, export, backup/restore, automation/docs | canonical gates and sanitized handoff |
| M07-I13 | live acceptance | M07-LIVE-001..011 | no new behavior; exercise owner-coordinated matrix | Passed/Failed/Blocked/Not Run report |

### 10.1 Ordering and parallel-development safety

- I01–I04 may proceed inside M07 after contracts are approved and without persistence/API/UI edits.
- I05–I08 own only M07 persistence/migrations allocated centrally.
- I09 cannot start until the Draft-aligned CTR-CAP-008/009, CTR-RUN-004/005, CTR-COL-007, CTR-REG-009/010, and CTR-EVT-001 contracts are approved with their producers and real-boundary evidence is available.
- P01/P02 agents own their modules and shared generated artifacts; M07 provides contracts and reviews mappings rather than editing in parallel.
- M08/DB own backup/restore/global retention/migration automation; M07 supplies ports/invariants.
- Only one agent edits `alerting_v1`, a migration revision, OpenAPI source, generated client, or event registry at a time under root allocation.
- A discovered contract change stops affected work and returns to synchronization; no duplicate DTO/direct table access is permitted.

## 11. Documentation outputs

Implementation and approval require synchronized updates to:

- `docs/modules/alerting.md`: purpose, invariants, rules, condition/state machines, ports, data, errors, health, limitations;
- contract reference for CTR-ALERT-001..005 and every synchronized consumed event/query;
- OpenAPI human guidance for rules, alerts, notifications, filters, pagination, idempotency, permissions, and problems;
- generated OpenAPI/client change record;
- configuration registry with exact technical keys and persisted rule policy;
- operations runbook for precedence diagnosis, stale/auth/stall alerts, jobs/deadlines, restart, retention, backup/restore/export;
- alert test/live evidence matrix and Blocked/Not Run report;
- migration/upgrade/recovery notes;
- threat model/data minimization review;
- dependency/SBOM/notices record (expected no M07-specific package);
- traceability matrix and release notes/known limitations;
- ADR only where synchronization requires a consequential new durable-event/outbox decision.

Every implementation handoff uses the repository template and names requirement/AC IDs, module/contract versions, files, R/G/R commands/evidence, real-boundary results, blocked tests, security/privacy/migration/license/docs impact, and next integration step.

## 12. Dependency and license impact

M07 proposes **no module-specific third-party dependency**.

- Exact ratio/fingerprint/time/state policies use approved standard-library/common primitives.
- Persistence, FastAPI, migration, browser, formatting/type/security/mutation, SBOM/license, and build tools are admitted by their owning plans; M07 does not broaden approval.
- No scheduler, event bus, rules engine, expression parser, notification library, SMTP client, desktop library, messenger SDK, webhook client, analytics, or crash-reporting package is justified for V1.
- Before any package is added, document purpose, alternatives, upstream identity/license, transitive licenses, maintenance/security/provenance, platforms/native code/install scripts/telemetry, exact pin/lock, SBOM/notices, update/removal plan, reviewer/date. Pending is not Approved.

## 13. Risks, unresolved decisions, and stop conditions

### 13.1 Module risks

| ID | Risk | Likelihood/impact | Mitigation/evidence | Owner | Status |
|---|---|---|---|---|---|
| M07-R01 | Missing recovery events leave alerts permanently open or falsely recovered | High/Critical | CAP/RUN/COL/AUTH state-change contracts with generations and real replay tests | producer owners/M07/root | Open |
| M07-R02 | Scope race applies wrong org/provider/account rule | Medium/Major | revisioned narrow M02 scope port, reevaluation, optimistic conflict | M02/M07 | Open |
| M07-R03 | Fingerprint merges unrelated native windows/sessions or splits repetitions | Medium/Major | versioned canonical material, collision check, producer review/mutation tests | M07/M05/M06 | Open |
| M07-R04 | Stale/unknown becomes exhausted/available/recovered | Medium/Critical | typed truth state, guards, explicit stale alert, no raw input | M07/M05 | Open; R-007/R-008 |
| M07-R05 | Stall alerts are noisy | High/Moderate | M06 owns ten-minute/wait exclusion, dedupe/snooze, real tuning | M06/M07 | Open; R-016 |
| M07-R06 | At-least-once delivery duplicates or regresses state after crash | Medium/Major | atomic receipts/projection/outbox, per-stream sequence, real restart | DB/integration/M07 | Open |
| M07-R07 | Ack/snooze hides a new critical condition | Medium/Major | escalation clears ack/snooze, unread revision, browser tests | M07/P02 | Open |
| M07-R08 | Alert facts/events leak identity/content/provider errors | Medium/Critical | typed allowlist, references not payloads, scans, no notes | M07/security | Open; R-005/R-020 |
| M07-R09 | Durable history/outbox causes SQLite growth/locking | Medium/Major | bounded coalescing, indexes, short transactions, 365-day retention, measurement | M07/DB/M08 | Open; R-011 |
| M07-R10 | External-delivery behavior slips into V1 | Medium/Major | import/config/network absence gates and ADR 0009 | root/M07/review | Open |
| M07-R11 | Real rare conditions unavailable under no-simulation policy | High/Major | pure state proof plus visible Blocked live tests, naturally available evidence | test/owner | Accepted project constraint R-009 |
| M07-R12 | UI count/order semantics diverge from backend | Medium/Major | CTR-ALERT-005 authoritative, generated client, real browser | M07/P01/P02 | Open |

### 13.2 Approval-blocking synchronization decisions

1. **CS-M07-001:** freeze `AlertRuleTypeV1`, fixed severity mappings, and which non-threshold condition rules are built-in enabled. Owners: product/M07/P02.
2. **CS-M07-002:** approve whole-rule resolution and exact account > provider > organization > global > built-in behavior, including explicit-disabled no-fallback. Owners: owner/M02/M07.
3. **CS-M07-003:** freeze remaining-percentage basis-point source/denominator/nullability/rounding and capacity unavailable semantics. Owners: M05/M07.
4. **CS-M07-004:** freeze forecast activation/recovery, recovery boundary, uncertainty sufficiency, and event/query shape without inventing a horizon. Owners: M05/M07/product.
5. **CS-M07-005:** approve CTR-CAP-008/009 forecast/availability event semantics; confirm CTR-CAP-001/002/003/007 queries support rule reevaluation and M07 does not supply M05 health policy. Owners: M05/M07/root.
6. **CS-M07-006:** approve correlation/replay semantics between CTR-RUN-005 detection and CTR-RUN-004 recovery; confirm current session queries are sufficient and M06 remains sole stall-policy owner. Owners: M06/M07.
7. **CS-M07-007:** approve CTR-COL-007 health/failure/stale/recovery semantics; decide which failure/backoff states alert. Owners: M04/M07/M08.
8. **CS-M07-008:** approve M02-owned CTR-REG-010 persistence/recovery responsibility while preserving CTR-PROV-006 meaning and preventing direct M07 provider invocation. Owners: M02/M03/M04/root.
9. **CS-M07-009:** approve acknowledgement/read/snooze behavior, proposed 60-second/30-day bounds, escalation/recovery override, expiry unread behavior, and mark-unread workflow. Owners: owner/M07/P01/P02.
10. **CS-M07-010:** freeze fingerprint material/version/canonicalization/digest disclosure/collision behavior with every producer. Owners: M05/M06/M04/M07/security.
11. **CS-M07-011:** freeze lifecycle/transition vocabulary, deescalation notification, repeat coalescing, reopened generation, and closed-by-configuration semantics. Owners: M07/P02/M08.
12. **CS-M07-012:** approve CTR-REG-009 narrow scope/re-evaluation ports, archive/disable/ungrouped behavior, and registry revision race handling. Owners: M02/M07.
13. **CS-M07-013:** approve CTR-EVT-001 durable delivery/receipt/outbox/replay/ordering/retention semantics and decide whether an ADR is required. Owners: integration/DB/all producers/M07.
14. **CS-M07-014:** approve every CTR-ALERT-001..005 field, enum, nullability, error, ordering, pagination, authorization, idempotency, and compatibility promise. Owners: M07/M08/P01/P02.
15. **CS-M07-015:** approve M01 read/write permission mapping, P01 routes/ETags/idempotency/problems, and CSRF/bearer behavior. Owners: M01/P01/M07.
16. **CS-M07-016:** approve table names, canonical typed-config/fact storage, migration allocation, indexes, cross-module scalar IDs, and PostgreSQL portability. Owners: DB/M07.
17. **CS-M07-017:** approve 365-day terminal/history/receipt/rule-revision retention dependencies and M08 purge/export/backup/restore behavior. Owners: M07/M08/DB/privacy.
18. **CS-M07-018:** approve technical configuration keys/defaults/ranges/formulas and deadline/job lease ownership. Owners: foundation/config/M07/operations.
19. **CS-M07-019:** approve compliant NFR-PERF-001 evidence for at least 100 registered accounts and 200 simultaneously discovered real processes without invented accounts, processes, events, or telemetry. Any session benchmark is supplemental and cannot satisfy either required subject. Owners: owner/test/integration.
20. **CS-M07-020:** approve live scenario prerequisites, safe owner checkpoints, and which unavailable rare states may remain Blocked for a milestone/release. Owners: owner/test/integration.
21. **CS-M07-021:** confirm V1 has no external delivery consumer and future consumers of CTR-ALERT events require separate approval; audit dependency/config/network surfaces. Owners: owner/root/security.

Any unresolved item permitting materially different production behavior keeps Definition of Ready unchecked.

### 13.3 Stop and escalation conditions

Stop implementation/planning synchronization and notify root if:

- an upstream event cannot prove both activation and recovery with ordering;
- another module/table/internal import appears necessary;
- M07 would need a raw provider payload, free-form error, profile locator, process content, path, environment value, or secret;
- provider/OS/email/messenger/network logic enters M07;
- a contract meaning/version must change or a consumer rejects its semantics;
- a migration could destroy/unrecoverably transform history;
- event replay/outbox ownership cannot provide atomic idempotency;
- a dependency/license/supply-chain concern is unresolved;
- a real test needs authentication, paid-credit exhaustion, provider mutation, process disruption, service interruption, or owner action not already approved;
- live evidence contradicts threshold/freshness/auth/stall assumptions;
- existing user/agent changes overlap assigned files;
- the canonical gate is absent, red, skipped, or narrower than a proposed completion claim.

## 14. Delivery, compatibility, and rollback

### 14.1 Delivery order

1. Synchronize upstream gaps and common event durability.
2. Approve contracts, permissions, configuration, migrations, test resources, and this plan.
3. Implement pure policies under TDD.
4. Apply additive real SQLite migrations and repositories.
5. Integrate one producer family at a time: capacity, collection/auth, runtime, then registry re-evaluation.
6. Expose P01 resource/actions and regenerate/validate OpenAPI/client.
7. Add P02 alert console using only generated client.
8. Integrate M08 health/retention/export/backup/restore.
9. Run real event/browser/live acceptance and hardening gates.

M07 remains hidden/not ready until event receipt/replay and at least one real producer path are verified. Empty-state UI may exist, but no invented alert is rendered.

### 14.2 Compatibility and migration

- CTR-ALERT additive optional fields require safe absence behavior; changed state/severity/scope/unit/fingerprint/ordering/idempotency meaning requires a new major and migration/consumer plan.
- Fingerprint version changes require dual recognition or explicit reevaluation/migration; silent recomputation that duplicates alerts is forbidden.
- Persisted enum/config schema changes use expand/migrate/switch/contract where needed.
- Older binaries must refuse a newer incompatible schema.
- OpenAPI/client/event/database compatibility gates run before rollout.

### 14.3 Rollback and recovery

- Before migration, run approved backup preflight through `AUTO-MIGRATE`/`AUTO-BACKUP`.
- Prefer forward fix for additive code defects while preserving alert history/outbox.
- Disable the affected event consumer only through approved operations while retaining events for replay; never drop unknown events.
- If schema rollback is unsafe/unverified, stop service, preserve current DB, restore a verified backup to a new target, use compatible prior binary, validate M07 invariants, then resume.
- Rollback never sends external notification, edits provider state, or modifies a running agent.

### 14.4 Post-deployment checks

- schema/config/policy/contract versions agree;
- M07 readiness and repository integrity are healthy;
- no overdue event/deadline/job/outbox backlog exists;
- rule precedence/default explanation is correct;
- real current alerts/history survive restart;
- API/OpenAPI/client/UI versions agree;
- logs/diagnostics/export/backup pass prohibited-data scan;
- all T1–T4 and migration results plus T5/T6/T7 Passed/Failed/Blocked/Not Run states are visible.

## 15. Definition of Ready

- [ ] Requirements, interpretations, and V1 dashboard-only non-goals are owner-approved.
- [ ] M02/M03/M04/M05/M06 producer contracts named in section 4.8 are synchronized.
- [ ] CTR-ALERT-001..005 schemas, errors, permissions, idempotency, ordering, and compatibility are Approved.
- [ ] Common event receipt/outbox/replay ownership and transaction semantics are Approved.
- [ ] Allowed paths/imports/shared-file ownership and migration revisions are allocated.
- [ ] Persistence schema/index/retention/backup/restore/portability review is complete.
- [ ] Configuration keys/defaults/ranges/reload behavior are registered and approved.
- [ ] Test scenarios have reviewed expected Red behavior and real resources/owner checkpoints.
- [ ] Canonical planning, documentation, test, quality, migration, Git-preflight, build, backup/restore, deployment, and release automation ownership is recorded; required pre-implementation gates are green.
- [ ] Security/privacy/data-minimization/threat and no-external-delivery review is complete.
- [ ] Dependency review confirms no unapproved package.
- [ ] No unresolved decision permits materially different implementation.
- [ ] Plan status is Approved with exact plan/contract versions and reviewer/date.

Until every applicable box is checked, M07 is **Not Ready for implementation**.

## 16. Approval record

| Reviewer/owner | Decision | Conditions/evidence | Date |
|---|---|---|---|
| Product owner | Pending | rule/lifecycle/notification semantics and live checkpoints | — |
| Root/integration steward | Pending | cross-plan contracts, event durability, automation gates | — |
| M02/M03/M04/M05/M06 owners | Pending | consumed event/query contracts and recovery semantics | — |
| M08/P01/P02 owners | Pending | operations/API/UI mappings | — |
| Persistence/migration reviewer | Pending | schema/concurrency/migration/retention/restore | — |
| Security/privacy reviewer | Pending | minimization, auth, no delivery/egress, scans | — |
| Test-integrity reviewer | Pending | scenario boundaries, R/G/R, live/Blocked truth | — |
| Dependency/license reviewer | Pending | no new M07 dependency or admitted changes | — |

Approval must name plan version `0.2.0-draft`, synchronized contract versions, accepted conditions, and date. No implementation begins while this plan remains Draft.
