# M7 Overview query reliability

Status: implementation `cd4f566de137370a44978696cf22543e1581928c` installed
and published, with passing concurrent verification below. T010/T012, supporting T003; FR-BUDGET-002/005,
NFR-PERF-001, AC-UI-002/003/005, AC-TEST-001/002/006, M7-A07/A08.
M05 owns query eligibility and projection; root owns runner integration.

## Defect and smallest correction

The installed `79821bf` concurrent browser run reproduced Overview HTTP 504:
two expected financial rows, zero rendered and a visible refresh error. Setup
and cloud controls passed independently. The repeatable concurrent wrapper
reproduced this again at 05:13 UTC with zero mutation requests; serial success
is not treated as resolution.

Overview previously requested financial current/funds/binding metadata for every
active subscription account. On a genuine private SQLite snapshot the regression
failed with thirteen financial-current calls where only three were necessary.
The production-path profiler recorded 181 SQLite opens before the correction,
81 after it; full installed concurrency remains the decisive boundary.

The query now omits financial reads only for Claude/Codex accounts with no API
creation intent, an active subscription resource, exclusively subscription
resources and fewer than the existing resource reader's 100-row bound. At the
bound the list cannot prove absence of a later billing resource, so it retains
the financial query. Accounts created for API use, unknown or mixed resources,
empty resource lists and Ollama keep the existing path. Billing enrollment
atomically creates its resource. Inventory,
subscription IDs, full-filter pool resolution and final revision/resource
rechecks remain unchanged. No timeout increase, cache, query truncation or new
worker is introduced.

Independent review caught the 100-row issue. Its pure regression first failed,
then passed with the conservative bound. Review otherwise found the retained
pool/cloud/metadata fences intact. The actual provider and monetary behavior is
unchanged; this does not complete T010/T012 or M7.

## Verification

- Red: genuine metadata regression failed `13 == 3`, establishing unnecessary
  financial reads. An earlier import-path error was corrected and is not Red.
- Green: focused pure/projection/pool/sort/SQLite/live-stored-data set passed
  74 cases before the bound review; subsequent bound plus real HTTP/stored-data
  set passed 25 cases.
- Red/Green: resource-bound case failed at 100, then the final canonical pure
  lane passed 737 cases plus eleven presentation suites.
- Red/Green: existing runner rejected the planned Overview selector; exact
  revision browser selection now passes, invalid/missing revisions remain
  rejected. Sixteen scoped selector tests passed.
- AUTO-QUALITY passed at 05:16 UTC: formatting, strict types, boundaries,
  generated API/client compatibility, TypeScript and production build. No public
  schema change; 98 API operations remain compatible.

Reproducible commands from the M7 worktree, using the admitted tool context:

```bash
python3 -m tools.automation.implementations.auto_m7 --lane pure
python3 -m tools.automation.implementations.auto_m7 --lane browser --check overview --expected-revision=<installed-40-character-revision>
```

The browser selection runs the genuine private-copy tests and existing installed
Overview/setup/cloud probes concurrently. It reports the bounded checks and
retains full monetary Overview acceptance as Not Run, exiting nonzero until
that broader evidence is implemented. A passing concurrency subcheck does not
claim genuine monetary totals. Each child owns only its new browser tab and
settles before exit. No retries hide a failure. Exact revision, outcomes and
unsafe-request counts are validated; raw child diagnostics are not emitted.

## Compatibility and operations

CTR-CAP-006 Overview 2.7.0/history 2.8.0, CTR-REG-014 1.5.0 and installed schema
`v1_0734` retain their meanings. No API/type/migration/credential/dependency or
license change. Tests use actual private copied metadata and retained reports,
never provider fixtures or seeded telemetry. No default profile, owner account,
monitoring preference or running agent is changed.

Changed production paths are M05 domain/application `budget_overview.py` only.
Added pure and genuine metadata regression suites, the concurrent browser wrapper
and a scoped selection in the existing M7 runner. The accompanying planning
clarification retains all sixteen tickets. Deployment uses the existing
same-schema update/recovery command; installed evidence will be appended after
the exact candidate is exercised.

