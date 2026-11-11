"""Normalize one bounded Ollama usage result against its admitted report intent."""

from datetime import datetime, timedelta
from typing import Literal

from agentmonitor.adapters.providers.ollama.api.manifest import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    EVIDENCE_REFERENCE,
    PROVIDER_VERSION,
)
from agentmonitor.adapters.providers.ollama.api.policy import (
    COST_BASIS,
    MAX_REQUESTS,
    SOURCE_ID,
)
from agentmonitor.adapters.providers.ollama.api.source import OllamaUsageResultV1
from agentmonitor.contracts.capacity_v1 import (
    BudgetCollectionInputV1,
    BudgetPeriodV1,
    BudgetReportInputV1,
    CapacitySubjectV2,
)
from agentmonitor.contracts.collection_control_v1 import (
    CloudBudgetCollectionRunAdmissionV1,
    CollectionFailedV1,
)
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1
from agentmonitor.contracts.provider_system_v1 import (
    CollectionOutcomeV1,
    FailureOutcomeStateV1,
    MissingFieldV1,
    RetryAdviceV1,
    SanitizedWarningV1,
)
from agentmonitor.modules.capacity.application.budget_commit import (
    budget_report_payload_digest,
)


def _require_admission(admission: CloudBudgetCollectionRunAdmissionV1) -> None:
    if (
        not isinstance(admission, CloudBudgetCollectionRunAdmissionV1)
        or admission.adapter_version != ADAPTER_VERSION
        or admission.provider_version != PROVIDER_VERSION
        or admission.adapter_protocol_version != "1.0.0"
        or admission.capability_set_version != "2.0.0"
    ):
        raise ValueError("ollama_usage_run_invalid")


def _require_completion(
    admission: CloudBudgetCollectionRunAdmissionV1, completed_at: datetime
) -> None:
    if (
        not isinstance(completed_at, datetime)
        or completed_at.utcoffset() != timedelta(0)
        or completed_at < admission.requested_at
    ):
        raise ValueError("ollama_usage_completion_invalid")


def _report_valid(
    admission: CloudBudgetCollectionRunAdmissionV1,
    report: BudgetReportInputV1 | None,
    completed_at: datetime,
) -> bool:
    context = admission.report_context
    period = BudgetPeriodV1(context.interval_start, context.interval_end)
    if not isinstance(report, BudgetReportInputV1):
        return False
    return (
        report.subject
        == CapacitySubjectV2(
            "ollama",
            admission.provider_target,
            admission.cloud_target.account_id,
            admission.cloud_target.resource_id,
        )
        and report.binding_id == admission.cloud_target.binding.binding_id
        and report.binding_generation == admission.target_generation
        and report.scope_generation == 1
        and report.scope_id is None
        and report.scope_evidence == "unresolved"
        and report.source_id == SOURCE_ID
        and report.source_category == context.scope + "_requests_and_cost"
        and report.cost_basis == COST_BASIS
        and report.grouping == ()
        and report.requested_period == period
        and report.covered_period == period
        and report.source_data_through is None
        and admission.requested_at
        <= report.collected_at
        <= completed_at
        <= admission.deadline_at
        and report.currency == ("USD" if report.cost_buckets else None)
        and not report.empty_means_zero
        and report.completeness in {"complete", "partial"}
        and (report.completeness != "partial" or bool(report.cost_buckets))
        and report.omission_codes
        == (
            ("cost_not_reported_for_all_buckets",)
            if report.completeness == "partial"
            else ()
        )
    )


def _result_valid(
    admission: CloudBudgetCollectionRunAdmissionV1,
    result: OllamaUsageResultV1,
    completed_at: datetime,
) -> bool:
    if (
        type(result) is not OllamaUsageResultV1
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
    ):
        return False
    if result.state in {"success", "partial"}:
        report = result.report
        if not _report_valid(admission, report, completed_at) or report is None:
            return False
        money = (
            "partial"
            if report.completeness == "partial"
            else "available"
            if report.cost_buckets
            else "not_reported"
        )
        return (
            result.requests_made == 1
            and result.http_status == 200
            and result.money_availability == money
            and (result.state == "success") == (report.completeness == "complete")
        )
    return (
        result.report is None
        and result.money_availability is None
        and result.state
        in {
            "authorization_unavailable",
            "unauthorized",
            "access_denied",
            "rate_limited",
            "provider_unavailable",
            "unexpected_response",
            "invalid_provider_data",
            "deadline_exceeded",
            "worker_required",
            "internal_error",
        }
    )


