# M4 live SQLite health and bounded read connection

- Status: Approved for this focused increment by root/integration steward, 2026-09-29.
- Version: 0.1.0.
- Owner: PLAN-DB, delegated implementation role.
- Parent: `docs/plans/persistence/sqlite/plan-v1.md` 0.2.0-draft; the broader plan remains Draft.
- Requirements: FR-OPS-002/006, NFR-DATA-001, NFR-COMP-001, NFR-RES-001, NFR-OBS-001, NFR-SEC-001, NFR-PRIV-001.
- Acceptance contribution: AC-OPS-003, AC-V1-003/005/006/007/008.
- Contracts: additive CTR-DB-001 V1 1.0.0; consumed by root's CTR-OPS-004/006 mapping.

## Outcome and current evidence

Provide an authoritative real live database/schema leaf without running startup integrity inspection on GET. The existing runtime opener waits up to five seconds before returning and the existing immutable inspector rejects active WAL/SHM. Neither is appropriate for M08's two-second query budget. The current reviewed catalog is loaded from actual admitted artifacts, never replaced by a target revision constant.

## Approved scope and exact signatures

Assigned writes: additive `contracts/database_v1.py`; new SQLite `core/bounded_read.py` and `schema/live_health.py`; `backend/tests/persistence/sqlite/core/test_bounded_read.py` and `schema/test_live_health.py`; this packet, `docs/evidence/m4-live-database-health.md`, and `docs/modules/persistence-sqlite.md`.

Published immutable declarations:

- `DatabaseHealthRequestV1(as_of: datetime, deadline: datetime, correlation_id: OpaqueIdV1)`; aware UTC, positive budget at most two seconds.
- `DatabaseHealthV1(reachable: bool, schema_revision: str | None, compatibility_state: DatabaseSchemaStateV1 | None, integrity_state: passed | failed | not_checked, integrity_checked_at: datetime | None, policy_state: passed | failed | not_checked, checked_at: datetime, reason_codes: tuple[str, ...])`.
- `async GetDatabaseHealthV1(request: DatabaseHealthRequestV1) -> DatabaseHealthV1`.

`DatabaseSchemaStateV1` reuses the existing closed schema state vocabulary. Nullable compatibility is explicitly approved: a current marker without an applicable genuine startup validation receipt is unknown, never ready. Unknown stored marker text is not disclosed; only a real revision admitted by the reviewed catalog can be returned.

Adapter-only surface:

- `open_bounded_sqlite_read(reference: DatabaseRefV1, *, deadline: datetime, allowed_tables: frozenset[str]) -> ContextManager[BoundedSqliteReadConnectionV1]`.
- Bounded connection exposes bounded `fetch_one`/`fetch_many` operations only to persistence adapters; no raw connection crosses a published module contract.
- `InspectStartupDatabaseHealthV1(reference, application_range, mode) -> tuple[SchemaCompatibilityViewV1, StartupDatabaseHealthReceiptV1 | None]` wraps the actual existing startup inspector with identity pre/post checks and captures the original integrity timestamp plus technical schema fingerprint.
- `LiveDatabaseHealthReaderV1(reference, application_range)` implements the public async leaf with small synchronous bounded reads.
- `bind_startup_receipt(receipt)` validates file identity, catalog, revision and genuine startup validation, and binds once. Root instantiates the reader before lifespan, then binds the real receipt when its resource factory inspects startup before opening the runtime writer. Absent binding remains unknown.

## Deadline, isolation and privacy policy

The dedicated connection uses direct `sqlite3`, `mode=ro`, `query_only`, WAL assertion, foreign keys on, FULL synchronous, read-uncommitted off and trusted-schema off. Remaining busy timeout is set before connect and before every statement; a real monotonic progress handler interrupts VM work, with deadline checks around every step. All connections close before returning, including failures. There is no executor, worker thread, connection pool, retry loop or background read surviving timeout. The existing normal runtime five-second policy is unchanged.

The verified deadline scope is SQLite lock and VM work on the approved local data root. It does not promise a hard bound on OS scheduling or stalled filesystem syscalls. Ordinary SQLite WAL/SHM bookkeeping can occur on a logical read; no DB/WAL content write, checkpoint, repair, migration, quick check or full integrity query occurs on GET.

Owner/mode/symlink/hardlink/ancestor and sidecar policy uses the existing DatabaseRef validation. Main file identity is rechecked before and after reads. A read transaction gives a consistent schema snapshot. A SQLite authorizer denies mutation/ATTACH and reads outside the adapter caller's explicit table allowlist. Producer adapters may use this mechanism for their own bounded health queries; DB health reads only technical schema and Alembic metadata. Schema fingerprints and raw SQL/rows remain adapter-local. Result/errors contain only closed codes, admitted revision, booleans and timestamps; no paths, accounts, credentials, raw marker values or exception messages.

Startup integrity is historical evidence with its original time. Live reachability does not renew it. Changed file, revision, catalog or technical schema invalidates its applicability; absent/inapplicable evidence is `not_checked`. No new persistent objects, migration, dependency, configuration key, API route or generated client is introduced here.

## Test-first sequence and completion gate

| Scenario | Expected Red | Real boundary and Green |
|---|---|---|
| DB-M4-READ-001 | Bounded read context absent | Actual owner-only temporary SQLite; query-only policy and resource closure |
| DB-M4-READ-002 | Lock/VM work exceeds request budget | Actual SQLite schema/exclusive lock and recursive VM query interrupt within local deadline |
| DB-M4-READ-003 | Mutation or unlisted reads accepted | Actual write/ATTACH/unlisted-table attempts refused without leaking SQL/path |
| DB-M4-HEALTH-001 | Live leaf absent or treats WAL as locked | Real production migration/startup inspection plus an open actual WAL writer; current revision/read succeeds |
| DB-M4-HEALTH-002 | Startup integrity fabricated/renewed | Missing receipt stays unknown; genuine bound receipt preserves original checked time |
| DB-M4-HEALTH-003 | Unsafe/replaced/unknown schema accepted | Actual isolated file permission/identity/schema-marker changes fail closed; unknown text withheld |

Canonical isolated selectors to hand to root: `backend/.venv/bin/python -m pytest backend/tests/persistence/sqlite/core/test_bounded_read.py backend/tests/persistence/sqlite/schema/test_live_health.py -q`. Root owns canonical automation registration, API mapping, composition, producer adapters and full M4 gate. Focused static checks and this real SQLite suite support only this increment; HTTP/browser/owner service and full M4 remain unverified by this role.

## Documentation, rollback and stop conditions

Update focused evidence and persistence guide with exact Red/Green/refactor commands and real statuses. Root owns contract-register/index/runbook/traceability integration. Removing this additive reader restores previous startup behavior without touching owner data. Stop for dependency, catalog/migration/shared ownership changes, cross-module business SQL, sensitive output, default-provider/running-agent actions or an unapproved deadline/schema semantic change. The broader PLAN-DB, M08 and full M4 are not accepted by this packet.
