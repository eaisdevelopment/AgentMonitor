# SQLite persistence: bounded live health

## Delivery scope

This guide covers the root-approved [M4 live-health increment](../plans/integration/m4-live-database-health-change.md), additive CTR-DB-001 V1 1.0.0. The wider PLAN-DB lifecycle and backup/restore remain outside this focused delivery. [Focused evidence](../evidence/m4-live-database-health.md) distinguishes its actual SQLite verification; the later [M4 completion evidence](../evidence/m4-completion.md) records the installed migration and standalone full-M4 integration result.

## Live health and startup integrity

`DatabaseHealthRequestV1` carries an aware UTC as-of, deadline and correlation ID with at most a two-second budget. `GetDatabaseHealthV1` returns actual reachability, admitted current schema revision, nullable schema compatibility, connection policy, historical startup integrity and original integrity time. It never substitutes the binary's target revision for the current database marker. Unknown stored marker text is withheld.

Root constructs `LiveDatabaseHealthReaderV1` before lifespan. During its actual startup resource factory, `InspectStartupDatabaseHealthV1` wraps the existing genuine schema/integrity inspector with file-identity checks and captures a receipt. Startup retains the existing quiescence/service-lock requirements; this wrapper does not authorize inspection concurrent with a writer. Root requires the startup view to be writable, binds the receipt once through `bind_startup_receipt`, then opens the normal runtime writer. A live check verifies the same file, revision/catalog and technical schema fingerprint. It preserves the original integrity time. Missing or inapplicable binding remains unknown/not checked; reachability alone cannot make readiness healthy.

GET reads only bounded technical schema/Alembic metadata. It runs no quick/full integrity check, checkpoint, migration, repair or business-table SQL. Root maps the leaf through M08's published contracts and owns authorization/API/readiness semantics.

## Reusable adapter-only read connection

`open_bounded_sqlite_read` uses direct `sqlite3` with `mode=ro`, query-only, WAL assertion and the secure connection-local policy. Callers must provide the approved `DatabaseRefV1`, real deadline and explicit table allowlist. The bounded connection exposes `fetch_one` and `fetch_many`; SQL/results remain in the owning persistence adapter. Producer-owned health adapters can query their own allowlisted tables without granting DB health business-table access.

Busy timeout is remaining budget before connect and each statement. A monotonic progress handler interrupts SQLite VM work, deadline checks surround each step, and every connection closes before return. There is no thread, executor, pool or read surviving cancellation/timeout. The normal runtime opener retains its five-second policy.

The verified deadline scope is local SQLite lock/VM work. OS scheduling and stalled filesystem syscalls are not universally bounded. Ordinary read-side WAL/SHM bookkeeping may occur; query-only denies DB/WAL content writes. Owner/mode/symlink/hardlink/sidecar policy and file-identity checks remain enforced. Authorizer rules deny mutation, ATTACH and access outside explicit tables. Errors return closed safe codes with no path, SQL, row values or raw exception.

## Limits and rollback

No schema migration, persistent object, dependency or configuration setting was added. Root composition, producer adoption and real HTTP/browser verification are separate handoff work. macOS filesystem and OS-stall behavior were not verified. Removing this additive leaf/helper changes no owner data, provider profile or running agent.
