# M7 plan refactor: findings and bounded review

## Current review at 62b1b9f — UI, financial meaning and finite delivery

The renewed owner request is a planning refactor. Changes in this review are
documentation and task/status metadata only; they do not change product code,
services, accounts, credentials, provider state, dependencies or public code.
Focused plan 1.1.0 and M05 increment 0.3.0 retain their existing approval and
scope: sixteen tickets, five stories, ten M7 acceptance items. No new approval
cycle, gate or framework was introduced.

Root inspected the real CTR-CAP-006 2.2.0 account query, financial React panel,
runner/checker and installed-increment evidence. Three independent read-only
reviews, assigned under the SDLC/runbook, covered P02 journeys, M05 math and
root delivery. Accepted findings were applied to their owning documents and
the existing ticket catalog:

| Finding | Bounded correction and ownership |
|---|---|
| T005 closure waited for a complete provider ticket despite a first-report handoff | Remove whole-provider dependency; require genuine monetary commit/retry/reopen and source lineage in T005's executable persistence check. T015 still requires all providers |
| Natural correction observations described as both optional and mandatory | Separate mandatory pure policy/real monetary persistence from conditional live corrections/empty results; preserve each non-pass disposition, T003/T005/T015 |
| Current overlay and T014 steps contradicted installed schema0733 proof | Mark M7/Stories in progress, retain unpassed full exit and unrecorded acceptance; preserve accepted M6 as historical evidence; use worksheet for current state |
| Existing Ollama funds have no route through billing-connection-only account query | Specify additive CTR-CAP-006 funds read using published cloud membership and quota-window ports, provider mapping in A03, no duplicate account/pool/table, T010/T011 |
| Shared link/reload state omitted the immutable report selector | Authorize/preserve opaque financial context/report through navigation and sign-in; explicit refresh replaces it, T010/T011/T012 |
| Historical spending could appear to explain today's balance | Show per-funds observation time beside amount, separate from spending period, T010/T011 |
| Empty component could imply whole-account exhaustion | Preserve non-constraining fund semantics; separate included/purchased components and account severity, T004/T010/T012 |
| Forecast ignored known credit expiry | Apply existing renewal bound to selected-credit expiry, T013/M7-MATH-15/16 |
| Chart put every adjustment below zero | Plot by actual sign; retain adjustment meaning, T013/M7-MATH-09 |
| Retention promise had no executable handoff | M05 participant, existing M08 invocation, real isolated SQLite cutoff/ref-preservation proof in T013; T015 verifies later installed invocation with existing continuity check |
| Acceptance mappings omitted test-integrity/interactive evidence and UI/history responsibilities | Map AC-TEST-002/004 and M7-A01/A06 to existing ticket obligations; no repeated account attestation |
| Read-only refresh could imply provider collection | Plan label Refresh view separately from Collect now; no behavior change in this review |

Follow-up review caught one setup-state contradiction: absence of a separate
billing binding must not send an existing Ollama cloud account to duplicate
setup. The state table now tests absence of both usable billing and cloud
resources and selects the action from published capabilities.

The revised [worksheet](../plans/integration/m7-delivery-worksheet-2026-11-11.md)
defines mandatory/conditional evidence and ordered visible increments. The
[catalog](../plans/integration/m7-ticket-catalog-v1.json) remains the only ticket
tracker. No implementation ticket was closed by this review. The original
7–12-day estimate is not a measured remaining-work promise; reassessment stays
at the first installed monetary journey. No additional owner input is needed
to apply this planning correction.

The initial AUTO-DOCS-CHECK rejected a planning-document path inside the status
overlay's evidence array. It was replaced with this actual review-evidence
path; the check was not weakened. No new production tests or Red/Green claim
apply to these documentation-only edits. Live verification and full M7 exit
remain outstanding.

Final real-checkout validation: `AUTO-M7-PLAN-CHECK` passed (16 tickets, five
stories, ten acceptance items); `AUTO-PLAN-CHECK` passed the synchronized
baseline; `AUTO-DOCS-CHECK` passed (377 Markdown files); `git diff --check`
passed. The planning checker proves structure/references/dependencies, not
financial correctness, complete implementation or live acceptance. Independent
math/delivery follow-up reviews found no remaining contradiction in their
bounded changes; the UI follow-up correction is recorded above.

---

The original review below is historical planning evidence. The later approved
implementation is recorded in the authority/progress documents. The follow-up
planning review at the end records current clarifications without replacing
the historical approval or claiming delivery.

- Status: planning refactor; production changes and M7 live verification Not Run.
- Authority: owner requested deeper UI/calculation planning, simplicity and a
  working first slice. This does not record implementation or credential approval.
- Previous plan commit: `f21ee7d`; prerequisite verification: `a47fc53`.
- Proposed versions: execution 1.1.0, M05 increment 0.3.0, ticket schema 1.1.
- Requirements: FR-BUDGET-001..006, FR-ORG-003, FR-ACC-001..004/006;
  AC-UI-002..006, AC-HIST-001, AC-LIVE-004/005/007, AC-TEST-001..006.

## Concrete problems found and decisions

