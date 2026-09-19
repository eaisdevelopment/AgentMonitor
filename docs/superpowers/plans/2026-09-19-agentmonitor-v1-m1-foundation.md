# AgentMonitor V1-M1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the reproducible, provider-free AgentMonitor foundation with a real file-backed SQLite migration, a running loopback FastAPI application, deterministic OpenAPI/client generation, a built browser shell, and fail-closed automation.

**Architecture:** Foundation publishes only technical V1 contracts and composition seams. SQLite implements versioned persistence contracts, FastAPI owns the HTTP boundary, and the React shell consumes only the generated client. Shared contracts, migrations, generated artifacts, locks, composition, and CI are changed only by their named writers.

**Tech Stack:** Python, FastAPI, OpenAPI 3, SQLite/Alembic, React/TypeScript, generated API client, Playwright, GitLab CI.

**Spec:** `docs/product/v1-specification.md`

## Milestone map

- Milestone: `V1-M1` — reproducible foundation and real local-stack skeleton.
- Epics: `EPIC-FND-01`, `EPIC-CONTRACT-01`, `EPIC-DATA-01`.
- Detailed authority: [foundation](../../plans/foundation/plan-v1.md), [SQLite](../../plans/persistence/sqlite/plan-v1.md), [FastAPI boundary](../../plans/api/fastapi-boundary/plan-v1.md), and [React dashboard](../../plans/ui/react-dashboard/plan-v1.md).
- Contract versions: `CTR-COMMON-001..003/006/007`, `CTR-CONFIG-001`, `CTR-FND-001..008`, `CTR-BOUNDARY-001/003`, `CTR-PLAT-001`, and `CTR-DB-001..003`, all V1 only after approval.
- Entry gate: `AUTO-PLAN-CHECK` passes; the listed plans/contracts and dependency admissions are owner-approved; the execution ledger allocates each exact shared write path.
- Exit gate: the commands in Task 5 pass against a real SQLite file, real loopback server, generated artifacts, and a built real-browser shell. Hosted CI evidence is reported only for a CI run that actually occurred.

## Global Constraints

- No production edit starts while the relevant plan or contract remains Draft, evidence-blocked, or unapproved.
- External boundaries use real systems. Mocks, fakes, stubs, in-memory SQLite, recordings, demo data, seeded telemetry, test-only endpoints, and placeholder UI values are forbidden.
- Each behavior follows Red → Green → Refactor; retain the command, expected behavioral Red, Green result, and review evidence under the approved sanitized evidence path.
- Do not read or persist prompts, responses, source content, arbitrary environment values, credentials, or provider state. No provider integration belongs in this milestone.
- Dependency and lock changes require approved license, maintenance, security, necessity, transitive-impact, SBOM, and notices records first.
- A Story is independently reviewed before a later Story consumes it. Shared-writer ownership follows `docs/plans/parallel-ownership.toml`.

---

### Task 1: `ST-CONTRACT-001` — Freeze V1 technical contracts and import ownership

**Epic:** `EPIC-CONTRACT-01`

**Requirements / acceptance:** `NFR-ARCH-001`, `NFR-ARCH-002`, `NFR-COMP-001`, `AC-TEST-001`, `AC-TEST-006`; `FND-BND-001..003`.

**Contracts:** `CTR-COMMON-001/002/003/006/007`, `CTR-FND-001`, `CTR-CONFIG-001`, `CTR-BOUNDARY-001/003`, `CTR-PLAT-001`, `CTR-DB-001..003` at V1.

**Files:**
- Create: `backend/src/agentmonitor/contracts/common_v1.py`
- Create: `backend/src/agentmonitor/contracts/configuration_v1.py`
- Create: `backend/src/agentmonitor/contracts/foundation_v1.py`
- Create: `backend/src/agentmonitor/contracts/platform_v1.py`
- Create: `backend/src/agentmonitor/contracts/boundary_v1.py`
- Create: `backend/src/agentmonitor/contracts/database_v1.py`
- Create: `backend/tests/foundation/test_contract_boundaries.py`
- Create: `tooling/foundation/check_boundaries.py`
- Create: `docs/modules/foundation.md`

