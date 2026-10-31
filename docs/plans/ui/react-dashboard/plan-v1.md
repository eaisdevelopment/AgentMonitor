# Boundary plan: P02 — React mission-control dashboard

- Status: **Draft; independent planning artifact; not approved for implementation**
- Plan ID: `PLAN-P02`
- Plan version: `0.2.0-draft`
- Boundary contract version: consumes proposed `CTR-UI-001 v1` and `CTR-API-001..003 v1`; publishes no backend contract
- Owner: P02 React web application owner
- Reviewers: integration steward, P01 owner, M01/M02/M04/M05/M06/M07/M08 consumer reviewers, security, accessibility, test, dependency/license, operations
- Requirements: `FR-UI-001..007` plus the presentation and workflow requirements mapped in section 2
- Acceptance criteria: `AC-UI-001..006` plus supporting release, live, process, alert, history, operations, and test criteria mapped in section 2
- Dependencies: synchronized `CTR-API-001..003`, generated-client contract `CTR-UI-001`, approved frontend foundation and build metadata
- Target milestone: M1 shell/authentication; M2–M7 feature slices as producer contracts become available
- Approved by/date: pending
- Implementation authority: none

## CS-1 alignment addendum — contract baseline 0.2.0

This addendum is normative for CS-1 and supersedes any wording below that could
make P02 an API-schema producer, generated-artifact writer, or direct consumer
of backend modules. The machine-readable
[contract baseline](../../contract-baseline.toml) and
[parallel ownership manifest](../../parallel-ownership.toml) remain unapproved
and grant no implementation authority.

- P01 owns API/OpenAPI semantics and source schemas. PLAN-FND owns the
  `CTR-FND-005` generation mechanism. PLAN-INT is the sole writer of OpenAPI and
  generated TypeScript client artifacts during each allocated wave. P02 owns
  only the handwritten generated-client wrapper and frontend consumption; it
  never edits generated output or duplicates generated DTOs.
- The generated client is P02's only typed server-data boundary. P02 imports no
  backend contract/module, repository, ORM, provider/platform adapter, database,
  provider file, or local-process surface. `CTR-COMMON-007`,
  `CTR-COMMON-005`, `CTR-APP-001`, `CTR-OPS-001..005`, provider/capacity/runtime
  state, and `CTR-EVT-001` effects reach P02 only through P01-generated API
  schemas and operations.
- `dashboard_authentication_required` means dashboard HTTP 401/session
  recovery: P02 clears protected API cache and enters the dashboard login flow.
  `provider_reauthentication_required` means a provider account/profile needs
  its approved M02/M03 workflow: P02 preserves the dashboard session and
  unrelated caches and shows only the eligible provider action. The states are
  never aliases.
- `CTR-COMMON-007` drives explicit UI states for missing, null, unknown,
  unsupported, unavailable, not-applicable, withheld/denied, stale, unresolved,
  and exact zero. The UI cannot infer provider facts, application readiness,
  aggregate status, or event recovery client-side.
- After an exact generated-client baseline is frozen, feature-private lanes may
  proceed in parallel only within their allocated `features/**` paths. The app
  shell, route map, design tokens, shared API wrapper, package/lock/build files,
  generated directory, navigation, and common evidence indexes each retain one
  writer per wave.

All browser claims require the real built frontend, real FastAPI service, real
SQLite data path, and real browser. No mocked transport, fake server, DOM-only
substitute, seeded telemetry, recorded provider result, or placeholder value can
pass a T4/provider claim; Blocked and Not Run remain non-Passed.

## Planning gate and evidence truth

This plan is detailed enough to allocate isolated feature ownership, design meaningful tests, and identify every producer contract P02 needs. It is not evidence that the UI, API, data, or browser workflows exist. No dependency has been installed, no frontend code has been written, no telemetry has been created, and no browser or live-provider test has been run by this planning task.

P02 implementation remains blocked until all of the following are true:

1. P01 publishes a synchronized OpenAPI resource and operation inventory for the feature slice being implemented.
2. Foundation publishes the admitted runtime, package manager, lockfile, build, generated-client, browser-test, and command-registry mechanisms.
3. `CTR-UI-001` identifies the generator, output path, generator version, wrapper boundary, and drift command.
4. M01/P01/P02 synchronize browser session, CSRF, authentication-expiry, logout, and one-time API-token transport behavior.
5. The producing module owns every value, aggregation, explanation, permission, state transition, and error that the UI renders.
6. Candidate UI dependencies pass the full dependency and license admission gate.
7. The root synchronization review accounts for this exact plan version and the canonical planning gate passes.

The UI is not allowed to compensate for a missing producer contract with a database query, backend import, handwritten DTO, provider read, fabricated value, inferred aggregation, or test fixture.

## 1. Outcome and boundaries

### 1.1 Outcome

P02 delivers a secure, responsive, accessible React application that gives the local administrator an information-dense mission-control view of real AgentMonitor state. It makes global health, critical alerts, capacity, freshness, authentication attention, and active sessions immediately visible; then supports progressively deeper organization, provider, account, session, history, alert, collector, diagnostics, and settings workflows.

Success is observable only when the production frontend is built and served with the production FastAPI application, a real migrated SQLite database, real application authentication, the generated client, and real persisted state. A fresh installation with no enrolled accounts must render a truthful onboarding/empty state. Populated telemetry views must use real collected observations. There is no permitted sample, seeded, demo, placeholder, or recorded telemetry path.

The visual language is a restrained dark spacecraft control console: dense grids, clear hierarchy, tabular numbers, strong state semantics, and deliberate focus. It is not a decorative cockpit. A gauge, chart, animation, panel, or accent exists only when it communicates a real bounded value or operational relationship.

### 1.2 In scope

- SPA routing, session bootstrap, guarded routes, document titles, focus transitions, error boundaries, and the authenticated application shell.
- Password login, logout, session-expiry recovery, current-session visibility, password-change entry when P01 exposes it, and secure return-to-route behavior.
- Named API-token list/create/rotate/revoke workflows, one-time plaintext reveal, scope/expiry explanation, and Swagger authorization guidance.
- Global command view, organization view, account view, provider/installations view, session/process view, alert console, history, authentication center, collector status, diagnostics, backups, exports, and settings.
- Organization create/rename/reorder/archive/restore and account registration/rename/group/monitor/archive/restore workflows through generated operations.
- Discovery-candidate review, explicit identity association, protected-profile explanation, and eligible official re-authentication guidance.
- Manual refresh request and collection-run progress/status display without direct provider calls.
- Every observable provider-native quota and budget window, exact units/money, normalized health explanation, source/provenance, freshness, precision, confidence, derivation inputs, and forecast uncertainty.
- Parent/child session hierarchy, parent aggregates, process/session details, correlation confidence, unresolved association, and explicit safe confirmation workflows.
- Dashboard notifications, alert lifecycle/history, threshold configuration, acknowledgement, snooze, recovery, unread behavior, and links to source evidence.
- Health/readiness, versions, collector runs, backup status/manual backup, export/diagnostic jobs and authorized downloads. Restore execution is excluded from browser UI in V1.
- Responsive behavior optimized for 1920×1080 and defined large, desktop, tablet, narrow, zoom, and reduced-motion conditions.
- WCAG 2.2 AA design and verification including keyboard, focus, landmarks, names, contrast, reflow, target size, non-color cues, and chart/table equivalence.
- Query/cache/error policies, correlation IDs, safe mutation coordination, and privacy-safe browser behavior.
- P02-owned test suites, documentation, automated quality rules, and sanitized evidence production.

### 1.3 Out of scope

- Business truth, aggregation, threshold evaluation, alert transitions, quota arithmetic, forecasting, correlation decisions, collection scheduling, retention, backup integrity, or authentication verification.
- FastAPI routes, OpenAPI schemas, HTTP status mapping, cookies, CSRF creation, bearer verification, host/origin enforcement, persistence, or database migrations.
- Direct provider API/CLI calls, provider file reads, process inspection, local filesystem inspection, or operating-system service control.
- Provider credential collection, password/OTP/MFA fields, default-profile mutation, private browser endpoints, or login automation.
- Email, desktop notifications, messenger delivery, remote/multi-user operation, additional post-V1 providers, transcript/content display, or agent routing/control.
- Restore execution in the browser, destructive data actions without a separately synchronized workflow, and any action that kills/restarts/pauses/injects/switches/routes a running agent.
- Design mockups containing invented accounts or telemetry. This plan specifies behavior and layout rules; it creates no telemetry mockup.
- A browser-side parallel domain model or offline data store.

### 1.4 Ownership

P02 owns:

- application routes, navigation, feature composition, responsive layout, focus restoration, and UI error boundaries;
- presentation-only state and view composition derived without changing API meaning;
- the wrapper/query layer around generated client operations, query keys, invalidation policies, and safe problem mapping;
- accessible components, semantic design tokens, icons, formatting adapters, chart/table pairing, and state presentation;
- the browser-side workflow orchestration for API calls, confirmations, progress, conflicts, and expiry recovery;
- frontend-specific diagnostics such as build/client version and safe rendering-error classification;
- P02 browser/accessibility/visual/performance tests and frontend module documentation.

P02 owns no database table, Alembic migration, background job, provider state, domain event, public REST schema, OpenAPI artifact, generated client output, secret, or server configuration key.

### 1.5 Proposed implementation paths and exclusive owners

Paths are proposals for foundation synchronization. Directories appear only during approved implementation.

```text
frontend/
  src/
    app/                              # P02 shell steward
      App.tsx
      router.tsx
      routeManifest.ts
      sessionBootstrap.ts
      AppErrorBoundary.tsx
      focusManagement.ts
    features/
      auth/                           # auth feature owner
      command/                        # global command owner
      organizations/                  # organization workflows owner
      accounts/                       # account/auth/profile workflows owner
      providers/                      # provider/installations/capabilities owner
      sessions/                       # runtime tree/detail/correlation owner
      alerts/                         # alert console/rules/notifications owner
      history/                        # history ranges/charts/tables owner
      collectors/                     # collection-run/manual-refresh owner
      diagnostics/                    # health/version/backup/export owner
      settings/                       # timezone/security/API-token owner
    shared/
      api/                            # P02 wrapper; generated calls only
      query/                          # query keys/cache/invalidation
      components/                     # accessible technical primitives
      formatting/                     # display-only typed formatters
      state/                          # UI-state algebra, no server truth
      security/                       # safe navigation/download helpers
      styles/                         # tokens, reset, layout, print/reduced-motion
    generated/api/                   # generator-owned; never manually edited
  tests/
    browser/p02/                      # P02 real built-browser suites
    accessibility/p02/                # real browser/accessibility suites
    visual/p02/                       # sanitized structural evidence only
    pure/p02/                         # optional I/O-free formatting/layout policy
docs/
  modules/react-dashboard.md          # P02 module documentation
  user/dashboard.md                   # user workflows
  user/accessibility.md               # keyboard/AT behavior
```

Shared-file allocation:

| Artifact | Edit owner | P02 relationship |
|---|---|---|
| `frontend/package.json` and lockfile | foundation/dependency steward | Proposes requirements; does not hand-edit after shared lock without allocation |
| Vite/TypeScript/lint/test configuration | foundation frontend steward | P02 proposes rules through synchronized change packet |
| `contracts/openapi/agentmonitor-v1.json` | PLAN-INT wave writer; P01 semantic source | P02 read-only; never edit |
| `frontend/src/generated/api/**` | PLAN-INT wave writer through FND mechanism | Import only through `shared/api`; never edit |
| `.gitlab-ci.yml` and canonical command registry | integration/foundation | P02 supplies suite requirements and evidence classification |
| Feature directory | one named feature agent per implementation wave | Other feature agents cannot edit it |
| `app/**`, `shared/**`, navigation, design tokens | P02 shell/shared steward | Feature agents submit requests; no concurrent edits |

### 1.6 Allowed dependencies and imports

Allowed dependency direction:

```text
app
  -> features
      -> shared/api + shared/query + shared/components + shared/formatting + shared/state
          -> generated/api
```

Additional rules:

- `app` may compose feature route exports but cannot import a feature's private components.
- A feature may import public exports from `shared/**` and its own directory only.
- A feature may not import another feature directly; cross-feature composition belongs in `app` or a synchronized shared presentation contract.
- `shared/api` is the only handwritten code allowed to import `generated/api`.
- `shared/api` can adapt transport mechanics and safe problems but cannot rename/reinterpret domain fields, calculate aggregates, or supply defaults for missing data.
- Server state lives in the admitted query layer. UI-only state stays in the closest component/feature owner.
- Runtime schema narrowing uses generated discriminated unions and generated validators if available; a handwritten parallel DTO is forbidden.

Forbidden imports and access:

- backend Python packages, backend source paths, ORM types, SQLAlchemy, SQLite files, Alembic state, or module tables;
- internal contracts from M01–M08 or provider/platform adapters;
- provider SDKs, provider APIs, CLI executables, `/proc`, session files, provider profiles, filesystem state, process environment, or local service managers;
- direct `fetch`, `XMLHttpRequest`, ad hoc WebSocket/EventSource creation, or generic HTTP libraries in app/feature code;
- secret-bearing browser storage, analytics/crash reporting, raw HTML injection, unreviewed external fonts/scripts, or remote CDNs.

## 2. Requirements and traceability

P02 presents workflows owned by other modules; this table does not transfer their business invariants to the UI.

