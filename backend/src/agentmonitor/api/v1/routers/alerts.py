"""Authenticated M07 rules; no client-provided alert signal or foreign SQL."""

import re
from datetime import UTC, datetime
from typing import Literal

from agentmonitor.api.problem import ProblemError
from agentmonitor.api.v1.dependencies import alert_ports, authorize_request
from agentmonitor.api.v1.routers._observation import (
    ERROR_RESPONSES,
    availability,
    decode_cursor,
    page_meta,
    policy,
    reject_unknown_query,
    require_opaque_selector,
)
from agentmonitor.api.v1.schemas.alerts import (
    AlertCommandWireV1,
    AlertHistoryPageV1,
    AlertHistoryWireV1,
    AlertNotificationCountsWireV1,
    AlertNotificationPageV1,
    AlertNotificationWireV1,
    AlertPageV1,
    AlertRuleCommandWireV1,
    AlertRuleInputV1,
    AlertRulePageV1,
    AlertRuleWireV1,
    AlertWireV1,
    ConditionRuleConfigurationWireV1,
    RemainingRuleConfigurationWireV1,
    SnoozeAlertInputV1,
)
from agentmonitor.api.v1.serialization import technical_wire
from agentmonitor.contracts.alerting_v1 import (
    AcknowledgeAlertCommandV1,
    AlertCommandResultV1,
    AlertConditionTypeV1,
    AlertHistoryEntryV1,
    AlertHistoryQueryV1,
    AlertListQueryV1,
    AlertRuleCommandResultV1,
    AlertRuleConfigurationV1,
    AlertRuleListQueryV1,
    AlertRuleViewV1,
    AlertScopeRefV1,
    AlertViewV1,
    ArchiveAlertRuleCommandV1,
    CapacityRemainingRuleConfigurationV1,
    ConditionRuleConfigurationV1,
    CreateAlertRuleCommandV1,
    InvalidAlertContractV1,
    MarkAlertReadCommandV1,
    SnoozeAlertCommandV1,
    UnsnoozeAlertCommandV1,
    UpdateAlertRuleCommandV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from fastapi import APIRouter, Query, Request, Response

router = APIRouter(tags=["alerts"])
_KEY = re.compile(r"[A-Za-z0-9_-]{16,128}\Z")


def _mutation_policy(port: str, *, version: bool = False) -> dict[str, object]:
    result = policy("write:alerts", port)
    result["security"] = [
        {"BrowserSessionCookieV1": [], "BrowserCsrfHeaderV1": []},
        {"BearerTokenV1": []},
    ]
    result["x-agentmonitor-replay-policy"] = "replay_safe_representation"
    parameters = [
        {
            "name": "Idempotency-Key",
            "in": "header",
            "required": True,
            "schema": {"type": "string", "pattern": "^[A-Za-z0-9_-]{16,128}$"},
        }
    ]
    if version:
        parameters.append(
            {
                "name": "If-Match",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "maxLength": 160},
            }
        )
    result["parameters"] = parameters
    return result


def _key(request: Request) -> OpaqueIdV1:
    value = request.headers.get("idempotency-key")
    if value is None or _KEY.fullmatch(value) is None:
        raise ProblemError(400, "invalid_idempotency_key")
    return OpaqueIdV1(value)


def _version(request: Request, rule_id: str) -> int:
    header = request.headers.get("if-match")
    if header is None:
        raise ProblemError(428, "precondition_required")
    match = re.fullmatch(r'"' + re.escape(rule_id) + r'\.(\d+)"\Z', header)
    if match is None or int(match.group(1)) < 1:
        raise ProblemError(400, "invalid_precondition")
    return int(match.group(1))


def _scope(
    kind: Literal["global", "organization", "provider", "account"], subject: str | None
) -> AlertScopeRefV1:
    if (kind == "global") != (subject is None):
        raise ProblemError(422, "invalid_request_fields")
    if subject is not None:
        require_opaque_selector(subject)
    try:
        return AlertScopeRefV1(kind, subject)
    except InvalidAlertContractV1:
        raise ProblemError(422, "invalid_request_fields") from None


