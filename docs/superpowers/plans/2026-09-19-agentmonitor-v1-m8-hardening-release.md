# AgentMonitor V1-M8 Hardening and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install AgentMonitor as a recoverable native Linux user service, harden the complete real application, and produce a fail-closed V1 release decision with every mandatory acceptance result visible.

**Architecture:** PLAN-DEP owns immutable release artifacts and fixed-service lifecycle; M08 owns application maintenance intent, health, backup, restore, retention, export, diagnostics, and operational audit; PLAN-DB alone snapshots and activates SQLite. P01/P02 expose safe operations without a browser restore action, while PLAN-INT aggregates candidate-bound evidence and makes `AUTO-RELEASE` the sole completion gate.

**Tech Stack:** Python, FastAPI/OpenAPI 3, real file-backed SQLite/Alembic, standard-library streaming/checksum/archive primitives where approved, React/TypeScript, generated API client, real browser/accessibility tooling, XDG paths, and real non-root `systemd --user`.

**Spec:** `docs/product/v1-specification.md`

## Global Constraints

- Milestone `V1-M8`; Epics `EPIC-DEP-01`, `EPIC-HARDEN-01`, and `EPIC-RELEASE-01`.
- Scope ownership: M8 closes the complete cross-provider matrices, dashboard,
  deployment and recovery behavior, natural-time scenarios, universal
  test/security/documentation controls, and final V1 acceptance. Earlier
  milestones contribute evidence without passing these release-wide rows.
- Requirements: `FR-HIST-001/003/004/005`, `FR-OPS-001..006`, `FR-UI-001..007`, `FR-SAFE-001/002`, and every V1 NFR. Release criteria: every mandatory `AC-V1-*`, `AC-LIVE-*`, `AC-UI-*`, `AC-PROC-*`, `AC-ALERT-*`, `AC-HIST-*`, `AC-OPS-*`, and `AC-TEST-*` row.
- Before implementation, require `IC-2`, Approved PLAN-M08/DEP/DB/P01/P02/INT contracts, admitted dependency/tool versions, exact path/migration/shared-writer allocation, approved destructive-isolation packets, a real Linux owner window, and required provider/browser resources.
- Detached M0 reviewer approvals are advisory and never block M8 execution or
  the local hardening run. `AUTO-RELEASE` still fails closed on missing real
  technical, security, migration, browser, deployment, or acceptance evidence.
- Follow `docs/plans/modules/m08-operations/plan-v1.md`, `docs/plans/deployment/linux-native/plan-v1.md`, `docs/plans/persistence/sqlite/plan-v1.md`, `docs/plans/ui/react-dashboard/plan-v1.md`, and `docs/plans/integration/v1-plan.md`; this plan selects execution slices and does not replace their detailed state machines or scenarios.
- All filesystem, SQLite, HTTP, browser, platform, service, provider, backup, restore, upgrade, and release claims use real production paths. No mocks, fakes, stubs, emulators, recordings, in-memory SQLite, seeded telemetry, direct table insertion, demo accounts, test-only services, or sample dashboard values.
- Run as the normal user. Reject root, sudo, system services, broad permissions, unsafe XDG roots, remote bind, wildcard CORS, lingering mutation, arbitrary unit/action/path/PID input, runtime dependency download, and provider/agent control.
- `.env`, provider profiles, database, backups, exports, logs, evidence, and owner data never enter release bundles. Upgrade/uninstall preserve them; no V1 purge-data operation exists.
- M08 never queries another module's table. Retention, export, and consistency use `CTR-OPS-007`; backup/restore uses `CTR-DB-003` and `CTR-DEP-001`; restored M01 sessions/tokens are invalidated before readiness.
- A valid backup is a finalized real SQLite snapshot with checksum, full integrity, safe manifest, owner-only permissions, and a catalog receipt. Restore stages and validates a new database, preserves the current database, and resumes normal service only after restricted-mode checks.
- Natural 7-daily/4-weekly/12-monthly and 365-day evidence is never accelerated with patched clocks, backdated rows, or test-only retention. Missing elapsed-time/platform/provider conditions remain Blocked.
- Performance evidence uses exactly 100 production-registered accounts and 200 simultaneous real AgentMonitor-owned processes. It does not create fake provider telemetry or claim provider compatibility.
- Shared migration head, contracts, composition, automation dispatcher, OpenAPI, generated client, CI, build/version manifest, locks, SBOM/notices, and release artifacts have one assigned writer.
- No task publishes, tags, pushes, deploys to the owner's primary installation, restores, or performs a destructive scenario without the separately approved owner checkpoint. Dry release is non-publishing by default.
- Every Story records exact Red/Green/refactor commands, real boundary, safe evidence, cleanup, and all Failed/Blocked/Not Run rows. Only `AUTO-RELEASE` against the exact candidate can support a V1 completion claim.

---

## File map and contract seams

