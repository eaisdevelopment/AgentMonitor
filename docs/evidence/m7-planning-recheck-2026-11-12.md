# M7 delivery planning recheck — 12 November 2026

Status: focused planning revision, not implementation, installed verification or
milestone acceptance. Requested outcome: deeper UI/calculation/delivery planning
with a simple working-first sequence. Existing approval, five stories, sixteen
tickets and M7-A01..A10 are unchanged. Primary owner: root integration; financial
semantics: M05. Existing uncommitted implementation work is preserved separately.

## Findings and resolution

| Finding | Decision and owning ticket | Rejected alternative |
|---|---|---|
| Provider coverage said frozen without a finite matrix | Execution plan enumerates Anthropic cost/usage, eleven OpenAI usage categories plus cost, and Ollama 7d/30d self/team/model coverage; T006/T008/T009/T013/T015 | Follow every future provider feature or call missing code Unsupported |
| Refresh and window navigation could change meaning | Pin navigation to read snapshot; Refresh preserves interval; Latest deliberately chooses today's cutoff; T010/T011 | Silently change the time window on reload/refresh |
| Known-report paging did not discover old-scope history | Bounded authorized metadata query feeding existing Source history; T010/T011 | New history application or treating daily paging as sufficient |
| Collect target unclear when no report exists | Resource/scope/category/interval plus server eligibility; no invented report ID; T007/T010/T011 | Generic report builder or automatic backfill |
| Rate and depletion conflated | Separate availability, source/funds freshness and component allocation; existing M7-MATH cases; T004/T013 | Hide useful rate without funds or invent dates from whole-pool spend |
| Required runner selections still unimplemented | Assign existing check names to each delivery increment; T003 integrates actual assertions with features | New gate framework or defer all executable acceptance until release |
| Competing current revision/instructions | Worksheet owns recorded installed state; catalog points to bounded-history evidence and retains historical revisions as history | Rebuild installed sorting/history or replay migrations |

Read-only independent UI, financial and delivery reviews identified these gaps.
Final review also caught wording about Next versus Latest and overly broad
component-allocation prerequisites; both were corrected. No provider-account,
credential, runtime, database, dependency, license or migration changes result
from this planning revision. Proposed API handoffs remain to be versioned/tested
before their implementation. Current history CTR-CAP-006 2.8.0, Overview 2.7.0,
and registry CTR-REG-014 1.5.0 remain the referenced published baseline.

The public Anthropic analytics and OpenAI usage documentation was reread for the
finite source inventory. Links and the documented-versus-live distinction are
in the [execution plan](../plans/integration/m7-execution-plan-2026-11-11.md).
No authenticated provider requests or owner configuration were performed.

## Verification and limits

- `python3 tools/automation/run.py AUTO-M7-PLAN-CHECK`: Passed; sixteen tickets,
  five stories, ten acceptance items, resolved references/dependencies.
- `python3 tools/automation/run.py AUTO-DOCS-CHECK`: Passed; documentation links,
  metadata and routing. Rerun after this record is included.
- `git diff --check`: Passed.
- No production TDD or live/browser/deployment pass is claimed by planning.
  The plan validator checks traceability, not feature completeness. Full M7
  executable checks still include unfinished implementation.

## Resulting delivery order

1. Finish useful detail interactions and demonstrate first genuine monetary
   source → storage → API → installed Overview/detail as soon as access exists.
2. Complete source lifecycle, captured collection intent, cooldown and historical
   selection; retain the current worker and query architecture.
3. Finish finite provider/range/dimension coverage, scheduling and recovery.
4. Add the same-fact chart, one-dimension analysis, conditional forecast and
   existing retention integration.
5. Reconcile the fixed source/API/browser matrix, run the full existing exit,
   verify installed/public revisions and demonstrate acceptance.

The [delivery worksheet](../plans/integration/m7-delivery-worksheet-2026-11-11.md)
owns this order and recorded baseline. The [ticket catalog](../plans/integration/m7-ticket-catalog-v1.json)
owns status/dependencies. No ticket was closed by this review. Owner/provider
access affects its live lane only; independent work must continue. Numeric
forecast and naturally unavailable error cases keep explicit conditional
outcomes. New enhancements remain deferred, not added to acceptance.

## Follow-up after installed manual billing controls

