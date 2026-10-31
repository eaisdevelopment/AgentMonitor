# M3 runtime process metrics transport evidence

Status: implementation Green; populated owner-browser rerun is owned by the M3 integration steward.

## Scope

- Requirements: `FR-DISC-002`, `FR-UI-002`, `AC-UI-002/006`, `AC-PROC-001`.
- Contracts: compatible `CTR-RUN-001` query-view expansion and additive
  `GET /api/v1/process-metrics` (`runtime_list_process_metrics_v1`,
  `AgentProcessMetricPageV1`). The frozen `AgentProcessViewV1` schema is unchanged.
- Data: current snapshot parent PID, user/system CPU ticks, resident pages,
  thread count, kernel state, source units/reasons, clock rate, page size, safe
  start marker, observation age, and freshness deadline. No content, command
  line, environment, path, or executable fingerprint is transported.

## Red / Green

- Red, real procfs -> production repository -> file SQLite:
  `test_real_linux_process_commit_replays_and_queries_history` failed with
  `AttributeError: 'AgentProcessRecordV1' object has no attribute 'parent_pid'`.
- Red, real migrated SQLite -> loopback FastAPI:
  `test_real_process_metrics_reach_authenticated_http_without_losing_semantics`
  failed with `KeyError: 'parent_pid'`.
- Red, built owner dashboard before the UI change: the populated browser timed
  out waiting for the `Parent PID` column.
- Green: focused M06/API/OpenAPI suite: `33 passed in 26.22s`; strict mypy:
  `Success: no issues found in 4 source files`; frontend typecheck and production
  build passed.
- Green, real Chrome + production build + Uvicorn + migrated file SQLite:
  `P02 BROWSER: PASSED — monitoring_dashboard`. The isolated database was
  truthfully empty; it did not prove populated metric cells.

The populated browser script now asserts every real row's parent PID, CPU ticks,
RSS pages, thread count, kernel state, safe start marker, observation age,
freshness deadline, source, and freshness-consistent presence. Its post-restart
owner-database run is Not Run here because the integration steward owns the
running service and owner database.

## Impact

No migration, dependency, provider write, profile mutation, or process-control
surface was added. RSS bytes and CPU seconds are display-only conversions from
the published page-size and clock-rate units; raw pages/ticks remain visible.
Missing/not-requested values retain their state and safe reason instead of
becoming zero.
