"""Closed financial checkpoint serialization is pure, never provider input."""

import pytest


@pytest.mark.parametrize("payload", [b"{}\n", b"[]\n", b"null\n", b"{}", b"invalid"])
def test_checkpoint_codec_rejects_unknown_or_noncanonical_record(
    payload: bytes,
) -> None:
    from agentmonitor.modules.capacity.domain.budget_retention_codec import (
        BudgetRetentionCodecV1,
    )

    with pytest.raises(ValueError, match="budget_checkpoint_record_invalid"):
        BudgetRetentionCodecV1().decode(payload)
