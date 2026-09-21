# Architecture decision records

Accepted decisions are historical records. Do not edit an accepted ADR to conceal a later change; add a new ADR that supersedes it.

| ADR | Status | Decision |
|---|---|---|
| [0001](0001-modular-monolith.md) | Accepted | Modular monolith with enforced module boundaries |
| [0002](0002-api-first-fastapi-openapi.md) | Accepted | API-first FastAPI/OpenAPI backend and generated UI client |
| [0003](0003-real-system-testing-no-test-doubles.md) | Accepted | TDD with real systems and no mocks/fakes at boundaries |
| [0004](0004-native-local-deployment.md) | Accepted | Native local deployment before containers/remote hosting |
| [0005](0005-capability-driven-provider-adapters.md) | Accepted | Capability-driven versioned provider adapters |
| [0006](0006-read-only-metadata-first.md) | Accepted | Read-only operational metadata; no content/process control in V1 |
| [0007](0007-secret-and-provider-profile-model.md) | Accepted | `.env` for app secrets; provider credentials remain provider-managed |
| [0008](0008-sqlite-local-persistence.md) | Accepted | SQLite V1 with migration discipline and portability seam |
| [0009](0009-polling-and-dashboard-notifications.md) | Accepted | Minute-scale polling and dashboard-only V1 notifications |
| [0010](0010-no-product-telemetry.md) | Accepted | No external AgentMonitor analytics/crash reporting in V1 |
| [0011](0011-copyright-and-dependency-licenses.md) | Accepted | All rights reserved; permissive dependency admission gate |
| [0012](0012-cookie-read-origin-proof.md) | Accepted for M2 correction | Origin proof before cookie-authenticated reads |

Use [the ADR template](../templates/adr-template.md) for new decisions.
