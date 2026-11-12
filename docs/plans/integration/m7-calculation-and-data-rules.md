# M7 calculation and data rules

- Status: Approved as part of focused execution plan 1.1.0; implementation in progress.
- Owner: M05; provider field interpretation A01/A02/A03; collection M04.
- Requirements: FR-BUDGET-001..006, FR-ORG-003; AC-UI-005/006,
  AC-HIST-001, AC-LIVE-005, AC-TEST-001/005.
- This is the calculation contract. Numerical examples below are pure-domain
  test vectors, not telemetry, fixtures, accounts or dashboard examples.

## 1. Different financial concepts stay different

| Field | Rule |
|---|---|
| Reported spend | Sum disjoint authoritative cost facts in one explicit `[start,end)` reporting interval, scope, currency and cost basis. Never price tokens locally to claim actual spend |
| Available balance | Latest authoritative snapshot of that pool; never sum snapshots or infer its original funding from current spend |
| Prepaid credits | Separate provider-reported balance and expiry/period when supplied. A negative cost adjustment is not automatically a prepaid deposit |
| Soft budget | A warning threshold, not available cash or an enforced stop. `soft_limit − matching spend` may be shown only as headroom to that soft budget |
| Hard limit | `hard_limit − matching spend` is valid headroom only if scope, period, currency, cost basis and enforcement semantics are established. Negative result is Exceeded by, not a negative cash balance |
| Remaining percentage | `100 × remaining / matching positive limit`, with observed/derived provenance. No denominator or zero limit means no percentage. A value outside 0–100 is retained and explained; only the visual bar is clipped |
| Renewal/reset | Provider-reported time only. Calendar filter boundaries are not inferred renewal or invoice dates |

If authoritative balance and derived limit headroom both exist, present them
separately. Do not select the more reassuring one or add them together. Do not
subtract credits from costs unless that exact cost basis requires it; discounts,
list costs, post-credit costs and tax/invoice totals are different measures.
The current integrated sources may not expose all these fields; that is an
explicit availability result. Local budget editing, FX conversion, invoice/tax
reconciliation and price-list estimation are outside M7.

Fund components retain their own scope, observation time and constraining
classification. In the existing Ollama contract, included and purchased credits
are non-constraining components: one being empty does not prove the account is
exhausted. Keep them separate; do not assume spending order, add overlapping
components or derive account severity from their minimum. Unknown companion
funds means unknown account capacity. M7-MATH-07/08 and T004/T010/T012 cover
component low/zero labels versus a justified account-level depletion state.

## 2. Exact representation and display

Use existing coefficient/scale plus ISO currency, never float, SQL REAL/SUM of
decimal text, `parseFloat` or `Number` for financial arithmetic. Decode JSON
numbers directly to Decimal; convert documented cents to currency units by exact
base-10 scaling in the provider adapter. Preserve source precision separately.

The initial inspection found that `CanonicalDecimalV1.as_decimal()` used
context-sensitive `scaleb`, rounding a permitted 38-digit coefficient under the
default 28-digit context. T004 corrected conversion at `6a87630`; retain its
regression evidence rather than treating that defect as still unimplemented.
Use context-independent decimal construction
and scaled-integer addition/subtraction. Keep the existing 78-digit coefficient /
18-scale public bounds; reject overflow explicitly, never silently round facts.

Threshold decisions use exact inputs before formatting or clipping. For the
20% low-remaining threshold, compare scaled numerator/denominator directly;
20.004% is not low and 19.996% is low even when both display 20.00%. T010 publishes the existing
backend-calculated percentage text, exact low flag, input lineage and declared
rounding, or a specific missing-denominator reason; P02 renders them without
reimplementing division/thresholds. Component warnings alone do not establish
account exhaustion. This extends
M7-MATH-14 and T004/T012 acceptance without changing money representation.

Financial totals remain exact. Division used for rate/ratio is derived:
retain exact numerator/denominator and input IDs; format a bounded decimal only
with declared precision/rounding. Display ordinary USD totals to two decimals
using half-even rounding, and positive sub-cent values as `<0.01 USD` with the
exact source amount available in details. Negative sub-cent adjustments get an
explicit negative label. Never display unqualified zero for nonzero money.
For currencies without an admitted display-minor-unit rule, display exact
decimal + currency code rather than guess the exponent. Exact presentation-only
formatting of API amounts (including existing BigInt half-even rounding) is allowed in P02. It never changes the source amount or
computes spend totals, headroom, ratios, severity or forecasts. Matching display
vectors cover half-even ties, signed/sub-cent amounts and large coefficients.
Formatting is not cross-currency conversion. Rounded rows can differ from the
rounded total; the total is computed from exact inputs and carries an explanation.

