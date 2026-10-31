# Change plan: explicit permission for dashboard alert commands

- Status: **Approved for this M01 supporting increment**.
- Plan version: `1.0.0`; root integration review: 2026-09-29.
- Owner: M01 Identity/access; parent [module plan](../modules/m01-identity-access/plan-v1.md).
- Authority: active owner-authorized full M4 implementation objective.
- Requirements: `FR-ALERT-005/006`, `FR-IAM-003/006/007`, `NFR-SEC-001`.
- Acceptance: bounded `AC-ALERT-002`, `AC-V1-005`, `AC-TEST-001/002/003` support.
- Contracts: additive permission vocabulary within `CTR-IAM-001/006` V1;
  M07/P01 consumers. No whole-module or milestone acceptance.

## Outcome, scope and boundaries

Alert commands require `write:alerts`; alert/rule/notification queries require
`read:alerts`. Browser administrator sessions receive both permissions through
M01. Bearer clients require each explicitly issued scope; `write:accounts`,
`read:status` or `write:tokens` alone never authorizes an alert operation.
This decision is synchronized with the independent M07 planner before its API.

Allowed files: M01 authorization/domain scope policy, token-summary contract,
their pure tests, real
token repository regression, and this plan/evidence. Root owns later P01
policies/generation and P02 scope picker integration. No other agent owns these
files. No provider/process/credential actions and no dependency change.

## Contract, persistence and operations impact

Both scopes are additive allowlisted strings. Existing token request/response
schemas already represent scope strings; existing tokens retain exactly their
stored scopes. M01-local scope rows accept bounded strings without an enum
constraint, so no migration is needed. Existing browser origin, CSRF, scoped
delegation, expiration and credential verification stay in force. The legacy
`M2_ISSUABLE_SCOPES` constant also serves V1 increments; adding one scope does
not retrospectively change historical M2 evidence.

The actual real-token test exposed the separate published token-summary scope
allowlist after the application rules admitted issuance. Root synchronized that
same additive scope in `ApiTokenSummaryV1`; this is a contract producer change,
not permission to broaden other stored or issued scopes.

## Test-first sequence and completion

1. Pure authorization checks cover browser permission, explicit scoped bearer,
   unrelated scope denial and delegation without escalation.
2. A real migrated owner-only SQLite installation authenticates its real
   administrator, issues the narrow token through production use cases,
   reopens the repository and verifies the same scope without exposing it.
3. Run both before production changes; record their expected denied/invalid
   scope Reds, then Green and existing M01 regressions.
4. Full alert-route HTTP/browser checks belong to M07/P01/P02 integration and
   remain Not Run until the real route exists. This permission change alone
   cannot pass the alert-console or full M4 gate.

No mocked auth, tokens in logs/fixtures, invented provider accounts or telemetry.
Transient random administrator credentials remain only inside the established
real IAM test setup. Rollback removes issuance/grants for this new permission;
existing narrower tokens and business data remain intact. Stop for privilege
escalation, a changed contract/schema or sensitive output. Root reviews those
impacts before extending this approved scope.
