"""Bounded local event construction for CTR-FND-004 V1; no sink or handlers.

Only technical event codes and opaque internal identifiers are accepted. Sink
paths, rotation and retention remain M08/DEP responsibilities. This module never
formats an exception, payload, header, path or arbitrary string message.
"""

import re
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Literal

from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.foundation_v1 import CorrelationContextAndSafeLogEventV1

SafeLogEventV1 = CorrelationContextAndSafeLogEventV1
_IDENTIFIER = re.compile(r"[a-f0-9]{32}")
_VERSION = re.compile(r"[0-9]{1,5}\.[0-9]{1,5}\.[0-9]{1,5}")


class UnsafeLogFieldError(ValueError):
    """Arguments contain only a stable local classification code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.__suppress_context__ = True


class SafeLogCodeV1(Enum):
    BOOTSTRAP_ACCEPTED = "bootstrap.accepted"
    BOOTSTRAP_REJECTED = "bootstrap.rejected"
    OPERATION_FAILED = "operation.failed"


class SafeLogComponentV1(Enum):
    FOUNDATION = "foundation"


def _new_id() -> OpaqueIdV1:
    return OpaqueIdV1(value=secrets.token_hex(16))


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _validate_id(value: OpaqueIdV1, code: str) -> None:
    if (
        type(value) is not OpaqueIdV1
        or type(value.value) is not str
        or not _IDENTIFIER.fullmatch(value.value)
    ):
        raise UnsafeLogFieldError(code)


@dataclass(frozen=True, slots=True)
class CorrelationContextV1:
    """32 lowercase hex IDs; callers own request replacement/propagation policy."""

    correlation_id: OpaqueIdV1 = field(default_factory=_new_id)
    causation_id: OpaqueIdV1 | None = None
    occurred_at: datetime = field(default_factory=_utc_now)
    component: SafeLogComponentV1 = SafeLogComponentV1.FOUNDATION
    component_version: str = "1.0.0"

    def __post_init__(self) -> None:
        _validate_id(self.correlation_id, "invalid_correlation_id")
        if self.causation_id is not None:
            _validate_id(self.causation_id, "invalid_causation_id")
        if type(
            self.occurred_at
        ) is not datetime or self.occurred_at.utcoffset() != timedelta(0):
            raise UnsafeLogFieldError("invalid_event_timestamp")
        # A zero-offset timezone may still carry an arbitrary, sensitive label.
        object.__setattr__(self, "occurred_at", self.occurred_at.astimezone(UTC))
        if type(self.component) is not SafeLogComponentV1:
            raise UnsafeLogFieldError("invalid_component")
        if type(self.component_version) is not str or not _VERSION.fullmatch(
            self.component_version
        ):
            raise UnsafeLogFieldError("invalid_component_version")


@dataclass(frozen=True, slots=True)
class SafeLogFieldV1:
    """The only optional V1 field is an opaque subject ID (at most eight/event)."""

    name: Literal["subject_id"]
    value: OpaqueIdV1

    def __post_init__(self) -> None:
        if self.name != "subject_id":
            raise UnsafeLogFieldError("unsafe_log_field")
        _validate_id(self.value, "invalid_subject_id")


def build_safe_log_event(
    context: CorrelationContextV1,
    code: SafeLogCodeV1,
    fields: tuple[SafeLogFieldV1, ...],
) -> SafeLogEventV1:
    """Construct an immutable contract event; no arbitrary payload or I/O."""
    if type(context) is not CorrelationContextV1:
        raise UnsafeLogFieldError("invalid_correlation_context")
    if type(code) is not SafeLogCodeV1:
        raise UnsafeLogFieldError("invalid_log_code")
    if type(fields) is not tuple or len(fields) > 8:
        raise UnsafeLogFieldError("unsafe_log_fields")
    for item in fields:
        if type(item) is not SafeLogFieldV1:
            raise UnsafeLogFieldError("unsafe_log_field")
    severity: Literal["info", "error"] = (
        "info" if code is SafeLogCodeV1.BOOTSTRAP_ACCEPTED else "error"
    )
    outcome = {
        SafeLogCodeV1.BOOTSTRAP_ACCEPTED: "accepted",
        SafeLogCodeV1.BOOTSTRAP_REJECTED: "rejected",
        SafeLogCodeV1.OPERATION_FAILED: "failed",
    }[code]
    return CorrelationContextAndSafeLogEventV1(
        occurred_at=context.occurred_at,
        severity=severity,
        component=context.component.value,
        event_name=code.value,
        component_version=context.component_version,
        correlation_id=context.correlation_id,
        causation_id=context.causation_id,
        outcome_code=outcome,
        subject_ids=tuple(item.value for item in fields),
    )
