# P02 React dashboard — authenticated operational UI

- Status: **M2 local identity shell accepted; M3 accepted for its approved
  one-account vertical; M4 dashboard delivery accepted through its
  revision-bound six-account gate; M5 P02 plan 1.8.0 browser evidence passed,
  and plan 1.16 complete alert-history pagination is local Green while its
  authenticated browser proof remains Not Run; M5 remains Intermediate and
  this is not a V1 dashboard release**.
- Post-audit note: Story 5's historical Red-first exceptions are documented in
  the [M2 correction record](../evidence/m2-audit-fixes.md), which records the
  owner disposition and independent QA reacceptance. The separate
  `hostile_resource` Chrome scenario and SQLite assertion cover cookie-read
  idle-state integrity after 62 real seconds. Current milestone distinctions are
  recorded in the [V1 status overlay](../evidence/v1-implementation-status-v1.json).
- Owner: P02 UI. Plan: [`PLAN-P02`](../plans/ui/react-dashboard/plan-v1.md), approved M2 slice [`ST-UI-001`](../superpowers/plans/2026-09-19-agentmonitor-v1-m2-authenticated-shell.md).
- Consumes `CTR-UI-001`, `CTR-API-002`, `CTR-IAM-003/004/005/006/007`, and the
  M3 registry, provider, collection, capacity, and runtime V1 contracts through
  the generated V1 client. Publishes no backend contract, database table,
  migration, configuration key, or provider adapter.

## Scope and ownership

The M1 `index.html` foundation entry remains intact. Vite builds a separate
`dashboard.html` entry. In IAM mode P01 serves it only on the closed P02 route
allowlist: `/`, `/login`, `/accounts`, `/accounts/{opaque-id}`,
`/organizations`, `/providers`, `/collectors`, `/sessions`, `/operations`,
`/alerts`, `/alert-rules`, and `/settings/api-tokens`. This lets a user refresh
or directly open every current React view. Unknown page paths and unknown
`/api/v1/**` resources retain the versioned JSON 404 behavior; there is no
catch-all HTML fallback. P02 owns the React entry, guarded route controller,
browser-session flow, password-change form, token settings, and the handwritten
`shared/api` wrapper. The wrapper is the only handwritten importer of
`frontend/src/generated/api/**`; feature modules do not call `fetch`, read
SQLite, import backend internals, or inspect provider state.

The `monitoring_dashboard` production Chrome scenario directly opens and
reloads the complete fixed feature-route set and an opaque account-detail path,
then verifies the selected React view. The real LAN HTTP suite separately keeps
the same paths synchronized with P01's closed public-shell navigation allowlist.

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
backend/.venv/bin/python -m pytest --import-mode=importlib -q --tb=short \
  frontend/tests/browser/p02/test_run_browser_policy.py
backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py responsive \
  --repeat 30 --no-build
backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py revocation \
  --repeat 30 --no-build
backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py \
  password_change --repeat 30 --no-build
