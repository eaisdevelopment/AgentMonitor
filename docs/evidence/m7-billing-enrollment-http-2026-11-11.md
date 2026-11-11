# M7 billing enrollment HTTP: initial Red

- Evidence ID: M7-REG-001-HTTP-RED-2026-11-11.
- Module: P01 real HTTP tests supporting M02 enrollment, M7-T002.
- Approved scope: [M7 execution plan 1.1.0](../plans/integration/m7-execution-plan-2026-11-11.md), [UI journeys](../plans/integration/m7-ui-and-user-journeys.md), and [implementation authority](m7-implementation-authority-2026-11-11.md).
- Requirements: FR-ACC-001..004/006, FR-BUDGET-001/006; this initial test directly exercises account creation and inert billing setup intent.
- Acceptance contribution: M7-A01, AC-UI-005, AC-TEST-001/003/006. No acceptance item is closed by this Red.
- Contracts: existing CTR-REG-002 and CTR-API-001..003 V1; proposed optional API creation intent and billing-connection read. Root owns publication of detailed billing status/capability DTOs.
- Checkout: `a91424881504389264362e8763c2fc1d79866502` plus this test and concurrent authorized M7 work in `m7-api-budgets`.
- Recorder: P01 delegated agent; 11 November 2026.

## Test inventory

| Test | Boundary | Result |
|---|---|---|
| `test_api_account_creation_exposes_safe_billing_status` | Real migrated file SQLite, production IAM login and loopback Uvicorn HTTP | Failed for the expected unsupported creation intent |
| `test_account_creation_rejects_invalid_purpose_and_unknown_fields` | Same real boundary; invalid purpose, unknown field, and null `api_key` field | Passed; all requests rejected with 422 and no account created |
| Created-account billing status GET | Continuation of first test | Not Run: creation assertion failed first |
| Detailed billing capability/status assertions | Root-owned contract publication | Not Run; not invented by this initial test |

## Red evidence

Command started at `2026-11-11 14:41:24 UTC` from the M7 worktree:

```bash
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -c backend/pyproject.toml --import-mode=importlib -q --tb=short -p no:cacheprovider backend/tests/integration/api/test_billing_enrollment_http.py
```

The existing admitted interpreter was used because this worktree has no
`backend/.venv`. The explicit candidate pytest configuration selects this
checkout's backend source and test imports. No dependency was installed.

Exit status: **1**. Result: **1 failed, 1 passed in 6.14s**.
The expected behavioral failure was:

```text
AssertionError: API-purpose account creation must succeed; received HTTP 422
assert 422 == 201
```

The server started and production IAM login succeeded before the assertion.
The request adds `initial_connection_purpose: "api"` to the otherwise valid
existing account-create schema. The current closed request schema rejects that
field. This is a missing enrollment behavior, not missing credentials or a
server/setup failure.

The same initial test retains assertions for a returned account ID and Location,
disabled monitoring, unresolved identity, and an account-scoped noncached billing
status GET. These later assertions were not executed in this run. Exact pending
capability/status assertions must be added once the root publishes their DTO.

## Green, refactor and live status

Green and post-production-refactor verification: **Not Run**. No production code
was changed. The passing rejection test records existing validation behavior,
not Green for API billing enrollment.

Real SQLite, IAM and HTTP executed. Built browser, provider access, local provider
credential enrollment, installed service and owner account flows: **Not Run**.
No M7 gate or milestone completion is claimed.

## Integrity and impact

Only the assigned test file and this evidence file were added. Tests reuse
`test_iam_http` helpers for real migrations, randomized isolated dashboard IAM,
and an ephemeral loopback server. Account labels are administrator metadata
submitted through production HTTP; no provider account or telemetry is seeded.
The unknown credential-named field has a null value; no provider credential is
created, read or submitted. The tests do not inspect the operator's `.env`,
provider profiles, owner database or installed service.

No mock, fake, stub, replay, network interception, test-only production branch,
skipped assertion or fabricated provider data was used. Evidence contains no
passwords, cookies, CSRF values, provider payloads or personal identifiers.
No migration, dependency/license, runtime configuration or deployment changed.

Next step: root publishes the additive creation/status contracts; the allocated
implementation writer implements them, extends the pending-capability assertions,
and reruns this command for Green. Live verification and browser evidence remain
separate required boundaries.
