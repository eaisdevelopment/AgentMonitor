"""Pure contract check for legacy-only normalizers."""

from datetime import UTC, datetime

import pytest
from agentmonitor.modules.collection_control.application.runner import v1_normalizer


def test_v1_normalizer_rejects_non_v1_admission_before_callback() -> None:
    def normalize(_admission, _outcome, _completed):
        raise AssertionError("legacy callback must not run")

    with pytest.raises(ValueError, match="collection_v1_admission_required"):
        v1_normalizer(normalize)(object(), object(), datetime.now(UTC))  # type: ignore[arg-type]
