# M6 organization/provider coverage: registry implementation evidence

Date: 3 November 2026. Scope: M02 only, implementing the reviewed
[coverage amendment](../plans/integration/m6-cloud-scope-outcomes-contract-impact.md)
and `CTR-REG-013` **1.0.0** from `5b1138c`. Migration dependency: `61af2cc`
(cherry-picked locally as `70d0ebb`), schema `v1_0719`.

## Delivered boundary

`SqliteOrganizationProviderCoverageRepositoryV1` implements the typed read,
set and revoke ports. The read preserves the requested organization ordering,
missing members and producer timestamp; inconsistent references or unreadable
storage yield an unavailable snapshot, never a successful empty observation.
Application use cases forward through the published protocols.

Writes validate the selected account version and actual current registry
relationships inside `BEGIN IMMEDIATE`. The retained coverage version, immutable
revision history, registry revision, sanitized change/outbox and idempotency
receipt commit together. Conflicting replays cannot overwrite later changes.
Revocation retains the same ID and monotonically increasing version. Owner
assertions never change credential ownership, quota, scheduling or pool identity.

Account archive/reassignment and organization archive invalidate affected
assertions in the registry mutation transaction. Restoring/reassigning back
cannot revive them. Renaming accounts/organizations or disabling monitoring
preserves the assertion. There is currently no provider-withdrawal mutator;
the read/write reference policy fails closed for a withdrawn/mismatched provider.

## Red and green

Requirements: `FR-ACC-001/002/006`, `FR-ORG-001`, `FR-SAFE-001/002`,
`AC-LIVE-003`, supporting `M6-A03/A04/A05/A09`. No whole-milestone pass is claimed.

Commands use the existing Python environment, `PYTHONDONTWRITEBYTECODE=1` and
`PYTHONPATH=backend/src`:

```text
python -m pytest backend/tests/registry/test_coverage_reference_policy.py -q
python -m pytest backend/tests/integration/registry/test_coverage_persistence.py -q --tb=short
python -m pytest backend/tests/integration/registry/test_registry_persistence.py backend/tests/registry/test_coverage_reference_policy.py backend/tests/registry/test_organization_provider_coverage.py -q --tb=short
```

- Pure policy Red: three failures at the explicitly unimplemented production
  reference policy. Green: three passed after policy implementation.
- Repository Red: four failures at unimplemented production read/set operations
  after actual private-copy migration and real account selection succeeded.
  These were behavior failures, not substituted repositories/provider responses.
- First repository Green: four passed in 79.87 seconds with actual 0719 schema.
- Expanded run: seven new actual SQLite scenarios passed, including concurrent
  same-request writes, rejected-transaction rollback, and rename/monitoring
  preservation. That combined run reported 24 passed and one pre-existing
  outdated schema-inventory assertion: it still expected only the tables from
  0200–0204. The test now explicitly includes all M02 tables through 0719;
  its exact-set, empty-table, foreign-key and integrity checks remain intact.
- After that correction: all 18 pure/registry regression tests passed in 3.45
  seconds. Together the focused evidence covers 25 tests; this is not a claim
  that the canonical M6 gate ran.
- Strict mypy passed the four changed production files. Ruff passed changed
  production/test files. `AUTO-DOCS-CHECK` passed before this evidence addition;
  final documentation verification is recorded in the handoff.

An initial test setup used the automation launcher, which could not find its
worktree-local Python executable. That setup failure is not counted as Red.
The test now invokes the existing canonical migration implementation
`auto_migrate.run_upgrade` with the active interpreter, on the private copy.

## Real-system and privacy limits

Tests use SQLite's read-only backup API against the actual database, then the
canonical verified-backup/migration routine on owner-only private copies.
Registry metadata is selected through production ports. Each mutation scenario
receives another private copy; the installed service/database is unchanged.
Own-account tests reuse the already explicit owner-confirmed organizational
association. They do not claim a new owner action happened on the live service.
No provider call, key/profile read, agent action, simulated telemetry, new account
or fabricated shared/unavailable outcome occurs.

Positive shared/unavailable owner outcomes, and organization archive while such
a current declaration exists, remain **NotRun** until the real owner supplies
that relationship. Pure branch tests are not substituted for those live checks.
The test harness requires one unambiguous existing owner-confirmed Ollama
account; a later multi-account setup requires an explicit safe test selection,
not choosing an arbitrary account.

## Handoff and remaining work

Files: new M02 domain/application/SQLite coverage modules, transaction hooks in
the existing registry repository, two new test files, the current registry
schema-inventory test, and this evidence. No contract, migration, API, UI,
catalog or credential changes are part of this implementation commit.

No new dependencies or license impact. New data is restricted to existing
internal references, owner attribution, closed outcomes/reasons, times and
versions. Schema/recovery evidence remains with the migration owner. Root owns
combined composition, authenticated HTTP/generated client/UI, canonical scope
evidence consumption, metadata synchronization, deployment and full M6 gate.
Those boundaries remain unverified by this lane.
