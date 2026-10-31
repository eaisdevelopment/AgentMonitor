# ADR 0015: Owner-confirmed live process account settings

- Status: Accepted for the owner's account-to-terminal drill-down request.
- Date: 2026-09-29.
- Deciders: M06/root under the owner's implementation and system-action authority.
- Requirements: `FR-ACC-006`, `FR-DISC-001/002/004/007`, `FR-SAFE-002`.

## Context

Ordinary running Claude terminals expose safe OS process metadata, but the
approved read-only source does not prove their account identity. The current
default login and the account used to collect quota cannot identify a different
running terminal. Inventing provider sessions to store manual process links
would misrepresent the observed source.

## Decision

M06 owns explicit administrator-confirmed process/account associations as
versioned settings, separately from provider telemetry and session history.
The owner reads Claude's official `/status` screen and confirms an account in
the dashboard. Associations are labeled Owner confirmed with their timestamp;
they do not become provider-verified current identity or activity evidence.
Changing accounts inside a terminal requires a new owner confirmation.

Use an M06-owned `owner-process-account-associations-v1.json` settings file in
the existing owner-only AgentMonitor data root. This bounded exception to the
SQLite runtime plan stores process boot/namespace, PID and start ticks, provider
key, exact executable fingerprint, opaque account/actor IDs, confirmation time,
and revision. The executable fingerprint rejects replacement or exec changes
of the guarded process image. There are no paths, account emails, provider
sessions, conversation data or credentials.
No existing database schema, row semantics, or provider files change.

The adapter validates regular-file ownership, mode, link count, format/version,
size and record count; rejects symlinks and incompatible/corrupt data; serializes
writers under a permanent owner-only lock; writes and fsyncs a private temporary
file; atomically replaces the settings file and fsyncs its directory. A removed
association retains a versioned tombstone. Optimistic per-process revisions
reject stale changes; identical retries cannot create a second confirmation.

The query joins settings only to freshly guarded same-user exact executable
processes using boot/namespace + PID + start ticks. Exited or reused PIDs never
inherit a link. Account lifecycle/provider eligibility is checked through the
published registry query. No inference from paths, parent processes, timing,
current profile, argv, environment, or terminal contents is permitted.

P01 adds a browser-admin-only, CSRF-protected conditional mutation and optional
read fields to `/api/v1/process-locations`. The legacy provider-correlation
field remains unresolved. P02 consumes the generated V1 API only. AgentMonitor
does not control, interrupt, switch, or inject commands into an agent.

## Alternatives and consequences

An automatic telemetry launch workflow needs separately verified official
per-session identity/process evidence and cannot retroactively instrument an
ordinary running terminal. A new SQLite migration would require the unfinished
installed upgrade workflow; using unrelated existing tables or invented
sessions would bypass module ownership or falsify telemetry. The small settings
adapter gives the approved manual association behavior a persistent source.

The settings are not part of existing SQLite-only backups. Offline operator
backups must include the two owner-only settings/lock files when present;
restore settings only to the same installation. A boot/namespace mismatch leaves
restored entries unassociated. Full M08/native backup/restore acceptance remains
outside this increment. Deleting the settings loses owner confirmations, but
does not change provider state, quota/history, or running processes.

## Verification and rollback

Real built-browser and authenticated HTTP checks require genuine running
Claude processes and an owner-completed confirmation. No test creates a fake
provider account, agent or confirmation. Pure transition tests cover identity,
clear/tombstone, replay and stale-version behavior without I/O. Filesystem
controls use actual owner-only files and fail closed. Missing live confirmation
remains Blocked. Roll back the binary/frontend; the older binary ignores the
separate settings file, and existing API fields retain their prior meanings.
