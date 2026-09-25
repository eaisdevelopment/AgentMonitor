# Provider-adapter plan: A02 — Codex and OpenAI account surfaces

- Status: **Draft — Milestone 0 evidence and contract synchronization pending; implementation is not authorized**
- Plan version: `0.2.0-draft`
- Proposed adapter version: `codex-adapter.v1` (unapproved)
- Proposed protocol target: `ProviderAdapterV1` protocol `1.0` (unapproved)
- Primary owner: A02 Codex provider-adapter implementation role
- Required reviewers: owner, root/integration steward, M02 Registry, M03 Provider system, M04 Collection control, M05 Capacity, M06 Runtime observation, A04 Linux, M08 Operations, P01 API, P02 UI, security/privacy, test-integrity, dependency/license, and operations reviewers
- Requirements: FR-ACC-005/006; FR-AUTH-001..006; FR-QUOTA-001..006; FR-BUDGET-001..006 for the A02-owned OpenAI API lane; FR-DISC-001/003/004/006/008; FR-COL-003..008; FR-SAFE-001/002; NFR-ARCH-001/002; NFR-TEST-001/002; NFR-SEC-001; NFR-PRIV-001/002; NFR-DOC-001; NFR-LIC-001; NFR-PLAT-001; NFR-PERF-001; NFR-RES-001; NFR-OBS-001; NFR-COMP-001
- Acceptance criteria: AC-V1-001/002/005/006/007/008; AC-LIVE-002/004/005/006/007; AC-UI-002/005/006; AC-PROC-001..004; AC-HIST-001; AC-OPS-003/006; AC-TEST-001..006
- Primary project risks: R-001..010, R-014, R-018, R-019, R-021, R-024
- Entry dependencies: approved M0 Codex and OpenAI API capability matrices and A02 handoff; synchronized common, registry, provider, collection, capacity, runtime, platform, operations, persistence, and safe-boundary contracts
- Accepted architecture decisions: ADR-0001, ADR-0003, ADR-0005, ADR-0006, ADR-0007, ADR-0010, and ADR-0011
- Target milestone: M2 Codex product/subscription/runtime adapter; M6 A02-owned OpenAI API usage/cost/budget expansion when supported by M0
- Approved by/date: pending

This plan follows the [product requirements](../../../product/requirements.md), [V1 acceptance criteria](../../../product/v1-acceptance-criteria.md), [provider-adapter contract](../../../architecture/provider-adapter-contract.md), [module boundaries](../../../architecture/modules.md), [security architecture](../../../architecture/security.md), [testing strategy](../../../engineering/testing-strategy.md), [SDLC](../../../engineering/sdlc.md), [completion and automation gates](../../../engineering/completion-and-automation-gates.md), [M0 execution plan](../../discovery/m0-execution-plan.md), and [contract register](../../contract-register.md). Structural types in this document are design proposals, not observed Codex/OpenAI data, provider fixtures, or live evidence.

## CS-1 alignment addendum — contract baseline 0.2.0

This addendum is normative for CS-1 and supersedes conditional ownership or
private-contract wording elsewhere in this Draft. The machine-readable
[contract baseline](../../contract-baseline.toml) and
[parallel ownership manifest](../../parallel-ownership.toml) remain unapproved;
they do not authorize implementation or provider access.

- A02 owns the Codex product/subscription/local adapter and the OpenAI API
  integration lane. M0 decides each exact capability's maturity, not lane
  ownership; an Unsupported or Deferred capability stays visible under A02.
- A02 implements, but never redefines, M03-owned `CTR-PROV-001..008`.
  Provider extensions live only under
  `backend/src/agentmonitor/contracts/providers/codex/<capability>/v1/**` and remain governed by
  `CTR-PROV-008`. Domain modules do not import A02 packages.
- A02 consumes `CTR-COMMON-001/002/004/007`, `CTR-CONFIG-001`,
  `CTR-FND-003/004/008`, `CTR-BOUNDARY-001..003`, and the typed REG/COL/CAP/RUN
  ports below. `CTR-COMMON-007` preserves absent, unsupported, unknown,
  unavailable, withheld, stale, unresolved, and exact-zero states. Provider
  HTTP uses M03-owned `CTR-BOUNDARY-002`; subprocess and approved-root reads use
  FND-owned `CTR-BOUNDARY-001/003`.
- A02 implements M08-owned leaf health port `CTR-OPS-006` without aggregating
  readiness. Durable domain events are emitted only through the owning domain
  workflow under `CTR-COMMON-006` and `CTR-EVT-001`; A02 owns no event store.
- `reauthentication_required` is the normalized provider state and maps to
  `provider_reauthentication_required` at API/UI. A Codex/OpenAI failure never
  maps to `dashboard_authentication_required` or clears the dashboard session.
- After M0 and contract approval, `subscription`, `local_state`, `openai_api`,
  and extension implementation lanes may proceed in parallel under
  `backend/src/agentmonitor/adapters/providers/codex/**`. They may not share a
  live alias/profile concurrently or edit common contracts, generated files,
  composition, migrations, manifests, or other shared-writer artifacts.

All Codex/OpenAI compatibility and account claims require the current real
boundary. No constructed value, response recording, mock, fake, or placeholder
may establish provider support, and Blocked/Not Run never mean Passed.

## 0. Authority, evidence state, and completion boundary

This is a planning artifact for A02 only. It authorizes no production code, test implementation, dependency installation, provider command, network request, local provider-file read, login/logout, account access, profile creation, `.env` change, database migration, API route, deployment, Git operation, or external resource change.

Milestone 0 has not executed. The plan therefore does not assert that any particular Codex command, slash command, app-server method, file, field, environment variable, authentication store, quota window, credit, reset time, session identifier, token count, process join key, or OpenAI billing endpoint is available, stable, safe, or machine-readable. Those facts remain `Unknown` until the exact M0 scenario produces reviewed evidence for an installed version, product/plan class, credential role, platform, and source.

The following are mandatory before a capability can move from design to implementation:

1. `M0-CDX-001..010` have terminal reviewed results and an accepted A02 handoff.
2. Applicable `M0-OAI-001..009` results exist for the A02-owned OpenAI API lane.
3. Applicable `M0-LNX-001..013` results identify safe process/session integration facts.
4. Each supported tuple names its exact source, side effects, provider/CLI version rule, account or role scope, freshness, precision, limits, and sanitized evidence reference.
5. Protected default-profile detection and read-only non-modification evidence are approved.
6. Any isolated `CODEX_HOME` or login/logout experiment has its own approved state-changing packet; read-only M0 does not authorize it.
7. M02, M03, M04, M05, M06, A04, M08, security, and test reviewers synchronize the exact contracts consumed or produced here.
8. The canonical planning gate passes for the entire planning catalog. This file alone cannot satisfy that gate.

Every provider-dependent scenario in this Draft is `Not Run`. No scenario is Passed by design review, documentation, source code, a constructed value, another account, another provider, or another Codex version.

## 1. Outcome and boundaries

### 1.1 Outcome

After approved implementation, A02 will expose only evidence-backed Codex and separately scoped OpenAI API capabilities through the provider-neutral M03 protocol. It will detect compatible installations, verify identity without guessing, report authentication health, collect supported native subscription quota/credit windows, produce safe local session/runtime inputs, and collect official OpenAI API usage/cost/budget data only where M0 marks the A02 capability Supported, without conflating it with the Codex subscription pool.

The adapter succeeds when:

- every enabled capability appears in a versioned manifest tied to M0 evidence and exact verified provider versions;
- unsupported, deferred, experimental, unavailable, authentication-required, wrong-account, unverified-version, stale, partial, and malformed states remain distinct;
- Codex subscription allowance and OpenAI API billing are separate resources and never summed as one balance;
- default `CODEX_HOME` and default/named profiles remain immutable;
- AgentMonitor-managed profiles are targeted only by a separately approved official authentication flow;
- local inspection returns closed typed operational metadata without reading or retaining prompts, responses, tool activity, source, arbitrary environment values, or credentials;
- account/session/process correlation is evidence-qualified and otherwise remains unresolved;
- all raw provider output is bounded, parsed at the boundary, and discarded before contracts, persistence, logs, diagnostics, or evidence;
- one A02 failure does not interrupt other provider adapters, the API, or dashboard queries;
- every external claim is verified against real installed executables, real approved files, real current accounts, real processes, or real official APIs as applicable.

### 1.2 Provider surfaces kept separate

A02 is one planning owner, not one undifferentiated collector. Future implementation uses separate internal source components and capability declarations:

| Surface | Purpose | Potential capabilities | Hard separation rule |
|---|---|---|---|
| Codex installation/version | Locate and identify approved installed Codex products | `installation.discovery`, diagnostics | No auto-install, update, execution from PATH without validated identity, or inferred compatibility |
| Codex interactive CLI | Owner-visible supported status/auth operations if M0 proves them | subscription quota, auth health, diagnostics | Interactive output is not assumed automatable or parseable |
| Codex structured/app-server | Structured supported protocol only if officially documented and safe | quota/auth/session/diagnostics as evidenced | No undocumented method discovery, raw RPC pass-through, or capability assumption |
| Codex authentication | Classify current profile/auth health and future managed reauth | identity verification, auth health, reauthorization | No credential reads; no default-profile logout/login |
| Codex local state | Read approved roots/files/fields | account/session/runtime metadata | Closed path and field allowlists per provider version; content and secret classes rejected |
| Codex session metadata | Produce typed session/metric inputs | local session discovery/metrics | No transcript, terminal, tool, prompt, response, or source capture |
| Codex process correlation | Supply provider evidence to M06 alongside A04 facts | local process correlation | No `/proc` implementation, environment reads, memory/terminal inspection, or account guess |
| OpenAI API administration | A02-owned official usage/cost/budget collection where M0 supports it | `api.usage`, `api.cost`, `api.budget`, project discovery | Separate provider key/resource/credential role/source; Codex auth never assumed to authorize it |

M0 may determine that one or more capabilities is Unsupported or requires a
separate provider/product key within A02. That is a valid maturity result; it
does not transfer OpenAI API lane ownership. A02 must not create a
private/browser workaround to fill a gap.

### 1.3 In scope

- Static A02 adapter construction and M03 manifest implementation.
- Evidence-scoped installation and version detection through approved safe execution/platform ports.
- Capability negotiation and exact source selection for Codex/OpenAI surfaces.
- Safe typed mapping from approved sources into M02 discovery/auth, M05 capacity, and M06 runtime input contracts.
- Codex-specific provider extension schemas whose fields are individually approved and bounded.
- Parser/source versions, verified provider-version rules, and fail-closed version drift behavior.
- Opaque profile/access-grant consumption with protected-default enforcement.
- Authentication-health and expected-identity comparison without credential access.
- Future official managed-profile reauthentication integration only after separate evidence and approval.
- Read-only local state/session inspection through approved path grants and allowlists.
- Provider-side correlation evidence; M06 owns the final session/account decision.
- Deadlines, bounded output, cancellation, single-attempt execution, safe errors, and no hidden retry.
- Adapter health, compatibility, safe diagnostics, documentation, test matrix, and rollback/disable behavior.

### 1.4 Out of scope

- Owning organizations, accounts, profiles, resource relationships, friendly names, or manual confirmation; M02 owns them.
- Owning provider protocol, generic outcome, manifest vocabulary, or compatibility history; M03 owns them.
- Scheduling, retries, leases, polling intervals, run history, or manual-refresh lifecycle; M04 owns them.
- Capacity validation, immutable history, normalized health, burn rate, forecast, or aggregation; M05 owns them.
- Process inspection, PID identity, ancestry, CPU/RAM, platform paths, or system services; A04/M06 own them.
- Runtime state, hierarchy, correlation decision, stall inference, or runtime history; M06 owns them.
- Alert lifecycle, dashboard notifications, public REST/OpenAPI, UI, persistence, backup, or deployment.
- Installing/upgrading Codex, changing Codex configuration, copying OAuth state, or selecting a user's default profile.
- Reading passwords, OAuth/access/refresh/API tokens, OTP/MFA/recovery codes, cookies, keyring values, or credential-file contents.
- Capturing prompt, response, reasoning, transcript, tool call/activity, terminal content, source-code content, Git content, arbitrary logs, or arbitrary process environment values.
- Using browser automation, traffic interception, private endpoints, undocumented app-server methods, or provider-cookie extraction.
- Killing, pausing, restarting, signalling, attaching to, injecting input into, rerouting, or changing credentials inside a running Codex process.
- Claiming transparent in-flight account switching. V1 monitors; it does not migrate a running session.

