# Module change plan: M05 — M4 fleet capacity, health, and forecasts

- Status: **Approved for I01 current metadata/health/aggregation, I02 current capacity facts, I03 committed-notice delivery, and I04 durable current forecasts/capability availability; auth/collector ingestion and full M4 acceptance remain separate**.
- Plan version: `0.5.0`; root review date: 2026-09-29.
- Owner: M05 Capacity; independent planning assignment from root.
- Parent: [M05 plan](../modules/m05-capacity/plan-v1.md), `0.2.0-draft`;
  this bounded plan does not approve that full V1 plan.
- Milestone/story: `V1-M4`, `ST-FLEET-002`; supports `ST-FLEET-003`,
  `ST-ALERT-001`, and `ST-OPS-001` through published contracts.
- Authority: the owner's full M4 implementation direction; root retains
  approval of shared contracts, migration ordering, and implementation packets.
- Requirements: `FR-ORG-003`, `FR-QUOTA-001..006`, `FR-COL-001..008`,
  `FR-HIST-001/002/005`; supporting `NFR-ARCH-001/002`, `NFR-DATA-001`,
  `NFR-API-001/002`, `NFR-SEC-001`, `NFR-PRIV-001/002`, `NFR-COMP-001`.
- Acceptance: M05 portions of `AC-LIVE-004/005/007`, `AC-HIST-001`,
  `AC-UI-002/005/006`, `AC-TEST-001/002/003/005/006`.
- Contracts: compatible extensions to `capacity.v1`, `CTR-CAP-001..009`;
  existing `CTR-COMMON-003/004/006/007`, `CTR-REG-002/005/009/010`,
  `CTR-COL-006/007`; root must synchronize new event storage ports under
  `CTR-EVT-001` and leaf health under `CTR-OPS-006`.
- Reviewers: root/integration, M02/M04/M07/M08, P01/P02,
  persistence/migration, security/privacy, test integrity.

## 1. Outcome and boundaries

An authenticated user sees organization, provider, global, or account capacity
with its actual member accounts, fresh coverage, missing and excluded accounts,
health counts, and separate native quota windows. A remaining percentage is
always for one evidenced window; the application never invents an organization
percentage by adding or averaging unrelated allowances. Each account/window
has either an explained derived forecast or an explicit insufficient-input
result linked to the actual history used.

M05 owns arithmetic, completeness, health, aggregation eligibility, burn and
forecast policies, capacity persistence, lineage, and capacity events. M02 owns
membership/identity/resource facts; M04 owns cadence, admission, leases,
deadlines, backoff and collection-run health. M07 owns alert thresholds and
lifecycle. P01 owns HTTP, IAM mapping and OpenAPI; P02 owns generated-client UI;
M08 owns product readiness and diagnostic/backup orchestration.

This plan excludes additional providers, API billing implementation,
currency conversion, process switching/control, provider parsing, provider
authentication changes, and a new retention/export feature. Existing 365-day
capacity retention policy and protections remain in force. Full V1 retention
deletion acceptance needs naturally aged real data and is not proved here.

### Write allocation after approval

M05 implementation may change only assigned files under:

```text
backend/src/agentmonitor/modules/capacity/domain/{aggregation,forecast,health}.py
backend/src/agentmonitor/modules/capacity/application/{queries,ports,projections,availability,events}.py
backend/src/agentmonitor/adapters/persistence/capacity/sqlite/**
backend/tests/capacity/pure/**
backend/tests/integration/capacity/**
docs/modules/capacity.md
docs/evidence/m4-capacity.md
```

For approved I01, the M05 agent is the sole assigned writer for
`contracts/capacity_v1.py` under root contract stewardship, its own
`application/commit.py` and `ingest.py` when health wiring requires them,
and the application/repository paths above. Root is the sole writer for registry/event/common
contracts, migration revisions/head, M02/M04 changes, composition, API schemas
and routers, OpenAPI/client generation, frontend, planning/control manifests,
canonical automation and shared documentation. A separate assignment is needed
before modifying an existing application/repository file also held by root.

Allowed domain imports: pure standard library, M05 domain and published common
and M05 contracts. Application imports its own domain/ports and published
registry, collection, event and operations contracts. Persistence imports its
own module's published ports and the admitted SQLite/SQLAlchemy stack. No
deep cross-module imports, foreign table access, framework/OS/provider imports
in the domain, provider-specific branches, raw dictionaries, or new dependency.

## 2. Requirements and traceability

| Requirement/AC | Owned outcome | Contracts | Scenarios |
|---|---|---|---|
| FR-ORG-003 | Revisioned global/org/provider/account inventory and compatible totals only | CAP-003, REG-009/005 | M4-CAP-P01..05, M4-CAP-L01, M4-CAP-H01 |
| FR-QUOTA-001/002 | Separate native windows, exact values and no fabricated combined allowance | CAP-001/003 | M4-CAP-P03/04, M4-CAP-L01 |
| FR-QUOTA-003 | Wire the existing classifier with M05-owned policy and current facts | CAP-003/005/009 | M4-CAP-P05, M4-CAP-L02 |
| FR-QUOTA-004; FR-COL-004/006/008 | Provenance, freshness, coverage and no-value states | CAP-001/003/009 | M4-CAP-P02/05/10, M4-CAP-L01..03 |
| FR-QUOTA-005 | Sufficient-input burn and forecast with method/input/uncertainty | CAP-006/007/008 | M4-CAP-P06..10, M4-CAP-L03, M4-CAP-H02 |
| FR-QUOTA-006; AC-LIVE-004/005/007 | Exact existing evidenced Claude source; truthful rare-state matrix | CAP-001, approved A01 handoff | M4-CAP-L01..04 |
| FR-COL-001/002/003/005/007 | Supporting M05 commit/availability seam only; M04 remains primary owner | COL-006/007, CAP-004/009 | M4-CAP-L04; root M04 fleet suite |
| FR-HIST-001/002/005; AC-HIST-001 | Immutable UTC history, reproducible derivations and actual chart/table | CAP-006/007 | M4-CAP-L03, M4-CAP-H02, M4-CAP-B01 |
| AC-TEST-001/002/003/005/006 | Meaningful Red/Green/refactor and separate live outcomes | canonical M4 gate | all scoped scenarios |

The table uses shortened contract families only; all refer to the exact
`CTR-*` IDs in the header. M05 does not claim the M04 requirements complete
because its own commit succeeds. Existing M05 scenario IDs remain valid;
the M4 IDs specify this focused change's executable inventory.

## 3. Current evidence and domain decisions

Planning inspection found these actual artifacts:

- `capacity_v1.py` publishes inputs/current/account/history types and a reserved
  budget view. It does not yet publish aggregate, forecast, or change-event DTOs.
