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
4. Owner completes the official browser flow; the tool checks exact identity.
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