### 1.5 Ownership and proposed paths

After approval and explicit root allocation, A02 owns:

```text
backend/src/agentmonitor/adapters/providers/codex/**
backend/tests/adapters/providers/codex/pure/**
backend/tests/adapters/providers/codex/integration/**
backend/tests/adapters/providers/codex/live/**
docs/adapters/codex.md
backend/src/agentmonitor/contracts/providers/codex/<capability>/v1/**
docs/test-evidence/codex/**                    # sanitized records only, if allocated
```

The A02-owned OpenAI API administration implementation remains isolated below:

```text
backend/src/agentmonitor/adapters/providers/codex/openai_api/**
```

The path is reserved by the ownership manifest; reservation is not
implementation authority. A02 owns the semantic content of Codex/OpenAI
extension schemas, while the integration steward remains the sole shared-file
writer per allocated wave; A02 writes no extension file without that allocation.

Shared paths require a single explicit edit owner:

```text
backend/src/agentmonitor/composition/**
backend/src/agentmonitor/contracts/provider_system_v1.py       # M03 owner
backend/src/agentmonitor/contracts/registry_v1.py              # M02 owner
backend/src/agentmonitor/contracts/capacity_v1.py              # M05 owner
backend/src/agentmonitor/contracts/runtime_observation_v1.py   # M06 owner
configuration registry
dependency manifests and lockfiles
OpenAPI/generated client
migration chain
central contract/traceability/risk registers
```

A02 owns no database table or migration. Provider-specific parser/version data is code and schema metadata; product observations are persisted only by owning domain modules.

### 1.6 Allowed and forbidden dependencies

Allowed imports after approval:

- Python standard library;
- synchronized M03 contracts `CTR-PROV-001..008` and common safe primitives;
- M02 narrow target/profile/access-grant and discovery-input contracts, not Registry internals;
- M05 provider quota/usage/cost/budget input DTOs;
- M06 local-session/runtime-metric/correlation-evidence input DTOs;
- approved safe filesystem, subprocess, HTTP, cancellation, and credential/profile-reference ports;
- A02-owned parsers and extension schemas.

Forbidden imports and coupling:

- another provider adapter or provider-specific shared helper;
- any M02–M08 implementation, repository, ORM model, table, or migration;
- FastAPI, Starlette, SQLAlchemy, Alembic, React, UI, or generated-client code;
- direct `/proc`, process signalling, terminal control, debugger, keyring, browser storage, shell, or arbitrary environment APIs;
- a generic `dict[str, Any]`, raw JSON/blob, free-form stdout/stderr, or catch-all extension at a public boundary;
- direct public API routes or scheduler calls;
- an OpenAI SDK, retry library, watcher, parser, or CLI wrapper until dependency admission explicitly approves it.

The adapter uses direct argument vectors and approved executor/network ports. It never launches a shell or mutates global process environment.

## 2. Requirements and traceability

| Requirement/AC | Planned A02 behavior | Contract | Scenario IDs | Evidence gate |
|---|---|---|---|---|
| FR-ACC-005/006 | Discover compatible installation/account candidates and preserve owner-confirmation need | CTR-PROV-002/005; CTR-REG-004/006 | CDX-EXEC-001..003, CDX-LIVE-001/002 | M0 + real installed Codex and accounts |
| FR-AUTH-001 | Return evidence-backed auth health without converting source failure to auth state | CTR-PROV-006 | CDX-PURE-006, CDX-LIVE-003..006 | Pure mapping plus real auth surface |
| FR-AUTH-002/003 | Support only approved official managed-profile reauth and verify expected identity/history continuity | CTR-PROV-007; M02 reconciliation | CDX-LIVE-021..024 | Separate approved owner-run flow |
| FR-AUTH-004/005 | Accept no credential values and reject default/unknown profile mutation before external I/O | CTR-PROV-001/007; M02 target | CDX-SEC-001..006, CDX-LIVE-020/025 | Static/security review and real non-modification check |
| FR-AUTH-006 | Gate profile isolation and reauth on exact installed-version evidence | Manifest/CTR-PROV-007 | CDX-PURE-004, CDX-LIVE-021/026 | M0 deferred experiment then live approval |
| FR-QUOTA-001/002 | Map each evidenced Codex-native window separately and retain only approved extensions | CTR-CAP-001, CTR-PROV-008 | CDX-PURE-011/012, CDX-LIVE-007..010 | M0 semantics + authoritative comparison |
| FR-QUOTA-003..005 | Preserve inputs/provenance so M05 can derive health/forecast; A02 does not derive them | CTR-CAP-001/003/007 | CDX-CONTRACT-003/004, CDX-LIVE-009/010 | Contract and end-to-end real capacity path |
| FR-QUOTA-006 | Enable only Codex quota capabilities proven for exact version/plan/source | CTR-PROV-002/004 | CDX-PURE-001..005, CDX-LIVE-007 | M0 matrix and current live version |
| FR-BUDGET-001..006 | In A02's OpenAI API lane, map supported official usage/cost/budget separately with exact role/scope/money | CTR-CAP-002; CTR-PROV-002/004 | CDX-OAI-001..010 | M0-OAI plus real admin API/authoritative UI |
| FR-DISC-001/003 | Read approved Codex session metadata without altering launch flow or content capture | CTR-PROV-004; CTR-RUN-002 | CDX-FS-001..008, CDX-LIVE-011..014 | Real files/sessions and allowlist review |
| FR-DISC-004 | Produce evidence, never final guessed account association | CTR-REG-006; CTR-RUN-007 | CDX-PURE-007/008, CDX-LIVE-015..019 | Four-account/real-process correlation matrix |
| FR-DISC-006 | Map only supported safe model/project/session/token/context/activity/error fields | CTR-RUN-002; CTR-PROV-008 | CDX-CONTRACT-005, CDX-LIVE-012..014 | Field-by-field M0/live approval |
| FR-DISC-008 | Record adapter/parser/source/provider version on every local parse | CTR-COMMON-004; CTR-PROV-003/004 | CDX-PURE-009/010, CDX-FS-003/004 | Pure contract plus real version/file evidence |
| FR-COL-003 | Return retry dispositions and provider retry-after facts; never retry internally | CTR-PROV-004; M04 policy | CDX-PURE-013..015, CDX-LIVE-027 | Policy plus natural live rate/failure state |
| FR-COL-004 | Attach complete source/time/version/freshness/precision/confidence provenance | CTR-COMMON-004 | CDX-CONTRACT-001/002, CDX-LIVE-009/013 | Contract validation and live observation |
| FR-COL-006..008 | Explicit unsupported/unavailable/unverified/partial outcomes and no silent source downgrade/fabrication | CTR-PROV-002..004 | CDX-PURE-002/003/016, CDX-LIVE-028/029 | Pure policy plus real adapter outcomes |
| FR-SAFE-001/002 | Publish refresh/read/managed-reauth only; no agent-control or in-flight switching surface | Entire A02 surface | CDX-ARCH-001..004, CDX-SEC-007 | Import/schema/API absence review |
| NFR-ARCH-001/002 | Isolated adapter using published typed contracts and no owned domain state | A02/M03 contracts | CDX-ARCH-001..006 | Boundary automation and contract review |
| NFR-TEST-001/002 | Red-Green-Refactor with real boundaries and no prohibited doubles/data | Evidence contract | All CDX scenarios; CDX-TEST-001..003 | Independent evidence review |
| NFR-SEC-001; NFR-PRIV-001/002 | Minimal grants, bounded reads/output, no secrets/content/telemetry | Safe boundary ports | CDX-SEC-001..010 | Source/log/DB/artifact/network inspection |
| NFR-DOC-001; NFR-COMP-001 | Versioned adapter/schema docs, compatibility and runbooks | A02 docs/contracts | CDX-DOC-001/002 | Docs and compatibility gates |
| NFR-LIC-001 | Admit no package before direct/transitive review | Dependency record | CDX-DEP-001/002 | Lock/SBOM/notices/admission review |
| NFR-PLAT-001 | Linux-first through platform ports; macOS status remains explicit | Manifest/platform scope | CDX-EXEC-004, CDX-LIVE-030 | Real Linux; real macOS Passed or Blocked |
| NFR-PERF-001 | Bounded observations and process batches fit 100 accounts/200 processes without provider over-polling | Manifest constraints | CDX-PERF-001/002 | AgentMonitor-owned load + separate live rate evidence |
| NFR-RES-001; AC-OPS-003 | Malformed/failed A02 operation is contained and unrelated service/adapters remain available | CTR-PROV-004 | CDX-EXEC-008, CDX-LIVE-028 | Real adapter/service failure where safe |
| NFR-OBS-001 | Safe structured events include IDs/codes/durations only | Safe logging contract | CDX-SEC-008/009 | Real log/diagnostic scan |
| AC-LIVE-002 | Four intended Codex accounts are enrolled or owner-marked unavailable | M02/M03/A02 | CDX-LIVE-001/002/015..019 | Owner-controlled real accounts |
| AC-LIVE-004/005 | A02 conformance and quota/API values reconcile with authoritative surfaces | CTR-PROV/CAP | CDX-LIVE-007..010, CDX-OAI-005..009 | Current provider versions and time-matched comparison |
| AC-LIVE-006/007 | Managed reauth and naturally available failure/recovery states are truthfully verified | CTR-PROV-006/007 | CDX-LIVE-021..029 | Owner-run real scenarios; absent states Blocked |
| AC-PROC-001..004 | Real Codex processes/sessions correlate safely and persist metadata only | CTR-RUN-001/002/007 | CDX-LIVE-011..020 | 5–6 representative real processes and privacy proof |
| AC-UI-002/005/006; AC-HIST-001 | Typed real data reaches API/UI/history with provenance and truthful states | M05/M06 through P01/P02 | CDX-E2E-001..004 | Real service/SQLite/built browser |
| AC-OPS-006 | Approved polling remains within provider constraints | Manifest/M04 | CDX-LIVE-027, CDX-OPS-003 | M0 rate/cost evidence and observed cadence |
| AC-TEST-001..006 | Exact R/G/R, no doubles, real boundaries, visible Blocked/Not Run | Evidence summary | CDX-TEST-001..003 | Canonical test/quality gate |

Interpretation: A02 contributes evidence and typed observations; it does not independently pass registry enrollment, capacity derivation, runtime hierarchy, public API, browser, or release-wide acceptance criteria.

## 3. Domain and adapter design

### 3.1 Adapter composition

The proposed A02 package contains explicit components, not a provider god object:

- `CodexAdapterV1`: M03 protocol facade and immutable manifest.
- `CodexInstallationInspectorV1`: detects only approved executable identities and versions.
- `CodexSourceSelectorV1`: selects one exact M03-approved source policy without fallback invention.
- `CodexCliCollectorV1`: invokes reviewed read-only CLI operations through safe executor grants.
- `CodexAppServerCollectorV1`: invokes only documented reviewed structured methods if M0 supports them.
- `CodexLocalStateReaderV1`: reads only approved files/fields through safe path grants.
- `CodexAuthInspectorV1`: produces auth-health/identity evidence without credential reads.
- `CodexSessionMapperV1`: maps approved safe metadata into M06-owned input DTOs.
- `CodexCapacityMapperV1`: maps approved subscription windows into M05-owned input DTOs.
- `OpenAiAdminApiCollectorV1`: separately scoped A02 API usage/cost/budget component, enabled only for M0-supported capabilities.
- `CodexDiagnosticsV1`: emits bounded safe compatibility/health facts, never raw output.

