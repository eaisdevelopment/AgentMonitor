# Platform-adapter plan: A04-LINUX — Linux process, filesystem, path, and user-service boundary

- Plan ID: `PLAN-A04-LINUX`
- Status: **Draft; not implementation-ready**
- Plan version: `0.2.0-draft`
- Adapter contract version: implements proposed `CTR-PLAT-001` / `PortablePlatformPrimitivesV1` and M06-owned `CTR-RUN-006` / `ProcessInspectionPortV1`; consumes deployment constraints but does not implement `CTR-DEP-001`
- Primary owner: Linux platform-adapter owner
- Reviewers: root/integration steward, M06 runtime owner, M02 registry owner, M03 provider-system owner, A01–A03 provider-adapter owners, M08 operations owner, deployment owner, security/privacy reviewer, test-integrity reviewer
- Requirements: FR-DISC-001..005, FR-DISC-007..008, FR-OPS-001..002, FR-OPS-005..006, FR-SAFE-002; NFR-ARCH-001..002, NFR-TEST-001..002, NFR-SEC-001, NFR-PRIV-001..002, NFR-DOC-001, NFR-LIC-001, NFR-PLAT-001, NFR-PERF-001, NFR-RES-001, NFR-OBS-001, NFR-COMP-001
- Acceptance contribution: AC-V1-001..002, AC-V1-005..008, AC-LIVE-004, AC-PROC-001..005, AC-OPS-001..003, AC-TEST-001..002, AC-TEST-004, AC-TEST-006
- Consumed contracts: proposed CTR-COMMON-001/002/004/007, CTR-FND-003/004/007/008, CTR-CONFIG-001, CTR-BOUNDARY-001/003, CTR-REG-003/004, CTR-PROV-002/003, CTR-RUN-006, CTR-OPS-006, CTR-DEP-001
- Contract roles: implements FND-owned portable CTR-PLAT-001 and M06-owned CTR-RUN-006; consumes PLAN-DEP intent/target constraints without implementing CTR-DEP-001 semantics
- Target milestone: M2 process visibility, with native lifecycle integration by M7
- Approved by/date: pending

## CS-1 alignment addendum — contract baseline 0.2.0

This addendum is normative for CS-1 and supersedes any wording below that makes
A04-LINUX a semantic producer of a shared contract or an implementer of the
deployment lifecycle. The machine-readable
[contract baseline](../../contract-baseline.toml) and
[parallel ownership manifest](../../parallel-ownership.toml) remain unapproved
and grant no implementation or host-mutation authority.

- PLAN-M06 is the sole semantic producer of
  `CTR-RUN-006 ProcessInspectionPortV1`; A04-LINUX implements its Linux side.
  Changes to process identity, fields, units, errors, cancellation, or side
  effects return to M06 producer/consumer review.
- PLAN-FND is the sole semantic producer of
  `CTR-PLAT-001 PortablePlatformPrimitivesV1`; A04-LINUX implements its Linux
  path, approved-file, platform-health, and fixed AgentMonitor user-service
  primitives. Linux-specific extensions cannot redefine the portable contract.
- A04-LINUX does not implement or publish `CTR-DEP-001`. PLAN-DEP owns artifact
  and unit activation plus fenced service-quiescence orchestration. A04-LINUX
  consumes its fixed target/intent and supplies only `CTR-PLAT-001` mechanics
  and receipts.
- The adapter consumes `CTR-COMMON-001/002/004/007`, `CTR-CONFIG-001`,
  `CTR-BOUNDARY-001/003`, and M08-owned `CTR-OPS-006`. Field states use
  `CTR-COMMON-007`; safe execution/read policy is not reimplemented privately;
  leaf health never becomes application readiness. A04-LINUX owns no durable
  event; domain events use `CTR-COMMON-006` plus `CTR-EVT-001` through the
  owning domain workflow.
- Process inspection, approved-file primitives, path resolution, and fixed
  user-service primitives may proceed in separate internal lanes after their
  exact paths and contracts freeze. Shared contracts, configuration registry,
  dependency files, composition, generated files, service-unit templates, and
  live process/profile/service targets remain single-writer or centrally
  reserved resources.

Linux capability claims require real non-root Linux evidence. No macOS credit,
mock/fake boundary, recorded output, seeded process, placeholder field, or
unexecuted test can establish support; Blocked and Not Run remain non-Passed.

## Planning gate and current evidence state

This document is a detailed implementation plan, not evidence that Linux behavior is supported. The required Milestone 0 scenarios `M0-LNX-001..013` are **Not Run**. No approved Linux source dossier, target kernel/distribution inventory, provider process observation, provider state-root allowlist, filesystem-atime decision, systemd user-manager finding, or process/session correlation result exists yet. Every exact source and field below is therefore either:

1. a contract invariant that follows from approved security/product rules; or
2. a candidate to confirm, reject, or narrow through M0 and contract synchronization.

No `/proc` path, provider file, systemd operation, process, profile, service, or account was inspected while preparing this plan. No test below has run. No dependency, configuration key, command, production path, or contract is approved merely because it is described here.

Implementation cannot start until all of the following evidence dependencies are resolved:

| Evidence dependency | Required M0 result | Consumer decision enabled | Current state |
|---|---|---|---|
| Linux source inventory | `M0-LNX-001` identifies exact documented kernel/procfs/filesystem sources, permission scope, and prohibited sources | CTR-PLAT-001 source registry | Not Run |
| Real provider process identity | `M0-LNX-002` observes Claude, Codex, and Ollama where naturally running | executable/provider selector rules | Not Run |
| Hierarchy behavior | `M0-LNX-003/008` records wrapper, reparent, orphan, and provider-subagent evidence | ancestry contract and confidence | Not Run |
| PID reuse/races | `M0-LNX-004` records start marker, scope, precision, and conflict behavior | process identity algorithm | Not Run |
| Working-directory privacy | `M0-LNX-005` records permission, path, symlink, deleted-path, display, and redaction rules | cwd field policy | Not Run |
| CPU/memory/state semantics | `M0-LNX-006` records exact source, unit, sampling, precision, and freshness | metric DTOs | Not Run |
| Provider session linkage | `M0-LNX-007/009` identifies safe join keys or explicit gaps | platform/provider handoff | Not Run |
| Runtime-state evidence | `M0-LNX-010` distinguishes definitive, inferred, and unavailable state signals | safe state input slots | Not Run |
| Negative privacy proof | `M0-LNX-011` proves prohibited sources are outside the path | security approval | Not Run |
| No-control/no-mutation proof | `M0-LNX-012` reconciles process and provider-file pre/post state | live safety approval | Not Run |
| Capability decision | `M0-LNX-013` scopes decisions to exact kernel, privilege, and provider versions | enabled manifest | Not Run |
| systemd/XDG inventory | Linux M0 handoff records real user-manager, lingering, XDG, mount, and atime behavior | CTR-PLAT-001 service/path profile | Not Run |

The implementation owner must reject a handoff that generalizes beyond observed distributions/kernels, treats PID or a path as identity, lacks source/units, hides Blocked results, or asks the adapter to read environment, memory, terminal, command-line, credential, or content data.

## 1. Outcome and boundaries

### 1.1 Outcome

A synchronized implementation of this plan will give AgentMonitor a least-privilege Linux boundary that can:

- enumerate and inspect bounded sets of real candidate agent processes without changing how they were launched;
- establish process identity using a M0-approved PID/start/scope/executable tuple and reject races or reuse rather than misattribute;
- return typed process ancestry, elapsed time, CPU, resident-memory, state, executable identity, and privacy-safe working-directory results with source, unit, timestamp, precision, and availability;
- discover only registered provider state-root candidates, and read only an approved relative file specification through race-resistant, bounded, non-mutating filesystem primitives;
- resolve AgentMonitor's own Linux XDG path classes without leaking provider paths into domain modules;
- inspect the real user-level AgentMonitor service through a bounded systemd integration;
- later implement only the FND-owned CTR-PLAT-001 fixed-unit filesystem and
  service-manager primitives that PLAN-DEP composes for its CTR-DEP-001
  lifecycle, without exposing an arbitrary service controller;
- publish bounded health/diagnostic facts without raw paths, process data, provider content, credentials, or arbitrary environment values;
- degrade each unavailable Linux capability independently so a procfs restriction, provider-file denial, or missing user systemd does not take down other collectors or the dashboard.

Success means the corresponding canonical T5/T7 selectors pass on the real target Linux environment for the exact supported scope, all unsupported/Blocked matrix rows remain visible, and the adapter has no process-control or unrestricted file-read surface.

### 1.2 In scope

- Linux platform capability detection for procfs, filesystem primitives, clock/page-size primitives, XDG resolution, and systemd user-manager availability.
- Bounded numeric-PID enumeration from an approved process source.
- PID plus start-marker plus platform/namespace/boot scope plus executable identity.
- Parent PID observation and validation of parent process identity when the parent remains observable.
- Process-exit, permission, reparenting, PID-reuse, source-version, and deadline races.
- CPU-time and optional utilization sampling only with explicit semantics; resident memory in bytes; elapsed duration in integer milliseconds; UTC observation time plus monotonic measurement intervals.
- Linux process-state source codes preserved in a versioned safe extension while normalized meaning remains M06-owned.
- Working-directory inspection only when explicitly requested and approved, with privacy-safe reference/label behavior.
- Registered root discovery, metadata inspection, symlink containment, regular-file enforcement, atime policy, bounded reads, and TOCTOU detection.
- AgentMonitor XDG config/data/state/cache/log/runtime path resolution and ownership/permission observations.
- Read-only systemd user-service inspection and a narrowly typed AgentMonitor-only service lifecycle implementation seam for PLAN-DEP.
- Local structured health, compatibility, and diagnostic summaries.
- Real Linux distribution/kernel/service/filesystem/provider-process compatibility evidence.

### 1.3 Out of scope

- Domain process/session entities, persistence, hierarchy aggregation, account correlation, runtime-state classification, stall policy, or history; M06 owns these.
- Provider CLI/API/local-file schema knowledge, file/field allowlists, provider identity, quota, session, token, model, task, or error parsing; A01–A03 own these through M03.
- Polling, deadlines selected for jobs, concurrency policy across accounts/providers, retries, backoff, or collection-run state; M04 owns these.
- Organizations, accounts, installations, profiles, protected-default flags, and opaque profile references; M02 owns these.
- API routes, authorization mapping, UI, SQLite, migrations, backups, exports, and release orchestration.
- macOS implementation or a Linux-derived claim about macOS. A04-MAC has a separate plan and real-platform gate.
- Windows.
- Docker/container deployment for V1 or pretending container procfs represents the owner's workstation.
- Reading target process command lines, arbitrary environment values, memory, maps, file descriptors, terminals, stdin/stdout, sockets, or debugger surfaces.
- Signaling, attaching, pausing, resuming, changing priority, killing, restarting, injecting into, routing, or switching credentials in a provider agent.
- Broad filesystem crawling, home-directory search, content indexing, hidden profile discovery by heuristic, or reading unregistered provider files.
- Running as root, acquiring Linux capabilities, setuid helpers, broad polkit rules, or silently enabling user lingering.
- Installing/updating provider tools or changing provider-owned files/profiles.

### 1.4 Ownership

A04-LINUX owns:

- the Linux implementation of proposed `ProcessInspectionPortV1`;
- Linux process source parsing/validation, identity stabilization, bounded enumeration, resource measurement, and typed platform errors;
- Linux implementations of FND-owned `PortablePlatformPrimitivesV1` subports for XDG paths, approved filesystem access, platform capability/health, and AgentMonitor user-service inspection;
- Linux-only source/version identifiers and their compatibility matrix;
- Linux adapter safe constants and module-owned non-secret configuration registrations;
- Linux platform tests, field/source/privacy register, compatibility records, and operator troubleshooting documentation;
- typed Linux service primitives and receipts under CTR-PLAT-001, consumed by PLAN-DEP without A04-LINUX owning CTR-DEP-001 lifecycle semantics.

A04-LINUX owns no business tables, Alembic revisions, HTTP routes, browser state, provider schema, domain event, schedule, account mapping, or secrets.

### 1.5 Proposed implementation paths and file ownership

Subject to PLAN-FND repository-layout approval, the isolated implementation owner may edit only:

```text
backend/src/agentmonitor/adapters/platform/linux/
  __init__.py
  capability_probe.py
  procfs.py
  process_inspector.py
  process_metrics.py
  approved_roots.py
  safe_file_reader.py
  xdg_paths.py
  systemd_user.py
  health.py
  errors.py
  models.py
backend/tests/platform/linux/
  test_process_inspection_live.py
  test_process_races_live.py
  test_process_hierarchy_live.py
  test_process_resources_live.py
  test_approved_filesystem_live.py
  test_provider_roots_live.py
  test_xdg_paths_live.py
  test_systemd_user_live.py
  test_linux_security_live.py
  test_linux_compatibility_live.py
  test_linux_performance_live.py
docs/modules/platform/linux.md
docs/operations/linux-platform-diagnostics.md
docs/reference/linux-platform-compatibility.md
```

Proposed shared contract sources require central allocation and explicit assignment before edit:

```text
backend/src/agentmonitor/contracts/platform_v1.py                  # FND owner
backend/src/agentmonitor/contracts/runtime_observation_v1.py       # M06 owner
backend/src/agentmonitor/contracts/deployment_v1.py                # PLAN-DEP owner
```

The A04 implementation agent must not edit M02–M08, A01–A03, P01/P02, persistence, migrations, composition, generated artifacts, root automation, dependency manifests, lockfiles, service-unit templates, or shared contract files unless the root issues a revised non-overlapping packet. Evidence files containing real workstation/provider information remain outside Git.

### 1.6 Allowed and forbidden imports

Allowed after synchronization:

- Python standard-library OS, path, stat, time, resource-safe subprocess, hashing, and typing primitives selected in the approved design;
- `agentmonitor.contracts.platform_v1` owned semantically by PLAN-FND;
- `agentmonitor.contracts.runtime_observation_v1` owned semantically by M06;
- narrow approved CTR-FND configuration, correlation, logging, build metadata, safe subprocess, and test-evidence primitives;
- narrow read-only M02 installation/profile/root descriptors and M03 capability/source descriptors through published contracts;
- CTR-OPS-006 health DTO;
- CTR-DEP-001 fixed target/intent constraints only when PLAN-DEP composes
  A04-LINUX's CTR-PLAT-001 service primitives.

Forbidden:

- imports from any module's domain/application/persistence internals;
- SQLAlchemy, FastAPI, provider SDK/CLI package, UI, database, or migration imports;
- A01/A02/A03 adapter internals or provider-specific branching outside registered descriptors;
- `psutil`, D-Bus client, inotify, privileged helper, or other third-party package until its exact dependency admission passes;
- shell strings, `shell=True`, dynamic executable lookup from provider data, or uncontrolled inherited environments;
- APIs for signals, ptrace/debugging, process memory, terminal input, priority/control, or arbitrary unit management;
- reads of `/proc/*/environ`, `/proc/*/mem`, `/proc/*/cmdline`, `/proc/*/maps`, terminal devices, or arbitrary `/proc/*/fd` targets;
- unbounded `Path.rglob`, home traversal, arbitrary absolute path parameters, raw-path logging, or content-bearing `repr` output.

An automated import/API/prohibited-symbol gate must enforce these rules before any implementation handoff.

### 1.7 Parallel-development isolation

- M06 may finalize DTO semantics while A04 works internally only after a frozen CTR-RUN-006 review baseline; changes return to contract synchronization.
- A01–A03 own provider root/file specifications and parsers. A04 enforces a generic registered specification and never embeds provider filenames.
- PLAN-DEP owns service lifecycle policy, artifact/unit activation, quiescence,
  and unit content. A04 owns only FND-defined Linux execution primitives for a
  fixed AgentMonitor service target.
- M08 consumes bounded health; it cannot call A04 internals or request raw platform inspection.
- A04-MAC implements the same portable contract separately and cannot import Linux code.
- Shared contract, composition, manifest, automation, and service-unit edits are serial root-owned integration work.

## 2. Requirements and traceability

| Requirement/AC | Planned A04-LINUX contribution | Contract | Scenario IDs | Evidence gate |
|---|---|---|---|---|
| FR-DISC-001 | Discover real candidate provider processes without launch-flow changes | CTR-RUN-006 | LNX-PROC-001, LNX-PROC-002, LNX-LIVE-001..003 | M0 plus real T5 |
| FR-DISC-002 | Typed PID/PPID/start/duration/CPU/memory/state/cwd results | CTR-RUN-006 | LNX-PROC-003..014 | real procfs and owner reconciliation |
| FR-DISC-003 | Enforce registered roots/files and bounded ephemeral reads | CTR-PLAT-001 | LNX-FS-001..014, LNX-LIVE-004..006 | real filesystem and approved provider roots |
| FR-DISC-004 | Preserve platform evidence; never infer account | CTR-RUN-006 | LNX-PROC-015, LNX-LIVE-007 | M06/provider correlation review |
| FR-DISC-005 | Supply validated OS ancestry without claiming provider semantics | CTR-RUN-006 | LNX-PROC-008..010, LNX-LIVE-008 | representative real trees |
| FR-DISC-007 | No arbitrary target-process environment access | CTR-RUN-006/CTR-PLAT-001 | LNX-SEC-001, LNX-SEC-002 | static plus real negative proof |
| FR-DISC-008 | Report source/parser/platform/provider descriptor versions | CTR-PLAT-001/CTR-RUN-006 | LNX-COMP-001..004 | compatibility matrix |
| FR-OPS-001 | XDG and systemd user-service primitives for native deployment | CTR-PLAT-001/CTR-DEP-001 | LNX-XDG-001..005, LNX-SVC-001..008 | T5/T7 target host |
| FR-OPS-002 | Publish bounded platform/service health | CTR-OPS-006 | LNX-OPS-001..003 | real health consumption |
| FR-OPS-005 | Keep secrets/content out of diagnostics/logs | CTR-PLAT-001 | LNX-SEC-003..006 | output/artifact scan |
| FR-OPS-006 | Expose safe adapter/kernel/source/service versions | CTR-PLAT-001 | LNX-COMP-001..006 | real target hosts |
| FR-SAFE-002 | No provider process control or credential switching | all A04 contracts | LNX-SEC-007..010 | API/import/live no-control proof |
| NFR-ARCH-001/002 | Linux code only behind versioned ports; no circular/internal imports | CTR-PLAT-001/CTR-RUN-006 | LNX-ARCH-001..003 | automated boundary gate |
| NFR-TEST-001/002 | Red-green-refactor at real boundaries; no test doubles | evidence contract | all LNX scenarios | canonical test report |
| NFR-SEC-001 | Least privilege, bounded path/process/subprocess behavior | all A04 contracts | LNX-FS-*, LNX-SEC-* | security review and real tests |
| NFR-PRIV-001/002 | Operational metadata only; no content/environment/external telemetry | all A04 contracts | LNX-SEC-001..006 | field/log/network proof |
| NFR-DOC-001 | Maintained module/source/compatibility/operations docs | documentation outputs | LNX-OPS-004 | AUTO-DOCS-CHECK |
| NFR-LIC-001 | No package/tool admission without full review | dependency register | LNX-QUAL-001 | license/SBOM gate |
| NFR-PLAT-001 | Linux fully verified; portable contract leaves macOS independent | CTR-PLAT-001/CTR-RUN-006 | LNX-COMP-001..006, LNX-ARCH-003 | real Linux matrix; macOS separate |
| NFR-PERF-001 | Bounded scan remains viable at 200 real processes | CTR-RUN-006 | LNX-PERF-001..003 | real host workload |
| NFR-RES-001 | Per-process/path/service failures stay isolated | CTR-PLAT-001/CTR-RUN-006 | LNX-PROC-006/007, LNX-FS-011/012, LNX-SVC-006 | partial-result tests |
| NFR-OBS-001 | Safe structured local events/correlation IDs | CTR-FND-004 | LNX-OPS-001, LNX-SEC-005 | log inspection |
| NFR-COMP-001 | Versioned platform/source/error semantics | CTR-PLAT-001/CTR-RUN-006 | LNX-COMP-003..006 | compatibility/diff gate |
| AC-PROC-001 | Observe real provider processes without workflow/input change | CTR-RUN-006 | LNX-LIVE-001..003, LNX-SEC-009 | owner-acknowledged T5 |
| AC-PROC-002 | Correct representative ancestry inputs | CTR-RUN-006 | LNX-LIVE-008, LNX-PROC-008..010 | owner comparison plus M06 |
| AC-PROC-003 | Weak platform evidence stays unresolved | CTR-RUN-006 | LNX-PROC-015, LNX-LIVE-007 | correlation evidence review |
| AC-PROC-004 | No prohibited data retained | all | LNX-SEC-001..006 | schema/log/artifact/DB consumer review |
| AC-PROC-005 | Supply real process/activity inputs without classifying waits/stalls | CTR-RUN-006 | LNX-LIVE-009 | M06 integration T5/T6 |
| AC-OPS-001 | Linux user-service behavior supported and later deployment-verified | CTR-DEP-001 | LNX-SVC-001..008 | PLAN-DEP coordinated T7 |
| AC-OPS-002 | Platform collection continues independently of browser | CTR-PLAT-001 | LNX-OPS-002 | real installed service |
| AC-OPS-003 | Linux/provider-source failure is contained | typed outcomes | LNX-OPS-003 | integrated real stack |
| AC-TEST-001/002/004/006 | RGR evidence; no doubles; safe live report; visible Blocked rows | CTR-FND-008 | all LNX scenarios | canonical automation |

Interpretations requiring synchronization:

- A04 discovers process facts; it does not decide that an OS child is a provider subagent. M06 combines platform and provider evidence.
- A provider selector cannot depend on command-line arguments because those may contain prompts, source paths, or secrets. If executable identity/comm/provider evidence is insufficient, discovery is unsupported or partial.
- A raw working-directory path is not a default output. The proposal is a field state plus an approved opaque root reference and optional owner-approved safe label. Any raw-path API/persistence use is a separate M06/security decision.
- “Read-only file” includes filesystem metadata side effects such as atime. A source is not supported until the atime/mount/open policy is evidence-backed.
- Systemd mutation is limited to the AgentMonitor user service and requires deployment authority. It is not provider-agent process control.

## 3. Internal design

### 3.1 Capability profile

`LinuxCapabilityProfileV1` is an immutable startup/refresh result containing safe platform scope and capability states, not arbitrary host inventory. Each capability is `supported`, `unavailable`, `permission_denied`, `unverified`, `incompatible`, or `disabled`; there is no optimistic default.

Candidate capability keys, pending M0:

- `process.enumeration.procfs.v1`;
- `process.identity.start_marker.v1`;
- `process.executable_identity.v1`;
- `process.parent_identity.v1`;
- `process.cpu_time.v1` and optional `process.cpu_utilization_sample.v1`;
- `process.resident_memory.v1`;
- `process.cwd_reference.v1`;
- `filesystem.registered_root.v1`;
- `filesystem.bounded_regular_read.v1`;
- `filesystem.no_atime_read.v1`;
- `paths.xdg.v1`;
- `service.systemd_user_inspection.v1`;
- `service.systemd_user_lifecycle.v1` only when PLAN-DEP enables it.

The profile records adapter version, safe kernel release class, distribution identifier/version where approved, architecture, procfs/source version, PID namespace/boot-scope fingerprint, systemd availability/version where safe, and observation time. It never includes hostname, username, home path, provider paths, command lines, environment, unit file content, or raw mount data.

One unavailable capability does not disable the others. Capability refresh is idempotent and bounded. Kernel/provider/systemd version change invalidates the corresponding compatibility assertion until reverified.

### 3.2 Process identity and source scope

The portable identity sent to M06 is conceptually:

```text
ProcessIdentityV1 =
  platform_scope_id
  + positive_pid
  + start_identity(kind, exact_value, precision)
  + executable_identity(kind, safe_fingerprint)
```

For Linux, candidate sources are procfs start ticks, a boot/namespace scope, and executable filesystem identity. M0 must confirm the exact safe source set. Linux ticks, inode values, or procfs paths do not leak into M06 as untyped strings; the contract carries a versioned identity kind and opaque canonical representation.

Invariants:

