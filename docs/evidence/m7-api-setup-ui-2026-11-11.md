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

## Credential status increment: CTR-REG-014 1.1.0

This bounded T002/P02 follow-up consumes the root-published optional
`credential_status` on AccountBillingConnectionsV1. It supports M7-A01 and
FR-BUDGET-006/FR-ACC-004 without claiming credential enrollment or a first reading.
The baseline was `e544f8c`; root owns the backend, schema and generated-client
changes. This UI follow-up changes only BillingConnectionPanel.tsx, the existing
accounts_admin.mjs scenario and this evidence.

The panel labels actual server states Credential required, Credential entry
pending, Credential stored, and Credential cleanup required. Stored explicitly
does not verify provider access. A cleanup flag adds its warning independently
of the main state, including when a stored active credential remains. Null or
absent status renders no credential-state claim; it never implies Missing.
No credential identifier, generation number, location or value is displayed.
No local command or entry control is invented. The mixed-account panel remains
collapsed below subscription activity until opened by the owner.

### Red

At 15:47 UTC, after root reported real HTTP status Green and generated types
ready, the built Chrome/HTTP/SQLite scenario failed at
`missing_billing_credential`:

```text
locator.waitFor: Timeout 30000ms exceeded.
waiting for getByText('Credential required', { exact: true }) to be visible
```

The scenario had already created an actual API account and billing connection,
then asserted that the real GET response contained `credential_status.state`
equal to `missing`. The failure was the absent UI label, before this production
rendering change. The same scenario checks no inferred Missing before creating
a binding or for the real Ollama null status, persistence after reload, and
the missing credential on the separately attached mixed-account binding.

### Green

At 15:48 UTC, strict frontend TypeScript and the rebuilt real browser scenario
both exited 0:

```text
P02 ACCOUNTS ADMIN: PASSED — real API, SQLite, and built browser
P02 BROWSER: PASSED — accounts_admin
```

The existing API-only, compact mixed-account, metadata persistence,
subscription-management, capacity-refresh and responsive assertions remained
enabled and passed. Scoped `git diff --check` passed. No production change
followed this Green. The temporary-tool context exited and was released back
to root before its subsequent schema-description regeneration.

The existing reproducible command above runs this increment. The root granted
an exclusive temporary-tool window to avoid concurrent guarded-link cleanup.
No temporary network response or lifecycle state was injected.

Stored, pending-entry and cleanup-required browser states are Not Run here:
this slice does not enter credentials or manufacture lifecycle records to obtain
those states. Their rendering is implemented, but this evidence proves the real
missing/null paths only. Provider access and first-reading verification remain
outside the slice.

## Server-provided local setup command increment

This follow-up to T002/M7-A01 consumes optional AccountBillingConnectionsV1
`local_setup` from the root-owned API: safe host label and exact command. The
baseline was `032a43f`. Only BillingConnectionPanel.tsx, accounts_admin.mjs and
this evidence were edited by the UI delegate; no API wrapper, schema, generated
client, environment, installed service or dependency was changed by this work.

When the server supplies setup, the existing billing panel contains a collapsed
Set up or replace local key section. It identifies the AgentMonitor host and
service user, renders the server command as escaped selectable code, and offers
Copy setup command. It never assembles, modifies or executes the command.
Clipboard failure leaves the exact command available for keyboard/manual
selection. Null/absent setup hides the section. Existing mixed-account billing
remains collapsed below subscription activity.

Returning focus/visibility while status is ready triggers one safe metadata GET,
with an in-flight guard and listener cleanup on unmount. It starts no provider
verification or collection. Existing ready content remains visible during that
read, preserving the expanded setup section. The panel no longer says credential
setup is unavailable when the command exists; access verification remains
explicitly unavailable in this increment.

### Red and intermediate result

At 16:12 UTC, before adding the setup rendering, the rebuilt real browser had
read a nonnull `local_setup.command` and `host_label` from the actual API but
failed at `local_setup_command`:

```text
locator.click: Timeout 30000ms exceeded.
waiting for getByText('Set up or replace local key', { exact: true })
```

