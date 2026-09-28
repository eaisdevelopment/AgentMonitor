# Dashboard Claude connection: intermediate evidence

- Date: 2026-09-28.
- Authority: the owner's instruction to build dashboard authentication under
  M4 `ST-FLEET-001` and the [approved connection change](../plans/integration/claude-managed-account-connection-change.md).
- Status: **Partial**. Real HTTP safeguards, browser controls, and managed
  native quota checks Passed. A newly authenticated profile connected from
  the dashboard remains **Not Run**; the selected live completion gate is
  not Passed. Full M4 and universal `AC-TEST-001` are not claimed.
- Ownership: M02 coordinates registry enrollment; A01 owns Claude behavior;
  M03 publishes `CTR-PROV-007` V1; P01/P02 and Foundation compose the workflow.
- Requirements: `FR-ACC-001/003/005/006`, `FR-AUTH-002/003/004/005/006`,
  `FR-SAFE-001/002`, `FR-UI-001/002/004/005/006`, `FR-QUOTA-001/002`.
  Bounded UI/safety evidence supports `AC-UI-002/003/005`; new-flow
  `AC-LIVE-006/007` acceptance remains incomplete.
- Contracts: additive `CTR-PROV-007` V1 command/status port and three V1 HTTP
  connection operations; existing `CTR-REG-006`, `CTR-API-001`, and
  `CTR-UI-001` V1. M01 grants `write:reauth` to the authenticated browser
  administrator; bearer-token scopes remain unchanged.

## Owner workflow and limits

The owner opens a pending Claude account, confirms its intended email, and
clicks **Connect Claude**. That explicit action starts the official native
login against a private managed profile and opens an ordinary Chrome window.
The owner completes authentication on Claude's page. The dashboard polls safe
status and verifies the returned identity before registry binding and monitoring
enablement. Account labels and organization membership remain admin CRUD data.
No terminal command or terminal setup is required for this monitoring path.

POST requires a browser session, CSRF, account version, and idempotency key;
GET is inert. DELETE cancels the owned attempt. One sign-in runs at a time.
Closed receipt fields permit replay and mark interrupted attempts cancelled
on restart. Default profiles and ordinary active-account reauthentication
are rejected. A separate **Finish connection** control can resume a partially
enrolled, identity-matched managed account; that recovery path is **Not Run**
live. Connected identity and enabled monitoring precede quota: the page waits
for a genuine scheduled reading and its matching identity receipt.

## Red, Green, and native evidence

| Boundary | Evidence |
|---|---|
| Real SQLite/Uvicorn connection API | Initial Red: missing pending status returned `404`, `1 failed in 1.82s`. Green: `2 passed in 5.01s`; anonymous, CSRF, missing/stale version, missing key, hostile origin, and invalid email requests remain inert. A real unsafe managed root is rejected; safe receipts replay after restart. |
| Production browser and V1 client | Initial Red at `pending_connect_control`; a later archive-panel Red exposed a duplicate React key. Final `claude_connection` scenario Passed. It exercises actual controls and HTTP responses without starting provider sign-in. |
| Native process/filesystem safeguards | `2 passed in 2.03s`: an existing opener symlink target stays untouched; actual service-parent death ends its owned native child. |
| Fresh unauthenticated managed quota | Red: `usage_blocked_onboarding` instead of `claude_reauthentication_required`, `1 failed in 14.27s`. After the managed-only presentation flag, Green: `1 passed in 14.57s`. No authentication or conversation was started. |
| Selected real managed quota comparison | Normal native `/usage` at **15:29:11.992111 UTC**, then with `IS_DEMO=1` at **15:29:16.172630 UTC**. Both parsed `current_session` and `current_week_all_models`; exact percentages and reset displays matched. Managed/default identity fingerprints were unchanged before/after. |
| Newly authenticated dashboard profile | **Not Run**. Provider sign-in, fresh-profile quota, and selected live gate still require the owner's explicit dashboard action and browser authentication. |

Canonical commands for the executed local boundaries:

```bash
backend/.venv/bin/python -m pytest -q --tb=short \
  backend/tests/integration/api/test_provider_connection_routes.py
backend/.venv/bin/python -m pytest -q --tb=short \
  backend/tests/adapters/providers/claude/live/test_connection_process.py
backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py \
  claude_connection --no-build
```

