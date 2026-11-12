# M7 full-inventory financial Overview sorting

Status: candidate implementation; installed verification and publication are
not yet claimed. Requirements FR-ORG-003, FR-BUDGET-002/005, AC-UI-002..006;
T010/T012, M7-A07/A08. M05 owns financial ordering, P01 transport and P02 controls;
root owns shared contracts, generated client and composition.

## Behavior and contract impact

CTR-CAP-006 Overview types advance2.6.0→2.7.0 with optional query fields:
`sort_by` account/organization/state and `sort_direction` ascending/descending.
Defaults state/ascending preserve the priority-first view. Canonical pool name
and primary organization label determine ordering; account access-path names
cannot substitute for the displayed pool. Stable ties remain ascending when the
selected primary direction reverses. Sort runs across the full filtered result
before pagination; summaries retain full-inventory coverage.

The current M02 OrganizationViewV1 query supplies names at the same registry
revision, rechecked before returning. Renames or other snapshot changes expire
cursors. API cursors bind sort field/direction; omitted defaults and explicit
defaults have the same meaning. No money arithmetic, organization sorting or
fetch-all workaround moves into React.

Existing CTR-FND-005 generation compared entire old operations literally and
rejected optional query additions. Generator2.0.10 now permits only additive
optional query parameters while retaining all old operation fields/parameters.
Required additions, non-query additions, duplicate parameters, removals and
changed parameter definitions remain breaking. No new generator or dependency.

## Red and Green evidence

- Nine pure sorting tests first failed: `BudgetOverviewQueryV1.__init__() got
  an unexpected keyword argument 'sort_by'` / `sort_direction`. After the
  implementation, ordering/cursor tests pass; invalid literals use the existing
  technical-value validation code `unsupported-field-state`.
- Actual isolated IAM/SQLite/HTTP test first returned400 for valid sorting,
  `overview_sort_http_unavailable`. After API integration all four Overview
  HTTP tests pass, including both directions, before-pagination winners,
  organization name versus opaque-ID order, default compatibility and cursors.
  Comparing whole minted cursor strings was corrected to compare semantics
  and verify cursor acceptance; their expiry timestamps can differ.
- Pure OpenAPI compatibility test failed `breaking` versus `compatible` for
  optional query addition. Its initial invalid test title was a setup error,
  not Red evidence. Six new compatibility cases plus existing breaking-diff
  regression pass. Actual production generation reports compatible91 operations.
- Built isolated browser first failed `overview_sort_first_page` after the
  sorted API source assertion passed: old UI omitted selected order parameters.
  The browser uses actual admin-created metadata beyond one page; no provider
  telemetry is inserted or replayed. The first Green attempt reached pagination and exposed a test-only issue:
  separately minted cursor tokens have different expiry times. The probe now
  follows the cursor from the actual rendered HTTP response and compares row
  identity/order against the independent API reading. Final Green follows below.
- Combined scoped pure/metadata checks:54 passed, covering pool selection,
  exact ordering/cursors, contract compatibility and real empty-query storage.

No migration, new dependency/license, credential custody, provider profile or
owner configuration changes. Browser metadata mutations are isolated test
storage. Natural provider/money evidence remains unchanged and M7 stays open.
No claimed sort result proves successful billing access, genuine monetary
aggregation, bounded financial history, complete provider coverage or M7 exit.

The preceding documentation-only refactor is committed separately as `3c7343f`.
Current read-only installed inventory still reports zero billing connections;
no repeated setup request was issued and no accounts were configured by agents.

## Candidate integration checks

Canonical `python -m tools.automation.implementations.auto_m7 --lane browser
--check owner_pool_controls` passed after the UI correction: production build,
all six sort choices, more than50 real isolated metadata rows, both pages,
return-to-old-sort reset, reload/detail/Back and existing pool-control cases.
No live owner metadata was changed. The installed read-only probe now compares
actual API/DOM ordering; it will run after activation.

AUTO-QUALITY passed at01:11UTC on12 November: Ruff762 files, strict mypy701,
zero boundary violations, compatible91-operation generated API/client,
TypeScript and production build. Its first run found test-helper typing errors;
the helper now uses explicit typed keyword options and deliberate invalid-input
casts only inside pure validation tests. No production behavior changed for it.

Canonical pure lane passed598 Python cases and seven presentation suites.
Canonical `--lane technical --check budget_http_guards` passed13 actual
IAM/current-read/Check/status/monitoring HTTP cases. Scope remains no-report
metadata/guards; neither count asserts genuine monetary persistence.
