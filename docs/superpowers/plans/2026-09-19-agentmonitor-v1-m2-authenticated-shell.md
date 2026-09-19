# AgentMonitor V1-M2 Authenticated Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a loopback-only dashboard shell with one real local administrator, durable server-side sessions and CSRF, least-privilege API tokens, generated `/api/v1` transport, and real built-browser login/logout/token workflows.

**Architecture:** M01 owns authentication, authorization, credential state, and `iam_*` persistence. P01 maps those ports to hardened loopback HTTP without duplicating security policy. P02 uses only the generated client through its shared wrapper; credentials never enter browser storage.

**Tech Stack:** Python, admitted Argon2id implementation, SQLite/Alembic, FastAPI/OpenAPI, React/TypeScript, generated API client, Playwright.

**Spec:** `docs/product/v1-specification.md`

## Milestone map

- Milestone: `V1-M2` — authenticated local dashboard shell.
- Epics: `EPIC-IAM-01`, `EPIC-API-01`, `EPIC-UI-01`.
- Detailed authority: [identity/access](../../plans/modules/m01-identity-access/plan-v1.md), [FastAPI boundary](../../plans/api/fastapi-boundary/plan-v1.md), and [React dashboard](../../plans/ui/react-dashboard/plan-v1.md).
- Contract versions: `CTR-IAM-001..008`, `CTR-API-001..003`, `CTR-COMMON-005`, and `CTR-UI-001`, all V1 only after producer/consumer and security approval.
- Entry gate: `V1-M1` has passed; exact Argon2 policy, cookie names/attributes, CSRF header, Origin/Host rules, session expiry, throttle policy, permissions, migration `v1_0100`, and shared writers are approved.
- Exit gate: real operator bootstrap, SQLite, loopback HTTP, malicious-origin denial, generated client, and built-browser login/session/logout/API-token scenarios pass. There is no HTTP bootstrap or provider authentication behavior.

## Global Constraints

- Use real cryptography, real file SQLite, a real loopback socket, and a real browser. No fake clock/repository/hasher, in-memory DB, direct route invocation, mocked HTTP, demo user, or seeded credential state.
- No default password or username. Bootstrap/recovery are local, exclusive, owner-present operations outside HTTP.
- Passwords, PHC strings, cookies, CSRF values, bearer plaintext, digests, idempotency keys, and request bodies never enter logs, events, screenshots, fixtures, or evidence.
- One-time session/CSRF and API-token secrets are never persisted or replayed. Idempotent replay returns `one_time_secret_not_replayable` with safe summary only.
- Browser authentication uses an `HttpOnly`, `SameSite=Strict`, path-root session cookie and a separate session-bound CSRF cookie/header proof. `localStorage` and `sessionStorage` remain credential-free.
- Provider reauthentication is outside M01. `dashboard_authentication_required` never represents a provider failure.
- Execute Stories serially at the shared migration, composition, OpenAPI, generated-client, `app/**`, and `shared/**` seams.

---

### Task 1: `ST-IAM-001` — M01 policy contracts, administrator bootstrap, and real persistence

**Epic:** `EPIC-IAM-01`

**Requirements / acceptance:** `FR-IAM-001`, `FR-IAM-002`, `FR-IAM-005`, `NFR-DATA-001`, `NFR-SEC-001`; `M01-PURE-001..005`, `M01-CRYPTO-001..004`, `M01-DB-001/002`.

**Contracts:** `CTR-IAM-001`, `CTR-IAM-002`, `CTR-IAM-004`, `CTR-IAM-008`, and `CTR-DB-002` at V1.

**Files:**
- Create: `backend/src/agentmonitor/contracts/identity_access_v1.py`
- Create: `backend/src/agentmonitor/modules/identity_access/domain/policy.py`
- Create: `backend/src/agentmonitor/modules/identity_access/application/bootstrap.py`
- Create: `backend/src/agentmonitor/adapters/persistence/identity_access/sqlite/repository.py`
- Create: `backend/migrations/versions/v1_0100_m01_identity_access.py`
- Modify: `backend/migrations/catalog.toml`
- Create: `backend/tests/identity_access/test_password_policy.py`
- Create: `backend/tests/integration/identity_access/test_bootstrap.py`

