"""Story 6 perimeter checks against production Uvicorn and migrated file SQLite."""

from __future__ import annotations

import asyncio
import http.cookiejar
import json
import secrets
import urllib.error
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
from agentmonitor.composition.bootstrap import create_iam_application, serve_loopback
from agentmonitor.contracts.identity_access_v1 import SecretInputV1
from agentmonitor.foundation.application import LifecycleHooksV1
from agentmonitor.modules.identity_access.application.bootstrap import (
    BootstrapAdministratorV1,
)
from fastapi import FastAPI


def _installation(root: Path) -> tuple[FastAPI, str]:
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    migrate_to_head(reference)
    credential = secrets.token_urlsafe(32)
    outcome = BootstrapAdministratorV1(
        SqliteIdentityAccessRepositoryV1(reference), Argon2PasswordV1()
    )(SecretInputV1(credential), correlation_id="story6-origin-bootstrap")
    assert outcome.code == "created"
    config = root / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    return (
        create_iam_application(config, root, lifecycle=LifecycleHooksV1()),
        credential,
    )


@asynccontextmanager
async def _running(app: FastAPI) -> AsyncIterator[str]:
    stop = asyncio.Event()
    ready: asyncio.Future[str] = asyncio.get_running_loop().create_future()
    server = asyncio.create_task(
        serve_loopback(app, host="127.0.0.1", port=0, ready=ready.set_result, stop=stop)
    )
    try:
        yield await asyncio.wait_for(ready, timeout=8)
    finally:
        stop.set()
        await asyncio.wait_for(server, timeout=8)


def _request(
    origin: str,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, object] | None = None,
    cookies: http.cookiejar.CookieJar | None = None,
    unclassified: bool = False,
) -> tuple[int, Message[str, str], bytes]:
    handlers: list[urllib.request.BaseHandler] = [urllib.request.ProxyHandler({})]
    if cookies is not None:
        handlers.append(urllib.request.HTTPCookieProcessor(cookies))
    opener = urllib.request.build_opener(*handlers)
    outgoing = {} if headers is None else headers.copy()
    if (
        cookies is not None
        and method in {"GET", "HEAD"}
        and not unclassified
        and not any(key.lower() in {"origin", "sec-fetch-site"} for key in outgoing)
    ):
        outgoing["Origin"] = origin
    if body is not None:
        outgoing["Content-Type"] = "application/json"
    request = urllib.request.Request(
        origin + path,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers=outgoing,
        method=method,
    )
    try:
        with opener.open(request, timeout=10) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read()


def _csrf(jar: http.cookiejar.CookieJar) -> str:
    value = next(
        (cookie.value for cookie in jar if cookie.name == "agentmonitor_csrf"),
        None,
    )
    assert value is not None
    return value


def test_hostile_origin_cannot_revoke_a_real_cookie_session(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            login = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                headers={"Origin": origin},
                body={"password": credential},
                cookies=jar,
            )
            assert login[0] == 204
            before = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/session", cookies=jar
            )
            assert before[0] == 200
            session_id = json.loads(before[2])["session_id"]
            etag = before[1].get("ETag")
            assert etag is not None
            attacker = "http://127.0.0.1:1"
            denied = await asyncio.to_thread(
                _request,
                origin,
                "DELETE",
                "/api/v1/session",
                headers={
                    "Origin": attacker,
                    "X-CSRF-Token": _csrf(jar),
                    "If-Match": etag,
                },
                cookies=jar,
            )
            assert denied[0] == 403
            assert json.loads(denied[2])["code"] == "origin_not_allowed"
            assert denied[1].get("Access-Control-Allow-Origin") is None
            after = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/session", cookies=jar
            )
            assert after[0] == 200
            assert json.loads(after[2])["session_id"] == session_id
            denied_read = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/session",
                headers={"Origin": attacker},
                cookies=jar,
            )
            assert denied_read[0] == 403
            assert json.loads(denied_read[2])["code"] == "origin_not_allowed"
            headerless_resource = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/session",
                headers={
                    "Sec-Fetch-Site": "same-site",
                    "Sec-Fetch-Mode": "no-cors",
                    "Sec-Fetch-Dest": "image",
                },
                cookies=jar,
            )
            assert headerless_resource[0] == 403
            assert json.loads(headerless_resource[2])["code"] == "origin_not_allowed"
            unclassified_cookie_get = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/session",
                cookies=jar,
                unclassified=True,
            )
            assert unclassified_cookie_get[0] == 403
            assert (
                json.loads(unclassified_cookie_get[2])["code"] == "origin_not_allowed"
            )
            same_origin_resource = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/session",
                headers={
                    "Sec-Fetch-Site": "same-origin",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Dest": "empty",
                },
                cookies=jar,
            )
            assert same_origin_resource[0] == 200
            direct_navigation = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/session",
                headers={
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Dest": "document",
                },
                cookies=jar,
            )
            assert direct_navigation[0] == 200
            preflight = await asyncio.to_thread(
                _request,
                origin,
                "OPTIONS",
                "/api/v1/session",
                headers={"Origin": attacker, "Access-Control-Request-Method": "DELETE"},
            )
            assert preflight[0] == 403
            assert json.loads(preflight[2])["code"] == "origin_not_allowed"
            assert preflight[1].get("Access-Control-Allow-Origin") is None

    asyncio.run(exercise())


def test_pure_bearer_is_origin_independent_but_scope_limited(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            login = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                headers={"Origin": origin},
                body={"password": credential},
                cookies=jar,
            )
            assert login[0] == 204
            created = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/api-tokens",
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": _csrf(jar),
                    "Idempotency-Key": secrets.token_urlsafe(18),
                },
                body={"name": "origin-boundary", "scopes": ["write:tokens"]},
                cookies=jar,
            )
            assert created[0] == 201
            bearer = json.loads(created[2])["bearer_credential"]
            foreign = "http://127.0.0.1:1"
            for headers in (
                {"Authorization": "Bearer " + bearer},
                {"Authorization": "Bearer " + bearer, "Origin": foreign},
            ):
                allowed = await asyncio.to_thread(
                    _request, origin, "GET", "/api/v1/api-tokens", headers=headers
                )
                assert allowed[0] == 200
                assert allowed[1].get("Access-Control-Allow-Origin") is None
            wrong_scope = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/iam/security-events",
                headers={"Authorization": "Bearer " + bearer, "Origin": foreign},
            )
            assert wrong_scope[0] == 403
            assert json.loads(wrong_scope[2])["code"] == "permission_denied"
            invalid = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/api-tokens",
                headers={"Authorization": "Bearer invalid", "Origin": foreign},
            )
            assert invalid[0] == 401
            assert json.loads(invalid[2])["code"] == "dashboard_authentication_required"

    asyncio.run(exercise())
