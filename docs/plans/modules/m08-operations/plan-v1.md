# Module plan: M08 — Operations

- Status: **Draft — contract synchronization and approval pending; implementation is not authorized**
- Plan version: `0.2.0-draft`
- Proposed module contract bundle: `operations.v1`
- Contract-register baseline: `0.2.0` Draft-aligned (`CTR-OPS-001` through `CTR-OPS-007` and `CTR-APP-001`); not synchronized or approved
- Primary owner: M08 operations implementation role (unassigned)
- Required reviewers: owner, root/integration steward, M01–M07 owners, PLAN-FND, PLAN-DB, PLAN-DEP, A04 platform, P01 API, P02 UI, persistence/migration, security/privacy, test-integrity, dependency/license, and release owners
- Primary requirements: FR-OPS-002..006; operations-owned FR-HIST-003/004
- Supporting requirements: FR-HIST-001/005, FR-OPS-001, FR-SAFE-001/002, NFR-ARCH-001/002, NFR-API-001/002, NFR-DATA-001, NFR-TEST-001/002, NFR-SEC-001, NFR-PRIV-001/002, NFR-DOC-001, NFR-LIC-001, NFR-PLAT-001, NFR-PERF-001, NFR-RES-001, NFR-OBS-001, NFR-COMP-001
- Acceptance contribution: AC-V1-001..008, AC-UI-002/005/006, AC-HIST-002, AC-OPS-001..005, AC-TEST-001..006
- Primary project risks: R-005, R-009, R-011, R-012, R-013, R-018, R-019, R-020, R-023
- Dependencies: accepted ADRs 0001, 0003, 0004, 0006, 0007, 0008, 0010, and 0011; approved foundation/configuration/build/evidence contracts; synchronized component-health/query/retention/export contracts; PLAN-DB snapshot/integrity/activation contracts; PLAN-DEP maintenance/service contracts; M01 authorization and restore invalidation
- Target milestone: M4 operations foundation, integrated and live exercised through M7
- Approved by/date: pending

This plan is governed by the [product requirements](../../../product/requirements.md), [V1 acceptance criteria](../../../product/v1-acceptance-criteria.md), [module boundaries](../../../architecture/modules.md), [contracts and versioning](../../../architecture/contracts-and-versioning.md), [data model](../../../architecture/data-model.md), [deployment architecture](../../../architecture/deployment.md), [security architecture](../../../architecture/security.md), [API standards](../../../api/api-standards.md), [testing strategy](../../../engineering/testing-strategy.md), [SDLC](../../../engineering/sdlc.md), [completion and automation gates](../../../engineering/completion-and-automation-gates.md), [operations runbook](../../../operations/runbook.md), [foundation plan](../../foundation/plan-v1.md), and [contract register](../../contract-register.md).

All schemas, paths, configuration names, schedules, and commands below are proposals for synchronization. They are not implemented commands, test evidence, or authorization to operate on the owner's database.

## CS-1 Draft-alignment addendum

M4 focused synchronization, 2026-09-29: the separately approved
[operations increment](../../integration/m4-operations-change.md) consumes
`CTR-FND-002` through its immutable in-process lifecycle snapshot query for
liveness. It imports the published contract, never a foundation runtime object
or resource handle. This focused authority does not approve this whole Draft.

This `0.2.0-draft` revision adopts contract-baseline `0.2.0` and the parallel-ownership manifest as its concrete CS-1 review position. It remains Draft; no operational command exists, every scenario is `Not Run`, and backup, restore, migration, service, or data authority is absent.

- M08 is the sole semantic producer of CTR-OPS-001..007 and CTR-APP-001. CTR-OPS-007 defines the common retention preview/purge, export-record query, and post-restore consistency participant protocol; M01–M07 implement their own semantics and table transactions. CTR-APP-001 is a bounded read-only dashboard overview fan-in over published query ports; it creates no new domain truth, cross-module transaction, or client-side join.
- M08 alone owns application-maintenance intent/state and restore workflow authority. PLAN-DEP alone executes fenced service quiescence, restricted/normal start, artifact/unit activation and rollback and returns CTR-DEP-001 receipts. PLAN-DB alone prepares/activates/rolls back a database and returns CTR-DB-003 receipts. M08 never invokes service-manager commands directly or activates a database.
- Restore order is fixed and acyclic: M08 maintenance intent -> DEP quiescence receipt -> PLAN-DB prepared staging target -> every required CTR-OPS-007 staged-consistency receipt including M01 credential invalidation -> PLAN-DB activation receipt -> DEP restricted-start receipt -> CTR-OPS-007 post-activation consistency receipts -> M08 validation/workflow receipt -> DEP normal-start/resume. Each rollback target/receipt remains typed by its owner.
- M08 readiness consumes only narrow non-composite DEP service facts plus bounded CTR-OPS-006 leaf health results. DEP may consume M08 readiness for composite display/verification, but M08 never consumes that composite. Liveness uses no database/provider/filesystem/network dependency and is cycle-free.
- All M08 field availability uses CTR-COMMON-007. M08 event producers and consumers use CTR-COMMON-006 plus CTR-EVT-001 atomic outbox, receipt/checkpoint, replay, ordering, poison/backlog, and retention semantics. Health timeout or consumer failure never rolls back another module's business commit.
- M08 adopts CTR-EVT-TOPOLOGY-001: it owns `ops_event_outbox` plus any M08 consumer receipt/checkpoint rows under `ops_*`. PLAN-DB's dispatcher reaches those rows only through published M08 event-storage ports; no central event table or cross-module SQL is allowed.
- The V1 public contracts are `backend/src/agentmonitor/contracts/operations_v1.py` and the producer-owned application projection declaration for CTR-APP-001; SQLite implementation files are only under `backend/src/agentmonitor/adapters/persistence/operations/sqlite/**`. M08 owns `ops_*` tables and `v1_0800..v1_0899`; PLAN-DB serializes the migration head.
- Alignment is verified by existing scenarios M08-PURE-001..016, M08-DB-001..015, M08-FS-001..014, M08-LIFE-001..014, and M08-ARCH-001..004. Only defined IDs may be cited; every applicable scenario remains `Not Run`.

## 0. Authority, evidence state, and completion boundary

The current authority is planning only. This plan authorizes no production code, dependency installation, migration, `.env` change, service action, backup, restore, retention deletion, export, diagnostic collection, Git/GitLab mutation, or live test.

At planning time:

- every M08 scenario is `Not Run`;
- CTR-OPS-001..007 and CTR-APP-001 are Draft-aligned proposals; producer/consumer synchronization and owner approval have not completed;
- PLAN-DB and PLAN-DEP do not yet have approved contracts, so physical database and native-service operations remain approval blockers;
- a written backup/restore flow is not proof that a backup can restore;
- a generated artifact is not safe until its real allowlist and secret/content scan pass;
- the complete daily/weekly/monthly rotation horizon and 365-day deletion boundary cannot be accelerated with patched clocks, backdated rows, or test-only settings; unavailable natural-time evidence remains Blocked;
- no gate may report M08, recovery readiness, or V1 complete while its canonical executable command is absent, red, skipped, or narrower than the claim.

The synchronized planning set is checked only by:

```bash
python3 tools/planning/validate_plans.py --stage synchronized
```

That command is not an M08 behavior test and does not approve this plan. M08 implementation and operational completion require the later fail-closed automation defined in section 8.8.

## 1. Outcome and boundaries

### 1.1 Outcome

M08 gives the owner a truthful operational control plane for AgentMonitor itself. It aggregates safe component health, decides normal-service readiness, exposes version and configuration-presence diagnostics, creates and verifies recoverable SQLite backups, orchestrates explicit restore and post-restore security invalidation, coordinates 365-day export-before-purge workflows through module ports, creates sanitized diagnostic/export artifacts, and records a product audit trail without reading another module's tables.

The outcome is measurable when:

1. Liveness, normal readiness, degraded health, setup-required, and maintenance states are distinct and cannot be inferred from PID existence alone.
2. One timed-out or degraded optional provider component remains visible without taking down unrelated API/dashboard reads.
3. A required database, configuration, IAM, schema, or restore-invalidation failure prevents normal readiness with a stable safe reason.
4. Application, frontend, OpenAPI, generated-client, schema, component, adapter, and policy versions are visible from authoritative version ports and never guessed from filenames.
5. Configuration diagnostics expose only approved non-secret values and secret `configured | missing` state; they never expose a secret value, length, prefix, suffix, digest, or provider credential presence.
6. Automatic and manual backups use the real SQLite-safe snapshot mechanism, pass checksum and full integrity validation, become catalog-visible only after durable finalization, and exclude `.env`, provider profiles, logs, exports, and unrelated files.
7. Backup retention maintains seven UTC daily, four ISO-weekly, and twelve UTC monthly slots, permits one valid backup to satisfy multiple slots, and never deletes the last valid holder of a retained slot.
8. Restore is an explicit offline/maintenance operation that validates the selected backup, restores through an isolated staging database, preserves the current database, validates/migrates the staging copy through approved ports, invalidates restored browser/API credentials, and resumes normal readiness only after every required post-restore check passes.
9. Every 365-day purge uses one fixed UTC cutoff, creates and validates a machine-readable export checkpoint first, calls each module's preview/purge ports idempotently, and exposes partial progress without direct table access.
10. Diagnostic and export artifacts are typed, size-bounded, owner-only, checksum-protected, expiry-controlled, and rejected if the production safety scan cannot complete cleanly.
11. Every privileged operations action and terminal outcome is represented in the M08 audit trail using safe IDs/codes, without free-form content or secrets.
12. Real SQLite, filesystem, loopback HTTP, built browser, native Linux lifecycle, backup, restore, and recovery evidence exists for every claim; missing macOS or natural-horizon evidence remains visibly Blocked.

### 1.2 In scope

- Product-level `HealthViewV1`, `ReadinessViewV1`, and minimal liveness projection.
- Parallel, deadline-bounded aggregation of `ComponentHealthPortV1` producers.
- Required-versus-optional component policy supplied by synchronized deployment/composition metadata.
- Authoritative build, application, frontend, OpenAPI/client, schema, module, adapter, and policy version diagnostics.
- Operator-facing configuration validation and presence diagnostics through the foundation configuration contract.
- Backup scheduling, manual requests, catalog, verification, GFS slot assignment, rotation, reconciliation, and failure visibility.
- Restore selection, preflight, maintenance state, external recovery journal, staging, migration coordination, post-restore validation, M01 credential invalidation, activation, rollback, and audit.
- Operations job state, leases/fencing, idempotency, resumable step journals, and concurrency policy.
- 365-day retention-cycle orchestration across M01–M07 and M08-owned history.
- Export-before-purge and owner-requested operational data exports using module-owned bounded query ports.
- Sanitized diagnostic summary and downloadable diagnostic bundle generation.
- M08-owned product audit events; IAM remains owner of IAM security-audit facts.
- M08-owned tables, repositories, migrations, configuration declarations, documentation, tests, and evidence.
- Behavioral ownership for `AUTO-BACKUP` and `AUTO-RESTORE`, and orchestration ownership shared with PLAN-DB/PLAN-DEP for `AUTO-MIGRATE`.

### 1.3 Out of scope

- Reading or writing another module's tables, ORM models, repositories, migrations, or private files.
- Interpreting provider quota, budget, authentication, runtime, collection, registry, or alert business semantics.
- Provider API/CLI/profile/filesystem access, provider authentication, or provider-account mutation.
- Changing `.env`, copying provider credentials, or bundling provider profiles.
- Silent database repair, `VACUUM`-as-repair, modifying a corrupt source database, or deleting the only copy.
- Starting restore from an ordinary browser or bearer-token request in V1. Restore execution is local maintenance authority only.
- Sending diagnostics automatically, external telemetry, crash reporting, email, desktop notifications, messenger messages, or uploads.
- Reading prompts, responses, tool activity, source code, arbitrary process environment, raw terminal/CLI/provider output, or unrestricted logs.
- Owning public HTTP routing, cookies/CSRF, API-token verification, generated clients, or UI rendering.
- Owning SQLite connection/journal/migration mechanics or native service installation; PLAN-DB and PLAN-DEP provide those ports.
- Killing, restarting, pausing, attaching to, injecting into, switching credentials inside, or routing a monitored agent.
- Remote hosting, multi-user operations, encrypted cloud backup, or automatic self-update.

### 1.4 Ownership

M08 exclusively owns:

- `OperationsHealthProjection`, `OperationsReadinessProjection`, `ComponentHealthSample`, `BackupRecord`, `BackupRetentionSlot`, `OperationsJob`, `OperationsJobStep`, `ArtifactRecord`, `RetentionCycle`, `RetentionParticipant`, `OperationsAuditEvent`, and M08 command-receipt concepts;
- product-level health/readiness aggregation and disclosure policies, not the component's internal health meaning;
- backup validity, catalog, retention-slot assignment, rotation eligibility, and restore workflow state;
- retention/export orchestration state, while each source module owns record eligibility, export schemas, and deletion;
- diagnostic/export bundle envelope, manifest, checksum, expiry, and final safety gate;
- all `ops_*` tables, indexes, repositories, and centrally allocated M08 migration revisions;
- the external restore journal format stored under the approved AgentMonitor state root;
- CTR-OPS-001..007 and CTR-APP-001 schema meanings after synchronization;
- M08 documentation, canonical-routine behavior, test matrix, and evidence handoff.

M08 does not own another module's health calculation, history, consistency rules, migrations, query rows, credentials, runtime logs, or provider facts.

### 1.5 Proposed implementation paths

Allowed after plan/contract approval and root allocation:

```text
backend/src/agentmonitor/modules/operations/**
backend/src/agentmonitor/adapters/persistence/operations/sqlite/**
backend/src/agentmonitor/adapters/operations/**
backend/tests/operations/**
backend/tests/integration/operations/**
docs/modules/operations.md
docs/contracts/operations-v1.md
docs/operations/backup-recovery.md
docs/operations/diagnostics-exports.md
docs/test-evidence/operations/**             # sanitized evidence only, if approved
```

`backend/src/agentmonitor/adapters/operations/**` is a proposed path for platform-neutral checksum/archive/manifest composition. Its use requires architecture approval. Native path resolution, permissions, fsync/atomic-move behavior, service control, and database snapshot/activation remain behind A04/PLAN-DB/PLAN-DEP ports.

Shared paths require explicit single-owner allocation per change:

```text
backend/src/agentmonitor/contracts/operations_v1.py
backend/migrations/versions/<allocated-m08-revision>.py
backend/src/agentmonitor/composition/**
backend/tests/contract/**
tooling/**                                  # canonical automation owner assigned by root
configuration registry
OpenAPI and generated-client sources/output
traceability, risk, automation standard, command registry, runbooks
```

M08 must not edit another module plan/source, PLAN-DB/PLAN-DEP/A04 implementations, P01 routes, P02 features, shared migration head, lockfiles, or generated artifacts without explicit reassignment.

### 1.6 Allowed and forbidden dependencies

M08 domain code may import only the Python standard library, approved common contracts, and M08-owned domain/contracts. M08 application code may consume synchronized health, version, configuration, query, retention, consistency, database, platform, IAM, and deployment ports. Persistence adapters may import the admitted SQLAlchemy/Alembic stack and M08 repository ports.

Platform-neutral artifact adapters may use approved Python standard-library `hashlib`, `json`, `zipfile`, and streaming I/O after architecture review. M08 domain/application code must not import `sqlite3`, SQLAlchemy, Alembic, FastAPI, Starlette, provider SDK/CLI packages, `systemd`, `/proc`, OS service APIs, or another module's implementation.

Forbidden techniques include:

- direct SQL against `iam_*`, `reg_*`, `provider_system_*`, `collection_*`, `capacity_*`, `runtime_*`, or `alert_*` tables;
- introspecting arbitrary Python objects or serializing `__dict__` into diagnostics;
- recursive filesystem collection, unresolved globs, symlink following, or paths outside approved roots;
- shell strings, secret-bearing arguments, broad environment inheritance, or privileged/root execution;
- fake repositories/filesystems/clocks/HTTP services, in-memory SQLite, replayed backups, seeded telemetry, or placeholder dashboard values;
- a test-only retention duration, backdated production row, patched time source, or bypass that makes one year elapse;
- a restore route that can activate a database while the normal service accepts mutations.

