"""Pure closed-envelope validation for real official Usage comparisons."""

import hashlib
import re
from dataclasses import dataclass, fields
from datetime import datetime, timedelta
from typing import Literal


@dataclass(frozen=True, slots=True)
class AuthoritativeComparisonV1:
    record_type: str
    schema_version: str
    status: Literal["passed", "failed", "not_run"]
    reason_code: str
    source_revision: str
    compared_targets: int
    current_balance_lineage_sha256: str
    comparison_sha256: str
    started_at: str
    completed_at: str
    provider_observed_at: str | None
    source_observed_at: str | None
    pairing_provenance: str = "owner_asserted_visible_principal"
    reset_unavailable_targets: int = 0


def parse_authoritative_comparison_v1(
    value: object,
    *,
    revision: str,
    return_code: int | None,
    now: datetime,
) -> AuthoritativeComparisonV1:
    try:
        if not isinstance(value, dict) or set(value) != {
            field.name for field in fields(AuthoritativeComparisonV1)
        }:
            raise ValueError
        result = AuthoritativeComparisonV1(**value)
        start = datetime.fromisoformat(result.started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(result.completed_at.replace("Z", "+00:00"))
        allowed = {
            "passed": {
                "official_usage_compared",
                "official_usage_balances_compared_reset_unavailable",
            },
            "failed": {"official_usage_value_mismatch"},
            "not_run": {
                "official_usage_pairing_unproven",
                "official_usage_observation_timeout",
                "official_usage_dashboard_unavailable",
                "official_usage_revision_mismatch",
                "official_usage_credit_view_unavailable",
                "official_usage_connection_unavailable",
                "official_usage_capacity_unavailable",
                "official_usage_lineage_changed",
                "official_usage_boundary_unavailable",
            },
        }
        if (
            result.record_type != "agentmonitor.m6_authoritative_comparison.v1"
            or result.schema_version != "1.1.0"
            or result.pairing_provenance != "owner_asserted_visible_principal"
            or result.source_revision != revision
            or re.fullmatch(r"[a-f0-9]{40}", revision) is None
            or result.reason_code not in allowed.get(result.status, set())
            or return_code
            != {"passed": 0, "failed": 1, "not_run": 3}.get(result.status)
            or type(result.compared_targets) is not int
            or not 0 <= result.compared_targets <= 100
            or type(result.reset_unavailable_targets) is not int
            or not 0 <= result.reset_unavailable_targets <= result.compared_targets
            or start.utcoffset() != timedelta(0)
            or end.utcoffset() != timedelta(0)
            or now.utcoffset() != timedelta(0)
            or not start <= end <= start + timedelta(seconds=90)
            or not now - timedelta(seconds=30) <= end <= now
            or any(
                re.fullmatch(r"[a-f0-9]{64}", item) is None
                for item in (
                    result.current_balance_lineage_sha256,
                    result.comparison_sha256,
                )
            )
        ):
            raise ValueError
        if result.status == "passed":
            if (
                result.compared_targets < 1
                or result.provider_observed_at is None
                or result.source_observed_at is None
                or (
                    result.reason_code
                    == "official_usage_balances_compared_reset_unavailable"
                )
                != (result.reset_unavailable_targets > 0)
            ):
                raise ValueError
            provider = datetime.fromisoformat(
                result.provider_observed_at.replace("Z", "+00:00")
            )
            source = datetime.fromisoformat(
                result.source_observed_at.replace("Z", "+00:00")
            )
            if (
                provider.utcoffset() != timedelta(0)
                or source.utcoffset() != timedelta(0)
                or not start <= provider <= end
                or source > provider
                or hashlib.sha256(b"").hexdigest()
                in (result.current_balance_lineage_sha256, result.comparison_sha256)
            ):
                raise ValueError
        elif result.compared_targets != 0:
            raise ValueError
        return result
    except (ValueError, TypeError, AttributeError):
        raise ValueError("m6_authoritative_evidence_invalid") from None
