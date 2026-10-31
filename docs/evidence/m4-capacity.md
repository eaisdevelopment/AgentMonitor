# M4 M05 capacity evidence — approved focused increments

Date: 2026-09-29. Status: **Intermediate implementation evidence**. This ledger
does not claim the canonical full M4 completion gate, full M05 acceptance,
HTTP/UI integration or unexecuted live conditions.

## Scope and contracts

Approved packet: [M4 capacity change](../plans/integration/m4-capacity-change.md),
I01, I02, I03 and I04. Requirements: `FR-ORG-003`, `FR-QUOTA-001..006`, supporting
`FR-COL-001..008`, `FR-HIST-001/002/005`; M05 portions of
`AC-LIVE-004/005/007`, `AC-HIST-001`, `AC-UI-002/005/006` and
`AC-TEST-001/002/003/005/006`. Compatible V1 changes affect
`CTR-CAP-001/003/004/005/006/007/008/009` with public `CTR-REG-009` and `CTR-EVT-001`
consumption. No master-plan approval flags were changed.

## Test-first evidence

| Step | Actual result | Expected reason / limits |
|---|---|---|
| I01 Red: new forecast/aggregate pure tests and selected real current metadata | 21 failed | Approved policies/contracts absent, default M05 policy unconfigured, actual stored native semantic role hidden; no missing-module import failure |
| I01 Green/refactor | 38 passed | Pure sufficient/insufficient forecasts, exact policy defaults, revision/coverage guards and genuine current metadata reads |
| I02 genuine Red | 1 failed, 1 passed | Actual current projections existed but bounded current alert query was absent |
| I02 pure Red | 11 failed | Native basis-point/current/no-value policy absent |
| Approved native percent complement Red | 1 genuine failure plus 1 pure failure | Supported fresh native percent reading could not yet produce explained current remaining condition |
| I02 complement Green | 53 passed | Native remaining ratio and explicit used-percent complement; exact-zero and stale/partial/conflict/no-value truth |
| I03 Red | 6 failed | Five closed-notice/digest behaviors absent; genuine persisted outbox lacked typed bounded read |
| I03 acknowledgement-policy Red | 5 failed, 5 passed | Exact duplicate/conflict/legacy-unknown proof policy absent as a pure application entry; no external receipt was fabricated |
| I03 Green plus coverage review | 67 passed, 1 skipped | Genuine outbox replay/current metadata/alert facts/aggregate/forecast explanations and pure policies; actual nonempty acknowledgement explicitly Not Run |
| Real fresh SQLite capacity schema suite after root catalog admission | 4 passed | Actual production Alembic chain, empty owned schema/invariants, no telemetry rows |
| I01–I03 assigned source Ruff and strict mypy | Passed; 14 source files type checked | No new suppression or dependency in those increments |
| I04 pure Red | 2 failed, 16 passed; new availability test had an expected missing-module collection error | Latest reset-compatible suffix, exact bounded reset relation and capability identity guard were absent |
| I04 pure Green | 20 passed | Latest exact segment, before/after/unknown reset relation, stale/partial/identity-unproven no-value |
| I04 selected genuine Reds | 1 failed for forecast query; later 1 failed for union adapter | Actual current windows lacked a distinct persisted forecast query; genuine outbox lacked the separate event union adapter |
| I04 staged migration | Fresh production SQLite DDL integrity `ok`, foreign keys clean; root pinned SHA `7d6314c...` and DDL digest `bb7fc310...` | 0707 additive nullable snapshot/source columns, independent availability table and new event producer version; no old rows backfilled |
| I04 actual owner-copy Green | 3 passed | Actual SQLite backup upgraded v1_0603 to pinned v1_0707, durable no-value forecast and capability unknown/stale facts, typed projection events, idempotent repeat; temporary copy deleted |
| Owned combined suite after 0707 | 77 passed, 1 skipped, 1 stale inventory failure; targeted correction 4 passed; final combined rerun **78 passed, 1 skipped** | Owned schema inventory omitted the new table; exact acknowledgement remains opt-in and Not Run |
| I04 Ruff and strict mypy | Passed; 19 owned source files type checked | No new package; SQL adapters use a file-local E501 exception to keep predicates auditable |

