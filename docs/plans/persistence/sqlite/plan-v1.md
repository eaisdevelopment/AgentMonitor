# PLAN-DB: SQLite persistence, migrations, and physical database lifecycle

- Status: **Draft — contract synchronization and approval pending; implementation is not authorized**
- Plan version: `0.2.0-draft`
- Proposed technical contract bundle: `sqlite-persistence.v1`
- Contract-register baseline: `0.2.0` (`CTR-DB-001..003`)
- Primary owner: PLAN-DB persistence and migration role (unassigned)
- Required reviewers: owner, root/integration steward, PLAN-FND, M01–M08, PLAN-DEP, A04 Linux/macOS, P01, security/privacy, test-integrity, operations/recovery, and dependency/license owners
- Primary requirements: NFR-DATA-001, NFR-COMP-001
- Supporting requirements: FR-HIST-001/003/004/005, FR-OPS-002/003/004/005/006, FR-SAFE-002; NFR-ARCH-001/002, NFR-TEST-001/002, NFR-SEC-001, NFR-PRIV-001/002, NFR-DOC-001, NFR-LIC-001, NFR-PLAT-001, NFR-PERF-001, NFR-RES-001, NFR-OBS-001
- Acceptance contribution: AC-V1-002/004/005/006/007/008, AC-HIST-002, AC-OPS-003/004/005, AC-TEST-001/002/003/006
- Primary risks: R-005, R-009, R-011, R-012, R-018, R-019, R-020, R-023
- Dependencies: accepted ADRs 0001, 0003, 0004, 0007, 0008, 0010, and 0011; approved PLAN-FND engine/migration/configuration contracts; approved module repository/unit-of-work ports; synchronized M08/DEP/platform database-lifecycle ports
- Target milestone: M1 persistence mechanism, expanded with every table-owning module and recovery integration through M7
- Approved by/date: pending

This plan is governed by the [product requirements](../../../product/requirements.md), [V1 acceptance criteria](../../../product/v1-acceptance-criteria.md), [module boundaries](../../../architecture/modules.md), [contracts and versioning](../../../architecture/contracts-and-versioning.md), [data model](../../../architecture/data-model.md), [deployment architecture](../../../architecture/deployment.md), [security architecture](../../../architecture/security.md), [testing strategy](../../../engineering/testing-strategy.md), [configuration standard](../../../engineering/configuration-standard.md), [completion and automation gates](../../../engineering/completion-and-automation-gates.md), [operations runbook](../../../operations/runbook.md), [foundation plan](../../foundation/plan-v1.md), [M01](../../modules/m01-identity-access/plan-v1.md), [M02](../../modules/m02-registry/plan-v1.md), [M03](../../modules/m03-provider-system/plan-v1.md), [M04](../../modules/m04-collection-control/plan-v1.md), [M05](../../modules/m05-capacity/plan-v1.md), [M06](../../modules/m06-runtime-observation/plan-v1.md), [M07](../../modules/m07-alerting/plan-v1.md), [M08](../../modules/m08-operations/plan-v1.md), and the [contract register](../../contract-register.md).

All paths, class names, settings, revision identifiers, commands, and contract names below are proposals for synchronization. They are not implemented behavior or test evidence.

## CS-1 alignment addendum — contract baseline 0.2.0

This addendum is normative for CS-1 and supersedes conflicting ownership,
layout, activation, or lifecycle wording below. The machine-readable
[contract baseline](../../contract-baseline.toml) and
[parallel ownership manifest](../../parallel-ownership.toml) remain unapproved
and grant no migration/database authority.

- PLAN-DB is the sole technical semantic producer of `CTR-DB-001..003`.
  Domain modules retain business repository/UoW meaning, table invariants, and
  DDL ownership; PLAN-DB supplies `CTR-DB-002` technical lifecycle and real
  SQLite implementations without becoming a business-module owner.
- Persistence paths are uniformly
  `backend/src/agentmonitor/adapters/persistence/<module>/sqlite/**`. PLAN-DB's
  shared physical mechanisms live under
  `backend/src/agentmonitor/adapters/persistence/_shared/sqlite/**`; no competing
  `adapters/persistence/sqlite/<module>` layout or compatibility re-export is
  allowed.
- `CTR-DB-003` owns database snapshot, prepared-database validation, database
  activation, and database rollback receipts only. M08 owns backup/restore and
  maintenance intent/workflow; PLAN-DEP owns artifact/unit activation and
  fenced service quiescence. Those phases and rollback targets remain typed and
  separate.
- The acyclic lifecycle is M08 intent -> DEP quiescence receipt -> DB
  prepare/activate receipt -> DEP restricted/normal service phase -> M08
  validation/readiness. PLAN-DB never calls composite M08 readiness to decide DB
  activation and never treats a running service or artifact switch as a DB
  activation receipt.
- PLAN-DB consumes `CTR-COMMON-001..003/006/007`, `CTR-FND-003/004/006/008`,
  `CTR-EVT-001`, `CTR-OPS-006/007`, `CTR-BOUNDARY-003`, and the narrow DEP/M08
  receipts required by the ordered workflow. Field availability, event
  delivery/checkpoint/replay, retention/export/consistency participation, and
  safe file roots cannot be redefined inside persistence.
- CTR-EVT-TOPOLOGY-001 fixes module-owned transactional outboxes: `reg_event_outbox`, `provider_system_event_outbox`, `collection_event_outbox`, `capacity_event_outbox`, `runtime_event_outbox`, `alert_event_outbox`, and `ops_event_outbox`. PLAN-DB implements reusable claim/delivery persistence mechanics only through each module's published event-storage port. It owns no central event table, never uses cross-module SQL, and leaves consumer receipts/checkpoints under the consuming module's prefix.
- Module repository adapters may proceed in parallel only in distinct
  `<module>/sqlite/**` paths after their domain ports and migration slots freeze.
  The Alembic environment/head/catalog, shared SQLite policy, DB contracts,
  snapshot/activation core, and live database target each retain one assigned
  writer/operator.

All persistence claims use real file-backed SQLite, the production migration
chain, and production adapters. In-memory substitutes, fake repositories,
direct seeded business rows, placeholder telemetry, and skipped/unexecuted
evidence cannot pass a T2/T7 claim.

## 0. Authority, evidence state, and planning constraints

The current authority is planning only. This plan authorizes no production code, test implementation, manifest or lockfile edit, dependency installation, migration, database creation, backup, restore, `.env` change, service action, Git/GitLab mutation, provider access, or operation against the owner's database.

At planning time:

- every `DB-*` scenario is `Not Run`;
- no SQLite file, Alembic revision, repository adapter, snapshot, migration lock, or activation mechanism exists;
- CTR-DB-001/002/003 are registered as `proposed_aligned` 1.0.0 in baseline
  0.2.0; none is Approved or live-verified;
- SQLAlchemy and Alembic remain Candidate/Pending until exact-version dependency admission;
- no module repository/UoW port is Approved merely because this plan names an implementation target;
- written migration, backup, and activation sequences are not proof that they work;
- a schema-only empty-database test cannot prove a data transform preserves real data;
- unavailable real prior-release data, macOS, corruption, disk-pressure, or recovery conditions remain `Blocked` or `Not Run`, never Passed;
- normal application startup must not create or migrate a database implicitly.

This plan is a required artifact in the canonical planning catalog. Its structural presence alone does not make the complete planning gate green and does not authorize implementation.

## 1. Outcome and boundaries

### 1.1 Outcome

PLAN-DB supplies one production SQLite persistence substrate that implements module-owned repository and unit-of-work ports without taking ownership of module data. It provides a fail-closed schema compatibility gate, one immutable Alembic chain, bounded connection and transaction behavior, real file-backed concurrency, exact value mappings, online snapshot/integrity/activation primitives, and a credible PostgreSQL replacement seam.

The outcome is measurable when:

1. every normal runtime connection verifies foreign-key, journal, synchronous, isolation, and busy-timeout policy before use;
2. normal service startup opens an existing database without implicitly creating a file, table, or revision;
3. empty, older, supported, newer, unknown-head, multiple-head, locked, read-only, corrupt, and permission-denied states are classified distinctly;
4. writable readiness is refused unless schema and connection policy are compatible;
5. each application use case owns one short transaction and no provider, platform, HTTP, filesystem, or cross-module call occurs while a write transaction is held;
6. SQLite busy/locked, uniqueness, optimistic conflict, disk-full/I/O, read-only, corruption, and incompatible-schema outcomes map to typed safe errors without SQL or row data leakage;
7. opaque IDs, UTC timestamps, exact decimal/money values, booleans, enums, digests, and bounded canonical payloads round-trip without hidden coercion or binary floating point;
8. every table and DDL operation has exactly one domain owner and one centrally allocated immutable revision;
9. no repository joins, queries, or foreign-keys another module's tables without an accepted ADR and versioned migration plan;
10. `AUTO-MIGRATE` resolves an exact chain, locks migration, requires the applicable verified backup, applies only approved revisions, validates schema/integrity/module invariants, and fails without starting normal service when incomplete;
11. M08 can create a real SQLite online snapshot, validate an isolated target, prepare an atomic activation, preserve the current database, activate once, and roll back through CTR-DB-003 without receiving a raw SQL connection;
12. all database claims use real file-backed SQLite and production adapters; `:memory:`, fake repositories, synthetic business rows, seeded telemetry, and test-only schema paths provide no evidence.

### 1.2 In scope

- SQLite engine, connection, pool, session, transaction, and unit-of-work infrastructure.
- Normal read/write, read-only inspection, migration-initialization, isolated-migration, snapshot, and activation connection modes.
- Required SQLite PRAGMA policy and verification.
- Typed persistence error classification and sanitized diagnostic metadata.
- Adapter mappings for common opaque IDs, UTC instants, durations, exact decimals, money, booleans, enums, digests, and versioned canonical values.
- Implementation conventions for M01–M08-owned repository/UoW ports.
- One linear Alembic chain, central revision allocation, immutable migration checksums, schema compatibility range, startup refusal, migration locking, validation, and recovery classification.
- Real fresh-install and supported-upgrade paths, safe downgrade classification, and failure preservation.
- Physical SQLite online snapshot, integrity, isolated-target, prepared database activation, atomic database switch, and database rollback mechanisms under Draft-aligned CTR-DB-003.
- Database health contribution to M08, including schema, connection policy, integrity, WAL/checkpoint, contention, and last migration/snapshot state.
- PostgreSQL portability review and dialect containment.
- Behavioral ownership of the database portion of `AUTO-MIGRATE`; cooperation with M08 and PLAN-DEP for operational preflight, backup, maintenance, and service restart.
- T2 and applicable T5/T7 evidence at the real SQLite/filesystem/process boundaries.

### 1.3 Out of scope

- Domain entities, invariants, query meaning, retention eligibility, current projections, or business transaction definitions owned by M01–M08.
- Ownership of any `iam_*`, `reg_*`, `provider_system_*`, `collection_*`, `capacity_*`, `runtime_*`, `alert_*`, or `ops_*` table.
- Generic CRUD repositories, cross-module repositories, reporting joins, or a shared ORM model layer.
- Provider/API/CLI/profile/process/filesystem discovery, provider data parsing, or live-provider verification.
- FastAPI routes, UI behavior, scheduler behavior, alerting, export formats, or service installation.
- Backup catalog, retention slots, restore workflow authority, product audit, or owner confirmation; M08 owns those workflows.
- Native service quiescence, installed roots, user service control, or autostart; PLAN-DEP/A04 own them.
- Database encryption, SQLCipher, remote PostgreSQL deployment, replication, multi-writer clustering, cloud backup, or remote object storage in V1.
- Silent repair, destructive salvage, `VACUUM` as corruption repair, automatic downgrade, or deletion of a failed/corrupt/current database.
- Any default-profile, provider-credential, or running-agent mutation.

### 1.4 Ownership and parallel-development model

PLAN-DB owns:

- `SqliteDatabasePolicyV1`, engine/session factories, connection-mode policy, SQLite error mapping, schema inspector, migration catalog/lock/runner, snapshot/integrity/activation adapters, and database health adapter;
- CTR-DB-001 and CTR-DB-003 technical semantics;
- CTR-DB-002 technical-family semantics and implementation rules while each domain module remains producer/owner of its specialized business repository and UoW ports;
- shared migration-chain allocation and checksum catalog, not module DDL meaning;
- database configuration descriptors, not installed path-root ownership;
- persistence module documentation, automation registration, test matrix, and portability report.

Each M01–M08 owner retains:

- its aggregate/repository/UoW interface and transaction semantic;
- its ORM mapping and repository adapter files inside its allocated adapter subtree;
- its tables, indexes, constraints, retention rules, validation queries, and individual revision body;
- Red/Green/refactor evidence for repository behavior and real module workflows.

The migration integration steward alone assigns revision IDs and attaches revision files to the shared head. Parallel module agents may implement independent repository adapters and test plans after their ports freeze, but may not independently create a migration head, edit another module's mappings, or change SQLite core policy.

### 1.5 Exact proposed paths

PLAN-DB-owned paths after approval:

```text
backend/src/agentmonitor/adapters/persistence/_shared/sqlite/core/**
backend/src/agentmonitor/adapters/persistence/_shared/sqlite/schema/**
backend/src/agentmonitor/adapters/persistence/_shared/sqlite/snapshot/**
backend/src/agentmonitor/adapters/persistence/_shared/sqlite/health/**
backend/tests/persistence/sqlite/core/**
backend/tests/persistence/sqlite/migrations/**
backend/tests/persistence/sqlite/concurrency/**
backend/tests/persistence/sqlite/snapshot/**
docs/modules/persistence-sqlite.md
docs/contracts/database-v1.md
docs/operations/database-migrations.md
docs/test-evidence/persistence-sqlite/**       # sanitized evidence only, if allocated
```

