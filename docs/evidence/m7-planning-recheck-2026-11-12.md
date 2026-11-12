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
