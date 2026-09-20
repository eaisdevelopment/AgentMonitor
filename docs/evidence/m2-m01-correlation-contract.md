# M01 frozen correlation-ID grammar — Story 4 dependency evidence

- Status: **Accepted as a narrow Story 4 dependency repair** after independent specification and QA reviews. This is not Story 4 or M2 acceptance.
- Owner/date: M01 worker, 2026-09-20.
- Requirement/acceptance: frozen P01 plan §10.1 request-ID grammar `[A-Za-z0-9._:-]{1,64}`; M01 request-origin correlation/audit continuity; `NFR-SEC-001`; Story 4 P01/M01 boundary dependency.
- Contract impact: M01 V1 published ports now accept the full already-frozen P01 request-ID grammar. Resource IDs, session/token selectors, cursors, receipt keys, and safe audit shapes remain unchanged. No DTO version, database schema/migration, OpenAPI, generated client, dependency, provider, or profile change.

## Genuine Red → Green

The new integration tests use real owner-only file-backed SQLite, production Alembic migration, production bootstrap and login ports, and real Argon2. They exercise legal `a.b:c` through bootstrap, local recovery, login, session resolution/CSRF/list/logout, token create/resolve/list/rotate/revoke, and the bounded safe event query. They also reject non-ASCII `é` at bootstrap, recovery, login, token creation, and audit query. The tests assert persisted safe audit correlation exactly equals the supplied P01-valid value and check no invalid bootstrap/token row is created. No credential, PHC, or one-time issue is printed or compared in failure output.

| Stage | Exact command | Sanitized result |
|---|---|---|
| Red: real SQLite rejected a P01-valid ID | `backend/.venv/bin/python -m pytest backend/tests/integration/identity_access/test_correlation_contract.py -q --tb=short` | Exit 1; 2 failed in 0.38 s. Bootstrap and login both raised safe `iam_repository_unavailable` on legal `a.b:c`. |
| Red: missing pure predicate | `backend/.venv/bin/python -m pytest backend/tests/identity_access/test_correlation_policy.py -q --tb=short` | Exit 2; import collection failed because `valid_correlation_id` was absent. |
| Green: dedicated correlation-only predicate and adapter use | `backend/.venv/bin/python -m pytest backend/tests/identity_access/test_correlation_policy.py backend/tests/integration/identity_access/test_correlation_contract.py -q --tb=short` | Exit 0; 3 passed in 0.53 s after extending acceptance coverage. |

The standalone predicate uses `type(value) is str` and an exact anchored ASCII grammar. The adapters use it **only** at correlation validation sites, not their existing `_SAFE_ID` resource/cursor checks. Replacing the wrong shared ID regex globally would be a contract regression and was not done.

## Gate status and limits

- `backend/.venv/bin/python -m pytest backend/tests/identity_access backend/tests/integration/identity_access -q --tb=short`: **124 passed in 150.35 s**, exit 0, including real elapsed 60-second session/token touch behavior. This M01 run is not a P01 HTTP or full-backend run.
- M01-scoped mypy: **Passed**, 37 source/test files. Changed-file Ruff lint and format: **Passed**, six files. Shared import-boundary checker: initially **Failed, 3 exact same-M01 symbol imports**; root added only the exact `valid_correlation_id` symbol allowance with its own Red/Green test; `python3 tooling/foundation/check_boundaries.py .` then **PASS, zero violations**.
- `AUTO-DOCS-CHECK`: **Passed**, 198 Markdown files. `AUTO-PLAN-CHECK`: **Passed** synchronized plans. `git diff --check`: **Passed**.
- Canonical `AUTO-QUALITY`: **Failed** at whole-checkout Ruff (8 findings in concurrently edited P01/composition/API-test files, none in M01); it stopped before later gates. It must be rerun after P01 work stabilizes and is **not** claimed passed here.
- P01 real HTTP request propagation, generated client, real browser, and full M2 exit gate: **Not Run** by this M01-only repair.

No mock, fake, stub, emulator, in-memory database, seeded credential state, fake clock, or provider account was used.

Independent specification review reran the three focused pure/real-SQLite tests and 175 boundary tests, plus the checker with zero violations; it accepted the exact grammar and unchanged resource-ID checks. Independent QA reran the three focused tests (0.58 s) and checker, inspected real migration/bootstrap/Argon2 use and unchanged audit correlation, and accepted the narrow repair. Both reviews kept whole-checkout quality failed and HTTP/browser gates Not Run.