Module-specific repository adapter paths, independently owned by the named module implementation agent and reviewed by PLAN-DB:

```text
backend/src/agentmonitor/adapters/persistence/identity_access/sqlite/**
backend/src/agentmonitor/adapters/persistence/registry/sqlite/**
backend/src/agentmonitor/adapters/persistence/provider_system/sqlite/**
backend/src/agentmonitor/adapters/persistence/collection_control/sqlite/**
backend/src/agentmonitor/adapters/persistence/capacity/sqlite/**
backend/src/agentmonitor/adapters/persistence/runtime_observation/sqlite/**
backend/src/agentmonitor/adapters/persistence/alerting/sqlite/**
backend/src/agentmonitor/adapters/persistence/operations/sqlite/**
```

Shared paths requiring explicit single-owner allocation for each edit:

```text
backend/src/agentmonitor/contracts/database_v1.py
backend/src/agentmonitor/composition/**
backend/migrations/env.py
backend/migrations/script.py.mako
backend/migrations/catalog.toml
backend/migrations/versions/<centrally-allocated-revision>.py
tooling/automation/database/**
configuration registry, manifests, lockfiles, CI, command registry, traceability, runbooks
```

The existing module plans allocate `backend/src/agentmonitor/adapters/persistence/<module>/**`; the added `/sqlite/**` leaf specializes those allocations without transferring module ownership to PLAN-DB. Root synchronization must record this exact convention before implementation.

### 1.6 Allowed and forbidden dependencies/imports

SQLite core adapters may import:

- admitted SQLAlchemy and Alembic packages;
- the Python standard-library `sqlite3` API only inside the approved low-level adapter where SQLAlchemy/Alembic cannot expose a required SQLite operation;
- approved foundation configuration, correlation, safe-log, lifecycle, and build-metadata contracts;
- CTR-PLAT-001 filesystem/lock/object operations and CTR-DEP-001 maintenance evidence through published ports;
- CTR-OPS-006 component-health shape;
- module-owned repository/UoW port packages solely in the corresponding module-specific adapter subtree.

Domain modules must not import SQLAlchemy, Alembic, `sqlite3`, SQLite PRAGMAs, ORM mappings, or PLAN-DB internals. PLAN-DB and module repository adapters must not:

- import another module's implementation, ORM models, repository adapter, table metadata, or private DTOs;
- expose a SQLAlchemy `Session`, connection, query, row, model, or dialect error through a domain port;
- issue SQL joining tables with different module prefixes;
- create a common base repository with business-aware CRUD/search behavior;
- use raw string SQL where SQLAlchemy Core/ORM can express the approved operation; any required raw SQLite operation is parameterized, isolated, documented, and reviewed;
- call a provider, filesystem discovery, HTTP API, platform process API, or another module port inside a write transaction;
- read `.env`, provider state, the operator's default database, or arbitrary paths directly;
- add an async SQLite driver, migration helper, lock library, backup framework, or PostgreSQL driver without separate admission;
- create a test-only engine mode, schema, repository, migration, bypass, or `:memory:` shortcut.

## 2. Requirements and traceability

| Requirement/AC | Planned PLAN-DB behavior | Contract | Scenario IDs | Evidence gate |
|---|---|---|---|---|
| NFR-DATA-001 | Real local SQLite file, explicit settings, owned repositories, portable mappings, no dialect leakage | CTR-DB-001/002; `sqlite-persistence.v1` | DB-FILE-001..010, DB-TXN-001..012, DB-PORT-001..006 | Real SQLite file/production adapters/portability review |
| NFR-COMP-001 | Immutable linear revisions, compatibility range, checksum/catalog validation, refusal of newer/unknown schema | CTR-DB-001; CTR-FND-006 | DB-MIG-001..016 | Real Alembic chain and prior/current binaries |
| NFR-ARCH-001/002 | Module-specific repositories implement typed ports; no cross-module tables/FKs/imports | CTR-DB-002 | DB-REP-001..012, DB-SEC-001/002 | Real source/schema/import inspection and repository workflows |
| NFR-TEST-001/002 | R/G/R at real file/migration/concurrency/filesystem boundaries; no doubles/in-memory/seeded business rows | test-evidence contract | DB-SEC-003/004, every DB scenario | Canonical AUTO-TEST evidence with boundary/status |
| NFR-SEC-001 | Owner-only files, safe paths, parameterization, bounded pool/locks, redacted errors | CTR-DB-001/003 | DB-FILE-003..010, DB-SEC-001..008 | Real filesystem/process/log/artifact inspection |
| NFR-PRIV-001/002 | Adapter adds no content fields and no telemetry/egress; schema inventory enforces module allowlists | schema catalog | DB-SEC-005..008 | Real schema/log/network/artifact review |
| NFR-DOC-001 | Maintained schema, migration, recovery, repository, and portability docs plus verified command registry | documentation outputs | DB-DOC-001/002 | AUTO-DOCS-CHECK plus runbook exercise |
| NFR-LIC-001 | Exact SQLAlchemy/Alembic/tool versions admitted with locks/SBOM/notices | dependency record | DB-DEP-001/002 | Actual locked graph and reviewer approval |
| NFR-PLAT-001 | Linux file/lock/atomic behavior verified; core remains portable; macOS real result stays distinct | CTR-PLAT-001/CTR-DB-003 | DB-PORT-001..006 | Real Linux; real macOS or visible Blocked |
| NFR-PERF-001 | Bounded pool/write serialization/index plans support target load without redesign | repository/query budgets | DB-TXN-007..012, DB-REP-009..012 | Real AgentMonitor-created operational volume only |
| NFR-RES-001 | Busy/corruption/migration/snapshot failure is contained and normal service fails safely | typed errors/health | DB-TXN-004..006, DB-MIG-010..016, DB-SNAP-006..012 | Real isolated failures and running service |
| NFR-OBS-001 | Correlation, safe operation category/duration/error code, no SQL/values/paths | safe-log/health contracts | DB-SEC-005/006 | Real logs and diagnostic scan |
| FR-HIST-001/003/005 | UTC/exact persistence and bounded module-owned deletion transactions | module ports/CTR-DB-002 | DB-REP-005..008 | Real production retention use cases; natural aged data if required |
| FR-HIST-004 | M08 exports through module ports; DB never creates a cross-module export query | CTR-DB-002 boundary | DB-SEC-002, DB-REP-008 | Architecture/query inspection |
| FR-OPS-002/006 | Publish schema/database health and authoritative current/compatible revisions | CTR-DB-001; CTR-OPS-006 | DB-FILE-007/008, DB-MIG-003/004 | Real service readiness/health |
| FR-OPS-003/004 | Real online snapshot/integrity/staging/activation/rollback seam | proposed CTR-DB-003 | DB-SNAP-001..012 | Real SQLite/database files and M08 orchestration |
| FR-OPS-005 | Backups/logs/evidence exclude secrets/content; database path never exposed publicly | CTR-DB-003 safe receipts | DB-SEC-005..008, DB-SNAP-010 | Real artifacts/scans |
| FR-SAFE-002 | No database contract controls or targets provider agent processes | complete public surface | DB-SEC-001 | Contract/import/API absence review |
| AC-V1-004 | Empty and every supported prior release migrate; safe recovery/downgrade evidence is truthful | AUTO-MIGRATE/CTR-DB-001 | DB-MIG-005..016 | Real release-created database artifacts |
| AC-OPS-004 | Snapshot, checksum/integrity coordination, restore activation, and post-start validation | CTR-DB-003 with M08 | DB-SNAP-001..012 | Real database/filesystem/service exercise |
| AC-OPS-005 | Upgrade failure preserves evidence/current data and follows tested recovery | AUTO-MIGRATE | DB-MIG-010..016 | Real isolated then owner-approved upgrade rehearsal |
| AC-TEST-001/002/003/006 | R/G/R; no prohibited doubles; real SQLite; statuses never collapsed | test-evidence contract | DB-SEC-003/004 and all scenarios | Canonical report with Passed/Failed/Blocked/Not Run |

### 2.1 Approved facts and proposals

Accepted facts are: SQLite V1, SQLAlchemy/Alembic architecture, explicit migrations, physical sharing with logical module ownership, no hidden DDL, file-backed tests, online backup, integrity validation, and PostgreSQL portability.

The following are PLAN-DB proposals requiring synchronization: synchronous SQLAlchemy 2.x-style persistence, the exact PRAGMA policy in section 3, bounded pool defaults, `BEGIN IMMEDIATE` for write UoWs, the exact migration allocation in section 5, CTR-DB-003, technical configuration names, and the activation/recovery mechanism. None may be treated as Approved until the listed consumers review it.

## 3. Domain design

PLAN-DB is an infrastructure adapter, not a business domain. Its deterministic policies still have explicit states and invariants.

### 3.1 Database references and connection modes

`DatabaseRefV1` is an opaque, non-displayable reference resolved through approved configuration/platform roots. It is not a raw path, URL, or SQLAlchemy connection string.

Allowed modes:

| Mode | File create | DDL | Business writes | Intended caller |
|---|---:|---:|---:|---|
| `runtime_read_write` | no | no | yes | normal service after compatibility passes |
| `runtime_read_only` | no | no | no | health/diagnostic bounded reads |
| `migration_initialize` | yes, exact absent target only | yes | migration only | AUTO-MIGRATE fresh install |
| `migration_existing` | no | yes | migration/backfill only | AUTO-MIGRATE supported upgrade |
| `isolated_validation` | no | no unless explicit migration sub-mode | module validation/invalidation through ports | M08 restore staging |
| `snapshot_source` | no | no | no | CTR-DB-003 online backup source |
| `activation_candidate` | no | no | only approved staging validation | CTR-DB-003 prepare/activate |

Normal service uses SQLite `mode=rw` semantics and therefore cannot create a missing database. Only explicit migration initialization uses `mode=rwc`, after validating the exact absent target and approved parent directory. Read-only inspection uses `mode=ro` and cannot silently reopen writable.

### 3.2 File identity and safety

- The installed database reference resolves beneath the PLAN-DEP-approved data root to the fixed V1 object `agentmonitor.db` unless a later configuration contract approves another exact object.
- The data root is an owner-controlled directory with mode `0700` on Linux; database, `-wal`, and `-shm` files must be regular owner-controlled files and no broader than `0600`.
- Symlinks, hard-link count surprises, special files, traversal, unresolved variables/globs, unexpected owner, and world/group-writable parents fail closed.
- Tests use a unique `mktemp`-style real directory outside the repository and never the operator's configured path.
- File identity `(device, inode)` is revalidated around activation-sensitive operations. A changed identity aborts the operation.
- Public API, logs, health, evidence, and errors never disclose the resolved path, username, home directory, inode, or connection URL.
- The database is never opened from `HOME`, `~`, the repository root, or an unresolved environment variable.

### 3.3 SQLite runtime policy

The proposed V1 normal-write policy is:

| Setting | Required value | Scope/rationale |
|---|---|---|
| `foreign_keys` | `ON` | every connection; module-local FKs enforced |
| `journal_mode` | `WAL` | database-level; concurrent readers and one writer |
| `synchronous` | `FULL` | durability-first local V1; measured before any weakening |
| `busy_timeout` | `5000` milliseconds | every connection; one bounded wait, no hidden retry loop |
| `read_uncommitted` | `OFF` | every connection; no dirty reads |
| `wal_autocheckpoint` | `1000` pages | database-level initial policy; measured and versioned |
| `trusted_schema` | `OFF` for runtime connections | reduce schema-level extension risk; baseline support required |

Rules:

- Opening a normal writable engine verifies the effective values; failure or silent fallback is `database_policy_incompatible` and blocks readiness.
- Migration connections use trusted repository migrations and may use the minimum exception needed by Alembic only if documented, then runtime policy is re-established and verified before service start.
- Read-only connections assert database-level values and set the connection-local values they are permitted to set.
- `journal_mode=DELETE`, `synchronous=NORMAL/OFF`, disabled foreign keys, or a zero/unbounded busy wait is not a permissive fallback.
- `secure_delete` is not claimed as a secrecy mechanism. Deleted verification material may remain in SQLite pages/backups until normal lifecycle removes it; storage permissions and credential rotation remain required.
- WAL checkpoint behavior is observed and bounded. Destructive/manual checkpoint modes are not run while active readers/writers exist without an approved operation.

### 3.4 Connection and pool lifecycle

- Use the admitted synchronous SQLAlchemy engine and Python SQLite driver; no async SQLite dependency is proposed.
- Proposed normal pool defaults are `pool_size=5`, `max_overflow=0`, and `pool_timeout=5 seconds`, configurable only within section 8 bounds after measurement.
- A connection is checked out for one bounded use case/UoW and never stored in a singleton domain service, request object, event, or background job.
- SQLAlchemy sessions are never shared across threads/tasks. `check_same_thread=False`, if required by the admitted server/thread model, is adapter-only and does not permit session sharing.
- Connection initialization attaches the PRAGMA policy and a safe correlation context. A failed initializer discards the connection.
- Pool disposal occurs before activation, restore, process fork, or shutdown. Open handles after the drain deadline block activation.
- No provider/network/filesystem call is made through a checkout callback or transaction hook.
- Read-only long history work is paginated; it cannot monopolize the pool or write lock.