1. PID alone never identifies a process instance.
2. The same PID with a different start identity or executable identity is a new process or an identity conflict.
3. A start marker is interpreted only within its recorded boot/namespace/platform scope.
4. Derived UTC start time is optional and carries precision/derivation; the exact start identity remains authoritative for equality.
5. Executable label/path is not identity. The approved fingerprint is based only on evidence allowed by M0 and does not hash executable content without a separate cost/privacy decision.
6. A source that cannot supply the synchronized tuple returns an incomplete/unsupported result; it never falls back to PID.

### 3.3 Stable process-inspection sequence

For each bounded inspection batch, the future implementation follows a source-approved equivalent of this algorithm:

1. Validate request version, deadline, result/candidate bounds, selector IDs, root/access-grant IDs, and requested allowlisted fields.
2. Resolve selectors from a local immutable registry; reject arbitrary names, paths, PIDs outside the request contract, and unknown field IDs.
3. Capture monotonic start and UTC observation context; resolve platform/boot/namespace scope.
4. Enumerate only numeric process entries up to the candidate bound; use deterministic ordering.
5. Open/stabilize the candidate process source where supported.
6. Read identity/start/executable facts before optional fields.
7. Read only requested approved facts. Each optional fact has its own field-state outcome.
8. Re-read the identity marker after observation. If process exit, PID reuse, executable conflict, or source mutation is detected, discard ambiguous values and return a typed race outcome.
9. Resolve parent identity separately and only while the parent remains observable.
10. Enforce deadline and output-size bounds throughout; return partial results with explicit truncation/reason.
11. Convert boundary exceptions to safe codes while retaining local cause chains only in redacted protected logs.

No broad retry hides a race. At most one immediate identity revalidation/re-read may be permitted by the synchronized policy; repeated churn becomes `process_changed_during_inspection` or `deadline_exceeded`.

### 3.4 Enumeration and provider selection

Process enumeration is bounded by maximum candidates, maximum results, deadline, and approved selector set. Candidate selectors may use only M0-approved executable identity, kernel process name/comm, ownership UID equal to the AgentMonitor service user, and safe M03/M02 installation references. They do not read command-line arguments or target environments.

If a provider runs through a generic executable and cannot be distinguished without prohibited data, A04 returns generic/unresolved candidates only if the contract allows them; it does not label them Claude/Codex/Ollama. Provider adapters/M06 may corroborate with separate safe session evidence.

Enumeration records `truncated`, `candidate_count_seen`, `result_count`, and safe reason. It never returns the whole machine process table to a caller that requested one provider selector.

### 3.5 Parent identity, hierarchy, wrappers, and reparenting

- Observed PPID is a point-in-time field, not a durable relationship.
- A parent edge is validated only when parent PID, parent start identity, and source scope are observed and compatible within the batch.
- Parent start must not be later than child start outside documented precision tolerance.
- Parent exit yields an orphan/unavailable field state, not attachment to a reused PID.
- Reparenting is preserved as observation history for M06; A04 does not infer original parent.
- Wrapper processes are returned as processes if they match approved selection/evidence. A04 does not remove a wrapper or promote a descendant by heuristic.
- OS ancestry alone is `platform_ancestry`; provider parent/subagent semantics require provider evidence and M06 rules.
- Cycle/impossible-time findings return invalid/conflict evidence and do not become a tree.

### 3.6 Time, CPU, memory, and process-state units

All wall timestamps are timezone-aware UTC. Deadlines and sampling intervals use a monotonic clock. Exact Linux source and conversion rules remain M0 blockers.

The proposed portable measurements are:

- `observed_at`: UTC instant and clock precision;
- `elapsed_duration_ms`: non-negative integer with derivation/source precision;
- `cpu_time_ns`: non-negative cumulative user-plus-system CPU duration if supported;
- optional `cpu_utilization_basis_points`: explicit sample start/end, monotonic duration, and normalization kind (`one_logical_cpu` or `host_capacity`), never an unlabeled percent;
- `resident_memory_bytes`: non-negative resident-set bytes and source semantics;
- `platform_state_code`: bounded Linux source code plus source-schema version; M06 decides normalized state/certainty.

CPU percentage is never calculated from a single cumulative sample. Cross-process aggregation occurs only in M06 after unit/sample compatibility. Page counts are converted with the actual runtime page size using overflow-safe integer arithmetic. Clock ticks use the runtime source value and are never assumed to be a universal constant. Missing/denied/unsupported is distinct from zero.

### 3.7 Working-directory handling

Working directory is owner-private operational metadata and can expose repository/customer names. The default contract result contains:

- field state: `available_mapped`, `available_unmapped`, `deleted`, `permission_denied`, `process_exited`, `unsupported`, or `not_requested`;
- an approved opaque root/project reference when the observed directory is proven beneath a registered root;
- an optional safe display label supplied or approved by Registry, not derived from arbitrary path components;
- no raw path in logs, events, diagnostics, evidence reports, or default persistence.

The raw kernel path, if M0 approves reading it, remains transient inside A04 for containment/mapping. Symlink resolution, mount crossing, deleted-path suffixes, bind mounts, permission failures, and cwd changes during inspection must be detected or surfaced as unknown. The adapter does not list directory contents or inspect repository/source files.

If owner-visible raw paths are later approved, they require an additive explicitly privacy-classified type, authorization/retention/export rules, consumer review, and security approval. They cannot be smuggled through a “safe label.”

### 3.8 Registered provider state roots

Provider root discovery is a finite candidate evaluation, not a search. Candidate roots originate only from:

- provider-version path specifications registered by A01–A03 and approved through M03;
- standard user/XDG root classes resolved by A04;
- opaque AgentMonitor-managed profile/root references published by M02;
- explicit owner-approved configuration registered through CTR-CONFIG-001.

Every candidate has `root_spec_id`, provider/source/schema version, root class, expected owner UID, accepted file type, symlink policy, permission policy, default-profile protection metadata, and read-only purpose. The contract returns an opaque root reference and safe metadata state. It does not expose the path to domain code or scan siblings/parents.

Missing roots are ordinary `not_found`; unreadable roots are `permission_denied`; unsupported symlink/mount layouts are `unsafe_layout` or `unsupported`. No root is created, chmodded, moved, normalized by write, or “repaired.”

### 3.9 Safe filesystem read algorithm

Provider-specific adapters register immutable relative-file specifications. A read request identifies a root/access grant and file-spec ID; it never supplies an arbitrary path or glob. The future implementation must use the strongest M0-supported descriptor-relative mechanism and meet these invariants:

1. Open the approved root with directory-only, close-on-exec, and no-follow semantics as supported.
2. Walk fixed relative components from the held directory descriptor; reject empty, dot, dot-dot, absolute, NUL, separator-in-component, glob, and unregistered components.
3. Reject symbolic links by default at every component and final target. Any explicitly allowed root indirection requires a separately proven containment policy.
4. Open the final object read-only/nonblocking as appropriate, then verify with the opened descriptor that it is a regular file, expected owner, safe mode, allowed link count, and within the byte limit.
5. Apply the approved no-atime policy. If read access would cause an unapproved atime/state change and no safe mechanism exists, return `unsupported_side_effect_policy` rather than read.
6. Read at most `max_bytes + 1` before rejecting oversize, enforce the monotonic deadline and aggregate batch byte limit, and never memory-map an untrusted provider file.
7. Compare device/inode and approved size/time/version facts before and after read; a mutation yields `changed_during_read` and no payload.
8. Return content only in an ephemeral redacted-representation wrapper to the owning provider parser. It cannot serialize, log, persist, or enter a cross-module view. Provider parsing/discard happens immediately.
9. Close every descriptor on success, error, cancellation, and timeout.

Reading by validating a string path and reopening it later is prohibited. Provider locks are not acquired unless M0 proves a documented non-disruptive read-lock contract. FIFOs, sockets, devices, proc/sysfs pseudo-files outside the process adapter, directories, and unknown types are rejected.

### 3.10 Filesystem access grant and ephemeral payload

`FilesystemAccessGrantV1` is an in-memory composition-issued capability referencing exact root/file-spec versions, operation/correlation ID, expiry/deadline, and maximum bytes. It carries no credential and is not accepted from HTTP. Grants are non-transferable across provider adapters and invalid after registry/spec version change.

`EphemeralApprovedFileV1` has a redacted `repr`/string representation, explicit byte length and safe metadata, one owning parser consumer, and immediate disposal semantics. Raw bytes never enter result logging, exception messages, test reports, fixtures, database, API, or evidence artifacts. Python cannot prove erasure from memory; documentation must state this limitation, minimize lifetime/copies, and avoid false secure-deletion claims.

### 3.11 XDG path resolution

A04 resolves path classes, not arbitrary paths:

- AgentMonitor configuration;
- AgentMonitor data/database/backups/exports;
- AgentMonitor state/locks/runtime;
- AgentMonitor cache;
- AgentMonitor logs if separately selected;
- AgentMonitor-managed provider-profile root.

Inputs are the service's own validated startup environment/configuration, never a target process environment. Resolution follows an approved XDG specification and records source/default. Results must be absolute, normalized lexically, free of NUL, and subject to ownership/type/permission checks before use. Resolution itself does not create directories or files. Creation/permission repair belongs to deployment under explicit authority.

The adapter never repurposes `HOME`, mutates global environment, prints paths, or treats a path string as proof of ownership. Tests use real child processes and real filesystem locations isolated from the operator's paths; production-environment verification separately checks the target service account.

### 3.12 systemd user-service boundary

The initial A04 surface is read-only `InspectAgentMonitorUserServiceV1`. It can inspect only the fixed synchronized AgentMonitor unit identifier and an allowlist of documented properties needed for status, autostart-at-login, restart result, executable/config path version consistency, and safe error diagnosis. Exact D-Bus or `systemctl --user` source is selected after M0/dependency review.

The result distinguishes:

- user manager unavailable;
- unit not installed/not found;
- installed but disabled;
- enabled/inactive/activating/active/deactivating/failed;
- permission/session-bus unavailable;
- unit/schema version incompatible;
- deadline exceeded or malformed source data.

Raw journal output, full unit properties, environment, command lines, user name, home path, failure text, and arbitrary units are not returned.

After CTR-DEP-001 synchronization, A04 may implement Linux mechanics for:

- atomic install/upgrade of the approved versioned AgentMonitor user-unit artifact to the approved XDG/systemd user path;
- daemon reload if required;
- enable/disable and start/stop/restart/status of that fixed unit;
- preserving/recovering the previous AgentMonitor unit artifact on failed upgrade;
- verifying post-action service identity, readiness, and artifact version.

PLAN-DEP owns the command sequence, approvals, preflight, artifact, rollback, and operator UX. A04 never accepts an arbitrary unit name or unit content from provider/user input, controls provider units, runs `sudo`, enables system lingering, edits login/session policy, or interprets PID existence as health. Lingering is inspected and reported as an installation decision only; changing it requires a separate explicit owner operation outside implicit deployment.

### 3.13 Concurrency, cancellation, and idempotency

- Process scans are concurrency-bounded by M04 and also enforce an adapter-local hard ceiling.
- File reads are bounded per request/root/provider and do not retain descriptors across jobs.
- Read-only inspection is idempotent with respect to AgentMonitor intent, though external state may change; every result has observation time/generation.
- Cancellation stops only AgentMonitor-owned inspection work. It never sends a signal to a monitored process.
- Service lifecycle requests require operation ID, expected installed artifact/version, fixed target, and idempotency semantics from CTR-DEP-001.
- Duplicate install/start requests return the already-achieved compatible state; conflicting artifact/version requests fail safely.
- Health probes never trigger a process scan, provider read, service start, install, or repair.

### 3.14 Degradation and recovery

- Per-process permission/exit/race failures produce partial batches and do not erase other valid entries.
- Procfs unavailable/incompatible disables process inspection only.
- Working-directory denial leaves other process fields valid.
- One provider root/file failure affects only that file/capability.
- Missing systemd user manager leaves the process/filesystem adapter available and makes native service lifecycle unsupported for that environment.
- Unknown kernel/source/provider-spec versions fail closed for affected fields; no best-effort parser guesses.
- A stale capability profile is visibly unverified until refreshed.
- Existing M06 observations remain subject to M06 freshness; A04 never re-emits cached values as current.

## 4. Public contracts

### 4.1 CTR-RUN-006 — Linux implementation of `ProcessInspectionPortV1`

