# M7 account financial application and worker integration

Status: intermediate local implementation. First genuine monetary journey and
M7 completion remain unverified. No installed transition or owner configuration
was performed by this increment.

## Scope and contracts

T004/T005/T007/T010; FR-BUDGET-001/002/004/005, AC-TEST-001/003/005,
M7-A01/A02/A07/A09. M05 owns exact selected-report spend and the application
query; root composes published M02/M04/M05 ports and supervises billing workers.

- Additive CTR-CAP-006 2.2.0 in `contracts/budget_query_v1.py` publishes the
  account financial result with calculated spend, current/attempt reports and
  separate latest collection availability. Existing 2.1.0 storage query stays
  compatible. This is per-account evidence, not completed global aggregation.
- Additive CTR-COL-002 2.2.0 in `contracts/billing_actions_v1.py` publishes the
  owner check command/port. Existing 2.1.0 budget run/receipt semantics remain.
- The new GET and POST are additive `/api/v1` operations. OpenAPI and TypeScript
  are generated from the real production route factory, not hand-edited.
- No new schema, dependency, license, credential purpose or provider mutation.

## Behavior

`GetAccountBudgetCurrentV1` resolves actual M02 billing resource/scope metadata,
reads M05 report selections and M04 latest billing run through public ports,
and invokes pure exact spend calculation. Current complete reports retain their
original report identity/time even after a later attempt. Breakdown and unknown
cost reports cannot become total spend; genuine complete empty coverage supports
zero only with the explicit source flag. The final metadata reread rejects a
concurrent scope/account change instead of relabeling old figures.

Authentication and closed UTC/range filters belong to P01. The wire mapper omits
credential bindings and run fencing/digests, carries exact coefficient strings,
and does not calculate money. Successful metadata reads with no configured
billing connection have an available query and no financial value; missing
reports have separate unavailable coverage, never zero.

The Anthropic worker now uses the same 64-hex admitted source fingerprint as
M02/M04, not the distinct M03 catalog ID. The billing supervisor starts with the
application lifecycle and exposes a thread-safe wake hint after durable action
admission. No hint replaces the database queue. Existing Ollama supervisor
cadence and provider profiles remain unchanged. The installed service has not
been switched to this candidate.

## Red and Green

- New account query contract: missing module Red, then pinned interval/as-of
  validation Green.
- Exact report calculation: missing pure module Red, then exact 0.10+0.20,
  complete-empty versus unknown, and breakdown exclusion Green. An initially
  overlapping constructed pure test input was corrected to disjoint intervals;
  that invalid-input failure is not claimed as a product Red.
- Real empty migrated SQLite application: missing application module Red, then
  missing-account result Green with no financial records created.
- Real owned systemd process lifecycle: `wake` missing AttributeError Red;
  immediate subsequent worker invocation and cancellation cleanup Green.
- Combined query/contracts/worker/HTTP regression: **43 passed in 10.05s**.
  This includes real empty SQLite, HTTP and owned processes, not genuine billing
  reports. No mock provider, recorded response or seeded financial row was used.
- Account HTTP evidence: [first financial GET](m7-budget-http-2026-11-11.md).
- Check action HTTP evidence: [billing check](m7-billing-check-http-2026-11-11.md).
- Action production/replay evidence: [billing actions](m7-billing-check-action-2026-11-11.md).
- Canonical generator: compatible **82 operations** after the two explicit
  route/policy additions. Initial policy/surface errors were corrected in the
  admitted operation matrix; the checker was not bypassed.

Root's scoped strict mypy passed six account-query/contract/worker sources.
The canonical pure and persistence-schema selections now include the new pure
and empty-query cases. They remain narrower than full technical/live/browser
acceptance. Remaining checks and frontend evidence are recorded separately.

## Remaining work

Successful genuine billing admission, populated dispatch/commit/recovery,
monetary HTTP/DOM comparison, full provider coverage, monitoring actions,
Overview/group summaries, pinned history endpoints, analysis, installed rollout
and fixed M7 exit remain open. Empty reads and pure mapper checks do not close
these requirements. No successful 202/provider report or numeric forecast is
claimed from this evidence.

The installed service was active and root HTTP returned 200 during this work;
the shared browser's dashboard tab was at sign-in. This is availability only.
No credentials were inspected and no sign-in repetition is requested by this
engineering increment.
