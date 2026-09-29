# P02 React dashboard — M2 identity shell and M3 observation views

- Status: **M2 identity shell and M3 Claude vertical slice accepted; not a V1 dashboard release**.
- Post-audit note: Story 5's historical Red-first exceptions are documented in the [M2 correction record](../evidence/m2-audit-fixes.md); the M2 milestone reacceptance remains held. The separate `hostile_resource` Chrome scenario and SQLite assertion now cover cookie-read idle-state integrity after 62 real seconds.
- Owner: P02 UI. Plan: [`PLAN-P02`](../plans/ui/react-dashboard/plan-v1.md), approved M2 slice [`ST-UI-001`](../superpowers/plans/2026-09-19-agentmonitor-v1-m2-authenticated-shell.md).
- Consumes `CTR-UI-001`, `CTR-IAM-003/006/007`, and the M3 registry,
  provider, collection, capacity, and runtime V1 contracts through the generated
  V1 client. Publishes no backend contract, database table, migration,
  configuration key, or provider adapter.

## Scope and ownership

The M1 `index.html` foundation entry remains intact. Vite builds a separate `dashboard.html` entry; P01 serves it only on `/`, `/login`, and `/settings/api-tokens` in IAM mode. P02 owns the React entry, guarded route controller, browser-session flow, password-change form, token settings, and the handwritten `shared/api` wrapper. The wrapper is the only handwritten importer of `frontend/src/generated/api/**`; feature modules do not call `fetch`, read SQLite, import backend internals, or inspect provider state.

M2 contains no account, quota, budget, agent, alert, or provider telemetry. The authenticated overview states that identity/access is active and provider monitoring is outside this milestone; it never renders invented values. The command dashboard and provider modules remain later V1 work.

## Browser workflow

1. A fresh migrated installation returns initialization state `uninitialized` and shows terminal-bootstrap guidance. `incompatible` or an unknown state fails closed as a service error, not as fresh setup.
2. On an initialized installation, a safe current-session GET selects either protected shell or password login. Password input remains in the form only until submit. Invalid login is generic; the real throttle `Retry-After` is bounded and displayed. A successful login replaces browser history with an allowlisted GET route; URL query/hash input is discarded.
3. A server `dashboard_authentication_required` response clears protected UI state and enters login. A separate safe “Check session” GET lets the owner detect idle expiry or revocation. No mutation is replayed automatically. Logout uses the current strong session ETag, CSRF, and server-side revocation. Password change verifies the current credential, uses a fresh current-session ETag and idempotency key, and refreshes the rotated session binding.
4. Token settings use only `read:diagnostics` and `write:tokens`, with descriptions and approved lifetimes. List items are safe summaries. Create/rotate issue a credential into a native one-time modal only; dismiss, navigation, or reload destroys the UI reference. Clipboard writing occurs only after the explicit Copy action. Rotate confirmation includes the current scopes and expiry; revoke requires confirmation. The UI never transfers a bearer credential to Swagger; Swagger authorization persistence is disabled.
5. `shared/api` reads only the AgentMonitor CSRF cookie, sends it as `X-CSRF-Token` for cookie-authenticated unsafe requests, and fails closed before sending when absent. Resource `If-Match` is built only there from the public opaque ID and positive record version as `"<id>.<version>"`. A rejected or missing CSRF proof prompts explicit password re-authentication; no failed mutation is automatically retried. The old browser session remains active until expiry unless the owner explicitly revokes it later.

## Failure and privacy policy

- Known SafeProblem codes map to fixed wording and a validated code/correlation reference; raw response detail, stack, submitted fields, and arbitrary URLs are never reflected. Server authority decides authentication, scope, concurrency, and one-time replay. A stale active ETag is surfaced as a conflict requiring refresh.
- A token create/rotate response lost after commitment has an **unknown** outcome. The UI safely refreshes summaries and warns that the plaintext cannot be recovered; it does not suggest a blind new-key retry. Naturally lost-response behavior is not artificially manufactured for tests.
- An uncertain logout is reconciled by one safe current-session GET: 401 enters login; 200 retains active state; another failure locks protected UI locally and does not assert server revocation. Uncertain password-change outcome similarly avoids retry and requires explicit verification.
- No browser Web Storage, URL, screenshot, log, analytics request, or query cache contains session credentials, CSRF values, bearer plaintext, passwords, provider data, prompts, source, or tool content. The production shell requests only same-origin assets and API. Browser tests capture boolean/header classes and status, not secret values in evidence.
- P02 makes no provider/default-profile read or write, process control, database migration, or remote-service request. All real browser tests use an isolated Alembic-migrated file SQLite, production Argon2 bootstrap, Uvicorn loopback, the production Vite build, and installed Chrome. Test credentials are OS-random and passed to Chrome only through a private stdin pipe.

