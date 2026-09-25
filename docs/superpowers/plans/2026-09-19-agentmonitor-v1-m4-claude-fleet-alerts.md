# AgentMonitor V1-M4 Claude Fleet, Alerts, and Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the first complete AgentMonitor slice with six intended Claude accounts, durable organization grouping, real organization/account capacity and runtime views, actionable dashboard alerts, and sanitized operational health.

**Architecture:** A01 supplies typed provider evidence through M03; M02 owns organizations, identities, and membership snapshots; M04 schedules collection; M05 and M06 own capacity and runtime projections; M07 owns alerts; M08 owns health and diagnostics. P01 publishes versioned HTTP and P02 consumes only the generated client.

**Tech Stack:** Python, real Claude sources, FastAPI, file-backed SQLite/Alembic, OpenAPI 3, React/TypeScript, generated API client, Playwright, native Linux process inspection.

**Spec:** `docs/product/v1-specification.md`

## Global Constraints

- Milestone: `V1-M4`; epics: `EPIC-FLEET-01`, `EPIC-ALERT-01`, `EPIC-OPS-01`; entry gates: `V1-M3`, accepted Claude evidence, Approved affected plans/contracts, and allocated shared writers.
- Detached M0 reviewer approvals are advisory evidence only. M4 execution uses
  the current technical handoff and real boundary checks; it must not require
  a detached-approval authorization flag. Naturally unavailable accounts,
  providers, processes, and time windows remain Blocked or Not Run.
- Detailed authority remains in `docs/plans/integration/v1-planning-program.md`, `docs/plans/adapters/claude/plan-v1.md`, M02/M04/M05/M06/M07/M08, P01/P02, `docs/plans/contract-adoption.toml`, and `docs/plans/parallel-ownership.toml`.
- The reauthentication entry gate is A01 `CLA-I09 — managed reauth, separately authorized`. Before that named packet is Approved, M4 implements read-only authentication health only and records managed reauth as Blocked. After approval, only an AgentMonitor-managed isolated profile may use the official owner-driven flow; a default or uncertain profile is rejected before provider I/O and is never modified.
- Use real provider accounts/sources/processes, file-backed SQLite, loopback HTTP, and a built browser. No mocks, fakes, stubs, emulators, recordings, copied provider files, demo accounts, seeded telemetry, placeholder values, or in-memory SQLite.
- Never read or retain prompts, responses, source, arbitrary environments, secrets, raw provider payloads, unrestricted errors, or credentials. Never control an agent process.
- Missing owners or naturally absent provider states are Blocked or Not Run, never Passed. Unknown, Unsupported, Unavailable, Stale, Partial, Unresolved, and exact zero remain distinct.
- Shared composition, contracts, migrations, events, OpenAPI, generated client, configuration, and frontend shell are edited only by the writer named in `parallel-ownership.toml`.

---

## EPIC-FLEET-01 — First Complete Claude Fleet Slice

### Task 1: ST-FLEET-001 — Reconcile six accounts, organizations, and read-only auth health

**Requirements:** FR-ACC-001..006, FR-ORG-001..003, FR-AUTH-001/004/005, FR-SAFE-001/002; AC-LIVE-001/006/007, AC-UI-002..005.

**Contracts:** CTR-REG-001/002/005/006/007/008, CTR-PROV-005/006, CTR-API-001, CTR-UI-001.

**Files:**
- Modify: `backend/src/agentmonitor/modules/registry/application/organizations.py`
- Modify: `backend/src/agentmonitor/modules/registry/application/discovery.py`
- Modify: `backend/src/agentmonitor/modules/registry/application/accounts.py`
- Modify: `backend/src/agentmonitor/adapters/providers/claude/authentication/health.py`
- Create: `backend/src/agentmonitor/adapters/providers/claude/authentication/reauthentication.py`
- Modify: `backend/src/agentmonitor/api/v1/routers/registry.py`
- Modify: `backend/src/agentmonitor/composition/bootstrap.py`
- Create: `frontend/src/features/organizations/OrganizationsPage.tsx`
- Create: `frontend/src/features/accounts/AccountsPage.tsx`
- Generate: `contracts/openapi/agentmonitor-v1.json`
- Generate: `frontend/src/generated/api/index.ts`
- Test: `backend/tests/integration/registry/test_claude_fleet.py`
- Test: `backend/tests/api/v1/test_organization_routes.py`
- Test: `backend/tests/adapters/providers/claude/live/test_authentication.py`
- Test: `frontend/tests/browser/p02/organizations.spec.ts`

