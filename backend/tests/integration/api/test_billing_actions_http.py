"""Billing Check transport over actual IAM, HTTP and empty file SQLite."""

import asyncio
import http.cookiejar
import json
import secrets
from pathlib import Path

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
    _session_cookies,
)


def test_billing_check_http_authorization_and_closed_input(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            account_id = secrets.token_urlsafe(24)
            resource_id = secrets.token_urlsafe(24)
            path = (
                f"/api/v1/accounts/{account_id}/billing-connections/"
                f"{resource_id}/checks"
            )
            body: dict[str, object] = {"expected_connection_version": 1}
            unauthenticated = await asyncio.to_thread(
                _request, origin, "POST", path, body=body, headers={"Origin": origin}
            )
            assert unauthenticated[0] == 401
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
            headers = {
                "Origin": origin,
                "X-CSRF-Token": _session_cookies(jar)["agentmonitor_csrf"],
                "If-Match": f'"{account_id}.1"',
                "Idempotency-Key": secrets.token_urlsafe(24),
            }
            for omit, expected in (
                ("X-CSRF-Token", 403),
                ("If-Match", 428),
                ("Idempotency-Key", 400),
            ):
                rejected = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    path,
                    body=body,
                    headers={k: v for k, v in headers.items() if k != omit},
                    cookies=jar,
                )
                assert rejected[0] == expected
            for name, value in (
                ("If-Match", '"other-account.1"'),
                ("If-Match", f'"{account_id}.0"'),
                ("Idempotency-Key", "invalid short key"),
            ):
                rejected = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    path,
                    body=body,
                    headers={**headers, name: value},
                    cookies=jar,
                )
                assert rejected[0] == 400
            invalid_cases: tuple[dict[str, object], ...] = (
                {"expected_connection_version": True},
                {"expected_connection_version": "1"},
                {"expected_connection_version": 0},
                {"expected_connection_version": 1, "api_key": None},
            )
            for invalid in invalid_cases:
                rejected = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    path,
                    body=invalid,
                    headers=headers,
                    cookies=jar,
                )
                assert rejected[0] == 422
                assert "input" not in json.loads(rejected[2])
            query = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                path + "?scope=other",
                body=body,
                headers=headers,
                cookies=jar,
            )
            assert query[0] == 400
            missing = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                path,
                body=body,
                headers=headers,
                cookies=jar,
            )
            assert missing[0] == 404
            assert json.loads(missing[2])["code"] == "billing_check_target_unavailable"

    asyncio.run(exercise())

    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
        open_sqlite_database,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    with open_sqlite_database(ref, "runtime_read_only") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM collection_budget_run"
                ).scalar_one()
                == 0
            )


def test_budget_run_status_http_requires_auth_and_preserves_absence(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            path = f"/api/v1/collection-runs/{secrets.token_urlsafe(24)}/budget"
            unauthenticated = await asyncio.to_thread(
                _request, origin, "GET", path, headers={"Origin": origin}
            )
            assert unauthenticated[0] == 401
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
            rejected = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                path + "?account_id=other",
                cookies=jar,
            )
            assert rejected[0] == 400
            missing = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                path,
                cookies=jar,
            )
            assert missing[0] == 404
            assert json.loads(missing[2])["code"] == "billing_check_target_unavailable"

    asyncio.run(exercise())
