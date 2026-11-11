"""Pure authority policy for independent API billing monitoring."""

from agentmonitor.contracts.registry_billing_v1 import (
    BillingAccessTargetV1,
    BillingMonitoringProofV1,
    SetBillingMonitoringCommandV1,
)
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1


def billing_binding_authority_changed(
    previous: ActiveCredentialBindingRefV1 | None,
    current: ActiveCredentialBindingRefV1 | None,
) -> bool:
    """Return whether an access check can no longer authorize monitoring."""
    return previous != current


def require_billing_monitoring_proof(
    command: SetBillingMonitoringCommandV1,
    proof: BillingMonitoringProofV1 | None,
    current_target: BillingAccessTargetV1 | None,
) -> None:
    """Require exact current binding/scope evidence only for enabling."""
    if command.monitoring_preference == "disabled":
        if proof is not None:
            raise ValueError("billing_monitoring_proof_conflict")
        return
    if proof is None or current_target is None:
        raise ValueError("billing_monitoring_proof_required")
    connection = current_target.connection
    if (
        proof.run_id != command.verified_run_id
        or proof.verified_at > command.requested_at
        or proof.current_target != current_target
        or connection.account_id != command.account_id
        or connection.resource_id != command.resource_id
        or connection.record_version != command.expected_connection_version
        or connection.scope_generation != command.expected_scope_generation
        or current_target.binding.generation != command.expected_binding_generation
    ):
        raise ValueError("billing_monitoring_target_changed")