### 3.5 Transaction and unit-of-work policy

- One application use case owns one UoW. Nested independent UoWs on the same call path are rejected unless an owning module explicitly publishes a composition rule.
- A write UoW starts with adapter-isolated `BEGIN IMMEDIATE`, acquiring the single-writer reservation before domain persistence work and avoiding a deferred mid-transaction lock surprise.
- A read UoW uses a consistent SQLite read transaction when multiple reads must agree; simple single queries close immediately.
- Business validation and external contract queries occur before the write transaction. Optimistic version/current-generation checks are repeated inside the transaction.
- Commit happens only after all owned writes and module-owned event/outbox records succeed. Any exception rolls back the complete UoW.
- Repository adapters return domain values/typed receipts, not live ORM entities. Lazy loading after UoW close is prohibited.
- The adapter performs no transaction replay. `busy_timeout` is the only implicit wait; a busy/locked result returns a typed retryable outcome and the owning idempotent use case decides whether to retry.
- Cancellation rolls back, closes, and preserves the original safe error classification.
- Database writes never encompass provider/HTTP/subprocess/filesystem calls, cross-module port calls, M08 artifact work, or UI serialization.

### 3.6 Typed persistence outcomes

The shared adapter error vocabulary proposed under `sqlite-persistence.v1` is:

- `persistence_busy` — writer/lock unavailable after bounded timeout; retryable only by owner policy;
- `persistence_conflict` — optimistic version/fence/current-generation mismatch;
- `persistence_duplicate` — module-owned uniqueness violation with safe constraint key;
- `persistence_integrity_violation` — other approved constraint/reference failure;
- `persistence_read_only` — target or filesystem cannot accept required write;
- `persistence_space_exhausted` — real `SQLITE_FULL`/filesystem exhaustion;
- `persistence_io_failure` — bounded filesystem/device I/O failure;
- `persistence_corrupt` — SQLite corruption/not-a-database/integrity failure;
- `persistence_schema_incompatible` — revision/range/checksum/policy mismatch;
- `persistence_unavailable` — safe catch-all for an unavailable database boundary;
- `persistence_cancelled` — caller cancellation before commit;
- programmer invariant failure — not converted into a recoverable business outcome.

Mappings use SQLite result/error codes where the supported runtime exposes them. No error contains SQL text, bind values, table rows, raw path, exception message, credential, or provider content. Constraint-to-domain error mapping belongs to the corresponding module adapter and must not parse unstable human-readable SQLite messages when a stable code/constraint identity is available.

### 3.7 Exact persistence representations

#### Opaque identifiers

- Stored as bounded UTF-8 `TEXT`, compared exactly, never parsed for business meaning.
- Contract validation allows only the approved opaque-ID alphabet/length from CTR-COMMON-001 before persistence.
- Provider IDs remain distinct columns from AgentMonitor internal IDs.
- PostgreSQL maps to `text`/bounded `varchar` unless a future contract explicitly chooses native UUID; V1 contracts do not assume UUID.

#### UTC instants and durations

- Persist UTC instants as canonical fixed-width RFC 3339 text with six fractional digits and `Z`: `YYYY-MM-DDTHH:MM:SS.ffffffZ`.
- Naive datetimes and non-UTC values are rejected at the adapter boundary rather than normalized silently.
- Lexical order equals chronological order for this representation.
- Duration contract values are signed or nonnegative integer milliseconds as the owning schema requires; no floating seconds.
- PostgreSQL maps instants to `timestamptz` behind an equivalent adapter and returns the same contract value.

#### Exact decimal, ratio, and money

- Binary floating point is prohibited for persisted financial, ratio, quota, token, or exact quantity values.
- General exact decimal uses a canonical base-10 coefficient stored as bounded canonical `TEXT` plus integer scale. The coefficient has one optional leading minus, digits only, no leading zeros except `0`, and no negative zero.
- Scale bounds and sign/range belong to CTR-COMMON-003/M05; PLAN-DB enforces the synchronized storage maximum and rejects overflow.
- Currency minor units use signed 64-bit `INTEGER` only where the currency/contract supplies a verified exponent and value fits the approved range.
- A money value using decimal coefficient/scale and one using minor units are mutually exclusive, with currency required for `value` state.
- Ratios use the approved exact coefficient/scale or basis-point representation and enforce the module-owned range.
- PostgreSQL may use `numeric` internally, but repository round trips must reproduce the same canonical coefficient/scale and reject database rounding.

#### Booleans, enums, digests, and canonical payloads

- Booleans are `INTEGER` constrained to `0` or `1`; NULL is used only when the contract says nullable/unknown.
- Enums are bounded `TEXT`; check constraints are used when the producer has frozen a closed storage vocabulary. Unknown-tolerant public enums still require explicit persisted handling, not coercion.
- Cryptographic digests/PHC strings use the owning security contract's exact `BLOB`/`TEXT` encoding and length; PLAN-DB does not reinterpret them.
- Arbitrary JSON columns are prohibited. A canonical JSON `TEXT` payload is permitted only for a closed, versioned, bounded schema such as an owned outbox event/configuration when its module plan explicitly approves it. It is never a raw provider object and is not queried dynamically.
- SQL NULL, domain Unknown, Unsupported, Unavailable, and zero are distinct; repository mappers never collapse them.

### 3.8 Schema compatibility state machine

CTR-DB-001 reports one of:

```text
missing -> empty -> upgrade_required -> compatible
                    |                    |
                    v                    v
              migration_failed      newer_than_binary

Any state may instead be: locked, unreadable, corrupt,
unknown_revision, multiple_heads, checksum_mismatch, or policy_incompatible.
```

- `missing` and `empty` are valid only for explicit initialization; normal readiness is false.
- `upgrade_required` names current/target revisions and compatibility range without applying them.
- `compatible` requires one known head in the binary's declared readable/writable range, valid migration catalog/checksums, successful connection policy, and required integrity level.
- `newer_than_binary`, unknown/multiple head, checksum mismatch, corrupt, and policy mismatch refuse normal read/write service.
- A service may expose only the separately approved minimal liveness/maintenance surface while incompatible; no protected business data becomes public.
- Startup never invokes Alembic upgrade. Only AUTO-MIGRATE may change schema.

### 3.9 Concurrency, crash, and restart behavior

- SQLite has one writer. The pool does not imply multiple writers can commit concurrently.
- Write UoWs remain short and rely on module idempotency/optimistic/fencing invariants.
- A killed AgentMonitor-owned migration/test process may leave WAL or an unapplied revision; next startup classifies and validates before normal service.
- WAL recovery is allowed only through SQLite's normal open/integrity behavior on an isolated or approved target; PLAN-DB does not edit WAL/SHM bytes.
- A crash after module commit but before caller receipt is reconciled through the module's receipt/idempotency port, not by replaying unknown writes.
- Pool/connection cleanup after fork is mandatory; V1 service is one process, but test/migration subprocesses do not inherit live connections.

## 4. Public contracts

### 4.1 CTR-DB-001 — `SchemaCompatibilityV1`

Producer: PLAN-DB. Consumers: composition, PLAN-DEP, M08, AUTO-MIGRATE, health/API through M08.

Published types/ports:

- `SchemaRevisionV1`: opaque known revision ID and catalog digest; no filename/path.
- `ApplicationSchemaRangeV1`: minimum readable, minimum writable, maximum readable/writable revision, and migration target.
- `SchemaCompatibilityViewV1`: state from section 3.8, current/target/range, integrity/policy states, migration-required flag, safe reason codes, checked time, build/catalog versions.
- `InspectSchemaCompatibilityV1(database_ref, application_range, mode)`.
- `RequireWritableSchemaV1(compatibility_view)` returning approved or a typed refusal.
- `GetDatabaseHealthV1(disclosure_scope)` implementing the DB portion of CTR-OPS-006.

Preconditions: approved opaque database ref and bounded deadline. Queries do not create/migrate/repair. The same unchanged file identity/catalog/build produces the same classification. A semantic change to compatibility states/range/checksum interpretation is breaking.

### 4.2 CTR-DB-002 — repository/unit-of-work implementation contract

CTR-DB-002 is not a generic business interface. It is a governance family connecting producer-owned module ports to concrete SQLite adapters.

Common technical rules:

- `UnitOfWorkFactoryV1` creates one mode-specific UoW with correlation, deadline, and cancellation context;
- `RepositoryOutcomeV1` uses typed module results plus section 3.6 technical errors;
- commit/rollback/close are explicit and exactly-once from the caller's perspective;
- transaction ownership stays in the application use case;
- ORM/session/dialect types never cross the port;
- repository adapter compatibility is declared against one exact module-port major and `sqlite-persistence.v1` major;
- a module adapter cannot access any prefix other than its owner's tables plus Alembic metadata through the core schema inspector;
- no fallback repository, in-memory implementation, or alternate schema is registered in production/tests.

Exact implementation targets:

| Module owner | Producer-owned port family to freeze | SQLite implementation path | Owned prefixes |
|---|---|---|---|
| M01 | `IdentityAccessRepositoryPortV1`, `IdentityAccessUnitOfWorkPortV1` covering bootstrap, administrator, throttle, session, CSRF, token, audit, idempotency, retention | `adapters/persistence/identity_access/sqlite/` | `iam_*` |
| M02 | `RegistryRepositoryPortV1`, `RegistryUnitOfWorkPortV1` covering organization, account, installation, identity, candidate, profile, resource, change, receipt/outbox | `adapters/persistence/registry/sqlite/` | `reg_*` |
| M03 | `ProviderCompatibilityRepositoryPortV1`, `ProviderSystemUnitOfWorkPortV1` | `adapters/persistence/provider_system/sqlite/` | `provider_system_*` |
| M04 | `CollectionRepositoryPortV1`, `CollectionUnitOfWorkPortV1` covering schedule, request, fenced lease, run, budget, instance, receipt/outbox | `adapters/persistence/collection_control/sqlite/` | `collection_*` |
| M05 | `CapacityRepositoryPortV1`, `CapacityUnitOfWorkPortV1` covering definitions, immutable observations, projections, derivations, receipts, availability, retention/outbox | `adapters/persistence/capacity/sqlite/` | `capacity_*` |
| M06 | `RuntimeRepositoryPortV1`, `RuntimeUnitOfWorkPortV1` covering processes, sessions, observations, hierarchy, correlation, policies, transitions, receipts/outbox | `adapters/persistence/runtime_observation/sqlite/` | `runtime_*` |
| M07 | `AlertingRepositoryPortV1`, `AlertingUnitOfWorkPortV1` covering rules, alerts, evidence/events, receipts, deadlines, jobs/outbox | `adapters/persistence/alerting/sqlite/` | `alert_*` |
| M08 | `OperationsRepositoryPortV1`, `OperationsUnitOfWorkPortV1` covering jobs, backups, artifacts, retention, health, audit, receipts/outbox | `adapters/persistence/operations/sqlite/` | `ops_*` |

These planning names make the implementation target unambiguous but do not overrule a producer's final port names or semantics. Each producer plan must adopt or replace the row during synchronization. A changed module transaction meaning is versioned by that module, not silently absorbed by PLAN-DB.

### 4.3 Proposed CTR-DB-003 — `DatabaseSnapshotActivationV1`

Producer: PLAN-DB. Consumers: M08, PLAN-DEP, AUTO-BACKUP/AUTO-RESTORE/AUTO-MIGRATE, A04 filesystem adapter.

Published opaque types:

- `DatabaseRefV1`, `SnapshotTargetRefV1`, `SnapshotReceiptV1`;
- `DatabaseIntegrityReportV1` with `quick | full`, result, checked revision/file generation, UTC time, bounded safe codes;
- `IsolatedDatabaseHandleV1` usable only by maintenance composition and approved module validators;
- `PreparedDatabaseActivationV1` identifying candidate and preserved-current generations without paths;
- `DatabaseActivationReceiptV1` and `DatabaseRollbackReceiptV1`.

Published ports and exact behavior:

| Port | Preconditions | Side effects | Typed outcomes/idempotency |
|---|---|---|---|
| `CreateOnlineDatabaseSnapshotV1` | compatible source, validated new target ref, deadline, operation/correlation IDs | SQLite online backup API writes one new isolated target; no live-file copy | same operation/target returns receipt or conflict; incomplete target never valid |
| `CheckDatabaseIntegrityV1` | approved source/candidate ref, closed or bounded read handle | runs real `quick_check` or full `integrity_check` | clean/corrupt/unreadable/deadline; no repair |
| `GetDatabaseSchemaCompatibilityV1` | isolated or current ref plus application range | read-only inspection | CTR-DB-001 view |
| `OpenIsolatedMigrationTargetV1` | target not active service DB, exclusive maintenance authority | supplies migration runner handle only | one fenced handle; no normal service composition |
| `OpenIsolatedPersistenceContextV1` | schema compatible; approved validators/invalidation list | composes production module repositories against staging DB only | no provider/background/API tasks; close required |
| `PrepareDatabaseActivationV1` | service quiesced, pools disposed, candidate full-integrity/schema/module checks Passed, current preservation target available | validates identities, preserves current generation, writes/fsyncs activation preparation through platform port | replay returns same prepared activation; changed input conflicts |
| `ActivatePreparedDatabaseV1` | matching prepared ID and quiescence/fence still valid | atomic same-filesystem switch and directory fsync | exactly one terminal activation receipt; never deletes preserved current |
| `RollbackDatabaseActivationV1` | activation receipt, service quiesced, preserved current validates | atomically restores preserved current and retains failed candidate | repeat-safe terminal receipt |

