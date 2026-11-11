"""Real migrated empty storage cannot grant billing access or commit authority."""

from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.registry.sqlite import (
    billing_connections as storage,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def test_missing_target_has_no_authority_and_reads_do_not_write(tmp_path: Path) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    repository = storage.SqliteBillingAccessRepositoryV1(reference)
    assert (
        repository.resolve(OpaqueIdV1("absent"), OpaqueIdV1("absent"), "verification")
        is None
    )
    assert (
        repository.resolve(OpaqueIdV1("absent"), OpaqueIdV1("absent"), "monitoring")
        is None
    )
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            for table in (
                "reg_account",
                "reg_billing_connection",
                "reg_credential_binding",
            ):
                assert (
                    connection.exec_driver_sql(
                        f"SELECT count(*) FROM {table}"
                    ).scalar_one()
                    == 0
                )
            assert (
                connection.exec_driver_sql("PRAGMA integrity_check").scalar_one()
                == "ok"
            )


def test_transaction_is_required_before_target_lookup(tmp_path: Path) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            assert not connection.in_transaction()
            with pytest.raises(ValueError, match="billing_transaction_required"):
                storage.resolve_billing_access_in_transaction(
                    connection,
                    OpaqueIdV1("absent"),
                    OpaqueIdV1("absent"),
                    "verification",
                )
