# M7 first source-entry history chart

Status: first increment installed and published at `c59d068`; the small series-label
correction below is a checked successor awaiting installation. T013 remains in progress. Requirements
FR-BUDGET-003/004, FR-HIST-001; acceptance AC-HIST-001, AC-UI-003/004/006,
M7-A06/A07. M05 owns semantics, P01 serialization and P02 presentation.

## Delivered candidate boundary

CTR-CAP-006 2.10.0 adds optional chart metadata to existing immutable history
rows. M05 computes per-series magnitudes using exact scaled integers across the
entire pinned report before pagination. Series separate cost/usage, native units
and dimensions. Signs, zeros, original facts and source precision are preserved.
Non-daily entries remain table-only with an explicit reason. No aggregation,
inferred gaps, daily totals, exchange rates or token pricing are introduced.

P01 publishes compatible optional fields on the existing history endpoint;
generated OpenAPI/client remain at 101 operations. P02 renders a compact signed
bar plot above the same loaded exact table. Series selection, keyboard selection,
exact accessible labels, partial-page information and retained error states use
the same history data. Loading another page does not rescale earlier entries.
No dependency, migration, storage, provider request, account setup or secret
handling changes. Existing provider profiles and user agents remain untouched.

## Red/Green and review

- Four pure chart cases failed for missing chart metadata before implementation;
  a prior invalid overlapping pure input was corrected before counting that Red.
  Cases cover full-report scale across pages, signed facts, exact extreme/tiny/
  zero values, separated dimensions and table-only non-daily intervals.
- Actual private genuine-report built-browser Red failed at
  `history_chart_missing` before P02 implementation.
- Focused final backend/history run: 44 passed in 39.25 seconds, including real
  retained-report authenticated HTTP assertions. An earlier command named a
  nonexistent test file and ran no tests; it is not evidence of a product failure.
- Canonical `--lane browser --check source_history`: four passed in 48.30 seconds
  after strengthening the probe to verify actual rendered bar geometry as well
  as API/DOM facts, series, keyboard selection, reload and narrow layout.
- Final probe/runner revision: four passed in 48.35 seconds, including the
  unchanged private boundary after adding explicit installed-revision mode.
- Canonical `--lane pure`: 755 backend cases passed in 19.84 seconds and twelve
  presentation suites passed. This is domain/presentation policy evidence.
- Independent read-only M05 review found no actionable arithmetic, source-fact,
  paging or contract defect. P02 review identified the missing geometry assertion;
  that assertion was added and passed against genuine data.
- `AUTO-QUALITY` passed at 09:03:04 UTC: 805 formatted files, 744 typed sources,
  zero boundary violations, compatible generated API, TypeScript and build.
  Its preceding run found one overlong result-description line; corrected.
- Installed read-only probe at predecessor `d73c171` reached the genuine selected
  report and failed `history_chart_missing`. Its first diagnostic invocation
  omitted required Overview period fields (422); corrected before this Red.
- Documentation (398 Markdown files), synchronized planning, M7 ticket tracing
  and Git preflight passed. Staged secret scanning reported only two generated
  OpenAPI artifact hashes, independently matched to actual old/new bytes;
  zero unresolved findings.

The same `history_chart.mjs` probe accepts either an isolated origin plus genuine
selection on stdin, or fixed installed origin plus an exact expected revision.
Installed mode discovers its actual report through authenticated API reads.
It performs no configuration/collection mutations and logs no financial values.
The canonical source-history runner covers isolated discovery and this chart;
its passing scope does not include complete detail/history or M7 acceptance.

## Files and remaining work

Backend: budget query contract, history policy and new chart policy, API budget
schema/router, pure chart tests and genuine HTTP/browser tests. Frontend: generated
client, BudgetDailyHistory, new BudgetHistoryChart component/style and chart probe;
the existing Overview probe compares original source facts independently of
additive chart fields. Automation: existing M7 pure/browser selection only.
Module handoff and contract register record the additive version.

Genuine live coverage here is retained Ollama usage, not a monetary provider
comparison or observed negative monetary bar. Pure signed/precision cases are
not claimed as live financial evidence. T013 still needs proven-disjoint daily
aggregation/rate, supported breakdowns, separate balance history, conditional
forecast and retention. Current broad installed concurrent continuity remains
unresolved independently of this chart. M7 remains open.

## Installed result and visual follow-up

Implementation `c59d0686aec0f2e7940d6ee860955dc57bea4319` passed the selected
same-schema updater. The installed read-only chart probe passed all fourteen
genuine entries at that exact revision. Service active and landing HTTP 200;
GitHub main independently matched the full implementation revision.

Actual current report inspection at 09:09 UTC found seven USD cost entries and
seven usage entries, complete coverage for 5–12 November, category
`self_requests_and_cost`, basis `provider_reported_usage_usd`. The report was
stored at 09:07:15 UTC. Thus current Ollama evidence is no longer counts-only;
it supports a genuine monetary history path. This is not yet comparison with
Ollama's own displayed cost or the required Anthropic/OpenAI source success.
Do not retain the prior absence-of-money assumption as a prerequisite.

Visual inspection of the actual chart found the short Series label wrapping
mid-word. The installed probe reproduced `history_chart_series_label`; a minimal
nowrap style fixes it. The strengthened canonical browser selection then passed
four tests in 45.52 seconds, including narrow layout. No financial behavior changed.

The broader Overview probe remains blocked at Back navigation. Added safe
diagnostics now identify `/api/v1/budgets`, `unavailable`,
`budget_overview_registry_changed`, with zero mutations. Source inspection and
independent M04 review identify conflated financial cutoff and current registry
metadata time in pool reads. A versioned, tested correction must preserve
revision/scope/binding/open-membership checks and command-time guards; do not
remove safety checks or call this broad continuity passed. The exact original
report context remains valid for the successful chart check.
