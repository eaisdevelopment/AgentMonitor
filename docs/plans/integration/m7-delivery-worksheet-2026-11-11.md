# M7 delivery worksheet: remaining work and fixed finish line

Status: execution clarification within approved focused plan 1.1.0, reviewed
against committed `445b947` on 11 November 2026 (installed funds evidence:
`14dee16`, schema `v1_0733`). Primary owner: root integration; financial owner:
M05. No new milestone, approval, dependency or completion gate.

The [ticket catalog](m7-ticket-catalog-v1.json) remains the only task tracker:
16 stable tickets, five stories, M7-A01..A10. This worksheet specifies delivery
order and cross-module handoffs. The [UI plan](m7-ui-and-user-journeys.md) owns
screen behavior; [calculation rules](m7-calculation-and-data-rules.md) own money
semantics. Historical findings remain in [review evidence](../../evidence/m7-plan-refactor-2026-11-11.md).

## 1. Verified starting point

| Boundary | Evidence at this review | Still unfinished |
|---|---|---|
| Committed implementation | `445b947`: cloud report authority/context/codec and unresolved-lineage partition policy, after `14dee16` funds projection | Cloud capture/dispatch/commit integration and active-lineage current selector; published DTOs alone do not enable reads |
| Installed dashboard | `14dee16`, schema `v1_0733`; genuine stored funds → HTTP → built DOM/reload passed for two existing cloud resources, all three eligible components | New usage report, spend, financial Overview and complete history/analysis |
| Existing setup | Installed authenticated setup surface and current account funds demonstrated | No verified independent Anthropic/OpenAI billing enrollment; an absent record does not prove unavailable access |
| Deployment | Same-schema funds update and authenticated shell/Overview continuity passed; accepted financial migrations already installed | Full financial scheduling, recovery and final M7 acceptance; do not rerun the initial migration |
| Current worktree | Candidate M04 dispatch, M05 active-binding/current-cloud selection and Ollama runtime have collected, committed and queried one genuine self usage report; full local quality/build passes | That report has counts only, not costs. Installed usage UI, first monetary journey and full M7 acceptance remain unverified; see the runtime evidence |
| Publication | This review inspects local artifacts and recorded installation evidence | No new remote-publication or current live-health claim from this planning pass |

Evidence: [installed funds](../../evidence/m7-stored-funds-2026-11-11.md),
[cloud authority and current-query gap](../../evidence/m7-cloud-usage-authority-2026-11-11.md),
[current cloud usage runtime](../../evidence/m7-cloud-usage-runtime-2026-11-11.md),
[financial installation](../../evidence/m7-financial-installed-2026-11-11.md).
Installed funds are real delivery, but not a usage/spend report. One planning
ticket is done; eleven implementation tickets are in progress and four planned.
These counts are tracker state, not percentage complete or elapsed-time estimates.
No implementation ticket closes through this review.

## 2. Ordered delivery, with an observable result at every checkpoint

| Order | Existing tickets / owner | Work to finish | Demonstration that ends the increment |
|---|---|---|---|
| 1. Installed collection prerequisite — operational checks passed | T014 root; T003 verification wiring | Storage/worker activated at schema0733; later funds build14dee16 and authenticated setup verified. Complete collector continuity and financial recovery proof with later integration | Correct installed revision/schema and authenticated controls demonstrated. This partial deployment does not close T014 |
| 2. First real financial journey | T002/T005/T007 + first available T006/T008/T009; M02/M04/M05/provider/root | Existing or newly owner-configured connection; genuine bounded read; exact atomic report/reopen; positive enable/disable; next due read with browser closed | One real account shows provider scope, interval, amount/currency, source time and useful access state. Check success is backed by its actual stored report |
| 3. First useful dashboard | T010/T011/T012 + T014; M05/P01/P02/root | Compact current/summary DTOs, supported funds, pinned history, Overview/shared filters, navigation and installed verification | Same report and exact amount in account/detail/history/Overview; group selection and Back/reload work; failed refresh retains prior value |
| 4. Finish provider coverage | Remaining T006/T008/T009 + T007 | Wire remaining providers, finite usage categories, thirty-day and pinned report intents, shared scope rate limits | Anthropic/OpenAI/Ollama use the same screens with explicit category/field coverage; all active resources accounted for |
| 5. Finish the analysis already promised | T013 with T010/T011 | One supported dimension, daily bars plus exact table, separate balance series, simple observed-rate forecast or precise unavailable reason | Chart/table reconcile to the selected reports; no invented balance, attribution or stop date |
| 6. Release and close | T015/T016; root | Fixed source/API/DOM comparison matrix, real recovery/continuity, bounded review, full executable exit, publication and demonstration | Installed and GitHub revisions verified; required checks pass; owner accepts the demonstrated full scope |

