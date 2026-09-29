# AgentMonitor documentation index

<!-- agentmonitor-milestone-status:v1 milestone=V1-M3 lifecycle=active status=blocked authority=M3-ACCEPTANCE-2026-09-24-01 -->

The authoritative V1-M3 status is **Blocked** in the machine-readable
[V1-M3 acceptance record](evidence/v1-m3-acceptance-status-v1.json). Historical
Story and handoff documents remain evidence, but they do not override that
record.

Status: **V1-M1 foundation and V1-M2 local authenticated shell are accepted; V1-M3 foundations and one real same-account Claude vertical are implemented, while milestone acceptance remains Blocked by the outstanding criteria in the active record.** A hostile browser resource initially invalidated M2's security acceptance; the [M2 audit correction](evidence/m2-audit-fixes.md) then passed the full local canonical rerun and independent post-audit QA. On 2026-09-21 the owner accepted the bounded historical M2 Red-first deviation; missing pre-fix Reds remain missing and universal `AC-TEST-001` is not retroactively Passed. This is not V1-M3 or V1 release approval. Installed native lifecycle, macOS, hosted, mutation, remaining live process, and release gates remain Not Run or Blocked as listed in the authoritative record.
Owner: Pavlo Sidelov <pavlo@sidelov.com>  
Last substantive review: 2026-09-23

This index is the entry point for product, architecture, engineering, and operations documentation. Requirements marked **Approved** reflect the project interview. Items marked **Discovery** require Milestone 0 evidence. Items marked **Deferred** are intentionally outside V1.

## Product

- [V1 specification](product/v1-specification.md): concise authoritative scope,
  capabilities, component inventory, boundaries, and implementation sequence.
- [Project charter](product/project-charter.md): problem, outcomes, stakeholders, constraints, and non-goals.
- [Requirements](product/requirements.md): traceable functional and non-functional requirements.
- [V1 acceptance criteria](product/v1-acceptance-criteria.md): the release gate for a complete V1.
- [Dashboard specification](product/dashboard-specification.md): information architecture, responsive behavior, and visual principles.

## Architecture

- [System architecture](architecture/system-architecture.md): context, containers, runtime, and dependency direction.
- [Module boundaries](architecture/modules.md): ownership, responsibilities, public surfaces, and forbidden dependencies.
- [Contracts and versioning](architecture/contracts-and-versioning.md): API, module, event, provider, and database compatibility policy.
- [Provider adapter contract](architecture/provider-adapter-contract.md): capability-driven provider integration model.
- [Data model](architecture/data-model.md): conceptual schema, invariants, provenance, retention, and privacy.
- [Security architecture](architecture/security.md): threat model and security controls.
- [Deployment architecture](architecture/deployment.md): native local deployment and future remote seam.

## API

- [API standards](api/api-standards.md): REST conventions, authentication, errors, pagination, schemas, and OpenAPI gates.

## Engineering

- [SDLC](engineering/sdlc.md): lifecycle, quality gates, definitions of ready and done, and release governance.
- [Testing strategy](engineering/testing-strategy.md): TDD and real-system verification without mocks or fakes.
- [Coding standards](engineering/coding-standards.md): Python, TypeScript, database, error, and logging conventions.
- [Dependency and license policy](engineering/dependency-and-license-policy.md): admission and continuous-review rules.
- [M1 React declaration admission](dependencies/m1-react-typecheck-admission.md): owner-approved exact development packages and residual release checks.
- [M1 audit-fix evidence](evidence/m1-audit-fixes.md): Red/Green/refactor and real-boundary reacceptance status.
- [M1 hosted CI evidence](evidence/m1-hosted-ci.md): clean-runner Red/Green, exact code commit, four hosted jobs, and residual boundaries.
- [M2 Story 1 evidence](evidence/m2-st-iam-001.md): independent bootstrap, migration, Argon2id, and real-PTY acceptance with deferred gates.
- [M2 API Story 4 evidence](evidence/m2-st-api-001.md): real IAM HTTP, offline API documentation, generated client, and independent acceptance.
- [M2 UI Story 5 evidence](evidence/m2-st-ui-001.md): accepted built-browser authentication, token settings, and real idle expiry; not the milestone exit gate.
- [M2 local recovery closure](evidence/m2-recovery-closure.md): real PTY/SQLite/service-lock verification of the approved forgotten-password command; owner-installed recovery remains Not Run.
- [M2 API Story 6 evidence](evidence/m2-st-api-002.md): hostile-origin HTTP/browser verification, historical failures, passing canonical local gate, and independent M2 acceptance.
- [M2 post-audit correction](evidence/m2-audit-fixes.md): hostile resource/SQLite regression, origin-proof contract decision, scanner correction, and historical TDD disposition.
- [M3 local release-gate decision](evidence/m3-local-release-gate-decision.md): detached M0 reviews are advisory; technical evidence and real boundaries remain mandatory.
- [M4 ST-FLEET-001 interim evidence](evidence/m4-st-fleet-001-interim.md): account and organization admin flows, one read-only Claude health observation, and remaining live blockers.
- [Claude dashboard polling delivery](evidence/claude-dashboard-polling.md): real service-owned five-minute collection, current quota refresh, preserved registry metadata, and restart cadence for one enrolled profile.
- [Account workspace redesign](evidence/account-workspace-redesign.md): automatic quota identity, calculated remaining allowance, real Claude process paths, and explicit unresolved process ownership.
- [Managed Claude connection progress](evidence/claude-managed-account-connection.md): three additional SDK accounts verified through isolated sign-in, enrollment, per-profile collection, and the real dashboard; native redraw correction and full fleet/M4 acceptance are tracked separately.
- [Dashboard Claude connection](evidence/claude-dashboard-connection.md): explicit browser connection controls, four owner-completed SDK/EAIS live gates, native quota redraw correction, a recovered first-read timeout, and remaining acceptance/M4 scope.
- [Compact dashboard and quota overview](evidence/dashboard-density-and-quota-overview.md): compact connection status and a main-page account/organization/state/remaining-quota table with real per-window percentages and bars.
- [M2 Argon2 admission](dependencies/m2-argon2-admission.md): approved exact Linux dependency graph, work profile, and platform limitations.
- [Configuration standard](engineering/configuration-standard.md): ownership, naming, precedence, secret classes, and compatibility.
- [Documentation standard](engineering/documentation-standard.md): required documentation and traceability.
- [Sub-agent runbook](engineering/subagent-runbook.md): module planning, ownership, synchronization, and handoff rules.
- [Review checklists](engineering/review-checklists.md): planning, boundary, contract, test, security, UI, dependency, and release gates.
- [Completion and automation gates](engineering/completion-and-automation-gates.md): executable completion claims and mandatory routine automation.

