# M6 local runtime failure diagnostics

- Date: 3 November 2026.
- Scope: approved local Ollama vertical, M04 runtime composition and its local
  admission automation; FR-COL-006/007, FR-SAFE-001/002, M6-A06/A09.
- Base: `a611cd7`; worktree `m6-runtime-order`.
- Contracts: existing collection-control V1 and runtime-observation V1 remain
  unchanged. The diagnostic enums are internal composition types. No API,
  database, provider request, dependency, or license change.

## Actual failure and investigation

The canonical pytest selection failed before this change: 114 passed, one
failed, zero skipped in 31.619 seconds. The failing test was
`test_real_ollama_collector_reuses_registry_and_schedule_between_ticks`; its
first tick returned `ollama_runtime_unavailable`. A published M04 repository
read of that test's private database found no collection runs, locating this
occurrence before admission. The previously reported direct runtime test
passed in this execution. The failure's underlying exception was discarded.

A subsequent trace-instrumented selection passed all 115 tests in 39.472
seconds. Twenty-four bounded local version probes passed. Twelve private real
SQLite/process collections passed in 18.219 seconds, alternating direct
collection and collector ticks. These passes do not identify or fix the
intermittent failure. No additional diagnostic series was run.

## Change and Red/Green

The collector retains only an allowlisted failure phase and reason. Unknown
exception arguments map to `internal_error`; arbitrary exception strings are
never logged or retained. Status, deadlines, backoff, and collection behavior
are unchanged. The first-tick test includes this safe diagnostic on failure.
Service events may include the same closed phase/reason fields.

The canonical gate filters its transient captured test output. It emits only
test IDs declared in the selected checked-out test sources, without parameter
values, plus a fixed set of observed runtime codes. It never echoes assertion
messages or provider bodies and does not write raw diagnostic output. Codes
are labelled as observed, not asserted to be the root cause.

Red command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend/src:. \
  backend/.venv/bin/python -B -m pytest -q \
  backend/tests/collection_control/test_ollama_runtime_diagnostics.py \
  tools/automation/test_m6_local_admit.py
```

Before implementation: six failures on the missing classifier/parser and two
existing passes. After implementation: eight passed. An additional real
private-database test, `test_optional_ollama_failure_backs_off_without_hot_looping`,
failed against the unchanged baseline collector because `last_failure` was
absent. With the candidate restored, those nine tests passed in 1.16 seconds.
The database failure was induced only by renaming the test-owned database;
no installed database was changed. Ruff with `backend/pyproject.toml`, strict
mypy for the production module, and `git diff --check` passed.

## Canonical verification and limits

One execution of `python -B tools/automation/run.py AUTO-M6-LOCAL-ADMIT`
passed with `operational_limited`, including real adapter/HTTP and built-browser
lanes. Its selected source-and-test digest was
`ff3a4a6ee5637512ae4a1f4b4f6f191d9490cbfb5ac11b911a182c2b71cb9c71`.
The developer interpreter and `_temporary_tool_environment` supply only the
existing local test dependencies; the sealed service runtime is not used.
The selection includes existing real local HTTP/process/SQLite boundaries and
the existing anonymous cloud worker boundary. No authenticated cloud request,
provider profile access, user-agent control, or installed-service change was
performed by this diagnostic task.

This change improves failure attribution. It does not establish a cause or a
behavioral correction for the intermittent runtime failure and does not close
M6. There are no mocks, response recordings, fabricated observations, disabled
assertions, relaxed deadlines, automatic retry additions, or test-only
production branches.
