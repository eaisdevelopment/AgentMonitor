# M6 organization coverage migration evidence

- Scope: PLAN-DB/M02, CTR-REG-013 1.0.0; FR-ACC-001/002/004/006,
  FR-ORG-001, FR-SAFE-001/002, NFR-DATA-001; M6-A03/A04/A05/A09.
- Base: `5b1138c`; branch `codex/m6-coverage-migration`.
- Schema: additive `v1_0718` to `v1_0719`; catalog 1.7.19.
- Authority: the reviewed M6 cloud scope outcomes contract-impact plan and
  root's explicit allocation of the two M02 tables.

Current and immutable revision tables contain the exact CTR-REG-013 view
fields. Current coverage is unique by organization/provider; history is keyed
by coverage ID/version and references only the retained current record.
Source organization fences remain explicit. There is no backfill, provider
action, credential storage, dependency or default-profile change.

## Initial Red/Green

Real fresh-database migration test
`test_real_migration_adds_empty_current_and_immutable_coverage_history` failed
because both coverage tables were absent. The supported-upgrade test
`test_auto_migrate_upgrades_v1_0718_without_coverage_backfill` failed because
0718 was not an admitted migration source. An initial execution lacked the
developer environment link; that setup failure was corrected and does not
count as Red. With `_temporary_tool_environment`, the real command still
returned exit 3 for the unsupported source before implementation.

After implementation, the same two tests passed in 2.62 seconds. They exercise
actual file-backed SQLite, real Alembic migrations and the canonical
`AUTO-MIGRATE` command with its real private backup.

The structural fingerprints were independently calculated from normalized
schema definitions emitted by the actual migrations:

- 0718, unchanged, 232 objects:
  `4037baf915c0bb134943f9d30d7d4026204840ee0af5e6cb646351f13b61bcf4`.
- 0719, 240 objects:
  `c57688987f38cb2c5f7e782c10f2937842f75abe4d5db1adc17487ffaf2d3b17`.

Historical migration bytes and schema hashes remain unchanged. The 0719
controller admits the exact retained 0718 source for cutover and recovery;
same-schema updates remain separate. Older retained controllers and backup
manifests are not rewritten.

## Intermediate status

This initial dependency handoff does not establish final migration readiness.
Actual private installed-data upgrade/preservation, pre-start restore and
broader migration/cutover regression results will be recorded below when run.
No installed database/service changes have been made. Root owns the routine
catalog wording, OpenAPI/client regeneration and planning metadata updates.
No fabricated coverage assertions were inserted; positive assertion/history
behavior is the separately assigned M02 repository boundary.

## Actual private installed-data upgrade

`test_actual_private_0718_upgrade_preserves_registry_quota_and_history` passed
in 32.55 seconds. It creates an owner-only copy using SQLite's read-only backup
API, then compares M02 organization/account/installation projections, M05
current quota and bounded 90-day history pages, and the 200 most recent M04
runs through published read ports at one fixed real observation time. The
canonical offline migration passed and these existing facts were unchanged.
The final read-only schema inspection confirmed compatible 0719. The private
copy is removed by the test finalizer; no live table was queried directly.

The broader initial migration batch returned 52 passes and three failures:
a missing explicit provider selection in the new test, an expected-owner list
that had not yet gained the new M02 revision, and a disposable readiness test
without built frontend assets. The first two test issues were corrected. The
actual-copy check also initially used the offline inspector after published
readers had opened WAL sidecars; the corrected post-read assertion uses the
existing active read-only schema inspector, not new migration authority.
The focused catalog test passed and strict mypy passed for compatibility and
the two new migration test files. Asset preparation and disposable recovery
verification remain the next bounded checks.

## Disposable activation and recovery verification

Built frontend assets from clean candidate `822f50c` with the existing
`build_clean_frontend` helper. Build SHA-256:
`a30e03e1723834982a833ff20e7ec42c343a12ba122fb8d41392348894eae8f5`.
The previously asset-blocked disposable dashboard readiness check passed,
as did the normal same-schema 0719 update check.

Five cutover checks initially stopped before migration/journal creation with
`candidate_checkout_not_clean`: the temporary dependency helper had added
untracked links. The clean-checkout guard was retained. Running only these
five cases directly with the developer interpreter, without dependency links,
passed: **5 passed in 113.42 seconds**.

Invocation from the clean candidate, with `PYTHONDONTWRITEBYTECODE=1`,
`PYTHONPATH=backend/src:.`, and `AGENTMONITOR_TEST_CANDIDATE` pointing to that
checkout:

```sh
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -B -m pytest -q \
  'tools/automation/tests/test_m6_cutover.py::test_disposable_unit_and_real_backup_migration[normal]' \
  'tools/automation/tests/test_m6_cutover.py::test_disposable_unit_and_real_backup_migration[real_source_restore]' \
  'tools/automation/tests/test_m6_cutover.py::test_disposable_unit_and_real_backup_migration[migration_crash_backup]' \
  'tools/automation/tests/test_m6_cutover.py::test_disposable_unit_and_real_backup_migration[migration_crash_committed]' \
  'tools/automation/tests/test_m6_cutover.py::test_disposable_unit_and_real_backup_migration[candidate_attempt_recovery]'
```

These exercise normal 0718-to-0719 cutover, restoration of a private actual
0718 source copy, and the existing migration/interrupted-activation recovery
paths. They use owned disposable units and private databases; no installed
service or database is changed. Other cutover parameter cases were not run
for this change. Historical 0718 migration bytes, schema fingerprint and
retained backup/controller identities remain unchanged.

This is bounded migration evidence, not an M6 completion claim. Root still
owns combined integration, OpenAPI/client provenance regeneration, routine
catalog wording, planning metadata, canonical deployment and the milestone
gate. M02 repository coverage assertions/history behavior has its separate
implementation and real-data checks. No new dependency, credential access,
provider request, fabricated coverage record or telemetry was introduced.
