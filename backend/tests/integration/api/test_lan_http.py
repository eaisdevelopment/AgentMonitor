"""Owner-selected real LAN sockets, migrated IAM, HTTP and built Chrome."""

from __future__ import annotations

import asyncio
import http.cookiejar
import json
import os
import secrets
import socket
import sqlite3
import subprocess
import urllib.error
import urllib.request
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
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
    result = BootstrapAdministratorV1(
        SqliteIdentityAccessRepositoryV1(reference), Argon2PasswordV1()
    )(SecretInputV1(credential), correlation_id="lan-browser-bootstrap")
    assert result.code == "created"
    config = root / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    return create_iam_application(
        config, root, lifecycle=LifecycleHooksV1()
    ), credential


@asynccontextmanager
async def _running(app: FastAPI) -> AsyncIterator[tuple[str, str]]:
    host = os.environ.get("AGENTMONITOR_TEST_LAN_HOST")
    network = os.environ.get("AGENTMONITOR_TEST_LAN_NETWORK")
    assert host and network, "explicit_real_lan_target_required"
    stop = asyncio.Event()
    ready: asyncio.Future[str] = asyncio.get_running_loop().create_future()
    task = asyncio.create_task(
        serve_loopback(
            app,
            host="127.0.0.1",
            port=0,
            ready=ready.set_result,
            stop=stop,
            lan_host=host,
            lan_network=network,
        )
    )
    try:
        finished, _ = await asyncio.wait(
            (ready, task), timeout=8, return_when=asyncio.FIRST_COMPLETED
        )
        assert finished, "real_lan_listener_not_ready"
        if task in finished:
            await task
            raise AssertionError("real_lan_listener_exited")
        local_origin = ready.result()
        yield local_origin, f"http://{host}:{local_origin.rsplit(':', 1)[1]}"
    finally:
        stop.set()
        await asyncio.wait_for(task, timeout=8)


def _request(
    origin: str,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, object] | None = None,
    cookies: http.cookiejar.CookieJar | None = None,
) -> tuple[int, object, bytes]:
    handlers: list[urllib.request.BaseHandler] = [urllib.request.ProxyHandler({})]
    if cookies is not None:
        handlers.append(urllib.request.HTTPCookieProcessor(cookies))
    outgoing = {} if headers is None else headers.copy()
    if body is not None:
        outgoing["Content-Type"] = "application/json"
    request = urllib.request.Request(
        origin + path,
        method=method,
        headers=outgoing,
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with urllib.request.build_opener(*handlers).open(
            request, timeout=10
        ) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read()


def test_real_lan_and_loopback_auth_host_origin_csrf_and_peer(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as (local, lan):
            for origin in (local, lan):
                assert (await asyncio.to_thread(_request, origin, "GET", "/"))[0] == 200
                assert (
                    await asyncio.to_thread(_request, origin, "GET", "/api/v1/accounts")
                )[0] == 401
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
                assert (
                    await asyncio.to_thread(
                        _request,
                        origin,
                        "GET",
                        "/api/v1/session",
                        headers={"Origin": origin},
                        cookies=jar,
                    )
                )[0] == 200
                assert (
                    await asyncio.to_thread(
                        _request, origin, "GET", "/api/v1/session", cookies=jar
                    )
                )[0] == 403
                assert (
                    await asyncio.to_thread(
                        _request,
                        origin,
                        "GET",
                        "/api/v1/session",
                        headers={"Origin": "http://evil.invalid"},
                        cookies=jar,
                    )
                )[0] == 403
                assert (
                    await asyncio.to_thread(
                        _request, origin, "GET", "/", headers={"Host": "evil.invalid"}
                    )
                )[0] == 403
                assert (
                    await asyncio.to_thread(
                        _request,
                        origin,
                        "POST",
                        "/api/v1/organizations",
                        body={"name": secrets.token_hex(8)},
                        headers={"Origin": origin},
                        cookies=jar,
                    )
                )[0] == 403
                if origin == lan:
                    assert (
                        await asyncio.to_thread(
                            _request,
                            origin,
                            "GET",
                            "/api/v1/session",
                            headers={"Referer": origin + "/accounts"},
                            cookies=jar,
                        )
                    )[0] == 200
                    assert (
                        await asyncio.to_thread(
                            _request,
                            origin,
                            "GET",
                            "/api/v1/session",
                            headers={"Referer": local + "/accounts"},
                            cookies=jar,
                        )
                    )[0] == 403
                    assert (
                        await asyncio.to_thread(
                            _request, origin, "GET", "/accounts", cookies=jar
                        )
                    )[0] == 200
                    csrf = next(
                        cookie.value
                        for cookie in jar
                        if cookie.name == "agentmonitor_csrf"
                    )
                    assert csrf is not None
                    created = await asyncio.to_thread(
                        _request,
                        origin,
                        "POST",
                        "/api/v1/organizations",
                        body={"name": secrets.token_hex(8)},
                        headers={
                            "Origin": origin,
                            "X-CSRF-Token": csrf,
                            "Idempotency-Key": secrets.token_urlsafe(20),
                        },
                        cookies=jar,
                    )
                    assert created[0] == 201
            host = os.environ["AGENTMONITOR_TEST_LAN_HOST"]
            port = int(lan.rsplit(":", 1)[1])

            def outside_subnet() -> int:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
                    connection.settimeout(10)
                    connection.bind(("127.0.0.1", 0))
                    connection.connect((host, port))
                    connection.sendall(
                        (
                            f"GET / HTTP/1.1\r\nHost: {host}:{port}\r\n"
                            f"X-Forwarded-For: {host}\r\nConnection: close\r\n\r\n"
                        ).encode()
                    )
                    return int(connection.recv(4096).split(b" ", 2)[1])

            assert await asyncio.to_thread(outside_subnet) == 403

    asyncio.run(exercise())


def test_real_lan_built_browser_sign_in_and_navigation(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)
    root = Path(__file__).resolve().parents[4]

    async def exercise() -> None:
        async with _running(app) as (_, lan):
            result = await asyncio.to_thread(
                subprocess.run,
                ["node", "tools/ui/verify_lan_dashboard.mjs", lan],
                input=credential,
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                timeout=45,
            )
            assert result.returncode == 0, result.stdout + result.stderr

    asyncio.run(exercise())


def test_real_lan_hostile_images_cannot_touch_cookie_session(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)
    root = Path(__file__).resolve().parents[4]

    async def exercise() -> None:
        async with _running(app) as (_, lan):
            result = await asyncio.to_thread(
                subprocess.run,
                ["node", "frontend/tests/browser/p02/hostile_resource.mjs", lan],
                input=credential,
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                timeout=150,
            )
            assert result.returncode == 0, "real_lan_hostile_browser_failed"
            assert "image_status=403" in result.stdout
            assert "no_referrer_status=403" in result.stdout
            with sqlite3.connect(tmp_path / "agentmonitor.db") as connection:
                rows = connection.execute(
                    "SELECT issued_at, last_activity_at, idle_expires_at, "
                    "record_version FROM iam_browser_session"
                ).fetchall()
            assert len(rows) == 1
            issued, activity, _, version = rows[0]
            assert issued == activity and version == 1, (
                "hostile_lan_read_touched_session"
            )

    asyncio.run(exercise())