A04 implements the M06-owned semantic port:

```text
InspectProcessesV1(PlatformInspectionRequestV1)
  -> PlatformInspectionOutcomeV1
```

Request fields are version, operation/correlation IDs, `platform_source=linux`, approved installation/selector IDs, approved root/access-grant references where needed, deadline, maximum candidate/result counts, and requested field IDs. There is no arbitrary path, command, PID list from an HTTP caller, environment-field name, shell string, provider credential, or control intent.

Each successful process entry includes:

- portable process identity tuple and Linux identity-kind/source version;
- observed PID and PPID with parent field state;
- optional validated parent identity;
- optional derived UTC start and elapsed duration with precision;
- safe executable identity/label fields allowed by M0;
- cwd field state plus approved opaque reference/label only;
- CPU and memory typed measurements with exact units/semantics;
- bounded platform state code/version;
- `observed_at`, source/platform/adapter version, field-level provenance, and permission/partial flags.

Batch outcomes are `success`, `partial`, `unsupported`, `permission_denied`, `source_unavailable`, `unverified_platform_version`, `deadline_exceeded`, `invalid_request`, `invalid_platform_data`, or `internal_adapter_error`. Entry/field outcomes further distinguish exit/race/reuse/conflict/missing/denied. A provider-labeled success requires evidence for that selector/version; generic process facts cannot be relabeled.

Compatibility promise: identity equality, units, measurement normalization, source scope, cwd privacy, and error meaning cannot change within V1. An additive field requires M0 evidence, field/privacy registration, producer/consumer review, and safe absent semantics. Adding environment/command-line/content/control behavior is a breaking future contract and prohibited in V1.

### 4.2 CTR-PLAT-001 — Linux implementation of `PortablePlatformPrimitivesV1`

Proposed operations:

- `GetLinuxCapabilityProfileV1(CapabilityProfileQueryV1) -> LinuxCapabilityProfileV1`;
- `ResolveAgentMonitorPathsV1(AgentMonitorPathQueryV1) -> AgentMonitorPathSetV1`;
- `DiscoverApprovedRootsV1(ApprovedRootDiscoveryRequestV1) -> ApprovedRootDiscoveryOutcomeV1`;
- `InspectApprovedPathV1(ApprovedPathInspectionRequestV1) -> ApprovedPathMetadataOutcomeV1`;
- `ReadApprovedRegularFileV1(ApprovedFileReadRequestV1) -> ApprovedFileReadOutcomeV1`;
- `InspectAgentMonitorUserServiceV1(UserServiceInspectionRequestV1) -> UserServiceInspectionOutcomeV1`;
- `GetLinuxPlatformHealthV1(PlatformHealthQueryV1) -> PlatformHealthViewV1`.

Preconditions:

- caller is composition-bound M02/M03/M06/M08/A01–A03/DEP authority, never an untrusted transport principal;
- contract/spec/source versions are supported;
- opaque root/file/selector IDs exist in the approved registry;
- deadline and bounds fall inside adapter hard limits;
- requested field/purpose is allowlisted and side-effect classification permits it.

Postconditions:

- no provider-owned or monitored-process state is intentionally changed;
- only allowlisted typed metadata crosses the contract;
- every result records source/version/observation/provenance and explicit partial/unknown/unsupported state;
- raw file payload crosses only the ephemeral A04-to-owning-provider-parser call and cannot enter domain contracts.

Read-only operations are observationally idempotent but do not promise identical values across a changing OS. Errors are typed, sanitized, and field/capability scoped.

### 4.3 CTR-DEP-001 — consumed deployment constraints; no A04 implementation

PLAN-DEP is the sole producer and lifecycle implementation owner. A04-LINUX
does not expose CTR-DEP-001 commands. After synchronization, PLAN-DEP may
compose these FND-owned CTR-PLAT-001 Linux primitives:

- validate the fixed AgentMonitor user-unit target and artifact reference;
- atomically install/replace/remove only a PLAN-DEP-rendered AgentMonitor unit;
- invoke a closed fixed-unit service action supplied by PLAN-DEP;
- inspect and verify the fixed AgentMonitor user service.

Inputs are approved artifact reference/digest/version, expected current version, operation/correlation/idempotency IDs, deadline, and owner/deployment authorization evidence. They do not contain arbitrary unit names, shell commands, provider process IDs, secret values, or dynamic unit text.

Platform receipts distinguish preflight failure, conflict, unsupported manager,
permission denial, artifact mismatch, atomic-write failure, reload/action
failure, and success. PLAN-DEP—not A04—classifies lifecycle readiness and
rollback. Every permitted primitive preserves a recoverable prior
AgentMonitor-owned artifact where possible. No service mutation exists until
PLAN-DEP owns the workflow, assigns shared files, and approves the real T7
matrix.

### 4.4 DTO field-state vocabulary

Every optional platform fact uses a closed field state rather than null alone:

`present`, `not_requested`, `not_found`, `unsupported`, `permission_denied`, `process_exited`, `changed_during_read`, `identity_conflict`, `unsafe_layout`, `unverified_source`, `deadline_exceeded`, or `redacted_by_policy`.

`present` always carries unit/type/source/precision as applicable. Zero is a value only under `present`; it is never used for missing. New states require compatibility review because consumers branch on them.

### 4.5 Consumed contracts

| Contract | Required status | A04 use | Failure/degradation |
|---|---|---|---|
| CTR-COMMON-001/002/007 | `proposed_aligned` 1.0.0 | opaque IDs, UTC instants, integer durations, exact field availability | invalid input rejected before I/O; missing never becomes zero |
| CTR-COMMON-004 | `evidence_blocked` 1.0.0 | source/version/freshness/precision/confidence | no successful fact without provenance |
| CTR-FND-003 | `proposed_aligned` 1.0.0 | typed non-secret settings and own-environment path inputs | invalid/missing critical configuration disables capability |
| CTR-FND-004 | `proposed_aligned` 1.0.0 | correlation and safe structured log events | incompatible log contract blocks startup/readiness |
| CTR-FND-007 | `proposed_aligned` 1.0.0 | adapter/build version facts | missing build version marks unverified |
| CTR-FND-008 | `proposed_aligned` 1.0.0 | Passed/Failed/Blocked/Not Run test evidence | no aggregate hidden status |
| CTR-REG-003/004 | `evidence_blocked` 1.0.0 | opaque approved profile/root and installation descriptors | unknown/mismatch rejects request; no path guessing |
| CTR-PROV-002/003 | `evidence_blocked` 1.0.0 | capability/source/version/side-effect registry | unsupported/unapproved source does no I/O |
| CTR-RUN-006 | `evidence_blocked` 1.0.0 | process request/result semantics | incompatible major rejected |
| CTR-OPS-006 | `proposed_aligned` 1.0.0 | bounded platform component health | M08 timeout cannot break A04 operations |
| CTR-DEP-001 | `proposed_aligned` 1.0.0 | fixed service target/intent constraints consumed by PLAN-DEP composition | A04 exposes no deployment lifecycle port |

### 4.6 Safe error vocabulary

Stable proposed codes include:

- `linux_capability_unavailable`, `linux_source_unverified`, `linux_source_incompatible`;
- `linux_process_permission_denied`, `linux_process_exited`, `linux_process_identity_incomplete`, `linux_process_identity_conflict`, `linux_pid_reused`, `linux_process_changed_during_inspection`;
- `linux_parent_unavailable`, `linux_parent_identity_conflict`, `linux_ancestry_ambiguous`;
- `linux_metric_unsupported`, `linux_metric_invalid`, `linux_metric_sample_incompatible`;
- `linux_cwd_permission_denied`, `linux_cwd_unmapped`, `linux_cwd_changed`, `linux_cwd_redacted`;
- `linux_root_not_found`, `linux_root_unsafe_layout`, `linux_path_unregistered`, `linux_path_escape_rejected`, `linux_file_type_rejected`, `linux_file_permission_rejected`, `linux_file_too_large`, `linux_file_changed_during_read`, `linux_file_atime_policy_unsupported`;
- `linux_xdg_invalid`, `linux_xdg_permission_mismatch`;
- `linux_user_manager_unavailable`, `linux_user_unit_not_found`, `linux_user_unit_incompatible`, `linux_user_service_action_failed`;
- `linux_deadline_exceeded`, `linux_output_limit_exceeded`, `linux_internal_adapter_error`.

Errors expose only code, correlation ID, safe operation category, contract/source version, and bounded remediation category. They never expose raw path, PID tied to identity, username, command, environment, file content, subprocess stdout/stderr, unit content, provider output, traceback, or exception arguments.

### 4.7 Contract-impact assessment

This plan proposes Linux implementations of FND-owned CTR-PLAT-001 and
M06-owned CTR-RUN-006. It consumes but does not implement CTR-DEP-001, and it
changes no implemented contract. Before approval, root synchronization must:

1. decide whether M06 or a common platform package owns the portable process input DTO source file;
2. freeze process identity/scope/start/executable representation from M0 evidence;
3. freeze CPU/memory/state/cwd units and field states;
4. freeze provider selector, root-spec, file-spec, access-grant, and ephemeral-payload ownership across M02/M03/A01–A04;
5. determine whether a raw cwd can ever cross A04; the default plan says no;
6. allocate CTR-PLAT-001 path/service/health operations and their macOS-portable subset;
7. freeze systemd source/dependency and CTR-PLAT-001 primitive receipts against
   PLAN-DEP-owned service action/idempotency/rollback semantics;
8. allocate Foundation safe-subprocess and automation contracts;
9. update the central contract register and every known consumer;
10. add an ADR/threat update for any weaker path/source policy, privileged helper, environment access, process control, or raw path disclosure.

## 5. Data and persistence

A04-LINUX owns no database table, migration, repository, retention job, backup record, or historical projection.

Permitted adapter state is limited to immutable in-process registries, bounded short-lived process samples, open descriptors during an operation, and safe capability/version caches with explicit generation/expiry. It cannot persist raw process snapshots, PIDs, paths, provider bytes, unit output, mount data, or subprocess output.

M06 owns process/session persistence. M02 owns installation/profile/root references. M08 owns diagnostics/health/backup catalogs. If later measurements show a need to persist Linux compatibility probes, the owning module and schema must be decided through a contract change; A04 does not create a private cache table or file.

Temporary AgentMonitor-owned files used by safe filesystem or unit installation are created only under an approved AgentMonitor state/target directory with owner-only permissions, explicit size bounds, atomic replacement, fsync policy, cleanup, and rollback defined by PLAN-DEP. Provider-owned roots never receive temp, lock, marker, or backup files.

## 6. External and platform boundaries

### 6.1 Candidate Linux process sources

M0 must approve the exact minimum set. Candidate official kernel surfaces include numeric procfs process directories, process stat/status/statm-style metadata, executable and cwd links, boot/namespace scope identifiers, system clock-tick/page-size values, and kernel process state codes. Candidate mention is not approval.

Each admitted source record contains:

- official documentation/source reference and access date;
- supported kernel/distribution/procfs/mount/namespace scope;
- exact fields and parser schema version;
- unit/conversion/precision/sampling semantics;
- ownership/permission/hidepid behavior;
- read/atime/other side effects;
- race and revalidation method;
- output/privacy class;
- unknown-version and malformed-data behavior;
- real test/evidence reference.

Unadmitted fields are not parsed “for future use.” Parsers reject unexpected structure safely without logging raw input.

### 6.2 Distribution, kernel, procfs, and namespace compatibility

Support is capability-driven, not inferred solely from a distribution name. The real verification matrix must cover the target workstation and any additional supported distributions/kernels as real hosts. It records:

- distribution identifier/version and architecture;
- kernel release family and Python runtime;
- procfs mount presence/options relevant to visibility and atime;
- permission/hidepid/user-namespace/PID-namespace scope;
- clock tick/page size facts;
- systemd user-manager/session-bus/lingering state;
- filesystem type/features relevant to descriptor-relative/no-follow/atomic operations;
- current Claude/Codex/Ollama installation/process versions when provider claims are tested.

WSL, containers, chroots, alternate procfs mounts, non-systemd distributions, hardened kernels, and SELinux/AppArmor policy are separate scopes. They are `unverified` or `unsupported` until real evidence exists. A container or emulator cannot pass the target-workstation T5 gate. Missing environments are Blocked, not generalized from the target.