**Interfaces:**
- Produces V1 symbols `OpaqueIdV1`, `TimestampAndDurationV1`, `ExactQuantityV1`, `EventEnvelopeV1`, `FieldAvailabilityV1`, `RepositoryLayoutAndOwnershipManifestV1`, `BootstrapConfigurationV1`, `ApplicationFactoryV1`, `CorrelationContextAndSafeLogEventV1`, `OpenApiArtifactAndGeneratedClientPipelineV1`, `MigrationMetadataV1`, `BuildMetadataV1`, `TestEvidenceSummaryV1`, `SafeSubprocessExecutionV1`, `ApprovedRootAndFileReadV1`, `PortablePlatformPrimitivesV1`, `SchemaCompatibilityV1`, `RepositoryAndUnitOfWorkTechnicalFamilyV1`, and `DatabaseSnapshotActivationV1`.
- Enforces `composition -> api/adapters -> application ports -> domain/contracts`; domain code cannot import FastAPI, SQLAlchemy, provider packages, OS APIs, composition, or UI code.

- [ ] **Step 1: Write the failing boundary test**

```python
from pathlib import Path

from tooling.foundation.check_boundaries import find_forbidden_imports


def test_domain_rejects_fastapi_import(tmp_path: Path) -> None:
    source = tmp_path / "backend/src/agentmonitor/modules/example/domain/rule.py"
    source.parent.mkdir(parents=True)
    source.write_text("from fastapi import FastAPI\n", encoding="utf-8")
    assert find_forbidden_imports(tmp_path) == [f"{source.relative_to(tmp_path)}:1:fastapi"]
```

- [ ] **Step 2: Run Red**

Run: `python3 -m pytest backend/tests/foundation/test_contract_boundaries.py -q`

Expected: FAIL because the real source-tree checker does not yet reject the forbidden domain import.

- [ ] **Step 3: Implement the minimum contract files and AST boundary checker**

Implement immutable, closed V1 value types in the six exact contract files and make `find_forbidden_imports(root: Path) -> list[str]` inspect real Python imports deterministically. Do not add compatibility re-exports or a shared utility package.

- [ ] **Step 4: Run Green and refactor checks**

Run: `python3 -m pytest backend/tests/foundation/test_contract_boundaries.py -q && python3 tooling/foundation/check_boundaries.py .`

Expected: PASS; the test violation is detected and the real repository has no ownership violation.

- [ ] **Step 5: Review and commit**

Verify contract names/versions against `contract-adoption.toml`, attach `FND-BND-001..003` evidence, then commit: `git commit -m "feat(foundation): publish v1 technical contracts"`.

---

### Task 2: `ST-FND-001` — Typed bootstrap configuration and safe correlation logging

**Epic:** `EPIC-FND-01`

**Requirements / acceptance:** `NFR-ARCH-002`, `NFR-SEC-001`, `NFR-PRIV-001`, `NFR-OBS-001`; `FND-CFG-001..004`, `FND-LOG-001..004`.

**Contracts:** `CTR-CONFIG-001`, `CTR-FND-003`, and `CTR-FND-004` at V1.

**Files:**
- Create: `backend/src/agentmonitor/foundation/configuration.py`
- Create: `backend/src/agentmonitor/foundation/observability.py`
- Create: `backend/tests/foundation/test_configuration.py`
- Create: `backend/tests/foundation/test_safe_logging.py`

**Interfaces:**
- `load_bootstrap_configuration(config_path: Path, environment: Mapping[str, str], cli: BootstrapCliOptionsV1) -> BootstrapConfigurationV1` accepts only registered `AGENTMONITOR_*` names and returns immutable settings plus non-secret source metadata.
- `build_safe_log_event(context: CorrelationContextV1, code: SafeLogCodeV1, fields: tuple[SafeLogFieldV1, ...]) -> SafeLogEventV1` accepts typed allowlisted fields only.

- [ ] **Step 1: Write failing privacy and validation tests**

