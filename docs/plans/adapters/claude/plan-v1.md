# Module plan: A01 — Claude provider adapter

- Plan ID: `PLAN-A01`
- Status: **Draft — M0 evidence and contract synchronization required; implementation is not authorized**
- Plan version: `0.2.1-draft`
- Proposed adapter contract bundle: `claude-adapter.v1`
- Proposed provider protocol: CTR-PROV-001 `ProviderAdapterV1` protocol `1.0`, subject to CS approval
- Primary owner: A01 Claude provider adapter
- Reviewers: integration, M02 Registry, M03 Provider system, M04 Collection control, M05 Capacity, M06 Runtime observation, A04-LINUX, M08 Operations, security/privacy, test-integrity, dependency/license
- Requirements: FR-ACC-005, FR-ACC-006, FR-AUTH-001..006, FR-QUOTA-001..006, FR-BUDGET-001..006 for the A01-owned Anthropic API lane, FR-DISC-001, FR-DISC-003, FR-DISC-004, FR-DISC-006, FR-DISC-008, FR-COL-004..008, FR-SAFE-001, FR-SAFE-002; supporting NFR-ARCH-001/002, NFR-TEST-001/002, NFR-SEC-001, NFR-PRIV-001/002, NFR-DOC-001, NFR-LIC-001, NFR-PLAT-001, NFR-PERF-001, NFR-RES-001, NFR-OBS-001, NFR-COMP-001
- Acceptance criteria contribution: AC-V1-001/002/005/006/007/008, AC-LIVE-001, AC-LIVE-004..007, AC-PROC-001..004 and the Claude evidence contribution to AC-PROC-005, AC-HIST-001, AC-OPS-003/006, AC-TEST-001..006
- Required predecessors: accepted M0 Claude and Anthropic API handoffs; synchronized CTR-COMMON, CTR-REG, CTR-PROV, CTR-COL, CTR-CAP, CTR-RUN, safe-execution, configuration, and evidence contracts
- Target milestone: M2 provider integration after M03 protocol approval
- Approved by/date: pending

## CS-1 alignment addendum — contract baseline 0.2.0

This addendum is normative for CS-1 and supersedes conditional ownership or
private-contract wording elsewhere in this Draft. The machine-readable
[contract baseline](../../contract-baseline.toml) and
[parallel ownership manifest](../../parallel-ownership.toml) remain unapproved;
therefore this alignment does not authorize implementation or live access.

- A01 owns the Claude product/subscription/local adapter and the Anthropic API
  integration lane. Milestone 0 decides each exact capability's maturity
  (`Supported`, `Experimental`, `Deferred`, or `Unsupported`), never whether
  Anthropic work silently moves to another adapter.
- A01 implements M03-owned `CTR-PROV-001..008`; it does not redefine those
  contracts. Provider extensions use only the M03-governed namespace
  `backend/src/agentmonitor/contracts/providers/claude/<capability>/v1/**`.
  Domain modules cannot import
  A01 packages, and A01 cannot import their internals or persistence adapters.
- A01 consumes `CTR-COMMON-001/002/004/007`, `CTR-CONFIG-001`,
  `CTR-FND-003/004/008`, `CTR-BOUNDARY-001..003`, and the typed REG/COL/CAP/RUN
  ports enumerated below. `CTR-COMMON-007` prevents every absent or uncertain
  provider field from becoming zero/current. Provider HTTP uses M03-owned
  `CTR-BOUNDARY-002`; CLI and approved-root reads use FND-owned
  `CTR-BOUNDARY-001/003`.
- A01 implements the M08-owned leaf health port `CTR-OPS-006`; it reports safe
  component facts but never aggregates application readiness. It creates no
  durable domain event directly; any durable event uses `CTR-COMMON-006` plus
  `CTR-EVT-001` through its owning domain workflow.
- `reauthentication_required` is the normalized provider-auth state.
  `provider_reauthentication_required` is the API/UI problem/flow mapping;
  `dashboard_authentication_required` is never emitted for a Claude or
  Anthropic provider failure.
- After M0 and contract approval, isolated implementation lanes may proceed in
  parallel for `subscription`, `local_state`, `anthropic_api`, and
  provider-extension code under
  `backend/src/agentmonitor/adapters/providers/claude/**`. They share no live
  alias/profile concurrently, write no common contract/generated/migration
  artifact, and enter composition only through the allocated integration writer.

All provider compatibility and account claims require current real Claude or
Anthropic boundaries. Constructed pure values cannot establish provider
support; Blocked and Not Run remain non-Passed.

## 0. Authority, evidence state, and planning rule

This document is the independent implementation-plan artifact for A01. It authorizes planning only. It does not authorize provider documentation research, provider/account access, command execution, filesystem inspection, API requests, login, `/login`, profile creation, reauthentication, dependency installation, production code, test execution, or edits outside the assigned plan.

Milestone 0 has not executed. Therefore this plan makes no assertion about:

- whether Claude exposes a supported machine-readable subscription usage source;
- whether `/usage` or another surface is invocable non-interactively or safely pollable;
- the names, locations, formats, or meanings of Claude local files;
- any installed Claude version, output schema, plan class, limit window, unit, reset, or freshness;
- safe account, profile, session, process, model, token, context, activity, hierarchy, error, or wait-state fields;
- `CLAUDE_CONFIG_DIR` behavior or isolated-profile safety;
- current Anthropic usage, cost, budget, credit, role, endpoint, grouping, pagination, latency, or rate-limit behavior;
- whether any capability is Supported, Experimental, Deferred, or Unsupported.

Those facts enter A01 only through the accepted M0 packet identified by scenario IDs `M0-CLA-001..010`, applicable `M0-ANT-001..008`, `M0-LNX-001..013`, and their sanitized capability-matrix evidence. Unknown behavior remains Unknown and blocks only its dependent capability. A backlog entry, guessed command, remembered provider behavior, or structurally plausible schema cannot substitute for M0 evidence.

Every future behavior follows Red -> Green -> Refactor. External claims require the real production adapter and real current boundary. Pure tests prove only deterministic policy or transformation of an owner-approved sanitized structure; they never prove Claude compatibility.

## 1. Outcome and boundaries

### 1.1 Outcome

After approval and implementation, A01 is a statically admitted, failure-isolated adapter package that exposes only the Claude and Anthropic capabilities proven for exact provider-product/version/plan/credential/platform tuples. It maps safe provider observations into M03 envelopes and the exact typed inputs owned by M02, M05, and M06, without leaking provider behavior into domain modules.

The adapter succeeds when:

1. each manifest declaration is no broader than accepted M0 evidence;
2. subscription allowance, Anthropic API billing, local sessions, authentication, installation, and process correlation remain separate capability/resource lanes;
3. default profiles and running agents remain unchanged;
4. unsupported, unknown, unavailable, partial, stale, authentication-required, authorization-insufficient, rate-limited, invalid-data, and unverified-version states remain distinct;
5. raw provider bodies, stdout/stderr, files, arbitrary metadata, secrets, content, and personal identifiers cannot cross the adapter boundary;
6. M05 receives only its closed `Provider*InputV1` values and M06 receives only its closed runtime input values;
7. the adapter has no database ownership and no hidden cache presented as current;
8. every compatibility claim is verified with real owner-controlled accounts, current installed/provider versions, and sanitized evidence.

### 1.2 Capability lanes

The package is divided into independently enabled lanes. A failure or unsupported decision in one lane does not imply anything about another.

| Lane | Concern | Potential M03 capabilities | Typed consumer | Activation evidence |
|---|---|---|---|---|
| `CLA-INSTALL` | Claude executable/product discovery and version evidence | `installation.discovery`, `provider.diagnostics` | M02/M08 via CTR-PROV | M0-CLA-001/002/010 |
| `CLA-SUBSCRIPTION` | Claude subscription quota/usage windows | `subscription.quota` | M05 `ProviderQuotaInputV1` | M0-CLA-003/004/010 |
| `CLA-AUTH` | Claude profile identity and authentication health | `account.discovery`, `identity.verification`, `authentication.health` | M02 via CTR-PROV | M0-CLA-007/010 |
| `CLA-REAUTH` | Official owner-driven login/reauth for an AgentMonitor-managed isolated profile | `authentication.reauthenticate` | synchronized coordinator via CTR-PROV-007 | separate approved isolated-profile evidence following M0-CLA-009 and FR-AUTH-006 |
| `CLA-LOCAL` | allowlisted Claude local session/metric metadata | `local.session.discovery`, `local.session.metrics` | M06 closed input contracts | M0-CLA-005/006/010 and M0-LNX |
| `CLA-CORRELATION` | provider-session/account/process evidence mapping | `local.process.correlation` | M06 correlation evidence; M02 confirmation | M0-CLA-007..010 and M0-LNX-007/008 |
| `ANTHROPIC-API` | A01-owned Anthropic API usage/cost/budget/project data | `api.usage`, `api.cost`, `api.budget`, `project.discovery`, possibly `model.catalog` | M05/M02 typed inputs | M0-ANT-001..008 |

`ANTHROPIC-API` is an independently registered A01 sub-adapter. M0 may mark
individual capabilities Unsupported or Deferred, but the lane remains assigned
to A01 and is never treated as a Claude subscription source. The two resource
pools are never merged.

### 1.3 In scope

- Claude-specific implementation of approved CTR-PROV-001..008 capabilities.
- Exact manifest rows and source descriptors derived from accepted M0 decisions.
- Provider/version detection and compatibility checks for evidenced schemes only.
- Source-specific parsers/mappers with closed allowlists and bounded inputs.
- Official supported CLI invocation where M0 proves it read-only and suitable.
- Approved local metadata reads where M0 proves path/file/field safety.
- Approved Anthropic read-only API calls where M0 proves endpoint, role, scope, request budget, and schema.
- Account/profile/session identity evidence without guessing or persisting identity ownership.
- Authentication-health mapping and safe managed-profile reauthentication protocol implementation only after separate approval.
- Mapping subscription observations to M05 `ProviderQuotaInputV1`.
- Mapping API observations to M05 `ProviderUsageInputV1`, `ProviderCostInputV1`, or `ProviderBudgetInputV1`.
- Mapping local session facts to M06 `LocalSessionObservationInputV1`, `RuntimeMetricObservationInputV1`, `RuntimeObservationBatchV1`, and approved correlation evidence.
- Claude extension schemas containing only M0-approved bounded operational fields.
- Adapter health, bounded diagnostics, conformance, real-boundary tests, and operator documentation.

