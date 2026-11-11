# M7 Check connection UI increment

Status: intermediate T007/T011 implementation. Genuine Check-to-money browser
acceptance remains Not Run; this is not ticket or milestone completion.

## Scope

P02 owns these controls under focused plan 1.1.0, FR-BUDGET-001/002/004 and
M7-A01/A07. Consume generated `billing_check_connection_v1` and
`billing_get_run_status_v1` operations and the account financial query. Root and
P01 own the underlying contracts, composition and generated 83-operation client.

- An actual metadata-only account shows disabled Check connection with the
  local credential instruction. Stored credentials are eligible for the admitted
  first Anthropic action; other provider actions say not yet available in this
  build, not provider Unsupported. No enable-monitoring button is invented.
- POST carries the captured account ETag, connection version and one idempotency
  key. Ambiguous results retain the original intent; Resolve check outcome uses
  that exact intent/key. It does not create a second request identity or
  automatically repeat a mutation after reload/sign-in.
- A known run uses real status GETs, checks returned account/resource/run IDs,
  and polls at two-second intervals while visible and pending. Requests abort
  on unmount/navigation. Polling has a deadline bound and stops on a read error;
  explicit Refresh check status reconciles the same run. Scope/credential
  generation changes invalidate the previous run display.
- Only allowlisted nonsecret request/run metadata is retained in per-tab
  sessionStorage: account/resource IDs, versions/generations, idempotency key,
  run ID and deadline. No credentials, browser authorization values or provider
  payloads are stored. Known runs resume GET after reload; unknown POST outcomes
  require explicit resolution. Invalid/foreign/oversized retained intent is
  rejected by a pure parser.
- Terminal status triggers a new financial `as_of` while preserving the exact
  reporting interval, including UTC-midnight crossing. The selected report/table
  is reset together. Account record version changes no longer remount the
  financial panel and silently reset its range. Queued, successful and failed
  run states never automatically claim Connected or enable monitoring.

## Red / Green evidence

Before implementation:

- `node frontend/tests/pure/billing-check-presentation.mjs` failed with
  `ERR_MODULE_NOT_FOUND` for the missing policy module. Pure cases cover
  credential/provider eligibility, pending/terminal states, account/resource/run
  mismatch and advancing only the read instant across midnight.
- Production build passed; the existing dedicated real browser reached a newly
  created account and billing metadata, then failed at `range_and_read_only`.
  Its newly added first assertion waited for the absent Check connection button.
  This was a genuine built-UI failure, with no stored key or invented telemetry.

After implementation:

- Pure Check policy and exact-money/UTC suites: Passed. Additional pure parser
  checks reject wrong-account, unknown-field, invalid-version, malformed,
  oversized and incomplete run/deadline metadata.
- Strict TypeScript and Vite production build: Passed.
- `M7 BUDGET ACCOUNT BROWSER: PASSED`: actual missing-key Check is disabled,
  local-entry reason is visible, no enable-monitoring control exists; real
  metadata/no-report/range/reload/narrow/read-only checks remain green.
- `P02 ACCOUNTS ADMIN: PASSED — real API, SQLite, and built browser` and
  `P02 BROWSER: PASSED — accounts_admin`: existing API-only, mixed and Ollama
  flows remain green.
- Browser script syntax and `git diff --check`: Passed.

Both browser scenarios ran against built assets, an actual temporary migrated
SQLite database, Uvicorn, IAM and Chromium using the existing isolated P02 runner.
The final helper context exited 0 and removed only links it created; the
exclusive helper window was explicitly released to root.

Commands use the existing helper/build sequence in
[account financial UI evidence](m7-account-financial-ui-2026-11-11.md), followed
by `node frontend/tests/pure/billing-check-presentation.mjs`.

## Limits and handoff

Stored-key POST acceptance, positive run-status polling/reload recovery, genuine
terminal-to-money refresh and failure beside a prior monetary value remain
**Not Run in the browser**. No real credentials were supplied and no synthetic
status/report responses were substituted. Backend action/status verification
belongs to its separate evidence. The current narrow browser Green is not a
claim that the full enrollment/collection journey passes.

Files: `BillingConnectionPanel.tsx`, `BudgetAccountPanel.tsx`, `AccountPage.tsx`,
new `billingCheckPresentation.ts`, shared `api/client.ts`, the pure Check test,
existing dedicated `budget_account.mjs` and this evidence. No generated file,
dependency, migration, provider profile, managed key, installed account or
service configuration was changed. Root owns canonical gate/catalog integration
and subsequent genuine source-to-screen verification.
