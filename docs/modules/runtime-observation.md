# Runtime observation (M06)

Status: M3 Task 5 live slice **Green**. Generic Linux process observation, M06
persistence/query, and the separately versioned owner-selected Claude OTLP
session-start lane are implemented. The owner-terminal OTLP run, durable
same-account session/process correlation, authenticated API, and populated
production-browser verification passed. Natural stall evidence and manual
resolution of an actually ambiguous correlation were unavailable and remain
Not Run; neither is substituted with constructed telemetry.

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
owns the three provider-neutral Claude local runtime capability ports. Their
generic unresolved methods remain fail-closed; the exact M3 lane is a separate
official-OTLP composition bound to Claude Code `2.1.282`, Linux, the protected
default profile, and one explicitly selected owner-confirmed account.

M04 calls M06 only through the collection commit seam. P01 exposes M06 through
versioned query ports, and P02 consumes only the generated API client; no UI or
API code reads these tables directly.

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
selection also requires an explicit typed owner-approved rule tuple. Generic
procfs evidence remains unresolved. The M3 OTLP composition admits exactly its
authenticated account-fingerprint rule after exact owner account selection and
process/install/version verification; it never uses sole-account inference.

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
durable receipt. Empty and process-populated queries run against the real
schema. The real owner-selected OTLP launch committed the session, exact process
link, strong account correlation, collection receipt, and full provenance. A
database reopen returned the same account/session lineage. The bounded tree
query marks parentage unknown when the linked parent process is no longer
current; it does not invent an edge.

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
`docs/evidence/m3-st-obs-002.md`,
`docs/evidence/m3-registry-provider-identity-binding.md`, and
`docs/evidence/m3-owner-confirmed-claude-vertical.md`. The final transparent
owner-terminal and populated-browser commands passed on 2026-09-24. Any skipped
live declaration remains Not Run and is not counted as a pass.

## Owner-confirmed terminal account view

The bounded [approved change](../plans/integration/live-agent-account-association-change.md)
adds explicit process/account settings under M06 application ports and
`adapters/persistence/runtime_observation/settings/`. Read joins only current
same-user processes with matching boot/namespace, PID/start and executable
fingerprint. Separate revisioned tombstones retain optimistic concurrency;
identical retries preserve confirmation time/actor. Legacy provider correlation
remains unresolved. Manual account changes in a surviving terminal require a
new owner confirmation. This does not invent provider sessions or per-agent
quota/model/tokens. ADR0015 records the private versioned settings format,
writer locking, fail-closed controls and separate backup requirement.

P01 adds a browser-only conditional PUT; the existing global GET remains
compatible. P02 filters that read into current confirmed account terminals and
an explicitly unlinked terminal section. Read-only native process discovery
includes verified retained CLI binaries independently of quota parser coverage.
The [progress record](../evidence/live-account-agents.md) records passing
detection, controls and owner-authorized live persistence after service restart.
The later [M4 completion evidence](../evidence/m4-completion.md) records the
standalone full-M4 gate; other naturally unavailable identity-change scenarios
retain their recorded status.

For the current-revision M4 gate, this freshly read live process association is
the positive account/runtime witness: at least one guarded running Claude process
must have an owner-confirmed link to a selected active monitored account before
and after AgentMonitor's restart. Account-scoped durable session reads remain
zero-or-more because unresolved correlation is a truthful result. The separate
persisted process/session topology suite and global runtime browser view remain
required, so accepting an empty selected-account session page does not waive
ST-FLEET-003 persistence, hierarchy, provenance, or UI evidence.

Canonical command: `python3 tools/automation/run.py AUTO-ACCOUNT-AGENTS`.
