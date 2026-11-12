"""Compose one bounded Anthropic cost report with published M02--M05 types."""

import hashlib
from dataclasses import fields
from datetime import datetime, timedelta
from typing import Literal

from agentmonitor.adapters.providers.claude.anthropic_api.manifest import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    EVIDENCE_REFERENCE,
    build_anthropic_cost_manifest,
)
from agentmonitor.adapters.providers.claude.anthropic_api.policy import (
    API_VERSION,
    COST_BASIS,
    MAX_REQUESTS,
    REPORT_SECONDS,
    SOURCE_ID,
    AnthropicCostRequestV1,
    completed_week,
    validate_period,
)
from agentmonitor.adapters.providers.claude.anthropic_api.source import (
    AnthropicCostResultV1,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetCollectionInputV1,
    BudgetPeriodV1,
    BudgetReportInputV1,
    CapacitySubjectV2,
)
from agentmonitor.contracts.collection_control_v1 import (
    BillingBudgetReportContextV1,
    BudgetCollectionRunAdmissionV1,
    BudgetCollectionRunAdmissionV2,
    CollectionFailedV1,
    CollectionTriggerV1,
)
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    CollectionOutcomeV1,
    FailureOutcomeStateV1,
    MissingFieldV1,
    RetryAdviceV1,
    SanitizedWarningV1,
)
from agentmonitor.contracts.registry_billing_v1 import BillingAccessTargetV1
from agentmonitor.contracts.registry_v1 import (
    ProviderAccessTargetV1,
    ProviderTargetRefV1,
)
from agentmonitor.modules.capacity.application.budget_commit import (
    budget_report_payload_digest,
)
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)

ANTHROPIC_COST_OPERATION_FAMILY_V1 = "billing.anthropic.cost.7d"
ANTHROPIC_COST_30D_OPERATION_FAMILY_V1 = "billing.anthropic.cost.30d"
ANTHROPIC_COST_BUDGET_POLICY_ID_V1 = "anthropic-cost-report-requests-v1"
ANTHROPIC_COST_BUDGET_POLICY_VERSION_V1 = "1.0.0"
ANTHROPIC_COST_COLLECTION_POLICY_VERSION_V1 = "1.1.0"
_CAPABILITY_ID = "api.cost"
_CAPABILITY_SCHEMA_VERSION = "2.0.0"
_PAYLOAD_SCHEMA = "budget.report.v1"
_PROTOCOL_VERSION = "1.0.0"
_LEASE_POLICY_VERSION = "1.0.0"
_AUTHORITY_ID = "anthropic.analytics"


def _digest(*values: str) -> str:
    return hashlib.sha256("\0".join(values).encode("utf-8")).hexdigest()


def anthropic_cost_manifest_fingerprint() -> str:
    """Bind M03's catalog identity to M04/M02's SHA-256 audit field."""
    return _digest(
        "provider-manifest-fingerprint-v1",
        get_manifest_fingerprint_v1(build_anthropic_cost_manifest()),
    )


def anthropic_billing_budget_limit(policy_id: str, version: str) -> int:
    """Resolve only the reviewed twenty-request report reservation."""
    if (
        policy_id != ANTHROPIC_COST_BUDGET_POLICY_ID_V1
        or version != ANTHROPIC_COST_BUDGET_POLICY_VERSION_V1
    ):
        raise ValueError("anthropic_billing_budget_policy_unknown")
    return MAX_REQUESTS


def _target_digest(
    target: BillingAccessTargetV1, provider_target: ProviderTargetRefV1
) -> str:
    connection = target.connection
    return _digest(
        "anthropic-cost-target-v1",
        provider_target.target_kind,
        provider_target.target_id.value,
        connection.account_id.value,
        connection.resource_id.value,
        connection.provider_key,
        connection.scope_id or "",
        connection.scope_evidence,
        str(connection.scope_generation),
        connection.monitoring_preference,
        connection.lifecycle,
        str(connection.record_version),
        str(connection.registry_revision),
        target.binding.binding_id.value,
        str(target.binding.generation),
        target.purpose,
    )