Security/compatibility:

- Callers receive no raw paths, connections, SQL, rows, WAL, or credentials.
- M08 owns operation authority/journal/owner checkpoint; DEP proves quiescence; A04 performs approved filesystem primitives; PLAN-DB owns SQLite validity and activation mechanics.
- Snapshot does not checkpoint by copying `db`, `-wal`, and `-shm`; it uses SQLite's online backup API.
- Full integrity and schema compatibility are necessary but not sufficient for restore: M01 invalidation and every required module consistency validator must also pass through production ports.
- Activation/file-format/journal semantics are versioned. A future PostgreSQL implementation replaces this contract implementation without changing M08's business workflow where semantics remain equivalent.

### 4.4 Consumed contracts

| Owner/contract | PLAN-DB use | Failure behavior |
|---|---|---|
| PLAN-FND `migration-metadata.v1` / CTR-FND-006 | ownership, requirements, range, tables, backup, validation, recovery metadata | missing/invalid metadata blocks catalog and migration |
| PLAN-FND configuration/log/correlation/build contracts | settings, safe events, app schema range/catalog digest | invalid config/build metadata blocks engine/readiness |
| M01–M08 repository/UoW ports | concrete persistence implementations | incompatible port major blocks composition |
| M01–M08 consistency/retention ports | post-migration/restore validation | required validator failure blocks normal readiness |
| CTR-OPS-006 | DB health contribution shape | timeout reports Unknown/degraded; no raw diagnostic fallback |
| CTR-PLAT-001 | approved root/object/lock/permission/fsync/atomic primitives | missing Linux primitive blocks migration/snapshot/activation |
| CTR-DEP-001 | quiescence, maintenance, restricted start, normal start | unproven quiescence blocks migration/activation |
| M08 backup/restore job contracts | verified backup prerequisite, operation IDs/journal | absent required backup receipt blocks migration |

### 4.5 Contract-impact assessment

This plan:

- specializes registered Draft-aligned CTR-DB-001 and CTR-DB-002;
- specializes registered Draft-aligned CTR-DB-003, required by the already
  documented M08 boundary;
- specializes CTR-FND-006 with revision allocation/checksum rules;
- does not change a public REST contract or own domain table semantics;
- requires producer-plan synchronization for the exact repository/UoW port family names;
- requires producer/consumer approval and real evidence for the already
  registered, Draft-aligned CTR-DB-003 before this plan can become Synchronized.

Breaking changes to schema-state meanings, transaction semantics, exact-value encoding, snapshot validity, activation authority, or migration history require a new contract major, migration/consumer plan, and an ADR where architectural.

## 5. Data and persistence

### 5.1 PLAN-DB-owned persistent objects

PLAN-DB owns no business history. Its only permitted database objects are:

- Alembic's single `alembic_version` marker;
- an optional `persistence_schema_metadata` technical table only if synchronization proves the repository migration catalog cannot supply required compatibility/checksum state safely.

The default proposal is **no extra technical table**: the current revision comes from `alembic_version`; the repository-owned signed/reviewed `backend/migrations/catalog.toml` supplies immutable chain metadata and SHA-256 revision-file digests. Adding `persistence_schema_metadata` requires root/PLAN-FND/M08 review and a centrally allocated PLAN-DB revision.

No migration creates users, example organizations, sample accounts, telemetry, default alerts, or seeded operational state. Domain defaults such as alert thresholds remain code/persisted-policy behavior owned by their module.

### 5.2 Migration catalog and naming

`backend/migrations/catalog.toml` is the proposed canonical allocation source. Each record contains:

- ordinal and exact Alembic revision ID;
- filename, `down_revision`, branch labels/dependencies (normally none);
- owning plan/module and implementation agent;
- requirement/AC IDs;
- owned table prefixes and exact tables changed;
- schema compatibility introduction/removal range;
- expected row/data volume and lock/downtime class;
- backup requirement (`none_empty_bootstrap | required | owner_decision`);
- upgrade validation and module consistency port;
- safe downgrade classification and recovery path;
- SQLite/PostgreSQL notes;
- normalized file SHA-256 after review;
- status `reserved | implemented | shared | released | superseded` and reviewer/date.

Naming rules:

- revision ID: `v1_NNNN`, fixed four-digit monotonically increasing ordinal;
- filename: `v1_NNNN_<owner>_<bounded_slug>.py`;
- exactly one `down_revision`, producing one head;
- one module owner per revision; mixed-module DDL is prohibited without an accepted cross-module change plan/ADR;
- no merge revisions in V1 unless a separately approved recovery from an accidental branch requires one;
- a reservation is not an empty migration and never enters the chain;
- after status `shared`, file bytes, revision ID, parent, and meaning are immutable; corrections use a new revision.

### 5.3 V1 revision allocation and table ownership matrix

The matrix fixes order and independent ownership. Exact DDL remains the module owner's approved plan. CTR-EVT-TOPOLOGY-001 fixes every producer outbox row under the producing module's prefix and migration; a shared journal is not an implementation alternative.

| Revision | Parent | Owner | Planned scope/tables | Parallel handoff rule |
|---|---|---|---|---|
| `v1_0000` | base | PLAN-FND | Alembic metadata-only anchor; no business table | migration steward only |
| `v1_0100` | `v1_0000` | M01 | `iam_administrator`, `iam_browser_session`, `iam_api_token`, `iam_api_token_scope`, `iam_login_throttle`, `iam_idempotency_record`, `iam_security_audit_event` | M01 owns body; DB reviews mapping/constraints |
| `v1_0200` | `v1_0100` | M02 | `reg_registry_state`, `reg_organization`, `reg_provider_definition`, `reg_account`, `reg_registry_change` | M02 core repository may develop independently after M01 head is reserved |
| `v1_0201` | `v1_0200` | M02 | `reg_provider_installation`, `reg_discovery_candidate`, `reg_provider_identity_claim`, `reg_identity_decision` | no provider data seeded |
| `v1_0202` | `v1_0201` | M02 | `reg_monitoring_profile`, `reg_account_resource`, `reg_profile_resource_link` | locator fields require security approval |
| `v1_0203` | `v1_0202` | M02 | `reg_account_configuration_reference` and synchronized resource/query indexes | no cross-module FK |
| `v1_0204` | `v1_0203` | M02 | `reg_command_receipt`, `reg_event_outbox` | M02 owns event rows; shared mechanics use its port |
| `v1_0300` | `v1_0204` | M03 | `provider_system_compatibility_assessments`, `provider_system_event_outbox` | M03 owns assessment/event rows only, not installations |
| `v1_0400` | `v1_0300` | M04 | `collection_schedule`, `collection_request`, `collection_lease`, `collection_run`, `collection_run_warning`, `collection_run_observation_ref`, `collection_budget_reservation`, `collection_scheduler_instance`, `collection_event_outbox`, `collection_event_delivery` | M04 write/fencing tests required before sharing |
| `v1_0500` | `v1_0400` | M05 | `capacity_resource_policy`, `capacity_quota_window_definition`, `capacity_budget_definition`, `capacity_quota_observation`, `capacity_quota_measure`, `capacity_budget_observation`, `capacity_budget_measure`, `capacity_usage_bucket`, `capacity_usage_dimension`, `capacity_observation_provenance`, conditional `capacity_provider_extension_value` | exact encoding frozen before DDL |
| `v1_0501` | `v1_0500` | M05 | `capacity_commit_receipt`, `capacity_commit_receipt_observation`, `capacity_current_projection` | M04 receipt contract frozen |
| `v1_0502` | `v1_0501` | M05 | `capacity_health_projection`, `capacity_aggregate_projection`, `capacity_aggregate_value`, `capacity_availability_signal`, `capacity_event_outbox`, `capacity_event_delivery` | health/event contracts frozen |
| `v1_0503` | `v1_0502` | M05 | `capacity_derivation`, `capacity_derivation_input`, `capacity_forecast_projection` and measured indexes | no synthetic observations/backfill |
| `v1_0504` | `v1_0503` | M05 | `capacity_retention_run`, export cursor support, measured index adjustments | retention rules approved |
| `v1_0600` | `v1_0504` | M06 | `runtime_session`, `runtime_process_instance`, `runtime_process_snapshot`, `runtime_session_observation` | M0 field allowlist frozen |
| `v1_0601` | `v1_0600` | M06 | `runtime_metric_observation`, `runtime_session_process_link`, `runtime_session_relationship`, `runtime_correlation_evidence`, `runtime_session_correlation_decision` | graph/identity semantics frozen |
| `v1_0602` | `v1_0601` | M06 | `runtime_stall_policy`, `runtime_state_transition`, `runtime_ingest_receipt`, `runtime_event_outbox` | no telemetry seed for 600-second default |
| `v1_0603` | `v1_0602` | M06 | measured indexes/query-plan adjustments | only evidenced indexes |
| `v1_0700` | `v1_0603` | M07 | `alert_rule`, `alert_rule_revision` | 30/15 defaults not seeded rows |
| `v1_0701` | `v1_0700` | M07 | `alert_alert`, `alert_evidence_reference`, `alert_event`, `alert_event_receipt`, `alert_command_receipt` and indexes | upstream recovery contract frozen |
| `v1_0702` | `v1_0701` | M07 | `alert_deadline`, `alert_reevaluation_job`, `alert_event_outbox` | M07 owns event rows; shared mechanics use its port |
| `v1_0800` | `v1_0702` | M08 | `ops_operation_job`, `ops_operation_job_step`, `ops_command_receipt`, `ops_audit_event` | bootstrap backup rule synchronized |
| `v1_0801` | `v1_0800` | M08 | `ops_backup`, `ops_backup_retention_slot` | no backup files embedded in DB |
| `v1_0802` | `v1_0801` | M08 | `ops_artifact` | private object refs only |
| `v1_0803` | `v1_0802` | M08 | `ops_retention_cycle`, `ops_retention_participant`, `ops_component_health_snapshot` | bounded indicator representation frozen |
| `v1_0804` | `v1_0803` | M08 | `ops_event_outbox` and final measured indexes | M08 owns event rows; shared mechanics use its port |

No agent may renumber this matrix privately. If a module combines/splits a proposed revision, the migration steward revises this Draft matrix and all downstream parent allocations before any revision is shared. Implementation branches do not manufacture temporary competing heads.

### 5.4 Cross-module data rules

- Within-module foreign keys are required where the module plan specifies them and SQLite can enforce them portably.
- Cross-module identifiers are scalar opaque IDs. There is no database FK, cascade, trigger, view, or join across module prefixes unless an accepted ADR defines ownership, migration ordering, failure behavior, and extraction path.
- A module repository never validates a scalar external ID by reading the producer's table. The application validates through the producer's published port before opening the write transaction and persists revision/evidence needed for stale-check behavior.
- Database triggers cannot publish cross-module events, perform business state transitions, or maintain another module's projection.
- CTR-EVT-TOPOLOGY-001 permits shared dispatcher and persistence code, not shared event tables. PLAN-DB reaches each producer outbox through that module's event-storage port; consumer processing receipts/checkpoints remain consumer-owned. Direct cross-module table reads/writes are forbidden.
- M08 backup and schema inspection may inspect SQLite technical catalog metadata, but exports/diagnostics use module ports rather than table reads.

### 5.5 Migration execution and lock

`AUTO-MIGRATE` uses this ordered database portion:

1. Resolve exact database object, build schema range, migration catalog digest, current revision, and target revision without writing.
2. Validate owner/mode/file identity, free-space policy, SQLite runtime/version, dependency/build/catalog compatibility, and recovery path.
3. Require M08's fresh verified backup receipt when the catalog row says required. Empty first initialization may use the explicitly approved `none_empty_bootstrap` policy only.
4. Require M08 maintenance intent plus PLAN-DEP's fenced quiescence receipt and drain/dispose every engine.
5. Acquire the A04/platform-backed exclusive migration lock for the exact database object; lock metadata contains only operation ID, process start identity, and expiry/recovery fields.
6. Reinspect file identity/current revision/catalog after the lock; any change aborts.
7. Apply the exact linear approved revision list through the production Alembic environment, one revision boundary at a time, with bounded sanitized progress.
8. After each revision, verify expected head and revision-owned validation query; never print SQL rows.
9. At target, verify PRAGMA policy, `foreign_key_check`, full integrity for migration/recovery scope, schema object allowlist/owner prefixes, and every changed module consistency port.
10. Record sanitized migration evidence/audit receipt; release the migration lock only after durable final result.
11. Start restricted validation mode, then normal service only when CTR-DB-001 and M08 readiness pass.

The lock is not a substitute for service quiescence. A stale lock is never deleted solely by age: platform process-start identity and M08 operation journal must prove the owner is gone and recovery state is understood.

### 5.6 Failed migration and recovery

- Migration DDL is transactional where the admitted SQLite/Alembic behavior genuinely supports it; the plan does not claim all SQLite schema operations roll back atomically.
- A failure stops at the first revision, preserves database/WAL/SHM and sanitized evidence, marks normal readiness false, and does not auto-retry.
- If current revision did not advance but DDL partially changed, schema-object validation classifies `migration_failed`; rerun is prohibited until the revision's reviewed recovery says it is safe.
- Safe, real, tested downgrade may be used only when the catalog declares it. A generated downgrade body or `drop_table` is not considered safe merely because Alembic accepts it.
- Default recovery for a destructive/uncertain failure is the verified pre-migration backup plus compatible prior binary through M08/DEP/CTR-DB-003.
- The failed database is retained under an approved recovery reference until the owner approves disposal; it is never overwritten by restore.
- Forward-fix uses a new revision and normal approval; shared history is never edited.