def _configuration(input: AlertRuleInputV1) -> AlertRuleConfigurationV1:
    try:
        if input.condition_type == "capacity_remaining":
            if not isinstance(input.configuration, RemainingRuleConfigurationWireV1):
                raise InvalidAlertContractV1("alert_rule_configuration_mismatch")
            item = input.configuration
            return CapacityRemainingRuleConfigurationV1(
                item.schema_major,
                item.warning_remaining_basis_points,
                item.critical_remaining_basis_points,
            )
        if not isinstance(input.configuration, ConditionRuleConfigurationWireV1):
            raise InvalidAlertContractV1("alert_rule_configuration_mismatch")
        return ConditionRuleConfigurationV1(input.configuration.schema_major)
    except InvalidAlertContractV1:
        raise ProblemError(422, "invalid_request_fields") from None


def _rule(value: AlertRuleViewV1) -> AlertRuleWireV1:
    return AlertRuleWireV1.model_validate(technical_wire(value))


def _result(
    value: AlertRuleCommandResultV1, response: Response
) -> AlertRuleCommandWireV1:
    if value.rule.rule_id is not None:
        response.headers["ETag"] = (
            f'"{value.rule.rule_id.value}.{value.rule.record_version}"'
        )
    return AlertRuleCommandWireV1(
        receipt_id=value.receipt_id.value, rule=_rule(value.rule)
    )


def _repository_error(error: ValueError) -> ProblemError:
    code = str(error)
    if code in {"alert_rule_not_found", "alert_not_found"}:
        return ProblemError(404, code)
    if code in {"alert_version_conflict", "alert_notification_conflict"}:
        return ProblemError(412, code)
    if code in {
        "alert_idempotency_conflict",
        "alert_rule_scope_conflict",
        "alert_rule_archived",
        "alert_rule_time_conflict",
        "alert_command_subject_conflict",
        "alert_not_open",
        "alert_transition_time_invalid",
    }:
        return ProblemError(409, code)
    return ProblemError(503, "alert_repository_unavailable")


def _alert(value: AlertViewV1) -> AlertWireV1:
    return AlertWireV1(
        alert_id=value.alert_id.value,
        account_id=value.subject.account_id.value if value.subject.account_id else None,
        organization_id=(
            value.subject.organization_id.value
            if value.subject.organization_id
            else None
        ),
        provider_key=value.subject.provider_key,
        subject_kind=value.subject.subject_kind,
        subject_id=value.subject.subject_id.value,
        dimension_kind=value.subject.dimension_kind,
        dimension_id=value.subject.dimension_id,
        condition_type=value.condition_type,
        severity=value.severity,
        lifecycle=value.lifecycle,
        occurrence_count=value.occurrence_count,
        record_version=value.record_version,
        notification_revision=value.notification_revision,
        opened_at=value.opened_at,
        last_seen_at=value.last_seen_at,
        recovered_at=value.recovered_at,
        unread=value.unread,
        acknowledged_at=value.acknowledged_at,
        snoozed_until=value.snoozed_until,
        decision_reason_code=value.decision.reason_code,
        truth_state=value.decision.truth_state,
        remaining_basis_points=(
            str(value.decision.remaining_basis_points.as_decimal())
            if value.decision.remaining_basis_points
            else None
        ),
        warning_remaining_basis_points=value.decision.warning_remaining_basis_points,
        critical_remaining_basis_points=value.decision.critical_remaining_basis_points,
        reset_at=value.decision.reset_at,
        forecast_exhaustion_at=value.decision.forecast_exhaustion_at,
        source_event_id=value.decision.source.event_id.value,
        source_observed_at=value.decision.source.observed_at,
        source_recorded_at=value.decision.source.recorded_at,
        source_freshness_deadline=value.decision.source.freshness_deadline,
        rule_scope_kind=value.rule.scope.scope_kind,
        rule_scope_id=value.rule.scope.scope_id,
    )


def _history(value: AlertHistoryEntryV1) -> AlertHistoryWireV1:
    return AlertHistoryWireV1(
        event_id=value.event_id.value,
        alert_id=value.alert_id.value,
        aggregate_sequence=value.aggregate_sequence,
        transition=value.transition,
        occurred_at=value.occurred_at,
        previous_lifecycle=value.previous_lifecycle,
        current_lifecycle=value.current_lifecycle,
        previous_severity=value.previous_severity,
        current_severity=value.current_severity,
        reason_code=value.reason_code,
        source_event_id=value.source_event_id.value if value.source_event_id else None,
    )


