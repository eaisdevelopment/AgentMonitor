# PLAN-DEP: native Linux installation, service lifecycle, upgrade, and rollback

- Status: **Draft — contract synchronization and approval pending; implementation is not authorized**
- Plan ID: `PLAN-DEP`
- Plan version: `0.2.0-draft`
- Proposed contract: `CTR-DEP-001` / `native-service-lifecycle.v1`
- Contract-register baseline: `0.2.0`
- Primary owner: native Linux deployment owner (unassigned)
- Required reviewers: owner, root/integration steward, PLAN-FND, PLAN-DB, M08, A04-LINUX, P01, P02, M01, security/privacy, test-integrity, dependency/license, and release owners
- Primary requirements: FR-OPS-001, FR-IAM-007, NFR-PLAT-001
- Supporting requirements: FR-OPS-002..006, FR-SAFE-001/002, NFR-ARCH-001/002, NFR-API-001/002, NFR-DATA-001, NFR-TEST-001/002, NFR-SEC-001, NFR-PRIV-001/002, NFR-DOC-001, NFR-LIC-001, NFR-PERF-001, NFR-RES-001, NFR-OBS-001, NFR-COMP-001
- Acceptance contribution: AC-V1-002..008, AC-UI-001..005, AC-OPS-001..005, AC-TEST-001..006
- Primary risks: R-005, R-009, R-011, R-012, R-013, R-018, R-019, R-020, R-023
- Dependencies: accepted ADRs 0001, 0002, 0003, 0004, 0007, 0008, 0010, and 0011; approved Foundation build/configuration/lifecycle contracts; approved PLAN-DB, M08, A04-LINUX, P01, P02, and M01 contracts
- Target milestone: M1 native developer installation foundation; exercised and release-gated through M7
- Approved by/date: pending

This plan is governed by the [product requirements](../../../product/requirements.md), [V1 acceptance criteria](../../../product/v1-acceptance-criteria.md), [system architecture](../../../architecture/system-architecture.md), [module boundaries](../../../architecture/modules.md), [contracts and versioning](../../../architecture/contracts-and-versioning.md), [data model](../../../architecture/data-model.md), [deployment architecture](../../../architecture/deployment.md), [security architecture](../../../architecture/security.md), [testing strategy](../../../engineering/testing-strategy.md), [configuration standard](../../../engineering/configuration-standard.md), [dependency and license policy](../../../engineering/dependency-and-license-policy.md), [completion and automation gates](../../../engineering/completion-and-automation-gates.md), [operations runbook](../../../operations/runbook.md), [Foundation plan](../../foundation/plan-v1.md), [SQLite plan](../../persistence/sqlite/plan-v1.md), [M08 operations plan](../../modules/m08-operations/plan-v1.md), [Linux platform plan](../../platform/linux/plan-v1.md), [P01 API plan](../../api/fastapi-boundary/plan-v1.md), [P02 UI plan](../../ui/react-dashboard/plan-v1.md), and [contract register](../../contract-register.md).

All source paths, installed paths, filenames, settings, service properties, artifact formats, and command entry points in this document are proposals for contract synchronization. They are not implemented commands or evidence. This planning task performs no installation, service mutation, dependency download, database operation, `.env` creation, Git action, provider access, or system configuration change.

## CS-1 alignment addendum — contract baseline 0.2.0

This addendum is normative for CS-1 and supersedes conflicting activation,
maintenance, readiness, or ownership wording below. The machine-readable
[contract baseline](../../contract-baseline.toml) and
[parallel ownership manifest](../../parallel-ownership.toml) remain unapproved
and grant no installation/service authority.

- PLAN-DEP is the sole producer of `CTR-DEP-001` and owns native artifact/unit
  materialization and activation, fixed AgentMonitor service execution, and
  fenced service quiescence execution/receipt. It does not own application
  maintenance intent, database activation, restore authority, or application
  readiness.
- M08 owns application maintenance intent/state and backup/restore workflow.
  PLAN-DB owns `CTR-DB-001..003`, including prepared database validation,
  database activation, and database rollback receipts. Artifact/unit activation
  and database activation are separate phases with separate rollback targets.
- Readiness is acyclic: DEP/A04 emit a narrow non-composite fixed-service fact;
  M08 consumes it to compute `CTR-OPS-002`. DEP may consume the completed M08
  readiness result for status or workflow validation, but M08 never consumes a
  DEP composite status that already embeds M08 readiness. Liveness never calls
  readiness recursively.
- The ordered upgrade/restore coordination is M08 intent -> DEP quiescence
  receipt -> DB prepare/activate receipt -> DEP restricted/normal service phase
  -> M08 validation/readiness. DEP cannot infer another phase from exit status,
  PID, artifact link, or database filename.
- DEP consumes `CTR-COMMON-001/002`, `CTR-CONFIG-001`, `CTR-FND-001..008`,
  `CTR-DB-001/003`, `CTR-OPS-001/002/006/007`, `CTR-PLAT-001`, and
  `CTR-BOUNDARY-001/003` only as enumerated by the baseline. Deployment journals
  are not domain events; DEP neither produces nor privately redefines
  `CTR-EVT-001` or `CTR-COMMON-007`.
- Bundle, installed-layout, journal, unit-template, and lifecycle-automation
  lanes may proceed only after exact path allocation and may be parallel only
  when they share no target or artifact. Unit templates, active installation,
  service target, deployment journal, root manifests/locks, migration chain,
  generated artifacts, and release candidate remain single-writer resources.

All install, service, upgrade, rollback, and recovery claims require the real
non-root Linux target and production artifacts. No fake service manager, mocked
filesystem, in-memory database, seeded state, placeholder bundle, or
unexecuted/skipped result can pass T5/T7; Blocked and Not Run remain non-Passed.

## 2026-10-16 owner-approved bounded V1-M5 D01 exception

This addendum is the sole exception to PLAN-DEP/D01's Draft implementation
prohibition and exclusive native unit-lifecycle ownership. The active owner's
objective, **fully implement M5 with our SDLC and runbook**, authorizes PLAN-INT
to implement and execute only `AUTO-M5-SERVICE-ACTIVATE` under the approved
[V1-M5 Codex slice plan 1.4.0](../../integration/m5-codex-slice-change.md).
That focused plan is the detailed authority and test specification. This
cross-reference resolves the ownership conflict before production code.

The exception permits root-owned M5 automation and its tests to inspect,
privately journal, atomically retarget, start, verify, and automatically restore
the already installed fixed `agentmonitor-dashboard.service` on the owner's
current Linux workstation. It is limited to a detached, clean, committed M5
worktree and the pinned trusted rollback runtime
`77a3bad12a096a81587b94b8981ceee812b6445b`. It preserves the existing data,
configuration, database, network, provider-tool and hardening selections; only
the candidate working directory, `PYTHONPATH`, backend Python path, and
30-to-45-second stop-timeout correction may differ. Rollback restores the exact
trusted unit, including its 30-second timeout, and proves the trusted service
healthy.

Plan 1.4.0 also permits one exact corrective rollover after the completed
`6bfa69dc13cc9e1ded9c6baa6e803cb99bc8c20b` activation exposed downstream
completion-control gaps. Under the same exclusive transition guard, the
command may validate that exact candidate and its completed journal, rollback
unit, receipt, clean checkout, live service/browser revision, Registry,
database and pinned runtime; restore and prove the pinned trusted service;
then preserve the whole transition directory by Linux same-filesystem atomic
no-replace rename into an owner-only revision-and-receipt-bound archive. It
creates a fresh owner-only transition root and requires the canonical command
to be rerun with the refreshed trusted PID for the corrected detached
candidate. Retry validates a completed archive before proceeding. No other
prior revision, evidence deletion, artifact replacement, general upgrade or
deployment behavior is authorized.

The final candidate worktree must have no symbolic branch reference. Activation
and every subsequent M5 archive, owner-outcome, alert-witness, quota-witness and
exit boundary revalidate its resolved root, detached state, clean tracked and
untracked status, unchanged 40-hex `HEAD`, selected process identity, and
matching Operations source revision before consuming or creating evidence. A
change blocks; it never becomes an implicit new deployment revision.

This exception does not approve or implement a release bundle, install, repair,
upgrade, uninstall, generic rollback, arbitrary unit/PID action, installed
layout, database activation, cleanup, or `AUTO-DEPLOY`. It grants PLAN-INT no
write ownership under `packaging/linux-native/**` or
`tooling/automation/deployment/**`, transfers no D01 contract ownership, and
expires with this exact M5 transition/evidence scope. Every broader section,
unchecked Definition of Ready item, pending approval row, scenario status, and
the overall PLAN-DEP `0.2.0-draft` status remains unchanged.

Contract impact is none. `CTR-DEP-001` remains a proposed PLAN-DEP/D01 contract
with unchanged version, producer, consumers and meaning; the M5 routine neither
publishes nor claims a `native-service-lifecycle.v1` receipt. No public API,
database, event, configuration, provider, UI, generated-client, dependency,
license, migration, or ADR change follows from this internal exception. The
private M5 transition journal is neither a domain event nor a public deployment
artifact. Passing the M5 activation routine is only prerequisite evidence and
does not pass a D01 scenario, `AUTO-DEPLOY`, PLAN-DEP approval, or release
readiness.

## 0. Authority, evidence state, and planning constraints

The current authority is planning only. Every `DEP-*` scenario is `Not Run`. There is no release bundle, installer, deployment journal, user unit, installed database, canonical deployment command, or deployment evidence. The current checkout may not be a Git repository; that is a visible `Blocked` state for Git preflight, not permission to initialize or publish it.

This plan deliberately separates four claims:

1. `AUTO-BUILD` proves a versioned release bundle can be reproduced from approved locked inputs.
2. `AUTO-DEPLOY` proves that exact bundle can be installed, upgraded, rolled back, or uninstalled through approved native paths.
3. CTR-DEP-001 proves typed lifecycle behavior and receipts for other modules.
4. T5/T7 evidence proves the behavior on the real target Linux workstation.

None substitutes for another. A unit file existing is not a running service. A running PID is not readiness. A successful build is not an install. A successful migration is not an upgrade until service, API, UI, and recovery checks pass. A hosted pipeline cannot pass target-workstation service or login-autostart scenarios.

The planning completion command remains:

```bash
python3 tools/planning/validate_plans.py --stage synchronized
```

It validates documentation only. It neither approves this plan nor exercises deployment.

## 1. Outcome and boundaries

### 1.1 Outcome

PLAN-DEP delivers one non-root, native Linux installation that runs AgentMonitor as a fixed user-level service, starts at that user's login, continues collection while the browser is closed, serves the version-matched frontend and API on loopback only, and preserves owner data through install, upgrade, rollback, reinstall, and default uninstall.

The outcome is measurable when:

1. A release bundle contains exactly the approved backend, built frontend, OpenAPI/client identities, migrations, metadata, SBOM, notices, and digests; it contains no secrets, operator data, provider profiles, or live evidence.
2. Install resolves one explicit normal-user XDG layout, rejects root/broad/unsafe targets, creates only AgentMonitor-owned paths, and never scans or mutates provider-owned paths.
3. `.env` is a protected owner-managed file at the approved configuration path. Installation may create an empty documented shell only at an explicit owner checkpoint; upgrade never reads, prints, rewrites, copies, hashes for disclosure, or replaces its values.
4. The systemd user unit can address only the fixed AgentMonitor service and exact installed artifact; no arbitrary unit, command, path, or monitored agent PID can enter a lifecycle request.
5. Start, stop, restart, status, enable-at-login, disable, and browser-independent operation are verified against the real user manager and real application readiness.
6. Lingering is detected and reported but never enabled or disabled by AgentMonitor. The default service lifetime follows the owner's login session.
7. Local mode binds exactly to approved loopback, enforces a coherent canonical Origin and trusted Host set, and refuses wildcard, LAN, proxy-trust, or remote exposure.
8. Upgrade performs fail-closed preflight, a fresh verified backup when required, quiescence, explicit migration, versioned artifact installation, atomic activation, restricted validation, normal readiness, and post-upgrade checks.
9. Failed installation or upgrade preserves the previous artifact and database, records a sanitized deployment journal, and executes only a tested safe rollback path. It never improvises a database downgrade.
10. Default uninstall stops/disables only AgentMonitor and removes only manifest-owned application artifacts while preserving `.env`, database, backups, exports, provider profiles, and operational history. V1 has no automated purge-data action.
11. Every routine is represented by one repository-owned, non-interactive, fail-closed canonical command with real tests. Owner checkpoints remain only for administrator bootstrap, destructive recovery, credentials, or explicit lifecycle windows.
12. Linux results are not generalized to macOS. Portable artifacts and contracts retain a macOS seam, but macOS deployment remains a separately planned and real-verified boundary.

### 1.2 In scope

- Linux release-bundle assembly and validation on top of Foundation's reproducible backend/frontend build.
- Exact repository ownership for native packaging templates, deployment automation, tests, and documentation.
- XDG configuration, data, state, cache, runtime, release, launcher, and user-unit paths.
- File/directory ownership, mode, type, symlink, atomicity, filesystem, free-space, and same-device preflight.
- Protected `.env` shell creation and preservation policy without secret-value handling.
- Versioned immutable releases plus an atomically switched `current` reference.
- Fixed AgentMonitor `systemd --user` unit rendering, installation, enablement, status, start, stop, restart, crash recovery, graceful shutdown, and removal.
- Explicit lingering inspection and owner decision record; no lingering mutation.
- Local loopback bind/origin/trusted-host coherence and service-start refusal on remote configuration.
- Backend runtime artifact, built static frontend, migration catalog, OpenAPI/client/build metadata, SBOM, notices, and license inventory deployment.
- Installation, repair of AgentMonitor-owned artifacts, upgrade, rollback, and non-purging uninstall workflows.
- Coordination with M01 bootstrap/re-login, PLAN-DB migration/activation, M08 backup/restore/readiness, P01 transport, P02 static assets, and A04 Linux platform primitives.
- Deployment journal, receipts, health/status integration, sanitized logs, operator runbooks, and canonical automation.
- Real T5/T7 Linux service, filesystem, install, upgrade, rollback, recovery, and login-autostart test design.

### 1.3 Out of scope

- Production implementation or system mutation under this Draft.
- Root/system-wide installation, `/etc`, `/opt`, `/usr`, system services, sudo, polkit policy, setuid helpers, Linux capabilities, package-manager repositories, or OS package publication.
- Docker/container deployment or treating a container user manager as the target workstation.
- Remote bind, TLS termination, reverse proxy, LAN access, multi-user authorization, or public hosting. `0.0.0.0` and `::` are always invalid in V1.
- macOS `launchd` implementation. Portable core remains required, but real macOS deployment needs a separate plan and evidence.
- Provider installation, login/logout, authentication, credential copying, default-profile modification, provider-profile migration, or provider service control.
- Killing, restarting, signaling, injecting into, rerouting, or switching credentials inside Claude, Codex, Ollama, or any monitored agent process.
- Database schema ownership, migration meaning, backup validity, restore policy, readiness policy, API security semantics, or UI feature behavior. Their owning plans publish those contracts.
- Automatic self-update, background download, update server, release publication, GitLab release creation, or telemetry.
- Automated deletion of owner data, `.env`, database, backups, exports, provider profiles, evidence, or logs. A future purge workflow requires a separate destructive change plan.
- Secret generation, password collection, MFA/OTP handling, or provider credential storage by deployment automation.

### 1.4 Ownership

PLAN-DEP exclusively owns:

- deployment policy and orchestration for install, upgrade, repair, rollback, uninstall, and installed-service lifecycle;
- release bundle envelope and native installation manifest semantics after Foundation supplies built inputs;
- installed layout policy and mapping from XDG roots to AgentMonitor-owned object references;
- fixed service name, unit template semantics, artifact activation protocol, and deployment journal;
- local deployment profile coherence across bind address, port, canonical Origin, and trusted Hosts, while P01 owns request validation;
- CTR-DEP-001 schema meanings and compatibility after synchronization;
- deployment-owned configuration descriptors and documentation;
- deployment selectors and behavior for `AUTO-BUILD`, `AUTO-DEPLOY`, and `AUTO-GIT-PREFLIGHT` in cooperation with their Foundation/integration owners;
- native Linux deployment tests and evidence packet.

PLAN-DEP owns no business table, Alembic revision body, provider profile, application secret, browser session, HTTP route, frontend feature, domain readiness meaning, or platform subprocess implementation.

