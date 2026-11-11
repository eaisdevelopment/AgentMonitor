# M7 T007 billing collection-control increment

Date: 2026-11-11. Owner: M04. Status: intermediate implementation and bounded
verification. No genuine billing run was admitted, dispatched, committed or
recovered in this work; full T007/M7 acceptance remains outstanding.
Authority: approved focused M7 plan 1.1.0, implementation authority and root's
bounded T007 delegation. No additional approval, dependency or deployment.

## Requirements and contracts

Supports FR-BUDGET-001..006 through durable billing collection, especially
M7-A02/A09, AC-LIVE-004/005/007, AC-HIST-001 and AC-TEST-001..006. The tests below
cover only the stated pure and real empty-storage boundaries.

Consumes additive CTR-REG-014 1.3.0 `BillingAccessTargetV1`, existing
CTR-REG-011 active binding reference, CTR-COL-002 2.1.0 budget admission/run view,
CTR-COL-006 2.0.0 budget receipt/typed commit port and published M05 budget
report/envelope contracts. Root owns shared contract publication and additive
migration v1_0733. No shared contracts, prior migrations or old executor changed
by this agent. Existing quota callers retain their old method arguments.

## Implementation

- `SqliteCollectionRepositoryV1` now accepts an optional
  `billing_admission_fence(Connection, BillingAccessTargetV1) -> None` constructor
  argument. It is mandatory for billing admissions, including replay; absence
  refuses before database opening. Actual M02 validation occurs inside the
  existing `BEGIN IMMEDIATE` admission transaction.
- The new M04 helper serializes only allowlisted billing connection/binding
  metadata and purpose, at most 8,192 ASCII bytes. UTC timestamps and exact
  generations remain canonical. Unknown/duplicate fields, invalid enums,
  noncanonical forms, floating numbers and oversized input are refused. This
  is not a credential or provider permission proof.
- Admission stores the immutable captured target in `collection_budget_run`;
  replay requires identical target JSON and does not replace it. Queued and
  terminal billing views use `BudgetCollectionRunViewV1`. A successful empty
  report carries its real `report_id` and zero observations.
- Existing schedule/lease/reservation/transition code is reused. Optional
  `scheduler_instance_id` keywords on transition methods are required for
  stored billing runs. Dispatch, committing and successful finalization check
  actual owner/token, schedule generation, scheduler state and live expiry.
  Negative terminal cleanup may pass an expired lease only with the same
  current owner/token and expected nonterminal state; a new owner/fence still
  rejects it. A committed outcome is never overwritten.
- `finalize_budget_committed` checks the typed receipt and exact run identity.
  It writes report/consumer/version metadata and real zero-or-more fact refs
  atomically with run completion, reservation handling, lease removal, schedule,
  request and existing sanitized outbox event. First report fields must still
  be null; conflicting or terminal replay does not replace the first receipt.
- `require_budget_commit_authority(connection, request, *,
  scheduler_instance_id, fencing_token, as_of) -> BillingAccessTargetV1` is the
  M04 half of M05's transaction fence. It checks committing state, run/source/
  schema/digest/generation/adapter version, subject/account/resource/provider
  target, binding/scope identity and generations, live lease and collection
  deadline. It returns the persisted target. Root's composition must also call
  the real M02 `ensure_billing_access_in_transaction` on that target in the same
  M05 transaction. No private M02 or M05 tables are accessed by M04.
- `ExecuteBudgetCollectionRunV1` consumes a real typed M03 report outcome and
  `BudgetCollectionCommitPortV1[BudgetCollectionInputV1]`. Collection occurs
  between repository calls. Commit exceptions leave the run committing for
  receipt reconciliation. Final completion time cannot precede receipt storage.
- Recovery uses existing expired/stale-owner lease claiming, restricted to
  billing runs. A positive matching receipt finalizes without collecting again.
  An absent receipt can mark interruption only after the batch has claimed and
  re-fenced the expired owner. A still-live replay with no receipt remains
  committing/pending, avoiding a race with the original worker's commit.
  Unavailable/conflicting receipts remain explicit; no observations or report
  IDs are invented. Recovery is bounded to 64 runs per call.

