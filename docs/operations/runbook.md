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

Claude Code `2.1.289` may report a current percentage without displaying a
reset for that window. AgentMonitor keeps the percentage and reports the reset
as Unknown/Not reported. Do not infer a reset display or time, edit the stored
reading, repeatedly refresh, or treat the missing reset alone as an
authentication failure. A present reset-shaped line that is malformed or
conflicting remains a source failure and follows the investigation procedure
below; it is never downgraded to the absent/Unknown case. A bounded
model-specific weekly card is omitted as `unsupported`, while the required
session and all-model windows remain available in the partial reading.

### Reconcile an exact admitted Claude installation

When the installed Claude Code version changes after a separately approved
exact-version admission, stop only the AgentMonitor service and run the bounded
installation reconciliation. Do not stop or modify running Claude agents. For
the owner data root and retained exact `2.1.289` admission, use:

```bash
AGENTMONITOR_OWNER_DATA_ROOT=/absolute/path/to/agentmonitor-owner-data
PYTHONPATH=backend/src backend/.venv/bin/python \
  -m agentmonitor.composition.claude_installation_reconciliation \
  --data-root "$AGENTMONITOR_OWNER_DATA_ROOT"
```

Success prints:

```text
CLAUDE INSTALLATION RECONCILIATION: PASSED — current admitted installation registered
```

The command requires an absolute data root, reads the real executable's bounded
version banner, and emits one installation with no account candidates through
`DiscoveryOutcomeV1`. M02 processes that outcome through its existing public
reconciliation port. The repository transaction requires one stable Claude
installation identity and platform, updates its reported exact version, and
verifies that Claude discovery candidates, accounts, monitoring profiles, and
profile-resource links did not change before commit. The same transaction
creates the strict operation receipt and verifies that the exact request is
classified as a replay. There are no failure-producing reads after commit. A
separate fresh observation preserves the stable installation ID and protected
records, although it may advance registry record/revision metadata; an exact
receipt replay does not.

Before discovery or registry mutation, the command acquires the stable
owner-only exclusive AgentMonitor service lock. If the running service already
owns that lock, the command exits non-success and prints:

```text
CLAUDE INSTALLATION RECONCILIATION: BLOCKED — service quiescence required
```

The occupied-lock path leaves the database unchanged. Stop AgentMonitor and
rerun the same command; never remove or bypass the lock file.

Missing or unadmitted binaries return **Blocked**. Relative targets, ambiguous
installations, identity/platform conflicts, incomplete protected-state checks,
or repository failures return non-success without a passing message. Do not
work around a failure with direct SQL or by changing a provider profile. Keep
AgentMonitor stopped and resolve the exact admission or registry conflict before
retrying.

This command never installs, upgrades, downgrades, or relinks the Claude
executable; changes its default symlink; discovers an account; reads a
credential; or writes a Claude profile. Restart AgentMonitor normally after a
pass. At the admission checkpoint, the later genuine scheduled collection and
current-revision M4 gate still had to prove account identity, quota/history
lineage, and browser state; the accepted M4 receipt now records that proof.
The command has passed real installed-binary and real file-backed SQLite tests;
its stopped-service invocation against the owner's current data root also
passed. It preserved the opaque installation ID while advancing the reported
version from `2.1.282` to `2.1.289`, and privacy-minimized public-view digests
for six accounts, one candidate, six profiles, and six resource links were
unchanged. See the
[exact-version admission evidence](../evidence/claude-2.1.289-admission.md).

### Current-revision M4 exact-version gate

`AUTO-M4-EXIT` is the canonical M4 completion command. Its technical lane runs
`AUTO-M3-TEST`, then the M4 story suite together with the exact admitted Claude
authentication, quota mapper, manifest, parser, installation, OTLP rejection,
subscription-quota, installation-policy, and reconciliation tests. Any failed
or skipped required test prevents the receipt.

The post-restart fleet witness also requires exact quota provenance in current
windows and their matching history: source
`claude.usage.ax-screen-reader.v1`, adapter `agentmonitor.claude` `1.0.3`,
parser `1.0.3`, provider `2.1.289`, and decision reference
`A01-M03-CLAUDE-2-1-289-001`. For every selected account, the built account
page must render the exact source, adapter/version, and provider version in its
quota technical details. A stale or partially matching tuple returns
non-success; it cannot satisfy the gate through current percentages alone.

Run the command only with the documented owner data root, authenticated shared
browser endpoint/origin, owner outcome file, and current service PID selectors.
The bounded `2.1.289` admission evidence is Passed. At the accepted M4 run, the
default `claude` command was `2.1.292` and exact resolution used the retained
`2.1.289` executable. As of 2026-10-11 the default is `2.1.296` and the retained
`2.1.289` executable is absent. Scheduled Claude quota/identity/authentication
collection therefore fails closed until a separately approved exact-version
admission is completed; the historical M4 acceptance remains a historical
revision-bound result. The accepted current-revision M4 run met
that condition; its sanitized receipt and owner countersignature are linked
from the documentation index.

### Current-revision M5 Codex completion gate

`AUTO-M5-EXIT` is the sole V1-M5 completion command. It is finite and
noninteractive. The owner completes Codex browser authentication, the
authoritative `/status` reconciliation, and the real capacity-alert lifecycle
before running it. The command never initiates login, acknowledges or snoozes
an alert, waits for a natural recovery, switches an agent account, or reads the
default Codex profile.

#### Activate the exact clean M5 service before collecting prerequisites

The currently trusted persistent dashboard runtime is
`77a3bad12a096a81587b94b8981ceee812b6445b`. Keep its extracted runtime and
existing user-unit launch material intact as the rollback target. That service
is suitable for ordinary dashboard use, but its extracted tree has no Git
metadata, so Operations truthfully reports an unknown source revision. Do not
collect or reuse M5 prerequisite files against it.

Finish and commit the exact M5 implementation in its development branch first.
Then make the stable owner-controlled service worktree immutable for this run by
detaching it at that commit. Never detach a worktree that still contains
uncommitted work:

```bash
revision="$(git rev-parse --verify HEAD)"
test -z "$(git status --porcelain --untracked-files=all)"
git switch --detach "$revision"
test "$(git rev-parse --verify HEAD)" = "$revision"
test -z "$(git status --porcelain --untracked-files=all)"
if git symbolic-ref --quiet HEAD >/dev/null; then exit 1; fi
```

