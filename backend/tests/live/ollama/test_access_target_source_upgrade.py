"""Exercise source-fingerprint reconciliation on a private real DB copy."""

from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.probe_descriptor import (
    ollama_cloud_probe_fingerprint,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1

_LIVE_DATABASE = Path("/home/dev/.local/share/agentmonitor/agentmonitor.db")
_OLLAMA_CLOUD_TARGET = OpaqueIdV1(
    "amat_" + hashlib.sha256(b"ollama\x00ollama.com").hexdigest()[:32]
)


def _private_real_copy(tmp_path: Path) -> DatabaseRefV1:
    os.chmod(tmp_path, 0o700)
    copied = tmp_path / "agentmonitor.db"
    source = sqlite3.connect(f"file:{_LIVE_DATABASE}?mode=ro", uri=True)
    target = sqlite3.connect(copied)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    os.chmod(copied, 0o600)
    return DatabaseRefV1(copied, tmp_path)


def test_real_access_target_accepts_reviewed_source_fingerprint_upgrade(
    tmp_path: Path,
) -> None:
    """M6-A03/A04/A07/A09: preserve identity while fencing old proof."""
    assert _LIVE_DATABASE.is_file()
    repository = SqliteCloudCredentialRegistryV1(_private_real_copy(tmp_path))
    before = repository.read_active_access_target(_OLLAMA_CLOUD_TARGET)
    assert before is not None
    expected_fingerprint = ollama_cloud_probe_fingerprint()

    updated = repository.reconcile_access_target(
        provider_key="ollama",
        authority_id="ollama.com",
        manifest_fingerprint=expected_fingerprint,
        as_of=datetime.now(UTC),
    )

    assert updated.access_target_id == before.access_target_id
    assert updated.provider_key == before.provider_key
    assert updated.target_kind == before.target_kind
    assert updated.authority_id == before.authority_id
    assert updated.lifecycle == before.lifecycle
    assert updated.manifest_fingerprint == expected_fingerprint
    expected_version = before.record_version + (
        1 if before.manifest_fingerprint != expected_fingerprint else 0
    )
    assert updated.record_version == expected_version
    assert repository.read_active_access_target(_OLLAMA_CLOUD_TARGET) == updated

    replay = repository.reconcile_access_target(
        provider_key="ollama",
        authority_id="ollama.com",
        manifest_fingerprint=expected_fingerprint,
        as_of=datetime.now(UTC),
    )
    assert replay == updated