**Interfaces:**
- Publishes `PrincipalV1`, `SessionSummaryV1`, `ApiTokenSummaryV1`, `PermissionV1`, `AuthorizationDecisionV1`, `IamInitializationStateV1`, `IamHealthV1`, and `IamSecurityEventViewV1`.
- `BootstrapAdministratorV1(password: SecretInputV1, correlation_id: OpaqueIdV1) -> BootstrapAdministratorOutcomeV1`; `GetIamInitializationStateV1() -> IamInitializationStateV1`.
- Revision `v1_0100` creates only `iam_administrator`, `iam_browser_session`, `iam_api_token`, `iam_api_token_scope`, `iam_login_throttle`, `iam_idempotency_record`, and `iam_security_audit_event`.

- [ ] **Step 1: Write failing real-crypto/DB tests**

```python
def test_bootstrap_commits_one_administrator_with_argon2id(real_iam: RealIam) -> None:
    issued = real_iam.bootstrap(password=real_iam.owner_password)
    assert issued.outcome == "created"
    assert real_iam.scalar("select count(*) from iam_administrator") == 1
    assert real_iam.scalar("select password_phc from iam_administrator").startswith("$argon2id$")
    assert real_iam.bootstrap(password=real_iam.owner_password).outcome == "administrator_already_initialized"
```

- [ ] **Step 2: Run Red**

Run: `python3 -m pytest backend/tests/identity_access/test_password_policy.py backend/tests/integration/identity_access/test_bootstrap.py -q`

Expected: FAIL because the approved password policy, real Argon2 adapter, M01 repository, and `v1_0100` transaction do not exist.

- [ ] **Step 3: Implement minimum bootstrap behavior**

Use the admitted Argon2id library and approved benchmarked parameters; commit administrator and safe audit event atomically. Do not print the password or PHC and do not add an HTTP bootstrap route.

- [ ] **Step 4: Run Green on a migrated real file**

Run: `python3 -m pytest backend/tests/identity_access/test_password_policy.py backend/tests/integration/identity_access/test_bootstrap.py -q`

Expected: PASS with one administrator, distinct random salts across separate real databases, and an owner-only database file.

- [ ] **Step 5: Review and commit**

Review cryptography, migration, backup exposure, and recovery impacts; commit: `git commit -m "feat(iam): add administrator bootstrap and persistence"`.

---

### Task 2: `ST-IAM-002` — Durable sessions, CSRF, throttle, and authorization

**Epic:** `EPIC-IAM-01`

**Requirements / acceptance:** `FR-IAM-003`, `FR-IAM-004`, `FR-IAM-007`, `AC-UI-001`; `M01-DB-003..009`, `M01-HTTP-002..010/018..021`, `M01-SEC-001/008`.

**Contracts:** `CTR-IAM-001..005` and `CTR-IAM-007` at V1.

**Files:**
- Create: `backend/src/agentmonitor/modules/identity_access/application/sessions.py`
- Create: `backend/src/agentmonitor/modules/identity_access/application/authorization.py`
- Create: `backend/src/agentmonitor/modules/identity_access/application/throttle.py`
- Create: `backend/src/agentmonitor/adapters/persistence/identity_access/sqlite/sessions.py`
- Create: `backend/tests/integration/identity_access/test_sessions.py`
- Create: `backend/tests/integration/identity_access/test_csrf.py`

**Interfaces:**
- `AuthenticateAdministratorV1`, `ResolveBrowserSessionV1`, `VerifyCsrfV1`, `LogoutSessionV1`, `ListSessionsV1`, `RevokeSessionV1`, `RevokeAllSessionsV1`, and `AuthorizePrincipalV1`.
- `SessionCredentialIssueV1` is redacted/non-serializable and exists only long enough for P01 to set cookies; the database stores selector/digest data only.

- [ ] **Step 1: Write the failing cross-session CSRF test**