### 5.7 Fresh, upgrade, downgrade, and prior-release evidence

- Fresh evidence creates a real absent SQLite target through `migration_initialize`, applies the full production chain, validates all approved schema objects, and starts the real service.
- Upgrade evidence begins with a database produced by the actual supported prior release and its production migration/application workflows. It is not a hand-built SQL fixture or copied schema-only fake.
- CI may prove empty-schema upgrade mechanics with prior migration code, but claims about transforming owner data require a sanitized isolated copy of real production-created records or remain Blocked.
- Business rows are created only through production use cases using real owner/module inputs. No direct inserts, factories, seeded telemetry, or backdated records support a persistence claim.
- Downgrade is `Unsupported` unless it is safe, implemented, and executed on a real database. Backup/prior-binary recovery is not mislabeled downgrade.
- Every supported release identifies the oldest/newest readable and writable revisions. Older unsupported and newer revisions fail closed.

### 5.8 Schema inspection and allowlist

The schema validator checks:

- exactly one expected Alembic head;
- every table/index/trigger/view is owned by Alembic/PLAN-DB or one registered module prefix;
- no unexpected cross-prefix FK/trigger/view exists;
- required PK/unique/check/FK/index objects exist with reviewed definitions;
- prohibited columns/types such as unowned arbitrary JSON, float money, prompt/response/content/environment/raw-payload fields do not appear;
- migration catalog table ownership matches the actual revision history;
- no `CREATE TABLE` occurred outside migration history.

The validator compares normalized structural metadata, not row contents, and never dumps `sqlite_master.sql` into user-visible evidence when it could expose sensitive names beyond the approved schema catalog.

### 5.9 Snapshot, backup, and restore seam

Snapshot creation:

- source is an open compatible real SQLite database under normal WAL operation;
- destination is a new exact platform object opened exclusively with owner-only permissions;
- SQLite online backup copies bounded page batches and observes cancellation/deadline without holding a long application write transaction;
- destination is closed, fsynced through the platform contract, reopened independently, full-integrity checked, and schema-classified;
- incomplete/failed destinations never receive a valid receipt and are quarantined under exact operation ownership for safe cleanup;
- M08 computes/catalogs checksum and retention only after PLAN-DB returns a valid snapshot receipt.

Restore/activation:

- M08 selects an exact cataloged backup ID and obtains local owner authority;
- checksum/integrity/schema are verified before any activation;
- staging is migrated only through AUTO-MIGRATE isolated-target mode;
- production module consistency checks and mandatory M01 credential invalidation run through production repositories in `OpenIsolatedPersistenceContextV1`;
- the active service is quiesced and every engine disposed;
- current DB is preserved under a new exact recovery object before switch;
- same-filesystem atomic activation and directory fsync occur through A04 platform primitives;
- restricted startup validates schema, module consistency, IAM re-login requirement, and M08 readiness before normal collection resumes;
- rollback restores the preserved current object if validation fails and retains the failed candidate.

### 5.10 Integrity and database health

Checks and cadence:

- connection checkout verifies connection-local policy;
- startup/restart performs bounded `quick_check`, schema compatibility, foreign-key configuration, and WAL state review;
- AUTO-MIGRATE, AUTO-BACKUP snapshot destination, and AUTO-RESTORE candidate/activated target perform full `integrity_check` plus `foreign_key_check`;
- periodic full checks, if adopted, are scheduled by M08 with measured impact and do not run concurrently with migration/activation;
- a failed integrity check never triggers repair or deletion.

CTR-OPS-006 DB health may disclose only:

- reachable/unreachable, read/write mode, schema compatibility state/current-safe revision, policy state;
- quick/full integrity result and checked time;
- WAL/checkpoint safe state and age/size class, not path;
- pool saturation and busy/lock counts/durations as bounded local measurements;
- last successful migration/snapshot/integrity times and safe operation IDs;
- stable safe reason/remediation codes.

It excludes SQL, row/table data beyond registered schema versions, paths, usernames, account labels, secrets, raw exceptions, or file contents.

### 5.11 PostgreSQL portability contract

The SQLite adapter may use WAL, PRAGMAs, `BEGIN IMMEDIATE`, SQLite online backup, file activation, and SQLite error codes internally. None appears in a module repository/UoW port.

Portability review covers:

- opaque ID/text and timestamp mappings;
- exact decimal/money ranges and canonical round trip;
- boolean/enum/check behavior;
- unique/partial index and NULL uniqueness differences;
- optimistic version/fencing and upsert conflict semantics;
- transaction isolation and retry classification;
- pagination/collation/order stability;
- graph/cycle query implementation;
- outbox ordering/idempotency;
- migration compatibility and backup/activation replacement.

Every module-specific SQLite optimization receives a PostgreSQL alternative or documented limitation before sharing the revision. A future PostgreSQL plan implements the same producer-owned repository ports and replaces CTR-DB-003 physical behavior under a new deployment ADR.

## 6. External and platform boundaries

### 6.1 Filesystem and locking

PLAN-DB consumes CTR-PLAT-001 for exact approved-root resolution, regular-file/owner/mode/symlink checks, exclusive object creation, free-space query, advisory lock with process-start identity, fsync file/directory, same-filesystem atomic replace, and exact-object retirement. Raw paths never enter domain/M08/API contracts.

Linux is verified first against the actual target filesystem. Atomic rename, fsync, WAL/SHM permissions, advisory lock, crash recovery, and service-user ownership are not inferred from Python portability. macOS implements the same semantic port on real macOS or stays Blocked.

### 6.2 Native service lifecycle

M08 owns application maintenance intent/state; PLAN-DEP owns fenced service
quiescence execution and its narrow receipt. PLAN-DB requires typed proof that:

- new mutations/collectors stopped;
- active UoWs drained or reached a documented timeout;
- every pool/engine was disposed;
- no normal service instance can reopen the database during migration/activation;
- restricted validation and normal restart are separate phases.

A PID file or process absence alone is insufficient quiescence evidence.

### 6.3 M08 operations boundary

M08 owns job admission, authorization/owner checkpoint, backup catalog/checksum/GFS, restore journal, product audit, retention, and overall readiness. PLAN-DB returns typed physical database receipts only. It never selects a backup, purges a catalog entry, prompts for owner authority, or starts/stops the service itself.

### 6.4 No provider/network boundary

PLAN-DB contacts no provider and requires no internet at runtime. It never reads provider profiles, process metadata, arbitrary environment variables, prompts, responses, source, or raw provider output. Dependency installation/advisory retrieval is a separately approved development/release action, not persistence runtime behavior.

### 6.5 Timeouts, retries, and cancellation

- Pool acquisition, SQLite busy wait, migration step, snapshot page loop, integrity, platform lock, and activation all have explicit deadlines.
- No automatic transaction/migration/activation retry occurs after a side effect may have happened.
- Snapshot page loops may continue/retry only under SQLite's documented online-backup semantics within the same operation/deadline; the receipt reports interruption truthfully.
- Cancellation before commit/activation rolls back or leaves a classified incomplete object; cancellation never deletes the original/current database.

## 7. Security and privacy

### 7.1 Trust boundaries and controls

| Threat | Control | Verification |
|---|---|---|
| Wrong/arbitrary database path | opaque refs, approved root, exact object, traversal/symlink/owner/mode checks | DB-FILE-003..006 |
| Missing DB silently created | runtime `mode=rw`; creation only migration initialize | DB-FILE-001/002 |
| Cross-module data coupling | prefix/metadata/import/SQL checks; no cross-FK/join | DB-REP-001/002, DB-SEC-001/002 |
| SQL injection | typed repositories and parameterized SQL; no dynamic caller SQL | DB-SEC-003 |
| Secret/content leak in errors/logs | stable codes and allowlisted diagnostics; canary scans | DB-SEC-005..008 |
| SQLite lock denial | bounded pool/busy wait/short write transactions/health | DB-TXN-004..010 |
| Corruption/data loss | WAL/FULL, integrity, online snapshot, preserve-on-failure | DB-SNAP-001..012 |
| Migration tampering | immutable checksums/catalog/one head/reviewer | DB-MIG-001..004 |
| Unsafe restore | exact backup, quiescence, staging, full validators, preserve current, rollback | DB-SNAP-006..012 |
| Dependency compromise | exact admission/locks/SBOM/notices/scans | DB-DEP-001/002 |

### 7.2 Data minimization and prohibited data

PLAN-DB persists exactly the columns approved by each table owner. It cannot add a convenience raw payload, request/response, exception, SQL history, filesystem path, arbitrary metadata JSON, prompt, response, tool/source content, command line, environment, provider credential, cookie, OTP/MFA value, or telemetry field.

Database query logging with bind values is disabled. SQL statement text is not emitted in normal logs. Development diagnostics may name an approved operation category and module/table owner, never values or raw database output.

### 7.3 Permissions and secret classification

- Database/WAL/SHM/snapshot/staging/preserved-current files are sensitive owner data and mode `0600` under owner-only roots.
- The database is not a secret store for provider credentials or `.env` values. It does contain sensitive password/token verification material and operational identities/usage; backups inherit that classification.
- Database path is non-secret configuration but privacy-sensitive and never exposed through UI/API/log/evidence.
- No database password or encryption key exists in V1 SQLite configuration.

### 7.4 Abuse and failure behavior

- Oversized pages, unbounded filters, long history queries, or arbitrary sort expressions are rejected by module/P01 contracts before repositories.
- Repeated busy/lock failures degrade health; the adapter does not spin/retry indefinitely.
- Disk-full, I/O, corruption, and integrity failure stop writes and preserve evidence; they do not trigger cleanup.
- A schema checksum or unknown object mismatch blocks normal service and requires review; PLAN-DB does not delete the object.
- Any observed secret/content/raw payload in logs/evidence triggers the incident stop rule.

### 7.5 Audit and safe logs

Allowlisted structured events include connection-policy verification result, schema compatibility state, migration operation/revision state, lock acquire/release/recovery classification, integrity result, snapshot/activation/rollback state, pool pressure, and typed database error counts. Fields are correlation/operation ID, module owner, revision, safe state/code, duration/count, and timestamps. M08 owns product audit rows; PLAN-DB does not create a general SQL audit log.

## 8. Configuration and operations

### 8.1 Proposed configuration registry

Exact allocation requires CTR-CONFIG-001/PLAN-DEP review.

| Proposed key | Owner | Type/default/range | Secret | Reload | Rule |
|---|---|---|---|---|---|
| `AGENTMONITOR_PERSISTENCE_DATABASE_PATH` | PLAN-DB with DEP root policy | path; installed default derived from approved data root; isolated tests explicit | no, privacy-sensitive | restart | resolved/validated; value never diagnosed |
| `AGENTMONITOR_PERSISTENCE_BUSY_TIMEOUT_MILLISECONDS` | PLAN-DB | integer; default 5000; range 100..60000 | no | restart | one bounded SQLite wait |
| `AGENTMONITOR_PERSISTENCE_POOL_SIZE` | PLAN-DB | integer; default 5; range 1..16 | no | restart | `max_overflow=0` in V1 |
| `AGENTMONITOR_PERSISTENCE_POOL_TIMEOUT_SECONDS` | PLAN-DB | integer; default 5; range 1..60 | no | restart | bounds checkout |

`WAL`, `FULL`, foreign keys on, read-uncommitted off, 1000-page auto-checkpoint, runtime trusted-schema off, and normal-service no-create behavior are versioned secure code policy, not operator knobs. Weakening them requires a change plan, real evidence, and compatibility/security review.

Automated tests supply isolated configuration explicitly and never read the operator's `.env`. Diagnostics report only setting source and safe policy version; the path is `configured | invalid | missing`, never printed.

### 8.2 Health/readiness

Database health is supplied through CTR-OPS-006 as described in section 5.10. Normal readiness is false for missing/empty/upgrade-required/newer/unknown/multiple/checksum mismatch/policy mismatch/corrupt/unreadable/locked-after-deadline states. A transient busy query can degrade an operation without making historical API reads public or bypassing authentication; M08 owns aggregate readiness.

### 8.3 Canonical automation ownership

PLAN-DB owns the database behavior and selectors for:

- `AUTO-MIGRATE`: schema preflight, catalog/lock, exact revision execution, database validations, evidence, and safe failure;
- `AUTO-TEST`: PLAN-DB T2/T5/T7 selectors with real file/migration/concurrency/filesystem boundaries;
- `AUTO-QUALITY`: schema ownership, cross-module FK/SQL/import, migration checksum/head, exact-value, secret, dependency, and portability checks;
- `AUTO-DOCS-CHECK`: migration catalog/requirements/contracts/scenario/runbook links;
- `AUTO-BACKUP`: CTR-DB-003 online snapshot/integrity portion, orchestrated by M08;
- `AUTO-RESTORE`: staging/integrity/schema/activation/rollback portion, orchestrated by M08/DEP;
- `AUTO-DEPLOY`: database path/permission/schema preflight, consumed by PLAN-DEP;
- `AUTO-RELEASE`: schema range/catalog/migration/recovery evidence consumed by PLAN-INT.

The proposed wrapper source is `tooling/automation/database/**`, owned by the integration/automation steward. Final executable syntax remains unregistered until implementation and real evidence. A prose sequence or personal shell command is not canonical automation.

### 8.4 AUTO-MIGRATE coordination contract

