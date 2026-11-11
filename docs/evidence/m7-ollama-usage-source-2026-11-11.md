# M7 bounded Ollama usage source increment

- Status: Partial T009 implementation; authenticated source mapping **Not Run**.
  This is not provider admission, installed collection or T009/M7 completion.
- Authority: approved focused M7 plan 1.1.0, T009; root-approved usage-specific
  authorization interface within the existing runtime-only credential exception.
- Requirements: FR-BUDGET-001/002/003/004/005/006; contributions to AC-LIVE-004/005,
  AC-HIST-001 and AC-TEST-001/002. No live criterion is claimed passed.
- Owner: A03. Consumes unchanged CTR-CAP-001 2.0.0, CTR-CAP-002 2.0.0,
  CTR-COMMON-003 1.0.0, CTR-REG-011 1.0.0 and CTR-REG-012 1.0.0.
- HEAD observed at final checks: `7e252b869e28d62582b675f9e3cecc1612d6c5c4`.

## Documentation and scope

The official [cloud usage reference](https://docs.ollama.com/api/cloud-usage) was
read on 11 November 2026. It documents GET `/api/usage`, `7d`/`30d` completed UTC
days plus today, explicit self/team scope, optional monetary/token fields and
legacy request-only usage. Team access requires an administrator. Its published
rate limit is ten requests per minute per user across keys/devices, with numeric
Retry-After on 429. The API describes reporting coverage but supplies no stable
user/team identifier or source-update watermark in the documented response.
These are documentation findings, not observed owner account capabilities.

The first source requests ungrouped daily request counts and optional reported
USD. It does not request model breakdowns, infer token costs, add cached tokens,
fetch balance, or create another credit pool. Token fields are validated when
present but not mapped in this increment; token/model mapping remains T009 work.

## Candidate behavior and interface

`policy.OllamaUsageRequestV1` captures the existing cloud subject and actual
active binding reference, scope identity/evidence/generation, `range_key`, exact
completed-day `period`, `requested_at` and `scope` (default `self`). Team scope
must be explicit. Identity evidence passes through unchanged; a successful GET
does not promote unresolved/owner-asserted scope to provider-verified identity.

The root-approved adapter-local interface is:

```python
collect_usage_report_in_worker_v1(
    request: OllamaUsageRequestV1,
    *,
    authorization: OllamaUsageAuthorizationV1 | None,
    deadline_monotonic: float | None = None,
) -> OllamaUsageResultV1
```

The grant implements `authorize(sink)`; the exact
`OllamaUsageAuthorizationSinkV1.put_bearer_token(bytearray)` applies only one
Authorization header and clears the supplied mutable buffer. This is a distinct
type/method from the existing balance grant. No balance grant, environment reader,
credential/profile file, database, composition or existing admission is imported
or broadened by this source. Root must issue the genuine usage-purpose grant,
validate inherited physical capabilities, and recheck binding/scope generations
before dispatch and commit. No shared contract edit was needed for this source.

Transport is one fixed HTTPS GET to `ollama.com`, no redirects, retries or
environment proxy. A ten-second request bound uses the dedicated-process alarm
pattern, including DNS/TLS/headers/body. Root still owns the outer supervised
process lifetime; local alarm checks do not prove process provenance. Headers
are bounded to 16 KiB/66 status-and-header lines and body to 2 MiB. The ungrouped
schema accepts at most the selected complete days plus one current partial day.
The intended periodic interval is the plan's fifteen minutes; this source does
not itself schedule, reserve rate budget or coordinate shared user limits.

The native range/scope/day granularity and top-level bounds must match the
request. Daily buckets must be contiguous and match exact UTC boundaries;
today must be the final partial bucket and is excluded from selected totals.
The wider native total is checked but never used as completed-period spend.
An unexpected gap or midnight cutoff mismatch fails closed as invalid source
data, retaining no falsely complete report.

JSON decimal numbers are decoded directly to Decimal and exact USD, preserving
signed values and precision within the shared bounds. Negative daily costs are
signed adjustments, not deposits. Missing monetary fields are not zero: all
missing produces `money_availability=not_reported`, no currency/cost facts and
real request-count facts; mixed availability produces a partial report. The
source does not assert which plan caused missing fields. Exact reported daily
zeroes remain observations, distinct from an invented empty-report zero.

`source_data_through=None` and `empty_means_zero=False` are deliberate. Request
time and native `until` are not update watermarks. Categories distinguish
`self_requests_and_cost` from `team_requests_and_cost`; cost basis is only
`provider_reported_usage_usd`, without inferred discount/credit semantics.
No balance denominator, remaining percentage or forecast is derived. Self usage
cannot establish compatibility with a team balance for later forecasting.

Results contain only normalized reports, closed state/reason, money availability,
HTTP status, Retry-After and a conservative request-attempt count. A pre-header
authorization failure can still consume a reserved attempt; this count is not
proof that the provider received the request. Raw bodies, headers and key bytes
are not returned/logged. Mutable body/token buffers are cleared; complete Python
heap erasure is not claimed.

## Red / Green and actual boundaries

Initial missing-owned-capability Red:

The request-policy file was named `test_request_policy.py` when this Red ran;
the command below uses its final unique filename after integration renaming.

```text
.../backend/.venv/bin/pytest -q backend/tests/adapters/providers/ollama/api/test_ollama_usage_policy.py
1 failed in 0.03s
AssertionError: Ollama usage-specific policy and grant are missing
```

Before the source existed, the four actual-process tests also failed at import
with `ModuleNotFoundError: No module named 'agentmonitor.adapters.providers.ollama.api'`
(4 failed in 0.12s). These are feature-absence Reds, not provider/schema failures
or evidence that alarm behavior had been tested before implementation.

The first combined run exposed 18 incorrectly constructed pure binding IDs;
these were test-input errors, not claimed production Red. Correcting them to
the existing `amcb_` shape yielded **37 passed in 1.21s**. Constructed active
references occur only in pure request policy tests and never cross I/O.

An additional real behavioral Red found that the initial HTTPS constructor
honored `SSLKEYLOGFILE`: an unconnected subprocess context enabled keylogging
(1 failed in 0.49s). No handshake, credential or network was involved. The
fixed-host connection now constructs verified TLS directly, using
`SSLContext(PROTOCOL_TLS_CLIENT)`, hostname checks, CERT_REQUIRED and default
trust, without the environment logging hook. The same test then passed without
creating the selected empty-test log path. The analogous A01 issue was reported
to root separately; no A01 file was edited here.

Final regression command:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/adapters/providers/ollama/api backend/tests/adapters/providers/ollama/test_cloud_probe_descriptor.py backend/tests/adapters/providers/ollama/test_env_authorization_policy.py backend/tests/adapters/providers/ollama/test_env_capability_policy.py
54 passed in 1.62s
```

The new tests comprise 33 pure request/unit/context cases and five real process /
unconnected TLS/sink checks. They prove exact request admission, finite deadlines,
actual blocking interruption/restoration, refusal of preexisting alarms and
non-main threads, empty-token denial and absence of environment-requested TLS
logging. They use no substitute transport, provider JSON fixtures, recordings,
fake grants, fake keys or owner credential files.

Ruff and strict mypy passed all five new Python files:

```text
MYPYPATH=src .../backend/.venv/bin/mypy --strict --explicit-package-bases src/agentmonitor/adapters/providers/ollama/api tests/adapters/providers/ollama/api
Success: no issues found in 5 source files
```

The meaningful authenticated provider Red remains **Blocked**: no actual
usage-purpose runtime grant is wired for this increment. Existing M6 balance
authorization cannot substitute for it. Credential availability was not inspected.
Authenticated parsing, legacy/paid field behavior, self/team comparison, 401/403/
429 outcomes, actual wire bounds and cost-to-storage/browser reconciliation are
**Not Run**. Source mapping is candidate code, not live-validated behavior.

## Compatibility and next integration

The actual existing balance fingerprint remains
`047d2bf64f70eae87a54223cb6f1aa3bec240c84ae99c0cc2155db8342a5110f`.
Before/after file hashes are unchanged:

- `cloud_balance/env_policy.py`: `b483b865b3cc760cb8f1a631647de0db8a1af34502a8142ad386b06c79bf96c9`.
- `cloud_balance/probe_descriptor.py`: `d3792a2b539dbeb1ea85976dd7528642207d77b459b597a2a9e4c17dc6ba6d2b`.
- `cloud_balance/source.py`: `001412eb403a0bb5bb6e7bb2bf568853fae23cd2f91b61823f6941acc2312a5f`.

Root must bind a new usage source policy/fingerprint and actual usage-purpose
lineage, reuse the existing owner-controlled connection, supervise the worker,
coordinate rate limits with other access paths, and re-fence the report before
M05 commit. No scheduled capability or owner monitoring preference was changed.
T009 still needs authenticated comparison, supported token/model views and actual
shared balance attribution; request-only usage cannot close the monetary slice.

Files: `backend/src/agentmonitor/adapters/providers/ollama/api/{__init__,policy,source}.py`,
`backend/tests/adapters/providers/ollama/api/{test_ollama_usage_policy,test_ollama_usage_worker}.py`,
and this evidence. No dependencies/license changes, migrations, shared contracts,
provider calls, owner account changes, secret reads or default-profile operations.
No commit was made by this agent.

## Combined discovery correction

Renamed the A03 tests to `test_ollama_usage_policy.py` and
`test_ollama_usage_worker.py` so default pytest import mode cannot confuse them
with another provider's modules. No production code changed. Combined verification:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/adapters/providers/claude/anthropic_api backend/tests/adapters/providers/ollama/api
73 passed in 2.59s
```

This confirms combined discovery and the scoped cases, not authenticated usage.

## Review correction: normalization deadline

Independent review found that the request alarm ended when `_fetch` returned,
but the source could normalize and return a report without rechecking its
absolute deadline. The source now calls the existing `bounded_deadline` policy
immediately before and after `_report`. Expiry returns the existing closed
`deadline_exceeded` result without a report. The outer supervised worker remains
responsible for the hard process lifetime; these checks do not interrupt Python
normalization themselves or replace that supervision.

The existing pure deadline tests and actual-process alarm tests cover the reused
policy and timer behavior. No new provider payload, substitute grant or simulated
transport was introduced. A failing authenticated normalization timing case was
**Not Run**, so this correction has no claimed live Red or authenticated mapping
Green. It is a review-driven guard correction within partial T009, not a completed
provider verification.

The same focused regression command above passed again: **54 passed in 1.52s**.
Scoped backend Ruff passed for `backend/src/agentmonitor/adapters/providers/ollama/api`
and `backend/tests/adapters/providers/ollama/api`. Only this evidence and
`backend/src/agentmonitor/adapters/providers/ollama/api/source.py` changed in this
correction. Requirements and unchanged contract versions remain those listed
above; no dependency, migration, secret access or account/runtime change.