| Requirement/AC | P02 planned behavior | Consumed contract | Scenario IDs | Evidence gate |
|---|---|---|---|---|
| FR-UI-001 | Dense responsive mission-control shell, 1920×1080 first, progressive reflow | CTR-UI-001/CTR-API-001 | UI-RESP-001..008, UI-VIS-001..005 | Built UI in real browsers/viewports |
| FR-UI-002 | Global, organization, account, provider, session, history, alert, auth, collector, diagnostics, settings routes | CTR-UI-001 | UI-NAV-001..008, feature scenarios below | Real route/workflow traversal |
| FR-UI-003 | Persistent critical/health/freshness/session summary at wide layouts; prioritized narrow status | CTR-API-001 projections | UI-CMD-001..010 | Real populated or truthful empty state |
| FR-UI-004 | Text, icon, and semantic structure accompany color | CTR-UI-001 | UI-A11Y-001..010 | Automated and manual real-browser checks |
| FR-UI-005 | Gauges only for real bounded numerator/denominator; no decoration | CTR-API-001 | UI-CAP-006, UI-VIS-003 | Source review and real rendering |
| FR-UI-006 | Explain normalized/derived values with inputs/source/time/confidence | CTR-API-001 capacity/provenance schemas | UI-CAP-004..010 | Real observation reconciliation view |
| FR-UI-007 | No sample accounts or invented telemetry in product/tests | CTR-UI-001 real service only | UI-DATA-001..006 | Source/artifact/browser data-provenance gate |
| FR-ORG-001..003 | CRUD/order/archive groups and display API-owned aggregates globally/by organization | CTR-API-001 registry/capacity/runtime/alert projections | UI-ORG-001..008 | Real persistence through UI/API |
| FR-ACC-001..006 | Account/profile/resource/install views, registration, monitoring state, discovery review, explicit association | CTR-API-001 registry resources | UI-ACC-001..012 | Real registered accounts or truthful empty/discovery states |
| FR-AUTH-001..006 | Auth-health states, protected-profile truth, eligible official re-auth guidance, identity preservation visibility | CTR-API-001/002 | UI-PAUTH-001..008 | Live owner-controlled workflow where available |
| FR-QUOTA-001..006 | Native windows, units/reset/status/source, health and forecast explanations, unsupported truth | CTR-API-001 capacity resources | UI-CAP-001..010 | Live real observation/browser reconciliation |
| FR-BUDGET-001..006 | Exact spend/credits/limits/periods and supported breakdowns without false totals | CTR-API-001 capacity/history resources | UI-BUD-001..008 | Real provider/API account data |
| FR-DISC-001..008 | Read-only session/process metadata and hierarchy as returned by API; safe unresolved correlations | CTR-API-001 runtime resources | UI-RUN-001..012 | Real workstation sessions/browser |
| FR-STATE-001..004 | Exact normalized/inferred runtime states, possible-stall and wait exclusions | CTR-API-001 runtime resources | UI-RUN-004..010 | Real state evidence; unavailable cases Blocked |
| FR-COL-001..008 | Freshness/provenance/run state; manual refresh request; no cached-as-current fallback | CTR-API-001 collection resources | UI-COL-001..010 | Real API/provider run where available |
| FR-HIST-001..005 | Bounded ranges, trends/timelines, exact table, export link, configured timezone | CTR-API-001 history/export resources | UI-HIST-001..009 | Real retained observations and jobs |
| FR-ALERT-001..006 | Rule scope/precedence explanation, active/history filters, ack/snooze/read/recovery | CTR-API-001 alerts | UI-ALERT-001..012 | Real SQLite/API/browser lifecycle |
| FR-IAM-001/003 | Password login, session cookie, CSRF mutation, logout and expiry recovery | CTR-API-002 | UI-AUTH-001..010 | Real server/session/browser |
| FR-IAM-004..006 | API-token list/create/rotate/revoke, one-time reveal, Swagger guidance | CTR-API-001/003 | UI-TOKEN-001..010 | Real persistence and bearer verification |
| FR-IAM-007 | UI assumes same-origin loopback; rejects no security error by bypass | CTR-API-002 deployment behavior | UI-SEC-001..004 | Real loopback server/host-origin tests owned jointly with P01 |
| FR-OPS-002..006 | Health/readiness, versions, collector/database/backup/export/diagnostic visibility | CTR-API-001 operations resources | UI-OPS-001..012 | Real production operations workflows |
| FR-SAFE-001 | Expose only approved refresh/metadata/config/alert/export actions | CTR-API-001 | UI-SAFE-001..004 | Route/control and OpenAPI review |
| FR-SAFE-002 | No process control, credential switch, routing, or input injection control | CTR-API-001 | UI-SAFE-005..008 | Built bundle/source/accessibility tree review |
| NFR-API-002 | Generated client is the only backend DTO/transport source | CTR-UI-001 | UI-CONTRACT-001..006 | Generation/compile/drift/import gates |
| NFR-TEST-001/002 | Real-boundary TDD with no doubles/seeded telemetry | Test evidence contract | UI-AUTO-001..006, all scenarios | Red/Green/refactor and prohibited-pattern gate |
| NFR-SEC-001/NFR-PRIV-001/002 | Minimized display, no secret/content capture/storage/telemetry | CTR-API-001..003 | UI-SEC-001..012 | Browser storage/bundle/network/log scan |
| NFR-DOC-001/NFR-LIC-001 | Maintained UI docs and admitted locked dependencies/notices | Foundation contracts | UI-DOC-001..004, UI-DEP-001..004 | Documentation/dependency automation |
| NFR-PLAT-001 | Browser UI remains platform-neutral; Linux verified first, macOS real when available | CTR-UI-001 | UI-PLAT-001..003 | Real Linux browser; macOS Passed or Blocked |
| NFR-PERF-001/NFR-RES-001 | Bounded pagination/rendering and isolated panel failure without dashboard collapse | CTR-API-001 | UI-PERF-001..008, UI-ERR-001..008 | Measured real browser/API state |
| NFR-OBS-001/NFR-COMP-001 | Safe correlation IDs and explicit API/client/build incompatibility | CTR-API-001/CTR-UI-001 | UI-ERR-004, UI-CONTRACT-001..006 | Real problem/version/drift behavior |
| AC-V1-003/007/008 | Current client, no secrets, no simulated data | CTR-UI-001 | UI-CONTRACT-001..006, UI-DATA-001..006, UI-SEC-001..012 | Build/security/real-browser gates |
| AC-UI-001 | Login/logout/expiry recovery/API-token rotation | CTR-API-001..003 | UI-AUTH-001..010, UI-TOKEN-001..010 | Real backend persistence/browser |
| AC-UI-002 | Real global/org/provider/account/capacity/runtime/alert/freshness | CTR-API-001 | UI-CMD/ORG/ACC/CAP/BUD/RUN/ALERT scenarios | Owner workstation live matrix |
| AC-UI-003 | 1920×1080 and responsive checkpoints usable | CTR-UI-001 | UI-RESP-001..008 | Real browser viewport/zoom matrix |
| AC-UI-004 | Keyboard/focus/names/contrast/non-color | CTR-UI-001 | UI-A11Y-001..010 | WCAG review with real browser |
| AC-UI-005 | Empty/loading/partial/stale/unsupported/unauthorized/failed actionable | CTR-API-001 problem/state schemas | UI-STATE-001..012 | Naturally/production-generated states only |
| AC-UI-006 | Normalized/derived values expose evidence and explanation | CTR-API-001 capacity/provenance | UI-CAP-004..010 | Real observation detail |
| AC-LIVE-005..007 | UI reconciliation and honest naturally available provider conditions | CTR-API-001 | UI-LIVE-001..006 | Owner-coordinated real provider evidence |
| AC-PROC-002..005 | Hierarchy, unresolved mapping, metadata privacy, possible-stall meaning | CTR-API-001 | UI-RUN-001..012, UI-SEC-008 | Real Linux process/session evidence |
| AC-ALERT-002/003 | Real alert lifecycle and stale/auth conditions | CTR-API-001 | UI-ALERT-001..012 | Running app/SQLite/real conditions |
| AC-HIST-001 | Collection → history → chart and table path | CTR-API-001 | UI-HIST-001..009 | Real observation end-to-end |
| AC-OPS-002/003 | Browser closure independence and isolated provider/API-panel failure visibility | CTR-API-001 | UI-OPS-010, UI-ERR-001..008 | Native service and real browser |
| AC-TEST-001..003/006 | R/G/R, no prohibited test framework, real built frontend/browser, explicit unavailable | Test evidence contract | UI-AUTO-001..006 | Canonical fail-closed suite |

Interpretation constraints:

- P02 displays producer-provided aggregates. It never sums account values into a global total unless the API explicitly supplies a semantically valid aggregate.
- P02 formats exact values but does not change precision, derive missing denominators, infer reset time, choose capacity health, or forecast exhaustion.
- P02 may sort a currently loaded display page only when the API contract identifies it as presentation-safe. Authoritative ordering, filtering, pagination, and scope membership remain server-owned.
- A UI control is visible/enabled only from an explicit permission/action-eligibility field or synchronized permission map. Absence is not guessed permission.
- Unsupported, unavailable, unknown, stale, partial, experimental, and zero are distinct visible states.

## 3. UI domain and interaction design

### 3.1 Application shell and navigation

The authenticated shell contains:

1. a skip link and semantic header with product/build identity;
2. a global health/freshness indicator with text and icon;
3. a critical-alert strip when active alerts exist;
4. primary navigation with Global, Organizations, Accounts, Providers, Sessions, Alerts, History, Collectors, Diagnostics, and Settings;
5. a route heading, safe breadcrumb, last successful query time, and explicit refresh status;
6. a notification control with unread count returned by the API;
7. administrator/session menu with logout;
8. one main landmark and route-level error/status region.

The URL may contain only opaque resource identifiers and allowlisted route/filter keys. It never contains account labels, provider identities, paths, search text copied from diagnostics, credentials, CSRF values, bearer tokens, or one-time API-token plaintext. Sensitive workflow form state is not encoded in query parameters.

Routes are lazy-loaded only when the loading and error behavior remains accessible and does not hide the critical global strip. Route changes place focus on the new `h1` or a declared error heading, update the document title, and retain navigation position only when doing so does not surprise keyboard users.

### 3.2 Truthful presentation-state algebra

Every data surface renders exactly one primary state and zero or more qualifications:

| Primary state | Meaning | Required UI behavior |
|---|---|---|
| `loading` | A real request is outstanding and no usable response is present | Structural skeleton without numeric/text telemetry; named busy region |
| `empty` | Successful complete response contains no records | Explain what is absent and show only API-authorized next actions |
| `available` | Complete usable response exists | Render values with freshness/source appropriate to contract |
| `partial` | Response identifies missing/failed components | Render available subsets and list missing scopes/reasons |
| `stale` | Producer marks data outside freshness policy | Keep last value visibly stale; never style or label as current |
| `unsupported` | Capability was discovered and classified unsupported | State unsupported and why/source; no zero or setup action unless supplied |
| `unknown` | Meaning/value cannot be established | Say unknown; expose safe explanation and next evidence action if supplied |
| `unavailable` | Capability/service exists but cannot currently return data | Preserve distinction from unsupported and failed request |
| `unauthorized` | Session/permission is absent | Login/permission recovery without leaking resource existence |
| `forbidden` | Authenticated principal lacks required permission | Safe explanation; no retry loop or hidden mutation |
| `conflict` | Record/revision/idempotency state changed | Preserve non-secret user intent, refetch, and require informed resubmission |
| `failed` | Request or rendering boundary failed | Stable safe code, correlation ID, bounded retry/help action |
| `maintenance` | Backend explicitly reports maintenance/not-ready | Global banner; disable unsafe writes; do not relabel historical data current |

Qualifications include `experimental`, `derived`, `heuristic`, `estimated`, `rounded`, `inferred`, `owner-confirmed`, `provider-verified`, and `unresolved`. A qualification is never represented by color alone.

The application must not infer `empty` from a failed or partial response. The query wrapper returns a discriminated UI transport state that preserves the API outcome and correlation ID without converting absent fields to default numbers, empty arrays, or empty strings.

### 3.3 Information architecture and workflows

#### Global command view

Wide-screen order:

1. system/readiness/collector health and last global refresh;
2. active critical/warning strip with links to exact alerts;
3. normalized capacity counts by API-provided health state;
4. organization × provider status matrix;
5. active parent session tree summary;
6. near-term quota/budget forecasts with uncertainty;
7. recent alert recoveries, authentication actions, and collector incidents.

No card displays a total when the API identifies incompatible pools or incomplete membership. The matrix cell exposes count/state/source age and drills into the filtered resource list. A failed panel is isolated with its own safe problem while the shell and other successful panels remain available.

#### Organizations

- Ordered list with Ungrouped represented as an API scope, not a fake organization.
- Detail shows API-provided capacity, spend, alerts, accounts, and active sessions.
- Create, rename, reorder, archive, and restore use version/ETag/idempotency data supplied by P01.
- Archive confirmation states consequences and is blocked when the API reports assigned active accounts.
- Threshold settings show effective source and scope override; M07 remains the policy owner.

#### Accounts and authentication center

- List filters by provider, organization, lifecycle, monitoring eligibility, auth health, and capacity health through API filters.
- Detail separates subscription, API, project/workspace, profile, and other resource pools.
- Registration and discovery review show masked safe identity only. Unprovable identity requires explicit owner confirmation; no preselected guess.
- Profile panels distinguish protected default from AgentMonitor-managed. Protected default profiles expose no re-auth mutation action.
- Re-authentication starts only when the API marks the managed profile eligible. The UI displays the official flow type, safe instructions, expiration/progress, intended safe account alias, identity result, and wrong-account block. It never asks for provider password, email OTP, MFA, recovery code, OAuth token, or API credential.
- Rename, move, monitoring preference, archive, and restore are optimistic-concurrency mutations; history remains server-owned.

#### Providers

- Provider and installation list shows presence/discovery, adapter/protocol/provider/CLI versions, compatibility, and capability classifications.
- Capability matrix uses Supported, Experimental, Unsupported, Unavailable, Unknown, or Incompatible exactly as returned.
- Provider view does not imply one shared quota or identity across multiple accounts/resources.
- Safe installation labels may appear; executable paths and profile locators do not.

#### Capacity and history

- Each provider-native window is a separate row/card with scope, used, remaining, limit, unit, window/reset, status, and provenance.
- Percentage/gauge rendering requires an explicit valid numerator and denominator from the API. Missing denominator uses a value row, never an empty gauge.
- Subscription and API pools remain visually and semantically separate.
- Money uses API currency plus exact minor-unit/decimal semantics and locale-aware display without changing stored precision.
- Forecast shows algorithm/version label, generated time, horizon, uncertainty, and input observation links. Insufficient input is a visible outcome.
- Every chart has a synchronized exact-data table, accessible summary, units, timezone, range, bucket meaning, and gaps. Gaps remain gaps.
- Time-range changes request server-side bounded history; the browser does not fetch or retain the full year unless the API explicitly returns a bounded export.

#### Sessions and processes

- Tree rows expose expansion, parent/child semantics, node runtime state, aggregate attention state, safe account/provider/project label, duration, and observable usage.
- Aggregate values show excluded/unknown child counts and do not silently treat missing as zero.
- Detail displays safe PID/parent PID, start/duration, CPU/memory, model/task label, token/context metrics, activity, state evidence/provenance, and account-correlation confidence only when fields are present.
- Inferred state is explicitly labeled. Waiting-for-input and waiting-for-permission are not visually merged with possible stall.
- Orphan, cycle/hierarchy conflict, permission denial, exited, and unresolved account states are understandable without reading raw data.
- Correlation confirmation is an explicit mutation showing only safe evidence summaries, intended account, and impact. No prompts, responses, tool arguments, command line, environment, source content, or raw path is displayed.

#### Alert console and notifications

- Filters cover active, unread, acknowledged, snoozed, recovered, severity, condition, scope, and bounded time range.
- Alert rows show severity text/icon, lifecycle, scope, affected resource, first/latest occurrence, count, snooze/ack state, and safe evidence/source link.
- Fetching or viewing a list never silently marks it read. Read/acknowledge/snooze are explicit actions following the synchronized contract.
- Acknowledge does not imply recovery. Snooze shows expiry and does not hide a more severe lifecycle transition unless the server contract says it becomes visible.
- Notification counts and state come from M07 via P01; the browser does not deduplicate or reconstruct alert lifecycle.
- Dashboard-only V1 delivery is explicit. No email/native/messenger controls appear.

#### Collectors

