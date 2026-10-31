# M04 current collector conditions for M4 alerts

- Status: Approved for this focused implementation by root/integration steward, 2026-09-29, under existing full M4 authority.
- Version: 0.2.0.
- Owner: M04 collection-control role; root is contract, composition and migration steward.
- Parent: M04 plan 0.2.0-draft and approved M4 alerting packet 0.2.0 section 4.
- Story: ST-ALERT-001.
- Requirements: FR-ALERT-003/004, FR-COL-003/005/006/008, NFR-ARCH-001/002, NFR-DATA-001, NFR-RES-001, NFR-OBS-001, NFR-SEC-001, NFR-PRIV-001, NFR-TEST-001/002.
- Acceptance contribution: AC-ALERT-003, AC-V1-003/005/007/008, AC-TEST-001/002/003/006.
- Contracts: additive CTR-COL-007 V1 1.0.0; existing CTR-COL-002/004 optional failure-policy metadata; CTR-PROV-004, CTR-COMMON-006/007 and CTR-EVT-001 consumed unchanged.

## Outcome and actual source evidence

M07 receives producer-owned current collector failure/freshness facts and an explicit newer healthy/current inverse. Queries never collect, inspect a provider, infer an account or read another module's tables.

Actual `collection_schedule.record_version` increments on terminal transitions and target-policy generation changes. `collection_run.record_version` increments on its transitions. Neither is `target_generation`, and different runs can share the latter. The existing terminal path initializes schedule block/backoff fields but does not maintain them; `next_due_at` does not advance on terminal completion. The current executor discards M03's genuine retry advice. Schedule `last_successful_run_id` also points at partial runs. The old outbox payload contains run ID/state only. A successful current query cannot invent richer retry/health facts from those omissions or parse provider-specific error text.

Elapsed freshness alone advances no existing durable source version. A computed stale record with the old generation cannot prove a new condition to M07. This proposal adds one small producer-owned durable current projection with its own record version, refreshed separately from its read-only query.

## Exact immutable contracts proposed

All records are frozen/slots `TechnicalValueV1`, aware UTC, bounded tuples and closed enums. No dictionary, raw exception, label, email, path, provider payload or observation value crosses CTR-COL-007.

```python
CollectorHealthStateV1 = Literal[
    "healthy", "degraded", "failed", "blocked", "backoff", "unsupported",
    "paused", "unknown"]
CollectorFreshnessStateV1 = Literal[
    "current", "stale", "unknown", "unsupported", "not_applicable"]
CollectorRetryCategoryV1 = Literal[
    "none", "rate_backoff", "transient_backoff", "authentication",
    "authorization", "user_action", "compatibility", "unknown_constraints",
    "unsupported", "cancelled", "unclassified"]

CollectorAlertConditionV1(
    target_id: OpaqueIdV1, account_id: OpaqueIdV1 | None,
    provider_key: str, capability_id: str, generation: int,
    health_state: CollectorHealthStateV1,
    freshness_state: CollectorFreshnessStateV1,
    retry_category: CollectorRetryCategoryV1,
    latest_run_id: OpaqueIdV1 | None, last_successful_at: datetime | None,
    freshness_deadline: datetime | None, not_before_at: datetime | None,
    evaluated_at: datetime, reason_code: CollectorConditionReasonV1)

CollectorAlertQueryV1(
    as_of: datetime, deadline: datetime, correlation_id: OpaqueIdV1,
    provider_key: str | None = None, account_id: OpaqueIdV1 | None = None,
    target_id: OpaqueIdV1 | None = None, minimum_generation: int | None = None,
    limit: int = 100, after_target_id: OpaqueIdV1 | None = None)

async GetCurrentCollectorAlertInputsV1(query: CollectorAlertQueryV1
    ) -> QueryPageV1[CollectorAlertConditionV1]
async RefreshCollectorAlertInputsV1(query: CollectorAlertQueryV1
    ) -> QueryPageV1[CollectorAlertConditionV1]

CollectorHealthChangedV1(
    previous_health_state: CollectorHealthStateV1 | None,
    previous_freshness_state: CollectorFreshnessStateV1 | None,
    current: CollectorAlertConditionV1)

CollectionFailurePolicyV1(
    provider_outcome: OutcomeStateV1, retry: RetryAdviceV1)
```

`target_id` is the M04 schedule ID, not an account or generation-derived ID. Generation is that target's committed health row `record_version`, positive and monotonic. `minimum_generation` is permitted only with `target_id`, is inclusive, and is never compared across targets. Page order is opaque target ID ascending; cursor is exclusive. Limit is 1..200; positive deadline budget is at most two seconds for bounded local SQLite reads. No omitted/sentinel generation is allowed.

