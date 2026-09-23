"""Pure M02 provider-identity fingerprint contract tests."""

from dataclasses import fields
from datetime import UTC, datetime

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    ConfirmProviderIdentityFingerprintCommandV1,
    ProviderIdentityResolutionV1,
    ResolveProviderIdentityFingerprintQueryV1,
)

NOW = datetime(2026, 9, 23, 12, 0, tzinfo=UTC)
SAFE_TEST_DIGEST = "7" * 64


def _command() -> ConfirmProviderIdentityFingerprintCommandV1:
    return ConfirmProviderIdentityFingerprintCommandV1(
        idempotency_key=OpaqueIdV1("identity-bind-command-1"),
        principal_id=OpaqueIdV1("owner-principal-1"),
        account_id=OpaqueIdV1("account-1"),
        expected_account_record_version=3,
        provider_key="claude",
        identity_scheme="claude.otel.account.sha256",
        identity_scope="provider_account",
        identity_scheme_version=1,
        subject_fingerprint=SAFE_TEST_DIGEST,
        source_id="claude.otel.metrics.http-json.v1",
        source_version="1.0.0",
        parser_version="1.0.0",
        evidence_reference=OpaqueIdV1("runtime-session-observation-1"),
        expected_evidence_digest="8" * 64,
        requested_at=NOW,
    )


def test_confirmation_contract_requires_explicit_account_version_and_owner() -> None:
    """M02-PURE-026: no sole-account or implicit-owner field exists."""
    command = _command()

    assert command.account_id == OpaqueIdV1("account-1")
    assert command.expected_account_record_version == 3
    assert command.principal_id == OpaqueIdV1("owner-principal-1")
    assert command.idempotency_key == OpaqueIdV1("identity-bind-command-1")
    names = {field.name for field in fields(command)}
    assert "email" not in names
    assert "raw_provider_account_id" not in names


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("provider_key", "owner@example.invalid"),
        ("subject_fingerprint", "not-a-sha256-fingerprint"),
        ("subject_fingerprint", "A" * 64),
        ("source_id", "unapproved/source"),
        ("evidence_reference", OpaqueIdV1("owner@example.invalid")),
        ("expected_evidence_digest", "not-a-sha256-digest"),
        ("identity_scheme_version", 0),
        ("expected_account_record_version", 0),
    ),
)
def test_confirmation_contract_rejects_raw_or_noncanonical_identity_values(
    field_name: str, value: object
) -> None:
    """M02-PURE-027: only bounded scheme metadata and lowercase SHA-256 fit."""
    values = {
        field.name: getattr(_command(), field.name) for field in fields(_command())
    }
    values[field_name] = value

    with pytest.raises(ValueError, match="registry_provider_identity_confirmation"):
        ConfirmProviderIdentityFingerprintCommandV1(**values)


def test_resolution_never_invents_an_account_for_unresolved_or_conflict() -> None:
    """M02-PURE-028: only resolved results may carry an exact account/version."""
    query = ResolveProviderIdentityFingerprintQueryV1(
        provider_key="claude",
        identity_scheme="claude.otel.account.sha256",
        identity_scope="provider_account",
        identity_scheme_version=1,
        subject_fingerprint=SAFE_TEST_DIGEST,
    )

    assert query.subject_fingerprint == SAFE_TEST_DIGEST
    assert (
        ProviderIdentityResolutionV1(
            "unresolved", None, None, "provider_identity_unresolved", 0
        ).account_id
        is None
    )
    assert (
        ProviderIdentityResolutionV1(
            "conflict", None, None, "provider_identity_conflict", 1
        ).account_id
        is None
    )
    with pytest.raises(ValueError, match="registry_provider_identity_resolution"):
        ProviderIdentityResolutionV1(
            "unresolved",
            OpaqueIdV1("account-1"),
            1,
            "provider_identity_unresolved",
            1,
        )
