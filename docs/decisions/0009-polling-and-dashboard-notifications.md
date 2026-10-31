# ADR 0009: Minute-scale polling and dashboard-only V1 notifications

- Status: Accepted
- Date: 2026-09-18
- Owner: Pavlo Sidelov

## Context

Near-real-time updates are not required. Providers may rate limit queries. The owner corrected the notification scope: dashboard notifications are sufficient for V1; email follows after the full dashboard is validated; native Linux notifications are not needed.

## Decision

Use adaptive polling—approximately one minute for active accounts and five minutes for idle accounts, with event/manual refresh and backoff. V1 alert delivery is dashboard-only. SSE may support low-frequency progress/notification updates but REST remains authoritative.

## Consequences

- Lower provider load and simpler reliability model.
- Every view must show freshness/collection time.
- Email/messenger delivery becomes a later adapter consuming the existing alert lifecycle.
- Native desktop notification work is excluded.

## Rejected alternatives

- High-frequency real-time streaming/polling.
- Email/native/messenger delivery as a V1 blocker.
- Browser-local alert state without durable backend lifecycle.
