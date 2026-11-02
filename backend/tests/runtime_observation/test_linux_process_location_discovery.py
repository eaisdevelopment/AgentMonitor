"""Provider discovery failure does not corrupt successful scan coverage."""

import time

from agentmonitor.composition.linux_process_locations import (
    _merge_provider_discoveries_v1,
    _ProviderDiscoveryResultV1,
    read_live_process_locations_v1,
)


def test_optional_unavailable_provider_does_not_mark_other_scans_truncated() -> None:
    existing = _ProviderDiscoveryResultV1("available", (), False)
    optional = _ProviderDiscoveryResultV1("unavailable", (), False)

    installations, truncated = _merge_provider_discoveries_v1((existing, optional))

    assert installations == ()
    assert truncated is False


def test_real_provider_discovery_and_scan_share_one_total_deadline() -> None:
    started = time.monotonic()

    result = read_live_process_locations_v1()

    assert time.monotonic() - started < 3.5
    assert result.availability.state in {"available", "partial", "unavailable"}
    if result.availability.state == "partial":
        assert result.availability.reason_code == "provider_discovery_partial"
    assert all(
        item.provider_key in {"claude", "codex", "ollama"}
        and item.account_association is None
        for item in result.items
    )


def test_discovery_availability_preserves_partial_provider_coverage() -> None:
    """A provider failure is distinct from truncation of a successful scan."""
    from agentmonitor.composition.linux_process_locations import _discovery_availability_v1

    assert _discovery_availability_v1(usable=True, provider_unavailable=True) == (
        'partial', 'provider_discovery_partial'
    )
    assert _discovery_availability_v1(usable=True, provider_unavailable=False) == (
        'available', 'same_user_exact_provider_executables'
    )
    assert _discovery_availability_v1(usable=False, provider_unavailable=True) == (
        'unavailable', 'process_source_unavailable'
    )
