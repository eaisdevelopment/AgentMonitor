# PLAN-FND: repository, tooling, composition, and verification foundation

- Status: **Draft — approval pending; implementation is not authorized**
- Plan version: 0.2.0-draft
- Primary owner: repository foundation/integration steward
- Reviewers: architecture, API, UI, persistence, security, test integrity, operations, deployment, and dependency/license owners
- Requirements: NFR-ARCH-001, NFR-ARCH-002, NFR-API-001, NFR-API-002, NFR-DATA-001, NFR-TEST-001, NFR-TEST-002, NFR-SEC-001, NFR-PRIV-001, NFR-PRIV-002, NFR-DOC-001, NFR-LIC-001, NFR-PLAT-001, NFR-PERF-001, NFR-RES-001, NFR-OBS-001, NFR-COMP-001; supporting FR-IAM-007, FR-OPS-001, FR-OPS-002, FR-OPS-005, FR-OPS-006, and FR-SAFE-002
- Acceptance criteria: supporting AC-V1-002, AC-V1-003, AC-V1-004, AC-V1-005, AC-V1-006, AC-V1-007, AC-V1-008, AC-OPS-001, AC-OPS-003, AC-TEST-001, AC-TEST-002, AC-TEST-003, and AC-TEST-006
- Proposed technical contract bundle: `foundation.contracts.v1` (**Proposed**, not approved)
- Dependencies: accepted ADRs 0001, 0002, 0003, 0004, 0007, 0008, 0010, and 0011; future approved PLAN-M01, PLAN-M08, PLAN-P01, PLAN-P02, PLAN-DB, and PLAN-DEP contracts
- Target milestone: M1 foundation, with gates used by every later milestone
- Approved by/date: pending

## CS-1 alignment addendum — contract baseline 0.2.0

This addendum is the normative interpretation of this Draft during CS-1. It
supersedes any older wording in this plan that implies joint semantic ownership,
an unallocated shared writer, or implementation authority. The governing
inventories are [contract-baseline.toml](../contract-baseline.toml) and
[parallel-ownership.toml](../parallel-ownership.toml); both remain Draft and
require producer/consumer review plus explicit owner approval.

- PLAN-FND is the sole semantic producer of `CTR-COMMON-001..003`,
  `CTR-COMMON-006..007`, `CTR-CONFIG-001`, and `CTR-FND-001..008`. Provider
  observation provenance (`CTR-COMMON-004`) remains M03-owned, and the HTTP
  problem contract (`CTR-COMMON-005`) remains P01-owned.
- PLAN-FND is the sole semantic producer of portable
  `CTR-PLAT-001 PortablePlatformPrimitivesV1`. A04-LINUX and A04-MAC implement
  that portable meaning; they do not publish divergent meanings under the same
  ID. Platform evidence may narrow a platform implementation without changing
  portable semantics privately.
- PLAN-FND produces the technical safety policies
  `CTR-BOUNDARY-001 SafeSubprocessExecutionV1` and
  `CTR-BOUNDARY-003 ApprovedRootAndFileReadV1`. M03 produces provider HTTP
  policy `CTR-BOUNDARY-002`; foundation does not own provider semantics.
- `CTR-COMMON-007 FieldAvailabilityV1` preserves exact zero separately from
  missing, null, unknown, unsupported, unavailable, not-applicable,
  withheld/denied, stale, and unresolved. Consumers may specialize allowed
  states but may not collapse them.
- `CTR-COMMON-006` defines the technical event envelope only. PLAN-INT governs
  durable delivery, outbox, consumer receipt/checkpoint, deduplication, and
  replay through `CTR-EVT-001`; domain producers retain event meaning.
- P01 owns API semantics and source schemas, PLAN-FND owns only the generator
  mechanism in `CTR-FND-005`, PLAN-INT is the sole generated-artifact writer in
  each allocated wave, and P02 consumes generated output only through its
  wrapper. No plan hand-edits OpenAPI or generated client output.
- `CTR-FND-001` freezes one producer-owned contract-package convention, the
  module-scoped SQLite path
  `backend/src/agentmonitor/adapters/persistence/<module>/sqlite/`, the provider
  extension namespace `contracts/providers/<provider>/<capability>/v1`, and
  the shared-writer allocations before parallel scaffolding.
- Foundation may be developed in isolated lanes for repository/import rules,
  common values, configuration, boundaries, application factory, logging,
  generation mechanics, migration metadata, build metadata, and evidence
  summaries only after their exact paths are allocated. Root manifests,
  lockfiles, CI, composition, migration metadata, command registry, OpenAPI,
  and generated output remain serial shared-writer work.

Every aligned contract remains proposed at `1.0.0`. This addendum records Draft
direction only: all external tests remain real-boundary tests, and no mock,
fake, recorded provider response, placeholder data, or unexecuted pass is
permitted.

## 0. Authority, interpretation, and planning constraints

This plan defines the repository mechanisms needed for independently owned modules to be built, checked, composed, and verified. It is not a business module, does not own provider or product behavior, and does not authorize production implementation while its status is Draft.

The foundation establishes paths, dependency direction, toolchain gates, reproducible environments, composition seams, generated-artifact flow, real-stack test harnesses, and CI evidence. It must remain intentionally thin. A foundation abstraction is justified only when at least one approved consumer needs it and its meaning is stable across those consumers.

This plan does **not** select exact Python, Node.js, dependency, image, scanner, formatter, generator, or browser versions. Every proposed third-party component remains **Candidate / Pending admission** until the dependency gate in section 12 is complete and the owner approves the resulting exact pins and lockfiles.

No command written in this plan is an operational command. The authoritative command registry is populated only after a command exists, has been run successfully in the stated environment, and has sanitized evidence. Until then, commands remain `TBD` in runbooks.

## 1. Outcome and boundaries

### 1.1 Outcome

After approved implementation, a developer or implementation agent can create a clean, pinned backend and frontend environment; run deterministic policy and static gates; apply a real Alembic chain to a real SQLite file; start the production FastAPI composition on an ephemeral loopback port; generate and validate OpenAPI; generate and compile the TypeScript client from that artifact; build and serve the real frontend shell; drive it in a real browser; and obtain truthful, sanitized evidence locally and in GitLab-hosted CI.

The foundation is successful only if later modules can be added without bypassing their published ports, editing another module's tables, hand-copying schemas, inventing telemetry, or sharing unowned mutable files.

### 1.2 In scope

- Repository topology, path ownership, import direction, and shared-file allocation.
- Selection gates for one supported Python baseline and one supported Node.js baseline.
- Reproducible backend/frontend development and build environments with committed lockfiles.
- Minimal FastAPI, React, TypeScript, Vite, OpenAPI, SQLAlchemy, Alembic, and SQLite scaffolding needed to prove composition, without product routes, module tables, business policies, or telemetry.
- One composition root and explicit application lifecycle hooks.
- Machine-enforced module/import boundaries.
- The OpenAPI-to-generated-client source-of-truth pipeline and generated-file ownership.
- Typed bootstrap configuration loading and `.env` shell policy, without allocating module-owned keys.
- Structured logging, correlation propagation, and redaction primitives.
- Real SQLite, real HTTP server, and real built-browser test harnesses.
- GitLab-hosted CI stages, evidence classifications, artifacts, and non-live gates.
- Dependency, vulnerability, secret, license, SBOM, notices, documentation, schema, and generated-drift gates.
- Native local application/service seams while leaving installation and service definitions to PLAN-DEP.
- Creation and governance of an authoritative command registry after commands are implemented and verified.

### 1.3 Out of scope

- Any account, organization, provider, quota, budget, collection, runtime, alert, authentication, backup, export, diagnostic, or retention business behavior.
- Public business endpoints, dashboard data, example accounts, seeded observations, placeholder metrics, or provider fixtures.
- Provider/platform discovery or access to provider profiles, credentials, local state, processes, or network APIs.
- Password hashing, sessions, CSRF, API-token behavior, or authorization rules, which belong to M01 and P01.
- Module repository implementations and module-owned tables/migrations, which require approved module plans and PLAN-DB synchronization.
- Operational health projections, backup/restore, retention, and diagnostic bundles, which belong to M08.
- UI information architecture, features, charts, state management, accessibility acceptance, and visual design, which belong to P02.
- Linux `systemd` units, macOS `launchd` definitions, installed filesystem paths, installers, upgrade scripts, and packages, which belong to PLAN-DEP/platform plans.
- GitLab project creation, runner installation, secret configuration, push, release, or external-resource mutation.
- Live-provider and workstation claims; CI must report those separately as Blocked or Not Run until their owning plans execute them.

### 1.4 Ownership and handoff matrix

| Concern/artifact | PLAN-FND owns | Explicit non-owner / handoff |
|---|---|---|
| Repository layout | Top-level shape, path map, ownership manifest, boundary rules | Each module owns content under its approved path |
| Backend bootstrap | Process/app factory mechanism and lifecycle composition | P01 owns route/middleware semantics; M01 owns authentication |
| Frontend bootstrap | Buildable empty application shell and generated-client integration seam | P02 owns features, layouts, state, and visual behavior |
| OpenAPI pipeline | Generation, validation, compatibility/diff mechanism, committed artifact location | P01 and module owners own schemas/operations |
| Generated client | Generator configuration, output location, reproducibility, drift check | P02 consumes through its API adapter; feature modules never edit generated output |
| SQLite/Alembic | Engine/session factory mechanism, Alembic environment, revision allocation policy, compatibility check mechanism | PLAN-DB owns repository adapters; modules own their tables and allocated revisions; M08 owns backup/restore |
| Configuration | Bootstrap loader, typed descriptor protocol, source/precedence enforcement, redaction | Each module owns its keys; M08 owns operator-facing validation/diagnostics |
| Logging/correlation | Technical event envelope, correlation context, sinks/rotation seam, redaction | Modules own event names and safe fields; M08 owns health/diagnostic projections |
| CI/tooling | Pipeline structure, deterministic gates, evidence summary, artifacts | Live-provider/platform owners supply separate evidence; GitLab settings remain owner-controlled |
| Native execution seam | Stable entrypoint and lifecycle/exit behavior | PLAN-DEP owns user service, installation paths, autostart, upgrade, and packaging |
| Shared technical primitives | Only approved, stable, domain-neutral primitives | No shared business helpers, DTOs, repositories, or provider logic |

### 1.5 Proposed repository topology

The topology is proposed for contract synchronization. Creating every empty directory is not required; paths appear when an approved owner implements content.

