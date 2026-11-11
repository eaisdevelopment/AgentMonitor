"""Pure scope policy and actual rejected commands/Git; no accepted activation."""

import subprocess
import sys
from pathlib import Path

import pytest

from tools.automation.implementations import auto_m7

ROOT = Path(__file__).resolve().parents[3]


def test_explicit_setup_selection_requires_its_deploy_lane_and_revision() -> None:
    auto_m7.validate_selection("deploy", "setup_activation", "a" * 40)
    auto_m7.validate_selection("deploy", None, None)
    for selection in (
        ("exit", "setup_activation", "a" * 40),
        ("deploy", "setup_activation", None),
        ("deploy", "setup_activation", "bad"),
        ("deploy", None, "a" * 40),
        ("deploy", "other", "a" * 40),
    ):
        with pytest.raises(ValueError, match="m7_selection_invalid"):
            auto_m7.validate_selection(*selection)


def test_operational_success_cannot_substitute_for_setup_acceptance() -> None:
    result = auto_m7.setup_activation_result(
        (
            auto_m7.CheckResult("installed_revision_loopback", "passed"),
            auto_m7.CheckResult("operator_command", "passed"),
            auto_m7.CheckResult("lan_readiness", "passed"),
        )
    )
    assert result.status == "blocked"
    assert {item.name for item in result.checks if item.status == "not_run"} >= {
        "authenticated_setup",
        "collector_continuity",
        "backup_recovery",
    }
    assert auto_m7.evaluate_lane("deploy", result.checks).status != "passed"


@pytest.fixture
def selected(tmp_path: Path):
    checkout = tmp_path / "selected"
    subprocess.run(
        [
            "/usr/bin/git",
            "clone",
            "--quiet",
            "--no-hardlinks",
            str(ROOT),
            str(checkout),
        ],
        check=True,
        capture_output=True,
    )
    revision = subprocess.check_output(
        ["/usr/bin/git", "rev-parse", "HEAD"],
        cwd=checkout,
        text=True,
    ).strip()
    return checkout, revision


def test_clean_selected_revision_is_observed_from_actual_git(selected) -> None:
    checkout, revision = selected
    assert auto_m7.selected_setup_revision(checkout, revision) == revision
    previous = subprocess.check_output(
        ["/usr/bin/git", "rev-parse", "HEAD^"],
        cwd=checkout,
        text=True,
    ).strip()
    with pytest.raises(RuntimeError, match="m7_setup_revision_mismatch"):
        auto_m7.selected_setup_revision(checkout, previous)


def test_dirty_selected_revision_refused(selected) -> None:
    checkout, revision = selected
    (checkout / "AGENTS.md").write_text("changed checkout\n")
    with pytest.raises(RuntimeError, match="frontend_source_not_clean"):
        auto_m7.selected_setup_revision(checkout, revision)


def test_clean_development_clone_is_not_a_sealed_controller(selected) -> None:
    checkout, revision = selected
    with pytest.raises(RuntimeError, match="m7_setup_controller_not_retained"):
        auto_m7.verify_setup_controller(checkout, revision)


@pytest.mark.parametrize(
    "arguments",
    [
        ["--lane", "deploy", "--check", "setup_activation"],
        [
            "--lane",
            "exit",
            "--check",
            "setup_activation",
            "--expected-revision=" + "a" * 40,
        ],
        ["--lane", "deploy", "--check", "setup_activation", "--expected-revision=bad"],
        [
            "--lane",
            "deploy",
            "--check",
            "setup_activation",
            "--expected-revision=" + "a" * 40,
            "--data-root=/tmp/other",
        ],
    ],
)
def test_invalid_real_cli_never_admits_activation(arguments) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "tools.automation.implementations.auto_m7",
            *arguments,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode != 0
    assert "M7 SETUP OPERATION" not in result.stdout


def test_real_setup_selector_reaches_controller_preflight_but_cannot_activate(
    selected,
) -> None:
    # Run the actual current source from a clean isolated clone, never the fixed
    # retained-release directory. Thus no accepted activation can be reached.
    checkout, _ = selected
    for filename in (
        "auto_m7.py",
        "auto_m6_cutover.py",
        "m6_cutover.py",
        "m6_cutover_diagnostics.py",
    ):
        relative = Path("tools/automation/implementations") / filename
        (checkout / relative).write_bytes((ROOT / relative).read_bytes())
        subprocess.run(["/usr/bin/git", "add", str(relative)], cwd=checkout, check=True)
    subprocess.run(
        [
            "/usr/bin/git",
            "-c",
            "user.name=Controller test",
            "-c",
            "user.email=controller@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--allow-empty",
            "-m",
            "Test current setup selector",
        ],
        cwd=checkout,
        check=True,
        capture_output=True,
    )
    revision = subprocess.check_output(
        ["/usr/bin/git", "rev-parse", "HEAD"],
        cwd=checkout,
        text=True,
    ).strip()
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "tools.automation.implementations.auto_m7",
            "--lane",
            "deploy",
            "--check",
            "setup_activation",
            "--expected-revision=" + revision,
        ],
        cwd=checkout,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 3
    assert "controller_preflight" in result.stdout
    assert "M7 SETUP OPERATION" not in result.stdout


def test_closed_wrapper_failure_is_preserved_without_arbitrary_output() -> None:
    message = "M6 CUTOVER: BLOCKED — review the transition journal and service state"
    assert (
        auto_m7.closed_setup_command_reason(message.encode())
        == "m7_setup_cutover_journal_review"
    )
    assert (
        auto_m7.closed_setup_command_reason(b"unexpected process detail")
        == "m7_setup_command_failed"
    )
    assert (
        auto_m7.closed_setup_command_reason(message.encode() + b"\nunexpected detail")
        == "m7_setup_command_failed"
    )
