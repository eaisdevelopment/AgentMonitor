# M05 capacity: M7 budget increment

- Status: **Draft — focused planning for contract synchronization; no implementation approval**
- Plan version: 0.2.0
- Date: 2026-11-11
- Inspection baseline: `f7a1799`, isolated `m7-api-budgets` worktree
- Owner: M05 capacity planning agent; integration steward assigns implementation
- Parent: [M05 plan 0.2.0-draft](plan-v1.md)
- Execution context: [V1-M7 Stories ST-BUDGET-001..005](../../../superpowers/plans/2026-09-19-agentmonitor-v1-m7-api-budgets.md)
- Requirements: FR-BUDGET-001..006; supporting FR-HIST-001/002, FR-QUOTA-004/005, FR-COL-004/008, NFR-DATA-001, NFR-ARCH-001/002, NFR-PRIV-001/002
- Acceptance contributions: AC-LIVE-004/005/007, AC-HIST-001, AC-TEST-001..006; P01/P02 own HTTP/browser contributions
- Reviewers: root, M02/M03/M04, A01/A02/A03, P01/P02, M07/M08, persistence, security, test integrity
- Approval: pending; no provider, account, profile, credential, service, or operator-data access performed

Root synchronization, 2026-11-11: this revision fixes the budget-specific
forecast policy, additive signed cost storage, and M04 chunk/manifest protocol
below. These are concrete changes within pre-approval planning, not additional
owner approval requests or implementation authority.

## 1. Outcome and boundaries

Persist and expose genuine API billing usage, cost, budget, credit and supported
breakdowns separately from subscription allowances. Each displayed value must
retain its currency/unit, billing and coverage interval, exact source lineage,
availability, precision and freshness. Forecasts must identify their input facts
and uncertainty or explain why no number is justified.

M05 owns the normalized input and read contracts, arithmetic, resource-pool
separation, observations, current selection, derived budget forecasts, owned
repositories, and `capacity_*` schema. A01/A02/A03 own official provider access
and field mapping; M03 owns admission/capability evidence; M04 owns scheduling,
leases, cooldown and durable run outcomes; M02 owns account/resource/target and
credential-binding identity. P01 owns authenticated REST and generated artifacts;
P02 consumes only that API. M07 owns alert policy/lifecycle. M08 owns operational
backup, export and retention orchestration.

This planning write set contains only this file. Future M05 implementation paths,
subject to root allocation, are:

```text
backend/src/agentmonitor/modules/capacity/domain/budgets.py
backend/src/agentmonitor/modules/capacity/domain/budget_forecast.py
backend/src/agentmonitor/modules/capacity/application/budgets.py
backend/src/agentmonitor/modules/capacity/ports/budgets.py
backend/src/agentmonitor/adapters/persistence/capacity/sqlite/budgets.py
backend/tests/capacity/test_budget_values.py
backend/tests/capacity/pure/test_budget_forecast.py
backend/tests/capacity/pure/test_budget_commit_policy.py
backend/tests/integration/capacity/test_budget_schema.py
backend/tests/integration/capacity/test_budget_repository_live.py
backend/tests/integration/capacity/test_budget_history_live.py
docs/modules/capacity.md
docs/test-evidence/capacity/v1-m7-api-budget-handoff.md
```

The contracts file, migration revision/catalog, composition, event consumers,
automation, API and UI require separate single-writer allocation. Domain code
uses standard library and versioned value contracts only. Applications use
published ports; persistence imports the admitted database stack. No M05 code
calls providers, reads credentials/profiles, reaches another module's tables,
imports backend transport into domain, or computes money in the browser.

## 2. Actual implementation inventory

These are source observations, not executed behavioral/live verification.

