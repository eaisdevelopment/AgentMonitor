"""Opt-in real elapsed browser-session expiry proof (about 24 hours)."""

from __future__ import annotations

import asyncio
import http.cookiejar
import json
import secrets
import time
from pathlib import Path

from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
    SqliteIdentityAccessRepositoryV1,
)
from agentmonitor.composition.bootstrap import create_iam_application
from agentmonitor.contracts.identity_access_v1 import SecretInputV1
from agentmonitor.foundation.application import LifecycleHooksV1
from agentmonitor.modules.identity_access.application.bootstrap import (
    BootstrapAdministratorV1,
)

from backend.tests.integration.api.test_iam_http import _request, _running


def test_real_elapsed_idle_expiry_denies_browser_cookie(tmp_path: Path) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    password = secrets.token_urlsafe(32)
    result = BootstrapAdministratorV1(
        SqliteIdentityAccessRepositoryV1(reference), Argon2PasswordV1()
    )(SecretInputV1(password), correlation_id="api-real-expiry-setup")
    assert result.code == "created"
    config = tmp_path / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    app = create_iam_application(config, tmp_path, lifecycle=LifecycleHooksV1())

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            login = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                body={"password": password},
                headers={"Origin": origin},
                cookies=jar,
            )
            assert login[0] == 204
            current = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/session", cookies=jar
            )
            assert current[0] == 200
            started = time.monotonic()
            await asyncio.sleep(86401)
            elapsed = time.monotonic() - started
            assert elapsed >= 86400
            expired = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/session", cookies=jar
            )
            assert expired[0] == 401
            assert json.loads(expired[2])["code"] == "dashboard_authentication_required"

    asyncio.run(exercise())
