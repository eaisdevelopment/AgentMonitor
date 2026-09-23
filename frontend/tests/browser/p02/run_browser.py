"""Run P02 browser scenarios against the built app and real local IAM stack.

The password exists only in this process and a private child stdin pipe. The
database is a fresh migrated file; no operator configuration or accounts are read.
"""

from __future__ import annotations

import argparse
import asyncio
import secrets
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from agentmonitor.adapters.identity_access.argon2_password import (  # noqa: E402
    Argon2PasswordV1,
)
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (  # noqa: E402
    DatabaseRefV1,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (  # noqa: E402
    migrate_to_head,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (  # noqa: E402
    SqliteIdentityAccessRepositoryV1,
)
from agentmonitor.composition.bootstrap import (  # noqa: E402
    create_iam_application,
    serve_loopback,
)
from agentmonitor.contracts.identity_access_v1 import SecretInputV1  # noqa: E402
from agentmonitor.foundation.application import LifecycleHooksV1  # noqa: E402
from agentmonitor.modules.identity_access.application.bootstrap import (  # noqa: E402
    BootstrapAdministratorV1,
)

SCENARIOS = {
    "auth",
    "api_tokens",
    "idle_expiry",
    "password_change",
    "auth_failures",
    "setup",
    "revocation",
    "return_route",
    "responsive",
    "logout_after_touch",
    "clipboard_denied",
    "security_boundary",
    "hostile_resource",
    "monitoring_dashboard",
}
QUICK_SCENARIOS = (
    "setup",
    "auth_failures",
    "auth",
    "return_route",
    "revocation",
    "password_change",
    "api_tokens",
    "clipboard_denied",
    "responsive",
    "monitoring_dashboard",
)


async def run_scenario(scenario: str, *, initialized: bool = True) -> None:
    with tempfile.TemporaryDirectory(prefix="agentmonitor-p02-") as directory:
        data_root = Path(directory)
        reference = DatabaseRefV1(data_root / "agentmonitor.db", data_root)
        migrate_to_head(reference)
        credential = secrets.token_urlsafe(32)
        if initialized:
            outcome = BootstrapAdministratorV1(
                SqliteIdentityAccessRepositoryV1(reference), Argon2PasswordV1()
            )(SecretInputV1(credential), correlation_id="p02-browser-bootstrap")
            if outcome.code != "created":
                raise RuntimeError("isolated_bootstrap_failed")
        config = data_root / "isolated.env"
        config.write_text("")
        config.chmod(0o600)
        application = create_iam_application(
            config, data_root, lifecycle=LifecycleHooksV1()
        )
        stop = asyncio.Event()
        ready: asyncio.Future[str] = asyncio.get_running_loop().create_future()
        server = asyncio.create_task(
            serve_loopback(
                application,
                host="127.0.0.1",
                port=0,
                ready=ready.set_result,
                stop=stop,
            )
        )
        try:
            origin = await asyncio.wait_for(ready, timeout=8)
            browser = await asyncio.to_thread(
                subprocess.run,
                ["node", str(Path(__file__).with_name(f"{scenario}.mjs")), origin],
                input=credential,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
                timeout=1950 if scenario == "idle_expiry" else 180,
            )
            if browser.returncode != 0:
                raise RuntimeError(
                    "real_p02_browser_failed: " + browser.stdout + browser.stderr
                )
            if scenario == "hostile_resource":
                with sqlite3.connect(data_root / "agentmonitor.db") as connection:
                    sessions = connection.execute(
                        "SELECT issued_at, last_activity_at, idle_expires_at, "
                        "record_version FROM iam_browser_session"
                    ).fetchall()
                if len(sessions) != 1:
                    raise RuntimeError("expected_exactly_one_real_session")
                issued, activity, idle, version = sessions[0]
                if (
                    activity != issued
                    or (
                        datetime.fromisoformat(idle) - datetime.fromisoformat(issued)
                    ).total_seconds()
                    != 1800
                    or version != 1
                ):
                    raise RuntimeError("hostile_resource_changed_session_state")
                if (
                    "image_status=403" not in browser.stdout
                    or "no_referrer_status=403" not in browser.stdout
                ):
                    raise RuntimeError(
                        "hostile_resource_not_denied: " + browser.stdout.strip()
                    )
            print(browser.stdout.strip())
        finally:
            stop.set()
            await asyncio.wait_for(server, timeout=8)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=sorted(SCENARIOS | {"quick", "all"}))
    parser.add_argument("--no-build", action="store_true")
    options = parser.parse_args()
    if not options.no_build:
        build = subprocess.run(
            ["npm", "--prefix", "frontend", "run", "build"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if build.returncode != 0:
            print("P02 BROWSER: FAILED — production_build", file=sys.stderr)
            return 1
    selected = (
        QUICK_SCENARIOS
        + (("logout_after_touch", "idle_expiry") if options.scenario == "all" else ())
        if options.scenario in {"quick", "all"}
        else (options.scenario,)
    )
    for position, scenario in enumerate(selected):
        try:
            asyncio.run(run_scenario(scenario, initialized=scenario != "setup"))
        except (RuntimeError, TimeoutError) as error:
            print(
                "P02 BROWSER: FAILED — " + scenario + ": " + str(error), file=sys.stderr
            )
            for remaining in selected[position + 1 :]:
                print("P02 BROWSER: NOT RUN — " + remaining, file=sys.stderr)
            return 1
    print("P02 BROWSER: PASSED — " + options.scenario)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
