"""Pure guards for the authorized cloud-schedule snapshot boundary."""

import pytest

from agentmonitor.adapters.persistence.integration.sqlite.ollama_cloud_schedule_snapshot import (  # noqa: E501
    OllamaCloudScheduleSnapshotErrorV1,
    _require_authorized_snapshot_inputs_v1,
)
from agentmonitor.contracts.cloud_schedule_status_v1 import CloudScheduleStatusV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1


def _target() -> CloudScheduleStatusV1:
    return CloudScheduleStatusV1(
        schedule_id="schedule",
        target_key_digest="a" * 64,
        account_id="account",
        profile_id="profile",
        resource_id="resource",
        access_target_id="ollama-cloud-target-" + "b" * 32,
        target_generation=1,
    )


def _binding() -> ActiveCredentialBindingRefV1:
    return ActiveCredentialBindingRefV1(
        account_id=OpaqueIdV1("account"),
        binding_id=OpaqueIdV1("amcb_" + "c" * 32),
        generation=1,
    )


@pytest.mark.parametrize(
    "target,account_version,binding,fingerprint",
    (
        (object(), 1, _binding(), "d" * 64),
        (_target(), True, _binding(), "d" * 64),
        (_target(), 1, object(), "d" * 64),
        (_target(), 1, _binding(), "D" * 64),
    ),
)
def test_invalid_snapshot_inputs_fail_with_closed_error(
    target: object,
    account_version: object,
    binding: object,
    fingerprint: object,
) -> None:
    with pytest.raises(
        OllamaCloudScheduleSnapshotErrorV1,
        match="ollama_cloud_schedule_snapshot_unavailable",
    ):
        _require_authorized_snapshot_inputs_v1(
            target,
            account_version,
            binding,
            fingerprint,
        )
