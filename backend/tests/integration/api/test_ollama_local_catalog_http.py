"""Real Ollama catalog through the authenticated versioned HTTP boundary."""

import asyncio
import http.cookiejar
import json
from pathlib import Path

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
)
from tools.discovery.m6_local_inventory import read_json


def test_real_ollama_catalog_requires_auth_and_reports_source_state(tmp_path: Path):
    app, credential = _installation(tmp_path)

    async def exercise():
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

            def source_names(path: str) -> tuple[str, ...]:
                return tuple(
                    sorted(model["name"] for model in read_json(path)["models"])
                )

            before = (source_names("/api/tags"), source_names("/api/ps"))
            result = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/providers/ollama/local-catalog",
                cookies=jar,
            )
            assert result[0] == 200
            payload = json.loads(result[2])
            after = (source_names("/api/tags"), source_names("/api/ps"))
            if before != after:
                raise AssertionError("local_model_state_changed_during_test")
            assert payload["daemon_version"] == "0.24.0"
            observed = (
                tuple(sorted(model["name"] for model in payload["installed"])),
                tuple(sorted(model["name"] for model in payload["loaded"])),
            )
            if observed != before:
                raise AssertionError("local_model_names_do_not_match_source")
            denied = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/providers/ollama/local-catalog"
            )
            assert denied[0] in (401, 403)
            invalid = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/providers/ollama/local-catalog?target=untrusted",
                cookies=jar,
            )
            assert invalid[0] == 400

    asyncio.run(exercise())
