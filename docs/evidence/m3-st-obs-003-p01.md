# M3 ST-OBS-003 P01 API increment evidence

- Evidence ID: `M3-ST-OBS-003-P01`
- Module/plan/increment: `P01` / M3 Task 6 authenticated observation API
- Requirements/acceptance IDs: `AC-V1-001/002/005/006/007/008`,
  `AC-UI-002/003/006`, `AC-PROC-001..005`, `AC-HIST-001`,
  `AC-TEST-001..006`, and applicable `API-HTTP`/`API-OAPI` scenarios
- Contract versions: compatible additions to `CTR-API-001..003 v1`,
  `CTR-COMMON-007 v1`, `CTR-REG-001..007 v1`, `CTR-PROV-002 v1`,
  `CTR-COL-001/002/005 v1`, `CTR-CAP-001/003 v1`, and
  `CTR-RUN-001..003/007 v1`
- Generated OpenAPI SHA-256:
  `74e48f5066dc76e7d4b7946a4411b00ccf94a5504db7dbca1ac96016ad2acfb7`
- Recorder/date: P01 implementation agent, 2026-09-23 Europe/London

## Test inventory and status

| Test/scenario | Layer | Real dependencies | Status | Notes |
|---|---|---|---|---|
| `test_observation_http.py` | T2/T3 | migrated file SQLite, production FastAPI/Uvicorn loopback, real IAM cookie/bearer credentials | Passed | Nine exact read operations, auth/scope policy, safe errors, manifest truth, bounded inputs, empty/unavailable truth |
| `test_capacity_schema_chain.py` | T2 | migrated file SQLite and production M05 repository | Passed | Direct bounded `page_account_quota_windows` invocation and oversize rejection; no rows invented |
| OpenAPI generator `--write` and `--check` | contract | production schema factory and generated TypeScript compiler | Passed | Compatible 22-operation contract; stable SHA above |
| strict mypy | static | canonical admitted Python toolchain | Passed | 170 source files, zero issues |
| boundary checker and boundary pytest | static | real checkout ownership/import graph | Passed | Zero violations; 180 tests passed |
| populated M05 quota page, second page, and M05-bound cursor | T2/T3/T5 | fresh real Claude Task 4 quota observations | Blocked | Task 4 has no live quota rows; constructed/seeded telemetry is forbidden |
| complete frozen P01 filter/sort profiles | contract/module | producer fields and owning-module query contracts | Deferred | Owner approved M3 narrowing to `provider_key` where implemented plus fixed producer ordering; remaining filters/sorts return to owning module plans |

## Red evidence

Before the nine production routes existed:

```text
backend/.venv/bin/python -m pytest \
  backend/tests/integration/api/test_observation_http.py -q --tb=short
# 13 failed in 8.56s
```

The failures were the expected missing/provisional route behavior. A later
strict transport test demonstrated that an unknown filter was incorrectly
accepted:

```text
backend/.venv/bin/python -m pytest \
  backend/tests/integration/api/test_observation_http.py::test_observation_permissions_and_bounded_lists \
  -q --tb=short
# failed: /api/v1/accounts?bogus=1 returned 200, expected 400
```

Independent strict typing review also produced a behavioral contract Red:
producer runtime/capacity states were not all representable by wire enums and
the exact canonical command reported 17 errors across six production files.

Post-review Reds then caught three transport defects before their fixes:

```text
# safe problem catalog: intended 404/503 collapsed to internal_error 500
# provider selector: missing maxLength/pattern and 65-character key returned 404
# account-scoped sessions: OpenAPI omitted account_id and HTTP returned invalid_filter
```

The safe-problem focused run failed all three catalog/loopback assertions; the
selector run failed both OpenAPI and real HTTP assertions; and the session run
failed both OpenAPI and real HTTP assertions for those exact reasons.
Independent review then added the already-working
`observation_repository_unavailable` 503 to the same regression matrix. That
coverage-only addition was Green on its first run because its production
catalog entry predated the test; no historical Red is claimed for it.

## Green and refactor evidence

