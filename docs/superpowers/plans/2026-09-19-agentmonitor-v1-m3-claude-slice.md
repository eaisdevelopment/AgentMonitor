# AgentMonitor V1-M3 Claude Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile one owner-controlled real Claude account from evidence-scoped discovery through registry, provider protocol, collection, capacity/runtime domains, authenticated `/api/v1`, generated client, and a built browser.

**Architecture:** M02 owns account/installation/profile/resource truth, M03 owns the provider-neutral protocol, A01 implements Claude-only behavior, M04 schedules and records runs, M05/M06 own capacity/runtime meaning and persistence, A04 supplies read-only Linux facts, P01 maps published ports, and P02 renders generated-client views. No layer reads another module's tables or raw provider data.

**Tech Stack:** Python, SQLite/Alembic, approved safe subprocess/filesystem boundaries, FastAPI/OpenAPI, React/TypeScript, generated API client, Playwright, real installed Claude on Linux.

**Spec:** `docs/product/v1-specification.md`

## Milestone map

- Milestone: `V1-M3` — one end-to-end real Claude vertical slice.
- Epics: `EPIC-REG-01`, `EPIC-PROV-01`, `EPIC-CLA-01`, `EPIC-OBS-01`.
- Detailed authority: [registry](../../plans/modules/m02-registry/plan-v1.md), [provider system](../../plans/modules/m03-provider-system/plan-v1.md), [Claude adapter](../../plans/adapters/claude/plan-v1.md), [collection](../../plans/modules/m04-collection-control/plan-v1.md), [capacity](../../plans/modules/m05-capacity/plan-v1.md), [runtime](../../plans/modules/m06-runtime-observation/plan-v1.md), [Linux](../../plans/platform/linux/plan-v1.md), [API](../../plans/api/fastapi-boundary/plan-v1.md), and [UI](../../plans/ui/react-dashboard/plan-v1.md).
- Contract versions: `CTR-REG-001..010`, `CTR-PROV-001..008`, `CTR-COL-001..007`, `CTR-CAP-001/003/004/009`, `CTR-RUN-001..007`, `CTR-BOUNDARY-001..003`, and `CTR-PLAT-001`, all V1 after approval.
- Entry gate: `V1-M2` passes and the current technical mapping/schema/probe
  evidence is valid. Detached M0 reviewer approvals are advisory and are not an
  executable prerequisite; the canonical technical preflight is
  `m3_handoff_validate.py --require-technical-live`. If either required
  observation lane is not `Supported`, that lane remains explicitly Blocked;
  no alternative source is guessed.
- Exit gate: one owner-confirmed account produces one real quota observation and one real runtime observation, each linked to real collection runs and rendered through authenticated generated-client browser views with complete provenance. Any naturally unavailable state remains visibly `Blocked`.

`M0-M3-CLAUDE-SCOPED-ENTRY-001` is an M3-only technical evidence boundary and
does not declare M0 G9 complete. It binds exactly one Claude Code `2.1.278` /
Linux / Claude Max opaque profile tuple, its mapping, sanitized evidence/status
index, schema and CTR-PROV-002 contract bundles. Detached approval records are
retained for optional governance review and are not a local release blocker.
Codex,
Ollama, Anthropic API, OpenAI API, Ollama API, and macOS remain deferred to the
full M0 G9 matrix. While the CTR-PROV-002 normative schema does not yet exist,
`structural_prerequisite_authorized` permits only ST-PROV-001 pure
provider-neutral protocol work needed to create it: no provider I/O, adapter,
registry, persistence, migration, or later M3 task is authorized. Adapter/live
entry additionally requires the current contract/schema digests,
`subscription.quota` under its accepted
host/request/rate/cost boundary, and accepted targeted-profile evidence for
`local.process.account_correlation`; safe process observation alone cannot
satisfy same-account runtime correlation. Any missing required item leaves the
adapter/live handoff Blocked.

## Global Constraints