From that detached worktree, set the owner data root and authenticated
shared-browser selectors described below. Select the currently running trusted
service without manually transcribing its PID, then run the bounded transition:

```bash
export AGENTMONITOR_M5_SERVICE_PID="$(
  systemctl --user show agentmonitor-dashboard.service \
    --property MainPID --value
)"
python3 tools/automation/run.py AUTO-M5-SERVICE-ACTIVATE
export AGENTMONITOR_M5_SERVICE_PID="$(
  systemctl --user show agentmonitor-dashboard.service \
    --property MainPID --value
)"
```

The activation command builds and validates the candidate before stopping the
trusted service. It preserves the same data root, `service.env`, database,
loopback/LAN arguments, provider-tool path, cache location, and service
hardening. The candidate changes `TimeoutStopSec` from the trusted unit's 30
seconds to the approved 45-second application drain bound; rollback restores
the exact prior 30-second unit value. The command privately journals the exact
old unit and process identity, atomically selects the clean checkout, reloads
the user manager, and starts the candidate. Success requires real HTTP
readiness, authenticated built-browser access, exact PID/start/cwd/executable
identity, unchanged complete public Registry state, and an Operations
`source_revision` equal to the checkout's unchanged 40-hex `HEAD`.

Any activation or verification failure automatically restores the exact prior
unit, restarts the trusted `77a3bad12a096a81587b94b8981ceee812b6445b`
runtime, and proves its real process and HTTP readiness before returning a
normal Blocked or Failed result. A
`m5_service_activation_rollback_failed` result means restoration could not be
proven: stop M5 evidence collection, preserve the journal and both runtimes,
and diagnose the user unit. Never edit the journal, unit backup, or trusted
runtime to force another result.

Exactly thirteen revision-pinned corrective rollover modes are authorized. The
first preserves the completed
`6bfa69dc13cc9e1ded9c6baa6e803cb99bc8c20b` transition below
`<owner-data-root>/m5-service-activation-corrective-archive/`. The second
preserves the completed
`063445154bca0bf5ec43db94ba57c17fd193fd99` transition below the distinct fixed
singleton parent
`<owner-data-root>/m5-service-activation-corrective-archive-0634451/`.
The third preserves the completed
`6d6e1aa9d9b64d50e3f83d0f1686e6cff04b7c17` transition below the distinct fixed
singleton parent
`<owner-data-root>/m5-service-activation-corrective-archive-6d6e1aa/`.
The fourth preserves the completed
`e066d7e1ba0124f0454c07002ea7b2ad0817d6b9` transition below the distinct fixed
singleton parent
`<owner-data-root>/m5-service-activation-corrective-archive-e066d7e/`.
The fifth preserves the completed
`d81afab9e5b1c1dbdb690f390e77cee66eba5437` transition below the distinct fixed
singleton parent
`<owner-data-root>/m5-service-activation-corrective-archive-d81afab/`.
The sixth preserves the completed
`8cc683d946b58f5eb72955e08a520195582e1a28` transition below the distinct fixed
singleton parent
`<owner-data-root>/m5-service-activation-corrective-archive-8cc683d/`.
The seventh preserves the completed
`35f50d8c4865505a9112d8aef7ea788f425ae658` transition below the distinct fixed
singleton parent
`<owner-data-root>/m5-service-activation-corrective-archive-35f50d8/`.
The eighth preserves the completed
`1ada84f71e827bb4f7ea966462a6cf51d050e9af` transition below the distinct fixed
singleton parent
`<owner-data-root>/m5-service-activation-corrective-archive-1ada84f/`.
The ninth preserves completed revision
`468a937d796efcb7ff1785a749789f07a3322abc` below
`<owner-data-root>/m5-service-activation-corrective-archive-468a937/`.
The tenth preserves completed revision
`10a7bc0db09997d92e62fb5c5e8ea7d5b85866cb` below
`<owner-data-root>/m5-service-activation-corrective-archive-10a7bc0/`.
The eleventh preserves completed revision
`04f8bcdb1adaa4bc5352794c3bc65bcfb7137348` below
`<owner-data-root>/m5-service-activation-corrective-archive-04f8bcd/`.
The twelfth preserves completed revision
`c271d47ef6c7fe20a3ac05bca0a0c63429bc9cdb` below
`<owner-data-root>/m5-service-activation-corrective-archive-c271d47/`.
The thirteenth preserves completed revision
`9db4c3d7add4da16a46b88b6c46bb23ed7855883` below
`<owner-data-root>/m5-service-activation-corrective-archive-9db4c3d/`.
Each archive entry name binds its source revision and activation-receipt
digest. No mode accepts a different source revision, archive parent, or
additional entry.

The requested new candidate must differ from the pinned trusted revision and
all thirteen completed corrective revisions above. The command checks those
reserved revisions before any service restoration, archive move, or
transition-state write; a reserved candidate blocks without changing the
existing service or evidence. This authorizes no general deployment mode.

The previously recorded owner outcomes and alert witness may remain bound to
`10a7bc0` only when the gate verifies their exact PID/start against its retained
activation receipt and permits tracked application changes only to the exact
digest-reviewed account history range selector, with no dependency input changes
between that predecessor and the current revision. It
validates their original timestamps and digests and checks the current service
independently. It does not create a new owner action or rewrite either witness.

An ordinary systemd or workstation restart can change the current dashboard
PID/start identity after its completed activation receipt was created. Leave
that immutable receipt unchanged. The rollover accepts the restarted process
only when the current unit, executable, working directory, clean source
revision, HTTP/browser proof, Registry, database, journal, rollback unit, and
trusted runtime all still validate for the receipt's exact completed revision.
Any other mismatch blocks before service or archive mutation.

When a newer detached candidate invokes the command while any exact source
candidate is active, the command validates the completed receipt, journal,
rollback unit, clean source checkout, current service/browser revision,
Registry digest, database identity, and retained trusted runtime before
changing the service. Each later mode also retains descriptors, inodes, modes,
link counts, and digests for every earlier archive and revalidates that ordered
chain before every service or filesystem mutation. It restores and proves the
trusted runtime, then atomically moves the complete current transition
directory without replacement into its fixed owner-only singleton. Every
archive parent and entry is fsynced and revalidated; each source evidence inode
and byte sequence remains preserved.