def anthropic_billing_budget_scope_digest(
    target: BillingAccessTargetV1, provider_target: ProviderTargetRefV1
) -> str:
    connection = target.connection
    return _digest(
        "anthropic-cost-budget-scope-v1",
        provider_target.target_id.value,
        connection.scope_id or connection.resource_id.value,
        str(connection.scope_generation),
    )


def _report_period(
    requested_at: datetime, context: BillingBudgetReportContextV1 | None
) -> BudgetPeriodV1:
    if context is None:
        return completed_week(requested_at)
    if (
        not isinstance(context, BillingBudgetReportContextV1)
        or context.source_category != "cost"
        or context.grouping != ()
    ):
        raise ValueError("anthropic_billing_run_invalid")
    period = BudgetPeriodV1(context.interval_start, context.interval_end)
    validate_period(period, requested_at)
    return period


def _operation_family(context: BillingBudgetReportContextV1 | None) -> str:
    return (
        ANTHROPIC_COST_30D_OPERATION_FAMILY_V1
        if context is not None and context.range_key == "30d"
        else ANTHROPIC_COST_OPERATION_FAMILY_V1
    )


def _request_digest(
    *,
    target_key_digest: str,
    trigger: CollectionTriggerV1,
    request_principal_id: OpaqueIdV1 | None,
    idempotency_key_digest: str | None,
    requested_at: datetime,
    attempt_ordinal: int,
    report_context: BillingBudgetReportContextV1 | None = None,
) -> str:
    period = _report_period(requested_at, report_context)
    return _digest(
        "anthropic-cost-request-v1"
        if report_context is None
        else "anthropic-cost-request-v2",
        target_key_digest,
        _operation_family(report_context),
        trigger,
        "" if request_principal_id is None else request_principal_id.value,
        idempotency_key_digest or "",
        period.start.isoformat(),
        period.end.isoformat(),
        str(attempt_ordinal),
        *(
            (
                report_context.range_key,
                report_context.source_category,
                *report_context.grouping,
            )
            if report_context is not None
            else ()
        ),
    )


