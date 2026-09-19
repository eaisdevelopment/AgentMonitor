# API standards

## Contract authority

FastAPI route and schema definitions generate the OpenAPI document. The generated, validated OpenAPI artifact is committed for review and is the sole source for generating clients. Neither the OpenAPI output nor generated clients are hand-edited.

The browser UI is a normal API consumer and receives no privileged backend imports or database access.

## Versioning and paths

- Public application routes begin `/api/v1`.
- OpenAPI is available at a documented endpoint, expected `/openapi.json`.
- Swagger UI and ReDoc are authenticated in installed mode.
- Health/liveness routes may be outside `/api/v1` only if an ADR defines their disclosure/authentication policy.
- Breaking changes require `/api/v2` or an approved compatibility bridge.

## Resource model

Expected V1 resource families:

```text
/api/v1/session
/api/v1/api-tokens
/api/v1/organizations
/api/v1/providers
/api/v1/provider-installations
/api/v1/accounts
/api/v1/accounts/{id}/profiles
/api/v1/accounts/{id}/quotas
/api/v1/accounts/{id}/budgets
/api/v1/sessions
/api/v1/processes
/api/v1/collection-runs
/api/v1/alerts
/api/v1/alert-rules
/api/v1/backups
/api/v1/exports
/api/v1/diagnostics
/api/v1/settings
```

These paths are architectural guidance, not authorization to implement before each owning module plan approves schemas and operations.

## HTTP semantics

- `GET` is safe and has no provider/profile mutations.
- `POST` creates resources or starts explicit actions.
- `PUT` replaces only where full replacement is meaningful.
- `PATCH` performs documented partial updates.
- `DELETE` archives/revokes/removes only where recovery/impact is explicit.
- State-changing retries use `Idempotency-Key` where duplicate action is harmful.
- Long operations return `202 Accepted` with a job/run resource rather than hold a request open.
- Use `ETag`/conditional requests or explicit version fields for concurrent configuration edits.

## Request and response conventions

- JSON property names use `snake_case` unless an accepted frontend-generation constraint proves otherwise.
- IDs are opaque strings.
- Timestamps are RFC 3339 UTC.
- Durations are integer milliseconds.
- Money and exact ratios follow the contract conventions document.
- Nullable, absent, unknown, and zero have separately documented meanings.
- Responses use direct typed resources; avoid a universal `data` wrapper unless pagination or metadata requires it.
- List endpoints use cursor pagination with deterministic ordering.
- Filters and sort fields are allowlisted and documented.
- Maximum page sizes are enforced.

## Error format

Use RFC 9457-style problem details with safe extensions:

```json
{
  "type": "https://agentmonitor.invalid/problems/authentication-required",
  "title": "Provider authentication required",
  "status": 409,
  "detail": "The selected monitoring profile requires re-authentication.",
  "instance": "/api/v1/collection-runs/opaque-id",
  "code": "provider_authentication_required",
  "correlation_id": "opaque-id",
  "errors": []
}
```

- `detail` is sanitized and useful to the owner.
- Validation errors identify safe field paths and reason codes.
- Stack traces, SQL, filesystem secrets, command output, tokens, and provider raw responses never appear.
- Stable machine-readable `code` values are versioned contracts.

## Authentication and authorization

### Browser

- Login establishes an HTTP-only same-origin session cookie.
- State-changing requests require CSRF proof.
- Logout invalidates server-side session state.
- The UI never stores API bearer tokens for its own normal session.

### API clients and Swagger

- `Authorization: Bearer <token>`.
- Token scopes are checked per operation.
- Token plaintext is accepted only for verification and never logged.
- Authentication failure does not reveal whether a token prefix exists.

Every route declares its permission dependency. Single-user status is not a reason to omit authorization.

## Collection actions

- Manual refresh returns/reuses a collection-run ID.
- Repeated refresh for the same account/capability joins or queues according to documented policy.
- API responses distinguish requested, queued, running, partial, succeeded, failed, blocked, and cancelled.
- Provider interactions are background work with deadlines.

## Event streaming

Near-real-time telemetry is not required. Server-Sent Events may be used for low-frequency dashboard notification and job progress after the ordinary REST behavior works.

- Event payloads use versioned event contracts.
- Reconnection and last-event ID behavior are documented.
- REST remains authoritative for current state.
- An SSE failure must not break collection or alerts.
- OpenAPI limitations for streaming are documented; the event schema is published separately if necessary.

## OpenAPI quality gates

- Unique stable `operationId` values.
- Explicit request/response models; no untyped dictionaries at public boundaries.
- Document all status codes and security requirements.
- Examples contain structural, non-secret values and are never presented as real account telemetry.
- Schema descriptions define units, nullability, precision, and provenance.
- OpenAPI validation passes.
- Compatibility diff passes for the declared API version.
- Generated TypeScript client compiles with strict TypeScript.
- Running-server contract tests confirm actual responses conform to the generated schema.

## API tests

API tests start a real server on an ephemeral loopback port, use a real temporary SQLite database and real migrations, and make actual HTTP requests. In-process route-function calls or a simulated transport do not count as API integration evidence.

Provider-backed API paths are verified with real enrolled accounts in the live test phase. CI does not replace unavailable providers with mocked responses.

## Rate and abuse controls

- Login attempts are rate limited.
- Manual refresh has per-principal/account/capability limits.
- Export, backup, token creation, and re-auth start operations are audited.
- Request body and response/page sizes are bounded.
- Correlation IDs are generated/validated and returned safely.

## Client-generation discipline

Frontend feature code imports the generated client through one shared adapter that handles base URL, browser session, CSRF, correlation ID, and problem mapping. Feature modules do not call `fetch` directly and do not redefine backend DTOs.