The command then creates a fresh owner-only transition directory and reports
`m5_service_activation_rerun_required` with the new trusted service PID. The
dispatcher exits with status `5` and prints
`AUTO-M5-SERVICE-ACTIVATE: RERUN REQUIRED by corrective rollover`. This typed
result records a completed restorative rollover; it is neither an activation
pass nor an activation failure.

After that result, refresh `AGENTMONITOR_M5_SERVICE_PID` from systemd and run
the same canonical command once more from the unchanged corrected detached
worktree. The next invocation performs the normal rollback drill and candidate
activation. Before any new transition, it revalidates every required completed
corrective archive through its own revision-pinned singleton selector,
including name, parent and entry identity, owner, mode, exact three artifacts,
artifact digests, clean source checkout, immutable rollback runtime, and prior
activation receipt.

A retry after a no-replace archive move accepts an absent canonical
transition root, or an owner-only root in exactly one recovery state: empty
`fresh`, `journal_only`, `rollback_only`, or `prepared` with the exact valid
journal and rollback unit. The existing guarded root creation handles an absent
root. Any other entry set or state blocks without cleanup or replacement. A
changed retained archive, dirty or moving checkout, unexpected service
revision, Registry/database change, absent, partial or multiple archive,
archive collision, or unsafe path also blocks. Do not move, copy, edit, link,
or delete a transition or corrective archive by hand.

The coordinator never invokes a provider or reads, copies, or changes provider
profiles. The selected AgentMonitor service may continue its already configured
scheduled monitoring under the existing managed-profile policy. This command
does not archive stale prerequisites and does not contribute an M5 completion
pass. After it succeeds, verify the refreshed PID selector above is nonzero and
use that same value for archive, owner-outcome, alert, quota, and exit work.
Do not switch branches, commit, reset, merge, rebase, or edit the detached
worktree during this sequence.

Success leaves an owner-only activation journal, exact rollback-unit copy, and
activation receipt below the fixed AgentMonitor transition directory. Preserve
all three with the trusted rollback runtime. `AUTO-M5-EXIT` requires their
canonical bytes, candidate and rollback revisions, rollback-runtime digest,
and current systemd ownership to remain valid; a missing, stale, or changed
artifact blocks completion. Never edit or replace these files to force the
exit gate.

The coordinator keeps the service-transition guard through its final receipt
write and validation. A final guard custody or release failure removes the
receipt created by that attempt and enters the same proven rollback policy.
A partial create-once receipt is removed by exact inode identity; an unsafe or
failed cleanup is reported explicitly, while a rollback failure keeps its
distinct higher-priority result.

Run it only against the already running authenticated loopback dashboard, with
these selectors in the calling environment:

- `AGENTMONITOR_TEST_OWNER_DATA_ROOT` and `AGENTMONITOR_TEST_DATA_ROOT`, both
  naming the same absolute owner-only data root;
- `AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT` and
  `AGENTMONITOR_TEST_DASHBOARD_ORIGIN`, both selecting the authenticated shared
  loopback browser/service; and
- `AGENTMONITOR_M5_SERVICE_PID`, selecting that exact dashboard process.

Every M5 prerequisite command and `AUTO-M5-EXIT` revalidates that the resolved
service worktree is still detached at the same committed 40-hex `HEAD`, its
tracked and untracked status remains empty, the selected PID/start/cwd/executable
still identifies that worktree, and Operations reports the same source
revision. Each prerequisite performs this check before consuming earlier
evidence and again before its own create-once write. Exit repeats it before its
service restart, after all technical/browser/local lanes, and immediately
before the final receipt. Any mismatch blocks without a success write. After a
new commit, checkout, or service generation, archive the now-stale prerequisite
set and collect it again in the documented order.

Create the fixed `<owner-data-root>/m5-owner-outcomes.json` prerequisite with:

```bash
python3 tools/automation/run.py AUTO-M5-OWNER-OUTCOMES
```

This command requires a controlling TTY and the owner data root, dashboard
origin, shared-browser CDP endpoint, and selected service PID variables above.
The CDP connection is used only to reprove the running Operations source
revision before the create-once write. The account selection itself reads
Codex accounts through the Registry's public query over the real owner database
and performs no provider operation. At selection,
disposition, and confirmation checkpoints it displays each selected registry
alias and opaque account ID with the fixed safe labels `vendor: OpenAI` and
`provider: Codex`. These labels are not persisted. The command collects
`verified` or `owner_unavailable` plus a bounded reason code for each row, shows
the four-row summary, and writes only after the owner types the exact
confirmation phrase.

The result is a regular, single-link, no-symlink `0600` file of at most 16 KiB
which the command creates once and never replaces. Its closed schema is
`agentmonitor.m5-owner-outcomes.v2`, with the exact top-level fields `schema`,
`implementation_revision`, `service_pid`, `service_start_time_ticks`,
`owner_confirmed_at`, `owner_confirmation`, and `outcomes`. The revision and
service tuple identify the selected pre-gate service, `owner_confirmation` is
true, and the confirmation remains current for at most eight days with five
minutes of allowed clock skew. `outcomes` contains exactly four rows with
unique opaque `account_id` values and unique private `alias` values. A
`verified` row has only `account_id`, `alias`, and `disposition`; an
`owner_unavailable` row additionally has a bounded lowercase `reason` code.
Identity fingerprints are not accepted in this private file. The live
authenticated API/browser verification derives a private digest from each
current provider identity and rejects duplicate verified identities. Alias,
account and identity values remain private; only digests and aggregate counts
reach the gate receipt.

#### Preserve stale M5 prerequisites before collecting them again

The three fixed M5 prerequisite files are create-once evidence. If the clean
implementation revision or selected service PID/start identity changes, or a
bounded witness expires before `AUTO-M5-EXIT`, do not edit, overwrite, copy,
hard-link, or delete the old files and do not create a replacement data root.
First finish and commit the intended clean revision, restart AgentMonitor from
that revision, and verify the Operations inventory reports it. Then, with the
same owner-root, data-root, dashboard-origin, and new service-PID selectors
used above, run:

```bash
python3 tools/automation/run.py AUTO-M5-ARCHIVE-PREREQUISITES
```

The command requires a clean checkout and the exact selected running service.
It refuses to act when `.agentmonitor-local/m5-current-gate-receipt.json`
already exists, when the existing prerequisite set is still usable for the
current revision/service/freshness bounds, when the owner-outcome file is
absent, or when any existing dependent witness is malformed or belongs to a
different owner-outcome context.