- Aggregate scheduler/collector health, target-level freshness/backoff/block, and paginated run history are visible.
- Run statuses preserve requested, queued, running, partial, succeeded, failed, blocked, cancelled, unsupported, and unknown.
- Manual refresh requires an explicit target/capability, confirmation of potential provider cost/rate impact where supplied, CSRF, permission, and idempotency key.
- The UI follows the returned run resource through ordinary REST polling at a bounded cadence. It does not claim request acceptance means provider success.
- Retry buttons are offered only when the API says the action is eligible. Authentication blocks direct the user to the authentication center.

#### Diagnostics, backups, exports, and settings

- Health/readiness expose component status, checked time, safe cause, and required/optional criticality.
- Version panel covers application, schema, frontend, OpenAPI, generated client, adapters, and provider/CLI versions where allowed; mismatches are explicit.
- Backup list shows freshness, slots, checksum/integrity state, schema, job progress, and failures without local paths. Manual backup is allowed through the approved mutation.
- Export and diagnostic jobs show scope, status, per-module completeness, safety scan, expiry, and download availability. Downloads use authenticated generated-client transport or a synchronized safe browser-download adapter.
- V1 provides no restore-execution button.
- Settings include configured timezone, alert thresholds/rules, safe polling/configuration controls exposed by the API, administrator security, and API tokens. Secret presence may be shown only when the API explicitly permits it; values never appear.

### 3.4 Responsive layout contract

Breakpoints are semantic targets subject to real-browser verification, not device assumptions:

| Mode | Proposed viewport condition | Composition and priority |
|---|---|---|
| Command wide | `>= 1600px` | 12-column fluid grid; simultaneous health/capacity/matrix/session/forecast; 1920×1080 reference |
| Desktop | `1280–1599px` | 8-column grid; secondary panels move below primary grid; critical strip remains visible |
| Compact desktop/tablet landscape | `960–1279px` | 6/4-column adaptive grid; navigation may collapse; tables use controlled horizontal region with labels |
| Tablet/narrow | `600–959px` | 2-column then single-column stack; secondary detail in disclosure panels; no meaning removed |
| Mobile fallback | `< 600px` | single column prioritizing login, global critical state, account availability, active sessions, and alerts; management remains possible only where usable |

Required verification viewports include 1920×1080, 1440×900, 1280×720, 1024×768, 768×1024, and 390×844. At 200% browser zoom on 1920×1080, the result must reflow without loss of critical meaning. Text zoom, minimum target size, system font scaling, long translated-like labels, reduced motion, and high-contrast/forced-color behavior are tested where the supported browser exposes them.

There is no no-scroll promise. The header/critical summary may remain sticky only when it does not consume excessive narrow-screen space, obscure focused content, or create nested keyboard traps. Data tables can scroll horizontally inside a named focusable region, with the first identifying column protected where feasible.

### 3.5 Visual system

- Dark neutral surfaces with AA-verified contrast; theme tokens encode role, not provider brand.
- Warning amber and critical red are reserved for state. Provider colors cannot override semantic colors.
- Every state combines icon, text, and structural cue. Icons have accessible names only when they add meaning; decorative duplicates are hidden.
- Tabular numerals apply to quota, money, duration, timestamps, and table comparisons.
- Density uses spacing/type hierarchy, not tiny text or undersized targets.
- Bounded progress/gauges require meaningful denominator, unit, range, and text equivalent.
- Line/area charts represent time, stacked bars represent compatible composition, and heatmaps represent density only when exact table alternatives exist.
- Motion is limited to useful transitions and progress. `prefers-reduced-motion` removes nonessential movement without hiding state.
- Loading skeletons represent geometry only: no digits, currency signs, percent-like bars, account labels, or chart traces.

### 3.6 Accessibility interaction contract

- One `h1` per route, logical heading sequence, semantic header/nav/main/aside/footer landmarks, and skip link.
- All actions are native buttons/links/forms unless an admitted primitive supplies equivalent semantics and keyboard behavior.
- Focus is visible, never covered, and programmatically moved only after route/dialog workflow transitions.
- Dialogs name their purpose, trap focus while open, close predictably, and restore focus to the invoker.
- Status changes use appropriately scoped live regions; polling does not repeatedly announce unchanged content.
- Tables have captions, headers, scope, sortable-state announcements, units, and pagination controls.
- Tree views follow the ARIA tree pattern only if the admitted implementation passes real keyboard/screen-reader testing; otherwise use nested semantic lists/disclosures.
- Charts have a concise conclusion plus an exact table reachable adjacent to the chart.
- Countdown/reset changes do not announce every tick. User-facing timestamps use configured timezone and details expose UTC.
- Color contrast targets WCAG 2.2 AA, including focus indicators, disabled/read-only distinctions, charts, and state chips.
- Error summaries link to invalid fields; error text is stable and never depends on icon/color alone.

### 3.7 Server-state, caching, retries, and refresh

The query layer is the only owner of server cache. Rules:

- Query keys are centrally typed from generated operation inputs and include exact scope/filter/pagination identifiers.
- Cache entries are in-memory only for V1. There is no persisted query cache, service worker offline cache, IndexedDB telemetry store, or local/session-storage server state.
- Producer `observed_at`, `collected_at`, freshness deadline/state, and API completeness remain authoritative. Query-library age never relabels stale data current.
- Route changes can retain last known data only while keeping its backend freshness label and indicating an active refetch.
- Safe GET queries may receive bounded retries only for synchronized transient codes. Authentication, authorization, validation, conflict, unsupported, and incompatible outcomes are never blindly retried.
- Mutation calls are never automatically replayed. An explicit user retry reuses or regenerates idempotency material according to the synchronized P01 contract.
- `Retry-After` is honored within a bounded UI policy. The UI does not create high-frequency provider/API polling.
- Background polling pauses when the document is hidden unless the contract requires job progress; collection itself continues server-side.
- Returning to a visible document triggers bounded stale-query revalidation, not a global provider refresh.
- Manual refresh calls the collection request operation and observes its run; it does not invalidate every cache before acceptance.
- Successful mutations invalidate only documented affected query keys. Cross-feature invalidation is maintained in one synchronized matrix.
- API network/offline errors leave last known data visibly stale/possibly outdated and expose a safe retry. They never synthesize zeros.

### 3.8 Authentication and API-token workflows

Session bootstrap states are `checking`, `authenticated`, `unauthenticated`, `setup_required`, `expired`, `maintenance`, and `failed`. Exact names are P02 internal presentation states, mapped one-to-one from synchronized P01 outcomes.

Login:

1. Load login status through the generated client against the real service.
2. Accept the dashboard password in a password input with password-manager-compatible semantics.
3. Submit only to the same-origin generated-client login operation.
4. Never store, log, echo, measure, or retain the submitted value after request completion.
5. On success, replace history and navigate to an allowlisted local return route.
6. On invalid credentials, show the same generic response for all invalid cases; respect throttling.

Logout uses the generated operation with CSRF, clears UI cache and non-sensitive ephemeral state after the server outcome, replaces history, and renders login. It does not imply provider logout.

Expiry handling:

- A synchronized `dashboard_authentication_required` response triggers one
  dashboard-session transition, cancels/settles mutations safely, clears
  protected server cache, and shows the dashboard-login recovery screen.
- A synchronized `provider_reauthentication_required` response preserves the
  dashboard session and unrelated caches, marks only the affected provider
  account/profile, and offers the approved reauthentication workflow when
  eligible.
- Multiple concurrent 401 responses do not create redirect loops or repeated announcements.
- Safe route intent may be retained in memory; form payloads, resource labels, search content, and secrets are discarded.
- After real login, a safe idempotent GET route may resume. Mutations are never automatically replayed.

API-token workflow:

- List responses contain summary fields only.
- Create/rotate requires explicit name/scopes/expiry review and CSRF.
- Plaintext appears exactly once in a dedicated modal after a successful new issuance. It is not put in the URL, DOM attributes outside the controlled field, logs, analytics, storage, clipboard automatically, or query cache.
- Copy requires an explicit user gesture and a warning that clipboard is outside AgentMonitor control. Closing, navigating, refreshing, or acknowledging destroys the UI reference; the token cannot be retrieved again.
- The modal cannot be reopened with plaintext. Replayed idempotency returns a safe non-secret conflict/summary.
- Rotate explains predecessor revocation/transition. Revoke confirms the safe name/prefix and terminal effect.
- Swagger guidance tells the user to paste a scoped token into authenticated Swagger UI and notes `persistAuthorization=false`; P02 does not transfer the token.

### 3.9 Error containment and recovery

- App-shell failure renders a minimal accessible local error with build version and correlation/remediation when safe.
- Route and panel error boundaries isolate render failures; one malformed optional panel cannot remove navigation or critical global state.
- Generated-client decoding/schema incompatibility is a high-severity compatibility error, not a generic empty state.
- RFC 9457 safe codes map centrally to user text and remediation. Unknown codes show a generic safe message plus correlation ID.
- No stack, raw response, SQL, filesystem path, provider output, request header/cookie, submitted form, or browser exception detail enters UI text or persisted evidence.
- Conflict recovery refetches the authoritative resource, displays changed state, and asks the user to reapply intent. It does not merge business fields in the browser.
- Failed downloads, expired artifacts, maintenance, and read-only mode have explicit safe outcomes.

## 4. Public and consumed contracts

### 4.1 Published surface

P02 publishes no backend, provider, event, persistence, or public API contract. Its externally observable surface is the built web application and its accessibility/route behavior. Deep-link route shapes and stable user workflows are product behavior and receive compatibility review, but they are not substitutes for `CTR-API-001`.

Internal P02 feature exports are private to the frontend build. They cannot be consumed by the backend or treated as cross-module business contracts.

### 4.2 Consumed contracts

| Contract | Required status/version | P02 use | Failure behavior |
|---|---|---|---|
| CTR-UI-001 `generated-client.v1` | `proposed_aligned` 1.0.0 | All HTTP operations and DTOs | Build fails on missing/drift/incompatible client; no handwritten fallback |
| CTR-API-001 `/api/v1` | `proposed_aligned` 1.0.0 | Resource queries/mutations/problems/pagination/jobs/downloads | Unknown major or decode failure becomes compatibility error |
| CTR-API-002 browser session/CSRF | `proposed_aligned` 1.0.0 | Login/session bootstrap/logout/CSRF/expiry | Fail closed to login/recovery; no bearer substitution |
| CTR-API-003 bearer scheme | `proposed_aligned` 1.0.0 | Token-management explanation and Swagger guidance only | UI normal session never uses/stores bearer token |
| CTR-FND-007 build metadata as exposed through API/build injection | `proposed_aligned` 1.0.0 | Frontend/app/API/client version diagnostics | Missing required build identity is visible and may block readiness |
| CTR-FND-008 evidence summary | `proposed_aligned` 1.0.0 | P02 handoff/test status | Blocked/Not Run cannot collapse into Passed |

P02 does not consume `CTR-IAM`, `CTR-REG`, `CTR-COL`, `CTR-CAP`, `CTR-RUN`, `CTR-ALERT`, or `CTR-OPS` source packages. P01 maps synchronized application views into `CTR-API-001`; the generated client is P02's only typed data boundary.

### 4.3 Required P01/OpenAPI synchronization matrix

Exact routes, `operationId` values, schemas, and HTTP outcomes belong to P01. Before a P02 feature increment starts, P01 must provide generated operations covering the following semantics:

| P02 feature | Required query semantics | Required mutation semantics | Mandatory state/provenance fields |
|---|---|---|---|
| Auth | session/bootstrap status; current session; safe session list | login, logout, password change if approved, revoke session | expiry, setup state, safe errors, CSRF handshake |
| Tokens | paginated token summaries and scope catalog | create, rotate, revoke | one-time issue union, prefix/fingerprint, scopes, expiry/revocation/version |
| Command | global health, alert counts, capacity aggregation, active-session summary, forecasts/incidents | optional explicit global refresh request only | completeness, generated/observed time, freshness, explanation links |
| Organizations | list/detail and server aggregates | create/rename/reorder/archive/restore | version/ETag, lifecycle, Ungrouped semantics, permission/action eligibility |
| Accounts | list/detail/resources/profiles/discovery/identity history | register/rename/move/monitor/archive/restore/confirm association/start eligible reauth | masked fields, identity/auth states, protected profile, completeness, version |
| Providers | providers/installations/capability matrix | discovery request only if separately approved | version compatibility, stability, unsupported/unavailable/unknown |
| Capacity | native quota/budget windows/current health/forecast/history | none except collection refresh through M04 | exact units/money, field state, provenance, freshness, precision/confidence, derivation |
| Sessions | tree/list/detail/history/correlation evidence summary | explicit correlation confirm/invalidate and approved stall-policy update | node/aggregate distinction, inferred confidence, safe metadata, hierarchy conflicts |
| Alerts | notifications/counts/rules/alerts/history | read/ack/snooze/rule changes using synchronized semantics | lifecycle, unread, evidence refs, scope/precedence, versions |
| Collectors | aggregate/target health, requests/runs/history | manual refresh request | run/job status, costs/warnings, retry eligibility, backoff/freshness |
| Diagnostics | health/readiness/versions/config-safe summary/audit | diagnostic/export job creation | component completeness, safe reason, versions, expiry/safety state |
| Backups/exports | backup/export/job lists/details and bounded authenticated download | manual backup and export; no browser restore | checksum/integrity/schema/status/expiry, no local path |
| Settings | timezone and approved user-editable configuration with effective source | versioned updates | validation, effective scope/source, optimistic concurrency |

Every list needs deterministic cursor pagination, bounded filters and page size. Every mutation needs declared permission, CSRF behavior, idempotency/version policy, problem outcomes, and safe action eligibility. Every metric-like response needs field-state and provenance rules. Structural OpenAPI examples cannot be rendered as live dashboard data.

### 4.4 Generated-client wrapper contract

`shared/api` may provide only:

- same-origin base selection supplied by the served application, never an arbitrary user URL in V1;
- browser cookie inclusion as generated transport supports it;
- CSRF acquisition/rotation/attachment exactly per CTR-API-002;
- validated correlation-ID propagation and safe extraction;
- RFC 9457 problem classification without raw-body logging;
- bounded request cancellation and feature-level timeout signaling;
- authenticated artifact download behavior if the generator cannot safely stream it directly;
- generated operation re-export through typed feature gateways.

It cannot provide generic `request(path, body)`, accept arbitrary URLs/headers, retry mutations invisibly, log payloads, cache bearer tokens, add provider credentials, coerce nulls, or convert unknown enums to known states.

### 4.5 Contract compatibility and change assessment

This plan proposes no breaking contract. It records P02 consumer requirements for first-version `CTR-API-001..003` and `CTR-UI-001` synchronization.

Contract review must freeze:

1. generated output ownership/path/tool/version and strict compile/drift gates;
2. cookie/CSRF/session/bootstrap/expiry/logout sequence;
3. one-time API-token response and non-replay semantics;
4. resource operation inventory, permission/action-eligibility vocabulary, pagination, filters, versions, and problems;
5. global aggregate projections so P02 never recomputes business truth;
6. provenance/explanation/field-state/completeness shapes common across relevant API resources;
7. artifact download behavior without exposing paths or credentials;
8. frontend/API/client/build version compatibility behavior;
9. cross-feature invalidation matrix after mutations;
10. whether low-frequency SSE is omitted from V1 UI until ordinary REST is complete. This plan recommends REST polling first.

