"""Read genuine existing funds through public ports, without provider calls."""

from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.api.funds_projection import project_funds
from agentmonitor.composition.budget_funds import StoredAccountBudgetFundsV1
from agentmonitor.contracts.capacity_v1 import QuotaWindowViewV2
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1
from agentmonitor.modules.capacity.application.queries import ListQuotaWindowsV1
from agentmonitor.modules.registry.application.accounts import (
    CapacityScopeMembershipQueryV2,
)
from agentmonitor.modules.registry.domain.credential_binding import (
    resolve_active_credential_binding,
)


def test_genuine_funds_require_current_run_lineage() -> None:
    root = Path("/home/dev/.local/share/agentmonitor")
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    registry = SqliteRegistryRepositoryV1(reference)
    membership = CapacityScopeMembershipQueryV2(registry)
    windows = ListQuotaWindowsV1(SqliteCapacityRepositoryV1(reference))
    bindings = SqliteCredentialBindingsV1(reference)
    runs = SqliteCollectionRepositoryV1(reference)
    binding_reads: list[OpaqueIdV1] = []

    def active_binding(account: OpaqueIdV1) -> ActiveCredentialBindingRefV1 | None:
        result = resolve_active_credential_binding(bindings.read(account))
        binding_reads.append(account)
        return result

    now = datetime.now(UTC)
    candidates = []
    for account in registry.list_accounts(provider_key="ollama", page_size=100):
        stored = tuple(
            component
            for window in windows(account.account_id, as_of=now)
            if isinstance(window, QuotaWindowViewV2)
            and (component := project_funds(window, as_of=now)) is not None
        )
        if stored and resolve_active_credential_binding(
            bindings.read(account.account_id)
        ):
            candidates.append((account.account_id, stored))
    assert candidates, "genuine_stored_funds_with_active_binding_required"
    account_id, stored = candidates[0]
    unproven = StoredAccountBudgetFundsV1(membership, windows)(account_id, as_of=now)
    assert unproven.components == (), "unproven_lineage_must_not_be_current"
    assert unproven.availability.reason_code == "funds_lineage_unavailable"

    result = StoredAccountBudgetFundsV1(
        membership, windows, active_binding=active_binding, get_run=runs.get_run
    )(account_id, as_of=now)
    assert result.components, "genuine_current_funds_required"
    assert binding_reads == [account_id, account_id]
    for component in result.components:
        assert component in stored
        run = runs.get_run(component.collection_run_id)
        binding = resolve_active_credential_binding(bindings.read(account_id))
        assert binding is not None
        assert run.account_id == account_id
        assert run.resource_id == component.subject.resource_id
        assert run.target_generation == binding.generation
        assert component.observation_id in run.observation_ids
