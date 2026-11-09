# M6 provider-display compatibility correction

Status: Approved by the owner on 9 November 2026 ("approve" in response to this
bounded correction); implementation and live verification in progress.
Owner: A01 for Claude; integration for official Ollama comparison.
Requirements: FR-COL-004/006/007/008, NFR-COMP-001, M6-A04/A07/A09,
AC-LIVE-004/007. Local Ollama remains deferred.

## Observed failures

On 9 November the owner authorized the existing managed Claude profile.
Its read-only identity matches the registered account. The scheduled reads at
10:19:38 and 10:24:44 UTC failed with `usage_deadline_window_set_invalid`.
Bounded in-memory diagnostics of the real admitted CLI found the all-models
weekly card and one model-specific weekly card, each with percentage/reset
fields, but no `Current session` label anywhere in the collected output.
Only allowlisted label presence/counts were retained; no raw output, credential,
conversation or profile contents were saved. These observations diagnose the
failure; they do not constitute a passing collection or completed TDD cycle.

Ollama moved balance cards to `/dashboard`. The EAIS USD comparison passed
with that route accepted. The SDK page exposes session/weekly percentages and
`#extra-usage-balance`, but its reset paragraphs contain only relative text:
no exact `data-time`, datetime, title or accessibility timestamp was observed.
The existing verifier therefore cannot claim exact reset equality.

## Approved bounded behavior

1. Claude: preserve a validated reported all-models weekly percentage when the
   complete bounded usage surface omits the session card. Represent the session
   percentage and reset as **unknown**, never zero, 100%, or a retained old
   value. Emit an explicit partial-result omission. A present but malformed,
   duplicate or incomplete session card still fails closed. Missing weekly
   data, ambiguous model cards and truncated surfaces still fail closed.
   Do not merely relax the parsed window count: absence fallback is considered
   only at the existing bounded capture deadline, after at least one second
   without new output, with a fresh post-command usage completion marker and a
   complete valid weekly surface. The entire bounded capture must contain no
   session label, so a label lost from the 40-row screen cannot qualify. Reject
   authentication/errors, unsupported controls and an observed session label
   with missing values. Validate these discriminants against real native output
   before admitting the fallback; an unproven render remains a failed read.
2. Ollama comparison: support both official routes and the new scoped quota
   element IDs. Compare session/weekly percentages at displayed precision and
   the purchased-credit balance. Compare exact reset values when actually
   supplied; otherwise explicitly record reset comparison as unavailable.
   Never derive exact times or a rounding tolerance from relative text.
3. Re-run the installed dashboard and bounded M6 recovery scenario using real
   newly committed Claude/Codex readings. Preserve the requirement for actual
   cross-provider collection during the recovery interval. Missing evidence
   remains Not Run/Failed; this plan does not accept or close M6.

## Authority and contract impact

The approved [Claude admission plan](claude-managed-account-connection-change.md)
requires both session and weekly windows with reported percentages. This
explicitly approved amendment allows the unknown session value only under the
bounded missing-card conditions above. Historical acceptance is unchanged.

`CLAUDE-SUBSCRIPTION-QUOTA-V1@1.0` already permits an unknown percentage and
reset while retaining both window identities. Preserve its wire schema and
M03/M05/public API shapes. Increment the A01 adapter/parser patch version and
publish a separate hash-bound admission mapping; retain historical M3/M4
receipts unchanged. Verify that unknown session observations replace stale
session values without manufacturing capacity.

Keep the two structural window identities and the existing payload's
`completeness=complete`; the collection outcome is `partial`. Map the new
session omission to availability `unknown`. The existing unsupported
model-specific omission retains availability `unsupported` rather than applying
the current blanket unsupported mapping to both cases.

Version the internal official-comparison evidence envelope so each accepted
comparison declares balance coverage and unavailable reset comparison. Update
its strict consumer, catalog hashes and evidence together. An older receipt
must not silently acquire the new coverage semantics. No account, organization,
key, default provider profile or running user agent is changed.

## Implementation boundaries and verification

- A01: Claude subscription source/mapper, omission mapping, manifest/admission,
  their focused tests and adapter documentation. Review M03/M05 consumers using
  existing versioned contracts before integration; no cross-module shortcut.
- Integration: `frontend/tests/browser/m6/compare_official_ollama_usage.mjs`,
  its pure comparison policy/tests, the internal authoritative evidence
  producer/consumer tests and canonical M6 catalog/selector metadata.
- First retain a failing real managed-quota test and pure rejection/availability
  tests, then implement. Cover missing versus malformed session fields,
  missing weekly fields, conflicting/duplicate windows, genuine partial
  persistence and UI freshness. Preserve known full-window cases.
- For Ollama, retain the current real DOM failure and pure tests covering exact
  versus absent reset metadata, percentage/USD mismatches and truthful coverage.
- Run focused checks, documentation/planning validation, source/security,
  quality/build, installed browser verification and `AUTO-M6-EXIT` on the clean
  deployed revision. Report each unexecuted live condition separately.

No new dependency, database migration, secret-storage change or license change
is planned. Deployment uses the existing canonical current-update command;
rollback selects the preceding sealed release. Owner account configuration
remains owner-operated. Owner authentication may be needed only if an official
session has genuinely expired; the confirmed Claude authorization is retained.
