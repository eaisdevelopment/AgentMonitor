"""Real owned namespaces and kernel cleanup; no account or provider access."""

import stat
import uuid
from pathlib import Path

import pytest

from tools.automation.implementations.m6_controlled_recovery_interval import (
    _namespace,
    _start_worker,
    _supervisor_lock,
)


def test_real_child_has_distinct_network_and_exits_without_go(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir(mode=0o700)
    env_file = tmp_path / ".env"
    env_file.touch(mode=0o600)
    (tmp_path / ".ollama-env.lock").touch(mode=0o600)
    worker = _start_worker(data_root, env_file, uuid.uuid4().hex)
    try:
        assert worker.namespace_inode != _namespace("self")
        assert worker.pid > 1 and worker.start_ticks > 0
        assert worker.process.stdin is not None
        worker.process.stdin.close()
        assert worker.process.wait(timeout=5) == 3
    finally:
        worker.close()
    assert not Path(f"/proc/{worker.pid}").exists()
    assert list(data_root.iterdir()) == []
    assert env_file.stat().st_size == 0


def test_real_worker_rejects_foreign_go_before_collection(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir(mode=0o700)
    env_file = tmp_path / ".env"
    env_file.touch(mode=0o600)
    (tmp_path / ".ollama-env.lock").touch(mode=0o600)
    worker = _start_worker(data_root, env_file, uuid.uuid4().hex)
    try:
        assert worker.process.stdin is not None
        worker.process.stdin.write(("GO " + uuid.uuid4().hex + "\n").encode())
        worker.process.stdin.flush()
        assert worker.process.wait(timeout=5) == 3
    finally:
        worker.close()
    assert list(data_root.iterdir()) == []
    assert env_file.stat().st_size == 0


def test_real_waiting_child_is_reaped_on_cleanup(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir(mode=0o700)
    env_file = tmp_path / ".env"
    env_file.touch(mode=0o600)
    (tmp_path / ".ollama-env.lock").touch(mode=0o600)
    worker = _start_worker(data_root, env_file, uuid.uuid4().hex)
    assert worker.process.poll() is None
    worker.close()
    assert not Path(f"/proc/{worker.pid}").exists()
    assert list(data_root.iterdir()) == []


def test_real_namespace_retains_supervisor_lock_until_cleanup(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir(mode=0o700)
    env_file = tmp_path / ".env"
    env_file.touch(mode=0o600)
    (tmp_path / ".ollama-env.lock").touch(mode=0o600)
    worker = None
    try:
        with _supervisor_lock(data_root) as descriptor:
            worker = _start_worker(data_root, env_file, uuid.uuid4().hex, descriptor)
        # Closing the parent descriptor cannot release a still-running child.
        with pytest.raises(BlockingIOError), _supervisor_lock(data_root):
            pass
    finally:
        if worker is not None:
            worker.close()
    with _supervisor_lock(data_root):
        assert not (data_root / "agentmonitor.db").exists()


def test_real_unsafe_credential_lock_refused_without_changes(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir(mode=0o700)
    env_file = tmp_path / ".env"
    env_file.touch(mode=0o600)
    lock = tmp_path / ".ollama-env.lock"
    lock.touch(mode=0o600)
    lock.chmod(0o644)
    with pytest.raises(ValueError, match="m6_controlled_file_unsafe"):
        _start_worker(data_root, env_file, uuid.uuid4().hex)
    assert list(data_root.iterdir()) == []
    assert env_file.stat().st_size == 0
    assert stat.S_IMODE(lock.stat().st_mode) == 0o644
