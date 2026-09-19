# Deployment architecture

## V1 topology

- One native AgentMonitor installation under the developer's user account.
- One user-level background service.
- FastAPI serves `/api/v1`, authenticated documentation, and the built React SPA on loopback.
- One SQLite database in the user's application-data directory.
- Protected configuration `.env` in the user's configuration directory for installed use.
- Provider profiles remain in provider-managed or AgentMonitor-managed provider directories.
- Browser may be closed without stopping collection.

Docker is intentionally deferred because V1 must inspect host processes, provider state directories, desktop credential mechanisms, and local CLIs without fragile host mounts or privilege expansion.

## Filesystem layout target

Exact paths are finalized in the deployment module plan. Follow the XDG convention on Linux and corresponding native macOS conventions.

```text
configuration/
  .env
  non-secret-settings
data/
  agentmonitor.db
  backups/
  exports/
state/
  locks/
  runtime/
cache/
logs/
provider-profiles/
  claude/<opaque-profile-id>/
  codex/<opaque-profile-id>/
  ollama/<opaque-profile-id>/
```

Permissions are owner-only for configuration, database, backup, export, logs, and provider-profile roots unless a documented platform requirement needs otherwise.

## Linux service

- Use a user-level `systemd` unit.
- Start automatically at user login.
- Restart on unexpected failure with bounded backoff.
- Use an explicit working directory, executable, configuration file, and resource limits.
- Do not run as root.
- Do not grant broad filesystem/process capabilities.
- Health/status commands query the service and do not infer health only from PID existence.
- Installation and upgrades preserve `.env`, database, provider profiles, and backups.

Whether user lingering is appropriate is an installation-time decision: it must not be enabled silently. Without lingering, collection follows the user's login session, matching the initial requirement.

## macOS seam

Core Python/backend/UI/domain behavior remains portable. Platform adapters isolate process inspection, path resolution, permissions, and service management. macOS uses a real `launchd` plan and real macOS tests when hardware/runner access exists. Linux-only assumptions in core code are prohibited.

## Application process model

V1 prefers one service process for operational simplicity. API handling, scheduling, and collectors are isolated by application task supervision, timeouts, and bounded worker concurrency. The collection contract does not assume in-process execution, allowing a later separate worker if measurements justify it.

Long-running provider work is not executed synchronously inside an API request.

## Database mode

- SQLite with foreign keys enabled and an explicitly reviewed journal/synchronous mode.
- One migration path managed by Alembic.
- Connection/transaction scope is explicit.
- Collection writes are short transactions.
- History reads are paginated/aggregated.
- Backup uses SQLite's safe online backup mechanism, followed by integrity validation and checksum.

## Frontend delivery

- Frontend builds to static versioned assets.
- Local production service serves assets same-origin with the API.
- Build embeds only public configuration, never `.env` values.
- Asset and backend version mismatch is detectable and visible.
- Source maps are handled according to the release security plan and never contain secrets.

## Configuration

- Typed startup validation.
- Secrets in `.env`; non-secret runtime settings may live in a documented config file or database according to ownership.
- Environment-specific defaults are explicit.
- Unknown variables are warned or rejected according to configuration policy.
- The service never rewrites `.env` implicitly.
- A setup command may create a protected file shell and prompt the owner to fill secrets locally; it never prints existing values.

## Backup and recovery

- Seven daily, four weekly, twelve monthly copies.
- Atomic catalog update and checksum.
- Integrity check before a backup is considered valid.
- Restore is an explicit offline/maintenance operation.
- Existing database is preserved until the restored copy starts and validates.
- Provider credentials and `.env` are not bundled in data backups.

## Upgrade strategy

1. Preflight versions, permissions, disk space, backup health, and migration compatibility.
2. Create/verify a fresh backup.
3. Stop accepting state changes; stop service if required.
4. Install pinned application/frontend assets.
5. Run explicit database migrations.
6. Start and verify readiness, schema, collectors, login, and real current data.
7. Keep prior binary and backup for documented recovery.

No automatic self-update is a V1 requirement.

## Future remote topology seam

A later ADR may introduce reverse proxy/TLS, PostgreSQL, separate worker, multi-user IAM, external secret manager, and remote collectors. The public API, application ports, provider contracts, and platform adapters are designed so this is evolution rather than a rewrite. Remote hosting is not enabled by simply binding V1 to `0.0.0.0`; it requires the security review listed in the threat model.
