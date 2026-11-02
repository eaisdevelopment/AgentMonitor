# M6 Ollama cloud balance contract — development evidence

Scope: M6-T011/M6-A04/A09, A03 contract version `OLLAMA-CLOUD-BALANCE-V1`
1.0.0 and existing M05 `CTR-CAP-001` projection. The new pure contract keeps
included and purchased USD balances, legacy percentages, UTC resets and source
period separate. Unknown values remain unknown. The period accompanies the
projection because the current capacity-window contract does not retain its
start; durable period fidelity is still unfinished.

Red: pure contract tests failed because the contract module did not exist.
After the first implementation, two tests exposed a false-exhaustion risk:
credit pools were independently marked constraining. They were corrected and
both monetary pools now remain non-constraining until their combined semantics
are supported. Legacy session/week windows remain constraining. The Ollama
[balance API](https://docs.ollama.com/api/balance) describes period endpoints
and provider variants; no example response was replayed or used as a fixture.

Green after formatting: 63 pure contract, capacity and collection-control tests
passed; Ruff passed for the new contract and test. No dependency, schema
migration, key, provider profile, live account or provider request was added.
This is not cloud collection or M6 completion. Live provider comparison,
credit exhaustion semantics, period persistence, history, alerts, API/UI and
sharing provenance remain open.

The official balance endpoint returned HTTP 401 to an anonymous read-only
request on 2 November 2026; no credentials or response body were captured.
The new pure status classifier distinguishes success, unauthorized, denied,
rate-limited, unavailable and unexpected responses. Its test failed before
the classifier existed and passes after implementation; Ruff and mypy pass.
This does not verify an authenticated account or other live response codes.

## Fixed HTTPS source increment

Scope: `M6-T005`, `M6-T011`, `M6-A04`, `M6-A09`; source
`ollama.cloud.balance.v1`; existing contract `OLLAMA-CLOUD-BALANCE-V1`.

Red at `2026-11-02T15:31Z`:

```text
uv run --project backend pytest -q \
  backend/tests/adapters/providers/ollama/test_cloud_balance_source_policy.py \
  backend/tests/adapters/providers/ollama/live/test_cloud_balance_endpoint.py
```

Collection failed with two `ModuleNotFoundError` errors because
`agentmonitor.adapters.providers.ollama.cloud_balance.source` did not exist.
The minimum implementation fixes the destination to one TLS-verified
`GET https://ollama.com/api/balance`, performs no redirect, retry, proxy,
query or request body, enforces finite connect/read/operation and response
bounds, does not read non-success bodies, and emits only closed sanitized
outcomes. The documented modern and legacy response variants are parsed with
exact `Decimal` values, duplicate-key rejection, closed fields and UTC times.
The source accepts an opaque private authorization-header applicator, never a
raw key value or configurable destination.

Green at `2026-11-02T15:41:18Z`:

```text
uv run --project backend pytest -q \
  backend/tests/contracts/pure/test_ollama_cloud_balance_v1.py \
  backend/tests/adapters/providers/ollama/test_cloud_balance_status.py \
  backend/tests/adapters/providers/ollama/test_cloud_balance_source_policy.py \
  backend/tests/adapters/providers/ollama/live/test_cloud_balance_endpoint.py
```

Result: `12 passed in 0.75s`. The live test used the production source for one
anonymous request to the fixed official endpoint and observed HTTP 401 as
`unauthorized`; it did not provide a credential or read/capture the response
body. No keyring, provider profile, application service or database was read
or changed.

An authenticated HTTP 200 response, current provider-payload compatibility,
native amount reconciliation, natural 403/429/timeout behavior and account or
team scope remain **Not Run** until the owner provisions a real key through the
approved private credential boundary. No provider JSON or credential was
fabricated for a test. The Ollama manifest remains unchanged and therefore
does not claim this cloud capability is admitted. The standard-library socket
timeout bounds connection and reads, and a monotonic whole-operation budget is
rechecked between operations; Python's system DNS resolution does not provide
a separately cancellable hard deadline, so no stronger wall-clock claim is
made. Contract-baseline/adoption registration and end-to-end credential,
scheduler, persistence, API and UI integration remain separate work.

Changed-file Ruff lint/format and strict mypy passed for the source and tests;
`AUTO-DOCS-CHECK` passed 259 Markdown files and `git diff --check` passed.
The broader `AUTO-QUALITY` command did **not** pass in this isolated worktree:
it stopped at `minimum_m1_local_control_failed` because the installed frontend
inventory was unavailable/mismatched (`verify_frontend_inputs() == False`),
while its backend input check passed. No package installation or lockfile
change was made. The independent boundary checker also remains red with nine
repository findings. For this increment the directly relevant findings are
the pre-existing undeclared `OLLAMA-CLOUD-BALANCE-V1` dependency on
`CTR-COMMON-003` and the resulting unresolved contract symbol at the new
source import. Contract baseline/adoption registration is an integration
prerequisite; these red gates are not reported as passed.

## Security-review correction

Independent review of the first HTTPS-source commit found that parser
exception chains could retain raw input, authorization failure codes were only
statically rather than runtime constrained, a valid long `Retry-After` was
discarded above an invented one-year cap, `SSLKEYLOGFILE` could enable TLS key
logging, and the authorization callback had the full mutable HTTP connection.
It also found that the Python resolver and `http.client` header parser do not
enforce the advertised absolute operation and wire-header limits. The real
network test was under the local-only adapter test tree even though the local
admission selector must not gain an Ollama cloud dependency.

The pure security Red was:

```text
uv run --project backend pytest -q \
  backend/tests/adapters/providers/ollama/test_cloud_balance_source_security.py
```

Result: five failures and one pass. Invalid JSON raised an exception chained
to `JSONDecodeError`; an excessive Decimal exponent escaped as
`InvalidOperation`; an arbitrary authorization failure code was accepted; a
valid 31,536,001-second retry wait became absent; and `2**63` seconds did not
fail closed. A separate TLS subprocess test failed because the secure context
helper did not exist. The authenticated-source fail-closed Red returned
`deadline_exceeded` instead of `source_not_admitted`.

The correction now returns a typed parse value or stable failure code after
raw parser frames unwind, catches Decimal conversion failure, validates the
two authorization-store codes at runtime, retains every decimal-seconds retry
through `2**63 - 1`, and maps a larger syntactically valid value to explicit
`ollama_cloud_retry_after_unrepresentable`. Malformed or absent retry advice
remains distinguishable and fallback-eligible. TLS uses a client context with
the platform trust store and explicitly disabled key logging; a real local
subprocess proves an `SSLKEYLOGFILE` request creates no keylog. The resolved
credential grant receives only a one-shot bounded bearer sink, never the HTTP
connection. The sink clears its caller-owned byte buffer, and HTTP debugging
is forced off immediately before sending. This is not a reliable Python-memory
zeroization claim.

Authenticated collection now returns
`ollama_cloud_authenticated_source_not_admitted` before authorization or
network I/O. Its policy explicitly records that strict whole-operation DNS,
authorization-callback and wire-header ingress guarantees are not established;
the manifest remains unadmitted. The post-parse header acceptance limit and
socket timeouts remain defense in depth, not the missing strict proof. The
anonymous official-endpoint probe remains available solely as admission
evidence, and its real test moved to
`backend/tests/live/ollama/test_cloud_balance_endpoint.py`, outside the
local-only adapter selector. Authenticated 200 and credential containment at a
real runtime boundary remain **Not Run**.

Final focused Green at `2026-11-02T15:56:28Z` ran the balance contract, status,
source-policy, source-security and moved real anonymous endpoint tests: `20
passed in 1.36s`. The real boundary again observed sanitized HTTP 401. No
credential, keyring item, provider profile, authenticated response body or
application service was accessed.
