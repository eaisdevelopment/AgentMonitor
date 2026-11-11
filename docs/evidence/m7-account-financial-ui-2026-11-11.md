# M7 first account financial panel

Status: intermediate T011 implementation. No full T011 or M7 completion claim.

## Scope and contracts

- P02; FR-BUDGET-002/004, AC-UI-005/006 and M7-A07.
- Consume P01 `capacity_get_account_api_budget_v1` and the generated
  `AccountBudgetCurrentWireV1` through the shared client wrapper. The application
  contract is CTR-CAP-006 2.2.0; no frontend financial aggregation.
- Compact account panel: pinned seven completed UTC days, explicit thirty-day
  selection, server-calculated spend, actual scope/source/coverage and separate
  latest collection/attempt state. Refresh reads persisted data only.
- Money formatting uses BigInt/string operations. USD uses half-even two-place
  display, explicit signed sub-cent labels and accessible exact amounts. Other
  currencies retain exact decimals rather than assume minor-unit rules.
- The cost table displays selected immutable report buckets and exact amounts;
  source intervals remain separate from report revisions. Local fifty-row
  display increments reveal existing returned facts; this is not a claim that
  the separate T010 history endpoint or its cursor is implemented.
- API-only account setup remains available. Mixed accounts preserve subscription
  sections and collapsed billing setup; the financial panel appears when the
  financial query returns a resource. Ollama's existing cloud connection/balance
  remains authoritative; no new unconfigured billing panel contradicts it.

## Red and corrections

1. `node frontend/tests/pure/budget-account-presentation.mjs` failed with
   `ERR_MODULE_NOT_FOUND` before the presentation module existed. Inputs are
   pure exact-formatting/UTC test vectors and never enter provider, HTTP, storage
   or browser boundaries.
2. Production build succeeded, then the dedicated browser scenario failed at
   `budget_panel`: real isolated login and API account metadata creation reached
   an account with no `API usage & spend` region. No provider telemetry was
   inserted or network response replaced.
3. First implementation passed typecheck/build but failed at
   `configured_no_report`. Billing metadata creation reloads the account without
   necessarily changing its record version; the panel originally depended only
   on that version and retained its unconfigured query. It now responds to the
   freshly read account object, clears superseded metadata and aborts obsolete
   requests.
4. Next browser run exposed a range-label defect. Wrapping the select in its
   label included option text in the accessible name; exact `Report range`
   lookup could not select thirty days. Added explicit label/selector IDs.
   The test also pairs the action/response promises so a timed-out response
   cannot escape the scenario's closed failure reporting.

## Verification

- Pure formatting/UTC tests: Passed. Includes coefficient beyond JavaScript's
  safe integer range, positive/negative sub-cent values, both half-even tie
  directions, exact non-USD display and seven/thirty-day UTC cutoffs.
- Strict TypeScript and production Vite build: Passed.
- Dedicated real browser: `M7 BUDGET ACCOUNT BROWSER: PASSED`. Actual migrated
  temporary SQLite, Uvicorn, IAM and built UI; no credentials/provider account
  configuration beyond the isolated runner's ephemeral local administrator.
  Real metadata creation progresses from unconfigured to no report. Thirty-day
  query and Refresh return actual empty reports, never zero spend. Reload,
  768px/390px overflow checks and zero mutation requests during financial reads
  pass.
- Existing `accounts_admin` regression: Passed (`P02 ACCOUNTS ADMIN: PASSED —
  real API, SQLite, and built browser`; runner exited 0). This covers existing
  API-only, mixed subscription/billing and Ollama setup behavior.
- Browser script syntax, dedicated runner Ruff and scoped diff checks: Passed.
- Genuine monetary API-to-DOM, actual failed collection beside a prior monetary
  report, populated exact table, and installed browser: **Not Run**. Require
  genuine source reports; pure inputs are not substituted for this evidence.

Reproducible command from this worktree:

```sh
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python - <<'PY'
import subprocess
import sys
from tools.automation.implementations.auto_m6_exit import _temporary_tool_environment
with _temporary_tool_environment():
    result = subprocess.run(['npm', '--prefix', 'frontend', 'run', 'typecheck'], check=False)
    if result.returncode == 0:
        result = subprocess.run(['npm', '--prefix', 'frontend', 'run', 'build'], check=False)
    if result.returncode == 0:
        result = subprocess.run([sys.executable, 'frontend/tests/browser/m7/run_budget_account.py'], check=False)
    if result.returncode == 0:
        result = subprocess.run([sys.executable, 'frontend/tests/browser/p02/run_browser.py', 'accounts_admin', '--no-build'], check=False)
raise SystemExit(result.returncode)
PY
node frontend/tests/pure/budget-account-presentation.mjs
```

