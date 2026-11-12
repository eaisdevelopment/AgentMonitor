# M7 delivery worksheet: remaining work and fixed finish line

Status: delivery clarification within approved focused plan 1.1.0, reviewed
12 November 2026. Primary owner: root integration; financial semantics: M05.
No new feature, ticket, approval or completion gate.

The [catalog](m7-ticket-catalog-v1.json) is the only task tracker: **16 tickets,
five stories, M7-A01..A10**. This worksheet owns order and the recorded installed
checkpoint. The [UI plan](m7-ui-and-user-journeys.md) owns screen behavior; the
[calculation rules](m7-calculation-and-data-rules.md) own financial meaning;
the [M05 increment](../modules/m05-capacity/m7-budget-increment-2026-11-11.md)
owns contract handoffs. Historical reviews are in
[planning evidence](../../evidence/m7-planning-recheck-2026-11-12.md).
Link to those decisions rather than maintaining competing copies here.

## Read this first: next result and finish line

**Next independent delivery:** the first-source history chart and rate-only
calculation in T013. Billing disconnect/local cleanup and status-to-financial
refresh are installed and published at `d985cc7`; their
[evidence](../../evidence/m7-billing-maintenance-2026-11-12.md) records 95 registry
tests, isolated SQLite/PTY/browser Red/Green, local quality and concurrent
authenticated installed checks. Real active-key rotation/deletion evidence
is separate and waits only for its actual credential, not all independent work.
The archive/restore reconnect
path is installed at `c1c8e8d`: it retains source/history metadata, keeps
monitoring off and requires new key setup/access verification. Its
[evidence](../../evidence/m7-billing-reconnect-2026-11-12.md) distinguishes the
actual isolated browser journey from read-only installed checks and unperformed
secret deletion/replacement. Retained report discovery is installed at `540ab8b`; its
[evidence](../../evidence/m7-source-history-2026-11-12.md) records genuine HTTP,
built-browser and installed checks, with original scope labels and historical
collection guards. Preserve this delivered path. Scope editing
is installed and published at `71185cf`; its [evidence](../../evidence/m7-billing-scope-edit-2026-11-12.md)
records real HTTP/registry/built-browser Green and installed read-only checks.
Retain that increment, including pool refresh and the historical-selection
collection guard; do not restart scope editing, routing or concurrent-read fixes.

**Highest-priority demonstration when access exists:** one genuine monetary
report, with identical scope, period, currency, cost basis and exact amount in
storage, API, installed Overview and account detail. Ollama counts/balances do
not replace that proof. All remaining categories, charts and forecasts must not
delay this first monetary journey. The existing monetary-setup request remains
pending; missing access pauses its live assertions only.

| Owner-visible checkpoint | Usable result | Remaining after it |
|---|---|---|
| Working money journey | Owner setup → actual cost → Overview → detail → exact history | Remaining frozen provider coverage, lifecycle and analysis |
| Complete M7 screens | Required providers, truthful totals/states, scope/history controls, chart, supported breakdown, forecast or real unavailable reason | Final candidate recovery/continuity and reconciliation |
| Released M7 | Fixed exit passes on the installed candidate, GitHub revision verified, demonstrated result accepted | Explicitly deferred improvements |

These are demonstrations, not extra gates. Ticket dependencies constrain
closure, not permission to begin independent work. Existing approval remains
valid. No repeated owner account attestations or new plan-version ceremony.

## 1. Verified starting point

