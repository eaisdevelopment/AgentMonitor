# M4 ST-FLEET-001 — interim registry and dashboard handoff

- Evidence ID: `M4-ST-FLEET-001-INTERIM-2026-09-25`
- Outcome: **Partial**. The admin registry and one real Claude health observation are usable; six-account reconciliation and the M4 exit gate remain **Blocked/Not Run**.
- Authority: the owner approved implementation of `ST-FLEET-001` in this session. The A01 `CLA-I09` managed reauthentication packet has not been approved.
- Requirements: `FR-ORG-001/002`, `FR-ACC-001/002/003/005/006`, `FR-AUTH-001/004/005`, `FR-SAFE-001/002`; partial `AC-LIVE-001`, `AC-UI-002/005`, `AC-TEST-001/003/004/006` evidence only.
- Contracts: additive `registry.v1` (`CTR-REG-001/002/005/007`), `identity_access.v1` (`write:accounts`), `CTR-API-001`, `CTR-UI-001`, and generated V1 OpenAPI/client (39 operations). No breaking public change or migration.
- Checkout: uncommitted shared worktree, 2026-09-25. Preserve all existing user changes.

## 2026-09-28 delivery update

The recovered admin work was committed as `2a03ee6` on `codex/v1-m2`.
The seven real admin HTTP tests and both built admin browser scenarios passed
again. The historical stale-quota observation below was superseded by
[automatic Claude polling](claude-dashboard-polling.md), which saved fresh
real quota while retaining the account and SDK assignment. Six-profile
enrollment and managed reauthentication remain separate scope.

## Delivered behavior

The authenticated dashboard has organization create, list, rename, reorder, archive, and restore, plus account pending registration, list, detail, rename, organization assignment, monitoring preference, archive, and restore. Names and provider keys are entered through admin CRUD; no owner email or account is hardcoded. A new account remains pending and cannot be monitored until provider identity, compatible profile, and resource are verified. Archive preserves history. The UI consumes only the generated V1 API through the shared wrapper.

The backend uses file-backed SQLite transactions, registry revisions, optimistic resource versions, idempotency receipts, safe changes, and the existing outbox. `write:accounts` is an additive M01 scope; P01 enforces authenticated authorization, CSRF for browser writes, and `If-Match` for edits. M02 remains the registry owner. Claude authentication health uses one bounded, read-only installed-provider observation and leaves the default profile untouched. The reauthentication module returns an unavailable decision before provider I/O without the separately approved packet.

## Test inventory and status

| Scenario | Real boundary | Status and evidence |
|---|---|---|
| Account and organization admin API | Uvicorn loopback, authenticated requests, file-backed SQLite | **Passed**: `backend/.venv/bin/python -m pytest backend/tests/integration/api/test_account_admin_routes.py backend/tests/integration/api/test_organization_routes.py -q` → `7 passed in 8.16s` on 2026-09-25. |
| Account and organization admin UI | Production frontend build, real Chrome, authenticated loopback service, file-backed SQLite | **Passed** in the interrupted session: `backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py accounts_admin` and `... organizations`. |
| Static/contract quality | Real checkout, generated OpenAPI/client, typecheck/build, module boundaries | **Passed** in the interrupted session: `backend/.venv/bin/python tools/automation/run.py AUTO-QUALITY`; 39 operations. |
| Claude authentication health | Installed Claude, bounded read-only `/usage` source | **Passed observation** on 2026-09-25: sanitized result `state=success`, `observed_auth=healthy`. Identity comparison remains unresolved. The broad live test command returned `2 passed in 8.66s`; that test result alone does not imply a healthy provider result. |
| Six intended Claude identities and organization membership | Six separate owner-controlled real profiles | **Blocked**: the owner has not yet identified six available distinct profiles and confirmed their identities through the live runbook. The one-account test is narrower. |
| Managed Claude reauthentication | Official owner-driven flow on an AgentMonitor-managed isolated profile | **Blocked** by A01 `CLA-I09` approval and suitable managed profile. Default-profile rejection before I/O is covered; no live reauthentication is claimed. |
| Owner's active dashboard | Existing local owner data root, authenticated loopback production service | **Partial, observed**: the service served `/accounts` with HTTP 200; the owner signed in, saw `Enable monitoring`, clicked it, and reported the control changed to `Disable monitoring`. A read-only M02 repository query then returned one active owner-confirmed Claude account with `monitoring_preference=enabled`, `is_effective_monitoring_enabled=True`, and reason `eligible`. |
| Owner organization CRUD | Authenticated browser mutation and M02 repository readback on owner data root | **Passed for create/list**: the owner created SDK and EAIS through the Organizations page and reported both visible. M02 initially returned both as active with zero active accounts. Rename/reorder/archive/restore are covered by isolated real-browser/API scenarios, not by owner-data mutation. |
| Owner account assignment | Authenticated browser mutation and M02 repository readback on owner data root | **Passed**: the owner assigned the existing Claude account to SDK. M02 readback returned SDK with one active account and EAIS with zero; the Claude account retained `monitoring_preference=enabled` and effective eligibility. The identity field remained withheld, so this is an owner-supplied organization relationship, not provider-proven email identity. |
| Claude quota after monitoring preference change | Existing M05 account observation query against the owner database | **Stale**: two quota windows were present, both `stale` as of the check; latest collection timestamp was 2026-09-25 09:56:18 UTC. The preference write did not create a new observation. |