```python
def test_unknown_environment_name_is_rejected() -> None:
    result = load_bootstrap_configuration(CONFIG, {"PATH": "/sensitive"}, CLI)
    assert result.error.code == "unknown_environment_name"


def test_log_event_rejects_arbitrary_payload() -> None:
    with pytest.raises(UnsafeLogFieldError):
        build_safe_log_event(CONTEXT, SAFE_CODE, (("payload", object()),))
```

- [ ] **Step 2: Run Red**

Run: `python3 -m pytest backend/tests/foundation/test_configuration.py backend/tests/foundation/test_safe_logging.py -q`

Expected: FAIL because unknown environment input and arbitrary log payloads are not yet rejected.

- [ ] **Step 3: Implement the minimum typed loader and logger**

Read only the explicit config path and supplied allowlisted environment mapping; never inspect the global environment inside domain logic. Make secret wrappers non-serializable and keep remote log sinks absent.

- [ ] **Step 4: Run Green and refactor suite**

Run: `python3 -m pytest backend/tests/foundation/test_configuration.py backend/tests/foundation/test_safe_logging.py -q`

Expected: PASS with stable safe error codes and no secret value in output or captured logs.

- [ ] **Step 5: Review and commit**

Perform the configuration/privacy checklist and commit: `git commit -m "feat(foundation): add typed bootstrap and safe logs"`.

---

### Task 3: `ST-DATA-001` — Real SQLite policy, compatibility inspection, and base migration

**Epic:** `EPIC-DATA-01`

**Requirements / acceptance:** `NFR-DATA-001`, `NFR-RES-001`, `NFR-COMP-001`, `AC-OPS-004`, `AC-TEST-004`; `FND-DB-001..004`, `FND-MIG-003`, `DB-FILE-001/002/007..009`, `DB-MIG-001..005/008/009/013`.

**Contracts:** `CTR-DB-001`, `CTR-DB-002`, and `CTR-FND-006` at V1.

**Files:**
- Create: `backend/src/agentmonitor/adapters/persistence/_shared/sqlite/core/policy.py`
- Create: `backend/src/agentmonitor/adapters/persistence/_shared/sqlite/schema/compatibility.py`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`
- Create: `backend/migrations/catalog.toml`
- Create: `backend/migrations/versions/v1_0000_fnd_anchor.py`
- Create: `backend/tests/persistence/sqlite/core/test_file_policy.py`
- Create: `backend/tests/persistence/sqlite/migrations/test_v1_0000.py`

**Interfaces:**
- `open_sqlite_database(database_ref: DatabaseRefV1, mode: DatabaseOpenModeV1) -> SqliteDatabaseHandleV1` applies `foreign_keys=ON`, `journal_mode=WAL`, `synchronous=FULL`, `busy_timeout=5000`, `read_uncommitted=OFF`, `wal_autocheckpoint=1000`, and `trusted_schema=OFF` to every real connection.
- `InspectSchemaCompatibilityV1(database_ref, application_range, mode) -> SchemaCompatibilityViewV1`; `RequireWritableSchemaV1(compatibility_view) -> WritableSchemaReceiptV1`.
- Revision `v1_0000` is a metadata-only anchor and creates no business table.

- [ ] **Step 1: Write a failing real-file migration test**

```python
def test_v1_0000_uses_real_file_and_creates_no_business_tables(tmp_path: Path) -> None:
    database = tmp_path / "agentmonitor.db"
    migrate_to_head(database)
    assert database.is_file()
    assert list_tables(database) == ["alembic_version"]
    assert pragma(database, "foreign_keys") == 1
    assert pragma(database, "journal_mode") == "wal"
