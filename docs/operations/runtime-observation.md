# Runtime observation operations

AgentMonitor V1 runtime observation is read-only. It must never signal, attach
to, pause, kill, restart, write stdin to, or switch credentials for a process.

The optional local Ollama collector uses one twenty-second scheduling budget,
at most two pending-commit recovery attempts per tick, and the existing bounded
process-inspection deadline. Each SQLite or provider boundary retains its own
short timeout. Service cancellation stops before a new durable admission when
possible and otherwise drains the already admitted run. A sanitized five-minute
failure deadline is stored atomically in the owner-only data root, so restarting
the service cannot turn a pre-admission failure into a hot retry loop. That small
operational state contains no provider identity or telemetry and is not part of
the SQLite backup. An unsafe or unreadable state file leaves this optional
collector unavailable; do not delete or loosen its permissions to force a retry.

Live dashboard process discovery shares three bounded provider-discovery
workers across requests. One unavailable provider remains visibly unavailable
without spawning another worker pool per request or changing the successful
Claude, Codex, or Ollama observations. Exact executable evidence never implies
an Ollama account, model, or active generation relationship.

Run the focused Task 5 tests from the repository root:

```text
backend/.venv/bin/pytest \
  backend/tests/runtime_observation \
  backend/tests/live/claude/test_runtime_observation.py \
  backend/tests/live/runtime/test_linux_primitives.py -q
```

Interpret skips literally. A skip saying `BLOCKED / NOT RUN` is not a pass. The
generic process lane and the separately versioned Claude OTLP lane have
different evidence boundaries; neither may be used to broaden the other.

## Owner-selected Claude session observation

The M3 one-shot launcher records one official Claude session-start metric for
an explicitly selected, existing owner-confirmed account. Stop the authenticated
dashboard first because both commands intentionally use the same exclusive
data-root lock. From the repository root run:

```text
PYTHONPATH=backend/src backend/.venv/bin/python \
  -m agentmonitor.composition.claude_otel_runtime \
  --data-root /home/dev/.local/share/agentmonitor \
  --account-id OPAQUE_ACCOUNT_ID_FROM_THE_DASHBOARD
```

The command replaces itself with the reviewed Claude executable in the same
owner terminal. It does not read terminal output, inject input, send signals,
or control Claude. Its loopback receiver accepts only the per-launch bearer,
allowlisted official metric fields, exact installation/version/process
identity, and the selected account/profile versions. HTTP success is released
only after the M04/M06 receipt, session, and process link reopen successfully.
Restart the dashboard after the receiver child releases the service lock.

A successful launch prints only safe AgentMonitor IDs and completion state. A
generic `claude_otel_monitoring_start_failed` means startup failed closed before
Claude was replaced; rerun only after checking the safe local configuration and
service-lock conditions. Do not weaken identity, version, account, or profile
checks to make the command start.

After a successful owner-terminal collection, run the canonical populated
dashboard acceptance:

```text
python3 tools/automation/run.py AUTO-M3-LIVE
```

The routine builds the production frontend, starts the authenticated service on
loopback with the owner-selected database, prompts for the dashboard password
through a native memory-only dialog, runs the real browser, and checkpoints the
database. `BLOCKED` and `FAILED` are not passes.

For a partial process result, inspect only safe outcome codes. Common causes are
candidate exit/change, permission denial, deadline/result bounds, unsafe stat
layout, or procfs/system-unit unavailability. Do not add logging of raw procfs
bytes, paths beyond the fixed source, argv, environment, or provider state.

Before publishing migration hashes, run the real file-backed SQLite constraint
suite and the repository commit/replay/history suite after the root migration
steward registers `v1_0600..v1_0603`. Also run Ruff, strict mypy with
`MYPYPATH=src --explicit-package-bases`, the boundary checker, migration
integrity checks, and `git diff --check`.

Do not broaden the generic comm label or caller-supplied version into provider
identity, and do not populate an account from weak process coincidence. The
Claude OTLP lane requires explicit owner account selection and exact durable
process/session evidence; it never selects an account merely because only one
account exists.
