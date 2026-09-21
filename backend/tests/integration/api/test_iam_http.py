"""ST-API-001 real Uvicorn/socket checks over migrated file-backed IAM state."""

from __future__ import annotations

import asyncio
import fcntl
import http.cookiejar
import json
import os
import secrets
import socket
import stat
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from email.message import Message
from pathlib import Path

from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
    SqliteIdentityAccessRepositoryV1,
)
from agentmonitor.composition.bootstrap import (
    create_iam_application,
    serve_loopback,
)
from agentmonitor.contracts.identity_access_v1 import SecretInputV1
from agentmonitor.foundation.application import LifecycleHooksV1
from agentmonitor.modules.identity_access.application.bootstrap import (
    BootstrapAdministratorV1,
)
from fastapi import FastAPI


@asynccontextmanager
async def _running(app: FastAPI) -> AsyncIterator[str]:
    stop = asyncio.Event()
    ready: asyncio.Future[str] = asyncio.get_running_loop().create_future()
    task = asyncio.create_task(
        serve_loopback(app, host="127.0.0.1", port=0, ready=ready.set_result, stop=stop)
    )
    try:
        finished, _ = await asyncio.wait(
            (ready, task), timeout=8, return_when=asyncio.FIRST_COMPLETED
        )
        assert finished, "real loopback server did not become ready"
        if task in finished:
            await task
            raise AssertionError("server exited before readiness")
        yield ready.result()
    finally:
        stop.set()
        await asyncio.wait_for(task, timeout=8)


def _request(
    origin: str,
    method: str,
    path: str,
    *,
    body: dict[str, object] | None = None,
    raw_body: bytes | None = None,
    headers: dict[str, str] | None = None,
    cookies: http.cookiejar.CookieJar | None = None,
) -> tuple[int, Message[str, str], bytes]:
    handlers: list[urllib.request.BaseHandler] = [urllib.request.ProxyHandler({})]
    if cookies is not None:
        handlers.append(urllib.request.HTTPCookieProcessor(cookies))
    opener = urllib.request.build_opener(*handlers)
    outgoing = {} if headers is None else headers.copy()
    if body is not None:
        outgoing["Content-Type"] = "application/json"
    request = urllib.request.Request(
        origin + path,
        data=json.dumps(body).encode("utf-8") if body is not None else raw_body,
        headers=outgoing,
        method=method,
    )
    try:
        with opener.open(request, timeout=10) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read()


def _session_cookies(jar: http.cookiejar.CookieJar) -> dict[str, str]:
    return {cookie.name: cookie.value for cookie in jar if cookie.value is not None}


def _raw_http(origin: str, request: bytes) -> bytes:
    port = int(origin.rsplit(":", 1)[1])
    with socket.create_connection(("127.0.0.1", port), timeout=12) as connection:
        connection.settimeout(12)
        connection.sendall(request)
        chunks: list[bytes] = []
        while chunk := connection.recv(65536):
            chunks.append(chunk)
        return b"".join(chunks)


def test_login_uses_real_migrated_iam_and_sets_two_cookies(tmp_path: Path) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    credential = secrets.token_urlsafe(32)
    outcome = BootstrapAdministratorV1(
        SqliteIdentityAccessRepositoryV1(reference), Argon2PasswordV1()
    )(SecretInputV1(credential), correlation_id="api-story4-bootstrap")
    assert outcome.code == "created"
    config = tmp_path / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    app = create_iam_application(config, tmp_path, lifecycle=LifecycleHooksV1())

    async def exercise() -> None:
        async with _running(app) as origin:
            status, headers, body = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                body={"password": credential},
                headers={"Origin": origin},
            )
            assert status == 204
            assert body == b""
            cookies = headers.get_all("Set-Cookie") or []
            assert len(cookies) == 2
            by_name = {item.split("=", 1)[0]: item for item in cookies}
            assert set(by_name) == {"agentmonitor_session", "agentmonitor_csrf"}
            for item in cookies:
                attributes = {part.strip().lower() for part in item.split(";")[1:]}
                assert "path=/" in attributes
                assert "samesite=strict" in attributes
                assert not any(part.startswith("domain=") for part in attributes)
                assert "secure" not in attributes  # exact loopback HTTP policy
                ages = [part for part in attributes if part.startswith("max-age=")]
                assert len(ages) == 1
                assert 1 <= int(ages[0].split("=", 1)[1]) <= 43200
            assert "httponly" in by_name["agentmonitor_session"].lower()
            assert "httponly" not in by_name["agentmonitor_csrf"].lower()
            assert headers.get("Cache-Control") == "no-store, private"

    asyncio.run(exercise())


def test_failed_logins_throttle_generically_over_real_http(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)
    wrong_password = secrets.token_urlsafe(32)
    assert wrong_password != credential

    async def exercise() -> None:
        async with _running(app) as origin:
            for index in range(5):
                response = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": wrong_password},
                    headers={"Origin": origin},
                )
                expected = 429 if index == 4 else 401
                assert response[0] == expected
                stored_credential_absent = credential.encode("ascii") not in response[2]
                wrong_credential_absent = (
                    wrong_password.encode("ascii") not in response[2]
                )
                assert stored_credential_absent is True, "credential reflected"
                assert wrong_credential_absent is True, "credential reflected"
                problem = json.loads(response[2])
                assert problem["code"] == (
                    "login_throttled" if index == 4 else "invalid_dashboard_credentials"
                )
                cookies_absent = not bool(response[1].get_all("Set-Cookie"))
                assert cookies_absent is True, "unexpected auth cookie"
                if index == 4:
                    retry = response[1].get("Retry-After")
                    assert retry is not None
                    assert 1 <= int(retry) <= 30
            correct_while_locked = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                body={"password": credential},
                headers={"Origin": origin},
            )
            assert correct_while_locked[0] == 429
            assert json.loads(correct_while_locked[2])["code"] == "login_throttled"
            cookies_absent = not bool(correct_while_locked[1].get_all("Set-Cookie"))
            assert cookies_absent is True, "unexpected auth cookie"

    asyncio.run(exercise())


def _installation(tmp_path: Path) -> tuple[FastAPI, str]:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    credential = secrets.token_urlsafe(32)
    outcome = BootstrapAdministratorV1(
        SqliteIdentityAccessRepositoryV1(reference), Argon2PasswordV1()
    )(SecretInputV1(credential), correlation_id="api-story4-setup")
    assert outcome.code == "created"
    config = tmp_path / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    return create_iam_application(
        config, tmp_path, lifecycle=LifecycleHooksV1()
    ), credential


def test_current_session_csrf_and_logout_use_real_cookie_jar(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            login = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                body={"password": credential},
                headers={"Origin": origin},
                cookies=jar,
            )
            assert login[0] == 204
            cookies = _session_cookies(jar)
            assert set(cookies) == {"agentmonitor_session", "agentmonitor_csrf"}
            current = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/session", cookies=jar
            )
            assert current[0] == 200
            assert json.loads(current[2])["state"] == "active"
            etag = current[1].get("ETag")
            assert etag
            denied = await asyncio.to_thread(
                _request,
                origin,
                "DELETE",
                "/api/v1/session",
                headers={"Origin": origin, "If-Match": etag},
                cookies=jar,
            )
            assert denied[0] == 403
            assert json.loads(denied[2])["code"] == "csrf_validation_failed"
            success = await asyncio.to_thread(
                _request,
                origin,
                "DELETE",
                "/api/v1/session",
                headers={
                    "Origin": origin,
                    "If-Match": etag,
                    "X-CSRF-Token": cookies["agentmonitor_csrf"],
                },
                cookies=jar,
            )
            assert success[0] == 204
            gone = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/session", cookies=jar
            )
            assert gone[0] == 401

    asyncio.run(exercise())


