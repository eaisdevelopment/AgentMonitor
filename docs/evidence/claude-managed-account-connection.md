# Managed Claude account connection: progress and evidence

- Date: 2026-09-28.
- Scope: the owner's request to connect the additional SDK Claude accounts
  through admin and continue using a shared visible browser.
- Plan: [bounded connection change](../plans/integration/claude-managed-account-connection-change.md).
- Status: **Partial** for the full requested fleet. All three additional SDK
  accounts have verified official authentication, registry enrollment, and
  selected real managed quota/browser gates. All four SDK records are active
  with effective monitoring. The subsequent native redraw correction and
  remaining fleet/M4 acceptance are tracked below.
- Primary owner: M02 coordination, A01 provider implementation, root operator
  integration. The initial authentication increment changed A01/operator code;
  the subsequent increment adds M02 activation, M04 account-scoped cadence,
  service composition, optional API provenance, and visible admin names.
- Requirements: `FR-ACC-001/003/005/006`, `FR-AUTH-002/003/006`,
  `FR-SAFE-001/002`, `FR-QUOTA-001/002/005/006`, `FR-COL-004/007`;
  bounded `AC-LIVE-006/007` and `AC-UI-002/003/005` evidence only.
- Contracts: `CTR-PROV-005` V1 gains optional receipt profile protection;
  `CTR-REG-006` V1 gains explicit optional pending activation; the M04 V1
  latest-source query gains an optional account filter. The V1 observed-identity
  API/client gains compatible optional profile provenance. No database migration
  or dependency change.

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
Red-first proof for completing a managed login; universal `AC-TEST-001` is not
claimed retroactively for that flow.

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
authentication, post-login default preservation, registry binding, quota,
and wrong-account verification were **Not Run at that initial handoff**.
The subsequent results below supersede that stage; full M4 remains incomplete.
No provider login page fields are scraped
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
The shared dashboard session remains available. The ordinary-browser retry
returned `CLAUDE CONNECTION: AUTHENTICATION VERIFIED — registry binding and
collection still required` with exit 0. Fresh native status verified the first
additional account's exact expected identity and unchanged protected default.
That result passed authentication only; it did not yet enroll the registry.

## Verified enrollment and separate collection

The new real managed source tests first failed with
`TypeError: collect_usage_once() got an unexpected keyword argument 'managed_profile_root'`.
After adding isolated source selection, the real read returned
`usage_blocked_onboarding`; that failure was retained. An ordinary owner-visible
terminal opened the official managed CLI first-run setup. A subsequent real
quota read passed (`1 passed in 4.82s`) with matching before/after managed
identity and unchanged default identity. No provider settings file was edited.

M02's explicit pending-activation test first failed with the missing
`activate_pending_account` argument. Green verified the same ID/name/group,
version increment, retained disabled preference, idempotent receipt, and
transactional rejection of stale versions and a duplicate real identity.
Existing callers still reject pending accounts unless explicitly authorized.
The default-false command fingerprint preserves historical receipt compatibility.

The account-scoped latest-source query first failed on its missing `account_id`
keyword. A01's managed adapter and expected-fingerprint checks first failed on
their missing constructor arguments. Green uses two different real identities
to reject wrong-account collection before quota I/O; no fabricated identity or
provider result is used. The adapter verifies identity again before returning
quota to the durable capacity sink, and the service verifies its registry binding.

The operator's new `--enroll` and owner-terminal `--setup` options first returned
argparse exit 2 before implementation. Green exercised the real selected account
and private profile; redirected setup returns a bounded non-success before any
provider operation. The new collector test first failed on the missing managed
root argument, then passed with a real scheduled managed run and exact native
identity (`1 passed in 9.32s`). One account's run does not control another's cadence.

The real browser initially displayed `Connected Claude profile` for the newly
active record, hiding its admin name. It now displays the selected admin name
while awaiting quota and reserves provider-verified wording for a matching
current collection receipt. The shared browser confirmed the account heading
and Account/State/Left/Path workspace. No values are seeded or hardcoded.

The canonical gate is `python3 tools/automation/run.py AUTO-CLAUDE-MANAGED` with
the four explicit real account/dashboard selectors documented in the runbook.
The first browser run returned `profile provenance missing` before the optional
API field existed. The latest gate returned `11 passed in 7.88s` for native,
registry, and cadence checks, then honestly remained Blocked because a fresh
service receipt was not yet available after restart. No cadence was shortened.
The test-collected quota is never assigned a freshly read identity retroactively.

`AUTO-QUALITY` passed for 223 formatted files, 213 strictly typed files, zero
boundary violations, compatible generated OpenAPI/client (41 operations),
locked dependencies, frontend typecheck, and production build. The new OpenAPI
digest after the recovery change is
`e243b8675470fcf0bc289f161d29d1869af1f4970f9646bb00ec7412b8756191`.
Documentation (256 files), synchronized planning, and the real automation
catalog/clean-clone checks passed. The prior one-default-profile polling gate
is not presented as a full multiple-account acceptance gate.

