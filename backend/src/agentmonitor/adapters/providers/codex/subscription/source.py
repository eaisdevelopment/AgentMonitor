"""Bounded Codex app-server rate-limit source with immediate raw disposal."""

from __future__ import annotations

import hashlib
import hmac
import re
import time
from pathlib import Path
from typing import cast

from agentmonitor.adapters.providers.codex.installation import CodexInstallationV1
from agentmonitor.adapters.providers.codex.subscription.schema import (
    CodexRateLimitBucketSourceV1,
    CodexRateLimitsSourceV1,
    CodexRateLimitWindowSourceV1,
    InvalidCodexRateLimitsSourceV1,
)
from agentmonitor.adapters.providers.codex.transport import invoke_codex_app_server_v1
from agentmonitor.contracts.providers.codex.subscription_quota.v1.schema import (
    CodexPlanTypeV1,
    CodexRateLimitReachedTypeV1,
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class CodexRateLimitsFailure(ValueError):
    """A sanitized failure at the native subscription response boundary."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _provider_fingerprint(provider_account_id: str) -> str:
    return hashlib.sha256(("codex\x00" + provider_account_id).encode()).hexdigest()


def _window(value: object) -> CodexRateLimitWindowSourceV1:
    if type(value) is not dict:
        raise CodexRateLimitsFailure("codex_quota_window_invalid")
    try:
        return CodexRateLimitWindowSourceV1(
            used_percent=value.get("usedPercent"),  # type: ignore[arg-type]
            window_duration_minutes=value.get("windowDurationMins"),
            resets_at_unix_seconds=value.get("resetsAt"),
        )
    except InvalidCodexRateLimitsSourceV1 as error:
        raise CodexRateLimitsFailure(error.code) from None


def _bucket(value: object, *, map_limit_id: str | None) -> CodexRateLimitBucketSourceV1:
    if type(value) is not dict:
        raise CodexRateLimitsFailure("codex_quota_bucket_invalid")
    payload_limit_id = value.get("limitId")
    if map_limit_id is not None:
        if payload_limit_id is not None and payload_limit_id != map_limit_id:
            raise CodexRateLimitsFailure("codex_quota_limit_id_mismatch")
        limit_id: object = map_limit_id
    else:
        limit_id = payload_limit_id
    primary = value.get("primary")
    secondary = value.get("secondary")
    try:
        return CodexRateLimitBucketSourceV1(
            limit_id=limit_id,  # type: ignore[arg-type]
            safe_label=value.get("limitName"),
            plan_type=cast(CodexPlanTypeV1 | None, value.get("planType")),
            rate_limit_reached_type=cast(
                CodexRateLimitReachedTypeV1 | None,
                value.get("rateLimitReachedType"),
            ),
            primary=_window(primary),
            secondary=_window(secondary) if secondary is not None else None,
        )
    except InvalidCodexRateLimitsSourceV1 as error:
        raise CodexRateLimitsFailure(error.code) from None


def parse_rate_limits_v1(
    payload: dict[str, object],
    *,
    expected_identity_fingerprint: str,
) -> CodexRateLimitsSourceV1:
    """Allowlist native windows and discard identity, billing, and display data."""
    if (
        type(payload) is not dict
        or type(expected_identity_fingerprint) is not str
        or _SHA256.fullmatch(expected_identity_fingerprint) is None
    ):
        raise CodexRateLimitsFailure("codex_quota_expected_identity_invalid")
    provider_account_id = payload.get("accountId")
    if (
        type(provider_account_id) is not str
        or provider_account_id != provider_account_id.strip()
        or not 1 <= len(provider_account_id) <= 256
        or not provider_account_id.isprintable()
        or any(character.isspace() for character in provider_account_id)
    ):
        raise CodexRateLimitsFailure("codex_quota_identity_invalid")
    if not hmac.compare_digest(
        _provider_fingerprint(provider_account_id), expected_identity_fingerprint
    ):
        raise CodexRateLimitsFailure("codex_quota_identity_mismatch")

    ordinary_usage_allowed = payload.get("ordinaryUsageAllowed")
    if ordinary_usage_allowed is not None and type(ordinary_usage_allowed) is not bool:
        raise CodexRateLimitsFailure("codex_quota_permission_invalid")
    legacy = payload.get("rateLimits")
    if type(legacy) is not dict:
        raise CodexRateLimitsFailure("codex_quota_legacy_bucket_invalid")
    by_limit_id = payload.get("rateLimitsByLimitId")
    buckets: tuple[CodexRateLimitBucketSourceV1, ...]
    if by_limit_id is None:
        buckets = (_bucket(legacy, map_limit_id=None),)
    else:
        if type(by_limit_id) is not dict or not 1 <= len(by_limit_id) <= 32:
            raise CodexRateLimitsFailure("codex_quota_bucket_set_invalid")
        if not all(type(limit_id) is str for limit_id in by_limit_id):
            raise CodexRateLimitsFailure("codex_quota_limit_id_invalid")
        parsed: list[CodexRateLimitBucketSourceV1] = []
        for limit_id in sorted(by_limit_id):
            if type(limit_id) is not str:
                raise CodexRateLimitsFailure("codex_quota_limit_id_invalid")
            parsed.append(_bucket(by_limit_id[limit_id], map_limit_id=limit_id))
        buckets = tuple(parsed)
    try:
        return CodexRateLimitsSourceV1(
            ordinary_usage_allowed=ordinary_usage_allowed,
            buckets=buckets,
        )
    except InvalidCodexRateLimitsSourceV1 as error:
        raise CodexRateLimitsFailure(error.code) from None


def collect_rate_limits_once_v1(
    installation: CodexInstallationV1,
    *,
    managed_profiles_root: Path,
    managed_profile_root: Path,
    expected_identity_fingerprint: str,
    deadline_monotonic: float | None = None,
) -> CodexRateLimitsSourceV1:
    """Read one native subscription response from one verified managed profile."""
    deadline = (
        time.monotonic() + 30.0 if deadline_monotonic is None else deadline_monotonic
    )

    def parse(payload: dict[str, object]) -> CodexRateLimitsSourceV1:
        return parse_rate_limits_v1(
            payload,
            expected_identity_fingerprint=expected_identity_fingerprint,
        )

    return invoke_codex_app_server_v1(
        installation,
        managed_profiles_root=managed_profiles_root,
        managed_profile_root=managed_profile_root,
        method="account/rateLimits/read",
        deadline_monotonic=deadline,
        parse_result=parse,
    )
