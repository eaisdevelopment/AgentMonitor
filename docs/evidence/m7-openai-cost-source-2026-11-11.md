# M7 A02 first OpenAI Costs source — partial implementation evidence

Date: 2026-11-11. Ticket M7-T008, scenario M7-PROV-A02; requirements
FR-BUDGET-001/002/003/006; acceptance AC-TEST-001, AC-LIVE-004/005, M7-A04.
Approved authority: focused M7 plan 1.1.0 and
[m7-implementation-authority-2026-11-11.md](m7-implementation-authority-2026-11-11.md).
Owner: A02. This is the first ungrouped cost-source candidate, not full T008,
provider live verification, scheduling admission, deployment or M7 acceptance.

## Official source and scope

Rechecked the official [Costs reference](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage/methods/costs)
on 11 November 2026. It documents GET `/v1/organization/costs`, administrative
Bearer authentication, inclusive/exclusive Unix-second boundaries, daily buckets,
optional grouping and paginated results. Amounts are numeric values with an
associated currency. Its response schema has no source-refresh watermark.
Documentation examples were not copied into tests or used as live evidence.

The candidate requests only seven or thirty completed UTC days, ungrouped and
without account/project/key filtering. It calls only `api.openai.com:443` and the
fixed cost path. It does not request inference, inspect Codex profiles, discover
keys or use subscription authentication. Usage categories, breakdowns, prepaid
balance and enforcement/limit claims remain separate work.

## Runtime handoff

Files under `backend/src/agentmonitor/adapters/providers/codex/openai_api/`:

- `policy.py`: `OpenAICostRequestV1`, `completed_period(instant, days)`, fixed query,
  bounded decimal conversion and deadline policy.
- `source.py`: `collect_cost_report_in_worker_v1(request, authorization=grant,
  deadline_monotonic=absolute_deadline)` and its typed result/protocols.
- `__init__.py`: package ownership only.

Request carries the real cloud-service `CapacitySubjectV2`, active binding,
scope evidence/generation, requested period and request time. Provider key is
`codex`; source ID is `openai.organization.costs.v1`. These are distinct from the
Codex subscription source. Root owns actual registry selection and grant issuance.

The root-issued grant implements `OpenAICostAuthorizationV1.authorize(sink)`.
The sink accepts `put_api_key(bytearray)` once, emits only the fixed
`Authorization: Bearer` header, and clears the supplied mutable buffer. It exposes
no destination or request control. Root revalidates the inherited credential
selection/account lock for each authorization and fences binding/scope again
before commit. This adapter reads no credential, environment or profile file.

Run only in the dedicated supervised worker with root's hard 120-second lifetime.
The source rejects thread/preexisting-alarm use and adds a real ten-second
SIGALRM request deadline. It is not safe to call from the API service main thread
merely because that thread currently has no alarm. Root supervision is required.

Result fields: state, closed reason code, optional normalized report, attempted
request count, optional HTTP status and Retry-After seconds. `requests_made`
counts attempts, including an authorization failure before wire dispatch; it
must not be presented as independently observed HTTP traffic.

## Financial and parser boundaries

The source parses numeric JSON lexemes directly into Decimal and published exact
quantity values. No binary float, token pricing, currency conversion, cents
scaling or context-dependent rounding. It admits the reported lowercase currency
and normalizes its code; mixed currencies cannot become one report. Cost basis
`openai_reported_cost` deliberately does not assert discount, tax or credit
semantics or equality with another provider's basis. Negative costs remain
signed adjustments.

Only exact allowlisted page/bucket/result fields are read. Ungrouped results must
not contain non-null grouping/quantity metadata or multiple result groups.
Malformed optional monetary fields fail closed; missing optional monetary fields
remain unavailable/partial rather than zero. Duplicate JSON keys, buckets or
cursors are refused. Every actual day must be aligned and within the request.

