"""Pure sanitized diagnostic policy; no I/O doubles or exception messages."""

import pytest


def test_known_worker_failure_has_only_closed_phase_type_and_source_location() -> None:
    from agentmonitor.composition.billing_worker import format_worker_failure

    assert format_worker_failure(
        "collect", "ValueError", "composition/ollama_usage_collection.py", 328
    ) == (
        "BILLING_WORKER_FAILURE phase=collect type=ValueError "
        "source=backend/src/agentmonitor/composition/ollama_usage_collection.py:328"
    )


@pytest.mark.parametrize(
    "path",
    (
        "/home/owner/private/.env",
        "../private.py",
        "composition/../../private.py",
        "composition/private name.py",
        "composition/worker.py\nextra=private",
        "third_party/worker.py",
        "composition/worker.py:123",
        "",
    ),
)
def test_nonproject_or_unsafe_paths_are_never_rendered(path: str) -> None:
    from agentmonitor.composition.billing_worker import format_worker_failure

    result = format_worker_failure("collect", "ValueError", path, 123)
    assert result.endswith("source=unknown:0")
    assert "private" not in result


def test_unknown_type_and_phase_are_closed_and_invalid_line_is_suppressed() -> None:
    from agentmonitor.composition.billing_worker import format_worker_failure

    assert (
        format_worker_failure(
            "private phase", "PrivateValueError", "composition/billing_worker.py", -1
        )
        == "BILLING_WORKER_FAILURE phase=unknown type=Exception source=unknown:0"
    )


def test_known_repository_error_is_retained_without_its_arguments() -> None:
    from agentmonitor.composition.billing_worker import format_worker_failure

    assert format_worker_failure(
        "initialize",
        "BudgetCollectionError",
        "adapters/persistence/collection_control/sqlite/budget.py",
        50,
    ).endswith(
        "type=BudgetCollectionError "
        "source=backend/src/agentmonitor/adapters/persistence/collection_control/sqlite/budget.py:50"
    )


def test_actual_local_lock_contention_type_is_retained_without_message() -> None:
    from agentmonitor.composition.billing_worker import format_worker_failure

    assert "type=BlockingIOError " in format_worker_failure(
        "collect",
        "BlockingIOError",
        "adapters/persistence/registry/sqlite/credential_guard.py",
        28,
    )
