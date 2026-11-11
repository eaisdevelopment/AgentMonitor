# M7 planning checkpoint — 11 November 2026

Historical plan 1.0.0 checkpoint. The later [1.1.0 planning refactor](m7-plan-refactor-2026-11-11.md) supersedes the proposed implementation sequence; the test results below remain historical evidence.

- Status: intermediate; production implementation and live M7 verification Not Run.
- Baseline: `f7a1799b04be762e1eb81c79d83d50d9bbcfcceb`.
- Worktree: `codex/m7-api-budgets`; accepted M6 runtime unchanged.
- Authority: active owner goal to implement M7 under the SDLC/runbook.
  Focused plan approval and new runtime credential permission are pending.

## Artifacts and review

- [Execution plan 1.0.0](../plans/integration/m7-execution-plan-2026-11-11.md)
- [Sixteen-ticket dependency ledger](../plans/integration/m7-ticket-catalog-v1.json)
- [M05 increment 0.2.0](../plans/modules/m05-capacity/m7-budget-increment-2026-11-11.md)
- [Official source discovery](m7-provider-discovery-2026-11-11.md)

Independent module planning inspected M05 and P01/P02 without credentials or
provider payloads. One bounded review identified three corrections, applied
before seeking approval:

1. Enrollment HTTP/UI belongs to T002; fresh adapter data precedes persistence
   closure; full scheduling follows; HTTP closure waits for forecast/history.
2. T015 runs live/browser reconciliation. T016 runs the technical gate and then
   publication/acceptance; publication does not circularly gate itself.
3. Billing forecast rate sums nonoverlapping bucket costs over covered duration.
   It never subtracts independent daily costs as cumulative counter endpoints.
   Equal positive buckets and signed adjustments have explicit pure test cases.

The synchronization also includes additive signed cost storage, source-cadence
forecast eligibility, 200-record durable chunks and parent completeness. Old
migrations, accepted M6 evidence and existing quota contracts remain intact.

## Verification actually performed

| Command/check | Result and scope |
|---|---|
| `python3 tools/automation/run.py AUTO-M7-PLAN-CHECK` | Passed; 16 tickets, five stories, ten acceptance items; planning only |
| `python3 tools/automation/run.py AUTO-PLAN-CHECK` | Passed; synchronized historical baseline plus new routine registration |
| `python3 tools/automation/run.py AUTO-DOCS-CHECK` | Passed, 317 Markdown files including this checkpoint |
| `python3 -m unittest tools.planning.test_validate_plans tools.automation.test_run.AutomationRoutineTests.test_real_catalog_defines_every_mandatory_routine` | Passed, 13 tests |
| Ruff for the changed planning/automation Python files | Passed after formatting the new checker |
| `git diff --check` | Passed |
| `python3 tools/automation/run.py AUTO-M7-EXIT` | Blocked, exit 3: executable M7 evidence gate/live evidence not yet implemented |
| Existing dashboard service and loopback HTTP | Active; HTTP 200 |

An initial broad automation-test attempt was **Failed**, not accepted as a
green run: 66 tests, 13 failures and four errors. The new isolated checkout had
no linked Python/M0 environments or frontend tools; those prerequisites affect
historical full-runtime tests. A stale expected routine inventory also omitted
seven existing M6 routines and the new M7 registrations; that expectation was
corrected and its focused test passed. The follow-up below records the later
real-environment reruns; this initial failure remains historical evidence.
No service restart or dependency change was used to conceal this result.

### Isolated toolchain follow-up

The existing `_temporary_tool_environment()` in `auto_m6_exit.py` exposed the
already admitted development `backend/.venv` and `frontend/node_modules` to this
isolated checkout. Its existing guarded link helpers also temporarily exposed
the project's `.venv-m0-g1`. The same 66-test invocation then had one failure:
the mutation baseline discovered Codex `0.167.0`, while the existing adapter
admits exactly `0.160.0` (`codex_version_unverified`). This was a real executable
selection failure, not evidence of a budget implementation defect.

The admitted binary was already installed at
`/home/dev/.codex/packages/standalone/releases/0.160.0-x86_64-unknown-linux-musl/bin/codex`.
Prepending only that directory to the test process's PATH allowed the ordinary
mutation runner to select its actual required binary. No executable, default
profile, global PATH, installed package or user service was changed.

Using those temporary existing-tool bindings, this exact selection passed:

```text
backend/.venv/bin/python -m unittest tools.automation.test_run tools.planning.test_validate_plans
Ran 66 tests in 21.457s
OK
```

The invocation used the admitted backend Python, not system Python. All links
created for this run were removed in `finally` through the identity-checking
cleanup helper. The checkout was clean after the run. Dashboard service remained
active and loopback HTTP returned 200. No browser login or provider billing
request occurred. M7-T003 must reuse this reproducible tool-selection evidence
when implementing its canonical runner; these are existing automation/planning
tests, not M7 budget acceptance or approval evidence.

## Scope and next action

Changed files are documentation, planning validation, canonical routine
registration and its expected inventory. No backend/frontend production code,
migrations, accounts, credentials, default profiles or deployed runtime changed.
No new dependency or license change. The credential exception remains proposed,
not applied to AGENTS.md. No production Red/Green or provider pass is claimed.

After the owner's single focused-plan approval, record it and start T002/T003/
T004 in the stated ownership order. Owner configuration and real provider
access are coordinated per lane, never used as an assumed global stop condition.
