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
- Historical inspection: `common_quantity_v1.py` used context-sensitive
  Decimal.scaleb in `as_decimal()`, rounding a valid 38-digit input. T004 corrected
  conversion at `6a87630`. Retain the regression and remaining exactness checks;
  this corrected defect is not new outstanding implementation work.
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
| CTR-CAP-004 2.1.0 | BudgetCollectionInputV1 and the typed report commit port | One bounded report, fenced binding/scope generation, atomic facts/coverage/receipt |
| CTR-COL-006 2.0.0 budget variants; CTR-COL-002 2.2.0 billing/cloud run variants | BudgetCollectionReceiptV1, typed commit port, BudgetCollectionRunViewV1 and profile-free admission | Real report reference permits zero facts; old quota receipt/run types unchanged |
| CTR-CAP-002/003/006 | GetBudgetV1, ListBudgetsV1, GetAccountApiCapacityV1, ListBudgetOverviewV1, ListBudgetHistoryV1, ListUsageBreakdownsV1 | Backend exact aggregation, immutable report selection, bounded stable cursors |
| CTR-CAP-007 budget variant | GetBudgetForecastV1 → BudgetForecastV1 | Pure bounded calculation with inputs/method/as-of or no-value reason; no DB writes |

Focused producer/consumer integration now consumes CTR-REG-014 1.5.0,
including BillingAccessTargetV1/BillingAccessPortV1 and monitoring proof/ports: M02 produces current nonsecret authority,
M04 captures it and root composition revalidates it at commit. Existing metadata
and local setup consumers stay compatible. These focused runtime versions extend
the historical whole-program Draft register; they do not mark that register
approved or replace existing published quota types.

Consume M02 revisioned scope/resource queries, M03 admitted provider output,
M04 generic commit envelope/generation fence, exact/common provenance and DB UoW.
Adapters cannot write M05 tables. Queries cannot collect. A successful access
check is not provider identity proof. Scope must be verified or explicitly owner
asserted; ambiguous overlap prevents invalid totals.

### T007 captured-interval handoff (12 November)

The approved selected-range behavior uses additive CTR-COL-002 2.3.0:
`BillingBudgetReportContextV1` captures exact 7/30 completed UTC-day bounds,
source category and at most one grouping; `BudgetCollectionRunAdmissionV2`
retains that context alongside the existing V1 authority; `BillingBudgetAuthorityV1`
is the durable target/context envelope. Existing V1 and cloud admissions keep
 their meanings. These types exist locally; they are not installed yet.

M04 stores the tagged envelope in its existing canonical target JSON, reconstructs
it on claim/recovery and filters latest runs by context before ordering/limit.
An omitted context preserves legacy query behavior; explicit context does not
invent coverage for old records. M05's run-state port consumes the additive
billing/cloud union. A01/A02 builders bind admitted interval/category/grouping
into request identity and validate it on reconstruction. Only admitted cost
requests are enabled by this increment; unsupported categories remain rejected.
Root owns typed contracts and composition integration. No migration, new queue,
credential access, account mutation or dependency is required. The first nine
pure contract cases passed; positive provider evidence remains separate.

## 5. Minimum data model and migration

Root allocates M05 `v1_0732` after M02 owner-setup `v1_0730`/`v1_0731`, which follow
accepted `v1_0720`; M04 `v1_0733` now supplies its captured billing
authority and run-to-report reference. Both financial revisions are committed
locally at `ad7a04e`; the later financial activation at `437a232` installed
`v1_0733`. Positive monetary integration remains unverified. Preserve all old
migration contents/digests.
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

T010 publishes additive CTR-CAP-006 2.8.0 history query/row/result/port types.
The query binds account, resource, immutable report, exact seven/thirty-day
period, read cutoff and page size (default 50, maximum 200). Facts sort by
period start/end, cost-or-usage kind and bucket key. Continuations bind the
immutable report body and selection; signed HTTP cursors also bind the caller
and expire under the existing cursor policy. Missing retained reports return
an explicit not-found response, never a substitute latest report.

P01 adds compact `GET /accounts/{account_id}/budgets` and paginated
`GET /budgets/{budget_id}/history`. Summary metadata carries genuine fact counts;
only history pages carry bucket bodies. Existing full-report endpoints remain
compatible. P02 consumes the summary for headings/totals and history for tables,
retains loaded pages on a failed continuation and resets on selection changes.
M05 reuses the existing bounded stored-report reader (10,000 facts/16 MiB);
no new storage schema, dependency, collection job or owner setup is needed.
Pure query/context/paging tests precede implementation; actual retained Ollama
reports verify SQLite/application/HTTP selection without manufactured telemetry.
Counts-only evidence is not monetary verification or retention acceptance.