**Interfaces:** M02 consumes bounded `DiscoveryOutcomeV1` and `AuthHealthOutcomeV1`, then publishes `OrganizationViewV1`, `AccountViewV1`, `RegistryScopeSnapshotV1`, and ordered `AuthenticationHealthChangedV1`. Organization membership is registry truth; telemetry aggregation remains in M05/M06/M07.

- [ ] **Step 1: Write concrete real-boundary tests.** Add this body to `test_claude_fleet.py` and a corresponding real HTTP/browser assertion in the listed files:

```python
def test_six_intended_owners_have_truthful_organization_membership(real_claude_fleet, registry):
    outcomes = real_claude_fleet.reconcile_into(registry)
    assert len(outcomes) == 6
    assert {item.status for item in outcomes} <= {"reconciled", "owner_unavailable"}
    assert len({item.alias for item in outcomes}) == 6
    snapshot = registry.get_scope_snapshot(scope_kind="global")
    assert set(snapshot.account_ids) == {item.account_id for item in outcomes if item.status == "reconciled"}
    assert all(account.organization_id is not None or account.is_ungrouped for account in snapshot.accounts)

def test_default_profile_is_rejected_before_provider_io(real_claude_auth_boundary):
    before = real_claude_auth_boundary.default_profile_digest()
    result = real_claude_auth_boundary.request_reauthentication(
        target=real_claude_auth_boundary.default_profile_target
    )
    assert result.reason_code == "protected_default_profile"
    assert real_claude_auth_boundary.provider_invocation_count == 0
    assert real_claude_auth_boundary.default_profile_digest() == before
```

- [ ] **Step 2: Run Red with each boundary independently.** Backend: `python3 -m pytest backend/tests/integration/registry/test_claude_fleet.py backend/tests/api/v1/test_organization_routes.py backend/tests/adapters/providers/claude/live/test_authentication.py -vv`. Frontend: `npm --prefix frontend run test:browser -- tests/browser/p02/organizations.spec.ts`. Expected: each available boundary FAILS for the missing behavior; unavailable owners are recorded Blocked.
- [ ] **Step 3: Implement the minimum slice.** Persist organization membership and Ungrouped explicitly, expose the frozen organization operations, render real grouping, and map auth health without reading credentials. Create `reauthentication.py` with a fail-closed pre-I/O gate in every build; without the Approved `CLA-I09` packet it returns the typed unavailable decision and performs no provider I/O. Enable the official managed-profile flow only under that packet with expected-identity and wrong-account stop.
- [ ] **Step 4: Run Green with the exact commands.** Backend: `python3 -m pytest backend/tests/integration/registry/test_claude_fleet.py backend/tests/api/v1/test_organization_routes.py backend/tests/adapters/providers/claude/live/test_authentication.py -vv`. Frontend: `npm --prefix frontend run test:browser -- tests/browser/p02/organizations.spec.ts`. Expected: available cases PASS, all six owner outcomes are explicit, and the default profile digest is unchanged.
- [ ] **Step 5: Checkpoint the complete write set.** `git add backend/src/agentmonitor/modules/registry backend/src/agentmonitor/adapters/providers/claude/authentication backend/src/agentmonitor/api/v1/routers/registry.py backend/src/agentmonitor/composition/bootstrap.py frontend/src/features/organizations frontend/src/features/accounts contracts/openapi/agentmonitor-v1.json frontend/src/generated/api/index.ts backend/tests/integration/registry/test_claude_fleet.py backend/tests/api/v1/test_organization_routes.py backend/tests/adapters/providers/claude/live/test_authentication.py frontend/tests/browser/p02/organizations.spec.ts && git commit -m "feat(v1-m4): reconcile Claude organizations and auth health"`.

