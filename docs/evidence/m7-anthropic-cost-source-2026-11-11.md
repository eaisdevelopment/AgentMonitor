# M7 Anthropic first cost-source increment

- Status: **Partial; authenticated live collection Not Run**. Not T006 closure.
- Date: 2026-11-11; verification recorded by 16:15 UTC.
- Owner: A01, delegated agent `m7_execution_commands`; root owns integration.
- Authority: approved focused M7 plan 1.1.0, T006, and the
  [implementation authority](m7-implementation-authority-2026-11-11.md).
- Requirements: FR-BUDGET-001/002/003/006; AC-LIVE-004/005; M7-A03.
- Worktree: `codex/m7-api-budgets`; changes are uncommitted in this handoff.
- Consumed contracts: CTR-CAP-002 2.0.0 (`BudgetReportInputV1`),
  CTR-CAP-001 2.0.0 (cloud subject), CTR-COMMON-003 1.0.0 (exact money),
  CTR-REG-012 1.0.0 (active binding/target), CTR-PROV-002 1.0.0 and
  CTR-PROV-003 1.3.0 (candidate descriptor/documented-beta source). No shared-contract file edited by this agent.

## Delivered scope

The new `backend/src/agentmonitor/adapters/providers/claude/anthropic_api/`
package contains request policy, one dedicated-worker source and an experimental
cost-only manifest. Existing subscription collection is untouched.

