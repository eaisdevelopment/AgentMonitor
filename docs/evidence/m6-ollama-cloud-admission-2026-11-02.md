# M6 Ollama cloud admission — integration candidate evidence

Scope: M6-T011/M6-A09, M04 `CTR-COL-008` version 1.0.0 and additive SQLite
schema `v1_0708`. The candidate adds persisted, global single-instance request
admission, fair cursor, fenced in-flight leases and retry deadlines. It is not
wired to a provider client and does not establish live rate-limit behavior.

Real SQLite tests failed before the new repository existed. Subsequent tests
exposed replay dispatch, missing Retry-After and unrepresentable waits; those
behaviors were corrected before the focused suite passed. On the integrated
candidate, 64 admission, schema/migration, offline migration, rate policy and
balance contract tests passed on 2 November 2026. Those tests used isolated
SQLite files. No live database was migrated, no cloud request was made and no
credential or provider profile was read.

Open: a populated `v1_0707` data-preservation upgrade, executable restore and
prior-binary rollback, the complete planning/boundary gates, a retention
policy for admission records, cloud composition and actual provider evidence.
The previous binary reports `unknown_revision` for `v1_0708` and fails closed;
that is not a verified rollback. Do not deploy the migration based on these
isolated tests alone. No new runtime dependency or license impact is introduced
by this admission module.
