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

## Owner controls and pool-aware Overview increment

Scope: existing T002/T004/T010/T011/T012 and their T003/T014 verification,
FR-BUDGET-001/002/005, FR-ORG-003, AC-UI-005 and AC-TEST-001/003.
M02 remains the metadata authority (CTR-REG-0141.5.0). M05 publishes optional
pool/access-path and contributing-report fields in CTR-CAP-0062.6.0, consumed
through P01/generated client by P02. The additive schema remains0734; no new
dependency, credential mechanism, provider mutation or migration is introduced
by the UI/query changes.

The account page has collapsed owner controls to create/join/unlink a billing
pool and change its primary dashboard organization. All organization/pool
pages are read before presenting choices. Mutation revision/idempotency is
retained across an uncertain result and reload; retries are explicit. Existing
Ollama self/team metadata controls use its cloud resources, without creating
an Anthropic/OpenAI-style connection or claiming team usage collection exists.

Overview resolves compatible access paths before primary-group attribution,
keeps each connection's error/monitoring state, chooses one whole funds source,
and uses the actual contributing account/resource/report in financial links.
Compatible totals are calculated in M05 over the filtered inventory before
pagination. Unknown overlap, incompatible contexts and absent monetary reports
remain explicit exclusions. Counts-only reports never become money. Final
server-side user-selected sorting and complete team/category coverage remain
unfinished on their existing tickets.

Test-first and current evidence:

- Pure pool policy: initial eleven missing-module failures, then two review
  failures for metadata-before-first-report and overflow exclusion counts;
  corrected. Twenty-four new policy cases pass, including exact lineage,
  source/target conflicts, primary/secondary/both-group selection, immutable
  corrections, currencies, empty/partial reports and whole funds provenance.
- Optional contract fields: two expected missing-projection/link failures,
  then two passes. Real SQLite Overview integration first rejected the absent
  financial-pools port, then passed primary-only and secondary-only metadata
  projection without inserting financial telemetry.
- Browser Red: `pool_controls_missing`. Canonical command
  `python -m tools.automation.implementations.auto_m7 --lane browser --check
  owner_pool_controls` now passes against the built application and isolated
  real IAM/SQLite. It exercises create/join/edit/unlink, a shared Overview row
  with two access paths, reload/keyboard/768px, 203 organization choices and
  more than50 pool choices, conflict and real browser-offline recovery with
  the original idempotency key. No request interception/provider substitutes.
- Canonical `--lane pure`:515 Python tests plus all six presentation suites
  pass. Its first run exposed an older timestamp test expecting `.000Z` although
  the existing accepted parser preserves exact source text. Corrected that
  assertion and added a six-digit fractional as-of preservation assertion;
  no production timestamp change was needed.
- Canonical `--lane technical --check budget_http_guards`:12 pass on actual
  IAM/HTTP/SQLite. This remains metadata/no-report evidence, not a real monetary
  source-to-screen comparison.
- AUTO-QUALITY passed at00:27:26UTC: strict mypy695 files, Ruff756 formatted
  files, zero boundary violations, compatible91-operation generated client,
  frontend typecheck and production build. Planning/documentation checks also
  passed; those results are not a full M7 exit.

Changed files: M05 Overview contract/domain/application and pure/integration
tests; P01 Overview schema/router and root composition; generated OpenAPI/client;
P02 account pool controls, API helpers, Overview provenance and presentation
tests; the scoped existing M7 runner and isolated built-browser harness; focused
module/worksheet documentation. Owner configuration and provider profiles are
unchanged. Installed activation, authenticated installed controls, genuine
shared monetary totals and public revision are not claimed by this local packet.

## Installed and published increment at 3c65e1d

The preceding local limitation is superseded for installation and read-only
screen verification by this execution, not for monetary provider evidence.
Clean revision `3c65e1d91f096fd4fe31c7cdee10f4d59ef80823` was retained with build
digest `719b2d6d5e3046606aefce48e47a787ba4b3211d0d2ded41ecae3902c4ef3c9d`.
The real isolated0733→0734 preparation and backup reopen passed without blockers.
Seven focused preparation/browser-selector regression tests also passed.

Canonical `auto_m7 --lane deploy --check financial_activation
--expected-revision=3c65e1d91f096fd4fe31c7cdee10f4d59ef80823` ran from the
sealed fixed release. Its eight operational checks passed: controller, actual
start, installed revision/loopback, restored restart policy, operator/worker
commands, LAN and final postcheck. Exit3 correctly retains separate full
authenticated-financial, collector-continuity and backup-recovery acceptance;
this is not a full deploy or M7 pass.

On12 November00:32UTC the authenticated installed probes passed:

- `node frontend/tests/browser/m7/verify_overview.mjs`: two real financial rows,
  API/DOM equality, filters, exact report drill-down/Back/reload, three viewport
  widths and existing cloud self/team pool controls; zero unsafe requests.
- `node frontend/tests/browser/m7/verify_setup.mjs 3c65e1d91f096fd4fe31c7cdee10f4d59ef80823`:
  actual build revision, setup form, Overview, promotion/support/footer
  continuity;39 requests, zero unsafe requests. No owner configuration changed.

The existing Overview probe now understands shared-report ownership and checks
installed pool control eligibility against the real metadata API. It does not
create/join pools in owner data. Full mutation behavior was proved only in the
isolated real browser workflow above. Actual monetary totals remain unverified.

GitHub `main` was fast-forwarded from `f7a1799` to `3c65e1d`; `git ls-remote`
confirmed the exact public head. The read-only push preflight passed. Pinned
Gitleaks8.30.0 scanned that commit range with full redaction: raw exit1, thirteen
generic-key findings. Each was independently matched to the SHA-256 of its
commit's generated OpenAPI artifact (twelve declarations and one documentation
hash); no credential finding or suppression. This is reviewed scan evidence,
not an unqualified clean scan or full release-security claim.

Remaining: actual provider-backed money and shared totals, full collection/
history/sorting/analysis coverage and the fixed M7 exit. The next independent
implementation packet is the missing OpenAI runtime composition; its source and
protected credential reader already exist. Administrative owner enrollment is
still required for that live source, not for implementing its missing wiring.
