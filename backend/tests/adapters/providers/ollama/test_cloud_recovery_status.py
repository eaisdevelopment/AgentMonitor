"""Pure status policy; no worker, provider or filesystem I/O."""

from agentmonitor.composition.ollama_cloud_worker import recovery_exit_code


def test_unresolved_recovery_never_reports_success() -> None:
    assert recovery_exit_code("outcome_unknown") == 4
    assert recovery_exit_code("legacy_unresolved") == 4
    assert recovery_exit_code("owner_active_or_unverified") == 4
    assert recovery_exit_code("recovered") == 0