## Red, Green, and refactor evidence

The interrupted session recorded behavioral Red responses: account creation initially returned 405, organization list/create/rename/reorder and account monitoring initially returned 404, and the built-browser account scenario failed when the provider field was missing. The built-browser organization scenario failed when rename and reorder controls were missing. Minimum API/UI implementations made the exact account and organization scenarios Green. These prior Reds are session evidence; no separate timestamped terminal artifact was retained, so universal `AC-TEST-001` is not claimed. The final admin API rerun above and prior `AUTO-QUALITY` form current refactor checks.

The owner then surfaced confusing identity copy on the real account page. A new assertion in `accounts_admin.mjs` failed in the built Chrome scenario at `account_edit`, waiting for `Withheld from dashboard` (30-second timeout). The account view now labels withheld identity plainly and says that names and organization assignments are administrator managed. The same real-browser command passed after the production build (`P02 BROWSER: PASSED — accounts_admin`). This wording does not claim that the provider supplied an email or verified the owner-entered group.

An earlier Claude live run failed its real `/usage` call with `deadline_exceeded` / `usage_deadline_after_command_echo`; the subsequent 2026-09-25 observation succeeded. That earlier failure remains part of the history and does not prove six-profile reliability.

## Impact and limits

- Security/privacy: no credentials, prompts, responses, provider payloads, or account email addresses are stored in this evidence or entered into source. The default Claude profile was read only. Dashboard admin login remains owner-controlled.
- Database/migration: no new schema revision; the change uses existing M02 tables. Archive is reversible, and rollback is the prior application build against the same schema after a normal service stop/start.
- Dependency/license: no new third-party dependency. The new root `pyproject.toml` declares no dependencies.
- Documentation: this record and the M02/P02 module notes describe current bounded behavior; older M2/M3 evidence remains historical.
- Remaining defects/risks: pending accounts have no dashboard flow to bind a newly confirmed provider identity; only the already confirmed Claude account can be enabled now. The owner enabled its preference, but its two quota windows remained stale; continuous collection is not scheduled by this mutation. Organization ordering history does not retain before/after numeric positions. The six-account live gate and the canonical M4 exit gate are absent or not passing. Do not claim `ST-FLEET-001` complete.

## Next integration step

The owner created SDK and EAIS and assigned the existing confirmed Claude account to SDK in the loopback dashboard. Continue `ST-FLEET-001` with an approved identity-confirmation flow for pending records and the owner-controlled six-account live matrix. A separate approved collection increment must wire eligible accounts to fresh quota runs. Add and execute a fail-closed M4 completion command before any completion claim.
