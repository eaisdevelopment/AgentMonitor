# M7 financial schema migration and recovery admission

Status: partial T014 technical evidence, not installed activation or M7 closure.
Authority: approved focused M7 plan 1.1.0/T014; requirements AC-OPS-003/006,
M7-A07/A10. This increment contributes operational evidence; it makes no new
authenticated UI claim. Base HEAD was
`7e252b869e28d62582b675f9e3cecc1612d6c5c4`; changes were uncommitted during testing.

## Initial 0732 scope and implementation

The installed database remains `v1_0731`. The initial candidate financial schema was
`v1_0732`, owned by M05 and supplied by the root's concurrent integration. This
increment changes only the existing automation admission and its tests:

- `auto_migrate.py` admits source `v1_0731`, targets `v1_0732`, and extends its
  exact reviewed migration chain. Earlier admitted source revisions remain.
- `m6_cutover.py` adds the explicit retained target/source pair
  `v1_0732` / `v1_0731`. The existing recovery/finalization engine consumes this
  pair; no new recovery engine or guessed revision range was introduced.
- Existing migration assertions now require the financial head. A new real
  SQLite case verifies source/target markers, backup checksum, reopened backup
  compatibility, empty financial tables and idempotent retry without a second
  backup. The existing disposable-unit scenarios now exercise 0731 to 0732.
- Pure admission retains the earlier reviewed pairs and explicitly refuses
  unreviewed `v1_0733`.

The selected clean-controller/revision mechanism and fixed installed selectors
are unchanged. Recovery must use the same retained controller as migration.
Older retained controllers retain their original source/target behavior; this
candidate's recovery does not reinterpret an earlier migration journal as its
new schema pair. Existing no-rollback-after-candidate-start protections remain.

No published Python/API contract changed. The relevant database contract changes
from 0731 to root-owned 0732; schema/catalog/compatibility files were not edited
by this increment. Root owns the canonical command description and plan snapshot
synchronization.

## Red and Green

The first attempt exposed an absent checkout toolchain link: canonical
AUTO-MIGRATE reported `missing or unusable local executable`. This was an
environment obstruction, not behavioral Red. Root granted exclusive use of the
existing `_temporary_tool_environment` helper; no permanent link was created.

With the helper, the unchanged implementation produced genuine Red:
**2 failed, 8 passed in 1.28s**:

- `_retained_migration_source('v1_0732')` returned `None`, not `v1_0731`.
- AUTO-MIGRATE rejected the real isolated 0731 database with
  `AUTO-MIGRATE: BLOCKED — explicit supported source/expected head required`.

After the bounded admission change the same selection yielded
**10 passed in 2.81s**.

Broader real regression: **58 passed, 1 deselected in 253.94s**. Exact invocation
from the candidate checkout, using the existing temporary helper:

```python
import subprocess, sys
from tools.automation.implementations.auto_m6_exit import _temporary_tool_environment
with _temporary_tool_environment():
    result = subprocess.run([
        sys.executable, '-m', 'pytest', '-q',
        'backend/tests/integration/persistence/test_auto_migrate.py',
        'tools/automation/test_m6_retained_migration_policy.py',
        'tools/automation/tests/test_m6_cutover.py',
        '-k', 'not real_source_restore',
    ], check=False)
raise SystemExit(result.returncode)
```

Interpreter: `/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python`,
with `PYTHONPATH=backend/src:.`. Migration integration invokes the actual
`python tools/automation/run.py AUTO-MIGRATE` command. Recovery tests use the
existing engine against actual temporary SQLite and unique disposable systemd
units: stop/lock refusal, verified backup, migration interruption before/after
commit, pre-start restore, interrupted restore/restart, candidate-start recovery,
restart-policy restoration and finalization checks. They do not prove installed
application compatibility or authenticated UI behavior.

`real_source_restore` was deliberately deselected because it copies the installed
database. It is **Not Run**, not Passed. No owner records, secrets or provider
payloads were copied for this work. Existing tests use real empty migrated
databases and real OS/service operations, not fake SQLite or provider fixtures.

An additional future-target refusal case was added after broader-run collection;
the final pure policy rerun yielded **10 passed in 0.63s**. Scoped Ruff with
`--config backend/pyproject.toml` passed. The temporary helper exited normally and
removed its links before root was notified.

## Files and remaining work

- `tools/automation/implementations/auto_migrate.py`
- `tools/automation/implementations/m6_cutover.py`
- `tools/automation/test_m6_retained_migration_policy.py`
- `tools/automation/tests/test_m6_cutover.py`
- `backend/tests/integration/persistence/test_auto_migrate.py`
- This evidence document.

Installed financial activation, installed backup/recovery, real current-revision
application start, authenticated UI, collector continuity and full AUTO-M7-DEPLOY
remain **Not Run** by this increment. Root must retain the final clean controller,
use its exact selected revision and existing migration/recovery commands, and
collect installed proof before any deployment completion claim.

No dependencies/license changes, provider requests, account configuration,
credential reads, default-profile operations, installed service mutations or
commits were performed. Runtime database stays on 0731.

## Planned 0733 collection metadata extension

Root then supplied the planned M04 `collection_budget_run` table in schema
`v1_0733`, after verifying its real migration and unchanged intermediate 0732
shape. This is the final candidate head for this evidence. The admission now
targets 0733, retains 0732 in the reviewed chain and accepts 0732 as an offline
source. The retained service recovery pair is explicitly **0733 to 0731**,
because 0731 is the actual installed baseline; it is not inferred from the
immediately preceding migration number. The earlier 0732 to 0731 pair remains.
Unreviewed 0734 is refused. No new recovery mechanism was introduced.

Before this extension, the focused tests produced **3 failed, 10 passed in
2.48s**: missing 0733 retained source, real 0731 migration refused with
`migration_catalog_not_m4`, and real 0732 source refused with
`explicit supported source/expected head required`. The closed error codes are
historical names retained by the existing operator, not evidence of M4 scope.

After admission, **15 passed in 15.78s**. The same interpreter, environment and
temporary helper ran this exact focused pytest selection:

```text
tools/automation/test_m6_retained_migration_policy.py
backend/tests/integration/persistence/test_auto_migrate.py::test_auto_migrate_upgrades_billing_setup_to_financial_schema
tools/automation/tests/test_m6_cutover.py::test_disposable_unit_and_real_backup_migration[restore]
tools/automation/tests/test_m6_cutover.py::test_disposable_unit_and_real_backup_migration[candidate_attempt_recovery]
```

The migration test now has actual 0731 and 0732 source cases, verifies the exact
0733 target and each unchanged backup source, and confirms all three new tables
are empty. The recovery cases exercise the actual installed-schema pair on
disposable units: 0731 to 0733 and verified pre-start restore back to 0731, plus
candidate-start recovery under the existing no-blind-rollback fence. The full
58-test run above pertains to the preceding 0732 stage and was not relabelled
as a 0733 full-suite result. Existing historical source assertions were advanced
to the new exact head; only the focused selection was repeated for 0733.

Scoped backend-config Ruff and diff checks passed. Helper links were cleaned
and ownership released. Schema/catalog/compatibility and command-catalog edits
remain root-owned. Installed activation/recovery, authenticated UI, collector
continuity and full deploy evidence remain **Not Run** for 0733 as well. No
installed service or owner database was changed.
