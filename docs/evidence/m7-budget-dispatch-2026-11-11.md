# M7 M04 queued billing dispatch and pre-commit recovery

Status: partial T007 implementation. Requirements FR-BUDGET-001/006, M7-A09;
approved focused M7 plan 1.1.0 and root's explicit M04 dispatch/executor assignment.
No installed/provider collection or complete T007 claim. Ownership is M04 SQLite
dispatch/repository and its application executor; no schema/shared contract edits.

## Implemented handoff

`SqliteCollectionRepositoryV1.claim_next_budget_run` accepts the real worker
instance, UTC `as_of`, immutable policy resolver and exact expected provider,
capability, source, manifest fingerprint, collection policy and operation family.
It selects one oldest unexpired queued billing run, reads its existing request,
schedule, lease, reservation and captured billing authority, and checks their
links, generations, fingerprints and original timestamps. It requires the real
transaction-bound M02 fence before dispatch. No fabricated CLI profile or
derived access-target ID is introduced.

Within the same `BEGIN IMMEDIATE`, it registers the new worker, advances the
fencing token, transfers the lease, marks the run running and conservatively
marks its reservation dispatched. Original requested time, deadline, request
digest and financial intent remain unchanged. A second claimant cannot select
the now-running row. Reusing an existing scheduler instance for fresh dispatch
is refused; recovery uses a distinct real owner.

All admission fields are recovered from existing M04 rows except
`budget_limit_units`, which was never stored. It is resolved from the original
stored policy ID/version by the supplied code-owned immutable policy resolver.
Reserved units are not substituted for that limit. The actual first-source
resolver is `composition.billing_run.anthropic_billing_budget_limit`. Root's
closed source plan derives the selected interval from the original request time
and operation family, never claim-time midnight. This increment does not create
a queue, job file, policy engine or migration.

`assert_claimed_budget_run(admission, as_of)` rechecks the reconstructed admission,
current owner/run/lease fence, original deadline and M02 authority before source
I/O. `ExecuteBudgetCollectionRunV1.execute_claimed(..., as_of, completed_at)` uses
this guard and shares the existing collect/normalize/commit path without
re-admission or a second running transition. Ordinary `execute` retains its
original admission/running path.

## Interrupted jobs

`claim_expired_budget_runs` reuses the existing recovery implementation through
a private helper. It selects only billing queued/running jobs with an expired
original deadline, expired lease and stale owner, refences them to an actual
recovery instance under a bounded recovery lease, and leaves committing jobs
untouched. `recover_expired_runs` finalizes queued jobs with
`collection_queued_expired` and running jobs with
`collection_worker_interrupted`. No provider outcome or successful report is
manufactured. Existing reservation finalization releases never-dispatched work
and keeps dispatched work `expired_conservative`; interruption does not imply
that no request reached the provider.

Committing jobs still reconcile through the public M05 receipt/status port.
Root must invoke the bounded recovery paths before fresh work. A full recovery
batch reports incomplete instead of claiming that every job has been drained.

## Evidence and limits

Feature-absence Reds were observed for the missing dispatch method, missing
`execute_claimed`, missing expired-run recovery and missing pure reconstruction
module. These are not live/provider or populated-queue behavioral Reds. An
initial pure-test syntax error and an incorrect test import were corrected;
neither is claimed as production Red.

The earlier empty-database integration test incorrectly supplied the M03
32-character manifest identifier to M02/M04's 64-character audit fingerprint
field. Its **1 failed, 50 passed** result was an integration/test-input defect,
not evidence that the 64-character admission requirement was wrong. Relaxing
that guard to a bounded string was incorrect; the earlier **51 passed** result
proved only that narrower empty test and did not justify the relaxation.

The corrected real empty test now uses production
`composition.billing_run.anthropic_cost_manifest_fingerprint()`. Three negative
admission cases require rejection of a 32-character identifier, nonhex text and
uppercase text before database open. Red: all three reached database handling
and returned `budget_dispatch_unavailable` instead of
`budget_dispatch_query_invalid`. The separate latest-run empty test failed
because `get_latest_budget_run` was absent. Combined Red: **4 failed, 4 passed
in 1.81s**. After restoring the exact 64-lowercase-hex guard and adding the
read-only query, the focused selection was **55 passed in 2.53s**.

```text
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -q backend/tests/integration/collection_control/test_budget_dispatch_empty.py backend/tests/collection_control/pure/test_budget_dispatch_policy.py backend/tests/collection_control/pure/test_budget_run_policy.py backend/tests/collection_control/pure/test_budget_executor_policy.py backend/tests/integration/collection_control/test_budget_run_repository_empty.py backend/tests/contracts/test_budget_run_contract.py
```

New tests include thirteen pure reconstruction cases and eight real empty/invalid
authority boundary cases. Pure values never enter SQLite. Real tests use the
actual migrated empty database, actual source manifest/policy and actual M02/M04/
M05 implementations. They prove empty claims/recovery do not invent worker/run/
lease/receipt rows and missing authority rejects before callbacks/database open.
They do **not** prove a populated claim, successful commit or recovery outcome.

Scoped backend-config Ruff, strict mypy on the three changed production files,
and diff whitespace checks passed. The internal M04 protocol adds methods;
public CTR-COL-002 2.1.0 admission/run types, CTR-COL-006 2.0.0 budget receipts,
CTR-REG-014 1.3.0 billing authority and existing M05 report types are unchanged.

**Not Run:** genuine administrative queued-run reconstruction, concurrent workers
claiming that actual run, populated expired queued/running recovery, populated
committing recovery regression, actual source execution through `execute_claimed`,
installed scheduling, browser/API journey and full canonical M7 collection gate.
Root must exercise these on genuine owner-created administrative state and real
reports; no seeded telemetry/runs or substitute provider were used here.

## Changed files and integration

- `backend/src/agentmonitor/adapters/persistence/collection_control/sqlite/budget_dispatch.py`
- `backend/src/agentmonitor/adapters/persistence/collection_control/sqlite/repository.py`
- `backend/src/agentmonitor/modules/collection_control/application/budget_executor.py`
- `backend/tests/collection_control/pure/test_budget_dispatch_policy.py`
- `backend/tests/integration/collection_control/test_budget_dispatch_empty.py`
- This evidence document.

Root owns fixed source-plan composition, actual access-target reconciliation,
worker entrypoint and all provider/HTTP/UI integration. No credential values,
provider profiles, account configuration, installed database/service or running
agent were accessed or changed. No dependencies, license changes, deployment
or commits were introduced by this increment.

## T010 latest-run query handoff

Root explicitly added this bounded M04 read increment for T010: resource billing
state must remain visible before any successful report. The public adapter method
`get_latest_budget_run(account_id, resource_id, scope_generation, as_of)` returns
an actual `BudgetCollectionRunViewV1` or `None`. Within one read transaction it
joins only billing metadata, requires the budget payload, exact run and captured
account/resource, the captured connection scope generation, and request time no
later than `as_of`; ordering is newest request first with deterministic run-ID
tie-break and `LIMIT 1`. It neither requires a report nor queries M02 tables.
Root owns the consumer protocol in `budget_query_v1.py`.

The real empty migrated database test proves absence remains absence and executes
the real SQL. Populated selection across scope generations, same-time requests,
reportless failures and subscription exclusion remains **Not Run**; no records
were fabricated to claim those cases. No schema, shared contract, provider or
account changes were made. Scoped Ruff and strict mypy passed after this change.