| Existing artifact | Usable behavior or structure | Missing budget behavior |
|---|---|---|
| `contracts/common_quantity_v1.py` | `CanonicalDecimalV1` uses coefficient/scale, maximum 18 fractional digits and 78 coefficient digits; `ExactMoneyV1` couples that with a three-letter uppercase currency; exact quantity/ratio primitives already exist | Money-field availability wrapper and budget validation. `ExactMoneyV1` itself permits signed decimal values; frozen budget measures prohibit negative values, so do not assume signed financial corrections fit storage |
| `contracts/capacity_v1.py` | `ExactMetricFieldV1`, provenance view, V1 installation subjects and V2 discriminated cloud/installation subjects | `BudgetViewV1` is only `budget_id`, `subject: CapacitySubjectV1`, `state`, `observed_at`. No money, period, spend, limits, credit, dimensions, input DTO, budget query, or budget forecast |
| `modules/capacity/application/ingest.py`, `commit.py` | V1 quota preparation validates provenance and canonical payload digest; M04 generic commit/receipt seam is available | Preparation accepts only `ProviderQuotaInputV1`; commit facade is quota typed. Do not pass a budget disguised as quota or broaden old signatures silently |
| `modules/capacity/domain/payload_digest.py` | Canonical quota V1/V2 digest, sorted windows, complete exact fields | No budget/cost/usage digest or dimensional identity |
| `adapters/persistence/capacity/sqlite/repository.py` | Real quota commit, idempotent receipt/status, cloud target handling, optional credential fence, bounded quota/current/history reads, durable outbox | No budget/usage writes or queries. Presence of budget tables is not a working repository |
| `modules/capacity/application/queries.py` | Typed quota/aggregate/history APIs and quota forecast derivation | No four budget queries named in the M7 Story plan. Existing history metrics are exactly `used`, `remaining`, `limit`, `remaining_ratio`; budget metrics must not be smuggled into that enum |
| `modules/capacity/domain/forecast.py` | Pure bounded secant, explicit `as_of`, compatible suffix, minimum samples/span, freshness, gap, source/definition/reset segmentation, outward uncertainty bounds | Samples/results require `CapacitySubjectV1`, quota window IDs and quota metrics; application `_window_forecast` explicitly returns no result for `QuotaWindowViewV2`. Monetary currency and billing revisions need their own contract |
| `adapters/persistence/capacity/sqlite/current_repository.py`, `forecast_snapshot.py` | Durable quota forecast generation and snapshots, availability projections, event delivery | Current forecast query joins quota observations/window definitions and snapshot encodes installation identity. It cannot truthfully represent an API cloud budget |
| `api/v1/routers/capacity.py`, `schemas/capacity.py` | Quota, aggregate, history and forecast transport | No budget routes/schema. Root must synchronize P01 rather than expose repository internals |

The accepted M6 Ollama cloud quota/balance path remains a regression boundary.
This plan does not claim those values are API monetary spend or that its key
authorizes additional billing operations. Subscription/API pool distinctions
apply even where the provider name or real account is the same.

## 3. Immutable storage inventory and proposed expansion

| Revision | Existing M05 schema | M7 use and limits |
|---|---|---|
| `v1_0500_m05_capacity_observations.py` | `capacity_budget_definition`, `capacity_budget_observation`, `capacity_budget_measure`; `capacity_usage_bucket`, `capacity_usage_dimension`, `capacity_usage_measure`; shared provenance and resource policy | Reuse these tables. Budget measures allow `current_spend`, `available_spend`, `prepaid_credit`, `soft_limit`, `hard_limit`, exact decimal or minor units and currency. Usage dimensions cover organization/account/project/workspace/API-key-safe/model/token-category/time bucket; measures cover input/output/cache tokens, requests, quantity. Usage has no money measure; budget observations have project/workspace but no arbitrary dimension set or explicit cost coverage start |
| `v1_0501_m05_capacity_receipts.py` | Receipt plus receipt-observation links (`quota`, `budget`, `usage`); current projection supports budget definition and `projection_kind='budget'` | Reuse atomic receipts and budget projection branch. Do not issue separate quota/budget commits for the same `(collection_run_id, capability_id)` key |
| `v1_0502_m05_capacity_health.py` | Health projection, availability signal, event outbox and delivery | Reuse durable envelope/sequence concepts; current implementations and decoder are not automatically budget-capable. Do not publish a new event to an old closed decoder |
| `v1_0503_m05_capacity_forecasts.py` | Derivations/input lineage support budget observations and usage buckets; forecast projection has nullable quota-definition FK, exact burn columns | Reuse lineage. Existing V1 forecast readers and later snapshot constraints remain quota-specific |
| `v1_0504_m05_capacity_retention.py` | Retention audit counts quota/budget/usage and export indexes | Reuse audit/index structures; this is not an implemented budget purge/export/restore service |
| `v1_0703`, `v1_0704`, `v1_0707`, `v1_0710`, `v1_0715` | Constraint metadata, event proof, durable quota forecast metadata/triggers, source period, discriminated cloud target | Preserve these. `v1_0715` updates quota definition/current projection targets, not budget definitions or resource-policy installation requirements |
| `v1_0720_m04_uncertain_outcome.py` | M04 `collection_cloud_uncertain_outcome`, parent `v1_0719` | Occupied current head; never reuse/edit it for M7 |

