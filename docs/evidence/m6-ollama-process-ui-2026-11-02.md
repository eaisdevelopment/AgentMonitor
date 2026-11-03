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