- Real current Claude, Linux, SQLite, HTTP, and browser boundaries are mandatory. No provider fixture, replay, fake adapter, emulated process tree, demo account, seeded telemetry, placeholder metric, or handcrafted observation row.
- M0 evidence bounds every provider claim. Unknown/new versions, fields, commands, paths, or identity evidence fail safely as unsupported/unverified and stop the affected Story.
- Claude's default profile and running agents are read-only. Do not log out, log in, modify, copy, relocate, signal, attach, send input, restart, kill, route, or switch credentials. Managed reauthentication is later scope.
- Do not read or persist prompts, responses, tools, source content, arbitrary command lines, process environments, terminal data, credentials, OTP/MFA values, raw provider output, or unapproved identity fields.
- Each external behavior records meaningful Red and Green against the same real boundary. An unavailable credential, absent provider state, setup failure, or constructed pure test is not live Green.
- One opaque live account/profile/process reservation is held for the entire live run; evidence uses opaque aliases and sanitized metadata only.
- Migration order is exactly `v1_0200..v1_0204`, `v1_0300`, `v1_0400`, `v1_0500..v1_0504`, and `v1_0600..v1_0603` after the migration steward allocates the files and records their reviewed SHA-256 values in `backend/migrations/catalog.toml`. Shared contracts, migration catalog, composition, OpenAPI, generated client, and app/shared UI files have one writer.

---

### Task 1: `ST-PROV-001` — Provider protocol, provenance, negotiation, and compatibility

**Epic:** `EPIC-PROV-01`

**Requirements / acceptance:** `FR-COL-004/006..008`, `FR-AUTH-001`, `NFR-ARCH-001/002`, `NFR-COMP-001`, `AC-LIVE-004`; `M03-PURE-001..024/031..034`, `M03-CONF-001..006`.

**Contracts:** `CTR-COMMON-004/007` and `CTR-PROV-001..008` at V1.

**Files:**
- Create: `backend/src/agentmonitor/contracts/common_provenance_v1.py`
- Create: `backend/src/agentmonitor/contracts/provider_system_v1.py`
- Create: `backend/src/agentmonitor/modules/provider_system/domain/protocol.py`
- Create: `backend/src/agentmonitor/modules/provider_system/application/gateway.py`
- Create: `backend/tests/provider_system/test_protocol.py`

**Interfaces:**
- Publishes `ProviderAdapterV1`, `CapabilityManifestV1`, `ProviderSourceV1`, `CollectionOutcomeV1[T]`, `DiscoveryOutcomeV1`, `AuthHealthOutcomeV1`, `ReauthFlowV1`, and governed provider-extension schemas.
- Capability ports include `InstallationDiscoveryPortV1`, `AccountDiscoveryPortV1`, `AuthenticationHealthPortV1`, `SubscriptionQuotaPortV1`, `LocalSessionDiscoveryPortV1`, `LocalSessionMetricsPortV1`, and `LocalProcessCorrelationPortV1`.
- Every request carries `ProviderOperationRequestHeaderV1`; every successful/partial result carries `ObservationProvenanceV1` and explicit `FieldAvailabilityV1` states.

- [ ] **Step 1: Write failing closed-outcome and version tests**

```python
def test_unverified_provider_version_is_rejected_before_invocation() -> None:
    calls = InvocationCounter()
    result = resolve_capability(APPROVED_MANIFEST, provider_version="new-unknown", invoke=calls)
    assert result.code == "provider_version_unverified"
    assert calls.count == 0


def test_partial_requires_omissions_and_provenance() -> None:
    with pytest.raises(InvalidCollectionOutcome):
        CollectionOutcomeV1.partial(value=SAFE_VALUE, omissions=(), provenance=None)
```

- [ ] **Step 2: Run protocol Red**

Run: `python3 -m pytest backend/tests/provider_system/test_protocol.py -q`

Expected: FAIL because protocol negotiation, closed outcome validation, and mandatory provenance are absent. Persistence is intentionally deferred until `ST-REG-001` creates its required `v1_0200..0204` parents.

- [ ] **Step 3: Implement the minimum provider-neutral protocol**

Use the approved M0-to-M03 mapping digest, reject duplicate manifests and incompatible majors before I/O, and forbid generic dictionaries/raw output. Do not create `v1_0300` before the M02 parent chain; the real compatibility repository moves to `ST-CLA-001` after `ST-REG-001`.

- [ ] **Step 4: Run protocol Green**