| Finding in real source/plan | Decision and ticket |
|---|---|
| T010 current UI/HTTP waited for T013 forecasts; no first usable dashboard | Current/list/history HTTP and exact UI first; T013 owns later chart/breakdown/forecast enhancement. S1 is a whole owner journey, T010–T012/T014 |
| AccountPage branches on provider key and shows CLI login/processes to every Claude/Codex account | API-published resource purpose controls sections; API-only creation and mixed-resource account behavior explicitly covered, T002/T011 |
| Existing account creation does not navigate to the new ID | Creation returns ID and opens its actual detail URL, T002 |
| Filters belong to quota component; first account/organization pages can omit records | Shared parent filter state and explicit continuation/coverage, T012 |
| Local credential command lacked per-binding/remote-browser journey detail | Installed command contains nonsecret binding selector, confirms provider/label/group, hidden local entry; host instruction and clipboard fallback, T002/T014 |
| No distinction among spend, balance, soft threshold and enforced limit in summary | Separate formulas/labels, supported-only remaining/percent, exact currency/period/cost-basis groups, T004/T010/T012 |
| Two credentials can access one billing pool | Canonical resource identity or disclosed owner assertion; ambiguous overlap excluded from totals, T002/T004 |
| Latest bucket alone leaves phantom charges when a complete revised report removes a row | Durable complete-report coverage/replacement plus immutable prior history, T005 |
| Empty complete report conflicts with current internal receipt/run invariants | Additive budget variants support real coverage without invented facts/events; existing HTTP observation-ID array already permits empty, T004/T007/T010 |
| Exact primitive can round allowed values | Small context-independent conversion correction and pure range/cancellation tests, T004 |
| Proposed 200-record child jobs introduce new scheduler semantics | One bounded report/run, sequential pages and one atomic commit; measured limits and safe partial outcome, T007 |
| Proposed persisted forecasts/events add unnecessary state | Pure bounded query over retained facts, no new forecast tables/events, T013 |
| Global organization budget aggregation was missing from minimal UI advice | Backend grouped totals, complete filtered inventory and exclusion reasons; no mixed-currency scalar, T010/T012 |
| Different moving report cutoffs make cross-account totals incomparable | Default completed UTC-day ranges with common midnight cutoff; native extra partial buckets remain separate |

## Reproduced exactness finding

Read-only pure-domain probe used the actual production class from
`backend/src/agentmonitor/contracts/common_quantity_v1.py`, with constructed
no-I/O values only. Under `localcontext(prec=28)`, coefficient
`12345678901234567890123456789012345678`, scale 0, produced:

```text
Round-trip exact: False
Current result: 1.234567890123456789012345679E+37
```

The permitted input has 38 digits; the contract permits up to 78. The refactor
does not fix production code; it adds this demonstrated prerequisite to T004.
No account data or provider response was used for the probe.

## Sources and inspection limits

Source inspection covered actual account/Overview/connection React components,
capacity and collection contracts, immutable migrations and existing scheduler
semantics. No active shared debugging browser was found on the checked local
ports; no rendered-M7 UI or live financial reconciliation is claimed.

