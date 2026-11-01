# M6 Ollama process observation — implementation plan

**Status: Draft.** M6-T013, M6-A06 and AC-PROC-001..004. The approved local
catalog plan leaves this separate owned path open. This plan does not claim
process-to-model or process-to-account association from process names.

## Outcome and boundaries

Show current Ollama-related processes that can be proven by exact executable
identity, with observation time and partial coverage. Display model and account
relationships as unknown unless independently established by real, documented
sources. Never infer active work from a loaded model or an Ollama daemon. Respect
same-user access, bound scan time and size, and never inspect argv, environment,
process contents, provider profiles or communications. Never control processes.
An inaccessible, replaced, unsupported or missing executable is reported as
unavailable or partial, not as zero activity.

## Modules and contracts

A03 owns installation/version discovery and the stable verified executable
identity; A04 owns Linux procfs inspection, admitting an Ollama selector only
after verifying the executable, owner and file identity. M03 owns registration
and versioned provider capabilities. M04/M06 own scheduling, collection and
runtime observation. P01 publishes existing versioned runtime contracts or an
additive versioned change if required; P02 uses only generated API clients.
Reuse existing process retention, PID-reuse protection and provenance. Assess
selector admission, path race, installed-binary changes, history/retention,
provider separation and API compatibility before implementation. Any breaking
contract requires versioned migration and an ADR. No new dependency is proposed.

## Test and delivery

1. Establish the real installed executable/version identity without touching
   provider profiles; compare it to representative same-user Ollama processes
   using the existing bounded process adapter. Use a stable real registry
   installation reference, not an invented durable account or installation.
2. First run a real-boundary test that fails because the selector or integration
   is unsupported; record that Red. Implement selector admission, installation
   reconciliation, collection and presentation as one traced path, then record
   Green and refactor evidence. Avoid exposing an intermediate provider claim
   based only on a process name. Do not reuse a default user profile.
3. Verify real SQLite/API and built-browser output, include partial scan and
   stale/unavailable behavior where the real system naturally exhibits it, and
   regression-check existing Claude/Codex collection. Record unavailable cases
   as not run. Validate actual model/process relationship only when the source
   supports it; otherwise display it as unknown and keep the relevant M6
   acceptance open.
4. Review security, contract compatibility, rollout and rollback, then use the
   canonical deployment and full M6 completion routines. Real multi-host
   coverage and account correlation remain separate acceptance evidence.

## Current discovery

The host has Ollama processes, but the existing platform selector rejects an
Ollama selector as unsupported. See
[m6-ollama-process-discovery-2026-11-01](../../evidence/m6-ollama-process-discovery-2026-11-01.md).
No production code is approved by this draft.
