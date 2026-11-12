# M7 delivery worksheet: remaining work and fixed finish line

Status: execution clarification within approved focused plan 1.1.0, reviewed
against committed and installed `93297fc` on 11 November 2026
(schema `v1_0733`). Primary owner: root integration; financial owner:
M05. No new milestone, approval, dependency or completion gate.

The [ticket catalog](m7-ticket-catalog-v1.json) remains the only task tracker:
16 stable tickets, five stories, M7-A01..A10. This worksheet specifies delivery
order and cross-module handoffs. The [UI plan](m7-ui-and-user-journeys.md) owns
screen behavior; [calculation rules](m7-calculation-and-data-rules.md) own money
semantics. Historical findings remain in [review evidence](../../evidence/m7-plan-refactor-2026-11-11.md).

## 1. Verified starting point

| Boundary | Evidence at this review | Still unfinished |
|---|---|---|
| Committed implementation | `93297fc`: financial Overview/shared filters, exact immutable report links, funds lineage and guarded update correction | Canonical pool totals, real monetary report, full provider/scheduling/history/analysis coverage |
| Installed dashboard | `93297fc`, schema `v1_0733`; authenticated Overview/API/DOM, exact report navigation, Back/reload and 1920/1366/768 widths passed | Remaining keyboard/zoom checks and complete M7 monetary/analysis experience |
| Existing setup | Authenticated setup surface verified; two existing cloud accounts have real funds and daily usage | Read-only inventory confirmed no Anthropic/OpenAI billing enrollment. Owner asked once to use the tested setup; absence of enrollment does not prove denied access |
| Deployment | Same-schema update succeeded; loopback/LAN HTTP200, original restart policy restored; real disposable stop/update regression passed | Full financial scheduling, recovery and final M7 acceptance; do not rerun the initial migration |
| Candidate verification | Local quality/build, exact timestamp Red/Green, real current Overview browser pass; earlier funds/usage tests cover two accounts and fourteen daily buckets | Demonstrated usage contains counts, not monetary spend; no implementation ticket closes from this increment alone |
| Publication | Local committed and installed revisions verified | No new remote-publication claim |

Earlier Overview update attempts stopped safely. The closed diagnostic exposed
`unit_has_children_or_not_stopped`; a real disposable regression reproduced a
frozen parent's inability to reap a short-lived child. The bounded resume/recheck
correction preserves final child-free proof and long-child refusal. Its checked
update succeeded. No database restore, credential/account configuration or user
agent interruption was performed. See [candidate and installed evidence](../../evidence/m7-financial-overview-2026-11-11.md)
and [deployment correction](../../evidence/m7-financial-cutover-diagnostics-2026-11-11.md).

Evidence: [installed funds](../../evidence/m7-stored-funds-2026-11-11.md),
[cloud authority and current-query gap](../../evidence/m7-cloud-usage-authority-2026-11-11.md),
[current cloud usage runtime](../../evidence/m7-cloud-usage-runtime-2026-11-11.md),
[financial installation](../../evidence/m7-financial-installed-2026-11-11.md).
Installed funds are real delivery, but not a usage/spend report. One planning
ticket is done; twelve implementation tickets are in progress and three planned.
These counts are tracker state, not percentage complete or elapsed-time estimates.
No implementation ticket closes through this review.

## 2. Ordered delivery, with an observable result at every checkpoint

### Execution order from the current checkpoint

The six rows below remain the delivery sequence, not six new work streams.
Foundations and funds/usage screens already demonstrated are retained. **Next:
finish the owner pool controls and totals, and connect one genuine monetary
report to the existing screen.** These are independent visible results: show
whichever works first. Genuine spending does not wait for completed totals,
charts or the second provider. Do not restart setup or redesign the shell.

Work on one integration packet at a time, with independent provider/pure-test
work only where its contracts are stable. Twelve `in_progress` tickets record
partial implementation, not twelve simultaneous priorities. T003 verification
wiring and T014 deployment accompany the feature being delivered; they are not
separate infrastructure projects. End each packet with its stated demonstration
or identify the exact failing boundary and continue other authorized work.