def _alert_result(
    value: AlertCommandResultV1, response: Response
) -> AlertCommandWireV1:
    response.headers["ETag"] = (
        f'"{value.alert.alert_id.value}.{value.alert.record_version}"'
    )
    return AlertCommandWireV1(
        receipt_id=value.receipt_id.value, alert=_alert(value.alert)
    )


def _alert_list_query(
    request: Request,
    *,
    operation_id: str,
    condition_type: AlertConditionTypeV1 | None,
    scope_kind: Literal["global", "organization", "provider", "account"] | None,
    scope_id: str | None,
    lifecycle: Literal["open", "recovered", "closed_by_configuration"] | None,
    severity: Literal["information", "warning", "critical"] | None,
    unread: bool | None,
    snoozed: bool | None,
    limit: int,
    cursor: str | None,
) -> tuple[AlertListQueryV1, dict[str, str | None]]:
    reject_unknown_query(
        request,
        frozenset(
            {
                "condition_type",
                "scope_kind",
                "scope_id",
                "lifecycle",
                "severity",
                "unread",
                "snoozed",
                "limit",
                "cursor",
            }
        ),
    )
    if scope_kind is None and scope_id is not None:
        raise ProblemError(400, "invalid_filter")
    scope = _scope(scope_kind, scope_id) if scope_kind else None
    filters = {
        "condition_type": condition_type,
        "scope_kind": scope_kind,
        "scope_id": scope_id,
        "lifecycle": lifecycle,
        "severity": severity,
        "unread": None if unread is None else str(unread),
        "snoozed": None if snoozed is None else str(snoozed),
    }
    caller = authorize_request(request, "read:alerts")
    after = decode_cursor(
        request, caller, cursor, operation_id=operation_id, limit=limit, filters=filters
    )
    return (
        AlertListQueryV1(
            datetime.now(UTC),
            condition_type,
            scope,
            lifecycle,
            severity,
            unread,
            snoozed,
            None,
            None,
            limit,
            after,
        ),
        filters,
    )


@router.get(
    "/alerts",
    operation_id="alert_list_alerts_v1",
    response_model=AlertPageV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:alerts", "ListAlertsV1"),
)
def list_alerts(
    request: Request,
    condition_type: AlertConditionTypeV1 | None = None,
    scope_kind: Literal["global", "organization", "provider", "account"] | None = None,
    scope_id: str | None = Query(None, max_length=128),
    lifecycle: Literal["open", "recovered", "closed_by_configuration"] | None = None,
    severity: Literal["information", "warning", "critical"] | None = None,
    unread: bool | None = None,
    snoozed: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=1024),
) -> AlertPageV1:
    caller = authorize_request(request, "read:alerts")
    query, filters = _alert_list_query(
        request,
        operation_id="alert_list_alerts_v1",
        condition_type=condition_type,
        scope_kind=scope_kind,
        scope_id=scope_id,
        lifecycle=lifecycle,
        severity=severity,
        unread=unread,
        snoozed=snoozed,
        limit=limit,
        cursor=cursor,
    )
    try:
        result = alert_ports(request).list_alerts(query)
    except ValueError as error:
        raise _repository_error(error) from None
    return AlertPageV1(
        items=tuple(_alert(item) for item in result.items),
        page=page_meta(
            request,
            caller,
            operation_id="alert_list_alerts_v1",
            limit=limit,
            has_more=result.has_more,
            next_key=result.next_key,
            filters=filters,
        ),
        availability=availability(result.availability),
    )