## Operations

- [Operations runbook](operations/runbook.md): installation, service, backup, recovery, authentication, diagnostics, and incidents.
- [M01 identity/access operator guide](modules/identity-access.md): fresh-only migration and local TTY bootstrap/recovery commands; native installed-service recovery remains Not Run.
- [P02 React dashboard module](modules/react-dashboard.md): authenticated shell, generated-client boundary, and current Story 5 browser coverage.
- [Milestone 0 discovery runbook](operations/milestone-0-discovery-runbook.md): safe, read-only provider feasibility work.
- [Live verification runbook](operations/live-verification-runbook.md): coordinated tests against real accounts.

## Governance

- [Roadmap](roadmap.md)
- [Superpowers implementation plans](superpowers/plans/README.md): eight
  milestones, 19 Epics, 44 traceable Stories, module coverage, and the
  import-ready GitLab backlog.
- [Approved M2 authenticated-shell plan](superpowers/plans/2026-09-19-agentmonitor-v1-m2-authenticated-shell.md): six serial Stories and the real HTTP/browser exit gate.
- [Module planning registry](plans/README.md): direct index to all 20 detailed
  module, adapter, boundary, persistence, deployment, discovery, foundation,
  and integration plans.
- [V1 planning program](plans/integration/v1-planning-program.md)
- [Exact contract adoption](plans/contract-adoption.toml)
- [Parallel ownership and exhaustive isolated write sets](plans/parallel-ownership.toml)
- [Milestone 0 execution plan](plans/discovery/m0-execution-plan.md)
- [Milestone 0 G0 gate evidence](plans/discovery/m0-g0-gate-evidence.md)
- [Milestone 0 G0 approval record](plans/discovery/m0-g0-approval.toml)
- [Milestone 0 G1 control specification](plans/discovery/m0-g1-control-specification.md)
- [Milestone 0 G1 minimal JSON Schema](plans/discovery/m0-g1-record.schema.json)
- [Milestone 0 G1 contract test evidence](plans/discovery/m0-g1-contract-test-evidence.md)
- [Milestone 0 G1 implementation approval](plans/discovery/m0-g1-implementation-approval.toml)
- [Milestone 0 scanner admission candidate](plans/discovery/dependencies/gitleaks-admission.md)
- [Milestone 0 Python jsonschema admission candidate](plans/discovery/dependencies/python-jsonschema-admission.md)
- [Proposed contract register](plans/contract-register.md)
- [Planning backlog](plans/planning-backlog.md)
- [CS-0 draft-integrity review](plans/integration/cs0-draft-integrity-review.md)
- [CS-1 independent final audit](plans/integration/cs1-final-readiness-audit.md)
- [Synchronized plan/control baseline](plans/plan-baseline.toml)
- [CS-1 full-plan synchronization record](plans/integration/cs1-full-plan-synchronization.md)
- [CS-1 planning-gate evidence](plans/integration/planning-gate-evidence.md)
- [Traceability matrix](traceability.md)
- [Risk register](risk-register.md)
- [Glossary](glossary.md)
- [Architecture decision records](decisions/README.md)
- [Local milestone release-gate policy](decisions/0013-local-milestone-release-gates.md)
- [Reusable templates](templates/README.md)

## Precedence

When documents conflict, use this order:

1. Explicit current user direction.
2. `AGENTS.md` non-negotiable invariants.
3. Accepted ADRs.
4. Approved product requirements and V1 acceptance criteria.
5. Architecture and engineering standards.
6. Module plans and operational procedures.

Resolve contradictions through an ADR or requirements change; do not silently choose one interpretation.