GetBudgetForecastV1 queries bounded immutable facts and computes the documented
observed-rate method; no stored forecast generation or new event consumer.
Three complete compatible buckets over ≥24h, no unknown gaps or signed
adjustments, at most 200 buckets from seven complete days. Cost sum divided by
covered duration; not subtraction of independent buckets. Authoritative compatible
remaining/headroom is required for an as-of exhaustion estimate. Nonpositive remaining
returns the observed zero/exceeded state with no calculated date. A zero rate
means No consumption in the observed interval, with no exhaustion date. Missing
funds/limits prevent a date but not an otherwise qualified observed rate. Rate and exhaustion have separate availability. Matching funds/cost coverage and source/funds freshness must be established
before a date is returned. When multiple funding components share a spending
stream, individual depletion requires source-established allocation; recent retrieval alone is insufficient. The linked rules define
rounding, horizons and renewal handling.

The existing report-history repository lists revisions for an exact requested
interval. T010's installed CTR-CAP-006 2.8.0 supplies bounded daily-fact paging
from a
known immutable report; T013 reuses it for the chart. Remaining historical
scope discovery needs a bounded authorized metadata query over retained reports
(original scope epoch, interval, source, observation/collection times and report
ID), consumed by Source history. Reuse existing report-list machinery; version
the minimal additive query before implementation. Known-report paging alone
does not discover old scopes. Revision rows are provenance, not additive spend.
Latest M04 run
state is a separate query input: a failed run can have no M05 report. Current
selection must consider every compatible revision within its declared query
bounds, not only a first history page; overflow stays explicit unavailable.

Budget history/breakdowns are distinct from quota metrics; add ports, do not
extend old enums silently. P01 carries exact values/report IDs and stable
snapshot cursors; P02 charts/tables share those same values and gaps.

### First account application view (T010)

CTR-CAP-006 2.1.0 supplies repository-level current report selection. The local
additive CTR-CAP-006 2.2.0 account application view and first P01 GET now exist
in `contracts/budget_query_v1.py`; genuine monetary HTTP verification remains
Not Run. See [query evidence](../../../evidence/m7-account-financial-query-2026-11-11.md). Resolve M02 resource/scope authority, obtain
M05 selected reports, and compose M04 latest collection state through public
ports. M05 supplies exact reported-spend totals, their compatible groups,
coverage/exclusions and report inputs; P01/React do not sum raw report buckets.
Expose current complete report and latest persisted attempt separately from
collection status. No-run, failed status lookup and actual failed run remain
different states.

The existing aggregation policy accepts one selection per resource. Current
queries can return several categories, currencies and groupings. The application
must select an admitted total cost context per compatible group, then invoke
the policy separately for each group. Reject ambiguous overlaps; never sum a
total with its breakdown or choose the first returned context. Retain the
same selected report identity for detail, Overview and daily history. Extend
existing published types rather than add a parallel financial query framework.
Overview rows retain the currency/basis/category context in addition to resource
identity. Summary/list DTOs carry exact calculated values and report selectors;
they must not ship every report body/bucket for every account. Detail/history
remain bounded independently. Measure real returned size and query behavior
with available genuine data; do not invent financial records for a capacity claim.
For these additive financial routes, `budget_id` resolves to the existing
canonical billing resource, not a new table or a report revision. Current
output publishes selected report IDs per context. Daily-history input pins one
selected report plus authorized resource/scope/period; its cursor cannot switch
reports after a newer collection. Expired retained data requests a new selection
explicitly. Existing reserved budget types retain their original meaning.
An explicit action's terminal result advances the read `as_of` while preserving
its selected UTC reporting interval, replacing report/table and resetting the
cursor together. Read action progress through M04 separately. A mutable run that
completed after a historical cutoff is not evidence of success at that cutoff;
return only the status/time semantics actually supported, without building an
event-sourcing subsystem.
The additive HTTP/client operations are generated; full account/global/history
coverage remains unfinished. See the worksheet's concrete first-slice contract decisions.

### Funds handoff inside T010, before adding more financial screens

The local increment now implements additive CTR-CAP-006 2.3.0: an optional
account funds view, typed exact components and its public query port. M02 cloud
membership and M05 quota reads are composed by root; A03 maps only admitted
Ollama monetary windows. P01 publishes the compatible field through the existing
account endpoint; P02 renders it independently of billing reports. A03 and FND
are declared contract consumers. There is no migration, dependency, collection
request or owner configuration change. See the
[scoped evidence](../../../evidence/m7-stored-funds-2026-11-11.md) for actual
Red/Green and installation/browser status; T010/T011 remain open.

