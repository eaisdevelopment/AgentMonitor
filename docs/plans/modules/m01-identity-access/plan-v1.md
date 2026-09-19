# Module plan: M01 — Identity and access

- Status: **Draft — approval pending; implementation is not authorized**
- Plan version: 0.2.0-draft
- Proposed module contract: `identity-access.v1` (unapproved)
- Owner: M01 identity/access implementation role (unassigned)
- Required reviewers: root/integration steward, P01 API owner, P02 UI owner, persistence/migration owner, security reviewer, test-integrity reviewer, operations owner
- Requirements: FR-IAM-001..007; supporting FR-HIST-001/003/005, FR-OPS-002/005, FR-SAFE-001/002; NFR-ARCH-001/002, NFR-API-001/002, NFR-DATA-001, NFR-TEST-001/002, NFR-SEC-001, NFR-PRIV-001/002, NFR-DOC-001, NFR-LIC-001, NFR-PLAT-001, NFR-RES-001, NFR-OBS-001, NFR-COMP-001
- Acceptance criteria: AC-V1-001..008, AC-UI-001/004/005, AC-OPS-005, AC-TEST-001..006
- Primary project risks: R-005, R-009, R-011, R-013, R-018, R-019, R-020
- Dependencies: accepted ADRs 0001, 0002, 0003, 0004, 0007, and 0008; repository foundation; centrally allocated migration chain; P01 transport contract; P02 generated-client workflow; M08 retention/recovery orchestration
- Target milestone: M1 foundation
- Approved by/date: pending

This plan is governed by the [product requirements](../../../product/requirements.md), [V1 acceptance criteria](../../../product/v1-acceptance-criteria.md), [module boundaries](../../../architecture/modules.md), [security architecture](../../../architecture/security.md), [API standards](../../../api/api-standards.md), [testing strategy](../../../engineering/testing-strategy.md), and [SDLC](../../../engineering/sdlc.md). Where this draft proposes behavior not already approved there, it labels the proposal and records a root synchronization decision in section 13.

## CS-1 Draft-alignment addendum

This `0.2.0-draft` revision adopts contract-baseline `0.2.0` and the parallel-ownership manifest as its concrete CS-1 review position. It remains Draft: no contract is Synchronized or Approved, every scenario is `Not Run`, and implementation authority is absent.

- M01 owns only AgentMonitor dashboard authentication: administrator password verification, dashboard sessions/CSRF, bearer API tokens, permissions, and IAM security events. Provider/profile authentication is outside M01. `dashboard_authentication_required` is the only normalized missing/expired/revoked dashboard-credential outcome; M01 never emits or interprets `provider_reauthentication_required`, and a provider-auth failure must not revoke a dashboard session.
- CTR-IAM-006/007 commands that reveal a password-derived session/CSRF credential or API-token plaintext declare `replay_policy = one_time_secret_non_replayable`. After commit, the same idempotency key returns `one_time_secret_not_replayable` plus safe resource ID/version/state only. Plaintext is never cached in the receipt, reconstructed, persisted, logged, serialized to an event, or returned again. Normal safe-summary mutations retain their separately declared replay policy.
- M01 consumes CTR-COMMON-007 for all credential/session field-state mappings and CTR-EVT-001 for atomic IAM event outbox plus consumer receipt/replay semantics. It implements the M08-owned CTR-OPS-006 leaf health port and CTR-OPS-007 IAM retention/export/consistency participant; those implementations expose typed, bounded, secret-free results and never transfer IAM semantic ownership to M08.
- CTR-DB-003 is consumed only for the restore workflow. M01 invalidates all restored browser sessions and API tokens against the prepared database before M08 can authorize normal readiness; M01 neither activates the database nor controls the service.
- The V1 public contract file is `backend/src/agentmonitor/contracts/identity_access_v1.py`; SQLite implementation files are only under `backend/src/agentmonitor/adapters/persistence/identity_access/sqlite/**`. M01 owns `iam_` tables and migration slots `v1_0100..v1_0199`; PLAN-DB alone serializes the common migration head.
- Alignment is verified by existing scenarios M01-DB-011, M01-HTTP-006, M01-HTTP-011, M01-HTTP-014, M01-HTTP-015, M01-OPS-003, M01-ARCH-001, and M01-ARCH-002. Their required boundary and evidence status are unchanged and remain `Not Run`.

## 1. Outcome and boundaries

### Outcome

M01 provides one local administrator with trustworthy access to AgentMonitor without a default password. It verifies a memory-hard password, creates and revokes server-side browser sessions, binds CSRF proof to those sessions, issues named least-privilege API bearer tokens once, and makes every authorization decision through an explicit permission contract.

The outcome is measurable when:

- an uninitialized installation cannot authenticate and contains no usable default credential;
- the owner can initialize the sole administrator through a local, non-logged, interactive bootstrap flow;
- the real dashboard can log in, use a server-side session, recover by returning to login after expiry, and log out;
- state-changing browser requests fail without the valid session-bound CSRF proof;
- named API tokens are returned in plaintext exactly once, stored only as verification digests, scoped, rotated, revoked, and usable in Swagger without Swagger persisting them;
- every route is authorized through a declared permission even though V1 has one human user;
- invalid, expired, revoked, malformed, or unknown credentials do not disclose which credential record exists;
- security-relevant changes are locally auditable without retaining credential values or sensitive request content;
- real SQLite, real FastAPI HTTP, and real built-browser tests demonstrate these claims without mocks, fakes, stubs, emulators, seeded identities, or bypass endpoints.

### In scope

- The single implicit V1 administrator identity and bootstrap state.
- Password policy, Argon2id verification material, parameter metadata, rehash-on-success, authenticated password change, and local recovery reset.
- Persistent login throttling and generic credential-failure behavior.
- Opaque server-side browser sessions, idle and absolute expiry, bounded activity updates, logout, bulk revocation, and rotation on credential change.
- Session-bound CSRF credential creation, verification, expiry, and revocation.
- Internal principals, authentication methods, explicit permissions, bearer scopes, authorization decisions, and safe denial reasons.
- Named API token creation, one-time reveal, verification, bounded last-use tracking, scope attenuation, rotation, expiry, and revocation.
- IAM-owned security audit records and safe query/retention ports.
- IAM tables, IAM migrations, repositories, invariants, and IAM configuration definitions.
- Published M01 application contracts consumed by P01, M08, composition/bootstrap tooling, and later authorized consumers.
- Sanitized IAM health information: initialized/uninitialized, repository available, and security-policy compatibility. It excludes counts or detail that would weaken authentication.

### Out of scope

- Provider OAuth, provider API credentials, provider login/reauthentication, email OTP, MFA, recovery codes, or provider profile management. These belong to M02/provider adapters.
- Organizations, monitored accounts, telemetry, alerts, backups, exports, and general product audit history.
- Socket binding, trusted-host parsing, Origin enforcement, CORS, security-header serialization, OpenAPI/Swagger transport configuration, HTTP routing, and cookie serialization. P01/deployment owns these boundaries while consuming M01 policy contracts.
- React login screens and browser state handling. P02 consumes only the generated API client.
- Remote binding, TLS termination, reverse proxies, multi-user identities, roles editable by users, SSO, password reset by email, WebAuthn, or external identity providers.
- Provider/process control. M01 grants no permission that kills, restarts, pauses, injects into, routes, or switches a running agent.
- A general-purpose cryptography, secrets, or audit utility package.
- Final commands for bootstrap or recovery. Commands remain `TBD` until their implementation and real operational verification.

### Ownership

M01 owns:

- `Administrator`, `PasswordVerificationMaterial`, `BrowserSession`, `CsrfBinding`, `ApiToken`, `BearerScope`, `Permission`, `Principal`, `AuthorizationDecision`, `LoginThrottle`, and `IamSecurityAuditEvent` concepts;
- all `iam_*` tables, constraints, indexes, repository ports, and centrally allocated IAM migration revisions;
- password verification and upgrade policy;
- session/token/CSRF lifecycle and credential-state transitions;
- authentication and authorization use cases;
- safe audit-event vocabulary for AgentMonitor authentication and authorization;
- its configuration schema and validation, but not global configuration loading;
- the proposed `identity-access.v1` contract family and compatibility promises after root approval;
- the module documentation, security behavior notes, test matrix, and recovery procedures specific to IAM.

### Allowed paths for a future implementation agent

These paths are proposed and require root allocation before implementation:

```text
backend/src/agentmonitor/modules/identity_access/**
backend/src/agentmonitor/adapters/persistence/identity_access/sqlite/**
backend/tests/identity_access/**
backend/tests/integration/identity_access/**
docs/modules/identity-access.md
docs/test-evidence/identity-access/**             # sanitized records only, if this path is approved
```

The following shared paths require an explicit per-change allocation from the root/integration steward:

```text
backend/src/agentmonitor/contracts/identity_access_v1.py
backend/migrations/versions/<allocated-iam-revision>.py
backend/src/agentmonitor/composition/**
openapi/generated artifacts
configuration registry and dependency manifests/lockfiles
```

### Forbidden paths and imports

The M01 implementation agent must not edit or import:

- another domain module's internals, repositories, ORM models, tables, or migrations;
- `backend/src/agentmonitor/api/**` or `frontend/**` except under a separately assigned P01/P02 integration task;
- provider/platform adapters, provider SDKs, CLIs, profile stores, local agent sessions, or process APIs;
- M08 tables to publish audit/health data, or any shared database read as a substitute for a contract;
- FastAPI, Starlette, SQLAlchemy, Alembic, Pydantic transport models, operating-system APIs, or UI code from M01 domain/application code;
- generic `utils`, shared credential helpers, handwritten frontend DTOs, or hidden test-only endpoints;
- `.env`, real credentials, provider state, or operator data.

M01 domain/application code may import Python standard-library types and approved stable contract primitives. Persistence adapters may import approved SQLAlchemy/Alembic packages and M01 repository ports. P01 may import only M01's published contracts/ports, never its implementation.

## 2. Requirements and traceability