During initial Green runs, the new gap-test query time was corrected to use its
actual latest constructed sample; page/digest assertions were corrected to the
published names `limit`, `next_key`, `input_set_digest`. These were test-input or
test-name mistakes, not additional behavioral Reds. They are not claimed as
separate TDD evidence. A concurrent M02 missing-import failure briefly blocked
the genuine complement Red; root fixed its import before the real Red/Green.

Commands used from repository root:

```bash
PYTHONPATH=backend/src AGENTMONITOR_TEST_DATA_ROOT=/home/dev/.local/share/agentmonitor backend/.venv/bin/python -m pytest backend/tests/capacity backend/tests/integration/capacity/test_m4_current_metadata.py backend/tests/integration/capacity/test_m4_event_delivery.py -q --tb=short
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest backend/tests/integration/capacity/test_capacity_schema_chain.py -q --tb=short
backend/.venv/bin/ruff check backend/src/agentmonitor/contracts/capacity_v1.py backend/src/agentmonitor/modules/capacity backend/src/agentmonitor/adapters/persistence/capacity/sqlite/repository.py backend/tests/capacity/pure backend/tests/integration/capacity/test_m4_current_metadata.py
PYTHONPATH=backend/src AGENTMONITOR_TEST_DATA_ROOT=/home/dev/.local/share/agentmonitor backend/.venv/bin/python -m pytest backend/tests/capacity backend/tests/integration/capacity/test_m4_current_metadata.py backend/tests/integration/capacity/test_m4_event_delivery.py backend/tests/integration/capacity/test_m4_current_forecast.py backend/tests/integration/capacity/test_capacity_schema_chain.py -q --tb=short
```

Strict type command from `backend/`:

```bash
MYPYPATH=src .venv/bin/mypy --explicit-package-bases --config-file pyproject.toml src/agentmonitor/contracts/capacity_v1.py src/agentmonitor/modules/capacity src/agentmonitor/adapters/persistence/capacity/sqlite/repository.py
MYPYPATH=src .venv/bin/mypy --explicit-package-bases --config-file pyproject.toml src/agentmonitor/contracts/capacity_v1.py src/agentmonitor/modules/capacity src/agentmonitor/adapters/persistence/capacity/sqlite/repository.py src/agentmonitor/adapters/persistence/capacity/sqlite/current_repository.py src/agentmonitor/adapters/persistence/capacity/sqlite/current_events.py src/agentmonitor/adapters/persistence/capacity/sqlite/forecast_snapshot.py
```

These exact invocations provide module evidence; root still owns canonical
routine admission and the complete fail-closed milestone gate.

## Real verification and explicit limitations

- `M4-CAP-L01`: selected genuine enrolled data traversed public registry and
  production capacity ports. Scope revision, eligibility/coverage partitions
  and native inventories were checked; no unrelated percentages were summed.
- `M4-CAP-L02`: actual stored window metadata, current projection generation,
  collection/observation lineage and storage timestamps were preserved. Legacy
  missing constraint evidence remains Unknown until a genuine post-upgrade
  collection; there is no backfill.
- `M4-CAP-L03`: actual recent immutable history returned explained no-value
  forecasts. Pure sufficient forecasts pass. A naturally observed available
  forecast remains **Not Run**: the supported Claude source does not provide a
  trustworthy reset instant or rounded uncertainty bounds. No reset or bound
  was manufactured.
- `M4-CAP-A01`: genuine fresh native percent observations produced explicitly
  derived complement facts with original precision/confidence and actual
  durable current `record_version`; stale/partial/conflicted inputs stay
  non-evaluable.
- `M4-CAP-E01`: genuine existing outbox read, bounded producer-sequence paging,
  stable replay, exact three-field payload digest and actual historical M05
  receipt version passed. Nonempty exact acknowledgement/reopen is **Not Run**
  in this assignment until composition supplies an actual committed consumer
  receipt. The opt-in test never fabricates one.
- Fresh post-upgrade classified commit/receipt replay and SQL health projection
  policy are **still required at root integration**. This agent did not run a
  provider, migrate the owner installation or restart services.
