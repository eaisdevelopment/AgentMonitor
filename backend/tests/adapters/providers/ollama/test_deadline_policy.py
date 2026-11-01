"""Pure timing policy for one bounded local collection."""

import pytest

from agentmonitor.adapters.providers.ollama.local_catalog.source import (
    request_deadline,
)


def test_per_request_deadline_cannot_outlive_global_operation():
    assert request_deadline(10.0, 11.0) == 11.0
    assert request_deadline(10.0, 30.0) == 13.0


def test_expired_operation_is_rejected_before_a_request():
    with pytest.raises(TimeoutError, match="operation_deadline_exceeded"):
        request_deadline(12.0, 12.0)
