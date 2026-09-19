"""Foundation-owned, I/O-free V1 technical values; no provider semantics."""

from dataclasses import dataclass, fields
from datetime import datetime, timedelta
from decimal import Decimal
from typing import ClassVar, Literal, get_args, get_origin, get_type_hints


@dataclass(frozen=True, slots=True)
class TechnicalValueV1:
    """Closed immutable record base, rejecting mutable nested containers.

    Type checking governs field types. Runtime construction additionally rejects
    mutable payloads, non-finite quantities, floats and non-UTC timestamps.
    This is not an external-data parser or a secret-bearing value container.
    """

    CONTRACT_VERSION: ClassVar[str] = "1.0.0"
    OWNER: ClassVar[str] = "PLAN-FND"

    def __post_init__(self) -> None:
        def validate(value: object) -> None:
            if value is None or type(value) in (str, int, bool):
                return
            if isinstance(value, TechnicalValueV1):
                return
            if isinstance(value, tuple):
                for item in value:
                    validate(item)
                return
            if isinstance(value, datetime):
                if value.utcoffset() != timedelta(0):
                    raise ValueError("timestamp-must-be-aware-utc")
                return
            if isinstance(value, Decimal):
                if not value.is_finite():
                    raise ValueError("quantity-must-be-finite")
                return
            raise TypeError("immutable-technical-value-required")

        annotations = get_type_hints(type(self))
        for field in fields(self):
            value = getattr(self, field.name)
            validate(value)
            annotation = annotations[field.name]
            if get_origin(annotation) is Literal and value not in get_args(annotation):
                raise ValueError("unsupported-field-state")


@dataclass(frozen=True, slots=True)
class OpaqueIdV1(TechnicalValueV1):
    """Opaque identity; generation and uniqueness belong to the producing owner."""

    CONTRACT_ID: ClassVar[str] = "CTR-COMMON-001"
    value: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("opaque-id-required")


@dataclass(frozen=True, slots=True)
class TimestampAndDurationV1(TechnicalValueV1):
    """Aware UTC instant and nonnegative elapsed integer milliseconds."""

    CONTRACT_ID: ClassVar[str] = "CTR-COMMON-002"
    timestamp: datetime
    duration_ms: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not isinstance(self.timestamp, datetime):
            raise TypeError("timestamp-required")
        if type(self.duration_ms) is not int or self.duration_ms < 0:
            raise ValueError("nonnegative-integer-duration-required")


@dataclass(frozen=True, slots=True)
class ExactQuantityV1(TechnicalValueV1):
    """Exact decimal and explicit native unit; currency uses its currency code."""

    CONTRACT_ID: ClassVar[str] = "CTR-COMMON-003"
    value: Decimal
    unit: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not isinstance(self.value, Decimal) or not self.unit:
            raise ValueError("exact-decimal-and-unit-required")


@dataclass(frozen=True, slots=True)
class EventEnvelopeV1(TechnicalValueV1):
    """Technical envelope; producers compose this with their typed payload.

    CTR-EVT-001 owns delivery, stream sequence, outbox, receipts and replay.
    No arbitrary dictionary or raw provider payload is carried here.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-COMMON-006"
    event_id: OpaqueIdV1
    event_type: str
    occurred_at: datetime
    recorded_at: datetime
    producer: str
    producer_version: str
    correlation_id: OpaqueIdV1
    causation_id: OpaqueIdV1 | None
    subject_id: OpaqueIdV1


AvailabilityStateV1 = Literal[
    "available",
    "missing",
    "null",
    "unknown",
    "unsupported",
    "unavailable",
    "not_applicable",
    "withheld_or_denied",
    "stale",
    "unresolved",
]


@dataclass(frozen=True, slots=True)
class FieldAvailabilityV1(TechnicalValueV1):
    """Availability accompanies a separately typed value; exact zero is available."""

    CONTRACT_ID: ClassVar[str] = "CTR-COMMON-007"
    state: AvailabilityStateV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if self.state not in (
            "available",
            "missing",
            "null",
            "unknown",
            "unsupported",
            "unavailable",
            "not_applicable",
            "withheld_or_denied",
            "stale",
            "unresolved",
        ):
            raise ValueError("unsupported-availability-state")