The owner requested deeper advance planning, proper UIs and budget calculations
without another expanding milestone. This follow-up inspected clean code baseline
`7083e43` (installed implementation recorded at `ef8fa86`) and refactored the
existing six plan/catalog files. No production changes, provider requests, owner
configuration, runtime changes or publication were performed in this pass.

| Concrete finding | Correction / existing owner | Rejected alternative |
|---|---|---|
| Repeated ticket steps still request installed routing, history and captured-context work | Consolidate packets, retain evidence and name only unfinished scenarios; T003/T006/T007/T010–T014 | Rebuild delivered components or add another tracker |
| Missing money is treated as incomplete in `capacity/domain/budget_overview.py` | Record exact complete-counts-only versus partial acceptance; T004/T010/T012 | Zero money or false incomplete coverage |
| Calculation rules demand a sort excluded by the UI plan | Keep account/organization/state sorts; monetary sort deferred; T010/T012 | New monetary ordering feature |
| Blanket credential-free restriction blocks pure ticket closure | Close T004 on its own pure/mutation scope; monetary I/O still requires genuine reports | Require credentials for mathematical policy tests |
| Browser formatting prohibition contradicts existing exact BigInt presentation | Allow presentation rounding only; prohibit client totals/ratios/forecasts | New API fields solely to move existing correct formatting |
| Mixed-account financial links land above unrelated process/quota content | Financial selection brings financial section into view; T011 | A new financial account page |
| Partly loaded chart can look like zero/missing source data | Same loaded immutable facts, explicit more-data state, M05 daily aggregation; T013 | Fetch-all requirement or client money summation |
| Usage categories/dimensions lack an explicit control handoff | Publish admitted source/category/dimension/unit choices; T006–T009/T013 | Hardcoded frontend capability guesses/query builder |
| Named check catalog exceeds actual CLI selectors | T003 adds each existing selector with its feature; current callable versus planned is explicit | Another runner or late testing phase |
| Final aggregate lacks a revision-bound persisted result | Minimal sanitized receipt binds clean checkout/installed revision/schema and named required/conditional outcomes; T003/T016 | Short-lived owner attestations or a new gate hierarchy |
| Empty source categories risk demanding manufactured activity | Required implementation/access separate from conditional populated examples; T015 | Treat absent examples as passed or spend to generate them |
| Provider-first/first-not-due dispatch risks starvation | Bounded fair eligible selection and later-resource proof; T007 | More workers or new queue infrastructure |
| Unconditional recollection conflicts with rolling intervals | Reconcile commit receipt; terminal expired authority; exact supported retry or separate new window; T007/T009 | Shift the request at restart |
| Historical setup transitions could be reused as final deployment proof | Same-schema current update plus real isolated restore/continuity; T014 | Replay installed migrations |

Read-only independent P02, M05 and collection/completion reviews supplied these
findings. Root inspected the cited code and reconciled the planning diff. A
bounded follow-up corrected ambiguous wording about unavailable totals; no new
feature or acceptance ID was added. Security/privacy/license/migration impact:
none from these document changes. Proposed additive contract handoffs are assigned
before implementation; this revision publishes no runtime contract version.

The worksheet now has eight delivery batches inside the same sixteen tickets,
with explicit UI demonstrations, integration prerequisites and check ownership.
The catalog retains all requirement/acceptance IDs, ticket statuses and dependency
edges. Mandatory scope remains five stories/M7-A01..A10; no milestone ticket is
closed by this planning pass. Existing monetary owner setup remains pending;
independent connected-provider, policy, UI and operational work does not wait.

Validation for this follow-up:

- `python3 tools/automation/run.py AUTO-M7-PLAN-CHECK`: Passed.
- `python3 tools/automation/run.py AUTO-DOCS-CHECK`: Passed.
- `python3 tools/automation/run.py AUTO-PLAN-CHECK`: Passed (synchronized baseline).
- `git diff --check`: Passed.

These are planning/documentation results, not production Red/Green, live-provider
acceptance or M7 completion. The edited plans remain local in the M7 worktree;
installed/public implementation was not changed by this planning task.

## Final scheduling clarification and recorded delivery

Read-only collection review at `50462c0` narrowed the T007 fairness work to
persisted selection order, both scheduled ranges, exact-context attempt lookup
and invalid-authority isolation. Global Ollama cooldown is correct behavior;
it must not be bypassed as a purported starvation fix. The worksheet records
these cases and the catalog retains installed manual cloud collection instead
of asking to rebuild it. No production code or runtime changed in this pass.