## Canonical commands and limitations

From the repository root:

```bash
npm --prefix frontend run typecheck
npm --prefix frontend run build
backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py quick
backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py all
```

`quick` runs nine isolated real-browser scenarios and is an intermediate development gate. `all` also waits for an actual ≥61-second session activity touch before logout and the actual 1,805-second browser idle interval; it is the P02 Story 5 browser gate. `--no-build` is available only when the caller has already built the exact source being tested. Neither command reads the operator `.env` or provider accounts. For Red/Green results and residual `Not Run`, see [`m2-st-ui-001.md`](../evidence/m2-st-ui-001.md).

Current limitations: local loopback only, single administrator, no provider dashboard data, and no automatic agent routing. Actual 200% browser zoom, macOS, owner installation, natural lost-response, and later V1 provider-data workflows remain outside the M2 acceptance claim unless separately verified.

## M3 authenticated observation foundation

The M3 P02 increment adds API-only command, account, provider, collection-run,
capacity, process, and session views. Feature modules import typed DTOs and
operations only from `frontend/src/shared/api/client.ts`; that wrapper is the
sole handwritten importer of the generated 25-operation client. The routes
`/accounts`, `/accounts/{opaque-id}`, `/providers`, `/collectors`, and
`/sessions` are safe authenticated GET views served by the same production
SPA document.

The command view composes producer-owned availability, freshness, capability,
collection, capacity, and runtime results. It does not infer account identity,
quota health, provider presence, or process ownership. Fresh installations
render explicit empty states from real API responses. Unknown, partial,
unsupported, unavailable, stale, and unresolved states are never converted to
zero. Capacity values retain their exact coefficient, scale, unit, precision,
confidence, and value-kind fields. Runtime detail exposes only approved safe
metadata and provenance; it does not display prompts, responses, command
lines, source content, environment values, or credentials.

An account detail places its provider-native quota windows beside a `Running
sessions` panel queried with that exact opaque `account_id`. The account panel
does not reuse the unfiltered global process list. Capacity health shows the
producer policy ID/version, constraining-window ID, and explanation codes;
quota rows show exact remaining ratio, observation/run IDs, collected and
stored times, source, adapter/provider versions, freshness policy, precision,
and confidence. Capacity history renders exact retained poll observations in a
non-interpolated chart and accessible table with shared observation IDs.
Collection runs expose their actual source,
adapter/provider version availability, request/start/completion times,
duration/outcome, and observation IDs; they do not claim freshness because the
run DTO publishes no freshness field.

The production browser scenario `monitoring_dashboard` uses a fresh real
file-backed SQLite database, real migrations, production Argon2 bootstrap,
Uvicorn loopback service, the Vite production build, and installed Chrome. It
verifies the truthful empty API path, direct SPA routes, no invented provider
presence, six responsive viewport widths, no horizontal document overflow,
no external request, no browser storage, and no browser exception. It passively
records same-origin responses without request interception and requires every
empty-dashboard observation GET to return `200`; removing generated-client
calls therefore fails the browser scenario. The separate populated scenario
passed against the owner database with real Claude quota history, collection
lineage, exact process runtime, same-account session hierarchy, and complete
provenance. It also passed at 1920×1080, 960×540 (200% equivalent), and 390×844.
Evidence: [M3 P02 browser increment](../evidence/m3-st-obs-003-p02.md).

M3 renders the bounded first page supplied by each observation endpoint. Counts
are labeled as records shown, not fleet totals, and `has_more` is disclosed as
“more available.” Cursor navigation is deferred to a later approved P02
increment; the UI never implies that the first page is the complete fleet.

## M4 interim organization and account administration

The authenticated `/organizations` and `/accounts` pages now use the additive
V1 registry API through the shared generated-client wrapper. Organizations can
be created, renamed, reordered, archived, and restored. Accounts can be added
as pending records, renamed, assigned to an active organization or Ungrouped,
archived, and restored. A confirmed account with an eligible profile/resource
can enable or disable its monitoring preference. Account names and organization
names are supplied in the admin UI; no operator accounts are built into the
frontend. Stale edits require a refresh, and new pending records never imply a
confirmed provider login.

When M02 withholds an account identity, the detail view says `Withheld from
dashboard` and explains that account names and organization assignments are
administrator managed. An owner-confirmed registry state does not imply that
the current read-only provider source supplied a displayable email.

The admin browser scenarios are `accounts_admin` and `organizations` through
`frontend/tests/browser/p02/run_browser.py`. See the
[M4 interim evidence](../evidence/m4-st-fleet-001-interim.md). Continuous
collection, new identity binding, and six-account owner verification remain
outside the passing browser scenarios.

## Current quota refresh