### 1.4 Out of scope

- Defining M03 protocol, M05 capacity meaning, M06 runtime state/stall logic, M02 account ownership, or M04 scheduling/retry policy.
- Database tables, Alembic migrations, repositories, outbox records, or durable adapter caches.
- Direct FastAPI routes, OpenAPI schemas, UI components, alerts, notification delivery, backup, restore, or deployment.
- Scraping, browser automation, cookies, traffic interception, private endpoints, or undocumented network calls.
- Reading prompts, responses, tools, source code, arbitrary command lines, terminal contents, process memory, arbitrary process environments, or raw unclassified provider data.
- Inspecting Linux processes directly; A04-LINUX owns OS observation and M06 owns process/session semantics.
- Modifying, copying, moving, logging out, or rewriting a default Claude profile.
- Starting `/login` against any profile until the managed-profile contract, isolated-profile evidence, and owner-controlled flow are separately approved.
- Switching credentials inside, sending input to, signaling, restarting, killing, pausing, attaching to, or routing a running agent.
- Generating model traffic merely to create billing, quota, error, or failure evidence.
- Combining Claude subscription allowance with Anthropic API budget or spend.
- Claiming all Claude plans, accounts, platforms, or versions behave like the observed sample.

### 1.5 Ownership and paths

Allowed future implementation paths, after an approved task packet:

```text
backend/src/agentmonitor/adapters/providers/claude/**
backend/tests/adapters/providers/claude/**
backend/tests/live/claude/**
docs/adapters/claude.md
docs/provider-capabilities/claude/**
backend/src/agentmonitor/contracts/providers/claude/<capability>/v1/**
docs/test-evidence/claude/**                 # sanitized records only, if allocated
```

Suggested internal isolation, subject to foundation naming approval:

```text
claude/
  adapter.py                # static M03 adapter facade and port routing
  manifest.py               # declarations built from approved capability records
  installation.py           # installation/version evidence mapping
  subscription/             # Claude subscription source/parsers/mapping
  authentication/           # auth-health and separately gated managed reauth
  local_sessions/           # approved provider-local metadata only
  correlation/              # safe evidence mapping, never account decisions
  anthropic_api/            # separately registered A01-owned API lane
  extensions/               # closed schema descriptors and mappers
  diagnostics.py            # safe bounded adapter health/details
```

Shared paths require root allocation and cannot be edited by the A01 agent unilaterally:

```text
backend/src/agentmonitor/composition/**
backend/src/agentmonitor/contracts/**
configuration registry
dependency manifests and lockfiles
generated OpenAPI/client artifacts
central capability, contract, traceability, risk, and evidence registries
```

A01 owns the semantic content of Claude extension schemas in its exact namespace,
but the integration steward remains the sole shared-file writer for each
allocated wave. A01 must not edit that namespace without a current allocation,
or edit/import internals from M02–M08, A02/A03/A04, P01/P02, persistence, or
deployment modules.

### 1.6 Allowed and forbidden dependencies

Allowed imports:

- Python standard library within the approved runtime baseline;
- approved CTR-COMMON primitives;
- approved M03 public protocol, outcome, source, context, and extension contracts;
- narrow approved M02 target/profile/installation/identity assertion contracts;
- M05-owned provider input DTO contracts;
- M06-owned local-session/metric/correlation input DTO contracts;
- approved safe filesystem, subprocess, HTTP, cancellation, time, redaction, and profile-reference ports;
- adapter-local pure types that do not escape A01.

Forbidden imports:

- M02–M08 internal/domain/application/persistence packages or tables;
- FastAPI, Starlette, React, UI, SQLAlchemy, Alembic, OS process APIs, or concrete platform adapters in A01 domain/mapping code;
- Codex/Ollama adapters;
- dynamic plugin loaders or arbitrary Python imports;
- an Anthropic SDK, HTTP/retry/subprocess/parser package, or provider binary wrapper until dependency admission and contract approval;
- shell execution, global environment mutation, unrestricted filesystem access, or generic JSON/raw payload tunnels.

## 2. Requirements and traceability

| Requirement/AC | A01 behavior | Contract | Planned scenarios | Evidence gate |
|---|---|---|---|---|
| FR-ACC-005 | Discover only evidenced Claude installation/profile/account candidates | CTR-PROV-002/005 | CLA-CLI-001..003, CLA-LIVE-001/002 | Real installed Claude and owner confirmation |
| FR-ACC-006; AC-PROC-003 | Emit evidence/confirmation-required, never guess account ownership | CTR-PROV-005; CTR-RUN-007 | CLA-PURE-006..008, CLA-LIVE-009/010 | Real ambiguous and provable cases |
| FR-AUTH-001 | Map only evidenced auth-health signals; preserve Unknown | CTR-PROV-006 | CLA-PURE-009/010, CLA-LIVE-003/011 | Real current profile/account state |
| FR-AUTH-002/003/006; AC-LIVE-006 | Managed-profile official reauth with identity preservation and wrong-account stop | CTR-PROV-007 plus M02 coordinator | CLA-LIVE-012..014 | Separate approved live owner flow; otherwise Blocked |
| FR-AUTH-004/005 | No credential parameters; protected/unknown default profile rejected before I/O | CTR-PROV-001/007 | CLA-SEC-001..004, CLA-LIVE-015 | Security review and real default-profile no-change check |
| FR-QUOTA-001/002/004/006 | Preserve every evidenced native Claude subscription window, unit, reset, source, precision, and field state | CTR-PROV-004; CTR-CAP-001 | CLA-PARSER-001..004, CLA-LIVE-004/005 | Real provider authoritative reconciliation |
| FR-QUOTA-003/005 | Supply exact inputs/provenance only; M05 owns health and forecast | CTR-CAP-001/003/007 | CLA-ARCH-003, CLA-LIVE-005 | Contract boundary review; M05 live path |
| FR-BUDGET-001..006 | In A01's Anthropic API lane, preserve exact native usage/cost/budget scope and money | CTR-CAP-002 | CLA-NET-001..008, CLA-LIVE-006/007 | Real approved organization/role/source |
| FR-DISC-001 | Contribute provider session identity without OS process inspection or workflow changes | CTR-PROV-001; CTR-RUN-002 | CLA-FS-001/002, CLA-LIVE-008 | Real running Claude sessions plus A04/M06 |
| FR-DISC-003/006; AC-PROC-004 | Parse only approved session/model/token/context/activity/error/hierarchy fields; no content | CTR-RUN-002/003 | CLA-PARSER-005..010, CLA-FS-003..008, CLA-SEC-005..008 | Real approved local source and artifact scan |
| FR-DISC-004 | Produce only approved correlation evidence | CTR-RUN-007 | CLA-PURE-006..008, CLA-FS-009, CLA-LIVE-009/010 | M0 rule plus owner review |
| FR-DISC-008 | Version parser/source/provider CLI in every local result | CTR-COMMON-004; CTR-PROV-003 | CLA-PURE-003..005, CLA-CLI-004, CLA-FS-010 | Unknown-version failure and real supported version |
| FR-COL-004 | Populate complete provenance, freshness, precision, confidence, and versions | CTR-COMMON-004 | CLA-PURE-001..005, CLA-ARCH-004 | Contract validation plus real results |
| FR-COL-005 | Return bounded sanitized duration/warnings/errors for M04 run recording | CTR-PROV-004 | CLA-CLI-005..008, CLA-NET-009/010 | Real boundary failure/timeout where available |
| FR-COL-006..008 | Explicit unsupported/unavailable/version/auth outcomes; no silent downgrade/cache/simulation | CTR-PROV-002..004 | CLA-PURE-001/002/011/012, CLA-LIVE-011 | Policy plus real capability matrix |
| FR-SAFE-001/002 | Read/refresh and separately authorized managed reauth only; no agent control/routing | Full A01 surface | CLA-ARCH-001/002, CLA-SEC-009/010 | Automated surface/import scan and live no-effect check |
| NFR-ARCH-001/002 | Provider logic isolated behind typed contracts | A01 bundle | CLA-ARCH-001..005 | Boundary and contract checks |
| NFR-TEST-001/002; AC-TEST-001/002/006 | Real-boundary TDD, no doubles/fixtures/recordings, truthful statuses | Evidence contract | All CLA IDs; CLA-OPS-005 | R/G/R records and integrity scan |
| NFR-SEC-001; NFR-PRIV-001/002 | Least privilege, allowlists, bounded execution, no content/secrets/analytics | A01 boundary policy | CLA-SEC-001..010 | Security and real artifact/network review |
| NFR-LIC-001 | No dependency before full admission | Dependency records | CLA-DEP-001/002 | Locked graph/SBOM/notices review |
| NFR-PLAT-001 | Linux verified; no Linux logic in adapter contracts; macOS explicit Blocked until real evidence | manifest platform scope | CLA-LIVE-008, CLA-OPS-004 | Real Linux; real macOS only |
| NFR-PERF-001 | Bounded pages/files/results and no per-account redesign | manifest constraints | CLA-PERF-001/002 | Real current sources/accounts; no invented load |
| NFR-RES-001; AC-OPS-003 | A01 failure cannot interrupt other adapters/API/UI | CTR-PROV-004; component health | CLA-OPS-001/002 | Real naturally unavailable/malformed case or Blocked |
| NFR-OBS-001 | Correlated structured safe codes only | safe logs/CTR-PROV-004 | CLA-SEC-007, CLA-OPS-003 | Real logs/diagnostics scan |
| NFR-COMP-001; AC-LIVE-004 | Version/schema/protocol compatibility and real conformance | CTR-PROV-001..008 | CLA-ARCH-004/005, CLA-LIVE-001..015 | M03 conformance plus live matrix |
| AC-LIVE-001 | Six intended Claude accounts enrolled or owner-documented unavailable | M02/A01 handoff | CLA-LIVE-002 | Per-account owner-countersigned ledger |
| AC-LIVE-005/007 | Reconcile dynamic quota/API values and naturally available states | M05 inputs | CLA-LIVE-004..007/011 | Same-scope/time provider comparison; unavailable stays Blocked |
| AC-HIST-001 | Real A01 observation reaches M05/M06 history/API/UI | typed inputs and commit contracts | CLA-OPS-006 | Full real vertical slice |
| AC-OPS-006 | Collection respects evidenced request/rate/cost constraints | CTR-PROV-002 | CLA-NET-009/010, CLA-PERF-001 | Real bounded observation and M04 evidence |