| Boundary | Recorded result | Still unproved |
|---|---|---|
| Installed implementation | `d985cc7`, schema `v1_0734`; local billing disconnect/cleanup and status-to-financial refresh, restored-account billing reconnect, retained Source history, scope-edit controls with authority/pool/history fences, resource-based account sections, organization pagination, pool controls, fair 7/30-day scheduling, manual collection, sorted Overview and pinned daily history | Full monetary journey and complete lifecycle/analysis |
| Public code | GitHub implementation `d985cc7`, independently verified | Later documentation-only receipts do not change installed code |
| Live reports | Genuine Ollama balances/counts, one manual 30-day report and scheduled 30-day reports on two real resources | Seven-day manual success remained rate-limited before POST; monetary reports and remaining provider matrix |
| Browser reliability | Actual installed concurrent Overview/setup/cloud reads passed; isolated real owner metadata covered pool controls, later organization pages and full-list sorting | Monetary totals, full accessibility and final acceptance |
| Source access | Read-only installed inventory at 08:11:53 UTC, 12 November: zero Anthropic/OpenAI billing connections, stored bindings or enabled billing connections | Subscription logins do not prove billing access; absence is not a provider denial |
| Tracker | 2 done, 11 in progress, 3 planned | Counts are not percentage complete |

Evidence: [resource layout](../../evidence/m7-account-resource-layout-2026-11-12.md),
[concurrent reads](../../evidence/m7-overview-query-reliability-2026-11-12.md),
[pools](../../evidence/m7-financial-pools-2026-11-12.md),
[scheduling](../../evidence/m7-fair-financial-scheduling-2026-11-12.md),
[manual cloud usage](../../evidence/m7-cloud-manual-collection-2026-11-12.md),
[manual billing controls](../../evidence/m7-manual-collection-2026-11-12.md),
[stored history windows](../../evidence/m7-window-navigation-2026-11-12.md).
These are bounded historical results, not a fresh runtime check or full M7 pass.

## 2. One remaining delivery sequence

Retain the following eight batches inside the existing tickets. Their numbers
identify work, not strict serial prerequisites. The batch 3 maintenance candidate
is installed; retain its evidence. Batch 2 takes priority as soon as monetary
access is ready. Otherwise start batch 6's pure rate/daily-chart work using existing
history contracts, alongside available batch 1/4 provider verification. Batch 5
travels with every visible increment, not a late UI cleanup phase. Complete
batch 7's recovery with the first genuine money, then batch 8. No need to finish
every provider before implementing a chart or to finish a forecast before
showing the first cost. Root serializes shared contracts, integration and
installation, with one integration packet in flight. Each increment includes its own
Red/Green, actual check wiring and visible installed result where applicable.

| Batch / tickets | Smallest remaining deliverable | Acceptance edge / exact dependency |
|---|---|---|
| 1 — T007/T009/T011 | Finish seven-day manual cloud proof when eligible and original-request/context recovery | Actual action/run/report linkage, reload and no duplicate request; retain installed 30-day proof, balance and shared cooldown. No owner setup repetition |
| 2 — T005/T006 or T008/T010–T012/T014 | First monetary source through exact storage, Overview, detail and history | One complete genuine report survives commit/retry/reopen and matches authenticated API/DOM at the same context. Needs actual admitted billing access, not completion of every provider ticket |
| 3 — T002/T010/T011 | Retain installed scope editing, report discovery, reconnect and local disconnect/cleanup; finish real rotation/deletion evidence | Old authority cannot commit; group-only edits preserve access; historic scope label survives reload; historical-scope Collect disabled and return-to-current works. Real isolated metadata tests are separate from populated history and actual secret-removal evidence |
| 4 — T006/T007/T008/T009 | Finish frozen endpoints, both ranges, supported dimensions and bounded fairness/recovery | Each mapping has its native unit/coverage and actual source result. Unsupported, denied, unimplemented and genuine empty success remain distinct. No new provider API additions |
| 5 — T004/T010/T011/T012 | Finish totals, navigation, refresh failure and accessibility | Compatible full-filter subtotal, one shared pool, no false zero, source/API/DOM exactness, keyboard/zoom/widths, preserved quota rows on financial error; retain delivered server sorting/concurrent-read fix |
| 6 — T013 | Same-fact daily chart, one supported dimension at a time, observed-rate/conditional exhaustion and retention | Uses existing history, backend math and existing retention scheduler. No generic analytics engine. Missing funds can prevent a date without hiding a valid observed rate |
| 7 — T003/T014/T015 | Bounded financial recovery, installed continuity and fixed-inventory reconciliation | Real isolated restore, current selected update, browser-closed collection and existing provider/alert continuity; reuse original source facts without relabelling them newly observed |
| 8 — T016 | Corrected clean candidate, existing full exit, publication and demonstration | Mandatory checks pass at installed revision, remote revision verified, owner accepts demonstrated scope. A failed correction reruns affected checks and the aggregate, not unrelated owner confirmations |

