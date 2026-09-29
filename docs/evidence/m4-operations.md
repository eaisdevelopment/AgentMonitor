# M4 ST-OPS-001 — operations typed-core progress

- Status: **Intermediate — I01 pure core and facades; real integration Not Run by this agent**
- Date: 2026-09-29
- Plan: [M4 operations](../plans/integration/m4-operations-change.md), approved `0.2.0` I01
- Owner: M08; root owns real producer leaves/composition/API/generated/UI/gates
- Contracts: CTR-OPS-001..007, CTR-APP-001 V1 `1.0.0`; FND-002/003/007 and COMMON-001/007 consumed
- Requirements: FR-OPS-002/005/006, NFR-RES-001, NFR-OBS-001
- Acceptance contribution: AC-OPS-003/006, AC-V1-003/005/006/007/008. None is marked fully accepted here.

## Changed files and scope

- `backend/src/agentmonitor/contracts/operations_v1.py`: closed immutable
  health/readiness/diagnostic/overview DTOs and leaf/version protocols;
  deferred backup/export/participant declarations without implementations.
- `backend/src/agentmonitor/modules/operations/domain/health.py`: pure
  required/optional classification, expiry/future reasons and liveness.
- `backend/src/agentmonitor/modules/operations/domain/diagnostics.py`: pure
  actual-version/presence allowlist projection.
- `backend/src/agentmonitor/modules/operations/application/health.py`,
  `diagnostics.py`, `service.py`: read-only typed facade and bounded leaf calls.
- `backend/tests/operations/pure/test_health_policy.py`,
  `test_diagnostic_policy.py`: pure domain/contract tests only.
- [Module guide](../modules/operations.md) and this evidence record.

No API, generated file, producer implementation, database migration,
dependency, browser navigation, provider action or service action was changed
by this module agent.

## Red and Green

Commands run with the real repository Python 3.12 environment and pytest.
Constructed immutable inputs are explicitly pure domain examples, never
provider observations or fake I/O producers.

| Scenario | Exact command | Observed result |
|---|---|---|
| M4-OPS-PURE-001..007 initial core Red | `backend/.venv/bin/python -m pytest backend/tests/operations/pure/test_health_policy.py -q` | Exit 1; 18 tests failed because operations contracts/domain module were absent (`ModuleNotFoundError`). This is missing-core evidence, not real external-boundary failure evidence. |
| Core Green | Same command | Exit 0; 18 passed after typed contracts/classification. |
| Diagnostic projection Red | `backend/.venv/bin/python -m pytest backend/tests/operations/pure/test_diagnostic_policy.py -q` | Exit 1; 6 failed because the pure diagnostic projection module was absent. |
| Diagnostic Green | `backend/.venv/bin/python -m pytest backend/tests/operations/pure -q` | Exit 0; 24 passed. |
| APP-001 declaration Red | `backend/.venv/bin/python -m pytest backend/tests/operations/pure/test_health_policy.py -q -k dashboard_overview` | Exit 1; actual missing `DashboardOverviewV1` attribute. |
| APP declaration Green | `backend/.venv/bin/python -m pytest backend/tests/operations/pure -q` | Exit 0; 25 passed after actual M05/M07 DTO binding. |
| Component freshness explanation behavioral Red | `backend/.venv/bin/python -m pytest backend/tests/operations/pure/test_health_policy.py -q -k 'expiry_at or future_sample'` | Exit 1; 2 failed: unknown stale/future component still carried `operations_component_healthy`. |
| Freshness correction Green | `backend/.venv/bin/python -m pytest backend/tests/operations/pure -q` | Exit 0; 25 passed with per-component stale/future reasons. |

The first-stage absent-module Reds do not claim a fully executed HTTP,
application-leaf, database or provider acceptance path. Runtime facade
integration requires root's meaningful real-boundary Red/Green evidence; no
fake lifecycle, schema, clock or health producer was introduced for testing.

## Static and refactor verification

```bash
backend/.venv/bin/ruff format backend/src/agentmonitor/contracts/operations_v1.py backend/src/agentmonitor/modules/operations backend/tests/operations
backend/.venv/bin/ruff check backend/src/agentmonitor/contracts/operations_v1.py backend/src/agentmonitor/modules/operations backend/tests/operations
MYPYPATH=backend/src backend/.venv/bin/mypy --follow-imports=silent --explicit-package-bases backend/src/agentmonitor/contracts/operations_v1.py backend/src/agentmonitor/modules/operations
backend/.venv/bin/python -m pytest backend/tests/operations/pure -q
```

Ruff passed. Focused source mypy passed (6 files), after correcting a
configuration-presence Literal annotation. The initial plain mypy invocation
reported duplicate namespace module names; the explicit package-base command
above is the usable invocation. Final post-refactor results are reported in
the module handoff; root owns the full boundary and canonical quality gates.

## Boundaries and limitations

| Boundary | State in this handoff |
|---|---|
| Pure contract/classification/disclosure | Passed focused suite |
| Real active-WAL DB and actual schema leaf | Not Run by module agent; root owns implementation/verification |
| Real IAM/registry/collector/capacity/runtime/alert health leaves | Not Run by module agent |
| Actual application fan-out, deadline/cancellation and exception isolation | Not Run with real leaves by module agent |
| HTTP authorization/origin/provenance/no-GET-mutation | Not Run by module agent; root-owned gate |
| Built browser diagnostics/overview | Not Run by module agent; root-owned gate |
| Actual provider failure isolation/rate-limit cadence | Not Run by module agent; no provider calls made |
| Full M4 | Incomplete until root's full canonical gate passes |
| Wider backup/restore/retention/install/macOS | Outside this approved increment; not accepted |

## Security, privacy, compatibility and integration

The facade serializes closed states, safe versions, registered technical
indicators and presence only. It cannot read arbitrary files, rows,
credentials, account IDs or paths. Detailed queries are denied for service
disclosure; actual authentication remains P01/IAM. All health requests are
read-only; provider/login/migration/checkpoint actions are absent. Default
profiles and running agents were untouched.

No new dependency/license impact or migration. V1 contracts are additive;
published future workflow declarations are not exposed as working features.
Build metadata comes from the existing FND receipt; real source population is
root-owned. APP-001 response uses source-owned DTOs and explicit null/
availability semantics rather than copied telemetry or fabricated counts.

Next integration: root supplies genuine published leaves/schema version,
wires OperationsServiceV1 through the public facade, exercises real
SQLite/HTTP/built-browser scenarios, generates current V1 transport, runs
independent bounded review, and includes every remaining Story/criterion in
AUTO-M4-EXIT. This core progress does not replace that gate.
