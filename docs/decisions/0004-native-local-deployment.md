# ADR 0004: Native local deployment first

- Status: Accepted
- Date: 2026-09-18
- Owner: Pavlo Sidelov

## Context

AgentMonitor must inspect host processes, provider state directories, local CLIs, and provider-managed credentials on the same development machine. Container mounts/privileges would complicate and weaken the initial design.

## Decision

Deploy natively under the user's account, use a user-level systemd service on Linux, bind to loopback, and continue collection while the browser is closed. Linux is primary; platform adapters preserve real macOS support. Containers are deferred to future remote deployment.

## Consequences

- Straightforward access to user-scoped real state with normal permissions.
- Installation/service/upgrade logic must be robust and documented.
- Linux and macOS platform details remain adapters.
- Remote hosting requires a new security/deployment ADR, not a bind-address change.

## Rejected alternatives

- Docker-first local deployment.
- Root/system-wide daemon.
- Browser-only application without background collection.