### Concrete work packets and acceptance edges

The catalog's existing `steps` are the executable work breakdown. Per packet:
identify owner/contracts → meaningful behavioral Red → minimum producer and
consumer change → actual Green → existing check selector → installed demonstration
when applicable. A missing selector is implementation work in T003, never a new
owner prerequisite. Do not leave finished work in progress solely because the
whole milestone is unfinished; close only against that ticket's full boundary.

Use the catalog's existing steps as the task list, not another backlog. Before
starting a packet, state its ticket IDs, concrete screen/result, actual input
dependency and exact relevant test. Finish that packet through its integrated
result before starting another integration packet. Parallel module work may
prepare independent, nonoverlapping changes; it does not multiply releases or
owner setup requests. Eleven tickets marked in progress describe incomplete
scope, not eleven simultaneous priorities.

| Start work with | Required before claiming that result | Existing owner / tickets |
|---|---|---|
| Installed maintenance controls | Retain quality/install/browser evidence; actual active-key deletion/rotation only when real credentials are available | M02/P01/P02, T002/T011/T014 |
| One successful admitted monetary report, even if its adapter ticket is incomplete | Exact same report/context in storage, HTTP, Overview, detail and history; genuine evidence, no mock balance | M05/P01/P02, T005/T010–T012/T014 |
| Current immutable history contracts plus pure domain inputs | Same-fact chart, exact daily aggregation and rate tests; monetary browser proof once a genuine report exists | M05/P01/P02, T013 |
| Each frozen provider's existing source contract | Complete required mapping/access/range inventory for that provider; other providers do not block its implementation | A01/A02/A03/M04, T006–T009 |
| Genuine retained financial data | Isolated receipt recovery/backup/restore and installed continuity, then final reconciliation | M04/M05/M08, T007/T014/T015 |

The known external setup dependency for the first monetary demonstration is
genuine admitted Anthropic or OpenAI billing access. The recorded
inventory is absent setup, not an observed permission denial. The owner uses
the existing dashboard/local key-entry flow; the agent does not create accounts,
change groups or enable monitoring on the owner's behalf. Report an exact
failed action if access is denied later. Do not assume that condition now or
repeat the pending setup request while independent work remains.

### Fair scheduling: narrowed implementation decision

Retain the installed single worker, persisted due/attempt age and stable ties;
no new queue, cursor table or concurrency setting. T007's finite remaining proof:

- Pure repeated-selection case: for a fixed set of N eligible contexts, updating
  the chosen context's service age must visit every context before any member is
  chosen again while an older eligible member remains. Exercise two rounds and
  newer queued arrivals, with manual/scheduled, provider and 7/30-day contexts.
- An eligible opportunity means the existing authority, due-time and shared
  cooldown rules permit a claim. Busy/cooldown/ineligible work is not a missed
  service opportunity; this is not a wall-clock or fifteen-minute guarantee.
- Real integration: preserve original intent and service age across successive
  claims/reopen; observe naturally due work for later real resources and both
  ranges while earlier contexts become eligible again or receive newer queued work.
  Record the finite eligible set and resulting run order. Do not create provider
  traffic merely to meet a repetition count; genuine 30-day evidence already
  exists, and missing seven-day/recovery evidence remains explicit.

Source request budgets include pages, balance jobs and every automatic category,
not merely report count. Measure actual eligible service intervals and disclose
lag; do not promise every category refreshes every fifteen minutes or add workers
to bypass source limits. Exact collection rules stay in calculation section 7.

### Completion checks travel with the feature

