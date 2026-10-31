# Adapter plan: A04-MAC — macOS platform adapter

- Status: **Draft; planning only; not approved for implementation**
- Plan version: 0.2.0-draft
- Adapter contract version: implements proposed FND-owned `CTR-PLAT-001 PortablePlatformPrimitivesV1` and M06-owned `CTR-RUN-006 ProcessInspectionPortV1`; consumes deployment constraints but does not implement `CTR-DEP-001`
- Owner: A04 macOS platform-adapter owner
- Reviewers: integration/contract, A04 Linux, M06, M08, DEP, A01–A03, security/privacy, test-integrity, operations, and dependency reviewers
- Requirements: FR-DISC-001/002/003/004/005/007/008; FR-OPS-001/002/005/006 where platform-portable; FR-SAFE-002; NFR-ARCH-001/002; NFR-TEST-001/002; NFR-SEC-001; NFR-PRIV-001/002; NFR-DOC-001; NFR-LIC-001; NFR-PLAT-001; NFR-PERF-001; NFR-RES-001; NFR-OBS-001; NFR-COMP-001
- Acceptance criteria: supports AC-V1-002/005/006/007/008; AC-PROC-002/003/004 where exercised on macOS; AC-OPS-002/003/005 where exercised on macOS; AC-TEST-001/002/004/006. It does **not** satisfy Linux-specific AC-PROC-001 or AC-OPS-001.
- Published/implemented contracts: implements M06-owned CTR-RUN-006 and FND-owned portable CTR-PLAT-001 only; publishes no independent shared semantics
- Consumed contracts: CTR-COMMON-001/002/004/007; CTR-FND-003/004/008; CTR-CONFIG-001; CTR-BOUNDARY-001/003; CTR-REG-004; CTR-PROV-002/003; CTR-RUN-001/002/003/006; CTR-OPS-006; CTR-DEP-001
- Target milestone: post-Linux V1 compatibility increment, after real macOS discovery and contract synchronization
- Approved by/date: pending

This plan is governed by the [requirements](../../../product/requirements.md), [V1 acceptance criteria](../../../product/v1-acceptance-criteria.md), [module boundaries](../../../architecture/modules.md), [contracts and versioning](../../../architecture/contracts-and-versioning.md), [data model](../../../architecture/data-model.md), [provider-adapter contract](../../../architecture/provider-adapter-contract.md), [security architecture](../../../architecture/security.md), [deployment architecture](../../../architecture/deployment.md), [testing strategy](../../../engineering/testing-strategy.md), [SDLC](../../../engineering/sdlc.md), [completion and automation gates](../../../engineering/completion-and-automation-gates.md), [dependency policy](../../../engineering/dependency-and-license-policy.md), [Milestone 0 runbook](../../../operations/milestone-0-discovery-runbook.md), [live-verification runbook](../../../operations/live-verification-runbook.md), [M06 plan](../../modules/m06-runtime-observation/plan-v1.md), [contract register](../../contract-register.md), and [planning catalog](../../planning-catalog.toml).

Structural names in this document are proposals, not claims about an available macOS API, command, provider path, launchd field, or supported macOS version. No macOS host, provider state, or service was inspected while producing this plan.

## CS-1 alignment addendum — contract baseline 0.2.0

This addendum is normative for CS-1 and supersedes any wording below that makes
A04-MAC a semantic producer of a shared contract or an implementer of the
deployment lifecycle. The machine-readable
[contract baseline](../../contract-baseline.toml) and
[parallel ownership manifest](../../parallel-ownership.toml) remain unapproved
and grant no implementation or macOS mutation authority.

- PLAN-M06 is the sole semantic producer of
  `CTR-RUN-006 ProcessInspectionPortV1`; A04-MAC implements the macOS side only
  after real-Mac evidence. Semantic changes return to M06 contract review.
- PLAN-FND is the sole semantic producer of
  `CTR-PLAT-001 PortablePlatformPrimitivesV1`; A04-MAC implements its macOS
  process-supporting, native-path, approved-file, platform-health, and fixed
  AgentMonitor user-service primitives. macOS extensions cannot redefine the
  portable meaning.
- A04-MAC does not implement or publish `CTR-DEP-001`. PLAN-DEP owns artifact
  and unit activation plus fenced service-quiescence orchestration. A04-MAC
  consumes the fixed target/intent and supplies only CTR-PLAT-001 mechanics and
  receipts.
- The adapter consumes `CTR-COMMON-001/002/004/007`, `CTR-CONFIG-001`,
  `CTR-BOUNDARY-001/003`, and M08-owned `CTR-OPS-006`. Field availability is
  never reduced to null/zero; file/subprocess safety is never privately
  weakened; leaf health cannot aggregate readiness. A04-MAC owns no durable
  event; domain events use `CTR-COMMON-006` plus `CTR-EVT-001` through the
  owning domain workflow.
- After a real Mac is assigned and contracts are approved, process,
  approved-file/native-path, diagnostics, and fixed user-service primitive
  lanes may proceed in separate internal paths. Shared contracts,
  configuration, dependencies, composition, generated files, native service
  definitions, and live targets remain centrally allocated single-writer work.

Linux or emulated behavior cannot establish macOS support. No mock, fake,
recording, seeded process, placeholder field, or unexecuted result is credited;
absent real macOS evidence remains Blocked or Not Run.

## Planning gate and present evidence state

The adapter can be specified without pretending that Linux evidence proves macOS behavior. The implementation boundary is deliberately split:

1. **Contract-only work may proceed later**, after the plan and shared contracts are approved, for pure value policies, closed outcome schemas, import boundaries, and fail-closed evidence reporting. It cannot claim a macOS capability works.
2. **macOS source implementation may not begin** until a real supported Mac is assigned, the read-only discovery packet is approved, source and version evidence is reviewed, and the relevant T5 scenarios can execute on that Mac.
3. Linux, Darwin compatibility layers, containers, emulators, simulated syscalls, patched platform identifiers, recorded command output, and mocked process/filesystem/service collaborators cannot satisfy the macOS gate.
4. A hosted job that merely reports `darwin` is insufficient unless the environment exposes the real process, filesystem-permission, user launchd, and provider-runtime boundaries claimed by the scenario.
5. Until the real-macOS gate opens, all T5 scenarios in this plan are `Blocked`; all unexecuted pure/contract scenarios are `Not Run`. Neither state is a pass.

The current peer A04-LINUX plan implements the same M06-owned CTR-RUN-006 and
FND-owned portable CTR-PLAT-001 boundaries. CS-1 reviews both plans together:
portable identities, units, field states, errors, cancellation, and side-effect
classes must agree, while `/proc`, systemd, cgroup, XDG, launchd, and other
native mechanics remain isolated. A04-MAC consumes PLAN-DEP constraints but
does not implement CTR-DEP-001 semantics. No Linux source detail or test result
is assumed to apply to macOS.

## 1. Outcome and boundaries

### 1.1 Outcome

A04-MAC will provide a least-privilege macOS implementation of the shared platform contracts so AgentMonitor can observe real supported provider processes, resolve approved provider state paths, perform bounded safe file reads, report sanitized platform diagnostics, and integrate its own user service with launchd. It preserves the same domain meaning as Linux without forcing either operating system's mechanisms into M06, providers, M08, or deployment orchestration.

Measurable outcomes are:

- every process identity includes PID plus a validated process-start identity and executable identity within an explicit boot/platform scope;
- process exit, PID reuse, reparenting, permission denial, and partial fields remain distinct typed outcomes;
- CPU and memory values carry their actual source semantics and units rather than Linux-derived assumptions;
- working-directory data is returned only when permitted and through the synchronized sensitive-path representation;
- provider-state reads accept only approved root handles and allowlisted relative paths, reject traversal and symlink escape, and are bounded by file type, owner, size, time, and output policy;
- AgentMonitor's launchd integration uses only the current user's service domain, contains no secret in service definitions or command arguments, and never targets provider processes;
- platform diagnostics expose only an allowlist of compatibility, capability, permission, timing, and health facts;
- unsupported OS versions, APIs, permissions, and sources disable the affected capability honestly;
- no implementation reads arbitrary process environments or command lines, attaches/debugs, reads memory, signals, pauses, restarts, kills, or injects input into provider agents;
- every macOS claim is backed by a real-macOS T5 record or remains visibly Blocked/Not Run.

### 1.2 In scope

- macOS process enumeration and per-process inspection behind CTR-RUN-006.
- Stable process identity, parent candidates, lifecycle/race detection, safe executable identity, process state, CPU, resident memory, and working directory when the selected real source supports them.
- Native macOS application/configuration/data/state/cache/log directory resolution for AgentMonitor.
- Validation of registry/provider-supplied approved state roots without inspecting provider content during path resolution.
- Descriptor-oriented or equivalently race-resistant bounded reads of specifically allowlisted provider metadata files after source evidence and security review.
- Owner/mode/type/size/symlink/path-boundary checks and safe typed failures.
- macOS platform/version/source capability detection and provenance.
- Current-user launchd primitives required by DEP-owned native service lifecycle: install-target validation, bootstrap/load mapping, start, stop, status, unload/disable mapping, and sanitized diagnostics after real-source verification.
- Safe local platform health for M08.
- TDD, real-macOS verification, security review, dependency admission, documentation, and handoff evidence for this adapter.

### 1.3 Out of scope

- M06 process/session identity, hierarchy, state, correlation, aggregation, stall, persistence, and history policies.
- Provider executable classification, session parsing, provider file/field allowlists, account identity, authentication, quotas, budgets, or provider-specific state roots; A01–A03/M02/M03 own those meanings.
- Global service installation, artifact layout, upgrade orchestration, rollback orchestration, or operator command names; PLAN-DEP owns CTR-DEP-001 and the canonical deployment routine.
- Global backup/restore/export, database, retention, or application readiness; M08/DB own them.
- Public REST routes, OpenAPI, UI, or generated client.
- Reading command-line arguments, arbitrary process environment values, process memory, terminal input/output, sockets/payloads, open-file contents, prompts, responses, tools, source code, credentials, cookies, or raw provider payloads.
- Root/system LaunchDaemons, privileged helpers, kernel extensions, Endpoint Security clients, debuggers, DTrace/instrumentation attachment, accessibility automation, screen capture, or terminal automation.
- Signaling or controlling Claude, Codex, Ollama, shells, terminals, or any non-AgentMonitor process.
- Automatic permission prompts or changes to Full Disk Access, Accessibility, developer tools, SIP, Gatekeeper, login items, provider profiles, or provider file permissions.
- macOS packaging/notarization/signing distribution decisions beyond reporting their interface needs to PLAN-DEP/release planning.
- Claiming macOS as a V1 release-verified platform while its required real scenarios are Blocked.