- `M4-CAP-L04`: the actual owner SQLite database was read through SQLite's
  consistent backup API into a private temporary file (mode 0600), upgraded by
  the production catalog from v1_0603 to v1_0707, then deleted after the test.
  M05 persisted current forecast and capability facts with actual source
  generations. Its first event batch contained the typed new producer payloads;
  a second refresh at the same actual `as_of` did not advance generations or
  add events. The old commit-only reader retained its original meaning.
  Numeric forecast remained no-value: native Claude reset/rounding bounds were
  not fabricated. Native capability `available` remained unasserted because
  public stored quota facts lack a per-observation identity-binding proof.
- Naturally rare/aged source states, full retention/export/backup/restore,
  account equality/additive-pool evidence, numeric forecast and verified
  availability/recovery, event consumption in M07, API/client/UI and full
  milestone acceptance remain outside this bounded evidence.

The actual acknowledgement test requires `AGENTMONITOR_RUN_CAPACITY_EVENT_ACK=1`
and safe explicit selectors `AGENTMONITOR_TEST_DATA_ROOT`,
`AGENTMONITOR_TEST_CAPACITY_ACK_EVENT_ID`,
`AGENTMONITOR_TEST_CAPACITY_ACK_RECEIPT_ID` and
`AGENTMONITOR_TEST_CAPACITY_ACK_CONSUMER`. Root must populate them from a genuine
completed consumer commit. The internal receipt-commit precondition is never
checked by reading another module's tables in M05. Missing selectors fail once
the test is explicitly selected; absent opt-in is reported Not Run.

## Persistence, security and delivery

Root allocated and pinned revisions `v1_0703` (nullable actual constraint
evidence and forecast precision columns), `v1_0704` (paired nullable exact
acknowledgement proof), and `v1_0707` (durable current forecast snapshot/source
reference, independent availability streams and typed event producer version).
All old revisions are unchanged. Root controls catalog,
schema fingerprint/head and the actual offline verified-backup upgrade. Legacy
nullable metadata is not backfilled. Legacy forecasts lack a snapshot and are
unavailable to the new current query until a genuine refresh.

No dependency, license, production configuration key or provider-profile write
was introduced. Data remains opaque references, canonical quantities, safe
codes, approved source versions, digests and actual UTC timestamps. No account
identity, project path, process environment, prompt/response, provider raw output
or credential was added to M05 facts/events/evidence. Provider-owned state and
running processes were untouched. M05 reads/writes only owned `capacity_*`
tables; persistence reaches pure policies through owned application ports.

Outbox `subject_version` retains original target-generation meaning and is never
used for condition generation. Historical producer version comes from actual
persisted M05 commit receipts. New delivery consumer version is Unknown because
the frozen acknowledgement port does not supply a build version; known old
versions are preserved. Identical proof is idempotent, conflicting proof fails
closed, old acknowledgement without proof remains unknown, and observations and
outbox rows survive acknowledgement.

## Handoff files and remaining root work

- `contracts/capacity_v1.py`: additive metadata/coverage/forecast/fact/notice DTOs
  and public current-condition/event protocols.
- M05 `domain/{aggregation,forecast,health,alert_conditions,events,current_projection}.py` and
  `application/{queries,ports,events,current}.py`: pure policies and composed query
  boundaries; no cross-module implementation import.
- Owned SQLite repositories: stored metadata/history reads, actual classified
  health on commit, durable forecast/availability producer and bounded current
  condition/event read and acknowledgement ports.
- Owned migrations `v1_0703_m05_capacity_projection_metadata.py`,
  `v1_0704_m05_event_delivery_proof.py`, and
  `v1_0707_m05_current_capacity_projections.py`, pure tests and real integration tests.
- [Module documentation](../modules/capacity.md) and approved focused packet.

Root must integrate exact contracts into API/client/overview and M07, run actual
receipt acknowledgement and fresh post-upgrade health commit, refresh the
reviewed critical-health mutation binding, bind an actual per-observation
identity proof and auth/collector runtime condition ports, admit canonical
automation and pass the full M4
gate before reporting milestone completion.
