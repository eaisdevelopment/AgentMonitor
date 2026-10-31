"""Real built Chrome documentation boundary over migrated SQLite and Uvicorn."""

from __future__ import annotations

import asyncio
import secrets
import subprocess
from pathlib import Path

from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
    SqliteIdentityAccessRepositoryV1,
)
from agentmonitor.composition.bootstrap import create_iam_application, serve_loopback
from agentmonitor.contracts.identity_access_v1 import SecretInputV1
from agentmonitor.foundation.application import LifecycleHooksV1
from agentmonitor.modules.identity_access.application.bootstrap import (
    BootstrapAdministratorV1,
)

ROOT = Path(__file__).resolve().parents[4]


def test_protected_local_documentation_in_real_chrome(tmp_path: Path) -> None:
    build = subprocess.run(
        ["npm", "--prefix", "frontend", "run", "build"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=90,
    )
    assert build.returncode == 0, "production_frontend_build_failed"
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    password = secrets.token_urlsafe(32)
    outcome = BootstrapAdministratorV1(
        SqliteIdentityAccessRepositoryV1(reference), Argon2PasswordV1()
    )(SecretInputV1(password), correlation_id="docs-browser-bootstrap")
    assert outcome.code == "created"
    config = tmp_path / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    app = create_iam_application(config, tmp_path, lifecycle=LifecycleHooksV1())

    async def exercise() -> None:
        stop = asyncio.Event()
        ready: asyncio.Future[str] = asyncio.get_running_loop().create_future()
        server = asyncio.create_task(
            serve_loopback(
                app, host="127.0.0.1", port=0, ready=ready.set_result, stop=stop
            )
        )
        try:
            origin = await asyncio.wait_for(ready, timeout=8)
            browser = await asyncio.to_thread(
                subprocess.run,
                [
                    "node",
                    str(ROOT / "frontend/tests/browser/api/docs.mjs"),
                    origin,
                ],
                input=password,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
            assert browser.returncode == 0, (
                "real_docs_browser_failed: " + browser.stdout + browser.stderr
            )
            assert browser.stdout.strip() == "DOCS BROWSER: PASSED"
        finally:
            stop.set()
            await asyncio.wait_for(server, timeout=8)

    asyncio.run(exercise())