- `queries.py` and the real SQLite repository serve per-account current and
  cursor history. Five M05 migrations already create aggregate, derivation,
  forecast, availability and outbox tables; their presence is not implementation.
- `domain/health.py` has the pure classifier. Commit persistence currently
  records `unknown` with `no_configured_health_policy`; classification is not
  wired into actual current projections.
- `RegistryScopeSnapshotV1` is `CTR-REG-009`, not the Task 2 plan's shorthand
  `CTR-REG-007`. It contains IDs/revision and includes non-archived accounts.
  It does not describe monitoring eligibility, exclusion reasons or evidenced
  pool aggregation relationships.
- `AccountResourceViewV1` has kind/parent/lifecycle but no cross-account shared
  pool ID or additive relationship proof. Similar labels/emails are not proof.
- Quota input/history preserve semantic role and reset metadata; current view
  omits these fields. Claude's accepted source supplies provider display reset
  text, while its mapper deliberately stores no inferred reset instant.
- The service already polls genuine enrolled Claude profiles independently,
  observing the accepted source's minimum interval. This change does not
  shorten that provider-specific minimum to satisfy a nominal active interval.

No provider/browser/database mutation or test was performed by this planning
assignment. New scenarios below are **Not Run**.

### Membership and coverage

One aggregate is computed from one immutable registry revision and explicit UTC
`as_of`. Input account/resource views must belong to that same revision; root
must obtain them through published M02 queries and verify the snapshot again,
or publish one atomic M02 fleet-scope port. A mismatch returns
`registry_scope_changed`; it never serves a silently mixed revision.

Partition registry member account IDs into `eligible_account_ids` and
`excluded_accounts` with reason codes. Eligibility follows current M02 lifecycle
and effective monitoring plus an active matching resource. Partition eligible
IDs into `covered_account_ids` and `missing_accounts`. Coverage means usable
fresh evidenced current windows; stale or partial records remain visible in
account inventory with their precise missing/partial reasons. Archived/disabled
records retain history and never become numeric zero.

Invariants: partitions are disjoint, exhaustive, deterministic and duplicate
free; covered is a subset of eligible and of scope membership. Report
`registered_account_count`, `eligible_account_count`, `covered_account_count`,
`excluded_account_count`, `missing_account_count`, and a separate
`observed_capacity_count`. Never rename connection count as unique identity
count. Include `registry_revision`, aggregate `generated_at`, input observation
IDs and a canonical input digest.

### Windows, pools and duplicate connections

Keep window inventories keyed by provider, resource/pool, native window key,
definition version, semantic role, unit, interval/reset segment and source
compatibility. Equal native labels do not establish equal quota periods.

Numeric sums require explicit M02 relationship evidence: an additive group,
identical quantity unit/currency and semantic role, identical native interval,
and no overlapping rollup parent/child. Ratios and percentages are never summed.
With the current independent Claude subscription windows, return no organization
numeric total and explain `independent_native_windows` or
`pool_relationship_unknown`; actual per-account allowances remain visible.

Known identical provider identities can share one *presentation* capacity
group only when current successful pre/post identity receipts are tied to the
actual observation/run and same provider, provider organization and dashboard
scope. Root must provide an opaque equality descriptor through a published
contract; M05 never receives email/profile paths or fabricates identity from
friendly names. Report all alias account IDs and separate connection count.
Identity equality alone never proves additive capacity, a shared resource pool,
or interchangeability of histories. A conflict or absent receipt retains
separate records and suppresses any uncertain numeric aggregation. Deduplication
never merges/deletes registry records or rewrites original observations.

### Health

Propose `capacity-health-default-v1`, policy version `1.0.0`, M05 fixed
classification boundaries constrained at `0.30` and critical at `0.15`, equality
inclusive; root must approve before wiring. These are separate policy values
from M07 editable alert thresholds and the owner's UI red-bar threshold of 20%.
Changing M07 settings never changes M05 health.

Use exact native remaining ratio or the existing explained `100-used percent`
derivation. Auth-required from matching current ordered auth evidence has
precedence; otherwise fresh exact exhaustion and the worst known independent
constraint apply. Unknown/stale/conflicted windows prevent an Available
result; definitive worse evidence remains with partial completeness. An
aggregate must not claim Available when any eligible member lacks coverage.
Unavailable/auth capability is distinct from a stale retained numeric fact.

### Forecast method and sufficiency

Propose pure method `bounded-secant-v1`, version `1.0.0`, over one compatible
window/metric/source/reset segment. Policy: at least three distinct observations,
minimum span 900 seconds, maximum adjacent gap 900 seconds, bounded latest 200
points, maximum future horizon seven days. Explicit UTC `as_of`; no clock I/O.
Root approves these product derivation defaults for I01.

Root also approves optional current `completeness` metadata from the actual
stored observation; partial scope cannot become complete/Available. An additive
M05 metadata/bounds revision is allocated after the three M07 revisions as
`v1_0703_m05_capacity_projection_metadata.py`, parent `v1_0702`, ordinal 703.
It adds nullable constraint metadata (legacy rows unknown) and required exact
forecast bounds columns without rewriting any shared migration. The M05 agent
may supply the isolated revision file; root owns its catalog/head/schema and
live backup/quiescence/migration integration. A field not previously stored
remains unknown until a real typed observation supplies it after migration.

Order by observed time and observation ID; retain zero-delta interior samples,
but require positive net consumption and monotonic compatible series. Reset
or decrease splits the evidenced segment; unknown reset identity, conflicting
equal-time values, source/schema/definition change or correction yields typed
insufficiency/conflict rather than a guessed rate. Latest remaining must be
fresh and exact, or have explicitly evidenced lower/upper precision bounds.

Use exact Decimal endpoint consumption divided by elapsed seconds and include
the full sample IDs. Compute rate lower/upper from input precision bounds;
positive lower rate is required for a bounded exhaustion range. Round only the
UTC result interval outward to whole seconds. Never use float timestamps in
rate arithmetic. Confidence is at most `medium` for this extrapolation; expose
`future_consumption_assumed_constant`, precision/source limits and method.
Validity is no later than the latest source freshness deadline. Report whether
an evidenced reset precedes exhaustion, follows it or is unknown.

Currently Claude reset segment/precision bounds may be unavailable. An actual
query then returns `insufficient_input` with `reset_segment_unknown` or
`precision_bounds_unknown` and actual input coverage. M05 must not parse Claude
display reset text. Any new A01 reset/rounding mapping is a separately allocated
provider contract change with fresh real evidence. An insufficient result may
pass its own truthful-state scenario; it does not pass a live available-forecast
scenario. Group/global forecasts remain per comparable native group/account
inventories and never produce a universal exhaustion timestamp.

## 4. Public contracts and synchronization packet

All proposals below are additive V1 with closed fields and bounded tuples.
No existing meaning, required constructor argument, request grammar, event
delivery guarantee or canonical payload digest is changed.