### Task 2: ST-FLEET-002 — Collect account and organization capacity with history

**Requirements:** FR-COL-001..008, FR-ORG-003, FR-QUOTA-001..006, FR-HIST-001/002/005; AC-LIVE-004/005/007, AC-HIST-001.

**Contracts:** CTR-REG-005/007, CTR-COL-001..007, CTR-CAP-001..009.

**Files:**
- Create: `backend/src/agentmonitor/modules/collection_control/application/scheduler.py`
- Modify: `backend/src/agentmonitor/modules/collection_control/application/runner.py`
- Modify: `backend/src/agentmonitor/modules/capacity/application/ingest.py`
- Modify: `backend/src/agentmonitor/modules/capacity/application/queries.py`
- Create: `backend/src/agentmonitor/modules/capacity/domain/forecast.py`
- Test: `backend/tests/capacity/pure/test_forecast_policy.py`
- Test: `backend/tests/integration/collection_control/test_claude_fleet_collection.py`
- Test: `backend/tests/integration/capacity/test_claude_history.py`
- Test: `backend/tests/integration/capacity/test_claude_organization_aggregates.py`

**Interfaces:** M04 consumes a revisioned `RegistryScopeSnapshotV1` and `CollectionOutcomeV1[T]`, then calls M05 `CollectionOutcomeCommitPortV1`. M05 derives `CapacityAggregateViewV1` for global, organization, provider, and account scopes without summing incompatible native windows.

- [ ] **Step 1: Write the concrete collection/aggregation test.** Add to `test_claude_organization_aggregates.py`:

```python
def test_real_claude_capacity_aggregates_follow_registry_membership(real_claude_collection, capacity_queries):
    run = real_claude_collection.collect_due_accounts()
    assert all(item.terminal for item in run.account_results)
    assert run.successful_account_ids.isdisjoint(run.failed_account_ids)
    for organization_id in real_claude_collection.expected_organization_ids:
        view = capacity_queries.get_aggregate(scope_kind="organization", scope_id=organization_id)
        expected_ids = real_claude_collection.account_ids_for(organization_id)
        assert set(view.covered_account_ids) <= expected_ids
        assert view.coverage.account_count == len(view.covered_account_ids)
        assert all(window.native_window_id for window in view.windows)
```

- [ ] **Step 2: Run Red.** `python3 -m pytest backend/tests/capacity/pure/test_forecast_policy.py backend/tests/integration/collection_control/test_claude_fleet_collection.py backend/tests/integration/capacity/test_claude_history.py backend/tests/integration/capacity/test_claude_organization_aggregates.py -vv`. Expected: FAIL on missing isolation, history, forecast, or organization coverage.
- [ ] **Step 3: Implement minimum Green.** Add bounded per-account execution, idempotent commits, immutable provenance, revisioned membership, explicit unavailable/partial states, and confidence-bearing forecasts. Never infer missing capacity or combine incompatible windows.
- [ ] **Step 4: Run Green.** `python3 -m pytest backend/tests/capacity/pure/test_forecast_policy.py backend/tests/integration/collection_control/test_claude_fleet_collection.py backend/tests/integration/capacity/test_claude_history.py backend/tests/integration/capacity/test_claude_organization_aggregates.py -vv`. Expected: PASS for available real accounts with isolated failures and correct organization coverage.
- [ ] **Step 5: Checkpoint.** `git add backend/src/agentmonitor/modules/collection_control backend/src/agentmonitor/modules/capacity backend/tests/capacity backend/tests/integration/collection_control backend/tests/integration/capacity && git commit -m "feat(v1-m4): aggregate Claude capacity by organization"`.

### Task 3: ST-FLEET-003 — Expose runtime, capacity, and history in the browser

**Requirements:** FR-DISC-001..008, FR-STATE-001..004, FR-UI-001..006, NFR-API-001/002; AC-PROC-001..005, AC-UI-002..006.

