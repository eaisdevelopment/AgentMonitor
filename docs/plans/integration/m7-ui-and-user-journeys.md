# M7 UI and user journeys

- Status: Approved under focused M7 plan 1.1.0; installed setup/pool/Overview increments are recorded in the delivery worksheet. Full monetary/history/analysis acceptance remains unfinished.
- Owner: P02; API contract owner P01; billing semantics M05.
- Requirements: FR-ACC-001..004/006, FR-ORG-001..003, FR-BUDGET-001..006;
  AC-UI-002..006, AC-HIST-001, AC-LIVE-005.
- Authority: [execution plan](m7-execution-plan-2026-11-11.md).
- Calculations: [money, coverage and forecast rules](m7-calculation-and-data-rules.md).

## 1. Questions the screens must answer

1. Which dashboard organization and provider billing scope does this money belong to?
2. How much usage/spend was reported, for which exact period, and how recent is it?
3. Is a real remaining balance or enforced limit known? If not, why not?
4. Which supported project, model or key identifier accounts for that usage?
5. What action can I take if setup, collection or access fails?

No new top-level application or design system. Reuse Accounts, Organizations,
Overview and account detail. Preserve the top promotion/support header, company
footer, existing quota rows, 24-hour dashboard session and LAN access.
Collection/History stays a collection-run screen; budget history lives with the
billing account. No collection diagnostics panel is added to Overview.

## 2. Account creation and connection

Accounts offers **Add API billing account** separately from the existing
subscription connection action. Minimum fields: Provider (Anthropic API,
OpenAI API, Ollama Cloud), Account name, Dashboard organization or Ungrouped.
No required email for an organization billing account. Reuse existing provider
keys (`claude`, `codex`, `ollama`) and add a typed resource purpose/capability;
display product-specific names. Do not create duplicate provider adapters.

Creation returns the real account ID and opens its detail URL immediately.
For an existing subscription account, **Add API billing connection** attaches
a separate resource; it does not replace the subscription or start CLI login.
An API-only account must not show Claude/Codex CLI login, agent activity,
subscription quota or a misleading disconnected subscription warning.
Sections are selected from API-published capabilities, not a provider-name test.
Initial creation intent is only the pending-state fallback. If an API-origin
account later gains a subscription resource, show both independent sections.
API-only records never become empty/error subscription rows in Overview.
Ollama API setup reuses its existing cloud connection controls and balance pool;
API-only routing must not hide those controls and leave a dead-end account.

The account page then shows these steps, with actual server state:

Reuse completed setup for an existing cloud/billing resource. Expand only the
step requiring owner action; a working resource is not sent through creation or
key entry again merely because usage support was added.

1. **Choose billing scope.** Show the scope supported by the provider: whole
   organization, supported project/workspace, or Ollama self/team. The dashboard
   organization label is not evidence of provider organization membership.
   Existing shared scope can be explicitly associated by the owner instead of
   creating a second financial pool. Do not infer it from equal amounts/emails.
   Manage connection includes **Change scope** and **Use existing billing pool**
   with provider/scope labels and a primary dashboard organization. T002 owns
   these metadata controls and API contracts. Changing scope starts a new epoch;
   it does not relabel prior financial history or transfer access verification.
   Existing compatible access paths can share a pool; an unresolved association
   stays visible but is excluded from totals until resolved.
2. **Store credential locally.** Give one installed, canonical copyable command
   prefilled with the nonsecret account/resource selectors. The installed
   command resolves the current binding locally; no manual IDs are needed. It must not require typing IDs or
   choosing from an unrelated account list. The local command confirms provider,
   account label and dashboard organization, then accepts the key without echo.
   It writes only the selected managed `.env` entry. No key textbox in the browser.
3. **Check connection.** A visible button queues one bounded read. Disable it
   while already queued/running and display the eventual result in place.
   Returning focus refreshes safe status automatically. Distinguish connection
   access from data availability and identity verification.
4. **Enable API monitoring.** Explicit owner action after successful access;
   queue the first reading if no compatible report was collected by Check
   connection. Reuse and display a genuine report from that check rather than
   immediately issuing an identical request; schedule its next due refresh.
   Show Waiting for first reading only when appropriate. Successful access with
   an empty report is valid.