def test_token_issue_scope_denial_replay_and_openapi_over_real_socket(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            assert (await asyncio.to_thread(_request, origin, "GET", "/openapi.json"))[
                0
            ] == 401
            jar = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
            )[0] == 204
            csrf = _session_cookies(jar)["agentmonitor_csrf"]
            issue_key = secrets.token_urlsafe(18)
            created = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/api-tokens",
                body={"name": "audit-scope", "scopes": ["write:tokens"]},
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "Idempotency-Key": issue_key,
                },
                cookies=jar,
            )
            assert created[0] == 201
            assert created[1].get("Location") is None
            one_time = json.loads(created[2])["bearer_credential"]
            replay = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/api-tokens",
                body={"name": "audit-scope", "scopes": ["write:tokens"]},
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "Idempotency-Key": issue_key,
                },
                cookies=jar,
            )
            assert replay[0] == 409
            one_time_absent = one_time.encode("ascii") not in replay[2]
            assert one_time_absent is True, "credential reflected"
            assert json.loads(replay[2])["code"] == "one_time_secret_not_replayable"
            assert json.loads(replay[2])["committed_resource"] == {
                "api_token_id": json.loads(created[2])["token"]["api_token_id"],
                "record_version": json.loads(created[2])["token"]["record_version"],
                "state": json.loads(created[2])["token"]["state"],
            }
            bearer = {"Authorization": "Bearer " + one_time}
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    "/api/v1/api-tokens",
                    headers={**bearer, "Origin": "http://127.0.0.1:1"},
                )
            )[0] == 200
            ambiguous = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/api-tokens",
                headers=bearer,
                cookies=jar,
            )
            assert ambiguous[0] == 400
            assert json.loads(ambiguous[2])["code"] == "ambiguous_credentials"
            denied = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/iam/security-events",
                headers=bearer,
            )
            assert denied[0] == 403
            assert json.loads(denied[2])["code"] == "permission_denied"
            bearer_doc = await asyncio.to_thread(
                _request, origin, "GET", "/openapi.json", headers=bearer
            )
            assert bearer_doc[0] == 200
            doc = await asyncio.to_thread(
                _request, origin, "GET", "/openapi.json", cookies=jar
            )
            assert doc[0] == 200
            document = json.loads(doc[2])
            operations = {
                (path, method): record["operationId"]
                for path, methods in document["paths"].items()
                for method, record in methods.items()
            }
            assert operations == {
                ("/api/v1/iam/initialization", "get"): "iam_get_initialization_v1",
                ("/api/v1/session", "post"): "iam_login_v1",
                ("/api/v1/session", "get"): "iam_get_current_session_v1",
                ("/api/v1/session", "delete"): "iam_logout_v1",
                ("/api/v1/session/password", "patch"): "iam_change_password_v1",
                ("/api/v1/iam/sessions", "get"): "iam_list_sessions_v1",
                (
                    "/api/v1/iam/sessions/{session_id}",
                    "delete",
                ): "iam_revoke_session_v1",
                (
                    "/api/v1/iam/session-revocations",
                    "post",
                ): "iam_revoke_other_sessions_v1",
                ("/api/v1/api-tokens", "get"): "iam_list_api_tokens_v1",
                ("/api/v1/api-tokens", "post"): "iam_create_api_token_v1",
                (
                    "/api/v1/api-tokens/{token_id}/rotations",
                    "post",
                ): "iam_rotate_api_token_v1",
                ("/api/v1/api-tokens/{token_id}", "delete"): "iam_revoke_api_token_v1",
                ("/api/v1/iam/security-events", "get"): "iam_list_security_events_v1",
            }
            assert len(set(operations.values())) == 13
            components = document["components"]
            assert "SafeProblemV1" in components["schemas"]
            replay_schema = components["schemas"]["SafeCommittedApiTokenV1"]
            assert set(replay_schema["required"]) == {
                "api_token_id",
                "record_version",
                "state",
            }
            problem_schema = components["schemas"]["SafeProblemV1"]
            assert "committed_resource" in problem_schema["properties"]
            assert "committed_resource" not in problem_schema["required"]
            assert problem_schema["properties"]["committed_resource"]["$ref"] == (
                "#/components/schemas/SafeCommittedApiTokenV1"
            )
            assert "anyOf" not in problem_schema["properties"]["committed_resource"]
            assert set(components["securitySchemes"]) == {
                "BearerTokenV1",
                "BrowserSessionCookieV1",
                "BrowserCsrfHeaderV1",
            }
            header_rules = {
                "iam_logout_v1": {"If-Match"},
                "iam_change_password_v1": {"If-Match", "Idempotency-Key"},
                "iam_revoke_session_v1": {"If-Match"},
                "iam_revoke_other_sessions_v1": {"Idempotency-Key"},
                "iam_create_api_token_v1": {"Idempotency-Key"},
                "iam_rotate_api_token_v1": {"If-Match", "Idempotency-Key"},
                "iam_revoke_api_token_v1": {"If-Match"},
            }
            for methods in document["paths"].values():
                for operation in methods.values():
                    required_headers = {
                        parameter["name"]
                        for parameter in operation.get("parameters", [])
                        if parameter["in"] == "header" and parameter["required"]
                    }
                    assert required_headers == header_rules.get(
                        operation["operationId"], set()
                    )
                    assert {"404", "405", "504"} <= set(operation["responses"])
                    for status, response in operation["responses"].items():
                        if not status.startswith("2"):
                            content = response["content"]
                            assert set(content) == {"application/problem+json"}
                            assert content["application/problem+json"]["schema"] == {
                                "$ref": "#/components/schemas/SafeProblemV1"
                            }
                    for requirement in operation["security"]:
                        assert set(requirement) <= set(components["securitySchemes"])

    asyncio.run(exercise())