| Batch | Existing check names to finish with the feature | Proof, not a placeholder pass |
|---|---|---|
| 1 | `collection`, `ollama`, `detail_history` | Genuine usage/run/report and original-context controls |
| 2 | `persistence`, `budget_http`, `anthropic` or `openai`, `detail_history` | Monetary source → atomic commit/reopen → HTTP → built table |
| 3 | `registry_http`, `owner_setup`, `collection` | Authority fences, history labels and owner lifecycle controls |
| 4 | `anthropic`, `openai`, `ollama`, `configured_inventory`, `recovery` | Frozen mapping/range inventory, fair dispatch and receipt recovery |
| 5 | `pure`, `mutation`, `budget_http`, `overview`, `accessibility` | Exact total/state, navigation, quota isolation, keyboard/zoom/widths |
| 6 | Extend `pure`, `mutation`, `persistence`, `budget_http`, `detail_history` | Same facts for table/chart, breakdown, forecast availability, retention |
| 7 | `compatibility`, `candidate`, `backup_recovery`, `installed_revision`, `continuity` | Same-schema selected update, real restore, actual installed continuity |
| 8 | Aggregate `exit` | All mandatory results and unchanged relevant inventory at the selected candidate |

Callable now on `python3 -m tools.automation.implementations.auto_m7` with its
admitted tool context: `--lane pure`, `mutation`, `registry_metadata`,
`persistence_schema`; `--lane technical --check collection_guards` or
`budget_http_guards`; `--lane browser --check owner_pool_controls`. The new
`--lane browser --check source_history` runs genuine retained-report HTTP and
built-browser discovery in isolation; full monetary/detail-history acceptance
remains separate.
`--lane browser --check overview --expected-revision=<installed-40SHA>` runs
bounded genuine metadata/concurrent installed reads but exits nonzero while
full monetary Overview remains Not Run. Other names above are **planned
selectors**, not runnable commands. Existing AUTO-M7-TEST/LIVE/BROWSER/DEPLOY/EXIT
entry points remain fail-closed. T003 extends them; no second runner/registry.
Commands owning temporary tool links run serially; app reads remain concurrent.

### Contract handoffs before each increment

Retain installed CTR-COL-002 2.6.0 collection context/status, CTR-CAP-006 2.7.0
Overview and 2.8.0 history, CTR-REG-014 1.5.0 pool/monitoring metadata and
CTR-REG-002 1.1.0 resource presence. Scope editing is installed under
CTR-REG-014 1.6.0; its evidence is linked above. Retained-report discovery is installed under CTR-CAP-006 2.9.0
([evidence](../../evidence/m7-source-history-2026-11-12.md)). Remaining additive handoffs:

- M02/P01/P02: retain installed scope/reconnect controls and prior-scope discovery;
  remaining lifecycle actions invalidate current authority without rewriting
  original reports. Extend their existing monetary/lifecycle evidence.
- M05/P01: source-reported limits are distinct from headroom derived using a
  compatible report; publish input lineage before deriving it. Spend/history
  does not wait for an unavailable balance endpoint.
- Adapters/M04/P01/P02: admitted category/dimension/interval selection exists
  even before a report. Reuse the current action, status and route allowlist;
  selection changes never retarget an in-flight request.
- M05/P01/P02: cost/usage chart uses existing immutable report history; separate
  balance series reuses authorized capacity observations through the versioned
  history API, never spend or a current card. Preserve source/component identity
  and add only missing snapshot selectors. Rejected daily-history cursors restart
  the same report from page one; they do not mean that report was deleted.
  Forecast/breakdown
  fields carry scope, units, inputs and reasons. No React financial aggregation,
  forecast storage, interval-stitching engine or new dependency.

Root synchronizes public types and generated client before consumers; private
table imports are not a shortcut. The owning module plan records exact changed
versions, files and tests. Historical migrations `0720→0731→0733→0734` remain
immutable installed history, not actions to repeat.

## 3. Ticket-level remaining work

The [catalog](m7-ticket-catalog-v1.json) already gives all sixteen IDs, owners,
requirements, acceptance IDs, dependency edges, steps, expected Red, verification
and evidence. Use its `status` and `done_when`; do not maintain another ticket
status table here. T001/T004 are done within their own scope. T005 and provider
success cannot close from schema/guards/pure math; T013 remains required.

