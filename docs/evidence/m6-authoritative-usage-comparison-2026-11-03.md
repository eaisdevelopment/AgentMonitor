# M6 official Usage comparison producer — 2026-11-03

Status: candidate implementation with one genuine account comparison observed.
This is not a full M6-A04 or M6 exit pass; the canonical scope still requires
all accessible required accounts and its other acceptance conditions.

Requirements: M6-A04, AC-LIVE-005, FR-QUOTA-001/002/004/006. Ownership:
integration/browser evidence only. Existing CTR-REG-002, CTR-REG-012 1.1.0,
CTR-CAP-001 and versioned quota/operations APIs are consumed unchanged. No
schema, API, provider adapter, dependency, credential or service change.

## Approved pairing and comparison

The integration steward approved this pairing before implementation: read the
visible non-secret principal on the already signed-in official Ollama Usage
page, require one active owner-confirmed monitored Registry account with that
exact email label, and require its existing owner-selected dashboard account
page. This remains **owner-asserted pairing**, not provider verification of the
API key's identity or organization membership. The artifact explicitly retains
that provenance. No email, organization name, amount or raw provider DOM is
persisted or printed by the producer.

At narrow screen widths the provider shows only an avatar. The producer opens
only the account menu to read its visible principal and restores its previous
open/closed state. It hovers the Usage credits breakdown and reads only the
monthly credit amount, refill allowance/date and added credits. It does not
navigate/reload the provider, issue provider HTTP/API requests, read request
history, prompts, keys, billing, invoices, cookies or authorization headers, or
change provider settings. The dashboard uses a disposable page and GET-only
versioned API reads; no collection is triggered.

Comparison uses exact BigInt decimal arithmetic in USD. Displayed two-decimal
amounts are compared using decimal half-up rounding; displayed integers require
exact equality, conservatively avoiding a hidden fractional balance. Included
and purchased balances stay separate. The provider's refill calendar date is
compared with the source UTC reset date; no undisplayed reset time, denominator,
percentage or purchased-credit expiry is manufactured. Unsupported shapes or
missing facts remain Not Run; a supported stable value disagreement is Failed.

Before/after checks fence the visible provider principal/card, selected Registry
record, connection state/observation time and every current quota row. Only
request-level availability/as-of metadata is excluded from the stable-row
comparison. The public connection API does not expose credential generations;
the gate therefore additionally requires the exact observation lineage digest
to match both the built dashboard verifier and the real DB snapshot, whose
existing public ports prove current binding and approved source. Root approved
this compatible fence without adding an API field.

The producer permits one read-only retry if facts move. Its internal deadline
is 60 seconds and canonical subprocess deadline 90 seconds. No owner ceremony,
attestation file or independent subgate was added. Existing AUTO-M6-EXIT runs
the pure comparison tests and real producer, rejects malformed/minimization-
violating output, and keeps the accepted count zero if exact current lineage
cannot be reconciled.

## Red / green and actual evidence

- The new pure decimal/date suite first failed with `ERR_MODULE_NOT_FOUND`.
  The official full-month-name case then failed `unavailable` versus `matched`
  before full month names were supported. Final Node suite: **7 passed**.
- The closed comparison-envelope suite first failed with the expected missing
  module. It now rejects absent timestamps, wrong revision, overlong intervals,
  bad digests, excessive counts and added raw amount fields.
- `test_counts_without_an_official_comparison_cannot_pass_a04` first failed
  because summary counts alone yielded Passed. The classifier now requires the
  actual comparison envelope and successful producer boundary.
- Independent review found that an envelope count greater than the reconciled
  target count could still pass the pure classifier. The exact-count regression
  failed with `passed` instead of `not_run`; the classifier now rejects both
  smaller and greater envelope counts.
- Focused canonical policy/catalog/envelope tests: **45 passed** using
  `python -B -m pytest tools/automation/test_m6_authoritative_evidence.py
  tools/automation/test_m6_direct_evidence.py tools/automation/test_m6_exit.py -q`.
- Real provider browser comparison **Passed at 13:42:32 UTC** against running
  revision `22d572c102f9684f38feaa1af4d99d7008c5d405`, for **one target** and a
  genuine source observation at **13:41:05 UTC**. Before/after principal, values
  and source lineage agreed. This is a candidate observer checking the existing
  deployed revision, not a claim that this new observer was deployed.
- Earlier real executions truthfully reported a revision mismatch, temporarily
  unavailable connection and changing request-as-of metadata. They were not
  presented as passing comparisons. The as-of issue was corrected by fencing
  actual observation rows instead of request timestamps.

## Handoff and remaining work

Changed files are the pure browser comparison policy/test, official Usage
browser producer, closed Python evidence parser/test, canonical direct evidence
selection/classifier/consumer, and regenerated exit-catalog hashes. Root owns
integration, deployment and the full combined gate. Further account scopes must
have genuine official views and owner pairing; this one comparison cannot be
counted as multiple accounts or proof of shared pool identity. Natural recovery,
local-host, alert and other M6 acceptance requirements are unchanged.