Earlier references here to local-only planning describe their historical pass.
The prior refactor was subsequently published with `bb43b67`; the evidence/probe
successor is `50462c0`. This final clarification remains a documentation change
until separately committed. Planning validation is separate from M7 acceptance.


## Final owner-facing sequence and stale-step reconciliation

Planning-only follow-up against committed baseline `92b6f64` and the existing
uncommitted T002/T011 implementation draft. The draft was preserved; this
follow-up did not implement, install or publish it. Requirements remain
FR-BUDGET-001..006, FR-ORG-003, the existing account/UI requirements and
M7-A01..A10. No ticket status or approval changed.

- The worksheet now leads with the next visible result and three checkpoints:
  working monetary journey, complete M7 screens, released M7. These summarize
  the eight existing delivery batches; they are not new tickets or gates.
- T010/T012 and the UI plan now retain the delivered `cd4f566` concurrent-read
  correction as regression evidence instead of instructing another repair.
- T011 distinguishes installed account views from the local API-origin to
  subscription-resource draft. Finish its evidence and installation; do not
  count a local field/client change as a working owner journey.
- The worksheet points at the delivered CTR-COL-002 2.6.0 scheduling handoff;
  historical 2.4.0 evidence remains history, not a new pending cloud action.
- Ticket dependencies constrain closure without preventing independent work.
  Required provider success and the fixed monetary acceptance remain required;
  natural populated examples and numerical forecast evidence keep their
  existing conditional disposition. No fabricated reports or new owner ceremony.

The calculation review retained the existing exact decimal, coverage,
whole-report correction, compatible subtotal, fund-component, UTC interval,
source-time and conditional forecast decisions. Their scenarios remain
M7-MATH-01..16; no new accounting or forecast framework is justified. The UI
review retained compact existing pages, independent subscription/API controls,
owner configuration, explicit unavailable states and pinned navigation.
A bounded independent P02 review confirmed the delivered-504 and local-routing
contradictions; both were reconciled in the worksheet, UI plan and catalog.

Changed in this pass: delivery worksheet, UI plan, ticket catalog and this
record. No public contract publication, migration, dependency, license,
credential or runtime change. Existing production/client/test modifications in
the checkout predate this planning follow-up. Validation below concerns the
planning artifacts only, not M7 implementation or live acceptance.

Validation for this follow-up:

- `python3 tools/automation/run.py AUTO-M7-PLAN-CHECK`: Passed; sixteen tickets,
  five stories and ten acceptance items traced.
- `python3 tools/automation/run.py AUTO-DOCS-CHECK`: Passed; 391 Markdown files.
- `python3 tools/automation/run.py AUTO-PLAN-CHECK`: Passed; synchronized baseline.
- `git diff --check`: Passed.

Result: planning clarification saved locally. No ticket is newly complete, no
new live test is claimed and no installed/public revision changed in this pass.

## Consolidation after the scope-editor draft

Reviewed committed baseline `23fd185` and preserved the uncommitted scope-editor
implementation. This pass changes planning artifacts only. The draft's separate
real HTTP/registry run completed with 38 tests passing; that is not its missing
built-browser Green, installation or M7 acceptance.

Three independent read-only reviews covered P02 journeys, M05 calculations and
M04/completion boundaries. Root checked the fund contract, runner dispatch and
existing test/helper paths. Material decisions, all inside existing tickets:

| Gap | Decision | Rejected alternative |
|---|---|---|
| Terminal status can overwrite a different selection | Only successful matching resource/authority/category/grouping/interval refreshes that financial view; T007/T011 | Replace values on every terminal event |
| Historical scope beside current Collect authority | Historical selection is read-only; existing Latest control returns to current scope; T010/T011 | Collect old scope with new credentials |
| No report yet for chosen breakdown | Preserve admitted nonsecret selection through existing routing; T007/T010/T013 | Dummy report ID or second router |
| Limit fields can imply unsupported headroom | Publish compatible calculation inputs/lineage before subtraction; T010 | Infer cash or headroom from same-currency amounts |
| Forecast paging independence can lose identity | Pin selected financial context, disclose sample bounds, reject incompatible funds; T013 | New-scope balance forecasting old-scope spend |
| Range composition sounds mandatory | Direct admitted 7/30-day reports suffice; T005/T010 | Generic interval assembler before useful money |
| Fairness has no finite proof | Fixed eligible-set two-round pure proof plus real successive eligible claims/ranges; T007 | Indefinite soak or artificial provider load |
| Recovery is too broad | Name five real boundary demonstrations using existing helpers; T007/T014 | New disaster-test platform |
| Final inventory/evidence moves indefinitely | Pin relevant configuration, invalidate affected resources only, separate source time from candidate verification; T015/T016 | Repeat every owner comparison after each metadata/doc change |
| Competing delivery instructions | Shorten worksheet; catalog alone owns status/steps, UI/math own rules | Another tracker or appended gate hierarchy |