The Story plan's instruction to use frozen M05 tables is correct for core facts;
it does not make missing cloud/period/cost metadata representable. The following
is a proposed focused amendment, requiring synchronization, not authority to
allocate or write a revision. Preserve every existing revision and digest. The
persistence steward centrally allocates proposed M05 revision `v1_0730` after
`v1_0720` and any intervening synchronized M7 revisions. Its final `down_revision`
must match the single integrated head; no branch or competing historical revision.

Proposed additive companion tables:

- `capacity_budget_definition_context`: one-to-one definition FK; capability,
  discriminated provider target, billing semantic/version, approved resource
  relationship and policy reference. This avoids inventing an installation ID
  for a cloud source or populating legacy `capacity_resource_policy` with one.
- `capacity_budget_observation_context`: one-to-one observation FK; source
  coverage start/end and precision/state, renewal timestamp/precision/state,
  registry/source generation, omission codes, fact role (`budget_snapshot` or
  `cost_bucket`), source bucket identity/revision and completeness. Original
  observed/collected/stored fields stay in their existing table.
- `capacity_budget_dimension`: observation FK plus dimension kind, field state,
  safe typed value, mapping version; bounded closed dimension vocabulary as for
  usage. Explicit cost-bucket role and coverage interval prevent interpretation
  as account-to-date spend. Each cost bucket references a real compatible resource/definition;
  creating a provider budget/limit is never required or implied.
- `capacity_cost_measure`: observation FK to the existing
  `capacity_budget_observation`, metric kind, availability, exact signed decimal
  coefficient/scale and currency, precision/confidence/value-kind, reason code
  and optional derivation ID. Use this companion for provider cost buckets and
  signed adjustments; preserve the nonnegative `capacity_budget_measure`
  semantics for budget spend/availability, credits and limits. Store signed
  amounts without clamping or changing immutable migration checks. Enforce
  canonical signed decimal text, reject negative zero, and couple all monetary
  values to currency and availability. Context identifies bucket revision and
  whether a source fact is a replacement or a distinct adjustment, so the same
  correction is never both substituted and added.
- `capacity_budget_forecast_current`: budget projection/definition IDs,
  source projection generation, forecast generation, method/version, input digest,
  derivation FK, currency, freshness, safe versioned snapshot and state. Keep
  quota snapshots and their existing trigger/decoder grammar unchanged.

Add indexes for `(account_id, resource_id, observed_at, observation_id)` on budget
history if query-plan measurement requires it, and dimension-filter plus coverage
bucket access. Existing budget definition-time, run and export indexes are
retained. Final DDL must constrain one-to-one links, dimensions, state/value
pairs, currency, canonical exactness and UTC interval ordering. SQL checks do not
replace domain validation. No provider facts are backfilled, no signed adjustment
is silently clamped to zero, and no existing observation is rewritten. Signed
cost storage is part of proposed `v1_0730`, not a deferred schema decision.

The expand migration runs offline under existing locks with a verified private
backup, single-head checks, FK and full integrity checks. Test a fresh database
and upgrade from an actual prior-schema artifact/owner-authorized isolated backup;
never insert invented telemetry into a prior schema. Existing fact counts,
digests and source links must survive. Recovery preserves the failed file and
uses a verified backup plus compatible binary, or a reviewed forward fix.

## 4. Requirements and scenario mapping

| Requirement/AC | Planned M05 behavior | Proposed contract | Scenarios below |
|---|---|---|---|
| FR-BUDGET-001 | One genuine supported billing lane per configured account; explicit unavailable coverage | CTR-CAP-002/004 | M7-CAP-DB-002, M7-CAP-LIVE-001 |
| FR-BUDGET-002 | Distinct spend/available/credit/soft/hard fields, billing/renewal and explained forecast | CTR-CAP-002/007 | M7-CAP-PURE-001/004, M7-CAP-DB-003 |
| FR-BUDGET-003 | Safe supported dimension sets and bounded time-bucket history; no invented breakdown | CTR-CAP-002/006 | M7-CAP-PURE-002, M7-CAP-DB-004 |
| FR-BUDGET-004 | Exact money through mapping, SQLite, query, wire and browser | CTR-COMMON-003, CTR-CAP-002 | M7-CAP-PURE-001, M7-CAP-DB-002, M7-CAP-STACK-001 |
| FR-BUDGET-005 | Distinct resource pools and nonoverlapping aggregation | CTR-CAP-002/003 | M7-CAP-PURE-002, M7-CAP-DB-004 |
| FR-BUDGET-006 | Admit only evidenced provider/role/source capability; retain unsupported/denied/unknown separately | CTR-PROV-002/004/008, CTR-CAP-002 | M7-CAP-LIVE-001/002 |
| AC-LIVE-004/005/007 | Adapter matrix, authoritative reconciliation, genuine failures/recovery | Provider and collection contracts | M7-CAP-LIVE-001/002 |
| AC-HIST-001 | Genuine collection → immutable history → API → chart/table | CTR-CAP-006, P01/P02 | M7-CAP-DB-004, M7-CAP-STACK-001 |
| AC-TEST-001/002/003/004/006 | Behavioral TDD, real boundaries, sanitized evidence, no hidden blocked cases | All above | All scenarios |
| AC-TEST-005 | Kill exactness, compatibility, source-selection and forecast mutants | CTR-CAP-002/007 | M7-CAP-MUT-001 |