Any later removal/rename/unit/nullability/state-meaning change in an API field is breaking and requires the API versioning workflow, regenerated client, consumer migration, and ADR where required.

## 5. Data and persistence

### 5.1 Server-owned data only

P02 owns no persistent business data. Organizations, accounts, telemetry, sessions, alerts, settings, tokens, backups, jobs, and audits remain server-owned. The UI never opens SQLite, ships a database driver, embeds SQL, or maintains an offline replica.

### 5.2 Browser-resident state

Allowed ephemeral state:

- route and allowlisted filter selection;
- open/closed panel state;
- current pagination cursor stack for the active route;
- unsaved non-secret form fields while the form is mounted;
- in-memory generated-client/query cache;
- one-time API token only within the successful issue modal lifecycle;
- focus-return and safe route-intent references.

Prohibited browser persistence:

- password, session cookie access, CSRF secret beyond synchronized in-memory/cookie use, API bearer token, provider credential, OTP/MFA/recovery code;
- telemetry, account labels, provider identities, project paths, process/session metadata, alerts, diagnostics, raw problems, or one-time token;
- query-cache persistence, service-worker response caching, IndexedDB/localStorage/sessionStorage business state;
- form drafts containing identity/diagnostic/search data after navigation or expiry.

A future decision to persist benign display preferences must allocate a versioned key, privacy classification, migration/removal rule, and test. V1 can use system theme and server-owned timezone without browser storage.

### 5.3 Cache invalidation and deletion

Logout, session expiry, explicit password recovery/credential invalidation, API-major incompatibility, and account switch in a future multi-user design clear all query cache and sensitive ephemeral state. Browser history is replaced at auth boundaries. The UI cannot promise memory erasure, but it removes references and avoids additional copies.

No P02 migration exists. Changes to route/filter state must preserve backward-safe handling of old bookmarks by rejecting unknown keys and navigating to a safe authenticated default.

## 6. External and platform boundaries

### 6.1 Browser ↔ FastAPI boundary

All application data crosses same-origin generated HTTPS/HTTP transport to the real loopback FastAPI server. P02 never falls back to direct provider network calls. Timeouts and cancellation stop only the browser request; they do not claim to cancel a server job/provider operation unless the API exposes an approved cancellation action.

### 6.2 Provider and workstation boundary

P02 has no direct provider, CLI, process, filesystem, or operating-system boundary. Real provider/process evidence reaches P02 only after adapters, domain modules, persistence, P01, OpenAPI, and client generation. Browser tests claiming populated telemetry therefore require the full real chain.

### 6.3 Browser capabilities

- Clipboard: explicit user gesture for one-time API token only; failure leaves selectable plaintext until modal close. No automatic copy and no read-back.
- Downloads: generated/synchronized authenticated download flow; safe suggested filename from allowlisted metadata; never a server/local path.
- External re-auth link/device flow: only a server-returned allowlisted official flow descriptor; opening a new context is announced. The UI never scrapes the provider result.
- Notifications: in-dashboard only. Browser Notification API and service-worker push are not used in V1.
- Storage: no business/server cache persistence as section 5 states.
- Console: production error handling emits no server payload, identifiers, submitted input, or secret. Development source maps and logging receive security review.

### 6.4 Supported browsers/platforms

The exact browser/version matrix is chosen after foundation dependency/tool admission. Minimum planning requirement:

- one current supported Chromium-family browser fully verified on target Linux;
- a second engine if admitted and supportable without weakening gates;
- macOS verification in a real supported browser when the environment exists, otherwise explicitly Blocked;
- no assertion that headless-only execution proves all focus, contrast, font, or assistive-technology behavior.

## 7. Security and privacy

### 7.1 Trust boundaries and controls

| Threat | P02 control | Coordinating owner |
|---|---|---|
| Malicious site calls localhost | Same-origin requests, CSRF handshake, no wildcard/API bypass | P01/M01/DEP |
| XSS steals local data | React escaping, no raw HTML, strict CSP compatibility, no external scripts/CDNs | P01/P02 |
| Token/password leaks | No storage/logging/URL, controlled input/modal lifecycle, no auto clipboard | M01/P01/P02 |
| Stale cache misleads owner | Preserve producer freshness/completeness and explicit refetch state | M05/M04/P01/P02 |
| Unknown becomes zero | Discriminated states; no default/coercion | Producers/P01/P02 |
| Wrong-account re-auth | Intended identity display, explicit result, server eligibility and mismatch block | M02/M03/adapters/P01 |
| Sensitive path/content display | Generated schema allowlist, rendering allowlist, safe labels only | Producers/P01/P02 |
| Open redirect | Local route-manifest allowlist; no arbitrary return URL | P02/P01 |
| Clickjacking | UI supports P01 frame-denial/CSP; destructive controls confirm | P01/P02 |
| Supply-chain UI exfiltration | Minimal admitted locked dependencies, no telemetry/network side effects, SBOM/notices | Foundation/P02 |
| Screenshot/evidence leak | Sanitized allowlist; populated evidence remains owner-local and uncommitted | Test/P02 |

### 7.2 Authentication and authorization

The browser normal workflow uses only an HTTP-only session cookie. UI visibility is usability, never the authorization boundary; P01 enforces permission for every route. Hidden/disabled controls cannot substitute for server denial tests.

CSRF is attached only to state-changing browser operations defined by CTR-API-002. The UI rejects an unavailable CSRF state and requests a safe session refresh; it does not retry the mutation automatically.

API bearer tokens are managed as resources but are never used by the SPA for normal API calls. The one-time plaintext response is sensitive and excluded from query devtools, generic error boundaries, error reporting, DOM snapshots, screenshot automation, browser storage, and logs.

### 7.3 Input, rendering, and navigation safety

- Generated types and server validation remain authoritative; client validation improves feedback but does not broaden accepted values.
- Text is rendered as text. No `dangerouslySetInnerHTML`, Markdown/HTML renderer, template evaluation, or dynamic script/style URL is permitted without a new security review and requirement.
- URLs are same-origin route-manifest entries or server-classified official re-auth destinations. Schemes/hosts are allowlisted by P01/adapters; P02 performs defense-in-depth validation.
- Long labels/errors are bounded by API and visually wrap/truncate with accessible full safe text where allowed.
- Correlation IDs are displayed only as opaque safe strings and copied only explicitly.
- Download names strip/control path separators and use server-approved safe metadata.

### 7.4 Privacy and data-minimization proof

P02 must include a generated-schema/render-field review proving that no view or component reads or displays:

- prompts, responses, tool arguments/results, source code, arbitrary terminal output, arbitrary environment values, process memory, command lines;
- provider OAuth/API tokens, browser cookies, passwords, OTP/MFA/recovery codes, profile locators, raw identity evidence;
- raw provider payloads/responses, exception text, SQL, database paths, backup paths, configuration secret values, arbitrary logs;
- non-allowlisted account email/display identity or project paths.

Working-directory/project information appears only as the safe API label approved by M06/P01. UI tests and evidence use opaque aliases and sanitized local artifacts.

### 7.5 Security headers and build artifacts

P02 supplies CSP-compatible static assets: no inline executable script, eval, external runtime CDN, or unreviewed dynamic code. P01 serves security headers. Source maps, if produced, are local release artifacts with explicit disclosure policy; they cannot embed secrets/config/provider data. The built bundle is scanned for secret patterns, external URLs, analytics SDKs, and prohibited strings.

## 8. Configuration and operations

### 8.1 Configuration ownership

P02 proposes no `.env` key and accepts no browser runtime secret. Build-time environment substitution is forbidden for secrets and server endpoints. Same-origin API location and safe build metadata are supplied through the approved foundation/deployment mechanism.

Potential non-secret UI settings are server-owned and API-delivered:

- configured display timezone;
- approved page-size options within P01 maximums;
- alert/collector settings owned by their modules;
- feature availability derived from synchronized API capability/permission contracts.

Theme is dark in V1. Adding user theme persistence is not required and would need setting ownership/versioning.

### 8.2 Health and diagnostics

P02 contributes safe frontend build/client/OpenAPI version and a coarse render status to M08/P01 only through an approved mechanism. It does not send analytics, crash reports, browser fingerprints, performance beacons, or console dumps.

User-visible diagnostics include safe API-provided component/version/problem/correlation information. The UI itself can suggest reload, re-login, retry, inspect diagnostics, or contact the local operator. It cannot claim to repair database/provider/service state.

### 8.3 Canonical automation obligations

The following routines must be repository-owned, non-interactive, fail closed, and registered only after real implementation and execution. Exact shell syntax remains `TBD` until the foundation command registry verifies it; prose in this plan is not an operational command.

| Routine capability | Parent automation | Required behavior before P02 handoff |
|---|---|---|
| frontend dependency install | AUTO-BUILD/AUTO-QUALITY | Frozen lockfile install; no manifest drift; no lifecycle telemetry/network surprise |
| generated-client drift | AUTO-QUALITY | Generate from real running OpenAPI source, compare, strict compile, fail on manual edits/drift |
| frontend build | AUTO-BUILD | Production Vite build with approved runtime, metadata, CSP compatibility, bundle inventory, SBOM/notices |
| P02 browser suite | AUTO-TEST selector T4/P02 | Start real migrated SQLite + real FastAPI + built UI; run real browser; classify Passed/Failed/Blocked/Not Run |
| P02 accessibility suite | AUTO-TEST/AUTO-QUALITY | Keyboard/focus/semantic/contrast/reflow checks in built browser; automated findings plus manual matrix |
| frontend quality | AUTO-QUALITY | Deterministic format/lint/strict type/import-boundary/security/secret/dependency/license checks |
| prohibited UI patterns | AUTO-QUALITY | Fail on direct fetch, backend imports, handwritten DTO directory, prohibited mocks/fixtures, telemetry/analytics, raw HTML, storage violations |
| visual evidence | AUTO-TEST T4 | Capture only approved structural/owner-local sanitized evidence; dynamic real telemetry never committed as golden data |
| documentation | AUTO-DOCS-CHECK | Links, IDs, status, route/workflow docs, generated references, commands only after verified |
| release bundle | AUTO-RELEASE | Re-run client/build/security/license/browser gates and record every live/AT Blocked or Not Run item |

The test runner must use isolated AgentMonitor-owned configuration and database paths and must never read the operator's `.env` or production database. Creating a fresh real database and using production bootstrap/API workflows is allowed; inserting seeded/demo telemetry directly is not.

### 8.4 Operational behavior

- Closing the browser has no effect on the service or collection.
- UI deployment is a versioned static bundle coordinated with API/client compatibility.
- A frontend/API incompatibility displays a maintenance/upgrade error rather than attempting unsafe calls.
- Browser refresh/deep links are served by the native deployment without losing route behavior.
- Cache-control prevents sensitive authenticated API data from being reused as public static content.
- Upgrade, rollback, and recovery instructions are added only after their canonical commands exist and pass.

## 9. Test design before implementation

### 9.1 Test integrity and environment

Every T3/T4 scenario starts the production FastAPI application on an ephemeral loopback port, applies the real migration chain to a real temporary SQLite file, builds and serves the production frontend, and drives a real admitted browser. Authentication uses the production bootstrap/login flow. A fresh database is legitimate empty state; it is not seeded telemetry. Any populated capacity/session/provider state must come through real production collection against owner-controlled accounts/processes.

No Playwright route interception, mocked network, fake clock, fake repository, fake API, MSW, fixture JSON, recorded response, test-only endpoint, direct SQL state injection, sample account, seeded telemetry, or DOM-only browser substitute can count as evidence. Pure I/O-free formatting/presentation-policy functions may use constructed values but cannot claim a workflow or provider state works.

Tests that require naturally unavailable provider/auth/exhaustion/stale/failure states remain Blocked. They are never manufactured by spending credits, modifying default profiles, changing the owner database, or disrupting running agents without explicit owner authorization.

Each implementation increment records exact Red, Green, and post-refactor command/evidence IDs. A missing dependency/server/account is setup Blocked, not meaningful Red.

### 9.2 Authentication, token, navigation, and shell scenarios

| Test ID | Layer | Requirement | Real dependencies | Expected initial Red | Pass condition | Coordination |
|---|---|---|---|---|---|---|
| UI-AUTH-001 | T4 | FR-IAM-001, AC-UI-001 | Built UI, real API/SQLite, production bootstrap admin | Login route/workflow absent | Real password login establishes server session and opens command view | Local |
| UI-AUTH-002 | T4 | FR-IAM-001/003 | Same | Invalid login unsafe/absent | Wrong password shows generic failure, creates no session, leaks no identity | Local |
| UI-AUTH-003 | T4 | FR-IAM-003 | Same | CSRF wrapper absent | Browser mutation succeeds with real CSRF; absent/invalid proof fails safely | Joint P01 |
| UI-AUTH-004 | T4 | AC-UI-001 | Same | Logout absent | Logout revokes real session, clears cache/history, returns login | Local |
| UI-AUTH-005 | T4 | AC-UI-001/005 | Real short approved session policy and elapsed wall time | Expiry recovery absent | Real expiry yields one accessible recovery flow; no mutation replay | Local; no fake clock |
| UI-AUTH-006 | T4 | FR-IAM-001 | Fresh real database | Setup state absent | Uninitialized install shows safe operator bootstrap instruction, no web password setup | Local |
| UI-AUTH-007 | T4 | NFR-SEC-001 | Real throttling policy | Throttle UI absent | Real repeated invalid attempts show generic bounded Retry-After state | Security-approved rate test |
| UI-AUTH-008 | T4 | FR-IAM-003 | Two real browser contexts/sessions | Revocation handling absent | Revoked session transitions to login without resource leak | Local |
| UI-AUTH-009 | T4 | AC-UI-001 | Real password-change operation if approved | Workflow absent | Change requires current credential/CSRF and invalidates/rotates exactly per contract | Joint M01/P01 |
| UI-AUTH-010 | T4 | NFR-SEC-001 | Running browser | Return-route guard absent | Only allowlisted local route resumes; arbitrary URL is rejected | Local |
| UI-AUTH-011 | T4/T3 | AC-UI-001, AC-UI-005 | Real expired dashboard session | Provider flow is shown or state is conflated | `dashboard_authentication_required` alone clears protected cache and opens dashboard login | Joint M01/P01 |
| UI-TOKEN-001 | T4 | FR-IAM-004/005 | Real API/SQLite/session | Token list absent | Summary list never contains plaintext/digest | Local |
| UI-TOKEN-002 | T4 | FR-IAM-004 | Same | Create flow absent | Named scoped token created through real persistence and shown once | Local |
| UI-TOKEN-003 | T4/security | FR-IAM-004/005 | Same plus browser inspection | Secret lifecycle unsafe | Plaintext absent from URL/storage/query cache/console/network logs/screenshot after close | Security review |
| UI-TOKEN-004 | T4 | AC-UI-001 | Same | Rotation absent | Rotate yields one new plaintext and predecessor state exactly per API | Local |
| UI-TOKEN-005 | T4 | FR-IAM-004 | Same | Revocation absent | Revoke updates summary and real bearer use is denied | Joint P01 |
| UI-TOKEN-006 | T4 | FR-IAM-004 | Real scoped token | Scope UI absent | Scope descriptions and attenuation errors are accurate/actionable | Local |
| UI-TOKEN-007 | T4 | FR-IAM-006 | Authenticated real Swagger | Guidance absent | User can authorize Swagger manually; UI never transfers/stores token | Owner manual |
| UI-TOKEN-008 | T4 | NFR-SEC-001 | Clipboard-capable real browser | Copy unsafe/absent | Copy occurs only after gesture; denial leaves selectable value safely | Local |
| UI-TOKEN-009 | T4 | FR-IAM-004 | Real issued token then reload | Secret incorrectly recoverable | Reload cannot recover plaintext and shows safe summary only | Local |
| UI-TOKEN-010 | T4 | NFR-RES-001 | Real idempotency replay | Replay mishandled | Replayed create/rotate never reveals prior plaintext and gives safe outcome | Joint P01 |
| UI-NAV-001 | T4 | FR-UI-002 | Real authenticated app | Route shell absent | Every required top-level route is reachable and has unique heading/title | Local |
| UI-NAV-002 | T4/a11y | FR-UI-004 | Same | Focus unmanaged | Route navigation moves focus predictably and skip link works | Local |
| UI-NAV-003 | T4 | NFR-SEC-001 | Same | Unsafe query handling | Unknown/unsafe URL keys are discarded without reflecting content | Local |
| UI-NAV-004 | T4 | NFR-RES-001 | Real page reload/static service | Deep-link fallback absent | Authenticated deep link reloads correct route without server 404 | Joint DEP |
| UI-NAV-005 | T4 | AC-UI-005 | Unauthorized browser | Guard absent | Protected routes show login without disclosing resource detail | Local |
| UI-NAV-006 | T4 | FR-UI-003 | Real global summaries | Critical status lost on navigation | Critical strip remains discoverable across authenticated routes | Live state when available |
| UI-NAV-007 | T4 | FR-UI-002 | Real bounded list | Pagination/filter URL unsafe | Allowlisted filters round-trip; labels/secrets do not enter URL | Local |
| UI-NAV-008 | T4 | NFR-RES-001 | Real route module load failure only if naturally reproducible | Error boundary absent | Safe route error does not remove shell; otherwise Blocked | No injected chunk failure |

