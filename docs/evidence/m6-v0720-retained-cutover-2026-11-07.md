# M6 retained-release v1_0720 cutover evidence

- Outcome: Partial integration handoff; installed rollout and M6 completion are not claimed.
- Agent: `m6_recovery_deployment`; date: 2026-11-07.
- Authority: approved M6 Ollama cloud implementation change plan and root's
  explicit allocation of exact retained-release migration/recovery admission.
- Requirements: `FR-SAFE-001`, `NFR-DATA-001`; acceptance: `M6-A07`, `M6-A09`.
- Owning scope: integration operations; consumed M04 database overlay
  `v1_0720`, catalog 1.7.20, predecessor `v1_0719`.
- Base: `8da0eb4e775692150293477a52bd6531a02e5ed7`, working tree
  `codex/m6-signal-composition`. Other agents own the schema/runtime changes.

## Behavior and compatibility

`AUTO-M6-CUTOVER` admits the exact reviewed retained transition
`v1_0719 -> v1_0720`. Candidate-attempt recovery and fixed-journal validation
use the same exact pair. The helper also retains the previously reviewed
`v1_0718 -> v1_0719` mapping when running against that catalog. Unknown future
catalog heads do not infer migration authority.

`AUTO-MIGRATE` adds source `v1_0719`, pins target `v1_0720`, and checks the
complete exact migration tail including the new overlay. Earlier admitted
sources remain admitted. Existing candidate revision/build integrity,
sealed-release, fixed-unit/process, backup, lock, journal, restart and rollback
checks remain intact. Same-schema update remains separate and backup-free.
No old backup manifest or migration is rewritten.

Changed files:

- `tools/automation/implementations/m6_cutover.py`
- `tools/automation/implementations/auto_migrate.py`
- `tools/automation/tests/test_m6_cutover.py`
- `tools/automation/test_m6_retained_migration_policy.py`
- this evidence record

## Red and Green

Before extending admission, the pure exact-pair test failed with
`assert None == 'v1_0719'` for target `v1_0720` (1 failed, 6 passed).
After adding only the reviewed pair, all seven policy cases passed.

The first real `v1_0719` disposable cutover failed with
`cutover_incomplete_review_journal`. Inspection of the retained exception
context established the actual cause: `MigrationRefused('migration_catalog_not_m4')`
in `auto_migrate._preflight_catalog`. This is the meaningful real migration Red;
it was not a provider or environment failure. Root extended this agent's
ownership to the exact `AUTO-MIGRATE` target/chain admission correction.

After that correction:

| Check | Real boundary | Result |
|---|---|---|
| Normal retained migration | Native disposable systemd user unit, actual Alembic and file-backed SQLite | 1 passed, 6.10 s |
| Candidate-attempt recovery, committed migration crash, restore/restart variants | Native disposable units, real process interruption, SQLite backup/restore | 6 passed, 57.51 s |
| Exact policy, public target rejection and override selection | Pure policy and local tooling | 10 passed, 1.92 s |
| Ruff check and format | Four changed Python files | Passed |
| Strict mypy | Both changed production files | Passed |

The predecessor regression was also run before the catalog changed:
normal and candidate-attempt recovery for `v1_0718 -> v1_0719` passed
(2 passed, 13.53 s). That historical evidence is retained as such; it is not
represented as the current target test.

Commands use the existing developer interpreter, no dependency links or new
dependencies, and do not bypass candidate-cleanliness checks:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend/src \
  /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -B -m pytest -q \
  'tools/automation/tests/test_m6_cutover.py::test_disposable_unit_and_real_backup_migration[normal]' --tb=short

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend/src \
  /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -B -m pytest -q \
  tools/automation/tests/test_m6_cutover.py \
  -k 'test_disposable_unit_and_real_backup_migration and (candidate_attempt_recovery or restore_restart or migration_crash_committed)' --tb=short
```

## Boundaries and root integration

These tests exercise real migration, backup and native process ownership with
an existing clean candidate checkout and built assets. Their disposable unit
executes the harness process; they do not establish new application HTTP,
provider recovery or dashboard correctness. Installed rollout, installed-data
preservation and actual candidate/browser/provider verification are Not Run
by this agent. No installed service, database, account or provider state was
changed. The installed-copy `real_source_restore` scenario was not run.

Root must review/integrate the M04 schema and runtime changes, preserve a clean
candidate with a valid frontend build, and confirm no unfinished transition
journal. Run canonical `AUTO-M6-CUTOVER` for this schema change, then the real
product checks and `AUTO-M6-FINALIZE-CANDIDATE`. Do not use the same-schema
`AUTO-M6-CURRENT-UPDATE` for `v1_0719 -> v1_0720`. If interrupted, use the
matching controller's canonical recovery command for its actual durable
journal phase. A pre-start verified backup remains a rollback boundary;
after candidate-start attempt, recovery resumes only the pinned candidate.

No HTTP/event/provider/configuration contract changes are introduced here.
No credentials, arbitrary process environment, account details, prompts or
responses were read or recorded. No new dependency or license impact exists.
No test double, seeded telemetry, disabled assertion or test-only production
path was added. Unrelated concurrent changes were preserved. No commit or
publication was performed by this agent.

## Concurrent-edit regression observation

The remaining disposable scenarios returned 10 passed and 3 failed in
122.68 seconds. `migration_crash_backup` and `override_installed_restore`
failed before setup with `migration_checksum_mismatch`; `crash_post` failed
catalog-dependent restore classification with `restore_recovery_unavailable`.
The schema agent confirmed that migration formatting changed source bytes
while this run was active and was refreshing its catalog checksum. These are
recorded failures, not passes. Only these three cases require rerun after the
schema agent freezes migration/catalog bytes; no check is weakened.

The first post-refresh three-case rerun still failed at catalog load
(3 failed, 1.09 s). Independent read-only digest comparison isolated the
new migration file's catalog record; the catalog checksum itself matched.
The schema agent corrected the refresh script's record anchor and verified
every revision digest plus a successful `load_migration_catalog()` call before
the next three-case rerun.

After the corrected digest was frozen, the exact three cases passed:
**3 passed, 21 deselected, 40.79 s**. Across the non-overlapping latest green
runs, all 20 disposable-unit scenarios selected here passed; the installed-copy
scenario remains Not Run. No production safety check changed to resolve the
checksum failures. Root still owns combined quality and installed rollout.
