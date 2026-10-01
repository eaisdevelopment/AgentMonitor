# V1 M4 completion evidence

- Date: 2026-09-29.
- Status: **Passed** by the canonical `AUTO-M4-EXIT` command against the
  installed owner environment.
- Program reconciliation (2026-10-01): this is a genuine standalone M4 gate
  pass. The [current implementation-status overlay](v1-implementation-status-v1.json)
  records formal V1-M3 acceptance as Blocked, so M4's declared M3 program
  prerequisite remains unresolved; no acceptance decision or exact
  tested-revision binding is inferred here. The fleet verifier proves six
  selected monitored registry/profile connections. It does not prove six
  distinct provider identities; the current overview has five genuine identity
  quota rows because two connections report the same identity.
- Stories: `ST-FLEET-001`, `ST-FLEET-002`, `ST-FLEET-003`,
  `ST-ALERT-001`, `ST-ALERT-002`, `ST-OPS-001`.
- Plan: [approved executable completion change](../plans/integration/m4-completion-change.md)
  plus the linked approved M4 module change packets.

## Delivered scope and contracts

M4 now provides organization and account administration, six-profile Claude
monitoring, current native quota and retained history, organization aggregates,
conservative forecasts, account-to-runtime drill-down, alert rule/lifecycle
views, and operations health/diagnostics through the authenticated versioned
API and built dashboard. The installed fleet contains six owner-selected real
Claude profile connections in two organizations and five distinct reported
identity quota rows. Account records remain administrator CRUD data; no account
address is compiled into the application. The duplicate reported identity still
requires owner review before `AC-LIVE-001` can claim six distinct intended
accounts.

The compatible V1 surface includes `CTR-REG-*`, `CTR-COL-002/004/006/007`,
`CTR-CAP-001/003..009`, `CTR-ALERT-001..005`, `CTR-EVT-001`,
`CTR-OPS-001/002/004/006`, `CTR-DB-001`, `CTR-API-001` and `CTR-UI-001`.
The generated OpenAPI/client publishes 66 operations with artifact SHA-256
`4c99fd499b404f97235a6fbf6a3c60418919b1b2016226daf0ab672336a085be`.
Database head is the additive `v1_0707` chain.

## Red, Green and canonical result

Module evidence records the focused contract/domain/persistence/API/UI Reds and
Greens. The final integration run first reached **244 passed, 2 failed**: a
healthy account crossed its genuine five-minute freshness boundary, so the
fleet test saw `stale` and the aggregate correctly reported `missing`. A new
pure scheduling assertion then failed with **1 failed, 10 passed** because the
source minimum interval was measured after run cleanup. M04 now measures the
unchanged 300-second provider interval between actual attempt starts and checks
due work once per second. The focused collection run returned **13 passed,
3 skipped**; those three are opt-in live scenarios outside that focused command.

The exact final command was:

```bash
AGENTMONITOR_TEST_OWNER_DATA_ROOT=/home/dev/.local/share/agentmonitor \
AGENTMONITOR_TEST_DATA_ROOT=/home/dev/.local/share/agentmonitor \
AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT=http://127.0.0.1:49391 \
AGENTMONITOR_TEST_DASHBOARD_ORIGIN=http://127.0.0.1:43110 \
AGENTMONITOR_TEST_M4_OWNER_OUTCOMES=/home/dev/.local/share/agentmonitor/m4-owner-outcomes.json \
python3 tools/automation/run.py AUTO-M4-EXIT
```

It passed **257 tests with zero skips**, then passed:

- the real fleet browser verifier for six selected registry connections, two
  organizations, current identity/quota lineage, history, runtime scope and
  account activity;
- the real alert browser verifier with one genuine derived alert and history;
- the real operations browser verifier with eleven component rows;
- `AUTO-PLAN-CHECK`, `AUTO-QUALITY`, `AUTO-BUILD`, `AUTO-MUTATION`,
  `AUTO-DOCS-CHECK` and local `AUTO-GIT-PREFLIGHT`.

Mutation evidence covered 628 critical-policy mutants: 621 killed and seven
preapproved exact-bound equivalents, with no untested or non-equivalent
survivor. The final production frontend build and strict Python typing passed.

## Installed migration and live operation

`AUTO-MIGRATE` upgraded the private installed database from `v1_0603` through
the exact `v1_0700..v1_0707` chain while holding the service lock. It made and
verified an owner-only SQLite backup, then passed schema, integrity, foreign-key,
checksum and file-mode postchecks. The service restarted on loopback and the
owner-authorized private LAN address. Five managed profiles recovered their
identity receipts through read-only fingerprint re-attestation; the protected
default recovered on its next genuine quota collection. All six profile records
were verified for the final gate.

## Security, privacy, migration, license and documentation impact

- Provider profiles remain read-only. M4 does not log or persist prompts,
  responses, source content, arbitrary environment values, credentials, tokens,
  passwords or one-time codes.
- The private owner outcome matrix, database, connection state and service
  configuration remain outside Git with owner-only modes. A repository scan
  found no SDK or EAIS account address literal and no private runtime artifact
  in the worktree change set.
- Migrations are additive and preserve historical rows. Existing provider and
  registry identities are not rewritten or backfilled.
- No dependency or license was added. The existing locked Python/Node inputs
  and notices checks passed.
- Module, integration-plan, operation, migration and automation documentation
  was updated. Earlier `interim` records remain historical and are superseded
  for the canonical M4 result by this record.

## Operational limits after M4

The protected default profile does not yet have a durable exact auth-status
fingerprint claim. After a service restart it can remain identity-unresolved
until its next genuine due quota read; automatic owner-confirmed claim creation
would require a separate M02 contract and policy. AgentMonitor V1 remains
read-mostly and does not switch, route, stop or restart a running Claude agent.
Naturally occurring alert recovery, aged retention, hosted CI and full V1
release acceptance are not claimed by this M4 result. Six distinct intended
Claude identities are also not claimed until the genuine duplicate profile
identity is owner-dispositioned.
