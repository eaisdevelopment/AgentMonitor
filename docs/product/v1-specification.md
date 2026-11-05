# AgentMonitor V1 specification

**Current scope amendment:** the owner [deferred all local Ollama tasks](../plans/integration/m6-local-ollama-deferral-2026-11-04.md) on 4 November 2026. Local service/model/process monitoring and associated validation belong to the future-version backlog, not V1 release acceptance. Ollama cloud account/balance monitoring remains in M6.

- Status: **Complete product and module-planning baseline**
- Product owner: Pavlo Sidelov <pavlo@sidelov.com>
- Copyright: Copyright © 2026 Essential AI Solutions Ltd <support@essentialai.uk>. Licensed under the [AgentMonitor Personal Use License 1.0](../../LICENSE) ([ADR 0016](../decisions/0016-eais-copyright-and-personal-use-license.md)).
- Delivery target: local, native, Linux-first application
- Detailed requirements: [Product requirements](requirements.md)
- Release gate: [V1 acceptance criteria](v1-acceptance-criteria.md)
- Detailed plans: [Module planning registry](../plans/README.md)

## 1. Product

AgentMonitor is a local monitoring service and responsive mission-control
dashboard for developers running many coding agents through multiple Claude,
Codex, and Ollama accounts. It combines subscription capacity, API billing,
authentication health, running-agent state, alerts, and history without
changing the user's provider profiles or running agents.

V1 answers four questions:

1. Which accounts and agents are currently available, limited, exhausted,
   unauthenticated, stale, or unknown?
2. How much native subscription quota, API budget, credit, or usage remains,
   and when does each native window reset?
3. Which agents are running, under which parent hierarchy and account when that
   association can be proven, and which may be stalled or failed?
4. What requires attention now, with enough history and provenance to explain
   the warning?

## 2. Operating scope

| Area | V1 target |
|---|---|
| Subscription accounts | 6 Claude, 4 Codex, 2 Ollama |
| Concurrent agents | 10–15 Claude, 5–6 Codex; local Ollama deferred |
| API billing | Anthropic, OpenAI, and supported Ollama API accounts |
| Grouping | Accounts grouped by organization with parent-level status and usage |
| Deployment | One developer workstation; native Linux first, macOS-compatible design |
| Access | One administrator, password-protected dashboard, scoped API tokens |
| History | 365 days |
| Primary display | Dense 1920×1080 layout with responsive smaller/larger layouts |
| Notifications | Dashboard only |

Unknown or provider-unavailable values remain visibly `Unknown`, `Unsupported`,
`Unavailable`, or `Stale`; they are never converted to zero or estimated as
provider facts.

## 3. V1 capabilities

### Account and organization inventory

- Register subscription, API, organization, workspace, project, and local
  profile relationships under stable internal identifiers.
- Group accounts under two or more organizations and aggregate only compatible
  resource pools.
- Preserve provider-native resource boundaries so subscription allowance and
  API billing are never merged accidentally.
- Display authentication health and reauthentication requirements without
  collecting passwords, OAuth tokens, email codes, MFA values, or recovery
  codes.

### Capacity and budget monitoring

- Collect all safely available Claude, Codex, and Ollama subscription windows,
  limits, remaining/used values, reset times, precision, and freshness.
- Collect safely available Anthropic, OpenAI, and Ollama API usage, cost,
  credits, budgets, limits, and billing dimensions.
- Preserve native units and windows, exact money, source, observation time,
  confidence, and provider latency.
- Calculate health, burn rate, and forecasts only when inputs support them, and
  label every derived value.

### Running-agent monitoring

- Automatically discover real Claude and Codex processes without
  changing how they were launched.
- Represent parent agents, subagents, wrappers, orphans, and unresolved
  relationships as a hierarchy with evidence strength.
- Show only operational metadata: task-safe label, state, model where safely
  available, duration, token/context totals, resource use, errors, account
  correlation, and possible-stall status.
- Never inspect process memory, terminal contents, arbitrary environments,
  prompts, responses, tool arguments, source code, or secret-bearing payloads.

### Alerts, history, and diagnosis

- Generate dashboard alerts for low/exhausted capacity, API budget conditions,
  authentication problems, stale/failed collection, agent errors, and possible
  stalls.
- Support severity, unread state, acknowledgement, snooze, recovery,
  deduplication, and alert history.
- Retain capacity observations, runtime metadata, alerts, authentication events,
  and collector events for 365 days.
- Expose source, freshness, precision, confidence, and safe diagnostics for
  every displayed status.

### API and dashboard

- FastAPI backend with versioned `/api/v1` REST resources.
- OpenAPI 3 artifact, authenticated Swagger UI, and generated TypeScript client.
- React/TypeScript responsive dashboard that consumes only the public API.
- Mission-control views: global status, organizations, accounts, agent tree,
  capacity/budget history, alert console, authentication center, settings, and
  diagnostics.
- Real data only: no demo accounts, seeded telemetry, placeholder metrics, or
  simulated provider responses.

### Local operation