For the first provider increment, action eligibility comes from the admitted
runtime and current credential/binding metadata. Missing credentials keep Check
disabled with the local-entry instruction. Stored credentials enable Check only
for an admitted source with a working collection runtime. A runtime-unavailable
response retains Stored and gives the safe retry reason; it never becomes
Connected. Enable stays disabled until its actual mutation exists and access
was proven for the current binding/scope generation. An unfinished provider
action is labelled Not yet available in this build, not provider Unsupported.
T002/T007/T011 own these controls; no inert button is presented as a working step.

For Ollama, the existing balance connection check does not prove usage
collection. Usage Check/Collect acceptance requires the matching actual usage
run and retained report. Until that action is wired, label it unavailable in
this build while stored usage remains readable. Reuse the existing connection;
do not request a second key or imply that refreshing stored data collected it.

LAN instruction: **Run the setup command on the computer hosting AgentMonitor,
as the user running its service.** A terminal on the browser's other computer
does not configure the server. Existing SSH/local terminal access is sufficient;
M7 does not build remote terminal access. Show the hosting computer's safe name
and selectable command text when LAN HTTP clipboard APIs are unavailable.
Use the installed runtime entry point, never a development-worktree path.

No owner step is requested before its button/command exists and is tested.
T014's setup activation must precede requesting key entry: the command resolves
the selected installed service, so displaying it from a candidate with an older
installed service is not a working enrollment demonstration. Candidate-only
tests and full later dashboard activation remain distinct evidence.
Owner configures accounts, organizations and secrets; coding agents do not.
T002 includes all pages of the organization selector. Failed/unloaded name lookup
shows Organization unavailable, never Ungrouped for an assigned account.

Keep setup inside the existing account page, not a separate wizard. Scope
choices are restricted to the admitted provider capabilities; no generic
provider-organization browser is required. If verification reveals a different
scope, show the mismatch and an explicit correction action before monitoring;
do not silently reassign the account's group or merge its billing pool.
The cloud setup panel is shared for Ollama regardless of how the account was
created. Rendering its command is not proof that enrollment or access succeeded.

Credential state is independent of provider access and monitoring. Show Missing,
Entry pending, Stored or Cleanup required using safe server metadata. Stored
does not mean Verified. Cancelled/interrupted entry can be resumed locally;
rotation preserves history and requires a new access check. If old-key cleanup
fails, report it without claiming the old key was removed. The owner need not
recreate the account. T007 completes Check connection → Enable API monitoring
→ Waiting for first reading; T014 proves the installed command/host journey.

**Disconnect or clean up local credentials** contains the published host-local
commands. Disconnect stops AgentMonitor's billing access before cleanup and
preserves history; it does not revoke the provider key. Cleanup retries only
recorded retired entries, including for archived accounts, and leaves an active
replacement key alone. Commands remain selectable when clipboard permission is
unavailable. Displaying or copying one never claims it executed. Refresh billing
status reads the actual result; successful changed authority must also invalidate
the current financial view, while a failed read retains prior facts and times.

## 3. Overview: compact, understandable rows

Keep subscription quotas and API billing as two labeled sections with one
shared organization multi-select and provider filter. Lift only filter state
out of the existing `AccountQuotaOverview`; retain its quota sorting behavior.
Add a compact resource-type filter **All / Subscriptions / API billing**, default
All, with section counts and nonsecret URL state. This keeps API records reachable
without scrolling through a large subscription list. It adds no top-level page.
Add a report-range selector inside **API usage & spend**. Initial ranges are
Last 7 completed UTC days and Last 30 completed UTC days, ending at a shared
UTC-midnight cutoff; display the actual bounds, not a misleading billing-month label.
Source-native partial periods and data coverage remain visible per row.

Design-only layout, no sample telemetry:

```text
Organizations [selection]   Provider [selection]   Resources [All]
Subscription quotas  [existing table]

API usage & spend    Period [Last 7 days]     [Refresh view]
[Grouped spend summaries: currency · period · coverage]
Billing account | Organization | State | Reported spend | Available | Data through
[owner label]   | [group]      | [text]| [amount + code]| [state]   | [timestamp]
 provider · billing scope                      reporting interval
```

