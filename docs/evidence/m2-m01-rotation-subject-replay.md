# M01 rotation receipt versus ETag subject — Story 4 dependency evidence

- Status: **Accepted M01 rotation-subject slice** after independent specification and QA reviews; not Story 4 or M2 acceptance.
- Owner/date: M01 worker, 2026-09-20.
- Requirement/acceptance: `FR-IAM-004`, `M01-DB-010/011`, frozen M2 one-time-secret receipt ordering and `If-Match` precondition semantics; P01 real-socket acceptance is separately owned.
- Contract impact: compatible optional keyword-only `presented_target_id: OpaqueIdV1 | None = None` on `RotateApiTokenV1`, forwarded as an optional narrow repository string. Existing non-HTTP callers and CTR-IAM-006 DTO/result codes remain unchanged. No database/migration, OpenAPI/generated-client, audit vocabulary, dependency, provider, or profile change.

## Genuine Red → Green

The real-file SQLite test uses production Alembic migration, Argon2 bootstrap/login, a real browser-session caller, and two actually issued token IDs. A fresh wrong-subject attempt against the still-active target must return `precondition_failed` without changing its persisted token rows or audit count. It then rotates that target with the matching subject. A committed same-key/same-metadata replay using the other token's valid subject must return only `one_time_secret_not_replayable` safe ID/version/state. The same key with changed safe metadata must still return `idempotency_key_reused`. A different fresh key with that wrong subject must also return `precondition_failed` before target expiry/terminal/rotation mutation. The test compares persisted safe token IDs/versions/terminal markers and audit count before and after denied/replayed calls; it never compares or prints bearer plaintext.

| Stage | Exact command | Sanitized result |
|---|---|---|
| Red: typed subject port absent | `backend/.venv/bin/python -m pytest backend/tests/integration/identity_access/test_api_tokens.py -q -k rotation_replay_precedes_wrong_subject_but_new_key_cannot_mutate --tb=short` | Exit 1; 1 failed, 21 deselected in 0.40 s: `RotateApiTokenV1.__call__()` rejected the `presented_target_id` keyword. |
| Green: optional typed port and post-receipt subject check | Same command after M01 change and persisted-state assertion | Exit 0; 1 passed, 21 deselected in 0.37 s. |

The adapter's existing transaction still authenticates the current caller and checks target administrator/scope authority before receipt disclosure. It computes the same canonical request fingerprint from target path/version and safe metadata; the presented ETag subject is **not** a receipt discriminator. Only after a missing receipt does it compare the optional subject to the target path and reject mismatch. Thus a new request cannot rotate a different target, while a committed one-time issue is never reconstructed or replayed.

## Gate status and limits

- `backend/.venv/bin/python -m pytest backend/tests/identity_access backend/tests/integration/identity_access -q --tb=short`: **132 passed in 211.88 s** on the exact final test checkout, exit 0, including real elapsed session/token touch and the new active-target snapshot case. An earlier interim run also passed 132 in 211.52 s before final test-only strengthening; the 211.88-second run is the gate evidence.
- M01-scoped mypy: **Passed**, 37 source/test files. Changed-file Ruff lint/format: **Passed**, three files (format initially failed at two newly edited test lines, then corrected). Import-boundary checker: **PASS, zero violations**. `AUTO-DOCS-CHECK`: **Passed**, 204 Markdown files; `AUTO-PLAN-CHECK`: **Passed**, synchronized plans; `git diff --check`: **Passed**.
- Canonical whole-checkout `AUTO-QUALITY`: initially **Failed** at one concurrently edited P01 test formatting location; after the API owner fixed it, rerun **PASSED** (Ruff 76 formatted, mypy 72 source files, boundary zero, OpenAPI/client compatibility, frontend typecheck/build, lock check). Hosted GitLab, live provider, platform, full secret/SAST/vulnerability scans, frozen install, and release SBOM/notices remain outside this local quality result.
- P01 real-socket wrong-subject replay/fresh-request mapping, browser, and full M2 exit gate: **Not Run** by this M01-only slice. The separate real ≥1-hour token-expiry test passed one case in 3601.23 s (root-owned Story 3 evidence); 24-hour receipt reclaim, 365-day token/retention boundaries, and backward-clock rollback remain **Not Run**.

No fake, mock, stub, emulator, direct seeded token state, altered clock, new secret artifact, or external account was used.

Independent specification review reran the focused real SQLite test (1 passed) and accepted the additive port/receipt-order semantics. Independent QA reran the same real SQLite test (1 passed, 21 deselected/0.28 s) plus the integrated P01 real-Uvicorn replay/problem subset (3 passed, 21 deselected/3.37 s) and the available API+M1 suite (60 passed, one documentation test deliberately deselected/46.28 s). Those HTTP results belong to Story 4 and do not accept its local Swagger/ReDoc/browser gate. The final exact-checkout M01 suite remains the 132-pass/211.88-second result above; the 0.37-second first Green is not represented as that final gate.
