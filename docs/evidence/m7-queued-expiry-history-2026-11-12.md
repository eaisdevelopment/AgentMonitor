# M7 queued-expiry history repair

Status: bounded repair installed and published; broader concurrent browser
continuity remains failed. T007/T009/T010/T014; FR-BUDGET-006, AC-TEST-001/003/006,
M7-A05/A07/A09. M04 owns run semantics; P01 and the existing history UI consume
the corrected reads. Approved focused plan 1.1.0 already includes queued expiry.

## Actual failure and correction

The installed seven-day manual cloud probe at `d985cc7` submitted exactly one
collection. The run expired before dispatch; recovery correctly persisted
`failed` / `collection_queued_expired` with null start and duration. The run DTO
required a start/duration for every failure and rejected this legitimate record.
Collection-history and cloud run-status reads then returned 503. No successful
provider collection is claimed from this attempt.

CTR-COL-002 2.7.0 admits this precise budget-only terminal case: completion at
or after the deadline, null start/duration/payload/report, no observations, and
matching queued-expiry outcome/error. Quota validation and dispatched/committed
invariants remain unchanged. The existing rows need no rewrite or migration.
There is no change to wire fields, account setup, credentials, provider profiles,
dependencies or licenses. No provider request is required for this repair.

## Red and Green evidence

- Before production changes, the focused pure contract and genuine private
  SQLite snapshot tests produced **14 failures and 3 passes in 5.22s**. The
  decisive failures were valid expiry construction and reading the genuine
  persisted run, both `collection_run_state_invalid`. Negative cases also
  failed while constructing their valid base; they are not separate Red claims.
- After the correction: **17 passed in 8.88s**. The genuine snapshot test uses
  production repositories and a real authenticated HTTP server. It verifies
  history and the original cloud run status, retaining null start/report and
  the captured reporting context. It makes no provider request and creates no
  substitute financial data.
- Broader contract, quota-policy, recovery-policy and genuine HTTP regression:
  **73 passed in 7.22s**, zero skips.
- Existing canonical `collection_guards`: **72 passed in 27.31s**. This remains
  bounded guard evidence, not successful collection or full recovery acceptance.
- Read-only installed browser probe at 08:29:46 UTC on `d985cc7`: Failed,
  `collection_read_failed`, zero mutations. This is the pre-install Red.
- Canonical `queued_expiry_history`: **17 passed in 5.44s**; runner selection
  tests: **3 passed**. Missing genuine expiry remains a failed prerequisite.
- Local quality passed: 803 formatted files, 742 typed files, zero import-boundary
  violations, 101 compatible API operations, TypeScript and production build.
  Initial quality attempts caught a long test line and generated source-hash
  drift; formatting and the canonical generator resolved them. Wire schema
  hash is unchanged. Documentation and M7 planning checks passed.

The existing runner exposes the bounded genuine-history check:

```sh
python -m tools.automation.implementations.auto_m7 --lane technical --check queued_expiry_history
```

Its real snapshot must contain an actual expired run; absent evidence fails,
never skips or substitutes data. It does not accept the full recovery check.
The installed probe takes an exact installed revision and the original manual
run ID, and performs only authenticated GETs and history navigation:

```sh
node frontend/tests/browser/m7/verify_collection_expiry.mjs <installed-40SHA> <existing-run-id>
```

Changed files: collection contract, budget contract tests, genuine snapshot/HTTP
test, canonical runner/selection test, read-only browser probe, contract register,
delivery worksheet and this evidence. Follow-up: verify the same failed run on
the installed candidate, publish/verify that revision, and continue independent
T013 work. Successful manual seven-day collection remains a separate open item.

## Installed and public result

Implementation `d73c1717eca0c3968c45044bf9fe0a8747ae8d68` passed the existing
selected-revision updater, retaining schema `v1_0734` and restoring the normal
restart policy. Independent M04 review found no correctness defect in the
writer/read match. Staged secret scan found only two generated OpenAPI artifact
hashes, verified against actual old/new artifact bytes; zero unresolved findings.

At 08:34:37 UTC the installed probe passed original expired-run history and
status GETs and the rendered Collection / History page, with zero mutations.
Its first installed attempt passed both APIs but used the wrong navigation
label (`Collection/History` instead of the actual `Collection / History`);
correcting that locator made the same installed production code pass. No
provider request, start time, report or success was manufactured.
GitHub main was independently verified at the full implementation revision.

The wider concurrent Overview/setup/cloud probe is **not passed** on this
revision. The 08:34 attempt reported `comparison_source_unavailable` and
`cloud_collect_control_missing`; the 08:36 attempt reported
`overview_probe_boundary_failed`, `setup_form_unavailable` and the missing
cloud control. Intermediate direct reads returned available Overview and both
cloud accounts, with both cloud controls rendered. A subsequent browser network
inspection observed `net::ERR_NETWORK_CHANGED` on several genuine reads;
successful reads still rendered two financial rows and a quota table. This
does not establish the cause of every earlier failed assertion. Retain the
failures and verify concurrent continuity when the browser boundary is stable;
do not declare the broad probe passed from the narrower history result.

The navigation-locator correction and this receipt are successors to installed
production. No additional installation is needed for a probe/document change.