| Unit | Exact planned paths | Contract responsibility |
|---|---|---|
| Native package/preflight | `packaging/linux-native/bundle-layout-v1.toml`, `packaging/linux-native/agentmonitor.service.in`, `packaging/linux-native/launcher.in`, `packaging/linux-native/deployment-profile-v1.toml`, `tooling/automation/deployment/bundle.py`, `tooling/automation/deployment/preflight.py`, `tooling/automation/deployment/layout.py`, `tooling/automation/deployment/manifest.py`, `tooling/automation/deployment/journal.py` | PLAN-DEP producer of `CTR-DEP-001` bundle/target/status semantics |
| Native lifecycle | `tooling/automation/deployment/install.py`, `upgrade.py`, `rollback.py`, `uninstall.py`, `status.py`, `cli.py`, `evidence.py` | Fixed AgentMonitor service actions, artifact activation, quiescence receipts |
| Operations core | `backend/src/agentmonitor/contracts/operations_v1.py`, `backend/src/agentmonitor/modules/operations/domain/policies.py`, `backend/src/agentmonitor/modules/operations/application/health.py`, `backend/src/agentmonitor/modules/operations/application/diagnostics.py`, `backend/src/agentmonitor/modules/operations/application/workflows.py`, `backend/src/agentmonitor/modules/operations/ports/operations.py`, `backend/src/agentmonitor/adapters/persistence/operations/sqlite/repository.py`, `backend/migrations/versions/v1_0800_m08_operation_jobs.py`, `backend/migrations/versions/v1_0801_m08_backups.py`, `backend/migrations/versions/v1_0802_m08_artifacts.py`, `backend/migrations/versions/v1_0803_m08_retention_health.py`, `backend/migrations/versions/v1_0804_m08_event_outbox.py` | Extends the M4-created operations contract/application package; M08 produces the remaining `CTR-OPS-001..007` and `CTR-APP-001` behavior without a parallel application module |
| Operations artifacts/API/UI | `backend/src/agentmonitor/adapters/operations/artifacts.py`, `backend/src/agentmonitor/api/v1/schemas/operations.py`, `backend/src/agentmonitor/api/v1/routers/operations.py`, `frontend/src/features/diagnostics/OperationsPage.tsx` | Safe backup/export/diagnostic resources; no restore-execute HTTP/UI action |
| Hardening evidence | `backend/tests/integration/release/test_scale_resilience_live.py`, `frontend/tests/browser/release/hardening.spec.ts`, `docs/releases/v1-hardening-report.md` | Exact scale, accessibility, resilience, security, privacy, license evidence |
| Release | `tooling/automation/integration/evidence.py`, `tooling/automation/release/manifest.py`, `tooling/automation/release/gate.py`, `backend/tests/integration/release/test_release_gate.py`, `docs/releases/v1.0.0.md`, `docs/releases/v1.0.0-known-limitations.md` | PLAN-INT `CTR-INT-001..006`, candidate manifest, fail-closed `AUTO-RELEASE` |

Restore ordering is fixed: M08 maintenance intent → DEP quiescence receipt → DB staged validation/activation receipt → every required `CTR-OPS-007` staged receipt including M01 credential invalidation → DEP restricted start → post-activation participant receipts → M08 readiness → DEP normal resume. No owner may infer or skip another owner's receipt.

### Task 1: ST-DEP-001 — Build and preflight the native Linux release

**Epic:** `EPIC-DEP-01`

**Files:**
- Create: `packaging/linux-native/bundle-layout-v1.toml`
- Create: `packaging/linux-native/agentmonitor.service.in`
- Create: `packaging/linux-native/launcher.in`
- Create: `packaging/linux-native/deployment-profile-v1.toml`
- Create: `tooling/automation/deployment/bundle.py`
- Create: `tooling/automation/deployment/preflight.py`
- Create: `tooling/automation/deployment/layout.py`
- Create: `tooling/automation/deployment/manifest.py`
- Create: `tooling/automation/deployment/journal.py`
- Create: `backend/tests/deployment/linux_native/test_bundle_live.py`
- Create: `backend/tests/deployment/linux_native/test_layout_live.py`

**Interfaces:** Implements `ValidateReleaseBundleV1` and `InspectDeploymentTargetV1`; consumes approved build metadata, `CTR-PLAT-001` safe path/object primitives, schema compatibility, and exact XDG target identity. Produces a read-only preflight receipt and no service/database mutation.

**Contracts:** Produces the bundle, deployment-target, and preflight portions of `CTR-DEP-001`; consumes `CTR-PLAT-001`, `CTR-FND-001..008`, `CTR-DB-001/003`, and `CTR-INT-001..006`, all at V1.

**Traceability:** `FR-OPS-001/005/006`, `FR-IAM-007`, `NFR-PLAT-001`; `DEP-BUILD-001..012`, `DEP-FS-001..014`, `DEP-INSTALL-001`; `AC-V1-003/005/007`, `AC-OPS-001`.

- [ ] **Step 1: Write failing real build/filesystem tests** that assemble from the locked production build, validate a closed member manifest/digests/SBOM/notices, reject traversal/link/special/unmanifested members, resolve isolated real XDG roots, reject root/wrong owner/mode/symlink/cross-device/low-space targets, and prove preflight creates nothing.

```python
def test_preflight_rejects_symlink_escape_without_writes(real_linux_target) -> None:
    before = real_linux_target.inventory()
    result = inspect_deployment_target(real_linux_target.symlink_escape_case())
    assert result.code == "deployment_path_escape"
    assert real_linux_target.inventory() == before
```

- [ ] **Step 2: Run Red:**

```bash
python3 -m pytest backend/tests/deployment/linux_native/test_bundle_live.py -q
python3 -m pytest backend/tests/deployment/linux_native/test_layout_live.py -q
```

