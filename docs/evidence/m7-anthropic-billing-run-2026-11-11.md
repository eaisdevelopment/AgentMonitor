# Test evidence: Anthropic billing-run composition

- Evidence ID: M7-ANTHROPIC-BILLING-RUN-2026-11-11
- Module/plan/increment: M7 composition; T006/T007
- Requirements/acceptance IDs: FR-BUDGET-001, FR-BUDGET-004,
  FR-BUDGET-006; M7-A02, M7-A03, M7-A09
- Contract versions: CTR-REG-012 ProviderAccessTargetV1; CTR-REG-014
  BillingAccessTargetV1 1.3.0; CTR-COL-002 BudgetCollectionRunAdmissionV1
  2.1.0; CTR-PROV-004 CollectionOutcomeV1; CTR-CAP-002
  BudgetReportInputV1 2.0.0; CTR-CAP-004 BudgetCollectionInputV1 2.1.0
- Commit/worktree reference: `m7-api-budgets` at base `ad7a04e`, uncommitted
  delegated slice
- Recorder/date: Codex `/root/a01_impl_preflight`, 2026-11-11

## Test inventory and status

| Test/scenario ID | Layer | Real dependencies | Status | Evidence reference | Notes |
|---|---|---|---|---|---|
| M7-BILLING-RUN-PURE | Pure domain/composition | Published technical contracts only | Passed | `backend/tests/contracts/test_anthropic_billing_run.py` | 21 checks cover admission, exact period, fixed request budget, idempotent digest, typed success/partial/failure normalization and identity fencing. |
| M7-BILLING-ADJACENT | Pure contracts | Published technical contracts only | Passed | Focused 61-test command below | Includes budget admission, budget codec and Anthropic request-policy checks. |
| M7-BILLING-STATIC | Static | Development toolchain | Passed | Scoped Ruff and strict mypy commands below | No suppressions added to production code. |
| M7-BILLING-REAL-PROVIDER | Provider | Real Anthropic account and owner-entered Admin API key | Not Run | Root-owned live verification | This slice performs no provider request and does not claim live source compatibility. |
| M7-BILLING-SQLITE | Database | Real migrated SQLite database | Not Run | Root-owned M04/M05 integration | This slice contains no storage adapter and does not claim durable admission/commit. |

## Red evidence

Before `billing_run.py` existed, this command failed during collection for the
expected missing production composition module:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -B -m pytest \
  -c backend/pyproject.toml -q --tb=short \
  backend/tests/contracts/test_anthropic_billing_run.py
```

Sanitized result: exit 2; `ModuleNotFoundError: No module named
'agentmonitor.composition.billing_run'`; one collection error.

## Green evidence

The same focused command passed after the minimum composition implementation:

```text
21 passed in 0.30s
```

Adjacent pure contract checks:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -B -m pytest \
  -c backend/pyproject.toml -q --tb=short \
  backend/tests/contracts/test_anthropic_billing_run.py \
  backend/tests/contracts/test_budget_run_contract.py \
  backend/tests/capacity/pure/test_budget_codec.py \
  backend/tests/adapters/providers/claude/anthropic_api/test_request_policy.py
```

Sanitized result: exit 0; `61 passed in 0.40s`.

## Refactor evidence

Scoped Ruff check and format check passed using `backend/pyproject.toml`.
Strict mypy passed for the new source and test: `Success: no issues found in 2
source files`.

## Real-system evidence

No filesystem, database, browser, process, network or provider boundary was
invoked by this delegated slice. Real M04 admission/recovery, M05 commit, and
authenticated Anthropic collection remain root-owned integration/live work and
are explicitly Not Run here.

## Integrity declaration

No mock, fake, stub, emulator, recorded provider response, demo account, seeded
telemetry, placeholder value, test-only production branch, disabled assertion,
or swallowed failure was used. Constructed values occur only in pure tests of
technical contracts with no I/O behavior.

## Data and secret review

The implementation and evidence contain no API key, provider payload, owner
account identifier, prompt/response content, profile data or arbitrary process
environment value. Failure mapping emits only closed sanitized reason codes.

## Conclusion and residual gaps

The evidence proves the pure composition from one exact M02 billing/access
target through bounded M04 admission, M03 outcome and M05 commit input. It does
not prove SQLite persistence or provider behavior. Integration must consistently
use `anthropic_cost_manifest_fingerprint()` for M02/M04's 64-hex SHA-256 audit
field; the underlying published M03 catalog fingerprint is 32 hex and cannot be
written directly into those contracts. Root must run the real database and live
provider gates before any completion claim.
