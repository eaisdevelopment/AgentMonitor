"""Pure checks distinguish natural recovery from local or ambiguous failures."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts.collection_recovery_v1 import (
    CollectionRecoveryRunV1,
    CollectionRecoveryScopeV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.collection_control.domain.recovery_evidence import (
    committed_recovery_after,
    latest_natural_failure,
)

NOW = datetime(2026, 11, 3, 12, tzinfo=UTC)
SCOPE = CollectionRecoveryScopeV1(
    OpaqueIdV1("account"),
    OpaqueIdV1("target"),
    3,
    "subscription.quota",
    "ollama.cloud.balance.v1",
    "1.1.0",
    "a" * 64,
    "ProviderQuotaInputV2@2",
    "ollama",
)


def failure() -> CollectionRecoveryRunV1:
    return CollectionRecoveryRunV1(
        OpaqueIdV1("failure"),
        "ollama",
        SCOPE.account_id,
        "cloud_service",
        SCOPE.access_target_id,
        3,
        SCOPE.capability_id,
        SCOPE.source_id,
        SCOPE.adapter_version,
        SCOPE.source_fingerprint,
        SCOPE.payload_schema,
        NOW,
        NOW + timedelta(seconds=1),
        "failed",
        "response_received",
        "failed",
        "unauthorized",
        None,
        (),
    )


def success() -> CollectionRecoveryRunV1:
    return replace(
        failure(),
        run_id=OpaqueIdV1("success"),
        requested_at=NOW + timedelta(seconds=300),
        completed_at=NOW + timedelta(seconds=301),
        state="partial",
        response_outcome="succeeded",
        failure_code=None,
        payload_digest="b" * 64,
        observation_ids=(OpaqueIdV1("observation"),),
    )


def test_exact_natural_failure_and_later_committed_success() -> None:
    failed = failure()
    assert latest_natural_failure((failed,), SCOPE) == failed
    assert committed_recovery_after((failed, success()), failed, SCOPE) == success()


@pytest.mark.parametrize(
    "code",
    [
        "pre_dispatch_failed",
        "internal_adapter_error",
        "invalid_provider_data",
        "unexpected_response",
        None,
    ],
)
def test_local_parser_or_unknown_failure_is_not_natural(code: str | None) -> None:
    assert (
        latest_natural_failure((replace(failure(), failure_code=code),), SCOPE) is None
    )


def test_provider_unavailable_without_durable_http_status_is_not_natural() -> None:
    """The same durable shape can represent a local HTTP-200 body-read failure."""
    unavailable = replace(failure(), failure_code="provider_unavailable")
    assert latest_natural_failure((unavailable,), SCOPE) is None


@pytest.mark.parametrize("certainty", ["not_started", "may_have_started", None])
def test_undispatched_or_ambiguous_failure_is_not_natural(
    certainty: str | None,
) -> None:
    assert (
        latest_natural_failure(
            (replace(failure(), dispatch_certainty=certainty),), SCOPE
        )
        is None
    )


def test_superseded_failure_is_not_a_current_failed_target() -> None:
    assert latest_natural_failure((failure(), success()), SCOPE) is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("account_id", OpaqueIdV1("other-account")),
        ("access_target_id", OpaqueIdV1("other-target")),
        ("binding_generation", 4),
        ("source_id", "other.source.v1"),
        ("provider_key", "codex"),
        ("adapter_version", "2.0.0"),
        ("source_fingerprint", "c" * 64),
        ("payload_schema", "ProviderQuotaInputV3@3"),
    ],
)
def test_changed_scope_does_not_reuse_old_failure(field: str, value: object) -> None:
    changed = replace(SCOPE, **{field: value})
    assert latest_natural_failure((failure(),), changed) is None
    assert committed_recovery_after((success(),), failure(), changed) is None


def test_missing_commit_or_out_of_order_success_is_not_recovery() -> None:
    failed = failure()
    for candidate in (
        replace(success(), observation_ids=()),
        replace(success(), payload_digest=None),
        replace(success(), dispatch_certainty="may_have_started"),
        replace(success(), requested_at=NOW, completed_at=NOW + timedelta(seconds=1)),
    ):
        assert committed_recovery_after((candidate,), failed, SCOPE) is None


def test_query_rejects_mixed_provider_scope_before_io() -> None:
    from agentmonitor.contracts.collection_recovery_v1 import CollectionRecoveryQueryV1

    with pytest.raises(ValueError, match="collection_recovery_query_invalid"):
        CollectionRecoveryQueryV1("codex", NOW, NOW + timedelta(minutes=1), SCOPE)


@pytest.mark.parametrize(
    "outcome,code",
    [
        ("failed", "unauthorized"),
        ("failed", "access_denied"),
        ("rate_limited", "rate_limited"),
    ],
)
def test_received_provider_auth_and_rate_failures_can_recover(
    outcome: str, code: str
) -> None:
    failed = replace(failure(), response_outcome=outcome, failure_code=code)
    assert latest_natural_failure((failed,), SCOPE) == failed
    assert committed_recovery_after((failed, success()), failed, SCOPE) == success()
