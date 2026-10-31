# Claude dashboard polling delivery

- Evidence ID: `CLA-DASH-POLL-2026-09-28`
- Status: **Passed for one enrolled real Claude default profile**; broader M4/V1 acceptance is unchanged.
- Authority: the owner's direction to finish the dashboard and continue delivery; [bounded change plan](../plans/integration/claude-dashboard-polling-change.md).
- Owner: M04; Foundation composition, M02 registry queries, M05 observations, A01 read-only adapter, P02 API rendering.
- Requirements: `FR-ACC-003`, `FR-COL-001`, `FR-COL-003`, `FR-COL-004`, `FR-COL-005`, `FR-COL-008`, `FR-OPS-002`.
- Acceptance evidence: bounded `AC-OPS-002`, `AC-OPS-006`, `AC-HIST-001`, `AC-UI-005`; API isolation supports `AC-OPS-003`, without claiming multi-adapter failure verification.
- Contracts: M02/M04/M05/A01/P02 V1, `CTR-REG-002/003/005`, `CTR-COL-002/004/006`, `CTR-CAP-001/003/004`, `CTR-PROV-004/008`, `CTR-UI-001`, schema and HTTP V1 unchanged.

## Delivered behavior

The authenticated service polls the one eligible, unambiguous, owner-confirmed
Claude default profile independently of the browser. It reads account, profile,
resource, and organization relationships from the admin registry. Enabling or
disabling monitoring controls eligibility for subsequent attempts. The source
minimum is 300 seconds between actual attempt starts; time spent finishing a
run does not extend that source constraint. Durable M04 runs preserve that
interval across service restarts. Failed,
blocked, or incomplete attempts are not automatically retried against the
adapter's no-retry advice. A failed observation never becomes fresh telemetry.

The account capacity panel refreshes current capacity and quota every 30
seconds through the generated API, retaining history pages already loaded.
Refresh failure preserves the last observations with an explicit message.
M04 admission, A01 provider parsing, and M05 transactional persistence retain
source/version/freshness and collection lineage. An in-flight bounded provider
read is drained at service shutdown. Startup checkpoints retained AgentMonitor
SQLite journals under the exclusive service lock before compatibility checking;
it applies no migration or DDL.

## Red, Green, and refactor

| Scenario | Real boundary and evidence |
|---|---|
| Automatic service collection | Red: production lifespan against the owner DB failed because the enabled account received no new quota (`1 failed in 46.01s`). Green: `AUTO-CLAUDE-POLL` returned `11 passed in 52.70s`, including real installed Claude, M04/M05 SQLite persistence, unchanged registry metadata, source interval after restart, and empty-service restart. |
| SQLite journal recovery | The first collecting implementation saved real fresh quota but failed its second startup with `database_locked`. The same live scenario passed after the exclusive-lock checkpoint; a second real empty file SQLite restart scenario also passed. |
| Automatic browser refresh | Red: built Chrome `accounts_admin` timed out after 35 seconds at `automatic_capacity_refresh`. Green: the same scenario observed a real subsequent capacity GET with HTTP 200 after the new production build. No request interception or generated telemetry. |
| Pure scheduling policy | Nine domain tests cover first attempt, the 299/300-second boundary, partial success, failure/incomplete blocking, and invalid input pairs. Constructed inputs have no I/O. |
| Fleet freshness boundary | Red: the full M4 gate returned `244 passed, 2 failed` when one healthy account's windows expired before its next permitted read; the fleet lineage assertion saw `stale` and the organization aggregate truthfully reported `missing`. A new pure assertion then failed because cadence was anchored to run completion. Green: cadence is anchored to the persisted attempt start, the scheduler checks once per second, the focused collection suite returned `13 passed, 3 skipped`, and the unchanged real M4 gate returned `246 passed` plus all three live browser verifiers. The provider's 300-second minimum and five-minute observation freshness policy are unchanged. |
| Regression | Registry/admin HTTP, collection repository, runtime recovery, and pure collection tests: `39 passed in 12.26s`. |
| Static/build refactor | `AUTO-QUALITY` passed lint, format, typing, declared module boundaries, generated artifacts, locked inputs, and production build. OpenAPI regeneration changed provenance hashes only; the 39 operations and schema digest are unchanged. Cadence remains behind M04's application boundary. |

The owner DB readback on 2026-09-28 showed two fresh quota windows, latest
collection at **08:43:19 UTC**. The enabled account retained its identity,
name, monitoring preference, record version, and SDK membership. No account
address or credential was written into code or this evidence. These session
results do not invent a historical terminal artifact for the earlier Reds.

The final refactor rerun returned **11 passed in 304.30s (0:05:04)** from
`AUTO-CLAUDE-POLL`, spanning the genuine source interval. `accounts_admin`
passed again against the final production build. The automation runner's 44
tests and planning validator's 12 tests passed, as did `AUTO-DOCS-CHECK`,
`AUTO-PLAN-CHECK`, and `AUTO-GIT-PREFLIGHT`. The permanent local service was
restarted afterward; `/accounts` returned HTTP 200 and the source remained in
its cadence wait. No six-account or full-release completion is inferred.

## Repeatable verification and operations

Stop the AgentMonitor service using its normal shutdown before running this
gate. It starts the real production lifespan itself. Supply the explicitly
selected non-secret owner data root; missing input returns Blocked.

```bash
AGENTMONITOR_TEST_OWNER_DATA_ROOT=/home/dev/.local/share/agentmonitor \
AGENTMONITOR_TEST_DASHBOARD_PORT=43110 \
backend/.venv/bin/python tools/automation/run.py AUTO-CLAUDE-POLL
```

The gate may wait for the genuine five-minute interval. It does not move the
clock, shorten the source interval, change account preferences, or fabricate
provider data. The permanent loopback dashboard must be restarted afterward
using the [documented local command](../operations/runbook.md#local-claude-dashboard-polling).

## Impact, files, and remaining scope

- Security/privacy: provider-owned profile is read-only; no prompts, responses, credentials, or raw provider payloads are retained. Ambiguous profile association prevents collection. User-controlled provider login is unchanged.
- Migration/license: no schema change, dependency, license change, or breaking API. Existing SQLite checkpoint primitive is reused only for AgentMonitor's DB.
- Files: collector and lifecycle in `backend/src/agentmonitor/composition/`; M04 polling domain/application and SQLite query; live/pure tests; `CapacityPanel.tsx` and its browser scenario; `AUTO-CLAUDE-POLL` implementation/catalog; contract consumer adoption and these linked docs.
- Rollback: normal AgentMonitor stop, previous application commit, normal restart against the unchanged schema. Provider profiles need no restoration.
- Follow-up: dashboard enrollment/binding of new provider profiles, managed official reauthentication, and six-account verification remain separate work. A pending admin record cannot collect until it has a confirmed compatible profile/resource. The current source does not prove a provider email. Failed-source recovery needs a reviewed operation; enabling monitoring does not silently clear a blocked durable run.
- Not Run: installed native-service/platform acceptance, hosted CI, full release security/license artifacts, multiple real Claude profiles, and the full M4/V1 exit gates. This delivery claims the working one-profile dashboard path only.
