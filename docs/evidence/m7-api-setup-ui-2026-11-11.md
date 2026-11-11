# M7 API account setup UI: bounded P02 handoff

- Outcome: Partial; T002 and M7-A01 remain open.
- Module/plan: P02, focused M7 execution plan 1.1.0, T002/P02 initial setup slice.
- Requirements: FR-ACC-001/002/004/006; setup prerequisite for
  FR-ACC-003 and FR-BUDGET-001/006. Acceptance: M7-A01 and bounded
  AC-UI-002/003/004/005 behavior; no full acceptance claim.
- Contracts: generated API V1 RegisterAccountInputV1 and AccountViewV1
  additive `initial_connection_purpose`; M02 CTR-REG-014 billing metadata V1
  and generated GET/POST billing-connection operations.
- Worktree: `m7-api-budgets`, baseline `6a87630`, uncommitted scope below.
- Recorder/date: delegated P02 agent, 2026-11-11 UTC.

## Observable result and compatibility

Accounts has an explicit Add API billing account mode with Anthropic API,
OpenAI API and Ollama Cloud labels mapped to the existing provider keys.
An owner supplies a friendly name and dashboard organization or Ungrouped.
Creation submits API intent through the shared generated-client adapter and
opens the actual returned account ID. API intent persists across reload.

API-only initial records read real billing status and offer the server-admitted
Add API billing connection action. Optional scope metadata is stored through
the real API; blank scope remains unresolved. Saved bindings show actual
pending lifecycle, disabled monitoring and scope evidence. Scope metadata does
not claim credential access or verified provider identity. They do not mount
subscription connection, quota, agent activity, or session-history components,
and their account cards offer no subscription Connect action. Existing
subscription records also have a separate billing metadata panel, preserving
their subscription controls. It is collapsed under API billing connection,
after activity and history; API-only accounts keep setup visible as their
primary content. No separate count request is made. Ollama respects the server prohibition on adding
a separate binding and explains that the existing cloud flow is required. Account naming,
organization assignment, and archive controls remain available. The page
explains that credentials belong on the computer hosting AgentMonitor, under
its service user; there is no key or email input in API setup.

Existing null-purpose records retain their subscription behavior. The optional
fourth shared `registerAccount` argument defaults to null and omits the new
request field for old callers, preserving existing request semantics. Billing POST uses the status response account version for If-Match and a new
idempotency key; success triggers authoritative GET rather than fabricated
local connection state. Read/write failures have a refresh action. No
generated files, backend code, contracts, schemas or migrations changed in
this delegated UI scope.

## Scope and files

- `frontend/src/features/accounts/AccountPage.tsx`: creation mode, returned-ID
  navigation, API-only initial routing, truthful pending copy and card actions.
- `frontend/src/features/accounts/BillingConnectionPanel.tsx`: real status,
  conditional metadata creation, pending scope evidence, errors and refresh.
- `frontend/src/features/accounts/providerPresentation.ts`: API product labels.
- `frontend/src/shared/api/client.ts`: root-authorized optional purpose argument
  and generated billing status/create wrappers.
- `frontend/tests/browser/p02/accounts_admin.mjs`: real browser scenario extended
  for API creation and persistence, then existing subscription regression.
  The old Provider key locator was corrected to the existing Provider label.
- This evidence file. Concurrent root/backend/automation changes were preserved.

## Test inventory and Red evidence

| Scenario | Boundary | Result |
|---|---|---|
| Initial browser invocation | Local build toolchain | Blocked: no worktree Vite executable; not behavioral Red |
| API creation before production edit | Built Chrome, real HTTP/IAM and migrated temporary SQLite | Expected Red |
| API creation, returned-ID route, reload and separate subscription regression | Same real boundary | Passed |
| Real billing status/create/reread, scope persistence, mixed metadata and Ollama restriction | Same real boundary | Passed |
| Strict TypeScript | Frontend and generated-client consumption | Passed |
| Full credential enrollment, provider verification and mixed resources | Real billing contracts/provider | Not Run in this slice; still required |

The first command without temporary admitted tooling failed with
`P02 BROWSER: FAILED — production_build`; direct build reported
`sh: 1: vite: not found`. This was resolved by reusing installed admitted tools,
without installing dependencies.

At 15:09 UTC, before production UI changes, the existing canonical browser
runner failed at `create_api_billing_account` with:

```text
locator.click: Timeout 30000ms exceeded.
waiting for getByRole('button', { name: 'Add API billing account', exact: true })
```

This is the expected missing-action Red, after real dashboard login and real
organization creation on a fresh isolated installation.

After root extended this task to real billing metadata, the first new test run
was Blocked before the browser by `SchemaCompatibilityError:
migration_catalog_invalid` while the root admitted migration 0731. No
production metadata UI was added before the next behavioral Red.

