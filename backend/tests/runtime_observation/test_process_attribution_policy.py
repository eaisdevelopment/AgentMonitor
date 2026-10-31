"""Pure M06 persistence-policy checks; no filesystem or database I/O."""

import pytest
from agentmonitor.adapters.persistence.runtime_observation.sqlite.repository import (
    RuntimeRepositoryErrorV1,
    _reconcile_process_attribution,
)

_FIRST_FINGERPRINT = "a" * 64
_SECOND_FINGERPRINT = "b" * 64


def test_verified_attribution_upgrades_an_existing_generic_process() -> None:
    """M06-DB-002: exact executable evidence may enrich the same process."""
    reconciled = _reconcile_process_attribution(
        existing_executable_identity=None,
        existing_provider_key=None,
        existing_installation_id=None,
        observed_executable_identity=_FIRST_FINGERPRINT,
        observed_provider_key="claude",
        observed_installation_id="installation-opaque",
    )

    assert reconciled == (
        _FIRST_FINGERPRINT,
        "claude",
        "installation-opaque",
    )


def test_generic_observation_cannot_erase_verified_attribution() -> None:
    """FR-DISC-002/008: weaker later input preserves established identity."""
    reconciled = _reconcile_process_attribution(
        existing_executable_identity=_FIRST_FINGERPRINT,
        existing_provider_key="claude",
        existing_installation_id="installation-opaque",
        observed_executable_identity=None,
        observed_provider_key=None,
        observed_installation_id=None,
    )

    assert reconciled == (
        _FIRST_FINGERPRINT,
        "claude",
        "installation-opaque",
    )


@pytest.mark.parametrize(
    (
        "observed_executable_identity",
        "observed_provider_key",
        "observed_installation_id",
    ),
    (
        (_SECOND_FINGERPRINT, "claude", "installation-opaque"),
        (_FIRST_FINGERPRINT, "codex", "installation-opaque"),
        (_FIRST_FINGERPRINT, "claude", "other-installation"),
    ),
)
def test_conflicting_verified_process_attribution_fails_closed(
    observed_executable_identity: str,
    observed_provider_key: str,
    observed_installation_id: str,
) -> None:
    """M06-DB-002/007: identity conflicts never rewrite current attribution."""
    with pytest.raises(
        RuntimeRepositoryErrorV1, match="runtime_process_identity_conflict"
    ):
        _reconcile_process_attribution(
            existing_executable_identity=_FIRST_FINGERPRINT,
            existing_provider_key="claude",
            existing_installation_id="installation-opaque",
            observed_executable_identity=observed_executable_identity,
            observed_provider_key=observed_provider_key,
            observed_installation_id=observed_installation_id,
        )
