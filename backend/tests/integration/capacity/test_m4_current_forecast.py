"""Read the selected genuine owner quota history; no telemetry is inserted."""

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    MIGRATIONS_PATH,
    InspectSchemaCompatibilityV1,
    application_schema_range,
    load_migration_catalog,
)
from agentmonitor.adapters.persistence.capacity.sqlite.current_events import (
    SqliteCapacityProjectionEventRepositoryV1,
)
from agentmonitor.adapters.persistence.capacity.sqlite.current_repository import (
    SqliteCurrentCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts import capacity_v1 as contracts
from agentmonitor.modules.capacity.application import events, queries
from agentmonitor.modules.capacity.application.current import (
    RefreshCurrentCapacityProjectionsV1,
)
from agentmonitor.modules.registry.application.accounts import ListAccountsV1
from alembic import command
from alembic.config import Config


def test_actual_history_has_a_distinct_durable_current_forecast_query() -> None:
    root_value = os.environ.get("AGENTMONITOR_TEST_DATA_ROOT")
    if root_value is None:
        pytest.skip("NOT RUN: select actual owner AgentMonitor data root")
    root = Path(root_value)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    capacity = SqliteCapacityRepositoryV1(reference)
    as_of = datetime.now(UTC)
    accounts = ListAccountsV1(SqliteRegistryRepositoryV1(reference))("claude")
    observed = next(
        (
            account
            for account in accounts
            if capacity.list_account_quota_windows(account.account_id, as_of)
        ),
        None,
    )
    if observed is None:
        pytest.skip("BLOCKED: selected owner database has no native quota history")
    entry = getattr(queries, "ListCurrentCapacityForecastsV1", None)
    assert callable(entry), "real current windows have no durable forecast query"
    query = contracts.CapacityForecastQueryV1(observed.account_id, None, None, as_of)
    page = entry(SqliteCurrentCapacityRepositoryV1(reference))(query)
    assert page.availability.state in {"available", "unavailable"}
    for item in page.items:
        assert item.forecast.generation > 0
        assert item.source_window_generation > 0
        if item.forecast.state != "available":
            assert item.forecast.earliest_exhaustion_at is None
            assert item.forecast.latest_exhaustion_at is None


def test_actual_commit_outbox_is_readable_by_distinct_projection_union() -> None:
    root_value = os.environ.get("AGENTMONITOR_TEST_DATA_ROOT")
    if root_value is None:
        pytest.skip("NOT RUN: select actual owner AgentMonitor data root")
    root = Path(root_value)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    quota = SqliteCapacityRepositoryV1(reference)
    as_of = datetime.now(UTC)
    existing = quota.read_capacity_events("m4-capacity-union-observer", None, as_of, 1)
    if not existing.events:
        pytest.skip("BLOCKED: selected owner database has no committed outbox")
    entry = getattr(events, "ReadCapacityProjectionEventsV1", None)
    assert callable(entry), (
        "commit history lacks distinct typed projection-event reader"
    )
    from agentmonitor.adapters.persistence.capacity.sqlite import current_events

    adapter_type = getattr(
        current_events, "SqliteCapacityProjectionEventRepositoryV1", None
    )
    assert adapter_type is not None, "separate closed union event adapter is absent"
    union = entry(adapter_type(reference))("m4-capacity-union-observer", None, as_of, 1)
    assert union.events[0].envelope.event_type == "capacity.committed.v1"


def test_genuine_owner_quota_copy_gets_durable_no_value_and_idempotent_events() -> None:
    root_value = os.environ.get("AGENTMONITOR_TEST_DATA_ROOT")
    if root_value is None:
        pytest.skip("NOT RUN: select actual owner AgentMonitor data root")
    source_path = Path(root_value) / "agentmonitor.db"
    with TemporaryDirectory(prefix="agentmonitor-m4-capacity-") as directory:
        root = Path(directory)
        target_path = root / "agentmonitor.db"
        with sqlite3.connect(f"file:{source_path}?mode=ro", uri=True) as source:
            with sqlite3.connect(target_path) as target:
                source.backup(target)
        target_path.chmod(0o600)
        reference = DatabaseRefV1(target_path, root)
        catalog = load_migration_catalog()
        with open_sqlite_database(reference, "migration_existing") as handle:
            with handle.connect() as connection:
                connection.exec_driver_sql("BEGIN IMMEDIATE")
                config = Config()
                config.set_main_option("script_location", str(MIGRATIONS_PATH))
                config.attributes.update(
                    connection=connection,
                    migrations_path=MIGRATIONS_PATH,
                    catalog_digest=catalog.digest,
                )
                command.upgrade(config, catalog.head)
                connection.commit()
        status = InspectSchemaCompatibilityV1(
            reference, application_schema_range(), "runtime_read_write"
        )
        assert status.state == "compatible"
        adapter = SqliteCurrentCapacityRepositoryV1(reference)
        as_of = datetime.now(UTC)
        first = RefreshCurrentCapacityProjectionsV1(adapter)(as_of, limit=32)
        if not first.items:
            pytest.skip("BLOCKED: actual copied owner data has no current quota window")
        with open_sqlite_database(reference, "runtime_read_only") as handle:
            with handle.connect() as connection:
                before = connection.exec_driver_sql(
                    "SELECT count(*) FROM capacity_event_outbox WHERE event_type IN "
                    "('capacity.forecast.changed.v1','capacity.availability.changed.v1')"
                ).scalar_one()
        repeated = RefreshCurrentCapacityProjectionsV1(adapter)(as_of, limit=32)
        with open_sqlite_database(reference, "runtime_read_only") as handle:
            with handle.connect() as connection:
                after = connection.exec_driver_sql(
                    "SELECT count(*) FROM capacity_event_outbox WHERE event_type IN "
                    "('capacity.forecast.changed.v1','capacity.availability.changed.v1')"
                ).scalar_one()
                first_new_sequence = connection.exec_driver_sql(
                    "SELECT min(producer_sequence) FROM capacity_event_outbox WHERE "
                    "event_type IN ('capacity.forecast.changed.v1',"
                    "'capacity.availability.changed.v1')"
                ).scalar_one()
        assert repeated.items == first.items
        assert before == after
        assert before >= len(first.items)
        union = events.ReadCapacityProjectionEventsV1(
            SqliteCapacityProjectionEventRepositoryV1(reference)
        )(
            "m4-capacity-projection-observer",
            str(first_new_sequence - 1),
            datetime.now(UTC),
            200,
        )
        assert union.events
        assert union.events[0].envelope.event_type in {
            "capacity.forecast.changed.v1",
            "capacity.availability.changed.v1",
        }
        assert isinstance(
            union.events[0].payload,
            (
                contracts.CapacityForecastChangedV1,
                contracts.CapacityAvailabilityChangedV1,
            ),
        )
        assert union.events[0].payload.generation == 1
        assert all(event.payload_digest for event in union.events)
        commit_only = SqliteCapacityRepositoryV1(reference).read_capacity_events(
            "m4-capacity-commit-only-observer",
            str(first_new_sequence - 1),
            datetime.now(UTC),
            200,
        )
        assert all(
            event.envelope.event_type == "capacity.committed.v1"
            for event in commit_only.events
        )
        for item in first.items:
            assert item.forecast.generation > 0
            assert item.source_window_generation > 0
            assert (
                item.forecast.state != "available" or item.source_reset_at is not None
            )
            assert item.forecast.state == "available" or (
                item.forecast.earliest_exhaustion_at is None
                and item.forecast.latest_exhaustion_at is None
            )
            availability = adapter.page_current_availability(
                contracts.CapacityAvailabilityQueryV1(
                    item.forecast.subject.account_id,
                    item.forecast.subject.resource_id,
                    None,
                    "capability",
                    as_of,
                )
            )
            assert all(
                condition.state != "available" for condition in availability.items
            )
