# M7 Overview query reliability

Status: local implementation with bounded verification; installed concurrent
verification remains pending. T010/T012, supporting T003; FR-BUDGET-002/005,
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
