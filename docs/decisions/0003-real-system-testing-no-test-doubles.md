# ADR 0003: Real-system TDD without boundary test doubles

- Status: Accepted
- Date: 2026-09-18
- Owner: Pavlo Sidelov

## Context

The owner requires trustworthy tests and explicitly rejects mocks, fakes, simulated accounts/data, hardcoded pass tests, and placeholder telemetry. Provider behavior is unstable enough that simulated success could mislead development.

## Decision

Use red-green-refactor TDD. Constructed inputs are allowed only for pure domain functions with no I/O. Database, HTTP, browser, filesystem, subprocess, platform, provider, authentication, and notification claims require the real production implementation and real system/account. Unavailable live tests are Blocked/Not Run, never simulated or counted as Passed.

## Consequences

- Provider development requires owner coordination and may progress more slowly.
- CI covers pure and real local-stack behavior but cannot claim live-provider success without real access.
- Some rare destructive/failure scenarios may remain visibly Blocked.
- Test architecture must make real components easy to start and observe.

## Rejected alternatives

- Mock/provider fixture suites as primary evidence.
- Recorded HTTP replay/cassettes.
- Demo accounts or seeded dashboard telemetry.
- Coverage percentage as a substitute for meaningful behavior tests.
