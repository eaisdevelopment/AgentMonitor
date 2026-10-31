# ADR 0005: Capability-driven versioned provider adapters

- Status: Accepted
- Date: 2026-09-18
- Owner: Pavlo Sidelov

## Context

Claude, Codex, Ollama, and future providers expose different quota, budget, authentication, session, and process information through sources of varying stability. A lowest-common-denominator interface would lose detail; core provider conditionals would couple everything.

## Decision

Define a versioned provider protocol with declared capabilities, source/stability/credential metadata, typed outcomes, provenance, and safe provider-extension schemas. Implement each provider in an isolated adapter with its own plan/version/live matrix.

## Consequences

- Unsupported data is explicit.
- Provider detail survives without contaminating core invariants.
- New providers can be added independently.
- Adapter/version compatibility and live verification become required operational work.

## Rejected alternatives

- One universal provider interface requiring every field.
- Provider conditionals inside capacity/runtime modules.
- Silent scraping fallback.