## 2. Requirements and traceability

| Requirement/AC | Planned M08 behavior | Contract | Scenario IDs | Evidence gate |
|---|---|---|---|---|
| FR-OPS-002 | Aggregate liveness, readiness, collector/database/component health and expose safe diagnostics | CTR-OPS-001/002/004/006 | M08-PURE-001..004, M08-DB-012, M08-HTTP-001..003, M08-LIFE-001/013 | Pure policy plus real DB/server/service/components |
| FR-OPS-003 | Create real automatic backups and retain seven daily/four weekly/twelve monthly slots with checksum/integrity | CTR-OPS-003 | M08-PURE-005..007, M08-DB-007/008, M08-FS-001..009, M08-LIFE-002 | Pure slot policy plus real SQLite/filesystem/natural schedule |
| FR-OPS-004 | Provide manual backup, explicit restore, validation, preservation, and recovery procedures | CTR-OPS-003 | M08-HTTP-004/005, M08-BROWSER-002, M08-LIFE-003..008 | Real service/database/filesystem and owner checkpoint |
| FR-OPS-005 | Exclude secrets/content from exports, backups, logs, diagnostics, and evidence | CTR-OPS-003..005 | M08-PURE-011/012, M08-FS-004/010..013, M08-HTTP-005/006/009, M08-SEC-001..006 | Real artifacts and production safety scan |
| FR-OPS-006 | Expose authoritative application/schema/adapter/component/frontend/API/client versions | CTR-OPS-001/004 consuming CTR-FND-007/CTR-DB-001/health ports | M08-PURE-014, M08-DB-012, M08-HTTP-003, M08-BROWSER-001 | Real build/schema/component metadata |
| FR-HIST-001/005 | Coordinate 365-day UTC retention while modules preserve their own eligible history | retention coordinator ports | M08-PURE-008, M08-DB-009, M08-LIFE-012 | Pure cutoff; real naturally aged DB remains Blocked until available |
| FR-HIST-003 | Run resumable, auditable, bounded retention cycles without cross-table deletion | retention coordinator ports | M08-PURE-008/009, M08-DB-009/011, M08-LIFE-009/012 | Real production module ports and SQLite |
| FR-HIST-004 | Finalize a safe machine-readable export checkpoint before deletion | CTR-OPS-005 | M08-PURE-012, M08-DB-009/010, M08-FS-011, M08-HTTP-007/008, M08-BROWSER-004 | Real module export ports/artifact/scanner |
| FR-OPS-001; AC-OPS-001 | Supply health/readiness/backup/recovery integration to native service; PLAN-DEP owns install/autostart | CTR-OPS-001/002 and CTR-DEP-001 | M08-LIFE-001/002/009 | Real target Linux service; supporting claim only |
| FR-SAFE-001 | Permit explicit backup/export/diagnostic/retention operations under authorization | CTR-OPS-003..005 | M08-HTTP-004..008, M08-ARCH-001 | Real HTTP/local maintenance surface |
| FR-SAFE-002 | Expose no running-agent process-control, routing, credential switching, or provider mutation | full operations.v1 | M08-ARCH-001..003, M08-SEC-006 | Contract/import/API absence review |
| NFR-ARCH-001/002 | Isolated M08 domain, typed contracts, owned tables, no direct module-table reads | operations.v1 | M08-ARCH-001..004 | Automated import/ownership/SQL review |
| NFR-API-001/002 | P01 maps authorized operation resources under `/api/v1`; P02 uses generated client only | CTR-API-001/CTR-UI-001 consuming CTR-OPS | M08-HTTP-001..010, M08-BROWSER-001..005 | Real server/OpenAPI/client/browser |
| NFR-DATA-001 | Real SQLite catalogs/jobs/audit plus DB-owned snapshot/activate seam preserve portability | CTR-DB-001..003, CTR-OPS-003 | M08-DB-001..015, M08-FS-001..009 | Real file SQLite/migrations/backup/restore |
| NFR-TEST-001/002 | R/G/R, real boundaries, no prohibited doubles or invented operational data | test/evidence contract | all M08 scenarios; M08-TEST-001/002 | Evidence review and repository scan |
| NFR-SEC-001 | Least privilege, root/path/symlink/permission checks, restore confirmation, scanner fail-closed | CTR-OPS-003..005 | M08-FS-005..013, M08-SEC-001..008 | Real filesystem/artifact/authorization review |
| NFR-PRIV-001/002 | Operational metadata only; local artifacts; no automatic upload/analytics | CTR-OPS-004/005 | M08-SEC-001..006, M08-PRIV-001/002 | Schema/artifact/network inspection |
| NFR-DOC-001 | Module/contracts/automation/runbooks/recovery/limitations stay executable and current | documentation outputs | M08-DOC-001..003 | AUTO-DOCS-CHECK and exercised runbooks |
| NFR-LIC-001 | No M08 package/tool before admission; scanner/tool graph reflected in SBOM/notices | dependency record | M08-DEP-001/002 | Locked graph/license/security review |
| NFR-PLAT-001 | Linux backup/filesystem/service behavior verified; core contract remains macOS-capable | CTR-PLAT-001/CTR-DEP-001 | M08-FS-005..009, M08-LIFE-001, M08-MAC-001/002 | Real Linux; real macOS Passed or Blocked |
| NFR-PERF-001 | Health aggregation, backup, export, and purge are bounded/streamed for target scale | job/query contracts | M08-PERF-001..003 | Measured real AgentMonitor-owned data; no provider simulation |
| NFR-RES-001 | Component timeout, failed backup/export/retention, and adapter degradation remain isolated | CTR-OPS-001/002/006 | M08-PURE-002..004, M08-DB-004/009, M08-LIFE-006/013/014 | Real failure isolation |
| NFR-OBS-001 | Structured correlation-aware audit/diagnostics contain safe fields only | CTR-FND-004, CTR-OPS-004 | M08-DB-006, M08-FS-010, M08-SEC-003/004 | Real DB/log/bundle inspection |
| NFR-COMP-001 | DTO/event/config/database/artifact formats are versioned and incompatible states fail closed | CTR-OPS-001..007; CTR-APP-001 | M08-PURE-014, M08-DB-001/002/015, M08-ARCH-004 | Compatibility/migration/artifact gates |
| AC-V1-001/002 | Exact requirements/evidence and an approved M08 plan/contracts are present | plan/traceability | M08-DOC-001/002 | Integration review; plan alone is not approval |
| AC-V1-003 | Operations OpenAPI and generated client validate without hand edits | CTR-API-001/CTR-UI-001 | M08-HTTP-010, M08-BROWSER-001..005 | Running server/generator/build gate |
| AC-V1-004 | Fresh/supported migrations and backup/restore recovery are real-tested | CTR-DB-001..003, CTR-OPS-003 | M08-DB-001/002/015, M08-LIFE-003..009 | Real SQLite and lifecycle |
| AC-V1-005/007/008 | Security/privacy/license review passes; no secret or simulated data claim | security/artifact/test policies | M08-SEC-001..008, M08-TEST-001/002, M08-DEP-001/002 | Independent review/scans |
| AC-V1-006 | Backup/restore/diagnostic/upgrade/operator/developer docs use verified commands | automation/runbooks | M08-DOC-001..003, M08-LIFE-009 | Command registry plus exercise evidence |
| AC-UI-002/005/006 | UI shows real health/versions/backups/jobs and truthful partial/stale/error explanations | CTR-OPS-001..005 | M08-BROWSER-001..005 | Real built browser, backend, database, artifacts |
| AC-HIST-002 | 365-day cutoff and real deletion transaction are verified without changing clock | retention ports | M08-PURE-008, M08-LIFE-012 | Pure calculation; real natural-age deletion required |
| AC-OPS-002 | Browser closure does not stop scheduled collection or automatic backup supervision | CTR-DEP-001/CTR-OPS-003 | M08-LIFE-002 | Real native service/browser closed |
| AC-OPS-003 | One provider/component failure does not interrupt operations/API/UI | CTR-OPS-001/002/006 | M08-LIFE-013/014 | Real failing component/provider path |
| AC-OPS-004 | GFS backup/checksum/integrity/restore/post-start all execute on real database | CTR-OPS-003 | M08-FS-001..009, M08-LIFE-003..008 | Mandatory real target evidence; horizon may remain Blocked |
| AC-OPS-005 | Upgrade and failure-recovery runbooks are exercised | AUTO-MIGRATE/AUTO-RESTORE | M08-LIFE-006..011 | Real isolated failure and target service |
| AC-TEST-001..006 | M08 retains R/G/R, real T1–T7 status, mutation result, and explicit Blocked/Not Run | CTR-FND-008 | all test IDs | Canonical AUTO-TEST/evidence gate |

M08 supports but cannot independently pass native installation, provider isolation, OpenAPI/client, browser, or full release criteria owned by PLAN-DEP, provider owners, P01/P02, and PLAN-INT.

## 3. Domain design

### 3.1 Core identifiers and value objects

- `ComponentKeyV1`: registered stable component key, never an import path or free-form provider value.
- `HealthStateV1`: `healthy | degraded | unavailable | incompatible | maintenance | unknown`.
- `ReadinessStateV1`: `ready | not_ready | setup_required | maintenance | unknown`.
- `ComponentCriticalityV1`: `required_for_liveness | required_for_normal_readiness | optional_degraded`.
- `BackupId`, `RestoreId`, `OperationsJobId`, `ArtifactId`, `RetentionCycleId`, and `AuditEventId`: unrelated opaque IDs.
- `ChecksumV1`: algorithm identifier plus lower-case canonical digest; V1 proposal is SHA-256.
- `IntegrityStateV1`: `not_checked | checking | valid | invalid | unavailable`.
- `ArtifactSafetyStateV1`: `not_scanned | scanning | safe | rejected | scanner_unavailable`.
- `StorageObjectRefV1`: internal opaque reference resolved only by the approved artifact store; never serialized to API/UI/events.
- `RetentionSlotV1`: class plus bucket key; daily uses UTC date, weekly uses ISO week/year in UTC, monthly uses UTC year/month.
- `OperationsActorV1`: `administrator | api_token | system_scheduler | local_operator | migration_orchestrator`, with safe M01 principal ID where applicable.

All instants are timezone-aware UTC. Domain policies receive explicit `as_of`; no domain object reads the system clock. Durations use integer milliseconds/seconds as named. File sizes are nonnegative integer bytes.

### 3.2 Component health and readiness

Every health producer implements CTR-OPS-006 and returns one bounded sample before a supplied deadline. M08 invokes producers concurrently through composition, but concurrency and timeout implementation remain outside the pure domain.

Aggregation rules:

1. Missing, timed-out, incompatible-major, or malformed producer output becomes that component's `unavailable`/`incompatible` sample; it never disappears from the required-component manifest.
2. `required_for_liveness` is reserved for the in-process liveness mechanism. Liveness performs no database, provider, filesystem, or network query.
3. A `required_for_normal_readiness` component in `unavailable`, `incompatible`, `maintenance`, or `unknown` makes normal readiness false.
4. `setup_required` is explicit when M01 is safely uninitialized and bootstrap is the only allowed next operation. It is not `ready` and not a crash.
5. A degraded/blocked provider, collector target, forecast, adapter, or optional platform capability degrades health but does not by itself make the HTTP service or unrelated reads unready.
6. Database schema incompatibility, database integrity failure, invalid security-critical configuration, missing required component registration, active restore/migration activation, or failed post-restore credential invalidation blocks readiness.
7. Backup overdue, retention overdue, disk pressure, outbox lag, or one optional component failure degrades health using approved thresholds; it does not silently become healthy because a last successful value exists.
8. Expired component samples become `unknown` using the producer's `valid_until`; M08 cannot extend freshness.
9. Results are deterministic for the same required-component manifest, samples, and `as_of`.

`HealthViewV1` is a detailed authenticated resource. `ReadinessViewV1` may have a minimal service-manager projection. Exact unauthenticated disclosure is a P01/security synchronization decision.

### 3.3 Version and configuration diagnostics

Version truth comes from `build-metadata.v1`, CTR-DB-001, registered module health samples, M02 installation views, and M03 compatibility summaries. M08 never derives a version from an executable filename, package directory, or user-controlled label.

The version projection distinguishes absent, unknown, unavailable, unverified, compatible, and incompatible. It exposes safe identifiers/hashes only after their disclosure classification is approved. Source revisions never include branch names, usernames, host paths, CI credentials, or dirty-worktree content.

Configuration diagnostics consume the foundation registry/loader result and produce:

- configuration schema version and validation state;
- key owner and approved external key name;
- required/optional and restart/reload semantics;
- for non-secret fields, either an explicitly approved safe effective value/source or a redacted state;
- for AgentMonitor secrets, only `configured | missing`;
- stable validation/deprecation/conflict reason code;
- no provider-owned credential presence claim unless an adapter publishes an approved health state.

M08 never opens `.env`, reads process environment, or asks a secret wrapper for serialization.

### 3.4 Operations job state and concurrency

Long-running work uses a durable state machine:

```text
requested -> queued -> claimed -> running -> verifying -> finalizing -> succeeded
                                          \-> blocked
                                          \-> failed
queued/claimed/running -> cancelled       # only AgentMonitor-owned work
```

`succeeded`, `failed`, `blocked`, and `cancelled` are terminal. A job cannot return to an earlier state. `blocked` identifies missing authority/resource/compatible state and is not a pass.

Each job has a type, canonical request fingerprint, idempotency key where user-triggered, schedule-slot ID where automatic, fencing token, lease owner/expiry, fixed `as_of`, safe progress step, correlation ID, retry disposition, and bounded safe error code. No request body, artifact content, path, or secret is stored.

Concurrency classes:

- at most one `database_maintenance` job (`restore`, incompatible migration activation) globally;
- at most one physical database snapshot at a time;
- bounded export/diagnostic jobs, with a shared artifact-byte reservation ceiling;
- one retention cycle per cutoff; retention cannot purge while restore/migration is active;
- health queries never wait behind long jobs and expose maintenance state;
- automatic requests for the same schedule slot coalesce; user requests use idempotency key plus canonical fingerprint.

A stale worker cannot commit after its fencing lease is lost. Recovery resumes only from a durable verified step; otherwise it safely fails and leaves finalized artifacts/database copies untouched.

### 3.5 Backup creation and validity

A valid backup follows this order:

1. Resolve the approved database and backup roots through CTR-DB/CTR-PLAT without accepting a provider/user path.
2. Check owner-only directory/file permissions, symlink/file type, available space threshold, schema compatibility, active maintenance job, and job lease.
3. Create a unique same-filesystem temporary target under the backup root.
4. Invoke the DB-owned real SQLite online snapshot port. M08 never copies a live database file directly.
5. Close the snapshot, fsync as required by the platform contract, and run the DB-owned full integrity check against the snapshot.
6. Compute the checksum by streaming the finalized bytes, record byte size, and write a safe versioned sidecar manifest through the artifact port.
7. Atomically move data and manifest to immutable backup object names; never overwrite an existing object.
8. Commit `BackupRecord`, applicable retention slots, audit event, and operation terminal state transactionally.
9. Only after a new valid backup exists may retention retire older backups.

A backup is not `valid` if snapshot, close/fsync, full integrity, checksum, manifest, permissions, immutable finalization, or catalog commit failed. A leftover temp is not a backup. A finalized-but-uncataloged pair is an `orphan_candidate` and may be reconciled only after full validation; it is never silently trusted.

Backup content is the SQLite snapshot only. It necessarily contains password/token verification digests and operational account metadata and is therefore sensitive owner data. It excludes `.env`, provider profiles, source trees, logs, exports, diagnostics, caches, and arbitrary application directories.

### 3.6 Backup schedule and GFS rotation

The V1 proposal schedules one automatic backup opportunity per UTC day after an approved configured UTC time. Service startup detects a missing/failed current slot and queues one eligible automatic job; it does not create a retry storm.

For every valid backup, the pure retention policy computes candidate slots:

- `daily/YYYY-MM-DD`: retain the newest valid backup in each of the newest seven distinct UTC dates;
- `weekly/YYYY-Www`: retain the newest valid backup in each of the newest four distinct ISO weeks;
- `monthly/YYYY-MM`: retain the newest valid backup in each of the newest twelve distinct UTC months.