def test_documentation_transports_require_real_auth_and_use_local_assets(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    def assert_security_headers(headers: Message[str, str], *, docs: bool) -> None:
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("Referrer-Policy") == "no-referrer"
        assert headers.get("Permissions-Policy") == (
            "camera=(), microphone=(), geolocation=()"
        )
        assert headers.get("Cross-Origin-Resource-Policy") == "same-origin"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("Cache-Control") == "no-store, private"
        policy = headers.get("Content-Security-Policy", "")
        assert "frame-ancestors 'none'" in policy
        if docs:
            assert "object-src 'none'" in policy
            assert "script-src 'self'" in policy
            assert "connect-src 'self'" in policy
            assert "https:" not in policy
        else:
            assert policy == "default-src 'none'; frame-ancestors 'none'"

    async def exercise() -> None:
        async with _running(app) as origin:
            for path in ("/openapi.json", "/docs", "/redoc"):
                denied = await asyncio.to_thread(_request, origin, "GET", path)
                assert denied[0] == 401
                assert_security_headers(denied[1], docs=False)
                assert (
                    json.loads(denied[2])["code"] == "dashboard_authentication_required"
                )
            jar = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
            )[0] == 204
            csrf = _session_cookies(jar)["agentmonitor_csrf"]
            created = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/api-tokens",
                body={"name": "docs-access", "scopes": ["write:tokens"]},
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "Idempotency-Key": secrets.token_urlsafe(18),
                },
                cookies=jar,
            )
            assert created[0] == 201
            assert_security_headers(created[1], docs=False)
            bearer = json.loads(created[2])["bearer_credential"]
            for path in ("/openapi.json", "/docs", "/redoc"):
                with_cookie = await asyncio.to_thread(
                    _request, origin, "GET", path, cookies=jar
                )
                assert with_cookie[0] == 200
                assert_security_headers(with_cookie[1], docs=path != "/openapi.json")
                with_bearer = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    path,
                    headers={"Authorization": "Bearer " + bearer},
                )
                assert with_bearer[0] == 200
                if path != "/openapi.json":
                    assert b"https://" not in with_cookie[2]
                    assert b"http://" not in with_cookie[2]
                    csp = with_cookie[1].get("Content-Security-Policy", "")
                    assert "script-src 'self'" in csp
                    assert "connect-src 'self'" in csp
                    assert "https:" not in csp
            for path, media in (
                ("/docs-assets/swagger/swagger-ui.css", "text/css"),
                ("/docs-assets/swagger/swagger-ui-bundle.js", "application/javascript"),
                (
                    "/docs-assets/swagger/swagger-ui-standalone-preset.js",
                    "application/javascript",
                ),
                ("/docs-assets/swagger/bootstrap.js", "application/javascript"),
                ("/docs-assets/redoc/redoc.standalone.js", "application/javascript"),
                ("/docs-assets/redoc/bootstrap.js", "application/javascript"),
                ("/docs-assets/redoc/redoc-mark.svg", "image/svg+xml"),
            ):
                denied = await asyncio.to_thread(_request, origin, "GET", path)
                assert denied[0] == 401
                assert_security_headers(denied[1], docs=False)
                served = await asyncio.to_thread(
                    _request, origin, "GET", path, cookies=jar
                )
                assert served[0] == 200
                assert_security_headers(served[1], docs=True)
                assert served[1].get_content_type() == media
                assert served[2]
            unknown = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/docs-assets/swagger/not-an-approved-file.js",
                cookies=jar,
            )
            assert unknown[0] == 404
            assert_security_headers(unknown[1], docs=False)
            assert json.loads(unknown[2])["code"] == "resource_not_found"

    asyncio.run(exercise())


def test_login_requires_origin_even_with_unsupported_bearer(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            result = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                body={"password": credential},
                headers={"Authorization": "Bearer invalid"},
            )
            assert result[0] == 403
            assert json.loads(result[2])["code"] == "origin_not_allowed"
            cookies_absent = not bool(result[1].get_all("Set-Cookie"))
            assert cookies_absent is True, "unexpected auth cookie"

    asyncio.run(exercise())


def test_initialization_rejects_foreign_origin_even_with_bearer(
    tmp_path: Path,
) -> None:
    app, _ = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            response = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/iam/initialization",
                headers={
                    "Origin": "http://127.0.0.1:1",
                    "Authorization": "Bearer invalid",
                },
            )
            assert response[0] == 403
            assert json.loads(response[2])["code"] == "origin_not_allowed"

    asyncio.run(exercise())


def test_real_initialization_projection_preserves_safe_m01_fields(
    tmp_path: Path,
) -> None:
    app, _ = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            response = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/iam/initialization"
            )
            assert response[0] == 200
            body = json.loads(response[2])
            assert set(body) == {"state", "policy_version", "schema_revision"}
            assert body["state"] == "initialized"
            assert isinstance(body["policy_version"], str)
            assert body["policy_version"]
            assert isinstance(body["schema_revision"], str)
            assert body["schema_revision"]

    asyncio.run(exercise())


def test_real_http_correlation_id_survives_iam_audit_write(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)
    supplied_id = "a.b:c"

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
            )[0] == 204
            csrf = _session_cookies(jar)["agentmonitor_csrf"]
            created = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/api-tokens",
                body={"name": "trace-audit", "scopes": ["read:diagnostics"]},
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "X-Correlation-ID": supplied_id,
                    "Idempotency-Key": secrets.token_urlsafe(18),
                },
                cookies=jar,
            )
            assert created[0] == 201
            assert created[1].get("X-Correlation-ID") == supplied_id
            events = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/iam/security-events",
                cookies=jar,
            )
            assert events[0] == 200
            assert any(
                item["correlation_id"] == supplied_id
                for item in json.loads(events[2])["items"]
            )

    asyncio.run(exercise())


def test_correlation_grammar_extremes_over_real_socket(tmp_path: Path) -> None:
    app, _ = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            for value in ("a", "a.b:c-d_e", "A" * 64):
                response = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    "/api/v1/iam/initialization",
                    headers={"X-Correlation-ID": value},
                )
                assert response[0] == 200
                assert response[1].get("X-Correlation-ID") == value
            authority = origin.removeprefix("http://").encode("ascii")
            for raw_value in (b"", b"A" * 65, b"a b"):
                rejected = await asyncio.to_thread(
                    _raw_http,
                    origin,
                    b"GET /api/v1/iam/initialization HTTP/1.1\r\nHost: "
                    + authority
                    + b"\r\nX-Correlation-ID: "
                    + raw_value
                    + b"\r\nConnection: close\r\n\r\n",
                )
                assert b" 400 " in rejected.split(b"\r\n", 1)[0]
                assert b"invalid_correlation_id" in rejected

    asyncio.run(exercise())


def test_weak_etag_denies_real_logout_without_state_change(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            login = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                body={"password": credential},
                headers={"Origin": origin},
                cookies=jar,
            )
            assert login[0] == 204
            current = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/session", cookies=jar
            )
            assert current[0] == 200
            etag = current[1].get("ETag")
            assert etag and etag.startswith('"') and etag.endswith('"')
            weak = await asyncio.to_thread(
                _request,
                origin,
                "DELETE",
                "/api/v1/session",
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": _session_cookies(jar)["agentmonitor_csrf"],
                    "If-Match": "W/" + etag,
                },
                cookies=jar,
            )
            assert weak[0] == 412
            assert json.loads(weak[2])["code"] == "precondition_failed"
            assert (
                await asyncio.to_thread(
                    _request, origin, "GET", "/api/v1/session", cookies=jar
                )
            )[0] == 200

    asyncio.run(exercise())


def test_validation_error_never_reflects_unknown_submitted_field(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            response = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                body={"password": credential, "unknown_sensitive_field": True},
                headers={"Origin": origin},
            )
            assert response[0] == 422
            credential_absent = credential.encode("utf-8") not in response[2]
            assert credential_absent is True, "credential reflected"
            unknown_field_absent = b"unknown_sensitive_field" not in response[2]
            assert unknown_field_absent is True, "submitted field reflected"
            payload = json.loads(response[2])
            assert payload["code"] == "invalid_request_fields"
            assert payload["errors"] == [{"path": "/request", "code": "invalid_field"}]

    asyncio.run(exercise())


