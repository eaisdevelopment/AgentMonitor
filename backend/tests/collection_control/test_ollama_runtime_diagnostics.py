"""Pure failure classification never retains an arbitrary exception message."""

from agentmonitor.composition import ollama_runtime_collection as runtime


def test_known_runtime_failure_keeps_closed_phase_and_reason() -> None:
    failure = runtime.classify_ollama_runtime_failure_v1(
        "installation", "ollama_installation_discovery_invalid"
    )
    assert failure.phase == "installation"
    assert failure.reason == "ollama_installation_discovery_invalid"


def test_unknown_runtime_failure_discards_untrusted_details() -> None:
    failure = runtime.classify_ollama_runtime_failure_v1(
        "untrusted phase", "arbitrary exception detail"
    )
    assert failure.phase == "internal"
    assert failure.reason == "internal_error"
    assert "arbitrary" not in repr(failure)


def test_known_code_substring_is_not_an_allowlisted_failure() -> None:
    failure = runtime.classify_ollama_runtime_failure_v1(
        "collection", "ollama_installation_unavailable: private detail"
    )
    assert failure.phase == "collection"
    assert failure.reason == "internal_error"
