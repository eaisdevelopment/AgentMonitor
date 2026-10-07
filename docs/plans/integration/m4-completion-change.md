# Change plan: executable completion of all six M4 stories

- Status: **Approved for root-owned completion automation**.
- Plan version: `1.3.0`; root integration review: 2026-10-06.
- Owner: PLAN-INT; parent [M4 milestone plan](../../superpowers/plans/2026-09-19-agentmonitor-v1-m4-claude-fleet-alerts.md).
- Authority: active owner-authorized objective, fully implement M4 goals.
- Requirements: the six canonical M4 story requirement sets; `NFR-TEST-002`,
  `NFR-COMP-001`, `NFR-DOC-001` for the executable integration boundary.
- Acceptance: M4-selected `AC-LIVE-*`, `AC-UI-*`, `AC-PROC-*`,
  `AC-ALERT-*`, `AC-HIST-*`, `AC-OPS-*`, `AC-V1-*`, `AC-TEST-*`.
- Contracts: existing V1 module/API/client/data contracts remain unchanged;
  the exact A01 provider compatibility/parser behavior changes within those
  contracts, with no API, generated-client, database schema, migration, or
  dependency change.

## Outcome and ownership

`python3 tools/automation/run.py AUTO-M4-EXIT` is the completion command for
ST-FLEET-001/002/003, ST-ALERT-001/002 and ST-OPS-001 together. It verifies
required actual implementation/test/browser artifacts, executes the real
selected suites, rejects skipped/empty test results, runs the production
browser fleet/Overview/alert/operations acceptance and the local quality routines.
A missing implementation fails; absent genuine live prerequisites blocks.
A narrower selected-account pass cannot satisfy this command.

Root owns this plan, automation runner/catalog/tests, shared documentation and
the full release integration test/browser verifier. Module agents own their
assigned production and scenario tests. No hidden test endpoints, invented
provider data, new dependency, profile changes or running-agent control.

## Inputs, tests and safeguards

Private runtime selectors identify the actual owner data root, authenticated
local dashboard/CDP and owner six-account outcome matrix. The browser verifier
must bind each enrolled account to its current genuine identity/quota lineage;
owner-unavailable dispositions need the owner's actual recorded declaration.
The matrix is acceptance data outside source, never an application account
limit. Unresolved identities, unavailable conditions and missing confirmations
cannot be promoted to a pass. Existing default-profile guards remain mandatory.

Red: a real-checkout test invokes the cataloged gate without any live selector;
the current checkout has no M4 routine. Green: it runs and refuses completion,
first for the actual missing M4 artifacts, later for absent real prerequisites.
This tests completion safety, not product behavior; each module retains its
own meaningful functional Red/Green. Real story suites plus full integration
and browser checks are mandatory before this gate can ever return success.

## Contract, migration, documentation and rollout

Only additive automation registry/control changes occur in this increment.
Register the routine in the dispatcher, planning validator, real catalog test
and completion standard together. Module plans remain independently approved;
this plan does not authorize otherwise unapproved production changes or count
historical M3 release blockers as passed. Root adds the active M4 evidence
record as implementation proceeds and preserves historical evidence.

No dependency/license/privacy/schema impact from the gate itself. Actual M4
migrations require their own backup/quiescence/recovery verification, including
the separate M06 settings file. Rollback removes this routine registration
coherently; it never deletes owner data. Stop for shared ownership conflict,
false evidence, sensitive output or a changed story/contract; continue unaffected
module implementation. Full M4 remains incomplete until the gate really passes.

## Current-revision acceptance correction

The owner directed M4 to be closed against the current implementation after
M3 acceptance. The canonical command therefore selects a fail-closed successor
that preserves the historical runner as evidence and adds the following
mandatory controls:

- a clean 40-character Git revision and an explicit running AgentMonitor
  service PID whose closed command, loopback origin and private data root match
  the selected owner installation;
- a production frontend build before a bounded restart of that service from the
  clean checkout, with Linux PID/start identity held through receipt creation;
- six owner-selected registry records in two organizations whose administrator
  names match six distinct current Claude-reported identities, without writing
  identity values to output or evidence;
- a fresh post-restart quota collection for every selected account, with the
  current identity, capacity and history records bound to the same run;