The native comparison used admitted Claude **2.1.282** and the existing
allowlisted parser. Raw output was discarded. Fresh isolated discovery also
showed that `--init-only` exits successfully while subsequent ordinary startup
still shows theme onboarding. Its documented purpose is
[initialization hooks](https://code.claude.com/docs/en/cli-reference).
The dashboard does not invoke it.

Claude documents [`IS_DEMO`](https://code.claude.com/docs/en/env-vars) as a
presentation setting that suppresses onboarding and hides terminal identity.
Only managed quota subprocesses receive it; independent native identity checks
retain their normal environment. The live comparison above establishes actual
quota equivalence for the selected existing profile. It does not establish
newly authenticated fresh-profile acceptance.

## Selected completion gate

```bash
python3 tools/automation/run.py AUTO-CLAUDE-CONNECT
```

Supply the four explicit non-secret selectors:
`AGENTMONITOR_TEST_OWNER_DATA_ROOT`, `AGENTMONITOR_TEST_MANAGED_ACCOUNT_ID`,
`AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT`, and
`AGENTMONITOR_TEST_DASHBOARD_ORIGIN`. The gate never starts sign-in. It checks
the local safeguards/browser scenario, a real completed dashboard flow, active
monitoring, and fresh managed identity/quota lineage. Missing owner interaction,
flow receipt, or fresh quota returns non-success. This gates one selected
connection, not M4.

## M4 scope still outstanding

| Story | Status | Remaining artifacts or acceptance |
|---|---|---|
| `ST-FLEET-001` | Partial | Owner-completed dashboard connection and remaining account outcomes; six-account enrollment/unavailability matrix and full story gate. |
| `ST-FLEET-002` | Partial | Organization/global/provider capacity aggregation, forecasts, revisioned membership coverage, and fleet collection/history/aggregation verification. Account quota/history and independent cadence exist. |
| `ST-FLEET-003` | Partial | Organization runtime/capacity views, reliable mixed-account process ownership, representative Claude hierarchy verification, and fleet browser acceptance. Account/history/session/process views exist. |
| `ST-ALERT-001` | Not implemented | Alert contracts, policy/consumer/repository, three M07 migrations, and lifecycle/persistence tests. |
| `ST-ALERT-002` | Not implemented | Alert rules/console routes, generated operations, pages, and HTTP/browser tests. |
| `ST-OPS-001` | Not implemented | Operations contracts/services/routes, diagnostics UI, operational tests, and canonical M4 acceptance gate. |

The six-account acceptance target is not an application limit; accounts and
organizations remain dynamic admin records. Live wrong-account, expiry,
cancellation during owner sign-in, and partial-enrollment recovery through this
new workflow remain Not Run. Process activity and ownership stay unresolved
where evidence is absent.

## Impact, files, and handoff

Provider credentials remain provider-managed. Passwords/codes/OAuth URLs never
enter API responses, receipts, logs, documentation, or screenshots. Browser
receipts retain opaque IDs/fingerprints, timestamps, versions, and closed states.
Unsafe roots and opener symlinks fail closed. Native children have bounded
ownership/lifetime; monitored agents are untouched. No provider file is directly
edited, credential copied, or default profile logged out. The UI uses only the
generated V1 client. No database migration or dependency/license change occurs.

Changed areas: A01 authentication/browser/process support and managed quota
environment; M03 connection contract; M01 browser authorization; Foundation
coordinator/bootstrap; P01 connection transport; P02 account connection panel
and wrapper; generated artifacts; real tests; canonical automation and linked
docs. Rollback uses the previous application build without moving or deleting
provider credential stores. Next integration step is the owner's deliberate
dashboard connection, followed by the selected live gate and remaining M4 work.

## Local delivery verification

Latest combined API/native safeguard run: **5 passed in 18.65s**.
The canonical connection gate repeated those boundaries with **5 passed
in 20.08s**, followed by the production `claude_connection` browser
scenario Passed. Static `AUTO-QUALITY`, synchronized planning validation,
`AUTO-DOCS-CHECK` (257 Markdown files), and local Git preflight Passed.
The service was reloaded with the built connection controls. A safe
read against the owner dashboard returned `401`: its browser session
has expired, so owner sign-in is required before the selected connection.

The broader automation-runner test suite initially found the new catalog
and boundary omissions, which were corrected. Its independent mutation
equivalence binding remains Failed: the existing runtime contract hash
differs from the runner's frozen hash. This increment changes neither
that contract nor its mutation equivalence declarations and does not
claim that broad suite Passed. Both changed catalog/clean-clone checks
Passed on their focused rerun. Live recovery and its individual Red
evidence remain Not Run; implemented retry handling is not live
recovery acceptance.

The selected `AUTO-CLAUDE-CONNECT` execution returned **Blocked (exit 3)**
after its local safeguard/browser checks Passed: an owner-completed
connection and fresh identity receipt are still required. No sign-in
was started by that command.

### Exact changed files

```text
backend/src/agentmonitor/adapters/providers/claude/authentication/browser.py
backend/src/agentmonitor/adapters/providers/claude/authentication/owned_process.py
backend/src/agentmonitor/adapters/providers/claude/authentication/reauthentication.py
backend/src/agentmonitor/adapters/providers/claude/subscription/source.py
backend/src/agentmonitor/api/problem.py
backend/src/agentmonitor/api/v1/dependencies.py
backend/src/agentmonitor/api/v1/router.py
backend/src/agentmonitor/api/v1/routers/provider_connections.py
backend/src/agentmonitor/api/v1/schemas/providers.py
backend/src/agentmonitor/composition/bootstrap.py
backend/src/agentmonitor/composition/claude_dashboard_connection.py
backend/src/agentmonitor/composition/claude_managed_connection.py
backend/src/agentmonitor/contracts/provider_system_v1.py
backend/src/agentmonitor/modules/identity_access/application/authorization.py
backend/tests/adapters/providers/claude/live/test_connection_process.py
backend/tests/integration/api/test_provider_connection_routes.py
contracts/openapi/agentmonitor-v1.json
docs/README.md
docs/engineering/completion-and-automation-gates.md
docs/evidence/claude-dashboard-connection.md
docs/modules/react-dashboard.md
docs/operations/runbook.md
docs/plans/contract-adoption.toml
docs/plans/contract-baseline.toml
docs/plans/integration/claude-managed-account-connection-change.md
docs/plans/integration/cs1-final-readiness-audit.md
docs/plans/integration/cs1-full-plan-synchronization.md
docs/plans/plan-baseline.toml
frontend/src/app/dashboard.css
frontend/src/features/accounts/AccountPage.tsx
frontend/src/features/accounts/ClaudeConnectionPanel.tsx
frontend/src/generated/api/index.ts
frontend/src/shared/api/client.ts
frontend/tests/browser/p02/claude_connection.mjs
frontend/tests/browser/p02/run_browser.py
tooling/foundation/check_boundaries.py
tooling/foundation/openapi_client.py
tools/automation/implementations/auto_claude_connect.py
tools/automation/routines.toml
tools/automation/run.py
tools/automation/test_run.py
tools/planning/validate_plans.py
tools/providers/verify_claude_dashboard_connection.mjs
```
