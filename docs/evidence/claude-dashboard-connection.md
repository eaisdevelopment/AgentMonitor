# Dashboard Claude connection: intermediate evidence

- Date: 2026-09-28.
- Authority: the owner's instruction to build dashboard authentication under
  M4 `ST-FLEET-001` and the [approved connection change](../plans/integration/claude-managed-account-connection-change.md).
- Status: **Passed for two selected owner-completed dashboard connections**;
  full `ST-FLEET-001` and M4 remain Partial. The owner started official
  browser sign-in and completed authentication; exact managed identity,
  enrollment, monitoring, genuine quota, and the selected canonical gate
  Passed. Universal `AC-TEST-001` is not claimed. Earlier Not Run/Blocked
  entries below are historical and superseded for these selected success
  paths by the owner verification sections.
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
| `ST-FLEET-001` | Partial | Remaining owner account connections and outcomes; six-account enrollment/unavailability matrix and full story gate. |
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

## Owner-completed dashboard verification — 2026-09-28

The owner opened the selected pending SDK account, clicked Connect Claude,
completed Claude's ordinary browser authentication, and reported that
the sign-in window closed. No agent started sign-in or completed provider
authentication for this attempt. No setup terminal was needed.

Authenticated V1 reads then verified a non-null connected flow receipt,
the same selected active account with effective monitoring enabled,
the expected provider identity with managed provenance, and two fresh
quota windows sharing its exact collection-run identity receipt. The
canonical selected gate returned **Passed (exit 0)**:

```bash
python3 tools/automation/run.py AUTO-CLAUDE-CONNECT
```

Its real API/native safeguard suite returned **5 passed in 18.93s**;
the production connection browser scenario Passed; the actual completed
flow/identity/monitoring check Passed; the selected real managed quota
suite returned **4 passed in 5.07s**; and the production V1 API/browser
fresh quota/identity/table verification Passed. Four explicit private
runtime selectors bound the existing owner service, selected account,
and shared local dashboard. They are omitted from this report.

This passes the selected owner-driven connection success path and
supersedes its earlier Blocked result. The managed directory existed
from earlier connection attempts: authentication against a brand-new
empty directory remains separate from this claim. Live wrong-account,
expiry, cancellation, interrupted enrollment, the remaining selected
account outcomes, broad mutation binding, and full M4 remain incomplete.

## Second owner-completed dashboard connection — 2026-09-28

The owner clicked Connect Claude for the remaining selected SDK record
and completed official browser authorization. Its connected flow,
expected native managed identity, active record, effective monitoring,
and two fresh quota windows sharing the exact identity receipt were
verified through V1. `AUTO-CLAUDE-CONNECT` **Passed (exit 0)** for this
selected account: API/native safeguards **5 passed in 18.73s**,
production connection browser Passed, completed-flow check Passed,
real managed quota **4 passed in 5.18s**, and API/browser fresh quota
verification Passed. No terminal setup or agent-performed login occurred.

A subsequent read of all four selected SDK records showed the correct
group, active lifecycle, and effective monitoring for each. Three had
fresh identity/quota lineage; the previously connected first managed
account did not. Its recent durable runs contain real
`usage_deadline_window_conflicting_duplicate` and
`usage_deadline_terminal_marker_missing` failures. A direct real source
test also Failed with `usage_deadline_terminal_marker_missing` after
**20.53s**. This remaining parser/refresh issue is under investigation;
four-account fresh fleet verification and full M4 are not Passed.

## Native quota redraw correction — 2026-09-28

The real failure above exposed cursor redraws being appended to the quota
text rather than overwriting the current terminal surface. A01 now
reconstructs only the bounded 40-row, 160-column current native surface,
discarding scrollback. Only its latest usage segment can supply a reading;
duplicate quota labels on that surface remain ambiguous and rejected.
The existing real managed-identity/quota test supplied the initial Red:
`usage_deadline_terminal_marker_missing`, **1 failed in 20.53s**. The same
test then returned **1 passed in 4.94s** after the correction.

Regression checks on the other managed profiles returned **5 passed in
19.51s** (including genuine unauthenticated managed startup) and **4 passed
in 5.06s**. A read against the protected default profile initially exposed
`usage_deadline_terminal_control_unsupported`. Allowlisted control-only
discovery identified two additional keyboard presentation controls,
`CSI >4m` and `CSI <u`; neither writes screen cells according to the
[xterm control reference](https://invisible-island.net/xterm/ctlseqs/ctlseqs.html)
and [kitty keyboard protocol](https://sw.kovidgoyal.net/kitty/keyboard-protocol/).
After admitting those exact selectors, the real default source returned
at least two quota windows and its independent before/after identity
fingerprints matched. Raw native buffers were discarded; no provider
credentials or conversation content were read or retained.

No new tests were added: the existing real source test exposed the changed
behavior. Requirements `FR-QUOTA-001/002`, `FR-COL-004/007`, and
`FR-SAFE-001/002` govern this A01 correction; selected `AC-LIVE-006/007`
evidence remains bounded by the live gates below. The internal reader keeps
`CTR-PROV-005`, `CTR-REG-006`, `CTR-API-001`, and `CTR-UI-001` V1 unchanged.
Generated provenance includes the new helper; the 44-operation HTTP schema
remains compatible. `AUTO-QUALITY` Passed with 231 formatted files, 220
strictly typed source files, and zero module-boundary violations.

With the corrected service, `AUTO-CLAUDE-MANAGED` **Passed (exit 0)**
against the originally failing managed account: **21 passed in 7.34s**,
then exact identified managed-account/fresh-quota V1 API and production
browser verification Passed. This is the selected managed-account gate,
not a full fleet or M4 completion gate.

The service was reloaded with the final reader. Each account retains its
independent 300-second minimum cadence; historical failed runs remain
failed. No database migration, dependency/license change, provider profile
edit, default logout, or running-agent action occurred. Rollback restores
the previous application build and leaves provider-managed profiles intact.

### Final selected SDK observations

At **18:12:04 UTC**, authenticated V1 reads verified all four selected
SDK records: intended admin name/group, active lifecycle, effective
monitoring, expected exact provider identity, and two fresh quota windows
sharing each account's current service collection-run identity receipt.
The default record retained `protected_default` provenance; the three
additional records retained `managed` provenance. Their latest native
service runs all succeeded, completing between **18:08:40** and
**18:11:36 UTC**. This is a current read of four selected SDK records,
not six-account acceptance or a full fleet completion gate.

Against the final reader/service, the latest support-account
`AUTO-CLAUDE-CONNECT` **Passed (exit 0)**: API/native safeguards
**5 passed in 18.48s**, production connection browser Passed,
owner-completed flow/identity/monitoring verification Passed,
real selected managed quota **4 passed in 4.98s**, and fresh exact
V1 API/browser lineage verification Passed. No new owner sign-in
was required. `AUTO-DOCS-CHECK` (257 Markdown files), synchronized
planning validation, local Git preflight, and `git diff --check`
Passed for the correction. Remaining live flow cases and full M4
remain incomplete as listed above.

### Redraw correction changed files

```text
backend/src/agentmonitor/adapters/providers/claude/subscription/source.py
backend/src/agentmonitor/adapters/providers/claude/subscription/terminal_screen.py
contracts/openapi/agentmonitor-v1.json
docs/README.md
docs/evidence/claude-dashboard-connection.md
docs/evidence/claude-managed-account-connection.md
docs/plans/integration/claude-managed-account-connection-change.md
frontend/src/generated/api/index.ts
tooling/foundation/openapi_client.py
```
