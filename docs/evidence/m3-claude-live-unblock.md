# M3 Claude live quota unblock evidence

- Evidence ID: `M3-CLAUDE-LIVE-UNBLOCK-2026-09-23`
- Scope: A01 Claude `subscription.quota` live source/parser correction
- Requirements: `FR-QUOTA-001..006`, `FR-COL-004..008`, `AC-LIVE-001/004/005`
- Contracts: provider extension and `CTR-PROV-001..008` V1 semantics unchanged
- Environment: Claude Code `2.1.278`, Linux x86_64, protected default profile
- Recorder/date: root integration steward, 2026-09-23 Europe/London

## Owner authorization and safety

The owner granted full repository and local execution authority. The exact
reviewed Claude executable was started only to accept trust for the AgentMonitor
workspace, then exited without sending project content. The default executable
selection, authentication, and profile location were not changed.

Diagnostics emitted only allowlisted structural counts and digit-redacted UI
shapes. No quota value, account identity, credential, provider payload, prompt,
response, tool content, source content, or arbitrary environment value was
retained.

## Red

After workspace trust was accepted, the real live test reached the quota UI but
the parser rejected the current screen-reader render:

```text
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/live/claude/test_subscription_quota.py -q --tb=short -rs
# 1 failed in 30.24s
# state=deadline_exceeded; safe code=usage_deadline_incomplete_render
```

The safe structural diagnostic established two compatible render changes: the
terminal can emit a bounded progress percentage before the `percent used`
value, and the screen can repeat a quota label/render before the `Usage
credits` terminator. It also established that sending `/usage` before the
application-ready banner can lose the command.

## Green and refactor

The production source now waits for the bounded application-ready marker,
accepts only the observed closed percentage shape, selects the latest occurrence
of each allowlisted quota label inside a completed segment, stops each field
scan at the next allowlisted label, and falls back through completed terminal
segments without broadening the field allowlist.

```text
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/live/claude/test_subscription_quota.py -q --tb=short -rs
# 1 passed in 4.02s

PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/live/claude/test_installation.py \
  backend/tests/live/claude/test_runtime_observation.py \
  backend/tests/live/runtime/test_linux_primitives.py \
  backend/tests/live/claude/test_subscription_quota.py -q --tb=short -rs
# 4 passed in 3.93s
```

Ruff check/format and strict mypy for the changed production source passed.
The test used the real installed executable, real protected profile, current
owner account, provider UI, PTY, and live values. No fake, mock, replay,
recording, seeded telemetry, or test-only production branch was used.

## Remaining scope

This proves the live adapter result only. Registry enrollment, collection and
capacity persistence, same-account runtime correlation, authenticated API, and
populated browser verification remain separate M3 gates.
