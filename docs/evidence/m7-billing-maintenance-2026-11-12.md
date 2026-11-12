# M7 local billing disconnect and cleanup

Status: implementation and bounded verification in progress under approved
focused plan 1.1.0. T002/T011, FR-ACC-001/004/006, FR-BUDGET-006;
M7-A01/A09, AC-UI-005/006, AC-TEST-001/003/006. M02 owns registry revocation;
composition owns local credential-file use; P01/P02 publish safe instructions.
This is an increment, not full M7 or genuine stored-key lifecycle acceptance.

## Boundary and behavior

CTR-REG-014 1.8.0 publishes the locked M02 disconnect operation and optional
local-maintenance descriptor on the existing billing-status GET. No HTTP writer,
job, migration, dependency, secret field or provider mutation is added. The
existing installed local operator accepts explicit store/disconnect/cleanup;
omitting the action retains its previous key-entry behavior.

Disconnect validates the account/resource/provider, captured versions and live
account/root lock. One SQLite transaction retires pending/active credential
bindings and sets billing disconnected/disabled. Even a connection with no key
is disconnected. Repeated disconnected requests do not advance generations.
Scope, pool association, resource and financial history stay intact. Archive
reuses the same retirement mechanics with its original account_archived reason.

The runtime retains the lock while removing only recorded retired entries from
the selected protected managed file. It checks file selection before each write
and before marking cleanup complete. A failure never restores access; cleanup
remains outstanding. Cleanup works after account archive and cannot prepare,
activate or disconnect a current key. The operator pins the database file
identity before target/label reads and rejects a replacement across its checks.
This prevents identical copied registry metadata from inheriting the selection.

The dashboard provides compact host-labelled, selectable/copyable commands and
states that copying does not execute them. No manual account IDs or additional
attestation. These actions disconnect AgentMonitor; they do not revoke a key at
the provider or touch a default provider profile. The existing reconnect action
returns a disconnected resource to setup without restoring old credentials.

## Red and bounded evidence

- M02 real SQLite Red: 14 tests failed because disconnect_billing_locked was
  absent. Green: **24 passed in 19.55 seconds**, including prior archive/binding
  and reconnect tests. Cases cover pending/no-binding, stale versions, pool and
  scope preservation, wrong resource/provider, root/account/expired lock,
  archived refusal, repeated action and retained caller lock.
- Local command Red: explicit maintenance action formatting was absent and the
  actual operator help lacked action choices. Real HTTP Red:
  `billing_local_maintenance_missing` on the existing billing-status response.
  The combined command/operator/HTTP Green passed **12 tests in 10 seconds**.
- Real PTY/operator Red: `billing_disconnect_runtime_missing`; the selected
  maintenance entry point did not exist. Genuine empty protected files and real
  pending metadata then exercised an actual unsafe-permission write failure:
  authority was retired first, cleanup stayed outstanding, corrected permissions
  permitted retry, and scope/history authority stayed unchanged. Both providers,
  archived cleanup and repeated operations passed. No fake key was inserted or
  marked active. Legacy billing enrollment guards also passed.
- Review found ambiguous upstream-revocation wording; it now explicitly says
  AgentMonitor billing disconnected. Review also identified missing database
  identity pinning across reads. An actual SQLite backup replacement preserving
  identical metadata now fails the pinned check. The five local-maintenance
  cases passed in **11.03 seconds** after their Red.
- Built-browser Red: `billing_local_disconnect` after the actual production
  build, before the maintenance UI existed. Its initial Green attempt reached
  archived cleanup but the probe inspected the outer disclosure before account
  hydration. Waiting for actual account controls corrected the probe; unchanged
  production then passed the canonical owner_pool_controls check, including
  real clipboard permission denial, selectable commands, archived cleanup-only
  instructions and zero browser mutation requests from these controls.
- Installed read-only Red at 07:42:39.516 UTC on `c1c8e8d`:
  `billing_maintenance_contract_missing`; existing authentication, Overview,
  setup and account layout passed. Zero mutation requests.

## Verification scope and remaining work

The existing canonical registry_metadata selector now includes the disconnect,
PTY/empty-file maintenance, enrollment guards, command formatting and actual
operator refusal/help tests. The existing owner_pool_controls browser selector
uses real isolated registry/IAM/HTTP and built Chrome. A real pending binding
is archived before the browser test to exercise cleanup-required metadata; it
does not contain a credential, provider identity, access proof or financial data.

The status-to-financial refresh review found an integration gap after local
actions. Behavioral Red was `billing_status_financial_refresh`: changing actual
scope metadata outside the page then refreshing status did not reread financial
state. P02 now compares successful status authority and refreshes financial data
after a change, explicit refresh or native focus return. Failed status reads
retain the prior facts. Canonical `auto_m7 --lane browser --check
owner_pool_controls` passed after the correction, including real external scope
PUTs, exact new summary/scope rendering and an offline failure with zero new
financial requests. The probe's ambiguous scope locator was narrowed; Playwright's
always-focused override was disabled on its two isolated pages so actual
`bringToFront`/`hasFocus` transitions supplied the native focus event. No synthetic
focus event or provider response was used. This metadata scenario does not prove
populated monetary retention.

Final local `AUTO-QUALITY` passed: 802 formatted files, strict typing of 741
source files, zero import-boundary violations, 101 compatible OpenAPI operations,
generated client/typecheck and production build. This is the canonical local
quality scope; hosted/live/platform and release-wide scans are not implied.
The expanded canonical `auto_m7 --lane registry_metadata` passed **95 tests in
74.10 seconds**, with zero skips. Documentation checks passed across 396 Markdown
files; M7 traceability and synchronized planning passed. Installed verification
remains a separate next step on a clean committed candidate.

Genuine active-key replacement/deletion, provider
access and populated monetary reconciliation remain separately unproved until
owner-supplied billing credentials are available. No owner configuration or
running agent was changed for these isolated tests.

Changed areas: CTR-REG-014; M02 credential bindings and tests; local operator,
enrollment/cleanup and command descriptor; registry HTTP schema/GET and generated
client; account maintenance UI; canonical registry/browser/probe selectors;
module handoff, operations and evidence. No schema, license or dependency change.