| Requirement/AC | Planned behavior | Proposed contract | Test/scenario IDs | Evidence gate |
|---|---|---|---|---|
| FR-IAM-001 | One implicit administrator; no credential exists by default; one-time local bootstrap creates the first password hash | `BootstrapAdministratorV1`, `GetIamInitializationStateV1` | M01-DB-001/002, M01-HTTP-001, M01-OPS-001 | Real migrated SQLite plus real service startup |
| FR-IAM-002 | Argon2id password hashing with per-password random salt, policy metadata, bounded input, safe verification, and rehash-on-success | `PasswordPolicyV1`, `AuthenticateAdministratorV1`, `ChangeAdministratorPasswordV1` | M01-CRYPTO-001..004, M01-HTTP-002 | Real admitted Argon2 implementation; no replacement verifier |
| FR-IAM-003 | Opaque HTTP-only session cookie; server-side revocation; SameSite policy; session-bound CSRF cookie/header proof for unsafe methods | `AuthenticateAdministratorV1`, `ResolveBrowserSessionV1`, `VerifyCsrfV1`, `LogoutSessionV1` | M01-DB-003..006, M01-HTTP-003..010, M01-BROWSER-001..004 | Real SQLite, real FastAPI socket, built UI/browser |
| FR-IAM-004 | Named scoped bearer tokens support create, list, rotate, expire, and revoke; plaintext is emitted in one response only | `CreateApiTokenV1`, `RotateApiTokenV1`, `RevokeApiTokenV1`, `ListApiTokensV1` | M01-DB-007..011, M01-HTTP-011..016, M01-BROWSER-005 | Real DB/HTTP/browser; artifact inspection |
| FR-IAM-005 | Store only cryptographic token verification digests plus non-secret selector/fingerprint metadata | `ResolveBearerTokenV1`, persistence contract | M01-DB-008, M01-SEC-001/002 | Database and backup inspection; secret scan |
| FR-IAM-006 | OpenAPI bearer scheme and Swagger authorization use a real M01 token; authorization persistence is disabled | P01 OpenAPI contract consuming `ResolveBearerTokenV1` | M01-HTTP-017, M01-BROWSER-006 | Real generated OpenAPI and real Swagger/browser |
| FR-IAM-007 | Deployment binds loopback; P01 enforces canonical Host/Origin; M01 rejects session-authenticated unsafe requests without CSRF | P01 boundary plus `VerifyCsrfV1` | M01-HTTP-018..021, M01-OPS-002 | Real loopback service and real cross-origin browser page |
| FR-HIST-001/003/005 | IAM audit history uses UTC, retains 365 days, and purges through an auditable M01-owned operation | `ListIamSecurityEventsV1`, `PurgeExpiredIamRecordsV1` | M01-PURE-005, M01-DB-012/013 | Pure cutoff policy plus real DB deletion transaction |
| FR-OPS-002/005 | Expose safe initialized/repository-policy state; diagnostics, backups, and exports never contain plaintext credentials | `GetIamHealthV1`, safe audit query | M01-HTTP-022, M01-SEC-003, M01-OPS-003 | Real diagnostics/export/backup integration inspection |
| FR-SAFE-001/002 | IAM mutations affect only AgentMonitor credentials; no provider or running-agent control surface exists | Entire contract surface | M01-ARCH-001, M01-SEC-004 | Import/API/contract review and absence check |
| NFR-ARCH-001/002 | Isolated module, typed V1 contracts, owned tables, no circular/private imports | `identity-access.v1` | M01-ARCH-001/002 | Automated import-boundary check plus reviewer inspection |
| NFR-API-001/002 | P01 maps contracts to `/api/v1`; frontend consumes generated client only | P01/OpenAPI | M01-HTTP-023, M01-BROWSER-007 | OpenAPI validation/diff and generated-client compile |
| NFR-DATA-001 | File-backed SQLite migrations/repositories avoid domain-level SQLite semantics and document PostgreSQL differences | IAM migration/repository contracts | M01-DB-001..013 | Fresh migration, query/constraint, portability review |
| NFR-TEST-001/002; AC-TEST-001..006 | Red-green-refactor at real claimed boundaries; no doubles, seeded identities, or hidden skipped tests | Evidence records | All M01 tests | Independent test-integrity review |
| NFR-SEC-001; AC-V1-005/007 | Least privilege, redaction, rate limits, secret-safe storage, dependency review, and threat tests | Permission/auth/audit contracts | M01-SEC-001..009 | Security review and real artifact scans |
| NFR-PRIV-001/002 | IAM stores only required authentication metadata and sends no analytics/crash telemetry | Persistence and logging allowlists | M01-SEC-003/010 | DB/log/network inspection |
| NFR-DOC-001; AC-V1-006 | Contracts, operations, recovery, test evidence, and limitations remain documented | Documentation outputs | M01-DOC-001 | Documentation review/link check |
| NFR-LIC-001 | Every non-standard dependency passes admission before import | Dependency admission record | M01-DEP-001 | License/security/SBOM gate |
| NFR-PLAT-001 | Core M01 is platform-neutral; bootstrap/recovery adapters receive Linux verification and macOS remains architecturally valid | Local operator adapter contract | M01-OPS-001/004 | Real Linux; macOS Passed or visibly Blocked |
| NFR-RES-001 | Repository/audit failure fails authentication closed without taking down unrelated read-only service health | Typed failures | M01-DB-014, M01-HTTP-024 | Real locked/unavailable isolated SQLite resource |
| NFR-OBS-001 | Correlation-aware structured events contain safe IDs/codes, never credentials/content | Audit/log policy | M01-SEC-005/006 | Captured local log and audit inspection |
| NFR-COMP-001; AC-V1-003/004 | Contract/schema versions and migration compatibility are explicit | `identity-access.v1`, IAM revisions | M01-ARCH-002, M01-DB-001/015, M01-HTTP-023 | Contract/API/schema compatibility gates |
| AC-UI-001 | Real user logs in/out, encounters real expiry, returns to login, and rotates a real persisted API token | Session/token contracts through P01/P02 | M01-BROWSER-001..006 | Built UI in real browser against real service/database |
| AC-UI-004/005 | Login/token UI is keyboard-accessible and represents unauthorized/expired/forbidden/throttled states truthfully | Generated API problem contracts | M01-BROWSER-007/008 | Real browser accessibility and state test |
| AC-OPS-005 | Password recovery, security-secret rotation, restore invalidation, and upgrade procedures are exercised | Recovery ports/runbook | M01-OPS-003..006 | Real installed-service procedure evidence |

### Approved interpretation versus proposal

- Approved: V1 has one administrator and password-only dashboard login. This plan therefore proposes an implicit administrator with no username/email field; a password is the only human login credential.
- Approved: there is no default password and plaintext password/token storage is forbidden.
- Proposed: initialization and forgotten-password recovery occur only through an interactive local operator entry point using a controlling TTY and exclusive database access. No web setup endpoint, command-line password argument, email recovery, or long-lived bootstrap password in `.env` is planned.
- Proposed: browser sessions use opaque random credentials and server-side state rather than JWTs.
- Proposed: API bearer tokens use high-entropy opaque secrets and fast cryptographic digests; the memory-hard primitive is reserved for human-chosen passwords.
- Proposed: default timeout, rate-limit, password-length, cookie, scope, and one-time-secret retry policies below require approval at contract synchronization.

## 3. Domain design

### Entities and value objects

#### Administrator

- Exactly zero or one record exists in V1.
- `administrator_id` is an opaque stable internal ID; it is never derived from a username, email, host user, or display label.
- No username/email is required for authentication. The principal display label is non-authoritative and may be a fixed localized UI label.
- State is `uninitialized` when no record exists and `active` after bootstrap. Deletion/deactivation is not a V1 operation.
- The record owns the current password-verification material and optimistic `record_version`.

#### PasswordVerificationMaterial

- Uses Argon2id through an admitted library, encoded in a standard PHC string containing algorithm/version, random salt, and work parameters.
- Password plaintext exists only in bounded request/TTY memory for verification or hashing and is never stored, logged, audited, serialized into diagnostics, accepted via a command-line argument, or returned.
- Bootstrap/change policy proposal: at least 15 Unicode code points, at most 1,024 UTF-8 bytes, no composition rule, allow paste/password managers, and compare exact entered Unicode without implicit normalization. These values require security approval.
- Login does not reject a plausible wrong password early based on the bootstrap minimum. All bounded, syntactically accepted login candidates reach one real Argon2 verification when the installation is initialized and the request is not already throttled.
- The hasher policy has a non-secret version. Successful verification checks whether parameters require rehash and replaces material atomically without changing the administrator identity.
- Exact Argon2id parameters are selected by a real startup benchmark on the supported workstation class, constrained by an approved minimum floor and maximum login resource budget. They are versioned security policy, not arbitrary user tuning.

#### BrowserSession

- The browser credential is at least 256 bits from the OS cryptographic random source, encoded URL-safely, and is never a signed self-contained authorization document.
- A public random selector supports bounded lookup; the database stores the selector and a cryptographic digest of the full credential, never the credential.
- Fields include stable session ID, administrator ID, credential selector/digest, issued time, last-activity time, idle-expiry time, absolute-expiry time, revocation time/reason, CSRF digest, and optimistic version.
- Proposed installed defaults are 30 minutes idle and 12 hours absolute. Defaults and permitted ranges require root/security approval.
- Expiry is evaluated at request authentication. Equality at the expiry instant is expired. Absolute expiry never slides. Idle expiry slides only on accepted authenticated activity and never beyond absolute expiry.
- `last_activity_at` persistence is coalesced (proposed once per 60 seconds) to avoid a write on every read. Authorization uses the calculated current deadline, not stale client state.
- A login always creates a fresh session and CSRF binding. Password change/recovery rotates or revokes sessions as specified below. Session fixation is not accepted.

#### CsrfBinding

- A separate random CSRF credential is created with a session. Its cryptographic digest is stored on the session row.
- Proposed browser mechanism: the CSRF credential is sent in a non-HTTP-only, same-origin, `SameSite=Strict` cookie and repeated by the generated client in `X-CSRF-Token`. The authentication session cookie remains HTTP-only.
- For a state-changing request authenticated by browser session, M01 requires the cookie value, header value, and stored digest to agree using safe comparison. Missing, malformed, stale, or mismatched proof is denied.
- Login/bootstrap are not session-authenticated and therefore do not consume CSRF. P01 must still enforce the canonical browser Origin for login. Bearer-only requests do not require CSRF because the credential is not ambient.
- If both a browser session and bearer credential are supplied, P01 rejects the ambiguous request rather than selecting one.
- The CSRF binding expires and is revoked with the session. Logout clears both cookies. Password change issues a new session and CSRF value. V1 does not expose a read endpoint that returns an existing CSRF secret.

#### LoginThrottle

- V1 uses a persistent installation-global bucket because every permitted network peer is loopback and there is one administrator. P01 may additionally supply a normalized safe source class; raw IP, user agent, password characteristic, or request body is not retained.
- Proposed defaults: five failed attempts within 15 minutes; a 30-second first lock with exponential increases capped at 15 minutes; a successful login resets the active failure window. Values require approval and configuration validation.
- Counter/lock transitions are atomic and survive service restart. Throttled requests return a bounded `Retry-After` and do not run Argon2, preventing password-hash denial of service.
- Every allowed initialized login performs exactly one real verifier call. Wrong credentials share one status, code, title, body shape, and audit classification. The service does not promise network-level constant time; it avoids identifier existence disclosure, unsafe comparisons, and credential-specific early exits.
- Uninitialized state is a distinct operational condition (`iam_setup_required`), not disguised as a wrong password. Because there is no username, no administrator-name enumeration exists.

#### ApiToken

- Proposed external format: a version marker, a random public selector, and a random secret containing at least 256 bits of entropy. The final syntax requires contract approval.
- Store only token ID, name, safe display prefix/fingerprint, selector, cryptographic verification digest, scopes, issue/expiry/last-use/revocation/rotation metadata, and optimistic version.
- Token plaintext is present only in the successful create/rotate application result. P01 marks the response `Cache-Control: no-store`; logging/telemetry/error capture excludes it. No retry cache stores it.
- Names are trimmed, bounded, non-secret operator labels. This draft permits duplicate names because IDs are authoritative and portable active-name uniqueness is unnecessary; P02 must display safe fingerprint and date to distinguish them.
- Unknown/malformed selectors, digest mismatch, revoked tokens, and expired tokens produce the same external authentication failure. The verifier hashes bounded input and uses safe comparison against a real or non-secret dummy digest so record existence is not exposed by application branches.
- Last-use persistence is coalesced (proposed once per 60 seconds). Concurrent requests cannot reactivate expiry/revocation or move `last_used_at` backward.

#### Scope, permission, and Principal

