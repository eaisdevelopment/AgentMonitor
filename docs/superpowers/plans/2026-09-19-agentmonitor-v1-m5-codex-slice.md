# AgentMonitor V1-M5 Codex Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an evidence-backed Codex subscription/runtime slice for four intended accounts and 5–6 representative concurrent processes without conflating Codex subscription capacity with OpenAI API billing.

**Architecture:** A02 implements M03 provider ports and maps approved Codex sources into M02 registry, M05 capacity, and M06 runtime input DTOs. M04 owns scheduling; P01 remains provider-neutral; P02 uses only the generated client.

**Tech Stack:** Python, real Codex CLI/app-server or accepted local metadata source, FastAPI, file-backed SQLite, OpenAPI 3, React/TypeScript, generated API client, Playwright, native Linux process inspection.

**Spec:** `docs/product/v1-specification.md`

## Global Constraints

- Milestone: `V1-M5`; epic: `EPIC-CDX-01`; entry gates: `V1-M3`, accepted applicable `M0-CDX-*`/`M0-LNX-*` evidence, Approved `docs/plans/adapters/codex/plan-v1.md`, affected contracts, and allocated shared writers.
- Detailed authority remains in `docs/plans/integration/v1-planning-program.md`, A02, M02–M06, P01/P02, `docs/plans/contract-adoption.toml`, and `docs/plans/parallel-ownership.toml`.
- Codex subscription and OpenAI API resources remain separate. `CDX-I08` / `CDX-OAI-*` API usage, cost, and budget work belongs to `V1-M7`, not M5.
- Use real installations, approved sources, intended owners, real processes, file-backed SQLite, loopback HTTP, and a built browser. No mocks, fakes, stubs, emulators, recordings, copied provider files, demo accounts, seeded telemetry, placeholder values, or in-memory SQLite.
- Constructed values are allowed only in pure no-I/O policy tests and never prove provider compatibility. An unknown installed provider/parser tuple leaves the capability declaration intact but returns compatibility `Unverified` with `unverified_provider_version`; it is not relabeled capability `Unsupported`.
- Default `CODEX_HOME`, profiles, credentials, and processes are read-only. Never retain prompts, responses, reasoning, tool activity, source, terminal content, arbitrary environments, raw provider output, or unrestricted errors.
- Shared composition, contracts, OpenAPI, generated client, configuration, and evidence files are edited only by the named writer. Missing owner/provider prerequisites remain Blocked or Not Run.

---

## EPIC-CDX-01 — Codex Vertical Slice and Fleet

### Task 1: ST-CDX-001 — Admit the evidence-scoped adapter and real installation

**Requirements:** FR-ACC-005/006, FR-COL-006..008, FR-DISC-008; AC-LIVE-002/004, AC-TEST-001..006.

**Contracts:** CTR-PROV-001..005/008 and CTR-COMMON-004.

**Files:**
- Create: `backend/src/agentmonitor/adapters/providers/codex/adapter.py`
- Create: `backend/src/agentmonitor/adapters/providers/codex/manifest.py`
- Create: `backend/src/agentmonitor/adapters/providers/codex/installation.py`
- Create: `backend/src/agentmonitor/adapters/providers/codex/sources.py`
- Test: `backend/tests/adapters/providers/codex/pure/test_manifest.py`
- Test: `backend/tests/adapters/providers/codex/integration/test_installation.py`
- Create: `docs/adapters/codex.md`

**Interfaces:** Implement `ProviderAdapterV1.manifest() -> CapabilityManifestV1`, `resolve_capability(ResolveCapabilityRequestV1) -> ProviderCapabilityPortV1`, exact `ProviderSourceV1` descriptors, and bounded `CollectionOutcomeV1[T]`.

- [ ] **Step 1: Write concrete compatibility tests.** Add to `test_manifest.py`:

```python
def test_unknown_codex_version_is_unverified_not_unsupported(codex_adapter, installed_codex_unknown_version):
    decision = codex_adapter.resolve_installation(installed_codex_unknown_version)
    assert decision.capability_state == "supported"
    assert decision.compatibility_state == "unverified"
    assert decision.reason_code == "unverified_provider_version"
    assert decision.invokable is False

def test_supported_capability_requires_an_accepted_evidence_tuple(codex_adapter):
    rows = codex_adapter.manifest().capabilities
    assert all(row.evidence_id for row in rows if row.capability_state == "supported")
    assert all(row.source_id and row.version_rule for row in rows if row.capability_state == "supported")
```

- [ ] **Step 2: Run Red.** `python3 -m pytest backend/tests/adapters/providers/codex/pure/test_manifest.py backend/tests/adapters/providers/codex/integration/test_installation.py -vv`. Expected: FAIL because A02 or exact real installation compatibility is absent; a missing installation is Blocked.
- [ ] **Step 3: Implement minimum Green.** Bind each lane to exact evidence/source/version/platform/plan/side-effect/bounds. Consume only bounded executable resolution and version inspection; expose no raw execute, arbitrary file read, or dictionary escape hatch.
- [ ] **Step 4: Run Green.** `python3 -m pytest backend/tests/adapters/providers/codex/pure/test_manifest.py backend/tests/adapters/providers/codex/integration/test_installation.py -vv`. Expected: PASS for pure policy and the available real tuple; unverified tuples fail closed without changing capability meaning.
- [ ] **Step 5: Checkpoint.** `git add backend/src/agentmonitor/adapters/providers/codex backend/tests/adapters/providers/codex/pure/test_manifest.py backend/tests/adapters/providers/codex/integration/test_installation.py docs/adapters/codex.md && git commit -m "feat(v1-m5): admit Codex adapter"`.

### Task 2: ST-CDX-002 — Reconcile four identities and authentication health

**Requirements:** FR-ACC-001/004..006, FR-AUTH-001/004/005/006; AC-LIVE-002, AC-UI-005/006.

**Contracts:** CTR-PROV-005/006 and CTR-REG-001/002/004/005/006/009/010.

**Files:**
- Create: `backend/src/agentmonitor/adapters/providers/codex/identity.py`
- Create: `backend/src/agentmonitor/adapters/providers/codex/authentication/health.py`
- Modify: `backend/src/agentmonitor/modules/registry/application/discovery.py`
- Modify: `backend/src/agentmonitor/modules/registry/application/accounts.py`
- Test: `backend/tests/adapters/providers/codex/live/test_identity_and_auth.py`
- Test: `backend/tests/integration/registry/test_codex_fleet.py`
- Modify: `docs/modules/registry.md`

**Interfaces:** A02 returns bounded `DiscoveryOutcomeV1` and `AuthHealthOutcomeV1`; M02 alone creates accounts/resources and identity decisions. Provider auth health never invalidates the dashboard session.

- [ ] **Step 1: Write the concrete live fleet test.** Add to `test_codex_fleet.py`:

```python
def test_four_codex_owners_reconcile_without_guessing(real_codex_fleet, registry):
    outcomes = real_codex_fleet.reconcile_into(registry)
    assert len(outcomes) == 4
    assert len({item.alias for item in outcomes}) == 4
    assert {item.status for item in outcomes} <= {"reconciled", "owner_unavailable", "unresolved"}
    assert all(item.account_id is None for item in outcomes if item.status == "unresolved")
    assert all(item.credential_locator is None for item in outcomes)
```