## 4. Small UI contract, decided before coding

[UI sections 2–6](m7-ui-and-user-journeys.md) own the complete state/action and
browser matrix. Existing pages and controls are enough:

| Location | First useful content | Interaction that must work |
|---|---|---|
| Overview | Shared organization/provider/resource filters; separate quota and API rows; spend/available/state/period plus compatible subtotals | Sort before paging, actual resource/report link, Back/reload, financial error leaves quotas usable |
| Account detail | Name, dashboard group and provider scope; actual spend/funds with their distinct dates | Financial link focuses financial content; compact connection disclosure; stored Refresh differs from provider Collect |
| Manage connection | Actual credential/access/monitoring state and only the missing step | Owner local entry, check, enable, scope edit, rotate/disconnect/archive; no opaque IDs to type or browser secrets |
| History/analysis | Exact pinned table before chart/breakdown/forecast | Original-scope label, paging and fixed-window navigation, expired-selection recovery; old-scope collection disabled |

Preserve promotion/support/footer and the existing 24-hour session/LAN behavior.
No large status banner, added top-level page or Overview collection-log panel.
A failed refresh keeps only compatible old values with their original times.
A successful matching Collect advances the read snapshot, not the reporting
interval; another selection's completion does not replace the current view.
Check 1920×1080, 1366×768, 768px, keyboard and 200% zoom using the existing browser.

## 5. Calculation rules that prevent misleading dashboards

[Calculation sections 1–9](m7-calculation-and-data-rules.md) and M7-MATH-01..16
are authoritative. Retain exact decimals; reported spend, cash, credits and
soft/hard-limit headroom are different quantities. Only compatible complete
scope/period/currency/basis totals combine; known shared pools count once.
Missing/denied/counts-only is not monetary zero. Exact remaining ≤20% controls
low state only with a valid denominator; a non-constraining empty component
is not whole-account exhaustion.

Direct exact-period 7/30-day reports satisfy the initial product. Do not build
a general interval assembler. History is daily facts from a pinned report, not
summed polls. Forecast needs qualified monetary history; a date additionally
needs compatible positive funds, freshness and allocation. Historical selection
pins financial identity even when its forecast sample spans other pages.
No balance changes used as burn, local token pricing, invented Other or FX.

## 6. Verification and fixed acceptance

