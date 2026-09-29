"""Real checked-in generated/build artifact identities, no invented versions."""

import hashlib
from pathlib import Path

from agentmonitor.composition.bootstrap import build_metadata


def test_build_inventory_reports_actual_generated_artifacts() -> None:
    root = Path(__file__).resolve().parents[3]
    metadata = build_metadata()
    assert (
        metadata.openapi_hash
        == hashlib.sha256(
            (root / "contracts/openapi/agentmonitor-v1.json").read_bytes()
        ).hexdigest()
    )
    assert (
        metadata.client_hash
        == hashlib.sha256(
            (root / "frontend/src/generated/api/index.ts").read_bytes()
        ).hexdigest()
    )
    versions = dict(metadata.component_versions)
    assert versions["api"] == metadata.application_version
    assert versions["openapi"] == "3.1.0"
    assert versions["client"]
    if (root / "frontend/dist/dashboard.html").exists():
        assert metadata.frontend_hash is not None
        assert versions["frontend"]