Expected: FAIL because bundle validation and read-only target preflight do not exist. Missing admitted build/platform tools are Blocked.

- [ ] **Step 3: Implement minimum bundle/layout/preflight behavior** with exact versioned members, canonical digests, immutable release IDs, normal-user owner-only XDG objects, held-reference path checks, same-filesystem atomicity checks, explicit `XDG_RUNTIME_DIR`, loopback profile validation, and a sanitized fsynced deployment journal. Never open `.env` or scan provider/home paths.

- [ ] **Step 4: Run Green/refactor:**

```bash
python3 -m pytest backend/tests/deployment/linux_native/test_bundle_live.py -q
python3 -m pytest backend/tests/deployment/linux_native/test_layout_live.py -q
python3 tools/automation/run.py AUTO-BUILD
python3 tools/automation/run.py AUTO-QUALITY
```

Expected: two clean real builds satisfy the approved reproducibility policy; preflight negative/clean cases pass and leave no writes; bundle/security/license scans are clean.

- [ ] **Step 5: Commit:**

```bash
git add packaging/linux-native/bundle-layout-v1.toml packaging/linux-native/agentmonitor.service.in packaging/linux-native/launcher.in packaging/linux-native/deployment-profile-v1.toml tooling/automation/deployment/bundle.py tooling/automation/deployment/preflight.py tooling/automation/deployment/layout.py tooling/automation/deployment/manifest.py tooling/automation/deployment/journal.py backend/tests/deployment/linux_native/test_bundle_live.py backend/tests/deployment/linux_native/test_layout_live.py
git commit -m "feat(deploy): add native bundle and target preflight"
```

### Task 2: ST-DEP-002 — Install, operate, upgrade, and recover the fixed user service

**Epic:** `EPIC-DEP-01`

**Files:**
- Create: `tooling/automation/deployment/install.py`
- Create: `tooling/automation/deployment/upgrade.py`
- Create: `tooling/automation/deployment/rollback.py`
- Create: `tooling/automation/deployment/uninstall.py`
- Create: `tooling/automation/deployment/status.py`
- Create: `tooling/automation/deployment/cli.py`
- Create: `tooling/automation/deployment/evidence.py`
- Create: `backend/tests/deployment/linux_native/test_install_live.py`
- Create: `backend/tests/deployment/linux_native/test_service_live.py`
- Create: `backend/tests/deployment/linux_native/test_upgrade_live.py`
- Create: `backend/tests/deployment/linux_native/test_rollback_live.py`
- Create: `backend/tests/deployment/linux_native/test_uninstall_live.py`
- Create: `docs/operations/install-linux.md`
- Create: `docs/operations/upgrade-linux.md`
- Create: `docs/operations/uninstall-linux.md`
- Create: `docs/operations/deployment-recovery-linux.md`

**Interfaces:** Implements the remaining `CTR-DEP-001` lifecycle ports: install/upgrade/repair/rollback/uninstall-preserve-data, start/stop/restart/status, enable/disable-at-login, quiesce/resume, and required-component manifest. Consumes typed M08/DB/IAM/P01/P02 receipts; never issues business/database work itself.

**Contracts:** Produces lifecycle, quiescence, activation, rollback, uninstall, and status operations in `CTR-DEP-001`; consumes `CTR-API-001`, `CTR-DB-001/003`, `CTR-IAM-004/008`, `CTR-OPS-001/002/003/006/007`, `CTR-PLAT-001`, and `CTR-UI-001`, all at V1.

**Traceability:** `FR-OPS-001..006`, `FR-SAFE-002`; `DEP-INSTALL-002..010`, `DEP-SVC-001..014`, `DEP-NET-001..010`, `DEP-UPG-001..014`, `DEP-REC-001..010`, `DEP-UNINSTALL-001..008`; `AC-OPS-001..005`.

- [ ] **Step 1: Write failing T5/T7 tests** against an approved isolated normal-user installation and real `systemd --user`. Cover install/start/stop/restart/status/login-autostart, browser closure, loopback/Host/Origin, fixed unit/actions, graceful drain, crash loop, upgrade backup/quiescence/migration/restricted start, activation failure, compatible rollback, preserve-data uninstall/reinstall, lingering unchanged, `.env` bytes unchanged, and provider agents unchanged.

```python
def test_browser_close_does_not_stop_collection(installed_candidate, browser) -> None:
    before = installed_candidate.latest_collection_run_id()
    browser.close()
    after = installed_candidate.wait_for_new_collection_run(after_id=before)
    assert after != before
    assert installed_candidate.service_status().is_running
```

- [ ] **Step 2: Run Red:**

```bash
python3 -m pytest backend/tests/deployment/linux_native/test_install_live.py -q
python3 -m pytest backend/tests/deployment/linux_native/test_service_live.py -q
python3 -m pytest backend/tests/deployment/linux_native/test_upgrade_live.py backend/tests/deployment/linux_native/test_rollback_live.py backend/tests/deployment/linux_native/test_uninstall_live.py -q
```

Expected: FAIL for missing lifecycle behavior. No real user manager, prior candidate, approved interruption packet, or owner window is Blocked, not Red.