A ticket's dependency is its **closure** prerequisite, not a blanket prohibition
on independent implementation. Pending provider access does not stop pool
metadata, exact calculations, history or UI work. No new account list, repeated
owner attestation or new plan approval is needed for routine work in this scope.

| Order | Existing tickets / owner | Work to finish | Demonstration that ends the increment |
|---|---|---|---|
| 1. Installed collection prerequisite — operational checks passed | T014 root; T003 verification wiring | Storage/worker activated at schema0733; later funds build14dee16 and authenticated setup verified. Complete collector continuity and financial recovery proof with later integration | Correct installed revision/schema and authenticated controls demonstrated. This partial deployment does not close T014 |
| 2. First real financial journey | T002/T005/T007 + first available T006/T008/T009; M02/M04/M05/provider/root | Existing or newly owner-configured connection; genuine bounded read; exact atomic report/reopen; positive enable/disable | One real account shows provider scope, interval, amount/currency, source time and useful access state. Check success is backed by its actual stored report |
| 3. First useful dashboard | T010/T011/T012 + T014; M05/P01/P02/root | Compact current/summary DTOs, supported funds, pinned history, Overview/shared filters, navigation and installed verification | Same report and exact amount in account/detail/history/Overview; group selection and Back/reload work; failed refresh retains prior value |
| 4. Finish provider coverage | Remaining T006/T008/T009 + T007 | Wire remaining providers, finite usage categories, thirty-day and pinned report intents, shared scope rate limits | Anthropic/OpenAI/Ollama use the same screens with explicit category/field coverage; all active resources accounted for |
| 5. Finish the analysis already promised | T013 with T010/T011 | One supported dimension, daily bars plus exact table, separate balance series, simple observed-rate forecast or precise unavailable reason | Chart/table reconcile to the selected reports; no invented balance, attribution or stop date |
| 6. Release and close | T015/T016; root | Fixed source/API/DOM comparison matrix, real recovery/continuity, bounded review, full executable exit, publication and demonstration | Installed and GitHub revisions verified; required checks pass; owner accepts the demonstrated full scope |

Increment 1 supplies the installed storage/worker prerequisite for increment 2;
it does not wait for all Overview work. Increment 3 closes the complete first
installed dashboard slice. These are increments inside T014, not three releases
requiring separate owner approvals. Pure/empty-stack API/UI work continues
while a particular live provider lane awaits normal owner setup.

The configured Ollama cloud lane has delivered the installed Overview/detail
increment at `93297fc`; retain its evidence and complete only the remaining
monetary, pool-total and full-view acceptance. Anthropic/OpenAI monetary work
continues independently. This early
funds/usage screen is an intermediate delivery, not closure of checkpoint 3's
monetary journey. Do not request completed cloud setup again. No account
names/counts are hardcoded. Browser-closed monetary scheduling and controlled
recovery are proved once in packet E, after the first visible dashboard.

### Retained prerequisites and the next implementation packets

These are ordered work packets inside existing tickets, not extra tickets,
release gates or approvals. The catalog tracks status; this table specifies the
handoff and test boundary. Root integrates shared contracts/composition serially.
Only isolated, contract-stable module work runs in parallel.

Already demonstrated at `ca5f062`: cloud authority capture and commit fencing,
active-binding spend selection, shared balance/usage request coordination,
stored daily usage, account HTTP/UI/reload and another scheduled usage report.
Reuse this evidence; these are not fresh prerequisites to build again. They
prove counts-only usage, not monetary spend or the full scheduling matrix.