def _provenance(
    admission: CloudBudgetCollectionRunAdmissionV1, report: BudgetReportInputV1
) -> ObservationProvenanceV1:
    return ObservationProvenanceV1(
        provider_key="ollama",
        capability_id="api.usage",
        capability_schema_version="2.0.0",
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        provider_protocol_version="1.0.0",
        source_id=SOURCE_ID,
        source_class="documented_api",
        mechanism_version=PROVIDER_VERSION,
        parser_version=ADAPTER_VERSION,
        provider_version=None,
        provider_version_availability=FieldAvailabilityV1("unknown"),
        observed_at=None,
        observed_at_availability=FieldAvailabilityV1("unknown"),
        collected_at=report.collected_at,
        freshness_deadline=None,
        freshness_availability=FieldAvailabilityV1("unknown"),
        freshness_policy_id="ollama_usage_source_watermark_v1",
        precision="exact",
        confidence="confirmed",
        confidence_reason_code="provider_reported_usage",
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
    result: OllamaUsageResultV1,
) -> CollectionOutcomeV1[BudgetReportInputV1]:
    if result.state == "authorization_unavailable":
        return _failure(
            "blocked_user_action_required",
            "ollama_usage_authorization_unavailable",
            RetryAdviceV1("after_user_action"),
        )
    if result.state == "unauthorized":
        return _failure(
            "reauthentication_required",
            "ollama_usage_unauthorized",
            RetryAdviceV1("after_reauthentication"),
        )
    if result.state == "access_denied":
        return _failure(
            "authorization_insufficient",
            "ollama_usage_access_denied",
            RetryAdviceV1("after_user_action"),
        )
    if result.state == "rate_limited":
        exact = (
            result.retry_after_seconds is not None and result.retry_after_seconds > 0
        )
        return _failure(
            "rate_limited",
            "ollama_usage_rate_limited",
            RetryAdviceV1(
                "after_delay",
                result.retry_after_seconds if exact else 60,
                "exact" if exact else "estimated",
            ),
        )
    if result.state == "provider_unavailable":
        return _failure(
            "provider_unavailable",
            "ollama_usage_provider_unavailable",
            RetryAdviceV1("after_delay", 60, "estimated"),
        )
    if result.state in {"unexpected_response", "invalid_provider_data"}:
        return _failure(
            "invalid_provider_data",
            "ollama_usage_data_invalid",
            RetryAdviceV1("after_version_review"),
        )
    if result.state == "deadline_exceeded":
        return _failure(
            "deadline_exceeded",
            "ollama_usage_deadline_exceeded",
            RetryAdviceV1("unknown"),
        )
    if result.state == "worker_required":
        return _failure(
            "internal_adapter_error",
            "ollama_usage_dedicated_worker_required",
            RetryAdviceV1("never"),
        )
    return _failure(
        "internal_adapter_error", "ollama_usage_internal_error", RetryAdviceV1("never")
    )


def usage_outcome(
    admission: CloudBudgetCollectionRunAdmissionV1,
    result: OllamaUsageResultV1,
    *,
    completed_at: datetime,
) -> CollectionOutcomeV1[BudgetReportInputV1]:
    """Validate the pinned report and map only fixed, sanitized failure codes."""
    _require_admission(admission)
    _require_completion(admission, completed_at)
    if completed_at > admission.deadline_at:
        return _failure(
            "deadline_exceeded",
            "ollama_usage_deadline_exceeded",
            RetryAdviceV1("unknown"),
        )
    if not _result_valid(admission, result, completed_at):
        return _failure(
            "internal_adapter_error",
            "ollama_usage_result_invalid",
            RetryAdviceV1("never"),
        )
    if result.state not in {"success", "partial"}:
        return _map_failure(result)
    assert result.report is not None
    provenance = _provenance(admission, result.report)
    if result.state == "success":
        return CollectionOutcomeV1.success(result.report, provenance)
    return CollectionOutcomeV1.partial(
        result.report,
        omissions=tuple(
            MissingFieldV1(code, FieldAvailabilityV1("unknown"))
            for code in result.report.omission_codes
        ),
        warnings=tuple(
            SanitizedWarningV1(code) for code in result.report.omission_codes
        ),
        provenance=provenance,
    )


def normalize_usage_report(
    admission: CloudBudgetCollectionRunAdmissionV1,
    outcome: CollectionOutcomeV1[BudgetReportInputV1],
    completed_at: datetime,
) -> BudgetCollectionInputV1 | CollectionFailedV1:
    """Revalidate the outcome before preparing a commit or terminal failure."""
    _require_admission(admission)
    _require_completion(admission, completed_at)
    if outcome.state not in {"success", "partial"}:
        if outcome.error is None:
            raise ValueError("ollama_usage_outcome_invalid")
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
        report is None
        or not _report_valid(admission, report, completed_at)
        or outcome.provenance != _provenance(admission, report)
        or (outcome.state == "success") != (report.completeness == "complete")
        or tuple(item.code for item in outcome.omissions) != report.omission_codes
        or tuple(item.code for item in outcome.warnings) != report.omission_codes
    ):
        raise ValueError("ollama_usage_outcome_invalid")
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