Internal component names may change without a contract version change, but their boundaries must remain independently testable against real sources and must not merge subscription, API billing, auth, local session, or process concerns.

### 3.2 Manifest and capability negotiation

The adapter publishes an immutable `CapabilityManifestV1` through M03. Each declaration is scoped by:

- provider key and product surface;
- adapter and parser/source version;
- provider/CLI/app-server/API version rule proven by M0;
- platform;
- account plan or credential-role class;
- capability and typed payload schema version;
- exact source ID/class and allowed fallback chain, normally one source;
- stability and decision: supported, experimental, deferred, unsupported, or pre-approval unknown;
- freshness/data-latency/precision/confidence constraints;
- minimum safe interval, request/cost/concurrency budget when known;
- side-effect class and owner interaction requirement;
- approved extension schema and evidence references.

Only `supported` is enabled by default. `experimental` is disabled unless an explicit scoped grant exists and the source has its own security/ADR approval. `deferred`, `unsupported`, and `unknown` are visible but non-invokable.

The adapter does not decide polling or retries. M04 passes a previously resolved capability and `ProviderOperationContextV1`. A02 validates target/source/version/grants again before any I/O and returns exactly one CTR-PROV outcome.

### 3.3 Installation and version rules

Installation discovery uses platform-approved executable candidates and produces typed M02 discovery candidates. The adapter must:

1. resolve an approved candidate without trusting an unvalidated current directory or provider-controlled path;
2. verify regular executable identity, ownership/permission policy, and symlink resolution through the platform port;
3. run only the reviewed version operation through an argument vector and minimal environment;
4. prevent update/install/login prompts and stop if any appear;
5. parse the exact evidenced version scheme, which may be semantic, date-based, or opaque;
6. return `unverified_provider_version` for unknown/out-of-range formats, never approximate ordering;
7. record executable identity reference and version evidence without exposing a personal absolute path publicly;
8. never install, upgrade, downgrade, repair, or configure Codex.

Multiple installations remain distinct M02 installation candidates. A02 does not choose a global winner.

### 3.4 Source priority and no-silent-fallback rule

Possible source classes follow CTR-PROV-003: documented API, supported CLI, approved local metadata, then separately approved experimental private/browser. This order is not automatic permission.

For every invocation, M03 and M04 negotiate one exact source or one evidence-approved ordered chain. A02 may move to the next source only when the manifest, caller request, first outcome, and security policy all permit that transition. Provenance records the actual source and safe prior outcome. Missing, stale, cached, or locally inferred values never replace a failed live source as current provider-reported data.

Experimental browser/private sources remain unimplemented under this plan. Their need triggers a new ADR and threat review rather than a fallback.

### 3.5 Parsing and allowlist pipeline

All source handlers follow this fail-closed pipeline:

1. enforce deadline, cancellation, source, target, version, output/response size, and count bounds;
2. acquire only the opaque grant for the exact executable, file, profile, or host;
3. read/capture no more than the approved operation requires;
4. reject an unexpected content type, method, schema, version, path, file type, ownership, symlink, or field;
5. tokenize/parse only with a bounded parser; no `eval`, unsafe deserialization, dynamic import, or recursive unbounded traversal;
6. copy only named fields into an internal typed candidate;
7. discard raw bytes/output before returning from the boundary component;
8. validate semantics and cross-field invariants against the capability schema;
9. map into M02/M05/M06 typed DTOs and attach provenance;
10. return a safe typed failure on any mismatch, with no raw excerpt.

An allowlist entry records source ID, provider versions, parser/schema version, field path/name, type, unit, nullability, cardinality, maximum size, privacy class, destination contract, and M0/live evidence. Unknown fields are ignored only if the approved parser rule proves they cannot alter known-field meaning; otherwise the version is unverified or data invalid. Unknown values never enter a generic extension.

### 3.6 Authentication and identity model

Authentication inspection returns an outer operation outcome plus `AuthHealthObservationV1`. A02 may report only evidenced states: `healthy`, `refreshing`, `expiring`, `reauthentication_required`, `revoked_or_disabled`, `wrong_account_detected`, or `unknown`. Network/source failure is not an authentication state.

Identity evidence is classified, versioned, and scoped. A stable provider identifier may be returned only if M0 and M02 approve its privacy, lifetime, and resource scope. Email, display name, filesystem path, current default login, organization label, plan label, or timing alone is not proof.

Comparison against the expected opaque M02 identity yields `matched`, `mismatched`, or `unresolved`. The result mapping is capability-specific: `identity.verification` mismatch returns outer `success`, identity `mismatched`, and authentication `not_applicable`; `authentication.health` wrong-account observation returns outer `success`, identity `mismatched`, and authentication `wrong_account_detected`. Neither case rewrites Registry state. `authentication.reauthenticate` remains non-invokable in M0; its future workflow state named `wrong_account_detected` is not an M0 provider invocation result.

Auth-store mode may be reported only as an approved non-secret category. A02 never reads keyring values, token files, token fields, secret lengths/hashes, or credential contents to determine that category.

### 3.7 Profile protection and reauthentication

The owner's default `CODEX_HOME`, default authentication store, and default/named profile are immutable. Read-only observation may target them only after approved M0 path/side-effect review. Mutation-capable operations reject targets marked protected default or with unknown protection classification before resolving an executable or flow.

An AgentMonitor-managed Codex profile, if isolated-profile behavior is proven, uses an opaque M02 reference and a provider-supported profile root. Provider credentials remain provider-managed inside that official store and are never copied into `.env`, SQLite, backups, exports, logs, diagnostics, tests, or chat.

Future reauthentication follows CTR-PROV-007:

```text
requested -> awaiting_owner_action -> verifying -> succeeded
                                      -> wrong_account_detected
                                      -> failed
requested/awaiting/verifying -> cancelled | expired
```

Conditions:

- the exact target is AgentMonitor-managed and non-protected;
- the owner explicitly starts the flow and performs all browser/device/email/MFA interaction;
- A02 invokes only the officially documented command/flow approved for that Codex version;
- `/logout`, login on restart, or an equivalent provider operation is never run against the default profile;
- passwords, OTPs, MFA values, recovery codes, tokens, cookies, and secret-bearing URLs do not cross A02 contracts;
- expected identity is verified before M02 reconciles success;
- wrong-account leaves prior association/history intact and disables the pending managed profile until owner review;
- the flow never claims to switch an already running Codex process; existing processes may continue under launch-time identity until naturally exited;
- restart behavior is fail-closed: no automatic reauth continuation unless the synchronized flow proves it safe.

The exact logout/login command and isolated `CODEX_HOME` behavior are unknown and M0-gated. No command is specified here.

### 3.8 Subscription quota and credit mapping

When M0 proves a supported Codex subscription source, A02 maps it into `ProviderQuotaInputV1` without normalizing provider semantics. For each native window/item it preserves only evidenced fields:

- stable resource and native-window identity;
- scope and safe label field state;
- used, remaining, limit, or ratio field states with exact unit;
- reset/renewal instant, interval, timezone, and precision;
- credit/balance/status semantics where actually exposed;
- provider observation/data-through and collection times;
- source/provider/parser/adapter versions;
- precision, confidence, value kind, freshness, partial/missing reasons;
- approved safe Codex extension.

Missing is not zero. Used is not converted to remaining unless M05 has an approved derivation with exact compatible inputs. Credits are not assumed to be currency, tokens, or requests. Five-hour, weekly, model-specific, feature-specific, or other windows are not asserted until M0 confirms them. Windows are never combined inside A02.

### 3.9 OpenAI API usage/cost/budget mapping

The A02-owned OpenAI Admin/API billing surface remains a distinct manifest provider/product surface and target resource. It consumes a separately approved least-privilege credential reference and official documented HTTPS host/method/schema. Codex subscription credentials are never reused or assumed valid.

A02 maps official results into `ProviderUsageInputV1`, `ProviderCostInputV1`, and `ProviderBudgetInputV1`. It preserves exact organization/project/account/key-safe/model/token/request/time-bucket dimensions only where officially exposed. Money uses exact decimal text or integer minor units plus currency; binary floating point is prohibited. Pagination completeness, data-through time, latency, limit/credit availability, and missing dimensions remain explicit.

M0 may mark any `api.*` capability Unsupported or Deferred. It does not move the
lane to another adapter, and duplicate collectors are prohibited.

### 3.10 Local state and session metadata

Every approved root is an opaque access grant derived from M02/platform configuration. A02 never accepts an arbitrary path from provider data or API input. Before reading it validates resolved-root containment, symlink policy, file type, owner/mode, size, modification behavior, provider version, and parser version.

Candidate safe session fields are conditional until M0: provider session identifier, model identifier, approved project/repository label, approved task label or code, start/end/activity time, token/context counters with scope and units, safe status/error code, parent/subagent evidence, and profile/account evidence. Each absent or unsafe field remains explicit Unknown/Unsupported.

Explicitly prohibited fields and sources include transcript/event bodies, prompts, responses, reasoning, messages, tool names/arguments/results when content-bearing, patches/diffs, source paths/content, terminal history/output, arbitrary logs, shell history, Git content, arbitrary JSON blobs, credential/auth fields, cookies, and arbitrary environment values.

The parser must discard prohibited fields before a typed DTO exists. A redaction pass over a stored raw object is not an acceptable design.

### 3.11 Process and account correlation

A02 does not enumerate processes or read `/proc`; A04 produces safe process observations. A02 may produce provider-session/profile/account evidence that M06 evaluates alongside A04 facts.

Correlation evidence levels are synchronized with M02/M06. Examples of possible evidence categories are structural only:

- provider-issued stable session-to-profile/account join proven for the exact version;
- corroborated provider session ID and platform/process relation;
- owner-confirmed relation;
- weak timing/path/current-login/label hint;
- conflict or stale evidence.

Only an approved Strong rule may auto-correlate. Corroborated rules require exact synchronized criteria. Weak, conflicting, absent, or stale evidence yields unresolved. Current Codex login never retroactively labels a running session. Five to six concurrently running Codex processes and all four intended accounts form the target live matrix; unavailable combinations remain Blocked, not synthesized.

### 3.12 Outcome, timeout, retry, and failure mapping

A02 returns CTR-PROV-004 outcomes exactly. It does not retry. M04 owns retry/backoff after inspecting the typed disposition.

| Observed boundary condition | A02 outcome | Retry disposition | Required behavior |
|---|---|---|---|
| Capability not supported by evidence | `unsupported` | never | No external I/O if already known |
| Capability disabled/experimental grant absent | not invoked; if an invalid caller attempts invocation, `unsupported` with safe `capability_disabled` reason code | never until policy change | No external I/O |
| Unknown/out-of-range provider version | `unverified_provider_version` | after version review | Do not parse/guess |
| Official provider auth missing/expired | `reauthentication_required` | after reauthentication | API/UI maps `provider_reauthentication_required`; no repeated login prompts or dashboard logout |
| Credential role lacks permission | `authorization_insufficient` | after user action | Preserve scope and safe code |
| `identity.verification` expected-identity mismatch | outer `success`; identity `mismatched`; authentication `not_applicable` | `not_applicable` for outer success | Stop; preserve prior registry state; wrong-account owner review is a recovery action, not retry metadata |
| `authentication.health` wrong-account observation | outer `success`; identity `mismatched`; authentication `wrong_account_detected` | `not_applicable` for outer success | Stop; preserve prior registry state; the future reauthentication workflow remains non-invokable in M0 |
| Provider/network/daemon unavailable | `provider_unavailable` | policy-controlled after delay | No source downgrade unless explicitly negotiated |
| Official rate limit | `rate_limited` | after evidenced delay | Preserve retry-after precision if safe |
| Schema/field/semantic mismatch | `invalid_provider_data` | after version review or never | Discard raw result; mark capability degraded |
| Deadline elapsed | `deadline_exceeded` | policy-controlled | Cancel only AgentMonitor-owned operation |
| Caller cancellation | no completed provider outcome; M04 cancelled collection-run state | caller decision | Never signal a monitored agent |
| Interactive owner action required | `blocked_user_action_required` | after user action | No credentials in result |
| Adapter boundary defect | `internal_adapter_error` | unknown/never automatically | Safe code and correlation only |