- `PrincipalV1` includes opaque principal ID, authentication method (`browser_session` or `api_bearer`), optional safe credential ID, effective permissions, issued/authenticated timestamps, and optional absolute expiry. It contains no raw credential, digest, password metadata, CSRF value, or provider identity.
- Browser-session principals receive the fixed V1 administrator permission set, but routes still call authorization explicitly.
- Proposed bearer scopes follow the security baseline: `read:status`, `read:accounts`, `read:telemetry`, `read:diagnostics`, `write:configuration`, `write:accounts`, `write:alerts`, `write:reauth`, `write:tokens`, and `write:backup`.
- A centrally synchronized mapping converts bearer scopes to fine-grained internal `PermissionV1` values. Routes declare permissions, not role checks or `is_admin` shortcuts.
- Unknown requested scopes are rejected. Adding a scope is a compatible contract addition only when older consumers tolerate unknown strings and no existing scope gains broader meaning.
- Token management obeys attenuation: a bearer principal can create/manage only credentials whose effective scopes are a subset of its own and only when it has `write:tokens`. The browser administrator can manage all V1 tokens. This proposed rule requires root approval.
- `AuthorizationDecisionV1` returns allowed/denied, stable safe reason code, required permission, and correlation metadata; it never returns policy internals or credential status.

#### IamSecurityAuditEvent

- Immutable, append-only security facts owned by M01: initialization, login success/failure-window/throttle activation, session creation/revocation, password change/recovery, API-token creation/rotation/revocation, CSRF denial, authorization denial, credential-wide invalidation, retention, and policy incompatibility.
- Event payload is an allowlisted schema of safe IDs, event/outcome codes, correlation ID, authentication method, target type/ID, count where aggregated, and UTC timestamps.
- It excludes password/token/CSRF values or lengths, hashes, cookies, authorization headers, request bodies, IP/user-agent detail, token names, filesystem paths, stack traces, emails, and provider/account data.
- Repeated invalid/throttled requests are summarized in bounded attempt-window records and transition audit events rather than creating unlimited audit rows per request. A successful login and each privileged credential mutation remain individual events.

### State machines

```text
Installation IAM
  uninitialized --bootstrap--> initialized
  initialized --password change/recovery--> initialized (new material/version)
  initialized --delete/deactivate--> forbidden in V1

Browser session
  active --idle deadline--> expired
  active --absolute deadline--> expired
  active --logout/admin recovery/bulk revoke--> revoked
  active --password change--> revoked, followed by a new session when change was online
  expired/revoked --any input--> terminal; never active again

API token
  active --expiry deadline--> expired
  active --explicit revoke--> revoked
  active --rotate--> rotated/revoked + distinct active successor
  expired/revoked/rotated --any input--> terminal; never active again

Login throttle
  clear --failed verification--> counting
  counting --threshold--> locked
  counting --successful verification/window elapsed--> clear
  locked --deadline elapsed--> counting or clear per approved algorithm
```

### Time and clock semantics

- Persist and exchange timezone-aware UTC instants; API representation is RFC 3339 with explicit `Z`/offset.
- Domain expiry/retention policies accept an explicit `as_of` instant in pure tests. Production application services obtain UTC time from the approved composition primitive; they do not read a patched global clock.
- Security decisions use one captured `as_of` per transaction/request to avoid boundary drift.
- A record is inactive when `as_of >= expires_at` or `revoked_at is not null`.
- Wall-clock rollback must not extend an already persisted absolute deadline. Operations logs anomalous backward movement; monotonic elapsed time may protect in-process rate calculations but is not persisted as an instant.

### Identity, correlation, and deduplication

- Administrator, session, API token, audit event, and idempotency IDs are independent opaque random identifiers.
- Credential selector/prefix/fingerprint is not an identity and grants no authority.
- Correlation IDs originate at P01 and are passed unchanged into M01 audit records after validation.
- A bootstrap singleton constraint and transaction prevent duplicate administrators.
- Each idempotent mutation is deduplicated by principal, operation family, and caller-supplied idempotency key digest; reused keys with a different canonical request fingerprint are conflicts.

### Concurrency and idempotency

- Bootstrap is a single transaction guarded by a database singleton constraint. Exactly one of concurrent attempts succeeds; the other receives `administrator_already_initialized` without replacing material.
- Login-throttle updates are atomic. Concurrent failures cannot lose increments or bypass a lock.
- Session activity uses compare-and-set/version semantics and a touch interval. Concurrent requests may coalesce to one write; none may extend beyond absolute expiry or resurrect revocation.
- Logout and token revocation are idempotent for an authenticated caller. A second revoke returns the current revoked summary or `204` according to the approved P01 schema, without a second state transition.
- Password changes compare the administrator record version, update the hash, revoke affected sessions, and append audit facts in one transaction.
- Token rotation creates the successor and terminally rotates the predecessor in one transaction. Plaintext is generated immediately before commit and never placed in an idempotency record.
- One-time-secret mutations use an idempotency key to prevent duplicate token creation and declare `replay_policy = one_time_secret_non_replayable`. A replay after the original success returns `409 one_time_secret_not_replayable` with safe created-resource metadata; the owner must deliberately rotate/recreate. Plaintext is neither cached in the receipt nor replayed.
- Repository adapters translate transient SQLite busy conditions into a typed retryable failure with a bounded internal retry policy approved by persistence; they never convert a failed write into authentication success.

### Degradation and recovery

- If IAM persistence is unavailable or schema/policy is incompatible, authentication fails closed. P01 may continue a minimal non-sensitive liveness endpoint under its own approved disclosure policy, but protected resources do not become public.
- Audit-write failure for a required security transition fails the transition unless the security reviewer approves a transactional outbox design. Login-read authentication may not silently succeed when its mandatory session/audit creation failed.
- Revoked/expired sessions and tokens are never recovered. The user returns to login or creates/rotates a token with another authorized credential.
- Restore of an older database may resurrect previously active credential records. Before normal readiness after restore, M08 must invoke an approved M01 recovery operation that revokes every browser session and API token and records the restore invalidation. This cross-module contract is unresolved.

## 4. Public contracts

All names and versions below are proposals for contract synchronization. Sensitive credential-issue results are application-boundary types with redacted `repr`/serialization rules; only P01/composition may consume them.

The exact public-contract projection is:

| Contract ID | Baseline name | Plan surface | Version / current maturity | Consumers |
|---|---|---|---|---|
| CTR-IAM-001 | `PrincipalAndPermissionV1` | `PrincipalV1`, `PermissionV1` and principal resolution | 1.0.0 / `proposed_aligned` | M02, M04, M06, M07, M08, P01, P02 |
| CTR-IAM-002 | `AuthorizationDecisionV1` | `AuthorizationDecisionV1`, `AuthorizePrincipalV1` | 1.0.0 / `proposed_aligned` | M02, M04, M06, M07, M08, P01 |
| CTR-IAM-003 | `BrowserSessionAndCsrfV1` | browser-session resolution, CSRF verification and logout | 1.0.0 / `proposed_aligned` | P01, P02 |
| CTR-IAM-004 | `AdministratorAuthenticationAndRecoveryV1` | bootstrap, authenticate, password change and recovery | 1.0.0 / `proposed_aligned` | P01, P02, DEP, M08 |
| CTR-IAM-005 | `SessionQueryAndRevocationV1` | session list and revocation ports | 1.0.0 / `proposed_aligned` | P01, P02, M08 |
| CTR-IAM-006 | `ApiTokenLifecycleV1` | API-token list/create/rotate/revoke and bearer resolution | 1.0.0 / `proposed_aligned` | P01, P02 |
| CTR-IAM-007 | `CredentialIssueAndSafeSummaryV1` | one-time credential issue plus safe summaries | 1.0.0 / `proposed_aligned` | P01, P02 |
| CTR-IAM-008 | `IamSecurityEventRetentionAndRestoreV1` | audit query, purge, health and post-restore invalidation | 1.0.0 / `proposed_aligned` | M08, DB, DEP, INT |

The machine-exact producer and consumer sets are bound in
`contract-adoption.toml`. Approval remains a Definition-of-Ready condition.

### Published data contracts

| Contract | Required fields and invariants | Consumers | Compatibility promise |
|---|---|---|---|
| `PrincipalV1` | principal ID, auth method, safe credential ID, effective permissions, authenticated/issued/expiry instants | P01 and application authorization | Additive optional fields only within V1; never credential material |
| `SessionSummaryV1` | session ID, issued/last-activity/idle/absolute expiry, state, current-session flag | P01/P02 via API mapping | State meaning is stable; new unknown-tolerant states additive |
| `ApiTokenSummaryV1` | token ID, name, safe prefix/fingerprint, scopes, issued/expiry/last-used/revoked/rotated metadata, version | P01/P02/Swagger clients | No verification digest or plaintext; nullable/unknown explicit |
| `PermissionV1` | stable permission key and description | P01 route declarations | Existing permission meaning never broadens silently |
| `AuthorizationDecisionV1` | allowed, stable reason code, required permission, principal ID, correlation ID | P01, application orchestrators | Denial reasons safe and versioned |
| `IamInitializationStateV1` | `uninitialized`/`initialized`/`incompatible`, safe policy/schema versions | composition, P01 setup UX, M08 health | Reveals no hash parameters beyond approved public policy version |
| `IamHealthV1` | repository reachability, initialization state, policy compatibility, retention health | M08/P01 | No credential/session/token counts unless separately approved |
| `IamSecurityEventViewV1` | safe event metadata and cursor fields | M08 diagnostics/audit UI through P01 | Strict allowlist; no free-form untrusted metadata |

### Published command/query ports

| Port | Input/output | Preconditions and authorization | Errors/outcomes | Idempotency |
|---|---|---|---|---|
| `GetIamInitializationStateV1` | no credential input → initialization state | local application only | repository unavailable/incompatible | Safe repeatable query |
| `BootstrapAdministratorV1` | bounded plaintext supplied through protected local input → administrator summary | installation uninitialized; controlling local operator context; no network caller | invalid password policy; already initialized; persistence/audit failure | DB singleton; no secret replay |
| `AuthenticateAdministratorV1` | bounded password + safe source class + correlation ID → one-time session/CSRF issue result | initialized and not throttled; P01 already accepted Host/Origin | invalid credentials; throttled with retry time; setup required; unavailable | Each success intentionally creates one fresh session; login endpoint is not replay-idempotent |
| `ResolveBrowserSessionV1` | raw bounded session credential + `as_of` → principal/session summary | P01 only; credential never logged | `dashboard_authentication_required`; unavailable | Read plus coalesced monotonic activity touch |
| `VerifyCsrfV1` | authenticated session ID + cookie/header proof + `as_of` → valid/denied | unsafe session-authenticated operation | generic CSRF validation failed; session inactive | Repeatable within active session |
| `LogoutSessionV1` | current session ID + version/correlation → revoked | valid browser principal and CSRF for actual mutation | safe unavailable; no record-existence disclosure | Idempotent terminal transition |
| `ListSessionsV1` | pagination/filter limited to own administrator → summaries | browser admin; bearer access is not proposed for V1 | forbidden; invalid cursor | Safe paginated query |
| `RevokeSessionV1` / `RevokeAllSessionsV1` | target or policy → revocation summary | explicit credential-management permission; CSRF for browser | not found for authorized caller; conflict only on invalid request | Idempotent |
| `ChangeAdministratorPasswordV1` | current and new bounded passwords → fresh session issue result | browser session, CSRF, current password re-verification | invalid current credential; password policy; stale version; throttled/unavailable | Idempotency key does not retain password or response secret; replay returns safe conflict |
| `RecoverAdministratorPasswordV1` | new password via protected local input → recovery result | exclusive local recovery context; service quiesced per runbook | uninitialized; policy; database lock; audit failure | One committed version transition; retry requires fresh input |
| `ResolveBearerTokenV1` | raw bounded bearer credential + `as_of` → principal/token summary | P01 only | one generic `dashboard_authentication_required` outcome | Read plus coalesced monotonic use touch |
| `ListApiTokensV1` | cursor/filter → token summaries | `write:tokens`/mapped permission | forbidden; invalid cursor | Safe query |
| `CreateApiTokenV1` | name, scopes, optional expiry, idempotency key → one-time token issue | browser admin or attenuated bearer with token-management permission | invalid scope/name/expiry; scope escalation; idempotency conflict; unavailable | Creates once; secret cannot be replayed |
| `RotateApiTokenV1` | target ID/version, optional replacement metadata, idempotency key → one-time token issue | token-management permission; attenuation for bearer caller | not found; terminal target; stale version; escalation; one-time replay conflict | Atomic predecessor/successor transition |
| `RevokeApiTokenV1` | target ID/version → terminal summary | token-management permission; attenuation for bearer caller | not found; stale non-terminal update | Repeated revoke is successful/idempotent |
| `AuthorizePrincipalV1` | principal + required permission + subject context key → decision | authenticated principal | denied with stable safe reason | Pure deterministic decision for fixed inputs |
| `ListIamSecurityEventsV1` | bounded cursor/time/event filters → safe event views | dedicated diagnostic/audit permission | invalid filter/cursor; forbidden | Safe paginated query |
| `PurgeExpiredIamRecordsV1` | explicit UTC cutoff and batch limit → counts/audit ID | M08 authorized scheduler/operation | active record invariant; unavailable | Re-running deletes no additional ineligible rows |
| `InvalidateCredentialsAfterRestoreV1` | restore ID/correlation → revocation counts | M08 recovery orchestration before readiness | already handled; unavailable | One effect per restore ID |
| `GetIamHealthV1` | no secret input → safe state | M08/P01 internal application | unavailable/incompatible | Safe repeatable query |

