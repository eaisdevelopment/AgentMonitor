"""Pure exact-version consistency policy for local catalog collection."""

import pytest
from agentmonitor.adapters.providers.ollama.local_catalog.source import (
    version_consistent,
)


@pytest.mark.parametrize(
    ("initial", "final", "expected"),
    [
        ("0.24.0", "0.24.0", True),
        ("0.24.0", "0.24.1", False),
        ("0.24.1", "0.24.1", False),
        ("0.24.0", None, False),
        (None, "0.24.0", False),
    ],
)
def test_only_unchanged_admitted_version_is_consistent(initial, final, expected):
    assert version_consistent(initial, final) is expected