```text
/
  AGENTS.md
  README.md
  LICENSE
  .gitignore
  .gitlab-ci.yml                         # integration steward only
  backend/
    pyproject.toml                       # foundation/dependency steward
    <approved-python-lockfile>           # generated by selected resolver; never hand-edited
    migrations/
      alembic.ini
      env.py                             # PLAN-FND mechanism
      script.py.mako
      versions/                          # centrally allocated; each revision has one module owner
    src/agentmonitor/
      __init__.py
      contracts/                         # versioned cross-module contracts; producer-owned files
      foundation/                        # configuration/logging/correlation/lifecycle mechanisms
      composition/                       # only cross-module wiring location
      api/                               # P01-owned; PLAN-FND may create bootstrap seam only
      modules/                           # module-owned subdirectories
      adapters/
        persistence/                     # PLAN-DB and module repository adapter owners
        providers/                       # A01-A03 owners
        platform/                        # A04 platform owners
        notifications/                   # deferred adapter owners
    tests/
      foundation/                        # PLAN-FND tests
      integration/foundation/            # real DB/HTTP/composition evidence
  frontend/
    package.json                         # foundation/dependency steward until P02 handoff
    <approved-node-lockfile>             # generated by selected package manager; never hand-edited
    vite.config.*                        # PLAN-FND mechanism, then shared-file controlled
    tsconfig*.json                       # PLAN-FND mechanism, then shared-file controlled
    src/
      app/                               # P02 owns after skeleton handoff
      generated/api/                     # generator-owned; no manual edits
      shared/api/                        # P02-owned wrapper around generated client
      features/                          # feature owners only
    tests/foundation/
    tests/browser/foundation/
  contracts/
    openapi/
      agentmonitor-v1.json               # generated from running/backend source; no manual edits
  tooling/                               # small reviewed repository-owned validation wrappers only
  docs/
    engineering/commands.md              # created only after first verified command; integration steward
    plans/
    evidence/                            # sanitized policy/evidence manifests only when approved
  THIRD_PARTY_NOTICES.*                  # generated/reviewed release artifact
  sbom/                                  # generated release artifacts; retention/commit policy decided at admission
```

`tooling/` must not become a second application, hide business rules, or contain copied third-party code. A wrapper exists only when it adds AgentMonitor-specific policy or makes a verified command reproducible; direct tool configuration is preferred.

### 1.6 Allowed and forbidden paths/imports for foundation implementation

**Allowed implementation paths after approval**

- Root tool/version/CI metadata explicitly allocated to PLAN-FND.
- `backend/src/agentmonitor/foundation/**`.
- `backend/src/agentmonitor/composition/**`.
- The minimum bootstrap seam under `backend/src/agentmonitor/api/**`, jointly reviewed by P01 and containing no route business behavior.
- Alembic environment/configuration but no module tables.
- `backend/tests/foundation/**` and `backend/tests/integration/foundation/**`.
- Frontend build/type/generation configuration, empty app shell, and foundation tests until formal P02 handoff.
- `docs/modules/foundation.md` as the nonshared foundation module reference.
- `contracts/openapi/**` only through the approved generator.
- Approved validation wrappers/configuration and foundation-owned documentation.

**Forbidden without a separately synchronized plan**

- `backend/src/agentmonitor/modules/**` business code or tests.
- Provider, platform, notification, or module persistence implementations.
- Module-owned migration DDL, schema fields, repositories, events, API DTOs, or feature UI.
- System service definitions, installers, release packages, or installed-path decisions.
- Any `.env` with values, provider state path, secret, credential, account identifier, telemetry sample, or content artifact.
- Manual edits to generated OpenAPI, generated client, lockfiles, SBOMs, or notices.
- GitLab project/runners/variables or external systems.

**Allowed dependency direction**

```text
composition -> api/scheduler/adapters -> application ports/use cases -> domain/contracts
frontend features -> shared API adapter -> generated client -> public OpenAPI contract
Alembic/persistence adapters -> module repository ports (never the reverse)
```

Domain modules must not import `agentmonitor.foundation`, `composition`, FastAPI, Pydantic transport models, SQLAlchemy, Alembic, SQLite drivers, provider packages, OS APIs, or frontend code. `foundation` must not import module internals. Composition may import public factories/ports from approved modules and adapters, but modules never import composition. No package may deep-import another module's private path.

## 2. Requirements and traceability

The foundation provides supporting evidence; it cannot alone pass a release-wide criterion owned by the integrated product.

| Requirement/AC | Planned foundation behavior | Proposed contract/evidence | Test/scenario IDs | Evidence gate |
|---|---|---|---|---|
| NFR-ARCH-001 | Enforce one-way module imports and prohibit cycles/private deep imports | `repository-layout.v1`, boundary policy | FND-BND-001, FND-BND-002 | Static gate on real source plus reviewed path manifest |
| NFR-ARCH-002 | Reserve producer-owned contract packages and table/migration ownership metadata | `ownership-manifest.v1` | FND-BND-003, FND-MIG-003 | Every owned path/contract/revision has one owner |
| NFR-API-001 | Provide FastAPI composition seam and `/api/v1` router mount point without product operations | `application-factory.v1` | FND-HTTP-001, FND-OAPI-001 | Real server and generated OpenAPI mechanism |
| NFR-API-002 | Generate committed OpenAPI then TypeScript client; block drift/manual edits | `openapi-artifact.v1`, `generated-client.v1` | FND-OAPI-001..003, FND-CLIENT-001..002 | Validation, compatibility classification, strict compile |
| NFR-DATA-001 | Establish real file-backed SQLite and Alembic mechanism with portability checks | `migration-metadata.v1` | FND-DB-001..004 | Fresh migration, schema compatibility, real transactions |
| NFR-TEST-001 | Make Red/Green/refactor evidence and truthful statuses first-class | `test-evidence-summary.v1` | FND-EVID-001, all behavioral tests | Evidence schema/gate, no setup failure counted as Red |
| NFR-TEST-002 | Prohibit doubles, recordings, seeded telemetry, and placeholder UI data | Test policy scan/review | FND-TEST-001, FND-UI-002 | Repository review and real-stack execution |
| NFR-SEC-001 | Add least-privilege configuration, redaction, scans, safe build/CI policy | `bootstrap-configuration.v1`, `safe-log-event.v1` | FND-CFG-001..004, FND-LOG-001..003, FND-SEC-001..003 | Real config/process/log/artifact evidence |
| NFR-PRIV-001 | Foundation stores no operational/provider content and creates no sample telemetry path | Ownership/data inventory | FND-PRIV-001, FND-UI-002 | Source/artifact inspection |
| NFR-PRIV-002 | No analytics/crash-reporting package, endpoint, or outbound build/runtime call | Dependency/network inventory | FND-PRIV-002 | Dependency and built-artifact review |
| NFR-DOC-001 | Validate docs/links/IDs/statuses and establish verified command registry process | Documentation gate | FND-DOC-001..003 | Real repository documentation checks |
| NFR-LIC-001 | Gate dependency admission, lockfiles, SBOM, notices, and license/vulnerability scans | Admission records and release inventory | FND-DEP-001..004 | Direct/transitive review and real locked graph scan |
| NFR-PLAT-001 | Keep core/bootstrap portable and expose platform/service ports without Linux imports | Platform-neutral entry/lifecycle seam | FND-PLAT-001, FND-PLAT-002 | Real Linux pass; real macOS is separately Passed or Blocked |
| NFR-PERF-001 | Ensure tooling/composition does not impose redesign; create later measurable load-harness seam | Startup/build/query baseline, no provider claims | FND-PERF-001 | Measured foundation overhead; business load deferred |
| NFR-RES-001 | Supervise lifecycle tasks and isolate bootstrap failures by typed outcomes | Lifecycle contract | FND-LIFE-001..003 | Real task/process failure behavior without provider simulation |
| NFR-OBS-001 | Structured local logs, correlation propagation, bounded/redacted records | `correlation-context.v1`, `safe-log-event.v1` | FND-LOG-001..004 | Real HTTP/process/log inspection |
| NFR-COMP-001 | Version and diff API/schema/generated/migration contracts | Contract gate | FND-OAPI-002, FND-DB-002, FND-MIG-003, FND-BND-003 | Compatibility report blocks unapproved breakage |
| FR-IAM-007 | Make loopback the only permitted local bootstrap bind and reserve strict host/origin hook | Deployment bootstrap policy; final semantics P01/M01 | FND-HTTP-001, FND-HTTP-002 | Real socket/request checks; cannot claim complete IAM |
| FR-OPS-001 | Provide long-lived process/lifecycle entry seam independent of browser | Application lifecycle seam; service owned by PLAN-DEP | FND-LIFE-001, FND-UI-001 | Service/autostart remains AC-OPS-001 work |
| FR-OPS-002/006 | Expose version/build/schema inputs to future M08 projection | `build-metadata.v1` | FND-META-001 | Values available through port, no health route claimed |
| FR-OPS-005 | Exclude secrets from foundation artifacts/logs/config diagnostics | Redaction/artifact policy | FND-LOG-002, FND-SEC-002, FND-PRIV-001 | Sanitized scan results |
| FR-SAFE-002 | Foundation exposes no process-control, credential-switching, or agent-routing port | Dependency/API absence review | FND-SAFE-001 | Public/schema/source review |
| AC-V1-002 | Supply planning/contract/boundary mechanisms | This approved plan plus later module plans | FND-BND-003 | Supporting only; every module must still be approved |
| AC-V1-003 | Validate OpenAPI, generated client, and compatible drift | Generated artifact pipeline | FND-OAPI-001..003, FND-CLIENT-001..002 | Integrated API/client gate |
| AC-V1-004 | Apply real Alembic chain from empty and supported schemas | Migration mechanism | FND-DB-001..004 | Supporting only; later module revisions expand matrix |
| AC-V1-005/007 | Run security/license/secret gates on real repo/build artifacts | CI policy | FND-SEC-001..003, FND-DEP-001..004 | No unresolved foundation finding; release remains integrated gate |
| AC-V1-006 | Validate maintained developer/command documentation | Documentation gate | FND-DOC-001..003 | Supporting only |
| AC-V1-008 | Empty shell and tests never claim invented telemetry | No telemetry/demo path | FND-TEST-001, FND-UI-002 | Source and browser review |
| AC-OPS-001/003 | Provide native lifecycle/failure-isolation seams | Lifecycle composition | FND-LIFE-001..003 | Supporting only; real service/provider isolation belongs later plans |
| AC-TEST-001/002/003/006 | Enable R/G/R evidence, prohibited-pattern gate, real DB/HTTP/browser suites, explicit statuses | Test/evidence contracts | FND-EVID-001, FND-TEST-001, FND-DB-001, FND-HTTP-001, FND-UI-001, FND-CI-002 | Required in every later pipeline/handoff |

### 2.1 Approved interpretation limits

- A successful foundation HTTP/browser test proves the production composition and delivery mechanism, not any business endpoint, authentication, or provider workflow.
- A successful empty Alembic migration proves the migration mechanism, not module schema correctness, upgrade safety, backup, or PostgreSQL compatibility.
- A clean hosted CI pipeline proves deterministic/local-stack gates only. T5 workstation and T6 provider evidence remain visibly separate.
- Structural examples used in OpenAPI documentation cannot be labeled or rendered as observed provider/account data.
- No requirement is weakened to accommodate unavailable tooling; unresolved selection is a planning blocker, not permission to skip a gate.

