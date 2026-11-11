"""Constructed admission reconstruction is pure; no rows enter SQLite."""

import json
from dataclasses import fields
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from agentmonitor.adapters.persistence.collection_control.sqlite.budget_dispatch import (  # noqa: E501
    restore_budget_admission,
)
from agentmonitor.contracts import collection_control_v1 as contracts
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import (
    BillingAccessTargetV1,
    BillingConnectionViewV1,
)
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    ProviderTargetRefV1,
)


def _admission() -> contracts.BudgetCollectionRunAdmissionV1:
    now = datetime(2026, 11, 11, tzinfo=UTC)
    target = BillingAccessTargetV1(
        BillingConnectionViewV1(
            OpaqueIdV1("account-1"),
            OpaqueIdV1("resource-1"),
            "claude",
            None,
            "unresolved",
            1,
            "disabled",
            "pending",
            1,
            1,
            now,
            now,
        ),
        ActiveCredentialBindingRefV1(
            OpaqueIdV1("account-1"), OpaqueIdV1("amcb_" + "a" * 32), 1
        ),
        "verification",
    )
    return contracts.BudgetCollectionRunAdmissionV1(
        billing_target=target,
        run_id=OpaqueIdV1("run-1"),
        schedule_id=OpaqueIdV1("schedule-1"),
        request_id=OpaqueIdV1("request-1"),
        trigger="reauth_verification",
        operation_family="billing_verification",
        requested_capability_ids=("api.billing",),
        capability_set_version="1.0.0",
        request_auth_method="dashboard_session",
        request_principal_id=OpaqueIdV1("principal-1"),
        correlation_id=OpaqueIdV1("correlation-1"),
        causation_id=None,
        target_key_digest="1" * 64,
        provider_key="claude",
        provider_target=ProviderTargetRefV1(
            target_kind="cloud_service",
            target_id=OpaqueIdV1("amat_" + "2" * 32),
        ),
        account_id=OpaqueIdV1("account-1"),
        profile_id=None,
        resource_id=OpaqueIdV1("resource-1"),
        capability_id="api.billing",
        source_id="anthropic.api.cost.v1",
        adapter_version="1.0.0",
        provider_version=None,
        adapter_protocol_version="1.0.0",
        manifest_fingerprint="3" * 64,
        collection_policy_version="1.0.0",
        registry_revision=1,
        retry_chain_id=OpaqueIdV1("retry-1"),
        attempt_ordinal=1,
        target_generation=1,
        scheduler_instance_id=OpaqueIdV1("scheduler-1"),
        lease_policy_version="1.0.0",
        budget_policy_id="ollama-cloud-global",
        budget_policy_version="1.0.0",
        budget_scope_digest="4" * 64,
        budget_dimension="request",
        budget_unit="count",
        budget_units=1,
        budget_limit_units=1,
        budget_window_start=now,
        budget_window_end=now + timedelta(minutes=1),
        payload_schema="budget.report.v1",
        idempotency_key_digest=None,
        request_digest="5" * 64,
        requested_at=now,
        deadline_at=now + timedelta(seconds=30),
    )


def snapshot() -> tuple[contracts.BudgetCollectionRunAdmissionV1, dict[str, object]]:
    original = _admission()
    raw: dict[str, object] = {
        field.name: getattr(original, field.name) for field in fields(original)
    }
    for name, value in tuple(raw.items()):
        if isinstance(value, OpaqueIdV1):
            raw[name] = value.value
        elif isinstance(value, datetime):
            raw[name] = value.isoformat()
    raw.pop("billing_target")
    raw.pop("budget_limit_units")
    raw.pop("provider_target")
    target = original.provider_target
    raw["provider_target_kind"] = target.target_kind
    raw["provider_target_id"] = target.target_id.value
    raw["requested_capability_ids"] = json.dumps(original.requested_capability_ids)
    return original, raw


def test_reconstruction_preserves_original_midnight_deadline_and_identity() -> None:
    original, raw = snapshot()
    actual = restore_budget_admission(
        raw, original.billing_target, resolved_budget_limit=1
    )
    assert actual == original
    assert actual.profile_id is None
    assert actual.requested_at.date() == datetime(2026, 11, 11, tzinfo=UTC).date()


@pytest.mark.parametrize(
    "field,value",
    [
        ("requested_capability_ids", '["api.billing","api.billing"]'),
        ("requested_capability_ids", "{}"),
        ("profile_id", "invented-profile"),
        ("request_digest", "invalid"),
        ("account_id", "other-account"),
        ("provider_target_kind", "installation"),
        ("deadline_at", "2026-11-12T00:00:00+00:00"),
        ("requested_at", "2026-11-11T00:00:00"),
    ],
)
def test_corrupt_or_cross_target_admission_is_rejected(field: str, value: str) -> None:
    original, raw = snapshot()
    raw[field] = value
    with pytest.raises(ValueError):
        restore_budget_admission(raw, original.billing_target, resolved_budget_limit=1)


@pytest.mark.parametrize("limit", [None, True, -1, 0])
def test_limit_is_required_from_original_immutable_policy(limit: object) -> None:
    original, raw = snapshot()
    # Intentionally violate the typed boundary to verify runtime rejection.
    with pytest.raises(ValueError):
        restore_budget_admission(
            raw, original.billing_target, resolved_budget_limit=cast(int, limit)
        )
