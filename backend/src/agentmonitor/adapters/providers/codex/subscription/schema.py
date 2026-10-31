"""Sanitized Codex 0.160.0 rate-limit source values; never raw JSON."""

import re
from dataclasses import dataclass
from typing import ClassVar

from agentmonitor.contracts.common_v1 import TechnicalValueV1
from agentmonitor.contracts.providers.codex.subscription_quota.v1.schema import (
    CodexPlanTypeV1,
    CodexRateLimitReachedTypeV1,
)

_LIMIT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,127}\Z")
_MAX_UNIX_SECONDS = 253_402_300_799
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


class InvalidCodexRateLimitsSourceV1(ValueError):
    """An allowlisted Codex source field has an invalid shape or value."""

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
class CodexRateLimitWindowSourceV1(TechnicalValueV1):
    """Allowlisted fields from one `RateLimitWindow` after raw JSON disposal."""

    OWNER: ClassVar[str] = "PLAN-A02"

    used_percent: int
    window_duration_minutes: int | None
    resets_at_unix_seconds: int | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if type(self.used_percent) is not int or not 0 <= self.used_percent <= 100:
            raise InvalidCodexRateLimitsSourceV1("codex_source_used_percent_invalid")
        if self.window_duration_minutes is not None and (
            type(self.window_duration_minutes) is not int
            or not 1 <= self.window_duration_minutes <= 2**63 - 1
        ):
            raise InvalidCodexRateLimitsSourceV1("codex_source_duration_invalid")
        if self.resets_at_unix_seconds is not None and (
            type(self.resets_at_unix_seconds) is not int
            or not 0 <= self.resets_at_unix_seconds <= _MAX_UNIX_SECONDS
        ):
            raise InvalidCodexRateLimitsSourceV1("codex_source_reset_invalid")


@dataclass(frozen=True, slots=True)
class CodexRateLimitBucketSourceV1(TechnicalValueV1):
    """Closed fields from one keyed `RateLimitSnapshot`."""

    OWNER: ClassVar[str] = "PLAN-A02"

    limit_id: str
    safe_label: str | None
    plan_type: CodexPlanTypeV1 | None
    rate_limit_reached_type: CodexRateLimitReachedTypeV1 | None
    primary: CodexRateLimitWindowSourceV1
    secondary: CodexRateLimitWindowSourceV1 | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if type(self.limit_id) is not str or _LIMIT_ID.fullmatch(self.limit_id) is None:
            raise InvalidCodexRateLimitsSourceV1("codex_source_limit_id_invalid")
        if not _valid_label(self.safe_label):
            raise InvalidCodexRateLimitsSourceV1("codex_source_label_invalid")
        if self.plan_type is not None and self.plan_type not in _PLAN_TYPES:
            raise InvalidCodexRateLimitsSourceV1("codex_source_plan_type_invalid")
        if (
            self.rate_limit_reached_type is not None
            and self.rate_limit_reached_type not in _REACHED_TYPES
        ):
            raise InvalidCodexRateLimitsSourceV1("codex_source_reached_type_invalid")
        if not isinstance(self.primary, CodexRateLimitWindowSourceV1):
            raise InvalidCodexRateLimitsSourceV1("codex_source_primary_window_invalid")
        if self.secondary is not None and not isinstance(
            self.secondary, CodexRateLimitWindowSourceV1
        ):
            raise InvalidCodexRateLimitsSourceV1(
                "codex_source_secondary_window_invalid"
            )


@dataclass(frozen=True, slots=True)
class CodexRateLimitsSourceV1(TechnicalValueV1):
    """Subscription-only source result, with all excluded fields discarded."""

    OWNER: ClassVar[str] = "PLAN-A02"

    ordinary_usage_allowed: bool | None
    buckets: tuple[CodexRateLimitBucketSourceV1, ...]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            self.ordinary_usage_allowed is not None
            and type(self.ordinary_usage_allowed) is not bool
        ):
            raise InvalidCodexRateLimitsSourceV1(
                "codex_source_usage_permission_invalid"
            )
        if not 1 <= len(self.buckets) <= 32 or not all(
            isinstance(item, CodexRateLimitBucketSourceV1) for item in self.buckets
        ):
            raise InvalidCodexRateLimitsSourceV1("codex_source_bucket_set_invalid")
        limit_ids = tuple(item.limit_id for item in self.buckets)
        if len(limit_ids) != len(set(limit_ids)):
            raise InvalidCodexRateLimitsSourceV1("codex_source_limit_id_duplicate")
