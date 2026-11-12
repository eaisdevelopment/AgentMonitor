# M7 stored-window navigation and captured collection intent

Status: local implementation; installed verification pending. Requirements
FR-BUDGET-001/002/004, FR-HIST-001, FR-COL-004/008; tickets T007/T010/T011,
M7-A06/A07/A09. This increment does not close those tickets or M7.

## Behavior and boundaries

The account financial panel adds Previous window, Next window and Latest
completed window. Navigation keeps the read snapshot; resizing preserves the
end; Refresh rereads the same interval at a new snapshot. Links retain resource
selection while dropping an obsolete report. Period-only links survive the
shared shell and reload. Reads never collect. Missing retained coverage remains
explicit rather than becoming zero. Prior-scope report discovery, full monetary
verification and complete collection controls remain separate unfinished work.

M04 adds CTR-COL-002 2.3.0 context/admission/authority types. The existing canonical
target JSON carries exact 7/30-day interval, category and at most one grouping.
Legacy raw billing and cloud records remain readable. Reconstruction, replay,
commit authority and latest-run lookup preserve the captured context. M05's
published run-state query seam accepts the additive context union. There is no
new table, queue, credential handling, dependency, license or migration.

Anthropic/OpenAI cost builders accept explicit captured context with a distinct
request identity; old callers retain V1 semantics. Only ungrouped cost is admitted
here. Both operation-family allowlists include thirty-day costs. Source policies
validate actual selected UTC intervals without falsifying request time. This
prepares durable selected collection; it does not itself enable Collect now or
claim completed scheduling/usage/category coverage. Existing workers and source
request/deadline bounds remain in force; no provider accounts/profiles changed.

## Test evidence

- Earlier contract Red: nine pure cases failed for absent captured-context types;
  rerun on this continuation: nine Passed.
- UI pure Red: missing window helper and period-only selections rejected by
  parser/shell. Green covers 7/30 navigation, cutoff, resizing, Refresh versus
  Latest, microsecond validation, resource retention and invalid URLs.
- Real installed browser Red at 02:07:43 UTC against `ff285c4`:
  `stored_window_controls_missing`; authentication, Overview and filters passed,
  two real financial rows, zero unsafe requests. The expanded probe checks
  API/DOM/URL bounds, older-window reload, Refresh, Next, resize, Latest and a
  period-only deep link, followed by existing navigation/layout/pool checks.
- Independent UI review found that AccountPage keyed the panel by its query
  string. Installed browser Red at 02:19:01 UTC proved
  `same_context_refresh_remounted_panel`. The panel now stays mounted per account;
  existing account/version/period fences still clear incompatible readings.
  A same-account plain URL deliberately restores the default seven-day view.
  The browser checks retained node identity; it does not manufacture a network
  outage or claim that naturally unavailable failure scenario passed.
- M04 Red: absent codec, unsupported captured authority and actual empty-SQLite
  `collection_query_invalid`. Seventeen new pure/empty-SQLite cases passed;
  172 related contract/storage regressions passed with no skips.
- A01/A02 Red: builders rejected the new report_context argument. Pure cases
  cover legacy identity, exact selected current/past intervals, tampering and
  rejection of unadmitted categories/groupings; final counts recorded below.
- Canonical collection_guards: 46 Passed. This proves no-credential guards,
  policy and actual empty storage behavior, not successful monetary collection.
- TypeScript typecheck passed. Initial expanded canonical pure run: 635 Python
  tests and nine presentation suites Passed; subsequent combined counts below.

Constructed inputs are pure only. No telemetry was seeded. Positive billing
capture/replay/commit and populated context-selection SQL remain unverified
without actual billing authority. Existing cloud counts cannot substitute for
money. The browser probe reads genuine installed records and does not change
owner configuration. No new owner approval or setup request was introduced.

## Integration result

Canonical pure run passed 670 Python cases plus nine presentation suites.
A01/A02 final focused suite passed 192 cases, including the trailing-year bound.
AUTO-QUALITY at 02:16 UTC passed Ruff773, mypy712, zero import violations,
93-operation compatible generated client, TypeScript and production build.
The boundary checker needed only the new inherited AdmissionV2 symbol registered.
UI review then added the remount correction above; the final AUTO-QUALITY rerun
at 02:20:35 UTC passed the same static/type/generated checks and production build.
Candidate installation and real browser Green remain pending. GitHub
publication and installed state will be recorded separately after verification.
