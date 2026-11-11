"""Pure safe-status policy: constructed lifecycle records never cross I/O."""

from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.registry.domain.billing_connection import (
    billing_credential_status,
)
from agentmonitor.modules.registry.domain.credential_binding import (
    activate_prepared_credential_binding,
    complete_credential_binding_cleanup,
    disconnect_active_credential_binding,
    new_credential_binding_aggregate,
    prepare_credential_binding,
)


def test_rotation_reports_pending_and_cleanup_without_losing_active_generation() -> (
    None
):
    """No state implies provider access; old cleanup remains independently visible."""
    first = OpaqueIdV1("amcb_" + "a" * 32)
    second = OpaqueIdV1("amcb_" + "b" * 32)
    aggregate = new_credential_binding_aggregate(OpaqueIdV1("pure-account"))
    assert billing_credential_status(aggregate).state == "missing"
    aggregate = prepare_credential_binding(
        aggregate, binding_id=first, expected_record_version=0
    )
    status = billing_credential_status(aggregate)
    assert (status.state, status.active_generation, status.pending_generation) == (
        "pending",
        None,
        1,
    )
    aggregate = activate_prepared_credential_binding(
        aggregate, binding_id=first, expected_record_version=1
    )
    assert billing_credential_status(aggregate).state == "stored"
    aggregate = prepare_credential_binding(
        aggregate, binding_id=second, expected_record_version=2
    )
    status = billing_credential_status(aggregate)
    assert (status.state, status.active_generation, status.pending_generation) == (
        "pending",
        1,
        2,
    )
    aggregate = activate_prepared_credential_binding(
        aggregate, binding_id=second, expected_record_version=3
    )
    status = billing_credential_status(aggregate)
    assert (status.state, status.active_generation, status.pending_generation) == (
        "stored",
        2,
        None,
    )
    assert status.cleanup_required
    aggregate = complete_credential_binding_cleanup(
        aggregate, binding_id=first, expected_record_version=4
    )
    assert not billing_credential_status(aggregate).cleanup_required
    aggregate = disconnect_active_credential_binding(
        aggregate, expected_record_version=5, reason_code="owner_disconnected"
    )
    status = billing_credential_status(aggregate)
    assert (status.state, status.active_generation, status.pending_generation) == (
        "cleanup_required",
        None,
        None,
    )
    assert status.cleanup_required
    aggregate = complete_credential_binding_cleanup(
        aggregate, binding_id=second, expected_record_version=6
    )
    status = billing_credential_status(aggregate)
    assert aggregate.binding_generation == 3
    assert status.state == "missing"
    assert status.active_generation is None
    assert not status.cleanup_required
