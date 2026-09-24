"""Behavioral safety contract for the one-shot Claude OTLP owner launcher."""

import sqlite3
import subprocess
import sys
from dataclasses import fields, replace
from datetime import UTC, datetime, timedelta
from inspect import signature
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.adapters.providers.claude.telemetry.launcher import (
    ClaudeMonitoredExecV1,
)
from agentmonitor.adapters.providers.claude.telemetry.otlp_http_json import (
    ClaudeOtlpErrorV1,
    ClaudeOtlpHttpJsonReceiverV1,
    ClaudeOtlpSessionCountV1,
    _CommitAcknowledgementV1,
)
from agentmonitor.composition.claude_otel_runtime import (
    ClaudeOtlpLaunchPlanV1,
    _admission,
    _checkpoint_and_acknowledge,
    _identity_resolution_matches_admission,
    _owner_binding_command,
    _prepare_commit,
    _start_failure_from_signal,
    _start_failure_signal,
    prepare_monitored_claude_launch,
)
from agentmonitor.contracts.collection_control_v1 import CollectionFailedV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    CollectionOutcomeV1,
    RetryAdviceV1,
)
from agentmonitor.contracts.registry_v1 import ProviderIdentityResolutionV1
from agentmonitor.contracts.runtime_observation_v1 import (
    ProcessIdentityV1,
    RuntimeObservationBatchV1,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[5]


def _launch_plan(account_id: str, profile_id: str) -> ClaudeOtlpLaunchPlanV1:
    return ClaudeOtlpLaunchPlanV1(
        executable=Path("/opt/claude"),
        configuration=ClaudeMonitoredExecV1(
            endpoint="http://127.0.0.1:4318/v1/metrics",
            authorization_secret="test-only-pure-domain-value",
            launch_id="launch-id",
            installation_id="installation-id",
            process_identity=ProcessIdentityV1(
                platform_source="linux.proc.process.v1",
                platform_scope_id="a" * 64,
                pid=1234,
                start_time_ticks=5678,
            ),
        ),
        provider_version="2.1.278",
        registry_revision=5,
        selected_account_id=OpaqueIdV1(account_id),
        selected_account_record_version=1,
        selected_profile_id=OpaqueIdV1(profile_id),
        selected_profile_record_version=1,
    )


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


def test_otlp_collection_schedule_is_bound_to_selected_account_and_profile() -> None:
    """M04-PURE-OTEL-001: stale/global schedules cannot block another scope."""
    requested_at = datetime(2026, 9, 23, 16, 0, tzinfo=UTC)
    first = _admission(_launch_plan("account-one", "profile-one"), requested_at)
    replay = _admission(_launch_plan("account-one", "profile-one"), requested_at)
    different_account = _admission(
        _launch_plan("account-two", "profile-two"), requested_at
    )

    assert first.schedule_id == replay.schedule_id
    assert first.schedule_id != different_account.schedule_id
    assert first.schedule_id.value != "claude-otel-session-manual-schedule"
    assert first.account_id == OpaqueIdV1("account-one")
    assert first.profile_id == OpaqueIdV1("profile-one")
    # The collection-policy generation is independent from the registry
    # revision so a reviewed manifest change cannot collide with a run
    # admitted under the preceding manifest at the same registry revision.
    assert first.target_generation == 6


def test_otlp_collection_persists_the_sanitized_adapter_failure_code() -> None:
    """M04-PURE-OTEL-002: live diagnosis keeps the bounded failure reason."""
    admission = _admission(
        _launch_plan("account-one", "profile-one"),
        datetime(2026, 9, 23, 16, 0, tzinfo=UTC),
    )
    outcome: CollectionOutcomeV1[RuntimeObservationBatchV1] = (
        CollectionOutcomeV1.failure(
            state="internal_adapter_error",
            code="claude_otel_live_process_verification_missing",
            retry=RetryAdviceV1("never"),
        )
    )

    result = _prepare_commit(
        admission,
        outcome,
        datetime(2026, 9, 23, 16, 0, 1, tzinfo=UTC),
    )

    assert isinstance(result, CollectionFailedV1)
    assert result.error_code == "claude_otel_live_process_verification_missing"


def test_launcher_child_reports_only_allowlisted_start_failure_codes() -> None:
    """M04-PURE-OTEL-003: operator diagnostics cannot carry arbitrary text."""
    safe = _start_failure_signal(ValueError("collection_schedule_conflict"))
    unsafe = _start_failure_signal(ValueError("unsafe /path value"))

    assert _start_failure_from_signal(safe) == "collection_schedule_conflict"
    assert _start_failure_from_signal(unsafe) == "claude_otel_monitoring_start_failed"
    assert (
        _start_failure_from_signal(b"0non-ascii-\xff")
        == "claude_otel_monitoring_start_failed"
    )


def test_collection_uses_preconfirmed_identity_without_mutation() -> None:
    """M02/M04-OTEL-004: admission generation stays closed during collection."""
    resolution = ProviderIdentityResolutionV1(
        "resolved",
        OpaqueIdV1("account-one"),
        1,
        "provider_identity_owner_confirmed",
        5,
    )

    assert _identity_resolution_matches_admission(
        resolution,
        account_id=OpaqueIdV1("account-one"),
        account_record_version=1,
        registry_revision=5,
    )
    assert not _identity_resolution_matches_admission(
        replace(resolution, registry_revision=6),
        account_id=OpaqueIdV1("account-one"),
        account_record_version=1,
        registry_revision=5,
    )
    assert not _identity_resolution_matches_admission(
        resolution,
        account_id=OpaqueIdV1("account-two"),
        account_record_version=1,
        registry_revision=5,
    )
    assert not _identity_resolution_matches_admission(
        resolution,
        account_id=OpaqueIdV1("account-one"),
        account_record_version=2,
        registry_revision=5,
    )


def test_owner_binding_command_closes_the_actual_metric_to_exact_source_tuple() -> None:
    """M02-PURE-029: binding carries no implicit account or caller source tuple."""
    plan = _launch_plan("account-one", "profile-one")
    metric = replace(
        _metric(datetime(2026, 9, 24, 12, 0, tzinfo=UTC)),
        process_identity=plan.configuration.process_identity,
    )

    command = _owner_binding_command(
        plan=plan,
        metric=metric,
        session_observation_id=OpaqueIdV1("runtime-session-observation-1"),
        payload_digest="d" * 64,
        requested_at=datetime(2026, 9, 24, 12, 0, 1, tzinfo=UTC),
    )

    assert command.account_id == OpaqueIdV1("account-one")
    assert command.expected_account_record_version == 1
    assert command.provider_key == "claude"
    assert command.identity_scheme == "claude.otel.account.sha256"
    assert command.identity_scope == "provider_account"
    assert command.identity_scheme_version == 1
    assert command.subject_fingerprint == metric.observed_account_fingerprint
    assert command.source_id == "claude.otel.metrics.http-json.v1"
    assert command.source_version == "1.0.0"
    assert command.parser_version == "1.0.0"
    assert command.evidence_reference == OpaqueIdV1("runtime-session-observation-1")
    assert command.expected_evidence_digest == "d" * 64

    with pytest.raises(ValueError, match="claude_otel_launch_scope_mismatch"):
        _owner_binding_command(
            plan=plan,
            metric=replace(metric, installation_id="different-installation"),
            session_observation_id=OpaqueIdV1("runtime-session-observation-1"),
            payload_digest="d" * 64,
            requested_at=datetime(2026, 9, 24, 12, 0, 1, tzinfo=UTC),
        )


def _metric(observed_at: datetime) -> ClaudeOtlpSessionCountV1:
    return ClaudeOtlpSessionCountV1(
        session_fingerprint="a" * 64,
        process_identity=ProcessIdentityV1(
            platform_source="linux.proc.process.v1",
            platform_scope_id="b" * 64,
            pid=1234,
            start_time_ticks=5678,
        ),
        installation_id="installation-id",
        launch_id="launch-id",
        observed_account_fingerprint="c" * 64,
        provider_version="2.1.278",
        observed_at=observed_at,
    )


def test_process_capture_opens_metric_acceptance_before_receiver_wait() -> None:
    """M06-OTEL-005: an OTLP point cannot be accepted before process capture."""
    receiver = ClaudeOtlpHttpJsonReceiverV1()
    metric = _metric(datetime.now(UTC))
    with receiver:
        assert receiver.submit_after_process_capture(metric) is False
        receiver.enable_observation_acceptance(datetime.now(UTC))
        assert receiver.submit_after_process_capture(metric) is True
        assert receiver.wait(0.001) == metric

    future_receiver = ClaudeOtlpHttpJsonReceiverV1()
    with future_receiver:
        future_receiver.enable_observation_acceptance(
            datetime.now(UTC) + timedelta(minutes=1)
        )
        assert future_receiver.submit_after_process_capture(metric) is False


def test_durable_checkpoint_precedes_otlp_success_acknowledgement(
    tmp_path: Path,
) -> None:
    """DB-FILE-011: exporter success cannot precede quiescent WAL cleanup."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    with open_sqlite_database(reference, "migration_initialize"):
        pass
    receiver = ClaudeOtlpHttpJsonReceiverV1()
    with receiver:
        metric = _metric(datetime.now(UTC))
        receiver.enable_observation_acceptance(datetime.now(UTC))
        assert receiver.submit_after_process_capture(metric)

        blocker = sqlite3.connect(tmp_path / "agentmonitor.db")
        blocker.execute("PRAGMA journal_mode=WAL")
        blocker.execute("CREATE TABLE real_checkpoint_probe (value INTEGER NOT NULL)")
        blocker.execute("INSERT INTO real_checkpoint_probe VALUES (1)")
        blocker.commit()
        blocker.execute("BEGIN IMMEDIATE")
        blocker.execute("INSERT INTO real_checkpoint_probe VALUES (2)")
        try:
            with pytest.raises(SqlitePolicyError, match="persistence_busy"):
                _checkpoint_and_acknowledge(reference, receiver, metric)
            assert receiver.wait_for_commit_acknowledgement(metric, 0.001) is False
        finally:
            blocker.rollback()
            blocker.close()

        _checkpoint_and_acknowledge(reference, receiver, metric)
        assert receiver.wait_for_commit_acknowledgement(metric, 0.001) is True