Usage counts remain separate from money. Token/request categories are additive
only when the adapter establishes they are disjoint; a total plus its cached or
other included subcategory must not be counted twice. Preserve exact integers
beyond JavaScript's safe-integer range through API formatting. Do not infer a
price, credit value or monetary subtotal from counts. These are T004/T010
precision/grouping cases within M7-MATH-10/14, not a new analytics feature.

## 3. Coverage, corrections and empty reports

A durable report identifies provider endpoint/category, pool/scope, grouping,
requested interval, actual covered interval, source snapshot/data-through time,
collection time, completeness and facts. Retrieve time does not mean data is
current. When no source watermark exists, say Data through not reported and show
the query coverage and checked time separately.

Current views select the newest **complete compatible report** for the requested
interval/grouping; they do not add repeated polls. For wider ranges use disjoint
complete report intervals, never both the parent total and its child breakdown.
If a later complete report omits a previously returned bucket, the earlier
bucket is no longer part of the current total. Preserve both reports in history.
Do not use latest-row-per-bucket alone: that retains phantom spend after a
provider correction. A distinct signed adjustment is included once; a replacement
bucket supersedes its predecessor instead. Adapters declare which semantics apply.

Current selection scans all matching compatible revisions, not merely the
first history page. A newer attempt with unknown currency is a different
context and cannot make earlier monetary evidence current. Keep last complete
report, latest persisted attempt and latest collection outcome distinct; failed
provider calls without reports come from M04, not inferred M05 history. These
are T004/T005/T010 cases within M7-MATH-04/05/10/15.

Unresolved upstream identity requires both binding ID and generation in current
selection. Partitioning history by those fields is insufficient: the current
query must receive the active binding through M02's published metadata boundary
and exclude other unresolved lineages. If active authority is missing or changes
during the read, current spend is unavailable/retry, not the newest old actor's
value or funds. Expose an opaque context discriminator so P02 can invalidate
retained current values without credential identifiers. Explicit authorized history can still select that old report, labelled
with its original context. Confirmed compatible scope may preserve history across
key rotation. Unassociated unresolved lineages cannot establish shared identity
for totals or forecasts. An explicit canonical owner association may select one compatible
complete report across currently validated members; it never sums alternative
reads, admits an old binding or proves coverage compatibility.
T004/T005/T010 cover this under M7-MATH-04/05/10/11/15; no new history engine.

A complete empty result is a real coverage record, not a fake observation.
Return No reported usage. A derived zero aggregate is allowed only when official
source semantics establish that empty complete coverage means zero; its input
is the real report receipt, and it is labeled derived. Complete empty coverage
stays complete even when currency or watermark is unknown. Without admitted monetary-zero semantics, show Cost not reported and
Data through not reported as applicable; do not relabel complete coverage Partial.
In particular, a complete counts-only report is not Incomplete merely because
`spend` is absent. Retain the installed T004/T010/T012 correction: report Complete
coverage / Cost not reported, while a genuinely missing page stays Partial.
Denied access and missing pages are separate unsuccessful/incomplete outcomes,
never monetary zero.
Do not create dummy observation/projection/event IDs to satisfy old receipts.

Publish additive budget receipt/run-view contracts because current
`CollectionCommitReceiptV1` and successful run views require observations (and
the receipt requires projections/events). Leave existing quota contracts intact.
An empty budget report can have zero facts and a real report/coverage reference.

## 4. Period selection and history

Reporting filters use UTC `[start,end)`. Initial common ranges: Last 7 or Last
30 completed UTC days, ending at the same UTC midnight for every account.
The fixed cutoff makes cross-account period comparisons meaningful. The UI shows
actual coverage and source watermark. For native responses containing a current
partial day, derive the selected total only from complete aligned source buckets;
never use the wider native total as the selected-period total. Keep any current
partial-day reading separately labeled in detail. No partial bucket prorating.
Ollama native ranges are not a billing-month total. Account detail may show a
separate provider billing period; incompatible period spend cannot derive its
limit headroom.

