"""Pure A01 admission and units for one ungrouped completed-week cost report."""

import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal
from urllib.parse import urlencode

from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1, CapacitySubjectV2
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1, ExactMoneyV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1

HOST = "api.anthropic.com"
PATH = "/v1/organizations/analytics/cost"
API_VERSION = "2026-10-21"
BETA_VERSION = "analytics-usage-cost-2026-08-24"
SOURCE_ID = "anthropic.analytics.cost.v1"
COST_BASIS = "discounted_before_credits"
MAX_REQUESTS = 20
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_NORMALIZED_BYTES = 16 * 1024 * 1024
MAX_ROWS = 10000
REPORT_SECONDS = 120
REQUEST_SECONDS = 10
_CENTS = re.compile(r"-?(?:0|[1-9][0-9]{0,69})\.[0-9]{6}\Z")


def completed_week(instant: datetime) -> BudgetPeriodV1:
    """Last seven completed UTC days; never include a provider partial today."""
    if not isinstance(instant, datetime) or instant.utcoffset() != timedelta(0):
        raise ValueError("anthropic_cost_request_time_invalid")
    end = instant.replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=7)
    if start < datetime(2026, 1, 1, tzinfo=UTC):
        raise ValueError("anthropic_cost_history_unavailable")
    return BudgetPeriodV1(start, end)


@dataclass(frozen=True, slots=True)
class AnthropicCostRequestV1(TechnicalValueV1):
    """Captured local authority; scope labels do not prove provider identity."""

    subject: CapacitySubjectV2
    binding: ActiveCredentialBindingRefV1
    scope_id: OpaqueIdV1 | None
    scope_evidence: Literal["provider_verified", "owner_asserted", "unresolved"]
    scope_generation: int
    period: BudgetPeriodV1
    requested_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not isinstance(self.subject, CapacitySubjectV2)
            or self.subject.provider_key != "claude"
            or self.subject.provider_target.target_kind != "cloud_service"
            or not isinstance(self.binding, ActiveCredentialBindingRefV1)
            or self.binding.account_id != self.subject.account_id
            or type(self.scope_generation) is not int
            or self.scope_generation < 1
            or (self.scope_evidence == "unresolved") != (self.scope_id is None)
            or self.scope_id is not None
            and not isinstance(self.scope_id, OpaqueIdV1)
            or self.period != completed_week(self.requested_at)
        ):
            raise ValueError("anthropic_cost_request_invalid")


def request_path(request: AnthropicCostRequestV1, cursor: str | None) -> str:
    """Fixed origin/path; opaque cursors can only become encoded query values."""
    if cursor is not None and (
        type(cursor) is not str
        or not 1 <= len(cursor) <= 1024
        or any(ord(char) < 0x21 or ord(char) > 0x7E for char in cursor)
    ):
        raise ValueError("anthropic_cost_cursor_invalid")
    parameters = {
        "starting_at": request.period.start.isoformat().replace("+00:00", "Z"),
        "ending_at": request.period.end.isoformat().replace("+00:00", "Z"),
        "time_bucket_width": "1d",
        "order_by": "time",
        "order": "asc",
        "limit": "1000",
    }
    if cursor is not None:
        parameters["page"] = cursor
    return PATH + "?" + urlencode(parameters)


def cents_to_usd(value: str) -> ExactMoneyV1:
    """Convert six-place decimal cents without context-sensitive arithmetic."""
    if type(value) is not str or _CENTS.fullmatch(value) is None:
        raise ValueError("anthropic_cost_amount_invalid")
    # Parsing a decimal string with an exponent is exact even under a tiny context.
    return ExactMoneyV1(CanonicalDecimalV1.from_decimal(Decimal(value + "e-2")), "USD")


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
        raise TimeoutError("anthropic_cost_deadline_invalid")
    result = min(
        now + budget_seconds, supplied if supplied is not None else now + budget_seconds
    )
    if not math.isfinite(result) or result <= now:
        raise TimeoutError("anthropic_cost_deadline_exceeded")
    return result
