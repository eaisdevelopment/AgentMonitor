# Roadmap

The roadmap is outcome-based. It intentionally contains no calendar promises. A milestone exits only when its evidence is complete.

## M0 — Read-only telemetry discovery

**Goal:** replace provider assumptions with real evidence before schemas/collectors are finalized.

Outputs:

- installed environment inventory;
- Claude/Codex/Ollama subscription capability matrices;
- Anthropic/OpenAI/Ollama API-budget capability matrices;
- local process/session metadata inventory;
- source stability, precision, freshness, permission, and rate-limit findings;
- supported/experimental/deferred/unsupported decisions;
- updated provider contracts, requirements, data model, and module plans.

Exit: discovery runbook complete, owner-reviewed, no secret/content leakage, and every V1 provider capability has a decision.

## M1 — Engineering foundation and real vertical shell

**Goal:** establish the product skeleton and quality system without fake telemetry.

Scope:

- repository, copyright, GitLab CI, lockfiles, license/SBOM/secret gates;
- module/package/import boundaries;
- typed configuration and protected `.env` workflow;
- FastAPI/OpenAPI/Swagger/ReDoc;
- real SQLite/Alembic and backup foundation;
- single-user dashboard login, browser sessions, CSRF, API tokens;
- React/Vite application using generated client;
- truthful onboarding/empty system and diagnostics;
- native user service foundation.

Exit: real server/database/browser/auth path works; no provider data claimed; foundation runbooks exercised.

## M2 — Claude first real vertical slice

**Goal:** first immediately useful real-data dashboard.

Scope:

- Claude installation/current profile/process discovery;
- account/organization registry and guided managed-profile enrollment;
- real subscription quota/auth/session/process observations supported by M0;
- history/provenance/current capacity API;
- first responsive mission-control panels;
- live reconciliation with at least one Claude account.

Exit: one real Claude account flows source → adapter → domain → SQLite → API → generated client → dashboard with live evidence.

## M3 — Claude operational completeness and dashboard alerts

**Goal:** cover the owner's Claude fleet and proactive pain point.

Scope:

- all six intended Claude accounts;
- parent/subagent hierarchy and account correlation;
- health, reset, forecast, possible-stall behavior;
- re-authentication workflow;
- dashboard alert lifecycle, thresholds, acknowledgement, snoozing, recovery;
- Claude history, diagnostics, error isolation, and provider-version compatibility.

Exit: Claude acceptance/live matrix complete for available scenarios; dashboard notifications fully validated before any other delivery channel.

## M4 — Codex vertical slice

**Goal:** apply stable contracts to four Codex accounts and concurrent sessions.

Scope:

- Codex installation/state/process/session discovery;
- isolated `CODEX_HOME` managed-profile enrollment and live verification;
- `/status`/supported quota sources from M0;
- 5–6 concurrent agents, hierarchy, history, alerts, diagnostics;
- default profile non-modification proof.

Exit: Codex requirements and live capability matrix complete.

## M5 — Ollama vertical slice

**Goal:** unify local runtime and cloud subscription visibility.

Scope:

- actual account/team/workspace semantics;
- current vs legacy subscription resource model;
- local models/processes/CPU/RAM/GPU metrics where officially/safely exposed;
- cloud credits/usage/concurrency and API usage where supported;
- 2–4 concurrent agents; history/alerts/diagnostics.

Exit: Ollama capability matrix implemented honestly; unsupported billing fields remain explicit.

## M6 — API budgets across providers

**Goal:** add real API organization/project cost and budget monitoring.

Scope:

- Anthropic Admin usage/cost;
- OpenAI organization/project usage/cost/spend limits;
- Ollama official capability set from M0;
- exact money/tokens/models/projects, billing windows, forecasts, groups;
- least-privilege admin credential setup in `.env` where applicable;
- live budget reconciliation.

Exit: all approved API budget acceptance criteria pass.

## M7 — V1 hardening and release

**Goal:** complete every V1 release gate.

Scope:

- 365-day retention, exports, backup rotation and real restore;
- responsive/accessibility/performance review;
- failure isolation, upgrade/recovery, security/privacy review;
- full OpenAPI/migration/contract compatibility;
- dependency/license/SBOM/notices;
- developer/operator/user docs;
- final real provider/platform/browser matrix.

Exit: every mandatory V1 acceptance criterion Passed.

## M8 — Email notification delivery

Begins only after M7. Owner supplies email credentials locally in `.env`. Uses a separate delivery adapter and real email account verification. It does not alter dashboard alert ownership.

## Later — Community and remote evolution

- project license decision and contribution/copyright policy;
- secure remote deployment, PostgreSQL, TLS, secret manager, multi-user IAM;
- Gemini, Grok, Muse, and other capability adapters;
- messenger notification adapters;
- optional content capture with separate privacy architecture.

## Later — Agent control plane

Built on verified monitoring evidence:

1. Account recommendation for new sessions.
2. Minimal launcher that selects an account/profile.
3. Automatic routing for new tasks.
4. Safe checkpoints and resumable handoffs at turn boundaries.
5. Recovery after quota failure.

No design may promise credential replacement inside an in-flight provider request. Supervisor work is a separate roadmap with its own security and process-control architecture.
