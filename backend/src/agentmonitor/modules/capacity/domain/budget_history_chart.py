"""Exact, stable chart geometry; source entries never imply disjoint totals."""

import hashlib
import json
from dataclasses import replace
from datetime import timedelta

from agentmonitor.contracts.budget_query_v1 import (
    BudgetHistoryChartPointV1,
    BudgetHistoryRowV1,
)
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1


def _series(row: BudgetHistoryRowV1) -> tuple[str, str, CanonicalDecimalV1]:
    if row.cost is not None:
        bucket = row.cost
        unit = bucket.amount.currency
        amount = bucket.amount.amount
        dimensions = bucket.dimensions
    else:
        assert row.usage is not None
        unit = row.usage.quantity.unit
        amount = row.usage.quantity.amount
        dimensions = row.usage.dimensions
    identity = (row.kind, unit, tuple((d.kind, d.value) for d in dimensions))
    key = hashlib.sha256(
        json.dumps(identity, separators=(",", ":")).encode()
    ).hexdigest()
    label = " · ".join(
        (
            "Cost" if row.kind == "cost" else "Usage",
            unit,
            *(
                f"{d.kind}: {d.value if d.value is not None else 'Not reported'}"
                for d in dimensions
            ),
        )
    )
    return key, label, amount


def chart_rows(rows: tuple[BudgetHistoryRowV1, ...]) -> tuple[BudgetHistoryRowV1, ...]:
    """Use the full pinned report's peak; ceil visual resolution to one basis point.

    Monetary facts are never rounded or aggregated here. Zero stays zero; tiny
    nonzero entries retain a visible nonzero magnitude and their exact label.
    """
    metadata: list[tuple[str, str, int] | None] = []
    maxima: dict[str, int] = {}
    for row in rows:
        bucket = row.cost or row.usage
        assert bucket is not None
        start = bucket.period.start
        if (
            start.utcoffset() != timedelta(0)
            or any((start.hour, start.minute, start.second, start.microsecond))
            or bucket.period.end - start != timedelta(days=1)
        ):
            metadata.append(None)
            continue
        key, label, value = _series(row)
        signed = int(value.coefficient) * 10 ** (18 - value.scale)
        metadata.append((key, label, signed))
        maxima[key] = max(maxima.get(key, 0), abs(signed))
    result = []
    for row, item in zip(rows, metadata, strict=True):
        if item is None:
            result.append(
                replace(
                    row,
                    chart=None,
                    chart_unavailable_reason="source_interval_not_daily",
                )
            )
            continue
        key, label, signed = item
        maximum = maxima[key]
        magnitude = (abs(signed) * 10000 + maximum - 1) // maximum if maximum else 0
        point = BudgetHistoryChartPointV1(
            key,
            label,
            magnitude,
            "zero" if signed == 0 else "negative" if signed < 0 else "positive",
        )
        result.append(replace(row, chart=point, chart_unavailable_reason=None))
    return tuple(result)