These focused IDs supplement the parent M05-PURE-043..058 and M05 database/live
families; root must map them into the active M7 completeness catalog. Their
presence is not test execution or a replacement for a canonical gate.

## 5. Proposed contracts and compatibility

Publish in `backend/src/agentmonitor/contracts/capacity_v1.py`, with explicit
versions despite the existing package filename. Keep existing V1 quota and the
reserved `BudgetViewV1` unchanged.

| Surface | Concrete proposal | Consumers/impact |
|---|---|---|
| CTR-CAP-002 | New `ExactMoneyFieldV1`, `ProviderUsageInputV1`, `ProviderCostInputV1`, `ProviderBudgetInputV1`, typed billing interval/dimensions and complete/partial page coverage; rich `BudgetViewV2` at `2.0.0` using `CapacitySubjectV2` | A01/A02/A03 produce normalized inputs; M04 carries them; P01 reads results. New view is parallel to V1; never reinterpret its installation field |
| CTR-CAP-004 | New `BudgetCollectionInputV1` batch containing independently typed budget/cost/usage collections, `BudgetCommitRequestV1` using the existing generic M04 commit envelope; new `CommitBudgetCollectionOutcomeV1` port; reuse `CapacityCommitReceiptV1` and status shape | Separate additive port preserves old quota signatures and receipt identity semantics. Root must amend the Story's quota-only commit facade instruction; M04 routing selects the sink by admitted schema |
| CTR-CAP-002/006 | `GetBudgetV1`, `ListBudgetsV1`, `ListUsageBreakdownsV1`, `GetAccountApiCapacityV1` as new ports returning V2 budget views; additive `ListBudgetHistoryV1` for chart/history use | Explicit queries contain subject/scope, optional resource/definition, dimension/time filters, UTC `as_of`, limit 1–200 and continuation. New read ports perform no provider call |
| CTR-CAP-007 | New `BudgetForecastSampleV1`, `BudgetForecastV1`, `GetBudgetForecastV1` with budget definition/period and currency, no quota window/installation fiction | Additive types/port, retain `CapacityForecastV1`. Version new monetary method `budget-observed-rate-v1/1.0.0`; do not relabel existing quota method |
| CTR-CAP-003 | Budget account/scope coverage inside `GetAccountApiCapacityV1`, separate compatible-currency/period groups with omitted reasons and M02 revision | Never extend a quota total to include money or change V1 health semantics |
| CTR-CAP-008/009, CTR-EVT-001 | Retain quota event grammars. Budget commit can emit the existing committed notice only where consumer routing safely recognizes its capability; new typed budget change events require explicit consumer synchronization | M07 must not receive new JSON payloads through the existing closed quota forecast decoder. Alert lifecycle changes are owned separately |

`ExactMoneyFieldV1` couples `ExactMoneyV1 | None` with the existing field
availability states, precision/confidence/value-kind and a safe reason code.
Available/stale values carry currency; unavailable fields contain no amount.
Overall query availability separately represents unavailable/reauthentication
state. Billing/renewal and safe dimensions use explicit state/precision; absence
never proves Unsupported. A money field rejects floats before conversion.

Input batches contain bounded typed records, scope/target, registry revision,
schema/meaning versions, complete/partial status and omission codes. Proposed
module limits: maximum 200 records per durable chunk and eight dimension kinds per
record, selected to match bounded pages rather than promise a provider page size.
M04 creates admitted child runs with unique receipt keys for those chunks and
owns a parent collection manifest recording expected and completed pages. Parent
scope becomes complete only after every page succeeds and source pagination is
closed. Partial child facts remain explicitly partial until that completion is
established through the published M04 seam; M05 never queries M04 tables. An
unknown expected page count cannot imply completion. Retries preserve each child
run's receipt identity; no silent truncation or second payload under the same
run/capability key. A genuine empty successful result is
distinct from an unavailable source and creates no synthetic zero observations.

New query outcomes distinguish found, not found, invalid selector/cursor,
unsupported, unavailable and partial coverage. Cursors bind filters/scope/as-of
and an upper stored-time bound; use stable time plus opaque-ID ordering. Owner
identity and safe resource IDs come from M02; M05 does not infer organization
membership from source names or API-key prefixes.

