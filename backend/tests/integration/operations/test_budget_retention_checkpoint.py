"""Private filesystem checkpoints; genuine export integration uses M05 ports."""

import json
import zipfile
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.operations.budget_retention_checkpoint import (  # noqa: E501
    FilesystemBudgetRetentionCheckpointV1,
)
from agentmonitor.composition.budget_retention import (
    build_budget_retention,
    build_budget_retention_checkpoints,
)
from agentmonitor.contracts.capacity_retention_v1 import BudgetRetentionExportRecordV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.operations_v1 import OperationsParticipantRequestV1

from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)
from backend.tests.persistence.sqlite.migrations.test_m05_model_remainder import (
    migrate_revision,
)


@pytest.fixture(scope="module")
def genuine_export(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[OperationsParticipantRequestV1, tuple[BudgetRetentionExportRecordV1, ...]]:
    root = tmp_path_factory.mktemp("m08-genuine-export")
    reference = _private_real_copy(root)
    migrate_revision(reference, "v1_0736", "migration_existing")
    participant = build_budget_retention(reference, root / "checkpoints")
    now = datetime.now(UTC)
    request = OperationsParticipantRequestV1(
        OpaqueIdV1("private-export-check"),
        OpaqueIdV1("private-export-check"),
        now + timedelta(minutes=15),
        1,
        now + timedelta(days=1),
        1,
        None,
        None,
        None,
        None,
    )
    # Explicit future cutoff is only for this disposable copy. No host clock or
    # installed history is changed; the source facts/identities remain genuine.
    for _ in range(100):
        preview = participant.preview_expired(request)
        if preview.count:
            prepared = replace(request, preview_digest=preview.digest)
            records = participant.query_export_records(prepared)
            if len(records) != 1:
                pytest.fail("genuine_export_record_required", pytrace=False)
            return prepared, records
        if preview.next_cursor is None:
            break
        request = replace(request, cursor=preview.next_cursor)
    pytest.fail("genuine_eligible_export_required", pytrace=False)


def _store(root: Path) -> FilesystemBudgetRetentionCheckpointV1:
    return build_budget_retention_checkpoints(root)


def test_checkpoint_directory_refuses_symlink_and_unsafe_permissions(
    tmp_path: Path,
) -> None:
    actual = tmp_path / "actual"
    actual.mkdir(mode=0o700)
    linked = tmp_path / "linked"
    linked.symlink_to(actual, target_is_directory=True)
    with pytest.raises(ValueError, match="^budget_checkpoint_directory_unsafe$"):
        _store(linked)
    actual.chmod(0o755)
    with pytest.raises(ValueError, match="^budget_checkpoint_directory_unsafe$"):
        _store(actual)
    assert not tuple(actual.iterdir())


def test_checkpoint_directory_is_private_when_created(tmp_path: Path) -> None:
    root = tmp_path / "checkpoints"
    _store(root)
    assert root.stat().st_mode & 0o777 == 0o700
    assert not tuple(root.iterdir())


def test_genuine_checkpoint_is_exact_private_and_create_once(
    genuine_export: tuple[
        OperationsParticipantRequestV1, tuple[BudgetRetentionExportRecordV1, ...]
    ],
    tmp_path: Path,
) -> None:
    request, records = genuine_export
    root = tmp_path / "checkpoints"
    store = _store(root)
    identity = store.store(request, records)
    prepared = replace(request, checkpoint_id=identity)
    assert store.verify(prepared, records)
    archive = root / (identity.value + ".zip")
    before = archive.stat()
    assert before.st_mode & 0o777 == 0o600
    assert store.store(request, records) == identity
    after = archive.stat()
    assert (before.st_ino, before.st_size, before.st_mtime_ns) == (
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    with zipfile.ZipFile(archive) as saved:
        assert set(saved.namelist()) == {"manifest.json", "budget-reports-v1.ndjson"}
        manifest = json.loads(saved.read("manifest.json"))
        record = json.loads(saved.read("budget-reports-v1.ndjson"))
    original = records[0]
    if record["receipt"]["fact_ids"] != [
        fact.value for fact in original.receipt.fact_ids
    ]:
        pytest.fail("checkpoint_original_fact_ids_changed", pytrace=False)
    if record["report_id"] != original.report.report_id.value:
        pytest.fail("checkpoint_original_report_id_changed", pytrace=False)
    assert manifest["record_count"] == 1
    assert manifest["fact_count"] == len(original.receipt.fact_ids)
    assert datetime.fromisoformat(manifest["expires_at"]) - datetime.fromisoformat(
        manifest["created_at"]
    ) == timedelta(days=7)
    assert request.cutoff is not None
    assert not store.verify(
        replace(prepared, cutoff=request.cutoff + timedelta(days=1)), records
    )


def test_real_archive_corruption_and_permissions_refuse_verification(
    genuine_export: tuple[
        OperationsParticipantRequestV1, tuple[BudgetRetentionExportRecordV1, ...]
    ],
    tmp_path: Path,
) -> None:
    request, records = genuine_export
    root = tmp_path / "checkpoints"
    store = _store(root)
    identity = store.store(request, records)
    prepared = replace(request, checkpoint_id=identity)
    archive = root / (identity.value + ".zip")
    archive.chmod(0o644)
    assert not store.verify(prepared, records)
    archive.chmod(0o600)
    with archive.open("r+b") as damaged:
        damaged.write(b"broken")
    assert not store.verify(prepared, records)
    assert store.cleanup_expired(as_of=datetime.now(UTC) + timedelta(days=8)) == 0
    assert archive.exists()


def test_cleanup_only_removes_valid_expired_owned_archive(
    genuine_export: tuple[
        OperationsParticipantRequestV1, tuple[BudgetRetentionExportRecordV1, ...]
    ],
    tmp_path: Path,
) -> None:
    request, records = genuine_export
    root = tmp_path / "checkpoints"
    store = _store(root)
    identity = store.store(request, records)
    assert store.cleanup_expired(as_of=datetime.now(UTC)) == 0
    foreign = root / "unrelated.txt"
    foreign.write_text("unrelated")
    unrelated = tmp_path / "outside"
    unrelated.write_text("unrelated")
    link = root / ("budget-checkpoint-" + "f" * 64 + ".zip")
    link.symlink_to(unrelated)
    assert (
        store.cleanup_expired(as_of=datetime.now(UTC) + timedelta(days=8), limit=1) == 1
    )
    assert not (root / (identity.value + ".zip")).exists()
    assert foreign.exists() and link.is_symlink() and unrelated.exists()


def test_real_storage_cap_refuses_new_export_without_deleting_files(
    genuine_export: tuple[
        OperationsParticipantRequestV1, tuple[BudgetRetentionExportRecordV1, ...]
    ],
    tmp_path: Path,
) -> None:
    request, records = genuine_export
    root = tmp_path / "checkpoints"
    store = _store(root)
    retained = root / ("budget-checkpoint-" + "f" * 64 + ".zip")
    with retained.open("xb") as target:
        target.truncate(256 * 1024 * 1024)
    retained.chmod(0o600)
    with pytest.raises(ValueError, match="^budget_checkpoint_storage_limit$"):
        store.store(request, records)
    assert retained.stat().st_size == 256 * 1024 * 1024
    assert len(tuple(root.glob("*.zip"))) == 1


def test_genuine_prepared_checkpoint_recovers_original_operation(
    genuine_export: tuple[
        OperationsParticipantRequestV1, tuple[BudgetRetentionExportRecordV1, ...]
    ],
    tmp_path: Path,
) -> None:
    request, records = genuine_export
    store = _store(tmp_path / "checkpoints")
    identity = store.store(request, records)
    original = replace(request, preview_digest=None)
    recovered = store.find_prepared(original)
    if recovered != replace(request, checkpoint_id=identity):
        pytest.fail("checkpoint_original_intent_not_recovered", pytrace=False)
    assert (
        store.find_prepared(
            replace(original, operation_id=OpaqueIdV1("another-private-operation"))
        )
        is None
    )


def test_coordinator_recovers_stored_checkpoint_and_replays_original_request(
    tmp_path: Path,
) -> None:
    from agentmonitor.modules.operations.application.budget_retention import (
        run_budget_retention_batch,
    )

    from backend.tests.live.ollama.test_budget_retention_live import _prepared

    _, participant, checkpoints, bound, records = _prepared(tmp_path)
    # Real export, followed by no purge, is the interrupted boundary. Reopening
    # the real adapter must reuse it, and completed retry must reuse the audit.
    identity = checkpoints.store(bound, records)
    original = replace(bound, preview_digest=None)
    reopened = _store(tmp_path / "checkpoints")
    result = run_budget_retention_batch(original, participant, reopened)
    if result.count != 1 or result.outcome not in {"complete", "partial"}:
        pytest.fail("coordinator_did_not_purge_prepared_report", pytrace=False)
    replay = run_budget_retention_batch(original, participant, reopened)
    if replay != result:
        pytest.fail("coordinator_original_request_not_idempotent", pytrace=False)
    assert tuple(path.name for path in (tmp_path / "checkpoints").glob("*.zip")) == (
        identity.value + ".zip",
    )


def test_checkpoint_directory_scan_is_bounded(tmp_path: Path) -> None:
    from agentmonitor.adapters.operations.budget_retention_checkpoint import (  # noqa: E501
        MAX_DIRECTORY_ENTRIES,
    )

    root = tmp_path / "checkpoints"
    checkpoints = _store(root)
    # Real empty filesystem entries, never telemetry or provider responses.
    for number in range(MAX_DIRECTORY_ENTRIES):
        path = root / ("budget-checkpoint-" + format(number, "064x") + ".zip")
        path.touch(mode=0o600)
    with pytest.raises(ValueError, match="^budget_checkpoint_directory_limit$"):
        checkpoints.cleanup_expired(as_of=datetime.now(UTC))
    assert len(tuple(root.glob("*.zip"))) == MAX_DIRECTORY_ENTRIES


def test_coordinator_empty_batch_is_audited_without_export(tmp_path: Path) -> None:
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
        open_sqlite_database,
    )
    from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
        migrate_to_head,
    )
    from agentmonitor.modules.operations.application.budget_retention import (
        run_budget_retention_batch,
    )

    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    checkpoints = _store(tmp_path / "checkpoints")
    participant = build_budget_retention(reference, tmp_path / "checkpoints")
    now = datetime.now(UTC)
    request = OperationsParticipantRequestV1(
        OpaqueIdV1("empty-coordinator"),
        OpaqueIdV1("empty-coordinator"),
        now + timedelta(minutes=1),
        1,
        now - timedelta(days=365),
        1,
        None,
        None,
        None,
        None,
    )
    result = run_budget_retention_batch(request, participant, checkpoints)
    assert result.count == 0 and result.outcome == "complete"
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            audit = connection.exec_driver_sql(
                "SELECT batch_count,export_checkpoint_ref,state "
                "FROM capacity_retention_run"
            ).all()
    assert [tuple(row) for row in audit] == [(0, None, "completed")]
    assert not tuple((tmp_path / "checkpoints").glob("*.zip"))