The existing helper cleans only links it created. The dedicated runner reuses
P02 isolated storage/service setup and emits closed stage results. No dependency,
migration, provider call, installed service/configuration or secret changes.
The final helper context exited successfully and its exclusive tool window was
released to root after both browser scenarios passed.

## Files and remaining work

- New `frontend/src/features/accounts/BudgetAccountPanel.tsx` and
  `budgetPresentation.ts`; small insertion in `AccountPage.tsx`.
- Generated-type exports and `budgets.account` wrapper in
  `frontend/src/shared/api/client.ts`; no generated files hand-edited.
- `frontend/tests/pure/budget-account-presentation.mjs`,
  `frontend/tests/browser/p02/budget_account.mjs`,
  `frontend/tests/browser/m7/run_budget_account.py`, and this evidence.

The newly published Check connection action still needs its actual UI control;
this increment does not invent an enable-monitoring control. Full daily-history
API/cursors, URL/shell filter retention, Overview/grouped summaries and live
monetary reconciliation remain assigned work. A no-report panel is not the
first real money-on-screen acceptance result.

Subsequent same-day [Check UI evidence](m7-billing-check-ui-2026-11-11.md) records
the action control, status polling and pinned-interval refresh increment. Its
genuine credential-backed browser path remains explicitly Not Run.

## Same-context refresh correction

T011 correction reviewed against `e40b23f`, 11 November 2026, under the same
FR-BUDGET-002/004, AC-UI-005/006, M7-A07 and CTR-CAP-006 2.2.0 scope.

The previous Check-completion effect erased the last financial response before
its replacement read succeeded. Rereading account metadata also erased it merely
because the object reference changed. The panel now stores the immutable
response together with its original account/configuration generation and UTC
interval. Same-context Check/Refresh keeps that snapshot while reading; an error
or rejected mismatched response leaves its original value, scope labels and
timestamps. A successful response replaces the entire snapshot, never merges new
scope metadata with old facts. Both render-time context selection and existing
request abort guards fence obsolete responses.

The currently available configuration fence is account `record_version`; a
changed version conservatively invalidates the prior snapshot. An unchanged
version with a freshly read account object does not. The panel has no separate
live scope-generation prop: external resource/scope edits are learned through
the next successful financial response, which replaces the whole snapshot with
its own scope. This correction introduces no additional registry query or new
contract and does not claim instant detection of unseen external edits.

Red/Green evidence checkpoint: 20:36:53 UTC. Meaningful Red: extracted the existing object-reference and
Check-revision invalidation rule into the actual-used pure presentation policy.
`node frontend/tests/pure/financial-read-presentation.mjs` failed its assertion
`Check completion must retain the prior same-context reading until its replacement succeeds`
with `false !== true`. This was a behavior failure, not a missing module.

Green: compare stable account/provider/configuration generation and UTC interval,
ignoring a Check-completion revision or an equal-version object reload. The same
command passed; existing `budget-account-presentation.mjs` and
`billing-check-presentation.mjs` also passed. Pure contexts remain no-I/O inputs;
no provider report or monetary observation was invented. Test cases additionally
reject another account/provider, changed generation, seven-to-thirty-day switch
and moved UTC cutoff while accepting equivalent UTC timestamp encodings.

Post-refactor verification: strict TypeScript, production Vite build and the
existing dedicated real `frontend/tests/browser/m7/run_budget_account.py`
scenario all passed; its output was `M7 BUDGET ACCOUNT BROWSER: PASSED`, exit 0.
The temporary tool helper was used exclusively and released after cleanup.
The browser exercised actual migrated SQLite/HTTP/IAM, no-report metadata,
thirty-day selection, Refresh, reload, narrow layouts and read-only behavior.
It did not contain monetary observations. Reproduce with the existing helper
command above through the dedicated browser step and run:

```sh
node frontend/tests/pure/financial-read-presentation.mjs
node frontend/tests/pure/budget-account-presentation.mjs
node frontend/tests/pure/billing-check-presentation.mjs
```

Changed files are this evidence, `BudgetAccountPanel.tsx`, new actual-used
`financialReadPresentation.ts`, and its pure test. No dependency, schema,
migration, credential, provider, installed-service or financial formula changes.
Populated real source/API/DOM behavior after a genuine failed replacement remains
Not Run until genuine financial reports exist; pure policy evidence is not that
live verification.