At `62b1b9f`, `GetAccountBudgetCurrentV1` enumerates only billing connections,
and CTR-CAP-006 2.2.0 carries reports/spend but no funds. Existing Ollama cloud
resources therefore need a read projection independent of those connections.
This is an additive contract change within T010, not a second billing registry.

1. Root publishes the next compatible CTR-CAP-006 surface before consumers
   change: exact amount/currency, component kind, optional limit/period/expiry,
   constraining semantics, field availability/reason, source observation/run
   identity and timestamps, scope compatibility and freshness. No guessed values.
2. Compose M02 `RegistryScopeSnapshotV2` cloud membership with M05's published
   quota-window query. A03 alone interprets the existing provider window names
   and maps admitted monetary components; legacy percentage windows are not money.
   Do not query another module's tables or match records by label/email.
3. Revalidate resource membership and scope generation on read. Unknown scope
   permits a labelled individual balance, but not inferred shared-pool totals,
   spend compatibility or forecast eligibility. Do not present an observation
   collected after the query snapshot as known then; current projection absence
   is not a historical zero. No new table or provider request is needed.
4. P01 maps the typed projection and regenerates its client. P02 can render
   funds when reports/connections are empty, with separate current-funds time
   and selected spending interval. Existing balances are not collected again
   merely to display them. Positive live verification uses the real stored
   observation → public query → actual HTTP → built DOM lineage.

T010's existing HTTP cases cover funds without spend, spend without funds,
non-constraining components, unavailable period and stale data. Pure cases cover
selection/compatibility; missing naturally occurring I/O combinations are
reported separately, never seeded into the database.

## 9. Test-first sequence

### Existing Ollama cloud authority for T009

The next integration uses additive CTR-COL-002 2.2.0
`CloudBudgetCollectionRunAdmissionV1` and `CloudBudgetReportContextV1`.
Existing CTR-REG-012 graph/service DTOs suffice: no new billing enrollment,
registry wrapper or secret store. The cloud profile/resource/binding are
captured intact. The original balance-service fingerprint remains distinct
from the usage-source fingerprint. Scope (self/team), native range (7d/30d)
and exact UTC completed-day interval are immutable request context, including
after recovery. Usage cannot produce balance-verification receipts.

The existing M04 budget target JSON gains a tagged cloud authority encoding;
old billing records retain their decoding. Dispatch/commit must revalidate
the live graph and binding through M02-owned fences, and usage must share
Ollama's existing request gate with balances. No second queue or rate limiter.
Publishing the contract/codec alone does not enable collection or close T009.

A resource-local scope epoch is not proof of upstream identity. Unresolved
reports must remain partitioned by their existing binding ID/generation;
rotating an unverified key cannot merge potentially different actors' spend.
Confirmed compatible scope preserves the existing cross-rotation history rule.
Both pure report compatibility and SQL context partitioning must agree. The
current read must select the active unresolved lineage; older lineages remain
retained history. The current query still lacks that selector at `445b947`:
root must publish an additive authorized active-binding input and opaque UI
context through CTR-CAP-006 before cloud spend is enabled. No absent/changed
active lineage may fall back to another actor's spend or funds as current.
The current implementation adds CTR-CAP-006 2.4.0: optional active-binding
selection and a separate existing-cloud-resource projection in the account
query. Older billing resources and funds remain compatible. Runtime composition
supplies actual binding/graph reads; the API omits credential identifiers.
The first self-usage read is verified against a genuine retained report;
installed browser verification and full M7 acceptance remain separate evidence.
M04 selected-context status must also match source/self-team/range/interval;
account-wide credential failure remains independent. T010 carries existing
backend exact percentage/low-state decisions with lineage/rounding or a missing
denominator reason. P02 does not calculate money or expose credential IDs. Shared totals and forecasts cannot infer scope equivalence.

CTR-CAP-006 2.5.0 adds the compact Overview query and explicit retained-report
selection. P01 exposes `GET /api/v1/budgets` and `GET /api/v1/budgets/{budget_id}`;
the latter requires account, report, exact period and read instant, returns the
selected report with backend-calculated spend, and never substitutes latest
data for a missing selection. Existing account/current DTOs remain compatible.
Overview drains bounded registry pages, fences metadata changes, projects
existing billing/cloud resources and exact component percentages, and signs
context-bound cursors. Independent cloud resources are not subscription pools.
Until T002 publishes canonical pool attribution, totals explicitly exclude
unresolved resources; this increment cannot close FR-ORG-003. Funds projection
also proves the current binding generation against the committed M04 run.
These changes reuse schema `v1_0733`; no migration or new dependency is needed.

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