### 1.5 Exact proposed repository paths and file ownership

PLAN-DEP-owned source paths after plan and contract approval:

```text
packaging/linux-native/
  README.md
  bundle-layout-v1.toml
  agentmonitor.service.in
  launcher.in
  deployment-profile-v1.toml
tooling/automation/deployment/
  __init__.py
  cli.py
  models.py
  bundle.py
  preflight.py
  layout.py
  manifest.py
  journal.py
  install.py
  upgrade.py
  rollback.py
  uninstall.py
  status.py
  evidence.py
backend/tests/deployment/linux_native/
  test_bundle_live.py
  test_layout_live.py
  test_install_live.py
  test_service_live.py
  test_upgrade_live.py
  test_rollback_live.py
  test_uninstall_live.py
  test_security_live.py
  test_automation_live.py
docs/modules/deployment-linux-native.md
docs/operations/install-linux.md
docs/operations/upgrade-linux.md
docs/operations/uninstall-linux.md
docs/operations/deployment-recovery-linux.md
docs/contracts/native-service-lifecycle-v1.md
```

Shared paths require one centrally allocated edit owner per change:

```text
tooling/automation/run.py                         # Foundation/integration automation steward
tooling/automation/git/**                        # Foundation/release steward
tooling/automation/build/**                      # Foundation/build steward
backend/src/agentmonitor/contracts/deployment_v1.py
backend/src/agentmonitor/composition/**
backend/pyproject.toml and Python lockfile
frontend/package.json and Node lockfile
contracts/openapi/agentmonitor-v1.json
frontend/src/generated/api/**
backend/migrations/**
.gitlab-ci.yml
configuration registry
command registry, traceability, risk, release, and evidence indexes
```

Generated native release bundles are written only beneath an explicitly selected build-output root and are never hand-edited. Installed files are outside the repository. Evidence containing workstation metadata remains outside Git.

### 1.6 Exact proposed installed Linux layout

All paths are resolved for the target normal user through approved XDG semantics. Defaults apply only when the corresponding XDG variable is absent and the resolved home is safe. Relative, empty-when-required, wrong-owner, symlink-escaped, special-file, or broad target roots fail closed.

| Class | Installed object | Proposed mode | Owner/meaning |
|---|---|---:|---|
| Config root | `${XDG_CONFIG_HOME:-$HOME/.config}/agentmonitor/` | `0700` | DEP creates/validates root |
| Secret config | `.../agentmonitor/.env` | `0600` | Owner-managed AgentMonitor secrets; never replaced on upgrade |
| Non-secret deployment record | `.../agentmonitor/deployment.toml` | `0600` | DEP-owned selected profile, artifact/version/object refs; no values from `.env` |
| User unit | `${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/agentmonitor.service` | `0600` | DEP template rendered for one fixed service |
| Data root | `${XDG_DATA_HOME:-$HOME/.local/share}/agentmonitor/` | `0700` | DEP creates/validates root |
| Release store | `.../agentmonitor/releases/<release-id>/` | directories `0700`, files `0600` or executable `0700` | immutable artifact generation |
| Active release | `.../agentmonitor/current` | atomic DEP-owned symlink/reference | points only to a validated release under release store |
| Database root | `.../agentmonitor/database/` | `0700` | PLAN-DB/M08 data; DEP owns path provisioning only |
| Database | `.../agentmonitor/database/agentmonitor.db` | `0600` | PLAN-DB-owned object |
| Backup root | `.../agentmonitor/backups/` | `0700` | M08-owned objects; DEP provisions root |
| Artifact root | `.../agentmonitor/artifacts/` | `0700` | M08 exports/diagnostics; DEP provisions root |
| Managed-profile root | `.../agentmonitor/provider-profiles/` | `0700` | M02/provider adapters; DEP may provision empty root only after their approval |
| State root | `${XDG_STATE_HOME:-$HOME/.local/state}/agentmonitor/` | `0700` | DEP/M08 operational state |
| Deployment journal | `.../agentmonitor/deployment/journal-v1.json` | `0600` | DEP crash/recovery journal; safe IDs/states only |
| Log root | `.../agentmonitor/logs/` | `0700` | M08/Foundation local structured logs |
| Restore state | `.../agentmonitor/restore/` | `0700` | M08 external restore journal, not DEP-owned content |
| Cache root | `${XDG_CACHE_HOME:-$HOME/.cache}/agentmonitor/` | `0700` | Re-creatable AgentMonitor-only cache |
| Runtime root | `${XDG_RUNTIME_DIR}/agentmonitor/` | `0700` | ephemeral locks/readiness/control receipts; must be current-user-owned local runtime fs |
| Launcher | `$HOME/.local/bin/agentmonitor` | `0700` | optional fixed launcher to active release; exact path must be approved |

The application release is separate from mutable configuration and data. `AUTO-DEPLOY` never places code in the database/configuration roots or mutable data in a release directory. Every created object has a manifest owner and lifecycle. Unknown files are neither adopted nor deleted.

### 1.7 Allowed and forbidden dependencies/imports

Deployment orchestration may consume only approved:

- Python standard-library filesystem, JSON/TOML-reading, hashing, archive, subprocess, and argument-parsing facilities through reviewed safe wrappers;
- CTR-FND build/configuration/lifecycle/log/evidence contracts;
- CTR-PLAT-001 fixed AgentMonitor filesystem and service primitives;
- CTR-DB-001/003 compatibility, migration, snapshot, activation, and rollback receipts;
- CTR-OPS-001/002/003/006 health, readiness, backup, and maintenance receipts;
- M01 initialization and post-restore/upgrade authentication checks through typed ports;
- P01 deployment profile validation and P02 build/client compatibility metadata.

Deployment code must not import module internals, ORM models, FastAPI route functions, React sources, provider adapters, provider SDKs/CLIs, `psutil`, or arbitrary system-service libraries. It cannot execute raw SQL, parse `.env` values, inspect provider files, or query application tables.

Forbidden mechanisms include shell strings, `shell=True`, unresolved globs/variables, recursive deletion of broad roots, arbitrary unit names, arbitrary executable arguments, global environment inheritance, runtime dependency downloads, privileged escalation, implicit migration, implicit lingering mutation, remote bind, and hand-edited generated artifacts.

### 1.8 Parallel-development isolation

- Foundation owns manifests/locks/build primitives and the common automation dispatcher. DEP supplies a deployment plugin/selector after their contracts freeze.
- PLAN-DB owns migration and physical database operations. DEP only sequences typed receipts.
- M08 owns backup/restore/readiness. DEP only requests quiescence/start phases and verifies receipts.
- A04-LINUX owns actual fixed-unit/filesystem/systemd operations. DEP owns policy and never invokes `systemctl` directly from domain/orchestration code.
- P01 owns Host/Origin/request validation and P02 owns static bundle contents. DEP owns coherent installed configuration and atomic artifact pairing.
- Only one agent edits the unit template, deployment journal schema, active-release protocol, or common automation dispatcher during a wave.
- An unresolved shared contract stops the relevant increment; no local duplicate interface is created.

## 2. Requirements and traceability

| Requirement/AC | Planned deployment behavior | Contract | Scenario IDs | Evidence gate |
|---|---|---|---|---|
| FR-OPS-001 | Native normal-user install, user service, login autostart, browser-independent collection | CTR-DEP-001/CTR-PLAT-001 | DEP-INSTALL-001..008, DEP-SVC-001..014 | Real target Linux T5/T7 |
| FR-OPS-002 | Lifecycle status uses application readiness and component health, not PID alone | CTR-DEP-001/CTR-OPS-001/002/006 | DEP-SVC-004/005, DEP-HEALTH-001..006 | Real service/application/database |
| FR-OPS-003/004 | Upgrade requires verified backup; rollback/restore preserve current and validate startup | CTR-DEP-001/CTR-OPS-003/CTR-DB-003 | DEP-UPG-001..012, DEP-REC-001..010 | Real SQLite/service/filesystem recovery |
| FR-OPS-005 | `.env`, credentials, profiles, content, and secrets excluded from bundles/logs/evidence | bundle.v1/CTR-DEP-001 | DEP-BUILD-005..008, DEP-SEC-001..010 | Real artifact/install/log scans |
| FR-OPS-006 | Installed app/backend/frontend/OpenAPI/client/schema/unit/build versions are authoritative | bundle.v1/CTR-FND-007 | DEP-BUILD-002..004, DEP-HEALTH-002/003 | Real bundle and running service |
| FR-IAM-007 | Loopback-only profile with coherent Host/Origin/port and no proxy trust | CTR-DEP-001/CTR-API-002 | DEP-NET-001..008 | Real socket/browser/request checks |
| FR-SAFE-001 | Local lifecycle/backup/migration actions exist only as authorized operator routines | CTR-DEP-001 | DEP-AUTO-001..008, DEP-SEC-008 | Contract/command/authority review |
| FR-SAFE-002 | Lifecycle targets AgentMonitor only and exposes no monitored-agent control | CTR-DEP-001 | DEP-SVC-008/009, DEP-SEC-006..010 | Real process/unit no-control proof |
| NFR-ARCH-001/002 | Deployment is an adapter/orchestrator consuming versioned ports only | CTR-DEP-001 | DEP-ARCH-001..004 | Import/ownership/contract gate |
| NFR-API-001/002 | One same-origin `/api/v1` plus version-matched static UI/generated client | CTR-API-001/CTR-UI-001 | DEP-NET-005..008, DEP-BUILD-003/004 | Real HTTP/built browser |
| NFR-DATA-001 | Mutable SQLite is outside release; migrations explicit; rollback coordinated | CTR-DB-001/003 | DEP-UPG-003..012, DEP-REC-004..008 | Real DB/service upgrade |
| NFR-TEST-001/002 | R/G/R and real Linux/filesystem/service/build boundaries; no doubles | evidence.v1 | all DEP scenarios | Canonical reports and prohibited-pattern scan |
| NFR-SEC-001 | Non-root, owner-only, safe paths/argv/service/unit/bind/supply chain | CTR-PLAT-001/CTR-DEP-001 | DEP-FS-001..014, DEP-SEC-001..010 | Real Linux/security review |
| NFR-PRIV-001/002 | Operational metadata only; no analytics/upload/content in release or runtime | bundle.v1 | DEP-BUILD-005/006, DEP-SEC-001..005 | Artifact/network/log inspection |
| NFR-DOC-001 | Install/upgrade/status/recovery/uninstall commands and contracts are maintained | documentation outputs | DEP-DOC-001..004 | AUTO-DOCS-CHECK plus runbook exercises |
| NFR-LIC-001 | Runtime/build/install graph, wheelhouse, frontend licenses, SBOM/notices reviewed | bundle.v1 | DEP-BUILD-006..008, DEP-DEP-001..004 | Locked graph and bundle inventory |
| NFR-PLAT-001 | Linux fully verified; portable build/contract does not claim macOS | CTR-DEP-001 | DEP-PLAT-001..004 | Real Linux; macOS separate/Blocked |
| NFR-PERF-001 | Install/upgrade/service resource use and startup stay within measured budgets | CTR-DEP-001 | DEP-PERF-001..005 | Real target measurements |
| NFR-RES-001 | Interrupted build/deploy, crash loop, migration/readiness failure recover safely | CTR-DEP-001 | DEP-SVC-010..014, DEP-REC-001..010 | Real isolated failures |
| NFR-OBS-001 | Bounded structured lifecycle events, receipts, and safe deployment journal | CTR-FND-004/CTR-DEP-001 | DEP-HEALTH-004..006, DEP-SEC-003 | Real logs/journal scan |
| NFR-COMP-001 | Bundle/service/config/database/API/UI contracts carry explicit compatibility | CTR-DEP-001/bundle.v1 | DEP-BUILD-001..004, DEP-UPG-008..012 | Compatibility and rollback gate |
| AC-OPS-001 | Install/start/stop/restart/status/autostart verified on target | CTR-DEP-001 | DEP-INSTALL-001..008, DEP-SVC-001..009 | Real target owner session |
| AC-OPS-002 | Browser closure leaves service and collection active | CTR-DEP-001 | DEP-SVC-007 | Real installed service and browser |
| AC-OPS-003 | Platform/provider failure does not stop API/UI/other adapters | readiness integration | DEP-HEALTH-005/006 | Real naturally failing component |
| AC-OPS-004 | Backup/integrity/restore/post-restore start exercised | CTR-OPS-003/CTR-DB-003 | DEP-REC-004..010 | Owner-approved T7 recovery |
| AC-OPS-005 | Upgrade and failure-recovery runbooks exercised | CTR-DEP-001 | DEP-UPG-001..012, DEP-REC-001..010 | Real upgrade/rollback rehearsal |
| AC-TEST-001..006 | Meaningful R/G/R, no doubles, real stack/platform, visible statuses | evidence.v1 | DEP-AUTO-001..010, DEP-TEST-001..004 | Canonical automation and review |

This plan supports but cannot alone pass API, UI, database, backup, restore, or provider acceptance. The owning module's evidence remains required.

## 3. Domain design

### 3.1 Deployment aggregates and value objects

`DeploymentTargetV1` identifies one normal-user installation using an opaque target ID and typed XDG root references. It never contains a username or raw path outside the platform adapter.

`ReleaseBundleManifestV1` identifies:

- product/application/backend/frontend/OpenAPI/client versions;
- build ID and source revision state (`clean_release | declared_local_change`);
- supported Python ABI/runtime and Linux architecture/platform constraints;
- schema readable/writable range and target migration head/catalog digest;
- configuration, CTR-DEP, CTR-FND, CTR-DB, CTR-OPS, CTR-API, and CTR-UI contract versions;
- exact member relative paths, type, size, executable flag, and SHA-256 digest;
- dependency lock identities, SBOM identity, notices identity, and build-tool versions;
- unit-template and launcher-template identity;
- no host path, user identity, timestamp that breaks the approved reproducibility policy, secret, or live-data field.

`InstalledReleaseV1` records manifest identity, immutable release-object reference, activation state, installed/activated times, previous release ID, compatibility, and safe health state.

`DeploymentOperationV1` records operation ID/type, target/release IDs, phase, fixed plan, preflight/backup/migration/quiescence/activation/readiness/rollback receipts, fencing generation, timestamps, safe error code, and recovery action. It contains no `.env` value, path, command output, provider identity, or free-form error.

### 3.2 Lifecycle state machines

Release state:

```text
candidate -> validated -> staged -> installed -> active -> previous -> retired
                         \-> rejected
active -> rollback_candidate -> active | quarantined
```

Deployment operation state:

```text
requested -> preflighting -> prepared -> quiescing -> migrating
          -> installing -> activating -> validating -> completed
any nonterminal -> failed_safe | rollback_required -> rolling_back
rolling_back -> rolled_back | recovery_required
```

Service state is a typed combination, not a single PID flag:

```text
unit: absent | disabled | enabled | activating | active | deactivating | failed | unknown
application: starting | setup_required | ready | degraded | maintenance | stopping | unavailable | incompatible
```

`active + unavailable` is not ready. `enabled` is not proof that next-login autostart works. `degraded` may still be normal-ready only according to M08's required-component manifest.

### 3.3 Release-bundle structure

The proposed uncompressed build-output directory avoids privileged packaging and archive-extraction ambiguity:

```text
dist/linux-native/<release-id>/
  manifest-v1.json
  manifest-v1.sha256
  backend/
    agentmonitor-<version>-py3-none-any.whl
    wheelhouse/                         # exact locked runtime wheels only
    runtime-lock.*                      # selected Foundation lock export
  frontend/
    static/                             # production Vite output, immutable names
    asset-manifest-v1.json
  contracts/
    agentmonitor-v1.json
    generated-client-metadata-v1.json
  migrations/
    catalog.toml
    revision-manifest-v1.json
  native/
    agentmonitor.service
    agentmonitor-launcher
    deployment-profile-v1.toml
  metadata/
    build-metadata-v1.json
    sbom.spdx.json
    third-party-notices.txt
    licenses/                            # approved direct/transitive license material
```

The exact wheel/lock/artifact format depends on Foundation dependency admission. `AUTO-BUILD` must be offline after its explicit dependency-acquisition phase and must never load the operator `.env`, database, logs, provider roots, account data, or home-directory content into build context.

No member may be a symlink, hard link, device, FIFO, socket, absolute path, traversal path, duplicate normalized path, or unmanifested file. Installed symlinks are created only by DEP for the fixed `current` and optional launcher references after target validation.

