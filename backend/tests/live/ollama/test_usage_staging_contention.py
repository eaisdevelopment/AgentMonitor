"""Real staging-guard contention over private metadata; no credential access."""

import os
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence.registry.sqlite.credential_guard import (
    acquire_credential_staging_guard,
)
from agentmonitor.composition.ollama_env_store import env_location_matches

from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


def test_real_staging_contention_is_distinct_from_missing_env_location(
    tmp_path: Path,
) -> None:
    _private_real_copy(tmp_path)
    env = tmp_path / ".env"
    env.touch(mode=0o600)
    root, lock = acquire_credential_staging_guard(tmp_path)
    try:
        with pytest.raises(BlockingIOError) as caught:
            env_location_matches(tmp_path, env)
        trace = caught.value.__traceback__
        failure = None
        while trace is not None:
            failure = (Path(trace.tb_frame.f_code.co_filename).name, trace.tb_lineno)
            trace = trace.tb_next
        assert failure == ("credential_guard.py", 28)
    finally:
        os.close(lock)
        os.close(root)
    # Releasing the actual OS lock changes this to ordinary absent-location
    # metadata, rather than an exception; no key is present or read in either case.
    assert env_location_matches(tmp_path, env) is False


def test_short_real_staging_lock_release_does_not_abort_usage(tmp_path: Path) -> None:
    import threading
    import time

    from agentmonitor.composition.ollama_usage_collection import (
        _bounded_env_location_matches,
    )

    _private_real_copy(tmp_path)
    env = tmp_path / ".env"
    env.touch(mode=0o600)
    ready = threading.Event()

    def hold_briefly() -> None:
        root, lock = acquire_credential_staging_guard(tmp_path)
        try:
            ready.set()
            time.sleep(0.15)
        finally:
            os.close(lock)
            os.close(root)

    holder = threading.Thread(target=hold_briefly)
    holder.start()
    try:
        assert ready.wait(5)
        start = time.monotonic()
        assert _bounded_env_location_matches(tmp_path, env, start + 5) is False
        assert time.monotonic() - start >= 0.10
    finally:
        holder.join(timeout=5)
    assert not holder.is_alive()


@pytest.mark.parametrize("remaining", [0.15, 60.0])
def test_contended_guard_respects_original_deadline_and_local_cap(
    tmp_path: Path,
    remaining: float,
) -> None:
    import time

    from agentmonitor.composition.ollama_usage_collection import (
        _bounded_env_location_matches,
    )

    _private_real_copy(tmp_path)
    env = tmp_path / ".env"
    env.touch(mode=0o600)
    root, lock = acquire_credential_staging_guard(tmp_path)
    try:
        start = time.monotonic()
        with pytest.raises(BlockingIOError):
            _bounded_env_location_matches(tmp_path, env, start + remaining)
        elapsed = time.monotonic() - start
        assert min(remaining, 2) <= elapsed < min(remaining, 2) + 0.5
    finally:
        os.close(lock)
        os.close(root)


def test_expired_local_guard_deadline_never_checks_location(tmp_path: Path) -> None:
    import time

    from agentmonitor.composition.ollama_usage_collection import (
        _bounded_env_location_matches,
    )

    tmp_path.chmod(0o700)
    with pytest.raises(TimeoutError):
        _bounded_env_location_matches(tmp_path, tmp_path / ".env", time.monotonic() - 1)
    assert not (tmp_path / ".ollama-env-staging.lock").exists()
