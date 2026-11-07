"""Recover the actual abandoned cloud request on a private database copy."""

import os
import shutil
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    MIGRATIONS_PATH,
    load_migration_catalog,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.ollama_cloud_admission import (  # noqa: E501
    SqliteOllamaCloudAdmissionRepositoryV1,
)
from alembic import command
from alembic.config import Config

LIVE = Path("/home/dev/.local/share/agentmonitor/agentmonitor.db")


@pytest.fixture
def abandoned_copy(tmp_path: Path) -> Iterator[tuple[DatabaseRefV1, Path]]:
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    target = root / "agentmonitor.db"
    os.close(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
    try:
        with sqlite3.connect(f"file:{LIVE}?mode=ro", uri=True) as source:
            with sqlite3.connect(target) as copy:
                source.backup(copy)
                actual = copy.execute(
                    "SELECT j.phase FROM collection_ollama_cloud_gate g JOIN "
                    "collection_cloud_attempt_journal j ON "
                    "j.admission_id=g.active_admission_id"
                ).fetchone()
                if actual != ("dispatched",):
                    pytest.skip("actual_abandoned_cloud_dispatch_unavailable")
        ref = DatabaseRefV1(target, root)
        catalog = load_migration_catalog()
        with open_sqlite_database(ref, "runtime_read_write") as db:
            with db.connect() as connection:
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
        yield ref, target
    finally:
        shutil.rmtree(root)


def test_actual_abandoned_dispatch_recovers_without_inventing_response(
    abandoned_copy: tuple[DatabaseRefV1, Path],
) -> None:
    with sqlite3.connect(abandoned_copy[1]) as connection:
        before = connection.execute(
            "SELECT * FROM collection_cloud_attempt_journal"
        ).fetchall()
        gate = connection.execute(
            "SELECT next_allowed_at FROM collection_ollama_cloud_gate"
        ).fetchone()
    assert gate is not None
    now = datetime.now(UTC)
    repository = SqliteOllamaCloudAdmissionRepositoryV1(abandoned_copy[0])
    assert (
        repository.recover_rate_gate(now, owner_stale_before=now - timedelta(minutes=2))
        == "recovered"
    )
    with sqlite3.connect(abandoned_copy[1]) as connection:
        assert (
            connection.execute(
                "SELECT * FROM collection_cloud_attempt_journal"
            ).fetchall()
            == before
        )
        active, next_allowed = connection.execute(
            "SELECT active_admission_id,next_allowed_at FROM "
            "collection_ollama_cloud_gate"
        ).fetchone()
        assert active is None
        assert datetime.fromisoformat(
            next_allowed.replace("Z", "+00:00")
        ) >= now + timedelta(seconds=300)
        assert next_allowed >= gate[0]
        record = connection.execute(
            "SELECT reason, released_at FROM collection_cloud_uncertain_outcome"
        ).fetchone()
        assert (
            record is not None
            and record[0] == "abandoned_outcome_unknown"
            and record[1] is not None
        )
    assert (
        repository.recover_rate_gate(now, owner_stale_before=now - timedelta(minutes=2))
        == "idle"
    )


def test_actual_abandoned_dispatch_requires_owner_staleness(
    abandoned_copy: tuple[DatabaseRefV1, Path],
) -> None:
    with sqlite3.connect(abandoned_copy[1]) as connection:
        owner = connection.execute(
            "SELECT i.heartbeat_at FROM collection_ollama_cloud_gate g JOIN "
            "collection_ollama_cloud_admission a ON "
            "a.admission_id=g.active_admission_id JOIN "
            "collection_scheduler_instance i ON "
            "i.instance_id=a.scheduler_instance_id"
        ).fetchone()
        before = connection.execute(
            "SELECT * FROM collection_ollama_cloud_gate"
        ).fetchall()
    assert owner is not None
    observed = datetime.fromisoformat(owner[0].replace("Z", "+00:00"))
    repository = SqliteOllamaCloudAdmissionRepositoryV1(abandoned_copy[0])
    assert (
        repository.recover_rate_gate(
            datetime.now(UTC), owner_stale_before=observed - timedelta(seconds=1)
        )
        == "owner_active_or_unverified"
    )
    with sqlite3.connect(abandoned_copy[1]) as connection:
        assert (
            connection.execute("SELECT * FROM collection_ollama_cloud_gate").fetchall()
            == before
        )


def test_actual_orphan_finalizes_and_projects_uncertainty(
    abandoned_copy: tuple[DatabaseRefV1, Path],
) -> None:
    from agentmonitor.composition.ollama_cloud_collection import OllamaCloudCollectionV1
    from agentmonitor.contracts.collection_control_v1 import (
        OllamaCloudLatestSourceSignalQueryV1,
    )
    from agentmonitor.contracts.common_v1 import OpaqueIdV1

    with sqlite3.connect(abandoned_copy[1]) as connection:
        connection.row_factory = sqlite3.Row
        run = connection.execute(
            "SELECT r.* FROM collection_run r JOIN collection_cloud_attempt_journal "
            "j ON j.run_id=r.run_id JOIN collection_ollama_cloud_gate g ON "
            "g.active_admission_id=j.admission_id"
        ).fetchone()
        history = connection.execute(
            "SELECT * FROM collection_cloud_attempt_journal"
        ).fetchall()
        admissions = connection.execute(
            "SELECT * FROM collection_ollama_cloud_admission"
        ).fetchall()
    assert run is not None
    now = datetime.now(UTC)
    collector = OllamaCloudCollectionV1(abandoned_copy[0])
    result = collector.recover_journals(
        as_of=now,
        owner_stale_before=now - timedelta(minutes=2),
        recovery_lease_expires_at=now + timedelta(minutes=1),
    )
    assert result == ("recovered", 0, 1)
    repository = SqliteOllamaCloudAdmissionRepositoryV1(abandoned_copy[0])
    signal = repository.read_latest_source_signal(
        OllamaCloudLatestSourceSignalQueryV1(
            account_id=OpaqueIdV1(run["account_id"]),
            binding_generation=run["target_generation"],
            access_target_id=OpaqueIdV1(run["provider_target_id"]),
            capability_id=run["capability_id"],
            source_id=run["source_id"],
            adapter_version=run["adapter_version"],
            source_fingerprint=run["manifest_fingerprint"],
            payload_schema=run["payload_schema"],
            queried_at=now,
        )
    )
    assert signal.signal == "transient_failure"
    assert signal.dispatch_certainty == "may_have_started"
    assert signal.run_state == "failed"
    assert signal.gate_state == "not_due"
    assert signal.retry_at is not None and signal.retry_at >= now + timedelta(
        seconds=300
    )
    with sqlite3.connect(abandoned_copy[1]) as connection:
        connection.row_factory = sqlite3.Row
        assert (
            connection.execute(
                "SELECT * FROM collection_cloud_attempt_journal"
            ).fetchall()
            == history
        )
        assert (
            connection.execute(
                "SELECT * FROM collection_ollama_cloud_admission"
            ).fetchall()
            == admissions
        )
        finished = connection.execute(
            "SELECT state,error_code,provider_outcome_state FROM collection_run "
            "WHERE run_id=?",
            (run["run_id"],),
        ).fetchone()
        assert tuple(finished) == (
            "failed",
            "ollama_cloud_outcome_unknown",
            "provider_unavailable",
        )
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert collector.recover_journals(
        as_of=now,
        owner_stale_before=now - timedelta(minutes=2),
        recovery_lease_expires_at=now + timedelta(minutes=1),
    ) == ("idle", 0, 0)
