"""Pure Codex 0.160.0 quota mapping checks; no provider I/O occurs."""

from dataclasses import fields, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
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
from agentmonitor.contracts.collection_control_v1 import CollectionRunAdmissionV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1

NOW = datetime(2026, 10, 7, 18, 0, tzinfo=UTC)
RESET_SECONDS = 1_791_460_800


def _admission(provider_key: str = "codex") -> CollectionRunAdmissionV1:
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
        provider_key=provider_key,
        installation_id=OpaqueIdV1("installation-codex"),
        account_id=OpaqueIdV1("account-codex"),
        profile_id=OpaqueIdV1("profile-codex"),
        resource_id=OpaqueIdV1("resource-codex"),
        capability_id="subscription.quota",
        source_id="codex.app_server.account_rate_limits.v2",
        adapter_version="1.0.0",
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
        budget_window_start=NOW,
        budget_window_end=NOW + timedelta(minutes=5),
        payload_schema="ProviderQuotaInputV1@1",
        idempotency_key_digest="f" * 64,
        request_digest="a" * 64,
        requested_at=NOW,
        deadline_at=NOW + timedelta(seconds=30),
    )


def _source() -> CodexRateLimitsSourceV1:
    return CodexRateLimitsSourceV1(
        ordinary_usage_allowed=True,
        buckets=(
            CodexRateLimitBucketSourceV1(
                limit_id="codex",
                safe_label="Codex",
                plan_type="plus",
                rate_limit_reached_type=None,
                primary=CodexRateLimitWindowSourceV1(
                    used_percent=18,
                    window_duration_minutes=300,
                    resets_at_unix_seconds=RESET_SECONDS,
                ),
                secondary=CodexRateLimitWindowSourceV1(
                    used_percent=41,
                    window_duration_minutes=None,
                    resets_at_unix_seconds=None,
                ),
            ),
        ),
    )


def test_codex_source_maps_native_roles_and_exact_remaining_to_capacity() -> None:
    """M5-CDX-PURE-009: native identity and exact arithmetic reach CTR-CAP-001."""
    admission = _admission()
    assert admission.account_id is not None and admission.resource_id is not None
    quota = map_subscription_quota(
        _source(),
        account_ref=admission.account_id,
        resource_ref=admission.resource_id,
    )

    assert quota.resource_kind == "subscription_pool"
    assert quota.buckets[0].limit_id == "codex"
    assert quota.buckets[0].primary.role == "primary"
    assert quota.buckets[0].primary.used_percent == Decimal("18")
    assert quota.buckets[0].primary.remaining_percent == Decimal("82")
    assert quota.buckets[0].primary.resets_at == datetime.fromtimestamp(
        RESET_SECONDS, tz=UTC
    )
    assert quota.buckets[0].secondary is not None
    assert quota.buckets[0].secondary.role == "secondary"
    assert quota.buckets[0].secondary.window_duration_minutes is None
    assert quota.buckets[0].secondary.resets_at is None

    capacity = map_codex_quota_to_capacity(quota, admission)

    assert capacity.subject.provider_key == "codex"
    assert capacity.registry_revision == 11
    assert capacity.capability_schema_version == "1.0"
    assert capacity.completeness == "complete_scope"
    assert tuple(window.window_key for window in capacity.windows) == (
        "codex:primary",
        "codex:secondary",
    )
    primary, secondary = capacity.windows
    assert primary.semantic_role == "primary"
    assert primary.used.value is not None
    assert primary.used.value.as_decimal() == Decimal("18")
    assert primary.used.value.unit == "percent"
    assert primary.used.value_kind == "provider_reported"
    assert primary.remaining.value is not None
    assert primary.remaining.value.as_decimal() == Decimal("82")
    assert primary.remaining.value.unit == "percent"
    assert primary.remaining.value_kind == "derived"
    assert primary.remaining_ratio.value is not None
    assert primary.remaining_ratio.value.as_decimal() == Decimal("0.82")
    assert primary.remaining_ratio.value.unit == "ratio"
    assert primary.limit.value is None
    assert primary.limit.availability.state == "unknown"
    assert primary.reset_at == datetime.fromtimestamp(RESET_SECONDS, tz=UTC)
    assert primary.reset_precision == "exact"
    assert secondary.reset_at is None
    assert secondary.reset_precision == "unknown"


def test_codex_source_schema_excludes_billing_credits_and_raw_payloads() -> None:
    """M5-CDX-PURE-001: source DTOs carry only the admitted subscription fields."""
    source = _source()
    all_names = {
        field.name
        for value in (source, source.buckets[0], source.buckets[0].primary)
        for field in fields(value)
    }

    assert all_names.isdisjoint(
        {
            "raw_payload",
            "credits",
            "reset_credits",
            "rate_limit_reset_credits",
            "balance",
            "spend_limit",
            "individual_limit",
            "openai_api",
            "account_id",
        }
    )
    with pytest.raises(TypeError):
        CodexRateLimitsSourceV1(
            ordinary_usage_allowed=True,
            buckets=source.buckets,
            raw_payload="forbidden",  # type: ignore[call-arg]
        )


@pytest.mark.parametrize("used_percent", [-1, 101, True, Decimal("18")])
def test_codex_source_window_rejects_invalid_used_percent(
    used_percent: object,
) -> None:
    """M5-CDX-PURE-010: wire percentage is an exact bounded JSON integer."""
    with pytest.raises(InvalidCodexRateLimitsSourceV1):
        CodexRateLimitWindowSourceV1(
            used_percent=used_percent,  # type: ignore[arg-type]
            window_duration_minutes=300,
            resets_at_unix_seconds=RESET_SECONDS,
        )


@pytest.mark.parametrize(
    ("duration", "reset"),
    [(0, RESET_SECONDS), (-1, RESET_SECONDS), (300, -1), (300, True)],
)
def test_codex_source_window_rejects_invalid_optional_numbers(
    duration: object, reset: object
) -> None:
    """M5-CDX-PURE-011: optional wire numbers are null or bounded integers."""
    with pytest.raises(InvalidCodexRateLimitsSourceV1):
        CodexRateLimitWindowSourceV1(
            used_percent=18,
            window_duration_minutes=duration,  # type: ignore[arg-type]
            resets_at_unix_seconds=reset,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("mismatch", ["provider", "account", "resource", "capability"])
def test_codex_capacity_mapper_rejects_a_different_target(mismatch: str) -> None:
    """M5-CDX-PURE-012: a Codex result cannot cross a collection target."""
    admission = _admission()
    assert admission.account_id is not None and admission.resource_id is not None
    quota = map_subscription_quota(
        _source(),
        account_ref=admission.account_id,
        resource_ref=admission.resource_id,
    )
    wrong = {
        "provider": replace(admission, provider_key="claude"),
        "account": replace(admission, account_id=OpaqueIdV1("account-other")),
        "resource": replace(admission, resource_id=OpaqueIdV1("resource-other")),
        "capability": replace(admission, capability_id="identity.read"),
    }[mismatch]

    with pytest.raises(ValueError, match="codex_capacity_target_mismatch"):
        map_codex_quota_to_capacity(quota, wrong)