Archive and `AUTO-M5-EXIT` use one checkout-global lock scope matching the
shared `.agentmonitor-local/m5-current-gate-receipt.json` path, regardless of
which owner data root is selected. On first use, the protocol may create only
that exact missing `.agentmonitor-local` directory with one atomic `mkdir` and
mode `0700`; an existing object continues through the same owner, mode,
resolved-path, no-symlink, and descriptor-identity checks. It then takes a
nonblocking exclusive lock on the directory descriptor and binds a Linux
abstract Unix socket whose kernel name is derived from the OS owner and
canonical receipt path. The kernel-bound name cannot be renamed, unlinked, or
replaced through the filesystem. Replacing even the complete receipt directory
cannot let a second process enter while the first guard is held, and the first
process detects the directory identity change before claiming success.

Archive holds the guard from final-receipt preflight through every move,
verification, fsync, and rollback. M5 exit acquires it before its first receipt
and prerequisite preflight and holds it through all gates, final rereads,
receipt creation, service recheck, and safe receipt cleanup. Contention, an
unsafe receipt directory, a changed directory identity, or an unavailable
kernel guard blocks the command. Do not start a fresh prerequisite writer until
archive reports success.

Exit creates and validates its final receipt relative to the directory
descriptor held by the completion guard, and retains both that directory and
the exact receipt inode through all final service and lock checks. Any
successful path repeats a descriptor-relative check that the canonical entry
still names that owner-owned regular `0600`, single-link retained inode after
the post-write service observation and both final lock validations. Any
post-write exception, including process interruption, first erases the exact
created receipt bytes while both original guards remain held. Duplicate
kernel-guard descriptors retain both abstract-socket names until any
release-failure cleanup retry finishes. Cleanup unlinks the directory entry
only when it is still the same owner-owned regular `0600`, single-link inode. A
replacement is never removed, failed invalidation is explicit, and a cleanup
failure cannot replace an earlier Blocked, Failed, interruption, or rollback
failure result.

Service activation and M5 exit also share a separate fixed service-transition
guard below the owner-only activation directory. Exit acquires it before live
service selection and holds it through its restart, final activation-receipt
validation, completion-receipt write, and cleanup. This prevents activation or
recovery from inspecting or changing the fixed user service concurrently with
the completion gate. Guard contention or custody change blocks without a
completion claim.

Before the first rename it validates the resolved owner-owned `0700` data root
and every existing fixed prerequisite as an owner-owned, regular, single-link,
no-symlink `0600` file of at most 16 KiB. It validates the closed documents as
one internally consistent dependency set, keeps each inode open, and computes
its SHA-256 digest. It then uses Linux `renameat2(RENAME_NOREPLACE)` to move
each entry atomically on the same filesystem without replacing a destination
created by another process. The command blocks when this kernel primitive is
unavailable. It moves the complete existing set below
`<owner-data-root>/.m5-prerequisite-archive/<old-revision>-<bundle-digest>/`.
The archive directories are `0700`; the evidence files retain their inode,
mode, link count, size, and digest. A final `0600` manifest contains only the
old revision, timestamp, fixed basenames, counts, and SHA-256 digests. It never
contains aliases, account IDs, provider identities, profile paths, process IDs,
or provider content.

The complete set is preflighted before mutation and each successful rename is
verified and fsynced. Rollback uses the same atomic no-replace primitive. A
detected rename or manifest failure attempts to return every moved inode to its
original fixed name without overwriting another file.
An abrupt host or process failure between the individually atomic renames may
leave a private incomplete archive; preserve it and investigate the fixed and
archive names by inode and digest before retrying. Never delete or rewrite a
partial archive to force a pass.

After a successful archive, rerun `AUTO-M5-OWNER-OUTCOMES` against that already
verified revision and service. Any capacity-alert lifecycle used for the new
alert witness must start a new occurrence after both that service start and
the new owner confirmation. A first occurrence records `opened`; a recovered
retained fingerprint records `reopened`. Older alert rules and generations
remain retained evidence but cannot satisfy the new service-bound witness.

Create the fixed `<owner-data-root>/m5-quota-witness.json` prerequisite with:

```bash
python3 tools/automation/run.py AUTO-M5-QUOTA-WITNESS
```

Run it from the same clean revision while the selected pre-gate service and
authenticated shared browser are still running. It requires a controlling TTY
and these exact selectors: `AGENTMONITOR_TEST_OWNER_DATA_ROOT`,
`AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT`,
`AGENTMONITOR_TEST_DASHBOARD_ORIGIN`, and `AGENTMONITOR_M5_SERVICE_PID`. The
owner root must be an absolute, resolved, owner-owned `0700` directory; both
browser selectors must resolve to loopback, the dashboard origin must use
HTTP, and the service PID, start identity, launch origin, data root, clean
40-character revision, and existing owner-outcome file must all agree.

The command does not invoke Codex. It first uses a new page in the already
authenticated shared browser to read every `verified` outcome account through
the versioned API and built dashboard. Each account must be active, monitored,
have a distinct current provider identity, and have genuine current collection
lineage. Current API values must render exactly in the account quota table, and
their observation IDs and exact values must occur in retained history. The
browser makes no POST, PUT, PATCH, or DELETE request. The command also hashes
the complete public Registry graph before and after its checks and rejects an
incomplete, changing, or over-200 account or organization graph.

For the original v1 witness, for every displayed private alias and quota window, open that account's
official Codex `/status` view and enter only:

1. the displayed whole percentage left, from `0` through `100`;
2. the displayed reset as a UTC RFC 3339 timestamp ending in `Z`, or `none`;
3. when a reset is present, its displayed precision: `second`, `minute`,
   `hour`, or `day`.

Do not paste provider output, credentials, prompts, responses, or account
content. Account/window membership, semantic roles, and whole percentages must
match AgentMonitor exactly; the command never creates a missing five-hour,
weekly, primary, or secondary window. A reset first must match at the stated
display precision. Only when that direct match fails may a window use the
full-unused rolling rule, and only when both readings are exactly `100%`, both
resets are present, AgentMonitor's reset is exact and future at collection, and
the owner observation follows collection by 1--300 seconds. The half-open
owner reset bucket at its stated precision must overlap the interval from the
exact AgentMonitor reset through that reset advanced by the observation delay,
and their intersection must contain a point after owner observation. Every
non-100, null, imprecise, missing/extra-window, stale, or otherwise unexplained
case keeps the strict rule and blocks. Finish by typing the exact phrase
`I CONFIRM CODEX USAGE`; a fractional percentage, mismatch, or wrong phrase
also blocks the writer without producing a witness.