Run: `python3 -m pytest backend/tests/provider_system/test_protocol.py -q`

Expected: PASS for provider-neutral protocol semantics; this does not claim persistence or Claude conformance.

- [ ] **Step 5: Review and commit**

Review M03/M02/M04/M05/M06 consumer signatures and commit: `git commit -m "feat(provider): add v1 protocol and compatibility"`.

---

### Task 2: `ST-REG-001` — Registry persistence and one owner-confirmed Claude account

**Epic:** `EPIC-REG-01`

**Requirements / acceptance:** `FR-ACC-001..006`, `NFR-DATA-001`, `NFR-SEC-001`; `M02-PURE-006..23`, `M02-DB-007..24/28`, `M02-LIVE-001..010` applicable to the selected account.

**Contracts:** `CTR-REG-001..010`, `CTR-PROV-002/005/006/007`, and `CTR-DB-002` at V1.

**Files:**
- Create: `backend/src/agentmonitor/contracts/registry_v1.py`
- Create: `backend/src/agentmonitor/modules/registry/domain/account.py`
- Create: `backend/src/agentmonitor/modules/registry/application/discovery.py`
- Create: `backend/src/agentmonitor/modules/registry/application/accounts.py`
- Create: `backend/src/agentmonitor/modules/registry/application/organizations.py`
- Create: `backend/src/agentmonitor/adapters/persistence/registry/sqlite/repository.py`
- Create: `backend/migrations/versions/v1_0200_m02_registry_core.py`
- Create: `backend/migrations/versions/v1_0201_m02_provider_identity.py`
- Create: `backend/migrations/versions/v1_0202_m02_profiles_resources.py`
- Create: `backend/migrations/versions/v1_0203_m02_account_configuration.py`
- Create: `backend/migrations/versions/v1_0204_m02_receipts_outbox.py`
- Modify: `backend/migrations/catalog.toml`
- Create: `backend/tests/registry/test_identity_policy.py`
- Create: `backend/tests/integration/registry/test_claude_reconciliation.py`
- Create: `docs/modules/registry.md`

**Interfaces:**
- Publishes `OrganizationViewV1`, `AccountViewV1`, `ProviderDefinitionViewV1`, `ProviderInstallationViewV1`, `MonitoringProfileViewV1`, `AccountResourceViewV1`, `DiscoveryCandidateViewV1`, and `IdentityCorrelationDecisionV1` through `CTR-REG-001..010`.
- Consumes `DiscoveryOutcomeV1`; exposes `ReconcileProviderDiscoveryV1`, `ListDiscoveryCandidatesV1`, `ConfirmIdentityAssociationV1`, `RegisterAccountV1`, `ListAccountsV1`, `ListMonitoringProfilesV1`, and `ListAccountResourcesV1`.

- [ ] **Step 1: Write the failing real-discovery reconciliation test**

```python
def test_real_claude_candidate_requires_owner_confirmation(real_claude_discovery: DiscoveryOutcomeV1, registry: Registry) -> None:
    candidate = registry.reconcile(real_claude_discovery).candidates[0]
    assert candidate.association_state == "confirmation_required"
    account = registry.confirm(candidate.id, owner=registry.owner_principal)
    assert account.provider_key == "claude"
    assert registry.list_accounts(provider_key="claude").items == (account,)
```

- [ ] **Step 2: Run Red**

Run: `python3 -m pytest backend/tests/integration/registry/test_claude_reconciliation.py -q`

Expected: FAIL because the production registry cannot persist and owner-confirm a real M03 discovery candidate.

- [ ] **Step 3: Implement minimum registry contracts, migrations, and use cases**

Store only approved safe identity/fingerprint/evidence references, keep locators private, prohibit cross-module foreign keys, require owner confirmation for non-strong identity, and emit atomic registry revision/outbox records.

- [ ] **Step 4: Run Green with the current real candidate**

Run: `python3 -m pytest backend/tests/registry backend/tests/integration/registry/test_claude_reconciliation.py -q`

Expected: PASS for one real candidate/account/profile/resource graph; labels, raw identity, locators, paths, and provider output are absent from public views and evidence.

- [ ] **Step 5: Review and commit**

Review identity/privacy/migration and account-history semantics; commit: `git commit -m "feat(registry): reconcile one real claude account"`.

