"""Internal pure signals; these records do not establish producer truth."""

from dataclasses import dataclass
from typing import Literal

from agentmonitor.contracts.alerting_v1 import (
    AlertConditionTypeV1,
    AlertDecisionSummaryV1,
    AlertSeverityV1,
    AlertSubjectV1,
    AlertValueV1,
)


@dataclass(frozen=True, slots=True)
class NormalizedAlertSignalV1(AlertValueV1):
    """Internal pure input only; no API/producer event injection contract."""

    condition_type: AlertConditionTypeV1
    subject: AlertSubjectV1
    transition: Literal["active", "recovered", "not_evaluable"]
    severity: AlertSeverityV1 | None
    decision: AlertDecisionSummaryV1
    condition_semantic_major: Literal[1]

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        if (self.transition == "active") != (self.severity in ("warning", "critical")):
            raise ValueError("alert_normalized_signal_invalid")
        if self.transition != "active" and self.severity is not None:
            raise ValueError("alert_normalized_signal_invalid")