For the owner-approved representative comparison, set
`AGENTMONITOR_M5_SAMPLE_ACCOUNT_IDS` to two distinct registry account IDs
separated by one space before starting the same command. At least one must be
among the verified selected outcomes; both must be active monitored Codex
accounts with distinct verified live identities. The browser still proves
identity, current quota, rendered values and retained history for every verified
selected account. It separately proves the two sample accounts and asks the
owner for official `/status` observations only for those two. The v2 witness
records separate fleet and sample counts and digests. A sample comparison does
not claim an independent official comparison of unsampled accounts. The same
precision, freshness, owner confirmation and create-once rules apply.

The result uses the closed schema `agentmonitor.m5-quota-witness.v1`. Its exact
top-level fields are `schema`, `implementation_revision`, `service_pid`,
`service_source_revision`, `service_start_time_ticks`, `recorded_at`,
`owner_confirmation`, `provider_key`,
`provider_version`, `source_id`, `account_count`, `window_count`,
`owner_outcomes_digest`, `identity_set_digest`, `collection_run_set_digest`,
`quota_value_set_digest`, `owner_observation_digest`,
`rendered_value_set_digest`, `history_value_set_digest`,
`browser_proof_digest`, `registry_graph_digest_before`,
`registry_graph_digest_after`, `browser_registry_digest_before`, and
`browser_registry_digest_after`. `service_source_revision` must equal the clean
gate revision and the available value returned by the running service's
Operations version inventory. These fields bind that service revision and the
selected service PID/start identity to the owner outcome, exact Codex `0.160.0`
rate-limit source, verified-account and window counts, distinct identities,
collection lineage, exact quota values, owner observations, API/DOM/history
proof, and unchanged Registry state. The file stores only aggregate counts and
SHA-256 digests, never the entered values, aliases, identities, profile paths,
provider payloads, or content.

The private browser proof keeps only the opaque current observation ID needed
to bind each safe window row to retained history; it discards rendered display
text. The Python writer independently rebuilds the same canonical history
material and accepts `history_value_set_digest` only when it matches. After
that history binding succeeds, the writer removes `current_observation_id` and
passes only the closed five provider-neutral quota fields into policy
reconciliation.

The fixed file is an owner-owned, regular, single-link, no-symlink `0600` file
of at most 16 KiB below the resolved owner-owned `0700` root. The command
creates it once with exclusive creation and never edits or replaces it. At gate
start, `AUTO-M5-EXIT` accepts it for at most 15 minutes after `recorded_at`, with
at most one minute of future clock skew. The gate rereads the identical file at
the end against the actual completion time. A stale, changed, wrong-revision,
wrong-service, wrong-outcome, or Registry-mismatched witness is **Blocked**.
Because the real alert lifecycle can take longer than this freshness window,
create the quota witness after the alert witness and immediately before
`AUTO-M5-EXIT`, even though its validation is documented here next to the
owner-outcome prerequisite on which it depends.

The fixed `<owner-data-root>/m5-alert-witness.json` prerequisite uses the same
file controls and the closed schema `agentmonitor.m5-alert-witness.v2`. The
application-owned witness binds the current 40-character implementation
revision, an equal `service_source_revision` read from the running service's
Operations version inventory, and the selected service PID/start identity; the
service start and browser check times plus an exact public-version digest; one
verified outcome account;
Codex provider, source, adapter, parser, mapping and schema-bundle versions; an
equal alert record version and aggregate sequence of at least four; ordered
service start, fresh opening (`opened` for a new fingerprint or `reopened` for
a retained recovered fingerprint), deduplication, owner action, recovery,
service check, and
recording times; and an `owner_action` of `acknowledged` or `snoozed`. Its seven
open, dedupe, browser, recovery, and source-proven assertions are true. Eleven
service, source-event, observation-stage, delivery, history, owner-action, and
registry fields are SHA-256 digests; the registry scope is
`all-public-registry-fields-v1` and its before/after digests are equal. A receipt
older than eight days, from another revision/service/account, with changed
registry state, or with an incomplete lifecycle is rejected. Its final registry
digest must also equal the gate's current read-only browser preflight. Only the
receipt's SHA-256 digest and the safe action category reach the final receipt.

Create the real lifecycle in this order:

1. Choose one verified Codex account with a current genuine reading above 0%
   remaining. Keep monitoring enabled and record only its opaque dashboard
   account ID for the command selector.
2. In **Alerts → Alert rules**, create an enabled **Capacity remaining** rule
   for that one account with warning and critical both set to 100%. Wait for a
   newer scheduled Codex collection and alert delivery. The account's genuine
   current reading must open the alert. It records `opened` for a new
   fingerprint or `reopened` when an earlier recovered generation is retained.
   Keep the condition active and wait for a second distinct scheduled Codex
   collection and delivery to record the repeated condition. Do not delete
   retained history or insert or edit quota, event, or alert rows.
3. In **Alerts**, open **Details and history** for that alert and click either
   **Acknowledge** or **Snooze 15 minutes** once. Keep the resulting opaque
   alert ID as `AGENTMONITOR_TEST_M5_ALERT_ID` if the account has more than one
   recovered capacity alert.
4. Return to **Alert rules**, archive the temporary 100% account rule, then
   create an enabled rule for the same account with warning and critical both
   set to 0%. Wait for another scheduled Codex collection and delivery. A
   newer genuine reading above 0% must recover the same alert. If the real
   reading is 0%, select another verified account or wait for a real provider
   reset; never edit telemetry to manufacture recovery.
5. Confirm the alert card says **recovered**. Use the card's **Load more
   history** control until it is no longer offered, then confirm the history
   shows the latest opening, repeated condition, owner action, and recovery in
   that order.
   Leave both rules and all alert history intact until the M5 exit gate
   succeeds.

After creating the owner-outcome file and completing that lifecycle, create the
alert prerequisite from the same clean revision and pre-gate service tuple:

```bash
python3 tools/automation/run.py AUTO-M5-ALERT-WITNESS
```

