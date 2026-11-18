"""Pure A02 admission for finite completed 7/30-day cost and usage views."""

import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal
from urllib.parse import urlencode

from agentmonitor.adapters.providers.codex.openai_api.usage_mapping import (
    GROUP_FIELDS,
    USAGE_MAPPINGS,
    UsageCategoryV1,
    usage_mapping,
    validate_grouping,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetDimensionKindV1,
    BudgetPeriodV1,
    CapacitySubjectV2,
)
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1, ExactMoneyV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1

HOST = "api.openai.com"
PATH = "/v1/organization/costs"
SOURCE_ID = "openai.organization.costs.v1"
USAGE_SOURCE_ID = "openai.organization.usage.v1"
COST_BASIS = "openai_reported_cost"
MAX_REQUESTS = 20
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_NORMALIZED_BYTES = 16 * 1024 * 1024
MAX_ROWS = 10000
REPORT_SECONDS = 120
REQUEST_SECONDS = 10
_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]{1,3})?\Z")

ANALYTICS_REPORT_SELECTIONS: tuple[
    tuple[str, tuple[BudgetDimensionKindV1, ...]], ...
] = (
    (
        ("cost", ()),
        ("cost", ("project",)),
        ("cost", ("api_key_id",)),
    )
    + tuple(
        ("usage_" + category, grouping)
        for category, mapping in USAGE_MAPPINGS.items()
        for grouping in ((), *((dimension,) for dimension in mapping.groupings))
    )
    + tuple(
        ("usage_" + category + "_tokens", ("token_category",))
        for category, mapping in USAGE_MAPPINGS.items()
        if mapping.token_fields
    )
)


def analytics_selection_is_usage(category: str, grouping: tuple[str, ...]) -> bool:
    """Admit only reviewed single-dimension views before selecting a source."""
    if (category, grouping) not in ANALYTICS_REPORT_SELECTIONS:
        raise ValueError("openai_analytics_selection_invalid")
    return category != "cost"


def completed_period(instant: datetime, days: int) -> BudgetPeriodV1:
    """A fixed completed-UTC interval, never partial today or arbitrary history."""
    if (
        not isinstance(instant, datetime)
        or instant.utcoffset() != timedelta(0)
        or type(days) is not int
        or days not in {7, 30}
    ):
        raise ValueError("openai_cost_period_invalid")
    end = instant.replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)
    if start < datetime(1970, 1, 1, tzinfo=UTC):
        raise ValueError("openai_cost_period_invalid")
    return BudgetPeriodV1(start, end)


def validate_period(period: BudgetPeriodV1, requested_at: datetime) -> None:
    """Admit captured completed 7/30-day coverage without changing request time."""
    if (
        not isinstance(period, BudgetPeriodV1)
        or not isinstance(requested_at, datetime)
        or requested_at.utcoffset() != timedelta(0)
        or any(
            value.utcoffset() != timedelta(0)
            or value.hour
            or value.minute
            or value.second
            or value.microsecond
            for value in (period.start, period.end)
        )
        or period.end - period.start not in (timedelta(days=7), timedelta(days=30))
        or period.start < datetime(1970, 1, 1, tzinfo=UTC)
        or period.end > requested_at
    ):
        raise ValueError("openai_cost_request_invalid")


@dataclass(frozen=True, slots=True)
class OpenAICostRequestV1(TechnicalValueV1):
    """Captured local authority; scope labels do not prove provider identity."""

    subject: CapacitySubjectV2
    binding: ActiveCredentialBindingRefV1
    scope_id: OpaqueIdV1 | None
    scope_evidence: Literal["provider_verified", "owner_asserted", "unresolved"]
    scope_generation: int
    period: BudgetPeriodV1
    requested_at: datetime
    grouping: tuple[BudgetDimensionKindV1, ...] = ()

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not isinstance(self.subject, CapacitySubjectV2)
            or self.subject.provider_key != "codex"
            or self.subject.provider_target.target_kind != "cloud_service"
            or not isinstance(self.binding, ActiveCredentialBindingRefV1)
            or self.binding.account_id != self.subject.account_id
            or type(self.scope_generation) is not int
            or self.scope_generation < 1
            or (self.scope_evidence == "unresolved") != (self.scope_id is None)
            or self.scope_id is not None
            and not isinstance(self.scope_id, OpaqueIdV1)
        ):
            raise ValueError("openai_cost_request_invalid")
        validate_period(self.period, self.requested_at)
        self._validate_grouping()

    def _validate_grouping(self) -> None:
        validate_grouping(self.grouping, ("project", "api_key_id"))


@dataclass(frozen=True, slots=True, kw_only=True)
class OpenAIUsageRequestV1(OpenAICostRequestV1):
    """Exactly one admitted endpoint, interval and optional single dimension."""

    category: UsageCategoryV1

    def _validate_grouping(self) -> None:
        mapping = usage_mapping(self.category)
        supported = mapping.groupings + (
            ("token_category",) if mapping.token_fields else ()
        )
        validate_grouping(self.grouping, supported)


def request_path(request: OpenAICostRequestV1, cursor: str | None) -> str:
    """Fixed origin/path; opaque cursors can only become encoded query values."""
    if cursor is not None and (
        type(cursor) is not str
        or not 1 <= len(cursor) <= 1024
        or any(ord(char) < 0x21 or ord(char) > 0x7E for char in cursor)
    ):
        raise ValueError("openai_cost_cursor_invalid")
    parameters = {
        "start_time": str(int(request.period.start.timestamp())),
        "end_time": str(int(request.period.end.timestamp())),
        "bucket_width": "1d",
        "limit": str((request.period.end - request.period.start).days),
    }
    if cursor is not None:
        parameters["page"] = cursor
    if request.grouping and request.grouping != ("token_category",):
        # Match OpenAI's REST array encoding even for one selected dimension.
        parameters["group_by[]"] = GROUP_FIELDS[request.grouping[0]]
    path = (
        "/v1/organization/usage/" + request.category
        if isinstance(request, OpenAIUsageRequestV1)
        else PATH
    )
    return path + "?" + urlencode(parameters)


def decimal_number(value: str) -> Decimal:
    """Decode a bounded JSON numeric lexeme without binary floating point."""
    if type(value) is not str or len(value) > 128 or _NUMBER.fullmatch(value) is None:
        raise ValueError("openai_cost_amount_invalid")
    return Decimal(value)


def money_from_number(value: object, currency: object) -> ExactMoneyV1:
    """Preserve provider units and currency; never default, scale or round them."""
    if (
        type(value) not in {Decimal, int}
        or type(currency) is not str
        or re.fullmatch(r"[a-z]{3}", currency) is None
    ):
        raise ValueError("openai_cost_amount_invalid")
    if isinstance(value, Decimal):
        amount = value
    else:
        assert isinstance(value, int)
        amount = Decimal(value)
    return ExactMoneyV1(CanonicalDecimalV1.from_decimal(amount), currency.upper())


def bounded_deadline(now: float, supplied: float | None, budget_seconds: int) -> float:
    """Clamp an absolute monotonic deadline to the admitted operation budget."""
    if (
        type(now) is not float
        or not math.isfinite(now)
        or type(budget_seconds) is not int
        or not 1 <= budget_seconds <= REPORT_SECONDS
        or supplied is not None
        and (type(supplied) is not float or not math.isfinite(supplied))
    ):
        raise TimeoutError("openai_cost_deadline_invalid")
    result = min(
        now + budget_seconds, supplied if supplied is not None else now + budget_seconds
    )
    if not math.isfinite(result) or result <= now:
        raise TimeoutError("openai_cost_deadline_exceeded")
    return result