## Security, privacy, compatibility, and follow-up

The native provider retains its credential store. The subprocess environment
uses official `CLAUDE_CONFIG_DIR`, retains the real HOME value, omits provider
environment credentials, and includes only named graphical-session metadata
when launching the browser. Profile roots are private, owned, and free of
symlink escapes. Default profiles cannot be submitted as managed roots. The
legacy coordinator entry remains unavailable. Explicit operator `--enroll`
now activates only a verified selected admin record; dashboard login controls
and the full durable reauthentication workflow remain later work.

No database migration, dependency/license change,
agent process mutation, default logout, provider credential read/copy, or
telemetry construction occurred. The only cancellation target is the command's
owned official login child; monitored agents are never signalled. Rollback
leaves all default and newly managed provider credentials provider-managed.

Files: A01 identity/authentication/adapter/source and native tests; M02 V1
command and SQLite binding plus real integration tests; M04 query/repository
and polling tests; service composition/bootstrap; P01 identity response and
generated OpenAPI/client; P02 account heading/workspace; operator and canonical
verification tools; automation catalog/dispatcher/validation/snapshot bindings;
the linked plan, evidence, module/runbook documentation.

The first service-owned managed attempt timed out with the safe code
`usage_deadline_terminal_marker_missing` and remained Failed. That exposed a
permanent-stop policy: the later dashboard gate was Blocked. The new pure
cadence scenario first failed on the missing `transient_read_failure` argument;
Green returned `10 passed in 0.03s`. Only A01-classified transient read deadlines
permit a distinct new scheduled observation after the complete minimum
interval. The failed run is retained and provider retry advice is unchanged.
Auth/onboarding/trust/version/unknown errors remain blocked. Managed dispatch
also reserves time for its four identity checks within the 30-second drain.

After the real service restart, it collected and attested the selected managed
profile successfully. The real shared-browser gate returned `CLAUDE DASHBOARD:
PASSED — identified managed account and fresh quota through V1 API and real
browser`. The selected account's provider email, managed protection, fresh
windows, and collection-run lineage matched; its SDK record and table remained
intact. Final `AUTO-CLAUDE-MANAGED` returned `21 passed in 8.22s` and Passed
for the real V1 API/browser. This covers the selected managed profile only;
full M4 is not implied.

A later other-account sign-in was kept unassociated because its native identity
did not match the selected pending record. An ordinary fresh browser was opened
for the intended official owner sign-in; its interaction deadline expired
without a verified intended identity. That account remains Pending. No default
or enrolled profile was logged out or reassigned.

At that earlier handoff, remaining work included other account sign-ins,
dashboard connection controls, running-agent ownership, and M4 fleet/alert/
operations goals. The later dashboard result below supersedes the connection
control and one further account blocker.

## Subsequent dashboard connection

The owner completed official browser authentication for the second
additional SDK account using the new Connect Claude control. Its exact
identity, active registry binding, effective monitoring, and two fresh
service-owned quota windows were verified through the authenticated V1
API and real dashboard. No setup terminal was required for that flow.
`AUTO-CLAUDE-CONNECT` Passed for this selected connection; see the
[owner-completed dashboard evidence](claude-dashboard-connection.md).
The next selected SDK account and the full fleet/M4 acceptance remained
incomplete at that handoff. Historical wrong-identity and expired attempts remain failed
evidence; no default or enrolled profile was reassigned or logged out.

The owner subsequently completed the third additional SDK account through
the dashboard. Its selected `AUTO-CLAUDE-CONNECT` gate Passed; see the
second owner-completed dashboard verification in the same evidence.
All four selected SDK records are active with effective monitoring.
The native quota redraw correction and remaining fleet/M4 acceptance
are tracked separately; enabled monitoring does not guarantee a fresh
reading when the native source fails.

The subsequent A01 redraw correction passed the original selected
managed-account gate and repeated the latest owner-completed dashboard
connection gate. A current authenticated V1 read verified exact identities
and fresh service-owned quota lineage on all four selected SDK records.
See the final selected SDK observations in the dashboard evidence.
EAIS connections and the remaining fleet/M4 artifacts are not claimed.

## EAIS owner connections — 2026-09-29

The owner subsequently created and authenticated two EAIS records through
the dashboard. Both selected `AUTO-CLAUDE-CONNECT` gates Passed with exact
managed identity and fresh service-owned quota. The second record's first
native read failed; its normal scheduled retry succeeded without code,
profile, or cadence changes. See the [EAIS connection evidence](claude-dashboard-connection.md).
The current overview has six real account records across SDK and EAIS.
The remaining EAIS record and full fleet/M4 scope are still incomplete.