## 3. Foundation design

### 3.1 Runtime version-selection gates

Python and Node.js baselines are chosen independently, recorded, and pinned only after this sequence:

1. Inventory the supported/security-maintained upstream release lines on the decision date.
2. Check every admitted direct dependency's declared runtime range and known incompatibilities.
3. Confirm availability on the target Linux distribution, real macOS environment when available, GitLab-hosted runner images, and selected local version manager/package tool.
4. Confirm native wheels/binaries are not required unexpectedly or document their supply-chain/platform consequences.
5. Run a clean resolve/build/test on Linux using the candidate runtime.
6. Run the portable foundation tests on real macOS, or record them as Blocked without claiming support evidence.
7. Approve one exact runtime baseline and a documented compatibility range. Commit the selected version files in the same reviewed change as lockfiles.
8. Make local preflight and CI fail clearly on an unsupported runtime; do not silently continue.

The selection record includes decision date, security-support horizon, exact runtime/build-tool versions, supported platforms, dependency resolution evidence, upgrade trigger, and owner approval. No exact version in an implementation task is valid unless that record is Approved.

### 3.2 Reproducible environments and lockfiles

The dependency review must select exactly one Python environment/resolver workflow and one Node package-manager workflow. Competing lock formats are not committed.

- Backend application and development groups are explicit; runtime packages do not inherit test/scanner packages.
- Frontend production and development dependencies are explicit.
- Direct constraints are intentional; all transitive versions are locked.
- CI uses frozen/immutable lock resolution and fails on manifest-lock mismatch.
- Lockfiles are generator-owned, committed, reviewed as code, and regenerated only by the selected verified command.
- Package acquisition uses canonical registries and TLS verification. Git branch/path dependencies and unreviewed forks are prohibited.
- Integrity hashes/signatures are enforced where the selected ecosystem supports them.
- Clean-environment verification begins without developer caches. CI caches are optimization only, keyed from runtime and lockfile identity, contain no secrets, and can be deleted without changing results.
- Build inputs include runtime versions, lockfiles, generator versions, environment classification, and source revision. Rebuilding the same source must produce functionally equivalent artifacts; known nondeterministic metadata is identified and bounded.
- Local test configuration is isolated and cannot read the operator's `.env` or production data paths.

### 3.3 Backend/API skeleton boundaries

The FastAPI skeleton contains only:

- an application factory accepting validated bootstrap configuration and approved component factories;
- lifecycle startup/shutdown registration;
- an empty `/api/v1` router mount point for P01;
- correlation/error/redaction middleware seams jointly reviewed with P01;
- static frontend mounting seam decided with P01/P02/DEP;
- OpenAPI generation hooks; and
- version/build metadata input for future M08 projections.

It contains no business routes, repositories, background collectors, implicit DDL, password/session behavior, provider calls, data examples, or global import-time side effects. Swagger/ReDoc must not be exposed unauthenticated in installed mode. Before M01/P01 exist, production-mode docs are disabled; generation occurs through the controlled build path. P01/M01 later own authenticated documentation behavior.

The actual server is started by an approved ASGI server selected through dependency admission. Development reload behavior is never enabled in installed mode. Bind host, port, worker/task model, graceful-shutdown deadline, and trusted-host/origin semantics are not silently defaulted; exact settings are allocated during P01/DEP synchronization.

### 3.4 Frontend skeleton boundaries

The React/TypeScript/Vite skeleton proves that:

- strict TypeScript builds;
- production assets are generated without secrets;
- the shell is served same-origin by the real backend delivery path;
- a real browser can load it at defined baseline viewports;
- the shared API adapter can accept the generated client; and
- no direct `fetch`, duplicated backend DTO, sample account, placeholder metric, chart, or feature behavior is introduced.

The skeleton may render only static product-shell text and explicit states such as “No feature modules installed” if approved by P02. That statement is application state, not telemetry. It must never resemble an account/usage dashboard or be used as evidence for FR-UI requirements.

### 3.5 OpenAPI and generated-client source of truth

The authoritative direction is:

```text
typed FastAPI route/schema source
  -> generated OpenAPI document
  -> validation + compatibility classification
  -> committed contracts/openapi/agentmonitor-v1.json
  -> generated TypeScript client
  -> strict TypeScript compile + real HTTP/browser consumers
```

Rules:

- The OpenAPI artifact is generated from the production application composition, not maintained by hand.
- The committed document is the sole client-generation input and is stable/canonicalized to avoid meaningless order drift.
- The TypeScript generator and configuration are pinned and admitted dependencies.
- Generated output carries a source hash/schema version where the generator supports it and is never manually patched.
- CI regenerates OpenAPI and client in a clean worktree context and fails on drift.
- Compatibility tooling classifies a diff; an unapproved breaking change fails even when regeneration succeeds.
- Unique `operationId`, security declaration, response model, problem details, unit/nullability/provenance descriptions, and status-code completeness become P01/module gates as routes are added.
- Feature modules import the generated client only through the P02-owned shared API adapter.
- Client/server integration uses a real running server as soon as P01 publishes the first approved operation. Generated-type compilation alone is not evidence that an API operation works, and foundation must not invent an endpoint merely to make that integration test pass.

P01 owns OpenAPI semantics and source schemas. PLAN-FND owns the deterministic
generator mechanism. PLAN-INT is the sole writer of the generated OpenAPI and
TypeScript client artifacts for an allocated wave, while P02 owns only the
generated-client wrapper and consumption. Consumers never edit generated
artifacts to resolve drift.

### 3.6 SQLite and Alembic foundation

The foundation owns the mechanism, not application data:

- one reviewed SQLAlchemy engine/session/unit-of-work infrastructure seam;
- one Alembic environment and monotonic revision chain;
- a real file-backed temporary SQLite database path for tests;
- foreign-key enablement and explicit, reviewed journal/synchronous configuration;
- schema compatibility checks before writable startup;
- no implicit `create_all` in installed or integration operation;
- transaction lifecycle and connection cleanup primitives; and
- PostgreSQL portability review hooks for types/SQL/transaction assumptions.

The initial chain may contain a metadata-only/no-op base revision if Alembic requires an anchor. It may create only tool-owned revision metadata such as Alembic's own version marker. It must not invent organizations, users, providers, observations, outbox, settings, health, audit, or any other module table.

Every later revision allocation records revision ID, parent/head, owning module, requirement/plan, tables affected, portability notes, backup prerequisite, validation, downgrade/recovery policy, and assigned implementation wave. A single integration steward serializes shared-head changes. Parallel agents must not create competing heads unless an explicit reviewed merge-revision strategy is approved.

`alembic_version` is tool-owned metadata. Each business table and its DDL remain owned by exactly one approved module. Cross-module foreign keys require a separate ADR. PLAN-DB supplies production repository implementations only after module repository ports exist.

### 3.7 Composition root and lifecycle

The composition root is the only location allowed to know concrete adapter implementations and wire them to module ports. It must:

- construct dependencies explicitly; no hidden service locator or mutable global container;
- distinguish process bootstrap failures from degraded optional components;
- establish a root correlation/startup context;
- run explicit schema/config compatibility preflight before accepting writable traffic;
- start supervised tasks only after prerequisites are ready;
- cancel/drain owned tasks within a bounded shutdown deadline;
- close HTTP/database/log resources deterministically;
- expose typed component startup/shutdown outcomes to future M08 health projection; and
- keep API request handlers from executing long provider work directly.

No module may import composition or discover dependencies by scanning/importing arbitrary plugins. Provider adapter registration requires M03 contracts and is not implemented by PLAN-FND.

### 3.8 Import-boundary enforcement

Boundary rules combine a machine-readable ownership/import policy with static dependency analysis:

- domain packages may depend only on the standard library and their own domain/public contract packages as approved;
- modules may import other modules only through the exact published contract path/range;
- adapters may depend inward on published ports/contracts, never module private implementations;
- API maps transport to application contracts and cannot import ORM tables/repositories;
- composition may wire public factories/ports but contains no business logic;
- provider adapters cannot import each other;
- frontend features cannot import backend files, generated internals outside the shared adapter, or another feature's private state;
- cycles, deep/private imports, undeclared cross-owner edges, and generic `utils` escape hatches fail the gate.

The checker runs against the real repository source. Its initial efficacy evidence uses a controlled Red revision containing one explicit forbidden import in an assigned foundation test package, records the expected violation, and removes that import for Green. It does not use a mock module, fake provider, or simulated product boundary. The review must ensure the final repository contains no deliberate violation or test-only production path.

### 3.9 Typed configuration and `.env` shell policy

Foundation implements only bootstrap configuration mechanics and a registry schema. Each exact key requires one owner and an approved consuming plan.

The registry record fields are: external name, internal name, owner, type/unit/range, required/optional status, safe default, secret class, sources/precedence, reload/restart behavior, first/deprecated/removed version, operational/security consequences, and test/documentation IDs.

Rules:

- External application variables follow `AGENTMONITOR_<OWNER>_<SETTING>`.
- Precedence follows the configuration standard and is deterministic.
- Unknown, malformed, conflicting, or missing security-critical settings fail closed with a safe setting name/reason and no value.
- Secrets are represented only as opaque secret values; serialization, repr, logs, API/OpenAPI, diagnostics, and exception output cannot disclose them.
- Secret presence can be reported only as `configured` or `missing`.
- `.env` is loaded only from an explicitly resolved approved path, once at startup; global process environment is not mutated.
- Tests use owner-permission temporary `.env` files and isolated data directories; they never read the operator's `.env`.
- `.env.example` is created only after keys are approved. It contains names/comments and safe non-secret structural examples, never realistic secrets, emails, IDs, or copied provider paths.
- The service never creates values, prints values, or rewrites `.env`. PLAN-DEP may later create an empty protected shell with owner approval.
- Provider-standard variables are adapter-owned and never passed through the foundation except by an approved minimal environment builder.
- GitLab/development tokens are not runtime configuration and cannot be loaded by the service.

The initial key allocation is a contract-synchronization output of P01, M01, M08, PLAN-DB, and PLAN-DEP. This plan deliberately reserves categories rather than inventing final names.

### 3.10 Logging, correlation, and redaction primitives

Foundation provides a structured local event interface with these mandatory fields: UTC timestamp, severity, component/module, stable event name, application/component version, correlation ID, and safe outcome classification. Optional subject IDs use opaque internal IDs only.

- Correlation IDs are generated with cryptographic randomness or accepted only after length/character validation; an untrusted value cannot inject logs or become an unlimited-cardinality payload.
- Request, job, event, and background-task causality can be related without copying provider payloads.
- Redaction is allowlist-first: callers submit typed safe fields, not arbitrary object dictionaries.
- No raw exception arguments, request/response bodies, SQL parameter values, CLI/provider output, `.env`, headers, cookies, process environment, prompts, responses, tools, source, account emails, or filesystem dumps are logged.
- Boundary handlers preserve exception type/cause locally only when safe and map it to a stable sanitized code.
- Log output is local; no analytics, crash uploader, remote sink, or implicit network handler exists.
- Rotation/retention/file paths are supplied by M08/DEP-approved configuration. Foundation does not claim the operational policy.
- Tests inspect the real configured sink and process output. Random test-only canaries may prove non-disclosure, but are never provider credentials or labeled as real secrets.

