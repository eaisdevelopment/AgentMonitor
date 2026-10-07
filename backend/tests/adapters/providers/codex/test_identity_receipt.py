"""Pure request-binding policy for one-shot Codex identity receipts."""

from datetime import UTC, datetime

from agentmonitor.adapters.providers.codex.adapter import _VerifiedIdentityReceiptSlotV1
from agentmonitor.adapters.providers.codex.manifest import CODEX_PROVIDER_VERSION
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import ObservedProfileIdentityV1


def test_verified_identity_receipt_is_request_bound_consumed_and_cleared() -> None:
    """M5-CDX-PURE-013: a receipt can be consumed by only its exact request."""
    slot = _VerifiedIdentityReceiptSlotV1()
    operation_id = OpaqueIdV1("operation-one")
    correlation_id = OpaqueIdV1("correlation-one")
    identity = ObservedProfileIdentityV1(
        email="owner@example.test",
        provider_organization=None,
        fingerprint="b" * 64,
        observed_at=datetime.now(UTC),
        provider_version=CODEX_PROVIDER_VERSION,
    )

    slot.put(operation_id, correlation_id, identity)
    assert slot.take(OpaqueIdV1("operation-other"), correlation_id) is None
    assert slot.take(operation_id, correlation_id) is None

    slot.put(operation_id, correlation_id, identity)
    assert slot.take(operation_id, correlation_id) == identity
    assert slot.take(operation_id, correlation_id) is None

    slot.put(operation_id, correlation_id, identity)
    slot.clear()
    assert slot.take(operation_id, correlation_id) is None