The first post-change run reached actual API-to-DOM command equality, successful
copy, real Chrome clipboard-write denial and manual code selection, then failed
at the tab-return harness with `Please use browser.newContext()`. The original
single-page browser convenience context did not support creating another tab.
The test now uses an explicit real browser context; no network or clipboard
function was replaced, and no assertion was removed.

A second run timed out waiting for the status GET on tab return. Real isolated
headless and headed probes showed no blur/focus events: installed Playwright's
`playwright-core/lib/coreBundle.js` automatically enables focus emulation.
The scenario now disables that default override for its own two pages, restoring
native focus rather than injecting a DOM event. A real headless probe then
observed `hasFocus=false` while away, `hasFocus=true` after return, and one native
focus event. The original return-status assertion remains in the scenario.

The next full run still found `hasFocus=true` while away (`true !== false`),
so the test removes the focus override on the final loaded documents immediately
before switching tabs; the earlier pre-navigation reset did not suffice.

### Latest verification: Failed, not Green

At 16:19 UTC, the real built-browser run passed exact API-to-DOM command/host,
successful clipboard copying, real permission-denied fallback, manual command
selection, native blur and the metadata GET on return focus. It then failed at
the existing mixed-account check:

```text
P02 ACCOUNTS ADMIN: FAILED — subscription_billing_collapsed:
locator.waitFor: Timeout 30000ms exceeded.
waiting for getByRole('button', {
  name: 'Add API billing connection', exact: true, includeHidden: true
})
```

The cause of the missing mixed-account action remains unresolved. This is not
a passing full browser scenario, and the assertions were retained. Strict
TypeScript passed during this increment; scoped `git diff --check` passed.
No complete-slice or first-reading claim follows from those narrower results.

The root redirected work to planning and instructed this delegate to finish
current verification/cleanup only. Implementation stopped after this failed
run. The temporary-tool context exited, removed its owned links, and was
explicitly released to root. No test/browser process from the run remains active.

### Resumed mixed-account verification

After root resumed implementation, the existing failed assertion was retained.
The scenario now also awaits the actual subscription-account POST, asserts HTTP
201 and null initial API purpose, and awaits that exact account's billing GET
before testing the collapsed control. The GET must report
`can_add_connection=true` with no existing bindings.

The rebuilt diagnostic run passed the entire scenario. Safe DOM counts showed
the section closed, `aria-busy=false`, one Add billing button, one scope input
and no alert. Temporary diagnostic output was then removed. At 16:31 UTC the
same full scenario, against those already-built production assets, passed again:

```text
P02 ACCOUNTS ADMIN: PASSED — real API, SQLite, and built browser
P02 BROWSER: PASSED — accounts_admin
```

This final follow-up used the existing command with `accounts_admin --no-build`;
it still created a new real SQLite/IAM/HTTP installation and real Chrome context.
All mixed-account, command equality, real clipboard success/denial, manual
selection, native return-focus GET, reload, subscription administration,
capacity refresh and responsive assertions remained active. Scoped
`git diff --check` passed. The exclusive tool window was released after cleanup.

No additional production change was needed in this follow-up. The test had
previously synchronized only to Account activity rather than the actual
account-specific billing response; the added boundary checks remove that
ambiguity. The precise cause of the historical timeout is not established by
the retained evidence. Do not describe this as a proven production defect and
fix. Current end-to-end behavior is Green; the earlier failed run remains part
of the record. This does not close the wider T002 or first-reading journey.

The scenario uses real Chrome permission changes for clipboard success/denial
and a real second tab for return-focus refresh. It never executes the displayed
command or enters a credential. Clipboard contents are compared inside the
browser only after a successful copy; output records no clipboard text.
Actual LAN HTTP insecure-context clipboard absence and owner credential entry
are Not Run in this UI slice. No full local enrollment or first-reading claim
is made from command display/copy evidence.

## API-only Ollama setup routing correction

- Scope: approved T002/M7-A01, FR-ACC-001/004 and FR-BUDGET-006 setup routing.
- Baseline: `716cf92`; existing API V1 Ollama cloud-connection and billing
  metadata contracts only. No schema/client, migration or credential change.
- Files: AccountPage.tsx, one corrected reason string in
  BillingConnectionPanel.tsx, accounts_admin.mjs and this evidence.

