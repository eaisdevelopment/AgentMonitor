"""Conservative financial-query eligibility; pure metadata, no I/O."""

from dataclasses import replace

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ResourceKindV1

from backend.tests.capacity.pure.test_budget_overview import _account, _resource


@pytest.mark.parametrize("provider", ("claude", "codex"))
def test_established_subscription_only_account_needs_no_financial_query(
    provider: str,
) -> None:
    from agentmonitor.modules.capacity.domain.budget_overview import (
        requires_financial_query,
    )

    account = replace(
        _account(), provider_key=provider, initial_connection_purpose=None
    )
    resource = _resource("subscription_pool")
    assert not requires_financial_query(account, (resource,))
    assert not requires_financial_query(
        account,
        (
            resource,
            replace(resource, resource_id=OpaqueIdV1("retired"), lifecycle="retired"),
        ),
    )


@pytest.mark.parametrize(
    "kind",
    (
        "api_organization",
        "api_project",
        "workspace",
        "prepaid_credit_pool",
        "local_runtime_pool",
        "provider_specific",
        "unknown",
    ),
)
@pytest.mark.parametrize("retired", (False, True))
def test_any_non_subscription_resource_preserves_financial_query(
    kind: ResourceKindV1,
    retired: bool,
) -> None:
    from agentmonitor.modules.capacity.domain.budget_overview import (
        requires_financial_query,
    )

    account = replace(_account(), initial_connection_purpose=None)
    extra = _resource(kind, "other-resource")
    if retired:
        extra = replace(extra, lifecycle="retired")
    assert requires_financial_query(account, (_resource("subscription_pool"), extra))


def test_pending_api_unknown_and_cloud_accounts_keep_their_read_path() -> None:
    from agentmonitor.modules.capacity.domain.budget_overview import (
        requires_financial_query,
    )

    resource = _resource("subscription_pool")
    assert requires_financial_query(_account(), (resource,))
    account = replace(_account(), initial_connection_purpose=None)
    assert requires_financial_query(account, ())
    assert requires_financial_query(account, (replace(resource, lifecycle="retired"),))
    assert requires_financial_query(account, (replace(resource, lifecycle="archived"),))
    assert requires_financial_query(
        replace(account, provider_key="ollama"), (resource,)
    )
    assert requires_financial_query(
        replace(account, provider_key="unknown"), (resource,)
    )


def test_resource_list_at_its_bound_cannot_prove_subscription_only() -> None:
    from agentmonitor.modules.capacity.domain.budget_overview import (
        requires_financial_query,
    )

    account = replace(_account(), initial_connection_purpose=None)
    resources = tuple(
        _resource("subscription_pool", f"resource-{i}") for i in range(100)
    )
    assert not requires_financial_query(account, resources[:99])
    assert requires_financial_query(account, resources)
