# Operations runbook

## Status

This is a specification-phase runbook. Procedures describe required behavior, but commands are marked **TBD until implemented and live-verified**. Do not invent or rely on command names merely because they appear as examples in a plan.

## Operating principles

- Run AgentMonitor as the normal user, never root.
- Keep service bound to loopback by default. Direct access from a trusted private
  subnet requires the explicit [LAN profile](../decisions/0014-trusted-lan-dashboard.md).

## Owner-approved trusted LAN dashboard

The [bounded change plan](../plans/integration/trusted-lan-dashboard-change.md)
adds two non-secret, startup-only CLI flags to the authenticated development
runner: `--lan-host` selects one usable private IPv4 interface;
`--lan-network` selects its canonical RFC1918 IPv4 CIDR. Supply both or neither.
Keep `--host 127.0.0.1`; the service binds the additional interface at the same
port using the same application lifespan. Foundation mode rejects LAN flags.
The flags are not `.env` keys and do not change configuration version 1.0.0.

Before activation, build the exact frontend and run the canonical real gate
with explicitly selected test interface/subnet:

```bash
npm --prefix frontend run build
python3 tools/automation/run.py AUTO-LAN-DASHBOARD
```

The gate requires `AGENTMONITOR_TEST_LAN_HOST` and
`AGENTMONITOR_TEST_LAN_NETWORK` supplied in the operator environment. It binds
real loopback/LAN sockets on one ephemeral port, uses isolated migrated SQLite
and random administrator credentials, and runs actual built Chrome. Missing
selectors or unavailable real interfaces are non-success. Test passwords stay
in memory and a private stdin pipe; no owner password/profile is read.

Restart only AgentMonitor with the existing config/data arguments and the
approved pair of LAN flags. Verify both listeners, public shell `200`, protected
unauthenticated reads `401`, and non-subnet peers `403`. The service announces
both exact origins. The LAN IP has a separate host-only dashboard cookie, so
sign in on that address. Quota observations persist; in-memory identity receipts
return only after genuine collection. Collection cadence is unchanged.

If UFW is enabled, an OS administrator must allow TCP from the selected subnet
to the selected interface/port using `ufw allow from ... to ... port ... proto
tcp`. Application authorization does not supply an OS administrator password.
Keep that password in the local terminal. A local socket/HTTP success does not
prove reachability through the firewall from a second computer; record the
owner's remote-browser result separately.

This profile uses HTTP on a trusted LAN. It provides no transport encryption
against network observers/attackers and must not be exposed to untrusted or
Internet networks. TLS/proxy/multi-user hosting is separate scope. To roll back,
omit both LAN flags and restart AgentMonitor; remove only the corresponding
firewall rule if it was added. Records, sessions, profiles, and history need no
migration or deletion.
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

### Connect Claude from the dashboard

1. Open **Accounts**, then the intended pending Claude account. Names and
   organization assignments come from admin CRUD.
2. Confirm **Claude account email** and click **Connect Claude** once.
3. Complete Claude's official sign-in in the ordinary browser window. Keep
   passwords and verification codes on Claude's page.
4. Return to the dashboard. It verifies identity, binds the managed profile,
   and enables monitoring. Quota waits for the next genuine scheduled reading;
   monitoring enabled alone does not prove a successful quota observation.

No terminal command or first-run terminal setup is needed for this monitoring
path. Managed quota readers use Claude's documented `IS_DEMO` presentation
setting to suppress onboarding; independent identity verification is unchanged.
Real normal/flag quota fields matched in the
[bounded evidence](../evidence/claude-dashboard-connection.md).
Newly authenticated fresh-profile acceptance remains **Not Run**.

Status reads never start sign-in. Use **Cancel connection** to cancel an active
attempt. Wrong-account and expired outcomes require a deliberate new attempt;
no authentication is automatically replayed. One sign-in runs at a time.
Protected defaults and ordinary active-profile reconnection are rejected.
An eligible interrupted managed enrollment exposes **Finish connection**,
which resumes verified registry work without starting a new login; live recovery
acceptance remains Not Run.

Run `python3 tools/automation/run.py AUTO-CLAUDE-CONNECT` after an owner-completed
dashboard flow with explicit `AGENTMONITOR_TEST_OWNER_DATA_ROOT`,
`AGENTMONITOR_TEST_MANAGED_ACCOUNT_ID`, `AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT`,
and `AGENTMONITOR_TEST_DASHBOARD_ORIGIN`. These are non-secret selectors;
credentials remain local. The gate never starts sign-in and returns non-success
without a completed flow and fresh managed quota receipt. Its scope is the
selected account only; remaining M4 work is listed in the evidence.