### 1.4 Ownership

A04-MAC owns:

- macOS implementations of M06-owned process inspection and FND-owned portable filesystem/service primitive interfaces;
- macOS source selection, compatibility range, source adapters, and error translation;
- macOS-specific value conversion into synchronized cross-platform units;
- the internal process sampling window and race-validation sequence;
- safe native-directory resolution and approved-root handle validation;
- macOS-specific fixed-service manager primitives beneath CTR-PLAT-001 for PLAN-DEP composition;
- macOS capability/health projection and sanitized diagnostic facts;
- platform T5 scenario automation selectors and evidence metadata;
- macOS adapter documentation and compatibility matrix.

A04-MAC owns no database table, migration, web route, persistent provider record, provider parser, alert, background schedule, or domain policy. It may return observations but cannot write M06, registry, operations, or provider tables.

### 1.5 Proposed future paths

Allowed paths, subject to PLAN-FND synchronization:

```text
backend/src/agentmonitor/adapters/platform/macos/
  process_source/
  filesystem/
  service_manager/
  diagnostics/
  compatibility/
backend/tests/platform/macos/pure/
backend/tests/platform/macos/contract/
backend/tests/platform/macos/live/
backend/tests/platform/macos/security/
docs/platform/macos.md
docs/contracts/platform-macos-v1.md
docs/operations/macos.md
```

Shared contract sources remain in centrally assigned contract paths owned by
M06 (CTR-RUN-006), FND (CTR-PLAT-001), and DEP (CTR-DEP-001). A04-MAC edits none
of them without an approved producer-owned contract-change assignment. Evidence
containing local operational metadata remains outside version control under the
owner-approved evidence root.

Forbidden imports/paths include:

- Linux adapter internals, `/proc`, systemd, cgroups, XDG-specific implementation modules, or Linux command parsers;
- M01–M08 internals, repositories, ORM models, migrations, or tables;
- Claude/Codex/Ollama adapter internals and provider credential stores;
- FastAPI, SQLAlchemy, Alembic, or UI code;
- arbitrary shared `utils` modules;
- shell execution, unbounded subprocess capture, process-control/debugger libraries, environment readers, or test-double frameworks;
- owner `.env`, provider profile content, source trees, raw diagnostics, or evidence directories.

Allowed imports are the Python standard library after runtime compatibility review, synchronized contract packages, A04-MAC internals, and dependencies that independently pass admission. Domain/core contract packages cannot import A04-MAC.

### 1.6 Parallel-development isolation

After contract synchronization:

- M06 can implement platform-neutral identity/race/field-state policies against CTR-RUN-006 without importing macOS code.
- A01–A03 can declare provider executable/state-root descriptors without knowing macOS APIs.
- A04-MAC can implement process and filesystem sources in separate internal paths once a real Mac is available and their shared result types freeze.
- DEP composes the user-service lifecycle through CTR-DEP-001 while A04-MAC
  owns only FND-defined CTR-PLAT-001 launchd primitives.
- M08 can consume bounded health through CTR-OPS-006.

Work is not parallel-safe when it changes a shared contract meaning, configuration key, native layout, service label, generated file, dependency lock, or common error vocabulary. Such changes return to synchronization.

## 2. Requirements and traceability

| Requirement/AC | Planned A04-MAC behavior | Contract | Scenario IDs | Evidence gate |
|---|---|---|---|---|
| FR-DISC-001 | Discover approved provider process identities without launch-flow change | CTR-RUN-006 | MAC-PROC-001/002, MAC-SEC-006 | real supported Mac + real provider processes |
| FR-DISC-002 | Return safe PID/parent/start/executable/state/CPU/memory/cwd fields with field-level outcomes | CTR-RUN-006 | MAC-PURE-001..004, MAC-PROC-003..012 | real-source unit and permission evidence |
| FR-DISC-003 | Supply bounded approved-file primitive without interpreting provider content | CTR-PLAT-001 | MAC-FS-001..010 | real filesystem and provider-approved paths |
| FR-DISC-004 | Return identity/link evidence only; never infer account ownership | CTR-RUN-006 | MAC-CONTRACT-003, MAC-PROC-013 | M06/provider correlation review |
| FR-DISC-005 | Return validated ancestry candidates; M06 owns session/subagent hierarchy | CTR-RUN-006 | MAC-PURE-005, MAC-PROC-009/010 | real representative process trees |
| FR-DISC-007 | Contract and implementation contain no arbitrary environment read | CTR-RUN-006/CTR-PLAT-001 | MAC-SEC-001/002/006 | source scan + real observation review |
| FR-DISC-008 | Attach source/adapter/OS/provider-version references where available | CTR-COMMON-004 | MAC-CONTRACT-004, MAC-DIAG-001 | contract + real provenance evidence |
| FR-OPS-001 | Provide analogous user-login launchd seam without claiming Linux acceptance | CTR-DEP-001 | MAC-SVC-001..010 | real user launchd lifecycle; not AC-OPS-001 credit |
| FR-OPS-002 | Report safe platform/service capability health | CTR-OPS-006/CTR-PLAT-001 | MAC-DIAG-002..005 | real service/application health |
| FR-OPS-005 | Prevent secrets/content in service files, logs, diagnostics, and evidence | CTR-PLAT-001/CTR-DEP-001 | MAC-SVC-011, MAC-SEC-003..005 | secret/content scans at real boundaries |
| FR-OPS-006 | Report safe OS/adapter/source/service versions | CTR-PLAT-001 | MAC-DIAG-001/002 | real Mac/version comparison |
| FR-SAFE-002 | Expose no provider process-control primitive | all | MAC-CONTRACT-005, MAC-SEC-006/007 | schema/import/live invariance proof |
| NFR-ARCH-001/002 | Isolate platform mechanics behind typed contracts | CTR-RUN-006/CTR-PLAT-001 | MAC-ARCH-001..003 | canonical import/ownership gate |
| NFR-TEST-001/002 | Red-Green-Refactor and no prohibited substitutes | evidence contract | all MAC-* | canonical test evidence |
| NFR-SEC-001 | Least privilege, safe path/subprocess/output/permissions | CTR-PLAT-001 | MAC-FS-*, MAC-SVC-*, MAC-SEC-* | security review + real Mac |
| NFR-PRIV-001/002 | Operational metadata only; no outbound telemetry | all | MAC-SEC-001..005/008 | code/network/artifact inspection |
| NFR-DOC-001 | Maintained contracts, compatibility, runbook, evidence | documentation | MAC-DOC-001 | canonical docs gate |
| NFR-LIC-001 | Dependency admission, locking, SBOM/notices | dependency record | MAC-DEP-001 | canonical dependency gate |
| NFR-PLAT-001 | Preserve Linux-first portability and verify only on real macOS | all | all MAC-PROC/FS/SVC/DIAG scenarios | actual supported Mac; no emulation |
| NFR-PERF-001 | Bounded inspection supports 200 processes without redesign | CTR-RUN-006 | MAC-PROC-014, MAC-PERF-001 | real approved workload |
| NFR-RES-001 | One denied/raced/malformed subject does not abort unrelated inspection | outcome types | MAC-PROC-006/007, MAC-FS-008, MAC-SVC-012 | real failure isolation |
| NFR-OBS-001 | Structured allowlisted logs/correlation IDs | CTR-FND-004 | MAC-SEC-003, MAC-DIAG-004 | protected local log inspection |
| NFR-COMP-001 | Version platform contracts, sources, OS compatibility | all | MAC-CONTRACT-001/002/004 | compatibility gate |
| AC-PROC-002 | Support truthful hierarchy on representative real Mac provider trees | CTR-RUN-006/CTR-RUN-003 | MAC-PROC-009/010 | supplemental macOS evidence only |
| AC-PROC-003 | Supply evidence without guessing account/session relationship | CTR-RUN-006 | MAC-PROC-013 | M06 live flow |
| AC-PROC-004 | Prove prohibited data absent | all | MAC-SEC-001..006 | real DB/log/export integration review |
| AC-OPS-002/003 | Service persists without browser; source failure isolated | CTR-DEP-001/CTR-OPS-006 | MAC-SVC-007/012, MAC-DIAG-005 | real installed application |
| AC-OPS-005 | Recovery/runbook exercised on macOS when supported | CTR-DEP-001 | MAC-SVC-010, MAC-DOC-001 | PLAN-DEP integration |
| AC-TEST-001/002/004/006 | RGR evidence; no doubles; real records; visible Blocked | evidence contract | MAC-AUTO-001/002/003 | canonical fail-closed report |

### 2.1 Acceptance non-credit rules

- AC-PROC-001 explicitly requires the real Linux workstation. macOS results cannot pass it.
- AC-OPS-001 explicitly requires native Linux lifecycle. launchd results cannot pass it.
- A generic non-provider process can verify process-source mechanics but cannot pass a provider-discovery or session-correlation claim.
- A launchd test agent created only to test AgentMonitor service mechanics may prove launchd behavior; it cannot impersonate a provider or count as application deployment evidence.
- Contract/pure tests cannot convert any T5 row to Passed.

## 3. Internal design

### 3.1 Components

