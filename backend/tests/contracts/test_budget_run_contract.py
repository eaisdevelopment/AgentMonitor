"""Pure budget run contracts preserve existing quota admission/commit rules."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
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


def test_billing_admission_has_real_account_and_scope_without_a_profile() -> None:
    current = _admission()
    assert current.profile_id is None
    assert current.billing_target.binding.generation == 1
    for change in (
        {"account_id": None},
        {"resource_id": None},
        {"provider_key": "codex"},
        {"profile_id": OpaqueIdV1("profile")},
        {"payload_schema": "quota"},
        {"trigger": "scheduled"},
    ):
        with pytest.raises(ValueError):
            replace(current, **change)


def _run() -> contracts.BudgetCollectionRunViewV1:
    now = datetime(2026, 11, 11, tzinfo=UTC)
    return contracts.BudgetCollectionRunViewV1(
        run_id=OpaqueIdV1("run"),
        schedule_id=OpaqueIdV1("schedule"),
        provider_key="claude",
        account_id=OpaqueIdV1("account"),
        resource_id=OpaqueIdV1("resource"),
        capability_id="api.billing",
        state="succeeded",
        source_id="anthropic.api.cost.v1",
        adapter_version="1.0.0",
        provider_version=None,
        target_generation=1,
        fencing_token=1,
        requested_at=now,
        started_at=now,
        completed_at=now + timedelta(seconds=1),
        deadline_at=now + timedelta(seconds=120),
        duration_ms=1000,
        payload_digest="a" * 64,
        outcome_code="succeeded",
        error_code=None,
        observation_ids=(),
        report_id=OpaqueIdV1("report"),
    )


def test_complete_empty_budget_run_keeps_report_identity() -> None:
    current = _run()
    assert current.observation_ids == ()
    with pytest.raises(ValueError):
        replace(current, report_id=None)
    with pytest.raises(ValueError):
        replace(current, state="running")


def test_nonempty_report_also_needs_report_identity() -> None:
    current = replace(_run(), observation_ids=(OpaqueIdV1("fact"),))
    with pytest.raises(ValueError):
        replace(current, report_id=None)
