# M6 Ollama credential-update contention — candidate evidence

- Scope: `M6-A03`, `M6-A04`, `M6-A09`, `M6-A10`; M02/M03/M04/P01/P02
- Contracts: `CTR-REG-012` 1.1.0, `CTR-PROV-003` 1.1.0,
  `CTR-COL-008` 1.1.0 and `CTR-COL-009` 1.1.0
- Schema: unshipped candidate `v1_0712`; installed schema remains `v1_0707`
- Date: 2 November 2026

## Behavior

Bounded local credential-update lock contention is recorded as the closed
no-request reason `credential_update_in_progress`. It retains exact
`not_started` certainty, consumes no provider response, preserves scheduled
admission, and is presented as “Another account update is in progress”. A
missing or inaccessible credential remains a separate authorization-unavailable
state. The existing candidate `.env` parent directory is group-writable; that
observed residual is unchanged by this slice.

## Red and green evidence

The focused pure command covered the no-response contract, adapter mapping,
latest-signal classification, connection status and scheduled-source admission:

```text
backend/.venv/bin/pytest -q \
  backend/tests/collection_control/domain/test_cloud_no_response_v2.py \
  backend/tests/adapters/providers/ollama/test_cloud_collection_target.py \
  backend/tests/collection_control/domain/test_ollama_latest_source_signal.py \
  backend/tests/registry/domain/test_cloud_connection_status.py \
  backend/tests/provider_system/test_scheduled_source_admission.py
```

Before production changes the command failed in the five new behaviors with
`5 failed, 61 passed`: the reason was rejected by the no-response contract,
the source mapper did not exist, the latest-signal classifier rejected the
reason, status collapsed to pending, and scheduled lineage rejected the signal.
After the implementation it returned `66 passed`.

The OpenAPI/client pair was regenerated from the exact `github/main` baseline.
That public baseline contains no Ollama cloud connection endpoint, so the
amended unshipped V1 candidate is compatible; the generation receipt reported
`compatibility='compatible'` and 74 operations.

`AUTO-DOCS-CHECK` passed. `AUTO-PLAN-CHECK` accepted the contract versions,
adoption and snapshot mechanics, then remained red only because the final
independent readiness audit and cross-plan synchronization review do not bind
the new snapshot. Those two independent-review bindings were not rewritten by
this implementation.

## Limits and impact

No `.env` contents, credential, provider profile or provider response was read.
No provider request, live database mutation, service restart or browser action
was performed. Natural credential-lock contention, populated migration,
provider/API/browser behavior and the canonical M6 completion gate remain Not
Run. The forward-only v1_0712 checksum/catalog binding changes because the
candidate revision is unshipped; no published or installed schema is rewritten.
There are no dependency or licence changes.
