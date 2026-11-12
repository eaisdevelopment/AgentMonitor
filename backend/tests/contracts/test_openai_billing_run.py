"""Pure composition checks for one bounded OpenAI cost report run."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal, cast

import pytest
from agentmonitor.adapters.providers.codex.openai_api.manifest import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    PROVIDER_VERSION,
)
from agentmonitor.adapters.providers.codex.openai_api.policy import (
    COST_BASIS,
    SOURCE_ID,
)
from agentmonitor.adapters.providers.codex.openai_api.source import (
    OpenAICostResultV1,
)
from agentmonitor.composition.openai_billing_run import (
    OPENAI_COST_BUDGET_POLICY_ID_V1,
    OPENAI_COST_BUDGET_POLICY_VERSION_V1,
    OPENAI_COST_OPERATION_FAMILY_V1,
    build_openai_billing_run,
    normalize_openai_billing_outcome,
    openai_billing_budget_limit,
    openai_billing_outcome,
    openai_billing_request,
    openai_cost_manifest_fingerprint,
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
        provider_key="codex",
        target_kind="cloud_service",
        authority_id="openai.organization",
        manifest_fingerprint=openai_cost_manifest_fingerprint(),
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
            provider_key="codex",
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
    return build_openai_billing_run(
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
    currency: str | None = "GBP",
) -> BudgetReportInputV1:
    request = openai_billing_request(_admission())
    period = request.period
    bucket = BudgetCostBucketV1(
        bucket_key="daily_" + period.start.strftime("%Y%m%d"),
        period=replace(period, end=period.start + timedelta(days=1)),
        amount=ExactMoneyV1(
            CanonicalDecimalV1.from_decimal(Decimal("1.25")), currency or "GBP"
        ),
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
        source_data_through=None,
        collected_at=NOW + timedelta(seconds=2),
        completeness="complete" if complete else "partial",
        omission_codes=() if complete else ("daily_coverage_incomplete",),
        currency=currency,
        empty_means_zero=False,
        cost_buckets=(bucket,) if currency is not None else (),
        usage_buckets=(),
    )


def test_closed_request_budget_policy_admits_only_the_known_pair() -> None:
    assert (
        openai_billing_budget_limit(
            OPENAI_COST_BUDGET_POLICY_ID_V1,
            OPENAI_COST_BUDGET_POLICY_VERSION_V1,
        )
        == 20
    )
    for policy_id, version in (
        ("unknown", OPENAI_COST_BUDGET_POLICY_VERSION_V1),
        (OPENAI_COST_BUDGET_POLICY_ID_V1, "2.0.0"),
    ):
        with pytest.raises(ValueError, match="openai_billing_budget_policy_unknown"):
            openai_billing_budget_limit(policy_id, version)


def test_admission_captures_exact_source_period_and_distinct_generations() -> None:
    admission = _admission()
    request = openai_billing_request(admission)
    assert admission.operation_family == OPENAI_COST_OPERATION_FAMILY_V1
    assert admission.capability_id == "api.cost"
    assert admission.source_id == SOURCE_ID
    assert admission.adapter_version == ADAPTER_VERSION
    assert admission.provider_version == PROVIDER_VERSION
    assert admission.manifest_fingerprint == openai_cost_manifest_fingerprint()
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
    later = build_openai_billing_run(
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
    with pytest.raises(ValueError, match="openai_billing_run_invalid"):
        build_openai_billing_run(
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
    outcome = openai_billing_outcome(
        admission,
        OpenAICostResultV1("success", "ignored", report, 1, 200),
        completed_at,
    )
    assert outcome.state == "success"
    assert outcome.value == report
    assert outcome.provenance is not None
    assert outcome.provenance.adapter_id == ADAPTER_ID
    assert outcome.provenance.collected_at == report.collected_at
    assert outcome.provenance.observed_at == report.source_data_through
    normalized = normalize_openai_billing_outcome(admission, outcome, completed_at)
    assert isinstance(normalized, BudgetCollectionInputV1)
    assert normalized.payload == report
    assert normalized.payload_digest == budget_report_payload_digest(report)
    assert normalized.target_generation == admission.target_generation
    assert normalized.terminal_state == "succeeded"


def test_partial_unknown_watermark_stays_partial_and_unknown() -> None:
    admission = _admission()
    report = _report(complete=False)
    completed_at = report.collected_at + timedelta(seconds=1)
    outcome = openai_billing_outcome(
        admission,
        OpenAICostResultV1("partial", "openai_cost_partial", report, 1, 200),
        completed_at,
    )
    assert outcome.state == "partial"
    assert tuple(item.code for item in outcome.omissions) == (
        "daily_coverage_incomplete",
    )
    assert outcome.provenance is not None
    assert outcome.provenance.observed_at is None
    assert outcome.provenance.observed_at_availability.state == "unknown"
    normalized = normalize_openai_billing_outcome(admission, outcome, completed_at)
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
    outcome = openai_billing_outcome(
        admission,
        OpenAICostResultV1(
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
    failed = normalize_openai_billing_outcome(admission, outcome, completed_at)
    assert isinstance(failed, CollectionFailedV1)
    assert failed.terminal_state == terminal


def test_success_with_changed_report_identity_fails_closed() -> None:
    admission = _admission()
    report = _report()
    changed = replace(report, binding_generation=report.binding_generation + 1)
    outcome = openai_billing_outcome(
        admission,
        OpenAICostResultV1("success", "ignored", changed, 1, 200),
        report.collected_at + timedelta(seconds=1),
    )
    assert outcome.state == "internal_adapter_error"
    assert outcome.error is not None
    assert outcome.error.code == "openai_cost_result_invalid"


def _build(**changes: Any) -> BudgetCollectionRunAdmissionV1:
    values: dict[str, Any] = {
        "target": _target(),
        "access_target": _access_target(),
        "registry_revision": 11,
        "scheduler_instance_id": OpaqueIdV1("scheduler-1"),
        "run_id": OpaqueIdV1("run-1"),
        "schedule_id": OpaqueIdV1("schedule-1"),
        "request_id": OpaqueIdV1("request-1"),
        "retry_chain_id": OpaqueIdV1("retry-1"),
        "correlation_id": OpaqueIdV1("correlation-1"),
        "causation_id": None,
        "trigger": "reauth_verification",
        "request_principal_id": OpaqueIdV1("principal-1"),
        "idempotency_key_digest": "1" * 64,
        "requested_at": NOW,
        "deadline_at": NOW + timedelta(seconds=120),
    }
    return build_openai_billing_run(**(values | changes))


@pytest.mark.parametrize(
    "field,value",
    [
        ("provider_key", "claude"),
        ("authority_id", "other-authority"),
        ("manifest_fingerprint", "f" * 64),
        ("lifecycle", "disabled"),
    ],
)
def test_service_target_requires_exact_openai_authority(field: str, value: Any) -> None:
    with pytest.raises(ValueError, match="openai_billing_run_invalid"):
        _build(access_target=replace(_access_target(), **{field: value}))


@pytest.mark.parametrize("seconds", [0, -1, 121])
def test_admission_cannot_escape_report_deadline(seconds: int) -> None:
    with pytest.raises(ValueError, match="openai_billing_run_invalid"):
        _build(deadline_at=NOW + timedelta(seconds=seconds))


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_id", "different-source"),
        ("manifest_fingerprint", "f" * 64),
        ("target_key_digest", "f" * 64),
        ("request_digest", "f" * 64),
        ("budget_scope_digest", "f" * 64),
        ("collection_policy_version", "2.0.0"),
        ("operation_family", "billing.openai.cost.30d"),
        ("provider_version", "different-version"),
        ("target_generation", 8),
        ("budget_policy_id", "other-policy"),
    ],
)
def test_restored_admission_is_revalidated_before_request(
    field: str, value: Any
) -> None:
    with pytest.raises(ValueError, match="openai_billing_run_invalid"):
        openai_billing_request(replace(_admission(), **{field: value}))


@pytest.mark.parametrize("changed", ["binding_id", "scope_generation", "scope_id"])
def test_restored_target_cannot_change_lineage_without_its_digest(changed: str) -> None:
    admission = _admission()
    target = admission.billing_target
    if changed == "binding_id":
        target = replace(
            target,
            binding=replace(target.binding, binding_id=OpaqueIdV1("amcb_" + "b" * 32)),
        )
    elif changed == "scope_generation":
        target = replace(
            target, connection=replace(target.connection, scope_generation=4)
        )
    else:
        target = replace(
            target, connection=replace(target.connection, scope_id="different-scope")
        )
    with pytest.raises(ValueError, match="openai_billing_run_invalid"):
        openai_billing_request(replace(admission, billing_target=target))


def test_period_is_immutable_from_original_request_not_restart_date() -> None:
    admission = _admission()
    original = openai_billing_request(admission)
    assert openai_billing_request(admission).period == original.period
    later = _build(
        requested_at=NOW + timedelta(days=1),
        deadline_at=NOW + timedelta(days=1, seconds=120),
    )
    assert later.request_digest != admission.request_digest
    assert openai_billing_request(later).period != original.period
    with pytest.raises(ValueError, match="openai_billing_run_invalid"):
        openai_billing_request(
            replace(
                admission,
                requested_at=NOW + timedelta(days=1),
                deadline_at=NOW + timedelta(days=1, seconds=120),
            )
        )


@pytest.mark.parametrize("currency", ["USD", "GBP", "JPY", None])
def test_actual_currency_or_empty_report_stays_exact_without_zero_or_watermark(
    currency: str | None,
) -> None:
    report = _report(currency=currency)
    completed = report.collected_at + timedelta(seconds=1)
    outcome = openai_billing_outcome(
        _admission(),
        OpenAICostResultV1("success", "ignored", report, 1, 200),
        completed,
    )
    assert outcome.state == "success" and outcome.value == report
    assert outcome.provenance is not None
    assert outcome.provenance.observed_at is None
    assert outcome.provenance.observed_at_availability.state == "unknown"
    assert outcome.provenance.freshness_deadline is None
    assert outcome.provenance.freshness_availability.state == "unknown"
    assert outcome.provenance.provider_version is None
    assert outcome.provenance.provider_version_availability.state == "unknown"
    normalized = normalize_openai_billing_outcome(_admission(), outcome, completed)
    assert isinstance(normalized, BudgetCollectionInputV1)
    assert normalized.payload.currency == currency
    assert normalized.payload.empty_means_zero is False
    assert normalized.payload.cost_buckets == report.cost_buckets
    assert normalized.payload_digest == budget_report_payload_digest(report)
    if currency is None:
        assert normalized.payload.cost_buckets == ()


@pytest.mark.parametrize(
    "field,value",
    [
        ("binding_id", OpaqueIdV1("different-binding")),
        ("binding_generation", 9),
        ("scope_generation", 4),
        ("scope_id", OpaqueIdV1("different-scope")),
        ("source_id", "other-source"),
        ("source_category", "other-category"),
        ("cost_basis", "other-basis"),
        ("source_data_through", NOW),
    ],
)
def test_result_identity_or_unadmitted_source_semantics_fail_closed(
    field: str, value: Any
) -> None:
    changed = replace(_report(), **{field: value})
    outcome = openai_billing_outcome(
        _admission(),
        OpenAICostResultV1("success", "ignored", changed, 1, 200),
        NOW + timedelta(seconds=3),
    )
    assert outcome.state == "internal_adapter_error"
    assert (
        outcome.error is not None and outcome.error.code == "openai_cost_result_invalid"
    )


@pytest.mark.parametrize("requests", [0, 21])
def test_success_requires_bounded_actual_request_attempt(requests: int) -> None:
    outcome = openai_billing_outcome(
        _admission(),
        OpenAICostResultV1("success", "ignored", _report(), requests, 200),
        NOW + timedelta(seconds=3),
    )
    assert outcome.state == "internal_adapter_error"


def test_result_after_deadline_cannot_become_report_or_refresh_money() -> None:
    admission = _admission()
    completed = admission.deadline_at + timedelta(seconds=1)
    outcome = openai_billing_outcome(
        admission,
        OpenAICostResultV1("success", "ignored", _report(), 1, 200),
        completed,
    )
    assert outcome.state == "deadline_exceeded" and outcome.value is None
    normalized = normalize_openai_billing_outcome(admission, outcome, completed)
    assert isinstance(normalized, CollectionFailedV1)


@pytest.mark.parametrize(
    "retry,seconds,precision",
    [(17, 17, "exact"), (None, 60, "estimated"), (0, 60, "estimated")],
)
def test_retry_after_remains_explicit_or_uses_labeled_estimate(
    retry: int | None, seconds: int, precision: str
) -> None:
    outcome = openai_billing_outcome(
        _admission(),
        OpenAICostResultV1("rate_limited", "do-not-copy", None, 1, 429, retry),
        NOW + timedelta(seconds=3),
    )
    assert outcome.error is not None
    assert outcome.error.retry.delay_seconds == seconds
    assert outcome.error.retry.delay_precision == precision


@pytest.mark.parametrize("changed", ["binding", "source", "deadline"])
def test_normalization_rechecks_payload_and_deadline_before_receipt(
    changed: str,
) -> None:
    admission = _admission()
    report = _report()
    completed = NOW + timedelta(seconds=3)
    outcome = openai_billing_outcome(
        admission, OpenAICostResultV1("success", "ignored", report, 1, 200), completed
    )
    if changed == "deadline":
        normalized = normalize_openai_billing_outcome(
            admission, outcome, admission.deadline_at + timedelta(seconds=1)
        )
        assert isinstance(normalized, CollectionFailedV1)
        assert normalized.error_code == "openai_cost_deadline_exceeded"
    else:
        report = (
            replace(report, binding_generation=9)
            if changed == "binding"
            else replace(report, source_id="different-source")
        )
        with pytest.raises(ValueError, match="openai_billing_outcome_invalid"):
            normalize_openai_billing_outcome(
                admission, replace(outcome, value=report), completed
            )


def test_unresolved_scope_keeps_distinct_credential_generation() -> None:
    target = _target()
    target = replace(
        target,
        connection=replace(
            target.connection, scope_id=None, scope_evidence="unresolved"
        ),
    )
    request = openai_billing_request(_build(target=target))
    assert request.scope_id is None and request.scope_evidence == "unresolved"
    assert request.scope_generation == 3 and request.binding.generation == 7


def test_signed_exact_cost_is_preserved_without_scaling_or_rounding() -> None:
    report = _report()
    amount = CanonicalDecimalV1("-123456789012345678901234567890123456789", 18)
    bucket = replace(
        report.cost_buckets[0], amount=ExactMoneyV1(amount, "GBP"), kind="adjustment"
    )
    report = replace(report, cost_buckets=(bucket,))
    outcome = openai_billing_outcome(
        _admission(),
        OpenAICostResultV1("success", "ignored", report, 1, 200),
        NOW + timedelta(seconds=3),
    )
    assert outcome.value == report
    assert outcome.value.cost_buckets[0].amount.amount == amount


def test_untyped_result_payload_is_rejected_before_reading_its_fields() -> None:
    result = OpenAICostResultV1(
        "success", "ignored", cast(BudgetReportInputV1, object()), 1, 200
    )
    outcome = openai_billing_outcome(_admission(), result, NOW + timedelta(seconds=3))
    assert outcome.state == "internal_adapter_error"
    assert (
        outcome.error is not None and outcome.error.code == "openai_cost_result_invalid"
    )
