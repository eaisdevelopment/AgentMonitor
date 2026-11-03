# AgentMonitor documentation index

<!-- agentmonitor-milestone-status:v1 milestone=V1-M3 lifecycle=active status=passed authority=M3-ACCEPTANCE-2026-10-03-01 -->
<!-- agentmonitor-milestone-status:v1 milestone=V1-M4 lifecycle=active status=passed authority=M4-ACCEPTANCE-2026-10-07-01 -->

The machine-readable
[V1 implementation-status overlay](evidence/v1-implementation-status-v1.json)
is the current delivery index. It is separate from the frozen import backlog
and records implementation, canonical gate, acceptance, and dependency state
independently. The authoritative V1-M3 acceptance status is **Passed** in the
[active V1-M3 record](evidence/v1-m3-acceptance-status-v3.json). Historical
Story, handoff, and superseded acceptance documents remain evidence, but they
do not override that record. V1-M4 is also **Passed and owner-accepted** in the
[active V1-M4 record](evidence/v1-m4-acceptance-status-v1.json).

Current program state:

- **V1-M1:** local foundation accepted; historical gate evidence.
- **V1-M2:** local authenticated shell accepted after its recorded correction;
  historical gate evidence.
- **V1-M3:** accepted for one real Claude vertical. The safe current-revision
  gate passed every required lane, and the owner countersigned the result and
  accepted the bounded historical TDD deviation without waiving future TDD.
- **V1-M4:** accepted in full at implementation revision `9dbb765`. Its
  current-revision gate passed six distinct Claude identities in two
  organizations, six fresh post-restart quota/history lineages, the guarded
  current-process witness, and every required technical, browser, and local
  quality lane with zero skips and zero registry mutations.
- **V1-M5:** the bounded Codex implementation and `AUTO-M5-EXIT` passed on
  clean deployed revision `ab1408b` on 30 October 2026. The result covers
  three verified accounts, one owner-recorded unavailable account, five
  representative processes, the recovered alert lifecycle, and the required
  browser and technical checks. The [completion record](evidence/m5-completion-2026-10-30.md)
  explains the evidence. The owner accepted M5 on 30 October 2026; see the
  [acceptance record](evidence/m5-owner-acceptance-2026-10-30.md).
- **V1-M6:** In progress and deployed locally. The canonical run at `894f092`
  passed all shared checks and the real one-account balance/history comparison,
  but remains unclosed for missing model-host, organization scope and natural
  recovery evidence. See the [current checkpoint](evidence/m6-delivery-checkpoint-2026-11-03.md).
- **V1-M7 and V1-M8:** Planned; their canonical gates have not run.

The approved [M3 scope correction](evidence/m3-scope-correction-2026-10-02.md)
moves fleet, other-provider, and release-wide outcomes to V1-M4 through V1-M8.
The [M3 current-gate receipt](evidence/m3-current-gate-receipt-2026-10-03.json)
and owner disposition records close the blockers retained by the historical
[M3 closure audit](evidence/m3-closure-audit-2026-10-01.md).
Owner: Pavlo Sidelov <pavlo@sidelov.com>  
Last substantive review: 2026-10-27

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
- [Historical M4 ST-FLEET-001 interim evidence](evidence/m4-st-fleet-001-interim.md): account and organization admin flows, one read-only Claude health observation, and the blockers that remained at that point.
- [M4 completion evidence](evidence/m4-completion.md): all six M4 Stories, installed migration, six distinct monitored identities, fresh post-restart lineage, browser verification, and owner-accepted revision-bound closure.
- [M4 current-gate receipt](evidence/m4-current-gate-receipt-2026-10-07.json): sanitized create-once result for the exact accepted implementation revision.
- [M4 owner countersignature](evidence/m4-owner-live-countersignature-2026-10-07.md): explicit acceptance of the complete approved M4 scope.
- [M5 Codex slice change](plans/integration/m5-codex-slice-change.md):
  exact Codex 0.160.0 managed-profile, quota, process, API/UI, and completion-gate scope.
- [Codex 0.160.0 discovery evidence](evidence/m5-codex-0.160.0-discovery.md):
  official-source, installed-schema, isolated app-server, and safe process findings that bind the M5 implementation.
- [Codex CLI adapter](adapters/codex.md): exact-version managed login, identity,
  quota, process, operations, privacy, and completion boundaries for V1-M5.