def test_raw_tcp_host_framing_and_header_budget_are_denied(tmp_path: Path) -> None:
    app, _ = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            authority = origin.removeprefix("http://").encode("ascii")
            path = b"GET /api/v1/iam/initialization HTTP/1.1\r\n"
            valid = await asyncio.to_thread(
                _raw_http,
                origin,
                path + b"Host: " + authority + b"\r\nConnection: close\r\n\r\n",
            )
            assert b" 200 " in valid.split(b"\r\n", 1)[0]
            for hostile_host in (b"localhost", b"127.0.0.1", b"bad host"):
                rejected = await asyncio.to_thread(
                    _raw_http,
                    origin,
                    path + b"Host: " + hostile_host + b"\r\nConnection: close\r\n\r\n",
                )
                assert b" 200 " not in rejected.split(b"\r\n", 1)[0]
            duplicated = await asyncio.to_thread(
                _raw_http,
                origin,
                path
                + b"Host: "
                + authority
                + b"\r\nHost: "
                + authority
                + b"\r\nConnection: close\r\n\r\n",
            )
            assert b" 200 " not in duplicated.split(b"\r\n", 1)[0]
            # h11 rejects duplicate Host before an ASGI scope exists.
            assert b" 400 " in duplicated.split(b"\r\n", 1)[0]
            invalid_correlation = await asyncio.to_thread(
                _raw_http,
                origin,
                path
                + b"Host: "
                + authority
                + b"\r\nX-Correlation-ID: a\xff\r\n"
                + b"Connection: close\r\n\r\n",
            )
            assert b" 400 " in invalid_correlation.split(b"\r\n", 1)[0]
            assert b"invalid_correlation_id" in invalid_correlation
            within_count = await asyncio.to_thread(
                _raw_http,
                origin,
                path
                + b"Host: "
                + authority
                + b"\r\n"
                + b"X-Bound: x\r\n" * 62
                + b"Connection: close\r\n\r\n",
            )
            assert b" 200 " in within_count.split(b"\r\n", 1)[0]
            oversized_count = await asyncio.to_thread(
                _raw_http,
                origin,
                path
                + b"Host: "
                + authority
                + b"\r\n"
                + b"X-Bound: x\r\n" * 64
                + b"Connection: close\r\n\r\n",
            )
            assert b" 413 " in oversized_count.split(b"\r\n", 1)[0]
            oversized_bytes = await asyncio.to_thread(
                _raw_http,
                origin,
                path
                + b"Host: "
                + authority
                + b"\r\nX-Bound: "
                + b"x" * (16 * 1024)
                + b"\r\nConnection: close\r\n\r\n",
            )
            assert b" 413 " in oversized_bytes.split(b"\r\n", 1)[0]

    asyncio.run(exercise())


def test_real_socket_concurrency_and_request_deadline(tmp_path: Path) -> None:
    app, _ = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            authority = origin.removeprefix("http://")
            port = int(origin.rsplit(":", 1)[1])
            pending: list[tuple[asyncio.StreamReader, asyncio.StreamWriter]] = []
            try:
                for _ in range(32):
                    reader, writer = await asyncio.open_connection("127.0.0.1", port)
                    writer.write(
                        f"POST /api/v1/session HTTP/1.1\r\n"
                        f"Host: {authority}\r\n"
                        f"Origin: {origin}\r\n"
                        "Content-Type: application/json\r\n"
                        "Content-Length: 2\r\n"
                        "Connection: close\r\n\r\n".encode("ascii")
                    )
                    await writer.drain()
                    pending.append((reader, writer))
                await asyncio.sleep(0.2)
                rejected = await asyncio.to_thread(
                    _raw_http,
                    origin,
                    f"GET /api/v1/iam/initialization HTTP/1.1\r\n"
                    f"Host: {authority}\r\nConnection: close\r\n\r\n".encode("ascii"),
                )
                assert b" 503 " in rejected.split(b"\r\n", 1)[0]
                assert b"request_capacity_exceeded" in rejected
                timed_out_headers = await asyncio.wait_for(
                    pending[0][0].readuntil(b"\r\n\r\n"), timeout=12
                )
                assert b" 504 " in timed_out_headers.split(b"\r\n", 1)[0]
                timed_out_body = await asyncio.wait_for(
                    pending[0][0].read(65536), timeout=2
                )
                assert b"request_timeout" in timed_out_body
            finally:
                for _, writer in pending:
                    writer.close()
                await asyncio.gather(
                    *(writer.wait_closed() for _, writer in pending),
                    return_exceptions=True,
                )

    asyncio.run(exercise())


def test_media_and_validation_errors_never_reflect_submitted_field(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            unsupported = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                raw_body=b"{}",
                headers={"Origin": origin, "Content-Type": "text/plain"},
            )
            assert unsupported[0] == 415
            assert json.loads(unsupported[2])["code"] == "unsupported_media_type"
            too_large = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                body={"password": "x" * (8 * 1024)},
                headers={"Origin": origin},
            )
            assert too_large[0] == 413
            assert json.loads(too_large[2])["code"] == "request_too_large"
            marker = secrets.token_urlsafe(18)
            rejected = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                body={"password": credential, marker: "unaccepted"},
                headers={"Origin": origin},
            )
            assert rejected[0] == 422
            credential_absent = credential.encode("utf-8") not in rejected[2]
            assert credential_absent is True, "credential reflected"
            marker_absent = marker.encode("ascii") not in rejected[2]
            assert marker_absent is True, "submitted field reflected"

    asyncio.run(exercise())


def test_password_change_rejects_multibyte_values_over_1024_utf8_bytes(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
            )[0] == 204
            csrf = _session_cookies(jar)["agentmonitor_csrf"]
            current = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/session", cookies=jar
            )
            assert current[0] == 200
            over_bytes = "é" * 1024
            assert len(over_bytes) == 1024
            assert len(over_bytes.encode("utf-8")) == 2048
            for current_password, new_password in (
                (over_bytes, secrets.token_urlsafe(32)),
                (credential, over_bytes),
            ):
                rejected = await asyncio.to_thread(
                    _request,
                    origin,
                    "PATCH",
                    "/api/v1/session/password",
                    body={
                        "current_password": current_password,
                        "new_password": new_password,
                    },
                    headers={
                        "Origin": origin,
                        "X-CSRF-Token": csrf,
                        "If-Match": current[1]["ETag"],
                        "Idempotency-Key": secrets.token_urlsafe(18),
                    },
                    cookies=jar,
                )
                assert rejected[0] == 422
                over_bytes_absent = over_bytes.encode("utf-8") not in rejected[2]
                assert over_bytes_absent is True, "credential reflected"
                assert json.loads(rejected[2])["code"] == "invalid_request_fields"
            assert (
                await asyncio.to_thread(
                    _request, origin, "GET", "/api/v1/session", cookies=jar
                )
            )[0] == 200

    asyncio.run(exercise())


def test_problem_perimeter_covers_framework_errors_and_private_headers(
    tmp_path: Path,
) -> None:
    app, _ = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            for method, path, expected in (
                ("GET", "/api/v1/unknown", 404),
                ("PUT", "/api/v1/iam/initialization", 405),
                ("GET", "/api/v1/session", 401),
            ):
                response = await asyncio.to_thread(
                    _request,
                    origin,
                    method,
                    path,
                    headers={"Origin": origin} if method == "PUT" else None,
                )
                assert response[0] == expected
                assert response[1].get_content_type() == "application/problem+json"
                assert response[1].get("Cache-Control") == "no-store, private"
                assert response[1].get("X-Content-Type-Options") == "nosniff"
                assert response[1].get("X-Correlation-ID")
                problem = json.loads(response[2])
                assert problem["status"] == expected
                assert problem["type"] == "/problems/" + problem["code"]
                assert problem["correlation_id"] == response[1].get("X-Correlation-ID")
                assert "traceback" not in response[2].decode("utf-8").lower()
                assert response[1].get("Access-Control-Allow-Origin") is None

    asyncio.run(exercise())


