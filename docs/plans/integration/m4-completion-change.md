# Change plan: executable completion of all six M4 stories

- Status: **Approved for root-owned completion automation**.
- Plan version: `1.0.0`; root integration review: 2026-09-29.
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
browser fleet/alert/operations acceptance and the local quality routines.
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