| Component | Responsibility | Forbidden responsibility |
|---|---|---|
| `MacCompatibilityProbe` | Determine OS/build/architecture and source availability through approved safe APIs | choose product support policy or install software |
| `MacProcessEnumerator` | Produce a bounded set of candidate PIDs under one inspection deadline | classify providers or retain history |
| `MacProcessInspector` | Read one candidate's approved fields and validate identity/races | read args/environment/memory/content or infer account |
| `MacProcessMeasurementConverter` | Convert source-native time/CPU/memory/state into synchronized units with provenance | invent missing values or Linux semantics |
| `MacApprovedRootResolver` | Resolve native/explicit roots and mint scoped approved-root handles | discover provider content or accept web/API paths |
| `MacBoundedMetadataReader` | Read one allowlisted relative regular file under a validated root | parse provider schemas or recurse arbitrarily |
| `MacUserServiceDriver` | Map DEP-owned AgentMonitor lifecycle requests to verified user launchd mechanisms | operate provider services/processes or define upgrade policy |
| `MacPlatformDiagnostics` | Project allowlisted capabilities, versions, permission states, and bounded counters | dump raw command output, paths, users, environment, or file contents |

All I/O remains in these adapter components. Shared contracts and pure conversion/policy types perform no I/O.

`MacOSCapabilityProfileV1` uses the portable states `supported`, `unavailable`, `permission_denied`, `unverified`, `incompatible`, or `disabled`; there is no optimistic default. Candidate capability keys, pending real discovery and synchronization, are:

- `process.enumeration.macos.v1`;
- `process.identity.start_marker.v1`;
- `process.executable_identity.v1`;
- `process.parent_identity.v1`;
- `process.cpu_time.v1` and optional `process.cpu_utilization_sample.v1`;
- `process.resident_memory.v1`;
- `process.cwd_reference.v1`;
- `filesystem.registered_root.v1`;
- `filesystem.bounded_regular_read.v1`;
- `filesystem.side_effect_safe_read.v1`;
- `paths.macos_user.v1`;
- `service.launchd_user_inspection.v1`;
- `service.launchd_user_lifecycle.v1` only when DEP enables it.

The profile records adapter version, safe OS product/build compatibility class, architecture, selected source IDs/versions, safe boot/platform-scope fingerprint, launchd-source availability/version where approved, and observation time. It omits host/user identity, hardware serial, home/provider paths, raw service output, arguments, environment, and content.

### 3.2 Process identity and sampling sequence

The proposed inspection algorithm is source-neutral until discovery selects public macOS mechanisms:

1. Establish one inspection context: correlation ID, UTC `observed_from`, monotonic deadline, adapter/source version, OS product/build, architecture, and boot/platform scope.
2. Resolve candidate selectors from approved installation descriptors, then enumerate candidate PIDs through the selected source with a configured hard count and time bound. Selectors may use only the same portable evidence classes as Linux: approved executable identity, safe native process-name evidence if synchronized, ownership by the AgentMonitor service user, and registered installation references. They never use command-line arguments or target environments.
3. For each PID, read the start identity and executable identity before optional fields.
4. Read parent candidate, state, CPU, resident-memory, and working-directory fields independently. Permission or unsupported outcomes remain field-local where identity is still trustworthy.
5. Re-read the process start identity using the same source before returning the record.
6. If the process disappeared, identity changed, or source observations conflict, return `process_disappeared` or `process_identity_changed`; never merge the optional fields into another process.
7. Record `observed_to`, duration, field outcomes, and provenance. Do not return observations after the request deadline.

The process key is conceptually `(platform_instance, pid, start_identity, executable_identity)`. Exact start-identity representation, boot-scope representation, precision, and executable evidence are blocked on real-source discovery and CTR-RUN-006 synchronization. PID alone is never stable identity.

### 3.3 Parent and hierarchy evidence

- A parent PID from the child's process record is a candidate, not a durable edge.
- A validated parent identity requires inspecting the parent and proving its start identity was valid during the relevant observation interval.
- A disappeared, inaccessible, reparented, or reused parent produces an explicit unavailable/conflict reason.
- The adapter does not label process ancestry as provider session/subagent hierarchy.
- M06 decides relationship type, cycles, orphans, and aggregation after consuming provider and platform evidence.
- Process enumeration order, shared executable, shared working directory, and timing proximity are never parent or account proof.

### 3.4 Field semantics

Each optional field uses a closed result state such as `known`, `permission_denied`, `unsupported`, `unavailable`, `raced`, or `unverified_source`. `unknown` is not encoded as zero, empty string, negative sentinel, or omitted provenance.

#### CPU

- Source-native cumulative CPU time and sampled utilization are different measurement kinds.
- A utilization sample records the observation interval and whether it is normalized per logical CPU, total machine capacity, or another documented source meaning.
- The adapter does not divide/multiply by processor count unless the shared contract explicitly selects that derivation.
- A first sample without a valid comparison interval may expose cumulative time or unavailable utilization; it cannot invent zero percent.
- Units and precision must reconcile on a real Mac with an independent approved system view before support is declared.

#### Memory

- Resident bytes, physical footprint, virtual size, compressed memory, and provider model memory are distinct concepts.
- V1 returns only the synchronized memory kind proven by the selected source, expected initially to be a resident-memory concept if evidence supports it.
- Conversion to bytes is exact and overflow checked. Missing/permission-denied is not zero.

#### State

- Raw macOS process state is converted only through a versioned allowlist.
- Unknown/new raw states map to `unknown` with the raw value discarded or represented only by an approved bounded safe code.
- The platform state does not prove M06 `working`, `waiting_for_input`, `waiting_for_permission`, or `possibly_stuck` by itself.

#### Working directory

- CWD is collected only if the approved source exposes it without attaching, environment access, terminal inspection, or content traversal.
- The boundary representation is synchronized as an owner-visible sensitive path, approved root-relative reference, safe label, or unavailable state.
- Raw absolute paths are never logged, included in diagnostics/evidence, or exposed to unauthenticated consumers.
- The default proposal aligns with M06: persist/display a safe label or opaque path reference, not the raw absolute path.

#### Executable

- No command-line arguments are read.
- Executable identity is based on an approved native source and may include a bounded safe basename, root-relative installed path, and stable file identity/code identity only after evidence.
- A path outside registered installation roots remains unclassified rather than guessed from its name.

### 3.5 Time, ordering, and concurrency

- Contract timestamps are aware UTC; monotonic time measures operation/sample durations.
- Wall-clock changes cannot create a negative sampling interval; affected derived measurements become unavailable.
- Inspection order is not a causal or hierarchy order.
- Per-PID work uses bounded concurrency selected from measurement, with one total deadline and cancellation propagation.
- Timeout stops new per-PID work and returns a partial outcome with exact inspected/uninspected counts, not a silent truncated success.
- No hidden retry converts a process race or permission denial into success. A single immediate identity recheck is part of the algorithm, not a retry loop.

### 3.6 Approved-root and bounded-read model

An `ApprovedRootHandleV1` is minted only from a registry/configuration reference already authorized for one provider installation/profile and one capability. It contains an opaque ID, resolved root identity, owner expectation, policy version, and allowed relative path set. It does not contain credential material and is never constructed from an HTTP request path or provider file contents.

For every requested file, the future implementation must:

1. require a registered root handle and manifest-owned relative path token;
2. reject absolute paths, empty components, `.`/`..`, NUL, malformed encoding, excessive depth/length, and unknown manifest entries before I/O;
3. open/validate the root and each component using a real macOS mechanism that prevents or detects symlink substitution and root escape;
4. reject symlinks unless a separately synchronized root policy explicitly resolves one fixed owner-approved root before the operation; file-level symlinks remain rejected by default;
5. require an expected owner and allowed mode, and reject unsafe type, device, socket, directory, or unexpected hard-link policy;
6. enforce a per-manifest byte limit, total request byte limit, read deadline, and regular-file identity check before and after reading;
7. enforce the synchronized metadata-access-time side-effect policy; if reading would mutate provider metadata and no approved non-mutating mechanism exists, return `unsupported_side_effect_policy` rather than read;
8. return bytes only to the owning approved provider parser in an `EphemeralApprovedFileV1`-equivalent in-memory wrapper, never to logs, diagnostics, evidence, database, API, or UI;
9. discard bytes on any identity/size/type/owner/race conflict and return a safe typed error;
10. avoid directory recursion and glob expansion unless a future specific manifest and threat review approve them.

Whether Python/macOS exposes adequate descriptor-relative and no-follow primitives is a discovery question. A lexical `resolve()`/prefix comparison alone is insufficient evidence against time-of-check/time-of-use attacks.

The ephemeral wrapper carries an explicit length, safe file identity metadata, one owning parser consumer, a redacted representation, and immediate disposal semantics. Python cannot guarantee physical memory erasure; the implementation minimizes lifetime and copies and does not make a false secure-deletion claim. A composition-issued `FilesystemAccessGrantV1` binds the exact root/file-spec versions, provider adapter, correlation ID, expiry/deadline, and byte limit. It cannot originate from HTTP and becomes invalid when a registry/spec version changes.

### 3.7 Native directory resolution

AgentMonitor directory categories are configuration, data, state, cache, logs, backups, exports, and AgentMonitor-managed provider profiles. A04-MAC maps categories to native user locations selected by DEP/configuration policy. It does not copy Linux XDG values or infer locations from a provider process environment.

Requirements for the mapping:

- explicit owner UID and user-domain context;
- no root/system location in V1;
- deterministic category result for a given approved configuration;
- owner-only permission target where supported;
- no automatic creation in a read-only resolution operation;
- safe handling of missing, inaccessible, symlinked, relocated, or non-directory targets;
- configuration override only through CTR-CONFIG-001 with root-boundary validation;
- no home/user/path value in logs or general diagnostics.

Exact native paths remain a DEP/A04-MAC synchronization decision and are not allocated by this draft.

### 3.8 User launchd model

CTR-DEP-001 owns lifecycle intent; A04-MAC maps it to the selected real user launchd interface. The proposed constraints are:

- only AgentMonitor's own stable service identifier in the current user's approved launchd domain;
- no LaunchDaemon, root, `sudo`, privileged helper, or manipulation of provider service definitions;
- deployment owns the plist/template and installation transaction; A04-MAC validates and invokes the native primitive;
- program plus argument vector only; no shell, redirection, command substitution, or secret argument;
- explicit executable, working, data, state, and log destinations approved by DEP;
- no secret values in the service definition; application loads its protected configuration through the approved mechanism;
- login/autostart, restart/backoff, stdout/stderr, resource limit, and exit semantics are selected only after real launchd verification;
- status is based on verified launchd/application-health evidence, not PID existence alone;
- raw service-manager output is never retained or logged because it may contain environment/path details;
- an allowlist parser extracts only service label, safe state, process ID when needed, last exit classification, source version, and bounded diagnostic codes proven safe;
- service stop/restart targets AgentMonitor only and cannot reach provider agents.

Exact `launchctl` subcommands, user-domain identifiers, plist keys, and output fields are discovery outputs. This plan deliberately does not invent commands.

### 3.9 Platform diagnostics and health

Safe diagnostics may include:

- adapter/contract version;
- supported/actual OS product-version compatibility class and architecture class;
- selected process/filesystem/service source identifiers and stability classes;
- capability state: supported, permission-limited, unavailable, unverified version, or unsupported;
- last successful operation time/duration, bounded race/permission/error counts, and safe error codes;
- launchd driver availability and AgentMonitor service state through the approved projection;
- owner-directory permission compliance as a boolean/category, not path/mode dump;
- evidence status for required T5 scenarios.

Diagnostics exclude username, host name, hardware serial, account identity, complete OS report, raw paths, provider filenames beyond approved structural labels, process arguments/environment, raw command output, file content, credentials, and source content.

## 4. Public contracts

### 4.1 CTR-RUN-006 — `ProcessInspectionPortV1`

M06 owns normalized runtime meaning; A04 Linux/macOS implement the port. Proposed operations are:

```text
InspectProcessesV1(PlatformInspectionRequestV1)
  -> PlatformInspectionOutcomeV1
```

`PlatformInspectionRequestV1` contains contract version, operation/correlation IDs, `platform_source=macos`, approved provider-installation/selector IDs, deadline, maximum candidate/result counts, requested field IDs, and contract/source version constraints. It contains no account credential, process environment request, arbitrary executable name, arbitrary PID list from HTTP, path from the browser, shell command, or control instruction.

`PlatformInspectionOutcomeV1` uses the same portable outcome vocabulary as Linux: `success`, `partial`, `unsupported`, `permission_denied`, `source_unavailable`, `unverified_platform_version`, `deadline_exceeded`, `invalid_request`, `invalid_platform_data`, or `internal_adapter_error`. Per-process/field outcomes preserve `process_disappeared`, `process_changed_during_inspection`, PID reuse/identity conflict, `parent_unresolved`, `field_unsupported`, and `field_unavailable` without failing unrelated records. Mac-native causes are translated into this vocabulary; they do not create incompatible public meanings.

Every returned process record includes:

- platform-instance/boot scope and positive PID;
- required validated start and executable identity or an explicit one-shot unresolved record;
- parent PID candidate and validated parent identity when available;
- typed state/CPU/memory/CWD fields;
- observation interval and provenance;
- source/adapter/OS version compatibility state;
- safe warnings and no raw output.

Idempotency is observational: repeating a request may return different real state. The operation is read-only and never promises identical data. Cancellation/deadline must not leave helper processes or retained output.

### 4.2 CTR-PLAT-001 — macOS implementation of `PortablePlatformPrimitivesV1`

A04-MAC implements these FND-owned portable contract families on macOS; it may
propose changes only through PLAN-FND producer review:

- `PlatformCompatibilityV1` — OS product/build/architecture classes, selected-source IDs, verified version range, and capability states;
- `NativeDirectoryQueryV1` / `NativeDirectoryResultV1` — category-based native path reference and permission policy, no side effect;
- `ApprovedRootHandleV1` — opaque root identity plus policy/version, never serialized to public API;
- `ApprovedMetadataReadRequestV1` / `ApprovedMetadataReadOutcomeV1` — manifest relative path, byte/deadline/type/owner limits, safe error union;
- `PlatformDiagnosticSummaryV1` — bounded allowlisted health/capability facts;
- `MacUserServiceDriverV1` — internal adapter consumed by DEP, not a public control API.

Proposed operations align one-for-one with the Linux portable semantics while retaining macOS-specific result types only where the platform fact is genuinely different:

- `GetMacOSCapabilityProfileV1(CapabilityProfileQueryV1) -> MacOSCapabilityProfileV1`;
- `ResolveAgentMonitorPathsV1(AgentMonitorPathQueryV1) -> AgentMonitorPathSetV1`;
- `DiscoverApprovedRootsV1(ApprovedRootDiscoveryRequestV1) -> ApprovedRootDiscoveryOutcomeV1`;
- `InspectApprovedPathV1(ApprovedPathInspectionRequestV1) -> ApprovedPathMetadataOutcomeV1`;
- `ReadApprovedRegularFileV1(ApprovedFileReadRequestV1) -> ApprovedFileReadOutcomeV1`;
- `InspectAgentMonitorUserServiceV1(UserServiceInspectionRequestV1) -> UserServiceInspectionOutcomeV1`;
- `GetMacOSPlatformHealthV1(PlatformHealthQueryV1) -> PlatformHealthViewV1`.

The common request shapes use version, operation/correlation ID, approved selector/root/file/access-grant identifiers, deadlines, and hard bounds. No operation accepts an arbitrary absolute path, service label, shell command, PID list from HTTP, environment-field name, credential, or provider process-control intent.

The file-read payload is sensitive ephemeral data. It is delivered only in-process to the authorized provider adapter call and must not be placed in a generic event, queue, persistence object, trace, exception, or diagnostic. This exception does not authorize content-bearing/provider-secret files; A01–A03 must provide an approved file/field classification first.

### 4.3 CTR-DEP-001 constraints consumed; no A04 implementation

DEP remains the sole producer and lifecycle implementation owner. A04-MAC does
not expose CTR-DEP-001 commands; DEP composes A04-MAC's CTR-PLAT-001 primitives
for:

- validate user-service target;
- install/replace/remove mapping as an explicitly authorized DEP operation;
- start/stop/restart AgentMonitor service;
- enable/disable or bootstrap/bootout mapping as selected by real launchd evidence;
- query safe service status;
- collect sanitized service diagnostics.

Installation/removal/restart are PLAN-DEP state-changing workflows, not A04
operations or discovery. They require an approved deployment plan, exact target
validation, canonical `AUTO-DEPLOY`, and owner authority where the runbook
requires it. Process-observation flows never invoke lifecycle behavior.

### 4.4 Consumed contract behavior

| Contract | Owner | A04-MAC use | Failure/degradation |
|---|---|---|---|
| CTR-COMMON-001/002/004/007 | foundation/M03 | opaque IDs, UTC/durations, provenance, exact field availability | reject incompatible major; no partial guessed conversion or missing-as-zero |
| CTR-FND-003/CTR-CONFIG-001 | foundation/setting owners | typed non-secret settings and approved references | invalid/missing setting disables capability or readiness as classified |
| CTR-FND-004 | foundation | correlation and safe logging envelope | operation may run with generated valid context; never logs raw data |
| CTR-FND-008 | test steward | truthful boundary/status evidence | missing real Mac reports Blocked |
| CTR-REG-004 | M02 | approved provider installations/executable/profile-root references | unknown installation is unclassified; no scan-all fallback |
| CTR-PROV-002/003 | M03 | approved source/capability/stability declaration | unsupported/unverified disables source |
| CTR-RUN-006 | M06 | required process semantics implemented by A04-MAC | semantic/version conflict stops implementation |
| CTR-OPS-006 | M08 | publish bounded component health | M08 timeout cannot affect inspection |
| CTR-DEP-001 | DEP | fixed AgentMonitor lifecycle target/intent consumed by DEP composition | A04 exposes no deployment lifecycle command |

### 4.5 Error vocabulary

Stable safe categories include:

- `unsupported_os_version`;
- `unsupported_architecture`;
- `unverified_platform_source`;
- `platform_source_unavailable`;
- `permission_denied`;
- `process_disappeared`;
- `process_changed_during_inspection`;
- `process_identity_conflict`;
- `parent_unresolved`;
- `deadline_exceeded`;
- `inspection_limit_reached`;
- `invalid_request`;
- `invalid_platform_data`;
- `invalid_approved_root`;
- `path_not_allowlisted`;
- `path_escape_rejected`;
- `symlink_rejected`;
- `file_type_rejected`;
- `file_owner_or_mode_rejected`;
- `file_size_limit_exceeded`;
- `file_identity_changed`;
- `service_source_unavailable`;
- `service_definition_rejected`;
- `service_operation_conflict`;
- `sanitized_internal_error`.

Errors include correlation ID, operation category, safe subject reference, source version, timestamps/duration, and retriable classification where synchronized. They exclude raw path, command/output, environment, file content, user name, provider identity, and exception payload. Authentication/permission errors are not blindly retried.

### 4.6 Compatibility promise and impact

- This plan adds macOS implementations of M06-owned CTR-RUN-006 and FND-owned
  CTR-PLAT-001 only; it does not approve, produce, or version shared semantics.
- PID/start identity, CPU normalization, memory kind, path disclosure, file-read security, service action semantics, and error meanings are compatibility-significant.
- A change to unit, start-identity scope, field privacy, service target, or side-effect class is breaking and requires contract review, consumer migration, and an ADR where required.
- Additive optional fields are compatible only with explicit unsupported/unknown handling.
- OS-version range expansion requires real verification on the added version before capability manifests change.
- macOS cannot narrow cross-platform meaning to what one native API happens to expose.

## 5. Data and persistence

A04-MAC owns no persistent data and no migration. It returns typed observations to M06, safe component health to M08, and service results to DEP. Those owners persist only their approved projections.

The adapter may hold bounded in-memory operation state:

- request/correlation ID;
- monotonic deadline and sampling window;
- candidate PID set;
- process identities and field outcomes for the active request;
- approved-root file descriptors/handles and byte buffers for the active read;
- bounded sanitized counters.

