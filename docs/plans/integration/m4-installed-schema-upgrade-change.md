# Change plan: M4 installed SQLite schema upgrade

- Status: **Approved for this bounded M4 upgrade implementation**.
- Version: `1.0.0`; root approval: 2026-09-29 under the owner's full M4 implementation and system-action authority.
- Owner: PLAN-DB migration automation, with M08 backup and deployment quiescence boundaries; implementation role `/root/m4_capacity_plan`.
- Parent plans: PLAN-DB `0.2.0-draft`, M08 `0.2.0-draft`, PLAN-DEP Draft. Their wider V1 scopes remain unapproved.
- Requirements: `FR-OPS-003/004`, `NFR-DATA-001`, `NFR-COMP-001`, `NFR-RES-001`, `NFR-SEC-001`, `NFR-PRIV-001/002`, `FR-SAFE-002`.
- Acceptance contribution: `AC-V1-004`, `AC-OPS-004/005`, `AC-TEST-001/002/003/006`; no full backup, restore, deployment, or M4 acceptance claim.
- Contracts: existing `CTR-DB-001` V1 schema/catalog and `CTR-FND-006` revision metadata; no public contract change. The existing service flock is an offline exclusion mechanism, not a `CTR-DEP-001` receipt. `CTR-DB-003` and `CTR-OPS-003` remain deferred.

## Outcome

`python3 tools/automation/run.py AUTO-MIGRATE` may upgrade one explicitly selected, already existing, owner-only AgentMonitor SQLite database from the admitted `v1_0603` prior head to the pinned `v1_0707` M4 head. It requires the AgentMonitor service to be quiescent, makes and verifies a fresh private pre-migration backup, applies only the exact cataloged linear chain, verifies target schema and integrity, and leaves normal service activation to the integration owner. The installed owner target is not run by this implementation assignment.

## Scope and ownership

The implementation role may add `tools/automation/implementations/auto_migrate.py`, `backend/tests/integration/persistence/test_auto_migrate.py`, this plan and `docs/evidence/m4-installed-schema-upgrade.md`; it may update only the `AUTO-MIGRATE` entry in `tools/automation/routines.toml` and dispatcher only if needed. No shared bootstrap, M4 gate, contract, migration revision, catalog, frontend, provider profile, owner database or owner service edit is authorized for this assignment. No new dependency is needed.

The canonical dispatcher has no argument forwarding. Its implementation reads only `AGENTMONITOR_MIGRATE_DATA_ROOT`, an explicit absolute non-secret target selector, and `AGENTMONITOR_MIGRATE_EXPECTED_HEAD=v1_0603`, an exact operator guard. Missing or incorrect selectors return `BLOCKED` before any target access. The implementation prints codes, revision IDs, and an opaque backup ID only; paths, row contents, settings contents, SQL and exception messages never enter output. A direct `--data-root` CLI is not a second canonical production path.

Only the existing database upgrade from `v1_0603` is in scope. An absent database, older or unknown head, incompatible catalog, damaged source, occupied service lock, unsafe path/sidecar/settings, failed backup, insufficient recovery capacity, or incomplete validation blocks before DDL. Already-at-target returns a verified no-op without creating a backup. Fresh initialization remains the existing separately approved path. This command does not stop/start a service, alter release artifacts, activate a restore, or claim post-start readiness.

## Current evidence and contract impact

The real catalog has pinned, additive, offline revisions `v1_0700..v1_0707`, each marked `required_existing_database` and `preserve_failed_database_and_restore_verified_backup_or_forward_fix`. The existing `migrate_to_head` refuses upgrades of present files. `AUTO-MIGRATE` currently exits 3 as blocked. The existing `exclusive_service_quiescence` flock prevents concurrency with the AgentMonitor service when held; it cannot stop the service or exclude arbitrary external SQLite writers. The algorithm checks the same SQLite connection's `data_version` and acquires a write reservation before DDL, refusing a source change after the backup. The backed-up database must pass the admitted source schema and full integrity checks.

No HTTP/API/client/event/schema change is made. The backup is a private, uniquely named, mode `0700` directory under the exact owner-only data root's `backups` directory. It contains an SQLite online-backup copy, a bounded manifest with SHA-256, source/target/catalog versions and optional M06 settings presence, and exact copies of `owner-process-account-associations-v1.json` and its lock when present. Each file is regular, owner-owned, mode `0600`, single-link, opened without following symlinks, copied with a size bound, fsynced, hashed and reread. The command holds the actual M06 writer flock from before copying settings through final verification, creating its permanent lock file if absent. A settings file present without its expected lock is rejected; absent settings are recorded absent. The copied settings must pass the production M06 record parser, including nested records and association keys, before DDL. It never copies `.env`, provider profiles, logs, prompts, source or tokens. The backup is retained on success or failure; this command never restores or deletes it.

