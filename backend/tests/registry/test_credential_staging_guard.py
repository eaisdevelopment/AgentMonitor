"""Real local filesystem guard; no accounts or credentials are constructed."""

import os
from pathlib import Path

import pytest

from agentmonitor.adapters.persistence._shared.sqlite.core.credential_guard import (
    acquire_credential_staging_guard,
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
