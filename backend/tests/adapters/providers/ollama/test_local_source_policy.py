"""Pure route and redirect security rules for the local source."""

import pytest
from agentmonitor.adapters.providers.ollama.local_catalog.source import (
    _read_json,
)


@pytest.mark.parametrize(
    "path", ["/api/generate", "https://example.org/api/tags", "/api/tags?extra=1"]
)
def test_unapproved_routes_are_rejected_before_network_io(path):
    with pytest.raises(ValueError, match="source_not_allowed"):
        _read_json(path)