At 15:16 UTC, after migration and port integration, the real browser created
an API account but failed at `create_billing_connection`:

```text
locator.fill: Timeout 30000ms exceeded.
waiting for getByLabel('Provider billing scope (optional)')
```

This missing scope/control is the second meaningful Red, before adding the
real billing metadata panel.

## Green and execution command

At 15:11 UTC, strict TypeScript and the real built-browser scenario exited 0:

```text
P02 ACCOUNTS ADMIN: PASSED — real API, SQLite, and built browser
P02 BROWSER: PASSED — accounts_admin
```

The scenario asserts the real HTTP 201 creation response, API intent,
disabled monitoring and unresolved identity, returned account-ID URL, pending
API detail after reload, and absence of subscription controls. It then checks
existing subscription rename, archive/restore, and automatic capacity refresh.

At 15:12 UTC the final first-slice rerun also passed keyboard activation of
the API mode, all three provider choices, no email/password/agent section,
and the API page at 390px without horizontal overflow. Strict TypeScript,
the rebuilt real browser scenario and the existing provider-presentation pure
regression all exited 0.

At 15:19 UTC, after adding real metadata controls, strict TypeScript and the
rebuilt browser scenario again exited 0 with the same two browser pass lines.
The expanded scenario asserts real billing POST 201, matching account
If-Match, presence of idempotency key, pending lifecycle, disabled monitoring,
owner-asserted scope, authoritative status after creation and scope persistence
after reload. It creates a second actual billing resource with unresolved scope
on a null-purpose subscription record and then exercises its retained account
activity, rename, archive/restore and capacity history. A real Ollama API-intent
record reports the existing-cloud-flow restriction with no Add binding action.
No provider access or connected state is claimed by these metadata assertions.
The provider-presentation pure regression and scoped `git diff --check` also
passed. The root layout review then identified and corrected the expanded
subscription billing panel as recorded below.

### Compact subscription layout correction

Root review found that the new expanded billing form displaced existing
subscription activity. The browser scenario was extended before the fix to
require the subscription form to be initially hidden, then expand API billing
connection and perform the same real mixed metadata creation.

At 15:20 UTC, the rebuilt real browser failed as expected:

```text
P02 ACCOUNTS ADMIN: FAILED — subscription_billing_collapsed:
Expected values to be strictly equal: true !== false
```

The correction keeps API-only setup in primary view and places the existing
subscription billing panel in a native collapsed details section below main
activity/history, before account settings. It introduces no extra query or
fabricated count.

At 15:22 UTC, strict TypeScript and the rebuilt real `accounts_admin` browser
scenario exited 0. The subscription Add form was hidden initially, expanding
the native section exposed it, and real mixed metadata creation plus the
remaining API-only, subscription, reload, responsive and Ollama checks passed.
Scoped `git diff --check` also passed. No production changes followed this Green.

Reproducible command from the worktree, using the existing guarded tool helper:

```bash
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python - <<'PY'
import subprocess
import sys
from tools.automation.implementations.auto_m6_exit import _temporary_tool_environment
with _temporary_tool_environment():
    result = subprocess.run(['npm', '--prefix', 'frontend', 'run', 'typecheck'], check=False)
    if result.returncode == 0:
        result = subprocess.run([sys.executable, 'frontend/tests/browser/p02/run_browser.py', 'accounts_admin'], check=False)
    if result.returncode == 0:
        result = subprocess.run(['node', 'frontend/tests/pure/provider-account-presentation.mjs'], check=False)
raise SystemExit(result.returncode)
PY
```

The helper removes only tool links it created. The runner builds production
assets, creates a fresh migrated temporary database and local IAM session,
starts a real ephemeral loopback HTTP service, and launches real Chrome.
Only administrator metadata is created; there is no seeded provider telemetry.

## Security, operations and residual work

No dependency, license, migration, service configuration or owner-runtime
change. No provider calls or protected credential/profile inspection. No
network interception, mocks, fakes, recorded responses, placeholder metrics,
test-only production branches or disabled assertions. The isolated IAM password
uses the existing private stdin channel and is not recorded in evidence.

The panel consumes real billing status and persists real metadata, but does
not imply working credentials. No setup command or verification action is
invented. Root owns the next integration: local credential setup, checking
access, and independent API monitoring.
Replace the initial-purpose-only selection with published resource capabilities
when mixed-resource setup is available, including API-origin accounts which
later gain a subscription connection. Existing null-purpose subscription
sections remain intact with separate pending billing metadata now; full
provider-connected mixed-resource verification is Not Run.

Provider access, local key custody, LAN enrollment, actual billing collection,
Overview/detail/history, forecast and the M7 exit gate remain outside this
bounded evidence. It does not establish T002 or M7 completion.