One backup may own daily, weekly, and monthly slots simultaneously. The policy retains the union, not 23 required physical copies. A backup referenced by an active restore, legal/operator hold, current verification job, or retained slot is not eligible for retirement.

Rotation is two phase: mark eligible in the catalog, then atomically move the exact validated regular files into an AgentMonitor-owned retired area. Final unlink occurs only after the approved grace period and a second root/symlink/catalog check. Every transition is audited. A failure leaves the object cataloged and visible; no broad recursive deletion occurs.

The classification policy can be proved with pure constructed UTC instants. Real creation/rotation evidence uses actual elapsed time. Complete seven-day/four-week/twelve-month operational evidence remains Blocked until that horizon naturally exists; time patching/backdating is prohibited.

### 3.7 Restore orchestration and security invalidation

Restore is deliberately not a normal online API mutation. `AUTO-RESTORE` runs a maintenance composition under the normal user with explicit local operator authority and an exact backup ID. It never accepts a free-form database source path.

Restore phases are:

1. **Preflight:** confirm service maintenance/quiescence through CTR-DEP-001, no active writes/collection, backup catalog identity, owner confirmation, target roots, free space, permissions, checksum, manifest, integrity, and schema compatibility.
2. **Journal:** create/fsync a versioned external restore journal under the approved state root. It contains safe IDs/phases/storage references only and is required because the active database may be replaced.
3. **Stage:** restore/copy the immutable backup through the DB snapshot port to a new staging database; never write the backup or current database.
4. **Validate/migrate:** run integrity and schema checks; if the schema is older but supported, invoke the DB-owned migration engine through `AUTO-MIGRATE` against the isolated staging target. Newer/incompatible schemas block.
5. **Staged module validation:** invoke every required CTR-OPS-007 consistency participant against the prepared staging target; no direct table reads and no provider calls.
6. **Invalidate security:** invoke M01's CTR-OPS-007 staging consistency action, including `InvalidateCredentialsAfterRestoreV1(restore_id)`. Every browser session and API token is revoked in staging before activation. Failure blocks activation.
7. **Preserve/activate:** preserve the current database at a unique recovery reference, fsync it, and ask PLAN-DB alone to activate the prepared staged database through CTR-DB-003. M08 records the typed receipt; PLAN-DEP never activates a database.
8. **Start restricted:** ask PLAN-DEP to start restricted validation mode; after its receipt, re-run every required CTR-OPS-007 post-activation check, confirm DB/schema/config/IAM consistency, artifact catalog reconciliation, scheduler paused, and readiness still false.
9. **Complete:** persist the restore audit in the restored database, close the external journal, resume normal service/collectors only after all mandatory checks pass, and require fresh dashboard login/token issuance.

The prior database and failed staging copy are retained until explicit owner disposal under a separate safe cleanup operation. A failure before activation leaves the current database untouched. A failure after activation uses the journal and preserved database for an explicit rollback; no automatic destructive guess is allowed.

Restore never contacts a provider, retries re-authentication, changes a provider profile, or attempts to repair corrupt records.

### 3.8 Retention orchestration

M08 coordinates but does not decide another module's row eligibility.

One retention cycle fixes `as_of`, `cutoff_utc = as_of - 365 * 24 hours`, participating contract versions, and a cycle ID. It proceeds as a resumable saga:

1. query every registered participant's retention health and schema/contract compatibility;
2. call each `PreviewExpired*V1` port with cutoff and bound, obtaining count/range plus deterministic preview digest;
3. stream all selected records through versioned module-owned export ports into a pre-retention export artifact;
4. finalize checksum, allowlist validation, production safety scan, manifest, permissions, and catalog entry;
5. invoke participant purge ports in stable registered order with cutoff, batch bound, preview digest, export checkpoint ID, and operation ID;
6. record per-participant completion cursor/count/audit reference and resume idempotently until no eligible record remains;
7. retain the checkpoint artifact for the approved recovery window, then expire it through the same artifact cleanup controls.

If an export or safety scan fails, no purge begins. If a preview changes, that participant is re-previewed/re-exported or blocked; M08 never weakens a module's reference/current-record invariants. Failure after one participant purges is a visible partial cycle; completed steps are not replayed, and remaining modules resume from durable checkpoints.

The exact automatic retention-export recovery window is an approval decision. Retaining it indefinitely would defeat the one-year policy; deleting it immediately would defeat recovery. The draft proposes seven days, owner-readable and excluded from diagnostic bundles.

### 3.9 Export artifacts

CTR-OPS-005 supports two purposes:

- `owner_requested`: selected authorized operational scopes/time ranges;
- `pre_retention_checkpoint`: the exact set selected before a purge cycle.

The proposed format is `agentmonitor-ndjson-v1` in a ZIP container made from:

- one safe manifest containing artifact/format/schema/contract versions, UTC scope, module list, counts, checksums, and safety result;
- one NDJSON member per source module using that module's versioned `SafeExportRecordV1` family;
- no raw database, WAL, `.env`, provider profile, log, screenshot, browser trace, or arbitrary file.

Records are streamed and bounded; no unbounded in-memory export. M08 validates the declared schema and does not inspect provider meaning. Unknown field/schema major stops the artifact. The download contract never exposes a local path. Owner-requested artifacts have an approved expiry; pre-retention artifacts follow their recovery window.

### 3.10 Diagnostic summary and bundle

The diagnostic summary is a safe view of:

- application/build/frontend/OpenAPI/client/schema/module/adapter versions;
- liveness/readiness/component states and stable reason codes;
- backup/restore/retention/export job status and freshness;
- collector/queue/outbox safe summaries obtained through ports;
- configuration validation and secret-presence booleans;
- bounded recent M08 audit categories/correlation IDs;
- platform/service version/state from approved ports.

It excludes account labels/emails, provider identities, metric/money values, PIDs, project/task/path labels, raw logs, database rows, provider payloads, exception text, SQL, headers/cookies, `.env`, process environments, credentials, prompts/responses/tools/source, and unrestricted extension objects.

A downloadable diagnostic bundle serializes only the typed summary and safe manifests. Raw logs are excluded in V1. Finalization requires allowlist schema validation and the approved production secret/content scanner. Scanner unavailable or any finding produces `rejected` and no downloadable artifact. AgentMonitor never uploads or sends the bundle.

### 3.11 Product audit

M08 owns immutable operational audit facts for:

- manual/automatic backup requested, succeeded, failed, verified, retired, or missing;
- restore requested, confirmed, staged, validated, security-invalidated, activated, completed, failed, or rolled back;
- export/diagnostic requested, finalized, rejected, downloaded, expired, or deleted;
- retention cycle/participant transitions;
- health/readiness/maintenance transitions at bounded coalescing points;
- configuration/schema/version incompatibility observations;
- migration preflight/backup/result coordination.

Fields are event ID/type, UTC times, safe actor kind/ID, safe target type/ID, job/correlation/causation IDs, outcome/reason code, bounded numeric counts, contract version, and aggregate sequence. There is no arbitrary note, path, filename, request body, provider/account label, secret, or raw exception.

M01 remains owner of authentication/authorization audit events. A product audit query may merge bounded M08 and M01 views in application orchestration, but neither module copies or reads the other's table.

## 4. Public contracts

All contracts are Proposed. Every payload is immutable, versioned, bounded, and uses common IDs/time/event conventions.

### 4.1 Contract summary

| Register ID | Proposed name/version | Producer | Consumers | Compatibility promise |
|---|---|---|---|---|
| CTR-OPS-001 | `HealthViewV1` and health-query family | M08 | P01/P02/PLAN-DEP/operator tooling | Overall/component state, freshness, criticality, and disclosure meanings fixed within V1 |
| CTR-OPS-002 | `ReadinessViewV1`, `LivenessViewV1` and readiness-query family | M08 | P01/PLAN-DEP/service manager | Ready/setup/maintenance/blocker semantics fixed; minimal and detailed projections distinct |
| CTR-OPS-003 | `BackupViewV1`, `RestoreJobViewV1`, backup/restore command/query/event family | M08 | P01/P02/local operator/PLAN-DEP/PLAN-DB | Validity, checksum, slot, restore phase, idempotency, and offline authority meanings stable |
| CTR-OPS-004 | `DiagnosticSummaryV1`, `OperationsAuditEventViewV1`, diagnostic/audit family | M08 | P01/P02/operator/support | Strict allowlist and disclosure; additive safe fields only after privacy review |
| CTR-OPS-005 | `ExportJobViewV1`, artifact manifest/download/export family | M08 | P01/P02/retention coordinator | Purpose/format/scope/status/expiry/safety semantics stable; local path never public |
| CTR-OPS-006 | `ComponentHealthPortV1` | M08 | M01–M07/FND/DB/DEP/adapters as implementers; M08 as caller | Fixed bounded shape, deadline, freshness, no side effect; registered indicators only |
| CTR-OPS-007 | `RetentionExportAndConsistencyParticipantV1` | M08 | M01–M07 as implementers; M08 as coordinator | Typed bounded retention preview/purge, export query, and staged/post-restore consistency receipts; module semantics remain with implementer |
| CTR-APP-001 | `DashboardOverviewV1` | M08 | P01/P02 | Bounded read-only fan-in over published query ports; no new truth, table read, or client-side join |

### 4.2 CTR-OPS-001 — health

`ComponentHealthViewV1` fields:

- component key, component version, contract/schema/policy versions as applicable;
- criticality from the deployment manifest;
- state, checked-at, valid-until, last-success time, safe reason codes;
- bounded registered indicators with fixed key/type/unit/privacy classification;
- correlation ID and optional safe evidence reference;
- no path, label, account identity, provider value, raw error, or arbitrary metadata.

`HealthViewV1` fields:

- overall state and generated/expires times;
- application/build/schema/frontend/API/client versions;
- component views ordered by registered component key;
- database, backup, retention, artifact, collector, and disk-pressure safe summaries;
- active maintenance kind and operation ID when authorized;
- incomplete/timed-out producer list by component key;
- stable explanation/remediation codes.

Published ports:

| Port | Input/output | Authorization/preconditions | Outcomes | Side effects/idempotency |
|---|---|---|---|---|
| `GetHealthV1` | projection level + deadline + correlation -> HealthView | detailed requires `read:status`; minimal policy synchronized with P01 | healthy/degraded/unavailable/incomplete | Read-only; never triggers repair/collection |
| `RefreshHealthProjectionV1` | registered manifest + deadline + operation ID -> view | internal scheduler/operator authority | complete/partial/timed out/incompatible | Idempotent per operation ID; calls only read-only health ports |
| `GetVersionInventoryV1` | approved disclosure level -> version inventory | `read:status` or `read:diagnostics` | complete/partial/unavailable | Read-only |

Overall health is not a substitute for readiness. A new indicator key requires registry/privacy review. Changing a state's meaning or component criticality source is breaking.

### 4.3 CTR-OPS-002 — liveness and readiness

`LivenessViewV1` contains only process responsiveness, application version class approved for disclosure, UTC observation time, and correlation ID. It does not query SQLite or reveal component/provider/account state.

`ReadinessViewV1` contains readiness state, generated time, maintenance/setup state, schema/config/IAM/database readiness, required-component results, safe blocker codes, and a retry/recheck hint. It contains no secret presence detail in the minimal projection.

Published ports:

- `GetLivenessV1()`;
- `GetReadinessV1(disclosure_level, deadline)`;
- `EnterOperationsMaintenanceV1(operation_id, kind, expected_state)` for the local deployment/migration/restore coordinator;
- `ExitOperationsMaintenanceV1(operation_id, validation_receipt)` only after mandatory checks;
- `GetMaintenanceStateV1()`.

Maintenance transitions are fenced and audited. An HTTP/bearer caller cannot enter restore/migration maintenance unless PLAN-DEP/P01/security explicitly approve a future transport; V1 local operator orchestration uses an internal authority.

### 4.4 CTR-OPS-003 — backup and restore

`BackupViewV1` contains backup ID, job ID, trigger (`automatic | manual | migration_preflight`), lifecycle, requested/started/completed UTC times, snapshot schema/application compatibility versions, size bytes, checksum algorithm/digest, integrity state/time, retention slot labels, expiry/retired state, verification time, and safe error code. It never exposes a filesystem path or database content.

`RestoreJobViewV1` contains restore/job/backup IDs, phase, maintenance state, schema transition, checksum/integrity/module-validation/security-invalidation/activation states, start/end time, preserved-current reference state (not value), required next action, and safe error code.

Published application ports:

| Port | Input/output | Authorization/preconditions | Outcomes | Idempotency/side effects |
|---|---|---|---|---|
| `RequestManualBackupV1` | actor, idempotency key, correlation -> job/backup summary | `write:backup`; service writable; safe roots/config | accepted/coalesced/blocked/unavailable | Same key+fingerprint returns same job; background snapshot |
| `RunAutomaticBackupCycleV1` | schedule slot ID, as-of -> job summary | internal scheduler | accepted/existing/blocked | One job per schedule slot |
| `Get/ListBackupsV1` | ID or bounded filters/cursor -> view/page | `read:status` plus disclosure decision | not found/invalid cursor/unavailable | Read-only |
| `VerifyBackupV1` | backup ID, operation ID -> updated view | internal/local operator; immutable backup | valid/invalid/missing/blocked | Idempotent for object checksum/generation |
| `ApplyBackupRetentionV1` | policy version, as-of, operation ID -> slot/retirement summary | internal after a new valid backup | applied/no-op/blocked | Pure slot decision plus fenced file transitions |
| `PrepareRestoreV1` | backup ID, restore ID -> preflight view | local maintenance authority; explicit owner checkpoint follows | ready/blocked/invalid/incompatible | Read-only except durable request/audit; no activation |
| `ExecuteRestoreV1` | restore ID + approved local confirmation reference -> RestoreJobView | service quiesced, exclusive lease, approved backup | succeeded/failed/blocked/rollback-required | One fenced workflow per restore ID; destructive activation explicit |
| `GetRestoreJobV1` | restore ID -> view | local operator; optional safe authenticated history view | not found/unavailable | Read-only |

Events under CTR-OPS-003 use `EventEnvelopeV1`: `BackupStateChangedV1` and `RestoreStateChangedV1`. They contain safe IDs/states/versions/reason codes only, are at-least-once, ordered per backup/restore stream, and deduplicated by event ID. V1 has no external delivery subscriber.

### 4.5 CTR-OPS-004 — diagnostics and audit

`ConfigurationDiagnosticItemV1` contains key name, owner, value class (`non_secret | agentmonitor_secret | sensitive_path`), validation/presence state, safe source class, reload rule, version, and safe reason. A secret item has no value-derived property.

`DiagnosticSummaryV1` contains the allowlisted items from section 3.10 plus generated/expiry times, completeness, missing component keys, and safety schema version.

`OperationsAuditEventViewV1` contains only the fields from section 3.11 and deterministic pagination metadata.

Published ports:

- `GetDiagnosticSummaryV1(disclosure_level, deadline)`;
- `RequestDiagnosticBundleV1(actor, idempotency_key, correlation)` returning an artifact job;
- `GetDiagnosticBundleJobV1(job_id)`;
- `ListOperationsAuditEventsV1(filters, cursor, page_size)`;
- `GetProductAuditPageV1(filters, cursor, page_size)`, an orchestration result that merges M08 and M01 views without shared persistence;
- `PurgeExpiredOperationsHistoryV1(cutoff, batch_limit, preview_digest, export_checkpoint_id, operation_id)` for M08-owned eligible records.

Audit filters are bounded by time/type/outcome/actor kind. Free-form search is not provided. Diagnostic bundle creation never attaches raw logs automatically.

### 4.6 CTR-OPS-005 — export jobs and artifacts

`ExportJobViewV1` fields:

- job/artifact IDs, purpose, requested scope/time range/module set;
- format/schema version;
- state (`queued | collecting | validating | scanning | finalizing | available | rejected | expired | failed | blocked`);
- requested/started/completed/expires UTC times;
- record/byte counts, checksum and safety state;
- per-module status/count/cursor with stable safe reason;
- download availability flag, never a local path.

`ExportArtifactManifestV1` contains the safe manifest defined in section 3.9. `SafeExportRecordV1` is a versioned family owned by each source module, not a generic dictionary.

Published ports:

| Port | Input/output | Authorization/preconditions | Outcomes | Idempotency/side effects |
|---|---|---|---|---|
| `RequestOperationalExportV1` | authorized typed scope/time/modules/format + key -> job | proposed `write:exports`; exact M01 scope pending | accepted/coalesced/invalid/blocked | Key+fingerprint returns same job |
| `Get/ListExportJobsV1` | ID or bounded filters/cursor -> view/page | `read:diagnostics` and subject authorization | not found/forbidden/unavailable | Read-only |
| `OpenArtifactDownloadV1` | artifact ID + principal + expected version -> bounded stream handle | artifact available/unexpired/safe; P01 transport owns response | not found/expired/rejected/forbidden | Records audited download; never path disclosure |
| `ExpireArtifactV1` | artifact/version/reason/operation ID -> terminal view | internal scheduler or owner | expired/already terminal/blocked | Idempotent fenced removal |
| `CreateRetentionCheckpointV1` | retention cycle/preview set -> artifact receipt | internal retention authority | available/rejected/blocked | One canonical checkpoint per preview set |

No API caller submits a local output path. P01 streams through the application port with size/time limits and no caching of sensitive downloads.

### 4.7 CTR-OPS-006 — component health producer port

`GetComponentHealthV1(ComponentHealthRequestV1) -> ComponentHealthResultV1` is implemented by each registered component.

Request fields are component key, correlation ID, deadline, disclosure class, and requested registered indicator keys. It carries no secret, provider target, or generic query.

Result fields are exactly the component fields in section 4.2 plus one of:

- `available(sample)`;
- `unavailable(reason_code, checked_at, retry_hint)`;
- `incompatible(contract_major, reason_code)`.

The call is read-only, bounded, and must not trigger provider collection, retention, repair, migration, login, or database mutation except a documented coalesced health timestamp owned by that component. Timeouts/cancellation apply only to AgentMonitor-owned health tasks. Indicator keys and types are registered during composition; arbitrary maps/text are rejected.

### 4.7A CTR-OPS-007 — operations participant protocol

M08 publishes the common request/receipt shapes for bounded retention preview/purge, export-record queries, and staged/post-restore consistency checks. M01–M07 implement their own eligibility, serialization, validation, and table transactions. Requests carry operation/correlation ID, contract version, deadline, bounded scope/cursor and, where applicable, cutoff, preview digest, checkpoint ID, or prepared-database reference. Receipts carry participant version, generation, deterministic digest/counts, next cursor, outcome, and safe reason codes. M08 never receives a repository, SQL connection, ORM row, raw provider payload, or arbitrary record dictionary.

### 4.7B CTR-APP-001 — dashboard overview projection

`GetDashboardOverviewV1` fans in only bounded published query ports for registry, capacity, runtime, alerting, collection, and operations. It returns per-section data plus explicit freshness/completeness/unavailable state using CTR-COMMON-007. It creates no cross-module transaction or derived domain truth; a failed section remains visibly partial and cannot be rendered as zero/healthy. P01 exposes the projection and P02 consumes the generated client.

### 4.8 Consumed contracts and exact degradation behavior

| Owner/contract | Required status/version | M08 use | Failure/degradation |
|---|---|---|---|
| CTR-COMMON-001/002/006/007 | Draft-aligned V1 | IDs, UTC/duration, event envelope, field availability | invalid/incompatible common value blocks affected write/event; absence never becomes zero |
| CTR-EVT-001 | Draft-aligned V1 | durable producer outbox, consumer receipt/checkpoint, replay and retention | incompatible/poison/backlog stays explicit; no in-memory-only delivery |
| CTR-FND-003 / CTR-CONFIG-001 | `proposed_aligned` 1.0.0 | configuration registry/validation/presence | invalid security-critical config blocks readiness; never open `.env` |
| CTR-FND-004 | `proposed_aligned` 1.0.0 | correlation and safe structured logging | invalid field rejected; no object/string fallback |
| CTR-FND-006 | `proposed_aligned` 1.0.0 | migration ownership/backup prerequisite metadata | missing requirement blocks AUTO-MIGRATE |
| CTR-FND-007 | `proposed_aligned` 1.0.0 | application/frontend/OpenAPI/client/runtime version inventory | absent required build metadata degrades or blocks readiness by policy |
| CTR-FND-008 | `proposed_aligned` 1.0.0 | executable evidence status | Blocked/Not Run never collapsed into Passed |
| CTR-IAM-001/002 | `proposed_aligned` 1.0.0 | permissions/actors for health, backup, export, diagnostics | deny/fail closed if authorization unavailable |
| CTR-IAM-008 | `proposed_aligned` 1.0.0 | IAM health/audit/purge/post-restore invalidation | restore cannot become ready until invalidation succeeds |
| CTR-REG-001/002/005 | mixed: CTR-REG-001 `proposed_aligned`; CTR-REG-002/005 `evidence_blocked` (1.0.0) | authorized export scopes and registry scope snapshots | unresolved scope blocks export; no guessed membership |
| CTR-REG-004 | `evidence_blocked` 1.0.0 | safe provider installation/version inventory | unavailable provider registry becomes partial diagnostics |
| CTR-REG-007 | `proposed_aligned` 1.0.0 | registry change audit refs where needed | stale change stream degrades only dependent summaries |
| CTR-OPS-006 via M02 `GetRegistryHealthV1` | `proposed_aligned` 1.0.0 | component health | unavailable registry makes registry mutations/not normal-ready per manifest |
| CTR-OPS-007 registry implementation | Draft-aligned V1 | safe export, retention, and post-restore validation | no direct table fallback; participant failure blocks affected workflow |
| CTR-PROV-002/005 and M03 compatibility query | `evidence_blocked` 1.0.0 | capability/adapter/discovery/version summaries | missing M0 remains Unknown/partial, not healthy/unsupported by guess |
| CTR-COL-002/005 | `proposed_aligned` 1.0.0 | collection run and collector health summaries | one target degraded does not fail global readiness |
| CTR-OPS-007 collection implementation | Draft-aligned V1 | retention/export/restore checks | affected participant blocked; no collection table reads |
| CTR-CAP-003/006/007 | `evidence_blocked` 1.0.0 | safe capacity health/history export and retention | numeric provider values excluded from diagnostics; export uses authorized port |
| CTR-OPS-007 capacity implementation | Draft-aligned V1 | capacity retention/export/post-restore validation | failure blocks restore readiness |
| CTR-RUN-001/002 and CTR-OPS-007 runtime implementation | Draft-aligned V1 | safe runtime export/retention/restore validation | prohibited content/path fields remain excluded |
| CTR-ALERT-002/005 and CTR-OPS-007 alert implementation | Draft-aligned V1 | alert diagnostics/export/retention/restore | no direct alert table access |
| CTR-DB-001 `SchemaCompatibilityV1` | `proposed_aligned` 1.0.0 | startup/readiness/backup/restore/migration range | newer/incompatible schema blocks writes/activation |
| CTR-DB-002 | `proposed_aligned` 1.0.0 | M08 repositories/UoW only | typed unavailable/conflict/corrupt; no generic cross-module repository |
| CTR-DB-003 `DatabaseSnapshotAndActivationPortV1` | Registered Draft-aligned; PLAN-DB-owned; approval and real evidence pending | online snapshot, integrity, staging, activate/rollback | backup/restore/AUTO-MIGRATE remain blocked until approval/evidence; no file-copy workaround |
| CTR-PLAT-001 | `evidence_blocked` 1.0.0 | approved roots, regular-file/symlink/permission/fsync/atomic operations, disk capacity | unsafe/unsupported platform blocks write, not bypassed |
| CTR-DEP-001 | `proposed_aligned` 1.0.0 | service quiesce/maintenance/start/status and required-component manifest | restore/deploy readiness blocked when unavailable |

P01 consumes M08's published operations ports and maps them through
CTR-API-001..003. M08 does not consume API contracts.

Every consumed module remains producer of its semantics. M08 may aggregate status and orchestrate public ports; it may not reinterpret a provider fact or inspect persistence to compensate for an absent port.

### 4.9 Required producer-port synchronization packet

Before approval, each M01–M07 producer must implement M08-owned CTR-OPS-007 by publishing:

1. one CTR-OPS-006 health implementation with safe states, freshness, versions, reason codes, and indicator registration;
2. one bounded consistency validation port for restore/upgrade readiness;
3. one preview/purge pair if it owns 365-day history, with cutoff, batch, preview digest, idempotency, protected-record rules, and audit reference;
4. one versioned export-record query if its retained operational data participates in FR-HIST-004;
5. explicit authorization and failure behavior;
6. proof no secret/content/raw provider data enters these outputs.

Missing participant implementations block the affected operation; they are not permission for M08 to query tables.

### 4.10 Event and job contracts

M08 publishes `OperationsJobStateChangedV1`, `BackupStateChangedV1`, `RestoreStateChangedV1`, `RetentionCycleStateChangedV1`, and `ArtifactStateChangedV1` under the applicable CTR-OPS family. All use `EventEnvelopeV1`, at-least-once delivery, aggregate-local sequence ordering, event-ID deduplication, and additive unknown-tolerant safe reason codes.

Events contain IDs, state transition, timestamps, version/checksum/integrity/safety categories where applicable, bounded counts, and correlation/causation. They never contain filesystem paths, artifact contents, configuration values, secret-presence details, account/provider labels, database rows, or exception text.

### 4.11 Safe error vocabulary

Stable proposed codes include:

- health/readiness: `operations_component_timeout`, `operations_component_unavailable`, `operations_component_incompatible`, `operations_required_component_missing`, `operations_setup_required`, `operations_maintenance_active`, `operations_readiness_unknown`;
- configuration/version: `operations_configuration_invalid`, `operations_secret_missing`, `operations_version_unknown`, `operations_version_mismatch`, `operations_schema_incompatible`;
- job/concurrency: `operations_job_not_found`, `operations_job_conflict`, `operations_idempotency_conflict`, `operations_lease_lost`, `operations_job_already_active`, `operations_service_stopping`;
- backup: `operations_backup_root_unsafe`, `operations_backup_space_insufficient`, `operations_backup_snapshot_failed`, `operations_backup_integrity_invalid`, `operations_backup_checksum_mismatch`, `operations_backup_manifest_invalid`, `operations_backup_missing`, `operations_backup_rotation_blocked`;
- restore: `operations_restore_confirmation_required`, `operations_restore_service_not_quiesced`, `operations_restore_backup_invalid`, `operations_restore_schema_unsupported`, `operations_restore_module_validation_failed`, `operations_restore_security_invalidation_failed`, `operations_restore_activation_failed`, `operations_restore_rollback_required`;
- export/diagnostic: `operations_export_scope_invalid`, `operations_export_contract_incompatible`, `operations_artifact_too_large`, `operations_artifact_scanner_unavailable`, `operations_artifact_rejected`, `operations_artifact_expired`, `operations_artifact_unavailable`;
- retention: `operations_retention_preview_changed`, `operations_retention_export_required`, `operations_retention_participant_blocked`, `operations_retention_partial`;
- infrastructure: `operations_repository_unavailable`, `operations_filesystem_denied`, `operations_path_escape`, `operations_symlink_rejected`, `operations_internal_error`.

Errors contain stable code, correlation/job ID, safe target ID if authorized, and remediation category. They never contain path, SQL, artifact content, checksum input, secret/config value, raw exception argument, or provider/module payload.

### 4.12 Contract-impact assessment

This plan proposes the first detailed CTR-OPS-001..007 and CTR-APP-001 contracts and changes no implemented behavior. Synchronization must:

1. freeze detailed versus minimal health/readiness disclosure and P01 authentication policy;
2. freeze required-component manifest ownership and readiness criticality;
3. approve each module's CTR-OPS-006 health schema and indicator allowlist;
4. freeze CTR-OPS-007 and approve M01–M07 participant implementations;
5. approve and freeze the registered Draft-aligned, PLAN-DB-owned CTR-DB-003 database snapshot/integrity/staging/activation/rollback semantics and obtain real implementation evidence;
6. define CTR-DEP-001 quiesce/maintenance/start/status and restore-journal recovery semantics;
7. freeze backup manifest/checksum/integrity/GFS schedule/retirement behavior;
8. freeze M01 post-restore session/API-token invalidation and owner re-login behavior;
9. freeze artifact formats, scan dependency, download authorization, expiry, and audit;
10. freeze shared event/outbox/receipt and automation ownership;
11. update the central contract register and producer plans;
12. create an ADR if database activation, external restore journal, artifact storage, or audit aggregation departs from accepted architecture.

## 5. Data and persistence

### 5.1 Owned tables

Names are proposed and require PLAN-DB review and central revision allocation.

#### `ops_operation_job`

- job ID/type, trigger, lifecycle, canonical request fingerprint, idempotency-key digest or schedule-slot ID;
- requested/started/completed times, fixed `as_of`, actor kind/safe ID, correlation/causation IDs;
- fencing token, lease owner/expiry, progress step, retry disposition, safe result/error code;
- record version and created/updated times;
- no request body, path, secret, artifact content, or free-form error.

#### `ops_operation_job_step`

- job ID, monotonic step ordinal, step type/state, started/completed times;
- safe receipt/reference IDs, bounded counts, contract version, safe reason;
- uniqueness on job plus step/attempt/fencing generation.

#### `ops_backup`

- backup ID/job ID, private storage-object reference, immutable object generation;
- trigger, state, created/completed/verified/retired/deleted times;
- application/schema compatibility/build/manifest versions;
- size bytes, checksum algorithm/digest, integrity state/time;
- hold/reference state, safe error code, record version;
- storage reference is never exposed outside the artifact adapter.

#### `ops_backup_retention_slot`

- slot class (`daily | weekly | monthly`), bucket key, policy version;
- backup ID, assigned/replaced times, active state;
- unique active slot per class/bucket and within-module FK to backup.

#### `ops_artifact`

- artifact/job ID, kind (`operational_export | retention_checkpoint | diagnostic_bundle`), format/schema version;
- private storage-object reference/generation;
- state, byte/record counts, checksum, safety state/scanner version;
- requested/finalized/expires/downloaded/retired/deleted times;
- authorized scope fingerprint, module-contract manifest fingerprint, safe error code;
- no artifact payload, path, provider identity, or secret.

#### `ops_retention_cycle` and `ops_retention_participant`

- cycle ID, fixed as-of/cutoff, policy version, state, checkpoint artifact ID;
- participant key/contract version, preview digest/count/range, export count/checksum reference;
- purge cursor/count/audit reference, state, safe error, timestamps;
- unique participant per cycle and idempotent progress constraint.

#### `ops_component_health_snapshot`

- snapshot ID, component key, checked/valid-until times, state, criticality, safe reason codes;
- safe registered indicator values, schema/version fingerprint, correlation ID;
- bounded recent snapshots only; no arbitrary JSON. Indicator persistence layout requires DB review.

#### `ops_audit_event`

- immutable audit ID/type, occurred/recorded times, actor kind/safe ID;
- target type/safe ID, job/correlation/causation IDs, outcome/reason, bounded counts;
- event schema version and aggregate sequence;
- no free-form details or payload.

#### `ops_command_receipt` and `ops_event_outbox`

- operation/principal/idempotency digest, canonical request fingerprint, result resource ID/state, expiry;
- no input/output secret or artifact content;
- CTR-EVT-TOPOLOGY-001 fixes `ops_event_outbox` as M08-owned and atomically appended with the producing M08 mutation. Consumer receipt/checkpoint rows are also M08-owned when M08 consumes an event. PLAN-DB supplies reusable persistence mechanics through published ports and owns no shared event table; M08 never writes another module's table.

### 5.2 Keys, constraints, and indexes

- Unique idempotency receipt per principal/operation/key digest; same key with a different fingerprint conflicts.
- Unique automatic job per type/schedule slot; unique active exclusive concurrency class.
- Lease fencing token strictly increases; terminal state cannot reactivate.
- Backup checksum/size/integrity relationships and immutable object generation enforced.
- Unique active daily/weekly/monthly slot; a backup can own multiple slots.
- Artifact available only when checksum present and safety state is `safe`; expired/rejected has no downloadable state.
- Retention participant cannot enter purge before checkpoint artifact is available and preview digest recorded.
- Audit/event sequence nonnegative and immutable.
- UTC timestamp ordering/checks, bounded enums/codes/counts, and nonnegative sizes.
- Indexes on job `(type, state, requested_at)`, lease expiry, backup `(state, completed_at)`, slot `(class, bucket)`, artifact `(state, expires_at)`, retention `(state, cutoff)`, health `(component_key, checked_at)`, audit `(occurred_at, audit_id)` and `(event_type, occurred_at)`.
- Query-plan budgets are verified on real data. Unbounded list/history scans are prohibited.

