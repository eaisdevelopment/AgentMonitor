"""Closed Claude subscription-quota output for the evidenced V1 source."""

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar, Literal

from agentmonitor.contracts.common_v1 import (
    FieldAvailabilityV1,
    OpaqueIdV1,
    TechnicalValueV1,
)

ClaudeWindowKeyV1 = Literal[
    "current_session",
    "current_week_all_models",
    "current_week_sonnet_only",
]
ClaudeModelScopeV1 = Literal["all_models", "sonnet_only"]


@dataclass(frozen=True, slots=True)
class ClaudePercentUsedV1(TechnicalValueV1):
    """Provider-reported rounded percentage; missing is never zero."""

    CONTRACT_ID: ClassVar[str] = "CLAUDE-SUBSCRIPTION-QUOTA-V1"
    OWNER: ClassVar[str] = "PLAN-A01"

    value: Decimal | None
    unit: Literal["percent"]
    availability: FieldAvailabilityV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        is_available = self.availability.state == "available"
        if (self.value is not None) != is_available:
            raise ValueError("claude_percent_availability_invalid")
        if self.value is not None and not Decimal("0") <= self.value <= Decimal("100"):
            raise ValueError("claude_percent_out_of_range")


@dataclass(frozen=True, slots=True)
class ClaudeResetDisplayV1(TechnicalValueV1):
    """Bounded provider display text; AgentMonitor does not infer an instant."""

    CONTRACT_ID: ClassVar[str] = "CLAUDE-SUBSCRIPTION-QUOTA-V1"
    OWNER: ClassVar[str] = "PLAN-A01"

    value: str | None
    availability: FieldAvailabilityV1
    precision: Literal["provider_display", "unknown"]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        is_available = self.availability.state == "available"
        if (self.value is not None) != is_available:
            raise ValueError("claude_reset_availability_invalid")
        if self.value is not None:
            if (
                not self.value.startswith("Resets ")
                or not 8 <= len(self.value) <= 96
                or not self.value.isprintable()
            ):
                raise ValueError("claude_reset_display_invalid")
            if self.precision != "provider_display":
                raise ValueError("claude_reset_precision_invalid")
        elif self.precision != "unknown":
            raise ValueError("claude_reset_precision_invalid")


@dataclass(frozen=True, slots=True)
class ClaudeQuotaWindowV1(TechnicalValueV1):
    """One native Claude quota window from the accepted screen-reader view."""

    CONTRACT_ID: ClassVar[str] = "CLAUDE-SUBSCRIPTION-QUOTA-V1"
    OWNER: ClassVar[str] = "PLAN-A01"

    window_key: ClaudeWindowKeyV1
    safe_label: str
    model_scope: ClaudeModelScopeV1
    percent_used: ClaudePercentUsedV1
    reset_display: ClaudeResetDisplayV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        expected = {
            "current_session": ("Current session", "all_models"),
            "current_week_all_models": (
                "Current week (all models)",
                "all_models",
            ),
            "current_week_sonnet_only": (
                "Current week (Sonnet only)",
                "sonnet_only",
            ),
        }
        if expected[self.window_key] != (self.safe_label, self.model_scope):
            raise ValueError("claude_window_identity_invalid")


@dataclass(frozen=True, slots=True)
class ClaudeSubscriptionQuotaV1(TechnicalValueV1):
    """One complete, current Claude subscription collection batch."""

    CONTRACT_ID: ClassVar[str] = "CLAUDE-SUBSCRIPTION-QUOTA-V1"
    OWNER: ClassVar[str] = "PLAN-A01"

    account_ref: OpaqueIdV1
    resource_ref: OpaqueIdV1
    plan_class: Literal["claude_max"]
    windows: tuple[ClaudeQuotaWindowV1, ...]
    completeness: Literal["complete"]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        keys = tuple(window.window_key for window in self.windows)
        if not 2 <= len(keys) <= 3 or len(keys) != len(set(keys)):
            raise ValueError("claude_window_set_invalid")
        if "current_session" not in keys or "current_week_all_models" not in keys:
            raise ValueError("claude_required_window_missing")
