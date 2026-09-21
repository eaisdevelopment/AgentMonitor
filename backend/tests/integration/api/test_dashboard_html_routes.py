"""Real loopback checks for the M2 dashboard HTML transport boundary."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
)


def test_iam_mode_serves_the_m2_entry_on_exact_browser_routes(tmp_path: Path) -> None:
    app, _ = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            for path in ("/", "/login", "/settings/api-tokens"):
                status, headers, body = await asyncio.to_thread(
                    _request, origin, "GET", path
                )
                assert status == 200, path
                assert b'id="agentmonitor-dashboard-root"' in body, path
                assert headers.get_content_type() == "text/html"
                assert headers.get("Cache-Control") == "no-store, private"
                assert "script-src 'self'" in headers.get("Content-Security-Policy", "")
            unknown = await asyncio.to_thread(
                _request, origin, "GET", "/settings/not-an-app-route"
            )
            assert unknown[0] == 404
            for direct_html in ("/dashboard.html", "/index.html"):
                denied = await asyncio.to_thread(_request, origin, "GET", direct_html)
                assert denied[0] == 404, direct_html
            asset = re.search(rb'src="(/assets/[^\"]+\.js)"', body)
            assert asset is not None, "built dashboard script missing"
            script = await asyncio.to_thread(
                _request, origin, "GET", asset.group(1).decode("ascii")
            )
            assert script[0] == 200
            assert script[1].get_content_type() in {
                "text/javascript",
                "application/javascript",
            }

    asyncio.run(exercise())