The fixed destination is `https://api.anthropic.com/v1/organizations/analytics/cost`.
The source requests seven completed UTC days, daily buckets, no grouping,
chronological order. The API version is `2026-10-21` and beta header is
`analytics-usage-cost-2026-08-24`. Official documentation was checked during this
increment; see [cost reference](https://platform.claude.com/docs/en/api/beta/organization/analytics/cost/list),
[analytics semantics](https://platform.claude.com/docs/en/manage-claude/usage-cost-analytics-api)
and [versioning](https://platform.claude.com/docs/en/api/versioning).

Amounts are six-place decimal USD cents. Only discounted cost before credits
maps to the report's cost basis; list cost is validated but never added. The
mapping never infers a cash balance, hard limit, subscription quota or invoice.
A null/behind refresh watermark cannot produce complete zero coverage. Pages
must share a refresh watermark. Duplicate JSON keys, cursors and daily buckets
fail closed. Signed values remain signed adjustments.

Bounds: 20 requests, 2 MiB response body, 10,000 rows, 16 MiB conservatively
accounted normalized rows, 120 seconds per report, 10 seconds per request.
The specific ungrouped seven-day query additionally permits only one unique row
per requested day. Body/row budget checks occur before retention. TLS uses the
system trust store; no environment proxy, redirect, retry, compression or
provider mutation is used. Raw provider bodies never enter results or logs.

## Runtime integration interface

`policy.AnthropicCostRequestV1` captures `subject`, `binding`, `scope_id`,
`scope_evidence`, `scope_generation`, `period` and `requested_at`. `period` must
match `completed_week(requested_at)`; provider/account/binding authority is
validated without pretending that an owner assertion is provider verification.

The callable is:

```python
collect_cost_report_in_worker_v1(
    request,
    authorization=grant,
    deadline_monotonic=absolute_monotonic_deadline,
)
```

The grant implements `AnthropicCostAuthorizationV1.authorize(sink)` and calls
`sink.put_api_key(bytearray_value)`. The sink permits one fixed `x-api-key`
header, clears the mutable buffer, and exposes no destination control. Root
must supply the real grant with inherited-file/account-lock validation; this
agent does not read or provide a key.

`AnthropicCostResultV1` contains safe state/reason, an optional normalized
`BudgetReportInputV1`, attempted request count, HTTP status and optional parsed
Retry-After seconds. `partial` reports cannot replace complete totals. The
root rechecks captured binding and scope generations before committing.

The source must run only in root's dedicated supervised billing process with
an outer hard 120-second deadline. Its request context applies SIGALRM only on
that process's main thread with default handler and no existing alarm; otherwise
it refuses before credential application. Handler/timer cleanup runs in finally.
This is not an in-process FastAPI collector. The descriptor names its actual
`AnthropicCostSourceV1` interface; root still adapts it to M03/M04 outcomes.

## Test evidence

| Scenario | Layer | Result | What it proves |
|---|---|---|---|
| Request range/account/scope/cursor and exact cents conversion | Pure, 24 cases | Passed | Constructed domain values only; no provider JSON |
| Hard alarm and restoration | Actual isolated Linux process | Passed | Real blocking sleep interrupted; original handler restored |
| Existing alarm | Actual isolated Linux process | Passed | Source refuses without cancelling another alarm |
| Non-main thread | Actual isolated Linux process/thread | Passed | Source refuses unsupported execution context |
| Official beta manifest and scoped grant | Pure contract construction/resolution | Passed after root correction | Documented beta remains experimental; no grant means no resolution |
| Authenticated cost/report parsing | Real Anthropic | Not Run | No available-key claim, no fabricated success |
| M03 admission, M04 run, M05 commit, API/browser | Integration | Not Run | Root-owned later boundaries |

Focused command (existing admitted Python environment, worktree test config):

```bash
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest \
  -c backend/pyproject.toml \
  backend/tests/adapters/providers/claude/anthropic_api -q --tb=short
```

Request policy Red: 22 failed, 2 passed. Seven assertion-level failures showed
that the initial typed boundary accepted wrong provider/account/scope/generation,
unadmitted range and pre-2026 coverage. Fifteen failed because query encoding
and unit conversion were not yet implemented; these are separately reported,
not asserted to establish provider compatibility. After implementation, 23 passed
and one genuine scaled-zero conversion failed inside the shared exact-decimal
contract. Root fixed that shared defect with its own independent Red/Green;
request policy then passed all 24.

Deadline Red: all three actual-process assertions failed before the timer and
ownership checks existed. Green: all three passed after implementation.
Combined request/deadline verification: **27 passed**, including after formatting
and strict type checking. No absent-provider setup error is called Red.

Manifest construction exposed `provider_source_experimental_invalid`: the
existing shared `ProviderSourceV1` equates experimental with private/browser
source class. A documented beta API must not be mislabeled private or fully
supported. The root owns the additive contract correction; the focused manifest
test remains Failed until that lands.

Static checks: scoped Ruff check passed; scoped strict mypy passed all four
source files with `MYPYPATH=backend/src --explicit-package-bases
--follow-imports=silent`. Provider parsing itself is not established by these
checks. No temporary backend/frontend tool links were created.

## Remaining integration work

1. Root resolves documented-beta experimental source classification and reruns
   the focused manifest test. Bind the descriptor to actual source admission;
   documentation-discovery hash is not authenticated live evidence.
2. Root connects the protected credential reader and supervised worker. The
   owner uses the tested local-entry UI workflow; no manual agent account setup.
3. T003 publishes a scoped Anthropic live invocation. Existing full M7 gates
   remain blocked; a passing policy suite cannot close T006 or M7.
4. Execute the real source with an actual owner-selected billing connection;
   reconcile exact period/scope/cost with the authoritative Console view.
5. T005/T007 persist and schedule the report. Existing scheduled-source policy
   only admits one request; paged reports need the planned additive bounded
   admission. Existing cloud run admission requires `profile_id`, which API-only
   enrollment does not create. Existing commit receipts require nonempty
   observation IDs; report coverage needs the planned additive receipt variant.
   No fictitious profile or observation ID was introduced here.

## Security, compatibility and integrity

No new dependencies, migration, API/UI change, environment-variable reads,
provider calls, credential entry, account configuration or default-profile access.
Only the new A01 package, its tests and this evidence file were written. Existing
Ollama transport patterns were inspected; no provider-private imports were added.
The protected credential grant and provider JSON success path remain live-test
obligations. No mocked/replayed provider data, test-only transport collaborator,
seeded telemetry or fabricated dashboard value was used. This record contains
no account identifiers, credential values or provider response bodies.


## Resumed correction and final scoped verification

The original-deadline defect was corrected after the planning review. The existing
clamp was first extracted without changing its behavior. New pure checks showed
that supplied NaN and positive infinity were silently replaced by a fresh budget;
an actual isolated-process check showed a NaN deadline was admitted and armed.
Meaningful Red after correcting a temporary test-file editing error:
**3 failed, 29 passed**. The editing error itself is not Red evidence.

`bounded_deadline()` now validates the original finite monotonic inputs before
clamping, preserves an earlier caller deadline, caps a later deadline and rejects
expired/non-finite values before an alarm is installed or a credential is used.
Both the report and per-request boundaries use this policy. Final report
normalization is bracketed by absolute-deadline checks, so a late final page cannot
return successful facts after the caller's deadline.

Root separately corrected CTR-PROV-003 to 1.3.0 with its own Red/Green: documented
API sources may explicitly be experimental; private-source restrictions remain.
The previously failing manifest construction now passes. Root's additional
resolver check confirms that the experimental source still needs an admitted
source policy and scoped grant; merely constructing the descriptor cannot enable
collection.

Final complete A01 directory command above: **34 passed**, comprising 28 pure
request/deadline/unit cases, four actual isolated-process cases and two manifest/
scoped-grant cases. Strict mypy passed the four A01 source files. Root formatted
its manifest test after a line-length finding. These checks establish no provider
HTTP, authentication, raw-response mapping or monetary-persistence success.

The manifest contract blocker is resolved. T006 remains partial: root's dedicated
worker/admission integration and a real owner-selected monetary reading are still
required, followed by T005/T007 integration. No new accounts, keys, service changes,
provider requests, dependency or shared-contract edits were performed by this agent.
