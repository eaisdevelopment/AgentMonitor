# M7 seven-day billing scheduling and persisted retry admission

Status: partial T007 implementation evidence, not M7 completion or installed
monitoring proof. Requirements FR-BUDGET-001/006 and M7-A09; approved focused
plan 1.1.0. Root assigned composition scheduling plus the bounded M04 retry
guard and Check error mapping. No shared contract, schema or dependency changes.
The increment consumes existing M04 collection contracts and CTR-REG-014 1.4.0
billing access; it adds no published DTO or contract version.

## Implemented boundary

`BillingCollectionV1` first claims existing queued work. Only when no eligible
queued run exists does `BillingScheduleV1.enqueue_due` admit at most one normal
seven-day Anthropic collection, then claim it through the same M04 worker path.
No separate queue or browser timer is introduced. Recovery-only operation does
not enqueue normal collections.

Inventory uses public M02 account pages (200 records per page, at most 2,000
accounts), current connection metadata and monitoring-purpose access resolution.
Only actual active, monitoring-enabled billing connections are eligible.
Inventory overflow or inconsistent pagination fails explicitly before admitting
a partial first-page selection. No account, binding or preference is created or
changed by scheduling. The existing code-owned provider access target is
reconciled only for a due, authorized target; it is not an owner account.

Pure intent selection uses fifteen-minute UTC windows and stable 0–59 second
jitter. Binding, scope and connection generations are part of intent identity.
Run/request identity is stable within one window; the real requested time is
retained. Oldest prior attempt sorts first, with a stable resource tie-breaker.
A Check in the current window also prevents an immediate redundant periodic
read. An inventory-to-admission window rollover is skipped until the next wake.
The existing worker's remaining deadline bounds inventory, admission, source
and commit; scheduling does not restart the hard 120-second lifetime. Admission
retains the existing twenty-request source budget.

New budget schedule metadata uses 900 seconds for both base and effective
intervals, consistent with this selection policy. Ordinary collection admissions
retain their existing 300-second interval. This uses the typed budget admission,
not a provider-name condition, and does not alter existing rows or schemas.

The scheduler catches scope-specific budget exhaustion, retry deferral and
existing conflict outcomes and tries the next due resource. Empty or entirely
disabled inventory is a successful no-work result, not a collection success.
This is the seven-day source lane only. Thirty-day scheduling and other provider
lanes are not claimed here.

## Persisted retry guard

M04 reads `collection_run.retry_after` joined to its existing budget reservation.
For budget-report admissions only, the maximum stored boundary for the exact
budget scope digest, dimension and unit defers a new admission while it is in
the future. The boundary is not restricted to the current schedule window or
reservation state. Idempotent replay continues returning the existing run.
Actual new admission checks current UTC time and returns the closed code
`collection_retry_deferred` before committing any new run or reservation.

The atomic queued-claim query independently excludes rows whose same budget
scope/dimension/unit has a future stored retry boundary. Consequently a Check
queued before the provider throttle cannot bypass it. This predicate is limited
to the budget-report lane; existing subscription collection remains unchanged.
At the exact stored instant the cooldown has elapsed. Check maps deferral to
the existing safe `billing_check_rate_limited` response. Exact retry-time UI
projection is not added or claimed.

## Red, Green and real boundaries

- Scheduler Red: four tests failed because the new scheduling module was absent.
  These established feature absence, not a populated provider regression.
- Scheduler initial Green: four passed; expanded builder/dispatch/scheduler
  selection passed 34 tests in 4.89 seconds.
- Retry pure Red: five failures for the absent retry policy, covering future,
  exact-boundary, elapsed, absent and invalid-naive timestamps. Empty SQL Red:
  one missing-query-helper failure, eight tests deselected. These are feature
  absence Red; no provider-429 regression is claimed.
- Combined scheduler/builder/dispatch/retry Green: 40 passed in 4.90 seconds.
- Post-format selection including existing Check/status HTTP tests: 42 passed
  in 8.49 seconds before the cadence metadata correction.
- Cadence metadata Red: after extracting the unchanged 300-second policy, the
  pure typed budget admission returned 300 against the required 900; one failed
  and the ordinary-admission 300-second regression passed. An earlier ordinary
  test construction omitted its required profile and was corrected before this
  behavioral Red; that construction error is not production regression evidence.
  Budget-only policy correction retains the ordinary lane unchanged.
- Final post-correction focused regression: **44 passed in 7.89 seconds**.
  Rechecked Ruff and strict mypy for both cadence-edited files: passed.
- Scoped Ruff and strict mypy passed for eight affected source/test files.
  An initial mypy invocation lacked explicit package bases and rejected a
  duplicate module path; the corrected invocation passed without ignores.

The I/O tests migrate real disposable SQLite and run the actual public IAM/HTTP
application to create administrative pending metadata. They prove empty and
disabled inventory produce no billing runs or provider access targets. The
actual empty claim/query SQL is exercised. A generic background runtime run
appears during the real app test, so its assertion intentionally counts billing
runs rather than incorrectly requiring all runtime collection to stay empty.
Constructed targets/timestamps are restricted to pure policy tests and never
inserted as provider telemetry. No mocks, credentials, provider replay or fake
throttle rows were used.

Focused command (absolute existing runtime; no tool-helper window):

```sh
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -q --tb=short backend/tests/collection_control/pure/test_budget_retry_policy.py backend/tests/integration/collection_control/test_budget_dispatch_empty.py backend/tests/contracts/test_billing_schedule.py backend/tests/integration/collection_control/test_billing_schedule_empty.py backend/tests/contracts/test_anthropic_billing_run.py backend/tests/integration/api/test_billing_actions_http.py
```

## Changed files and remaining evidence

- `backend/src/agentmonitor/composition/billing_schedule.py`
- `backend/src/agentmonitor/composition/billing_collection.py`
- `backend/src/agentmonitor/composition/billing_actions.py` (retry error mapping only)
- `backend/src/agentmonitor/adapters/persistence/collection_control/sqlite/repository.py`
- `backend/tests/contracts/test_billing_schedule.py`
- `backend/tests/integration/collection_control/test_billing_schedule_empty.py`
- `backend/tests/collection_control/pure/test_budget_retry_policy.py`
- `backend/tests/integration/collection_control/test_budget_dispatch_empty.py`
- This evidence record.

Installed enabled-account periodic collection, multi-page populated inventory,
concurrent queued work under a genuine provider throttle, and natural recovery
after its Retry-After are **Not Run**. They require real owner-established
access; empty SQL and pure tests do not replace them. Root owns bootstrap
availability wiring and canonical integration checks. Existing schedule rows
are not rewritten by this increment; the corrected interval applies to newly
admitted budget schedules. No broader scheduling metadata claim is made.

Security/privacy impact: no key, profile, prompt or environment-value access;
no user configuration or installed process mutation. Migration, dependency and
license impact: none. No installed activation or repository commit was made.
