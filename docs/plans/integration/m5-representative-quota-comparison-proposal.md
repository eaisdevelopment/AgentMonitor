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

The current activation chain ends with revision `468a937`; the running
candidate `10a7bc0` must be admitted as the next specific source so the
canonical activation can preserve the complete prior archive prefix before
rolling forward. This does not authorize arbitrary sources or replacement of
retained artifacts. The existing historical owner and alert witnesses retain
their original bindings; a new candidate requires an independently validated
migration or new evidence.

## History usability correction

The real fleet check revealed that the account history view loads the oldest
page of a full year, requiring thousands of rows to reach a recent reading.
The approved P02 account-workspace plan requires accessible real history and
preserved chart/table pagination. Keep the full 365-day option and add a
visible bounded range selector, initially showing 24 hours, so recent real
readings can be inspected promptly. No backend API, retained data, account or
provider behavior changes. Check the actual browser against real API data and
verify both the recent view and the full-year option. The predecessor-evidence
proof may accept only the exact reviewed history-view source digest in addition
to documentation and automation changes; the original alert and owner
evidence remains bound to its original activation and is never rewritten.

## Owner direction: retain the two supplied comparisons

On 2026-10-30 the owner explicitly directed us to use the two `/status`
screenshots already supplied and not repeat account checks. Treat each image
as a user-submitted historical observation, not as a current reading. Match
its account, windows, percentages and displayed reset precision to genuine
retained API history near the image file's modification time, a submission
proxy rather than a verified capture time. Bind the source image
by digest without copying its contents or persisting credentials or provider
payloads. Retain the file modification time and accurately label the
comparison as historical; never claim the owner typed a new terminal
confirmation. The selected fleet still requires independent current identity,
quota, rendered UI and history proof, and the final gate must pass normally.
This owner direction replaces the previous plan's requirement to ask the
owner to repeat the two official-view observations immediately before exit.

The live preflight remains bound to its exact current quota and history. After
the service restart, the browser verifies the newly collected values and
resets against the account page and retained provider history for the same
identities. Values can change between those two checks: for example, a fully
unused five-hour window advances its reset as time passes. The receipt retains
the separate preflight quota and post-restart history digests; it does not
claim the two readings were identical.
