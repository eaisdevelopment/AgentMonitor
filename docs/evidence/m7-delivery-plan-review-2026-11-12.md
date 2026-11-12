# M7 delivery-plan review: usable screens and a finite finish line

Status: planning review within approved focused plan 1.1.0. Product
implementation and full milestone acceptance remain unfinished. This record
does not reopen approval or replace the existing ticket catalog.

## Scope and inspected baseline

Owner requested deep planning for UI, budget calculations and foreseeable
delivery gaps, with a simple first working version rather than another M5 loop.
Reviewed integration worktree `codex/m7-api-budgets` at `ee1df6a`, its focused
execution plan, worksheet, UI/calculation rules, M05 increment, ticket catalog,
completion runner, public contracts and genuine-history/browser test seams.
Recorded installed revision remains in the worksheet; no runtime verification
or deployment is claimed by this planning review.

Requirements: FR-BUDGET-001..006, FR-ORG-003, FR-ACC-001..004/006;
acceptance M7-A01..A10, with existing M7-MATH-01..16. Primary owner: root
integration; M05 owns calculations, P02 UI, A01/A02/A03 source semantics.
Independent read-only reviews covered UI journeys, financial meaning and
collection/completion boundaries. Root checked their findings against files.

## Decisions and concrete corrections

| Finding | Decision / reason | Rejected alternative | Existing tickets |
|---|---|---|---|
| Worksheet records genuine Ollama USD costs, while execution order/check rows still exclude T009 or say counts only | Use available monetary reports now for exact stored API/DOM proof; use an actual monetary collection result for commit/retry/reopen. Correct stale text and task mapping | Waiting for new Anthropic/OpenAI setup before any money demonstration; counting balances or requests as spend | T005/T009–T012/T014 |
| Unresolved corrections could mean waiting for proof that a complete report will never change | Require declared replacement/adjustment semantics for the selected report. Future revisions are allowed; each immutable selection has its own rate | Permanent rate unavailability or adding revised and original costs together | T013; M7-MATH-03/04/05/09/15 |
| Named completion checks are partly unimplemented and existing generic tests can select counts-only reports | Name exact current test seams, missing monetary assertions and planned wiring in worksheet section2. Finish each check with its behavior | Assuming a named selector is implemented; building another runner or postponing all verification until release | T003/T005/T010–T015 |
| An earlier setup-form failure is recorded but not assigned | Assign diagnosis to T011 and installed proof to T014 using existing sanitized probes; establish UI versus probe cause before fixing | Erasing failure after a later pass; arbitrary reruns; resetting owner configuration | T011/T014 |
| Gate documentation says installed runtime is still M6 | Retain M6 historical acceptance and link current installed M7 state; refresh outdated contract-version recap | Reopening M6 or treating old versions as current consumer targets | T003/T014 |
| Rate UI needs precise compact presentation | One currency/day row with actual sample dates and separate estimate/reason; keep real balances visible when their compatibility is unknown | Large status cards; a missing-funds message when funds exist; implying a 30-day average from a shorter sample | T013/P02 |

These are corrections and delivery decisions inside the approved scope, not new
features, milestones, checks, dependencies or owner configuration tasks. Ticket
IDs, statuses, dependency graph and M7 acceptance inventory remain unchanged.

## Retained boundaries and omitted machinery

The existing plans already specify exact signed decimals, currency/cost-basis
separation, shared-pool deduplication, complete versus empty/partial coverage,
replacement rather than repeated-poll summation, scope/key generations,
three-complete-day minimum rate, seven-day forecast horizon, separate funds
allocation/freshness eligibility, and genuine-source reconciliation. Retain
those rules and their existing test cases; no new financial model is needed.

The existing UI plan already specifies API-only/mixed accounts, all-page filters
and totals, low-state thresholds, pinned detail/history, navigation/sign-in
return, refresh versus collection, stale-data retention, keyboard/zoom/widths
and source-chart/table agreement. Retain these existing screens and controls.

No new dependency, general analytics framework, forecast storage, queue, router,
interval-stitching engine, financial alert policy, inference spend, or local
Ollama work. Source-owned evidence and additive public contracts precede any
remaining M05/P01/P02 integration; this review itself changes no contract/code.
Security, privacy, migration and license behavior are unchanged. No provider
request, credential access, account edit or user-agent control was performed.

## Delivery and estimation

