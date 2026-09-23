# M03 provider-system module

Status: **provider-neutral protocol and compatibility persistence implemented;
Claude/provider conformance Not Run**.

Owner: `PLAN-M03`

Contracts: `CTR-PROV-001..008` V1

Database revision: `v1_0300`

## Persistence boundary

M03 owns only `provider_system_compatibility_assessment` and
`provider_system_event_outbox`. The SQLite repository accepts the public
`CompatibilityAssessmentInputV1` and returns immutable safe compatibility
views. It never calls a provider or reads a profile.

An exact replay of the current canonical compatibility input returns the
existing assessment and does not append another event. Request metadata
(`assessed_at` and `correlation_id`) is excluded from that fingerprint. A
changed compatibility input creates a new assessment, marks the prior row
non-current, links the supersession, and appends one outbox event in the same
`BEGIN IMMEDIATE` transaction. The transaction also serializes nullable
installation/source scopes, for which SQLite's ordinary unique-index `NULL`
behavior is insufficient. Discovery of more than one current row fails closed.

History and pending-outbox reads require an explicit limit from 1 through 100.
Every query validates opaque-ID types and bounds, capability syntax, optional
source syntax, optional installation-ID type, and limits before opening the
database. Invalid query input crosses the boundary only as
`provider_system_query_invalid`.
Persistence and corrupt-record failures cross the adapter boundary only as
stable `ProviderSystemRepositoryErrorV1` codes; SQL, paths, stored values, and
driver messages are not exposed.

## Data and privacy

Compatibility rows contain safe scalar IDs, declared versions/states, stable
reason codes, manifest/input SHA-256 fingerprints, UTC instants, and
supersession metadata. Outbox rows contain only safe event routing metadata.
Neither table accepts credentials, account identity, profile paths, provider
payloads, prompts, responses, source content, or free-form provider errors.

Non-available provider versions require the value, scheme, and rule to all be
absent at the public contract, repository, and `v1_0300` database-constraint
boundaries. DTO construction rejects naive/non-UTC assessment and validity
instants, and persisted non-UTC timestamps fail closed as invalid records.
The database also requires lower-case hexadecimal SHA-256 fingerprints,
canonical microsecond UTC `Z` timestamps, nondecreasing validity, the closed
compatibility/version-scheme vocabularies, and complete available-version
tuples.

Outbox DTO and database rows require
`occurred_at <= recorded_at <= available_at <= claimed_at <= delivered_at`
for timestamps that are present. Pending rows have no claim/delivery time;
claimed rows have one positive attempt and no delivery time; delivered rows
have both times and a positive attempt. The implemented repository publishes
and lists only the bounded pending lifecycle. Claim, retry, delivery, consumer
receipt, and replay operations remain Not Run and are not implied by these
storage invariants.

## Verification and limitations

Real file-backed SQLite tests cover reopen/round-trip, deterministic replay,
supersession/history, concurrent nullable scopes, exhaustive query validation,
direct-SQL constraint rejection, bounded pending ordering, and assessment/
outbox rollback on an actual SQLite write failure. See
[the ST-CLA-001 persistence evidence](../evidence/m3-st-cla-001-provider-system-persistence.md).

The broader `ST-CLA-001` adapter, live provider/account observation, registry
reconciliation, collection/capacity/runtime integration, API, and browser are
outside this slice and remain Not Run. The repository does not establish
Claude conformance or milestone completion.