Consumed contracts: CTR-COMMON-003 exact money unchanged; M03
`CollectionOutcomeV1`/provenance and admitted capabilities; M04 generic
`CollectionOutcomeCommitV1`, receipt/status and run fences; M02
`ProviderTargetRefV1`, revisioned V2 scope/resource views; database V1 handles and
transactions; existing event envelopes. Exact producer schemas, credentials,
limits and collector admission still require cross-module agreement.

API route additions can stay under `/api/v1` while generated response types
identify their own shape versions. Existing response types remain unchanged.
No major replacement is proposed; additive parallel contracts need synchronization
and adoption records. Any later removal, enum reinterpretation, signed-value
reinterpretation, or change of event delivery semantics requires the ADR and
migration process in the contracts standard.

## 6. Domain and transaction invariants

1. Canonical decimal plus currency end to end; signed cost facts use the additive
   cost-measure companion, while legacy budget measures remain nonnegative.
   Never float, currency conversion,
   inferred currency exponent, price-list spend estimate or cross-currency total.
2. Current spend, available spend, credit, soft limit and hard limit are distinct
   facts. A provider-supported hard-cap relation may derive available spend only
   with matched scope/currency/period and explicit method/input IDs. Do not
   subtract an arbitrary soft limit, combine credits with a limit, or turn absent
   limits into unlimited/zero.
3. Resource semantic, account, target, billing definition, period, dimensional
   grouping and source compatibility form the aggregation identity. Parent
   rollup and child breakdown are alternate views, never additive together.
   Unsupported dimensions produce availability metadata, not invented rows.
4. Billing start/end, coverage start/end, observation, collection, storage and
   renewal are distinct UTC times. End is exclusive; unknown precision remains
   unknown. A cost bucket is not an invoice or an enforced account cap.
5. Canonical digest includes every accepted monetary/usage field, dimensions,
   period, source identity/version, omissions and completeness. Record ordering
   is canonical; duplicate semantic keys are rejected before I/O. The adapter
   supplies a safe source-bucket revision/identity only when evidenced.
6. One transaction inserts provenance, observations/measures/dimensions,
   context, current projection, derivation/outbox and receipt. Same run,
   capability, generation, schema and digest returns the original receipt with
   no new fact/event. Mismatch is a typed integrity conflict preserving the first
   commit. The authenticated binding/run fence is checked in the commit unit of
   work through the agreed seam, never by M05 querying registry/collection tables.
7. Failed/denied/unsupported runs do not create facts or freshen old values.
   Late observations remain history; source coverage/revision and observation
   chronology decide current selection, not arrival order alone. Equal semantic
   time with conflicting facts is conflicted. Rebilling/corrected buckets stay
   immutable with explicit supersession/selection; repeated polls are not summed.
8. Forecast only within one compatible budget/currency/period, scope and source
   semantics. Require at least three complete, nonoverlapping provider cost
   buckets spanning at least 24 hours, at most 200 samples and a seven-day
   projection horizon. Gaps are bounded by the declared source cadence and may
   not exceed two expected bucket widths; missing cadence/width evidence yields
   insufficient input. Repeated collection of the same buckets never increases
   the sample count. Only derive exhaustion with authoritative remaining capacity
   or an authoritative compatible limit plus evidenced compatible spend, and
   fresh compatible data. Billing source freshness follows its declared latency,
   rather than quota polling defaults. Sparse, partial, overlapping, stale or
   unresolved revised data yields a precise no-value result. Signed corrections
   remain stored and reconciled, but a nonpositive or otherwise unjustified
   consumption rate cannot produce exhaustion. Compute the exact sum of eligible
   complete bucket costs divided by the sum of their covered durations. Do not
   subtract independent bucket amounts as if they were cumulative counters.
   Gaps are disclosed and excluded from covered duration; forecast assumes the
   observed covered-period rate continues. Report minimum/maximum per-bucket
   rates as observed variability bounds, not statistical confidence. Any signed
   adjustment in the selected sample invalidates the exhaustion estimate until
   a compatible correction-free segment exists. Never inherit quota 900-second
   policy. Equal positive daily buckets must yield a positive rate, with exact
   lineage and explicit seven-day projection cap.
9. Outward forecast bounds and uncertainty disclose assumed future consumption.
   A reset/renewal comparison is only available when that timestamp and precision
   justify it. New generation/invalidation retains exact input lineage; a query
   does not silently persist or synthesize source facts.