- [ ] **Step 3: Implement the fixed lifecycle** using immutable release generations, exact unit template, fenced journal, atomic active reference, typed M08/DB receipts, explicit restricted/normal modes, bounded restart policy, offline install, rollback-class precomputation, and exact manifest-owned uninstall. No arbitrary command/unit/path/PID or data purge surface.

- [ ] **Step 4: Run Green/refactor:**

```bash
python3 -m pytest backend/tests/deployment/linux_native/test_install_live.py -q
python3 -m pytest backend/tests/deployment/linux_native/test_service_live.py -q
python3 -m pytest backend/tests/deployment/linux_native/test_upgrade_live.py backend/tests/deployment/linux_native/test_rollback_live.py backend/tests/deployment/linux_native/test_uninstall_live.py -q
python3 tools/automation/run.py AUTO-DEPLOY
```

Expected: real authorized lifecycle paths pass; failure/interruption resolves to rollback or `recovery_required`; provider profiles/processes and owner data are unchanged; missing natural/login/prior-version cases remain visible.

- [ ] **Step 5: Exercise only implemented commands and synchronize runbooks:** `python3 tools/automation/run.py AUTO-DOCS-CHECK`

Expected: all documented deployment commands resolve to the verified command registry; no proposed command is presented as executable.

- [ ] **Step 6: Commit:**

```bash
git add tooling/automation/deployment/install.py tooling/automation/deployment/upgrade.py tooling/automation/deployment/rollback.py tooling/automation/deployment/uninstall.py tooling/automation/deployment/status.py tooling/automation/deployment/cli.py tooling/automation/deployment/evidence.py backend/tests/deployment/linux_native/test_install_live.py backend/tests/deployment/linux_native/test_service_live.py backend/tests/deployment/linux_native/test_upgrade_live.py backend/tests/deployment/linux_native/test_rollback_live.py backend/tests/deployment/linux_native/test_uninstall_live.py docs/operations/install-linux.md docs/operations/upgrade-linux.md docs/operations/uninstall-linux.md docs/operations/deployment-recovery-linux.md
git commit -m "feat(deploy): add native service lifecycle and recovery"
```

### Task 3: ST-HARDEN-001 — Implement operations, backup, retention, export, and restore

**Epic:** `EPIC-HARDEN-01`

**Files:**
- Modify: `backend/src/agentmonitor/contracts/operations_v1.py`
- Create: `backend/src/agentmonitor/modules/operations/domain/policies.py`
- Modify: `backend/src/agentmonitor/modules/operations/application/health.py`
- Modify: `backend/src/agentmonitor/modules/operations/application/diagnostics.py`
- Create: `backend/src/agentmonitor/modules/operations/application/workflows.py`
- Create: `backend/src/agentmonitor/modules/operations/ports/operations.py`
- Create: `backend/src/agentmonitor/adapters/persistence/operations/sqlite/repository.py`
- Create: `backend/src/agentmonitor/adapters/operations/artifacts.py`
- Create: `backend/migrations/versions/v1_0800_m08_operation_jobs.py`
- Create: `backend/migrations/versions/v1_0801_m08_backups.py`
- Create: `backend/migrations/versions/v1_0802_m08_artifacts.py`
- Create: `backend/migrations/versions/v1_0803_m08_retention_health.py`
- Create: `backend/migrations/versions/v1_0804_m08_event_outbox.py`
- Modify: `backend/migrations/catalog.toml`
- Create: `backend/tests/operations/test_operations_policies.py`
- Create: `backend/tests/integration/operations/test_operations_repository_live.py`
- Create: `backend/tests/integration/operations/test_backup_restore_live.py`
- Create: `backend/tests/integration/operations/test_retention_export_live.py`
- Create: `docs/operations/backup-recovery.md`
- Create: `docs/operations/diagnostics-exports.md`

**Interfaces:** Modifies the M4-created `operations_v1.py` contract and its `modules/operations/application/` health/diagnostics seams; produces the remaining `CTR-OPS-001..007` and `CTR-APP-001` behavior through that package. Consumes registered leaf health ports, Foundation configuration/build metadata, `CTR-DB-001..003`, `CTR-DEP-001`, `CTR-PLAT-001`, M01 authorization/invalidation, and module-owned `CTR-OPS-007` participants.

**Contracts:** Produces `CTR-APP-001` and `CTR-OPS-001..007`; consumes `CTR-DB-001..003`, `CTR-DEP-001`, `CTR-IAM-001/002/004/005/008`, `CTR-PLAT-001`, `CTR-CONFIG-001`, `CTR-FND-001/003/004/006/007/008`, and every registered module's `CTR-OPS-007` participant, all at V1.

**Traceability:** `FR-OPS-002..006`, `FR-HIST-001/003/004/005`; `M08-PURE-001..016`, `M08-DB-001..015`, `M08-FS-001..014`, `M08-LIFE-001..014`; `AC-HIST-002`, `AC-OPS-002..005`, `AC-V1-004/007`.

- [ ] **Step 1: Write failing pure tests** for required/optional health/readiness, expired samples, job/fencing/idempotency transitions, exact UTC 365-day cutoff, GFS union selection, held backups, checkpoint-before-purge, closed artifact schemas, and safe configuration presence. Pure tests receive explicit `as_of` and do no I/O.