Each row identifies a canonical billing resource and compatible financial
context: currency, cost basis and admitted total-cost category for the selected
interval. Different contexts use labelled subrows under the same resource;
linked access paths appear under its label, not as additional money. Account
name opens its detail at the selected resource and context. A context without
money can still show its unavailable reason; it is not silently removed.
Funds-only resources still have an Overview row even before a spending report
exists. Show **No spending report** in Reported spend, retain the genuine funds
and their observation time in Available, and link by authorized account/resource.
Do not invent a report ID, currency context, cost basis or zero spend to make the
link work. Such a link preserves the selected Overview interval and read cutoff without
inventing a report selector. Only direct account URLs without financial selection
default to seven completed days. A row with a report retains the immutable report/context
selection described below. Counts-only reports likewise show counts in detail
and **Spend not reported**, never money. This is T010/T011/T012, not another view.

Provider-reported scope and dashboard organization are separately named.
An account connected to a whole provider organization does not imply all its
spend belongs to that individual email or one running agent.

Default API state/sort uses one server-computed priority: owner action required
(credential/scope/setup) → latest collection failure → incomplete or stale
financial evidence → known depletion/low remaining → current. Pending/reading
and monitoring preference remain secondary labels; retain any lower-priority
failure/fund facts in row detail. Within a priority sort by organization/name,
then stable account/resource/context ID. This is a fixed decision table, not a
configurable ranking engine. Unknown remaining capacity is not exhausted.
Column headings support organization, state and account sorting. These are the
required M7 sort controls; this increment adds no monetary-sort control. Any later monetary ordering must stay inside one
compatible currency/period/basis group and never compare USD and GBP values.
Final account/organization/state sorting applies to the complete filtered set
before pagination, with a stable tie-breaker and a reset cursor when sorting
changes. A first increment may label sorting as applying only to loaded rows;
that limitation is not completion of T012. No client fetch-all workaround is
required. T010 owns the bounded server query and T012 its controls.

Remaining percentages/bars appear only with a valid matching denominator.
Red on a component means remaining **≤20%**, or explicitly reported depletion/exceeded hard
limit. Account depletion additionally requires established constraining semantics:
an empty included-credit component does not exhaust an account with a separate
purchased-credit component. Preserve the existing non-constraining Ollama balance
classification; do not invent a combined percentage or credit spending order.
Show the raw percentage plus a bounded visual bar and text, never just
color. Compare the exact ratio before display rounding: 20.004% is not low,
19.996% is low even if both render as 20.00%. A high remaining percentage is not low capacity. A cash balance without
a cap shows money, not a made-up percent. No automatic red threshold for spend.

FR-ORG-003 requires organization/global summaries: render compact grouped
reported-spend totals by currency, exact coverage period and source cost basis.
Never one mixed-currency grand total. Label included/excluded scope counts;
unresolved overlap or incomplete inputs produce a clearly labeled partial
subtotal or no total. Totals cover the filtered set, not merely the loaded page.
Use server-calculated summaries; no money aggregation in React. Current
Anthropic/OpenAI/Ollama adapters report different cost bases, so show separately
named subtotals even when each currency is USD; do not promise one common USD
total without proven equivalence. A pool linked from a secondary organization
shows Shared; counted under [primary organization]. Its canonical row identifies
the pool's scope and counted-under group first; connected account labels remain
visible as access paths, so a whole organization's spend is never presented as
one person's consumption. Expanding access paths or opening account detail
shows each connection's own failure/monitoring state separately from the pool's
financial evidence. A healthy compatible path may supply the pool's reading
without concealing another connection's error. Selecting only that secondary
group does not add it to that group's subtotal or classify it as missing data;
selecting both groups counts it once under the primary group. Selecting only
the primary group still resolves eligible evidence from all of that pool's
authorized access paths before attribution; filtering out a secondary account
must not remove the pool's valid report. The financial-value link uses the
contributing report's authorized account/resource/report tuple returned by the
API. Other access-path links open their own account details without borrowing
that report selector. T010/T012 test primary-only, secondary-only and both-group
selections plus each link's Back/reload behavior.

