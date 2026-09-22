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

Checksum and post-migration validation failures while shared migrations were
being re-pinned were setup failures and are not claimed as behavioral Red.

## Green and refactor

The integration tests execute the canonical checksum-governed Alembic chain
through the current `v1_0504` head, including the M03-owned `v1_0300`, against
the real file-backed SQLite policy. They do not replace the migrations,
database, or repository with a double.

```text
backend/.venv/bin/python -m pytest \
  backend/tests/integration/provider_system -q
.............                                                [100%]
13 passed in 3.47s

backend/.venv/bin/ruff check <four focused Python files>
All checks passed!

MYPYPATH=backend/src backend/.venv/bin/mypy \
  --config-file backend/pyproject.toml --explicit-package-bases \
  <four focused Python files>
Success: no issues found in 4 source files

backend/.venv/bin/python -m pytest \
  backend/tests/provider_system/test_protocol.py -q
74 passed in 0.19s

python3 tools/automation/run.py AUTO-DOCS-CHECK
DOCUMENTATION CHECK: PASSED (222 Markdown files)
AUTO-DOCS-CHECK: PASSED (operational)
```

The cases prove exact round-trip after repository reopen; one-row/one-event
replay; immutable payload history with current/supersession semantics; two
concurrent writes in the same nullable scope leaving exactly one current row;
limits of 1..100 and safe error codes; rejection of scheme/rule data for an
unknown version at both DTO and database layers; rejection of naive/non-UTC
input and persisted timestamps; request-metadata-insensitive replay; and
rollback of both assessment and event when a real SQLite trigger rejects the
outbox insert.

## Integrity and residual gates

No mock, fake, stub, emulator, provider response, seeded provider telemetry,
provider/profile access, credential, prompt, response, source content, or raw
provider output was used. No dependency, provider adapter, registry,
collection/capacity/runtime, API/UI, generated file, or migration was changed.

The checkout-wide boundary checker remains Red pending shared reviewed
allowlists. Its finding attributable to this slice is the required M03 SQLite
adapter import of the shared policy module; the checker currently admits that
symbol set only for M01/M02. This task did not edit the forbidden shared
checker, and no architecture-gate pass is claimed.

Live Claude/provider conformance, account reconciliation, subscription values,
source/cost/rate evidence, collection/capacity/runtime commits, HTTP, and browser
verification remain Not Run. This evidence is not an `ST-CLA-001` completion or
V1-M3 exit claim.