```python
def test_csrf_proof_is_bound_to_its_real_session(real_iam: RealIam) -> None:
    session_a = real_iam.login(real_iam.owner_password)
    session_b = real_iam.login(real_iam.owner_password)
    denied = real_iam.verify_csrf(session_b.session_credential, session_a.csrf_credential)
    assert denied.code == "csrf_validation_failed"
    assert real_iam.resolve_session(session_b.session_credential).active is True
```

- [ ] **Step 2: Run Red**

Run: `python3 -m pytest backend/tests/integration/identity_access/test_sessions.py backend/tests/integration/identity_access/test_csrf.py -q`

Expected: FAIL because session-bound proof, persistent throttle, expiry/revocation, and explicit permission decisions are absent.

- [ ] **Step 3: Implement minimum session policy**

Generate high-entropy credentials with approved primitives, store only digests, use safe comparison, enforce idle/absolute expiry, persist throttle transitions, and atomically write security events. A provider-auth outcome must not revoke a dashboard session.

- [ ] **Step 4: Run Green and security refactor suite**

Run: `python3 -m pytest backend/tests/identity_access backend/tests/integration/identity_access -q`

Expected: PASS for cross-session denial, restart-surviving revocation/throttle, generic wrong-password behavior, and permission denial.

- [ ] **Step 5: Review and commit**

Scan the real DB/WAL and captured logs for credential material; commit: `git commit -m "feat(iam): add sessions csrf and authorization"`.

---

### Task 3: `ST-IAM-003` — Least-privilege API-token lifecycle

**Epic:** `EPIC-IAM-01`

**Requirements / acceptance:** `FR-IAM-006`, `NFR-SEC-001`; `M01-DB-010..015`, `M01-HTTP-011..017`, `M01-SEC-001`.

**Contracts:** `CTR-IAM-001`, `CTR-IAM-002`, `CTR-IAM-006`, and `CTR-IAM-007` at V1.

**Files:**
- Create: `backend/src/agentmonitor/modules/identity_access/application/api_tokens.py`
- Create: `backend/src/agentmonitor/adapters/persistence/identity_access/sqlite/api_tokens.py`
- Create: `backend/tests/integration/identity_access/test_api_tokens.py`

**Interfaces:**
- `ResolveBearerTokenV1`, `ListApiTokensV1`, `CreateApiTokenV1`, `RotateApiTokenV1`, and `RevokeApiTokenV1`.
- `ApiTokenCredentialIssueV1` reveals plaintext once; scopes are a closed subset of approved V1 scopes and bearer callers cannot escalate beyond their effective scopes.

- [ ] **Step 1: Write the failing one-time-secret test**

```python
def test_token_idempotency_never_replays_plaintext(real_iam: RealIam) -> None:
    first = real_iam.create_token(name="collector", scopes=("read:status",), key="same-key")
    replay = real_iam.create_token(name="collector", scopes=("read:status",), key="same-key")
    assert first.plaintext is not None
    assert replay.code == "one_time_secret_not_replayable"
    assert not hasattr(replay, "plaintext")
```

- [ ] **Step 2: Run Red**

Run: `python3 -m pytest backend/tests/integration/identity_access/test_api_tokens.py -q`

Expected: FAIL because token issue, attenuation, rotation, revocation, and non-replay receipts are absent.

- [ ] **Step 3: Implement the minimum token lifecycle**

Persist public selector, digest, safe prefix, scopes, lifecycle, and idempotency receipt without plaintext. Rotation commits successor and predecessor transition atomically.

- [ ] **Step 4: Run Green and artifact scan**

Run: `python3 -m pytest backend/tests/integration/identity_access/test_api_tokens.py -q`

Expected: PASS; old/revoked bearer values fail, new values resolve exact scopes, and plaintext is absent from DB/WAL/log evidence.

- [ ] **Step 5: Review and commit**

Review attenuation and one-time disclosure semantics; commit: `git commit -m "feat(iam): add api token lifecycle"`.

---

### Task 4: `ST-API-001` — Hardened IAM HTTP boundary and generated client

**Epic:** `EPIC-API-01`

**Requirements / acceptance:** `NFR-API-001`, `NFR-API-002`, `FR-IAM-007`, `AC-TEST-004`; `API-PURE-001..010`, `API-HTTP-001..009/039/041`, `API-OAPI-001..004`, `API-CLIENT-004/006/007`.

