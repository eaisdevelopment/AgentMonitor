"""Pure V2 capacity target serialization never invents an installation."""

from agentmonitor.api.v1.routers.capacity import _subject
from agentmonitor.contracts.capacity_v1 import CapacitySubjectV2
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ProviderTargetRefV1


def test_cloud_subject_serializes_as_cloud_target() -> None:
    target = ProviderTargetRefV1("cloud_service", OpaqueIdV1("amat_" + "a" * 32))
    result = _subject(
        CapacitySubjectV2("ollama", target, OpaqueIdV1("acct"), OpaqueIdV1("resource"))
    )
    assert result.model_dump()["provider_target_kind"] == "cloud_service"
    assert result.model_dump()["provider_target_id"] == target.target_id.value
    assert "installation_id" not in result.model_dump()


def test_cloud_capacity_routes_are_versioned_without_changing_v1_subject() -> None:
    from agentmonitor.composition.bootstrap import create_iam_schema_application

    schema = create_iam_schema_application().openapi()
    paths = schema["paths"]
    assert "/api/v1/accounts/{account_id}/capacity/v2" in paths
    assert "/api/v1/accounts/{account_id}/quotas/v2" in paths
    assert "/api/v1/capacity/history/v2" in paths
    original = schema["components"]["schemas"]["CapacitySubjectWireV1"]
    assert "installation_id" in original["required"]
    assert "provider_target_id" not in original["properties"]
