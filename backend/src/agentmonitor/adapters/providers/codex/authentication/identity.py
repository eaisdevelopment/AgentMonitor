"""Allowlisted Codex ChatGPT identity from the managed app-server boundary."""

from __future__ import annotations

import hashlib
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.providers.codex.installation import CodexInstallationV1
from agentmonitor.adapters.providers.codex.transport import (
    CodexAppServerFailure,
    invoke_codex_app_server_v1,
)
from agentmonitor.contracts.provider_system_v1 import ObservedProfileIdentityV1

_PLAN_TYPES = frozenset(
    {
        "free",
        "go",
        "plus",
        "pro",
        "prolite",
        "promax",
        "team",
        "self_serve_business_prolite",
        "self_serve_business_usage_based",
        "business",
        "ent26",
        "enterprise_cbp_automation",
        "enterprise_cbp_usage_based",
        "enterprise",
        "edu",
        "edu_plus",
        "edu_pro",
        "unknown",
    }
)


class CodexIdentityFailure(ValueError):
    """The provider identity response is absent, unsafe, or out of contract."""


def _valid_email(value: object) -> bool:
    if type(value) is not str or value != value.strip() or not 3 <= len(value) <= 254:
        return False
    if not value.isprintable() or any(character.isspace() for character in value):
        return False
    local, separator, domain = value.rpartition("@")
    return bool(local and separator and domain and "." in domain)


def parse_account_identity_v1(
    payload: dict[str, object],
    *,
    provider_version: str,
    observed_at: datetime,
) -> ObservedProfileIdentityV1 | None:
    """Reduce one response to the identity contract without raw payload escape."""
    if type(payload) is not dict:
        raise CodexIdentityFailure("codex_identity_invalid")
    provider_requires_auth = payload.get("requiresOpenaiAuth")
    if type(provider_requires_auth) is not bool:
        raise CodexIdentityFailure("codex_identity_invalid")
    account = payload.get("account")
    workspace = payload.get("workspaceRouting")
    if account is None:
        if provider_requires_auth and workspace is None:
            return None
        raise CodexIdentityFailure("codex_identity_invalid")
    if not provider_requires_auth:
        raise CodexIdentityFailure("codex_identity_invalid")
    if type(account) is not dict or account.get("type") != "chatgpt":
        raise CodexIdentityFailure("codex_identity_invalid")
    email = account.get("email")
    plan_type = account.get("planType")
    provider_account_id = (
        workspace.get("chatgptAccountId") if type(workspace) is dict else None
    )
    if (
        not _valid_email(email)
        or type(plan_type) is not str
        or plan_type not in _PLAN_TYPES
        or type(provider_account_id) is not str
        or provider_account_id != provider_account_id.strip()
        or not 1 <= len(provider_account_id) <= 256
        or not provider_account_id.isprintable()
        or any(character.isspace() for character in provider_account_id)
    ):
        raise CodexIdentityFailure("codex_identity_invalid")
    if (
        type(provider_version) is not str
        or not 1 <= len(provider_version) <= 64
        or not provider_version.isascii()
        or type(observed_at) is not datetime
        or observed_at.utcoffset() != timedelta(0)
    ):
        raise CodexIdentityFailure("codex_identity_invalid")
    assert isinstance(email, str)
    assert isinstance(provider_account_id, str)
    fingerprint = hashlib.sha256(
        ("codex\x00" + provider_account_id).encode("utf-8")
    ).hexdigest()
    return ObservedProfileIdentityV1(
        email=email,
        provider_organization=None,
        fingerprint=fingerprint,
        observed_at=observed_at,
        provider_version=provider_version,
    )


def read_managed_profile_identity_v1(
    installation: CodexInstallationV1,
    *,
    managed_profiles_root: Path,
    managed_profile_root: Path,
    deadline_monotonic: float | None = None,
) -> ObservedProfileIdentityV1 | None:
    """Read one managed identity with provider-controlled auth maintenance."""
    deadline = (
        time.monotonic() + 10.0 if deadline_monotonic is None else deadline_monotonic
    )

    def parse(payload: dict[str, object]) -> ObservedProfileIdentityV1 | None:
        return parse_account_identity_v1(
            payload,
            provider_version=installation.provider_version,
            observed_at=datetime.now(UTC),
        )

    try:
        return invoke_codex_app_server_v1(
            installation,
            managed_profiles_root=managed_profiles_root,
            managed_profile_root=managed_profile_root,
            method="account/read",
            deadline_monotonic=deadline,
            parse_result=parse,
        )
    except CodexAppServerFailure as error:
        if error.code == "codex_managed_authentication_required":
            return None
        raise