**Contracts:** `CTR-API-001..003`, `CTR-COMMON-005`, and `CTR-IAM-001..007` at V1.

**Files:**
- Create: `backend/src/agentmonitor/api/problem.py`
- Create: `backend/src/agentmonitor/api/security_headers.py`
- Create: `backend/src/agentmonitor/api/transport.py`
- Create: `backend/src/agentmonitor/api/v1/dependencies.py`
- Create: `backend/src/agentmonitor/api/v1/routers/iam.py`
- Create: `backend/src/agentmonitor/api/v1/schemas/iam.py`
- Create: `backend/tests/integration/api/test_iam_http.py`
- Modify: `contracts/openapi/agentmonitor-v1.json`
- Modify: `frontend/src/generated/api/index.ts`

**Interfaces:**
- Exposes exact operations `iam_get_initialization_v1`, `iam_login_v1`, `iam_get_current_session_v1`, `iam_logout_v1`, `iam_change_password_v1`, `iam_list_sessions_v1`, `iam_revoke_session_v1`, `iam_revoke_other_sessions_v1`, `iam_list_api_tokens_v1`, `iam_create_api_token_v1`, `iam_rotate_api_token_v1`, `iam_revoke_api_token_v1`, and `iam_list_security_events_v1` on the paths in P01 section 12.1.
- Every non-success response is `SafeProblemV1`; cookie-plus-bearer ambiguity is rejected; initialized docs/OpenAPI require authentication.

- [ ] **Step 1: Write the failing real-socket security test**

```python
def test_login_and_csrf_over_real_loopback(real_http: RealHttp, owner_password: str) -> None:
    login = real_http.post("/api/v1/session", json={"password": owner_password}, origin=real_http.origin)
    assert login.status_code == 204
    assert login.cookies["session"].has_flag("HttpOnly")
    denied = real_http.delete("/api/v1/session", cookies=login.cookies, origin=real_http.origin)
    assert denied.status_code == 403
    assert denied.json()["code"] == "csrf_validation_failed"
```

- [ ] **Step 2: Run Red**

Run: `python3 -m pytest backend/tests/integration/api/test_iam_http.py -q`

Expected: FAIL because the production IAM routes and transport enforcement are not registered.

- [ ] **Step 3: Implement routes as thin contract mappings**

Enforce loopback bind, canonical Host/Origin, body bounds, security headers, cookie policy, CSRF, exact permissions, no-store token responses, and stable problem mapping. Do not embed M01 policy in route code.

- [ ] **Step 4: Run Green and regenerate**

Run: `python3 -m pytest backend/tests/integration/api/test_iam_http.py -q && python3 tooling/foundation/openapi_client.py --write && npm --prefix frontend run typecheck`

Expected: PASS; OpenAPI has unique exact operation IDs and the generated client compiles with no handwritten DTO.

- [ ] **Step 5: Review and commit**

The allocated integration writer commits source plus generated artifacts: `git commit -m "feat(api): expose hardened iam v1 routes"`.

---

### Task 5: `ST-UI-001` — Real-browser authentication and token settings

**Epic:** `EPIC-UI-01`

**Requirements / acceptance:** `AC-UI-001`, `NFR-API-002`, `NFR-SEC-001`; `UI-AUTH-001..010`, `UI-TOKEN-001..010`, `UI-SEC-001/003/004/006/011`.

**Contracts:** `CTR-UI-001`, `CTR-IAM-003`, `CTR-IAM-006`, and `CTR-IAM-007` at V1.

**Files:**
- Modify: `frontend/src/shared/api/client.ts`
- Create: `frontend/src/app/sessionBootstrap.ts`
- Create: `frontend/src/features/auth/LoginPage.tsx`
- Create: `frontend/src/features/auth/ProtectedRoute.tsx`
- Create: `frontend/src/features/settings/security/ApiTokensPage.tsx`
- Create: `frontend/tests/browser/p02/auth.spec.ts`
- Create: `frontend/tests/browser/p02/api-tokens.spec.ts`