Set `AGENTMONITOR_TEST_CODEX_ACCOUNT_ID` when more than one verified outcome
could supply the witness, and `AGENTMONITOR_TEST_M5_ALERT_ID` when more than one
recovered Codex capacity alert matches. The writer first proves that the source
open and repeated-condition events are distinct persisted genuine deliveries,
that the owner action has an authenticated command receipt, and that a third
distinct genuine event recovered the alert. It validates exact per-stage
observations and delivery receipts, alert history, the built browser, service
freshness and version inventory, and unchanged full public registry snapshots.
The source proof uses one M05 query for exactly the three distinct event IDs and
consumer `m07-alert-capacity-v1`; it cross-checks each result against M07's
published receipt by event ID, acknowledgement receipt and time, processed
time, and payload digest. The query must use the outbox and delivery primary
keys, decode only those three events, and finish within 30 seconds against the
current owner database without whole-outbox traversal.

The browser child reads the unchanged history API in pages of 200, accepting at
most 200 pages, 40,000 unique entries, and 199 cursor transitions after the
first page. It then uses only the selected card's **Load more history** control
until the UI reaches terminal state. API and DOM count, ascending sequence,
order, and digest must agree exactly, and dashboard mutation count must remain
zero. A repeated, missing, invalid, or overlong cursor; duplicate or wrong-alert
entry; nonprogressing order; partial terminal state; or bound excess blocks the
witness while preserving existing application history.

The writer is read-only: it does not replay delivery or mutate the lifecycle.
It creates the owner-only witness once and never replaces an existing witness.
Its browser child opens one temporary page through the shared loopback CDP
connection. After emitting the proof, it must close only that page and release
its owned Playwright client transport so the child exits inside the writer's
180-second bound. The owner's Chrome process, authenticated session, and
pre-existing pages remain open. A child that emits proof but retains its CDP
connection is still Blocked as `m5_alert_witness_browser_unavailable`; never
use `process.exit()` or close Chrome to mask that resource-lifecycle failure.

Run:

```bash
python3 tools/automation/run.py AUTO-M5-EXIT
```

The command first validates the current clean revision, holds both completion
and service-transition guards, and requires the exact successful activation
receipt plus its journal, rollback unit, rollback-runtime tree, candidate unit,
and current systemd ownership. It then validates all three exact private
prerequisites. Before the browser preflight, it runs the production
managed-profile identity and quota operations under the real system `strace`,
requires zero access or writes to the default Codex profile, and permits
provider-controlled writes only below the selected managed profile. It binds
only the activation-receipt digest, a sanitized containment digest, and
aggregate syscall counts to the final receipt, and requires the complete public
Registry graph to remain unchanged.

Managed-profile tree containment is evaluated through the enclosing private
root chain. The owner data root, intermediate `profiles` root,
`profiles/codex` root, and selected profile root must each remain the same
owner-owned `0700` directory before and after provider work. Ordinary modes on
nested provider-created files and directories do not require operator repair
while the validated private ancestors make them unreachable to other users;
their metadata still enters the before/after digests. `auth.json` retains its
separate private-file rule. A symlink, nonregular entry, foreign owner/device,
regular-file hard link, special bit, unsearchable directory, traversal error,
changed root identity, or write outside the selected profile blocks the gate.
Do not `chmod`, copy, relocate, or recreate provider state to satisfy this
check.

The containment verifier admits `ftruncate` only for an exact provider-lineage
descriptor annotation whose normalized absolute path remains inside the
selected managed profile, after current and traced-process mount topology is
proved unchanged and contains no mount at or below that profile. It counts an
admitted call as one provider access and one provider write. Missing, deleted,
ambiguous, malformed, default-profile, and outside-profile targets fail closed;
unverifiable descriptor targets report
`m5_codex_containment_fd_write_unverifiable`, while missing or changing mount
proof reports `m5_codex_containment_mount_topology_unverifiable`. Every other
successful descriptor-only mutator remains rejected.

For `unlinkat`, an absolute quoted target is evaluated directly. A relative
target is resolved only from literal `AT_FDCWD` plus the tracked working
directory, or from an exact decimal descriptor `3..999999` with a canonical
absolute normalized `strace -yy` annotation. Missing, deleted, relative,
escaped, control-bearing, noncanonical, or ambiguous annotations and syscall
results report `m5_codex_containment_trace_invalid`. A resolved default-profile
target retains `m5_codex_default_profile_access_detected`; another target
outside the selected profile retains `m5_codex_managed_profile_write_escape`;
replacement of the inode-bound `chmod` target or one of its ancestors remains
rejected. Any annotation present with an absolute target must still be
structurally valid. No annotation, target path, or raw trace enters evidence or
logs.

Pinned Codex CLI `0.160.0` uses a bounded Arg0 setup inside each managed
identity and quota app-server operation. Before the protected session
lifecycle, its root may attempt `mkdir(arg0_root, 0777)`, receive `EEXIST`, and
complete the already admitted inode-bound `chmod(arg0_root, 0700)`. These calls
remain ordinarily confined and must complete before the exact session
creation; they do not satisfy a session or child requirement.

The operation root must then create one canonical managed
`tmp/arg0/codex-arg0XXXXXX` session with `mkdir(..., 0777) = 0`, open its one
regular `.lock` child with
`O_RDWR|O_CREAT|O_LARGEFILE|O_CLOEXEC` and mode `0666`, and create exactly four
successful plain symlinks in this order: `apply_patch`, `applypatch`,
`codex-linux-sandbox`, and `codex-execve-wrapper`. All four aliases must use the
inode-validated pinned executable as payload. The lock and aliases must each
have exactly one successful same-operation `unlinkat` cleanup before the
operation actually closes. Cleanup order among the five children is not
significant; optional ordinary removal of the empty session directory is
allowed only after all five cleanups. Double-leading-slash and every other
noncanonical path spelling are rejected before containment comparison,
including separately decoded successful-open descriptor annotations.

