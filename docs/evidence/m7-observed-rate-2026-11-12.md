# M7 observed spending rate: exact retained costs to compact detail

Status: integration in progress under approved focused M7 plan 1.1.0.
This packet is not full T013 or M7 completion. Installation and publication of
this production increment remain pending until the checks below finish.

## Scope and contracts

T003/T005/T010/T011/T013/T014; FR-BUDGET-002/003/004,
AC-UI-006, AC-HIST-001, AC-TEST-001/005 and M7-A06/A07.
M05 owns daily normalization, exact observed rate and conditional numerical
policy. Additive CTR-CAP-007 2.0.0 budget DTOs/ports leave quota forecasts intact.
A03 supplies source-owned interpretation; P01 exposes the already allocated
compact GET `/api/v1/budgets/{budget_id}/forecast`; P02 consumes its generated
client. Root owns composition and generated artifacts. No database migration,
new dependency, license, credential-custody or provider-profile change.

## Candidate behavior

- Normalize proven-disjoint costs once per complete UTC day; do not count model
  rows as elapsed days or add replacement report revisions together.
- Use the newest qualifying contiguous sample of three to seven days, at most
  200 contributing cost facts. Keep exact cost numerator, covered seconds,
  report/bucket references and sample bounds. No floating-point financial math.
- Display USD/day with half-even rounding and a positive sub-cent label. Other
  currencies retain exact rational details without guessed precision.
- Read retained provenance with report/receipt/run/digest validation. Current
  admitted Ollama daily snapshots establish replacement/disjointness, not zero
  gaps or financial freshness. Unknown source/parser semantics fail closed.
- Render one compact rate row in current or pinned financial history. History
  paging does not recalculate or fetch analysis. Abort old-context responses;
  analysis errors leave spend, balances, quota and history sections usable.
- Existing fund components do not establish financial scope/epoch or cost
  allocation; no production exhaustion date is fabricated. The pure conditional
  policy covers qualified balances, observation-time anchoring, depletion,
  expiry/renewal and a seven-day horizon. Pure numerical tests are not live
  numerical exhaustion evidence.

## Red and Green

Real behavioral Red before implementation:

- Existing genuine-money HTTP scenario failed `genuine_monetary_forecast_endpoint_missing`:
  actual new route returned 404 (1 failed, 1 deselected, 5.92s).
- Installed `e0ecf92` loaded a genuine monetary report/history, then
  `forecast.mjs` failed `observed_rate_missing`. No provider calls or mutations.

Prepared domain packet was copied tests-first. Integration initially had missing
implementation/import failures; these are not represented as behavioral numeric
assertions. Its independent audit added six failing assertions for missing rate
formatting and incorrectly admitted 201-fact samples, followed by Green.

Executed results:

- New daily/rate domain cases: 60 passed in 0.85s in the integration tree.
- Genuine-money HTTP with exact source-fact sum, duration/lineage, pinned reload,
  unauthenticated refusal and forbidden-query rejection: 1 passed, 1 deselected
  in 30.39s. This uses an unchanged private real SQLite copy and actual IAM/HTTP.
- Source evidence: 55 focused tests passed in the agent handoff, including a
  genuine private SQLite provenance/reopen/account-boundary check and pure
  normalized-value policy cases. Missing reader/mapper Red retained by handoff.
- Canonical `--lane browser --check source_history`: production build and
  nine tests passed in 67.51s, including real HTTP/history and built-browser
  analysis. Review found the new browser probe allowed a null rate; strict
  numeric evidence was then verified by the strengthened probe below.
- Canonical `--lane pure`: 824 cases and existing presentation checks passed.
- Existing mutation runner extended: 137 clean cases; all fourteen critical
  mutants killed, including seven daily/rate/display regressions. Private
  copied helper imports are verified; no external-boundary mocks are involved.

Quality initially failed because the new contract path/consumers were not yet
registered. Root added exact ownership, named public support ports and A03/FND
consumption; subsequent boundary check passed with zero violations and the
synchronized planning check passed. Independent review confirmed only three
control digests changed and all historical parent plans remain unchanged.

## Evidence limits and remaining work

These are retained-source reads, not fresh provider observations or provider-UI
reconciliation. Current code has no eligible funds/source evidence for a numeric
exhaustion date. Daily-total chart, separate balance series, supported breakdowns,
retention, full filtered totals, fresh monetary commit/retry, remaining provider
coverage and final M7 acceptance remain open in the existing tickets.

No live account configuration, credentials, default profiles or user agents were
modified. No provider request was made by these verification tests.


## Strict numeric browser and integration review

The strengthened probe rejects null rates, requires three to seven complete
consecutive UTC days, independently sums every source cost fact in the selected
sample, checks exact duration and lineage, and verifies displayed sample/rate,
reload stability, pagination independence and no mutations. The Python harness
also requires `rate_available=true` in its successful output.

Command: `PYTHONPATH=backend/src:.` with the admitted shared pytest,
`-c backend/pyproject.toml -q -s --tb=short -p tools.automation.pytest_no_skip
backend/tests/live/ollama/test_source_history_browser.py -k forecast`.
Result: **1 passed, 2 deselected in 14.63s**, exit 0, using the actual production
build and real private database copy. An earlier execution completed but its
terminal handle was not retained; it is not counted as evidence. The recorded
rerun began only after that process had exited.

The existing packet quality run passed formatting, typing, zero boundary
violations, generated OpenAPI/client compatibility and production frontend
build. Foundation boundary tests passed 191 cases in 11.34s. Subsequent changes
were the stricter browser assertion and planning clarification. All three
planning/documentation commands and Git diff/preflight passed. Installation and
installed-page verification remain the next boundary, not implied by this pass.