```

- [ ] **Step 2: Run Red**

Run: `python3 -m pytest backend/tests/persistence/sqlite/core/test_file_policy.py backend/tests/persistence/sqlite/migrations/test_v1_0000.py -q`

Expected: FAIL because the production migration runner and enforced connection policy do not exist.

- [ ] **Step 3: Implement minimum production persistence**

Use the admitted SQLite/Alembic stack, reject `:memory:` and URI memory modes, make migration catalog checksum validation fail closed, and keep provider/module data absent.

- [ ] **Step 4: Run Green against a fresh real file**

Run: `python3 -m pytest backend/tests/persistence/sqlite/core backend/tests/persistence/sqlite/migrations -q`

Expected: PASS for create, reopen, compatibility refusal, immutable revision metadata, and exact PRAGMAs.

- [ ] **Step 5: Review and commit**

Review migration, recovery, portability, and path-permission impact; commit: `git commit -m "feat(data): add real sqlite foundation migration"`.

---

### Task 4: `ST-CONTRACT-002` — Loopback application factory and deterministic OpenAPI client

**Epic:** `EPIC-CONTRACT-01`

**Requirements / acceptance:** `NFR-API-001`, `NFR-API-002`, `NFR-COMP-001`; `FND-HTTP-001/002`, `FND-LIFE-001..003`, `FND-OAPI-001..003`, `FND-CLIENT-001`.

**Contracts:** `CTR-FND-002`, `CTR-FND-005`, and `CTR-FND-007` at V1.

**Files:**
- Create: `backend/src/agentmonitor/foundation/application.py`
- Create: `backend/src/agentmonitor/composition/bootstrap.py`
- Create: `backend/src/agentmonitor/api/app.py`
- Create: `backend/src/agentmonitor/api/v1/router.py`
- Create: `backend/tests/integration/foundation/test_loopback_app.py`
- Create: `contracts/openapi/agentmonitor-v1.json`
- Create: `frontend/src/generated/api/index.ts`
- Create: `tooling/foundation/openapi_client.py`

**Interfaces:**
- `create_application(settings: BootstrapConfigurationV1, components: ComponentFactorySetV1, build: BuildMetadataV1, lifecycle: LifecycleHooksV1) -> ASGIApp` has no import-time I/O and mounts only the approved `/api/v1` router.
- `generate_openapi_client(app_factory_ref: str, openapi_path: Path, client_dir: Path) -> OpenApiGenerationReceiptV1` emits deterministic OpenAPI 3 and strict TypeScript artifacts with source/tool hashes.

- [ ] **Step 1: Write the failing loopback contract test**

```python
def test_real_loopback_openapi_has_unique_versioned_operations(running_server: Server) -> None:
    response = urllib.request.urlopen(f"{running_server.origin}/openapi.json", timeout=2)
    document = json.load(response)
    ids = operation_ids(document)
    assert response.status == 200
    assert document["openapi"].startswith("3.")
    assert all(path.startswith("/api/v1") for path in document["paths"])
    assert len(ids) == len(set(ids))
