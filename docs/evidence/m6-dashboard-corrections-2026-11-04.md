# M6 dashboard corrections and remaining verification

This is an intermediate delivery record, not M6 acceptance. Implementation is
authorized by the existing approved local, cloud and process plans. No new
owner approval or account name was required for the corrections below.

## Delivered batch and traceability

This batch was first deployed at `37ac828171026de2f3b2a408e7d62d4105595f80`.
`AUTO-M6-CURRENT-UPDATE` passed for the unchanged v1_0719 schema, and the
authenticated operations API reported that exact build revision with HTTP 200.

| Change | Owning boundary and requirements | Evidence |
|---|---|---|
| Keep settled connection status refreshing while visible; retry after local read errors | P02, existing versioned Ollama connection GET; M6-T010/T014, M6-A01/A08, FR-COL-003, AC-UI-005 | Before the production change, the real installed browser failed `connection_refresh.mjs` with `settled_connection_not_refreshed`. Typecheck/build passed after the change. Installed Green is still required: the first post-rollout attempt could not establish its prerequisites (`connection_refresh_unavailable`), and the shared session subsequently returned an authentication-required response. |
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

## Combined check at 9bc2f8f

`9bc2f8f7b01201256733bdfaebe5742eb2788819` was deployed through the same
unchanged-schema command. `AUTO-M6-EXIT` ran at that clean revision. Build,
local admission, quality, documentation and planning all passed. The direct
source/security and real database snapshot also passed. Its private artifact is
`.agentmonitor-local/m6-evidence/direct-9bc2f8f7b01201256733bdfaebe5742eb2788819-05aa9c508f0abc13.json`,
SHA-256 `05aa9c508f0abc13fc8960dc1573e19590e2f20f4dd8b1aad2a62162ad23f437`.

The command exited **1 (Failed)**, not a completion receipt. The artifact
reports browser checks as Not Run (`signed_in_dashboard_unavailable`) and the
official comparison as Not Run (`official_usage_dashboard_unavailable`). The
result combiner incorrectly converted the former into `ollama_capacity_ui_missing`
solely because current database readings existed. The correction from `b6c0baf`
preserves this exact unavailable-session outcome as Not Run. Forty-two policy
tests passed, including the prior failing case and controls that retain genuine
authenticated missing-capacity failures and concurrent-change Blocked states.
It changes no provider data and does not accept an unexecuted test.
Separately, model-present, SDK coverage and natural failure/recovery evidence
were absent. The dashboard itself remained active and returned HTTP 200.

## Remaining work is not one blanket blocker

| Category | Exact remaining action |
|---|---|
| Engineering verification | The combined check below ran after all identified corrections; no additional engineering defect was reported by that run. Preserve the remaining live prerequisites instead of adding scope. |
| Installed browser | Authorized automatic login restored the session. Connection refresh and all five composite browser checks passed after the history verifier followed real pagination. |
| SDK scope | Owner adds/selects the actual account or declares the actual coverage through the dashboard. Knowing the account email is not an implementation prerequisite. No manual fabricated record is permitted. |
| Model-present observation | Observe the actual model-present endpoint without loading/downloading/stopping a model. The currently approved fixed loopback source reports empty installed/loaded lists. |
| Natural recovery | Observe a qualifying real failure/recovery interval and existing-provider/dashboard continuity. Do not manufacture an outage or claim an absent scenario passed. |
| Acceptance | Record the required receipt and owner review only after the actual technical outcomes justify them. M7/M8 remain separate. |

Missing external observations constrain the associated acceptance claims;
they do not justify stopping independently executable engineering work. The
ticket register remains in progress where its dependencies or live criteria
are not closed. Previously supplied approvals and account outcomes remain valid.

## Final combined run for this correction batch

The unchanged-schema update passed for deployed revision
`5839f05e029005d72cff89ddba571b4794d11482`. On that clean revision,
`AUTO-M6-EXIT` exited **3**, with overall **Not Run**, no Failed outcomes and
no completion receipt. Build, local Ollama admission, static quality,
documentation and planning all passed. ST-OLL-001 passed; the remaining Story
and M6 acceptance outcomes retain unavailable live prerequisites. This does
not erase earlier real results or convert unavailable checks into passes.