An exhausted wholly empty report may carry complete requested coverage with
`currency=None`, zero facts and `empty_means_zero=False`. It is not a claim of zero
money. Nonempty daily coverage missing requested days remains partial; explicit
empty result buckets contribute coverage without manufactured monetary facts.
Source freshness stays `source_data_through=None`, never collection time.
Collection time is separate. Pagination limits produce partial coverage and no
complete total. Earlier complete data must be retained by the consumer.

Bounds: twenty requests, 2 MiB per response, 16 MiB conservatively bounded
normalized data, 10,000 normalized records, 120-second report deadline and
10-second request deadline. The ungrouped daily source is additionally limited
by its unique seven/thirty daily intervals. No automatic retries, redirects,
proxy-environment use, compressed response acceptance or raw response persistence.
TLS uses verified system roots/hostname checking and disables key logging even
when SSLKEYLOGFILE is set. The destination is fixed before connection setup.

## Tests and actual outcomes

Owned tests are uniquely named under
`backend/tests/adapters/providers/codex/openai_api/` to avoid collisions with A01
or A03 pytest modules. They contain no provider JSON, replay, mock transport,
fake grant, configured account or credential.

- Initial new-policy unavailability: 43 tests failed because the new policy
  module did not exist. This is missing implementation evidence, not an observed
  provider failure or a successful behavioral live Red.
- Actual TLS-factory Red: using `create_default_context` with a process-local
  requested keylog path failed the assertion that key logging remained disabled.
  No TLS handshake or key existed. After replacing the factory, the final test
  exercises the actual `_Connection` constructor wired to it and verifies trust,
  hostname checks, no keylog file and rejection of another destination.
- Final Green: **54 passed** (1.35 seconds): 43 pure request/money/deadline cases,
  five pure normalized-report policies, one absent-grant refusal, four actual
  isolated alarm-process checks and one actual TLS-context check.
- Ruff: passed. Strict scoped mypy: passed, three source files.
- Authenticated HTTP, genuine payload mapping, real pagination, natural
  401/403/429, provider revisions and source reconciliation: **Not Run**.

Commands:

```sh
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -c backend/pyproject.toml backend/tests/adapters/providers/codex/openai_api -q --tb=short
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m ruff check backend/src/agentmonitor/adapters/providers/codex/openai_api backend/tests/adapters/providers/codex/openai_api
MYPYPATH=backend/src /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m mypy --config-file backend/pyproject.toml --explicit-package-bases --follow-imports=silent backend/src/agentmonitor/adapters/providers/codex/openai_api
```

## Contract and remaining integration impact

Consumes `BudgetReportInputV1` / `BudgetCostBucketV1` (code-declared
CTR-CAP-002 2.0.0), `CanonicalDecimalV1` / `ExactMoneyV1` (CTR-COMMON-003 1.0.0),
and `ActiveCredentialBindingRefV1` (CTR-REG-011 1.0.0). No shared contract edited.
Root was notified that the frozen planning baseline has older CAP metadata and
omits A02 from the REG-011 consumers; normal shared adoption synchronization is
root-owned. No private provider/domain imports were introduced.

Next integration uses this typed callable in root's billing worker, admits its
source/capability, supplies the real runtime grant and reconciles a genuine report
through the existing report store/API. No manifest or scheduling grant is
fabricated here. A real monetary fact remains necessary for first-money proof;
a coverage-only or unavailable report cannot satisfy it.

No installed service, source account, provider state, default profile or credential
was changed. No dependency, license, migration, UI or database change. Raw provider
payload parsing remains unverified until genuine authorized access; this evidence
must not be used to close M7-A04 or T008.

## First seven-day runtime integration, 12 November 2026

T008/T007 now have a local OpenAI cost manifest and run composition, plus explicit
OpenAI selection in Check, scheduling, recovery, durable claims, the protected
credential grant and source/commit normalization. The UI permits the existing
Check workflow for stored OpenAI administrative credentials. This extends the
same worker and contracts; no new queue, shared DTO, migration, dependency,
credential store, source category or default-profile behavior.