- [ ] **Step 2: Run Red.** `python3 -m pytest backend/tests/adapters/providers/codex/live/test_identity_and_auth.py backend/tests/integration/registry/test_codex_fleet.py -vv`. Expected: FAIL on missing mapping/reconciliation; inaccessible owners are Blocked, never synthesized.
- [ ] **Step 3: Implement minimum Green.** Enforce expected provider/identity, idempotent discovery receipts, stable reason codes, protected-profile read-only handling, and separation of source availability from auth state. Do not add managed reauthentication.
- [ ] **Step 4: Run Green.** `python3 -m pytest backend/tests/adapters/providers/codex/live/test_identity_and_auth.py backend/tests/integration/registry/test_codex_fleet.py -vv`. Expected: PASS for available real owners with all four outcomes explicit and no locator/credential leakage.
- [ ] **Step 5: Checkpoint.** `git add backend/src/agentmonitor/adapters/providers/codex/identity.py backend/src/agentmonitor/adapters/providers/codex/authentication backend/src/agentmonitor/modules/registry backend/tests/adapters/providers/codex/live/test_identity_and_auth.py backend/tests/integration/registry/test_codex_fleet.py docs/modules/registry.md && git commit -m "feat(v1-m5): reconcile Codex identities"`.

### Task 3: ST-CDX-003 — Collect native subscription windows into capacity history

**Requirements:** FR-QUOTA-001..006, FR-COL-003..008, FR-HIST-001/002; AC-LIVE-004/005/007, AC-HIST-001.

**Contracts:** CTR-PROV-002..004/008, CTR-COL-004, CTR-CAP-001/003/007.

**Files:**
- Create: `backend/src/agentmonitor/adapters/providers/codex/subscription/quota.py`
- Create: `backend/src/agentmonitor/adapters/providers/codex/subscription/mapping.py`
- Modify: `backend/src/agentmonitor/modules/collection_control/application/runner.py`
- Modify: `backend/src/agentmonitor/modules/capacity/application/ingest.py`
- Test: `backend/tests/adapters/providers/codex/live/test_subscription_quota.py`
- Test: `backend/tests/integration/capacity/test_codex_subscription_history.py`

**Interfaces:** Produce validated `ProviderQuotaInputV1` inside `CollectionOutcomeV1[ProviderQuotaInputV1]`; M04 commits through M05 `CollectionOutcomeCommitPortV1`. OpenAI API billing is absent.

- [ ] **Step 1: Write the concrete real quota test.** Add to `test_codex_subscription_history.py`:

```python
def test_real_codex_windows_retain_native_identity_and_provenance(real_codex_quota, capacity_repository):
    outcome = real_codex_quota.collect_and_commit(capacity_repository)
    assert outcome.state in {"success", "partial"}
    assert len({item.native_window_id for item in outcome.items}) == len(outcome.items)
    assert all(item.source_id and item.observed_at and item.collected_at for item in outcome.items)
    stored = capacity_repository.history_for(outcome.account_id)
    assert {item.native_window_id for item in stored} == {item.native_window_id for item in outcome.items}
    assert all(item.resource_kind == "codex_subscription" for item in stored)
```

- [ ] **Step 2: Run Red.** `python3 -m pytest backend/tests/adapters/providers/codex/live/test_subscription_quota.py backend/tests/integration/capacity/test_codex_subscription_history.py -vv`. Expected: FAIL on missing source, mapping, or commit; no accepted source is Blocked.
- [ ] **Step 3: Implement minimum Green.** Preserve native IDs, scopes, units, reset times, field states, source/version/freshness, and idempotent commit identity. Never merge by display label or emit an API-billing resource.
- [ ] **Step 4: Run Green.** `python3 -m pytest backend/tests/adapters/providers/codex/live/test_subscription_quota.py backend/tests/integration/capacity/test_codex_subscription_history.py -vv`. Expected: PASS for supported real windows with truthful unavailable/partial states.
- [ ] **Step 5: Checkpoint.** `git add backend/src/agentmonitor/adapters/providers/codex/subscription backend/src/agentmonitor/modules/collection_control/application/runner.py backend/src/agentmonitor/modules/capacity/application/ingest.py backend/tests/adapters/providers/codex/live/test_subscription_quota.py backend/tests/integration/capacity/test_codex_subscription_history.py && git commit -m "feat(v1-m5): collect Codex subscription quota"`.

