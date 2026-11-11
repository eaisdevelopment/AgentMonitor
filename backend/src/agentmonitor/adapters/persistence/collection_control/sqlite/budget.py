"""M04 billing target codec and transaction-bound authority checks."""

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from agentmonitor.contracts.capacity_v1 import (
    BudgetCollectionInputV1,
    BudgetReportInputV1,
)
from agentmonitor.contracts.collection_control_v1 import (
    BudgetCollectionRunAdmissionV1,
    CloudBudgetCollectionRunAdmissionV1,
    CloudBudgetReportContextV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import (
    BillingAccessTargetV1,
    BillingConnectionViewV1,
)
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    CloudMonitoringTargetV1,
    ProviderAccessTargetV1,
)
from sqlalchemy.engine import Connection

BillingAdmissionFence = Callable[[Connection, BillingAccessTargetV1], None]
CloudAdmissionFence = Callable[
    [
        Connection,
        CloudMonitoringTargetV1,
        ProviderAccessTargetV1,
        CloudBudgetReportContextV1,
    ],
    None,
]


class BudgetCollectionError(ValueError):
    """Closed collection errors never expose stored metadata or SQL."""

    def __init__(self, code: str = "budget_target_encoding_invalid") -> None:
        self.code = code
        super().__init__(code)


def _utc(value: datetime) -> str:
    if value.utcoffset() != timedelta(0):
        raise BudgetCollectionError()
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def _encode(value: object) -> object:
    if value is None or type(value) in (int, str):
        return value
    if type(value) is OpaqueIdV1:
        return value.value
    if type(value) is datetime:
        return _utc(value)
    if type(value) in (
        BillingAccessTargetV1,
        BillingConnectionViewV1,
        ActiveCredentialBindingRefV1,
    ):
        return {
            field.name: _encode(getattr(value, field.name))
            for field in fields(cast(Any, value))
        }
    raise BudgetCollectionError()


