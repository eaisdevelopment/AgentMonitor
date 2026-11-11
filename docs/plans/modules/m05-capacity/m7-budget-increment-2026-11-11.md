# M05 capacity: focused M7 budget increment

- Status: Approved focused increment under execution plan 1.1.0; implementation in progress.
- Plan version: 0.3.0; synchronized with focused M7 execution plan 1.1.0.
- Owner: M05; shared contracts/migration catalog/composition writer: root.
- Parent: [M05 0.2.0-draft](plan-v1.md), not approved wholesale.
- Requirements: FR-BUDGET-001..006, FR-ORG-003, FR-HIST-001/002,
  FR-COL-004/008, NFR-DATA-001, NFR-ARCH-001/002, NFR-PRIV-001/002.
- Acceptance: AC-LIVE-004/005/007, AC-HIST-001, AC-UI-002/005/006,
  AC-TEST-001..006; P01/P02 own actual HTTP/browser evidence.
- Authority: [execution plan](../../integration/m7-execution-plan-2026-11-11.md).
- Financial semantics: [calculation rules](../../integration/m7-calculation-and-data-rules.md).
- UI consumer: [journeys](../../integration/m7-ui-and-user-journeys.md).

## 1. Outcome and boundaries

Persist genuine billing reports and serve exact spend, supported budget fields,
shared-pool-aware summaries, history/breakdowns and a small explainable forecast.
M05 owns financial meaning and facts. Providers own retrieval/mapping; M02 owns
resource/account/credential metadata; M04 owns jobs and commit recovery. No M05
provider calls, credentials, private cross-module tables or UI calculations.

Do not build new alert policies, a forecast event stream, persistent forecast
state, parent/child collection jobs, general analytics engine or FX accounting.
Existing quota/history/event consumers remain compatible. No local Ollama work.

## 2. Actual source inventory and hazards

- `capacity_v1.py` has a four-field reserved BudgetViewV1; preserve it and add
  BudgetViewV2 with existing CapacitySubjectV2 tagged cloud identity.
- `common_quantity_v1.py` supports exact coefficient/scale and currency, but
  `as_decimal()` uses context-sensitive Decimal.scaleb. A pure probe rounds a
  valid 38-digit value at default precision. T004 must correct this shared leaf
  primitive and exact aggregation before the budget implementation uses it.
- Existing quota commit/query/forecast ports are quota typed. Do not disguise
  budget money as quota units or manufacture an installation/window ID.
- Frozen `v1_0500` provides budget and usage tables; `v1_0501` receipts/current
  projections; `v1_0502..0504` event/forecast/retention foundations. Presence of
  those tables is not evidence of a working budget repository.
- Existing budget measures disallow negative amounts. Cost corrections need
  additive signed storage; never alter old checks or clamp adjustments.
- `CollectionCommitReceiptV1` requires nonempty observation/projection/event IDs.
  Successful `CollectionRunViewV1` also requires observations. A genuine empty
  report needs a versioned budget result, not fabricated facts or events.
- The collection HTTP wire uses an ordinary tuple of observation IDs, without a
  nonempty constraint. Internal V2 run/query adoption can retain the existing
  JSON fields, state vocabulary and empty-array wire compatibility; verify that
  with actual HTTP/generated-client tests rather than broadening old domain DTOs.
- Current M04 execution is one admit → collect → normalize → commit → finalize,
  with one active run per schedule. Reuse it. Page-level child jobs would be new
  scheduler machinery and are deferred unless real report size proves need.

## 3. Ownership and exact write areas

M05: `backend/src/agentmonitor/modules/capacity/{domain,application,ports}`,
`backend/src/agentmonitor/adapters/persistence/capacity/sqlite`, capacity tests
and module documentation. Root writes `contracts/capacity_v1.py`, exact shared
quantity primitive, `collection_control_v1.py` additions, migration catalog,
composition and generated artifacts. M02/M04 receive their own isolated writers.

Domain imports standard-library and published value contracts only. Application
uses ports; SQLite stays in its adapter. No provider SDK/framework/OS imports in
financial domain. No new package or license change.

## 4. Published and consumed contracts