Responsibility split:

| Phase | Owner | Required receipt |
|---|---|---|
| resolve installed target/build/config/free space | DEP/FND/PLAN-DB | preflight |
| enter maintenance and quiesce/drain | DEP | quiescence |
| fresh verified backup when required | M08 using DB snapshot | backup validity |
| lock/inspect/apply/validate schema | PLAN-DB | migration result |
| validate changed modules | M01–M08 through ports | consistency results |
| restricted then normal start/readiness | DEP/M08 | readiness |
| failure recovery/rollback decision | M08/DEP/owner with DB activation | recovery result |

No phase silently substitutes for another. A valid backup without quiescence does not authorize migration; a successful Alembic exit without integrity/module/readiness validation is not a Passed migration.

### 8.5 Operator procedures to implement and exercise

- inspect safe database/schema/integrity/policy health;
- initialize an exact new database through AUTO-MIGRATE;
- upgrade from each supported prior release with backup/maintenance/recovery;
- investigate busy/locked pool and long transaction symptoms;
- run full integrity without dumping rows;
- create/verify an online snapshot through AUTO-BACKUP;
- stage/validate/activate/roll back a restore through AUTO-RESTORE;
- respond to newer/unknown/checksum mismatch/corruption/disk-full/permission failure;
- reconcile WAL/checkpoint growth without copying/deleting live sidecars;
- review PostgreSQL portability before schema change.

Commands remain Planned until implemented, registered, and real-executed.

### 8.6 Local operational measurements

Allowed bounded local measurements are pool checkout wait, transaction duration, busy/locked counts, write duration, migration step duration/state, WAL/checkpoint size class, snapshot pages/duration, integrity duration/result, and schema/connection policy states. Labels use registered module/operation/outcome keys and never IDs that create unbounded cardinality, SQL, paths, account labels, or values. No external analytics or crash reporting exists.

## 9. Test design before implementation

### 9.1 Evidence integrity rules

- Every scenario below starts `Not Run`.
- All database claims use a real temporary SQLite file and the production engine, migration chain, repository adapter, and configuration.
- `:memory:`, temporary schemas inside the operator database, fake repository/UoW, monkeypatching, SQL interception, replay, emulator, and test-only engine/migration paths are prohibited.
- Business records are created only through production application use cases with real eligible input. No direct SQL inserts, ORM factories, fixtures, seeded identities/accounts/telemetry/alerts, or backdated rows prove repository behavior.
- Empty schema/migration tests may use an empty real database because no provider/business claim is made.
- Upgrade data tests use databases created by actual prior production releases/workflows. If real data for a transformation is unavailable, that row is Blocked.
- Concurrency uses real threads/processes and independent production connections against one file.
- Permission/corruption/crash/disk tests use an exact isolated real resource and approved destructive-test packet. They never target owner data.
- Red is a behavior failure at the intended boundary, not a missing dependency, syntax/setup error, unavailable account, or absent platform.
- Evidence contains command ID, versions, database generation/revision, boundary, status, duration, and safe codes—not paths, SQL, rows, secrets, or content.

### 9.2 Real file, configuration, and connection scenarios

| Test ID | Requirement/AC | Real boundary | Expected behavioral Red | Green/pass condition | Coordination |
|---|---|---|---|---|---|
| DB-FILE-001 | NFR-DATA-001 | normal production engine + absent real path | service silently creates DB | normal open refuses missing target; file remains absent | FND/DEP |
| DB-FILE-002 | AC-V1-004 | AUTO-MIGRATE initialize + absent isolated path | explicit initialization cannot create/migrate exact target | target created once, reaches approved head, validates | migration steward |
| DB-FILE-003 | NFR-SEC-001 | real owner-only directory/file | insecure mode is accepted | parent/file/WAL/SHM ownership/mode policy enforced | A04 Linux |
| DB-FILE-004 | NFR-SEC-001 | real symlink target | engine follows symlink | preflight refuses without opening target | A04/security |
| DB-FILE-005 | NFR-SEC-001 | real traversal/outside-root config | arbitrary path is opened | safe validation failure; no outside write | A04/security |
| DB-FILE-006 | NFR-SEC-001 | real special file/hard-link anomaly | target accepted as DB | exact unsafe file identity rejected | A04/security |
| DB-FILE-007 | FR-OPS-002/006 | real runtime connection | FK/journal/sync/busy/isolation policy absent or wrong | every effective setting matches section 3.3 | M08 |
| DB-FILE-008 | CTR-DB-001 | real empty/older/current/newer/unknown files | states collapse or writable start succeeds incorrectly | exact compatibility/refusal state returned | FND/DEP |
| DB-FILE-009 | NFR-RES-001 | real pool/process startup-shutdown | connections/locks leak after stop | pool drains/disposes and exact file can be reopened/activated | DEP |
| DB-FILE-010 | NFR-PLAT-001 | real Linux, then real macOS | Linux behavior leaks into core or macOS inferred | Linux passes; macOS passes separately or remains Blocked | A04 |

### 9.3 Real transactions and concurrency scenarios

| Test ID | Requirement/AC | Real boundary | Expected behavioral Red | Green/pass condition | Coordination |
|---|---|---|---|---|---|
| DB-TXN-001 | NFR-DATA-001 | real module UoW | exception leaves partial rows | complete UoW rollback and connection reusable | module owner |
| DB-TXN-002 | NFR-DATA-001 | real module UoW | commit leaks live ORM/lazy load | domain result remains valid; no post-close I/O | module owner |
| DB-TXN-003 | NFR-ARCH-002 | real nested use case | hidden nested transaction commits independently | unsupported nesting rejected or synchronized composition works exactly | integration |
| DB-TXN-004 | R-011 | two real writers/processes | second writer spins/hangs or raw error leaks | bounded timeout and typed busy outcome | DB owner |
| DB-TXN-005 | NFR-RES-001 | real reader plus writer in WAL | reader blocks all write or sees partial commit | consistent old/new snapshot only; bounded progress | DB owner |
| DB-TXN-006 | NFR-RES-001 | killed AgentMonitor-owned writer process | committed/partial state becomes ambiguous | SQLite recovery plus module receipt/invariant classifies state | approved destructive packet |
| DB-TXN-007 | NFR-PERF-001 | real approved application activity | pool exhaustion is unbounded/hidden | bounded wait/health and target latency budget | performance owner |
| DB-TXN-008 | NFR-DATA-001 | real optimistic update | two updates silently overwrite | one commit; one typed conflict | module owner |
| DB-TXN-009 | NFR-DATA-001 | real fenced lease/job operation | stale fence commits | stale holder rejected inside transaction | M04/M07/M08 |
| DB-TXN-010 | NFR-RES-001 | real cancellation during UoW | lock/session remains or commit occurs | rollback/close with typed cancelled result | integration |
| DB-TXN-011 | NFR-DATA-001 | real long page/history use case | unbounded transaction monopolizes writer/pool | bounded pages/connections; no writer starvation beyond budget | module/P01 |
| DB-TXN-012 | NFR-OBS-001 | real failures and logs | SQL/binds/path/row data emitted | allowlisted safe codes/correlation only | security |

### 9.4 Real migration and schema scenarios

| Test ID | Requirement/AC | Real boundary | Expected behavioral Red | Green/pass condition | Coordination |
|---|---|---|---|---|---|
| DB-MIG-001 | NFR-COMP-001 | real revision catalog/files | duplicate/gap/wrong owner/head accepted | one linear owned chain and exact parent order | migration steward |
| DB-MIG-002 | NFR-COMP-001 | real shared revision changed | checksum change goes unnoticed | immutable checksum mismatch blocks gate/start | integration |
| DB-MIG-003 | CTR-DB-001 | real current DB/build | current/range/head misclassified | exact state and safe revision metadata | FND/M08 |
| DB-MIG-004 | CTR-FND-006 | real revision metadata | missing requirements/backup/validation/recovery passes | catalog validation fails closed | docs/integration |
| DB-MIG-005 | AC-V1-004 | real absent file/full chain | fresh apply fails or hidden DDL needed | complete head/integrity/service start | all module owners |
| DB-MIG-006 | AC-V1-004 | actual supported prior-release empty DB | supported schema cannot upgrade | exact approved chain and validations pass | release owner |
| DB-MIG-007 | AC-V1-004 | isolated real prior-release operational DB | real records lose meaning/data | production views/invariants match migration contract | owner/module; Blocked until data exists |
| DB-MIG-008 | NFR-ARCH-002 | real schema inspector | unowned/cross-prefix table/FK/trigger/view passes | ownership gate rejects it | architecture |
| DB-MIG-009 | NFR-DATA-001 | normal app startup against older DB | startup migrates implicitly | no DDL; readiness says upgrade required | FND/DEP |
| DB-MIG-010 | AC-OPS-005 | real migration with DB lock held | migration races/hangs | bounded lock failure; source unchanged | DEP/DB |
| DB-MIG-011 | AC-OPS-005 | real corrupted isolated candidate | Alembic writes/claims success | preflight/integrity blocks migration | approved destructive packet |
| DB-MIG-012 | AC-OPS-005 | real permission loss on isolated target | partial failure hidden/retried | Failed state, preserved evidence/backup recovery | A04/owner approval |
| DB-MIG-013 | AC-V1-004 | real newer/unknown/multiple-head DB | older binary writes | normal service refuses | release owner |
| DB-MIG-014 | AC-V1-004 | real safe downgrade candidate if any | untested downgrade advertised | only executed verified downgrade is Supported; otherwise explicit Unsupported | module owner |
| DB-MIG-015 | AC-OPS-005 | real post-migration module validators | Alembic exit alone starts service despite invariant failure | restricted start remains blocked and recovery invoked | M01–M08/M08 |
| DB-MIG-016 | NFR-COMP-001 | real rollback/forward-fix rehearsal | shared revision edited or only DB overwritten | prior backup/current evidence preserved; new revision used | integration |

### 9.5 Real module repository and exact-value scenarios

| Test ID | Requirement/AC | Real boundary/input source | Expected behavioral Red | Green/pass condition | Coordination |
|---|---|---|---|---|---|
| DB-REP-001 | NFR-ARCH-002 | real source/schema | repository reads/writes other prefix | static/schema/SQL review rejects cross-owner access | all modules |
| DB-REP-002 | NFR-ARCH-002 | real module composition | generic repository/ORM leaks into domain | only producer-owned typed ports visible | architecture |
| DB-REP-003 | FR-IAM-001..005 | M01 production bootstrap/auth/token workflows | IAM constraints/transactions fail or plaintext persists | real M01 workflow and artifact scans pass | M01/security |
| DB-REP-004 | FR-ORG-001..003; FR-ACC-001..006 | M02 production workflows and real enrolled identities | registry history/uniqueness/transactions fail | module contract passes without direct seeded accounts | M02/owner |
| DB-REP-005 | FR-COL-001..008 | M04 real schedules/runs/leases from approved targets | fencing/idempotency/restart state fails | production run receipts/queries pass | M04/live target |
| DB-REP-006 | FR-QUOTA-001..006; FR-BUDGET-001..006 | M05 real provider observations | exact values round/float/current selection corrupts | canonical exact round trip and real reconciliation pass | M05/owner |
| DB-REP-007 | FR-DISC-001..008; FR-STATE-001..004 | M06 real process/session observations | identity/time/metrics/hierarchy persistence corrupts | production views/invariants pass | M06/A04/providers |
| DB-REP-008 | FR-ALERT-001..006 | M07 naturally produced real signals | dedupe/lifecycle/receipts persistence fails | real app lifecycle/history pass | M07/producer owners |
| DB-REP-009 | FR-OPS-002..006 | M08 production backup/artifact/job workflows | catalog/job/fencing persistence inconsistent | real operations workflows pass | M08 |
| DB-REP-010 | NFR-DATA-001 | production exact ID/time values from real workflows | ID/time changes or naive value accepted | byte/semantic round trip and UTC enforcement | modules |
| DB-REP-011 | NFR-DATA-001 | real provider money/ratio values | binary float/rounding/overflow accepted | coefficient/scale/minor-unit round trip exactly | M05/owner |
| DB-REP-012 | NFR-PERF-001 | real accumulated operational DB | query plans scan unbounded history or miss budgets | approved indexes/query/latency budgets pass | owner/performance; Blocked until volume exists |

### 9.6 Real snapshot, activation, and recovery scenarios

| Test ID | Requirement/AC | Real boundary | Expected behavioral Red | Green/pass condition | Coordination |
|---|---|---|---|---|---|
| DB-SNAP-001 | FR-OPS-003 | live WAL DB + SQLite online backup | live file copy needed/inconsistent snapshot | online API produces independently valid snapshot | M08 |
| DB-SNAP-002 | FR-OPS-003 | real concurrent production writes during snapshot | snapshot blocks/corrupts or includes partial transaction | consistent point-in-time snapshot; bounded writer impact | M04/M08 |
| DB-SNAP-003 | FR-OPS-003 | real snapshot target/filesystem | invalid permissions/symlink target accepted | exact new owner-only target only | A04/security |
| DB-SNAP-004 | AC-OPS-004 | real snapshot | checksum/integrity/schema receipts disagree | M08 catalog only after all required receipts agree | M08 |
| DB-SNAP-005 | NFR-RES-001 | interrupted snapshot on isolated target | partial target becomes valid/overwrites prior | no valid receipt; source/prior backups unchanged | approved destructive packet |
| DB-SNAP-006 | AC-OPS-004 | real cataloged backup to staging | arbitrary/raw path restore works | exact backup ID/opaque refs only | M08/security |
| DB-SNAP-007 | AC-OPS-004 | real staging migration and validators | candidate activates before validation | full required validations/invalidation gate activation | M01–M08 |
| DB-SNAP-008 | AC-OPS-004 | real service/pool handles | activation occurs without proven quiescence | preparation refuses until every handle drained | DEP |
| DB-SNAP-009 | AC-OPS-004 | real same-filesystem activation | current DB overwritten/deleted | current preserved; atomic switch/fsync receipt | A04/M08 |
| DB-SNAP-010 | AC-V1-007 | real DB/WAL/snapshot/log/evidence | secret/content/path leaks through receipt/output | scans pass; typed metadata only | security |
| DB-SNAP-011 | AC-OPS-005 | forced restricted-start validation failure | failed candidate stays active/no rollback | preserved current restored; failed candidate retained | M08/DEP |
| DB-SNAP-012 | AC-OPS-004 | post-activation real service | DB integrity passes but app/login/modules fail unnoticed | normal readiness only after app/module/IAM checks | M01–M08/P01 |

