"""Pure scope-target fencing, with no registry or provider I/O."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from backend.tests.capacity.pure.test_alert_conditions import _window
from backend.tests.capacity.pure.test_cloud_scope_v2 import _account

from agentmonitor.contracts.capacity_v1 import (
    AccountCapacityViewV1,
    CapacityAggregateQueryV2,
    InvalidCapacityContractV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    AccountResourceViewV1,
    MaskedRegistryFieldV1,
    RegistryLocalResourceTargetV2,
    RegistryScopeSnapshotV2,
)
from agentmonitor.modules.capacity.domain.aggregation import aggregate_capacity_v2
from agentmonitor.modules.capacity.domain.health import (
    default_capacity_health_policy_v1,
)


def test_local_scope_rejects_wrong_installation() -> None:
    now = datetime(2026, 11, 2, tzinfo=UTC)
    oid = OpaqueIdV1
    account = _account("account")
    resource = AccountResourceViewV1(
        oid("resource"),
        account.account_id,
        "subscription_pool",
        None,
        MaskedRegistryFieldV1("withheld", None, "identity_privacy_minimized"),
        "active",
        (oid("profile"),),
        1,
        7,
        now,
        now,
    )
    target = RegistryLocalResourceTargetV2(
        resource.resource_id,
        account.account_id,
        "ollama",
        oid("actual-installation"),
        7,
    )
    snapshot = RegistryScopeSnapshotV2(
        "account",
        account.account_id,
        (oid("organization"),),
        (account.account_id,),
        (resource.resource_id,),
        (),
        "complete",
        7,
        (target,),
    )
    query = CapacityAggregateQueryV2(
        snapshot, (account,), (resource,), now, default_capacity_health_policy_v1()
    )
    window = _window()
    valid_subject = replace(
        window.subject,
        provider_key="ollama",
        installation_id=oid("actual-installation"),
    )
    valid_window = replace(window, subject=valid_subject, registry_revision=7)
    assert (
        aggregate_capacity_v2(
            query, (AccountCapacityViewV1(valid_subject, (valid_window,), None),)
        ).covered_account_count
        == 1
    )
    wrong_subject = replace(
        window.subject, provider_key="ollama", installation_id=oid("wrong-installation")
    )
    wrong_window = replace(window, subject=wrong_subject, registry_revision=7)
    with pytest.raises(
        InvalidCapacityContractV1, match="capacity_aggregate_subject_outside_scope"
    ):
        aggregate_capacity_v2(
            query, (AccountCapacityViewV1(wrong_subject, (wrong_window,), None),)
        )
    wrong_provider = replace(valid_subject, provider_key="claude")
    with pytest.raises(
        InvalidCapacityContractV1, match="capacity_aggregate_subject_outside_scope"
    ):
        aggregate_capacity_v2(
            query,
            (
                AccountCapacityViewV1(
                    wrong_provider,
                    (replace(valid_window, subject=wrong_provider),),
                    None,
                ),
            ),
        )


def test_unresolved_wire_schema_forbids_numeric_totals() -> None:
    from agentmonitor.api.v1.schemas.capacity import CapacityWindowGroupWireV2

    schema = CapacityWindowGroupWireV2.model_json_schema()
    assert schema["properties"]["numeric_values"]["maxItems"] == 0


def test_target_kind_must_be_known() -> None:
    from agentmonitor.contracts.registry_v1 import ProviderTargetRefV1

    with pytest.raises(ValueError):
        ProviderTargetRefV1("unexpected", OpaqueIdV1("target"))  # type: ignore[arg-type]


def test_provider_scope_rejects_local_targets_of_another_provider() -> None:
    from agentmonitor.contracts.registry_v1 import (
        RegistryLocalResourceTargetV2,
        RegistryScopeSnapshotV2,
    )

    oid = OpaqueIdV1
    target = RegistryLocalResourceTargetV2(
        oid("resource"), oid("account"), "claude", oid("installation"), 7
    )
    with pytest.raises(ValueError, match="registry_scope_snapshot_invalid"):
        RegistryScopeSnapshotV2(
            "provider",
            oid("ollama"),
            (),
            (oid("account"),),
            (oid("resource"),),
            (),
            "complete",
            7,
            (target,),
        )
