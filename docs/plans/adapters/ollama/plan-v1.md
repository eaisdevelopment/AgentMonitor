# Module plan: A03 — Ollama provider adapter

- Plan ID: `PLAN-A03`
- Status: **Draft — M0 evidence and contract synchronization required; implementation is not authorized**
- Plan version: `0.2.1-draft`
- Proposed adapter contract bundle: `ollama-adapter.v1`
- Proposed provider protocol: CTR-PROV-001 `ProviderAdapterV1` protocol `1.0`, subject to synchronization
- Primary owner: A03 Ollama provider adapter
- Required reviewers: owner, root/integration steward, M02 Registry, M03 Provider system, M04 Collection control, M05 Capacity, M06 Runtime observation, A04-LINUX, M08 Operations, security/privacy, test-integrity, and dependency/license owners
- Requirements: FR-ACC-001, FR-ACC-004..006; FR-AUTH-001..006; FR-QUOTA-001..006; FR-BUDGET-001..006; FR-DISC-001..006, FR-DISC-008; adapter-contributed FR-STATE-001/002/004; FR-COL-003..008; FR-OPS-002, FR-OPS-006; FR-SAFE-001/002; supporting NFR-ARCH-001/002, NFR-TEST-001/002, NFR-SEC-001, NFR-PRIV-001/002, NFR-DOC-001, NFR-LIC-001, NFR-PLAT-001, NFR-PERF-001, NFR-RES-001, NFR-OBS-001, NFR-COMP-001
- Acceptance-criteria contribution: AC-V1-001/002/005/006/007/008; AC-LIVE-003..007; Ollama portions of AC-PROC-001..004 and evidence contribution to AC-PROC-005; AC-HIST-001; AC-OPS-003/006; AC-TEST-001..006
- Required predecessors: accepted M0 Ollama product/local, Ollama API, and Linux handoffs; synchronized CTR-COMMON, CTR-REG, CTR-PROV, CTR-COL, CTR-CAP, CTR-RUN, CTR-PLAT, safe-execution, configuration, and evidence contracts
- Target milestone: M4/M6 provider integration after M03 protocol approval
- Approved by/date: pending

This plan is governed by the [product requirements](../../../product/requirements.md), [V1 acceptance criteria](../../../product/v1-acceptance-criteria.md), [module boundaries](../../../architecture/modules.md), [contracts and versioning](../../../architecture/contracts-and-versioning.md), [data model](../../../architecture/data-model.md), [provider-adapter contract](../../../architecture/provider-adapter-contract.md), [security architecture](../../../architecture/security.md), [testing strategy](../../../engineering/testing-strategy.md), [SDLC](../../../engineering/sdlc.md), [completion and automation gates](../../../engineering/completion-and-automation-gates.md), [M0 execution plan](../../discovery/m0-execution-plan.md), and [contract register](../../contract-register.md). Structural shapes in this plan are proposed contracts, not provider facts, sample telemetry, fixtures, or evidence.

## CS-1 alignment addendum — contract baseline 0.2.0

This addendum is normative for CS-1 and supersedes conditional ownership or
private-contract wording elsewhere in this Draft. The machine-readable
[contract baseline](../../contract-baseline.toml) and
[parallel ownership manifest](../../parallel-ownership.toml) remain unapproved;
they do not authorize implementation, service access, or account access.

- A03 owns the Ollama local, cloud/subscription, and supported Ollama API
  integration lanes. M0 decides each exact capability's maturity and may leave
  it Experimental, Deferred, Unsupported, or evidence-blocked; it does not move
  the lane to a different adapter.
- A03 implements M03-owned `CTR-PROV-001..008` without redefining their
  semantics. Ollama extensions use only
  `backend/src/agentmonitor/contracts/providers/ollama/<capability>/v1/**` under M03 governance. Domain
  modules cannot import A03 packages.
- A03 consumes `CTR-COMMON-001/002/004/007`, `CTR-CONFIG-001`,
  `CTR-FND-003/004/008`, `CTR-BOUNDARY-001..003`, and the typed REG/COL/CAP/RUN
  ports below. `CTR-COMMON-007` keeps unavailable, unsupported, unknown,
  not-applicable, withheld, stale, unresolved, and exact-zero observations
  distinct. M03-owned `CTR-BOUNDARY-002` governs both local-service and provider
  HTTP; FND-owned `CTR-BOUNDARY-001/003` govern subprocess and approved-root
  reads.
- A03 implements the M08-owned `CTR-OPS-006` leaf health port and never
  aggregates application readiness. Any durable domain event passes through its
  owning domain workflow using `CTR-COMMON-006` and `CTR-EVT-001`; A03 owns no
  event/outbox persistence.
- `reauthentication_required` is the normalized provider-auth state and maps to
  `provider_reauthentication_required` at API/UI. It never becomes
  `dashboard_authentication_required` or invalidates dashboard login.
- After M0 and contract approval, `local_service`, `local_metadata`,
  `cloud_identity`, `cloud_subscription`, `api_billing`, and extension lanes may
  proceed independently under
  `backend/src/agentmonitor/adapters/providers/ollama/**`. They may not share a
  live identity/resource concurrently or edit common contracts, generated
  artifacts, composition, migrations, manifests, or other shared-writer files.

All Ollama compatibility and account/resource claims require real current
boundaries. No mock, fake, replay, constructed provider response, seeded
telemetry, or placeholder can establish support; Blocked and Not Run remain
non-Passed.

## 0. Authority, evidence state, and planning rule

This is the independent implementation plan for A03 only. It authorizes planning, not provider research, provider/account access, local service calls, command execution, filesystem inspection, API requests, authentication, profile changes, dependency installation, production code, test execution, configuration creation, or shared-file edits.

Milestone 0 has not executed. This plan therefore makes no assertion about:

- whether an observed Ollama identity represents a personal account, team, organization, workspace, API billing subject, or another scope;
- whether an account uses a current or legacy subscription/credit model;
- whether subscription credits, purchased credits, limits, resets, concurrency, or queue information are exposed through a supported machine-readable source;
- whether Ollama exposes an official usage, cost, credit, limit, or budget API for the intended identities and credential roles;
- whether local daemon endpoints, client commands, files, or logs expose safe model, load, CPU, RAM, GPU, queue, request-count, token, cost, or session data;
- whether local runtime facts can be related to a cloud subscription, API billing resource, provider session, account, workspace, or Linux process;
- whether an official isolated-profile or managed reauthentication mechanism exists or is safe;
- exact executable, client, daemon, API, schema, parser, plan, account, role, host, path, field, version, unit, window, time, precision, freshness, rate, or cost semantics;
- whether any A03 capability is `Supported`, `Experimental`, `Deferred`, or `Unsupported`.

Those facts may enter A03 only through accepted results for `M0-OLL-001..010`, `M0-OAPI-001..007`, applicable `M0-LNX-001..013`, and their sanitized M0 capability matrices and handoff packet. Unknown behavior remains Unknown and blocks its dependent lane. A remembered command, plausible endpoint, local installation convention, provider marketing term, or inferred pricing model is not evidence.

Every future behavior follows Red -> Green -> Refactor. Provider, daemon, CLI, filesystem, network, authentication, and account claims require the production A03 adapter against the real approved boundary. Pure tests prove only deterministic contract and mapping rules; they never prove Ollama compatibility.

## 1. Outcome and boundaries

### 1.1 Outcome

After approval and implementation, A03 is a statically admitted, failure-isolated provider package that exposes only Ollama capabilities proven for exact product/version/plan/account/workspace/credential/platform/source tuples. It keeps three resource domains structurally separate:

1. local service, installed models, model-load, and runtime resources;
2. Ollama cloud subscription/account/team/workspace resources;
3. Ollama API usage, billing, credit, and budget resources.

The adapter succeeds when:

- each manifest declaration is no broader than the accepted M0 decision;
- local compute, cloud subscription, and API billing are never merged, inferred from each other, or double counted;
- local daemon health does not imply cloud authentication health or remaining cloud/API capacity;
- per-request values do not become account totals and unobserved requests do not become zero usage;
- already-running clients are not intercepted, proxied, instrumented, or retrospectively accounted without an official aggregate source;
- default provider profiles, provider state, models, local services, and running agents remain unchanged by read-only collection;
- unsupported, Unknown, unavailable, partial, stale, unauthenticated, unauthorized, rate-limited, invalid-data, exhausted, and unverified-version states remain distinct;
- raw response bodies, request bodies, prompts, model output, provider files, logs, stdout/stderr, arbitrary metadata, secrets, and personal identifiers cannot cross the adapter boundary;
- M05 receives only its closed typed capacity inputs and M06 receives only its closed typed runtime inputs;
- A03 owns no database table or durable telemetry cache;
- every compatibility claim has real evidence from the intended two account/workspace identities and the representative naturally running 2–4 Ollama processes/models where available.

### 1.2 Independently enabled capability lanes

One lane can be Unsupported or failed without changing another lane's decision or availability.

| Lane | Concern | Potential M03 capability | Typed consumer | Required activation evidence |
|---|---|---|---|---|
| `OLL-INSTALL` | Ollama client/service discovery and independent version evidence | `installation.discovery`, `provider.diagnostics` | M02/M08 through CTR-PROV | M0-OLL-001/002/010 |
| `OLL-LOCAL-CATALOG` | Locally available models and approved safe catalog metadata | `model.catalog` | synchronized catalog owner; M06 only when runtime relevant | M0-OLL-005/010 |
| `OLL-LOCAL-RUNTIME` | Running/loaded models, resource/load/queue/concurrency/request counters proven safe | `local.session.discovery`, `local.session.metrics` or synchronized narrower capabilities | M06 closed inputs | M0-OLL-005/006/010 plus M0-LNX |
| `OLL-LOCAL-CORRELATION` | Ollama service/model/process evidence relationships | `local.process.correlation` | M06 correlation evidence; M02 confirmation where identity is involved | M0-OLL-007/010 plus M0-LNX-007/008 |
| `OLL-CLOUD-IDENTITY` | Cloud account/team/workspace/project candidates and auth health | `account.discovery`, `project.discovery`, `identity.verification`, `authentication.health` | M02 through CTR-PROV | M0-OLL-003/007/009/010 and M0-OAPI-002/007 |
| `OLL-CLOUD-SUBSCRIPTION` | Provider-defined cloud subscription/credit/quota windows | `subscription.quota` | M05 `ProviderQuotaInputV1` | M0-OLL-003/004/008/010 |
| `OLL-API` | Official API usage/cost/budget/credit data | `api.usage`, `api.cost`, `api.budget` | M05 `Provider*InputV1` | M0-OAPI-001..007 |
| `OLL-AUTH` | Official owner-driven reauthentication of an AgentMonitor-managed profile | `authentication.reauthenticate` | synchronized coordinator through CTR-PROV-007 | separate approved isolation evidence after M0-OLL-009 |

The Ollama API lane remains owned by A03 and is registered as a separate static
provider/product surface wherever its identity, credential, host, resource, or
billing scope differs. Contract synchronization freezes the exact registration
shape; no implementation may assume subscription and API use one credential,
account key, host, resource, or billing period.

### 1.3 In scope

- Ollama-specific implementations of evidence-approved CTR-PROV-001..008 capabilities.
- Manifest rows and source descriptors scoped to accepted M0 tuples.
- Independent client, daemon/service, cloud API, and parser version detection according to evidenced version schemes.
- Source-specific closed parsers and mappers with bounded input and field allowlists.
- Approved official CLI/service operations only when M0 proves them read-only and non-generative.
- Approved documented local service endpoints only when M0 proves host, method, path, output, side effect, and privacy safety.
- Approved local files or logs only when M0 proves their path/file/field safety and content prevention.
- Approved official cloud/API requests only when M0 proves endpoint, role, scope, request/rate/cost bounds, schema, and no model generation.
- Evidence-based account/team/workspace/project/resource candidates without deciding registry ownership.
- Auth-health mapping and, only after separate approval, managed-profile reauthentication.
- Mapping cloud subscription data to M05 `ProviderQuotaInputV1`.
- Mapping API usage/cost/budget/credit data to M05 `ProviderUsageInputV1`, `ProviderCostInputV1`, and `ProviderBudgetInputV1`.
- Mapping local runtime/model/session facts to M06-approved closed input families.
- Ollama provider-extension schemas containing only M0-approved bounded operational fields.
- Bounded adapter health, diagnostics, real conformance/live matrices, and operator documentation.

### 1.4 Out of scope