### 5.3 Transaction and filesystem boundaries

- Job admission, idempotency receipt, audit request event, and initial job state commit atomically.
- Lease claim/fencing is one short transaction; filesystem/database work occurs outside it.
- Backup catalog success transaction occurs only after immutable object/manifest finalization; failure state is separately committed.
- Retention slot replacement and catalog retirement eligibility commit atomically; physical retirement is a fenced follow-up step.
- Artifact catalog becomes `available` only after final checksum/safety/permission validation.
- Retention per-participant progress is committed after that participant's idempotent public operation returns a receipt.
- Restore external journal is fsynced before each irreversible phase because the active database may be replaced.
- No cross-module query occurs while an M08 SQLite write transaction is held.
- Cross-database/filesystem atomicity is modeled as recoverable steps; it is never falsely described as one transaction.

### 5.4 Migration sequence

Proposed expand-only M08 revisions:

1. operations job/step/command/audit foundations;
2. backup catalog and retention slots;
3. artifact/export/diagnostic catalog;
4. retention cycle/participants and health snapshots;
5. outbox integration after common event ownership is approved.

Every revision records M08 owner, requirement/plan IDs, expected rows/bytes, table/index changes, lock/downtime, backup prerequisite, validation, compatibility range, PostgreSQL portability, and recovery. Fresh install and every supported prior revision use a real file-backed SQLite database and real Alembic chain. Startup never creates tables implicitly.

A migration cannot require M08 to back up through tables not yet available. The initial bootstrap/first migration backup policy is synchronized with PLAN-DB/DEP. After owner data exists, any risky migration requires a fresh valid backup. Destructive contraction requires a separate approved change plan/ADR/owner confirmation.

### 5.5 Retention of M08 data

- M08 audit events, terminal job/step history, health snapshots, command receipts needed for audit, and terminal retention history are retained 365 days unless a security review requires longer.
- Active jobs, active backup records, retained slot assignments, available artifacts, active restore journals, unresolved incidents, holds, pending outbox events, and references required for current explanation are protected.
- Expired artifacts and retired backups follow their shorter artifact/retirement policies; catalog audit facts remain for 365 days.
- M08 uses its own preview/export/purge operation for eligible M08 history and includes itself as a retention participant.
- A pure cutoff identifies eligibility. Real deletion needs naturally aged production-created records; until then the T2/T7 row is Blocked, not replaced by backdating.

### 5.6 Backup/restore and catalog reconciliation

The physical database backup includes `ops_*` catalog state but not the external files themselves. Therefore startup/post-restore reconciliation compares the catalog to exact approved-root object/manifest pairs:

- cataloged object present and matching remains valid;
- cataloged object missing becomes `missing` and degrades health;
- finalized valid object/manifest absent from catalog becomes `orphan_candidate` and requires deterministic validation/reconciliation;
- temp/partial/unknown-name/symlink objects are ignored from the catalog and surfaced through a safe count for operator cleanup;
- no unknown file is opened recursively or deleted automatically.

### 5.7 PostgreSQL and remote portability

Domain/repository contracts expose no SQLite PRAGMA, rowid, lock-code, path, rename, or filesystem semantics. Database snapshot/activation remains an adapter port and will change for PostgreSQL. Exact UTC, enum, sequence, idempotency, lease, cursor, digest, and transaction meanings remain portable. Remote object storage/encryption/multi-node coordination are not hidden in V1 abstractions; they require a future ADR and contract version.

## 6. External, database, platform, API, and UI boundaries

### 6.1 Database boundary

Registered Draft-aligned CTR-DB-003 is owned by PLAN-DB. Approval and real implementation evidence remain pending; its frozen surface must provide operations equivalent to:

- `CreateOnlineDatabaseSnapshotV1(target_ref, deadline, correlation)`;
- `CheckDatabaseIntegrityV1(database_ref, level=full)`;
- `GetDatabaseSchemaCompatibilityV1(database_ref, application_range)`;
- `PrepareDatabaseActivationV1(staging_ref, preserved_current_ref, operation_id)`;
- `ActivatePreparedDatabaseV1(activation_id)`;
- `RollbackDatabaseActivationV1(activation_id)`;
- `OpenIsolatedMigrationTargetV1(database_ref)`.

The implementation must use SQLite's real online backup/integrity mechanisms, short/bounded connections, exact fsync/close semantics, and no live-file copy shortcut. M08 receives typed receipts, never a general SQL connection.

### 6.2 Platform/filesystem boundary

CTR-PLAT-001 must supply typed primitives for approved root resolution, owner/mode/file-type/symlink validation, disk capacity, unique temp creation, bounded streaming read/write, fsync file/directory, immutable/atomic move, safe exact-file retirement/deletion, and state-root restore journal operations.

Each call uses an opaque root/object reference or prevalidated relative key, not an arbitrary caller path. It rejects traversal, symlinks, special files, different owner, broad permissions, unresolved variables/globs, and cross-device atomicity assumptions. Linux is verified first. macOS must implement the same semantic port on real macOS or remain Blocked.

### 6.3 Native service/deployment boundary

CTR-DEP-001 supplies narrow service status, request-quiesce, wait-for-drain, start restricted validation mode, start normal mode, and required-component facts. M08 owns `EnterOperationsMaintenanceV1`/`ExitOperationsMaintenanceV1` intent and never consumes a DEP composite that itself consumes M08 readiness. M08 does not invoke `systemctl` directly.

Restore/migration refuses to proceed if quiescence cannot be proven. A PID alone is insufficient. Collection resumes only through normal lifecycle after readiness. User lingering, installation, autostart, executable paths, and package layout remain PLAN-DEP decisions.

### 6.4 Artifact safety scanner boundary

One local scanner is selected and admitted by foundation/security. M08 invokes it through a bounded `ArtifactSafetyScannerPortV1` with exact artifact reference, size/deadline, scanner/rule version, and no upload/network permission. Output is `safe | finding | unavailable | incompatible` plus safe category/count; match content is never returned to logs/API/chat.

Unavailable/incompatible scanner fails artifact finalization closed. Allowlist serialization remains the primary control; scanning is defense in depth, not permission to collect raw data.

### 6.5 API boundary

P01 owns exact routes. Expected resource families are `/api/v1/backups`, `/api/v1/exports`, `/api/v1/diagnostics`, and authenticated health/version resources. Long actions return `202` with a job resource. GET never creates a backup/export/diagnostic or starts provider work.

Proposed permission map requiring M01/P01 approval:

- minimal liveness/readiness: disclosure policy pending, local service manager may use a non-HTTP internal port;
- detailed health/version/backups: `read:status`;
- diagnostics/audit/export listing/download: `read:diagnostics` plus subject authorization;
- backup creation/verification/retirement: `write:backup`;
- owner-requested export creation: proposed `write:exports` (new M01 scope; approval blocking);
- restore execution: no browser/bearer permission in V1; local maintenance authority only.

Browser state changes use CSRF, bearer actions require scopes, and duplicate actions use `Idempotency-Key`. P01 maps typed failures to RFC 9457 without paths/SQL/exception text.

### 6.6 UI boundary

P02 consumes only the generated client and displays:

- overall health/readiness with component cause/freshness and text/icon cues;
- application/schema/frontend/API/client/adapter versions and mismatch warnings;
- backup freshness, integrity, retained slots, job progress/failure, and manual-backup action;
- export/diagnostic job state, expiry, safety rejection, and authorized download;
- retention status and partial/blocked participants;
- truthful empty/loading/partial/stale/unauthorized/maintenance/error states.

P02 does not display paths, secrets, raw diagnostic content, provider credentials, arbitrary logs, or a restore execution button in V1. Browser tests use real operations records produced through production workflows, never placeholder cards.

## 7. Security and privacy

### 7.1 Trust boundaries and controls

| Threat | Control | Required evidence |
|---|---|---|
| Backup captures `.env`/profiles/files outside DB | DB snapshot port only; exact target; content inventory | real backup member/schema scan |
| Path traversal/symlink swaps backup/export target | opaque roots, no caller path, open/verify/atomic platform primitives | real isolated filesystem race/path tests |
| Backup is corrupt but labeled valid | full integrity then checksum then immutable catalog | real snapshot, corruption, restore tests |
| Restore overwrites only good database | stage first, preserve current, external journal, explicit activation/rollback | real failure after each safe phase |
| Restored DB resurrects sessions/tokens | mandatory M01 invalidation before activation/readiness | real token/session rejection after restore |
| Diagnostic/export leaks content/secret | typed module allowlists, no raw logs, size bounds, final scanner | real DB/API/bundle/token/config inspection |
| Browser/API triggers destructive restore | no public restore execution contract; local authority/quiescence | OpenAPI/route/source review |
| Retention deletes without recoverable export | checkpoint must be available/safe and digest must match | real saga/blocked-path evidence |
| One health producer hangs service | concurrent deadline/cancellation, stale/unknown state | real failing component isolation |
| Malicious checksum/manifest creates false identity | canonical encoding, object generation, immutable naming, digest verify | real tamper test |
| Artifact download leaks path/cache | application stream handle, auth, no path, no-store headers | real HTTP/browser inspection |
| Operations audit becomes content channel | enumerated events/codes, no free text/dicts | schema/DB/log review |

### 7.2 Authorization and owner confirmation

- Single-user does not bypass permission checks.
- Restore requires an explicit local operator checkpoint naming the resolved backup ID, impact, preserved-current behavior, and expected credential invalidation. Secrets are not part of confirmation.
- Artifact download reauthorizes at access time; possessing an artifact ID is insufficient.
- Internal scheduler/retention/migration principals are composition-bound typed authorities, not forgeable API fields.
- M08 cannot mint principals, scopes, or local-maintenance authority.

### 7.3 Secrets and sensitive data

M08 owns no secret configuration in V1. Backup/export/diagnostic roots are sensitive paths, not secrets, and are never returned. Database backups and operational exports are sensitive owner data even when they contain no plaintext credentials.

Prohibited from M08 API/events/logs/audit/manifests/evidence: `.env` values, password/session/API-token hashes or plaintext, OAuth/API credentials, cookies/headers, OTP/MFA, provider profile content, raw provider data, prompts/responses/tools/source, arbitrary environment, process memory/terminal output, SQL values, full local paths, and raw exception text.

Tests never read the operator `.env`. Secret-exclusion evidence uses credentials created through the real production bootstrap/token flow in an isolated real installation and prevents the values from entering test output/artifacts. The production scanner may be exercised with a short-lived real credential only under an approved security test packet; the credential is revoked and the contaminated disposable file is securely contained/deleted. No literal secret appears in reports.

### 7.4 Path and destructive-operation safety

- Resolve and validate exact approved roots before any write/delete.
- Never use `$HOME`, `~`, `/`, workspace root, unresolved variables, globs, or provider directories as recursive targets.
- Refuse symlinks and special files at every destructive step.
- Backup rotation deletes only a cataloged immutable object generation after a fresh valid backup and retained-slot calculation.
- Restore never deletes current DB; it preserves and swaps through the approved activation port.
- Disk-full/corruption tests target isolated real resources under an approved destructive-test plan.

### 7.5 Incident behavior

A secret/content finding, unexpected path, checksum mismatch, integrity failure, impossible job transition, fencing conflict, or activation ambiguity stops the affected operation. The artifact/database copy is quarantined by exact reference, normal readiness is reduced as appropriate, sanitized evidence is preserved, and the operations/security runbook is followed. M08 never edits data until an error disappears.

## 8. Configuration and operations

### 8.1 Proposed M08 configuration registry

No key is approved or may be added to `.env` by this Draft. All M08 settings are non-secret; paths are sensitive and values are absent from diagnostics.

| Proposed external key | Internal type/default/range | Reload | Consequence |
|---|---|---|---|
| `AGENTMONITOR_OPERATIONS_BACKUP_DIR` | approved absolute directory from PLAN-DEP; no repository-relative default | restart | backup object root; owner-only |
| `AGENTMONITOR_OPERATIONS_ARTIFACT_DIR` | approved absolute directory from PLAN-DEP | restart | export/diagnostic artifact root |
| `AGENTMONITOR_OPERATIONS_STATE_DIR` | approved absolute directory from PLAN-DEP | restart | restore journal/locks; not provider state |
| `AGENTMONITOR_OPERATIONS_BACKUP_DAILY_AT_UTC` | validated `HH:MM`; proposed `02:00` | restart | automatic schedule slot |
| `AGENTMONITOR_OPERATIONS_RETENTION_DAILY_AT_UTC` | validated `HH:MM`; proposed after backup, exact TBD | restart | export/purge opportunity |
| `AGENTMONITOR_OPERATIONS_BACKUP_MIN_FREE_BYTES` | positive bytes; measured safe default TBD | restart | backup/restore preflight |
| `AGENTMONITOR_OPERATIONS_BACKUP_RETIRE_GRACE_HOURS` | proposed 24; bounded | restart | two-phase deletion grace |
| `AGENTMONITOR_OPERATIONS_EXPORT_EXPIRY_HOURS` | proposed 168; bounded | restart | owner-requested artifact lifetime |
| `AGENTMONITOR_OPERATIONS_DIAGNOSTIC_EXPIRY_HOURS` | proposed 24; bounded | restart | diagnostic lifetime |
| `AGENTMONITOR_OPERATIONS_RETENTION_CHECKPOINT_EXPIRY_HOURS` | proposed 168; owner/privacy approval required | restart | post-purge recovery window |
| `AGENTMONITOR_OPERATIONS_JOB_LEASE_SECONDS` | derived bounded value TBD | restart | crash/fencing recovery |
| `AGENTMONITOR_OPERATIONS_HEALTH_TIMEOUT_MILLISECONDS` | measured bounded value TBD | restart | per-aggregation deadline |
| `AGENTMONITOR_OPERATIONS_ARTIFACT_MAX_BYTES` | measured bounded size TBD | restart | fail-closed output limit |
| `AGENTMONITOR_OPERATIONS_EXPORT_PAGE_COUNT` | bounded positive count TBD | restart | streaming page bound |
| `AGENTMONITOR_OPERATIONS_LOG_LEVEL` | approved enum; default INFO proposed | restart/reload decision pending | local verbosity without bodies/content |
| `AGENTMONITOR_OPERATIONS_LOG_DIR` | approved PLAN-DEP path | restart | owner-only local logs |
| `AGENTMONITOR_OPERATIONS_LOG_MAX_BYTES` | bounded positive bytes TBD | restart | rotation size |
| `AGENTMONITOR_OPERATIONS_LOG_BACKUP_COUNT` | bounded positive count TBD | restart | local rotations |

History retention is fixed at 365 days in V1 and is not weakened by an environment key. GFS counts are fixed at 7/4/12 by requirement. Configuration cannot disable checksum/integrity/scanning, allow unsafe roots, include `.env`/profiles, or make restore online.

### 8.2 Health thresholds and operational states

Exact thresholds for backup overdue, retention overdue, disk pressure, outbox lag, and job duration require PLAN-DEP/DB/performance evidence and are versioned policy, not hidden constants. A threshold change updates diagnostics, tests, and compatibility notes.

M08 lifecycle is `starting | reconciling | ready | degraded | maintenance | stopping | unavailable`. Artifact/backup/retention workers are supervised AgentMonitor-owned tasks. Browser closure has no effect. Shutdown stops admitting jobs, drains/cancels only owned tasks within deadline, persists resumable states, and never signals provider agents.

### 8.3 Structured logs and local measurements

Allowlisted logs: operation/job/backup/artifact/retention/audit IDs, component key, state transition, safe reason code, correlation/causation, duration, bounded counts/bytes, schema/contract/tool versions. Never log storage references, paths, checksums if disclosure is not approved, config values, artifact members, query records, or raw errors.

Local measurements include health-call duration/timeouts, job queue/lease age, backup duration/size/age, checksum/integrity duration, retained-slot counts, artifact bytes/records/expiry, retention participant lag/count, restore phase duration, and audit/outbox backlog. Labels are bounded. Nothing is sent externally.

### 8.4 Operator procedures to implement and exercise

