# M7 P01 explicit billing Check action

Status: partial T007 transport increment under focused plan 1.1.0 and root's
explicit P01 assignment. Requirements FR-BUDGET-001/006, M7-A09. This is admission
of one read-only collection job, not proof of provider access, connection success,
monitoring enablement or full M7 completion.

## Boundary

`POST /api/v1/accounts/{account_id}/billing-connections/{resource_id}/checks`
uses the published `BillingCheckPortV1.check` / `BillingCheckCommandV1`
(CTR-COL-002 2.2.0). Only authenticated browser administrators with
`write:accounts` and valid CSRF may use it. It requires account `If-Match` and a
bounded `Idempotency-Key`. Its closed JSON body accepts only strict integer
`expected_connection_version >= 1`; no key, secret, provider URL or arbitrary
operation is accepted. Unknown query parameters are rejected.

On admission/replay it returns HTTP 202 with actual run ID, state, outcome/error
codes and times. It does not label the account connected. The response is
`no-store, private`. Application errors are mapped through a closed allowlist;
unknown exception values never become public problem text. Root owns application
port/bootstrap/router wiring, safe problem catalog, generation and actual job
service. No provider, database or credential implementation is imported here.

## Evidence

Real HTTP Red, using actual migrated file SQLite, real administrator bootstrap,
real IAM session machinery and a real loopback Uvicorn socket: **1 failed in
2.02s**. The absent endpoint returned 404 instead of the expected authentication
401. No provider account, report, credential or queued job was fabricated.

Command:

```text
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -q backend/tests/integration/api/test_billing_actions_http.py
```

After root's actual mount/composition wiring, Green: **1 passed in 2.38s**.
The adjacent billing enrollment regression selection was **3 passed in 6.33s**.
Scoped Ruff, strict mypy on both new source files and diff whitespace checks
passed. The test covers unauthenticated
access, valid actual local administrator session, missing CSRF/precondition/key,
malformed precondition/key, strict body validation, forbidden extra key field,
unknown filters and a genuinely missing account/resource. It checks that no
budget run was created. Provider/account enrollment, credential access, successful
202 admission/replay, resource/version conflicts and live job execution are
**Not Run** by this increment. No mocks or provider replay payloads are used.

## Changes and impact

- `backend/src/agentmonitor/api/v1/routers/billing_actions.py`
- `backend/src/agentmonitor/api/v1/schemas/billing_actions.py`
- `backend/tests/integration/api/test_billing_actions_http.py`
- This evidence record.

Additive HTTP action only; no migration, dependency or license change. No owner
accounts, default profiles, installed service or credentials were inspected or
modified. No deployment or commit was performed. Full canonical M7 gate remains
outside this partial transport result.

## Durable run-status read increment

Under root's additional approved T007 assignment (M7-A01/A07/A09), added
`GET /api/v1/collection-runs/{run_id}/budget`, operation
`billing_get_run_status_v1`. `BudgetRunStatusV1` additively extends the Check
response fields with account/resource IDs and optional committed report ID.
The POST response remains unchanged. The GET uses the standard `read:telemetry`
cookie-or-bearer policy and no-store response; unknown query parameters fail.

`BillingCheckActionsV1.get_status` calls M04's real `get_run` and
`get_billing_target` ports. Missing/non-budget runs remain absent; captured
account/resource/provider identity must match the run before exposure. Reading
history does not require a currently active credential binding or scope
generation. An unavailable/corrupt boundary returns the existing closed 503;
missing/non-budget identifiers map to the existing closed 404. No provider call,
queue action or credential read occurs. The captured target is immutable, so its
separate read cannot replace the returned run's identity with current metadata.

Real HTTP Red: **1 failed, 1 deselected in 1.96s**; the missing GET returned 404
instead of authentication 401. Initial Green attempt was interrupted during
collection by an unrelated concurrent `BudgetReportInputV1` NameError in M05;
this setup error is not claimed as behavior evidence. Scoped Ruff and strict
mypy on all three changed production files passed.

Additional changed production file:
`backend/src/agentmonitor/composition/billing_actions.py` (`get_status` only).
Root owns the additive CTR-COL-002 2.2.0 port, shared API operation metadata and
client generation. Successful status projection for a genuine populated run,
non-budget populated selection and mismatched captured metadata are **Not Run**;
no seeded runs or mock ports were used to claim them.

After M05's owner corrected that import, real HTTP plus adjacent enrollment and
billing-command contract regression: **5 passed in 10.89s**:

```text
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -q backend/tests/integration/api/test_billing_actions_http.py backend/tests/integration/api/test_billing_enrollment_http.py backend/tests/contracts/test_billing_actions.py
```

This Green covers the actual unauthenticated GET, actual administrator session,
rejected query and real missing-run lookup. It does not turn the populated
status/provenance cases above into passed evidence.
