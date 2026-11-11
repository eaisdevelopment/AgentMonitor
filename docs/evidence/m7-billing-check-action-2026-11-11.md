# Test evidence: Anthropic billing check action

- Evidence ID: M7-BILLING-CHECK-ACTION-2026-11-11
- Module/plan/increment: M7 composition; M7-T007 first owner action to
  durable work
- Requirements/acceptance IDs: FR-BUDGET-001, FR-BUDGET-006; M7-A09;
  M7-COL-001..004 (partial)
- Contract versions: CTR-COL-002 `BillingCheckCommandV1` 2.2.0 and
  `BudgetCollectionRunViewV1` 2.1.0; CTR-REG-014
  `BillingAccessTargetV1` 1.3.0; CTR-REG-012 `ProviderAccessTargetV1`
- Commit/worktree reference: `m7-api-budgets` at base `ad7a04e`,
  uncommitted delegated slice
- Recorder/date: Codex `/root/a01_impl_preflight`, 2026-11-11

## Test inventory and status

| Test/scenario ID | Layer | Real dependencies | Status | Evidence reference | Notes |
|---|---|---|---|---|---|
| M7-BILLING-ACTION-IDENTITY | Pure composition | Published technical values only | Passed | `test_check_identity_is_stable_for_exact_retry_and_scoped_to_owner_intent` | The same principal and command retain one run identity across time; target/version intent remains in the schedule and request digest; another principal cannot replay it. |
| M7-BILLING-ACTION-EMPTY-DB | Database | Newly migrated real SQLite database | Passed | `test_empty_real_database_refuses_before_creating_target_or_run` | Missing genuine account/resource state fails closed before service-target, request, schedule, run or budget writes. SQLite integrity remains `ok`. |
| M7-BILLING-ACTION-ADJACENT | Pure/database | Published contracts and real empty SQLite | Passed | Focused 32-test command below | Covers the command contract, Anthropic admission/normalization, action refusal and empty-dispatch behavior. |
| M7-BILLING-ACTION-WORKER-HINT | Process/composition | Actual `BillingWorkerSupervisorV1` readiness and wake callbacks | Not Run | Root-owned integration | The production seam is present; this slice did not substitute a fake callback. |
| M7-BILLING-ACTION-POPULATED | Database/provider | Genuine owner-created Anthropic billing connection and admitted run | Not Run | Root-owned integration/live verification | No account, credential, target or telemetry was seeded to manufacture a positive path. |

## Red evidence

Before `billing_actions.py` existed, the focused test command failed during
collection for the expected missing action producer:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -B -m pytest \
  -c backend/pyproject.toml -q --tb=short \
  backend/tests/integration/collection_control/test_billing_actions.py
```

Sanitized result: exit 2; `ModuleNotFoundError: No module named
'agentmonitor.composition.billing_actions'`; one collection error. The test was
then renamed to `test_billing_action_admission.py` so it can be collected beside
the existing contract test with a similar name.

## Green evidence

After the minimum producer implementation, the focused pure and real empty-DB
checks passed:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -B -m pytest \
  -c backend/pyproject.toml -q --tb=short \
  backend/tests/integration/collection_control/test_billing_action_admission.py
```

Sanitized result: exit 0; `2 passed in 0.54s`.

The adjacent action, admission and empty-dispatch checks passed together:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -B -m pytest \
  -c backend/pyproject.toml -q --tb=short \
  backend/tests/contracts/test_billing_actions.py \
  backend/tests/contracts/test_anthropic_billing_run.py \
  backend/tests/integration/collection_control/test_billing_action_admission.py \
  backend/tests/integration/collection_control/test_budget_dispatch_empty.py
```

Sanitized result: exit 0; `32 passed in 2.07s`.

## Refactor evidence

Scoped Ruff check and format check passed with `backend/pyproject.toml`. Strict
mypy passed for the new production source and integration test: `Success: no
issues found in 2 source files`. Canonical `AUTO-DOCS-CHECK` passed for 363
Markdown files.

## Real-system evidence

The database test uses a real migrated SQLite file and real production
repositories. It proves the action refuses absent owner metadata without
creating a code-owned target or any M04 request, schedule, run or reservation.
It does not prove the populated path. A genuine connection, durable admission,
actual supervisor readiness/wake wiring, worker claim, provider request and M05
commit remain Not Run here and belong to the root integration/live boundary.

## Integrity declaration

No mock, fake, stub, emulator, recorded provider response, demo account, seeded
account/credential/telemetry, placeholder value, test-only production branch,
disabled assertion or swallowed persistence failure was used. Constructed
values occur only in the pure deterministic-identity test. The I/O test starts
from an actual empty migrated database and asserts no synthetic rows are added.

## Data and secret review

The action receives only versioned nonsecret IDs and metadata. It performs no
credential read and no provider I/O. Evidence contains no key, provider payload,
account identifier, profile value, prompt/response content or arbitrary process
environment value. All public failures are closed `billing_check_*` codes.

## Conclusion and residual gaps

This increment proves deterministic owner-scoped intent and safe failure on a
real empty database. The production action replays an existing exact run before
consulting current readiness, validates the current Claude billing resource and
owner-selected versions for new work, reconciles the fixed official Anthropic
service target, and admits through the existing fenced M04 repository. Optional
worker readiness blocks only new admission; the optional wake callback runs only
after a durable queued result and is non-authoritative.

It does not establish a positive populated admission, callback invocation,
worker execution, provider response or committed report. Those remain explicit
root-owned integration/live checks; no completion claim is made for T007 or M7.
