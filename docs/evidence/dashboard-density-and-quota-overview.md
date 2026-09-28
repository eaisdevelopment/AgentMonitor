# Compact dashboard and account quota overview

- Date: 2026-09-28.
- Authority: the owner's requests to compact the connected Claude notice and
  make the main dashboard prioritize account state and quota percentages.
  The [approved connection change](../plans/integration/claude-managed-account-connection-change.md)
  records both P02 increments.
- Owner: P02 presentation; root owns the existing live verification automation.
- Requirements: `FR-UI-001/002/004/005/006`; bounded `AC-UI-002/003/005`
  evidence. This is not full M4 or universal UI/accessibility acceptance.
- Contracts: consumes existing `CTR-UI-001` and `CTR-API-001` V1, registry,
  account-capacity, observed-identity, and connection V1 responses. No contract
  shape, server behavior, generated client, or migration changes.

## Owner-visible behavior

A completed Claude connection is a compact row: check icon, Claude connected,
actual monitoring on/off state, and the read-only Check status action. Its
repeated title and future quota message are removed. Setup, attention, and
recovery guidance retain their existing form. A failed status read remains
an explicit alert and may expand the row.

The main introduction is a small heading. The first substantive panel is a
full-width account table with organization, quota-reading state, every returned
quota window's remaining percentage and bounded bar, and its update time.
Calculated/rounded provenance remains visible; details explain the exact
source on the account page. Provider, collection, and session panels follow.
Account names and groups come from dynamic admin/API data. A provider-verified
name requires matching current quota collection-run lineage.

State means quota-reading freshness/availability, with explicit registry
eligibility. It never means an agent is working or that an unknown capacity
policy passed. Pending, paused, unknown, unsupported, partial, stale,
conflicted, and failed reads retain distinct wording. Missing quota has no
percentage or bar. Read refresh is every 30 seconds with at most six accounts'
two detail reads in flight; it does not invoke provider authentication or
change collection cadence. A bounded registry page reports additional
coverage instead of claiming every account was loaded.

## Red, Green, and real boundaries

| Scenario | Evidence |
|---|---|
| Connected density Red | The extended existing owner-browser verifier returned exit 3, `CLAUDE DASHBOARD: BLOCKED — connected status occupies too much space`, against the real connected account before production edits. Its actual prior panel height was 250.22 pixels. |
| Connected density Green | The same real browser/V1 check Passed: 62.80 pixels at 1920 and 1280 widths, 65.92 pixels at 390. Keyboard access, minimum action size, a successful manual status GET, and zero authentication mutations Passed. |
| Main quota overview Red | The new owner-browser verifier reached `account_quota_overview` and timed out waiting for the absent Account quota overview table, returning exit 3, `DASHBOARD OVERVIEW: BLOCKED — account_quota_overview: browser_verification_unavailable`. The running original overview contained registry cards, without per-account percentages/bars. |
| Main quota overview Green | The real populated overview check Passed for four real account rows: organization, exact per-window API percentages, bounded bars, reading-state labels, update times, first-screen desktop placement, narrow reflow, keyboard account navigation, and zero mutations. |
| Pending real SQLite/API/browser | The extended `claude_connection` scenario Passed: pending account appears Not connected with no invented quota meter, and the account link returns to its setup form. Its first increment Failed at `pending_overview_state` because the icon prevented the exact text selector; a separate label span corrected it. |
| Empty real SQLite/API/browser | `monitoring_dashboard` Passed with a genuine empty migrated database and no provider telemetry. Its first run Failed at a 392/390 responsive measurement; geometry checks now wait for two real animation frames after viewport changes. No overflow assertion was weakened. The existing account-empty wording was also aligned with the actual current registry view. |

The populated browser test compares actual current V1 data; no response is
constructed, recorded/replayed, or persisted. The empty scenario reports
account-detail acceptance Blocked because its database has no registered
account. Real owner navigation and the pending scenario supply their own
separate account-detail evidence. Native sign-in was never started by these
tests. Natural stale/unavailable/conflicted/unsupported/partial runtime cases,
actual screen-reader/200% zoom, and other platforms are Not Run for this slice.

