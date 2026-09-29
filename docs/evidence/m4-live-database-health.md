# M4 bounded live SQLite health evidence

- Scope: focused PLAN-DB increment, [approved packet](../plans/integration/m4-live-database-health-change.md) 0.1.0, CTR-DB-001 V1 1.0.0.
- Requirements: FR-OPS-002/006, NFR-DATA-001, NFR-COMP-001, NFR-RES-001, NFR-OBS-001, NFR-SEC-001, NFR-PRIV-001; supporting AC-OPS-003 and AC-V1-003/005/006/007/008.
- Environment: actual Linux checkout, Python 3.12 / SQLite 3.45.1, admitted Alembic stack, unique temporary owner-only SQLite files, production migrations and startup inspector. At final verification the actual reviewed catalog was 1.7.4 with head `v1_0704`; tests load these artifacts rather than pinning a substituted marker.
- Full M4, wider PLAN-DB and M08 status: incomplete; this evidence is not their acceptance gate.

## Red, Green and refactor

Canonical focused test selector handed to root:

```sh
backend/.venv/bin/python -m pytest backend/tests/persistence/sqlite/core/test_bounded_read.py backend/tests/persistence/sqlite/schema/test_live_health.py -q
```

1. Initial Red: **20 failed, 0.41 s**, both new production modules absent (`ModuleNotFoundError`). This is missing-core evidence, not a lock/deadline behavior claim.
2. First real implementation: **8 failed, 12 passed, 3.77 s**. Actual schema reads were denied because SQLite names schema columns `sqlite_master` and count(*) can authorize an implicit database name. The narrow schema-alias correction preserved table admission and mutation refusal.
3. First Green: **20 passed, 3.55 s** with actual live WAL, exclusive lock, recursive VM interruption, startup inspection and schema-failure cases.
4. Additional pure contract-policy Red: **3 failed, 0.26 s**, unsupported nested reason/state and integer-as-boolean were accepted (`DID NOT RAISE`). Added closed runtime validation. A subsequent edit misplaced validation on request instead of result and caused **12 failed, 11 passed**; corrected placement, not counted as a meaningful requirement Red.
5. Post-format Green: **23 passed, 4.05 s**. Three cases construct immutable pure policy inputs with no I/O; the remaining 20 use real SQLite/filesystem behavior. Final rerun after the ATTACH-denial test selected an isolated real target instead of an in-memory target: **23 passed, 4.06 s**.

Static commands:

```sh
backend/.venv/bin/ruff check backend/src/agentmonitor/contracts/database_v1.py backend/src/agentmonitor/adapters/persistence/_shared/sqlite/core/bounded_read.py backend/src/agentmonitor/adapters/persistence/_shared/sqlite/schema/live_health.py backend/tests/persistence/sqlite/core/test_bounded_read.py backend/tests/persistence/sqlite/schema/test_live_health.py
MYPYPATH=backend/src backend/.venv/bin/mypy --follow-imports=silent --explicit-package-bases backend/src/agentmonitor/contracts/database_v1.py backend/src/agentmonitor/adapters/persistence/_shared/sqlite/core/bounded_read.py backend/src/agentmonitor/adapters/persistence/_shared/sqlite/schema/live_health.py
```

Ruff **Passed**. Mypy initially found repeated `utcoffset()` could be nullable; storing its checked value fixed it. Final mypy **Passed, 3 source files**. Scoped `git diff --check` **Passed, exit 0** for the eight assigned code/test/documentation files.

## Actual boundaries and limits

| Boundary/scenario | Status | Evidence |
|---|---|---|
| Production migrations and real startup integrity receipt | Passed | Current revision sourced from actual reviewed catalog and DB marker; historical time preserved |
| Live WAL read with an actual writer retained | Passed | No quiescent/immutable inspector called on live GET; database/WAL content unchanged while writer idle |
| Actual exclusive SQLite lock before reader returns | Passed | 100 ms budget fails safely in less than 500 ms; no background work |
| Actual recursive SQLite VM work | Passed | Progress interruption under 100 ms budget, returns within 500 ms; fresh reader succeeds afterward |
| Query-only/mutation/ATTACH/unlisted read refusal | Passed | Actual SQLite authorizer, safe code, no stored SQL/path output |
| Missing/unsafe/symlink/replaced file | Passed | No creation/repair; changed identity refuses result |
| Actual unknown/older/multiple markers and changed technical schema | Passed | No migration; raw unknown marker withheld; startup receipt invalidated |
| Missing startup binding | Passed | Reachable actual marker remains unknown/not checked |
| Root composition and producer adapter adoption | Not Run by this role | Root-owned integration |
| Real HTTP/browser/owner service and canonical full M4 gate | Not Run by this role | Root-owned integration |
| Hard OS-stall deadline/macOS/disk-pressure | Not Run | SQLite busy/VM scope is the approved limit; no universal filesystem/OS bound claimed |

## Impact and handoff

Files: database contract additions; new `core/bounded_read.py`, `schema/live_health.py`; the two focused persistence test files; approved packet, this evidence and persistence guide. Root alone edits composition, canonical automation/checker/register/index/runbook and APIs. `InspectStartupDatabaseHealthV1` returns the real startup view and optional internal receipt; root binds before opening the writer. `LiveDatabaseHealthReaderV1` implements the async public DB leaf with bounded synchronous local work. Nullable compatibility must map to unknown, never ready.

No provider/default-profile/process/browser mutation, dependency, license change, migration, schema object, secret/config value or path exposure was introduced. Sidecar bookkeeping is ordinary SQLite behavior, not an unchanged-SHM claim. Full gate/HTTP/browser remain explicit integration work.
