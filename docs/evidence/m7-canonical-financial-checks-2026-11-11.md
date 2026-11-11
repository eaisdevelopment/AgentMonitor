# M7 canonical financial guard checks

Status: partial T003 verification implementation under approved focused plan
1.1.0. Requirements FR-BUDGET-001, AC-TEST-001/006 and M7-A10. This increment
makes existing collection and financial HTTP guard suites executable through
the existing runner. It does not prove a populated report, provider success,
browser journey, installed financial deployment or complete M7 acceptance.

## Commands and actual scope

From the current checkout with the admitted Python toolchain and
`PYTHONPATH=backend/src:.`:

```text
python -m tools.automation.implementations.auto_m7 --lane technical --check collection_guards
python -m tools.automation.implementations.auto_m7 --lane technical --check budget_http_guards
```

Both selections belong only to `technical`; they reject `--expected-revision`.
The existing exact-revision deployment selections retain their admission rules.
No new lane, registered routine, framework, dependency or completion criterion
was introduced.

`collection_guards` executes the existing pure scheduling/retry policy tests and
real temporary SQLite/admission/dispatch, empty recovery, no-key scheduling,
worker entry point and isolated owned transient-unit tests. No provider report
or credential is constructed. Pending registry metadata is created through the
actual product commands and never presented as verified provider identity.

`budget_http_guards` executes the current account financial query, Check/run
status and monitoring transport tests over actual IAM, HTTP and temporary
SQLite. It verifies authorization, input guards, credential absence and no-report
responses. The exact-value wire mapper case is pure: its constructed inputs do
not enter HTTP or storage. It is not populated monetary integration evidence.

The full technical lane now executes these guard checks under its existing
`collection` and `budget_http` checks. A failing guard remains Failed. Passing
guards leave those full checks Not Run, with respectively
`m7_genuine_report_collection_not_implemented` and
`m7_populated_budget_http_not_implemented`. Aggregate technical/exit cannot
become green from partial guard success. The remaining catalog checks are
unchanged; positive reports, current/summary/history reconciliation and required
live boundaries still need their actual assertions and command wiring.

## Red and Green

The five new tests first failed in **27.40 seconds** for the expected reasons:
selection validation rejected both guard names, both real CLI invocations
rejected unknown `--check` choices, and actual aggregate technical execution did
not execute either guard suite. This was not missing-tool or provider failure.

```text
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -q tools/automation/tests/test_m7_financial_checks.py
```

Green: **5 passed in 73.92 seconds**. The actual command tests ran
both guard selections and the full technical lane; they assert exact scope text,
real test execution, and a non-success full-lane result for missing populated
boundaries. No mocked subprocess or synthetic success result is used.
Existing setup/financial selection and completion-policy regressions also passed:
**12 tests and 2 subtests in 0.57 seconds**; this regression selection required
no activation, build or temporary-tool helper.

Scoped Ruff passed. Scoped strict mypy using `--follow-imports=silent` passed for
the two changed source files. An additional unrestricted imported-module mypy
run reported four existing issues outside this change:
`m6_controlled_recovery_evidence.py:74`, `m6_direct_evidence.py:910` and
`auto_m6_exit.py:1368/1376`. This is not a whole-repository type-check pass.

## Impact and handoff

Files:

- `tools/automation/implementations/auto_m7.py`
- `tools/automation/tests/test_m7_financial_checks.py`
- This evidence record.

No product/shared contract or schema changes. No dependency/license changes.
No keys, default profiles, installed service, owner account configuration or
running owner agents are modified. Real worker tests own and clean up their
isolated transient units. The toolchain-link helper is held exclusively while
command tests execute, then released for other work.

Remaining T003 work is bounded by the existing catalog: attach genuine populated
collection/report and HTTP assertions, remaining live/browser/deployment checks,
and the final aggregate result. This guard increment neither closes those
tickets nor delays the first real financial journey until every exit check exists.