All sensitive path/file buffers and native command output are discarded at operation end. They cannot enter an event, cache, retry queue, crash report, test artifact, or database. OS facilities may maintain their own state; A04-MAC does not duplicate it.

## 6. External and platform boundaries

### 6.1 Process-source selection gate

M0-MAC discovery must compare only legitimate real macOS mechanisms, preferring public documented native APIs. For each candidate, record:

- upstream owner/documentation and stability;
- supported macOS versions/architectures;
- exact fields and units;
- permissions/TCC/SIP behavior under a normal user;
- race/PID-reuse behavior;
- output/data exposure;
- Python binding/dependency/ABI needs;
- performance at expected and 200-process load;
- side effects and stop conditions.

Candidates might include public system APIs, built-in read-only tools, or an admitted maintained library, but this plan approves none. Undocumented kernel layouts, private frameworks, debugger/attachment APIs, and parsing locale-dependent human output are rejected unless a later explicit architecture/security decision changes scope.

### 6.2 Filesystem boundary

Real tests use isolated AgentMonitor-owned directories/files for destructive or adversarial cases. Provider-owned roots are inspected only through a separately approved read-only packet and are never modified to manufacture permissions, symlinks, races, or sizes. Adversarial symlink/replace/permission scenarios target only temporary AgentMonitor-owned resources on the real Mac.

### 6.3 launchd boundary

Real lifecycle tests use the actual current-user launchd service mechanism and an AgentMonitor-owned service definition/artifact. They do not touch provider services. Exact state-changing steps wait for PLAN-DEP approval and an isolated target. Raw native output is treated as potentially sensitive and sanitized at source.

### 6.4 Platform/version support policy

The first supported macOS product versions and architectures are unresolved. Approval requires:

- owner-selected minimum/current product-version policy;
- at least one real primary development Mac;
- evidence for every selected process/filesystem/launchd source;
- explicit architecture coverage (for example, Apple silicon and/or Intel) rather than inference;
- behavior under normal user permissions;
- compatibility record for provider CLI architectures and any translation layer;
- declared `supported`, `unverified`, and `unsupported` ranges.

An unverified newer OS reports `unverified_platform_version` and disables unsafe parsing/ABI paths. It is not silently accepted because version ordering looks compatible.

### 6.5 Timeouts and output bounds

Exact defaults remain configuration decisions after measurement, but every operation requires:

- caller deadline and adapter hard maximum;
- per-PID/per-file/per-service sub-budget;
- candidate process count, file bytes, relative-path depth, service-output bytes, and diagnostic item bounds;
- cancellation propagation and helper cleanup;
- partial-result accounting;
- no indefinite wait and no automatic retry loop.

Deadline expiry never changes provider or AgentMonitor service state beyond an already authorized lifecycle operation whose result must be reconciled explicitly.

## 7. Security and privacy

### 7.1 Trust boundaries and threats

Untrusted inputs include process-table churn, filesystem names/metadata, provider-created files, symlinks, service-manager output, OS/version changes, configuration references, and dependency/native-library behavior. Controls are closed schemas, bounds, root/owner/type checks, start-identity validation, source compatibility checks, safe error mapping, and no raw-output persistence.

### 7.2 Least privilege

- Run as the normal dashboard owner, never root.
- Request no Full Disk Access, Accessibility, automation, screen recording, developer/debug entitlement, privileged helper, or kernel extension for V1.
- If a required fact is inaccessible, return permission-limited/unsupported and surface the limitation.
- Never weaken provider or AgentMonitor file permissions automatically.
- Never change TCC, SIP, Gatekeeper, login-item, quarantine, code-signing, or provider configuration.

### 7.3 Prohibited API surface proof

The source, contracts, dependency graph, and native symbol/command allowlist must prove absence of:

- environment/arguments/memory/terminal/content readers;
- debug/attach/tracing/injection mechanisms;
- signal/kill/suspend/resume/set-priority/provider-service control;
- shell command construction;
- arbitrary path/file read endpoints;
- network clients or outbound analytics owned by A04-MAC;
- generic raw native output/error passthrough.

### 7.4 Secrets and content

The adapter never reads `.env`, provider credential files, keychains, cookies, tokens, passwords, OTPs, prompts, responses, tools, source files, or terminal buffers. If an approved metadata file unexpectedly contains a secret/content/unknown field, the provider parser stop rule applies: discard/quarantine the in-memory output, emit only a safe incident code, and stop the capability. No contaminated bytes enter chat or committed evidence.

### 7.5 Logging and evidence

Logs use correlation ID, component, operation class, adapter/source version, safe status/error, duration, and counts. They omit raw PIDs when not operationally necessary and always omit raw paths/output/content. Live reports use an opaque Mac alias, OS product/build class, architecture, adapter/source versions, UTC times, scenario result, safe comparison summary, and external evidence reference.

## 8. Configuration and operations

### 8.1 Proposed configuration categories

Exact external keys are **not allocated** until CTR-CONFIG-001 synchronization. A04-MAC needs typed owner-approved entries for:

| Category | Type/validation | Secret | Default/reload proposal |
|---|---|---|---|
| platform source selection | closed source ID/auto only among verified sources | no | verified auto; restart |
| total inspection timeout | bounded duration | no | measured later; runtime reload via M04 policy if owned there |
| per-process timeout | bounded duration less than total | no | measured later |
| maximum enumerated processes | positive bounded count, at least product target | no | measured later |
| file-read byte/depth/time bounds | positive per-manifest limits | no | conservative; restart/manifest reload |
| approved native directories | typed category references, root validated | path-sensitive | native defaults; restart |
| service identifier/domain | DEP-owned stable identifier/closed user domain | no | no operator free-form override |
| diagnostics detail | closed safe level | no | safe default; reloadable |

Provider/profile roots are registry-owned opaque references, not environment variables. No configuration enables prohibited process fields or bypasses path checks. Secret configuration is never required by the platform adapter itself.

### 8.2 Health/readiness

`MacPlatformHealthV1` reports:

- contract/adapter/source compatibility;
- OS/architecture support state;
- process, safe-file, native-directory, launchd, and diagnostics capability state;
- last successful/failed operation times and safe codes;
- bounded race/permission/deadline counters;
- real-macOS verification state by required scenario family.

The application may remain ready when one observation capability is permission-limited, but that capability is degraded and data becomes unavailable/stale. Incompatible contract/OS/source, unsafe path primitive, or invalid service target fails the affected readiness requirement. M08 defines application-wide aggregation.

### 8.3 Operator/runbook obligations

Verified macOS documentation must cover:

- compatibility preflight;
- native directory and permission diagnosis;
- missing/stale process fields and normal permission limitations;
- PID race/reuse and parent ambiguity diagnosis;
- approved-root/path rejection diagnosis without exposing paths;
- AgentMonitor user-service install/start/stop/restart/status/autostart through canonical DEP automation;
- browser-closed collection confirmation;
- service failure and rollback/recovery;
- version/source incompatibility;
- privacy/secret incident handling;
- how Blocked macOS scenarios remain visible.

No command is added to an operator runbook until it exists in repository automation and is exercised on the real supported Mac.

### 8.4 Canonical automation obligations

A04-MAC registers with repository-owned routines; it does not create personal shell recipes:

- `AUTO-PLAN-CHECK`: plan sections, scenario count, contract/status/link synchronization.
- `AUTO-DOCS-CHECK`: requirements/contracts/scenarios/compatibility/runbook links and prohibited-value scans.
- `AUTO-TEST`: explicit A04-MAC pure/contract/T5/security/service selectors with Passed/Failed/Blocked/Not Run separation.
- `AUTO-QUALITY`: format/type/import-boundary/security/secret/prohibited-double/dependency/license/native-symbol/command allowlist checks.
- `AUTO-GIT-PREFLIGHT`: normal shared repository preflight; the adapter adds no special Git behavior.
- `AUTO-BUILD`: reproducible macOS artifact/source compatibility metadata after dependency admission.
- `AUTO-DEPLOY`: DEP-owned, fail-closed AgentMonitor launchd lifecycle with exact-target validation and rollback.
- `AUTO-RELEASE`: macOS evidence matrix and known limitations; cannot report macOS verified while T5 rows are Blocked.

The real-macOS selector returns a structured Blocked result and non-success-for-claim status when no supported Mac is available. It never skips to green. The deterministic selector can pass independently but must identify its narrower boundary.

## 9. Test design before implementation

### 9.1 Evidence status and Red/Green rule

Pure/contract/static scenarios are currently **Not Run**. Real-macOS T5/T7 scenarios are **Blocked by missing real supported Mac**. No test or implementation is authorized by this plan.

For each future increment:

1. write and run the smallest scenario at its actual boundary;
2. record a behavioral Red caused by missing/incorrect behavior, never missing dependencies or platform access;
3. implement minimum Green;
4. refactor with the same real boundary green;
5. retain sanitized command, timestamp, environment, result, and status evidence.

When the real Mac is absent, the T5 scenario remains Blocked; it cannot provide Red. Pure/contract work may proceed only under the conditional track in section 10.

### 9.2 Pure and contract scenarios

These scenarios construct only closed typed values and perform no process/filesystem/service/environment I/O.