A01 contributes evidence but does not by itself pass M02 enrollment, M05 calculation, M06 hierarchy/state, M04 scheduling, API, UI, or release criteria.

## 3. Domain design

### 3.1 Adapter identity and composition

A01 is statically registered by the composition root. It does not scan entry points or import provider code dynamically. If Claude subscription/local behavior and Anthropic API behavior require different provider-product keys, credential roles, version schemes, or failure boundaries, A01 registers separate immutable adapter descriptors from separate factories. Synchronization freezes those keys; the adapter does not infer them from display labels.

Each registration has:

- immutable adapter ID and semantic adapter version;
- exact provider-product key;
- supported M03 protocol range;
- canonical capability manifest fingerprint;
- build/version metadata;
- one implementation route per approved capability/source tuple;
- no general-purpose `execute`, raw request, or arbitrary metadata operation.

### 3.2 Capability activation state

Each capability tuple is keyed by provider product, adapter version, provider/CLI/API version rule, plan/account class, credential-role category, platform, capability schema, source ID, and M0 decision reference.

States are:

- `supported`: enabled only for the evidenced tuple;
- `experimental`: disabled by default and requires the synchronized scoped grant; no private/browser source is approved by this plan;
- `deferred`: advertised as non-invokable;
- `unsupported`: advertised with safe reason and evidence reference;
- `unknown`: pre-decision only and non-invokable.

The manifest cannot use wildcard plan/version/role scope unless M0 evidence explicitly supports it. A new provider version is `unverified_provider_version`, not assumed compatible from a similar version string.

### 3.3 Source registry and priority

Every source is an explicit `ProviderSourceV1` descriptor. M0 supplies its class, supported operation, version signal, credential role, side effects, freshness, output/input bounds, request/read cost, and failure semantics.

Source selection rules:

1. M03 resolves an exact approved source or exact approved chain before A01 I/O.
2. A01 never probes an unselected source.
3. Fallback occurs only when the manifest and request both authorize the transition and the first typed outcome permits it.
4. A weaker source is never substituted silently.
5. The actual source and any prior safe failure code appear in provenance.
6. Cached/local prior values are never returned as a fresh collection outcome.

No source command, endpoint, host, path, or field is named in production design until M0 approves it. The capability matrix is the authority, not a hardcoded assumption in this plan.

### 3.4 Version and parser registry

Every parser/mapping route is selected by a closed key:

```text
(provider_product, capability, source_id, source_schema_or_format_version,
 provider_cli_or_api_version_rule, capability_schema_major,
 extension_schema_major)
```

Rules:

- detect versions through an approved safe mechanism before parsing version-sensitive data;
- use exact/opaque/date/semantic comparison only according to M0 evidence;
- never parse an unknown version with the “nearest” known parser;
- parser identity/version and actual provider version enter provenance;
- reject unknown fields unless the approved source schema explicitly ignores them safely before content can enter memory/logs;
- bound bytes, fields, nesting, items, text length, numeric precision, and parse time;
- discard raw input immediately after closed mapping; never store, log, emit, or attach it to an exception;
- an invalid structure returns `invalid_provider_data`; an unknown version returns `unverified_provider_version`.

Pure parser tests may operate only on owner-approved sanitized structural values that contain no dynamic account data, content, identity, or secret. Such tests prove deterministic transformation and rejection only. They are not provider compatibility evidence and are not committed as provider response fixtures or recordings.

### 3.5 Subscription quota mapping

The `CLA-SUBSCRIPTION` lane maps an evidenced source into M05 `ProviderQuotaInputV1` without interpreting health or forecasting.

The mapping must preserve, when M0 proves each field:

- resource/window identity and provider-native safe label;
- exact used, remaining, limit, ratio field states and units;
- reset/renewal time plus timezone and precision;
- provider status only through an approved bounded mapping or extension;
- completeness/partial scope and explicit missing fields;
- observed/data-through/collected times;
- source, adapter/parser/provider versions, freshness, precision, confidence, and warnings.

Missing values never become zero. A displayed percentage is never reverse-engineered into a hidden denominator. Distinct native windows remain distinct. Subscription data is never mapped to Anthropic API cost/budget resources.

### 3.6 Anthropic API mapping

The A01-owned `ANTHROPIC-API` lane maps only M0-supported official read-only surfaces:

- usage into `ProviderUsageInputV1`;
- cost into `ProviderCostInputV1`;
- budget/credit/limit into `ProviderBudgetInputV1`;
- project/workspace candidates into M02 discovery inputs.

Each request uses a bounded supported time window, group set, page count, result count, response size, and request budget. It uses the least-privilege approved provider-managed credential reference. A01 never accepts a key value in a method parameter, command argument, log, test, configuration record, or evidence artifact.

Money, token/request counts, bucket intervals, model/project/key-safe dimensions, pagination completeness, data latency, and currency are mapped exactly as M0 and M05 contracts define. A field not exposed by the provider is Unsupported/Unknown, never derived from unrelated spend. A01 performs no currency conversion and no billable model generation.

### 3.7 Local session metadata mapping

The `CLA-LOCAL` lane reads only M0-approved paths/files/fields through the approved filesystem port. Before a read, it validates the approved root grant, canonical containment, symlink policy, file type, owner/mode where required, maximum size, expected format/version signal, and deadline.

Allowlist categories may include only those proven safe by M0 and accepted by M06, such as a stable safe session identity, bounded model/project/task operational labels, exact token/context metrics, activity timestamp/class, safe error code, or parent-session evidence. This list is illustrative contract space, not a claim that Claude exposes any item.

Explicitly prohibited:

- prompt or response text;
- tool names/arguments/results when they expose activity/content beyond an approved safe code;
- source-code/file contents;
- terminal transcript/output;
- free-form task or error text;
- credential/auth/cookie/token fields;
- arbitrary JSON objects or unknown fields;
- absolute paths unless separately classified and approved;
- environment values.

The parser must avoid reading prohibited values, not broadly capture and redact later. When a container file intermixes allowed and prohibited data and the approved parser cannot extract safely without materializing content, that source is Unsupported.

### 3.8 Identity and correlation

A01 emits evidence; M02 and M06 own decisions.

Potential identity layers remain distinct:

- installation;
- default or managed profile reference;
- Claude product account identity;
- Anthropic API organization/workspace/project identity;
- subscription or API resource pool;
- provider session identity;
- Linux process identity received from A04/M06.

An automatic correlation is emitted only when an accepted M0 rule classifies the exact evidence as Strong and collision/lifetime behavior is understood. Email, display name, working directory, process timing, current login, PID alone, or plan label never proves identity. Conflicts return typed conflicting evidence. Weak evidence produces `confirmation_required` or `unresolved`.

A01 does not inspect `/proc`, command lines, environment, terminals, or memory. `local.process.correlation` accepts only the safe process/session references in the synchronized request and returns M06-owned evidence values.

### 3.9 Authentication health

Only an M0-approved observable signal can map to one of:

- `healthy`;
- `refreshing`;
- `expiring`;
- `reauthentication_required`;
- `revoked_or_disabled`;
- `wrong_account_detected`;
- `unknown`.

Network/provider unavailability is an outer outcome, not an auth state. A successful unrelated local parse does not prove auth health. If the expected identity is unavailable, identity comparison remains unresolved.

### 3.10 Managed-profile reauthentication

Reauthentication is a separately gated capability. The adapter must reject the operation before external I/O when the profile is protected-default, protection is Unknown, the target/expected identity is missing, the M0 isolated-profile decision is absent, or the caller lacks an approved owner-interaction grant.

When enabled, the adapter invokes only the official reviewed flow against an AgentMonitor-managed profile root. The owner performs browser/device/email/MFA/OTP interaction directly. A01 never accepts or captures credentials/codes. It emits typed safe action state and verifies the returned identity before the coordinator updates M02. Wrong identity ends the flow as `wrong_account_detected`; it never relinks or overwrites history.

No reauth implementation begins merely because Claude has an interactive `/login` command. Exact profile isolation, command behavior, process lifecycle, cancellation, restart recovery, and default-profile no-change evidence must be approved first.

### 3.11 Timeout, cancellation, pagination, retry, and backoff

- M04/context owns the total deadline and cancellation signal; A01 never extends it.
- Every filesystem, subprocess, and HTTP operation receives a bounded slice of the remaining deadline.
- Subprocess output and HTTP response bytes are bounded before parsing.
- Pagination is explicit and bounded by approved page/item/request limits; partial completion reports the cursor/completeness semantics allowed by the typed contract.
- A01 performs no autonomous retry by default. If a provider-documented idempotent transport retry is ever proposed, it requires M0 evidence, M04 ownership agreement, and a new reviewed plan version.
- Authentication, authorization, wrong-account, version, malformed-data, and protected-profile outcomes are never retried.
- Rate limiting returns `rate_limited` with only provider-supported retry timing/precision and no repeated attempt.
- Cancellation stops only AgentMonitor collector work; it cannot signal or affect a monitored Claude process.

### 3.12 Error and degradation model

A01 returns only CTR-PROV-004 outcomes and stable adapter reason codes. It never returns a provider exception, response body, stdout/stderr, file fragment, path, credential detail, or free-form error.

Expected mappings include:

- executable/source absent -> approved `unsupported` or `provider_unavailable` according to capability decision/context;
- provider version absent/unknown -> `unverified_provider_version`;
- provider authentication signal -> `reauthentication_required` in
  `CTR-PROV-006`, mapped by API/UI to
  `provider_reauthentication_required`; it never becomes
  `dashboard_authentication_required`;
- insufficient role -> `authorization_insufficient`;
- identity mismatch -> outer `success` with typed identity/reauthentication result `wrong_account_detected`;
- provider throttle -> `rate_limited`;
- schema/parser mismatch -> `invalid_provider_data`;
- deadline expiry -> `deadline_exceeded`; caller cancellation publishes no completed provider outcome and M04 records the cancelled collection-run state;
- owner step required -> `blocked_user_action_required`;
- contained unexpected defect -> `internal_adapter_error` with correlation ID.

One lane's failure changes only that lane's health/outcome. It does not clear historical/current M05/M06 facts, which become stale according to their owners.

## 4. Public contracts

### 4.1 Implemented M03 contracts