---

### Task 3: `ST-CLA-001` — Evidence-scoped Claude adapter and real subscription observation

**Epic:** `EPIC-CLA-01`

**Requirements / acceptance:** `FR-ACC-005/006`, `FR-AUTH-001`, `FR-QUOTA-001..006`, `FR-COL-004..008`, `AC-LIVE-001/004/005`; `M03-DB-001..013`, `CLA-PURE-001..012`, `CLA-CLI-001..008`, `CLA-PARSER-001..004`, `CLA-LIVE-001..005/011`, `CLA-SEC-001..010`.

**Contracts:** `CTR-PROV-001..008`, `CTR-CAP-001`, `CTR-REG-002/003`, `CTR-BOUNDARY-001/003`, and `CTR-DB-002` at V1.

**Files:**
- Create: `backend/src/agentmonitor/adapters/providers/claude/adapter.py`
- Create: `backend/src/agentmonitor/adapters/providers/claude/manifest.py`
- Create: `backend/src/agentmonitor/adapters/providers/claude/installation.py`
- Create: `backend/src/agentmonitor/adapters/providers/claude/authentication/health.py`
- Create: `backend/src/agentmonitor/adapters/providers/claude/subscription/source.py`
- Create: `backend/src/agentmonitor/adapters/providers/claude/subscription/mapper.py`
- Create: `backend/src/agentmonitor/contracts/providers/claude/subscription_quota/v1/schema.py`
- Create: `backend/src/agentmonitor/adapters/persistence/provider_system/sqlite/repository.py`
- Create: `backend/migrations/versions/v1_0300_m03_compatibility.py`
- Modify: `backend/migrations/catalog.toml`
- Create: `backend/tests/adapters/providers/claude/test_manifest.py`
- Create: `backend/tests/integration/provider_system/test_compatibility.py`
- Create: `backend/tests/live/claude/test_subscription_quota.py`
- Create: `docs/provider-capabilities/claude/subscription-quota.md`
- Create: `docs/adapters/claude.md`

**Interfaces:**
- Implements the approved `ProviderAdapterV1`, `InstallationDiscoveryPortV1`, `AccountDiscoveryPortV1`, `AuthenticationHealthPortV1`, and `SubscriptionQuotaPortV1` declarations only for the exact accepted tuple.
- Maps the real provider result to M05-owned `ProviderQuotaInputV1` inside `CollectionOutcomeV1[ProviderQuotaInputV1]`; raw bytes/stdout are discarded before the adapter boundary.
- All external work flows through approved `SafeSubprocessExecutionV1` or `ApprovedRootAndFileReadV1` operation references from M0, never a shell string or arbitrary path.

- [ ] **Step 1: Write the failing real-provider reconciliation test**

```python
def test_real_subscription_observation_matches_authoritative_view(real_claude: RealClaudeTarget) -> None:
    outcome = real_claude.adapter.collect_subscription_quota(real_claude.request)
    assert outcome.state in {"success", "partial"}
    assert outcome.value.account_id == real_claude.confirmed_account_id
    assert outcome.provenance.source_id == real_claude.approved_source_id
    assert real_claude.authoritative_view.reconciles(outcome.value)


def test_compatibility_assessment_survives_real_sqlite_reopen(real_provider_system_repository) -> None:
    receipt = real_provider_system_repository.record(COMPATIBILITY_ASSESSMENT)
    reopened = real_provider_system_repository.reopen()
    assert reopened.get(receipt.assessment_id) == COMPATIBILITY_ASSESSMENT
```

- [ ] **Step 2: Run Red**

Run: `python3 -m pytest backend/tests/integration/provider_system/test_compatibility.py backend/tests/live/claude/test_subscription_quota.py -q`

Expected: FAIL because the `v1_0300` repository and production Claude adapter do not exist. If the real provider boundary is unavailable, its case is Blocked, while the real-file SQLite case must still produce behavioral Red.

- [ ] **Step 3: Implement the minimum evidenced adapter lane**

After the M02 migration chain exists, create `v1_0300` with only compatibility assessments and the M03 outbox, then implement the real-file repository. Encode only accepted manifest tuples, version rules, operation/file/field bounds, native windows/units/reset semantics, safe auth states, and provenance. Reject unknown versions/fields and do not add fallback sources.

