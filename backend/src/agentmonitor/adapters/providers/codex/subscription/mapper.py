"""Pure Codex 0.160.0 subscription and capacity mapping."""

from datetime import UTC, datetime
from decimal import Decimal

from agentmonitor.adapters.providers.codex.subscription.schema import (
    CodexRateLimitBucketSourceV1,
    CodexRateLimitsSourceV1,
    CodexRateLimitWindowSourceV1,
)
from agentmonitor.contracts.capacity_v1 import (
    CapacitySubjectV1,
    ConfidenceV1,
    ExactMetricFieldV1,
    ProviderQuotaInputV1,
    ProviderQuotaWindowInputV1,
    ValueKindV1,
)
from agentmonitor.contracts.collection_control_v1 import CollectionRunAdmissionV1
from agentmonitor.contracts.common_quantity_v1 import ExactQuantityV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.providers.codex.subscription_quota.v1.schema import (
    CodexQuotaWindowV1,
    CodexRateLimitBucketV1,
    CodexSubscriptionQuotaV1,
    CodexWindowRoleV1,
)


def _map_window(
    source: CodexRateLimitWindowSourceV1, role: CodexWindowRoleV1
) -> CodexQuotaWindowV1:
    used = Decimal(source.used_percent)
    reset = (
        datetime.fromtimestamp(source.resets_at_unix_seconds, tz=UTC)
        if source.resets_at_unix_seconds is not None
        else None
    )
    return CodexQuotaWindowV1(
        role=role,
        used_percent=used,
        remaining_percent=Decimal("100") - used,
        window_duration_minutes=source.window_duration_minutes,
        resets_at=reset,
    )


def _map_bucket(source: CodexRateLimitBucketSourceV1) -> CodexRateLimitBucketV1:
    return CodexRateLimitBucketV1(
        limit_id=source.limit_id,
        safe_label=source.safe_label,
        plan_type=source.plan_type,
        rate_limit_reached_type=source.rate_limit_reached_type,
        primary=_map_window(source.primary, "primary"),
        secondary=(
            _map_window(source.secondary, "secondary")
            if source.secondary is not None
            else None
        ),
    )


def map_subscription_quota(
    source: CodexRateLimitsSourceV1,
    *,
    account_ref: OpaqueIdV1,
    resource_ref: OpaqueIdV1,
) -> CodexSubscriptionQuotaV1:
    """Map the discarded-raw source DTO into the public Codex contract."""
    if not isinstance(source, CodexRateLimitsSourceV1):
        raise TypeError("codex_rate_limits_source_required")
    return CodexSubscriptionQuotaV1(
        account_ref=account_ref,
        resource_ref=resource_ref,
        resource_kind="subscription_pool",
        ordinary_usage_allowed=source.ordinary_usage_allowed,
        buckets=tuple(
            _map_bucket(item)
            for item in sorted(source.buckets, key=lambda item: item.limit_id)
        ),
        completeness="complete",
    )


def _available(
    value: Decimal,
    *,
    unit: str,
    value_kind: ValueKindV1,
    confidence: ConfidenceV1,
) -> ExactMetricFieldV1:
    return ExactMetricFieldV1(
        availability=FieldAvailabilityV1("available"),
        value=ExactQuantityV1.from_decimal(value, unit=unit),
        precision="exact",
        confidence=confidence,
        value_kind=value_kind,
        reason_code=None,
    )


def _unknown(reason_code: str) -> ExactMetricFieldV1:
    return ExactMetricFieldV1(
        availability=FieldAvailabilityV1("unknown"),
        value=None,
        precision="unknown",
        confidence="unknown",
        value_kind="unknown",
        reason_code=reason_code,
    )


def map_codex_quota_to_capacity(
    quota: CodexSubscriptionQuotaV1,
    admission: CollectionRunAdmissionV1,
) -> ProviderQuotaInputV1:
    """Map subscription windows into CTR-CAP-001 without API-billing data."""
    if (
        admission.provider_key != "codex"
        or admission.capability_id != "subscription.quota"
        or admission.account_id != quota.account_ref
        or admission.resource_id != quota.resource_ref
        or quota.resource_kind != "subscription_pool"
    ):
        raise ValueError("codex_capacity_target_mismatch")

    windows: list[ProviderQuotaWindowInputV1] = []
    for bucket in quota.buckets:
        native_windows = (bucket.primary,) + (
            (bucket.secondary,) if bucket.secondary is not None else ()
        )
        for window in native_windows:
            windows.append(
                ProviderQuotaWindowInputV1(
                    window_key=f"{bucket.limit_id}:{window.role}",
                    safe_label=bucket.safe_label or bucket.limit_id,
                    semantic_role=window.role,
                    is_constraining=True,
                    used=_available(
                        window.used_percent,
                        unit="percent",
                        value_kind="provider_reported",
                        confidence="confirmed",
                    ),
                    remaining=_available(
                        window.remaining_percent,
                        unit="percent",
                        value_kind="derived",
                        confidence="high",
                    ),
                    limit=_unknown("source_does_not_report_native_limit_quantity"),
                    remaining_ratio=_available(
                        window.remaining_percent / Decimal("100"),
                        unit="ratio",
                        value_kind="derived",
                        confidence="high",
                    ),
                    reset_at=window.resets_at,
                    reset_precision=(
                        "exact" if window.resets_at is not None else "unknown"
                    ),
                )
            )

    return ProviderQuotaInputV1(
        subject=CapacitySubjectV1(
            provider_key="codex",
            installation_id=admission.installation_id,
            account_id=quota.account_ref,
            resource_id=quota.resource_ref,
        ),
        registry_revision=admission.registry_revision,
        capability_schema_version="1.0",
        completeness="complete_scope",
        windows=tuple(windows),
    )