### 9.7 Architecture, security, platform, dependency, and documentation scenarios

| Test ID | Requirement/AC | Real boundary | Expected behavioral Red | Green/pass condition | Coordination |
|---|---|---|---|---|---|
| DB-SEC-001 | FR-SAFE-002 | public contracts/source | process/provider-control operation exists | no signal/kill/restart/inject/route/profile operation | security |
| DB-SEC-002 | NFR-ARCH-002 | SQL/import/schema inventory | cross-module query/FK/repository exists | none without accepted ADR | architecture |
| DB-SEC-003 | AC-TEST-002 | actual tests/dependencies/source | fake/mock/in-memory/fixture framework accepted | prohibited mechanism scan/review clean | test-integrity |
| DB-SEC-004 | AC-TEST-001/006 | actual evidence reports | missing Red or Blocked hidden by aggregate green | exact R/G/R and statuses remain distinct | integration |
| DB-SEC-005 | AC-V1-007 | real logs/errors/diagnostics | SQL/binds/path/secret canary appears | allowlist scan clean | security |
| DB-SEC-006 | NFR-PRIV-001 | real schema catalog | prohibited content/raw/environment field exists | schema inventory matches approved module plans | privacy |
| DB-SEC-007 | NFR-PRIV-002 | real process/dependency traffic | persistence emits analytics/crash data | no outbound runtime traffic | privacy |
| DB-SEC-008 | NFR-SEC-001 | real isolated corrupt/permission/full conditions | unsafe cleanup/repair or broad path action occurs | fail closed; exact target preserved | owner/security |
| DB-PORT-001 | NFR-PLAT-001 | real Linux filesystem | rename/fsync/lock assumptions fail | Linux contract passes on target FS | A04 Linux |
| DB-PORT-002 | NFR-PLAT-001 | real macOS filesystem | status inferred from Linux | real pass or visible Blocked | A04 macOS |
| DB-PORT-003 | NFR-DATA-001 | portability mapping review/tests | SQLite rowid/pragma/error escapes port | public ports remain dialect-neutral | architecture |
| DB-PORT-004 | NFR-DATA-001 | approved PostgreSQL compatibility analysis | exact-value/index/null/concurrency mapping absent | reviewed mapping/limitation per table/repository | future DB reviewer |
| DB-PORT-005 | NFR-COMP-001 | real migration/schema artifacts | SQLite optimization has no migration/exit plan | documented alternative and compatibility impact | migration reviewer |
| DB-PORT-006 | NFR-RES-001 | real SQLite version/runtime matrix | unsupported SQLite silently used | version/capability preflight fails safely | dependency owner |
| DB-DEP-001 | NFR-LIC-001 | actual manifests/locks/upstream | unadmitted SQLAlchemy/Alembic/transitive exists | exact approved locked inventory/SBOM/notices | dependency reviewer |
| DB-DEP-002 | NFR-LIC-001 | actual packages/advisories | blocking license/security/provenance issue hidden | no unresolved blocker or approved expiring exception | dependency/security |
| DB-DOC-001 | NFR-DOC-001 | actual docs/catalog/contracts | stale/broken ownership/revision/runbook link | AUTO-DOCS-CHECK passes exact plan scope | docs owner |
| DB-DOC-002 | NFR-DOC-001 | actual command registry/runbook | prose/TBD command represented executable | only real-tested registered commands authoritative | operations |

### 9.8 Failure, migration, and recovery coverage

The matrix covers missing/unsafe paths, wrong permissions, symlinks, policy mismatch, pool exhaustion, writer contention, process crash, cancellation, optimistic/fencing conflicts, migration branches/checksum/locks/permission/corruption/newer schema/module validation, exact value round trips, online snapshot interruption, activation failure, rollback, logs/artifacts, and platform portability.

Naturally unavailable disk-full, real long-horizon operational volume, prior-release owner data, and macOS states remain Blocked. Tests never make them pass through fake filesystems, quotas, backdated rows, or machine-clock changes.

### 9.9 Mutation and coverage quality

- Critical pure encoding/schema-range/error-classification policies require every documented branch covered and a mutation target selected by the test steward.
- Repository/migration/snapshot line coverage does not replace real T2/T5/T7 behavior.
- A meaningful mutant that removes schema refusal, exact-value bounds, cross-module protection, backup precondition, or activation validation must be killed or independently classified equivalent.
- No low-value test is added solely to reach a percentage.

## 10. Implementation increments

Every behavior increment follows Red → Green → Refactor after the admitted toolchain works. Dependency/tool setup is a prerequisite, not Red evidence.

| Increment | Primary owner/files | Failing tests first | Minimum production change | Refactor/documentation | Exit evidence |
|---|---|---|---|---|---|
| DB-I00 — synchronize contracts/allocation | plans/contracts/catalog proposals only | no product Green claim | approve CTR-DB-001/002/003, paths, settings, revision matrix | update register/ADR decisions | owner/reviewer decisions; still no code |
| DB-I01 — file/connection policy | PLAN-DB SQLite core | DB-FILE-001..010 | modes, safe ref resolution, engine/pool/PRAGMA verification | config/health docs | real file/process R/G/R |
| DB-I02 — UoW/error/type core | PLAN-DB SQLite core | DB-TXN-001..005/010/012, DB-REP-010/011 | transaction modes, typed errors, common mappings | portability/security docs | real SQLite R/G/R |
| DB-I03 — migration catalog/compatibility | PLAN-DB/FND allocated shared files | DB-MIG-001..005/008/009/013 | catalog validator, schema inspector, Alembic mechanism/anchor | migration runbook | fresh real DB/head/refusal evidence |
| DB-I04 — M01 repository adapter | M01 allocated adapter + `v1_0100` | DB-REP-003 and M01 DB tests | implement approved M01 ports only | M01 migration/security notes | production M01 workflows |
| DB-I05 — M02 repository adapter | M02 allocated adapter + `v1_0200..0204` | DB-REP-004 and M02 DB tests | implement approved M02 ports only | registry migration notes | real owner registry workflows |
| DB-I06 — M03/M04 adapters | independent M03/M04 paths; serialized revisions | DB-TXN-008/009, DB-REP-005 and module tests | compatibility plus collection/fencing ports | concurrency/restart docs | real target/run evidence |
| DB-I07 — M05/M06 adapters | independent M05/M06 paths; serialized revisions | DB-REP-006/007/010/011 and module tests | exact capacity/runtime persistence | field/portability docs | real observations only |
| DB-I08 — M07/M08 adapters | independent M07/M08 paths; serialized revisions | DB-REP-008/009 and module tests | alert/operations repositories | recovery/retention docs | production workflows |
| DB-I09 — AUTO-MIGRATE | PLAN-DB automation + DEP/M08 composition | DB-MIG-006..016 | lock, backup receipt, exact upgrade, validations, safe failure | command registry/runbook | fresh/prior/failure evidence |
| DB-I10 — snapshot/integrity | PLAN-DB snapshot adapter + M08 | DB-SNAP-001..007/010 | online backup, integrity, isolated context | backup contract docs | real backup receipt/artifact scans |
| DB-I11 — activation/rollback | PLAN-DB/A04/DEP/M08 | DB-SNAP-008/009/011/012 | prepared activation, atomic switch, rollback | restore runbook/journal contract | owner-approved real recovery rehearsal |
| DB-I12 — hardening/portability | all allocated DB paths | DB-TXN-006..012, DB-REP-012, DB-SEC/PORT/DEP/DOC | measured policies/indexes/health/gates | final compatibility report | all actual statuses visible |

### 10.1 Parallel-safe execution

After DB-I03 and producer-port approval:

- DB-I04 and DB-I05 can implement in separate module paths but revision integration follows the fixed chain.
- DB-I06 through DB-I08 module repository adapters can proceed in parallel in non-overlapping paths once their producer contracts/M0 gates are ready.
- The migration steward alone edits `catalog.toml`, attaches revision parents, and integrates `versions/` in ordinal order.
- Only PLAN-DB edits SQLite core; module agents consume it through the approved technical surface.
- Only M08/DEP/A04 owners edit their operation/platform/service implementations; DB agents consume ports.
- Generated OpenAPI/client and public API are unaffected unless M08/P01 separately maps health/operation contracts.

An adapter implementation stops if its producer port changes semantically. It does not copy the old interface or reach directly into module/application/table internals.

### 10.2 TDD evidence per increment

Each handoff records requirement/AC IDs, plan/contract/schema versions, exact scenario, canonical Red command/time/expected behavior failure, minimal Green change and command/result, refactor command/result, real boundary/environment versions, migration/catalog diff, Passed/Failed/Blocked/Not Run rows, security/privacy/license/docs impact, and next shared-head action.

## 11. Documentation outputs

Required maintained outputs after implementation:

- `docs/modules/persistence-sqlite.md`: outcome, modes, settings, UoW/error/type policy, health, limits;
- `docs/contracts/database-v1.md`: CTR-DB-001/002/003 schemas, errors, compatibility, authority, idempotency;
- `docs/operations/database-migrations.md`: verified AUTO-MIGRATE preflight/apply/validation/failure/recovery;
- M08 backup/recovery runbook updates for CTR-DB-003;
- PLAN-DEP install/upgrade/service runbook updates for DB paths/quiescence/restricted start;
- configuration registry entries and safe diagnostics;
- migration catalog and per-revision owner/requirements/backup/validation/recovery/PostgreSQL notes;
- schema ownership/prohibited-field inventory and portability report;
- real test evidence reports with all non-Passed states;
- dependency admission, lock, SBOM, notices, vulnerability/license review;
- traceability/risk/known-limitations/release notes for every schema-range change;
- an ADR if CTR-DB-003 activation, a technical schema table, the CTR-EVT-TOPOLOGY-001 module-owned outbox architecture, a cross-module FK, or migration-branch policy changes accepted architecture.

No runbook command becomes authoritative while it is Planned/TBD or lacks real execution evidence.

## 12. Dependency and license impact

No dependency is approved or may be installed by this Draft.

| Candidate | Purpose | Necessity/alternative | Admission state |
|---|---|---|---|
| SQLAlchemy | engine/session/mapping and production repository adapters | architecture-selected; standard `sqlite3` alone would duplicate UoW/mapping work and diverge from PostgreSQL seam | Candidate/Pending exact version, MIT recheck, full transitive review |
| Alembic | explicit versioned migration chain | architecture-selected; hand-rolled migration history rejected | Candidate/Pending exact version/license/transitives review |
| Python `sqlite3` | SQLite driver, online backup, result codes/integrity where needed | standard library; no package | runtime/SQLite version still pinned and reviewed |
| existing FND test/type/lint/security/license tools | execute/gate DB behavior | selected by PLAN-FND | Pending their admission; no mock plugin |

PLAN-DB proposes no async SQLite driver, PostgreSQL driver, file-lock package, backup framework, ORM extension, migration helper, data generator, fixture loader, SQL logger, encryption package, telemetry client, or cloud SDK.

Admission must record exact upstream/package/version, purpose, current license file, all transitive licenses, maintenance/security/provenance, supported Python/Linux/macOS/SQLite, native/install scripts, network/telemetry, vulnerabilities, performance/size, exact pin/lock/integrity, alternatives, removal/upgrade cost, SBOM/notices, reviewer/date. A headline permissive license is insufficient.

## 13. Risks and unresolved decisions

### 13.1 Risks

