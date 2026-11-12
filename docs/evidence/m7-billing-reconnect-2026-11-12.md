# M7 restored billing connection

Status: bounded increment installed and published at `c1c8e8d` under approved
focused plan 1.1.0. M7 and T002/T010/T011 remain open. This packet fixes the
archive/restore dead end; it does not claim the complete credential lifecycle.

Requirements: FR-ACC-001/004/006, FR-BUDGET-006; M7-A01/A09,
AC-UI-005/006, AC-TEST-001/003/006. M02 owns metadata, P01 the transport,
P02 the visible action; root owns shared contracts and integration.

## Behavior and contract

CTR-REG-014 1.7.0 adds ReconnectBillingConnectionCommandV1 and
BillingConnectionPortV1.reconnect. The existing connection's POST `/reconnect`
requires write:accounts, browser CSRF, idempotency, connection If-Match and
expected account/scope versions. The account must have been restored and the
connection must be disconnected without any active or pending credential.

One SQLite transaction changes only connection lifecycle to pending with
monitoring disabled, increments its version, and writes an audit/outbox event
and replay receipt. Resource identity, scope generation, retained financial
facts, pool membership and retired credential bindings are not rewritten.
Replay after later account/connection changes fails. Reconnect neither contacts
a provider nor revives old access proof. The existing owner-local setup command
becomes available again. A new credential and Check are needed before enabling.

The UI uses this action after Restore account. It preserves current context and
requires a fresh billing-status read after an uncertain result rather than
automatically repeating the mutation. Archived accounts must be restored first.
No schema, dependency, license or secret-custody change; schema stays v1_0734.

## Red and intermediate evidence

- Real migrated SQLite tests for both providers failed with
  `AttributeError: 'SqliteBillingConnectionRepositoryV1' object has no attribute 'reconnect'`.
- Real HTTP test, after providing required Origin, failed
  `billing_reconnect_route_missing`: actual 404 versus required 401. The initial
  request without Origin was rejected by the existing transport guard at 403;
  that was not the route's meaningful Red.
- First registry Green attempt exposed a test expectation error: existing
  account/resource views publish the global registry revision. The tests now
  compare all preserved fields while allowing that revision to advance. No
  production behavior was changed for that correction.
- Focused actual HTTP/registry Green: three tests passed (4.08 seconds),
  covering archive/restore/reconnect, old binding retirement, unchanged scope,
  disabled monitoring, stale versions, idempotency, guards and no secret fields.
- Built-browser Red: existing canonical owner_pool_controls built the actual
  sources and failed at `billing_reconnect_controls` after real archive/restore.
  Two earlier build attempts found the generator's new-operation inventory and
  count incomplete; both were corrected explicitly to 101 operations, with
  compatibility and exact security policies retained.
- Installed read-only Red at 07:11:22 UTC on `540ab8b`:
  `billing_reconnect_contract_missing`. Authentication, exact revision, Overview,
  setup and account layout passed; zero mutation requests. This is a contract
  check, not an owner account mutation.
- Independent backend review found no blocking authority, transaction or replay
  issue. No old credential or proof is made current by this operation.

## Verification and remaining boundary

- Broader real registry/HTTP plus exhaustive OpenAPI negative-policy checks:
  **38 passed in 207.53 seconds**. Mypy checked 739 sources with no issues.
- First UI run reached `billing_reconnect_reconcile` and found the success
  message being cleared before refreshed metadata arrived. Preserving it until
  a later real transition back to disconnected corrected the behavior.
- Canonical built-browser Green completed about 07:15:20 UTC, exit 0:
  `--lane browser --check owner_pool_controls`. It covers actual archive/restore,
  offline uncertainty and explicit status reconciliation without automatic retry,
  same-resource/scope reconnect, monitoring off, reload/setup recovery, disabled
  Check without a credential, and rejection while archived. Existing pool,
  organization pagination and sorting scenarios also passed. TypeScript and
  the production build passed with the compatible 101-operation client.
- Planning synchronization, 16-ticket M7 traceability and documentation checks
  passed. Installed verification and publication are recorded after cutover.
- `AUTO-QUALITY` passed at 07:15:55 UTC: 800 formatted files, 739 mypy sources,
  zero boundary violations, compatible 101-operation API, TypeScript and actual
  production build. Canonical `--lane registry_metadata`: **62 passed in
  38.59 seconds**, including the new reconnect cases.

The new real registry/HTTP tests are included in the existing canonical
`auto_m7 --lane registry_metadata`. The expanded built-browser test uses the
existing `--lane browser --check owner_pool_controls`. Installed setup probes
check the additive route/schema without changing owner records.

Actual owner key replacement/deletion, disconnect cleanup and monetary-history
comparisons remain separate outstanding cases. Pending metadata is not a stored
secret or fabricated provider identity. No owner account, credential, provider
profile, running agent or provider data was modified by these isolated tests.
Full provider coverage, monetary flow, analysis and final M7 exit remain open.

Changed areas: registry_billing_v1 contract; M02 billing_connections repository;
P01 registry schema/router and explicit OpenAPI policy; generated contract/client;
P02 billing control/client/panel; real registry/HTTP/browser tests and existing
canonical runner; module handoff, UI behavior and operational documentation.

## Installed and public verification

Implementation `c1c8e8d553f1fdf99ade9d3b0f8e96daa75fb437` was installed with the
existing selected-revision updater; candidate readiness passed and original
restart policy was restored. No migration or owner configuration mutation.
The service was active and the dashboard returned HTTP 200.

At 07:19:42.475 UTC the existing concurrent installed browser probe passed
Overview, setup (including the reconnect route/schema) and cloud controls at
that exact implementation revision, with zero mutation requests. The actual
reconnect button journey was exercised on isolated real registry/HTTP/browser
boundaries; the installed read-only probe did not archive an owner's account.

GitHub push completed and independent `git ls-remote github refs/heads/main`
confirmed the exact implementation hash. The staged secret scan reported two
findings, both verified old/new generated OpenAPI SHA-256 identifiers, with zero
unresolved findings. No suppressions were added. This documentation-only receipt
does not change the installed implementation revision.
