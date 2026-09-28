# Change plan: connect additional real Claude accounts

- Status: Approved for the bounded connection work by the owner's direction to
  connect the additional SDK accounts, authorization for all needed system
  actions, and instruction to continue through the shared browser.
- Owner: M02 registry coordination; A01 owns all Claude behavior; root owns
  operational and shared-file integration.
- Parent: M4 `ST-FLEET-001`, A01 `CLA-I09`, M02 V1.
- Requirements: `FR-ACC-001/003/005/006`, `FR-AUTH-002/003/006`,
  `FR-SAFE-001/002`; bounded `AC-LIVE-006/007`.
- Contracts: existing identity `CTR-PROV-005` V1; no public API or database
  change in the initial authentication increment.

## Outcome

Connect the real accounts selected in admin through official owner-controlled
Claude authentication in separate AgentMonitor-managed profiles. Account names
and SDK membership come from admin CRUD. No account identifier is hardcoded.
The owner completes provider sign-in in the browser, and AgentMonitor verifies
the provider-reported email before any monitoring association is enrolled.

## Scope and sequence

1. Register the requested additional accounts through the real admin UI.
2. Add A01's managed-profile identity read and safe profile-root validation in
   `backend/src/agentmonitor/adapters/providers/claude/authentication/identity.py`.
3. Codify owner-controlled official login in
   `tools/providers/connect_claude_profile.py`. It selects a real registered
   account through M02, derives an opaque private directory under the selected
   AgentMonitor data root, and uses Claude's official `auth login --claudeai`.
4. Owner completes the official browser flow and native first-run setup; the
   tool checks exact identity. No AgentMonitor code edits provider settings.
5. Continue M02 profile enrollment, per-profile collection, and generated V1
   dashboard connection controls as subsequent increments. Authentication alone
   does not activate a pending account or claim that its quota is monitored.

Default profiles and existing running agents are protected throughout. The
initial tool changes no registry record, monitoring preference, or telemetry.
It does not invoke logout, copy credentials, inspect provider files, accept
codes, log OAuth URLs, or manipulate a user's default browser profile.

## Current evidence and contract impact

The owner dashboard has one connected default Claude profile. The additional
admin records were created through the shared real browser, assigned to SDK,
and verified pending with monitoring disabled. Installed admitted native Claude
is `2.1.282`. Its official login help supports `--claudeai` and `--email`.
A real `auth status --json` invocation with only `CLAUDE_CONFIG_DIR` pointing
at a fresh private directory reports no logged-in account. The default HOME
value is preserved; no process-global environment is changed.

Official references:

- [CLI commands](https://code.claude.com/docs/en/cli-reference).
- [Separate account directories](https://code.claude.com/docs/en/env-vars).
- [Provider-managed credential storage](https://code.claude.com/docs/en/authentication).

The internal A01 reader gains an optional managed root with safe defaults;
existing default-profile callers retain their behavior. No migration,
dependency, public contract, event, OpenAPI, or generated-client change is
required for the initial increment. Later coordinator/API work requires its
own explicit contract assessment within this change.

## Test-first sequence and completion gate

The real installed-CLI tests must fail first because the identity reader cannot
target an isolated managed profile. They then verify a fresh profile remains
unidentified, independent native status agrees, insecure/symlink/default roots
are rejected, and the default profile identity is unchanged. No provider
responses are constructed or replayed.

```bash
backend/.venv/bin/python -m pytest \
  backend/tests/adapters/providers/claude/live/test_managed_identity.py -q
```

This command gates only isolated identity reads. Official login verification
requires owner interaction and remains Not Run until that interaction succeeds.
The canonical operational login command accepts the selected private data root
and opaque registry account ID. It must return a non-success result for failed,
expired, unavailable, or mismatched authentication.

## Security, privacy, operations, documentation, and rollback

### Dashboard connection increment (owner directed)

The owner's instruction to build dashboard authentication approves this next
`ST-FLEET-001` increment. M02 coordinates the selected pending admin record;
A01 owns official authentication and native setup; M03 publishes the additive
connection command/status port under `CTR-PROV-007` V1; P01 publishes account
connection POST/GET/DELETE operations; P02 consumes the generated V1 client.
M01 adds `write:reauth` to the authenticated browser administrator permission
set only; bearer token permissions and issuable scopes remain unchanged.
Existing public operations and default-profile behavior remain compatible.

The owner clicks Connect Claude. Only that authenticated, CSRF-protected,
version-checked, idempotent action starts the official CLI in the background
against an isolated managed root and opens an ordinary browser. Provider URLs,
codes, passwords, and credentials never enter the HTTP response or audit.
Safe lifecycle receipts beneath the private service data root retain opaque
request fingerprints, account IDs, timestamps, and closed outcomes; interrupted
flows are cancelled on restart and never automatically resume authentication.
One active sign-in at a time keeps account order explicit. Read-only status
requests never start provider I/O. Wrong identity, changed account version,
unsafe roots, and protected/default or already connected profiles fail closed.
The owner performs browser authorization. A01's managed quota subprocess uses
Claude's documented `IS_DEMO` presentation flag to skip terminal onboarding,
without editing provider settings or sending a conversation. Real native quota
reads with and without that flag returned matching percentages and resets;
identity checks remain separate. Default-profile reads retain their existing
environment. `--init-only` was rejected as an onboarding solution after real
fresh-profile verification still displayed theme setup. Newly authenticated
fresh-profile end-to-end verification remains required.

Tests must first observe missing connection HTTP/browser behavior, then verify
real SQLite/HTTP mutation protections, native isolated flows, generated-client
UI states, and a selected owner-completed sign-in and quota reading. Provider
output must not be fabricated or replayed. The selected live completion routine
must fail closed while owner interaction is incomplete. No schema migration or
new dependency is planned. Full M4 fleet/aggregation/runtime/alerts/operations
acceptance remains separate.

### Verified enrollment and multiple-profile increment

The owner's successful official sign-in authorizes the next already-planned
connection increment. M02 remains the primary owner. `CTR-REG-006` V1 gains
an optional `activate_pending_account=False` on its internal owner identity
command: explicit activation preserves the account ID, label, group, disabled
monitoring preference, optimistic version check, identity conflict rejection,
transaction, receipt, and atomic outbox. Existing callers retain their current
active-account precondition. No REST or database shape changes.

A01's internal quota reader and composed adapter gain an optional validated
managed root; default callers retain their exact protected-default selection.
M04's internal latest-source query gains an optional account filter so one
account's run cannot postpone another account. The service polls eligible
default and managed profiles separately and verifies managed identity against
M02 both before and after collection. A01 also checks identity around its native
quota read before any quota can be committed to M05. A private root is derived from the opaque
registry account ID beneath the selected service data root, never from an email.
`CTR-PROV-005` V1 and the observed-identity V1 response gain an optional
`profile_protection`, preserving existing constructors and API shape. The old
`scope=default_profile_quota` remains a legacy compatibility marker; new clients
must use `profile_protection` to distinguish default, managed, and unavailable
provenance. Generate OpenAPI/client normally; no enum or existing field changes.
The operator command's explicit `--enroll` performs enrollment and enables the selected account only
after a fresh exact identity match and unchanged protected-default identity.

A real service timeout exposed a permanent-stop policy. A01 may classify only
`usage_deadline_*` as a transient read failure; M04's optional default-false
flag admits a distinct future scheduled observation after the full five-minute
interval. The failed run and provider retry advice remain unchanged. Auth,
onboarding, trust, permission, version, and unknown failures remain blocked.
Managed dispatch reserves identity/cleanup time within the 30-second drain.

Real native CLI, SQLite, and service/browser evidence must cover managed quota,
explicit pending activation, unchanged default semantics, stale/conflicting
identity rejection, separate collection cadence, and per-account run lineage.
Add a canonical fail-closed managed-connection gate; missing authentication or
unexecuted collection is a non-success result. No dependency, credential copy,
direct provider settings edit, running-agent action, or schema migration is
approved or required. Native first-run setup belongs to the approved official
connection flow. Remaining dashboard login controls and full M4 acceptance retain
their separate incomplete status until their own real evidence exists.

Roots must be private, owned directories without symlink escapes. Only the
official provider CLI writes credentials. Login stdout/stderr are discarded;
no passwords, OTPs, OAuth URL, authorization code, or token reaches AgentMonitor
output. A fresh expected identity is compared against the safe CLI metadata.
The browser opener is an explicit local executable, passed only to the login
subprocess, and receives the official URL without AgentMonitor logging it.
Only named graphical-session environment keys are inherited for browser launch.
No new package or license admission is needed.

Wrong account, default-profile metadata change, provider-version mismatch,
unsafe root, login failure, or expired owner interaction stops the increment.
Provider authentication state is left provider-managed; rollback never logs
out or deletes any default or managed credential store. The evidence document
and operations runbook must state separately whether authentication, registry
binding, collection, and full M4 acceptance have actually been verified.

### Native quota redraw correction within the connection increment

Verification of the selected SDK records exposed real native
`usage_deadline_window_conflicting_duplicate` and
`usage_deadline_terminal_marker_missing` failures on an earlier
connected managed account. A01 owns correcting its admitted bounded
quota reader using genuine native output and allowlisted diagnostic
fields. No terminal output is persisted or replayed. The existing
real managed quota test supplies the failing boundary and must pass
after the correction. Parsing must retain authoritative window
labels, percentage/reset validation, current-render conflict
rejection, output bounds, and default/managed identity checks.
Earlier incomplete renders must not be presented as a new reading.
No dependency, provider file edit, migration, normalized contract,
source cadence, authentication, or running-agent action is needed.