- inspect liveness/readiness/component/version/config-presence safely;
- run and verify a manual backup;
- understand automatic backup schedule/slot assignment/rotation/blocking;
- verify a backup again and investigate checksum/integrity/missing-object failure;
- execute offline restore, validate credential invalidation, and roll back from an activation failure;
- run migration preflight with mandatory fresh backup;
- request/download/expire an operational export or diagnostic bundle;
- inspect partial retention cycle and resume safely;
- recover stale job lease, orphan backup/artifact, and restore journal;
- respond to disk pressure, permission failure, corruption, secret/content finding, and database incompatibility;
- validate post-upgrade health/schema/component versions;
- confirm collection continues with browser closed.

Commands remain Planned until the command registry contains an implemented, real-executed entry.

### 8.5 AUTO-BACKUP responsibility

M08 owns the behavioral contract and application workflow. The command wrapper location/syntax is assigned by PLAN-FND/PLAN-INT and registered only after execution.

`AUTO-BACKUP` must:

1. identify the exact installed configuration and database through approved config/DB ports;
2. acquire/coalesce a manual/automatic/migration-preflight job;
3. run every section 3.5 step;
4. optionally apply section 3.6 retention only after a new valid backup;
5. emit deterministic parseable evidence with command ID, job/backup ID, boundary, checksum/integrity/slot state, Passed/Failed/Blocked/Not Run, and no path/secret;
6. exit nonzero for failed/blocked required behavior;
7. be idempotent for the same explicit operation/schedule slot;
8. never install tools, migrate, restore, deploy, or delete outside the exact approved backup objects.

### 8.6 AUTO-RESTORE responsibility

M08 owns restore orchestration; DB owns snapshot/integrity/activation mechanics; DEP owns service lifecycle; M01 owns invalidation; modules own consistency.

`AUTO-RESTORE` must:

- require explicit local owner checkpoint after a read-only preflight;
- accept an exact backup ID, never an arbitrary path;
- execute section 3.7 with an external journal and fail-safe resume/rollback instructions;
- keep the current database until the restored system validates;
- fail closed if any required validation or security invalidation is unavailable;
- produce sanitized phase/evidence status and a nonzero exit for incomplete recovery;
- never claim success until post-restore startup/readiness/login-with-new-credentials and module checks actually pass.

### 8.7 AUTO-MIGRATE responsibility

PLAN-DB owns migration planning/execution/validation and schema locking. M08 owns operational preflight, maintenance, fresh verified backup, audit, and recovery coordination. PLAN-DEP owns service quiescence/start.

The synchronized `AUTO-MIGRATE` routine must:

1. resolve current/target schema compatibility and exact revision chain;
2. validate configuration, permissions, disk, active jobs, and recovery path;
3. call `AUTO-BACKUP` in `migration_preflight` mode and require a valid receipt;
4. enter maintenance/quiesce through DEP;
5. acquire DB migration lock and apply only approved revisions;
6. run DB integrity and every changed module's consistency validation;
7. start restricted then normal service only if readiness passes;
8. on failure preserve database/evidence and use tested downgrade or backup/prior-binary recovery, never improvise;
9. emit revision/backup/validation/evidence statuses without SQL/data/paths.

M08 never executes module DDL itself.

### 8.8 Diagnostic, export, retention, and completion automation

The integration steward must allocate repository-owned fail-closed command IDs for:

- `OPS-AUTO-DIAGNOSTIC`: create/validate/scan/catalog one diagnostic bundle;
- `OPS-AUTO-EXPORT`: create/validate/scan/catalog one authorized export;
- `OPS-AUTO-RETENTION`: fixed cutoff, checkpoint-before-purge, resumable participant saga;
- `OPS-AUTO-VERIFY-BACKUPS`: bounded catalog/object/checksum/integrity verification;
- M08 selectors under `AUTO-TEST`, `AUTO-QUALITY`, `AUTO-DOCS-CHECK`, and `AUTO-MIGRATE`;
- post-restore M08 checks under `AUTO-RESTORE`;
- M08 service checks under `AUTO-DEPLOY` and `AUTO-RELEASE`.

The exact executable syntax remains TBD until implemented and real-tested. Each routine is non-interactive except the named restore/secret/owner checkpoints; uses the same production application ports as the UI/service; emits Passed/Failed/Blocked/Not Run; returns nonzero on violations; has bounded redacted output; and never treats an absent platform, scanner, service, account, or natural-time state as Passed.

M08 cannot be called operations-ready until these routines exist in the verified command registry and their own real-boundary tests pass.

## 9. Test design before implementation

### 9.1 Integrity rules

- All scenarios below are `Not Run` at plan creation.
- Pure tests may construct health samples, UTC instants, slot candidates, and job transitions only for deterministic no-I/O policy.
- Persistence uses real file-backed SQLite, the full real migration chain, and production repositories.
- Filesystem/backup tests use actual files, modes, checksums, SQLite snapshots, fsync/rename behavior, and isolated approved roots.
- HTTP tests start the production server over an ephemeral loopback socket with real config, migrations, M01 authentication, and authorization.
- Browser tests use the production build in a real supported browser against the real server/database.
- Native lifecycle tests use the real target Linux user service. macOS is real or Blocked.
- Backup/export/diagnostic UI data is created by production operations on the actual test installation; no direct rows or placeholder artifacts.
- Upstream operational export data comes from real production module behavior/accounts or the scenario is Blocked. It is never seeded.
- Clocks are not patched and the machine clock is not changed. Full GFS horizon and 365-day deletion remain Blocked until naturally observable.
- Expected Red is missing/incorrect behavior, never missing dependency, syntax/setup failure, unavailable owner credential, or absent natural history.
- Every artifact and evidence record is secret/content-scanned and stored outside source control when it contains real operational metadata.

### 9.2 Pure domain scenarios (T1)

| Test ID | Requirement | Real dependencies | Expected behavioral Red | Green/pass condition | Owner |
|---|---|---|---|---|---|
| M08-PURE-001 | FR-OPS-002 | None; explicit samples/as-of | worst state is hidden by healthy sample | deterministic overall health preserves required worst state/reasons | M08 |
| M08-PURE-002 | NFR-RES-001 | None | optional degraded component makes service not ready | health degrades while normal readiness remains true | M08/DEP |
| M08-PURE-003 | FR-OPS-002 | None | required unavailable component is ignored | readiness false with exact blocker | M08/DEP |
| M08-PURE-004 | FR-OPS-002 | None | expired sample remains current | expired sample becomes Unknown and incomplete | M08/component owners |
| M08-PURE-005 | FR-OPS-003 | None; explicit UTC backups | GFS selection keeps wrong buckets/copy | newest 7 daily/4 weekly/12 monthly bucket union selected | M08 |
| M08-PURE-006 | FR-OPS-003 | None | one physical backup duplicated for three classes | one backup can hold multiple slot assignments | M08 |
| M08-PURE-007 | FR-OPS-003 | None | retention removes held/sole retained valid backup | protected and slot-holder backups never eligible | M08/security |
| M08-PURE-008 | FR-HIST-003, AC-HIST-002 | None; explicit UTC as-of | cutoff boundary is local-time/off by one | cutoff is exactly approved 365-day UTC duration | M08/module owners |
| M08-PURE-009 | FR-HIST-003 | None | retention participant can purge before checkpoint | state machine forbids purge without safe available checkpoint | M08 |
| M08-PURE-010 | FR-OPS-004 | None | readiness becomes true during restore | maintenance/restore/security-invalid states block readiness | M08/M01/DEP |
| M08-PURE-011 | FR-OPS-005 | None | secret diagnostic exposes source/value metadata | only configured/missing is representable | M08/FND/security |
| M08-PURE-012 | FR-HIST-004 | None | unregistered export field/schema is accepted | closed module schema rejects unknown field/major | M08/module owners |
| M08-PURE-013 | FR-OPS-005 | None | expired/rejected artifact remains downloadable | availability requires safe, unexpired, checksum-valid state | M08/P01 |
| M08-PURE-014 | FR-OPS-006, NFR-COMP-001 | None | unknown/mismatched version is labeled current | version state remains explicit and affects readiness per policy | M08/FND/DB |
| M08-PURE-015 | NFR-TEST-001 | None | invalid/terminal job transition succeeds | only documented transitions are accepted | M08 |
| M08-PURE-016 | NFR-SEC-001 | None | same idempotency key accepts different fingerprint | replay returns same result; mismatch conflicts | M08 |

Critical health, retention, GFS, artifact availability, readiness, and job-transition branches receive mutation testing. The exact admitted tool/score is synchronized; meaningful surviving mutants block completion.

### 9.3 Real SQLite and migration scenarios (T2)

| Test ID | Requirement | Real dependencies | Expected behavioral Red | Green/pass condition | Owner |
|---|---|---|---|---|---|
| M08-DB-001 | AC-V1-004 | real file SQLite/full Alembic chain | M08 tables absent/incompatible | fresh migration creates only owned schema and validates | DB/M08 |
| M08-DB-002 | AC-V1-004 | supported prior real schema artifact | upgrade loses/rewrites history or competing head | approved upgrade applies with compatibility/integrity | DB/M08 |
| M08-DB-003 | NFR-RES-001 | real DB/concurrent repositories | duplicate key creates two jobs | one job/receipt wins and replay resolves identically | M08 |
| M08-DB-004 | NFR-RES-001 | real DB/concurrent workers | two workers commit same lease generation | one fencing token wins; stale writer rejected | M08/DB |
| M08-DB-005 | FR-OPS-004 | real DB | invalid job transition/step ordering commits | constraints and domain reject impossible sequence | M08 |
| M08-DB-006 | NFR-OBS-001 | real DB/production workflows | audit missing/non-atomic/free-form field appears | action and required audit are atomic and allowlisted | M08/security |
| M08-DB-007 | FR-OPS-003 | real DB + finalized backup object | catalog says valid before verification/object final | valid record exists only after final receipt | M08/DB |
| M08-DB-008 | FR-OPS-003 | real DB/concurrent retention | duplicate active slot or held backup retired | uniqueness/protection and transaction hold | M08 |
| M08-DB-009 | FR-HIST-003/004 | real DB + real producer ports | purge begins without available checkpoint or resume repeats purge | checkpoint gates purge; participant progress resumes idempotently | M08/modules |
| M08-DB-010 | FR-HIST-004 | real DB + real export job | cursors/count/checksum do not reconcile | manifest and participant counts/checksums reconcile | M08/modules |
| M08-DB-011 | FR-HIST-003 | real DB | M08 purge deletes active/reference/audit-required row | only naturally eligible bounded rows delete and audit persists | M08 |
| M08-DB-012 | FR-OPS-002/006 | real component ports + DB | health snapshot loses freshness/version/reasons | bounded authoritative sample round-trips | M08/components |
| M08-DB-013 | NFR-PERF-001 | real production-created job/catalog volume | list/expiry/lease query scans unbounded tables | approved indexes and bounded query plans used | DB/performance |
| M08-DB-014 | FR-OPS-004 | real restored catalog DB + object root | restore loses/relabels missing/orphan backup state | deterministic safe reconciliation results | M08/DB/platform |
| M08-DB-015 | NFR-COMP-001 | real newer/incompatible schema copy | writable service silently starts | schema compatibility blocks writes/activation | DB/DEP/M08 |

No table is directly seeded for these claims. M08 records are created through production operations ports. Naturally aged deletion evidence may remain Blocked until real age exists.

### 9.4 Real filesystem, SQLite backup, and artifact scenarios (T2/T5/T7)

| Test ID | Requirement | Real dependencies | Expected behavioral Red | Green/pass condition | Owner |
|---|---|---|---|---|---|
| M08-FS-001 | FR-OPS-003 | real active SQLite DB/online backup port | copied live DB is inconsistent | online snapshot completes as standalone real SQLite DB | DB/M08 |
| M08-FS-002 | FR-OPS-003 | real snapshot/filesystem | checksum changes/not verified | streamed checksum recomputes identically before catalog success | M08 |
| M08-FS-003 | FR-OPS-003 | real snapshot/SQLite integrity | unchecked/corrupt copy labeled valid | full integrity valid is mandatory | DB/M08 |
| M08-FS-004 | FR-OPS-005 | real installed roots/backup | backup archive includes `.env`, profiles, logs, exports | object is database snapshot only; inventory excludes them | security/M08 |
| M08-FS-005 | NFR-SEC-001 | real Linux filesystem | broad owner/group/world access accepted | roots/manifests/backups/artifacts are owner-only | platform/security |
| M08-FS-006 | NFR-SEC-001 | real isolated symlink/traversal targets | write/delete escapes approved root | operation rejects before modification | platform/security |
| M08-FS-007 | FR-OPS-003 | real filesystem/process termination at approved safe point | partial temp becomes valid/cataloged | temp/orphan reconciliation never trusts partial object | M08/platform |
| M08-FS-008 | FR-OPS-003 | real service across actual UTC day slot | automatic slot omitted/duplicated | exactly one valid/coalesced scheduled job for slot | M08/DEP |
| M08-FS-009 | AC-OPS-004 | real backups over natural GFS horizon | rotation violates 7/4/12 or deletes retained holder | actual retained union matches policy; otherwise Blocked until horizon | owner/operations |
| M08-FS-010 | FR-OPS-002/005 | real service/components/config + scanner | diagnostic includes prohibited data/raw logs | only typed summary/manifests; scan safe | M08/security |
| M08-FS-011 | FR-HIST-004 | real module records/export ports + scanner | export missing rows/schema/checksum or contains prohibited field | complete versioned NDJSON ZIP finalizes safe | M08/modules/security |
| M08-FS-012 | FR-OPS-005 | isolated real IAM/config/token workflow | real credential appears in finalized artifact | no value appears; production scanner safe; credential revoked after test | M01/security/owner |
| M08-FS-013 | NFR-SEC-001 | real bounded filesystem/artifact | size limit fills disk or partial becomes downloadable | bounded failure cleans/quarantines exact temp and no download | M08/platform |
| M08-FS-014 | AC-OPS-005 | isolated real corrupted backup copy under approved plan | checksum/integrity mismatch ignored | restore preflight rejects and preserves current DB | M08/DB/security |

### 9.5 Real HTTP service scenarios (T3)

| Test ID | Requirement | Real dependencies | Expected behavioral Red | Green/pass condition | Owner |
|---|---|---|---|---|---|
| M08-HTTP-001 | FR-OPS-002 | real server/config/DB/IAM | detailed health leaks unauthenticated | disclosure and permission contract enforced | P01/M08/security |
| M08-HTTP-002 | FR-OPS-002 | real server/components | readiness returns 200-ready during required failure/maintenance | status/body truthfully not ready; liveness separate | P01/M08/DEP |
| M08-HTTP-003 | FR-OPS-006 | real built backend/frontend/schema/modules | version values missing/guessed or path leaks | authoritative safe inventory returned | P01/M08/FND |
| M08-HTTP-004 | FR-OPS-004 | real server/IAM/DB/filesystem | duplicate manual backup starts two snapshots | `202` points to same job for same key/fingerprint | P01/M08 |
| M08-HTTP-005 | FR-OPS-003/005 | real valid backup/catalog | backup response exposes storage path/content | typed view contains only approved metadata | P01/security |
| M08-HTTP-006 | FR-OPS-002/005 | real config/components | diagnostic returns secret value/length/raw error | safe presence/state/reason only | P01/M08/security |
| M08-HTTP-007 | FR-HIST-004 | real authorized export inputs | export blocks request or bypasses scope | `202` job; bounded authorized background work | P01/M08/modules |
| M08-HTTP-008 | FR-OPS-005 | real safe/expired artifacts | unauth/expired ID downloads file/path | reauthorization, no-store stream, expiry enforced | P01/M08 |
| M08-HTTP-009 | FR-OPS-004 | real OpenAPI/routes | online restore execution route is exposed | no V1 HTTP restore-execute operation exists | P01/security |
| M08-HTTP-010 | AC-V1-003 | real server/OpenAPI/generator/client | contract invalid/drift/handwritten mismatch | OpenAPI validates/diff passes/client compiles and calls real routes | P01/P02 |

### 9.6 Real built-browser scenarios (T4)

