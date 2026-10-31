# Change plan: M4 dashboard API integration

- Status: **Approved for root-owned additive P01/P02 integration**.
- Version: `1.0.0`; root integration review: 2026-09-29.
- Authority: existing full M4 implementation authorization.
- Requirements: `FR-UI-001..006`, `FR-ALERT-001..005`, `FR-OPS-002/005/006`,
  `NFR-API-001/002`, `NFR-SEC-001`, `NFR-COMP-001`.
- Acceptance: `AC-UI-004/005/006`, `AC-ALERT-002`, `AC-OPS-003/006`,
  `AC-V1-003/005/006/007/008`, `AC-TEST-001/002/003/006`.
- Contracts: existing V1 `CTR-API-001`, `CTR-UI-001`, and approved M4
  `CTR-CAP-003/007`, `CTR-ALERT-001..005`, `CTR-OPS-001/002/004/006`.

## Scope and ownership

Root wires actual module query/command ports into composition, adds closed
authenticated API schemas/routes, updates the explicit generator policy and
regenerates OpenAPI/client artifacts. UI imports only that generated client.
The approved module agents own their domain/application/persistence artifacts.
No existing operation is removed or given a changed required field or meaning.

Operations adds GET `/api/v1/operations/liveness`, `/readiness`, `/health`,
`/versions`, `/diagnostics`; all use existing `read:status`. Liveness reads
only in-process lifecycle. Other requests use a two-second deadline, actual
producer leaves and explicit unavailable/partial state. Diagnostic output is
restricted to versions, allowlisted configuration presence, bounded health
codes/counters and timestamps. It contains no account identity, process path,
provider files, credentials, exception text or environment values.

Alerts adds bounded query/history/notification/rule routes and explicit
`write:alerts` commands with browser CSRF or explicitly scoped bearer token,
idempotency and record-version preconditions. Scope resolution and precedence
stay in their owning modules. Capacity scope/forecast routes retain native
window separation and explicit insufficient-input explanations.

## Verification and rollout

Write real HTTP tests before routes. They run the actual Uvicorn service,
production migrations and actual IAM bootstrap/session authentication; an empty
installation is legitimate and must not contain invented provider telemetry.
Follow with real enrolled-owner reads and built shared-browser checks. Test
authentication, closed diagnostics, empty actual alert inventory, command CAS,
scope separation and genuine low-capacity alert delivery. Missing live states
remain Blocked. The full M4 gate remains the completion authority.

No dependency or provider write is introduced. Any schema migration is the
separately reviewed additive M4 chain and is activated only after verified
backup, including M06 association settings, and application quiescence. Rollback
preserves owner data. The default provider profiles and running user agents
remain unchanged.
