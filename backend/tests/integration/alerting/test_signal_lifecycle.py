"""A genuine Claude capacity event crosses the installed composition boundary."""

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    MIGRATIONS_PATH,
    load_migration_catalog,
)
from agentmonitor.adapters.persistence.alerting.sqlite.capacity_consumer import (
    SqliteCapacityAlertRepositoryV1,
)
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.composition.alert_delivery import CapacityAlertDeliveryV1
from agentmonitor.modules.capacity.application.events import ReadCapacityEventsV1
from alembic import command as alembic_command
from alembic.config import Config

from backend.tests.integration.alerting.test_real_capacity_consumer import (
    _selected_actual_trigger,
)


def test_actual_capacity_event_commits_consumer_receipt_before_producer_ack(
    tmp_path: Path,
) -> None:
    _source, selected_event, account_id, _ = _selected_actual_trigger()
    copied = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    selected_root = os.environ.get("AGENTMONITOR_TEST_DATA_ROOT")
    assert selected_root is not None
    with sqlite3.connect(Path(selected_root) / "agentmonitor.db") as owner:
        with sqlite3.connect(tmp_path / "agentmonitor.db") as target:
            owner.backup(target)
    os.chmod(tmp_path / "agentmonitor.db", 0o600)
    catalog = load_migration_catalog()
    with open_sqlite_database(copied, "migration_existing") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            config = Config()
            config.set_main_option("script_location", str(MIGRATIONS_PATH))
            config.attributes.update(
                connection=connection,
                migrations_path=MIGRATIONS_PATH,
                catalog_digest=catalog.digest,
            )
            alembic_command.upgrade(config, catalog.head)
            connection.commit()
    delivery = CapacityAlertDeliveryV1(copied)
    receipt = delivery.deliver_one(selected_event, account_id, as_of=datetime.now(UTC))
    assert receipt.event_id == selected_event.envelope.event_id
    assert (
        SqliteCapacityAlertRepositoryV1(copied).lookup_capacity_event(selected_event)
        == receipt
    )
    assert all(
        item.envelope.event_id != selected_event.envelope.event_id
        for item in ReadCapacityEventsV1(SqliteCapacityRepositoryV1(copied))(
            "m07-alert-capacity-v1", None, datetime.now(UTC), 200
        ).events
    )
    assert (
        delivery.deliver_one(selected_event, account_id, as_of=datetime.now(UTC))
        == receipt
    )