```

`quick` runs the isolated real-browser development scenarios. `all` also waits
for an actual ≥61-second session activity touch before logout. The explicit
`idle_expiry` scenario now observes the fixed 24-hour session deadline and is an
owner-long-run check; the ordinary `all` gate proves 24-hour issuance in the
production Chrome authentication scenario without claiming a full day elapsed.
`--repeat` accepts only 1 through 30, creates a new isolated real server and
browser scenario for every repetition, and stops at the first failure without
retry. `--no-build` is available only when the caller has already built the
exact source being tested. Neither command reads the operator `.env` or
provider accounts. Historical M2 browser evidence remains in
[`m2-st-ui-001.md`](../evidence/m2-st-ui-001.md); the current policy change is
recorded in [`dashboard-session-24h.md`](../evidence/dashboard-session-24h.md).

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
The `/collectors` **Collection / History** view exposes each run's actual
source, adapter/provider version availability, request/start/completion times,
duration/outcome, and observation IDs. It does not claim freshness because the
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
and update times above secondary provider and session panels. Collection-run
history is available only from the primary **Collection / History** action at
`/collectors`; opening Overview does not request that history. The UI consumes
existing V1 operations, verifies identity lineage, and never infers working
agent ownership. The canonical M4 exit includes the real populated Overview
check. See [density and quota-overview evidence](../evidence/dashboard-density-and-quota-overview.md).

Overview organization buttons select one or more admin-defined groups; All
organizations restores the default. Ungrouped and unavailable assignments
remain visible and can be filtered when present. Counts describe the filtered
account rows and registry connections. Selection survives manual and 30-second
read refresh while Overview stays open, without browser storage or registry
changes. Rows sort by their lowest usable remaining quota percentage, ascending,
with missing percentages last and deterministic name/ID ties. Each native
window remains separate. The Organization, State, and Quota left headings are
keyboard-accessible sort controls; activating the current heading reverses its
direction. On narrow screens an equivalent labeled select remains visible.
Missing quota stays last in either direction. A percentage at or below 20 has
a red bar, a visible Low label, and an accessible low description. Freshness,
calculated/rounded provenance, and provider health policy retain their existing
meanings.

When more than one provider exists in the loaded account page, Overview shows
a compact labeled Provider select. Its dynamic choices include All providers
plus each returned provider, using the existing display-name mapping. Claude,
Codex, and organization selections compose before identity grouping and quota
sorting. The provider choice survives manual and 30-second read refresh while
the page remains open, returns to All after navigation or reload, and performs
no storage or API mutation. It also returns to All when the selected provider
no longer exists in a refreshed account page. Counts reflect the filtered loaded page; the
existing bounded-page notice remains visible when more Registry accounts exist.

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

## Configured capacity alert presentation

A `capacity_remaining` alert uses the neutral title **Capacity threshold
reached** because administrators may configure its warning and critical
thresholds anywhere from 0% through 100%. The card shows the exact remaining
percentage separately and explains the effective severity threshold as
`Warning threshold: N% or less` or `Critical threshold: N% or less`. It does
not describe a high remaining percentage as intrinsically low merely because a
high custom threshold matched. A recovered record says **Capacity threshold
cleared** and retains its warning threshold context; a record closed by a rule
change says **Capacity alert closed** and explains that the configured rule is
inactive. Severity, lifecycle, remaining value, threshold, and rule scope
continue to come only from the V1 alert API.

## M5 complete alert-history pagination

The plan 1.16 Alerts view requests the existing V1 history endpoint at its
200-entry maximum and retains every validated page already loaded for a card.
When `has_more` is true, that card exposes **Load more history** and requests
exactly the API's opaque cursor. A valid next page appends in API order without
discarding earlier rows. A later unavailable or invalid page leaves those rows
visible, presents an error on the same card, and never claims that history is
complete.

The shared pagination policy requires a cursor of 1 through 1,024 characters
without controls, a new cursor on each nonterminal transition, a null terminal
cursor, one unchanged alert ID, unique event IDs and aggregate sequences, and
strictly increasing `aggregate_sequence`. Missing, empty, repeated, changed,
or overlong cursors; duplicate or wrong-alert entries; nonprogressing order;
and a terminal page with a cursor fail closed.

The M5 browser verifier builds an all-page API oracle with at most 200 pages,
40,000 unique entries, and 199 transitions after the first page. It then drives
only the selected card's visible control until the DOM reaches the same
terminal count, order, and digest, while requiring zero dashboard mutations.
The missing pagination module and missing production-policy wiring supplied the
expected Reds. Local Green covers 192 and 200 terminal entries and 201 entries
across two pages; the M5 UI policy file passes `17/17`, frontend typecheck and
the production build pass, and independent UI review is CLEAN. The active
service remains `8cc683d`; authenticated scenario `M5-CDX-UI-014` is Not Run.

## M5 canonical-browser correction

The owner-approved M5 plan 1.8.0 closes three P02 defects found by the required
canonical browser lane. At 400 pixels and below, the header uses two rows so
**Change password**, **Check session**, and **Sign out** remain fully inside a
390-pixel viewport and keyboard reachable. The primary navigation retains its
own horizontal scroll without creating document overflow.

Revocation verification accepts only two secure outcomes after the real server
revokes the secondary session: automatic arrival at **Sign in**, or one
explicit **Check session** action followed by **Sign in**. Both paths prove the
protected navigation is absent, reload remains signed out, and the primary
session remains active.

Password change uses the closed parent lifecycle `closed`, `draining`, `ready`,
and `submitting`. Opening the flow advances the protected-feature generation,
unmounts feature content, waits for effect cleanup to abort its reads, and
fences late callbacks, including callbacks from an already-started header
session check. Navigation, popstate, header session actions, and repeat submit
remain inert until the flow closes. One submit permits exactly one preflight,
one password PATCH, and at most one reconciliation GET. Only PATCH 204 followed
by GET 200 installs the renewed session and success state. Only
`dashboard_authentication_required` enters login; known noncommitted validation
or conflict outcomes return to the ready form; missing or rejected CSRF uses
the existing explicit proof renewal; an unknown mutation outcome locks the
protected view for owner verification. Ready, Cancel, and successful close
restore focus to their documented targets.

The focused runner keeps the approved existing direct Node invocation and adds
only the bounded repeat and closed output policy. Spawn, timeout, encoding, or
unexpected output returns only `browser_output_invalid`. Its grammar admits the
scenario's fixed pass line at exit zero or one allowlisted failure stage at the
exact script failure exit one; process-level exit 2, 127, and signal exit -9
remain invalid. It clears captured child output before returning and never
propagates raw child text. The pure policy suite passed 65 tests.
Responsive, revocation, and password change each passed 30 consecutive
first-attempt isolated real-stack runs; the complete P02 `all`,
`security_boundary`, and `hostile_resource` browser lanes also passed. These are
local implementation results. After two transparently retained failed attempts,
the complete `AUTO-TEST` passed its command, Argon2, backend, OpenAPI/client,
production-build, foundation-browser, P02, security, and hostile-resource
lanes. No `AUTO-M5-EXIT` or M5 completion is claimed.
