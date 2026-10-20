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
    "organizations",
    "accounts_admin",
    "account_beyond_page",
    "claude_connection",
    "alerts",
    "alert_console",
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

BROWSER_OUTPUT_INVALID = "browser_output_invalid"
_CLOSED_OUTPUT_PASS_LINES = {
    "responsive": (
        "P02 RESPONSIVE BROWSER: PASSED — six viewports, reduced motion and focus"
    ),
    "revocation": "P02 REVOCATION BROWSER: PASSED",
    "password_change": "P02 PASSWORD CHANGE BROWSER: PASSED",
}
_CLOSED_OUTPUT_FAILURE_STAGES = {
    "responsive": frozenset(
        {
            "browser_launch",
            "login_1920",
            "login_1440",
            "login_1280",
            "login_1024",
            "login_768",
            "login_390",
            "keyboard_sign_in",
            "token_settings_1920",
            "token_settings_1440",
            "token_settings_1280",
            "token_settings_1024",
            "token_settings_768",
            "token_settings_390",
            "mobile_header_layout",
            "mobile_header_keyboard",
            "browser_close",
        }
    ),
    "revocation": frozenset(
        {
            "browser_launch",
            "two_real_sessions",
            "revoke_other_session",
            "revoked_recovery",
            "revoked_nav_absent",
            "revoked_reload",
            "revoked_reload_sign_in",
            "revoked_reload_nav_absent",
            "primary_check_click",
            "primary_active_text",
            "browser_close",
        }
    ),
    "password_change": frozenset(
        {
            "browser_launch",
            "initial_login",
            "password_open",
            "password_draining",
            "password_ready",
            "password_cancel",
            "password_submit",
            "password_request_oracle",
            "password_success",
            "route_stable",
            "password_rotated",
            "old_credential_denied",
            "new_credential_accepted",
        }
    ),
}


def parse_repeat_count(value: str) -> int:
    """Return a bounded browser-run count without reflecting invalid input."""

    try:
        repeat = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "repeat_must_be_integer_1_through_30"
        ) from error
    if repeat < 1 or repeat > 30:
        raise argparse.ArgumentTypeError("repeat_must_be_integer_1_through_30")
    return repeat


def should_run_browser_repetition(
    repetition: int,
    *,
    repeat: int,
    failed: bool,
) -> bool:
    """Permit only the bounded next repetition before the first failure."""

    return not failed and 1 <= repeat <= 30 and 1 <= repetition <= repeat


def sanitize_closed_browser_output(
    scenario: str,
    stdout: str,
    stderr: str,
    returncode: int,
) -> tuple[str, ...]:
    """Admit one exact safe child line or return only the stable reject code."""

    pass_line = _CLOSED_OUTPUT_PASS_LINES.get(scenario)
    failure_stages = _CLOSED_OUTPUT_FAILURE_STAGES.get(scenario)
    if pass_line is None or failure_stages is None:
        return (BROWSER_OUTPUT_INVALID,)

    stdout_lines = tuple(stdout.splitlines())
    stderr_lines = tuple(stderr.splitlines())
    if returncode == 0:
        if stdout_lines == (pass_line,) and not stderr_lines:
            return stdout_lines
        return (BROWSER_OUTPUT_INVALID,)

    if returncode != 1 or stdout_lines or len(stderr_lines) != 1:
        return (BROWSER_OUTPUT_INVALID,)
    failure_prefix = pass_line.split(": PASSED", 1)[0] + ": FAILED — "
    for stage in failure_stages:
        if stderr_lines == (failure_prefix + stage,):
            return stderr_lines
    return (BROWSER_OUTPUT_INVALID,)


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
            try:
                browser = await asyncio.to_thread(
                    subprocess.run,
                    [
                        "node",
                        str(Path(__file__).with_name(f"{scenario}.mjs")),
                        origin,
                    ],
                    input=credential,
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=86_550 if scenario == "idle_expiry" else 180,
                )
            except Exception:
                if scenario in _CLOSED_OUTPUT_PASS_LINES:
                    raise RuntimeError(BROWSER_OUTPUT_INVALID) from None
                raise
            if scenario in _CLOSED_OUTPUT_PASS_LINES:
                safe_output = sanitize_closed_browser_output(
                    scenario,
                    browser.stdout,
                    browser.stderr,
                    browser.returncode,
                )
                browser.stdout = ""
                browser.stderr = ""
                if safe_output == (BROWSER_OUTPUT_INVALID,):
                    raise RuntimeError(BROWSER_OUTPUT_INVALID)
                display_output = safe_output[0]
            else:
                display_output = browser.stdout.strip()
            if browser.returncode != 0:
                if scenario in _CLOSED_OUTPUT_PASS_LINES:
                    raise RuntimeError("real_p02_browser_failed: " + display_output)
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
                    != 86400
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
            print(display_output)
        finally:
            stop.set()
            await asyncio.wait_for(server, timeout=8)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=sorted(SCENARIOS | {"quick", "all"}))
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument(
        "--repeat",
        type=parse_repeat_count,
        default=1,
        metavar="1..30",
    )
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
        QUICK_SCENARIOS + (("logout_after_touch",) if options.scenario == "all" else ())
        if options.scenario in {"quick", "all"}
        else (options.scenario,)
    )
    for position, scenario in enumerate(selected):
        repetition = 1
        failed = False
        failure_code = ""
        while should_run_browser_repetition(
            repetition,
            repeat=options.repeat,
            failed=failed,
        ):
            try:
                asyncio.run(run_scenario(scenario, initialized=scenario != "setup"))
            except (RuntimeError, TimeoutError) as error:
                failure_code = str(error)
                failed = True
                continue
            repetition += 1
        if failed:
            repetition_label = (
                f" repetition {repetition}/{options.repeat}"
                if options.repeat > 1
                else ""
            )
            print(
                "P02 BROWSER: FAILED — "
                + scenario
                + repetition_label
                + ": "
                + failure_code,
                file=sys.stderr,
            )
            for remaining in selected[position + 1 :]:
                print("P02 BROWSER: NOT RUN — " + remaining, file=sys.stderr)
            return 1
    print("P02 BROWSER: PASSED — " + options.scenario)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