| Contract | New/extended public types and ports | Semantics |
|---|---|---|
| CTR-CAP-001 | Optional current-view `semantic_role`, `is_constraining`, `definition_version`, `reset_at`, `reset_precision`, `registry_revision`, `projection_version`; `ListQuotaWindowsV1` remains compatible | Fields come from already stored facts; absent is unknown, never inferred |
| CTR-CAP-002 | Existing reserved `BudgetViewV1` unchanged | M4 Claude slice does not invent API billing values |
| CTR-CAP-003 | `CapacityAggregateQueryV1`, `CapacityAggregateViewV1`, `CapacityAccountCoverageV1`, `CapacityAggregateWindowGroupV1`, `CapacityNumericAggregateV1`; `GetCapacityAggregateV1(query)` | One scope/revision/as_of; exhaustive eligibility/coverage/exclusion, native inventories, health/freshness counts, optional proven numeric groups |
| CTR-CAP-004 | `CapacityObservationRecordedV1`; public bounded M05 event storage port | Observation/run/projection references, subject scope, schema/generation/sequence, no metric values/labels |
| CTR-CAP-005 | `CapacityHealthChangedV1` | Canonical state/completeness/freshness transition and source refs; no M07 rule state |
| CTR-CAP-006 | Existing `CapacityHistoryQueryV1` preserved; module-owned bounded forecast-history read port | Exact existing series/cursor/UTC rules; no hidden provider refresh |
| CTR-CAP-007 | `CapacityForecastPolicyV1`, `CapacityForecastQueryV1`, `CapacityForecastV1`, `CapacityBurnRateV1`; `GetCapacityForecastV1`, `ListCapacityForecastsV1`, internal `RecomputeCapacityForecastV1` | Discriminated available/insufficient_input/not_applicable/stale/conflicted; exact rates/ranges, confidence, reasons, lineage and validity |
| CTR-CAP-008 | `CapacityForecastChangedV1` | Ordered generation and explicit active/invalidated/recovered/not_evaluable; no recovery inferred from silence |
| CTR-CAP-009 | `CapacityAvailabilityViewV1`, `CapacityAvailabilitySignalV1`, `CapacityAvailabilityChangedV1`; internal apply/query ports | Separate auth/collector/capability streams, generation ordering and explicit matching newer recovery |

`CapacityAggregateQueryV1` carries `RegistryScopeSnapshotV1`, revision-consistent
published account/resource views, safe optional pool/identity equality evidence,
`as_of` and policy version. No second hand-written registry DTO. Domain input
is prepared by M05 application from these published facts. If root chooses an
atomic M02 query instead, that snapshot belongs to M02 under `CTR-REG-009`.
The current separate public queries are adequate only with the revision check.

`CapacityForecastV1` includes account/resource/window/metric IDs, state,
method/version, input observation IDs/digest, generated/valid-until UTC times,
confidence, precision, reason codes and explicit uncertainty. Available adds
exact rate with fixed per-second unit plus earliest/latest exhaustion UTC and
reset relation. No-value variants carry no numeric estimate. Persist optional
prior result only as an explicitly stale view, never current available.

Root must publish exact event envelope/storage/receipt types before M07 consumes
M05 outbox. Existing internal `capacity.committed.v1` must keep its meaning;
add canonical CAP-004/005/008/009 events, do not silently reinterpret it. M07
owns processing receipts/checkpoints; M05 owns producer delivery rows. Outbox
delivery loss must not recollect, erase committed observations, or infer recovery.

### Minimal concrete DTO field proposals

These are closed schema definitions for root review, not runtime telemetry or
an alternative handwritten UI schema. All identifiers use `OpaqueIdV1`, exact
quantities use the admitted `ExactQuantityV1`, timestamps are aware UTC.

- `CapacityAggregateQueryV1`: `scope_snapshot: RegistryScopeSnapshotV1`,
  `accounts: tuple[AccountViewV1, ...]`,
  `resources: tuple[AccountResourceViewV1, ...]`, `as_of: datetime`,
  `policy: CapacityHealthPolicyV1`, optional tuple of root-approved opaque
  equality/relationship evidence. Default evidence is empty, meaning unknown.
- `CapacityAccountCoverageV1`: `account_id`, `resource_ids`,
  `eligibility: eligible|excluded`, `coverage: covered|missing|partial`,
  `reason_codes`, `health: CapacityHealthViewV1|None`, `windows`,
  `input_observation_ids`. Excluded accounts have no coverage contribution;
  their stored historical data is still accessible through account history.
- `CapacityAggregateWindowGroupV1`: `provider_key`, `native_window_key`,
  `semantic_role`, `unit|None`, `resource_ids`, `account_ids`,
  `input_observation_ids`, `relationship_state`, `reason_codes`,
  `numeric_values: tuple[CapacityNumericAggregateV1, ...]`. Window inventory
  grouping does not certify that periods or resource pools are comparable.
- `CapacityNumericAggregateV1`: `metric: used|remaining|limit`,
  `quantity: ExactQuantityV1`, `interval_start`, `interval_end`,
  `aggregation_group_id`, `relationship_evidence_id`, `input_observation_ids`,
  `value_kind='derived'`, `precision`, `confidence`. Never a ratio/percentage.
- `CapacityAggregateViewV1`: `scope_kind`, `scope_id|None`,
  `registry_revision`, `generated_at`, `completeness: complete|partial|unknown`,
  `availability: available|unavailable`, `reason_codes`,
  `eligible_account_ids`, `covered_account_ids`, `missing_accounts`,
  `excluded_accounts`, `accounts`, `window_groups`, `health_counts`,
  `freshness_counts`, `worst_health`, `input_observation_ids`,
  `input_set_digest`, `policy_id`, `policy_version`; named counts are derived
  from these exhaustive partitions, never maintained as contradictory values.
- `CapacityForecastSampleV1`: `observation_id`, `window_definition_id`,
  `definition_version`, `subject`, `window_key`, `metric`, `observed_at`,
  `consumed: ExactMetricFieldV1`, `remaining: ExactMetricFieldV1`,
  `source_compatibility_id`, `reset_segment_id|None`, `reset_at|None`,
  `freshness_deadline|None`, `lower_consumed_bound|None`,
  `upper_consumed_bound|None`, `lower_remaining_bound|None`,
  `upper_remaining_bound|None`. Bounds and segment ID require evidence;
  unknown inputs produce insufficiency. Exact values can be their own bounds.
- `CapacityForecastPolicyV1`: `method_id`, `method_version`,
  `minimum_samples=3`, `minimum_span_seconds=900`,
  `maximum_gap_seconds=900`, `maximum_samples=200`,
  `maximum_horizon_seconds=604800`. Pure function takes policy, ordered
  samples and `as_of`; output does not perform I/O or retain a fake clock.
