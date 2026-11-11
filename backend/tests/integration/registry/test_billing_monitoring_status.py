"""Real owner-metadata boundaries; no keys or synthetic provider reports."""

from pathlib import Path

from agentmonitor.contracts.common_v1 import OpaqueIdV1

from backend.tests.integration.registry.test_billing_connections import (
    _account,
    _command,
    _database,
)


def test_missing_credentials_never_offer_enable(tmp_path: Path) -> None:
    from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
        SqliteBillingConnectionRepositoryV1,
    )
    from agentmonitor.composition.billing_monitoring import BillingMonitoringActionsV1

    reference = _database(tmp_path)
    account = _account(reference)
    connection = SqliteBillingConnectionRepositoryV1(reference).create(
        _command(account)
    )
    service = BillingMonitoringActionsV1(reference)
    status = service.get_status(account.account_id, connection.resource_id)
    assert status is not None
    assert not status.can_enable and not status.can_disable
    assert status.reason_code == "billing_monitoring_credential_required"
    assert status.verified_run_id is None and status.verified_at is None
    assert status.binding_generation is None
    assert status.connection == connection
    assert service.get_status(account.account_id, OpaqueIdV1("missing")) is None