Containment tracks syscall invocation and completion separately, including
unfinished/resumed records and live descendants. Its two broad Arg0 guards run
from exact session-`mkdir` invocation through completion of the final
fifth-child cleanup; records invoked in or crossing the interval stay guarded.
It rejects namespace movement or exchange throughout that interval, as well as
missing, duplicate, cross-operation, early, late, or unresolved cleanup. A
cwd-dependent relative path lookup fails closed when its
invocation/completion interval overlaps a successful unfinished `chdir` in the
same tracked `CLONE_FS` group. Absolute paths, descriptor-bound relative
cleanup, and relative lookups invoked after the `chdir` completes retain their
ordinary containment checks. A successful filesystem write without ownership
in the selected provider operation fails closed when its syscall interval
overlaps the protected Arg0 operation. `/proc/*/root`, directory-descriptor,
and other lexical aliases cannot bypass namespace or write-through protection.
Any additional link, hard link, `symlinkat`, retained final-tree symlink,
default-profile target, or outside-profile target remains a failure. The exact
provider-owned create/cleanup lifecycle is the only admitted link lifecycle.
Do not delete, rename, or repair Arg0 paths manually after a containment
failure. Preserve the unchanged managed profile and resolve the exact provider
version, chronology, or trace-shape failure before rerunning the gate. No path,
alias, session component, payload, PID, or raw trace enters the receipt or log.

The traced driver is bound by PID, start ticks, pidfd, process group, and
session identity. Cleanup signals the complete AgentMonitor-owned new session
before reaping its leader and shares the channel settlement deadline. Cleanup
that cannot prove termination reports
`m5_codex_containment_driver_deadline_exceeded`; do not signal or restart any
ordinary Codex agent in response.

It then binds the owner-observed quota values to its read-only browser
preflight, runs the canonical build, and restarts only the selected
AgentMonitor service. It waits for fresh post-restart Codex quota/history
lineage and requires those exact quota values and verified identities to remain
unchanged, executes the M3 dependency gate and exact M5 technical suite with
the no-skip plugin, observes five or six real exact-executable Codex processes,
and verifies account, history, provider, Overview, alert and Operations
behavior in the production build. Planning, quality, mutation, documentation
and Git preflight must all pass. Any Registry digest change, quota value change,
or prerequisite-file change blocks completion.

The same-user process scan may truthfully report `truncated` when unrelated
procfs entries disappear or deny safe metadata during the bounded read. That
does not invalidate five or six exact admitted Codex observations. The gate
independently rereads PID/start and executable identity for every selected row,
and excludes AgentMonitor's own managed-profile Codex children from the agent
sample. A missing working directory cannot provide positive representative
agent evidence. The gate still rejects fewer than five valid rows and records `partial` or `complete`
scan completeness in its sanitized receipt without retaining process IDs or
paths.

The gate supplies `AGENTMONITOR_M5_DETACHED_GIT_PREFLIGHT=1` only to its
internal `AUTO-GIT-PREFLIGHT` commit-mode subprocess. Do not export that
selector in the operator shell. It lets that one lane verify the already
required detached checkout by an unchanged 40-hex `HEAD` plus empty tracked
and untracked status. Ordinary `AUTO-GIT-PREFLIGHT` still requires a branch,
and the selector blocks for an attached or dirty checkout and for push or
release operations.

On success it creates `.agentmonitor-local/m5-current-gate-receipt.json` with
mode `0600`. It never replaces an existing receipt. The receipt contains the
revision, exact admitted public versions and digests, aggregate outcome/process
counts, the pre-restart `quota_history_value_set_digest`, the distinct
`post_restart_history_value_set_digest`, the authenticated-containment digest
and aggregate access/write counts, the activation-receipt digest, other
sanitized evidence digests, test count, zero skips and every required lane,
including `service_activation`. It contains no account identity,
alias, provider/profile path, process ID,
credential, provider payload, prompt, response, source content or arbitrary
environment value. Missing live prerequisites return **Blocked**; a failing
implemented boundary returns **Failed**. Neither result is M5 completion.

### Canonical M6 technical exit gate

Run the canonical M6 technical evidence command from the exact candidate
checkout:

```bash
python3 tools/automation/run.py AUTO-M6-EXIT
```

The command is non-interactive. It never asks the owner to repeat an account
disposition, enter an opaque ID, or provide a credential, and it does not
activate or restart the dashboard. It runs the already cataloged
`AUTO-BUILD`, `AUTO-M6-LOCAL-ADMIT`, `AUTO-QUALITY`, `AUTO-DOCS-CHECK`,
and `AUTO-PLAN-CHECK` checks directly. It independently requires the checkout
to remain at one exact clean revision before and after evidence collection and
receipt publication; ordinary Git branch, upstream, and author configuration
are not M6 acceptance criteria.
Those commands retain their documented real read-only boundaries and limited
scope. The same gate also runs the local inventory, provider-security checks,
responsive browser, signed-in installed Ollama dashboard check, and one
privacy-minimized read-only database snapshot. Each check is attempted
independently; a missing cloud prerequisite does not erase a valid local
result. Still-valid owner-guided account/scope outcomes are read through the
application's versioned state rather than requested again.

The gate does not promote a narrower proxy into acceptance evidence. M6-A02
remains `not_run` until both available machines have their own fresh real
inventory observation. M6-A04 requires the separate provider-authoritative
comparison from the approved catalog; equality between AgentMonitor's SQLite,
API and DOM proves only internal lineage. M6-A05 binds retained history to the
exact current observation and collection run and accepts an alert only when
its matching source event has one durable transition. M6-A07 remains
`not_run` unless a natural failure and recovery can be bound to the exact
target, binding generation, source and candidate interval while Claude, Codex
and dashboard continuity are evidenced through that same interval. Missing
sources stay visible and never trigger another owner prompt inside this gate.

The versioned selector catalog is
`tools/automation/m6-exit-catalog-v1.json`. It freezes the exact boundary,
selection policy, source-version policy and required limitation set for each
of nine external `M6-A01..A09` acceptance entries and five
`ST-OLL-001..005` story entries. `AUTO-M6-EXIT` owns these direct selections;
there are no fourteen subsidiary producer routines and no manually assembled
bundle. The command records one owner-only shared artifact below
`.agentmonitor-local/m6-evidence/`, containing only bounded statuses, counts,
digests, times and reason/limitation codes. It contains no account identity,
email, key, raw provider value/payload, profile path, screenshot, prompt,
response, source content or arbitrary environment value. Every scope binds the
same artifact digest plus its own frozen selection/source-version digests,
exact result and test count. Process-related results disclose
`sampled_process_coverage`, as required by M6-A06.

An unavailable real scenario is reported as `not_run` in that criterion and
the overall command exits 3. A naturally ambiguous, busy or inaccessible
boundary is `blocked` and also exits 3. An executed behavioral failure,
malformed result, digest mismatch, wrong scope or unsafe evidence artifact is
`failed` and exits 1. No one of those outcomes is completion.

