"""Pure cloud reconstruction and report fences; no DTO enters a database."""

import json
from dataclasses import fields, replace
from datetime import datetime, timedelta
from typing import Any

import pytest
from agentmonitor.adapters.persistence.collection_control.sqlite import budget
from agentmonitor.adapters.persistence.collection_control.sqlite.budget_dispatch import (  # noqa: E501
    restore_budget_admission,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetPeriodV1,
    BudgetReportInputV1,
    CapacitySubjectV2,
)
from agentmonitor.contracts.collection_control_v1 import (
    CloudBudgetCollectionRunAdmissionV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1

from backend.tests.capacity.pure.test_budget_report_selection import _report
from backend.tests.contracts.test_cloud_budget_run_contract import _admission


def _snapshot() -> tuple[CloudBudgetCollectionRunAdmissionV1, dict[str, Any]]:
    admission = _admission()
    raw = {field.name: getattr(admission, field.name) for field in fields(admission)}
    for name, value in tuple(raw.items()):
        if isinstance(value, OpaqueIdV1):
            raw[name] = value.value
        elif isinstance(value, datetime):
            raw[name] = value.isoformat()
    for name in (
        "cloud_target",
        "service_target",
        "report_context",
        "provider_target",
        "budget_limit_units",
    ):
        raw.pop(name)
    raw["provider_target_kind"] = admission.provider_target.target_kind
    raw["provider_target_id"] = admission.provider_target.target_id.value
    raw["requested_capability_ids"] = json.dumps(admission.requested_capability_ids)
    return admission, raw


def test_cloud_reconstruction_retains_profile_context_and_separate_fingerprints() -> (
    None
):
    admission, raw = _snapshot()
    target = admission.cloud_target, admission.service_target, admission.report_context
    restored = restore_budget_admission(raw, target, resolved_budget_limit=1)
    assert restored == admission
    assert restored.profile_id == admission.cloud_target.profile_id
    assert restored.manifest_fingerprint != restored.service_target.manifest_fingerprint


@pytest.mark.parametrize(
    "field,value",
    [
        ("profile_id", None),
        ("profile_id", "another-profile"),
        ("account_id", "another-account"),
        ("resource_id", "another-resource"),
        ("source_id", "ollama.cloud.balance.v1"),
        ("target_generation", 99),
        ("requested_capability_ids", '["subscription.quota"]'),
    ],
)
def test_cloud_reconstruction_rejects_cross_graph_metadata(
    field: str, value: object
) -> None:
    admission, raw = _snapshot()
    raw[field] = value
    with pytest.raises(budget.BudgetCollectionError):
        restore_budget_admission(
            raw,
            (
                admission.cloud_target,
                admission.service_target,
                admission.report_context,
            ),
            resolved_budget_limit=1,
        )


def test_tag_selects_cloud_authority_without_legacy_fallback() -> None:
    admission = _admission()
    target = admission.cloud_target, admission.service_target, admission.report_context
    decode = getattr(budget, "decode_budget_target", None)
    assert callable(decode), "M04 tagged budget authority selection is absent"
    text = budget.encode_cloud_budget_target(*target)
    assert decode(text) == target
    with pytest.raises(budget.BudgetCollectionError):
        decode(text.replace("cloud_budget_target.v1", "unknown.v1"))


def test_valid_team_thirty_day_context_is_preserved_after_restart() -> None:
    admission, raw = _snapshot()
    context = replace(
        admission.report_context,
        scope="team",
        range_key="30d",
        interval_start=admission.report_context.interval_end - timedelta(days=30),
    )
    restored = restore_budget_admission(
        raw,
        (admission.cloud_target, admission.service_target, context),
        resolved_budget_limit=1,
    )
    assert restored.report_context == context
    assert restored.requested_at == admission.requested_at


def _cloud_report() -> BudgetReportInputV1:
    admission = _admission()
    context = admission.report_context
    period = BudgetPeriodV1(context.interval_start, context.interval_end)
    return replace(
        _report(1, None).report,
        subject=CapacitySubjectV2(
            "ollama",
            admission.provider_target,
            admission.cloud_target.account_id,
            admission.cloud_target.resource_id,
        ),
        binding_id=admission.cloud_target.binding.binding_id,
        binding_generation=admission.cloud_target.binding.generation,
        scope_generation=1,
        scope_id=None,
        scope_evidence="unresolved",
        source_id="ollama.cloud.usage.v1",
        source_category="self_requests_and_cost",
        cost_basis="provider_reported_usage_usd",
        requested_period=period,
        covered_period=period,
        source_data_through=None,
        collected_at=admission.requested_at,
        empty_means_zero=False,
    )


@pytest.mark.parametrize(
    "change",
    [
        None,
        "binding",
        "generation",
        "scope_epoch",
        "scope_verified",
        "category",
        "period",
        "provider",
        "resource",
        "source",
    ],
)
def test_cloud_report_authority_is_exact_and_never_infers_scope(
    change: str | None,
) -> None:
    admission = _admission()
    target = admission.cloud_target, admission.service_target, admission.report_context
    report = _cloud_report()
    if change == "binding":
        report = replace(report, binding_id=OpaqueIdV1("other-binding"))
    elif change == "generation":
        report = replace(report, binding_generation=5)
    elif change == "scope_epoch":
        report = replace(report, scope_generation=4)
    elif change == "scope_verified":
        report = replace(
            report,
            scope_id=OpaqueIdV1("guessed-scope"),
            scope_evidence="provider_verified",
        )
    elif change == "category":
        report = replace(report, source_category="team_requests_and_cost")
    elif change == "period":
        report = replace(
            report,
            requested_period=BudgetPeriodV1(
                report.requested_period.start - timedelta(days=1),
                report.requested_period.end,
            ),
        )
    elif change in {"provider", "resource"}:
        report = replace(
            report,
            subject=replace(
                report.subject,
                **(
                    {"provider_key": "claude"}
                    if change == "provider"
                    else {"resource_id": OpaqueIdV1("other-resource")}
                ),
            ),
        )
    elif change == "source":
        report = replace(report, source_id="ollama.cloud.balance.v1")
    check = getattr(budget, "require_budget_report_authority", None)
    assert callable(check), "M04 cloud report authority matching is absent"
    if change is None:
        check(target, report)
    else:
        with pytest.raises(
            budget.BudgetCollectionError, match="budget_commit_run_mismatch"
        ):
            check(target, report)


@pytest.mark.parametrize(
    "changed",
    [
        None,
        "profile_id",
        "target_generation",
        "capability_id",
        "account_id",
        "source_id",
    ],
)
def test_cloud_commit_row_matches_captured_graph(changed: str | None) -> None:
    admission, raw = _snapshot()
    target = admission.cloud_target, admission.service_target, admission.report_context
    if changed is not None:
        raw[changed] = 99 if changed == "target_generation" else "other"
    check = getattr(budget, "require_budget_run_authority", None)
    assert callable(check), "M04 cloud commit row matching is absent"
    if changed is None:
        check(target, raw)
    else:
        with pytest.raises(
            budget.BudgetCollectionError, match="budget_commit_run_mismatch"
        ):
            check(target, raw)


@pytest.mark.parametrize(
    "changed", [None, "account", "resource", "epoch", "scope", "range", "interval"]
)
def test_cloud_latest_selection_uses_exact_resource_and_context(
    changed: str | None,
) -> None:
    admission = _admission()
    target = admission.cloud_target, admission.service_target, admission.report_context
    account, resource = admission.account_id, admission.resource_id
    epoch = 1
    context = admission.report_context
    if changed == "account":
        account = OpaqueIdV1("other-account")
    elif changed == "resource":
        resource = OpaqueIdV1("other-resource")
    elif changed == "epoch":
        epoch = 2
    elif changed == "scope":
        context = replace(context, scope="team")
    elif changed == "range":
        context = replace(
            context,
            range_key="30d",
            interval_start=context.interval_end - timedelta(days=30),
        )
    elif changed == "interval":
        context = replace(
            context,
            interval_start=context.interval_start - timedelta(days=1),
            interval_end=context.interval_end - timedelta(days=1),
        )
    matches = getattr(budget, "budget_target_matches_query", None)
    assert callable(matches), "M04 cloud latest context matching is absent"
    assert matches(target, account, resource, epoch, context) is (changed is None)
    assert matches(target, admission.account_id, admission.resource_id, 1, None)


def test_untagged_billing_authority_and_scope_query_remain_separate() -> None:
    from backend.tests.collection_control.pure.test_budget_dispatch_policy import (
        snapshot,
    )

    admission, raw = snapshot()
    target = admission.billing_target
    assert budget.decode_budget_target(budget.encode_billing_target(target)) == target
    budget.require_budget_run_authority(target, raw)
    assert budget.budget_target_matches_query(
        target,
        target.connection.account_id,
        target.connection.resource_id,
        target.connection.scope_generation,
    )
    assert not budget.budget_target_matches_query(
        target,
        target.connection.account_id,
        target.connection.resource_id,
        target.connection.scope_generation,
        _admission().report_context,
    )