| Test ID | Layer | Requirement | Expected behavioral Red | Green pass condition | Current state |
|---|---|---|---|---|---|
| MAC-PURE-001 | T1 | FR-DISC-002 | PID-only identity compares stable | missing start/executable identity cannot form stable process key | Not Run |
| MAC-PURE-002 | T1 | FR-DISC-002 | changed start identity merges optional fields | identity change yields race/conflict outcome | Not Run |
| MAC-PURE-003 | T1 | FR-DISC-002 | missing CPU/memory becomes zero | closed unavailable state retains unit/source semantics | Not Run |
| MAC-PURE-004 | T1 | FR-DISC-002 | incompatible CPU meanings aggregate | measurement kind/window/normalization mismatch is rejected | Not Run |
| MAC-PURE-005 | T1 | FR-DISC-005 | parent PID alone creates validated parent | parent identity remains unresolved without start evidence | Not Run |
| MAC-PURE-006 | T1 | NFR-COMP-001 | unknown raw process state maps to a known state | becomes explicit unknown with safe reason | Not Run |
| MAC-PURE-007 | T1 | NFR-SEC-001 | lexical path accepts absolute/dot-dot/NUL/depth overflow | all invalid relative tokens fail before I/O | Not Run |
| MAC-PURE-008 | T1 | NFR-SEC-001 | deadline/count/byte bounds permit invalid combinations | configuration policy fails closed | Not Run |
| MAC-CONTRACT-001 | contract | NFR-COMP-001 | incompatible CTR-RUN-006 major is accepted | compatibility negotiation rejects it safely | Not Run |
| MAC-CONTRACT-002 | contract | NFR-PLAT-001 | Linux-only field becomes required | common contract permits macOS unsupported field state | Not Run |
| MAC-CONTRACT-003 | contract | FR-DISC-004 | platform result contains account decision | schema permits evidence only and rejects account inference | Not Run |
| MAC-CONTRACT-004 | contract | FR-DISC-008 | result omits adapter/source/OS provenance | closed schema rejects missing required provenance | Not Run |
| MAC-CONTRACT-005 | contract | FR-SAFE-002 | process port exposes signal/control operation | public schema/port surface contains observation only | Not Run |

### 9.3 Real macOS process scenarios (T5)

Every row requires the actual selected supported Mac and production adapter. Generic process mechanics use an AgentMonitor-owned harmless real process only where stated. Provider claims require real owner-identified Claude/Codex/Ollama processes.

| Test ID | Requirement/AC | Real dependency | Expected behavioral Red | Green pass condition | Current state |
|---|---|---|---|---|---|
| MAC-PROC-001 | FR-DISC-001 | real Claude/Codex/Ollama process | supported process missed or launch disturbed | process discovered read-only with owner reconciliation | Blocked |
| MAC-PROC-002 | FR-DISC-001 | real provider process set | unrelated same-name process misclassified | only approved installation evidence is returned/classified | Blocked |
| MAC-PROC-003 | FR-DISC-002 | real normal-user process | PID lacks validated start identity | source provides synchronized PID/start/executable tuple | Blocked |
| MAC-PROC-004 | FR-DISC-002 | real process lifecycle | PID reuse merges two lifetimes | re-used PID remains distinct or race outcome | Blocked |
| MAC-PROC-005 | FR-DISC-002 | short-lived owned process | exit during inspection creates current row | typed disappeared outcome, no stale merge | Blocked |
| MAC-PROC-006 | NFR-RES-001 | mix of readable/denied processes | one denial aborts enumeration | denied record is partial; unrelated records return | Blocked |
| MAC-PROC-007 | NFR-RES-001 | real churn | one race crashes/poisons request | bounded partial outcome and continued service | Blocked |
| MAC-PROC-008 | FR-DISC-002 | real process + independent system view | CPU/memory units or semantics differ | values reconcile within documented precision/interval | Blocked |
| MAC-PROC-009 | FR-DISC-005; AC-PROC-002 | real parent/child provider tree | parent PID becomes false edge | validated identity/interval or visible unresolved result | Blocked |
| MAC-PROC-010 | FR-DISC-005 | reparenting/parent exit on owned processes | obsolete parent retained as current | race/reparent state represented truthfully | Blocked |
| MAC-PROC-011 | FR-DISC-002 | permitted and denied CWD cases | path guessed/leaked or denial becomes empty | approved representation or typed denial only | Blocked |
| MAC-PROC-012 | FR-DISC-002 | new/unsupported raw state if naturally available | state silently coerced | unknown safe mapping without raw leakage | Blocked |
| MAC-PROC-013 | FR-DISC-004; AC-PROC-003 | real process/session evidence | adapter chooses account/session from weak evidence | evidence forwarded; M06 remains unresolved | Blocked |
| MAC-PROC-014 | NFR-PERF-001 | approved real 200-process workload | deadline/resource budget exceeded | measured synchronized budget met or target visibly failed | Blocked |

### 9.4 Real macOS filesystem scenarios (T5)

Adversarial writes use only isolated AgentMonitor-owned temporary roots. Provider roots remain read-only.

| Test ID | Requirement | Real dependency | Expected behavioral Red | Green pass condition | Current state |
|---|---|---|---|---|---|
| MAC-FS-001 | NFR-PLAT-001 | real native user directories | Linux/XDG path leaks into result | native category maps per synchronized macOS policy | Blocked |
| MAC-FS-002 | NFR-SEC-001 | owned regular file | approved bounded read unavailable | exact allowed file read within limits and discarded | Blocked |
| MAC-FS-003 | NFR-SEC-001 | owned escape symlink | file outside root is read | escape rejected without opening/returning content | Blocked |
| MAC-FS-004 | NFR-SEC-001 | owned in-root symlink | file symlink accepted by default | symlink rejected with safe code | Blocked |
| MAC-FS-005 | NFR-SEC-001 | owned replace race | check/read swap returns attacker bytes | identity change detected and bytes discarded | Blocked |
| MAC-FS-006 | NFR-SEC-001 | owned directory/device/socket cases | non-regular target read | every disallowed type rejected | Blocked |
| MAC-FS-007 | NFR-SEC-001 | wrong owner/unsafe mode owned setup | unsafe file accepted | owner/mode policy rejects it | Blocked |
| MAC-FS-008 | NFR-RES-001 | one denied plus one valid file | denial aborts unrelated capability | scoped failure; valid operation remains usable | Blocked |
| MAC-FS-009 | NFR-SEC-001 | file above size/deadline bound | unbounded read/output | operation stops, discards bytes, reports bound | Blocked |
| MAC-FS-010 | FR-DISC-003 | approved provider metadata path | provider read mutates metadata/state | approved pre/post metadata proves read-only; no raw bytes retained | Blocked |

### 9.5 Real macOS launchd scenarios (T5/T7)

These use only an approved AgentMonitor-owned user service after DEP authorizes state-changing lifecycle tests.

| Test ID | Requirement/AC | Real dependency | Expected behavioral Red | Green pass condition | Current state |
|---|---|---|---|---|---|
| MAC-SVC-001 | FR-OPS-001 | real user launchd | service targets system/root domain | current-user domain enforced | Blocked |
| MAC-SVC-002 | FR-OPS-001 | real service definition | shell or secret argument is accepted | fixed vector and secret-free validated definition | Blocked |
| MAC-SVC-003 | FR-OPS-001 | real service artifact | install target/path/owner unsafe | exact AgentMonitor target and permissions enforced | Blocked |
| MAC-SVC-004 | FR-OPS-001 | real user service | start reports success from PID only | launchd plus application readiness reconciled | Blocked |
| MAC-SVC-005 | FR-OPS-001 | real user service | stop affects unrelated/provider process | only exact AgentMonitor service stops | Blocked |
| MAC-SVC-006 | FR-OPS-001 | real user login lifecycle | autostart semantics differ/missing | approved login behavior observed and recorded | Blocked |
| MAC-SVC-007 | AC-OPS-002 | real installed service/browser | closing browser stops collection | service/collection continue and reopen recovers view | Blocked |
| MAC-SVC-008 | NFR-RES-001 | real unexpected app exit | unbounded restart storm or silent death | verified bounded launchd/application recovery behavior | Blocked |
| MAC-SVC-009 | FR-OPS-002 | real service status | raw output or PID existence equals health | allowlisted status plus app health is truthful | Blocked |
| MAC-SVC-010 | AC-OPS-005 | isolated failed upgrade/config | recovery destroys config/data | DEP rollback preserves state and restores readiness | Blocked |
| MAC-SVC-011 | FR-OPS-005 | real plist/log/status artifacts | secret/path/environment leaks | automated scan and review find only allowlisted fields | Blocked |
| MAC-SVC-012 | AC-OPS-003 | service plus failed platform source | source failure takes down API/service | component degrades; service/API remain available | Blocked |

### 9.6 Diagnostics, security, architecture, and automation scenarios

| Test ID | Layer | Requirement | Expected behavioral Red | Green pass condition | Current state |
|---|---|---|---|---|---|
| MAC-DIAG-001 | T5 | FR-OPS-006 | OS/adapter/source version absent or misreported | real safe version facts reconcile | Blocked |
| MAC-DIAG-002 | T5 | FR-OPS-002 | unsupported OS appears healthy | compatibility state is explicit and capability disabled | Blocked |
| MAC-DIAG-003 | T5 | FR-OPS-002 | permission denial appears as source outage | distinct permission-limited state | Blocked |
| MAC-DIAG-004 | T5 | NFR-OBS-001 | raw paths/output appear in diagnostic | only allowlisted safe fields remain | Blocked |
| MAC-DIAG-005 | T7 | AC-OPS-003 | degraded capability makes entire app unready | scoped degradation follows M08 policy | Blocked |
| MAC-SEC-001 | security | FR-DISC-007 | source/import scan finds environment reader | no arbitrary environment capability exists | Not Run |
| MAC-SEC-002 | T5 security | FR-DISC-007 | real inspection accesses environment/args | trace/review proves only approved sources/fields | Blocked |
| MAC-SEC-003 | real artifact | NFR-OBS-001 | log/error contains raw native output/path/content | allowlist scan is clean | Blocked |
| MAC-SEC-004 | real artifact | FR-OPS-005 | service/diagnostic evidence contains secret/content | scanner and manual review are clean | Blocked |
| MAC-SEC-005 | static/contract | NFR-PRIV-001 | payload schema permits generic/raw content | closed schemas reject it | Not Run |
| MAC-SEC-006 | T5 live | FR-SAFE-002 | observation changes/signals target/provider state | approved pre/post checks prove no control/mutation | Blocked |
| MAC-SEC-007 | static/native allowlist | FR-SAFE-002 | control/attach/debug symbol or command admitted | allowlist gate rejects prohibited surface | Not Run |
| MAC-SEC-008 | dependency/network | NFR-PRIV-002 | adapter dependency sends telemetry/network data | no A04-MAC outbound telemetry/network behavior | Not Run |
| MAC-ARCH-001 | quality | NFR-ARCH-001 | mac adapter imports domain/module internals | canonical boundary check rejects import | Not Run |
| MAC-ARCH-002 | quality | NFR-PLAT-001 | Linux/systemd/XDG implementation leaks into macOS/core | platform-neutral contracts and isolated adapters only | Not Run |
| MAC-ARCH-003 | ownership | NFR-ARCH-002 | A04-MAC writes table/migration/provider parser | ownership gate rejects change | Not Run |
| MAC-AUTO-001 | automation | AC-TEST-006 | absent Mac is hidden as pass/skip | canonical report emits Blocked and claim gate fails | Not Run |
| MAC-AUTO-002 | test integrity | AC-TEST-002 | mock/emulator/recording framework is accepted | prohibited-substitute scan/review fails closed | Not Run |
| MAC-AUTO-003 | evidence | AC-TEST-001/004 | report lacks RGR/boundary/version/status | schema requires complete sanitized record | Not Run |
| MAC-PERF-001 | T5 performance | NFR-PERF-001 | 200-process inspection is unbounded | measured deadline/resource/output budget met | Blocked |
| MAC-DOC-001 | documentation | NFR-DOC-001 | links/IDs/status/runbook drift | canonical docs/planning gate passes | Not Run |
| MAC-DEP-001 | dependency | NFR-LIC-001 | unreviewed package/native binary enters lock/build | admission, SBOM/notices/security/license gate passes | Not Run |

