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
requires owner interaction and remains Not Run for a selected profile until
that interaction succeeds; completed flows are recorded in live evidence.
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
fresh-profile verification still displayed theme setup. A later selected
`2.1.289` managed profile completed owner authentication and a genuine quota
read; interrupted-flow recovery, the full wrong-account matrix, and M4 fleet
acceptance remain separate.

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

### Compact connected status (owner directed)

The owner's request to reduce the connected account notification approves
this bounded P02 presentation correction. A completed connection uses one
compact row with a text/icon connection label, current monitoring state,
and the existing read-only status action. Setup, attention, and recovery
retain their actionable guidance. Remove the repeated heading and future
quota promise from the connected state; capacity freshness stays in the
account activity view. No provider, API, domain, database, dependency, or
generated-client contract changes are needed (`CTR-UI-001` and
`CTR-API-001` V1 remain unchanged).

Extend the existing real-owner browser verifier before production changes
to reject a tall connected panel at 1920, 1280, and 390 pixels, verify
keyboard/status refresh access, and forbid authentication mutations.
The selected live `AUTO-CLAUDE-CONNECT` gate plus the pending-connection
browser scenario bound completion. Requirements `FR-UI-001/002/004`
and selected `AC-UI-003/005` apply. Rollback restores the prior static
bundle; owner/provider records and profiles are untouched.

### Compact quota overview (owner directed)

The owner's follow-up request approves a P02 main-page correction under
`FR-UI-001/002/004/005/006` and selected `AC-UI-002/003/005`: replace
the oversized introduction with a small heading and prioritize a dense
account/organization/state/remaining-quota overview above secondary
provider, collection, and session panels. Each genuine quota window has
its existing percentage formatter, bounded bar, freshness, and update
time. State describes quota-reading freshness and explicit registry
eligibility; it does not guess working-agent ownership or derive a new
capacity policy. Provider-verified names require exact current quota
receipt lineage. Pending, absent, stale, failed, and incomplete page
coverage stay explicit. Admin records remain dynamic.

P02 reads existing V1 registry, capacity, and observed-identity operations
through its generated-client wrapper, with bounded concurrency and
30-second read refresh. Add real populated-overview browser assertions
before production changes and include them in `AUTO-CLAUDE-CONNECT`.
The existing real SQLite/API/browser empty and pending scenarios must
also pass. No API, domain, provider, schema, migration, dependency,
or generated-client change is authorized or needed. This is a display
of per-account readings, not organization/global capacity aggregation,
forecasting, running-agent correlation, or full M4 acceptance.

### Organization filters and low-quota emphasis (owner directed)

The owner's 2026-09-29 request approves this additional P02 Overview increment
under `FR-UI-001/002/004/005/006` and selected `AC-UI-002/003/005`.
Compact organization toggle buttons use the existing dynamic registry. All
organizations is the default/reset; selecting a group isolates it, and further
selections include multiple groups. An empty selection has an explicit empty
view. Ungrouped and unavailable organization assignments remain selectable
when present. Selection survives manual and periodic refresh within Overview;
no browser storage or registry mutation is used.

Rows sort ascending by the lowest usable remaining percentage among their
returned quota windows, with unavailable percentages last and deterministic
ties. Every window remains visible and retains freshness/provenance. A usable
percentage at or below 20 receives a red bar and a textual Low indicator.
These are owner-requested display rules, not changes to producer health policy,
organization aggregation, forecasts, or running-agent ownership.

Extend the existing real-owner overview verifier before production changes to
cover single/multiple/reset/empty organization selection, retained selection
after refresh, actual quota ordering, inclusive red threshold and accessible
low wording, compact responsive layout, and zero mutations. Use actual current
V1 readings; never fabricate a provider response to reach a threshold.
The existing `AUTO-CLAUDE-CONNECT`, empty and pending browser scenarios, and
quality/documentation/planning/Git gates bound completion. P02 remains the
production owner; root owns verification and evidence. `CTR-UI-001` and
`CTR-API-001` V1 remain unchanged, with no backend, provider, generated-client,
schema, migration, dependency/license, or collection-cadence change. Rollback
restores the previous compatible static bundle and leaves all records and
provider profiles intact.

### Interactive Overview sorting (owner directed, 2026-10-05)

The owner's request to activate sorting from the **Organization**, **State**,
and **Quota left** headings approves this bounded P02 presentation increment
under `FR-UI-001/002/003/004/006` and selected
`AC-UI-002/003/004/005`. The loaded Overview page retains lowest usable quota
ascending as its default. Each approved heading is a keyboard-accessible button:
selecting a different heading starts ascending, while selecting the active
heading toggles ascending and descending. Exactly one heading exposes
`aria-sort`; its visible direction indicator is supplementary.

Organization sorting uses the displayed administrator-defined organization
name. State sorting uses the displayed reading-state label. Quota sorting uses
the existing minimum usable remaining percentage, with unavailable percentages
last in either direction. Name and account-ID ties remain deterministic.
Sorting applies after organization filtering and duplicate-identity grouping,
retains every native quota window, and survives manual and 30-second refreshes
while Overview remains mounted. It sorts only the bounded account page already
returned by V1 and makes no global-pagination claim.

Extend the real authenticated Overview verifier before production changes to
exercise all three controls in both directions, focus/keyboard access,
`aria-sort`, deterministic actual row order, filter composition, refresh
retention, compact layouts, and zero API mutations. No provider response or
quota value may be fabricated. `CTR-UI-001` and `CTR-API-001` V1 remain
unchanged; there is no backend, provider, generated-client, schema, migration,
dependency/license, persistence, or collection-cadence impact.

### Overview collection-history separation (owner directed, 2026-10-05)