No interpolation or prorating across incomplete daily boundaries. Request only
source-supported boundaries; unsupported selection returns a clear reason.
Source latency is shown separately from collector failure. A successful poll
with an unchanged source watermark is not fresh usage. Backfill/revision work
re-queries supported recent intervals under the normal request budget and retains
superseded versions. No unbounded full-history import on first connection.

The [Ollama usage reference](https://docs.ollama.com/api/cloud-usage), rechecked
on 11 November 2026, explicitly defines `7d` and `30d` as seven/thirty completed
UTC days plus today's partial bucket. Use the matching native range and exclude
today from the completed-day total. No wider-range workaround or extra backfill
is required by that documented shape. Verify the actual returned boundaries;
an unexpected gap is Partial/source drift, not permission to prorate. General
coverage checks still reject genuinely missing intervals for any provider.
UTC cutoff calculations are independent of browser timezone/DST; display local
timestamps with the timezone and expose UTC bounds in details.

Daily history is selected-report bucket history, not collection-run or report
revision history. Repeated full reports describe the same spend and must not
be summed into a time series. For ranges that need multiple reports, choose
compatible disjoint complete intervals or report missing coverage; never splice
a revised bucket into an older total without its report context. T010 provides
the first table query; T013 adds the chart from the same exact values.

Keep a selected range's UTC cutoff fixed through pagination, table/chart reads
and the source comparison. Crossing midnight does not silently retitle yesterday's
report as today's selection. An explicit stored-data refresh preserves the interval,
creates a new read snapshot and discloses missing coverage for that selected
interval. Only Latest completed window advances the cutoff. This is T010/T012's existing
snapshot rule and M7-MATH-15, not a new scheduling mechanism.

Initial history fetch is up to 30 days where supported. Retain genuine collected
history for the existing 365-day policy, showing Coverage begins at… when less
exists. Never promise a year of data on a new connection. Cost bars and balance
snapshots use separate chart series; no line across missing periods. API queries
use a fixed report/revision cursor so later corrections do not shuffle pages.
Retention keeps referenced current/derivation facts; expired cursors request a
fresh query rather than returning misleading continuity. T010/T011 expose older
retained seven-/thirty-day windows via Previous/Next and exact UTC cutoffs, with
No retained report for gaps. Source history retains original scope-epoch labels
and authorized report references. Retention is not a promise that the provider
can recollect an arbitrary old interval; history GETs never collect.

The reporting cutoff is not the read snapshot. A completed explicit collection
advances `as_of` for the stored-data reread while retaining the requested
`[start,end)`; otherwise the report can be permanently excluded by the page's
pre-action snapshot. Update selected report, derived total and history cursor
together. Live run progress is queried separately through M04. If a run starts
before an `as_of` but completes afterward, do not represent its later result as
an outcome known at that earlier time. This clarification is within
M7-MATH-15 and T007/T010/T011, not temporal event-sourcing machinery.

## 5. Aggregation and shared identity

A credential binding proves an access path, not an independent pot of money.
Use safe provider scope IDs where supplied; otherwise the owner may explicitly
associate a shared resource. Association declares identity, not coverage: a
project-restricted report is not a whole-organization report merely because
both use the same pool. Self/team and parent/project coverage remain separate.
Resolve eligible current reports for the pool before primary-group attribution;
a healthy compatible access path can supply its one contribution even if a
second path fails. Keep the failed connection's state visible. Use the existing
deterministic newest-complete-report policy, with retained input identity; do
not sum alternative reads or require another key merely to verify duplication. Do not deduplicate by email, label or equal amounts.
If overlap is unresolved, keep observations visible and omit the ambiguous pool
from aggregates with a count/reason. Owner-confirmed attribution is disclosed.

Aggregate by currency, exact interval, cost basis and compatible coverage.
Do not combine provider list cost with after-discount cost, self with team usage,
organization with included project rollups, or API spend with subscription fees.
Current admitted source labels are `discounted_before_credits` (Anthropic),
`openai_reported_cost` (OpenAI) and `provider_reported_usage_usd` (Ollama).
A shared currency does not establish equivalent cost bases: initial Overview
shows separate labelled subtotals, unless an admitted mapping proves equivalence.
No new conversion or cross-provider accounting layer is required.
Dashboard organization aggregates follow current owner grouping; moving an
account preserves source history and does not rewrite provider ownership.
A shared pool is assigned one primary dashboard group and counted once globally.
M02 publishes canonical association and primary-group attribution through
CTR-REG-014 1.5.0; pool controls/query are installed at schema0734. Billing
connection scope/resource fields alone never establish that association.
Unresolved rows may ship visibly with an exclusion reason during the first
increment; implementing only those exclusions does not complete organization
aggregation. T002 supplies the metadata, T004 proves the policy and T010/T012
consume it. No heuristic merging or new identity-resolution service is needed.
Links from accounts in other groups show Shared pool; not counted again here.
If only a secondary group is selected, its row says Shared; counted under
[primary organization] and contributes nothing to that group's subtotal. This
is an attribution exclusion, not missing financial coverage. Selecting primary
and secondary groups counts the pool once under the primary. Moving the primary
group affects current dashboard attribution only, never source history.
Provide partial-subtotal coverage explicitly; never a reassuring whole total
when configured accounts failed or later pages have not been loaded.

The backend computes filtered summaries across the complete selected inventory,
independently of the returned row page. More than 2,000 selected canonical pools
returns aggregate unavailable / narrow the filter, not a truncated total.
Ordinary API pages remain bounded (maximum 200). This is a resource guard, not
a supported-capacity claim or a reason to omit ordinary later-page accounts.

Each subtotal includes only compatible complete reports for its stated interval.
Show counts/reasons for missing, partial, stale or unresolved pools; keep their
last values on their rows. If an older complete report remains after a failed
refresh, any subtotal using it must disclose that older evidence and its age,
not claim all sources current. A filtered set with no eligible reports has an
unavailable total, not zero. Rows, eligible-pool selection and primary-group
attribution consume one revisioned registry snapshot. A concurrent edit causes
a retry of stored queries, not a partly old/partly new financial total. This is
ordinary optimistic consistency within the existing query, not event sourcing. Provider totals and dimension breakdowns are
alternative views of the same spend, never additive contributions.

Overview identity includes cost basis/category as well as canonical resource
and currency. Render multiple compatible groups as labelled subrows, retaining
their context on detail links. Group labels do not prove financial disjointness:
two source categories that cover overlapping cost must still be excluded or
represented as alternative views. Prefer the admitted ungrouped total, not the
sum of every context returned by a repository.

Different resource epochs remain separate report contexts. A registry scope
edit timestamp is not a provider financial boundary: never cut or prorate a daily
bucket there. Only source-established disjoint compatible coverage can compose
a wider interval; retained reports keep their original epoch and full interval.
Moving a dashboard group changes
current grouping only; historical financial scope and source identity stay
unchanged. Currency or cost-basis changes likewise create separate compatible
groups rather than an implicit conversion.

## 6. Small, defensible forecast

Compute on demand from retained facts; no forecast persistence table, new event
stream or configurable forecasting framework in M7. Return method version,
`as_of`, exact input report IDs, coverage, assumptions and availability reason.

Method `budget-observed-rate-v1/1.0.0` requires at least three complete,
nonoverlapping cost buckets spanning ≥24 hours, same pool/currency/cost basis,
known bucket duration, no missing coverage, no signed adjustments or unresolved
corrections. Select at most 200 buckets within the latest seven completed UTC
days ending at the selected funds observation's UTC-midnight cutoff, bounded
by query `as_of`.
For a rate without funds, use the query `as_of` cutoff and return no exhaustion
date. Three consecutive complete daily buckets can qualify; seven populated
days are not mandatory. Use the newest contiguous qualifying observed interval
and return its actual bounds; never join observations across a missing bucket.
Freshness eligibility still applies, so an older interval is not silently current.
Known zero-cost intervals contribute duration only from explicit zero monetary
facts or admitted complete-cost-coverage zero semantics. Request/token counts
cannot fill monetary coverage. Unknown gaps must not be removed from the
denominator to inflate burn.

`rate = sum(bucket costs) / complete covered duration`.
Equal positive daily costs therefore yield a positive rate. Rate zero produces
No consumption in observed interval, not an infinite forecast. No rate estimate
is taken from a changing cash balance, since top-ups and expiries may change it.

Missing funds or limits prevents an exhaustion estimate, not a qualified
observed spending rate. Publish rate and exhaustion availability separately.
Counts-only data supports neither monetary rate nor an inferred cost.

An exhaustion estimate requires costs attributable to the selected funds
component. Whole-pool spending cannot predict separate included/purchased-credit
depletion without source-established allocation. Owner pool association does
not supply that evidence. Show the balances and observed whole-pool rate;
do not invent spending order, a combined balance or account-stop date.

Exhaustion also requires fresh selected funds and an admitted cost-source
freshness policy evaluated against the pinned forecast context. Missing source
watermark or missing admitted freshness policy means freshness unknown and no
exhaustion date. A successful recent poll and the fifteen-minute collection
cadence are not evidence of fresh underlying financial data. Keep an otherwise
qualified historical rate labelled with its actual interval. T006/T008/T009
supply source metadata; T013 owns this existing eligibility decision, with no
new universal freshness threshold or subsystem.

Exhaustion needs a compatible authoritative remaining amount or enforced limit
headroom. Numeric time-left requires **strictly positive** compatible remaining/headroom
and rate. Zero or negative headroom is an observed zero/exceeded condition,
never negative time-left or a fabricated historical exhaustion date. A zero
cash balance does not prove service is blocked if enforcement is unknown.
Select cost buckets whose ends are no later than both the selected
balance/headroom observation and query `as_of`. Anchor the projected exhaustion
to that observation time, not page-load time. Unchanged report inputs therefore
produce the same projected date after reload; later costs cannot be applied
retrospectively to an earlier balance. If compatible fresh inputs cannot be
established, return the existing unavailable reason. Historical estimates are
labelled as-of estimates, never a live countdown. This is T013/M7-MATH-15/16.

`time_left = remaining / rate`. Label **Estimated at the observed
rate, as of [balance time]**. Provider lag, current unposted spend and possible
future top-ups are disclosed; never silently subtract estimated unposted usage.
If compatibility/freshness cannot be established, show a reason and no date.
If a known reset occurs first, say Estimate extends beyond known renewal; do
not promise exhaustion after that reset. Beyond seven days, show Beyond the
7-day forecast horizon, not a fabricated precise date. Reported zero balance is
observed depletion of that component independently of forecasting, not proof
that the whole account is blocked. Apply the same bound to known expiry of the
selected credits: **Credits expire before the estimated consumption date**;
do not carry expiring funds beyond expiry or assume replacement funds. In pure
M7-MATH-15/16, 6 USD at 2 USD/day with expiry in one day has no three-day
consumption date; expiry in four days does not exclude the three-day estimate.
Observed per-bucket variability
can be shown in detail; it is not a statistical confidence interval.

Numeric forecasts are conditional on actual available inputs. A correct
No estimate—provider does not expose remaining funds response satisfies that
case; it is not a numeric live-verification pass. Pure numerical tests plus a
real no-input UI result do not claim an observed real exhaustion date.

## 7. Bounded collection, without new scheduler machinery

Use one existing M04 run per report: endpoint/category, scope, one grouping and
bounded interval. Paginate sequentially, normalize allowlisted fields, discard
raw bodies, and perform one atomic M05 commit of facts and report coverage.
Reuse run leases, idempotent receipts and get-commit-status recovery. A crash
during commit reconciles the receipt before any recollection. Expired queued or
running authority gets a truthful terminal outcome. Recollection is permitted
only when the source still admits the exact captured interval and current
authority permits it. A rolling Ollama interval lost across midnight remains a
failed old request; a new due interval is admitted separately, never relabelled
as recovery of the old one.

Initial admission bounds per report: 20 pages/requests, 2 MiB per response,
16 MiB normalized total, 10,000 normalized records, 120-second run deadline,
10-second request timeout, one in-flight request per billing binding. These are
conservative implementation budgets to measure in the first real vertical,
not provider limits. Enforce normalized size while mapping, before allocation
grows unbounded. Never trust `limit` as a bound on expanded provider rows.

The deadline covers the admitted work, not a fresh allowance per request.
Pass remaining time to each request and leave time for normalization/commit;
20 requests is a maximum, not a promise that 20 ten-second pages fit. Retry-After
causes a later scheduled attempt, not sleeping past the current deadline.
Expired queued/running work is reclaimed through existing M04 ownership rules;
committing work first reconciles the M05 receipt. Never recollect while a live
owner could still commit. T007 tests these separately from supervisor exit.

Rate control is per known provider user/shared scope, across local bindings and
balance/usage jobs; respect Retry-After. Use the stricter admitted provider limit.
Default periodic report refresh is 15 minutes with jitter; Ollama balance keeps
its existing schedule. Report categories/groupings are staggered, not a burst.
T007 schedules the supported ungrouped seven- and thirty-completed-day reports
needed by the two initial selectors, with first thirty-day collection bounded
as above. Reuse a wider source response for a shorter view only when the
adapter's complete daily buckets and M05 exact-coverage policy prove that
projection; otherwise retain distinct report intents under the same existing
scheduler. Check initially collects the seven-day report, not every category.
Persist distinct closed seven-/thirty-day operation families and the exact
selected UTC interval/cutoff in the existing durable request context. Current
billing admission now retains that context through CTR-COL-002 2.4.0; selected
7/30-day ungrouped billing actions first shipped at `ef8fa86`. The worksheet
records subsequent installed cloud manual usage and fair 7/30-day scheduling.
Remaining T007 work includes category/grouping coverage and outstanding live,
sustained-fairness and recovery evidence. Reuse installed context/actions.
Recovered work uses
the captured intent, never the restart clock; do not falsify `requested_at` to
represent an older cutoff. A native rolling source that cannot still serve that
captured interval must report it as no longer collectable, not silently move it.
No new queue or report-job schema is implied.
Additional supported breakdowns use explicit collection and the same cooldown;
opening or changing a view never silently enables background work.

The fifteen-minute due cadence is not a freshness guarantee for every report.
T007 records the finite automatic context inventory per shared request-budget
scope and the admitted allowance before adding each category. Request demand is
the sum of actual page requests across due contexts, including balance work
where it shares that allowance. Distinct keys/access paths do not create more
allowance for the same scope. Compare demand with the admitted request budget
and measure service time during genuine collection; do not invent provider
quotas or promise a full refresh cycle from the timer alone. A maximum twenty-page
report can consume twenty requests, not one. Fair selection staggers due work;
explicit breakdowns compete under the same limit. Publish actual source times
and retry eligibility through existing fields. If the required inventory cannot
meet a claimed cadence, correct the claim and report the measured constraint;
do not add workers, violate cooldown, or silently drop mandatory categories.
This is T007/M7-A09 resource-budget verification, not a new tuning UI or scheduler.

Durable eligible work drives dispatch; an in-memory wake signal is only a hint.
Drain admitted work fairly across successive claims, retaining one worker and
existing per-scope limits, so coalesced wakes
cannot strand a second account's job. One throttled or failed scope must not
block another due scope. On restart, reconcile retained runs and resume current
due work without launching one job for every missed polling tick. Disable stops
new automatic admission; any running job follows the generation/commit fence
and retains truthful history. No new queue, catch-up engine or tuning screen.
M7 never intentionally produces requests/spend to make data appear. Views and
history queries do not synchronously fetch providers. A supported breakdown can
queue an explicit bounded collection when its report is not yet present.

If a report exceeds bounds, retain prior complete values, expose Partial/Too
large and request a smaller source-supported interval next. No partial batch
becomes the complete total. If the minimum supported report still exceeds bounds,
record that actual account limitation and raise the smallest decision once.
Do not prebuild parent/child jobs, page checkpoint tables or a generic report
engine. Introduce them only if measured real data proves necessary, with the
original requirement and affected ticket named.

## 8. Calculation examples and acceptance cases

These values are solely pure no-I/O test inputs:

| ID | Input/condition | Expected result |
|---|---|---|
| M7-MATH-01 | 0.10 + 0.20 USD | Exactly 0.30 USD before formatting |
| M7-MATH-02 | Provider supplies 123.456789 cents | Exactly 1.23456789 USD, with source precision |
| M7-MATH-03 | Same daily costs 2, 2, 2 USD over three full days | 6 USD; rate 2 USD/day, not zero |
| M7-MATH-04 | Complete report changes a bucket from 8 to 6 | Current 6, retained earlier 8; never 14 |
| M7-MATH-05 | Later complete report removes that bucket | Old bucket excluded from current total; history retained |
| M7-MATH-06 | Hard limit 100, compatible spend 110 | Exceeded by 10; no negative cash balance, false zero-spend or calculated exhaustion date even with a positive rate |
| M7-MATH-07 | Soft budget 100, spend 20, cash unknown | Soft-budget headroom 80; available funds unknown |
| M7-MATH-08 | Balance snapshots 40, 35, 50 | Current balance 50; not 125, no burn inferred from top-up |
| M7-MATH-09 | Cost 10 and distinct adjustment −2 | Net 8 for compatible report; forecast unavailable for adjusted sample |
| M7-MATH-10 | USD and GBP, or parent/project duplicate rows | Separate groups; no invalid total |
| M7-MATH-11 | Same shared pool via two keys | One total with two access paths; unresolved pool excluded |
| M7-MATH-12 | Complete empty report with unknown currency/watermark versus qualified zero or missing pages | Complete coverage remains complete; money/watermark unavailable unless admitted. Missing pages remain partial; counts never imply zero cost |
| M7-MATH-13 | 0.004 USD | `<0.01 USD`, exact 0.004 available; not plain 0.00 |
| M7-MATH-14 | 38/78-digit valid coefficient; cancellation; overflow | Exact conversion/sum within bounds; overflow rejected |
| M7-MATH-15 | Partial day, gap, mixed period, revised data, missing limit | Explicit partial/no-forecast reason; no extrapolated real funds |
| M7-MATH-16 | 100 USD remaining; daily rate 2 USD | Beyond 7-day horizon, with rate/as-of; no precise stop date |

Additional cases within the same IDs (no new acceptance inventory):

| Existing IDs | Pure input | Required result |
|---|---|---|
| M7-MATH-03/15/16 | Three complete days at 2 USD/day; no balance/limit | Rate 2 USD/day with sample bounds; no exhaustion date; Remaining funds not reported |
| M7-MATH-07/08/15/16 | Included credits 10 USD, purchased 30 USD; whole-pool rate 2 USD/day; allocation unknown | Show components and rate separately; no component date, assumed combined balance or account-stop claim |
| M7-MATH-15/16 | Same complete costs fetched twice; source watermark unknown | Later retrieval alone cannot enable an exhaustion date or move a previously pinned estimate |

Existing test families also cover native-range alignment and DST boundaries
(M7-MATH-15), no eligible subtotal versus a genuine zero (M7-MATH-12), scope-epoch
and currency changes (M7-MATH-10/11), and a last complete report following a
failed or partial refresh (M7-MATH-04/05/15). T004 owns exact money, availability,
selection and grouping policies; T013 owns rate/horizon/forecast cases
M7-MATH-03/16 and the forecast branch of M7-MATH-15. Forecast completion is not
a prerequisite for first-report storage or the first useful dashboard.

Boundary acceptance independently uses genuine provider reports, migrated
SQLite, actual HTTP and built-browser values. Pure examples never cross I/O.

## 9. Presentation and reconciliation decisions

- M7 sorts account, organization and state across the full filtered inventory
  with stable ID tie-breakers. Monetary sorting is deferred, matching the UI
  plan; exact arithmetic does not introduce another sort feature. Changing
  filters starts a new snapshot query. Stored-window/width navigation invalidates
  report/cursor selection but preserves read `as_of` as defined in section 4.
  Neither change may append pages from the prior selection. T010/T012 own this
  behavior.
- Chart geometry is approximate presentation, never a second financial
  calculation. Exact API amounts remain the table, label and tooltip authority.
  Plot negative amounts below zero and positive amounts above zero; retain
  adjustment labels. An adjustment can have either sign: M7-MATH-09 covers
  cost 10 plus adjustment +2 = 12 and adjustment −2 = 8, with matching chart
  signs. Both adjusted samples remain forecast-ineligible under section 6.
  Never clamp negative costs to zero.
  Do not connect balance points across unknown intervals. T013 owns this.
- A dimension breakdown reconciles to its matching total only when the source
  establishes disjoint, complete coverage for the same snapshot. Include a
  reported Unallocated/Other remainder once. A partial or top-N list without
  a complete remainder is labelled partial; do not manufacture an Other value
  or allocate organization cost to an agent, email or key by proportions.
  This is M7-MATH-10 and T013/T015, not a new accounting dimension.
- Compare the same scope, interval, grouping and cost basis. The provider's
  displayed rounding may differ from stored precision; record the comparison
  precision and source watermark. No universal percentage tolerance and no
  arbitrary rounding to make a discrepancy pass. T015 owns reconciliation.
- Collection success, coverage and provider update time are separate facts.
  A successful unchanged report can be a healthy collector with delayed source
  data. A complete interval is not a promise that the provider will never revise
  it. Keep source freshness policy in each admitted adapter; do not impose
  subscription reset/freshness assumptions on financial reports.
- The first successful genuine report supplies both access evidence and report
  data for its exact binding/scope generation. Persist it once and reuse it;
  enabling monitoring schedules the next due read instead of immediately
  repeating a still-current identical request. Metadata-only access checks do
  not count as reports. T005/T007 own this distinction.