Closed condition reasons proposed: `collector_healthy`, `collector_partial`, `collector_failed`, `collector_blocked_authentication`, `collector_blocked_authorization`, `collector_blocked_user_action`, `collector_blocked_compatibility`, `collector_blocked_unknown_constraints`, `collector_blocked_unclassified`, `collector_rate_backoff`, `collector_transient_backoff`, `collector_unsupported`, `collector_cancelled`, `collector_paused`, `collector_no_success`, `collector_stale`, `collector_source_unknown`, `collector_clock_invalid`. Separate query availability codes: `collector_query_complete`, `collector_query_partial`, `collector_query_unavailable`, `collector_projection_missing`, `collector_projection_refresh_due`, `collector_generation_not_yet_available`. Queries never persist or return raw run error text.

## Meaning, freshness and explicit inverse

Classification uses only M04-owned actual schedule/run state and, when present, genuine typed M03 outcome/retry metadata:

| Actual evidence | Current meaning |
|---|---|
| Fully succeeded run, committed references, compatible current schedule/target generation | Healthy, current only before actual collection freshness deadline |
| Partial committed run | Degraded; cannot prove the healthy/current inverse |
| Failed run | Failed, unless actual persisted retry/backoff evidence applies |
| Blocked run/schedule | Blocked with proven category; absent metadata is unclassified |
| Actual persisted delayed retry, typed rate limit or transient outcome | Backoff with actual eligibility instant; provider advice alone is not proof that the scheduler persisted/applied a deferral |
| Unsupported run/schedule | Unsupported; no failure-as-zero or recovered assertion |
| Queued/running/committing | No recovery; preserve prior terminal condition or unknown if none |
| Cancelled | Unclassified/cancelled, never recovery |
| Paused/retired schedule | Paused/not applicable; configuration closure belongs to M07, not source recovery |
| Missing/inconsistent lineage or failed repository read | Unknown/query unavailable; no manufactured healthy or infrastructure-unavailable condition |

Approved conservative freshness policy: use the latest **fully succeeded** actual run with committed M04 references, under the current target generation. Deadline is its real `completed_at + schedule.effective_interval_seconds`. Retry/backoff does not extend that deadline or create new freshness. There is no hardcoded extra grace. No successful run means unknown. Equality with deadline is stale. This is collection freshness; M05/M06 metric/session currency remains their ownership.

A newer succeeded run is an explicit healthy/current inverse only when its same-target committed lineage is verified and its deadline is still current. Partial, unsupported, missing input, generic completion notice, silence and running state never recover. Refresh can accept only genuine current/past UTC as-of, cannot manufacture elapsed conditions using future instants, and cannot regress a prior evaluation. Pure policy tests may construct immutable temporal inputs; external-boundary tests cannot backdate records or patch time.

## Durable storage and transaction proposal

Root allocated additive migration `v1_0706`, parent `v1_0705`, owner M04. This role stages `backend/migrations/candidates/v1_0706_m04_collector_alerts.py`; root alone atomically publishes it and changes catalog/checker. Approved M04-local `collection_alert_condition`:

- schedule ID primary key / M04-local FK;
- positive `record_version`, source schedule record version and nullable latest run record version;
- closed current health/freshness/retry category and safe reason;
- latest run ID, successful completion, freshness deadline, not-before and evaluated-at;
- canonical condition digest, excluding evaluated-at so clock ticks alone cannot create repeated transitions.

Same actual source revisions/state/references/deadline return the same version. Actual new source evidence or a genuine elapsed freshness boundary increments the durable version. Generation, projection and `collector.health_changed.v1` typed event commit atomically. A distinct `collector-condition/<40-character schedule digest prefix>` outbox stream fits the existing 64-character column and uses the health record version as its sequence; it cannot collide with the existing run-terminal stream. The event payload and read adapter bind the full target ID and generation to that stream. Existing collection outbox/delivery remains M04-owned. Use the published `DurableEventV1`, `ReadEventBatchV1`, and `AcknowledgeEventDeliveryV1` signatures for owned typed read/ack adapters; never let root/M07 read M04 SQL.

Optional failure metadata seam: add `failure_policy: CollectionFailurePolicyV1 | None = None` keyword to M04's existing `finalize_failed`. The executor supplies it from the genuine collected `CollectionOutcomeV1` before normalization discards that envelope. The same terminal transaction persists new nullable `collection_run.provider_outcome_state` plus existing `retry_disposition/retry_eligible/retry_after`. Success/partial are rejected as a failure policy. Legacy missing values remain unknown/unclassified. This proposal changes no provider dispatch, eligibility or retry policy; any new applied schedule deferral needs a separately synchronized producer decision, not silent inference from advice.

Refresh is a named internal producer command, no HTTP route. It reads bounded M04 schedule/run/reference records, calculates pure conditions, rechecks source versions and commits a bounded batch. It holds no transaction across provider/module calls. Read query uses `open_bounded_sqlite_read` on explicit M04 tables only. Missing projection or expired unevaluated deadline is truthful partial/unknown; it does not synthesize a fresh state under an old generation. Query does not return expired healthy/current rows as current. Root's worker refreshes before reading and triggers M07 via published typed sources.

