# Software development lifecycle

## Purpose

This lifecycle is the mandatory path from an idea to a released AgentMonitor behavior. It optimizes for correctness, traceability, independent module ownership, and truthful live-provider evidence rather than speed of code production.

## Owner authority and delivery

The owner's requested outcome and applicable governing instructions control the
work. An agent's plan, task list, gate, version label, interpretation, or
preference does not acquire authority merely because the agent wrote it.

- Check existing owner approvals and their scope before asking again. An
  approval remains valid for the scope approved; routine implementation and
  documentation changes inside that scope do not require a new approval just
  because a version, commit, artifact, or test result changed. Respect an
  explicit revision-bound approval without inventing such a condition. An actual
  requirement for a new approval must identify its source and explain why it
  applies to the proposed change.
- Do not invent a mandatory gate, approval, prerequisite, or scope change.
  Apply the requirements that actually govern the task. When a required
  executable routine is missing or broken, implement or repair it within the
  authorized scope and continue other independent work; its absence is not a
  reason to repeatedly ask the owner to perform mechanical steps.
- For a claimed blocker, identify the actual rule, failed command or external
  condition and the evidence. Distinguish a requirement from an assumption or
  preferred approach. Ask the owner only for information, an action or a
  decision that is genuinely necessary and cannot be obtained within the
  existing authority; prepare the concrete choice before asking.
- Review the requested outcome against the real target, not only internal
  artifacts. State whether a change is local, committed, pushed, deployed or
  publicly accessible, based on verification of the relevant target. Do not
  describe a locally staged result as an external result. Disclose material
  incompleteness and failures without calling them passed.
- When the owner reports a broken or missing outcome, investigate that outcome
  first. Correct mistaken claims and fix the problem within authorized scope;
  do not treat previous plans, historical receipts or agent status reports as
  proof that the current user-visible result works.

These directions do not waive the approved module plan, security, test or
completion requirements in `AGENTS.md`. They do not themselves enforce agent
tool calls; a reviewer must inspect actual actions and evidence.

## Lifecycle states

```text
Proposed
  -> Discovered
  -> Specified
  -> Architecture Approved
  -> Module Planned
  -> Test Designed
  -> Implementing (Red -> Green -> Refactor)
  -> Integrated
  -> Live Verified
  -> Release Ready
  -> Released
  -> Operated / Reviewed
```

A state may move backward when evidence invalidates an assumption. No state is inferred from elapsed time or code volume.

Every state transition requires its canonical executable gate from the
[completion and automation standard](completion-and-automation-gates.md). Prose,
code volume, a partial artifact set, or an agent's confidence cannot substitute
for a green gate. A missing gate leaves the transition Not Ready.

## Phase 0 — Discovery

Required for unstable external behavior, provider formats, authentication, OS integration, and unknown performance.

Outputs:

- question/hypothesis list;
- read-only method and safety boundary;
- real environment/version inventory;
- sanitized evidence;
- capability/constraint matrix;
- decision to support, experiment, defer, or reject;
- requirement/architecture updates.

Discovery code, if any, is not production code by default. It cannot be promoted without normal design and TDD.

## Phase 1 — Requirement and acceptance definition

Every change has:

- requirement ID and owner-visible outcome;
- in-scope and out-of-scope statements;
- observable acceptance criteria;
- privacy/security classification;
- data/retention impact;
- provider/platform assumptions;
- failure and unavailable behavior;
- documentation/operation impact.

Ambiguous external behavior is marked Discovery, not silently specified as fact.

## Phase 2 — Architecture and contract impact

Determine:

- owning module and consumers;
- public/internal/provider/event/database contracts affected;
- compatibility and version changes;
- dependency direction and forbidden imports;
- persistence ownership and migration path;
- threat-model changes;
- performance/reliability expectations;
- dependency/license impact;
- rollout/recovery strategy.

Breaking changes require an ADR before implementation.

## Phase 3 — Independent module plan

One planning sub-agent owns one module plan using the module-plan template. The plan includes exact responsibilities, internal design, contract use, data, test scenarios, live-verification needs, operations, documentation, and work sequence.

Module plans are reviewed together at a contract synchronization gate before any parallel implementation. Plans may change internals independently after that gate, but contract changes return to synchronization.

The complete V1 planning set is enumerated in
`docs/plans/planning-catalog.toml`. Planning is not complete until the real
checkout passes `python3 tools/planning/validate_plans.py --stage synchronized`.
A backlog entry or planning framework does not satisfy a required module-plan
artifact.

## Phase 4 — Test design

Before production code:

- map acceptance criteria to test scenarios;
- classify each as pure domain, real local stack, migration, platform, or live provider;
- identify required real account/system state and owner interaction;
- define red failure expected before implementation;
- define prohibited simulated substitutes;
- specify test evidence and cleanup;
- mark naturally unavailable scenarios as Blocked rather than invent them.

