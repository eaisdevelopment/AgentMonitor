# Module plan: M08 — M4 operations health and diagnostics

- Status: **Approved for I01 contracts, pure health/readiness/diagnostic projections and application facades; real producer leaves remain root integration**
- Plan version: `0.2.0`
- Primary owner: M08 operations; independent planning agent `/root/dashboard_connection_ui`
- Parent plan: [M08 operations](../modules/m08-operations/plan-v1.md), `0.2.0-draft`
- Story: `ST-OPS-001`; target milestone `V1-M4`, canonical [Task 6](../../superpowers/plans/2026-09-19-agentmonitor-v1-m4-claude-fleet-alerts.md#task-6-st-ops-001--publish-operations-contracts-diagnostics-and-m4-evidence)
- Requirements: `FR-OPS-002/005/006`, `NFR-RES-001`, `NFR-OBS-001`
- Acceptance contributions: `AC-OPS-003/006`, `AC-V1-003/005/006/007/008`; supporting `AC-UI-004/005`, `AC-TEST-001/002/003/006`
- Proposed published contracts: `CTR-OPS-001..007`, `CTR-APP-001`, V1 `1.0.0`; focused executable subset below
- Consumers/reviewers: root/integration, PLAN-FND, PLAN-DB, M01–M07, P01/P02, security/privacy, test-integrity
- Approved by/date: root integration, 2026-09-29, under the owner's active full M4 implementation authority
- Evidence: planning inspection only. All new behavior scenarios are **Not Run**. Neither full M4 nor full M08 is accepted by this document.

This focused proposal follows [AGENTS.md](../../../AGENTS.md), the [engineering skill](../../../.agents/skills/agentmonitor-engineering/SKILL.md), [SDLC](../../engineering/sdlc.md), [real-system testing](../../engineering/testing-strategy.md), [module boundaries](../../architecture/modules.md), [contract policy](../../architecture/contracts-and-versioning.md), [security](../../architecture/security.md), and [completion gates](../../engineering/completion-and-automation-gates.md). It narrows implementation scheduling within the wider M08 plan; it does not remove its later V1 requirements.

## 1. Outcome and boundaries

The owner can distinguish a responsive service, a service ready for ordinary work, a degraded collector, and unavailable evidence. The diagnostics page shows authoritative application/schema/API/client/frontend/adapter versions and allowlisted operational states. A failed provider cannot make unrelated queries fail or be hidden behind a healthy label.

### M4 executable scope

- Pure health/readiness classification, freshness and required-component policy.
- Read-only, deadline-bounded aggregation through published leaf health ports.
- Liveness with no database, filesystem, provider, authentication-store, or network dependency.
- Authoritative version inventory and configuration **presence/validation**, never values.
- Typed diagnostic summary; explicit unavailable/partial/unknown states.
- Public M08 application facade in `health.py`, `diagnostics.py`, `service.py`.
- Root-owned HTTP, generated client, built diagnostics UI, and executable M4 integration evidence.
- Publication of CTR-OPS-003/005/007 support declarations, preserving future ownership without claiming their workflows exist.

### Wider M08 work remains outside this Story

Backup creation/rotation/catalog, restore/maintenance activation, retention/purge/export jobs, downloadable diagnostic bundles, artifact scanners, durable operations audit/outbox, native installation/service management and macOS operation remain separate later M08/deployment increments. No backup/export/restore button or route is added merely because its contract family is declared. FR-OPS-003/004, AC-OPS-004/005 and naturally elapsed retention/rotation horizons are not passed here. M06's owner-association settings file must be covered by a future approved backup design; an SQLite-only backup is not a full installation backup.

### Isolated ownership

This planning assignment writes **only this new file**. Proposed later module allocation:

```text
backend/src/agentmonitor/modules/operations/domain/health.py
backend/src/agentmonitor/modules/operations/application/health.py
backend/src/agentmonitor/modules/operations/application/diagnostics.py
backend/src/agentmonitor/modules/operations/application/service.py
backend/tests/operations/pure/test_health_policy.py
backend/tests/integration/operations/test_health_and_diagnostics.py
```

For I01, the M08 agent is sole assigned writer of `contracts/operations_v1.py`
under root contract stewardship, the operations module and its own pure tests
and module evidence. Root owns compatible additions to existing producer
contracts, composition, API/schema/routes, generated files, frontend,
automation, documentation registries and migrations. Producer owners implement
their own leaves. M08 imports only its own code, reviewed standard library
orchestration and published contracts. No deep producer imports, DB handles,
frameworks, SQL, OS/provider I/O or private configuration access.

Root approves the exact section 4 type vocabulary, 32-component/16-indicator/
8-reason bounds, registered manifest, and 2,000-ms aggregate budget. Asyncio
cancellation/fan-out is approved only in M08 `application/health.py`; root will
codify that narrow application import allowance without admitting asyncio in
domain code. Producer adapters must enforce their actual remaining I/O budget;
the application timeout alone is insufficient for blocking SQLite. I01 pure
tests use constructed immutable results with no fake injected I/O collaborator.
Real adapter/application integration waits for root's genuine leaf wiring.
Unsupported backup/export/retention protocols are declarations only, with no
placeholder service methods or API routes.

## 2. Requirements and traceability

| Requirement/AC | M4 behavior | Contracts | Defined scenarios |
|---|---|---|---|
| FR-OPS-002 | Distinct liveness/readiness/health; real DB/IAM/collector leaves; typed diagnostics | OPS-001/002/004/006 | M4-OPS-PURE-001..005; M4-OPS-DB-001; M4-OPS-HTTP-001/002; M4-OPS-BROWSER-001 |
| FR-OPS-005; AC-V1-007 | No secret/content/config value/path/account identity in summary, HTTP or evidence | OPS-004/006; FND-003/004 | M4-OPS-PURE-006; M4-OPS-HTTP-003; M4-OPS-SEC-001 |
| FR-OPS-006 | Application, schema, API, generated-client, frontend, module/adapter versions originate in owned metadata | OPS-001/004; FND-007; DB-001 | M4-OPS-PURE-007; M4-OPS-DB-001; M4-OPS-HTTP-004; M4-OPS-BROWSER-001 |
| NFR-RES-001; AC-OPS-003 | One optional component failure degrades health without losing other sections/readiness | OPS-001/002/006; APP-001 | M4-OPS-PURE-002/004/005; M4-OPS-HTTP-002; M4-OPS-LIVE-001 |
| NFR-OBS-001 | Safe codes, component key, UTC timestamps and correlation; bounded structured local records | OPS-004; FND-004 | M4-OPS-HTTP-003; M4-OPS-SEC-001 |
| AC-OPS-006 | Health/diagnostic GET does not collect, retry or change cadence; fleet gate uses actual M04 run evidence | OPS-006; COL-005 | M4-OPS-HTTP-005; M4-OPS-LIVE-002 |
| AC-V1-003 | Versioned closed schemas, current generated client and real HTTP/browser | OPS-001/002/004; API-001; UI-001 | M4-OPS-HTTP-006; M4-OPS-BROWSER-001 |
| AC-V1-005/006/008 | Bounded independent privacy/boundary review, current runbook, no invented health/counts | all focused contracts | M4-OPS-ARCH-001; M4-OPS-SEC-001; M4-OPS-GATE-001 |

`OPS-*`, `FND-*`, `DB-*`, `COL-*`, `APP-*`, `API-*`, `UI-*` in this table are the corresponding `CTR-` register IDs. These are contributions to release-wide criteria, not full-V1 acceptance.

## 3. Domain design and invariants

All declarations are immutable frozen dataclasses with slots, following `TechnicalValueV1`. Public schemas are closed; no untyped dictionaries, arbitrary metadata, exception text or free-form descriptions. Times are aware UTC. `as_of` is supplied explicitly to pure rules; elapsed timeout handling uses an injected application clock/real runtime mechanism, not patched time. Numeric counts use nonnegative exact integers, reject booleans, and have explicit units.

### States

```text
HealthStateV1 = healthy | degraded | unavailable | incompatible | maintenance | unknown
ReadinessStateV1 = ready | not_ready | setup_required | maintenance | unknown
ComponentCriticalityV1 = required_for_normal_readiness | optional_degraded
ComponentResultStateV1 = available | unavailable | incompatible
```

Liveness is separately `healthy | unavailable`, based only on in-process responsiveness and lifecycle phase supplied by foundation. It does not aggregate component health. Maintenance can remain live. `degraded` is a health state; optional failure can leave readiness `ready`. The illustrative Task 6 assertion `readiness in {ready,degraded}` must be corrected by root to this parent-plan distinction; no new readiness meaning is invented.

### Classification

1. Root supplies one registered manifest containing every required leaf, including missing registrations. Producers never select their criticality.
2. Missing, failed, malformed, incompatible or timed-out producers remain visible as unavailable/incompatible/unknown results; they are not dropped.
3. A required component must have a fresh valid healthy sample for normal readiness. Required degraded/unavailable/incompatible/unknown blocks readiness. Safely uninitialized IAM yields `setup_required`; active operations maintenance yields `maintenance` through a future published receipt, never an inferred PID.
4. Optional non-healthy samples degrade overall health and preserve ordinary readiness when required components are healthy. Healthy empty optional collections are valid only after a successful complete producer query; zero is not a fallback.
5. Freshness expires at `valid_until <= as_of`. Expired required samples block readiness. Aggregate validity is bounded by the earliest participating sample expiry; M08 cannot extend freshness. Last success alone is not current health.
6. Duplicate component keys, unexpected keys, invalid UTC/order/types, unknown reason/indicator keys, or a sample for another requested component are rejected and classified safely at the producer boundary. Caller cancellation propagates; isolated leaf failures do not cancel siblings or provider collection.
7. Readiness reports all blockers deterministically by registered key. Overall health preserves incompatible/maintenance/unavailable causes; it cannot simply average component states. A responsive API may truthfully return a not-ready resource.
8. All GET workflows are read-only: no migration, WAL checkpoint, provider collection/login, recovery, lease mutation, retention, or silent repair. Do not persist health timestamps merely to make a GET work.

## 4. Public contracts and exact synchronization proposal

Root publishes the declarations in `backend/src/agentmonitor/contracts/operations_v1.py`; M08 remains sole semantic producer. Names/types below freeze the focused proposal for producer review, not current implementations. Every port lists its contract major as V1. P01 owns authorization/transport; M08 receives an already-authorized disclosure class and never mints authority.

### CTR-OPS-006: bounded leaf protocol

| Dataclass | Exact fields |
|---|---|
| `ComponentRegistrationV1` | `component_key: str`, `criticality: ComponentCriticalityV1`, `indicator_keys: tuple[str, ...]`, `contract_major: int = 1` |
| `ComponentHealthRequestV1` | `component_key: str`, `correlation_id: OpaqueIdV1`, `as_of: datetime`, `deadline: datetime`, `disclosure_level: Literal["administrator", "service"]`, `indicator_keys: tuple[str, ...]` |
| `ComponentIndicatorV1` | `key: str`, `value: int | None`, `unit: Literal["count", "milliseconds"]`, `availability: FieldAvailabilityV1` |
| `ComponentHealthSampleV1` | `component_key: str`, `component_version: str | None`, `state: HealthStateV1`, `checked_at: datetime`, `valid_until: datetime`, `last_success_at: datetime | None`, `reason_codes: tuple[str, ...]`, `indicators: tuple[ComponentIndicatorV1, ...]` |
| `ComponentHealthResultV1` | `component_key: str`, `outcome: ComponentResultStateV1`, `sample: ComponentHealthSampleV1 | None`, `checked_at: datetime`, `reason_code: str`, `contract_major: int = 1` |

Published protocol: `async GetComponentHealthV1.__call__(request: ComponentHealthRequestV1) -> ComponentHealthResultV1`. `available` means a valid sample exists, not that its health is healthy; unavailable/incompatible require `sample=None`. An unavailable optional leaf still occupies its manifest slot. Result and sample component keys must equal the request. `valid_until > checked_at`; `last_success_at <= checked_at`; clocks in the future beyond the approved bounded tolerance yield unknown, not fresh.

Initial manifest keys: `foundation`, `configuration`, `database`, `identity_access`, `registry`, `provider_system`, `collection_control`, `capacity`, `runtime_observation`, `alerting`, and registered `provider.claude`. Required: foundation, configuration, database, IAM, registry. Optional: provider/collector/capacity/runtime/alerting lanes. Root may register additional leaf keys only with explicit producer ownership and reviewed indicator/reason allowlists. This manifest does not claim optional implementations or provider compatibility exist.

Limits proposed for synchronization: 32 components, 16 indicators/component, 8 reason codes/sample; key/code length at most 96 ASCII characters from registered code-owned vocabulary. No user-supplied key/code is passed through. Indicators allowed initially are M04 `due_count`, `running_count`, `blocked_count` and registered operational timing indicators if actually measured; quota, money, tokens, PIDs, account counts/IDs or labels are excluded from diagnostics. `value=None` must carry a non-available status. Unmeasured indicator keys are omitted or explicitly unavailable, never zero.

The request deadline is at most 2,000 ms after its actual `as_of`, root-supplied policy version `operations-health.v1`. All leaves run concurrently within that aggregate budget. Each producer must obey its remaining deadline and enforce bounded underlying I/O. A `wait_for` around uncancellable synchronous SQLite work is insufficient. Root selects a reviewed cancellable/bounded DB mechanism and verifies actual elapsed behavior. No new configurable environment keys are required for this first policy.

### CTR-OPS-001/002: focused views and query ports

| Dataclass | Exact fields |
|---|---|
| `HealthViewV1` | `state: HealthStateV1`, `generated_at: datetime`, `valid_until: datetime`, `components: tuple[ComponentHealthResultV1, ...]`, `availability: QueryAvailabilityV1`, `reason_codes: tuple[str, ...]`, `correlation_id: OpaqueIdV1` |
| `ReadinessViewV1` | `state: ReadinessStateV1`, `generated_at: datetime`, `valid_until: datetime`, `blocker_component_keys: tuple[str, ...]`, `reason_codes: tuple[str, ...]`, `correlation_id: OpaqueIdV1` |
| `LivenessViewV1` | `state: Literal["healthy", "unavailable"]`, `checked_at: datetime`, `correlation_id: OpaqueIdV1` |
| `OperationsQueryRequestV1` | `as_of: datetime`, `deadline: datetime`, `correlation_id: OpaqueIdV1`, `disclosure_level: Literal["administrator", "service"]` |

`GetHealthV1(request) -> HealthViewV1`, `GetReadinessV1(request) -> ReadinessViewV1`, and `GetVersionInventoryV1(request) -> VersionInventoryV1` are async read-only facade queries. `GetLivenessV1(as_of, correlation_id) -> LivenessViewV1` is synchronous with no I/O. The facade may reuse one completed health aggregation for readiness/diagnostics within the same request; it never extends a producer's validity or uses cached-as-current results after expiry. Every required blocker is independently represented.

M4 exposes no maintenance commands; future `EnterOperationsMaintenanceV1`/`ExitOperationsMaintenanceV1` remain with the wider plan. `service.py` does not synthesize a maintenance success receipt.

### CTR-OPS-004: authoritative versions and diagnostics

| Dataclass | Exact fields |
|---|---|
| `VersionValueV1` | `value: str | None`, `availability: FieldAvailabilityV1`, `source: Literal["application_manifest", "build_manifest", "schema_port", "adapter_manifest", "generated_artifact"]` |
| `ComponentVersionV1` | `component_key: str`, `version: VersionValueV1` |
| `VersionInventoryV1` | `application_version: VersionValueV1`, `schema_version: VersionValueV1`, `api_version: VersionValueV1`, `openapi_version: VersionValueV1`, `client_version: VersionValueV1`, `frontend_version: VersionValueV1`, `components: tuple[ComponentVersionV1, ...]`, `availability: QueryAvailabilityV1` |
| `ConfigurationPresenceV1` | `key: str`, `owner: str`, `presence: Literal["configured", "missing", "invalid", "unknown"]` |
| `DiagnosticSummaryV1` | `versions: VersionInventoryV1`, `health: HealthViewV1`, `readiness: ReadinessViewV1`, `configuration_presence: tuple[ConfigurationPresenceV1, ...]`, `generated_at: datetime`, `valid_until: datetime`, `availability: QueryAvailabilityV1`, `reason_codes: tuple[str, ...]`, `correlation_id: OpaqueIdV1` |

Published `async GetDiagnosticSummaryV1(request) -> DiagnosticSummaryV1`. `administrator` permits the closed summary; `service` permits only liveness/minimal readiness, not secret-presence or detailed diagnostic fields. Unauthorized disclosure is denied by P01 before entering M08. No arbitrary `to_dict()` fallback is permitted; boundary serialization must follow closed schemas.

Available version requires a validated safe value from its named source. Missing, unknown, unavailable and incompatible stay distinct; `None` cannot be reported available. Application version comes from the checked-in/pinned backend manifest, actual schema revision from DB's leaf, adapter version from M03's registered descriptor. `api_version` is the actual OpenAPI `info.version`; `openapi_version` is the document's schema protocol version. These are distinct from the `/api/v1` routing major. Client version is the actual generator/schema identity in generated provenance, not a guess copied from application version. Frontend version comes from its reviewed package manifest and is accompanied by the actual served-build digest; a declared package version alone is not a matching-build claim. Integrity checks reconcile frontend/OpenAPI/client hashes from CTR-FND-007; missing artifacts remain unknown. Different independent version numbers alone do not prove an incompatible build.

Root fills the existing CTR-FND-007 `component_versions` tuple with registered `api`, `frontend`, `client` and `openapi` entries from the real sources above, retaining its actual artifact hash fields. No new FND metadata field is required. M08 receives that receipt and approved configuration presence via injected published ports; it never reads files or `.env`. Schemas require code-owned safe semver/revision/digest patterns per field and reject raw paths/branch/user text. Metadata absent in a development build is visible and makes the diagnostic/version section partial; it is not filled with `0.0.0` merely as a fallback. A literal actual manifest version of `0.0.0` is reported with its real source, not treated as runtime evidence of a release.

### CTR-OPS-003/005/007: publication without unfinished workflow exposure

Task 6 requires publishing these families. Root must synchronize their declarations with the parent plan while keeping operational behavior deferred. No fake backup/job/export/consistency result is returned by M08.

- **OPS-003** support: `BackupViewV1` fields are opaque backup/job IDs, trigger enum, lifecycle enum, requested/completed UTC times, actual schema/application versions, nullable verified byte size/checksum, integrity enum and safe reason. `RestoreJobViewV1` fields are opaque restore/backup/job IDs, parent-plan phase enum, timestamps and safe reason. Publish typed backup/restore protocol declarations from parent section 4.4; do not expose their transport or implement placeholder methods. Any storage reference is internal and cannot enter a public view.
- **OPS-005** support: `ExportJobViewV1` fields are opaque job/artifact IDs, purpose enum, format/schema version, parent-plan state enum, UTC requested/completed/expiry times, nullable actual record/byte counts and checksum, safety enum, download-available boolean and safe reason. `available` requires real verified safe artifact; no artifact store or downloader is claimed here. Publish request/query protocol declarations only.
- **OPS-007** support: immutable `OperationsParticipantRequestV1(operation_id: OpaqueIdV1, correlation_id: OpaqueIdV1, deadline: datetime, contract_major: int, cutoff: datetime | None, limit: int, cursor: str | None, preview_digest: str | None, checkpoint_id: OpaqueIdV1 | None, prepared_database_ref: OpaqueIdV1 | None)` and `OperationsParticipantReceiptV1(participant_key: str, operation_id: OpaqueIdV1, outcome: Literal["complete", "partial", "blocked", "unavailable", "incompatible"], generation: int | None, digest: str | None, count: int | None, next_cursor: str | None, checked_at: datetime, reason_code: str)`. `limit` is 1..200; each operation validates its required and forbidden fields. Publish separate `preview_expired`, `query_export_records`, `purge_expired`, `validate_staged_consistency`, `validate_activated_consistency` protocol signatures, not a string-selected generic operation. Export records remain source-module-owned typed families; no generic dictionary records. No participant execution is scheduled by this M4 health increment.

These future declaration details are synchronization inputs, not permission to implement restore/export/retention now. If root needs a materially different frozen family, return to producer/consumer sync before implementation; do not put convenience stubs in the facade.

### CTR-APP-001: bounded dashboard projection ownership

The register and master plan assign its semantic production to M08. Task 6's word “consume” is interpreted as consuming root-injected **published leaf queries**, not importing a composite that recursively consumes M08. Root must synchronize this interpretation before exposing an overview route.

`DashboardOverviewRequestV1(scope_kind: RegistryScopeKindV1, scope_id: OpaqueIdV1 | None, as_of: datetime, deadline: datetime, correlation_id: OpaqueIdV1, limit: int)` uses the published registry scope kind and 1..200 bound; `global` requires null scope ID and other kinds require a valid ID. `DashboardOverviewV1` carries the exact registry `RegistryScopeSnapshotV1`, M05 capacity aggregate, M06 `RuntimeOverviewViewV1`, M07 alert summary, M04 `CollectorHealthV1`, M08 `HealthViewV1`, and separate `QueryAvailabilityV1` for each section. Nullable sections must carry explicit unavailable/unknown/unsupported state; no missing count becomes zero. Each section is an existing producer-owned typed DTO, never `object`, a copied manual DTO or an arbitrary dictionary. Scope snapshot revision must accompany scope-dependent sections; membership conflicts yield partial/unresolved, not a guessed join. M08 creates no new quota math or account/agent attribution.

The current checkout lacks the final global M05 aggregate and M07 alert-summary DTO/query definitions. Root must publish their exact approved types first; no generic overview contract or route may hide that gap. A future `GetDashboardOverviewV1` calls those exact queries concurrently with operations health, never provider I/O. The currently approved account-quota UI is preserved until root allocates any overview integration. No counts/cards are invented to occupy absent sections.

### Public application facade

`health.py` owns deadline orchestration and pure-classification invocation. `diagnostics.py` owns version/config-presence allowlist projections. `service.py` exposes only the published queries, injected manifest, leaves, version/config receipts and in-process lifecycle port. P01 imports this public facade; M08 never imports P01 or root composition. Health leaves must not call `GetHealthV1`, `GetReadinessV1`, diagnostics, dashboard overview or a DEP composite containing them. DEP may later consume M08 readiness; M08 may consume only narrow DEP leaf facts, preventing cycles.

## 5. Consumed ports and data ownership

| Producer | Exact proposed published leaf/receipt | M4 source and safe degradation |
|---|---|---|
| PLAN-FND | `GetLifecycleStateV1() -> LifecycleStateV1` with phase/last safe failure code, no resource handles | Foundation reads owned in-memory phase. Liveness uses this only; no task-success placeholder. Root publishes support type in FND contract. |
| PLAN-FND | `GetBuildMetadataV1() -> BuildMetadataV1`; existing registered `component_versions` plus hashes | Root loads reviewed actual build manifests/artifact provenance. Missing version/hash stays unknown. |
| PLAN-FND | `GetConfigurationPresenceV1() -> BootstrapConfigurationV1` plus its approved descriptor registry | Existing validated receipt only. No second configuration read, environment dump or secret serialization. |
| PLAN-DB | `async GetDatabaseHealthV1(request: ComponentHealthRequestV1) -> DatabaseHealthV1` | Root publishes DB-owned `DatabaseHealthV1(reachable: bool, schema_revision: str | None, compatibility_state: str from DB's existing closed state vocabulary, integrity_state: passed/failed/not_checked, integrity_checked_at: datetime | None, policy_state: passed/failed/not_checked, checked_at: datetime, reason_codes: tuple[str, ...])`. Adapter probes active file through bounded real read-only SQLite, no immutable/quiescent inspector, checkpoint, repair or business-table query. An old startup integrity receipt retains its original time; a reachability probe is not full integrity proof. |
| M01 | `async GetIamHealthV1(request: ComponentHealthRequestV1) -> IamHealthV1` (CTR-IAM-008) | Existing DTO; M01 checks owned initialization/policy/repository via its ports. No hash/token/session count returned. Uninitialized is setup-required; unreachable/incompatible blocks readiness. `retention_health=not_run` remains not-run, not healthy. |
| M02 | `GetRegistryHealthV1(request) -> ComponentHealthResultV1` (OPS-006 implementation) | Producer-owned bounded query, actual registry reachability/compatibility. Empty fresh registry can be healthy. No names/IDs or fabricated inventory counts. |
| M03 | `GetProviderSystemHealthV1(request) -> ComponentHealthResultV1`, registered capability/version receipts | Existing safe manifests only; unverified provider version remains explicit. No executable/provider invocation on health read. |
| M04 | `async GetCollectorHealthV1(request: ComponentHealthRequestV1) -> CollectorHealthV1` (CTR-COL-005) | Existing DTO. M04 derives actual due/running/blocked counts from its scheduler/repository state at checked time, not a truncated run page. No installed scheduler means unavailable, not healthy zero. |
| M05/M06/M07 | Producer-owned `GetComponentHealthV1` implementation | Health of their projection/query infrastructure only. Provider quota exhaustion, unknown activity or an active alert is not automatically an infrastructure crash. Missing producer remains explicit optional unavailable. |
| A01 through M03 | `provider.claude` OPS-006 leaf from existing registered capability/last safe collection outcomes | Read existing safe evidence; no collection/login/credential read. Naturally absent failure states remain unknown/Blocked in live evidence. |

All signatures above require root/producer synchronization. M08 can consume only the shared contract declarations. Root composition may instantiate producers/adapters and inject structural implementations; M08 does not use a deep import to obtain a missing implementation.

No M08 table/migration is needed for the focused stateless projection. No health history, outbox or operation audit table is introduced. Existing IAM/security audit remains owned by IAM. Health failures can emit only approved FND-004 events through an injected sink: component/code/correlation/timestamp/version with **no subject account IDs**. Foundation's current enums allow only foundation events, so root must publish compatible operations component/event vocabulary before logging them; arbitrary strings are not a shortcut.

## 6. Current evidence and external boundaries

Source inspection on this revision established:

- No `operations_v1.py`, M08 application facade or diagnostics page exists.
- `bootstrap.build_metadata()` reads actual backend version/schema range, but returns null frontend/OpenAPI/client hashes and an empty component tuple.
- Existing `InspectSchemaCompatibilityV1` is a quiescent immutable inspector that rejects WAL/SHM; it must not be reused as an active-service periodic probe or made healthy by checkpointing in a GET.
- `IamHealthV1` and `CollectorHealthV1` exist as DTOs; their health query implementations are absent.
- Current migration head is `v1_0603`. Task 6's `v1_0702` expectation is the planned post-alert head, not current evidence. Tests reconcile the actual DB revision against the root-reviewed target after alert migrations; neither schema value is returned as a hardcoded substitute.
- Foundation provides in-process lifecycle state but no public operational health/readiness contract. Current API has no operations route.

Module planning reads no owner data root, provider files, credentials, process environments or shared browser. Real verification will use isolated actual configuration/SQLite/server/browser for local claims; owner fleet evidence remains separate. M08 initiates no provider work during either diagnostics or its integration tests.

## 7. Security and privacy

Only code-owned component keys, safe versions/revisions, states, bounded technical counters, UTC times, availability and correlation IDs are serializable. Configuration items expose approved registered key/owner and configured/missing/invalid/unknown status. They expose no effective value, value length/digest/prefix/suffix, filename/path, arbitrary source label, or provider credential presence. Presence metadata is detailed authenticated information.

Diagnostics exclude account/organization IDs, names/emails, provider identities/profile references, PIDs, working directories/projects/tasks, quota/cost/token values, raw errors/SQL/HTTP/CLI output, headers/cookies, prompts/responses/source, `.env`, arbitrary environment and credentials. Build source revisions/digests must be explicitly safe technical identifiers; no branch/user/path text. M08 serialization cannot introspect `__dict__` or traverse component internals. Unknown fields/indicator keys fail closed; scanners are defense in depth, not permission to gather unsafe inputs.

P01 proposed routes: `/api/v1/health`, `/api/v1/readiness`, `/api/v1/versions` require `read:status`; `/api/v1/diagnostics` requires `read:diagnostics`. Browser read-origin and token-scope checks retain M2 controls. `/api/v1/liveness` may have explicit minimal public admission after root/P01 security synchronization, with only state/time/correlation and non-I/O host/origin guards; it must not resolve IAM through SQLite. No unversioned health route is proposed. If root chooses authentication for liveness, it must use an independent in-process authority mechanism or retain liveness as an internal port rather than introduce DB dependency. Detailed readiness is not made public as a convenience.

## 8. Configuration and operations

No dependency, secret, environment key, persisted setting or service-manager action is added in this focused plan. Root provides startup-only typed manifest and bounded aggregation policy; all defaults/limits are reviewed at contract sync. Missing configuration/version receipts yield explicit degradation. Required security configuration invalidity prevents writable startup; a running application's stale/invalid receipt never becomes valid through an M08 fallback.

Readiness/diagnostics inspect existing safe state. Closing the browser cannot stop the collector. Collection rate limits are enforced by M04/A01, not M08; operations health reflects their real state without claiming that a lack of visible errors proves compliance. The runbook explains liveness vs readiness vs collector degradation and codes; no unimplemented backup/restore command is documented as available.

## 9. Test design before implementation

All new scenarios below are Not Run. Pure T1 tests may construct immutable sample inputs and explicit times with no I/O. DB/API/browser claims use production implementations at their real boundaries. No injected fake health producer, monkeypatch, replay, synthetic provider state, direct telemetry seeding, copied owner profile or in-memory SQLite is allowed.

| Scenario | Boundary and real resources | Meaningful expected Red | Required Green |
|---|---|---|---|
| M4-OPS-PURE-001 | T1 pure required healthy/missing samples | Required missing component ignored | All manifest keys preserved; missing required blocks readiness |
| M4-OPS-PURE-002 | T1 pure optional degraded sample | Optional failure makes all service work unready or falsely healthy | Health degraded; readiness ready; failed leaf visible |
| M4-OPS-PURE-003 | T1 UTC boundary/schema/IAM inputs | Expired sample/current schema or uninitialized IAM labeled ready | Equality expiry unknown; setup_required and incompatible blockers accurate |
| M4-OPS-PURE-004 | T1 invalid keys/times/tag consistency | Invalid/duplicate/foreign-component sample accepted | Closed invariants reject invalid data safely |
| M4-OPS-PURE-005 | T1 simultaneous partial component inputs | Sibling results lost; last success labeled current | Deterministic independent results and minimum validity |
| M4-OPS-PURE-006 | T1 diagnostic field/presence projection | Config value/free-form metadata representable | Only closed presence/state/version fields retained |
| M4-OPS-PURE-007 | T1 version availability policy | Null/missing version called compatible/current | Unknown/unavailable preserved; mismatches classified by provenance |
| M4-OPS-DB-001 | T2 actual file SQLite, real migrations/bootstrap and PLAN-DB/M01/M04 leaves | No live schema/health leaf or false health under actual WAL | Actual schema matches catalog target; active WAL read succeeds without checkpoint; query-only probe records original integrity time |
| M4-OPS-HTTP-001 | T3 actual ephemeral loopback production server/IAM/SQLite | Missing operations endpoint or missing detailed authorization | Authenticated closed views; unauthenticated 401/scoped denial; no detailed public disclosure |
| M4-OPS-HTTP-002 | T3 real unhealthy leaf condition from safe isolated DB permission/removal/lock or naturally failed component | Unavailable required leaf labeled ready; unrelated endpoint crashes | Required blocker + live separate responsiveness; unaffected queries stay usable within deadline |
| M4-OPS-HTTP-003 | T3 actual random isolated bootstrap/password/token/config flow | Summary response or logs expose prohibited value/field | Memory-only test credentials absent from bounded emitted response/logs/artifacts; no actual credential printed or committed |
| M4-OPS-HTTP-004 | T3 real actual build and migrated schema | Version endpoint guesses/misreports schema/client/build | Compare independently with catalog, manifests, generated provenance and served assets; missing metadata explicit |
| M4-OPS-HTTP-005 | T3 repeated real health/diagnostic reads against actual collector state | GET creates runs/retries/profile changes | Run IDs/count/cadence unchanged solely by GET; elapsed scheduled runs distinguished from request causality |
| M4-OPS-HTTP-006 | T3 actual OpenAPI/generator/client | Missing/invalid typed routes/client drift | Current generated artifacts compile and call real endpoints; no handwritten transport |
| M4-OPS-BROWSER-001 | T4 real built UI, actual server/SQLite and generated client | Missing diagnostics page/version/state labels | Actual values/availability shown; keyboard/focus/non-color labels; usable 1920×1080 and narrow viewport |
| M4-OPS-LIVE-001 | T5/T6 actual owner fleet and naturally unavailable adapter/source | Real failing account masks another account/service | Affected account/component explicit; independent real collection/HTTP/browser continue; no manufactured provider outage |
| M4-OPS-LIVE-002 | T5/T6 actual M04 admitted polling/provider run evidence | Operations polling triggers collection or masks over-polling | Actual per-source timestamps/cadence agree with approved policy; no extra provider I/O |
| M4-OPS-ARCH-001 | Actual checkout import graph/contracts | Deep import/composite cycle/cross-table access | M08 consumes leaf contracts only; generated V1 frontend access |
| M4-OPS-SEC-001 | Actual source/build/HTTP/structured logs/evidence inspection | Prohibited fields/config/secret/raw text reach output | Allowlist inventory and admitted existing scans clean; separate independent review |
| M4-OPS-GATE-001 | Root's actual full-M4 catalog and artifacts | Gate missing or a required Story/scenario absent/blocked | Canonical gate fail-closed; only exact all-required Passed evidence permits full-M4 claim |

Required failure resources are isolated AgentMonitor-owned DB/files only; root first approves the bounded failure-test packet. Do not corrupt/remove the owner's active DB, revoke provider auth, exhaust credits, signal provider agents or change the clock. If a genuine timeout condition is unavailable, pure deadline classification may pass but the real elapsed timeout scenario remains Blocked. An already-absent port/import is not a behavioral Red; integration tests first establish valid setup and fail on actual unavailable/missing behavior or assertion. No test-only production path is added to manufacture a timeout.

Proposed canonical selectors, for root to implement and register before completion claims:

```bash
backend/.venv/bin/python -m pytest backend/tests/operations/pure/test_health_policy.py backend/tests/integration/operations/test_health_and_diagnostics.py -vv
backend/.venv/bin/python -m pytest backend/tests/api/v1/test_operations_routes.py -vv
backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py operations
python3 tools/automation/run.py AUTO-M4-EXIT
```

These new paths/selectors/routine are **proposed**, not existing verified commands. Root owns their registration; do not use an absent selector or static planning check as behavior evidence. Use existing AUTO-DOCS-CHECK/AUTO-QUALITY/AUTO-BUILD and generation check as applicable after implementation; a limited existing routine cannot certify missing M4 scopes.

## 10. Implementation increments

| Increment | Owner/files | Red first | Minimal production work and exit |
|---|---|---|---|
| OPS-M4-I00 | Root shared contracts/producer sync | Contract invariant and ownership review | Freeze focused types/leaves/disclosure/version sources and gap resolutions; this proposed file is not that approval |
| OPS-M4-I01 | M08 domain + root declarations | PURE-001..007 behavioral assertions | Pure aggregation/readiness/freshness/projection; no real-boundary health claim yet |
| OPS-M4-I02 | Producer owners + PLAN-DB/FND | DB-001 real WAL/leaf assertions | Publish actual deadline-bounded leaves; root injects through composition; no implicit migration/checkpoint |
| OPS-M4-I03 | M08 application facade | HTTP/integration-002/004 available boundaries | health.py aggregation, diagnostics.py allowlist, service.py facade; no private imports |
| OPS-M4-I04 | Root P01/P02/generated | HTTP-001/003/005/006 and BROWSER-001 | Versioned authorized routes, generated transport, real diagnostics UI; retain unavailable state |
| OPS-M4-I05 | Root integration/test/security | LIVE-001/002 and GATE-001 | Actual fleet isolation/cadence, independent bounded review, all six Story evidence and canonical gate |

Refactor reruns the same meaningful selectors. Root records sanitized Red command/time/reason before production, exact Green and post-refactor evidence. New leaves can be implemented independently within producer-owned paths once shared signatures are frozen. Shared contracts/composition/generated files remain serialized under root ownership. A missing provider state blocks only that scenario; it cannot justify simulation or a broader acceptance claim.

## 11. Documentation outputs and root handoff

Root integrates this focused approval into the planning registry and exact ownership/contracts before implementation. Update operations module/contract docs, diagnostics/runbook, API route/permission descriptions, configuration presence/version sources, traceability, known limitations, and actual test evidence in the same implementation change. Wider backup/restore/install procedures remain Planned where not executed. Root updates Task 6's illustrative readiness/schema assertions to real contract/catalog truth.

### Full M4 executable artifact proposal — root owns this work

Propose `AUTO-M4-EXIT`, `tools/automation/implementations/auto_m4_exit.py`, `docs/evidence/v1-m4-acceptance-status-v1.json`, and an explicit M4 scope/scenario catalog allocated by root. This routine does not exist yet and is not implemented by the M08 planning agent.

The gate must bind exact checkout/artifact hashes, plan/contract versions, database schema target, real environment and evidence status for **all six canonical Stories**. It must account for the six intended Claude owners with real enrollment or owner-recorded unavailability, registry organizations and owner identity, per-account collection/history/organization aggregates, runtime correlation/tree/stall evidence, real alerts/rules/lifecycle/HTTP/browser, and this operations/diagnostics increment. Required unavailable cases remain non-success under the applicable criterion; an owner-unavailable outcome allowed by AC-LIVE-001 is not a provider capability pass. Existing bounded gates support their named scope only.

Fresh/upgrade migration checks, OpenAPI validation/diff/current client, generated build, privacy/secrets/dependency review, documentation and real browser/live cadence/isolation must join the same catalog. Unexecuted provider states/platform/time windows cannot be hidden by Passed pure tests. The artifact may be updated to truthful intermediate status while work continues; **no full M4 acceptance** follows from this plan, an M08 facade, or AUTO-TEST alone. Commands fail nonzero when required evidence/artifacts are absent, stale for the bound revision, Failed, Blocked or Not Run; output states each missing prerequisite without sensitive data.

## 12. Dependency and license impact

No new dependency. Existing Python standard library, approved dataclasses/common contracts, existing SQLite/SQLAlchemy/Alembic producer adapters, FastAPI and generated frontend stack suffice. Root retains existing admitted scanners/build/quality tools. Downloadable bundle scanning is not quietly added as a prerequisite for a read-only typed summary. If later work needs a new package/scanner or transport, stop for documented license/security/necessity/transitive admission and an updated plan.

## 13. Risks, open decisions and stop conditions

| Gap/risk | Smallest closure | Owner/state |
|---|---|---|
| Active-service DB health cannot use existing immutable inspector (R-011) | Publish DB-owned live read-only bounded leaf and real WAL test; preserve original integrity timestamps | Root/PLAN-DB; Pending |
| FND-007 provenance absent; client/API/frontend identity ambiguous (R-007/R-019) | Populate existing registered component-version entries and artifact hashes from actual manifests/provenance; unknown if absent; real served-artifact comparison | Root/PLAN-FND; Pending |
| IAM/collector DTOs exist without leaf implementations | Producer-owned query ports and owned adapter methods; no M08 table/import fallback | Root/M01/M04; Pending |
| Composite-health/DEP/overview cycles (NFR-ARCH-001) | Leaf-only manifest; M08 never consumes its own overview/readiness composite | Root/M08; Proposed fixed invariant |
| APP-001 missing exact M05/M07 overview DTOs | Freeze published aggregate/alert-summary types before overview exposure; preserve partial sections meanwhile | Root/M05/M07; Pending |
| Timeout cancellation only cosmetic (NFR-RES-001) | Producer I/O bound and actual elapsed isolated failure verification; absent natural provider timeout remains Blocked | Producer/test; Pending |
| Health green mistaken for quota/provider rate-limit/full-M4 proof | Separate producer/runtime facts, real M04 cadence and explicit full-M4 gate catalog | Root/test; Pending |
| Sensitive detailed operational state exposed (R-005/R-013) | Closed typed allowlist and scoped/origin-protected routes; minimal non-I/O liveness disclosure synchronized | Root/P01/security; Pending |

Stop affected implementation and return to root if a contract/type/meaning needs changing, a producer port is absent, private imports/SQL are needed, a dependency/secret/provider access is introduced, a runtime health GET would write/checkpoint/migrate, an exact real failure resource is unavailable, or another owner overlaps files. This escalation is contract coordination, not a new user permission request for already-authorized M4 work.

## 14. Delivery, migration and rollback

Synchronize/publish additive V1 declarations first, implement pure policy, then real producer leaves, facade, authorized routes/generated client/UI, and full-M4 evidence. This stateless M08 increment requires no new tables or migration; M07's schema changes remain independently owned and must be included in the root target. No compatibility-breaking change is proposed. Future backup/restore/retention protocol evolution follows parent version policy/ADR requirements.

Rollback is removal of this additive UI/route exposure and reverting its code to a prior compatible build; preserve all accounts, history, settings/provider profiles. Do not downgrade/remove M07 data or rewrite migrations as part of operations rollback. On failed health reads return typed unavailable/blockers; do not repair owner state. Post-delivery verify actual schema/version sources, expected required manifest, scoped reads, GET no mutation and actual browser messages.

## 15. Focused definition of ready

- [ ] Root reviews/approves this focused M4 plan and exact declarations/disclosure/producer ownership.
- [ ] Required leaf signatures and actual producer implementation allocations are synchronized; no private coupling remains.
- [ ] Authoritative FND/DB/client/frontend metadata path and live WAL leaf policy are frozen.
- [ ] Expected meaningful Reds, isolated real resources, cleanup and evidence custody are allocated.
- [ ] Root-owned shared/API/generated/UI/automation write sets and full-M4 catalog are allocated.
- [ ] Focused privacy/boundary/dependency review resolves material gaps; no new dependency.

These items concern this increment, not approval of wider M08 restore/install/retention. Published future support types do not require their deferred workflow implementations before pure health work, but missing types required by an exposed route do block that route.

## 16. Approval and handoff record

| Reviewer | Decision | Scope/version |
|---|---|---|
| Independent M08 planning agent | Proposed; source inspection only, no production/test/service/browser/provider action | This document `0.1.0-proposed` |
| Root/integration and affected producers | Pending synchronization | Focused OPS-001/002/004/006, support OPS-003/005/007, APP-001 exact types |
| Security/privacy/test/P01/P02 | Pending | Disclosure, real-boundary evidence, generated V1-only consumers |

Required implementation handoff names requirement/AC IDs, exact contract/module/artifact versions, every changed file, Red/Green/refactor commands/results, real DB/HTTP/browser/platform/provider boundaries, all Failed/Blocked/Not Run items, security/privacy/migration/license/docs impact, and exact remaining integration work. This planning handoff supplies no runtime passing evidence and does not mark M4 or M08 complete.