### 3.4 Install workflow

1. Resolve the exact normal-user target and XDG roots through CTR-PLAT-001; reject UID 0, owner mismatch, unsafe filesystem types as decided, relative roots, and broad targets.
2. Validate bundle manifest/schema/digests/member inventory, runtime/platform compatibility, licenses/SBOM/notices presence, and clean-release policy.
3. Validate required Python runtime and systemd user manager. Node.js is not required at runtime because frontend assets are prebuilt.
4. Validate free space for staged release, database initialization, backup reserve, and rollback copy/reference.
5. Acquire one deployment lock and create/fsync the external deployment journal before writes.
6. Create only the approved XDG roots with exact owner-only modes; reject unexpected existing object types or owners.
7. At a named owner checkpoint, create `.env` only if absent, as an empty/comment-only shell with mode `0600`. Never replace an existing file.
8. Materialize the release into a unique staging directory, validate every installed member and runtime environment, fsync, and atomically rename to the immutable release ID.
9. Render/install the fixed unit and optional launcher from manifest-approved templates. Unit content contains paths only, never secret values.
10. Initialize/migrate the exact database through `AUTO-MIGRATE`; normal application startup performs no DDL.
11. Atomically activate `current`, reload the user manager, and enable the fixed service for login without changing lingering.
12. Start restricted/setup mode, complete M01 administrator bootstrap at an owner-controlled no-log checkpoint when required, then start/verify normal readiness and real login.
13. Verify version alignment, static UI/deep link, API authentication, scheduler independence from browser, and backup path readiness.
14. Mark the journal completed only after every mandatory check passes; retain sanitized receipt and previous release if one exists.

Install is idempotent for the same manifest and target. A different manifest under the same release ID is a conflict. An existing unknown installation is never adopted automatically.

### 3.5 Service unit policy

The fixed unit name is proposed as `agentmonitor.service`. The template may contain only manifest/configuration-derived AgentMonitor-owned paths and approved constant service settings.

Required semantics:

- user-level manager only; no system unit and no root;
- one explicit `ExecStart` pointing through the validated active-release launcher to the production application entry point;
- explicit `.env` path argument to Foundation's typed loader; the unit does not embed values and does not dump the environment;
- explicit working/state/data/runtime roots;
- `UMask=0077` and owner-only created files;
- `Restart=on-failure` with measured bounded delay/start-limit policy, not unlimited crash looping;
- bounded `TimeoutStartSec`/`TimeoutStopSec` and production graceful-shutdown receipt;
- auto-start through the approved user target at login;
- no `User=`, `Group=`, privilege escalation, ambient capabilities, arbitrary environment inheritance, or provider variables;
- no shell, reload command, provider command, or monitored PID argument;
- stdout/stderr policy limited to already-sanitized startup events; application logs use approved local structured sink;
- hardening directives selected only after real target systemd and provider-read requirements are verified. Unsupported directives cannot silently disappear.

The preferred integration emits a narrow, non-composite fixed-service state
receipt for M08 to consume when computing readiness. DEP may later display the
completed M08 readiness result, but that result never feeds back into the
service-state receipt. If `Type=notify`/systemd notification is selected,
Foundation/A04 must implement it from an approved AgentMonitor-owned
variable/socket without reading arbitrary target-process environments. A plain
`Type=simple` active state never counts as application readiness by itself.

### 3.6 Login autostart and lingering

Install enables only the fixed user unit for the approved login target. Verification requires an actual owner-coordinated logout/login or equivalent real user-manager lifecycle that demonstrates the service starts without a browser or terminal holding it.

Lingering states are `enabled_before_install | disabled_before_install | unavailable | unknown`. DEP records the observed state and never calls an enable/disable-linger operation. Default V1 behavior assumes no lingering and therefore collection follows the login session. If the owner independently enables lingering, AgentMonitor reports the behavior but does not claim or require it. Any future automated lingering change requires a new owner-authorized security/operations plan because it may invoke system policy or privilege boundaries.

### 3.7 Start, stop, restart, and status

- `start` runs config/path/schema/build compatibility preflight before requesting the fixed unit start.
- `stop` prevents new AgentMonitor mutations/jobs, drains/cancels AgentMonitor-owned work within the approved deadline, releases leases/resources, and never signals monitored agents.
- `restart` is stop plus start for AgentMonitor only; it is not exposed as a normal browser/API operation.
- `status` combines fixed-unit state, manager enablement, lingering observation, active artifact identity, deployment journal state, application readiness, database/schema compatibility, frontend/API/client version match, and safe component health.
- lifecycle operations require a typed local deployment authority and idempotency key. Arbitrary unit/action/path input is rejected before I/O.
- failed start retains exact safe reason and bounded unit/application status; it never falls back to a development server or different port.

### 3.8 Local network and same-origin profile

The proposed initial local profile is:

- bind address: exactly `127.0.0.1`;
- canonical browser origin: `http://127.0.0.1:<approved-port>`;
- trusted Host: exactly `127.0.0.1:<approved-port>`;
- proxy trust: disabled;
- wildcard CORS: absent;
- runtime documentation: authenticated according to P01;
- remote forwarding/bind: unsupported.

The exact default port is an approval-blocking synchronization item. A configured nondefault port is accepted only when bind, Origin, Host, service, UI URL, and diagnostics agree atomically. `localhost`, IPv6 loopback, and aliases are not inferred. Adding `::1` later requires explicit dual-bind/canonical-Origin tests and cannot create a wildcard.

Socket binding is owned by the production ASGI process. DEP verifies the resolved bind before start and the actual listening sockets after start. A non-loopback listener, proxy-trust setting, or unexpected listener is a security failure that stops the service.

### 3.9 Upgrade workflow

1. Validate source control/build provenance and the complete new bundle without touching the active install.
2. Resolve current installation, active/previous release, unit, configuration, database, journal, and compatibility.
3. Refuse upgrade if another deploy/restore/migration is active, `.env`/data roots are unsafe, current state is ambiguous, or recovery capacity is insufficient.
4. Ask M08 for a fresh verified `migration_preflight` backup when any schema or policy requires it.
5. Stage and fully validate the immutable new release and candidate unit while the old service remains available.
6. Receive M08 maintenance intent, then quiesce through CTR-DEP-001; prove
   engines/jobs drained through separate DEP/DB/M08 receipts.
7. Run `AUTO-MIGRATE` against the exact target and revision chain. Failure keeps the new release inactive and invokes its approved recovery.
8. Atomically activate the release and unit generation, reload only the user manager, and start restricted validation.
9. Verify schema/module consistency, M08 readiness, M01 login/session policy, API/OpenAPI, generated client, frontend static assets/deep links, scheduler, and safe component health.
10. Start normal mode only after mandatory checks pass. Record previous release as rollback candidate.
11. On validation failure, stop the candidate, restore the prior unit/artifact and, only if schema compatibility requires, use the approved DB downgrade or backup/activation recovery. Never run an old binary against a schema outside its range.
12. Complete the journal and retire no release/backup until the owner-defined stability checkpoint passes.

### 3.10 Atomic activation and rollback

Release materialization uses a unique staging directory under the release store, exact member validation, fsync, and same-filesystem rename. Activation atomically replaces only the DEP-owned `current` reference after the destination release is immutable and verified. Unit replacement uses an AgentMonitor-owned temporary file plus fsync/atomic replace through CTR-PLAT-001 and retains the prior generation.

The deployment journal is fsynced before each irreversible boundary and supports deterministic inspection after interruption. Recovery never guesses whether activation occurred; it validates the actual current reference, unit digest, database compatibility, and service state.

Rollback classes:

- `artifact_only`: prior binary/UI/unit remains compatible with current schema; atomically reactivate it.
- `artifact_and_safe_downgrade`: only when PLAN-DB marks and proves a real downgrade.
- `artifact_and_verified_backup`: activate the verified pre-upgrade database via M08/CTR-DB-003, with owner authority and post-restore credential invalidation.
- `forward_fix_required`: preserve old/current/candidate artifacts and keep normal service stopped or maintenance-only until an approved recovery.

No rollback edits migration history, hand-patches the database, copies a live SQLite file, deletes the failed candidate, or touches provider state.

### 3.11 Repair and uninstall

`repair` is limited to manifest-owned application artifacts, launcher, unit, directory modes, and active-reference coherence. It cannot repair database contents, rewrite `.env`, regenerate secrets, modify provider profiles, or silently migrate. Unknown or modified files cause a conflict requiring review.

Default uninstall is `preserve-data` and must:

1. resolve exact target and acquire the deployment lock;
2. stop and disable only `agentmonitor.service`;
3. verify no AgentMonitor process remains and no provider process was targeted;
4. remove only exact manifest-owned unit, launcher, active reference, and immutable release artifacts through enumerated object references;
5. preserve config root, `.env`, database, backups, artifacts, provider profiles, state/history, and logs;
6. retain a sanitized uninstall receipt and list preserved classes without paths/values;
7. never change lingering;
8. support reinstall against preserved data only after schema/application compatibility preflight.

V1 exposes no `purge`, `delete data`, or recursive cleanup flag. Cache/runtime cleanup may remove only exact DEP-owned ephemeral objects after service stop and identity validation.

### 3.12 Concurrency, idempotency, and recovery

- Exactly one install/upgrade/rollback/uninstall/restore/migration operation may own the target deployment fencing class.
- A deployment idempotency key is bound to operation, target, manifest, current release, and requested action. Replay returns the same receipt; mismatch conflicts.
- Start/stop/status may coalesce only under documented fixed-unit semantics and cannot bypass an active destructive lifecycle phase.
- Interrupted work resumes or rolls back from the journal and actual object identities. It never blindly repeats migration, activation, or deletion.
- Browser/API requests cannot forge local deployment authority. Service actions are local operator/integration operations.
- All times are UTC instants; elapsed durations use monotonic measurement and integer milliseconds.

### 3.13 Failure and degradation behavior

Failures are phase-specific and preserve the prior safe state wherever possible. Bundle invalidity leaves installed state unchanged. Staging failure leaves active service unchanged. Quiescence failure leaves old release active or explicitly maintenance, never mixed. Migration failure follows DB recovery. Activation/readiness failure attempts only the precomputed rollback class. Rollback ambiguity produces `recovery_required` and leaves service stopped or restricted, with both database/artifact generations preserved.

Provider capability degradation after an otherwise valid deployment is an M08 degraded-health result, not automatic artifact rollback, unless the synchronized release policy identifies a binary compatibility regression. One provider failure cannot stop the API/UI or other adapters.

## 4. Public contracts

### 4.1 CTR-DEP-001 contract summary

Proposed `native-service-lifecycle.v1` is a local application/platform contract, not a public HTTP API. It publishes typed commands/queries/receipts for composition, M08, PLAN-DB, A04-LINUX, and canonical automation. P01 exposes no install, upgrade, restart, rollback, uninstall, lingering, or restore-execution route in V1.

Changing target identity, unit identity, path class, bind policy, quiescence proof, activation meaning, rollback class, authority, or idempotency semantics is breaking and requires a new major plus migration/ADR as applicable.

### 4.2 Published DTOs

`DeploymentTargetViewV1`:

- opaque target ID and platform profile/version;
- normal-user/root-rejected state;
- XDG path-class states as opaque refs, never raw paths;
- user-manager and lingering observed state;
- fixed unit ID/version and install/enable state;
- active/previous release IDs and compatibility;
- local network profile state;
- deployment operation/journal state;
- safe error/remediation codes and observation time.

`ServiceLifecycleViewV1`:

- fixed unit state, enablement, manager generation;
- service process identity as safe internal receipt, not a public PID;
- narrow service lifecycle state plus an optional separately sourced M08 readiness projection;
- active build/backend/frontend/API/client/schema versions;
- start/stop times, restart count class, crash-loop state;
- required-component manifest identity and safe blocker codes.

`DeploymentOperationViewV1`:

- operation/target/release IDs, action, phase, state, actor category;
- preflight, backup, migration, quiescence, activation, validation, rollback states;
- requested/started/completed times and durations;
- previous/candidate/active release references;
- required next action and safe error code;
- no path, argv, environment, secret, unit output, or raw log.

`DeploymentReceiptV1` is an immutable versioned result containing operation ID, manifest identity, before/after release and service states, compatibility receipts, evidence status, and safe digest references. It does not contain evidence payload.

### 4.3 Published commands and queries

| Port | Input/output | Authority/preconditions | Outcomes | Side effects/idempotency |
|---|---|---|---|---|
| `InspectDeploymentTargetV1` | target selector + deadline -> target view | local read authority; exact current user | available/partial/unsafe/unsupported | Read-only; never creates paths |
| `ValidateReleaseBundleV1` | approved bundle object ref + target profile -> validation receipt | build/deploy authority; immutable bundle | valid/incompatible/rejected/unavailable | Read-only, bounded |
| `InstallAgentMonitorV1` | target, manifest, operation/idempotency IDs -> operation view | owner checkpoint for first config/bootstrap; absent or compatible install | completed/failed-safe/blocked/recovery-required | One fenced operation; creates only manifest paths |
| `UpgradeAgentMonitorV1` | target, candidate manifest, expected active release, operation ID -> view | compatible current install, backup/recovery/quiescence available | completed/rolled-back/recovery-required | One fenced operation; resumable journal |
| `RepairAgentMonitorInstallationV1` | target, expected manifest, operation ID -> view | no unknown ownership/data changes | repaired/no-op/conflict/blocked | Manifest-owned artifacts only |
| `RollbackAgentMonitorV1` | operation/release/recovery plan IDs -> view | precomputed compatible rollback; owner checkpoint if DB restore | rolled-back/recovery-required/blocked | No improvised downgrade |
| `UninstallAgentMonitorV1` | target, preserve-data policy, operation ID -> view | explicit owner authority; exact installed inventory | completed/partial/blocked | No purge-data operation in V1 |
| `StartAgentMonitorServiceV1` | fixed target + expected release -> service view | safe config/schema/current artifact | started/already-running/blocked/failed | AgentMonitor unit only; idempotent |
| `StopAgentMonitorServiceV1` | fixed target + drain policy -> service view | local lifecycle authority | stopped/already-stopped/drain-timeout/failed | AgentMonitor-owned tasks only |
| `RestartAgentMonitorServiceV1` | fixed target + expected release -> service view | stop/start preconditions | restarted/blocked/failed | No provider process control |
| `EnableAgentMonitorAtLoginV1` | fixed target -> target view | valid installed unit/user manager | enabled/already-enabled/unsupported/failed | Does not mutate lingering |
| `DisableAgentMonitorAtLoginV1` | fixed target -> target view | exact fixed unit | disabled/already-disabled/failed | Does not stop unless separately requested |
| `GetAgentMonitorServiceStatusV1` | fixed target + deadline -> service view | local read authority | complete/partial/unavailable | Read-only; uses readiness, not PID only |
| `QuiesceAgentMonitorServiceV1` | M08 intent receipt + operation/kind/expected state -> receipt | M08 owns maintenance intent; DEP owns fixed-service fence | quiesced/conflict/blocked | Fenced; stops new AgentMonitor work but creates no maintenance intent |
| `ResumeAgentMonitorServiceV1` | operation + DB/M08 validation receipts -> narrow service view | M08 workflow authorizes phase; required receipts present | running/restricted/blocked | Cannot compute or force application readiness |
| `GetRequiredComponentManifestV1` | release ID -> typed manifest | approved active/candidate release | available/incompatible | Read-only |

### 4.4 Consumed contracts