def test_problem_type_resolves_to_authenticated_local_allowlisted_html(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            denied = await asyncio.to_thread(_request, origin, "GET", "/api/v1/session")
            assert denied[0] == 401
            problem = json.loads(denied[2])
            assert problem["type"] == "/problems/dashboard_authentication_required"
            assert not problem["type"].startswith("http")
            protected = await asyncio.to_thread(
                _request, origin, "GET", problem["type"]
            )
            assert protected[0] == 401
            assert protected[1].get_content_type() == "application/problem+json"
            jar = http.cookiejar.CookieJar()
            login = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                body={"password": credential},
                headers={"Origin": origin},
                cookies=jar,
            )
            assert login[0] == 204
            documented = await asyncio.to_thread(
                _request, origin, "GET", problem["type"], cookies=jar
            )
            assert documented[0] == 200
            credential_absent = credential.encode() not in documented[2]
            assert credential_absent is True, "credential reflected"
            assert documented[1].get_content_type() == "text/html"
            assert "default-src 'none'" in documented[1]["Content-Security-Policy"]
            has_documented_code = b"dashboard_authentication_required" in documented[2]
            assert has_documented_code is True, "safe problem help missing"
            has_no_external_url = (
                b"https://" not in documented[2] and b"http://" not in documented[2]
            )
            assert has_no_external_url is True, "external URL in local problem help"
            marker = secrets.token_urlsafe(18)
            unknown = await asyncio.to_thread(
                _request, origin, "GET", "/problems/" + marker, cookies=jar
            )
            assert unknown[0] == 404
            marker_absent = marker.encode() not in unknown[2]
            assert marker_absent is True, "requested path reflected"
            assert unknown[1].get_content_type() == "application/problem+json"
            assert json.loads(unknown[2])["type"] == "/problems/resource_not_found"

    asyncio.run(exercise())


def test_invalid_presented_session_clears_both_cookie_names(tmp_path: Path) -> None:
    app, _ = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            invalid = secrets.token_urlsafe(36)
            response = await asyncio.to_thread(
                _request,
                origin,
                "DELETE",
                "/api/v1/session",
                headers={
                    "Origin": origin,
                    "Cookie": (
                        f"agentmonitor_session={invalid}; agentmonitor_csrf={invalid}"
                    ),
                },
            )
            assert response[0] == 401
            assert (
                json.loads(response[2])["code"] == "dashboard_authentication_required"
            )
            clearing = response[1].get_all("Set-Cookie") or []
            assert len(clearing) == 2
            assert any(value.startswith("agentmonitor_session=") for value in clearing)
            assert any(value.startswith("agentmonitor_csrf=") for value in clearing)
            assert all("samesite=strict" in value.lower() for value in clearing)

    asyncio.run(exercise())


def test_invalid_logout_clears_presented_csrf_cookie_without_session(
    tmp_path: Path,
) -> None:
    app, _ = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            response = await asyncio.to_thread(
                _request,
                origin,
                "DELETE",
                "/api/v1/session",
                headers={
                    "Origin": origin,
                    "Cookie": f"agentmonitor_csrf={secrets.token_urlsafe(36)}",
                },
            )
            assert response[0] == 401
            assert (
                json.loads(response[2])["code"] == "dashboard_authentication_required"
            )
            clearing = response[1].get_all("Set-Cookie") or []
            assert len(clearing) == 1
            assert clearing[0].startswith("agentmonitor_csrf=")
            assert "max-age=0" in clearing[0].lower()

    asyncio.run(exercise())


def test_failed_login_does_not_clear_an_existing_valid_session(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
            )[0] == 204
            invalid = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                body={"password": secrets.token_urlsafe(32)},
                headers={"Origin": origin},
                cookies=jar,
            )
            assert invalid[0] == 401
            assert json.loads(invalid[2])["code"] == "invalid_dashboard_credentials"
            cookies_absent = not bool(invalid[1].get_all("Set-Cookie"))
            assert cookies_absent is True, "unexpected auth cookie"
            assert (
                await asyncio.to_thread(
                    _request, origin, "GET", "/api/v1/session", cookies=jar
                )
            )[0] == 200

    asyncio.run(exercise())


def test_stale_mutation_precondition_returns_412_over_real_socket(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
            )[0] == 204
            csrf = _session_cookies(jar)["agentmonitor_csrf"]
            created = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/api-tokens",
                body={"name": "precondition", "scopes": ["write:tokens"]},
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "Idempotency-Key": secrets.token_urlsafe(18),
                },
                cookies=jar,
            )
            assert created[0] == 201
            token_id = json.loads(created[2])["token"]["api_token_id"]
            stale = await asyncio.to_thread(
                _request,
                origin,
                "DELETE",
                f"/api/v1/api-tokens/{token_id}",
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "If-Match": f'"{token_id}.999"',
                },
                cookies=jar,
            )
            assert stale[0] == 412
            assert json.loads(stale[2])["code"] == "precondition_failed"

    asyncio.run(exercise())


def test_stale_session_preconditions_distinguish_active_from_terminal_conflict(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            actor = http.cookiejar.CookieJar()
            target = http.cookiejar.CookieJar()
            for jar in (actor, target):
                assert (
                    await asyncio.to_thread(
                        _request,
                        origin,
                        "POST",
                        "/api/v1/session",
                        body={"password": credential},
                        headers={"Origin": origin},
                        cookies=jar,
                    )
                )[0] == 204
            current = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/session", cookies=actor
            )
            assert current[0] == 200
            actor_id = json.loads(current[2])["session_id"]
            csrf = _session_cookies(actor)["agentmonitor_csrf"]
            stale_actor_etag = f'"{actor_id}.999"'
            logout = await asyncio.to_thread(
                _request,
                origin,
                "DELETE",
                "/api/v1/session",
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "If-Match": stale_actor_etag,
                },
                cookies=actor,
            )
            assert logout[0] == 412
            assert json.loads(logout[2])["code"] == "precondition_failed"
            listed = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/iam/sessions", cookies=actor
            )
            assert listed[0] == 200
            target_id = next(
                item["session_id"]
                for item in json.loads(listed[2])["items"]
                if item["session_id"] != actor_id
            )
            revoke = await asyncio.to_thread(
                _request,
                origin,
                "DELETE",
                f"/api/v1/iam/sessions/{target_id}",
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "If-Match": f'"{target_id}.999"',
                },
                cookies=actor,
            )
            assert revoke[0] == 412
            assert json.loads(revoke[2])["code"] == "precondition_failed"
            password = await asyncio.to_thread(
                _request,
                origin,
                "PATCH",
                "/api/v1/session/password",
                body={
                    "current_password": credential,
                    "new_password": secrets.token_urlsafe(32),
                },
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "If-Match": stale_actor_etag,
                    "Idempotency-Key": secrets.token_urlsafe(18),
                },
                cookies=actor,
            )
            assert password[0] == 412
            assert json.loads(password[2])["code"] == "precondition_failed"
            assert (
                await asyncio.to_thread(
                    _request, origin, "GET", "/api/v1/session", cookies=target
                )
            )[0] == 200

    asyncio.run(exercise())


