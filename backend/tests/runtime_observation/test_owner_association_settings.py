"""Real filesystem safety checks; no provider records or owner claims created."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence.runtime_observation.settings.repository import (
    MAX_BYTES,
    SETTINGS_NAME,
    OwnerAssociationSettingsRepositoryV1,
)
from agentmonitor.modules.runtime_observation.application.ports import (
    OwnerAssociationErrorV1,
)


def test_missing_settings_remain_absent(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    repository = OwnerAssociationSettingsRepositoryV1(tmp_path)
    assert repository.records() == {}
    assert not (tmp_path / SETTINGS_NAME).exists()


@pytest.mark.parametrize("mode", (0o755, 0o770))
def test_shared_directory_rejected(tmp_path: Path, mode: int) -> None:
    tmp_path.chmod(mode)
    with pytest.raises(OwnerAssociationErrorV1):
        OwnerAssociationSettingsRepositoryV1(tmp_path).records()


@pytest.mark.parametrize("unsafe", ("symlink", "hardlink", "shared", "oversize"))
def test_unsafe_settings_rejected(tmp_path: Path, unsafe: str) -> None:
    tmp_path.chmod(0o700)
    target = tmp_path / SETTINGS_NAME
    source = tmp_path / "private-settings"
    source.write_bytes(b"{}")
    source.chmod(0o600)
    if unsafe == "symlink":
        target.symlink_to(source)
    elif unsafe == "hardlink":
        os.link(source, target)
    else:
        target.write_bytes(b" " * (MAX_BYTES + 1) if unsafe == "oversize" else b"{}")
        target.chmod(0o644 if unsafe == "shared" else 0o600)
    before = source.read_bytes()
    with pytest.raises(OwnerAssociationErrorV1):
        OwnerAssociationSettingsRepositoryV1(tmp_path).records()
    assert source.read_bytes() == before


@pytest.mark.parametrize(
    "document",
    (
        b"{",
        b'{"format":"future.v9","records":{}}',
        b'{"format":"owner-process-account-associations.v1","records":{},"extra":1}',
        b'{"format":"owner-process-account-associations.v1","records":{},"records":{}}',
    ),
)
def test_invalid_configuration_is_not_reset(tmp_path: Path, document: bytes) -> None:
    tmp_path.chmod(0o700)
    target = tmp_path / SETTINGS_NAME
    target.write_bytes(document)
    target.chmod(0o600)
    with pytest.raises(OwnerAssociationErrorV1):
        OwnerAssociationSettingsRepositoryV1(tmp_path).records()
    assert target.read_bytes() == document


def test_special_file_rejected_without_blocking(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    os.mkfifo(tmp_path / SETTINGS_NAME, 0o600)
    command = [
        sys.executable,
        "-c",
        "from pathlib import Path; import sys; "
        "from agentmonitor.adapters.persistence.runtime_observation.settings."
        "repository "
        "import OwnerAssociationSettingsRepositoryV1; "
        "OwnerAssociationSettingsRepositoryV1(Path(sys.argv[1])).records()",
        str(tmp_path),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=3,
            check=False,
            env={"PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")},
        )
    except subprocess.TimeoutExpired:
        pytest.fail("unsafe_settings_special_file_blocks_reader")
    assert result.returncode != 0
    assert b"observation_repository_unavailable" in result.stderr
