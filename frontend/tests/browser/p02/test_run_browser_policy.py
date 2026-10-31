"""Pure policy checks for the P02 browser runner."""

from __future__ import annotations

import argparse

import pytest

from frontend.tests.browser.p02.run_browser import (
    BROWSER_OUTPUT_INVALID,
    parse_repeat_count,
    sanitize_closed_browser_output,
    should_run_browser_repetition,
)


@pytest.mark.parametrize("value", ("1", "2", "30"))
def test_repeat_count_accepts_only_the_bounded_integer_range(value: str) -> None:
    assert parse_repeat_count(value) == int(value)


@pytest.mark.parametrize("value", ("0", "31", "-1", "1.5", "many", ""))
def test_repeat_count_rejects_every_value_outside_the_closed_range(
    value: str,
) -> None:
    with pytest.raises(argparse.ArgumentTypeError) as raised:
        parse_repeat_count(value)

    assert raised.value.args == ("repeat_must_be_integer_1_through_30",)


def test_repeat_policy_stops_before_any_retry_after_the_first_failure() -> None:
    assert should_run_browser_repetition(1, repeat=30, failed=False)
    assert should_run_browser_repetition(7, repeat=30, failed=False)
    assert should_run_browser_repetition(30, repeat=30, failed=False)
    assert not should_run_browser_repetition(31, repeat=30, failed=False)
    assert not should_run_browser_repetition(7, repeat=30, failed=True)
    assert not should_run_browser_repetition(8, repeat=30, failed=True)


@pytest.mark.parametrize(
    ("scenario", "line"),
    (
        (
            "responsive",
            "P02 RESPONSIVE BROWSER: PASSED — six viewports, reduced motion and focus",
        ),
        ("revocation", "P02 REVOCATION BROWSER: PASSED"),
        ("password_change", "P02 PASSWORD CHANGE BROWSER: PASSED"),
    ),
)
def test_closed_output_accepts_only_the_scenario_pass_line(
    scenario: str,
    line: str,
) -> None:
    assert sanitize_closed_browser_output(scenario, line + "\n", "", 0) == (line,)


@pytest.mark.parametrize(
    ("scenario", "stage"),
    (
        *(
            ("responsive", stage)
            for stage in (
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
            )
        ),
        *(
            ("revocation", stage)
            for stage in (
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
            )
        ),
        *(
            ("password_change", stage)
            for stage in (
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
            )
        ),
    ),
)
def test_closed_output_accepts_every_allowlisted_failure_stage(
    scenario: str,
    stage: str,
) -> None:
    label = {
        "responsive": "RESPONSIVE",
        "revocation": "REVOCATION",
        "password_change": "PASSWORD CHANGE",
    }[scenario]
    line = f"P02 {label} BROWSER: FAILED — {stage}"
    assert sanitize_closed_browser_output(scenario, "", line + "\n", 1) == (line,)


@pytest.mark.parametrize(
    "unexpected",
    (
        "TimeoutError: locator.click exceeded 30000ms",
        "request failed at http://127.0.0.1:43110/login?token=private",
        "Authorization: Bearer secret-shaped-value",
        "P02 REVOCATION BROWSER: FAILED — invented_stage",
    ),
)
def test_unexpected_output_returns_only_the_stable_code(unexpected: str) -> None:
    result = sanitize_closed_browser_output(
        "revocation",
        "",
        unexpected + "\n",
        1,
    )

    assert result == (BROWSER_OUTPUT_INVALID,)
    assert unexpected not in "\n".join(result)


@pytest.mark.parametrize(
    ("stdout", "stderr", "returncode"),
    (
        ("P02 REVOCATION BROWSER: PASSED\n", "", 1),
        ("", "P02 REVOCATION BROWSER: FAILED — revoked_recovery\n", 0),
        (
            "P02 REVOCATION BROWSER: PASSED\n",
            "P02 REVOCATION BROWSER: FAILED — revoked_recovery\n",
            0,
        ),
        ("", "", 0),
    ),
)
def test_channel_or_exit_status_conflicts_fail_closed(
    stdout: str,
    stderr: str,
    returncode: int,
) -> None:
    assert sanitize_closed_browser_output(
        "revocation",
        stdout,
        stderr,
        returncode,
    ) == (BROWSER_OUTPUT_INVALID,)


@pytest.mark.parametrize("returncode", (2, 127, -9))
def test_allowlisted_failure_line_requires_the_script_exit_code(
    returncode: int,
) -> None:
    line = "P02 REVOCATION BROWSER: FAILED — revoked_recovery"

    assert sanitize_closed_browser_output(
        "revocation",
        "",
        line + "\n",
        returncode,
    ) == (BROWSER_OUTPUT_INVALID,)
