"""T007 billing action admission without credential or provider access."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.composition.billing_actions import (
    BillingCheckActionsV1,
    billing_check_identifiers,
)
from agentmonitor.contracts.billing_actions_v1 import BillingCheckCommandV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1

NOW = datetime(2026, 11, 11, 14, tzinfo=UTC)


def _command(
    *,
    account: str = "account-1",
    resource: str = "resource-1",
    principal: str = "principal-1",
    command: str = "command-1",
    requested_at: datetime = NOW,
) -> BillingCheckCommandV1:
    return BillingCheckCommandV1(
        account_id=OpaqueIdV1(account),
        resource_id=OpaqueIdV1(resource),
        expected_account_version=3,
        expected_connection_version=2,
        principal_id=OpaqueIdV1(principal),
        command_id=OpaqueIdV1(command),
        requested_at=requested_at,
    )


def test_check_identity_is_stable_for_exact_retry_and_scoped_to_owner_intent() -> None:
    first = billing_check_identifiers(_command())
    replay = billing_check_identifiers(
        _command(requested_at=NOW + timedelta(minutes=5))
    )
    other_principal = billing_check_identifiers(_command(principal="principal-2"))
    other_resource = billing_check_identifiers(_command(resource="resource-2"))

    assert replay == first
    assert other_principal.run_id != first.run_id
    assert other_resource.run_id == first.run_id
    assert other_resource.schedule_id != first.schedule_id
    assert other_resource.idempotency_key_digest != first.idempotency_key_digest


def test_empty_real_database_refuses_before_creating_target_or_run(
    tmp_path: Path,
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)

    with pytest.raises(ValueError, match="billing_check_target_unavailable"):
        BillingCheckActionsV1(reference).check(_command())

    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            for table in (
                "reg_provider_access_target",
                "collection_request",
                "collection_schedule",
                "collection_run",
                "collection_budget_reservation",
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