**Contracts:** CTR-RUN-001..007, CTR-CAP-003/004/006/007, CTR-API-001, CTR-UI-001.

**Files:**
- Modify: `backend/src/agentmonitor/modules/runtime_observation/application/ingest.py`
- Modify: `backend/src/agentmonitor/modules/runtime_observation/application/correlation.py`
- Modify: `backend/src/agentmonitor/modules/runtime_observation/application/queries.py`
- Modify: `backend/src/agentmonitor/api/v1/routers/capacity.py`
- Modify: `backend/src/agentmonitor/api/v1/routers/runtime.py`
- Modify: `backend/src/agentmonitor/composition/bootstrap.py`
- Modify: `frontend/src/features/organizations/OrganizationsPage.tsx`
- Create: `frontend/src/features/history/HistoryPage.tsx`
- Create: `frontend/src/features/sessions/SessionsPage.tsx`
- Generate: `contracts/openapi/agentmonitor-v1.json`
- Generate: `frontend/src/generated/api/index.ts`
- Test: `backend/tests/runtime_observation/integration/test_claude_process_tree.py`
- Test: `backend/tests/api/v1/test_fleet_routes.py`
- Test: `frontend/tests/browser/p02/fleet.spec.ts`

**Interfaces:** M06 consumes real A04 `ProcessSnapshotInputV1` and A01 `RuntimeObservationBatchV1`, publishes CTR-RUN views/events, and leaves weak/conflicting correlation unresolved. P01 maps frozen operation IDs; P02 imports generated client types only.

- [ ] **Step 1: Write concrete runtime and browser tests.** Add to `test_claude_process_tree.py`:

```python
def test_real_claude_tree_preserves_orphans_and_wait_semantics(real_claude_runtime, runtime_queries):
    receipt = real_claude_runtime.observe()
    tree = runtime_queries.get_tree(receipt.root_session_id)
    assert tree.is_acyclic
    assert set(tree.orphan_process_ids) == set(receipt.expected_orphan_process_ids)
    assert all(node.correlation_state != "resolved" for node in tree.nodes if node.evidence_conflict)
    assert all(not node.possible_stall for node in tree.nodes if node.runtime_state == "waiting_permission")
```

- [ ] **Step 2: Run Red separately.** Backend: `python3 -m pytest backend/tests/runtime_observation/integration/test_claude_process_tree.py backend/tests/api/v1/test_fleet_routes.py -vv`. Frontend: `npm --prefix frontend run test:browser -- tests/browser/p02/fleet.spec.ts`. Expected: both available boundaries FAIL for missing hierarchy/routes/pages.
- [ ] **Step 3: Implement through owned contracts.** Persist safe fields only, use the 600-second default stall policy, add capacity/runtime handlers, regenerate both artifacts through the shared writer, and render organization/account/history/session states without backend imports.
- [ ] **Step 4: Run Green separately.** Backend: `python3 -m pytest backend/tests/runtime_observation/integration/test_claude_process_tree.py backend/tests/api/v1/test_fleet_routes.py -vv`. Frontend: `npm --prefix frontend run test:browser -- tests/browser/p02/fleet.spec.ts`. Expected: available real process, HTTP, and browser cases PASS with no content leakage.
- [ ] **Step 5: Checkpoint.** `git add backend/src/agentmonitor/modules/runtime_observation backend/src/agentmonitor/api/v1/routers/capacity.py backend/src/agentmonitor/api/v1/routers/runtime.py backend/src/agentmonitor/composition/bootstrap.py frontend/src/features/organizations frontend/src/features/history frontend/src/features/sessions contracts/openapi/agentmonitor-v1.json frontend/src/generated/api/index.ts backend/tests/runtime_observation backend/tests/api/v1/test_fleet_routes.py frontend/tests/browser/p02/fleet.spec.ts && git commit -m "feat(v1-m4): expose Claude capacity and runtime"`.

---

## EPIC-ALERT-01 — Dashboard Alerting

### Task 4: ST-ALERT-001 — Implement alert contracts, three migrations, and event lifecycle