A01 publishes no replacement protocol. It implements only approved versions of:

| Register ID | A01 responsibility | Prohibited behavior |
|---|---|---|
| CTR-PROV-001 | static adapter descriptor and typed capability ports | generic execute/raw dict |
| CTR-PROV-002 | evidence-scoped manifest rows and collection constraints | wildcard unsupported claims |
| CTR-PROV-003 | exact source descriptors and approved source chain | silent downgrade |
| CTR-PROV-004 | validated typed outcomes and sanitized failures | exception/raw payload leakage |
| CTR-PROV-005 | bounded installation/account/project candidates | creating or linking accounts |
| CTR-PROV-006 | auth-health/identity observation | treating provider outage as auth failure |
| CTR-PROV-007 | managed-only reauth flow after separate approval | default-profile mutation/secret capture |
| CTR-PROV-008 | Claude-specific closed safe extensions | arbitrary JSON/free text |

Every method uses `ProviderOperationContextV1`; no method accepts a credential, environment map, unrestricted root, raw shell command, or free-form provider identifier.

### 4.2 Consumed M02/M04 contracts

From M02, A01 consumes a narrow target that includes only opaque installation/account/profile/resource references, provider product, profile purpose/protection classification, expected identity assertion, and approved access-grant references. Friendly name/email is not required for collection.

From M04, A01 receives operation/correlation IDs, selected capability/source, deadline/cancellation, page/time scope, run reference, and approved cost/concurrency policy through M03 context. A01 does not schedule itself, decide cadence, acquire leases, retry runs, or write collection history.

Missing/unknown profile protection blocks reauth. Missing account/resource identity blocks capability invocations whose semantics require it. M02/M04 unavailability produces a pre-I/O typed failure; A01 does not query their tables.

### 4.3 Typed M05 outputs

A01 can construct only the approved major versions of:

- CTR-CAP-001 `ProviderQuotaInputV1`;
- CTR-CAP-002 `ProviderUsageInputV1`;
- CTR-CAP-002 `ProviderCostInputV1`;
- CTR-CAP-002 `ProviderBudgetInputV1`.

The M05 contract owns exact quantities, field states, windows, resource definitions, dimensions, money, completeness, and cardinality. A01 owns the source-specific mapping. A mapping gap is escalated to contract synchronization; it is never solved with an `extra`, dictionary, raw string, or provider conditional in M05.

### 4.4 Typed M06 outputs

A01 can construct only M06-approved closed values:

- CTR-RUN-002 `LocalSessionObservationInputV1`;
- CTR-RUN-002 `RuntimeMetricObservationInputV1`;
- the approved M06 session relationship/state evidence types;
- CTR-RUN-007 correlation evidence inputs;
- `RuntimeObservationBatchV1` through the synchronized M03/M04 commit path.

A01 does not create `AgentSessionViewV1`, normalized runtime state, tree aggregate, stall classification, or account decision. Unknown/unsupported fields use M06 field states and never zero/default.

### 4.5 Claude provider extensions

No extension field is approved by this Draft. M0 may propose an extension only when a safe Claude-specific concept cannot map to a normalized contract.

Each proposed extension receives:

- stable schema identity `claude.<capability>.<schema>.v<major>` or the CS-approved equivalent;
- exact provider-product/capability/source/parser/provider-version scope;
- closed fields with type, unit, nullability, enum values, cardinality, length, numeric and nesting bounds;
- privacy classification and proof excluding credentials, identity beyond approval, content, arbitrary environment, raw output, and free-form errors;
- owner/consumer list and whether M05/M06/API/UI opt in;
- compatibility and migration behavior;
- M0 and live evidence references.

Unknown extension fields or majors are rejected, not persisted as opaque JSON. A breaking meaning/unit/privacy change requires a new major and consumer migration.

### 4.6 Provenance contract

Every successful or partial A01 observation supplies the provider-boundary portion of CTR-COMMON-004:

- provider-product/capability/schema;
- adapter/protocol/source/parser/provider version;
- actual source class and stable source ID;
- observed/data-through and collection start/end times as available;
- freshness deadline or explicit Unknown plus policy reference;
- precision, confidence and explanation code;
- value kind;
- Experimental flag/fallback lineage;
- bounded safe warning codes;
- operation/correlation and accepted M0 decision reference.

A01 does not set `stored_at` or downstream derivation metadata. A result missing mandatory provenance cannot be `success`.

### 4.7 Contract impact assessment

This plan implements but does not own `CTR-PROV-001..008`,
`CTR-COMMON-004`, CTR-CAP inputs, or CTR-RUN inputs. A01 owns the Claude
extension schema definitions inside the M03-governed versioned namespace; M03
remains semantic producer of `CTR-PROV-008`.

Before approval the synchronization review must resolve:

1. exact provider-product identity and registration of the A01-owned Anthropic
   API sub-adapter;
2. exact provider-product/adapter/source/capability/schema identifiers;
3. exact narrow M02 target/profile/identity contracts;
4. exact M05/M06 typed input versions and bounds;
5. safe filesystem/subprocess/HTTP/profile-access port owners and versions;
6. the reauth coordinator and managed-profile lifecycle;
7. configuration/manifest authority and static registration ownership;
8. evidence/extension schema locations and compatibility policy.

Any semantic change after synchronization follows the contract versioning policy and may require an ADR.

## 5. Data and persistence

### 5.1 Owned data

A01 owns **no database table, migration, repository, outbox, durable cache, account record, observation history, or credential store**.

- M02 persists registry/profile/resource relationships.
- M03 persists compatibility assessments if approved.
- M04 persists collection runs.
- M05 persists quota/API observations and projections.
- M06 persists runtime observations/correlation decisions.
- M08 persists product operations data.

Adapter/source/parser/version/extension compatibility metadata is declared in the versioned A01 manifest and schema documents, then assessed by M03. A01 must not duplicate that state in an adapter table.

If implementation reveals a requirement for durable pagination, reauth flow, or compatibility data, work stops. The appropriate owner and contract are determined through synchronization; A01 does not add a convenience table.

### 5.2 In-memory state

Permitted in-process state is limited to immutable parser/source registries, bounded connection/executor resources supplied by approved ports, and per-operation ephemeral variables. It cannot outlive/relabel an observation as current, contain secret values beyond the owning boundary's unavoidable ephemeral use, or act as a cross-run telemetry cache.

Raw provider input is released after mapping. Cancellation/exception handling clears references as practical and never includes them in diagnostics.

### 5.3 Retention, backup, restore, and migration impact

A01 has no adapter-owned retention or backup content. Manifest/schema source files follow normal release versioning. A rollback changes the statically composed adapter version/capability exposure; it never deletes M02/M05/M06 history.

M03/M05/M06 persistence migrations are outside A01. A01 contract/schema changes must remain readable by the supported consumer compatibility range or use a new major and coordinated migration.

## 6. External and platform boundaries

### 6.1 Installation/CLI boundary

An approved safe subprocess port resolves an allowlisted executable reference and supplies exact argument vectors. A01 never uses a shell or searches mutable untrusted path state on its own. It uses a minimal environment selected by the profile/execution owner; A01 cannot request arbitrary environment values.

Before every version-sensitive operation, the adapter verifies the resolved executable identity/version according to the accepted compatibility rule. Commands are fixed reviewed operation IDs from the M0 handoff. A help/status label does not authorize execution.

Timeout, process-group cleanup, stdout/stderr bounds, decoding policy, exit mapping, and redaction happen through approved production execution code. Cancellation terminates only the collector subprocess it created, never a monitored Claude process.

### 6.2 Filesystem boundary

An approved safe filesystem port supplies opaque root/file grants. A01 validates containment, symlink policy, regular-file/type expectation, ownership/mode where required, maximum size, stable-read/race behavior, and deadline before parsing.

No recursive broad scan, glob over an unapproved root, credential-file hash/content read, provider-state write, atime promise, or default-profile mutation is allowed. The exact file list and field allowlist come from M0. Permission denied and format drift are typed outcomes.

### 6.3 Network/API boundary

An approved provider network port supplies HTTPS policy and opaque credential application. A01 never receives or logs the credential value. Allowed host, redirect, TLS, method, endpoint, query/grouping, page, response-size, timeout, and request-count rules come from M0.

No model-generation endpoint is called to test monitoring. No private/browser endpoint, cookie, proxy, interception, global TLS disable, arbitrary URL, or cross-host redirect is allowed. An unexpected redirect/host/schema/cost stops the operation.

### 6.4 Process boundary

A01 does not enumerate OS processes. A04-LINUX supplies safe process facts through CTR-RUN-006/M06. A01 may correlate only closed safe references when an exact M0-approved join rule exists. It has no signal, input, attach, memory, terminal, environment, restart, kill, or routing method.

### 6.5 Authentication boundary

Provider credentials remain in provider-managed storage. A01 receives opaque profile/credential references through approved access ports and never copies them to `.env`, database, logs, evidence, tests, command arguments, or diagnostics.

Owner login/browser/device/email/MFA/OTP actions occur outside A01 data contracts. Default profiles are protected and read-only. Managed-profile writes require the separate reauth grant and official flow.

### 6.6 Real verification method

Every external lane is verified against its real boundary:

- installed/version/CLI behavior: current real Claude executable through production executor;
- filesystem behavior: approved real provider files through production safe filesystem path;
- subscription values: real owner account and authoritative provider surface at matching time/scope;
- API usage/cost/budget: real owner-controlled Anthropic organization/role and official surface;
- local sessions/correlation: real naturally running Claude sessions and real Linux observations;
- reauth: real AgentMonitor-managed profile and owner-performed official flow;
- failure isolation: naturally available real failure/unavailability only; otherwise Blocked.

No response recording, fixture, fake adapter, fake CLI, fake filesystem, local provider server, seeded account, demo telemetry, or test-only production path may replace these boundaries.

## 7. Security and privacy

### 7.1 Trust boundaries and controls

| Threat | Required A01 control |
|---|---|
| malicious/changed CLI output | byte/time bounds, closed versioned parser, unknown rejection, no raw diagnostics |
| malicious/huge provider file | approved path/type/owner/size, symlink containment, allowlisted fields, parse deadline |
| credential leakage | opaque refs, credential applied only by owning port, no args/logs/results/evidence |
| content leakage | source/field allowlist prevents capture; raw payload never retained |
| default profile damage | protected/unknown mutation rejection before invocation and live pre/post evidence |
| wrong account enrollment/reauth | expected stable identity, mismatch stop, owner confirmation, no automatic relink |
| source downgrade/private endpoint | exact M03 resolution; unsupported rather than fallback |
| running-agent disruption | no process-control API; collector cancellation isolated from monitored processes |
| parser/version drift | exact evidenced rules; unknown version non-invokable |
| API overuse/cost | M0/M04 request budget, no autonomous retry/generation, rate-limit outcome |

