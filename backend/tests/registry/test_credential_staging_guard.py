"""Real local filesystem guard; no accounts or credentials are constructed."""

import os
from pathlib import Path

import pytest

from agentmonitor.adapters.persistence._shared.sqlite.core.credential_guard import (
    acquire_credential_staging_guard,
    validate_credential_staging_guard,
)


def test_same_data_root_excludes_another_writer(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    root, lock = acquire_credential_staging_guard(tmp_path)
    try:
        with pytest.raises(BlockingIOError):
            acquire_credential_staging_guard(tmp_path)
    finally:
        os.close(lock)
        os.close(root)


def test_replaced_data_root_is_rejected(tmp_path: Path) -> None:
    selected = tmp_path / "data"
    selected.mkdir(mode=0o700)
    root, lock = acquire_credential_staging_guard(selected)
    try:
        selected.rename(tmp_path / "previous")
        selected.mkdir(mode=0o700)
        replacement_root, replacement_lock = acquire_credential_staging_guard(selected)
        try:
            with pytest.raises(ValueError):
                validate_credential_staging_guard(selected, root, lock)
        finally:
            os.close(replacement_lock)
            os.close(replacement_root)
    finally:
        os.close(lock)
        os.close(root)