- Defining M02 identity/resource semantics, M03 protocol meaning, M04 schedule/retry behavior, M05 capacity policy, M06 state/stall policy, or M07 alert lifecycle.
- Any database table, migration, repository, outbox, durable cache, or copied provider credential.
- Public FastAPI routes, OpenAPI transport schemas, UI components, alerts, notification delivery, backups, deployment, or service management.
- Treating installed-model size, GPU/RAM use, local request counts, or per-response tokens as subscription/API spend or remaining credit.
- Treating a reachable local daemon as proof of cloud identity, subscription health, API authorization, or billing scope.
- Treating provider display names, plan labels, local hostnames, model names, current login, timing, or process order as stable account identity.
- Proxy insertion, traffic interception, request mirroring, packet capture, browser automation, cookie extraction, private billing endpoints, or undocumented network calls.
- Model generation, model pull/delete/copy, unload/load, keep-alive alteration, queue manipulation, service restart, configuration write, or provider state mutation for monitoring or testing.
- Reading or persisting request bodies, prompts, responses, embeddings, tool data, source code, arbitrary terminal/command output, process memory, arbitrary process environments, or unclassified logs.
- Inspecting Linux processes directly; A04-LINUX owns OS observation and M06 owns runtime semantics.
- Modifying, copying, moving, logging out, or rewriting a default Ollama profile or credential store.
- Starting authentication against any profile before official managed-profile isolation, protected-default rejection, and owner-interaction behavior are approved.
- Switching credentials inside, signalling, restarting, pausing, killing, attaching to, or routing a running agent or Ollama service.
- Claiming support for unobserved Ollama versions, plan classes, workspaces, credential roles, endpoints, or platforms.

### 1.5 Ownership and implementation paths

Allowed future implementation paths, only after an approved task packet:

```text
backend/src/agentmonitor/adapters/providers/ollama/**
backend/tests/adapters/providers/ollama/**
backend/tests/live/ollama/**
docs/adapters/ollama.md
docs/provider-capabilities/ollama/**
backend/src/agentmonitor/contracts/providers/ollama/<capability>/v1/**
docs/test-evidence/ollama/**                 # sanitized records only, if allocated
```

Suggested internal isolation, subject to foundation naming approval:

```text
ollama/
  adapter.py                 # static M03 facade and typed port routing
  manifest.py                # immutable evidence-scoped declarations
  installation.py            # independent client/service version evidence
  local_service/             # approved local endpoints and runtime mapping
  local_metadata/            # approved files/logs only; may remain absent
  cloud_identity/            # account/team/workspace/auth observations
  cloud_subscription/        # subscription quota/credit mapping
  api_billing/               # official API usage/cost/budget mapping
  authentication/            # auth health; managed reauth separately gated
  correlation/               # safe evidence mapping, never ownership decisions
  extensions/                # closed approved schemas and mappers
  diagnostics.py             # safe bounded health details
```

Shared paths require an explicit root-owned allocation and cannot be edited by the A03 implementation agent unilaterally:

```text
backend/src/agentmonitor/composition/**
backend/src/agentmonitor/contracts/**
configuration registry
dependency manifests and lockfiles
generated OpenAPI/client artifacts
central capability, contract, traceability, risk, evidence, and release registries
```

A03 owns the semantic content of Ollama extension schemas in its exact namespace,
but the integration steward remains the sole shared-file writer for each
allocated wave. A03 must not edit that namespace without a current allocation,
or edit/import internals from M01–M08, A01/A02/A04, P01/P02, persistence,
deployment, or another provider adapter.

### 1.6 Allowed and forbidden dependencies

Allowed imports after approval:

- Python standard library within the admitted runtime baseline;
- approved CTR-COMMON primitives;
- approved M03 protocol, capability, source, outcome, context, discovery, auth, and extension contracts;
- narrow approved M02 installation/target/profile/resource/identity-assertion contracts;
- M05-owned provider quota/usage/cost/budget input contracts;
- M06-owned process/session/metric/relationship/correlation input contracts;
- approved safe network, filesystem, subprocess, cancellation, time, redaction, and provider-profile access ports;
- adapter-local pure types that do not escape A03.

Forbidden imports and mechanisms:

- M01–M08 internal/domain/application/persistence packages, ORM models, repositories, migrations, or tables;
- FastAPI, Starlette, React, UI, SQLAlchemy, Alembic, OS process APIs, or concrete platform adapters in adapter mapping code;
- Claude/Codex provider adapters;
- dynamic plugins or arbitrary imports;
- provider SDKs, HTTP clients, retry packages, CLI wrappers, GPU libraries, process libraries, filesystem watchers, browser drivers, or telemetry clients before dependency admission;
- shells, global environment mutation, unrestricted paths/URLs, arbitrary headers, generic JSON escape hatches, or raw provider payload tunnels.

## 2. Requirements and traceability

| Requirement/AC | Planned A03 behavior | Contract | Planned scenarios | Evidence gate |
|---|---|---|---|---|
| FR-ACC-001/004/005 | Discover evidence-scoped Ollama installations, identities, profiles, workspaces, and separate resource pools | CTR-PROV-002/005; CTR-REG-004/005 | OLL-PURE-006, OLL-SVC-001..003, OLL-NET-001, OLL-LIVE-001..003 | Accepted M0 plus real installations and intended identities |
| FR-ACC-006; AC-PROC-003 | Emit owner-confirmation-required or unresolved evidence; never guess account/workspace/process association | CTR-PROV-005; CTR-REG-006; CTR-RUN-007 | OLL-PURE-007..009, OLL-LIVE-014/015 | Real strong/ambiguous cases and owner review |
| FR-AUTH-001 | Map only evidenced cloud/API auth signals and keep local service reachability separate | CTR-PROV-006 | OLL-PURE-010/011, OLL-LIVE-004/016 | Real current account/profile state |
| FR-AUTH-002/003/006; AC-LIVE-006 | Official managed-profile reauth with expected-identity verification and durable M02 identity preservation | CTR-PROV-007 plus M02 coordinator | OLL-LIVE-017..019 | Separate approved profile-isolation evidence and owner-run flow |
| FR-AUTH-004/005 | No credential/code parameter; reject protected-default or unknown profile before external I/O | CTR-PROV-001/007 | OLL-SEC-001..004, OLL-LIVE-020 | Security review and real no-change evidence |
| FR-QUOTA-001/002/004/006 | Preserve each supported cloud subscription window/credit pool, scope, unit, reset, source, precision, and field state | CTR-PROV-004; CTR-CAP-001 | OLL-MAP-001..004, OLL-LIVE-005/006 | Real authoritative comparison |
| FR-QUOTA-003/005 | Provide exact observations/provenance only; M05 owns health and forecast | CTR-CAP-001/003/007 | OLL-ARCH-003, OLL-LIVE-006 | Contract review and M05 real path |
| FR-BUDGET-001..006 | Preserve supported Ollama API usage/cost/budget/credits by exact account/team/workspace/resource scope | CTR-CAP-002 | OLL-MAP-009..012, OLL-NET-002..010, OLL-LIVE-007/008 | Real official API and authoritative comparison |
| FR-DISC-001 | Contribute provider/runtime evidence without changing launch workflow or inspecting OS directly | CTR-PROV-001; CTR-RUN-002 | OLL-SVC-004/005, OLL-LIVE-009 | Real naturally running service/process/model |
| FR-DISC-002 | Consume A04 safe process facts only for typed correlation; never collect or redefine PID/CPU/memory semantics | CTR-RUN-001/006 | OLL-ARCH-001/003, OLL-LIVE-009/013 | Contract boundary plus real A04/M06 observation |
| FR-DISC-003/006; AC-PROC-004 | Read only approved local service/file fields and exclude bodies/content/secrets | CTR-RUN-002/003; CTR-PROV-008 | OLL-MAP-005..008, OLL-SVC-006..011, OLL-FS-001..008, OLL-SEC-005..009 | Real approved source plus artifact scan |
| FR-DISC-004 | Produce only approved process/session/account/workspace correlation evidence | CTR-RUN-007 | OLL-PURE-007..009, OLL-SVC-012, OLL-LIVE-013..015 | M0 rules and real owner confirmation |
| FR-DISC-005 | Emit approved provider relationship evidence without treating OS ancestry/model workers as parent-agent semantics | CTR-RUN-003 | OLL-MAP-006/007, OLL-LIVE-010/011 | Real representative topology; conflicts/orphans visible |
| FR-DISC-008 | Record parser, adapter, client/service/API versions with every version-sensitive local result | CTR-COMMON-004; CTR-PROV-003 | OLL-PURE-003..005, OLL-SVC-002/010, OLL-FS-009 | Real supported and naturally changed versions |
| FR-STATE-001/002/004 | Emit only approved provider state/wait/error evidence with definitive/inferred/unknown certainty; M06 owns normalized state/stall | CTR-RUN-002/004/005 | OLL-MAP-006..008, OLL-LIVE-010/016/021 | Real natural signals; unavailable states remain Blocked |
| FR-COL-003 | Return provider-supported rate/retry hints but never autonomously retry | CTR-PROV-004; CTR-COL-004 | OLL-PURE-012, OLL-NET-009/010 | Policy plus natural real rate/outage behavior |
| FR-COL-004/005 | Supply complete provenance and bounded sanitized outcomes/warnings/durations | CTR-COMMON-004; CTR-PROV-004 | OLL-PURE-001..005, OLL-SVC-008, OLL-NET-006 | Contract validation and real results |
| FR-COL-006..008 | Explicit Unsupported/Unknown/unavailable/auth/version states; no silent downgrade/cache/simulation | CTR-PROV-002..004 | OLL-PURE-001/002/013..015, OLL-LIVE-016 | Policy plus real capability matrices |
| FR-OPS-002/006 | Publish bounded version/lane/compatibility health without provider calls or raw data | CTR-OPS-006 via M03 | OLL-OPS-002/003 | Real application health/diagnostic inspection |
| FR-SAFE-001/002 | Read/refresh and separately approved managed reauth only; no generation, service/model/agent control, routing, or proxy | Full A03 surface | OLL-ARCH-001/002, OLL-SEC-010/011 | Automated surface/import scan and live no-effect checks |
| NFR-ARCH-001/002 | Isolated provider adapter behind typed versioned contracts | `ollama-adapter.v1` | OLL-ARCH-001..005 | Import/contract/ownership gates |
| NFR-TEST-001/002; AC-TEST-001/002/006 | Meaningful R/G/R at real boundaries; no doubles/recordings/seed data; visible non-Passed states | Evidence contract | All OLL scenarios; OLL-OPS-005 | Test-integrity review and canonical report |
| NFR-SEC-001; NFR-PRIV-001/002 | Least privilege, allowlists, safe execution, no content/secrets/analytics | A03 boundary policy | OLL-SEC-001..012 | Security, artifact, and network review |
| NFR-DOC-001; AC-V1-006 | Maintain contracts, matrices, operations, limitations, and evidence routing | Documentation outputs | OLL-DOC-001/002 | Documentation gate |
| NFR-LIC-001 | No dependency before full direct/transitive admission | Dependency record | OLL-DEP-001/002 | Lock/SBOM/notices/license/security review |
| NFR-PLAT-001 | Linux verified; platform-neutral contracts; macOS distinct Passed or Blocked | Manifest platform scope | OLL-LIVE-009, OLL-OPS-004 | Real Linux and real macOS only |
| NFR-PERF-001 | Bounded accounts/pages/models/files/results and no per-account redesign | Manifest/collection constraints | OLL-PERF-001..003 | Real intended accounts and 2–4 processes/models |
| NFR-RES-001; AC-OPS-003 | Failure of one A03 lane leaves other adapters, lanes, API, and UI available | M03 outcome/health contracts | OLL-OPS-001, OLL-LIVE-016 | Natural real lane failure or Blocked status |
| NFR-OBS-001 | Structured safe codes/correlation only; no raw provider or local data | Safe logging contract | OLL-SEC-007/008, OLL-OPS-003 | Log/diagnostic/artifact review |
| NFR-COMP-001; AC-LIVE-004 | Exact protocol/source/parser/provider/extension compatibility and live conformance | CTR-PROV-001..008 | OLL-PURE-003..005, OLL-LIVE-001 | Contract gate plus real current tuples |
| AC-LIVE-003 | Enroll or accurately document both intended Ollama account/workspace identities | CTR-REG/CTR-PROV | OLL-LIVE-002/003 | Owner-confirmed real identities |
| AC-LIVE-005 | Reconcile displayed quota/API values with authoritative surface at matching scope/time | CTR-CAP-001/002 | OLL-LIVE-006/008 | Owner comparison within evidenced tolerance |
| AC-LIVE-007 | Preserve naturally observed unavailable/exhausted/auth/recovery states; otherwise report Blocked | CTR-PROV-004/006 | OLL-LIVE-016 | No manufactured provider condition |
| AC-HIST-001 | Real A03 observation reaches M05/M06 history and UI through production path | CTR-COL/CAP/RUN | OLL-OPS-006 | Real DB/HTTP/built-browser path; no seed |
| AC-OPS-006 | Stay within approved local/cloud/API request/rate/cost constraints | CTR-PROV-002 and M04 policy | OLL-NET-009, OLL-PERF-001 | Real measured polling under approved policy |

A03 contributes evidence to these criteria; it cannot by itself pass registry enrollment, capacity normalization, process hierarchy, database history, API, UI, or release criteria.

## 3. Adapter design

### 3.1 Adapter identity and composition

A03 is registered statically through M03. Provider-product identity must distinguish every product surface M0 finds materially different. The manifest cannot use one broad `ollama` record to hide different client, daemon, cloud subscription, or API compatibility rules.

The adapter facade contains no global mutable singleton and performs no discovery during import. Composition supplies admitted production ports and immutable configuration. Adapter initialization validates its descriptor, capability rows, sources, parser registry, extension schemas, bounds, and compatibility fingerprints without contacting Ollama.

