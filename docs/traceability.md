# Traceability matrix

## Purpose

This document is a human-readable family summary. The machine-readable
[`requirement-ownership.toml`](plans/requirement-ownership.toml) is the canonical
Draft mapping for every one of the 147 requirement and acceptance IDs: exactly
one primary plan, explicit supporting plans, exact contract IDs, exact defined
scenario IDs, and evidence boundaries. Its current 140 V1 and 7 post-V1 records
do not imply owner approval, implementation, test execution, or live evidence.

The tables below are navigational summaries only. Where a family crosses
modules, the exact per-ID primary in the machine manifest wins; a release cannot
rely on a family-level row.

## Requirement-to-module matrix

| Requirement IDs | Primary owner | Supporting modules/adapters | First milestone | Contract/evidence |
|---|---|---|---|---|
| FR-ORG-* | Registry | API, UI | M1/M2 | Organization/Account views; real DB/API/browser |
| FR-ACC-* | Registry | Provider system, provider adapters | M0/M2 | Discovery/registry contracts; owner identity confirmation |
| FR-AUTH-001..006 | Exact owner varies by ID; see canonical manifest | Registry, provider system/adapters, collection, API/UI, IAM | M0/M2–M5 | Auth-health/reauth contracts; live provider verification |
| FR-QUOTA-* | Capacity | Provider adapters, collection, UI | M0/M2–M5 | Quota observations/health; live reconciliation |
| FR-BUDGET-* | Capacity | Provider adapters, collection, UI | M0/M6 | Budget/cost contracts; live admin API reconciliation |
| FR-DISC-* | Runtime observation | Platform/provider adapters, registry | M0/M2–M5 | Session/process contracts; real workstation tests |
| FR-STATE-* | Runtime observation | Alerting, provider/platform adapters | M3 | Runtime states/events; pure policies + real processes |
| FR-COL-* | Collection control | Provider system/adapters, operations | M1/M2 | Collection request/run/events; real scheduler/provider tests |
| FR-HIST-* | Exact owner varies by ID; see canonical manifest | Capacity, runtime, alerting, operations, API/UI | M2/M7 | Owned histories, retention/export contracts; real DB |
| FR-ALERT-* | Alerting | Capacity/runtime/collection, UI | M3 | Alert state/events; pure policy + real DB/API/browser |
| FR-UI-* | React UI | All query contracts, API | M1 onward | Generated client; real built-browser workflows |
| FR-IAM-* | Identity/access | API, UI, security | M1 | Session/token/permission contracts; real HTTP/browser |
| FR-OPS-* | Operations | Persistence, deployment, all health ports | M1/M7 | Health/backup/export contracts; real service/restore |
| FR-SAFE-* | Exact owner varies by ID; see canonical manifest | All modules, security/API/adapters | All | Boundary checks and absence of process-control paths |
| FR-ROUTE-* | Deferred future module | Runtime/registry/capacity | Post-V1 | New ADR/threat model required |
| FR-CONTENT-* | Deferred future module | Security/data | Post-V1 | New consent/encryption/retention architecture |
| FR-REMOTE-* | Deployment/IAM future | All | Post-V1 | New remote threat model/ADR |
| FR-PROVIDER-EXT-* | New provider adapters | Provider system | Post-V1 | Provider protocol/capability matrix |

## Non-functional matrix

| Requirement | Evidence owner | Required gate |
|---|---|---|
| NFR-ARCH-001/002 | Integration steward | import-boundary checks, module-plan review, no circular dependencies |
| NFR-API-001/002 | API/UI | OpenAPI validation/diff, generated-client compilation, real HTTP/browser |
| NFR-DATA-001 | Persistence/operations | migrations, real SQLite behavior, repository portability review |
| NFR-TEST-001/002 | Every module | red/green evidence, prohibited-double scan/review, live matrix |
| NFR-SEC-001 | Security reviewers/module owners | threat review, secret scan, safe subprocess/path tests |
| NFR-PRIV-001/002 | Runtime/provider/API/operations | persistence/log/export inspection; no outbound telemetry |
| NFR-DOC-001 | Module owners/integration steward | doc impact gate and runbook exercise |
| NFR-LIC-001 | Dependency reviewer | admission records, lockfile/SBOM/notices/license scan |
| NFR-PLAT-001 | Platform adapters | real Linux verification; macOS Passed or visible Blocked state |
| NFR-PERF-001 | Performance plan owner | real generated AgentMonitor-owned load; no fake provider claims |
| NFR-RES-001 | Integration/collection | real module/process failure isolation scenarios |
| NFR-OBS-001 | Operations/security | structured redacted log review and diagnostic secret scan |
| NFR-COMP-001 | Contract owners | API/event/provider/database compatibility checks |

## V1 acceptance ownership

| Acceptance IDs | Owner/reviewer | Evidence phase |
|---|---|---|
| AC-V1-001..008 | Root/integration steward | M7 release review |
| AC-LIVE-001..007 | Provider adapter owners + owner | M2–M7 live verification |
| AC-UI-001..006 | IAM/API/UI owners | M1–M7 real browser |
| AC-PROC-001..005 | Runtime/platform/provider owners | M2–M5 workstation live tests |
| AC-ALERT-001..003 | Alerting owner | M3 pure + real stack + live conditions |
| AC-HIST-001..002 | Capacity/runtime/operations | M2/M7 real observation/database |
| AC-OPS-001..006 | Deployment/operations | M1/M7 target workstation |
| AC-TEST-001..006 | Each module + independent reviewer | Every milestone/release |

## Evidence reference format

Module plans allocate stable test/scenario IDs. Evidence references use a non-secret form such as:

```text
REQ: FR-QUOTA-001
TEST: CAP-PURE-014, CLAUDE-LIVE-003, UI-E2E-022
CONTRACT: quota-window.v1
EVIDENCE: live-reports/2026-.../CLAUDE-LIVE-003 (sanitized, not necessarily committed)
STATUS: Passed | Failed | Blocked | Not Run
```

## Maintenance

- New requirements get new IDs and an exact manifest record before implementation.
- Retired IDs remain recorded with reason/replacement.
- Contract or scenario changes update the exact manifest in the same review.
- Every module handoff identifies matrix changes.
- Release evidence records are joined to the exact manifest entries; this summary
  never becomes the release evidence source.

## 2026-09-29 bounded account terminal drill-down

FR-ACC-006 remains primarily M02; M06/P01/P02/A01/A04 support the
[owner process association change](plans/integration/live-agent-account-association-change.md)
and [duplicate identity correction](plans/integration/duplicate-account-overview-change.md).
CTR-RUN-006/007 V1 adds optional read metadata and browser-only conditional
owner settings writes; existing GET grammar stays compatible. Focused
AC-PROC-001/003/004, AC-UI-002/004/005/006 and AC-TEST-001/002/003/004/006
coverage is named in [the progress record](evidence/live-account-agents.md).
AUTO-ACCOUNT-AGENTS fails closed without an actual owner-completed terminal
link; detection/controls/duplicate presentation passed independently. Full M4,
automatic retrospective attribution and process/account switching are not
accepted by this bounded change.
