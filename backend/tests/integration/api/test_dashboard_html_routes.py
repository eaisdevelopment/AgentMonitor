"""Real loopback checks for the M2 dashboard HTML transport boundary."""

from __future__ import annotations

import asyncio
import json
import os
import re
import select
import signal
import subprocess
import sys
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
)

ROOT = Path(__file__).resolve().parents[4]


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


def test_production_cli_starts_authenticated_dashboard_mode(tmp_path: Path) -> None:
    """M3 Task 6: the production CLI can run the real dashboard composition."""
    config = tmp_path / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    migrate_to_head(DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path))
    child = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "agentmonitor.composition.bootstrap",
            "--config",
            str(config),
            "--data-root",
            str(tmp_path),
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--authenticated-dashboard",
        ],
        cwd=ROOT,
        env={"PATH": os.defpath, "PYTHONPATH": str(ROOT / "backend/src")},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout is not None
        assert select.select([child.stdout], [], [], 8)[0], "no bounded readiness"
        record = json.loads(child.stdout.readline())
        assert record["event"] == "ready"
        status, _, body = _request(record["origin"], "GET", "/")
        assert status == 200
        assert b'id="agentmonitor-dashboard-root"' in body
        child.send_signal(signal.SIGTERM)
        out, err = child.communicate(timeout=8)
        assert child.returncode == 0
        assert not err
        assert str(tmp_path) not in out
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=8)