| Owner/contract | Required status | Deployment use | Failure/degradation |
|---|---|---|---|
| CTR-FND-001 | `proposed_aligned` 1.0.0 | exact repository/build/path ownership | conflict blocks build/deploy |
| CTR-FND-002 | `proposed_aligned` 1.0.0 | production entrypoint, lifecycle, restricted/normal modes | incompatible factory blocks install |
| CTR-FND-003 / CTR-CONFIG-001 | `proposed_aligned` 1.0.0 | typed explicit `.env` path, key registry, safe validation | missing/invalid security setting blocks start; no value readout |
| CTR-FND-004 | `proposed_aligned` 1.0.0 | safe structured lifecycle logs/correlation | incompatible logging blocks readiness |
| CTR-FND-005 | `proposed_aligned` 1.0.0 | OpenAPI/generated-client build identities | mismatch blocks activation |
| CTR-FND-006 | `proposed_aligned` 1.0.0 | migration catalog/backup/recovery metadata | missing metadata blocks upgrade |
| CTR-FND-007 | `proposed_aligned` 1.0.0 | build/application/frontend/API/client versions | missing/mismatched metadata blocks release |
| CTR-FND-008 | `proposed_aligned` 1.0.0 | evidence status model | Blocked/Not Run never collapses to Passed |
| CTR-IAM-004 | `proposed_aligned` 1.0.0 | first-install bootstrap and owner re-login validation | absent bootstrap authority leaves setup-required; no default password |
| CTR-IAM-008 | `proposed_aligned` 1.0.0 | post-restore invalidation/health | failure blocks normal readiness |
| CTR-DB-001 | `proposed_aligned` 1.0.0 | schema compatibility and startup refusal | older/newer/unknown schema blocks normal start |
| CTR-DB-003 | `proposed_aligned` 1.0.0 | migration target, activation, rollback receipts | unavailable blocks upgrade/restore recovery |
| CTR-OPS-001/002/006/007 | `proposed_aligned` 1.0.0 | consume health/readiness; publish DEP leaf health and lifecycle participant receipts | incomplete required state blocks normal ready; DEP does not aggregate readiness |
| CTR-OPS-003 | `proposed_aligned` 1.0.0 | fresh backup and restore receipt | invalid/unavailable backup blocks risky upgrade |
| CTR-PLAT-001 | `evidence_blocked` 1.0.0 | XDG, exact objects, permissions, fsync/atomicity, fixed service operations | unsafe/unavailable capability blocks affected operation |
| CTR-API-001/002/003 | `proposed_aligned` 1.0.0 | loopback transport, auth docs, smoke checks | mismatch/security failure blocks activation |
| CTR-UI-001 | `proposed_aligned` 1.0.0 | generated-client/static artifact identity | mismatch blocks UI activation |

There is no fallback to direct database access, `systemctl`, shell, file copy, provider inspection, route invocation, or UI internals when a port is absent.

### 4.5 Safe error vocabulary

Stable proposed codes include:

- target/path: `deployment_root_user_rejected`, `deployment_target_unsafe`, `deployment_xdg_invalid`, `deployment_path_owner_mismatch`, `deployment_path_mode_mismatch`, `deployment_path_type_rejected`, `deployment_path_escape`, `deployment_filesystem_unsupported`;
- artifact: `deployment_bundle_missing`, `deployment_bundle_manifest_invalid`, `deployment_bundle_member_unexpected`, `deployment_bundle_digest_mismatch`, `deployment_bundle_incompatible`, `deployment_build_provenance_invalid`, `deployment_license_inventory_missing`;
- config/network: `deployment_configuration_missing`, `deployment_configuration_invalid`, `deployment_env_permissions_invalid`, `deployment_remote_bind_rejected`, `deployment_origin_host_mismatch`, `deployment_port_unavailable`;
- service: `deployment_user_manager_unavailable`, `deployment_unit_incompatible`, `deployment_unit_action_failed`, `deployment_service_start_timeout`, `deployment_service_stop_timeout`, `deployment_crash_loop`, `deployment_readiness_failed`, `deployment_lingering_observation_unavailable`;
- lifecycle: `deployment_operation_conflict`, `deployment_lock_unavailable`, `deployment_journal_incompatible`, `deployment_preflight_failed`, `deployment_quiescence_failed`, `deployment_backup_required`, `deployment_migration_failed`, `deployment_activation_failed`, `deployment_validation_failed`, `deployment_rollback_required`, `deployment_rollback_failed`, `deployment_recovery_required`;
- uninstall: `deployment_unknown_owned_object`, `deployment_preserved_data_incompatible`, `deployment_uninstall_partial`, `deployment_purge_unsupported`;
- generic: `deployment_deadline_exceeded`, `deployment_permission_denied`, `deployment_disk_space_insufficient`, `deployment_internal_error`.

Errors expose code, operation/correlation ID, safe phase, version/contract class, status, and remediation category. They never expose raw paths, usernames, home, argv, unit text/output, `.env` details, secrets, database rows, SQL, provider state, exception messages, or journal payload.

### 4.6 Contract-impact assessment

This plan supplies the first detailed CTR-DEP-001 proposal and changes no implemented behavior. Synchronization must:

1. freeze which DTO source package owns CTR-DEP-001 and its consumers;
2. freeze release manifest/member/configuration/build metadata schemas and compatibility;
3. align repository/build artifact paths with Foundation and static asset ownership with P01/P02;
4. align XDG/path/object/fsync/atomic semantics with A04-LINUX and future macOS;
5. align quiescence/restricted-start/normal-start/required-component receipts with M08/PLAN-DB;
6. freeze local network profile and exact configuration ownership with P01/M01;
7. freeze first-install bootstrap and post-restore/upgrade login behavior with M01;
8. freeze unit manager source, fixed unit identifier, notification/readiness, actions, limits, hardening, and rollback with A04-LINUX;
9. freeze deployment operation/journal/idempotency/authority/evidence behavior;
10. allocate common automation dispatcher and shared build/Git files to one steward;
11. approve the already registered, Draft-aligned CTR-DEP-001 details and the
    bundle/config contract specializations; implementation and live evidence
    remain pending;
12. create an ADR if activation, installed layout, notification, launcher, or artifact format changes accepted architecture.

## 5. Data and persistence

### 5.1 Deployment-owned persistent records

PLAN-DEP owns no SQLite business table or migration. Deployment truth that must survive database replacement is stored in two versioned owner-only files beneath approved roots:

1. `deployment.toml`: current target/profile, active/previous release IDs, manifest/unit/config contract versions, installed object inventory reference, and successful operation receipt ID.
2. `deployment/journal-v1.json`: one active/recent lifecycle operation, phase receipts, fencing generation, recovery class, and safe terminal result.

These formats contain no arbitrary map, path value exposed outside DEP, secret-presence detail, `.env` content, database content, provider identity, hostname, username, or raw error. They are written canonically through temp/fsync/atomic replace and versioned for forward-safe reading.

M08 may maintain a product audit reference to deployment operations through a published safe receipt. DEP does not write M08 tables or depend on SQLite availability to recover the external deployment journal.

### 5.2 Installed-object manifest

Every installed code/template/reference object is traceable to one validated release bundle or deployment-created descriptor. The private inventory records opaque object reference, relative role, expected type/mode/owner, manifest digest, installed generation, and lifecycle state.

Mutable owner data is never an installed-object deletion target:

- `.env`, database/WAL/SHM, backups, exports, diagnostics, logs, provider profiles, and real evidence are `preserved_data`;
- deployment record/journal are `deployment_state` and retained across default uninstall;
- release members, fixed unit, launcher, and active reference are `reproducible_artifact`;
- runtime locks/receipts are `ephemeral_exact_object`.

Unknown files under any root are reported and left untouched.

### 5.3 Transaction and filesystem boundaries

- Deployment lock/journal admission commits before any material write.
- Release staging occurs while the old service remains available and outside database transactions.
- Service quiescence and engine drain precede migration or active-artifact switch.
- Database migration/activation occurs only through PLAN-DB/M08 and has separate receipts.
- Artifact and unit activation are recoverable filesystem steps, not falsely described as atomic with database migration.
- The journal is fsynced before migration, release switch, unit switch, database activation, and destructive artifact removal.
- No cross-module call occurs while DEP holds an application database transaction because DEP owns none.

### 5.4 Retention and cleanup

At least the active release and the last verified compatible rollback release remain until a later successful stability checkpoint and recovery review. The exact additional release retention count/age is approval-blocking and cannot cause backup/data deletion.

Failed/staged/quarantined release objects are removed only by exact manifest/object reference after the terminal operation and recovery need are understood. Cleanup never traverses a broad root, follows symlinks, or deletes unknown objects. Default uninstall retains deployment state and all owner data. A future purge must be separately specified, authorized, and recoverable.

### 5.5 Backup and restore coordination

DEP never copies the database. It requests M08/PLAN-DB receipts. Upgrade stores the backup ID and validity state only. Restore execution is owned by M08; DEP supplies stop/quiesce, restricted start, normal start, and fixed-service status. Post-restore readiness is blocked until M01 invalidation, schema/module validation, and authenticated login checks pass.

### 5.6 Portability

CTR-DEP-001 uses target, artifact, service, path-class, and receipt semantics without exposing systemd, symlinks, XDG strings, SQLite filenames, or shell commands. A future macOS deployment can implement corresponding application lifecycle behavior with `launchd` and native paths. Linux-specific unit/template/atomic-reference behavior remains within this adapter plan.

## 6. External and platform boundaries

### 6.1 Linux filesystem boundary

All path work uses CTR-PLAT-001 typed approved-root and exact-object operations. Required capabilities include root resolution, owner/mode/type/symlink checks, same-filesystem assessment, free-space reservation, unique temp creation, bounded streaming copy, digest, fsync file/directory, atomic rename/reference swap, exact-file retirement, advisory deployment lock, and crash-safe journal storage.

The implementation rejects `$HOME`, `~`, `/`, repository root, unresolved variables, globs, path strings supplied by browser/API, cross-device atomicity assumptions, special files, hard-link anomalies where policy rejects them, and different-owner objects. Tests use isolated AgentMonitor-owned targets, never the owner's active install until an explicit live deployment packet.

### 6.2 systemd user-manager boundary

A04-LINUX implements the FND-owned CTR-PLAT-001 fixed-unit primitives that
PLAN-DEP composes into CTR-DEP-001 lifecycle operations. If a safe subprocess is
selected:

- executable path/version is approved;
- argv uses a closed action/property/unit vocabulary;
- environment is minimal and explicit for the real user manager;
- stdout/stderr are bounded, parsed only for documented machine fields, discarded, and never logged;
- timeout/cancellation affects only the AgentMonitor-owned helper;
- raw unit output, environment, and journal content do not cross the port.

DEP never issues arbitrary `systemctl`, `loginctl`, shell, unit, PID, or path operations. Lingering is query-only. The absence of a real user manager is `Blocked`/`Unsupported`, not permission to install a system service.

### 6.3 Build and runtime boundaries

Build consumes only repository source, committed approved locks, admitted tools, and explicit public build metadata. Dependency acquisition is a separate network-aware Foundation phase. Runtime installation consumes a complete validated local bundle and performs no network download.

The installed backend uses the approved Python runtime and isolated versioned environment. Frontend is prebuilt; Node/package manager is not a runtime requirement. Exact Python/ABI/architecture compatibility is validated before staging. Native wheels/binaries, if any, require target/platform admission and bundle inventory.

### 6.4 API/browser boundary

P01 supplies the production ASGI configuration and enforces request Host/Origin/authentication. DEP supplies coherent loopback settings and verifies actual sockets. P02 supplies immutable static assets and deep-link fallback rules. Static assets and API are served same-origin by the production FastAPI deployable; no separate development server, CDN, or external asset host exists in installed mode.

The deployment smoke workflow uses real login/session and generated-client requests. It does not create an unauthenticated readiness route. Native supervision consumes an internal readiness receipt or approved notification mechanism.

### 6.5 Database and operations boundary

PLAN-DB classifies schema and performs migrations/snapshots/database activation.
M08 owns maintenance intent/state, readiness, backups, restore orchestration,
and audit. DEP supplies exact target/runtime context, fenced service quiescence,
service phases, artifact/unit activation, and installed-version facts. Missing
receipts stop the workflow; DEP cannot infer success from process exit alone.

### 6.6 Provider boundary

Deployment has no provider network, CLI, profile, credential, or process boundary. It never installs provider software, changes provider profiles, starts/stops provider services, reads provider credentials, or inherits provider environment values. Post-deploy integration may observe adapters through ordinary M08 health only.

### 6.7 Real verification environment

- All installation/service/filesystem claims run on the actual target Linux workstation under the intended normal user.
- Generic failure mechanics may use a second isolated AgentMonitor target/root and AgentMonitor-owned processes/files on the same real kernel/filesystem/user manager.
- Login autostart requires a real owner session transition.
- Upgrade/rollback requires real versioned AgentMonitor artifacts and a real application-created database; schema/data paths unavailable before a prior release remain Blocked.
- Browser checks use the production build and real supported browser.
- Provider agents may continue running during deployment verification but are observed only to prove they were not controlled or modified.
- Containers, fake systemd, chroots, mocked filesystem calls, recorded command output, and in-memory SQLite do not satisfy T5/T7.

## 7. Security and privacy

### 7.1 Trust boundaries and controls

| Threat | Required control | Evidence |
|---|---|---|
| Installer runs as root/system-wide | reject UID 0/system roots; no sudo/polkit/capability path | real root-rejection and source/import review |
| Malicious bundle traversal/symlink | closed manifest, normalized relative members, no links/special types, exact digests | real malicious isolated bundle mechanics, never a provider fixture |
| Existing path is attacker-controlled | owner/mode/type/symlink/hard-link validation through held object refs | real isolated filesystem tests |
| `.env` leaks or is overwritten | owner-only path, never print/read for diagnostics/replace/copy/bundle | pre/post identity/mode and artifact scans |
| Unit executes arbitrary command | fixed template/entrypoint/unit; no shell or caller argv | rendered unit/source and real fixed-action tests |
| Service exposed to LAN | fixed loopback preflight plus actual socket inspection and P01 Host/Origin | real network tests |
| Upgrade destroys database | verified backup, quiescence, explicit migration, preserve current, compatible rollback | real T7 upgrade/recovery |
| Old UI runs with new API | build/OpenAPI/client compatibility and atomic release activation | real browser/version mismatch test |
| Crash leaves mixed release | fsynced journal, immutable generations, atomic current/unit switch, deterministic recovery | terminate AgentMonitor-owned isolated deploy at approved phases |
| Uninstall removes owner data | exact inventory; preserve-data invariant; no purge API | real isolated install/uninstall/reinstall |
| Service action hits provider agent | fixed unit, no PID/signal input, before/after provider process observation | owner-coordinated no-control proof |
| Build/install adds unreviewed dependency | frozen locks, offline bundle, SBOM/notices/license/digest gates | real bundle inventory and dependency review |
| Logs/evidence leak paths/output | typed allowlist, stable codes, bounded fields, scanner | real journal/log/report scan |

### 7.2 Secret handling

DEP treats `.env` as an opaque owner-managed secret file. Allowed operations are: test existence/type/owner/mode through platform metadata, create an absent comment-only shell after owner confirmation, pass its approved object reference to the application, and preserve it untouched. DEP does not parse, serialize, hash for display, back up, migrate, compare values, print, or include it in evidence.

Systemd unit content contains only the config-file path reference, not `Environment=` secret values. Service/process logs cannot dump environment. GitLab tokens are development-only and never loaded by the service or deployment bundle. Provider credentials remain in provider stores.

### 7.3 Least privilege and filesystem safety

- Normal user only; no group/world-writable AgentMonitor-owned object.
- Created directories default `0700`; sensitive/data/config files `0600`; executable launchers/runtime binaries `0700` unless the approved artifact requires a narrower portable mode.
- Service `UMask=0077`.
- Every write/delete target is resolved from an approved root and exact object reference.
- No recursive operation targets an unresolved or broad path.
- Unit hardening is evidence-driven and must preserve required read-only provider observation while restricting writes to AgentMonitor-owned roots.
- Unknown files or ownership changes stop repair/uninstall cleanup.

### 7.4 Local web security

DEP enforces local-mode invariants before process start: exact IPv4 loopback bind, canonical origin/host/port coherence, proxy trust off, no wildcard CORS, authenticated docs, no development reload, and no external static assets. After start it inspects actual listening sockets through A04 and sends real Host/Origin requests through P01. Any non-loopback listener or mismatch stops readiness and triggers rollback/recovery according to phase.

Remote use is not enabled by editing `.env`. A future remote profile requires its own ADR, TLS/proxy/multi-user threat model, configuration contract, migration, and deployment plan.

### 7.5 Privacy and data-minimization proof

Release bundles are built from source and dependency artifacts only. Installed manifests/journals/receipts contain version and lifecycle metadata only. The deployment field register must trace every output to a requirement and classify disclosure.

Prohibited from bundles, unit files, launchers, manifests, deployment records/journals, logs, evidence, SBOM metadata, and screenshots:

- real usernames, home paths, hostnames, emails, accounts, provider/profile identifiers;
- `.env` values, passwords, API/OAuth/session/CSRF tokens, cookies, OTP/MFA/recovery values;
- prompts, responses, tools, source content, arbitrary environment, terminal output, provider payloads;
- database rows, SQL, backup contents, raw service output, raw exceptions, process command lines.

