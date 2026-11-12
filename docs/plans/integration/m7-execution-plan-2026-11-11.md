# M7 API budgets: deliver a working dashboard first

- Status: Approved for implementation by the owner’s subsequent active M7 goal; see the authority record.
- Plan version: 1.1.0; supersedes focused 1.0.0.
- Owner: root integration; primary financial semantics: M05 Capacity.
- Original planning baseline: `a47fc53` on `codex/m7-api-budgets`.
- Current implementation and installed-state checkpoint: see the single
  [delivery worksheet](m7-delivery-worksheet-2026-11-11.md#1-verified-starting-point).
  That worksheet owns the installed revision and delivered-increment list;
  this plan does not duplicate a competing current deployment checkpoint.
  Retained monetary display is verified; fresh commit/recovery, provider
  comparisons, complete provider/history/analysis coverage and full M7 acceptance
  remain unfinished. The worksheet alone owns current order.
- Requirements: FR-BUDGET-001..006, FR-ORG-003, FR-ACC-001..004/006;
  AC-LIVE-004/005/007, AC-UI-002..006, AC-HIST-001, AC-OPS-003/006,
  AC-TEST-001..006.
- Parent scope: [five M7 stories](../../superpowers/plans/2026-09-19-agentmonitor-v1-m7-api-budgets.md).

## 1. The delivery promise

Read the [six-action owner demonstration](m7-delivery-worksheet-2026-11-11.md#owner-demonstration-in-six-actions)
for the screen-level finish line. Implementation order is: finish the current
bounded visible packet; demonstrate one genuine money journey as soon as access
exists; finish the frozen provider and analysis coverage; verify recovery and
release. One integration packet is active at a time. Required acceptance stays
fixed; source limitations are disclosed rather than replaced with guessed data.
The [ticket catalog](m7-ticket-catalog-v1.json) supplies owners, dependencies,
test-first steps and completion evidence for each of the sixteen tickets.

An existing or newly owner-configured resource shows its reported spend on
Overview and account detail, with organization, billing scope, period and
freshness. Existing Ollama cloud connections are reused; request only genuinely
missing setup, never another account or key entry just to fit the billing path.
That whole journey is the first usable slice. Other providers and advanced views
do not precede that demonstration.

The full M7 scope still includes Anthropic, OpenAI and supported Ollama cloud
usage, provider-exposed budgets/credits/limits, supported breakdowns, history,
forecasts, real comparisons and safe deployment. Names/counts are owner-defined.
M6 is not reopened. No local Ollama work, agent switching, provider mutations,
inference spending, invoices/tax/FX, local budget editing or unrelated redesign.

Critical expectation: cost APIs may expose spend without exposing remaining
funds or an enforced limit. In that case M7 shows useful spend/history and a
clear missing-balance/forecast reason. It must not promise a percentage or date
that the provider data cannot support. A subscription login is not billing API
access. These are known product limitations, not surprises to discover at exit.

### Finite provider coverage for this milestone

This is the implementation inventory for T006/T008/T009 and the downstream
T013/T015 comparisons. It refines FR-BUDGET-001/003 within the approved scope;
it is not a promise to implement every feature added to provider APIs later.
The linked discovery proves documented interfaces, not successful account access.

| Ticket / source | Required reports and ranges | Required single-dimension views when exposed | Current implementation boundary |
|---|---|---|---|
| T006 Anthropic Console analytics | Cost and usage, daily buckets, 7/30 completed UTC days; token/request measures retain their types | Workspace, safe API-key identifier, model, token category; organization/account remain source scope and owner grouping | Ungrouped cost runtime, captured manual dispatch and 7/30-day scheduling are installed; successful live costs and complete usage/grouped coverage remain unfinished |
| T008 OpenAI organization | Costs plus the eleven usage categories listed below; daily 7/30-day reports | Project, safe API-key identifier, model, token category where that endpoint exposes them; time is the daily bucket | Ungrouped cost runtime, captured manual dispatch and 7/30-day scheduling are installed; successful live costs and complete usage/grouped coverage remain unfinished |
| T009 Ollama cloud | Native 7d/30d self/team usage; retain actual covered bounds and partial buckets; existing balance collection | Model plus provider-reported remainder; monetary and token fields only when supplied | Installed usage/balance and genuine monetary-history increments are recorded in the worksheet; complete range/scope/model/manual acceptance remains unfinished |

OpenAI's fixed usage list is **completions, embeddings, moderations, images,
audio speeches, audio transcriptions, code-interpreter sessions, vector stores,
file-search calls, web-search calls, decisions**. Each is accounted for in the
same adapter ticket; a completions-only report is never called all API usage.
An endpoint's native unit is retained: tokens, requests, images, duration,
sessions or storage are not interchangeable and are never priced locally.

Before implementing a grouped request, its adapter records the exact allowlisted
field, unit, grouping parameter and applicable role in its existing source
manifest/tests. An unsupported endpoint/dimension combination is disabled with
a reason; an unimplemented supported combination remains unfinished. No Cartesian
product of every dimension, range and account is required. Verify each distinct
supported mapping and both ranges, then account for every active resource through
its actual supported lane. Real empty responses can prove access/coverage under
that source's contract; they cannot prove a nonempty dimension mapping.
For each row of this finite matrix, record implemented request/mapping, admitted
unit/dimension, successful access/coverage, and populated-example evidence
separately in T015. Mandatory implementation and required successful provider
lanes cannot be waived. A category that naturally returns a genuine empty
success has no populated example: that scenario remains conditional Not Run,
not a claim of populated mapping verification and not a requirement to buy or
manufacture usage. A denied request is not an empty success. Preserve the
mandatory monetary source proof described in section 7; counts-only or missing
currency cannot satisfy it. Future API additions do not enter this matrix.

The Anthropic documentation rechecked on 12 November lists separate usage and
cost endpoints with common model/workspace/key dimensions and a cost token-type
split. It permits up to 31 days per request. Its reported costs exclude some
commitment fees, and data can arrive late. Therefore these are **reported API
costs**, not an invoice or a complete financial liability. These are documented
capabilities, not new live evidence. [Official analytics documentation](https://platform.claude.com/docs/en/manage-claude/usage-cost-analytics-api).
The fixed OpenAI category inventory is checked against its [official usage
reference](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage).

New provider dimensions/categories, Enterprise/AWS authentication, 24h Ollama
views and arbitrary historical backfill are not added by this review. Existing
source omissions are disclosed; scraping or additional financial endpoints are
not required to fill missing funds/limits. Source discovery/admission changes
must identify the affected existing requirement before becoming delivery work.

## 2. One authoritative plan set

| Artifact | Owns |
|---|---|
| [UI and user journeys](m7-ui-and-user-journeys.md) | Exact screens, controls, setup, LAN flow, state copy and browser acceptance |
| [Calculation and data rules](m7-calculation-and-data-rules.md) | Formulas, exactness, time/coverage, shared pools, empty reports, corrections and forecast eligibility |
| [M05 increment](../modules/m05-capacity/m7-budget-increment-2026-11-11.md) | Contracts, storage, import boundaries and test sequence |
| [Ticket catalog](m7-ticket-catalog-v1.json) | Sixteen stable ticket IDs, dependencies, delivery slices, acceptance and actual status |
| [Delivery worksheet](m7-delivery-worksheet-2026-11-11.md) | Ordered demonstrable increments, concrete unresolved integration work, test boundaries and owner participation |
| [Source discovery](../../evidence/m7-provider-discovery-2026-11-11.md) | Official documentation versus unverified live account facts |
| [Refactor review](../../evidence/m7-plan-refactor-2026-11-11.md) | Actual hazards found, bounded review and validation results |

These focused documents override conflicting implementation instructions in the
historical M7 plan only within this approved change: additive money/report
contracts, necessary new migrations, supported empty results, UI-first delivery
and simple query-time forecasts. They do not waive the real-boundary/TDD rules.
Approval covers the synchronized focused set once. Routine fixes inside it do
not require a new plan version or owner ceremony. New financial meaning, secret
custody, dependency, destructive operation or incompatible contract does.

The worksheet also fixes the remaining finite fairness/recovery demonstrations
and final candidate inventory. The UI/calculation documents resolve historical
scope actions, matching collection completion, uncollected breakdown selection,
observed limits versus derived headroom and forecast identity. Direct admitted
7/30-day reports suffice; no generic interval assembly is a prerequisite.
These are clarifications of existing tickets, not additional release features.

## 3. What the owner sees

Keep existing navigation/header/footer. Accounts gains Add API billing account
and capability-based sections so an API-only account is not sent to CLI login.
Setup has a visible connection action, one copied nonsecret local command and
an explicit Enable API monitoring action. The owner never manually types opaque
account IDs or supplies repeated account attestations.

Overview keeps subscription quotas and adds a compact API usage & spend table:
Billing account | Organization | State | Reported spend | Available | Data through.
Both sections share organization/provider filters. Grouped organization/global
spend summaries preserve currency, exact period and cost basis, deduplicate
known shared pools and disclose missing coverage. No misleading mixed total.

Account detail presents money and its meaning first, then supported breakdowns,
exact history/chart, and a forecast or reason it is unavailable. Connection and
source diagnostics are compact/expandable. Refresh view rereads stored data;
Collect now is a separate rate-limited action. See the UI document for exact
states, sorting, controls, pagination, responsive and accessibility behavior.

## 4. Delivery slices and checkpoints

These are delivery stages, not five serial implementation barriers. The
[worksheet](m7-delivery-worksheet-2026-11-11.md#2-one-remaining-delivery-sequence)
alone owns current work order. Catalog dependencies constrain ticket closure;
its steps name smaller handoffs that allow independent work to start. In
particular T013's math and first-source chart can start before all provider
tickets close. Each stage ends with the indicated running result.

| Slice | Contributing tickets | Demonstration / exit |
|---|---|---|
| S0: known prerequisites | T001; start T003; T004 exactness; T002 owner setup | Plan/contract freeze, scoped test commands, tested setup UI; known access needs identified once |
| S1: first usable dashboard | First available provider T006/T008/T009 → T005 → T007 → T010 → T011 → T012; T014 deployment | One existing or newly owner-configured resource goes through collection, exact history table, Overview/detail and installed browser. No numeric-forecast prerequisite |
| S2: provider coverage | Remaining T006/T008/T009 | All three provider lanes use the same working screens; actual unsupported fields remain explicit |
| S3: complete M7 views | T013 | One-dimension breakdowns, simple history chart and explainable query-time forecast; later refinements are not added |
| S4: stabilize and publish | T015 → T016 | Real cross-provider/browser reconciliation, one bounded independent review, one full exit run, remote revision verified and owner demonstration |

The installed Ollama increment already connects cloud-graph commit fencing,
active-lineage spend selection and shared balance/usage rate coordination.
The worksheet records both earlier counts-only reports and later genuine USD
cost reports. Reuse the monetary reports now available for the first money
journey; neither their existence nor the chart alone proves reconciliation.
Retain the existing funds/usage views on Overview and detail.
Retain the installed canonical pool attribution, OpenAI cost runtime, manual
billing controls/cooldown, context-aware status and prior-scope report discovery.
Outstanding source lifecycle, Ollama manual verification and monetary proof are
ordered in the worksheet, using whichever admitted source supplies real money,
including the existing Ollama cloud resource. No new billing enrollment is a
prerequisite for using its report.
No provider is dropped
from M7. A requests-only
legacy source can advance its own usage lane but cannot substitute for the first
demonstrated monetary report. T005 can integrate one genuine normalized report from a partially completed
provider ticket; it does not wait for that adapter’s remaining usage categories.
Its own final live persistence checks still require the actual report. No
hardcoded account is required. Missing access to one
lane blocks its live evidence only. No invented demo account or seeded telemetry.

T010 closes the current/list/summary/history HTTP slice; forecast/breakdown HTTP
and later UI enhancement belong to T013. This removes the earlier UI↔forecast
completion dependency. T014 begins operational design immediately and supports
the first installed slice; it does not wait until the last week.
T010 requires the first provider's genuine collection/run-status handoff, not
closure of all-provider T007. Full scheduling/range coverage remains required
by T015. This keeps the first dashboard deliverable before provider expansion.

T014 has ordered increments inside one existing ticket: tested setup activation
before owner entry; tested financial storage/worker activation before the
installed first report; then complete Overview/detail/history activation and
verification. The storage/worker increment need not wait for full Overview.
Only the complete installed financial journey closes T014. Each partial
activation preserves the existing dashboard and collectors and reports its scope.

The setup command resolves the selected installed service. Candidate-only
command tests do not prove installed enrollment. Retain delivered migrations:
`0720 → 0731` setup, `0731 → 0733` financial storage and `0733 → 0734` pool
metadata. They are not pending actions.
Root reuses the existing selected-revision build, migration, backup and recovery
routines; there is no additional deployment project or approval ceremony.
The historical failed attempt, checked diagnostic and later successful financial
activation are recorded in the worksheet. A generic cutover error does not establish whether
migration or candidate startup happened: inspect actual service revision,
schema and transition journal before choosing retry, finalize or recovery.
Never restore an old database over possible new writes.

First-slice results are explicitly partial M7 delivery. They are not milestone
completion. The full original three-provider/five-story scope remains required.

## 5. Minimal architecture and exact ownership

| Owner | Allowed work / contract |
|---|---|
| Foundation/root | Correct context-dependent exact decimal conversion under CTR-COMMON-003 without changing its public range; sole shared contract writer |
| M02 | Registry account/resource purpose, scope association, opaque credential binding/generation; independent billing monitoring; API-only eligibility and archive/disconnect rules |
| A01/A02/A03 | Official read-only endpoint allowlists, role/version admission, exact mapping, scope/dimension semantics and source delay; no direct DB writes |
| M04 | Existing one-run admit/collect/commit/reconcile flow; budget receipt/run variants for empty and observation-only reports; bounded per-report pagination and source throttling |
| M05 | Exact signed cost, report coverage/replacement, budget/current/history/aggregation query ports and pure forecast policy |
| P01 | Authenticated typed HTTP, safe action/response states, schema/client generation; no adapter or database access in handlers |
| P02 | Existing Accounts/Overview/detail components, capability-driven rendering, API-only values and formatting; no financial computation in React |
| Root/operations | Serial composition/generated files/migration catalog, installed setup command, selected-candidate build/deploy/recovery and canonical verification |

Root owns contracts, migration order, composition and generated artifacts;
module agents receive nonoverlapping paths after synchronization. Provider-specific
code stays under `adapters/providers/{claude/anthropic_api,codex/openai_api,ollama/api}`.
Capacity code stays under its domain/application/ports and SQLite adapter.
P02 extends existing account/overview features and a budget-history component.

Reuse frozen budget/usage tables where their semantics fit. Existing additive
M02 revisions `v1_0730`/`v1_0731`, M05 `v1_0732` and M04 `v1_0733` supply setup,
financial storage and run-to-report authority. These were installed at `437a232`;
pool metadata later added M02 `v1_0734`, now installed. See the worksheet and
linked transition evidence. Full financial acceptance remains outstanding.
Preserve old migration digests.
Do not automatically create one-to-one tables for every field: use necessary
additive context columns, a report-coverage relation and signed cost storage.
No forecast storage table or parent/child job engine. The first real report
measures whether the documented bounds fit; query page size is not a collection
batch size. Exact details are in the M05 and calculation documents.

### API contract allocation

All telemetry reads require `read:telemetry`; mutations use existing admin/CSRF
and concurrency controls. GET never starts collection. Additive V2 budget types
use the existing tagged cloud subject; old quota/V1 DTO semantics stay intact.

| Route under `/api/v1` | Operation | Ticket |
|---|---|---|
| `GET /budgets` | `capacity_list_budget_overview_v1`: filtered rows and backend grouped summaries | T010 |
| `GET /accounts/{account_id}/budgets` | `capacity_list_budgets_v1` | T010 |
| `GET /budgets/{budget_id}` | `capacity_get_budget_v1` | T010 |
| `GET /accounts/{account_id}/api-capacity` | `capacity_get_account_api_budget_v1` | T010 |
| `GET /budgets/{budget_id}/history` | `capacity_list_budget_history_v1` | T010 |
| `GET /budgets/{budget_id}/usage-breakdowns` | `capacity_list_usage_breakdowns_v1` | T013 |
| `GET /budgets/{budget_id}/forecast` | `capacity_get_budget_forecast_v1` | T013 |

T007's existing first action is
`POST /accounts/{account_id}/billing-connections/{resource_id}/checks`
(`billing_check_connection_v1`). Its guarded transport and Check UI exist locally.
Read-only `GET /collection-runs/{run_id}/budget`
(`billing_get_run_status_v1`) is also implemented through M04's public run query.
Its additive status DTO includes actual `report_id`, account and resource;
non-budget runs are rejected. Generated operation counts are checkpoint evidence,
not feature coverage; the delivery worksheet owns the current installed revision. Real HTTP guards and
built no-report/browser controls pass; a
successful credential-backed report and populated status-to-DOM journey remain
unverified. See [integration evidence](../../evidence/m7-billing-integration-2026-11-11.md).

This status GET tracks action progress separately from the pinned financial
snapshot. On completion the UI advances read time, preserves the selected
reporting interval and replaces report/table together. Existing run-list
consumers remain compatible; zero-fact reports require no fabricated quota
observations. Monitoring GET/PUT and current-generation proof exist in current
CTR-REG-014 1.5.0. Selected 7/30-day billing intent, Collect now, cooldown and
matching status first shipped at `ef8fa86`; subsequent cloud manual actions and
fair seven-/thirty-day scheduling use CTR-COL-002 2.5.0/2.6.0. Remaining T007
work includes positive monetary monitoring/collection, full category coverage,
sustained fairness and recovery. See the worksheet for exact live outcomes;
credential-free checks
and runtime wiring alone do not establish successful monetary collection.

T002 owns account billing-connection metadata, credential status and local entry,
disconnect/rotation eligibility and their HTTP/UI. T007 owns the executable
verification, monitoring-enable and collect-now actions and their HTTP/UI wiring.
T002's metadata/status tests can advance independently. Its command boundary is
tested against the built candidate on isolated real storage; that is not a
successful installed command or real-key enrollment claim. T014's early setup
activation verifies the selected-service entry point before owner entry; full
T014 closure still follows the first dashboard slice. No nonfunctional
verify/enable button is presented as usable in the interim. POST metadata/verify returns
real IDs/status with idempotency and account generation. No key values in JSON.
M04/M05 expose additive receipt/run variants supporting real empty coverage
without fictitious observations/events. Existing consumers are tested against
new budget capability routing; quota alert semantics remain unchanged.
New budget alert rules are outside M7; do not build forecast events for them.

## 6. Credential permission and owner work

Approved extension of the existing protected `.env` mechanism: AgentMonitor
runtime alone can store an owner-entered Anthropic/OpenAI administrative API
credential and read the binding-specific entry for admitted read-only billing
GETs, and use Ollama's key for its official usage GET in addition to balance.
The coding agent never views keys. No secrets in browser, arguments, source,
logs, database, evidence, exports or backups. No provider profile read/write,
key listing, inference or provider mutation. Fixed HTTPS origins, no redirects.

The account page supplies the exact installed command and host context. Owner
creates records/associations, enters keys locally and enables monitoring. The
agent builds/tests that experience and opens required pages; it does not ask
for unavailable buttons or manually configure owner accounts. Key rotation
invalidates old access proof and in-flight generation without deleting history.
No new dependency. The existing focused plan/permission approval covers
repeatable implementation/test/deploy actions inside this scope.

## 7. Fixed completion catalog

| ID | Required result | Principal tickets |
|---|---|---|
| M7-A01 | Owner-created billing setup, API-only/mixed-purpose UI and safe credential lifecycle | T002/T007/T011 |
| M7-A02 | Exact money, signed corrections, valid totals, periods, availability and separate pools | T004/T005 |
| M7-A03 | Real Anthropic permitted reports and source comparison | T006/T015 |
| M7-A04 | Real OpenAI permitted reports and source comparison | T008/T015 |
| M7-A05 | Real supported Ollama usage with shared balance semantics | T009/T015 |
| M7-A06 | Supported breakdowns, immutable corrected/empty-report history, chart and conditional forecast | T010/T013 |
| M7-A07 | Authenticated HTTP/client and built UI; real IAM, keyboard/responsive checks | T010/T011/T012 |
| M7-A08 | Compact filtered Overview, valid organization/global grouped totals and useful states | T012 |
| M7-A09 | Rate/size/deadline bounds, one source failure isolation and genuine recovery; protected profiles untouched | T007/T015 |
| M7-A10 | Revision-bound install/recovery, existing dashboard/provider continuity and final evidence | T014/T016 |

Required live coverage is a successful admitted cost report and supported usage
for Anthropic/OpenAI, and a successful supported usage report for Ollama plus its
existing balance continuity. Counts-only Ollama is valid for that provider's
actual capability, but cannot replace monetary verification. Every configured
active billing **or existing Ollama cloud** resource is accounted for.
Pending/disabled resources remain visible with their state;
no duplicate billing enrollment is needed for cloud coverage. No fixed
six/four-account ceremony. Existing comparisons record exact resource, interval,
source time and precision once; reuse them for documentation changes. Technical
changes invalidate only affected evidence lanes until the final candidate run.

Numerical forecast validation is conditional on naturally adequate compatible
source history/remaining funds. Correct unavailable/insufficient-input behavior
is required and tested when that is the real state. Report the numerical live
scenario Not Run/Blocked; do not mistake it for a pass or force spend to obtain it.
Natural 401/403/429/exhaustion cases are listed individually when unobserved;
required access/reconciliation cannot be silently declared optional. Controlled
failure/recovery uses isolated real resources without taking the live dashboard
down, revoking credentials or restarting owner agents.

## 8. Testing, deployment and closure without an endless loop

T003 implements one runner with technical/live/browser/exit selections behind
the registered canonical commands; reuse existing checks. No new general gate
framework, detached approval hierarchy or manual owner-code paste workflow.
Start each changed behavior with meaningful Red at its real boundary. The money
rules document provides exact pure test cases; I/O proof uses real provider
reports, real SQLite/migrations, real HTTP and a real built browser.

T014 is limited to this AgentMonitor user service and an explicitly selected
clean revision. Reuse build sealing/locks/backup/recovery helpers, remove only
the M6 fixed-worktree assumption. Do not build a general deployment platform.
Before transition verify schema/backup/rollback, then loopback/LAN readiness and
installed revision. On failure restore the known-good runtime safely. Never
restore an old database after new writes without explicit recovery authority.
Promotion/support/footer/quota/filter behavior must survive each rollout.

After S3, freeze known defects and the required check inventory. Run
`AUTO-M7-EXIT` and one bounded independent review. If a defect changes code,
rerun its affected checks and the final aggregate on the corrected candidate;
"one review" never means accepting a failing check or reusing another revision's
receipt. Findings repair existing requirements; they do not expand scope.
New blockers must prove a stated requirement/invariant is
violated and name the smallest fix. Enhancements go to the deferred list below;
no silent gate expansion. T015 uses live/browser lanes; T016 runs the technical
exit, publishes current code to GitHub, verifies remote revision, demonstrates
the result and records acceptance separately. Publication never gates itself.
GitLab mirror authentication cannot block authorized GitHub delivery.

Planning check: `python3 tools/automation/run.py AUTO-M7-PLAN-CHECK`.
Documentation, quality, Git preflight and synchronized baseline checks retain
their existing commands. M7 execution commands remain fail-closed until built.
The already-passing 66 automation/planning tests are prerequisites, not M7 proof.

## 9. Risks, scope control and estimates

Known risks are now explicit: administrative access, absent balances/limits,
provider lag, complete-empty/corrected reports, shared pools, exact-decimal
context, oversized minimum reports, API-only account eligibility, later-page
accounts and installed setup/deployment. Each maps to a named ticket and test.
Provider documentation proves a supported interface, not owner credentials or
live behavior. Missing input pauses its dependent lane only.

Deferred improvements: user-set budgets, FX/invoice reconciliation, arbitrary
multi-dimension query builder, custom reports, advanced/statistical forecasts,
new budget alert policies, durable page/child-job orchestration without proven
need, remote secret entry, additional top-level history screens, general
multi-host deployment and all local Ollama work. These are not exit conditions.
Existing supported one-dimension breakdowns, aggregation, chart and conditional
forecast are retained in M7; they are not removed under the word simplification.

Original effort estimate, not a measured remaining-work estimate: S0/S1 about 3–5 focused engineering days after
usable access; S2 2–3; S3 1–2; S4 1–2. Total 7–12, excluding provider/owner wait.
The first installed vertical is the checkpoint to revise estimates from measured
work. Report completed tickets and visible behavior, current failing test and
next demo every work session. If two sessions produce no new user-visible slice,
review the dependency causing delay instead of adding more infrastructure.

## 10. Approval state

The owner directed full M7 implementation after receiving this 1.1.0 plan.
[Implementation authority](../../evidence/m7-implementation-authority-2026-11-11.md)
records that instruction, the runtime-only credential purpose and retained
controls. Execute S0/S1 without repeating the approval request. Implementation,
live verification and milestone acceptance remain separate evidence states.

## 11. Execution checkpoints and exceptions

The ticket catalog remains the task tracker: stable ticket IDs, module owner,
prerequisites, test-first steps, verification command and evidence. The checks
below clarify delivery order within existing tickets; they add no new gate,
approval or product scope.

| Checkpoint | Concrete result to inspect | What must not delay it |
|---|---|---|
| T002 owner setup | Create/attach → actual detail URL → locally entered credential → safe status; early T014 setup activation precedes owner entry; cancel/retry/rotation/archive preserve unrelated configuration | Full provider coverage, forecast, final full-dashboard deployment or a provider success mislabeled as local storage success |
| T004 exact policy | Exact money and complete-report selection tested, with explicit availability and shared-pool rules | T013 rate/horizon implementation; its math cases are verified there |
| First available T006/T008/T009 monetary lane | One complete real monetary report for one owner-selected resource, with exact coverage and source comparison; existing Ollama monetary reports qualify, while counts and balances alone do not | An inaccessible second provider, all organizations, all usage dimensions, or duplicate Ollama billing enrollment |
| T005/T007 | That report survives database reopen; scheduled/manual reads use one real run and generation fences; first-reading state resolves | A generic job framework, new alert engine or manufactured rare provider failures |
| T010–T012 | Real API → detail/history table → filtered Overview; exact same values/scope/period | Charts, numerical forecasts or all providers |
| T014 | Same candidate installed; health plus authenticated Overview and first detail work; subscriptions remain usable | Final publication and full-milestone acceptance |
| Remaining providers and T013 | Provider coverage, supported breakdowns, chart and conditional forecast on the working screens | Unsupported balances/limits or artificial spending to obtain history |
| T015/T016 | Fixed full matrix, safe deployment/recovery, current public revision verified, demonstrated owner acceptance | Unrelated improvements or a failed secondary GitLab mirror |

T003 grows the existing runner alongside each tested behavior. A missing final
lane stays explicitly Not Run; implementing the whole exit catalog is not a
prerequisite for writing or running the first provider test. Likewise, a ticket
dependency constrains its final completion; independent pure/empty-stack work
may proceed before the dependent live evidence is available.

Ticket closure uses its own executable scope. A provider ticket does not require
the all-provider LIVE command, and T004 does not require the full technical gate
which includes its downstream storage/API consumers. Existing `pure`, `mutation`
and `registry_metadata` selectors remain narrow. T003 adds the other named-check
selectors to the same runner and tests their dispatch/missing-evidence behavior;
their exact invocations remain Planned until implemented. No new runner or
separate approval layer. T015/T016 still require the complete aggregate commands.

T003/T014's **setup_activation** selection is implemented in the existing M7
runner. Its historical setup increment was installed at `7e252b8`, schema `v1_0731`;
current financial activation/setup proof is recorded in the worksheet. Its
[invocation and evidence](../../evidence/m7-setup-activation-selector-2026-11-11.md)
require the exact clean revision and a sealed controller under the fixed release
directory. It covers the initial `0720 → 0731` transition only. Operational
success remains an intermediate result until authenticated setup, collector
continuity and recovery evidence are reconciled. Exit 3 does not authorize
retrying a migration that already started; inspect its actual journal and use
the applicable recovery path. Unfinished budget charts or the first provider's
money do not prevent this setup increment. `AUTO-M7-DEPLOY` full-slice verification
and T014 closure retain their later dashboard requirements. This is one routine
with explicit scope, not a new deployment framework or permission ceremony.

When an external prerequisite fails, record the exact ticket, observed error,
affected test and smallest required action. Keep independent tickets running.
Request owner action only through a tested workflow with its URL/host and the
expected outcome. Do not ask again for an account list or acceptance already
recorded. Credentials and account configuration remain owner-controlled.

Source access is checked before promising a first monetary result. A subscription
account alone proves neither an API billing organization nor administrative
access. If no provider can supply a real monetary report, report that specific
S1 live blocker; an empty setup page or request-count report cannot close S1.
No silent fallback to scraped/private endpoints or spending to generate data.

Before rollout, distinguish database recovery from secret recovery. Backups
exclude keys: restored bindings with missing local entries are Credential
required, not Connected. Preserve the selected protected `.env` during normal
upgrade, verify binding presence without inspecting values, and test recovery
on isolated storage. Root owns T014; full multi-host backup tooling remains M8.

Progress reports name the latest visible result, ticket/evidence, remaining
first-slice work and actual blocker (or none). Report local, committed, pushed
and installed states separately. Re-estimate at the first installed vertical;
the 7–12-day planning range is not a guaranteed date or an authorization to
extend scope. Routine corrections stay under this plan version.