| Packet / existing ticket | Owner and smallest remaining output | Evidence ending that packet |
|---|---|---|
| A — T002/T004/T010 | M02/M05/root: publish canonical pool and primary-group attribution; finish funds collection-lineage wiring. Keep unresolved resources visible and excluded from totals | Exact shared-pool policy plus real metadata/API evidence; present funds trace to the current binding and committed run. A resource ID, key, label or equal amount cannot stand in for pool identity |
| B — T006 or T008, T005/T007 | First accessible monetary provider: existing owner setup, one ungrouped cost report, exact atomic commit/reopen and successful monitoring enable | Genuine source amount/currency/scope/interval → stored report. Ollama's demonstrated counts do not satisfy this packet; a later genuine monetary Ollama report may do so without another adapter |
| C — T010/T011 | M05/P01/P02: compact rows and full-inventory summaries, authorized immutable report/history selection, account detail and safe URL state | Actual HTTP/current/history agree on one report; direct URL, reload, sign-in return and expired selection behave explicitly. No history substitution or full-report bodies in Overview |
| D — T012/T014 | P02/root: shared filters, API-only subscription exclusion, compact financial table and correct partial subtotals; install checked candidate | Installed Overview → detail → Back/reload preserves report and selection. Funds-only/counts-only/pending rows remain useful; quota/header/footer survive a budget failure |
| E — T007/T015 | M04/root: monetary browser-closed refresh, controlled isolated restart/reconciliation and other-source isolation | Actual due run and receipt, no duplicated commit from recovery uncertainty; existing dashboard stays usable |

A and B can advance independently. C can begin with genuine retained usage and
funds while monetary access is prepared, but its monetary acceptance consumes B.
D consumes C; complete totals also consume A. Rendering truthful unavailable
summaries is a useful intermediate result, not completion of FR-ORG-003.
E reuses the existing cloud scheduled-read proof and adds the missing monetary
and recovery boundaries. These are working packets within existing tickets,
not another status ledger, gate or approval sequence.

Packet D's funds/usage screen is installed; it is no longer the next target.
The remaining first financial slice requires A's usable attribution/totals and
B's genuine money, carried through C/D's existing views. If all
monetary lanes prove inaccessible, name the actual access failure and required
owner action once; continue A/C and other independent required work. Account
names, invented telemetry and repeated configuration are not substitutes.

Every work report names the packet, last observed output and next demonstration.
A discovered defect is assigned to its existing ticket with the failing
requirement/test; it does not create another free-standing improvement project.
Do not replace the first spend demo with another contract-only increment.

### Immediate work and release dependencies

The funds/usage Overview and immutable report drill-down are now installed and
verified at93297fc. Reuse that evidence rather than repeating setup or deployment
diagnosis. The next visible increments are canonical shared-pool attribution/totals
and the first genuine monetary report; the current counts-only demonstration
does not close the monetary checkpoint.

In parallel with that integration, establish the first genuine monetary report
in T006 or T008, using the tested owner workflow if access is missing. An
existing Claude/Codex subscription login does not establish administrative billing
access. Record the actual access outcome before giving a monetary-demo date.
Missing setup blocks that provider's live test only; metadata, exact calculations,
queries and other connected providers continue. The owner setup request is pending; independent pool/query/analysis work proceeds.

Finish canonical pool metadata before declaring organization totals delivered.
Then finish the same report across detail, history and Overview, remaining
provider coverage, analysis, and the fixed release checks. These dependencies
constrain ticket closure; they do not require unrelated work to stop.

### Surprises to prevent in the existing acceptance tests

