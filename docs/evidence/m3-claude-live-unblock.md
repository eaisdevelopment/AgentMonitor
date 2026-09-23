# M3 Claude live quota unblock evidence

- Evidence ID: `M3-CLAUDE-LIVE-UNBLOCK-2026-09-23`
- Scope: A01 Claude `subscription.quota` live source/parser correction
- Requirements: `FR-QUOTA-001..006`, `FR-COL-004..008`, `AC-LIVE-001/004/005`
- Contracts: provider extension and `CTR-PROV-001..008` V1 semantics unchanged
- Environment: Claude Code `2.1.278`, Linux x86_64, protected default profile
- Recorder/date: root integration steward, 2026-09-23 Europe/London

## Owner authorization and safety

After being told that workspace trust required owner interaction, the owner
explicitly granted the agent all access and permission to perform the required
work without further questions. Under that separate authorization, the exact
reviewed Claude executable was started only to accept trust for the AgentMonitor
workspace, then exited without sending project content. This persisted a
provider-owned workspace-trust choice and is recorded as an owner-authorized
side effect. The default executable selection, authentication, and profile
location were not changed.

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

The production source now waits for the bounded application-ready marker and
accepts only the observed closed percentage shape. It selects only the newest
quota-bearing segment before its terminal marker; an incomplete quota-bearing
segment cannot fall back to older quota data. Repeated percentage/reset values
inside the newest label block must agree exactly or parsing fails closed.
Earlier occurrences of the same label are superseded Ink terminal
redraw history; treating them as simultaneous values produced the subsequent
real-boundary Red `usage_deadline_window_conflicting_duplicate`. Field scans
stop at the next allowlisted label and the field allowlist is unchanged. The
current behavior is published as adapter/parser patch version `1.0.2`; it cannot
be persisted under either pre-correction provenance identity.

```text
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/live/claude/test_subscription_quota.py -q --tb=short -rs
# Historical Green: 1 passed in 6.52s using latest-label redraw semantics

PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/adapters/providers/claude/test_manifest.py -q --tb=short
# First Red: collection error because CLAUDE_PARSER_VERSION did not exist
# First Green: 2 passed in 0.04s with adapter/parser provenance 1.0.1
# Second Red: 1 failed, 1 passed in 0.05s because 1.0.2 was not published
# Second Green: 2 passed in 0.04s with adapter/parser provenance 1.0.2

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

This proves current live source parsing and mapping behavior only. It does not
approve the adapter/live handoff: the checked-in M0 acceptance record remains
fail-closed, and the production invocation has not yet demonstrated an admitted
equivalent for the mapping's exact-host, redirect-deny, TLS-connection, 4 MiB
upstream/downstream, and 300-second minimum-interval controls. Registry
enrollment, collection/capacity persistence, and the populated authenticated
browser were subsequently proven through the production M02 → M04 → M05 path
in `m3-owner-confirmed-claude-vertical.md`. Same-account runtime correlation and
the exact M0 transport-control handoff remain separate M3 gates.