The local service authority `openai.organization` is a code-owned routing key,
not proof of provider identity. Source/version admission pins the reviewed
documentation mechanism; report provenance retains unknown upstream version,
watermark and freshness. Exact reported currency is preserved, including
currency=None for empty coverage without monetary facts. Existing Anthropic
source/digest behavior remains unchanged.

Tests and scope:

- Initial manifest/run Red: two missing-module errors; later malformed-result
  Red exposed an AttributeError and now produces a sanitized closed failure.
  Sixty-eight new pure cases and140 combined provider/run regressions pass.
- Root Red: OpenAI schedule intent rejected with
  `billing_schedule_target_invalid`; actual isolated metadata Check incorrectly
  returned `billing_check_provider_unsupported` instead of missing authority.
  Both corrected. Fifteen scoped actual HTTP/SQLite/worker and pure tests pass;
  no constructed report, binding credential or provider result enters storage.
- UI Red: OpenAI missing-credential guidance said checking was not implemented.
  Pure Green verifies required local entry, stored-credential eligibility and
  continued separation from Ollama's cloud setup.
- Canonical M7 pure passes583 Python cases and seven presentation suites.
  Canonical collection_guards passes42 cases: actual no-credential inventory,
  worker/recovery/supervisor boundaries and scheduling/retry policy. These are
  not successful OpenAI requests or populated monetary commits.
- AUTO-QUALITY passes at00:41:20UTC: Ruff760 formatted files, strict mypy699,
  zero boundary violations, compatible91-operation API/client, typecheck/build.
  An earlier overlapping execution of canonical checks removed shared temporary
  tool links before another test finished, causing tool/import failures. The
  independent reruns passed; those orchestration failures are not product Red
  evidence. Run tool-link-owning canonical checks serially.

Root reviewed the module implementation and wired the source to existing
binding/scope/commit fences. Both already-admitted cost queues are inspected
before fresh scheduled work; due selection covers both provider inventories.
Full cross-provider backlog fairness, thirty-day intents, usage/categories and
breakdowns remain the existing T007/T008 scope, not implied by this increment.

Read-only installed inventory currently contains zero billing connections.
No genuine source read/parse/receipt or provider-to-screen amount is claimed.
Owner enrollment and local credential entry remain necessary for that live lane;
no owner account configuration was performed. The code remains a candidate until
its exact commit is installed and separately verified. Full T008/M7 stay open.

Files: new A02 manifest and `composition/openai_billing_run.py`; existing billing
actions/collection/schedule/monitoring; P02 Check presentation; pure and actual
metadata/worker tests; existing M7 runner suite registrations. Reuses
CTR-REG-0141.3+, CTR-COL-0022.1, CTR-CAP-0022.0 and current API schemas without
breaking changes. Security custody, license and database shape are unchanged.

### Installed checkpoint

Clean implementation revision `46b8d9d5dd546e0d46aa07e1c20cfc8bd26f9a06`
passed the existing same-schema update command on12 November2026:
`python3 tools/automation/implementations/auto_m6_current_update.py
--expected-revision=46b8d9d5dd546e0d46aa07e1c20cfc8bd26f9a06`.
It retained schema0734 and restored the original restart policy. Service active,
loopback HTTP200, exact installed revision and authenticated browser were verified.
At00:45UTC the Overview probe passed all seven checks, two real rows and zero
unsafe requests; setup/shell probe passed all six checks with64 requests and zero
unsafe requests. These prove installed continuity and controls, not OpenAI costs.

The54 existing OpenAI pure/actual TLS/alarm checks passed again in1.93s. Pinned
Gitleaks8.30.0 scanned the new publication range: exit0, no findings. GitHub main
was fast-forwarded and `git ls-remote` confirmed exact revision46b8d9d.
No account, group, credential, monitoring preference or provider profile was
changed. Required monetary source evidence and full M7 remain unfinished.