- `CapacityForecastQueryV1`: `account_id`, `resource_id|None`,
  `window_id|None`, `as_of`, `limit` in 1..200, `after_key|None`.
- `CapacityBurnRateV1`: exact `estimate`, `lower_bound`, `upper_bound`,
  `time_basis='second'`, `sample_count`, `observed_span_seconds`,
  `input_observation_ids`; rate quantity unit is fixed by native input unit.
- `CapacityForecastV1`: `forecast_id`, `generation`, `subject`,
  `window_id`, `window_definition_id`, `metric`, `state`,
  `burn_rate|None`, `earliest_exhaustion_at|None`,
  `latest_exhaustion_at|None`, `reset_relation: before|after|unknown`,
  `confidence`, `precision`, `uncertainty_codes`, `reason_codes`,
  `input_observation_ids`, `input_set_digest`, `method_id`, `method_version`,
  `generated_at`, `valid_until|None`. Values exist only in the available
  variant; no-value variants preserve lineage and explanation.
- CAP-004/005/008 events: frozen published event envelope plus opaque
  `account_id`, `resource_id`, `projection_id`, `generation`,
  `input_observation_ids`, canonical prior/current state when applicable,
  `reason_codes`; no metric values, aliases, email or private fingerprints.
- `CapacityAvailabilitySignalV1` / `CapacityAvailabilityViewV1` / CAP-009:
  `account_id`, `resource_id`, `capability_id`,
  `signal_kind: authentication|collector|capability`, `generation`,
  `stream_sequence`, `state`, `source_record_id`, `source_record_version`,
  `observed_at`, `expires_at|None`, `reason_code`,
  `recovery_of_generation|None`. Different kinds are independent streams;
  generation alone never clears another kind or scope.

Exact shared envelope, equality/relationship descriptor and availability enum
spellings are the remaining root-owned synchronization choices. These must
exist before affected implementation; pure health/coverage/forecast increments
can be individually approved with unknown external evidence preserved.

### Root integration requirements

1. Approve the policy defaults and these type signatures; allocate contracts
   and any M02 pool/equality evidence type. Unknown relationships stay unknown.
2. Synchronize M04 capability failure/auth/recovery mapping and matching
   generations into CAP-009. A generic successful collection does not clear
   an auth-required or unrelated capability signal.
3. Publish shared event/leaf operations ports and closed error codes.
4. Add new endpoints rather than change existing operation objects. Proposed
   GET `/api/v1/capacity-aggregates` with bounded scope kind/ID and GET
   `/api/v1/accounts/{account_id}/capacity-forecasts`, with explicit scope,
   native window filter, as_of and read:telemetry permission. Stable operation
   IDs proposed `getCapacityAggregateV1`, `listAccountCapacityForecastsV1`.
   P01 must freeze grammar/page bounds/problem mappings before generation.
5. Update API generator admission/policy/source hash list, generate both
   artifacts, compile all consumers and run actual HTTP contract tests.
6. Render aggregate inventory/counts and per-window forecast/no-value states
   through the generated client, retaining independent native window charts.
7. Register scoped suites and machine-readable live outcomes under the full
   fail-closed M4 gate; update adoption/ownership/configuration/traceability.

## 5. Data, migration and recovery

Use existing M05 `capacity_*` definitions, immutable observations/provenance,
current/health/aggregate projections, derivation inputs, forecast, availability,
outbox/delivery and retention tables through the M05 repository only. Cross
module IDs remain scalar; no foreign joins/FKs. Reads are bounded and indexed.

Commit observations, receipts, current health and canonical source-change events
atomically. Forecast recompute is a separate short idempotent transaction keyed
by canonical observation set + method/policy version. Query is read-only; an
explicit internal recompute owns writes and emits generation changes. Registry
revisions partition aggregate projections; newer membership never relabels
immutable historical observations. Validate projection/input consistency.

Existing forecast storage has only one exhaustion instant; storing earliest/
latest bounds requires an additive M05 migration allocated by root, rather
than hiding fields in JSON or modifying a shared revision. Existing aggregate
storage counts included/omitted subjects; any required partition details need
module-owned child records or an additive closed bounded representation reviewed
by persistence. Root selects exact changes after checking query needs. No hidden
startup DDL, migration-history rewrite, drop, destructive backfill or downgrade.

Before upgrading the live database: use the canonical approved migration
preflight/service lock and verified backup, preserving M06's separate owner
association settings under ADR0015. Apply additive revisions explicitly and
verify integrity, prior history/receipt IDs, readiness and actual quota queries.
Recovery preserves the failed database and restores to a distinct approved
target or uses a forward fix; never overwrite the only copy. Recovery acceptance
must exercise a real file-backed database, not a schema description.

Exact coefficients/scales, UTC text and integer generations remain portable
through adapter mapping; no SQLite float coercion or cross-module SQL. Inputs,
derivations and events retain existing 365-day/protected-reference policy.

## 6. External boundaries

M05 makes no provider, profile, filesystem, browser, process or network calls.
Real A01 observations arrive through M03/M04 typed outcomes; source/provider
version and approved freshness/minimum interval remain unchanged. Root schedules
the existing real collectors once per due target; no looping retries or extra
quota-consuming requests to create forecast history. A collection failure
affects only its target; retained source facts age normally.

## 7. Security and privacy

Only authenticated authorized read:telemetry views expose capacity/history.
Internal writes require root-owned system orchestration and generation guards.
Scope/cursor/time/cardinality validation is closed and bounded. Persist opaque
IDs, exact capacity values, method versions, input lineage and safe reason codes
only; no identity email, profile path, prompts/responses/source, environment,
provider credentials/raw responses or free-form errors. Numeric capacity and
private identity fingerprints never enter logs/events/diagnostics/evidence.

Inspect real resulting database/WAL, generated payloads, browser console/storage,
events and M08 diagnostic output for prohibited fields. Shared-pool overlap,
stale-as-current, wrong membership and falsely precise forecasting are explicit
integrity threats (R-007/008/014). No new outbound telemetry or dependency.

## 8. Configuration and operations

The proposed M05 health and forecast policies are versioned non-secret typed
defaults, not new `.env` keys or M07 settings. Root approves any future editable
policy separately with audit/version/recompute semantics. Provider freshness and
source minimums cannot be weakened by these policies. Component leaf health
reports only safe versions, repository/derivation status, counts/ages/backlog
and safe failure codes. It does not fan in global readiness or account values.

## 9. Test design and evidence inventory

