# M7 billing credential status

Status: intermediate implementation; T002 and M7 remain incomplete.
Requirements: FR-ACC-001/002/004/006, FR-BUDGET-001/006; M7-A01/A07.
Owners: M02 metadata policy/repository, P01 wire, P02 rendering; root integration.

## Contract and behavior

CTR-REG-014 advances additively from 1.0.0 to 1.1.0. The optional
`AccountBillingConnectionsV1.credential_status` defaults to null: not queried or
not applicable, never implicitly Missing. When a billing connection exists, a
single real SQLite read transaction projects the existing credential-binding
records into Missing, Pending, Stored or Cleanup required. Pending wins during
rotation; the actual prior active generation remains separately represented.
Cleanup can remain required alongside a stored or pending record. A revocation
fence generation is never presented as an active credential generation.

Stored means the lifecycle records completed local entry. It does not inspect
the file, verify the provider, prove present-day file availability, enable
monitoring or assert identity. No credential/binding IDs, paths, variable names,
secret values or secret-derived metadata are included. No schema migration or
new dependency is needed. Existing subscription identity/preferences remain
unchanged. The UI shows the safe state and an independent cleanup warning;
no local command or provider access button is invented by this increment.

GET remains authenticated and no-store. Review found its strong account-version
ETag was invalid for this composite representation: credential state changes
without changing account version. GET now omits that validator. The explicit
body account version and POST If-Match concurrency behavior remain unchanged.

## Red, Green and review

Commands below use the admitted backend Python with `PYTHONPATH=backend/src`:

- Registry Red: `pytest backend/tests/integration/registry/test_billing_credential_binding.py -q --tb=short`:
  **2 failed, 6 passed**; `AccountBillingConnectionsV1` lacked
  `credential_status`. These use real migrated file SQLite, actual prepare and
  archive operations, without a key or fabricated activation.
- HTTP Red: `pytest backend/tests/integration/api/test_billing_enrollment_http.py -q --tb=short`:
  **1 failed, 1 passed** with `KeyError: 'credential_status'` from real HTTP.
- After implementation, those suites plus
  `backend/tests/registry/test_billing_credential_status.py`: **11 passed**.
  The latter is a pure, no-I/O rotation/disconnect/cleanup policy test; its
  constructed lifecycle records are not evidence of credential storage.
- Expanded account-intent/connections/binding/HTTP/pure regression:
  **34 passed**, before the subsequent ETag correction.
- ETag Red: the HTTP suite produced **1 failed, 1 passed**, rejecting the
  incorrect strong validator. After removal: **2 passed**, including unchanged
  POST version/idempotency/CSRF behavior.
- Strict mypy passed for six changed contract/domain/repository/API files.
  Scoped Ruff check/format passed.
- P02 captured real browser Red after actual HTTP reported Missing but the
  required label was absent. Strict TypeScript and the rebuilt real
  `accounts_admin` browser scenario then passed. See the
  [UI evidence](m7-api-setup-ui-2026-11-11.md).
- Independent read-only review checked projection generations, transaction
  consistency, nonsecret response fields and the provider namespace changes.
  Its one concrete status finding was the ETag correction above.

Root updated the compatible OpenAPI/client from source. The exact contract
registration/adoption control bindings were independently verified against
`e544f8c`; twenty frozen plans remain unchanged. Historical evidence is retained.

Final root verification: canonical `registry_metadata` passed all **34 tests**,
including the ETag correction. `AUTO-BUILD` passed generated-contract checks
(80 operations), strict TypeScript and Vite. The surrounding one-off wrapper
then failed its temporary-link cleanup call with a missing argument; root
checked the exact symlink target and creation time from that invocation and
removed it using the existing guarded helper. This was a wrapper failure after
the successful build, not a build pass inferred from the wrapper exit code.

The synchronized planning check initially rejected the new contract version
(`CTR-REG-014: expected proposed version 1.0.0`). Updating its explicit admitted
minor version to 1.1.0 made `AUTO-PLAN-CHECK` pass. No broad version bypass was
added. M7 ticket planning and documentation checks passed as well.

## Limits and next work

No real key was viewed or entered, no default provider profile or installed
service was changed, and no owner account was configured. Full local entry,
successful provider verification, enable/first-reading behavior and installed
browser proof are separate outstanding boundaries. Missing-state browser
evidence does not claim naturally observed stored/pending/cleanup browser states.
Financial reporting, persistence, collection, Overview and final M7 acceptance
remain open. The provider-neutral file writer has separate
[bounded evidence](m7-billing-env-store-2026-11-11.md).