### 9.3 Global, registry, provider, and authentication scenarios

| Test ID | Layer | Requirement | Real dependencies | Expected initial Red | Pass condition | Coordination |
|---|---|---|---|---|---|---|
| UI-CMD-001 | T4 | FR-UI-003 | Fresh real DB | Command empty state absent | Truthful onboarding has no metric-like placeholders | Local |
| UI-CMD-002 | T4/T6 | AC-UI-002 | Real enrolled accounts/observations | Global composition absent | Health/alerts/capacity/sessions render from real API | Owner/live |
| UI-CMD-003 | T4 | FR-ORG-003 | Real API aggregates | Browser recomputes/omits | API-provided global/org totals display with completeness | Owner/live |
| UI-CMD-004 | T4 | FR-UI-003 | Real critical alert | Priority unclear | Critical warning is immediately visible with text/icon/link | Owner/natural state |
| UI-CMD-005 | T4 | FR-COL-004 | Real mixed freshness | Freshness missing | Global and panel freshness/source are visible and not conflated | Owner/live |
| UI-CMD-006 | T4 | NFR-RES-001 | Real API with one degraded component | Failure cascades | Healthy panels work and degraded panel shows safe cause | Natural/approved isolated state |
| UI-CMD-007 | T4 | FR-UI-005 | Real denominator/no-denominator resources | Decorative gauges appear | Gauges only render for bounded values; exact text always present | Owner/live |
| UI-CMD-008 | T4/a11y | FR-UI-004 | Real mixed health | Color-only meaning | Matrix and summaries remain understandable without color | Local/live |
| UI-CMD-009 | T4 | AC-UI-005 | Real partial aggregate | Partial appears complete | Missing scopes/components are named without fake zeros | Natural state |
| UI-CMD-010 | T4 | FR-UI-003 | Real active sessions | Session summary absent | Parent aggregate and active attention state link to session tree | Owner/live |
| UI-ORG-001 | T4 | FR-ORG-001 | Real API/SQLite/session | Organization creation absent | Create persists and appears in server order | Local through UI |
| UI-ORG-002 | T4 | FR-ORG-001 | Existing real org | Rename absent | Rename persists and histories/views retain stable opaque ID | Local |
| UI-ORG-003 | T4 | FR-ORG-001 | Three UI-created orgs | Reorder absent | Explicit order persists after reload | Local |
| UI-ORG-004 | T4 | FR-ORG-001/002 | Empty UI-created org | Archive absent | Archive/restore lifecycle is explicit and real | Local |
| UI-ORG-005 | T4 | FR-ORG-001 | Org with real account | Unsafe archive | API conflict is actionable; UI does not hide assigned account | Owner/local |
| UI-ORG-006 | T4 | FR-ORG-002 | Ungrouped real account | Fake group behavior | Ungrouped is shown as scope, not mutable organization | Owner/live |
| UI-ORG-007 | T4/T6 | FR-ORG-003 | Real organization state | Aggregate detail absent | Capacity/spend/alerts/sessions are producer projections | Owner/live |
| UI-ORG-008 | T4 | NFR-COMP-001 | Concurrent real browser edit | Conflict overwrites | Stale version refetches and requests informed retry | Two browsers |
| UI-ACC-001 | T4 | FR-ACC-001/002 | Real discovered/manual candidate | Registration absent | Account registered with safe identity/friendly name | Owner/live |
| UI-ACC-002 | T4 | FR-ACC-002 | Real account | Rename/move absent | Rename and group move persist without losing linked history | Owner/live |
| UI-ACC-003 | T4 | FR-ACC-003 | Real account | Monitor toggle absent | Effective preference/reason updates; no history deleted | Owner/live |
| UI-ACC-004 | T4 | FR-ACC-004 | Multi-resource real account | Resources conflated | Subscription/API/project/profile relationships remain distinct | Owner/live |
| UI-ACC-005 | T4/T6 | FR-ACC-005 | Real discovery | Candidates hidden | Partial/complete discovery status and candidates render truthfully | Owner/live |
| UI-ACC-006 | T4/T6 | FR-ACC-006, AC-PROC-003 | Ambiguous real candidate | UI guesses association | No account preselection; explicit safe confirmation required | Owner/live |
| UI-ACC-007 | T4 | FR-ACC-003 | Real archived account | Lifecycle conflated | Archived, disabled, and monitoring-ineligible differ | Owner/live |
| UI-ACC-008 | T4 | AC-UI-005 | Withheld/unknown identity | Blank appears broken | Masked/withheld/unknown field-state labels are explicit | Owner/live |
| UI-ACC-009 | T4 | FR-ACC-001 | 100 real accounts if available | Pagination not scalable | Server pagination/filtering remains usable; otherwise Blocked | No synthetic accounts |
| UI-ACC-010 | T4 | FR-ACC-002 | Real history | History link absent | Rename/move history view uses bounded API data | Owner/live |
| UI-ACC-011 | T4 | FR-SAFE-002 | Built UI | Unsafe account-switch action present | No running-agent credential switch/routing action exists | Local inspection |
| UI-ACC-012 | T4 | NFR-PRIV-001 | Real account | Sensitive fields rendered | Only allowlisted masked labels appear | Security/owner |
| UI-PAUTH-001 | T4/T6 | FR-AUTH-001 | Real auth-health states | States incomplete | All API auth states have distinct text/icon/remediation | Naturally available matrix |
| UI-PAUTH-002 | T4 | FR-AUTH-005 | Protected default profile | Unsafe action present | No reauth/logout/mutation control; protection explained | Owner/live |
| UI-PAUTH-003 | T4/T6 | FR-AUTH-002/006 | Eligible managed profile | Reauth start absent | Official flow starts only after explicit action | Owner present |
| UI-PAUTH-004 | T4/T6 | FR-AUTH-004 | Reauth flow | Secret form present | UI never requests password/OTP/MFA/recovery/provider token | Owner/security |
| UI-PAUTH-005 | T4/T6 | FR-AUTH-003 | Successful reauth | Identity/history loss | Stable account/name/group/history remain after reauth | Owner/live |
| UI-PAUTH-006 | T4/T6 | FR-AUTH-003 | Wrong-account result naturally available | Mismatch hidden | Wrong-account blocks relink and displays safe intended/actual state | Blocked if unavailable |
| UI-PAUTH-007 | T4 | AC-UI-005 | Unsupported/unavailable reauth | Misleading button | State explains unsupported/unavailable; no action shown | Owner/live |
| UI-PAUTH-008 | T4 | NFR-SEC-001 | Browser/network/storage inspection | Auth data leak | No provider auth material reaches DOM/storage/log/evidence | Security/owner |
| UI-PAUTH-009 | T4/T6 | FR-AUTH-001..006, AC-UI-005 | Real provider reauthentication-required response while dashboard session is valid | Dashboard is logged out or unrelated cache cleared | `provider_reauthentication_required` marks only affected provider scope and dashboard session remains valid | Owner/P01/M02 |

### 9.4 Capacity, budget, history, session, and collection scenarios

| Test ID | Layer | Requirement | Real dependencies | Expected initial Red | Pass condition | Coordination |
|---|---|---|---|---|---|---|
| UI-CAP-001 | T4/T6 | FR-QUOTA-001 | Real quota observations | Windows omitted/merged | Every observable native window is separate with units/reset/status | Owner/live |
| UI-CAP-002 | T4/T6 | FR-QUOTA-002 | Incompatible real windows | False total rendered | No universal sum/gauge; scopes remain distinct | Owner/live |
| UI-CAP-003 | T4/T6 | FR-QUOTA-003 | Real health projection | Health missing | Exact normalized state and constraining window display | Owner/live |
| UI-CAP-004 | T4/T6 | FR-QUOTA-004, AC-UI-006 | Real provenance | Explanation absent | Source/kind/time/version/precision/confidence visible | Owner/live |
| UI-CAP-005 | T4/T6 | FR-QUOTA-005 | Real sufficient forecast | Derived shown authoritative | Forecast/uncertainty/inputs/method are labeled | Owner/live |
| UI-CAP-006 | T4/T6 | FR-UI-005 | Real bounded and unbounded values | Invalid gauge | Gauge only for real denominator and includes exact text/table | Owner/live |
| UI-CAP-007 | T4/T6 | AC-LIVE-005 | Provider authoritative comparison | Mismatch hidden | Displayed value/time/unit matches reconciled API evidence | Owner countersign |
| UI-CAP-008 | T4/T6 | AC-UI-005 | Real unsupported/unknown/stale cases | State becomes blank/zero | Each state remains distinct and actionable | Natural state |
| UI-CAP-009 | T4/T6 | AC-UI-006 | Derived value detail | Input link absent | Inputs and timestamps open safe explanation | Owner/live |
| UI-CAP-010 | T4 | NFR-RES-001 | One malformed/incompatible API response caused by real version mismatch | Dashboard collapses | Compatibility error isolated; no coerced rendering | Blocked unless naturally testable |
| UI-BUD-001 | T4/T6 | FR-BUDGET-001/002 | Real API billing account | Budget absent | Spend/available/credit/limits/period/reset reflect supported fields | Owner/live |
| UI-BUD-002 | T4/T6 | FR-BUDGET-003 | Real supported breakdown | Breakdown invented/absent | Only provider-supported dimensions appear | Owner/live |
| UI-BUD-003 | T4 | FR-BUDGET-004 | Real exact monetary values | Binary/display rounding unsafe | Currency/precision display follows generated exact contract | Owner/live |
| UI-BUD-004 | T4/T6 | FR-BUDGET-005 | Subscription and API pools | Pools merged | Separate sections and no combined availability claim | Owner/live |
| UI-BUD-005 | T4/T6 | FR-BUDGET-006 | Unsupported dimension | Empty chart | Explicit unsupported with capability source | Owner/live |
| UI-BUD-006 | T4/T6 | FR-BUDGET-002 | Insufficient forecast inputs | False forecast | Insufficient-input outcome, no exhaustion date | Owner/live |
| UI-BUD-007 | T4/a11y | AC-UI-004 | Real money/time chart | Chart-only | Accessible summary and exact table match visible data | Owner/live |
| UI-BUD-008 | T4 | NFR-PRIV-001 | Key dimension safely exposed | Raw key shown | Only provider-safe identifier/masked value appears | Security/owner |
| UI-HIST-001 | T4/T6 | FR-HIST-002, AC-HIST-001 | Real retained observations | Chart path absent | Range request renders real trend plus exact table | Owner/live |
| UI-HIST-002 | T4 | FR-HIST-005 | Real timestamps and configured timezone | Time ambiguous | Local timezone label and UTC detail are correct | Local |
| UI-HIST-003 | T4 | FR-HIST-002 | Real gaps | Lines interpolate falsely | Gaps remain visible in chart/table | Owner/live |
| UI-HIST-004 | T4 | FR-HIST-002 | Real paginated history | Unbounded fetch | Cursor/range stays bounded and navigation works | Owner/live |
| UI-HIST-005 | T4 | FR-HIST-004 | Real export job | Export absent | Job status/safety/expiry and authenticated download work | Local production workflow |
| UI-HIST-006 | T4 | AC-UI-005 | Empty real history | Placeholder chart | Truthful empty message and no fake series | Fresh DB/account |
| UI-HIST-007 | T4 | AC-UI-005 | Partial real history response | Partial hidden | Missing buckets/scopes are disclosed | Natural state |
| UI-HIST-008 | T4/a11y | FR-UI-004 | Real chart | Keyboard/table mismatch | Table accessible and values/range/units equivalent | Owner/live |
| UI-HIST-009 | T4/perf | NFR-PERF-001 | Largest real retained set available | Interaction too slow | Measured bounded range meets approved budget | Scale target Blocked if unavailable |
| UI-RUN-001 | T4/T5/T6 | FR-DISC-005, AC-PROC-002 | Real Claude/Codex/Ollama trees | Tree absent | Correct expandable parent/child structure | Owner/Linux |
| UI-RUN-002 | T4/T5 | FR-DISC-005 | Real aggregate | Unknown child treated zero | Aggregate shows included/excluded/unknown counts | Owner/Linux |
| UI-RUN-003 | T4/T5 | FR-DISC-002/006 | Real process/session | Detail incomplete | Safe metadata fields/units/times render when available | Owner/Linux |
| UI-RUN-004 | T4/T5 | FR-STATE-001/002 | Real states | Inferred/definitive merged | State evidence/confidence distinction visible | Owner/Linux |
| UI-RUN-005 | T4/T5 | FR-STATE-003, AC-PROC-005 | Real possible stall naturally occurs | Stall absent/misleading | Possible-stall label shows threshold/evidence as inferred | Owner; Blocked if absent |
| UI-RUN-006 | T4/T5 | FR-STATE-004 | Real observable wait | Wait shown stuck | Waiting state remains distinct and not alarming as stall | Owner; Blocked if absent |
| UI-RUN-007 | T4/T5 | FR-DISC-004 | Real unresolved correlation | UI guesses | Unresolved state and safe confirmation action shown | Owner/Linux |
| UI-RUN-008 | T4/T5 | FR-DISC-004 | Real safe correlation evidence | Confirmation implicit | Explicit intended account/evidence summary required | Owner/Linux |
| UI-RUN-009 | T4/T5 | AC-PROC-004 | Browser/DOM/storage inspection | Content/path leak | No prohibited content/environment/raw path appears | Security/owner |
| UI-RUN-010 | T4/T5 | FR-STATE-001 | Real exited/crashed/error state | Terminal states conflated | Exact terminal/error state with safe cause/time | Owner/natural |
| UI-RUN-011 | T4/T5 | AC-UI-005 | Real orphan/cycle/permission state | Tree breaks | Conflict/orphan/denial renders safely without recursion failure | Natural; otherwise Blocked |
| UI-RUN-012 | T4/perf | NFR-PERF-001 | Up to 200 real concurrent processes if available | Tree unusable | Bounded rendering/navigation meets approved budget | Blocked without real scale |
| UI-COL-001 | T4 | FR-COL-005 | Real run history | Status vocabulary incomplete | Every run state/time/warning/capability renders distinctly | Owner/live |
| UI-COL-002 | T4/T6 | FR-COL-002 | Real eligible account | Manual refresh absent | Explicit request returns/opens real run resource | Owner/live |
| UI-COL-003 | T4 | FR-COL-002 | Duplicate real request | Duplicate jobs implied | Joined/queued/idempotent outcome displayed accurately | Owner/live |
| UI-COL-004 | T4/T6 | FR-COL-003 | Real provider backoff | Backoff hidden | Next eligible/reason visible; no blind retry | Natural state |
| UI-COL-005 | T4/T6 | FR-COL-004 | Real observation/run | Provenance absent | Source/versions/observed/collected/freshness visible | Owner/live |
| UI-COL-006 | T4/T6 | FR-COL-006 | Unsupported/unavailable capability | State treated failure/zero | Exact outcome and next action displayed | Owner/live |
| UI-COL-007 | T4 | FR-COL-008 | API stopped after real page load | Cached value appears current | Last known data is visibly stale/offline; no fake fallback | Local real service stop |
| UI-COL-008 | T4 | NFR-RES-001 | One real target failure | Global UI fails | Failure isolated to affected scope/provider | Natural/approved condition |
| UI-COL-009 | T4 | NFR-SEC-001 | Real manual refresh | Cost warning absent | API-provided rate/cost impact and permission eligibility shown | Owner/live |
| UI-COL-010 | T4 | AC-OPS-002 | Native service and browser | Browser owns polling work | Close browser; service collection continues; reopen shows real newer run | Joint DEP/M04 |

