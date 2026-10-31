# AgentMonitor V1 Implementation Program

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the local Linux-first AgentMonitor V1 through eight traceable, independently gated milestones.

**Architecture:** Eight domain modules remain isolated behind versioned contracts, provider and operating-system behavior stays in adapters, FastAPI is the only UI boundary, and SQLite implements module-owned repository ports. Vertical slices add one real provider at a time after the authenticated local shell is operational.

**Tech Stack:** Python, FastAPI, OpenAPI 3, SQLite/Alembic, React/TypeScript, generated API client, Playwright, native Linux user service.

**Spec:** `docs/product/v1-specification.md`

## Global Constraints

- Real systems and real provider data are required at every external boundary; mocks, fakes, stubs, recordings, demo accounts, seeded telemetry, and placeholder dashboard values are forbidden.
- Every changed behavior follows Red → Green → Refactor with retained sanitized evidence.
- V1 never automates login/logout, mutates a default provider profile, injects input, signals/restarts agents, routes work, or fails over. A separately approved, owner-driven official reauthentication flow may write only an AgentMonitor-managed profile after M0 proves isolation and the owner controls browser/device/MFA interaction.
- Prompts, responses, tool activity, source content, arbitrary environments, credentials, OTP/MFA values, and raw secret-bearing payloads are never read or persisted.
- The UI consumes only the generated `/api/v1` client; it never reads SQLite, provider files, or backend internals.
- Domain modules do not import FastAPI, SQLAlchemy, provider SDK/CLI packages, operating-system APIs, or UI code.
- Dependencies require approved license, security, maintenance, necessity, transitive-impact, SBOM, and notice evidence before installation.
- Linux is the V1 execution target; macOS remains contract-compatible but live verification is visibly Blocked until a real Mac is available.
- Secrets remain in owner-only `.env` or provider-managed stores and never enter Git, logs, tests, screenshots, diagnostics, or chat.
- A milestone is complete only when its canonical gate passes; Blocked and Not Run evidence remains visible.

---

## Tracker hierarchy

GitLab mapping is one-to-one:

- each `V1-M*` record is a Milestone;
- each `EPIC-*` record is an Epic;
- each `ST-*` task in a milestone plan is a Story represented by a GitLab Issue;
- requirement, contract, test, and dependency IDs are issue labels/links, not duplicated prose;
- completion is derived from acceptance evidence, never from issue closure alone.

Actual GitLab objects are created only after the project ID and protected API
token are configured. Until then, these repository plans are the authoritative,
import-ready tracker source.

## Milestones

| Milestone | Outcome | Epics | Entry | Exit gate |
|---|---|---|---|---|
| `V1-M1` | Reproducible foundation and real local-stack skeleton | `EPIC-FND-01`, `EPIC-CONTRACT-01`, `EPIC-DATA-01` | Specification and plans synchronized | Real file SQLite migration, running FastAPI/OpenAPI, built UI, CI/tooling gates |
| `V1-M2` | Authenticated local dashboard shell | `EPIC-IAM-01`, `EPIC-API-01`, `EPIC-UI-01` | `V1-M1` | Real login/session/CSRF/API-token/browser flow on loopback |
| `V1-M3` | One end-to-end real Claude vertical slice | `EPIC-REG-01`, `EPIC-PROV-01`, `EPIC-CLA-01`, `EPIC-OBS-01` | `V1-M2`, required Claude discovery | One account reconciled through adapter → domains → API → browser |
| `V1-M4` | Claude fleet, history, alerts, and operations | `EPIC-FLEET-01`, `EPIC-ALERT-01`, `EPIC-OPS-01` | `V1-M3` | Six intended accounts or explicit owner-unavailable records; dashboard alerts validated |
| `V1-M5` | Codex vertical slice and fleet | `EPIC-CDX-01` | `V1-M3`, required Codex discovery | Four intended accounts and representative running processes reconciled |
| `V1-M6` | Ollama local/cloud vertical slice | `EPIC-OLL-01` | `V1-M3`, required Ollama discovery | Two intended identities and local/cloud resource pools represented separately |
| `V1-M7` | API usage, cost, credit, and budget monitoring | `EPIC-BUDGET-01` | Stable capacity contract plus API discovery | Anthropic/OpenAI/supported Ollama billing data reconciled to authoritative views |
| `V1-M8` | Native deployment, recovery, hardening, and release | `EPIC-DEP-01`, `EPIC-HARDEN-01`, `EPIC-RELEASE-01` | `V1-M4`–`V1-M7` | Every mandatory V1 acceptance gate passes; non-mandatory limitations remain visible |

## Plan files

