# AgentMonitor V1-M6 Ollama Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an evidence-backed Ollama local-runtime and cloud-subscription slice for two intended identities while keeping local compute, cloud subscription, and API billing as distinct resource pools.

**Architecture:** A03 implements independently gated M03 local-service, local-metadata, cloud-identity, cloud-subscription, and correlation lanes. M02 owns identity, M04 owns collection, M05 owns capacity, M06 owns runtime, P01 owns provider-neutral HTTP, and P02 consumes only the generated client.

**Tech Stack:** Python, real Ollama client/service and accepted official cloud source, bounded local/HTTPS ports, FastAPI, file-backed SQLite, OpenAPI 3, React/TypeScript, generated API client, Playwright, native Linux process inspection.

**Spec:** `docs/product/v1-specification.md`

## Global Constraints

- Milestone: `V1-M6`; epic: `EPIC-OLL-01`; entry gates: `V1-M3`, accepted applicable `M0-OLL-*`/`M0-LNX-*` evidence, Approved `docs/plans/adapters/ollama/plan-v1.md`, affected contracts, and allocated shared writers.
- Detached M0 reviewer approvals are advisory and never block M6 execution.
  M6 gates current technical evidence and real Ollama boundaries directly;
  unavailable services, identities, models, or processes remain Blocked or Not
  Run.
- Detailed authority remains in `docs/plans/integration/v1-planning-program.md`, A03, M02–M06, P01/P02, `docs/plans/contract-adoption.toml`, and `docs/plans/parallel-ownership.toml`.
- Local installation/service, installed model, loaded/runtime model, cloud identity, cloud subscription, and API billing are independent resources. `OLL-I09` API billing belongs to `V1-M7`; `OLL-I11` managed reauthentication requires its own authorization. Neither is implemented here.
- All listed files and tests are unconditional deliverables. If accepted M0 evidence says a lane is Unsupported, its manifest/adapter/test must return that typed truth before external I/O; do not omit the file, test, or write set.
- Use real client/service, approved endpoints/files, intended identities, subscription sources, processes/models, file-backed SQLite, loopback HTTP, and a built browser. No mocks, fakes, stubs, emulators, fake daemons/servers, recordings, copied provider files, demo accounts, seeded telemetry, placeholder values, or in-memory SQLite.
- Never generate, pull, load, unload, copy, delete, restart, signal, or reconfigure provider state. Never retain prompts, bodies, model output, source, arbitrary environments, credentials, raw provider output, local paths, query-bearing URLs, or unrestricted errors.
- Missing real prerequisites remain Blocked or Not Run. Unknown, Unsupported, Unavailable, Stale, Partial, Unresolved, and exact zero remain distinct.
- Shared composition, contracts, OpenAPI, generated client, configuration, and evidence files are edited only by the named writer.

---

## EPIC-OLL-01 — Ollama Local and Cloud Vertical Slice

### Task 1: ST-OLL-001 — Admit independently gated capabilities and installation evidence

**Requirements:** FR-ACC-004/005, FR-COL-004/006..008, FR-DISC-008, NFR-COMP-001; AC-LIVE-004, AC-TEST-001..006.

**Contracts:** CTR-PROV-001..005/008 and CTR-COMMON-004.

**Files:**
- Create: `backend/src/agentmonitor/adapters/providers/ollama/adapter.py`
- Create: `backend/src/agentmonitor/adapters/providers/ollama/manifest.py`
- Create: `backend/src/agentmonitor/adapters/providers/ollama/installation.py`
- Create: `backend/src/agentmonitor/adapters/providers/ollama/sources.py`
- Test: `backend/tests/adapters/providers/ollama/pure/test_manifest.py`
- Test: `backend/tests/adapters/providers/ollama/integration/test_installation.py`
- Create: `docs/adapters/ollama.md`

**Interfaces:** Implement `ProviderAdapterV1.manifest() -> CapabilityManifestV1`, `resolve_capability(ResolveCapabilityRequestV1) -> ProviderCapabilityPortV1`, exact sources, and bounded outcomes. Track client, service, local schema/parser, and cloud source versions independently.

- [ ] **Step 1: Write concrete manifest tests.** Add to `test_manifest.py`:

```python
def test_ollama_lanes_are_independent_and_evidence_scoped(ollama_adapter):
    manifest = ollama_adapter.manifest()
    rows = {row.capability_key: row for row in manifest.capabilities}
    assert rows["local.runtime"].resource_kind == "ollama_local_runtime"
    assert rows["cloud.subscription"].resource_kind == "ollama_cloud_subscription"
    assert rows["api.billing"].resource_kind == "ollama_api_billing"
    assert all(row.evidence_id for row in rows.values() if row.capability_state == "supported")
    assert rows["api.billing"].invokable is False

def test_client_version_never_substitutes_for_service_version(ollama_adapter, real_ollama_installation):
    result = ollama_adapter.inspect_installation(real_ollama_installation)
    assert result.client_version == real_ollama_installation.client_version
    assert result.service_version == real_ollama_installation.service_version
    assert result.client_version_source != result.service_version_source
```

- [ ] **Step 2: Run Red.** `python3 -m pytest backend/tests/adapters/providers/ollama/pure/test_manifest.py backend/tests/adapters/providers/ollama/integration/test_installation.py -vv`. Expected: FAIL because A03 or independent version/source decisions are absent; missing installation/service is Blocked.
- [ ] **Step 3: Implement minimum Green.** Bind every lane to exact evidence/source/version/platform/side-effect/bounds, keep unapproved lanes non-invokable, and prohibit fallback across local service, local metadata, cloud subscription, and API billing.
- [ ] **Step 4: Run Green.** `python3 -m pytest backend/tests/adapters/providers/ollama/pure/test_manifest.py backend/tests/adapters/providers/ollama/integration/test_installation.py -vv`. Expected: PASS for policy and the available real tuple; unsupported/unverified lanes retain their exact typed state.
- [ ] **Step 5: Checkpoint.** `git add backend/src/agentmonitor/adapters/providers/ollama/adapter.py backend/src/agentmonitor/adapters/providers/ollama/manifest.py backend/src/agentmonitor/adapters/providers/ollama/installation.py backend/src/agentmonitor/adapters/providers/ollama/sources.py backend/tests/adapters/providers/ollama/pure/test_manifest.py backend/tests/adapters/providers/ollama/integration/test_installation.py docs/adapters/ollama.md && git commit -m "feat(v1-m6): admit Ollama adapter"`.

### Task 2: ST-OLL-002 — Observe local service, metadata decision, catalog, and runtime safely

**Requirements:** FR-DISC-001/003/006/008, FR-COL-003..008, FR-SAFE-002, NFR-SEC-001; AC-PROC-001/002/004.

**Contracts:** CTR-BOUNDARY-002, CTR-PROV-002..004/008, CTR-RUN-002/003, CTR-PLAT-001.

**Files:**
- Create: `backend/src/agentmonitor/adapters/providers/ollama/local_service/client.py`
- Create: `backend/src/agentmonitor/adapters/providers/ollama/local_service/catalog.py`
- Create: `backend/src/agentmonitor/adapters/providers/ollama/local_service/runtime.py`
- Create: `backend/src/agentmonitor/adapters/providers/ollama/local_metadata/reader.py`
- Test: `backend/tests/adapters/providers/ollama/integration/test_local_service.py`
- Test: `backend/tests/adapters/providers/ollama/integration/test_local_metadata.py`
- Test: `backend/tests/adapters/providers/ollama/live/test_local_runtime.py`

**Interfaces:** Use only approved local destinations/methods/routes and bounded file grants. Produce closed `RuntimeObservationBatchV1` inputs. Installed and loaded/running models remain distinct; an Unsupported metadata lane performs zero file I/O.

- [ ] **Step 1: Write concrete unconditional tests.** Add to `test_local_metadata.py` and `test_local_runtime.py`:

```python
def test_local_metadata_matches_the_accepted_capability_decision(ollama_adapter, real_ollama_target):
    decision = ollama_adapter.manifest().capability("local.metadata")
    result = ollama_adapter.read_local_metadata(real_ollama_target)
    if decision.capability_state == "unsupported":
        assert result.state == "unsupported"
        assert real_ollama_target.metadata_read_count == 0
    else:
        assert result.state in {"success", "partial", "unavailable"}
        assert result.source_id == decision.source_id

def test_real_local_runtime_never_labels_installed_as_running(real_ollama_runtime):
    result = real_ollama_runtime.observe()
    installed_ids = {item.model_id for item in result.models if item.lifecycle == "installed"}
    running_ids = {item.model_id for item in result.models if item.lifecycle == "running"}
    assert all(item.source_id and item.collected_at for item in result.models)
    assert running_ids <= installed_ids
    assert all(item.request_body is None and item.response_body is None for item in result.models)
```

