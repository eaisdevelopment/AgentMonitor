"""Serve the checked release contract over real authenticated HTTP."""

import asyncio
import hashlib
import http.cookiejar
from pathlib import Path

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
)


def test_documentation_serves_published_contract_with_authentication(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)
    published = (
        Path(__file__).resolve().parents[4] / "contracts/openapi/agentmonitor-v1.json"
    ).read_bytes()

    async def exercise() -> None:
        async with _running(app) as origin:
            anonymous = await asyncio.to_thread(
                _request, origin, "GET", "/openapi.json"
            )
            assert anonymous[0] == 401
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
            response = await asyncio.to_thread(
                _request, origin, "GET", "/openapi.json", cookies=jar
            )
            assert response[0] == 200
            assert response[1].get_content_type() == "application/json"
            assert (
                hashlib.sha256(response[2]).digest()
                == hashlib.sha256(published).digest()
            ), "served_contract_differs_from_checked_release_artifact"
            # Authentication remains required after a successful schema read.
            anonymous = await asyncio.to_thread(
                _request, origin, "GET", "/openapi.json"
            )
            assert anonymous[0] == 401

    asyncio.run(exercise())
