# M7 initial installed setup increment

Status: setup increment installed; authenticated acceptance still pending.
T003/T014; M7-A01/A07/A10.
This is partial setup delivery, not financial collection or milestone acceptance.

Selected revision: `7e252b869e28d62582b675f9e3cecc1612d6c5c4`.
Build: `a400265860d11a6d907356ab108803bb72e06eb1c9633c7f028a1a3f5ec8a35d`.
Retained controller:
`/home/dev/.local/share/agentmonitor/releases/m6-candidate-7e252b869e28d62582b675f9e3cecc1612d6c5c4-a400265860d11a6d907356ab108803bb72e06eb1c9633c7f028a1a3f5ec8a35d`.
Prior running revision: `0f7ca54e28e74b8a905f6e2773b9d5c9f26b3578`;
service active/running and root HTTP 200 immediately before preparation.
Initial migration: `v1_0720` to `v1_0731`.

Preparation used the production retained-release helper under its transition
lock, with a clean clone of the exact commit. It built and verified the sealed
release. Scoped selector tests: 19 passed, two subtests; canonical pure lane:
104 passed; scoped Ruff and staged secret scan: passed, zero secret findings.
Previously recorded isolated real service restore/finalize evidence covers this
initial schema pair. It does not prove the later financial-schema transition.

## Exact operation and recovery selection

Run from the retained controller above:

```sh
PYTHONPATH=backend/src:. /home/dev/.local/share/agentmonitor/releases/m6-runtime-2fedf0809fc9/bin/python -B -m tools.automation.implementations.auto_m7 --lane deploy --check setup_activation --expected-revision=7e252b869e28d62582b675f9e3cecc1612d6c5c4
```

The command returns an intermediate result even when operational checks pass;
do not rerun it to clear unexecuted authenticated/continuity checks. Inspect the
actual stage/journal and service after any failure. Recovery scripts below run
with `/home/dev/.local/share/agentmonitor/releases/m6-runtime-2fedf0809fc9/bin/python -B`
from this same retained controller, with no target arguments:

- Before candidate startup only: `tools/automation/implementations/auto_m6_recover_migration.py`
  resumes the recorded migration while keeping the service start-blocked.
- Alternatively, before startup only, `tools/automation/implementations/auto_m6_restore_prestart.py`
  restores the verified previous schema; `tools/automation/implementations/auto_m6_start_restored.py`
  starts and verifies that restored baseline.
- After candidate startup, preserve potential writes and use
  `tools/automation/implementations/auto_m6_finalize_candidate.py` only when the
  recorded candidate is ready. Never restore the old database over new writes.

No owner account, organization, key or provider profile is configured by this
operation. Protected credential storage is preserved and excluded from backups.
Authenticated installed setup remains pending the shared browser sign-in;
the existing request is not repeated. Other implementation continues.

## Observed installed result

The exact command completed with the expected intermediate exit 3. All seven
operational checks passed: controller, candidate startup, installed revision and
loopback, restored restart policy, installed operator help, LAN readiness and
postcheck. The separately required authenticated setup, collector continuity
and backup/recovery fields remained Not Run in that invocation.

Independent service inspection then reported active/running, Restart=on-failure,
the exact selected retained WorkingDirectory, and HTTP 200. Read-only schema
inspection confirmed `v1_0731`. At 17:28:55 UTC, the installed browser verifier
reported authentication_required, six requests and zero mutations; it did not
claim authenticated Overview/setup proof.

A later read-only aggregate query found new quota observations after startup:
Claude 17:30:09 UTC, Ollama 17:30:37 UTC and Codex 17:31:24 UTC. This establishes
post-start collection activity for each existing provider, not full per-account
value reconciliation or a replacement for the final continuity matrix. No
account names, paths, credentials or raw payloads were read by that query.
