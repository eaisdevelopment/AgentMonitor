# Change plan: Claude dashboard polling

- Status: Approved for this bounded delivery by the owner's 2026-09-28 direction to continue normal dashboard delivery.
- Owner: M04 collection control; root owns composition and lifecycle wiring.
- Parent: M4 `ST-FLEET-002`, existing M04/M02/M05 V1 collection and registry ports.
- Requirements: `FR-ACC-003`, `FR-COL-001/003/004/005/008`, `FR-OPS-002`, `AC-OPS-002/003/006`, bounded `AC-HIST-001`, `AC-UI-005`.

## Outcome and scope

The authenticated local service polls the one unambiguous, eligible,
owner-confirmed Claude default profile while its registry monitoring preference
is enabled. IDs, labels, and organization membership come from M02. Each run is
admitted by M04 before the existing A01 adapter executes and commits through
M05. Polling continues with the browser closed. The admitted source has a
five-minute minimum interval, including after a service restart. An adapter
failure remains visible in collection history; no unsupported auth flow is
started. The loop rechecks registry eligibility before each attempt.

Changes are limited to M04 scheduling/query code, its persistence adapter,
Claude composition, bootstrap lifecycle, real tests, the existing automation
catalog, and documentation. No new dependency, database migration, public HTTP
operation, provider profile mutation, credential access, or process control is
required. Managed/new-profile login and the six-account live matrix remain
separate scopes and do not block this delivery.

P02 refreshes current capacity and quota through the generated API every 30
seconds, preserving history pages already loaded. Refresh errors retain the
previous observations with an explicit message. Foundation composition adds
read-only consumption of `CTR-REG-003` and `CTR-REG-005` at `1.0.0`; their
producer, payloads, and semantics remain unchanged. M04 owns the cadence
decision behind its application boundary. M02, M04, M05, A01, and P02 contracts
remain V1; the HTTP/client surface and schema do not change.

## Test-first sequence and completion command

The real production lifespan test starts over the owner database and must fail
first because no fresh quota is collected. After wiring the collector, it must
observe a new successful M04 run and fresh M05 windows with the registry name,
organization, account ID, and monitoring preference preserved. A second service
start must not poll again inside the source interval. Pure scheduling tests
cover interval and failure blocking; real empty SQLite startup covers no-target
operation, including retained SQLite journal recovery under the service's
exclusive startup lock. The canonical live command is `AUTO-CLAUDE-POLL`, with the explicit
non-secret test data root supplied by `AGENTMONITOR_TEST_OWNER_DATA_ROOT`.
Existing quality, docs, and local Git checks precede the delivery commit.

## Operations and limits

The service owns a bounded worker task and drains an in-flight read before
shutdown. The loop never guesses between competing default-profile
associations. Failed/blocked runs are not treated as fresh observations or
automatically retried contrary to the adapter's no-retry advice. Default-profile
identity is owner confirmed; this read-only source does not prove the email.
Rollback is the previous application commit against the unchanged schema.