```python
def test_retention_requires_safe_checkpoint() -> None:
    state = RetentionCycleV1.previewed(cycle_id="cycle-1", preview_digest="digest-1")
    with pytest.raises(RetentionCheckpointRequired):
        state.begin_purge(checkpoint=None)
```

- [ ] **Step 2: Run Red:** `python3 -m pytest backend/tests/operations/test_operations_policies.py -q`

Expected: FAIL on missing M08 policies.

- [ ] **Step 3: Implement the minimum pure operations core** in `domain/policies.py`, extend the existing M4 `application/health.py` and `application/diagnostics.py`, and add orchestration only in `application/workflows.py` with ports in `ports/operations.py`. Cover deterministic health/readiness, job/fencing transitions, GFS and 365-day policy, checkpoint rules, closed safe errors, and typed ports. Do not add persistence or create a competing `modules/operations/application.py` module in this step.

- [ ] **Step 4: Run pure Green/refactor:** `python3 -m pytest backend/tests/operations/test_operations_policies.py -q && python3 tools/automation/run.py AUTO-QUALITY`

Expected: pure policy scenarios pass and exact critical mutants are killed by the admitted quality gate.

- [ ] **Step 5: Write failing real operational tests** that apply the complete migration chain, including the exact `v1_0800_m08_operation_jobs.py` through `v1_0804_m08_event_outbox.py` sequence, to a new file SQLite database and use real filesystem/service ports to exercise repository idempotency/fencing, online snapshot, checksum, full integrity, immutable catalog, GFS slots, safe export/checkpoint, bounded participant purge, staging restore, schema/module validation, M01 invalidation, DB activation, restricted start, rollback journal, and post-start checks. Naturally aged/GFS horizons remain Blocked until elapsed.

- [ ] **Step 6: Run Red:**

```bash
python3 -m pytest backend/tests/integration/operations/test_operations_repository_live.py -q
python3 -m pytest backend/tests/integration/operations/test_backup_restore_live.py -q
python3 -m pytest backend/tests/integration/operations/test_retention_export_live.py -q
```

Expected: FAIL because the M08 migration/repository and real workflows are missing; lack of an approved destructive target or natural-age data is Blocked.

- [ ] **Step 7: Implement persistence and workflows using PLAN-DB's exact frozen allocation:** `v1_0800_m08_operation_jobs.py` creates `ops_operation_job`, `ops_operation_job_step`, `ops_command_receipt`, and `ops_audit_event`; `v1_0801_m08_backups.py` creates `ops_backup` and `ops_backup_retention_slot`; `v1_0802_m08_artifacts.py` creates `ops_artifact`; `v1_0803_m08_retention_health.py` creates `ops_retention_cycle`, `ops_retention_participant`, and `ops_component_health_snapshot`; `v1_0804_m08_event_outbox.py` creates `ops_event_outbox` and final measured indexes. Create no competing revision and move no table between slots. Use job leases/fencing and typed ports only. Artifact finalization requires allowlist validation, checksum, safety scan, owner-only permissions, bounded streaming, and atomic catalog receipt. Restore accepts a catalog backup ID, never a free path; preserves the current database; and exposes no HTTP execute route.

- [ ] **Step 8: Run Green and canonical recovery routines:**

```bash
python3 -m pytest backend/tests/integration/operations/test_operations_repository_live.py -q
python3 -m pytest backend/tests/integration/operations/test_backup_restore_live.py -q
python3 -m pytest backend/tests/integration/operations/test_retention_export_live.py -q
python3 tools/automation/run.py AUTO-MIGRATE
python3 tools/automation/run.py AUTO-BACKUP
python3 tools/automation/run.py AUTO-RESTORE
```

Expected: actual available boundaries pass and every unavailable natural/destructive row is explicit; a scanner or integrity failure rejects the artifact/backup.

- [ ] **Step 9: Commit:**

```bash
git add backend/src/agentmonitor/contracts/operations_v1.py backend/src/agentmonitor/modules/operations/domain/policies.py backend/src/agentmonitor/modules/operations/application/health.py backend/src/agentmonitor/modules/operations/application/diagnostics.py backend/src/agentmonitor/modules/operations/application/workflows.py backend/src/agentmonitor/modules/operations/ports/operations.py backend/src/agentmonitor/adapters/persistence/operations/sqlite/repository.py backend/src/agentmonitor/adapters/operations/artifacts.py backend/migrations/catalog.toml backend/migrations/versions/v1_0800_m08_operation_jobs.py backend/migrations/versions/v1_0801_m08_backups.py backend/migrations/versions/v1_0802_m08_artifacts.py backend/migrations/versions/v1_0803_m08_retention_health.py backend/migrations/versions/v1_0804_m08_event_outbox.py backend/tests/operations/test_operations_policies.py backend/tests/integration/operations/test_operations_repository_live.py backend/tests/integration/operations/test_backup_restore_live.py backend/tests/integration/operations/test_retention_export_live.py docs/operations/backup-recovery.md docs/operations/diagnostics-exports.md
git commit -m "feat(operations): add recovery and retention workflows"
```

### Task 4: ST-HARDEN-002 — Expose operations and close UI, scale, security, and license findings

**Epic:** `EPIC-HARDEN-01`