def test_all_iam_mutation_routes_change_real_persisted_state(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            actor = http.cookiejar.CookieJar()
            target = http.cookiejar.CookieJar()
            for jar in (actor, target):
                login = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
                assert login[0] == 204
            csrf = _session_cookies(actor)["agentmonitor_csrf"]
            sessions = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/iam/sessions", cookies=actor
            )
            assert sessions[0] == 200
            items = json.loads(sessions[2])["items"]
            assert len(items) == 2
            other = next(item for item in items if not item["is_current"])
            other_id = other["session_id"]
            revoked = await asyncio.to_thread(
                _request,
                origin,
                "DELETE",
                f"/api/v1/iam/sessions/{other_id}",
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "If-Match": f'"{other_id}.{other["record_version"]}"',
                },
                cookies=actor,
            )
            assert revoked[0] == 204
            assert (
                await asyncio.to_thread(
                    _request, origin, "GET", "/api/v1/session", cookies=target
                )
            )[0] == 401

            newer = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=newer,
                )
            )[0] == 204
            revoke_key = secrets.token_urlsafe(18)
            all_others = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/iam/session-revocations",
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "Idempotency-Key": revoke_key,
                },
                cookies=actor,
            )
            assert all_others[0] == 200
            assert json.loads(all_others[2])["affected_count"] == 1
            assert (
                await asyncio.to_thread(
                    _request, origin, "GET", "/api/v1/session", cookies=newer
                )
            )[0] == 401
            repeated = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/iam/session-revocations",
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "Idempotency-Key": revoke_key,
                },
                cookies=actor,
            )
            assert repeated[0] == 200
            assert repeated[2] == all_others[2]

            created = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/api-tokens",
                body={"name": "lifecycle", "scopes": ["write:tokens"]},
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "Idempotency-Key": secrets.token_urlsafe(18),
                },
                cookies=actor,
            )
            assert created[0] == 201
            old_id = json.loads(created[2])["token"]["api_token_id"]
            old_version = json.loads(created[2])["token"]["record_version"]
            old_bearer = json.loads(created[2])["bearer_credential"]
            rotation_key = secrets.token_urlsafe(18)
            rotated = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                f"/api/v1/api-tokens/{old_id}/rotations",
                body={"name": "rotated"},
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "If-Match": created[1]["ETag"],
                    "Idempotency-Key": rotation_key,
                },
                cookies=actor,
            )
            assert rotated[0] == 201
            new_id = json.loads(rotated[2])["token"]["api_token_id"]
            new_bearer = json.loads(rotated[2])["bearer_credential"]
            assert new_id != old_id
            replay_wrong_subject = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                f"/api/v1/api-tokens/{old_id}/rotations",
                body={"name": "rotated"},
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "If-Match": f'"{new_id}.{old_version}"',
                    "Idempotency-Key": rotation_key,
                },
                cookies=actor,
            )
            assert replay_wrong_subject[0] == 409
            assert (
                json.loads(replay_wrong_subject[2])["code"]
                == "one_time_secret_not_replayable"
            )
            assert json.loads(replay_wrong_subject[2])["committed_resource"] == {
                "api_token_id": new_id,
                "record_version": json.loads(rotated[2])["token"]["record_version"],
                "state": json.loads(rotated[2])["token"]["state"],
            }
            fresh_wrong_subject = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                f"/api/v1/api-tokens/{old_id}/rotations",
                body={"name": "rotated"},
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "If-Match": f'"{new_id}.{old_version}"',
                    "Idempotency-Key": secrets.token_urlsafe(18),
                },
                cookies=actor,
            )
            assert fresh_wrong_subject[0] == 412
            assert json.loads(fresh_wrong_subject[2])["code"] == "precondition_failed"
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    "/api/v1/api-tokens",
                    headers={"Authorization": "Bearer " + old_bearer},
                )
            )[0] == 401
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    "/api/v1/api-tokens",
                    headers={"Authorization": "Bearer " + new_bearer},
                )
            )[0] == 200
            tokens = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/api-tokens", cookies=actor
            )
            assert tokens[0] == 200
            new_version = next(
                item["record_version"]
                for item in json.loads(tokens[2])["items"]
                if item["api_token_id"] == new_id
            )
            token_revoke = await asyncio.to_thread(
                _request,
                origin,
                "DELETE",
                f"/api/v1/api-tokens/{new_id}",
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "If-Match": f'"{new_id}.{new_version}"',
                },
                cookies=actor,
            )
            assert token_revoke[0] == 204
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    "/api/v1/api-tokens",
                    headers={"Authorization": "Bearer " + new_bearer},
                )
            )[0] == 401

            current = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/session", cookies=actor
            )
            assert current[0] == 200
            new_password = secrets.token_urlsafe(32)
            changed = await asyncio.to_thread(
                _request,
                origin,
                "PATCH",
                "/api/v1/session/password",
                body={
                    "current_password": credential,
                    "new_password": new_password,
                },
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "If-Match": current[1]["ETag"],
                    "Idempotency-Key": secrets.token_urlsafe(18),
                },
                cookies=actor,
            )
            assert changed[0] == 204
            assert (
                await asyncio.to_thread(
                    _request, origin, "GET", "/api/v1/session", cookies=actor
                )
            )[0] == 200
            fresh = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": new_password},
                    headers={"Origin": origin},
                    cookies=fresh,
                )
            )[0] == 204

    asyncio.run(exercise())


def test_password_change_replay_checks_live_auth_before_receipt_and_version(
    tmp_path: Path,
) -> None:
    app, old_password = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            old_jar = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": old_password},
                    headers={"Origin": origin},
                    cookies=old_jar,
                )
            )[0] == 204
            old_cookies = _session_cookies(old_jar)
            old_cookie_header = "; ".join(
                f"{name}={value}" for name, value in old_cookies.items()
            )
            current = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/session", cookies=old_jar
            )
            assert current[0] == 200
            key = secrets.token_urlsafe(18)
            new_password = secrets.token_urlsafe(32)
            body: dict[str, object] = {
                "current_password": old_password,
                "new_password": new_password,
            }
            changed = await asyncio.to_thread(
                _request,
                origin,
                "PATCH",
                "/api/v1/session/password",
                body=body,
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": old_cookies["agentmonitor_csrf"],
                    "If-Match": current[1]["ETag"],
                    "Idempotency-Key": key,
                },
                cookies=old_jar,
            )
            assert changed[0] == 204
            stale_credential_retry = await asyncio.to_thread(
                _request,
                origin,
                "PATCH",
                "/api/v1/session/password",
                body=body,
                headers={
                    "Origin": origin,
                    "Cookie": old_cookie_header,
                    "X-CSRF-Token": old_cookies["agentmonitor_csrf"],
                    "If-Match": current[1]["ETag"],
                    "Idempotency-Key": key,
                },
            )
            assert stale_credential_retry[0] == 401
            assert (
                json.loads(stale_credential_retry[2])["code"]
                == "dashboard_authentication_required"
            )
            fresh_jar = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": new_password},
                    headers={"Origin": origin},
                    cookies=fresh_jar,
                )
            )[0] == 204
            fresh_csrf = _session_cookies(fresh_jar)["agentmonitor_csrf"]
            fresh_current = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/session", cookies=fresh_jar
            )
            assert fresh_current[0] == 200
            fresh_id = json.loads(fresh_current[2])["session_id"]
            old_subject_replay = await asyncio.to_thread(
                _request,
                origin,
                "PATCH",
                "/api/v1/session/password",
                body=body,
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": fresh_csrf,
                    "If-Match": current[1]["ETag"],
                    "Idempotency-Key": key,
                },
                cookies=fresh_jar,
            )
            assert old_subject_replay[0] == 409
            assert (
                json.loads(old_subject_replay[2])["code"]
                == "one_time_secret_not_replayable"
            )
            authenticated_replay = await asyncio.to_thread(
                _request,
                origin,
                "PATCH",
                "/api/v1/session/password",
                body=body,
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": fresh_csrf,
                    "If-Match": f'"{fresh_id}.999"',
                    "Idempotency-Key": key,
                },
                cookies=fresh_jar,
            )
            assert authenticated_replay[0] == 409
            new_password_absent = new_password.encode() not in authenticated_replay[2]
            assert new_password_absent is True, "credential reflected"
            assert (
                json.loads(authenticated_replay[2])["code"]
                == "one_time_secret_not_replayable"
            )
            assert "committed_resource" not in json.loads(authenticated_replay[2])
            no_receipt = await asyncio.to_thread(
                _request,
                origin,
                "PATCH",
                "/api/v1/session/password",
                body=body,
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": fresh_csrf,
                    "If-Match": current[1]["ETag"],
                    "Idempotency-Key": secrets.token_urlsafe(18),
                },
                cookies=fresh_jar,
            )
            assert no_receipt[0] == 412
            assert json.loads(no_receipt[2])["code"] == "precondition_failed"
            still_current = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/session", cookies=fresh_jar
            )
            assert still_current[0] == 200
            assert still_current[1]["ETag"] == fresh_current[1]["ETag"]

    asyncio.run(exercise())