- [ ] **Step 4: Run Green against the same account and source**

Run: `python3 -m pytest backend/tests/provider_system/test_protocol.py backend/tests/integration/provider_system/test_compatibility.py backend/tests/adapters/providers/claude/test_manifest.py backend/tests/live/claude/test_subscription_quota.py -q`

Expected: PASS for real-file compatibility persistence plus owner-reconciled real values and clean DB/log/report scans; no compatibility claim extends beyond the observed tuple.

- [ ] **Step 5: Review and commit**

Confirm source rate/cost budget and protected-profile no-change evidence; commit: `git commit -m "feat(claude): add evidenced subscription adapter lane"`.

---

### Task 4: `ST-OBS-001` — Real collection run and idempotent capacity commit

**Epic:** `EPIC-OBS-01`

**Requirements / acceptance:** `FR-COL-001..008`, `FR-QUOTA-001..005`, `AC-HIST-001`, `AC-OPS-003`; `M04-DB-001..19`, `M04-LIVE-004/009..011`, `M05-DB-001..10/16..21`, `M05-LIVE-001..006` applicable to quota.

**Contracts:** `CTR-COL-001..007`, `CTR-CAP-001/003/004/009`, `CTR-PROV-001..004`, and `CTR-DB-002` at V1.

**Files:**
- Create: `backend/src/agentmonitor/contracts/collection_control_v1.py`
- Create: `backend/src/agentmonitor/contracts/common_quantity_v1.py`
- Create: `backend/src/agentmonitor/contracts/capacity_v1.py`
- Create: `backend/src/agentmonitor/modules/collection_control/application/executor.py`
- Create: `backend/src/agentmonitor/modules/collection_control/application/runner.py`
- Create: `backend/src/agentmonitor/modules/capacity/application/commit.py`
- Create: `backend/src/agentmonitor/modules/capacity/application/ingest.py`
- Create: `backend/src/agentmonitor/modules/capacity/application/queries.py`
- Create: `backend/src/agentmonitor/adapters/persistence/collection_control/sqlite/repository.py`
- Create: `backend/src/agentmonitor/adapters/persistence/capacity/sqlite/repository.py`
- Create: `backend/migrations/versions/v1_0400_m04_collection.py`
- Create: `backend/migrations/versions/v1_0500_m05_capacity_observations.py`
- Create: `backend/migrations/versions/v1_0501_m05_capacity_receipts.py`
- Create: `backend/migrations/versions/v1_0502_m05_capacity_health.py`
- Create: `backend/migrations/versions/v1_0503_m05_capacity_forecasts.py`
- Create: `backend/migrations/versions/v1_0504_m05_capacity_retention.py`
- Modify: `backend/migrations/catalog.toml`
- Create: `backend/tests/integration/collection_control/test_claude_quota_run.py`
- Create: `backend/tests/integration/capacity/test_claude_quota_commit.py`
- Create: `backend/tests/integration/capacity/test_capacity_schema_chain.py`
- Create: `docs/modules/capacity.md`

**Interfaces:**
- M04 publishes `RequestManualCollectionV1`, `CollectionRunViewV1`, `CollectionCompletedV1`, `CollectionFailedV1`, `CollectorHealthV1`, and `CollectionOutcomeCommitPortV1`.
- M05 implements `CommitCapacityCollectionOutcomeV1(...) -> CapacityCommitReceiptV1`; exposes `GetCollectionCommitStatusV1`, `GetAccountCapacityV1`, `ListQuotaWindowsV1`, and `GetCapacityHealthV1`.

- [ ] **Step 1: Write the failing real-run/commit test**

```python
def test_real_claude_run_commits_once(real_stack: RealClaudeStack) -> None:
    run = real_stack.request_manual_quota_collection()
    receipt = real_stack.await_terminal_receipt(run.id)
    replay = real_stack.capacity.commit(real_stack.recorded_outcome(run.id))
    assert run.id == receipt.run_id == replay.run_id
    assert receipt.observation_ids == replay.observation_ids
    assert real_stack.collection.get_run(run.id).state in {"succeeded", "partial"}


def test_capacity_schema_chain_is_complete_before_runtime(migrated_database: Path) -> None:
    schema = inspect_sqlite_schema(migrated_database, through="v1_0504")
    assert schema.revisions[-5:] == ("v1_0500", "v1_0501", "v1_0502", "v1_0503", "v1_0504")
    assert {"capacity_budget_observation", "capacity_forecast_projection", "capacity_retention_run"} <= schema.tables
```

