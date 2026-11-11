"""Pure normalized-domain result checks; constructed reports never cross I/O."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from importlib import import_module
from types import ModuleType
from typing import Any, Literal, cast

import pytest
from agentmonitor.adapters.providers.ollama.api.manifest import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    EVIDENCE_REFERENCE,
    PROVIDER_VERSION,
)
from agentmonitor.adapters.providers.ollama.api.policy import COST_BASIS, SOURCE_ID
from agentmonitor.adapters.providers.ollama.api.source import (
    OllamaUsageResultV1,
    State,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetCollectionInputV1,
    BudgetCostBucketV1,
    BudgetPeriodV1,
    BudgetReportInputV1,
    BudgetUsageBucketV1,
    CapacitySubjectV2,
)
from agentmonitor.contracts.collection_control_v1 import (
    CloudBudgetCollectionRunAdmissionV1,
    CollectionFailedV1,
)
from agentmonitor.contracts.common_quantity_v1 import (
    CanonicalDecimalV1,
    ExactMoneyV1,
    ExactQuantityV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import CollectionOutcomeV1
from agentmonitor.modules.capacity.application.budget_commit import (
    budget_report_payload_digest,
    validate_budget_commit,
)

from backend.tests.contracts.test_cloud_budget_run_contract import (
    NOW,
)
from backend.tests.contracts.test_cloud_budget_run_contract import (
    _admission as _cloud_admission,
)


def _module() -> ModuleType:
    try:
        return import_module("agentmonitor.composition.ollama_usage_result")
    except ModuleNotFoundError as error:
        if error.name != "agentmonitor.composition.ollama_usage_result":
            raise
        raise AssertionError("Ollama usage result normalization is absent") from None


def _admission(
    scope: Literal["self", "team"] = "self",
) -> CloudBudgetCollectionRunAdmissionV1:
    run = _cloud_admission()
    return replace(
        run,
        report_context=replace(run.report_context, scope=scope),
        adapter_version=ADAPTER_VERSION,
        provider_version=PROVIDER_VERSION,
        adapter_protocol_version="1.0.0",
        capability_set_version="2.0.0",
    )


def _report(
    admission: CloudBudgetCollectionRunAdmissionV1,
    *,
    money: Literal["available", "not_reported", "partial"] = "available",
) -> BudgetReportInputV1:
    period = BudgetPeriodV1(
        admission.report_context.interval_start, admission.report_context.interval_end
    )
    days = tuple(
        BudgetPeriodV1(
            period.start + timedelta(days=i), period.start + timedelta(days=i + 1)
        )
        for i in range(7)
    )
    costs = tuple(
        BudgetCostBucketV1(
            f"cost-{i}",
            day,
            ExactMoneyV1(CanonicalDecimalV1.from_decimal(Decimal("0.004")), "USD"),
            (),
            "charge",
        )
        for i, day in enumerate(
            days if money == "available" else days[:1] if money == "partial" else ()
        )
    )
    return BudgetReportInputV1(
        subject=CapacitySubjectV2(
            "ollama",
            admission.provider_target,
            admission.cloud_target.account_id,
            admission.cloud_target.resource_id,
        ),
        binding_id=admission.cloud_target.binding.binding_id,
        binding_generation=admission.target_generation,
        scope_generation=1,
        scope_id=None,
        scope_evidence="unresolved",
        source_id=SOURCE_ID,
        source_category=admission.report_context.scope + "_requests_and_cost",
        cost_basis=COST_BASIS,
        grouping=(),
        requested_period=period,
        covered_period=period,
        source_data_through=None,
        collected_at=NOW + timedelta(seconds=2),
        completeness="partial" if money == "partial" else "complete",
        omission_codes=("cost_not_reported_for_all_buckets",)
        if money == "partial"
        else (),
        currency="USD" if costs else None,
        empty_means_zero=False,
        cost_buckets=costs,
        usage_buckets=tuple(
            BudgetUsageBucketV1(
                f"requests-{i}",
                day,
                ExactQuantityV1.from_decimal(Decimal("3"), unit="requests"),
                (),
            )
            for i, day in enumerate(days)
        ),
    )


def _outcome(
    admission: CloudBudgetCollectionRunAdmissionV1, result: OllamaUsageResultV1
) -> CollectionOutcomeV1[BudgetReportInputV1]:
    return cast(
        CollectionOutcomeV1[BudgetReportInputV1],
        _module().usage_outcome(
            admission, result, completed_at=NOW + timedelta(seconds=3)
        ),
    )


@pytest.mark.parametrize("scope", ["self", "team"])
@pytest.mark.parametrize("money", ["available", "not_reported", "partial"])
def test_exact_usage_report_becomes_matching_commit_without_invented_money(
    scope: Literal["self", "team"],
    money: Literal["available", "not_reported", "partial"],
) -> None:
    admission = _admission(scope)
    report = _report(admission, money=money)
    state: State = "partial" if money == "partial" else "success"
    outcome = _outcome(
        admission, OllamaUsageResultV1(state, "ignored", report, 1, money, 200)
    )
    assert outcome.state == state and outcome.value == report
    provenance = outcome.provenance
    assert provenance is not None
    assert provenance.adapter_id == ADAPTER_ID
    assert provenance.adapter_version == ADAPTER_VERSION
    assert provenance.mechanism_version == PROVIDER_VERSION
    assert provenance.decision_reference == EVIDENCE_REFERENCE
    assert provenance.source_id == SOURCE_ID and provenance.is_experimental
    assert provenance.observed_at is None
    assert provenance.observed_at_availability.state == "unknown"
    assert provenance.freshness_deadline is None
    commit = _module().normalize_usage_report(
        admission, outcome, NOW + timedelta(seconds=3)
    )
    assert isinstance(commit, BudgetCollectionInputV1)
    assert commit.payload == report
    assert commit.payload_digest == budget_report_payload_digest(report)
    assert commit.target_generation == admission.target_generation
    assert commit.terminal_state == ("partial" if money == "partial" else "succeeded")
    assert validate_budget_commit(commit)
    if money == "not_reported":
        assert commit.payload.currency is None and commit.payload.cost_buckets == ()
    if money == "partial":
        assert tuple(item.code for item in outcome.omissions) == report.omission_codes


@pytest.mark.parametrize(
    "state,expected,terminal",
    [
        ("authorization_unavailable", "blocked_user_action_required", "blocked"),
        ("unauthorized", "reauthentication_required", "blocked"),
        ("access_denied", "authorization_insufficient", "blocked"),
        ("rate_limited", "rate_limited", "failed"),
        ("provider_unavailable", "provider_unavailable", "failed"),
        ("unexpected_response", "invalid_provider_data", "blocked"),
        ("invalid_provider_data", "invalid_provider_data", "blocked"),
        ("deadline_exceeded", "deadline_exceeded", "failed"),
        ("worker_required", "internal_adapter_error", "failed"),
        ("internal_error", "internal_adapter_error", "failed"),
    ],
)
def test_closed_failure_preserves_terminal_class_without_source_diagnostics(
    state: State, expected: str, terminal: str
) -> None:
    admission = _admission()
    result = OllamaUsageResultV1(
        state,
        "must_not_escape",
        None,
        0 if state == "authorization_unavailable" else 1,
        retry_after_seconds=17 if state == "rate_limited" else None,
    )
    outcome = _outcome(admission, result)
    assert outcome.state == expected and outcome.error is not None
    assert "must_not_escape" not in repr(outcome)
    if state == "rate_limited":
        assert outcome.error.retry.delay_seconds == 17
    failed = _module().normalize_usage_report(
        admission, outcome, NOW + timedelta(seconds=3)
    )
    assert isinstance(failed, CollectionFailedV1)
    assert failed.terminal_state == terminal and failed.run_id == admission.run_id


@pytest.mark.parametrize(
    "changes",
    [
        {"requests_made": 0},
        {"requests_made": 2},
        {"requests_made": -1},
        {"requests_made": True},
        {"http_status": 201},
        {"state": "partial"},
        {"report": None},
        {"money_availability": "not_reported"},
        {"retry_after_seconds": True},
    ],
)
def test_inconsistent_source_success_fails_closed(changes: dict[str, Any]) -> None:
    admission = _admission()
    result = OllamaUsageResultV1(
        "success", "ignored", _report(admission), 1, "available", 200
    )
    outcome = _outcome(admission, replace(result, **changes))
    assert outcome.state == "internal_adapter_error"
    assert (
        outcome.error is not None
        and outcome.error.code == "ollama_usage_result_invalid"
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"source_id": "ollama.cloud.balance.v1"},
        {"source_category": "team_requests_and_cost"},
        {"cost_basis": "another_basis"},
        {"binding_id": OpaqueIdV1("other-binding")},
        {"binding_generation": 99},
        {"scope_generation": 2},
        {"scope_id": OpaqueIdV1("asserted-scope"), "scope_evidence": "owner_asserted"},
        {"collected_at": NOW - timedelta(seconds=1)},
        {"collected_at": NOW + timedelta(seconds=4)},
    ],
)
def test_mismatched_report_authority_or_time_fails_closed(
    changes: dict[str, Any],
) -> None:
    admission = _admission()
    report = replace(_report(admission), **changes)
    outcome = _outcome(
        admission,
        OllamaUsageResultV1("success", "ignored", report, 1, "available", 200),
    )
    assert outcome.state == "internal_adapter_error"


def test_normalization_revalidates_report_and_provenance() -> None:
    admission = _admission()
    report = _report(admission)
    outcome = _outcome(
        admission,
        OllamaUsageResultV1("success", "ignored", report, 1, "available", 200),
    )
    assert outcome.provenance is not None
    for invalid in (
        replace(outcome, value=replace(report, binding_generation=99)),
        replace(
            outcome,
            provenance=replace(
                outcome.provenance, operation_id=OpaqueIdV1("other-run")
            ),
        ),
    ):
        with pytest.raises(ValueError, match="ollama_usage_outcome_invalid"):
            _module().normalize_usage_report(
                admission, invalid, NOW + timedelta(seconds=3)
            )


def test_failure_cannot_smuggle_a_report_and_late_success_cannot_commit() -> None:
    admission = _admission()
    report = _report(admission)
    invalid = _outcome(
        admission, OllamaUsageResultV1("provider_unavailable", "ignored", report, 1)
    )
    assert invalid.state == "internal_adapter_error"
    late = _module().usage_outcome(
        admission,
        OllamaUsageResultV1("success", "ignored", report, 1, "available", 200),
        completed_at=admission.deadline_at + timedelta(seconds=1),
    )
    assert late.state == "deadline_exceeded"


def test_invalid_completion_is_rejected_without_echoing_values() -> None:
    admission = _admission()
    for completed in (NOW - timedelta(seconds=1), NOW.replace(tzinfo=None)):
        with pytest.raises(ValueError, match="ollama_usage_completion_invalid"):
            _module().usage_outcome(
                admission,
                OllamaUsageResultV1("authorization_unavailable", "ignored", None, 0),
                completed_at=completed,
            )


def test_normalization_rejects_partial_money_without_any_cost_bucket() -> None:
    admission = _admission()
    report = _report(admission, money="partial")
    outcome = _outcome(
        admission, OllamaUsageResultV1("partial", "ignored", report, 1, "partial", 200)
    )
    invalid = replace(outcome, value=replace(report, cost_buckets=(), currency=None))
    with pytest.raises(ValueError, match="ollama_usage_outcome_invalid"):
        _module().normalize_usage_report(admission, invalid, NOW + timedelta(seconds=3))
