# Change plan: executable completion of all six M4 stories

- Status: **Approved for root-owned completion automation**.
- Plan version: `1.1.0`; root integration review: 2026-10-03.
- Owner: PLAN-INT; parent [M4 milestone plan](../../superpowers/plans/2026-09-19-agentmonitor-v1-m4-claude-fleet-alerts.md).
- Authority: active owner-authorized objective, fully implement M4 goals.
- Requirements: the six canonical M4 story requirement sets; `NFR-TEST-002`,
  `NFR-COMP-001`, `NFR-DOC-001` for the executable integration boundary.
- Acceptance: M4-selected `AC-LIVE-*`, `AC-UI-*`, `AC-PROC-*`,
  `AC-ALERT-*`, `AC-HIST-*`, `AC-OPS-*`, `AC-V1-*`, `AC-TEST-*`.
- Contracts: existing V1 module/API/client contracts; no provider or data change.

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
