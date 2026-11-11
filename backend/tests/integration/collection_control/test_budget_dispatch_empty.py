"""Actual empty SQLite dispatch; no fabricated queued runs or provider state."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.collection_control.sqlite.budget import (
    BudgetCollectionError,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetCollectionInputV1,
    BudgetReportInputV1,
)
from agentmonitor.contracts.collection_control_v1 import (
    BudgetCollectionRunAdmissionV1,
    CollectionFailedV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import CollectionOutcomeV1


def test_empty_retry_lookup_does_not_create_provider_or_collection_rows(
    tmp_path: Path,
) -> None:
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        open_sqlite_database,
    )
    from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
        migrate_to_head,
    )
    from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
        _budget_retry_after,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    with open_sqlite_database(ref, "runtime_read_only") as handle:
        with handle.connect() as connection:
            assert (
                _budget_retry_after(connection, "absent-scope", "requests", "request")
                is None
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM collection_run"
                ).scalar_one()
                == 0
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM collection_budget_reservation"
                ).scalar_one()
                == 0
            )


def test_dispatch_without_registry_fence_refuses_before_database_open(
    tmp_path: Path,
) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    repository = SqliteCollectionRepositoryV1(ref)
    with pytest.raises(BudgetCollectionError, match="budget_admission_fence_required"):
        repository.claim_next_budget_run(
            scheduler_instance_id=OpaqueIdV1("absent-worker"),
            as_of=datetime.now(UTC),
            # Missing authority must reject before this invalid callback is used.
            resolve_budget_limit=cast(Callable[[str, str], int], None),
            provider_key="claude",
            capability_id="api.billing",
            source_id="anthropic.api.cost.v1",
            manifest_fingerprint="a" * 64,
            collection_policy_version="1.0.0",
            operation_family="billing.cost.7d",
        )
    assert not (tmp_path / "agentmonitor.db").exists()


def test_claimed_execution_refuses_without_authority_before_callbacks(
    tmp_path: Path,
) -> None:
    from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
        SqliteBudgetReportRepositoryV1,
    )
    from agentmonitor.modules.collection_control.application.budget_executor import (
        ExecuteBudgetCollectionRunV1,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    executor = ExecuteBudgetCollectionRunV1(
        SqliteCollectionRepositoryV1(ref), SqliteBudgetReportRepositoryV1(ref)
    )
    now = datetime.now(UTC)
    with pytest.raises(BudgetCollectionError, match="budget_admission_fence_required"):
        # These intentionally invalid inputs prove the authority guard runs first.
        executor.execute_claimed(
            cast(BudgetCollectionRunAdmissionV1, None),
            cast(Callable[[], CollectionOutcomeV1[BudgetReportInputV1]], None),
            cast(
                Callable[
                    [
                        BudgetCollectionRunAdmissionV1,
                        CollectionOutcomeV1[BudgetReportInputV1],
                        datetime,
                    ],
                    BudgetCollectionInputV1 | CollectionFailedV1,
                ],
                None,
            ),
            as_of=now,
            completed_at=now,
        )
    assert not (tmp_path / "agentmonitor.db").exists()


def test_empty_expired_run_recovery_creates_no_owner_or_results(tmp_path: Path) -> None:
    from datetime import timedelta

    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        open_sqlite_database,
    )
    from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
        migrate_to_head,
    )
    from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
        SqliteBudgetReportRepositoryV1,
    )
    from agentmonitor.modules.collection_control.application.budget_executor import (
        ExecuteBudgetCollectionRunV1,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    executor = ExecuteBudgetCollectionRunV1(
        SqliteCollectionRepositoryV1(ref), SqliteBudgetReportRepositoryV1(ref)
    )
    now = datetime.now(UTC)
    assert (
        executor.recover_expired_runs(
            provider_key="claude",
            capability_id="api.cost",
            source_id="anthropic.analytics.cost.v1",
            as_of=now,
            owner_stale_before=now - timedelta(seconds=120),
            recovery_instance_id=OpaqueIdV1("empty-recovery-owner"),
            recovery_lease_expires_at=now + timedelta(seconds=30),
            maximum_runs=16,
        )
        == ()
    )
    with open_sqlite_database(ref, "runtime_read_only") as handle:
        with handle.connect() as connection:
            for table in (
                "collection_run",
                "collection_scheduler_instance",
                "collection_lease",
                "capacity_commit_receipt",
            ):
                assert (
                    connection.exec_driver_sql(
                        f"SELECT count(*) FROM {table}"
                    ).scalar_one()
                    == 0
                )


def test_actual_source_policy_claims_nothing_from_empty_database(
    tmp_path: Path,
) -> None:
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        open_sqlite_database,
    )
    from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
        migrate_to_head,
    )
    from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
        ensure_billing_access_in_transaction,
    )
    from agentmonitor.adapters.providers.claude.anthropic_api.policy import SOURCE_ID
    from agentmonitor.composition.billing_run import (
        ANTHROPIC_COST_COLLECTION_POLICY_VERSION_V1,
        ANTHROPIC_COST_OPERATION_FAMILY_V1,
        anthropic_billing_budget_limit,
        anthropic_cost_manifest_fingerprint,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    repository = SqliteCollectionRepositoryV1(
        ref, billing_admission_fence=ensure_billing_access_in_transaction
    )
    assert (
        repository.claim_next_budget_run(
            scheduler_instance_id=OpaqueIdV1("empty-dispatch-worker"),
            as_of=datetime.now(UTC),
            resolve_budget_limit=anthropic_billing_budget_limit,
            provider_key="claude",
            capability_id="api.cost",
            source_id=SOURCE_ID,
            manifest_fingerprint=anthropic_cost_manifest_fingerprint(),
            collection_policy_version=ANTHROPIC_COST_COLLECTION_POLICY_VERSION_V1,
            operation_family=ANTHROPIC_COST_OPERATION_FAMILY_V1,
        )
        is None
    )
    with open_sqlite_database(ref, "runtime_read_only") as handle:
        with handle.connect() as connection:
            for table in (
                "collection_run",
                "collection_scheduler_instance",
                "collection_lease",
                "collection_budget_reservation",
            ):
                assert (
                    connection.exec_driver_sql(
                        f"SELECT count(*) FROM {table}"
                    ).scalar_one()
                    == 0
                )


@pytest.mark.parametrize("fingerprint", ["a" * 32, "g" * 64, "A" * 64])
def test_dispatch_rejects_non_audit_fingerprint_before_database_open(
    tmp_path: Path,
    fingerprint: str,
) -> None:
    from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
        ensure_billing_access_in_transaction,
    )
    from agentmonitor.composition.billing_run import anthropic_billing_budget_limit

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    repository = SqliteCollectionRepositoryV1(
        ref, billing_admission_fence=ensure_billing_access_in_transaction
    )
    with pytest.raises(BudgetCollectionError, match="budget_dispatch_query_invalid"):
        repository.claim_next_budget_run(
            scheduler_instance_id=OpaqueIdV1("absent-worker"),
            as_of=datetime.now(UTC),
            resolve_budget_limit=anthropic_billing_budget_limit,
            provider_key="claude",
            capability_id="api.cost",
            source_id="anthropic.analytics.cost.v1",
            manifest_fingerprint=fingerprint,
            collection_policy_version="1.0.0",
            operation_family="billing.anthropic.cost.7d",
        )
    assert not (tmp_path / "agentmonitor.db").exists()


def test_latest_budget_run_from_empty_database_is_absent(tmp_path: Path) -> None:
    from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
        migrate_to_head,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    repository = SqliteCollectionRepositoryV1(ref)
    assert (
        repository.get_latest_budget_run(
            OpaqueIdV1("absent-account"),
            OpaqueIdV1("absent-resource"),
            1,
            datetime.now(UTC),
        )
        is None
    )
