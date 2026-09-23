"""M04 pure policy evidence; constructed values never represent provider facts."""

from dataclasses import fields
from datetime import UTC, datetime

from agentmonitor.contracts.collection_control_v1 import (
    CollectionCommitReceiptV1,
    CollectionFailedV1,
    CollectionRunViewV1,
    InvalidCollectionControlV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.collection_control.domain.policy import (
    CollectionCadencePolicyV1,
    CollectionPolicyErrorV1,
    decide_retry,
    effective_interval_seconds,
)


def test_active_idle_and_unknown_cadence_respect_source_minimum() -> None:
    """M04-PURE-001..003: defaults yield to a stricter source constraint."""
    policy = CollectionCadencePolicyV1(
        active_interval_seconds=60,
        idle_interval_seconds=300,
    )

    assert effective_interval_seconds("active", 0, policy) == 60
    assert effective_interval_seconds("idle", 0, policy) == 300
    assert effective_interval_seconds("unknown", 0, policy) == 300
    assert effective_interval_seconds("active", 120, policy) == 120


def test_cadence_rejects_invalid_policy_instead_of_polling_unsafely() -> None:
    """M04-PURE-003: invalid/unknown source constraints do not get a default."""
    try:
        CollectionCadencePolicyV1(
            active_interval_seconds=300,
            idle_interval_seconds=60,
        )
    except CollectionPolicyErrorV1 as error:
        assert error.code == "collection_cadence_policy_invalid"
    else:
        raise AssertionError("an unsafe cadence policy was accepted")

    try:
        effective_interval_seconds(
            "active",
            None,
            CollectionCadencePolicyV1(60, 300),
        )
    except CollectionPolicyErrorV1 as error:
        assert error.code == "collection_constraints_unknown"
    else:
        raise AssertionError("an unknown source minimum was admitted")


def test_retry_policy_keeps_auth_compatibility_and_delay_distinct() -> None:
    """M04-PURE-010..014/018: outcome classes never collapse to success."""
    assert decide_retry("success", None).kind == "normal_cadence"
    assert decide_retry("partial", None).kind == "normal_cadence"
    assert decide_retry("rate_limited", 90).kind == "delayed_retry"
    assert decide_retry("rate_limited", 90).delay_seconds == 90
    assert decide_retry("reauthentication_required", None).kind == "auth_block"
    assert decide_retry("unverified_provider_version", None).kind == (
        "compatibility_block"
    )
    assert decide_retry("unsupported", None).kind == "unsupported"


def test_run_and_failure_contracts_reject_impossible_or_unsafe_state() -> None:
    """M04-PURE-016/017: lifecycle fields and error codes are closed."""
    try:
        CollectionFailedV1(
            run_id=OpaqueIdV1("run-one"),
            terminal_state="failed",
            error_code="raw provider error!",
            completed_at=datetime(2026, 9, 22, tzinfo=UTC),
        )
    except InvalidCollectionControlV1 as error:
        assert error.code == "collection_error_code_invalid"
    else:
        raise AssertionError("free-form provider error entered the contract")

    try:
        CollectionRunViewV1(
            run_id=OpaqueIdV1("run-one"),
            schedule_id=OpaqueIdV1("schedule-one"),
            provider_key="claude",
            account_id=OpaqueIdV1("account-one"),
            resource_id=OpaqueIdV1("resource-one"),
            capability_id="subscription.quota",
            state="queued",
            source_id="claude.subscription.usage.screen_reader",
            adapter_version="1.0.0",
            provider_version="2.1.278",
            target_generation=1,
            fencing_token=1,
            requested_at=datetime(2026, 9, 22, tzinfo=UTC),
            started_at=datetime(2026, 9, 22, tzinfo=UTC),
            completed_at=None,
            deadline_at=datetime(2026, 9, 22, 0, 1, tzinfo=UTC),
            duration_ms=None,
            payload_digest=None,
            outcome_code=None,
            error_code=None,
            observation_ids=(),
        )
    except InvalidCollectionControlV1 as error:
        assert error.code == "collection_run_state_invalid"
    else:
        raise AssertionError("queued run carried a started timestamp")


def test_commit_receipt_contract_carries_complete_recovery_evidence() -> None:
    """M04-PURE-015: receipt exposes all durable M05 reconciliation refs."""
    names = {field.name for field in fields(CollectionCommitReceiptV1)}
    assert {
        "observation_set_digest",
        "stored_at_start",
        "stored_at_end",
        "affected_projection_ids",
        "projection_versions",
        "event_ids",
    } <= names