Build and installed artifacts receive a production secret/content/path scan. Findings stop the operation and invoke the incident runbook; they are not copied into chat or committed.

### 7.6 No-control proof

Contracts and production source must contain no operation accepting a monitored PID, provider unit/service, terminal, input, signal, credential switch, route, or provider profile path. A04's service implementation accepts only the fixed AgentMonitor unit. Stop/restart cancellation affects AgentMonitor-owned tasks/helpers only. Owner-reviewed pre/post evidence confirms concurrently running provider agents and default profiles were unchanged within the approved observation method.

## 8. Configuration and operations

### 8.1 Configuration ownership and exact proposed keys

Names below are proposed and cannot enter `.env` until CTR-CONFIG synchronization. DEP owns deployment-profile/layout settings; P01 owns HTTP semantics; PLAN-DB/M08 own their path semantics. DEP validates the combined profile.

| Proposed key | Semantic owner | Type/default | Secret | Reload | Deployment rule |
|---|---|---|---|---|---|
| `AGENTMONITOR_DEPLOYMENT_PROFILE` | DEP | enum; fixed `linux_local_v1` | no | restart | no remote profile in V1 |
| `AGENTMONITOR_DEPLOYMENT_RELEASE_DIR` | DEP | derived approved data-root path | no, path-sensitive | restart | value never diagnosed; cannot escape root |
| `AGENTMONITOR_DEPLOYMENT_STATE_DIR` | DEP | derived approved state-root path | no, path-sensitive | restart | journal/receipts only |
| `AGENTMONITOR_API_BIND_HOST` | P01/DEP | fixed `127.0.0.1` in local profile | no | restart | any other value rejected |
| `AGENTMONITOR_API_PORT` | P01/DEP | integer 1..65535; exact default pending | no | restart | must match origin/host and be available |
| `AGENTMONITOR_API_PUBLIC_ORIGIN` | P01 | exact derived `http://127.0.0.1:<port>` | no | restart | no alias/path/query/fragment/credentials |
| `AGENTMONITOR_API_TRUSTED_HOSTS` | P01 | exact singleton derived host:port | no | restart | no wildcard/comma ambiguity |
| `AGENTMONITOR_PERSISTENCE_DATABASE_PATH` | PLAN-DB/DEP | derived approved database object | no, path-sensitive | restart | exact installed DB only |
| `AGENTMONITOR_OPERATIONS_BACKUP_DIR` | M08/DEP | derived approved backup root | no, path-sensitive | restart | outside release/config/profile roots |
| `AGENTMONITOR_OPERATIONS_ARTIFACT_DIR` | M08/DEP | derived approved artifact root | no, path-sensitive | restart | owner-only |
| `AGENTMONITOR_OPERATIONS_STATE_DIR` | M08/DEP | derived approved operations state root | no, path-sensitive | restart | distinct from DEP journal where contracts require |
| `AGENTMONITOR_OPERATIONS_LOG_DIR` | M08/DEP | derived approved log root | no, path-sensitive | restart | owner-only, local |

The `.env` file path itself is not an environment variable passed from an arbitrary caller; it is selected by the deployment target contract. Security-critical values fail closed. The deployment record may state safe sources/contract versions and `configured | missing` for required secret keys only through Foundation, never values or value-derived properties.

### 8.2 XDG validation and creation policy

Resolution precedes creation and has no side effects. DEP records the effective path classes as opaque platform refs. Creation occurs only within the exact approved user roots after bundle and target preflight. Existing objects must have expected owner, type, mode, filesystem/atomic support, and containment. Permissions that are too broad are not silently changed unless the explicit repair action and owner authorize that exact AgentMonitor-owned object; default behavior is fail closed.

`XDG_RUNTIME_DIR` is mandatory for the real user service and must be current-user-owned with suitable lifecycle. DEP does not substitute `/tmp`. Missing runtime dir/user manager makes service installation Blocked for that session.

### 8.3 Health, readiness, and status

CTR-DEP-001 contributes these narrow safe service/deployment facts to M08:

- target/platform/deployment-contract version;
- active/previous/candidate release states and build/version compatibility;
- fixed unit install/enable/manager/application states;
- observed lingering category;
- bind-profile validation and actual listener state category;
- journal/operation/recovery state;
- last lifecycle action, duration, safe outcome;
- config/path/artifact compatibility categories and separately referenced DB/M08 receipts;
- no raw paths, PID, username, port unless disclosure is explicitly approved, unit output, or environment.

Liveness and readiness remain separate. DEP's leaf status can be partial when
M08/API is unavailable, but cannot label the application ready. Composite
operator status may display an already-computed M08 readiness result; M08 never
consumes that composite view. A healthy unit plus failed schema or failed
required component is not ready. A degraded optional provider may keep normal
readiness only according to M08 policy.

### 8.4 Canonical automation ownership

The common dispatcher and final syntax are Foundation/integration-owned. PLAN-DEP owns the behavior/selectors below. The proposed source registration is under `tooling/automation/deployment/**`; no separate ad hoc shell scripts are allowed.

#### `AUTO-BUILD` deployment portion

The canonical build routine must:

1. require an approved real Git/source identity or explicitly mark a local declared-change build as non-release;
2. verify exact runtime/tool/lock/generated states and refuse lock drift;
3. build the backend artifact and production frontend from clean locked environments;
4. generate/validate OpenAPI, regenerate/compile client, and bind their digests to frontend/backend metadata;
5. assemble the exact section 3.3 bundle with no operator `.env`, database, evidence, provider, home, or network-derived runtime data;
6. generate direct/transitive SBOM and notices and verify license/security/secret policies;
7. generate member digests and canonical manifest deterministically;
8. rebuild in a clean second build root according to the approved reproducibility definition and compare;
9. emit a bounded receipt with command ID, source/build/bundle IDs, boundary, status, and artifact reference, never local paths or secret findings;
10. return nonzero on missing, drifted, unsafe, incompatible, Failed, or required Blocked input.

It does not install, deploy, migrate, contact providers, create releases, or publish.

#### `AUTO-GIT-PREFLIGHT` deployment/release portion

The canonical preflight is read-only and must:

1. verify the checkout is a real Git worktree; absence is `Blocked` and nonzero;
2. verify expected repository identity, remote host/project, branch/upstream, detached-head state, and release/tag policy without changing them;
3. classify clean versus explicitly declared changes and reject undeclared/untracked deployment inputs;
4. verify no secret-sensitive files (`.env`, databases, backups, profiles, evidence) are tracked or staged;
5. run the required plan/docs/test/quality/build/generated/schema/dependency checks for the intended action;
6. verify commits/tags/signing policy after it is approved, without creating a commit/tag/push;
7. emit sanitized repository/source status and nonzero on wrong remote/branch, divergence, secret finding, generated drift, red gate, or absent policy.

It never initializes Git, changes a remote/branch/index, commits, tags, pushes, creates GitLab resources, or prints token/remote credentials.

#### `AUTO-DEPLOY`

The canonical deploy routine has closed actions: `preflight`, `install`, `upgrade`, `status`, `start`, `stop`, `restart`, `enable-at-login`, `disable-at-login`, `repair`, `rollback`, and `uninstall-preserve-data`. There is no arbitrary action, unit, command, path, or `purge`.

It must:

- accept exact approved bundle/target/release object references, never broad paths from API/browser;
- call the production ports and workflows in this plan, not duplicate shell logic;
- precompute rollback/recovery before the first write;
- invoke `AUTO-BACKUP` and `AUTO-MIGRATE` by typed receipt where required;
- journal/fence every mutating action and fail closed on ambiguity;
- verify service/readiness/API/UI/login/post-deploy conditions at the real boundary;
- keep Passed/Failed/Blocked/Not Run distinct and return nonzero unless every mandatory row for the action passes;
- produce a bounded redacted receipt and exact next recovery action;
- be idempotent where semantics allow and refuse mismatched replay;
- never mutate lingering, provider state, monitored processes, remote network exposure, Git, or external resources.

The exact executable command is not authoritative until implemented, registered, and real-tested. A table or successful manual `systemctl` session is not automation.

### 8.5 Coordination with other canonical routines

| Routine | DEP responsibility | Non-owner responsibility |
|---|---|---|
| AUTO-PLAN-CHECK | ensure PLAN-DEP artifact, scenarios, registry, and CS review are included | integration owns validator |
| AUTO-DOCS-CHECK | deployment paths/contracts/runbooks/config/command references | Foundation/integration owns common validator |
| AUTO-TEST | select all DEP T5/T7 and integrated T2/T3/T4 scenarios; preserve statuses | test steward owns dispatcher/evidence aggregation |
| AUTO-QUALITY | unit/template/path/secret/import/config/license/security checks | Foundation/security own shared tools |
| AUTO-BUILD | native bundle assembly/validation | Foundation builds backend/frontend and owns locks/tools |
| AUTO-MIGRATE | target/runtime/quiesce/restart/rollback sequencing | PLAN-DB schema, M08 backup/health, modules validation |
| AUTO-BACKUP | installed target/service/path context | M08 owns workflow, PLAN-DB snapshot |
| AUTO-RESTORE | service stop/restricted/normal start and installed compatibility | M08/DB/M01 own restore/data/invalidation |
| AUTO-DEPLOY | lifecycle orchestration and receipts | platform executes fixed primitives; modules supply health |
| AUTO-RELEASE | provide bundle/deploy/rollback evidence | PLAN-INT owns release aggregation/publication authority |

### 8.6 Operational logs and measurements

Allowed structured events: operation/release/target IDs, lifecycle phase/state, contract/build/schema/unit-template versions, safe receipt IDs, duration, bounded bytes/counts, rollback class, and stable outcome code. Raw path, command, unit output, environment, `.env`, account/provider data, and exception text are prohibited.

Allowed local measurements include build/bundle size/duration, install/upgrade phase duration, service start/stop/readiness duration, restart count class, deployment lock age, and release-count/disk-space classes. Labels are bounded and sent nowhere.

### 8.7 Operator procedures to implement and exercise

- preflight target/runtime/user manager/bundle without writes;
- first install, `.env` owner checkpoint, M01 bootstrap, and login verification;
- start/stop/restart/status and enable/disable at login;
- verify actual login autostart and browser-independent collection;
- inspect lingering without changing it;
- build and verify a native release bundle;
- upgrade with fresh backup/migration/restricted start;
- rollback artifact-only and backup-recovery cases;
- recover an interrupted staged/install/migrate/activate/validate operation;
- diagnose unsafe XDG paths/modes, missing runtime dir, port conflict, remote bind, unit failure, crash loop, and readiness failure;
- uninstall while preserving data and reinstall against preserved data;
- verify provider agents/profiles were untouched.

Commands remain Planned until the command registry points to implemented and real-executed automation.

## 9. Test design before implementation

### 9.1 Evidence integrity rules

- Every scenario below is `Not Run` at plan creation.
- A Red is valid only when the admitted toolchain is working and the real production path fails for the intended missing/incorrect behavior. Missing packages, syntax errors, unavailable systemd, absent prior releases, or missing owner authority are not Red.
- T5/T7 uses the actual target Linux kernel/filesystem/user manager and production deployment code. A container, fake systemd, emulated filesystem, patched subprocess, or recorded command output cannot pass it.
- Filesystem failure tests use exact isolated AgentMonitor-owned roots created for the test on the real target filesystem. They never target the operator's active configuration/data/home or provider directories.
- Build tests use the actual locked build graph and real build tools. An intentionally malformed AgentMonitor-owned bundle can test rejection mechanics, but cannot prove a real release builds or installs.
- Install/upgrade tests use complete real bundles produced by `AUTO-BUILD`, a real file-backed SQLite database created through production migrations/use cases, the real production server, and the built frontend.
- Tests never read the operator's `.env`. Isolated installations create their own secret configuration through the production bootstrap flow. Secret values never enter output/evidence.
- No mock, fake, stub, monkeypatch, emulator, replay, fixture service, seeded telemetry, demo account, test-only unit, placeholder dashboard value, in-memory SQLite, direct database insertion, or test-only production branch is permitted.
- Generic install/service mechanics may use a second real AgentMonitor installation target and AgentMonitor-owned service instance only if the fixed target/unit contract explicitly supports an isolated test identity. Such evidence proves generic mechanics, not the production unit until the real production unit is exercised.
- Provider agents are never started/stopped for deployment tests. Naturally running agents may be observed only to prove absence of control/mutation.
- Every result records exact kernel/distribution/systemd/Python/build/schema/bundle versions, real boundary, command ID, status, duration, sanitized evidence reference, and cleanup result. Failed, Blocked, and Not Run remain visible.

### 9.2 Real build and release-bundle scenarios

| Test ID | Requirement/AC | Real dependencies | Expected behavioral Red | Green/pass condition | Coordination |
|---|---|---|---|---|---|
| DEP-BUILD-001 | NFR-COMP-001 | actual source, approved runtimes, committed locks | bundle cannot be reproduced or lacks manifest | `AUTO-BUILD` creates one complete versioned bundle | FND/build steward |
| DEP-BUILD-002 | FR-OPS-006 | real backend wheel/build metadata | backend/app/build identity missing or disagrees | manifest and installed package identities agree | FND/M08 |
| DEP-BUILD-003 | NFR-API-002 | real OpenAPI generation/client compilation | OpenAPI/client digest drift is accepted | canonical OpenAPI/client digests match build | P01/P02 |
| DEP-BUILD-004 | FR-OPS-006 | production frontend build | frontend/API/backend versions can be mixed | bundle validator rejects mismatch and valid set aligns | P01/P02 |
| DEP-BUILD-005 | FR-OPS-005 | real repository/build roots and artifact scanner | operator/local/prohibited file enters bundle | strict member inventory contains only approved build inputs | security |
| DEP-BUILD-006 | NFR-LIC-001 | actual locked Python/Node/tool graph | SBOM omits a runtime member or unknown package passes | bundle SBOM reconciles to all shipped components | dependency owner |
| DEP-BUILD-007 | NFR-LIC-001 | actual upstream license inventory/notices | missing/incompatible/unclear license passes | reviewed notices/licenses cover shipped graph | license reviewer |
| DEP-BUILD-008 | AC-V1-007 | real source/build/bundle scanner | secret/content/path canary or real finding is ignored | sanitized scan has no unresolved finding | security; contaminated isolated input contained |
| DEP-BUILD-009 | NFR-SEC-001 | real bundle files on filesystem | unmanifested, link, special, traversal, duplicate member accepted | validator rejects before install and writes nothing | generic AgentMonitor-owned artifact mechanics |
| DEP-BUILD-010 | NFR-COMP-001 | two independent clean real build roots | functional reproducibility definition is violated | outputs/differences match approved reproducibility policy | FND/release |
| DEP-BUILD-011 | NFR-PLAT-001 | real target architecture/Python ABI | incompatible artifact stages | preflight rejects before target mutation | platform/dependency |
| DEP-BUILD-012 | NFR-PRIV-002 | real build/browser process network observation | analytics/crash/CDN/update egress exists | no prohibited egress/runtime external asset | privacy/security |

### 9.3 Real XDG, path, permission, and filesystem scenarios

