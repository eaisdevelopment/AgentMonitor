"""Real empty database migration exposes durable cloud scheduler bookkeeping."""

# ruff: noqa: E501 -- use the explicit M04 adapter path.

from pathlib import Path

from sqlalchemy import inspect

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)


def test_cloud_lane_and_attempt_journal_exist(tmp_path: Path) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    with open_sqlite_database(reference, "runtime_read_only") as database:
        with database.connect() as connection:
            tables = set(inspect(connection).get_table_names())
            assert {
                "collection_cloud_schedule_lane",
                "collection_cloud_attempt_journal",
            } <= tables


def test_empty_real_registry_has_no_cloud_candidate(tmp_path: Path) -> None:
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from agentmonitor.adapters.persistence.collection_control.sqlite.ollama_cloud_admission import (
        SqliteOllamaCloudAdmissionRepositoryV1,
    )
    from agentmonitor.contracts.collection_control_v1 import OllamaCloudRequestAcquireV1
    from agentmonitor.contracts.common_v1 import OpaqueIdV1

    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    now = datetime.now(UTC)
    decision = SqliteOllamaCloudAdmissionRepositoryV1(reference).acquire(
        OllamaCloudRequestAcquireV1(
            admission_id=OpaqueIdV1("admission-" + uuid4().hex),
            scheduler_instance_id=OpaqueIdV1("scheduler-" + uuid4().hex),
            requested_at=now,
            lease_expires_at=now + timedelta(seconds=30),
            jitter_seconds=0,
        )
    )
    assert decision.state == "no_candidate" and decision.lease is None
