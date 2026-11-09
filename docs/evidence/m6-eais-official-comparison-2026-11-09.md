# EAIS official Ollama comparison — 9 November 2026

Status: one-account live comparison passed; full M6 completion is not claimed.
Requirements: M6-A04/A09, AC-LIVE-005. Owning scope: integration verification.
No production API, database, provider contract or dependency change.

The owner signed into the second organization's official Ollama page. Ollama's
`/settings` now shows usage costs; its balance cards moved to `/dashboard`.
The original verifier returned `not_run/official_usage_pairing_unproven` against
the real open pages. The verifier now admits both exact official paths while
retaining identity, current-source lineage, amount and reset comparisons.
It performs no provider navigation or configuration writes.

With the actual EAIS credit card and authenticated installed dashboard, the
updated verifier returned `passed/official_usage_compared`, one target, at
2026-11-09T09:14:20.004Z. The source observation was
2026-11-09T09:09:14.801085Z. Monthly remaining, monthly allowance, separately
purchased credits and refill calendar date matched. The installed product was
`a6b1904394285949c1e91dd0ec6ff017baec120d`; the verifier path correction was
uncommitted during this component check. This is not a clean-revision full-gate
receipt. Syntax check and 23 pure comparison/stability tests passed, zero skips.

The owner subsequently authorized Claude and its managed identity was verified.
Fresh quota reads still fail with `usage_deadline_window_set_invalid`: the
observed usage surface omits the previously required current-session window.
Claude quota continuity, a fresh complete canonical M6 result and owner
acceptance remain outstanding. The percentage-plan cards on
Ollama's new Dashboard no longer expose the previous exact reset metadata in
the inspected DOM; their updated comparison remains unverified. The historical
SDK comparison is not presented as current-revision evidence for the new page.

The original shared browser later closed. A new headed shared browser was
opened and its dashboard authentication returned HTTP 200. The SDK official
Dashboard is open with the correct visible principal. Its current quota IDs
expose both percentages and purchased credits, but only relative reset text.
The former EAIS incognito page was not preserved; the earlier passing
component observation remains historical evidence, not a currently open tab.

## SDK Dashboard comparison correction

Under the approved M6 native-balance comparison scope, the verifier now reads
the real Dashboard's scoped session/weekly quota IDs and purchased balance.
The exact-metadata comparison remains unchanged for pages that provide it.
The new balance-only view explicitly carries `resetComparison=unavailable`;
it compares both percentages and purchased USD and never derives a timestamp
from the provider's relative display.

Internal comparison evidence is version `1.1.0`, with an explicit count of
targets whose resets could not be compared and a distinct successful reason
`official_usage_balances_compared_reset_unavailable`. Its strict consumer
rejects inconsistent counts/reasons and old envelopes. M6-A04 source-version
hashes and the exit catalog now bind that version, and the gate propagates
`official_reset_comparison_unavailable` into its declared limitations.
No product API/schema, production collection, accounts, credentials or database
changed. The separate proposed Claude behavior remains unimplemented.

Red: the real new Dashboard returned `official_usage_credit_view_unavailable`.
Three new pure JavaScript cases failed before the balance-only API existed;
the new Python coverage envelope was rejected. A subsequent pure gate test
failed because the limitation was not propagated. After correction, 26
JavaScript tests passed with zero skips. Focused evidence/catalog checks are
recorded in the implementation handoff below.

Live SDK comparison passed at `2026-11-09T10:36:04.616Z`, against source
observation `2026-11-09T10:34:30.268521Z`, one compared target and one target
with unavailable reset comparison. The current-lineage digest was
`7aeb64de5a5f30c372d7d81898ed615f0b1c0cf78f01a08886fd519559c62e1b`;
comparison digest was
`61a65875e17da2c2a4fe449adf912baa4a180bf3105b48f7d6eb65c500f043b3`.
The installed product was still `a6b1904394285949c1e91dd0ec6ff017baec120d`
and verifier changes were uncommitted during this component check.

The installed built-browser checks also passed account administration, both
current cloud balance lineages, both history lineages and dashboard availability.
Local model checks correctly remain Not Run because the owner deferred them.
The historical EAIS and current SDK component checks are not combined into a
single current two-account gate result. Full M6 recovery/acceptance remains
open, especially the newly observed Claude source compatibility issue.

## Verification handoff

- JavaScript comparison/stability: 26 passed, zero skips.
- Python authoritative envelope/direct evidence/exit catalog: 90 passed, zero skips.
- `AUTO-QUALITY`: passed, including static boundaries, generated API checks,
  frontend type checks and the production frontend build.
- `AUTO-DOCS-CHECK` and `AUTO-PLAN-CHECK`: passed. These do not approve the
  [proposed Claude change](../plans/integration/m6-provider-display-compatibility-2026-11-09.md).
- Independent read-only review found no blocking comparison defect; its
  catalog-binding and visible-limitation findings were addressed and tested.
- Files: official comparison producer, pure policy/test, strict evidence
  consumer/test, direct gate classifier/test, exit catalog and these docs.
- Security/privacy: quota/principal-scoped browser reads only; no raw request
  history, credentials or conversations. No migration/dependency/license impact.
- Full `AUTO-M6-EXIT`: not rerun; current Claude quota failure and the missing
  currently signed-in EAIS official tab prevent a complete live result.