| User situation | Required behavior | Existing tickets |
|---|---|---|
| Two credentials expose one provider organization | One financial pool, visible access paths and one primary dashboard group; no duplicate total | T002/T004/T010/T012 |
| More accounts than one page; sort a column | Backend totals cover the full filter; final sort applies before pagination. Intermediate loaded-row sorting must be labelled and cannot close the final sorting check | T010/T012 |
| Subscription is paid but billing API access is absent | Explain the separate access requirement; preserve working subscription monitoring; never mark billing verified | T002/T006/T008/T011 |
| A successful read has counts but no costs | Useful usage and actual funds remain visible; spend is not reported, never inferred or zero | T009/T010/T011/T012 |
| A provider revises yesterday's cost or removes a bucket | Replace the complete current report; retain old history; no double counting | T004/T005/T010 |
| A read fails while an older report exists | Show the failure and original amount/time together; no green freshness from a failed request | T007/T010/T011/T012 |
| Midnight, reload, sign-in or a scheduled read occurs during navigation | Preserve interval and pinned report; explicit refresh changes the selection atomically | T007/T010/T011/T012 |
| An account moves group, rotates a key or disconnects | Preserve original financial history, invalidate stale authority, keep owner configuration separate from collection | T002/T005/T007/T011 |
| Negative/sub-cent costs, zero denominator, mixed currencies/bases | Exact money, signed adjustment labels, no invented percentage or incompatible grand total | T004/T010/T012 |
| Current balance appears beside historical spending | Separate timestamps; never suggest that current balance was the historical balance | T010/T011/T013 |
| No compatible funds or adequate cost history | Specific forecast-unavailable reason; no precise exhaustion date or forced provider spending | T013 |
| Upgrade/restart or browser closure | Persisted scheduling continues, safe recovery preserves data and protected secrets, authenticated dashboard verified | T007/T014/T015 |

This table is a review index into existing ticket/test obligations, not another
checklist engine or additional exit gate. Missing implementations remain on
those tickets; unsupported provider fields do not generate invented features.

## 3. Remaining task handoffs (details live in the existing catalog)

| Tickets | Explicit remaining output | Acceptance boundary |
|---|---|---|
| T001/T003 root | Keep scope/traceability current; attach existing suites and missing real assertions to the fixed runner checks as each feature lands | No declaration-only pass; no new runner or manual attestation workflow |
| T002 M02/M03 | Change scope / Use existing billing pool / primary group, generation invalidation and preserved history; usable owner-only setup/rotation/disconnect | Real metadata/HTTP/built UI, including mixed/API-only/Ollama accounts and all organization pages |
| T004 M05 | Finish exact policy/selection coverage including unrounded low-capacity decisions, compatible groups, shared pools and unknown/zero | Pure no-I/O math tests and meaningful mutations; no provider access prerequisite |
| T005 M05 | First real monetary commit/reopen and receipt replay; corrected/empty report behavior and retained lineage | Genuine report through actual SQLite, never inserted test telemetry |
| T006/T008 providers | Full frozen Anthropic/OpenAI category/one-dimension coverage and seven/thirty-day support | Official admitted reads, exact normalization and same-scope/time comparison |
| T007 M04/root | Other providers; durable selected interval/category/grouping; safe Collect now; persisted retry instant to UI; browser-closed refresh and recovery | Real source/run/receipt, disable/rotation fencing, fair work across accounts; one shared deadline and no second queue |
| T009 Ollama | Existing cloud connection/pool reused for usage and balance, compatible scope/units and shared rate control | Genuine self/team-authorized report; no duplicate funds or invented monetary values |
| T010 M05/P01 | Compact list/current/group summaries; supported funds with reasons; authoritative state rank; pinned bounded history; cutoff/as-of isolation | Real IAM/HTTP; exact values and full filtered inventory; no money arithmetic in handlers or React |
| T011 P02 | Retain old same-context value until replacement succeeds; expose available first-partial buckets without a complete total; actionable cooldown; older stored windows; direct URL, Back/reload/sign-in return | Real built account journey; clear only when financial context changes; no mutation replay |
| T012 P02 | Shared organization/provider/resource filters; API table and compatible subtotals; independent quota failure behavior | Same selected report across links; later pages counted; unknown is not zero or depletion |
| T013 M05/P01/P02 | Table/chart from identical immutable facts; safe supported dimension selection; explicit forecast snapshot and eligibility | Exact history plus conditional real forecast evidence, not a generic analytics engine |
| T014 root/M08 | Safe failure diagnostics, financial installation, authenticated proof, existing collector continuity and actual recovery | Selected clean build and real service/storage boundaries; no default-profile/user-agent changes |
| T015/T016 root | All-provider source-to-screen reconciliation, fixed exit checks, current public code and demonstrated acceptance | Technical pass, publication, installation and owner acceptance recorded separately |