The account capacity panel rereads current capacity and quota through the V1
API every 30 seconds. It keeps loaded history pages and preserves previous
observations with a message if a refresh fails. This timer does not contact a
provider; Claude collection runs independently in the service at the admitted
five-minute minimum. The built `accounts_admin` scenario verifies a subsequent
real API response. See [polling evidence](../evidence/claude-dashboard-polling.md).

## Account workspace and observed identity

The account page now leads with Account / State / Left / Path. Its email comes
from an authenticated V1 read of identity observed consistently around the
same quota collection; the UI checks account and run IDs before displaying it.
An administrator's registry name and dashboard organization remain separate
from the provider-reported identity/organization. A restart leaves identity
unresolved until the next genuine quota reading; it never backfills older data.

M05 supplies a derived percentage and calculation/input lineage without
rewriting source metrics or history. The UI formats that value and labels its
calculation and rounding. Individual quota windows remain separate when no
single constraining window is published. Administration, exact metrics,
history, and session inspection are expandable.

A live workstation table shows actual Claude process PIDs and working
directories through the additive V1 process-location read. Running means
process presence. Per-process account ownership and Working/waiting status
remain unresolved, so these rows receive no guessed account quota. Detection
is limited to same-user processes matching the admitted executable version;
partial and unavailable scans are visible. Refresh is every 30 seconds.

The canonical real-owner browser gate is
`backend/.venv/bin/python tools/ui/verify_account_workspace.py --origin` with
the explicit loopback origin and `--screenshots` private artifact directory.
See [workspace evidence and limitations](../evidence/account-workspace-redesign.md).

## M4 owner-driven Claude connection

A pending Claude account exposes **Connect Claude**. The owner confirms its
email and explicitly starts the official browser authentication flow through
the generated V1 connection operation. The panel reads safe status every two
seconds while active and offers cancellation. Status reads and page navigation
never start authentication. Credentials stay on Claude's ordinary browser page;
P02 receives no provider URL, authorization code, or credential.

The service verifies identity before registry enrollment and monitoring.
Managed quota collection suppresses native onboarding using the documented
presentation flag; the owner needs no terminal setup for this monitoring path.
Connected/monitoring status still waits for fresh quota to establish observed
identity and run lineage. Wrong identity, expiry, unsafe roots, and changed
versions remain explicit failures. An eligible interrupted managed enrollment
has a separate **Finish connection** action; ordinary active/default
reauthentication stays rejected.

The real `claude_connection` browser scenario Passed for controls and safe V1
behavior without launching provider sign-in. `AUTO-CLAUDE-CONNECT` additionally
requires an owner-completed dashboard flow and fresh managed quota. Four selected
owner-completed SDK/EAIS connection gates Passed; interrupted-enrollment recovery and
other live flow cases remain Not Run. See
[connection evidence and the six-story M4 status](../evidence/claude-dashboard-connection.md).

Completed connections now use a compact status row. The main page prioritizes
per-account organization, quota-reading state, remaining percentages/bars,
and update times above secondary provider/collection/session panels. It consumes
existing V1 operations, verifies identity lineage, and never infers working
agent ownership. The same canonical connection gate includes real connected
layout and populated overview checks. See [density and quota-overview evidence](../evidence/dashboard-density-and-quota-overview.md).

Overview organization buttons select one or more admin-defined groups; All
organizations restores the default. Ungrouped and unavailable assignments
remain visible and can be filtered when present. Counts describe the filtered
account rows and registry connections. Selection survives manual and 30-second
read refresh while Overview stays open, without browser storage or registry
changes. Rows sort by their lowest usable remaining quota percentage, ascending,
with missing percentages last and deterministic name/ID ties. Each native
window remains separate. A percentage at or below 20 has a red bar, a visible
Low label, and an accessible low description. Freshness, calculated/rounded
provenance, and provider health policy retain their existing meanings.

## Account agent drill-down and duplicate connections

Account detail has **Agents using this account** for current owner-confirmed
terminal links. **Identify other Claude terminals** lists unlinked processes;
the owner checks the official `/status` in the matching terminal, selects an
admin-defined account, checks confirmation, then presses **Confirm account
link**. Agent details show only actual available PID/start, parent, CLI version,
working directory, RSS, cumulative CPU and OS state. Running is presence;
working/waiting, per-process session/model/tokens remain unknown. Links need
reconfirmation after account changes inside a terminal. Session history is
separate. No process switching/control is offered.

Overview groups fresh successful lineage-matched identical reported identities
within the same provider/provider organization/dashboard group into one quota
row, preferring a correctly named admin record. It displays the connected
profile count and separate review links. Incomplete/conflicted/unavailable
readings remain separate. Accounts admin retains every registry record; no
automatic merge, deletion or provider reconnection occurs. A different admin
name remains visible beside observed identity on account details. See
[bounded progress and real verification](../evidence/live-account-agents.md).