| Test ID | Requirement | Real dependencies | Expected behavioral Red | Green/pass condition | Owner |
|---|---|---|---|---|---|
| M08-BROWSER-001 | FR-OPS-002/006 | production UI/server/DB/components | health/version partial state hidden/color-only | real status/freshness/cause/version rendered accessibly | P02/M08 |
| M08-BROWSER-002 | FR-OPS-004 | real production backup workflow | manual backup is placeholder/synchronous/wrong state | real action/job/validity/slots visible through generated client | P02/P01/M08 |
| M08-BROWSER-003 | FR-OPS-005 | real diagnostic job/artifact | UI exposes paths/raw data or claims rejected available | safe summary/job/rejection/expiry truthful | P02/security |
| M08-BROWSER-004 | FR-HIST-004 | real export job/artifact | unauthorized/partial export appears complete | scope/progress/safety/download states truthful | P02/M08 |
| M08-BROWSER-005 | AC-UI-005 | real auth expiry/maintenance/component failure | stale session or maintenance appears generic success | actionable unauthorized/maintenance/partial/error states | P02/M01/M08 |

All browser checks cover keyboard/focus/names/non-color cues and responsive layouts through the P02 acceptance plan; M08 does not own global visual design.

### 9.7 Native lifecycle, restore, migration, and recovery scenarios (T5/T7)

| Test ID | Requirement | Real dependencies | Expected behavioral Red | Green/pass condition | Owner |
|---|---|---|---|---|---|
| M08-LIFE-001 | FR-OPS-001/002 | real Linux user service | PID-running is reported ready before preflight | service health/readiness follows contracts | DEP/M08 |
| M08-LIFE-002 | AC-OPS-002 | real service/browser/collector/backup schedule | browser closure stops scheduler/backup opportunity | service continues independently | DEP/M04/M08 |
| M08-LIFE-003 | AC-OPS-004 | real valid backup/current DB/service | restore writes active DB directly | isolated staging and preserved current precede activation | owner/DB/DEP/M08 |
| M08-LIFE-004 | FR-OPS-004 | real restore/schema/modules | restored incompatible/corrupt DB activates | checksum/integrity/schema/module checks block | DB/modules/M08 |
| M08-LIFE-005 | FR-OPS-004 | real IAM session/API token and restore | pre-restore credentials remain usable | all restored sessions/tokens invalid before readiness | M01/M08/security |
| M08-LIFE-006 | AC-OPS-005 | real activation failure at approved isolated boundary | current DB lost/no recovery state | external journal and preserved DB support explicit rollback | owner/DB/DEP |
| M08-LIFE-007 | AC-OPS-004 | real successful restore/start | collectors resume before validation | restricted mode validates, then normal readiness/resume | DEP/M04/M08 |
| M08-LIFE-008 | FR-OPS-004 | real restored data/API/UI | account/history/alerts/backups silently missing | required module consistency and representative reads pass | module owners/P01/P02 |
| M08-LIFE-009 | AC-OPS-005 | real migration with data | migration begins without fresh valid backup/maintenance | AUTO-MIGRATE requires backup receipt and quiescence | DB/DEP/M08 |
| M08-LIFE-010 | AC-OPS-005 | real failed migration in isolated approved target | failure is called rollback-ready without proof | tested recovery restores/forward-fixes and validates | DB/M08/owner |
| M08-LIFE-011 | NFR-SEC-001 | real isolated permission/disk-pressure resource | unsafe write proceeds or broad cleanup runs | exact job blocks; current DB/newest backups preserved | platform/M08 |
| M08-LIFE-012 | AC-HIST-002 | naturally aged real module history | eligible data survives or protected data deletes | checkpoint then real bounded delete; Blocked until age exists | owner/modules/M08 |
| M08-LIFE-013 | AC-OPS-003 | real naturally failing provider adapter/component | health aggregation failure crashes API/other collection | affected component degraded; others remain available | M03/M04/M08 |
| M08-LIFE-014 | NFR-RES-001 | real timed-out component port | aggregate request hangs past deadline | timeout isolated and bounded Unknown/Unavailable returned | component owner/M08 |

### 9.8 macOS scenarios (T5)

| Test ID | Requirement | Real dependencies | Expected behavioral Red | Green/pass condition | Owner |
|---|---|---|---|---|---|
| M08-MAC-001 | NFR-PLAT-001 | real supported macOS | Not Run until available | approved roots/permissions/atomicity/backup work or visible Blocked | A04-MAC/M08 |
| M08-MAC-002 | NFR-PLAT-001 | real macOS launchd service | Not Run until available | maintenance/restore/service lifecycle passes or visible Blocked | DEP-MAC/M08 |

Linux success never satisfies these rows.

### 9.9 Architecture, security, privacy, quality, and documentation scenarios

| Test ID | Gate | Real dependencies | Expected behavioral Red | Green/pass condition | Owner |
|---|---|---|---|---|---|
| M08-ARCH-001 | NFR-ARCH-001/FR-SAFE-002 | real source/import/API graph | M08 imports internals/tables or exposes control/restore API | boundary and surface clean | architecture/security |
| M08-ARCH-002 | NFR-ARCH-002 | ownership manifest/migrations | table/contract/path has conflicting owner | exactly one owner and approved consumer edges | integration |
| M08-ARCH-003 | FR-SAFE-002 | real source/dependencies | provider/process control/network sender enters M08 | prohibited imports/operations absent | security |
| M08-ARCH-004 | NFR-COMP-001 | real schemas/events/OpenAPI/DB/artifacts | breaking drift accepted in V1 | compatibility gate blocks or approved migration/ADR exists | integration |
| M08-SEC-001 | FR-OPS-005 | real DB/WAL/log/backups/exports/bundles/reports | secret/content/raw path/provider field appears | all inventories/scans clean | security/privacy |
| M08-SEC-002 | NFR-SEC-001 | real files/process ownership | service/root/broad mode violates least privilege | normal user and owner-only files | platform/security |
| M08-SEC-003 | NFR-OBS-001 | real logs/audit/errors | exception/path/payload/object dump emitted | typed safe fields/codes only | security |
| M08-SEC-004 | FR-OPS-005 | real diagnostic/config output | secret value-derived property exposed | only approved safe value or presence state | security/FND |
| M08-SEC-005 | NFR-PRIV-001 | real export/diagnostic schemas | prohibited arbitrary/free-form field accepted | field register traces every field to requirement | privacy |
| M08-SEC-006 | FR-SAFE-002 | real service/process/provider state | operation modifies provider profile/agent process | no such call/path and live agents unchanged | security/platform |
| M08-SEC-007 | NFR-SEC-001 | real restore/API/token workflow | remote/browser principal obtains local restore authority | authority boundary fails closed | M01/P01/DEP/security |
| M08-SEC-008 | AC-V1-007 | real repository/build/test artifacts | secret scanner absent/unsafe finding unresolved | blocking sanitized scan passes | security |
| M08-PRIV-001 | NFR-PRIV-001 | real network/artifact inventory | bundle contains content or unneeded identity | operational allowlist only | privacy |
| M08-PRIV-002 | NFR-PRIV-002 | real process/browser/dependency traffic | analytics/crash/upload egress exists | no external AgentMonitor telemetry/upload | privacy |
| M08-TEST-001 | AC-TEST-001/002 | real tests/source/dependency graph | double/replay/seed/test-only bypass exists | prohibited mechanism scan/review clean | test-integrity |
| M08-TEST-002 | AC-TEST-006 | real evidence summary | Blocked/Not Run hidden by aggregate green | every boundary/status remains visible | integration/test |
| M08-DEP-001 | NFR-LIC-001 | actual locked graph/upstream metadata | unadmitted M08/scanner package exists | full admission/SBOM/notices pass | dependency/license |
| M08-DEP-002 | NFR-LIC-001 | actual build/runtime scanners/tools | network/telemetry/license risk unreviewed | approved exact versions/data flow | dependency/security |
| M08-DOC-001 | NFR-DOC-001 | actual Markdown/contract/requirement tree | missing/broken/stale M08 docs | AUTO-DOCS-CHECK passes | docs/integration |
| M08-DOC-002 | AC-V1-001/006 | actual traceability/evidence/runbooks | scenario/command not mapped or invented | exact IDs and verified command refs resolve | integration/operations |
| M08-DOC-003 | AC-OPS-005 | real operator exercise records | prose procedure not executable/recoverable | runbook executed at claimed boundary | owner/operations |
| M08-PERF-001 | NFR-PERF-001 | real registered components | health query exceeds target/deadline | bounded parallel aggregation meets approved budget | performance/M08 |
| M08-PERF-002 | NFR-PERF-001 | real DB/artifact volume | export exhausts memory/unbounded query | streaming and page/byte limits hold | performance/M08 |
| M08-PERF-003 | NFR-PERF-001 | real SQLite under normal collection | backup/retention causes unacceptable lock/collection failure | measured approved latency/availability budget holds | DB/M04/M08 |

### 9.10 Failure and recovery coverage summary

The matrix covers invalid/missing configuration, setup-required IAM, incompatible/newer schema, component timeout, degraded provider, database unavailable/corrupt/locked, permission denial, symlink/path escape, insufficient space, process interruption, orphan/temp objects, checksum/integrity/manifest mismatch, concurrent jobs, stale lease/fencing, artifact scanner unavailable/finding, expired download, partial export, changed retention preview, partial purge, service not quiesced, restore validation/invalidation/activation failure, failed migration, and post-restart reconciliation.

Disk-full, corruption, real provider failure, macOS, GFS horizon, and 365-day history execute only on real safe resources/conditions. Otherwise they remain Blocked.

## 10. Implementation increments

Each increment begins with meaningful Red evidence in a working admitted environment, then minimum Green, then refactor/documentation with the relevant suite green.

| Increment | Owned files/area | Failing tests first | Minimum production change | Synchronization/docs | Exit evidence |
|---|---|---|---|---|---|
| M08-I00 contracts/automation | contract proposals/shared docs under root allocation | M08-ARCH-002/004, documentation validators | freeze CTR-OPS and producer/DB/DEP/automation seams; no module behavior | register/traceability/ADR as needed | Approved contracts; no code claim |
| M08-I01 pure health/readiness/jobs | M08 domain | M08-PURE-001..004/010/014..016 | deterministic aggregation/readiness/job/idempotency policies | module contract docs | T1 R/G/R + mutation |
| M08-I02 pure backup/retention/artifacts | M08 domain | M08-PURE-005..009/011..013 | GFS, cutoff, artifact eligibility, retention saga policies | backup/retention docs | T1 R/G/R + mutation |
| M08-I03 persistence foundation | M08 persistence/migrations | M08-DB-001..006/012/013/015 | jobs/audit/health repositories and migrations | migration metadata/recovery | real T2 R/G/R |
| M08-I04 backup catalog/artifact store | M08 persistence/adapters | M08-DB-007/008, M08-FS-002/005..007/013 | backup/artifact catalog, manifests, checksum, safe exact-file adapter | dependency/path review | real DB/filesystem R/G/R |
| M08-I05 real database backup | M08 app + DB ports | M08-FS-001..004/008 | manual/automatic online snapshot, verify, slots | AUTO-BACKUP/runbook | real SQLite backup R/G/R |
| M08-I06 health/config/version | M08 app/contracts | M08-DB-012, M08-HTTP-001..003/006, M08-LIFE-001/014 | health/readiness/config/version aggregation | P01/DEP/component docs | real component/server/service R/G/R |
| M08-I07 exports/diagnostics | M08 app/artifacts | M08-DB-010, M08-FS-010..013, M08-HTTP-007/008 | safe streaming artifacts/scanner/download ports | format/security docs | real artifact/HTTP R/G/R |
| M08-I08 retention orchestration | M08 app/persistence | M08-DB-009/011, M08-LIFE-012 | preview/checkpoint/purge saga using real producer ports | retention runbook | real available-boundary R/G/R; age state visible |
| M08-I09 restore/migration orchestration | M08 app + external journal | M08-DB-014, M08-FS-014, M08-LIFE-003..011 | AUTO-RESTORE/AUTO-MIGRATE orchestration and recovery | backup/recovery/upgrade docs | owner-coordinated real T7 R/G/R |
| M08-I10 API/browser | P01/P02 owners, M08 contract only | M08-HTTP-004..010, M08-BROWSER-001..005 | routes/generated client/UI workflows; no restore execute route | OpenAPI/UI/operator docs | real T3/T4 |
| M08-I11 native/long-horizon hardening | integration/DEP/platform | M08-LIFE-002/013, M08-FS-009, M08-MAC-001/002, M08-PERF-* | service scheduling/failure/performance evidence | release limitations | real results; unavailable rows Blocked |

### 10.1 Parallel-development safety

- I01 and I02 may proceed in parallel after common types freeze because both are pure and use distinct files allocated by root.
- I03 owns the M08 migration slice and serializes shared Alembic-head integration.
- I04/I05 require approved DB/platform ports; they do not implement those ports in M08 paths.
- I06 can integrate one health producer at a time after CTR-OPS-006 freezes; producers edit only their modules.
- I07 depends on source-module export schemas and the admitted scanner; source owners publish contracts independently.
- I08 waits for every participating preview/export/purge contract.
- I09 is sequential and exclusive with DB/DEP/M01 because it crosses maintenance/activation contracts.
- P01/P02 own routes/generated artifacts/UI. M08 never edits them to unblock itself.
- No two agents edit the same contract file, migration head, composition root, automation wrapper, OpenAPI, generated client, manifest, lock, or command registry concurrently.

### 10.2 Evidence per increment

Every implementation handoff records requirement/AC IDs, M08/contract/schema versions, exact changed files, test IDs, Red command/result/time, Green command/result/time, post-refactor command/result, actual boundary/environment, live-owner acknowledgement, Failed/Blocked/Not Run rows, secret scan, migration/backup/recovery, dependency/license/docs impact, and exact integration step.

## 11. Documentation outputs

Implementation requires synchronized updates to:

- `docs/modules/operations.md`: purpose, boundaries, invariants, DTOs/ports/errors, tables, jobs, health, limits;
- `docs/contracts/operations-v1.md`: exact CTR-OPS-001..007 and CTR-APP-001 schemas and compatibility;
- API/OpenAPI guidance for health, backups, exports, diagnostics, jobs, artifact download, and no public restore execution;
- configuration registry/reference with safe visibility and restart rules;
- backup/recovery runbook with verified command IDs, GFS policy, integrity, restore, rollback, IAM invalidation;
- diagnostic/export/retention runbook with formats, expiry, scanning, partial recovery;
- migration/upgrade/deployment runbooks and AUTO-BACKUP/AUTO-RESTORE/AUTO-MIGRATE coordination;
- threat model/data inventory for backup/export/diagnostic/restore journal;
- schema/migration notes and PostgreSQL/remote limitations;
- dependency admission/SBOM/notices for scanner/tool changes;
- traceability, risk register, known limitations, evidence/live matrix, and release notes.

No command moves from Planned/TBD to authoritative until it exists in the command registry and has real execution evidence.

## 12. Dependency and license impact

### 12.1 Proposed dependency posture

M08 proposes no new Python runtime package for domain policies, hashing, JSON, or ZIP creation; approved standard-library primitives are sufficient. SQLAlchemy/Alembic are shared persistence dependencies owned by foundation/PLAN-DB. SQLite online backup/integrity uses the DB adapter and the runtime's real SQLite implementation, not an M08 convenience package.

A production artifact secret/content scanner is mandatory but not selected by M08. Foundation/security must admit exactly one local, non-uploading tool and expose a bounded port. If the approved scanner requires a runtime binary/package, PLAN-DEP includes it and release SBOM/notices cover it. Scanner absence keeps artifact creation Blocked.

No scheduler, backup framework, cloud storage SDK, encryption library, archive package, daemon helper, telemetry/crash reporter, or remote upload dependency is justified in V1.

### 12.2 Admission requirements

Before any manifest/import/install, record exact package/tool/version/upstream, purpose and why standard library/current stack is insufficient, direct/transitive licenses, maintenance/security/provenance, supported Linux/macOS/Python, native binaries/install scripts, network/telemetry behavior, size/performance, vulnerabilities, pin/update/removal, alternatives, SBOM/notices, reviewer/date, and owner approval for non-permissive/unclear licensing.

### 12.3 License effects

The project remains Copyright (c) 2026 Pavlo Sidelov <pavlo@sidelov.com>, all rights reserved. This plan grants no license. Backup/export formats contain owner data, not redistribution rights. Public release requires the separate ADR/policy work already defined.