- Loopback-only default binding and strict host/origin/CSRF/session controls.
- SQLite persistence with explicit migrations, integrity checks, backup,
  restore, and retention jobs.
- Native Linux user service; monitoring continues when the browser is closed.
- Secrets are local, owner-only, ignored by Git, and never returned by an API or
  diagnostic export.

## 4. Explicit V1 boundaries

V1 does not switch provider accounts, log users in or out automatically, mutate
default profiles, inject terminal input, signal/restart/kill agents, route work,
or attempt transparent failover. It does not store prompts, responses, tool
activity, source code, or arbitrary terminal output. Email, native desktop
notifications, messengers, remote hosting, multi-user access, and additional
providers are post-V1.

The architecture keeps seams for future AgentMonitor-managed profiles,
reauthentication workflows, checkpointing, account-aware launching, and
automatic routing, but none of those future capabilities can bypass a new
security and contract review.

## 5. Definitive component and plan inventory

| Plan | Owner and isolated responsibility |
|---|---|
| `PLAN-FND` | Repository, toolchain, CI, composition, dependency controls |
| `PLAN-M01` | Dashboard identity, sessions, CSRF, API tokens, authorization |
| `PLAN-M02` | Organizations, accounts, provider installations, profile references |
| `PLAN-M03` | Provider protocol, capabilities, compatibility, source classification |
| `PLAN-M04` | Polling, refresh, concurrency, deadlines, retries, collection runs |
| `PLAN-M05` | Quotas, budgets, credits, health, aggregation, forecasts, history |
| `PLAN-M06` | Processes, sessions, hierarchy, correlation, runtime state, stalls |
| `PLAN-M07` | Alert rules, lifecycle, deduplication, acknowledgement, snooze |
| `PLAN-M08` | Health, configuration diagnostics, backup, restore, export, audit |
| `PLAN-A01` | Claude-specific read-only adapter |
| `PLAN-A02` | Codex-specific read-only adapter |
| `PLAN-A03` | Ollama local/cloud read-only adapter |
| `PLAN-A04-LINUX` | Linux process, filesystem, service, and resource observation |
| `PLAN-A04-MAC` | macOS implementation of the same platform contract; evidence blocked |
| `PLAN-P01` | FastAPI transport, OpenAPI, authentication enforcement |
| `PLAN-P02` | React dashboard and generated API client |
| `PLAN-DB` | SQLite repositories, migrations, transactions, retention storage |
| `PLAN-DEP` | Native Linux installation, service lifecycle, upgrade, rollback |
| `PLAN-INT` | Cross-module integration, acceptance, hardening, V1 release |
| `PLAN-M0-DISCOVERY` | Real provider/platform capability verification before adapter claims |

Each plan defines allowed paths/imports, published and consumed contracts,
tables/configuration ownership, test scenarios, live evidence, implementation
increments, rollback, and stop conditions. The machine-readable contract,
requirement, configuration, and parallel-write manifests are linked from the
[planning registry](../plans/README.md).

## 6. Dependency flow

```text
Provider/platform adapters -> Provider system -> Collection control
Registry ------------------------------+---------> Capacity
Linux/provider observations -----------+---------> Runtime observation
Capacity + Runtime observation -----------------> Alerting
IAM + domain queries + Operations --------------> FastAPI/OpenAPI
FastAPI generated client -----------------------> React dashboard
All persistence ports --------------------------> SQLite adapter
All components ---------------------------------> Integration/release
```

Domain modules contain no FastAPI, SQLAlchemy, provider SDK/CLI, operating-
system, or UI dependencies. The UI has no database or backend-internal access.

## 7. Implementation sequence

1. Foundation: repository/toolchain, module boundaries, real SQLite migration
   harness, running FastAPI/OpenAPI, minimal built UI, and CI.
2. Authenticated local shell: dashboard login, sessions, CSRF, API tokens,
   loopback security, and health skeleton.
3. One real Claude vertical slice across registry, collection, capacity/runtime,
   API, generated client, and dashboard.
4. Claude fleet, history, reauthentication status, alerts, and diagnostics.
5. Codex vertical slice and concurrent-agent coverage.
6. Ollama cloud subscription vertical slice; local Ollama is deferred.
7. Anthropic, OpenAI, and supported Ollama API budget vertical slices.
8. Retention, backup/restore, accessibility, responsiveness, performance,
   security/license review, Linux service lifecycle, and V1 release gate.

Independent implementation may run in parallel only where the published
contract and write-ownership manifests show no collision.

## 8. Completion rule

The specification is complete when the product requirements, acceptance
criteria, 20 detailed plans, contract adoption, requirement ownership,
configuration ownership, parallel write sets, and planning synchronization
gate agree. Provider-specific metric availability remains a real discovery
result—not a reason to invent behavior or endlessly expand the specification.

V1 itself is complete only when the acceptance criteria pass against the real
application, real local services, real browser, real workstation, and real
owner-controlled accounts. Blocked or unavailable provider capabilities remain
visible limitations rather than simulated passes.
