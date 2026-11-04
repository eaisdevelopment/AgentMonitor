# M6 dashboard corrections and remaining verification

This is an intermediate delivery record, not M6 acceptance. Implementation is
authorized by the existing approved local, cloud and process plans. No new
owner approval or account name was required for the corrections below.

## Delivered batch and traceability

The installed dashboard revision is `37ac828171026de2f3b2a408e7d62d4105595f80`.
`AUTO-M6-CURRENT-UPDATE` passed for the unchanged v1_0719 schema, and the
authenticated operations API reported that exact build revision with HTTP 200.

| Change | Owning boundary and requirements | Evidence |
|---|---|---|
| Keep settled connection status refreshing while visible; retry after local read errors | P02, existing versioned Ollama connection GET; M6-T010/T014, M6-A01/A08, FR-COL-003, AC-UI-005 | Before the production change, the real installed browser failed `connection_refresh.mjs` with `settled_connection_not_refreshed`. Typecheck/build passed after the change. Installed Green is still required: the first post-rollout attempt lacked its settled-state prerequisite, and the shared session subsequently expired. |
| Show provider-supplied period starts in history, with explicit absence | P02, existing `CapacityHistoryPointV2`; M6-T011/T014, M6-A04/A05/A08, FR-QUOTA-001/002/004/006, AC-HIST-001 | Real browser Red found supplied dates missing. Installed Green compared 200 actual observations, including 100 supplied starts, with no failures and no desktop/mobile document overflow. Current quota API does not supply this field; no start was inferred. |
| Publish implemented local capabilities accurately | A03/M03, existing manifest and `CTR-PROV-OLLAMA-LOCAL-CATALOG-001` 1.0.0; M6-T006/T008, ST-OLL-001, FR-ACC-005, FR-DISC-008 | Two expected manifest/API failures preceded the correction. Six focused checks passed, including actual CLI 0.24.0, fixed loopback source and authenticated API. Cloud admission remains separate. |
| Remove singleton account assumptions from real coverage tests | M02/P01/P02 test boundaries, `CTR-REG-013` 1.0.0; M6-T010/T014 | Pure Red reproduced two eligible accounts being rejected. Twelve checks passed, including private-copy real SQLite, HTTP and built UI. Multiple live connected accounts remain unobserved; no account or owner declaration was invented. |
| Correct operating instructions and stale approval metadata | Operations/integration; M6-T006/T016/T018 | The runbook describes actual account selection, hidden local key entry, rotation, disconnect and cleanup. Scoped approval links replace obsolete pending-approval wording. The bounded security/privacy review identifies no new mandatory defect and retains its limits. |

No production contract shape, migration or dependency changed in this batch.
Provider profiles, user agents and model state were not modified. The refresh
uses the local cached connection-status endpoint; it does not initiate extra
provider requests. Source dates and process labels come from the versioned API.
See the [security/privacy review](m6-security-privacy-review-2026-11-04.md).

## Verification and one consistency correction

`AUTO-QUALITY`, `AUTO-DOCS-CHECK`, `AUTO-PLAN-CHECK`, the ticket validator and
local Git preflight passed. The real installed source-period browser test
passed. The installed composite browser check passed account administration,
process display (including the actual executable label and unresolved account/
model relationships), and dashboard continuity; current balance/history lanes
were Not Run because the confirmed connection was not yet available to that
check. These are not substituted for a passing complete browser result.

The canonical local admission first failed its browser lane because
`p02/ollama_catalog.mjs` still expected two **unknown** capability labels after
the manifest correction. Its actual failure was
`ollama_manifest_not_truthfully_published`. Updating that expectation to two
**supported** labels, with no unknown/cloud declaration, made
`AUTO-M6-LOCAL-ADMIT` pass. Its source-and-test digest was
`bbd2f5dc35739e9c8a88213bb097f9b01a39a72d653f865f74a743623049ecc2`.
This is consistency with the approved behavior, not removal of a requirement.

A subsequent real read-only database snapshot passed: one verified cloud
target had current balance and matching history, and one local installation
and real process were observed. There were no configured Ollama alert targets.
The browser API later returned `401 dashboard_authentication_required`; a
sign-in tab was opened. No password, cookie or session token was extracted.

The alert-evidence correction is now integrated from `922e00e` (M6-T012/T017,
M6-A05, AC-HIST-001/AC-ALERT-002). Its pure Red demonstrated that a healthy
configured target incorrectly required a nonexistent transition. The corrected
reader distinguishes fresh, exact-observation evidence that no transition is
applicable from a genuine durable alert transition. It honors effective
disabled overrides and still requires current-source transitions for low
conditions or recovery of open alerts. Deduplication distinguishes separate
window streams within one event. Eighty-four focused checks passed, including
the real read-only snapshot/history checks. No rule or alert was created; live
configured-alert scenarios remain Not Run because no such rule is configured.

## Remaining work is not one blanket blocker

| Category | Exact remaining action |
|---|---|
| Engineering verification | Run the final canonical check for the integrated corrections and record its actual result. |
| Installed browser | Restore the expired owner session and rerun connection-refresh/current-balance/history verification against the deployed revision. |
| SDK scope | Owner adds/selects the actual account or declares the actual coverage through the dashboard. Knowing the account email is not an implementation prerequisite. No manual fabricated record is permitted. |
| Model-present observation | Observe the actual model-present endpoint without loading/downloading/stopping a model. The currently approved fixed loopback source reports empty installed/loaded lists. |
| Natural recovery | Observe a qualifying real failure/recovery interval and existing-provider/dashboard continuity. Do not manufacture an outage or claim an absent scenario passed. |
| Acceptance | Record the required receipt and owner review only after the actual technical outcomes justify them. M7/M8 remain separate. |

Missing external observations constrain the associated acceptance claims;
they do not justify stopping independently executable engineering work. The
ticket register remains in progress where its dependencies or live criteria
are not closed. Previously supplied approvals and account outcomes remain valid.
