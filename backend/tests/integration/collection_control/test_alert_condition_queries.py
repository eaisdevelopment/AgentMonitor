"""Actual empty migrated SQLite boundary; no synthetic run/source data."""

import asyncio
import importlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def test_current_query_empty_real_schema_truth_and_no_provider_actions(
    tmp_path: Path,
) -> None:
    conditions = importlib.import_module(
        "agentmonitor.adapters.persistence.collection_control.sqlite.alert_conditions"
    )
    from agentmonitor.contracts.collection_control_v1 import CollectorAlertQueryV1

    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    repository = conditions.SqliteCollectorAlertConditionsV1(reference)
    now = datetime.now(UTC)
    query = CollectorAlertQueryV1(
        now, now + timedelta(seconds=2), OpaqueIdV1("collector-query")
    )
    result = asyncio.run(repository.get_current(query))
    assert result.items == () and result.availability.state == "available"
    refreshed = asyncio.run(repository.refresh(query))
    assert refreshed.items == () and refreshed.availability.state == "available"
    events = repository.read_events("m07", None, datetime.now(UTC), 100)
    assert events.events == () and events.availability.state == "available"
