# Roadmap

The roadmap is outcome-based and contains no calendar promises. The canonical
V1 numbering and dependency graph come from the
[implementation program](superpowers/plans/2026-09-19-agentmonitor-v1-program.md).
The import backlog preserves planning topology; the
[implementation-status overlay](evidence/v1-implementation-status-v1.json)
records current delivery, gate, acceptance, and dependency state.

M0 is a separate discovery track. It is not one of the eight V1 implementation
milestones. A milestone exits only when its own gate and required program
dependencies are complete.

## M0 — Read-only telemetry discovery

**Goal:** replace provider assumptions with real evidence before schemas and
collectors are finalized.

Outputs:

- installed environment inventory;
- Claude, Codex, and Ollama subscription capability matrices;
- Anthropic, OpenAI, and Ollama API-budget capability matrices;
- local process and session metadata inventory;
- source stability, precision, freshness, permission, and rate-limit findings;
- supported, experimental, deferred, and unsupported decisions;
- updated provider contracts, requirements, data model, and module plans.

Exit: the discovery runbook is complete and owner-reviewed, no secret or content
leakage occurred, and every V1 provider capability has a recorded decision.

## V1-M1 — Foundation and local-stack skeleton

**Goal:** establish the repository, contract, persistence, and quality
foundation without claiming provider telemetry.

Scope:

- repository, copyright, CI, lockfiles, and development dependency/license and
  secret checks; release SBOM/notices and full scans remain in V1-M8;
- module, package, and import boundaries;
- typed configuration and protected `.env` workflow;
- real SQLite, Alembic, and backup foundations;
- loopback application, deterministic OpenAPI artifact, generated client, and
  truthful built-browser shell;
- canonical milestone automation and hosted clean-runner evidence.

Exit: the real foundation stack and its local/hosted gates pass without fake
provider data.

## V1-M2 — Authenticated local dashboard shell

**Goal:** protect the local dashboard and versioned API with real single-owner
identity and access behavior.

Scope:

- administrator bootstrap and recovery;
- durable browser sessions, CSRF, throttling, authorization, and API tokens;
- hardened FastAPI/OpenAPI/Swagger/ReDoc boundary;
- generated-client React login, password, token, expiry, and logout flows;
- hostile-origin denial and the authenticated-shell milestone gate.

Exit: the real server, SQLite, HTTP, generated-client, and built-browser
authentication path passes the approved local gate.

## V1-M3 — Real Claude vertical slice

**Goal:** carry one owner-confirmed Claude account through the complete real
monitoring path.

Scope:

- provider protocol and provenance;
- one registry account and protected default profile;
- real Claude subscription quota observation;
- durable collection and capacity history;
- real Linux process and session observation for the same account;
- authenticated API, generated client, and dashboard provenance views.

Exit: one owner-confirmed account produces real quota and runtime observations
with same-account lineage from source through SQLite, API, generated client,
and browser. The revision-bound current gate passed at implementation revision
`b0113bba2e330bb63cc2d1d6f4c266e879ab3ffe`; the active M3 acceptance record
is Passed.

## V1-M4 — Claude fleet, alerts, and operations

**Goal:** cover the owner's Claude fleet and the proactive capacity pain point.

Scope:

- six owner-selected Claude accounts and organization administration;
- account and organization capacity, history, forecasts, and runtime drill-down;
- dashboard alert rules, lifecycle, acknowledgement, snoozing, and recovery;
- health, diagnostics, migrations, collection cadence, and provider-version
  compatibility;
- built-browser verification across fleet, alerts, and operations.

Exit: **Passed and owner-accepted.** All six M4 Stories passed the canonical
gate at implementation revision
`9dbb765531f05f2ae1e8174383cc0ff8b7cb8072`. The gate proved six distinct
current Claude identities across two organizations, six fresh post-restart
quota/history lineages, the guarded current-process witness, and every required
technical, built-browser, and local quality lane with zero skips and zero
registry mutations. The owner countersigned the result on 2026-10-07.

## V1-M5 — Codex vertical slice and fleet

**Goal:** apply the stable monitoring contracts to four Codex accounts and
representative concurrent sessions.

Scope:

- Codex installation, state, process, and session discovery;
- isolated `CODEX_HOME` managed-profile enrollment and live verification;
- supported native quota sources established by discovery;
- four identities, 5–6 concurrent agents, hierarchy, history, alerts, and
  diagnostics;
- default-profile non-modification proof.

Exit: Codex requirements and the approved real capability matrix pass.

## V1-M6 — Ollama cloud subscription vertical slice

**Goal:** provide supported cloud subscription visibility. All local Ollama
work is deferred by the [4 November scope decision](plans/integration/m6-local-ollama-deferral-2026-11-04.md).

Scope:

- actual account, team, and workspace semantics;
- current versus legacy subscription resource model;
- cloud credits, usage, concurrency, and API usage where supported;
- cloud history, alerts, failure isolation and diagnostics.

Exit: the Ollama capability matrix is implemented honestly and unsupported
billing fields remain explicit.

## V1-M7 — API usage, cost, credit, and budget monitoring

**Goal:** add real provider organization and project usage, cost, credit, and
budget monitoring.

Scope:

- Anthropic Admin usage and cost;
- OpenAI organization and project usage, cost, and spend limits;
- Ollama's officially supported API capability set from discovery;
- exact money, tokens, models, projects, billing windows, forecasts, and groups;
- least-privilege administrator credential setup in `.env` where applicable;
- live budget reconciliation through API and dashboard views.

Exit: all approved API-budget acceptance criteria pass.

## V1-M8 — Hardening and release

**Goal:** complete every mandatory V1 release gate.

Scope:

- native Linux build, installation, service lifecycle, upgrade, and recovery;
- 365-day retention, exports, backup rotation, and real restore;
- responsive, accessibility, performance, security, and privacy review;
- failure isolation and full OpenAPI, migration, and contract compatibility;
- dependency, license, SBOM, notices, and complete operator/user/developer docs;
- final real provider, platform, browser, and release-candidate matrix.

Exit: every mandatory V1 acceptance criterion passes against the release
candidate.

## Post-V1 — Email notification delivery

Begins only after V1-M8. The owner supplies email credentials locally in
`.env`. A separate delivery adapter performs real email verification and does
not change dashboard alert ownership.

## Later — Local Ollama monitoring

The [future local Ollama backlog](plans/integration/future-local-ollama-backlog-v1.json)
contains FUT-OLL-LOCAL-001..004: local installation/service discovery, model
inventory, process/resource/correlation observation, UI and local verification.
These are unscheduled future-version tasks, not M6, M7, M8 or V1 release
prerequisites. Existing code and historical results are retained.

## Later — Community and remote evolution

- contribution and copyright-assignment policy (the project licence is decided in [ADR 0016](decisions/0016-eais-copyright-and-personal-use-license.md));
- secure remote deployment, PostgreSQL, TLS, secret manager, and multi-user IAM;
- Gemini, Grok, Muse, and other capability adapters;
- messenger notification adapters;
- optional content capture with a separate privacy architecture.

## Later — Agent control plane

Built on verified monitoring evidence:

1. Account recommendation for new sessions.
2. Minimal launcher that selects an account/profile.
3. Automatic routing for new tasks.
4. Safe checkpoints and resumable handoffs at turn boundaries.
5. Recovery after quota failure.

No design may promise credential replacement inside an in-flight provider
request. Supervisor work is a separate roadmap with its own security and
process-control architecture.