The command rechecks the clean revision, catalog, current evidence times, and
the shared artifact before and after its receipt write. Only
when all checks and all 14 external selectors pass does it create one
owner-only receipt at
`.agentmonitor-local/m6-exit-receipts/<implementation-revision>.json`. The
receipt contains only safe counts, digests, check IDs, times, and declared
limitation codes. The successful durable receipt records nine technically
passed acceptance entries and explicitly lists `M6-A10` as pending. It is the
evidence presented for the formal owner review required by M6-A10; the command
does not grant that review to itself and therefore does not claim milestone
completion. The owner review follows the receipt without an interactive prompt,
repeated technical run, or extra attestation inside this command.

### Connect Codex from the dashboard

1. In **Accounts**, create a pending Codex account record through admin CRUD,
   give it a useful name, and assign its dashboard organization. Open that
   record; organization membership does not prove the provider identity.
2. Enter the intended **Codex account email** and click **Connect Codex** once.
   Complete only the official Codex browser sign-in that opens. Keep the
   password, verification codes, cookies, and authorization data on that page.
   The bounded login waits at most ten minutes before returning an expired
   outcome; start a new deliberate attempt if that happens.
3. Return to the account page and use **Check connection status**. A connected
   result means Codex returned the intended identity and monitoring was
   enabled. Quota remains unavailable until a genuine scheduled collection
   succeeds, so **Monitoring on** by itself is not a quota reading.

If Codex returns another identity, the attempt ends in the terminal
`wrong_account` state and monitoring is not enabled by that attempt. The
managed profile is quarantined from retry for that account record; do not
rename the record to make the mismatch appear valid. Review the selected
account and create or use the correct record before starting another deliberate
connection.

Every connection uses that account record's private AgentMonitor-managed
`CODEX_HOME`. The service rejects unsafe or symlinked roots and never selects,
reads, logs out, relocates, or rewrites the user's default Codex profile. Only
Codex CLI `0.160.0` is admitted. If the installed executable or reported schema
drifts, collection and connection fail closed; inspect **Operations**, restore
or approve an exact-version admission through the engineering process, and do
not treat a nearby version as compatible. See the
[Codex adapter runbook](../adapters/codex.md) for the admitted tuple, data flow,
failure codes, and current acceptance status.

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
One newly authenticated `2.1.289` managed profile subsequently passed a genuine
quota read with a provider-omitted reset preserved as Unknown. See the
[exact-version admission evidence](../evidence/claude-2.1.289-admission.md).
This selected-profile result does not replace the six-account M4 gate.

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
selected account only. The linked evidence preserves what remained at that
checkpoint; current M4 status is recorded in the implementation overlay.

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
has its own selected live gate; aggregate process ownership and M4 acceptance
are established separately by the accepted milestone receipt. See
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
4. If the provider reports no reset, confirm AgentMonitor exposes Unknown/Not reported rather than an inferred time.
5. Confirm polling delay and provider eventual consistency.
6. Do not edit stored observation to match manually.
7. If meaning/mapping is wrong, mark capability unverified/degraded, preserve sanitized evidence, and return through discovery/contract/TDD.

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

## Identify accounts of ordinary running Claude terminals

Open the account from Overview. Expand **Identify other Claude terminals**,
find the real PID/path/version, and open `/status` in that terminal yourself.
Choose its account and confirm the link. The account page then lists that
current terminal under **Agents using this account**. Confirmations are manual
observations with a timestamp; reconfirm or unlink when you change the account
inside the terminal. AgentMonitor never switches or interrupts it. Terminals
with reused PIDs, another boot/scope or changed executable images do not inherit
old confirmations.

This process view is independent of Claude quota/auth parser admission. It
scans only safe owner-controlled native executables already present in Claude's
versions directory, validates each official version banner, and reads guarded
OS metadata. A missing exact quota binary can therefore leave Overview quota
stale while current terminals remain visible on the account page. The time
shown with quota on Overview is the quota reading time, not agent activity.
Processes whose executable was deleted after launch cannot be revalidated from
disk and are omitted, so this view must not be treated as proof of a complete
fleet. Detected permission, exit, deadline and candidate-limit omissions mark
the response partial/truncated. Do not reinstall, downgrade or relink Claude
merely to populate the process view.

A repeated email in Overview can mean two distinct registered profiles signed
in to the same provider identity. Fresh successful evidence is grouped into one
quota row with **connected profiles** and separate review links. The configured
account name can differ from Claude's current identity; use the corresponding
record's admin connection workflow to review it. Grouping does not alter any
profile, registry record or underlying quota history.

M06 owner confirmations use `owner-process-account-associations-v1.json` and
`.owner-process-account-associations-v1.lock` in the private data root. These
are metadata settings, not provider telemetry or credentials. A SQLite-only
backup omits them. Preserve them with owner-only permissions and checksums when
performing an approved offline same-installation backup; validate the versioned
format and current process identity after restore. Do not restore across users
or installations. Full M08 backup/restore automation remains Blocked and is not
accepted by the account-view gate. Corrupt/unsafe settings fail closed and are
never silently reset. See ADR0015 and the account-agents progress record.

Focused live verification is `python3 tools/automation/run.py AUTO-ACCOUNT-AGENTS`
with `AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT`,
`AGENTMONITOR_TEST_DASHBOARD_ORIGIN`, `AGENTMONITOR_TEST_AGENT_ACCOUNT_ID`,
`AGENTMONITOR_TEST_AGENT_PID`, and `AGENTMONITOR_TEST_AGENT_DATA_ROOT`. Use only
local AgentMonitor browser/data-root selectors, no provider paths/credentials.
The command requires a real owner-completed confirmation and never creates one.

### Ollama cloud reading freshness

The candidate Ollama cloud freshness deadline is an AgentMonitor policy, not
an Ollama guarantee. It is the observation time plus the greater of 15 minutes
or two nominal round-robin turns per monitored cloud account, allowing 70
seconds per account per turn (the 60-second minimum gap plus up to 10 seconds
of jitter). A one-shot verification counts as a participant even before normal
monitoring is enabled. If the account count cannot be read consistently, the
freshness is unknown. A longer provider cooldown can make a reading stale
before its next permitted poll; the policy never shortens that cooldown.

The current candidate has no audited administrator setting for this policy;
the default is not editable in the dashboard. Provider access, a live cloud
reading and the resulting stale/current display remain unverified until the
owner's credential-policy conflict and live verification are resolved.
