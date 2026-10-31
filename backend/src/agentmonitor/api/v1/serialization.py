"""P01 mapping of closed technical contracts into validated wire records."""

from dataclasses import fields
from datetime import datetime

from agentmonitor.contracts.common_quantity_v1 import ExactQuantityV1
from agentmonitor.contracts.common_v1 import (
    FieldAvailabilityV1,
    OpaqueIdV1,
    TechnicalValueV1,
)


def technical_wire(value: object) -> object:
    if isinstance(value, OpaqueIdV1):
        return value.value
    if isinstance(value, FieldAvailabilityV1):
        return value.state
    if isinstance(value, ExactQuantityV1):
        return {
            "coefficient": value.amount.coefficient,
            "scale": value.amount.scale,
            "unit": value.unit,
        }
    if isinstance(value, TechnicalValueV1):
        return {
            item.name: technical_wire(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, tuple):
        return tuple(technical_wire(item) for item in value)
    if value is None or isinstance(value, (str, int, bool, datetime)):
        return value
    raise ValueError("wire_value_not_admitted")
