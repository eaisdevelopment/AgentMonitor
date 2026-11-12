# M7 manual Ollama usage collection

Status: local implementation, integration verification in progress. Not installed
or published. T004 pure-domain scope is closed below; no other ticket or
milestone closure. T007/T009/T011, with T004/T010/T012
counts-only state correction; FR-COL-004/008, FR-BUDGET-001/004,
M7-A02/A05/A07/A08/A09. Root integration owns this handoff.

## Contract and behavior

Additive CTR-COL-002 2.5.0 exposes captured cloud usage action, eligibility and
status; CTR-COL-008 1.2.0 retains shared balance/usage admission. Existing
CTR-CAP-006 Overview 2.7.0/history 2.8.0 and CTR-REG-014 1.5.0 are unchanged.
Generated API client 2.0.13 validates 98 operations with compatible changes.
The module handoff defines exact ownership, authority, replay and worker bounds:
[M05 integration plan](../plans/modules/m05-capacity/m7-budget-increment-2026-11-11.md).

The account page offers explicit Collect usage for its selected native interval.
It retains original intent across reload and window changes, separates unknown
outcomes from confirmed rate limits, and reads actual status. It does not change
accounts, credentials or monitoring. Cloud collection requires existing active
monitoring authority. Missing monetary fields alone no longer imply incomplete
coverage. Financial entry places the existing financial section first and
focuses its heading; ordinary account entry retains its existing layout.

## Red/Green and current verification

- Pure action tests failed for missing command/builder behavior, then passed:
  strict versions, original context, retry identity and shared scheduled budget.
- Real empty SQLite and real IAM/HTTP failed for missing action/route; passed
  absent-target, authentication, CSRF, preconditions and closed input checks.
- Atomic M04 claim tests first failed for missing methods. Genuine private
  metadata then exposed a 120-second run versus 60-second lease mismatch;
  bounded lease correction passed queue, replay and busy-rollback assertions.
  No provider request, credential copy or owner-state mutation occurred.
- Pure counts-only tests: four failures before classification correction;
  focused 46-case suite passed afterward.
- Pure P02 intent tests failed before the helper existed, then passed; a later
  rolling-window assertion also failed and passed after preserving unknown
  outcomes while retiring confirmed unadmitted expired intervals.
- Installed financial-entry probe at ef8fa86 failed with
  `financial_entry_focus_missing`; installed Green remains required.
- Generator first failed `operation_policy_mismatch`, then passed 98 operations
  after publishing the three new routes and policies. Boundary check caught
  missing contract ownership; explicit registration resolved all violations.
- AUTO-QUALITY passed at 03:59 UTC: Ruff/format, mypy 727 source files,
  boundaries, generated API, TypeScript and production build. Later corrections
  require the affected checks again before installation.
- Canonical pure lane passed 713 Python cases plus 11 presentation suites.
  Collection guards passed 63 cases; HTTP guards passed 22 cases.
- Installed read-only cloud control probe failed `cloud_collect_control_missing`
  at ef8fa86, with zero POSTs or other mutations. This is the UI Red for the
  new control.
- Genuine builder admission exposed the existing unique target digest shared by
  two different schedules. A distinct manual target digest preserves the original
  source request budget; its pure regression failed then passed. Manual intent
  now uses the existing 120-second admission bound, while provider execution
  remains capped to the 60-second shared rate lease; its assertion also failed
  before correction and passed afterward.
- Independent integration review found normal manual dispatch preceded expired
  cloud recovery. The genuine expiry test failed because the active reservation
  remained set; both paths now recover first. Its next assertion reproduced
  `recovery_consumed_manual_dispatch_owner`: recovery had registered the same
  worker ID needed for claim. Recovery now uses a separate owner. The combined
  actual-metadata/expiry test passed in 161.03 seconds. It verifies exact-key
  replay, changed-context conflict, atomic claim/journal, busy rollback, genuine
  not-started expiry recovery and a dispatch ID still available after recovery.
  One intervening attempt could not obtain two actual self request budgets;
  bounded self/team command enumeration supplied eligible technical intents
  without provider calls, reset budgets or invented telemetry. A prior run was
  interrupted while waiting on copied cooldown and provides no pass evidence.
  Independent review found no remaining must-fix in its bounded integration scope.
- Final static/build check at 04:07 UTC passed, and collection guards passed
  again (63 cases). The later distinct recovery-owner edit passed focused Ruff
  and mypy. Pure mutation policy passed one test with seven subtests. Fifteen
  focused command/empty-store/worker-entry checks passed after the extraction.
- Staged secret scan found only the removed and added generated
  `openapiArtifactSha256` constants; each was independently matched to the
  actual old/new OpenAPI artifact bytes. No credential was identified.


## Limits and follow-up

The local action still needs final integration review, installed browser Green,
actual provider collection and balance-continuity evidence. T007 fair scheduling
and wider provider coverage remain unfinished. Genuine monetary acceptance is
separate. No live success is inferred from pure or empty-storage checks.

No dependency/license, schema/migration or provider-profile changes. Protected
runtime credential handling remains existing behavior; no credential values are
read by coding agents or included here. Source changes are contracts, M04 storage,
composition, P01 routes/schema, P02 generated client/account controls, domain
classification and their tests; planning and runner inventories are synchronized.

## Repeatable verification commands

- `node frontend/tests/browser/m7/verify_cloud_collect.mjs`: installed read-only
  controls, context/eligibility and reload with no provider collection.
- `node frontend/tests/browser/m7/verify_cloud_collect.mjs --collect`: same checks
  plus exactly one explicit official usage request through the real UI, persisted
  status after reload, readable report and retained balance components. It does
  not configure accounts or credentials. Provider cooldown is bounded and cannot
  become an implicit pass. It reports only safe statuses and source revision.
- `node frontend/tests/browser/m7/verify_overview.mjs`: existing real
  Overview/history/navigation comparison, including financial entry and ordinary
  account refresh behavior. No provider requests or owner configuration.

The real metadata queue test lives at
`backend/tests/integration/collection_control/test_ollama_usage_queue_real_metadata.py`.
It is separate from credential-free guards because it requires actual existing
owner metadata and natural expiry; it does not manufacture provider responses.

## T004 pure-domain closure

Independent M05 review confirmed the ticket's exact arithmetic, report selection,
compatible aggregation, shared-pool deduplication and unrounded threshold scope.
Its focused audit passed 179 cases, alongside root's canonical 713-case pure lane,
11 presentation suites and seven killed targeted policy mutants. These mutation
checks are targeted coverage, not an exhaustive mutation score. Earlier Red and
correction evidence remains linked from T004; counts-only classification Red/Green
is recorded above.

One duplicated checklist clause assigned breakdown-plus-remainder reconciliation
to T004 even though calculation rules section 9 and T013/T015 already own it.
The catalog now keeps breakdown exclusion/deduplication in T004 and preserves
reconciliation under T013/T015. No required milestone scope was removed.
T004 is done on its own pure/mutation boundary; forecasts, report persistence,
real monetary/provider comparisons and UI acceptance remain separate unfinished
work. This does not mark M7-A02 or the milestone accepted.
