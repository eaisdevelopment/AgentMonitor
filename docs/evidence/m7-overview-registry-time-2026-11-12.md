# M7 Overview: current registry with pinned financial evidence

Status: correction under verification; not yet installed at this checkpoint.
T010/T012/T014, FR-ORG-003, FR-BUDGET-001/003/004, AC-UI-005/006,
M7-A07/A08/A10. Root integrates M02 metadata and M05 read policy.

## Observed defect

Installed Back navigation repeatedly returned `/api/v1/budgets` availability
`unavailable`, reason `budget_overview_registry_changed`. The safe browser
diagnostic at 09:09:30 UTC on `c59d068` identified this exact failure after
Overview, filters, financial entry, source history and window checks passed.
No mutations occurred. Earlier generic failures did not establish the cause.

An unchanged private copy of real storage reproduced the difference: financial
cutoff one microsecond before its actual registry update failed, while the
current cutoff returned two rows. Exception tracing restricted to fixed reason
codes identified `financial_pool_time_conflict` in the pool repository. No
provider data, timestamps or owner configuration were rewritten.

Overview already resolves current accounts/resources/groups. Pool reads alone
also required their timestamps to precede the financial cutoff. A background
registry update after opening Overview could therefore make Back unavailable.
This is not proof of a genuine current scope or permission change.

## Small compatible correction

CTR-REG-014 1.9.0 adds explicit `read_current` and snapshot `metadata_basis`.
Legacy callable reads retain their cutoff-time rules and default metadata basis.
The new path resolves current metadata in one transaction at the expected
registry revision, with only open memberships. M05 explicitly opts into that
path and rereads it after assembly. Reports/funds retain their selected cutoff;
scope/binding, authorization, current revision and command timestamp checks are
unchanged. No clock, migration, dependency, endpoint or owner action is added.

## Evidence

- Meaningful Red: two failed in 10.23 seconds. The new metadata method was absent;
  the genuine composed Overview returned `budget_overview_registry_changed`.
- Green: 41 passed in 24.38 seconds across real isolated pool metadata,
  genuine snapshot regression, empty Overview integration and pure pool policy.
  Legacy old-time refusal, stale revision refusal and closed-membership rejection
  remain exercised. The snapshot regression is read correctness, not monetary
  provider reconciliation.
- Independent read-only M04 review found no must-fix correctness/security issue
  and confirmed that installed Back/reload still requires verification.
- The existing canonical Overview selector now includes the genuine snapshot
  regression before installed concurrent browser checks; no new gate is added.
- Further genuine Overview, real HTTP and complete-inventory metadata checks:
  eight passed in 35.49 seconds. Canonical pure regression: 755 backend cases
  in 18.98 seconds plus twelve presentation suites passed.
- `AUTO-QUALITY` passed at 09:21:10 UTC: 806 formatted files, 745 typed sources,
  zero boundary violations, TypeScript/build and compatible 101-operation API.
  Public HTTP schema is unchanged; generated source/artifact identity advances.
  Documentation, synchronized planning and ticket tracing passed.

Changed: registry pool contract/repository, M05 Overview, registry integration
and genuine snapshot tests, existing M7 runner, generated source identity and
plan/contract/evidence documentation. Installation, broader regressions and
actual concurrent browser outcome will be recorded after execution. Full M7
provider/analysis/release scope remains unfinished.
