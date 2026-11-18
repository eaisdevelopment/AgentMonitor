"""Read actual current metadata only; absence is not a passed lifecycle claim."""

import time
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1

from tools.automation.implementations.auto_m7 import (
    CREDENTIAL_LIFECYCLE_ABSENCE_REASONS as ABSENCE_REASONS,
)
from tools.automation.implementations.m7_credential_lifecycle import (
    LIVE,
    _retained_location,
    inspect_metadata,
)


def test_real_registry_requires_binding_history_before_store_inspection() -> None:
    reference = DatabaseRefV1(LIVE / "agentmonitor.db", LIVE)
    candidate, reason = inspect_metadata(reference, deadline=time.monotonic() + 70)
    if candidate is None:
        assert reason in ABSENCE_REASONS
        print("M7 LIFECYCLE METADATA: NOT_RUN " + str(reason))
        return
    assert reason is None
    assert candidate.target.connection.provider_key in {"claude", "codex"}
    assert candidate.retired.lifecycle == "cleanup_complete"
    assert candidate.previous.binding_id == candidate.retired.binding_id
    assert candidate.replacement.binding_id == candidate.target.binding.binding_id
    assert candidate.previous.generation < candidate.replacement.generation
    assert candidate.previous.completed_at <= candidate.replacement.requested_at
    assert candidate.previous.digest and candidate.replacement.digest
    print("M7 LIFECYCLE METADATA: candidate_present; physical_store_not_inspected")


def test_retained_location_read_preserves_real_staging_metadata(tmp_path: Path) -> None:
    """The operator's normal reader cleans staging; the observer must only read."""
    root = tmp_path / "owner-private"
    root.mkdir(mode=0o700)
    location = root / ".ollama-env-location"
    selected = root / "separate-credential-directory" / ".env"
    location.write_text(str(selected))  # Nonsecret configuration path, no key file.
    location.chmod(0o600)
    staging = root / (".ollama-env-location-tmp-" + "1" * 32)
    staging.write_text(str(selected))
    staging.chmod(0o600)
    before = {item.name: item.read_bytes() for item in root.iterdir()}
    assert _retained_location(root) == selected
    assert {item.name: item.read_bytes() for item in root.iterdir()} == before
    assert not (root / ".ollama-env-staging.lock").exists()
    assert not selected.exists()