### 7.2 Allowlist data flow

The security review maintains a field-flow table for every enabled source:

```text
external field/category
  -> read prevention or approved ephemeral read
  -> adapter-local typed field
  -> M02/M05/M06 contract field or approved extension
  -> allowed log/diagnostic representation
  -> persistence owner/retention
```

Anything not in the table is rejected. “Redact later” is not approval. Safe errors use stable codes and opaque correlation IDs. Account emails, raw local paths, provider output, request IDs that can expose account identity, and dynamic values are absent from committed evidence.

### 7.3 Default-profile immutability proof

For read-only capability live tests, the operation packet defines approved non-secret pre/post metadata and owner-visible checks that do not require reading credential contents or storing credential-file hashes. Any uncertainty or observed mutation fails the scenario and stops A01 work.

For managed reauth, the target root must be an AgentMonitor-managed profile with a verified non-default classification. The operation is rejected before invoking Claude if classification is not definitive.

### 7.4 Logging and diagnostics

Allowed fields are timestamp, severity, A01 component/lane, stable event/safe error code, correlation/operation ID, opaque internal target ID, capability/source/adapter/provider/parser versions, duration, outcome class, bounded counts, and retry disposition.

Forbidden fields include raw command, arguments when sensitive, stdout/stderr, response bodies/headers, URLs with queries, local paths, identity labels/email, credential presence detail beyond approved boolean at M08, provider values, prompts/responses/tools/source, environment, traceback text containing external data, and arbitrary exception strings.

### 7.5 Incident stop

If secret/content/identity/raw payload appears, a default profile may have changed, a running agent reacts, an unexpected host/cost/write/login/update occurs, or source/version differs from approval:

1. stop without retry or broadened inspection;
2. preserve only sanitized incident metadata;
3. quarantine accidental sensitive output outside repository/chat;
4. notify owner/root/security;
5. rotate/revoke only through owner/provider incident procedure when required;
6. mark affected scenarios Failed or Blocked;
7. require new discovery/security/contract approval before resuming.

## 8. Configuration and operations

### 8.1 Configuration ownership

This Draft allocates no final environment-variable name. Candidate categories, all M0/CS-blocked, are:

- adapter/lane enablement derived from registered monitoring profiles;
- opaque executable/service/profile/root references owned by M02/deployment;
- capability/source enablement and Experimental grant owned by synchronized M02/M03 workflow;
- timeouts, page/result/output bounds, request/concurrency budgets owned by M04/M03 with provider caps from A01 evidence;
- safe network host policy owned by security/network boundary;
- parser/compatibility records shipped with A01 version, not user-overridable to weaken safety.

Configuration cannot enable an Unsupported/Unknown version, disable default-profile protection, add paths/hosts/fields, expose raw diagnostics, or weaken provider constraints. Provider credentials are not AgentMonitor configuration values.

Each approved key requires a CTR-CONFIG-001 record naming type, bounds, safe default, source/precedence, owner, reload behavior, secret class, first/deprecation version, operational consequence, and tests.

### 8.2 Health and readiness

A01 publishes a bounded component-health contribution through M03/M08:

- adapter registration/protocol/manifest status;
- each lane/capability decision and enabled/disabled state;
- provider-version verified/unverified status;
- last attempt/success time and outcome class from owning collection view references, not duplicated telemetry;
- authentication-required/authorization/version/rate/deadline safe status;
- source/schema/parser versions;
- stale/Unknown/Unsupported distinction;
- safe warning codes.

Readiness policy is synchronized: an optional Unsupported capability cannot take down the service; an invalid manifest, unsafe profile classification, or enabled incompatible capability makes that lane unavailable and visible. A01 health performs no provider call.

### 8.3 Canonical automation selectors

Foundation/integration owns canonical commands. Before A01 implementation handoff, repository automation must support fail-closed selectors for:

- A01 pure/contract/parser policy tests;
- real Claude CLI/filesystem/Linux tests;
- real Anthropic API tests when the lane is enabled;
- live-account reconciliation and reauth matrices;
- import/contract/version/extension checks;
- prohibited-double/fixture/content/secret/control-path scans;
- dependency/license/SBOM/notices checks;
- documentation/traceability/live-status validation.

The command must report Passed, Failed, Blocked, and Not Run separately. A deterministic green result cannot conceal absent T5/T6 evidence. Exact command names remain foundation-owned until implemented and tested; prose here is not the executable gate.

### 8.4 Operator procedures

Documentation must provide only verified commands/procedures for:

- inspect A01 manifest/capability/compatibility health;
- diagnose installation/source/version/auth/authorization/rate/parse failures safely;
- enroll/confirm account/profile/resource through M02;
- run bounded manual refresh through M04;
- perform managed-profile reauth with owner interaction;
- disable/rollback an affected capability/source;
- respond to provider version drift and repeat live verification;
- handle suspected secret/content/default-profile incidents.

Unimplemented commands are marked Planned/TBD and are never invented in a runbook.

### 8.5 Operational measurements

Allowed local measurements are bounded counts and durations for A01 operations by capability/outcome, current compatibility status, response/output bytes after safe count-only measurement, and rate-limit/backoff safe metadata. No provider metric value, account identity, local path, content, secret, or external analytics is emitted.

## 9. Test design before implementation

### 9.1 Evidence and integrity rules

Every scenario below is **Not Run** at plan creation. A future Red is valid only when the test reaches the specified real or pure boundary and fails for the expected missing/incorrect behavior. Missing credentials, absent owner, unavailable account, syntax errors, uninstalled dependencies, or setup failure are Blocked/Not Run—not Red.

No mock, fake, stub, emulator, simulated provider/process, recorded/replayed response, provider fixture, demo account, seeded telemetry, placeholder value, monkeypatch of a production collaborator, hardcoded pass, swallowed failure, or test-only production branch is permitted.

Pure parser checks use only owner-approved sanitized structural values and do not claim provider compatibility. CLI/filesystem/network/provider claims use the production adapter against the real boundary. Dynamic values are compared by identity, scope, unit, time, precision, freshness, and provider tolerance, never hardcoded.

### 9.2 Pure contract and policy scenarios (T1)

| Test ID | Requirement | Initial Red | Green/pass condition |
|---|---|---|---|
| CLA-PURE-001 | FR-COL-006/008 | Unknown capability resolves to invocation | Unknown/Deferred/Unsupported has no port |
| CLA-PURE-002 | FR-COL-007/008 | adapter silently moves to weaker/unapproved source | only exact approved source chain can resolve |
| CLA-PURE-003 | FR-DISC-008 | provider version uses guessed semantic ordering | evidenced version scheme only; unknown is unverified |
| CLA-PURE-004 | FR-DISC-008 | parser selected for nearest unsupported version | exact approved rule selects or rejects |
| CLA-PURE-005 | FR-COL-004 | success accepts missing parser/provider/source version | required provenance validation fails safely |
| CLA-PURE-006 | FR-ACC-006/FR-DISC-004 | display label/recent login proves account | evidence remains unresolved/confirmation required |
| CLA-PURE-007 | FR-DISC-004 | conflicting evidence chooses highest score | conflict returned; no account selected |
| CLA-PURE-008 | FR-DISC-004 | provider session/process timing alone links account | weak evidence cannot auto-correlate |
| CLA-PURE-009 | FR-AUTH-001 | provider unavailable maps to reauth required | outer availability and auth state remain distinct |
| CLA-PURE-010 | FR-AUTH-001 | missing auth evidence maps healthy | state is Unknown with reason |
| CLA-PURE-011 | FR-COL-006 | Unsupported becomes temporary unavailable | decision and runtime outcome stay distinct |
| CLA-PURE-012 | FR-COL-008 | partial omission retires/zeros absent values | completeness/missing fields preserved |

Constructed values in this group are contract/policy examples only, contain no provider observations, and perform no I/O.

### 9.3 Sanitized parser and mapping scenarios

These functions are deterministic and side-effect free, but their inputs must be owner-approved E1 structural values from the accepted source schema. They are not committed provider-response fixtures and do not expand the verified provider-version range.

| Test ID | Requirement | Initial Red | Green/pass condition |
|---|---|---|---|
| CLA-PARSER-001 | FR-QUOTA-001/002 | two native windows collapse into one | each approved window identity remains separate |
| CLA-PARSER-002 | FR-QUOTA-001/004 | missing amount becomes zero | exact field state remains Unknown/Unsupported |
| CLA-PARSER-003 | FR-QUOTA-001 | reset loses timezone/precision | approved reset semantics preserved exactly |
| CLA-PARSER-004 | FR-COL-004 | quota mapping omits source/freshness/confidence | valid M05 input requires complete provenance |
| CLA-PARSER-005 | FR-DISC-003/006 | unknown/free-form local field passes | closed M06 allowlist rejects it |
| CLA-PARSER-006 | FR-DISC-006 | incompatible token/context scope is mislabeled | exact kind/unit/scope required or field unverified |
| CLA-PARSER-007 | FR-DISC-006 | free-form task/error is accepted | only approved bounded code/operational label passes |
| CLA-PARSER-008 | FR-DISC-005/006 | inclusive parent/child metric marked disjoint | aggregation eligibility remains unknown/inclusive |
| CLA-PARSER-009 | FR-BUDGET-004 | API money becomes binary float | exact M05 representation preserved |
| CLA-PARSER-010 | FR-BUDGET-003 | arbitrary grouping dimension enters DTO | closed dimension/schema rejects it |

### 9.4 Real CLI/subprocess scenarios (T5/T6 as applicable)