**Refresh view** rereads stored API data only, with the hint **Reload stored
readings; collect a new report from account detail**. Use the same read-only
label on detail. It does not make all accounts call their providers.
Detail offers the separate **Collect now** action with
server cooldown. One failed API budget request must leave quota rows usable.

T010/T012 retain the concurrent Overview correction delivered at `cd4f566`;
its [real concurrent-read evidence](../../evidence/m7-overview-query-reliability-2026-11-12.md)
is a regression boundary, not remaining implementation. Reuse that authenticated
concurrent Overview/setup/cloud probe during subsequent relevant changes. Add
monetary row/context assertions when genuine monetary reports become available;
the bounded current pass does not prove monetary Overview acceptance. Surface
any failed request. Retained same-context data is labelled with original times;
it is not a successful refresh. Keep the existing HTTP deadline. Serial reruns
and a healthy landing page cannot replace this proof. Reuse the existing browser
runner; no load-test platform or new acceptance ID is introduced.

## 4. Account detail: useful information first

Opening an Overview financial link on a mixed subscription/API account brings
the selected financial section into view, with a visible heading/focus target.
Ordinary account entry retains the subscription-first layout. Both sections
remain available; no new account page or router is needed. T011 verifies the
financial entry, Back, reload and keyboard/narrow-layout journey rather than
requiring the owner to scroll past unrelated processes to find the amount.

At the top: owner account name, provider product, dashboard organization,
provider billing scope, current state, report interval and data-through time.
The connection status is one compact line with **Manage connection** expandable;
setup details expand automatically only when action is required. T010 projects
supported balance/credits/soft and hard limits, period and availability reasons
from M05/existing cloud resources through typed API fields. T011 renders those
actual fields rather than a hardcoded Remaining funds not reported message.
Cost reports alone cannot establish absence or presence of funds. Reuse the
existing Ollama balance pool and disclose any incompatible scope/cost basis.

Show the funds observation time beside each balance/credit/headroom amount,
separately from the spend interval. While browsing older spending, label a latest
snapshot **Current balance as of [time]**; do not imply it belongs to that old
window. Funds can be visible before a usage report exists. The absence of an
Anthropic/OpenAI-style billing binding must not hide existing Ollama balances
or ask the owner to create a duplicate account. No historical balance is inferred.

| Section | Required content and behavior |
|---|---|
| Usage & spend | Reported spend; available balance; prepaid credits; soft budget; hard limit; actual billing/renewal period when exposed. Missing fields have a short reason, not empty cards or zero. Show source cost basis such as before credits |
| Usage breakdown | One supported dimension at a time: project/workspace, safe key identifier, model, token category or time. Separate money, tokens and requests. Do not fabricate a join between cost and usage reports. Include Other/Unallocated and coverage when reported |
| Forecast | Derived rate/as-of estimate with assumptions, or precise reason: no limit/balance, insufficient history, scope mismatch, delayed data or corrections. Not a promise that service will stop at that time |
| History | Bounded period, exact table and then simple chart from the same API facts. Spending per day uses bars; balance snapshots use separate series. Missing intervals are gaps; corrections retain lineage. Load more does not discard earlier rows if a later page fails |
| Source details | Collapsed: source/version, checked/data-through times, exact value, precision, observed/derived meaning, report coverage, omissions and inputs |
| Settings | Rename, move group, API monitoring on/off, replace key, disconnect/archive. Existing subscription monitoring remains independent |

The installed history table uses server-paged daily facts from a pinned report:
period, exact amount/currency, coverage and report provenance. Retain that query,
authorized report selection and explicit cursor/expiry behavior. The existing
`list_reports` query describes report revisions, not a daily-spend series;
revisions belong in expandable Source history. Prior-scope discovery is already
installed under CTR-CAP-006 2.9.0; retain it and extend genuine monetary and
naturally available prior-scope verification. The
financial detail identity resolves to the canonical billing resource; each
current financial context supplies its immutable report ID. History and its
pages stay on that report until explicit refresh. If retention removed it,
show Selection expired with Refresh, rather than silently changing the numbers. T013 uses
those same buckets for its chart. When the UTC cutoff moves, preserve the
selected reporting interval until Latest completed window is chosen; never
concatenate overlapping reports
to fill missing days. A provider without daily buckets shows its actual
aggregate interval, with daily history unavailable.

