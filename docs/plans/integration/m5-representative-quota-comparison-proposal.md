# M5 representative quota comparison proposal

Status: Owner approved 2026-10-30; implementation and milestone acceptance remain outstanding. The owner approved the representative comparison and its stated verification limit in chat.

The owner directed that the official usage comparison should not require
manually checking every account. Preserve the four selected account outcomes
and real full-fleet collection, identity, dashboard rendering and retained
history checks. Compare official usage for representative accounts and report
the sample and its limits explicitly; never represent unsampled accounts as
independently compared with the official view.

This proposes a change to the M5 plan's per-account interpretation of
`AC-LIVE-005`; it does not change `AC-LIVE-002` (four account outcomes),
`AC-LIVE-004` (approved live scenario matrix), or `AC-UI-002` (real dashboard
data). Sampling establishes correctness for the observed accounts and windows,
not independent reconciliation of every displayed account. The owner must
accept that verification limit as part of the plan decision.

The two observations supplied on 2026-10-30 matched the dashboard, but only
one belongs to the existing selected four-account set. Both are time-sensitive;
they do not constitute an existing canonical quota witness. The proposed
policy must define how a second real monitored account outside that selected
set is bound and independently checked without changing the selected outcomes.

## Proposed implementation and acceptance

- Keep all verified selected accounts subject to current identity, collection,
  rendered quota and history proof and keep the unavailable outcome explicit.
- Bind at least two distinct real monitored Codex accounts to a representative
  official-view sample, including at least one verified selected account. Check
  every displayed window and reset using the existing reconciliation rules.
- Version the private witness to distinguish fleet coverage from sample coverage;
  validate membership, distinct identities, timestamps, service and revision,
  and reject missing, stale, mismatched or fabricated evidence. Preserve privacy.
- Update the final gate, tests, approved M5 acceptance text and runbook together.
  Retain current strict behavior for old witness versions; do not relabel old
  or incomplete evidence as a pass.
- Prove red and green behavior, including one sampled account only, duplicate
  identities, missing fleet lineage, incorrect windows, stale sample, and two
  valid distinct real accounts. Run the full current-revision M5 gate and seek
  owner acceptance only after it passes.

## Operational impact to resolve before implementation

The current gate validates the owner outcomes and alert witness against the
exact implementation revision, service PID and service start marker in
`read_owner_outcomes_v1` and `read_alert_witness_v1`. A new deployed revision
or service would therefore reject those existing artifacts. Preserve their
original files and prove an explicit migration from the old revision and
service to the new one, or repeat the affected live checks if an honest
migration cannot be established. Do not simply relax revision or service
binding. No provider profile or running agent is changed by this proposal.