The [worksheet](../plans/integration/m7-delivery-worksheet-2026-11-11.md)
owns the order: available-money journey, prepared daily/rate packet, remaining
frozen provider and supported breakdown coverage, outstanding lifecycle/UI
evidence, retention/recovery, and final installed reconciliation/publication.
UI checks travel with each visible increment. The catalog remains the sole
tracker; a prepared file, local change or partial pass does not close a ticket.

Anthropic/OpenAI billing access remains necessary for their own mandatory live
lanes; missing access cannot pause unrelated work. Numerical exhaustion evidence
is conditional on genuine inputs. No repeated account-code attestation is added.

The old 7–12-day estimate is not a new deadline. The next monetary packet is the
explicit point to measure remaining effort, with engineering work and external
wait reported separately. It no longer waits for another provider's enrollment.
An unmeasured finish date would conceal the substantial remaining source/check
work; the finite tickets and fixed acceptance, not a date guess, define closure.

## Verification

Executed on the reviewed documentation changes:

- `python3 tools/automation/run.py AUTO-DOCS-CHECK`: Passed, 400 Markdown files.
- `python3 tools/automation/run.py AUTO-M7-PLAN-CHECK`: Passed, sixteen tickets,
  five stories and ten acceptance items traced.
- `python3 tools/automation/run.py AUTO-PLAN-CHECK`: initially Failed on the
  automation-standard digest/byte count after its stale runtime statement was
  corrected. Regenerated the snapshot with `tools/planning/render_snapshot.py`
  and appended scoped rebinds without rewriting historical attestations;
  rerun Passed (synchronized). Only that control's digest/byte count changed.
- `git diff --check`: Passed.
- Independent final diff review: no must-fix findings; verified unchanged
  ticket IDs/status/dependencies/acceptance, existing referenced test seams,
  and the single-control snapshot change with append-only historical rebinds.

No production tests or Red/Green claims are made for this documentation-only
change. Required implementation tests and their expected failures remain mapped
to existing tickets and worksheet check names. These results validate planning
coherence, not implementation, installed behavior or M7 completion.

## Follow-up planning reconciliation at 4a64417

Re-read the current worksheet/catalog and the staged monetary verification
packet without changing its production or test files. Preserve that packet's
recorded checks; this planning follow-up did not run a browser or deploy code.
Independent M05 and P02 read-only reviews found these remaining corrections:

- Remove the worksheet's stale claim that the retained monetary display journey
  still needs its first proof. Fresh commit/retry, interrupted receipt recovery,
  provider comparison and full filtered shared-pool totals remain open. Daily
  rate integration stays next; this review does not change ticket completion.
- Reproducibility means the same report **and pinned as_of/evidence context**.
  An explicit snapshot advance can change the eligible sample. Calculation,
  UI and T013 steps now require its actual sample bounds.
- Name the already allocated compact forecast endpoint as the M05/P01/P02
  handoff. Keep account summaries compact, avoid full-report UI reads, keep the
  analysis query independent of history cursors, reject old-context responses,
  and isolate analysis errors from spend/history/quota sections. Reuse the
  existing USD half-even/sub-cent display policy with exact rational details.

Rejected: a second analysis response on every history page, a new analytics
framework, repeated already-valid money checks as a new first-delivery hurdle,
new tickets or an additional owner approval. Scope stays sixteen tickets, five
stories and M7-A01..A10. Primary owner remains M05 for financial semantics;
root owns integration, P01 transport and P02 rendering. The planned additive
CTR-CAP-007 budget variant is clarified, not published by this documentation
change; existing installed contracts remain unchanged. No schema, dependency,
license, security or credential-custody change.

Changed planning artifacts: worksheet, calculation rules, UI journeys, M05
increment, catalog T013 steps, and this review record. Existing staged
verification work is preserved. Required implementation Red/Green and real
HTTP/browser checks remain in T013; this document is not their substitute.

Follow-up validation: `AUTO-DOCS-CHECK` Passed (401 Markdown files),
`AUTO-M7-PLAN-CHECK` Passed (16 tickets / 5 stories / 10 acceptance items),
`AUTO-PLAN-CHECK` Passed (synchronized), and `git diff --check` Passed.
No production implementation, deployment or M7 completion is claimed.

Independent final M05 and P02 diff reviews found no must-fix issue. They
confirmed the unchanged scope, compact allocated API, pinned sampling context,
exact rate representation and separation of retained proof from open work.