### 6.3 Timeouts and retry policy

- Every external operation receives a monotonic deadline and adapter hard maximum.
- Candidate count, result count, file count, bytes per file, bytes per batch, ancestry depth, service properties, stdout/stderr capture, and diagnostic fields are bounded.
- Procfs/file races may receive one immediate identity/descriptor revalidation only if the synchronized policy permits; there is no retry loop that chases a changing process/file.
- Systemd transient transport failure is reported to M04/DEP; A04 does not autonomously restart or repeatedly retry the user manager.
- Permission/auth/config failures are never retried automatically.
- Cancellation cleans up A04 work/descriptors/owned subprocess group only and never targets monitored PIDs.

Exact numerical bounds are approval blockers derived from real M0/performance evidence. They are not invented in this plan.

### 6.4 Safe subprocess boundary

If systemd inspection/lifecycle uses a command rather than an admitted D-Bus library:

- executable path/version is resolved and approved before invocation;
- direct argv only; no shell, glob, interpolation, response file, or provider input;
- fixed AgentMonitor unit and allowlisted properties/actions only;
- minimal explicit environment required for the real user manager, never the full application/provider environment;
- no secret arguments;
- bounded stdout/stderr/time/process-group cleanup;
- parse only documented machine-oriented output fields;
- raw output discarded before contract return and never logged;
- exit/signal/timeout/malformed states map to typed outcomes.

The safe subprocess executor is Foundation-owned. A04 cannot invent a competing helper.

### 6.5 Provider-filesystem boundary

Provider adapter files remain provider-owned and read-only. A04 enforces path mechanics; A01–A03 own schema/field parsing and must discard prohibited content before producing M03/M06 data. A04 does not know whether bytes represent Claude, Codex, or Ollama except through a registered opaque spec.

Default-profile protection is mandatory even though reads are permitted: no A04 contract can write, rename, chmod, touch, lock, truncate, delete, or relocate a provider root/file. Pre/post metadata reconciliation in live tests proves no intentional change within the approved method. If the filesystem necessarily updates atime and no non-mutating read is possible, the capability is Blocked/Unsupported until the owner/security decision explicitly accounts for it.

### 6.6 Real verification method

- T5 uses the real target Linux workstation and naturally running owner-identified Claude, Codex, and Ollama processes. A provider absent at the observation time is Blocked, not replaced.
- Generic race, limit, symlink, type, permission, TOCTOU, and 200-process mechanics may use bounded AgentMonitor-owned real processes/files on the real kernel/filesystem. These tests prove only platform mechanics and are never labeled provider evidence.
- Provider-root compatibility uses only owner-approved real installed provider roots/files and approved fields; generated structures cannot prove provider compatibility.
- Service inspection/lifecycle uses the real user systemd manager and real installed AgentMonitor unit. If unavailable, the scenario is Blocked/Unsupported for that environment.
- Distribution compatibility uses real hosts/runners of the claimed distribution/kernel; containers/emulators do not substitute.
- Owner validates representative provider process identities/hierarchies and acknowledges pre/post no-control/no-file-mutation checks.

## 7. Security and privacy

### 7.1 Threats and controls

| Threat | Required control and proof |
|---|---|
| PID reused during scan | scope + PID + start + executable identity; before/after validation; conflict discards facts |
| Process exits/reparents mid-scan | per-field race outcomes; no attachment to newly reused PID |
| Generic runtime mislabeled as provider | only registered evidence selectors; unresolved if command line would be needed |
| Command line/environment contains prompt/secret | those sources absent from contracts, imports, source registry, tests, and diagnostics |
| cwd leaks customer/project path | transient mapping to opaque approved root/safe label; no default raw output/log/event |
| Symlink/path traversal escapes root | descriptor-relative component walk; no-follow; fixed registered components; containment proof |
| TOCTOU swaps checked file | use held descriptors; fstat before/after; changed result discarded |
| FIFO/device/socket blocks or leaks | nonblocking safe open where applicable; opened-descriptor regular-file check before read |
| Huge/malformed provider file exhausts service | byte/time/count bounds; no mmap; typed invalid/oversize outcome |
| Read mutates atime/provider state | admitted no-atime/mount policy or capability refused; pre/post reconciliation |
| File bytes leak via repr/log/error | ephemeral redacted wrapper; allowlist logging; artifact/exception scans |
| Arbitrary unit/process controlled | closed fixed AgentMonitor unit/action; no target PID; no arbitrary unit/path/argv |
| systemd output leaks environment/path | allowlisted documented properties; raw output discarded |
| Root/capability escalation | refuse root/capabilities/polkit; user privilege only |
| Cancellation signals monitored agent | separate A04-owned worker process group/handles; monitored PIDs never cancellation targets |
| Platform failure cascades | typed bounded partial outcomes and module isolation |
| Hidden outbound telemetry | no network dependency, analytics, or crash reporting; egress inspection gate |

### 7.2 Prohibited-source register

The following are structurally prohibited, even if readable by the current user:

- target process environments;
- target process command lines;
- process memory, maps, debugger/ptrace surfaces;
- terminal devices, stdin/stdout/stderr content, shell history;
- arbitrary process file descriptors or network/socket payloads;
- arbitrary home/repository enumeration or source-file contents;
- provider credential/token/cookie/OTP/MFA/recovery files or fields;
- prompts, responses, tool inputs/outputs, transcript content, source code;
- raw systemd journal or unrestricted property dumps;
- kernel interfaces that control/signal/schedule/renice a monitored process.

Any future request to admit one requires stopping implementation and obtaining the requirement, threat model, ADR, contract major, field/privacy registration, test, and owner approvals. FR-DISC-007 specifically requires an ADR even for proposed allowlisted target-process environment metadata; this V1 plan admits none.

### 7.3 Least privilege and authorization

- Run as the same normal user as AgentMonitor, never root.
- No ambient Linux capabilities, setuid/setgid binary, sudo, broad group membership, or policy change.
- Process inspection is limited to facts exposed to the normal user and approved by source policy.
- Filesystem access grants are internal, purpose-bound, version-bound, time-bound, and root/file-specific.
- API users never submit filesystem paths, unit names, executable paths, or PIDs directly to A04.
- Service mutation requires deployment authority and owner-visible operation; query authority cannot be upgraded to mutation.
- Provider default profiles are read-only regardless of dashboard authorization.

### 7.4 Data minimization proof

Before implementation approval, every output field must appear in a Linux field register with requirement, exact source, source/version/platform scope, purpose, type/unit/precision, privacy class, request condition, allowed consumers, persistence/log/event/API/UI/export policy, freshness, and M0 evidence reference. A field absent from the register is rejected.

The proof combines:

- closed request/result schemas with unknown fields forbidden;
- imports/API/prohibited-symbol scans;
- source/path registry review;
- real output, error, log, evidence, API/DB/export/backup scans after integration;
- owner-reviewed no-control/no-profile-change live checks;
- absence of external network flows.

Redacting after unrestricted capture is not acceptable.

### 7.5 Logging and diagnostics

Allowed structured fields: event name, component, operation/correlation ID, safe installation/provider key, safe capability/error code, counts, bounded durations, adapter/contract/source versions, and capability state. PID is excluded unless a security-reviewed diagnostic requires a short-lived local correlation; raw paths and file/unit output are always excluded.

Local protected logs may retain exception type/stack only after argument/message redaction review. No input object, bytes, `repr` of external data, stdout/stderr, `/proc` line, unit property dump, or provider file metadata that reveals identity/path is logged.

Unexpected prohibited data stops the operation, invalidates privacy evidence, quarantines contaminated evidence outside Git without copying it into chat, and follows the incident runbook.

### 7.6 No-control proof

The canonical security gate must verify:

- public/internal schemas contain no signal/kill/pause/resume/attach/stdin/terminal/renice/route/switch-agent operation;
- production imports and symbols contain no ptrace/debugger/terminal/process-control path;
- any OS signal capability used to clean up an AgentMonitor-owned helper is encapsulated by Foundation and cannot receive a monitored PID;
- systemd actions accept only the fixed AgentMonitor unit;
- process and provider-file pre/post evidence is unchanged within the approved method;
- no provider default profile write is possible through filesystem/service ports.

## 8. Configuration and operations

### 8.1 Configuration ownership

A04 proposes no secret setting. It never reads `.env` itself and never receives provider credentials.

Candidate non-secret registry entries, pending Foundation/root allocation and real measurement:

| Candidate setting | Owner | Type/default | Validation | Reload | Visibility |
|---|---|---|---|---|---|
| Linux process candidate hard limit | A04 | positive integer; no default approved | measured safe min/max; cannot exceed compiled safety ceiling | restart or immutable startup | safe effective value |
| Linux process result hard limit | A04 | positive integer; no default approved | <= candidate limit | restart or immutable startup | safe effective value |
| Linux inspection hard deadline | A04 | duration; no default approved | bounds M04-requested deadline | restart | safe effective value |
| Approved file per-read byte ceiling | A04 security | bytes; no default approved | >= admitted file needs and <= measured ceiling | restart | safe effective value |
| Approved file per-batch byte ceiling | A04 security | bytes; no default approved | >= per-file; bounded | restart | safe effective value |
| Capability-profile refresh interval | A04 | duration; no default approved | bounded; version change can invalidate immediately | restart | safe effective value |

Provider filenames/roots/field allowlists belong to versioned adapter/source registries, not user-entered A04 environment keys. XDG source values follow Foundation/deployment policy. Poll cadence belongs to M04. Service artifact/unit values belong to PLAN-DEP. Exact `AGENTMONITOR_*` names are not allocated here.

### 8.2 Health and readiness

A04's CTR-OPS-006 contribution is bounded to:

- adapter/contract/build/source versions;
- capability states/counts by category;
- last process/root/file/service operation time, duration, and safe outcome code;
- procfs/source compatibility state;
- systemd user-manager/unit compatibility state;
- active operation count and hard-limit saturation state;
- last security-policy rejection count/time/code category;
- configuration validity and safe secret-free setting presence/source.

No health payload includes process list, PID, path, username, hostname, account identity, provider bytes, unit text/output, or exception text.

Invalid contract/config/source version makes the affected capability not ready. An absent provider process/root is not global unready. M08 timeout does not block A04 operations. Health probes perform no provider read/process scan/service mutation.

### 8.3 Operational procedures

The Linux operations document must contain verified procedures for:

- diagnose procfs unavailable/permission/hidepid/source-version outcomes;
- diagnose missed provider process without using command-line/environment/content;
- investigate PID reuse/race/parent ambiguity;
- review cwd mapping/privacy/permission outcomes;
- review unsafe root/symlink/type/atime/TOCTOU/oversize outcomes;
- diagnose XDG ownership/permission/path configuration;
- diagnose missing user systemd/session bus/unit/version and lingering state;
- verify no-control and no-provider-file-mutation after inspection;
- re-run compatibility after kernel, distribution, systemd, filesystem, Python, or provider version change;
- respond to prohibited data or secret/content capture.

Commands remain TBD until implemented and real-verified. No prose command is represented as executable automation.

### 8.4 Canonical automation obligations

A04 must integrate with repository-owned fail-closed routines; no private shell checklist substitutes:

- `AUTO-PLAN-CHECK`: validates this artifact, scenario count/IDs, registry link, and CS synchronization inclusion.
- `AUTO-DOCS-CHECK`: validates requirements/contracts/field/source/compatibility links and prohibited sensitive examples.
- `AUTO-TEST`: selects `platform-linux` T5 and integrated T6/T7 rows, records exact real boundary, and preserves Passed/Failed/Blocked/Not Run separately.
- `AUTO-QUALITY`: formatting, strict typing, import boundary, prohibited-symbol/API/source scan, secret/content scan, dependency/license scan, and contract compatibility.
- `AUTO-GIT-PREFLIGHT`: checks only repository state and secrets; it does not inspect provider state.
- `AUTO-BUILD`: reproduces locked artifacts/SBOM/notices and includes the adapter/source/build versions.
- `AUTO-DEPLOY`: invokes approved CTR-DEP-001 for the fixed AgentMonitor user service and captures rollback evidence.
- `AUTO-RELEASE`: refuses release if required target Linux/platform/provider rows are Failed/Blocked/Not Run contrary to the acceptance policy.

