# M7 financial Overview and retained report selection

Status: implementation increment; full M7 remains open. Approved scope is
focused plan 1.1.0 / M05 increment 0.3.0. Root integrates M02/M04 public reads,
M05 semantics, P01 transport and P02 presentation. No owner configuration is
performed by this increment.

## Requirement and contract coverage

T004/T010/T011/T012/T014; FR-BUDGET-001/002/005/006, FR-ORG-003,
AC-UI-002..006, AC-TEST-001/003/006. Additive CTR-CAP-006 2.5.0 publishes compact
financial rows and explicit retained-report reads. Existing CTR-REG-005 resource
and M04 run contracts supply metadata/lineage; their semantics do not change.
The generated compatible API now contains 87 operations, including
`capacity_list_budget_overview_v1` and `capacity_get_budget_v1`.

Overview shares organization/provider/resource filters with quotas, retains
safe URL state, includes funds/counts-only resources and pending API accounts,
and excludes actual cloud-only resources from subscription membership. M05
calculates percentages and state; React formats exact money and preserves the
backend low flag. No client totals or token-price inference.

An account link retains the resource, immutable report, exact interval and
read instant. The authenticated selected-report route rejects another account,
resource, period or report stored later than that instant. Missing/expired
selection never silently becomes latest. Sanitization preserves a safe invalid
marker for malformed/duplicate selectors through reload and sign-in return.
Collection status remains separate from the pinned historical report.

Existing funds now require the current binding generation and the genuine
committed M04 run's account/resource/source/observation membership, with a
before/after metadata check. No provider key is inspected by these queries.

## Red/Green and review

- Installed browser Red: `financial_overview_missing`, authenticated and zero
  mutation requests.
- Overview HTTP Red: missing route returned 404 instead of authenticated
  route's 401. Selected-report HTTP Red: generic `resource_not_found` instead
  of the explicit report-selection outcome.
- Pure selection Red: `immutable_budget_report_selection_missing`; frontend
  Red: `pinned financial selection missing` and
  `financial_overview_replacement_policy_missing`.
- Real private snapshot exposed false registry-change rejection: a billing
  connection retains a historical revision and cloud resources use a separate
  public graph. Fixed those distinctions, retaining actual inventory rereads.
- Pure subscription classification Red preceded exclusion of actual cloud-only
  resources; the genuine snapshot now asserts that exclusion explicitly.
- Independent review caught malformed-selector normalization and hidden
  collection failures. Corrected both without changing report history.
- Funds lineage: meaningful live Red `unproven_lineage_must_not_be_current`;
  genuine current funds, pure mismatch policy and empty SQLite checks passed.
- Real HTTP guard selection passed ten checks, including IAM permissions,
  bounded filters, pagination and signed-cursor context isolation. Schema
  errors use existing 422 semantics; semantic invalid filters use 400.
- Full local quality passed: 747 formatted files, strict typing across 686
  source files, zero boundary violations, compatible API generation, frontend
  types, locked dependency metadata and production build.

The existing M7 pure command includes the new financial policies and five
actual pure presentation scripts. Browser verification remains a separate
real-service boundary, using `frontend/tests/browser/m7/verify_overview.mjs`.
Final command outcomes and installed revision are recorded after execution.

Pre-install results: the canonical pure lane passed 489 Python checks plus all
five presentation scripts; the HTTP guard lane passed ten checks; five genuine
stored-data/empty SQLite checks passed. Documentation (381 Markdown files),
planning, ticket traceability, local Git preflight and diff checks passed.
The staged secret scan flagged one generated `openapiArtifactSha256` declaration;
inspection matched the 87-operation generated artifact hash, not a credential.
No scanner suppression or ignore rule was added. Installation/browser results
remain separate until the committed candidate runs.

## Scope, files and limits

Changed contracts/composition/funds lineage, M05 Overview and selected-report
queries/policies, P01 schemas/routes/problem/client generator, P02 Overview and
account/router/query-state rendering, focused tests, existing M7 runner target
lists and the synchronized planning documents. New substantive sources are
`capacity/{application,domain}/budget_overview.py`,
`capacity/application/budget_selected.py`, P01 `budget_overview.py` schema/route,
and P02 `features/overview/BudgetOverview.tsx` plus its selection helpers.

No dependency/license change, migration, default profile access, provider
request, agent interruption, key entry, account/group configuration or secret
export is required by this read-only feature. Schema remains `v1_0733`.

Canonical pool/primary-group attribution is still T002 work. Overview explicitly
excludes unresolved pools; empty summaries are not completion of FR-ORG-003.
The genuine usage currently demonstrated contains counts, not monetary costs.
First monetary reporting, other provider/category coverage, complete history
pagination/analysis, scheduling/recovery and final M7 exit remain outstanding.
No implementation ticket is closed solely by this increment.