Root additionally approved a narrow M04-private direct SQLite writer because the shared normal opener's five-second pre-return wait cannot satisfy refresh's two-second budget. The writer uses `mode=rw`, `BEGIN IMMEDIATE`, remaining busy timeout, VM progress interruption, secure WAL/FK/FULL/read-uncommitted/trusted-schema policy, fixed M04 SQL/table authorization and unconditional rollback/close. Public `DatabaseRefV1.validate()` and the exact admitted adapter-only `DatabaseRefV1._path` field are its sole shared file-policy primitives; no other private symbol is admitted. Shared/global runtime timeouts are unchanged. Verified bounds cover local SQLite lock/VM work, not hard OS filesystem stalls.

The published v1_0706 migration adds nullable `consumer_receipt_id` and `ack_payload_digest` to M04's delivery table. Two producer-owned BEFORE INSERT/UPDATE triggers reject partial or malformed proof; a preflight accepts legacy NULL/NULL pairs but refuses inconsistent existing rows. The adapter binds a genuine consumer receipt and exact payload digest, permits exact replay, and rejects a conflicting re-ack. The migration also adds nullable closed typed provider outcome metadata without backfilling legacy rows.

## Assigned paths proposed and forbidden scope

Proposed exclusive writes after root approval: `contracts/collection_control_v1.py`; M04 domain policy and application condition facade/ports; owned `adapters/persistence/collection_control/sqlite/` condition adapter; existing M04 executor/repository optional metadata seam; focused `backend/tests/collection_control/` pure and `backend/tests/integration/collection_control/` real tests; M04 module/evidence guide; this plan. Root alone allocates the migration, catalog, checker, composition, event/common/alert contracts, API/UI/generated client and automation.

No imports of M02/M05/M06/M07 internals, other-module SQL, provider I/O, profile changes, agent control, new dependency, `.env` change or owner-service action by this role.

## Test-first and truthful resources

| Scenario | Expected meaningful Red | Real Green/resource |
|---|---|---|
| M04-ALERT-P01 | Failure conflated with blocked/backoff/unsupported | Pure immutable classifier inputs; exact inverse and unknown branches |
| M04-ALERT-P02 | Partial/running/missing evidence recovers | Pure fully committed lineage and explicit recovery requirements |
| M04-ALERT-P03 | Equality expiry/current deadline or time-only old generation | Pure boundary plus actual persisted refresh generation |
| M04-ALERT-DB01 | Missing current projection reported available | Actual production migrations/empty SQLite; no seeded business rows |
| M04-ALERT-DB02 | New actual source/expiry does not advance durable version | Genuine pipeline-produced M04 runs, durable refresh/reopen/idempotency/concurrency/page checks |
| M04-ALERT-DB03 | Actual retry metadata lost or inferred for legacy | Genuine applicable M03 failure if naturally available; otherwise Not Run, pure policy only |
| M04-ALERT-LIVE01 | Success/real expiry not represented through current query | Actual eligible pipeline history and naturally elapsed deadline; no provider action by this role |
| M04-ALERT-INT01 | No explicit current/inverse delivery | Root real producer/M07/service/HTTP/browser integration |

Direct seeded schedule/run/failure/health rows, fake collectors/sinks, canned provider results, patched clocks and backdated telemetry are forbidden. Existing tests with constructed provider-shaped admissions are not reused as non-empty producer truth. Root must supply/wire actual eligible pipeline history for non-empty T2 evidence; naturally absent failure/rate/auth/unsupported conditions remain Not Run or Blocked. Schema-only actual migrations can proceed without a provider claim after allocation. No broader M04/M4 completion claim follows from pure or empty-query Green.

## Documentation, security, compatibility and approval needs

Add M04 guide/evidence and root-owned contract registry/traceability/runbook integration. No provider payload, identity label, path or credential is added; event and query snapshots contain opaque subject/run references, closed states and times. Existing table ownership remains M04. The migration is additive with nullable legacy metadata; old rows are not backfilled with invented outcomes. Reverting exposure/code preserves rows/history; migration downgrade is not promised.

Root approved the exact six-point proposal and target-scoped generation/full-success corrections. Freshness has no retry extension. This role is sole writer of the declared collection contract and M04 paths; root owns shared catalog/common/event adoption/composition. Current condition and event must commit atomically. Genuine non-empty source resources remain required for T2/live acceptance and cannot be substituted. Stop on incompatible contract, provider-specific parsing, unapproved scheduling changes, shared migration conflict, prohibited data or fake external-boundary proof. This focused approval does not accept the broader M04 Draft or full M4.