### 3.11 GitLab-hosted CI design

The proposed pipeline runs on GitLab-hosted runners and has no provider credentials, operator `.env`, local profile directories, or workstation process access.

| Stage | Purpose and blocking gates | Principal artifacts |
|---|---|---|
| `policy` | Manifest/lock consistency, path ownership, prohibited files/patterns, documentation structure, copyright | Sanitized policy summary |
| `secrets` | Repository/history range and build-input secret scan using admitted scanner | Sanitized finding summary; never secret value |
| `backend-static` | Format/lint, strict types, import boundaries, security static analysis | Tool reports and versions |
| `frontend-static` | Format/lint, strict TypeScript, dependency/import boundaries | Tool reports and versions |
| `backend-test` | T1 pure and foundation tests; T2 uses a real SQLite file/migrations | JUnit/coverage diagnostics without data |
| `frontend-test` | Approved pure UI/build-tool tests; no telemetry claims | JUnit/coverage diagnostics |
| `contracts` | Start/generate/validate/diff OpenAPI, generate client, drift/strict-compile gate | OpenAPI diff and generation provenance |
| `real-stack` | Real server over loopback, real SQLite, production frontend build, real browser | Sanitized T2/T3/T4 reports/screenshots only when reviewed safe |
| `supply-chain` | Locked dependency vulnerability/license/provenance scans, SBOM, notices verification | SBOM, notices, scan summary |
| `build` | Reproducible backend/frontend/package inputs; no release/publish | Checksums and build metadata |
| `evidence` | Aggregate Passed/Failed/Blocked/Not Run without hiding T5/T6 | Release-evidence summary |

Stage names are provisional until CI configuration is implemented and verified. The pipeline must:

- use pinned runner images/tools by immutable version/digest where supported;
- install only from committed locks in frozen mode;
- use least-privilege job tokens and no protected provider/live variables;
- prevent fork/untrusted pipelines from accessing protected release credentials;
- avoid privileged containers and Docker-in-Docker unless separately approved;
- key caches by runtime plus lockfile identity and exclude credentials/reports with sensitive data;
- set bounded job timeouts and artifact retention;
- fail on security/license/secret/generated/contract/boundary findings according to approved severity policy;
- never auto-retry a failing test into a pass;
- publish each live-provider/platform scenario as `Blocked` or `Not Run` when not executed, not as a green aggregate;
- not push, publish, deploy, create releases, or mutate GitLab configuration without a separate approved release plan.

Local validation precedes any contact with GitLab. A GitLab-hosted run is required before the CI contract is considered Passed; a local CI syntax tool alone is insufficient.

### 3.12 Native development and service seams

Foundation supplies a platform-neutral executable/application entry seam with explicit configuration input, preflight, run, graceful shutdown, and stable sanitized exit classifications. It does not decide installed locations or service-manager syntax.

PLAN-DEP/platform owners later provide:

- XDG and macOS path resolution;
- `systemd --user`/`launchd` definitions;
- auto-start, restart/backoff, resource limits, logs, lingering choice, install/upgrade/uninstall;
- artifact placement and executable invocation; and
- real platform/service evidence.

Core imports no `systemd`, `/proc`, Linux path, or launchd library. Linux-specific test success cannot be relabeled macOS success. Browser closure is naturally separated from the service process; the browser never owns the scheduler or database lifecycle.

### 3.13 Verified command registry

After the first command is implemented and successfully executed, the integration steward creates the registry described in section 1.5. Each entry records:

- stable command ID and intent;
- exact executable/tool version and working directory;
- prerequisites and supported platform;
- authoritative arguments and safe environment/config inputs;
- side effects, files changed, network use, and secret exposure classification;
- expected success/failure outcomes and cleanup;
- verification date, evidence ID, and reviewer;
- replacement/deprecation history.

A command is not added from a package's presumed convention. Planned commands remain `TBD`; runbooks link only to verified entries. Help output alone is insufficient for a command that claims build, migration, service, backup, or test behavior.

## 4. Proposed technical contracts

All contracts below are **Proposed** and must be synchronized with consumers before approval. They are technical contracts, not new business capabilities.

The exact contract-baseline projection is:

| Contract ID | Baseline name | Detailed definition | Version / current maturity |
|---|---|---|---|
| CTR-FND-001 | `RepositoryLayoutAndOwnershipManifestV1` | sections 1.4–1.6 and 10.1 | 1.0.0 / `proposed_aligned` |
| CTR-FND-002 | `ApplicationFactoryV1` | section 4.1 | 1.0.0 / `proposed_aligned` |
| CTR-FND-003 | `BootstrapConfigurationV1` | section 4.2 | 1.0.0 / `proposed_aligned` |
| CTR-FND-004 | `CorrelationContextAndSafeLogEventV1` | section 4.3 | 1.0.0 / `proposed_aligned` |
| CTR-FND-005 | `OpenApiArtifactAndGeneratedClientPipelineV1` | section 4.4 | 1.0.0 / `proposed_aligned` |
| CTR-FND-006 | `MigrationMetadataV1` | section 4.5 | 1.0.0 / `proposed_aligned` |
| CTR-FND-007 | `BuildMetadataV1` | section 4.6 | 1.0.0 / `proposed_aligned` |
| CTR-FND-008 | `TestEvidenceSummaryV1` | section 4.7 | 1.0.0 / `proposed_aligned` |

The machine-exact producer and consumer sets are bound in
`contract-adoption.toml`; this table is the human-readable projection and
does not grant approval.

### 4.1 `application-factory.v1`

- **Owner:** PLAN-FND; consumers P01, PLAN-DEP, tests.
- **Input:** validated bootstrap settings, approved component factory set, build metadata, lifecycle hooks.
- **Output:** production ASGI application instance with no hidden external side effects during import.
- **Preconditions:** configuration schema compatible; dependencies already constructed or expressed as factories.
- **Postconditions:** lifecycle is deterministic; `/api/v1` router mount exists; no module route is invented.
- **Errors:** typed bootstrap/configuration/composition failures with sanitized codes.
- **Compatibility:** additive hook fields only within v1; lifecycle meaning changes require new major.

### 4.2 `bootstrap-configuration.v1`

- **Owner:** PLAN-FND mechanism; every key owned by its module/adapter/DEP plan.
- **Input:** explicit configuration path, process environment snapshot limited to allowlisted AgentMonitor names, non-secret CLI options where approved.
- **Output:** immutable typed settings grouped by owner plus source metadata for non-secret fields.
- **Errors:** missing, malformed, unknown-critical, permission-unsafe, conflicting, and unsupported-version outcomes.
- **Security:** secret values cannot serialize; no global environment mutation; operator `.env` never used in tests.
- **Compatibility:** key additions/renames/removals follow configuration versioning and owner approval.

### 4.3 `correlation-context.v1` and `safe-log-event.v1`

- **Owner:** PLAN-FND; consumers all boundaries/modules through a minimal stable interface.
- **Input:** validated or generated correlation/causation IDs and typed allowlisted fields.
- **Output:** immutable context and structured local record.
- **Errors:** invalid external correlation input is rejected/replaced according to P01 policy and never echoed unsafely.
- **Security:** arbitrary objects/payloads cannot be passed; remote sinks absent.
- **Compatibility:** mandatory field meaning cannot change within v1.

### 4.4 `openapi-artifact.v1` and `generated-client.v1`

- **Owner:** API/integration steward; producer P01/modules; consumer P02/other API clients.
- **Input:** production route/schema source and approved generator configuration.
- **Output:** canonical OpenAPI 3.x document and generator-owned strict TypeScript client.
- **Postconditions:** source hash/tool version captured; no handwritten schema fork; compatibility status emitted.
- **Errors:** validation, unstable generation, breaking drift, duplicate operation ID, and client compile failure.
- **Compatibility:** follows `/api/v1` and contract-versioning policy.

### 4.5 `migration-metadata.v1`

- **Owner:** migration integration steward; each revision has one module owner.
- **Fields:** revision/parent, module/plan/requirements, schema compatibility range, tables, portability, locks/downtime, data volume, backup prerequisite, validation, downgrade/recovery, reviewer.
- **Errors:** missing/duplicate owner, competing head, unapproved cross-module DDL, unsupported schema.
- **Compatibility:** metadata additions are compatible; revision history is immutable after shared use.

### 4.6 `build-metadata.v1`

- **Owner:** PLAN-FND; consumers M08, P01/P02 version mismatch display, release tooling.
- **Fields:** application version, source revision when safely available, build timestamp policy, schema compatibility range, frontend/OpenAPI/client artifact hashes, runtime/component versions.
- **Privacy:** no username, host path, environment dump, branch token, CI secret, or provider data.
- **Compatibility:** additive fields allowed; identifier meaning is stable.

### 4.7 `test-evidence-summary.v1`

- **Owner:** test/integration steward; consumers every handoff and release gate.
- **Fields:** test ID, requirement/AC, boundary class, command-registry ID, environment/runtime versions, Red/Green/refactor result references, Passed/Failed/Blocked/Not Run, sanitization review, timestamp, reviewer/live-owner counter-signature where applicable.
- **Rules:** no raw command/provider output or secrets; an aggregate cannot convert Blocked/Not Run to Passed.

### 4.8 Contract-impact assessment

This plan proposes new technical contracts and paths but changes no accepted public REST, module event, provider protocol, or business database contract. Approval requires consumers to accept ownership and dependency direction. Any decision to place business meaning in foundation, expose unauthenticated public routes, create module tables, or change accepted architecture requires plan revision and potentially a new ADR.

## 5. Data and persistence

### 5.1 Owned persistence

PLAN-FND owns no business table and no operational history. The only database object it may introduce is migration-tool metadata required by the approved Alembic chain. Build/test evidence belongs in CI/local evidence records, not application database tables.

### 5.2 Real database behavior

- T2 tests use a unique real temporary directory and file-backed SQLite database, never `:memory:` for file/WAL/migration/backup claims.
- Tests apply the production Alembic chain through the real command/API entry and then use production SQLAlchemy connection/session configuration.
- Foreign keys and selected journal/synchronous settings are asserted from the real connection.
- Startup recognizes empty, supported, older-supported, newer-than-supported, locked, read-only/permission-failed, and invalid database conditions distinctly.
- A newer schema prevents writable startup.
- Older schemas are upgraded only by explicit migration operation; application startup performs no hidden DDL.
- Connection lifetimes and transactions are bounded and closed on shutdown/failure.
- SQLite-specific pragmas/types/queries remain inside the persistence adapter and are recorded for PostgreSQL portability review.

### 5.3 Migration/shared-file ownership