**Requirements:** FR-ALERT-001..005, FR-HIST-001..003; AC-ALERT-001/002, AC-HIST-002.

**Contracts:** Create CTR-ALERT-001..005 in `alerting_v1.py`; consume CTR-REG-009/010, CTR-COL-007, CTR-CAP-005/008/009, CTR-RUN-004/005, and CTR-EVT-001.

**Files:**
- Create: `backend/src/agentmonitor/contracts/alerting_v1.py`
- Create: `backend/src/agentmonitor/modules/alerting/domain/policy.py`
- Create: `backend/src/agentmonitor/modules/alerting/application/consume.py`
- Create: `backend/src/agentmonitor/modules/alerting/application/commands.py`
- Create: `backend/src/agentmonitor/adapters/persistence/alerting/sqlite/repository.py`
- Create: `backend/migrations/versions/v1_0700_m07_alert_rules.py`
- Create: `backend/migrations/versions/v1_0701_m07_alert_lifecycle.py`
- Create: `backend/migrations/versions/v1_0702_m07_alert_deadlines_outbox.py`
- Modify: `backend/migrations/catalog.toml`
- Test: `backend/tests/alerting/pure/test_policy.py`
- Test: `backend/tests/alerting/persistence/test_v1_0700_0702_alerting.py`
- Test: `backend/tests/integration/alerting/test_signal_lifecycle.py`

**Interfaces:** CTR-ALERT commands/views produce immutable alert state. `v1_0700` owns rule/revision tables, `v1_0701` owns alert/evidence/event/receipt tables, and `v1_0702` owns deadlines/reevaluation/outbox, with parents `v1_0603`, `v1_0700`, and `v1_0701` respectively.

- [ ] **Step 1: Write concrete policy and persistence tests.** Add to `test_signal_lifecycle.py`:

```python
def test_real_capacity_signal_is_atomic_and_idempotent(real_capacity_signal, alert_service, alert_repository):
    first = alert_service.consume(real_capacity_signal)
    duplicate = alert_service.consume(real_capacity_signal)
    stored = alert_repository.get(first.alert_id)
    assert first.receipt_id == duplicate.receipt_id
    assert stored.severity == "critical"
    assert stored.unread is True
    assert alert_repository.event_count(first.alert_id) == 1
    assert alert_repository.outbox_count(first.alert_id) == 1
```

- [ ] **Step 2: Run Red.** `python3 -m pytest backend/tests/alerting/pure/test_policy.py backend/tests/alerting/persistence/test_v1_0700_0702_alerting.py backend/tests/integration/alerting/test_signal_lifecycle.py -vv`. Expected: FAIL because contract, policy, migrations, repository, and consumer do not exist.
- [ ] **Step 3: Implement minimum Green.** Apply precedence account > provider > organization > global > built-in and inclusive 3000/1500 basis-point defaults. Recover only from a newer explicit producer generation; collection success alone never recovers. Commit receipt, transition, deadline, and outbox atomically.
- [ ] **Step 4: Run Green.** `python3 -m pytest backend/tests/alerting/pure/test_policy.py backend/tests/alerting/persistence/test_v1_0700_0702_alerting.py backend/tests/integration/alerting/test_signal_lifecycle.py -vv`. Expected: PASS against fresh and upgraded real SQLite files with the exact three-revision chain.
- [ ] **Step 5: Checkpoint.** `git add backend/src/agentmonitor/contracts/alerting_v1.py backend/src/agentmonitor/modules/alerting backend/src/agentmonitor/adapters/persistence/alerting/sqlite backend/migrations/catalog.toml backend/migrations/versions/v1_0700_m07_alert_rules.py backend/migrations/versions/v1_0701_m07_alert_lifecycle.py backend/migrations/versions/v1_0702_m07_alert_deadlines_outbox.py backend/tests/alerting backend/tests/integration/alerting && git commit -m "feat(v1-m4): add alert contracts and lifecycle"`.

### Task 5: ST-ALERT-002 — Deliver alert rules and console through HTTP and browser

**Requirements:** FR-ALERT-001..006, FR-UI-001..006; AC-ALERT-002/003, AC-UI-002..006.