Timeout budgets are capability/source-specific and derived from M0 latency evidence plus M04 policy. Output, response, file, item, page, redirect, and nesting bounds are fixed in approved source descriptors. Redirects and network hosts are allowlisted. Hidden SDK/CLI retries or update checks must be disabled or proven absent; otherwise automated polling for that source is blocked.

### 3.13 Provenance and extensions

Every success or permitted partial result includes `ObservationProvenanceV1` fields required by M03: actual source ID/class, source/parser/app-server/API version, Codex/OpenAI product version, adapter/protocol/schema versions, observed/data-through/collection times, freshness, precision, confidence, value kind, experimental flag, warnings, correlation/operation IDs, and M0 decision reference.

Candidate A02 extension schemas are placeholders until M0:

- `codex.subscription-quota.v1`;
- `codex.auth-health.v1`;
- `codex.local-session.v1`;
- `codex.process-correlation.v1`;
- `openai.api-usage.v1`, `openai.api-cost.v1`, and `openai.api-budget.v1` where M0 marks the A02-owned capabilities Supported.

Each extension field requires type, unit, nullability, bound, privacy class, consumers, compatibility, parser/provider-version scope, and live evidence. Unknown extension majors are non-invokable/non-persistable; no opaque JSON survives.

## 4. Public contracts

### 4.1 Implemented provider protocol contracts

A02 implements, but does not redefine:

| Contract | A02 responsibility | Approval blocker |
|---|---|---|
| CTR-PROV-001 `ProviderAdapterV1` | Static adapter facade and typed port resolution | Final M03 signatures and safe context |
| CTR-PROV-002 `CapabilityManifestV1` | Exact Codex/OpenAI evidence-scoped declarations | M0 decisions/version/role/platform scope |
| CTR-PROV-003 `ProviderSourceV1` | Codex/OpenAI source descriptors and allowed transitions | Official-source and side-effect review |
| CTR-PROV-004 `CollectionOutcomeV1[T]` | One validated typed outcome per invocation | Closed union/error/retry synchronization |
| CTR-PROV-005 `DiscoveryOutcomeV1` | Installation/account/project candidates | M02 safe identity/locator contracts |
| CTR-PROV-006 `AuthHealthOutcomeV1` | Auth-health and identity-comparison result | Observable non-secret auth signals |
| CTR-PROV-007 `ReauthFlowV1` | Managed-profile-only official flow implementation | Isolated-home/login evidence and coordinator ownership |
| CTR-PROV-008 provider extensions | M03-owned protocol; A02-owned schemas in the governed Codex namespace | M03 registry plus M05/M06 consumer opt-in |

A02 adds no generic execute method, raw command method, raw file read method, arbitrary endpoint method, or generic diagnostics dump.

### 4.2 Consumed registry contracts

A02 requires narrow synchronized M02 types rather than full Registry views:

- provider installation target with opaque executable reference, platform, provider-version evidence, and compatibility generation;
- monitoring-profile target with opaque profile locator/reference, purpose, lifecycle, protected-default classification, and expected identity assertion;
- account/resource target with internal scalar IDs and provider/resource scope, never friendly labels as identity;
- source/access policy and owner-confirmation state;
- reauthentication preparation/result reference.

Unknown protection classification blocks mutation. Missing expected identity makes identity-sensitive collection unresolved or blocked according to capability contract. A02 never persists or mutates Registry records.

### 4.3 Produced capacity inputs

For supported subscription quota, A02 returns M05-owned `ProviderQuotaInputV1`. For supported capabilities in its OpenAI API lane, it returns M05-owned `ProviderUsageInputV1`, `ProviderCostInputV1`, or `ProviderBudgetInputV1`.

Preconditions:

- manifest tuple is compatible and supported;
- target account/resource/profile and source are approved;
- provider version is verified;
- operation context contains only exact required grants;
- response/output is complete enough for success or explicitly allowed partial;
- every field maps to an approved semantic, unit, and field state.

A02 does not calculate capacity health, forecast, aggregation, derived spend remaining, or cross-window totals. M05 may reject the input. A02 treats that as a typed integration defect/outcome, not a reason to loosen parsing.

### 4.4 Produced runtime inputs

A02 produces M06-owned closed inputs only for enabled capabilities:

- `LocalSessionObservationInputV1`;
- `RuntimeMetricObservationInputV1`;
- approved provider-side relationship/state/correlation evidence inside `RuntimeObservationBatchV1`.

It never creates `AgentSessionViewV1`, normalized runtime state, hierarchy, account decision, or stall result. Provider raw state may appear only as an approved bounded safe code/extension. M06 owns normalized meaning and persistence.

### 4.5 Safe boundary ports consumed

The following ports must have one synchronized owner and version before A02 implementation:

- safe executable resolution and version inspection;
- direct subprocess execution with argument vector, minimal named environment allowlist, process-group cleanup, output bounds, deadline, and cancellation;
- safe file/root resolution and bounded regular-file read with ownership/permission/symlink checks;
- approved HTTPS client with host/method/redirect/TLS/response bounds and no hidden retry;
- provider-profile and credential-reference resolution that never exposes credential values to contracts/logging;
- monotonic deadline/cancellation context;
- platform information and safe process/session reference inputs.

The adapter cannot implement a private alternative if a port is absent. Absence keeps the capability Not Ready.

### 4.6 Adapter-owned extension contracts

Each approved A02 extension schema is versioned independently. A compatible minor may add an optional field only when absence is safe and every consumer tolerates it. Removing/renaming a field, changing type/unit/nullability/privacy/source meaning, or expanding from code to free text is breaking and requires a new major, consumer migration, and possibly an ADR.

### 4.7 Contract change assessment

All referenced surfaces are registered in contract baseline 0.2.0. The
CTR-PROV family is `evidence_blocked`; the remaining consumed contracts retain
their exact `proposed_aligned` or `evidence_blocked` maturity in
`contract-baseline.toml`. `contract-adoption.toml` binds their exact A02
relationship. None is Approved. Before A02 approval, the root must:

1. bind every A02 capability to an exact M03 port and M05/M06 payload version;
2. freeze the provider/product key and registration for A02's OpenAI API lane;
3. allocate safe execution/filesystem/network/profile port owners;
4. freeze narrow M02 target and protected-profile types;
5. freeze extension descriptors and consumers;
6. resolve reauth orchestration and audit ownership;
7. update the central contract register through synchronization review only if
   any registered meaning, party, or version changes.

Any later breaking change requires a change plan, versioned migration path, consumer review, and ADR.

## 5. Data and persistence

### 5.1 Owned persistent data

A02 owns no SQLite table, migration, repository, cache treated as truth, or provider credential store. It does not persist raw responses, output, files, session artifacts, compatibility history, telemetry, or test data.

Persistence allocation remains:

- M02: installation/account/profile/resource identity and opaque references;
- M03: adapter compatibility assessments and manifests/health history as approved;
- M04: collection run/schedule/backoff metadata;
- M05: capacity observations/projections/history;
- M06: process/session/runtime/correlation observations and history;
- M08: product health/backup/export metadata.

### 5.2 Adapter static/versioned assets

A02 source may contain only reviewed static metadata:

- capability/source identifiers;
- exact provider-version rule identifiers;
- allowlisted operation descriptors referencing approved command IDs, not secrets or user paths;
- closed parser schema definitions and field mappings;
- extension schema descriptors;
- safe error/reason code mappings;
- adapter/parser version declarations.

These assets contain no captured provider data, account identifiers, real paths, screenshots, raw outputs, or credentials.

### 5.3 Caches and temporary files

The default design uses no adapter-owned disk cache or temporary capture file. Bounded output is processed in memory and discarded at the boundary. If a real interface requires a temporary file, that requirement triggers security/operations review, an AgentMonitor-owned isolated directory, owner-only permissions, size/time bounds, guaranteed cleanup, incident handling, and real filesystem tests. It cannot use a provider profile directory or repository.

### 5.4 Retention, backup, restore, and migration impact

Adapter code/schema/version changes require no A02 database migration. Domain observations retain the adapter/parser/source/provider versions that produced them. Removing/disabling an adapter preserves existing history and marks new collection unavailable/disabled; it never deletes data.

Backups exclude `.env`, provider profiles, raw evidence, and credential stores. A02 participates only through safe version/health metadata. After restore, collection remains disabled until M02/M03 compatibility and protected-profile checks pass.

## 6. External and platform boundaries

### 6.1 Codex executable boundary

- Exact executable/version operations are supplied only by an approved operation register.
- Invocation is direct, never via shell.
- Working directory is an AgentMonitor-controlled neutral directory unless official behavior requires and approves another.
- Environment contains only explicitly named required variables; values are supplied opaquely and never logged.
- Auto-update, install, login, telemetry, pager, color/control sequences, and interactive behavior are reviewed.
- stdout/stderr are separately bounded; raw values are not logged or retained.
- cancellation terminates only the AgentMonitor-owned child/process group, never a monitored Codex agent.

### 6.2 Structured/app-server boundary

M0 must prove documentation, transport, version negotiation, methods, lifecycle, authentication, side effects, framing, message bounds, cancellation, and shutdown. A02 sends only typed reviewed requests and accepts only matching typed responses. It does not enumerate undocumented methods, proxy arbitrary JSON-RPC, expose raw messages, or keep a server alive outside its approved lifecycle.

If app-server startup writes caches/state or uses the default profile, those effects must be known and explicitly approved. Otherwise it cannot serve read-only collection.

### 6.3 Local filesystem boundary

- Roots come from approved grants, not string concatenation or provider content.
- Resolved files must remain within the root and meet type/owner/mode/link/size rules.
- Directory enumeration is bounded to approved names/patterns and depth.
- No recursive crawl.
- File changes during read yield retry-safe `invalid_provider_data`/partial according to approved semantics; A02 does not loop indefinitely.
- Provider state is never locked, touched, rewritten, renamed, copied, or normalized.
- Read side effects such as atime must be assessed in M0; an unacceptable effect blocks that source.

### 6.4 HTTPS/API boundary

For M0-supported capabilities in A02's OpenAI API lane:

- only official documented HTTPS hosts, methods, parameters, pagination, and credential role are allowed;
- TLS verification is mandatory; redirects are absent or explicitly allowlisted;
- credentials are resolved and inserted by the approved client boundary, never by DTO or argument string;
- request and response bodies are bounded and allowlist-parsed;
- no generation/model call is made to test billing; only approved read-only administrative operations are used;
- no automatic retries; M04 owns retry policy;
- provider request IDs may be retained only as safe opaque references if approved;
- source latency/data-through time and rate-limit headers are interpreted only with official semantics.

### 6.5 Linux and macOS boundaries

Linux is the first verified platform. A02 receives platform primitives from A04 and contains no Linux API logic. macOS compatibility remains architectural until real macOS evidence exists; absence is Blocked, never inferred from Python portability.

A02 never reads process memory, attaches to a PID, requests arbitrary process environment, or signals a process. Platform process metadata and provider session metadata join only through M06-owned evidence contracts.

### 6.6 Real verification boundary

Live verification targets four intended Codex accounts and five to six representative concurrently running Codex processes where naturally available. Account aliases remain local and opaque. The owner confirms identity and authoritative values. Tests do not exhaust credits, revoke auth, change budget, manufacture failure, or interrupt work solely to obtain a pass.