@router.get(
    "/alert-notifications",
    operation_id="alert_list_notifications_v1",
    response_model=AlertNotificationPageV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:alerts", "ListDashboardNotificationsV1"),
)
def list_notifications(
    request: Request,
    scope_kind: Literal["global", "organization", "provider", "account"] | None = None,
    scope_id: str | None = Query(None, max_length=128),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=1024),
) -> AlertNotificationPageV1:
    caller = authorize_request(request, "read:alerts")
    query, filters = _alert_list_query(
        request,
        operation_id="alert_list_notifications_v1",
        condition_type=None,
        scope_kind=scope_kind,
        scope_id=scope_id,
        lifecycle=None,
        severity=None,
        unread=None,
        snoozed=None,
        limit=limit,
        cursor=cursor,
    )
    try:
        result = alert_ports(request).list_notifications(query)
    except ValueError as error:
        raise _repository_error(error) from None
    return AlertNotificationPageV1(
        items=tuple(
            AlertNotificationWireV1(
                alert=_alert(item.alert),
                rank=item.rank,
                is_visible_unread=item.is_visible_unread,
            )
            for item in result.items
        ),
        page=page_meta(
            request,
            caller,
            operation_id="alert_list_notifications_v1",
            limit=limit,
            has_more=result.has_more,
            next_key=result.next_key,
            filters=filters,
        ),
        availability=availability(result.availability),
    )


@router.get(
    "/alert-notifications/counts",
    operation_id="alert_get_notification_counts_v1",
    response_model=AlertNotificationCountsWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:alerts", "GetDashboardNotificationCountsV1"),
)
def notification_counts(
    request: Request,
    scope_kind: Literal["global", "organization", "provider", "account"] | None = None,
    scope_id: str | None = Query(None, max_length=128),
) -> AlertNotificationCountsWireV1:
    authorize_request(request, "read:alerts")
    query, _ = _alert_list_query(
        request,
        operation_id="alert_get_notification_counts_v1",
        condition_type=None,
        scope_kind=scope_kind,
        scope_id=scope_id,
        lifecycle=None,
        severity=None,
        unread=None,
        snoozed=None,
        limit=50,
        cursor=None,
    )
    try:
        result = alert_ports(request).notification_counts(query)
    except ValueError as error:
        raise _repository_error(error) from None
    return AlertNotificationCountsWireV1.model_validate(technical_wire(result))


@router.get(
    "/alerts/{alert_id}",
    operation_id="alert_get_alert_v1",
    response_model=AlertWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:alerts", "GetAlertV1"),
)
def get_alert(alert_id: str, request: Request, response: Response) -> AlertWireV1:
    authorize_request(request, "read:alerts")
    reject_unknown_query(request, frozenset())
    require_opaque_selector(alert_id)
    try:
        found = alert_ports(request).get_alert(
            OpaqueIdV1(alert_id), as_of=datetime.now(UTC)
        )
    except ValueError as error:
        raise _repository_error(error) from None
    if found is None:
        raise ProblemError(404, "alert_not_found")
    response.headers["ETag"] = f'"{alert_id}.{found.record_version}"'
    return _alert(found)


@router.get(
    "/alerts/{alert_id}/history",
    operation_id="alert_list_history_v1",
    response_model=AlertHistoryPageV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:alerts", "ListAlertHistoryV1"),
)
def list_alert_history(
    alert_id: str,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=1024),
) -> AlertHistoryPageV1:
    caller = authorize_request(request, "read:alerts")
    reject_unknown_query(request, frozenset({"limit", "cursor"}))
    require_opaque_selector(alert_id)
    filters: dict[str, str | None] = {"alert_id": alert_id}
    after = decode_cursor(
        request,
        caller,
        cursor,
        operation_id="alert_list_history_v1",
        limit=limit,
        filters=filters,
    )
    try:
        port = alert_ports(request)
        if port.get_alert(OpaqueIdV1(alert_id), as_of=datetime.now(UTC)) is None:
            raise ProblemError(404, "alert_not_found")
        result = port.list_alert_history(
            AlertHistoryQueryV1(OpaqueIdV1(alert_id), datetime.now(UTC), limit, after)
        )
    except ValueError as error:
        raise _repository_error(error) from None
    return AlertHistoryPageV1(
        items=tuple(_history(item) for item in result.items),
        page=page_meta(
            request,
            caller,
            operation_id="alert_list_history_v1",
            limit=limit,
            has_more=result.has_more,
            next_key=result.next_key,
            filters=filters,
        ),
        availability=availability(result.availability),
    )


