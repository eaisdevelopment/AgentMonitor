# M7 UI and user journeys

- Status: Approved under focused M7 plan 1.1.0; setup metadata UI is partially implemented, the full live journey remains unfinished.
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

API usage & spend    Period [Last 7 days]     [Refresh readings]
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
Provider-reported scope and dashboard organization are separately named.
An account connected to a whole provider organization does not imply all its
spend belongs to that individual email or one running agent.

Default API sort: action needed (denied/setup/failure/stale/partial), then known
depletion or low remaining capacity, then organization/name/stable ID. Unknown
remaining capacity is not exhausted. Column headings support organization,
state and account sorting. Monetary sorting is offered only inside one
compatible currency/period/basis group; it never compares USD and GBP values.

Remaining percentages/bars appear only with a valid matching denominator.
Red means remaining **≤20%**, or explicitly reported depletion/exceeded hard
limit. Show the raw percentage plus a bounded visual bar and text, never just
color. A high remaining percentage is not low capacity. A cash balance without
a cap shows money, not a made-up percent. No automatic red threshold for spend.

FR-ORG-003 requires organization/global summaries: render compact grouped
reported-spend totals by currency, exact coverage period and source cost basis.
Never one mixed-currency grand total. Label included/excluded scope counts;
unresolved overlap or incomplete inputs produce a clearly labeled partial
subtotal or no total. Totals cover the filtered set, not merely the loaded page.
Use server-calculated summaries; no money aggregation in React.

**Refresh readings** rereads stored API data only. It does not make all accounts
call their providers. Detail offers the separate **Collect now** action with
server cooldown. One failed API budget request must leave quota rows usable.

## 4. Account detail: useful information first

At the top: owner account name, provider product, dashboard organization,
provider billing scope, current state, report interval and data-through time.
The connection status is one compact line with **Manage connection** expandable;
setup details expand automatically only when action is required.

| Section | Required content and behavior |
|---|---|
| Usage & spend | Reported spend; available balance; prepaid credits; soft budget; hard limit; actual billing/renewal period when exposed. Missing fields have a short reason, not empty cards or zero. Show source cost basis such as before credits |
| Usage breakdown | One supported dimension at a time: project/workspace, safe key identifier, model, token category or time. Separate money, tokens and requests. Do not fabricate a join between cost and usage reports. Include Other/Unallocated and coverage when reported |
| Forecast | Derived rate/as-of estimate with assumptions, or precise reason: no limit/balance, insufficient history, scope mismatch, delayed data or corrections. Not a promise that service will stop at that time |
| History | Bounded period, exact table and then simple chart from the same API facts. Spending per day uses bars; balance snapshots use separate series. Missing intervals are gaps; corrections retain lineage. Load more does not discard earlier rows if a later page fails |
| Source details | Collapsed: source/version, checked/data-through times, exact value, precision, observed/derived meaning, report coverage, omissions and inputs |
| Settings | Rename, move group, API monitoring on/off, replace key, disconnect/archive. Existing subscription monitoring remains independent |

The first history table is daily buckets from the pinned selected complete
report: period, exact amount/currency, coverage and report provenance. The
existing `list_reports` query returns revisions of an exact interval; it is not
a daily-spend series. Keep revisions in expandable source history. The first
visible increment may render bounded daily buckets already returned with the
selected immutable report by the current GET; this is now locally tested for
the empty state. It must not fetch every report revision or claim server
pagination from local Load more. T010/T011 closure still requires the dedicated
bounded financial history query, authorized report selection and cursor/expiry
behavior. This does not delay showing the first genuine money in the existing
table or permit closing those tickets early. The new
financial detail identity resolves to the canonical billing resource; each
current financial context supplies its immutable report ID. History and its
pages stay on that report until explicit refresh. If retention removed it,
show Selection expired with Refresh, rather than silently changing the numbers. T013 uses
those same buckets for its chart. When the UTC cutoff moves, preserve the
selected query until explicit refresh; never concatenate overlapping reports
to fill missing days. A provider without daily buckets shows its actual
aggregate interval, with daily history unavailable.

Start with the exact table in the first usable slice; chart and forecast arrive
in the later M7 enhancement slice. They are still required before M7 closes.
Keep source/diagnostic detail out of the primary table unless it explains a state.

For the first viewport, prioritize account/scope, state, spend/period and
available funds when known. Never show a combined Subscriptions + API capacity
percentage. With spend-only data, the main result is still a useful spend figure;
use **Remaining funds not reported** beside it, not a screen dominated by empty
budget/credit/limit cards. Funds and limit headroom use distinct labels if both
exist. Token/request totals never occupy a monetary column. These are rendering
rules for the existing sections, not additional cards or screens.

## 5. Complete state/action table

| State | Visible message | Available action |
|---|---|---|
| No billing binding | API billing is not set up | Add billing connection |
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

P01 assembles collection state from M04 separately from M05 report values. A
latest denied/failed run may have no stored report; it must not be hidden by a
green old complete report. Likewise, an unknown-currency latest report cannot
freshen or supply a currency for the earlier monetary value. Publish last
successful report identity/time, latest collection state/time, covered interval
and source watermark as distinct typed fields.

An expired dashboard session returns to sign-in and then the same nonsecret
account/filter URL. Do not replay a mutation after sign-in: fetch actual status
first and let the owner retry if still needed. Poll only the visible job/status
while pending, stop on navigation/unmount, and honour server retry times.

T011/T012 include the existing shell files `frontend/src/app/DashboardApp.tsx`
and `frontend/src/app/sessionBootstrap.ts`: the current shell strips query
parameters and expires to `/login`. Preserve only allowlisted nonsecret
organization/provider/resource/range/cutoff/sort state and a safe return path.
Reject arbitrary return URLs; never carry credentials or replay actions. This
is a small routing correction, not a new router dependency.

A queued action displays its actual run state until success/failure; HTTP
acceptance alone must not change the label to Connected. Concurrent edits in
another tab produce a conflict and a status reread, not last-write-wins account
configuration. Duplicate clicks join/reconcile the existing operation according
to the API contract. Exercise these behaviors in T007/T011 using the real
service; do not simulate a provider failure to manufacture a UI state.

Keep three time selections distinct: the reporting interval, the read snapshot
(`as_of`), and the live action status. Check/Collect progress follows the returned
run ID through a safe status GET, including after reload; a fixed old financial
snapshot cannot show a newly completed run. On terminal status, reread stored
financial data with a new `as_of` but the **same reporting interval**. Replace
the selected report/table together and reset its history cursor. Do not move
the interval to a new UTC day, replay the action, or issue a second provider
read. Explicit range refresh may advance the UTC cutoff. An unrelated later
collection does not reshuffle a history page already being read. T007/T010/T011
test completion across midnight and account/scope changes within the existing
collection, HTTP and UI scenario families.

Default Check reads the admitted seven-completed-day report (cost for the first
monetary lane; Ollama uses its admitted cloud usage/balance flow). Collect now
targets the currently selected supported interval/context and says which one
will be read; a seven-day Check result is not displayed under a thirty-day
selection. Supported but not collected means No report for this interval, with
the real collection action. Unknown/unimplemented range support is named before
dispatch; changing a range or opening a detail page never starts provider work.

## 6. UI acceptance, included in tickets

Test real creation → direct detail URL/reload → local setup status → first
reading → Overview link → detail/history. Verify mixed-purpose/API-only accounts,
all listed states where naturally available, and source-to-API-to-DOM exactness.
Pure presentation rules can test label decisions; no fake network responses.

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