| Test ID | Requirement/AC | Real dependency | Initial Red | Green/pass condition |
|---|---|---|---|---|
| CLA-CLI-001 | FR-ACC-005 | real installed Claude | installation not discovered or wrong product | exact executable/version evidence mapped safely |
| CLA-CLI-002 | FR-ACC-005 | real supported discovery surface | discovery triggers update/login/write | bounded read-only result and zero unapproved effect |
| CLA-CLI-003 | AC-LIVE-004 | real M03 registration | manifest differs from installed/evidenced tuple | exact scoped manifest/compatibility result |
| CLA-CLI-004 | FR-DISC-008 | real supported CLI output | parser/provider version absent or wrong | versions reconcile with real executable/source |
| CLA-CLI-005 | FR-COL-005 | naturally nonzero/partial real result | raw stderr/free text leaks or is misclassified | stable safe outcome, bounded discarded output |
| CLA-CLI-006 | FR-COL-004/005 | real deadline | operation exceeds deadline or leaves child collector | deadline outcome and collector cleanup only |
| CLA-CLI-007 | FR-COL-008 | real unknown/new version when naturally present | known parser runs anyway | version-sensitive capability blocked safely |
| CLA-CLI-008 | FR-SAFE-002 | real running Claude agents | collector sends input/signal/restart | no monitored process effect; only collector process managed |

No test intentionally installs, updates, logs in/out, corrupts output, or kills a running agent to create a case.

### 9.5 Real filesystem/local-session scenarios (T5/T6)

| Test ID | Requirement/AC | Real dependency | Initial Red | Green/pass condition |
|---|---|---|---|---|
| CLA-FS-001 | FR-DISC-001/003 | approved real Claude root | unapproved root/file enumerated | only grant/allowlist accessed |
| CLA-FS-002 | FR-DISC-001 | real running session metadata | current session missed/misattributed | supported presence is truthful or explicit unresolved |
| CLA-FS-003 | FR-DISC-003; AC-PROC-004 | approved real file | content/credential field materialized/persisted | prevention and artifact scan prove absence |
| CLA-FS-004 | FR-DISC-008 | real current format/version | version/schema omitted or guessed | exact parser/source/provider versions recorded |
| CLA-FS-005 | FR-DISC-003 | real permission boundary | denied file becomes empty success | permission/partial/unavailable outcome explicit |
| CLA-FS-006 | NFR-SEC-001 | real safe symlink/path condition if present | path escapes approved root | escape rejected before read; unavailable stays Blocked if absent |
| CLA-FS-007 | NFR-SEC-001 | real bounded file | oversized/changed file read unbounded | size/race/deadline fail safely |
| CLA-FS-008 | FR-DISC-006 | real approved metadata | model/token/context/activity/error meanings wrong | fields reconcile by scope/unit/time/source |
| CLA-FS-009 | FR-DISC-004 | real provider sessions and M06 refs | weak/conflicting evidence auto-maps | Strong rule only or unresolved/confirmation required |
| CLA-FS-010 | FR-DISC-008 | real version drift | prior parser accepts changed format | invalid/unverified result; prior facts only become stale |

### 9.6 Real Anthropic API scenarios (T6, fixed A01 ownership)

| Test ID | Requirement/AC | Real dependency | Initial Red | Green/pass condition |
|---|---|---|---|---|
| CLA-NET-001 | FR-BUDGET-001/006 | real approved role/account | unsupported source invoked or wrong scope | exact capability/role/source tuple enforced |
| CLA-NET-002 | FR-BUDGET-003 | real usage source | group/bucket/page scope lost | bounded typed M05 usage input reconciles |
| CLA-NET-003 | FR-BUDGET-002/004 | real cost source if supported | money/currency/interval imprecise | exact cost input reconciles; otherwise Unsupported |
| CLA-NET-004 | FR-BUDGET-002 | real budget/credit source if supported | absent field inferred from spend | provider field mapped or explicit Unsupported/Unknown |
| CLA-NET-005 | FR-BUDGET-003 | real pagination | page omission appears complete | completeness/cursor/request count truthful |
| CLA-NET-006 | FR-COL-004 | real data latency | observed/data-through/freshness conflated | each time and precision preserved |
| CLA-NET-007 | FR-AUTH-001 | naturally insufficient/expired role if available | authorization/auth/provider outage collapse | exact outcome; otherwise Blocked |
| CLA-NET-008 | FR-COL-008 | real provider response | unexpected field/schema accepted or raw retained | closed mapping/rejection and no raw artifact |
| CLA-NET-009 | FR-COL-003; AC-OPS-006 | naturally rate-limited signal if available | adapter retries or ignores retry semantics | one typed outcome; M04 owns backoff; otherwise Blocked |
| CLA-NET-010 | FR-COL-005 | real network deadline/outage if natural | unbounded retry blocks other lanes | bounded failure isolation; otherwise Blocked |

### 9.7 Live account, reconciliation, runtime, and reauth matrix (T6)

| Test ID | Requirement/AC | Real boundary | Initial Red | Green/pass condition/coordination |
|---|---|---|---|---|
| CLA-LIVE-001 | AC-LIVE-004 | real current Claude version | adapter registration/conformance fails | M03 real conformance for enabled tuple |
| CLA-LIVE-002 | AC-LIVE-001 | six intended account aliases | enrollment/availability ledger incomplete | each owner-confirmed or owner-documented unavailable |
| CLA-LIVE-003 | FR-AUTH-001 | real account/profile | displayed auth state disagrees with authoritative surface | scope/time/evidence reconcile |
| CLA-LIVE-004 | FR-QUOTA-001/006 | real subscription account | native windows/fields differ | all supported windows mapped; gaps explicit |
| CLA-LIVE-005 | AC-LIVE-005 | provider authoritative usage view | value/unit/reset/scope/time mismatch | reconciles within documented latency/precision |
| CLA-LIVE-006 | FR-BUDGET-001..006 | real Anthropic API organization | usage/cost/budget lane incomplete | enabled capabilities reconcile; unsupported explicit |
| CLA-LIVE-007 | AC-LIVE-005 | authoritative API billing view | identity/scope/time/currency mismatch | nearest-time comparison passes tolerance |
| CLA-LIVE-008 | AC-PROC-001 | real running Claude process/session on Linux | launch workflow/state changes or session absent | safe supported presence without workflow change |
| CLA-LIVE-009 | AC-PROC-002/003 | real parent/subagent and account evidence | hierarchy/correlation guessed/wrong | owner/evidence agrees or visible unresolved conflict |
| CLA-LIVE-010 | FR-ACC-006 | naturally ambiguous real session | adapter assigns account | confirmation required/unresolved |
| CLA-LIVE-011 | AC-LIVE-007 | natural auth/exhausted/unavailable/recovery state | states collapse or cached data shown current | exact observed state; absent conditions Blocked |
| CLA-LIVE-012 | AC-LIVE-006 | approved managed profile | reauth cannot start safely | owner-visible official flow starts only for managed target |
| CLA-LIVE-013 | FR-AUTH-003 | same managed account reauth | account/history/group/config duplicated/lost | identity matches and M02 preserves records |
| CLA-LIVE-014 | FR-AUTH-001/003 | natural/approved wrong-account case | mismatch relinks account | flow stops wrong_account_detected; otherwise Blocked |
| CLA-LIVE-015 | FR-AUTH-005 | default profile plus managed reauth/read operations | default state changes | approved pre/post checks prove unchanged |

Owner performs all interactive authentication locally. No one intentionally exhausts quota, revokes credentials, switches active default login, or disrupts work merely to satisfy a test. Unavailable states remain Blocked.

### 9.8 Architecture, security, operations, performance, and documentation scenarios

| Test ID | Layer | Requirement | Green/pass condition |
|---|---|---|---|
| CLA-ARCH-001 | architecture | NFR-ARCH-001 | import gate permits only approved contracts/ports |
| CLA-ARCH-002 | architecture | FR-SAFE-002 | public/static surface contains no control/routing method |
| CLA-ARCH-003 | contract | NFR-ARCH-002 | A01 returns exact M05/M06 types; no domain logic/raw dict |
| CLA-ARCH-004 | contract | NFR-COMP-001 | manifest/protocol/source/schema/provenance versions match approvals |
| CLA-ARCH-005 | composition | NFR-RES-001 | static registration isolates lanes/adapters and duplicate conflicts |
| CLA-SEC-001 | security | FR-AUTH-004 | no credential/OTP/MFA/password/code parameter or retention path |
| CLA-SEC-002 | security/live | FR-AUTH-005 | protected/unknown profile mutation rejected before I/O |
| CLA-SEC-003 | security/live | NFR-SEC-001 | minimal command/network environment and no secret argument/output |
| CLA-SEC-004 | security/live | FR-AUTH-005 | real default profile unchanged after allowed operations |
| CLA-SEC-005 | privacy | NFR-PRIV-001 | field/source schema contains no prompt/response/tool/source content |
| CLA-SEC-006 | privacy/live | AC-PROC-004 | DB/log/event/API/export/backup/evidence scan finds no prohibited data |
| CLA-SEC-007 | observability | NFR-OBS-001 | logs/diagnostics are bounded stable codes with correlation IDs |
| CLA-SEC-008 | filesystem | NFR-SEC-001 | path/type/symlink/size/time bounds enforced at real boundary |
| CLA-SEC-009 | test integrity | NFR-TEST-002 | repository scan/review finds no doubles/recordings/fixtures/seed telemetry |
| CLA-SEC-010 | privacy/network | NFR-PRIV-002 | no analytics/crash reports/unapproved outbound host |
| CLA-OPS-001 | resilience | AC-OPS-003 | one real A01 lane failure leaves other adapters/API/UI available |
| CLA-OPS-002 | health | FR-OPS-002/006 | safe manifest/version/lane health is truthful and query-only |
| CLA-OPS-003 | diagnostics | NFR-OBS-001 | diagnostic bundle exposes only allowlisted version/outcome data |
| CLA-OPS-004 | platform | NFR-PLAT-001 | real Linux passes; macOS remains distinct Passed or Blocked |
| CLA-OPS-005 | automation | AC-TEST-001/006 | canonical report includes R/G/R and all non-Passed live states |
| CLA-OPS-006 | integration | AC-HIST-001 | real observation reaches M05/M06 DB, HTTP, built UI/history without seed |
| CLA-PERF-001 | performance | NFR-PERF-001 | real bounded polling for intended accounts stays within approved request/resource budget |
| CLA-PERF-002 | performance | NFR-PERF-001 | real local parsing/session collection meets synchronized bound without broad reads |
| CLA-DOC-001 | documentation | NFR-DOC-001 | docs/link/requirement/contract/live-status gate passes |
| CLA-DOC-002 | documentation | AC-V1-006 | verified operations, limitations, compatibility and reauth docs complete |
| CLA-DEP-001 | dependency | NFR-LIC-001 | every direct/transitive package passes admission and is locked |
| CLA-DEP-002 | dependency | NFR-LIC-001 | SBOM/notices/security/license scan includes exact graph and no undeclared SDK |

