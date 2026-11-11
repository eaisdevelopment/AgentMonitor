# M7 account financial HTTP increment

Status: intermediate. T010 / M7-A07 is not complete.

## Scope and boundaries

- Requirements: FR-BUDGET-002 and FR-BUDGET-004; acceptance M7-A07.
- Owner: P01. Additive account current financial read; daily history, global
  grouped summaries, frontend integration and genuine monetary API acceptance
  remain separate work.
- Consume CTR-CAP-006 2.2.0 `AccountBudgetCurrentPortV1`, composed from current
  reports, registry metadata and collection state. Root owns its publication,
  composition and generated API/client outputs.
- GET performs no collection, credential access or provider request. Public
  money retains a string coefficient, integer scale and currency. Report source,
  range, scope, coverage and availability must remain explicit. Credential
  binding internals are excluded from wire projections.

## Red evidence

Command from the M7 worktree:

```sh
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -c backend/pyproject.toml backend/tests/integration/api/test_budget_http.py -q
```

Before new route/schema production code: **1 failed in 2.04s**.
`test_current_budget_authentication_and_filter_boundary` failed with:

```text
The current budget read must authenticate before account lookup; received HTTP 404
assert 404 == 401
```

This is an actual Uvicorn loopback HTTP request against a freshly migrated
temporary file-backed SQLite/IAM installation. It has no enrolled provider
accounts, reports, recorded payloads, telemetry seeds or network replacements.
The assertion demonstrates the missing operation. Later assertions retain the
missing-account and closed UTC/range/scope-filter behavior for Green.

Before the production route/schema were added, expanded verification returned
**3 failed in 3.37s**: the original unauthenticated 404; authenticated GET after
actual temporary account creation returned 404 instead of 200; pure projection
import failed because the new router module did not exist. Temporary account
metadata has no credential, provider identity or telemetry. The constructed
large-money value is confined to the pure projection test and never enters
HTTP, SQLite or provider adapters.

## Implementation and quality

The additive operation is `capacity_get_account_api_budget_v1` at
`GET /api/v1/accounts/{account_id}/api-capacity`. It requires `read:telemetry`
and explicit `period_start`, `period_end`, `as_of` UTC query values; rejects
unknown/duplicate parameters, non-UTC instants, inverted/empty intervals and
intervals ending after the pinned read instant. Scope epochs are resolved by
the application rather than accepted from the caller.

Closed response models preserve current/attempt report identities, exact cost
and usage buckets, source/basis/coverage/watermark, independent latest collection
state, and application-supplied spend. The mapper performs no arithmetic and
excludes report credential binding IDs/generations and run fencing/digest
internals. An empty successful metadata query is `available` with
`billing_not_configured`; this query status does not claim available financial
data. Configured resources without reports have unavailable report status and
no invented totals.

Scoped Ruff check/format, strict Mypy for both API source files and
`git diff --check` passed. Mypy uses `--explicit-package-bases` with
`MYPYPATH=backend/src`; the first invocation without that option stopped on
duplicate module-name discovery, before checking source. Pure report mapping
passed after implementation, preserving `9007199254740993123456789` at scale 9
without exposing binding fields. HTTP remained 404 until root router mounting.

## Green and remaining evidence

After root mounted/wired the operation, the same scoped command passed:
**3 passed in 3.89s**. Actual HTTP verifies unauthenticated 401, authenticated
missing-account 404, invalid filter 400, empty-account and configured-resource
200, cookie authentication, scoped bearer denial/permission, no-store responses
and no collection runs created by repeated GET. Empty configured reports remain
unavailable with no totals. The third test is pure projection, not monetary
HTTP evidence.

Root's preceding combined run reported 1 failed / 7 passed solely because the
test originally expected financial unavailability in the top-level query status.
That assertion was corrected to the published semantics: successful empty
metadata query is available / billing_not_configured, while each absent report
is unavailable. No production behavior was changed to satisfy that correction.

Authenticated monetary report mapping over HTTP: **Not Run**; requires a genuine
committed provider report. No empty result is reported as financial acceptance.
No dependency, migration, deployment or owner configuration changes in this P01
increment. Canonical T010/M7 closure is not claimed.

Owned files: `api/v1/schemas/budgets.py`, `api/v1/routers/budgets.py`,
`backend/tests/integration/api/test_budget_http.py` and this evidence. Root owns
the application port, composition, route mounting and generated artifacts.
