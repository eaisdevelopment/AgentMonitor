"""M04-ALERT-P01..P03: immutable pure facts only, no external boundary."""

import importlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import ModuleType
from typing import Any

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1

NOW = datetime(2026, 9, 29, 10, tzinfo=UTC)


def implementation() -> ModuleType:
    return importlib.import_module(
        "agentmonitor.modules.collection_control.domain.alert_conditions"
    )


def source(*, state: str = "succeeded", outcome: str | None = None) -> Any:
    policy = implementation()
    run = policy.CollectorRunFactV1(
        OpaqueIdV1("run"), 4, 1, state, NOW, outcome, None, None, state == "succeeded"
    )
    return policy.CollectorSourceSnapshotV1(
        OpaqueIdV1("schedule"),
        OpaqueIdV1("account"),
        "claude",
        "subscription.quota",
        2,
        1,
        "enabled",
        300,
        None,
        None,
        run,
        run if state == "succeeded" else None,
    )


def test_full_success_current_inverse_uses_actual_completion_and_cadence() -> None:
    policy = implementation()
    result = policy.classify_collector_condition_v1(source(), generation=3, as_of=NOW)
    assert result.health_state == "healthy" and result.freshness_state == "current"
    assert result.generation == 3
    assert result.last_successful_at == NOW
    assert result.freshness_deadline == NOW + timedelta(seconds=300)


@pytest.mark.parametrize(
    "state,health",
    [
        ("partial", "degraded"),
        ("failed", "failed"),
        ("blocked", "blocked"),
        ("cancelled", "unknown"),
        ("unsupported", "unsupported"),
    ],
)
def test_terminal_categories_do_not_fabricate_recovery(state: str, health: str) -> None:
    result = implementation().classify_collector_condition_v1(
        source(state=state), generation=2, as_of=NOW
    )
    assert result.health_state == health
    assert result.freshness_state in {"unknown", "unsupported"}
    assert result.last_successful_at is None


def test_deadline_equality_is_stale() -> None:
    result = implementation().classify_collector_condition_v1(
        source(), generation=4, as_of=NOW + timedelta(seconds=300)
    )
    assert result.freshness_state == "stale" and result.reason_code == "collector_stale"


def test_partial_does_not_recover_even_with_prior_current_full_success() -> None:
    original = source()
    partial = replace(
        original.latest_run, run_id=OpaqueIdV1("partial"), state="partial"
    )
    result = implementation().classify_collector_condition_v1(
        replace(original, latest_run=partial), generation=5, as_of=NOW
    )
    assert result.health_state == "degraded" and result.freshness_state != "current"


def test_missing_actual_success_is_unknown() -> None:
    result = implementation().classify_collector_condition_v1(
        replace(source(), latest_run=None, last_success=None), generation=1, as_of=NOW
    )
    assert result.health_state == "unknown" and result.freshness_deadline is None


def test_actual_backoff_does_not_extend_success_freshness() -> None:
    original = source()
    failed = replace(
        original.latest_run,
        state="failed",
        provider_outcome="rate_limited",
        retry_disposition="after_delay",
        retry_after=NOW + timedelta(seconds=600),
        has_committed_references=False,
    )
    result = implementation().classify_collector_condition_v1(
        replace(
            original,
            latest_run=failed,
            not_before_at=NOW + timedelta(seconds=600),
            backoff_kind="rate_limited",
        ),
        generation=5,
        as_of=NOW + timedelta(seconds=300),
    )
    assert result.health_state == "backoff" and result.retry_category == "rate_backoff"
    assert result.freshness_deadline == NOW + timedelta(seconds=300)
    assert result.freshness_state == "stale"


def test_retry_advice_without_applied_deferral_is_not_backoff() -> None:
    result = implementation().classify_collector_condition_v1(
        source(state="failed", outcome="rate_limited"), generation=3, as_of=NOW
    )
    assert result.health_state == "failed"


def test_clock_or_target_mismatch_cannot_recover() -> None:
    policy = implementation()
    result = policy.classify_collector_condition_v1(
        source(), generation=4, as_of=NOW - timedelta(seconds=1)
    )
    assert result.health_state == "unknown"
    result = policy.classify_collector_condition_v1(
        replace(source(), target_generation=2), generation=4, as_of=NOW
    )
    assert result.health_state == "unknown"
