"""Pure validation of minimized official-browser comparison results."""

from datetime import UTC, datetime, timedelta

import pytest

from tools.automation.implementations.m6_authoritative_evidence import (
    parse_authoritative_comparison_v1,
)

NOW = datetime(2026, 11, 3, 14, tzinfo=UTC)


def document():
    return {
        "record_type": "agentmonitor.m6_authoritative_comparison.v1",
        "pairing_provenance": "owner_asserted_visible_principal",
        "schema_version": "1.0.0",
        "status": "passed",
        "reason_code": "official_usage_compared",
        "source_revision": "a" * 40,
        "compared_targets": 1,
        "current_balance_lineage_sha256": "b" * 64,
        "comparison_sha256": "c" * 64,
        "started_at": (NOW - timedelta(seconds=5)).isoformat(),
        "completed_at": NOW.isoformat(),
        "provider_observed_at": (NOW - timedelta(seconds=1)).isoformat(),
        "source_observed_at": (NOW - timedelta(minutes=2)).isoformat(),
    }


def test_genuine_comparison_envelope_retains_only_counts_digests_and_times():
    evidence = parse_authoritative_comparison_v1(
        document(), revision="a" * 40, return_code=0, now=NOW
    )
    assert evidence.compared_targets == 1
    assert evidence.current_balance_lineage_sha256 == "b" * 64


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_revision", "d" * 40),
        ("compared_targets", 0),
        ("compared_targets", 101),
        ("provider_observed_at", None),
        ("source_observed_at", None),
        ("comparison_sha256", "bad"),
        ("reason_code", "unproved"),
        ("started_at", (NOW - timedelta(seconds=91)).isoformat()),
        ("source_observed_at", (NOW + timedelta(seconds=5)).isoformat()),
    ],
)
def test_unbound_incomplete_or_overlong_comparison_is_rejected(field, value):
    data = document()
    data[field] = value
    with pytest.raises(ValueError, match="m6_authoritative_evidence_invalid"):
        parse_authoritative_comparison_v1(
            data, revision="a" * 40, return_code=0, now=NOW
        )


def test_raw_account_or_amount_fields_are_rejected():
    data = document()
    data["monthly_usd"] = "42.38"
    with pytest.raises(ValueError, match="m6_authoritative_evidence_invalid"):
        parse_authoritative_comparison_v1(
            data, revision="a" * 40, return_code=0, now=NOW
        )
