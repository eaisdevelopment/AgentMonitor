# M5 scheduled collection recovery after timeout

- Status: Owner-approved; implementation and deployment authorized by the
  owner's 2026-10-27 “yes” to the focused timeout recovery and deployment.
- Plan version: 1.21.0.
- Owner: PLAN-INT; M04 scheduler composition owns the correction. A02's
  per-operation timeout and cleanup behavior remains unchanged.
- Parent: [M5 Codex change](m5-codex-slice-change.md).
- Requirements: FR-COL-001, FR-COL-003, NFR-RES-001, AC-LIVE-005,
  AC-TEST-001/002/003/004/006.
- Contracts: compatible use of CTR-COL-002/004/006/007 V1 and
  CTR-PROV-002/004 V1; REST `/api/v1`, database `v1_0707`, provider
  `codex-cli 0.160.0`, adapter and schema versions unchanged.

## Evidence and intended behavior

The active clean revision `468a937d796efcb7ff1785a749789f07a3322abc`
recorded a genuine managed Codex collection timeout at 2026-10-25 22:05 UTC.
The selected monitored account had no later run, while other accounts kept
updating. On 2026-10-27 the authenticated quota prerequisite returned
`current_codex_lineage: m5_quota_current_lineage_required`. The scheduler's
`_is_transient_failure` rejects the exact deadline code; `poll_is_due` then
rejects every future scheduled run for that account.

Allow the exact `codex_app_server_deadline_exceeded` code to admit a distinct
future scheduled run after the existing full minimum cadence (300 seconds).
Never retry the expired operation itself. Preserve its failed record, existing
deadlines, owned-child cleanup, durable admission, target checks, request budget,
identity checks and rate limits. Repeated timeouts remain failed observations
with at most one new scheduled attempt per normal cadence. Authentication,
identity, version, schema, cleanup and unknown failures retain their current
classification. The existing explicitly delayed provider-unavailable policy
also remains unchanged. No provider adapter or generic domain policy change
is required.

## Scope and test design

- `backend/src/agentmonitor/composition/codex_dashboard_collection.py`: exact
  timeout eligibility for a new scheduled run only.
- `backend/tests/adapters/providers/codex/unit/test_collection_action_policy.py`:
  pure regression over timeout classification and real production cadence
  policy, before/at/after 300 seconds, persisted failed status, repeated
  timeout timing, and unchanged security failure exclusions.
- Existing real SQLite collector, adapter security, and M5 Story tests remain
  mandatory; no fabricated provider response or injected telemetry.
- `tools/automation/implementations/m5_service_activation.py` and its tests:
  one ninth rollover from the exact revision above into fixed singleton
  `m5-service-activation-corrective-archive-468a937`. Retain all eight earlier
  archives and all existing guards, rollback, receipt, revision and no-replace
  checks. No tenth rollover or general deployment is authorized.
- `auto_m5_current_exit.py` and its tests: rebind only the intentional exact
  Story inventory from a successful final report, preserving zero-skip checks.
- Update routine catalog, completion standard, runbook, Codex operator guide,
  M5 evidence/index/status, and generated planning snapshot plus CS1 bindings.

Regression IDs: M5-CDX-COL-014 (timeout cadence recovery), M5-SVC-ACT-024
(ninth exact rollover). Obtain behavioral Red before production edits, then
focused Green, complete affected files, exact Story suite, quality, build,
documentation and synchronized planning. Run the canonical M5 completion
command for milestone closure; local regression passes alone do not close M5.

## Deployment and live verification

Commit the isolated candidate cleanly. Run the existing two-invocation
`AUTO-M5-SERVICE-ACTIVATE` with the new exact ninth binding. Verify HTTP and
authenticated dashboard readiness and fresh scheduled recovery for the account
with the retained real timeout, including successful collection and quota
history through the versioned API. Do not edit history or provider profiles to
recover it. The old revision remains intact for archive validation.

Archive stale prerequisite files through `AUTO-M5-ARCHIVE-PREREQUISITES`;
collect current owner, alert, quota and process evidence before `AUTO-M5-EXIT`.
Preserve the passing 2026-10-27 alert witness as evidence of the old service;
it cannot be reused for the new service. Provider login remains owner-controlled
if actually required; no login is assumed necessary for this timeout.

## Impact and stop conditions

No contract shape, migration, schema, dependency, license, secret, credential,
default profile or running-agent change. Existing managed authentication
maintenance policy applies to the new scheduled observation. Risks R-006 and
R-007 are addressed by full cadence and truthful retained failure/stale state.
Stop on unexpected provider behavior, containment/cleanup failure, identity
mismatch or failed activation rollback. Missing live evidence remains Blocked.
This approval supersedes 1.20's production and ninth-rollover exclusions only
for the bounded correction and deployment described here.