Ticket dependencies constrain final closure, not independent work or the first
partial provider report. A complete provider ticket includes its remaining
categories; T005 may integrate that provider's first real report before then.
T013 can start pure math/chart work when the first history exists without waiting
for another provider's login. Shared contracts and migrations remain root-owned;
module work uses published ports and nonoverlapping paths.

## 4. Small UI contract, decided before coding

Preserve the top promotion/support header, footer, navigation and subscription
table. No connection banner taking the first viewport and no collection-run
panel on Overview. Existing Accounts/Overview/detail pages are sufficient.

- Overview: shared organization/provider/resource filters; API interval;
  compatible subtotals; Account / Organization / State / Reported spend /
  Available / Data through. Labels link to the same resource/context/interval.
- Detail: identity and provider scope, period, spend and actual supported funds
  first; one compact connection line; exact history; breakdown/chart/forecast
  afterward. Missing funds use one reason, not multiple empty cards.
- Setup for a new resource: create/attach → owner local entry with exact host
  and copyable command → Check → current-generation access evidence → Enable.
  Existing valid resources reuse completed steps; only missing actions appear.
  Existing subscription controls remain independent. No browser key field or opaque IDs to type.
- State: owner action first, collection failure next, incomplete/stale evidence
  next, then known low capacity, then current. Keep monitoring and source times
  separate; retain secondary facts. Exact percentages determine low status.
- History: Last 7/30 completed UTC days plus Previous/Next fixed windows over
  retained reports. Show exact bounds; missing history is No retained report.
  Reading history never triggers collection. No date-picker/query builder.
- Reliability: preserve old same-context money while refreshing or on failed
  replacement; invalidate old-account/scope responses; reconcile unknown
  mutations; preserve safe URL state through sign-in. One failed API request
  must not remove working subscription rows.

Financial links also retain the authorized immutable report/context, so a later
scheduled read cannot change the number between Overview, detail and reload.
Use **Refresh view** for stored reads and **Collect now** for a provider request.
Funds have their own visible observation time; today's balance is not a balance
for a historical spending window. Empty non-constraining credit components do
not imply account exhaustion. Positive adjustments plot above zero; forecasts
respect known credit expiry as well as renewal.

T010 must carry supported balance/credits/soft/hard-limit fields and their
availability reasons through the API; T011 must not hardcode Remaining funds
not reported for every provider. Cash and limit headroom remain separate.
T007 must expose its actual persisted retry instant before the UI promises a
retry time. These are missing handoffs for existing requirements, not new features.

## 5. Calculation rules that prevent misleading dashboards

| Question | Fixed rule |
|---|---|
| What was spent? | Exact disjoint costs from one compatible complete report; replacements supersede old facts, distinct signed adjustments count once |
| What remains? | Authoritative balance, or separately labelled compatible limit headroom; soft budget is not cash |
| Is it low? | Exact remaining/positive denominator ≤20%; never decide severity from rounded text, never derive a percentage without a denominator |
| Can amounts be combined? | Same currency, exact period and established cost basis; known shared pools once; incomplete/ambiguous coverage disclosed |
| Do providers share one USD total? | Not by default. Current adapters expose different cost bases; show labelled separate subtotals unless equivalence is established |
| What does zero mean? | Genuine supported zero/qualified empty coverage only; denied/missing/partial data are not zero |
| What is history? | Selected-report daily buckets, not the sum of repeated collection snapshots; retain corrections without duplicating spend |
| Can we forecast? | Only compatible positive funds/headroom and adequate complete cost history; source time and assumptions visible; otherwise a specific reason |

