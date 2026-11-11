# M7 early setup activation preparation

- Status: Intermediate T014 preparation; installed activation and M7-A10 are not
  complete. The observed candidate result is `prepared_activation_blocked`.
- Authority: approved focused M7 execution plan 1.1.0, early T014 setup increment,
  and delivery worksheet. Scope contributes to M7-A10, FR-ACC-001..004/006,
  AC-OPS-003/006 and AC-TEST-001/002; no full criterion acceptance claim.
- Owner: operations/composition tooling. No published product contract changes.
- Selected real candidate: `bfe1e3515c12fd286d28e3c6c90c2f1fc1befc2e`.

## Actual preparation

`tools/automation/implementations/m7_setup_activation.py` accepts an explicit
clean checkout, exact expected revision, new private workspace, installed local
frontend dependency directory and Python executable. It does not accept an
installed service/data-root selector, start or stop a service, or inspect owner
configuration, credential files, accounts or provider profiles.

The existing `prepare_candidate_release` helper clones without hardlinks,
performs a real offline frontend build, seals and rechecks the retained release.
Its existing internal `m6-candidate-<revision>-<build>` filename convention is
preserved; this is helper compatibility, not a claim that the candidate is M6.
Only the isolated retained clone receives the temporary frontend tooling link.
No shared root helper links are acquired or changed.

Candidate-pinned subprocesses run billing credential CLI `--help` and real
SQLite rehearsal. The latter initializes an empty database at `v1_0720` using
the selected candidate's real Alembic revisions; creates an actual SQLite
backup with `_create_sqlite_backup`; checks it with `_verify_sqlite_backup`;
migrates the isolated database to candidate head; verifies compatibility,
integrity and policy; then reopens/rechecks the retained source backup. No
account or telemetry rows are seeded. This is an isolated schema/backup
rehearsal, not installed backup/restore or guarded `run_upgrade` proof.

The preparation queries the selected candidate's actual `_preflight_catalog`
and `_retained_migration_source` policies. Unsupported policies yield typed
blockers and CLI exit 3 after useful preparation. A genuinely admitted later
candidate can yield `prepared` and exit 0, which means preparation only; it does
not authorize a broader completion claim. No policy status is hardcoded.
Failures retain the private workspace. Existing workspaces, dirty checkouts,
wrong revisions and symlink selections are refused before a build.

Preparation facts are written to a newly created mode-0600 `preparation.json`;
this is not a cutover journal, service-quiescence receipt or acceptance record.

## Red / Green

Before production implementation, the actual clean-checkout test failed:

```text
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q tools/automation/tests/test_m7_setup_activation.py
1 failed in 0.40s
AssertionError: selected M7 setup preparation is missing
```

This is a missing owned-capability Red at a real Git boundary. The final suite
uses ordinary production imports and actual Git/build/SQLite/filesystem paths;
no mocks, fake receipts, manufactured credentials or service substitutions.

Initial Green: **4 passed in 13.80s**. After refactoring assertions to verify
actual candidate policy rather than permanently expecting a blocked result:
**4 passed in 18.66s**. Cases cover a real sealed build, CLI help, migration,
backup integrity/reopen, observed policy/CLI status, dirty-checkout refusal,
existing-workspace refusal, wrong real revision and symlink refusal. Both
databases contain zero accounts; no `.env` files are created.

Ruff check and format check passed. Scoped strict typing:

```text
MYPYPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/mypy --strict --follow-imports=silent --explicit-package-bases tools/automation/implementations/m7_setup_activation.py tools/automation/tests/test_m7_setup_activation.py
Success: no issues found in 2 source files
```

The imports-silent setting limits this typing claim to the two changed files.

Actual final run facts:

- Candidate: `bfe1e3515c12fd286d28e3c6c90c2f1fc1befc2e`.
- Build digest: `3e4887df467b56620eef3b43e29bde1f48d8c457869263e25aa3a84a945a6815`.
- Catalog digest: `fcdb1b37905004bec926cb4de473e37faebe238a1ac679f218e12573420ceec0`.
- Isolated source/target: `v1_0720` → `v1_0731`.
- Backup digest: `304d1ec4c30a7207a3e941c2cf3eddd40aa699c5b7d7099896dd996f42952a98`.
- Result: `prepared_activation_blocked`, exit 3; actual blockers
  `migration_operator_policy_not_admitted`, `cutover_source_policy_not_admitted`.
- Retained test artifact:
  `/tmp/pytest-of-dev/pytest-1685/test_real_candidate_build_sche0/preparation/preparation.json`.
  Temporary test artifacts are local evidence, not durable deployment storage.

## Exact next activation seam

Root owns these shared changes; none were made by this increment:

1. `auto_migrate.py`: admit the actual `v1_0720` source, target `v1_0731`, and
   exact `v1_0730` → `v1_0731` tail while preserving backup/quiescence checks.
2. `m6_cutover.py:_retained_migration_source`: map `v1_0731` to `v1_0720`.
3. `m6_cutover.py:cutover`: allow an explicit selected clean source checkout and
   expected revision, preserving the legacy default and every fixed service,
   executable, override, transition lock, journal and recovery check. The old
   `auto_m6_cutover.py` entry point separately hardcodes an M6 checkout and is
   not an M7 selected-checkout dispatcher.

Subsequent root correction: items 1 and 2 are now implemented. The real offline
upgrade test initially failed with `explicit supported source/expected head
required`, and the new retained-predecessor case returned None (Red: two failed,
seven passed). AUTO-MIGRATE now admits the existing M6 schema `v1_0720` and
the exact `v1_0730`/`v1_0731` tail. Its backup, quiescence, stale-source, settings
and WAL safeguards are unchanged. Existing tests now assert the actual current
head; historical source fixtures remain unchanged. The complete real migration
and pure retained-policy selection passed **33 tests in 65.56s**. Backup digest,
source-schema reopen and repeat-upgrade idempotency passed for the M6 path.
Ruff with the backend configuration passed. No installed database was migrated.
Item 3 and installed verification remain outstanding; the above recorded
`bfe1e35` preparation outcome remains historical and is not rewritten as Passed.

The fixed installed preflight expects releases beneath its code-owned releases
directory. Reuse `prepare_candidate_release` there under transition locks and
revalidate the selected revision/build; do not redirect its globals or activate
the disposable test workspace. `_cutover_engine` then owns the existing guarded
stop/backup/migrate/start transition and recovery journal. Root adds dispatch to
the existing M7 runner and its setup-activation scope.

After those shared corrections are committed, rerun preparation on that clean
candidate. Installed runtime selection, owner-data backup/recovery, service
activation, installed copied-command behavior, authenticated dashboard and
Claude/Codex/Ollama continuity are **Not Run** here. The rehearsed empty backup
does not establish recovery of real credential bindings or owner data.

Files changed: this evidence, the new implementation module and
`tools/automation/tests/test_m7_setup_activation.py`. No dependency/license,
migration-file, service, account, profile, secret or installed configuration
changes. New files remain uncommitted for root integration.
