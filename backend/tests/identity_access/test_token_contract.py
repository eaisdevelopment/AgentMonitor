"""Pure V1 bearer and token-management outcome invariants."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.identity_access_v1 import (
    ApiTokenMutationOutcomeV1,
    ApiTokenSummaryV1,
    BearerTokenResolutionV1,
    IamSecurityEventViewV1,
    PrincipalV1,
)


def _summary() -> ApiTokenSummaryV1:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return ApiTokenSummaryV1(
        OpaqueIdV1("token-id"),
        "operator label",
        "abcdefgh",
        ("write:tokens",),
        now,
        now + timedelta(days=90),
        None,
        None,
        None,
        None,
        None,
        "active",
        1,
    )


def test_bearer_resolution_requires_matching_live_bearer_principal() -> None:
    summary = _summary()
    principal = PrincipalV1(
        OpaqueIdV1("administrator"),
        "api_bearer",
        summary.api_token_id,
        ("write:tokens",),
        summary.issued_at,
        summary.issued_at,
        summary.expires_at,
    )
    accepted = BearerTokenResolutionV1("authenticated", principal, summary)
    assert accepted.token == summary
    with pytest.raises(ValueError, match="bearer_resolution_pair_invalid"):
        BearerTokenResolutionV1("dashboard_authentication_required", principal, None)
    with pytest.raises(ValueError, match="bearer_resolution_pair_invalid"):
        BearerTokenResolutionV1("authenticated", None, summary)
    wrong_method = PrincipalV1(
        principal.principal_id,
        "browser_session",
        principal.credential_id,
        principal.effective_permissions,
        principal.issued_at,
        principal.authenticated_at,
        principal.expires_at,
    )
    with pytest.raises(ValueError, match="bearer_resolution_pair_invalid"):
        BearerTokenResolutionV1("authenticated", wrong_method, summary)


def test_one_time_replay_metadata_is_all_or_none_and_secret_free() -> None:
    summary = _summary()
    replay = ApiTokenMutationOutcomeV1(
        "one_time_secret_not_replayable",
        summary.api_token_id,
        1,
        "active",
    )
    assert replay.api_token_id == summary.api_token_id
    with pytest.raises(ValueError, match="token_mutation_metadata_pair_invalid"):
        ApiTokenMutationOutcomeV1("one_time_secret_not_replayable")
    with pytest.raises(ValueError, match="token_mutation_metadata_pair_invalid"):
        ApiTokenMutationOutcomeV1("scope_escalation_denied", summary.api_token_id, 1)


def test_stale_active_precondition_outcome_carries_no_resource_metadata() -> None:
    summary = _summary()
    stale = ApiTokenMutationOutcomeV1("precondition_failed")
    assert stale.code == "precondition_failed"
    assert stale.api_token_id is None
    with pytest.raises(ValueError, match="token_mutation_metadata_pair_invalid"):
        ApiTokenMutationOutcomeV1(
            "precondition_failed",
            summary.api_token_id,
            summary.record_version,
            "active",
        )


def test_token_audit_projection_accepts_only_reviewed_shapes() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    created = IamSecurityEventViewV1(
        OpaqueIdV1("event"),
        "api_token_created",
        now,
        now,
        OpaqueIdV1("administrator"),
        "api_bearer",
        "api_token",
        OpaqueIdV1("token"),
        "created",
        None,
        OpaqueIdV1("request"),
        1,
        None,
    )
    assert created.authentication_method == "api_bearer"
    with pytest.raises(ValueError, match="iam_audit_code_invalid"):
        IamSecurityEventViewV1(
            OpaqueIdV1("event"),
            "api_token_created",
            now,
            now,
            OpaqueIdV1("administrator"),
            "api_bearer",
            "api_token",
            OpaqueIdV1("token"),
            "revoked",
            None,
            OpaqueIdV1("request"),
            1,
            None,
        )


def test_public_token_summary_rejects_unsafe_or_incoherent_fields() -> None:
    summary = _summary()
    for changed in (
        {"name": "line\nsecret"},
        {"safe_prefix": "secret!"},
        {"scopes": ("read:status",)},
        {"record_version": 0},
        {"expires_at": summary.issued_at},
        {"state": "revoked"},
    ):
        with pytest.raises(ValueError, match="token_summary_invalid"):
            replace(summary, **changed)