### Task 4: ST-CDX-004 — Discover and correlate 5–6 representative processes

**Requirements:** FR-DISC-001/003/004/006/008, FR-STATE-001..004, FR-SAFE-002; AC-PROC-001..005.

**Contracts:** CTR-PROV-003/004/008, CTR-RUN-001/002/003/007, CTR-PLAT-001.

**Files:**
- Create: `backend/src/agentmonitor/adapters/providers/codex/runtime/sessions.py`
- Create: `backend/src/agentmonitor/adapters/providers/codex/runtime/correlation.py`
- Modify: `backend/src/agentmonitor/modules/runtime_observation/application/ingest.py`
- Modify: `backend/src/agentmonitor/modules/runtime_observation/application/correlation.py`
- Test: `backend/tests/adapters/providers/codex/live/test_runtime_sessions.py`
- Test: `backend/tests/runtime_observation/integration/test_codex_process_correlation.py`

**Interfaces:** A02 produces closed `RuntimeObservationBatchV1` inputs and approved evidence; M06 owns hierarchy, normalized state, stall decisions, persistence, and final account correlation.

- [ ] **Step 1: Write the concrete live process test.** Add to `test_codex_process_correlation.py`:

```python
def test_representative_codex_processes_keep_weak_identity_unresolved(real_codex_runtime, runtime_queries):
    receipt = real_codex_runtime.observe_representative_processes(minimum=5, maximum=6)
    sessions = runtime_queries.list_sessions(receipt.batch_id)
    assert 5 <= len(receipt.process_ids) <= 6
    assert set(receipt.process_ids) <= {process.process_id for session in sessions for process in session.processes}
    assert all(session.account_id is None for session in sessions if session.correlation_strength != "strong")
    assert all(process.prompt is None and process.environment is None for session in sessions for process in session.processes)
```

- [ ] **Step 2: Run Red.** `python3 -m pytest backend/tests/adapters/providers/codex/live/test_runtime_sessions.py backend/tests/runtime_observation/integration/test_codex_process_correlation.py -vv`. Expected: FAIL on missing safe observation/correlation; absent representative processes are Blocked.
- [ ] **Step 3: Implement minimum Green.** Use accepted local evidence plus A04 safe process metadata, explicit PID-reuse handling, source/freshness, and deterministic confidence/reasons. Never signal or mutate a process.
- [ ] **Step 4: Run Green.** `python3 -m pytest backend/tests/adapters/providers/codex/live/test_runtime_sessions.py backend/tests/runtime_observation/integration/test_codex_process_correlation.py -vv`. Expected: PASS for 5–6 real processes or truthful unresolved decisions, with forbidden content absent.
- [ ] **Step 5: Checkpoint.** `git add backend/src/agentmonitor/adapters/providers/codex/runtime backend/src/agentmonitor/modules/runtime_observation backend/tests/adapters/providers/codex/live/test_runtime_sessions.py backend/tests/runtime_observation/integration/test_codex_process_correlation.py && git commit -m "feat(v1-m5): observe Codex runtime"`.

### Task 5: ST-CDX-005 — Integrate HTTP, browser, health, and M5 evidence

**Requirements:** FR-UI-001..006, NFR-API-001/002, NFR-RES-001, NFR-OBS-001; AC-LIVE-002/004/005/007, AC-UI-002/005/006, AC-OPS-003/006.

**Contracts:** CTR-PROV-001/006, CTR-REG, CTR-CAP, CTR-RUN, CTR-OPS-006, CTR-API-001, CTR-UI-001.