- [ ] **Step 2: Run Red**

Run: `python3 -m pytest backend/tests/integration/collection_control/test_claude_quota_run.py backend/tests/integration/capacity/test_claude_quota_commit.py backend/tests/integration/capacity/test_capacity_schema_chain.py -q`

Expected: FAIL because no real scheduler/executor routes the typed A01 result to a durable M05 receipt.

- [ ] **Step 3: Implement the minimum collection and capacity slice**

Persist durable admission/run/fencing state before provider I/O, perform no I/O inside DB transactions, route quota to exactly one M05 sink, commit immutable exact quantities and projections, then finalize the run only after receipt. Create the complete frozen `v1_0500` through `v1_0504` DDL allocation now—including budget, forecast, and retention tables that later Stories will use—without seeding or claiming their later behavior. Once Green, these migration files are shared and immutable. Never retain the raw provider result in M04.

- [ ] **Step 4: Run Green against real provider data**

Run: `python3 -m pytest backend/tests/integration/collection_control/test_claude_quota_run.py backend/tests/integration/capacity/test_claude_quota_commit.py backend/tests/integration/capacity/test_capacity_schema_chain.py -q`

Expected: PASS with one real run, one idempotent receipt, exact field states/units/provenance, and no duplicate observation on replay.

- [ ] **Step 5: Review and commit**

Review concurrency, retry, freshness, migration, and provider-budget impact; commit: `git commit -m "feat(observation): commit real claude quota run"`.

---

### Task 5: `ST-OBS-002` — Real Linux process/session observation for the same account

**Epic:** `EPIC-OBS-01`

**Requirements / acceptance:** `FR-DISC-001..008`, `FR-STATE-001/002`, `AC-PROC-001..005`; `LNX-PROC-001..015`, `LNX-LIVE-001..009`, `CLA-FS-001..010`, `CLA-LIVE-008..010`, `M06-LNX-001..009`, `M06-LIVE-001..008` applicable to the reserved process.

**Contracts:** `CTR-PLAT-001`, `CTR-RUN-001..007`, `CTR-COL-006`, `CTR-PROV-001/003/004/008`, and `CTR-BOUNDARY-001/003` at V1.

**Files:**
- Modify: `backend/src/agentmonitor/contracts/platform_v1.py`
- Create: `backend/src/agentmonitor/contracts/runtime_observation_v1.py`
- Create: `backend/src/agentmonitor/adapters/platform/linux/processes.py`
- Create: `backend/src/agentmonitor/adapters/providers/claude/local_sessions/source.py`
- Create: `backend/src/agentmonitor/adapters/providers/claude/correlation/evidence.py`
- Create: `backend/src/agentmonitor/modules/runtime_observation/application/commit.py`
- Create: `backend/src/agentmonitor/modules/runtime_observation/application/ingest.py`
- Create: `backend/src/agentmonitor/modules/runtime_observation/application/correlation.py`
- Create: `backend/src/agentmonitor/modules/runtime_observation/application/queries.py`
- Create: `backend/src/agentmonitor/adapters/persistence/runtime_observation/sqlite/repository.py`
- Create: `backend/migrations/versions/v1_0600_m06_runtime_core.py`
- Create: `backend/migrations/versions/v1_0601_m06_runtime_correlation.py`
- Create: `backend/migrations/versions/v1_0602_m06_runtime_state_outbox.py`
- Create: `backend/migrations/versions/v1_0603_m06_runtime_indexes.py`
- Modify: `backend/migrations/catalog.toml`
- Create: `backend/tests/live/claude/test_runtime_observation.py`
- Create: `backend/tests/runtime_observation/integration/test_real_linux_commit.py`
- Create: `backend/tests/runtime_observation/integration/test_runtime_schema_chain.py`