### Additional managed Claude account authentication: operator fallback

The [bounded connection change](../plans/integration/claude-managed-account-connection-change.md)
adds an owner-operated official sign-in stage. Start with an actual pending
Claude account created through admin CRUD. Use its opaque registry account ID
and the explicitly selected AgentMonitor data root:

```bash
backend/.venv/bin/python tools/providers/connect_claude_profile.py \
  --data-root /path/to/agentmonitor-data --account-id REGISTRY_ACCOUNT_ID
```

The tool uses the admin name as the expected email when it is an email address.
For other friendly names, supply `--expected-email` with the intended email.
Credentials and codes must remain in the official provider browser flow. The
tool accepts no credential/code input and discards provider login output. It
waits at most ten minutes and returns a non-success result when the expected
managed identity cannot be verified. No default logout or credential copying
occurs. The selected directory is private and derived from the registry ID;
Claude's official `CLAUDE_CONFIG_DIR` isolates its credential store.

An explicitly selected owner-only executable may be supplied using
`--browser-opener` to hand the official URL directly to a shared browser. The
opener must not log that URL or read browser credentials. Only graphical-session
metadata is inherited for this operation; provider environment credentials are
excluded. A new directory is never inferred from arbitrary agent environments.

Use an ordinary owner-controlled browser window for provider authentication.
Cloudflare documents Playwright and other browser automation frameworks as
[unsupported for production challenges](https://developers.cloudflare.com/cloudflare-challenges/reference/supported-browsers/).
The dashboard may remain in a shared Playwright session while the owner completes
provider authentication separately. If verification loops, let the current
attempt expire or cancel only the operator-owned login child, then use the
official login command with an ordinary browser. Do not automate challenge
answers, change browser identity, or transfer challenge/session cookies.

Authentication alone does not enable monitoring. Use `--setup --enroll` in an
owner terminal to finish native first-run setup and bind the verified identity
to the selected existing admin record:

```bash
backend/.venv/bin/python tools/providers/connect_claude_profile.py \
  --data-root /path/to/agentmonitor-data --account-id REGISTRY_ACCOUNT_ID \
  --setup --enroll
```

Complete native setup, then type `/exit`. Setup refuses redirected input and
output; AgentMonitor never captures the setup terminal. If setup is already
finished, `--enroll` alone is sufficient. The command verifies exact identity,
preserves the account ID/name/group, enrolls a private subscription profile,
and enables monitoring. Existing matching enrollment is reused. It never
edits provider files, logs out, or replaces an account on an identity conflict.

The service independently polls default and managed profiles at their minimum
five-minute cadence, using each account's latest source run. Managed identity
is verified around the native read before quota is committed. After a restart,
the provider identity display waits for a new service-owned collection;
historical quota is never backfilled with a newly read identity.

The bounded gate is `python3 tools/automation/run.py AUTO-CLAUDE-MANAGED`. It
requires explicit `AGENTMONITOR_TEST_OWNER_DATA_ROOT`,
`AGENTMONITOR_TEST_MANAGED_ACCOUNT_ID`, `AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT`,
and `AGENTMONITOR_TEST_DASHBOARD_ORIGIN`. These select a real owner-approved
record and authenticated shared dashboard, never credentials. Missing sign-in,
pending setup, absent service receipt, stale quota, or wrong identity returns
non-success. It proves the selected profile only. The dashboard workflow above
has its own selected live gate; process ownership and remaining M4 goals remain
separate. See
[current evidence](../evidence/claude-managed-account-connection.md).

After an intentional service stop, start the verified local dashboard command:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m agentmonitor.composition.bootstrap \
  --config /home/dev/.local/share/agentmonitor/service.env \
  --data-root /home/dev/.local/share/agentmonitor \
  --host 127.0.0.1 --port 43110 --authenticated-dashboard
```

Open `http://127.0.0.1:43110/accounts` and sign in locally. Read-only source
failures remain visible as actual M04 outcomes; an existing failed run is not
retried. A transient timeout permits a distinct new scheduled observation after
the full five-minute interval. Authentication, setup, trust, permission,
version, and unknown failures require action. Retained observations become
stale normally. Disabling monitoring
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