Official [Anthropic analytics documentation](https://platform.claude.com/docs/en/manage-claude/usage-cost-analytics-api)
was rechecked for beta status, cents/credit basis, empty reports and data watermark.
The [Ollama usage](https://docs.ollama.com/api/cloud-usage) and
[balance](https://docs.ollama.com/api/balance) pages distinguish user/team usage,
shared balances and fixed report ranges. OpenAI's endpoint-specific official
OpenAPI schema was rechecked for administrative authentication, daily costs and
grouping. See [provider discovery](m7-provider-discovery-2026-11-11.md).
Documentation establishes capability, not credentials or observed account values.

## Independent review and correction batch

Two independent module reviews were authorized by SDLC Phase 3/runbook planning
sequence: P01/P02 journeys/dependencies and M05 financial/data semantics.
Neither reviewer changed files, credentials, profiles or services.

The bounded final review identified two remaining corrections:

1. T011 closes on real built detail/direct URL/history, T012 adds Overview
   navigation, T014 proves installed service. Their definitions no longer
   require later dependent tickets to be complete first.
2. Numeric exhaustion requires strictly positive headroom and rate. Zero/
   negative enforced headroom yields observed depleted/exceeded state, not a
   calculated past date. M7-MATH-06 covers limit 100, spend 110, positive rate.

Both corrections are applied in the current documents/catalog. No additional
blocking conflict was reported within the bounded review. This is planning
review evidence, not an implementation guarantee or promise of no surprises.

## Planning validation

The real updated catalog initially failed the existing command with
`M7 PLAN: FAILED — invalid_catalog` because schema 1.1 was not admitted.
The validator now recognizes delivery slices/supporting documents and alternative
first-provider prerequisites. Four pure tests verify completion dependency
policy. Initial Red: two expected assertion failures (unfinished alternatives
and unknown alternative not rejected). After the implementation, all four passed.
No constructed value crossed an I/O boundary in these policy tests.

Final checks executed against this real worktree:

| Check | Result |
|---|---|
| `python3 tools/automation/run.py AUTO-DOCS-CHECK` | Passed; 321 Markdown files |
| `python3 tools/automation/run.py AUTO-M7-PLAN-CHECK` | Passed; 16 tickets, five stories, ten acceptance items |
| `python3 tools/automation/run.py AUTO-PLAN-CHECK` | Passed; synchronized baseline |
| `python -m unittest tools.planning.test_m7_prerequisites tools.planning.test_validate_plans tools.automation.test_run.AutomationRoutineTests.test_real_catalog_defines_every_mandatory_routine` | Passed; 17 tests, using the existing backend virtual environment |
| `ruff check tools/planning/validate_m7_tickets.py tools/planning/test_m7_prerequisites.py` | Passed |
| `ruff format --check tools/planning/validate_m7_tickets.py tools/planning/test_m7_prerequisites.py` | Passed; two files |
| `git diff --check` | Passed |
| `python3 tools/automation/run.py AUTO-GIT-PREFLIGHT` | Passed for local commit only; remote/upstream not claimed |

Full M7 technical/live gates remain unimplemented; the existing historical
66 prerequisite-test pass is not reclassified as M7 acceptance.

## Scope and handoff

Changes are limited to focused plans, ticket detail, planning checker/tests,
indexes and this evidence. No backend/frontend product code, service, migration,
accounts, provider profiles or dependencies changed. No key was read or stored.
The dashboard stays on accepted M6. The complete five-story/three-provider scope
remains; speculative frameworks and later product enhancements are explicitly
outside the exit criteria. The next action is owner review of plan 1.1.0.

## Follow-up planning review against the implementation at f21e367

The requested deeper planning review retains approved focused plan 1.1.0,
sixteen tickets, five stories and ten acceptance items. Routine clarification
does not create a new approval cycle. M7 implementation remains incomplete.

Two independent read-only reviews covered P01/P02 journeys and execution/test
dependencies. Root checked the financial rules, current contracts, ticket
catalog and governing SDLC. The following corrections are now in the owning
documents and ticket steps:

| Concrete gap | Correction within existing scope |
|---|---|
| T002 required installed controls provided by its downstream tickets | Candidate enrollment/status in T002; working verification/monitoring in T007; installed proof in T014 |
| Full technical/live checks could prevent their own prerequisite tickets closing | Existing narrow checks explicitly named; other scoped selectors are Planned T003 work; full aggregate checks remain T015/T016 |
| T004 included forecast tests belonging to downstream T013 | Exact policy versus rate/horizon ownership is explicit in both catalog and calculation rules |
| API-origin flag could hide later subscription resources or admit empty quota rows | API capability routing covers account detail and Overview; initial intent is a pending fallback |
| Ollama API-only creation hid the existing cloud connection UI | T002 must reuse that usable flow and its canonical balance pool |
| First-page organization list and unknown label could misassign a record | Complete selector coverage and Organization unavailable versus Ungrouped acceptance |
| Shared-pool/scope controls were promised without a concrete ticket step | T002 owns correction, association and primary-group metadata; T004/T012 verify deduplication and disclosed exclusions |
| Stored credential, access success and monitoring could appear equivalent | Separate safe states, cancellation/retry, cleanup failure, generation invalidation and real first-reading handoff |
| Native rolling ranges could masquerade as complete UTC periods | Align complete buckets; retained coverage or explicit missing interval; no prorating |
| Subtotals could conceal missing/stale/overlapping reports | Compatible complete inputs, exclusion counts, retained original ages, no eligible reports means unavailable |
| Database recovery could imply secret recovery | T014 explicitly preserves selected local env on upgrade; backups exclude keys; restored missing entries require local entry |

Both reviewers rechecked their original findings after the corrections and
confirmed them resolved in the plan. This was a bounded correction review,
not a new acceptance layer or implementation verification.

Verification executed on the actual worktree after these corrections:

- `AUTO-M7-PLAN-CHECK`: Passed, sixteen tickets/five stories/ten acceptance items.
- `AUTO-PLAN-CHECK`: Passed, synchronized baseline.
- `AUTO-DOCS-CHECK`: Passed, 334 Markdown files at this checkpoint.
- `git diff --check`: Passed.
- Installed `agentmonitor-dashboard.service`: active; root HTTP returned 200.
  This is availability evidence only, not authenticated M7 browser acceptance.

The plan review changes only the execution/UI/calculation/M05 documents,
ticket catalog and this evidence. Separate in-progress credential-store code
and a pending credential-status test remain outside this planning change; they
are not promoted to passed/delivered by these results. No accounts, keys,
provider state, deployed service or published revision were changed by this
review. No new dependency, contract version, migration or test framework is
introduced. Pending scoped commands are explicitly Planned rather than invented
as available commands. The next implementation result remains the complete
first monetary account journey, followed by the retained full M7 scope.

## Further delivery review against 032a43f and the current candidate

This section records the owner's renewed request for deeper planning and simple
delivery. Earlier approvals remain applicable; focused plan 1.1.0, five stories,
sixteen tickets and ten acceptance items are unchanged. The new
[delivery worksheet](../plans/integration/m7-delivery-worksheet-2026-11-11.md)
is an explanation of execution order, not another gate or task tracker.

Root inspected the current billing command/service selection, provider source,
collection admission and receipt contracts, current ticket dependencies and
the owning UI/calculation plans. Independent A01 and P02 reviews were read-only;
the credential/financial agent also supplied a bounded implementation handoff.

| Finding | Resolution in the planning set |
|---|---|
| Owner entry command selects installed M6 while installation waited for first M7 data | T014 has an early setup activation increment, with a Planned scoped selection owned by T003/T014; full dashboard activation and ticket closure remain later |
| Existing checkpoint text still excluded all installed deployment | Corrected to exclude only final full-dashboard deployment; early setup activation remains required before owner key entry |
| Provider ticket completion could delay its own first-report consumers | Closure prerequisites remain strict; verified partial provider cost output can feed storage/UI before remaining categories/dimensions close |
| Official-beta manifest, profile-required billing target, one-request admission and nonempty receipt restrictions | Concrete smallest contract changes, owner, ticket and evidence are enumerated; no fake profile, private-source relabeling or new scheduler |
| Last UI verification failed in mixed-account attach flow | T002 explicitly retains the unresolved browser failure; command/copy/focus successes are not full setup acceptance |
| Large quota list could bury API billing | Existing shared filter area gains All/Subscriptions/API billing choice and counts; no extra navigation/application |
| Check connection can already return a genuine report | Persist/reuse that result once; enable schedules next due read instead of an unnecessary identical immediate request |
| Financial charts/reconciliation could silently round or misgroup | Exact API figures remain authoritative; signed chart values, snapshot changes and same-scope/time/basis/precision comparison are explicit |
| Calculation/M05 text still described corrected decimal conversion as broken | Marked historical with `6a87630`; outstanding exactness work remains separate |
| Speculative native-range gap could cause extra collection complexity | Rechecked official Ollama boundaries and corrected the calculation plan; actual unexpected gaps remain explicit source drift |

The independent execution reviewer identified the checkpoint contradiction and
missing scoped setup-selection allocation; both are corrected. The UI reviewer
reported no additional critical omission in its bounded review and confirmed
the mixed-account regression remains an implementation item. Neither review
claims product completion or absence of future bugs.

Verification on the real worktree after these planning edits:

- `AUTO-M7-PLAN-CHECK`: Passed; 16 tickets, five stories, ten acceptance items.
- `AUTO-PLAN-CHECK`: Passed; synchronized baseline.
- `AUTO-DOCS-CHECK`: Passed; 340 Markdown files.
- `git diff --check`: Passed.
- Installed `agentmonitor-dashboard.service`: active; root HTTP 200. This is
  availability only, not an authenticated M7 dashboard or provider pass.

No new test is needed for this documentation-only refactor. Existing catalog
and documentation checks validate the changed artifacts. No contract version,
migration, dependency, secret custody, license or deployment was changed by
these planning edits. Existing unfinished production/test/generated changes in
the worktree are preserved separately and are not certified by these passes.
No account/key configuration or publication occurred in this review.

Changed planning artifacts: execution plan, UI journeys, calculation rules,
M05 increment, ticket catalog, delivery worksheet and this evidence. All map
to the existing FR-BUDGET-001..006, FR-ORG-003, FR-ACC-001..004/006 and
M7-A01..A10 set. Remaining implementation is named in the worksheet and tickets;
M7 remains unfinished. The immediate delivery target is tested installed setup,
then the first real financial report on Overview/detail/history.

## Delivery refinement against 716cf92

The owner requested another deep planning review focused on UI, calculations,
predictable delivery and simplicity. This revision retains execution plan 1.1.0,
sixteen existing tickets, five stories and M7-A01..A10. It adds no approval,
dependency, financial feature or completion gate.

The worksheet now names the actual engineering handoffs from owner setup to
the first stored report, typed HTTP and installed Overview/detail. It records
which real empty-stack work can proceed without provider access and which
nonempty financial assertions must wait for a genuine report. Completed beta
classification and deadline fixes are no longer described as pending. The
current uncommitted Ollama browser correction remains explicitly unaccepted:
controls rendered, but a subsequent test request returned HTTP 403. Historical
mixed-account browser passes are retained, not relabeled as that new failure.

Read-only execution review found and mapped these concrete T003/T014 hazards:
selected source ignored by old deployment entry points, fixed old-checkout
recovery rejection, missing M7 predecessor in actual recovery tests, and backup
reopen being narrower than service restoration. Its bounded follow-up identified
the second migration transition after setup; the worksheet and catalog now cover
both `0720 → 0731` and actual installed `0731 → 0732/0733`. No installed
transition was performed during this review.

UI clarification keeps setup on the existing account page, shares Ollama cloud
controls, prioritizes spend/scope/state and avoids empty financial cards. Async
acceptance and concurrent-edit conflicts must reconcile actual state. Money and
usage precision rules now explicitly exclude overlapping count categories and
JavaScript integer rounding; a query's UTC cutoff stays fixed across midnight.
These map to existing T002/T004/T007/T010–T014 and M7-MATH-10/14/15, rather than
new tickets or an analytics framework. The worksheet lists each unknown, the
step that resolves it and the bounded outcome if the source cannot provide it.

Validation found an existing stale snapshot after `30f81d3` changed the
AUTO-MIGRATE scope description. Initial AUTO-PLAN-CHECK failed with
`automation-routines: snapshot control SHA-256 mismatch` and
`automation-routines: snapshot control byte count mismatch`. The canonical
snapshot renderer changed only that control's hash/size. The subsequent check
correctly required both review records to bind the new snapshot; no validator
or required check was weakened.

This planning change affects the focused execution/UI/calculation/worksheet,
ticket catalog and review records. It does not change published contract
versions, schemas, dependency/license policy or secret custody. Separate
in-progress frontend changes and their evidence remain outside the planning
validation claim. The dashboard service was active and root HTTP returned 200;
that is availability only, not authenticated M7 acceptance. M7 remains open.

Final verification after the independently reviewed snapshot repair:

- `AUTO-M7-PLAN-CHECK`: Passed; 16 tickets, five stories, ten acceptance items.
- `AUTO-PLAN-CHECK`: Passed; synchronized baseline.
- `AUTO-DOCS-CHECK`: Passed; 341 Markdown files.
- `git diff --check`: Passed.

No new tests were added for these documentation-only corrections. The canonical
planning/documentation checks exercise the changed artifacts. Planning files
are saved in `codex/m7-api-budgets`; this review does not claim they are pushed
or that the partial M7 product is installed.

## Execution-state reconciliation after c453fe0

The focused execution plan, worksheet and ticket catalog now distinguish the
locally tested initial setup selector from its still-unexecuted installed
transition. They retain both schema upgrades, partial-result handling and
journal-based recovery. The worksheet's earlier deployment findings remain
historical; links identify the selected-controller and real isolated recovery
corrections already tested. T004 links its aggregation evidence, and T009 is
In progress for the bounded Ollama source work, not live-verified or complete.

The fixed scope, UI/calculation decisions, contract versions, dependencies and
owner permissions are unchanged. This reconciliation adds no gate or approval.
Dashboard sign-in affects authenticated browser proof only; independent work
continues. No installed activation or account configuration was performed by
this documentation update.

Validation: AUTO-M7-PLAN-CHECK passed with 16 tickets, five stories and ten
acceptance items; AUTO-PLAN-CHECK passed synchronized; AUTO-DOCS-CHECK passed
346 Markdown files; git diff --check passed. These are planning checks, not a
claim that M7 is delivered. The updated documents remain local and uncommitted
at this checkpoint.


## Current delivery refactor against ad7a04e

The latest owner request is planning refinement: proper UI, budget calculations,
concrete detail and a simple working-first sequence. Implementation agents stopped
and preserved their existing uncommitted supervisor/current-query work. This
review changes planning documents and the existing ticket ledger only.

The delivery worksheet is consolidated around the actual checkpoint instead of
accumulating historical blockers. Locally committed `ad7a04e` contains financial
storage and billing authority/recovery; installed setup remains `7e252b8` on
`v1_0731`. Billing CLI integration, genuine monetary persistence and financial
HTTP/UI remain unfinished. Uncommitted query/supervisor code is not promoted to
delivered by this review.

Two independent read-only reviews checked actual P01/P02 routing/history and
M04/operations integration. Root inspected the relevant code and owning financial
plan. The resulting corrections are assigned inside the existing tickets:

| Finding | Smallest planned correction |
|---|---|
| No defined durable billing action-to-worker handoff | T007 reuses M04 request/run/lease storage and public claim/reclaim ports, capturing the exact source/range/generations; complete the fixed CLI |
| Request, adapter and supervisor deadlines could restart independently | T007 propagates remaining admitted time, reserves commit time and schedules Retry-After outside the current run |
| Ollama source candidate cannot use the Anthropic/OpenAI commit fence yet | T009/T007 connect the existing cloud-graph fence and shared balance/usage rate policy; no duplicate account/pool |
| Old report can hide latest failed call with no report | T010 composes M04 collection state separately from M05 selected monetary evidence |
| Revision history is not daily spend history | T010/T011 project pinned-report financial buckets; T013 charts the same facts; overlapping revisions are never summed |
| Shell strips query state and expiry loses safe return state | T011/T012 include DashboardApp.tsx and sessionBootstrap.ts, preserving allowlisted nonsecret selection only |
| Setup plan named a binding selector, but command uses account/resource | UI wording now matches the installed command resolver; owner types no IDs |
| Seven-day-only Anthropic candidate could be presented under thirty-day UI | T006 explicitly includes thirty-day admission; T010 keeps requested/actual coverage truthful |
| Open-ended provider category work could expand late | Existing discovery inventory fixes the category set; new future endpoints are later scope; supported-but-unimplemented remains unfinished |
| Registered checks could be mistaken for executable financial coverage | T003 wires each existing named check with the corresponding real boundary; schema-only evidence stays distinct |

The UI review follow-up confirmed its three findings addressed and found one
remaining midnight wording conflict in T010; corrected to preserve the pinned
cutoff until explicit range/filter refresh. The execution reviewer confirmed all five critical findings addressed; stale
T003 setup-activation and T007 migration wording was also corrected to their
implemented-local state. Existing formulas, safety rules,
16 tickets, five stories, ten acceptance items and approvals remain unchanged.
No new architecture, dependencies, migrations, contract versions, licensing or
secret custody are introduced by this planning change. No provider calls,
owner configuration, publication or service transition were performed.

Validation is recorded after the final corrections below. No new tests were
added for documentation-only changes. Existing production/test edits were
preserved separately and are not certified by planning checks.


Planning validation for this refactor:

- `AUTO-M7-PLAN-CHECK`: Passed; 16 tickets, five stories, ten acceptance items.
- `AUTO-PLAN-CHECK`: Passed; synchronized baseline, no snapshot repair needed.
- `AUTO-DOCS-CHECK`: Passed; 357 Markdown files.
- `git diff --check`: Passed.

Changed files: focused execution plan, delivery worksheet, UI journeys,
calculation rules, M05 increment, ticket catalog and this evidence. They map to
FR-BUDGET-001..006, FR-ORG-003, FR-ACC-001..004/006 and M7-A01..A10. Published
contract versions are unchanged. The planning refactor is saved locally; no
commit, push or installation is claimed. The next implementation result remains
a genuine stored report followed by its installed Overview/detail/history.
M7 itself remains unfinished.


## Planning reconciliation of the current uncommitted integration

The owner requested deep planning with proper UI, budget calculations and a
simple working-first delivery. Root reviewed the actual current source and
commissioned one bounded read-only P01/P02 handoff review under the runbook.
Existing implementation work is preserved; this planning pass makes no further
production, service, account, credential or publication changes.

The worksheet now reflects the actual uncommitted CLI/run factory/dispatch and
current-query increments. Their scoped pure and empty-boundary evidence is
linked without promoting it to genuine provider, populated SQL or browser
proof. T010 is In progress based on the retained real missing-route HTTP Red;
no implementation ticket is newly closed. Stale setup-not-installed wording is
corrected to the recorded installed `7e252b8`/`v1_0731` checkpoint.

| Observed gap | Existing ticket and bounded decision |
|---|---|
| Run factory uses a 64-hex audit fingerprint while worker claim still passes the 32-hex M03 catalog ID | T007 root must use the same admitted helper for service-target reconciliation, admission and claim; no weakening old quota contracts |
| Current-report repository output lacks the spend and latest collection result needed by the UI | T010 publishes one application result composed through public ports; M05 computes money, P01 maps, P02 renders |
| Several current report contexts can violate the aggregation policy's one-input-per-resource contract | T004/T010 select admitted ungrouped cost contexts per compatible group before aggregation; no total-plus-breakdown double counting |
| Planned budget routes and daily history lack a concrete selection identity | T005/T010/T011 use the existing canonical billing resource and pin history to the selected immutable report; no new storage entity |
| Provider category inventory could remain open-ended | Worksheet names the finite categories from recorded discovery; later provider additions are future scope |

The independent reviewer identified the application result, aggregation
cardinality and history-identity gaps. Their minimum fixes are now included in
the worksheet, owning M05/UI plan and ticket steps. No new gate, approval,
dependency, schema, financial feature or contract version is declared by this
review. Runtime-only secret custody, license and migration policy are unchanged.
Existing requirements FR-BUDGET-001..006, FR-ORG-003 and M7-A01..A10 still govern.

The first delivery remains one genuine report on installed Overview/detail,
followed by all required providers, supported analysis and the fixed exit.
No calendar completion claim is derived from test counts. The previous 7–12
focused-day figure remains an initial estimate, not a restarted countdown.
Validation results for this planning reconciliation follow below.

Independent bounded recheck confirmed all three consumer-contract findings
addressed consistently, with no remaining contradiction within that scope.
That is a planning review result, not a product pass.

Validation executed on this worktree:

- `AUTO-M7-PLAN-CHECK`: Passed; 16 tickets, five stories, ten acceptance items.
- `AUTO-PLAN-CHECK`: Passed; synchronized baseline.
- `AUTO-DOCS-CHECK`: Passed; 361 Markdown files.
- `git diff --check`: Passed.

This reconciliation edits the execution plan, delivery worksheet, UI journeys,
M05 increment, ticket catalog and this evidence. The earlier calculation-rule
refactor remains preserved. No new tests were added for these documentation
changes; existing canonical checks validate them. No commit, push, deployment,
new live financial verification or M7 completion is claimed.

## User-journey and delivery review after the first account panel

This planning-only pass responds to the owner's request for detailed UI and
budget planning without another expanding M5 cycle. It preserves the approved
1.1.0 scope, 16 tickets, five stories and M7-A01..A10. Current catalog state is
one planning ticket done, eleven in progress and four planned. No implementation
ticket is closed by this review. Existing uncommitted production work is preserved.

Root inspected the current account panel, query/action contracts, collection
routes and runner, and read the governing requirements, SDLC and runbook.
Bounded read-only P02 and boundary reviews supplied specific findings:

| Finding | Decision and existing owner |
|---|---|
| A newly completed Check can be excluded by the page's old `as_of` | T007/T010/T011: read live action status separately, then advance read time while keeping the selected reporting interval and replacing report/table together |
| History wording would discard an already useful bounded table | T010/T011: permit current-GET buckets for the initial visible increment; dedicated authorized history/cursors remain ticket closure requirements |
| Resource/currency alone cannot identify several cost bases/categories | T010/T012: label context subrows and carry context into detail; aggregate compatible ungrouped totals only |
| First Check transport exists but UI and monitoring mutation are unfinished | T007/T011: publish eligibility and actual run status, wire controls, retain Stored on runtime failure; never label 202 as Connected |
| Periodic 7/30-day behavior and coalesced wake handling need explicit implementation | T007: bounded staggered reports, durable fair dispatch, no missed-tick catch-up engine, browser-closed scheduled proof |
| Summary responses could multiply whole report bodies across accounts | T010: compact calculated values/selectors; separate bounded detail/history, measured using genuine available data |
| Boundary command reports 76 violations | Read-only review classifies 73 stale/missing declarations and three real private imports. T003/T007 repair exact declarations and owning application/composition surfaces; checkout remains red until rerun |

The three private imports are in `composition/billing_collection.py` (M02 access
policy), `composition/billing_run.py` (M05 codec) and
`composition/billing_worker.py` (Ollama worker start authority). Root confirmed
these source references. No production refactor or checker relaxation occurred
in this planning pass. The worksheet now distinguishes these remaining tasks
from the fingerprint/application query/action transport already corrected locally.

The planned run-status GET extends the existing T007 action workflow through
M04; its exact DTO/policy publication precedes implementation. It does not add
a queue or a new acceptance gate. This pass changes no published contract,
schema, dependency, license, credential custody or owner account configuration.

The next batch is fixed: integrate the current candidate and Check/status;
produce a genuine report with normal monitoring; show that same report on
Overview/detail and install it. Other providers, chart/breakdowns/conditional
forecast and release remain the existing later slices. No new approval request,
account list or repeated attestation is required by this planning work.

Changed planning files: execution plan, delivery worksheet, UI journeys,
calculation rules, M05 increment, ticket catalog and this evidence. Traceability
remains FR-BUDGET-001..006, FR-ORG-003, FR-ACC-001..004/006 and M7-A01..A10.
No new tests were added for documentation-only edits. Canonical plan/doc checks
are run against the saved files; their final results are recorded below.

The bounded integration recheck found no scope conflict and identified two
contract details now made explicit: durable range intent must distinguish
seven/thirty days and preserve the selected cutoff; a zero-fact successful run
needs its real `report_id` in the budget status DTO. The planned route is
`GET /collection-runs/{run_id}/budget`, leaving the generic list unchanged.
Root also checked that today's admission reconstructs only seven days from
`requested_at`; older pinned selections need an additive request context, not
a falsified timestamp. Fair dispatch means no starvation across successive
claims with the existing worker, not a new parallel scheduler.

Final planning verification (all exit 0):

- `python3 tools/automation/run.py AUTO-M7-PLAN-CHECK`: Passed, 16 tickets,
  five stories, ten acceptance items.
- `python3 tools/automation/run.py AUTO-PLAN-CHECK`: Passed, synchronized.
- `python3 tools/automation/run.py AUTO-DOCS-CHECK`: Passed, 365 Markdown files.
- `git diff --check`: Passed.

These results validate the planning artifacts only. Product import-boundary
corrections, genuine financial source/API/DOM evidence and installed financial
delivery remain unfinished. This planning pass made no commit, push or service
transition and did not configure owner accounts. The prior 7–12 focused-day
estimate is not reset or represented as measured remaining work.


## Reconciliation after the local Check/status integration

The current worksheet and execution plan now distinguish locally implemented
Check/status and passing boundary/build checks from the still-unverified genuine
financial journey. Stale statements that the status route is only planned or
that the current import boundary is red no longer describe the current candidate.
Historical failures above remain unchanged as evidence.

The plan remains 16 tickets, five stories and ten acceptance items. Its first
visible result remains a real monetary report on installed Overview/detail,
with normal monitoring; remaining provider coverage, history/breakdowns/chart,
conditional forecast, installation and release are still explicit existing work.
No new ticket, approval, feature, dependency or scope reduction was introduced.
No owner configuration or production implementation was performed by this
reconciliation. Existing uncommitted implementation was preserved and its local
quality command was rerun with captured output; see the integration evidence.

Validation: AUTO-M7-PLAN-CHECK passed all 16 tickets / five stories / ten
acceptance items; AUTO-PLAN-CHECK passed synchronized; AUTO-DOCS-CHECK passed
367 Markdown files; git diff --check passed. These are planning/static results,
not an M7 completion or deployed-financial-UI claim. The revised documents are
local; this reconciliation did not commit, push or deploy them.

## Current bounded refactor against b69d96a

Date: 11 November 2026. Authority: owner's request for deeper UI/calculation
planning, detailed tasks, fewer surprises and a simple working first release.
This is a planning-only review within approved focused plan 1.1.0. It does not
close an implementation ticket or the active full-M7 implementation goal.

Root consolidated the delivery worksheet rather than appending another parallel
plan. The existing catalog remains sixteen tickets/five stories/ten acceptance
items; statuses and scope were not inflated. Three read-only module reviews
covered P01/P02 journeys, M05 calculations and root deployment/verification.
Root reviewed their findings, applied bounded corrections, and requested one
recheck of those same findings. No new approval layer or dependency was added.

| Observed problem / source | Correction and owner |
|---|---|
| Execution/worksheet described ad7a04e and uncommitted work; current clean implementation was b69d96a with 85 operations | One current checkpoint separates committed, installed and unverified outcomes; root/T001 |
| `api/v1/schemas/budgets.py` exposes reports/spend while `BudgetAccountPanel.tsx` hardcodes the missing-funds text | Explicit supported balance/credit/limit fields with reasons through M05/P01; T010/T011 |
| Same-context action completion clears `BudgetAccountPanel` before replacement GET succeeds | Preserve prior values/times until successful atomic replacement; clear for actual context changes; T011 |
| UI state ordering grouped multiple actionable states without precedence | Fixed server rank: owner action, collection failure, incomplete/stale, low/depleted, current; secondary facts remain; T010/T012 |
| Retry copy promises a time not yet projected by action/financial status DTOs | Existing persisted M04 retry instant/eligibility to safe status API and UI; no countdown; T007 |
| T002 closure was too generic for promised scope/shared-pool controls | Explicit metadata/epoch/history/monitoring-invalidation checks; downstream filtered totals stay T010/T012 |
| 365-day retention but only current seven/thirty-day navigation specified | Previous/Next fixed stored windows and authorized retained report/scope references; no arbitrary backfill or calendar builder; T010/T011 |
| `budget_money.py` percentage display rounds 20.004% to 20.00 | Exact threshold comparison before formatting; paired 20.004/19.996 pure cases; T004/T012 |
| Three provider policy modules use different cost-basis identifiers | Separate labelled subtotals even when all are USD unless equivalence is established; T010/T012 |
| Secondary-organization shared-pool filter semantics were implicit | Show link and primary attribution, omit from secondary subtotal without calling it missing data; both selected counts once; T002 metadata/T010/T012 queries |
| Forecast time anchoring was implicit | Cost inputs end by funds observation and query as_of; anchor date to observation, invariant on reload; T013 |
| Full `auto_m7.py` lanes still return m7_boundary_runner_not_implemented | Wire actual suites and missing boundary assertions incrementally in the existing fixed catalog; T003, no new runner |
| Financial activation order unclear relative to full UI | Setup → storage/worker activation → first real report → full UI verification, all inside T014 |
| Cutover generic error obscures underlying phase/cause | Safe allowlisted diagnostic and actual revision/schema/journal reconciliation before retry/recovery; T014 |

The UI reviewer found one dependency ambiguity in the proposed ticket update:
T002's new step included filtered subtotal verification, which depends on later
Overview/query work. Root removed that requirement from T002 and retained it in
T010/T012. This preserves independent setup closure and avoids a circular delivery
expectation. The math and operations rechecks found no introduced contradiction
within their original findings. Reviews establish planning consistency, not
implemented behavior or a guarantee that no future defects exist.

### Installed-state observation and activation limitation

The prior financial activation attempt for committed
`b69d96a03e7013bdd23f30c82f33b5c5c1ba77d6` returned:

```text
M7 CHECK controller_preflight: PASSED
M7 CHECK candidate_started: FAILED (m7_setup_cutover_journal_review)
```

No activation was rerun during this planning review. Root and the operations
reviewer independently checked current state read-only:

- User service active/running; working directory is retained
  `7e252b869e28d62582b675f9e3cecc1612d6c5c4`.
- Read-only `alembic_version`: `v1_0731`.
- `.m6-cutover-journal.json`: absent.
- Loopback dashboard: HTTP 200.

`m6_cutover.py` collapses underlying failures into
`cutover_incomplete_review_journal`; pre-stop cleanup can remove a journal.
The outer `candidate_started` check name covers the cutover call and does not
prove startup occurred. The failure's underlying cause remains unproven. No
restore is justified solely by that generic error. HTTP availability is not an
authenticated financial acceptance pass. These findings supersede earlier
"installed activation has not yet run" checkpoint wording only; they do not
rewrite historical isolated-preparation evidence.

### Validation and impact

Executed against this actual planning diff:

- `python3 tools/automation/run.py AUTO-M7-PLAN-CHECK`: Passed, unchanged
  sixteen tickets/five stories/ten acceptance items.
- `python3 tools/automation/run.py AUTO-PLAN-CHECK`: Passed, synchronized.
- `python3 tools/automation/run.py AUTO-DOCS-CHECK`: Passed, 373 Markdown files.
- `git diff --check`: Passed.

Owning modules/contracts remain M02/M03/M04/M05/P01/P02/root, including already
published CTR-REG-014 1.4.0 monitoring and CTR-CAP-006 2.2.0 account queries;
this review changes no contract implementation/version, schema or dependency.
Requirements remain FR-BUDGET-001..006, FR-ORG-003, FR-ACC-001..004/006 and the
existing M7-A01..A10 acceptance mappings. Pure calculation examples are proposed
test cases, never database/provider fixtures. Production Red/Green is not claimed
for documentation changes. Live financial/browser verification was not executed.

Changed artifacts: execution plan, delivery worksheet, UI journeys, calculation
rules, existing ticket catalog, M05 focused contract reference and this evidence.
No product code, provider/account configuration, secrets, profiles, service or
running agent was changed. No new security, privacy, migration, license or
publication effect. Next implementation step is T014's actual failure diagnosis
and tested financial prerequisite, while independent T010/T011/T012 work proceeds.
The complete M7 goal remains open.