Every invocation carries one `ProviderTargetV1`, one negotiated capability/source policy, one deadline/cancellation context, and only opaque access grants. It cannot enumerate other accounts, workspaces, roots, hosts, or credentials.

### 3.2 Capability activation state

Each exact capability tuple has two separate dimensions:

- discovery decision: `supported`, `experimental`, `deferred`, `unsupported`, or `unknown`;
- compatibility/activation state, using the exact M03 vocabulary:
  `compatible_verified`, `protocol_incompatible`, `manifest_invalid`,
  `capability_schema_incompatible`, `extension_schema_incompatible`,
  `provider_version_unverified`, `provider_version_unknown`,
  `platform_unsupported`, `disabled_by_policy`, or `registration_conflict`.

Completed invocations use only the twelve canonical M03 provider outcomes.
Caller cancellation publishes no completed provider outcome; M04 records the
cancelled collection-run state through the separate cancellation control path.

Only `supported` and separately approved/opted-in `experimental` rows may expose an invokable port. This Draft approves no Experimental source. `Unknown`, `Deferred`, and `Unsupported` are never implemented as a call that returns empty data.

An enabled local-service capability does not enable a cloud/API lane. A cloud identity result does not enable subscription quota or API billing. Unsupported API billing does not disable local runtime metrics.

### 3.3 Source registry and no-fallback rule

For each capability, A03 registers exact source IDs under CTR-PROV-003 using only:

1. documented API;
2. supported CLI;
3. approved local metadata;
4. separately approved Experimental private/browser source.

Every source record includes product surface, capability/schema, method category, official citation/evidence ID, client/service/API version scope, platform, plan/account/workspace class, credential-role category, expected freshness/latency, timeout/page/output/request/rate/cost bounds, potential side effects, and permitted fallback transitions.

There is no implicit fallback between local daemon, local file/log, cloud subscription UI, cloud API, or API billing source. An official-source failure cannot activate a local log or private endpoint. A configured custom endpoint cannot silently replace the approved host/source tuple.

### 3.4 Version and parser registry

Client, daemon/service, local response schema, cloud API, and local metadata format may have independent versions. A03 stores them independently in provenance and applies only the M0-approved version comparison scheme: semantic, exact, date-based, opaque, or another evidenced rule. It never assumes that a client version proves daemon or cloud schema compatibility.

Each parser/mapping registration contains:

- provider product surface and capability;
- exact source/mechanism ID and parser/schema version;
- verified client, daemon, API, and platform tuple as applicable;
- closed input field/path selection and output DTO major;
- size, depth, item, numeric, string, and time bounds;
- forbidden-field categories;
- expected completeness and version signal;
- sanitized error codes and live evidence references.

Unknown or missing version evidence returns `unverified_provider_version` before a version-sensitive source is interpreted. There is no nearest-version or best-effort parser. A parser behavior or field-meaning change increments A03 version and extension major where required.

### 3.5 Resource-pool separation

A03 represents potential identity/resource layers separately:

- local installation and daemon/service instance;
- local installed model definition;
- local loaded/running model/runtime instance;
- cloud personal/team/organization/workspace identity;
- cloud subscription/credit pool;
- API billing account/team/workspace/project/key-safe resource;
- provider session/request reference when safely observable;
- Linux process identity supplied by A04/M06.

Only M0- and M02-approved stable identifiers or opaque adapter-issued references can appear in candidates. A03 emits relationship evidence, not ownership. Unknown relations remain unresolved. A local model name, daemon address, current cloud login, or shared workspace label cannot prove that a local request consumed a subscription/API pool.

Resource-pool mapping to M05 must preserve `independent`, `additive`, `rollup_parent`, `informational`, or `unknown` relationship semantics supplied by M02; A03 does not choose aggregation behavior. Current/legacy plan semantics are source-scoped and never inferred from a display label.

### 3.6 Local service, model, and runtime mapping

When M0 approves a supported local source, A03 may map only its allowlisted structural fields into synchronized contracts. Potential categories remain conditional until M0:

- installed model identity and safe bounded label/version/digest fields;
- loaded/running state and load/unload timing evidence;
- model memory/resource allocation and processor/device classification;
- daemon queue/concurrency and aggregate request counters;
- per-request token/timing counts where the official source exposes them without request/response content;
- safe service health/version state.

Units, scopes, sampling semantics, cumulative versus interval behavior, overlap, and reset behavior must be explicit. CPU/RAM/GPU values are not accepted merely because a field name suggests them. M06 owns runtime state, history, tree, aggregate, and stall meaning. A03 cannot classify working/idle/stuck from service reachability alone.

A local endpoint must be proven read-only. A route that can trigger generation, pull/load/unload/delete/copy a model, change keep-alive, mutate configuration, or return request/response content is not a monitoring source for V1.

### 3.7 Cloud subscription mapping

Only an M0-approved source can produce `ProviderQuotaInputV1`. A03 maps provider-native subscription/credit windows without inventing a universal allowance. Each item preserves:

- exact account/team/workspace/resource scope;
- provider-native window identity and plan class scope;
- used, remaining, limit, credit, or ratio field state and exact unit;
- reset/renewal semantics, timezone, and precision;
- provider status/enforcement code through approved mapping or extension;
- observation/data-through/collection times, freshness, precision, confidence, and source;
- `complete_scope` or `partial_scope` with explicit missing items.

Included and purchased credits remain separate if the provider treats them separately. Subscription and API billing remain separate even if one UI presents them together. A missing limit/credit is Unknown or Unsupported from capability evidence, never computed from another pool.

### 3.8 Ollama API usage, cost, budget, and per-response coverage

The API lane exists only if M0 identifies an official supported source and least-privilege role. It may map the exact approved combination of provider-native time buckets, safe grouping dimensions, token/request quantities, exact money, credits, limits, budgets, renewal/reset, concurrency, or queue values into M05 types.

Per-response metadata has strictly limited coverage:

- it represents only the request that produced it and only fields proven by the source;
- it is not an account total, budget, credit balance, or complete usage history;
- it cannot account for requests sent by already-running external clients unless an official aggregate source proves that coverage;
- A03 will not proxy, intercept, wrap, or modify existing Ollama traffic to expand visibility;
- request and response bodies are never accepted, stored, logged, hashed, sampled, or sent through a contract.

A03 will not estimate provider spend from model pricing and local counts as provider-reported cost. Any future derived-cost feature requires an approved requirement/method contract and must remain visibly derived under M05 ownership.

### 3.9 Local metadata and log eligibility

Files/logs are disabled until M0 approves exact roots, files, fields, versions, bounds, privacy classification, atime/side effects, and containment rules. Allowed output may contain only approved operational metadata. Prohibited categories include:

- prompt/request/response/embedding/tool/source or arbitrary text content;
- request bodies, response bodies, model output, raw HTTP records, or arbitrary headers;
- OAuth/API/session tokens, cookies, credentials, account email, OTP/MFA/recovery material;
- arbitrary command lines, terminal data, environment values, paths, or free-form errors;
- unbounded identifiers, tags, maps, or unknown fields.

The parser must prevent reading prohibited values rather than broadly capture and redact them later. If allowed metadata is inseparable from content/credentials without materializing it, the source is Unsupported. Raw provider artifacts are never retained as fixtures or recordings.

### 3.10 Identity and correlation

A03 produces typed evidence; M02 and M06 own decisions.

Automatic correlation is permitted only when the accepted M0 rule is Strong, identity scope/lifetime/collision behavior is known, and the evidence has no privacy/secret issue. Display names, model names, local host/port, working directory, process timing, current cloud login, PID alone, and plan label never prove an account/workspace relation.

`local.process.correlation` receives only safe A04/M06 process references and approved provider runtime/session references. A03 does not read `/proc`, process command lines, arbitrary environment, terminal, memory, or sockets. Conflicting evidence produces a conflict; weak evidence produces owner confirmation required or unresolved.

### 3.11 Authentication health and reauthentication

Only an approved cloud/API/profile signal can map to `healthy`, `refreshing`,
`expiring`, `reauthentication_required`, `revoked_or_disabled`,
`wrong_account_detected`, or `unknown`. If a provider-native source spells the
state `reauthorization_required`, A03 records only the approved source code and
maps it to canonical `reauthentication_required` before the normalized boundary.
Local daemon reachability, local model availability, and successful
unauthenticated local calls do not prove cloud/API authentication.

Reauthentication is a separately gated capability. A03 rejects before I/O when the profile is protected-default, protection is Unknown, target identity is missing, isolated-profile evidence is absent, the provider version is unverified, or the context lacks an owner-interaction grant.

If later enabled, A03 invokes only the approved official flow against an AgentMonitor-managed profile. The owner performs browser/device/email/MFA/OTP actions directly. A03 never accepts or captures credentials/codes. It verifies returned identity against the expected assertion before M02 reconciliation. A mismatch ends as `wrong_account_detected`; it cannot relink an account or overwrite history.

### 3.12 Deadline, cancellation, pagination, retry, and backoff

- M04/context owns the total deadline, cancellation, concurrency, request/rate/cost admission, and retry/backoff policy.
- Every service, CLI, filesystem, and cloud/API operation receives a bounded slice of the remaining deadline.
- Response/output/file bytes, JSON depth, item counts, pages, and request count are bounded before mapping.
- Pagination uses documented cursor/time semantics and exposes partial completeness truthfully.
- A03 performs no autonomous retry by default. A future provider-documented transport retry requires M0 evidence and an approved M04 contract change.
- Authentication, authorization, wrong-account, protected-profile, unverified-version, invalid-data, and unsafe-source outcomes are never retried.
- Rate limiting returns one typed outcome with provider-supported retry timing/precision only.
- Cancellation stops only the AgentMonitor-owned collection operation; it never signals a monitored agent, local daemon, or model process.

### 3.13 Error and degradation model

A03 returns only CTR-PROV-004 outcomes and bounded stable reason codes. It never returns an exception object, provider message, raw response, stdout/stderr, file fragment, local path, endpoint with query, credential detail, request body, response body, model content, or free-form error.

Expected mappings, subject to M0 evidence, are:

- source/product not installed or documented absent -> `unsupported` or `provider_unavailable` according to the approved decision;
- client/daemon/API version missing or out of range -> `unverified_provider_version`;
- cloud/API credential state -> `reauthentication_required` in
  `CTR-PROV-006`, mapped by API/UI to
  `provider_reauthentication_required`, never dashboard authentication;
- insufficient role -> `authorization_insufficient`;
- expected identity mismatch -> outer `success` with typed identity/reauthentication result `wrong_account_detected`;
- provider throttle -> `rate_limited`;
- response/file/schema mismatch -> `invalid_provider_data`;
- deadline expiry -> `deadline_exceeded`; caller cancellation publishes no completed provider outcome and M04 records the cancelled collection-run state;
- owner step -> `blocked_user_action_required`;
- contained unexpected defect -> `internal_adapter_error` with correlation ID.

One lane's failure changes only that lane. It cannot clear or rewrite current M05/M06 facts; their owners age those facts to stale/Unknown. A03 does not use a cached provider value as current fallback.

## 4. Public contracts

### 4.1 Implemented M03 contracts

A03 implements, but does not redefine, only synchronized versions of:

| Contract | A03 responsibility | Prohibited behavior |
|---|---|---|
| CTR-PROV-001 | static descriptor and typed capability ports | generic execute/raw dictionary |
| CTR-PROV-002 | exact evidence-scoped manifest rows and collection constraints | wildcard version/plan/account support |
| CTR-PROV-003 | exact source descriptors and approved transition chain | implicit source downgrade |
| CTR-PROV-004 | typed success/partial/failure outcome with safe codes | raw body/output/exception leakage |
| CTR-PROV-005 | bounded installation/account/project/resource candidates | creating/linking registry records |
| CTR-PROV-006 | auth-health and expected-identity observation | treating local availability/provider outage as auth fact |
| CTR-PROV-007 | managed-profile official reauth only after separate approval | default-profile mutation or secret capture |
| CTR-PROV-008 | closed Ollama-specific extension schemas | arbitrary JSON, free text, or opaque raw payload |

Every operation receives `ProviderOperationContextV1`. No method accepts a raw credential, environment map, unrestricted path/root, arbitrary host/URL, shell command, request/response body, or free-form provider identifier.

### 4.2 Consumed registry and collection contracts

From M02, A03 consumes a narrow immutable target containing only opaque installation, account, profile, resource, workspace/project references; provider-product key; profile purpose/protection; expected identity assertion; and approved access-grant references. It does not require a friendly name, email, profile path, or credential contents.

Relevant synchronized contracts are CTR-REG-003 `MonitoringProfileViewV1` or its private narrow target, CTR-REG-004 `ProviderInstallationViewV1`, CTR-REG-005 `AccountResourceViewV1`, and CTR-REG-006 `IdentityCorrelationDecisionV1`. Unknown profile protection blocks every mutation-capable flow. Unknown resource identity blocks capacity calls that require it.

From M04 through M03 context, A03 receives operation/correlation IDs, selected capability/source, deadline/cancellation, approved time/page scope, run reference, and request/rate/cost/concurrency grants. A03 never schedules, polls itself, leases work, retries, writes collection history, or decides backoff.

