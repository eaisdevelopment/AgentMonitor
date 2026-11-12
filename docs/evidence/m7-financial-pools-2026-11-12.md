# M7 owner-managed financial pools

Status: implementation in progress; not installed, no full M7 acceptance.
Requirements: FR-ORG-003, FR-ACC-001..004/006, FR-BUDGET-004/005/006.
Tickets: M7-T002/T004/T010/T012/T014; acceptance M7-A01/A02/A07/A08/A10.
Owners: M02 metadata, M05 calculations, P01/P02 transport/UI, root integration.

## Contract and schema impact

Additive CTR-REG-014 1.5.0 preserves existing billing 1.4.0 types. New typed
owner association/attribution commands, source lineage, bounded choices and
revisioned snapshot support known/shared pools without guessing identity.
The root allocates M02 schema v1_0734 after0733; installation is not authorized
by a schema definition alone and requires the existing actual migration/recovery
checks. No new dependency, license, secret handling or provider behavior.

## Test-first evidence

- Initial pure scope/snapshot tests: three failures,
  `financial_pool_scope_contract_missing`, before their production types.
- Current pure scope/snapshot checks: three passed.
- Owner command Red: `financial_pool_owner_commands_missing`, one failed/three
  passed before adding mutation/configuration contracts.
- Green: `PYTHONPATH=backend/src:. backend/.venv/bin/pytest -c
  backend/pyproject.toml -q --tb=short -p tools.automation.pytest_no_skip
  backend/tests/contracts/test_registry_financial.py`: four passed. The actual
  interpreter is the shared repository backend virtualenv; no external I/O.

Owner controls, financial aggregation and installed verification remain
unfinished. The API/storage evidence below supersedes the earlier Not Run state. No owner
account/group/key configuration is changed by this implementation work. Pending
billing access affects its monetary live lane only; independent work continues.


## Registry and API integration

Real isolated owner metadata tests passed: twelve storage cases plus one
end-to-end IAM/HTTP workflow. Five pure contract tests passed; combined result
18 passed in14.37s. Storage Red covered missing schema/module and later exact
event aggregate identity. API Red was404 financial_pool_http_missing; Green
exercises create/join/unlink, primary-group editing, exact replay, changed
request rejection, stale revisions, CSRF/authentication and credential-field
rejection. Unknown binding authority remains unassignable. These records are
owner metadata, never provider responses or seeded financial telemetry.

Generated OpenAPI/TypeScript has91 compatible operations. Generation first
failed operation_policy_mismatch until the explicit four-operation policy was
added. Boundary check initially identified an unsupported internal type import
and unpublished supporting port symbols; the type annotation and published
symbol catalog were corrected. Boundary check passed with zero violations.
Strict mypy passed the router, schemas and contract; M02 repository strict mypy
and Ruff passed. This does not establish built-browser usability.

Canonical M7 registry_metadata now includes these tests; it does not close the
full registry or monetary provider lanes. CTR-REG-014 1.5.0 adoption/snapshot
are synchronized. The existing metadata policy mutation test was found stale
at78 operations; explicit reviewed expectations now cover91, including the
previously added nine M7 endpoints and these four pool endpoints.

Financial rehearsal Red: m7_setup_schema_unavailable because the controller
still targeted0733. The bounded controller now selects the actual installed
predecessor0733 and candidate0734; genuine isolated rehearsal passed including
reopening its private0733 backup. No installed upgrade was executed.

Affected files include M02 migration/catalog/compatibility and repository,
registry contract, P01 schemas/router/ports/composition/problems, generated
OpenAPI/client and policy checks, isolated contract/storage/HTTP tests, canonical
M7 metadata and migration/preparation routines, and contract synchronization
documents. No dependency/license/provider/profile/credential custody change.
Owner configuration, installed service and public repository remain untouched.
Further work: complete the owner UI, pool-aware query/totals, source-scope
editing and genuine cloud/rotation evidence, then actual installed verification.


## Offline recovery and final local checks

The canonical migration policy initially rejected the new real catalog with
`migration_catalog_not_m4`. Its reviewed source/target chain now admits0733 to
0734. The three actual migration suites passed60 tests in91.55s, including
private pre-migration backup hash/integrity, reopening unchanged0733 after
upgrade, preserved prior table counts, empty new pool tables and idempotent
retry without an additional backup. Installed migration remains Not Run.

After type-only test refactoring, five pure contracts plus the real HTTP flow
passed6 tests in4.48s; M02 storage passed12 in9.56s. The explicit API policy
mutation/shape suite passed6 tests in149.69s. No test skip is counted as pass.

AUTO-QUALITY passed on12 November00:03:55UTC: strict mypy692 files, Ruff753
files, zero boundary violations, compatible91-operation generated API/client,
frontend typecheck and production build, and locked dependency metadata. Initial
quality failures were import ordering and missing test annotations; corrected
without ignores or disabling checks. This is local quality, not hosted CI,
provider evidence or full release security acceptance.

AUTO-M7-PLAN-CHECK passed16 tickets/five stories/ten acceptance items;
AUTO-PLAN-CHECK synchronized passed; AUTO-DOCS-CHECK passed382 Markdown files;
local AUTO-GIT-PREFLIGHT and git diff --check passed. Public publication and
installed UI are not claimed by these checks.

Canonical M7 registry_metadata lane passed58 tests in33.94s after integration.
This covers real owner metadata/nonsecret lifecycle only; it does not claim
credential entry, provider access, owner controls or full M7 acceptance.