No requirement, acceptance ID, provider inventory, ticket dependency/status or
approval changed. Primary owner remains root/M05; module/API handoffs are
assigned, not published as new runtime contracts by this edit. No secret access,
provider call, owner configuration, deployment, migration, dependency or license
change occurred. The first monetary source remains an external live prerequisite;
independent work remains executable. Final read-only review found no remaining
financial-identity/evidence contradiction. Its two wording corrections distinguish
mandatory local recovery from conditional provider failures and repeated eligible
contexts from concurrently active work under the single worker.

Validation for this consolidation:

- `python3 tools/automation/run.py AUTO-M7-PLAN-CHECK`: Passed.
- `python3 tools/automation/run.py AUTO-DOCS-CHECK`: Passed (392 Markdown files).
- `python3 tools/automation/run.py AUTO-PLAN-CHECK`: Passed (synchronized).
- `git diff --check`: Passed.

Saved locally in the M7 worktree. No installed/public revision changed and no
production completion is claimed. The implementation goal remains unfinished;
the worksheet names the next implementation packet and fixed completion scope.

## Working-first refinement at f786ea0

Planning review against committed `f786ea0`, preserving the separate uncommitted
billing-maintenance candidate. Root checked the real daily-history UI, cursor
error contract, capacity-history route and calculation handoff. Independent
read-only M05 and P02 reviews found four concrete acceptance ambiguities:

| Existing ticket / scenario | Clarified decision | Rejected alternative |
|---|---|---|
| T013, M7-MATH-03/10/15 | Count complete UTC days after proven-disjoint daily aggregation; multiple model rows are not multiple days | Duplicate duration or a rate from one day's rows |
| T013, M7-MATH-03/15/16 | Ineligible funds use rate-only query cutoff; keep selected financial identity and omit exhaustion date | Stale or unrelated balance suppresses useful recent cost rate |
| T010/T013, M7-UI-004 | Cost/usage chart uses report history; balance series reuses scoped capacity observations with a versioned snapshot handoff | Manufacture balance history from spend/current funds |
| T010/T011, M7-UI-003/004 | Rejected continuation restarts the same report from page one; unavailable report is a different recovery | Retry invalid cursor forever or silently select latest |

The worksheet now separates implementation-start inputs from ticket closure and
keeps one integration packet in flight. Finish the existing candidate, prioritize
the first monetary journey when access exists, otherwise advance independent
first-source chart/rate work. UI acceptance travels with each packet. The
execution-plan stage table no longer supplies a competing serial work order;
stale prior-scope discovery instructions now retain the installed implementation.
Catalog steps carry these decisions without new tickets, status changes,
dependency edges, provider endpoints, acceptance IDs or repeated approval.

Scope remains sixteen tickets/five stories/M7-A01..A10. No production change,
live test, deployment, provider configuration, credential read, migration,
dependency or license change was performed by this planning review. No new
runtime contract version is published here. Proposed missing balance snapshot
fields must use the existing producer/consumer synchronization before code.
The current maintenance implementation and its separate test evidence predate
this review; installed/public delivery of that candidate remains outstanding.

Bounded follow-up review confirmed the UI changes and corrected one math phrase:
enforcement evidence is required for limit-derived headroom, not for an
authoritative cash balance's component-depletion estimate. No broader feature
review or additional acceptance inventory was opened.

Validation:

- `python3 tools/automation/run.py AUTO-M7-PLAN-CHECK`: Passed; sixteen tickets,
  five stories and ten acceptance items traced.
