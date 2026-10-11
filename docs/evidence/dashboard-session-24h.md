# Dashboard 24-hour session policy evidence

- Date: 2026-10-09
- Status: bounded implementation evidence; canonical integration verification
  remains recorded by its executable gate
- Approved change: [dashboard 24-hour session policy](../plans/integration/dashboard-session-24h-change.md)
- Owning module: M01 identity and access
- Requirements: `FR-IAM-001`, `FR-IAM-003`, `NFR-SEC-001`
- Acceptance evidence: `AC-UI-001`, `AC-TEST-002`, `AC-TEST-003`,
  `AC-TEST-006`
- Contracts: compatible policy amendment to `CTR-IAM-003/005` V1

## Outcome

Newly issued dashboard browser sessions use equal idle and absolute deadlines
exactly 86,400 seconds after successful login. Equality remains expired, and
an activity touch cannot extend either deadline past the original absolute
deadline. The change is a fixed code policy: the documentary configuration
names are not runtime `.env` controls.

Existing persisted session rows retain their original absolute deadline and
idle window. Normal activity may continue sliding an old idle deadline by its
original window, but deployment cannot replace that window with 24 hours. No
migration or database rewrite occurs. After deployment, the owner signs in once
to receive a session under the new policy.

## Requirement and boundary mapping

| Evidence | Requirement or acceptance ID | Boundary | Result |
|---|---|---|---|
| Equal 86,400-second issue deadlines, equality expiry, absolute cap | `FR-IAM-003`, `NFR-SEC-001`, `AC-TEST-002` | M01 pure policy | Passed in the focused Green below |
| Preserve each persisted session's issued idle window on touch | `FR-IAM-003`, `NFR-SEC-001`, `AC-TEST-002` | M01 pure policy and real pre-upgrade service session | Passed in pure policy and live post-restart checks |
| Real migrated SQLite and HTTP login, returned deadlines, cookie lifetime | `FR-IAM-001/003`, `AC-TEST-003` | M01/P01 real SQLite and HTTP | Passed in the focused Green below |
| Production-built Chrome authentication and retained session protections | `AC-UI-001`, `AC-TEST-006` | P02 built browser | Owned by the applicable canonical local gate |
| Literal elapsed expiry after at least 86,400 seconds | `FR-IAM-003`, `AC-UI-001` | Real service and browser wall clock | **Not Run**; it is an explicit long-run scenario and is not credited by issuance tests |

## Red

Before the production policy constants changed, the approved assertions were
run at `2026-10-09T16:14Z` with:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest backend/tests/identity_access/test_session_policy.py backend/tests/integration/api/test_iam_http.py::test_login_uses_real_migrated_iam_and_sets_two_cookies -q --tb=short
```

The command exited 1 with `2 failed, 6 passed in 3.02s` for the expected
reasons:

- `test_idle_deadline_is_capped_by_absolute_and_touch_is_coalesced` expected
  `issued + 86400` but received the prior 00:30 idle deadline;
- `test_login_uses_real_migrated_iam_and_sets_two_cookies` required cookie
  `Max-Age >= 86390` but received `43199` from the prior 43,200-second absolute
  policy.

These failures reached the old production behavior. They were not import,
fixture, environment, or test-setup failures.

## Green

After setting both M01 production policy constants to 86,400 seconds, the same
exact command exited 0 at `2026-10-09T16:17Z` with:

```text
8 passed in 1.99s
```

The focused Green exercises deterministic boundary behavior and the real
migrated file-SQLite/HTTP login path. Wider real-touch, generated-contract,
built-browser, quality, documentation, and planning coverage remains the
responsibility of the applicable canonical local gate; this record does not
convert an unexecuted lane into a pass.

The canonical `AUTO-TEST` run completed at `2026-10-09T16:59Z` with status
**Passed**. Its backend lane reported `1359 passed, 37 skipped` in 651.22
seconds; the skipped cases are explicit later-milestone owner/live conditions
outside this M1/M2 gate and are not credited here. The same gate passed the
production Chrome authentication and reload scenario, real elapsed 61-second
touch/logout scenario, same-origin security boundary, hostile-resource denial,
generated contract check, and production frontend build. Its separate M0-G1
approval check remained Failed outside the M2 acceptance gate and is not
reclassified by this result.

### Existing-session compatibility Red/Green

Independent review found that the first implementation could apply the new
idle duration when touching a pre-upgrade row. Test
`test_existing_absolute_deadline_requires_its_persisted_idle_window` was added
to fail closed against that exact call shape. At `2026-10-09T16:43Z`:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest backend/tests/identity_access/test_session_policy.py::test_existing_absolute_deadline_requires_its_persisted_idle_window -q --tb=short
```