| Milestone | Superpowers execution plan |
|---|---|
| `V1-M1` | `docs/superpowers/plans/2026-09-19-agentmonitor-v1-m1-foundation.md` |
| `V1-M2` | `docs/superpowers/plans/2026-09-19-agentmonitor-v1-m2-authenticated-shell.md` |
| `V1-M3` | `docs/superpowers/plans/2026-09-19-agentmonitor-v1-m3-claude-slice.md` |
| `V1-M4` | `docs/superpowers/plans/2026-09-19-agentmonitor-v1-m4-claude-fleet-alerts.md` |
| `V1-M5` | `docs/superpowers/plans/2026-09-19-agentmonitor-v1-m5-codex-slice.md` |
| `V1-M6` | `docs/superpowers/plans/2026-09-19-agentmonitor-v1-m6-ollama-slice.md` |
| `V1-M7` | `docs/superpowers/plans/2026-09-19-agentmonitor-v1-m7-api-budgets.md` |
| `V1-M8` | `docs/superpowers/plans/2026-09-19-agentmonitor-v1-m8-hardening-release.md` |

## Dependency and parallel-execution policy

```text
V1-M1 -> V1-M2 -> V1-M3 -> V1-M4 ----+
                         +-> V1-M5 ----+-> V1-M8
                         +-> V1-M6 ----+
                         +-> V1-M7 ----+
```

After `V1-M3` freezes the registry, provider, capacity, runtime, API, and UI
contracts, adapter-owned work in M4–M7 may run in parallel. Changes to shared
contracts, the Alembic migration head, composition root, OpenAPI artifact,
generated client, root dependency locks, or shared API/UI surfaces remain
serialized through the shared writer named in `parallel-ownership.toml`.

Live work reserves one opaque account/profile/process target at a time. Claude,
Codex, Ollama, Anthropic API, OpenAI API, and Ollama API live scenarios never
share a credential or mutable profile target between workers.

## Story lifecycle

Every `ST-*` Story uses these states:

```text
Planned -> Ready -> Red -> Green -> Reviewed -> Integrated -> Live Verified
```

`Blocked` and `Not Run` are evidence states, not shortcuts to `Reviewed` or
`Live Verified`. A Story may be `Ready` only when its owning module plan,
contracts, dependency admissions, file ownership, real test boundary, and any
required live resource reservation are resolved.

## Epic completion rules

- Every Story's requirement and acceptance IDs have evidence references.
- Published contracts match the adopted versions and all consumers compile.
- The module owns only its declared paths, tables, migrations, and settings.
- Red/Green/Refactor evidence demonstrates behavior rather than setup failure.
- Security, privacy, license, migration, operations, and documentation impacts
  are recorded in the same Story.
- Required real SQLite, HTTP, browser, Linux, service, and provider tests pass;
  unavailable live scenarios remain visible.
- The Epic reviewer accepts specification compliance and code quality.

## Milestone execution checklist

- [ ] **Step 1: Freeze the milestone input**

Run: `python3 tools/automation/run.py AUTO-PLAN-CHECK`

Expected: exit `0`, with the synchronized planning baseline reported as passed.

- [ ] **Step 2: Reserve isolated Story ownership**

Record the Story ID, exact write paths, contract families, migration slot,
shared-writer needs, and live resources from `parallel-ownership.toml` in the
execution ledger before dispatch.

- [ ] **Step 3: Execute Stories through Superpowers**

Use `superpowers:subagent-driven-development` one Story at a time per write set.
Each worker receives only its milestone plan, owning detailed module plan,
contract references, and global constraints.

- [ ] **Step 4: Review each Story**

Require an independent specification-compliance and quality review. Critical or
Important findings return to the same implementer through the bounded fix loop.

- [ ] **Step 5: Run milestone integration evidence**

Run the exact commands listed by the milestone plan against the real boundaries
claimed. Hosted CI cannot satisfy workstation or live-provider evidence.

- [ ] **Step 6: Update tracker state**

Attach sanitized evidence references to the corresponding `ST-*` issue and
derive Epic/Milestone completion from their gates.

- [ ] **Step 7: Commit the coherent milestone result**

```bash
git add backend frontend packaging tooling docs
git commit -m "feat(v1-mN): complete milestone outcome"
```

The command is used only after Git initialization and branch policy are
established by `V1-M1`; it is never run against an uninitialized checkout.

## Program completion

The program finishes only when `V1-M8` validates every applicable
`AC-V1-*`, `AC-LIVE-*`, `AC-UI-*`, `AC-PROC-*`, `AC-ALERT-*`, `AC-HIST-*`,
`AC-OPS-*`, and `AC-TEST-*` criterion against the required real boundary.
Closing GitLab issues, completing code, or passing deterministic CI alone does
not constitute V1 completion.