**Contracts:** CTR-ALERT-001..005, CTR-API-001, CTR-UI-001.

**Files:**
- Create: `backend/src/agentmonitor/api/v1/routers/alerts.py`
- Modify: `backend/src/agentmonitor/composition/bootstrap.py`
- Create: `frontend/src/features/alerts/AlertsPage.tsx`
- Create: `frontend/src/features/alerts/AlertRulesPage.tsx`
- Generate: `contracts/openapi/agentmonitor-v1.json`
- Generate: `frontend/src/generated/api/index.ts`
- Test: `backend/tests/api/v1/test_alert_routes.py`
- Test: `frontend/tests/browser/p02/alerts.spec.ts`

**Interfaces:** P01 exposes bounded rule CRUD, list, acknowledge, snooze, unsnooze, and read operations; P02 uses only generated client methods. V1 has dashboard notifications only.

- [ ] **Step 1: Write the concrete real HTTP test.** Add to `test_alert_routes.py`:

```python
def test_alert_acknowledge_and_snooze_survive_reload(real_alert_api, real_alert_id):
    acknowledged = real_alert_api.post(f"/api/v1/alerts/{real_alert_id}/acknowledgements", json={})
    assert acknowledged.status_code == 200
    snoozed = real_alert_api.post(
        f"/api/v1/alerts/{real_alert_id}/snoozes", json={"duration_seconds": 900}
    )
    assert snoozed.status_code == 200
    loaded = real_alert_api.get(f"/api/v1/alerts/{real_alert_id}")
    assert loaded.json()["acknowledged"] is True
    assert loaded.json()["snoozed"] is True
```

- [ ] **Step 2: Run Red separately.** Backend: `python3 -m pytest backend/tests/api/v1/test_alert_routes.py -vv`. Frontend: `npm --prefix frontend run test:browser -- tests/browser/p02/alerts.spec.ts`. Expected: both available boundaries FAIL because routes/client/pages are absent.
- [ ] **Step 3: Implement and regenerate.** Add stable errors, authorization, bounded pagination, accessible controls/live regions, and generated artifacts through the named writer. Do not add an external-delivery surface.
- [ ] **Step 4: Run Green separately.** Backend: `python3 -m pytest backend/tests/api/v1/test_alert_routes.py -vv`. Frontend: `npm --prefix frontend run test:browser -- tests/browser/p02/alerts.spec.ts`. Expected: PASS against real database/server/browser with keyboard and non-color cues.
- [ ] **Step 5: Checkpoint.** `git add backend/src/agentmonitor/api/v1/routers/alerts.py backend/src/agentmonitor/composition/bootstrap.py frontend/src/features/alerts contracts/openapi/agentmonitor-v1.json frontend/src/generated/api/index.ts backend/tests/api/v1/test_alert_routes.py frontend/tests/browser/p02/alerts.spec.ts && git commit -m "feat(v1-m4): deliver alert console"`.

---

## EPIC-OPS-01 — Operational Health and Milestone Evidence

### Task 6: ST-OPS-001 — Publish operations contracts, diagnostics, and M4 evidence

**Requirements:** FR-OPS-002/005/006, NFR-RES-001, NFR-OBS-001; AC-OPS-003/006, AC-V1-003/005/006/007/008.

**Contracts:** Create CTR-OPS-001..007 in `operations_v1.py`; consume CTR-APP-001, CTR-FND-007, CTR-DB-001, and component CTR-OPS-006 ports.

**Files:**
- Create: `backend/src/agentmonitor/contracts/operations_v1.py`
- Create: `backend/src/agentmonitor/modules/operations/application/health.py`
- Create: `backend/src/agentmonitor/modules/operations/application/diagnostics.py`
- Create: `backend/src/agentmonitor/modules/operations/application/service.py`
- Create: `backend/src/agentmonitor/api/v1/routers/operations.py`
- Create: `backend/src/agentmonitor/api/v1/schemas/operations.py`
- Modify: `backend/src/agentmonitor/composition/bootstrap.py`
- Create: `frontend/src/features/diagnostics/DiagnosticsPage.tsx`
- Generate: `contracts/openapi/agentmonitor-v1.json`
- Generate: `frontend/src/generated/api/index.ts`
- Test: `backend/tests/integration/operations/test_health_and_diagnostics.py`
- Test: `backend/tests/api/v1/test_operations_routes.py`
- Test: `frontend/tests/browser/p02/operations.spec.ts`
- Test: `backend/tests/integration/release/test_v1_m4_claude_fleet_alerts.py`