```text
backend/.venv/bin/python -m pytest \
  backend/tests/integration/api/test_observation_http.py -q --tb=short
# 13 passed in 9.48s

backend/.venv/bin/python -m pytest \
  backend/tests/integration/capacity/test_capacity_schema_chain.py -q --tb=short
# 4 passed in 1.39s

MYPYPATH=backend/src backend/.venv/bin/mypy \
  --config-file backend/pyproject.toml --explicit-package-bases \
  backend/src/agentmonitor backend/tests tooling/provider_system/manifest_schema.py
# Success: no issues found in 170 source files

backend/.venv/bin/python tooling/foundation/check_boundaries.py .
# boundaries: PASS (0 violations)

backend/.venv/bin/python -m pytest \
  backend/tests/foundation/test_contract_boundaries.py -q --tb=short
# 180 passed in 4.50s

backend/.venv/bin/python tooling/foundation/openapi_client.py --write
backend/.venv/bin/python tooling/foundation/openapi_client.py --check
# both passed; compatibility=compatible; operations=22; SHA shown above

backend/.venv/bin/python -m pytest \
  backend/tests/api/test_transport_policy.py::test_observation_problem_codes_preserve_safe_status \
  backend/tests/integration/api/test_observation_http.py \
  backend/tests/runtime_observation/integration/test_real_linux_commit.py \
  -q --tb=short
# 20 passed in 12.07s

backend/.venv/bin/python -m pytest \
  backend/tests/api/test_transport_policy.py::test_observation_problem_codes_preserve_safe_status \
  backend/tests/integration/api/test_observation_http.py -q --tb=short
# 18 passed in 11.31s; includes repository-unavailable 503 regression
```

The earlier combined API/OpenAPI/boundary/capacity/runtime refactor suite
passed `204` tests. The final post-review API/OpenAPI/boundary/capacity/runtime/
transport/token suite passed `217` tests in `23.63s`. `AUTO-QUALITY` passed the
local static, formatting, boundary, generated-artifact, lockfile, TypeScript,
and production-build checks; `AUTO-DOCS-CHECK` passed all `227` Markdown files.

## Contract and scope decisions

- Each route maps one-to-one to its named producer application/query port.
- All routes are read-only GET operations using `cookie_or_bearer`; account and
  installation queries require `read:accounts`, capabilities require
  `read:status`, and collection/capacity/runtime require `read:telemetry`.
- Producer availability, freshness, provenance, presence, lifecycle, run, and
  correlation enums are preserved in OpenAPI and generated TypeScript. The API
  does not turn unknown values into zero or synthesize provider/account truth.
- The owner explicitly accepted the M3 vertical-slice query narrowing:
  `provider_key`, the required account-scoped session filter, and fixed
  producer-owned ordering. Unsupported filters were not invented. Full P01
  filter/sort profiles remain follow-up work for the owning modules.
- Signed-cursor tamper, query binding, restart invalidation, and populated page
  mechanics are already exercised by the shared P01 cursor over real IAM
  file-SQLite rows. That evidence is not claimed as populated M05 proof.

## Real-system and integrity declaration

The passed API tests used real migrations, real temporary file-backed SQLite,
production IAM/bootstrap/composition, a real loopback Uvicorn server, real HTTP
cookies and bearer tokens, and the accepted Claude capability manifest. No
mock, fake, stub, emulator, response recording, demo account, seeded telemetry,
placeholder value, hardcoded passing branch, disabled assertion, or test-only
production path was used.

No provider profile or running agent was modified. No prompt, response, source
content, environment, credential value, provider payload, or personal account
identifier was read or retained. This increment adds no dependency or database
migration and makes no license change.

## Conclusion and residual gaps

The authenticated P01 observation API, OpenAPI contract, and generated client
foundation are locally Passed for truthful empty/unavailable states. The exact
populated Claude account/quota/runtime milestone vertical remains Blocked by the
upstream live Task 3/4/5 evidence and must not be inferred from this result.

## 2026-09-24 populated API supplement

The earlier Blocked conclusion is superseded for the M3 Claude lane. Compatible
V1 operations `capacity_list_history_v1` and `runtime_get_session_tree_v1`
raised the generated contract to 25 operations. Real persisted Claude history
passed direct repository and authenticated loopback pagination/no-write checks;
the real same-account session tree passed database reopen and authenticated
transport checks. The production browser received 200 responses from both new
operations. OpenAPI/client generation remained compatible with SHA-256
`aae7bbddef229a5f61ddfbe8bb388af1736467f759647770dcd51c2e6f1ca933`.