@router.post(
    "/alerts/{alert_id}/acknowledgements",
    operation_id="alert_acknowledge_v1",
    response_model=AlertCommandWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_mutation_policy("AcknowledgeAlertV1", version=True),
)
def acknowledge_alert(
    alert_id: str, request: Request, response: Response
) -> AlertCommandWireV1:
    caller = authorize_request(request, "write:alerts", require_csrf=True)
    reject_unknown_query(request, frozenset())
    require_opaque_selector(alert_id)
    command = AcknowledgeAlertCommandV1(
        _key(request),
        caller.principal.principal_id,
        OpaqueIdV1(alert_id),
        _version(request, alert_id),
        datetime.now(UTC),
    )
    try:
        return _alert_result(alert_ports(request).acknowledge_alert(command), response)
    except ValueError as error:
        raise _repository_error(error) from None


@router.post(
    "/alerts/{alert_id}/snoozes",
    operation_id="alert_snooze_v1",
    response_model=AlertCommandWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_mutation_policy("SnoozeAlertV1", version=True),
)
def snooze_alert(
    alert_id: str,
    input: SnoozeAlertInputV1,
    request: Request,
    response: Response,
) -> AlertCommandWireV1:
    caller = authorize_request(request, "write:alerts", require_csrf=True)
    reject_unknown_query(request, frozenset())
    require_opaque_selector(alert_id)
    command = SnoozeAlertCommandV1(
        _key(request),
        caller.principal.principal_id,
        OpaqueIdV1(alert_id),
        _version(request, alert_id),
        datetime.now(UTC),
        input.duration_seconds,
    )
    try:
        return _alert_result(alert_ports(request).snooze_alert(command), response)
    except ValueError as error:
        raise _repository_error(error) from None


@router.post(
    "/alerts/{alert_id}/unsnoozes",
    operation_id="alert_unsnooze_v1",
    response_model=AlertCommandWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_mutation_policy("UnsnoozeAlertV1", version=True),
)
def unsnooze_alert(
    alert_id: str, request: Request, response: Response
) -> AlertCommandWireV1:
    caller = authorize_request(request, "write:alerts", require_csrf=True)
    reject_unknown_query(request, frozenset())
    require_opaque_selector(alert_id)
    command = UnsnoozeAlertCommandV1(
        _key(request),
        caller.principal.principal_id,
        OpaqueIdV1(alert_id),
        _version(request, alert_id),
        datetime.now(UTC),
    )
    try:
        return _alert_result(alert_ports(request).unsnooze_alert(command), response)
    except ValueError as error:
        raise _repository_error(error) from None


@router.post(
    "/alerts/{alert_id}/read-receipts",
    operation_id="alert_mark_read_v1",
    response_model=AlertCommandWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_mutation_policy("MarkAlertReadV1", version=True),
)
def mark_alert_read(
    alert_id: str, request: Request, response: Response
) -> AlertCommandWireV1:
    caller = authorize_request(request, "write:alerts", require_csrf=True)
    reject_unknown_query(request, frozenset())
    require_opaque_selector(alert_id)
    command = MarkAlertReadCommandV1(
        _key(request),
        caller.principal.principal_id,
        OpaqueIdV1(alert_id),
        _version(request, alert_id),
        datetime.now(UTC),
    )
    try:
        return _alert_result(alert_ports(request).mark_alert_read(command), response)
    except ValueError as error:
        raise _repository_error(error) from None


@router.get(
    "/alert-rules",
    operation_id="alert_list_rules_v1",
    response_model=AlertRulePageV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:alerts", "ListAlertRulesV1"),
)
def list_rules(
    request: Request,
    condition_type: AlertConditionTypeV1 | None = None,
    scope_kind: Literal["global", "organization", "provider", "account"] | None = None,
    scope_id: str | None = Query(None, max_length=128),
    include_archived: bool = False,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=1024),
) -> AlertRulePageV1:
    caller = authorize_request(request, "read:alerts")
    reject_unknown_query(
        request,
        frozenset(
            {
                "condition_type",
                "scope_kind",
                "scope_id",
                "include_archived",
                "limit",
                "cursor",
            }
        ),
    )
    if (scope_kind is None) != (scope_id is None) and scope_kind != "global":
        raise ProblemError(400, "invalid_filter")
    scope = _scope(scope_kind, scope_id) if scope_kind else None
    filters = {
        "condition_type": condition_type,
        "scope_kind": scope_kind,
        "scope_id": scope_id,
        "include_archived": str(include_archived),
    }
    after = decode_cursor(
        request,
        caller,
        cursor,
        operation_id="alert_list_rules_v1",
        limit=limit,
        filters=filters,
    )
    try:
        result = alert_ports(request).list_rules(
            AlertRuleListQueryV1(
                datetime.now(UTC), condition_type, scope, include_archived, limit, after
            )
        )
    except ValueError as error:
        raise _repository_error(error) from None
    return AlertRulePageV1(
        items=tuple(_rule(item) for item in result.items),
        page=page_meta(
            request,
            caller,
            operation_id="alert_list_rules_v1",
            limit=limit,
            has_more=result.has_more,
            next_key=result.next_key,
            filters=filters,
        ),
        availability=availability(result.availability),
    )