Stored history has **Previous window**, **Next window**, and **Latest completed
window** controls with exact UTC bounds. Previous/Next and changing 7/30-day
width preserve the read snapshot; width changes keep the selected end. Next is
disabled beyond that snapshot's latest completed UTC cutoff. **Refresh view**
rereads the same interval with a new read snapshot. Only **Latest completed
window** deliberately moves to today's completed cutoff. An explicit selection
change clears the old report selector/history cursor, retains the selected
resource and never starts collection. Use 7/30 completed UTC days as width
labels; Last is misleading when the owner browses an older window. No retained
report means missing stored coverage, not zero usage. These
reads never fetch a provider. Offer Collect now only for a source-admitted
interval; no arbitrary historical backfill promise. Source history lists retained
reports from prior scope epochs with original scope labels; selecting one uses
its authorized immutable report reference, not an arbitrary caller-selected scope.
T010 supplies a bounded authorized report-metadata list for that existing Source
history disclosure (report ID, original scope epoch, interval, source and
observation/collection times); T011 renders it. Paging daily facts of a known
report does not supply this discovery flow. Reuse the existing report-list port
where possible; no separate history application or provider call.
When an older report is selected, its main financial scope/epoch label comes
from that report, including after reload. The current connection scope belongs
separately in Manage connection; current funds retain their own scope/time.
Never put an old amount under the newly configured scope's heading. T002/T010/T011
cover scope change followed by old-report selection; naturally unavailable live
history is recorded separately from pure selection/presentation evidence.
An old-scope report is read-only historical evidence. Its Collect action is
disabled with **Historical or unconfirmed scope — return to current scope to collect**.
Unconfirmed covers a pinned report absent from current published evidence without
asserting that its epoch definitely differs. The
existing **Latest completed window** action clears that historical selection
and returns to the current resource scope; it still does not collect. Never
submit current credentials for the old scope merely because its report is open.
Use existing lists/controls, without a calendar or report-builder dependency.

History recovery distinguishes transport failure, rejected continuation and a
missing retained report. A transient error retries the same page. For
`400 invalid_cursor`, offer **Restart history pages**: request page one with the
same account/resource/report/period/`as_of`, without the rejected cursor. Keep
the old rows and chart, visibly marked, until the replacement succeeds; replace
them together rather than append duplicates. This is a read, not Collect or
Refresh view. If the report itself is no longer available, retain the explicit
selection-unavailable message and let the owner choose another retained report
or Latest completed window. Do not retry a permanently rejected cursor forever
or silently replace the selected report with the latest one. T010/T011 cover
the real rejected-cursor HTTP response and built recovery within existing
history checks; no pagination framework is required.

Start with the exact table in the first usable slice; chart and forecast arrive
in the later M7 enhancement slice. They are still required before M7 closes.
Keep source/diagnostic detail out of the primary table unless it explains a state.

Chart and table use the same loaded immutable facts. While pages remain, label
the view **More history available**; an unloaded day is neither zero nor a source
gap. Load more updates both, and a failed page preserves both. A daily aggregate
must be supplied by M05; React never sums financial rows. Do not require automatic
fetch-all to draw the chart. The complete selected-report total remains distinct
from the displayed page, and forecast inputs are selected independently by M05.
That independence concerns pagination, not identity: a forecast stays in the
selected report's financial scope/epoch and states its actual sample interval.
Current funds from a different epoch cannot supply its exhaustion date without
established compatibility. Historical rate/estimate labels remain historical.

The first chart uses existing cost/usage report history, with separate units.
Label this increment **Source entries**, not Daily total: multiple rows on one
day are not automatically additive. Keep each series within one native unit
and dimension context. M05 supplies visual magnitudes against the full pinned
report so loading another page does not resize existing bars. A non-daily source
interval remains in the exact table with its reason; do not flatten it into a
daily point. A compact plot with horizontal scrolling is sufficient; do not
turn every historical entry into a full-height dashboard row. Keyboard focus
and selection expose the exact value and interval. Daily aggregate/rate and
balance series remain distinct T013 work, with no new chart dependency.

