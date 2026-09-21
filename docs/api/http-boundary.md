# AgentMonitor local IAM HTTP boundary (V1-M2)

Status: **Stories 4–6 and the V1-M2 local authenticated-shell exit gate accepted**.
This is the V1-M2 local-only profile, not approval of the all-V1 Draft P01 surface. The frozen authority is
the [M2 contract overlay](../evidence/m2-contract-freeze.md), the
[P01 module plan](../plans/api/fastapi-boundary/plan-v1.md), and the generated
[`agentmonitor-v1.json`](../../contracts/openapi/agentmonitor-v1.json).

## Boundary and resources

P01 accepts only one bound `http://127.0.0.1:<port>` authority. The installed
port defaults to `43110`; tests may bind ephemeral port zero. The request Host
must equal the actual bound authority; `localhost`, IPv6/wildcard, forwarded
host, and remote access are not alternate authorities. Browser login and
cookie-authenticated mutations require exact Origin. An Origin supplied on
cookie GET/HEAD or pre-auth initialization must match. Pure bearer requests
are Origin-independent but receive no CORS grant. A cookie plus bearer is
rejected before IAM resolution as `400 ambiguous_credentials`.

| Resource | Operation ID | Caller | Success |
|---|---|---|---|
| GET `/api/v1/iam/initialization` | `iam_get_initialization_v1` | Pre-auth | 200 safe state |
| POST `/api/v1/session` | `iam_login_v1` | Pre-auth, exact Origin | 204, session and CSRF cookies |
| GET `/api/v1/session` | `iam_get_current_session_v1` | Cookie, `read:self` | 200 summary + strong ETag |
| DELETE `/api/v1/session` | `iam_logout_v1` | Cookie, CSRF, `write:self`, If-Match | 204, clear cookies |
| PATCH `/api/v1/session/password` | `iam_change_password_v1` | Cookie, CSRF, `write:self`, If-Match, idempotency key | 204, fresh cookies |
| GET `/api/v1/iam/sessions` | `iam_list_sessions_v1` | Cookie, `write:sessions` | 200 bounded page |
| DELETE `/api/v1/iam/sessions/{session_id}` | `iam_revoke_session_v1` | Cookie, CSRF, `write:sessions`, If-Match | 204 |
| POST `/api/v1/iam/session-revocations` | `iam_revoke_other_sessions_v1` | Cookie, CSRF, `write:sessions`, idempotency key | 200 affected count |
| GET `/api/v1/api-tokens` | `iam_list_api_tokens_v1` | Cookie or bearer, `write:tokens` | 200 bounded page |
| POST `/api/v1/api-tokens` | `iam_create_api_token_v1` | Cookie+CSRF or bearer, `write:tokens`, idempotency key | 201 one-time issue |
| POST `/api/v1/api-tokens/{token_id}/rotations` | `iam_rotate_api_token_v1` | Cookie+CSRF or bearer, `write:tokens`, If-Match, idempotency key | 201 one-time issue |
| DELETE `/api/v1/api-tokens/{token_id}` | `iam_revoke_api_token_v1` | Cookie+CSRF or bearer, `write:tokens`, If-Match | 204 |
| GET `/api/v1/iam/security-events` | `iam_list_security_events_v1` | Cookie or bearer, `read:diagnostics` | 200 bounded safe page |

The initialization projection contains the three safe `CTR-IAM-004` fields:
`state`, nullable `policy_version`, and `schema_revision`; no credential or
setup secret is returned. Existing IAM request/success component names match
the P01 §12.9 catalog in the generated V1 OpenAPI/client. The M2
`iam_revoke_other_sessions_v1` operation has no body because its approved M01
port revokes all other sessions; P01 Draft §12.9's proposed
`RevokeSessionsInputV1` is not introduced as an invented M2 request.

The list resources use limit 1–200 (default 50), opaque cursor, and only
allowlisted filters. The M2 IAM list profile is deliberately narrower than the
all-V1 P01 proposal:

| List | Accepted query | Effective stable order |
|---|---|---|
| Sessions | `limit`, `cursor`, optional `sort=-issued_at` | `issued_at DESC, session_id DESC` |
| API tokens | `limit`, `cursor`, optional `sort=-issued_at` | `issued_at DESC, api_token_id DESC` |
| Security events | `limit`, `cursor`, optional `sort=-occurred_at`, `event_type`, `outcome`, `occurred_from`, `occurred_before` | `occurred_at DESC, event_id DESC` |

