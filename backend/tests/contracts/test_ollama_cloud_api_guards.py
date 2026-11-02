"""Pure wire-boundary checks; no HTTP or database I/O."""

import pytest

from agentmonitor.api.problem import ProblemError
from agentmonitor.api.v1.routers.provider_connections import (
    _ollama_cloud_conflict,
    _ollama_cloud_view,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import CredentialConnectionStatusV1
from agentmonitor.modules.registry.application.organizations import (
    RegistryCommandConflictV1,
)


def test_cloud_status_rejects_another_account() -> None:
    status = CredentialConnectionStatusV1(
        OpaqueIdV1("account-a"), "unavailable", False, None, None, "unavailable"
    )
    with pytest.raises(ProblemError):
        _ollama_cloud_view(status, OpaqueIdV1("account-b"))


def test_stale_account_version_is_precondition_failure() -> None:
    problem = _ollama_cloud_conflict(
        RegistryCommandConflictV1("registry_account_version_conflict")
    )
    assert problem.status == 412


def test_stale_concurrently_activated_account_reports_version_conflict() -> None:
    from agentmonitor.modules.registry.domain.cloud_verification import (
        decide_cloud_owner_assertion,
    )

    with pytest.raises(ValueError, match="registry_account_version_conflict"):
        decide_cloud_owner_assertion(
            account_provider="ollama",
            account_lifecycle="active",
            account_identity_state="owner_confirmed",
            account_monitoring_preference="enabled",
            account_record_version=2,
            expected_account_record_version=1,
            target_provider="ollama",
            target_lifecycle="active",
            binding_is_current=True,
        )


def test_registry_detail_rejects_wrong_account() -> None:
    from backend.tests.capacity.pure.test_cloud_scope_v2 import _account

    from agentmonitor.api.v1.routers.registry import _assert_account_matches

    with pytest.raises(ProblemError):
        _assert_account_matches(_account("account-a"), OpaqueIdV1("account-b"))


def test_cloud_enqueue_idempotency_conflict_maps_to_http_409() -> None:
    from agentmonitor.adapters.persistence.collection_control.sqlite.ollama_cloud_admission import (  # noqa: E501
        OllamaCloudAdmissionRepositoryErrorV1,
    )
    from agentmonitor.composition.ollama_cloud_connection import _enqueue_conflict

    error = _enqueue_conflict(
        OllamaCloudAdmissionRepositoryErrorV1(
            "ollama_cloud_verification_idempotency_conflict"
        )
    )
    assert error is not None
    assert _ollama_cloud_conflict(error).status == 409


def test_cloud_credential_update_contention_is_actionable_temporary_busy() -> None:
    from agentmonitor.adapters.persistence.collection_control.sqlite.ollama_cloud_admission import (  # noqa: E501
        OllamaCloudAdmissionRepositoryErrorV1,
    )
    from agentmonitor.api.problem import PROBLEM_DESCRIPTIONS
    from agentmonitor.composition.ollama_cloud_connection import _enqueue_conflict

    conflict = _enqueue_conflict(
        OllamaCloudAdmissionRepositoryErrorV1(
            "ollama_cloud_verification_credential_update_in_progress"
        )
    )
    assert conflict is not None
    problem = _ollama_cloud_conflict(conflict)
    assert problem.status == 409
    assert problem.code == "credential_update_in_progress"
    assert (
        PROBLEM_DESCRIPTIONS[problem.code] == "Another account update is in progress."
    )
