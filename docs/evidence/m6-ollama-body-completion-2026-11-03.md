# M6 Ollama complete-response correction

## Failure and ownership

M03's cloud balance transport received HTTP 200 on the real owner-authorized
connection check but reported `provider_unavailable`. A bounded diagnostic of
the existing queued M04 verification printed only the typed source state,
HTTP status and dispatch certainty: `provider_unavailable`, `200`, and
`response_received`. The request used the existing credential binding and
durable admission gate. No response body or credential was printed.

The body loop attempted to configure another socket read after receiving all
Content-Length bytes. Python's HTTPResponse closes its stream on that final
read; with Connection: close there is no socket left for the next iteration.
This produced `ollama_cloud_transport_unavailable` despite a complete response.
The earlier provider-unavailable result did not establish an upstream outage.

## Red and green

`backend/tests/live/ollama/test_balance_body_completion.py` calls the actual
installed Ollama daemon at its existing loopback `/api/version` endpoint and
passes its real response through the production bounded-header and body reader.
Before the fix it failed at `_set_socket_timeout` with
`OSError: ollama_cloud_transport_unavailable`. No HTTP fixture, replay, fake
server, credential, or fabricated provider data was used.

The reader now stops when the declared body length has been received. The
existing exact-length check still rejects premature EOF; unknown-length and
chunked bodies keep their EOF loop and size limit. The regression plus source
security, policy and status tests passed: **12 passed**. Ruff and diff checks
passed. Independent source review confirmed the EOF mechanism and checked the
zero-length, incomplete, unknown-length and chunked branches by inspection.

Command (repository root, developer environment):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend/src backend/.venv/bin/python -B -m pytest -q --tb=short backend/tests/live/ollama/test_balance_body_completion.py backend/tests/adapters/providers/ollama/test_cloud_balance_source_security.py backend/tests/adapters/providers/ollama/test_cloud_balance_source_policy.py backend/tests/adapters/providers/ollama/test_cloud_balance_status.py
```

The cloud mechanism version advances from 1.0.4 to 1.0.5, changing its source
fingerprint so earlier verification receipts cannot authorize the corrected
mechanism. The provenance test first failed on 1.0.4 before this update.
Source ID, public API, payload schema and database schema are unchanged.

## Scope and remaining verification

Requirements: FR-QUOTA-001/002, FR-COL-003..008; M6-A04/A07/A09.
Affected source: `ollama.cloud.balance.v1`, mechanism 1.0.5;
`OLLAMA-CLOUD-BALANCE-V1` and `ProviderQuotaInputV2@2` remain unchanged.
Changes are confined to the M03 reader/provenance, their tests, and this record.
No dependency, license, migration, provider-profile or credential-format change.
No running user agent was interrupted. The diagnostic used existing owner
authorization and did not request key re-entry.

Deployment, actual authenticated cloud balance, dashboard history and the full
M6 completion command remain to be verified after this change. The local
daemon regression is not itself proof of a successful cloud balance.
