"""Rule commands over approved registry snapshot and M07-only persistence ports."""

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta

from agentmonitor.contracts.alerting_v1 import (
    AlertConditionTypeV1,
    AlertRuleCommandResultV1,
    AlertRuleListQueryV1,
    AlertRuleViewV1,
    AlertScopeRefV1,
    AlertSubjectV1,
    ArchiveAlertRuleCommandV1,
    CreateAlertRuleCommandV1,
    EffectiveAlertRuleViewV1,
    UpdateAlertRuleCommandV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1, QueryPageV1
from agentmonitor.contracts.registry_v1 import (
    AlertScopeAndSubjectQueryV1,
    AlertSubjectScopeV1,
    RegistryScopeSnapshotV1,
)
from agentmonitor.modules.alerting.application.ports import AlertRuleRepositoryV1
from agentmonitor.modules.alerting.domain.policy import resolve_effective_rule


def validate_scope_snapshot(
    scope: AlertScopeRefV1, snapshot: RegistryScopeSnapshotV1
) -> None:
    value = scope.scope_id
    if (
        snapshot.completeness_state != "complete"
        or snapshot.scope_kind != scope.scope_kind
        or (snapshot.scope_id.value if snapshot.scope_id else None) != value
    ):
        raise ValueError("alert_scope_unavailable")
    if (
        scope.scope_kind == "account"
        and OpaqueIdV1(value or "invalid") not in snapshot.account_ids
    ):
        raise ValueError("alert_scope_unavailable")
    if (
        scope.scope_kind == "organization"
        and OpaqueIdV1(value or "invalid") not in snapshot.organization_ids
    ):
        raise ValueError("alert_scope_unavailable")
    # Membership proves only providers which actually have an eligible account.
    # Empty providers wait for the separately published definition-confirmation port.
    if scope.scope_kind == "provider" and not snapshot.account_ids:
        raise ValueError("alert_scope_unavailable")


class CreateAlertRuleV1:
    def __init__(
        self,
        repository: AlertRuleRepositoryV1,
        scope_query: AlertScopeAndSubjectQueryV1,
    ) -> None:
        self._repository = repository
        self._scope_query = scope_query

    def __call__(self, command: CreateAlertRuleCommandV1) -> AlertRuleCommandResultV1:
        replay = self._repository.lookup_rule_command(command)
        if replay is not None:
            return replay
        snapshot = self._scope_query(
            command.scope.scope_kind,
            OpaqueIdV1(command.scope.scope_id) if command.scope.scope_id else None,
        )
        validate_scope_snapshot(command.scope, snapshot)
        return self._repository.create_rule(command, snapshot)


class UpdateAlertRuleV1:
    def __init__(
        self,
        repository: AlertRuleRepositoryV1,
        scope_query: AlertScopeAndSubjectQueryV1,
    ) -> None:
        self._repository = repository
        self._scope_query = scope_query

    def __call__(self, command: UpdateAlertRuleCommandV1) -> AlertRuleCommandResultV1:
        replay = self._repository.lookup_rule_command(command)
        if replay is not None:
            return replay
        snapshot = self._scope_query(
            command.scope.scope_kind,
            OpaqueIdV1(command.scope.scope_id) if command.scope.scope_id else None,
        )
        validate_scope_snapshot(command.scope, snapshot)
        return self._repository.update_rule(command, snapshot)


class ArchiveAlertRuleOverrideV1:
    def __init__(
        self,
        repository: AlertRuleRepositoryV1,
        scope_query: AlertScopeAndSubjectQueryV1,
    ) -> None:
        self._repository = repository
        self._scope_query = scope_query

    def __call__(self, command: ArchiveAlertRuleCommandV1) -> AlertRuleCommandResultV1:
        replay = self._repository.lookup_rule_command(command)
        if replay is not None:
            return replay
        snapshot = self._scope_query("global", None)
        if snapshot.completeness_state != "complete":
            raise ValueError("alert_scope_unavailable")
        return self._repository.archive_rule(command, snapshot)


class GetAlertRuleV1:
    def __init__(self, repository: AlertRuleRepositoryV1) -> None:
        self._repository = repository

    def __call__(self, rule_id: OpaqueIdV1) -> AlertRuleViewV1 | None:
        return self._repository.get_rule(rule_id)


class ListAlertRulesV1:
    def __init__(self, repository: AlertRuleRepositoryV1) -> None:
        self._repository = repository

    def __call__(self, query: AlertRuleListQueryV1) -> QueryPageV1[AlertRuleViewV1]:
        return self._repository.list_rules(query)


class ResolveEffectiveAlertRuleV1:
    """Recheck actual membership around M07 rule reads; no inferred association."""

    def __init__(
        self,
        repository: AlertRuleRepositoryV1,
        subject_scope_query: Callable[[OpaqueIdV1], AlertSubjectScopeV1 | None],
        scope_query: AlertScopeAndSubjectQueryV1,
    ) -> None:
        self._repository = repository
        self._subject_scope_query = subject_scope_query
        self._scope_query = scope_query

    def __call__(
        self,
        subject: AlertSubjectV1,
        condition_type: AlertConditionTypeV1,
        *,
        as_of: datetime,
    ) -> EffectiveAlertRuleViewV1:
        if as_of.utcoffset() != timedelta(0):
            raise ValueError("alert_utc_required")
        if subject.account_id is None:
            before = self._scope_query("global", None)
            if before.completeness_state != "complete":
                raise ValueError("alert_scope_unavailable")
            current_subject = replace(
                subject, registry_revision=before.registry_revision
            )
            candidates = self._repository.list_rule_candidates(
                current_subject, condition_type
            )
            if self._scope_query("global", None) != before:
                raise ValueError("alert_scope_changed")
        else:
            before_subject = self._subject_scope_query(subject.account_id)
            if before_subject is None or not before_subject.eligible:
                raise ValueError("alert_subject_unavailable")
            if subject.provider_key != before_subject.provider_key:
                raise ValueError("alert_subject_scope_conflict")
            current_subject = replace(
                subject,
                organization_id=before_subject.organization_id,
                registry_revision=before_subject.registry_revision,
            )
            candidates = self._repository.list_rule_candidates(
                current_subject, condition_type
            )
            if self._subject_scope_query(subject.account_id) != before_subject:
                raise ValueError("alert_scope_changed")
        return resolve_effective_rule(current_subject, condition_type, candidates)
