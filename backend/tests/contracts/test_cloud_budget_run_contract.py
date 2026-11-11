"""Pure M7 cloud admission invariants; constructed DTOs never cross I/O."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

import pytest
from agentmonitor.contracts import collection_control_v1 as contracts
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    CloudMonitoringTargetV1,
    ProviderAccessTargetV1,
    ProviderTargetRefV1,
)

from backend.tests.contracts.test_budget_run_contract import _admission as _billing

NOW = datetime(2026, 11, 11, tzinfo=UTC)


def _context(**changes: object) -> contracts.CloudBudgetReportContextV1:
    context_type = getattr(contracts, "CloudBudgetReportContextV1", None)
    assert context_type is not None, "immutable cloud budget report context is absent"
    values: dict[str, object] = {
        "scope": "self",
        "range_key": "7d",
        "interval_start": NOW - timedelta(days=7),
        "interval_end": NOW,
    }
    return cast(
        contracts.CloudBudgetReportContextV1, context_type(**(values | changes))
    )


def _graph() -> CloudMonitoringTargetV1:
    return CloudMonitoringTargetV1(
        profile_id=OpaqueIdV1("pure-cloud-profile"),
        resource_id=OpaqueIdV1("pure-cloud-resource"),
        account_id=OpaqueIdV1("pure-cloud-account"),
        access_target_id=OpaqueIdV1("amat_" + "a" * 32),
        binding=ActiveCredentialBindingRefV1(
            OpaqueIdV1("pure-cloud-account"),
            OpaqueIdV1("amcb_" + "b" * 32),
            4,
        ),
        lifecycle="active",
        identity_state="owner_confirmed",
        owner_principal_id=OpaqueIdV1("pure-owner"),
        owner_asserted_at=NOW - timedelta(days=1),
        record_version=7,
    )


def _service() -> ProviderAccessTargetV1:
    return ProviderAccessTargetV1(
        access_target_id=_graph().access_target_id,
        provider_key="ollama",
        target_kind="cloud_service",
        authority_id="ollama.com",
        manifest_fingerprint="b" * 64,
        lifecycle="active",
        record_version=2,
    )


def _admission(**changes: object) -> contracts.CloudBudgetCollectionRunAdmissionV1:
    admission_type = getattr(contracts, "CloudBudgetCollectionRunAdmissionV1", None)
    assert admission_type is not None, "cloud budget run admission is absent"
    billing = _billing()
    values = {
        field.name: getattr(billing, field.name)
        for field in fields(contracts.CollectionRunAdmissionV2)
    }
    graph = _graph()
    values.update(
        cloud_target=graph,
        service_target=_service(),
        report_context=_context(),
        trigger="scheduled",
        operation_family="collect.ollama.usage.7d",
        requested_capability_ids=("api.usage",),
        request_auth_method="internal_scheduler",
        request_principal_id=None,
        provider_key="ollama",
        provider_target=ProviderTargetRefV1("cloud_service", graph.access_target_id),
        account_id=graph.account_id,
        profile_id=graph.profile_id,
        resource_id=graph.resource_id,
        capability_id="api.usage",
        source_id="ollama.cloud.usage.v1",
        manifest_fingerprint="c" * 64,
        target_generation=graph.binding.generation,
    )
    return cast(
        contracts.CloudBudgetCollectionRunAdmissionV1,
        admission_type(**(values | changes)),
    )


def test_cloud_run_retains_existing_graph_and_separate_service_fingerprint() -> None:
    admission = _admission()
    assert isinstance(admission, contracts.CollectionRunAdmissionV2)
    assert admission.CONTRACT_ID == "CTR-COL-002"
    assert admission.CONTRACT_VERSION == "2.2.0"
    assert admission.profile_id == admission.cloud_target.profile_id
    assert admission.service_target.manifest_fingerprint == "b" * 64
    assert admission.manifest_fingerprint == "c" * 64
    assert admission.target_generation == 4
    assert admission.cloud_target.record_version == 7
    assert admission.report_context.scope == "self"
    assert not hasattr(admission, "billing_target")


def test_explicit_team_thirty_day_context_stays_pinned_on_later_admission() -> None:
    context = _context(
        scope="team",
        range_key="30d",
        interval_start=NOW - timedelta(days=30),
    )
    later = NOW + timedelta(days=2)
    admission = _admission(
        report_context=context,
        requested_at=later,
        deadline_at=later + timedelta(seconds=120),
    )
    assert admission.report_context == context
    assert admission.report_context.interval_end == NOW
    assert admission.report_context.scope == "team"
    with pytest.raises(FrozenInstanceError):
        cast(Any, context).scope = "self"


@pytest.mark.parametrize(
    "changes",
    [
        {"scope": "organization"},
        {"range_key": "14d"},
        {"range_key": "30d"},
        {"interval_start": NOW - timedelta(days=6)},
        {"interval_start": NOW},
        {"interval_end": NOW - timedelta(days=8)},
        {"interval_start": NOW - timedelta(days=7) + timedelta(seconds=1)},
        {
            "interval_start": NOW - timedelta(days=7) + timedelta(hours=1),
            "interval_end": NOW + timedelta(hours=1),
        },
        {"interval_start": (NOW - timedelta(days=7)).replace(tzinfo=None)},
        {"interval_end": NOW.replace(tzinfo=None)},
    ],
)
def test_report_context_rejects_unknown_scope_and_noncompleted_utc_ranges(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        _context(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"profile_id": None},
        {"profile_id": OpaqueIdV1("other-profile")},
        {"account_id": OpaqueIdV1("other-account")},
        {"resource_id": OpaqueIdV1("other-resource")},
        {"provider_key": "codex"},
        {
            "provider_target": ProviderTargetRefV1(
                "cloud_service", OpaqueIdV1("amat_" + "d" * 32)
            )
        },
        {"target_generation": 5},
        {"payload_schema": "ProviderQuotaInputV2@2"},
        {"capability_id": "subscription.quota"},
        {"requested_capability_ids": ("subscription.quota",)},
        {"source_id": "ollama.cloud.balance.v1"},
        {"budget_units": 2},
        {"budget_units": 0},
        {"budget_unit": "usd"},
        {"budget_dimension": "money"},
        {"deadline_at": NOW + timedelta(seconds=121)},
        {"requested_at": NOW - timedelta(seconds=1)},
        {"trigger": "reauth_verification"},
    ],
)
def test_cloud_run_rejects_mismatched_authority_or_report_operation(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        _admission(**changes)


@pytest.mark.parametrize("lifecycle", ["disabled", "archived"])
def test_inactive_cloud_graph_cannot_authorize_usage(
    lifecycle: Literal["disabled", "archived"],
) -> None:
    with pytest.raises(ValueError):
        _admission(cloud_target=replace(_graph(), lifecycle=lifecycle))


@pytest.mark.parametrize(
    "changes",
    [
        {"lifecycle": "disabled"},
        {"provider_key": "codex"},
        {"authority_id": "ollama.cloud"},
        {"access_target_id": OpaqueIdV1("amat_" + "d" * 32)},
    ],
)
def test_service_authority_must_match_existing_ollama_graph(
    changes: dict[str, Any],
) -> None:
    with pytest.raises(ValueError):
        _admission(service_target=replace(_service(), **changes))


def test_usage_manual_action_does_not_need_or_create_balance_verification() -> None:
    admission = _admission(
        trigger="manual",
        request_auth_method="dashboard_session",
        request_principal_id=OpaqueIdV1("pure-owner"),
        idempotency_key_digest="d" * 64,
    )
    assert admission.trigger == "manual"
    assert admission.source_id == "ollama.cloud.usage.v1"
    assert admission.payload_schema == "budget.report.v1"


def test_existing_profile_free_billing_admission_is_unchanged() -> None:
    billing = _billing()
    assert billing.profile_id is None
    assert billing.billing_target.connection.provider_key == "claude"
    assert billing.CONTRACT_VERSION == "2.1.0"
