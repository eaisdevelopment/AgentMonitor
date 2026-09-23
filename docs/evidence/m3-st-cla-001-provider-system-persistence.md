# ST-CLA-001 provider-system persistence evidence

- Status: **focused persistence Green; broader Task 3 Not Run**.
- Module/plan: M03 provider system / `PLAN-M03`, V1-M3 Task 3 persistence slice.
- Requirements: `FR-COL-004/006..008`, `NFR-COMP-001`, `NFR-DATA-001`,
  `NFR-SEC-001`.
- Acceptance exercised: `M03-DB-001..006/008/009/013`.
- Contracts: additive `CTR-PROV-002` V1 compatibility input/view/outbox DTOs;
  no HTTP or provider contract behavior was changed.
- Recorder/date: implementation worker, 2026-09-22.

## Red

At `2026-09-22T17:53:17Z` this focused command failed against the real checkout:

```text
backend/.venv/bin/python -m pytest \
  backend/tests/integration/provider_system/test_compatibility_repository.py::test_assessment_round_trip_survives_real_sqlite_reopen -q

FAILED ... ModuleNotFoundError: No module named
'agentmonitor.adapters.persistence.provider_system'
1 failed in 0.25s
```

The failure was the expected absent production persistence adapter. An earlier
wrong-interpreter setup failure was not counted as Red.

Further behavioral Reds retained during review were:

| Time (UTC) | Test | Expected failure |
|---|---|---|
| `2026-09-22T18:13:05Z` | non-available version DB tuple | `DID NOT RAISE IntegrityError`; SQLite accepted non-null scheme/rule |
| `2026-09-22T18:18:20Z` | input timestamp contract | generic `timestamp-must-be-aware-utc`; stable compatibility code absent |
| `2026-09-22T18:43:52Z` | semantically identical reassessment | later request produced a different assessment/fingerprint |
| `2026-09-22T18:43:52Z` | two persisted non-UTC timestamp cases | generic `provider_system_repository_unavailable`, not record-invalid |
| `2026-09-22` | calendar-invalid canonical-looking UTC direct SQL | real file SQLite accepted `2026-02-30T13:00:00.123456Z`; the focused probe exited 1 with `AssertionError: calendar-invalid canonical-looking UTC timestamp was accepted` |

Checksum and post-migration validation failures while shared migrations were
being re-pinned were setup failures and are not claimed as behavioral Red.

The independent-QA correction added the exact missing behavioral checks before
changing production artifacts. Against the then-current admitted `v1_0300`:

```text
backend/.venv/bin/python -m pytest \
  backend/tests/integration/provider_system/test_compatibility.py \
  backend/tests/integration/provider_system/test_compatibility_repository.py -q
..FFFF..FFFFFFFFFF.....FF......
16 failed, 15 passed in 5.28s
```

The failures were the expected acceptance of non-lowercase/non-hex
fingerprints, noncanonical or misordered timestamps, an invalid version scheme,
an empty available version value, invalid outbox state/time/attempt tuples,
invalid public query arguments, and the same missing relationships in the
public outbox DTO. Existing enum checks remained Green and were retained as
regressions.

## Green and refactor

The integration tests execute the canonical checksum-governed Alembic chain
through the current `v1_0504` head, including the M03-owned `v1_0300`, against
the real file-backed SQLite policy. They do not replace the migrations,
database, or repository with a double.

```text
backend/.venv/bin/python -m pytest \
  backend/tests/integration/provider_system -q
................................                             [100%]
32 passed in 6.09s

backend/.venv/bin/python -m pytest \
  backend/tests/integration/provider_system/test_compatibility.py::test_m03_db_008_rejects_calendar_invalid_canonical_utc \
  -q --tb=short
1 passed in 0.43s

backend/.venv/bin/python -m pytest \
  backend/tests/persistence/sqlite/migrations/test_v1_0000.py -q
29 passed in 6.28s

backend/.venv/bin/ruff check --config backend/pyproject.toml <five focused files>
All checks passed!

MYPYPATH=backend/src backend/.venv/bin/mypy \
  --config-file backend/pyproject.toml --explicit-package-bases \
  <four focused source/test files>
Success: no issues found in 4 source files

backend/.venv/bin/python -m pytest \
  backend/tests/provider_system/test_protocol.py -q
74 passed in 0.15s

python3 tooling/foundation/check_boundaries.py .
boundaries: PASS (0 violations)

python3 tools/automation/run.py AUTO-DOCS-CHECK
DOCUMENTATION CHECK: PASSED (222 Markdown files)
AUTO-DOCS-CHECK: PASSED (operational)
```

The cases prove exact round-trip after repository reopen; one-row/one-event
replay; immutable payload history with current/supersession semantics; two
concurrent writes in the same nullable scope leaving exactly one current row;
validation of every public query argument with safe codes; lower-case SHA-256,
canonical UTC, validity ordering, enum and version-tuple constraints through
direct SQL; matching outbox DTO/database lifecycle and time ordering; rejection
of naive/non-UTC input and persisted timestamps; request-metadata-insensitive
replay; and rollback of both assessment and event when a real SQLite trigger
rejects the outbox insert.

The calendar-validity correction loads the production `v1_0300`
`_canonical_utc` expression into a real temporary file SQLite `CHECK`. Before
the migration edit the probe exited 1 with the assertion recorded above. After
the edit it exited 0, accepting the canonical leap-day value
`2024-02-29T23:59:59.123456Z` and rejecting the impossible-day value. The
canonical integration test performs the same two direct-SQL operations against
the migrated production table.

The unpublished `v1_0300` bytes are pinned as
`db44963d67744c6d5dae3b941b6f15783e082c9e4828dd7fb327c14d2c8e34d3`.
The integration steward atomically re-pinned the combined catalog as
`1540b1c21bc7c49c78ef3c10be1084453e88ce212d115a226ce77151c1739e2a`,
the through-M3 structural schema as
`aa65cda689f337c8fe7189d723812b10a2a4ecac53d63e68a9e56ff51a4b48e7`,
and the through-M5 schema as
`8a975e08cf454d1c1189791d5e53c248786d42857d66df4d0bcf745deaa28111`.

## Integrity and residual gates

No mock, fake, stub, emulator, provider response, seeded provider telemetry,
provider/profile access, credential, prompt, response, source content, or raw
provider output was used. No dependency, provider adapter, registry,
collection/capacity/runtime, API/UI, generated file, or Task 4 migration was
changed by this worker. The only schema source change is the unpublished,
M03-owned `v1_0300`; the integration steward performed the shared digest
re-pin. The boundary checker is Green without an allowlist change.

Only pending outbox creation/query is implemented. Claim, retry, delivery,
consumer receipt/checkpoint, replay, retention, and recovery scenarios remain
Not Run even though the DTO/database reject impossible claimed/delivered rows.

Live Claude/provider conformance, account reconciliation, subscription values,
source/cost/rate evidence, collection/capacity/runtime commits, HTTP, and browser
verification remain Not Run. This evidence is not an `ST-CLA-001` completion or
V1-M3 exit claim.
