"""Fail-closed Claude managed-profile reauthentication boundary.

M4 has read-only authentication health only.  The reviewed ``CLA-I09``
isolated-profile packet is not approved, so this module intentionally performs
no provider I/O.  A future change may add the official owner-driven flow only
behind that packet and the existing M02 workflow coordinator.
"""

from dataclasses import dataclass
from typing import Literal

from agentmonitor.contracts import provider_system_v1
from agentmonitor.contracts.common_v1 import OpaqueIdV1


@dataclass(frozen=True, slots=True)
class ClaudeReauthenticationTargetV1:
    """Opaque target metadata used by the pre-I/O authorization gate."""

    profile_ref: OpaqueIdV1
    profile_protection: provider_system_v1.ProfileProtectionV1
    expected_identity_available: bool
    owner_interaction_granted: bool

    def __post_init__(self) -> None:
        if (
            type(self.expected_identity_available) is not bool
            or type(self.owner_interaction_granted) is not bool
        ):
            raise ValueError("claude_reauthentication_target_invalid")


@dataclass(frozen=True, slots=True)
class ClaudeReauthenticationDecisionV1:
    """Typed unavailable result; no provider response or credential is carried."""

    state: Literal["unavailable"]
    reason_code: str
    provider_io_started: bool


def request_reauthentication(
    target: ClaudeReauthenticationTargetV1,
) -> ClaudeReauthenticationDecisionV1:
    """Reject unsafe or not-yet-approved reauthentication before provider I/O."""
    if target.profile_protection == "protected_default":
        return ClaudeReauthenticationDecisionV1(
            "unavailable", "protected_default_profile", False
        )
    if target.profile_protection != "managed":
        return ClaudeReauthenticationDecisionV1(
            "unavailable", "profile_protection_unknown", False
        )
    if not target.expected_identity_available:
        return ClaudeReauthenticationDecisionV1(
            "unavailable", "expected_identity_required", False
        )
    if not target.owner_interaction_granted:
        return ClaudeReauthenticationDecisionV1(
            "unavailable", "owner_interaction_required", False
        )
    # CLA-I09 is intentionally not approved in M4.  Keep the final gate in
    # this module so a caller cannot accidentally reach /login before the
    # separately reviewed packet is wired into the implementation.
    return ClaudeReauthenticationDecisionV1(
        "unavailable", "managed_reauthentication_not_approved", False
    )