T004 completion covers exact money, grouping/availability and report selection,
not the later rate/horizon cases owned by T013. Use scoped executable checks for
each ticket; the full technical/live gate includes downstream work and cannot
be a prerequisite for completing its own inputs. T003 owns publication of the
remaining selector invocations before dependent ticket closure. Scope epochs,
rolling UTC-range alignment and subtotal exclusions follow the calculation
document; setup and installed-service proof follow the execution checkpoints.

Use the [delivery worksheet](../../integration/m7-delivery-worksheet-2026-11-11.md)
for early setup activation and the observed documented-beta/API-only/paged-run
contract gaps. T014 begins with the tested setup increment before real owner key
entry; its full dashboard closure follows the stored-report/API/UI work. A
complete provider ticket is not a prerequisite for starting first-report storage
with its verified monetary increment. No placeholder data crosses that boundary.

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

T013 explicitly owns this financial-retention handoff: M05 implements the
report/fact retention participant and reference-preservation policy; root wires
it through M08's existing scheduling contract. T015 reuses the T014 continuity
check to verify installed invocation after T013; the first installation does
not wait for that later work. T005 supplies the real persisted report used by the isolated SQLite
test. Pass an explicit future cutoff to that isolated test without changing the
machine clock, manufacturing old telemetry or touching the owner's database.
Verify current/derivation references survive, eligible unreferenced report facts
expire together, and expired cursors cannot return a different report. Add these
assertions to the existing persistence check, with pure cutoff/mutation coverage.
This covers only M7-owned storage; M8-wide retention/backup work stays M8.

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


### Canonical pool metadata increment

CTR-REG-014 1.5.0 adds a bounded revisioned financial-pool snapshot, owner
association/attribution commands and configuration/page views in the existing
`registry_billing_v1.py` contract. M02 produces, M05/P01/P02/root consume; existing
1.4.0 billing/access/monitoring types retain their meaning. Source scope and
credential lineage are internal authority, never browser-supplied proof. M02
validates create/join/unlink and primary-group changes atomically, preserving
superseded associations. Known scopes survive key rotation; unresolved scopes
require the exact active binding and generation. An owner association is not
provider-verified identity or billing access.

Root allocates additive M02 `v1_0734` after installed0733 for pool and association
metadata, with no telemetry backfill or owner configuration migration. The real
catalog/compatibility and isolated upgrade/recovery checks must cover this new
head before installation. No dependency or secret-custody change. T002/T004/T010/
T012/T014 retain their existing requirement and acceptance mappings; the
[implementation evidence](../../../evidence/m7-financial-pools-2026-11-12.md)
records actual tests and remaining integration.


### Shared-pool Overview projection (CTR-CAP-006 2.6.0)

Additive optional row metadata exposes canonical pool, primary group, owner
association evidence and all connected access paths. Compact report/funds links
carry their actual authorized account/resource IDs. M05 resolves the full
provider inventory through one CTR-REG-0141.5 snapshot before organization
filtering, then selects compatible pool evidence and computes exact subtotals.
Primary-only selection may use a secondary path; secondary-only rows disclose
where the pool is counted without adding it to that subtotal or calling it
missing. No source identity or coverage is inferred from labels/equal values.
P01 serializes these fields; P02 renders source-owned links and attribution.
Existing2.5 rows remain readable with no-pool defaults. T004/T010/T012 own pure
selection, actual HTTP/metadata and built-browser evidence respectively.


## 12 November: full-inventory Overview sorting (T010/T012)

Compatible CTR-CAP-006 Overview query/types advance from2.6.0 to2.7.0:
optional `sort_by` account/organization/state (default state), and
`sort_direction` ascending/descending (default ascending). Response shape and
existing detail/history contracts remain unchanged. Root owns shared contract,
API/generated client and composition; M05 sorts before pagination, P02 renders
server order. Organization names come through the existing CTR-REG-001
OrganizationViewV1 callable composed from GetOrganizationV1, never a table read.
Primary-pool organization and canonical pool label determine visible sort keys.
Stable ascending ID ties remain stable when primary direction reverses.
Cursor identity includes query order and revision-consistent resolved group
labels; concurrent metadata edits require a fresh stored-data query.

Red: nine pure cases initially failed because the query lacked sort fields.
Real metadata HTTP tests and built isolated browser cover page-boundary winners,
both directions, cursor mismatch, navigation and selected filters. No fabricated
provider telemetry. No new dependency, migration, secret handling, owner-account
mutation or production provider call. Genuine monetary acceptance remains open.

The existing CTR-FND-005 generator's operation equality check rejected this
compatible optional-query addition. Root's bounded correction permits new
optional query parameters only while preserving every old parameter, response
and security field. Required additions, duplicates, removals, changed existing
parameters and non-query additions remain rejected. Generator2.0.10; no new tool
or dependency. Pure schema Red/Green and real production generation verify it.
