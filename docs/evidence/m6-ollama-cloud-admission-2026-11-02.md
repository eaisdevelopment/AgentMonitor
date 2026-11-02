# M6 Ollama cloud admission — integration candidate evidence

Scope: M6-T011/M6-A09, M04 `CTR-COL-008` version 1.0.0 and additive SQLite
schema `v1_0708`. The candidate adds persisted, global single-instance request
admission, fair cursor, fenced in-flight leases and retry deadlines. It is not
wired to a provider client and does not establish live rate-limit behavior.

Real SQLite tests failed before the new repository existed. Subsequent tests
exposed replay dispatch, missing Retry-After and unrepresentable waits; those
behaviors were corrected before the focused suite passed. On the integrated
candidate, 64 admission, schema/migration, offline migration, rate policy and
balance contract tests returned passing results on 2 November 2026. However,
the admission I/O tests constructed account IDs and schedule rows in isolated
SQLite, contrary to the project rule limiting constructed values to pure tests.
Those results are not admissible live-boundary evidence; the noncompliant new
admission test was removed and must be replaced with real account and schedule
state. No live database was migrated, no cloud request was made and no
credential or provider profile was read.

Open: a populated `v1_0707` data-preservation upgrade, executable restore and
prior-binary rollback, the complete planning/boundary gates, a retention
policy for admission records, cloud composition and actual provider evidence.
The previous binary reports `unknown_revision` for `v1_0708` and fails closed;
that is not a verified rollback. Do not deploy the migration based on these
isolated tests alone. No new runtime dependency or license impact is introduced
by this admission module.

Independent review identified that lease expiry alone cannot prove a provider
request has stopped, and an acquire-time reservation cannot guarantee spacing
from a delayed dispatch. The candidate now reserves the next start at least
60 seconds after the lease's latest possible dispatch and refuses to re-admit
an expired unresolved request. This prevents automatic early re-admission but
also means crash/expiry recovery is not implemented; that limitation must be
visible and resolved before cloud delivery. The reservation calculation was
first tested Red and now passes as a pure no-I/O test. The changed SQLite path
has not yet been tested with real Ollama account/schedule state.
