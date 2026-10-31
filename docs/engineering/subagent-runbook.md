# Independent sub-agent runbook

## Purpose

This runbook governs future planning and implementation by independent agents. The strategy is one primary agent per isolated module, synchronized through approved contracts and a root integration steward. Parallelism is earned by stable boundaries; it is not used to hide unresolved architecture.

## Roles

### Root/integration steward

- owns the global requirements, architecture, contract registry, traceability, and release gate;
- assigns one module and explicit directory scope per sub-agent;
- resolves cross-module conflicts and approves contract changes;
- reviews actual artifacts/evidence rather than trusting completion claims;
- coordinates user participation for live tests;
- integrates modules only after synchronization gates.

### Module planning agent

- reads all governing docs itself;
- creates a detailed implementation plan for exactly one module;
- defines internal design without changing other modules;
- identifies contract gaps rather than inventing private coupling;
- maps requirements to real tests and operations;
- does not implement during planning unless separately authorized.

### Module implementation agent

- works only from an approved plan and contract version;
- follows red-green-refactor;
- edits only assigned module, its owned migrations/tests/docs, and explicitly permitted generated artifacts;
- escalates contract changes before crossing boundaries;
- provides the required handoff evidence.

### Contract/integration reviewer

- independently verifies dependency direction, schemas, compatibility, generated client, migrations, idempotency, and cross-module behavior;
- does not rewrite the module implementation while reviewing unless explicitly reassigned.

### Live-verification operator

- root agent plus owner;
- owner controls login/MFA/OTP/secrets;
- executes real provider/platform scenario matrix;
- records sanitized Passed/Failed/Blocked evidence.

## Mandatory task packet

Every delegated module task includes:

- objective and non-goals;
- requirement and acceptance IDs;
- owning module and allowed paths;
- forbidden modules/paths/imports;
- consumed/published contract names and versions;
- data/table/migration ownership;
- security/privacy/secrets constraints;
- TDD and live-verification scenarios;
- documentation/runbook outputs;
- dependencies permitted and admission status;
- expected handoff format;
- stop/escalation conditions.

Use [the module-plan template](../templates/module-plan-template.md) and [sub-agent handoff template](../templates/subagent-handoff-template.md).

## Required reading by task type

All agents read `AGENTS.md`, documentation index, requirements IDs, SDLC, testing strategy, coding standards, and this runbook.

- Domain/module work: modules, contracts/versioning, data model.
- Provider work: provider adapter contract, security, discovery/live runbooks.
- API work: API standards, IAM/security, contracts.
- UI work: dashboard specification, API standards, accessibility requirements.
- Persistence/migration work: data model, contracts, deployment, backup/recovery.
- Operations work: deployment, security, operations runbook.

Agents cannot delegate reading/interpreting these governing documents to another agent.

## Planning sequence

1. Root freezes a baseline contract proposal and assigns modules.
2. Independent module agents produce plans without editing shared contracts.
3. Root compares plans for gaps, duplicated ownership, circular dependencies, data leakage, and incompatible assumptions.
4. Contract synchronization review resolves all shared changes.
5. Contract versions and module plans are approved.
6. Implementation waves begin only for modules whose contracts are stable.

## Implementation waves

Suggested dependency order:

1. Shared contract primitives and repository foundation.
2. Identity/access and registry.
3. Provider protocol and collection control.
4. Capacity/runtime modules plus platform/provider adapters.
5. Alerting and operations.
6. API boundary/generated client.
7. UI feature modules.
8. Full integration/live verification/hardening.

Within a wave, agents may work in parallel only when they do not edit the same contract, migration chain, generated file, or shared module.

## Synchronization protocol

### Start sync

Root confirms current branch/worktree state, approved plan/version, file ownership, dependencies, and no conflicting agent.

### Contract sync

If implementation reveals a missing/change contract:

1. Stop the affected cross-boundary work.
2. Submit a contract-change proposal with consumers and compatibility impact.
3. Root notifies every affected module owner.
4. Review/version/ADR occurs as required.
5. Regenerate artifacts and update plans.
6. Resume only after approval.

Do not solve a contract gap through direct table access, deep import, duplicated type, or hidden provider field.

### Completion sync

Agent supplies evidence packet. Root reviews diff, test commands/results, live-test state, contract/API/migration diffs, docs, and security/license impact before marking complete.

## File and data discipline

- Existing/unrelated user changes are preserved.
- Destructive commands and broad cleanup are prohibited without explicit authorization.
- No agent reads or prints `.env` values, provider credentials, or real content.
- No agent stores secret-bearing command output in chat or artifacts.
- Generated files are changed only through their source generator.
- Shared database migration ordering is allocated centrally.
- A sub-agent cannot create external GitLab resources, push, release, send email, or mutate provider accounts unless explicitly authorized for that action.

## Testing discipline

- Sub-agents do not replace unavailable real systems with simulations.
- Pure tests use constructed inputs only for side-effect-free domain rules.
- Application/persistence/API/browser tests use real components.
- Provider/platform live tests are scheduled with the root and owner.
- Blocked tests remain visible in handoff.
- A module is not complete because code compiles or a narrow unit suite passes.

## Stop and escalate conditions

Stop work and contact root when:

- contract meaning/version must change;
- another module/table/path must be edited unexpectedly;
- a requirement conflicts with security/privacy/testing rules;
- a provider requires an undocumented/private mechanism not approved;
- a secret or sensitive content may have been exposed;
- migration can destroy/irreversibly transform data;
- dependency has an unapproved license or supply-chain risk;
- real test requires owner authentication/credits/disruptive state;
- existing user changes overlap assigned files;
- observed behavior contradicts the specification.

## Handoff minimum

- concise outcome and limitations;
- requirement/acceptance coverage;
- module/contract versions;
- files changed;
- red/green/refactor evidence;
- real database/API/browser/platform/provider evidence;
- Blocked/Not Run scenarios;
- migration and recovery evidence;
- security/privacy/license review;
- documentation updated;
- known risks and exact next integration step.

Claims without inspectable evidence are not accepted.

## Review independence

Critical skills/modules may receive an independent review agent with a realistic task and only necessary artifacts. The reviewer is not told the expected conclusion. Review occurs in a non-destructive scope and cannot use fake provider systems as forward-testing evidence.