## Canonical verification

```bash
python3 tools/automation/run.py AUTO-CLAUDE-CONNECT
backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py \
  monitoring_dashboard --no-build
python3 tools/automation/run.py AUTO-QUALITY
python3 tools/automation/run.py AUTO-DOCS-CHECK
python3 tools/planning/validate_plans.py --stage synchronized
python3 tools/automation/run.py AUTO-GIT-PREFLIGHT
git diff --check
```

The connection gate uses the four explicit real owner/account/dashboard
selectors from the runbook, omitted here. It now includes both the connected
density assertions and the actual populated overview. Missing real owner
state is non-success. The exact production frontend must be built before
`--no-build`. Final combined gate and review results are recorded below.

### Final review and checks

The bounded independent P02 review found one accessibility defect: the generic
Open account accessible label omitted its visible account name. The name is
now included, the real verifier asserts label inclusion, and the reviewer
confirmed closure. The same visible-label consistency was applied to the compact
Check status control. This is one accessibility reopening; no other blockers
or scope additions were reported.

`AUTO-QUALITY` Passed after the correction: strict frontend typecheck,
production build, unchanged compatible 44-operation OpenAPI/client, and zero
module-boundary violations. The genuine empty `monitoring_dashboard` scenario
also Passed, retaining its explicit account-detail Blocked qualification.
Documentation (258 Markdown files), synchronized planning, local Git preflight,
and `git diff --check` Passed.

The first final gate after that review returned **Blocked (exit 3)** at
`no verified managed quota identity yet`, during a normal scheduled native
read. A subsequent real V1 read verified its successful collection
(**21:15:06–21:15:10 UTC**) and restored managed identity. No provider sign-in,
service restart, cadence shortening, run rewriting, or fabricated receipt was
used; the bounded gate was repeated against the actual refreshed environment.

The final repeated `AUTO-CLAUDE-CONNECT` **Passed (exit 0)**:
API/native safeguards **5 passed in 19.66s**, real pending connection browser
Passed, actual owner-completed receipt verification Passed, real selected
managed quota **4 passed in 5.77s**, compact connected status and exact
API/browser lineage Passed, and four-account populated overview Passed.
Final connected heights remained **62.80 / 62.80 / 65.92 pixels** at
1920 / 1280 / 390 widths. The production static build is served by the
running owner service; backend restart was unnecessary. This passes the
requested density and per-account overview slice, with the limitations
and remaining M4 scope above.

## Impact, files, and follow-up

No provider/default-profile change, owner sign-in, credentials/prompts/source
read, monitored-agent action, database migration, dependency/license change,
backend implementation, or generated artifact change occurred. Screenshots
of the connection notice were private local crops without identity/quota
content; no populated provider screenshot or browser trace was retained.
Rollback restores the previous compatible static build. The service keeps
collecting at its normal interval throughout the UI change.

Changed files:

```text
docs/README.md
docs/evidence/claude-dashboard-connection.md
docs/evidence/dashboard-density-and-quota-overview.md
docs/modules/react-dashboard.md
docs/plans/integration/claude-managed-account-connection-change.md
frontend/src/app/dashboard.css
frontend/src/features/accounts/ClaudeConnectionPanel.tsx
frontend/src/features/overview/AccountQuotaOverview.tsx
frontend/src/features/overview/OverviewPage.tsx
frontend/tests/browser/p02/claude_connection.mjs
frontend/tests/browser/p02/monitoring_dashboard.mjs
tools/automation/implementations/auto_claude_connect.py
tools/providers/verify_claude_connection.mjs
tools/ui/verify_dashboard_overview.mjs
```

The owner can review the served Overview and the selected account page by
refreshing their browser. Organization/global capacity aggregation, forecasts,
mixed-account running-agent ownership, alerts, operations, and full M4 retain
their existing incomplete status.
