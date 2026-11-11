"""Real empty credential files only; no invented key or stored-access proof."""

import fcntl
import os
import secrets
import stat
from pathlib import Path

import pytest
from agentmonitor.adapters.credential_env.format import CredentialProviderKey
from agentmonitor.composition.ollama_env_store import (
    _managed_entries,
    import_managed_env_variable,
    update_managed_env,
    update_ollama_env,
)


def _empty_store(tmp_path: Path) -> tuple[Path, Path]:
    parent = tmp_path / "owner-private"
    parent.mkdir(mode=0o700)
    staging = tmp_path / "data"
    staging.mkdir(mode=0o700)
    selected = parent / ".env"
    descriptor = os.open(selected, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    return selected, staging


@pytest.mark.parametrize("provider", ["claude", "codex", "ollama"])
def test_remove_absent_entry_keeps_real_empty_file_unchanged(
    tmp_path: Path, provider: CredentialProviderKey
) -> None:
    """M7-ENV-FS-001: generic writer runs against an actual empty protected file."""
    selected, staging = _empty_store(tmp_path)
    before = selected.stat()
    binding = "amcb_" + secrets.token_hex(16)
    update_managed_env(
        selected, binding, None, provider_key=provider, staging_root=staging
    )
    after = selected.stat()
    assert after.st_size == 0
    assert stat.S_IMODE(after.st_mode) == 0o600
    assert (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)
    assert _managed_entries(selected) == ()
    lock = selected.parent / ".ollama-env.lock"
    held = lock.stat()
    assert stat.S_IMODE(held.st_mode) == 0o600 and held.st_nlink == 1
    # The compatibility writer uses the identical persistent inode.
    update_ollama_env(selected, binding, None, staging_root=staging)
    assert (lock.stat().st_dev, lock.stat().st_ino) == (held.st_dev, held.st_ino)
    assert {entry.name for entry in selected.parent.iterdir()} == {
        ".env",
        ".ollama-env.lock",
    }


@pytest.mark.parametrize("provider", ["claude", "codex", "ollama"])
def test_literal_import_from_empty_file_fails_without_writing(
    tmp_path: Path, provider: CredentialProviderKey
) -> None:
    """M7-ENV-FS-002: missing actual source entry never becomes a stored key."""
    selected, staging = _empty_store(tmp_path)
    before = selected.stat()
    with pytest.raises(ValueError, match="ollama_env_import_entry_missing"):
        import_managed_env_variable(
            selected,
            "amcb_" + secrets.token_hex(16),
            "OWNER_BILLING_KEY",
            provider_key=provider,
            staging_root=staging,
        )
    after = selected.stat()
    assert after.st_size == 0
    assert (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)
    assert _managed_entries(selected) == ()


def test_generic_and_ollama_writer_obey_same_real_file_lock(tmp_path: Path) -> None:
    """M7-ENV-FS-003: another descriptor excludes both writer entry points."""
    selected, staging = _empty_store(tmp_path)
    binding = "amcb_" + secrets.token_hex(16)
    update_managed_env(
        selected, binding, None, provider_key="claude", staging_root=staging
    )
    descriptor = os.open(selected.parent / ".ollama-env.lock", os.O_RDWR)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            update_managed_env(
                selected, binding, None, provider_key="codex", staging_root=staging
            )
        with pytest.raises(BlockingIOError):
            update_ollama_env(selected, binding, None, staging_root=staging)
    finally:
        os.close(descriptor)
    assert selected.stat().st_size == 0
    update_managed_env(
        selected, binding, None, provider_key="codex", staging_root=staging
    )
