"""Pure compatibility and validation for the additive recovery-query filter."""

from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts.collection_recovery_v1 import (
    CollectionRecoveryQueryV1,
    CollectionRecoveryScopeV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


@pytest.mark.parametrize("capability", ["", "subscription quota", "x" * 129, 1, False])
def test_recovery_capability_filter_rejects_non_codes(capability: object) -> None:
    start = datetime(2026, 11, 17, tzinfo=UTC)
    with pytest.raises(ValueError, match="collection_recovery_query_invalid"):
        CollectionRecoveryQueryV1(
            "claude",
            start,
            start + timedelta(hours=1),
            capability_id=capability,  # type: ignore[arg-type]
        )


def test_recovery_capability_filter_preserves_default_and_exact_scope() -> None:
    start = datetime(2026, 11, 17, tzinfo=UTC)
    end = start + timedelta(hours=1)
    scope = CollectionRecoveryScopeV1(
        OpaqueIdV1("account"),
        OpaqueIdV1("service"),
        1,
        "subscription.quota",
        "source",
        "1.0.0",
        "a" * 64,
        "quota.v1",
        "ollama",
    )
    original = CollectionRecoveryQueryV1("ollama", start, end, scope, 1)
    assert original.capability_id is None
    assert (
        CollectionRecoveryQueryV1(
            "ollama", start, end, scope, 1, capability_id="subscription.quota"
        ).scope
        == scope
    )
    with pytest.raises(ValueError, match="collection_recovery_query_invalid"):
        CollectionRecoveryQueryV1(
            "ollama", start, end, scope, 1, capability_id="api.usage"
        )