- [ ] **Step 2: Run Red.** `python3 -m pytest backend/tests/adapters/providers/ollama/integration/test_local_service.py backend/tests/adapters/providers/ollama/integration/test_local_metadata.py backend/tests/adapters/providers/ollama/live/test_local_runtime.py -vv`. Expected: FAIL on missing safe projection or typed Unsupported behavior; absent natural models/processes are Blocked.
- [ ] **Step 3: Implement minimum Green.** Enforce destination/method/route/redirect/byte/item/page/deadline bounds, exact parser selection, allowlisted extraction, and zero metadata access when Unsupported. Cancellation stops only AgentMonitor collection.
- [ ] **Step 4: Run Green.** `python3 -m pytest backend/tests/adapters/providers/ollama/integration/test_local_service.py backend/tests/adapters/providers/ollama/integration/test_local_metadata.py backend/tests/adapters/providers/ollama/live/test_local_runtime.py -vv`. Expected: PASS for the accepted capability decision and available real local state with no provider mutation.
- [ ] **Step 5: Checkpoint.** `git add backend/src/agentmonitor/adapters/providers/ollama/local_service backend/src/agentmonitor/adapters/providers/ollama/local_metadata backend/tests/adapters/providers/ollama/integration/test_local_service.py backend/tests/adapters/providers/ollama/integration/test_local_metadata.py backend/tests/adapters/providers/ollama/live/test_local_runtime.py && git commit -m "feat(v1-m6): observe Ollama local runtime"`.

### Task 3: ST-OLL-003 — Reconcile two cloud identities and authentication health

**Requirements:** FR-ACC-001/004..006, FR-AUTH-001/004/005, FR-SAFE-001/002; AC-LIVE-003, AC-UI-005/006.

**Contracts:** CTR-PROV-005/006 and CTR-REG-001/002/004/005/006/009/010.

**Files:**
- Create: `backend/src/agentmonitor/adapters/providers/ollama/cloud_identity/discovery.py`
- Create: `backend/src/agentmonitor/adapters/providers/ollama/authentication/health.py`
- Modify: `backend/src/agentmonitor/modules/registry/application/discovery.py`
- Modify: `backend/src/agentmonitor/modules/registry/application/accounts.py`
- Test: `backend/tests/adapters/providers/ollama/live/test_cloud_identity.py`
- Test: `backend/tests/integration/registry/test_ollama_fleet.py`

**Interfaces:** A03 returns bounded discovery/auth outcomes; M02 alone owns identities and relationships. Local service reachability cannot prove cloud auth, and credentials never enter A03.

- [ ] **Step 1: Write the concrete two-identity test.** Add to `test_ollama_fleet.py`:

```python
def test_two_ollama_identities_reconcile_without_local_cloud_inference(real_ollama_identities, registry):
    outcomes = real_ollama_identities.reconcile_into(registry)
    assert len(outcomes) == 2
    assert len({item.alias for item in outcomes}) == 2
    assert {item.status for item in outcomes} <= {"reconciled", "owner_unavailable", "unresolved"}
    assert all(item.account_id is None for item in outcomes if item.evidence_strength != "strong")
    assert all(item.auth_source_kind != "local_service" for item in outcomes)
```

- [ ] **Step 2: Run Red.** `python3 -m pytest backend/tests/adapters/providers/ollama/live/test_cloud_identity.py backend/tests/integration/registry/test_ollama_fleet.py -vv`. Expected: FAIL on missing identity/auth/reconciliation; inaccessible owners are Blocked.
- [ ] **Step 3: Implement minimum Green.** Apply exact host/source/role/version bounds, provider-managed credential application, idempotent discovery, expected-identity checks, and sanitized reason codes. Do not implement reauthentication.
- [ ] **Step 4: Run Green.** `python3 -m pytest backend/tests/adapters/providers/ollama/live/test_cloud_identity.py backend/tests/integration/registry/test_ollama_fleet.py -vv`. Expected: PASS for available identities with both intended outcomes explicit and no local-to-cloud inference.
- [ ] **Step 5: Checkpoint.** `git add backend/src/agentmonitor/adapters/providers/ollama/cloud_identity backend/src/agentmonitor/adapters/providers/ollama/authentication backend/src/agentmonitor/modules/registry backend/tests/adapters/providers/ollama/live/test_cloud_identity.py backend/tests/integration/registry/test_ollama_fleet.py && git commit -m "feat(v1-m6): reconcile Ollama cloud identities"`.

