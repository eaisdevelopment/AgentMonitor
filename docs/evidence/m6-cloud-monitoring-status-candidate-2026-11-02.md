# M6 cloud monitoring status candidate

This intermediate candidate addresses M6-A02 and M6-A09: the account and
overview screens distinguish a monitoring preference from a scheduled cloud
poll. Scheduling is presented only when the worker lifecycle and authority
are available, the exact current binding has an M03 source proof, and an
enabled M04 lane matches the account, target graph and generation.

The change adds a read-only M04 schedule view, extends the unshipped M02
CTR-REG-012 connection status and the corresponding P01 wire model, and
consumes it in the UI. Contract registry/adoption and independent review are
still required. The public OpenAPI baseline used for compatibility was the
existing `github/main` contract; the candidate cloud endpoint is not shipped.

The pure scheduling policy and target digest tests failed before their
implementation and passed afterward. The real empty-SQLite lane read failed
before its adapter existed and passed afterward. Twenty focused tests,
targeted Ruff and mypy, and frontend typecheck/build passed. A natural
populated cloud lane, authenticated API/browser behavior, provider checks,
worker lifecycle and restart behavior were not tested. The canonical M6
completion gate has not passed; this is not milestone completion.

No provider state, user agent, credential or service was modified or read.
The read-only query introduces no schema migration or dependency. Follow-up:
independent review, M04 contract registration and actual-system verification.
