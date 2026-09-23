# Runtime observation operations

AgentMonitor V1 runtime observation is read-only. It must never signal, attach
to, pause, kill, restart, write stdin to, or switch credentials for a process.

Run the focused Task 5 tests from the repository root:

```text
backend/.venv/bin/pytest \
  backend/tests/runtime_observation \
  backend/tests/live/claude/test_runtime_observation.py \
  backend/tests/live/runtime/test_linux_primitives.py -q
```

Interpret skips literally. A skip saying `BLOCKED / NOT RUN` is not a pass. The
current approved handoff supports only generic same-UID procfs observation; it
does not authorize exact Claude/version/session/account claims.

For a partial process result, inspect only safe outcome codes. Common causes are
candidate exit/change, permission denial, deadline/result bounds, unsafe stat
layout, or procfs/system-unit unavailability. Do not add logging of raw procfs
bytes, paths beyond the fixed source, argv, environment, or provider state.

Before publishing migration hashes, run the real file-backed SQLite constraint
suite and the repository commit/replay/history suite after the root migration
steward registers `v1_0600..v1_0603`. Also run Ruff, strict mypy with
`MYPYPATH=src --explicit-package-bases`, the boundary checker, migration
integrity checks, and `git diff --check`.

If a future M0 packet approves executable fingerprint or local-session sources,
add an explicit versioned selector/rule catalog and real owner-controlled tests.
Do not broaden the current comm label or caller-supplied version into provider
identity, and do not populate an account from weak process coincidence.
