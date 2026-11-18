"""Recover actual abandoned subscription work only in a private real snapshot."""

import os
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.collection_control.application.queries import (
    source_poll_is_due_v1,
)

from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


def test_genuine_abandoned_subscription_run_recovers_without_provider_io(
    tmp_path: Path,
) -> None:
    source_name = os.environ.get("AGENTMONITOR_M7_ABANDONED_SOURCE_DATABASE")
    if source_name is None:
        reference = _private_real_copy(tmp_path)
    else:
        # An unchanged genuine incident snapshot keeps this regression usable
        # after production has recovered. It never supplies provider responses.
        source = Path(source_name)
        assert source.is_absolute() and source.is_file()
        os.chmod(tmp_path, 0o700)
        copied = tmp_path / "agentmonitor.db"
        os.close(os.open(copied, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as original:
            with sqlite3.connect(copied) as target:
                original.backup(target)
        reference = DatabaseRefV1(copied, tmp_path)
    now = datetime.now(UTC)
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            row = connection.exec_driver_sql(
                "SELECT r.run_id,r.provider_key,r.source_id,owner.heartbeat_at "
                "FROM collection_run r JOIN collection_lease l ON l.run_id=r.run_id "
                "JOIN collection_scheduler_instance owner "
                "ON owner.instance_id=l.owner_instance_id "
                "WHERE r.capability_id='subscription.quota' AND r.state='running' "
                "AND r.deadline_at<? AND l.expires_at<? AND owner.heartbeat_at<? "
                "ORDER BY r.requested_at LIMIT 1",
                (
                    now.isoformat().replace("+00:00", "Z"),
                    now.isoformat().replace("+00:00", "Z"),
                    (now - timedelta(seconds=120)).isoformat().replace("+00:00", "Z"),
                ),
            ).first()
    assert row is not None, "genuine_abandoned_subscription_run_required"
    run_id, provider, source, heartbeat = row
    repository = SqliteCollectionRepositoryV1(reference)
    before = repository.get_run(OpaqueIdV1(run_id))
    assert before is not None and before.state == "running"
    assert not source_poll_is_due_v1(now, before, 300000)

    from agentmonitor.modules.collection_control.application.source_recovery import (
        RecoverExpiredSourceRunsV1,
    )

    recover = RecoverExpiredSourceRunsV1(repository)
    arguments = dict(
        provider_key=provider,
        capability_id="subscription.quota",
        source_id=source,
        as_of=now,
        recovery_instance_id=OpaqueIdV1("private-expired-source-recovery"),
    )
    # The actual recorded heartbeat is newer than this conservative cutoff.
    assert (
        recover(
            **arguments,
            owner_stale_before=datetime.fromisoformat(heartbeat)
            - timedelta(microseconds=1),
        )
        == ()
    )
    assert repository.get_run(before.run_id) == before
    failures = recover(**arguments, owner_stale_before=now - timedelta(seconds=120))
    assert before.run_id in {failure.run_id for failure in failures}
    after = repository.get_run(before.run_id)
    assert after is not None and after.state == "failed"
    assert after.error_code == "collection_worker_interrupted"
    assert (
        after.requested_at == before.requested_at
        and after.started_at == before.started_at
    )
    assert after.fencing_token > before.fencing_token
    assert after.payload_digest is None and after.observation_ids == ()
    assert source_poll_is_due_v1(now, after, 300000)
    assert recover(**arguments, owner_stale_before=now - timedelta(seconds=120)) == ()
