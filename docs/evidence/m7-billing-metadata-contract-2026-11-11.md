# M7 billing metadata boundary

Status: implementation in progress, not a connected billing account or M7 pass.
Requirements: FR-ACC-001/002/004/006, FR-BUDGET-001/006; M7-A01/A07.
Owner: M02 registry; consumers P01/P02 and later M04/M05 billing collection.

## Contract decision

Additive `CTR-REG-014` version 1.0.0 lives in
`backend/src/agentmonitor/contracts/registry_billing_v1.py`. A billing connection
uses its existing registry resource ID as its connection ID. It has a distinct
monitoring preference from subscription monitoring. Enrollment stores only owner
metadata; it cannot establish provider access or identity, enable monitoring,
or create a provider observation. An optional safe provider scope ID is explicitly
owner-asserted; absent scope stays unresolved. Scope generation and record version
are separate from credential generation. No secret field exists in the command
or wire model.

The first metadata increment offers authenticated GET/POST on
`/api/v1/accounts/{id}/billing-connections`. GET is read-only and does not inspect
credentials. POST requires account write permission, CSRF for cookie sessions,
Idempotency-Key and the current account ETag. Changed payload replay conflicts.
A pending billing resource is persisted and survives reopen; existing account
identity and subscription preference remain unchanged. Missing accounts are 404;
archived/disabled accounts cannot enroll. This increment does not implement the
separate credential, verification, scope-edit, monitoring or disconnect flows.

One connection per account is the initial approved scope. Ollama must reuse its
existing M6 balance resource/binding, not create a second key or duplicate pool.
Until that reuse is wired, metadata creation is refused explicitly and existing
cloud controls remain authoritative. This limitation does not close T002/T009.

## Database allocation

Committed `v1_0730` remains immutable. The additional M02 connection relation is
`v1_0731`, following `v1_0730`. Planned M05 report storage moves to `v1_0732` and
optional M04 receipt storage to `v1_0733`. This changes internal migration order,
not product scope or existing contracts. Fresh migration and metadata tests use
isolated real file SQLite; the installed M6 database is untouched.

## Evidence so far

The real Uvicorn/IAM/SQLite enrollment test failed at GET connection status:
HTTP 404 instead of 200. Creation already succeeds and remains pending,
unresolved and monitoring-disabled. The expanded scenario also requires actual
persisted metadata, unchanged subscription state, idempotent replay, conflicting
payload rejection, and auth/CSRF/version/key-field protections. Green and final
migration evidence will be added after execution, not inferred from code.

No new dependency, license change, provider request, owner account edit, default
profile access or credential read is part of this increment. P01 delegates through
the published registry port; it does not inspect tables or provider files.


## Executed integration results

The GET/POST enrollment scenario now passes against real Uvicorn/IAM/file SQLite:
creation/replay/readback, disabled monitoring and unchanged subscription identity;
missing authentication, CSRF, version and idempotency input are rejected, as is
an unexpected API-key field (tested with null, not credential material).
`AUTO-M7-TEST`'s direct `registry_metadata` selection passed 25 tests. The focused
registry/schema/intent regression passed 27 tests. Scoped strict mypy passed the
six root-owned contract/API/composition/schema files. Generated OpenAPI/client
admission passed with 80 operations and compatible additive changes.

New migration digest:
`03cee77d6b3beca1d545227b72dca0cb7c027e7c3dca8d2c5e48f0c3bfde83ee`.
The real fresh Alembic chain produced schema digest
`16a46f10c7d1bdf70dff9e81ae75b8f4dfddd65fbdab81304e2a0a9708be733a`, with
integrity and foreign-key checks passing and zero billing rows before use.
An initial schema-inspection helper used an invalid database filename and was
corrected to the actual required agentmonitor.db name; that setup failure is not
claimed as behavioral Red. Old migrations remain unchanged. The installed service
has not been migrated or switched.

Independent bounded implementation review found no blocking defect in metadata
persistence/HTTP safeguards. Its scope excludes credentials, provider I/O,
monitoring, disconnect, Ollama reuse and installed activation; T002 remains open.
See the separate [UI evidence](m7-api-setup-ui-2026-11-11.md) for built-browser
creation and mixed-account metadata behavior.


The capacity schema and actual SQLite health regression selection passed 17
tests after admitting `v1_0731`. The subscription layout review caught an expanded
billing form above important account activity; the corrected built-browser test
now proves that API-only setup stays visible while subscription billing is a
collapsed secondary section. This avoids consuming the main activity area with
unconfigured billing controls.


## Nonsecret credential references

Existing provider-neutral CTR-REG-011 shapes are unchanged. Their SQLite loader
now admits Claude/Codex only after persisted pending/active billing enrollment.
Archive acquires the existing account credential lock and retires pending
references in the registry transaction; subscription-only records remain denied.
The eight new real metadata/lock tests moved from four failures to eight passes;
a six-file adjacent regression passed 44 tests. See
[binding evidence](m7-billing-credential-binding-2026-11-11.md).
No key storage, activation, provider verification or physical credential cleanup
is claimed. No change was made to Ollama-specific access-target verification.


## Checkpoint validation

The expanded canonical `registry_metadata` selection passed 33 tests, including
nonsecret binding preparation/archive locks. `AUTO-BUILD` passed strict
TypeScript, generated 80-operation compatibility, locked asset checks and the
production Vite build. Planning and documentation checks passed. The installed
M6 dashboard remains active and returned HTTP 200; no M7 deployment or financial
provider verification is implied by that availability check.


The staged secret scan reported two generic-key findings, both generated old/new
`openapiArtifactSha256` assignments. Each was independently matched to SHA-256 of
its exact Git OpenAPI artifact bytes. No other finding was reported; these are
reviewed nonsecret digests, not credential values.