Omitted and explicit canonical sort mean the same order. A different sort,
unknown key/filter, malformed value, or repeated singleton query parameter
returns a safe 400. Filtering by session/token state, token scope/date, and
alternative sorts are not available in M2 and are absent from OpenAPI.
Time filters are half-open UTC `[occurred_from, occurred_before)`.

The `v1.` cursor envelope contains only the nonsecret M01 keyset ID, expiry,
and keyed query binding. It is URL-safe, HMAC-authenticated, valid for at most
15 minutes, and bound to the normalized query, administrator, credential ID,
authentication method, and effective permissions/scopes. An altered or expired
cursor returns `400 invalid_cursor`; valid cursor reuse under a different
binding returns `400 cursor_query_mismatch`. Each service lifespan generates
its own OS-random signing key and never persists or logs it, so restart
invalidates outstanding cursors. P01 decodes only the verified raw keyset ID
for M01; it never reads IAM tables or changes M01 query ordering.

IAM application ports own credential policy, atomic mutation, audit, and
SQLite state. P01 translates transport values and typed
outcomes; it does not query IAM tables. Every emitted IAM app/framework error
is `SafeProblemV1` with `application/problem+json`, a safe code, and
`X-Correlation-ID`; response detail contains no rejected input or exception.
`errors` is omitted for ordinary problems and present with safe field paths
for validation errors; it is never an invented `null`. By contrast,
`page.next_cursor` is always present and is explicit JSON `null` on the last
page. The OpenAPI/client contracts preserve this optional-versus-nullable
distinction. `detail` is an optional, non-null string in the V1 schema/client;
current M2 errors still emit the allowlisted detail string.
The optional, non-null `committed_resource` object appears only for committed
token-create/rotate one-time replay and contains the token ID, record version,
and state—never the bearer credential or scopes. Password replay and ordinary
problems omit it. This is an additive pre-release M2 schema/client correction.
Its `type` is the same-origin, root-relative `/problems/{closed_safe_code}`.
`GET /problems/{code}` is an authenticated local HTML documentation transport,
excluded from the 13-resource OpenAPI operation set; unknown codes receive a
safe 404 without reflecting the requested segment. Unrecognized application
port outcomes are collapsed to `500 internal_error`, whose type also resolves.
In IAM mode, the unauthenticated dashboard shell is served from the production
`dashboard.html` build at only `/`, `/login`, and `/settings/api-tokens`.
Authentication is enforced on versioned data operations, so a browser can load
the login shell without a session; unknown deep links do not silently become
the dashboard. Direct `/dashboard.html` and `/index.html` requests are denied;
only the built `/assets/*` files and `/favicon.svg` are static fallbacks in IAM
mode. Foundation mode continues to serve its original M1 entrypoint.
The shell routes do not appear in the versioned OpenAPI operation set and use
the same loopback Host/Origin guard, private no-store caching, and CSP as the
other IAM HTML transports.
The accepted correlation grammar is `[A-Za-z0-9._:-]{1,64}`. An absent ID is
OS-random. HTTP parser rejection before an ASGI scope exists (for example a
duplicate Host or malformed request line) is a narrow Uvicorn/h11 exception:
the wire request is denied but cannot carry an application SafeProblem or
correlation header. It is not counted as an app/framework Green assertion.
The same pure correlation validator is used by the live transport. Conditional
IAM mutations decode only positive-version strong ETags; weak, malformed,
multi-valued, or oversized tags fail with `412 precondition_failed` before an
M01 mutation. The generated OpenAPI gate validates the FastAPI OpenAPI 3.1
model and checks each of the 13 exact success status/body-schema pairs as well
as the published auth, port, replay, request-body schema, required SafeProblem
statuses, and other safe-problem policies.

Session and CSRF cookies are host-only, `Path=/`, `SameSite=Strict`, capped by
session absolute expiry; only the session is `HttpOnly`. Local plain HTTP uses
`Secure=false`. Valid and invalid logout clear presented cookies with matching
attributes. The response is `Cache-Control: no-store, private`. A real
authenticated browser must never put these credentials in browser storage.
The one-time bearer is never retrievable after issue; an authenticated same-key
replay returns `409 one_time_secret_not_replayable` without plaintext.
Committed token create/rotate retries include only the safe resource metadata
described above; no one-time secret is reconstructed.
For password change and token rotation, an authenticated same-key retry checks
the M01 receipt before a stale or wrong-subject `If-Match` is rejected. A new
request with that precondition still gets 412 without mutation. Revocation has
no one-time receipt and validates its precondition before the M01 transition.