```

- [ ] **Step 2: Run Red**

Run: `python3 -m pytest backend/tests/integration/foundation/test_loopback_app.py -q`

Expected: FAIL because no production server can yet start from validated configuration and expose its real schema.

- [ ] **Step 3: Implement the smallest running skeleton and generator**

Bind loopback only, open the real migrated SQLite file during lifecycle startup, shut down deterministically, and generate artifacts from production routes. Do not add a health, status, or telemetry route merely to populate the schema.

- [ ] **Step 4: Run Green and deterministic generation**

Run: `python3 -m pytest backend/tests/integration/foundation/test_loopback_app.py -q && python3 tooling/foundation/openapi_client.py --check`

Expected: PASS; a second generation produces no diff and the generated TypeScript compiles under the admitted frontend toolchain.

- [ ] **Step 5: Review and commit**

Confirm the integration steward authored generated outputs and commit: `git commit -m "feat(api): add loopback app and generated client"`.

---

### Task 5: `ST-FND-002` — Built browser shell and canonical milestone automation

**Epic:** `EPIC-FND-01`

**Requirements / acceptance:** `NFR-API-002`, `NFR-TEST-001`, `NFR-TEST-002`, `NFR-DOC-001`, `NFR-LIC-001`, `AC-TEST-001/002/004/006`; `FND-UI-001/002`, `FND-TEST-001`, `FND-CI-001/002`.

**Contracts:** `CTR-FND-005`, `CTR-FND-007`, `CTR-FND-008`, and `CTR-UI-001` at V1.

**Files:**
- Create: `frontend/src/app/App.tsx`
- Create: `frontend/src/shared/api/client.ts`
- Create: `frontend/tests/browser/foundation/shell.spec.ts`
- Create: `tools/automation/implementations/auto_test.py`
- Create: `tools/automation/implementations/auto_quality.py`
- Create: `tools/automation/implementations/auto_build.py`
- Modify: `tools/automation/routines.toml`
- Modify: `tools/automation/test_run.py`
- Create: `.gitlab-ci.yml`

**Interfaces:**
- `App` renders only build/onboarding state obtained through `frontend/src/shared/api/client.ts`; it imports no backend, database, or provider file.
- `tools/automation/run.py` remains the sole dispatcher and loads `AUTO-TEST`, `AUTO-QUALITY`, and `AUTO-BUILD` from `tools/automation/routines.toml`; each catalog entry resolves to its automation-steward implementation under `tools/automation/implementations/`.
- Canonical routines fail closed, classify unexecuted live boundaries as `Not Run` or `Blocked`, and emit `TestEvidenceSummaryV1`.

- [ ] **Step 1: Write the failing built-browser and canonical-catalog tests**

```typescript
test("loads the production shell without invented telemetry", async ({ page }) => {
  await page.goto(process.env.AGENTMONITOR_TEST_ORIGIN!);
  await expect(page.getByRole("heading", { name: "AgentMonitor" })).toBeVisible();
  await expect(page.getByText(/quota|token usage|running agents/i)).toHaveCount(0);
});
```

```python
def test_m1_routines_resolve_from_canonical_catalog(self) -> None:
    catalog = load_catalog(REPOSITORY_ROOT)
    self.assertEqual(
        ["python3", "tools/automation/implementations/auto_test.py"],
        catalog["AUTO-TEST"]["implementation_command"],
    )
    self.assertEqual(
        ["python3", "tools/automation/implementations/auto_quality.py"],
        catalog["AUTO-QUALITY"]["implementation_command"],
    )
    self.assertEqual(
        ["python3", "tools/automation/implementations/auto_build.py"],
        catalog["AUTO-BUILD"]["implementation_command"],
    )
    self.assertEqual([], validate_catalog(REPOSITORY_ROOT, catalog))
```

- [ ] **Step 2: Run Red**

Run:

```bash
python3 -m unittest tools.automation.test_run.AutomationRoutineTests.test_m1_routines_resolve_from_canonical_catalog
npm --prefix frontend run build && npx --prefix frontend playwright test frontend/tests/browser/foundation/shell.spec.ts
```

Expected: the catalog test FAILS because the three M1 routines do not yet resolve to their production implementations, and the browser test FAILS because the production build and same-origin shell are not yet served.

- [ ] **Step 3: Implement the minimum shell and fail-closed routines**

Serve the built artifact from the real loopback app and use only the generated client through the wrapper. Implement the three PLAN-FND routine entry points, update only their entries in `tools/automation/routines.toml`, and make CI and milestone commands invoke them exclusively through `python3 tools/automation/run.py <AUTO-ID>`; do not add a bypass dispatcher or duplicate catalog.

- [ ] **Step 4: Run the complete milestone gate**

Run:

```bash
python3 -m unittest tools.automation.test_run.AutomationRoutineTests.test_m1_routines_resolve_from_canonical_catalog
python3 tools/automation/run.py AUTO-TEST
python3 tools/automation/run.py AUTO-QUALITY
python3 tools/automation/run.py AUTO-BUILD
python3 tools/automation/run.py AUTO-DOCS-CHECK
```

Expected: exit `0`; real SQLite, loopback HTTP, OpenAPI/client determinism, production frontend build, and real-browser evidence are present. A hosted CI row remains `Not Run` until an actual pipeline succeeds.

- [ ] **Step 5: Review, document, and commit**

Record requirement/AC IDs, V1 contract versions, Red/Green commands, real-boundary status, security/privacy/migration/license/docs impact, and files changed using `docs/templates`; commit: `git commit -m "feat(foundation): complete v1 m1 local skeleton"`.

## Completion rule

`V1-M1` is complete only when all five Stories are reviewed and the Task 5 milestone gate passes on the real checkout. Missing hosted CI, browser, SQLite, build, or migration evidence is reported as intermediate status, never as completion.