The owner's instruction to remove the low-value **Collection runs** status card
from Overview approves a bounded P02 information-architecture correction under
`FR-UI-001/002/003/004/006` and selected `AC-UI-002/003/004/005`. The existing
`/collectors` page remains the only collection-run/history presentation and its
primary-navigation label and document title become **Collection / History**.
Overview keeps account quota first and does not issue the collection-history
request merely because the landing page opened.

The real browser verifier must first reject the old duplicated card, then prove
the Overview has no Collection runs region, the renamed main-menu action opens
the existing real collection page, direct `/collectors` navigation remains
valid, and navigation causes no mutation. No API, generated client, backend,
provider, schema, migration, dependency, persistence, collection cadence, or
data-retention behavior changes.

### Claude Code 2.1.289 capability admission (owner directed, 2026-10-05)

The owner's direction to finish M4 against the current real workstation
approves a bounded A01/M03 compatibility increment under `FR-DISC-008`,
`FR-COL-004/006/007/008`, `FR-AUTH-002/003/006`, `FR-SAFE-001/002`,
`NFR-COMP-001`, and `AC-LIVE-004/005/006/007`. At approval time, the default
native Claude Code executable was `2.1.289`; production discovery initially
failed closed with `claude_version_unverified`, which is the required Red. The
workstation default later advanced to `2.1.292`, which remains outside this
admission. The exact `2.1.289` executable is retained and selected for these
capabilities; the historical OTLP `2.1.282` executable is not retained.

Admit only the exact Linux x86-64 Claude Code `2.1.289` tuple through a
separately versioned, hash-bound technical mapping. Its approved capabilities
are read-only subscription quota, authentication health, bounded `auth status`
identity, and the official interactive `auth login` flow for an
AgentMonitor-managed profile. The write-capable login flow
requires owner browser interaction, writes only provider-owned state below the
selected managed profile root, and rechecks that the protected default identity
did not change. Increment the adapter and parser versions because compatibility
and parsing change. Preserve the historical `2.1.282` M0/M3 handoff,
approvals, receipts, and evidence bytes.

Generic `local.process.observation` through `linux.proc.process.v1` remains an
A04/M06-owned platform/runtime lane used alongside Claude monitoring. It is
not an A01 capability and is not bound to the Claude Code `2.1.289` admission.

The official OTLP session manifest remains pinned to `2.1.282`. OTLP launch
must request that exact capability version before provider-profile access or a
monitored process launch and fail closed with `claude_version_unverified` on
this workstation until a separate real OTLP probe is approved and run. The
general 2.1.289 resolver must not widen the OTLP tuple.

Before commit, use the selected retained `2.1.289` binary to prove exact
installation selection, bounded `auth status --json` identity behavior for
protected and managed profiles, an unauthenticated isolated-profile denial, genuine native
quota reads with the existing window bounds and truthful per-field reset
availability, stable identity before and after reads, exact provenance and
decision reference, and at least one fresh scheduled reading per selected fleet
account. The new mapping digest must be checked against its repository bytes.
Unknown versions remain non-invokable.

The first genuine `2.1.289` quota Red exposed one provider-format change: the
optional model-specific weekly card now has a bounded provider label rather
than the former fixed Sonnet-only label. The V1 Claude quota extension is a
closed cross-module contract, so this increment does not add an enum value to
that schema. A01 validates at most one bounded model-specific card as a render
boundary, omits it from the V1 value, and returns a partial outcome with the
closed `claude_model_specific_window_unsupported` omission and
`availability=unsupported`. The required session and all-model windows remain
available. More than one such card, an unallowlisted label, or
duplicate/conflicting values fails closed. There is no provider-extension,
wire-shape, or generated-client version change.

A later genuine read immediately after owner-completed managed authentication
exposed another valid `2.1.289` presentation: Claude reported a percentage for
the required current-session window without displaying a reset line. The live
test first failed with `usage_deadline_window_incomplete`. A safe structural
diagnostic confirmed only that the percentage field was present and the reset
field was absent; no value or raw provider output was retained.

The approved correction uses the `ClaudeResetDisplayV1` field availability
already defined within `ClaudeSubscriptionQuotaV1@1.0`. A recognized quota
window still requires a valid reported percentage with no conflicting value.
When it has no reset line, A01 preserves the percentage and maps reset display
to `value=None`, `availability=unknown`, and `precision=unknown`. A valid,
nonconflicting reported reset remains available with `provider_display`
precision. A present reset-shaped line that is malformed or conflicting still
fails closed and is never treated as absent. AgentMonitor never invents a reset
display or reset instant. Pure parser/mapper Red and Green evidence and the
same genuine managed-profile quota test bind this behavior.

The M4 current-revision fleet witness may treat that one exact `2.1.289` /
adapter `1.0.3` partial collection as fresh lineage only when the committed run
has current observations and partial history for the required session and
all-model windows, every returned key remains in the V1 allowlist, and no
provider error exists. Any other partial tuple or missing required window stays
fail closed. This preserves truthful partial status without weakening the six
identity, post-restart, history, freshness, or registry-immutability checks.

M02 installation-version reconciliation, when needed, must consume a genuine
A01 discovery outcome through the existing public application port while
holding the stable owner-only exclusive service lock. An occupied lock blocks
before mutation; no SQL edit or profile relinking is authorized. The canonical
M4 technical lane runs `AUTO-M3-TEST` plus the exact admitted auth/quota,
manifest/parser, installation/reconciliation, and OTLP version-gate tests. Its
fleet witness requires exact persisted and rendered provenance for the admitted
tuple. There is no public API, UI shape, database schema, migration,
dependency/license, credential, provider-profile, or running-agent-control
change beyond the already approved official managed login flow. Rollback
restores the prior manifest/code and leaves registry history, quota history,
provider profiles, and the default Claude installation untouched.