### Task 4: ST-OLL-004 — Collect cloud subscription capacity as a separate pool

**Requirements:** FR-QUOTA-001/002/004/006, FR-COL-003..008, FR-HIST-001/002; AC-LIVE-005/007, AC-HIST-001, AC-OPS-006.

**Contracts:** CTR-PROV-002..004/008, CTR-COL-004, CTR-CAP-001/003/007.

**Files:**
- Create: `backend/src/agentmonitor/adapters/providers/ollama/cloud_subscription/quota.py`
- Create: `backend/src/agentmonitor/adapters/providers/ollama/cloud_subscription/mapping.py`
- Modify: `backend/src/agentmonitor/modules/collection_control/application/runner.py`
- Modify: `backend/src/agentmonitor/modules/capacity/application/ingest.py`
- Test: `backend/tests/adapters/providers/ollama/pure/test_resource_separation.py`
- Test: `backend/tests/adapters/providers/ollama/live/test_cloud_subscription.py`
- Test: `backend/tests/integration/capacity/test_ollama_subscription_history.py`

**Interfaces:** Produce accepted `ProviderQuotaInputV1` values only; M04 commits through M05. Preserve native identity/scope/unit/reset/precision/provenance/freshness/field state. Never derive quota from local usage or API billing.

- [ ] **Step 1: Write the concrete resource separation test.** Add to `test_ollama_subscription_history.py`:

```python
def test_cloud_subscription_history_never_merges_local_or_api_pools(real_ollama_subscription, capacity_repository):
    outcome = real_ollama_subscription.collect_and_commit(capacity_repository)
    assert outcome.state in {"success", "partial"}
    assert len({item.native_window_id for item in outcome.items}) == len(outcome.items)
    stored = capacity_repository.history_for(outcome.account_id)
    assert all(item.resource_kind == "ollama_cloud_subscription" for item in stored)
    assert all(item.reset_at is not None or item.reset_state in {"unknown", "unsupported"} for item in stored)
    assert not any(item.resource_kind in {"ollama_local_runtime", "ollama_api_billing"} for item in stored)
```

- [ ] **Step 2: Run Red.** `python3 -m pytest backend/tests/adapters/providers/ollama/pure/test_resource_separation.py backend/tests/adapters/providers/ollama/live/test_cloud_subscription.py backend/tests/integration/capacity/test_ollama_subscription_history.py -vv`. Expected: FAIL on missing separation/mapping/commit; Unsupported or inaccessible quota is reported truthfully.
- [ ] **Step 3: Implement minimum Green.** Enforce official host/method/role/request/page/rate/cost/deadline bounds, deterministic mapping, idempotent commits, and explicit Unsupported/Unknown/Unavailable/Partial states. Do not create `api_billing` production code.
- [ ] **Step 4: Run Green.** `python3 -m pytest backend/tests/adapters/providers/ollama/pure/test_resource_separation.py backend/tests/adapters/providers/ollama/live/test_cloud_subscription.py backend/tests/integration/capacity/test_ollama_subscription_history.py -vv`. Expected: PASS for the accepted real capability state, with resource pools visibly separate.
- [ ] **Step 5: Checkpoint.** `git add backend/src/agentmonitor/adapters/providers/ollama/cloud_subscription backend/src/agentmonitor/modules/collection_control/application/runner.py backend/src/agentmonitor/modules/capacity/application/ingest.py backend/tests/adapters/providers/ollama/pure/test_resource_separation.py backend/tests/adapters/providers/ollama/live/test_cloud_subscription.py backend/tests/integration/capacity/test_ollama_subscription_history.py && git commit -m "feat(v1-m6): collect Ollama cloud subscription"`.

### Task 5: ST-OLL-005 — Correlate, integrate, render, and close M6 evidence

**Requirements:** FR-DISC-004, FR-STATE-001..004, FR-UI-001..006, NFR-API-001/002, NFR-OBS-001; AC-PROC-003..005, AC-UI-002/005/006, AC-OPS-003/006.

**Contracts:** CTR-RUN-007, CTR-REG, CTR-CAP, CTR-OPS-006, CTR-API-001, CTR-UI-001.