def _object(value: Any, cls: type[Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {field.name for field in fields(cls)}:
        raise BudgetCollectionError()
    return cast(dict[str, Any], value)


def _decode(value: Any) -> BillingAccessTargetV1:
    target = dict(_object(value, BillingAccessTargetV1))
    connection = dict(_object(target["connection"], BillingConnectionViewV1))
    binding = dict(_object(target["binding"], ActiveCredentialBindingRefV1))
    if (
        target["purpose"] not in ("verification", "monitoring")
        or connection["provider_key"] not in ("claude", "codex", "ollama")
        or connection["scope_evidence"]
        not in ("unresolved", "owner_asserted", "provider_verified")
        or connection["monitoring_preference"] not in ("enabled", "disabled")
        or connection["lifecycle"] not in ("pending", "active", "disconnected")
    ):
        raise BudgetCollectionError()
    for name in ("account_id", "resource_id"):
        connection[name] = OpaqueIdV1(connection[name])
    for name in ("account_id", "binding_id"):
        binding[name] = OpaqueIdV1(binding[name])
    for name in ("created_at", "updated_at"):
        text = connection[name]
        if type(text) is not str:
            raise BudgetCollectionError()
        connection[name] = datetime.fromisoformat(text)
        if _utc(connection[name]) != text:
            raise BudgetCollectionError()
    return BillingAccessTargetV1(
        BillingConnectionViewV1(**connection),
        ActiveCredentialBindingRefV1(**binding),
        target["purpose"],
    )


def encode_billing_target(target: BillingAccessTargetV1) -> str:
    try:
        if type(target) is not BillingAccessTargetV1:
            raise BudgetCollectionError()
        normalized = _decode(_encode(target))
        text = json.dumps(
            _encode(normalized),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        if len(text) > 8192:
            raise BudgetCollectionError()
        return text
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise BudgetCollectionError() from None


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BudgetCollectionError()
        result[key] = value
    return result


def _reject_number(value: str) -> None:
    raise BudgetCollectionError()


def decode_billing_target(text: str) -> BillingAccessTargetV1:
    try:
        if type(text) is not str or not 2 <= len(text) <= 8192 or not text.isascii():
            raise BudgetCollectionError()
        target = _decode(
            json.loads(
                text,
                object_pairs_hook=_pairs,
                parse_float=_reject_number,
                parse_constant=_reject_number,
            )
        )
        if encode_billing_target(target) != text:
            raise BudgetCollectionError()
        return target
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise BudgetCollectionError() from None


CloudBudgetAuthority = tuple[
    CloudMonitoringTargetV1, ProviderAccessTargetV1, CloudBudgetReportContextV1
]


def _cloud_value(value: object) -> object:
    if type(value) in (
        CloudMonitoringTargetV1,
        ProviderAccessTargetV1,
        CloudBudgetReportContextV1,
    ):
        return {
            field.name: _cloud_value(getattr(value, field.name))
            for field in fields(cast(Any, value))
        }
    return _encode(value)


def _cloud_document(authority: CloudBudgetAuthority) -> dict[str, object]:
    graph, service, context = authority
    if (
        type(graph) is not CloudMonitoringTargetV1
        or type(service) is not ProviderAccessTargetV1
        or type(context) is not CloudBudgetReportContextV1
    ):
        raise BudgetCollectionError()
    return {
        "tag": "cloud_budget_target.v1",
        "cloud_target": _cloud_value(graph),
        "service_target": _cloud_value(service),
        "report_context": _cloud_value(context),
    }


def _cloud_timestamp(value: Any) -> datetime:
    if type(value) is not str:
        raise BudgetCollectionError()
    result = datetime.fromisoformat(value)
    if _utc(result) != value:
        raise BudgetCollectionError()
    return result


def _decode_cloud(value: Any) -> CloudBudgetAuthority:
    if (
        type(value) is not dict
        or set(value) != {"tag", "cloud_target", "service_target", "report_context"}
        or value["tag"] != "cloud_budget_target.v1"
    ):
        raise BudgetCollectionError()
    graph = dict(_object(value["cloud_target"], CloudMonitoringTargetV1))
    binding = dict(_object(graph["binding"], ActiveCredentialBindingRefV1))
    service = dict(_object(value["service_target"], ProviderAccessTargetV1))
    context = dict(_object(value["report_context"], CloudBudgetReportContextV1))
    for name in (
        "profile_id",
        "resource_id",
        "account_id",
        "access_target_id",
        "owner_principal_id",
    ):
        graph[name] = OpaqueIdV1(graph[name])
    for name in ("account_id", "binding_id"):
        binding[name] = OpaqueIdV1(binding[name])
    graph["binding"] = ActiveCredentialBindingRefV1(**binding)
    graph["owner_asserted_at"] = _cloud_timestamp(graph["owner_asserted_at"])
    service["access_target_id"] = OpaqueIdV1(service["access_target_id"])
    for name in ("interval_start", "interval_end"):
        context[name] = _cloud_timestamp(context[name])
    target = CloudMonitoringTargetV1(**graph)
    provider = ProviderAccessTargetV1(**service)
    report_context = CloudBudgetReportContextV1(**context)
    if (
        target.lifecycle != "active"
        or target.identity_state != "owner_confirmed"
        or provider.lifecycle != "active"
        or provider.provider_key != "ollama"
        or provider.target_kind != "cloud_service"
        or provider.authority_id != "ollama.com"
        or target.access_target_id != provider.access_target_id
    ):
        raise BudgetCollectionError()
    return target, provider, report_context


def encode_cloud_budget_target(
    cloud_target: CloudMonitoringTargetV1,
    service_target: ProviderAccessTargetV1,
    report_context: CloudBudgetReportContextV1,
) -> str:
    """Encode captured authority only; this never proves it remains current."""
    try:
        normalized = _decode_cloud(
            _cloud_document((cloud_target, service_target, report_context))
        )
        text = json.dumps(
            _cloud_document(normalized),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        if len(text) > 8192:
            raise BudgetCollectionError()
        return text
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise BudgetCollectionError() from None


def decode_cloud_budget_target(text: str) -> CloudBudgetAuthority:
    """Require the exact tagged canonical representation before restoring DTOs."""
    try:
        if type(text) is not str or not 2 <= len(text) <= 8192 or not text.isascii():
            raise BudgetCollectionError()
        authority = _decode_cloud(
            json.loads(
                text,
                object_pairs_hook=_pairs,
                parse_float=_reject_number,
                parse_constant=_reject_number,
            )
        )
        if encode_cloud_budget_target(*authority) != text:
            raise BudgetCollectionError()
        return authority
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise BudgetCollectionError() from None


def decode_budget_target(text: str) -> BillingAccessTargetV1 | CloudBudgetAuthority:
    """Select the closed tagged authority; never reinterpret an unknown tag."""
    try:
        if type(text) is not str or not text.isascii() or len(text) > 8192:
            raise BudgetCollectionError()
        value = json.loads(text, object_pairs_hook=_pairs)
        if type(value) is not dict:
            raise BudgetCollectionError()
        if "tag" in value:
            return decode_cloud_budget_target(text)
        return decode_billing_target(text)
    except (ValueError, TypeError, RecursionError):
        raise BudgetCollectionError() from None


def capture_cloud_budget_target(
    connection: Connection,
    admission: CloudBudgetCollectionRunAdmissionV1,
    *,
    resolved_run_id: OpaqueIdV1,
    newly_created: bool,
    fence: CloudAdmissionFence | None,
) -> None:
    if fence is None:
        raise BudgetCollectionError("budget_admission_fence_required")
    target = admission.cloud_target, admission.service_target, admission.report_context
    encoded = encode_cloud_budget_target(*target)
    fence(connection, *target)
    _capture_target(connection, encoded, resolved_run_id, newly_created)


def _capture_target(
    connection: Connection,
    encoded: str,
    resolved_run_id: OpaqueIdV1,
    newly_created: bool,
) -> None:
    if not connection.in_transaction():
        raise BudgetCollectionError("budget_admission_fence_invalid")
    if newly_created:
        connection.exec_driver_sql(
            "INSERT INTO collection_budget_run (run_id,canonical_target_json) "
            "VALUES (?,?)",
            (resolved_run_id.value, encoded),
        )
    else:
        prior = connection.exec_driver_sql(
            "SELECT canonical_target_json FROM collection_budget_run WHERE run_id=?",
            (resolved_run_id.value,),
        ).scalar_one_or_none()
        if prior != encoded:
            raise BudgetCollectionError("budget_admission_target_conflict")


def capture_billing_target(
    connection: Connection,
    admission: BudgetCollectionRunAdmissionV1,
    *,
    resolved_run_id: OpaqueIdV1,
    newly_created: bool,
    fence: BillingAdmissionFence | None,
) -> None:
    if fence is None:
        raise BudgetCollectionError("budget_admission_fence_required")
    encoded = encode_billing_target(admission.billing_target)
    fence(connection, admission.billing_target)
    _capture_target(connection, encoded, resolved_run_id, newly_created)


def read_budget_target(
    connection: Connection, run_id: OpaqueIdV1
) -> BillingAccessTargetV1 | CloudBudgetAuthority:
    encoded = connection.exec_driver_sql(
        "SELECT canonical_target_json FROM collection_budget_run WHERE run_id=?",
        (run_id.value,),
    ).scalar_one_or_none()
    if encoded is None:
        raise BudgetCollectionError("budget_run_not_found")
    return decode_budget_target(str(encoded))


def read_billing_target(
    connection: Connection, run_id: OpaqueIdV1
) -> BillingAccessTargetV1:
    target = read_budget_target(connection, run_id)
    if not isinstance(target, BillingAccessTargetV1):
        raise BudgetCollectionError()
    return target


@dataclass(frozen=True, slots=True)
class BudgetLeaseSnapshot:
    """Closed lease facts for pure fencing policy, read from M04 tables only."""

    run_state: str
    run_generation: int
    schedule_generation: int
    run_fence: int
    lease_fence: int
    owner_instance_id: OpaqueIdV1
    scheduler_state: str
    stopping_at: datetime | None
    completed_at: datetime | None
    heartbeat_at: datetime
    expires_at: datetime


def require_budget_lease_current(
    lease: BudgetLeaseSnapshot,
    *,
    scheduler_instance_id: OpaqueIdV1,
    fencing_token: int,
    as_of: datetime,
    expected_state: str = "committing",
    transition_state: str | None = None,
) -> None:
    if (
        type(fencing_token) is not int
        or fencing_token < 1
        or as_of.utcoffset() != timedelta(0)
        or expected_state not in {"queued", "running", "committing"}
        or lease.run_state != expected_state
        or lease.run_generation != lease.schedule_generation
        or lease.run_fence != fencing_token
        or lease.lease_fence != fencing_token
        or lease.owner_instance_id != scheduler_instance_id
        or lease.scheduler_state not in ("running", "reconciling")
        or lease.stopping_at is not None
        or lease.completed_at is not None
        or lease.heartbeat_at > as_of
        or (
            lease.expires_at <= as_of
            and transition_state
            not in {"failed", "blocked", "cancelled", "unsupported"}
        )
    ):
        raise BudgetCollectionError("budget_run_fencing_conflict")


def require_budget_run_lease(
    connection: Connection,
    run_id: OpaqueIdV1,
    *,
    scheduler_instance_id: OpaqueIdV1,
    fencing_token: int,
    as_of: datetime,
    expected_state: str = "committing",
    transition_state: str | None = None,
) -> None:
    if not connection.in_transaction():
        raise BudgetCollectionError("budget_run_transaction_required")
    row = (
        connection.exec_driver_sql(
            "SELECT r.state,r.target_generation,r.fencing_token,"
            "s.target_generation AS schedule_generation,l.fencing_token AS lease_fence,"
            "l.owner_instance_id,l.expires_at,o.lifecycle_state,o.stopping_at,"
            "o.completed_at,o.heartbeat_at FROM collection_run r "
            "JOIN collection_budget_run b ON b.run_id=r.run_id "
            "JOIN collection_schedule s ON s.schedule_id=r.schedule_id "
            "JOIN collection_lease l ON l.run_id=r.run_id "
            "AND l.schedule_id=r.schedule_id "
            "JOIN collection_scheduler_instance o ON o.instance_id=l.owner_instance_id "
            "WHERE r.run_id=?",
            (run_id.value,),
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise BudgetCollectionError("budget_run_fencing_conflict")
    snapshot = BudgetLeaseSnapshot(
        str(row["state"]),
        int(row["target_generation"]),
        int(row["schedule_generation"]),
        int(row["fencing_token"]),
        int(row["lease_fence"]),
        OpaqueIdV1(str(row["owner_instance_id"])),
        str(row["lifecycle_state"]),
        datetime.fromisoformat(str(row["stopping_at"]))
        if row["stopping_at"] is not None
        else None,
        datetime.fromisoformat(str(row["completed_at"]))
        if row["completed_at"] is not None
        else None,
        datetime.fromisoformat(str(row["heartbeat_at"])),
        datetime.fromisoformat(str(row["expires_at"])),
    )
    require_budget_lease_current(
        snapshot,
        scheduler_instance_id=scheduler_instance_id,
        fencing_token=fencing_token,
        as_of=as_of,
        expected_state=expected_state,
        transition_state=transition_state,
    )


def _require_budget_commit_authority(
    connection: Connection,
    request: BudgetCollectionInputV1,
    *,
    scheduler_instance_id: OpaqueIdV1,
    fencing_token: int,
    as_of: datetime,
) -> BillingAccessTargetV1 | CloudBudgetAuthority:
    """M04 half of M05's transaction fence; composition must also check M02."""
    require_budget_run_lease(
        connection,
        request.run_id,
        scheduler_instance_id=scheduler_instance_id,
        fencing_token=fencing_token,
        as_of=as_of,
    )
    row = (
        connection.exec_driver_sql(
            "SELECT * FROM collection_run WHERE run_id=?", (request.run_id.value,)
        )
        .mappings()
        .one()
    )
    target = read_budget_target(connection, request.run_id)
    report = request.payload
    if (
        row["payload_digest"] != request.payload_digest
        or row["target_generation"] != request.target_generation
        or row["capability_id"] != request.capability_id
        or row["payload_schema"] != request.payload_schema
        or row["outcome_code"] != request.terminal_state
        or row["source_id"] != report.source_id
        or row["source_id"] != request.provenance.source_id
        or row["adapter_version"] != request.provenance.adapter_version
        or row["provider_key"] != report.subject.provider_key
        or row["account_id"] != report.subject.account_id.value
        or row["resource_id"] != report.subject.resource_id.value
        or row["provider_target_kind"] != report.subject.provider_target.target_kind
        or row["provider_target_id"] != report.subject.provider_target.target_id.value
        or datetime.fromisoformat(str(row["deadline_at"])) <= as_of
    ):
        raise BudgetCollectionError("budget_commit_run_mismatch")
    require_budget_run_authority(target, dict(row))
    require_budget_report_authority(target, report)
    return target


def budget_target_matches_query(
    target: BillingAccessTargetV1 | CloudBudgetAuthority,
    account_id: OpaqueIdV1,
    resource_id: OpaqueIdV1,
    scope_generation: int,
    report_context: CloudBudgetReportContextV1 | None = None,
) -> bool:
    """Match captured financial identity; key generation never becomes scope epoch."""
    if isinstance(target, BillingAccessTargetV1):
        return (
            target.connection.account_id == account_id
            and target.connection.resource_id == resource_id
            and target.connection.scope_generation == scope_generation
            and report_context is None
        )
    graph, _, context = target
    return (
        graph.account_id == account_id
        and graph.resource_id == resource_id
        and scope_generation == 1
        and (report_context is None or context == report_context)
    )


def require_budget_run_authority(
    target: BillingAccessTargetV1 | CloudBudgetAuthority,
    raw: Mapping[str, object],
) -> None:
    """Keep stored run identity tied to its captured graph, including profile."""
    if isinstance(target, BillingAccessTargetV1):
        matches = (
            raw.get("account_id") == target.connection.account_id.value
            and raw.get("resource_id") == target.connection.resource_id.value
            and raw.get("target_generation") == target.binding.generation
            and raw.get("profile_id") is None
        )
    else:
        graph, service, _ = target
        matches = (
            raw.get("account_id") == graph.account_id.value
            and raw.get("resource_id") == graph.resource_id.value
            and raw.get("profile_id") == graph.profile_id.value
            and raw.get("target_generation") == graph.binding.generation
            and raw.get("provider_key") == service.provider_key
            and raw.get("provider_target_kind") == service.target_kind
            and raw.get("provider_target_id") == service.access_target_id.value
            and raw.get("source_id") == "ollama.cloud.usage.v1"
            and raw.get("capability_id") == "api.usage"
        )
    if not matches:
        raise BudgetCollectionError("budget_commit_run_mismatch")


def require_budget_report_authority(
    target: BillingAccessTargetV1 | CloudBudgetAuthority, report: BudgetReportInputV1
) -> None:
    """Pure exact captured-authority policy; current M02 access remains separate."""
    if isinstance(target, BillingAccessTargetV1):
        matches = (
            report.binding_id == target.binding.binding_id
            and report.binding_generation == target.binding.generation
            and report.scope_generation == target.connection.scope_generation
            and (report.scope_id.value if report.scope_id else None)
            == target.connection.scope_id
            and report.scope_evidence == target.connection.scope_evidence
        )
    else:
        graph, service, context = target
        matches = (
            report.subject.provider_key == service.provider_key
            and report.subject.account_id == graph.account_id
            and report.subject.resource_id == graph.resource_id
            and report.subject.provider_target.target_kind == service.target_kind
            and report.subject.provider_target.target_id == service.access_target_id
            and report.binding_id == graph.binding.binding_id
            and report.binding_generation == graph.binding.generation
            and report.scope_generation == 1
            and report.scope_id is None
            and report.scope_evidence == "unresolved"
            and report.source_id == "ollama.cloud.usage.v1"
            and report.source_category == context.scope + "_requests_and_cost"
            and report.requested_period.start == context.interval_start
            and report.requested_period.end == context.interval_end
        )
    if not matches:
        raise BudgetCollectionError("budget_commit_run_mismatch")


def require_budget_commit_authority(
    connection: Connection,
    request: BudgetCollectionInputV1,
    *,
    scheduler_instance_id: OpaqueIdV1,
    fencing_token: int,
    as_of: datetime,
) -> BillingAccessTargetV1:
    target = _require_budget_commit_authority(
        connection,
        request,
        scheduler_instance_id=scheduler_instance_id,
        fencing_token=fencing_token,
        as_of=as_of,
    )
    if not isinstance(target, BillingAccessTargetV1):
        raise BudgetCollectionError("budget_commit_run_mismatch")
    return target


def require_cloud_budget_commit_authority(
    connection: Connection,
    request: BudgetCollectionInputV1,
    *,
    scheduler_instance_id: OpaqueIdV1,
    fencing_token: int,
    as_of: datetime,
) -> CloudBudgetAuthority:
    target = _require_budget_commit_authority(
        connection,
        request,
        scheduler_instance_id=scheduler_instance_id,
        fencing_token=fencing_token,
        as_of=as_of,
    )
    if isinstance(target, BillingAccessTargetV1):
        raise BudgetCollectionError("budget_commit_run_mismatch")
    return target
