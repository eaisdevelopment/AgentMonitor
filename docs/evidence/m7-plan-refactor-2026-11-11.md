# M7 plan refactor: findings and bounded review

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