10. Retention uses the 365-day policy with explicit time, bounded deletion and
    genuine source facts. Keep current facts and derivation inputs needed by
    retained projections, plus dependent provenance/context until references
    permit removal. No cascade may erase unrelated registry/alert state.

## 7. Test-first sequence

All rows are **Not Run** for this draft. No Red, Green or live pass is claimed.
Absence of an import, executable, credentials or fixture setup is not meaningful
Red: write tests against the approved callable seam with explicit assertions,
and record the missing/incorrect behavior once the test is runnable. Pure
constructed inputs never leave the no-I/O test. Persistence telemetry must come
directly from a fresh production adapter run or an explicitly authorized genuine
database backup, never constructed/replayed provider responses.

| Order/test ID and path | Expected behavioral Red | Green and refactor proof |
|---|---|---|
| 1. M7-CAP-PURE-001 `backend/tests/capacity/test_budget_values.py` | Budget field cannot represent exact fractional currency with independent unknown credit/limit/renewal; signed cost correction is rejected/clamped or incorrectly treated as negative credit; invalid floats/currency mismatch/overflow accepted | Exact signed cost arithmetic and state-pair boundaries; preserve nonnegative budget/credit semantics; no inferred balance or float conversion; zero differs from missing |
| 2. M7-CAP-PURE-002 same file | Aggregation double-counts parent/child or conflates subscription/API, periods, currency, dimension identity or revised buckets | Reject incompatible groups, preserve genuine zero and explicit omissions; no total for unknown overlap |
| 3. M7-CAP-PURE-003 `pure/test_budget_commit_policy.py` | Equivalent reordered inputs yield different digest, changed dimension/coverage omitted from digest, duplicate key or stale selection accepted; incomplete page manifest incorrectly implies complete scope | Every semantic input binds digest; generation/schema/digest conflicts, equal-time contradiction, late source rules, 200-record chunk boundary and all-pages-success completeness tested purely |
| 4. M7-CAP-DB-001 `integration/capacity/test_budget_schema.py` | Real freshly migrated SQLite lacks approved signed cost/context/forecast tables and query paths; immutable migration digest or cloud target shape differs | Full real chain, fresh/upgrade/integrity/FK checks, signed cost DDL and preserved old nonnegative measure checks; no invented business rows. Empty budget reads return explicit absence and zero rows. Explain bounded query plans |
| 5. M7-CAP-DB-002 `integration/capacity/test_budget_repository_live.py` | Fresh real Anthropic outcome cannot produce retrievable budget/cost/usage facts and exact receipt, duplicate commit changes counts, or parent scope becomes complete before all pages succeed | Fresh admitted adapter output through the production M05 commit port → actual file SQLite; full M03/M04 scheduling and parent manifest completion is verified in M7-T007; repeat the same in-memory commit request for retry semantics (not a provider replay), reopen, exact money/provenance/target/receipt preserved. Actual concurrent retry must create one receipt per child key; real multipage input preserves manifest/partial semantics. Signed adjustment round-trip requires a genuine source adjustment, otherwise that scenario is Blocked |
| 6. M7-CAP-PURE-004 `pure/test_budget_forecast.py` | Monetary forecast absent or uses mixed scope/currency/period, fabricated reset, repeated refreshes as samples, partial/overlapping buckets, missing cadence or unjustified remaining capacity | At least three complete compatible buckets spanning 24 hours give exact bounded rate/interval with authoritative remaining/limit, fresh data, inputs, method and uncertainty; test equal positive daily buckets produce positive burn, signed corrections invalidate exhaustion, cadence-gap boundary at two expected bucket widths, 200-sample/seven-day caps, signed correction reconciliation and every no-value state |
| 7. M7-CAP-DB-003 live repository/history tests | Genuine budget history does not yield durable explainable forecast/no-value state or changes generation on identical refresh | Genuine compatible history, no-value reason when insufficient, exact lineage and reopen; naturally adequate history required for numeric live forecast |
| 8. M7-CAP-DB-004 `integration/capacity/test_budget_history_live.py` | Current/bucket history repeats revised totals, ignores filters, changes cursor meaning, loses dimensions or refreshes old facts after source failure | Real history/current revisions, complete paginated retrieval, supported dimensions, source interval and pool separation; actual failure/recovery only when available |
| 9. M7-CAP-STACK-001 P01/P02-owned live vertical | Running authenticated HTTP/build lacks budget/history response or coerces money to float; chart/table disagrees with stored genuine facts | Real service, generated client, built browser, exact display and chart/table lineage; IAM scopes, foreign-account selectors and error availability tested through actual HTTP |
| 10. M7-CAP-LIVE-001 integration-owned matrix | Configured supported billing account has no reconciled current result | Anthropic/OpenAI/supported Ollama per-account source/role/version matrix; authoritative owner comparison records currency, period, time, precision and allowed lag |
| 11. M7-CAP-LIVE-002 integration-owned matrix | Naturally observed denial/unavailable/exhausted/recovery is conflated or old money becomes current | Real state observed without exhausting credits/revoking keys/manufacturing provider failure; unavailable cases Blocked individually |
| 12. M7-CAP-MUT-001 root-owned automation | Critical exactness/scope/current-selection/forecast mutants survive | Extend canonical mutation surface; zero non-equivalent survivors, independently justified exact equivalences only |