### Credential issue result rules

- `SessionCredentialIssueV1` contains raw session and CSRF credentials only long enough for P01 to set cookies; default string/repr/debug serialization must redact them. It is not persisted or placed on the event bus.
- `ApiTokenCredentialIssueV1` contains `ApiTokenSummaryV1` plus plaintext bearer token. It is returned only for a newly committed create/rotation. It is not recoverable, queryable, logged, included in OpenAPI examples, or retained for idempotency replay.
- P01 must clear local references after response construction to the extent Python permits; the design does not claim guaranteed memory erasure.

### Consumed ports

| Owner/contract | Version/range | M01 use | Failure behavior |
|---|---|---|---|
| Foundation ID/time/correlation primitives | Proposed V1 | opaque IDs, explicit UTC instants, validated correlation IDs | fail startup/operation; never invent malformed IDs |
| M01 repository/unit-of-work adapters | Private port V1 | persistent invariants and transactions | typed unavailable/conflict/corrupt outcomes; fail closed |
| Approved password-hasher adapter | Private port V1 | Argon2id hash/verify/rehash decision | hasher failure is internal unavailable, never invalid credential success |
| Cryptographic random/digest primitives | Private port V1 | sessions, CSRF, bearer tokens, IDs | generation failure aborts transaction and secret issuance |
| Configuration registry/loader | Foundation contract TBD | validated non-secret policy and secret-presence state | invalid security configuration prevents protected-service readiness |
| CTR-COMMON-007 `FieldAvailabilityV1` | Foundation | explicit optional/unknown/unavailable state in safe summaries | invalid combinations rejected; zero/absence never conflated |
| CTR-EVT-001 | PLAN-INT governance/PLAN-DB infrastructure | IAM outbox, delivery receipts, replay/checkpoints | producer commit is atomic; consumer failure cannot erase security fact |
| CTR-OPS-006/007 | M08 semantic protocols | publish leaf health; implement IAM retention/export/consistency participant | bounded safe failure; M08 receives no table or credential access |
| CTR-DB-003 | PLAN-DB | prepared-restore database reference/receipt for mandatory credential invalidation | IAM remains not-ready when invalidation or typed database phase fails |

M01 intentionally consumes no registry, provider, capacity, runtime, alerting, or UI contract.

### M01/P01 boundary allocation

| Concern | M01 owns | P01/deployment owns |
|---|---|---|
| Network exposure | Auth policy assumes accepted local request context | Bind only approved loopback addresses; reject non-loopback configuration in local mode |
| DNS rebinding/host | No direct header parsing | Exact canonical Host allowlist, no wildcard, ignore untrusted forwarding headers |
| Cross-origin browser calls | Determines which authenticated mutations require CSRF | Exact public Origin validation before login/session mutation; no wildcard CORS |
| Credential extraction | Verifies bounded credential values | Parse Cookie/Authorization, reject duplicates/ambiguity, impose header/body limits |
| Cookies | Session/CSRF lifecycles and attributes required by policy | Serialize/clear exact cookies and flags; TLS-aware `Secure` behavior |
| HTTP/OpenAPI | Typed outcomes and permissions | Routes, status/problem mapping, operation IDs, security schemes, docs protection |
| Security headers | States required policy outcomes | CSP, frame denial, content-type/referrer protections, cache controls |
| Rate-source context | Global throttle policy and safe source-class input | Establish trustworthy source class; never trust proxy headers in V1 |
| Swagger | Valid bearer principal/scope decisions | Protect docs, define bearer scheme, set `persistAuthorization=false` |

Proposed cookie policy for synchronization:

- session cookie: `HttpOnly`, `SameSite=Strict`, `Path=/`, no `Domain`, bounded `Max-Age` no later than absolute expiry; `Secure` whenever TLS is present;
- CSRF cookie: same attributes except intentionally not `HttpOnly`, because the generated client must echo it in a header;
- local plain HTTP cannot use `Secure`; P01 must never infer that loopback makes other controls optional;
- no credential is stored in `localStorage` or `sessionStorage`;
- exact cookie names and whether a TLS-only deployment may use a `__Host-` prefix remain P01 contract decisions.

### Proposed API outcome mapping requiring P01 approval

| M01 outcome code | Proposed HTTP | External behavior |
|---|---:|---|
| `iam_setup_required` | 503 | Login/setup UI can direct the local owner to the bootstrap runbook; no hash detail |
| `invalid_credentials` | 401 | Same response for every bounded wrong password |
| `login_throttled` | 429 | Safe `Retry-After`; no attempt/count detail |
| `dashboard_authentication_required` | 401 | Same for malformed/unknown/expired/revoked dashboard session or bearer credential; never used for provider reauthentication |
| `multiple_authentication_credentials` | 400 | P01 rejects cookie plus bearer ambiguity before M01 authorization |
| `csrf_validation_failed` | 403 | Same for absent/malformed/mismatch; no token detail |
| `permission_denied` | 403 | Required permission may be named; held scopes need not be echoed |
| `administrator_already_initialized` | 409 | Bootstrap only; does not alter current hash |
| `password_policy_violation` | 422 | Safe rule codes only; never echo submitted value |
| `scope_escalation_denied` | 403 | Bearer caller cannot mint/manage broader token |
| `api_token_not_found` | 404 | Only after an authorized token-management principal is established |
| `credential_state_conflict` | 409 | Rotate/change target is terminal or current version conflicts |
| `one_time_secret_not_replayable` | 409 | Prior resource ID/summary may be returned; secret never replayed |
| `idempotency_key_reused` | 409 | Same key was used for a different canonical request |
| `iam_repository_unavailable` | 503 | Correlation ID only; no SQL/path detail |
| request/schema error | 400/413/422 | Owned by P01 validation; bounded safe field reasons |

For logout, the proposal is: a valid session mutation requires CSRF and returns `204`; an absent/invalid session returns `204` while P01 clears presented cookies, but no server record is changed. Host/Origin still apply. This provides idempotent local cleanup without exposing session state and requires security approval.

### Contract change assessment

This plan proposes new V1 contracts; it does not change an already implemented contract. Before approval, the root/integration steward must:

1. freeze the shared primitive types and exact names;
2. reconcile every permission/scope with P01 route plans and all module use cases;
3. approve the browser/CSRF/cookie transport handshake with P01/P02;
4. approve HTTP/problem and one-time-secret retry semantics;
5. approve M08 retention, audit, restore-invalidation, and health seams;
6. allocate migration revisions and shared contract paths;
7. decide whether an ADR is required for the bootstrap/recovery mechanism or token rotation semantics.

No implementation agent may publish these proposals privately or compensate with direct P01/M08/table access.

## 5. Data and persistence

### Owned tables

Names are proposed; exact DDL is approved with the persistence review.

#### `iam_administrator`

- `singleton_key` with a database check enforcing the sole V1 slot;
- opaque `administrator_id` primary/business ID;
- Argon2id PHC verification string and non-secret hash-policy version;
- `password_changed_at`, `created_at`, `updated_at`, `record_version`;
- no username/email, password plaintext, password hint, provider identity, or recovery answer.

#### `iam_browser_session`

- `session_id`, `administrator_id` (within-module FK), random selector, credential digest, CSRF digest;
- issued/last-activity/idle-expiry/absolute-expiry timestamps;
- nullable revocation timestamp and safe reason enum;
- `record_version`, created/updated timestamps;
- no cookie plaintext, IP, user-agent, browser fingerprint, URL, or request content.

#### `iam_api_token`

- `api_token_id`, `administrator_id`, bounded operator name, public selector, safe prefix/fingerprint, verification digest;
- issued/expiry/last-used/revoked timestamps, safe revocation reason;
- nullable `rotated_from_token_id`/`replacement_token_id` within module;
- `record_version`, created/updated timestamps;
- no token plaintext.

#### `iam_api_token_scope`

- within-module FK to token and canonical scope key;
- composite primary/unique constraint preventing duplicate scope;
- normalized rows avoid SQLite JSON-query semantics and keep PostgreSQL portability.

#### `iam_login_throttle`

- bounded bucket ID/source class, window start, failure count, consecutive lock count, locked-until, updated time, version;
- contains no raw source address, user-agent, or credential characteristic.

#### `iam_idempotency_record`

- principal/operation/key digest, canonical request fingerprint, state, affected resource ID, created/expiry timestamps;
- never stores request secrets or one-time response plaintext;
- retention is short and configuration-owned by M01.

#### `iam_security_audit_event`

- immutable event ID/type, occurred/recorded timestamps, actor principal/auth method, target type/ID, safe outcome/reason code, correlation ID, safe schema version;
- strictly typed optional integer count and allowlisted code metadata; no unrestricted text/payload dump.

### Keys, constraints, and indexes

- Unique administrator singleton and administrator ID.
- Unique session selector and verification digest; indexes supporting credential lookup, administrator plus active/revoked state, absolute/idle expiry, and retention cutoff.
- Unique API-token selector and verification digest; indexes for administrator plus issue order, expiry/revocation, replacement relationship, and retention cutoff.
- Composite primary key on token scope.
- Unique throttle bucket and atomic version.
- Unique `(principal_id, operation_key, idempotency_key_digest)` plus expiry index.
- Audit indexes on `(occurred_at, event_id)`, `(actor_principal_id, occurred_at)`, and `(event_type, occurred_at)` for bounded cursor queries.
- Database checks enforce timestamp ordering where portable, nonempty bounded names/codes, supported states, nonnegative counts, and terminal-state fields. Domain validation remains authoritative across databases.
- No foreign key crosses the M01 boundary. No other module queries these tables.

### Transaction boundaries

- Bootstrap: administrator + audit event atomically.
- Successful login: throttle success transition + session/CSRF row + audit event atomically.
- Failed login: throttle transition + bounded audit transition atomically; no session row.
- Logout/revoke: terminal credential transition + audit event atomically.
- Password change/recovery: verify/replace material + required session revocations + audit event(s) atomically. Recovery's API-token invalidation policy is an approval decision.
- API-token create: token/scopes + idempotency outcome + audit event atomically; plaintext never enters the transaction data.
- Rotation: successor/scopes + predecessor terminal transition + idempotency outcome + audit event atomically.
- Retention: bounded batch transaction plus completion audit summary; it cannot delete the administrator or active credentials.