**Files:**
- Modify: `backend/src/agentmonitor/api/v1/schemas/operations.py`
- Modify: `backend/src/agentmonitor/api/v1/routers/operations.py`
- Create: `backend/tests/integration/api/test_operations_http.py`
- Modify: `contracts/openapi/agentmonitor-v1.json`
- Regenerate: `frontend/src/generated/api/index.ts`
- Modify: `frontend/src/shared/api/client.ts`
- Create: `frontend/src/features/diagnostics/OperationsPage.tsx`
- Create: `frontend/tests/browser/p02/operations.spec.ts`
- Create: `backend/tests/integration/release/test_scale_resilience_live.py`
- Create: `frontend/tests/browser/release/hardening.spec.ts`
- Create: `docs/releases/v1-hardening-report.md`

**Interfaces:** P01 consumes M08 health/readiness/version/backup/export/diagnostic/audit ports and bounded artifact streams. P02 consumes generated operations only. Hardening consumes public ports and canonical evidence through a fail-closed finding/dispatch gate: every defect is assigned to a bounded follow-up Story in its approved owning plan, and this Story does not patch another module's internals.

**Contracts:** Consumes `CTR-APP-001`, `CTR-OPS-001..005`, `CTR-API-001..003`, `CTR-COMMON-005`, and `CTR-IAM-001..007`; regenerates the `CTR-UI-001` client at V1 without changing producer semantics.

**Traceability:** `FR-OPS-002..006`, `FR-UI-001..007`, all V1 NFRs; `M08-HTTP-001..010`, `M08-BROWSER-001..005`, `UI-OPS-001..012`, `INT-UI-001..012`, `INT-PERF-001..008`, `INT-SEC-001..012`, `INT-LIC-001..007`; `AC-V1-003/005/007/008`, `AC-UI-003..006`, `AC-TEST-002/003/005`.

- [ ] **Step 1: Write failing real HTTP/browser tests** for authenticated health/readiness/version, idempotent backup/export jobs, safe no-store downloads, diagnostics/config presence, maintenance, partial components, accessibility/responsiveness, and explicit proof that restore execution is absent from API/UI.

```typescript
test("operations page has safe actions and no restore execution", async ({ page }) => {
  await loginThroughProductionFlow(page);
  await page.goto("/diagnostics");
  await expect(page.getByRole("heading", { name: "System health" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create backup" })).toBeEnabled();
  await expect(page.getByRole("button", { name: /restore/i })).toHaveCount(0);
  await expectNoFilesystemPathOrSecretValue(page);
});
```

- [ ] **Step 2: Run Red:**

```bash
python3 -m pytest backend/tests/integration/api/test_operations_http.py -q
npm --prefix frontend run test:browser -- --grep "operations page"
```

Expected: FAIL because routes/UI are incomplete. Missing real jobs/artifacts/browser is Blocked.

- [ ] **Step 3: Implement transport and UI** with exact P01 operation IDs from the API plan, generated schemas/client, job resources, authorization/idempotency/ETag rules, bounded streams, explicit field states, and accessible non-color explanations. No public restore execution or generic settings/file/log endpoint.

- [ ] **Step 4: Run HTTP/browser Green and regenerate:**

```bash
python3 -m pytest backend/tests/integration/api/test_operations_http.py -q
npm --prefix frontend run test:browser -- --grep "operations page"
python3 tools/automation/run.py AUTO-BUILD
```

Expected: running server, generated client, and built browser agree; no path/secret/raw log appears.

- [ ] **Step 5: Write and run the hardening finding gate** against exactly 100 production-registered accounts and 200 simultaneous real owned processes, real SQLite/API/browser load, one real isolated component failure, 1920×1080 and defined responsive viewports, keyboard/AT/zoom/reduced-motion, and full source/artifact/dependency inventories.

Run the real-boundary Red before any correction:

```bash
python3 -m pytest backend/tests/integration/release/test_scale_resilience_live.py -q
npm --prefix frontend run test:browser -- --grep "release hardening"
```

Expected: a targeted missing behavior FAILS for a measured budget, accessibility, resilience, security, privacy, dependency, or license assertion. Unavailable exact scale/AT/platform state is Blocked. Each failure emits a sanitized finding containing the exact failing command/assertion, requirement and AC IDs, real boundary, owning module and approved plan, contract-impact assessment, and proposed exact write set; it does not authorize a fix.

- [ ] **Step 6: Dispatch every finding before M8 resumes.** Create one bounded follow-up Story with a unique `ST-HARDEN-FOLLOWUP-<OWNER>-NNN` ID in the approved owning module plan for each finding; record its Epic, dependencies, exact files, contract/migration/shared-writer impact, real Red/Green commands, acceptance IDs, and review gate. The owning Story must obtain its own allocation and complete its own TDD and review. `ST-HARDEN-002` remains Blocked while any finding is undispatched or any dispatched Story is not accepted; do not repair undeclared files under this Story.

- [ ] **Step 7: Rerun Green only after every dispatched owning Story is accepted:**

```bash
python3 -m pytest backend/tests/integration/release/test_scale_resilience_live.py -q
npm --prefix frontend run test:browser -- --grep "release hardening"
python3 tools/automation/run.py AUTO-QUALITY
```

Expected: approved numeric budgets pass without provider-data claims; security/privacy/secret/prohibited-double/import/compatibility/mutation/dependency/license/SBOM/notices gates have no unresolved finding or blocker. Any recurrence creates a new dispatched follow-up and blocks M8 again.