Balance snapshots are a separate input: reuse the versioned capacity-history
query for each authorized resource/fund component, exact currency and observation
identity/time. T010/T013 must publish any missing safe selector through the
existing API before P02 consumes it; do not infer a balance time series from
spend, the current funds card or repeated page loads. Included/purchased credits
stay separate. Balance-series delivery does not block the first cost chart.
Each plotted point has the same exact observation in its accessible table;
unknown intervals remain gaps. This is a bounded history projection, not a
new financial storage system.

Usage breakdown has one source/category selector followed by one supported
dimension selector. Adapters/P01 publish the admitted combinations, native units
and availability reasons through a versioned surface before P02 enables them.
Do not infer support from a provider name or combine category measures. Changing
a selector reads stored data only; Unsupported differs from Not yet collected.
An explicit Collect action names that exact source/category/dimension/interval.
T006–T009/T013 own this handoff; T007 supplies the existing collection action.
No query builder, nested grouping or new page is required.
The API publishes an admitted nonsecret selection identity even when no report
exists. Back/reload/sign-in preserves that selection through the existing URL
allowlist. Changing category/dimension clears incompatible report/history
cursors; it never retargets a submitted collection. No dummy report ID or second
routing mechanism is needed. T007/T010/T011/T013 share this contract handoff.

For the first viewport, prioritize account/scope, state, spend/period and
available funds when known. Never show a combined Subscriptions + API capacity
percentage. With spend-only data, the main result is still a useful spend figure;
use **Remaining funds not reported** beside it, not a screen dominated by empty
budget/credit/limit cards. Funds and limit headroom use distinct labels if both
exist. Token/request totals never occupy a monetary column. These are rendering
rules for the existing sections, not additional cards or screens.

The observed-rate increment occupies one compact row in that financial section:
**Observed spending rate · [amount] [currency]/day · [sample UTC dates]**.
Its sample is independent of whether the page displays seven or thirty days;
always show the actual qualifying sample, never imply a thirty-day average.
An adjacent line shows an eligible as-of exhaustion estimate or one specific
reason. If balances exist but their allocation/scope/freshness cannot support a
date, say **Estimate unavailable — [actual reason]**, not Remaining funds not
reported. Keep the real balances visible. Expand calculation details for exact
numerator/duration, inputs and method; no new banner or separate analysis page.
When rate itself is unavailable, keep spend/history useful and show its reason
in that same row. T013/M7-MATH-03/15/16 and the existing detail-history browser
check cover this presentation; no new feature or metric is introduced.

## 5. Complete state/action table

| State | Visible message | Available action |
|---|---|---|
| No usable billing or cloud resource | API billing is not set up | Add billing connection or existing cloud setup, as published by the account capability |
| Missing credential | Credential required on the AgentMonitor computer | Copy setup command; Check connection disabled with reason |
| Queued/reading | Checking connection / Reading usage | Show progress state; prevent duplicate submission |
| Access verified, scope owner asserted | Access works; billing scope is owner-confirmed | Review scope; enable monitoring |
| No successful collection | Waiting for first reading | Collect now when server permits |
| Complete empty report | No reported usage in this interval | Change period; show source coverage |
| Provider data not available yet | Provider has not reported data for this interval | Keep last successful reading separately; scheduled retry |
| Partial data | Partial data; named missing scope/time | Show available facts, qualified subtotal and retry state |
| Refresh failure/stale | Last successful values with their original times | Try again when allowed; View collection details |
| Credential denied/expired | Credential rejected or permission missing | Replace credential locally; Check connection |
| Rate limited | Retry after server-supplied time | Disable early retry; do not busy-loop |
| Monitoring off | Monitoring off; last reading at its real time | Enable monitoring |
| Unknown mutation outcome | Connection/update result not confirmed | Reconcile status first; no automatic duplicate write |
| Disconnected/archived | Monitoring stopped; history retained | Reconnect/restore by owner; never log out provider profiles |

