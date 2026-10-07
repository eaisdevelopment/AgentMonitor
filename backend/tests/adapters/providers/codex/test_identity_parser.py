"""Pure closed-shape tests for Codex account identity parsing."""

from datetime import UTC, datetime

import pytest
from agentmonitor.adapters.providers.codex.authentication.identity import (
    CodexIdentityFailure,
    parse_account_identity_v1,
)


def test_chatgpt_identity_is_allowlisted_and_fingerprinted() -> None:
    observed_at = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)

    identity = parse_account_identity_v1(
        {
            "account": {
                "type": "chatgpt",
                "email": "owner@example.invalid",
                "planType": "plus",
            },
            "requiresOpenaiAuth": False,
            "workspaceRouting": {
                "chatgptAccountId": "account-owner-1",
                "ignored": "provider detail",
            },
        },
        provider_version="0.160.0",
        observed_at=observed_at,
    )

    assert identity is not None
    assert identity.email == "owner@example.invalid"
    assert identity.provider_organization is None
    assert identity.provider_version == "0.160.0"
    assert identity.observed_at == observed_at
    assert len(identity.fingerprint) == 64
    assert "owner@example.invalid" not in repr(identity)


def test_auth_required_is_an_explicit_absent_identity() -> None:
    assert (
        parse_account_identity_v1(
            {"account": None, "requiresOpenaiAuth": True},
            provider_version="0.160.0",
            observed_at=datetime(2026, 10, 7, 12, 0, tzinfo=UTC),
        )
        is None
    )


@pytest.mark.parametrize(
    "payload",
    [
        {
            "account": {
                "type": "chatgpt",
                "email": "owner@example.invalid",
                "planType": "plus",
            },
            "requiresOpenaiAuth": False,
            "workspaceRouting": {"chatgptAccountId": "account owner"},
        },
        {
            "account": {},
            "requiresOpenaiAuth": True,
            "workspaceRouting": None,
        },
        {
            "account": None,
            "requiresOpenaiAuth": True,
            "workspaceRouting": {"chatgptAccountId": "unexpected"},
        },
    ],
)
def test_identity_rejects_ambiguous_account_ids_and_inconsistent_auth_shapes(
    payload: dict[str, object],
) -> None:
    with pytest.raises(CodexIdentityFailure, match="^codex_identity_invalid$"):
        parse_account_identity_v1(
            payload,
            provider_version="0.160.0",
            observed_at=datetime(2026, 10, 7, 12, 0, tzinfo=UTC),
        )


def test_stable_provider_account_changes_the_private_fingerprint() -> None:
    observed_at = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
    base: dict[str, object] = {
        "account": {
            "type": "chatgpt",
            "email": "owner@example.invalid",
            "planType": "plus",
        },
        "requiresOpenaiAuth": False,
        "workspaceRouting": {"chatgptAccountId": "account-owner-1"},
    }
    first = parse_account_identity_v1(
        base, provider_version="0.160.0", observed_at=observed_at
    )
    second = parse_account_identity_v1(
        {**base, "workspaceRouting": {"chatgptAccountId": "account-owner-2"}},
        provider_version="0.160.0",
        observed_at=observed_at,
    )

    assert first is not None and second is not None
    assert first.fingerprint != second.fingerprint
    assert "account-owner" not in repr(first)


@pytest.mark.parametrize(
    "payload",
    [
        {"account": None, "requiresOpenaiAuth": False},
        {"account": {"type": "apiKey"}, "requiresOpenaiAuth": False},
        {
            "account": {
                "type": "chatgpt",
                "email": None,
                "planType": "plus",
            },
            "requiresOpenaiAuth": False,
        },
        {
            "account": {
                "type": "chatgpt",
                "email": "owner@example.invalid",
                "planType": "invented",
            },
            "requiresOpenaiAuth": False,
            "workspaceRouting": {"chatgptAccountId": "account-owner-1"},
        },
        {
            "account": {
                "type": "chatgpt",
                "email": "owner@example.invalid",
                "planType": "plus",
            },
            "requiresOpenaiAuth": False,
            "workspaceRouting": None,
        },
    ],
)
def test_non_subscription_or_incomplete_identity_fails_closed(
    payload: dict[str, object],
) -> None:
    with pytest.raises(CodexIdentityFailure, match="codex_identity_invalid"):
        parse_account_identity_v1(
            payload,
            provider_version="0.160.0",
            observed_at=datetime(2026, 10, 7, 12, 0, tzinfo=UTC),
        )