- Alembic environment/templates: PLAN-FND owner; changes require PLAN-DB and integration review after handoff.
- Revision directory ordering/head: migration integration steward.
- Individual revision content: exactly one approved module owner.
- Multiple module migrations in one revision are prohibited unless a synchronized cross-module migration plan explicitly approves it.
- Generated schema diagrams, if introduced, are generator-owned and cannot become migration authority.
- Destructive downgrade is never implied. Unsafe rollback uses a verified backup plus compatible prior binary per the owning migration plan.

### 5.4 Retention, backup, and restore

No foundation-specific application data requires retention. M08/PLAN-DEP own backup and restore. Foundation must make the database path and lifecycle available through an approved port, avoid holding connections across shutdown, and preserve compatibility metadata needed by backup/restore checks. A migration test does not count as AC-OPS-004 backup evidence.

## 6. External and platform boundaries

| Boundary | Foundation behavior | Safety/failure behavior | Real verification |
|---|---|---|---|
| Package registries | Resolve only admitted locked packages during controlled install | TLS on; canonical registry; fail on lock/integrity mismatch; no fallback fork | Clean Linux resolve; macOS when available |
| GitLab hosted runner | Run deterministic/local-stack pipeline only | No provider secrets/profile/data; bounded artifact/caches; no deployment | Actual hosted pipeline, otherwise Not Run |
| Loopback socket | Start production server on ephemeral loopback for T3/T4 | Never non-loopback in local mode; bounded startup/shutdown | Real socket and HTTP client/browser |
| Filesystem config/data | Use explicit isolated roots and owner permissions | Resolve paths; avoid symlink/permission surprises; never scan provider/default paths | Real temporary filesystem; installed paths deferred |
| SQLite file | Use real file, production driver/engine, Alembic | Typed locked/permission/schema/integrity outcomes | Real file and migration chain |
| Browser | Drive production build through real supported browser | No localStorage bearer token, sample telemetry, external analytics | Playwright with installed real engine after admission |
| OS signals/process lifecycle | Bounded startup/shutdown for AgentMonitor itself only | Never signal provider agents; no root; stable safe exit | Real AgentMonitor child process on Linux |
| macOS | Keep imports/seams portable | No simulated macOS result | Real macOS execution or Blocked |

No provider/API account boundary is exercised by PLAN-FND. Network isolation tests must allow only the loopback/build registry traffic explicitly needed for their scope and must not claim provider behavior.

## 7. Security and privacy

### 7.1 Trust-boundary controls

- Application import and build steps must have no provider/profile side effects.
- Local service defaults to loopback; P01/M01 later add authenticated/authorized routes and strict host/origin/CSRF behavior.
- Before IAM exists, there is no production-exposed Swagger/ReDoc or mutating route.
- The frontend bundle contains only public build metadata and cannot embed `.env`, tokens, local paths, CI variables, or source maps contrary to release policy.
- Tooling and CI execute least privilege, without root/privileged runner access or workstation profile mounts.
- Dependencies with install scripts, binary components, telemetry, or outbound behavior require explicit review.
- Exceptions and validation errors expose stable safe codes and correlation IDs, not raw values or stack traces over HTTP.
- The foundation cannot read arbitrary process environments. Configuration receives only the explicit allowlist needed at bootstrap.

### 7.2 Secret controls

- Never create or inspect the owner's `.env` during foundation planning/testing.
- Integration tests generate ephemeral non-provider canary values within isolated config files only to test non-disclosure; reports record only whether the canary was absent.
- `.env`, provider profiles, database files, logs, browser storage, screenshots, caches, and local paths are excluded from CI upload by default.
- Secret scans run before artifact publication and again over the artifact set.
- Scanner output is sanitized so a detected value is never echoed into logs/artifacts.
- An actual secret finding triggers the incident runbook; it is not copied into evidence.

### 7.3 Privacy/data minimization proof

Foundation has no model for provider/account/session/telemetry content. Its schemas accept only technical configuration descriptors, safe build metadata, correlation identifiers, and typed safe log fields. Dependency inventory confirms no analytics or crash-reporting service. Browser network inspection confirms no application-originated external analytics call. Source and artifact review confirms no example account, metric, email, project path, provider payload, prompt, response, tool, source, or arbitrary environment capture.

### 7.4 Abuse and failure cases

- Malicious Host/Origin: final enforcement belongs P01; foundation ensures the hook and refuses non-loopback local bind.
- Correlation header injection/cardinality attack: validate bounds and characters; generate a safe ID if policy permits.
- Configuration value exfiltration through error/repr/schema: secret wrapper and real output scan.
- Dependency install compromise: locks, integrity/provenance review, no unreviewed scripts/binaries, SBOM.
- Generated artifact poisoning/manual change: clean regeneration, source hashes, protected ownership, drift gate.
- Migration race/competing head: central allocation and single migration job/lock policy.
- CI artifact leak: allowlisted artifact paths, secret scan, short retention, no raw environment dumps.
- Browser bundle leak: production-build string/source-map inspection and network review.

## 8. Configuration and operations

### 8.1 Configuration allocation table

No exact external variable name is approved in this Draft. The following categories require owner synchronization before allocation.

| Category | Key owner | Foundation responsibility | Secret class | Reload behavior |
|---|---|---|---|---|
| Local bind/public origin/trusted hosts | P01/PLAN-DEP | Typed bootstrap transport | Non-secret, security-critical | Restart |
| Database path/connection mode | PLAN-DB/M08/PLAN-DEP | Typed path/engine bootstrap | Sensitive path, not secret | Restart |
| Alembic/schema compatibility | PLAN-DB/integration | Build/runtime metadata | Non-secret | Restart/migration |
| Session/signing/bootstrap auth | M01 | Secret wrapper/loader only | AgentMonitor-managed secret | Defined by M01; likely restart/rotation |
| Log level/path/rotation | M08/PLAN-DEP | Typed sink construction/redaction | Path may be sensitive | Owner-defined |
| Frontend/OpenAPI/build IDs | PLAN-FND/P01/P02 | Validated immutable metadata | Public/non-secret | Build-time/restart |
| Provider/profile state | M02/A01-A04 | No key allocation in foundation | Provider-managed/opaque | Adapter-defined after discovery |
| GitLab development token | Development tooling owner | Explicitly excluded from runtime loader | Development secret | Tool-only |

### 8.2 Liveness, readiness, and diagnostics seam

Foundation may provide internal lifecycle status types and a minimal liveness mechanism needed by the real-stack harness. Public disclosure, route paths, authentication, readiness aggregation, database/collector health, diagnostics, and version views belong to P01/M08 and are not claimed here. A process being alive is never equated with application readiness.

### 8.3 Operational constraints

- No service manager command is documented until PLAN-DEP implements and verifies it.
- Startup fails safely on invalid security-critical configuration or incompatible schema.
- Shutdown is bounded and never signals/manages provider agents.
- Logs are local, bounded through a future M08/DEP policy, and safe by construction.
- The browser is only a client; closing it cannot own or terminate the application process.
- The foundation does not create backups, exports, retention jobs, provider profiles, or external resources.

## 9. Test design before implementation

### 9.1 Integrity rules for foundation tests

- No mocks, fakes, stubs, emulators, replay/recording servers, monkeypatched collaborators, in-memory SQLite substitutes, DOM-only E2E substitutes, seeded telemetry, demo accounts, or placeholder provider values.
- Pure constructed inputs are limited to deterministic policy/value functions with no I/O and cannot prove an external boundary.
- Real configuration tests use actual isolated files and process startup, not patched environment access.
- HTTP tests start the production application through the selected real ASGI server on an ephemeral loopback port and send real network requests.
- Browser tests build production assets and drive a real supported browser against the running server.
- SQLite tests use an actual file and production migration/engine code.
- GitLab CI claims require a real hosted pipeline; macOS claims require real macOS.
- No dependency/setup/syntax/credential failure satisfies Red. A missing production symbol may be Red only when the admitted test environment works and the failure is the explicitly expected missing behavior.

### 9.2 Test inventory