For archived API billing, the owner uses **Restore account**, then **Reconnect
API billing** on that account's existing connection. Reconnect retains source
identity, scope and history and leaves monitoring off. It exposes the existing
local key setup command again; it does not restore a retired key or earlier
access verification. Unknown outcomes require **Refresh billing status** before
another reconnect attempt. No automatic retry or provider request follows.

If the first report is partial, display its available exact buckets, coverage
and omissions as partial evidence, without a complete-period total. If an older
complete report exists, keep its total and history together, and show the newer
partial attempt separately; never splice their buckets. This uses the existing
detail table, not another screen. T010/T011 cover the selection/presentation
policy; a naturally absent live partial case remains Not Run.

Use existing request-generation fencing: switching accounts, replacing a key,
changing scope or archiving during a request must not apply the old response to
the new account. Scope changes create a new resource epoch; key rotation for
the same scope preserves history but invalidates old access verification.
Disconnect revokes AgentMonitor's binding. It does not revoke the upstream key;
local credential deletion is an explicit owner action and reports its outcome.

Monitoring and data quality are separate labels. Monitoring on never means
Current; Monitoring off never erases a last reading. For the main state, prefer
an actionable access/collection failure over a green historical reading; show
the last successful value/time alongside the failure. A successful access check
without usage is Access verified, not Current usage. Offline dashboard requests
retain clearly marked old values; they never silently refresh timestamps.
After a same-context Check completes or Refresh starts, keep the last successful
amount/table until its replacement GET succeeds. Replace report, amount and
history together. A failed replacement shows its error beside old values and
original times; clear retained current data for a different account/resource/scope/period or
changed/absent unresolved binding lineage. Use an opaque financial-context
discriminator from the API, not credential IDs. Old-lineage values remain
accessible only as explicitly selected historical evidence, excluded from
current totals. Apply this to funds as well as spend.
T011 specifically tests this transition, not just the initial empty/error view.

P01 assembles collection state from M04 separately from M05 report values.
Select the latest run for the displayed source, self/team scope, range and exact
interval. A seven-day success cannot refresh the thirty-day view, and a team
report cannot refresh self usage. No matching run means no collection for that
selection. Account-wide credential failures remain separately visible. T007/T010
carry the minimal typed selection; T011 never infers it from latest account activity. A
latest denied/failed run may have no stored report; it must not be hidden by a
green old complete report. Likewise, an unknown-currency latest report cannot
freshen or supply a currency for the earlier monetary value. Publish last
successful report identity/time, latest collection state/time, covered interval
and source watermark as distinct typed fields.

An expired dashboard session returns to sign-in and then the same nonsecret
account/filter URL. Do not replay a mutation after sign-in: fetch actual status
first and let the owner retry if still needed. Poll only the visible job/status
while pending, stop on navigation/unmount, and honour server retry times.
T007/P01 projects the persisted retry instant and current eligibility from M04
through the existing safe status response. Show Retry after [time/timezone] and
disable early collection; read-only status refresh remains usable. No client
invented retry interval or live countdown component is needed.

T011/T012 retain the installed allowlisted routing in
`frontend/src/app/DashboardApp.tsx` and `frontend/src/app/sessionBootstrap.ts`;
extend its remaining sign-in-return and financial-selection evidence rather
than replacing the router. Preserve only allowlisted nonsecret
organization/provider/resource/range/cutoff/sort state, the opaque financial
context and immutable report selection, and a safe return path.
Reject arbitrary return URLs; never carry credentials or replay actions. This
is a small routing correction, not a new router dependency.

The server authorizes those selectors against the account/resource and retained
scope. Overview → detail → reload/sign-in return preserves the selected report
and amount even if scheduled collection has since produced a newer report.
Explicit Refresh view replaces the selection; an expired selection uses the
existing Selection expired recovery. An unlinked account URL defaults to the
admitted seven-completed-day view. URLs carry opaque selectors, not emails,
provider scope names, financial values or credentials.