The command retained
`.agentmonitor-local/m6-evidence/direct-5839f05e029005d72cff89ddba571b4794d11482-d68ec1a77d922a05.json`,
SHA-256 `d68ec1a77d922a0547ffb48531115d1f56bfc1d137029447285c4fd7df829ada`.
Its real database snapshot and source/security checks passed. One verified
cloud target still had current balance and matching history; no configured
Ollama alert target or natural recovery was observed. Both loopback and the
configured LAN address returned HTTP 200 after deployment. The shared browser
still required sign-in, so installed connection-refresh Green and the full
authenticated comparison remain unexecuted on this revision.

This final evidence addition is documentation only. The exact deployed and
checked implementation remains `5839f05`; it does not claim that a later
documentation commit has been deployed or independently reverified.

## Automatic local login and resumed browser verification

The owner's 4 November instruction explicitly confirms permission to
authenticate to the local dashboard using its stored password. Requiring
owner-operated sign-in was an overly restrictive interpretation, not a
technical necessity. The existing local secret name is
`AGENTMONITOR_DASHBOARD_PASSWORD`; the existing M3 operator already documents
reading that exact entry for authorized verification. The browser can receive
it directly without displaying its value to the coding agent or logging it.
This authorization concerns the local dashboard, not other provider credentials.

The normal login succeeded with HTTP 204 and the subsequent authenticated
account query returned HTTP 200. No password reset, authentication bypass,
database/session edit or service restart was used. No credential value was
printed, committed or passed as a command argument.

On the installed `5839f05` build, `connection_refresh.mjs` then passed with
`local_status_refresh: true` and zero mutation requests. This supplies the
previously outstanding installed Green for the connection refresh correction.
The composite browser check passed account administration, current capacity,
process visibility and dashboard continuity; its history reconciliation failed
with `ollama_history_lineage_mismatch`; the bounded investigation is recorded below.

The official Usage comparison initially failed because the already-open
provider page displayed an older balance. An ordinary read-only browser refresh
of that page resolved the discrepancy. The comparison subsequently passed for
one target at `2026-11-04T10:25:13.576Z`, against source observation
`2026-11-04T10:21:16.435907Z`, with comparison digest
`20ffaf25934d148abb4e248bce15b4e4b54aa8870b2b74ec9c3c53bbbbf2a422`.
No balance value, observation or comparison rule was changed to make it match.

The history investigation found no incorrect displayed values: the initial API
and DOM each contained 200 rows, every checked field matched, and the API
explicitly reported another page. The verifier had incorrectly required the
current observations in that first older-first page. The test-only correction
from `04b9811` and `cb91bda` follows the visible **Load next history page** action,
checks its exact cursor/query and each returned page, and matches all captured
quota windows to exact observation/run identities. It reconciles the current
quota DOM before pagination so a subsequent automatic refresh cannot invalidate
that captured evidence. Repeated cursors, duplicate observations or invalid
pages fail; a 32-page bound returns Not Run instead of inventing success.

The real browser rerun against deployed `5839f05` then exited 0: account
administration, current capacity, history, process visibility and dashboard
continuity all passed for the connected target, with identical current/history
lineage digests. Only the verifier and documentation changed; no production
schema, API, dependency, account, provider profile or service changed. These
results close the authentication-related verification gap, not the separate
SDK, model-present or natural-recovery acceptance requirements.

## Cloud-only browser registry stability correction

After local Ollama deferral, the installed browser check returned
`dashboard_registry_changed_concurrently`. Inspection found that its digest
included `registry_revision`, which is joined from the global
`reg_registry_state` into every account and organization view. Background
installation discovery advances that counter independently of account or
organization edits. A global revision change therefore cannot by itself prove
that the compared account/organization records changed.