Increment 1 supplies the installed storage/worker prerequisite for increment 2;
it does not wait for all Overview work. Increment 3 closes the complete first
installed dashboard slice. These are increments inside T014, not three releases
requiring separate owner approvals. Pure/empty-stack API/UI work continues
while a particular live provider lane awaits normal owner setup.

Use the already configured Ollama cloud lane for the next integration; it is
eligible after cloud-graph commit fencing, active-binding current selection and
shared balance/usage rate coordination are connected. Anthropic/OpenAI access
work continues independently. Do not ask for cloud setup already completed.
Requests-only data is useful usage but cannot substitute for
the first monetary demonstration. No account names/counts are hardcoded.

### Next increment: finite handoffs before the first spend demonstration

These are ordered work packets inside existing tickets, not extra tickets,
release gates or approvals. The catalog tracks status; this table specifies the
handoff and test boundary. Root integrates shared contracts/composition serially.
Only isolated, contract-stable module work runs in parallel.

| Order / ticket | Owner and smallest output | Evidence ending that packet |
|---|---|---|
| 1 — T007/T009 | M04: finish cloud target capture, restored admission, claim and commit fences in existing budget repository/executor. Root retains distinct service and usage fingerprints | Pure restoration Red/Green; actual migrated SQLite with genuine registry graph proves rejection of changed authority and exact retained context. Empty-queue tests alone are insufficient |
| 2 — T004/T005/T010 | Root publishes minimal active-binding selector through existing current-query contract; M05 filters unresolved current reports. Resolved compatible scope and authorized old history remain available | Pure rotation/isolation Red/Green and real current-query verification. Populated old-lineage exclusion uses naturally available genuine history; otherwise record that case Not Run. No forced credential rotation or delay of the first spend demo solely to manufacture the case |
| 3 — T007/T009 | Root/A03 connect usage to the existing Ollama request gate and worker, then M05 report sink. One shared gate covers balances and usage; no second queue | One actual permitted usage request under captured generation/interval, real report receipt, exact commit/retry/reopen. Counts-only is recorded honestly and cannot satisfy monetary acceptance |
| 4 — T010/T011 | M05/P01/P02 project that immutable report into account detail, amount/period/coverage and exact table beside independently timestamped funds | Genuine source → HTTP → built DOM/reload equality; Check/Collect completion rereads the same interval. Missing monetary fields show a reason |
| 5 — T010/T012/T014 | Compact Overview and backend summaries using that same resource/report; shared filters and detail link; install checked candidate | Installed Overview → detail → Back/reload preserves value/context; funds-only rows work; existing subscription rows/header/footer survive. This ends first useful spend delivery, not full M7 |
| 6 — T007/T015 | Prove next scheduled read with browser closed, then controlled isolated restart/reconciliation and other-source isolation | Actual due run and receipt, no duplicated commit/request from recovery uncertainty; known-good dashboard retained |

Packets 1 and 2 can proceed independently after root synchronizes their small
contract changes. Packet 3 consumes both. UI structure and pure calculation
work need not wait for another provider login; populated acceptance does.
Existing balance-only delivery is not repeated and does not close packets 3–5.
After packet 3, use the measured actual provider fields to identify the shortest
remaining path to the installed demo. If no monetary field exists, continue its
usage lane and use a genuinely accessible Anthropic/OpenAI cost lane; do not
convert counts to money, change the finish line or wait without independent work.

Every work report names the packet, last observed output and next demonstration.
A discovered defect is assigned to its existing ticket with the failing
requirement/test; it does not create another free-standing improvement project.
Do not replace the first spend demo with another contract-only increment.

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
| T011 P02 | Retain old same-context value until replacement succeeds; actionable cooldown; older stored windows; direct URL, Back/reload/sign-in return | Real built account journey; clear only when financial context changes; no mutation replay |
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