**Interfaces:**
- The shared wrapper calls generated `iam_*_v1` operations, echoes the CSRF cookie only through `X-CSRF-Token`, and maps `dashboard_authentication_required` to session expiry.
- The one-time token modal cannot be reopened after dismissal or refresh; the UI never copies a token unless the owner explicitly invokes the copy control.

- [ ] **Step 1: Write the failing built-browser workflow**

```typescript
test("login, protected navigation, and logout use server state", async ({ page }) => {
  await page.goto(process.env.AGENTMONITOR_TEST_ORIGIN!);
  await page.getByLabel("Administrator password").fill(process.env.AGENTMONITOR_TEST_PASSWORD!);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "AgentMonitor" })).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});
```

- [ ] **Step 2: Run Red**

Run: `npm --prefix frontend run build && npx --prefix frontend playwright test frontend/tests/browser/p02/auth.spec.ts frontend/tests/browser/p02/api-tokens.spec.ts`

Expected: FAIL because the built application has no generated-client auth/token workflows.

- [ ] **Step 3: Implement the smallest accessible workflows**

Add keyboard/focus/error behavior, setup-required guidance to the native bootstrap runbook, login/session/logout, token list/create/rotate/revoke, one-time reveal, and expiry recovery. Do not place credentials in Web Storage or application state beyond the immediate one-time view.

- [ ] **Step 4: Run Green in a real browser**

Run: `npx --prefix frontend playwright test frontend/tests/browser/p02/auth.spec.ts frontend/tests/browser/p02/api-tokens.spec.ts`

Expected: PASS against the running production build and real M01 database.

- [ ] **Step 5: Review and commit**

Inspect browser storage/cookies, accessibility, and screenshots for secret leakage; commit: `git commit -m "feat(ui): add authenticated shell and token settings"`.

---

### Task 6: `ST-API-002` — Cross-origin denial and milestone integration gate

**Epic:** `EPIC-API-01`

**Requirements / acceptance:** `FR-IAM-007`, `AC-UI-001`, `AC-OPS-003`, `AC-TEST-001..004/006`; `M01-BROWSER-001..004`, `M01-SEC-001..008`, `API-BROWSER-001..007`.

**Contracts:** `CTR-API-001..003`, `CTR-COMMON-005`, `CTR-IAM-001..007`, and `CTR-UI-001` at V1.

**Files:**
- Create: `backend/tests/api/v1/test_origin_policy.py`
- Create: `frontend/tests/browser/p02/security-boundary.spec.ts`
- Create: `docs/modules/identity-access.md`
- Create: `docs/api/http-boundary.md`
- Create: `docs/modules/react-dashboard.md`

**Interfaces:**
- `authenticated_owner_session` is a real-loopback fixture exposing the live session cookie, CSRF header value, current-session ETag, and non-secret session ID created through the production login route.
- Cookie-authenticated unsafe requests require exact Origin plus valid CSRF; pure bearer requests require neither ambient-cookie CSRF nor browser Origin and remain scope-limited.
- Completion evidence is `TestEvidenceSummaryV1` with real T2/T3/T4 boundaries separated from unexecuted evidence.

- [ ] **Step 1: Write the failing real-socket Origin and bearer tests**

```python
def test_hostile_origin_is_rejected_before_logout(
    real_http: RealHttp,
    authenticated_owner_session: AuthenticatedOwnerSession,
) -> None:
    session = authenticated_owner_session
    before = real_http.get(
        "/api/v1/session", cookies=session.cookies, origin=real_http.origin
    )
    denied = real_http.delete(
        "/api/v1/session",
        cookies=session.cookies,
        origin="http://127.0.0.1:43119",
        headers={"X-CSRF-Token": session.csrf, "If-Match": session.etag},
    )
    after = real_http.get(
        "/api/v1/session", cookies=session.cookies, origin=real_http.origin
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "origin_not_allowed"
    assert before.status_code == after.status_code == 200
    assert before.json()["session_id"] == after.json()["session_id"] == session.session_id


def test_pure_bearer_is_origin_independent_but_still_authenticated(
    real_http: RealHttp,
    issued_write_tokens_bearer: str,
) -> None:
    allowed = real_http.get(
        "/api/v1/api-tokens",
        headers={"Authorization": f"Bearer {issued_write_tokens_bearer}"},
        origin="http://127.0.0.1:43119",
    )
    rejected = real_http.get(
        "/api/v1/api-tokens",
        headers={"Authorization": "Bearer invalid"},
        origin="http://127.0.0.1:43119",
    )
    assert allowed.status_code == 200
    assert rejected.status_code == 401
```

