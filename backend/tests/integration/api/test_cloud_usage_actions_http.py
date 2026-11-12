"""Actual IAM/HTTP guards for manual cloud usage; no provider or key requests."""

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


def test_cloud_usage_http_closed_intent_and_authorization(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            account, resource = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
            base = f"/api/v1/accounts/{account}/cloud-usage/{resource}"
            context = {
                "scope": "self",
                "range_key": "7d",
                "interval_start": "2026-11-01T00:00:00Z",
                "interval_end": "2026-11-08T00:00:00Z",
            }
            body = {"expected_target_version": 1, "report_context": context}
            response = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                base + "/collections",
                body=body,
                headers={"Origin": origin},
            )
            assert response[0] == 401
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
                "If-Match": f'"{account}.1"',
                "Idempotency-Key": secrets.token_urlsafe(24),
            }
            for omit, expected in (
                ("X-CSRF-Token", 403),
                ("If-Match", 428),
                ("Idempotency-Key", 400),
            ):
                response = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    base + "/collections",
                    body=body,
                    headers={k: v for k, v in headers.items() if k != omit},
                    cookies=jar,
                )
                assert response[0] == expected
            for invalid in (
                {"expected_target_version": True},
                {"api_key": None},
                {"report_context": {**context, "scope": "arbitrary"}},
                {"report_context": {**context, "range_key": "30d"}},
                {"report_context": {**context, "grouping": ["model"]}},
            ):
                response = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    base + "/collections",
                    body={**body, **invalid},
                    headers=headers,
                    cookies=jar,
                )
                assert response[0] == 422
                assert "input" not in json.loads(response[2])
            response = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                base + "/collections",
                body=body,
                headers=headers,
                cookies=jar,
            )
            assert response[0] == 404
            assert json.loads(response[2])["code"] == "cloud_usage_target_unavailable"
            query = (
                "?scope=self&range_key=7d"
                "&interval_start=2026-11-01T00%3A00%3A00Z"
                "&interval_end=2026-11-08T00%3A00%3A00Z"
            )
            for path in (
                base + "/collection-eligibility" + query,
                base + "/runs/absent-run",
            ):
                denied = await asyncio.to_thread(_request, origin, "GET", path)
                assert denied[0] == 401
                absent = await asyncio.to_thread(
                    _request, origin, "GET", path, cookies=jar
                )
                assert absent[0] == 404
            unknown = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                base + "/collection-eligibility" + query + "&key=unused",
                cookies=jar,
            )
            assert unknown[0] == 400

    asyncio.run(exercise())
