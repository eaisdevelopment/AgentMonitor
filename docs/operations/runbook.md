# Operations runbook

## Status

This is a specification-phase runbook. Procedures describe required behavior, but commands are marked **TBD until implemented and live-verified**. Do not invent or rely on command names merely because they appear as examples in a plan.

## Operating principles

- Run AgentMonitor as the normal user, never root.
- Keep service bound to loopback in V1.
- Never paste `.env`, tokens, OAuth files, OTPs, or raw provider output into diagnostics or issues.
- Never modify default provider profiles.
- Treat unknown/stale data as unknown/stale, not zero/current.
- Back up and verify before migrations or recovery.
- Preserve real evidence while redacting secrets/content.

## Expected healthy state

- User service is running and ready.
- Database schema is compatible and integrity check is healthy.
- UI/backend versions match.
- Login works; API token verification works.
- Scheduler is active and no lease is permanently stuck.
- Each enabled capability is Current, Backing off, Authentication Required, Unsupported, Experimental Disabled, or explicitly Degraded.
- Latest verified backup is within policy.
- No critical unacknowledged alert exists unless a known condition is active.

## Initial installation procedure

Final commands: **TBD by deployment module plan**.

Required steps:

1. Verify supported Linux/Python/Node/provider CLI versions and disk space.
2. Install from a pinned, verifiable artifact/source revision.
3. Create configuration/data/state/log/profile directories with owner-only permissions.
4. Create a protected `.env` shell without values being printed.
5. Owner enters AgentMonitor-managed secrets locally.
6. Initialize the administrator password through a non-default, non-logged flow.
7. Apply migrations to the real SQLite database.
8. Build/verify frontend assets and OpenAPI/client version alignment.
9. Install user-level service without enabling lingering silently.
10. Start and verify liveness/readiness/login/backup paths.
11. Run auto-discovery; review every discovered path/account before enrollment.
12. Begin provider enrollment only through approved flows.

## Service lifecycle

Final commands: **TBD and must be tested**.

### Start/restart

- Check configuration file permissions and schema compatibility first.
- A restart must not delete leases/history or duplicate observations.
- After restart verify readiness, scheduler recovery, alert state, and current frontend/backend version.

### Stop

- Stop accepting new mutations.
- Allow or cancel bounded collection jobs according to documented shutdown deadline.
- Release/expire leases safely.
- Flush database/log buffers.
- Do not terminate provider agent processes.

### Browser closed

Service and collectors continue. Reopening UI rebuilds state from API; browser memory is never the authoritative state.

## Health investigation

1. Check liveness then readiness.
2. Check schema/application/frontend versions.
3. Check database integrity and free disk space.
4. Check scheduler heartbeat, active leases, queue depth, and last successful collection.
5. Check provider capability status individually.
6. Use correlation ID to inspect sanitized structured logs.
7. Export a sanitized diagnostic bundle only after automated secret scan.

Never enable broad debug logging that dumps HTTP bodies, CLI output, environment, or provider files.

## Stale or missing telemetry

### Local Claude dashboard polling

The current local authenticated service automatically collects from one
unambiguous enrolled default Claude profile when monitoring is enabled. The
admitted read-only source permits collection every five minutes. Closing the
browser leaves collection running; the account page refreshes quota through
the API every 30 seconds. Account labels and organizations are admin-managed.
Adding a pending account record does not itself authenticate or bind a profile.

After an intentional service stop, start the verified local dashboard command:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m agentmonitor.composition.bootstrap \
  --config /home/dev/.local/share/agentmonitor/service.env \
  --data-root /home/dev/.local/share/agentmonitor \
  --host 127.0.0.1 --port 43110 --authenticated-dashboard
```

Open `http://127.0.0.1:43110/accounts` and sign in locally. Read-only source
failures remain visible as actual M04 outcomes and are not automatically
retried. Retained observations become stale normally. Disabling monitoring
prevents subsequent attempts; it does not interrupt an in-flight provider read.
On normal startup, retained AgentMonitor WAL journals are checkpointed under
the service lock before schema validation. No migration or provider write is
performed. This is the local CLI service, not native installed-service approval.
See [real polling verification](../evidence/claude-dashboard-polling.md).

### Investigation

1. Confirm account/capability is enabled.
2. Inspect last collection outcome, source, versions, and backoff.
3. Distinguish Unsupported, Experimental Disabled, Authentication Required, Rate Limited, Provider Unavailable, Invalid Provider Data, and internal failure.
4. Check provider/CLI version against verified adapter range.
5. Use manual refresh once; do not repeatedly hammer a provider.
6. If authentication is required, follow re-authentication.
7. If format/version changed, disable affected capability if necessary and open a discovery/adapter change; do not guess.
8. Keep last observation visible as stale.

## Quota/budget mismatch