The exact UI defect was that AccountPage placed OllamaCloudConnectionView inside
the `!apiOnly` section. An API-intent Ollama record instead displayed the generic
billing panel, whose API correctly refused a second billing connection, leaving
the owner without the existing cloud setup controls.

At 16:48 UTC, before production changes, the real built `accounts_admin`
scenario created an actual API-intent Ollama metadata account and failed at
`ollama_existing_cloud_setup`:

```text
locator.waitFor: Timeout 30000ms exceeded.
waiting for getByRole('region', { name: 'Ollama cloud connection', exact: true })
  .getByRole('heading', { name: 'Ollama cloud not connected', exact: true })
```

The minimum change lifts the existing OllamaCloudConnectionView outside the
subscription-only guard and excludes Ollama from the primary generic billing
panel. Its existing archive guard remains intact. API-only Claude/Codex routing
and the mixed-account layout retain their existing controls. The generic Ollama
reason now describes reuse of the existing cloud connection and shared balance,
instead of claiming API-only setup is unavailable.

The expanded real-browser assertions require the existing not-configured cloud
state, local operator command and Copy setup command control, and compare the
real cloud-status response. A separate real billing-status GET must still show
`existing_cloud_connection_required`, `can_add_connection=false` and zero billing
connections. No credential entry, verification action, provider login or
provider collection is performed. The scenario also checks absent subscription
activity/quota/session panels, reload and the 390px layout.

This proves routing into the existing canonical cloud flow; it does not prove
live access, a populated financial pool or a first reading. Those require the
owner's real connection and later live integration evidence.

### Current verification: partial, full scenario Failed

Strict TypeScript passed and the production frontend rebuilt. The first
post-change browser run reached the existing cloud not-connected heading,
local setup summary, operator command and Copy setup command control. It then
failed at `ollama_existing_cloud_setup` with `403 !== 200` on the test's
separate `page.request.get` call to the cloud-status endpoint. The component's
own real browser status request had succeeded sufficiently to render its
not-configured state. The separate request's authorization failure is unresolved;
it is not evidence that the UI setup rendering failed.

The subsequent separate-billing-response, reload and narrow-layout assertions
were Not Run in this attempt. No full browser Green or completed Ollama setup
claim is made. Scoped `git diff --check` passed. The root redirected the task
to planning during verification; this delegate preserved the scoped edits,
stopped further implementation/test runs, and released the helper window after
the failed run exited and its owned links were cleaned up.

### Resumed transport diagnosis

On resumption, source inspection identified the precise 403 cause in
`backend/src/agentmonitor/api/transport.py`: cookie-authenticated safe requests
without browser same-origin Fetch Metadata must supply canonical `Origin`.
Playwright's separate `page.request` client shared the session cookie but sent
neither browser Fetch Metadata nor an Origin header. The protected service
therefore correctly rejected it before the application route. The component's
normal browser request was already using the admitted same-origin path.

The test now supplies `headers: { Origin: origin }` on its two read-only status
requests, matching the existing ollama_catalog.mjs transport pattern. No
application security policy, provider adapter, contract or credential behavior
was changed for this correction. The original 403 failure is retained above.

### Green

At 16:58 UTC, strict frontend TypeScript and the full rebuilt real
`accounts_admin` scenario exited 0:

```text
P02 ACCOUNTS ADMIN: PASSED — real API, SQLite, and built browser
P02 BROWSER: PASSED — accounts_admin
```

The cloud-status GET returned the actual new account, `not_configured` and
`can_verify=false`. The separate billing-status GET retained
`can_add_connection=false`, `existing_cloud_connection_required` and zero
connections. Existing cloud setup/command/copy controls were visible; the
unavailable placeholder and subscription activity/quota/session/password
sections were absent. Reload and the 390px no-overflow check passed. All earlier
Claude/API-only/mixed-account, clipboard/native-focus and subscription
administration assertions also passed.

This final run used the reproducible typecheck/build/browser command above with
the admitted guarded tool environment. The context exited, cleaned its owned
links and was explicitly released to root immediately afterward. No production
change followed this Green. No credential entry, provider login or collection
action occurred, and no commit was made by the delegate. Live cloud access and
populated-pool/first-reading verification remain separate required evidence.

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
