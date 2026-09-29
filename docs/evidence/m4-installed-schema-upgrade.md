# M4 bounded offline SQLite upgrade evidence

- Status: **Installed owner upgrade and postcheck Passed**; full M4 completion is not claimed here.
- Focused approved plan: [M4 installed schema upgrade](../plans/integration/m4-installed-schema-upgrade-change.md) `1.0.0`.
- Requirements: `FR-OPS-003/004`, `NFR-DATA-001`, `NFR-COMP-001`, `NFR-RES-001`, `NFR-SEC-001`, `NFR-PRIV-001/002`, `FR-SAFE-002`.
- Acceptance contributions: `AC-V1-004`, `AC-OPS-004/005`, `AC-TEST-001/002/003/006`.
- Contracts/revisions: existing `CTR-DB-001`/`CTR-FND-006` V1; pinned production `v1_0603→v1_0707`. No public contract or schema change in this increment.

## Red, Green and refactor

| Boundary | Exact command and result |
|---|---|
| Main Red | `backend/.venv/bin/python -m pytest backend/tests/integration/persistence/test_auto_migrate.py::test_auto_migrate_keeps_verified_prior_backup_and_reaches_exact_m4_head -q` exited 1: canonical `AUTO-MIGRATE` returned 3, `BLOCKED — PLAN-DB approval and real migration implementation`. The real isolated `v1_0603` database existed before command execution. |
| Settings-format Red | `backend/.venv/bin/python -m pytest backend/tests/integration/persistence/test_auto_migrate.py::test_auto_migrate_refuses_invalid_m06_settings_before_ddl -q` exited 1: command incorrectly returned 0 with an actual malformed private settings file. The source was an isolated production-migrated SQLite file. |
| M06 lock/nested-record Reds | `backend/.venv/bin/python -m pytest backend/tests/integration/persistence/test_auto_migrate.py::test_auto_migrate_refuses_m06_settings_lock_contention_before_backup backend/tests/integration/persistence/test_auto_migrate.py::test_auto_migrate_refuses_invalid_nested_m06_record_before_ddl -q` exited 1: **2 failed** because the command returned 0 while a separate process held the real M06 flock and while copied settings contained an invalid nested record. |
| Green/refactor | `backend/.venv/bin/python -m pytest backend/tests/integration/persistence/test_auto_migrate.py -q` exited 0: **7 passed**. The actual production Alembic chain upgraded a temporary owner-only file; exact prior backup, SHA-256, source schema, service and M06 flocks, M06 settings copies and parser, unsafe symlink refusal, malformed settings refusal, and retry no-op were verified. |
| Static | `backend/.venv/bin/ruff check tools/automation/implementations/auto_migrate.py backend/tests/integration/persistence/test_auto_migrate.py` passed. `MYPYPATH=backend/src backend/.venv/bin/python -m mypy --strict tools/automation/implementations/auto_migrate.py` passed. |
| Documentation | `python3 tools/automation/run.py AUTO-DOCS-CHECK` passed for 287 Markdown files. |
| Default command | `python3 tools/automation/run.py AUTO-MIGRATE` without explicit target/expected-head selectors exited 3 and printed a bounded `BLOCKED` result. It did not select owner data. |

The larger `python3 -m unittest tools.automation.test_run` run exited 1 with three failures outside this owned increment: the M0 clean-clone executable test, checkout-wide quality on concurrently edited shared files, and frontend generated build drift. These are **Failed**, not included in the bounded Green claim. Root owns their reconciliation and any full M4 gate run.

## Verified behavior and limits

The command uses the existing exclusive AgentMonitor service flock and holds the M06 writer flock through final verification. It creates an owner-only private migration backup under the selected data root, uses the real SQLite online backup API, closes the destination before fsync, verifies the copied source through the admitted schema inspector, full `integrity_check`, `foreign_key_check`, checksum and a fsynced manifest, then applies only reviewed `0700..0707` revisions on the production Alembic environment. M06 owner association settings and lock are copied with exact bytes/checksums when present, and the copied settings pass the production M06 record parser before DDL. Invalid format or nested records, unsafe path, source drift and occupied service/M06 flocks block before DDL. It never logs SQL, settings contents, identities, paths or provider data.

The isolated tests contain no provider telemetry or business rows. Their settings happy path uses a valid empty M06 format with no process/account record. This implementation assignment did not operate the installed owner database or service. Root subsequently ran the installed migration and checks recorded below. A failure-recovery rehearsal was not reported. `AUTO-BACKUP`, `AUTO-RESTORE` and `AUTO-DEPLOY` remain separate; this command does not claim their outcomes. A failed migration retains the database and backup for separately approved recovery and does not start the service.

## Installed owner activation

Root used the canonical invocation with an explicit owner-only data root and expected prior head; the path is omitted from this evidence:

```bash
AGENTMONITOR_MIGRATE_DATA_ROOT=/absolute/owner-only/data-root \
AGENTMONITOR_MIGRATE_EXPECTED_HEAD=v1_0603 \
python3 tools/automation/run.py AUTO-MIGRATE
```

The owner `AUTO-MIGRATE` run **Passed**, upgrading `v1_0603` to `v1_0707` with a verified private pre-migration backup. The postcheck found the installed current schema compatible with integrity and policy passed. It also verified the retained backup at `v1_0603`, with integrity, policy, checksums and private file modes passed. Root restarted the service afterward on loopback and `192.168.1.18`. This offline migration result does not by itself close M4 or V1 acceptance; the separate release and browser results are recorded in [operations verification](m4-operations-verification.md).

## Files and impacts

Added the focused plan, this evidence, `tools/automation/implementations/auto_migrate.py` and `backend/tests/integration/persistence/test_auto_migrate.py`; changed only the `AUTO-MIGRATE` entry in `tools/automation/routines.toml`. No dependency/license, public contract, API, UI, provider or migration-revision change. The backup is sensitive local installation data and is retained with owner-only permissions. Broader runbook/traceability/M4-gate integration belongs to root.