def test_iam_session_cursor_is_signed_query_bound_and_restart_invalidated(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        jars = [http.cookiejar.CookieJar() for _ in range(3)]
        async with _running(app) as origin:
            for jar in jars:
                login = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
                assert login[0] == 204
            first = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/iam/sessions?limit=1",
                cookies=jars[0],
            )
            assert first[0] == 200
            page = json.loads(first[2])
            assert page["page"]["has_more"] is True
            cursor = page["page"]["next_cursor"]
            assert isinstance(cursor, str) and cursor.startswith("v1.")
            assert cursor != page["items"][0]["session_id"]
            assert cursor.isascii() and len(cursor) <= 1024
            suffix = urllib.parse.urlencode({"limit": 1, "cursor": cursor})
            second = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/iam/sessions?" + suffix,
                cookies=jars[0],
            )
            assert second[0] == 200
            assert (
                json.loads(second[2])["items"][0]["session_id"]
                != page["items"][0]["session_id"]
            )
            explicit_default = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/iam/sessions?" + suffix + "&sort=-issued_at",
                cookies=jars[0],
            )
            assert explicit_default[0] == 200
            explicit_page = json.loads(explicit_default[2])
            assert [item["session_id"] for item in explicit_page["items"]] == [
                item["session_id"] for item in json.loads(second[2])["items"]
            ]
            assert (
                explicit_page["page"]["has_more"]
                == json.loads(second[2])["page"]["has_more"]
            )
            wrong_query = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/iam/sessions?"
                + urllib.parse.urlencode({"limit": 2, "cursor": cursor}),
                cookies=jars[0],
            )
            assert wrong_query[0] == 400
            assert json.loads(wrong_query[2])["code"] == "cursor_query_mismatch"
            wrong_session = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/iam/sessions?" + suffix,
                cookies=jars[1],
            )
            assert wrong_session[0] == 400
            assert json.loads(wrong_session[2])["code"] == "cursor_query_mismatch"
            midpoint = len(cursor) // 2
            tampered = (
                cursor[:midpoint]
                + ("A" if cursor[midpoint] != "A" else "B")
                + cursor[midpoint + 1 :]
            )
            invalid = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/iam/sessions?"
                + urllib.parse.urlencode({"limit": 1, "cursor": tampered}),
                cookies=jars[0],
            )
            assert invalid[0] == 400
            assert json.loads(invalid[2])["code"] == "invalid_cursor"
        restarted_app = create_iam_application(
            tmp_path / "isolated.env", tmp_path, lifecycle=LifecycleHooksV1()
        )
        async with _running(restarted_app) as restarted_origin:
            expired_key = await asyncio.to_thread(
                _request,
                restarted_origin,
                "GET",
                "/api/v1/iam/sessions?" + suffix,
                cookies=jars[0],
            )
            assert expired_key[0] == 400
            assert json.loads(expired_key[2])["code"] == "invalid_cursor"

    asyncio.run(exercise())


def test_iam_cursor_rejects_reuse_with_another_page_size_over_real_socket(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            for _ in range(2):
                login = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
                assert login[0] == 204
            first = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/iam/sessions?limit=1",
                cookies=jar,
            )
            assert first[0] == 200
            cursor = json.loads(first[2])["page"]["next_cursor"]
            assert isinstance(cursor, str)
            reused = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/iam/sessions?"
                + urllib.parse.urlencode({"limit": 2, "cursor": cursor}),
                cookies=jar,
            )
            assert reused[0] == 400
            assert json.loads(reused[2])["code"] == "cursor_query_mismatch"

    asyncio.run(exercise())


def test_iam_list_repeated_singletons_and_event_filter_are_denied(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            login = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                body={"password": credential},
                headers={"Origin": origin},
                cookies=jar,
            )
            assert login[0] == 204
            for path in (
                "/api/v1/iam/sessions?limit=1&limit=2",
                "/api/v1/api-tokens?cursor=x&cursor=y",
                "/api/v1/iam/security-events?event_type=login_succeeded&event_type=login_succeeded",
            ):
                rejected = await asyncio.to_thread(
                    _request, origin, "GET", path, cookies=jar
                )
                assert rejected[0] == 400

    asyncio.run(exercise())


def test_iam_list_authentication_precedes_malformed_query_policy(
    tmp_path: Path,
) -> None:
    app, _ = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            for path in (
                "/api/v1/iam/sessions?sort=secret",
                "/api/v1/api-tokens?limit=0",
                "/api/v1/iam/security-events?event_type=",
            ):
                denied = await asyncio.to_thread(_request, origin, "GET", path)
                assert denied[0] == 401
                assert (
                    json.loads(denied[2])["code"] == "dashboard_authentication_required"
                )

    asyncio.run(exercise())


def test_iam_list_sort_filter_and_singleton_query_profiles_over_real_socket(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            for _ in range(2):
                assert (
                    await asyncio.to_thread(
                        _request,
                        origin,
                        "POST",
                        "/api/v1/session",
                        body={"password": credential},
                        headers={"Origin": origin},
                        cookies=jar,
                    )
                )[0] == 204
            csrf = _session_cookies(jar)["agentmonitor_csrf"]
            bearers: list[str] = []
            for index in range(2):
                created = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/api-tokens",
                    body={"name": f"list-{index}", "scopes": ["write:tokens"]},
                    headers={
                        "Origin": origin,
                        "X-CSRF-Token": csrf,
                        "Idempotency-Key": secrets.token_urlsafe(18),
                    },
                    cookies=jar,
                )
                assert created[0] == 201
                bearers.append(json.loads(created[2])["bearer_credential"])
            profiles = (
                ("/api/v1/iam/sessions", "-issued_at", {"state": "active"}),
                ("/api/v1/api-tokens", "-issued_at", {"scope": "write:tokens"}),
                ("/api/v1/iam/security-events", "-occurred_at", {"state": "active"}),
            )
            published = await asyncio.to_thread(
                _request, origin, "GET", "/openapi.json", cookies=jar
            )
            assert published[0] == 200
            operations = json.loads(published[2])["paths"]
            for path, sort, unsupported in profiles:
                parameters = {
                    item["name"]: item
                    for item in operations[path]["get"]["parameters"]
                    if item["in"] == "query"
                }
                expected = {"limit", "cursor", "sort"}
                if path.endswith("security-events"):
                    expected |= {
                        "event_type",
                        "outcome",
                        "occurred_from",
                        "occurred_before",
                    }
                assert set(parameters) == expected
                assert parameters["sort"]["schema"]["enum"] == [sort]
                accepted = await asyncio.to_thread(
                    _request, origin, "GET", path + "?limit=1&sort=" + sort, cookies=jar
                )
                assert accepted[0] == 200
                assert json.loads(accepted[2])["page"]["has_more"] is True
                ordered = await asyncio.to_thread(
                    _request, origin, "GET", path + "?sort=" + sort, cookies=jar
                )
                assert ordered[0] == 200
                time_key, id_key = (
                    ("occurred_at", "event_id")
                    if path.endswith("security-events")
                    else (
                        ("issued_at", "session_id")
                        if path.endswith("sessions")
                        else ("issued_at", "api_token_id")
                    )
                )
                keysets = [
                    (item[time_key], item[id_key])
                    for item in json.loads(ordered[2])["items"]
                ]
                assert len(keysets) >= 2
                assert keysets == sorted(keysets, reverse=True)
                for suffix in (
                    "?sort=name",
                    "?sort=" + sort + "&sort=" + sort,
                    "?limit=1&limit=2",
                    "?cursor=x&cursor=y",
                    "?" + urllib.parse.urlencode(unsupported),
                ):
                    rejected = await asyncio.to_thread(
                        _request, origin, "GET", path + suffix, cookies=jar
                    )
                    assert rejected[0] == 400
            filtered = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/iam/security-events?event_type=login_succeeded&limit=1&sort=-occurred_at",
                cookies=jar,
            )
            assert filtered[0] == 200
            filtered_body = json.loads(filtered[2])
            assert filtered_body["items"][0]["event_type"] == "login_succeeded"
            event_cursor = filtered_body["page"]["next_cursor"]
            assert isinstance(event_cursor, str)
            for changed in (
                {
                    "limit": 1,
                    "event_type": "browser_session_revoked",
                    "cursor": event_cursor,
                },
                {
                    "limit": 1,
                    "event_type": "login_succeeded",
                    "occurred_from": filtered_body["items"][0]["occurred_at"],
                    "cursor": event_cursor,
                },
            ):
                mismatch = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    "/api/v1/iam/security-events?" + urllib.parse.urlencode(changed),
                    cookies=jar,
                )
                assert mismatch[0] == 400
                assert json.loads(mismatch[2])["code"] == "cursor_query_mismatch"
            repeated_filter = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/iam/security-events?event_type=login_succeeded&event_type=login_succeeded",
                cookies=jar,
            )
            assert repeated_filter[0] == 400
            bearer_first = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/api-tokens?limit=1",
                headers={"Authorization": "Bearer " + bearers[0]},
            )
            assert bearer_first[0] == 200
            cursor = json.loads(bearer_first[2])["page"]["next_cursor"]
            assert isinstance(cursor, str)
            bearer_other = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/api-tokens?"
                + urllib.parse.urlencode({"limit": 1, "cursor": cursor}),
                headers={"Authorization": "Bearer " + bearers[1]},
            )
            assert bearer_other[0] == 400
            assert json.loads(bearer_other[2])["code"] == "cursor_query_mismatch"

    asyncio.run(exercise())


