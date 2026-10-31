# M01 token active-version precondition — Story 4 dependency evidence

- Status: **Accepted M01 token slice** after independent specification and QA reviews; not Story 4 or M2 acceptance.
- Owner/date: M01 worker, 2026-09-20.
- Requirement/acceptance: `FR-IAM-004`, `M01-DB-010`, `M01-HTTP-016`, frozen M2 `If-Match` outcome table (412 `precondition_failed` for stale active conditional mutation; 409 `credential_state_conflict` for terminal state). P01 real-socket acceptance remains separately owned.
- Contract impact: compatible additive code `precondition_failed` in `ApiTokenMutationOutcomeV1` (`CTR-IAM-006` V1) with no resource metadata. The existing outcome class, one-time issue type, stored token schema, event vocabulary, idempotency receipt, OpenAPI, generated client, and provider boundaries are otherwise unchanged. Root owns the M01 Draft-plan reconciliation to the approved M2 freeze.

## Genuine Red → Green

The new integration test starts with the production Alembic migration and real Argon2 administrator/bootstrap/session ports, creates an actual token, and resolves its actual bearer. That first real resolve advances the persisted active token version. A browser administrator then attempts rotation or revocation using the now-stale issued version. The test requires `precondition_failed`, no resource metadata, no token-state or audit transition, and subsequent success with the current version. It also checks a rotated target still conflicts and repeated authorized explicit revoke remains idempotently successful; a separate real test covers rotate-after-explicit-revoke conflict. No DB version/timestamp seeding, fake clock, mock repository, or synthetic token state is used.

| Stage | Exact command | Sanitized result |
|---|---|---|
| Red: active stale version conflated with terminal state | `backend/.venv/bin/python -m pytest backend/tests/integration/identity_access/test_api_tokens.py -q -k 'stale_active_token_version or rotated_terminal_target' --tb=short` | Exit 1; 2 failed, 1 passed, 17 deselected in 0.67 s. Both real active stale mutations returned `credential_state_conflict` instead of `precondition_failed`; rotated-target control passed. |
| Green: active version split and additive CTR-IAM-006 code | `backend/.venv/bin/python -m pytest backend/tests/identity_access/test_token_contract.py backend/tests/integration/identity_access/test_api_tokens.py -q -k 'stale_active_token_version or rotated_terminal_target or stale_active_precondition' --tb=short` | Exit 0; 4 passed, 21 deselected in 0.64 s. |
| Regression: explicit revoked-target control added | `backend/.venv/bin/python -m pytest backend/tests/identity_access/test_token_contract.py backend/tests/integration/identity_access/test_api_tokens.py -q -k 'stale_active_token_version or terminal_target or stale_active_precondition' --tb=short` | Exit 0; 5 passed, 21 deselected in 0.92 s. |

The terminal check remains before the active-version check. A completed one-time rotation receipt is still checked first, so an authenticated replay does not become a stale-precondition response. The explicitly revoked target's terminal-idempotent revoke branch still precedes its version check. Caller authentication, CSRF, bearer target attenuation, and atomic transaction boundaries are unchanged.

## Gate status and limits

- `backend/.venv/bin/python -m pytest backend/tests/identity_access backend/tests/integration/identity_access -q --tb=short`: **129 passed in 150.82 s**, exit 0, including real elapsed 60-second session/token touch tests. Post-format focused rerun: **5 passed, 21 deselected in 0.95 s**.
- Changed-file Ruff lint/format: initially **Failed** only on two newly edited test formatting locations; corrected with the admitted formatter and then **Passed** on all four changed Python files. M01-scoped mypy: **Passed**, 31 source/test files. Import-boundary checker: **PASS, zero violations**.
- `AUTO-DOCS-CHECK`: **Passed**, 200 Markdown files. `AUTO-PLAN-CHECK`: **Passed**, synchronized plans. `git diff --check`: **Passed**.
- Canonical whole-checkout `AUTO-QUALITY`: **Failed** at seven Ruff import findings in concurrently edited P01/composition/API-test files, none in M01; it stopped before subsequent stages. It must rerun after those files stabilize and is **not** claimed passed here.
- Real P01 HTTP 412 mapping, browser, actual one-hour token expiry, and full M2 gate: **Not Run** in this M01-only slice. A real ≥1-hour token-expiry verification remains separately documented in Story 3 evidence and is not claimed here.

No provider account, profile, credential plaintext artifact, external deployment, new dependency, or migration was touched.

Independent specification and QA reviewers each reran the focused real SQLite/pure tests (5 passed). Both accepted the token-only semantic split and its evidence. The M01/P01 Draft-plan reconciliation remains provisional until the separate stale active-session outcome is repaired and rebound; the token slice is committed independently so P01 can consume its exact published outcome.