### 4.3 Typed M05 outputs

A03 may construct only approved major versions of:

- CTR-CAP-001 `ProviderQuotaInputV1` for evidenced subscription quota/credit windows;
- CTR-CAP-002 `ProviderUsageInputV1` for evidenced API usage buckets;
- CTR-CAP-002 `ProviderCostInputV1` for evidenced exact provider cost;
- CTR-CAP-002 `ProviderBudgetInputV1` for evidenced budget/credit/limit/enforcement data.

M05 owns exact field states, values, units, money, windows, periods, dimensions, completeness, resource-pool semantics, and cardinality. A03 owns source-specific extraction/mapping. A proven safe provider concept that does not fit triggers contract synchronization; it never becomes an `extra` dictionary, arbitrary dimension, guessed normalization, or provider conditional in M05.

Local resource metrics cannot be sent through a capacity DTO merely because they are numeric. Subscription and API resource IDs cannot be substituted for one another.

### 4.4 Typed M06 outputs

A03 may construct only synchronized M06 closed values:

- CTR-RUN-002 `LocalSessionObservationInputV1` or the approved Ollama runtime equivalent;
- CTR-RUN-002 `RuntimeMetricObservationInputV1`;
- approved model/runtime relationship and state-evidence input types;
- CTR-RUN-007 correlation-evidence inputs;
- `RuntimeObservationBatchV1` through the M03/M04 commit path.

A03 does not create public `AgentSessionViewV1`, process identity, normalized runtime state, session tree, parent aggregate, stall classification, or account-correlation decision. It cannot relabel installed models as running sessions or local daemon workers as user agents without approved semantics. Unknown/unsupported values remain field states, never zeros/defaults.

### 4.5 A04 platform boundary

A04-LINUX implements process inspection. A03 receives only approved safe process references when a correlation operation requires them. It neither imports A04 implementation nor invokes OS APIs.

The final synchronization must define whether generic Ollama daemon/model processes are presented as M06 sessions, process-only records, model-runtime records, or another safe typed concept. A03 cannot invent hierarchy or turn OS ancestry into provider parent/subagent semantics.

### 4.6 Ollama provider extensions

No extension field is approved by this Draft. M0 may propose one only when a safe Ollama-specific concept cannot map to a normalized M05/M06 contract.

Every proposed extension declares:

- stable identity `ollama.<surface>.<capability>.<schema>.v<major>` or synchronized equivalent;
- exact surface/capability/source/parser/client/daemon/API/platform/account-plan scope;
- closed fields with type, unit, nullability, enums, cardinality, length/numeric/depth bounds;
- privacy classification and proof excluding credentials, identity beyond approval, request/response/prompt/tool/source content, arbitrary environment, paths, or raw output;
- M05/M06/API/UI consumer opt-ins;
- compatibility, migration, and unknown-major behavior;
- M0 and live evidence references.

Unknown members or majors are rejected. They are not persisted as opaque JSON. Meaning, unit, privacy, or scope changes require a new extension major and consumer migration.

### 4.7 Provenance contract

Every successful or partial result supplies the A03 portion of CTR-COMMON-004:

- provider product surface, capability, and schema;
- adapter/protocol/source/parser/client/daemon/API version as applicable;
- actual source class and stable source ID;
- provider observation/data-through and collection start/end times when available;
- freshness deadline or explicit Unknown plus policy reference;
- precision, confidence, and stable explanation code;
- value kind: authoritative, provider-reported, derived, heuristic, or Unknown;
- Experimental flag and any approved fallback lineage;
- bounded safe warning codes;
- operation/correlation ID and accepted M0 decision reference.

A03 does not set `stored_at`, capacity/runtime projection time, or downstream derivation metadata. Missing mandatory provenance invalidates success or creates an explicitly allowed partial result.

### 4.8 Contract impact and required synchronization

This plan implements `CTR-PROV-001..008`, `CTR-COMMON-004`, CTR-CAP inputs,
and CTR-RUN inputs. A03 owns Ollama extension schema definitions only within the
M03-governed namespace; M03 remains semantic producer of `CTR-PROV-008`. This
Draft changes no implemented contract.

Before approval, synchronization must resolve:

1. exact separate/static provider-product registrations inside A03 for Ollama
   local, cloud subscription, and API billing identities;
2. exact provider-product, adapter, lane, capability, source, parser, schema, extension, and version identifiers;
3. exact narrow M02 target/profile/protection/identity/resource contracts;
4. exact M05/M06 input contract versions, fields, bounds, and completeness rules;
5. the M06 representation of models, model-load instances, daemon processes, requests, sessions, and hierarchy;
6. safe HTTP/subprocess/filesystem/profile/cancellation/redaction port ownership;
7. local-service versus cloud/API network host policy and opaque credential application;
8. the managed reauth coordinator and isolated profile lifecycle;
9. M04 time/page/request/rate/cost/concurrency/retry/commit semantics for every lane;
10. extension locations/consumer opt-ins and component-health mapping;
11. configuration ownership and static composition ownership;
12. canonical automation selectors and evidence formats.

Any semantic change after synchronization follows contract versioning and may require an ADR.

## 5. Data and persistence

### 5.1 Owned persistent data

A03 owns **no database table, migration, repository, outbox, durable cache, account/resource record, observation history, profile credential, or provider state**.

- M02 persists registry/profile/resource relationships.
- M03 persists compatibility assessments if synchronized.
- M04 persists schedules and collection runs.
- M05 persists quota/API observations and projections.
- M06 persists runtime/process/session observations and correlation decisions.
- M08 persists operations records.

Adapter source/parser/version/extension metadata is declared in versioned code and schema documentation, then assessed through M03. A03 must not duplicate it in a convenience table.

If implementation reveals a need for durable page cursors, auth-flow state, request accounting, local model inventory cache, or mapping data, work stops. The owning module and versioned contract are assigned through synchronization; A03 does not create a table or file.

### 5.2 Permitted in-memory state

Permitted process-local state is limited to immutable descriptor/source/parser registries, bounded executor/network resources supplied by approved ports, and per-operation ephemeral values. It cannot:

- outlive an operation as current telemetry;
- become a cross-run provider-result cache;
- hold provider credentials outside the owning access port;
- retain request/response bodies, prompts, model output, logs, or raw provider artifacts;
- bypass M04 request/rate/concurrency accounting;
- infer completeness from accumulated partial results.

Raw approved input is released after allowlisted mapping. Cancellation/exception handling clears references as practical and emits only stable safe diagnostics.

### 5.3 Retention, backup, restore, migration, and rollback impact

A03 has no adapter-owned retention, backup, restore, or database migration. Manifest/parser/schema source files follow release versioning. Rollback changes static adapter composition/capability exposure and never deletes M02/M05/M06 history.

M03/M05/M06 migrations remain owned by those modules. A03 schema changes stay readable across the synchronized compatibility window or use a new major with coordinated consumer migration.

## 6. External and platform boundaries

### 6.1 Installation/client/service boundary

A03 uses an approved safe subprocess/service-discovery port with opaque executable/service references. It never searches arbitrary `PATH`, starts/stops/restarts a daemon, uses a shell, installs/updates Ollama, or changes service configuration.

Client and service versions are discovered independently through reviewed operations. A read-only-looking command is not executable until M0 verifies it. Direct argument vectors, minimal environment, deadlines, process-group cleanup, and stdout/stderr bounds are enforced by the production safe-execution port. Cancellation may stop only an AgentMonitor-owned collector subprocess.

### 6.2 Local service network boundary

The local-service lane uses only M0-approved documented hosts, schemes, methods, routes, and response shapes. The network port enforces destination identity, redirect policy, TLS when applicable, method, header, response-size, item, and deadline bounds.

No arbitrary base URL is accepted merely because it speaks a similar protocol. An owner-configured remote Ollama service is a separate platform/trust tuple and remains Unknown until reviewed. A03 never sends cloud/API credentials to a local or custom host and never calls a generation, model-management, or state-mutating route for monitoring.

### 6.3 Cloud/API network boundary

The cloud/API lane uses only approved official HTTPS hosts and least-privilege provider-managed credential application. A03 never receives/logs the credential value. Allowed endpoint, method, query/grouping, pagination, response-size, redirect, timeout, request-count, rate, and possible monetary cost derive from M0.

No private/browser endpoint, cookie, traffic interception, proxy, model-generation call, arbitrary URL, cross-host redirect, or insecure TLS override is allowed. Unexpected redirect/host/schema/role/cost stops the operation.

### 6.4 Filesystem and log boundary

An approved safe filesystem port supplies opaque root/file grants. A03 validates containment, symlink policy, regular-file/type/owner/mode where required, size, stable-read/race behavior, atime decision, and deadline before an approved read.

There is no recursive scan, broad glob, credential-file read/hash/copy, raw log ingestion, provider-state write, or unapproved path. M0 must prove prohibited content is prevented at source. Permission denied, format drift, unsafe mixed content, and path escape return typed outcomes.

### 6.5 Process boundary

A03 does not enumerate processes or inspect `/proc`. A04-LINUX supplies safe process facts through CTR-RUN-006/M06. A03 may correlate only closed safe references using an approved join rule. It has no signal, stdin, attach, memory, terminal, environment, restart, stop, kill, model unload/load, or routing method.

### 6.6 Authentication/profile boundary

Provider credentials stay in provider-managed storage. A03 receives only opaque profile/credential access grants and never copies values to `.env`, database, logs, tests, evidence, arguments, or diagnostics.

The owner's browser/device/email/MFA/OTP interactions remain outside A03. Default profiles are protected/read-only. An AgentMonitor-managed profile can be changed only through the separately approved official flow and explicit owner grant.

### 6.7 Timeout, isolation, and safe failure

Every external operation has a finite deadline and byte/item/page/request bound. Boundary failures map to typed outcomes before they reach domain modules. A malformed local response or cloud payload affects one lane/target/capability only. A03 health reports degradation without making unrelated API/UI queries unavailable.

### 6.8 Real verification matrix

Every enabled lane is verified at its real boundary:

- client/service discovery: current real installed Ollama components through production execution/discovery ports;
- local service/model/runtime: approved real daemon endpoints/tools and 2–4 naturally running processes/models where available;
- filesystem/log source: approved real provider artifact through production safe-filesystem path, only if M0 supports it;
- cloud subscription: both intended owner-confirmed account/workspace identities and authoritative provider surface;
- API usage/cost/budget: real owner-controlled credential role and official data source, if supported;
- local correlation: real naturally running Ollama processes/models plus A04/M06 safe observations;
- reauth: real AgentMonitor-managed profile and owner-driven official flow after separate authorization;
- failure isolation: naturally available real failure/unavailability only; otherwise Blocked.

No local provider simulator, fake daemon, fake CLI, fake filesystem, fixture response, recording, seeded account, demo telemetry, placeholder model, or test-only production path can replace these boundaries.

## 7. Security and privacy

### 7.1 Threats and required controls

| Threat | Required A03 control |
|---|---|
| local endpoint performs generation/mutation | exact method/route allowlist and M0 side-effect proof; reject unapproved operation |
| local endpoint is remote/untrusted | destination identity and trust tuple; no arbitrary URL or credential forwarding |
| huge/malicious response or provider file | byte/depth/item/time bounds, closed parser, no unsafe deserialization |
| logs/responses contain prompts or model output | exclude source/route or parse only proven structural metadata without retaining raw data |
| credential leakage | opaque grant applied only by owner port; no values in args/results/logs/evidence |
| subscription/API/local pools are conflated | separate lanes/IDs/DTOs and M02/M05 relationship proof |
| local per-request count becomes account total | explicit scope/completeness; no aggregation beyond observed request |
| already-running clients become invisible | truthful coverage limitation; no proxy/interception workaround |
| wrong account/workspace enrolled | stable evidence plus owner confirmation; mismatch stop |
| default profile changed | protected/unknown rejection before mutation and live no-change verification |
| provider/parser version drifts | exact version gate; unverified rather than best effort |
| source downgrades to private/log surface | exact M03 negotiation; no implicit fallback |
| monitored agents/service are disrupted | no control methods; collector cancellation isolated |
| dependency/SDK leaks telemetry or credentials | dependency admission, network/telemetry review, minimal graph |

### 7.2 Allowlist data flow

Security review maintains one field-flow record for every enabled source:

```text
external field/category
  -> prevention or approved bounded ephemeral read
  -> A03-local typed field
  -> M02/M05/M06 field or approved Ollama extension
  -> allowed log/diagnostic representation
  -> owning persistence/retention contract
```

Anything not listed is rejected. Broad capture followed by redaction is not approval. Dynamic quota/cost values, account identity, local paths, raw request IDs, model content, provider output, and credentials never enter committed evidence.

### 7.3 Request/response-content exclusion proof

Every local/cloud endpoint or file candidate receives a schema-level content review before activation. The proof must show:

- which exact fields are requested/read;
- that request bodies are absent for monitoring calls except a non-content typed query proven necessary and safe;
- that response mapping cannot retain prompt, response, embedding, tool, source, or arbitrary free text;
- that raw bytes/objects are discarded after mapping and never logged, recorded, hashed, cached, or persisted;
- that API/UI/event/DB/export/backup/diagnostic schemas cannot carry prohibited fields;
- that malformed/unknown fields fail closed.

If this cannot be shown, the source is Deferred or Unsupported.

### 7.4 Default-profile and state immutability proof

Read-only live packets define approved non-secret pre/post metadata and owner-visible checks for provider profile, service configuration, installed/loaded model state, and running processes. They do not read credential contents or retain credential-file hashes. Any unexpected write, model load/unload, provider audit action beyond approved read access, or process reaction fails the scenario and stops work.

Managed reauth targets only an AgentMonitor-managed profile with definitive non-default classification. Unknown classification rejects the operation before provider invocation.

### 7.5 Logging and diagnostics

Allowed fields are timestamp, severity, A03 component/lane, safe event/error code, correlation/operation ID, opaque internal target, capability/source/adapter/client/service/API/parser/schema versions, duration, bounded counts, outcome class, and retry disposition.

Forbidden fields include response/request bodies, prompts, model output, tool/source content, raw command/stdout/stderr, URLs with query, headers, local paths, model/account/workspace labels unless separately approved for authenticated view, credential material, provider metric values, arbitrary exception strings, and environment values.

### 7.6 No-control proof

Static API/import/operation scans must show A03 exposes no model generation, model management, daemon lifecycle, process signal, terminal input, attach, routing, credential switching, or arbitrary request port. Runtime live verification confirms only AgentMonitor collector work can be cancelled.

### 7.7 Incident stop

Stop without retry or broader inspection when:

- secret, personal identity, request/response/prompt/tool/source content, raw payload, arbitrary path/environment, or unknown high-risk data appears;
- a command/request prompts login, update, install, pull, purchase, consent, model generation, or write;
- a provider profile, daemon configuration, model state, account, budget, credential, or running agent may have changed;
- an unexpected host/redirect/endpoint/cost/rate condition occurs;
- source/version/scope differs from the approved tuple;
- account/workspace/resource/process identity is uncertain or conflicting.

Protect only sanitized incident metadata, quarantine accidental sensitive output outside repository/chat, notify owner/root/security, follow owner-controlled rotation/incident procedure when required, mark affected tests Failed or Blocked, and require new discovery/security/contract approval before resuming.

## 8. Configuration and operations

### 8.1 Configuration ownership

This Draft allocates no final environment-variable name. Candidate categories, all M0 and synchronization blocked, are:

- lane enablement derived from registered monitoring profiles/resources;
- opaque client/service/profile/root references owned by M02/deployment;
- approved local service endpoint reference and trust classification, never arbitrary URL by default;
- capability/source and Experimental grant state owned by synchronized M02/M03 workflow;
- deadlines, page/item/byte/request/rate/cost/concurrency bounds owned by M04/M03 with A03 evidence constraints;
- cloud/API host allowlist and credential access owned by the security/network/profile ports;
- parser and compatibility records shipped with A03, never operator-overridden to weaken safety.

Configuration cannot enable an Unknown/Unsupported version, add a host/path/field/route, turn a generation route into telemetry, bypass profile protection, expose raw diagnostics, or merge resource pools. Provider credentials are not AgentMonitor `.env` values.

Every approved key receives a CTR-CONFIG-001 record naming owner, type, unit, bound, safe default, source/precedence, reload/restart behavior, secret classification, compatibility version, operational consequence, and tests.

### 8.2 Health and readiness

A03 publishes a bounded component-health contribution through M03/M08:

- adapter registration/protocol/manifest status;
- lane/capability decision and enabled state;
- independent client/service/API version verification;
- local-service availability separate from cloud/API authentication;
- last collection outcome references from M04, not duplicated observation values;
- authentication/authorization/version/rate/deadline/invalid-data safe categories;
- source/parser/schema version and current compatibility decision;
- stale, Unknown, Unsupported, Disabled, and unavailable distinctions;
- bounded safe warning codes.

Health performs no provider call. An optional Unsupported lane does not make the application unready. Invalid manifest, unsafe endpoint/profile, or enabled incompatible capability makes only the affected lane unavailable and visible.

### 8.3 Canonical automation selectors

Foundation/integration owns canonical commands. Before A03 implementation handoff, repository automation must provide fail-closed selectors for:

- A03 pure contract/source/version/mapping policy tests;
- real Ollama client/service/local-endpoint/filesystem tests;
- real Ollama cloud subscription/API tests where supported;
- live identity/quota/API/runtime/correlation/reauth matrices;
- import, public-surface, protocol, schema, extension, and compatibility checks;
- prohibited double/recording/fixture/seed/content/secret/control/proxy scans;
- dependency/license/security/SBOM/notices checks;
- documentation, traceability, live-status, and evidence validation.

Each command reports Passed, Failed, Blocked, and Not Run separately. A deterministic green suite cannot conceal absent T5/T6 evidence. Exact command names remain foundation/integration owned until implemented and verified; prose here is not the executable gate.

### 8.4 Operator procedures

Approved implementation documentation must eventually contain verified procedures to:

- inspect A03 manifest, lane, source, version, and compatibility health;
- distinguish local-service, cloud-subscription, and API-billing problems;
- enroll/confirm account, workspace, profile, and resource relationships through M02;
- trigger one bounded manual refresh through M04;
- diagnose local endpoint, version, auth, authorization, rate, parse, privacy, and source failures safely;
- run the real 2-identity and 2–4-process/model verification matrix;
- perform managed-profile reauth only through the approved owner interaction;
- disable/rollback an affected source/lane;
- repeat discovery/live verification after version or plan changes;
- handle suspected secret/content/default-profile/provider-state incidents.

Unimplemented commands remain Planned/TBD and are never invented.

### 8.5 Operational measurements

Allowed local measurements are bounded A03 operation counts/durations by capability/outcome, compatibility states, safe response/output byte counts, page/item counts, and rate/backoff metadata. No provider metric value, money, account/workspace identity, model/request content, local path, secret, or external AgentMonitor analytics is emitted.

## 9. Test design before implementation

### 9.1 Evidence state and integrity rules

Every scenario in this section is **Not Run** when this Draft is created. No provider, service, file, account, profile, process, or credential has been accessed by this plan.

A future Red is valid only when the test reaches its specified production or pure boundary and fails for the expected missing/incorrect behavior. Missing dependencies, credentials, owner availability, installed products, approved sources, or setup are `Blocked` or `Not Run`, not Red. A syntax/import/setup error does not prove behavior.

Prohibited in every test:

- mocks, fakes, stubs, emulators, fake daemons, local provider servers, monkeypatched collaborators, or fake clocks;
- recorded/replayed network/service/CLI/file responses or committed provider fixtures;
- demo accounts, invented accounts/workspaces, seeded telemetry, placeholder values, generated provider rows, or screenshots presented as data;
- hardcoded passing branches, disabled assertions, swallowed failures, test-only production endpoints, or retry-until-green behavior;
- model-generation calls, credit exhaustion, credential revocation, profile modification, daemon/model/process control, or traffic proxying merely to manufacture a state.

Constructed values are permitted only for side-effect-free domain/contract rules such as capability-state distinction, source selection, unit-preserving mapping, and identity-evidence policy. Pure mapping tests use owner-approved E1 field names/types from M0, represented as typed structural examples without dynamic provider values. They do not prove parser or provider compatibility. Real parser compatibility is verified by the production parser against the current real service/API/file source without retaining raw input.

All dynamic values are reconciled by identity, scope, unit, relationship, time, precision, freshness, source, and documented tolerance. Quota, spend, tokens, loaded models, and reset values are never hardcoded.

### 9.2 Pure contract, resource, and source-policy scenarios (T1)

| Test ID | Requirement | Initial Red expected | Green/pass condition |
|---|---|---|---|
| OLL-PURE-001 | FR-COL-006/008 | Unknown/Deferred/Unsupported capability exposes an invokable port | only Supported or approved opted-in Experimental resolves |
| OLL-PURE-002 | FR-COL-007/008 | failed official source silently downgrades to log/private source | only exact approved source chain can transition |
| OLL-PURE-003 | FR-DISC-008 | client version is reused as daemon/API version | each version dimension remains independent/Unknown-aware |
| OLL-PURE-004 | FR-DISC-008 | nearest/guessed parser is chosen for an unknown version | exact evidenced rule selects or returns unverified |
| OLL-PURE-005 | FR-COL-004 | success accepts missing source/parser/service/API version provenance | mandatory evidence is present or success is rejected |
| OLL-PURE-006 | FR-ACC-004 | local, subscription, and API resources collapse into one pool | separate typed resource references and relationships survive |
| OLL-PURE-007 | FR-ACC-006/FR-DISC-004 | same display/model/workspace label proves identity | weak evidence remains unresolved/confirmation required |
| OLL-PURE-008 | FR-DISC-004 | timing/PID/current login selects an account | no automatic association without approved Strong rule |
| OLL-PURE-009 | FR-DISC-004 | conflicting evidence chooses one candidate | conflict is explicit and no account is selected |
| OLL-PURE-010 | FR-AUTH-001 | reachable local service maps to healthy cloud auth | local availability and auth remain separate |
| OLL-PURE-011 | FR-AUTH-001 | missing auth evidence maps to healthy | auth state is Unknown with stable reason |
| OLL-PURE-012 | FR-COL-003 | adapter retries a rate/auth/version result | one typed outcome returned; M04 owns retry/backoff |
| OLL-PURE-013 | FR-COL-006 | Unsupported and runtime unavailable collapse | decision and current availability remain distinct |
| OLL-PURE-014 | FR-COL-008 | partial omission becomes zero/retired/complete | explicit partial scope and missing fields survive |
| OLL-PURE-015 | FR-BUDGET-003 | one per-response count becomes complete account usage | scope remains one request and completeness stays partial |

Mutation review must kill meaningful changes to resource-lane separation, no-fallback policy, version selection, completeness, correlation, and authentication separation. Exact mutation score is selected at synchronization; coverage percentage alone is not proof.

### 9.3 Pure typed mapping scenarios (T1; no provider-boundary claim)

| Test ID | Requirement | Initial Red expected | Green/pass condition |
|---|---|---|---|
| OLL-MAP-001 | FR-QUOTA-001/002 | two native subscription windows merge by label | each approved window identity remains distinct |
| OLL-MAP-002 | FR-QUOTA-001/004 | missing balance/limit maps to zero | exact Unknown/Unsupported/withheld state preserved |
| OLL-MAP-003 | FR-QUOTA-001 | reset loses source timezone/precision | exact reset/renewal semantics preserved |
| OLL-MAP-004 | FR-COL-004 | quota mapping omits freshness/confidence/source | M05 input requires complete provenance |
| OLL-MAP-005 | FR-DISC-006 | local memory/GPU value loses unit/sampling scope | exact unit/semantics required or field unverified |
| OLL-MAP-006 | FR-DISC-006 | installed model is treated as loaded/running | lifecycle/presence kinds remain distinct |
| OLL-MAP-007 | FR-DISC-006 | cumulative and interval request/token counts combine | scope/time/overlap classification blocks invalid aggregate |
| OLL-MAP-008 | FR-DISC-003 | arbitrary text/log/error enters runtime DTO | closed safe field/code contract rejects it |
| OLL-MAP-009 | FR-BUDGET-004 | money becomes binary float | exact M05 money representation is preserved |
| OLL-MAP-010 | FR-BUDGET-003 | arbitrary model/key/tag grouping enters DTO | only synchronized dimensions and safe IDs pass |
| OLL-MAP-011 | FR-BUDGET-005 | subscription credit and API credit add together | independent resource pools remain separate |
| OLL-MAP-012 | FR-BUDGET-002/006 | absent official budget becomes derived provider budget | field remains Unsupported/Unknown; no provider claim |

These tests accept only typed structural values; they do not feed stored provider payloads into a parser and cannot expand a verified version range.

### 9.4 Real client, daemon, and local-service scenarios (T5/T6)

| Test ID | Requirement/AC | Real dependency | Initial Red expected | Green/pass condition / owner coordination |
|---|---|---|---|---|
| OLL-SVC-001 | FR-ACC-005 | current real Ollama installation | installation/client/service not found or conflated | supported components and absence map truthfully |
| OLL-SVC-002 | FR-DISC-008 | real client and service version surfaces | provenance omits or conflates versions | exact available versions/Unknown fields recorded |
| OLL-SVC-003 | AC-LIVE-004 | real M03 registration | manifest is broader than installed/evidenced tuple | only matching compatible rows resolve |
| OLL-SVC-004 | FR-DISC-001 | naturally running real Ollama service | discovery changes launch/service workflow | supported presence observed with zero control effect |
| OLL-SVC-005 | FR-DISC-006 | 2–4 real loaded/running models/processes when naturally available | model/runtime presence is missed or mislabeled | facts reconcile or explicitly remain unavailable |
| OLL-SVC-006 | FR-DISC-003/006 | approved real read-only endpoint/tool | content-bearing/mutating route is invoked | only reviewed source/fields read; zero unapproved effect |
| OLL-SVC-007 | FR-DISC-006 | real resource/load data if supported | units/scope/sampling semantics are wrong | values reconcile structurally with authoritative source |
| OLL-SVC-008 | FR-COL-005 | natural partial/nonzero service outcome | raw provider error/output leaks | stable code and bounded discarded raw data |
| OLL-SVC-009 | FR-COL-005 | real finite deadline | operation hangs or stops daemon/agent | typed deadline; collector cleanup only |
| OLL-SVC-010 | FR-DISC-008 | real current response/parser version | wrong parser accepts source | exact parser selection and provenance |
| OLL-SVC-011 | NFR-SEC-001 | real endpoint response | unknown/unbounded field passes to domain | allowlisted extraction or invalid-data outcome |
| OLL-SVC-012 | FR-DISC-004 | real safe M06/A04 references | weak runtime/process evidence maps account | Strong rule only or unresolved/conflict |

