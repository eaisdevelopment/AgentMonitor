# M7 genuine monetary journey: retained storage to installed screens

Status: Intermediate. This verifies actual money already collected by the
installed application; it does not close M7, full shared-pool aggregation,
fresh commit/retry or provider-display reconciliation.

Requirements: FR-BUDGET-002..005, FR-ORG-003; M7-A02/A06/A07/A08/A10.
Tickets: T003/T005/T010/T011/T012/T014. Owning boundaries: M05 storage,
P01 HTTP, P02 built UI, root executable verification. Existing CTR-CAP-006
2.10.0 and CTR-REG-014 1.9.0 remain unchanged. No schema or application contract
change is introduced by these tests/probes.

## What was established

The earlier history checks could select counts-only reports. Their passing
status was not proof of money. The HTTP suite now has a separate required-money
case selecting a genuine complete ungrouped cost-bearing report. It checks
coefficient/scale/currency, source/category/basis/scope and an independent
scaled-integer sum against the actual HTTP total, then verifies each exact
history page and the compact account summary.

New retained-persistence checks use an unchanged private backup of the real
SQLite database. Normalized signed-cost/usage rows agree with the immutable
report and receipt. Reopened production repositories preserve exact values,
coverage, provenance and run/report/receipt lineage. Repeated production
`get_commit_status` reads neither change facts nor create duplicates. No
invented telemetry or raw provider-response replay is involved.

The existing Overview browser probe gains `--require-money`. It selects a
monetary context explicitly, preserves that candidate through provider/group
filters, opens that exact report, checks scope/basis/period/source identity and
independently sums its actual cost entries using BigInt. Overview, selected
detail and every history row must agree. Balance/counts-only fallback cannot
pass this mode. Existing generic mixed-account checks remain available.

The installed monetary journey passed at **09:46:42 UTC, 12 November**, revision
`e0ecf925dcfec2fd1c305028040cb7ab02b9ec55`: two financial rows checked; money,
filters, pinned navigation/reload, exact history, window controls, responsive
layouts, pool controls and zero mutations verified. This is evidence about the
existing installed behavior, not a new application deployment or provider-page
comparison. No amounts, account labels or credentials enter this record.

## Executable verification

- Initial genuine persistence checks: **2 Passed in 11.73 s**. Existing behavior
  passed on first execution; no product Red is claimed.
- Extended real HTTP/history cases: **2 Passed in 49.89 s**. This adds explicit
  monetary evidence to already implemented reads, not invented product Red.
- New pure result-admission policy initially failed because
  `monetary_probe_result` was absent (`ImportError` during collection). After
  implementation, that policy plus existing Overview selector tests:
  **19 Passed in 0.09 s**. It rejects counts-only/generic success, incomplete
  checks, wrong revisions, mutations and inconsistent process results. This is
  automation-policy Red/Green, not provider TDD.
- `auto_m7 --lane browser --check source_history`: production build and
  **7 Passed in 54.40 s** across real HTTP, retained monetary persistence,
  report discovery and built history/chart. No provider request was made.
- The existing revision-bound `overview` check now also runs retained monetary
  HTTP/persistence and the strict installed money probe. It continues to leave
  full filtered-total acceptance Not Run; the single monetary journey cannot
  close every aggregation boundary.

The expanded canonical Overview selection executed **9 real metadata/monetary
tests Passed in 43.01 s**, concurrent installed Overview/setup/cloud reads
Passed at **09:54:51 UTC**, and strict installed monetary journey Passed. The
command correctly exited **3 / Not Run** for the outstanding broader
`m7_full_filtered_totals_required` result. That nonzero aggregate is retained;
the successful subchecks do not make the whole Overview or M7 pass.

## Concurrent probe failure and diagnostic correction

The baseline concurrent run at **09:43:29 UTC** had Overview and setup Passed,
but cloud controls Failed with `cloud_collect_control_missing`. Keep that
failure: its cause was not established from the old output.

The cloud probe previously collapsed any timeout before its region appeared
into that message. It now observes the page's own matching summary response,
validates account/period/cutoff/resource, waits for the settled financial panel,
then asserts the exact resource control. It retains the ten-second readiness
budget and does not retry. The wrapper forwards bounded allowlisted stage,
HTTP-status and network-error diagnostics, never URLs, IDs or raw payloads.
This improves synchronization and diagnosis; it is not evidence that a product
failure has been fixed. Subsequent actual results are recorded below.

The instrumented concurrent run passed all three children, with the cloud
summary HTTP 200, requested resource present and financial panel settled on
reload. The earlier failure's cause remains unestablished; this result does not
retroactively erase it. Independent review also caught a weakened generic
mixed-account quota-presence assertion in the monetary-mode extension. Root
restored explicit quota-presence checks on reload, ordinary entry and refresh,
allowing absence only when the selected monetary page originally had none.
The generic mixed-account probe after that correction Passed at **09:57:05 UTC**
on the same installed revision; the reviewer confirmed its finding resolved.

Final local quality Passed at **09:57:25 UTC**: lint/format (807 files), typing
(746 source files), zero module-boundary violations, unchanged compatible
101-operation API/client and production frontend build. Its first attempt
caught a reused test-local variable name with incompatible inferred types;
renaming it corrected the test without changing assertions or application code.
Documentation (401 Markdown files), M7 ticket traceability, synchronized planning
and diff whitespace checks Passed. Hosted/provider/fresh-install evidence is
not claimed by those checks.

## Remaining boundaries and effects

T005 commit retry needs the original captured admission, live M04 committing
ownership and Ollama request lease. A succeeded retained run does not supply
that authority. No lease was fabricated, committing fence weakened or live
owner database changed to manufacture this test. Fresh commit/retry and
interrupted-commit recovery remain required separately.

Remaining monetary work includes full compatible shared-pool/filter totals,
authoritative provider comparison, the other provider lanes and T013 daily
rate/breakdown/conditional estimate. Actual balance values are not a substitute
for source cost comparison. Existing official dashboard tabs were identified;
no numerical provider-display comparison was performed in this packet.

No production UI, provider behavior, account configuration, secret custody,
dependency, migration, license or default profile changed. New tests use genuine
private data or pure no-I/O result-policy inputs. The runtime remains at the
recorded installed revision; publishing verification code does not install a
different application. Root retains full M7 scope and the ticket catalog's
unfinished dispositions.
