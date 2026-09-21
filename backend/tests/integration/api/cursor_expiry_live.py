"""Opt-in elapsed-time IAM cursor check; never collected by the default suite.

Run explicitly from the repository root with the installed backend interpreter:
pytest -q backend/tests/integration/api/cursor_expiry_live.py

This takes more than 15 minutes of real wall time. It does not patch a clock,
replace a service, or infer expiry from a decoded implementation payload.
"""

import asyncio
import http.cookiejar
import json
import urllib.parse
from pathlib import Path

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
)


def test_iam_cursor_expires_after_real_fifteen_minutes(tmp_path: Path) -> None:
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
            await asyncio.sleep(901)
            expired = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/iam/sessions?"
                + urllib.parse.urlencode({"limit": 1, "cursor": cursor}),
                cookies=jar,
            )
            assert expired[0] == 400
            assert json.loads(expired[2])["code"] == "invalid_cursor"

    asyncio.run(exercise())