**Files:**
- Create: `backend/src/agentmonitor/adapters/providers/ollama/correlation/evidence.py`
- Create: `backend/src/agentmonitor/adapters/providers/ollama/diagnostics.py`
- Modify: `backend/src/agentmonitor/modules/runtime_observation/application/correlation.py`
- Modify: `backend/src/agentmonitor/composition/providers.py`
- Modify: `backend/src/agentmonitor/api/v1/routers/registry.py`
- Modify: `backend/src/agentmonitor/api/v1/routers/capacity.py`
- Modify: `backend/src/agentmonitor/api/v1/routers/runtime.py`
- Modify: `frontend/src/features/accounts/AccountsPage.tsx`
- Modify: `frontend/src/features/history/HistoryPage.tsx`
- Modify: `frontend/src/features/sessions/SessionsPage.tsx`
- Generate: `contracts/openapi/agentmonitor-v1.json`
- Generate: `frontend/src/generated/api/index.ts`
- Test: `backend/tests/adapters/providers/ollama/integration/test_ollama_slice.py`
- Test: `backend/tests/integration/release/test_v1_m6_ollama_slice.py`
- Test: `frontend/tests/browser/p02/ollama-slice.spec.ts`

**Interfaces:** A03 emits approved correlation evidence only; M06 decides. Register A03 through `composition/providers.py`, expose provider-neutral operations, return bounded component health, and render generated DTOs.

- [ ] **Step 1: Write the concrete integrated test.** Add to `test_ollama_slice.py`:

```python
def test_ollama_slice_keeps_local_and_cloud_resources_separate(real_ollama_application):
    accounts = real_ollama_application.api.get("/api/v1/accounts", params={"provider_key": "ollama"})
    capacity = real_ollama_application.api.get("/api/v1/capacity/history", params={"provider_key": "ollama"})
    sessions = real_ollama_application.api.get("/api/v1/runtime/sessions", params={"provider_key": "ollama"})
    assert accounts.status_code == capacity.status_code == sessions.status_code == 200
    assert len(accounts.json()["items"]) == 2
    assert all(item["resource_kind"] == "ollama_cloud_subscription" for item in capacity.json()["items"])
    assert all(item["resource_kind"] == "ollama_local_runtime" for item in sessions.json()["items"])
    assert "ollama_api_billing" not in capacity.text
```

- [ ] **Step 2: Run Red separately.** Backend: `python3 -m pytest backend/tests/adapters/providers/ollama/integration/test_ollama_slice.py backend/tests/integration/release/test_v1_m6_ollama_slice.py -vv`. Frontend: `npm --prefix frontend run test:browser -- tests/browser/p02/ollama-slice.spec.ts`. Expected: each available boundary FAILS for missing correlation/composition/API/client/UI; absent natural states remain Blocked.
- [ ] **Step 3: Wire approved evidence through shared surfaces.** Preserve unresolved/conflict decisions, register A03 in the exact shared composition file, regenerate both artifacts through their named writer, render provider-neutral states, and expose allowlisted diagnostics only.
- [ ] **Step 4: Run Green and cataloged gates.** Backend: `python3 -m pytest backend/tests/adapters/providers/ollama/integration/test_ollama_slice.py backend/tests/integration/release/test_v1_m6_ollama_slice.py -vv`. Frontend: `npm --prefix frontend run test:browser -- tests/browser/p02/ollama-slice.spec.ts`. Governance: `python3 tools/automation/run.py AUTO-TEST`. Documentation: `python3 tools/automation/run.py AUTO-DOCS-CHECK`. Expected: available boundaries and operational gates PASS; unavailable live conditions remain Blocked or Not Run.
- [ ] **Step 5: Review and checkpoint.** Record `EPIC-OLL-01`, `ST-OLL-001..005`, contract versions, Red/Green evidence, two-identity and process/model outcomes, pool separation, and security/privacy/migration/license/docs impact. Commit: `git add backend/src/agentmonitor/adapters/providers/ollama/correlation backend/src/agentmonitor/adapters/providers/ollama/diagnostics.py backend/src/agentmonitor/modules/runtime_observation/application/correlation.py backend/src/agentmonitor/composition/providers.py backend/src/agentmonitor/api/v1/routers/registry.py backend/src/agentmonitor/api/v1/routers/capacity.py backend/src/agentmonitor/api/v1/routers/runtime.py frontend/src/features/accounts frontend/src/features/history frontend/src/features/sessions contracts/openapi/agentmonitor-v1.json frontend/src/generated/api/index.ts backend/tests/adapters/providers/ollama/integration/test_ollama_slice.py backend/tests/integration/release/test_v1_m6_ollama_slice.py frontend/tests/browser/p02/ollama-slice.spec.ts && git commit -m "feat(v1-m6): complete Ollama slice"`.
