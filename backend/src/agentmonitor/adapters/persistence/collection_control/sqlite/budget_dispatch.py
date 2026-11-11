"""M04 queued billing reconstruction; no second queue or provider payload storage."""

import json
from collections.abc import Mapping
from dataclasses import fields
from datetime import datetime, timedelta
from typing import Any, overload

from agentmonitor.adapters.persistence.collection_control.sqlite.budget import (
    BudgetCollectionError,
    CloudBudgetAuthority,
    read_budget_target,
)
from agentmonitor.contracts.collection_control_v1 import (
    BudgetCollectionRunAdmissionV1,
    CloudBudgetCollectionRunAdmissionV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import BillingAccessTargetV1
from agentmonitor.contracts.registry_v1 import ProviderTargetRefV1
from sqlalchemy.engine import Connection


@overload
def restore_budget_admission(
    raw: Mapping[str, Any],
    target: BillingAccessTargetV1,
    *,
    resolved_budget_limit: int,
) -> BudgetCollectionRunAdmissionV1: ...


@overload
def restore_budget_admission(
    raw: Mapping[str, Any],
    target: CloudBudgetAuthority,
    *,
    resolved_budget_limit: int,
) -> CloudBudgetCollectionRunAdmissionV1: ...


def restore_budget_admission(
    raw: Mapping[str, Any],
    target: BillingAccessTargetV1 | CloudBudgetAuthority,
    *,
    resolved_budget_limit: int,
) -> BudgetCollectionRunAdmissionV1 | CloudBudgetCollectionRunAdmissionV1:
    """Pure reconstruction of M04 metadata, with a separately resolved old policy."""
    try:
        if type(resolved_budget_limit) is not int or resolved_budget_limit < 1:
            raise ValueError()
        omitted = {
            "billing_target",
            "cloud_target",
            "service_target",
            "report_context",
            "budget_limit_units",
            "provider_target",
        }
        admission_type = (
            BudgetCollectionRunAdmissionV1
            if isinstance(target, BillingAccessTargetV1)
            else CloudBudgetCollectionRunAdmissionV1
        )
        values = {
            field.name: raw[field.name]
            for field in fields(admission_type)
            if field.name not in omitted
        }
        for name in (
            "run_id",
            "schedule_id",
            "request_id",
            "correlation_id",
            "retry_chain_id",
            "scheduler_instance_id",
        ):
            values[name] = OpaqueIdV1(values[name])
        for name in (
            "request_principal_id",
            "causation_id",
            "account_id",
            "profile_id",
            "resource_id",
        ):
            if values[name] is not None:
                values[name] = OpaqueIdV1(values[name])
        for name in (
            "requested_at",
            "deadline_at",
            "budget_window_start",
            "budget_window_end",
        ):
            if type(values[name]) is not str:
                raise ValueError()
            values[name] = datetime.fromisoformat(values[name])
            if values[name].utcoffset() != timedelta(0):
                raise ValueError()
        capabilities = values["requested_capability_ids"]
        if type(capabilities) is not str or len(capabilities) > 2048:
            raise ValueError()
        capabilities = json.loads(capabilities)
        if type(capabilities) is not list or not all(
            type(item) is str for item in capabilities
        ):
            raise ValueError()
        values["requested_capability_ids"] = tuple(capabilities)
        values["provider_target"] = ProviderTargetRefV1(
            raw["provider_target_kind"], OpaqueIdV1(raw["provider_target_id"])
        )
        if not isinstance(target, BillingAccessTargetV1):
            graph, service, context = target
            return CloudBudgetCollectionRunAdmissionV1(
                **values,
                cloud_target=graph,
                service_target=service,
                report_context=context,
                budget_limit_units=resolved_budget_limit,
            )
        return BudgetCollectionRunAdmissionV1(
            **values, billing_target=target, budget_limit_units=resolved_budget_limit
        )
    except (KeyError, TypeError, ValueError, AttributeError, RecursionError):
        raise BudgetCollectionError("budget_dispatch_metadata_invalid") from None


def read_dispatch_snapshot(
    connection: Connection, run_id: OpaqueIdV1
) -> tuple[dict[str, Any], BillingAccessTargetV1 | CloudBudgetAuthority]:
    """Read only M04-owned tables inside the caller's transaction."""
    run = (
        connection.exec_driver_sql(
            "SELECT * FROM collection_run WHERE run_id=?", (run_id.value,)
        )
        .mappings()
        .one_or_none()
    )
    if run is None or run["payload_schema"] != "budget.report.v1":
        raise BudgetCollectionError("budget_run_not_found")
    request = (
        connection.exec_driver_sql(
            "SELECT * FROM collection_request WHERE request_id=?",
            (run["primary_request_id"],),
        )
        .mappings()
        .one_or_none()
    )
    schedule = (
        connection.exec_driver_sql(
            "SELECT * FROM collection_schedule WHERE schedule_id=?",
            (run["schedule_id"],),
        )
        .mappings()
        .one_or_none()
    )
    lease = (
        connection.exec_driver_sql(
            "SELECT * FROM collection_lease WHERE run_id=?", (run_id.value,)
        )
        .mappings()
        .one_or_none()
    )
    reservation = (
        connection.exec_driver_sql(
            "SELECT * FROM collection_budget_reservation WHERE reservation_id=?",
            (run["budget_reservation_id"],),
        )
        .mappings()
        .one_or_none()
    )
    if request is None or schedule is None or lease is None or reservation is None:
        raise BudgetCollectionError("budget_dispatch_metadata_invalid")
    if (
        request["request_fingerprint"] != run["request_digest"]
        or request["linked_run_id"] != run_id.value
        or request["schedule_id"] != run["schedule_id"]
        or request["trigger_kind"] != run["trigger_kind"]
        or request["requested_at"] != run["requested_at"]
        or request["expires_at"] != run["deadline_at"]
        or request["correlation_id"] != run["correlation_id"]
        or request["causation_id"] != run["causation_id"]
        or request["state"] != "accepted"
        or request["completed_at"] is not None
        or lease["schedule_id"] != run["schedule_id"]
        or lease["fencing_token"] != run["fencing_token"]
        or lease["expires_at"] != run["deadline_at"]
        or reservation["run_id"] != run_id.value
        or reservation["state"] not in {"reserved", "dispatched"}
        or schedule["target_generation"] != run["target_generation"]
        or any(
            schedule[name] != run[name]
            for name in (
                "provider_key",
                "provider_target_kind",
                "provider_target_id",
                "account_id",
                "resource_id",
                "profile_id",
                "capability_id",
            )
        )
    ):
        raise BudgetCollectionError("budget_dispatch_metadata_invalid")
    raw = dict(run)
    raw.update(
        request_id=run["primary_request_id"],
        trigger=run["trigger_kind"],
        operation_family=request["operation_family"],
        requested_capability_ids=request["requested_capabilities_json"],
        capability_set_version=request["capability_set_version"],
        request_auth_method=request["request_auth_method"],
        request_principal_id=request["principal_id"],
        idempotency_key_digest=request["idempotency_key_digest"],
        target_key_digest=schedule["target_key_digest"],
        scheduler_instance_id=lease["owner_instance_id"],
        lease_policy_version=lease["lease_policy_version"],
        budget_policy_id=reservation["constraint_policy_id"],
        budget_policy_version=reservation["constraint_policy_version"],
        budget_scope_digest=reservation["scope_key_digest"],
        budget_dimension=reservation["dimension"],
        budget_unit=reservation["unit"],
        budget_units=reservation["units"],
        budget_window_start=reservation["window_start"],
        budget_window_end=reservation["window_end"],
    )
    return raw, read_budget_target(connection, run_id)
