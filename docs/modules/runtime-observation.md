# Runtime observation (M06)

Status: M3 Task 5 partial implementation. Generic Linux process observation and
the M06 persistence/query foundation are implemented. Exact Claude executable,
version, installation, session, and account correlation remain **Blocked / Not
Run** because the approved M0 handoff contains no executable-fingerprint join or
targeted-profile/session source.

## Ownership and contracts

M06 owns the `CTR-RUN-001..007` family. This Task 5 slice publishes the
`CTR-RUN-001..003` and `CTR-RUN-006..007` foundations in
`backend/src/agentmonitor/contracts/runtime_observation_v1.py`: process/session
identities and observations, metrics, graph/correlation decisions, commit DTOs,
and bounded query views. It also publishes minimum `CTR-RUN-004..005` state and
stall types plus a pure fail-closed evaluator. State persistence/events, policy
mutation/persistence, and real session/stall evaluation remain unimplemented or
Blocked and are not accepted by this slice. Pure effective-policy precedence is
account, provider, organization, then global. A04-LINUX owns the read-only procfs
implementation and the narrow Linux `CTR-PLAT-001` capability producer. A01
owns the three Claude local runtime capability adapters. Those A01 ports
intentionally return `unsupported` with `never` retry until M0 approves a real
source.

M04 calls M06 only through the collection commit seam. P01/P02 are not part of
Task 5 and must use the later versioned API; no UI or API code reads these tables
directly.

## Implemented truth boundary

The Linux process identity is the safe tuple `(platform source, hashed boot and
PID-namespace scope, PID, start-time ticks)`. The `/proc/PID/stat` `comm` value
is stored separately as an explicitly observed executable label and is excluded
from identity hashing. It does not establish provider, version, installation,
session, or account identity. Those references stay null/unresolved.

The outer `ObservationProvenanceV1.provider_key = claude` identifies the
M0-approved capability/selector lineage, not the observed process subject.
Subject-level `provider_key` and `installation_id` remain null, provider version
is unavailable, and the confidence reason explicitly states that procfs fields
are confirmed while provider attribution is unresolved.

The adapter reads only same-UID numeric `/proc` entries, the boot ID, PID
namespace identifier, and allowlisted `/proc/PID/stat` fields. It never reads
argv, command lines, environment, memory content, file descriptors, terminal
data, prompts, responses, tools, source code, or credentials. It has no process
control method. Candidate races, permission errors, malformed layouts, bounds,
deadline expiry, and unsupported source/version/selector tuples are explicit
typed outcomes. Each procfs metadata read uses a fixed upper bound and reads at
most one byte beyond that bound before failing closed.

Correlation is fail-closed. `strong` is only an evidence class; automatic
selection also requires an explicit typed owner-approved rule tuple. The
production rule catalog is empty for current Claude, so current evidence stays
unresolved.

## Persistence and queries

Additive migrations `v1_0600..v1_0603` allocate process/session
current state and observations, runtime metrics, graph/correlation history,
state policy/transitions, commit receipts, a durable outbox, and bounded query
indexes. Constraints enforce process boot scope, field state/value/unit/reason
pairing, activity and metric semantics, UTC text, graph/current-row rules,
correlation state/account pairing, stall-policy scope uniqueness, receipt
lineage, and outbox lifecycle. No telemetry is seeded.

The repository atomically commits a digest-validated typed batch, its complete
safe `ObservationProvenanceV1`, current projections, immutable observations,
correlation decisions, receipt, and outbox event. Exact replay returns the
stored receipt; conflicting reuse fails closed. Process current/history queries
reconstruct provenance after restart. Session list/tree DTOs require provenance
and the repository reconstructs it from the current session observation and
durable receipt. The empty query runs against the real schema; non-empty
real-provider acceptance remains blocked by the missing approved A01 source.

The pure state/stall evaluator accepts only the approved normalized state
vocabulary. Missing, stale, unknown, or invalid progress evidence is not
evaluable; only definitive current wait/error/auth/quota evidence excludes a
stall; a current running-presence fact is required; and reaching the 600-second
default can produce only an `inferred` possible-stall result. No
provider-specific raw state is mapped in M06.

## Degradation

- An unapproved provider/version/source/selector tuple is rejected before
  procfs I/O.
- Procfs/system-unit failure returns a typed safe outcome; it does not raise raw
  OS details through the contract.
- Partial candidate inspection remains partial with bounded omission codes.
- Unknown provider/install/account facts remain null or unresolved, never
  guessed.
- A malformed or provenance-inconsistent batch is rejected without erasing
  prior current state.
- Query/database failure is mapped to `runtime_repository_unavailable` without
  SQL or stored metadata disclosure.

## Verification

Canonical focused evidence is recorded in
`docs/evidence/m3-st-obs-002.md`. The real-provider session/account rows are
listed there as Blocked / Not Run and must not be counted as passed.
