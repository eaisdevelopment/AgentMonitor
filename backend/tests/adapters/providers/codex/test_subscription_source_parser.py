"""Pure allowlist parsing for Codex 0.160.0 account rate limits."""

import hashlib
from dataclasses import fields

import pytest
from agentmonitor.adapters.providers.codex.subscription.source import (
    CodexRateLimitsFailure,
    parse_rate_limits_v1,
)


def _fingerprint(account_id: str = "provider-account-1") -> str:
    return hashlib.sha256(("codex\x00" + account_id).encode()).hexdigest()


def _window(used: int) -> dict[str, object]:
    return {
        "usedPercent": used,
        "windowDurationMins": 300,
        "resetsAt": 1_791_460_800,
    }


def test_multi_bucket_response_is_reduced_to_the_closed_source_schema() -> None:
    parsed = parse_rate_limits_v1(
        {
            "accountId": "provider-account-1",
            "ordinaryUsageAllowed": True,
            "rateLimits": {
                "limitId": "legacy",
                "primary": _window(99),
            },
            "rateLimitsByLimitId": {
                "codex": {
                    "limitId": "codex",
                    "limitName": "Codex",
                    "planType": "plus",
                    "primary": _window(18),
                    "secondary": {
                        "usedPercent": 41,
                        "windowDurationMins": None,
                        "resetsAt": None,
                    },
                    "rateLimitReachedType": None,
                    "credits": {"balance": "forbidden"},
                    "individualLimit": {"used": "forbidden"},
                }
            },
            "rateLimitResetCredits": {"availableCount": 8},
            "rateLimitUpsell": {"content": "forbidden"},
        },
        expected_identity_fingerprint=_fingerprint(),
    )

    assert parsed.ordinary_usage_allowed is True
    assert len(parsed.buckets) == 1
    bucket = parsed.buckets[0]
    assert bucket.limit_id == "codex"
    assert bucket.safe_label == "Codex"
    assert bucket.primary.used_percent == 18
    assert bucket.secondary is not None
    assert bucket.secondary.window_duration_minutes is None
    names = {
        item.name
        for value in (parsed, bucket, bucket.primary)
        for item in fields(value)
    }
    assert names.isdisjoint(
        {
            "account_id",
            "raw_payload",
            "credits",
            "individual_limit",
            "reset_credits",
            "upsell",
        }
    )
    assert "provider-account-1" not in repr(parsed)


def test_legacy_bucket_uses_its_native_limit_id() -> None:
    parsed = parse_rate_limits_v1(
        {
            "accountId": "provider-account-1",
            "ordinaryUsageAllowed": None,
            "rateLimits": {
                "limitId": "codex-legacy",
                "limitName": None,
                "planType": None,
                "primary": _window(5),
                "secondary": None,
                "rateLimitReachedType": None,
            },
            "rateLimitsByLimitId": None,
        },
        expected_identity_fingerprint=_fingerprint(),
    )

    assert tuple(item.limit_id for item in parsed.buckets) == ("codex-legacy",)


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ({"accountId": "provider-account-2"}, "codex_quota_identity_mismatch"),
        ({"accountId": None}, "codex_quota_identity_invalid"),
        ({"ordinaryUsageAllowed": "yes"}, "codex_quota_permission_invalid"),
        ({"rateLimitsByLimitId": {}}, "codex_quota_bucket_set_invalid"),
    ],
)
def test_invalid_top_level_rate_limit_response_fails_closed(
    mutation: dict[str, object], code: str
) -> None:
    payload: dict[str, object] = {
        "accountId": "provider-account-1",
        "ordinaryUsageAllowed": True,
        "rateLimits": {"limitId": "codex", "primary": _window(18)},
        "rateLimitsByLimitId": {"codex": {"limitId": "codex", "primary": _window(18)}},
    }
    payload.update(mutation)

    with pytest.raises(CodexRateLimitsFailure, match=f"^{code}$"):
        parse_rate_limits_v1(
            payload,
            expected_identity_fingerprint=_fingerprint(),
        )


def test_map_key_and_bucket_limit_id_must_match() -> None:
    with pytest.raises(CodexRateLimitsFailure, match="^codex_quota_limit_id_mismatch$"):
        parse_rate_limits_v1(
            {
                "accountId": "provider-account-1",
                "ordinaryUsageAllowed": True,
                "rateLimits": {"limitId": "codex", "primary": _window(18)},
                "rateLimitsByLimitId": {
                    "codex": {"limitId": "other", "primary": _window(18)}
                },
            },
            expected_identity_fingerprint=_fingerprint(),
        )


def test_mixed_limit_id_key_types_fail_sanitized_without_raw_exception_chain() -> None:
    with pytest.raises(
        CodexRateLimitsFailure,
        match="^codex_quota_limit_id_invalid$",
    ) as caught:
        parse_rate_limits_v1(
            {
                "accountId": "provider-account-1",
                "ordinaryUsageAllowed": True,
                "rateLimits": {"limitId": "codex", "primary": _window(18)},
                "rateLimitsByLimitId": {
                    "codex": {"limitId": "codex", "primary": _window(18)},
                    7: {"limitId": "seven", "primary": _window(18)},
                },
            },
            expected_identity_fingerprint=_fingerprint(),
        )
    assert caught.value.__cause__ is None


def test_provider_account_id_with_internal_whitespace_is_rejected() -> None:
    with pytest.raises(
        CodexRateLimitsFailure,
        match="^codex_quota_identity_invalid$",
    ):
        parse_rate_limits_v1(
            {
                "accountId": "provider account 1",
                "ordinaryUsageAllowed": True,
                "rateLimits": {"limitId": "codex", "primary": _window(18)},
                "rateLimitsByLimitId": None,
            },
            expected_identity_fingerprint=_fingerprint("provider account 1"),
        )