def _budget_window(requested_at: datetime) -> tuple[datetime, datetime]:
    start = requested_at.replace(
        minute=(requested_at.minute // 15) * 15,
        second=0,
        microsecond=0,
    )
    return start, start + timedelta(minutes=15)


def _valid_trigger_authority(
    *,
    target: BillingAccessTargetV1,
    trigger: CollectionTriggerV1,
    request_principal_id: OpaqueIdV1 | None,
    idempotency_key_digest: str | None,
) -> bool:
    if target.purpose == "verification":
        return (
            trigger in {"reauth_verification", "manual"}
            and request_principal_id is not None
            and idempotency_key_digest is not None
        )
    if trigger == "scheduled":
        return request_principal_id is None and idempotency_key_digest is None
    return (
        trigger == "manual"
        and request_principal_id is not None
        and idempotency_key_digest is not None
    )


def build_anthropic_billing_run(
    *,
    target: BillingAccessTargetV1,
    access_target: ProviderAccessTargetV1,
    registry_revision: int,
    scheduler_instance_id: OpaqueIdV1,
    run_id: OpaqueIdV1,
    schedule_id: OpaqueIdV1,
    request_id: OpaqueIdV1,
    retry_chain_id: OpaqueIdV1,
    correlation_id: OpaqueIdV1,
    causation_id: OpaqueIdV1 | None,
    trigger: CollectionTriggerV1,
    request_principal_id: OpaqueIdV1 | None,
    idempotency_key_digest: str | None,
    requested_at: datetime,
    deadline_at: datetime,
    attempt_ordinal: int = 1,
    report_context: BillingBudgetReportContextV1 | None = None,
) -> BudgetCollectionRunAdmissionV1:
    """Capture authority and optional explicit coverage; no context retains V1."""
    fingerprint = anthropic_cost_manifest_fingerprint()
    if (
        not isinstance(target, BillingAccessTargetV1)
        or not isinstance(access_target, ProviderAccessTargetV1)
        or target.connection.provider_key != "claude"
        or access_target.provider_key != "claude"
        or access_target.target_kind != "cloud_service"
        or access_target.authority_id != _AUTHORITY_ID
        or access_target.lifecycle != "active"
        or access_target.manifest_fingerprint != fingerprint
        or type(registry_revision) is not int
        or registry_revision < target.connection.registry_revision
        or not isinstance(requested_at, datetime)
        or not isinstance(deadline_at, datetime)
        or requested_at.utcoffset() != timedelta(0)
        or deadline_at.utcoffset() != timedelta(0)
        or not timedelta(0)
        < deadline_at - requested_at
        <= timedelta(seconds=REPORT_SECONDS)
        or type(attempt_ordinal) is not int
        or attempt_ordinal < 1
        or not _valid_trigger_authority(
            target=target,
            trigger=trigger,
            request_principal_id=request_principal_id,
            idempotency_key_digest=idempotency_key_digest,
        )
    ):
        raise ValueError("anthropic_billing_run_invalid")
    # Validate the completed interval before any durable admission is built.
    _report_period(requested_at, report_context)
    budget_window_start, budget_window_end = _budget_window(requested_at)
    provider_target = ProviderTargetRefV1(
        "cloud_service", access_target.access_target_id
    )
    target_digest = _digest(
        "billing-schedule-target-v2",
        _target_digest(target, provider_target),
        schedule_id.value,
    )
    admission = BudgetCollectionRunAdmissionV1(
        billing_target=target,
        run_id=run_id,
        schedule_id=schedule_id,
        request_id=request_id,
        trigger=trigger,
        operation_family=_operation_family(report_context),
        requested_capability_ids=(_CAPABILITY_ID,),
        capability_set_version=_CAPABILITY_SCHEMA_VERSION,
        request_auth_method=(
            "internal_scheduler" if trigger == "scheduled" else "dashboard_session"
        ),
        request_principal_id=request_principal_id,
        correlation_id=correlation_id,
        causation_id=causation_id,
        target_key_digest=target_digest,
        provider_key="claude",
        provider_target=provider_target,
        account_id=target.connection.account_id,
        profile_id=None,
        resource_id=target.connection.resource_id,
        capability_id=_CAPABILITY_ID,
        source_id=SOURCE_ID,
        adapter_version=ADAPTER_VERSION,
        provider_version=API_VERSION,
        adapter_protocol_version=_PROTOCOL_VERSION,
        manifest_fingerprint=fingerprint,
        collection_policy_version=ANTHROPIC_COST_COLLECTION_POLICY_VERSION_V1,
        registry_revision=registry_revision,
        retry_chain_id=retry_chain_id,
        attempt_ordinal=attempt_ordinal,
        target_generation=target.binding.generation,
        scheduler_instance_id=scheduler_instance_id,
        lease_policy_version=_LEASE_POLICY_VERSION,
        budget_policy_id=ANTHROPIC_COST_BUDGET_POLICY_ID_V1,
        budget_policy_version=ANTHROPIC_COST_BUDGET_POLICY_VERSION_V1,
        budget_scope_digest=anthropic_billing_budget_scope_digest(
            target, provider_target
        ),
        budget_dimension="request",
        budget_unit="count",
        budget_units=MAX_REQUESTS,
        budget_limit_units=MAX_REQUESTS,
        budget_window_start=budget_window_start,
        budget_window_end=budget_window_end,
        payload_schema=_PAYLOAD_SCHEMA,
        idempotency_key_digest=idempotency_key_digest,
        request_digest=_request_digest(
            target_key_digest=_target_digest(target, provider_target),
            trigger=trigger,
            request_principal_id=request_principal_id,
            idempotency_key_digest=idempotency_key_digest,
            requested_at=requested_at,
            attempt_ordinal=attempt_ordinal,
            report_context=report_context,
        ),
        requested_at=requested_at,
        deadline_at=deadline_at,
    )

    if report_context is None:
        return admission
    return BudgetCollectionRunAdmissionV2(
        **{field.name: getattr(admission, field.name) for field in fields(admission)},
        report_context=report_context,
    )


def _require_anthropic_admission(
    admission: BudgetCollectionRunAdmissionV1,
) -> None:
    if not isinstance(admission, BudgetCollectionRunAdmissionV1):
        raise ValueError("anthropic_billing_run_invalid")
    context = (
        admission.report_context
        if isinstance(admission, BudgetCollectionRunAdmissionV2)
        else None
    )
    target = admission.billing_target
    expected_target_digest = _digest(
        "billing-schedule-target-v2",
        _target_digest(target, admission.provider_target),
        admission.schedule_id.value,
    )
    expected_request_digest = _request_digest(
        target_key_digest=_target_digest(target, admission.provider_target),
        trigger=admission.trigger,
        request_principal_id=admission.request_principal_id,
        idempotency_key_digest=admission.idempotency_key_digest,
        requested_at=admission.requested_at,
        attempt_ordinal=admission.attempt_ordinal,
        report_context=context,
    )
    expected_budget_window = _budget_window(admission.requested_at)
    if (
        admission.operation_family != _operation_family(context)
        or admission.requested_capability_ids != (_CAPABILITY_ID,)
        or admission.capability_set_version != _CAPABILITY_SCHEMA_VERSION
        or admission.provider_key != "claude"
        or admission.provider_target.target_kind != "cloud_service"
        or admission.account_id != target.connection.account_id
        or admission.profile_id is not None
        or admission.resource_id != target.connection.resource_id
        or admission.capability_id != _CAPABILITY_ID
        or admission.source_id != SOURCE_ID
        or admission.adapter_version != ADAPTER_VERSION
        or admission.provider_version != API_VERSION
        or admission.adapter_protocol_version != _PROTOCOL_VERSION
        or admission.manifest_fingerprint != anthropic_cost_manifest_fingerprint()
        or admission.collection_policy_version
        != ANTHROPIC_COST_COLLECTION_POLICY_VERSION_V1
        or admission.registry_revision < target.connection.registry_revision
        or admission.target_generation != target.binding.generation
        or admission.lease_policy_version != _LEASE_POLICY_VERSION
        or admission.budget_policy_id != ANTHROPIC_COST_BUDGET_POLICY_ID_V1
        or admission.budget_policy_version != ANTHROPIC_COST_BUDGET_POLICY_VERSION_V1
        or admission.budget_scope_digest
        != anthropic_billing_budget_scope_digest(target, admission.provider_target)
        or admission.budget_dimension != "request"
        or admission.budget_unit != "count"
        or admission.budget_units != MAX_REQUESTS
        or admission.budget_limit_units != MAX_REQUESTS
        or (
            admission.budget_window_start,
            admission.budget_window_end,
        )
        != expected_budget_window
        or admission.payload_schema != _PAYLOAD_SCHEMA
        or admission.target_key_digest != expected_target_digest
        or admission.request_digest != expected_request_digest
        or admission.requested_at.utcoffset() != timedelta(0)
        or admission.deadline_at.utcoffset() != timedelta(0)
        or not timedelta(0)
        < admission.deadline_at - admission.requested_at
        <= timedelta(seconds=REPORT_SECONDS)
        or admission.request_auth_method
        != (
            "internal_scheduler"
            if admission.trigger == "scheduled"
            else "dashboard_session"
        )
        or not _valid_trigger_authority(
            target=target,
            trigger=admission.trigger,
            request_principal_id=admission.request_principal_id,
            idempotency_key_digest=admission.idempotency_key_digest,
        )
    ):
        raise ValueError("anthropic_billing_run_invalid")


def anthropic_billing_request(
    admission: BudgetCollectionRunAdmissionV1,
) -> AnthropicCostRequestV1:
    """Reconstruct the exact source request from persisted M04 run fields."""
    _require_anthropic_admission(admission)
    target = admission.billing_target
    connection = target.connection
    return AnthropicCostRequestV1(
        subject=CapacitySubjectV2(
            provider_key="claude",
            provider_target=admission.provider_target,
            account_id=connection.account_id,
            resource_id=connection.resource_id,
        ),
        binding=target.binding,
        scope_id=(
            None if connection.scope_id is None else OpaqueIdV1(connection.scope_id)
        ),
        scope_evidence=connection.scope_evidence,
        scope_generation=connection.scope_generation,
        period=_report_period(
            admission.requested_at,
            admission.report_context
            if isinstance(admission, BudgetCollectionRunAdmissionV2)
            else None,
        ),
        requested_at=admission.requested_at,
    )


def _result_valid(
    request: AnthropicCostRequestV1,
    result: AnthropicCostResultV1,
    completed_at: datetime,
) -> bool:
    if (
        type(result) is not AnthropicCostResultV1
        or type(result.requests_made) is not int
        or not 0 <= result.requests_made <= MAX_REQUESTS
        or result.http_status is not None
        and (
            type(result.http_status) is not int or not 100 <= result.http_status <= 599
        )
        or result.retry_after_seconds is not None
        and (
            type(result.retry_after_seconds) is not int
            or not 0 <= result.retry_after_seconds <= 2**63 - 1
        )
        or completed_at.utcoffset() != timedelta(0)
    ):
        return False
    if result.state in {"success", "partial"}:
        report = result.report
        return (
            result.http_status == 200
            and report is not None
            and report.subject == request.subject
            and report.binding_id == request.binding.binding_id
            and report.binding_generation == request.binding.generation
            and report.scope_generation == request.scope_generation
            and report.scope_id == request.scope_id
            and report.scope_evidence == request.scope_evidence
            and report.source_id == SOURCE_ID
            and report.source_category == "cost"
            and report.cost_basis == COST_BASIS
            and report.grouping == ()
            and report.requested_period == request.period
            and report.currency == "USD"
            and report.usage_buckets == ()
            and request.requested_at <= report.collected_at <= completed_at
            and (result.state == "success")
            == (
                report.completeness == "complete"
                and report.covered_period == report.requested_period
            )
        )
    return result.report is None


def _provenance(
    admission: BudgetCollectionRunAdmissionV1,
    report: BudgetReportInputV1,
) -> ObservationProvenanceV1:
    observed = report.source_data_through
    availability = FieldAvailabilityV1(
        "available" if observed is not None else "unknown"
    )
    return ObservationProvenanceV1(
        provider_key="claude",
        capability_id=_CAPABILITY_ID,
        capability_schema_version=_CAPABILITY_SCHEMA_VERSION,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        provider_protocol_version=_PROTOCOL_VERSION,
        source_id=SOURCE_ID,
        source_class="documented_api",
        mechanism_version=API_VERSION,
        parser_version=ADAPTER_VERSION,
        provider_version=API_VERSION,
        provider_version_availability=FieldAvailabilityV1("available"),
        observed_at=observed,
        observed_at_availability=availability,
        collected_at=report.collected_at,
        freshness_deadline=None,
        freshness_availability=FieldAvailabilityV1("unknown"),
        freshness_policy_id="anthropic_cost_source_watermark_v1",
        precision="exact",
        confidence="confirmed",
        confidence_reason_code="provider_reported_cost",
        value_kind="provider_reported",
        is_experimental=True,
        fallback_lineage=(),
        warnings=report.omission_codes,
        operation_id=admission.run_id,
        correlation_id=admission.correlation_id,
        decision_reference=EVIDENCE_REFERENCE,
        derivation_method=None,
        input_observation_ids=(),
    )


def _failure(
    state: FailureOutcomeStateV1, code: str, retry: RetryAdviceV1
) -> CollectionOutcomeV1[BudgetReportInputV1]:
    return CollectionOutcomeV1.failure(state=state, code=code, retry=retry)


def _map_failure(
    result: AnthropicCostResultV1,
) -> CollectionOutcomeV1[BudgetReportInputV1]:
    if result.state == "authorization_unavailable":
        return _failure(
            "blocked_user_action_required",
            "anthropic_cost_authorization_unavailable",
            RetryAdviceV1("after_user_action"),
        )
    if result.state == "unauthorized":
        return _failure(
            "reauthentication_required",
            "anthropic_cost_unauthorized",
            RetryAdviceV1("after_reauthentication"),
        )
    if result.state == "access_denied":
        return _failure(
            "authorization_insufficient",
            "anthropic_cost_access_denied",
            RetryAdviceV1("after_user_action"),
        )
    if result.state == "rate_limited":
        exact = (
            result.retry_after_seconds is not None and result.retry_after_seconds > 0
        )
        return _failure(
            "rate_limited",
            "anthropic_cost_rate_limited",
            RetryAdviceV1(
                "after_delay",
                result.retry_after_seconds if exact else 60,
                "exact" if exact else "estimated",
            ),
        )
    if result.state == "provider_unavailable":
        return _failure(
            "provider_unavailable",
            "anthropic_cost_provider_unavailable",
            RetryAdviceV1("after_delay", 60, "estimated"),
        )
    if result.state in {"unexpected_response", "invalid_provider_data"}:
        return _failure(
            "invalid_provider_data",
            "anthropic_cost_data_invalid",
            RetryAdviceV1("after_version_review"),
        )
    if result.state == "deadline_exceeded":
        return _failure(
            "deadline_exceeded",
            "anthropic_cost_deadline_exceeded",
            RetryAdviceV1("unknown"),
        )
    if result.state == "worker_required":
        return _failure(
            "internal_adapter_error",
            "anthropic_cost_dedicated_worker_required",
            RetryAdviceV1("never"),
        )
    return _failure(
        "internal_adapter_error",
        "anthropic_cost_internal_error",
        RetryAdviceV1("never"),
    )


def anthropic_billing_outcome(
    admission: BudgetCollectionRunAdmissionV1,
    result: AnthropicCostResultV1,
    completed_at: datetime,
) -> CollectionOutcomeV1[BudgetReportInputV1]:
    """Map one safe adapter result into the closed provider outcome contract."""
    request = anthropic_billing_request(admission)
    if not isinstance(completed_at, datetime) or completed_at < admission.requested_at:
        raise ValueError("anthropic_billing_completion_invalid")
    if completed_at > admission.deadline_at:
        return _failure(
            "deadline_exceeded",
            "anthropic_cost_deadline_exceeded",
            RetryAdviceV1("unknown"),
        )
    if not _result_valid(request, result, completed_at):
        return _failure(
            "internal_adapter_error",
            "anthropic_cost_result_invalid",
            RetryAdviceV1("never"),
        )
    if result.state not in {"success", "partial"}:
        return _map_failure(result)
    assert result.report is not None
    provenance = _provenance(admission, result.report)
    if result.state == "success":
        return CollectionOutcomeV1.success(result.report, provenance)
    omissions = tuple(
        MissingFieldV1(
            code,
            FieldAvailabilityV1(
                "unknown"
                if result.report.source_data_through is None
                else "unavailable"
            ),
        )
        for code in result.report.omission_codes
    )
    return CollectionOutcomeV1.partial(
        result.report,
        omissions=omissions,
        warnings=tuple(SanitizedWarningV1(item.code) for item in omissions),
        provenance=provenance,
    )


def normalize_anthropic_billing_outcome(
    admission: BudgetCollectionRunAdmissionV1,
    outcome: CollectionOutcomeV1[BudgetReportInputV1],
    completed_at: datetime,
) -> BudgetCollectionInputV1 | CollectionFailedV1:
    """Prepare one exact M05 commit or one sanitized M04 terminal failure."""
    request = anthropic_billing_request(admission)
    if not isinstance(completed_at, datetime) or completed_at.utcoffset() != timedelta(
        0
    ):
        raise ValueError("anthropic_billing_completion_invalid")
    if outcome.state not in {"success", "partial"}:
        if outcome.error is None:
            raise ValueError("anthropic_billing_outcome_invalid")
        terminal: Literal["failed", "blocked", "unsupported"] = (
            "unsupported"
            if outcome.state == "unsupported"
            else "blocked"
            if outcome.state
            in {
                "unverified_provider_version",
                "reauthentication_required",
                "authorization_insufficient",
                "invalid_provider_data",
                "blocked_user_action_required",
            }
            else "failed"
        )
        return CollectionFailedV1(
            admission.run_id, terminal, outcome.error.code, completed_at
        )
    report = outcome.value
    if (
        not isinstance(report, BudgetReportInputV1)
        or report.requested_period != request.period
        or outcome.provenance != _provenance(admission, report)
        or (outcome.state == "success")
        != (
            report.completeness == "complete"
            and report.covered_period == report.requested_period
        )
    ):
        raise ValueError("anthropic_billing_outcome_invalid")
    return BudgetCollectionInputV1(
        run_id=admission.run_id,
        target_generation=admission.target_generation,
        capability_id=admission.capability_id,
        payload_schema=admission.payload_schema,
        payload_digest=budget_report_payload_digest(report),
        terminal_state="succeeded" if outcome.state == "success" else "partial",
        payload=report,
        provenance=outcome.provenance,
    )