A queued action displays its actual run state until success/failure; HTTP
acceptance alone must not change the label to Connected. Concurrent edits in
another tab produce a conflict and a status reread, not last-write-wins account
configuration. Group/primary-pool attribution edits refresh rows and subtotals
from one registry revision. If metadata changes between summary and row reads,
restart that stored-data snapshot; do not show a row in its new group with a
subtotal from its old group. This never starts provider collection or rewrites
historical source identity. Duplicate clicks join/reconcile the existing operation according
to the API contract. Exercise these behaviors in T007/T011 using the real
service; do not simulate a provider failure to manufacture a UI state.

Keep three time selections distinct: the reporting interval, the read snapshot
(`as_of`), and the live action status. Check/Collect progress follows the returned
run ID through a safe status GET, including after reload; a fixed old financial
snapshot cannot show a newly completed run. Only successful completion matching
the currently selected resource, authority,
category/grouping and interval rereads financial data with a new `as_of` and the
**same reporting interval**. Replace the selected report/table together and
reset its history cursor. Failure retains prior facts and their times alongside
the failure. Completion for another selection updates that original request's
status without replacing the displayed financial selection. Do not move
the interval to a new UTC day, replay the action, or issue a second provider
read. Previous/Next move within the pinned snapshot
bound; Latest completed window selects today's completed UTC cutoff. An unrelated later
collection does not reshuffle a history page already being read. T007/T010/T011
test completion across midnight and account/scope changes within the existing
collection, HTTP and UI scenario families.

Default Check reads the admitted seven-completed-day report (cost for the first
monetary lane; Ollama uses its admitted cloud usage/balance flow). Collect now
targets the currently selected supported interval/context and says which one
will be read. Place it beside the named scope/category and UTC interval, using
server-published eligibility and retry time. An empty view needs an authorized
resource and admitted request context, never an invented report ID. When there
are multiple report contexts, each action identifies exactly one target; a
seven-day Check result is not displayed under a thirty-day
selection. Supported but not collected means No report for this interval, with
the real collection action. Unknown/unimplemented range support is named before
dispatch; changing a range or opening a detail page never starts provider work.

## 6. UI acceptance, included in tickets

Test real creation → direct detail URL/reload → local setup status → first
reading → Overview link → detail/history. Verify mixed-purpose/API-only accounts,
all listed states where naturally available, and source-to-API-to-DOM exactness.
Pure presentation rules can test label decisions; no fake network responses.

Specifically verify an account created for API billing that later has an active
subscription resource: both sections and their independent controls must appear.
The `edbe2fc` increment adds the derived resource-presence field and passes pure
routing, genuine registry/API and installed subscription-page checks; see
[bounded evidence](../../evidence/m7-account-resource-layout-2026-11-12.md).
No live owner API-origin account was reconfigured to induce a new subscription
transition. Keep that observation distinct from the composed policy/producer/UI
coverage; this increment does not close all account lifecycle acceptance. Use authoritative published resource/capability state,
with creation intent only for the pending fallback. If a minimal additive API
classification is needed, synchronize M02/P01 before its P02 consumer. Exercise
metadata transitions on an isolated genuine registry copy; do not enroll or
reconfigure the owner's accounts to create this test. Also retain the explicit
Organization unavailable state for assigned groups whose names did not load.

Account and organization choices must include later pages. Pending/disabled
records remain findable; filters never silently drop them. An unrequested or
failed organization page means unavailable name, not Ungrouped. Show counts and
pagination; preserve filters on return from detail and ordinary reload using
nonsecret URL state. Never persist keys/tokens there.

Check 1920×1080, 1366×768 and 768px layouts, keyboard focus, 200% zoom, status
text alongside color, exact chart table, small positive money, long names,
loading/error/empty views and LAN clipboard fallback. At narrow widths prioritize
account, organization, state and spend; other details can expand. No invisible
required controls or horizontal page-wide overflow.

Pre-implementation source seams inspected: `AccountPage.tsx` routed every Claude/Codex
account to subscription controls; `AccountQuotaOverview.tsx` owns private filter
state and requested first-page account lists; `OllamaCloudConnectionView.tsx`
already fences stale responses; `OllamaCloudConnectionPanel.tsx` supplies a
local-only key setup pattern. Source inspection is not a rendered-browser pass.
The metadata increment at `f21e367` adds creation/attach controls but does not
close the capability routing, full setup or monitoring journey described here.