@router.get(
    "/alert-rules/{rule_id}",
    operation_id="alert_get_rule_v1",
    response_model=AlertRuleWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:alerts", "GetAlertRuleV1"),
)
def get_rule(rule_id: str, request: Request, response: Response) -> AlertRuleWireV1:
    authorize_request(request, "read:alerts")
    reject_unknown_query(request, frozenset())
    require_opaque_selector(rule_id)
    try:
        result = alert_ports(request).get_rule(OpaqueIdV1(rule_id))
    except ValueError as error:
        raise _repository_error(error) from None
    if result is None:
        raise ProblemError(404, "alert_rule_not_found")
    response.headers["ETag"] = f'"{rule_id}.{result.record_version}"'
    return _rule(result)


@router.post(
    "/alert-rules",
    operation_id="alert_create_rule_v1",
    status_code=201,
    response_model=AlertRuleCommandWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_mutation_policy("CreateAlertRuleV1"),
)
def create_rule(
    input: AlertRuleInputV1, request: Request, response: Response
) -> AlertRuleCommandWireV1:
    caller = authorize_request(request, "write:alerts", require_csrf=True)
    reject_unknown_query(request, frozenset())
    command = CreateAlertRuleCommandV1(
        _key(request),
        caller.principal.principal_id,
        input.condition_type,
        _scope(input.scope_kind, input.scope_id),
        input.enabled,
        _configuration(input),
        datetime.now(UTC),
    )
    try:
        return _result(alert_ports(request).create_rule(command), response)
    except ValueError as error:
        raise _repository_error(error) from None


@router.put(
    "/alert-rules/{rule_id}",
    operation_id="alert_update_rule_v1",
    response_model=AlertRuleCommandWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_mutation_policy("UpdateAlertRuleV1", version=True),
)
def update_rule(
    rule_id: str, input: AlertRuleInputV1, request: Request, response: Response
) -> AlertRuleCommandWireV1:
    caller = authorize_request(request, "write:alerts", require_csrf=True)
    reject_unknown_query(request, frozenset())
    require_opaque_selector(rule_id)
    command = UpdateAlertRuleCommandV1(
        _key(request),
        caller.principal.principal_id,
        input.condition_type,
        _scope(input.scope_kind, input.scope_id),
        input.enabled,
        _configuration(input),
        datetime.now(UTC),
        OpaqueIdV1(rule_id),
        _version(request, rule_id),
    )
    try:
        return _result(alert_ports(request).update_rule(command), response)
    except ValueError as error:
        raise _repository_error(error) from None


@router.post(
    "/alert-rules/{rule_id}/archivals",
    operation_id="alert_archive_rule_v1",
    response_model=AlertRuleCommandWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_mutation_policy("ArchiveAlertRuleOverrideV1", version=True),
)
def archive_rule(
    rule_id: str, request: Request, response: Response
) -> AlertRuleCommandWireV1:
    caller = authorize_request(request, "write:alerts", require_csrf=True)
    reject_unknown_query(request, frozenset())
    require_opaque_selector(rule_id)
    command = ArchiveAlertRuleCommandV1(
        _key(request),
        caller.principal.principal_id,
        OpaqueIdV1(rule_id),
        _version(request, rule_id),
        datetime.now(UTC),
    )
    try:
        return _result(alert_ports(request).archive_rule(command), response)
    except ValueError as error:
        raise _repository_error(error) from None