| Test ID | Layer | Requirement | Real dependencies | Initial failure expected | Pass condition | Owner/live coordination |
|---|---|---|---|---|---|---|
| FND-VER-001 | Toolchain | Coding standards/NFR-LIC-001 | Real selected Python/Node executables | Unsupported runtime is not rejected | Supported baseline accepted; unsupported one fails preflight safely | Dependency/integration owner |
| FND-ENV-001 | Build | NFR-LIC-001 | Clean Linux environment, canonical registries, committed locks | Frozen install cannot complete/reproduce | Clean locked backend/frontend installs and builds succeed | Network required; no provider auth |
| FND-ENV-002 | Build/macOS | NFR-PLAT-001 | Real macOS | Not Run until hardware exists | Same portable environment/build gates pass | Owner supplies macOS or Blocked |
| FND-BND-001 | Static policy | NFR-ARCH-001 | Real repository source/checker | Controlled real forbidden import is not detected | Red evidence detects it; clean source passes after removal | Architecture reviewer |
| FND-BND-002 | Static policy | NFR-ARCH-001/002 | Real source dependency graph | Cycle/private/deep import remains possible | Gate rejects all documented forbidden edges | Architecture reviewer |
| FND-BND-003 | Policy | NFR-ARCH-002/NFR-COMP-001 | Real ownership/contract manifest | Owned path/contract can be unowned or multiply owned | Exactly one owner and valid version/status per entry | Integration steward |
| FND-CFG-001 | Process/filesystem | NFR-SEC-001 | Real temp `.env`, real app process | Missing/malformed/conflicting critical setting does not fail safely | Typed outcomes, nonzero safe exit, no value echo | Security reviewer |
| FND-CFG-002 | Process/filesystem | NFR-SEC-001 | Real owner-permission config path | Operator/default `.env` can be discovered implicitly | Only explicit isolated path read; permissions enforced where supported | Security reviewer |
| FND-CFG-003 | Process/log | NFR-SEC-001, AC-V1-007 | Ephemeral canary, real error/log sinks | Secret canary appears in repr/error/log/schema | Canary absent everywhere; only configured/missing exposed | Security reviewer |
| FND-CFG-004 | Compatibility | NFR-COMP-001 | Real config loader/process | Unknown/deprecated setting silently changes behavior | Documented reject/warn/migrate policy observed | Configuration owners |
| FND-DB-001 | T2 DB | NFR-DATA-001, AC-V1-004 | Real SQLite file, real Alembic chain | Empty database cannot reach head | Migration reaches head; only approved tool metadata exists | PLAN-DB review |
| FND-DB-002 | T2 DB | NFR-COMP-001 | Real SQLite schemas | Writable startup accepts newer schema or hides older DDL | Newer refused; older handled only by explicit supported migration | PLAN-DB review |
| FND-DB-003 | T2 DB | NFR-DATA-001 | Real engine/file | FK/journal/transaction/cleanup policy absent | Settings and rollback/close behavior match approved record | PLAN-DB review |
| FND-DB-004 | T2 DB | NFR-DATA-001 | Real failed migration against isolated file | Failed migration leaves unclassified/unsafe state | Failure is visible; recovery path preserves original evidence | Migration steward |
| FND-MIG-003 | Policy/migration | NFR-ARCH-002 | Real revision files | Revision lacks owner/metadata or competing head is accepted | Allocation/metadata/head rules enforced | Migration steward |
| FND-HTTP-001 | T3 HTTP | NFR-API-001, FR-IAM-007 | Real server, real loopback socket, real SQLite config | App cannot start/stop via production factory | Starts only loopback, serves approved skeleton behavior, shuts down cleanly | P01/DEP review |
| FND-HTTP-002 | T3 HTTP | FR-IAM-007 | Real requests/socket | Non-loopback or untrusted host/origin policy seam is absent | Local-mode bind cannot expand; enforcement ownership visible | P01 owns final security behavior |
| FND-OAPI-001 | Contract | NFR-API-001/002 | Production app composition and generator | No canonical valid OpenAPI artifact | OpenAPI 3.x validates and generation is stable | P01/integration |
| FND-OAPI-002 | Contract | NFR-COMP-001, AC-V1-003 | Real current/baseline documents | Breaking drift is not classified/blocked | Compatible/breaking report follows policy | P01/contract reviewer |
| FND-OAPI-003 | Generated drift | NFR-API-002 | Clean worktree generation | Manual/stale artifact can pass | Regeneration has no unexplained diff | Integration steward |
| FND-CLIENT-001 | Build/contract | NFR-API-002 | Admitted generator, real OpenAPI, TypeScript compiler | Client absent or cannot compile strictly | Generated client compiles without handwritten DTO patch | P02 reviewer |
| FND-CLIENT-002 | T3 | AC-V1-003 | Real server, generated client, first approved P01 operation | Not Run until an approved operation exists; then client cannot execute it correctly | Real network request conforms to the approved server/schema; no foundation-only test endpoint | P01/P02 review; visibly Not Run during empty skeleton |
| FND-UI-001 | T4 browser | AC-TEST-003, FR-OPS-001 support | Production frontend build, backend, real browser, SQLite | Built shell cannot be served/loaded | Browser loads same-origin shell at baseline viewports | P02/DEP review |
| FND-UI-002 | T4/review | NFR-TEST-002, AC-V1-008 | Real built browser/assets | Sample/placeholder telemetry or direct fetch appears | No telemetry-like data, duplicated DTO, or direct feature fetch | P02/test-integrity reviewer |
| FND-LOG-001 | Process/HTTP | NFR-OBS-001 | Real HTTP/process/background events and sink | Required structure/correlation absent | Safe fields and correlation propagate across actual boundaries | P01/M08 review |
| FND-LOG-002 | Security | NFR-OBS-001, FR-OPS-005 | Real sink and generated canaries | Secret/content/path/header values appear | Allowlist output contains none of them | Security reviewer |
| FND-LOG-003 | Resilience | NFR-RES-001 | Real exception/process task | Failure crashes process or leaks raw cause | Typed sanitized outcome; unrelated skeleton request remains available | Integration reviewer |
| FND-LOG-004 | Operations | NFR-OBS-001 | Real bounded local sink | Unbounded/remote logging enabled | No remote handler; bounded sink seam and safe defaults verified | M08/DEP review |
| FND-LIFE-001 | Process | FR-OPS-001, AC-OPS-001 support | Real AgentMonitor process/signals | Shutdown hangs/leaks resources | Bounded graceful stop and stable exit classification | Linux platform/DEP review |
| FND-LIFE-002 | Resilience | NFR-RES-001 | Real supervised task/process | One owned task failure terminates service silently | Failure isolated/surfaced; service behavior follows policy | Integration reviewer |
| FND-LIFE-003 | Restart | AC-OPS-003 support | Real process + SQLite | Restart causes hidden DDL/resource conflict | Clean restart with compatible schema and released resources | M08/DEP review |
| FND-META-001 | Build/runtime | FR-OPS-006 | Real built frontend/backend/artifacts | Versions/hashes unavailable or leak local data | Safe build/schema/API/client IDs align and expose via port | M08/P01/P02 |
| FND-TEST-001 | Repository review | NFR-TEST-002, AC-TEST-002 | Real source/dependency graph | Prohibited test-double/replay/demo framework or path is accepted | No prohibited mechanism/dependency/test pattern | Test-integrity reviewer |
| FND-EVID-001 | Evidence | AC-TEST-001/006 | Actual test reports/evidence | Aggregate hides Failed/Blocked/Not Run or lacks Red | Statuses remain distinct; R/G/R refs required | Integration steward |
| FND-DEP-001 | Dependency | NFR-LIC-001 | Actual manifests/locks/upstream metadata | Unadmitted direct/transitive package exists | Every package traceable to approved admission and lock | Dependency reviewer |
| FND-DEP-002 | License | NFR-LIC-001 | Actual locked graph/scanner/manual review | License missing/incompatible/notices incomplete | Reviewed report, SBOM, notices pass | Owner approval for exceptional license |
| FND-DEP-003 | Security | NFR-SEC-001 | Actual locked graph/advisory sources | Unreviewed blocking vulnerability/provenance issue | No unresolved blocking issue; exceptions have owner/expiry | Security reviewer |
| FND-DEP-004 | Reproducibility | NFR-LIC-001 | Real clean builds | Lock drift/unpinned tool produces differing dependency graph | Frozen resolution matches reviewed graph | Dependency reviewer |
| FND-SEC-001 | Secret scan | AC-V1-007 | Actual repository/history range/artifacts | Scan not configured or reports unsafe output | Admitted scanner completes with sanitized no-blocker result | Security reviewer |
| FND-SEC-002 | Artifact review | NFR-SEC-001/PRIV-001 | Actual build/UI/OpenAPI/log/test artifacts | Local path/config/private field leaks | Allowlisted artifact inventory passes | Security/privacy reviewer |
| FND-SEC-003 | SAST/config | NFR-SEC-001 | Real source/config | High-risk pattern/misconfiguration is not gated | No unresolved blocking finding | Security reviewer |
| FND-PRIV-001 | Data inventory | NFR-PRIV-001 | Actual schemas/source/artifacts | Content/provider/account field exists in foundation | Inventory contains only approved technical metadata | Privacy reviewer |
| FND-PRIV-002 | Network/dependency | NFR-PRIV-002 | Actual dependency graph and browser/process traffic | Analytics/crash outbound behavior exists | No analytics/crash dependency or call | Privacy reviewer |
| FND-DOC-001 | Docs | NFR-DOC-001 | Actual Markdown tree | Broken local links/duplicate IDs/invalid status | All configured checks pass | Documentation owner |
| FND-DOC-002 | Docs/contracts | NFR-COMP-001 | Actual docs/OpenAPI/ownership records | Referenced contract/requirement/version missing | Cross-reference registry resolves | Integration steward |
| FND-DOC-003 | Commands | NFR-DOC-001 | Actual verified command executions | Unverified/invented command enters runbook | Every authoritative command links executed evidence | Operations reviewer |
| FND-PLAT-001 | Platform | NFR-PLAT-001 | Real Linux | Core imports hard-code Linux/service details | Platform-specific dependencies isolated | Linux reviewer |
| FND-PLAT-002 | Platform | NFR-PLAT-001 | Real macOS | Not Run until real environment | Portable subset passes or remains Blocked visibly | macOS owner |
| FND-PERF-001 | Performance | NFR-PERF-001 support | Real production skeleton/build | Foundation startup/resources have no baseline | Measured baseline with limits defined; no business-scale claim | Performance reviewer |
| FND-SAFE-001 | Contract/source | FR-SAFE-002 | Real public schemas/source | Agent-control port or subprocess operation is exposed | No kill/restart/inject/switch/route capability | Security/architecture |
| FND-CI-001 | CI | SDLC GitLab policy | Real GitLab-hosted runner | Pipeline cannot execute from locks | Required local-stack stages execute | Owner authorizes repository use |
| FND-CI-002 | CI evidence | AC-TEST-006 | Real pipeline summary | T5/T6 absent states hidden by green | Separate Passed/Failed/Blocked/Not Run matrix visible | Integration/live owners |

### 9.3 Failure, migration, and recovery scenarios

Foundation tests cover malformed/missing configuration, unsafe permissions where supported, unsupported runtimes, lock drift, package registry failure, database lock/permission/schema mismatch, failed migration, server port collision, startup cancellation, task exception, shutdown timeout, invalid correlation input, stale generated artifacts, breaking OpenAPI diff, frontend/backend version mismatch, browser asset failure, secret/static/license finding, and GitLab job/artifact failure.

They do not manufacture provider quota/auth/rate-limit/process states. Those remain live scenarios under owning plans. Destructive database/disk tests use isolated temporary roots and an approved test design; they never target operator data.

### 9.4 Red evidence policy for bootstrap work

Installing an admitted test runner/resolver is a prerequisite, not a product behavior and not itself claimed as TDD evidence. Once the clean toolchain works, every production mechanism begins with a behaviorally meaningful failing test. Expected first failures are missing contract behavior or an actual policy violation, never a missing dependency, syntax error, invalid setup, or unavailable credential. The handoff captures sanitized timestamps/commands by verified command ID after the registry exists.

## 10. Implementation increments

Implementation is sequential until shared mechanisms stabilize. Parallel work begins only after explicit file allocation and cannot share manifests, locks, Alembic head, OpenAPI, generated client, CI file, or build configuration.

