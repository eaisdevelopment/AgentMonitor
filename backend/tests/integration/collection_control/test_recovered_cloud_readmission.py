"""Read actual recovered cloud state through the public composition proof path."""

import os
import shutil
import sqlite3
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCredentialBindingsV1,
)
from agentmonitor.composition.ollama_cloud_collection import OllamaCloudCollectionV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.registry.application.cloud_connection import (
    resolve_active_credential_binding,
)

LIVE = Path("/home/dev/.local/share/agentmonitor/agentmonitor.db")


def test_actual_recovered_target_can_rederive_scheduled_proof(tmp_path: Path) -> None:
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    target = root / "agentmonitor.db"
    os.close(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
    try:
        with sqlite3.connect(f"file:{LIVE}?mode=ro", uri=True) as source:
            with sqlite3.connect(target) as copy:
                source.backup(copy)
                recovered = copy.execute(
                    "SELECT a.account_id,j.run_id,j.admission_id,u.released_at "
                    "FROM collection_cloud_uncertain_outcome u "
                    "JOIN collection_ollama_cloud_admission a ON "
                    "a.admission_id=u.admission_id "
                    "JOIN collection_cloud_attempt_journal j ON "
                    "j.admission_id=u.admission_id "
                    "WHERE u.reason='abandoned_outcome_unknown' "
                    "AND u.released_at IS NOT NULL "
                    "ORDER BY u.recorded_at DESC LIMIT 1"
                ).fetchone()
                if recovered is None:
                    pytest.skip("actual_recovered_cloud_target_unavailable")
        reference = DatabaseRefV1(target, root)
        binding = resolve_active_credential_binding(
            SqliteCredentialBindingsV1(reference).read(OpaqueIdV1(recovered[0]))
        )
        assert binding is not None
        proof = OllamaCloudCollectionV1(reference).scheduled_proof_for_binding(binding)
        assert proof.account_id == binding.account_id
        if proof.authorization_signal_run_id == OpaqueIdV1(recovered[1]):
            assert proof.authorization_signal == "transient_failure"
            assert proof.authorization_signal_dispatch_certainty == "may_have_started"
            assert proof.authorization_signal_admission_id == OpaqueIdV1(recovered[2])
        else:
            from datetime import datetime

            assert proof.authorization_signal_observed_at is not None
            assert proof.authorization_signal_observed_at >= datetime.fromisoformat(
                recovered[3].replace("Z", "+00:00")
            )
        assert proof.probe_run_id != proof.authorization_signal_run_id
        with sqlite3.connect(target) as copy:
            assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        shutil.rmtree(root)
