"""Behavioral safety contract for the one-shot Claude OTLP owner launcher."""

import subprocess
import sys
from dataclasses import fields
from inspect import signature
from pathlib import Path

import pytest
from agentmonitor.adapters.providers.claude.telemetry.otlp_http_json import (
    ClaudeOtlpErrorV1,
    _CommitAcknowledgementV1,
)
from agentmonitor.composition.claude_otel_runtime import (
    ClaudeOtlpLaunchPlanV1,
    prepare_monitored_claude_launch,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[5]


def _run_operator(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (
            sys.executable,
            "-m",
            "agentmonitor.composition.claude_otel_runtime",
            *arguments,
        ),
        cwd=_PROJECT_ROOT / "backend" / "src",
        capture_output=True,
        check=False,
        text=True,
        timeout=5,
    )


def test_owner_launcher_requires_and_carries_exact_account_selection() -> None:
    """M03-STATIC-OTEL-001: owner selection is explicit and version-closed."""
    preparation = signature(prepare_monitored_claude_launch)
    selected = preparation.parameters["selected_account_id"]
    assert selected.default is selected.empty
    assert {
        "selected_account_id",
        "selected_account_record_version",
        "selected_profile_id",
        "selected_profile_record_version",
    } <= {item.name for item in fields(ClaudeOtlpLaunchPlanV1)}

    missing_selection = _run_operator("--data-root", str(_PROJECT_ROOT))
    assert missing_selection.returncode == 2
    assert missing_selection.stdout.strip() == "invalid_operator_arguments"

    complete = _run_operator(
        "--data-root",
        str(_PROJECT_ROOT),
        "--account-id",
        "owner-selected-account",
    )
    assert complete.returncode == 2
    assert complete.stdout.strip() == "controlling_tty_required"


def test_otlp_success_response_is_gated_by_durable_commit_acknowledgement() -> None:
    """M03-STATIC-OTEL-002: receipt success cannot precede durable verification."""
    committed = _CommitAcknowledgementV1()
    assert committed.wait(0.001) is False
    committed.committed()
    assert committed.wait(0.001) is True

    failed = _CommitAcknowledgementV1()
    failed.failed()
    assert failed.wait(0.001) is False
    with pytest.raises(ClaudeOtlpErrorV1, match="claude_otel_ack_state_invalid"):
        failed.committed()