The [M7-A01..A10 table](m7-execution-plan-2026-11-11.md#7-fixed-completion-catalog)
is unchanged. Required Anthropic/OpenAI cost and supported usage success plus
Ollama usage/balance continuity remain mandatory. Genuine empty success is
separate from a populated-example test; naturally absent numeric forecasts,
corrections or provider errors retain their conditional non-pass disposition.
Neither absent implementation nor denied mandatory access is optional.

### Finite recovery demonstrations (T007/T014)

| Case | Required actual boundary | Reuse / extension point |
|---|---|---|
| Expired queued work | Existing real admission, expiry and safe release; another eligible target can proceed | M04 `test_billing_action_admission.py` and dispatch integration family; extend for the missing case |
| Uncertain dispatched work | Live-owner/authority fence prevents replay; abandoned outcome remains unknown and respects cooldown | Existing M04 recovery policy and real supervisor tests; genuine abandoned-state test is conditional on that state, never manufactured provider success |
| Interrupted commit | In isolated storage, persist a genuine report/receipt, stop before finalization, then invoke normal recovery; reopen reconciles the receipt without duplicate facts or recollection | T005 populated persistence + T007 budget-run recovery; existing non-budget recovery tests alone do not prove this |
| Backup/restore | Secret-excluding backup of genuine financial storage restores to isolated real SQLite; report IDs/amounts/coverage survive, absent key is Credential required | Existing selected-release/backup helpers, extended monetary assertions; never restore over live writes |
| Installed continuity | Selected same-schema update, authenticated concurrent dashboard, browser-closed scheduled collection and existing Claude/Codex/Ollama/alerts continue | Existing installed probes, selected update/recovery helpers and real collection timestamps; do not restart user agents |

These are the recovery acceptance edges, not a general disaster-test program.
Reuse existing helpers; name missing tests as planned until they execute. Tests
for naturally absent external outcomes retain their conditional non-pass status.
Required controlled local receipt/recovery/restore demonstrations must execute
using genuine reports in isolated storage; they do not wait for a provider to
fail naturally and never substitute fabricated telemetry.

### Fixed candidate and inventory (T015/T016)

At final reconciliation select one clean candidate and capture the real registry
inventory revision plus relevant account/resource/scope/binding generation,
monitoring and pool attribution through published queries. Account for each
active financial resource; pending/disabled records remain visibly classified.
At the final aggregate compare that relevant configuration again. A change
requires checks for affected resources and refreshed aggregate inventory only;
unchanged resources retain their valid evidence. Unrelated registry updates or
normal telemetry arrival do not invalidate everything. No manual account-code
list, owner configuration freeze or second inventory store.

Keep source observation time distinct from candidate verification time. A current
candidate can requery an immutable genuine report and compare its API/DOM value
with its original authoritative evidence; this does not claim newly observed
provider data. Live scheduling/freshness checks still need their actual current
outcomes. A changed parser, scope or financial rule invalidates its affected
comparison; a docs-only edit does not demand owner login or a new attestation.

The existing final receipt binds clean source/installed revision/schema, check
name/outcome/time, required/conditional disposition and sanitized evidence
references. Missing mandatory checks prevent pass. Publication follows this
candidate check and remote verification follows publication; GitLab mirror auth
cannot block the authorized GitHub result. Acceptance is the demonstrated scope,
not another mechanical terminal-input ceremony.

## 7. Scope, risks and delivery control

| Risk | Smallest response within existing tickets |
|---|---|
| Missing/denied billing access | State actual provider/action/result once; use the existing tested owner setup flow and continue independent work |
| No funds/limit/source watermark | Show spend and precise missing reason; no scraping, guessed percentage or guaranteed stop date |
| Corrected/late/empty data or changed scope | Preserve report lineage, original scope/time and coverage; do not freshen or splice old money |
| Duplicate pools, later pages, concurrent metadata | Complete filtered snapshot, canonical attribution, cursor conflict recovery; no client fetch-all |
| Minimum report exceeds limits | Retain previous complete data; disclose measured size/time bound and smallest supported interval; no speculative job engine |
| Failed upgrade | Inspect revision/schema/journal and preserve new writes before tested recovery; no blind migration replay/restore |

The provider matrix in [execution-plan section 1](m7-execution-plan-2026-11-11.md#finite-provider-coverage-for-this-milestone)
is frozen. Future endpoints, local Ollama, user-set budgets, FX/tax/invoices,
price estimates, new alerts, custom multi-dimension reports, statistical
forecasting, remote secret entry and general deployment machinery remain deferred.
A later finding must identify an existing requirement, actual failing boundary
and smallest correction; preference/cleanup does not become a release condition.
Required chart, supported single-dimension breakdown and conditional forecast
remain in M7. Simplification removes machinery, not these outcomes.

No new owner action is required for this planning review. Owner-controlled
configuration remains owner-controlled; agent handles code, tests, routine
commands and installation already authorized. Report each integrated result
with its URL, ticket IDs, verified local/committed/installed/public state,
remaining failure and next visible result. Avoid backend-only accumulation.

The historical 7–12 engineering-day estimate is not a renewed deadline. After the
first genuine monetary journey, estimate only remaining batches using measured
work; report engineering time separately from provider/owner wait. Two sessions
without a visible increment trigger inspection of the dependency and a smaller
implementation inside the same scope, not added infrastructure or another plan.
Finish means all sixteen ticket outcomes and M7-A01..A10 have their required
evidence, full exit passes at the installed candidate, GitHub matches and the
owner accepts. Planning validation alone establishes none of those outcomes.