- [ ] **Step 8: Commit:**

```bash
git add backend/src/agentmonitor/api/v1/schemas/operations.py backend/src/agentmonitor/api/v1/routers/operations.py backend/tests/integration/api/test_operations_http.py contracts/openapi/agentmonitor-v1.json frontend/src/generated/api/index.ts frontend/src/shared/api/client.ts frontend/src/features/diagnostics/OperationsPage.tsx frontend/tests/browser/p02/operations.spec.ts backend/tests/integration/release/test_scale_resilience_live.py frontend/tests/browser/release/hardening.spec.ts docs/releases/v1-hardening-report.md
git commit -m "feat(v1-m8): harden operations and dashboard"
```

### Task 5: ST-RELEASE-001 — Implement candidate evidence and fail-closed release automation

**Epic:** `EPIC-RELEASE-01`

**Files:**
- Create: `tooling/automation/integration/evidence.py`
- Create: `tooling/automation/release/manifest.py`
- Create: `tooling/automation/release/gate.py`
- Create: `backend/tests/integration/release/test_release_gate.py`
- Modify: `tools/automation/routines.toml`

**Interfaces:** Implements `CTR-INT-001..006` evidence status/catalog/start/completion/release semantics and `AUTO-RELEASE`; consumes immutable results from every canonical routine and producer handoff without rewriting their status.

**Contracts:** Produces `CTR-INT-001..006`; consumes `CTR-API-001..003`, `CTR-APP-001`, `CTR-DB-001/003`, `CTR-DEP-001`, `CTR-EVT-001`, `CTR-OPS-002..005/007`, and `CTR-UI-001` at their approved V1 versions.

**Traceability:** `AC-V1-001..008`, `AC-TEST-001/004/006`; `INT-AUTO-001..011`, `INT-REL-001..010`, `INT-TRACE-001..006`, `INT-EVID-001..004`.

- [ ] **Step 1: Write failing release-gate tests** proving a missing, stale, digest-mismatched, Failed, Blocked, Not Run, uncountersigned, or wrong-boundary mandatory row rejects the candidate; artifact/config/schema/OpenAPI/client/provider versions and checksums must bind to one candidate; dry mode cannot publish.

```python
def test_mandatory_blocked_live_row_rejects_candidate(
    real_blocked_candidate_catalog,
) -> None:
    result = evaluate_release_candidate(
        load_candidate_catalog(real_blocked_candidate_catalog.path)
    )
    assert result.state == "rejected"
    assert result.reason_codes == ("mandatory_evidence_not_passed",)
    assert result.blocking_ids == ("INT-LIVE-005",)
```

- [ ] **Step 2: Run Red:** `python3 -m pytest backend/tests/integration/release/test_release_gate.py -q`

Expected: FAIL because candidate aggregation and `AUTO-RELEASE` do not exist.

- [ ] **Step 3: Implement candidate-bound aggregation** with exact completeness catalog, four-state evidence, freshness/countersignature/digest checks, requirement/AC/contract closure, release artifact allowlist, schema/API/client/build/dependency identities, rollback matrix, and local dry assembly. Publication remains a separate unauthorized mode requiring owner/version/commit/remote/destination authority.

- [ ] **Step 4: Prove controlled Red then Green:**

```bash
python3 -m pytest backend/tests/integration/release/test_release_gate.py -q
python3 tools/automation/run.py AUTO-RELEASE
```

Expected: the test suite passes its controlled rejection cases; `AUTO-RELEASE` returns nonzero until every mandatory real result passes, then produces one non-publishing eligible dry-candidate receipt with exact artifact digests.

- [ ] **Step 5: Commit:**

```bash
git add tooling/automation/integration/evidence.py tooling/automation/release/manifest.py tooling/automation/release/gate.py tools/automation/routines.toml backend/tests/integration/release/test_release_gate.py
git commit -m "feat(release): add fail-closed V1 candidate gate"
```

### Task 6: ST-RELEASE-002 — Exercise the release candidate and record the V1 decision

**Epic:** `EPIC-RELEASE-01`

**Files:**
- Create: `docs/releases/v1.0.0.md`
- Create: `docs/releases/v1.0.0-known-limitations.md`
- Create: `docs/releases/v1.0.0-evidence.md`
- Create: `docs/releases/v1.0.0-rollback.md`

**Interfaces:** Consumes the exact candidate receipt plus T1–T7 evidence, migration/build/deploy/backup/restore receipts, provider owner countersignatures, reviews, and artifact scans. Produces an Eligible or Rejected decision; it creates no product behavior and does not publish. Its behavioral Red/Green evidence is the retained controlled rejection and eligibility proof produced by `ST-RELEASE-001`; this Story executes that gate against the candidate and does not invent a second implementation Red.

**Contracts:** Verifies the approved V1 versions of `CTR-INT-001..006`, `CTR-DB-001..003`, `CTR-DEP-001`, `CTR-APP-001`, `CTR-OPS-001..007`, `CTR-API-001..003`, `CTR-UI-001`, and every registered provider/module contract; it publishes no new product contract.