No test starts generation, pulls/deletes/copies/loads/unloads a model, changes keep-alive, restarts the daemon, installs/updates Ollama, or kills a process.

### 9.5 Real filesystem and local-metadata scenarios (T5/T6; only if M0 supports a source)

| Test ID | Requirement/AC | Real dependency | Initial Red expected | Green/pass condition / owner coordination |
|---|---|---|---|---|
| OLL-FS-001 | FR-DISC-003 | approved real Ollama root/file | adapter enumerates an unapproved path | only opaque grant/allowlist accessed |
| OLL-FS-002 | AC-PROC-004 | approved real metadata artifact | content/credential/raw log is materialized or persisted | prevention plus artifact scan proves absence |
| OLL-FS-003 | FR-DISC-003 | real permission boundary | denial becomes empty success | permission/partial/unavailable is explicit |
| OLL-FS-004 | NFR-SEC-001 | real symlink/path condition if naturally present | path escapes approved root | escape rejected before read; absent case remains Blocked |
| OLL-FS-005 | NFR-SEC-001 | real bounded file | oversized/racing file is read unbounded | size/stable-read/deadline policy fails safely |
| OLL-FS-006 | FR-DISC-006 | real approved metadata | model/runtime/request scope mapped incorrectly | source/unit/time/completeness reconcile |
| OLL-FS-007 | FR-DISC-003 | real mixed-content candidate | parser broadly captures then redacts | source rejected unless prohibited values are never materialized |
| OLL-FS-008 | FR-DISC-004 | real identity/correlation metadata if supported | label/current login proves account | safe stable evidence only or unresolved |
| OLL-FS-009 | FR-DISC-008 | real format/version drift if naturally present | old parser accepts changed shape | invalid/unverified result; prior facts age stale |

When M0 marks local files/logs Unsupported, these scenarios document the decision and remain non-executable; Unsupported discovery is not a Passed filesystem integration test.

### 9.6 Real cloud subscription and Ollama API scenarios (T6)

| Test ID | Requirement/AC | Real dependency | Initial Red expected | Green/pass condition / owner coordination |
|---|---|---|---|---|
| OLL-NET-001 | FR-ACC-004/005 | approved real cloud identity source | wrong account/team/workspace/resource scope | owner-confirmed candidates and relations are preserved |
| OLL-NET-002 | FR-BUDGET-001/006 | approved real API role/account | unsupported endpoint/role is invoked | exact capability/role/source tuple enforced |
| OLL-NET-003 | FR-BUDGET-003 | real usage source if supported | bucket/group/page scope lost | bounded typed M05 usage input reconciles |
| OLL-NET-004 | FR-BUDGET-002/004 | real cost source if supported | money/currency/period imprecise | exact cost input reconciles; otherwise Unsupported |
| OLL-NET-005 | FR-BUDGET-002 | real budget/credit/limit source if supported | absent fields inferred from usage/pricing | provider field mapped or explicit Unsupported/Unknown |
| OLL-NET-006 | FR-COL-004 | real provider data latency | observed/data-through/collected/freshness conflated | each time/precision retained |
| OLL-NET-007 | FR-BUDGET-003 | real pagination if supported | omitted pages appear complete | cursor/request count/completeness truthful |
| OLL-NET-008 | FR-COL-008 | real provider response | unexpected shape accepted or raw retained | closed extraction/rejection and no raw artifact |
| OLL-NET-009 | FR-COL-003; AC-OPS-006 | natural real rate-limit signal if available | adapter retries or exceeds budget | one typed outcome; M04 backoff; otherwise Blocked |
| OLL-NET-010 | FR-COL-005 | natural network outage/deadline if available | one failure blocks other lanes | bounded isolated failure; otherwise Blocked |

Credentials are supplied only through the approved owner-controlled local mechanism. The agent never sees, prints, passes in arguments, or records the value.

### 9.7 Live identity, reconciliation, runtime, and reauth matrix (T6)

| Test ID | Requirement/AC | Real boundary | Initial Red expected | Green/pass condition / owner coordination |
|---|---|---|---|---|
| OLL-LIVE-001 | AC-LIVE-004 | current real Ollama client/service/cloud/API tuples | M03 conformance fails or overclaims | every enabled tuple passes exact real conformance |
| OLL-LIVE-002 | AC-LIVE-003 | intended Ollama identity alias 1 | not enrolled/relationship unclear | owner confirms identity/resources or records unavailable |
| OLL-LIVE-003 | AC-LIVE-003 | intended Ollama identity alias 2 | not enrolled/relationship unclear | owner confirms identity/resources or records unavailable |
| OLL-LIVE-004 | FR-AUTH-001 | real account/profile | auth state disagrees with authoritative surface | scope/time/evidence reconcile |
| OLL-LIVE-005 | FR-QUOTA-001/006 | real supported cloud subscription identity | native windows/credits/limits differ | every supported field/window maps; gaps explicit |
| OLL-LIVE-006 | AC-LIVE-005 | authoritative subscription surface | value/unit/reset/scope/time mismatch | nearest-time comparison passes approved tolerance |
| OLL-LIVE-007 | FR-BUDGET-001..006 | real API billing account/workspace | usage/cost/budget lane incomplete | supported capabilities reconcile; unsupported explicit |
| OLL-LIVE-008 | AC-LIVE-005 | authoritative API billing surface | identity/scope/time/currency mismatch | nearest-time comparison passes approved tolerance |
| OLL-LIVE-009 | AC-PROC-001 | real running Ollama processes on Linux | workflow/service/process changes or discovery misses | safe presence without launch-flow change |
| OLL-LIVE-010 | FR-DISC-006 | 2–4 naturally running/loaded process/model instances | catalog/load/runtime state conflated | each fact is correctly typed or unavailable |
| OLL-LIVE-011 | AC-PROC-002 | representative real process/model hierarchy | OS/provider hierarchy guessed | proven edges only; conflicts/orphans visible |
| OLL-LIVE-012 | AC-PROC-004 | full real observation path | content/environment/secret enters persistence/artifacts | scans prove only approved operational metadata |
| OLL-LIVE-013 | FR-DISC-004 | real strong correlation candidate | expected account/workspace/process relation not found | approved rule agrees with owner/evidence |
| OLL-LIVE-014 | AC-PROC-003 | real ambiguous candidate | adapter assigns account/workspace | unresolved/confirmation-required is visible |
| OLL-LIVE-015 | FR-ACC-006 | real conflicting candidate if naturally present | adapter selects one side | conflict retained; otherwise Blocked |
| OLL-LIVE-016 | AC-LIVE-007 | natural auth/exhausted/unavailable/recovery condition | states collapse or cached data is current | exact state/recovery; absent cases remain Blocked |
| OLL-LIVE-017 | AC-LIVE-006 | separately approved managed profile | reauth targets unsafe/default profile | official flow starts only for managed target |
| OLL-LIVE-018 | FR-AUTH-003 | same managed identity reauth | duplicate/lost registry/history/groups/config | identity matches and M02 records persist |
| OLL-LIVE-019 | FR-AUTH-001/003 | natural/approved wrong-account case | mismatch relinks target | wrong-account terminal state; otherwise Blocked |
| OLL-LIVE-020 | FR-AUTH-005 | default profile plus allowed read/managed flow | default provider state changes | reviewed pre/post checks prove unchanged |
| OLL-LIVE-021 | FR-STATE-001/002/004 | natural provider wait/activity/error signal if safely exposed | missing/ambiguous evidence becomes definitive state or possible stall | typed certainty and wait exclusion evidence reconcile; otherwise Blocked |

The owner performs every interactive auth and authoritative comparison. No one intentionally exhausts credits, revokes credentials, alters a budget, switches a live default profile, generates model requests, unloads models, or disrupts work solely to satisfy a test.

### 9.8 Architecture, security, operations, performance, docs, and dependency scenarios

| Test ID | Layer | Requirement | Initial Red expected | Green/pass condition |
|---|---|---|---|---|
| OLL-ARCH-001 | architecture | NFR-ARCH-001 | A03 imports module/provider/platform internals | import boundary permits approved contracts/ports only |
| OLL-ARCH-002 | public surface | FR-SAFE-002 | generation/control/proxy/routing method exists | surface contains monitoring and separately gated reauth only |
| OLL-ARCH-003 | contract | NFR-ARCH-002 | adapter emits raw dict/domain decision | exact M05/M06 input types only |
| OLL-ARCH-004 | compatibility | NFR-COMP-001 | protocol/source/schema/version metadata differs | manifest and contracts match approvals |
| OLL-ARCH-005 | composition | NFR-RES-001 | duplicate/lane failure disables unrelated adapters | static registration/failure isolation passes |
| OLL-SEC-001 | security | FR-AUTH-004 | credential/password/code parameter exists | no credential/OTP/MFA/recovery input/retention path |
| OLL-SEC-002 | security/live | FR-AUTH-005 | protected/unknown profile reaches external flow | rejected before I/O |
| OLL-SEC-003 | network/subprocess | NFR-SEC-001 | secret appears in argument/header/log/result | credential remains inside owning access port |
| OLL-SEC-004 | security/live | FR-AUTH-005 | default profile changes after allowed operations | real no-change check passes |
| OLL-SEC-005 | privacy | NFR-PRIV-001 | contract/schema admits request/response/prompt/tool/source | prohibited categories absent and rejected |
| OLL-SEC-006 | privacy/live | AC-PROC-004 | DB/WAL/log/event/API/UI/export/backup/evidence contains prohibited data | full artifact scan passes |
| OLL-SEC-007 | observability | NFR-OBS-001 | raw/free-form external error is logged | bounded safe codes and correlation only |
| OLL-SEC-008 | diagnostics | NFR-SEC-001 | response body/path/metric/account value appears | allowlisted version/outcome summary only |
| OLL-SEC-009 | filesystem | NFR-SEC-001 | path/type/symlink/size/time bound can be bypassed | production safe-file boundary enforces all bounds |
| OLL-SEC-010 | local service | FR-SAFE-002 | monitoring route generates/manages model or service | route/method absence and real side-effect check pass |
| OLL-SEC-011 | process | FR-SAFE-002 | adapter can signal/attach/restart/kill/input/route | static and live no-control proof passes |
| OLL-SEC-012 | privacy/network | NFR-PRIV-002 | analytics/crash reporting/unapproved host occurs | no external product telemetry or host |
| OLL-OPS-001 | resilience | AC-OPS-003 | real A03 lane failure takes down other lanes/API/UI | unrelated paths remain available |
| OLL-OPS-002 | health | FR-OPS-002/006 | health calls provider or conflates lanes | query-only truthful lane/version state |
| OLL-OPS-003 | diagnostics | NFR-OBS-001 | diagnostics contain raw values/paths/identity | allowlisted safe summary only |
| OLL-OPS-004 | platform | NFR-PLAT-001 | Linux evidence generalized to macOS | Linux passes; macOS separately Passed or Blocked |
| OLL-OPS-005 | automation | AC-TEST-001/006 | aggregate green hides non-Passed live scenarios | canonical report exposes R/G/R and all statuses |
| OLL-OPS-006 | vertical integration | AC-HIST-001 | real result fails before M05/M06 history/UI | production DB/HTTP/built UI path succeeds without seed |
| OLL-PERF-001 | performance | NFR-PERF-001 | intended-account polling exceeds approved request/rate/cost | real measurements remain within synchronized budget |
| OLL-PERF-002 | performance | NFR-PERF-001 | 2–4 process/model observation is unbounded/slow | bounded real collection meets synchronized limit |
| OLL-PERF-003 | scale | NFR-PERF-001 | bounded 100-account catalog policy requires redesign | AgentMonitor-owned descriptor load plus real source bounds pass without fake provider claims |
| OLL-DOC-001 | documentation | NFR-DOC-001 | links/IDs/contracts/statuses are stale | canonical documentation/planning validation passes |
| OLL-DOC-002 | documentation | AC-V1-006 | operations/limitations/compatibility/reauth docs incomplete | verified procedures and all limitations are current |
| OLL-DEP-001 | dependency | NFR-LIC-001 | undeclared/unreviewed package is required | exact direct/transitive graph passes admission and lock |
| OLL-DEP-002 | dependency | NFR-LIC-001 | SBOM/notices/license/security output omits dependency | complete graph and artifacts pass review |

### 9.9 Red, Green, Refactor evidence record

