---
name: agentmonitor-engineering
description: Plan, implement, review, verify, or operate AgentMonitor work under the project's module-isolation, versioned-contract, real-system TDD, security, documentation, and sub-agent handoff rules. Use for any AgentMonitor product, architecture, provider adapter, API, UI, database, test, deployment, or runbook task.
---

# AgentMonitor engineering

## Start with authority and scope

1. Read the repository-root `AGENTS.md` completely.
2. Read `docs/README.md`, then the requirements/acceptance IDs governing the task.
3. Identify whether the user authorized discussion, discovery, planning, implementation, review, verification, or operations. Do not infer implementation authority from a planning/review request.
4. Identify exactly one primary owning module or explicitly escalate an ownership gap.
5. Confirm an approved module/change plan and contract versions exist before production implementation.

## Route required reading

Always read:

- `docs/engineering/sdlc.md`
- `docs/engineering/testing-strategy.md`
- `docs/engineering/coding-standards.md`
- `docs/engineering/configuration-standard.md`
- `docs/engineering/documentation-standard.md`
- `docs/engineering/review-checklists.md`
- `docs/traceability.md`
- `docs/risk-register.md`

Then read the smallest complete task-specific set:

- Module/domain: `docs/architecture/modules.md`, `contracts-and-versioning.md`, and `data-model.md`.
- Provider/platform adapter or discovery: provider adapter contract, security architecture, Milestone 0 discovery runbook, and live-verification runbook.
- API/IAM: API standards, security architecture, and relevant module contracts.
- UI: dashboard specification, API standards, accessibility/review sections, and generated-client contract.
- Persistence/migrations: data model, deployment, operations runbook, backup/recovery, and owning module plan.
- Dependency/tooling: dependency-and-license policy and relevant ADRs.
- Delegated work: sub-agent runbook and the applicable templates under `docs/templates/`.

Read linked governing material yourself; do not delegate interpretation of project instructions.

## Enforce hard invariants

- Use real provider/accounts, real local processes/platforms, real SQLite, real HTTP service, and real built-browser behavior for external-boundary claims.
- Never use mocks, fakes, stubs, emulators, recordings/replays, demo accounts, seeded telemetry, placeholder values, hardcoded passing tests, or test-only production paths.
- Constructed inputs are allowed only for pure deterministic domain tests with no I/O.
- Record meaningful Red, Green, and post-refactor evidence. `Failed`, `Blocked`, and `Not Run` never mean `Passed`.
- Never inspect/persist prompts, responses, tool/source content, arbitrary environments, credential values, OTP/MFA data, or secret-bearing raw payloads.
- Never modify/log out/relocate a default provider profile or control a running agent in V1.
- Keep provider/OS/framework/persistence/UI details out of domain modules.
- Never bypass a module contract by importing internals or querying its tables.
- Treat API, event, provider, configuration, and database changes as versioned contracts.
- Admit no dependency before security, maintenance, necessity, direct/transitive license, SBOM, and notices review.
- Do not create external resources, push/release, send messages/email, change provider state, or perform destructive operations without explicit authority.

## Execute the lifecycle

### Discovery

Use the provider capability template and Milestone 0 runbook. Prefer official documented interfaces, perform read-only inspection, record provenance/confidence/version/scope, and accept `Unsupported` as a valid result. Discovery does not authorize production implementation.

### Planning

Copy the module-plan or change-plan template. Map requirements through contracts to test/scenario IDs. Specify ownership, allowed/forbidden imports and paths, data, security, operations, real verification, documentation, risks, rollback, and stop conditions. Resolve cross-module contract changes before parallel work.

### Implementation

Work only inside the approved scope. For each increment: create the meaningful failing test, run and retain sanitized Red evidence, make the minimum production change, run Green, refactor with tests green, and update docs/contracts in the same change. Stop on boundary, secret, destructive migration, live-auth, dependency, or provider-behavior surprises.

### Review and verification

Use `docs/engineering/review-checklists.md`. Inspect artifacts and commands; do not trust completion claims. Verify the exact real boundary claimed. Coordinate owner-performed login/MFA/OTP and live provider conditions through the live-verification runbook.

### Handoff

Complete the test-evidence and sub-agent-handoff templates. Include requirements, contract versions, files, compatibility/migrations, Red/Green/refactor, all real-boundary results, every Blocked/Not Run item, security/privacy/license/operations effects, risks, and exact next integration step. Keep evidence sanitized.

## Preserve truthful uncertainty

Do not invent provider behavior, metric precision, reset semantics, account correlation, commands, configuration keys, or pass results. Mark unresolved facts as Discovery, Unknown, Unsupported, Blocked, or Not Run, with the evidence needed to resolve them.