### 9.9 Red, Green, Refactor evidence

For every implemented behavior, the handoff records:

- requirement/AC, plan/increment, adapter/protocol/capability/source/parser/extension versions;
- exact scenario ID and real boundary;
- Red command, UTC timestamp, expected behavioral failure, actual sanitized failure, and worktree reference;
- minimum production change;
- Green command/result against the same boundary;
- post-refactor command/result and broader relevant suite;
- owner alias/version/time and countersignature for live work;
- Passed, Failed, Blocked, and Not Run rows separately;
- security/privacy/default-profile/side-effect reconciliation;
- dependency/license/operations/docs impact.

The canonical automation command and evidence format are foundation/integration contracts. No aggregate green can hide provider, platform, reauth, or naturally unavailable scenarios.

## 10. Implementation increments

Implementation starts only after section 15 is checked and the root issues a path/contract task packet.

| Increment | Owned scope | Failing tests first | Minimum Green production change | Exit evidence |
|---|---|---|---|---|
| CLA-I00 | contract/M0 synchronization only | no production test | freeze capability tuples, typed inputs, ports, source/field/command records | signed CS/M0 handoff; still no code |
| CLA-I01 | adapter skeleton/manifest pure files | CLA-PURE-001..005, CLA-ARCH-001/004 | static descriptor, evidence-scoped declarations and version rules | pure R/G/R and manifest review |
| CLA-I02 | source/outcome/correlation policies | CLA-PURE-006..012 | source resolution helpers, evidence mappings, safe reason codes | pure R/G/R and mutation review |
| CLA-I03 | parser/mapping registry | CLA-PARSER-001..010 | closed transformations for approved structural schemas | sanitized-structure R/G/R; no compatibility claim |
| CLA-I04 | installation/CLI lane | CLA-CLI-001..008 | production safe-executor integration for approved operations | real executable/version/side-effect evidence |
| CLA-I05 | subscription lane | CLA-LIVE-004/005 plus applicable parser/CLI IDs | exact `ProviderQuotaInputV1` mapping | real account reconciliation |
| CLA-I06 | local-session lane | CLA-FS-001..010, CLA-LIVE-008..010 | approved safe filesystem parsing and M06 inputs | real session/process/privacy evidence |
| CLA-I07 | auth-health lane | CLA-LIVE-003/011, CLA-SEC-001..004 | identity/auth observation only; no reauth | real auth evidence and no-change proof |
| CLA-I08 | A01-owned Anthropic API lane | CLA-NET-001..010, CLA-LIVE-006/007 | approved HTTP mappings to M05/M02 inputs | real API reconciliation, cost/rate bounds |
| CLA-I09 | managed reauth, separately authorized | CLA-LIVE-012..015 | protected-profile precondition and official flow adapter | owner-countersigned real flow; rare mismatch may remain Blocked |
| CLA-I10 | extension schemas/diagnostics | CLA-SEC-005..010, CLA-OPS-002/003 | only approved extensions and safe health/diagnostics | privacy/artifact/network scan |
| CLA-I11 | composition and M03 conformance | CLA-LIVE-001, CLA-ARCH-003/005 | static registration and real adapter conformance | M03 conformance/live matrix |
| CLA-I12 | vertical M04/M05/M06 integration | CLA-OPS-001/005/006 | real collection commit paths and failure isolation | real DB/HTTP/browser/history evidence |
| CLA-I13 | performance/platform/hardening | CLA-PERF-001/002, CLA-OPS-004, CLA-DOC/DEP | bounds, automation, docs, dependency proof | full handoff; non-Passed rows visible |

### 10.1 Ordering

- I00 is serial and approval-blocking.
- I01–I03 may proceed only after shared protocol/input types freeze. One A01 owner integrates manifest/parser registries.
- I04, I05, I06, and I08 may be assigned in parallel only to non-overlapping subdirectories after their exact lanes are Supported and safe boundary ports are Approved.
- I07 precedes I09; read-only auth health cannot be coupled to reauth mutation.
- I09 is a separate state-changing official managed-profile flow and needs explicit task authorization even after plan approval.
- I10 cannot add extension fields not accepted by M05/M06/security.
- I11 composition/shared files are owned by the integration steward, not parallel adapter agents.
- I12 requires M04/M05/M06 implementations and real observation flow; it cannot use a fake consumer or seeded row.
- I13 does not broaden provider compatibility from performance results.

### 10.2 Parallel-development isolation

Parallel A01 lane agents receive one directory, exact contract versions, exact M0 rows, and exact test IDs. They do not edit shared manifest aggregation, composition, dependency files, central contracts, generated files, migration chains, or another lane.

Suggested ownership:

| Work packet | Exclusive path | Consumes | Publishes |
|---|---|---|---|
| A01-SUB | `claude/subscription/**` and matching tests | M03 + CTR-CAP-001 | subscription mapper/port implementation |
| A01-LOCAL | `claude/local_sessions/**`, `correlation/**` and matching tests | M03 + CTR-RUN inputs + safe FS | local runtime mapper/ports |
| A01-AUTH | `claude/authentication/**` and matching tests | M03/M02 profile contracts | auth-health; reauth only separate task |
| A01-API | `claude/anthropic_api/**` and matching tests | M03 + CTR-CAP-002 + safe HTTP | API usage/cost/budget ports |
| A01-INTEGRATE | `adapter.py`, `manifest.py`, composition allocation | all lane outputs | one immutable A01 registration set |

Any needed shared contract change stops the affected packet and returns to root synchronization. No duplicate DTO, direct table read, `dict` payload, or private import may unblock it.

### 10.3 Stop points during implementation

Stop and notify root when:

- M0 evidence is missing, contradictory, or narrower than a proposed capability;
- exact provider/source/version/plan/role/platform behavior differs from the approved row;
- an undocumented/private/browser/cookie/interception source appears necessary;
- a command prompts login/update/write/purchase or a request reaches an unexpected host/cost;
- a default/unknown profile could be modified;
- local/API parsing would capture content, credentials, identity, arbitrary environment, raw paths, or unknown fields;
- account/session/process/resource identity would be guessed;
- the typed M05/M06 contract cannot represent a proven safe concept;
- process control, terminal input, routing, model generation, or credential switching is requested;
- a new dependency lacks admission or its license/telemetry/install behavior is unacceptable;
- a secret/content/raw provider value appears in code/test/log/DB/artifact/evidence/chat;
- a contract meaning/version or shared file must change;
- another agent owns or changes the same path.

## 11. Documentation outputs

Approved implementation must create/update, through assigned owners:

- `docs/adapters/claude.md`: outcome, lanes, boundaries, supported tuples, failures, health, limitations, and extension points;
- one capability matrix per distinct Claude subscription/local and Anthropic API product surface;
- safe operation registry: official source, operation ID, executable/endpoint/path class, bounds, side effects, versions, and evidence reference—without secret values or raw commands that have not been verified;
- source/parser/provider compatibility matrix and re-verification trigger;
- closed local/API field allowlist and prohibited-field proof;
- Claude extension-schema documentation and consumers;
- real test/live matrix with all Passed/Failed/Blocked/Not Run rows;
- install/discovery, account confirmation, refresh, version drift, diagnostics, managed reauth, disable/rollback, and incident runbooks using verified commands only;
- configuration registry entries after approval;
- dependency admission records, lock/SBOM/notices updates if any package is added;
- threat/data-flow updates for managed reauth or any Experimental proposal;
- central contract/traceability/risk/planning/release updates through root ownership;
- ADR for private/browser source, new secret storage, default-profile policy change, process/environment access, or breaking contract.

Documentation never includes real account identity, credentials, local absolute paths, dynamic quota/spend, raw provider output, screenshots with sensitive data, prompts/responses/tools/source, or arbitrary environment values.

## 12. Dependency and license impact

### 12.1 Initial posture

No dependency is approved or installed by this Draft.

A01 should initially use:

- approved standard-library parsing primitives where sufficient;
- centrally approved M03/common contracts;
- centrally approved safe filesystem/subprocess/HTTP/profile-access ports;
- the real installed Claude executable as an external tool, not a bundled dependency.

No Anthropic SDK, HTTP client, retry library, semantic-version library, filesystem watcher, process library, schema library, keyring, browser driver, telemetry client, or CLI wrapper is selected here. Direct documented HTTP versus an official SDK is decided only after M0 and full admission; convenience is not justification.

### 12.2 Admission record

Every proposed package/version must document before manifest/import/install:

- exact purpose and why standard library/admitted ports are insufficient;
- canonical upstream/package identity and exact license from upstream;
- full transitive dependency/license inventory;
- maintenance, ownership, release cadence, security policy/advisories, provenance and compromise history;
- supported Python/platform versions, native/binary components and install scripts;
- network/telemetry behavior;
- locked version/integrity/update/removal strategy;
- size/performance and operational effect;
- alternatives and removal cost;
- SBOM/notices impact;
- reviewer, decision, date, and recheck trigger.

Copyleft, custom, unclear, source-available, telemetry-bearing, opaque binary, or risky install behavior requires explicit owner decision. A package name in prose is not approval.

## 13. Risks and unresolved decisions

### 13.1 Risks