exited 1 with `1 failed in 0.06s`: the policy did not raise
`session_idle_window_incomplete` when an existing absolute deadline was supplied
without the row's persisted activity and idle deadline. The SQLite touch path
was then changed to supply both persisted values, and `session_deadlines`
rejects the incomplete call. At `2026-10-09T16:44Z`:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest backend/tests/identity_access/test_session_policy.py -q --tb=short
```

exited 0 with `9 passed in 0.04s`. The same suite proves that a persisted
1,800-second window remains 1,800 seconds and that a newly issued 86,400-second
window remains capped by its original absolute deadline. A real active
pre-upgrade service session was observed before deployment with a 1,800-second
idle window and 43,200-second absolute lifetime; its post-restart observation is
recorded under live verification below.

## Refactor

The production change sets the two existing M01 policy constants and makes the
SQLite touch path derive its sliding window from the session's persisted
activity and idle deadline. This prevents a pre-upgrade 1,800-second window
from silently becoming 86,400 seconds. Session and CSRF credential generation,
digest-only persistence, expiry comparison, activity coalescing, revocation,
cookie attributes, Host/Origin admission, API shapes, and error mappings retain
their existing paths. Tests, automation descriptions, and maintained
documentation now use the current policy. Historical M2 evidence remains
unchanged except for an explicit supersession note.

Refactor verification used the canonical commands rather than narrower local
aliases:

- `AUTO-PLAN-CHECK`: Passed (synchronized).
- `AUTO-DOCS-CHECK`: Passed for 307 Markdown files.
- `AUTO-QUALITY`: Passed static, type, boundary, generated-artifact, locked
  input, and production-build checks.
- `AUTO-BUILD`: Passed generated contract and production frontend build.
- `AUTO-TEST`: Passed as recorded above.

The literal 86,400-second wall-clock expiry is still **Not Run** and appears as
an explicit Not Run evidence row in `AUTO-TEST` with `FR-IAM-003`,
`AC-UI-001`, and `AC-TEST-006`; no Passed row claims that elapsed boundary.

## Live deployment verification

Before restart, the authenticated real dashboard session returned status 200
with a persisted 1,800-second idle window, 43,200-second absolute lifetime,
active state, and record version 2. This is the real pre-upgrade row selected
for the compatibility check. That shared-browser row reached its existing idle
deadline before the post-restart request and was correctly recorded expired; it
was not reclassified as a compatibility pass.

After restart on revision `cdc42eb177228c21e84ae04d6c4c584c99c73991`, a
different real active pre-upgrade session was touched by the running service at
`2026-10-09T17:04:20Z`. Its last activity moved to that instant, its idle
deadline moved to `2026-10-09T17:34:20Z`, and its original absolute deadline
remained `2026-10-10T01:22:48Z`. The exact 1,800-second window proves the
deployed touch path preserved that row's prior policy rather than applying the
new 86,400-second duration.

On `2026-10-11`, the owner completed one fresh dashboard login in the shared
production Chrome profile. A same-origin `GET /api/v1/session` returned status
200, active state, record version 1, an 86,400-second idle window, and an
86,400-second issued-to-absolute lifetime. At observation, 86,384 seconds
remained on the absolute deadline. Chrome reported 86,383 seconds remaining on
both cookies; the session cookie remained host-only, `HttpOnly`, and
`SameSite=Strict`. Loopback and LAN listeners both returned HTTP 200. No cookie
or credential value was read, printed, or stored.

## Impact assessment

- **Security:** a stolen browser credential can remain useful for longer. The
  absolute deadline is capped at the same 24 hours, and server-side revocation,
  password-change rotation, strict Host/Origin admission, CSRF binding,
  host-only `HttpOnly` session cookie, `SameSite=Strict`, and the Web Storage
  prohibition remain in force.
- **Privacy:** no new field, identity, provider datum, prompt, response, source
  content, credential value, or telemetry is read, stored, logged, or exposed.
- **Migration and compatibility:** no schema, route, DTO, error, OpenAPI,
  generated-client, cookie-name, or cookie-attribute change. Existing rows are
  deliberately unchanged. This is a compatible `CTR-IAM-003/005` V1 policy
  amendment.
- **Dependencies and licenses:** no package or transitive dependency changed;
  no admission, SBOM, or notices update is required.
- **Operations:** restart AgentMonitor, then sign in once. Restart alone does
  not extend an existing session. Rollback restores the prior constants in a
  new revision; already-issued 24-hour rows remain bounded and revocable.

## Changed artifacts

- Production policy:
  `backend/src/agentmonitor/modules/identity_access/domain/policy.py` and
  `backend/src/agentmonitor/adapters/persistence/identity_access/sqlite/sessions.py`.
- Policy and real-boundary tests:
  `backend/tests/identity_access/test_session_policy.py`,
  `backend/tests/integration/identity_access/test_session_touch.py`,
  `backend/tests/integration/api/test_iam_http.py`, and the opt-in
  `backend/tests/integration/api/session_expiry_live.py`.
- Browser verification:
  `frontend/tests/browser/p02/auth.mjs`,
  `frontend/tests/browser/p02/run_browser.py`, and the opt-in
  `frontend/tests/browser/p02/idle_expiry.mjs`.
- Automation and documentation: the `AUTO-TEST`/`AUTO-M3-TEST` descriptions,
  configuration baseline, M01 plan/operator guide, documentation indexes,
  approved change plan, this record, and the historical M2 supersession note.

## Remaining truthful limitation

The literal 24-hour wall-clock service/browser expiry scenario is **Not Run**.
The prior real 30-minute elapsed result remains valid only for the historical
M2 policy. It does not prove the new 24-hour elapsed boundary.