## 7. Security and privacy

### 7.1 Trust boundaries and controls

| Threat | Required A02 control |
|---|---|
| Malicious/replaced executable | approved path identity, ownership/permission checks, version compatibility, no PATH-only trust |
| CLI/app-server output includes secret/content | bounded capture, source-specific parser, field allowlist, raw discard, no diagnostic excerpt |
| Local file contains prompt/source/credential | path+field allowlist, schema/version gate, reject prohibited/unknown classes before DTO |
| Symlink/path escape | canonical approved root, no unapproved link following, regular-file/ownership checks |
| Default profile mutation | protected/unknown fail closed before external I/O; read-only operation review and pre/post evidence |
| Wrong account | expected opaque identity comparison, mismatch terminal, no Registry mutation |
| Current login mislabels old process | no current-login correlation rule; evidence/time scope and unresolved outcome |
| API credential reaches wrong host | host/method allowlist and owning credential resolver |
| Hidden retry/update consumes quota/state | prove absent/disable; otherwise source blocked |
| Huge/malformed data exhausts service | byte/item/page/depth/time bounds and typed invalid outcome |
| Error/log/evidence leak | stable safe codes/IDs only; no object/raw-output serialization |
| Adapter gains process control | forbidden imports/API surface and cancellation-handle separation |

### 7.2 Data allowlist and prohibited data

Before implementation, A02 produces a field register. Every accepted field names requirement, source, version scope, type, unit, semantic, privacy class, storage/display/export permissions, and evidence. No field register entry means no field.

Never read or persist:

- provider OAuth/API token/password/key/cookie/OTP/MFA/recovery material;
- prompts, responses, messages, reasoning, transcript contents, tool calls/arguments/results;
- source-code contents, patches, diffs, terminal input/output/history, arbitrary logs;
- arbitrary command lines or process environment values;
- raw provider payloads, CLI output, app-server messages, HTTP bodies, or local files;
- personal email/display identity unless a future approved contract establishes necessity; it is excluded by default.

### 7.3 Secret handling

Provider credentials remain in provider-supported storage or an approved local credential resolver. A02 contracts receive opaque references/grants only. AgentMonitor-managed secrets may be loaded by the application configuration boundary from protected `.env`, but A02 cannot enumerate, log, serialize, diagnose, return, or persist them.

No secret appears in command arguments, URLs, process titles, exception messages, screenshots, OpenAPI examples, evidence, or test output. Secret presence may be reported only as `configured`/`missing` by the owning operations/configuration module, not by A02.

### 7.4 Logging, diagnostics, and audit

Allowed structured fields: event name, component/adapter version, correlation/operation/run ID, safe internal installation/account/profile reference, capability/source safe key, provider version, outcome/safe reason, duration, bounded counts, and manifest fingerprint.

Forbidden log fields: executable/profile/file absolute paths, labels/emails, raw identity, request parameters containing provider IDs, output snippets, exception arguments before sanitization, source DTO dumps, response sizes that fingerprint secrets, and all prohibited content.

A02 does not own an audit table. M03/M04/M02 record compatibility/run/identity/auth workflow events through approved contracts. Diagnostics expose only manifest/compatibility/source/last safe outcome/version summaries.

### 7.5 No-mutation and no-control proof

Security review must prove:

- no write/open mode, rename, unlink, chmod, copy, move, provider-config edit, or credential-store mutation path exists for read-only capabilities;
- reauth mutation exists only behind CTR-PROV-007 managed-profile checks and is absent until separately approved;
- no logout/login operation can target a default/unknown profile;
- no signal, kill, pause, restart, attach, stdin, terminal, routing, or credential-switch contract/import exists;
- monitored PIDs never become cancellation handles;
- pre/post live checks show representative default profile/provider files/running processes were not modified by the approved method.

### 7.6 Incident and stop behavior

Stop immediately if an operation prompts for install/update/login/logout/consent, reaches an unapproved host, writes provider state, displays prohibited data, selects the wrong account, exceeds its request/cost/output budget, encounters unknown version/schema, requires private/browser access, or affects a running agent.

Do not retry or broaden access. Quarantine accidental sensitive evidence locally outside Git, record only a sanitized Failed/Blocked status, notify root/owner/security, rotate credentials if exposure is plausible, and require a new reviewed operation/plan before resuming.

## 8. Configuration and operations

### 8.1 Configuration ownership

A02 proposes no approved configuration key in this Draft. Candidate categories requiring synchronization are:

| Category | Proposed owner/source | Secret class | Rule |
|---|---|---|---|
| Installed executable reference | M02 installation/private platform locator | non-secret but sensitive path | opaque to contracts/logs; no auto-discovery override without validation |
| Profile root/reference | M02 monitoring profile/private resolver | provider-managed sensitive reference | default protection mandatory; no raw public path |
| OpenAI admin credential reference | provider credential/config resolver | provider-managed secret | value never enters A02 DTO/log/DB |
| Capability enablement/experimental grant | M02/M03 policy | non-secret audited setting | defaults disabled until evidence/approval |
| Timeouts/output/page limits | M03 manifest + M04 policy | non-secret | evidence-derived ceiling; operator may only tighten |
| Poll cadence/concurrency/retry | M04 | non-secret | A02 does not override |

Exact environment variable names are not allocated here. Provider-standard variables, if unavoidable, are passed by the safe execution boundary through an exact name allowlist and never read from an arbitrary environment map. The service never rewrites `.env` or provider configuration.

### 8.2 Health and readiness

A02 contributes a bounded health projection containing:

- adapter/protocol/manifest/parser/source schema versions;
- installation present/absent and compatible/unverified state;
- capability counts by supported/experimental/deferred/unsupported/disabled;
- source readiness and safe last-outcome category/time;
- auth-health category only when an approved observation exists;
- last successful collection time per safe capability key;
- rate-limit/backoff facts only as received from M04/approved source;
- field/parser/version mismatch counts;
- safe error/reason codes and next required operator action category.

It excludes account labels, paths, profile references, secrets, quota numbers, raw warnings, and provider payloads. One incompatible capability degrades that capability; it does not make unrelated adapters or dashboard liveness fail.

### 8.3 Operational procedures to document and automate

Future verified runbooks cover:

- inspect discovered Codex installation/version/compatibility;
- inspect capability and source readiness;
- diagnose unsupported, unverified, authentication-required, authorization-insufficient, wrong-account, rate-limited, invalid-data, deadline, and unavailable states;
- enroll/confirm a real account through M02 without exposing identity;
- perform an owner-run managed-profile reauth only after approval;
- disable/rollback one A02 capability or whole adapter without deleting history;
- reverify after Codex/OpenAI version/schema changes;
- investigate missing/stale sessions or quota without repeated provider calls;
- respond to possible secret/content/default-profile incident.

Exact commands remain Planned until implemented and real-tested. Prose command names do not count as automation.

### 8.4 Canonical automation obligations

A02 registers with repository-owned fail-closed routines rather than creating personal shell procedures:

- `AUTO-TEST`: select CDX T1/T3/T4/T5/T6/T7 scenarios and preserve Passed/Failed/Blocked/Not Run separately;
- `AUTO-QUALITY`: format/type/import-boundary/security/secret/prohibited-double/dependency/license/contract checks;
- `AUTO-DOCS-CHECK`: validate A02 requirements, contracts, field register, source matrix, scenario links, and runbooks;
- `AUTO-GIT-PREFLIGHT`: include A02 evidence/secret/provider-artifact exclusions before any commit/push;
- `AUTO-BUILD`: include adapter manifest/schema metadata, SBOM, and notices;
- `AUTO-DEPLOY`: preserve provider profiles and keep unsupported/unverified A02 capabilities disabled;
- `AUTO-BACKUP`/`AUTO-RESTORE`: prove provider credentials/profiles are excluded and A02 history remains domain-owned;
- `AUTO-RELEASE`: require current A02 compatibility/live matrix and visible Blocked cases.

The foundation/integration owner supplies the exact canonical command interface. A02 is not implementation-ready until the selectors and real-boundary evidence reporting exist and are themselves tested. Hosted CI cannot mark T5/T6 Passed.

### 8.5 Version-change trigger

Any Codex CLI/app-server/local schema, OpenAI API schema/role, adapter/parser, platform, operation descriptor, path/field allowlist, auth-store category, or account-plan change invalidates the affected compatibility assessment. Collection stops with `unverified_provider_version` until official review and real re-verification expand the matrix.

## 9. Test design before implementation

### 9.1 Integrity rules

- Tests exercise the real boundary they claim: real installed Codex, real approved files, real app-server/CLI, real owner accounts, real OpenAI API, real running service, real SQLite through owning modules, and real built browser.
- No mock, fake, stub, emulator, replay/cassette, copied provider response, fixture provider file, demo account, seeded telemetry, placeholder value, monkeypatch, fake clock/filesystem/subprocess/HTTP client, or test-only production branch.
- Constructed values are allowed only in pure no-I/O policy/contract tests and never prove provider parsing or compatibility.
- Provider parsing is verified against the real current source at execution time. Raw source is not retained as a fixture.
- Dynamic values are reconciled by identity/scope/unit/time/freshness/precision, never hardcoded.
- Naturally unavailable failure states remain Blocked. Tests do not exhaust credits, revoke credentials, corrupt profiles, change budgets, or terminate active agents for convenience.
- Each behavior records meaningful behavioral Red, minimum Green, and post-refactor evidence under the canonical test command.

### 9.2 Pure contract and policy scenarios — T1

These scenarios construct only AgentMonitor-owned descriptors/outcomes and perform no I/O. They do not claim Codex/OpenAI behavior.

| Test ID | Requirement | Initial Red expected | Pass condition |
|---|---|---|---|
| CDX-PURE-001 | FR-QUOTA-006 | No A02 manifest policy exists | Manifest rejects supported capability without evidence tuple |
| CDX-PURE-002 | FR-COL-007/008 | Source selector permits implicit fallback | Only explicitly approved source/transition can resolve |
| CDX-PURE-003 | FR-COL-006 | Unsupported/unavailable/unknown collapse | Decision, compatibility, and runtime states remain distinct |
| CDX-PURE-004 | FR-AUTH-006 | Version/profile evidence is not enforced | Profile/version-sensitive capability blocks unknown scope |
| CDX-PURE-005 | NFR-COMP-001 | Unknown capability/schema major is accepted | Unknown major is visible but non-invokable |
| CDX-PURE-006 | FR-AUTH-001 | Outer failure maps to auth state | Auth health remains separate from source/network outcome |
| CDX-PURE-007 | FR-DISC-004 | Weak identity evidence auto-matches | Weak/conflicting/stale evidence yields unresolved |
| CDX-PURE-008 | FR-DISC-004 | Current login labels prior sessions | Evidence validity interval prevents retroactive correlation |
| CDX-PURE-009 | FR-DISC-008 | Provenance omits parser/provider version | Local typed input without required versions is rejected |
| CDX-PURE-010 | FR-DISC-008 | Opaque version is guessed as ordered | Only the approved version rule accepts compatibility |
| CDX-PURE-011 | FR-QUOTA-001 | Native windows are merged | Each native window remains distinct by approved identity |
| CDX-PURE-012 | FR-QUOTA-002 | Unknown provider field enters generic map | Only registered extension fields survive |
| CDX-PURE-013 | FR-COL-003 | Adapter retries a retryable outcome | Adapter policy returns disposition without retry action |
| CDX-PURE-014 | FR-COL-003 | Auth/rate/version failures share retry rule | Each outcome maps to synchronized disposition |
| CDX-PURE-015 | FR-COL-003 | Missing retry-after becomes zero-delay | Unknown precision/value stays absent/unknown |
| CDX-PURE-016 | FR-COL-008 | Stale/local value is relabelled live | Provenance/source/freshness validation rejects fabrication |