### 9.5 Alerts, operations, state, accessibility, visual, and automation scenarios

| Test ID | Layer | Requirement | Real dependencies | Expected initial Red | Pass condition | Coordination |
|---|---|---|---|---|---|---|
| UI-ALERT-001 | T4 | FR-ALERT-005 | Real persisted alerts | Console absent | Active/history filters and lifecycle fields work | Real API/SQLite |
| UI-ALERT-002 | T4 | AC-ALERT-002 | Real alert | Ack absent | Explicit acknowledge persists; recovery remains distinct | Real workflow |
| UI-ALERT-003 | T4 | AC-ALERT-002 | Real alert | Snooze absent | Snooze/expiry persist and are visible | Real workflow/wall time |
| UI-ALERT-004 | T4 | AC-ALERT-002 | Real repeated condition | Duplicate cards | One alert with occurrence/lifecycle updates from server | Natural/real event |
| UI-ALERT-005 | T4 | FR-ALERT-005 | Real recovery | Recovery hidden | Recovered state/time/history visible | Natural/real event |
| UI-ALERT-006 | T4 | FR-ALERT-005 | Real unread notification | Fetch mutates read | Viewing list does not mark read; explicit action does | Real API/SQLite |
| UI-ALERT-007 | T4 | FR-ALERT-001/002 | Real rules/settings | Precedence obscured | Effective threshold and override source display accurately | Real configuration |
| UI-ALERT-008 | T4/T6 | AC-ALERT-003 | Real stale alert | Stale condition absent | Alert links to exact collector/capacity evidence | Owner/natural |
| UI-ALERT-009 | T4/T6 | AC-ALERT-003 | Real auth-required alert | Auth action wrong | Links to intended account/profile auth center | Owner/natural |
| UI-ALERT-010 | T4/a11y | FR-UI-004 | Real severity mix | Color-only | Severity/lifecycle understood in monochrome/AT | Local/live |
| UI-ALERT-011 | T4 | FR-ALERT-006 | Built UI | Deferred delivery controls present | No email/native/messenger controls/endpoints invoked | Local inspection |
| UI-ALERT-012 | T4 | AC-UI-005 | No real alerts | Fake incident list | Truthful empty state without sample incidents | Fresh DB |
| UI-OPS-001 | T4 | FR-OPS-002 | Real health endpoint | Health absent | Component state/cause/check time and readiness show | Local |
| UI-OPS-002 | T4 | FR-OPS-006 | Real build metadata | Versions absent | App/schema/frontend/API/client/adapters show with unknown handling | Local/live |
| UI-OPS-003 | T4 | FR-OPS-003 | Real backup cycle | Backup status absent | Slots/checksum/integrity/freshness render without paths | Joint M08 |
| UI-OPS-004 | T4 | FR-SAFE-001 | Real manual backup | Action absent | CSRF/idempotent job starts and progress is truthful | Joint M08 |
| UI-OPS-005 | T4 | FR-OPS-004 | Built UI | Unsafe restore action appears | No browser restore execution control exists | Local inspection |
| UI-OPS-006 | T4 | FR-HIST-004 | Real export/diagnostic job | Job UI absent | Status/completeness/safety/expiry/download are accurate | Joint M08 |
| UI-OPS-007 | T4/security | FR-OPS-005 | Real artifacts/summaries | Path/secret leak | No path/config value/raw log/secret appears | Security/M08 |
| UI-OPS-008 | T4 | AC-UI-005 | Real maintenance state | Writes remain active | Maintenance banner and unsafe actions disabled | Joint DEP/M08 |
| UI-OPS-009 | T4 | NFR-COMP-001 | Real version incompatibility when testable | Generic failure | Explicit incompatible version/client message | Joint P01/FND |
| UI-OPS-010 | T4/T7 | AC-OPS-002 | Native service | Browser closure affects service | Closing browser does not stop collection | Joint DEP/M04 |
| UI-OPS-011 | T4 | NFR-RES-001 | One real degraded provider/component | Whole dashboard down | Overall health degrades while independent UI works | Natural state |
| UI-OPS-012 | T4 | FR-OPS-002 | Real sanitized correlation problem | Diagnostics unclear | Safe code/correlation/remediation display, no raw error | Local |
| UI-STATE-001 | T4 | AC-UI-005 | Fresh real DB | Empty state missing | Empty is distinct from failure and offers valid action | Local |
| UI-STATE-002 | T4 | AC-UI-005 | Real in-flight request | Loading inaccessible | Busy named skeleton contains no telemetry-like value | Real timing; Blocked if unobservable |
| UI-STATE-003 | T4/T6 | AC-UI-005 | Real partial result | Partial hidden | Available and missing portions/reasons both visible | Natural state |
| UI-STATE-004 | T4/T6 | AC-UI-005 | Real stale observation | Stale appears current | Stale label/time/source persistent | Natural/waited state |
| UI-STATE-005 | T4/T6 | AC-UI-005 | Real unsupported capability | Blank/zero | Unsupported classification and source visible | Owner/live |
| UI-STATE-006 | T4 | AC-UI-005 | Expired/no session | Unauthorized leaks | Auth recovery with no resource details | Local |
| UI-STATE-007 | T4 | AC-UI-005 | Real permission denial | Forbidden becomes login loop | Safe forbidden state and navigation | Real scoped context if available |
| UI-STATE-008 | T4 | AC-UI-005 | Real API stopped | Network error becomes empty | Safe offline/error and bounded retry | Local service stop |
| UI-STATE-009 | T4 | AC-UI-005 | Real stale version conflict | User input overwritten | Refetch plus explicit reapply decision | Two browsers |
| UI-STATE-010 | T4 | AC-UI-005 | Real maintenance/not-ready | Generic spinner | Maintenance state/action policy clear | Joint M08 |
| UI-STATE-011 | T4/T6 | AC-UI-005 | Real unknown value | Unknown becomes zero | Unknown and evidence need display | Owner/live |
| UI-STATE-012 | T4/T6 | AC-UI-005 | Real unavailable value | Unavailable becomes unsupported | Temporary unavailable remains distinct | Owner/live |
| UI-ERR-001 | T4 | NFR-RES-001 | One real panel request fails while other real requests succeed | Panel failure removes route | Failed panel is isolated; shell and successful panels remain usable | Natural or safely induced real service boundary |
| UI-ERR-002 | T4 | AC-UI-005 | Real RFC 9457 validation problem | Raw/generic error | Safe code, field reason, and correlation render accessibly | Joint P01 |
| UI-ERR-003 | T4 | NFR-RES-001 | Real HTTP timeout at production boundary | Infinite spinner | Bounded timeout state preserves last data freshness and offers safe retry | Natural/approved isolated condition |
| UI-ERR-004 | T4/security | NFR-OBS-001 | Real internal-error problem | Sensitive detail appears | Only safe remediation and correlation ID render; console remains clean | Joint P01/security |
| UI-ERR-005 | T4 | NFR-COMP-001 | Real client/API incompatibility in isolated upgrade test | Empty/coerced view | Compatibility state blocks affected writes and identifies upgrade need | Joint P01/DEP |
| UI-ERR-006 | T4 | NFR-RES-001 | Real artifact download failure/expiry | Navigation breaks | Download error stays in workflow and preserves safe job state | Joint M08/P01 |
| UI-ERR-007 | T4 | AC-UI-005 | Real 429 with `Retry-After` | Blind retry loop | Countdown/remediation is bounded and no hidden retry occurs | Joint P01/provider condition |
| UI-ERR-008 | T4/a11y | AC-UI-004/005 | Real route and form errors | Error not announced/focus lost | Error heading/summary receives appropriate focus and fields remain identifiable | Local real API validation |
| UI-RESP-001 | T4 | FR-UI-001 | 1920×1080 real browser/data | Layout absent | Dense command composition works without overlap/lost meaning | Local/live |
| UI-RESP-002 | T4 | AC-UI-003 | 1440×900 | Reflow absent | Priorities preserved and detail accessible | Local/live |
| UI-RESP-003 | T4 | AC-UI-003 | 1280×720 | Reflow absent | Critical header/panels usable | Local/live |
| UI-RESP-004 | T4 | AC-UI-003 | 1024×768 | Reflow absent | Navigation/grid/table regions usable | Local/live |
| UI-RESP-005 | T4 | AC-UI-003 | 768×1024 | Reflow absent | Stack/disclosures preserve state meaning | Local/live |
| UI-RESP-006 | T4 | FR-UI-001 | 390×844 | Fallback absent | Login/critical/accounts/sessions/alerts usable | Local/live |
| UI-RESP-007 | T4/a11y | WCAG reflow | 1920×1080 at 200% zoom | Overflow hides content | Critical meaning/actions remain reachable | Local |
| UI-RESP-008 | T4/a11y | WCAG text spacing | Real browser override styles | Clipping/overlap | Text spacing and long labels do not lose content | Local |
| UI-A11Y-001 | T4/a11y | AC-UI-004 | Real browser keyboard | Keyboard traps | All workflows keyboard operable with visible focus | Manual+automated |
| UI-A11Y-002 | T4/a11y | AC-UI-004 | Accessibility tree | Names/landmarks absent | Unique names and landmark/heading structure pass | Local |
| UI-A11Y-003 | T4/a11y | AC-UI-004 | Real computed styles | Contrast fails | Text/components/focus/charts meet AA | Admitted checker+manual |
| UI-A11Y-004 | T4/a11y | FR-UI-004 | Forced colors/monochrome | State lost | Text/icon/structure preserve state | Real browser |
| UI-A11Y-005 | T4/a11y | Dashboard spec | Reduced motion | Motion persists | Nonessential animation removed | Real browser media setting |
| UI-A11Y-006 | T4/a11y | Dashboard spec | Real chart/table | Alternative absent | Summary and exact table agree with API values | Owner/live |
| UI-A11Y-007 | T4/a11y | AC-UI-004 | Real dialogs | Focus escapes | Focus trap/name/restore/Escape behavior correct | Local |
| UI-A11Y-008 | T4/a11y | AC-UI-004 | Real validation problems | Errors inaccessible | Summary/field links/status announcement work | Local |
| UI-A11Y-009 | T4/a11y/T5 | WCAG screen-reader behavior | Real Linux screen reader/browser | Announcements unclear | Login, navigation, alert, tree/table workflow understandable | Manual; tool availability explicit |
| UI-A11Y-010 | T4/a11y | WCAG target size | Real viewport/input | Targets undersized | Essential pointer targets meet approved AA interpretation | Local |
| UI-VIS-001 | T4/visual | FR-UI-001 | Built login/fresh empty app | Tokens/layout absent | Sanitized screenshots and geometry assertions match reviewed structure | No telemetry golden |
| UI-VIS-002 | T4/visual | AC-UI-003 | Real populated owner state | Density unusable | Owner-local review confirms hierarchy/readability at 1920×1080 | Screenshot uncommitted/sanitized |
| UI-VIS-003 | T4/visual | FR-UI-005 | Real data | Decorative controls | Review finds every visualization maps to real meaning | Local/live |
| UI-VIS-004 | T4/visual | FR-UI-004 | State matrix naturally available | Semantic colors misused | Warning/critical reserved and non-color cues present | Natural/Blocked gaps |
| UI-VIS-005 | T4/visual | Dashboard spec | Reduced motion/zoom | Visual regression | Reviewed modes show no obscured focus/content | Local |
| UI-DATA-001 | Quality/T4 | FR-UI-007 | Source/build/browser | Sample telemetry exists | Scan and browser prove no sample/demo account path | Local |
| UI-DATA-002 | Quality | NFR-TEST-002 | Test source | Fixture server/data exists | No provider/API fixture/recording/seeded telemetry framework | Local |
| UI-DATA-003 | T4 | AC-V1-008 | Fresh DB | Numeric placeholders render | No telemetry-like loading/empty value | Local |
| UI-DATA-004 | T4/T6 | AC-UI-002 | Populated UI | Origin cannot be proven | Every displayed telemetry subject traces to real API record | Owner/live |
| UI-DATA-005 | Security | NFR-PRIV-001 | Built DOM/network/storage | Prohibited content exists | Allowlist review finds no prohibited field | Security |
| UI-DATA-006 | Quality | NFR-PRIV-002 | Built bundle/network | Analytics/crash service present | No analytics, beacon, remote telemetry, or crash SDK | Local |
| UI-CONTRACT-001 | Build | NFR-API-002 | Real OpenAPI/generator | Client missing | Deterministic generation and strict compile pass | Joint FND/P01 |
| UI-CONTRACT-002 | Quality | NFR-API-002 | Source tree | Direct fetch/import exists | Boundary rule fails on any bypass and passes clean source | Local |
| UI-CONTRACT-003 | Build | AC-V1-003 | Intentional compatible API addition | Drift unchecked | Generated diff is additive and consumer compiles | Joint P01 |
| UI-CONTRACT-004 | Build | NFR-COMP-001 | Intentional breaking schema change in isolated gate test | Gate accepts break | Compatibility/client gate fails closed | Joint P01/FND |
| UI-CONTRACT-005 | T3/T4 | AC-V1-003 | Running real API/client | Runtime response unconstrained | Client calls conform to running OpenAPI | Joint P01 |
| UI-CONTRACT-006 | Quality | NFR-API-002 | Generated output | Manual patch possible | Generated directory ownership/drift rejects manual change | Local |
| UI-SEC-001 | T4/security | NFR-SEC-001 | Browser storage inspection | Sensitive data stored | Storage contains no session/token/telemetry/account data | Security |
| UI-SEC-002 | Build/security | NFR-SEC-001 | Production bundle | Secret/external endpoint present | Scan finds no secret/config value/unknown external URL | Security |
| UI-SEC-003 | T4/security | NFR-SEC-001 | Real errors | Raw body/stack in UI/console | Only safe problem/code/correlation appears | Security |
| UI-SEC-004 | T4/security | FR-IAM-007 | Real hostile Host/Origin tests | UI bypasses API denial | API rejects; UI exposes no workaround | Joint P01 |
| UI-SEC-005 | Quality/security | NFR-SEC-001 | Source/build | Raw HTML/dynamic script path exists | Prohibited rendering/execution patterns absent | Security |
| UI-SEC-006 | T4/security | NFR-PRIV-001 | Auth expiry/logout | Cache retains data | DOM/cache/history no longer expose protected data | Security |
| UI-SEC-007 | T4/security | FR-AUTH-004 | Provider reauth | Secret field exists | No prohibited provider credential input/control | Owner/security |
| UI-SEC-008 | T4/security | AC-PROC-004 | Real runtime views | Content/env/path leaks | Only approved metadata rendered | Owner/security |
| UI-SEC-009 | T4/security | FR-OPS-005 | Diagnostics/downloads | Path/content leaked | No local path/raw diagnostic/log value rendered | M08/security |
| UI-SEC-010 | Quality/security | NFR-PRIV-002 | Runtime network inspection | Undeclared outbound request | Only same-origin API and approved reauth navigation occur | Security |
| UI-SEC-011 | T4/security | NFR-SEC-001 | One-time token flow | Browser tooling captures secret | Generic instrumentation/evidence excludes plaintext | Security |
| UI-SEC-012 | Quality/security | NFR-LIC-001 | Locked dependency graph | Risk unknown | License/vulnerability/telemetry/install-script review passes | Dependency reviewer |
| UI-PERF-001 | T4/perf | NFR-PERF-001 | Real current workload | Budget undefined | Navigation/current panels meet approved measured budget | Local/live |
| UI-PERF-002 | T4/perf | NFR-PERF-001 | Largest real history page | Rendering blocks | Bounded page/chart/table meets budget | Owner/live |
| UI-PERF-003 | Build/perf | NFR-PERF-001 | Production bundle | Bundle unbounded | Route chunks and dependencies meet approved size budget | Local |
| UI-PERF-004 | T4/perf | NFR-PERF-001 | 100 real registered accounts | Scale unverified | Filters/pagination remain usable; otherwise Blocked | No synthetic accounts |
| UI-PERF-005 | T4/perf | NFR-PERF-001 | 200 real processes | Tree scale unverified | Tree/detail remain usable; otherwise Blocked | No synthetic processes |
| UI-PERF-006 | T4/perf | NFR-RES-001 | Real rapid poll/update within policy | Render thrashes | Updates preserve focus and approved CPU/memory budget | Owner/live |
| UI-PERF-007 | T4/perf | NFR-RES-001 | Hidden/visible real document | Excess polling | Hidden polling obeys policy; revalidation bounded | Local |
| UI-PERF-008 | T4/perf/a11y | FR-UI-001 | Real dense data at zoom | Virtualization harms AT | Chosen bounded rendering retains semantic access | Owner/live |
| UI-SAFE-001 | Quality/T4 | FR-SAFE-001 | Built routes/controls | Missing allowed workflows | Only approved refresh/metadata/config/alert/export actions exposed | Review |
| UI-SAFE-002 | T4 | FR-SAFE-001 | Real export/config flows | Side effect hidden | Confirmations and job status accurately describe side effect | Local |
| UI-SAFE-003 | T4 | FR-SAFE-001 | Real reauth eligibility | Ineligible action shown | Reauth only on managed eligible profile | Owner/live |
| UI-SAFE-004 | T4 | FR-SAFE-001 | Real collector target | GET causes refresh | Page loads never trigger provider collection | Joint P01/M04 |
| UI-SAFE-005 | Quality/T4 | FR-SAFE-002 | Built UI/client | Kill/restart control exists | No agent process-control operation/control | Review |
| UI-SAFE-006 | Quality/T4 | FR-SAFE-002 | Built UI/client | Input injection exists | No terminal/prompt input path/control | Review |
| UI-SAFE-007 | Quality/T4 | FR-SAFE-002 | Built UI/client | Credential switching exists | No running-session credential-switch action | Review |
| UI-SAFE-008 | Quality/T4 | FR-SAFE-002 | Built UI/client | Routing recommendation exists | No agent routing/account-selection control | Review |
| UI-AUTO-001 | Automation | AC-TEST-001 | Canonical evidence tool | R/G/R not enforced | Each changed behavior has meaningful Red/Green/refactor IDs | Test steward |
| UI-AUTO-002 | Automation | AC-TEST-002 | Source/dependency scan | Prohibited framework accepted | Gate rejects mocks/fakes/fixtures/recordings/test-only path | Test steward |
| UI-AUTO-003 | Automation | AC-TEST-003 | Real built stack/browser | Narrow tests reported green | T4 command proves actual boundaries and reports environment | Test steward |
| UI-AUTO-004 | Automation | AC-TEST-006 | Missing provider/macOS/AT condition | Missing reported pass | Output separates Passed/Failed/Blocked/Not Run | Test steward |
| UI-AUTO-005 | Automation | AC-V1-007 | Evidence/bundle/log artifacts | Secret scan absent | Allowlist/secret scan passes without exposing findings | Security |
| UI-AUTO-006 | Automation | NFR-DOC-001 | Real checkout | Prose claim outruns gate | P02 handoff fails until required command registry/gates exist | Integration |
| UI-DOC-001 | Docs | NFR-DOC-001 | Real docs tree | Module docs absent | Boundaries/contracts/workflows/tests/limitations documented | Docs review |
| UI-DOC-002 | Docs | NFR-DOC-001 | Generated API references | Docs drift | User workflows link current operation concepts | Joint P01 |
| UI-DOC-003 | Docs | NFR-DOC-001 | Accessibility matrix | Keyboard/AT docs absent | Supported behavior and Blocked evidence visible | Accessibility review |
| UI-DOC-004 | Docs | NFR-DOC-001 | Command registry | Invented commands present | Only verified commands are operational; planned remain TBD | Integration |
| UI-DEP-001 | Dependency | NFR-LIC-001 | Locked graph | License unreviewed | Direct/transitive licenses and notices approved | License reviewer |
| UI-DEP-002 | Dependency | NFR-SEC-001 | Locked graph/scanner | Vulnerability unknown | No unaccepted vulnerability/install-script/telemetry risk | Security |
| UI-DEP-003 | Dependency | NFR-PLAT-001 | Real Linux and macOS when available | Platform support guessed | Linux passes; macOS is Passed or Blocked truthfully | Platform owners |
| UI-DEP-004 | Dependency | NFR-LIC-001 | Build/SBOM | Inventory incomplete | SBOM/notices include shipped frontend graph/assets | Release steward |
| UI-PLAT-001 | T4/T5 | NFR-PLAT-001 | Real Linux browser | Linux behavior unknown | Full P02 critical matrix passes on target Linux | Local |
| UI-PLAT-002 | T4/T5 | NFR-PLAT-001 | Real macOS browser | macOS assumed | Portable matrix passes or remains Blocked | macOS owner |
| UI-PLAT-003 | Quality | NFR-PLAT-001 | Source/build | OS-specific logic leaks | No OS/provider API import in P02 | Local |
| UI-LIVE-001 | T4/T6 | AC-LIVE-005 | Real Claude account/data | Values not reconciled | UI value/source/time/unit matches authoritative provider evidence | Owner countersign |
| UI-LIVE-002 | T4/T6 | AC-LIVE-005 | Real Codex account/data | Same | Same reconciliation for Codex | Owner countersign |
| UI-LIVE-003 | T4/T6 | AC-LIVE-005 | Real Ollama/API data as applicable | Same | Same reconciliation for Ollama supported metrics | Owner countersign |
| UI-LIVE-004 | T4/T6 | AC-LIVE-006 | Real reauth per provider | UI continuity unverified | Reauth workflow retains account history and protects default profile | Owner present |
| UI-LIVE-005 | T4/T6 | AC-LIVE-007 | Naturally available exhausted/auth/unavailable/recovery | UI states unverified | Each observed state displays truthfully; absent remain Blocked | Owner/live |
| UI-LIVE-006 | T4/T6 | AC-UI-002 | All intended enrolled accounts | Coverage incomplete | Global/org/provider/account views include real intended inventory | Owner countersign |

