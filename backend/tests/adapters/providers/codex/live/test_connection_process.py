"""Owned Codex initial authentication boundaries on the real local CLI."""

from __future__ import annotations

from pathlib import Path

import pytest
from agentmonitor.adapters.providers.codex.authentication.reauthentication import (
    CodexManagedAuthenticationTargetV1,
    begin_managed_profile_authentication_v1,
)
from agentmonitor.adapters.providers.codex.installation import (
    discover_default_installation,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def _target(**changes: object) -> CodexManagedAuthenticationTargetV1:
    values: dict[str, object] = {
        "profile_ref": OpaqueIdV1("codex-managed-profile"),
        "profile_protection": "managed",
        "expected_identity_available": True,
        "owner_interaction_granted": True,
        "existing_verified_identity": False,
    }
    values.update(changes)
    return CodexManagedAuthenticationTargetV1(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        (
            {"profile_protection": "protected_default"},
            "codex_managed_login_target_invalid",
        ),
        ({"expected_identity_available": False}, "codex_managed_login_target_invalid"),
        ({"owner_interaction_granted": False}, "codex_managed_login_target_invalid"),
        ({"existing_verified_identity": True}, "codex_reauthentication_not_in_m5"),
    ],
)
def test_initial_login_rejects_ineligible_target_before_provider_io(
    tmp_path: Path,
    changes: dict[str, object],
    code: str,
) -> None:
    """M5-CDX-CONNECT-001: protected or historical profiles never start login."""
    installation = discover_default_installation()
    root = tmp_path / "managed-codex"
    root.mkdir(mode=0o700)

    with pytest.raises(ValueError, match=code):
        begin_managed_profile_authentication_v1(
            installation,
            _target(**changes),
            managed_profiles_root=root.parent,
            managed_profile_root=root,
            expected_email="owner@example.invalid",
        )

    assert tuple(root.iterdir()) == ()


@pytest.mark.parametrize(
    "expected_email",
    ("", "owner", " owner@example.invalid", "owner@example.invalid\n"),
)
def test_initial_login_rejects_invalid_expected_identity_without_writes(
    tmp_path: Path, expected_email: str
) -> None:
    """M5-CDX-CONNECT-002: expected identity is mandatory before provider I/O."""
    installation = discover_default_installation()
    root = tmp_path / "managed-codex"
    root.mkdir(mode=0o700)

    with pytest.raises(ValueError, match="codex_managed_login_target_invalid"):
        begin_managed_profile_authentication_v1(
            installation,
            _target(),
            managed_profiles_root=root.parent,
            managed_profile_root=root,
            expected_email=expected_email,
        )

    assert tuple(root.iterdir()) == ()


def test_initial_login_refuses_a_symlinked_managed_root(tmp_path: Path) -> None:
    """M5-CDX-CONNECT-003: login cannot follow a profile-root symlink."""
    installation = discover_default_installation()
    target = tmp_path / "target"
    target.mkdir(mode=0o700)
    linked = tmp_path / "managed-codex"
    linked.symlink_to(target, target_is_directory=True)

    with pytest.raises(ValueError, match="codex_managed_profile_unsafe"):
        begin_managed_profile_authentication_v1(
            installation,
            _target(),
            managed_profiles_root=linked.parent,
            managed_profile_root=linked,
            expected_email="owner@example.invalid",
        )

    assert tuple(target.iterdir()) == ()


def test_initial_login_refuses_a_private_root_outside_the_explicit_provider_root(
    tmp_path: Path,
) -> None:
    """M5-CDX-CONNECT-003: a private directory is not itself a profile grant."""
    installation = discover_default_installation()
    profiles_root = tmp_path / "profiles" / "codex"
    profiles_root.mkdir(mode=0o700, parents=True)
    profiles_root.parent.chmod(0o700)
    other_root = tmp_path / "other" / "managed-codex"
    other_root.mkdir(mode=0o700, parents=True)
    other_root.parent.chmod(0o700)

    with pytest.raises(ValueError, match="codex_managed_profile_unsafe"):
        begin_managed_profile_authentication_v1(
            installation,
            _target(),
            managed_profiles_root=profiles_root,
            managed_profile_root=other_root,
            expected_email="owner@example.invalid",
        )

    assert tuple(profiles_root.iterdir()) == ()
    assert tuple(other_root.iterdir()) == ()