### 9.3 Real executable and structured-source scenarios — T5/T6

| Test ID | Requirement/AC | Real dependencies | Initial Red expected | Pass condition/coordination |
|---|---|---|---|---|
| CDX-EXEC-001 | FR-ACC-005 | Real installed Codex executable | Adapter cannot discover/identify installation | Exact safe installation candidate and version outcome |
| CDX-EXEC-002 | FR-DISC-008 | Real reviewed version operation | Version parser absent | Exact observed version maps or returns unverified |
| CDX-EXEC-003 | FR-ACC-006 | Multiple real installations if present | Duplicate/ambiguous install handling absent | Distinct candidates or truthful unavailable |
| CDX-EXEC-004 | NFR-PLAT-001 | Real Linux; real macOS when available | Platform scope unreported | Linux passes; unavailable macOS remains Blocked |
| CDX-EXEC-005 | FR-COL-007 | Real approved CLI/status source | Source selection/invocation absent | Exact approved source used with complete provenance |
| CDX-EXEC-006 | FR-COL-007 | Real approved app-server if Supported | Structured client absent | Typed method works or scenario is Blocked/Unsupported |
| CDX-EXEC-007 | NFR-SEC-001 | Real output bounds/deadline | Boundary does not contain oversized/long operation | Bounded safe outcome; no raw output artifact |
| CDX-EXEC-008 | NFR-RES-001 | Real malformed/version-changed source when naturally present | Failure escapes adapter | Affected operation contained; service/other adapters available |

No command is authorized by these rows. Each execution requires an approved operation ID and owner-reviewed preflight from M0/live runbooks.

### 9.4 Real filesystem and parser scenarios — T5/T6

| Test ID | Requirement/AC | Real dependencies | Initial Red expected | Pass condition |
|---|---|---|---|---|
| CDX-FS-001 | FR-DISC-003 | Real approved Codex root | Root grant/reader absent | Only approved root/names enumerated within bounds |
| CDX-FS-002 | NFR-SEC-001 | Real symlink/file permission cases naturally present or isolated approved files | Path safeguards absent | Escape/type/owner/mode violations fail closed |
| CDX-FS-003 | FR-DISC-008 | Real current state file/schema | Parser absent | Allowed fields parse with exact schema/parser/provider version |
| CDX-FS-004 | R-002 | Real changed/unknown schema when naturally observed | Drift may be guessed | Unverified/invalid outcome without partial invented mapping |
| CDX-FS-005 | NFR-PRIV-001 | Real session metadata | Field minimization not implemented | Only field-register entries reach typed DTO |
| CDX-FS-006 | AC-PROC-004 | Real DB/log/API/export after read | Prohibited data proof absent | Secret/content/environment scans are clean |
| CDX-FS-007 | FR-AUTH-005 | Real default profile pre/post safe metadata | Non-modification proof absent | No approved non-secret state change attributable to read |
| CDX-FS-008 | NFR-SEC-001 | Real concurrent file modification when naturally encountered | Race behavior unsafe/unknown | Bounded typed partial/invalid result; no repeated read storm |

### 9.5 Contract and integration scenarios — real production stack

| Test ID | Layer | Requirement/AC | Real dependencies | Initial Red expected | Pass condition |
|---|---|---|---|---|---|
| CDX-CONTRACT-001 | Contract | FR-COL-004 | Real A02 result | Provenance fields absent | M03 accepts exact complete provenance |
| CDX-CONTRACT-002 | Contract | NFR-COMP-001 | Real production adapter registered with M03 | Conformance fails/no adapter | Exact protocol/manifest/source/outcome schemas pass |
| CDX-CONTRACT-003 | Integration | FR-QUOTA-001 | Real A02 + M04 + M05 + SQLite | Capacity commit route absent | Typed observation committed once with receipt |
| CDX-CONTRACT-004 | Integration | FR-COL-008 | Real provider failure + M04/M05 | Failed run may freshen capacity | Failure stores no new observation; prior data is stale |
| CDX-CONTRACT-005 | Integration | FR-DISC-006 | Real A02 + M04 + M06 + SQLite | Runtime commit route absent | Approved session/metric input committed once |
| CDX-CONTRACT-006 | Integration | NFR-RES-001 | Running service and other real adapter | A02 failure affects service | Failure isolated; health/query availability preserved |

### 9.6 Codex live account/session matrix — T6

| Test ID | Requirement/AC | Real dependency | Initial Red expected | Pass condition/owner role |
|---|---|---|---|---|
| CDX-LIVE-001 | AC-LIVE-002 | Four intended account aliases | Enrollment evidence absent | Each enrolled or owner records unavailable |
| CDX-LIVE-002 | FR-ACC-006 | Ambiguous real candidate if naturally present | Confirmation path absent | Owner-confirmed or unresolved; never guessed |
| CDX-LIVE-003 | FR-AUTH-001 | Real healthy account | Auth inspector absent | Healthy only with evidenced identity/source |
| CDX-LIVE-004 | FR-AUTH-001 | Naturally expiring/refreshing state | State unavailable | Passed if real; otherwise Blocked |
| CDX-LIVE-005 | FR-AUTH-001 | Naturally reauth-required/revoked state | State unavailable | Correct distinct outcome or Blocked |
| CDX-LIVE-006 | FR-AUTH-001 | Wrong-account evidence when safely natural | State unavailable | Mismatch stops flow; otherwise Blocked |
| CDX-LIVE-007 | FR-QUOTA-006; AC-LIVE-004 | Real supported plan/version | Subscription collector absent | Exact manifest capability and live result |
| CDX-LIVE-008 | FR-QUOTA-001 | Real native windows | Mapping absent | Each window/scope/unit/reset retained separately |
| CDX-LIVE-009 | AC-LIVE-005 | Owner authoritative Codex view/command | Reconciliation absent | Identity/scope/unit/time/precision match tolerance |
| CDX-LIVE-010 | FR-QUOTA-005 | Sufficient real history if naturally accumulated | Forecast path unavailable | Inputs/provenance preserved; M05 derives or reports insufficient |
| CDX-LIVE-011 | AC-PROC-001 | Five–six running Codex processes | No session discovery | Read-only discovery without launch-flow change |
| CDX-LIVE-012 | FR-DISC-006 | Real safe session/model/activity metadata | Mapping absent | Only supported fields with explicit field states |
| CDX-LIVE-013 | FR-DISC-006 | Real safe token/context metadata if Supported | Field unavailable | Correct units/scope/provenance or Unsupported/Blocked |
| CDX-LIVE-014 | AC-PROC-004 | Real storage/log/API/export | Privacy proof absent | No prohibited content/environment/secret persisted |
| CDX-LIVE-015 | FR-DISC-004 | Real session/account relation with strong evidence | Correlation absent | Matched only under approved rule |
| CDX-LIVE-016 | FR-DISC-004 | Real unresolved relation | Unknown might be guessed | Visible unresolved outcome |
| CDX-LIVE-017 | AC-PROC-002 | Real parent/child Codex processes/sessions | Evidence absent | M06 tree correct or ambiguity explicit |
| CDX-LIVE-018 | FR-DISC-004 | Multiple processes across accounts | Cross-account contamination possible | Every evidence scope isolated; uncertain remains unresolved |
| CDX-LIVE-019 | R-003 | Current login changes naturally while old process runs | Behavior unknown | Old session not relabelled; otherwise defect/Blocked |
| CDX-LIVE-020 | FR-AUTH-005; AC-PROC-004 | Default profile/process pre/post checks | Mutation proof absent | Default profile and running agents unchanged |
| CDX-LIVE-021 | FR-AUTH-006 | Approved isolated managed profile experiment | Isolation unproven | Exact version isolation proven or Failed/Blocked |
| CDX-LIVE-022 | AC-LIVE-006 | One managed real account and owner | Reauth implementation absent | Official owner-run flow succeeds on managed target |
| CDX-LIVE-023 | FR-AUTH-003 | Real M02 history before/after reauth | Continuity absent | Stable account/name/group/history/config preserved |
| CDX-LIVE-024 | R-021 | Owner selects wrong account during approved flow if naturally encountered | State unavailable | Wrong-account preserves prior state or remains Blocked |
| CDX-LIVE-025 | FR-AUTH-005 | Default/unknown profile target | Guard absent | Reauth rejects before external process/network I/O |
| CDX-LIVE-026 | FR-AUTH-006 | Service restart during managed auth only if safely approved | Restart behavior unknown | Flow expires/resumes exactly per contract; otherwise Blocked |
| CDX-LIVE-027 | AC-OPS-006 | Approved safe collection cadence | Rate evidence absent | Requests remain within source limits with no hidden retries |
| CDX-LIVE-028 | AC-OPS-003 | Natural provider/unavailable/malformed failure | Failure may propagate | A02 degrades only affected capability |
| CDX-LIVE-029 | AC-LIVE-007 | Natural exhausted/recovery condition | Condition unavailable | Correct transition if observed; otherwise Blocked |
| CDX-LIVE-030 | NFR-PLAT-001 | Real macOS environment | Environment unavailable | Current macOS result Passed or visibly Blocked |

### 9.7 OpenAI API live matrix — T6, fixed A02 ownership

| Test ID | Requirement/AC | Real dependency | Initial Red expected | Pass condition |
|---|---|---|---|---|
| CDX-OAI-001 | FR-BUDGET-001/006 | Real approved admin credential role | Collector absent | Least-privilege role/scope established without secret exposure |
| CDX-OAI-002 | FR-BUDGET-005 | Real Codex subscription + API resource | Pools may conflate | Separate provider/resource identities and observations |
| CDX-OAI-003 | FR-BUDGET-003 | Real official usage endpoint | Mapping absent | Supported buckets/dimensions/pagination mapped exactly |
| CDX-OAI-004 | FR-BUDGET-002/004 | Real official cost endpoint | Exact money mapping absent | Currency/exact amount/interval round-trip without float |
| CDX-OAI-005 | FR-BUDGET-002 | Real credits/limits/budget source if official | Availability unknown | Supported fields mapped or explicit Unsupported/Unknown |
| CDX-OAI-006 | AC-LIVE-005 | Owner authoritative billing UI | Reconciliation absent | Same org/project/time/unit/latency/precision reconcile |
| CDX-OAI-007 | FR-COL-003 | Natural auth/authorization/rate condition | Failure unavailable | Correct typed state or Blocked; no manufacturing |
| CDX-OAI-008 | FR-COL-004 | Real API result | Provenance incomplete | Role/source/version/data-through/freshness complete |
| CDX-OAI-009 | FR-COL-008 | Real provider failure | Stale might appear current | No invented/cached-as-current result |
| CDX-OAI-010 | NFR-RES-001 | One real API account failure and another available surface | Isolation absent | Other Codex/local/API/dashboard functions remain available |

If M0 marks an OpenAI API capability Unsupported or Deferred, its scenario stays
in A02 with that truthful state; it cannot disappear, move, or be double-counted.

### 9.8 Real API/browser/history scenarios — T2/T3/T4

| Test ID | Requirement/AC | Real dependencies | Initial Red expected | Pass condition |
|---|---|---|---|---|
| CDX-E2E-001 | AC-UI-002 | A02/M02/M04/M05/M06/P01/P02, real SQLite/server/browser | Codex views absent | Real account/quota/session states render without placeholders |
| CDX-E2E-002 | AC-UI-005 | Real unsupported/stale/auth/error condition | Truthful states absent | UI/API distinguish and explain each state |
| CDX-E2E-003 | AC-UI-006 | Real provenance/derived path | Explanation absent | Source/time/version/confidence/derivation visible |
| CDX-E2E-004 | AC-HIST-001 | Real repeated observations | History path absent | Collection→SQLite→API→built chart/table verified |

### 9.9 Architecture, security, operations, quality, and documentation scenarios

