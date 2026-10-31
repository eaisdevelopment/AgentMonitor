# ADR 0012: Require origin proof before cookie-authenticated reads

- Status: Accepted for the V1-M2 audit correction
- Date: 2026-09-21
- Deciders: P01 security/integration owner under the owner's M2 audit-fix request
- Requirements: `FR-IAM-007`, `NFR-SEC-001`, `API-BROWSER-006`, `M01-HTTP-019`, `M01-SEC-008`
- Supersedes: the absent-Origin cookie GET/HEAD allowance in the accepted M2 contract overlay §3
- Superseded by: none

## Context

A real Chrome image request from an unrelated `127.0.0.1` port omitted `Origin` but carried AgentMonitor's host-only session cookie. After 62 real seconds, `GET /api/v1/session` returned a response blocked from the page by CORP, yet IAM had already advanced the persisted session activity, idle deadline, and record version. CORS/CORP response isolation therefore did not meet the approved no-mutation criterion. The approved overlay allowed a headerless cookie read; that allowance conflicts with `API-BROWSER-006` and `M01-HTTP-019` for this local-origin threat.

## Decision drivers

- Reject hostile browser traffic before M01 session resolution and its coalesced activity write.
- Preserve same-origin UI/API/docs behavior, deliberate address-bar navigation, and origin-independent pure bearer clients.
- Fail closed for browser-like or unclassified cookie reads without making M01 depend on HTTP headers.
- Keep the pre-release V1 contract change explicit and testable.

## Considered options

### A: Keep absent-Origin cookie reads and rely on CORS/CORP/CSRF

Rejected: these controls did not prevent the observed persisted idle-deadline change.

### B: Suppress IAM touch on all absent-Origin reads

Rejected for this correction: it would add an HTTP-specific mode to the M01 resolution contract, and same-origin browser GETs commonly omit `Origin`. It also leaves a needless authenticated request path for hostile resources.

### C: Require transport origin proof before cookie-authenticated reads

Selected. P01 accepts a cookie GET/HEAD only with the exact canonical `Origin`, browser `Sec-Fetch-Site: same-origin`, or a direct user navigation with the exact `Sec-Fetch-Site: none`, `Sec-Fetch-Mode: navigate`, and `Sec-Fetch-Dest: document` tuple. A supplied foreign `Origin`, foreign/indeterminate Fetch Metadata, duplicate `Sec-Fetch-Site`, or absence of all proof receives `403 origin_not_allowed` before M01. Pure bearer requests remain Origin-independent. Same-origin static navigation remains usable; protected documentation follows the same rule.

## Consequences

### Positive

- A hostile image, including one suppressing `Referer`, is denied before it can refresh a cookie session.
- P01 owns transport classification; M01's published session policy and SQLite schema are unchanged.

### Negative and trade-offs

- A non-browser client using cookie authentication for GET/HEAD without an `Origin` header must add the configured exact Origin. Old browsers lacking Fetch Metadata also need that header and may not be supported for cookie navigation. This is an intentional security tightening before V1 release.
- Host-only cookies remain shared across ports on the same host. This decision does not remove the separately disclosed local-service cookie-exposure risk.

### Neutral or follow-up

- Any future remote, proxy, or browser-support profile needs its own threat review. No new dependency, configuration key, or provider behavior is introduced.

## Compatibility and migration

`CTR-API-002` V1's cookie-read admission rule is amended before external V1 release. The previously permitted no-Origin/no-Fetch-Metadata cookie GET is denied; this is a security-motivated behavioral incompatibility, documented here rather than silently called compatible. All in-repository generated-client consumers and real HTTP tests use same-origin browser metadata or exact Origin. `/api/v1` route shapes, schemas, generated artifacts, IAM contracts `CTR-IAM-003/005`, events, database, and configuration remain unchanged. No persisted-data migration is needed. A V1 client must send exact Origin for a non-browser cookie read or use its approved bearer route; there is no unsafe compatibility fallback.

## Verification

- Real migrated SQLite, production Argon2 bootstrap, Uvicorn and HTTP test: headerless same-site and unclassified cookie GETs receive 403; same-origin and direct user navigation work; bearer remains Origin-independent.
- Built Chrome at a second real loopback origin: two headerless images (ordinary and `no-referrer`) receive 403, and `last_activity_at`, `idle_expires_at`, and `record_version` remain unchanged after at least 61 real seconds.
- Canonical `AUTO-TEST`, `AUTO-QUALITY`, `AUTO-BUILD`, `AUTO-DOCS-CHECK`, and `AUTO-PLAN-CHECK` must pass before M2 reacceptance. Any discovered browser request without the expected proof is denied rather than silently refreshing a session.