### 9.7 Test integrity

- No mock, fake, stub, monkeypatch, emulator, compatibility layer, recorded/replayed output, provider fixture, demo process, seeded telemetry, or test-only production branch may prove a macOS boundary.
- Pure tests use constructed closed values only and claim only deterministic policy/contract behavior.
- Real process tests use actual production adapter code and real processes on the supported Mac.
- Adversarial filesystem/service tests use isolated AgentMonitor-owned resources and production code.
- Provider tests use current real provider processes and approved read-only metadata; unavailable conditions remain Blocked.
- Platform logs/evidence are allowlist sanitized at source.
- No auto-retry converts a flaky/racy failure into a pass.
- Passed, Failed, Blocked, and Not Run are reported separately by the canonical command.

## 10. Implementation increments and gates

### 10.1 Gate sequence

| Gate | Required evidence | Enables | Does not enable |
|---|---|---|---|
| MAC-G0 plan synchronization | A04 Linux/M06/DEP/M08/security review of this plan and shared semantics | approval decision | code, dependency, Mac access |
| MAC-G1 real-Mac assignment | exact owner-approved Mac alias, OS/build/arch, evidence root, no-install inventory | read-only discovery packet preparation | commands or writes |
| MAC-G2 source discovery | approved exact read-only commands/APIs and safe evidence for process/path/launchd sources | source/dependency decision | production implementation |
| MAC-G3 contract freeze | CTR-RUN-006/CTR-PLAT-001/CTR-DEP-001 synchronized; units/errors/config fixed | contract/pure implementation packet | platform I/O without tests |
| MAC-G4 dependency admission | selected library/tool/source license/security/maintenance/transitive/ABI review | lock/build change if separately authorized | install by this plan |
| MAC-G5 real T5 harness | canonical selector runs production boundary and reports truthful states | platform Red-Green loops | provider mutation/control |
| MAC-G6 platform verification | required process/filesystem/service/security rows Passed on supported Mac | integration/release review | Linux acceptance credit |

### 10.2 Conditional work tracks

**Track C — contract/pure work** may begin only after MAC-G3 and normal implementation approval. It includes closed DTOs, error enums, compatibility negotiation, lexical relative-path policy, measurement conversion policies, evidence reporting, and import/ownership rules. It must not contain a syscall, platform command, filesystem read, launchd call, or “temporary” Linux-backed implementation.

**Track P — platform implementation** is blocked until MAC-G1 through MAC-G5 are green. It includes every actual process, filesystem, native-directory, launchd, permission, and OS diagnostic source. Cross-compiling or authoring it on Linux without an executable real-Mac Red test is prohibited.

**Track I — provider/application integration** follows Track P evidence and requires real provider processes, M06/DEP/M08 consumers, and owner coordination. It cannot be replaced by AgentMonitor-owned generic processes.

### 10.3 Increments

| Increment | Track/owned area | Failing scenarios first | Minimum Green outcome | Exit evidence |
|---|---|---|---|---|
| MAC-I00 | C automation/contract registration | MAC-AUTO-001..003, MAC-ARCH-001..003 | selectors/status schema/boundaries registered; no platform behavior | deterministic RGR evidence |
| MAC-I01 | C common process values | MAC-PURE-001..006, MAC-CONTRACT-001..004 | closed identity/field/measurement/provenance policies | pure RGR + mutation review |
| MAC-I02 | C path/request policy | MAC-PURE-007/008, MAC-CONTRACT-005, MAC-SEC-005/007 | closed lexical/limit/no-control schemas | pure/static RGR |
| MAC-I03 | P compatibility/source probe | MAC-DIAG-001..003 | real verified OS/arch/source capability result | real Mac RGR |
| MAC-I04 | P process identity/enumeration | MAC-PROC-001..007 | bounded real enumeration and PID/start/executable race safety | real Mac/process RGR |
| MAC-I05 | P process fields/ancestry | MAC-PROC-008..013 | truthful units/field outcomes/parent evidence | real Mac/provider RGR |
| MAC-I06 | P approved roots/safe reads | MAC-FS-001..010 | race-resistant bounded root/file primitive | real filesystem RGR/security review |
| MAC-I07 | P diagnostics/health | MAC-DIAG-004/005, MAC-SEC-002/003/008 | safe health and no prohibited output/network behavior | real service/artifact evidence |
| MAC-I08 | P launchd driver | MAC-SVC-001..006/008/009/011 | exact AgentMonitor user-service lifecycle mapping | real launchd RGR; DEP review |
| MAC-I09 | I application lifecycle | MAC-SVC-007/010/012 | browser-independent collection, recovery, failure isolation | real installed stack evidence |
| MAC-I10 | I performance/provider hardening | MAC-PROC-014, MAC-PERF-001, MAC-SEC-004/006 | measured bounds and no-control/no-leak proof | owner-coordinated T5 report |
| MAC-I11 | I docs/release evidence | MAC-DOC-001, MAC-DEP-001 | verified runbook, compatibility matrix, dependency evidence | canonical gates |

### 10.4 Parallel safety

After MAC-G3, I01 and I02 can proceed in separate owned files. I03 determines
the real source and blocks I04–I08. Process and filesystem implementations may
proceed in parallel only if they share no native wrapper, dependency,
configuration source, or output type. CTR-PLAT-001 fixed-service primitives can
proceed separately after DEP freezes the CTR-DEP-001 constraints it will supply,
but shared build/lock/config files remain centrally assigned. Integration and
hardening serialize through the A04-MAC owner.

### 10.5 Stop conditions

Stop and return to discovery/contract/security review when:

- the assigned environment is not a real supported Mac or cannot expose the claimed boundary;
- selected API/command is private, undocumented, unstable, locale-dependent, privileged, or different from approved evidence;
- a process fact requires environment, arguments, memory, attach/debug/tracing, terminal access, signal, or control;
- safe CWD/executable identity requires broader path disclosure than synchronized;
- provider metadata needs arbitrary traversal, raw content persistence, credential/keychain access, or symlink weakening;
- a launchd operation could target a provider/unrelated service, expose secret/environment data, or require root/system domain;
- a new OS version/architecture/source contradicts verified semantics;
- a dependency lacks admission or introduces native ABI/install-script/telemetry/license risk;
- another module's internals/table/path must be edited;
- a shared contract meaning/unit/error/privacy/side effect must change;
- a test would need simulation, recording, disabled assertion, or test-only path;
- owner/provider state, service data, or secrets might be altered/exposed;
- real evidence contradicts the plan.

## 11. Documentation outputs

Implementation must produce/update, through assigned ownership:

- `docs/platform/macos.md`: support matrix, architecture, boundaries, capabilities, limitations, privacy and extension points;
- `docs/contracts/platform-macos-v1.md`: CTR-RUN-006/CTR-PLAT-001 macOS schemas, units, field/error states, compatibility;
- `docs/operations/macos.md`: only verified native-directory, service, diagnostics, incident, rollback, and troubleshooting routines;
- real-macOS capability/source matrix with exact OS/build/architecture scope;
- process/filesystem/launchd source and native symbol/command allowlists;
- configuration registry entries and safe diagnostic visibility;
- dependency admission, lock/SBOM/notices records where applicable;
- sanitized Red/Green/refactor and live T5 reports with Blocked/Not Run rows;
- traceability, risk register, contract register, planning registry/catalog, and release known limitations;
- DEP/M06/M08/provider handoff notes and compatibility consequences.

No document contains real username, host name, account identity, absolute local path, raw PID linked to identity, provider filename/content, native raw output, environment, prompt/response/tool/source content, or secret.

## 12. Dependency and license impact

### 12.1 Current status

No dependency is selected or approved. No manifest/lockfile/install action is authorized.

Potential approaches requiring MAC-G2 evidence and full admission are:

| Approach | Potential purpose | Unresolved review |
|---|---|---|
| Python standard library plus documented native API binding | minimal process/filesystem/service access | ABI safety, public-header stability, packaging, architecture behavior, maintenance burden |
| maintained cross-platform process library | process fields and compatibility | exact package/version, source semantics, license, transitive/native code, telemetry, release/security history, Linux parity |
| maintained macOS framework binding | public framework access | exact modules/version, license/transitives, binary/build support, package size, removal cost |
| built-in read-only system executable | source/service interaction | documented structured output, locale/version stability, environment/output sensitivity, timeouts, no shell |