The exact executable command/selector is Foundation/integration-owned and must exist, be documented, and be tested on the real boundary before A04 can be called implementation-ready. A manual successful run cannot satisfy the automation gate. Hosted CI cannot mark target-workstation/provider T5/T6 Passed.

### 8.5 Operational metrics and resource bounds

A04 may expose local counts/durations for its own operations only: candidates examined, results returned, field failures by safe code, bytes read, deadline/limit events, capability state, and operation duration. It sends no telemetry. Labels cannot contain PID, path, account, process name, unit output, or provider content.

Resource ceilings and performance budgets are selected from real measurements. A runaway scan/file/service call is terminated within its own A04 work boundary without signaling provider processes.

## 9. Test design before implementation

### 9.1 Evidence state and integrity rules

Every scenario in this section is **Not Run**. A future Red is valid only when the test executes the correct real production boundary and fails because required behavior is missing or wrong. Syntax errors, missing packages, absent credentials/processes, an unavailable platform, or an unapproved source are not Red.

Rules:

- no mocks, fakes, stubs, monkeypatches, emulators, replayed procfs/provider files, recorded systemd output, generated provider trees, seeded telemetry, placeholder process values, or test-only production paths;
- T5 provider claims use naturally running real Claude/Codex/Ollama processes and actual approved provider roots;
- bounded AgentMonitor-owned real processes/files may prove generic kernel/filesystem mechanics only and are labeled as such;
- tests do not terminate/restart/signal or feed input to provider agents;
- systemd lifecycle tests are owner/deployment coordinated against the real AgentMonitor user service, not an emulated manager;
- real unavailable cases are Blocked, not skipped into success;
- output/evidence is allowlisted and secret/content scanned before retention;
- every implemented scenario records Red, Green, post-refactor commands, timestamps, exact host/source versions, status, and sanitized evidence reference.

### 9.2 Real process inspection — T5

| Test ID | Requirement | Real dependencies | Expected behavioral Red | Pass condition | Owner/live coordination |
|---|---|---|---|---|---|
| LNX-PROC-001 | FR-DISC-001 | target Linux + naturally running approved provider process | real process omitted | approved candidate is discovered without launch change | owner identifies candidate |
| LNX-PROC-002 | FR-DISC-001 | simultaneous real Claude/Codex/Ollama where available | generic/process/provider misclassification | each observed candidate is correctly scoped or explicitly unresolved | absent provider is Blocked |
| LNX-PROC-003 | FR-DISC-002 | real process + approved procfs source | PID accepted without start/scope/executable | complete identity tuple is present | none beyond safe identity check |
| LNX-PROC-004 | FR-DISC-002 | real stable process sampled twice | identity changes or timestamp drift mislabeled | exact identity stable and observation times differ correctly | provider process not controlled |
| LNX-PROC-005 | R-015 | naturally occurring or bounded real owned PID reuse | reused PID merged | reused instance rejected/distinguished | Blocked until real reuse observed if necessary |
| LNX-PROC-006 | NFR-RES-001 | real owned process exits during inspection | stale values returned as current process | typed exit/race and no ambiguous facts | only A04-owned harmless process may be started/exited |
| LNX-PROC-007 | NFR-RES-001 | real inaccessible/exited process mixed with accessible processes | one failure aborts batch | partial batch preserves independent valid entries | no privilege escalation |
| LNX-PROC-008 | FR-DISC-005 | representative real parent/child agent tree | PPID alone becomes durable parent | parent identity validated or unresolved | owner identifies expected tree |
| LNX-PROC-009 | FR-DISC-005 | real wrapper/provider descendant tree | wrapper silently removed/promoted | platform ancestry preserves wrapper and evidence | owner comparison |
| LNX-PROC-010 | FR-DISC-005 | naturally reparented/orphaned or real owned lifecycle | child attached to reused/new parent | orphan/reparent ambiguity explicit | provider process not induced to exit |
| LNX-PROC-011 | FR-DISC-002 | real process resource source | tick/page constants assumed | runtime source values and exact units used | source reconciled |
| LNX-PROC-012 | FR-DISC-002 | two real samples over measured monotonic interval | CPU percent from one sample/unlabeled | cumulative/sample/normalization semantics exact | no load injected into provider process |
| LNX-PROC-013 | FR-DISC-002 | real memory source | pages labeled bytes or wrong memory kind | resident bytes reconcile within source precision | approved authoritative comparison |
| LNX-PROC-014 | FR-DISC-002 | real process state transitions naturally available | unknown state guessed | raw safe state/version preserved; normalized state left to M06 | unavailable transition is Blocked |
| LNX-PROC-015 | FR-DISC-004 | generic executable/weak evidence case | process auto-mapped to provider/account | generic/unresolved result with evidence state | owner confirms no guess |

### 9.3 Real approved filesystem and provider-root behavior — T5

| Test ID | Requirement | Real dependencies | Expected behavioral Red | Pass condition | Owner/live coordination |
|---|---|---|---|---|---|
| LNX-FS-001 | FR-DISC-003 | real approved provider root | adapter searches unregistered locations | only registered finite candidates evaluated | owner approves root class |
| LNX-FS-002 | NFR-SEC-001 | real AgentMonitor-owned isolated filesystem | `..`/absolute/separator escape accepted | invalid component rejected before target read | generic mechanic only |
| LNX-FS-003 | NFR-SEC-001 | real symlink inside isolated root | final symlink followed | no-follow rejection | generic mechanic only |
| LNX-FS-004 | NFR-SEC-001 | real intermediate symlink escape | traversal leaves root | descriptor-relative walk rejects escape | generic mechanic only |
| LNX-FS-005 | NFR-SEC-001 | real FIFO/socket/device candidate in isolated root | read blocks or special object accepted | non-regular type rejected within deadline | safe owned artifacts only |
| LNX-FS-006 | NFR-SEC-001 | real oversized owned file | full file read/retained | max+1 detects oversize; no payload returned | generic mechanic only |
| LNX-FS-007 | NFR-SEC-001 | real permission-restricted owned file/root | permission treated missing or bypassed | typed permission denial; no chmod/root | generic mechanic only |
| LNX-FS-008 | NFR-SEC-001 | real owned path swapped during read | checked path reopened unsafely | descriptor identity/change check rejects payload | bounded safe race harness |
| LNX-FS-009 | FR-DISC-003 | real approved provider file | read updates prohibited metadata/provider state | approved atime policy holds or scenario is Blocked/Unsupported | owner reviews pre/post |
| LNX-FS-010 | FR-DISC-003 | real approved provider file/version | unknown file spec/version read anyway | no I/O for unregistered/incompatible spec | owner approves source scope |
| LNX-FS-011 | NFR-RES-001 | two real approved files, one failing | one failure aborts unrelated read capability | typed isolation/partial outcome | real roots only for provider claim |
| LNX-FS-012 | NFR-RES-001 | real file changes naturally or owned race | mixed-version bytes accepted | changed result rejected without raw evidence | no provider file modification induced |
| LNX-FS-013 | NFR-PRIV-001 | real approved file through production parser | raw payload appears in logs/errors/artifacts | payload remains ephemeral and outputs scan clean | owner-approved safe field only |
| LNX-FS-014 | FR-DISC-003 | real default provider profile | read primitive exposes any write/repair path | pre/post approved metadata unchanged; no write capability | owner acknowledges |

### 9.4 Real working-directory and XDG behavior — T5

| Test ID | Requirement | Real dependencies | Expected behavioral Red | Pass condition | Owner/live coordination |
|---|---|---|---|---|---|
| LNX-CWD-001 | FR-DISC-002 | real provider process with permitted cwd | raw path logged/returned by default | opaque mapped ref/safe label or explicit state only | owner approves visibility |
| LNX-CWD-002 | FR-DISC-002 | real cwd permission denial/unavailability | guessed/stale cwd returned | typed denial/exit/unmapped state | naturally available or Blocked |
| LNX-CWD-003 | FR-DISC-002 | real deleted/moved cwd or owned process | deleted suffix/path treated normal | explicit deleted/changed state | generic mechanics may use owned process |
| LNX-CWD-004 | NFR-SEC-001 | real cwd through symlink/bind behavior | lexical prefix proves containment | filesystem identity/approved policy or unresolved | host filesystem scope recorded |
| LNX-XDG-001 | FR-OPS-001 | real target user's startup context | wrong default/relative path accepted | path classes resolve per approved XDG source | no path printed in report |
| LNX-XDG-002 | FR-OPS-001 | real child process with isolated valid XDG dirs | global environment mutated | child-only production loader resolves isolated paths | generic path rule only |
| LNX-XDG-003 | NFR-SEC-001 | real invalid/relative XDG source in isolated child | unsafe path accepted/created | fail closed with safe setting name | no operator path mutation |
| LNX-XDG-004 | NFR-SEC-001 | real wrong-owner/mode/type owned test target | path string treated safe | typed ownership/mode/type mismatch | generic mechanic only |
| LNX-XDG-005 | FR-OPS-001 | real resolution call | resolving creates/changes filesystem | no creation/write occurs | pre/post filesystem check |

### 9.5 Real systemd user-service and lifecycle behavior — T5/T7

| Test ID | Requirement | Real dependencies | Expected behavioral Red | Pass condition | Owner/live coordination |
|---|---|---|---|---|---|
| LNX-SVC-001 | FR-OPS-001 | real target user systemd manager | manager assumed available | supported or explicit unavailable with version/source | owner session context |
| LNX-SVC-002 | FR-OPS-001 | real installed AgentMonitor unit | arbitrary unit/property access possible | fixed unit and property allowlist only | deployment-installed service |
| LNX-SVC-003 | FR-OPS-001 | real AgentMonitor unit state | PID existence called healthy | typed unit state plus application readiness distinction | M08/DEP integration |
| LNX-SVC-004 | FR-OPS-001 | real enabled/disabled login policy | lingering silently enabled/assumed | actual state reported; no lingering mutation | owner reviews decision |
| LNX-SVC-005 | FR-OPS-001 | real approved unit artifact install/upgrade | unversioned/non-atomic overwrite | digest/version preflight, atomic install, recoverable prior artifact | explicit PLAN-DEP owner checkpoint |
| LNX-SVC-006 | NFR-RES-001 | real failed/denied user-manager action naturally available | failure corrupts unit/other capability | typed failure; previous artifact/state recoverable; process adapter stays available | do not manufacture harmful failure |
| LNX-SVC-007 | AC-OPS-001 | real start/stop/restart/status of AgentMonitor | arbitrary/provider process affected | only AgentMonitor service changes and readiness verified | explicit owner/deployment window |
| LNX-SVC-008 | AC-OPS-001 | real login/autostart behavior | enabled flag assumed proof | actual next-login behavior verified; lingering choice recorded | may require owner login cycle |

### 9.6 Real provider-process/live integration — T5/T6

| Test ID | Requirement | Real dependencies | Expected behavioral Red | Pass condition | Owner/live coordination |
|---|---|---|---|---|---|
| LNX-LIVE-001 | AC-PROC-001 | naturally running Claude agent | missed/misidentified or workflow changed | correct safe process observation/no input/state change | owner present |
| LNX-LIVE-002 | AC-PROC-001 | naturally running Codex agent | missed/misidentified or workflow changed | correct safe process observation/no input/state change | owner present |
| LNX-LIVE-003 | AC-PROC-001 | naturally running Ollama agent/service process | local/cloud/service role conflated | exact observed role or unresolved; no control | owner present |
| LNX-LIVE-004 | FR-DISC-003 | real approved Claude root/file | generated/recorded file used or raw bytes retained | actual approved source parsed safely; unchanged | owner approves read |
| LNX-LIVE-005 | FR-DISC-003 | real approved Codex root/file | generated/recorded file used or raw bytes retained | actual approved source parsed safely; unchanged | owner approves read |
| LNX-LIVE-006 | FR-DISC-003 | real approved Ollama root/file | generated/recorded file used or raw bytes retained | actual approved source parsed safely; unchanged | owner approves read |
| LNX-LIVE-007 | AC-PROC-003 | real account/session/process evidence | current login/path/timing silently maps account | Strong/corroborated/owner-confirmed or Unresolved preserved | owner validates mapping conclusion |
| LNX-LIVE-008 | AC-PROC-002 | representative real parent/subagent trees | OS relation mislabeled provider hierarchy | M06 combined tree matches owner or shows conflict/unresolved | owner identifies expected hierarchy |
| LNX-LIVE-009 | AC-PROC-005 | real sessions with naturally visible activity/wait evidence | platform metric alone marks stuck/wait | A04 facts retain certainty/source and M06 applies policy | unavailable state Blocked |