Token creation/rotation deliberately omit `Location`. The P01 Draft §8.1
default would point to a non-existent GET-by-ID route; the frozen M2 surface has
only the 13 operations above. The safe token summary is in the 201 body and
the list route is the sole retrieval. No 14th route is inferred. This is an
approved M2-specific exception to that Draft default.

## Transport budgets and local operations

The request envelope admits at most 64 headers/16 KiB aggregate headers,
8 KiB JSON auth/token body, 32 in-flight requests, and a ten-second request
deadline (excluding bounded prebuilt static shell streaming). Credential
header/cookie values are bounded before IAM resolution. Unsupported JSON media
returns 415 before FastAPI body parsing. Static shell CSP allows only
same-origin script/style/connect; API CSP uses `default-src 'none'`. No
wildcard CORS, proxy-header trust, or server access log is enabled.

The IAM service holds a nonblocking exclusive `flock` on the stable
`<data_root>/.agentmonitor-service.lock` (regular, owner-owned, mode `0600`)
before database startup and through response drain/shutdown. It never unlinks
the file. The separately owned local forgotten-password command must acquire
that *same* lock before opening SQLite and refuse an occupied/unsafe file;
the command itself is not delivered by Story 4.

`GET /openapi.json`, `/docs`, `/redoc`, `/docs-assets/{family}/{filename}`,
and `/problems/{code}` are authenticated documentation transports, not resource
operations. The asset route has an exact allowlist; runtime makes no CDN or
package-manager requests. Swagger authorization is non-persistent. Its real
browser Try-it-out adds the CSRF cookie value as `X-CSRF-Token` for unsafe
cookie requests, but uses `credentials=omit` and no CSRF header when a bearer
is entered. Swagger and ReDoc use a separate same-origin script/style/connect
CSP; API JSON and every `application/problem+json` response retain the strict
`default-src 'none'; frame-ancestors 'none'` CSP, even on docs/assets paths.
The ReDoc 2.5.4 upstream bundle contains one unconditional external
footer-logo URL. The vendoring routine
verifies the exact source hash, replaces only that URL with a pinned same-origin
SVG, pins the derived bundle hash, and preserves upstream notices. The real
Chrome gate rejects any external request attempt.

## Story 6 cross-origin verification

The real-socket regression at
`backend/tests/integration/api/test_origin_policy.py` uses a freshly migrated
file SQLite installation, production Argon2 bootstrap and live Uvicorn. Its
hostile `DELETE /api/v1/session` carries an otherwise valid session cookie,
CSRF proof and current strong ETag; the 403 `origin_not_allowed` response leaves
the same session active. A supplied hostile Origin on cookie GET is denied;
cross-origin preflight grants no CORS access. A valid `write:tokens` bearer is
accepted with an absent or hostile Origin without CSRF, but remains scoped:
`read:diagnostics` is denied and an invalid bearer returns 401. None of these
responses grants `Access-Control-Allow-Origin`.

The built-Chrome regression at
`frontend/tests/browser/p02/security_boundary.mjs` loads a minimal attacker
page from a second real loopback HTTP origin. Credentialed browser GET and
DELETE attempts cannot read a cross-origin response, and navigation back to
the production dashboard still resolves the same persisted session ID. The
attacker page is local test input, not an AgentMonitor response substitute;
the target app, socket, database and Chrome are real. These checks were Green
on the existing Story 4 perimeter; they are not claimed as pre-fix Reds.

## Generated artifacts and verification

`tooling/foundation/openapi_client.py` generates the canonical OpenAPI JSON
and `frontend/src/generated/api/index.ts` from the same M2 route factory. The
generator checks the exact path/method/operation-ID matrix, local `$ref`s,
security schemes, problem media, source hashes, deterministic output, and
compatibility. Do not hand-edit either artifact. The real-client integration
test runs Node 22 against a live Uvicorn server and a freshly migrated file
SQLite installation, piping its ephemeral owner password through stdin only.
See [Story 4 evidence](../evidence/m2-st-api-001.md) for exact gate status.
The prior 502-pass/one-deselected non-docs run was a checkpoint, not the
complete Story gate; final complete regression is recorded separately there.
