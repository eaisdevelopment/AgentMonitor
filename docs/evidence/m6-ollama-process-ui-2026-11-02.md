# Ollama process relationship display candidate

M6-T013, M6-A06 and AC-PROC-001..004; P02 consumes the existing P01 runtime process metrics API. Ollama rows now explicitly say account and model relationships are unresolved; process identity, metrics, freshness and partial-coverage semantics remain sourced from the existing API. No provider or account relationship is inferred. No API, migration, or dependency changes.

A real local diagnostic using the existing isolated P02 harness reached actual Ollama process observations and failed on the missing relationship labels before the UI change, then passed afterward. The harness uses a newly bootstrapped temporary dashboard administrator. Under the owner's current interpretation of the real-account test rule, this diagnostic is not admissible signed-in browser acceptance evidence. Genuine owner-authenticated browser Red/Green and M6-A06 acceptance remain Not Run; no provider account or telemetry was fabricated. The live service and user profiles were not changed.

The M6 evidence policy separately treats an unavailable signed-in browser as Not Run even if a later database snapshot has process observations. Pure policy Red: the new test observed `failed` instead of `not_run`. Green: all 14 direct evidence policy tests passed. The browser evidence script waits for the actual process API response and compares the displayed row with the same page and a real provider-filtered query; it does not infer a UI defect from a later snapshot.

## Real owner browser, 3 November 2026

The owner signed in to the shared browser. On deployed revision `4d189ca`,
the browser check incorrectly returned `signed_in_dashboard_unavailable`:
it expected an `AgentMonitor` heading, while the authenticated Accounts page
has an Accounts heading and a visible Sign out button. Replacing that check
with the actual Sign out control lets the same owner session reach revision
verification. That next stage reports `dashboard_revision_unavailable` because
the real operations API returns an unknown source revision. This proves the
authentication-selector correction only; it does not pass the complete browser
check. No credentials, account records or provider state were changed.

A separate read-only Playwright check in that same owner session opened
`/sessions` on deployed `4d189ca` and found one real Ollama process row with
both Account unresolved and Model unresolved visible. The authenticated local
catalog endpoint returned HTTP 200, daemon version `0.24.0`, zero installed
models and zero loaded models. These counts describe this configured local
daemon only; they do not establish the model state on another desktop or host.
The verification tab was closed without changing the owner's Accounts tab.

`AUTO-M6-CURRENT-UPDATE` passed its limited operational scope for `4d189ca`;
local and LAN HTTP returned 200, and the service was active with
`Restart=on-failure`. The integrated worker tests passed 12 tests with the one
anonymous-provider test deliberately deselected. `AUTO-QUALITY` passed after
linking the existing development tools into the isolated checkout; the initial
attempt without those tools failed its local control prerequisite. These
results do not establish cloud onboarding, cloud balances, history, or full
M6 acceptance.

On deployed `3bb38f6`, the owner-authenticated browser check passed the exact
revision check but initially failed `ollama_account_form_unavailable` because
it checked the Provider control immediately after the Accounts heading,
before the registry response had rendered the form. The corrected test waits
up to 15 seconds for the real Provider control; it does not supply or replace
any API data. The browser connection disappeared during the first rerun, so
that attempt remained Not Run. Reopening the same dedicated browser profile
retained the owner's session without reading credentials. The next run passed
account-form availability, process visibility and dashboard continuity
(including the product carousel, six viewport sizes, reduced motion and
keyboard focus). Cloud capacity and history remained Not Run with
`real_ollama_accounts_unavailable`; the script exited 3 rather than claiming a
full pass. This used the corrected local test script against the exact deployed
`3bb38f6` application, without registry mutations.