| Test ID | Requirement/AC | Real dependencies | Expected behavioral Red | Green/pass condition | Coordination |
|---|---|---|---|---|---|
| DEP-FS-001 | FR-OPS-001 | real normal-user Linux/XDG context | defaults resolve outside approved user roots | exact path classes resolve safely without writes | A04-LINUX |
| DEP-FS-002 | NFR-SEC-001 | isolated real relative/invalid XDG context | unsafe relative root accepted | preflight fails and creates nothing | A04/security |
| DEP-FS-003 | NFR-SEC-001 | real target executed as UID 0 in safe read-only preflight | root install proceeds | root rejected before any filesystem/service action | owner/security; no actual install as root |
| DEP-FS-004 | NFR-SEC-001 | isolated real wrong-owner/type/mode object | unsafe existing object adopted/chmodded silently | typed rejection and no mutation | A04/security |
| DEP-FS-005 | NFR-SEC-001 | isolated real symlink/traversal/hard-link anomaly | operation escapes or follows unsafe object | held-ref validation rejects before write/delete | A04/security |
| DEP-FS-006 | FR-OPS-005 | isolated real `.env` through production config/bootstrap | install exposes or replaces file | absent shell created only at checkpoint; existing bytes untouched | M01/FND/security |
| DEP-FS-007 | NFR-SEC-001 | real created install roots/files | broad permissions survive successful install | all objects match approved owner/mode/type | A04/security |
| DEP-FS-008 | NFR-RES-001 | real same-filesystem staging and process interruption | partial staging becomes active | active reference unchanged; partial classified | approved isolated termination packet |
| DEP-FS-009 | NFR-RES-001 | isolated real cross-device roots | atomic activation assumed across filesystems | preflight rejects or approved non-atomic plan remains unsupported | A04 |
| DEP-FS-010 | NFR-SEC-001 | real low-space isolated filesystem/limit | install exhausts reserve or harms current release | preflight blocks and current data/artifact remain | approved resource test |
| DEP-FS-011 | NFR-SEC-001 | real unknown file beneath isolated target | repair/uninstall deletes unknown file | conflict reported and unknown object preserved | security |
| DEP-FS-012 | NFR-COMP-001 | real immutable installed release | post-install member modification goes unnoticed | status/repair detects manifest mismatch and refuses activation | DEP/security |
| DEP-FS-013 | NFR-OBS-001 | real deployment journal interruption | journal is partial/unreadable or exposes data | prior/final canonical generation recoverable and safe | A04/operations |
| DEP-FS-014 | NFR-PLAT-001 | real target filesystem | fsync/atomic reference behavior inferred | exact target behavior passes or deployment is Blocked | A04-LINUX |

### 9.4 Real installation and first-start scenarios

| Test ID | Requirement/AC | Real dependencies | Expected behavioral Red | Green/pass condition | Coordination |
|---|---|---|---|---|---|
| DEP-INSTALL-001 | FR-OPS-001 | real target Linux, bundle, isolated XDG install | clean preflight mutates target or misses prerequisite | complete read-only preflight with safe receipt | owner/A04 |
| DEP-INSTALL-002 | AC-OPS-001 | real valid bundle and normal user | clean install cannot materialize exact layout | release/unit/launcher/data roots installed with correct ownership | owner deployment window |
| DEP-INSTALL-003 | AC-V1-004 | real absent DB and production migrations | service startup creates schema implicitly | explicit `AUTO-MIGRATE` initializes; normal start does no DDL | PLAN-DB |
| DEP-INSTALL-004 | FR-IAM-001 | real M01 production bootstrap | default password or secret in unit/env output | owner initializes no-default admin via approved flow | M01/owner |
| DEP-INSTALL-005 | AC-UI-001 | real installed service/browser/database | login cannot complete after bootstrap | real password login/session/logout works | M01/P01/P02 |
| DEP-INSTALL-006 | FR-OPS-002 | real initial service and DB | PID/unit active before readiness called success | typed setup/ready state and blocker are exact | M08 |
| DEP-INSTALL-007 | NFR-TEST-001 | same real manifest/target repeated | repeat duplicates files/service/database initialization | install is idempotent/no-op with same receipt | DEP/test |
| DEP-INSTALL-008 | NFR-COMP-001 | different real manifest reusing release ID | mutable ID collision overwrites release | conflict before change | build/DEP |
| DEP-INSTALL-009 | NFR-RES-001 | real port occupied by AgentMonitor-owned harmless listener | installer kills process or selects fallback port silently | safe conflict; no listener control/config drift | P01/A04 |
| DEP-INSTALL-010 | NFR-SEC-001 | valid local bundle with network disabled | install attempts runtime dependency download | installation succeeds offline or blocks before mutation | dependency/security |

### 9.5 Real systemd user-service and lifecycle scenarios

| Test ID | Requirement/AC | Real dependencies | Expected behavioral Red | Green/pass condition | Coordination |
|---|---|---|---|---|---|
| DEP-SVC-001 | FR-OPS-001 | real user systemd manager | system manager/root path used or manager assumed | only current user's manager and fixed unit used | A04/owner |
| DEP-SVC-002 | AC-OPS-001 | real installed unit | start succeeds by PID only or wrong artifact | fixed active release starts and readiness validates | M08/FND |
| DEP-SVC-003 | AC-OPS-001 | real running service | stop leaves work/resources or affects providers | graceful bounded stop; DB closes; provider agents unchanged | M04/DB/A04/owner |
| DEP-SVC-004 | AC-OPS-001 | real stopped/running service | status conflates unit/PID/readiness | exact unit/application/schema/version states returned | M08 |
| DEP-SVC-005 | AC-OPS-001 | real service restart | restart duplicates jobs/loses leases or targets agent | AgentMonitor only restarts; recovery invariants hold | M04/M08 |
| DEP-SVC-006 | FR-OPS-001 | real enable/disable operations | arbitrary unit or lingering changes | only fixed unit enablement changes | A04/security |
| DEP-SVC-007 | AC-OPS-002 | real service, production browser and collection | closing browser stops service/scheduler | service/collection continues; reopen reflects API state | M04/P02/owner |
| DEP-SVC-008 | FR-SAFE-002 | real concurrently running provider agents | fixed lifecycle action signals/restarts provider process | pre/post approved process evidence unchanged | A04/owner |
| DEP-SVC-009 | FR-SAFE-002 | real service contract/source | arbitrary unit/action/PID is accepted | closed request rejects before I/O | security |
| DEP-SVC-010 | NFR-RES-001 | real AgentMonitor-owned service crash | unbounded crash loop or silent stop | bounded restart/start-limit and visible failure | approved isolated service failure |
| DEP-SVC-011 | NFR-RES-001 | real shutdown deadline condition | stop hangs indefinitely or kills monitored agents | owned tasks bounded; timeout state explicit | M04/A04 |
| DEP-SVC-012 | FR-OPS-001 | real owner session transition | enabled flag treated as autostart proof | actual login starts service and reaches approved readiness | owner logout/login coordination |
| DEP-SVC-013 | FR-OPS-001 | real lingering state before/after operations | install/enable changes lingering | state unchanged and reported | owner/A04 |
| DEP-SVC-014 | NFR-OBS-001 | real unit/app logs and failures | raw env/unit output/path/secret appears | structured allowlisted output only | security/M08 |

### 9.6 Real loopback, API, static-frontend, and browser scenarios

| Test ID | Requirement/AC | Real dependencies | Expected behavioral Red | Green/pass condition | Coordination |
|---|---|---|---|---|---|
| DEP-NET-001 | FR-IAM-007 | real installed socket process | wildcard/LAN listener opens | only approved `127.0.0.1` socket listens | P01/A04/security |
| DEP-NET-002 | FR-IAM-007 | real invalid non-loopback config in isolated install | service starts remotely | startup fails before bind with safe code | P01/security |
| DEP-NET-003 | FR-IAM-007 | real Host request variants | unapproved Host reaches app | exact configured host:port only | P01 |
| DEP-NET-004 | FR-IAM-007 | real browser foreign Origin/preflight | cross-origin request succeeds/CORS wildcard appears | foreign Origin denied, no permissive CORS | P01/M01 |
| DEP-NET-005 | NFR-API-001 | real server | API mounted outside/missing `/api/v1` | exact versioned API reachable after auth | P01 |
| DEP-NET-006 | NFR-API-002 | real built static bundle/server | development server/CDN/direct file is required | same-origin production assets served locally | P01/P02 |
| DEP-NET-007 | AC-UI-001 | real built browser/login | deep link/refresh breaks auth shell | protected deep link, login, refresh function | P02 |
| DEP-NET-008 | AC-V1-003 | real OpenAPI/generated client/browser | stale client calls incompatible API | identity gate blocks mixed set; valid set performs real call | P01/P02 |
| DEP-NET-009 | NFR-SEC-001 | real docs endpoints/browser | docs/OpenAPI exposed unauthenticated or CDN used | authenticated local assets only | P01 |
| DEP-NET-010 | NFR-RES-001 | real port collision/restart | service falls back to remote/different port | remains failed with exact safe remediation | P01/DEP |

### 9.7 Real upgrade, migration, activation, and rollback scenarios

| Test ID | Requirement/AC | Real dependencies | Expected behavioral Red | Green/pass condition | Coordination |
|---|---|---|---|---|---|
| DEP-UPG-001 | AC-OPS-005 | real current install + new real bundle | preflight mutates active install | compatibility/recovery plan produced read-only | owner |
| DEP-UPG-002 | FR-OPS-003 | real M08 backup workflow | risky upgrade proceeds without fresh valid backup | required backup receipt gates quiescence | M08/PLAN-DB |
| DEP-UPG-003 | AC-OPS-005 | real running service/jobs/DB | migration starts before quiescence/drain | typed quiescence and engine-dispose receipts required | M04/DB/M08 |
| DEP-UPG-004 | AC-V1-004 | real supported prior-release database | normal startup migrates or upgrade misses revision | explicit approved chain reaches target and validates | PLAN-DB/module owners |
| DEP-UPG-005 | NFR-RES-001 | real old service while candidate stages | staging interrupts current availability | current remains available until quiescence | DEP |
| DEP-UPG-006 | NFR-COMP-001 | real artifact/unit activation | mixed backend/frontend/unit generation observable | switch selects one complete compatible generation | FND/P01/P02 |
| DEP-UPG-007 | AC-OPS-005 | real restricted start | normal collectors run before validation | restricted validators pass before normal mode | M04/M08 |
| DEP-UPG-008 | NFR-COMP-001 | real incompatible frontend/API candidate | candidate becomes active | compatibility blocks before/at activation and old set retained | P01/P02 |
| DEP-UPG-009 | AC-OPS-005 | real candidate start/readiness failure | failure called success or old artifact lost | artifact-only rollback restores old ready release where schema permits | owner/DEP |
| DEP-UPG-010 | AC-OPS-005 | real failed migration in isolated target | old binary starts on incompatible/partial schema | service remains restricted/stopped and DB recovery follows plan | DB/M08/owner |
| DEP-UPG-011 | AC-OPS-005 | real post-migration module validation failure | normal readiness ignores invariant failure | rollback/forward-fix class invoked, data preserved | module owners/M08 |
| DEP-UPG-012 | FR-OPS-005 | real existing `.env`, data, backups, profiles | upgrade rewrites/copies/deletes mutable roots | pre/post protected objects unchanged except approved DB migration | security/owner |
| DEP-UPG-013 | NFR-RES-001 | real interruption at approved activation boundary | journal cannot determine active generation | deterministic resume/rollback from actual identities | isolated termination packet |
| DEP-UPG-014 | NFR-COMP-001 | prior binary plus current schema | incompatible rollback starts | range check blocks and selects backup/forward-fix path | PLAN-DB |

### 9.8 Real recovery, uninstall, and reinstall scenarios

| Test ID | Requirement/AC | Real dependencies | Expected behavioral Red | Green/pass condition | Coordination |
|---|---|---|---|---|---|
| DEP-REC-001 | NFR-RES-001 | real interrupted staging journal | unknown temp is adopted/active | reconciled as exact incomplete object; active unchanged | DEP/A04 |
| DEP-REC-002 | NFR-RES-001 | real interrupted unit switch | wrong unit/release remains mixed | prior/candidate digests determine safe repair/rollback | A04 |
| DEP-REC-003 | NFR-RES-001 | real corrupt/incompatible journal copy | automation guesses or overwrites | recovery-required, no lifecycle write | security/DEP |
| DEP-REC-004 | AC-OPS-004 | real valid backup/current DB/service | restore cannot quiesce or current DB overwritten | current preserved and staging validated before activation | M08/DB/owner |
| DEP-REC-005 | AC-OPS-004 | real restored DB/M01 state | restored sessions/tokens remain accepted | invalidation then owner re-login required | M01/M08 |
| DEP-REC-006 | AC-OPS-004 | real activation/readiness failure | preserved current cannot resume | tested rollback restores compatible prior system | DB/M08/DEP |
| DEP-REC-007 | NFR-RES-001 | real crash-loop after upgrade | repeated restart damages/retries migration | bounded failure; migration never implicit/repeated | A04/DB |
| DEP-REC-008 | FR-OPS-002 | real partial component failure after deploy | whole service rolls back/stops unnecessarily | required/optional readiness policy applied exactly | M08 |
| DEP-REC-009 | NFR-SEC-001 | real disk/permission failure in isolated recovery target | broad cleanup or data loss occurs | exact failure target preserved; no broad delete | owner-approved packet |
| DEP-REC-010 | AC-OPS-005 | real complete recovery rehearsal | runbook step cannot be executed by automation | canonical receipt reaches ready or truthful recovery-required | owner/operations |
| DEP-UNINSTALL-001 | FR-OPS-001 | real isolated installed service/data | uninstall leaves running/enabled unit | fixed unit stopped/disabled/removed | owner |
| DEP-UNINSTALL-002 | FR-OPS-005 | real isolated config/DB/backups/profiles | default uninstall deletes mutable owner data | all preserved classes unchanged | security/M08/M02 |
| DEP-UNINSTALL-003 | NFR-SEC-001 | real install plus unknown target object | uninstall removes unknown object | operation blocks/partial and preserves unknown | security |
| DEP-UNINSTALL-004 | NFR-COMP-001 | real preserved compatible DB + reinstall bundle | reinstall overwrites/misclassifies data | schema preflight and explicit migration preserve data | DB/owner |
| DEP-UNINSTALL-005 | FR-OPS-001 | real lingering before/after uninstall | lingering changes | exact observed state unchanged | A04/owner |
| DEP-UNINSTALL-006 | NFR-SEC-001 | production CLI/API surface | purge-data option exists or broad target accepted | no V1 purge operation in command/contract/API | security |
| DEP-UNINSTALL-007 | NFR-RES-001 | interruption during artifact removal | mixed service becomes active or data deleted | recovery receipt identifies exact remaining artifacts; data preserved | DEP |
| DEP-UNINSTALL-008 | NFR-DOC-001 | real uninstall/reinstall runbook exercise | documented command diverges from executable | registered automation performs documented preserve-data flow | operations |

### 9.9 Automation, Git, security, quality, platform, and documentation scenarios