### Migration policy

- The first IAM revision creates only M01 tables and constraints through the real Alembic chain allocated by the integration steward.
- Fresh install and every supported upgrade path use a real file-backed SQLite database. Installed startup never creates tables implicitly.
- Shared revisions are immutable after use. Every revision declares M01 ownership, expected locking/data size, backup prerequisite, validation query, and recovery.
- A destructive downgrade that drops credential/audit state is not presented as safe. Recovery uses a verified backup and compatible binary unless a genuinely safe downgrade is implemented and tested.
- Schema-newer-than-binary and incompatible hash/scope policy prevent writable readiness; they do not silently discard records.
- Portability review covers timestamp encoding, booleans/enums, binary/text digests, unique/partial-index behavior, transaction isolation, and upsert/locking differences.

### Retention and deletion proposal

- Active administrator and active credential metadata are retained while active.
- Revoked/expired session and token summaries, IAM security events, and required authentication history are retained for 365 days, satisfying FR-HIST-001.
- Expired idempotency records: proposed 24 hours after terminal completion.
- Cleared login-throttle buckets: proposed 30 days, while security transition events retain 365 days.
- Credential digests are sensitive verification material. Whether they are nulled after terminal transition or retained until row expiry requires a security/persistence decision; external behavior must remain generic either way.
- Cutoff calculation is a pure explicit-`as_of` policy. Deletion is executed against the real database in bounded batches and is itself audited.
- Backup/restore follows M08 policy. IAM verification material is present in the database backup and must be treated as sensitive even though plaintext credentials are absent.

### Repository interfaces

Private repository ports express domain operations rather than generic CRUD: claim singleton bootstrap, load administrator for verification, commit failed/successful attempt, create/resolve/touch/revoke session, create/resolve/touch/rotate/revoke token, append/query audit, claim idempotency key, and purge eligible rows. They expose no ORM objects or arbitrary query interface.

## 6. External and platform boundaries

M01 has no provider boundary. Its real external boundaries are local TTY/operator input, the cryptographic library/OS random source, SQLite through the persistence adapter, and P01 HTTP/browser delivery.

| Boundary | Adapter/contract | Limits and safe failure | Real verification |
|---|---|---|---|
| Password hashing | Approved Argon2id adapter | Input byte limit; configured policy floor; verification deadline/resource benchmark; exception becomes unavailable | Real library hashes/verifies on target Linux; PHC and rehash inspected |
| OS randomness | standard `secrets`/OS CSPRNG adapter | Minimum entropy/length; generation exception aborts; no fallback PRNG | Generate/verify format/uniqueness through production code; static security review |
| SQLite | production IAM repository adapter | Bounded transactions/busy handling; constraints; fail closed; no in-memory substitution | Real file DB, real migrations, concurrency, backup/restore |
| Local bootstrap/recovery input | platform-neutral operator port with Linux TTY adapter first | Require interactive hidden input and confirmation; reject arguments, redirected secrets, echo, logging; exclusive recovery lock | Real Linux terminal with owner; macOS remains Blocked until real system available |
| FastAPI/browser | P01 consumes M01 ports | Size/time bounds, exact origin/host, safe cookie/header mapping, no credential logging | Real server socket and built browser |

There are no network retries inside M01. A caller may retry a safe query after a typed unavailable result. Credential mutations follow their explicit idempotency behavior and never replay a secret.

## 7. Security and privacy

### Authentication and authorization controls

- Password login is local-dashboard only. API automation uses bearer tokens, not the administrator password.
- The fixed browser administrator role still becomes a `PrincipalV1` and passes every operation through `AuthorizePrincipalV1`.
- Bearer permissions are the intersection of valid token scopes and the current contract mapping. Revocation/expiry is evaluated before authorization.
- No route may depend only on UI visibility, loopback source, single-user status, token name, or a boolean admin shortcut.
- Swagger's bearer authorization uses the same P01/M01 path as every API client.

### Constant-behavior and side-channel policy

- One implicit administrator removes username enumeration.
- Every allowed initialized password attempt uses the admitted verifier exactly once; hash-policy upgrade occurs only after success.
- Invalid passwords share one external outcome and bounded response schema. No response reports whether a hash existed, which check failed, current failure count, hash parameters, or password length.
- Throttled behavior is intentionally distinguishable with `429` and `Retry-After`; this is required for abuse control and does not identify a credential.
- Bearer/session failures share `dashboard_authentication_required`; selector existence and revoked/expired state are not disclosed before a separate authenticated management query.
- Secret comparison uses library constant-time operations where applicable. The plan does not claim end-to-end constant response time across database and network operations.

### Threat/control matrix

| Threat | Planned controls | Verification |
|---|---|---|
| No/default/weak bootstrap credential | uninitialized closed state, one-time interactive bootstrap, proposed password floor, singleton transaction | DB/HTTP/operator tests |
| Online guessing or Argon2 DoS | persistent global throttle, request-size bound, one verifier per admitted attempt, capped lock, audit transitions | real HTTP rate/concurrency tests |
| Malicious website calling localhost | P01 exact Host/Origin, same-origin UI, SameSite Strict, session-bound CSRF, no wildcard CORS | cross-origin real-browser test |
| DNS rebinding | canonical host allowlist and loopback bind owned by P01/deployment | real HTTP Host tests |
| Session theft/fixation/replay | 256-bit opaque credential, HttpOnly, fresh login session, server expiry/revocation, TLS Secure flag | cookie/session DB/browser tests |
| CSRF theft/replay | separate binding, cookie+header+stored digest, strict origin, session lifecycle | HTTP/browser tests |
| XSS stealing bearer credential | UI never stores API token; Swagger persistence disabled; CSP owned by P01 | storage/CSP/browser inspection |
| Database/backup disclosure | Argon2id human secret; high-entropy token/session digest only; owner-only files; bounded retention | DB/backup/permission inspection |
| API-token privilege escalation | explicit scopes/permissions, attenuation, unknown-scope rejection, audited management | pure plus real API tests |
| Token create retry leaks/replays secret | no plaintext idempotency record; one-time response; deterministic conflict | real HTTP lost-response/retry scenario |
| Timing/record enumeration | generic outcomes, safe comparisons, dummy digest path, no external state detail | HTTP response-contract review; bounded timing observation is diagnostic, not proof |
| Audit/log flooding or leakage | bounded aggregate throttle events, allowlisted fields, no raw metadata, local retention | load/log/DB inspection |
| Restore resurrects credentials | pre-readiness bulk invalidation through M08/M01 contract | real backup/restore integration |
| Lost password | exclusive local interactive recovery, all-session revocation, security audit | real operator recovery test |
| Dependency compromise | direct minimal dependency, pinned/locked, admission review, SBOM/notices/scans | dependency gate |

### Privacy and data minimization proof

The module needs only one opaque administrator ID, verifier material, credential lifecycle metadata, scope keys, and safe security-event codes. It does not need or permit email, OS username, provider identity, IP/user-agent history, browsing history, prompts, responses, tool/source content, process data, arbitrary environment values, or raw request bodies. M01 emits no outbound analytics or crash reports.

### Logging and audit rules

- Structured local logs use module/event/outcome/correlation/safe IDs only.
- Authentication headers, cookies, password/token/CSRF input, verification digests, PHC strings, idempotency keys, request bodies, and one-time issue results are marked non-loggable at type/boundary review.
- Expected invalid credentials are not stack traces. Internal exception cause remains in protected local diagnostics only after redaction review.
- Screenshot/browser evidence must avoid the token reveal screen or redact it before capture; redaction cannot make a leaked committed artifact acceptable.

## 8. Configuration and operations

### Proposed configuration registry

These names allocate no secret values. Exact names/defaults/ranges require configuration-owner approval. Security floors cannot be weakened below the approved minimum merely through `.env`.

| Proposed key | Type/default proposal | Secret | Reload | Owner/validation |
|---|---|---:|---|---|
| `AGENTMONITOR_IAM_SESSION_IDLE_SECONDS` | positive duration; proposed installed default 1,800 | No | restart | M01; less than absolute, approved range |
| `AGENTMONITOR_IAM_SESSION_ABSOLUTE_SECONDS` | positive duration; proposed default 43,200 | No | restart | M01; greater than idle, bounded maximum |
| `AGENTMONITOR_IAM_SESSION_TOUCH_INTERVAL_SECONDS` | positive duration; proposed default 60 | No | restart | M01; less than idle |
| `AGENTMONITOR_IAM_LOGIN_WINDOW_SECONDS` | positive duration; proposed default 900 | No | restart | M01 |
| `AGENTMONITOR_IAM_LOGIN_MAX_FAILURES` | positive count; proposed default 5 | No | restart | M01 |
| `AGENTMONITOR_IAM_LOGIN_INITIAL_LOCK_SECONDS` | positive duration; proposed default 30 | No | restart | M01 |
| `AGENTMONITOR_IAM_LOGIN_MAX_LOCK_SECONDS` | positive duration; proposed default 900 | No | restart | M01; not below initial lock |
| `AGENTMONITOR_IAM_IDEMPOTENCY_RETENTION_SECONDS` | positive duration; proposed default 86,400 | No | restart | M01 |
| `AGENTMONITOR_IAM_TERMINAL_RECORD_RETENTION_DAYS` | proposed fixed/default 365 | No | restart | M01; cannot undercut approved history without requirements change |
| Argon2 policy keys or code policy version | exact model unresolved | No | restart | M01/security; benchmark plus hard floor; invalid policy fails readiness |

Cookie name, canonical public origin, trusted hosts, bind host/port, TLS, and proxy trust are P01/deployment configuration, not M01 keys. Passwords, API-token plaintext, session/CSRF credentials, and token bootstrap material are never configuration values. A future root-approved application cryptographic key, if proven necessary, must use an `AGENTMONITOR_` secret name, live only in the protected `.env`, and have a rotation runbook; this draft does not invent one.

### Bootstrap

1. Migration creates an uninitialized IAM store, not an administrator/password.
2. Protected service endpoints report `iam_setup_required`; no public web setup mutation exists.
3. Owner runs the final approved local operator entry point (command name TBD) from a controlling terminal as the service user.
4. It reads and confirms a password without echo, applies the real policy/Argon2id library, and commits administrator plus audit event transactionally.
5. It prints only success/failure and safe next action, never the password/hash/session/token.
6. Service readiness/login are verified over loopback.

### Normal rotation

- Authenticated password change requires current password, browser session, valid CSRF, and an explicit new value. It revokes all other sessions and replaces the current session with a fresh session/CSRF pair. API tokens remain active unless the owner selects an explicitly approved revoke-all option; this policy is unresolved.
- API-token rotation returns one successor secret, terminally marks the predecessor, and is audited. If delivery is lost, the secret is not replayed; browser admin creates another replacement.
- Session/CSRF credentials rotate on login and password change. Logout/revocation is server-side and clears browser cookies through P01.

### Forgotten password and incident recovery

- There is no default, email, hint, recovery answer, or bypass credential.
- Owner stops/quiesces the installed service and uses the approved local interactive recovery entry point (name TBD) with exclusive database ownership.
- Recovery creates new Argon2id material, revokes every browser session, and by proposed secure default revokes every API token. It appends an audit event and never prints credential data.
- Suspected token exposure uses an authenticated revoke when possible; broad compromise uses local recovery/bulk invalidation.
- After database restore, normal readiness remains false until the approved credential-invalidation operation completes.

### Health, diagnostics, and metrics

