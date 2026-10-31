"""Exact pure policies for the Codex M5 mutation gate."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from agentmonitor.adapters.providers.codex.authentication.identity import (
    CodexIdentityFailure,
    parse_account_identity_v1,
)
from agentmonitor.adapters.providers.codex.manifest import build_codex_manifest
from agentmonitor.adapters.providers.codex.subscription.mapper import (
    map_codex_quota_to_capacity,
    map_subscription_quota,
)
from agentmonitor.adapters.providers.codex.subscription.schema import (
    CodexRateLimitBucketSourceV1,
    CodexRateLimitsSourceV1,
    CodexRateLimitWindowSourceV1,
    InvalidCodexRateLimitsSourceV1,
)
from agentmonitor.adapters.providers.codex.subscription.source import (
    CodexRateLimitsFailure,
    parse_rate_limits_v1,
)
from agentmonitor.contracts.collection_control_v1 import CollectionRunAdmissionV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1

OBSERVED_AT = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
MAX_UNIX_SECONDS = 253_402_300_799
SCHEMA_DIGEST = "36bd8e1d76b12b89b06446a85c45e957945eb8cb63b05061264c3dec97f625da"
MAPPING_DIGEST = "417c46ba301f9c4217c606beed52be93c9bf497da9ca5b99ca4b1993167688d3"


def _manifest_row(declaration: object) -> tuple[object, ...]:
    item = declaration
    source = item.sources[0]  # type: ignore[attr-defined]
    versions = item.schema_versions  # type: ignore[attr-defined]
    rule = item.provider_version_rule  # type: ignore[attr-defined]
    constraints = item.constraints  # type: ignore[attr-defined]
    return (
        item.capability_id,  # type: ignore[attr-defined]
        (
            versions.minimum.major,
            versions.minimum.minor,
            versions.maximum.major,
            versions.maximum.minor,
        ),
        item.decision,  # type: ignore[attr-defined]
        item.stability,  # type: ignore[attr-defined]
        item.reason_code,  # type: ignore[attr-defined]
        item.evidence_reference,  # type: ignore[attr-defined]
        item.port_type,  # type: ignore[attr-defined]
        item.output_schema,  # type: ignore[attr-defined]
        (
            source.source_id,
            source.provider_key,
            source.capability_id,
            source.source_class,
            source.stability,
            source.mechanism_version,
            source.credential_role,
            source.side_effect_class,
            source.evidence_reference,
            source.is_experimental,
        ),
        (
            rule.rule_id,
            rule.scheme,
            rule.verified_versions,
        ),
        (
            constraints.deadline_ms,
            constraints.minimum_interval_ms,
            constraints.maximum_concurrency,
            constraints.automatic_retry_count,
            constraints.provider_request_count,
            constraints.provider_request_count_availability.state,
        ),
        item.side_effect_class,  # type: ignore[attr-defined]
        item.platforms,  # type: ignore[attr-defined]
    )


def test_manifest_exactly_declares_every_admitted_codex_policy() -> None:
    """M5-CDX-GATE-012: the exact manifest policy must resist semantic mutation."""
    manifest = build_codex_manifest()
    app_server = f"codex-app-server-v2@0.160.0+schema.{SCHEMA_DIGEST}"

    assert (
        manifest.descriptor.adapter_id,
        manifest.descriptor.adapter_version,
        manifest.descriptor.provider_key,
        manifest.descriptor.protocol_versions.minimum,
        manifest.descriptor.protocol_versions.maximum,
        manifest.descriptor.build_identity,
        manifest.manifest_schema_version,
        manifest.m0_mapping_id,
        manifest.m0_mapping_version,
        manifest.m0_mapping_digest,
    ) == (
        "agentmonitor.codex",
        "1.0.2",
        "codex",
        "1.0.0",
        "1.0.0",
        "agentmonitor-codex-v1",
        "1.0.0",
        "M5-CDX-0-160-0-002",
        "1.0.0",
        MAPPING_DIGEST,
    )
    assert tuple(_manifest_row(item) for item in manifest.declarations) == (
        (
            "installation.discovery",
            (1, 0, 1, 0),
            "supported",
            "documented",
            "accepted_exact_installed_tuple",
            "M5-CDX-0-160-0-002",
            "InstallationDiscoveryPortV1",
            "DiscoveryOutcomeV1",
            (
                "codex.version.banner.v1",
                "codex",
                "installation.discovery",
                "supported_cli",
                "documented",
                "codex-cli@0.160.0",
                "none",
                "read_only",
                "M5-CDX-0-160-0-002",
                False,
            ),
            ("codex-cli-0-160-0-installation-exact", "opaque_exact", ("0.160.0",)),
            (3_000, 0, 1, 0, None, "unknown"),
            "read_only",
            ("linux-x86_64",),
        ),
        (
            "identity.verification",
            (1, 0, 1, 0),
            "experimental",
            "experimental",
            "approved_experimental_exact_tuple",
            "M5-CDX-0-160-0-002",
            "ProviderCapabilityPortV1",
            "ObservedProfileIdentityV1",
            (
                "codex.app-server.account-read.v2",
                "codex",
                "identity.verification",
                "experimental_private_or_browser",
                "experimental",
                app_server,
                "agentmonitor_managed_profile",
                "managed_profile_write",
                "M5-CDX-0-160-0-002",
                True,
            ),
            ("codex-cli-0-160-0-identity-exact", "opaque_exact", ("0.160.0",)),
            (30_000, 0, 1, 0, None, "unknown"),
            "managed_profile_write",
            ("linux-x86_64",),
        ),
        (
            "authentication.health",
            (1, 0, 1, 0),
            "experimental",
            "experimental",
            "approved_experimental_exact_tuple",
            "M5-CDX-0-160-0-002",
            "AuthenticationHealthPortV1",
            "AuthHealthObservationV1",
            (
                "codex.app-server.account-read.v2",
                "codex",
                "authentication.health",
                "experimental_private_or_browser",
                "experimental",
                app_server,
                "agentmonitor_managed_profile",
                "managed_profile_write",
                "M5-CDX-0-160-0-002",
                True,
            ),
            ("codex-cli-0-160-0-auth-health-exact", "opaque_exact", ("0.160.0",)),
            (30_000, 0, 1, 0, None, "unknown"),
            "managed_profile_write",
            ("linux-x86_64",),
        ),
        (
            "subscription.quota",
            (1, 0, 1, 0),
            "experimental",
            "experimental",
            "approved_experimental_exact_tuple",
            "M5-CDX-0-160-0-002",
            "SubscriptionQuotaPortV1",
            "CodexSubscriptionQuotaV1",
            (
                "codex.app-server.account-rate-limits-read.v2",
                "codex",
                "subscription.quota",
                "experimental_private_or_browser",
                "experimental",
                app_server,
                "agentmonitor_managed_profile",
                "managed_profile_write",
                "M5-CDX-0-160-0-002",
                True,
            ),
            ("codex-cli-0-160-0-quota-exact", "opaque_exact", ("0.160.0",)),
            (30_000, 300_000, 1, 0, None, "unknown"),
            "managed_profile_write",
            ("linux-x86_64",),
        ),
        (
            "authentication.reauthenticate",
            (1, 0, 1, 0),
            "experimental",
            "experimental",
            "approved_experimental_exact_tuple",
            "M5-CDX-0-160-0-002",
            "ProviderConnectionPortV1",
            "ProviderConnectionViewV1",
            (
                "codex.login.browser.v1",
                "codex",
                "authentication.reauthenticate",
                "experimental_private_or_browser",
                "experimental",
                "codex-cli@0.160.0",
                "agentmonitor_managed_profile",
                "managed_profile_write",
                "M5-CDX-0-160-0-002",
                True,
            ),
            (
                "codex-cli-0-160-0-managed-reauth-exact",
                "opaque_exact",
                ("0.160.0",),
            ),
            (600_000, 0, 1, 0, None, "unknown"),
            "managed_profile_write",
            ("linux-x86_64",),
        ),
    )


def _identity_payload(
    *,
    email: object = "owner@example.invalid",
    plan_type: object = "plus",
    account_id: object = "account-owner-1",
) -> dict[str, object]:
    return {
        "account": {"type": "chatgpt", "email": email, "planType": plan_type},
        "requiresOpenaiAuth": True,
        "workspaceRouting": {"chatgptAccountId": account_id},
    }


def test_identity_fingerprint_has_exact_domain_separation() -> None:
    parsed = parse_account_identity_v1(
        _identity_payload(),
        provider_version="0.160.0",
        observed_at=OBSERVED_AT,
    )

    assert parsed is not None
    assert parsed.fingerprint == (
        "6e73b7c51762763b1ceaeadc216e77f7226b7cdf174a7fe5952258ecf62739e5"
    )


@pytest.mark.parametrize(
    ("email", "account_id", "provider_version"),
    (
        ("a@.", "a", "v"),
        ("a" * 251 + "@a.", "x" * 256, "v" * 64),
    ),
)
def test_identity_accepts_every_exact_closed_boundary(
    email: str, account_id: str, provider_version: str
) -> None:
    parsed = parse_account_identity_v1(
        _identity_payload(email=email, account_id=account_id),
        provider_version=provider_version,
        observed_at=OBSERVED_AT,
    )

    assert parsed is not None
    assert parsed.email == email
    assert parsed.provider_version == provider_version


@pytest.mark.parametrize(
    "email",
    (
        "a" * 252 + "@a.",
        "a@\x00.",
        "@a.",
        "a.b",
        "aa@",
        "a@b.c@d",
    ),
)
def test_identity_rejects_each_email_policy_violation(email: str) -> None:
    with pytest.raises(CodexIdentityFailure) as caught:
        parse_account_identity_v1(
            _identity_payload(email=email),
            provider_version="0.160.0",
            observed_at=OBSERVED_AT,
        )
    assert str(caught.value) == "codex_identity_invalid"


@pytest.mark.parametrize("account_id", ("", "x" * 257, "a\x00b"))
def test_identity_rejects_each_account_id_policy_violation(account_id: str) -> None:
    with pytest.raises(CodexIdentityFailure) as caught:
        parse_account_identity_v1(
            _identity_payload(account_id=account_id),
            provider_version="0.160.0",
            observed_at=OBSERVED_AT,
        )
    assert caught.value.args == ("codex_identity_invalid",)


@pytest.mark.parametrize("provider_version", ("", "v" * 65, "vé", 160))
def test_identity_rejects_each_provider_version_policy_violation(
    provider_version: object,
) -> None:
    with pytest.raises(CodexIdentityFailure) as caught:
        parse_account_identity_v1(
            _identity_payload(),
            provider_version=provider_version,  # type: ignore[arg-type]
            observed_at=OBSERVED_AT,
        )
    assert caught.value.args == ("codex_identity_invalid",)


@pytest.mark.parametrize(
    "observed_at",
    (
        "2026-10-07T12:00:00Z",
        datetime(2026, 10, 7, 12, 0),
        datetime(2026, 10, 7, 13, 0, tzinfo=timezone(timedelta(hours=1))),
    ),
)
def test_identity_rejects_each_observation_time_policy_violation(
    observed_at: object,
) -> None:
    with pytest.raises(CodexIdentityFailure) as caught:
        parse_account_identity_v1(
            _identity_payload(),
            provider_version="0.160.0",
            observed_at=observed_at,  # type: ignore[arg-type]
        )
    assert caught.value.args == ("codex_identity_invalid",)


def test_identity_rejects_invalid_email_even_with_a_typed_plan() -> None:
    with pytest.raises(CodexIdentityFailure) as caught:
        parse_account_identity_v1(
            _identity_payload(email="invalid", plan_type="plus"),
            provider_version="0.160.0",
            observed_at=OBSERVED_AT,
        )
    assert caught.value.args == ("codex_identity_invalid",)


def test_identity_account_shape_failure_is_exact() -> None:
    with pytest.raises(CodexIdentityFailure) as caught:
        parse_account_identity_v1(
            {"account": {}, "requiresOpenaiAuth": True},
            provider_version="0.160.0",
            observed_at=OBSERVED_AT,
        )
    assert caught.value.args == ("codex_identity_invalid",)


def _source_window(
    used_percent: int = 18,
    *,
    duration: int | None = 300,
    reset: int | None = 1_791_460_800,
) -> dict[str, object]:
    return {
        "usedPercent": used_percent,
        "windowDurationMins": duration,
        "resetsAt": reset,
    }


def _source_payload(
    *,
    account_id: object = "provider-account-1",
    by_limit_id: object | None = None,
) -> dict[str, object]:
    if by_limit_id is None:
        by_limit_id = {
            "codex": {
                "limitId": "codex",
                "limitName": "Codex",
                "planType": "plus",
                "primary": _source_window(),
                "secondary": _source_window(41, duration=None, reset=None),
                "rateLimitReachedType": "rate_limit_reached",
            }
        }
    return {
        "accountId": account_id,
        "ordinaryUsageAllowed": True,
        "rateLimits": {"limitId": "legacy", "primary": _source_window(99)},
        "rateLimitsByLimitId": by_limit_id,
    }


def _source_fingerprint(account_id: str = "provider-account-1") -> str:
    return hashlib.sha256(("codex\x00" + account_id).encode("utf-8")).hexdigest()


def test_source_parser_preserves_every_allowlisted_field_exactly() -> None:
    parsed = parse_rate_limits_v1(
        _source_payload(), expected_identity_fingerprint=_source_fingerprint()
    )

    assert parsed == CodexRateLimitsSourceV1(
        ordinary_usage_allowed=True,
        buckets=(
            CodexRateLimitBucketSourceV1(
                limit_id="codex",
                safe_label="Codex",
                plan_type="plus",
                rate_limit_reached_type="rate_limit_reached",
                primary=CodexRateLimitWindowSourceV1(
                    used_percent=18,
                    window_duration_minutes=300,
                    resets_at_unix_seconds=1_791_460_800,
                ),
                secondary=CodexRateLimitWindowSourceV1(
                    used_percent=41,
                    window_duration_minutes=None,
                    resets_at_unix_seconds=None,
                ),
            ),
        ),
    )


@pytest.mark.parametrize("account_id", ("a", "x" * 256))
def test_source_parser_accepts_exact_account_id_boundaries(account_id: str) -> None:
    parsed = parse_rate_limits_v1(
        _source_payload(account_id=account_id),
        expected_identity_fingerprint=_source_fingerprint(account_id),
    )
    assert len(parsed.buckets) == 1


@pytest.mark.parametrize("account_id", ("", "x" * 257, "a\x00b"))
def test_source_parser_rejects_account_id_policy_violations(account_id: str) -> None:
    with pytest.raises(CodexRateLimitsFailure) as caught:
        parse_rate_limits_v1(
            _source_payload(account_id=account_id),
            expected_identity_fingerprint=_source_fingerprint(account_id),
        )
    assert caught.value.args == ("codex_quota_identity_invalid",)


@pytest.mark.parametrize("fingerprint", (7, "g" * 64, "a" * 63))
def test_source_parser_rejects_invalid_expected_fingerprint(
    fingerprint: object,
) -> None:
    with pytest.raises(CodexRateLimitsFailure) as caught:
        parse_rate_limits_v1(
            _source_payload(),
            expected_identity_fingerprint=fingerprint,  # type: ignore[arg-type]
        )
    assert caught.value.args == ("codex_quota_expected_identity_invalid",)


def test_source_parser_rejects_non_mapping_payload_with_sanitized_failure() -> None:
    with pytest.raises(CodexRateLimitsFailure) as caught:
        parse_rate_limits_v1(
            [],  # type: ignore[arg-type]
            expected_identity_fingerprint=_source_fingerprint(),
        )
    assert caught.value.args == ("codex_quota_expected_identity_invalid",)


def _source_bucket(limit_id: str) -> dict[str, object]:
    return {"limitId": limit_id, "primary": _source_window()}


def test_source_parser_accepts_32_buckets_and_rejects_33() -> None:
    accepted = {
        f"bucket-{index:02d}": _source_bucket(f"bucket-{index:02d}")
        for index in range(32)
    }
    rejected = {
        f"bucket-{index:02d}": _source_bucket(f"bucket-{index:02d}")
        for index in range(33)
    }

    parsed = parse_rate_limits_v1(
        _source_payload(by_limit_id=accepted),
        expected_identity_fingerprint=_source_fingerprint(),
    )
    assert len(parsed.buckets) == 32
    with pytest.raises(CodexRateLimitsFailure) as caught:
        parse_rate_limits_v1(
            _source_payload(by_limit_id=rejected),
            expected_identity_fingerprint=_source_fingerprint(),
        )
    assert caught.value.args == ("codex_quota_bucket_set_invalid",)


def test_source_failure_keeps_the_exact_sanitized_code() -> None:
    failure = CodexRateLimitsFailure("codex_quota_window_invalid")
    assert failure.code == "codex_quota_window_invalid"
    assert failure.args == ("codex_quota_window_invalid",)


def _schema_window(
    *,
    used: int = 18,
    duration: int | None = 300,
    reset: int | None = 1_791_460_800,
) -> CodexRateLimitWindowSourceV1:
    return CodexRateLimitWindowSourceV1(
        used_percent=used,
        window_duration_minutes=duration,
        resets_at_unix_seconds=reset,
    )


def _schema_bucket(
    limit_id: object = "codex", safe_label: object = "Codex"
) -> CodexRateLimitBucketSourceV1:
    return CodexRateLimitBucketSourceV1(
        limit_id=limit_id,  # type: ignore[arg-type]
        safe_label=safe_label,  # type: ignore[arg-type]
        plan_type="plus",
        rate_limit_reached_type="rate_limit_reached",
        primary=_schema_window(),
        secondary=None,
    )


def test_source_schema_failure_keeps_exact_code_and_exception_message() -> None:
    failure = InvalidCodexRateLimitsSourceV1("codex_source_label_invalid")
    assert failure.code == "codex_source_label_invalid"
    assert failure.args == ("codex_source_label_invalid",)
    assert str(failure) == "codex_source_label_invalid"


@pytest.mark.parametrize("label", ("x", "x" * 96, None))
def test_source_schema_accepts_exact_safe_label_boundaries(label: str | None) -> None:
    assert _schema_bucket(safe_label=label).safe_label == label


@pytest.mark.parametrize("label", ("", "x" * 97, " label", "a\x00b", 7))
def test_source_schema_rejects_each_safe_label_violation(label: object) -> None:
    with pytest.raises(InvalidCodexRateLimitsSourceV1) as caught:
        _schema_bucket(safe_label=label)
    assert caught.value.args == ("codex_source_label_invalid",)


@pytest.mark.parametrize("used", (0, 100))
def test_source_schema_accepts_exact_percentage_boundaries(used: int) -> None:
    assert _schema_window(used=used).used_percent == used


def test_source_schema_reports_exact_percentage_failure_code() -> None:
    with pytest.raises(InvalidCodexRateLimitsSourceV1) as caught:
        _schema_window(used=-1)
    assert caught.value.code == "codex_source_used_percent_invalid"
    assert caught.value.args == ("codex_source_used_percent_invalid",)


@pytest.mark.parametrize("duration", (1, 2**63 - 1))
def test_source_schema_accepts_exact_duration_boundaries(duration: int) -> None:
    assert _schema_window(duration=duration).window_duration_minutes == duration


@pytest.mark.parametrize("duration", (0, 2**63))
def test_source_schema_reports_exact_duration_failure_code(duration: int) -> None:
    with pytest.raises(InvalidCodexRateLimitsSourceV1) as caught:
        _schema_window(duration=duration)
    assert caught.value.code == "codex_source_duration_invalid"
    assert caught.value.args == ("codex_source_duration_invalid",)


@pytest.mark.parametrize("reset", (0, MAX_UNIX_SECONDS))
def test_source_schema_accepts_exact_reset_boundaries(reset: int) -> None:
    assert _schema_window(reset=reset).resets_at_unix_seconds == reset


def test_source_schema_reports_exact_reset_failure_code() -> None:
    with pytest.raises(InvalidCodexRateLimitsSourceV1) as caught:
        _schema_window(reset=MAX_UNIX_SECONDS + 1)
    assert caught.value.code == "codex_source_reset_invalid"
    assert caught.value.args == ("codex_source_reset_invalid",)


def test_source_schema_rejects_non_string_limit_id_with_sanitized_failure() -> None:
    with pytest.raises(InvalidCodexRateLimitsSourceV1) as caught:
        _schema_bucket(limit_id=7)
    assert caught.value.args == ("codex_source_limit_id_invalid",)


def test_source_schema_accepts_32_buckets_and_rejects_33_or_wrong_type() -> None:
    accepted = tuple(_schema_bucket(f"bucket-{index:02d}") for index in range(32))
    assert len(CodexRateLimitsSourceV1(True, accepted).buckets) == 32

    with pytest.raises(InvalidCodexRateLimitsSourceV1) as too_many:
        CodexRateLimitsSourceV1(True, accepted + (_schema_bucket("extra"),))
    assert too_many.value.args == ("codex_source_bucket_set_invalid",)

    with pytest.raises(InvalidCodexRateLimitsSourceV1) as wrong_type:
        CodexRateLimitsSourceV1(
            True,
            (_schema_window(),),  # type: ignore[arg-type]
        )
    assert wrong_type.value.args == ("codex_source_bucket_set_invalid",)


def _mapping_source() -> CodexRateLimitsSourceV1:
    return CodexRateLimitsSourceV1(
        ordinary_usage_allowed=True,
        buckets=(
            CodexRateLimitBucketSourceV1(
                limit_id="zeta",
                safe_label="Zeta",
                plan_type="pro",
                rate_limit_reached_type="workspace_owner_credits_depleted",
                primary=_schema_window(used=25, duration=60, reset=None),
                secondary=_schema_window(used=50, duration=120, reset=0),
            ),
            CodexRateLimitBucketSourceV1(
                limit_id="alpha",
                safe_label=None,
                plan_type="plus",
                rate_limit_reached_type="rate_limit_reached",
                primary=_schema_window(used=10, duration=1, reset=MAX_UNIX_SECONDS),
                secondary=None,
            ),
        ),
    )


def _admission() -> CollectionRunAdmissionV1:
    return CollectionRunAdmissionV1(
        run_id=OpaqueIdV1("collection-run-codex"),
        schedule_id=OpaqueIdV1("collection-schedule-codex"),
        request_id=OpaqueIdV1("collection-request-codex"),
        trigger="scheduled",
        operation_family="collect.subscription.quota",
        requested_capability_ids=("subscription.quota",),
        capability_set_version="1.0.0",
        request_auth_method="service",
        request_principal_id=OpaqueIdV1("service-one"),
        correlation_id=OpaqueIdV1("correlation-codex"),
        causation_id=None,
        target_key_digest="b" * 64,
        provider_key="codex",
        installation_id=OpaqueIdV1("installation-codex"),
        account_id=OpaqueIdV1("account-codex"),
        profile_id=OpaqueIdV1("profile-codex"),
        resource_id=OpaqueIdV1("resource-codex"),
        capability_id="subscription.quota",
        source_id="codex.app-server.account-rate-limits-read.v2",
        adapter_version="1.0.2",
        provider_version="0.160.0",
        adapter_protocol_version="1.0.0",
        manifest_fingerprint="e" * 64,
        collection_policy_version="1.0.0",
        registry_revision=11,
        retry_chain_id=OpaqueIdV1("retry-chain-codex"),
        attempt_ordinal=1,
        target_generation=12,
        scheduler_instance_id=OpaqueIdV1("scheduler-codex"),
        lease_policy_version="1.0.0",
        budget_policy_id="provider-request-budget-v1",
        budget_policy_version="1.0.0",
        budget_scope_digest="d" * 64,
        budget_dimension="provider_requests",
        budget_unit="request",
        budget_units=1,
        budget_limit_units=1,
        budget_window_start=OBSERVED_AT,
        budget_window_end=OBSERVED_AT + timedelta(minutes=5),
        payload_schema="ProviderQuotaInputV1@1",
        idempotency_key_digest="f" * 64,
        request_digest="a" * 64,
        requested_at=OBSERVED_AT,
        deadline_at=OBSERVED_AT + timedelta(seconds=30),
    )


def test_subscription_mapper_preserves_all_native_fields_and_order() -> None:
    quota = map_subscription_quota(
        _mapping_source(),
        account_ref=OpaqueIdV1("account-codex"),
        resource_ref=OpaqueIdV1("resource-codex"),
    )

    assert quota.ordinary_usage_allowed is True
    assert tuple(bucket.limit_id for bucket in quota.buckets) == ("alpha", "zeta")
    alpha, zeta = quota.buckets
    assert (
        alpha.safe_label,
        alpha.plan_type,
        alpha.rate_limit_reached_type,
        alpha.primary.role,
        alpha.primary.used_percent,
        alpha.primary.remaining_percent,
        alpha.primary.window_duration_minutes,
        alpha.primary.resets_at,
        alpha.secondary,
    ) == (
        None,
        "plus",
        "rate_limit_reached",
        "primary",
        Decimal("10"),
        Decimal("90"),
        1,
        datetime.fromtimestamp(MAX_UNIX_SECONDS, tz=UTC),
        None,
    )
    assert (
        zeta.safe_label,
        zeta.plan_type,
        zeta.rate_limit_reached_type,
        zeta.primary.window_duration_minutes,
        zeta.secondary.role if zeta.secondary is not None else None,
        zeta.secondary.window_duration_minutes if zeta.secondary is not None else None,
        zeta.secondary.resets_at if zeta.secondary is not None else None,
    ) == (
        "Zeta",
        "pro",
        "workspace_owner_credits_depleted",
        60,
        "secondary",
        120,
        datetime.fromtimestamp(0, tz=UTC),
    )


def test_capacity_mapper_preserves_exact_target_and_window_policy() -> None:
    admission = _admission()
    quota = map_subscription_quota(
        _mapping_source(),
        account_ref=OpaqueIdV1("account-codex"),
        resource_ref=OpaqueIdV1("resource-codex"),
    )
    capacity = map_codex_quota_to_capacity(quota, admission)

    assert (
        capacity.subject.provider_key,
        capacity.subject.installation_id,
        capacity.subject.account_id,
        capacity.subject.resource_id,
    ) == (
        "codex",
        OpaqueIdV1("installation-codex"),
        OpaqueIdV1("account-codex"),
        OpaqueIdV1("resource-codex"),
    )
    assert tuple(window.window_key for window in capacity.windows) == (
        "alpha:primary",
        "zeta:primary",
        "zeta:secondary",
    )
    assert tuple(window.safe_label for window in capacity.windows) == (
        "alpha",
        "Zeta",
        "Zeta",
    )
    assert all(window.is_constraining is True for window in capacity.windows)
    assert all(
        window.limit.reason_code == "source_does_not_report_native_limit_quantity"
        for window in capacity.windows
    )


def test_capacity_target_failure_code_is_exact() -> None:
    quota = map_subscription_quota(
        _mapping_source(),
        account_ref=OpaqueIdV1("account-codex"),
        resource_ref=OpaqueIdV1("resource-codex"),
    )
    wrong = replace(_admission(), provider_key="claude")

    with pytest.raises(ValueError) as caught:
        map_codex_quota_to_capacity(quota, wrong)
    assert caught.value.args == ("codex_capacity_target_mismatch",)
