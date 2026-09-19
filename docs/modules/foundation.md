# Foundation technical contracts

- Status: Task 1 / FND-I02 technical contracts and Python policy published;
  application mechanisms and full M1 completion remain later work.
- Owner: PLAN-FND; PLAN-DB retains semantic ownership of CTR-DB-001..003.
- Version: `foundation.contracts.v1`, technical contracts `1.0.0`.
- Last substantive review: 2026-09-19.
- Requirements: NFR-ARCH-001, NFR-ARCH-002, NFR-COMP-001.
- Acceptance support: AC-TEST-001, AC-TEST-006; FND-BND-001..003.

The approved [foundation plan](../plans/foundation/plan-v1.md) publishes
immutable, closed technical values in the six producer-owned contract files.
The explicit milestone approval governs this work despite historical Draft
metadata in the unchanged planning records. This increment adds no application,
provider, API, database, browser, logging, configuration-loading, process-control,
or deployment behavior.

| Contract file | Published contracts |
|---|---|
| `agentmonitor.contracts.common_v1` | CTR-COMMON-001 OpaqueIdV1; CTR-COMMON-002 TimestampAndDurationV1; CTR-COMMON-003 ExactQuantityV1; CTR-COMMON-006 EventEnvelopeV1; CTR-COMMON-007 FieldAvailabilityV1 |
| `agentmonitor.contracts.configuration_v1` | CTR-CONFIG-001 ConfigurationRegistryV1; CTR-FND-003 BootstrapConfigurationV1 |
| `agentmonitor.contracts.foundation_v1` | CTR-FND-001 RepositoryLayoutAndOwnershipManifestV1; CTR-FND-002 ApplicationFactoryV1; CTR-FND-004 CorrelationContextAndSafeLogEventV1; CTR-FND-005 OpenApiArtifactAndGeneratedClientPipelineV1; CTR-FND-006 MigrationMetadataV1; CTR-FND-007 BuildMetadataV1; CTR-FND-008 TestEvidenceSummaryV1 |
| `agentmonitor.contracts.boundary_v1` | CTR-BOUNDARY-001 SafeSubprocessExecutionV1; CTR-BOUNDARY-003 ApprovedRootAndFileReadV1 |
| `agentmonitor.contracts.platform_v1` | CTR-PLAT-001 PortablePlatformPrimitivesV1 |
| `agentmonitor.contracts.database_v1` | CTR-DB-001 SchemaCompatibilityV1; CTR-DB-002 RepositoryAndUnitOfWorkTechnicalFamilyV1; CTR-DB-003 DatabaseSnapshotActivationV1 |

Each type exposes `CONTRACT_ID`, `CONTRACT_VERSION`, and `OWNER`; no compatibility
re-exports or unversioned contract package are provided. The
[adoption manifest](../plans/contract-adoption.toml) and
[contract baseline](../plans/contract-baseline.toml) remain the semantic
producer/consumer catalog. Breaking meanings require a new major and the
[contract migration process](../architecture/contracts-and-versioning.md).

## Value semantics and limits

Frozen, slotted dataclasses reject unknown constructor fields and field writes.
`TechnicalValueV1` is the common immutable technical record base. It rejects
mutable nested containers, binary floating point, non-finite decimals, and
non-UTC or naive timestamps; Literal status fields are runtime-closed. Public
field types are also checked statically; these values do not parse untrusted
external data. Callers must validate external input at its owning boundary.

Opaque IDs carry no provider identity or inferred meaning. Quantities use
`Decimal` with explicit units (currency code for money); durations use integer
milliseconds. Availability preserves available exact zero separately from
missing, null, unknown, unsupported, unavailable, not-applicable,
withheld/denied, stale, and unresolved. Event producers compose the technical
envelope with their own typed payload; the envelope admits no arbitrary raw
payload, and CTR-EVT-001 separately governs durable delivery and replay.

Factory, bootstrap, subprocess, file, platform and database values are input,
capability or compatibility metadata, not executable ports. Factory IDs refer
to approved registrations, never dynamic import strings. Bootstrap metadata
contains non-secret source descriptions and secret-presence booleans only;
owner-specific settings and the secret-safe loader belong to later increments.
Platform availability does not prove Linux or macOS behavior. Database ranges
use opaque catalog revisions without lexical comparison; transaction, snapshot,
activation and recovery implementations remain PLAN-DB work. No tables,
migrations or retained operational data are introduced.

## Import and ownership enforcement

The canonical Task 1 checks, run from the repository root, are:

```bash
python3 -m pytest backend/tests/foundation/test_contract_boundaries.py -q
python3 tooling/foundation/check_boundaries.py .
```

The checker parses real Python files under `backend/src/agentmonitor` without
importing or executing them. It emits sorted `path:line:reason` diagnostics,
returns nonzero for violations and never emits source contents. Missing source,
unreadable/invalid Python, source symlinks, wildcard imports and detectable
dynamic import calls fail closed. Relative imports and package-child imports
are resolved for policy; cycles are detected on the actual source graph.

Dependency direction is composition → API/adapters → application ports →
domain/contracts. Domain and contract packages use explicitly reviewed pure
standard-library modules and published contracts. Domain code cannot import
OS, framework, provider, composition or UI packages. Module code cannot import
another module's internals; API cannot import persistence implementations;
adapters consume module application ports; provider adapters cannot import
each other; foundation cannot import module internals. Cross-owner private
imports and generic `utils` imports fail. This static Python checker is not a
runtime sandbox, table-access analyzer or frontend TypeScript analyzer.

The same command validates real ownership/adoption/baseline TOML: each source
path has exactly one allocation; each contract has its unique declared
producer, V1 version, and recognized baseline maturity. Shared writer authority
and semantic producer ownership remain distinct. Historical `evidence_blocked`
platform maturity never becomes a live pass. Full planning synchronization is
separately checked by `python3 tools/planning/validate_plans.py --stage synchronized`.

## Verification and operations

FND-BND-001 covers outward imports and fail-closed parsing, FND-BND-002 covers
relative/package imports, private edges and cycles, and FND-BND-003 covers
published names/versions/immutability plus manifest producer and path ownership.
Tests use pure constructed technical values and real temporary Python/TOML
files as deterministic policy inputs. They do not simulate a product external
boundary or provider. The CLI is exercised against the real checkout and an
invalid root, with sanitized output and real subprocess exit codes.

No dependency, license, secret store, network call, service, provider profile,
default profile or running agent is changed. Rollback is a source revision
rollback before consumers adopt these types; future breaking consumers follow
the versioned migration policy. The next foundation stories implement the
approved mechanisms and their real boundary evidence. DB, HTTP, browser,
provider, platform-operation and hosted-CI verification are Not Run here.
The wider AUTO-QUALITY/build/migration/release gates remain unavailable until
their owning tasks provide the full implementations; this document claims
only the scoped Task 1 checks.