| ID | Risk/question | Likelihood/impact | Mitigation/evidence | Owner | Status |
|---|---|---|---|---|---|
| DB-R01 / R-011 | writer contention blocks auth/collection/UI | Medium/Major | WAL/FULL, short immediate writes, bounded pool/busy, real concurrency/load | DB/module owners | Open |
| DB-R02 / R-011 | corruption or unsafe shutdown loses data | Medium/Critical | durability policy, integrity, verified snapshots/restore | DB/M08/DEP | Open |
| DB-R03 / R-012 | SQLite details leak into module ports | Medium/Major | adapter-only PRAGMA/error/rowid/file semantics and portability review | architecture/DB | Open |
| DB-R04 | shared migration head blocks parallel work | High/Major | fixed allocation, one steward, serialized revision integration | integration | Open |
| DB-R05 | partially transactional SQLite DDL leaves ambiguous state | Medium/Critical | one-step stop, schema validation, backup recovery, no auto retry | DB/M08 | Open |
| DB-R06 | exact decimal/money representation overflows or rounds | Medium/Critical | bounded coefficient/scale, no float, real provider round trip | M05/DB | Open |
| DB-R07 | generic repository erases module ownership | Medium/Critical | producer-owned ports and per-module paths; no cross joins | architecture | Open |
| DB-R08 / R-020 | snapshot exists but is corrupt/unrestorable | Medium/Critical | online backup/full integrity/real activation/startup | DB/M08 | Open |
| DB-R09 / R-020 | restore resurrects credentials | Medium/Critical | isolated production M01 invalidation before activation | M01/M08/DB | Open |
| DB-R10 / R-005 | SQL/binds/path/rows leak in diagnostics | Medium/Critical | allowlisted errors/logs/scans | security/DB | Open |
| DB-R11 | migration checksum/catalog creates false assurance | Medium/Major | independent schema/invariant checks and immutable review | integration/test | Open |
| DB-R12 | test policy prevents real prior-data migration evidence | High/Major | production-created prior DB/private sanitized copy; visible Blocked | owner/test | Accepted constraint |
| DB-R13 | WAL/checkpoint grows under readers/history | Medium/Major | bounded reads, monitoring, measured checkpoint policy | DB/P01/M08 | Open |
| DB-R14 / R-023 | macOS lock/fsync/rename differs | Medium/Major | platform port and real macOS result | A04-MAC | Open |
| DB-R15 / R-018 | ORM/migration dependency risk | Medium/Critical | exact admission/locks/SBOM/notices/security review | dependency owner | Open |
| DB-R16 | file activation semantics prevent future PostgreSQL | Medium/Major | CTR-DB-003 physical adapter seam; future ADR | architecture | Monitoring |
| DB-R17 | disk-full test or recovery damages owner data | Low/Critical | isolated exact target, explicit packet/authority, no broad cleanup | owner/security | Open |

### 13.2 Approval-blocking synchronization decisions

1. Approve synchronous SQLAlchemy/standard SQLite driver rather than an async driver.
2. Approve the exact SQLite runtime/version floor and required `trusted_schema`/backup/result-code capabilities.
3. Approve WAL, FULL synchronous, 5000 ms busy timeout, 1000-page auto-checkpoint, and no permissive fallback.
4. Approve bounded pool defaults/ranges and `BEGIN IMMEDIATE` write UoW behavior with FND/P01/background task execution model.
5. Freeze CTR-DB-001 states, schema range, startup/maintenance disclosure, catalog/checksum semantics, and minimal liveness behavior.
6. Freeze producer-owned repository/UoW port names/versions for M01–M08 and the exact adapter paths in section 1.5.
7. Freeze technical error mapping and which constraint identities may cross into module adapters safely.
8. Freeze opaque ID, timestamp, duration, exact decimal/ratio/money, boolean/enum/digest/canonical payload representations and bounds.
9. Approve `catalog.toml`, exact V1 revision allocation/parent chain, metadata/checksum/status workflow, and no merge-head policy.
10. Approve every table/revision row with the owning module and approve CTR-EVT-TOPOLOGY-001 port/schema details without reopening central-versus-module ownership.
11. Decide whether any PLAN-DB technical table is needed; default is none beyond Alembic metadata.
12. Approve migration lock representation/recovery, platform lock contract, and quiescence proof.
13. Freeze AUTO-MIGRATE backup precondition, initial-empty exception, per-revision validation, module consistency, restricted start, and failure recovery.
14. Freeze supported prior schema range and required real production-created upgrade evidence per release.
15. Add and approve CTR-DB-003 fields, operations, deadlines, idempotency, authority, snapshot/integrity/staging/activation/rollback semantics.
16. Freeze M08/DEP/A04 responsibility split, external restore journal, same-filesystem atomic activation, current preservation, rollback, and cleanup.
17. Approve startup/full integrity cadence, WAL/checkpoint health policy, and performance budgets.
18. Approve configuration names/defaults/ranges, installed-path derivation, privacy/disclosure, and macOS mapping.
19. Complete exact dependency/license/security/maintenance/transitive admission and lock/SBOM/notices strategy.
20. Approve every destructive isolated test packet and owner checkpoint for corruption/permission/disk/migration/activation failures.
21. Decide whether CTR-DB-003 activation, migration checksum catalog, or any departure from CTR-EVT-TOPOLOGY-001 requires a new ADR.
22. Allocate canonical automation wrapper/command-registry ownership and real tests; absent commands keep dependent phases Not Ready.

No unresolved item may be selected privately by a DB or module implementation agent when alternatives materially affect data, compatibility, security, recovery, or tests.

### 13.3 Stop and escalation conditions

Stop and return to root synchronization if work would:

- change a module repository/UoW transaction, invariant, table, retention, event, or error meaning;
- introduce a cross-module query/FK/trigger/view, shared ORM entity, generic repository, or another module's import;
- create an unallocated revision, competing head, mixed-owner migration, or modify a shared revision/checksum;
- create/migrate schema during normal startup or bypass AUTO-MIGRATE/backup/quiescence;
- store/use binary float for exact values or reinterpret Unknown/NULL/zero;
- require arbitrary JSON/provider payload/content/environment/credential/path persistence;
- leak ORM/session/SQLite/file semantics through a domain/M08/API contract;
- use `:memory:`, fake repository, mock/stub/emulator/replay, seeded business row/telemetry, backdated row, patched clock, or test-only migration path;
- add/install a dependency before admission;
- run a destructive/permission/corruption/disk/migration/restore test outside an exact isolated approved target;
- copy a live SQLite file/WAL/SHM rather than use CTR-DB-003;
- activate without quiescence, full validations, M01 invalidation, current preservation, or owner authority;
- delete/overwrite/repair the only current/failed/corrupt database or unknown file;
- touch provider state, credentials, `.env`, a default profile, or a monitored agent;
- expose a secret/content/raw row/SQL/path in output/evidence;
- overlap another agent's migration/catalog/core/module-adapter file ownership.

## 14. Delivery and rollback

### 14.1 Delivery order

1. Synchronize sections 4/5/13 with FND, M01–M08, DEP, A04, P01, security, test, and dependency owners.
2. Approve the already registered, Draft-aligned CTR-DB-003 exact fields,
   paths, settings, representations, migration matrix, dependencies, and test
   packets; implementation and live evidence remain pending.
3. Implement DB-I01..I03 using real file SQLite and R/G/R before any business table revision.
4. Deliver M01/M02 repository adapters and migrations in the fixed chain.
5. Deliver M03–M08 adapters independently by module path while the migration steward serializes revisions.
6. Integrate AUTO-MIGRATE and exercise fresh/upgrade/failure/recovery.
7. Integrate M08 online snapshot/integrity and AUTO-BACKUP.
8. Integrate DEP/A04/M08 staging/activation/rollback and owner-exercise AUTO-RESTORE.
9. Measure real concurrency/query/WAL behavior, complete portability/security/license/docs reviews, and feed actual statuses to release integration.

### 14.2 Compatibility and exposure

- `sqlite-persistence.v1` supports only approved repository-port majors and the declared schema range.
- Additive nullable columns/tables may be compatible when old binaries safely ignore them. Unit/time/null/state/ID/exact-value/transaction/constraint reinterpretation is breaking.
- Old and new binaries never run concurrently unless the schema range and lease/event contracts explicitly support it.
- Normal service remains disabled until schema, policy, integrity, and required module consistency are compatible.
- Database health/backup UI exposure follows M08/P01 authorization and never reveals paths/SQL/rows.

### 14.3 Rollback and recovery

- Prefer forward-fix after a shared additive migration.
- Use a real tested downgrade only when cataloged safe for real data.
- Otherwise quiesce, preserve failed/current database, activate the verified pre-migration backup through CTR-DB-003, and use the compatible prior binary.
- Never rewrite migration history, delete history, drop/recreate owner tables, or hand-edit `alembic_version` as rollback.
- Manifest/lock changes roll back together; partial dependency rollback is prohibited.
- Failed snapshot/activation/migration artifacts remain isolated and unavailable until reviewed; exact cleanup is owner-approved and recoverable where possible.

### 14.4 Post-deployment checks

- installed path/owner/mode/file identity safe;
- SQLite/runtime/dependency/catalog versions approved;
- effective PRAGMAs exactly match policy;
- schema head/range/checksums/ownership/integrity compatible;
- normal startup performed no DDL;
- module repository/UoW health and required consistency checks pass;
- pool/busy/WAL/checkpoint health within measured budgets;
- newest M08 backup uses a valid online snapshot and real restore evidence is current;
- AUTO-MIGRATE/BACKUP/RESTORE statuses reflect actual boundaries and show every Blocked/Not Run item;
- logs, DB/WAL, snapshots, diagnostics, evidence, and build artifacts pass prohibited-data/secret scans;
- no provider profile, running agent, unrelated file, or external resource changed.

### 14.5 Implementation handoff packet

Every PLAN-DB/module-adapter handoff states:

- exact requirement/AC and test IDs;
- PLAN-DB, CTR-DB, producer-port, schema/catalog/revision, and SQLite/dependency versions;
- files, table prefixes, revision IDs/parents/checksums, configuration, and command entries changed;
- Red/Green/refactor canonical commands/results/timestamps and actual boundary;
- real file/migration/concurrency/filesystem/snapshot/activation/platform results;
- every Failed/Blocked/Not Run row, especially prior-data/macOS/disk/recovery;
- schema/API/event/config compatibility and PostgreSQL portability impact;
- security/privacy/secret/content/path/permission review;
- dependency/license/lock/SBOM/notices impact;
- backup/recovery evidence and rollback position;
- documentation/traceability/risk changes and exact next shared-head/integration step.

## 15. Definition of ready

- [ ] Owner approves outcomes, non-goals, durability/recovery posture, and limitations.
- [ ] Root approves this exact plan/version and changes Status to Approved.
- [ ] Canonical synchronized planning gate includes PLAN-DB and passes against the real checkout.
- [ ] PLAN-DB core, each module adapter, migration/catalog, automation, composition, and documentation path has one conflict-free owner.
- [ ] CTR-DB-001/002/003 schemas, errors, authority, idempotency, compatibility, and consumer reviews are Approved.
- [ ] M01–M08 producer-owned repository/UoW ports and transaction meanings are Approved.
- [ ] FND engine/config/log/build/evidence/migration-metadata contracts are Approved.
- [ ] DEP/A04/M08 quiescence/path/lock/fsync/snapshot/journal/activation/recovery contracts are Approved.
- [ ] Exact SQLite/Python/SQLAlchemy/Alembic versions and every direct/transitive license/security/provenance/lock/SBOM/notices item are approved.
- [ ] Exact PRAGMA, pool, timeout, transaction, error, and type representation decisions are approved.
- [ ] Migration catalog, full V1 revision chain, outbox ownership, backup prerequisites, validators, compatibility range, downgrade/recovery, and checksum workflow are approved.
- [ ] Configuration names/defaults/ranges/path derivation/reload/privacy behavior are registered.
- [ ] Each scenario has a meaningful expected Red, correct real boundary, safe isolated target/cleanup/evidence path, and assigned owner.
- [ ] Real Linux/SQLite/filesystem/service resources are available; macOS/prior-data/natural failure states are preclassified truthfully.
- [ ] Destructive isolated test packets and owner checkpoints are explicitly approved.
- [ ] Canonical AUTO-MIGRATE and first-increment AUTO-TEST/QUALITY/DOCS selectors exist and are real-tested before their dependent handoff; later absent commands keep later phases Not Ready.
- [ ] Threat/privacy/prohibited-field/path/permission/log/artifact reviews resolve or explicitly accept every Critical risk.
- [ ] Backup/restore/activation/rollback and post-restore M01/module validation are reviewed.
- [ ] PostgreSQL portability report has an explicit mapping/limitation for every nonportable mechanism.
- [ ] Required documentation, evidence custody, traceability, risk, release, and handoff outputs are assigned.
- [ ] Any required ADR is Accepted.
- [ ] No unresolved section 13.2 item permits materially different implementation.

Until every applicable item is checked, PLAN-DB is **Not Ready for implementation**.

## 16. Approval record

| Reviewer/owner | Decision | Conditions/evidence | Date | Approved versions |
|---|---|---|---|---|
| Pavlo Sidelov / product owner | Pending | durability, backup/restore, authority, limitation decisions | — | — |
| Root/integration steward | Pending | paths, contracts, chain/catalog, parallel ownership, automation | — | — |
| PLAN-FND owner | Pending | engine/Alembic/config/log/build/evidence/tooling seams | — | — |
| M01–M08 owners | Pending | repository/UoW ports, DDL/transactions/validators/retention | — | — |
| M08 operations owner | Pending | CTR-DB-003, backup/restore/migration orchestration | — | — |
| PLAN-DEP/A04 owners | Pending | paths/permissions/lock/fsync/quiescence/activation/platform evidence | — | — |
| P01/composition owner | Pending | startup/readiness/health exposure and transaction execution model | — | — |
| Security/privacy reviewer | Pending | paths, permissions, errors/logs, schema fields, backups, activation | — | — |
| Test-integrity reviewer | Pending | real file/data/migration/concurrency/failure evidence; no doubles | — | — |
| Dependency/license reviewer | Pending | exact runtime/packages/transitives/locks/SBOM/notices | — | — |
| Release/recovery reviewer | Pending | compatibility range, upgrade, downgrade, backup/restore/rollback | — | — |

Approval authorizes only a later explicit implementation task packet. It does not authorize dependency installation, database creation/migration, backup, restore, service/deployment action, destructive testing, `.env` changes, provider access, Git/GitLab mutation, or work against owner data.
