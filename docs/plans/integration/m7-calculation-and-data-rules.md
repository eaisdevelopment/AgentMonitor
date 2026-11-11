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

## 2. Exact representation and display

Use existing coefficient/scale plus ISO currency, never float, SQL REAL/SUM of
decimal text, `parseFloat`, `Number` or browser arithmetic for money. Decode JSON
numbers directly to Decimal; convert documented cents to currency units by exact
base-10 scaling in the provider adapter. Preserve source precision separately.

The existing `CanonicalDecimalV1.as_decimal()` uses context-sensitive `scaleb`;
it rounds a permitted 38-digit coefficient under the default 28-digit context.
T004 includes the small shared-primitive correction and regression tests before
budget calculations depend on it. Use context-independent decimal construction
and scaled-integer addition/subtraction. Keep the existing 78-digit coefficient /
18-scale public bounds; reject overflow explicitly, never silently round facts.

Financial totals remain exact. Division used for rate/ratio is derived:
retain exact numerator/denominator and input IDs; format a bounded decimal only
with declared precision/rounding. Display ordinary USD totals to two decimals
using half-even rounding, and positive sub-cent values as `<0.01 USD` with the
exact source amount available in details. Negative sub-cent adjustments get an
explicit negative label. Never display unqualified zero for nonzero money.
For currencies without an admitted display-minor-unit rule, display exact
decimal + currency code rather than guess the exponent. Formatting is not
cross-currency conversion. Rounded rows can differ from rounded total; the
total is computed from exact inputs and carries an explanation.

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

A complete empty result is a real coverage record, not a fake observation.
Return No reported usage. A derived zero aggregate is allowed only when official
source semantics establish that empty complete coverage means zero; its input
is the real report receipt, and it is labeled derived. Empty data with unknown
watermark, denied access or missing pages is unavailable/partial, never zero.
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

A rolling 7-day response does not necessarily cover seven completed UTC days;
it can miss the first partial day and include today instead. Select an admitted
wider native report where supported, then use only complete aligned buckets.
A rolling 30-day response may still lack the start of a 30-completed-day query.
Use retained compatible coverage if present, otherwise expose the exact missing
interval as Partial. Never relabel that rolling total as the selected interval.
UTC cutoff calculations are independent of browser timezone/DST; display local
timestamps with the timezone and expose UTC bounds in details.

Initial history fetch is up to 30 days where supported. Retain genuine collected
history for the existing 365-day policy, showing Coverage begins at… when less
exists. Never promise a year of data on a new connection. Cost bars and balance
snapshots use separate chart series; no line across missing periods. API queries
use a fixed report/revision cursor so later corrections do not shuffle pages.
Retention keeps referenced current/derivation facts; expired cursors request a
fresh query rather than returning misleading continuity.

## 5. Aggregation and shared identity

A credential binding proves an access path, not an independent pot of money.
Use safe provider scope IDs where supplied; otherwise the owner may explicitly
associate a shared resource. Do not deduplicate by email, label or equal amounts.
If overlap is unresolved, keep observations visible and omit the ambiguous pool
from aggregates with a count/reason. Owner-confirmed attribution is disclosed.

Aggregate by currency, exact interval, cost basis and compatible coverage.
Do not combine provider list cost with after-discount cost, self with team usage,
organization with included project rollups, or API spend with subscription fees.
Dashboard organization aggregates follow current owner grouping; moving an
account preserves source history and does not rewrite provider ownership.
A shared pool is assigned one primary dashboard group and counted once globally.
Links from accounts in other groups show Shared pool; not counted again here.
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
unavailable total, not zero. Provider totals and dimension breakdowns are
alternative views of the same spend, never additive contributions.

A request spanning a billing-scope change cannot become one pool total. Split
by resource epoch and show its coverage. Moving a dashboard group changes
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
corrections. Select at most 200 buckets from the latest seven complete UTC days.
Known zero-usage intervals may contribute duration only from complete coverage
evidence. Unknown gaps must not be removed from the denominator to inflate burn.

`rate = sum(bucket costs) / complete covered duration`.
Equal positive daily costs therefore yield a positive rate. Rate zero produces
No consumption in observed interval, not an infinite forecast. No rate estimate
is taken from a changing cash balance, since top-ups and expiries may change it.

Exhaustion needs a compatible authoritative remaining amount or enforced limit
headroom. Numeric time-left requires **strictly positive** compatible remaining/headroom
and rate. Zero or negative headroom is an observed zero/exceeded condition,
never negative time-left or a fabricated historical exhaustion date. A zero
cash balance does not prove service is blocked if enforcement is unknown.
`time_left = remaining / rate`. Label **Estimated at the observed
rate, as of [balance time]**. Provider lag, current unposted spend and possible
future top-ups are disclosed; never silently subtract estimated unposted usage.
If compatibility/freshness cannot be established, show a reason and no date.
If a known reset occurs first, say Estimate extends beyond known renewal; do
not promise exhaustion after that reset. Beyond seven days, show Beyond the
7-day forecast horizon, not a fabricated precise date. Reported zero balance is
observed depletion independently of forecasting. Observed per-bucket variability
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
before commit recollects; a crash during commit reconciles the receipt.

Initial admission bounds per report: 20 pages/requests, 2 MiB per response,
16 MiB normalized total, 10,000 normalized records, 120-second run deadline,
10-second request timeout, one in-flight request per billing binding. These are
conservative implementation budgets to measure in the first real vertical,
not provider limits. Enforce normalized size while mapping, before allocation
grows unbounded. Never trust `limit` as a bound on expanded provider rows.

Rate control is per known provider user/shared scope, across local bindings and
balance/usage jobs; respect Retry-After. Use the stricter admitted provider limit.
Default periodic report refresh is 15 minutes with jitter; Ollama balance keeps
its existing schedule. Report categories/groupings are staggered, not a burst.
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
| M7-MATH-12 | Empty complete versus empty delayed/null-watermark | No usage/qualified derived zero versus unavailable; never conflated |
| M7-MATH-13 | 0.004 USD | `<0.01 USD`, exact 0.004 available; not plain 0.00 |
| M7-MATH-14 | 38/78-digit valid coefficient; cancellation; overflow | Exact conversion/sum within bounds; overflow rejected |
| M7-MATH-15 | Partial day, gap, mixed period, revised data, missing limit | Explicit partial/no-forecast reason; no extrapolated real funds |
| M7-MATH-16 | 100 USD remaining; daily rate 2 USD | Beyond 7-day horizon, with rate/as-of; no precise stop date |

Existing test families also cover rolling-range alignment and DST boundaries
(M7-MATH-15), no eligible subtotal versus a genuine zero (M7-MATH-12), scope-epoch
and currency changes (M7-MATH-10/11), and a last complete report following a
failed or partial refresh (M7-MATH-04/05/15). T004 owns exact money, availability,
selection and grouping policies; T013 owns rate/horizon/forecast cases
M7-MATH-03/16 and the forecast branch of M7-MATH-15. Forecast completion is not
a prerequisite for first-report storage or the first useful dashboard.

Boundary acceptance independently uses genuine provider reports, migrated
SQLite, actual HTTP and built-browser values. Pure examples never cross I/O.
