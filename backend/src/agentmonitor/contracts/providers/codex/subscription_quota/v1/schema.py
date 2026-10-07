"""Closed Codex CLI 0.160.0 subscription-quota output contract."""

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import ClassVar, Literal

from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1

CodexWindowRoleV1 = Literal["primary", "secondary"]
CodexPlanTypeV1 = Literal[
    "free",
    "go",
    "plus",
    "pro",
    "prolite",
    "promax",
    "team",
    "self_serve_business_prolite",
    "self_serve_business_usage_based",
    "business",
    "ent26",
    "enterprise_cbp_automation",
    "enterprise_cbp_usage_based",
    "enterprise",
    "edu",
    "edu_plus",
    "edu_pro",
    "unknown",
]
CodexRateLimitReachedTypeV1 = Literal[
    "rate_limit_reached",
    "workspace_owner_credits_depleted",
    "workspace_member_credits_depleted",
    "workspace_owner_usage_limit_reached",
    "workspace_member_usage_limit_reached",
]

_LIMIT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,127}\Z")
_PLAN_TYPES = {
    "free",
    "go",
    "plus",
    "pro",
    "prolite",
    "promax",
    "team",
    "self_serve_business_prolite",
    "self_serve_business_usage_based",
    "business",
    "ent26",
    "enterprise_cbp_automation",
    "enterprise_cbp_usage_based",
    "enterprise",
    "edu",
    "edu_plus",
    "edu_pro",
    "unknown",
}
_REACHED_TYPES = {
    "rate_limit_reached",
    "workspace_owner_credits_depleted",
    "workspace_member_credits_depleted",
    "workspace_owner_usage_limit_reached",
    "workspace_member_usage_limit_reached",
}


class InvalidCodexSubscriptionQuotaV1(ValueError):
    """The closed Codex subscription result violates its V1 contract."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _valid_label(value: object) -> bool:
    return (
        value is None
        or type(value) is str
        and value == value.strip()
        and 1 <= len(value) <= 96
        and value.isprintable()
    )


@dataclass(frozen=True, slots=True)
class CodexQuotaWindowV1(TechnicalValueV1):
    """One native primary or secondary Codex subscription window."""

    CONTRACT_ID: ClassVar[str] = "CODEX-SUBSCRIPTION-QUOTA-V1"
    OWNER: ClassVar[str] = "PLAN-A02"

    role: CodexWindowRoleV1
    used_percent: Decimal
    remaining_percent: Decimal
    window_duration_minutes: int | None
    resets_at: datetime | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.used_percent) is not Decimal
            or type(self.remaining_percent) is not Decimal
            or self.used_percent != self.used_percent.to_integral_value()
            or not Decimal("0") <= self.used_percent <= Decimal("100")
            or self.remaining_percent != Decimal("100") - self.used_percent
        ):
            raise InvalidCodexSubscriptionQuotaV1("codex_quota_percentage_invalid")
        if self.window_duration_minutes is not None and (
            type(self.window_duration_minutes) is not int
            or not 1 <= self.window_duration_minutes <= 2**63 - 1
        ):
            raise InvalidCodexSubscriptionQuotaV1("codex_quota_duration_invalid")
        if self.resets_at is not None and type(self.resets_at) is not datetime:
            raise InvalidCodexSubscriptionQuotaV1("codex_quota_reset_invalid")


@dataclass(frozen=True, slots=True)
class CodexRateLimitBucketV1(TechnicalValueV1):
    """One native Codex limit ID with its primary and optional secondary window."""

    CONTRACT_ID: ClassVar[str] = "CODEX-SUBSCRIPTION-QUOTA-V1"
    OWNER: ClassVar[str] = "PLAN-A02"

    limit_id: str
    safe_label: str | None
    plan_type: CodexPlanTypeV1 | None
    rate_limit_reached_type: CodexRateLimitReachedTypeV1 | None
    primary: CodexQuotaWindowV1
    secondary: CodexQuotaWindowV1 | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if type(self.limit_id) is not str or _LIMIT_ID.fullmatch(self.limit_id) is None:
            raise InvalidCodexSubscriptionQuotaV1("codex_quota_limit_id_invalid")
        if not _valid_label(self.safe_label):
            raise InvalidCodexSubscriptionQuotaV1("codex_quota_label_invalid")
        if self.plan_type is not None and self.plan_type not in _PLAN_TYPES:
            raise InvalidCodexSubscriptionQuotaV1("codex_quota_plan_type_invalid")
        if (
            self.rate_limit_reached_type is not None
            and self.rate_limit_reached_type not in _REACHED_TYPES
        ):
            raise InvalidCodexSubscriptionQuotaV1("codex_quota_reached_type_invalid")
        if (
            not isinstance(self.primary, CodexQuotaWindowV1)
            or self.primary.role != "primary"
        ):
            raise InvalidCodexSubscriptionQuotaV1("codex_quota_primary_window_invalid")
        if self.secondary is not None and (
            not isinstance(self.secondary, CodexQuotaWindowV1)
            or self.secondary.role != "secondary"
        ):
            raise InvalidCodexSubscriptionQuotaV1(
                "codex_quota_secondary_window_invalid"
            )


@dataclass(frozen=True, slots=True)
class CodexSubscriptionQuotaV1(TechnicalValueV1):
    """Sanitized subscription-only result from the admitted Codex source."""

    CONTRACT_ID: ClassVar[str] = "CODEX-SUBSCRIPTION-QUOTA-V1"
    OWNER: ClassVar[str] = "PLAN-A02"

    account_ref: OpaqueIdV1
    resource_ref: OpaqueIdV1
    resource_kind: Literal["subscription_pool"]
    ordinary_usage_allowed: bool | None
    buckets: tuple[CodexRateLimitBucketV1, ...]
    completeness: Literal["complete"]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not isinstance(self.account_ref, OpaqueIdV1) or not isinstance(
            self.resource_ref, OpaqueIdV1
        ):
            raise InvalidCodexSubscriptionQuotaV1("codex_quota_target_invalid")
        if (
            self.ordinary_usage_allowed is not None
            and type(self.ordinary_usage_allowed) is not bool
        ):
            raise InvalidCodexSubscriptionQuotaV1(
                "codex_quota_usage_permission_invalid"
            )
        if not 1 <= len(self.buckets) <= 32 or not all(
            isinstance(item, CodexRateLimitBucketV1) for item in self.buckets
        ):
            raise InvalidCodexSubscriptionQuotaV1("codex_quota_bucket_set_invalid")
        limit_ids = tuple(item.limit_id for item in self.buckets)
        if len(limit_ids) != len(set(limit_ids)):
            raise InvalidCodexSubscriptionQuotaV1("codex_quota_limit_id_duplicate")
