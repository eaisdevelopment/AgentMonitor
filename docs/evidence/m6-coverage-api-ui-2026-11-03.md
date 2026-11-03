# M6 organization coverage API and dashboard increment

Status: Intermediate; deployed service remains on schema v1_0718 during these checks.

Scope: P01/P02 and composition consumers of M02 CTR-REG-013 1.0.0;
FR-ACC-001/002/004/006, FR-ORG-001, FR-SAFE-001/002, AC-UI-002..006,
AC-LIVE-003 and M6-A03/A04/A05/A09. Existing owner-approved M6 cloud scope
and the reviewed coverage impact plan authorize this implementation.

## Red and increment

The real signed-in dashboard probe `coverage_endpoint.mjs` returned
`coverage_endpoint_unavailable`, HTTP 404, before transport implementation.
The real Organizations probe `coverage_editor.mjs` then returned
`organization_coverage_editor_missing` before the component was added.
An earlier closed test-browser connection was a setup failure, not behavioral Red.

Additive GET/PUT/DELETE organization coverage routes consume CTR-REG-013.
The bounded provider query accepts an explicit ordered comma-separated selection
of 1..200 distinct organization IDs and returns unchanged selection, sparse
rows, completeness, revision and producer time from one registry read. Singular
absence returns `coverage: null` with version-zero ETag; an absent organization
returns 404. GET needs read:accounts; PUT/DELETE need write:accounts, normal
CSRF, If-Match and Idempotency-Key. Account-version mismatches return 412.
No route calls a provider, reads a credential, changes a connection or duplicates
a monetary balance. The generated OpenAPI/client now exposes 78 operations.

Organizations gains a collapsed Provider coverage form with named existing
accounts and organizations, closed unavailable reasons and owner-declared
validity. Shared means use of that selected account, not proven pool identity.
The original account link remains available. Removing a declaration retains
history and leaves the account untouched.

## Verification so far

The first private-copy HTTP/browser test passed in 43.91 seconds. It used a
real owner-only SQLite backup upgraded through AUTO-MIGRATE, actual production
repositories/IAM/HTTP transport and the current authenticated browser session.
The HTTP-only test composition omitted background collection tasks; no fake
ports, credentials, accounts, provider responses or provider actions were used.
Only the existing owner-confirmed own-account relationship was written, and
only to the private copy.

Checks covered CSRF refusal, forged provenance refusal, stale selected-account
version, create, exact retry, stale create conflict, retained removal, sparse
ordered selection, duplicate-selection refusal and account nonmutation. The
built form displayed ordinary choices and required an explicit unavailable
reason; a 390-pixel viewport had no horizontal overflow. Positive shared and
unavailable writes remain NotRun because no real owner disposition was supplied.

The OpenAPI positive/negative policy suite passed all six tests in 141.66 seconds
after its exact operation/request catalog was extended. TypeScript and scoped
strict Python type checks passed. The boundary scan initially found reciprocal
persistence imports and a missing exact policy seam; the structural correction
removed the cycle and admitted only the coverage policy through its application
module. The subsequent boundary scan passed with zero violations.

Independent P01/P02 review corrected the maximum ETag/header length mismatch,
made incomplete organization choices explicit, and stopped post-save/conflict
reload failures from claiming that choices had refreshed. A subsequent browser
run additionally exercised actual Save coverage and Remove declaration controls
on the private own-account record and passed in 30.13 seconds. This second run
also included the two reviewed UI corrections; failure-refresh and truncated
organization states were code-reviewed, not injected into a fake server.

Canonical repeatable focused command, with normal developer dependencies and
the existing signed-in shared browser on port 9225:

```bash
PYTHONPATH=backend/src python -B -m pytest backend/tests/integration/api/test_coverage_private_http.py -q --tb=short
```

The test creates its own private migrated database and ephemeral loopback port,
refuses the live dashboard port for mutations, closes its tab/server and uses no
new login or owner attestation. API/browser status output excludes identifiers,
request payloads and credentials. The installed service and full AUTO-M6-EXIT
remain separate boundaries; this document does not claim their completion.

## Impact and next work

Changed paths: API schemas/router/dependencies/problems, composition wiring,
OpenAPI generator and generated artifacts, Organizations component and API
adapter, exact boundary policy, focused real tests, module/impact documentation
and routine migration description. The reviewed M02/DB changes add v1_0719;
no new dependency, license, runtime configuration or secret store is introduced.

Remaining: complete migration/cutover recovery checks; canonical quality/docs/
planning checks; deploy with verified backup; rerun installed API/browser checks;
consume genuine coverage through canonical M6 evidence. Missing live models,
actual second-organization disposition and natural failure/recovery evidence
remain distinct requirements, not erased by this administrative feature.


## Combined pre-deployment result

The combined final run passed AUTO-QUALITY (583 formatted Python files, strict
types across 527 files, zero boundary violations, generated 78-operation API
and production frontend build) and all eight actual private-copy registry/HTTP/
browser scenarios in 72.88 seconds. No test was skipped. AUTO-DOCS-CHECK passed
297 Markdown files, and AUTO-PLAN-CHECK passed after synchronizing the changed
migration routine description. The original public registry exception remains
explicitly re-exported after helper extraction; no consumer compatibility was
removed. Typed private-copy fixtures now accept a genuine compatible 0719 copy
as well as upgrading 0718, so deploying this migration does not invalidate
the test setup.

The exact two intended organizations were resolved once from the authenticated
registry using the owner's previously supplied SDK/EAIS selection. Their stable
IDs were saved in an owner-only non-secret verification selection file; this
creates no coverage assertion. Its SHA-256 is
`995499fd1a277c03aacab086ee9beefd4e97c14fc643c263a969ad891dfd21d3`.
Repeated gates will use the stable IDs, not infer scope from organization names.
Installed activation and full M6 acceptance remain unclaimed at this checkpoint.