- [ ] **Step 2: Write the failing built-browser attack test**

```typescript
test("a hostile origin cannot mutate the loopback session", async ({ page }) => {
  const target = process.env.AGENTMONITOR_TEST_ORIGIN!;
  await page.goto(`${target}/login`);
  await page.getByLabel("Password").fill(process.env.AGENTMONITOR_OWNER_PASSWORD!);
  await page.getByRole("button", { name: "Sign in" }).click();
  const before = await page.evaluate(async () => {
    const response = await fetch("/api/v1/session", { credentials: "include" });
    return { status: response.status, sessionId: (await response.json()).session_id };
  });

  await page.goto(process.env.AGENTMONITOR_ATTACK_ORIGIN!);
  const outcome = await page.evaluate(async (target) => {
    try {
      await fetch(`${target}/api/v1/session`, { method: "DELETE", credentials: "include" });
      return "cross-origin-response-readable";
    } catch {
      return "cors-opaque-fetch-rejection";
    }
  }, target);
  expect(outcome).toBe("cors-opaque-fetch-rejection");

  await page.goto(`${target}/settings/api-tokens`);
  const after = await page.evaluate(async () => {
    const response = await fetch("/api/v1/session", { credentials: "include" });
    return { status: response.status, sessionId: (await response.json()).session_id };
  });
  expect(after).toEqual(before);
  await expect(page.getByRole("heading", { name: "API tokens" })).toBeVisible();
});
```

- [ ] **Step 3: Run Red before the final perimeter correction**

Run:

```bash
python3 -m pytest backend/tests/api/v1/test_origin_policy.py -q
npm --prefix frontend run build && npx --prefix frontend playwright test frontend/tests/browser/p02/security-boundary.spec.ts
```

Expected: the real-socket test FAILS if a hostile cookie request reaches logout or if bearer policy is tied to browser Origin; the browser test FAILS if the hostile page reads a response or the same real session is no longer authenticated after the opaque rejection. A missing real browser/server/password is Blocked, not Red.

- [ ] **Step 4: Make the minimum perimeter correction and document operations**

Correct only the production Host/Origin/CORS/CSRF mapping required by the failing case. Document bootstrap, login failure, session revocation, token compromise, and local recovery without including secrets.

- [ ] **Step 5: Run Green and the complete milestone gate**

Run:

```bash
python3 -m pytest backend/tests/api/v1/test_origin_policy.py -q
npx --prefix frontend playwright test frontend/tests/browser/p02/security-boundary.spec.ts
python3 tools/automation/run.py AUTO-TEST
python3 tools/automation/run.py AUTO-QUALITY
python3 tools/automation/run.py AUTO-BUILD
python3 tools/automation/run.py AUTO-DOCS-CHECK
```

Expected: exit `0`; real bootstrap, SQLite, Argon2, loopback HTTP, bearer, CSRF, cross-origin, built-browser, OpenAPI, and generated-client evidence all pass.

- [ ] **Step 6: Review, evidence, and commit**

Record Story IDs, `CTR-IAM/API/UI` versions, Red/Green/refactor commands, T2/T3/T4 results, and security/privacy/migration/license/docs impact; commit: `git add backend/tests/api/v1/test_origin_policy.py frontend/tests/browser/p02/security-boundary.spec.ts docs/modules/identity-access.md docs/api/http-boundary.md docs/modules/react-dashboard.md && git commit -m "feat(v1-m2): validate authenticated local shell"`.

## Completion rule

`V1-M2` is complete only after all six Stories are reviewed and the Task 6 gate passes against the real local stack. Provider authentication, absent live-browser evidence, or an unexecuted security scenario cannot be represented as a passing dashboard-auth result.