| Test ID | Gate | Initial Red expected | Pass condition |
|---|---|---|---|
| CDX-ARCH-001 | Import boundary | No rule exists | Adapter does not import provider peers/module internals/framework/UI/DB |
| CDX-ARCH-002 | Surface review | Unsafe generic operation possible | No raw execute/file/endpoint/dict escape hatch |
| CDX-ARCH-003 | Ownership | Paths/contracts overlap | All edited paths have one owner and contracts one producer |
| CDX-ARCH-004 | V1 action boundary | Control/switch verb may exist | No process control/routing/in-flight switching surface |
| CDX-ARCH-005 | Contract compatibility | Schema drift unchecked | Protocol/payload/extension majors fail closed |
| CDX-ARCH-006 | Provider isolation | Provider condition leaks downstream | All Codex/OpenAI logic stays in A02 |
| CDX-SEC-001 | Credential schema scan | Credential-like fields not checked | Public/internal DTOs contain no credential values |
| CDX-SEC-002 | Source scan | Prohibited I/O possible | No shell/keyring/browser cookie/memory/terminal/arbitrary env access |
| CDX-SEC-003 | Data artifact scan | DB/log/evidence safety unproven | No secret/content/raw payload in real artifacts |
| CDX-SEC-004 | Path/output bounds | Boundary may be unbounded | Every source has reviewed size/count/time/link/host constraints |
| CDX-SEC-005 | Profile protection | Default target might reach reauth | Protected/unknown rejects before I/O |
| CDX-SEC-006 | Environment | Full environment might be inherited | Exact minimum name allowlist only; values never logged |
| CDX-SEC-007 | No-control | Cancellation may target agent | Only AgentMonitor-owned child/request handle cancelled |
| CDX-SEC-008 | Logs | Raw exception/object might serialize | Allowlisted structured log fields only |
| CDX-SEC-009 | Diagnostics | Account/path/values might leak | Bounded safe version/state/code summary only |
| CDX-SEC-010 | Network privacy | External analytics/unknown host possible | Only approved provider hosts; no AgentMonitor telemetry |
| CDX-OPS-001 | Health | No component health | Safe capability/version/outcome health is queryable |
| CDX-OPS-002 | Disable/rollback | Adapter cannot be isolated | Capability/adapter disables without data/profile mutation |
| CDX-OPS-003 | Polling budget | Rate/cost gate absent | M04 enforces exact evidence ceilings |
| CDX-PERF-001 | Bounded local parsing | Memory/time unmeasured | Real approved largest observed files stay within approved budget |
| CDX-PERF-002 | Process/account envelope | Target scale unmeasured | 4 accounts/5–6 current processes pass; 100/200 architecture remains bounded without fake provider claims |
| CDX-DEP-001 | Dependency admission | Candidate package unreviewed | Exact purpose/license/transitives/security/telemetry/pinning approved |
| CDX-DEP-002 | External tool distribution | Codex binary terms unclear | Tool is not bundled; documented operator dependency reviewed |
| CDX-DOC-001 | Documentation | A02 module/runbook/contracts missing | Required docs linked and status accurate |
| CDX-DOC-002 | Evidence traceability | Provider claim lacks evidence | Every claim maps to scoped M0/live report |
| CDX-TEST-001 | R/G/R evidence | Behavior lacks behavioral Red | Every increment has Red/Green/refactor records |
| CDX-TEST-002 | Prohibited substitutes | Repository policy not enforced | Canonical scan/review finds no prohibited test approach |
| CDX-TEST-003 | Status truth | Aggregate green may hide live gaps | Passed/Failed/Blocked/Not Run emitted separately |

### 9.10 Red, Green, and evidence record

For every scenario implemented, the handoff records requirement/AC, A02/M03/M05/M06 contract versions, adapter/parser/provider/source versions, exact canonical command and selector, UTC timestamp, real boundary, expected behavioral Red, actual sanitized Red, minimum production change, Green result, post-refactor rerun, evidence reference, side-effect reconciliation, owner acknowledgement where interactive, and every Blocked/Not Run item.

Setup failures, missing credentials, syntax errors, missing dependencies, or unavailable providers are not meaningful Red. A live scenario that cannot run remains Blocked/Not Run and cannot be replaced with a pure test.

## 10. Implementation increments

Implementation starts only after section 15 is checked and a root task packet allocates paths/contracts.

| Increment | Scope | Failing tests first | Minimum production change | Exit evidence |
|---|---|---|---|---|
| CDX-I00 | Contract/evidence synchronization only | No production test | Bind M0 rows, contracts, ownership, source/field/version registers | Signed synchronization; still no code |
| CDX-I01 | Adapter identity and manifest | CDX-PURE-001..005, CDX-CONTRACT-002 | Static A02 descriptor/manifest builder | Pure R/G/R and contract review |
| CDX-I02 | Installation/version discovery | CDX-EXEC-001..004 | Approved platform/executable mapping | Real Linux install/version evidence |
| CDX-I03 | Safe source boundary and common parser pipeline | CDX-EXEC-005..008, CDX-FS-001/002 | Minimum reviewed executor/file/app-server source seam | Real boundary and security evidence |
| CDX-I04 | Authentication health and identity | CDX-PURE-006..008, CDX-LIVE-003..006 | Typed auth/identity mapper | Real account states or visible Blocked rows |
| CDX-I05 | Codex subscription quota | CDX-PURE-011/012, CDX-CONTRACT-001/003, CDX-LIVE-007..010 | One evidenced source to M05 payload | Real authoritative reconciliation |
| CDX-I06 | Local sessions and metrics | CDX-FS-003..008, CDX-CONTRACT-005, CDX-LIVE-011..014 | One evidenced local source to M06 payload | Real file/session/privacy evidence |
| CDX-I07 | Process/session/account evidence | CDX-PURE-007/008, CDX-LIVE-015..020 | Provider evidence mapper only | 5–6 real processes; unresolved stays truthful |
| CDX-I08 | A02-owned OpenAI API usage/cost/budget where supported | CDX-OAI-001..010 | Separately scoped official admin API collector | Real API and UI reconciliation |
| CDX-I09 | Managed-profile reauth | CDX-LIVE-021..026 | Official isolated managed-profile flow only | Owner-run live flow/default-profile proof |
| CDX-I10 | Service/API/UI/history vertical slice | CDX-CONTRACT-004/006, CDX-E2E-001..004 | Composition wiring and minimum adapter fixes | Real stack/browser/history evidence |
| CDX-I11 | Hardening/version change/operations | CDX-ARCH/SEC/OPS/PERF/DEP/DOC/TEST scenarios | Minimum safety/docs/disable improvements | Full handoff and independent review |

### 10.1 Ordering and parallel safety

- I00 is serial and blocks all production work.
- I01 can begin only after M03 protocol synchronization; it owns no provider fact beyond accepted M0 rows.
- I02–I07 may use separate A02-owned files, but manifest, source registry, common parser policy, and adapter facade have one integration owner.
- I05 and I06 can proceed in parallel only after M05/M06 payloads and separate source grants are frozen.
- I08 is independent from Codex subscription/local sources after provider-key/resource/credential ownership is frozen; it shares only the A02 manifest/facade under one owner.
- I09 is isolated and later because it is state-changing. No read-only increment may quietly add login/logout behavior.
- M02–M06/A04 can implement their consumers/producers in parallel against synchronized versions without editing A02 files.
- Composition, lockfiles, configuration registry, generated artifacts, central contracts, and evidence catalogs are shared and allocated centrally.
- Provider live runs execute one bounded account/source block at a time to keep evidence attributable and protect active development.

### 10.2 Increment stop points

Stop the increment if evidence contradicts a field/source/version rule, a contract change is required, the provider emits prohibited data, a default/unknown profile could be changed, the source requires hidden retries/private endpoints/browser cookies, the wrong account appears, a new dependency is needed, another owner path must be edited, or a live run would consume material credits/disrupt agents without approval.

## 11. Documentation outputs

Implementation and every compatibility expansion update as applicable:

- `docs/adapters/codex.md`: purpose, boundaries, supported/unsupported capabilities, versions, source classifications, outcomes, limitations, and disable behavior;
- A02 capability matrix with exact product/version/plan/role/platform scope and Passed/Failed/Blocked/Not Run live rows;
- source and operation register references, with no executable command documented before review and verification;
- field/path allowlist and prohibited-data register;
- Codex/OpenAI extension schema documentation and compatibility history;
- managed-profile/default-profile protection and reauth runbook;
- troubleshooting for installation/version/auth/wrong-account/quota/session/rate/version/schema failures;
- real verification guide for four accounts and five–six processes;
- dependency admission/SBOM/notices impact;
- security/threat/data-flow update for any new source or auth behavior;
- root-owned contract register, traceability, risk register, planning registry, and release notes through synchronized edits;
- sanitized test evidence/handoff records using repository templates.

Documentation distinguishes Planned, Supported, Experimental, Deferred, Unsupported, Implemented, and Live Verified. It contains no real account identity, raw output, secret, provider file, prompt/content, or invented metric example presented as data.

## 12. Dependency and license impact

### 12.1 Proposed dependency posture

A02 proposes no new Python runtime or test dependency in this Draft. It prefers approved foundation safe-boundary ports and standard-library pure parsing where sufficient. The Codex executable and provider services are operator-managed external products, not vendored, downloaded, installed, or redistributed by AgentMonitor.

For supported official OpenAI HTTP access, A02 first consumes the centrally admitted HTTP client. It does not automatically add the OpenAI SDK. A provider SDK is considered only when an official direct contract cannot be implemented safely and its hidden retry, telemetry, environment, credential, binary, license, and transitive behavior pass admission.

### 12.2 Admission record for any candidate

Before any manifest/lockfile edit, record:

- exact documented need and why standard library/current stack is insufficient;
- canonical package/upstream identity and exact version;
- upstream license file plus all transitive licenses;
- maintenance/release/security policy, ownership, provenance, compromise history, and vulnerabilities;
- supported Python/Linux/macOS versions and native/binary/install-script behavior;
- network, telemetry, retry, update, environment, credential, and subprocess behavior;
- size/performance and supply-chain implications;
- exact pin/lock/hash/update/removal strategy and alternatives;
- SBOM/notices changes and reviewer/date.

Copyleft, unclear, custom, source-available, telemetry-bearing, or opaque-binary dependencies require explicit owner approval. No dependency is installed merely to write or validate this plan.

## 13. Risks, unresolved decisions, and stop conditions

### 13.1 Adapter risks

| Risk | Likelihood/impact | Mitigation/evidence | Owner | Status |
|---|---|---|---|---|
| R-001 no stable subscription source | High/Critical | Official-first M0; Unsupported is valid; no scraping fallback | M0/A02/security | Open |
| R-002 CLI/app-server/local schema drift | High/Major | Exact version/parser rules, unverified fail closed, live expansion | A02/M03 | Open |
| R-003 account/session correlation is weak | High/Critical | Evidence classes, validity intervals, unresolved/manual confirmation | A02/M02/M06 | Open |
| R-004 default profile modified | Low/Critical | Protected/unknown precondition, read-only operation review, real pre/post proof | A02/security | Open |
| R-005 secret/content captured | Medium/Critical | Allowlist-at-source, raw discard, scans, incident stop | A02/security | Open |
| R-006 polling hidden retry/rate contamination | Medium/Major | Prove no hidden retries; one attempt; M04 budgets | A02/M04 | Open |
| R-007 stale/partial appears current | Medium/Critical | Complete provenance, partial codes, no cached fallback | A02/M05/M06 | Open |
| R-009 natural failure unavailable | High/Major | Blocked live row; never manufacture | Test/owner | Accepted constraint |
| R-010 live tests spend credits/disrupt agents | Medium/Major | Read-only/low-cost packet, owner timing, immediate stop | Live operator | Open |
| R-014 subscription/API resources double-count | Medium/Major | Separate provider/resource targets and source schemas | A02/M02/M05 | Open |
| R-018 dependency/CLI supply chain | Medium/Critical | No install; dependency admission; executable identity/version | Dependency/security | Open |
| R-019 CI mistaken for live evidence | Medium/Major | T5/T6 statuses separate in canonical gate | Integration | Open |
| R-021 reauth wrong account/history loss | Medium/Critical | Expected identity, M02 atomic reconcile, managed-only flow | A02/M02 | Open |
| R-024 terms/private source conflict | Medium/Critical | Official supported sources; legal/security review; defer unsafe methods | Product/security | Open |
| A02-R01 app-server appears structured but mutates state | Medium/Critical | Method/lifecycle/file/network side-effect discovery and pre/post proof | M0/A02 | Open |
| A02-R02 auth-store category inference reads secrets | Medium/Critical | Approved category signal only; no credential file/keyring access | Security/A02 | Open |
| A02-R03 current login reassigns old processes | High/Critical | Session-scoped evidence and validity; current login never sufficient | A02/M06 | Open |
| A02-R04 provider output includes content in a safe-looking field | Medium/Critical | Field-level privacy review and real artifact scan | Security/A02 | Open |
| A02-R05 provider version cannot be ordered | High/Major | Exact/opaque compatibility set; no semver assumption | M03/A02 | Open |