## Installed result

The canonical same-schema update passed for clean implementation revision
`cd4f566de137370a44978696cf22543e1581928c`, restoring the normal service
restart policy. The exact-revision browser selection then passed its three
genuine private-copy tests and all three concurrent installed probes at
05:20:04 UTC: Overview API/DOM, filters, financial entry/history/navigation,
responsive/pool controls; installed setup; and cloud usage read-only controls.
Each child verified the selected revision and zero unsafe requests. There was
no automatic retry of the earlier failed run; the production query changed.

`overview_concurrency` is Passed. The selection intentionally exits 3 with
`overview: NOT_RUN (m7_monetary_overview_required)` because the available cloud
data is counts-only; this does not close full T012 or M7. The observed 504
reproduction now passes; this is not an unlimited-load or all-financial-state
performance claim. Service is active and Dashboard HTTP 200 after verification.
GitHub `refs/heads/main` was verified at that implementation revision.

The staged secret scan initially flagged the documentation words describing
unknown/empty/mixed resources. Exact in-memory comparison confirmed ordinary
prose, not a credential; wording was clarified and the final scan passed with
zero findings. No scanner suppression was added.


## Reproduced concurrency failure and read-efficiency correction

At installed `4c6a63db8c8a7b465b6592e2ebb79fa69f81441c`, the new rate check
passed with genuine numeric input. The existing Overview/setup/cloud concurrency
check failed twice; an independent three-page read diagnostic observed Overview
HTTP504 at 10005ms. Current service had zero restarts. Standalone API200 and
serial rate success do not establish concurrent continuity.

A private unchanged genuine database profile identified 81 opens per Overview,
18 billing-status reads for three financial current queries, and writable mode
for SELECT-only resource reads. Two changes preserve authority checks:
composition consumes the binding repository's transactional eligibility directly,
mapping only its exact unavailable-account error to no binding; resource listing
uses the already supported read-only connection policy. No cache, timeout change,
new connection pool, schema/contract/dependency or provider operation.

Real test file: `backend/tests/live/ollama/test_budget_read_efficiency.py`.
Red before production correction: **2 failed, 1 passed in 13.72s**; 18 reads
versus six required fences and 30 journal-mode assignments versus zero. The
complete original/current DTO comparison and absent/ineligible metadata case
were not replaced with stubs. SQL tracing observes real statements and retains
counts only. Green with existing metadata/reconnect cases: **7 passed in 35.37s**.
The tests verify exact full snapshot equality, unchanged authority fences,
absent/ineligible binding compatibility and no journal-mode assignment on reads.

A paired same-copy measurement with the read-only fix common to both paths gave
prior binding composition 1.1646s and corrected composition 0.9604s. Overall
opens measured 81 before the packet and 73 after; billing reads fell 18→6. The
net reduction is eight opens because direct eligibility reads replace previously
skipped branches for some accounts. These are observations, not latency promises.

Root regression command used admitted shared pytest with
`test_billing_credential_binding.py`, `test_budget_account_empty.py`,
`test_budget_history_http_live.py` and `test_budget_overview_history_snapshot.py`:
**15 passed in 103.02s**. Boundary check had zero violations; changed files passed
Ruff. `AUTO-PLAN-CHECK` passed. The regression is added to the existing Overview
runner. Full quality, installed correction and concurrent browser acceptance
remain pending at this record; the first installed rate candidate is not called
fully verified or published by this evidence.


Local full quality passed at 10:51:38 UTC after regenerating the OpenAPI/client
source fingerprint (102 compatible operations). The first run correctly caught
generated drift after bootstrap changed; a later concurrent test-probe edit was
caught by Ruff and wrapped before the final clean run. Final result: 819 formatted
files, 758 typed source files, zero boundary violations, generated compatibility
and production frontend build passed. Independent read-only review found no
must-fix authority, policy-mode or test-integrity issue. Installed concurrent
verification remains required after the new correction is deployed.