| Contract | Additive proposed surface | Main invariants |
|---|---|---|
| CTR-COMMON-003 | Same public exact representation; context-independent conversion implementation correction | No float; same 78-digit/18-scale range; reject arithmetic overflow |
| CTR-CAP-002 2.0.0 | BudgetViewV2, ExactMoneyFieldV1, typed budget/cost/usage inputs, report coverage/context | Availability, currency, cost basis, period and source watermark stay distinct |
| CTR-CAP-004 | BudgetCollectionInputV1 and CommitBudgetCollectionOutcomeV1 | One bounded report, fenced binding/scope generation, atomic facts/coverage/receipt |
| CTR-COL-006 2.0.0 budget variants | BudgetCollectionReceiptV1 and BudgetCollectionRunViewV1; V2 query adoption | Real report reference permits zero facts; optional empty projections/events; old quota types unchanged |
| CTR-CAP-002/003/006 | GetBudgetV1, ListBudgetsV1, GetAccountApiCapacityV1, ListBudgetOverviewV1, ListBudgetHistoryV1, ListUsageBreakdownsV1 | Backend exact aggregation, immutable report selection, bounded stable cursors |
| CTR-CAP-007 budget variant | GetBudgetForecastV1 → BudgetForecastV1 | Pure bounded calculation with inputs/method/as-of or no-value reason; no DB writes |

Consume M02 revisioned scope/resource queries, M03 admitted provider output,
M04 generic commit envelope/generation fence, exact/common provenance and DB UoW.
Adapters cannot write M05 tables. Queries cannot collect. A successful access
check is not provider identity proof. Scope must be verified or explicitly owner
asserted; ambiguous overlap prevents invalid totals.

## 5. Minimum data model and migration

Root allocates M05 `v1_0731` after M02 owner-setup `v1_0730`, which follows
current `v1_0720`; M04 `v1_0732` follows only if needed. Preserve all old migration contents/digests.
Use existing budget/usage/provenance facts and receipt keys where semantics fit.
Add only:

1. A durable report record: source/endpoint/category, account/resource/target,
   binding generation, report grouping, requested/covered interval, cost basis,
   source snapshot/watermark, collected time, completeness/omissions, and digest.
2. Links from report to its actual budget/cost/usage facts; a complete empty
   report has no invented fact links. Add missing context as columns where that
   is sufficient, rather than automatic one-to-one companion-table proliferation.
3. Signed exact cost measures linked to genuine observations, with dimensions
   and source revision semantics. Old budget balance/limit checks remain intact.
4. Minimal receipt/query compatibility storage required by M04 empty reports.
   Do not add forecast tables or page-checkpoint/parent-run tables.

Index account/resource + source interval/collection order and supported dimension
queries. Explicit constraints preserve canonical money, UTC interval ordering,
FK ownership and state/value pairs. Test real query plans after real data exists.
No provider telemetry is backfilled, seeded, copied from documentation or altered.

## 6. Financial and temporal invariants

The linked calculation document is normative. Most important: spend is a flow;
balance is a snapshot; soft-budget headroom is not cash; a valid hard-limit
headroom can be exceeded; provider credits are not automatically applied twice.

The newest complete compatible report replaces prior current coverage, including
buckets that disappear. Preserve old reports as history. Repeated polls, parent
rollups and their breakdowns are never summed together. Partial reports do not
replace the last complete total or its source freshness. A genuine empty complete
report retains coverage and may support a labeled derived zero only when source
semantics justify it. Unknown watermark/permission is never zero usage.

Reporting ranges are not inferred billing periods. Group totals only across
compatible period/currency/cost basis, count shared pools once, and show missing
coverage. Backend derives totals over the complete filtered resource inventory,
not a browser page. Refuse oversized aggregate selections explicitly.

## 7. Idempotency, concurrency and recovery

One run collects one bounded report and commits once. Transaction covers report,
facts, current selection, applicable provenance/receipt, and only actually needed
notices. Same run/generation/schema/digest returns the prior receipt. Conflict
preserves the first commit. Key rotation/scope change/archive invalidate stale
in-flight generation through the published fence, not private-table access.

A restart before commit recollects. During committing, M04 asks get_commit_status.
No fabricated success from timeout. Failed/partial calls leave prior complete
current data visibly unchanged/stale. Source snapshot consistency is checked
across pages when the provider supplies a watermark. One provenance envelope
must not pretend several endpoint/category/time snapshots are identical.

## 8. Forecast and history design

GetBudgetForecastV1 queries bounded immutable facts and computes the documented
observed-rate method; no stored forecast generation or new event consumer.
Three complete compatible buckets over ≥24h, no unknown gaps or signed
adjustments, at most 200 buckets from seven complete days. Cost sum divided by
covered duration; not subtraction of independent buckets. Authoritative compatible
remaining/headroom is required for an as-of exhaustion estimate. Nonpositive remaining
returns the observed zero/exceeded state with no calculated date. Rate zero,
missing limits, unsupported scope or delayed/incompatible data yield precise
no-value states. The linked rules define rounding, horizons and renewal handling.

Budget history/breakdowns are distinct from quota metrics; add ports, do not
extend old enums silently. P01 carries exact values/report IDs and stable
snapshot cursors; P02 charts/tables share those same values and gaps.