### 13.2 Approval-blocking synchronization decisions

1. Accepted M0 Codex capability matrix and A02 handoff with no `Unknown` treated as support.
2. Exact provider/product identity and registration for the A02-owned OpenAI API lane; no duplicate collection.
3. Stable provider keys for Codex product/subscription and OpenAI API resources.
4. Exact verified installed Codex versions and their version-comparison rule.
5. Supported source per capability: interactive CLI, structured CLI, app-server, local state, or official API.
6. Exact operation IDs, argument/method/request shapes, read-only side effects, output bounds, and cancellation behavior.
7. Exact supported quota windows, fields, units, credit/reset semantics, precision, freshness, and plan scopes.
8. Exact OpenAI usage/cost/budget roles, fields, money, dimensions, pagination, latency, and limits where M0 supports the A02-owned capability.
9. Exact Codex installation identity and safe executable locator contract.
10. Exact auth-store category signal and auth-health/wrong-account state evidence.
11. Exact stable account/profile/resource identity representation and privacy classification.
12. Exact default-profile detection/protection rule with no public unprotect path.
13. Whether isolated `CODEX_HOME` and named configuration profiles provide independent credential/session state for each verified version.
14. Official managed-profile logout/login/reauth lifecycle and coordinator ownership; no default-profile target.
15. Exact local roots/files/fields, path/link/mode/size/change behavior, parser versions, and prohibited classes.
16. Exact safe session/model/project/task/token/context/activity/error/hierarchy fields and units.
17. Exact process/session/profile/account correlation evidence classes, validity, conflicts, and owner-confirmation boundary.
18. M03 manifest/source/outcome/auth/reauth/extension schemas and cardinality/size bounds.
19. M05 quota and M0-supported API input DTO versions plus extension opt-in.
20. M06 session/metric/correlation input DTO versions and provider raw-state policy.
21. M04 deadline/cancellation/rate/cost/concurrency/no-hidden-retry constraints.
22. Owners/versions for safe subprocess, filesystem, HTTP, profile/credential, and platform ports.
23. Adapter health/diagnostic disclosure and M08/P01 presentation.
24. Canonical A02 automation selectors, evidence custody, and live-test scheduling.
25. Exact dependency graph/license review or confirmed no A02-specific dependency.
26. macOS evidence availability and any platform-specific source differences.
27. Any ADR required for app-server lifecycle, experimental/private source, new credential storage, or profile isolation.

No implementation agent may select among materially different answers privately.

### 13.3 Stop and escalation conditions

Stop and return to root synchronization when:

- M0 evidence is missing, contradictory, broader/narrower than the planned capability, or outside the installed version;
- an undocumented/private/browser source, cookie, traffic interception, process memory, terminal injection, or arbitrary environment read appears necessary;
- default/unknown profile protection cannot be proven before a mutation-capable operation;
- a source prompts to install/update/login/logout/write or changes provider files/state unexpectedly;
- provider output contains a credential, identity, prompt, response, reasoning, tool activity, terminal/source content, arbitrary log/environment, or unknown high-risk field;
- identity is mismatched/ambiguous or correlation would require a guess;
- quota/window/unit/reset/credit/budget/money/session/token semantics are unknown;
- a command/SDK contains unknown hidden retry, telemetry, update, rate, cost, or side-effect behavior;
- a contract meaning/version, extension, source class, permission, or owner must change;
- another module/path/table/shared artifact must be edited without allocation;
- a dependency is not admitted or has unacceptable license/supply-chain behavior;
- live work requires credentials in chat, material spend, quota exhaustion, budget change, provider mutation, or agent interruption;
- real evidence becomes contaminated with prohibited data.

## 14. Delivery, compatibility, and rollback

### 14.1 Delivery order

1. Execute and approve M0 Codex/OpenAI/Linux handoffs under the discovery gates.
2. Resolve section 13.2 and synchronize M02/M03/M04/M05/M06/A04/M08 contracts.
3. Approve A02 plan, exact paths, dependencies, operations, source/field registers, and live resources.
4. Implement manifest/pure policy through R/G/R without provider claims.
5. Implement installation/version and one safest supported real source.
6. Deliver one real subscription quota vertical slice through M04/M05/API/UI.
7. Deliver one real local session/runtime vertical slice through A04/M04/M06/API/UI.
8. Expand correlation only after evidence and four-account/five–six-process live validation.
9. Add A02-owned OpenAI API administration only for approved M0-supported sources and credential roles.
10. Add managed-profile reauth last under a separately approved state-changing live packet.
11. Complete failure isolation, version drift, rollback, security, performance, documentation, and release matrices.

### 14.2 Compatibility promise

- A02 implements the current approved M03 protocol major and exact M05/M06 input schema majors.
- Provider-version compatibility is capability/source-specific; an unknown version disables only affected sources/capabilities.
- Adding an optional extension field is compatible only with approved safe absence and consumer tolerance.
- Changing source, field meaning, unit, window/resource identity, auth state, correlation strength, privacy class, retry/side-effect behavior, or extension major is breaking.
- Expanding the verified provider-version/plan/role/platform range requires official review and real live verification even when code does not change.
- Historical observations remain readable with their original adapter/parser/source versions after an adapter upgrade or disable.

### 14.3 Deployment and exposure

A02 ships disabled for every capability until the exact manifest tuple is approved and current installation/source compatibility passes. Installation discovery may expose only safe candidates. Public API/UI exposure follows real backend/domain readiness and never introduces sample values.

Provider version drift automatically makes the affected capability unverified/degraded; it does not silently use a weaker source. One adapter failure does not make the dashboard unavailable.

### 14.4 Rollback and recovery

- Disable the affected capability/source or entire A02 registration through the approved composition/policy mechanism.
- Roll back to a prior adapter binary only when M03 protocol and domain schema compatibility permit it.
- Preserve M02 identities and M05/M06 histories; never delete or rewrite observations to fit a rollback.
- Do not roll back provider profiles, credentials, authentication, or running agents.
- A failed managed reauth rolls back only pending AgentMonitor workflow state; provider-side partial state follows the approved incident/runbook and owner decision.
- After service restore/restart, verify schema/application/adapter/manifest/provider versions, protected-profile state, target identity, safe health, and one approved read-only operation before enabling scheduled collection.

### 14.5 Post-delivery checks

- A02 registers with the approved protocol and manifest fingerprint.
- Every capability/source/provider-version/account-plan/role/platform tuple has an explicit decision and live status.
- Codex subscription and OpenAI API resource pools remain separate.
- Real quota/API observations reconcile where supported.
- Real sessions/process evidence uses only approved fields and uncertain account mappings remain unresolved.
- Default profiles and representative running agents are unchanged.
- No hidden retries, source downgrade, browser/private access, control, or in-flight credential switching exists.
- Logs, DB/WAL, API/UI, diagnostics, backups, exports, build/test/evidence artifacts scan clean of prohibited data.
- Blocked/Not Run auth/failure/macOS/provider states remain visible.

## 15. Definition of ready

- [ ] Owner/root approves this exact plan, outcome, non-goals, surface separation, and status becomes Approved.
- [ ] Canonical draft-complete and synchronized planning gates include PLAN-A02 and pass against the real checkout.
- [ ] M0-CDX, applicable M0-OAI, and M0-LNX technical handoffs validate with
      exact versions/scopes/evidence; detached reviews are advisory.
- [ ] A02 OpenAI API provider-key and resource separation are approved.
- [ ] A02 allowed/shared/forbidden paths and agent ownership are conflict-free.
- [ ] CTR-COMMON and CTR-PROV-001..008 are Approved for the first capability.
- [ ] Narrow M02 installation/target/profile/protection/identity/resource contracts are Approved.
- [ ] M04 operation context/deadline/cancellation/rate/cost/retry/commit routing is Approved.
- [ ] M05 provider quota and M0-supported usage/cost/budget input contracts are Approved.
- [ ] M06 local-session/runtime-metric/correlation input contracts are Approved.
- [ ] A04/safe subprocess/filesystem/HTTP/profile/credential ports and owners are Approved.
- [ ] Exact source/operation/path/field/version/extension registers pass security/privacy review.
- [ ] Default-profile protection and no-mutation proof are evidence-backed.
- [ ] Managed-profile isolation/reauth remains disabled until its separate evidence and approval pass.
- [ ] Every scenario has the correct real boundary, meaningful behavioral Red, safe evidence/cleanup, and assigned owner.
- [ ] Four real account aliases and representative five–six processes are available or owner-declared unavailable for live scheduling.
- [ ] Canonical A02 test/quality/docs/build/Git/deploy/backup/restore/release selectors are implemented and real-tested at the boundary required for their lifecycle gate.
- [ ] Dependency/license/security/maintenance/transitive review is complete for every exact selected package/tool version.
- [ ] Health/diagnostic/disable/rollback/version-change/incident runbooks and documentation outputs are assigned.
- [ ] Critical risks are mitigated with evidence or explicitly accepted by the owner; no unresolved decision permits materially different implementation.
- [ ] Root confirms no overlapping agent owns the same adapter/shared files immediately before implementation.

## 16. Approval record

| Reviewer | Decision | Conditions/findings | Date | Approved versions |
|---|---|---|---|---|
| Pavlo Sidelov / owner | Pending | Product scope, live accounts, managed-profile action, API ownership | — | — |
| Root/integration steward | Pending | M0, synchronization, paths, canonical planning gate | — | — |
| M02 Registry owner | Pending | Installation/account/profile/resource/protection/identity contracts | — | — |
| M03 Provider-system owner | Pending | Protocol/manifest/source/outcome/auth/extension conformance | — | — |
| M04 Collection owner | Pending | Deadline/rate/cost/retry/no-hidden-retry/commit lifecycle | — | — |
| M05 Capacity owner | Pending | Quota/API payload semantics and reconciliation | — | — |
| M06 Runtime owner | Pending | Session/metric/correlation inputs and privacy | — | — |
| A04 platform owner | Pending | Executable/path/process primitives and Linux/macOS scope | — | — |
| M08/P01/P02 owners | Pending | Health/diagnostics/API/UI/history exposure | — | — |
| Security/privacy reviewer | Pending | Profiles, credentials, field/path allowlists, no-control proof | — | — |
| Test-integrity/live reviewer | Pending | Real matrix, R/G/R, Blocked policy, evidence custody | — | — |
| Dependency/license reviewer | Pending | Exact dependency/tool graph and external distribution terms | — | — |

Implementation remains prohibited while this plan is Draft, M0 evidence is absent, any required contract is unsynchronized/unapproved, canonical readiness automation is absent/red, or any Definition-of-Ready item remains unchecked.
