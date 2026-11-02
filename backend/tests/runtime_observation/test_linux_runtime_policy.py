"""Pure provider policy for exact process scans with no matching process."""

from agentmonitor.composition.linux_runtime_monitoring import (
    empty_process_observation_is_valid_v1,
)


def test_verified_empty_ollama_scan_is_valid_without_widening_claude() -> None:
    assert empty_process_observation_is_valid_v1(
        provider_key="ollama", inspection_state="success", process_count=0
    )
    assert not empty_process_observation_is_valid_v1(
        provider_key="claude", inspection_state="success", process_count=0
    )
    assert not empty_process_observation_is_valid_v1(
        provider_key="ollama", inspection_state="source_unavailable", process_count=0
    )
