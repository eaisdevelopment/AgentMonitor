# AgentMonitor agent instructions

These instructions apply to every human or coding agent working anywhere in this repository.

## Start here

1. Read [docs/README.md](docs/README.md).
2. Read the documents routed for the task in [.agents/skills/agentmonitor-engineering/SKILL.md](.agents/skills/agentmonitor-engineering/SKILL.md).
3. Identify the owning module and its published contracts before proposing changes.
4. Do not implement production code until the relevant module plan has been approved.

## Non-negotiable invariants

- Use real systems and real provider data at every external boundary. Do not use mocks, fakes, stubs, emulators, recorded provider responses, demo accounts, seeded telemetry, or placeholder dashboard values.
- Constructed values are allowed only in pure domain tests whose inputs and outputs have no I/O behavior.
- Follow red-green-refactor TDD. A changed behavior must have evidence that its test failed for the expected reason before production code made it pass.
- Never claim a blocked, skipped, unavailable, or unexecuted live test passed.
- Never modify, log out, relocate, or rewrite a user's default Claude, Codex, or Ollama profile.
- Provider-owned state is read-only unless a separately approved, official authentication flow explicitly writes to an AgentMonitor-managed profile.
- Do not read or persist prompts, responses, source-code content, arbitrary process environment values, OAuth tokens, API keys, passwords, or one-time codes.
- Owner-approved M6 exception (2 November 2026): the AgentMonitor runtime may store an owner-provided Ollama API key in an OS Secret Service item and read it transiently only to authenticate the approved Ollama balance request. Coding agents must not view keys; keys must not enter chat, browser, logs, source, database, evidence, or command arguments. This exception does not authorize reading or altering provider profiles.
- Do not put secrets in source, tests, fixtures, logs, diagnostics, screenshots, documentation, commits, or chat. AgentMonitor-managed secrets belong in `.env`; provider OAuth credentials remain provider-managed.
- The UI consumes only the versioned API. It must not import backend internals, read the database, or inspect provider files directly.
- Provider-specific behavior must remain in provider adapters. The domain must not import provider SDKs, CLI packages, FastAPI, SQLAlchemy, operating-system APIs, or UI code.
- Cross-module changes require a contract-impact assessment. Breaking public changes require a versioned migration path and an ADR.
- Do not add a dependency until its license, maintenance, security, necessity, and transitive dependency impact are documented and approved.
- V1 is read-mostly. It must not kill, restart, interrupt, route, or mutate running agent processes.

## Required quality evidence

Every implementation handoff must name:

- requirement and acceptance-criterion IDs;
- module and contract versions affected;
- tests added and their red/green evidence;
- live verification performed, blocked, or still required;
- security, privacy, migration, license, and documentation impact;
- files changed and any follow-up work.

Use the templates under [docs/templates](docs/templates). The full process is defined in [the SDLC](docs/engineering/sdlc.md) and [sub-agent runbook](docs/engineering/subagent-runbook.md).

## Completion and automation gate

- Never report a requested scope as complete, done, ready, implemented, or validated unless its canonical executable completion gate passes against the real checkout/environment.
- A framework, backlog, registry entry, future task, or partial module set is not a substitute for a required artifact.
- If a gate is red, absent, skipped, or narrower than the claim, report an intermediate status and continue working; do not make the owner discover missing scope.
- Every repeatable routine—including documentation validation, planning validation, tests, quality checks, Git preflight, builds, migrations, deployment, backup, restore, and release—must be codified as a canonical fail-closed command before its dependent lifecycle phase is ready.
- Follow [the completion and automation gates](docs/engineering/completion-and-automation-gates.md).

# Compact instructions

When compacting, preserve exact file paths, error messages verbatim,
test commands, stated constraints, and the current task list.
Summarize decisions as choice | reason | rejected alternative.
Drop file contents that have already been read and conversational filler.
