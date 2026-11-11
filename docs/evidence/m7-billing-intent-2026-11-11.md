# M7 billing intent persistence evidence

- Evidence ID: M7-REG-INTENT-2026-11-11.
- Module: M02 Registry, M7-T002; focused execution plan 1.1.0.
- Requirements: FR-ACC-001/002/004/006, FR-BUDGET-001/006; acceptance contribution M7-A01, AC-TEST-001/003/006.
- Authority: [M7 implementation authority](m7-implementation-authority-2026-11-11.md).
- Contracts: CTR-REG-002 V1 additive nullable `initial_connection_purpose`; existing account command semantics and credential/monitoring boundaries remain intact.
- Schema: centrally allocated M02 `v1_0730` after `v1_0720`; one nullable checked account column. No provider telemetry migration or default value.
- Baseline: `a91424881504389264362e8763c2fc1d79866502` plus concurrent authorized M7 changes in `m7-api-budgets`.
- State: Narrow persistence increment has Green evidence; full T002 remains intermediate because billing status/enrollment are unfinished. No deployed change claimed.

## Tests and Red

The test file is `backend/tests/integration/registry/test_billing_account_intent.py`.
It uses real file-backed SQLite, the real migration chain, production registry
commands and the code-owned Claude capability manifest. Created account labels
are administrator metadata, not provider identities or telemetry.

At `2026-11-11 14:46:48 UTC`, before migration/application/repository edits:

```bash
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -c backend/pyproject.toml --import-mode=importlib -q --tb=short -p no:cacheprovider backend/tests/integration/registry/test_billing_account_intent.py::test_existing_account_creation_has_nullable_intent_storage
```

Result: exit **1**, **1 failed in 2.39s**. The production repository successfully
created a pending metadata account, then the real schema assertion failed:

```text
AssertionError: Registered accounts need nullable persisted API setup intent
```

The actual migrated `reg_account` table lacked `initial_connection_purpose`.
This is a missing persistence behavior, not unavailable provider access or a
test setup failure. The earlier [real HTTP Red](m7-billing-enrollment-http-2026-11-11.md)
separately records rejection of API creation intent.

After root admitted the migration and the application command accepted the
typed optional field, the full new test file ran at `2026-11-11 14:50:06 UTC`
using the same command prefix and this file selection:

```text
backend/tests/integration/registry/test_billing_account_intent.py
```

Result before repository edits: exit **1**, **2 failed, 5 passed in 2.45s**.
The meaningful repository failures were:

```text
assert None == 'api'
Failed: DID NOT RAISE RegistryCommandConflictV1
```

The production repository discarded the valid command's API intent, and a
changed-purpose retry reused the previous request identity. No invented
provider fact or mocked collaborator was needed to expose either defect.

## Green and refactor

Minimum production change: validate the optional command value, persist/read
the nullable field, and include it in the creation fingerprint only when
non-null. Existing null/omitted commands retain their prior receipt grammar.
API intent leaves lifecycle pending, identity unresolved and monitoring disabled;
it creates no monitoring profile or resource. The database rejects values other
than null or `api`.

At `2026-11-11 14:50:37 UTC`, the new file passed: exit **0**, **7 passed in
2.19s**. Coverage includes reopen/get/list, exact replay, conflicting intent in
both directions, historical null fingerprint compatibility, nullable storage,
CHECK enforcement, integrity/FK checks and four pure invalid-input cases.

The first broadened regression attempt found a concurrent P01 mapping defect:
organization creation returned HTTP 500. Result: **5 failed, 6 passed in
17.13s**. Root corrected its `_organization`/`_account` response mapping; no
P01 file was edited by this task.

At `2026-11-11 14:52:34 UTC`, post-correction and post-refactor verification ran:

```bash
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -c backend/pyproject.toml --import-mode=importlib -q --tb=short -p no:cacheprovider backend/tests/integration/registry/test_billing_account_intent.py backend/tests/integration/registry/test_registry_persistence.py backend/tests/integration/api/test_account_admin_routes.py backend/tests/integration/api/test_organization_routes.py
```

Result: exit **0**, **18 passed in 22.67s**. The checks exercise real migrated
SQLite, production registry applications, real IAM and loopback HTTP. Existing
account and organization administration remain passing within this test scope.

Scoped Ruff check/format with explicit `--config backend/pyproject.toml` passed
for both changed production files, the new migration and the new test. Scoped
strict mypy passed for the two production files and test, using the admitted
interpreter's mypy, `MYPYPATH=backend/src`, `--config-file backend/pyproject.toml`,
`--explicit-package-bases` and `--follow-imports=silent`. Initial import-order
and negative-test typing findings were corrected; these scoped checks do not
substitute for root's full quality gate.

The earlier HTTP enrollment test was also rerun. It now passes creation and
reaches the next meaningful Red:

```text
AssertionError: The created account must expose safe billing setup status; received HTTP 404
assert 404 == 200
```

That run exited **1**, **1 failed, 1 passed in 4.99s**. No placeholder billing
status route was added. Full billing status/capability verification, built
browser, live credential/provider flow, installed migration and recovery remain
**Not Run** here. The fresh-chain/null-default evidence does not claim an
installed prior-schema account upgrade has passed.

## Security, privacy and impact

No credential, operator `.env`, default profile, private owner database or
installed service was accessed. Only isolated test databases are created.
The invalid-purpose policy tests use constructed values without I/O; database
tests operate only on real command-created administrator metadata. No fake,
mock, recorded provider response, seeded telemetry, test-only production path,
new dependency or license change is involved.

Allowed file scope is the registry application command, registry SQLite
repository, new `v1_0730_m02_billing_intent.py`, the new integration test and this
evidence. Root owns shared DTOs, migration catalog/compatibility admission and
API wiring. Existing migrations remain unchanged. Upgrade/recovery operations
remain root-owned and require their own real verification.
