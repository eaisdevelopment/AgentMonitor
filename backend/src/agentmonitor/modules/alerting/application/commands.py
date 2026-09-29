"""M07 alert user commands over owned atomic persistence only."""

from agentmonitor.contracts.alerting_v1 import (
    AcknowledgeAlertCommandV1,
    AlertCommandResultV1,
    MarkAlertReadCommandV1,
    SnoozeAlertCommandV1,
    UnsnoozeAlertCommandV1,
)
from agentmonitor.modules.alerting.application.ports import AlertActionRepositoryV1


class AcknowledgeAlertV1:
    def __init__(self, repository: AlertActionRepositoryV1) -> None:
        self._repository = repository

    def __call__(self, command: AcknowledgeAlertCommandV1) -> AlertCommandResultV1:
        return self._repository.apply_alert_command(command)


class SnoozeAlertV1:
    def __init__(self, repository: AlertActionRepositoryV1) -> None:
        self._repository = repository

    def __call__(self, command: SnoozeAlertCommandV1) -> AlertCommandResultV1:
        return self._repository.apply_alert_command(command)


class UnsnoozeAlertV1:
    def __init__(self, repository: AlertActionRepositoryV1) -> None:
        self._repository = repository

    def __call__(self, command: UnsnoozeAlertCommandV1) -> AlertCommandResultV1:
        return self._repository.apply_alert_command(command)


class MarkAlertReadV1:
    def __init__(self, repository: AlertActionRepositoryV1) -> None:
        self._repository = repository

    def __call__(self, command: MarkAlertReadCommandV1) -> AlertCommandResultV1:
        return self._repository.apply_alert_command(command)