- `GetIamHealthV1` exposes only initialization, repository reachability, policy/schema compatibility, and last successful retention state.
- Local operational metrics may include aggregate login-denial/throttle, active-session, active-token, and authorization-denial counts only after privacy/security review. They stay local and expose no labels containing credential or personal data.
- Diagnostics expose safe policy/schema versions and secret-presence booleans only. They exclude PHC material, digests, cookie/scope assignments tied to real IDs, audit payloads beyond safe summaries, and all credential values.

### Backup/restore and upgrade

- Database backups contain password/token/session verification material and must use owner-only protection even though plaintext is absent.
- Restore/rollback procedures invalidate sessions/tokens before protected readiness to prevent credential resurrection.
- An Argon2 parameter/library upgrade preserves old verification until successful login rehash, unless a security advisory requires forced local reset.
- Scope/permission removals require migration/compatibility handling; an old token never gains new authority because a string was reinterpreted.
- Operational command names remain TBD until implemented and exercised on real Linux.

## 9. Test design before implementation

No test below is implemented or passed by this plan. Every integration identity is a real administrator created through the production bootstrap flow in an isolated real SQLite database; it is not a seeded row or fake repository. Credentials are generated/entered for that isolated application and never committed or retained in artifacts.

### Test inventory

| Test ID | Layer | Requirement | Real dependencies | Meaningful initial Red expected | Pass condition | Owner/live coordination |
|---|---|---|---|---|---|---|
| M01-PURE-001 | T1 pure | FR-IAM-003 | None; constructed explicit instants | expiry boundary permits `as_of == expires_at` | idle/absolute boundary transitions exactly as specified | M01 |
| M01-PURE-002 | T1 pure | FR-IAM-004 | None | scope attenuation permits an unavailable/escalated permission | every requested scope must be subset and caller must hold management permission | M01/security |
| M01-PURE-003 | T1 pure | NFR-SEC-001 | None | permission mapping grants a route without its declared permission | every scope/permission branch denies or grants exactly by contract | M01/P01 reviewer |
| M01-PURE-004 | T1 pure | FR-IAM-004 | None | token/session state transition can reactivate terminal state | state machine rejects every invalid transition | M01 |
| M01-PURE-005 | T1 pure | FR-HIST-003 | None; explicit UTC `as_of` | cutoff deletes record at wrong boundary | cutoff honors retention and preserves active records | M01/M08 |
| M01-CRYPTO-001 | real library | FR-IAM-002 | admitted Argon2id package on target Python/Linux | stored verification material is absent/wrong algorithm | bootstrap creates valid Argon2id PHC with approved floor and random salt | M01/security |
| M01-CRYPTO-002 | real library | FR-IAM-002 | same | wrong password verifies or raises distinguishable unsafe outcome | correct succeeds, incorrect safely fails, plaintext absent | M01/security |
| M01-CRYPTO-003 | real library + DB | FR-IAM-002 | real SQLite/migrations | weaker historical PHC is not upgraded after successful verification | successful login atomically rehashes; failure never rehashes | M01/security |
| M01-CRYPTO-004 | real workload | NFR-SEC-001 | target workstation | policy exceeds resource budget or falls below floor | recorded benchmark satisfies approved floor/budget | owner/security |
| M01-DB-001 | T2 DB/migration | AC-V1-004 | real file SQLite, full Alembic chain | fresh migration lacks IAM tables/constraints | full chain applies and schema validates | persistence/M01 |
| M01-DB-002 | T2 DB/concurrency | FR-IAM-001 | real file SQLite, production repositories | two concurrent bootstraps create/replace administrators | exactly one succeeds; other conflicts; one audit fact | M01 |
| M01-DB-003 | T2 DB | FR-IAM-003 | real DB | session survives revocation or deadline | lookup denies terminal session; no resurrection | M01 |
| M01-DB-004 | T2 DB/concurrency | FR-IAM-003 | real DB/threads or processes | concurrent touches move time backward or exceed absolute expiry | monotonic bounded touch and invariant preserved | M01 |
| M01-DB-005 | T2 DB | FR-IAM-003 | real DB | CSRF digest can validate against another session | binding validates only its owning active session | M01/security |
| M01-DB-006 | T2 DB/concurrency | NFR-SEC-001 | real DB | failed-login increments are lost; lock bypassed | atomic threshold/lock across concurrent real transactions | M01/security |
| M01-DB-007 | T2 DB | FR-IAM-004 | real DB/production create use case | token name/scopes/terminal metadata do not persist correctly | summary survives restart; secret remains unrecoverable | M01 |
| M01-DB-008 | T2 DB/artifact | FR-IAM-005 | real DB and SQLite inspection | plaintext/full bearer appears in DB/WAL/application row | only approved digest/selector/fingerprint metadata exists | security reviewer |
| M01-DB-009 | T2 DB | FR-IAM-004 | real DB | revoked/expired token still resolves | all terminal states deny generically | M01 |
| M01-DB-010 | T2 DB/concurrency | FR-IAM-004 | real DB | concurrent rotations produce multiple successors or leave predecessor active | one successor commits; competing version conflicts | M01 |
| M01-DB-011 | T2 DB/idempotency | FR-IAM-004 | real DB | retry creates a second token or replays plaintext | one resource; safe non-replay conflict; no plaintext persistence | M01/P01 |
| M01-DB-012 | T2 DB | FR-HIST-001/003 | real DB populated only through production IAM use cases | retention removes active/recent record or leaves eligible terminal rows | bounded eligible deletion and audit summary | M01/M08 |
| M01-DB-013 | T2 DB | NFR-DATA-001 | real DB/query planner at planned volume | token/audit/history query scans unbounded table | approved indexes and bounded cursor plans are used | persistence |
| M01-DB-014 | T2 resilience | NFR-RES-001 | real isolated DB with real lock/permission failure | authentication succeeds or leaks SQL/path on unavailable write | protected operation fails closed with sanitized typed outcome | M01/operations |
| M01-DB-015 | T2 migration | AC-V1-004 | each real supported prior schema artifact | upgrade loses/weakens credential state or fails validation | supported path upgrades with recovery evidence | persistence |
| M01-HTTP-001 | T3 HTTP | FR-IAM-001 | real uvicorn/FastAPI, real DB/migrations | uninitialized login grants access or returns default session | setup-required; no session; protected API denied | P01/M01 |
| M01-HTTP-002 | T3 HTTP | FR-IAM-002 | real Argon2, DB, server | wrong password authenticates or yields credential-specific detail | generic 401; correct creates exactly one fresh session | P01/M01 |
| M01-HTTP-003 | T3 HTTP | FR-IAM-003 | real server | login cookie lacks HttpOnly/SameSite/Path/no-Domain policy | exact approved attributes and no body token | P01 |
| M01-HTTP-004 | T3 HTTP | FR-IAM-003 | real server | authenticated unsafe request succeeds without CSRF header/cookie | safe reads work; every unsafe session request needs valid binding | P01/M01 |
| M01-HTTP-005 | T3 HTTP | FR-IAM-003 | real server | CSRF from session A succeeds with session B | cross-session proof denied generically | P01/M01 |
| M01-HTTP-006 | T3 HTTP | FR-IAM-003 | real server and elapsed real time | idle-expired session remains usable | after approved minimum real interval, request is 401 and UI can relogin | P01/M01; slower test is intentional |
| M01-HTTP-007 | T3 HTTP | FR-IAM-003 | real server and elapsed real time | activity extends beyond absolute deadline | absolute expiry wins despite accepted activity | P01/M01 |
| M01-HTTP-008 | T3 HTTP | FR-IAM-003 | real server | logout without CSRF mutates; repeat exposes existence | valid-CSRF logout revokes; repeat follows approved idempotent semantics | P01/M01 |
| M01-HTTP-009 | T3 HTTP | NFR-SEC-001 | real server/concurrent clients | rate threshold is bypassed or leaks attempt details | atomic 429/Retry-After and recovery per approved real interval | P01/M01 |
| M01-HTTP-010 | T3 HTTP | NFR-SEC-001 | real server | password change leaves prior sessions valid | fresh current session issued; selected revocation policy enforced | P01/M01 |
| M01-HTTP-011 | T3 HTTP | FR-IAM-004/005 | real server/DB | create returns no token, returns it twice, or persists it | one no-store response reveals token; later GET only summary | P01/M01 |
| M01-HTTP-012 | T3 HTTP | FR-IAM-004 | real server | token accesses operation outside scope | correct 403; allowed operation succeeds | P01/M01 |
| M01-HTTP-013 | T3 HTTP | FR-IAM-004 | real server | bearer mints broader token | attenuation denies; equal/subset behavior matches approved policy | P01/M01 |
| M01-HTTP-014 | T3 HTTP | FR-IAM-004 | real server | revoked/expired/malformed/unknown tokens reveal different states | all authenticate as the same 401 outcome | P01/M01/security |
| M01-HTTP-015 | T3 HTTP | FR-IAM-004 | real server/DB | rotation leaves old valid or retry leaks successor | old terminal, successor valid, retry has no plaintext | P01/M01 |
| M01-HTTP-016 | T3 HTTP | FR-IAM-004 | real server | repeated revoke fails or recreates state | terminal idempotent result and one transition audit | P01/M01 |
| M01-HTTP-017 | T3/OpenAPI | FR-IAM-006 | generated OpenAPI, real token/server | Swagger scheme absent or token bypasses M01 | bearer scheme authenticates real scoped request; docs persist disabled | P01 |
| M01-HTTP-018 | T3 HTTP | FR-IAM-007 | real loopback service | unexpected Host reaches login/protected handler | P01 rejects before authentication | P01/deployment |
| M01-HTTP-019 | T3 HTTP | FR-IAM-007 | real server | foreign/missing browser Origin can mutate session-auth state | canonical Origin required; request denied before mutation | P01 |
| M01-HTTP-020 | T3 HTTP | FR-IAM-007 | real server | cookie+bearer ambiguity selects more privileged principal | request rejected with safe problem | P01 |
| M01-HTTP-021 | T3 HTTP | FR-IAM-007 | real non-browser bearer client | Origin/CSRF is incorrectly required for pure bearer request | valid scoped bearer works without ambient-cookie CSRF | P01/M01 |
| M01-HTTP-022 | T3 HTTP | FR-OPS-002/005 | real service | health/diagnostic response exposes counts/hash/config values | only allowlisted safe state/presence/version data | M01/M08/P01 |
| M01-HTTP-023 | T3 contract | NFR-API-001/002 | running service/OpenAPI/client generator | runtime response diverges or handwritten DTO compiles independently | schema validates/diffs and generated client compiles | P01/P02 |
| M01-HTTP-024 | T3 resilience | NFR-RES-001 | real isolated persistence failure | auth failure takes unrelated liveness down or opens access | protected API closed; approved liveness remains truthful | P01/operations |
| M01-BROWSER-001 | T4 browser | AC-UI-001 | production UI build, real browser/server/DB | login workflow cannot establish dashboard session | owner-like test admin bootstrapped through production flow logs in | P02/P01/M01 |
| M01-BROWSER-002 | T4 browser | AC-UI-001 | same | logout leaves dashboard/API usable | cookies clear, session revoked, protected route returns to login | P02/P01/M01 |
| M01-BROWSER-003 | T4 browser | AC-UI-001 | same plus real elapsed time | expired session displays stale protected data or loops | next request returns to accessible login with safe message | P02 |
| M01-BROWSER-004 | T4 browser/security | FR-IAM-003 | browser dev storage inspection | session/API credential appears in local/session storage or JS-visible auth cookie | no bearer/session secret in storage; auth cookie is HttpOnly | P02/security |
| M01-BROWSER-005 | T4 browser | FR-IAM-004 | built UI/real backend | token is revealed after leaving/reloading creation result | shown once, then summary only; real rotate/revoke works | P02/M01 |
| M01-BROWSER-006 | T4 browser | FR-IAM-006 | real Swagger/browser/token | docs persist token or call outside scope | authorized real call works; reload does not persist bearer | P01/security |
| M01-BROWSER-007 | T4 browser/a11y | AC-UI-004 | real browser | login/token controls lack keyboard/focus/name/contrast behavior | accessibility checklist passes | P02 |
| M01-BROWSER-008 | T4 browser | AC-UI-005 | real backend states | throttle/expired/forbidden/setup errors are misleading | truthful actionable state without sensitive detail | P02/M01 |
| M01-SEC-001 | T2/T3 inspection | FR-IAM-005 | DB/WAL/log/artifact scan | created token or cookie is discoverable outside one response/browser store | no plaintext in persistent/test/log artifacts | security |
| M01-SEC-002 | T2 backup | FR-IAM-005 | real SQLite backup | backup contains plaintext secret or restore makes revoked token active | digest only; restore invalidation prevents reuse | M01/M08/security |
| M01-SEC-003 | artifact/network | AC-V1-007 | real logs/diagnostics/export/backup/build | real credential appears in any artifact | allowlist scan clean; any finding fails and triggers incident | security |
| M01-SEC-004 | architecture/API | FR-SAFE-002 | source/import/OpenAPI inspection | IAM surface exposes process/provider control | no prohibited path or dependency exists | architecture |
| M01-SEC-005 | logging | NFR-OBS-001 | real invalid/successful flows and local logs | request credential/body/header is logged | only safe structured codes/IDs/correlation | security |
| M01-SEC-006 | audit | NFR-OBS-001 | real DB and flows | audit contains token name/value, password metadata, or unbounded text | strict safe schema only | security |
| M01-SEC-007 | real HTTP concurrency | NFR-SEC-001 | real server/workload | parallel login work exhausts resources or bypasses limit | bounded latency/concurrency within approved target | security/performance |
| M01-SEC-008 | real browser | FR-IAM-007 | malicious-origin page in real browser | localhost mutation succeeds | browser attack denied by Origin/SameSite/CSRF | owner/P01 |
| M01-SEC-009 | mutation test | AC-TEST-005 | admitted mutation tool | meaningful authorization/expiry/attenuation mutant survives | 100% of non-equivalent targeted M01 pure security-policy mutants killed | test reviewer |
| M01-SEC-010 | outbound inspection | NFR-PRIV-002 | running real local app/network observation | IAM emits analytics/crash traffic | no outbound AgentMonitor telemetry | security/operations |
| M01-ARCH-001 | boundary | NFR-ARCH-001/002 | repository checks | domain imports framework/provider/other module internals | boundary check passes and review confirms ownership | architecture |
| M01-ARCH-002 | compatibility | NFR-COMP-001 | contract/schema diff tools | incompatible change passes without version/ADR | declared compatible diff or approved major migration | integration |
| M01-OPS-001 | T7 operations | FR-IAM-001 | real installed Linux/TTY/service user | bootstrap accepts leaked/noninteractive input or creates two admins | interactive one-time bootstrap succeeds safely | owner/operations |
| M01-OPS-002 | T7 operations | FR-IAM-007 | real installed service/network inspection | service listens non-loopback | only approved loopback sockets reachable | owner/deployment |
| M01-OPS-003 | T7 recovery | AC-OPS-005 | real backup/restore and service | restore resurrects existing session/token | mandatory invalidation before readiness | owner/M08/M01 |
| M01-OPS-004 | T7 operations | NFR-PLAT-001 | real Linux; real macOS when available | platform behavior leaks into domain or recovery fails | Linux Passed; macOS Passed or explicitly Blocked | owner/platform |
| M01-OPS-005 | T7 recovery | AC-OPS-005 | real installed service/TTY | forgotten-password recovery leaves old credentials usable | new password works; required credentials revoked; audit present | owner/operations |
| M01-OPS-006 | T7 upgrade | AC-OPS-005 | real prior/current install DB | upgrade makes password/token unverifiable without recovery | compatibility/rehash or documented recovery passes | owner/operations |
| M01-DEP-001 | dependency | NFR-LIC-001 | lockfile/SBOM/scanners | unapproved or incompatible package enters graph | admission approved and reproducible artifacts current | dependency reviewer |
| M01-DOC-001 | documentation | NFR-DOC-001 | maintained docs/runbook | developer/operator cannot reproduce safe lifecycle | review/link/runbook exercise passes | docs/operations |