## 13. Risks, unresolved decisions, and stop conditions

### 13.1 Risks

| ID | Risk | Likelihood/impact | Mitigation/evidence | Owner | Status |
|---|---|---|---|---|---|
| M08-R01 / R-020 | Backup exists but cannot restore | Medium/Critical | validity pipeline plus real restore and startup | M08/DB/DEP | Open |
| M08-R02 / R-005 | Backup/export/diagnostic leaks secrets/content | Medium/Critical | strict content source, typed allowlist, scanner, artifact inventories | security/M08 | Open |
| M08-R03 / R-011 | Backup/retention locks or corrupts SQLite | Medium/Critical | online snapshot, short transactions, measured concurrency, integrity | DB/M08/M04 | Open |
| M08-R04 | GFS algorithm deletes required or last valid backup | Medium/Critical | pure union policy, holds, new-valid prerequisite, two-phase retirement | M08/test | Open |
| M08-R05 | Restore activation leaves ambiguous database state | Low/Critical | external journal, preserve current, fenced activation/rollback | DB/DEP/M08 | Open |
| M08-R06 | Restore resurrects sessions/API tokens | Medium/Critical | mandatory M01 staging invalidation and real credential test | M01/M08 | Open |
| M08-R07 | Cross-module purge partially completes | Medium/Major | checkpoint first, per-participant receipts/cursors, resume visibility | modules/M08 | Open |
| M08-R08 | Retention checkpoint extends data beyond policy | Medium/Major | approved short expiry, owner-only, explicit privacy decision | owner/privacy | Open/blocking |
| M08-R09 | Health aggregation hides timeout/uncertainty | Medium/Major | deadline and Unknown/partial state, required manifest | components/M08 | Open |
| M08-R10 / R-013 | Health/diagnostics disclose local security state | Medium/Critical | minimal/detailed projection, authorization, no paths/counts unless approved | P01/security/M08 | Open |
| M08-R11 / R-019 | CI green mistaken for restore/native evidence | High/Major | T7/T5 separate statuses and target-host evidence | integration/M08 | Open |
| M08-R12 | Long-horizon rotation/retention evidence unavailable | High/Major | real ongoing operation; visible Blocked; no time manipulation | owner/test | Accepted constraint |
| M08-R13 / R-012 | SQLite/file activation semantics block future remote DB | Medium/Major | DB adapter port, no domain path semantics, future ADR | DB/architecture | Monitoring |
| M08-R14 / R-023 | macOS file/service semantics diverge | Medium/Major | platform contract, real macOS gate, no inferred pass | A04-MAC/DEP | Open |
| M08-R15 / R-018 | Scanner/backup tooling adds license/supply-chain/egress risk | Medium/Critical | dependency admission, local-only, locks/SBOM/notices | dependency/security | Open |
| M08-R16 | Artifact catalog and filesystem diverge after crash/restore | Medium/Major | immutable manifest, reconciliation states, never trust unknown file | M08/platform | Open |
| M08-R17 | Product audit duplicates IAM or becomes content store | Medium/Major | ownership split, bounded orchestration, fixed schema | M01/M08/privacy | Open |
| M08-R18 | Disk pressure causes backup to consume remaining recovery space | Medium/Critical | free-space reservation, fail early, preserve newest backups/current DB | M08/platform | Open |

### 13.2 Approval-blocking synchronization decisions

1. Approve exact Health/Readiness/Liveness state semantics, disclosure, HTTP mapping, freshness, and required-component manifest ownership.
2. Approve each M01–M07/FND/DB/DEP CTR-OPS-006 result schema, indicator allowlist, deadline, and criticality.
3. Approve/freeze each producer's implementation of registered CTR-OPS-007 consistency, preview/purge, and safe export query semantics without direct tables.
4. Approve CTR-DB-003 snapshot/integrity/schema/staging/activation/rollback semantics and SQLite durability settings.
5. Approve CTR-DEP-001 quiesce/maintenance/restricted-start/normal-start/required-component semantics and Linux service evidence.
6. Approve CTR-PLAT-001 root/object/permission/symlink/fsync/atomic/disk semantics for Linux; record macOS availability.
7. Freeze backup object/sidecar manifest formats, checksum algorithm, integrity level, naming, immutable generation, and reconciliation.
8. Freeze automatic daily schedule behavior and exact GFS bucket/selection/tie/hold/two-phase retirement/grace rules.
9. Freeze restore local authority/owner confirmation, external journal, staging migration, validation order, activation/rollback, and cleanup.
10. Approve M01 bulk invalidation of every browser session/API token in staging and the post-restore login/token UX.
11. Decide whether backup encryption is explicitly Deferred for local V1 and document owner-only risk acceptance; no encryption is implied by this draft.
12. Freeze M08 job state/lease/fencing/concurrency/idempotency/restart behavior and outbox owner.
13. Freeze operational export/diagnostic schemas, NDJSON/ZIP format, source-module fields, bounds, checksums, scanner, expiry, and download behavior.
14. Approve `write:exports` or another least-privilege M01/P01 scope; approve detailed health/backup/audit permissions.
15. Approve retention fixed cutoff, participant order, preview digest, export-before-purge, partial saga, and seven-day checkpoint proposal.
16. Freeze M08 audit versus IAM audit ownership, product audit merge/pagination, and retention.
17. Allocate M08 tables, migration revisions, indexes, restore bootstrap behavior, and PostgreSQL portability review.
18. Approve every M08 configuration name/default/range/source/reload/diagnostic-visibility rule.
19. Allocate and implement command-registry owners for AUTO-BACKUP/AUTO-RESTORE/AUTO-MIGRATE/OPS-AUTO-DIAGNOSTIC/EXPORT/RETENTION and their real tests.
20. Select/admit the production scanner and exact runtime/deployment handling; unavailable scan must fail closed.
21. Approve P01 routes/status/problems/idempotency/download caching and explicit absence of online restore execution.
22. Approve P02 health/backup/artifact/retention workflows and accessible truthful states.
23. Approve real destructive-test packets for isolated corruption, permission, disk pressure, interrupted snapshot, migration, and restore.
24. Decide acceptable release treatment for naturally unavailable 12-month GFS and 365-day deletion evidence; it cannot be relabeled Passed.
25. Decide whether restore-journal/database activation/artifact storage/product-audit choices require new ADRs.

No item may be silently selected by an implementation agent when alternatives materially affect data loss, security, contracts, or evidence.

### 13.3 Stop and escalation conditions

Stop and return to root synchronization if work would:

- read another module's table/private code or serialize its ORM row;
- change a contract state, disclosure, unit, time, checksum, retention, idempotency, ordering, or authority meaning;
- copy a live SQLite file rather than use the approved snapshot port;
- operate on a path not resolved from an approved root/object reference;
- follow a symlink, use a broad recursive delete, overwrite a backup, delete the only/current DB, or drop an unverified backup;
- activate a restore without quiescence, owner confirmation, integrity/schema/module validation, or M01 invalidation;
- purge before a complete safe export checkpoint or after a preview digest changed;
- include `.env`, provider profiles, logs, raw payloads, content, secrets, paths, or arbitrary fields in an artifact;
- finalize an artifact while its scanner is unavailable/incompatible or reports a finding;
- add/install a dependency before admission;
- use a mock/fake/stub/emulator/replay/in-memory DB/seed/backdated row/patched clock/test-only bypass;
- claim macOS, long-horizon rotation, aged retention, or failure recovery Passed without real evidence;
- contact a provider, change a provider profile, control an agent, send/upload an artifact, or run as root;
- perform a destructive owner-data test, migration, restore, deployment, or external operation without explicit authority;
- encounter overlapping user/agent changes in an assigned/shared file.

## 14. Delivery, compatibility, migration, and rollback

### 14.1 Delivery order

1. Synchronize CTR-OPS-001..007, CTR-APP-001, participant implementations, CTR-DB-003, CTR-DEP-001, CTR-PLAT-001, IAM scopes/invalidation, and event durability.
2. Approve this plan, paths, migrations, configurations, dependencies, tests, destructive-test packets, and command ownership.
3. Implement pure health/readiness/job/GFS/retention/artifact policies with R/G/R.
4. Implement M08 schema/repositories/audit/jobs against real SQLite.
5. Implement real backup/catalog/integrity/checksum/rotation vertical slice and AUTO-BACKUP.
6. Integrate health/config/version ports one producer at a time.
7. Implement diagnostic/export artifacts, scanner, authorization, and API/UI workflows.
8. Integrate every retention participant; enable automatic purge only after checkpoint/purge recovery tests.
9. Implement and owner-exercise AUTO-RESTORE and AUTO-MIGRATE on isolated then real approved target data.
10. Integrate native service/background scheduling, measure performance, accumulate natural-horizon evidence, and complete release review.

### 14.2 Compatibility

- CTR-OPS additive optional fields are compatible only with safe absence/Unknown handling.
- Health/readiness state meaning, criticality, backup validity, checksum/integrity, GFS slot semantics, restore authority/phase, artifact format/safety, retention cutoff/checkpoint, event ordering/idempotency, or public disclosure changes require a new major and consumer/data migration; consequential changes require an ADR.
- Artifact manifests and external restore journals have explicit schema majors and retain reader compatibility for all supported recovery artifacts.
- Older binaries refuse newer incompatible database/artifact/journal schemas.
- Backup compatibility records the application/schema range; compatibility is checked at restore time, not assumed from age.

### 14.3 Rollback and recovery

- Prefer forward-fix for additive M08 code/schema defects while preserving catalog/audit/jobs.
- Before M08 migration, create/verify a fresh backup unless bootstrap policy explicitly and safely excludes an empty first install.
- Never rewrite shared migration history. Unsafe downgrade uses a verified backup plus prior compatible binary.
- A failed backup leaves current DB and prior backups untouched.
- A failed artifact remains unavailable and its exact temp is quarantined/retired safely.
- A failed retention cycle resumes from participant receipts; it never reruns completed destructive steps blindly.
- Restore rollback uses the external journal and preserved current database; owner reviews data-loss window before choosing restored versus preserved copy.
- Rollback never modifies provider profiles, accounts, or running agents.

### 14.4 Post-deployment checks

- service liveness/readiness/health and required manifest agree;
- application/frontend/API/client/schema/module/adapter versions are authoritative and compatible;
- automatic scheduler and browser-independent work are active;
- newest backup is valid, checksum/integrity verified, and GFS slots reconcile;
- export/diagnostic artifact safety and expiry jobs are healthy;
- retention participant/checkpoint states are not overdue/partial without visible reason;
- M08 job leases/outbox/audit/reconciliation have no unexplained backlog;
- real manual backup and representative restore evidence are current;
- logs/DB/WAL/backups/artifacts/browser/evidence pass prohibited-data scans;
- every T5/T7/macOS/natural-horizon scenario remains explicitly Passed/Failed/Blocked/Not Run.

### 14.5 Implementation handoff packet

Every M08 implementation handoff uses the repository templates and includes:

- exact requirement and acceptance-criterion IDs addressed;
- plan, `operations.v1`, consumed-contract, schema, artifact-format, and automation versions;
- every changed file, migration, generated artifact, configuration key, command-registry entry, and owning reviewer;
- test IDs with exact Red, Green, and post-refactor commands/results/timestamps and the real boundary exercised;
- real SQLite/filesystem/HTTP/browser/Linux/backup/restore/migration evidence, plus every Failed, Blocked, and Not Run row;
- owner acknowledgement for restore, destructive isolated tests, and any credential-sensitive live verification;
- API/event/database/configuration/artifact compatibility diffs and migration/recovery results;
- security/privacy field inventory, secret/content scan, path/permission/no-control proof, and incident findings;
- dependency/license/lock/SBOM/notices impact;
- runbook/documentation/traceability/risk updates;
- remaining limitations, natural-horizon status, rollback position, and exact next integration step.

A handoff cannot say M08 or recovery is complete unless the applicable canonical commands pass against the real target and the evidence scope covers the claim.

## 15. Definition of Ready for implementation

- [ ] Owner approves outcomes, non-goals, backup/restore/retention/export behavior, and long-horizon limitation.
- [ ] Root approves this exact plan/version and changes status to Approved.
- [ ] Canonical synchronized planning gate includes M08 and passes against the real checkout.
- [ ] Allowed/forbidden/shared paths, migration head, automation, generated files, and implementation/reviewer owners are conflict-free.
- [ ] CTR-COMMON/FND/CONFIG/IAM/DB/PLAT/DEP contracts consumed by M08 are Approved.
- [ ] CTR-OPS-001..007 and CTR-APP-001 schemas/ports/events/errors/versions/disclosure/idempotency are synchronized with every producer/consumer.
- [ ] Every M01–M07 health/consistency/retention/export port is approved; no direct-table workaround remains.
- [ ] CTR-DB-003 and CTR-DEP-001 are approved with real Linux implementation resources.
- [ ] Backup manifest/checksum/integrity/GFS/rotation/reconciliation/encryption-deferral decisions are approved.
- [ ] Restore journal/staging/migration/validation/invalidation/activation/rollback/cleanup decisions are approved.
- [ ] Retention cutoff/checkpoint/expiry/partial-recovery behavior and module order are approved.
- [ ] Artifact formats/allowlists/scanner/bounds/expiry/download/audit are approved.
- [ ] M01 permissions and P01/P02 transport/workflows are approved, including no public restore execution.
- [ ] M08 tables/indexes/transactions/retention/outbox/migration/portability are approved.
- [ ] Configuration keys/defaults/ranges/reload/visibility and log/rotation ownership are approved.
- [ ] Exact dependency/tool versions, direct/transitive licenses, security/provenance, locks, SBOM, and notices pass admission.
- [ ] Each test has correct real boundary, meaningful expected Red, safe cleanup/evidence, and assigned owner.
- [ ] Real SQLite/filesystem/server/browser/Linux service and owner restore checkpoints are available; macOS/long-horizon states are preclassified truthfully.
- [ ] Destructive isolated test packets for corruption/permission/disk/migration/restore are explicitly approved.
- [ ] Canonical automation entrypoints required for the first increment exist and are themselves real-tested; absent later-stage commands keep those stages Not Ready.
- [ ] Threat/privacy/data-inventory/security review resolves or explicitly accepts every Critical risk.
- [ ] Runbooks, traceability, evidence custody, rollback, and handoff outputs are assigned.
- [ ] Any required ADR is Accepted.
- [ ] No unresolved section 13.2 decision permits materially different implementation.

Until every applicable item is checked, M08 is **Not Ready for implementation**.

## 16. Approval record

| Reviewer/owner | Decision | Conditions/evidence | Date | Approved versions |
|---|---|---|---|---|
| Pavlo Sidelov / product owner | Pending | backup/restore/retention/export/authority/long-horizon decisions | — | — |
| Root/integration steward | Pending | cross-plan contracts, automation, paths, migration allocation | — | — |
| M01 owner | Pending | permissions, audit query, purge, post-restore invalidation | — | — |
| M02–M07 owners | Pending | health/consistency/export/retention ports and failure semantics | — | — |
| PLAN-FND/config/build/evidence owners | Pending | metadata/config/log/scanner/command seams | — | — |
| PLAN-DB/persistence reviewer | Pending | snapshot/integrity/schema/activation/migrations/tables/portability | — | — |
| PLAN-DEP/A04 reviewers | Pending | roots/permissions/fsync/service/maintenance/Linux/macOS | — | — |
| P01/P02 owners | Pending | authorization/OpenAPI/generated client/UI/disclosure/no restore route | — | — |
| Security/privacy reviewer | Pending | artifacts, paths, secrets, destructive flow, data inventory | — | — |
| Test-integrity/live reviewer | Pending | real boundaries, R/G/R, natural-time/Blocked policy | — | — |
| Dependency/license reviewer | Pending | scanner/shared tool/runtime admission | — | — |

Approval authorizes only a later explicit implementation task packet. It does not authorize backup, restore, migration, deployment, provider access, dependency installation, `.env` creation, destructive testing, Git/GitLab mutation, or external publication.


### Focused M4 overview adoption

The approved M4 operations packet publishes APP-001 using the actual REG-009
registry scope snapshot and ALERT-005 dashboard notification counts. M08
consumes both V1 contracts for typed bounded projections; it does not query
producer tables or infer missing section values. Full master approval remains
Draft; this adoption is confined to the approved focused M4 implementation.