Every increment handoff records:

- requirement/AC, plan/increment, adapter/protocol/lane/capability/source/parser/extension versions;
- exact scenario ID and actual boundary exercised;
- Red command, UTC timestamp, expected behavioral failure, actual sanitized failure, and worktree reference;
- minimum production change reference;
- Green command/result against the same boundary;
- post-refactor command/result and broader relevant suite;
- real provider/service/account/workspace/platform aliases, versions, time, and owner acknowledgement without sensitive identity;
- Passed, Failed, Blocked, and Not Run rows separately;
- side-effect, default-profile, provider-state, content/secret, and request/rate/cost reconciliation;
- dependency/license, operations, migration, security/privacy, and docs impact.

The canonical command and evidence format are foundation/integration contracts. No narrower command may support a broader completion claim.

## 10. Implementation increments

Implementation begins only after every applicable Definition-of-Ready item is checked and root assigns exact paths/contracts.

| Increment | Exclusive owned scope | Failing tests first | Minimum Green production change | Refactor/docs and exit evidence |
|---|---|---|---|---|
| OLL-I00 | accepted evidence and contract lock | OLL-DOC-001, OLL-ARCH-004 | no production change; bind M0 rows to exact synchronized contracts | signed packet, shared path allocation, planning gate |
| OLL-I01 | adapter package/descriptor/manifest skeleton | OLL-PURE-001/013, OLL-ARCH-001/005 | statically admitted A03 descriptor with all lanes non-invokable until approved | boundary docs and real M03 registration evidence |
| OLL-I02 | source/version/parser registry | OLL-PURE-002..005, OLL-SVC-002/003/010 | exact approved descriptors and fail-closed version resolution | compatibility docs and live current tuple |
| OLL-I03 | typed resource/completeness mapping | OLL-PURE-006/014/015, OLL-MAP-001..012 | pure closed mapping into synchronized M05/M06 types | mutation/contract evidence; no provider claim |
| OLL-I04 | installation and service discovery | OLL-SVC-001..004 | approved read-only component/version discovery | real installation evidence and no service mutation |
| OLL-I05 | local model/runtime lane | OLL-SVC-005..012, OLL-LIVE-009..012 | approved endpoint/tool mapping to M06 inputs | real 2–4 process/model evidence and privacy scan |
| OLL-I06 | local metadata lane, only if Supported | OLL-FS-001..009 | approved bounded file source/parser or explicit absent lane | real filesystem evidence; no fixture |
| OLL-I07 | cloud identity/auth-health lane | OLL-NET-001, OLL-LIVE-002..004 | candidate/identity/auth observation only; no reauth | both identity rows and default-state checks |
| OLL-I08 | cloud subscription lane | OLL-MAP-001..004, OLL-LIVE-005/006 | exact quota/credit mapping to CTR-CAP-001 | real authoritative reconciliation |
| OLL-I09 | API billing lane, only if Supported | OLL-NET-002..010, OLL-LIVE-007/008 | approved official usage/cost/budget mappings | real API reconciliation/request budget |
| OLL-I10 | correlation lane | OLL-PURE-007..009, OLL-SVC-012, OLL-LIVE-013..015 | approved evidence mapping only | real Strong/ambiguous evidence statuses |
| OLL-I11 | managed reauth, separately authorized | OLL-LIVE-017..020, OLL-SEC-001..004 | protected-profile precondition and official managed flow | owner-countersigned live flow; rare mismatch may remain Blocked |
| OLL-I12 | extensions/diagnostics | OLL-SEC-005..012, OLL-OPS-002/003 | approved extension schemas and bounded health | privacy/artifact/network/no-control scans |
| OLL-I13 | composition and M03 conformance | OLL-LIVE-001, OLL-ARCH-003..005 | root-owned static wiring plus real adapter conformance | exact manifest/conformance matrix |
| OLL-I14 | vertical collection/history/UI | OLL-OPS-001/005/006 | production M04 -> A03 -> M05/M06 commit flow | real DB/HTTP/browser/history/failure evidence |
| OLL-I15 | performance/platform/docs/dependency hardening | OLL-PERF-001..003, OLL-OPS-004, OLL-DOC/DEP | approved bounds, automation, docs, dependency proof | full handoff with every non-Passed row |

### 10.1 Ordering and gates

- OLL-I00 is serial and approval-blocking.
- OLL-I01–I03 start only after the shared protocol and typed consumer contracts freeze.
- OLL-I04 must establish independent client/service compatibility before any version-sensitive local lane.
- OLL-I05 and OLL-I06 are separate: local endpoints do not authorize filesystem/log access.
- OLL-I07 precedes OLL-I08 and OLL-I11; read-only identity/auth health is not coupled to auth mutation.
- OLL-I08 and OLL-I09 remain separate resource paths even when the provider presents one UI.
- OLL-I09 cannot be built merely from per-response metadata if account-level API coverage is required.
- OLL-I11 needs a separate explicit state-changing task after plan approval and isolated-profile evidence.
- OLL-I12 cannot add an extension that M05/M06/security has not approved.
- OLL-I13 composition/shared files remain integration-steward owned.
- OLL-I14 waits for M04/M05/M06 and uses no fake consumer or seeded row.
- OLL-I15 cannot broaden the verified provider tuple from performance evidence.

### 10.2 Parallel-development isolation

After synchronization, independent lane agents can work only in non-overlapping directories with exact M0 rows, contracts, tests, and safe-boundary grants:

| Work packet | Exclusive path | Consumes | Publishes |
|---|---|---|---|
| A03-LOCAL | `ollama/local_service/**` and matching tests | M03, M06 inputs, safe local HTTP | local model/runtime ports |
| A03-FILES | `ollama/local_metadata/**` and matching tests | M03, M06 inputs, safe filesystem | local metadata parser/port if Supported |
| A03-CLOUD | `ollama/cloud_identity/**`, `cloud_subscription/**` and matching tests | M03, M02 target, CTR-CAP-001, safe HTTP/profile | identity/auth/quota ports |
| A03-API | `ollama/api_billing/**` and matching tests | M03, CTR-CAP-002, safe HTTP/profile | API usage/cost/budget ports |
| A03-CORR | `ollama/correlation/**` and matching tests | M03, M06 correlation inputs | evidence only |
| A03-AUTH | `ollama/authentication/**` and matching tests | M03/M02 profile contracts | auth health; reauth only separately authorized |
| A03-INTEGRATE | `adapter.py`, `manifest.py`, extension registry, root-allocated composition | every lane output | one immutable A03 registration set |

Lane agents do not edit shared contracts, manifest aggregation, composition, dependency manifests, central configuration, migration chains, generated artifacts, another lane, or another module. A contract gap stops the packet; it cannot be bypassed with duplicated DTOs, raw dictionaries, direct table reads, or private imports.

### 10.3 Implementation stop and escalation points

Stop and notify root when:

- M0 evidence is absent, contradictory, stale, or narrower than the planned capability;
- current source/version/plan/account/workspace/role/platform behavior differs from its approved tuple;
- a private/browser/cookie/proxy/interception source is needed;
- a command/request prompts login, install, update, pull, generate, purchase, budget, model, profile, consent, or configuration change;
- a local endpoint could generate content, manage models, mutate state, or reach an unapproved host;
- profile protection/isolation is uncertain;
- parsing would materialize content, credentials, arbitrary logs/paths/environments, or unclassified data;
- subscription/API/local resource identity or process/session/account correlation would be guessed;
- per-response data is being proposed as complete historical/account usage;
- M05/M06 cannot represent a proven safe concept;
- daemon/model/process control, proxy insertion, routing, credential switching, or request generation is requested;
- a dependency lacks admission or has unacceptable license/telemetry/install/provenance behavior;
- secret/content/raw provider value appears in code, test, log, DB, artifact, evidence, screenshot, or chat;
- another owner controls the path/contract/shared file or concurrent edits overlap.

## 11. Documentation outputs

Approved implementation must create/update, through assigned owners:

- `docs/adapters/ollama.md`: outcome, lanes, boundaries, supported tuples, failures, health, limitations, and extension points;
- separate capability matrices for Ollama local product/runtime, cloud subscription/identity, and Ollama API billing;
- safe operation/source registry with official citation, operation ID, host/method/path or command/file class, bounds, side effects, versions, and evidence reference—never secret values or unverified command examples;
- independent client/service/API/parser compatibility matrix and re-verification trigger;
- account/team/organization/workspace/resource relationship map with Unknown/owner-confirmation semantics;
- closed local/API field allowlists and request/response/content exclusion proof;
- provider-extension schemas and consumer opt-ins;
- real matrix for both intended identity aliases and representative 2–4 process/model cases;
- test-evidence matrix with every Passed/Failed/Blocked/Not Run status;
- install/discovery, enrollment, refresh, version drift, diagnostics, managed reauth, source disable/rollback, and incident runbooks using verified commands only;
- configuration registry entries after approval;
- dependency admission, lockfile, SBOM, notices, and scan updates if any package is added;
- threat/data-flow updates for managed reauth, remote/custom local endpoints, or any Experimental source;
- central contract/traceability/risk/planning/release updates through root ownership;
- ADR before any private/browser source, new secret store, default-profile policy change, process/environment access, traffic proxying, control behavior, or breaking contract.

Documentation never contains real account identity, credentials, local absolute paths, dynamic quota/spend/token/model values, raw provider output, sensitive screenshots, request/response/prompt/tool/source content, or arbitrary environment values.

## 12. Dependency and license impact

### 12.1 Initial posture

No dependency is approved, installed, or added by this Draft.

A03 should initially use:

- admitted standard-library parsing/URL primitives where sufficient;
- centrally approved M03/common/M05/M06 contracts;
- centrally approved safe filesystem/subprocess/network/profile/cancellation ports;
- the real installed Ollama client/service as an external boundary, never a bundled test dependency.

No Ollama SDK, HTTP/retry library, semantic-version library, JSON streaming library, GPU/process library, filesystem watcher, browser driver, keyring wrapper, telemetry client, CLI wrapper, or provider binary is selected here. Direct documented HTTP versus an official SDK is decided only after M0 and full dependency admission. Convenience is not necessity.

### 12.2 Required admission record

Before any package/version enters a manifest, lockfile, import, or test toolchain, record:

- exact purpose and why standard library/current admitted ports are insufficient;
- canonical upstream/package identity and license from the upstream license file;
- complete direct/transitive dependency and license inventory;
- maintenance activity, ownership, release cadence, security policy/advisories, provenance, and compromise history;
- supported Python/platform versions, native/binary components, install/build scripts, and system dependencies;
- network, analytics, telemetry, update, and credential behavior;
- exact pin/integrity/update/removal strategy;
- performance/size/runtime effect and failure isolation;
- alternatives and removal cost;
- SBOM and third-party notices impact;
- reviewer, decision, date, and recheck trigger.

Copyleft, custom, unclear, source-available, telemetry-bearing, opaque binary, or risky install behavior requires explicit owner decision. A package name in this plan is never approval.

## 13. Risks, unresolved decisions, and stop conditions

### 13.1 Risks

| ID | Risk | Likelihood/impact | Mitigation/evidence | Owner/status |
|---|---|---|---|---|
| A03-R01 / R-001 | no stable official machine-readable subscription or API billing source | High/Critical | official-first M0; Unsupported is valid | M0/A03 Open |
| A03-R02 / R-002 | client, daemon, API, or file schema changes independently | High/Major | separate versions, exact parser registry, fail unverified | A03/M03 Open |
| A03-R03 / R-003 | local runtime cannot correlate with cloud/API identity | High/Critical | Strong-only rules; unresolved/manual confirmation | A03/M02/M06 Open |
| A03-R04 / R-004 | monitoring modifies default profile, daemon, or model state | Low/Critical | pre-I/O safety, read-only sources, real pre/post checks | A03/security Open |
| A03-R05 / R-005 | request/response/model/log content or secret is captured | Medium/Critical | source exclusion, preventive allowlist, bounds, scans | A03/security Open |
| A03-R06 / R-006 | cloud/API collection exceeds rate/cost or local service load budget | Medium/Major | M0 constraints, M04 budgets, no autonomous retry/generation | A03/M04 Open |
| A03-R07 / R-007 | stale/partial local/cloud value appears current/complete | Medium/Critical | completeness/freshness/provenance and no cache fallback | A03/M05/M06 Open |
| A03-R08 / R-008 | incompatible pools/windows create false total/forecast | Medium/Major | strict lane/pool identity and M05 aggregation policy | A03/M05 Open |
| A03-R09 / R-009 | rare auth/exhaustion/outage/rate states unavailable | High/Major | visible Blocked; no manufacturing | Test/owner Accepted constraint |
| A03-R10 / R-010 | live tests consume credits, load models, or interrupt work | Medium/Major | zero-generation default, owner schedule, stop budget | Live operator Open |
| A03-R11 / R-014 | subscription/API/local resources double count | Medium/Major | separate resource IDs/DTO lanes/relationship proof | M02/M05/A03 Open |
| A03-R12 / R-015 | PID/model-process reuse or wrapper ambiguity misattributes runtime | Medium/Major | A04 PID/start tuple and unresolved conflicts | A04/M06/A03 Open |
| A03-R13 / R-018 | SDK/HTTP/GPU dependency introduces license or supply-chain risk | Medium/Critical | no dependency before admission | Dependency reviewer Open |
| A03-R14 / R-021 | reauth reaches wrong identity or loses history | Medium/Critical | expected identity, mismatch stop, M02 reconciliation | A03/M02 Open |
| A03-R15 / R-024 | valuable data requires private/browser endpoint or interception | Medium/Critical | Deferred/Unsupported; ADR/threat/approval first | Security/product Open |
| A03-R16 | local service endpoint can trigger generation or model-state change | Medium/Critical | exact read-only route/method proof and live side-effect reconciliation | A03/security Open |
| A03-R17 | per-response metadata undercounts other clients but appears account-complete | High/Critical | explicit request scope/completeness; no proxy workaround | A03/M05 Open |
| A03-R18 | remote/custom Ollama endpoint expands trust/credential exposure | Medium/Critical | separate trust tuple and host/credential isolation | A03/security Open |
| A03-R19 | current/legacy plan or workspace semantics change | High/Major | exact plan/version/date scope and M0 re-verification | M0/M02/A03 Open |
| A03-R20 | local CPU/RAM/GPU/model metrics overlap or have unclear units | High/Major | M0 semantics; unverified/Unknown rather than aggregation | A03/M06 Open |