| Increment | Files/area | Failing test first | Minimum production/mechanism change | Refactor/documentation | Exit evidence |
|---|---|---|---|---|---|
| FND-I00 — decisions/admission | Version/dependency records only | No product behavior; admission gates FND-DEP-001 baseline current graph | Approve runtime/package/tool choices; no app code | Record alternatives, licenses, security, platforms, exact pin strategy | Owner approval; this is prerequisite, not Green behavior |
| FND-I01 — reproducible toolchains | Manifests/version files/locks | FND-VER-001, FND-ENV-001 | Minimal selected backend/frontend projects with frozen resolution | Document clean setup only after executed | Clean Linux install/build evidence; macOS visible state |
| FND-I02 — ownership and boundaries | Source topology/policy | FND-BND-001..003 | Minimal package topology and enforced dependency/ownership rules | Remove controlled Red violation; document owner map | Red detector proof then clean Green graph |
| FND-I03 — typed configuration | Foundation configuration | FND-CFG-001..004 | Immutable loader/descriptors/secret-safe wrapper with no final module keys | Security review and registry schema docs | Real file/process R/G/R evidence |
| FND-I04 — SQLite/Alembic mechanism | Persistence bootstrap/migrations | FND-DB-001..004, FND-MIG-003 | Engine/UoW seam, explicit migration entry, metadata-only base | Portability and recovery notes | Real file/head/failure evidence; no module tables |
| FND-I05 — logging/correlation | Foundation observability | FND-LOG-001..004 | Typed allowlisted log/correlation/lifecycle primitives | Redaction and cardinality review | Real sink/process evidence, canary absent |
| FND-I06 — composition/HTTP | App factory/composition/API seam | FND-HTTP-001..002, FND-LIFE-001..003 | Minimal production application factory/server lifecycle on loopback | P01/DEP handoff docs | Real socket/process/SQLite startup/shutdown evidence |
| FND-I07 — OpenAPI/client | OpenAPI artifact/generator/client | FND-OAPI-001..003, FND-CLIENT-001; register FND-CLIENT-002 as Not Run until P01 operation exists | Deterministic generation/validation/diff/client pipeline for skeleton | Generated ownership/provenance docs | Valid artifact and strict compile; no invented test endpoint; real request follows approved P01 contract |
| FND-I08 — built UI/browser | Frontend shell/static delivery | FND-UI-001..002, FND-META-001 | Secret-free production shell and same-origin delivery | P02/DEP handoff; no feature data | Real built-browser evidence at approved viewports |
| FND-I09 — scans/docs/supply chain | Tool policies and artifacts | FND-TEST-001, FND-DEP-001..004, FND-SEC-001..003, FND-PRIV-001..002, FND-DOC-001..003 | Blocking gates, SBOM/notices, documentation validators | Review false-positive/exception policy | Actual graph/source/artifact reports |
| FND-I10 — hosted CI | `.gitlab-ci.yml` and CI-owned config | FND-CI-001..002 | Minimum hosted pipeline implementing approved stages | Add only commands verified locally; artifact policy | Real GitLab-hosted run; no live-provider claim |
| FND-I11 — native handoff/performance | Entrypoint/metadata seams | FND-PLAT-001..002, FND-PERF-001, FND-SAFE-001 | Stabilize entry/build metadata and platform-neutral seams | PLAN-DEP/P01/P02/DB/M08 handoff | Linux evidence; macOS status explicit; review sign-off |

### 10.1 Shared-file edit ownership

| Shared artifact | Single edit owner during foundation wave | Required reviewers/consumers |
|---|---|---|
| Backend manifest/lock | Dependency steward | Security, license, backend owners |
| Frontend manifest/lock | Dependency steward | Security, license, P02 |
| Runtime version files | Integration steward | Backend/frontend/DEP |
| `.gitlab-ci.yml` | CI integration steward | Security, test, dependency owners |
| Alembic environment/head allocation | Migration integration steward | PLAN-DB and affected module owner |
| OpenAPI committed artifact | Generator/API steward through generator only | P01, all API consumers |
| Generated TypeScript client | Generator steward through generator only | P02 |
| Vite/TypeScript configs | Frontend foundation steward until P02 handoff | P02/security |
| Composition root | Integration steward | Every wired producer/consumer; no parallel edits |
| Ownership/import policy | Architecture steward | Every module owner |
| SBOM/notices | Dependency/release steward through generator | License/security |
| Command registry | Integration/operations steward | Command owner and verifier |

### 10.2 Stop/escalation conditions

Stop when an exact dependency lacks admission; a module key/table/route/business rule is needed; a provider/profile/process path would be touched; a public contract meaning changes; an unauthenticated endpoint must be exposed; a secret/content field appears; a migration would be destructive or cross-module; GitLab access or external mutation is required without authority; a real test requires user credentials; macOS is being inferred; or another agent owns the same shared file/head/generated artifact.

### 10.3 Implementation-agent return packet

Every separately authorized FND increment returns one inspectable packet naming
the requirement/acceptance and scenario IDs, plan and contract versions, exact
files changed, and exact Red/Green/refactor commands and results. It separates
T1–T7 Passed, Failed, Blocked, and Not Run states; identifies every real
boundary exercised; records security, privacy, migration, dependency/license,
and documentation impact; lists residual risks; and names the next integration
step and its required authority. A narrative completion claim without this
packet and the applicable canonical gates is rejected.

## 11. Documentation outputs

Implementation increments, when separately authorized, must update/create only the approved documents for their behavior:

- Repository topology and ownership map.
- Approved runtime/dependency admission records and update policy.
- Clean development/build setup using only verified command-registry entries.
- Configuration key registry and `.env` handling guidance once keys are allocated.
- Generated OpenAPI/client provenance and compatibility workflow.
- Migration allocation/metadata/recovery standard.
- CI stage/artifact/evidence documentation.
- Test evidence records and explicit platform/live-state matrix.
- SBOM and third-party notices provenance.
- P01/P02/PLAN-DB/M08/PLAN-DEP handoff notes.
- Traceability/risk updates if approval changes ownership or mitigation.

Runbooks keep `TBD` command placeholders until real execution passes. Generated documents identify source/tool/version and are never patched manually.

## 12. Dependency and license impact

### 12.1 Admission rule

Every item below is **Candidate / Pending admission**. Mention in an accepted architecture document is not version or transitive approval. No manifest, lock, download, or install is authorized by this Draft.

For each selected item, admission records canonical upstream/package identity, exact version, upstream license file at that version, all transitive packages/licenses, maintenance/release/security posture, supported Python/Node/OS range, native/binary/install-script behavior, network/telemetry behavior, vulnerabilities, provenance/integrity, size/performance, alternatives, removal strategy, SBOM/notices obligations, reviewer, and approval date. License and transitive review repeat at pinning and every lock update.

### 12.2 Candidate inventory

| Candidate/group | Purpose | Baseline license indication, not approval | Alternatives/decision required | Status |
|---|---|---|---|---|
| Python runtime + one resolver/environment tool | Backend runtime and reproducible lock/install | Runtime/tool licenses must be verified | Compare supported lock/hash/export behavior and CI/macOS availability | Candidate / Pending |
| FastAPI | Public ASGI/OpenAPI boundary | MIT in baseline policy; recheck exact version | Required by NFR; assess transitive graph | Candidate / Pending |
| One production ASGI server | Real installed/test HTTP service | Verify canonical license/version/transitives | Compare supported lifecycle, limits, logging, platforms | Candidate / Pending |
| Pydantic plus settings integration if separate | Typed transport/bootstrap validation | MIT baseline for Pydantic; recheck all packages | Prefer minimum package set; assess secret serialization | Candidate / Pending |
| SQLAlchemy | Persistence mechanism | MIT baseline; recheck exact version | Required architecture candidate; inspect SQLite/PostgreSQL support | Candidate / Pending |
| Alembic | Explicit migration chain | Verify exact upstream license/transitives | Required architecture candidate; assess deterministic CLI/API use | Candidate / Pending |
| One Python test runner | Execute pure/real-stack tests and report status | Verify exact license/transitives/plugins | Must work without mock plugins; minimal plugin set | Candidate / Pending |
| One real HTTP client library or standard library | T3 requests/generated-client contract checks | Verify if third-party | Prefer production-relevant client where justified | Candidate / Pending |
| One Python formatter/linter | Deterministic format/lint | Verify exact license/binary provenance | Select one coherent tool, avoid overlapping formatters | Candidate / Pending |
| One strict Python type checker | Public/cross-module type gate | Verify exact license/transitives | Compare strictness, plugin needs, CI/macOS support | Candidate / Pending |
| One import-boundary/dependency analyzer | Enforce architecture | Verify license/maintenance/parser support | Admit tool or small repository-owned analyzer after build-vs-buy review | Candidate / Pending |
| Coverage/mutation tools | Diagnostic coverage and critical-policy mutation gates | Verify each exact license/transitives | Mutation tool may be deferred until first critical pure logic but gate must be planned | Candidate / Pending |
| Node.js runtime + one package manager | Frontend build and reproducible lock/install | Verify runtime/tool license and bundled components | Select one lock format/frozen-install behavior | Candidate / Pending |
| React | UI shell/runtime | MIT baseline; recheck exact version | Required architecture candidate | Candidate / Pending |
| TypeScript | Strict frontend types | Verify exact Apache-2.0 indication and bundled notices | Required for selected stack | Candidate / Pending |
| Vite and required official plugin(s) | Production frontend build | MIT baseline; recheck bundled/transitive notices | Assess install scripts, bundle provenance, source-map policy | Candidate / Pending |
| One frontend formatter/linter set | Deterministic format/lint/import checks | Verify every package/transitive | Choose smallest coherent set; no duplicate toolchains | Candidate / Pending |
| Vitest or selected pure frontend runner | Non-E2E frontend/tooling tests | MIT baseline for Vitest; recheck | Only where pure tests add value; never DOM substitute for T4 | Candidate / Pending |
| Playwright | Real built-browser T4 tests | Apache-2.0 baseline; recheck package/browser binary notices | Review browser downloads/binaries/cache/platform cost | Candidate / Pending |
| One OpenAPI validator and compatibility-diff tool | Validate/classify API artifact | Verify exact licenses/transitives/binaries | Evaluate OpenAPI 3.x coverage and false positives | Candidate / Pending |
| One OpenAPI TypeScript client generator | Generated client source of truth | Verify exact license/templates/transitives | Compare strict typing, runtime size, fetch abstraction, deterministic output | Candidate / Pending |
| Secret scanner | Repository/artifact secret gate | Verify license/binary provenance/rules | Must redact findings; no cloud upload | Candidate / Pending |
| Python/Node SAST and vulnerability scanners | Security/advisory gates | Verify each license/data flow/advisory source | Prefer local/offline reports where practical; define severity policy | Candidate / Pending |
| License inventory/scanner | Direct/transitive license gate/notices | Verify package and detection data licenses | Manual review remains authoritative | Candidate / Pending |
| SPDX or CycloneDX SBOM generator(s) | Release component inventory | Verify tool/license/ecosystem coverage | One merged authoritative format or documented outputs | Candidate / Pending |
| Markdown/link/schema validation tools | Documentation quality gates | Verify licenses/transitives | Prefer minimal tools; no external document upload | Candidate / Pending |

TanStack Query, ECharts, accessible UI primitives, CSS frameworks, provider SDKs, systemd helpers, and operational backup tools are not admitted by PLAN-FND merely because they are shortlisted elsewhere. Their owning plans must justify and admit them.

### 12.3 Supply-chain outputs

- Frozen backend/frontend lockfiles with generator/tool versions.
- Direct/transitive license inventory with manual exception review.
- Vulnerability/provenance report with time-bounded exceptions.
- SPDX or CycloneDX SBOM covering backend, frontend, browser/build binaries as applicable.
- Third-party notices including bundled Vite/browser/frontend obligations.
- Dependency delta report for every lockfile update.
- Evidence that no selected package introduces external analytics/crash reporting.

## 13. Risks and unresolved decisions

### 13.1 Linked project risks

This plan mitigates but does not close R-005, R-011, R-012, R-013, R-018, R-019, R-020, and R-023. Closure requires implementation/live evidence and the owning module/operations plans.

