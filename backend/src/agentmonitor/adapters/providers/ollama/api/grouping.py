"""Pure exact partitions of typed Ollama model metrics; no provider I/O."""

from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

from agentmonitor.contracts.capacity_v1 import BudgetDimensionV1
from agentmonitor.contracts.common_quantity_v1 import ExactMoneyV1, ExactQuantityV1

MoneyAvailability = Literal["available", "not_reported", "partial"]


@dataclass(frozen=True, slots=True)
class UsageMetrics:
    quantities: tuple[ExactQuantityV1, ...]
    money: ExactMoneyV1 | None

    def __post_init__(self) -> None:
        units = tuple(q.unit for q in self.quantities)
        if (
            type(self.quantities) is not tuple
            or len(set(units)) != len(units)
            or "requests" not in units
            or any(
                q.unit
                not in {
                    "requests",
                    "input_tokens",
                    "cached_input_tokens",
                    "output_tokens",
                }
                or q.amount.scale != 0
                or int(q.amount.coefficient) < 0
                for q in self.quantities
            )
            or self.money is not None
            and self.money.currency != "USD"
        ):
            raise ValueError("ollama_usage_metrics_invalid")


@dataclass(frozen=True, slots=True)
class ModelUsage:
    dimension: BudgetDimensionV1
    metrics: UsageMetrics


@dataclass(frozen=True, slots=True)
class ModelPartition:
    components: tuple[ModelUsage, ...]
    money_availability: MoneyAvailability


def _quantities(metrics: UsageMetrics) -> dict[str, int]:
    return {q.unit: int(q.amount.coefficient) for q in metrics.quantities}


def _money(money: ExactMoneyV1) -> Fraction:
    return Fraction(int(money.amount.coefficient), 10**money.amount.scale)


def reconcile_model_usage(
    total: UsageMetrics, groups: tuple[ModelUsage, ...], remainder: ModelUsage | None
) -> ModelPartition:
    """Validate the reported partition without synthesizing missing components.

    Optional measures remain absent. A parent and fully reported children must
    reconcile exactly; incomplete monetary partitions cannot become spend.
    """
    if type(groups) is not tuple or len(groups) > 10:
        raise ValueError("ollama_usage_groups_invalid")
    names = tuple(g.dimension.value for g in groups)
    if (
        len(set(names)) != len(names)
        or any(
            g.dimension.kind != "model"
            or g.dimension.value is None
            or g.dimension.is_remainder
            for g in groups
        )
        or remainder is not None
        and (
            remainder.dimension.kind != "model"
            or remainder.dimension.value is not None
            or not remainder.dimension.is_remainder
        )
    ):
        raise ValueError("ollama_usage_groups_invalid")
    components = groups + (() if remainder is None else (remainder,))
    parts = tuple(_quantities(component.metrics) for component in components)
    if any(part["requests"] <= 0 for part in parts):
        raise ValueError("ollama_usage_groups_invalid")
    for unit, count in _quantities(total).items():
        if (
            all(unit in part for part in parts)
            and sum(part[unit] for part in parts) != count
        ):
            raise ValueError("ollama_usage_partition_invalid")
    amounts = tuple(part.metrics.money for part in components)
    if total.money is not None and all(amount is not None for amount in amounts):
        if sum(
            (_money(amount) for amount in amounts if amount is not None), Fraction()
        ) != _money(total.money):
            raise ValueError("ollama_usage_partition_invalid")
        state: MoneyAvailability = "available"
    elif total.money is None and all(amount is None for amount in amounts):
        state = "not_reported"
    else:
        state = "partial"
    return ModelPartition(components, state)


def validate_model_selection(
    selection: tuple[str, ...], bucket: tuple[str, ...]
) -> None:
    """Per-day groups are an ordered subset of the source's range-wide choice."""
    if (
        len(selection) > 10
        or len(set(selection)) != len(selection)
        or len(set(bucket)) != len(bucket)
    ):
        raise ValueError("ollama_usage_model_selection_invalid")
    included = frozenset(bucket)
    if tuple(name for name in selection if name in included) != bucket:
        raise ValueError("ollama_usage_model_selection_invalid")


def report_money_availability(
    states: tuple[MoneyAvailability, ...], *, has_costs: bool
) -> MoneyAvailability:
    """Reported empty partitions do not create retained monetary zero facts."""
    if (
        not states
        or type(has_costs) is not bool
        or any(
            state not in {"available", "not_reported", "partial"} for state in states
        )
    ):
        raise ValueError("ollama_usage_money_coverage_invalid")
    if all(state == "available" for state in states):
        return "available" if has_costs else "not_reported"
    if all(state == "not_reported" for state in states):
        return "not_reported"
    return "partial"