Minimum production increments follow those rows: publish contracts and pure value
policy; migrate owned additive context and empty reads; implement one genuine
Anthropic commit/query vertical; add other admitted lanes without modifying
quota behavior; implement monetary forecast plus durable lineage; finish history
and P01/P02 verticals; run full matrix/regressions. M05 may proceed with pure work
after plan/contract approval while an independent live prerequisite is being
prepared; a live row stays Blocked and cannot close its Story.

Conflict cases needing constructed values are tested purely. Database failure or
recovery tests use isolated real resources and genuine collected facts, not
altered provider payloads or injected fake repositories. Migration schema tests
may inspect real DDL and empty queries without claiming observed provider data.

## 8. Real prerequisites and privacy

Before each live lane, root supplies an approved real account/resource/target
selector, exact credential role, documented source and admitted schema,
bounded read operation, source field meanings, currency/period precision,
pagination/coverage semantics, collection request budget and comparison method.
The owner performs any credential/login step. The M6 Ollama managed-secret
exception does not authorize handling new Anthropic/OpenAI credentials without
the appropriate approved provider plan. M05 only receives opaque references and
typed facts; no credential values enter it.

Safe API-key identifiers must be provider-exposed identifiers proven independent
of credentials, or approved opaque internal references; no key prefix, suffix,
hash of a secret, reversible credential representation, or arbitrary label.
Project/model names are allowlisted metadata with source-specific privacy review;
no prompts, responses, source content, environments or raw payloads are read or
stored. Evidence uses opaque aliases, versions, time and closed reason codes.

No external state is modified by this plan. Future read-only source calls obey
M04 cadence and provider limits. No telemetry is generated solely to populate a
forecast or dashboard. Missing role/credits/account/history/failure condition is
reported Blocked, never replaced by another account or invented source fact.

## 9. Configuration, operations and recovery

No new dependency or secret/configuration key is proposed. Forecast policy is a
versioned explicit value object; query/commit limits above are contract bounds.
Provider freshness/role/cadence remain adapter/M04 responsibilities. Any later
runtime setting must enter the configuration registry with validation and reload
semantics before use.

Expose safe budget schema/query availability and source age through existing
health seams, without logging amounts, identities or raw data. Schema mismatch
fails closed; old source facts remain visible with stale/unknown status.

`AUTO-MIGRATE` currently supports an explicit set of source revisions through
`v1_0720`; it does not authorize a future budget revision. PLAN-DB must extend
the executable migration/backup/recovery path and its real tests before any
dependent deployment. `AUTO-BACKUP` and `AUTO-RESTORE` are currently blocked in
the automation catalog; M7 may not claim product backup/restore readiness from
an isolated migration backup. Required M7 recovery routines must be codified
under the approved focused operational scope; full M8 operations stay separate.

Deployment order: synchronized DTOs/consumers → reviewed additive migration and
schema compatibility → M05 and provider/collection composition → generated
API/client → UI → selected service activation and genuine reconciliation. Keep
old quota contracts working throughout. Previous binaries may refuse a newer
schema; rollback uses the verified pre-upgrade backup and prior binary, not
untested downgrade DDL or deletion of new observations.

## 10. Automation, documentation and evidence gates

Existing canonical commands to use within their actual authority/scope:

```text
python3 tools/automation/run.py AUTO-DOCS-CHECK
python3 tools/automation/run.py AUTO-PLAN-CHECK
python3 tools/automation/run.py AUTO-TEST
python3 tools/automation/run.py AUTO-QUALITY
python3 tools/automation/run.py AUTO-MUTATION
python3 tools/automation/run.py AUTO-MIGRATE
```

The first two validate documentation and the synchronized planning baseline;
they do not approve production work. `AUTO-MUTATION` currently covers M3/M5
policies, not these new budget policies. No `AUTO-M7-EXIT` is registered at the
inspection baseline. Root must implement/register the M7 gate and exact scenario
catalog, update the mutation selection and define any budget test selection
before claiming their lifecycle phase ready. This document deliberately does
not present a proposed runner as an existing executable command.

