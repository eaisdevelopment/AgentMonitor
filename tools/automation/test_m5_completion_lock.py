"""Real-filesystem coverage for the M5 completion lock boundary."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from tools.automation.implementations.m5_completion_lock import (
    M5CompletionLockErrorV1,
    acquire_m5_completion_lock_v1,
    release_m5_completion_lock_v1,
    validate_m5_completion_lock_v1,
)


def test_completion_lock_creates_exact_absent_private_receipt_scope(
    tmp_path: Path,
) -> None:
    scope = tmp_path / ".agentmonitor-local"
    receipt = scope / "m5-current-gate-receipt.json"

    lock = acquire_m5_completion_lock_v1(receipt)
    try:
        scope_metadata = scope.lstat()
        descriptor_metadata = os.fstat(lock.directory_descriptor)
        assert stat.S_ISDIR(scope_metadata.st_mode)
        assert scope_metadata.st_uid == os.getuid()
        assert stat.S_IMODE(scope_metadata.st_mode) == 0o700
        assert (scope_metadata.st_dev, scope_metadata.st_ino) == (
            descriptor_metadata.st_dev,
            descriptor_metadata.st_ino,
        )
        assert not receipt.exists()
        validate_m5_completion_lock_v1(lock)
    finally:
        release_m5_completion_lock_v1(lock)


def test_completion_lock_accepts_an_existing_exact_private_receipt_scope(
    tmp_path: Path,
) -> None:
    scope = tmp_path / ".agentmonitor-local"
    scope.mkdir(mode=0o700)
    before = scope.stat()

    lock = acquire_m5_completion_lock_v1(scope / "m5-current-gate-receipt.json")
    try:
        after = scope.stat()
        assert (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino)
        assert stat.S_IMODE(after.st_mode) == 0o700
        validate_m5_completion_lock_v1(lock)
    finally:
        release_m5_completion_lock_v1(lock)


def test_completion_lock_does_not_create_an_unapproved_missing_scope(
    tmp_path: Path,
) -> None:
    scope = tmp_path / "unapproved-scope"

    with pytest.raises(M5CompletionLockErrorV1, match="m5_completion_lock_invalid"):
        acquire_m5_completion_lock_v1(scope / "arbitrary-receipt.json")

    assert not scope.exists()


@pytest.mark.parametrize("invalid", ("wrong_mode", "symlink", "file"))
def test_completion_lock_rejects_an_unsafe_existing_receipt_scope(
    tmp_path: Path,
    invalid: str,
) -> None:
    scope = tmp_path / ".agentmonitor-local"
    if invalid == "wrong_mode":
        scope.mkdir(mode=0o700)
        scope.chmod(0o755)
    elif invalid == "symlink":
        target = tmp_path / "receipt-target"
        target.mkdir(mode=0o700)
        scope.symlink_to(target, target_is_directory=True)
    else:
        scope.write_bytes(b"not a directory\n")
        scope.chmod(0o600)

    with pytest.raises(M5CompletionLockErrorV1, match="m5_completion_lock_invalid"):
        acquire_m5_completion_lock_v1(scope / "m5-current-gate-receipt.json")

    assert os.path.lexists(scope)


def _run_first_use_contender(
    receipt: Path,
    *,
    start_descriptor: int,
    result_descriptor: int,
    release_descriptor: int,
) -> None:
    lock = None
    try:
        if os.read(start_descriptor, 1) != b"1":
            os._exit(41)
        try:
            lock = acquire_m5_completion_lock_v1(receipt)
        except M5CompletionLockErrorV1 as error:
            outcome = b"B" if str(error) == "m5_completion_lock_busy" else b"I"
            os.write(result_descriptor, outcome)
            os._exit(0)
        except OSError:
            os.write(result_descriptor, b"E")
            os._exit(0)
        os.write(result_descriptor, b"A")
        if os.read(release_descriptor, 1) != b"1":
            os._exit(42)
        release_m5_completion_lock_v1(lock)
        lock = None
        os._exit(0)
    finally:
        if lock is not None:
            release_m5_completion_lock_v1(lock)


def test_completion_lock_serializes_real_processes_during_first_use(
    tmp_path: Path,
) -> None:
    scope = tmp_path / ".agentmonitor-local"
    receipt = scope / "m5-current-gate-receipt.json"
    start_read, start_write = os.pipe()
    result_read, result_write = os.pipe()
    release_read, release_write = os.pipe()
    children: list[int] = []
    for _ in range(2):
        pid = os.fork()
        if pid == 0:
            os.close(start_write)
            os.close(result_read)
            os.close(release_write)
            _run_first_use_contender(
                receipt,
                start_descriptor=start_read,
                result_descriptor=result_write,
                release_descriptor=release_read,
            )
        children.append(pid)

    os.close(start_read)
    os.close(result_write)
    os.close(release_read)
    outcomes = b""
    statuses: list[int] = []
    try:
        os.write(start_write, b"11")
        os.close(start_write)
        start_write = -1
        while len(outcomes) < 2:
            chunk = os.read(result_read, 2 - len(outcomes))
            if not chunk:
                break
            outcomes += chunk
        if b"A" in outcomes:
            os.write(release_write, b"1")
        os.close(release_write)
        release_write = -1
        for child in children:
            waited, status = os.waitpid(child, 0)
            assert waited == child
            statuses.append(os.waitstatus_to_exitcode(status))
    finally:
        os.close(result_read)
        if start_write >= 0:
            os.close(start_write)
        if release_write >= 0:
            os.close(release_write)
        for child in children[len(statuses) :]:
            os.waitpid(child, 0)

    assert sorted(outcomes) == sorted(b"AB")
    assert statuses == [0, 0]
    metadata = scope.stat()
    assert stat.S_IMODE(metadata.st_mode) == 0o700
    assert not receipt.exists()
