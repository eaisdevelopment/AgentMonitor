"""Pure, closed Ollama cloud balance contract and M05 window projection.

This module has no I/O and does not parse or retain provider payloads.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, localcontext
from typing import ClassVar

from agentmonitor.contracts.capacity_v1 import ExactMetricFieldV1, ProviderQuotaWindowInputV1
from agentmonitor.contracts.common_quantity_v1 import ExactQuantityV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, TechnicalValueV1


def _amount(value: Decimal | None, *, percent: bool = False) -> None:
    if value is not None:
        if type(value) is not Decimal or not value.is_finite() or value < 0:
            raise ValueError('ollama_balance_amount_invalid')
        if percent and value > 100:
            raise ValueError('ollama_balance_percent_invalid')
        # Require all accepted quantities to be representable in the M05 contract.
        ExactQuantityV1.from_decimal(value, unit='percent' if percent else 'usd')


@dataclass(frozen=True, slots=True)
class SourcePeriodV1(TechnicalValueV1):
    """Source period: start inclusive, end exclusive, independently unknown.

    Ollama documents these UTC boundary semantics at
    https://docs.ollama.com/api/balance.
    """

    CONTRACT_ID: ClassVar[str] = 'OLLAMA-CLOUD-BALANCE-V1'
    OWNER: ClassVar[str] = 'PLAN-A03'
    start: datetime | None
    end: datetime | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if any(value is not None and type(value) is not datetime
               for value in (self.start, self.end)):
            raise ValueError('ollama_balance_period_invalid')
        if self.start is not None and self.end is not None and self.start >= self.end:
            raise ValueError('ollama_balance_period_invalid')


@dataclass(frozen=True, slots=True)
class IncludedCreditsV1(TechnicalValueV1):
    balance_usd: Decimal | None
    allowance_usd: Decimal | None
    period: SourcePeriodV1 | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _amount(self.balance_usd)
        _amount(self.allowance_usd)
        if self.period is not None and not isinstance(self.period, SourcePeriodV1):
            raise ValueError('ollama_balance_period_invalid')


@dataclass(frozen=True, slots=True)
class LegacyWindowV1(TechnicalValueV1):
    remaining_percent: Decimal | None
    resets_at: datetime | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _amount(self.remaining_percent, percent=True)
        if self.resets_at is not None and type(self.resets_at) is not datetime:
            raise ValueError('ollama_balance_reset_invalid')
        if self.remaining_percent is not None:
            with localcontext() as context:
                context.prec = 100
                ExactQuantityV1.from_decimal(self.remaining_percent / 100, unit='ratio')


@dataclass(frozen=True, slots=True)
class LegacyLimitsV1(TechnicalValueV1):
    session: LegacyWindowV1 | None
    weekly: LegacyWindowV1 | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if any(value is not None and not isinstance(value, LegacyWindowV1)
               for value in (self.session, self.weekly)):
            raise ValueError('ollama_balance_window_invalid')


@dataclass(frozen=True, slots=True)
class OllamaCloudBalanceV1(TechnicalValueV1):
    """Typed safe source observation; None means unknown, never zero."""

    CONTRACT_ID: ClassVar[str] = 'OLLAMA-CLOUD-BALANCE-V1'
    OWNER: ClassVar[str] = 'PLAN-A03'
    included: IncludedCreditsV1 | LegacyLimitsV1 | None
    purchased_usd: Decimal | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if self.included is not None and not isinstance(
            self.included, (IncludedCreditsV1, LegacyLimitsV1)
        ):
            raise ValueError('ollama_balance_included_invalid')
        _amount(self.purchased_usd)


@dataclass(frozen=True, slots=True)
class BalanceProjectionV1(TechnicalValueV1):
    """Period is separate because CTR-CAP-001 windows lack a period start."""

    windows: tuple[ProviderQuotaWindowInputV1, ...]
    period: SourcePeriodV1 | None


def _field(value: Decimal | None, unit: str, *, derived: bool = False) -> ExactMetricFieldV1:
    if value is None:
        return ExactMetricFieldV1(FieldAvailabilityV1('unknown'), None, 'unknown',
                                  'unknown', 'unknown', 'source_value_unknown')
    return ExactMetricFieldV1(FieldAvailabilityV1('available'),
                              ExactQuantityV1.from_decimal(value, unit=unit),
                              'exact', 'confirmed',
                              'derived' if derived else 'provider_reported', None)


def _window(key: str, label: str, remaining: Decimal | None, limit: Decimal | None,
            ratio: Decimal | None, reset: datetime | None, *, derived: bool = False,
            constraining: bool = False
            ) -> ProviderQuotaWindowInputV1:
    return ProviderQuotaWindowInputV1(
        window_key=key, safe_label=label, semantic_role='capacity', is_constraining=constraining,
        used=_field(None, 'usd'), remaining=_field(remaining, 'usd'),
        limit=_field(limit, 'usd'), remaining_ratio=_field(ratio, 'ratio', derived=derived),
        reset_at=reset, reset_precision='exact' if reset is not None else 'unknown',
    )


def _included_ratio(balance: Decimal | None, allowance: Decimal | None) -> Decimal | None:
    if balance is None or allowance is None or allowance <= 0 or balance > allowance:
        return None
    with localcontext() as context:
        context.prec = 100
        value = balance / allowance
        if value * allowance != balance:
            return None
        try:
            ExactQuantityV1.from_decimal(value, unit='ratio')
        except ValueError:
            return None
        return value


def to_capacity_windows(balance: OllamaCloudBalanceV1) -> BalanceProjectionV1:
    """Project amounts without losing source period at this module boundary."""
    # Monetary pools are not independent constraints: either can be empty
    # while the other still has funds. Do not infer aggregate exhaustion.
    windows: list[ProviderQuotaWindowInputV1] = []
    period = None
    if isinstance(balance.included, IncludedCreditsV1):
        included = balance.included
        period = included.period
        windows.append(_window('ollama_included_credits', 'Included credits',
            included.balance_usd, included.allowance_usd,
            _included_ratio(included.balance_usd, included.allowance_usd),
            period.end if period else None, derived=True))
    elif isinstance(balance.included, LegacyLimitsV1):
        for name, label, item in (('session', 'Session', balance.included.session),
                                  ('weekly', 'Weekly', balance.included.weekly)):
            if item is not None:
                with localcontext() as context:
                    context.prec = 100
                    ratio = item.remaining_percent / 100 if item.remaining_percent is not None else None
                windows.append(_window('ollama_' + name, label, None, None, ratio, item.resets_at, constraining=True))
    windows.append(_window('ollama_purchased_credits', 'Purchased credits',
                           balance.purchased_usd, None, None, None))
    return BalanceProjectionV1(tuple(windows), period)