| ID | Risk/question | Likelihood/impact | Mitigation or decision experiment | Owner | Trigger/deadline | Status |
|---|---|---|---|---|---|---|
| FND-R01 | Exact Python line conflicts with dependency/platform security support | Medium/Major | Run selection gate and clean Linux/macOS compatibility matrix | Dependency steward | Before any backend manifest | Open |
| FND-R02 | Exact Node/package-manager line produces unstable or insecure lock/build | Medium/Major | Compare frozen resolution, security horizon, GitLab/macOS availability | Frontend dependency steward | Before frontend manifest | Open |
| FND-R03 | Tooling graph becomes larger/riskier than product runtime | Medium/Major | Dependency budget, single tool per role, isolated dev groups, SBOM | Dependency reviewer | Every admission/update | Open |
| FND-R04 | Foundation becomes a shared-business `utils` layer | Medium/Critical | Consumer proof, explicit imports, architecture review, delete unused abstraction | Architecture steward | Any proposed shared helper | Open |
| FND-R05 | Composition root becomes hidden business orchestration | Medium/Major | Wiring/lifecycle only; use-case behavior stays module-owned | Integration steward | Any branch/decision on domain values | Open |
| FND-R06 | Generated client/OpenAPI drift or manual patch hides incompatibility | Medium/Critical | One-way generator, clean regeneration, source hashes, protected ownership | API/client steward | Every API change | Open |
| FND-R07 | Shared migration chain blocks parallel module work | High/Major | Central allocation, one head owner, serialized migration integration | Migration steward | Before parallel DB work | Open |
| FND-R08 | SQLite bootstrap choices block PostgreSQL later | Medium/Major | Adapter isolation, portable contract/types, explicit portability report | PLAN-DB reviewer | Engine/migration decision | Open |
| FND-R09 | Config loader leaks or implicitly reads developer secrets | Medium/Critical | Explicit path, secret type, isolated tests, output scan, no global mutation | Security/config owner | Before startup implementation | Open |
| FND-R10 | Structured logging accepts arbitrary sensitive objects | Medium/Critical | Typed allowlist fields, no raw dumps, real canary/artifact scans | Security/observability owner | Before any module logs | Open |
| FND-R11 | CI green is mistaken for live provider/platform success | High/Major | Separate T1-T4 vs T5/T6 matrix; Blocked/Not Run cannot collapse | Test/integration owner | First hosted pipeline | Open |
| FND-R12 | GitLab artifacts/caches expose paths, secrets, or operational data | Medium/Critical | Allowlisted artifacts, scans, retention, no provider/local inputs | CI/security owner | Before artifact upload | Open |
| FND-R13 | Browser dependency downloads/binaries create license/supply-chain risk | Medium/Major | Explicit Playwright/browser admission, pin/cache/notices review | Dependency/P02 owner | Before T4 harness | Open |
| FND-R14 | Authenticated docs requirement conflicts with pre-IAM API skeleton | Medium/Major | Disable installed docs until M01/P01; controlled build generation only | P01/M01 reviewer | Before HTTP skeleton approval | Open |
| FND-R15 | Exact scanner/generator selection produces false assurance | Medium/Major | Independent manual review, efficacy evidence, no tool equals proof | Security/contract reviewers | Admission and milestone review | Open |
| FND-R16 | Native entrypoint embeds Linux assumptions and blocks macOS | Medium/Major | Platform-neutral lifecycle; real macOS gate remains visible | Platform/DEP owner | Before native handoff | Open |
| FND-R17 | Reproducible build is claimed despite timestamps/platform variation | Medium/Moderate | Define functional/bit reproducibility scope and normalize approved metadata | Build steward | Before build gate approval | Open |
| FND-R18 | TDD bootstrap is weakened into setup-failure Red evidence | Medium/Critical | Admit tools first; require behavior failure and independent test review | Test-integrity reviewer | Every increment handoff | Open |

### 13.2 Approval-blocking unresolved choices

1. Exact supported Python version/range and selection record owner.
2. Exact supported Node.js version/range and selection record owner.
3. Python resolver/environment tool and lock format.
4. Node package manager and lock format.
5. ASGI server and lifecycle configuration.
6. Python formatter/linter, strict type checker, test runner, coverage/mutation, and import-boundary tools.
7. Frontend formatter/linter/test tooling.
8. OpenAPI validator, compatibility-diff tool, canonicalization policy, and TypeScript generator.
9. Real browser(s) required in the initial foundation gate and browser-binary supply-chain policy.
10. Secret, SAST, vulnerability, license, SBOM, and documentation tool set plus blocking severities.
11. Exact ownership-manifest representation and enforcement engine.
12. SQLite journal/synchronous/timeout settings and SQLAlchemy/Alembic integration details after PLAN-DB review.
13. Whether a metadata-only/no-op base Alembic revision is useful or an empty chain is preferable.
14. Installed-mode docs generation/exposure sequence with P01/M01.
15. Static frontend serving ownership and artifact layout across P01/P02/PLAN-DEP.
16. Correlation ID representation, validation policy, and external header ownership.
17. Build reproducibility definition and generated artifact commit/retention policy.
18. GitLab-hosted runner images, artifact retention, branch protection/review policy, and permission to contact/configure GitLab.
19. Real macOS environment availability; absence must stay Blocked.
20. Command-registry file name/location and first independently verified command.

Any choice above that could produce materially different layouts, lockfiles, public behavior, or security posture must be resolved before implementation approval, not delegated to an implementation agent.

## 14. Delivery, compatibility, and rollback

### 14.1 Delivery order

1. Approve this plan and ownership map.
2. Complete runtime/dependency/tool admissions with exact pins.
3. Synchronize proposed contracts with P01, P02, PLAN-DB, M01, M08, and PLAN-DEP.
4. Implement FND-I01 through FND-I11 using one shared-file owner at a time.
5. Run local clean Linux gates, then an actual GitLab-hosted pipeline when authorized.
6. Record macOS as Passed or Blocked based only on real execution.
7. Freeze `foundation.contracts.v1`, hand paths/seams to module owners, and update the module planning registry through the root steward.

No foundation delivery is a product release. No provider account, local default profile, running agent, GitLab setting, or installed service is changed by planning.

### 14.2 Compatibility window

- Pre-1.0 Draft mechanisms may change only before consumer plans approve them.
- Once a module consumes `foundation.contracts.v1`, compatible additive changes follow normal review; semantic/breaking changes require a new major, consumer migration, and ADR if architectural.
- Alembic history is immutable after shared use.
- OpenAPI `/api/v1` compatibility and generated-client drift are separately governed.
- Runtime/toolchain upgrades are reviewed changes with clean resolve/build/test evidence on supported platforms.

### 14.3 Rollback/recovery

- Manifest/tooling changes roll back by restoring the prior reviewed manifests and generated locks together; partial manifest/lock rollback is forbidden.
- Generated OpenAPI/client/SBOM/notices roll back only by restoring source/config/tool version and regenerating; never hand-edit output.
- CI changes retain a prior known-good pipeline revision; rollback cannot suppress a newly discovered security/license finding without explicit risk acceptance.
- Before business data exists, an isolated foundation database can be recreated from the empty migration chain. This rule never applies to later operator databases.
- After shared migrations exist, rollback follows each migration's tested downgrade or verified-backup/prior-binary recovery plan.
- Composition/config changes preserve last known compatible artifact/config and fail closed rather than silently downgrade semantics.
- Foundation removal/replacement must leave no orphaned module imports or duplicated generated schema.

### 14.4 Post-delivery checks

- Ownership/import graph clean and acyclic.
- Frozen clean installs and builds pass.
- Real SQLite migration and schema compatibility pass.
- Real loopback HTTP start/stop passes.
- OpenAPI validates; compatibility and drift gates pass; generated client compiles. FND-CLIENT-002 either executes an approved P01 operation against the real server or remains explicitly Not Run while the skeleton has no operation; foundation never invents a test endpoint.
- Production UI shell loads in a real browser and contains no telemetry/secret.
- Security, privacy, vulnerability, license, SBOM, notices, and documentation gates pass.
- GitLab-hosted evidence is separate from local/live state.
- No default provider profile, process, external resource, or user `.env` was touched.

## 15. Definition of Ready for implementation

- [ ] Pavlo Sidelov/root steward approves the plan version and changes Status from Draft.
- [ ] Exact requirements/AC scope and supporting-only claims are accepted.
- [ ] P01, P02, PLAN-DB, M01, M08, and PLAN-DEP accept the handoff/ownership matrix.
- [ ] `foundation.contracts.v1` schemas and compatibility promises are reviewed and approved.
- [ ] Allowed/forbidden paths/imports and shared-file owners are frozen for the implementation wave.
- [ ] Exact Python and Node baselines pass their selection gates and are approved.
- [ ] Every direct tool/runtime dependency has exact-version, transitive-license, security, maintenance, provenance, telemetry, platform, and notices approval.
- [ ] One Python and one Node lock workflow are approved; clean resolution evidence is possible.
- [ ] Test inventory and every meaningful expected Red are independently reviewed.
- [ ] The initial test runner/toolchain can execute without treating setup failure as Red.
- [ ] Real Linux, real SQLite, real loopback HTTP, and real supported browser resources are available.
- [ ] Real macOS availability is identified; unavailable work is preclassified Blocked, not simulated.
- [ ] GitLab-hosted runner use and any external access are separately authorized before FND-I10.
- [ ] Security/privacy threat review approves config, logs, CI artifacts, generation, and dependency flows.
- [ ] Migration/base-revision/head-allocation and PostgreSQL portability choices are approved.
- [ ] OpenAPI/client source-of-truth, generator, artifact paths, and manual-edit prevention are approved.
- [ ] CI scanners, severities, artifacts, retention, and secret-output handling are approved.
- [ ] Command registry governance is approved; no unverified command is presented as authoritative.
- [ ] Rollback/recovery and generated/shared-file ownership are accepted.
- [ ] No unresolved choice in section 13.2 permits materially different implementations.
- [ ] No other agent is assigned the same manifest, lock, migration head, generated artifact, CI file, composition root, or tool configuration.

Until every applicable item is checked and the approval record below is completed, production implementation must not begin.

## 16. Approval record

| Reviewer/owner | Decision | Conditions | Plan/contract version | Date |
|---|---|---|---|---|
| Pavlo Sidelov / root steward | Pending | All Definition of Ready items resolved | Plan 0.2.0-draft / proposed `foundation.contracts.v1` | Pending |
| Architecture/integration | Pending | Ownership, topology, imports, composition, shared files | Same | Pending |
| Security/privacy | Pending | Config, logging, CI, artifact and secret controls | Same | Pending |
| Test integrity | Pending | Meaningful Red and real-boundary harness design | Same | Pending |
| Dependency/license | Pending | Exact-version direct/transitive admission | Same | Pending |
| P01/P02/PLAN-DB/M01/M08/PLAN-DEP consumers | Pending | Contract and handoff synchronization | Same | Pending |

Drafting this document creates no authorization to initialize Git, add manifests or configuration, install/download dependencies, create `.env`, contact GitLab, inspect provider state, or implement production/test code.
