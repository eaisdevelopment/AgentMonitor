# M6 independent source-signal lease fences

- Evidence ID: `M6-SOURCE-SIGNAL-LEASE-FENCES-2026-11-03`
- Owner: M04 persistence; approved [M6 cloud plan](../plans/integration/m6-ollama-cloud-implementation-change.md)
- Requirements: FR-COL-003..008, FR-SAFE-001/002; acceptance M6-A07/A09
- Contracts: existing `CTR-COL-008` source-signal view 1.1.0 and existing
  collection/cloud lease contracts; unchanged
- Candidate base: `dbcfd26`
- Recorder/date: AgentMonitor engineering, 3 November 2026

## Defect and bounded correction

During a scheduled cloud run, source proof excludes its own reserved attempt
so it can evaluate the last completed real source result. The exclusion query
incorrectly compared the collection run's per-schedule fencing token with the
global Ollama request gate's independently increasing fencing token. Both
leases could be valid while this comparison rejected the proof before any
provider request.

The query now reads the current collection lease's token and compares the run
token with that token. `ensure_ollama_lease_in_transaction` still separately
checks the global cloud admission and gate fencing token, active admission,
owner, schedule, times and gate record version. Existing collection owner,
run state, reserved phase, account, schedule, source, target and generation
checks remain unchanged. This is a persistence comparison correction, not a
schema, API, lease epoch or source-policy change.

## Real Red and Green

The dedicated regression uses SQLite's online backup API with the installed
database opened read-only. Its private temporary directory and copied database
have modes 0700 and 0600. It selects actual enabled registered Ollama targets,
builds real scheduled commands through production composition, registers the
real schedules, and waits for their genuine due time. No schedule timestamp,
provider response, account, credential binding or telemetry is fabricated.

On this private copy the test calls production cloud-gate acquisition,
`SqliteOllamaCloudRunRepositoryV1.admit_run`, `mark_running` and
`read_latest_source_signal`. It asserts that the actual acquired global and
collection tokens differ. It never marks the request dispatched or invokes a
provider adapter or credential worker.

Red before production change:

```text
OllamaCloudAdmissionRepositoryErrorV1:
  ollama_cloud_source_signal_exclusion_invalid
1 failed in 67.51s
```

The elapsed time includes a natural wait for the copied schedule. After the
minimum comparison correction, a fresh actual database copy passed:

```text
1 passed in 6.89s
```

The exclusion returned the same prior actual run ID, admission ID and source
signal observed before the new run was admitted. An invalid command carrying
an incremented global token was rejected with
`ollama_cloud_fencing_conflict`, verifying that the independent global guard
remains active. No persisted row was altered to manufacture this negative case.

Repeatable command from the candidate checkout:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend/src \
  /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -B \
  -m pytest -q --tb=short \
  backend/tests/live/ollama/test_source_signal_lease_fences.py
```

The check requires an actual enrolled, enabled cloud target, prior source
history, no active cloud request at backup time and naturally differing token
sequences. It fails on missing prerequisites rather than fabricating them.
It may wait up to 330 real seconds for the copied schedule/gate to become due.

The existing pure latest-source classifier suite passed: `23 passed in 0.65s`.
Ruff lint and format checks with explicit `backend/pyproject.toml` passed for
both changed Python files. Strict mypy with explicit package bases passed for
both files. The only post-Green test change was Ruff line wrapping.

## Privacy, compatibility and outstanding verification

Only the M04 repository comparison, its dedicated regression and this evidence
record changed. No dependencies, license changes, migrations, configuration,
generated client or public contracts changed. The live database and service
were not written; the selected `.env`, default profiles, API keys, credentials,
prompts, responses and user-agent controls were not accessed. Evidence contains
no account identities or provider payloads. Rollback is a code revert.

Root owns deployment, actual scheduled provider dispatch, successful durable
capacity/history collection, browser continuity and the canonical M6 exit.
Those checks are **Not Run** for this isolated correction; the passing private
database test is not a claim of live provider or full M6 completion.