Every candidate must document necessity, upstream identity, exact version/source, direct and transitive licenses, maintenance/release/security posture, supported macOS/Python/architectures, native code and build/install scripts, network/telemetry behavior, size/performance, pin/update/removal strategy, alternatives, SBOM/notices, and reviewer/date. Until then its status is Candidate/Pending, not Approved.

### 12.2 Selection principles

- Prefer an official public stable source whose exact semantics can be tested.
- Avoid implementing undocumented C layouts or private API bindings merely to reduce dependency count.
- Avoid a convenience dependency that exposes prohibited process capabilities unless use can be constrained and reviewed.
- Built-in executables are platform dependencies and require the same source/version/output/security review.
- One platform's dependency cannot leak into the domain or become mandatory on the other platform.

## 13. Risks and unresolved decisions

### 13.1 Risks

| Risk | Likelihood/impact | Mitigation/evidence | Owner | Status |
|---|---|---|---|---|
| R-015 PID reuse/hierarchy ambiguity | Medium/Major | PID+start+executable, recheck, typed races, real churn | A04-MAC/M06 | Open |
| R-023 macOS silently degrades | Medium/Major | real-Mac gate, compatibility matrix, Blocked visibility | A04-MAC/integration | Open |
| R-004 provider/default state mutation | Low/Critical | read-only roots, no provider control, pre/post checks | security/adapters | Open |
| R-005 secret/content/path leak | Medium/Critical | closed fields, no raw output, safe reads, scanners | security/all | Open |
| R-009 rare races/permissions unavailable | High/Major | owned real resources; otherwise Blocked | test steward | Accepted/Open |
| R-019 CI mistaken for platform proof | Medium/Major | separate T5 report and claim-failing Blocked result | integration | Open |
| TCC/SIP restriction changes | Medium/Major | normal-user capability probing; honest permission-limited result | A04-MAC | Open |
| public API/ABI changes across macOS | Medium/Critical | verified range, source version, no silent newer acceptance | A04-MAC/dependency | Open |
| CPU/memory semantic mismatch | Medium/Major | typed measurement kind and independent reconciliation | A04-MAC/M06 | Open |
| symlink/TOCTOU escape | Medium/Critical | descriptor/race-safe design and real adversarial tests | A04-MAC/security | Open |
| launchd output exposes environment/path | Medium/Critical | bounded allowlist parsing and no raw retention | A04-MAC/DEP | Open |
| launchd service control targets wrong label/domain | Low/Critical | exact immutable target and current-user restriction | A04-MAC/DEP | Open |
| Intel/Apple-silicon/Rosetta divergence | Medium/Major | explicit architecture matrix; no inferred support | A04-MAC | Open |
| no real supported Mac available | High/Major | keep platform implementation/release claim Blocked | owner/integration | Open |

### 13.2 Approval-blocking synchronization decisions

1. First supported macOS product versions/build policy and architectures.
2. Real Mac ownership/access, evidence custody, and approved read-only discovery packet.
3. Selected public process enumeration/detail sources and verified version/permission behavior.
4. Cross-platform process start identity, boot/platform scope, executable identity, and precision.
5. CPU measurement kind/normalization/window and memory kind/units.
6. Process state allowlist and unknown-version/raw-state handling.
7. Parent identity/reparent/race evidence semantics shared with M06 and Linux.
8. CWD/executable path privacy representation and persistence/display policy.
9. CTR-RUN-006 request/outcome/partial/error/cancellation shapes and ownership.
10. CTR-PLAT-001 native-directory, approved-root, safe-file, diagnostics, and health schemas.
11. Secure component-resolution/read primitive proven available on supported macOS/Python.
12. Provider root/file manifests and ephemeral bytes handoff to A01–A03.
13. Native directory categories/paths, permissions, overrides, and creation ownership with DEP.
14. DEP-owned CTR-DEP-001 lifecycle meanings and macOS launchd mapping.
15. Exact launchd service label/domain, definition ownership, safe status fields, retry/backoff, and login semantics.
16. Timeout, process-count, byte/depth/output, concurrency, and performance budgets.
17. Configuration key ownership/names/defaults/reload behavior.
18. Component health/readiness degradation rules with M08.
19. Platform source/dependency approach and complete admission.
20. Canonical automation selectors and how Blocked T5 causes macOS claim failure.
21. Linux plan comparison proving no `/proc`/systemd/XDG or macOS semantic leakage.
22. Packaging, signing/notarization, supported Python, and build architecture implications owned by DEP/FND.
23. Whether any decision requires an ADR or security/threat-model amendment.

No implementation agent may choose silently among alternatives that change semantics, privacy, privilege, compatibility, dependency, or service side effects.

## 14. Delivery, rollback, recovery, and handoff

### 14.1 Delivery order

1. Synchronize this plan with Linux/M06/DEP/M08/provider consumers.
2. Assign and inventory a real supported Mac without installing or modifying anything.
3. Approve and execute source discovery; update capability/compatibility decisions.
4. Freeze contracts/config/error/source allowlists and complete dependency admission.
5. Approve isolated implementation task packets.
6. Implement contract/pure then process, filesystem, diagnostics, and launchd increments through real-boundary TDD.
7. Integrate with M06/A01–A03/M08/DEP only through frozen contracts.
8. Run required real-Mac T5/T7/security/performance matrices.
9. Exercise verified runbook and complete release/known-limitations review.

### 14.2 Rollback and recovery

- Process/filesystem observation capabilities can be disabled by the approved capability/configuration mechanism; existing M06 data becomes stale/unavailable, never fabricated.
- Adapter rollback must respect contract/schema compatibility and preserve M06/operations data.
- A launchd deployment rollback targets only the exact AgentMonitor user service, preserves `.env`, database, backups, logs, and provider profiles, and restores the prior verified artifact/definition through `AUTO-DEPLOY`.
- No rollback deletes provider state, changes provider permissions, signals provider processes, removes unknown services, or uses broad filesystem operations.
- Failed safe-file validation discards in-memory bytes and leaves the file untouched.
- If a security/privacy violation occurs, disable the capability, quarantine sanitized evidence, follow incident response, and do not resume until controls and real tests pass.

### 14.3 Post-deployment checks

- actual OS/build/architecture and selected sources are inside verified ranges;
- adapter/contracts/application versions are compatible;
- AgentMonitor user service target/domain, readiness, and browser-independent collection are healthy;
- real provider processes are observed without launch/process/profile changes;
- PID/start/executable identity, units, permissions, races, and parent ambiguity are truthful;
- approved roots/read limits and symlink defenses are active;
- logs/diagnostics/service artifacts/evidence contain no secrets/content/raw paths/output;
- no prohibited process-control/environment/memory/terminal capability exists;
- every Failed/Blocked/Not Run T5 row remains visible.

### 14.4 Required handoff

The implementation handoff must list:

- exact requirement/AC/scenario IDs;
- plan, adapter, CTR-RUN-006, CTR-PLAT-001, and CTR-DEP-001 versions;
- supported OS/build/architecture and source compatibility scope;
- files/dependencies/configuration/contracts changed;
- Red/Green/refactor commands, timestamps, boundaries, and sanitized evidence;
- real process/filesystem/launchd/provider/application results;
- every Failed, Blocked, and Not Run item;
- no-control, no-environment, no-content, path-safety, secret-scan, and failure-isolation evidence;
- dependency/license/security/SBOM/notices impact;
- deployment/rollback/recovery/runbook results;
- known limitations, risks, and exact integration step.

## 15. Definition of ready

- [ ] Requirements, outcome, non-goals, and acceptance non-credit rules are approved.
- [ ] A real supported Mac, OS/build/architecture scope, and evidence-custody location are approved.
- [ ] Read-only M0-MAC source discovery has terminal reviewed evidence.
- [ ] A04 Linux comparison is complete and no OS implementation semantics leak into shared contracts.
- [ ] CTR-RUN-006, CTR-PLAT-001, and CTR-DEP-001 are synchronized with every producer/consumer.
- [ ] Process identity, parent/race, state, CPU, memory, CWD, source, and provenance meanings are frozen.
- [ ] Native-directory, approved-root, symlink/TOCTOU, file bounds, and provider handoff rules are approved.
- [ ] User launchd source/domain/label/definition/status/autostart/recovery meanings are verified and frozen.
- [ ] Paths/imports/configuration/shared-file ownership are conflict-free.
- [ ] Every source/dependency/tool has completed security, maintenance, license, transitive, ABI, SBOM, and notices admission.
- [ ] Every scenario has an actual boundary, expected behavioral Red, owner/real-resource coordination, safe cleanup, and truthful unavailable policy.
- [ ] Canonical fail-closed test/quality/docs/build/deploy selectors exist for the required phase and themselves have real evidence.
- [ ] Security/threat/privacy/no-control/no-content reviews have no unresolved implementation-changing issue.
- [ ] Documentation, compatibility matrix, operations, rollback, and handoff ownership are assigned.
- [ ] Planning catalog/registry and cross-plan synchronization review include this exact artifact and the planning gate passes.
- [ ] No unresolved decision permits materially different implementation.
- [ ] Owner, integration, M06, M08, DEP, A04 Linux, provider, security, test, operations, and dependency reviewers approve this plan/version.

Until every applicable item is checked, platform implementation is not ready. Contract-only work is also unauthorized until its narrower MAC-G3 approval/task packet exists.

## 16. Approval record

| Role | Decision | Conditions | Date |
|---|---|---|---|
| Owner | Pending | real supported Mac and support scope required |  |
| Root/integration steward | Pending | full-plan synchronization and canonical gate |  |
| A04 Linux/M06 contract reviewers | Pending | shared semantic comparison |  |
| DEP/M08 reviewers | Pending | lifecycle/health mapping |  |
| A01–A03/M02/M03 reviewers | Pending | installation/root/provider boundary |  |
| Security/privacy reviewer | Pending | source/path/service/no-control review |  |
| Test-integrity/live reviewer | Pending | real-Mac matrix and evidence automation |  |
| Operations/dependency reviewer | Pending | runbook/dependency/rollback review |  |

Approval of this document authorizes neither system access nor implementation. A later implementation task packet must name the approved gate/contract versions and exact owned paths.