Exact formulas, rounding/overflow, input lineage and M7-MATH-01..16 remain in
the calculation document. API returns computed values; chart geometry and text
formatting never become a second financial calculation. Scope/key/group changes
cannot silently change the meaning of retained financial history.

## 6. Verification is part of delivery, not a surprise after it

Currently executable partial checks in the existing M7 runner:
`pure`, `mutation`, `registry_metadata`, `persistence_schema`.
The technical lane also implements `--check collection_guards` and
`--check budget_http_guards` for real isolated process/SQLite and no-report
IAM/HTTP assertions. Full collection/HTTP checks remain incomplete until genuine
populated report proof exists; these guards cannot close them.
The `deploy` selections `setup_activation` and `financial_activation` also exist
and require a retained clean controller plus exact revision. They change the
installed service and are not planning checks.

At `b69d96a`, full technical/live/browser/deploy dispatch still contains
`m7_boundary_runner_not_implemented`. T003 wires the existing actual suites and
missing assertions as each boundary lands. Test-file counts and registered
command names cannot substitute for executable required coverage. Do not build
another gate framework or delay product work until every final check exists.

| Boundary | Required evidence |
|---|---|
| Math | Pure edge cases, exact values, meaningful Red/Green/mutations |
| Persistence and API | Actual migrations/SQLite, genuine reports, IAM and versioned HTTP/client |
| User experience | Built browser, same source/API/DOM amounts, keyboard/200% zoom/narrow layout, context-preserving failures |
| Collection | Genuine manual and scheduled report, browser closed, other accounts continue, restart reconciliation |
| Deployment | Before/after revision/schema, secret-excluding backup, real recovery and authenticated financial screen; HTTP 200 is necessary but insufficient |
| Exit | Fixed M7-A01..A10, all three providers, active-resource inventory, current GitHub revision and separate owner acceptance |

Natural 401/403/429/depletion/correction/numeric-forecast cases are individually
Not Run when not observed. They are not passes and must not be manufactured by
spending, revoking keys or altering provider data. Required success and full
coverage cannot be reclassified as optional. Use isolated real systems for
controlled recovery. Reuse valid comparisons; rerun affected boundaries after
behavior changes, not owner attestations after documentation edits.

The following distinctions apply inside the existing checks, not a new gate:

| Always required before the relevant ticket closes | Conditional real-provider observation |
|---|---|
| T005: one genuine monetary report, atomic commit/retry/reopen, exact public query handoff; pure replacement/empty policies | A provider later corrects/removes a bucket or returns a genuinely empty report |
| T006/T008/T009 and T015: successful admitted read for each provider, frozen category dispositions and source comparison | A supported optional field/dimension is present on the owner's particular plan |
| T007/T015: real isolated failure/recovery, durable scheduling, generation fences and other-provider isolation | Natural 401/403/429/depletion; never revoke keys or spend funds to produce it |
| T013: exact rate/expiry/horizon policy, real history/chart, truthful unavailable forecast and financial retention | A real compatible balance/history sample permits a numeric forecast |
| T014/T016: installed authenticated UI, required continuity/recovery and fixed full exit | No conditional label excuses these mandatory results |

T003 must retain separate scenario dispositions inside its existing results;
required-check aggregation remains strict. A natural case stays Not Run/Blocked,
not Passed. A missing implementation, incomplete required category or denied
required provider access cannot be excused as a natural optional case.
T005's real-report evidence is its prerequisite; the catalog no longer waits
for every usage category in an entire provider ticket to close first. All three
complete provider tickets are still required by T015.

Financial retention is assigned inside T013 to M05's report/fact participant
and M08's existing invocation, with root integration. Its real isolated SQLite
test uses genuine reports and an explicit cutoff; no clock change or seeded old
telemetry. T015 rechecks installed invocation through the existing deployment
continuity check after T013, without making the first T014 installation wait.

### Cross-module decisions to settle in these tickets