| ID | Risk | Likelihood/impact | Mitigation/evidence | Owner/status |
|---|---|---|---|---|
| A01-R01 / R-001 | no stable machine-readable subscription quota source | High/Critical | official-first M0; Unsupported is valid | M0/A01 Open |
| A01-R02 / R-002 | Claude local/CLI format changes | High/Major | exact version/parser registry, fail unverified, live range expansion | A01/M03 Open |
| A01-R03 / R-003 | account/session/process cannot correlate safely | High/Critical | Strong-only rule, unresolved/manual confirmation | A01/M02/M06 Open |
| A01-R04 / R-004 | default profile modified | Low/Critical | pre-I/O protection, zero-write sources, live pre/post checks | A01/security Open |
| A01-R05 / R-005 | secret/content captured from mixed provider data | Medium/Critical | prevention/allowlist/bounds/scans/incident stop | A01/security Open |
| A01-R06 / R-006 | collection exceeds safe rate/cost | Medium/Major | M0 constraints, M04 budget, no retry/generation | A01/M04 Open |
| A01-R07 / R-007 | stale/partial value looks current | Medium/Critical | mandatory completeness/freshness/provenance | A01/M05 Open |
| A01-R08 / R-009 | rare auth/exhausted/failure cases unavailable | High/Major | visible Blocked, no manufacturing | Test/owner Accepted constraint |
| A01-R09 / R-010 | live tests interrupt work/consume credits | Medium/Major | owner schedule, zero generation, stop budget | Live operator Open |
| A01-R10 / R-014 | subscription and API pools double-count | Medium/Major | distinct product/resource identities and DTO lanes | M02/M05/A01 Open |
| A01-R11 / R-018 | provider SDK/dependency introduces license/supply-chain risk | Medium/Critical | no dependency before admission | Dependency reviewer Open |
| A01-R12 / R-021 | reauth logs into wrong account/loses history | Medium/Critical | expected identity, mismatch stop, M02 transactional relink | A01/M02 Open |
| A01-R13 / R-024 | useful data requires private/browser source | Medium/Critical | Deferred/Unsupported; ADR/threat/approval required | Security/product Open |
| A01-R14 | official interactive UI cannot be safely polled | High/Major | dashboard comparison only; do not automate | M0/A01 Open |
| A01-R15 | mixed allowed/content local record makes safe parse impossible | High/Critical | reject source unless prevention is proven | Security/A01 Open |

### 13.2 Approval-blocking synchronization decisions

1. Accept M0 Claude/Anthropic/Linux handoff and capability matrices with all statuses and evidence references.
2. Freeze provider-product identity and registration for the A01-owned
   Anthropic API lane.
3. Freeze exact supported/experimental/deferred/unsupported capability tuples.
4. Freeze executable/service/provider version detection and compatibility schemes.
5. Freeze source IDs/classes/chains, command/request/path records, output/response/file bounds, and side effects.
6. Freeze exact native subscription windows, fields, units, reset/time precision, completeness, and reconciliation tolerance.
7. Freeze Anthropic API role/scope/endpoints/grouping/pagination/money/latency/rate/request-cost semantics where supported.
8. Freeze safe local path/file/field allowlists and parser/version identifiers.
9. Freeze safe session/model/project/task/token/context/activity/error/hierarchy inputs accepted by M06.
10. Freeze stable account/profile/session identity evidence, collision/lifetime behavior, Strong correlation rules, and owner-confirmation boundary.
11. Freeze narrow M02 provider target/profile-protection/expected-identity contracts.
12. Freeze CTR-PROV-001..008 and CTR-COMMON-004 versions/bounds.
13. Freeze M05 provider input schema versions/cardinalities/dimensions/extensions.
14. Freeze M06 input/correlation/relationship schema versions/cardinalities/extensions.
15. Allocate safe filesystem/subprocess/HTTP/cancellation/profile-access ports and owners.
16. Freeze M04 deadline/pagination/request budget/concurrency/no-retry/backoff/commit routing semantics.
17. Decide reauth coordinator, official operation, managed-root creation/ownership, process lifecycle, expiry/cancel/restart/idempotency/audit, and API/UI handoff.
18. Approve extension schemas and exact consumer opt-ins; none is implied.
19. Allocate configuration categories/keys/owners/reload behavior without weakening compatibility/safety.
20. Freeze component health/readiness effect and sanitized diagnostics.
21. Select exact test/mutation/performance budgets and canonical automation selectors.
22. Complete dependency/license/security review and confirm shared-file/parallel ownership.

No implementation agent may choose among materially different answers privately.

### 13.3 M0 handoff acceptance

A01 rejects the handoff if any enabled capability lacks:

- exact provider product, version, plan/account class, credential role, platform, and source class;
- official source/citation and observed real evidence;
- safe operation/path/field allowlist and prohibited-field analysis;
- units, windows, timestamps, reset/renewal, precision, freshness, completeness, and latency semantics;
- identity/resource/session scope and correlation strength;
- rate, request, cost, timeout, pagination, concurrency, and retry constraints;
- side-effect/default-profile/running-agent reconciliation;
- parser/version/compatibility signal;
- capability decision and every Blocked/Not Run scenario;
- safe extension need and consumer mapping.

Unknown items block the affected lane; they do not block documentation of Unsupported or independent supported lanes.

## 14. Delivery and rollback

### 14.1 Delivery order

1. Complete M0 G9 and accept A01 handoffs.
2. Synchronize section 13.2 contracts and approve this plan.
3. Implement pure manifest/source/version/outcome policies through TDD.
4. Implement one lowest-side-effect Supported read-only lane and complete real conformance.
5. Add subscription, local-session, and API lanes one at a time with independent live gates.
6. Add read-only auth health before considering managed reauth.
7. Implement reauth only through a separately authorized task after isolated-profile proof.
8. Integrate M04/M05/M06/M02 and static composition through root-owned changes.
9. Run real DB/API/browser/history/failure-isolation/operations evidence.
10. Complete security/privacy/dependency/license/docs and release handoff.

### 14.2 Feature exposure

Every lane defaults disabled/non-invokable until its exact manifest tuple is Approved and real live verification has passed for the claimed version/scope. An unknown/new version disables only the affected version-sensitive source/capability. Unsupported and Blocked remain visible.

No rollout flag can enable a source, field, host, path, version, or reauth behavior beyond the approved manifest. Experimental behavior requires a separate explicit grant and is never automatic fallback.

### 14.3 Rollback and recovery

- Disable/remove the affected A01 manifest lane from static composition using the approved release rollback; do not delete M02/M05/M06 history.
- Revert to a prior compatible adapter binary only when M03 protocol/extension compatibility allows it.
- Mark latest facts stale/unverified through normal domain behavior; never replace them with cached/fake current values.
- Preserve immutable capability/compatibility/evidence history owned by other modules.
- Expire active reauth flows on uncertain restart unless the synchronized coordinator proves safe resumption.
- Re-run manifest/version/default-profile/secret-content checks before re-enabling.
- A contract-breaking rollback follows the ADR/migration/consumer plan; A01 has no database downgrade.

### 14.4 Post-delivery checks

- exact adapter/protocol/manifest/source/parser/provider/extension versions are visible and compatible;
- only Approved tuples are enabled;
- real quota/API/session observations retain source/scope/unit/time/precision/confidence/freshness;
- subscription and API pools remain separate;
- unresolved identity stays unresolved and owner confirmation remains explicit;
- no default profile/provider/running agent state changed;
- no provider-specific code leaked into M03/M05/M06;
- no content/secret/raw provider value exists in logs, DB, events, API, UI, export, backup, test, build, diagnostics, or evidence;
- other adapters/API/UI remain available when an A01 lane fails;
- every live/provider/platform scenario has a visible status;
- canonical planning/test/quality/docs/dependency gates report exact scope and exit status.

### 14.5 Implementation handoff

The handoff must name requirement/AC IDs, plan and all contract/schema versions, exact files, M0 decision rows, Red/Green/refactor evidence, real account/provider/CLI/API/platform versions, owner acknowledgement, live reconciliation, side-effect/default-profile checks, every Failed/Blocked/Not Run scenario, dependency/license/SBOM/notices impact, security/privacy scan, configuration/operations/docs changes, rollback, known limitations, and exact integration step.

## 15. Definition of ready

- [ ] M0 G9 is complete and Claude, Anthropic API, and Linux handoff packets are accepted.
- [ ] Capability decisions and exact evidenced tuples are frozen; Unknown behavior is not treated as implementation detail.
- [ ] This plan's scope/non-goals/lanes and Anthropic API ownership are approved.
- [ ] CTR-COMMON, CTR-REG, CTR-PROV-001..008, CTR-COL, CTR-CAP inputs, CTR-RUN inputs, safe-execution, configuration, and evidence contracts are Synchronized/Approved.
- [ ] Every command, endpoint, host, path, file, field, parser, version rule, side effect, rate/cost/timeout/page bound, and source chain is approved by operation/source ID.
- [ ] Default-profile protection and managed-profile isolation are evidence-backed; reauth remains separately gated.
- [ ] M05/M06 typed outputs and all extension schemas/bounds/consumer opt-ins are approved.
- [ ] Requirements/AC/test IDs and expected behavioral Red are reviewed.
- [ ] Real intended account aliases/current tools/platforms and owner checkpoints are scheduled.
- [ ] Canonical fail-closed A01 test/quality/docs/live reporting selectors exist and are tested for their claimed boundaries.
- [ ] Security/privacy/field-flow/threat/default-profile/no-control reviews pass.
- [ ] Every dependency/version/lock/transitive license/security/provenance record is approved.
- [ ] Configuration, health, diagnostics, operator procedures, rollback, and incident handling are assigned.
- [ ] Paths/shared files/composition/generated artifacts are allocated without parallel conflict.
- [ ] Planning registry/catalog and synchronization review account for this exact plan/version.
- [ ] The canonical planning gate passes for the claimed stage.
- [ ] No unresolved decision permits materially different implementation.
- [ ] Owner/root/contracts/security/test/live/operations/dependency reviewers approve the plan.

Until every applicable item is checked, A01 is not implementation-ready. Plan approval alone does not authorize provider access, authentication, dependency installation, implementation, deployment, or live execution.

## 16. Approval record

| Role | Decision | Conditions | Date |
|---|---|---|---|
| Owner | Pending | M0/live resources and interaction model |  |
| Root/integration steward | Pending | contract synchronization and path allocation |  |
| M02 Registry owner | Pending | target/profile/identity/resource semantics |  |
| M03 Provider-system owner | Pending | protocol/conformance/source/extension semantics |  |
| M04 Collection owner | Pending | deadlines/rate/cost/commit/failure policy |  |
| M05 Capacity owner | Pending | quota/API input mappings and extensions |  |
| M06 Runtime owner | Pending | session/metric/correlation inputs and privacy |  |
| A04-LINUX owner | Pending | process-reference boundary only |  |
| M08/operations owner | Pending | health/diagnostics/recovery |  |
| Security/privacy reviewer | Pending | field flow, default-profile, reauth and incident controls |  |
| Test-integrity/live reviewer | Pending | no-double and real-boundary matrix |  |
| Dependency/license reviewer | Pending | exact admitted graph |  |

Implementation remains prohibited while Status is Draft, M0 is incomplete, contracts are unsynchronized, the canonical gate is red/absent, or any Definition-of-Ready item is unchecked.
