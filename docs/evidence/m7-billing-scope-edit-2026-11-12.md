# M7 billing scope editing

Status: local T002/T010/T011 increment under approved focused plan 1.1.0.
Local verification passed; installation/publication remain pending until
recorded below. M7 remains open; this increment does not close these
broader tickets. Owners: M02 registry, P01 transport, P02 rendering; root integrates.

Requirements: FR-ACC-001/002/004/006, FR-BUDGET-001/006, FR-ORG-003;
acceptance AC-UI-002/005/006, AC-TEST-001/003/006, M7-A01/A07.
Scenario families: M7-REG-001..004 and existing M7-UI owner controls.

## Behavior and boundaries

CTR-REG-014 1.6.0 adds ChangeBillingScopeCommandV1 and the existing billing
port's change_scope operation. P01 exposes authenticated PUT
`/api/v1/accounts/{account_id}/billing-connections/{resource_id}/scope`.
Explicit nullable scope, expected account/scope generation, connection If-Match,
idempotency, write:accounts and browser CSRF are required. Extra fields are
rejected; omitted scope cannot silently clear an existing scope.

M02 runs one real SQLite transaction: check versions/lifecycle, use the existing
monitoring invalidation hook, advance scope generation, mark pending/disabled,
close the active pool membership without deleting its original scope/history,
and persist audit/outbox/replay receipt. Same-scope is a no-op; stale edits/replays
cannot restore an old scope. Null explicitly returns to unresolved scope.
No credential, account-group or M05 report mutation occurs. No new table/schema,
dependency/license or secret permission. Schema remains v1_0734.

P02 adds Change provider billing scope inside the existing account connection
panel. It explains monitoring stops, old pool unlinking and retained history.
No provider request follows automatically. Unknown outcomes block another save
until a billing-status read started under a newer refresh revision completes.
A successful mutation validates returned identity/generation/state. The account
financial panel invalidates retained current values across scope mutation;
ordinary same-context refresh still retains values with their original times.
Pool controls remount on scope generation so an already-open panel cannot keep
showing the old association after the server closed it.

## Red and bounded verification

- Real HTTP Red: PUT returned 404, failing
  `billing_scope_edit_must_be_available`. Production route/port/transaction then
  passed its actual HTTP and registry checks.
- Request-body Red: omitting scope returned 200 rather than required 422,
  failing `scope_edit_requires_explicit_scope_or_null`. A required nullable field
  fixes the distinction between explicit clearing and an incomplete request.
- Pure presentation Red: changing authority revision with unchanged account
  version returned true for retaining old current data. The authority revision
  now participates in financial-read identity. Pure Green passed.
- Built-browser Red: existing owner_pool_controls failed at
  `billing_scope_controls` before the control existed. Initial built Green
  covered save/reload and real browser offline failure.
- Strengthened built Red: `billing_scope_pool_refresh` reproduced an already-open
  pool panel retaining its old association after successful scope change.
  The scope-generation key is the minimal correction; no new query framework.
- Installed read-only Red on `edbe2fc`: verify_setup returned
  `billing_scope_contract_missing` at 06:15:56 UTC. Authentication, exact revision,
  Overview, setup and account layout passed; zero mutation requests. This is an
  installed-contract probe, not an owner account edit or provider verification.

The final focused real HTTP/registry run passed 38 tests, including explicit
null clearing and stale receipt replay. The actual pool
repository test verifies the closed membership retains its original scope and
version, replay conflicts cannot restore it, and reopening returns the new scope.
Pending accounts/groups/pools are real isolated AgentMonitor-owned metadata;
no fake provider identity, credential or financial telemetry is created.

## Commands, files and limitations

- Focused shared pytest, no-skip plugin: integration/api/test_billing_enrollment_http.py;
  integration/registry/test_financial_pools.py, test_billing_connections.py and
  test_billing_enrollment_guards.py under backend/tests.
- `node --experimental-strip-types frontend/tests/pure/financial-read-presentation.mjs`.
- Existing `auto_m7 --lane browser --check owner_pool_controls`: real production
  build, IAM/HTTP/SQLite and Chrome; includes scope save, actual pool removal,
  reload, browser offline outcome, status reconciliation, organization pagination
  and existing pool/sorting controls. No provider calls or owner reconfiguration.
- Existing `verify_setup.mjs <installed-40SHA>` now checks installed scope API
  contract and explicit required nullable body through authenticated OpenAPI.
  An installed route is not a live populated financial scope-change pass.

Files: registry contract/SQLite mutation; P01 router/input and generated API/client;
shared client and BillingScopeControls/BillingConnectionPanel; AccountPage,
BudgetAccountPanel and financialReadPresentation; focused real/pure/browser tests,
existing runner stage allowlist and installed setup probe; owning module plan,
M7 catalog/worksheet and the accompanying bounded planning consolidation.

Live monetary lineage after a real owner scope edit remains unverified while
administrative billing access is absent. Full disconnect/reconnect/rotation,
prior-scope report discovery, genuine monetary comparison and remaining M7 work
stay in the existing tickets. User configuration remains owner-controlled.
Rollback uses the existing compatible same-schema selected updater; the added
route does not change old consumers or delete retained history.

## Review correction and local Green

Independent review found that a pinned report could still offer Collect using
current authority merely because its resource ID matched. Extracting that
existing predicate preserved behavior; a pure old-report/new-scope case then
failed `true !== false`. Collection now requires the selected report to be in
current published evidence with matching account/resource/provider/scope ID and
generation. Otherwise the button is disabled with a historical/unconfirmed-scope
reason and the existing return-to-current action. Current report and funds-only
positive cases remain enabled subject to ordinary server eligibility. No
fabricated historical billing report was used; populated old-scope browser
verification remains dependent on genuine source data.

The strengthened owner_pool_controls browser passed after the scope-generation
pool refresh correction, including Refresh billing status recovery from an actual
offline save without a page reload. A final run follows the historical-selection
guard. Canonical M7 pure passed 737 backend policy tests and twelve presentation
suites. AUTO-QUALITY passed at 06:19 UTC: formatting/lint, 734-source type check,
module boundaries, generated-compatible OpenAPI/client (99 operations), locked
inputs and production build. Final browser build covers the later explanatory
wording. No full monetary/provider or milestone acceptance is claimed.

At 06:22 UTC a read-only installed metadata inventory again found zero
Anthropic/OpenAI billing connections, stored billing bindings or enabled billing
resources. It made no mutations and exposed no credentials or account labels.
This explains the missing monetary scope-transition observation; it does not
block scope-control implementation, isolated real metadata tests or deployment.


Final local built-browser owner_pool_controls passed at 06:24 UTC after all
production changes, including the historical-selection guard. The browser uses
actual isolated metadata/IAM/HTTP/SQLite and performs no provider work. This
passes that bounded metadata/UI selection, not the unavailable populated
historical-money journey. Final focused integration: 38 passed. Canonical pure:
737 backend tests plus twelve presentation suites passed. Planning, documentation,
synchronized baseline and git diff/preflight checks passed.