Under the existing M6 integration/browser verification scope (M6-A01/A08/A09,
ST-OLL-005), the verifier now compares every returned record field except that
one global counter. It retains per-record versions, timestamps, names,
organizations, monitoring preferences, effective state, identity state,
counts, additions/removals and unknown future fields. The separate zero-write
request guard, full-page requirement and current/history lineage checks stay
in force. Changed-and-restored edits still change record versions.

The pure comparison regression produced one expected Red failure with the old
whole-record digest, while two mutation-detection cases passed. After the
correction all three passed; the existing authoritative comparison suite plus
these tests passed 16 tests. Exit/direct/deferral policy checks passed 57 tests.
The new pure checks are included in the existing canonical exit selection and
its catalog hashes were regenerated.

Real verification on installed revision
`5839f05e029005d72cff89ddba571b4794d11482` then returned **Passed** for account
administration, cloud capacity, capacity history and dashboard continuity.
One actual confirmed cloud target had matching current/history lineage.
Local process verification remained **Not Run — local_ollama_deferred**,
outside M6 scope. SDK remains an owner-configured connection; this one-target
browser result does not prove two-organization coverage or full M6 closure.

Files: `frontend/tests/browser/m6/registry_stability_policy.mjs`,
`frontend/tests/pure/m6-registry-stability.mjs`, the M6 browser verifier,
`m6_direct_evidence.py` and the exit catalog. No production/API/database contract,
dependency, license or migration change. Verification used normal authorized
local dashboard sign-in; no provider key, account/organization configuration,
monitoring preference, provider profile or running agent was changed.

## Controlled cloud recovery implementation

The owner-approved [bounded recovery amendment](../plans/integration/m6-cloud-controlled-recovery-proposal-2026-11-04.md)
adds one genuine isolated-network collector request and normal scheduled
recovery as an alternative to waiting for a natural provider error. This is
M6-A07, M6-T015/T017, AC-LIVE-007 and AC-OPS-003, owned by integration with the
M04 supervisor. CTR-COL-012 and CTR-COMMON-001 remain 1.0.0; the separate internal
controlled receipt is 1.0.0. No public API, schema, dependency or license change.

The supervisor's real held-flock regression failed with
`'quarantined' != 'worker_busy'` before the correction. After catching ordinary
`BlockingIOError` as transient contention, six focused tests and the broader
18-test worker selection passed. Unsafe permissions still quarantine; releasing
a competing lock restores availability without restarting the supervisor. The
anonymous-provider helper test was not part of that lock-only selection.

Pure controlled-evidence rejection tests first produced 70 expected failures
and one pass before validation was implemented. The completed policy checks
foreign nonce/revision/invocation, exact target/binding/source, failed and later
committed runs, namespace separation, cleanup and continuity. Separate
regressions caught an incorrect requirement that Claude/Codex carry Ollama-only
response metadata; their real generic committed-run contract is now accepted.
The focused policy/gate integration suite passed 172 tests. Controlled success
always retains zero natural-recovery targets and declares unobserved
provider-side 401/403/429 coverage.

Real process tests establish distinct kernel network namespaces, refusal to
collect before the GO handshake and cleanup of the owned namespace process.
They use temporary protected files and no provider, credential or database
substitute. The live browser probe was checked against the healthy installed
`5839f05e029005d72cff89ddba571b4794d11482` account: it rejected that reading as a
failed-connection observation and accepted its actual current connection,
exact quota values, observation IDs and collection run. A source observation
precedes durable commit, so its timestamp is checked within the real run's
requested/completed interval.

Files include the supervisor and real boundary tests; controlled runner,
evidence policy and tests; M6 gate/direct classifier/catalog; the rendered
account probe; and the execution plan, ticket register, runbook and automation
scope. Account configuration, credentials, provider profiles and running user
agents remain untouched. Local Ollama remains deferred. The actual isolated
provider failure, ordinary recovery and complete canonical M6 result still
require execution on the deployed candidate; implementation tests alone do
not close M6. Subsequent machine receipts name their exact tested revision.