## 9. Test-first sequence

| Scenario | Expected Red | Green evidence |
|---|---|---|
| M7-CAP-PURE-001; M7-MATH-01/02/13/14 | Valid large decimal loses digits; cents/rounding/state rules absent | Pure exact conversion, cancellation, bounds, small positive display inputs; no I/O |
| M7-CAP-PURE-002; M7-MATH-04..12 | Duplicate/shared/mixed totals or empty/unknown conflation | Pure report-selection, scope, signed adjustment and availability policies |
| M7-CAP-DB-001 | Fresh real migration lacks report/signed-cost structures | Fresh/upgrade/FK/integrity and empty read checks; no seeded telemetry |
| M7-CAP-DB-002 | Fresh real adapter result cannot commit/query/reopen | Production M05 port, actual SQLite, same receipt on retry, safe conflict/recovery |
| M7-CAP-DB-004 | Later complete/empty report leaves phantom prior spend | Genuine provider revision when available; pure selection proof always, unobserved live revision explicit |
| M7-EMPTY-001 | Real successful no-usage report cannot finalize without invented observations | V2 receipt/run plus unchanged compatible HTTP wire, genuine zero-fact coverage |
| M7-HTTP-001..006 | Real budget endpoints missing or money/coverage corrupted | IAM, pagination, generated schemas, report history and backend filtered totals |
| M7-UI-001..006 | Real table/detail absent or misleading | Actual API-to-DOM precision, unavailable states, filters, charts and accessibility |
| M7-CAP-PURE-004; M7-MATH-03/15/16 | Wrong bucket rate or invented exhaustion | Exact rate/as-of policy with reasons and seven-day bound |
| M7-CAP-LIVE-001/002 | Configured supported lane has no reconciled report | Real source comparison/failure isolation/recovery; unavailable natural cases remain explicit |
| M7-CAP-MUT-001 | Exactness, selection or forecast mutant survives | Existing mutation runner extended to critical budget policies; no new framework |

Missing credentials are Blocked, not behavioral Red. Pure vectors stay pure.
Database/API/browser assertions use real migrated storage and fresh actual
provider facts; retries of the same in-memory normalized commit test idempotency,
not provider-response playback. No empty response is fabricated for acceptance.

## 10. Implementation order

T004 corrects exact primitives and financial policies; T002 prepares owner setup;
one real provider adapter feeds T005 storage; T007 integrates scheduling/empty
receipt recovery; T010/T011/T012 expose current spend and exact history on the
actual dashboard. Other provider adapters then reuse it. T013 adds breakdown
query/UI, chart and query-time forecast. The first visible slice does not await
forecast, alert events or all providers.

## 11. Security and configuration

Only the approved focused M7 runtime exception authorizes transient local
credential use. M05 sees no keys, token derivatives, prompts, raw payloads or
arbitrary environments. Safe key identifiers are independent provider IDs or
internal opaque references, never key prefixes/suffixes/hashes. Allowlisted
project/model metadata and owner labels retain separate provenance.

Collection resource limits/default cadence are in the calculation document;
freeze their config/version manifest during T003/T007, measure the first real
report and admit exact provider rate limits. No new generic tuning UI is needed.

## 12. Operations and retention

365-day retained genuine history, with bounded purge of unreferenced facts and
report context. Reuse M08 retention/backup participants; preserve current facts
and links. Installed rollout needs a compatible binary and verified backup.
No old migration rewrites or post-write blind restore. T014 owns actual deployed
rollback; isolated SQLite tests do not claim full M8 backup/restore delivery.

## 13. Documentation and handoff

Update contracts/adoption, exact financial module docs, provider capability
matrix, API/generated client, configuration/runbook, traceability and sanitized
Red/Green/live evidence per increment. Parent frozen whole-module plan remains
Draft; focused approval does not approve unrelated future features.

## 14. Dependencies and bounded risks

No new dependency. The installed admitted toolchain and Codex legacy test binary
are already verified in the planning checkpoint. Known risks: admin access,
source delay/limits, minimum report exceeding bounds, unknown shared scope,
empty receipt compatibility and exact overflow. Each is a named ticket/test;
none is an excuse to invent data, change accounts or halt independent work.

## 15. Readiness

Planning checks and bounded review passed at `a914248`. The owner then directed
full M7 implementation. Root publishes exact contract types before parallel
writers, with one migration/contract/composition writer. Product live tests are
not implied by planning evidence.

## 16. Approval record

See [implementation authority](../../../evidence/m7-implementation-authority-2026-11-11.md).
It applies to this focused 0.3.0 increment and execution plan 1.1.0, not the
unrelated whole-module Draft parent. Routine internal fixes do not require
repeated owner approval.
