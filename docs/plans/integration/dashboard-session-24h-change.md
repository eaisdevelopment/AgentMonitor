# Dashboard 24-hour session policy change

- Status: Approved for the bounded owner-directed implementation.
- Date: 2026-10-09.
- Authority: the owner's explicit request, “session token is so short I already
  asked increase to 24h”.
- Primary owner: M01 identity and access. P01 consumes the persisted deadline
  when serializing the existing session and CSRF cookies; P02 behavior is
  unchanged.
- Requirements: `FR-IAM-001/003`, `NFR-SEC-001`, and selected
  `AC-UI-001`, `AC-TEST-002/003/006` evidence.
- Contract impact: compatible policy amendment to `CTR-IAM-003/005` V1. HTTP
  routes, DTOs, errors, OpenAPI, generated clients, database schema, and cookie
  names/attributes remain unchanged.

## Approved behavior

New dashboard browser sessions have a fixed 86,400-second idle deadline and a
fixed 86,400-second absolute deadline from successful login. The initial
deadlines therefore coincide. Accepted activity may refresh the persisted
activity time, but it never moves either deadline beyond the original absolute
deadline. Equality at the deadline remains expired. Logout, password change,
recovery, administrator revocation, and first-observed expiry remain terminal.

Existing persisted sessions retain their issued absolute deadline and issued
idle window. Normal accepted activity may continue sliding an old idle deadline
by its original 1,800-second window, but deployment never replaces that window
with 86,400 seconds and performs no database rewrite. The owner signs in once
after the new revision starts to receive the 24-hour policy. The fixed values
replace the M2 1,800-second idle and 43,200-second absolute policy for new
sessions in current builds.
Historical M2 evidence remains an accurate record of the earlier revision.

This change does not expose the two documentary configuration names as runtime
`.env` controls. A fixed policy is intentional: making security lifetime
arbitrarily configurable requires a separate typed configuration contract,
bounds, startup validation, and review.

## Security and privacy review

The longer idle window increases the time in which a stolen browser credential
could remain useful. The absolute lifetime is capped at the same 24 hours, and
the existing controls remain mandatory: at least 256 bits of OS-generated
session material; digest-only server storage; host-only `Path=/`,
`HttpOnly`, `SameSite=Strict` session cookie; separate same-origin CSRF binding;
strict Host/Origin admission; explicit permissions; server-side revocation;
password-change rotation; and no Web Storage or URL credential.

The trusted-LAN HTTP limitation remains unchanged: the network transport is not
encrypted against a LAN observer. No provider profile, account, process,
prompt, response, source content, or secret is read or changed by this policy
update.

## Implementation and verification

Owned production write set:

- `backend/src/agentmonitor/modules/identity_access/domain/policy.py`
- `backend/src/agentmonitor/adapters/persistence/identity_access/sqlite/sessions.py`

Required consistency writes cover M01 policy tests, real SQLite/HTTP tests, the
built P02 authentication scenario, the fixed configuration baseline, current
M01/P02/operator documentation, automation descriptions, and a dated evidence
record. No migration, dependency, license review, OpenAPI regeneration, or
frontend production-code change is expected.

Red must first prove that the current implementation still issues
1,800/43,200-second deadlines. Green must prove:

1. pure policy returns equal idle and absolute deadlines exactly 86,400 seconds
   after issue, remains expired at equality, caps touches at the original
   absolute deadline, and preserves the idle window already persisted for an
   older session;
2. real migrated SQLite persists the new deadlines and a real elapsed touch
   never extends them;
3. real HTTP login issues both existing cookies with a remaining maximum age
   consistent with 86,400 seconds and returns matching session timestamps;
4. the production-built Chrome authentication scenario observes the 24-hour
   session cookie, reloads the authenticated shell, and retains the existing
   storage, CSRF, logout, and hostile-origin protections;
5. documentation, planning, quality, and the applicable canonical local test
   gate pass with no hidden skip.

A literal 24-hour wall-clock expiry observation remains **Not Run** until that
elapsed scenario is deliberately executed. The normal gate verifies issuance,
persistence, boundary equality, cap behavior, and browser presentation without
claiming that a full day elapsed. The prior 30-minute elapsed result remains
historical evidence for the superseded policy.

## Operations and rollback

Deploy by building and restarting only AgentMonitor, then sign in once and
verify the new server-side and cookie deadlines through the authenticated
session API/browser. Restarting alone does not extend an old session.

Rollback restores the previous constants and documentation in a new revision;
already issued 24-hour rows remain bounded by their persisted absolute deadline
and can be revoked through the existing session controls. No destructive data
rollback is required.
