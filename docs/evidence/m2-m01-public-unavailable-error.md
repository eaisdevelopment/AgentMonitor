# M01 public repository-unavailable error seam — Story 4 dependency evidence

- Status: **Accepted as a narrow Story 4 dependency repair** after root specification review and independent QA review. This is not Story 4 or M2 acceptance.
- Owner/date: M01 worker, 2026-09-20.
- Requirement/acceptance: approved `iam_repository_unavailable` 503 mapping in M01 plan §4 and M2 contract freeze §5; `NFR-SEC-001`; Story 4 P01/M01 API-boundary dependency. This does not satisfy a P01 HTTP test.
- Contract impact: compatible additive M01 V1 application error `IamRepositoryUnavailableV1`, fixed code `iam_repository_unavailable`. Existing adapter-private `IdentityAccessRepositoryErrorV1` now subclasses it; its name, message, and all existing adapter callers remain compatible. No `CTR-IAM-001..008` DTO, schema, migration, OpenAPI, generated client, dependency, or provider change.

## Red → Green over a real file

The test uses the production Alembic migration and `BootstrapAdministratorV1` fixture with a real Argon2 owner credential, then calls the published `GetIamInitializationStateV1` use case. It verifies the compatible file starts initialized, temporarily changes **only that isolated test DB** from owner-only `0600` to inaccessible `0000`, expects the public error, restores the exact prior mode in `finally`, and verifies initialization is still readable. This is a real filesystem/SQLite-policy availability fault, not a fake repository or constructed result. No DB path, credential, PHC, or SQL error text appears in the assertion or evidence.

| Stage | Exact command | Sanitized result |
|---|---|---|
| Red: public type absent | `backend/.venv/bin/python -m pytest backend/tests/integration/identity_access/test_public_repository_error.py -q --tb=short` | Exit 2; `ImportError: cannot import name 'IamRepositoryUnavailableV1'`. |
| Red: real failure escapes as private adapter type | Same command after only the public class was added | Exit 1; real file-mode denial raised `IdentityAccessRepositoryErrorV1: iam_repository_unavailable`, not the public application type. |
| Green: private subtype conforms to published type | Same command after adapter inheritance change | Exit 0; 1 passed in 0.14 s. |

The new test asserts the exact safe public message and that normal initialized state works again after permission restoration. No mock, fake, stub, emulator, in-memory DB, seeded administrator, test-only production branch, fake time, or provider account was used.

## Gate status and limits

- `backend/.venv/bin/python -m pytest backend/tests/identity_access backend/tests/integration/identity_access -q --tb=short`: **121 passed in 150.07 s**, exit 0, including real 60-second browser/token touch and the new real permission failure.
- Changed-file Ruff lint and format: **Passed** (3 files). M01-scoped mypy: **Passed**, 11 source files. The root-owned checker now admits the exact public same-M01 error import; `python3 tooling/foundation/check_boundaries.py .`: **PASS, zero violations**.
- `AUTO-DOCS-CHECK`: **Passed**, 197 Markdown files. The worker-time `AUTO-PLAN-CHECK` passed before the root's exact P01 `CTR-IAM-008` rebind; on the final shared checkout the synchronized planning validator passed after reviewed snapshot binding. `git diff --check`: **Passed**.
- Whole-checkout mypy: **Failed**, 29 errors in four concurrently edited P01 API/test files, none in M01. Canonical `AUTO-QUALITY`: **Failed** at Ruff with 31 concurrent P01 source/test lint findings before reaching mypy. These are not reported as Passed; P01/root owners must resolve and rerun the full gate before M2 completion. This M01-only handoff is not a milestone completion claim.

The shared boundary checker initially failed on the new exact M01 error import plus a concurrent P01 declaration; root-owned rule/declaration work made the checker green without a broad exemption. Actual P01 503 mapping over a real loopback FastAPI server, OpenAPI/client behavior, browser, and live provider/account tests remain **Not Run** under this M01-only change.

Independent QA reran the real-file test (1 passed in 0.14 s) and the complete 174-test boundary suite (3.65 s), inspected the production bootstrap fixture and reversible isolated chmod fault, and accepted this exact additive error seam. Root separately reviewed the public-type/subtype layering and approved P01 catch-by-application-type only. Concurrent P01 work still makes whole-checkout quality non-green; no global gate is claimed here.
