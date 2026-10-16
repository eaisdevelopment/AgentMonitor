"""Real-filesystem policy for preserving stale M5 prerequisite evidence."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tools.automation._m5_test_git import (
    attached_real_checkout_v1,
    git_status_v1,
)
from tools.automation.implementations.auto_m5_current_exit import (
    ALERT_WITNESS_BASENAME,
    CODEX_ADAPTER_VERSION,
    CODEX_MAPPING_DIGEST,
    CODEX_MAPPING_ID,
    CODEX_PARSER_VERSION,
    CODEX_PROVIDER_VERSION,
    CODEX_SCHEMA_BUNDLE_DIGEST,
    M5CurrentExitErrorV1,
    _acquire_m5_current_completion_lock_v1,
)
from tools.automation.implementations.m5_codex_quota_witness import (
    CODEX_RATE_LIMITS_SOURCE_ID,
    QUOTA_WITNESS_BASENAME,
)
from tools.automation.implementations.m5_completion_lock import (
    M5CompletionLockErrorV1,
    acquire_m5_completion_lock_v1,
    release_m5_completion_lock_v1,
    validate_m5_completion_lock_v1,
)
from tools.automation.implementations.m5_owner_outcomes import (
    OWNER_OUTCOMES_BASENAME,
    OwnerOutcomeV1,
    build_owner_outcomes_document_v2,
    write_owner_outcomes_v2,
)
from tools.automation.implementations.m5_prerequisite_archive import (
    ARCHIVE_MANIFEST_BASENAME,
    ARCHIVE_ROOT_BASENAME,
    M5PrerequisiteArchiveErrorV1,
    M5PrerequisiteArchiveResultV1,
    _open_artifact,
    _rename_noreplace_v1,
    _revalidate_runtime_binding_v1,
    _rollback,
    _select_runtime_binding_v1,
    archive_m5_prerequisites_v1,
)
from tools.automation.implementations.m5_service_activation import (
    candidate_for_checkout_v1,
)

OLD_REVISION = "a" * 40
CURRENT_REVISION = "b" * 40
OLD_PID = 321
OLD_START_TICKS = 654
CURRENT_PID = 987
CURRENT_START_TICKS = 765
NOW = datetime(2026, 10, 8, 10, 10, tzinfo=UTC)
DIGESTS = tuple(character * 64 for character in "cdef0123456789")


def test_archive_selection_rejects_a_real_attached_checkout_before_runtime_io() -> None:
    with attached_real_checkout_v1() as checkout:
        before = git_status_v1(checkout)
        with pytest.raises(
            M5PrerequisiteArchiveErrorV1,
            match="m5_prerequisite_archive_checkout_invalid",
        ):
            _select_runtime_binding_v1({}, checkout_root=checkout)
        assert before == git_status_v1(checkout) == ""


def test_archive_prewrite_recheck_rejects_an_attached_checkout_before_io() -> None:
    with attached_real_checkout_v1() as checkout:
        candidate = candidate_for_checkout_v1(
            source_revision=CURRENT_REVISION,
            checkout_root=checkout,
        )
        with pytest.raises(
            M5PrerequisiteArchiveErrorV1,
            match="m5_prerequisite_archive_context_changed",
        ):
            _revalidate_runtime_binding_v1(
                candidate,
                expected_revision=CURRENT_REVISION,
                selected_pid=CURRENT_PID,
                selected_start_time_ticks=CURRENT_START_TICKS,
                dashboard_origin="http://127.0.0.1:43110",
                dashboard_cdp_endpoint="http://127.0.0.1:9222",
                checkout_root=checkout,
            )
        assert git_status_v1(checkout) == ""


def _owner_document(
    *,
    revision: str = OLD_REVISION,
    service_pid: int = OLD_PID,
    service_start_time_ticks: int = OLD_START_TICKS,
    confirmed_at: datetime = NOW - timedelta(minutes=10),
) -> dict[str, object]:
    return build_owner_outcomes_document_v2(
        implementation_revision=revision,
        service_pid=service_pid,
        service_start_time_ticks=service_start_time_ticks,
        owner_confirmed_at=confirmed_at,
        outcomes=(
            OwnerOutcomeV1("account-one", "Private owner one", "verified"),
            OwnerOutcomeV1("account-two", "Private owner two", "verified"),
            OwnerOutcomeV1(
                "account-three",
                "Private owner three",
                "owner_unavailable",
                "subscription_unavailable",
            ),
            OwnerOutcomeV1(
                "account-four",
                "Private owner four",
                "owner_unavailable",
                "subscription_unavailable",
            ),
        ),
    )


def _write_owner(root: Path, **overrides: object) -> str:
    return write_owner_outcomes_v2(
        root / OWNER_OUTCOMES_BASENAME,
        _owner_document(**overrides),  # type: ignore[arg-type]
    )


def _write_private_json(path: Path, document: object) -> bytes:
    payload = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(payload)
    path.chmod(0o600)
    return payload


def _quota_document(owner_digest: str) -> dict[str, object]:
    return {
        "schema": "agentmonitor.m5-quota-witness.v1",
        "implementation_revision": OLD_REVISION,
        "service_source_revision": OLD_REVISION,
        "service_pid": OLD_PID,
        "service_start_time_ticks": OLD_START_TICKS,
        "recorded_at": "2026-10-08T10:04:00Z",
        "owner_confirmation": "interactive_terminal",
        "provider_key": "codex",
        "provider_version": CODEX_PROVIDER_VERSION,
        "source_id": CODEX_RATE_LIMITS_SOURCE_ID,
        "account_count": 2,
        "window_count": 4,
        "owner_outcomes_digest": owner_digest,
        "identity_set_digest": DIGESTS[0],
        "collection_run_set_digest": DIGESTS[1],
        "quota_value_set_digest": DIGESTS[2],
        "owner_observation_digest": DIGESTS[3],
        "rendered_value_set_digest": DIGESTS[2],
        "history_value_set_digest": DIGESTS[4],
        "browser_proof_digest": DIGESTS[5],
        "registry_graph_digest_before": DIGESTS[6],
        "registry_graph_digest_after": DIGESTS[6],
        "browser_registry_digest_before": DIGESTS[7],
        "browser_registry_digest_after": DIGESTS[7],
    }


def _alert_document() -> dict[str, object]:
    return {
        "schema": "agentmonitor.m5-alert-witness.v2",
        "implementation_revision": OLD_REVISION,
        "service_source_revision": OLD_REVISION,
        "service_pid": OLD_PID,
        "service_start_time_ticks": OLD_START_TICKS,
        "service_started_at": "2026-10-08T09:50:00Z",
        "service_checked_at": "2026-10-08T10:03:30Z",
        "service_versions_digest": DIGESTS[0],
        "provider_key": "codex",
        "account_id": "account-one",
        "source_id": CODEX_RATE_LIMITS_SOURCE_ID,
        "provider_version": CODEX_PROVIDER_VERSION,
        "adapter_id": "agentmonitor.codex",
        "adapter_version": CODEX_ADAPTER_VERSION,
        "parser_version": CODEX_PARSER_VERSION,
        "mapping_id": CODEX_MAPPING_ID,
        "mapping_digest": CODEX_MAPPING_DIGEST,
        "schema_bundle_digest": CODEX_SCHEMA_BUNDLE_DIGEST,
        "alert_record_version": 4,
        "alert_aggregate_sequence": 4,
        "opened_at": "2026-10-08T10:00:00Z",
        "deduplicated_at": "2026-10-08T10:01:00Z",
        "owner_action_at": "2026-10-08T10:02:00Z",
        "recovered_at": "2026-10-08T10:03:00Z",
        "recorded_at": "2026-10-08T10:04:00Z",
        "owner_action": "acknowledged",
        "opened": True,
        "deduplicated": True,
        "browser_presented": True,
        "recovered": True,
        "source_proven_opening": True,
        "source_proven_deduplication": True,
        "source_proven_recovery": True,
        "source_event_digest": DIGESTS[1],
        "source_observation_digest": DIGESTS[2],
        "opening_observation_digest": DIGESTS[3],
        "deduplication_observation_digest": DIGESTS[4],
        "recovery_observation_digest": DIGESTS[5],
        "source_delivery_receipt_digest": DIGESTS[6],
        "alert_history_digest": DIGESTS[7],
        "owner_action_receipt_digest": DIGESTS[8],
        "registry_digest_scope": "all-public-registry-fields-v1",
        "registry_digest_before": DIGESTS[9],
        "registry_digest_after": DIGESTS[9],
    }


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "owner"
    root.mkdir(mode=0o700)
    return root


def _archive(
    root: Path,
    *,
    receipt_path: Path,
    current_revision: str = CURRENT_REVISION,
    service_pid: int = CURRENT_PID,
    service_start_time_ticks: int = CURRENT_START_TICKS,
) -> M5PrerequisiteArchiveResultV1:
    return archive_m5_prerequisites_v1(
        root,
        current_revision=current_revision,
        current_service_pid=service_pid,
        current_service_start_time_ticks=service_start_time_ticks,
        now=NOW,
        final_receipt_path=receipt_path,
    )


def _start_lock_holder(receipt_path: Path) -> tuple[int, int]:
    ready_read, ready_write = os.pipe()
    release_read, release_write = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(ready_read)
        os.close(release_write)
        completion_lock = None
        try:
            completion_lock = acquire_m5_completion_lock_v1(receipt_path)
            os.write(ready_write, b"1")
            if os.read(release_read, 1) != b"1":
                os._exit(31)
            release_m5_completion_lock_v1(completion_lock)
            completion_lock = None
            os._exit(0)
        except (M5CompletionLockErrorV1, OSError):
            os._exit(32)
        finally:
            if completion_lock is not None:
                release_m5_completion_lock_v1(completion_lock)
    os.close(ready_write)
    os.close(release_read)
    assert os.read(ready_read, 1) == b"1"
    os.close(ready_read)
    return pid, release_write


def _stop_lock_holder(pid: int, release_write: int) -> None:
    os.write(release_write, b"1")
    os.close(release_write)
    waited, status = os.waitpid(pid, 0)
    assert waited == pid
    assert os.waitstatus_to_exitcode(status) == 0


def _completion_lock_attempt_exit_code(receipt_path: Path) -> int:
    pid = os.fork()
    if pid == 0:
        try:
            completion_lock = acquire_m5_completion_lock_v1(receipt_path)
            release_m5_completion_lock_v1(completion_lock)
            os._exit(0)
        except M5CompletionLockErrorV1 as error:
            os._exit(17 if str(error) == "m5_completion_lock_busy" else 18)
        except OSError:
            os._exit(19)
    waited, status = os.waitpid(pid, 0)
    assert waited == pid
    return os.waitstatus_to_exitcode(status)


def test_stale_complete_set_is_renamed_with_inode_mode_link_and_hash_preserved(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    owner_digest = _write_owner(root)
    payloads = {
        OWNER_OUTCOMES_BASENAME: (root / OWNER_OUTCOMES_BASENAME).read_bytes(),
        QUOTA_WITNESS_BASENAME: _write_private_json(
            root / QUOTA_WITNESS_BASENAME, _quota_document(owner_digest)
        ),
        ALERT_WITNESS_BASENAME: _write_private_json(
            root / ALERT_WITNESS_BASENAME, _alert_document()
        ),
    }
    before = {name: (root / name).stat() for name in payloads}

    result = _archive(root, receipt_path=tmp_path / "receipt.json")

    archive = root / ARCHIVE_ROOT_BASENAME / result.archive_id
    assert result.implementation_revision == OLD_REVISION
    assert result.artifact_count == 3
    assert stat.S_IMODE(archive.stat().st_mode) == 0o700
    for name, payload in payloads.items():
        assert not (root / name).exists()
        archived = archive / name
        metadata = archived.stat()
        assert (metadata.st_dev, metadata.st_ino) == (
            before[name].st_dev,
            before[name].st_ino,
        )
        assert stat.S_IMODE(metadata.st_mode) == 0o600
        assert metadata.st_nlink == 1
        assert archived.read_bytes() == payload
        assert (
            dict(result.artifact_digests)[name] == hashlib.sha256(payload).hexdigest()
        )
    manifest_path = archive / ARCHIVE_MANIFEST_BASENAME
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    assert stat.S_IMODE(manifest_path.stat().st_mode) == 0o600
    assert manifest["bundle_digest"] == result.bundle_digest
    serialized = json.dumps(manifest)
    assert "Private owner" not in serialized
    assert "account-one" not in serialized


def test_current_valid_partial_set_is_refused_without_moving_it(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _write_owner(
        root,
        revision=CURRENT_REVISION,
        service_pid=CURRENT_PID,
        service_start_time_ticks=CURRENT_START_TICKS,
        confirmed_at=NOW - timedelta(minutes=1),
    )
    path = root / OWNER_OUTCOMES_BASENAME
    before = path.stat()

    with pytest.raises(
        M5PrerequisiteArchiveErrorV1,
        match="m5_prerequisite_archive_current_valid",
    ):
        _archive(root, receipt_path=tmp_path / "receipt.json")

    after = path.stat()
    assert (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino)
    assert not (root / ARCHIVE_ROOT_BASENAME).exists()


def test_expired_current_revision_set_can_be_archived(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _write_private_json(
        root / OWNER_OUTCOMES_BASENAME,
        _owner_document(
            revision=CURRENT_REVISION,
            service_pid=CURRENT_PID,
            service_start_time_ticks=CURRENT_START_TICKS,
            confirmed_at=NOW - timedelta(days=9),
        ),
    )

    result = _archive(root, receipt_path=tmp_path / "receipt.json")

    assert result.artifact_count == 1
    assert (root / ARCHIVE_ROOT_BASENAME / result.archive_id).is_dir()


def test_final_receipt_refuses_archive_before_artifact_mutation(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _write_owner(root)
    receipt = tmp_path / "m5-current-gate-receipt.json"
    receipt.write_text("{}", encoding="ascii")
    receipt.chmod(0o600)

    with pytest.raises(
        M5PrerequisiteArchiveErrorV1,
        match="m5_prerequisite_archive_final_receipt_exists",
    ):
        _archive(root, receipt_path=receipt)

    assert (root / OWNER_OUTCOMES_BASENAME).is_file()
    assert not (root / ARCHIVE_ROOT_BASENAME).exists()


@pytest.mark.parametrize("invalid", ("root_mode", "symlink", "hardlink"))
def test_invalid_private_boundaries_are_refused_without_archive(
    tmp_path: Path, invalid: str
) -> None:
    root = _root(tmp_path)
    _write_owner(root)
    owner = root / OWNER_OUTCOMES_BASENAME
    if invalid == "root_mode":
        root.chmod(0o755)
    elif invalid == "symlink":
        target = root / "owner-target.json"
        owner.rename(target)
        owner.symlink_to(target)
    else:
        os.link(owner, root / "owner-second-link.json")

    with pytest.raises(M5PrerequisiteArchiveErrorV1):
        _archive(root, receipt_path=tmp_path / "receipt.json")

    assert not (root / ARCHIVE_ROOT_BASENAME).exists()


def test_inconsistent_dependent_witness_is_refused_without_archive(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    owner_digest = _write_owner(root)
    quota = _quota_document(owner_digest)
    quota["implementation_revision"] = CURRENT_REVISION
    _write_private_json(root / QUOTA_WITNESS_BASENAME, quota)

    with pytest.raises(
        M5PrerequisiteArchiveErrorV1,
        match="m5_prerequisite_archive_artifact_invalid",
    ):
        _archive(root, receipt_path=tmp_path / "receipt.json")

    assert (root / OWNER_OUTCOMES_BASENAME).is_file()
    assert (root / QUOTA_WITNESS_BASENAME).is_file()
    assert not (root / ARCHIVE_ROOT_BASENAME).exists()


def test_linux_noreplace_rename_preserves_an_existing_target(tmp_path: Path) -> None:
    source_directory = tmp_path / "source"
    target_directory = tmp_path / "target"
    source_directory.mkdir()
    target_directory.mkdir()
    source = source_directory / "evidence.json"
    target = target_directory / "evidence.json"
    source.write_bytes(b"source evidence\n")
    target.write_bytes(b"existing target\n")
    source_descriptor = os.open(source_directory, os.O_RDONLY | os.O_DIRECTORY)
    target_descriptor = os.open(target_directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(FileExistsError):
            _rename_noreplace_v1(
                "evidence.json",
                "evidence.json",
                source_directory_descriptor=source_descriptor,
                target_directory_descriptor=target_descriptor,
            )
    finally:
        os.close(source_descriptor)
        os.close(target_descriptor)

    assert source.read_bytes() == b"source evidence\n"
    assert target.read_bytes() == b"existing target\n"


def test_linux_noreplace_rename_allows_only_one_real_process_to_win(
    tmp_path: Path,
) -> None:
    source_directory = tmp_path / "source"
    target_directory = tmp_path / "target"
    source_directory.mkdir()
    target_directory.mkdir()
    for name in ("first.json", "second.json"):
        (source_directory / name).write_text(name, encoding="ascii")
    start_read, start_write = os.pipe()
    children: list[int] = []
    for source_name in ("first.json", "second.json"):
        pid = os.fork()
        if pid == 0:
            os.close(start_write)
            try:
                if os.read(start_read, 1) != b"1":
                    os._exit(41)
                source_descriptor = os.open(
                    source_directory, os.O_RDONLY | os.O_DIRECTORY
                )
                target_descriptor = os.open(
                    target_directory, os.O_RDONLY | os.O_DIRECTORY
                )
                try:
                    _rename_noreplace_v1(
                        source_name,
                        "winner.json",
                        source_directory_descriptor=source_descriptor,
                        target_directory_descriptor=target_descriptor,
                    )
                finally:
                    os.close(source_descriptor)
                    os.close(target_descriptor)
                os._exit(0)
            except FileExistsError:
                os._exit(17)
            except (M5PrerequisiteArchiveErrorV1, OSError):
                os._exit(42)
        children.append(pid)
    os.close(start_read)
    os.write(start_write, b"11")
    os.close(start_write)
    statuses = {os.waitstatus_to_exitcode(os.waitpid(pid, 0)[1]) for pid in children}

    assert statuses == {0, 17}
    winner = (target_directory / "winner.json").read_text(encoding="ascii")
    loser = "second.json" if winner == "first.json" else "first.json"
    assert (source_directory / loser).read_text(encoding="ascii") == loser


def test_rollback_never_replaces_a_fixed_name_created_after_the_move(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    archive = root / "archive"
    archive.mkdir(mode=0o700)
    basename = OWNER_OUTCOMES_BASENAME
    _write_private_json(root / basename, {"old": "evidence"})
    root_descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    archive_descriptor = os.open(archive, os.O_RDONLY | os.O_DIRECTORY)
    artifact = _open_artifact(root_descriptor, basename, root_device=root.stat().st_dev)
    assert artifact is not None
    try:
        _rename_noreplace_v1(
            basename,
            basename,
            source_directory_descriptor=root_descriptor,
            target_directory_descriptor=archive_descriptor,
        )
        replacement = _write_private_json(root / basename, {"new": "replacement"})

        restored = _rollback(
            root_descriptor=root_descriptor,
            archive_descriptor=archive_descriptor,
            artifacts=(artifact,),
            moved=[artifact],
            manifest_identity=None,
        )

        assert not restored
        assert (root / basename).read_bytes() == replacement
        assert (archive / basename).is_file()
        assert (archive / basename).stat().st_ino == artifact.inode
    finally:
        os.close(artifact.descriptor)
        os.close(archive_descriptor)
        os.close(root_descriptor)


@pytest.mark.parametrize("invalid", ("mode", "symlink"))
def test_completion_lock_rejects_nonprivate_or_aliased_receipt_scope(
    tmp_path: Path, invalid: str
) -> None:
    scope = tmp_path / "receipt-scope"
    scope.mkdir(mode=0o700)
    if invalid == "mode":
        scope.chmod(0o755)
    else:
        target = tmp_path / "receipt-target"
        scope.rename(target)
        scope.symlink_to(target, target_is_directory=True)

    with pytest.raises(M5CompletionLockErrorV1, match="m5_completion_lock_invalid"):
        acquire_m5_completion_lock_v1(scope / "receipt.json")


def test_archive_and_exit_fail_closed_while_another_process_holds_shared_lock(
    tmp_path: Path,
) -> None:
    first_root = _root(tmp_path)
    second_root = tmp_path / "second-owner"
    second_root.mkdir(mode=0o700)
    _write_owner(first_root)
    _write_owner(second_root)
    receipt_directory = tmp_path / "receipt-scope"
    receipt_directory.mkdir(mode=0o700)
    receipt = receipt_directory / "receipt.json"
    holder, release_write = _start_lock_holder(receipt)
    try:
        for root in (first_root, second_root):
            with pytest.raises(
                M5PrerequisiteArchiveErrorV1,
                match="m5_prerequisite_archive_lock_unavailable",
            ):
                _archive(root, receipt_path=receipt)
        with pytest.raises(
            M5CurrentExitErrorV1,
            match="m5_current_completion_lock_unavailable",
        ):
            _acquire_m5_current_completion_lock_v1(receipt)
    finally:
        _stop_lock_holder(holder, release_write)
    descriptor = _acquire_m5_current_completion_lock_v1(receipt)
    release_m5_completion_lock_v1(descriptor)


def test_receipt_scope_lock_survives_same_uid_directory_replacement(
    tmp_path: Path,
) -> None:
    scope = tmp_path / "receipt-scope"
    scope.mkdir(mode=0o700)
    receipt = scope / "receipt.json"
    first = acquire_m5_completion_lock_v1(receipt)
    displaced = tmp_path / "displaced-receipt-scope"
    scope.rename(displaced)
    scope.mkdir(mode=0o700)
    try:
        assert _completion_lock_attempt_exit_code(receipt) == 17
        with pytest.raises(M5CompletionLockErrorV1, match="m5_completion_lock_changed"):
            validate_m5_completion_lock_v1(first)
    finally:
        release_m5_completion_lock_v1(first)

    second = acquire_m5_completion_lock_v1(receipt)
    release_m5_completion_lock_v1(second)