- [Claude dashboard polling delivery](evidence/claude-dashboard-polling.md): real service-owned five-minute collection, current quota refresh, preserved registry metadata, and restart cadence for one enrolled profile.
- [Claude Code 2.1.289 admission evidence](evidence/claude-2.1.289-admission.md):
  exact-version quota and managed-auth compatibility, bounded model-card
  omission, separate OTLP gating, and its historical admission-checkpoint
  preflight. The later M4 receipt records the successful post-restart gate
  without rewriting that hash-bound evidence.
- [Account workspace redesign](evidence/account-workspace-redesign.md): automatic quota identity, calculated remaining allowance, real Claude process paths, and explicit unresolved process ownership.
- [Historical managed Claude connection progress](evidence/claude-managed-account-connection.md): three additional SDK accounts verified through isolated sign-in, enrollment, per-profile collection, and the real dashboard.
- [Historical dashboard Claude connection increment](evidence/claude-dashboard-connection.md): explicit browser connection controls, four owner-completed SDK/EAIS live gates, native quota redraw correction, and a recovered first-read timeout.
- [Compact dashboard and quota overview](evidence/dashboard-density-and-quota-overview.md): compact connection status, organization and provider filters, interactive account sorting, low-quota warnings, and collection history on its own page.
- [Trusted LAN dashboard change](plans/integration/trusted-lan-dashboard-change.md): owner-approved private interface/subnet listener, HTTP browser admission, and the real completion gate.
- [Dashboard 24-hour session policy change](plans/integration/dashboard-session-24h-change.md):
  owner-approved fixed 24-hour browser-session lifetime with existing IAM,
  CSRF, revocation, and transport protections retained.
- [Trusted LAN dashboard evidence](evidence/trusted-lan-dashboard.md): real dual listeners, IAM protections, LAN browser admin behavior, and pending firewall/second-computer verification.
- [Live agent account associations](plans/integration/live-agent-account-association-change.md): approved bounded manual terminal identity and guarded process drill-down.
- [Duplicate identity overview correction](plans/integration/duplicate-account-overview-change.md): one quota row for fresh identical observed identities, with separate connection review.
- [Live account agents progress](evidence/live-account-agents.md): real terminal detection, HTTP guards, duplicate presentation, and a verified owner-authorized process/account link after restart.
- [M2 Argon2 admission](dependencies/m2-argon2-admission.md): approved exact Linux dependency graph, work profile, and platform limitations.
- [M6 Ollama Secret Service admission](dependencies/m6-ollama-secret-service-admission.md):
  historical dependency review, superseded by the owner's protected `.env` decision.
- [Configuration standard](engineering/configuration-standard.md): ownership, naming, precedence, secret classes, and compatibility.
- [Documentation standard](engineering/documentation-standard.md): required documentation and traceability.
- [Sub-agent runbook](engineering/subagent-runbook.md): module planning, ownership, synchronization, and handoff rules.
- [Review checklists](engineering/review-checklists.md): planning, boundary, contract, test, security, UI, dependency, and release gates.
- [Completion and automation gates](engineering/completion-and-automation-gates.md): executable completion claims and mandatory routine automation.

- [M6 local Ollama catalog intermediate evidence](evidence/m6-ollama-local-preview-2026-11-01.md): approved local slice, narrow real-source/API/browser checks, and explicit outstanding M6 requirements.

## Operations

- [Operations runbook](operations/runbook.md): installation, service, backup, recovery, authentication, diagnostics, and incidents.
- [M01 identity/access operator guide](modules/identity-access.md): fresh-only migration and local TTY bootstrap/recovery commands; native installed-service recovery remains Not Run.
- [P02 React dashboard module](modules/react-dashboard.md): authenticated
  operational shell, generated-client boundary, and current browser coverage.
- [Milestone 0 discovery runbook](operations/milestone-0-discovery-runbook.md): safe, read-only provider feasibility work.
- [Live verification runbook](operations/live-verification-runbook.md): coordinated tests against real accounts.

## Governance

- [Roadmap](roadmap.md)
- [Current V1 implementation status](evidence/v1-implementation-status-v1.json):
  evidence-bound delivery, gate, acceptance, and dependency state for all eight
  milestones and 44 Stories.
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