## Red → Green evidence

Constructed targets, lease facts, run views and receipts are used only in pure
codec/policy functions. No fake ports, active bindings crossing I/O, provider
responses, financial reports or seeded telemetry are used.

1. Target/lease policy: expected missing-helper `ModuleNotFoundError` before
   production implementation, followed by 16 passing vectors. Explicit queued
   dispatch policy then recorded Red `unexpected keyword argument
   'expected_state'` and Green. Final policy set contains 18 tests.
2. Real empty SQLite: two actual failures before repository additions,
   `AttributeError` for missing `get_billing_target` and
   `finalize_budget_committed`. Green proves absent captured target and lease
   deny authority, no run/target rows are manufactured, and untyped receipt
   finalization refuses before database opening. A third regression check
   composes real M04/M05 repositories and performs empty recovery: no scheduler
   or receipt is created. It exercises no positive sink commit.
3. Receipt recovery: expected missing-executor `ModuleNotFoundError` before
   implementation; initial Green9 covered original zero-fact receipt identity,
   unavailable/conflict, and mismatched run/generation/capability/schema/digest.
4. Deadline cleanup: expected Red `unexpected keyword argument
   'transition_state'` before the distinction was added. Green proves failure
   cleanup with unchanged ownership, while expired commit/success/partial and
   different-owner cleanup remain rejected.
5. Live-owner absent-receipt race: actual behavioral Red `DID NOT RAISE
   CollectionExecutionErrorV1` before correction. Green10 follows: absent
   receipt remains pending until expired-owner recovery has re-fenced the run.

Final regression command from the worktree root:

```sh
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q \
  backend/tests/collection_control/pure \
  backend/tests/collection_control/domain \
  backend/tests/collection_control/test_policy.py \
  backend/tests/collection_control/test_polling.py \
  backend/tests/collection_control/test_identity_reattest_policy.py \
  backend/tests/contracts/test_budget_run_contract.py \
  backend/tests/contracts/test_budget_commit_contract.py \
  backend/tests/integration/collection_control/test_budget_run_repository_empty.py
```

Result: **163 passed in 1.45s**, zero skips. Includes 28 new pure and three new
real empty-store checks plus existing M04 pure/contract regression coverage.
Canonical-context scoped Ruff from the worktree root with
`--config backend/pyproject.toml --fix` corrected five import-group findings;
check passed and all six source/test files remain formatted under that same
explicit configuration. Strict mypy
with `MYPYPATH=backend/src --strict --explicit-package-bases` passed for those
six files. Root owns canonical `auto_m7` selector registration and the wider
current-checkout gate; this focused command is not the full M7 exit gate.

## Not Run and next integration

Positive admission with a genuine active binding, actual provider dispatch,
M05 commit with both real M04/M02 transaction fences, successful M04 finalization,
zero-fact genuine report, positive idempotency/replay, recovery after a real
commit interruption, and concurrent rotation/re-fencing races remain **Not
Run**. No positive financial integration is inferred from empty-store or pure
results. Root must wire the dedicated worker and execute those boundaries with
owner-controlled real access. Existing live quota/provider regression was not
run by this agent; only the listed pure and empty real-store regression ran.

Root owns schema v1_0733 admission/recovery and installation work. No installed
database, service, provider profile, owner account, configuration or credential
was accessed or modified. No provider/network request or new dependency.
Captured metadata contains no keys, provider bodies or profile paths; events
remain the existing safe run-ID/state payload.

## Owned files

- `backend/src/agentmonitor/adapters/persistence/collection_control/sqlite/repository.py`
- `backend/src/agentmonitor/adapters/persistence/collection_control/sqlite/budget.py`
- `backend/src/agentmonitor/modules/collection_control/application/budget_executor.py`
- `backend/tests/collection_control/pure/test_budget_run_policy.py`
- `backend/tests/collection_control/pure/test_budget_executor_policy.py`
- `backend/tests/integration/collection_control/test_budget_run_repository_empty.py`
- `docs/evidence/m7-budget-collection-control-2026-11-11.md`

No commit created. Other agents' files were not changed.