### 9.7 Security, privacy, architecture, operations, compatibility, and performance

| Test ID | Layer | Requirement | Real dependencies | Expected behavioral Red | Pass condition |
|---|---|---|---|---|---|
| LNX-SEC-001 | T5/static | FR-DISC-007 | production source + real run | target environment path exists or is read | no source/schema/import/read of target environment |
| LNX-SEC-002 | T5/static | NFR-PRIV-001 | production source + real run | command line/memory/terminal/fd content read | prohibited sources absent and real output clean |
| LNX-SEC-003 | T5/integration | FR-OPS-005 | real logs/errors/diagnostics | raw path/provider bytes/stdout leaks | allowlist scan clean |
| LNX-SEC-004 | T5/integration | AC-PROC-004 | real A04→M06→DB/API/export flow | prohibited field persists | schema/data/artifacts contain none |
| LNX-SEC-005 | T5 | NFR-OBS-001 | real failures | exception/input dump leaks | safe structured code/correlation only |
| LNX-SEC-006 | T5 | NFR-PRIV-002 | real service under network observation | analytics/crash egress occurs | no A04 external egress |
| LNX-SEC-007 | static/contract | FR-SAFE-002 | production contracts/source | control verb/type/import exposed | prohibited API/symbol scan green |
| LNX-SEC-008 | T5 | FR-SAFE-002 | real inspected provider process | cancellation/timeout signals target | only A04-owned work stops; target unchanged |
| LNX-SEC-009 | T5/live | AC-PROC-001 | real provider processes | observation changes PID/start/state/input | approved pre/post check unchanged |
| LNX-SEC-010 | T5/T7 | FR-SAFE-002 | real systemd service action | arbitrary/provider unit accepted | only fixed AgentMonitor unit is addressable |
| LNX-ARCH-001 | automated | NFR-ARCH-001 | real source tree | forbidden module/internal import | import-boundary gate rejects violation |
| LNX-ARCH-002 | automated | NFR-ARCH-002 | generated contract schema | Linux field leaks unversioned into domain | only synchronized DTOs cross boundary |
| LNX-ARCH-003 | contract | NFR-PLAT-001 | Linux and macOS plan/contracts | portable contract requires procfs/systemd | macOS can implement semantics without Linux imports/fields |
| LNX-OPS-001 | T5 | NFR-OBS-001 | real operations/log sink | health/log emits sensitive identity | safe bounded events only |
| LNX-OPS-002 | T7 | AC-OPS-002 | installed real service, browser closed | inspection/collection stops with browser | service continues and health remains available |
| LNX-OPS-003 | integration | AC-OPS-003 | real denied/malformed/unavailable source | A04 failure takes API/other adapter down | affected capability degrades only |
| LNX-OPS-004 | automated/docs | NFR-DOC-001 | repository docs | plan/module/source/runbook links stale | AUTO-DOCS-CHECK passes exact artifacts |
| LNX-COMP-001 | T5 | NFR-PLAT-001 | target distribution/kernel | target unverified | exact matrix row passes or limitation recorded |
| LNX-COMP-002 | T5 | NFR-PLAT-001 | each additional claimed real host | target result generalized | each claim has its own real evidence |
| LNX-COMP-003 | T5 | FR-DISC-008 | source/kernel change | old parser silently accepts change | incompatible/unverified until live revalidation |
| LNX-COMP-004 | T5/T6 | FR-DISC-008 | provider version change | provider selector/root spec silently reused | affected capability unverified until evidence |
| LNX-COMP-005 | T5 | NFR-COMP-001 | prior/current contract producer-consumer | breaking unit/state meaning accepted | compatibility gate fails breaking drift |
| LNX-COMP-006 | T5 | FR-OPS-006 | real installed build/source/service | version absent/mismatched | safe versions visible; mismatch explicit |
| LNX-PERF-001 | T5 | NFR-PERF-001 | real host with >=200 real processes | scan breaches synchronized latency/CPU/memory budget | measured bounded result without content capture |
| LNX-PERF-002 | T5 | NFR-PERF-001 | real 200-process AgentMonitor-owned bounded workload if natural host insufficient | workload mislabeled provider evidence or resource leak | generic mechanics meet budget; provider claims separate |
| LNX-PERF-003 | T5 | NFR-RES-001 | concurrent real bounded requests | fd/task/output leak or starvation | hard ceilings, cleanup, independent progress |
| LNX-QUAL-001 | automated | NFR-LIC-001 | real lock/SBOM/notices | unadmitted dependency/tool omitted | admission and artifacts match actual graph |

This inventory defines 82 stable `LNX-*` scenarios. The canonical validator, not this prose count, is authoritative and must fail on missing/duplicate IDs or a count below the planning catalog threshold.

### 9.8 Failure, race, recovery, and unavailable coverage

The matrix covers source absent/incompatible, permission denial, process exit/PID reuse/reparenting, incomplete identity, unsupported field, time conversion, metric sample mismatch, cwd denied/deleted/unmapped, root absent/unsafe, symlink/path escape, non-regular type, oversize, atime policy, TOCTOU/file mutation, unknown provider spec, deadline/output limits, systemd absent/denied/failed/incompatible, browser closure, module failure isolation, version drift, concurrent saturation, and cleanup.

Rare PID reuse, naturally changing provider files, login/autostart cycles, unavailable provider processes, or denied real provider roots may remain Blocked until safely available. A constructed pure-policy test cannot convert those live rows to Passed.

### 9.9 Red-green-refactor evidence protocol

For each increment:

1. register scenario IDs and exact real boundary in the canonical selector;
2. execute Red and retain sanitized command, environment/source versions, timestamp, expected behavioral failure, exit status, and evidence reference;
3. make the minimum production change;
4. execute Green at the same boundary;
5. refactor, rerun the scenario plus affected regression/security/quality selectors;
6. record Failed/Blocked/Not Run separately;
7. scan logs/artifacts/evidence for secrets/content/path leakage;
8. update contract/source/field/compatibility/documentation in the same change.

Unavailable dependency, absent provider process, missing user manager, or setup error is Blocked/Not Run, not Red. No retry converts flakiness to Passed.

## 10. Implementation increments

No increment starts until its required M0 fact, contract, dependency, canonical test selector, and file ownership are approved.

| Increment | Files/area | Failing test first | Production change | Refactor/documentation | Exit evidence |
|---|---|---|---|---|---|
| LNX-I00 | contracts/source/field registries | LNX-ARCH-001..003, LNX-COMP-005 | approved DTO bindings and closed registries only | contract docs/register | compatibility/boundary gate |
| LNX-I01 | capability_probe.py | LNX-COMP-001/003/006 | safe real capability/version probe | compatibility doc | target T5 Red/Green |
| LNX-I02 | procfs.py/models.py | LNX-PROC-003/004/006 | identity-stable single-process inspection | source/identity docs | real process evidence |
| LNX-I03 | process_metrics.py | LNX-PROC-011..014 | exact time/CPU/memory/state facts | units/precision register | real reconciliation |
| LNX-I04 | process_inspector.py | LNX-PROC-001/002/007/015 | bounded selection/batch/partial outcomes | selector/limit docs | real provider/generic evidence |
| LNX-I05 | ancestry/cwd paths | LNX-PROC-008..010, LNX-CWD-001..004 | validated parent evidence and safe cwd mapping | privacy/hierarchy docs | representative trees |
| LNX-I06 | approved_roots.py | LNX-FS-001/002/010/014 | finite root/access-grant registry | provider handoff docs | real approved roots |
| LNX-I07 | safe_file_reader.py | LNX-FS-003..009/011/012 | descriptor-relative bounded read | threat/source docs | real filesystem evidence |
| LNX-I08 | provider parser handoff | LNX-FS-013, LNX-LIVE-004..006 | ephemeral payload integration | field/privacy proof | real provider root evidence |
| LNX-I09 | xdg_paths.py | LNX-XDG-001..005 | pure resolution plus real ownership/type observation, no creation | configuration/deployment docs | real XDG evidence |
| LNX-I10 | systemd_user.py inspection | LNX-SVC-001..004 | fixed-unit read-only status | operations/compatibility docs | real user manager evidence |
| LNX-I11 | health.py | LNX-OPS-001/003, LNX-SEC-003/005 | bounded health/log/error integration | diagnostics runbook | real degraded-state evidence |
| LNX-I12 | deployment-authorized service lifecycle | LNX-SVC-005..008, LNX-SEC-010 | fixed-unit install/action/rollback mechanics | deploy/rollback docs | owner-coordinated real T7 |
| LNX-I13 | full M06/provider integration | LNX-LIVE-001..009, LNX-SEC-004/008/009 | composition wiring through approved ports | live matrix/handoff | owner-acknowledged T5/T6 |
| LNX-I14 | hardening/performance | LNX-SEC-001..010, LNX-PERF-001..003, LNX-QUAL-001 | bounds, cleanup, automated negative gates | final compatibility/risk docs | canonical quality/security/perf evidence |

### 10.1 Ordering and parallel safety

- I00 is centrally synchronized and serial.
- I01–I05 can proceed inside the Linux path after CTR-RUN-006 freeze; they must not edit M06.
- I06–I08 require approved A01–A03 root/file specs but can implement generic mechanics without provider branches.
- I09 is isolated after Foundation/deployment path contracts freeze.
- I10 is read-only and may proceed after systemd source selection; I12 waits for PLAN-DEP and explicit mutation ownership.
- I11 consumes only CTR-OPS-006.
- I13 composition/generated/shared changes are root-owned integration, not an A04 unilateral edit.
- One agent owns the Linux adapter path at a time; real live sessions are centrally scheduled to avoid disturbing development.

### 10.2 Stop conditions during implementation

Stop and escalate if:

- M0 evidence is absent, broader/narrower, or contradicts a proposed source/field/unit;
- provider identification appears to require command-line/environment/terminal/content;
- path safety appears to require string validate-then-reopen, following unapproved symlinks, or provider-directory writes;
- no-atime/read-only behavior cannot meet the approved side-effect budget;
- root, capabilities, sudo, polkit, broad group access, or user policy mutation appears necessary;
- a dependency/source license, maintenance, security, telemetry, native-code, or provenance risk is unapproved;
- a raw path, PID-linked identity, content, secret, provider bytes, or systemd output enters a log/artifact/report;
- a monitored/provider process receives a signal/input/state change;
- shared contract/file/migration/composition ownership is needed unexpectedly;
- a systemd operation could target anything except the fixed AgentMonitor unit;
- real test needs login/logout, provider mutation, agent interruption, or other owner authority not already approved.

## 11. Documentation outputs

Before implementation handoff, create/update through assigned ownership:

- `docs/modules/platform/linux.md`: purpose, sources, ports, field/error semantics, boundaries, compatibility, health, and limitations;
- `docs/operations/linux-platform-diagnostics.md`: verified safe diagnostics and incident paths;
- `docs/reference/linux-platform-compatibility.md`: real distribution/kernel/procfs/filesystem/systemd/provider-version matrix with Blocked rows;
- Linux field/source/privacy registry with M0 evidence references;
- CTR-PLAT-001, CTR-RUN-006 implementation, and CTR-DEP-001 compatibility documentation;
- configuration registry entries after allocation;
- threat model and ADR if any approved decision changes existing safety assumptions;
- provider adapter handoff notes for registered roots/file specs and ephemeral parsing;
- M06 handoff notes for identity/units/cwd/ancestry/outcomes;
- PLAN-DEP service/source/action/rollback handoff;
- canonical automation selector documentation;
- test evidence and live owner-acknowledged reports;
- traceability, risk register, planning registry, release notes, and known limitations.

No document/example includes a real username, hostname, absolute provider/project path, PID tied to identity, provider file/schema value, command line, environment, content, secret, raw output, or screenshot of sensitive state. Structural examples are explicitly non-live and cannot serve as evidence.

## 12. Dependency and license impact

### 12.1 Initial dependency position

