# M3-FIX-010 session-tree root and truncation repair

Status: implemented; focused deterministic and real-owner-SQLite checks passed.  
Date: 2026-09-24  
Owner: M06 runtime observation  
Contract: CTR-RUN-003 V1, behavior-compatible correction  
Requirements: FR-HIST-002, AC-PROC-001/002; M06-DB-011 and M06-PERF-001 where real volume exists

## Corrected behavior

- `GetSessionTreeV1` passes the requested root and requested node bound to the
  repository instead of requesting a fixed global 200-row topology window.
- The SQLite read selects the requested root independently, then fills only the
  remaining bounded companion slots. An existing requested root therefore
  cannot disappear because of unrelated session ordering.
- Current primary links are read at most twice per selected session, which is
  sufficient to distinguish a single exact link from ambiguity without an
  unbounded link read. Only process rows named by a selected single Strong,
  definitive link are read.
- A bounded source window reports `partial` with
  `topology_source_bound_reached`; it is not reported as complete.
- Every published `child_session_id` is present in the returned `nodes`. Known
  descendants excluded by the requested depth/node bound remain represented by
  `excluded_count`, `partial`, and `tree_bound_reached`.

No schema, migration, API, generated client, UI, provider, process-control, or
dependency change was made. The repository remains `runtime_read_only` and all
SQL parameters carrying data are bound parameters.

## Red

```text
PYTHONPATH=backend/src:. backend/.venv/bin/python -m pytest backend/tests/runtime_observation/test_session_tree_query.py::test_strong_current_process_ancestry_builds_bounded_tree_without_guessing -q --tb=short
```

Result: failed because a bounded returned node retained a grandchild ID absent
from the returned node set.

```text
AGENTMONITOR_TEST_DATA_ROOT=/home/dev/.local/share/agentmonitor PYTHONPATH=backend/src:. backend/.venv/bin/python -m pytest backend/tests/runtime_observation/integration/test_real_session_tree_read.py -q --tb=short
```

Result: failed with `TypeError` because the production repository did not
accept a requested root for its bounded topology read.

## Green and refactor verification

```text
PYTHONPATH=backend/src:. backend/.venv/bin/python -m pytest backend/tests/runtime_observation/test_session_tree_query.py -q --tb=short
# 2 passed

AGENTMONITOR_TEST_DATA_ROOT=/home/dev/.local/share/agentmonitor PYTHONPATH=backend/src:. backend/.venv/bin/python -m pytest backend/tests/runtime_observation/integration/test_real_session_tree_read.py -q --tb=short
# 1 passed

PYTHONPATH=backend/src:. backend/.venv/bin/python -m pytest backend/tests/runtime_observation -q --tb=short
# 76 passed, 2 skipped
```

The two module skips remain explicit unavailable live boundaries; they are not
counted as passes. Ruff and strict focused mypy passed on the changed source and
tests.

## Residual real-volume evidence

The owner database did not contain a naturally accumulated topology above 200
real process/session observations. M06-PERF-001 and the over-bound real-volume
portion of M06-DB-011 are therefore **Not Run**, not passed. The executed real
SQLite check proves root preservation at a one-row requested bound and uses the
production database policy/repository against naturally persisted owner data.
