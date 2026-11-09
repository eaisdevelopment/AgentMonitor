"""Map sanitized Claude `/usage` fields into the closed V1 contract."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from agentmonitor.contracts.capacity_v1 import (
    CapacitySubjectV1,
    ExactMetricFieldV1,
    ProviderQuotaInputV1,
    ProviderQuotaWindowInputV1,
)
from agentmonitor.contracts.collection_control_v1 import CollectionRunAdmissionV1
from agentmonitor.contracts.common_quantity_v1 import ExactQuantityV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.providers.claude.subscription_quota.v1.schema import (
    ClaudePercentUsedV1,
    ClaudeQuotaWindowV1,
    ClaudeResetDisplayV1,
    ClaudeSubscriptionQuotaV1,
)

SanitizedWindowKey = Literal[
    "current_session",
    "current_week_all_models",
    "current_week_sonnet_only",
]


@dataclass(frozen=True, slots=True)
class SanitizedClaudeUsageWindow:
    """Allowlisted source output; no arbitrary terminal field can be carried."""

    window_key: SanitizedWindowKey
    percent_used: Decimal | None
    reset_display: str | None


@dataclass(frozen=True, slots=True)
class SanitizedClaudeUsageSnapshot:
    """Allowlisted source result after raw terminal bytes have been discarded."""

    windows: tuple[SanitizedClaudeUsageWindow, ...]
    observed_at: datetime
    collected_at: datetime
    omission_codes: tuple[str, ...] = ()


_WINDOW_METADATA = {
    "current_session": ("Current session", "all_models"),
    "current_week_all_models": ("Current week (all models)", "all_models"),
    "current_week_sonnet_only": (
        "Current week (Sonnet only)",
        "sonnet_only",
    ),
}


def map_subscription_quota(
    snapshot: SanitizedClaudeUsageSnapshot,
    *,
    account_ref: OpaqueIdV1,
    resource_ref: OpaqueIdV1,
) -> ClaudeSubscriptionQuotaV1:
    """Perform the deterministic provider-specific mapping only."""
    windows = tuple(
        ClaudeQuotaWindowV1(
            window_key=item.window_key,
            safe_label=_WINDOW_METADATA[item.window_key][0],
            model_scope=_WINDOW_METADATA[item.window_key][1],  # type: ignore[arg-type]
            percent_used=ClaudePercentUsedV1(
                value=item.percent_used,
                unit="percent",
                availability=FieldAvailabilityV1(
                    "available" if item.percent_used is not None else "unknown"
                ),
            ),
            reset_display=ClaudeResetDisplayV1(
                value=item.reset_display,
                availability=FieldAvailabilityV1(
                    "available" if item.reset_display is not None else "unknown"
                ),
                precision=(
                    "provider_display" if item.reset_display is not None else "unknown"
                ),
            ),
        )
        for item in snapshot.windows
    )
    return ClaudeSubscriptionQuotaV1(
        account_ref=account_ref,
        resource_ref=resource_ref,
        plan_class="claude_max",
        windows=windows,
        completeness="complete",
    )


def map_claude_quota_to_capacity(
    quota: ClaudeSubscriptionQuotaV1,
    admission: CollectionRunAdmissionV1,
) -> ProviderQuotaInputV1:
    """Normalize the closed Claude result without inventing missing values."""
    if (
        admission.provider_key != "claude"
        or admission.account_id != quota.account_ref
        or admission.resource_id != quota.resource_ref
    ):
        raise ValueError("claude_capacity_target_mismatch")

    def unknown(reason_code: str) -> ExactMetricFieldV1:
        return ExactMetricFieldV1(
            availability=FieldAvailabilityV1("unknown"),
            value=None,
            precision="unknown",
            confidence="unknown",
            value_kind="unknown",
            reason_code=reason_code,
        )

    windows = tuple(
        ProviderQuotaWindowInputV1(
            window_key=window.window_key,
            safe_label=window.safe_label,
            semantic_role=(
                "session" if window.window_key == "current_session" else "weekly"
            ),
            is_constraining=True,
            used=ExactMetricFieldV1(
                availability=window.percent_used.availability,
                value=(
                    ExactQuantityV1.from_decimal(
                        window.percent_used.value, unit="percent"
                    )
                    if window.percent_used.value is not None
                    else None
                ),
                precision=(
                    "rounded" if window.percent_used.value is not None else "unknown"
                ),
                confidence=(
                    "confirmed" if window.percent_used.value is not None else "unknown"
                ),
                value_kind=(
                    "provider_reported"
                    if window.percent_used.value is not None
                    else "unknown"
                ),
                reason_code=(
                    None
                    if window.percent_used.value is not None
                    else "source_value_unknown"
                ),
            ),
            remaining=unknown("source_does_not_report_remaining"),
            limit=unknown("source_does_not_report_limit"),
            remaining_ratio=unknown("source_does_not_report_remaining_ratio"),
            reset_at=None,
            reset_precision="unknown",
        )
        for window in quota.windows
    )
    return ProviderQuotaInputV1(
        subject=CapacitySubjectV1(
            provider_key="claude",
            installation_id=admission.installation_id,
            account_id=quota.account_ref,
            resource_id=quota.resource_ref,
        ),
        registry_revision=admission.registry_revision,
        capability_schema_version="1.0",
        completeness="complete_scope",
        windows=windows,
    )