**Traceability:** `FR-ORG-001..003`, `FR-ACC-001..006`, `FR-AUTH-001..006`, `FR-QUOTA-001..006`, `FR-BUDGET-001..006`, `FR-DISC-001..008`, `FR-STATE-001..004`, `FR-COL-001..008`, `FR-HIST-001..005`, `FR-ALERT-001..006`, `FR-UI-001..007`, `FR-IAM-001..007`, `FR-OPS-001..006`, `FR-SAFE-001..002`; `NFR-ARCH-001`, `NFR-ARCH-002`, `NFR-API-001`, `NFR-API-002`, `NFR-DATA-001`, `NFR-TEST-001`, `NFR-TEST-002`, `NFR-SEC-001`, `NFR-PRIV-001`, `NFR-PRIV-002`, `NFR-DOC-001`, `NFR-LIC-001`, `NFR-PLAT-001`, `NFR-PERF-001`, `NFR-RES-001`, `NFR-OBS-001`, `NFR-COMP-001`; `AC-V1-001..008`, `AC-LIVE-001..007`, `AC-UI-001..006`, `AC-PROC-001..005`, `AC-ALERT-001..003`, `AC-HIST-001..002`, `AC-OPS-001..006`, `AC-TEST-001..006`; `INT-REL-001..010`, `INT-DOC-001..008`, `INT-OPS-001..014`, `INT-TEST-001..008`.

- [ ] **Step 1: Freeze one `1.0.0-rc.N` candidate** only after IC-3. Bind source, plan/contract baseline, database head, OpenAPI/client, backend/frontend/adapters, native bundle, lockfiles, SBOM/notices, evidence catalog, and rollback target digests. Any changed digest creates a new candidate.

- [ ] **Step 2: Run the complete non-publishing gate set:**

```bash
python3 tools/automation/run.py AUTO-PLAN-CHECK
python3 tools/automation/run.py AUTO-DOCS-CHECK
python3 tools/automation/run.py AUTO-TEST
python3 tools/automation/run.py AUTO-QUALITY
python3 tools/automation/run.py AUTO-GIT-PREFLIGHT
python3 tools/automation/run.py AUTO-BUILD
python3 tools/automation/run.py AUTO-MIGRATE
python3 tools/automation/run.py AUTO-DEPLOY
python3 tools/automation/run.py AUTO-BACKUP
python3 tools/automation/run.py AUTO-RESTORE
python3 tools/automation/run.py AUTO-RELEASE
```

Expected: each command reports its actual real boundary and exact exit code. Any mandatory Failed/Blocked/Not Run result rejects the candidate; hosted CI never supplies T5/T6/T7 credit.

- [ ] **Step 3: Exercise owner-controlled IC-4 evidence** on the exact installed candidate: native install/start/stop/restart/status/login-autostart; browser-closed collection; fresh and supported-prior migrations; real backup/checksum/integrity/staged restore/post-start login; rollback/failure recovery; all current provider matrices and authoritative comparisons; real browser/accessibility; scale/resilience; and prohibited-data/default-profile/no-control proof.

- [ ] **Step 4: Write release documents from actual receipts only.** `v1.0.0.md` lists changes/compatibility/migrations; `v1.0.0-known-limitations.md` lists every Unsupported/Blocked/Not Run item; `v1.0.0-evidence.md` maps every AC to safe evidence; `v1.0.0-rollback.md` records exact compatible artifact/backup recovery paths. Do not copy secrets, raw evidence, account identity, or machine paths.

- [ ] **Step 5: Rerun docs and release gates:** `python3 tools/automation/run.py AUTO-DOCS-CHECK && python3 tools/automation/run.py AUTO-RELEASE`

Expected: Eligible only when every mandatory AC is individually Passed and every artifact/review/rollback record matches the candidate. Otherwise record Rejected and the exact blockers without a completion claim.

- [ ] **Step 6: Commit the dry release record:**

```bash
git add docs/releases/v1.0.0.md docs/releases/v1.0.0-known-limitations.md docs/releases/v1.0.0-evidence.md docs/releases/v1.0.0-rollback.md
git commit -m "docs(release): record AgentMonitor V1 candidate"
```

Tagging, pushing, GitLab release creation, upload, deployment to the owner's primary installation, or public distribution requires a separate explicit owner instruction after this Story.

## V1-M8 exit gate

- [ ] `ST-DEP-001/002`, `ST-HARDEN-001/002`, and `ST-RELEASE-001/002` have specification-compliance and quality approval.
- [ ] Native non-root install, fixed user service, loopback transport, browser independence, upgrade, rollback, preserve-data uninstall, and recovery pass on the real target.
- [ ] Health/readiness, real backups, restore, export-before-purge, diagnostics, artifacts, audit, and version/config projections pass without cross-module table reads or prohibited data.
- [ ] Accessibility/responsiveness, exact 100-account/200-process scale, resilience, security/privacy, mutation, dependency/license, SBOM/notices, API/client/schema compatibility, and documentation gates pass.
- [ ] Every mandatory acceptance criterion is individually Passed at T1–T7 as required; every non-Passed row is visible and rejects release where mandatory.
- [ ] `AUTO-RELEASE` returns one Eligible receipt for the exact dry candidate. Publication remains separately authorized.

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-19-agentmonitor-v1-m8-hardening-release.md`. Execute one Story per approved write set with `superpowers:subagent-driven-development`, or inline with `superpowers:executing-plans` and a review checkpoint after every Story.