- `python3 tools/automation/run.py AUTO-DOCS-CHECK`: Passed; 396 Markdown files.
- `python3 tools/automation/run.py AUTO-PLAN-CHECK`: Passed; synchronized baseline.
- `git diff --check`: Passed.

Saved locally in the M7 worktree. These checks establish planning structure and
references, not M7 completion, a new financial pass, deployment or publication.

## Delivery clarification against d5c6018

The owner requested deep advance planning while keeping the first implementation
simple. Root reviewed the existing fixed scope, requirements, current worksheet,
UI states, calculation rules and ticket dependencies. Independent read-only P02
and M05 reviews checked the user journey and financial semantics. Existing
uncommitted chart code and its earlier evidence were preserved, not delivered by
this planning edit.

- T013's next packet is the existing source-entry chart, independently of daily
  aggregation/rate. The worksheet had incorrectly bundled those deliveries.
  Source entries, daily totals and balance snapshots are explicitly distinct.
- T013/M7-MATH-03/10/15/16 retain a qualified historical observed rate with its
  sample dates/freshness limitation; missing fresh funds can prevent an
  exhaustion date without suppressing that rate. This resolves contradictory
  freshness wording, without changing the seven-day sample or financial identity.
- T002/T007/T010–T015 now have a concise six-action owner demonstration in the
  worksheet, linked from the execution plan. Existing provider, retention and
  recovery checks remain required; the demonstration introduces no new gate.
- Removed duplicated changing tracker counts from the worksheet. The catalog
  remains the sole status source. The frozen sixteen tickets, five stories and
  M7-A01..A10, approved scope and deferred list remain unchanged.

Changed: execution plan, worksheet, UI plan, calculation rules, T013 catalog
wording and this evidence record. No new production behavior, contract version,
dependency, migration, license, credential or account-configuration change.
No provider access, install, publication or live/browser success is claimed.

Validation for this clarification:

- `python3 tools/automation/run.py AUTO-M7-PLAN-CHECK`: Passed; sixteen tickets,
  five stories, ten acceptance items traced.
- `python3 tools/automation/run.py AUTO-DOCS-CHECK`: Passed; 397 Markdown files.
- `python3 tools/automation/run.py AUTO-PLAN-CHECK`: Passed; synchronized baseline.
- `git diff --check`: Passed.

Planning is saved locally. M7 implementation and final acceptance remain open.


## Consolidation against the prepared rate packet

Planning-only review at committed baseline `c49b6cd`, preserving the existing
uncommitted rate implementation and generated artifacts. The owner requested
proper UI/calculation/detail planning with make-work-first scope. This pass
changes the existing worksheet, calculation rules, execution-plan summary and
T013 steps; it creates no new tickets, gates, dependency or plan version.

- Condensed repeated installed-history narrative and duplicate work tables.
  The worksheet starts with the actual next deliverable: finish the locally
  integrated rate row through strict numeric browser proof and installation,
  then full filtered totals. Installed monetary/history controls are retained.
- Corrected two financial ambiguities: 7/30-day coverage comes from the directly
  admitted report, without cross-revision interval assembly; the bounded rate
  sample permits 200 contributing source facts, distinct from 3–7 daily totals.
  Existing M7-MATH-03/10/15 and T013 own the boundary cases.
- Distinguished retained monetary proof from remaining fresh commit/recovery,
  source comparison and full filtered shared-pool totals. Local API/UI code is
  not described as installed. The stricter numeric browser result is pending.
- Read-only independent P02 review found no additional acceptance decision gap.
  Compact layout, money/usage units, pinned navigation, unavailable states and
  isolated failures are already specified. Cursor recovery remains existing
  implementation work. Independent M05 review identified the source-fact limit
  ambiguity above; no new accounting framework is needed.
- Retained the fixed three-provider matrix, eight work batches, sixteen tickets
  and M7-A01..A10. No ticket status changed. Missing provider access affects its
  live lane only; no repeated owner confirmation is introduced.

Validation: `AUTO-M7-PLAN-CHECK`, `AUTO-DOCS-CHECK`, `AUTO-PLAN-CHECK` and
`git diff --check` passed again after the evidence/catalog update, all with
exit status 0. These checks establish document consistency,
not implementation or milestone completion. No runtime, owner configuration,
secrets, database, license or dependency changed in this planning pass. The
plan changes are local until committed/published; installed revision remains
as recorded in the worksheet. Production work already present is not claimed
as an output of this review.
