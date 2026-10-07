"""Pure closed Codex subscription contract checks; no provider I/O occurs."""

from dataclasses import fields
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.providers.codex.subscription_quota.v1.schema import (
    CodexQuotaWindowV1,
    CodexRateLimitBucketV1,
    CodexSubscriptionQuotaV1,
    InvalidCodexSubscriptionQuotaV1,
)

RESET_AT = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)


def _window(
    role: str = "primary",
    *,
    used_percent: Decimal = Decimal("18"),
    remaining_percent: Decimal = Decimal("82"),
    window_duration_minutes: int | None = 300,
    resets_at: datetime | None = RESET_AT,
) -> CodexQuotaWindowV1:
    return CodexQuotaWindowV1(
        role=role,  # type: ignore[arg-type]
        used_percent=used_percent,
        remaining_percent=remaining_percent,
        window_duration_minutes=window_duration_minutes,
        resets_at=resets_at,
    )


def _bucket(
    limit_id: str = "codex",
    *,
    primary: CodexQuotaWindowV1 | None = None,
    secondary: CodexQuotaWindowV1 | None = None,
) -> CodexRateLimitBucketV1:
    return CodexRateLimitBucketV1(
        limit_id=limit_id,
        safe_label="Codex",
        plan_type="plus",
        rate_limit_reached_type=None,
        primary=primary or _window(),
        secondary=secondary,
    )


def test_codex_subscription_contract_is_closed_and_subscription_only() -> None:
    """M5-CDX-PURE-001: the typed result cannot carry billing or raw data."""
    quota = CodexSubscriptionQuotaV1(
        account_ref=OpaqueIdV1("account-one"),
        resource_ref=OpaqueIdV1("resource-one"),
        resource_kind="subscription_pool",
        ordinary_usage_allowed=True,
        buckets=(_bucket(),),
        completeness="complete",
    )

    assert quota.resource_kind == "subscription_pool"
    assert quota.buckets[0].limit_id == "codex"
    assert {field.name for field in fields(quota)} == {
        "account_ref",
        "resource_ref",
        "resource_kind",
        "ordinary_usage_allowed",
        "buckets",
        "completeness",
    }
    all_names = {
        field.name
        for contract in (quota, quota.buckets[0], quota.buckets[0].primary)
        for field in fields(contract)
    }
    assert all_names.isdisjoint(
        {
            "raw_payload",
            "credits",
            "reset_credits",
            "balance",
            "spend_limit",
            "openai_api",
            "account_id",
        }
    )


@pytest.mark.parametrize(
    ("used", "remaining"),
    [
        (Decimal("-1"), Decimal("101")),
        (Decimal("101"), Decimal("-1")),
        (Decimal("18"), Decimal("81")),
        (Decimal("18.5"), Decimal("81.5")),
    ],
)
def test_codex_window_rejects_invalid_percentages(
    used: Decimal, remaining: Decimal
) -> None:
    """M5-CDX-PURE-002: exact provider integers and complement are enforced."""
    with pytest.raises(InvalidCodexSubscriptionQuotaV1):
        _window(used_percent=used, remaining_percent=remaining)


@pytest.mark.parametrize("duration", [0, -1, True])
def test_codex_window_rejects_invalid_duration(duration: object) -> None:
    """M5-CDX-PURE-003: nullable duration is positive when present."""
    with pytest.raises(InvalidCodexSubscriptionQuotaV1):
        _window(window_duration_minutes=duration)  # type: ignore[arg-type]


def test_codex_window_preserves_null_duration_and_reset() -> None:
    """M5-CDX-PURE-004: provider null is preserved rather than inferred."""
    window = _window(window_duration_minutes=None, resets_at=None)

    assert window.window_duration_minutes is None
    assert window.resets_at is None


@pytest.mark.parametrize("limit_id", ["", " codex", "codex limit", "x" * 129])
def test_codex_bucket_rejects_invalid_native_limit_id(limit_id: str) -> None:
    """M5-CDX-PURE-005: native IDs are bounded before becoming M05 keys."""
    with pytest.raises(InvalidCodexSubscriptionQuotaV1):
        _bucket(limit_id)


def test_codex_bucket_requires_primary_and_correct_roles() -> None:
    """M5-CDX-PURE-006: primary and secondary roles cannot be relabelled."""
    with pytest.raises(InvalidCodexSubscriptionQuotaV1):
        CodexRateLimitBucketV1(
            limit_id="codex",
            safe_label=None,
            plan_type=None,
            rate_limit_reached_type=None,
            primary=None,  # type: ignore[arg-type]
            secondary=None,
        )
    with pytest.raises(InvalidCodexSubscriptionQuotaV1):
        _bucket(primary=_window("secondary"))
    with pytest.raises(InvalidCodexSubscriptionQuotaV1):
        _bucket(secondary=_window("primary"))


def test_codex_subscription_rejects_duplicate_limit_ids() -> None:
    """M5-CDX-PURE-007: buckets remain separate by native identity."""
    with pytest.raises(InvalidCodexSubscriptionQuotaV1):
        CodexSubscriptionQuotaV1(
            account_ref=OpaqueIdV1("account-one"),
            resource_ref=OpaqueIdV1("resource-one"),
            resource_kind="subscription_pool",
            ordinary_usage_allowed=None,
            buckets=(_bucket(), _bucket()),
            completeness="complete",
        )


@pytest.mark.parametrize("allowed", [0, 1, "true"])
def test_codex_subscription_rejects_non_boolean_usage_permission(
    allowed: object,
) -> None:
    """M5-CDX-PURE-008: unavailable permission is null, never a coercion."""
    with pytest.raises(InvalidCodexSubscriptionQuotaV1):
        CodexSubscriptionQuotaV1(
            account_ref=OpaqueIdV1("account-one"),
            resource_ref=OpaqueIdV1("resource-one"),
            resource_kind="subscription_pool",
            ordinary_usage_allowed=allowed,  # type: ignore[arg-type]
            buckets=(_bucket(),),
            completeness="complete",
        )
