# ADR 0008: SQLite local persistence with portability seam

- Status: Accepted
- Date: 2026-09-18
- Owner: Pavlo Sidelov

## Context

V1 is single-user, local, modest scale, and should install without operating another database. It also needs durable observations, migrations, backups, and future remote migration.

## Decision

Use SQLite through SQLAlchemy/Alembic for V1. Enforce module table ownership, explicit transactions/migrations, online backup/integrity validation, and repository contracts that avoid unnecessary SQLite-specific semantics. Preserve a PostgreSQL path for remote deployment.

## Consequences

- Simple native operation and backup.
- Write concurrency and long queries require discipline.
- Physical shared database cannot become a cross-module coupling mechanism.
- Remote scale may require PostgreSQL and a migration ADR.

## Rejected alternatives

- PostgreSQL required for local V1.
- JSON/files as primary history store.
- ORM implicit create/update without migration history.
