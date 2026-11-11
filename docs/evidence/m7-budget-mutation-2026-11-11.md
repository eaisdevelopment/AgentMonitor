# M7 exact money and report selection: critical mutation evidence

- Status: Passed for seven targeted pure-policy mutations; not full T004 or M7 completion.
- Scope: focused plan 1.1.0, T004, M7-CAP-MUT-001.
- Requirements: FR-BUDGET-002/003/005; AC-TEST-001/005, AC-UI-006; M7-A02.
- Rules: M7-MATH-04/05/09/10/12/13/14 in the
  [calculation contract](../plans/integration/m7-calculation-and-data-rules.md).
- Contracts exercised: CTR-COMMON-003 exact conversion and M05 budget/report policy.
- Authorization: root explicitly approved this bounded targeted mutation scope
  within [owner-directed M7 implementation](m7-implementation-authority-2026-11-11.md).

## Method and boundaries

Reuse the existing mutation runner's isolated-copy/subprocess method and `_run`
helper. Copy actual backend source and three existing pure test files into a
fresh temporary directory. Run the unchanged baseline first. Apply each of seven
reviewed source substitutions only in that copy; restore its original content
between mutations. Never alter working-tree production files or runtime
collaborators. No new mutation framework or dependency is introduced.

Each mutant must collect the same number of tests as the baseline, return pytest
assertion failure, include at least one behavioral assertion failure, and have
no collection/setup error or skipped test. A crash, timeout, import failure or
zero-test result cannot count as a killed mutant. The existing no-skip plugin is
copied unchanged into the isolated workspace. Only pure constructed domain values
are used; there are no provider responses, accounts, storage or HTTP fixtures.

## Results

`backend/.venv/bin/python -m unittest tools.automation.test_m7_budget_mutation_policies`
was executed with the existing admitted backend Python:

- Unchanged baseline: **59 pure tests passed**.
- Seven targeted mutants: **all killed** by behavioral assertions.
- Full bounded mutation test: Passed, 11.119 seconds on first execution.

| Mutation | Incorrect behavior detected |
|---|---|
| Context-sensitive `scaleb` conversion restored | Admitted decimal digits round under caller precision |
| Negative cost input clamped to zero | Signed adjustment no longer reduces compatible cost |
| Currency guard bypassed | USD and GBP participate in one arithmetic result |
| Half-up replaces half-even ties | Reported display/percentage tie rounding violates the rule |
| Oldest report selected | Corrected complete report fails to replace older cost |
| Partial report admitted as current | Incomplete later result displaces complete current coverage |
| Empty complete report rejected | Removed charge reappears from an earlier report |

These are targeted mutation results, not an exhaustive mutation score for all
M7 code, a live correction observation, or a financial/provider reconciliation.

## Canonical integration and quality

The existing `auto_m7.py` technical lane now executes this mutation test. The
explicit partial command also passed:

```text
python3 -m tools.automation.implementations.auto_m7 --lane mutation
1 passed, 7 subtests passed
M7 CHECK mutation: PASSED
M7 RESULT: PASSED — pure policy verification only; no database, HTTP, browser or provider claim
```

Ruff lint/format and strict mypy on the changed runner and mutation test passed.
Full technical, live, browser and deployment checks remain independently required.
No services, default profiles, accounts, credentials, migrations, dependencies or
licenses changed. Temporary source/test/report copies are removed by their
context manager. Root owns commit/integration; no commit was made by this agent.
