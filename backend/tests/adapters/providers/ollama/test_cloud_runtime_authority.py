"""Pure metadata policy for the non-secret, owner-controlled runtime grant."""

import stat

from agentmonitor.composition.ollama_cloud_authority import valid_authority_marker


def test_only_private_digest_regular_owner_marker_enables_access() -> None:
    assert valid_authority_marker(stat.S_IFREG | 0o600, 1000, 1000, 64)
    assert not valid_authority_marker(stat.S_IFREG | 0o644, 1000, 1000, 64)
    assert not valid_authority_marker(stat.S_IFLNK | 0o600, 1000, 1000, 64)
    assert not valid_authority_marker(stat.S_IFREG | 0o600, 1001, 1000, 64)
    assert not valid_authority_marker(stat.S_IFREG | 0o600, 1000, 1000, 0)
