# M7 billing monitoring HTTP boundary

Status: partial T007/T011 implementation under approved focused plan 1.1.0,
M7-A01/A07/A09. P01 consumes CTR-REG-014 1.4.0; root owns composition,
dependencies/bootstrap, contract registration and client generation. This
increment is not successful provider verification or a full monitoring claim.

## API

GET and PUT `/api/v1/accounts/{account_id}/billing-connections/{resource_id}/monitoring`
are `billing_get_monitoring_v1` and `billing_set_monitoring_v1`.

GET uses standard `read:telemetry` cookie-or-bearer policy and returns the flat
`BillingMonitoringStatusV1`: account/resource IDs, account/connection versions,
scope/binding generations, preference/lifecycle, enable/disable eligibility,
closed reason and optional verification run/time. No binding ID, credential,
location or secret value is exposed. No composite ETag is manufactured.

PUT is cookie-administrator `write:accounts` plus CSRF, account `If-Match` and
required bounded `Idempotency-Key`. `SetBillingMonitoringInputV1` forbids extra
fields and accepts only strict positive version/generation integers, nullable
binding generation, enabled/disabled preference and nullable verification run
ID. It rejects enabling without both a verification run and binding generation
with a closed 409; missing values cannot reach a mutation. Disabling does not
require provider proof. Root composition resolves genuine proof and M02 applies
its transaction fences; this handler never treats submitted IDs as proof.

`BillingMonitoringResultV1` contains only the actual updated account/resource,
connection version, scope generation, preference/lifecycle, registry revision
and update time. Both success responses are no-store. Closed known version
conflicts map to 412, stale authority/proof/idempotency to 409, absence to 404 and
unknown failures to 503. Internal proof-required/conflict/timestamp codes map to
existing public monitoring reasons; arbitrary exception text is never returned.

## Red/Green

Real HTTP Red: **1 failed in 1.93s**, absent GET returned 404 instead of 401.
An intermediate integration regression found M02's in-progress edit had split
its `_get` function: existing and new billing routes returned absence. The owning
agent corrected that defect; it is not counted as a P01 feature Red.

A separate pure error-mapping Red showed a recognized proof conflict incorrectly
mapped to 503: **1 failed, 1 passed in 2.96s**. The bounded mapping now produces
safe 409 responses.

Final focused selection: **6 passed in 9.63s**:

```text
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -q backend/tests/integration/api/test_billing_monitoring_http.py backend/tests/integration/api/test_billing_actions_http.py backend/tests/integration/api/test_billing_enrollment_http.py
```

The new real HTTP test uses actual migrated SQLite, actual IAM bootstrap/session,
real loopback server, and administrative account/connection creation through the
real API. It creates no provider account/credential/report/telemetry. It checks:

- unauthenticated denial; missing CSRF, precondition and idempotency key;
- real missing-credential status with false enable/disable eligibility;
- strict input, extra-field and query rejection;
- missing target and enable-without-proof refusal;
- stale account/connection/scope versions;
- credential-free disabling of an actual pending connection without promoting it;
- idempotent replay and conflicting reuse of the operation key.

Scoped Ruff, formatting and strict mypy on the three production files and test
passed; whitespace checks passed. No assertions were removed and no mocks,
provider recordings, synthetic reports or positive proof substitutes were used.

**Not Run:** enablement from genuine complete provider evidence, populated
binding-rotation race through HTTP, positive bearer-token read, installed
monitoring/scheduler continuity and browser journey. Shared authentication policy
is reused, but unexecuted paths are not claimed as new live proof.

## Files and impact

- `backend/src/agentmonitor/api/v1/routers/billing_actions.py`
- `backend/src/agentmonitor/api/v1/schemas/billing_actions.py`
- `backend/src/agentmonitor/api/problem.py`
- `backend/tests/integration/api/test_billing_monitoring_http.py`
- This evidence record.

No schemas/migrations, dependencies or licenses changed. No installed service,
owner accounts/keys/default profiles or running agents were configured. No live
activation or commit occurred. No tool-helper window was used or retained.