**Files:**
- Create: `backend/src/agentmonitor/composition/providers.py`
- Modify: `backend/src/agentmonitor/api/v1/routers/registry.py`
- Modify: `backend/src/agentmonitor/api/v1/routers/capacity.py`
- Modify: `backend/src/agentmonitor/api/v1/routers/runtime.py`
- Modify: `frontend/src/features/accounts/AccountsPage.tsx`
- Modify: `frontend/src/features/history/HistoryPage.tsx`
- Modify: `frontend/src/features/sessions/SessionsPage.tsx`
- Generate: `contracts/openapi/agentmonitor-v1.json`
- Generate: `frontend/src/generated/api/index.ts`
- Test: `backend/tests/adapters/providers/codex/integration/test_codex_slice.py`
- Test: `backend/tests/integration/release/test_v1_m5_codex_slice.py`
- Test: `frontend/tests/browser/p02/codex-slice.spec.ts`

**Interfaces:** Register A02 through `composition/providers.py`, expose provider-neutral operations only, return A02 `ComponentHealthResultV1`, and render generated DTOs without provider-shaped endpoints.

- [ ] **Step 1: Write the concrete end-to-end test.** Add to the A02-owned `test_codex_slice.py`:

```python
def test_codex_slice_exposes_subscription_not_openai_api_billing(real_codex_application):
    accounts = real_codex_application.api.get("/api/v1/accounts", params={"provider_key": "codex"})
    capacity = real_codex_application.api.get("/api/v1/capacity/history", params={"provider_key": "codex"})
    sessions = real_codex_application.api.get("/api/v1/runtime/sessions", params={"provider_key": "codex"})
    assert accounts.status_code == capacity.status_code == sessions.status_code == 200
    assert len(accounts.json()["items"]) == 4
    assert all(item["resource_kind"] == "codex_subscription" for item in capacity.json()["items"])
    assert 5 <= len(sessions.json()["items"]) <= 6
    assert "openai_api" not in capacity.text
```

- [ ] **Step 2: Run Red separately.** Backend: `python3 -m pytest backend/tests/adapters/providers/codex/integration/test_codex_slice.py backend/tests/integration/release/test_v1_m5_codex_slice.py -vv`. Frontend: `npm --prefix frontend run test:browser -- tests/browser/p02/codex-slice.spec.ts`. Expected: each available boundary FAILS for missing composition/API/client/UI; missing owners/processes are Blocked.
- [ ] **Step 3: Wire the shared surfaces.** Register A02, regenerate the exact OpenAPI/client artifacts through their named writer, and render provider-neutral account/capacity/runtime/health states with accessible unknown/stale/unavailable/zero distinctions.
- [ ] **Step 4: Run Green and cataloged gates.** Backend: `python3 -m pytest backend/tests/adapters/providers/codex/integration/test_codex_slice.py backend/tests/integration/release/test_v1_m5_codex_slice.py -vv`. Frontend: `npm --prefix frontend run test:browser -- tests/browser/p02/codex-slice.spec.ts`. Governance: `python3 tools/automation/run.py AUTO-TEST`. Documentation: `python3 tools/automation/run.py AUTO-DOCS-CHECK`. Expected: available boundaries and operational gates PASS; every live gap remains Blocked or Not Run.
- [ ] **Step 5: Review and checkpoint.** Record `EPIC-CDX-01`, `ST-CDX-001..005`, affected contract versions, Red/Green evidence, four-owner and process outcomes, and security/privacy/migration/license/docs impact. Commit: `git add backend/src/agentmonitor/composition/providers.py backend/src/agentmonitor/api/v1/routers/registry.py backend/src/agentmonitor/api/v1/routers/capacity.py backend/src/agentmonitor/api/v1/routers/runtime.py frontend/src/features/accounts frontend/src/features/history frontend/src/features/sessions contracts/openapi/agentmonitor-v1.json frontend/src/generated/api/index.ts backend/tests/adapters/providers/codex/integration/test_codex_slice.py backend/tests/integration/release/test_v1_m5_codex_slice.py frontend/tests/browser/p02/codex-slice.spec.ts && git commit -m "feat(v1-m5): complete Codex slice"`.