**Interfaces:**
- A04 implements `InspectProcessesV1(PlatformInspectionRequestV1) -> PlatformInspectionOutcomeV1` and `PortablePlatformPrimitivesV1` with read-only, bounded Linux metadata.
- A01 implements `LocalSessionDiscoveryPortV1`, `LocalSessionMetricsPortV1`, and `LocalProcessCorrelationPortV1`; M06 consumes `RuntimeObservationBatchV1` and implements `CollectionOutcomeCommitPortV1[RuntimeObservationBatchV1]` plus `GetRuntimeCommitStatusV1(run_id)`.
- M06 exposes `ListAgentProcessesV1`, `ListAgentSessionsV1`, `GetSessionTreeV1`, and `SessionCorrelationDecisionV1`; weak evidence remains `unresolved`.

- [ ] **Step 1: Write the failing real Linux/provider test**

```python
def test_real_claude_process_and_session_commit_without_private_fields(real_running_claude: RealRunningClaude) -> None:
    receipt = real_running_claude.collect_runtime()
    session = real_running_claude.runtime.get_session(receipt.session_ids[0])
    assert session.provider_key == "claude"
    assert session.account_id == real_running_claude.confirmed_account_id
    assert session.provenance.source_id == real_running_claude.approved_local_source_id
    assert not set(session.serialized()) & {"command_line", "environment", "prompt", "response", "raw_path"}


def test_runtime_schema_chain_reaches_alert_parent(migrated_database: Path) -> None:
    schema = inspect_sqlite_schema(migrated_database, through="v1_0603")
    assert schema.revisions[-4:] == ("v1_0600", "v1_0601", "v1_0602", "v1_0603")
    assert {"runtime_session", "runtime_correlation_evidence", "runtime_event_outbox"} <= schema.tables
```

- [ ] **Step 2: Run Red**

Run: `python3 -m pytest backend/tests/live/claude/test_runtime_observation.py backend/tests/runtime_observation/integration/test_real_linux_commit.py backend/tests/runtime_observation/integration/test_runtime_schema_chain.py -q`

Expected: FAIL because the production Linux/A01/M06 path cannot yet collect and commit the reserved real process/session. If no safe representative process is running, record `Blocked`.

- [ ] **Step 3: Implement the minimum read-only runtime slice**

Use PID plus start identity to prevent reuse, approved selectors and fields only, explicit partial/error states, no `/proc/*/environ`, no arbitrary command line, no process control, and Strong-only automatic account correlation. Create the complete frozen `v1_0600` through `v1_0603` DDL allocation so `v1_0700` has its required parent; do not seed telemetry or claim later scale/index evidence. Keep unresolved/conflict states visible.

- [ ] **Step 4: Run Green against the same reserved process**

Run: `python3 -m pytest backend/tests/live/claude/test_runtime_observation.py backend/tests/runtime_observation/integration/test_real_linux_commit.py backend/tests/runtime_observation/integration/test_runtime_schema_chain.py -q`

Expected: PASS with real process/session provenance, one durable commit receipt, and unchanged running process/profile state.

- [ ] **Step 5: Review and commit**

Review privacy, PID reuse, correlation, no-control, and migration evidence; commit: `git commit -m "feat(observation): add real claude runtime slice"`.

---

### Task 6: `ST-OBS-003` — Authenticated API, generated client, browser, and live milestone gate

**Epic:** `EPIC-OBS-01`

**Requirements / acceptance:** `AC-V1-001/002/005/006/007/008`, `AC-UI-002/003/006`, `AC-LIVE-001/004/005`, `AC-PROC-001..005`, `AC-HIST-001`, `AC-TEST-001..006`; applicable `API-HTTP`, `API-OAPI`, `UI-ACC`, `UI-CAP`, `UI-RUN`, and `UI-COL` scenarios from P01/P02.

**Contracts:** `CTR-API-001..003`, `CTR-UI-001`, `CTR-REG-001..007`, `CTR-PROV-002`, `CTR-COL-001/002/005`, `CTR-CAP-001/003`, and `CTR-RUN-001..003/007` at V1.