The preferred process/filesystem/XDG implementation uses approved Python standard-library and documented Linux interfaces. This is not permission to hand-roll unsafe parsing: every parser and filesystem primitive still needs source/security review and real tests.

No new Python dependency is approved by this plan. Specifically:

- `psutil` is not selected. It may be evaluated only if raw procfs implementation cannot safely satisfy portability/race/unit requirements. The review must prove its exact source behavior does not read prohibited fields or add control APIs to the exposed surface.
- A D-Bus client is not selected. It may be evaluated against the approved fixed-argv systemd tool boundary for schema stability, dependencies, async behavior, maintenance, and license.
- inotify/watchdog-style packages are not selected; V1 polling does not require filesystem watches.
- no privileged helper, native extension, eBPF, ptrace, or process supervisor package is admissible under this scope.

External Linux/systemd executables/interfaces are runtime dependencies and receive version/source/behavior review even if they are not package-manifest dependencies.

### 12.2 Admission record required before any selection

For every package/tool, record canonical upstream/package identity, exact pinned/minimum-supported version, purpose, standard-library/existing alternative, direct/transitive licenses, maintenance/release/security policy, provenance/ownership, vulnerabilities/compromise history, native components/install scripts, supported distributions/Python, network/telemetry behavior, resource impact, lock/SBOM/notices effect, update/removal strategy, alternatives, reviewer, and date.

Copyleft/custom/unclear licensing requires explicit owner approval. No dependency manifest/lockfile changes within the A04 implementation packet without assigned ownership and admission approval.

## 13. Risks and unresolved decisions

### 13.1 Risk register

| Risk/question | Likelihood/impact | Mitigation/evidence | Owner | Trigger/deadline | Status |
|---|---|---|---|---|---|
| R-003 process cannot correlate to session/account | High/Critical | A04 supplies facts/evidence only; unresolved without M06/provider proof | M06/M02/A01–A04 | generic runtime or missing join key | Open |
| R-004 provider profile/process disturbed | Low/Critical | no-control/read-only contracts, atime decision, live pre/post proof | A04/security | any state/metadata change | Open |
| R-005 content/secret/environment leak | Medium/Critical | prohibited sources, ephemeral bytes, closed fields, output scans | A04/security | unexpected field/output | Open |
| R-009 rare races unavailable | High/Major | real owned mechanics plus visible Blocked provider rows | test steward | safe natural state absent | Accepted project risk |
| R-010 live test interrupts development | Medium/Major | owner window, natural agents, no control, immediate stop | live operator | agent/provider reaction | Open |
| R-015 PID reuse/hierarchy ambiguity | Medium/Major | full tuple, before/after check, unknown on conflict | A04/M06 | reuse/reparent/wrapper ambiguity | Open |
| R-019 CI mistaken for workstation evidence | Medium/Major | T5/T6 split and target-host evidence | integration | aggregate green status | Open |
| R-023 Linux leaks into macOS/core | Medium/Major | portable contract, import/schema gate, A04-MAC review | platform owners | procfs/systemd field crosses contract | Open |
| TOCTOU/path escape | Medium/Critical | descriptor-relative no-follow traversal and real race tests | A04/security | path reopen/symlink/mount ambiguity | Open |
| atime violates read-only promise | Medium/Major | M0 mount/open evidence; fail closed if not safe | A04/security | metadata changes on read | Open |
| hardened kernel hides metadata | Medium/Major | capability-specific unavailable/permission outcomes | A04 | hidepid/LSM/namespace restriction | Open |
| generic executable prevents provider discovery | High/Major | corroborated provider source or explicit unsupported/unresolved | A01–A04/M06 | command line would be required | Open |
| systemd absent/nonstandard | Medium/Major | independent process/filesystem capabilities; deployment limitation | A04/DEP | no real user manager | Open |
| service lifecycle targets wrong unit | Low/Critical | fixed identifier/artifact, expected version, real rollback tests | A04/DEP/security | arbitrary unit/value enters request | Open |
| adapter scan impacts host | Medium/Major | measured limits, deadlines, concurrency, no broad scans | A04/M04 | latency/CPU/fd ceiling | Open |

### 13.2 Approval-blocking synchronization decisions

1. Exact target Linux distribution/kernel/architecture/procfs/filesystem/systemd scope from M0.
2. Exact process start marker, boot/namespace scope, executable fingerprint, and precision.
3. Approved process selector evidence for each Claude/Codex/Ollama installation/version without command line.
4. Exact procfs/source fields and parser/version behavior.
5. Exact CPU time/utilization, memory, elapsed, and process-state semantics/units.
6. Parent validation, reparent/orphan/wrapper, co-observation, and ancestry ambiguity semantics.
7. Whether raw cwd ever crosses A04; proposed answer is no by default.
8. Registered root/file-spec/access-grant ownership and versioning across M02/M03/A01–A04.
9. Descriptor-relative/no-follow/atime/TOCTOU mechanism for the real Python/kernel/filesystems.
10. Ephemeral payload type ownership and enforceable no-log/no-persist behavior.
11. Exact hard limits/deadlines/concurrency/performance budgets.
12. XDG source/default/path/ownership/permission contract and creation ownership.
13. systemd inspection source: admitted D-Bus library versus fixed safe subprocess.
14. Fixed AgentMonitor unit identifier, artifact source/digest/version, lifecycle actions, idempotency, readiness, and rollback under CTR-DEP-001.
15. User lingering decision and explicit prohibition on implicit enablement.
16. Exact CTR-PLAT-001 portable subset required by A04-MAC.
17. Foundation safe-subprocess, configuration, logging, build, test-evidence, and automation commands/selectors.
18. Real supported distribution/kernel matrix beyond the owner's target; missing hosts stay Blocked.
19. Dependency/tool admission and exact runtime/Python baseline.
20. Whether any M0 finding requires requirement/architecture/security/risk/ADR change.

No implementation agent may choose among materially different answers. The item remains a visible gate until root, producer/consumers, security/test/operations, and owner approve as applicable.

### 13.3 M0 and owner checkpoints

- Owner identifies naturally running representative processes and expected human-level hierarchy.
- Owner approves each provider root/file observation and cwd visibility.
- Owner is present for live provider/system checks and can stop immediately.
- Owner/deployment explicitly authorizes the service lifecycle window; inspection alone grants no mutation authority.
- Owner decides lingering separately; no automation changes it implicitly.
- No login/logout/reauth/profile movement is requested by this plan.

## 14. Delivery and rollback

### 14.1 Delivery order

1. Complete and review `M0-LNX-001..013` plus systemd/XDG/atime findings.
2. Synchronize CTR-RUN-006, CTR-PLAT-001, root/file/access-grant, health, and portable macOS semantics.
3. Approve source/field/privacy/compatibility/dependency registers and this plan.
4. Implement I00–I05 through real T5 Red/Green/refactor with process capability disabled by default until verified.
5. Implement I06–I08 per approved provider source/spec, one real capability/version at a time.
6. Implement XDG and read-only service inspection.
7. Integrate M06/A01–A03/M08 through composition-owned changes.
8. Only after PLAN-DEP approval implement the fixed AgentMonitor service lifecycle and run T7.
9. Run full real Linux/provider/security/performance/operations matrix; preserve all Failed/Blocked/Not Run states.
10. Complete compatibility, license, threat, documentation, rollback, and release reviews.

### 14.2 Exposure and compatibility

Every capability starts disabled/unverified unless the exact source/platform/provider version is approved and live-verified. A version change moves the affected capability to unverified without disabling unrelated capabilities. The API/UI must show unsupported/unavailable/permission/unverified states through M06/M08, never cached-as-current fallback.

Changes to identity, units, field privacy, path containment, read side effects, error meaning, service target/actions, or portable semantics require contract review and may require a major/ADR. Additive optional fields need source/privacy evidence and consumer-safe absence.

### 14.3 Rollback and recovery

- Process/file/XDG inspection is deployed capability-disabled and can be disabled per source/version without deleting history.
- A failing source/parser rolls back to `unverified/unsupported`, not an older unverified parser or invented value.
- A04 owns no database rollback.
- Provider-owned files/profiles are never changed, so rollback never “restores” them.
- AgentMonitor unit installation/upgrade preserves a verified prior AgentMonitor-owned unit artifact and its metadata. Failed lifecycle action follows CTR-DEP-001 rollback and readiness verification.
- If rollback itself fails, leave the service stopped/failed with explicit safe diagnosis; do not alter unrelated units or use root escalation.
- Existing provider processes are never part of rollback.

### 14.4 Post-deployment checks

- adapter/contract/source/kernel/systemd/build versions match approved compatibility rows;
- capability/health states are accurate and partial failures isolated;
- current real provider processes appear only with complete identities and approved evidence;
- PID/parent/cwd/CPU/memory/state fields have correct units/source/precision;
- real provider roots/files remain unchanged within the approved check;
- logs/diagnostics/API/DB/export/backup/evidence contain no prohibited data;
- no provider process receives input/signal/restart/control;
- systemd lifecycle can address only the fixed AgentMonitor unit and readiness is verified;
- browser closure does not stop service collection;
- every unavailable platform/provider/distribution scenario remains visibly Blocked/Not Run.

### 14.5 Implementation handoff contents

The handoff must name requirement/AC IDs, plan/contract/source/schema versions, exact files and shared integration assignments, Red/Green/refactor commands/results, real host/distribution/kernel/procfs/filesystem/systemd/provider versions, owner acknowledgements, Passed/Failed/Blocked/Not Run rows, process/provider/service side-effect reconciliation, compatibility diff, security/privacy/no-control proof, dependency/license/SBOM/notices impact, performance/resource results, rollback/recovery evidence, documentation changes, risks, and exact next integration step.

## 15. Definition of ready

- [ ] M0-LNX-001..013 and systemd/XDG/atime handoff results are reviewed for the exact target environment.
- [ ] Requirements, interpretations, outcome, non-goals, and read-only/no-control/privacy boundaries are approved.
- [ ] Linux paths/imports/shared files and agent ownership are conflict-free.
- [ ] CTR-RUN-006 and CTR-PLAT-001 are synchronized with M06/M02/M03/A01–A03/M08/A04-MAC.
- [ ] CTR-DEP-001 is synchronized before any service mutation increment.
- [ ] Process identity, selection, ancestry, cwd, CPU, memory, state, race, and error semantics are evidence-backed.
- [ ] Root/file/access-grant/atime/symlink/TOCTOU/ephemeral payload rules are synchronized and security-approved.
- [ ] XDG and systemd source/lifecycle/lingering/rollback decisions are frozen.
- [ ] Source/field/privacy/compatibility registers are complete and linked to evidence.
- [ ] Every test has a meaningful expected behavioral Red, exact real dependency, safe owner coordination, and truthful unavailable policy.
- [ ] Canonical fail-closed plan/docs/test/quality/build/deploy/release selectors exist and are real-tested for their claimed boundaries.
- [ ] No required routine is represented only by prose/manual history.
- [ ] Dependency/tool/runtime admission is complete, pinned, locked, and represented in SBOM/notices where applicable.
- [ ] Threat model, no-control proof, diagnostics/logging, incident, and rollback reviews are approved.
- [ ] Documentation/handoff/traceability/risk/shared integration ownership is assigned.
- [ ] Planning registry/catalog and CS synchronization include PLAN-A04-LINUX, and the canonical synchronized planning gate passes the real checkout.
- [ ] No unresolved decision permits materially different, unsafe, or incompatible implementations.
- [ ] Owner/root/integration/security/test/operations/platform/deployment and all contract consumers approve this exact plan/version.

Until every applicable item is checked, PLAN-A04-LINUX is not implementation-ready.

## 16. Approval record

| Role | Decision | Conditions | Date |
|---|---|---|---|
| Owner | Pending |  |  |
| Root/integration steward | Pending |  |  |
| M06 runtime owner | Pending |  |  |
| M02/M03/A01–A03 owners | Pending |  |  |
| M08/PLAN-DEP owners | Pending |  |  |
| A04-MAC/platform compatibility reviewer | Pending |  |  |
| Security/privacy reviewer | Pending |  |  |
| Test-integrity reviewer | Pending |  |  |
| Dependency/license reviewer | Pending |  |  |

Implementation does not start while Status remains Draft or any required decision/gate is pending.
