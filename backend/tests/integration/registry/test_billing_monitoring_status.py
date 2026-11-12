"""Real owner-metadata boundaries; no keys or synthetic provider reports."""

from pathlib import Path

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1

from backend.tests.integration.registry.test_billing_connections import (
    _account,
    _command,
    _database,
)


@pytest.mark.parametrize("provider", ("claude", "codex"))
def test_missing_credentials_never_offer_enable(tmp_path: Path, provider: str) -> None:
    from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
        SqliteBillingConnectionRepositoryV1,
    )
    from agentmonitor.composition.billing_monitoring import BillingMonitoringActionsV1

    reference = _database(tmp_path)
    account = _account(reference, provider)
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


def test_openai_check_requires_real_credentials_instead_of_rejecting_provider(
    tmp_path: Path,
) -> None:
    import secrets
    from datetime import UTC, datetime

    from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
        SqliteBillingConnectionRepositoryV1,
    )
    from agentmonitor.composition.billing_actions import BillingCheckActionsV1
    from agentmonitor.contracts.billing_actions_v1 import BillingCheckCommandV1

    reference = _database(tmp_path)
    account = _account(reference, "codex")
    connections = SqliteBillingConnectionRepositoryV1(reference)
    connection = connections.create(_command(account))
    status = connections.get(account.account_id)
    assert status is not None
    command = BillingCheckCommandV1(
        account.account_id,
        connection.resource_id,
        status.account_record_version,
        connection.record_version,
        OpaqueIdV1("isolated-registry-owner"),
        OpaqueIdV1(secrets.token_urlsafe(24)),
        datetime.now(UTC),
    )
    with pytest.raises(ValueError, match="^billing_check_authority_unavailable$"):
        BillingCheckActionsV1(reference).check(command)
