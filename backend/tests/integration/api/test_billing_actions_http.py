"""Billing Check transport over actual IAM, HTTP and empty file SQLite."""

import asyncio
import http.cookiejar
import json
import secrets
from pathlib import Path

import pytest

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
    _session_cookies,
)


@pytest.mark.parametrize("action", ["checks", "collections"])
def test_billing_check_http_authorization_and_closed_input(
    tmp_path: Path, action: str
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            account_id = secrets.token_urlsafe(24)
            resource_id = secrets.token_urlsafe(24)
            path = (
                f"/api/v1/accounts/{account_id}/billing-connections/"
                f"{resource_id}/{action}"
            )
            body: dict[str, object] = {"expected_connection_version": 1}
            if action == "collections":
                body["report_context"] = {
                    "range_key": "7d",
                    "interval_start": "2026-11-01T00:00:00Z",
                    "interval_end": "2026-11-08T00:00:00Z",
                    "source_category": "cost",
                    "grouping": [],
                }
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
            if action == "collections":
                context = body["report_context"]
                assert isinstance(context, dict)
                invalid_cases += tuple(
                    {"report_context": {**context, **change}}
                    for change in (
                        {"range_key": "30d"},
                        {"interval_end": "2026-11-08T01:00:00Z"},
                        {"source_category": "unknown"},
                        {"grouping": ["model"]},
                        {"credential": None},
                    )
                )
            for invalid in invalid_cases:
                rejected = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    path,
                    body={**body, **invalid},
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


def test_collect_eligibility_http_is_read_only_and_requires_auth(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            path = (
                f"/api/v1/accounts/{secrets.token_urlsafe(24)}/billing-connections/"
                f"{secrets.token_urlsafe(24)}/collection-eligibility"
            )
            query = (
                "?range_key=7d&interval_start=2026-11-01T00:00:00Z"
                "&interval_end=2026-11-08T00:00:00Z"
            )
            assert (await asyncio.to_thread(_request, origin, "GET", path + query))[
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
            assert (
                await asyncio.to_thread(
                    _request, origin, "GET", path + query, cookies=jar
                )
            )[0] == 404
            assert (
                await asyncio.to_thread(
                    _request, origin, "GET", path + query + "&unknown=1", cookies=jar
                )
            )[0] == 400
            for malformed in (
                query.replace("range_key=7d", "range_key=30d"),
                query.replace("01T00", "01T01"),
                query.replace("00:00Z", "00:00"),
            ):
                assert (
                    await asyncio.to_thread(
                        _request, origin, "GET", path + malformed, cookies=jar
                    )
                )[0] == 422

    asyncio.run(exercise())
