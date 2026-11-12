# M7 retained report discovery

Status: implementation in progress under approved focused plan 1.1.0; not yet
installed or published. T010/T011, FR-BUDGET-006, FR-HIST-001, M7-A06/A07.
M05 owns retained report semantics; P01 the HTTP boundary; P02 presentation.
This increment does not close the full tickets or milestone.

## Contract and behavior

CTR-CAP-006 2.9.0 adds optional `as_of` to the existing bounded report-history
query and publishes `BudgetReportHistoryPortV1`. Legacy repository callers keep
their existing behavior. The application authorizes the account before and after
the query. SQLite filters stored time at the selected snapshot and retains original
scope generations and report identity. Its compact snapshot cursor fits the
existing authenticated HTTP cursor envelope; legacy internal cursors remain
compatible. P01's new `capacity_list_budget_reports_v1` operation returns only
existing allowlisted summaries through GET `/api/v1/budgets/{budget_id}/reports`.
It does not return report bodies or credential binding fields, collect data,
change scope, or establish current access authority.

P02's Source history is being integrated into existing account detail. Original
scope metadata and immutable report links use existing financial URL selection,
daily history and Back/reload behavior. A historical report cannot authorize
collection with the current credentials. No new schema, dependency, provider
endpoint, license permission or owner configuration is required.

## Red and Green evidence

- Actual isolated IAM/HTTP Red: new route returned 404 instead of required 401,
  assertion `budget_report_discovery_route_missing`.
- First genuine retained-data HTTP attempt exposed an integration mismatch:
  the existing repository cursor did not fit P01's bounded keyset envelope.
  The pinned query now uses a compact context-bound continuation, leaving legacy
  repository calls unchanged. No widening of the public cursor policy.
- Genuine stored Ollama history then failed
  `report_discovery_leaked_future_snapshot`: reports newer than selected `as_of`
  were returned. Adding the actual stored-time predicate made the check pass.
- Focused backend run: 15 passed, covering real IAM guards, genuine retained
  report metadata, original scopes, two HTTP pages, caller/filter cursor mismatch,
  snapshot exclusion, legacy cursor behavior and real empty storage. Later
  permission/compact-cursor tests and final verification are recorded below.
- Independent read-only backend review found no material authorization, temporal,
  pagination, privacy or module-boundary regression.
- Built-browser Red reached authenticated genuine private report metadata, then
  failed `source_history_disclosure_missing` (normal exit1, one failed test).
  Browser Green remains pending at this checkpoint.
- Partial-selector Red: `source_history` rejected with `m7_selection_invalid`.
  It is being wired into the existing M7 runner; its pass will not certify full
  monetary detail/history, charts, forecasts or M7 acceptance.

Broader API policy verification found a stale test catalog at 91 operations.
The explicit operation/schema inventory now includes the nine omitted shipped/new
operations, including this discovery route; the current generated API has 100.
Twenty checks passed and two failed on the stale fixed count/request catalog;
after correction those two checks passed (23.57 seconds). No API protection was
relaxed to make the tests pass. Generated contract/client compatibility passed.

## Limits and next work

Genuine Ollama counts prove the shared retained-history path, not a monetary
provider comparison or an actual previous-scope epoch unless one is present.
No provider response was fabricated, replayed or edited. Tests use private copies
of genuine stored data, actual application ports, real SQLite/IAM/HTTP and the
built browser; owner configuration and the installed service remain untouched.
Full M7 still needs the fixed remaining provider, monetary, lifecycle, analysis
and release acceptance. See the delivery worksheet for the complete sequence.

## Verification correction during integration

An unintentionally broad root test invoked temporary-tool routines concurrently
with the browser Red run. Its first collection-guard run failed because the
other context removed shared temporary tool links. A subsequent serial pass in
the same process passed all 72 collection guards and 23 budget HTTP guards.
That process also passed 738 backend pure tests, 59 registry metadata tests and
the critical mutation test, but encountered the P02 guard's deliberately failing
Red while UI implementation was in progress. These mixed working-copy results
are diagnostic only. Final serial verification below supersedes them; no full
technical acceptance is claimed. Root stopped starting shared-context commands
until the active process was terminal and returned exclusive build ownership.
The installed dashboard remained HTTP 200 throughout these isolated checks.

## Integrated verification before installation

- P02 pure Red required the missing current-authority guard for selected cloud
  history; Green covers current versus retained/unconfirmed reports. Discovery
  metadata alone cannot authorize collection. Selected facts now display the
  original scope generation, and links retain exact period/read timestamp.
- First browser Green attempt failed at coarse `source_history_selection`.
  Splitting probe stages improved safe diagnostics; unchanged production then
  passed (12.63 seconds). No root cause was established for that earlier probe
  failure; it is not erased by the later pass.
- Canonical `--lane browser --check source_history` passed all three actual
  HTTP/genuine-data/built-browser tests (28.04 seconds). Root strengthened its
  selection to the second genuine retained report instead of only the latest;
  the subsequent result is recorded below.
- `AUTO-QUALITY` passed at 06:49:47 UTC: 798 formatted files, 737 mypy sources,
  zero import-boundary violations, compatible generated 100-operation API,
  TypeScript and production build. No dependency change.
- Final `--lane pure`: 738 backend tests and twelve presentation suites passed;
  this includes the now-Green cloud-history guard. Pure constructed inputs do
  not substitute for genuine HTTP/browser verification.
- Exact old installed revision `71185cf` failed the expanded read-only Overview
  probe at 06:51:04 UTC with `source_history_disclosure_missing`. Authentication,
  Overview/filter reads and zero mutations passed. This is the pre-install Red
  for the installed UI, not an outage; current service remained HTTP 200.
- Both independent backend and UI reviews reported no material blocking finding.
  Planning/doc checks passed. The overall M7 gate remains incomplete.
- Strengthened canonical source-history rerun passed all three tests in 22.47
  seconds after the production rebuild at 06:52:45 UTC. It selects the second
  genuine retained report, verifies exact facts and scope labels after reload/
  Back/Forward, and tests page-scoped offline retention without owner mutations.