### Test integrity and evidence rules

- Pure tests may construct principals, scopes, states, and explicit UTC instants only for deterministic no-I/O policies.
- Cryptographic tests use the real admitted implementation; no replacement hasher, fixed-success function, monkeypatch, or reduced test-only algorithm.
- Persistence tests use a real temporary SQLite file, the full production migration chain, production repositories, and real transaction behavior.
- HTTP tests launch the production FastAPI composition through its real server on an ephemeral loopback port. Direct route calls or simulated ASGI transports do not count.
- Browser tests use the real production frontend build in a real supported browser. DOM simulators do not count.
- A local test administrator is created through the production bootstrap use case. No direct seeded administrator/session/token rows are used to claim end-to-end success.
- Expiry/recovery tests use real elapsed time at an approved production-valid minimum. Clocks are not patched and the machine clock is not changed. Slower trustworthy tests are accepted.
- Real one-time credentials remain in process/browser memory only. Test output, screenshots, traces, videos, reports, CI artifacts, and failure diagnostics must be configured not to retain them.
- Failed, Blocked, and Not Run remain distinct. macOS or live operator scenarios not executed are never counted as Passed.
- Every behavior records meaningful Red, Green, and post-refactor evidence. A missing dependency, syntax error, unavailable browser, or migration setup failure is not valid Red.

### Mutation and coverage gate

- Every documented branch of password policy, expiry, terminal transitions, scope attenuation, permission decisions, and retention eligibility receives meaningful coverage.
- The proposed mutation target is 100% of non-equivalent mutants for the selected pure M01 security-policy package. Equivalent mutants require independent written classification; exclusions cannot hide a security branch.
- Cryptographic/persistence/API line coverage never substitutes for real behavior and artifact inspection.

## 10. Implementation increments

Implementation may start only after section 15 is fully satisfied and the plan status is Approved. Each increment receives its own evidence record.

| Increment | Files/area | Failing test first | Minimum production change | Refactor/documentation | Exit evidence |
|---|---|---|---|---|---|
| I-00 Contract synchronization | Shared contracts/config registry only under root allocation | Contract/schema review checks | Freeze V1 DTO/ports, errors, P01/M08 seams, permission map | Update contract registry/traceability/ADR if required | Approved contract versions; no module code |
| I-01 Pure IAM model | M01 domain | M01-PURE-001..005, M01-ARCH-001 | States, expiry, scope/permission, retention policies | Domain docs/names/invariants | Red/Green/refactor plus boundary check |
| I-02 Real password/bootstrap | M01 app + hasher adapter + owned persistence | M01-CRYPTO-001..004, M01-DB-001/002 | Migration, administrator repository, interactive bootstrap port, Argon2id | Security/config docs and admission evidence | Real DB/crypto/operator-safe evidence |
| I-03 Server-side sessions/CSRF | M01 app/repository | M01-DB-003..005 | Session/CSRF lifecycle and resolving ports | State/error docs | Real DB evidence; no P01 shortcut |
| I-04 Throttle and IAM audit | M01 app/repository | M01-DB-006, M01-SEC-005/006 | Persistent rate state and allowlisted audit | Audit/retention docs | Concurrency and leak inspection |
| I-05 API tokens | M01 app/repository | M01-PURE-002/004, M01-DB-007..011 | Token create/verify/attenuate/rotate/revoke/idempotency | One-time secret and recovery docs | DB/concurrency/artifact evidence |
| I-06 Retention/recovery/health | M01 app/repository contracts | M01-DB-012..015, M01-OPS-003/005/006 | Purge, post-restore invalidation, health, password recovery | Operations procedures (commands still verified before finalization) | Real DB/restore/upgrade evidence |
| I-07 P01 HTTP integration | Separately assigned P01 files plus published M01 ports | M01-HTTP-001..024 | Real route/security/cookie/problem/OpenAPI mapping | API docs/generated artifact | Real socket/OpenAPI evidence |
| I-08 P02 browser integration | Separately assigned P02 files/generated client | M01-BROWSER-001..008 | Login/logout/token views and auth-expiry handling | Accessibility/user docs | Built-browser evidence |
| I-09 Installed security hardening | Deployment/operations tasks with M01 | M01-SEC-001..010, M01-OPS-001..006 | Approved configuration floors, service/runbook integration | Threat model/runbook/evidence | Independent security/test review |

### Ordering and parallel safety

- I-00 precedes all implementation.
- I-01 may begin only after shared primitive contracts are frozen.
- I-02 through I-06 are primarily sequential because they share M01 invariants and one migration chain. A separate test reviewer may work read-only in parallel.
- I-07 and I-08 are separate P01/P02 owner tasks. They consume the frozen M01 contract and must not edit M01 internals.
- Only the centrally assigned migration owner edits the Alembic revision chain. Only the P01 owner generates OpenAPI; only the P02 owner regenerates the client.
- A discovered contract gap stops affected work and returns to root synchronization. It is not solved with a deep import, shared ORM model, duplicated DTO, direct table read, or test bypass.

### Implementation-agent return packet

Every separately authorized M01 increment returns the requirement/acceptance
and scenario IDs, exact plan/contract versions, files changed, and the exact
Red/Green/refactor commands and results. It distinguishes Passed, Failed,
Blocked, and Not Run for every T1–T7 boundary; records security, privacy,
migration/recovery, dependency/license, and documentation impact; identifies
residual risks; and names the next integration step. Missing live owner
authentication remains Blocked and is never replaced by constructed evidence.

## 11. Documentation outputs

Future implementation must update or create, under assigned ownership:

- M01 module documentation: invariants, contracts, states, permissions/scopes, table ownership, errors, and known limitations;
- generated OpenAPI and human API guidance for session/token/auth problems, produced from P01 source rather than hand editing;
- generated frontend client and login/token workflow documentation;
- configuration registry entries with safe names/defaults/ranges and no values;
- local bootstrap, password change/recovery, token rotation/revocation, restore invalidation, and troubleshooting runbooks with only implemented/verified commands;
- migration notes, backup/restore credential implications, and upgrade/rehash behavior;
- threat-model and risk-register updates for the accepted design;
- dependency admission, SBOM, notices, and security review records;
- sanitized Red/Green/refactor, DB/API/browser/operations evidence and every Blocked/Not Run item;
- individual requirement/acceptance mappings in the traceability matrix;
- ADR for any consequential decision the root reviewer classifies as requiring one.

## 12. Dependency and license impact

No dependency is approved by this draft and none may be installed during planning.

| Candidate | Proposed purpose/scope | Alternatives | Admission required |
|---|---|---|---|
| `argon2-cffi` (exact version TBD) | Real Argon2id password hashing adapter | another maintained standards-conformant Argon2id implementation; standard library lacks approved memory-hard password hash | direct/transitive license, maintainer/provenance, binary-wheel/source-build, vulnerabilities, API stability, performance, removal cost |
| Python `secrets`, `hashlib`, `hmac` | CSPRNG and high-entropy session/token digest/comparison | avoid extra JWT/crypto wrapper | standard-library threat/API review; no package admission |
| SQLAlchemy/Alembic candidates selected by foundation | Real repository and migration adapters only | reviewed direct SQLite layer, if foundation changes | project-wide admission; M01 domain cannot import them |
| FastAPI/uvicorn/Pydantic selected by P01/foundation | HTTP transport, server, schemas | already architecture-selected, still license/security reviewed | project-wide admission; not M01 domain dependencies |
| pytest/Playwright/property/mutation tools | Test runner, real browser, meaningful pure boundary/mutation tests | foundation-approved equivalents | development-dependency admission; no mocking plugins/frameworks |

