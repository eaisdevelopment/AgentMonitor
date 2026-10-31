# M01 active-session precondition — Story 4 dependency evidence

- Status: **Accepted M01 session slice** after independent specification and QA reviews; not Story 4 or M2 acceptance.
- Owner/date: M01 worker, 2026-09-20.
- Requirement/acceptance: `FR-IAM-003`, `M01-DB-003..005`, `M01-HTTP-008/010`, frozen M2 `If-Match` outcome table (412 `precondition_failed` for stale active conditional mutations; 401 for invalid logout actor; safe idempotent target revoke; 409 for completed one-time password receipt).
- Contract impact: compatible additive `precondition_failed` code in `SessionMutationOutcomeV1` (`CTR-IAM-005` V1), without affected rows or retry metadata. No session/CSRF issue shape, database schema/migration, audit vocabulary, OpenAPI, generated client, dependency, provider, or profile change. Root owns synchronized plan rebind and P01 HTTP mapping.

## Genuine Red → Green

The integration test uses production Alembic migration, real Argon2 administrator/bootstrap and browser-session ports, a file-backed owner-only SQLite database, and actual elapsed wall-clock time beyond the 60-second touch coalescing threshold. Three genuine browser sessions are resolved after that interval, advancing their persisted active versions through the normal production path. The test then presents each issued (now stale) version to logout, target-session revoke, and password change with current CSRF proof. It requires three `precondition_failed` outcomes, no administrator/session-count/audit transition, and subsequent success using current versions. It also checks terminal logout authentication and password-change replay precedence. No fake clock, test-only threshold, direct DB version/timestamp rewrite, seeded credential row, mock, or emulator is used.

| Stage | Exact command | Sanitized result |
|---|---|---|
| Red: active version conflated with state conflict | `backend/.venv/bin/python -m pytest backend/tests/integration/identity_access/test_session_management.py -q -k real_touched_active_sessions_distinguish_stale_preconditions --tb=short` | Exit 1; 1 failed, 5 deselected in 60.56 s. All three active stale operations returned `credential_state_conflict`; expected `precondition_failed`. |
| Green: exact CTR-IAM-005 and M01 adapter distinction | Same command after the minimum production change | Exit 0; 1 passed, 5 deselected in 60.64 s. |
| Fast contract and existing target-revoke regression | `backend/.venv/bin/python -m pytest backend/tests/identity_access/test_session_contract.py backend/tests/integration/identity_access/test_session_management.py -q -k 'active_session_precondition or target_revoke_rechecks_actor_csrf_and_target_version_atomically' --tb=short` | Exit 0; 2 passed, 22 deselected in 0.35 s. |

The session adapter changes only three active-version checks after current actor authentication/CSRF and, for password change, completed receipt replay. It does not alter terminal authentication denial, target-revoke idempotency, Argon2 policy, throttle, expiry, or audit payloads.

## Gate status and limits

- `backend/.venv/bin/python -m pytest backend/tests/identity_access backend/tests/integration/identity_access -q --tb=short`: **131 passed in 211.49 s**, exit 0, including this new 60-second case and the existing real session/token touch cases. The final test also compares persisted session IDs, versions, terminal markers, and audit count before/after stale requests, then checks current-version success, terminal logout, repeated target-revoke idempotency, and password receipt replay.
- M01-scoped mypy: **Passed**, 31 source/test files. Changed-file Ruff lint: **Passed**; format initially **Failed** only on the new test, corrected with the admitted formatter and then **Passed** (four changed Python files). Import-boundary checker: **PASS, zero violations**.
- `AUTO-DOCS-CHECK`: **Passed**, 203 Markdown files. `AUTO-PLAN-CHECK`: **Passed** synchronized plans. `git diff --check`: **Passed**.
- Canonical whole-checkout `AUTO-QUALITY`: **Failed** at eight Ruff import-order findings in concurrently edited P01/composition/API tests, none in M01. It stopped before later stages and is **not** claimed passed here.
- Real P01 HTTP 412 mapping, browser, actual 30-minute idle/12-hour absolute expiry, and full M2 exit gate: **Not Run** in this M01-only slice.

No secret values or PHCs are printed or stored in evidence. No new dependency, provider state, migration, or external resource is involved.

Independent specification review reran focused contract plus real 60-second SQLite integration tests (3 passed, 21 deselected); independent QA reran the real elapsed test (1 passed, 5 deselected) and pure contract test (1 passed, 17 deselected). Both accepted this bounded M01 change. The integrated P01 real-HTTP 412 checks were independently rerun later by QA (2 passed, 20 deselected), but remain a separate Story 4 gate. Root's M01/P01 planning-snapshot rebind still requires its final coherence review.
