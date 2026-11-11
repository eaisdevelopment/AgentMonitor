"""Pure billing monitoring authority checks; no persistence or provider I/O."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import (
    BillingAccessTargetV1,
    BillingConnectionViewV1,
    BillingMonitoringProofV1,
    SetBillingMonitoringCommandV1,
)
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1
from agentmonitor.modules.registry.domain.billing_monitoring import (
    billing_binding_authority_changed,
    require_billing_monitoring_proof,
)

NOW = datetime(2026, 11, 11, 12, tzinfo=UTC)


def _target(*, generation: int = 1) -> BillingAccessTargetV1:
    account_id = OpaqueIdV1("account")
    return BillingAccessTargetV1(
        connection=BillingConnectionViewV1(
            account_id=account_id,
            resource_id=OpaqueIdV1("resource"),
            provider_key="claude",
            scope_id="owner-scope",
            scope_evidence="owner_asserted",
            scope_generation=2,
            monitoring_preference="disabled",
            lifecycle="pending",
            record_version=3,
            registry_revision=4,
            created_at=NOW,
            updated_at=NOW,
        ),
        binding=ActiveCredentialBindingRefV1(
            account_id=account_id,
            binding_id=OpaqueIdV1("amcb_" + "a" * 32),
            generation=generation,
        ),
        purpose="verification",
    )


def _command(target: BillingAccessTargetV1) -> SetBillingMonitoringCommandV1:
    return SetBillingMonitoringCommandV1(
        account_id=target.connection.account_id,
        resource_id=target.connection.resource_id,
        expected_account_version=5,
        expected_connection_version=target.connection.record_version,
        expected_scope_generation=target.connection.scope_generation,
        expected_binding_generation=target.binding.generation,
        monitoring_preference="enabled",
        verified_run_id=OpaqueIdV1("run"),
        principal_id=OpaqueIdV1("owner"),
        command_id=OpaqueIdV1("command"),
        requested_at=NOW,
    )


def _proof(target: BillingAccessTargetV1) -> BillingMonitoringProofV1:
    return BillingMonitoringProofV1(
        current_target=target,
        run_id=OpaqueIdV1("run"),
        report_id=OpaqueIdV1("report"),
        payload_digest="a" * 64,
        verified_at=NOW,
    )


def test_enable_requires_exact_current_binding_scope_and_run() -> None:
    target = _target()
    command = _command(target)
    proof = _proof(target)
    require_billing_monitoring_proof(command, proof, target)

    for invalid_command, invalid_proof, invalid_target in (
        (replace(command, verified_run_id=OpaqueIdV1("other")), proof, target),
        (command, proof, _target(generation=2)),
        (
            command,
            replace(
                proof,
                current_target=replace(
                    target,
                    connection=replace(target.connection, scope_generation=3),
                ),
            ),
            target,
        ),
        (
            command,
            replace(proof, verified_at=command.requested_at + timedelta(seconds=1)),
            target,
        ),
    ):
        with pytest.raises(ValueError, match="billing_monitoring_target_changed"):
            require_billing_monitoring_proof(
                invalid_command, invalid_proof, invalid_target
            )


def test_active_binding_replacement_requires_monitoring_invalidation() -> None:
    first = _target().binding
    replacement = replace(
        first,
        binding_id=OpaqueIdV1("amcb_" + "b" * 32),
        generation=2,
    )
    assert not billing_binding_authority_changed(None, None)
    assert not billing_binding_authority_changed(first, first)
    assert billing_binding_authority_changed(None, first)
    assert billing_binding_authority_changed(first, None)
    assert billing_binding_authority_changed(first, replacement)
