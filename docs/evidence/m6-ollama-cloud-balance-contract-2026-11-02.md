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

The first exploratory run had five failures and one pass, but two cases used
constructed provider-shaped JSON. Those two cases conflict with the project
rule against fabricated provider responses; they were removed and are **not
admissible evidence**. The admissible subset had three failures and one pass:
an arbitrary authorization failure code was accepted, a valid
31,536,001-second retry wait became absent, and `2**63` seconds did not fail
closed; malformed/absent retry advice already remained fallback eligible. A
separate real local TLS-context subprocess test failed because the secure
context helper did not exist. The authenticated-source fail-closed Red
returned `deadline_exceeded` instead of `source_not_admitted` without making a
network request.

Code review corrected the parser to return a typed value or stable failure
code after raw parser frames unwind and to sanitize Decimal conversion
failure. No fabricated response test is used to claim that behavior; real
authenticated parser compatibility remains Not Run. Admissible pure tests
prove that the two authorization-store codes are runtime constrained, every
decimal-seconds retry through `2**63 - 1` is retained, and a larger
syntactically valid value maps to explicit
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

The final focused Green below excludes the removed inadmissible parser cases.
It runs the balance contract, status, source-policy, admissible source-security
and moved real anonymous endpoint tests. The real boundary observes sanitized
HTTP 401. No credential, keyring item, provider profile, authenticated
response body or application service is accessed.

Final admissible focused Green at `2026-11-02T15:57:33Z`: `18 passed in
1.71s`.

## Enforceable anonymous-probe deadline

The next policy Red expected the anonymous official-endpoint probe to declare
an isolated process and strict deadline. It failed with
`AttributeError: 'CloudBalancePolicyV1' object has no attribute
'anonymous_probe_process_isolated'`.

The probe now launches one fixed in-package helper under isolated Python with
a minimal environment, no stdin, discarded stderr, a bounded sanitized stdout
record and no credential or destination input. DNS resolution, TCP/TLS,
response-header parsing and any body read all occur in that child. The parent
applies the caller/8-second monotonic deadline to the whole child, starts it in
its own session, passes only that non-secret absolute deadline, arms
`ITIMER_REAL` in the single-threaded child before project import, and sends
`SIGKILL` to the process group from the parent on expiry. Thus a blocked
resolver or slow-drip header read is interruptible in the child and has a
process-kill backstop before the supervisor returns `deadline_exceeded`. The
helper returns only state, HTTP status and bounded retry metadata; raw headers,
body, exceptions and balance values never cross the process boundary.

One real anonymous probe still reaches the fixed official endpoint and returns
sanitized HTTP 401. A second invocation of the same process-supervised entry
point applies a 1-millisecond deadline, observes `deadline_exceeded` and
returns within the bounded cleanup allowance. This is admission evidence for
the anonymous probe only. The direct authenticated path remains fail-closed as
`source_not_admitted`; no credential is passed to or inherited by the helper.
A future authenticated worker must retrieve/apply the managed item entirely
inside an equally bounded private process before this policy can be widened.
The accepted header-size check remains post-parse inside the isolated process,
so `wire_header_limit_strict` and authenticated admission remain false.

Final focused result after the child-timer hardening at
`2026-11-02T16:04:49Z`: `19 passed in 0.85s`.
