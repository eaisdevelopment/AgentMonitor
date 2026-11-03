"""Pure checks of the closed interval-evidence envelope; no boundary substitution."""

from datetime import UTC, datetime, timedelta

import pytest

from tools.automation.implementations.m6_recovery_evidence import (
    parse_recovery_interval_v1,
)

NOW = datetime(2026, 11, 3, 13, tzinfo=UTC)


def document():
    return {
        "record_type": "agentmonitor.m6_recovery_interval.v1",
        "schema_version": "1.0.0",
        "status": "passed",
        "reason_code": "m6_recovery_observed",
        "source_revision": "a" * 40,
        "service_invocation_id": "b" * 32,
        "natural_recovery_targets": 1,
        "cross_provider_continuity_targets": 1,
        "dashboard_sample_count": 2,
        "lineage_sha256": "c" * 64,
        "started_at": (NOW - timedelta(seconds=30)).isoformat(),
        "completed_at": NOW.isoformat(),
        "dashboard_observed_at": [
            (NOW - timedelta(seconds=20)).isoformat(),
            NOW.isoformat(),
        ],
        "continuity_run_ids": [["claude", "run-claude"], ["codex", "run-codex"]],
        "recovery_run_pairs": [["run-failed", "run-recovered"]],
    }


def test_actual_interval_envelope_preserves_identity_and_lineage():
    result = parse_recovery_interval_v1(
        document(), revision="a" * 40, return_code=0, now=NOW
    )
    assert result.service_invocation_id == "b" * 32
    assert (
        result.natural_recovery_targets == result.cross_provider_continuity_targets == 1
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_revision", "d" * 40),
        ("service_invocation_id", None),
        ("dashboard_sample_count", 1),
        ("natural_recovery_targets", 0),
        ("cross_provider_continuity_targets", 0),
        ("lineage_sha256", "bad"),
        ("completed_at", (NOW - timedelta(hours=1)).isoformat()),
        ("started_at", (NOW - timedelta(seconds=661)).isoformat()),
        ("status", "invented"),
        ("reason_code", "arbitrary_text"),
    ],
)
def test_incomplete_or_unbound_positive_evidence_is_rejected(field, value):
    data = document()
    data[field] = value
    with pytest.raises(ValueError):
        parse_recovery_interval_v1(data, revision="a" * 40, return_code=0, now=NOW)


def test_unobserved_condition_must_not_carry_positive_counts():
    data = document()
    data.update(
        status="not_run", reason_code="m6_recovery_current_natural_failure_absent"
    )
    with pytest.raises(ValueError):
        parse_recovery_interval_v1(data, revision="a" * 40, return_code=3, now=NOW)


@pytest.mark.parametrize(
    "field,value",
    [
        ("dashboard_observed_at", []),
        ("dashboard_observed_at", [NOW.isoformat(), NOW.isoformat()]),
        ("continuity_run_ids", [["codex", "only-codex"]]),
        ("recovery_run_pairs", [["same-run", "same-run"]]),
    ],
)
def test_interval_requires_auditable_distinct_run_and_sample_references(field, value):
    data = document()
    data[field] = value
    with pytest.raises(ValueError, match="m6_recovery_interval_evidence_invalid"):
        parse_recovery_interval_v1(data, revision="a" * 40, return_code=0, now=NOW)


def test_absent_natural_condition_is_an_explicit_zero_count_result():
    data = document()
    data.update(
        status="not_run",
        reason_code="m6_recovery_current_natural_failure_absent",
        natural_recovery_targets=0,
        cross_provider_continuity_targets=0,
        dashboard_sample_count=0,
        dashboard_observed_at=[],
        continuity_run_ids=[],
        recovery_run_pairs=[],
    )
    assert (
        parse_recovery_interval_v1(
            data, revision="a" * 40, return_code=3, now=NOW
        ).status
        == "not_run"
    )