| Test ID | Layer | Requirement/AC | Real dependencies | Expected behavioral Red | Green/pass condition |
|---|---|---|---|---|---|
| DEP-AUTO-001 | automation/T7 | AC-TEST-006 | real command registry and deploy selector | required scenario deselected/hidden | nonzero and explicit missing/Blocked row |
| DEP-AUTO-002 | automation/T7 | AC-TEST-001 | actual R/G/R evidence | setup failure accepted as Red | behavioral failure and commands/receipts required |
| DEP-AUTO-003 | automation/T5 | AC-OPS-001 | real production unit | command uses manual shell checklist | production ports execute fixed lifecycle |
| DEP-AUTO-004 | automation/build | NFR-COMP-001 | real build inputs/output | partial bundle receives success | fail-closed complete manifest receipt only |
| DEP-AUTO-005 | automation/recovery | AC-OPS-005 | real failure rehearsal | recovery-required exits zero | nonzero with exact safe next action |
| DEP-AUTO-006 | automation/security | AC-V1-007 | real logs/artifacts/evidence | scanner absent/finding hidden | absent/finding blocks with sanitized result |
| DEP-AUTO-007 | automation/docs | NFR-DOC-001 | actual command registry/runbooks | prose/TBD command accepted | docs gate requires verified registered command |
| DEP-AUTO-008 | automation/release | AC-TEST-006 | actual T5/T7 matrix | hosted CI green hides local Not Run | release gate keeps separate status and blocks |
| DEP-AUTO-009 | automation/idempotency | NFR-RES-001 | real same deploy command replay | duplicate migration/install/action occurs | same fingerprint returns same receipt |
| DEP-AUTO-010 | automation/authority | NFR-SEC-001 | real CLI invocation | browser/unprivileged request obtains local deploy authority | typed local authority required |
| DEP-GIT-001 | real Git | SDLC Git policy | current real checkout | non-Git checkout reported clean/ready | Blocked nonzero with no initialization |
| DEP-GIT-002 | real Git | NFR-SEC-001 | real isolated Git worktree | wrong remote/branch/detached state passes | exact policy violation fails without mutation |
| DEP-GIT-003 | real Git | AC-V1-007 | real worktree/index | `.env`/DB/profile/evidence tracked/staged | safe finding blocks without printing contents |
| DEP-GIT-004 | real Git | NFR-COMP-001 | real worktree with generated drift | drifted OpenAPI/client/manifest passes | preflight blocks |
| DEP-GIT-005 | real Git | NFR-DOC-001 | real untracked/modified files | undeclared release input ignored | clean or explicitly declared local state only |
| DEP-GIT-006 | real Git | NFR-SEC-001 | real preflight execution | preflight commits/tags/pushes/changes index | repository state unchanged |
| DEP-SEC-001 | security | FR-OPS-005 | real bundle/install/log/evidence | prohibited content/secret/path present | all scans/inventories clean |
| DEP-SEC-002 | security | NFR-SEC-001 | real installed objects | group/world permissions or wrong owner exist | owner-only policy passes |
| DEP-SEC-003 | security | NFR-OBS-001 | real failed deployment | raw exception/unit/command/environment output logged | typed safe event only |
| DEP-SEC-004 | privacy | NFR-PRIV-002 | real build/install/runtime network observation | analytics/crash/update upload occurs | no product telemetry/automatic egress |
| DEP-SEC-005 | privacy | NFR-PRIV-001 | real manifests/journals/API/UI | owner/provider/content field crosses DEP | operational allowlist only |
| DEP-SEC-006 | safety | FR-SAFE-002 | real contracts/source | agent control/routing/credential operation exists | prohibited API/import/symbol gate clean |
| DEP-SEC-007 | service | NFR-SEC-001 | real rendered unit | shell/root/capability/full environment is used | approved fixed least-privilege unit only |
| DEP-SEC-008 | network | FR-IAM-007 | real installed process | remote bind/proxy trust can be enabled casually | local profile rejects before readiness |
| DEP-SEC-009 | provider safety | FR-SAFE-002 | real concurrent provider agents/profiles | deployment changes provider state | pre/post approved observation unchanged |
| DEP-SEC-010 | uninstall | NFR-SEC-001 | real installed inventory | recursive/broad deletion path exists | exact enumerated object deletion only |
| DEP-ARCH-001 | architecture | NFR-ARCH-001 | real source/import graph | DEP imports domain/provider/API internals | boundary gate rejects |
| DEP-ARCH-002 | ownership | NFR-ARCH-002 | ownership manifest | artifact/path/contract has conflicting owner | exactly one owner and reviewed consumers |
| DEP-ARCH-003 | contract | NFR-COMP-001 | generated CTR-DEP/bundle/config schemas | breaking drift accepted | compatibility gate blocks or approved major/ADR exists |
| DEP-ARCH-004 | architecture | NFR-PLAT-001 | CTR-DEP and macOS plan | portable contract contains systemd/XDG field | portable semantics remain implementable independently |
| DEP-DEP-001 | dependency | NFR-LIC-001 | actual shipped lock/bundle | unadmitted package/tool shipped | every member traces to approval |
| DEP-DEP-002 | license | NFR-LIC-001 | actual bundle/SBOM/notices | incompatible/missing license unresolved | reviewed inventory passes |
| DEP-DEP-003 | supply chain | NFR-SEC-001 | actual tools/wheels/frontend artifacts | provenance/install script/native binary unreviewed | approved pinned provenance only |
| DEP-DEP-004 | runtime | NFR-LIC-001 | real offline install | installer fetches undeclared package | complete offline graph or fail before write |
| DEP-PLAT-001 | platform/T5 | NFR-PLAT-001 | target real Linux distribution/kernel/systemd | target generalized from another host | exact target matrix passes |
| DEP-PLAT-002 | platform/T5 | NFR-PLAT-001 | additional claimed real Linux host | container/emulator used as proof | each support claim has real-host evidence |
| DEP-PLAT-003 | portability | NFR-PLAT-001 | real macOS availability | Linux result labeled macOS pass | macOS separate Passed or Blocked |
| DEP-PLAT-004 | compatibility | NFR-COMP-001 | systemd/Python/kernel upgrade | old evidence silently reused | affected row unverified until rerun |
| DEP-HEALTH-001 | operations | FR-OPS-002 | real service/M08 | PID active is called ready | application readiness and blocker exact |
| DEP-HEALTH-002 | operations | FR-OPS-006 | real running release | versions guessed from filenames | authoritative build/schema/client facts |
| DEP-HEALTH-003 | operations | NFR-COMP-001 | real mismatched component | mismatch hidden | not-ready/incompatible visible |
| DEP-HEALTH-004 | operations | NFR-OBS-001 | real journal/status/logs | unsafe field exposed | allowlisted bounded facts only |
| DEP-HEALTH-005 | resilience | AC-OPS-003 | real naturally degraded optional adapter | entire service becomes unready | degradation remains isolated per manifest |
| DEP-HEALTH-006 | resilience | AC-OPS-003 | real required component unavailable | readiness incorrectly remains true | exact required blocker prevents normal ready |
| DEP-PERF-001 | performance | NFR-PERF-001 | real target clean start | startup exceeds approved measured budget | bounded startup/readiness percentile |
| DEP-PERF-002 | performance | NFR-PERF-001 | real release bundle/install | bundle/install disk/memory unbounded | approved resource budget holds |
| DEP-PERF-003 | performance | NFR-PERF-001 | real upgrade/database/activity | maintenance exceeds approved window without status | measured duration/progress/recovery visibility |
| DEP-PERF-004 | resilience | NFR-RES-001 | real repeated status requests | subprocess/process/resource leak | bounded stable resources |
| DEP-PERF-005 | reliability | FR-OPS-001 | real service over approved observation period | restart/health churn hidden | stable service or exact failures recorded |
| DEP-DOC-001 | docs | NFR-DOC-001 | real Markdown/contracts/registry | missing/broken plan/runbook links | AUTO-DOCS-CHECK passes |
| DEP-DOC-002 | docs | AC-V1-006 | actual command registry | invented/unverified command in runbook | every operational command resolves to evidence |
| DEP-DOC-003 | traceability | AC-V1-001 | actual requirements/scenarios/evidence | unmapped requirement/status | exact references resolve |
| DEP-DOC-004 | operations | AC-OPS-005 | real exercised runbooks | prose cannot recover real install | exercise record matches canonical receipts |
| DEP-TEST-001 | test integrity | AC-TEST-002 | real source/test graph | mock/fake/emulator/replay/fixture framework exists | prohibited mechanism gate clean |
| DEP-TEST-002 | status integrity | AC-TEST-006 | actual reports | Blocked/Not Run omitted | every scenario status explicit |
| DEP-TEST-003 | boundary | AC-TEST-003 | real DB/HTTP/browser/service | narrower layer claims full deploy | evidence labels exact real boundary |
| DEP-TEST-004 | TDD | AC-TEST-001 | actual change records | missing/irrelevant Red accepted | meaningful Red, Green, refactor evidence |

### 9.10 Failure, migration, and recovery coverage

The matrix covers missing/unsafe XDG roots, root execution, wrong owner/mode/type, symlink/traversal/hard-link anomalies, cross-device activation, low space, missing runtime directory, absent user manager, lingering state, invalid bundle/digest/license inventory, incompatible Python/architecture/schema/API/UI, `.env` preservation, port collision, remote bind, unit install/action failure, start/stop timeout, crash loop, interrupted staging/unit/release activation, missing backup, migration and module-validation failure, restricted-start/readiness failure, corrupted journal, restore activation failure, uninstall interruption, unknown files, and reinstall from preserved data.

Naturally unavailable prior-release data, provider failure, login-session behavior, disk-full, actual corruption, macOS, and long-running stability scenarios remain Blocked until their real safe conditions and authority exist. They are never simulated or relabeled Passed.

### 9.11 Red-green-refactor protocol

For every increment:

1. run the canonical baseline selector in the actual environment;
2. add the smallest real-boundary test and record the intended behavior failure;
3. verify the Red is not setup, missing dependency, missing permission, or unavailable system state;
4. implement the minimum production behavior in allocated paths;
5. run Green plus all affected contract/security/recovery selectors;
6. refactor while retaining Green;
7. scan artifacts/logs/evidence for prohibited data;
8. update contracts/runbooks/compatibility and record every non-Passed scenario.

No automatic retry can convert a flaky failure to Passed. A live unavailable state is Blocked, not a reason to create a fake unit/database/provider condition.

## 10. Implementation increments

No increment begins until its contracts, exact paths, dependency/runtime/tool decisions, canonical selector, real test resources, and file ownership are Approved.

| Increment | Owned files/area | Failing tests first | Minimum production change | Synchronization/docs | Exit evidence |
|---|---|---|---|---|---|
| DEP-I00 — contract/layout freeze | plan/contracts/layout/template proposals | DEP-ARCH-002..004, DEP-DOC-001/003 | freeze CTR-DEP/bundle/layout/config/automation schemas; no runtime behavior | register/ADR/ownership updates | Approved schemas and path allocation |
| DEP-I01 — bundle validator | `tooling/automation/deployment/bundle.py`, manifest models | DEP-BUILD-002..009 | closed manifest/member/digest/platform validator | bundle contract/security field register | real bundle filesystem R/G/R |
| DEP-I02 — native bundle assembly | build plugin + packaging templates | DEP-BUILD-001..012, DEP-DEP-001..004 | assemble backend/frontend/contracts/migrations/SBOM/notices | AUTO-BUILD docs | two clean real builds and scans |
| DEP-I03 — target/XDG preflight | preflight/layout | DEP-FS-001..007/009/010/014, DEP-INSTALL-001 | read-only target/runtime/filesystem preflight | configuration/layout docs | real Linux R/G/R |
| DEP-I04 — journal/staging/activation | journal/install core | DEP-FS-008/011..013, DEP-REC-001..003 | fenced journal, immutable staging, atomic current reference | recovery format/runbook | real interruption/recovery R/G/R |
| DEP-I05 — user unit/status | unit template + A04 port integration | DEP-SVC-001/004/006/009/013/014, DEP-HEALTH-001..004 | fixed unit rendering/install/read-only status/enablement/lingering observation | CTR-DEP service docs | real user-manager R/G/R |
| DEP-I06 — start/stop/restart | lifecycle orchestration | DEP-SVC-002/003/005/010/011 | production lifecycle with readiness/drain and safe failure | lifecycle runbook | real fixed service R/G/R |
| DEP-I07 — first install | install orchestration | DEP-INSTALL-002..010 | complete install, explicit migration/bootstrap/readiness | install/M01/DB docs | owner-coordinated real install |
| DEP-I08 — local network/static UI | profile + P01/P02 integration | DEP-NET-001..010 | coherent loopback profile, socket verify, static/deep-link smoke | API/UI/deploy docs | real HTTP/browser R/G/R |
| DEP-I09 — upgrade | upgrade orchestration | DEP-UPG-001..008/012 | backup/quiesce/migrate/activate/restricted/normal workflow | upgrade runbook | real supported prior-version R/G/R |
| DEP-I10 — rollback/recovery | rollback and recovery | DEP-UPG-009..014, DEP-REC-004..010 | precomputed rollback classes, restore coordination, journal recovery | recovery runbook | owner-approved real T7 |
| DEP-I11 — repair/uninstall/reinstall | repair/uninstall | DEP-UNINSTALL-001..008 | exact artifact repair and preserve-data uninstall | uninstall/reinstall docs | real isolated lifecycle R/G/R |
| DEP-I12 — canonical automation | deployment selectors/common dispatcher allocation | DEP-AUTO-001..010, DEP-GIT-001..006 | register fail-closed commands and structured receipts | command registry | real command negative/positive evidence |
| DEP-I13 — hardening/release | tests/docs/security/performance | DEP-SEC/ARCH/PLAT/HEALTH/PERF/DOC/TEST families | bounds, service hardening, compatibility and release evidence | final traceability/risk/known limits | actual complete status matrix |

### 10.1 Ordering and parallel-development safety

- I00 is central and serial.
- I01 can proceed within DEP-owned files after the manifest schema freezes; I02 needs Foundation build/dependency decisions and owns no manifests/locks itself.
- I03/I04 may proceed in distinct DEP files after CTR-PLAT-001 freezes, but one steward owns journal/state models.
- I05/I06 wait for A04 fixed-unit contracts and cannot edit A04 implementation files.
- I07 coordinates M01/DB/M08 and is sequential across first-install shared resources.
- I08 changes P01/P02/composition/generated files only through those owners.
- I09/I10 are exclusive deployment/recovery waves; no migration, restore, or service lifecycle agent runs concurrently on the same target.
- I11 acts only on DEP-owned artifacts and exact test targets.
- I12 common dispatcher/Git/build files are edited only by the integration/automation steward from DEP-supplied selector proposals.
- Migration head, OpenAPI, generated client, composition root, manifests/locks, service template, and command registry each have one writer per integration wave.

### 10.2 Stop and escalation conditions during implementation

Stop and return to contract synchronization if:

- a raw path, username, unit output, environment value, secret, provider identity, or content would cross a contract/log/evidence boundary;
- root, sudo, polkit, capability, system service, broad group, or lingering mutation appears necessary;
- install/upgrade would download runtime dependencies or contact a provider;
- an arbitrary unit/action/argv/path/PID can enter lifecycle code;
- a non-loopback bind, proxy trust, wildcard CORS, or remote profile is requested;
- database work would bypass AUTO-MIGRATE/AUTO-BACKUP/AUTO-RESTORE or copy a live SQLite file;
- rollback compatibility is ambiguous or would require editing migration history/data manually;
- repair/uninstall would delete an unknown or mutable owner-data object;
- `.env` would be parsed, printed, rewritten, bundled, copied, or exposed;
- a dependency/tool/license/security/provenance decision is unapproved;
- a real test requires destructive owner-data action, provider/process mutation, login-session interruption, or root authority not explicitly approved;
- another agent owns the shared file/target/service/migration/recovery operation;
- someone proposes a mock/fake/emulator/replay/fixture/seed/test-only path or claims hosted CI proves T5/T7.

## 11. Documentation outputs

Approved implementation must create/update, through assigned owners:

- `docs/modules/deployment-linux-native.md`: outcomes, boundaries, state machines, CTR-DEP-001, layout, service, health, errors, compatibility, limits;
- `docs/contracts/native-service-lifecycle-v1.md`: exact DTOs/ports/authority/idempotency/errors/versioning;
- native release-bundle manifest/layout schema and build provenance documentation;
- Linux install, first-login/bootstrap, status, start/stop/restart, and autostart runbook;
- upgrade/migration/backup/restricted-start/validation/rollback runbook;
- interrupted deployment/recovery and restore coordination runbook;
- preserve-data uninstall and compatible reinstall runbook;
- configuration registry with ownership, defaults, bounds, restart, and safe disclosure;
- verified command registry entries for build/Git/deploy selectors;
- service-unit source/hardening/compatibility and real systemd matrix;
- dependency admission, locked graph, SBOM, notices, license and provenance records;
- security/privacy field inventory, threat model, no-control/no-remote-bind proof;
- TDD evidence and real Linux/service/filesystem/browser/recovery matrix;
- traceability, risk, planning registry, known limitations, release notes, and operator troubleshooting.

Documentation uses no real usernames, paths, hostnames, ports tied to a machine, provider identities, accounts, screenshots containing live data, secret values, raw output, or invented operational commands. A command appears only after it exists in the command registry and has real execution evidence.

## 12. Dependency and license impact

No dependency, package, service, or tool is approved or installed by this Draft.

### 12.1 Candidate dependency posture

| Candidate/role | Purpose | Necessity/alternative | Admission state |
|---|---|---|---|
| Approved Python runtime | run installed backend/deployment automation | required by backend; exact supported line from Foundation | Candidate/Pending exact version/platform review |
| Backend wheel/wheelhouse tooling | reproducible offline application install | selected by Foundation resolver/build policy | Candidate/Pending; no second packaging stack |
| Production ASGI server | installed HTTP process | architecture requires production server | Candidate/Pending exact lifecycle/license/transitives |
| systemd user-manager tooling/interface | fixed service lifecycle | native Linux requirement; D-Bus library vs fixed CLI decided by A04 | Runtime dependency pending source/version review |
| Frontend build/runtime tools | build static assets only | Foundation/P02 locked graph; absent from installed runtime where possible | Candidate/Pending |
| Artifact/secret/license/SBOM scanners | fail-closed release gates | selected centrally; no upload/telemetry | Candidate/Pending exact tool graph |

PLAN-DEP proposes no daemon supervisor, updater, process-control library, Docker tool, cloud SDK, remote storage, privileged helper, archive framework, configuration templating engine, or telemetry/crash package. Prefer standard-library manifest/journal/file logic behind A04 safe primitives where it is demonstrably correct.

### 12.2 Admission record

