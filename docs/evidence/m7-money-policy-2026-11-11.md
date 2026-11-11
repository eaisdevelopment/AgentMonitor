# M7 T004 pure monetary policy evidence

- Status: Intermediate T004 contribution; local pure tests and focused static checks passed. Full T004/M7 acceptance is not claimed.
- Date: 2026-11-11, 14:38–14:41 UTC.
- Authority: [M7 implementation instruction](m7-implementation-authority-2026-11-11.md).
- Plan: [M05 focused increment 0.3.0](../plans/modules/m05-capacity/m7-budget-increment-2026-11-11.md), focused M7 execution 1.1.0.
- Requirements: FR-BUDGET-002/004/005, AC-TEST-001/002/003/006; arithmetic contribution to AC-TEST-005 remains subject to canonical mutation integration.
- Scenarios: M7-MATH-01/02/06/07/09/13/14 and pure percentage/availability boundaries in the [calculation rules](../plans/integration/m7-calculation-and-data-rules.md).
- Contracts: consumes unchanged CTR-COMMON-003 `CanonicalDecimalV1`/`ExactMoneyV1`; no public contract, API or database version change in this contribution.
- Checkout: `a91424881504389264362e8763c2fc1d79866502` plus concurrent declared M7 work, isolated `m7-api-budgets` worktree. Root separately corrected shared decimal conversion before this contribution.

## Behavior and scope

`budget_money.py` provides exact integer-aligned sum/subtraction, bounded exact
base-10 scaling, backend USD half-even formatting and exact formatting for other
currencies. It rejects empty sums, currency mismatch and final representation
overflow; intermediate cancellation is independent of input order and Decimal
context. Scaling can normalize a documented cents amount without assuming any
provider or currency exponent.

Headroom returns a signed amount with explicit soft/hard kind and remaining,
at-limit or exceeded state. It does not return cash or imply enforcement.
Percentage results retain exact numerator/denominator and declare method,
two-place presentation and half-even rounding. They preserve out-of-range values
instead of clipping. Missing/incompatible inputs or nonpositive denominators
produce no percentage. Nonzero USD below one cent is explicitly displayed as
`<0.01 USD` or `Negative <0.01 USD`, with original exact money available to callers.

The caller must derive `compatible=True` from validated typed report scope,
period, currency, cost basis and, for a hard limit, enforcement semantics.
These helpers do not validate source facts, select/deduplicate reports, infer
available funds, attach source IDs, calculate a forecast or change a balance.
Root owns those orchestration/contracts. Derived public results must carry their
source IDs from that context.

Files added only:

- `backend/src/agentmonitor/modules/capacity/domain/budget_money.py`
- `backend/tests/capacity/pure/test_budget_money.py`
- `docs/evidence/m7-money-policy-2026-11-11.md`

## Red evidence

Before adding the production module, the pure suite defined six required owned
operations and 44 cases. The first test ran to an explicit contract assertion:

```text
Failed: M05 has no published exact budget money policy operations
1 failed in 0.10s
```

This is new owned-capability availability Red, agreed with the integration
steward. It is not a claim that a numerical implementation returned a wrong
answer. The production module did not yet exist; no empty shell, deliberately
incorrect implementation, substituted collaborator or fallback arithmetic was
added to manufacture Red. The complete suite then reported `44 failed in 0.17s`
at the same missing-capability assertion. Numerical vectors first execute once
the real operation exists. Root's separate existing-conversion regression Red
must be retained independently.

Commands, working directory the worktree's `backend/`:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest tests/capacity/pure/test_budget_money.py -q -x
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest tests/capacity/pure/test_budget_money.py -q --tb=no
```

Both returned exit 1 before the production file was added, recorded at 14:38 UTC.
The existing admitted toolchain is selected explicitly; no package was installed.

## Green and refactor evidence

After the real integer implementation, the first command below passed all 44
new tests. Formatting and a strict-type correction followed: mypy initially
reported `Returning Any from function declared to return "int" [no-any-return]`
on integer exponentiation. The alignment helper now explicitly types the
integral power; all callers select the maximum source scale. No money behavior
or test expectation was weakened.

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest tests/capacity/pure/test_budget_money.py -q
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest tests/capacity/pure/test_budget_money.py tests/capacity/pure/test_budget_exact_arithmetic.py tests/capacity/test_quantity_and_health.py -q
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/ruff check src/agentmonitor/modules/capacity/domain/budget_money.py tests/capacity/pure/test_budget_money.py
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/ruff format --check src/agentmonitor/modules/capacity/domain/budget_money.py tests/capacity/pure/test_budget_money.py
MYPYPATH=src /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/mypy --strict src/agentmonitor/modules/capacity/domain/budget_money.py tests/capacity/pure/test_budget_money.py
```

Final focused results at 14:40 UTC: `63 passed in 0.32s`; Ruff `All checks
passed!`; formatter `2 files already formatted`; strict mypy `Success: no issues
found in 2 source files`. All commands returned exit 0. All 44 new cases are
pure; no skips/xfails. Test examples never cross an I/O boundary. Source parsing
and ordinary test-module loading do not provide provider/DB/HTTP evidence.

The repository-root canonical documentation command
`python3 tools/automation/run.py AUTO-DOCS-CHECK` also returned exit 0:
`DOCUMENTATION CHECK: PASSED (325 Markdown files)`.

## Remaining verification and impact

| Boundary | State | Explanation |
|---|---|---|
| Pure arithmetic/policy | Passed | 44 new cases; 63 with shared exactness and quantity/health regressions |
| Focused lint/format/typing | Passed | Both assigned Python files |
| Mutation gate | Not Run for this contribution | Root must add the approved critical money-policy surface to canonical mutation selection |
| Database, provider, HTTP, browser | Not Run | No implementation or claim at those boundaries; integration retains real-data requirements |
| Full T004/M7 canonical gate | Not Run | This isolated domain contribution cannot establish ticket/milestone completion |

No dependency/license, configuration, migration, provider profile or service
change. No credentials, live records, arbitrary environments, raw provider data
or source content from monitored agents were accessed. No mocks, fakes, stubs,
recordings, seeded telemetry, test-only production branches or hidden test
failures were used. Shared contracts and unrelated edits remain untouched.

Integration next step: root maps these internal pure values into its typed
budget/report views with explicit lineage and compatibility decisions, includes
the monetary mutation cases, and runs the canonical scope gate. No commit or
deployment was performed by this module agent.
