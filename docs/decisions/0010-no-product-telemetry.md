# ADR 0010: No external AgentMonitor telemetry in V1

- Status: Accepted
- Date: 2026-09-18
- Owner: Pavlo Sidelov

## Context

AgentMonitor handles account, budget, process, path, and authentication metadata. External analytics/crash services would create additional data flows and dependencies without a current need.

## Decision

Do not send AgentMonitor analytics, product usage, or automatic crash reports externally in V1. Keep logs/diagnostics local unless the owner explicitly exports them. Required outbound traffic is limited to configured provider/GitLab actions and later explicitly configured email.

## Consequences

- Privacy and threat model are simpler.
- Troubleshooting depends on safe local diagnostics and explicit export.
- Any future telemetry requires opt-in owner decision, ADR, privacy/security review, and clear data inventory.

## Rejected alternatives

- Sentry/Google Analytics or equivalent by default.
- Hidden update/usage checks.
