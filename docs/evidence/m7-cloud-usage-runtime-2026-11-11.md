# M7 existing-cloud usage collection and account read

Status: implementation increment under focused plan 1.1.0. M7 remains open.
Owners: M04 collection, M05 financial reads, A03 source, P01/P02 presentation;
root integrates contracts, composition, generated artifacts and installation.
Requirements: FR-BUDGET-001/002/003/004/005/006; T004/T005/T007/T009/T010/T011,
M7-A02/A05/A07/A09 and M7-MATH-10/11/12/15. These tickets are not closed here.

## Change and compatibility

The existing supervised billing worker can admit one Ollama self usage report
through the same persistent request gate used by balance polling. Seven/thirty
day intents retain their exact completed UTC interval. Dispatch and atomic
report commit recheck the real cloud graph, current binding, service authority,
usage fingerprint, collection ownership and request reservation. Recovery uses
the existing run/receipt mechanisms. No new account, queue or migration is added.

CTR-COL-002 2.2.0 cloud context/admission now reaches repository/executor/runtime;
explicit inherited contract identity metadata fixes its import declaration.
CTR-CAP-006 2.4.0 adds active-binding current selection and a separate cloud
resource result. Existing billing-resource and funds fields stay compatible.
Unresolved current reports require the current binding; history is preserved.
The account query rereads graph/binding after assembling the result. Collection
status matches the selected self/range/interval, not another report's run.

The API/client safely project cloud resources without exposing binding IDs or
fabricating billing enrollments. Account UI uses shared report rendering and
exact daily usage quantities. Missing monetary costs remain unavailable with
the specific cost-not-reported explanation. Funds retain their own timestamps.

## Evidence observed

- Pre-integration supervised worker Red: `supervised_cloud_usage_report_missing`.
  After wiring, `test_usage_billing_worker_live.py` passed against actual owner-
  enabled cloud metadata and runtime-only protected credentials. One real
  report was committed at 22:11 UTC on 11 November. It contains seven daily
  usage buckets, no cost buckets and no currency. This proves usage, not spend.
- New run/result/manifest/dispatch/current-selection/empty-storage scoped run:
  112 passed, zero skips. Normalizer had missing-module Red and an additional
  rejected-partial-report Red; its completed scoped suite passed 53 checks.
- Actual private SQLite snapshot with genuine graph passed shared-gate schedule,
  admission, restored authority and running-state checks; no provider request.
- Current account read Red: unexpected `cloud_target` argument. Green: genuine
  stored report returned without billing enrollment; 34 scoped tests passed,
  including mismatched interval and captured-binding checks. Initial test-harness
  path/signature mistakes were corrected before that meaningful Red.
- Pure wire projection Red: cloud result omitted (zero rather than one). Green:
  one safe cloud resource, no credential binding identifier or fake connection.
- Counts-only calculation reason Red: `currency_unavailable` rather than
  `cost_not_reported`; Green: three account-spend policy cases passed.
- Read-only review found proven pre-send authorization failures were treated as
  uncertain dispatch. The correction uses existing no-response terminal/run
  finalization. Eighteen pure cases and two actual adapter/private-SQLite checks
  passed: actionable failure, released reservation and no invented response time.
  Requests that may have reached the provider retain conservative uncertainty.
- Installed browser Red at `14dee16`: `cloud_usage_projection_missing`,
  authenticated, zero mutation requests. Built-browser Green is still required.
- The existing M7 pure runner passed 447 checks before adding the final eighteen
  dispatch cases. This is pure policy evidence, not full milestone acceptance.

Canonical scoped commands use the admitted interpreter and
`PYTHONPATH=backend/src:.`, pytest `-c backend/pyproject.toml -q --tb=short
-p tools.automation.pytest_no_skip`. Real suites are
`backend/tests/live/ollama/test_usage_billing_worker_live.py` (one actual request),
`backend/tests/live/ollama/test_usage_current_query_live.py` (read-only), and
`backend/tests/integration/collection_control/test_cloud_usage_rate_gate.py` /
`test_ollama_usage_no_response.py` (private actual-metadata copies).
The installed read-only browser command is
`node frontend/tests/browser/m7/verify_usage.mjs`.

## Impact and outstanding work

No dependencies/license changes, migration, default-provider-profile mutation,
owner account configuration or agent interruption. Runtime alone reads the
already approved protected credential file; no secrets in evidence or output.
The live report is retained in the actual database, not replayed as a fixture.

Full quality/build, installed browser Green and continuity must be recorded
after execution. First monetary demonstration, team-selection UI, all other
provider lanes/categories, full scheduling/fairness/recovery, Overview/totals,
history/analysis and fixed M7 exit remain outstanding. Successful counts-only
collection does not replace any monetary acceptance requirement.

## Pre-install verification

Full local quality passed at 22:21 UTC: 733 formatted files, strict typing across
672 source files, zero import-boundary violations, compatible 85-operation
OpenAPI/client, frontend types, locked dependency checks and production build.
The expanded M7 pure lane passed 465 tests, zero skips. Documentation (380 files),
planning, M7 ticket traceability and local Git preflight passed.

Actual HTTP regression found unconfigured non-Ollama accounts were queried for
credential metadata before enrollment. Composition now returns no active billing
binding when no applicable connection exists; the real HTTP tests pass. A later
combined run passed ten HTTP/current-query/shared-gate cases but could not obtain
a naturally due slot for the no-response snapshot repeat. Read-only live state
showed a global cooldown until 22:22:35 UTC; no reservation or due time was reset.
The earlier successful actual finalization evidence remains separately recorded.

The repeated private-snapshot test now waits for the copied real cooldown to
expire naturally (maximum 130 seconds), refusing active/long-held requests.
At 22:24 UTC its two real adapter/SQLite tests passed in 70.66 seconds. No
timestamps, reservation states or provider responses were altered to obtain it.
The staged secret scan found only old/new generated `openapiArtifactSha256`
declarations. Both are verified generated hashes, not credentials; no scanner
rule or ignore list was changed. Installed verification still follows the commit.
