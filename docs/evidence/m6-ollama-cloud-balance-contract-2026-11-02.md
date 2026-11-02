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