**Interfaces:** M8 owns one `modules/operations/application/` package: `health.py` implements health/liveness/readiness/version aggregation, `diagnostics.py` implements `GetDiagnosticSummaryV1(disclosure_level, deadline)`, and `service.py` is their public application façade. The package calls deadline-bounded `GetComponentHealthV1(ComponentHealthRequestV1) -> ComponentHealthResultV1` and never imports component internals.

- [ ] **Step 1: Write the concrete integration test.** Add to `test_health_and_diagnostics.py`:

```python
def test_diagnostics_are_authoritative_and_allowlisted(real_operations_service):
    health = real_operations_service.get_health()
    diagnostics = real_operations_service.get_diagnostic_summary(disclosure_level="administrator")
    assert health.liveness == "healthy"
    assert health.readiness in {"ready", "degraded"}
    assert diagnostics.application_version
    assert diagnostics.schema_version == "v1_0702"
    assert set(diagnostics.to_dict()) <= {
        "application_version", "schema_version", "api_version", "client_version",
        "components", "freshness", "reason_codes", "configuration_presence", "correlation_id",
    }
```

- [ ] **Step 2: Run Red independently.** Backend: `python3 -m pytest backend/tests/integration/operations/test_health_and_diagnostics.py backend/tests/api/v1/test_operations_routes.py backend/tests/integration/release/test_v1_m4_claude_fleet_alerts.py -vv`. Frontend: `npm --prefix frontend run test:browser -- tests/browser/p02/operations.spec.ts`. Expected: each available boundary FAILS for missing contract/service/routes/page or reports its named real prerequisite Blocked.
- [ ] **Step 3: Implement the M08-consistent application package.** Put aggregation in `health.py`, allowlisted disclosure in `diagnostics.py`, and only façade orchestration in `service.py`; bound component deadlines, source versions authoritatively, register the route in composition, and regenerate both artifacts.
- [ ] **Step 4: Run Green and cataloged gates.** Backend: `python3 -m pytest backend/tests/integration/operations/test_health_and_diagnostics.py backend/tests/api/v1/test_operations_routes.py backend/tests/integration/release/test_v1_m4_claude_fleet_alerts.py -vv`. Frontend: `npm --prefix frontend run test:browser -- tests/browser/p02/operations.spec.ts`. Governance: `python3 tools/automation/run.py AUTO-TEST`. Documentation: `python3 tools/automation/run.py AUTO-DOCS-CHECK`. Expected: available boundaries and operational cataloged gates PASS; live gaps remain explicitly Blocked.
- [ ] **Step 5: Review and checkpoint.** Record all requirement/contract versions, Red/Green evidence, six-owner outcomes, privacy/security/migration/license/docs impact, and residual Blocked items. Commit: `git add backend/src/agentmonitor/contracts/operations_v1.py backend/src/agentmonitor/modules/operations/application/health.py backend/src/agentmonitor/modules/operations/application/diagnostics.py backend/src/agentmonitor/modules/operations/application/service.py backend/src/agentmonitor/api/v1/routers/operations.py backend/src/agentmonitor/api/v1/schemas/operations.py backend/src/agentmonitor/composition/bootstrap.py frontend/src/features/diagnostics contracts/openapi/agentmonitor-v1.json frontend/src/generated/api/index.ts backend/tests/integration/operations backend/tests/api/v1/test_operations_routes.py frontend/tests/browser/p02/operations.spec.ts backend/tests/integration/release/test_v1_m4_claude_fleet_alerts.py && git commit -m "feat(v1-m4): publish operations diagnostics"`.