1. Record AgentMonitor observation time, source, unit, precision, and provider/adapter version.
2. Owner checks provider authoritative UI/command at the nearest possible time.
3. Confirm correct account, workspace/project, billing interval, model scope, timezone, and reset precision.
4. Confirm polling delay and provider eventual consistency.
5. Do not edit stored observation to match manually.
6. If meaning/mapping is wrong, mark capability unverified/degraded, preserve sanitized evidence, and return through discovery/contract/TDD.

## Unresolved session-account mapping

1. Review evidence and confidence; do not infer from process order alone.
2. Compare safe provider session/account identifiers where available.
3. Owner may confirm mapping through the dashboard.
4. Store confirmation with time/evidence and retain history.
5. If contradictory evidence later appears, mark mismatch and require reconfirmation; do not silently remap.

## Possible-stall investigation

1. Verify ten-minute threshold and all activity inputs.
2. Check whether session is observably waiting for input/permission.
3. Check provider quota/auth/network alerts.
4. Inspect safe process CPU/memory/state and session metadata freshness.
5. AgentMonitor does not inject input, signal, restart, or kill the process.
6. Owner decides any manual process action outside AgentMonitor V1.

## Provider re-authentication

1. Confirm target account alias and that profile is AgentMonitor-managed, not protected default.
2. Record existing account/provider identity and history link.
3. Start official provider flow.
4. Owner performs browser/device/email/MFA interaction directly.
5. Verify returned stable identity matches expected account.
6. On mismatch, stop and label Wrong Account Detected; do not overwrite the profile/account relationship.
7. On success, verify auth health and run a read-only capability collection.
8. Confirm history/group/settings remained intact.

## Backup operation

Final command: **TBD**.

- Use SQLite online backup API or approved offline copy procedure.
- Write to a temporary destination, complete, fsync as appropriate, checksum, run integrity check, then atomically catalog.
- Do not include `.env`, provider profiles, logs, exports, or credentials.
- Apply seven daily/four weekly/twelve monthly retention only after a new valid backup exists.
- Surface backup failure in dashboard health/alerts.

## Restore operation

Restore is potentially destructive and requires explicit owner confirmation.

1. Stop AgentMonitor cleanly.
2. Identify backup by timestamp/schema/application compatibility/checksum.
3. Verify checksum and SQLite integrity before use.
4. Preserve current database under a new recovery name; do not delete it.
5. Restore to a new file with correct permissions.
6. Start in validation/maintenance mode if implemented.
7. Verify migration compatibility, login, registry, observations, alerts, and latest backup catalog.
8. Resume collectors only after validation.
9. Document recovery and retain old database until owner approves disposal.

## Upgrade

1. Review release notes, provider compatibility, dependency/license/security, and migrations.
2. Verify latest backup and free space.
3. Run preflight.
4. Stop or enter maintenance as required.
5. Install pinned backend/frontend artifacts.
6. Apply explicit migrations.
7. Start and verify readiness/login/API/OpenAPI/frontend/collectors/live data.
8. If failure, follow documented recovery; do not improvise downgrade across destructive migration.

## Disk pressure

1. Stop exports/diagnostics and nonessential collection if writes may fail.
2. Identify owned AgentMonitor directories; never run broad recursive deletion.
3. Preserve database and newest verified backups.
4. Use retention/export cleanup through product operations where possible.
5. Verify database integrity after recovery.

## Secret exposure incident

1. Stop the affected integration/service component if continued use increases exposure.
2. Do not repeat the secret in chat, logs, issue, or report.
3. Identify secret type, scope, where it appeared, and affected artifacts.
4. Owner/provider revokes or rotates it.
5. Rotate AgentMonitor sessions/API tokens/signing material as affected.
6. Remove exposed artifact safely while preserving non-secret audit evidence.
7. Scan repository history, CI artifacts, logs, backups, exports, and diagnostics.
8. Update threat controls/tests/runbook before resuming.

## Database corruption

1. Stop writes and preserve the corrupt file.
2. Record application/schema/database details and integrity output without data dump.
3. Do not run destructive repair against the only copy.
4. Restore newest verified compatible backup to a new file.
5. Validate and compare data loss window.
6. Root-cause journal/disk/shutdown/migration behavior.

## Diagnostic bundle

Must be allowlist-generated and include only safe versions, health states, schema revision, collector outcomes/codes, correlation IDs, performance summaries, and redacted configuration presence. It excludes `.env`, provider files, database rows containing identity unless explicitly needed/masked, raw logs by default, process environment, prompts/responses/source, raw provider/CLI output, cookies, and credentials.

## Operational evidence

Every exercised procedure records date, application/schema/provider versions, operator, result, sanitized evidence reference, deviations, and follow-up. A written but unexecuted procedure remains Planned.
