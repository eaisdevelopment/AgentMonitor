"""Real IAM/HTTP/native-process denials; no account attestation is submitted."""

import asyncio
import http.cookiejar
import json
from pathlib import Path

from agentmonitor.adapters.persistence.runtime_observation.settings.repository import (
    SETTINGS_NAME,
)

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
    _session_cookies,
)


def test_owner_confirmation_and_conditional_mutation_guards(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)
    tmp_path.chmod(0o700)

    async def exercise() -> None:
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
            observed = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/process-locations", cookies=jar
            )
            assert observed[0] == 200
            page = json.loads(observed[2])
            assert page["availability"]["state"] == "available"
            assert page["items"], "real running Claude processes required"
            item = page["items"][0]
            key = item["association_key"]
            assert len(key) == 64
            assert item["account_association"] is None
            assert item["association_record_version"] == 0
            path = "/api/v1/process-locations/" + key + "/account"
            body: dict[str, object] = {"account_id": None, "owner_confirmed": False}
            headers = {
                "Origin": origin,
                "X-CSRF-Token": _session_cookies(jar)["agentmonitor_csrf"],
                "If-Match": '"' + key + '.0"',
            }
            anonymous = await asyncio.to_thread(
                _request, origin, "PUT", path, body=body, headers=headers
            )
            assert anonymous[0] == 401
            for omitted, status in (("X-CSRF-Token", 403), ("If-Match", 428)):
                denied = await asyncio.to_thread(
                    _request,
                    origin,
                    "PUT",
                    path,
                    body=body,
                    headers={k: v for k, v in headers.items() if k != omitted},
                    cookies=jar,
                )
                assert denied[0] == status
            malformed = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                path,
                body=body,
                headers={**headers, "If-Match": 'W/"' + key + '.0"'},
                cookies=jar,
            )
            assert malformed[0] == 400
            unconfirmed = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                path,
                body=body,
                headers=headers,
                cookies=jar,
            )
            assert unconfirmed[0] == 422
            assert json.loads(unconfirmed[2])["code"] == "invalid_request_fields"
            assert not (tmp_path / SETTINGS_NAME).exists()

    asyncio.run(exercise())