def test_safe_problem_optional_errors_are_omitted_not_null_over_real_socket(
    tmp_path: Path,
) -> None:
    app, _ = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            ordinary = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/session"
            )
            assert ordinary[0] == 401
            ordinary_body = json.loads(ordinary[2])
            assert "errors" not in ordinary_body
            assert ordinary_body["detail"] == "Dashboard authentication required."
            invalid = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                body={},
                headers={"Origin": origin},
            )
            assert invalid[0] == 422
            fields = json.loads(invalid[2])["errors"]
            assert fields and fields[0]["path"] == "/password"
            assert fields[0]["code"] == "invalid_field"

    asyncio.run(exercise())


def test_iam_list_wire_schema_preserves_absent_credentials_and_explicit_nulls(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
            )[0] == 204
            created = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/api-tokens",
                body={"name": "nullable-fields", "scopes": ["write:tokens"]},
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": _session_cookies(jar)["agentmonitor_csrf"],
                    "Idempotency-Key": secrets.token_urlsafe(18),
                },
                cookies=jar,
            )
            assert created[0] == 201
            listed = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/api-tokens", cookies=jar
            )
            assert listed[0] == 200
            item = json.loads(listed[2])["items"][0]
            assert "bearer_credential" not in item
            for field in (
                "last_used_at",
                "revoked_at",
                "revocation_reason",
                "rotated_from_token_id",
                "replacement_token_id",
            ):
                assert field in item and item[field] is None
            assert json.loads(listed[2])["page"]["next_cursor"] is None
            schema = json.loads(
                (
                    await asyncio.to_thread(
                        _request, origin, "GET", "/openapi.json", cookies=jar
                    )
                )[2]
            )
            summary = schema["components"]["schemas"]["ApiTokenSummaryV1"]
            assert "bearer_credential" not in summary["properties"]
            assert "last_used_at" in summary["required"]
            assert {
                part["type"] for part in summary["properties"]["last_used_at"]["anyOf"]
            } == {"string", "null"}
            page_schema = schema["components"]["schemas"]["PageMetaV1"]
            assert "next_cursor" in page_schema["required"]
            assert {
                part["type"]
                for part in page_schema["properties"]["next_cursor"]["anyOf"]
            } == {"string", "null"}
            problem_schema = schema["components"]["schemas"]["SafeProblemV1"]
            assert "errors" in problem_schema["properties"]
            assert "errors" not in problem_schema["required"]
            assert "detail" not in problem_schema["required"]
            assert problem_schema["properties"]["detail"]["type"] == "string"

    asyncio.run(exercise())


def test_canonical_generated_artifacts_publish_m2_iam_operations() -> None:
    root = Path(__file__).resolve().parents[4]
    document = json.loads(
        (root / "contracts/openapi/agentmonitor-v1.json").read_bytes()
    )
    identifiers = [
        operation["operationId"]
        for methods in document["paths"].values()
        for operation in methods.values()
    ]
    assert len(identifiers) == len(set(identifiers)) == 13
    client = (root / "frontend/src/generated/api/index.ts").read_text()
    assert "iam_login_v1:" in client
    assert "iam_create_api_token_v1:" in client
    assert '"detail"?: string' in client
    assert '"committed_resource"?: SafeCommittedApiTokenV1;' in client


def test_generated_typescript_client_calls_real_iam_server(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)
    root = Path(__file__).resolve().parents[4]
    script = root / "frontend/tests/client/real-iam-http.mjs"

    async def exercise() -> None:
        async with _running(app) as origin:
            result = await asyncio.to_thread(
                subprocess.run,
                ["node", "--experimental-strip-types", str(script)],
                input=json.dumps({"origin": origin, "password": credential}).encode(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=root,
                timeout=20,
                check=False,
            )
            credential_absent = credential.encode() not in result.stdout + result.stderr
            assert credential_absent is True, "credential reflected"
            assert result.returncode == 0, "real generated client failed"
            assert result.stdout == b'{"status":"passed","operations":13}\n'
            assert result.stderr == b""

    asyncio.run(exercise())


def test_real_unavailable_iam_file_maps_to_safe_public_503(tmp_path: Path) -> None:
    app, _ = _installation(tmp_path)
    database = tmp_path / "agentmonitor.db"

    async def exercise() -> None:
        async with _running(app) as origin:
            available = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/iam/initialization"
            )
            assert available[0] == 200
            previous = database.stat().st_mode & 0o777
            os.chmod(database, 0o000)
            try:
                unavailable = await asyncio.to_thread(
                    _request, origin, "GET", "/api/v1/iam/initialization"
                )
                assert unavailable[0] == 503
                problem = json.loads(unavailable[2])
                assert problem["code"] == "iam_repository_unavailable"
                assert problem["status"] == 503
            finally:
                os.chmod(database, previous)
            restored = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/iam/initialization"
            )
            assert restored[0] == 200

    asyncio.run(exercise())


def test_service_holds_owner_only_exclusive_lock_until_drain(tmp_path: Path) -> None:
    app, _ = _installation(tmp_path)
    lock_path = tmp_path / ".agentmonitor-service.lock"

    async def exercise() -> None:
        async with _running(app):
            assert lock_path.is_file()
            assert stat.S_IMODE(lock_path.stat().st_mode) == 0o600
            descriptor = os.open(lock_path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    pass
                else:
                    raise AssertionError("service did not hold the recovery lock")
            finally:
                os.close(descriptor)
        descriptor = os.open(lock_path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)

    asyncio.run(exercise())
