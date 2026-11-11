"""Actual account query with empty migrated storage, no financial fixtures."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    SqliteBillingConnectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCredentialBindingsV1,
)
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1
from agentmonitor.modules.capacity.application.budget_queries import (
    GetAccountBudgetCurrentV1,
)
from agentmonitor.modules.registry.domain.credential_binding import (
    resolve_active_credential_binding,
)

from backend.tests.integration.registry.test_billing_connections import (
    _account,
    _command,
)


def test_absent_account_does_not_become_an_empty_financial_account(
    tmp_path: Path,
) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    query = GetAccountBudgetCurrentV1(
        SqliteBillingConnectionRepositoryV1(ref),
        SqliteBudgetReportRepositoryV1(ref),
        SqliteCollectionRepositoryV1(ref),
    )
    now = datetime.now(UTC)
    assert (
        query(
            OpaqueIdV1("not-enrolled"),
            period=BudgetPeriodV1(now - timedelta(days=7), now),
            as_of=now,
        )
        is None
    )


def test_account_query_rechecks_real_active_binding_metadata(tmp_path: Path) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    account = _account(ref)
    registry = SqliteBillingConnectionRepositoryV1(ref)
    registry.create(replace(_command(account), scope_id=None))
    bindings = SqliteCredentialBindingsV1(ref)
    reads: list[OpaqueIdV1] = []

    def active_binding(account_id: OpaqueIdV1) -> ActiveCredentialBindingRefV1 | None:
        current = resolve_active_credential_binding(bindings.read(account_id))
        reads.append(account_id)
        return current

    query = GetAccountBudgetCurrentV1(
        registry,
        SqliteBudgetReportRepositoryV1(ref),
        SqliteCollectionRepositoryV1(ref),
        active_binding=active_binding,
    )
    now = datetime.now(UTC)
    result = query(
        account.account_id,
        period=BudgetPeriodV1(now - timedelta(days=7), now),
        as_of=now,
    )
    assert result is not None
    assert result.availability.state == "available"
    assert len(result.resources) == 1
    assert result.resources[0].reports == ()
    assert reads == [account.account_id, account.account_id]


def test_binding_metadata_read_failure_does_not_fall_back_to_account_read(
    tmp_path: Path,
) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    account = _account(ref)
    unavailable = SqliteCredentialBindingsV1(
        DatabaseRefV1(
            tmp_path / "unavailable" / "agentmonitor.db", tmp_path / "unavailable"
        )
    )

    def active_binding(account_id: OpaqueIdV1) -> ActiveCredentialBindingRefV1 | None:
        return resolve_active_credential_binding(unavailable.read(account_id))

    query = GetAccountBudgetCurrentV1(
        SqliteBillingConnectionRepositoryV1(ref),
        SqliteBudgetReportRepositoryV1(ref),
        SqliteCollectionRepositoryV1(ref),
        active_binding=active_binding,
    )
    now = datetime.now(UTC)
    result = query(
        account.account_id,
        period=BudgetPeriodV1(now - timedelta(days=7), now),
        as_of=now,
    )
    assert result is not None
    assert result.availability.state == "unavailable"
    assert result.availability.reason_code == "budget_account_query_unavailable"
    assert result.resources == ()
    assert result.funds is None


def test_existing_four_argument_query_reads_empty_registered_account(
    tmp_path: Path,
) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    account = _account(ref)
    registry = SqliteBillingConnectionRepositoryV1(ref)
    registry.create(replace(_command(account), scope_id=None))
    query = GetAccountBudgetCurrentV1(
        registry,
        SqliteBudgetReportRepositoryV1(ref),
        SqliteCollectionRepositoryV1(ref),
        None,
    )
    now = datetime.now(UTC)
    result = query(
        account.account_id,
        period=BudgetPeriodV1(now - timedelta(days=7), now),
        as_of=now,
    )
    assert result is not None
    assert result.availability.state == "available"
    assert len(result.resources) == 1
    assert result.resources[0].reports == ()