## Ordered algorithm and failure semantics

1. Parse explicit selector/expected head; admit the exact root/file, pinned catalog and linear `0603→0707` chain without writing.
2. Acquire and hold the existing exclusive AgentMonitor service flock. Validate the exact database and private backup root. A running service or unsafe target fails closed.
3. Open the real SQLite source through the production `migration_existing` policy; read the exact current revision and `data_version`. Use SQLite's online backup API to create a fresh private backup while fenced.
4. Acquire the M06 writer flock and hold it through final verification. Copy and verify M06 settings when present; validate the copied file through the production M06 reader. Fsync and checksum every backup object. Close the SQLite backup destination before fsync, validate the copied SQLite file through the production schema inspector, `integrity_check` and `foreign_key_check`, and write and fsync the bounded manifest only after all checks pass.
5. Recheck file identity, source `data_version`, exact revision/catalog, and acquire `BEGIN IMMEDIATE`. Recheck `data_version` after reservation. Any source drift fails without DDL; retain the backup.
6. Apply the eight approved revisions through the production Alembic environment on the same admitted connection. After each step, verify its exact marker. At target, verify the admitted schema shape, full integrity, foreign keys and required M04/M05/M07 structures. No raw business rows are logged or returned.
7. Commit, close/dispose, verify the final database via `InspectSchemaCompatibilityV1` and the exact backup manifest, then release the service flock. Report migration success only for this offline schema boundary. Normal service start/restricted validation and end-to-end owner readiness remain separate, Not Run.

On any failure, stop; never retry, downgrade, restore, remove a sidecar, delete the backup, or start normal service. Preserve the original/partially upgraded database and WAL/SHM for approved recovery. SQLite DDL may not be fully transactional, so source/backup cannot be described as automatically rolled back. The command returns a sanitized failure and nonzero status.

## Test-first sequence

| ID | Meaningful Red | Green boundary |
|---|---|---|
| `M4-MIG-001` | Canonical command still blocked; no offline upgrade implementation | Real file-backed SQLite admitted `0603→0707` through production Alembic, preserving current state and a verified backup |
| `M4-MIG-002` | Missing selector/occupied service lock could reach DDL | Real temporary root, actual flock and subprocess; source unchanged and nonzero |
| `M4-MIG-003` | Backup omitted or settings not included | Actual SQLite online backup, checksum/integrity and real owner-only M06 settings files; exact bytes preserved |
| `M4-MIG-004` | Unsafe settings/backup root or source revision could be accepted | Real symlink/mode/current-head/unknown-marker cases refuse before DDL |
| `M4-MIG-005` | Failed validation could report success or delete recovery objects | Real isolated corrupt/incompatible target and retained source/backup; sanitized failure |
| `M4-MIG-006` | An occupied M06 settings flock could be ignored | Real process-held flock refuses before backup and DDL |
| `M4-MIG-007` | A valid outer settings envelope could hide an invalid nested record | Production M06 parser rejects the copied file before DDL |

Construct no provider telemetry or business rows. Temporary databases come only from the production migration chain; filesystem and lock tests use actual OS resources. The owner's installed database/service/profile are untouched. The canonical command without selectors must block; execution on the owner target is a separate root-owned activation decision and evidence step.

## Security, privacy, operations, license and documentation

Target/backup references are exact and owner-only; symlinks, hardlinks, unsafe ancestors and broad path cleanup are rejected. Use atomic unique creation, bounded file reads, checksum, fsync and closed result codes. The backup is sensitive installation data despite containing no AgentMonitor-managed secret file; its manifest carries no paths or account identities. No new dependency or license impact. Root owns runbook/traceability/completion-gate synchronization, installed service quiescence confirmation, actual owner activation and recovery exercise. The later full M08 `AUTO-BACKUP`/`AUTO-RESTORE` and PLAN-DEP workflows remain blocked.

## Stop conditions and completion gate

Stop for catalog/head change, business data transformation, missing source validation, unsafe backup root, unexpected settings format/size, lock conflict, an unapproved cross-module port need, or any owner-target operation. Red/Green/refactor evidence, isolated real SQLite upgrade and negative cases, local static checks, and canonical selector-block result are required for a bounded implementation handoff. Installed owner upgrade, service restart, recovery rehearsal, and full M4 exit remain Not Run until root runs their actual gates.
