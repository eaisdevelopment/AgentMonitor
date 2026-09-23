# M3 ST-OBS-003 P02 browser increment evidence

- Evidence ID: `M3-ST-OBS-003-P02`
- Module/plan/increment: `P02` / M3 Task 6 authenticated observation UI
- Requirements/acceptance IDs: `FR-UI-001..007`, `FR-ACC-001..006`,
  `FR-QUOTA-001..006`, `FR-DISC-001..008`, `FR-STATE-001/002`,
  `FR-COL-001..008`, `AC-UI-002/003/006`, `AC-PROC-001..005`,
  `AC-TEST-001..003/006`
- Contract versions: consumes `CTR-API-001..003 v1`, `CTR-UI-001 v1` through
  generated client; generated OpenAPI artifact SHA-256
  `74e48f5066dc76e7d4b7946a4411b00ccf94a5504db7dbca1ac96016ad2acfb7`
- Commit/worktree reference: baseline commit
  `b23015ba0e8b6ca475de558ec37cda51c24aec19`; uncommitted M3 P02 paths named
  in the root integration handoff
- Recorder/date: P02 implementation agent, 2026-09-23 Europe/London

## Test inventory and status

| Test/scenario | Layer | Real dependencies | Status | Notes |
|---|---|---|---|---|
| `monitoring_dashboard` | T2/T3/T4 | real migrated file SQLite, production IAM/bootstrap, Uvicorn loopback, Vite production bundle, installed Chrome | Passed | Fresh database/API empty state, five required GETs observed at 200 without interception, direct routes, six viewport widths, storage/network/console checks |
| Populated account detail: filtered sessions beside quota | T2/T3/T4/T5/T6 | same real stack plus real registered account/capacity/runtime observations | Blocked | Isolated database truthfully has no account; conditional real-browser path exists but did not execute |
| P02 `quick` | T2/T3/T4 | same real stack, ten isolated browser scenarios | Passed | Auth, return route, revocation, password, tokens, clipboard denial, prior responsive checks, M3 monitoring view |
| Populated Claude account/quota/session vertical | T5/T6/T4 | exact owner account, real provider observations, supported account correlation | Blocked | Required live records are unavailable; no substitute data used |
| macOS browser | T4/platform | real macOS host | Not Run | Linux-first environment only |

## Red evidence

At approximately `2026-09-23T00:59+01:00`, after adding the real browser
scenario and before production UI implementation:

```text
COMMAND: backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py monitoring_dashboard
RESULT: exit 1
P02 BROWSER: FAILED — monitoring_dashboard: real_p02_browser_failed:
P02 MONITORING DASHBOARD: FAILED — accounts_navigation:
locator.click: Timeout 30000ms exceeded; waiting for button Accounts
```

This was the expected behavioral Red: the real authenticated provisional
dashboard had no Accounts route/control. Production build, database,
migrations, server, login, and browser had already succeeded.

The review correction added passive same-origin request/response assertions.
Because the generated-client calls already existed, an honest original
Red-first state was no longer available. Test sensitivity was therefore
verified with a controlled production mutation, not misreported as historical
Red. At `2026-09-23T01:41:44+01:00`, the runtime panel load call was removed,
the exact production bundle was rebuilt, and the real browser failed:

```text
P02 MONITORING DASHBOARD: FAILED — command_responsive:
observation_get_missing_/api/v1/processes?limit=200
```

The mutation was reverted before Green. This proves a hardcoded empty runtime
panel or removed generated-client call is caught. No HTTP route, response,
database, or provider telemetry was mocked, intercepted, seeded, or replaced.

## Green and refactor evidence

The minimum UI integrated all nine generated read operations behind the shared
API wrapper and exposed truthful observation routes. The same test then found a
real 390-pixel viewport defect (`document_horizontal_overflow_419/390`), which
was corrected by bounding the application grid track. It subsequently passed:

```text
P02 MONITORING DASHBOARD: PASSED — real empty database/API/browser
P02 BROWSER: PASSED — monitoring_dashboard
```

Post-refactor commands and results at `2026-09-23T01:22:05+01:00`:

```text
npm --prefix frontend run typecheck
# exit 0

npm --prefix frontend run build
# exit 0; Vite production build, 33 modules transformed

backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py quick
# exit 0; ten isolated production-browser scenarios passed
```

The quick browser run includes six existing authentication/token viewports and
the M3 command dashboard scenario itself verifies 1920×1080, 1440×900,
1280×720, 1024×768, 768×1024, and 390×844.

After final producer-enum/client regeneration and the review correction that
labels page lengths as records shown while disclosing `has_more`, the exact
final client was reverified at `2026-09-23T01:26:30+01:00`: typecheck, build,
the targeted production monitoring browser, and documentation gate all exited
`0`.

The account filter, provenance/detail, and passive HTTP-proof correction used
final client SHA `74e48f50…`. At `2026-09-23T01:45:03+01:00`, production build,
`monitoring_dashboard`, and `auth` passed. The browser explicitly reported the
populated account-detail lane `BLOCKED — no real registered account in the
isolated database`; it was not counted as Passed.

The frozen correction batch was rerun at `2026-09-23T01:46:32+01:00`:
typecheck, production build, all ten `quick` real-browser scenarios, and the
documentation gate passed. The browser result retained the populated account
detail as Blocked.

## Integrity, privacy, and impact

- No mock, fake, stub, emulator, request interception, response-body recording, seeded
  telemetry, demo account, placeholder metric, hardcoded passing branch, or
  disabled assertion was used.
- Feature modules contain no direct `fetch`, generated-client import, backend
  import, database read, provider file read, or process inspection.
- The browser scenario observed a real empty database. It did not create
  provider/accounts/capacity/runtime telemetry.
- No dependency, backend contract, database schema, migration, provider state,
  default profile, or running agent was changed by P02.
- Browser evidence contains no password, cookie, CSRF value, bearer value,
  account identity, provider payload, prompt/response, source, environment, or
  raw process content.

## Conclusion and residual gaps

The local M3 API-to-built-browser empty/unavailable foundation is Passed. This
does not prove the required populated Claude account, quota, session,
same-account correlation, or macOS behavior; those remain Blocked/Not Run and
prevent a full M3 live acceptance claim.
