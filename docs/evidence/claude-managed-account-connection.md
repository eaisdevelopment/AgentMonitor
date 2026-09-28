# Managed Claude account connection: progress and evidence

- Date: 2026-09-28.
- Scope: the owner's request to connect the additional SDK Claude accounts
  through admin and continue using a shared visible browser.
- Plan: [bounded connection change](../plans/integration/claude-managed-account-connection-change.md).
- Status: **Partial**. Admin records and isolated identity checks are verified;
  official owner sign-in is awaiting interaction. No additional account's quota
  is claimed monitored, and M4 remains incomplete.
- Primary owner: M02 coordination, A01 provider implementation, root operator
  integration. No domain, API, database, UI, or dependency change is introduced
  by the authentication code in this increment.
- Requirements: `FR-ACC-001/003/005/006`, `FR-AUTH-002/003/006`,
  `FR-SAFE-001/002`; bounded `AC-LIVE-006/007` evidence only.
- Contract: existing `CTR-PROV-005` identity DTO V1; no public schema change.

## Real admin and browser observations

The three requested additional SDK account records were created through the
authenticated production form in the shared visible Playwright browser.
Each mutation was followed by a versioned API read verifying the selected SDK
organization, pending lifecycle, and disabled effective monitoring. Existing
Claude polling continues on its already enrolled default profile.

The new Chrome session uses a private separate browser directory, and its
debugging connection listens only on loopback. The owner and agent interact
with the same page. Account addresses and screenshots remain runtime/private
artifacts; none is inserted into application source, tests, or this report.

## Isolated identity Red and Green

Canonical command:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/adapters/providers/claude/live/test_managed_identity.py \
  backend/tests/adapters/providers/claude/live/test_authentication.py::test_default_profile_reauthentication_is_rejected_before_provider_io \
  -q
```

The three new scenarios first failed with the expected missing API:
`TypeError: read_default_profile_identity_v1() got an unexpected keyword argument 'managed_profile_root'`.
After implementation the same scenarios returned `3 passed in 0.79s`; the final
rerun with the existing protected-default rejection returned
`4 passed in 0.75s`. Real installed native Claude `2.1.282` reported no identity
for a fresh private managed root, and an independent official CLI invocation
agreed. Default identity fingerprints matched before and after. Real public,
symlink, and protected default roots were rejected before invoking the CLI.

Targeted Ruff and strict Mypy passed for the changed source, real tests, and
operator command. The official login command's help was checked on the admitted
installation; it supports `--claudeai` and `--email`. There is no historical
Red-first proof for completing a managed login: owner sign-in has not yet
completed, and universal `AC-TEST-001` is not claimed for that flow.

`AUTO-QUALITY` passed against this checkout: 217 formatted files, strict typing
for 208 source files, zero boundary violations, unchanged compatible generated
V1 schema (41 operations), locked inputs, frontend typecheck, and production
build. Documentation passed for 256 Markdown files, synchronized planning
passed, and local Git commit preflight passed. These controls do not turn the
pending owner-authentication or M4 scenarios into Passed.

## Official sign-in stage

`tools/providers/connect_claude_profile.py` is the canonical owner-operated
command. It reads the selected pending record through M02, selects the admitted
installation, creates an opaque private profile beneath the AgentMonitor data
root, and delegates login entirely to Claude's official CLI. The account label
is an expected identity only; the native status must verify it after login.

The first attempt returned `CLAUDE CONNECTION: AWAITING OWNER SIGN-IN` and its
official browser opener was invoked. The shared Chrome session gained the
provider sign-in tab. That confirms handoff/start only: successful provider
authentication, post-login default preservation, registry binding, quota
collection, wrong-account live verification, and the full M4 gate remain
**Not Run / awaiting owner action**. No provider login page fields are scraped
or screenshotted, and no raw URL, code, token, or login output is inspected.

### Owner-reported verification failure and ordinary-browser retry

The owner reported that the provider's human verification repeatedly reloaded
in the shared Playwright browser. The first operator command ended with
`CLAUDE CONNECTION: BLOCKED — expected managed identity not verified` (exit 3).
That is a failed authentication prerequisite, not successful connection.

Cloudflare lists browser automation frameworks, including Playwright, as
[unsupported for production challenges](https://developers.cloudflare.com/cloudflare-challenges/reference/supported-browsers/).
The browser environment is therefore a likely contributor; the exact cause
has not been established. A fresh official CLI login was started with a private
ordinary Chrome window, without browser automation or a debugging connection.
Its opener was invoked and its own Chrome process was verified running using
only the private browser's lock metadata. No provider page, input value, token,
challenge answer, browser fingerprint, or cookie was inspected or manipulated.
The shared dashboard session remains available. The retry awaits owner
verification/sign-in and is not recorded as Passed.

## Security, privacy, compatibility, and follow-up

The native provider retains its credential store. The subprocess environment
uses official `CLAUDE_CONFIG_DIR`, retains the real HOME value, omits provider
environment credentials, and includes only named graphical-session metadata
when launching the browser. Profile roots are private, owned, and free of
symlink escapes. Default profiles cannot be submitted as managed roots. The
legacy coordinator entry remains unavailable; this operator stage does not
silently enable dashboard reauthentication or registry enrollment.

No database migration, public API/client change, dependency/license change,
agent process mutation, default logout, provider credential read/copy, or
telemetry construction occurred. The only cancellation target is the command's
owned official login child; monitored agents are never signalled. Rollback
leaves all default and newly managed provider credentials provider-managed.

Files: A01 `authentication/{identity,reauthentication}.py`, the new native
`live/test_managed_identity.py`, operator `tools/providers/connect_claude_profile.py`,
the linked change plan, this evidence, documentation index, and runbook.
Remaining work: owner sign-in, verified pending-account enrollment, independently
scheduled managed-profile quota collection, generated dashboard connection
controls, and the remaining fleet/runtime/alert/operations M4 goals.
