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

The first candidate advanced the cloud mechanism from 1.0.4 to 1.0.5; its
provenance test first failed on 1.0.4 before that update. Subsequent independent
review classified this as unnecessary versioning: the correction honors the
existing complete-body semantics and changes no endpoint, parser/schema,
authentication, response limit, retry policy or worker protocol. The fingerprint
is a semantic-policy digest, not an executable hash. The corrected final
classification therefore retains mechanism 1.0.4 and its existing fingerprint.
No earlier successful verification receipt exists. Failed 1.0.5 attempts remain
historical; no receipt is rewritten or accepted for a different semantic policy.
Actual parser, protocol and policy changes still require versioning. Source ID,
public API, payload schema and database schema are unchanged by this fix.

## Scope and remaining verification

Requirements: FR-QUOTA-001/002, FR-COL-003..008; M6-A04/A07/A09.
Affected source: `ollama.cloud.balance.v1`, mechanism 1.0.4;
`OLLAMA-CLOUD-BALANCE-V1` and `ProviderQuotaInputV2@2` remain unchanged.
Changes are confined to the M03 reader/provenance, their tests, and this record.
No dependency, license, migration, provider-profile or credential-format change.
No running user agent was interrupted. The diagnostic used existing owner
authorization and did not request key re-entry.

Deployment, actual authenticated cloud balance, dashboard history and the full
M6 completion command remain to be verified after this change. The local
daemon regression is not itself proof of a successful cloud balance.

## Deployment and whole-scope check

`AUTO-M6-CURRENT-UPDATE` passed for `3807977`; the authenticated Operations API
reported that exact revision, and the dashboard remained HTTP 200. The cloud
connection POST then returned 503 before dispatch. Inspection found the M02
access-target reconciler rejects a changed source fingerprint for an existing
target; the required upgrade correction is separate from the body-reader fix.
No successful cloud reading is claimed at this point.

`AUTO-M6-EXIT` ran on `3807977` and retained
`.agentmonitor-local/m6-evidence/direct-3807977ab1288113b47d521f8be7b0d7c91f4181-44334151d9c3567f.json`.
M6-A01/A06/A08 passed; the other acceptance lanes remained Not Run. Local
admission, documentation and planning checks passed. Build failed on stale
generated provenance; quality failed on three test-formatting issues. The
generator was rerun through `tooling/foundation/openapi_client.py --write`:
the API schema digest and all 74 operations were unchanged, only generated
source/artifact digests changed. After formatting the three tests, canonical
`AUTO-BUILD` and `AUTO-QUALITY` both passed, including strict mypy on 501 source
files, boundary checks, TypeScript and production build. This repairs those
technical failures, not the remaining real M6 coverage.

## First real cloud success

After the conformance-classification correction, `AUTO-M6-CURRENT-UPDATE`
passed for `1e6eb7d`. The actual dashboard connection action returned 202;
the admitted verification used the existing owner-provided key and returned
`success`, HTTP 200, `response_received`, and a genuine M05 capacity commit.
The source observation was at **2026-11-03 09:29:43 UTC**. The account API and
real browser showed fresh included and purchased USD balances, the reported
included-credit reset, and “Ollama cloud access confirmed”. The connection API
subsequently reported `monitoring_state=scheduled`. Identity remains owner
asserted; endpoint access does not prove the account email or organization.

This proves the corrected cloud request, parsing and first persistence path.
It does not yet prove repeated automatic reads or provider-UI reconciliation.
The real browser exposed remaining UI defects: secondary allowance cards said
Unknown for available USD balances, history selected only the ratio metric,
and summary wording confused missing provider identity with missing quota.
Those defects are being corrected separately using this actual observation.
Repeated verification on an already verified binding also requires retaining
receipt history; no existing receipt has been deleted or replaced to bypass it.