JWT, OAuth frameworks, fake repositories, mock plugins, ASGI simulated clients as HTTP evidence, in-memory SQLite substitutes, and general-purpose auth frameworks are not proposed. A package is not admitted merely because its headline license is permissive; transitive licenses, telemetry/install behavior, provenance, vulnerabilities, and lock/SBOM/notices must pass the project policy.

## 13. Risks and unresolved decisions

### Risks

| Risk/question | Likelihood/impact | Mitigation or experiment | Owner | Trigger/deadline | Status |
|---|---|---|---|---|---|
| R-013: local authentication is exposed beyond loopback | Medium/Critical | P01/deployment loopback fail-closed, exact Host/Origin, real network/browser tests; remote requires new ADR/threat model | P01/deployment/security | Before I-07 approval | Open |
| Password hashing parameters are too weak or cause local DoS | Medium/Critical | admitted Argon2id, target benchmark, minimum floor, rate limiting, bounded concurrent verification | M01/security | Before I-02 implementation | Open |
| Persistent throttle locks the only administrator out | Medium/Major | capped deadlines, truthful Retry-After, local recovery procedure that does not bypass password except explicit reset | M01/operations | Before I-04 approval | Open |
| Session/CSRF contract mismatches browser/P01 | Medium/Critical | freeze cookie/header/origin lifecycle jointly and run real cross-origin tests | M01/P01/P02 | I-00 | Open |
| One-time token response is lost and cannot be replayed | Medium/Major | explicit non-replay conflict, safe resource metadata, browser recovery/rotate; decide whether grace rotation is needed | M01/P01/product | I-00 | Open |
| Database/backup leak permits offline password attack | Medium/Critical | Argon2id floor, strong owner password guidance, owner-only storage, no plaintext, incident runbook | security/operations | Security review | Open |
| Restored DB resurrects revoked credentials | Medium/Critical | mandatory M01 bulk invalidation before readiness; real restore test | M01/M08 | Before I-06/I-09 | Open |
| Audit/rate state grows under local attack | Medium/Major | bounded transition events, aggregated attempt windows, retention and indexed batches | M01/security | Before I-04 | Open |
| SQLite lock contention causes auth outage | Medium/Major | short transactions, coalesced touches, measured concurrency, typed fail-closed response | persistence/M01 | I-02..I-05 | Open |
| Secret appears in trace/video/failure output | Medium/Critical | disable sensitive capture, response/log redaction, artifact scans, stop/incident rule | test/security | Every increment | Open |
| Permission vocabulary drifts across module plans | High/Critical | root-owned synchronized permission catalog and generated/static route checks | integration/M01/P01 | I-00 before parallel implementation | Open |
| macOS recovery/bootstrap is assumed from Linux | Medium/Major | platform-neutral port; real macOS status Blocked until exercised | platform/M01 | V1 platform gate | Open |
| Unapproved dependency or transitive license enters graph | Medium/Critical | dependency admission before import/install; lock/SBOM/notices/scans | dependency reviewer | Before I-02/tooling | Open |

### Contract decisions requiring root synchronization

The following are not delegated to the M01 implementation agent. Each can materially change P01/P02/M08 or other module plans:

1. Confirm password-only implicit administrator login versus adding a username field. This draft chooses password-only based on the approved interview outcome.
2. Approve local interactive bootstrap and forgotten-password recovery, including whether any one-shot `.env` bootstrap input is permitted. This draft recommends no plaintext dashboard password in `.env`.
3. Freeze exact `identity-access.v1` DTO/port/event names, package path, sensitive-result handling, and compatibility promise.
4. Freeze permission and bearer-scope vocabulary/mapping for every `/api/v1` operation, including whether bearer tokens may manage attenuated tokens or token management is browser-only.
5. Approve session idle/absolute defaults and ranges, activity touch interval, password policy, Argon2 selection/parameter policy, and rate-limit algorithm/defaults.
6. Approve session and CSRF cookie names/attributes, CSRF cookie+header method, login Origin rule, ambiguous cookie+bearer denial, plain-loopback HTTP `Secure` behavior, and exact M01/P01/P02 responsibility split.
7. Approve canonical loopback/public-origin/trusted-host semantics for IPv4, IPv6, and `localhost`, plus forwarded-header rejection in V1.
8. Approve every stable problem code/status mapping, particularly `iam_setup_required`, idempotent logout, stale versions, and management-time `404` behavior.
9. Approve API-token wire format, digest/selector/fingerprint policy, scope attenuation, expiry limits, and whether duplicate token names are allowed.
10. Confirm the aligned `one_time_secret_non_replayable` policy and `one_time_secret_not_replayable` problem code for create/rotation; any proposed grace/confirmation phase is a separate contract change and cannot permit plaintext replay.
11. Decide password-change and local-recovery effects on existing browser sessions and API tokens. This draft proposes all other sessions revoked on change and all credentials revoked on recovery.
12. Approve M08 contracts for IAM audit queries, retention scheduling, health, backup/diagnostic exclusion, and mandatory post-restore credential invalidation.
13. Allocate exact IAM table/migration names and revision order in the shared Alembic chain; resolve whether terminal credential digests are nulled or retained until expiry.
14. Approve configuration keys and determine whether Argon2 work parameters are operator configuration or a versioned code policy with non-weakenable floors.
15. Complete dependency/security/license admission for the Argon2 implementation and all foundation/test packages.
16. Decide whether bootstrap/recovery, token-rotation, or restore-invalidation decisions require a new ADR before plan approval.

## 14. Delivery and rollback

### Delivery order

1. Approve contracts, permissions, P01/P02/M08 seams, migration allocation, dependencies, and this plan.
2. Land pure M01 contracts/policies and import-boundary checks without exposing HTTP behavior.
3. Apply the first IAM migration and verify fresh/upgrade/backup recovery on real SQLite.
4. Deliver bootstrap/password/session/CSRF/rate/audit/token behavior in small TDD increments.
5. Integrate P01 and generate/validate OpenAPI.
6. Integrate P02 through the generated client and run the built-browser suite.
7. Exercise installed Linux bootstrap/recovery/restore and independent security/test-integrity reviews.

### Compatibility and exposure

- No protected route is exposed until initialization, persistence, auth resolution, and required security middleware are composed and readiness passes.
- New nullable/additive fields may evolve V1; renamed/removed/reinterpreted fields, permission meaning, credential format, or state transitions require the versioning workflow.
- Old password hashes remain verifiable only within the explicitly supported algorithm/policy range and are upgraded after real successful verification.
- Unknown token format versions fail authentication generically; they are never guessed.

### Rollback and recovery

- Before an IAM migration/upgrade, create and verify a real SQLite backup through M08 procedure.
- Prefer forward-fix for additive migrations. Do not run a destructive downgrade against the only database.
- If the new binary cannot safely read supported old hashes/tokens/sessions, fail readiness and use the documented compatible binary/backup or local credential recovery; never silently reset credentials.
- Restoring a backup requires all session/token invalidation before normal readiness because credential state may be stale.
- Rollback evidence verifies login, scope enforcement, token revocation, audit integrity, and absence of credential leakage.

### Post-deployment checks

- Service listens only on approved loopback interfaces and rejects invalid Host/Origin.
- Initialization state is correct; login/logout/session expiry and CSRF work.
- Real scoped API token works in an ordinary client and Swagger, and revoked token fails.
- Database schema/policy versions and IAM health are compatible.
- Logs, diagnostics, database, WAL, backup, browser storage, OpenAPI examples, and evidence artifacts contain no plaintext credential.
- Browser close does not alter server-side authentication/collection service operation.

## 15. Definition of ready

Implementation remains blocked until every item is checked by the named reviewer. Current status is intentionally not Ready.

- [ ] Requirements/non-goals and the password-only implicit administrator interpretation are approved.
- [ ] This plan is approved and its status/version are updated by the root/integration steward.
- [ ] Exact owning/allowed/shared/forbidden paths and implementation agent assignments are allocated with no overlap.
- [ ] `identity-access.v1` contracts, sensitive result types, stable outcome codes, and compatibility rules are approved.
- [ ] P01 boundary covers bind/Host/Origin/CORS/cookie/header/OpenAPI/Swagger semantics without duplicating M01 policy.
- [ ] P02 agrees to the CSRF/generated-client/expiry/token-reveal contract and browser-storage prohibition.
- [ ] M08 retention, IAM audit, health, diagnostics, restore-invalidation, and recovery contracts are approved.
- [ ] Permission/scope catalog and every planned route requirement are centrally synchronized.
- [ ] Bootstrap, normal password change, forgotten-password recovery, and credential invalidation policies are security-approved.
- [ ] Password policy, Argon2id parameters/benchmark method, rate defaults, session expiries, and configuration ranges are approved.
- [ ] API-token format, digest, attenuation, rotation, one-time reveal, and retry/idempotency decisions are approved.
- [ ] IAM table/constraint/index plan and shared migration revision order are approved; backup/recovery exists.
- [ ] Every test has a valid real boundary, meaningful expected Red, safe credential handling, cleanup, and assigned owner.
- [ ] Real Linux TTY, real browser, real file SQLite, and owner participation are scheduled; unavailable macOS work is visibly Blocked.
- [ ] Dependency/security/license admission is complete before packages are installed/imported; lock/SBOM/notices plan exists.
- [ ] Threat-model/risk review resolves or explicitly accepts every Critical item; required ADRs are accepted.
- [ ] No unresolved decision permits materially different implementations.

### Stop conditions during implementation

Stop and return to root synchronization if any implementation would:

- change a contract/permission/error meaning or P01/P02/M08 assumption;
- read another module's tables/import internals or edit an unallocated shared path;
- add a dependency without admission;
- persist/log/return a credential outside the approved one-time/cookie channel;
- require a test double, clock patch, seeded identity, simulated HTTP/browser, or test-only bypass;
- expose beyond loopback, trust proxy headers, weaken Origin/CSRF, or introduce remote/multi-user behavior;
- use provider credentials/state or affect a running agent;
- perform a destructive migration/recovery without explicit approval and verified backup;
- reveal a real secret in output/evidence, which triggers the incident stop rule immediately.

## 16. Approval record

| Reviewer | Decision | Conditions/findings | Date | Approved versions |
|---|---|---|---|---|
| Root/integration steward | Pending | Contract synchronization decisions 1–16 unresolved | — | — |
| Security reviewer | Pending | Threat, hash, rate, cookie/CSRF, recovery, and token review required | — | — |
| P01 API owner | Pending | Transport/error/permission/OpenAPI contract required | — | — |
| P02 UI owner | Pending | Generated client, CSRF, auth expiry, token reveal, and accessibility required | — | — |
| Persistence/migration owner | Pending | DDL/index/concurrency/retention/restore review required | — | — |
| M08 operations owner | Pending | Audit/health/retention/restore-invalidation contract required | — | — |
| Test-integrity reviewer | Pending | Real-boundary test design and evidence-safety review required | — | — |
| Dependency/license reviewer | Pending | Argon2 and foundation/test dependency admission required | — | — |

No production implementation, dependency installation, migration, configuration file, `.env`, API route, generated artifact, or frontend work is authorized by this Draft plan.