## Phase 5 — TDD implementation

For each behavior:

1. **Red:** write the smallest meaningful test at the correct real boundary and run it. Record that it fails for the expected missing/incorrect behavior, not an unrelated setup error.
2. **Green:** implement the minimum production behavior that satisfies the test and contract.
3. **Refactor:** improve names, boundaries, duplication, errors, and performance while all relevant tests remain green.
4. Update contract/documentation alongside code, not at the end.
5. Commit/review in small coherent changes.

Provider adapters execute this loop with coordinated real accounts. They do not substitute recorded responses or fake servers.

## Phase 6 — Integration

- Apply real migrations to a fresh database.
- Start the real FastAPI service and built UI.
- Exercise generated client against the server.
- Verify event/outbox/idempotency behavior.
- Check module-boundary and contract compatibility gates.
- Run real browser workflows.
- Verify one-module failure does not cascade.
- Inspect sanitized logs and diagnostics.

## Phase 7 — Live verification

Use the live-verification runbook with the owner for provider authentication, quota/budget reconciliation, re-authentication, installed CLI behavior, and real process/session discovery.

Results are Passed, Failed, Blocked, or Not Run. There is no assumed pass. Interactive credentials remain owner-controlled.

## Phase 8 — Release readiness

Required reviews:

- requirements/traceability;
- architecture/contracts/migrations;
- test integrity and live evidence;
- security/privacy/secrets;
- dependency licenses and SBOM;
- accessibility/responsiveness;
- performance/reliability;
- documentation/runbooks;
- backup/recovery/upgrade;
- known limitations and blocked scenarios.

The V1 release uses the V1 acceptance criteria as its gate.

## Phase 9 — Operate and learn

- Monitor local health, collector failures, stale data, backup status, and database size.
- Record incidents and root causes.
- Convert demonstrated gaps into requirements/ADRs, not ad hoc permanent exceptions.
- Reverify provider adapters after provider/CLI version changes.
- Review dependencies and licenses continuously.

## Definition of Ready for implementation

A module/change is ready only when:

- requirements and acceptance criteria are approved;
- owner module and boundaries are unambiguous;
- contracts are published/versioned;
- discovery questions are resolved or explicitly deferred;
- security/privacy/dependency impacts are reviewed;
- real-test resources and owner interaction are available;
- migration/recovery approach exists where relevant;
- module plan is approved;
- no conflicting agent owns the same files/contract.
- the canonical planning and automation readiness gates pass for the claimed scope.

## Definition of Done

- Acceptance criteria pass with evidence.
- Red-green-refactor evidence exists.
- Required pure, real-stack, platform, migration, browser, and live suites pass.
- Blocked/not-run tests are explicit and do not hide behind a green status.
- Contracts and generated artifacts are current.
- Migrations, backup, recovery, and operations are validated as applicable.
- Threat model, dependency/license review, and documentation are current.
- No secrets/content/test artifacts leaked.
- Module owner and integration reviewer handoffs are complete.
- Traceability matrix is updated.
- the canonical completion command passes against the real target environment,
  and its reported scope is no narrower than the completion claim.

## Routine automation

Documentation checks, planning checks, tests, quality controls, Git preflight,
builds, migrations, deployment, backup, restore, and release are repository-owned
automation. Each owning plan must provide the canonical fail-closed command before
its dependent phase becomes ready. Manual runbook steps remain only for explicit
owner authority, credentials/MFA, live-provider observations, or material state
changes and are invoked by the automation at a named checkpoint.

## Change control

### Small compatible change

May use a focused change plan; still requires TDD, contract diff, and documentation impact.

### New capability/module

Requires module plan, architecture review, threat/data review, full test mapping, and operational plan.

### Breaking contract or destructive migration

Requires ADR, compatibility/migration window, consumer plan, verified backup/recovery, and explicit approval.

### Emergency security fix

May compress review order but cannot remove testing, secret handling, incident recording, or post-change verification. Document the exception and follow-up.

## GitLab workflow

- Protected default branch.
- Merge request per coherent change.
- Requirement/module identifiers in title or description.
- Required pipeline and reviews before merge.
- No secrets in GitLab variables unless protected/masked and specifically needed; interactive provider OAuth remains local.
- GitLab-hosted runners run deterministic suites. Live-provider verification runs locally with sanitized reports.
- A successful hosted pipeline does not imply live-provider verification passed.

Branch naming and commit conventions are finalized in the repository foundation module plan, then documented without rewriting shared history casually.

## Release versioning

Use semantic product versions after the first release. Pre-release specifications and discovery may use milestone labels. Release notes list contract changes, migrations, provider compatibility, security changes, known limitations, and live-verification matrix.
