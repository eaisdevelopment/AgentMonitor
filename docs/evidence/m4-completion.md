# V1 M4 completion evidence

- Historical standalone run: 2026-09-29.
- Current-revision closure: **Passed and owner-accepted** on 2026-10-07.
- Assessed implementation revision:
  `9dbb765531f05f2ae1e8174383cc0ff8b7cb8072`.
- Current receipt:
  [sanitized M4 gate receipt](m4-current-gate-receipt-2026-10-07.json).
- Acceptance:
  [owner live countersignature](m4-owner-live-countersignature-2026-10-07.md)
  and [active M4 acceptance record](v1-m4-acceptance-status-v1.json).
- Stories: `ST-FLEET-001`, `ST-FLEET-002`, `ST-FLEET-003`,
  `ST-ALERT-001`, `ST-ALERT-002`, `ST-OPS-001`.
- Plan: [approved executable completion change](../plans/integration/m4-completion-change.md)
  plus the linked approved M4 module change packets.

## Current-revision closure and acceptance

The canonical gate restarted the dashboard from the exact clean assessed
revision and verified six selected accounts as six distinct current Claude
identities in two organizations. Every account received a fresh post-restart
quota run with matching current/history lineage. The same fleet metadata was
present before and after the run, browser/API mutations were zero, and one
owner-confirmed current Claude process supplied the guarded runtime witness.

`AUTO-M3-TEST` passed 303 tests. The M4 selected suite passed 302 tests with
zero skips, and the fleet policy checks passed 8/8. The built Overview, alert,
and operations browser checks passed, followed by planning, quality, mutation,
documentation, and local Git preflight. The gate wrote its private create-once
receipt only after all fourteen required lanes passed. The owner then reviewed
this result and explicitly answered **confirm**, accepting the full approved
V1-M4 scope.

The final scheduler blocker was handled Red/Green before the accepted run. A
real isolated copy of the owner database first reproduced
`collection_generation_conflict`: registry revision 48 and the prior quota
policy both used target generation 48 while the reviewed manifest had changed.
M04 now assigns the reviewed quota policy its own generation, yielding target
generation 49 without weakening same-generation policy rejection, active-lease
protection, or fencing. The focused suite passed 25 tests, and a genuine
read-only Claude collection against a private database copy proved the 48 to 49
transition while preserving prior history.

The compatible V1 contracts and database head remain unchanged. The generated
OpenAPI/client still publishes 66 operations, with current artifact SHA-256
`cbc2b7a1a67dfc8bf4915d6267368e915e2b9118d2b6e29c29ee9e48ca45be15`.
No dependency, license, schema, migration, provider-write, or process-control
capability was added by the final correction or closure records.

## Historical standalone result — 2026-09-29

The following sections preserve the earlier standalone run as historical
evidence. At that checkpoint M3 acceptance and the duplicate reported identity
were unresolved, so it did not constitute the current formal acceptance above.

### Delivered scope and contracts

M4 provided organization and account administration, monitoring for six
selected Claude profile connections, current native quota and retained history,
conservative forecasts, account-to-runtime drill-down, alert rule/lifecycle
views, and operations health/diagnostics through the authenticated versioned
API and built dashboard. At that checkpoint the installed fleet contained six
owner-selected real Claude profile connections in two organizations and five
distinct reported identity quota rows. Account records remained administrator
CRUD data; no account address was compiled into the application. The duplicate
reported identity still required owner review before `AC-LIVE-001` could claim
six distinct intended accounts at that checkpoint.

The compatible V1 surface includes `CTR-REG-*`, `CTR-COL-002/004/006/007`,
`CTR-CAP-001/003..009`, `CTR-ALERT-001..005`, `CTR-EVT-001`,
`CTR-OPS-001/002/004/006`, `CTR-DB-001`, `CTR-API-001` and `CTR-UI-001`.
The generated OpenAPI/client publishes 66 operations with artifact SHA-256
`4c99fd499b404f97235a6fbf6a3c60418919b1b2016226daf0ab672336a085be`.
Database head is the additive `v1_0707` chain.

### Red, Green and historical canonical result

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

### Installed migration and live operation

`AUTO-MIGRATE` upgraded the private installed database from `v1_0603` through
the exact `v1_0700..v1_0707` chain while holding the service lock. It made and
verified an owner-only SQLite backup, then passed schema, integrity, foreign-key,
checksum and file-mode postchecks. The service restarted on loopback and the
owner-authorized private LAN address. Five managed profiles recovered their
identity receipts through read-only fingerprint re-attestation; the protected
default recovered on its next genuine quota collection. All six profile records
were verified for the final gate.

### Security, privacy, migration, license and documentation impact

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

## Operational limits after accepted M4

The protected default profile does not yet have a durable exact auth-status
fingerprint claim. After a service restart it can remain identity-unresolved
until its next genuine due quota read; automatic owner-confirmed claim creation
would require a separate M02 contract and policy. AgentMonitor V1 remains
read-mostly and does not switch, route, stop or restart a running Claude agent.
Naturally occurring alert recovery, aged retention, hosted CI and full V1
release acceptance are not claimed by this M4 result. The historical duplicate
identity blocker is closed by the accepted current gate's six distinct current
identity witness.