| ID | Boundary | Expected meaningful Red | Required Green evidence |
|---|---|---|---|
| M4-CAP-P01 | Pure | Scope partitions/counts mix revisions or duplicate IDs | Exhaustive disjoint membership, stable order and revision rejection |
| M4-CAP-P02 | Pure | No-data/stale/excluded becomes zero or Available | Distinct reasons, partial completeness, coverage counts |
| M4-CAP-P03 | Pure | Percentages/incompatible units/intervals or rollups sum | No numeric total; only proven additive compatible quantities sum |
| M4-CAP-P04 | Pure | Labels/unknown identity merge pools or known aliases count twice numerically | Proof-bound presentation grouping, all registry IDs retained, unknown suppressed |
| M4-CAP-P05 | Pure | Wrong health boundary/auth/unknown precedence | Exact 30/15 equality, exhausted/auth precedence and partial/worst known state |
| M4-CAP-P06 | Pure | Too few/short/gapped/flat observations yield estimate | Typed insufficiency with precise reasons |
| M4-CAP-P07 | Pure | Mixed segment/reset/correction/source/definition ignored | Segment compatibility, conflict and reset handling |
| M4-CAP-P08 | Pure | Exact linear samples lose arithmetic/lineage | Independent known-rate math, full input IDs and method, exact per-second quantity |
| M4-CAP-P09 | Pure | Rounded values produce false exact projection | Evidenced outward uncertainty bounds; unknown precision bounds stays insufficient |
| M4-CAP-P10 | Pure | Stale input/later reset/new generation leaves current forecast | Expiry/invalidation/reset relation and explicit recovery |
| M4-CAP-L01 | Real native Claude + M02 + file SQLite | Aggregate port absent/incorrect group coverage | Actual every organization/global/provider/account scope reconciles to real membership/windows, no invented totals |
| M4-CAP-L02 | Real committed data/file SQLite | Actual health remains unconfigured Unknown despite classifiable current windows | Persisted classifier inputs/policy/source refs match genuine window values |
| M4-CAP-L03 | Real accumulated native history/file SQLite/reopen | Forecast query/recompute absent, lineage lost after reopen | Actual insufficient/available union, exact lineage and method persistence; available branch Blocked if actual sufficient inputs absent |
| M4-CAP-L04 | Real M04 failed and healthy targets | Failure overwrites/freshens quota or blocks unrelated aggregate | Failed target explicit, healthy account queries continue; natural failure required |
| M4-CAP-H01 | Real authenticated HTTP | New fleet endpoint absent or scope/counts wrong | Actual responses conform to generated schema; unauthorized/invalid scope denied |
| M4-CAP-H02 | Real authenticated HTTP/history | Forecast/history no-value union absent or fake metric serialized | Actual UTC points/state/reasons/input IDs, bounded request and pagination |
| M4-CAP-B01 | Real built dashboard/shared browser | Organization inventory/actual history chart and explanation missing | Native per-account values chart/table match real API, missing/partial/no forecast clearly rendered at responsive widths |
| M4-CAP-D01 | Real file database + actual Alembic chain | Required new bounds/schema absent | Fresh+supported prior upgrade, integrity, history/receipts and recovery preserved |
| M4-CAP-E01 | Real outbox producer/consumer/reopen | CAP events/storage port absent or replay mutates facts | Durable ordered/idempotent M05 event path; M07 interruption leaves backlog and observations intact |

Constructed examples are allowed only in the zero-I/O P01..10 tests; clocks are
explicit input. No seeded/recorded provider data in any L/H/B/D/E test, fake
repository/clock, test-only provider path, machine clock change or backdated row.
Empty real schemas are valid for migration mechanics; telemetry assertions use
fresh genuine collection or an approved real AgentMonitor database. Missing real
selectors, receipts, observations or naturally unavailable conditions report
Blocked/Not Run, never a successful empty dataset. Mutate sufficiency,
compatibility, health and exact arithmetic branches; no surviving meaningful
mutant may be silently exempted.

Proposed exact implementation commands (not executed by this plan):

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/capacity/pure/test_aggregate_policy.py \
  backend/tests/capacity/pure/test_forecast_policy.py -vv
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/integration/capacity/test_claude_organization_aggregates.py \
  backend/tests/integration/capacity/test_claude_history.py -vv