- pre/post fleet metadata and identity-set digests, zero API mutations, the
  existing zero-skip M4 suite, fleet/Overview/alert/operations browser checks
  and every local gate; and
- one owner-only, create-once receipt containing digests and counts rather than
  account identifiers, addresses, profile paths or provider payloads.

The successor blocks before replacing the service when the preflight fleet is
ambiguous, including duplicate or wrong reported identities. A blocked run
does not create a receipt or acceptance claim. This correction changes
PLAN-INT automation and browser verification only; it adds no provider write,
registry mutation, public contract, schema, dependency or process-control
capability beyond restarting AgentMonitor's own selected dashboard service.

The owner's 2026-10-05 Overview sorting and collection-history separation
instructions also require the current-revision gate to execute the real
authenticated Overview verifier after the fresh six-account witness. The
existing `fleet_browser` lane covers both the identity/quota witness and that
built presentation check; no receipt schema or public contract changes.

## Current runtime witness

ST-FLEET-003 continues to require its real persisted Claude process/session
topology suite and the built global runtime view. A durable session does not,
however, have to be associated with one of the six selected accounts. Under
`FR-DISC-004` and `AC-PROC-003`, an ordinary terminal without approved strong
session evidence remains visibly unresolved; a historical durable row is not
proof that an agent is currently running under that account.

The positive current account/runtime witness therefore uses the additive
`CTR-RUN-006/007` owner-confirmed process view. After quota lineage settles, both
the preflight and post-restart fleet checks freshly read
`/api/v1/process-locations` and require an available real Linux scan containing
at least one running Claude process with a guarded association key, matching
association record versions, `owner_confirmed` provenance, and an account ID in
the final six active monitored selections. The built account page must render
that same guarded process with its PID, Running state, and Owner confirmed
label. Missing genuine process/owner evidence blocks; the verifier never creates
an association.

Account-scoped `/api/v1/sessions` reads remain zero-or-more. Every returned row
must stay within the requested selected account, and the global durable
session/tree and unresolved-state checks remain in the required zero-skip M4
suite and runtime page. Pure policy Red/Green coverage rejects unavailable,
unselected, cleared, or version-inconsistent live links. This correction changes
only PLAN-INT verification and documentation; it adds no public contract,
schema, provider write, process control, dependency, or receipt field.

## Claude 2.1.289 bounded partial lineage

The approved exact-version increment may return a partial quota collection
when Claude reports the new bounded model-specific weekly card that is outside
the closed V1 provider extension. The required current-session and all-model
windows remain current, persisted, and usable. The M4 witness therefore accepts
`partial` as fresh lineage only for provider `2.1.289` with adapter `1.0.3`, a
null error, terminal outcome `partial`, the complete V1 window allowlist, both
required windows, and partial history bound to the same observation IDs. Every
other partial tuple remains ineligible.

Reset display remains a field-level availability within each quota window. An
exact `2.1.289` reading may carry a current provider-reported percentage while
its reset display and reset instant are Unknown because Claude displayed no
reset line. That state remains eligible for the same fresh-lineage checks; the
witness must not invent reset data or reject the genuine percentage. Required
window keys, percentage values, observation/history linkage, provenance, and
all other freshness checks remain unchanged. A malformed or conflicting reset
is still a source failure rather than an Unknown field.

Pure Red/Green policy coverage binds this exception before the real browser
witness. The change does not alter the six distinct identities, post-restart
time bound, current observation/history relationship, registry digests, zero
mutation rule, API, database, provider extension, or receipt contract.

For every selected account, the built-page witness expands the quota technical
details and requires every rendered provenance row to show source
`claude.usage.ax-screen-reader.v1`, adapter `agentmonitor.claude · 1.0.3`, and
provider version `2.1.289`. The underlying current windows and their matching
history points must also carry the exact parser `1.0.3` and decision reference
`A01-M03-CLAUDE-2-1-289-001`; a stale field blocks both successful and partial
collection lineage. Both terminal outcomes require the current-session and
all-model weekly windows, no duplicate or unapproved window key, distinct
current observation IDs, and exactly one history point with the same window key
and observation ID. History completeness must be `complete` for success and
`partial` for partial.
