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

## Organization selection and low-quota emphasis — 2026-09-29

The owner's next request approves the bounded P02 increment recorded in the
same change plan. Requirements `FR-UI-001/002/004/005/006` and selected
`AC-UI-002/003/005` apply. `CTR-UI-001` and `CTR-API-001` V1 and their registry,
capacity, and observed-identity responses remain compatible and unchanged.

Compact dynamic organization buttons support single and multiple selection.
All organizations is the initial/reset choice. Selecting a group isolates it;
further selected groups join the view. An empty selection is explicit instead
of silently restoring unrelated accounts. Ungrouped/unavailable assignments
get their own options when present. Filtered counts, manual read refresh, and
30-second API refresh retain the current selection within Overview. Navigation
or reload returns to All; no selection is placed in browser storage.

The account list sorts by the minimum usable remaining percentage across its
native quota windows, with missing percentages last and deterministic registry
name/account-ID ties. The display retains every window and its freshness.
At or below 20%, the individual window's bar and value are red with a textual
Low label and accessible low wording. Other windows keep their normal color.
The threshold does not alter the producer's health policy or reading-state
label and does not aggregate organization capacity.

### Incremental real-browser Red and Green

The existing live overview verifier was extended before production changes.
It used the actual authenticated loopback service, real registry organizations,
current V1 per-account quota, and the built production UI. No provider response
was constructed, persisted, intercepted, or replayed.

| Increment | Real evidence |
|---|---|
| Organization filter Red | Exit 3: `DASHBOARD OVERVIEW: BLOCKED — organization_filter: organization_filter_missing`. |
| Filter Green / ordering Red | After the filter implementation, single/multiple/reset/empty selection and manual refresh Passed; the verifier advanced to exit 3: `DASHBOARD OVERVIEW: BLOCKED — lowest_quota_first: accounts_not_sorted_by_lowest_remaining_quota`. |
| Ordering Green / color Red | After ordering was implemented, the actual lowest-percentage order and accessible ascending column Passed; the verifier advanced to exit 3: `DASHBOARD OVERVIEW: BLOCKED — per_window_quota: low_quota_bar_not_red`. |
| Color and initial combined Green | Exit 0: six real rows; single/multiple/reset/empty selection; retained manual refresh selection; lowest quota first; one actual low red bar and eleven normal bars; exact per-window readings; 1920/1280/390 layout; keyboard filter/account access and read-only navigation. The low reading was 18%; the test used the live numeric field, not a hardcoded account or percentage. |

The verifier also waits for the actual subsequent 30-second account GET and
checks that selection and filtered rows survive that periodic refresh. This
does not change the clock, native collection cadence, or provider state.
The final `AUTO-CLAUDE-CONNECT` **Passed (exit 0)** against the exact built
checkout: five real API/native safeguards in **19.66s**, the real pending
connection browser, the actual owner-completed identity/monitoring/quota
receipt, four real selected managed quota tests in **5.05s**, compact connected
status, and the six-account Overview. The extended Overview check Passed
single/multiple/reset/empty selection, keyboard filtering, retained selection
after both manual refresh and the actual subsequent periodic GET, ascending
minimum quota, one low red/eleven normal bars, desktop/narrow geometry, and
zero API mutations. All six real rows remained on the first 1920×1080 screen.

The isolated real SQLite/API/browser `monitoring_dashboard` scenario also
Passed, retaining its explicit account-detail Blocked qualification because
that database contains no registered accounts. `AUTO-QUALITY` Passed strict
typechecking/build, zero module-boundary violations, and unchanged compatible
44-operation OpenAPI/generated-client checks. The bounded independent P02
review found no blocking implementation, accessibility, privacy, or test
integrity issues. `AUTO-DOCS-CHECK` Passed all 258 Markdown files, synchronized
planning Passed, local `AUTO-GIT-PREFLIGHT` Passed, and `git diff --check`
Passed. Remote push/release was Not Run.

Exact live 20% and 0% cases, missing-percentage ordering among populated rows,
and naturally unavailable organization lookups were **Not Run**: those
conditions were not present in the six-account environment. The inclusive
numeric `<= 20` rule and missing-value-last comparator are present in code;
the 18% actual reading supplies the live red-color/text evidence. No fake
quota, consumed allowance, or registry changes were used to manufacture cases.

### Increment impact and changed files

There is no backend, API/schema, generated-client, dependency/license,
migration, provider/default-profile, running-agent, authentication, or native
collection-cadence change. The production frontend build is served by the
existing service without restarting it. No prompts, responses, credentials,
provider pages, browser cookies, populated screenshots, or traces were read
or retained. Rollback restores the prior compatible static build.

```text
docs/README.md
docs/evidence/dashboard-density-and-quota-overview.md
docs/modules/react-dashboard.md
docs/plans/integration/claude-managed-account-connection-change.md
frontend/src/app/dashboard.css
frontend/src/features/overview/AccountQuotaOverview.tsx
tools/ui/verify_dashboard_overview.mjs
```

The increment retains the earlier full-M4 limitations and does not change
organization aggregation, forecasts, process ownership, alerts, or operations
scope.