Before any manifest/lock/import/install, record canonical upstream identity, exact version, purpose, why existing/standard tools are insufficient, direct/transitive licenses, maintenance/security policy, provenance/ownership, release activity, vulnerabilities/compromise history, native binaries/install scripts, supported Python/Linux/macOS/architecture, network/telemetry behavior, size/performance, exact pin/hash/lock, update/removal strategy, alternatives, SBOM/notices obligations, reviewer/date, and owner approval for any copyleft/custom/unclear license.

### 12.3 Bundle supply-chain requirements

- Every shipped runtime member appears in manifest, lock/provenance inventory, SBOM, and notices where applicable.
- Runtime installation is offline and rejects missing/unmanifested artifacts.
- Build tools are recorded even when not shipped.
- Native/browser binaries and install scripts receive explicit review.
- No build or install hook reads user home, `.env`, provider state, or starts network telemetry.
- Dependency/lock changes rebuild the bundle and invalidate prior approval until scans/reviews pass.
- The all-rights-reserved copyright remains Pavlo Sidelov <pavlo@sidelov.com>; this plan grants no public license.

## 13. Risks, unresolved decisions, and stop conditions

### 13.1 Risk register

| ID | Risk/question | Likelihood/impact | Mitigation/evidence | Owner | Status |
|---|---|---|---|---|---|
| DEP-R01 / R-013 | local service becomes network-exposed | Medium/Critical | fixed loopback profile, actual socket and Host/Origin tests | DEP/P01/security | Open |
| DEP-R02 / R-020 | upgrade/rollback loses database | Medium/Critical | fresh verified backup, quiescence, explicit migration, current preservation | DEP/DB/M08 | Open |
| DEP-R03 / R-005 | `.env`/provider/content leaks into build/log/evidence | Medium/Critical | opaque config, strict build context, scans, stop rule | security/DEP | Open |
| DEP-R04 / R-018 | native bundle ships risky/unlicensed dependency | Medium/Critical | admission, locks, SBOM/notices, offline inventory | dependency owner | Open |
| DEP-R05 | interrupted activation leaves mixed release/unit | Medium/Critical | immutable generations, atomic refs, fsynced journal | DEP/A04 | Open |
| DEP-R06 | lingering changed silently | Low/Major | query-only contract and pre/post evidence | DEP/A04/owner | Open |
| DEP-R07 | systemd hardening blocks provider observation or is silently weak | Medium/Major | evidence-driven directives and real provider/platform tests | A04/security | Open |
| DEP-R08 / R-011 | migration/service overlap corrupts SQLite | Medium/Critical | exclusive fence, quiescence, DB locks, restricted start | DEP/DB/M08 | Open |
| DEP-R09 / R-019 | hosted CI green mistaken for native readiness | High/Major | separate T5/T7 status and release refusal | integration/DEP | Open |
| DEP-R10 / R-023 | Linux layout/service leaks into portable core | Medium/Major | CTR-DEP semantic contract and import/schema gate | architecture/platform | Open |
| DEP-R11 | preserve-data uninstall deletes owner data | Low/Critical | exact inventory, no purge, unknown-file stop, real tests | DEP/security | Open |
| DEP-R12 | old UI/new API mismatch misleads owner | Medium/Critical | atomic release set and build/client/OpenAPI identity | DEP/P01/P02 | Open |
| DEP-R13 | runtime dependency download makes install irreproducible | Medium/Major | complete offline bundle and no-network test | DEP/FND | Open |
| DEP-R14 | rollback binary incompatible with migrated schema | Medium/Critical | explicit range and rollback class, backup/forward fix | DB/DEP | Open |
| DEP-R15 | login autostart unverified due session constraints | Medium/Major | owner-coordinated real login cycle; otherwise Blocked | owner/DEP | Open |
| DEP-R16 | service action targets a provider process/unit | Low/Critical | fixed unit, no PID/action input, no-control proof | A04/security | Open |
| DEP-R17 | XDG/symlink/ownership race escapes root | Medium/Critical | held refs, exact objects, atomic A04 primitives | A04/security | Open |
| DEP-R18 | Git/build automation mutates or publishes unexpectedly | Low/Critical | read-only preflight, separate external authority, state-diff tests | integration/release | Open |

### 13.2 Approval-blocking synchronization decisions

1. Exact supported Linux distribution/kernel/architecture/systemd/filesystem scope from A04 evidence.
2. Exact Python version/ABI, resolver, build frontend, wheel/wheelhouse format, and offline runtime-install mechanism.
3. Exact release bundle directory/archive format, canonical manifest encoding, digest algorithm, member policy, and reproducibility definition.
4. Exact repository paths and ownership for packaging, deployment automation, shared dispatcher, evidence, and docs.
5. Exact installed XDG layout, optional launcher path, modes, mutable/immutable object classes, and macOS-portable semantics.
6. Whether release environments are self-contained venvs or another approved versioned runtime layout; no implementation agent chooses privately.
7. Exact unit name/template, user target, service type/readiness notification, restart/start-limit/timeouts, resource limits, journaling, and hardening directives.
8. Exact systemd interface: fixed safe subprocess versus admitted D-Bus dependency.
9. Exact lingering inspection/record behavior and confirmation that mutation is excluded.
10. Exact default local port and approved IPv4-only versus explicit dual-loopback behavior.
11. Exact P01 config key ownership, bind/origin/host coherence, cookie local-HTTP policy, proxy/CORS/docs/static behavior.
12. Exact frontend static layout, deep-link fallback, cache-control, CSP, source-map, API/client/build compatibility, and atomic pairing.
13. Exact `.env` shell content/creation authority, M01 bootstrap command/checkpoint, secret-key presence validation, and post-install login gate.
14. Exact PLAN-DB schema/migration target, quiescence, lock, first-empty exception, backup prerequisite, restricted start, downgrade/recovery semantics.
15. Exact M08 health/readiness/required-component/backup/restore receipts and deployment criticality policy.
16. Exact deployment journal/record formats, location, fsync, fencing, idempotency, crash recovery, retention, and safe disclosure.
17. Exact active-release/unit atomic activation, previous-release retention, stability checkpoint, and artifact cleanup rules.
18. Exact install/repair/upgrade/rollback/uninstall authority and owner checkpoints; confirm no purge-data action.
19. Exact canonical command paths/syntax/selectors/structured output/exit codes for AUTO-BUILD, AUTO-GIT-PREFLIGHT, and AUTO-DEPLOY.
20. Git repository identity/default branch/upstream/signing/tag/release policies; absent current Git repository remains Blocked.
21. Exact scanners/build tools/direct and transitive dependency licenses/provenance/locks/SBOM/notices policy.
22. Exact real test targets and authority for login cycle, crash, disk/permission, interrupted deploy, migration, rollback, restore, and uninstall.
23. Exact performance/resource/start/stop/maintenance/stability budgets from real measurements.
24. Whether installed-layout, readiness notification, release activation, or launcher decisions require a new ADR.

No implementation agent may silently select among alternatives that materially affect security, data recovery, portability, contract behavior, or release evidence.

### 13.3 Stop and escalation conditions

The section 10.2 stop list applies throughout delivery. Additionally stop on a real target when actual systemd/XDG/filesystem/Python behavior contradicts the approved compatibility record; when an installed unknown object overlaps a proposed target; when current deployment state cannot be classified; when backup/rollback capacity is insufficient; when owner login/session/provider work would be interrupted beyond the approved window; or when a secret/content finding occurs.

## 14. Delivery, compatibility, and rollback

### 14.1 Delivery order

1. Complete Linux M0/systemd/XDG/filesystem evidence needed by A04 and this plan.
2. Synchronize CTR-DEP-001, bundle, installed layout, config, readiness, DB/M08, P01/P02, and automation contracts.
3. Approve exact runtime/dependency/tool/license decisions and this plan.
4. Implement bundle validation/assembly and real `AUTO-BUILD` evidence.
5. Implement target preflight, journal, staging, activation, and A04 fixed-unit status.
6. Implement lifecycle plus first install against an isolated real XDG target, then owner-approved actual local install.
7. Integrate loopback API, static UI, M01 bootstrap, DB initialization, M08 readiness, and browser-independent collection.
8. Produce a second real release and implement/verify upgrade plus artifact-only rollback.
9. Exercise migration/backup/restore recovery and incompatible-schema rollback classes on approved isolated real data.
10. Implement repair/preserve-data uninstall/reinstall, Git/build/deploy automation, hardening, performance, documentation, and release evidence.

### 14.2 Compatibility

- A release declares supported platform/Python ABI, configuration contract, CTR-DEP major, schema readable/writable range, OpenAPI/client/frontend compatibility, and migration head.
- Installed configuration may evolve additively only when old binaries safely ignore new optional non-secret settings. Renames/meaning changes require migration/deprecation.
- Unit-template, journal, manifest, path-class, activation, authority, or rollback semantic changes require contract review and may require a new major/ADR.
- Older binary rollback is allowed only when current schema/config/artifacts fall within its declared compatible range.
- Provider versions are adapter compatibility, not deployment compatibility, unless the binary cannot start safely; degraded provider support remains visible.
- A systemd/Python/kernel/filesystem change moves affected deployment evidence to unverified until rerun.

### 14.3 Rollback and recovery

- Bundle/build failure: no target changes.
- Staging failure: active release/service/data unchanged; exact partial staging quarantined.
- Unit install failure before activation: restore prior unit generation and current reference; old service remains/restarts if compatible.
- Migration failure: PLAN-DB/M08 recovery; candidate stays inactive.
- Activation or readiness failure: use the precomputed rollback class, never improvise.
- DB restore rollback: owner-approved M08/DB flow with current preservation, M01 invalidation, restricted validation, and normal readiness.
- Failed rollback: preserve all relevant artifact/database generations, stop/restrict service, mark `recovery_required`, and provide an exact safe next action.
- Shared migration history, `.env`, provider profiles, and monitored agents are never modified as rollback techniques.

### 14.4 Post-deployment checks

- target user/XDG paths/owners/modes/types and current release reference are safe;
- bundle/member/build/backend/frontend/OpenAPI/client/unit/config/schema versions match;
- fixed unit is installed/enabled according to request and lingering is unchanged;
- actual socket is loopback-only and Host/Origin/CORS/proxy/docs policies pass;
- liveness/readiness/required components and database integrity/schema are accurate;
- real login/logout and generated-client browser smoke pass;
- scheduler/collectors continue when browser closes;
- newest required backup remains valid and recovery receipts are current;
- no unexpected crash loop, lock/journal, staging, unit, migration, or rollback state remains;
- bundles, installed files, logs, journal, DB artifacts, browser, and evidence pass secret/content/path scans;
- provider processes/profiles and unrelated units/files remain unchanged;
- every required T5/T7/macOS/provider/natural-condition row retains its truthful Passed/Failed/Blocked/Not Run status.

### 14.5 Implementation handoff packet

Every DEP handoff includes:

- exact requirement/AC, plan, CTR-DEP, bundle, unit, configuration, schema, API/client/frontend, and automation versions;
- all changed source/template/test/doc/shared files and their allocated owners;
- exact canonical Red, Green, and post-refactor commands/results/timestamps;
- real distribution/kernel/filesystem/systemd/Python/browser/build/bundle/schema environment;
- install/start/stop/restart/status/autostart/upgrade/rollback/uninstall results and every non-Passed scenario;
- owner acknowledgements for login cycle, service window, destructive isolated test, restore, and real target deployment;
- artifact/unit/config/database/API/UI compatibility diffs and rollback position;
- security/privacy `.env`/path/permission/bind/no-control/prohibited-data scans;
- dependency/license/lock/SBOM/notices/provenance impact;
- Git preflight state without claiming Git/GitLab actions occurred;
- documentation/runbook/traceability/risk changes and exact next integration step.

No handoff calls deployment ready unless its exact canonical completion selector passes on the real target and every required boundary is covered.

## 15. Definition of ready

- [ ] Owner approves non-root native layout, login autostart, lingering exclusion, local bind, install/upgrade/rollback/uninstall outcomes, and limitations.
- [ ] Root approves this exact plan/version and changes Status to Approved.
- [ ] Canonical synchronized planning gate includes PLAN-DEP and passes against the real checkout.
- [ ] Repository/installed/shared paths, unit/template, automation, generated artifacts, migration head, and implementation/reviewer owners are conflict-free.
- [ ] CTR-DEP-001 DTOs/ports/errors/authority/idempotency/compatibility are Approved by all consumers.
- [ ] Release bundle manifest/layout/build metadata/SBOM/notices contracts are Approved.
- [ ] Foundation runtime/build/config/log/lifecycle/evidence/automation contracts are Approved.
- [ ] CTR-PLAT-001 exact XDG/object/permission/fsync/atomic/systemd semantics are Approved from real Linux evidence.
- [ ] CTR-DB-001/003 and AUTO-MIGRATE schema/quiescence/activation/recovery semantics are Approved.
- [ ] CTR-OPS-001/002/003/006 backup/restore/readiness/required-component semantics are Approved.
- [ ] P01/P02 loopback/origin/host/port/static/deep-link/cache/CSP/version-smoke behavior is Approved.
- [ ] M01 first-install bootstrap and post-restore/upgrade authentication validation are Approved.
- [ ] Exact XDG layout, modes, launcher, immutable/mutable classes, previous-release retention, cleanup, and no-purge policy are Approved.
- [ ] Exact service type/unit/target/readiness/restart/limits/hardening/log/autostart/lingering decisions are Approved.
- [ ] Exact local port and configuration keys/defaults/ranges/restart/disclosure rules are registered.
- [ ] Exact Python/build/package/scanner/systemd dependency versions and all license/security/provenance/lock/SBOM/notices items pass admission.
- [ ] Canonical AUTO-BUILD, AUTO-GIT-PREFLIGHT, AUTO-DEPLOY, and first-increment TEST/QUALITY/DOCS selectors exist, are real-tested, and fail controlled negative cases.
- [ ] Current Git worktree state and Git policy are known; absent Git remains visible Blocked and is not initialized implicitly.
- [ ] Every test has a meaningful expected Red, correct real boundary, exact safe target/cleanup/evidence, and assigned owner.
- [ ] Real target Linux/XDG/systemd/filesystem/browser resources and owner login/service windows are available; unavailable prior releases/macOS/natural failures are preclassified truthfully.
- [ ] Destructive isolated packets for interruption, permission, disk, migration, activation, rollback, restore, and uninstall are explicitly approved.
- [ ] Security/privacy/no-control/no-remote-bind/`.env`/path/bundle/unit/secret review resolves every Critical risk.
- [ ] Performance/resource budgets and crash/start-limit/recovery policies are approved from real baselines.
- [ ] Required runbooks, command registry, evidence custody, traceability, risk, known limitations, and handoff outputs are assigned.
- [ ] Any required ADR is Accepted.
- [ ] No unresolved section 13.2 decision permits materially different implementation.

Until every applicable item is checked, PLAN-DEP is **Not Ready for implementation**.

## 16. Approval record

| Reviewer/owner | Decision | Conditions/evidence | Date | Approved versions |
|---|---|---|---|---|
| Pavlo Sidelov / product owner | Pending | native layout, lifecycle, lingering, recovery, uninstall, local-only limitations | — | — |
| Root/integration steward | Pending | contracts, paths, automation, ownership, planning gate | — | — |
| PLAN-FND/build/config owner | Pending | runtime, bundle inputs, locks, metadata, common commands | — | — |
| A04-LINUX owner | Pending | XDG/filesystem/systemd/fixed-unit/atomic behavior and T5 | — | — |
| PLAN-DB owner | Pending | schema compatibility, migration, activation, rollback | — | — |
| M08 operations owner | Pending | readiness, backup, restore, maintenance, health | — | — |
| M01 owner | Pending | bootstrap, configuration presence, login/invalidation | — | — |
| P01/P02 owners | Pending | local transport, static artifacts, generated client, browser smoke | — | — |
| Security/privacy reviewer | Pending | secrets, paths, permissions, unit, bind, no-control, uninstall | — | — |
| Test-integrity reviewer | Pending | real T5/T7/RGR, isolated destructive packets, statuses | — | — |
| Dependency/license reviewer | Pending | exact graph, tools, provenance, locks, SBOM/notices | — | — |
| Release/recovery reviewer | Pending | build/deploy/Git gates, upgrade/rollback/uninstall runbooks | — | — |

Approval authorizes only a later explicit implementation task packet. It does not authorize dependency installation, Git initialization/push, build publication, `.env` creation, database migration, service installation/action, lingering change, provider access, destructive testing, or deployment to the owner's workstation.