python3 tools/automation/run.py AUTO-QUALITY
python3 tools/automation/run.py AUTO-DOCS-CHECK
```

Root must codify these into AUTO-TEST/full M4 routines with explicit selected
real resource prerequisites. Integration/browser/migration commands are finalized
in root's packet; this planning file does not invent a current runnable M4 gate.

## 10. Implementation sequence

1. Root synchronizes/approves this focused packet, shared types/defaults,
   metadata/evidence inputs, event/health ports, storage bounds and write sets.
2. Author and run pure membership/aggregation/forecast tests against current
   behavior. Record assertion Reds, not import/setup errors; use existing
   callable behavior or the approved test specification entry point to demonstrate
   missing capability before changing production.
3. Implement pure policies and wire current health; run Green and refactor.
4. Apply any assigned additive migrations to actual temporary prior/fresh files;
   extend M05 repository/public query/recompute/event ports; test actual native
   observations and reopen. Preserve immutable source/commit behavior.
5. Root integrates M02 revision/equality evidence, M04 ordered availability,
   M07 delivery and M08 leaf health. Run real fleet isolation/history scenarios.
6. Root exposes additive P01 endpoints, generates client, builds UI and verifies
   real organization/account/history/forecast browser behavior.
7. Run full canonical M4 completion catalog, independent bounded review, update
   sanitized evidence and handoff. Scope is incomplete until that full gate passes.

## 11. Documentation and handoff

Update M05 module guidance, contract register/adoption/ownership, policy method
and insufficiency explanations, API/generated artifact guidance, traceability,
M4 capacity evidence/live matrix, and migration/operations/runbook notes. Root
owns shared edits. Handoff records exact requirements/ACs, contracts/versions,
files, Red/Green/refactor commands/times, actual DB/HTTP/browser/provider evidence,
mutation result, migration/recovery/privacy/license impact and all remaining
Blocked/Not Run cases. No full M05, full M4 or V1 acceptance claim from this plan.

## 12. Dependency and license impact

No new dependency, manifest or lock change. Exact arithmetic/time policies use
the existing admitted standard library; persistence/API/UI use the approved
project stack. Existing SBOM/notices/security admission gates remain applicable.

## 13. Risks, unresolved decisions and stops

Root approval must settle the concrete policy defaults, public event/storage
types, revision-atomic metadata acquisition, opaque duplicate evidence input,
exact new wire grammar and migration representation for bounds/coverage.
Unknown resource relationships and Claude reset/precision evidence are
intentional no-value outcomes, not permission to infer. A real available forecast
or additive shared pool remains Blocked when no sufficient genuine data exists.

Stop the affected work for contract drift, shared-file conflict, foreign table
access, unapproved dependency, provider/version/parsing scope change, sensitive
content, destructive migration, owner auth/credits need, or attempted process/
profile mutation. Continue independent pure/read-only work while root resolves
that specific dependency. Risks R-001/002/005/006/007/008/009/010/011/014/020
retain their existing owners and require actual evidence, not plan assertions.

## 14. Delivery and rollback

Additive DTOs/new operations preserve old clients; optional current metadata has
unknown defaults. Persisted schema changes expand under the centrally allocated
chain and declared compatibility range. Before live exposure, migrations,
backup/recovery, actual events and generated-contract checks must pass. Preserve
historical observations and prior receipts. Roll back only through a verified
compatible binary/backup or forward fix; never use unverified downgrade.

## 15. Definition of ready and completion gate

- [ ] Root has reviewed and approved the exact focused plan and contracts.
- [ ] All shared types/defaults/import/write assignments are synchronized.
- [ ] Required actual M02/M04/event/operations ports exist or are allocated.
- [ ] Real source/identity/freshness/forecast limits are explicit.
- [ ] Meaningful Red inventory and real safe resources are allocated.
- [ ] Migration/recovery/privacy/license/doc/automation impact reviewed.
- [ ] Root canonical M4 gate accounts for all required scoped artifacts and
      separates every Blocked/Not Run live condition.

## 16. Approval record

| Reviewer | Decision | Conditions | Date |
|---|---|---|---|
| Root/integration | Approved I01 | Exact metadata/coverage/forecast DTO proposals and defaults above; no event delivery or new forecast persistence until separate synchronization | 2026-09-29 |
| Root/integration | Approved I02 | Exact bounded current alert fact/query protocols and native remaining-ratio or explicit published used-percent-complement derivation in §17 | 2026-09-29 |
| Root/integration | Approved I03 | Exact existing notice/read/ack protocols, actual historical receipt version and allocated nullable proof revision 0704 in §18 | 2026-09-29 |
| Root/integration | Approved I04 | §19 durable current forecast and independent capability availability first; v1_0707 candidate staged outside catalog, parent v1_0706; auth/collector ingest waits for published runtime seams | 2026-09-29 |
| M02/M04 | Pending | Revisioned eligibility/pool evidence and ordered availability | — |
| M07/M08 | Pending | Public events/processing receipts and leaf health | — |
| P01/P02 | Pending | Exact additive API/client/UI states and real browser proof | — |
| Persistence/security/test | Pending | Real migration/recovery, minimization and no fabricated telemetry | — |

Root reviewed the existing schema/current queries and this independent plan.
I01 authorizes meaningful test-first implementation of the exact DTO proposals,
pure health/coverage/aggregation/forecast policies, current optional metadata,
existing health projection wiring and read-only aggregate queries. Use existing
published M02 snapshot/account/resource contracts and a revision recheck; a race
returns unavailable rather than mixed membership. Empty equality/additive-pool
evidence means unknown. Current independent native-window inventories have no
numeric totals. Scope-specific monotonic events, forecast-bound persistence,
M02 equality descriptors, migrations, public HTTP/UI exposure and M08 leaf ports
remain subsequent synchronized increments. This preserves forward progress
without claiming an unwired event or unsupported forecast passed.

No service/browser/provider/default-profile action is assigned to the M05
implementation agent. Root retains operational and shared integration ownership.
The full original Draft module plan and milestone acceptance remain unchanged.

## 17. Approved I02: bounded current producer alert facts

Root approved this increment on 2026-09-29 under the owner's full M4 authority.
It adds the M05-owned `CTR-CAP-005` fact/query contracts from section 4 of the
approved M07 packet, using actual current projection provenance. M07 consumes
these facts through a public port. Root adapts durable commit notices to that
query and owns `CTR-EVT-001`; this increment adds no event reinterpretation.

```python
CapacityAlertConditionV1(
    resource_id: OpaqueIdV1, account_id: OpaqueIdV1, provider_key: str,
    window_id: OpaqueIdV1, generation: int,
    remaining_basis_points: CanonicalDecimalV1 | None,
    denominator_kind: Literal["remaining_ratio", "used_percent_complement", "unknown"],
    availability: Literal["current", "stale", "unknown", "unsupported", "unavailable"],
    exhausted: bool | None, reset_at: datetime | None,
    freshness_deadline: datetime | None, observation_ids: tuple[OpaqueIdV1, ...],
    precision: PrecisionV1, confidence: ConfidenceV1, reason_code: str,
    observed_at: datetime | None, recorded_at: datetime)
CapacityAlertConditionQueryV1(
    account_id: OpaqueIdV1, resource_id: OpaqueIdV1 | None,
    window_id: OpaqueIdV1 | None, as_of: datetime,
    limit: int = 50, after_key: str | None = None)