### 13.2 Approval-blocking synchronization decisions

1. Accept M0 Ollama product/local, Ollama API, and Linux handoffs with all terminal statuses/evidence references.
2. Freeze provider-product and A03 registration boundaries for local, cloud subscription, and supported API billing surfaces.
3. Freeze Supported/Experimental/Deferred/Unsupported tuples at exact version/plan/account/workspace/role/platform/source scope.
4. Freeze client, daemon/service, API, parser, and local-format version detection/comparison rules.
5. Freeze source IDs/classes/chains, operations, hosts/methods/routes, commands, paths/files/fields, bounds, side effects, and citations.
6. Freeze personal/team/organization/workspace/project/API-billing identity semantics and owner-confirmation boundary.
7. Freeze current/legacy plan classification, native quota/credit windows, units, reset/renewal, precision, completeness, and authoritative comparison tolerance.
8. Decide official API usage/cost/budget availability, least-privilege roles, dimensions, buckets, pagination, currency, latency, rates, costs, limits, credits, and reset semantics.
9. Decide exact per-response coverage and explicitly document inability to observe other clients without an official aggregate source.
10. Freeze local catalog, load/runtime, queue/concurrency, CPU/RAM/GPU, request/token metrics, units, sampling, overlap, freshness, and side-effect semantics.
11. Freeze local metadata/log eligibility, exact field allowlist, content-prevention proof, parser versions, and path safety rules.
12. Freeze process/model/session hierarchy and correlation evidence accepted by M06; OS ancestry alone cannot become provider hierarchy.
13. Freeze narrow M02 target/profile/protection/expected-identity/account-resource contracts.
14. Freeze CTR-PROV-001..008, CTR-COMMON-004, and provider target/context bounds.
15. Freeze CTR-CAP-001/002 input versions, exact fields, dimensions, cardinalities, extensions, and completeness.
16. Freeze CTR-RUN input, relationship, correlation, and model/runtime representation versions/bounds.
17. Allocate safe local HTTP, provider HTTP, filesystem, subprocess, cancellation, profile access, and redaction ports and owners.
18. Freeze M04 deadlines, page/item/request/rate/cost/concurrency budgets, retry/no-retry, source admission, and commit routing.
19. Decide managed reauth coordinator, official flow, managed profile root, lifecycle, expiry/cancel/restart/idempotency/audit, and API/UI handoff.
20. Approve each extension schema and exact M05/M06/API/UI consumer; none is implied.
21. Allocate configuration categories/keys/owners/defaults/reload behavior without allowing arbitrary hosts or weakened safety.
22. Freeze component-health/readiness effects and diagnostic disclosure.
23. Select test mutation/performance budgets and canonical automation selectors, including status separation.
24. Complete dependency/license/security review and lock exact graph.
25. Allocate implementation/shared/generated/composition paths with no parallel conflict.
26. Confirm live coverage for both intended identities and 2–4 natural process/model cases, or mark each unavailable case Blocked.
27. Update the central contract register and CS review; create ADRs for any deviation, private source, new secret model, proxy, process access, or breaking change.

No implementation agent may privately decide an item that allows materially different implementations.

### 13.3 M0 handoff acceptance criteria

A03 rejects an M0 handoff when any enabled lane lacks:

- exact product surface, client/service/API/parser version, plan/account/workspace/resource class, role, platform, and source class;
- official citation and scoped real evidence;
- reviewed operation/host/method/route/command/path/file/field allowlist;
- content/credential/request-body/response-body/prohibited-field prevention analysis;
- units, windows, intervals, timestamps, resets, precision, freshness, completeness, and latency semantics;
- identity/resource/process/model/session scope, relation, lifetime/collision, and correlation strength;
- timeout, byte/item/page/request/rate/cost/concurrency and retry constraints;
- side-effect/default-profile/daemon/model/running-agent reconciliation;
- parser/version compatibility signal and drift behavior;
- capability decision and every Failed/Blocked/Not Run scenario;
- extension need and explicit consumer mapping.

Unknown fields block their lane or field; they do not block independent supported lanes or an honest Unsupported decision.

### 13.4 Stop conditions during implementation/live work

The section 10.3 and security incident conditions are mandatory. In addition, stop when local/cloud/API terminology would cause two resource pools to share one identifier, a test needs request generation or model-state manipulation, a real source exposes content despite the approved field review, or the owner cannot confirm which identity/workspace/billing scope is being observed.

## 14. Delivery, compatibility, rollback, and recovery

### 14.1 Delivery order

1. Complete the applicable M0 technical evidence and validate A03 handoffs;
   detached review records are advisory and do not block local execution.
2. Synchronize section 13.2 contracts, shared ports, paths, and automation; approve this plan.
3. Implement pure manifest/source/version/resource-separation policy through TDD.
4. Implement installation and one lowest-side-effect Supported local read-only lane; complete real conformance.
5. Add local runtime, local metadata, cloud identity, subscription, and API lanes independently, each with its own live gate.
6. Implement read-only auth health before any managed reauth.
7. Implement managed reauth only under a separately authorized task after isolated-profile proof.
8. Integrate M04/M05/M06/M02 and static composition through root-owned changes.
9. Run real DB/API/browser/history/failure-isolation/operations evidence.
10. Complete security/privacy/dependency/license/docs/automation review and implementation handoff.

### 14.2 Compatibility and feature exposure

Every lane defaults non-invokable until its exact manifest tuple is Approved and required real verification passes. Unknown/new client, daemon, API, parser, plan, role, or platform disables only the affected version-sensitive source/capability. Unsupported and Blocked remain visible.

No feature/configuration flag may enable a host, route, operation, path, field, version, profile mutation, proxy behavior, or extension beyond the approved manifest. Experimental behavior requires a separate explicit scoped grant and is never fallback.

Compatible changes may add an optional bounded field with safe absence after producer/consumer review. Changes to unit, scope, resource relationship, completeness, identity, privacy, source class, method side effect, version interpretation, or extension meaning require a new major and possibly an ADR.

### 14.3 Rollback and recovery

- Disable/remove the affected A03 lane from static composition using the approved release rollback; do not delete M02/M05/M06 history.
- Revert to a prior adapter only if M03 protocol/schema/extension compatibility permits it.
- Mark latest observations stale/unverified through owning domain behavior; never insert cached/fake replacement facts.
- Preserve compatibility/evidence/history owned by other modules.
- Expire uncertain active reauth work unless the synchronized coordinator proves safe resumption.
- Do not restart or repair the Ollama service, reload models, rewrite provider state, or modify a profile as adapter rollback.
- Re-run manifest/version/host/profile/content/default-state checks before re-enabling.
- A contract-breaking rollback follows its ADR/consumer/migration plan; A03 has no database downgrade.

### 14.4 Post-delivery verification

- exact adapter/protocol/manifest/lane/source/parser/client/service/API/extension versions are visible and compatible;
- only Approved exact tuples are enabled;
- local runtime, cloud subscription, and API billing remain distinct in registry, capacity, runtime, API, and UI;
- quota/API/runtime values retain identity/scope/unit/time/precision/confidence/freshness/completeness;
- per-response data remains request-scoped and no unobserved-client total is implied;
- unresolved identity remains unresolved and owner confirmation is explicit;
- no default profile, daemon/model, provider account/budget/credential, or running agent changed;
- no provider-specific code leaked into M03/M05/M06;
- no secret/content/raw provider data exists in logs, DB/WAL, event, API, UI, export, backup, test, build, diagnostics, evidence, or docs;
- other adapters/lanes/API/UI remain available when one A03 lane fails;
- both intended identity rows and 2–4 natural process/model rows have visible status;
- canonical planning/test/quality/docs/dependency/live gates report exact scope and exit status.

### 14.5 Implementation handoff packet

The future handoff must name requirement/AC IDs; plan/adapter/protocol/capability/source/parser/extension versions; exact files; accepted M0 rows; Red/Green/refactor evidence; real identity aliases and client/service/API/platform versions; authoritative reconciliation and owner acknowledgement; side-effect/default-profile/daemon/model/process checks; every Failed/Blocked/Not Run scenario; security/privacy/content/secret scans; dependency/license/SBOM/notices impact; configuration/operations/docs impact; migration statement (`none` for A03-owned persistence); rollback/known limitations; and exact next integration command/step.

## 15. Definition of Ready for implementation

- [ ] Ollama product/local, Ollama API, and Linux technical handoff packets
      pass section 13.3; detached reviews remain advisory.
- [ ] Exact capability decisions/tuples are frozen; Unknown behavior is not delegated to implementation guesswork.
- [ ] Local service/model/runtime, cloud subscription, and API billing lanes/resource identities are distinct and approved.
- [ ] This plan's scope, non-goals, paths, lane ownership, and API-adapter registration choice are approved.
- [ ] CTR-COMMON, CTR-REG, CTR-PROV-001..008, CTR-COL, CTR-CAP, CTR-RUN, CTR-PLAT, safe-execution, configuration, and evidence contracts are Synchronized/Approved.
- [ ] Every host/method/route, command, path/file/field, parser, version rule, side effect, timeout/byte/item/page/request/rate/cost/concurrency bound, and source chain is approved by stable operation/source ID.
- [ ] Request/response/content/credential prevention and data-flow review passes for every enabled source.
- [ ] Default-profile protection and managed-profile isolation are evidence-backed; reauth remains separately authorized.
- [ ] M05/M06 typed outputs and every extension/schema/bound/consumer opt-in are approved.
- [ ] Requirements/AC/test IDs and each expected behavioral Red are reviewed.
- [ ] Both intended account/workspace aliases, current tools/services/platforms, and 2–4 naturally available process/model cases are scheduled with the owner.
- [ ] Canonical fail-closed A03 test/quality/docs/live selectors exist and are tested for the boundary they claim.
- [ ] Security/privacy/threat/default-profile/provider-state/no-control/no-proxy reviews pass.
- [ ] Every dependency/version/lock/transitive license/security/provenance record is approved.
- [ ] Configuration, health, diagnostics, operator procedures, rollback, and incident handling are assigned.
- [ ] Implementation, shared, composition, generated, and documentation paths are allocated without agent conflict.
- [ ] Planning registry/catalog and synchronization review account for this exact plan/version.
- [ ] `python3 tools/planning/validate_plans.py --stage synchronized` passes for the complete real checkout, not merely A03.
- [ ] No unresolved decision permits materially different implementation.
- [ ] Owner/root/contracts/security/test/live/operations/dependency reviewers approve the plan.

Until every applicable item is checked, A03 is not implementation-ready. Plan approval alone does not authorize provider access, authentication, dependency installation, implementation, deployment, or live execution.

## 16. Approval record

| Role | Decision | Conditions | Date |
|---|---|---|---|
| Owner | Pending | intended identities, live resources, and interaction model |  |
| Root/integration steward | Pending | contract synchronization, automation, and path allocation |  |
| M02 Registry owner | Pending | identity/profile/resource/workspace semantics |  |
| M03 Provider-system owner | Pending | protocol/conformance/source/extension semantics |  |
| M04 Collection owner | Pending | deadlines/rates/costs/commit/failure policy |  |
| M05 Capacity owner | Pending | quota/API resource/input mappings and extensions |  |
| M06 Runtime owner | Pending | model/runtime/session/correlation inputs and privacy |  |
| A04-LINUX owner | Pending | process-reference/source boundary |  |
| M08/operations owner | Pending | health/diagnostics/recovery |  |
| Security/privacy reviewer | Pending | hosts, content prevention, profile/state safety, incident controls |  |
| Test-integrity/live reviewer | Pending | no-double and real-boundary matrix |  |
| Dependency/license reviewer | Pending | exact admitted graph |  |

Implementation remains prohibited while Status is Draft, M0 is incomplete, contracts are unsynchronized, the canonical gate is red/absent, or any Definition-of-Ready item is unchecked.
