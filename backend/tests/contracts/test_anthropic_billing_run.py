"""Pure composition checks for one bounded Anthropic cost report run."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

import pytest
from agentmonitor.adapters.providers.claude.anthropic_api.manifest import (
    ADAPTER_ID,
    ADAPTER_VERSION,
)
from agentmonitor.adapters.providers.claude.anthropic_api.policy import (
    API_VERSION,
    COST_BASIS,
    SOURCE_ID,
)
from agentmonitor.adapters.providers.claude.anthropic_api.source import (
    AnthropicCostResultV1,
)
from agentmonitor.composition.billing_run import (
    ANTHROPIC_COST_BUDGET_POLICY_ID_V1,
    ANTHROPIC_COST_BUDGET_POLICY_VERSION_V1,
    ANTHROPIC_COST_OPERATION_FAMILY_V1,
    anthropic_billing_budget_limit,
    anthropic_billing_outcome,
    anthropic_billing_request,
    anthropic_cost_manifest_fingerprint,
    build_anthropic_billing_run,
    normalize_anthropic_billing_outcome,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetCollectionInputV1,
    BudgetCostBucketV1,
    BudgetReportInputV1,
)
from agentmonitor.contracts.collection_control_v1 import (
    BudgetCollectionRunAdmissionV1,
    CollectionFailedV1,
    CollectionTriggerV1,
)
from agentmonitor.contracts.common_quantity_v1 import (
    CanonicalDecimalV1,
    ExactMoneyV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import (
    BillingAccessPurposeV1,
    BillingAccessTargetV1,
    BillingConnectionViewV1,
)
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    ProviderAccessTargetV1,
)
from agentmonitor.modules.capacity.application.budget_commit import (
    budget_report_payload_digest,
)

NOW = datetime(2026, 11, 11, 12, tzinfo=UTC)
ACCESS_TARGET_ID = OpaqueIdV1("amat_" + "2" * 32)


def _access_target() -> ProviderAccessTargetV1:
    return ProviderAccessTargetV1(
        access_target_id=ACCESS_TARGET_ID,
        provider_key="claude",
        target_kind="cloud_service",
        authority_id="anthropic.analytics",
        manifest_fingerprint=anthropic_cost_manifest_fingerprint(),
        lifecycle="active",
        record_version=2,
    )


def _target(
    *, purpose: BillingAccessPurposeV1 = "verification"
) -> BillingAccessTargetV1:
    monitoring = purpose == "monitoring"
    return BillingAccessTargetV1(
        connection=BillingConnectionViewV1(
            account_id=OpaqueIdV1("account-1"),
            resource_id=OpaqueIdV1("resource-1"),
            provider_key="claude",
            scope_id="org-1",
            scope_evidence="owner_asserted",
            scope_generation=3,
            monitoring_preference="enabled" if monitoring else "disabled",
            lifecycle="active" if monitoring else "pending",
            record_version=5,
            registry_revision=10,
            created_at=NOW - timedelta(days=1),
            updated_at=NOW - timedelta(hours=1),
        ),
        binding=ActiveCredentialBindingRefV1(
            OpaqueIdV1("account-1"), OpaqueIdV1("amcb_" + "a" * 32), 7
        ),
        purpose=purpose,
    )


def _admission(
    *, purpose: BillingAccessPurposeV1 = "verification"
) -> BudgetCollectionRunAdmissionV1:
    trigger: CollectionTriggerV1 = (
        "reauth_verification" if purpose == "verification" else "scheduled"
    )
    return build_anthropic_billing_run(
        target=_target(purpose=purpose),
        access_target=_access_target(),
        registry_revision=11,
        scheduler_instance_id=OpaqueIdV1("scheduler-1"),
        run_id=OpaqueIdV1("run-1"),
        schedule_id=OpaqueIdV1("schedule-1"),
        request_id=OpaqueIdV1("request-1"),
        retry_chain_id=OpaqueIdV1("retry-1"),
        correlation_id=OpaqueIdV1("correlation-1"),
        causation_id=None,
        trigger=trigger,
        request_principal_id=(
            OpaqueIdV1("principal-1") if purpose == "verification" else None
        ),
        idempotency_key_digest=("1" * 64 if purpose == "verification" else None),
        requested_at=NOW,
        deadline_at=NOW + timedelta(seconds=120),
    )


def _report(
    *,
    complete: bool = True,
    source_data_through: datetime | None = None,
) -> BudgetReportInputV1:
    request = anthropic_billing_request(_admission())
    period = request.period
    if source_data_through is None and complete:
        source_data_through = period.end
    bucket = BudgetCostBucketV1(
        bucket_key="daily_" + period.start.strftime("%Y%m%d"),
        period=replace(period, end=period.start + timedelta(days=1)),
        amount=ExactMoneyV1(CanonicalDecimalV1.from_decimal(Decimal("1.25")), "USD"),
        dimensions=(),
        kind="charge",
    )
    return BudgetReportInputV1(
        subject=request.subject,
        binding_id=request.binding.binding_id,
        binding_generation=request.binding.generation,
        scope_generation=request.scope_generation,
        scope_id=request.scope_id,
        scope_evidence=request.scope_evidence,
        source_id=SOURCE_ID,
        source_category="cost",
        cost_basis=COST_BASIS,
        grouping=(),
        requested_period=period,
        covered_period=period if complete else None,
        source_data_through=source_data_through,
        collected_at=NOW + timedelta(seconds=2),
        completeness="complete" if complete else "unknown",
        omission_codes=() if complete else ("provider_data_not_ready",),
        currency="USD",
        empty_means_zero=complete,
        cost_buckets=(bucket,) if complete or source_data_through is not None else (),
        usage_buckets=(),
    )


def test_closed_request_budget_policy_admits_only_the_known_pair() -> None:
    assert (
        anthropic_billing_budget_limit(
            ANTHROPIC_COST_BUDGET_POLICY_ID_V1,
            ANTHROPIC_COST_BUDGET_POLICY_VERSION_V1,
        )
        == 20
    )
    for policy_id, version in (
        ("unknown", ANTHROPIC_COST_BUDGET_POLICY_VERSION_V1),
        (ANTHROPIC_COST_BUDGET_POLICY_ID_V1, "2.0.0"),
    ):
        with pytest.raises(ValueError, match="anthropic_billing_budget_policy_unknown"):
            anthropic_billing_budget_limit(policy_id, version)


def test_admission_captures_exact_source_period_and_distinct_generations() -> None:
    admission = _admission()
    request = anthropic_billing_request(admission)
    assert admission.operation_family == ANTHROPIC_COST_OPERATION_FAMILY_V1
    assert admission.capability_id == "api.cost"
    assert admission.source_id == SOURCE_ID
    assert admission.adapter_version == ADAPTER_VERSION
    assert admission.provider_version == API_VERSION
    assert admission.manifest_fingerprint == anthropic_cost_manifest_fingerprint()
    assert admission.target_generation == 7
    assert admission.billing_target.connection.scope_generation == 3
    assert admission.registry_revision == 11
    assert admission.budget_units == admission.budget_limit_units == 20
    assert admission.budget_window_start == datetime(2026, 11, 11, 12, tzinfo=UTC)
    assert admission.budget_window_end == datetime(2026, 11, 11, 12, 15, tzinfo=UTC)
    assert request.period.start == datetime(2026, 11, 4, tzinfo=UTC)
    assert request.period.end == datetime(2026, 11, 11, tzinfo=UTC)
    assert request.subject.provider_target.target_id == ACCESS_TARGET_ID


def test_request_digest_is_stable_for_same_owner_idempotency_replay() -> None:
    first = _admission()
    later = build_anthropic_billing_run(
        target=_target(),
        access_target=_access_target(),
        registry_revision=11,
        scheduler_instance_id=OpaqueIdV1("scheduler-2"),
        run_id=OpaqueIdV1("run-2"),
        schedule_id=OpaqueIdV1("schedule-2"),
        request_id=OpaqueIdV1("request-2"),
        retry_chain_id=OpaqueIdV1("retry-2"),
        correlation_id=OpaqueIdV1("correlation-2"),
        causation_id=None,
        trigger="reauth_verification",
        request_principal_id=OpaqueIdV1("principal-1"),
        idempotency_key_digest="1" * 64,
        requested_at=NOW + timedelta(hours=1),
        deadline_at=NOW + timedelta(hours=1, seconds=120),
    )

    assert later.request_digest == first.request_digest
    assert later.request_id != first.request_id
    assert later.budget_window_start != first.budget_window_start


@pytest.mark.parametrize(
    "purpose,trigger,principal,digest",
    [
        ("verification", "scheduled", None, None),
        ("monitoring", "reauth_verification", OpaqueIdV1("p"), "1" * 64),
        ("monitoring", "manual", None, "1" * 64),
        ("monitoring", "manual", OpaqueIdV1("p"), None),
        ("monitoring", "scheduled", OpaqueIdV1("p"), None),
    ],
)
def test_admission_rejects_trigger_authority_mismatch(
    purpose: BillingAccessPurposeV1,
    trigger: CollectionTriggerV1,
    principal: OpaqueIdV1 | None,
    digest: str | None,
) -> None:
    with pytest.raises(ValueError, match="anthropic_billing_run_invalid"):
        build_anthropic_billing_run(
            target=_target(purpose=purpose),
            access_target=_access_target(),
            registry_revision=11,
            scheduler_instance_id=OpaqueIdV1("scheduler-1"),
            run_id=OpaqueIdV1("run-1"),
            schedule_id=OpaqueIdV1("schedule-1"),
            request_id=OpaqueIdV1("request-1"),
            retry_chain_id=OpaqueIdV1("retry-1"),
            correlation_id=OpaqueIdV1("correlation-1"),
            causation_id=None,
            trigger=trigger,
            request_principal_id=principal,
            idempotency_key_digest=digest,
            requested_at=NOW,
            deadline_at=NOW + timedelta(seconds=120),
        )


def test_success_becomes_exact_m03_outcome_and_m05_commit_envelope() -> None:
    admission = _admission()
    report = _report()
    completed_at = report.collected_at + timedelta(seconds=1)
    outcome = anthropic_billing_outcome(
        admission,
        AnthropicCostResultV1("success", "ignored", report, 1, 200),
        completed_at,
    )
    assert outcome.state == "success"
    assert outcome.value == report
    assert outcome.provenance is not None
    assert outcome.provenance.adapter_id == ADAPTER_ID
    assert outcome.provenance.collected_at == report.collected_at
    assert outcome.provenance.observed_at == report.source_data_through
    normalized = normalize_anthropic_billing_outcome(admission, outcome, completed_at)
    assert isinstance(normalized, BudgetCollectionInputV1)
    assert normalized.payload == report
    assert normalized.payload_digest == budget_report_payload_digest(report)
    assert normalized.target_generation == admission.target_generation
    assert normalized.terminal_state == "succeeded"


def test_partial_unknown_watermark_stays_partial_and_unknown() -> None:
    admission = _admission()
    report = _report(complete=False, source_data_through=None)
    completed_at = report.collected_at + timedelta(seconds=1)
    outcome = anthropic_billing_outcome(
        admission,
        AnthropicCostResultV1("partial", "anthropic_cost_partial", report, 1, 200),
        completed_at,
    )
    assert outcome.state == "partial"
    assert tuple(item.code for item in outcome.omissions) == (
        "provider_data_not_ready",
    )
    assert outcome.provenance is not None
    assert outcome.provenance.observed_at is None
    assert outcome.provenance.observed_at_availability.state == "unknown"
    normalized = normalize_anthropic_billing_outcome(admission, outcome, completed_at)
    assert isinstance(normalized, BudgetCollectionInputV1)
    assert normalized.terminal_state == "partial"


@pytest.mark.parametrize(
    "source_state,expected_state,disposition,terminal",
    [
        (
            "authorization_unavailable",
            "blocked_user_action_required",
            "after_user_action",
            "blocked",
        ),
        (
            "unauthorized",
            "reauthentication_required",
            "after_reauthentication",
            "blocked",
        ),
        ("access_denied", "authorization_insufficient", "after_user_action", "blocked"),
        ("rate_limited", "rate_limited", "after_delay", "failed"),
        ("provider_unavailable", "provider_unavailable", "after_delay", "failed"),
        (
            "unexpected_response",
            "invalid_provider_data",
            "after_version_review",
            "blocked",
        ),
        (
            "invalid_provider_data",
            "invalid_provider_data",
            "after_version_review",
            "blocked",
        ),
        ("deadline_exceeded", "deadline_exceeded", "unknown", "failed"),
        ("worker_required", "internal_adapter_error", "never", "failed"),
        ("internal_error", "internal_adapter_error", "never", "failed"),
    ],
)
def test_closed_source_failures_map_without_exposing_source_reason(
    source_state: str,
    expected_state: str,
    disposition: str,
    terminal: Literal["failed", "blocked"],
) -> None:
    admission = _admission()
    completed_at = NOW + timedelta(seconds=3)
    outcome = anthropic_billing_outcome(
        admission,
        AnthropicCostResultV1(
            source_state,  # type: ignore[arg-type]  # Runtime-hostile pure boundary.
            "must_not_escape",
            None,
            1,
            429 if source_state == "rate_limited" else None,
            17 if source_state == "rate_limited" else None,
        ),
        completed_at,
    )
    assert outcome.state == expected_state
    assert outcome.error is not None
    assert outcome.error.code != "must_not_escape"
    assert outcome.error.retry.disposition == disposition
    failed = normalize_anthropic_billing_outcome(admission, outcome, completed_at)
    assert isinstance(failed, CollectionFailedV1)
    assert failed.terminal_state == terminal


def test_success_with_changed_report_identity_fails_closed() -> None:
    admission = _admission()
    report = _report()
    changed = replace(report, binding_generation=report.binding_generation + 1)
    outcome = anthropic_billing_outcome(
        admission,
        AnthropicCostResultV1("success", "ignored", changed, 1, 200),
        report.collected_at + timedelta(seconds=1),
    )
    assert outcome.state == "internal_adapter_error"
    assert outcome.error is not None
    assert outcome.error.code == "anthropic_cost_result_invalid"