| Decision | Simple implementation boundary | Required evidence / owner |
|---|---|---|
| Duplicate access paths | Resolve eligible current reports across the canonical pool before attributing it to its primary group. One failed key does not erase a healthy same-scope report from another key; preserve failure on that connection | M7-MATH-11 and M7-HTTP-001..006; T002/T004/T010 |
| Scope versus group edit | Source-scope change invalidates access/monitoring proof; group/primary-attribution edit does not trigger provider calls or rewrite old reports. Metadata and totals use one registry revision; conflict rereads, never mixed revisions | M7-REG-001..004 and M7-HTTP-001..006; T002/T010 |
| Pool persistence upgrade | New M02 association storage needs its own additive migration after installed0733, compatibility and isolated recovery. Allocate/version it with the actual contract; do not imply existing0733 deployment proves this future upgrade | M7-OPS-001..004; T002/T014, root owns catalog |
| Empty cost report | A qualified complete report with declared currency/basis and official empty-means-zero semantics is valid monetary zero. Missing costs in a counts-only report are not zero; never create spend for a test | M7-MATH-12, M7-EMPTY-001, M7-PROV-A01..A03; T004/T005/providers |
| More than one browser tab | Account/scope/primary-group changes conflict or invalidate the current snapshot; a still-open page cannot apply an old mutation/result under the new configuration | Existing M7-REG/HTTP/UI scenarios; T002/T007/T010/T011 |
| Shared-row and old-history links | Financial links use the contributing report's authorized account/resource tuple. Primary-only filters retain eligible secondary-path evidence. An old report displays its original scope, with current configuration/funds separately labelled | Existing M7-HTTP/UI scenarios, AC-UI-006 and AC-HIST-001; T002/T010/T011/T012 |
| Breakdown completeness | One dimension at a time, including actual unallocated/remainder where reported. Sum only disjoint fully covered rows; otherwise show partial coverage without asserting equality to a different total | M7-MATH-10 and M7-UI-004; T004/T013/T015 |

These are detailed cases within existing acceptance IDs, not new tickets or
extra manual exit checks. They identify necessary producer/consumer handoffs
before implementation rather than discovering them at final acceptance.

## 7. Scope, risks and reporting discipline

Freeze the provider/category inventory in
[discovery](../../evidence/m7-provider-discovery-2026-11-11.md). Supported but
unimplemented is Unfinished; denied access is an access problem; absent optional
fields are Unavailable. Future API categories are later scope. Each provider's
existing evidence records endpoint/role, range, units/basis, safe dimensions,
coverage/watermark and comparison method before that category is enabled.

Known remaining risks: real administrative access; no exposed funds/limits;
source lag/corrections; shared identity; oversized minimum report; financial
activation diagnosis; unsupported historical backfill. Resolve them in their
own tickets. An unavailable account label or untested access is not a blocker.
If all monetary lanes are actually inaccessible, disclose that precise first-demo
dependency; continue independent required work.

No new owner action is required for this planning refactor. During implementation,
owner participation is normal account/group setup, local key entry, official
login when necessary and final demonstration. Prepare the actual working
URL/host/control before asking once. Agents do not configure the owner's accounts.

Keep deferred: local Ollama, user-set budgets, FX/tax/invoices, price-list spend,
new budget alerts, custom/multi-dimension reports, statistical forecasts,
page/child-job orchestration, remote secret entry and general deployment tooling.
Existing one-dimension breakdowns, chart, totals and conditional forecast remain M7.

Report after each increment: visible result and URL, ticket/evidence, local vs
committed vs installed vs published revision, actual failing boundary, next demo
and necessary owner input only. If two sessions have no visible result, address
the integration dependency instead of expanding infrastructure. The previous
7–12-day estimate was not measured remaining work; do not reset it. Re-estimate
remaining provider/analysis/release effort after the first installed monetary
journey, with observed throughput and concrete causes of uncertainty.

Finish means the six checkpoints above and fixed M7-A01..A10 are satisfied;
partial deployment, passing local tests or this plan are not M7 completion.
