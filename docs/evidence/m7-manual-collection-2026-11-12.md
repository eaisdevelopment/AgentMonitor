# M7 selected-period manual collection

Status: local implementation and verification in progress. T007/T010/T011,
FR-COL-004/008, FR-BUDGET-001/004, M7-A01/A06/A07/A09. No ticket or milestone
closure is claimed by this increment.

## Behavior and contract impact

CTR-COL-002 2.4.0 adds a selected-context manual command, read-only eligibility
and captured run-context query to the existing billing action port. The new
admin/CSRF collection POST uses the selected 7/30 completed UTC-day ungrouped
cost interval. Check retains its wire input. New Check and scheduled admissions
also capture their default seven-day context; legacy stored admissions remain
readable without inventing their context. M05 asks M04 for the exact selected
cost context before choosing the latest run, rather than presenting another
period's attempt as its status.

Manual verification authority permits one explicit owner read while automatic
monitoring is disabled. It does not modify monitoring. Scheduled verification
and unrelated event triggers remain forbidden; manual requires principal and
idempotency identity. Replay checks captured context; changed selection under
the same key conflicts. The existing worker, durable target envelope, registry
fences and atomic reservation remain authoritative.

M04 projects the later future restriction from persisted provider retry and an
unreleased current-window reservation. The current billing policy reserves its
whole bounded allowance per run. This read is advisory; POST admission handles
concurrent changes. Eligibility GET never reconciles or creates a service target;
M02 supplies a read-only lookup for an existing service authority. No database
migration, dependency, license, credential handling or provider-profile change.

P01 adds collection and eligibility routes; generated client 2.0.12 validates
95 operations compatibly. P02 renders Collect now and Refresh collection status
for billing resources, including no-report intervals. A single session intent
per account/resource survives navigation and reload with its original interval.
No automatic mutation occurs after reload/sign-in. Confirmed rate-limit failure
requires fresh eligibility before retry; unknown outcomes reconcile with their
original identity. Successful completion advances the financial read only for
the matching selected interval. Existing Ollama controls are not represented as
manual usage collection; that remains separate unfinished T007/T009 work.

## Red and Green evidence

- Command/context tests failed for missing BillingCollectCommandV1 and later
  passed. Provider tests failed with anthropic_billing_run_invalid and
  openai_billing_run_invalid for explicit manual/disabled-monitoring authority,
  then passed after the bounded authority correction.
- Real IAM/HTTP collection POST returned 404 before the route existed; tests then
  passed authentication, CSRF, preconditions, closed body and absent-target
  behavior. Real eligibility GET similarly failed before its route existed.
- Real isolated owner metadata failed for the missing eligibility method; it
  now returns credential-required without creating any run/service target or
  changing metadata. No credential or provider telemetry is seeded.
- M04 cooldown: 15 new pure/empty-SQLite cases Red to Green; 31 scoped regressions
  passed. Populated reservation/retry SQL is not proved by empty storage.
- M05: 9 missing-context-helper cases and 2 real-empty-SQLite status failures;
  37 focused regressions passed after exact-context lookup was added.
- P02 pure test initially failed because its helper did not exist. The added
  cross-window regression later failed because restore discarded another
  selected interval; it passed after retaining one original resource intent.
  Existing billing-check and window-navigation pure suites also passed.
- New Check/scheduled context tests failed for missing captured defaults;
  12 scoped action/scheduling tests passed. A security regression demonstrated
  that widening manual authority also admitted unrelated verification triggers;
  the correction retained the prohibition and 27 focused cases passed.
- Independent action/API/UI review found that an unregistered safe error code
  changed intended 422 to 500. The pure response assertion reproduced that failure
  and passed after adding the explicit problem-catalog entry. Review found no
  further concrete must-fix in its bounded scope; reviewer-owned cooldown code
  was excluded from its independent assessment.
- Combined focused run: 149 passed before the final small error-catalog fix.
  Canonical pure: 692 Python tests plus 10 presentation suites passed before that
  extra pure regression; canonical collection_guards: 55 passed.
- AUTO-QUALITY at 03:10:37 UTC passed Ruff 779, mypy 718, zero boundary violations,
  generated compatibility, TypeScript and production build. Subsequent safe
  error-catalog correction requires final quality/generated recheck.

Earlier integration attempts correctly failed on a negative-test mypy annotation
and generated source-hash drift; both were corrected. The initial expanded
browser command stopped during build with generated_drift, so it did not produce
browser behavior evidence. Do not call that a UI Red.

## Real-environment limits and remaining work

Read-only authenticated installed inventory at this checkpoint: 15 accounts,
zero Anthropic/OpenAI billing connections, no further account page. Dashboard
service active, HTTP 200. An initial browser inventory evaluation failed during
page startup; retry after the actual authenticated UI was ready succeeded.
No owner registry, credentials, monitoring preference or agent process changed.

Successful monetary source→admission→commit→API→DOM, populated cooldown SQL,
manual replay/restart against real billing authority, complete provider/range/
category scheduling and Ollama manual usage remain unverified or unfinished.
The existing owner setup request is not repeated. These affect their dependent
live lanes only; independent implementation continues. Full M7 exit has not run.

Canonical budget_http_guards passed 21 real no-report/HTTP checks. The expanded
closed collection body and read-only service-authority lookup then passed all
seven focused action/HTTP tests.

The canonical `browser --check owner_pool_controls` passed against the built
candidate and isolated real IAM/SQLite. Added assertions verify credential-
required disabled Collect now, exact thirty-day eligibility and zero collection
POSTs during range/status/reload. Existing pool CRUD, attribution, uncertain
metadata replay, pagination, sorting and responsive checks also passed. This
uses isolated owner metadata only, not synthetic reports or the live registry.

Final AUTO-QUALITY at 03:19:49 UTC passed Ruff 779, mypy 718, boundaries,
95-operation compatible generation, TypeScript and production build after the
safe-error correction. A negative-test response-body type/format issue was fixed
without changing product behavior. Git/documentation/planning preflight passed.
The staged-patch scan reported two generic-api-key matches; both were generated
OpenAPI artifact SHA256 declarations, verified against actual old/new artifact
bytes. No credential finding or secret output was retained.