### 9.6 Evidence, visual, accessibility, and performance rules

- Browser screenshots are supporting evidence, not behavioral assertions. Screenshots containing real account/session/usage information remain owner-local, sanitized, access-controlled, and uncommitted.
- Stable structural visual checks can use the real login page and real fresh-database empty state. They cannot insert sample telemetry for pixel baselines.
- Automated accessibility scanners are supplemental. Keyboard, focus, zoom/reflow, forced-color, reduced-motion, chart/table, and screen-reader workflows require actual browser/manual evidence.
- Performance budgets are selected after foundation baseline measurement and recorded in plan amendment before implementation approval. Tests measure production builds, not development mode.
- The 100-account/200-process scale scenarios remain Blocked unless that real state exists through production workflows. Code review/pagination design cannot be mislabeled a performance pass.
- Dynamic values are asserted by identity, units, invariants, provenance, range, freshness, and provider reconciliation, never hardcoded amounts/reset times.

### 9.7 Mutation and coverage quality

Meaningful branch coverage is required for auth-expiry decisions, state algebra, problem mapping, action eligibility, safe route handling, cache invalidation, formatters, and accessibility interaction policies. Mutation testing may use constructed inputs only for pure no-I/O policies. Surviving mutations that could convert unknown/stale/unsupported to available, replay a mutation, leak a token, bypass route guards, or remove non-color cues block P02 completion.

Line coverage is diagnostic. It cannot replace real browser workflows or live reconciliation.

## 10. Implementation increments

Each increment starts only after its exact generated operations and dependencies are synchronized. Every row follows Red → Green → Refactor and produces sanitized evidence.

| Increment | Exclusive files/area | Failing tests first | Minimum production behavior | Refactor/docs | Exit evidence |
|---|---|---|---|---|---|
| UI-I00 boundary automation | P02 import/test rule allocation; no features | UI-CONTRACT-001/002/006, UI-AUTO-001..004 | Generated wrapper seam, import restrictions, real T4 harness selector | Boundary/command docs | Client/build/browser gate executes; statuses truthful |
| UI-I01 app shell | `app/**`, shared tokens/primitives | UI-NAV-001..005, UI-RESP-001, UI-A11Y-001/002 | Routes, shell, focus, error boundaries, empty safe composition | Shell/accessibility docs | Built browser on real API shell |
| UI-I02 dashboard auth | `features/auth/**`, auth shared adapter | UI-AUTH-001..010, UI-SEC-001/003/004/006 | Login/bootstrap/logout/expiry/password workflow as synchronized | Security/user auth docs | Real session/CSRF/browser evidence |
| UI-I03 token settings | `features/settings/security/**` | UI-TOKEN-001..010, UI-SEC-011 | Token summary/create/rotate/revoke/one-time modal | Token/Swagger guidance | Real persistence and bearer denial/use evidence |
| UI-I04 registry/providers | organizations/accounts/providers features | UI-ORG-001..008, UI-ACC-001..012, UI-PAUTH-001..008 | Registry CRUD, discovery/identity/profile/auth workflows | Registry/auth docs | Real account/provider browser evidence; blocked states listed |
| UI-I05 command/capacity | command/accounts capacity panels | UI-CMD-001..010, UI-CAP-001..010, UI-BUD-001..008 | Global composition, native windows, budget, explanation | Visual/data-truth docs | Real provider reconciliation matrix |
| UI-I06 history | `features/history/**` | UI-HIST-001..009, UI-A11Y-006 | Bounded range/chart/exact table/timezone/export entry | Chart accessibility docs | Real collection-history-browser evidence |
| UI-I07 runtime | `features/sessions/**` | UI-RUN-001..012, UI-SEC-008 | Tree/detail/aggregate/state/correlation confirmation | Runtime privacy docs | Real Linux/browser evidence |
| UI-I08 alerts | `features/alerts/**` | UI-ALERT-001..012 | Notification counts, alert/rule/history/read/ack/snooze | Alert workflow docs | Real DB/API/browser lifecycle evidence |
| UI-I09 collectors | `features/collectors/**` | UI-COL-001..010 | Health/runs/manual refresh/progress/backoff | Collector docs | Real run and browser-closure evidence |
| UI-I10 operations | `features/diagnostics/**` and operations settings | UI-OPS-001..012, UI-SEC-009 | Health/version/backups/exports/diagnostics; no restore action | Operations user docs | Real jobs/download/status evidence |
| UI-I11 responsive/a11y | shared styles/components plus feature fixes allocated centrally | UI-RESP-001..008, UI-A11Y-001..010, UI-VIS-001..005 | Final breakpoint, keyboard, chart/table, contrast, motion behavior | Accessibility matrix | Real viewport/AT evidence |
| UI-I12 hardening/release | P02 tests/docs; shared build changes by steward | UI-DATA/CONTRACT/SEC/PERF/SAFE/AUTO/DEP/PLAT/LIVE families | Bundle/security/perf/failure compatibility hardening | Complete handoff/known limits | Canonical commands and live matrix |

### 10.1 Parallel-development safety

After UI-I00 through UI-I03 stabilize `app/**`, `shared/**`, auth transport, generated-client imports, and design tokens, feature increments UI-I04 through UI-I10 may proceed in parallel only when:

- each agent owns exactly one feature directory and its matching test subdirectory;
- no two agents edit `app`, `shared`, package/lock/config/generated files, navigation, design tokens, or shared evidence indexes;
- the shell/shared steward makes shared changes from explicit proposals after consumer review;
- producer OpenAPI slices are already synchronized and client regeneration has one steward;
- features communicate through route parameters and API/query state, never direct feature imports;
- query keys/invalidation additions receive shared steward allocation;
- a contract gap stops the feature rather than creating a local DTO or HTTP call.

UI-I11 and UI-I12 are integration increments and are not parallel merge dumping grounds. Findings return to the owning feature agent or are fixed under an explicit path reassignment.

### 10.2 Red/Green/refactor evidence per increment

Each increment handoff records:

- scenario and requirement/AC IDs;
- exact verified command-registry entry, runtime/browser/API/client/build/database versions, timestamp, and environment;
- expected meaningful Red and sanitized failure summary;
- minimal Green change reference and result;
- post-refactor full relevant gate result;
- real boundary exercised and whether provider/AT/platform evidence is Passed, Failed, Blocked, or Not Run;
- browser/storage/network/console/secret scan result;
- OpenAPI/client/build/bundle/dependency/license diff;
- screenshots only under the sanitization policy;
- remaining consumer/owner action.

## 11. Documentation outputs

Approved implementation produces and maintains:

- `docs/modules/react-dashboard.md`: purpose, boundaries, routes/features, query/error/state model, generated-client rule, security/privacy, operations, test matrix, known limitations;
- `docs/user/dashboard.md`: login, navigation, organizations/accounts, quota/budget/source/freshness, sessions, alerts, collectors, diagnostics, settings;
- `docs/user/accessibility.md`: keyboard map, focus behavior, chart/table alternatives, zoom/reflow, reduced motion, screen-reader expectations;
- API-token and Swagger workflow guidance with no token examples;
- provider re-authentication guidance linking only verified official workflows and emphasizing no credential entry;
- frontend development guide using only verified command-registry commands;
- dependency admission records, SBOM, notices, and frontend asset provenance;
- P02 Red/Green/refactor and real-browser/live evidence summaries;
- supported browser/platform/accessibility matrix with all Blocked/Not Run entries;
- responsive viewport and visual review matrix;
- operations/upgrade/rollback/cache troubleshooting after real commands exist;
- traceability updates for every scenario above and release known limitations.

Documentation contains no sample telemetry screenshot, real identity, secret, provider payload, prompt/response/source content, or invented operational command.

## 12. Dependency and license impact

No package is approved or installable from this draft. Exact versions and transitives are selected at implementation readiness, rechecked against canonical upstream data, locked, scanned, and owner-approved.

| Candidate | Purpose | Preliminary license from policy | Necessity/alternative | Admission status |
|---|---|---|---|---|
| React | Required UI framework | MIT | Architecture decision; no substitute planned | Candidate/Pending |
| Vite | Production build/dev tooling | MIT with bundled notices | Foundation-selected build tool | Candidate/Pending |
| TypeScript | Strict frontend types | Apache-2.0 upstream verification required at pinning | Required by architecture/generated client | Candidate/Pending |
| TanStack Query | Server-state lifecycle/cache/cancellation | MIT | Compare against small in-house layer; avoid reimplementing complex cache semantics | Candidate/Pending |
| React Router or selected router | Accessible SPA routing/deep links | License/upstream review required | Compare small route manifest/history implementation | Candidate/Pending; not shortlisted yet |
| Radix Primitives, selectively | Security/accessibility-sensitive dialogs/menus/tabs | MIT | Use only components whose behavior beats native primitives | Candidate/Pending |
| Apache ECharts | Time-series/composition visualization | Apache-2.0 | Admit only after accessible table pairing and bundle analysis; native SVG alternative assessed | Candidate/Pending |
| Playwright | Real supported browser automation | Apache-2.0 | Required T4 boundary; browser binaries/supply chain reviewed | Candidate/Pending |
| Accessibility rule engine such as axe-core | Supplemental automated WCAG findings | License/upstream review required | Manual-only misses repeatable rules; not proof by itself | Candidate/Pending |

Default styling proposal is app-owned CSS custom properties, CSS Grid/Flexbox, and scoped styles. Tailwind is not required by this plan; adding it needs a demonstrated need and separate admission. No icon package is assumed; a minimal reviewed app-owned semantic SVG set is preferred unless an admitted library materially reduces accessibility/security risk.

Admission record for every package includes canonical identity/license, exact version, transitives/licenses, maintenance/security policy, provenance, release activity, native/binary/install scripts, browser/network/telemetry behavior, bundle/runtime size, supported platforms, pin/update/remove strategy, alternatives, SBOM/notices effect, reviewer, and date. Copyleft/custom/unclear licensing requires explicit owner approval.

## 13. Risks, unresolved decisions, and stop conditions

### 13.1 Risks

| Risk/question | Likelihood/impact | Mitigation/evidence | Owner | Trigger | Status |
|---|---|---|---|---|---|
| R-017 dense UI becomes inaccessible | Medium/Major | Semantic hierarchy, real viewport/zoom/keyboard/AT matrix, no density through tiny targets | P02/accessibility | Overflow, hidden focus/status | Open |
| R-007 stale/partial looks current | Medium/Critical | Preserve producer field-state/freshness/completeness; state algebra and mutations | P02/M05/P01 | Missing timestamp/source or cache relabel | Open |
| R-008 false aggregate/forecast accuracy | Medium/Major | Server projections only; inputs/uncertainty; no browser arithmetic | M05/P01/P02 | Combined incompatible pools | Open |
| R-005 content/secret leak in DOM/evidence | Medium/Critical | Schema/render allowlists, storage/network/bundle/evidence scans | Security/P02 | Prohibited field/secret finding | Open |
| API/client contracts arrive inconsistently | High/Major | Per-slice synchronization and generated-client gate; no handwritten fallback | P01/integration | Missing operation/schema/state | Open |
| Dynamic real data makes visual tests flaky/leaky | High/Major | Structural empty/login baselines; owner-local populated review; behavioral assertions | P02/test | Golden contains telemetry | Open |
| No safe way to produce failure states | High/Major | Natural real states or Blocked; no simulation/destructive manufacture | Test/owner | Requested fake/forced state | Accepted policy |
| Browser cache/retry causes duplicate mutation | Medium/Critical | No mutation auto-retry; idempotency contract; explicit conflict UI | P01/P02 | Duplicate side effect | Open |
| Third-party component harms accessibility/security/license | Medium/Critical | Dependency admission, selective import, real AT test, removal path | Dependency/security | Audit finding | Open |
| Real 100/200 scale state unavailable | High/Major | Server pagination/tree design; mark scale tests Blocked until real state | Integration/owner | Release scale claim | Open |
| Frontend/API bundle version mismatch after rollback | Medium/Major | Compatibility metadata, atomic deploy, explicit mismatch UI/rollback matrix | FND/DEP/P01/P02 | Decode/version error | Open |
| One-time token copied into evidence/tooling | Medium/Critical | Exclude modal from screenshots/tracing; disable payload logs; explicit test | Security/P02 | Token pattern finding | Open |

### 13.2 Approval-blocking synchronization decisions

1. P01 full resource/operation/permission/problem inventory and producer ownership for every P02 view/workflow.
2. Exact `CTR-UI-001` generator, output, runtime validation, streaming/download, compile, and drift behavior.
3. Session bootstrap, cookie/CSRF rotation, expiry, logout, password-change, and concurrent 401 behavior.
4. API-token one-time response, clipboard/evidence safeguards, rotation/replay and Swagger guidance.
5. Global/org/provider aggregate shapes and completeness/provenance so P02 performs no business aggregation.
6. Common API field-state/provenance/explanation/action-eligibility vocabulary.
7. REST polling cadence and whether SSE is explicitly deferred until post-V1 hardening.
8. Browser/version support and real screen-reader/contrast automation matrix.
9. Exact responsive breakpoint acceptance and approved performance/bundle budgets after measurement.
10. Dependency candidates, direct/transitive licenses, exact pins, browser binaries, SBOM/notices, and no-telemetry proof.
11. Static UI/API hosting, deep-link fallback, cache-control, CSP, source-map, and atomic deploy/rollback semantics.
12. Safe authenticated download transport and filename/content-disposition handling.
13. Whether UI may persist any non-sensitive preference; default proposal is no browser persistence.
14. Shared-file ownership and feature implementation wave allocation.
15. Canonical command entry points for build, generated drift, quality, T4, accessibility, security, dependency, docs, and release gates.
16. Exact sanitization/storage policy for real populated browser evidence.
17. Missing natural/live test states that release criteria require Passed versus capability-honest Blocked.

### 13.3 Stop and escalation conditions

An implementation agent stops and informs the integration steward when:

- a required generated operation/schema/state/permission/error is missing or ambiguous;
- a feature would need direct fetch, backend/internal contract import, database/provider/filesystem/process access, or handwritten DTO;
- a proposed component would compute backend truth or hide unknown/partial/stale/unsupported meaning;
- real test state is unavailable and someone proposes a mock, fixture, seeded telemetry, replay, test-only endpoint, database insertion, or destructive provider action;
- any prompt/response/tool/source/environment/secret/profile locator/raw provider field appears in API, DOM, console, storage, screenshot, trace, or artifact;
- a default provider profile, running agent, provider account, or external service would be mutated outside the approved workflow;
- a dependency/license/security/install-script/telemetry/transitive issue lacks approval;
- generated client/OpenAPI compatibility changes, especially units/nullability/status/provenance;
- another agent owns the needed shared file or concurrent edits overlap;
- a browser action could restore, delete, kill, restart, pause, inject, switch, or route outside V1;
- evidence cannot distinguish Passed, Failed, Blocked, and Not Run;
- an operational command is requested before it exists in the verified command registry.

## 14. Delivery and rollback

### 14.1 Delivery order

1. Implement and verify foundation frontend build/generated-client/T4 automation.
2. Synchronize and implement P01/M01 auth transport; deliver shell/auth/token increments.
3. Generate the client from each synchronized API feature slice.
4. Deliver registry/provider, command/capacity/history/runtime, alert/collector, and operations slices in the isolated order from section 10.
5. Run integration accessibility/responsive/security/performance/live matrices.
6. Build versioned immutable frontend artifact with SBOM/notices/build metadata.
7. Deploy atomically with a compatible API/client version through PLAN-DEP automation.

No feature flag may expose a route whose required API contract is absent. A route may be omitted until its feature slice is integrated; it must not render placeholder telemetry.

### 14.2 Compatibility window

Within `/api/v1`, additive optional fields are tolerated only when generated types and unknown-state rules permit them. Removing/renaming fields, changing units/nullability/status meanings, or changing auth/CSRF semantics requires an API major or approved compatibility bridge.

The deployed UI advertises frontend build, OpenAPI schema identity, and generated-client identity. P01/DEP must define an accepted compatibility range. Outside that range, P02 shows a safe upgrade/maintenance message and performs no writes.

### 14.3 Rollback

P02 has no data migration to reverse. Rollback means atomically restoring the prior verified static bundle only when it remains compatible with the running `/api/v1`. If the API already made a breaking change, restore the compatible release set through deployment rollback; never hand-patch generated output or serve mixed files.

Rollback checks:

- preserve server/database state; UI rollback never mutates it;
- clear static-asset caches and verify deep links/login;
- verify session/CSRF compatibility or require safe re-login;
- run smoke browser checks against the rolled-back bundle and real API;
- record any features temporarily unavailable and do not replace them with cached/sample values.

### 14.4 Post-deployment checks

- Static assets and deep links load on loopback with expected security headers.
- Frontend/API/OpenAPI/client/build versions are compatible and visible.
- Real login/logout/expiry behavior works; API token plaintext is not retained.
- Global empty or real populated command state is truthful.
- Critical navigation, keyboard/focus, 1920×1080, narrow reflow, and reduced motion pass.
- One real safe GET and one approved CSRF/idempotent mutation cross the generated client.
- Browser storage, console, network, bundle, and evidence scans are clean.
- Browser close does not stop collection.
- All provider/platform/accessibility scenarios retain truthful result status.

## 15. Definition of ready

- [ ] Requirements, workflow scope, non-goals, and owner-visible information hierarchy are approved.
- [ ] This exact plan version passes structural/catalog validation and the cross-plan synchronization review accounts for it.
- [ ] P01 publishes synchronized `CTR-API-001..003` operations/schemas/problems/permissions for the first increment.
- [ ] `CTR-UI-001` generator/output/wrapper/drift contract is approved.
- [ ] Foundation frontend runtime/package manager/build/test/import/command mechanisms are approved and implemented where required.
- [ ] Exact allowed paths, shared-file owners, generated-file owner, and feature-agent allocations are approved.
- [ ] Browser session/CSRF/expiry/logout and one-time API-token workflows receive M01/P01/P02/security approval.
- [ ] Common field-state/provenance/completeness/explanation/action-eligibility semantics are synchronized.
- [ ] Test scenarios have meaningful expected Red and required real environments/accounts/owner checkpoints.
- [ ] Candidate dependencies pass license, security, maintenance, telemetry, transitive, lockfile, SBOM, notices, and owner review.
- [ ] Browser/platform/accessibility support matrix and responsive/performance budgets are approved from real baseline measurements.
- [ ] Evidence sanitization and local retention rules are approved.
- [ ] Canonical automation entry points needed for the increment exist, are tested at their real boundary, and are registered.
- [ ] No unresolved decision allows a materially different security, contract, data, accessibility, or workflow implementation.

P02 implementation may begin increment-by-increment only when the exact slice's dependencies are ready. Approval of an auth shell does not authorize capacity, provider, runtime, alert, diagnostics, or live-data work.

## 16. Approval record

Current decision: **Draft only. No implementation, dependency installation, client generation, browser execution, live-provider access, or external mutation is authorized by this artifact.**

Required approvals:

| Reviewer | Decision | Conditions/evidence | Date |
|---|---|---|---|
| Owner/product | Pending | Mission-control hierarchy, workflows, responsive priorities | Pending |
| Integration steward | Pending | Catalog, cross-plan ownership, parallel paths, completion gate | Pending |
| P01/API owner | Pending | OpenAPI/generated operations, auth/errors/pagination/jobs/download | Pending |
| M01/security | Pending | Session/CSRF/token/expiry/password/re-auth safety | Pending |
| M02/M04/M05/M06/M07/M08 producers | Pending | Resource projections, states, actions, provenance, failure semantics | Pending |
| Accessibility reviewer | Pending | WCAG 2.2 AA interaction and real test matrix | Pending |
| Test steward | Pending | Real T4/T5/T6 evidence design and no-doubles enforcement | Pending |
| Dependency/license reviewer | Pending | Exact graph, licenses, supply chain, SBOM/notices | Pending |
| Deployment/operations | Pending | Static serving, versions, cache, atomic deploy/rollback | Pending |

Approval must record the exact plan version, synchronized contract versions, admitted dependency decisions, allowed implementation paths, first authorized increment, and unresolved Blocked/Not Run live scenarios. A later implementation handoff must use the repository templates and name every changed file, requirement/AC, contract, Red/Green/refactor result, real boundary, security/privacy/license/documentation impact, and next integration step.