**Files:**
- Create: `backend/src/agentmonitor/api/v1/routers/registry.py`
- Create: `backend/src/agentmonitor/api/v1/routers/providers.py`
- Create: `backend/src/agentmonitor/api/v1/routers/collection.py`
- Create: `backend/src/agentmonitor/api/v1/routers/capacity.py`
- Create: `backend/src/agentmonitor/api/v1/routers/runtime.py`
- Create: `backend/src/agentmonitor/api/v1/schemas/registry.py`
- Create: `backend/src/agentmonitor/api/v1/schemas/providers.py`
- Create: `backend/src/agentmonitor/api/v1/schemas/collection.py`
- Create: `backend/src/agentmonitor/api/v1/schemas/capacity.py`
- Create: `backend/src/agentmonitor/api/v1/schemas/runtime.py`
- Modify: `contracts/openapi/agentmonitor-v1.json`
- Modify: `frontend/src/generated/api/index.ts`
- Create: `frontend/src/features/accounts/AccountPage.tsx`
- Create: `frontend/src/features/providers/ProviderPage.tsx`
- Create: `frontend/src/features/collectors/CollectionRunPanel.tsx`
- Create: `frontend/src/features/command/CapacityPanel.tsx`
- Create: `frontend/src/features/sessions/SessionPanel.tsx`
- Create: `frontend/tests/browser/p02/claude_vertical_slice.spec.ts`

**Interfaces:**
- Exposes exact P01 operations `registry_list_accounts_v1`, `registry_list_provider_installations_v1`, `provider_get_capabilities_v1`, `collection_list_runs_v1`, `capacity_get_account_v1`, `capacity_list_quota_windows_v1`, `runtime_list_processes_v1`, `runtime_list_sessions_v1`, and `runtime_get_session_v1`.
- All operations require the approved M01 permission, return producer-owned V1 DTO semantics through P01 schemas, and are consumed only through `frontend/src/shared/api/**` plus the generated client.

- [ ] **Step 1: Write the failing built-browser vertical test**

```typescript
test("renders one real Claude account with quota and runtime provenance", async ({ page }) => {
  await loginAsOwner(page);
  await page.goto(`${process.env.AGENTMONITOR_TEST_ORIGIN!}/accounts/${process.env.AGENTMONITOR_TEST_ACCOUNT_ID!}`);
  await expect(page.getByText("Claude", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Quota windows" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Running sessions" })).toBeVisible();
  await expect(page.getByText(/source|observed|freshness|version/i).first()).toBeVisible();
  await expect(page.getByText(/sample|demo|placeholder/i)).toHaveCount(0);
});
```

- [ ] **Step 2: Run Red**

Run: `npm --prefix frontend run build && npx --prefix frontend playwright test frontend/tests/browser/p02/claude_vertical_slice.spec.ts`

Expected: FAIL because the real account/capacity/runtime published ports are not yet transported and rendered.

- [ ] **Step 3: Implement thin routes and truthful browser views**

Map each route one-to-one to its published application port, regenerate artifacts through the integration writer, and render exact availability/freshness/provenance/partial states. The browser never computes domain health or substitutes zero for unknown.

- [ ] **Step 4: Run Green and the complete real milestone gate**

Run: `python3 tools/automation/run.py AUTO-TEST && python3 tools/automation/run.py AUTO-QUALITY && python3 tools/automation/run.py AUTO-BUILD && python3 tools/automation/run.py AUTO-DOCS-CHECK`

Expected: exit `0`; T2/T3/T4/T5/T6 evidence proves the same opaque Claude account and observation IDs across adapter, registry, run, domain records, API, and browser. Required Blocked rows prevent milestone completion.

- [ ] **Step 5: Review, reconcile, and commit**

Reconcile authoritative provider views, default-profile/running-process no-change evidence, DB/log/artifact privacy scans, contract/migration/generated diffs, dependency/license status, and docs. Commit: `git commit -m "feat(v1-m3): validate real claude vertical slice"`.

## Completion rule

`V1-M3` is complete only when all six Stories are reviewed, the one account is owner-confirmed, both approved Claude observation lanes reach the same account through real production paths, and Task 6 passes. Unsupported or unavailable required lanes, unverified versions, missing live owner evidence, or skipped T5/T6 work leave the milestone intermediate or Blocked; they never justify fake data or a broader provider claim.
