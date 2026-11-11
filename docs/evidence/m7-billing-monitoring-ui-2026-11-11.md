# M7 monitoring controls and stale Check display

Status: intermediate T007/T011 implementation under focused plan 1.1.0;
M7-A01/A07/A09. No complete enrollment, monitoring or M7 acceptance claim.

## Implemented boundary

P02 consumes generated `billing_get_monitoring_v1` and
`billing_set_monitoring_v1`, backed by CTR-REG-014 1.4.0. Root/P01 own the
85-operation generated client, contracts, backend eligibility and scheduling.

- Compact controls read the server's current preference, `can_enable`,
  `can_disable`, verification reference and reason. They never derive permission
  from local Check success or Stored credential text. Missing-key Enable uses
  `aria-disabled` plus a guarded handler, allowing keyboard focus on its help.
- Each PUT captures the displayed account ETag, connection version, scope and
  binding generations, verified run, intended preference and idempotency key.
  It does not optimistically change the displayed preference. A successful
  matching response triggers fresh authoritative GET/status reads.
- Ambiguous mutations retain their original nonsecret intent in per-tab
  sessionStorage. Explicit Resolve monitoring outcome repeats that exact request
  identity. Reload/sign-in performs status GET only, not an automatic PUT. No
  `can_enable`, credential material or browser eligibility proof is persisted;
  a retained verified-run ID is only an original command selector, checked again
  by the server.
- Disable follows `can_disable` independently of credential eligibility.
  Runtime-unavailable enablement is labelled "API monitoring is not yet available
  in this build", not provider Unsupported. Metadata reload, focus and terminal
  Check reread server eligibility.
- Completed Check display now retains its target metadata separately from the
  pending request. A pure guard checks account/resource, lifecycle, scope epoch
  and current stored credential generation even after the pending intent was
  cleared. Changed authority suppresses the old result immediately and clears
  it; restoring a page does not restore a successful-verification claim.
  Original pending/unknown Check reconciliation remains intact.

## Red / Green

Before implementation, the extended pure suite failed because
`currentCheckEvidence` was not exported. Its new cases require a matching
authority snapshot and reject rotation, changed scope/account, disconnected
lifecycle and absent evidence. Inputs remain pure metadata, never simulated
provider responses or storage records.

The production build then passed, while the actual isolated browser failed at
`range_and_read_only`: its new assertion could not find the missing monitoring
control after real account/connection metadata creation. No key or financial
telemetry was inserted.

After implementation:

- `node frontend/tests/pure/billing-check-presentation.mjs`: Passed, including
  stale-evidence guards, closed runtime/credential reason mapping and restoration
  of a disabled intent with no binding. Foreign-account and enabled-without-proof
  intent are rejected. Earlier Check/cutoff tests remain green.
- Exact money/UTC pure suite: Passed.
- Strict TypeScript and production Vite build: Passed.
- Dedicated built browser: Passed. Real server missing-key eligibility renders
  a focusable disabled Enable with the local-entry reason. Pressing Enter does
  not dispatch a PUT; total unsafe requests during the financial read phase
  remain zero. Existing range, refresh, reload and narrow checks remain green.
- Full existing `accounts_admin` real browser: Passed, preserving API-only,
  mixed subscription/billing and Ollama setup behavior.
- Browser syntax and `git diff --check`: Passed.

Both browser scenarios used the existing P02 temporary migrated SQLite/IAM and
Uvicorn runner with built assets. A final dedicated rerun verified the keyboard
no-mutation assertion. Helper contexts exited 0, cleaned their owned links and
the exclusive window was explicitly released to root.

The reproducible helper/typecheck/build/browser command is recorded in
[account financial UI evidence](m7-account-financial-ui-2026-11-11.md); run the
Check pure command above as well. No dependency or new test framework was added.

## Remaining real verification and files

Genuine successful Check eligibility, Enable mutation, scheduled collection,
Disable after credential loss, positive idempotent replay/reload, and actual
rotation invalidating displayed success remain **Not Run in this browser lane**.
These require genuine evidence; no fake network, credential or seeded report
substitutes were used. Backend mutation/fencing evidence is separate. Runtime
enablement remains unavailable until its real scheduler wiring is admitted.

Changed only `BillingConnectionPanel.tsx`, `billingCheckPresentation.ts`, shared
`api/client.ts`, `billing-check-presentation.mjs`, `budget_account.mjs` and this
evidence. No generated source, backend production, migration, provider profile,
secret, owner account configuration or installed service was changed.

## Independent review correction

Root review found that the original UI copied `verified_run_id` into a Disable
command, which the backend rejects. The current-status display also lacked
account and connection record-version comparisons. The existing expressions
were extracted unchanged into the pure helpers actually called by the UI,
then the retained tests demonstrated these semantic Reds:

- `Changed account version must suppress stale eligibility`: actual `true`,
  expected `false`.
- `Disable must not submit an enable verification proof`: actual `verified-run`,
  expected `null`.
- `Invalid old Disable intent must not be replayed`: the restore parser returned
  an invalid command carrying an enable proof instead of rejecting it.

The corrected request builder always supplies null verification for Disable
and preserves the current verification run for Enable. Invalid old Disable
intents are rejected rather than silently rewritten/replayed. The display guard
now matches account/resource IDs, account/connection record versions, scope and
binding generations against freshly read metadata. A mismatch gives a refresh
instruction instead of stale eligibility or an indefinite loading claim.

Pure tests, strict TypeScript, rebuild and the dedicated actual no-key browser
passed after this correction. The helper context exited 0 and was released to
root. The genuine verified Disable path remains Not Run because no such account
was fabricated.

## Collector availability wording

The runtime-unavailable reason also covers an unhealthy or quarantined collector,
so its UI text now reads: “The billing collector is unavailable. Refresh
monitoring status to check again.” This changes no eligibility or mutation rules.
The pure presentation test first failed against the former build-only wording,
then passed with the corrected mapping using
`node frontend/tests/pure/billing-check-presentation.mjs`. No browser rerun or
shared helper was needed for this copy-only change. Genuine positive monitoring
verification remains Not Run in this browser lane.