Direct pytest commands in the approved implementation packet must name the test
paths in section 7, run before and after production changes, and retain actual
timestamp/revision/exit status. Per-test success is narrower than a milestone
gate. The final gate must bind one real candidate revision, supported account
inventory, source versions, provider matrix, data-to-history-to-browser lineage,
schema/quality/mutation/regression lanes and every Blocked/Not Run result.

Required documentation updates after synchronization, owned by root/assigned
writers: module documentation, M7 execution-plan corrections, contract register
and adoption manifest, database migration catalog/compatibility, traceability and
scenario catalog, API/OpenAPI/generated client, provider capability matrices,
operations migration/recovery and troubleshooting, safe-key privacy policy,
sanitized TDD/live handoff. This planning agent edits none of those shared files.

## 11. Risks, decisions and approval needs

| ID | Risk or concrete decision | Disposition/owner |
|---|---|---|
| M7-CAP-D01 | Story assumes budget-ready V1 commit/query types; baseline only has quota and reserved view | Root/M04/P01/A01–A03 review additive batch/commit/query contract proposal before implementation |
| M7-CAP-D02 | Cloud target, cost dimensions/coverage and budget forecast cannot use existing quota snapshot encoding | Root/PLAN-DB review companion-table expansion at proposed centrally allocated `v1_0730`; preserve frozen `v1_0500..0504` and occupied `v1_0720` |
| M7-CAP-D03 | Provider returns signed correction, unknown period, unsupported dimension or no budget | Root-synchronized decision: signed cost companion in `v1_0730`, preserving nonnegative legacy measures. Source mapping still establishes adjustment/replacement meaning; explicitly unavailable/unknown fields remain truthful |
| M7-CAP-D04 | Repeated/overlapping/corrected source buckets double-count or incomplete pages appear complete | Root-synchronized decision: at most 200 records per M04 child run, unique receipt keys, parent expected/completed-page manifest and all-pages-success scope completion; M05 preserves partial facts and source revision identity |
| M7-CAP-D05 | M7 gate/mutation/migration automation lacks this scope | Root implements canonical routines before dependent readiness; absence is an engineering task, not a request for repeated owner permission |
| M7-CAP-D06 | Numeric forecast cannot be reconciled from available billing history | Root-synchronized policy: at least three complete nonoverlapping buckets over 24 hours, declared-cadence gaps bounded by two bucket widths, at most 200 samples/seven-day horizon and authoritative remaining/limit. M05 returns precise no-value reason if ineligible; live numeric scenario remains Blocked without genuine sufficient history |
| M7-CAP-D07 | Old event consumers assume quota-only payloads | Root/M07 coordinate typed event/routing addition; no change to old closed decoder grammar without version review |

Project risks R-005/007/008/009/010/011/014/018/019/020/024 apply. No new package,
license, credential access, provider mechanism or profile mutation is authorized.
Use the admitted standard library/database stack; any dependency addition returns
through admission rather than being hidden in this plan.

Implementation approval is required by `AGENTS.md` Start here item 4 and SDLC
Definition of Ready, because this focused M7 module plan and proposed contract
changes are not approved yet. Detached historical M0 reviewers are advisory per
the M7 plan; do not turn them into additional owner approval gates. Actual
technical provider evidence and real account prerequisites still apply.

Stop affected work for unexpected provider semantics, unrepresentable financial
values, cross-module/private-table requirements, overlapping write ownership,
new secret handling, unapproved dependency, destructive migration or a live
operation needing new owner authority. Continue independent authorized work.

## 12. Readiness and handoff status

- [x] Existing source contracts, repositories and immutable schema inspected.
- [x] M05 ownership, proposed isolated paths, data gaps and test order documented.
- [x] Root-synchronized billing forecast, signed cost storage and child-run/page-manifest decisions incorporated; no additional owner approval requested for this draft revision.
- [ ] Root synchronizes provider/M02/M04/P01/P02 input, output and migration proposals.
- [ ] Approved focused plan and contract adoption recorded; source capability facts evidenced.
- [ ] Canonical planning/M7 automation covers the integrated scope.
- [ ] Real accounts, source-role authorization and reconciliation procedure available.
- [ ] Behavioral Red, Green, refactor, migration, provider, HTTP and browser evidence executed.

This is an intermediate planning artifact. All implementation/live scenarios are
Not Run. It changes no production behavior, migration, shared contract or external
state. Integration next step: compare sections 3 and 5 with the other M7 module
plans, settle those concrete contracts and revision allocation, then present the
combined reviewable plan for the required implementation approval.
