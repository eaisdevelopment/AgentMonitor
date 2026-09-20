"""CTR-IAM V1 published safe values and transient credential boundary."""

import dataclasses
import json
import pickle
import secrets
from datetime import UTC, datetime

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.identity_access_v1 import (
    ApiTokenSummaryV1,
    AuthorizationDecisionV1,
    BootstrapAdministratorOutcomeV1,
    IamHealthV1,
    IamInitializationStateV1,
    IamSecurityEventViewV1,
    PermissionV1,
    PrincipalV1,
    RecoverAdministratorOutcomeV1,
    SecretInputV1,
    SessionSummaryV1,
)


@pytest.mark.parametrize(
    ("value_type", "contract_id"),
    [
        (PrincipalV1, "CTR-IAM-001"),
        (PermissionV1, "CTR-IAM-001"),
        (AuthorizationDecisionV1, "CTR-IAM-002"),
        (IamInitializationStateV1, "CTR-IAM-004"),
        (BootstrapAdministratorOutcomeV1, "CTR-IAM-004"),
        (RecoverAdministratorOutcomeV1, "CTR-IAM-004"),
        (SessionSummaryV1, "CTR-IAM-005"),
        (ApiTokenSummaryV1, "CTR-IAM-007"),
        (IamSecurityEventViewV1, "CTR-IAM-008"),
        (IamHealthV1, "CTR-IAM-008"),
    ],
)
def test_published_iam_values_have_exact_owner_and_version(
    value_type: type, contract_id: str
) -> None:
    for field_name, expected in (
        ("CONTRACT_ID", contract_id),
        ("CONTRACT_VERSION", "1.0.0"),
        ("OWNER", "PLAN-M01"),
    ):
        assert getattr(value_type, field_name) == expected
    assert dataclasses.is_dataclass(value_type)


def test_transient_secret_refuses_common_serializers_and_redacts_repr() -> None:
    secret = SecretInputV1(secrets.token_urlsafe(32))
    is_dataclass = dataclasses.is_dataclass(secret)
    safe_repr = repr(secret)
    safe_str = str(secret)
    assert is_dataclass is False
    assert safe_repr == "<SecretInputV1 redacted>"
    assert safe_str == "<SecretInputV1 redacted>"
    with pytest.raises(TypeError):
        dataclasses.asdict(secret)  # type: ignore[call-overload]  # intentional rejection test
    with pytest.raises(TypeError):
        pickle.dumps(secret)
    with pytest.raises(TypeError):
        json.dumps(secret)


def test_bootstrap_outcome_cannot_pair_success_with_missing_id() -> None:
    with pytest.raises(ValueError, match="bootstrap_outcome_id_pair_invalid"):
        BootstrapAdministratorOutcomeV1("created", None)
    with pytest.raises(ValueError, match="bootstrap_outcome_id_pair_invalid"):
        BootstrapAdministratorOutcomeV1(
            "administrator_already_initialized", OpaqueIdV1("opaque")
        )


def test_initialization_state_requires_policy_only_when_initialized() -> None:
    with pytest.raises(ValueError, match="iam_initialization_policy_pair_invalid"):
        IamInitializationStateV1("initialized", None, "v1_0100")
    with pytest.raises(ValueError, match="iam_initialization_policy_pair_invalid"):
        IamInitializationStateV1(
            "uninitialized", "argon2id-rfc9106-low-memory-v1", "v1_0100"
        )


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("event_type", "unreviewed_event"),
        ("outcome_code", "unreviewed_outcome"),
        ("target_type", "unreviewed_target"),
        ("reason_code", "unreviewed_reason"),
    ],
)
def test_security_event_view_refuses_unreviewed_codes(
    field_name: str, invalid_value: str
) -> None:
    now = datetime.now(UTC)
    values: dict[str, object] = {
        "event_id": OpaqueIdV1("event"),
        "event_type": "administrator_initialized",
        "occurred_at": now,
        "recorded_at": now,
        "actor_principal_id": None,
        "authentication_method": None,
        "target_type": "administrator",
        "target_id": OpaqueIdV1("administrator"),
        "outcome_code": "created",
        "reason_code": None,
        "correlation_id": OpaqueIdV1("correlation"),
        "schema_version": 1,
        "aggregate_count": None,
    }
    values[field_name] = invalid_value
    with pytest.raises(ValueError, match="iam_audit_code_invalid"):
        IamSecurityEventViewV1(**values)  # type: ignore[arg-type]


def test_security_event_view_accepts_only_current_producer_metadata() -> None:
    now = datetime.now(UTC)
    event = IamSecurityEventViewV1(
        OpaqueIdV1("event"),
        "administrator_initialized",
        now,
        now,
        None,
        None,
        "administrator",
        OpaqueIdV1("administrator"),
        "created",
        None,
        OpaqueIdV1("correlation"),
        1,
        None,
    )
    assert event.event_type == "administrator_initialized"


def test_recovery_outcome_refuses_failure_counts_and_noninteger_counts() -> None:
    with pytest.raises(ValueError, match="recovery_outcome_count_invalid"):
        RecoverAdministratorOutcomeV1("iam_repository_unavailable", None, 1, 1)
    with pytest.raises(ValueError, match="recovery_outcome_count_invalid"):
        RecoverAdministratorOutcomeV1("recovered", OpaqueIdV1("administrator"), True, 0)


def test_recovery_contract_includes_policy_violation_outcome() -> None:
    outcome = RecoverAdministratorOutcomeV1("password_policy_violation", None, 0, 0)
    assert outcome.code == "password_policy_violation"