ListCapacityAlertConditionsV1(repository)(query) -> QueryPageV1[CapacityAlertConditionV1]
```

The source `generation` is the durable quota current projection's positive
`record_version`; target generation, run IDs and query times are never used.
`recorded_at` comes from the immutable observation's actual storage timestamp.
IDs are bounded, opaque observation references. Query bounds are 1..200 with an
opaque stable current-projection cursor and optional resource/window filters.

M05 derives basis points from a fresh, available, complete-scope native
`remaining_ratio` in [0,1], multiplying its exact canonical decimal by 10,000.
Root additionally approved the genuine supported Claude native percent-used
source on 2026-09-29: use the existing published allowance's
`100_minus_used_percent` derivation, then multiply the exact remaining percentage
by 100. Label its denominator `used_percent_complement`; its rounded, derived
precision/confidence and original observation remain explicit. This source is
never described as provider-reported remaining ratio. Other units are rejected.
Its original precision/confidence and observation IDs remain visible. Missing,
unsupported, conflicted, stale, partial or unavailable ratios produce explicit
no-value states, never zero or a recovery condition without current evidence.
Reason codes are closed: `capacity_ratio_current`, `capacity_reading_stale`,
`capacity_reading_conflicted`, `capacity_reading_partial`,
`capacity_freshness_unknown`, `capacity_ratio_unsupported`,
`capacity_ratio_unavailable`, `capacity_ratio_unknown` and
`capacity_used_percent_current`.

Tests first assert the absent bounded query against the genuine selected owner
database, then verify actual projection generations/provenance/freshness and
no-value truth after implementation. Constructed ratio arithmetic, stale and
partial cases run only in zero-I/O domain tests. No telemetry is seeded or
replayed. `ForecastAlertConditionV1` and
`CapacityAvailabilityAlertConditionV1` remain unimplemented until their actual
persisted producer state exists. No extra migration/dependency/privacy field is
added by I02. The full master-plan approval flags remain unchanged.

## 18. Approved I03: existing commit-notice delivery and exact acknowledgement

Root approved the exact signatures and migration allocation on 2026-09-29.
`CapacityCommittedNoticeV1(capability_id: str, projection_count: int,
state: Literal["succeeded", "partial"])` is the closed three-field payload of
the existing `capacity.committed.v1` event under `CTR-CAP-004`. It indicates a
commit only. It never activates or recovers an alert; the consumer reads I02's
current condition and its durable projection generation. The published quota
input contains 1..32 unique windows, and one projection per window guarantees
the same committed-notice projection-count bound.

`ReadCapacityEventsV1(repository)(consumer_key, after_cursor, as_of, limit=200)`
returns `DurableEventBatchV1[CapacityCommittedNoticeV1]` under `CTR-EVT-001`.
Its stable producer cursor is the actual unique `producer_sequence`; the
envelope retains actual event, correlation, causation and resource subject IDs,
stored UTC times, native stream key and sequence. Historical producer version
comes only from the matching actual M05 commit receipt's `consumer_version`,
joined via its persisted event references. Decode exactly schema major 1 and
the closed payload keys; unknown/malformed records fail closed. Hash the
canonical three-field JSON, preserving its original notice meaning.

`AcknowledgeCapacityEventV1(repository)(consumer_key, event_id, payload_digest,
receipt_id, as_of) -> None` checks the actual immutable event and exact digest,
then transactionally stores acknowledgement proof. An identical retry is
idempotent; a different receipt/digest conflicts without modifying the first
proof. M05 never inspects M07 tables. A committed consumer receipt is an internal
port precondition established by composition before acknowledgement; no bearer
API exposes this internal operation. Outbox rows and observations remain intact.

Root allocated exactly
`backend/migrations/versions/v1_0704_m05_event_delivery_proof.py`, parent
`v1_0703`, owned M05. It adds only nullable `ack_receipt_id` String(64) and
`ack_payload_digest` String(64) to `capacity_event_delivery`, with closed paired
opaque-ID/canonical-digest constraints. Legacy proof stays NULL and unknown,
with no backfill or silent rebinding of an old acknowledgement. The catalog,
schema validator and actual offline, verified-backup upgrade remain root-owned;
all prior revision bytes are immutable. No further dependency or schema change
is authorized by this packet.

Meaningful Red/Green covers absent genuine outbox read against selected actual
owner data, bounded stable replay and exact canonical lineage, plus pure closed
notice validation. A real acknowledgement/reopen/conflict test requires an
actual committed consumer receipt; no generated placeholder receipt or seeded
event substitutes for it. If that live input is absent, that specific boundary
remains Not Run while read and pure work continues. Consumer outage does not
block M05 commits or mutate capacity facts. Malformed event errors remain safe
codes without raw payload in logs, tests, evidence or API responses.

## 19. Approved I04 — durable forecast and independent availability streams

**Root approved this focused increment on 2026-09-29.** Start with persisted
forecast and capability-native availability. Auth/collector source ingestion
waits for actual normalized runtime ports and root composition. M05 remains the
sole semantic owner of `CTR-CAP-007/008/009`; root allocated a staged candidate
`v1_0707` with parent `v1_0706` and owns catalog/pin, composition and
M07/P01/P02 synchronization. No pinned revision `v1_0703` or `v1_0704`
changes. The full M05 master plan remains Draft.

### 19.1 Actual data and producer-source boundaries

`capacity_forecast_projection` and `capacity_derivation(_input)` exist but have
no active M4 producer. Forecast bounds were additively allocated in 0703. The
current I01 `ListCapacityForecastsV1` derives read-only explanations from
actual history; its pure result's `generation=1` is **not** a durable source
generation and cannot drive M07. The supported Claude quota source reports a
rounded native percent used; it has no trustworthy reset instant or documented
rounding interval. Native history therefore yields an explained
`insufficient_input` forecast, never a numeric exhaustion prediction.

`capacity_availability_signal` can store only
`reauthentication_required|unavailable|blocked|recovered`, and its unique
current key excludes `signal_kind`. It cannot safely store initial current
healthy/unknown/unsupported/stale truth or concurrent independent auth,
collector and capability streams. Changing its uniqueness or inserting
`recovered` as a fabricated initial healthy event is prohibited. I04 proposes
one new M05-owned current table and leaves old signal rows intact. The generic
`capacity.committed.v1` notice continues to mean only an actual commit.

Native capability availability is derived only when actual selected quota
observations prove a complete, fresh, identity-bound capability reading. An
available native percent-used value is positive availability evidence; the
remaining ratio may still be unavailable. Partial/unknown/stale/missing input
stays non-evaluable. No collection failure alone proves provider quota
unavailable or requests provider reauthentication. External auth/collector
states require the public, revisioned `CTR-REG-010`/`CTR-COL-007` normalized
current-condition and event ports. `CTR-COL-007` now publishes a condition DTO
and query protocols, but its repository implementation and composition are not
yet present; `CTR-REG-010` currently publishes a health-change DTO without a
corresponding current-condition query. Both runtime seams remain separate
synchronization before M05 consumes them. M05 never reads their tables,
credentials, raw errors or provider files. No unavailable or recovery signal
is constructed just to pass an alert test.

### 19.2 Exact contract proposal for producer/consumer review

Add `CurrentCapacityForecastV1(forecast: CapacityForecastV1,
source_window_projection_id: OpaqueIdV1, source_window_generation: int,
source_reset_at: datetime | None, source_observed_at: datetime | None,
recorded_at: datetime, freshness_deadline: datetime | None)` under
`CTR-CAP-007/008`. Its nested `forecast.generation` is the current persisted
forecast `record_version`, positive and monotonic per stable window/metric/method
key. `ListCurrentCapacityForecastsV1(CapacityForecastQueryV1) ->
QueryPageV1[CurrentCapacityForecastV1]` is a bounded read-only public protocol.
The existing exploratory I01 query remains labelled query-derived; a current
consumer never substitutes its synthetic generation. The current reader
requires a complete persisted snapshot; legacy rows without one are explicitly
unavailable until genuine recomputation, with no backfill.

Add `ForecastAlertConditionV1(resource_id, account_id, window_id, generation,
state, exhaustion_at: datetime | None, earliest_exhaustion_at: datetime | None,
latest_exhaustion_at: datetime | None, reset_at: datetime | None,
before_reset: bool | None, confidence, precision, observation_ids, reason_code,
observed_at: datetime | None, recorded_at: datetime,
freshness_deadline: datetime | None)` under `CTR-CAP-008`, plus
`ListForecastAlertConditionsV1(CapacityForecastQueryV1) -> QueryPageV1[...]`.
`exhaustion_at` is the **latest** bounded exhaustion estimate, never an
unlabelled midpoint. `before_reset=True` only if that latest bound precedes an
exact native reset instant; `False` only if the earliest bound is at/after it;
an interval crossing the reset or unknown reset yields `None`. Non-available
states carry no exhaustion value and cannot imply a recovery. Source
observations, bounds, method/policy version, uncertainty and digest remain
visible through the current forecast view.

Add `CapacityAvailabilityAlertConditionV1(resource_id, account_id, generation,
state, observation_ids, evaluated_at, reason_code, capability_id, signal_kind:
authentication|collector|capability, source_subject_id, source_record_id,
source_generation, source_contract_id, observed_at: datetime | None,
recorded_at: datetime, freshness_deadline: datetime | None,
recovery_of_generation: int | None)` under `CTR-CAP-009`. The `state` vocabulary
is exactly `available|unavailable|blocked|reauthentication_required|unknown|
unsupported|stale|withheld_or_denied`; one row is one source stream, not a
provider-wide merged verdict. Public `ListCapacityAvailabilityConditionsV1`
pages by account, optional resource/capability/kind and `as_of`, limit 1..200,
stable stream cursor. Its `generation` is the M05 current row `record_version`;
`source_generation` is the actual upstream durable version and is never a
collection target generation. Newer healthy/current evidence from the **same**
source stream may clear an actual prior failure and references that failure
generation. Unknown, stale, unsupported, missing or a healthy different stream
cannot clear it. M07 maps per-stream fingerprint/subject without collapsing
independent sources into one boolean.

Add small typed `CapacityForecastChangedV1` and
`CapacityAvailabilityChangedV1` cause payloads under `CTR-CAP-008/009`, both
inside CTR-EVT-001 envelopes. They contain subject/window or stream key,
previous/current state, durable generation, input/source version and digest,
safe reason, actual UTC times and at most the latest observation reference;
they carry no numeric quota, account identity, path or 200-point history.
Forecast transition is `active|invalidated|recovered|not_evaluable`. An
available-before-reset forecast is active; an evidenced later matching reset
or available-after-reset forecast can recover it. Insufficient/stale/conflicted
facts are not-evaluable and cannot recover by silence. Availability transition
has the analogous explicit `active|recovered|not_evaluable` semantics per
source stream and the matching prior bad generation.

Preserve existing `ReadCapacityEventsV1` committed-notice meaning. Add a
separate closed-union `ReadCapacityProjectionEventsV1` over commit, forecast and
availability payload types, with the same bounded producer-sequence cursor and
exact digest/receipt acknowledgement. The old committed-notice reader selects
only its own event type; it never decodes a new type as a commit. Root/M07 must
review the new typed dispatch path before activating the producer. New events
stamp the actual M05 producer version at write time. Legacy committed notices
continue to recover their historical version from their actual commit receipt;
the old `subject_version` meaning as collection target generation is preserved.

### 19.3 Pure policy and atomic persistence proposal

Select a bounded newest contiguous history suffix with the **same evidenced**
window definition, source compatibility ID and exact reset segment. A genuinely
changed reset/source/definition starts a new segment; older observations remain
immutable history but cannot contaminate the current rate. Unknown reset never
creates a segment ID. The approved three-sample, 900-second span/gap and
seven-day horizon, unit, monotonicity, freshness and rounded-bound policies
remain unchanged. No history produces an explicit no-value state grounded in
the current native projection, not an invented sample.

`RefreshCurrentCapacityProjectionsV1(as_of, after_key=None, limit=1..32)` scans
M05's own current quota projections; root schedules repeated bounded passes.
It prepares actual history/facts outside the short write lock, then in one
M05-owned `BEGIN IMMEDIATE` transaction checks the current window generation
**and** selected immutable observation-ID set. A changed source retries later
without a partial write. On an actual input/policy/freshness-state change, it
inserts immutable derivation/input references, advances the one current
forecast/availability row and appends the matching typed outbox event atomically.
An identical reread leaves generation, stored time and outbox unchanged.
Expiry uses actual `as_of >= stored freshness_deadline`: it writes a new stale
or not-evaluable generation and event once. A failed forecast refresh never
rolls back native observations or blocks M04 commits; retry reads real stored
facts. Consumers re-query the new current-condition port and compare durable
generation before acting. No generic event or clock alone changes truth.

Proposed **one new M05 migration, ordinal pending root allocation**:

| Table | Additive fields / constraint | Legacy rule |
|---|---|---|
| `capacity_forecast_projection` | Nullable `window_projection_id`, `source_projection_version`, and bounded closed `snapshot_json`; paired positive source version and exact generation/snapshot mapping | NULL remains unavailable until actual refresh; no guessed forecast or reset |
| `capacity_event_outbox` | Nullable `producer_version` stamped on new forecast/availability events; commit notices retain receipt lookup | Old NULL remains actual historical receipt lookup |
| New `capacity_availability_current` | Unique `(provider_key,account_id,resource_id,capability_id,signal_kind,source_subject_id)`; positive M05 record version/source generation; closed state, source contract/record/version, evidence IDs/digest, actual observed/recorded/evaluated/deadline UTC, active failure and recovery references | Empty on creation; old `capacity_availability_signal` rows remain intact and cannot be silently interpreted as current |

New forecast snapshots are allowlisted V1 typed fields only, size-bounded to
65,536 characters because a worst-case 200-observation lineage appears twice
in the existing forecast/burn DTO. No source payload is copied. The new
availability row is limited to safe IDs/codes/UTC, no free-form error. The
existing M05 outbox retains a small typed cause payload within its reviewed
4,096-character bound. Physical checks enforce paired NULL/value fields,
positive generations, closed states and valid digest shapes. Root checks actual
production Alembic chain, schema fingerprint/compatibility, verified backup,
recovery and portability before a real owner upgrade. No new package,
configuration secret or provider write is proposed.

### 19.4 Meaningful evidence and handoff conditions

Pure Reds: same-source generation/digest idempotency, reset-suffix selection,
expiry once, explicit healthy inverse only in matching newer stream, mismatch
and out-of-order rejection, partial/unknown non-recovery, and exact forecast
before/after/straddling reset bounds. Green uses only constructed zero-I/O
domain values. External Red/Green uses selected genuine owner quota history,
real file-backed SQLite and production migration/ports: absent durable current
forecast/availability/outbox first, then actual persisted no-value Claude
forecast, native fresh capability availability, repeat/reopen stability,
immutable history preservation and outbox-generation agreement. No telemetry
rows, provider responses, resets or source failures are seeded or replayed.

Root must separately provide/approve the missing `CTR-REG-010` current query,
the `CTR-COL-007` runtime adapter/composition, identity/scope mapping, M07
typed union dispatch and P01/P02 current views. A naturally observed available numeric forecast, explicit
provider/collector/auth unavailability and exact matching recovery remain
**Not Run / Blocked by source evidence** until real provider facts exist. A
passed pure example or known unavailable state does not count as that live
acceptance. Full M4 completion still requires its canonical gate over all
modules/API/built browser, migrations and actual service operation.
