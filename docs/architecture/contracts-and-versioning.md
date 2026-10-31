# Contracts and versioning

## Contract classes

AgentMonitor recognizes five separately governed contract classes:

1. Public REST/OpenAPI contracts.
2. Internal cross-module command/query/view contracts.
3. Internal domain-event contracts.
4. Provider-adapter protocol and provider-extension schemas.
5. Database schema and persisted-record compatibility.

Source-code function signatures that never cross a module boundary are implementation details, not public contracts.

## Version identifiers

- Public API: URL major version, initially `/api/v1`.
- OpenAPI document: product semantic version plus API major.
- Internal DTO/event: stable schema name with integer major suffix, for example `CapacityObservationRecordedV1`.
- Provider adapter protocol: semantic protocol version, initially `1.0` after Milestone 0.
- Provider-specific extension schema: provider name + capability + integer schema major.
- Database: monotonic Alembic revision chain and application schema compatibility range.

## Compatibility rules

### Compatible changes

- Add an optional response field with a safe documented default.
- Add a new endpoint, event type, enum extension designed for unknown values, or provider capability.
- Relax request validation without changing existing interpretation.
- Add a nullable database column or new table through an expand migration.

### Breaking changes

- Remove or rename a field, route, event, capability, or enum value.
- Change units, currency representation, timestamp meaning, nullability, or identifier semantics.
- Make an optional request field required.
- Reinterpret an existing status or confidence category.
- Change event delivery/idempotency semantics.
- Change stored data so an older supported binary cannot safely read it.

Breaking changes require an ADR, migration plan, compatibility window, consumer update, and major contract version. Deprecation precedes removal unless a security issue makes compatibility unsafe.

## Core contract conventions

### Identifiers

- Internal IDs are opaque, globally unique strings; clients never infer meaning from them.
- Provider IDs are separate fields and never become primary keys.
- Account aliases are mutable display data, not identity.

### Time

- API timestamps are RFC 3339 UTC with explicit `Z`/offset.
- Durations are integer milliseconds unless a schema explicitly states another unit.
- A metric distinguishes `observed_at`, `collected_at`, and `stored_at` when they differ.
- Reset time may be exact, estimated, or unknown; precision is explicit.

### Quantities and money

- Every numeric metric carries a unit or a contract-fixed unit.
- Money uses currency and integer minor units or an exact decimal string where a currency lacks suitable minor units.
- Ratios are exact decimal strings or documented basis points; binary floating point is not persisted for financial values.

### Provenance

Every observation includes:

- source type and stable source identifier;
- provider/adapter/provider-CLI version when known;
- stability: documented, supported CLI, local undocumented, experimental private/browser;
- value kind: authoritative, provider-reported, derived, heuristic, or unknown;
- freshness and expiry policy;
- precision and confidence;
- derivation identifier and input observation IDs for derived values;
- sanitized warnings.

### Status extensibility

API schemas must tolerate future provider-specific states without mapping them to false known states. Normalized enums include `unknown`, and raw provider state may be present in a safe extension field.

## Event envelope

Published events use an envelope conceptually equivalent to:

```json
{
  "event_id": "opaque-id",
  "event_type": "capacity.health.changed.v1",
  "occurred_at": "2026-09-18T12:00:00Z",
  "recorded_at": "2026-09-18T12:00:01Z",
  "producer": "capacity",
  "producer_version": "1.2.0",
  "correlation_id": "opaque-id",
  "causation_id": "opaque-id-or-null",
  "subject_id": "opaque-id",
  "payload": {}
}
```

Events are immutable, at-least-once, and ordered only within the documented aggregate stream. Consumers use `event_id` for idempotency. PII, secrets, content, and raw provider payloads are prohibited.

## API compatibility workflow

1. Change a typed backend schema and use case contract.
2. Generate OpenAPI from the running application.
3. Validate and compare against the committed baseline.
4. Classify changes as compatible/breaking.
5. Generate the TypeScript client.
6. Compile and test all consumers.
7. Update API documentation, examples using non-secret structural values, and changelog.
8. Obtain approval for breaking changes before implementation merges.

Hand-edited generated clients or OpenAPI documents are prohibited.

## Provider contract workflow

- Adapter declares protocol versions and capability schema versions it implements.
- Registry rejects incompatible adapter protocol majors.
- A provider CLI version outside the verified range yields `incompatible`/`unverified`, not silent parsing.
- A parser change increments adapter version and, when shape/meaning changes, provider-extension schema version.
- Real live verification is required before expanding the verified provider-version range.

## Database migration policy

- Alembic revision history is immutable after shared use.
- Prefer expand → migrate/backfill → switch readers/writers → contract over destructive changes.
- Every migration documents owner module, requirements, expected data volume, locks/downtime, backup prerequisite, validation query, and recovery.
- Migrations run transactionally where SQLite permits.
- Downgrade scripts are provided only when they are real, safe, and tested. Otherwise recovery uses a verified backup plus prior binary.
- The application refuses to start writable service against a schema newer than it supports.
- A schema older than supported is upgraded explicitly; no hidden runtime DDL.

## Contract governance

Contract proposals use [the change-plan template](../templates/change-plan-template.md). The producing module owner and every known consumer must review a breaking change. The traceability matrix records the contract version implementing each requirement.
