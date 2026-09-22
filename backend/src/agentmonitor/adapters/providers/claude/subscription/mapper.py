"""Map sanitized Claude `/usage` fields into the closed V1 contract."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.providers.claude.subscription_quota.v1.schema import (
    ClaudePercentUsedV1,
    ClaudeQuotaWindowV1,
    ClaudeResetDisplayV1,
    ClaudeSubscriptionQuotaV1,
)

SanitizedWindowKey = Literal[
    "current_session", "current_week_all_models", "current_week_sonnet_only"
]


@dataclass(frozen=True, slots=True)
class SanitizedClaudeUsageWindow:
    """Allowlisted source output; no arbitrary terminal field can be carried."""

    window_key: SanitizedWindowKey
    percent_used: Decimal
    reset_display: str


@dataclass(frozen=True, slots=True)
class SanitizedClaudeUsageSnapshot:
    """Allowlisted source result after raw terminal bytes have been discarded."""

    windows: tuple[SanitizedClaudeUsageWindow, ...]
    observed_at: datetime
    collected_at: datetime


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
                availability=FieldAvailabilityV1("available"),
            ),
            reset_display=ClaudeResetDisplayV1(
                value=item.reset_display,
                availability=FieldAvailabilityV1("available"),
                precision="provider_display",
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
