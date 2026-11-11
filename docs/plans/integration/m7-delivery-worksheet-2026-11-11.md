# M7 delivery worksheet: remaining work and fixed finish line

Status: execution clarification within approved focused plan 1.1.0, reviewed
against committed `e310b82` and installed `ca5f062` on 11 November 2026
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
| Committed implementation | `e310b82`: financial Overview, shared filters, immutable report drill-down and funds lineage; retains the prior cloud usage increment | Installed browser proof for this revision, canonical pool totals, monetary reporting and full provider/scheduling/analysis coverage |
| Installed dashboard | `ca5f062`, schema `v1_0733`; source/API/DOM/reload proof for one seven-bucket usage report, plus both existing cloud accounts' three funds components | Actual spend, financial Overview and complete history/analysis |
| Existing setup | Installed authenticated setup surface and current account funds demonstrated | No verified independent Anthropic/OpenAI billing enrollment; an absent record does not prove unavailable access |
| Deployment | Same-schema funds update and authenticated shell/Overview continuity passed; accepted financial migrations already installed | Full financial scheduling, recovery and final M7 acceptance; do not rerun the initial migration |
| Candidate verification | `e310b82`: local quality/build, 489 Python pure checks plus five presentation scripts, ten HTTP guards and five stored-data/empty-storage checks passed | New Overview browser checks remain Not Run against the installed candidate. Existing source reports demonstrate counts, not monetary spend |
| Publication | This review inspects local artifacts and recorded installation evidence | No new remote-publication or current live-health claim from this planning pass |

The attempted same-schema update to `e310b82` exited 3 with
`M6 CURRENT UPDATE: BLOCKED — review the transition journal and service state`.
A subsequent read-only check confirms the old `ca5f062` service is active/running
and the dashboard returns HTTP 200. That proves availability, not the new UI.
T014 must diagnose the retained transition state before retry/finalize/recovery;
this is engineering work, not a request for another owner approval. Do not
repeat migrations or restore a database on the strength of the generic error.
See [candidate evidence](../../evidence/m7-financial-overview-2026-11-11.md).

Evidence: [installed funds](../../evidence/m7-stored-funds-2026-11-11.md),
[cloud authority and current-query gap](../../evidence/m7-cloud-usage-authority-2026-11-11.md),
[current cloud usage runtime](../../evidence/m7-cloud-usage-runtime-2026-11-11.md),
[financial installation](../../evidence/m7-financial-installed-2026-11-11.md).
Installed funds are real delivery, but not a usage/spend report. One planning
ticket is done; twelve implementation tickets are in progress and three planned.
These counts are tracker state, not percentage complete or elapsed-time estimates.
No implementation ticket closes through this review.

## 2. Ordered delivery, with an observable result at every checkpoint

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

Use the already configured Ollama cloud lane and retained evidence to deliver
the next visible Overview/detail increment; those collection prerequisites are
connected. Anthropic/OpenAI monetary work continues independently. This early
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

The next user-visible target is D using retained real funds/usage; the complete
first financial slice additionally requires B's genuine money. If all
monetary lanes prove inaccessible, name the actual access failure and required
owner action once; continue A/C and other independent required work. Account
names, invented telemetry and repeated configuration are not substitutes.

Every work report names the packet, last observed output and next demonstration.
A discovered defect is assigned to its existing ticket with the failing
requirement/test; it does not create another free-standing improvement project.
Do not replace the first spend demo with another contract-only increment.

### Immediate work and release dependencies

The next observable result is the existing committed Overview on the running
service. Diagnose T014's update failure, install the selected clean candidate,
then compare its authenticated browser values with the API and stored report.
Do not hold this funds/usage demonstration for all monetary providers or charts.
It does not close the monetary checkpoint.

In parallel with that integration, establish the first genuine monetary report
in T006 or T008, using the tested owner workflow if access is missing. An
existing Claude/Codex subscription login does not establish administrative billing
access. Record the actual access outcome before giving a monetary-demo date.
Missing setup blocks that provider's live test only; metadata, exact calculations,
queries and other connected providers continue. No owner action is currently
required to refactor the plan or diagnose/install the existing candidate.

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
