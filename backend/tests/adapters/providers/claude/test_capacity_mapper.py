"""Pure Claude-to-capacity mapping evidence; no provider I/O occurs here."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from agentmonitor.adapters.providers.claude.subscription.mapper import (
    SanitizedClaudeUsageSnapshot,
    SanitizedClaudeUsageWindow,
    map_claude_quota_to_capacity,
    map_subscription_quota,
)
from agentmonitor.contracts.collection_control_v1 import CollectionRunAdmissionV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1

NOW = datetime(2026, 9, 22, 14, 0, tzinfo=UTC)


def _admission() -> CollectionRunAdmissionV1:
    return CollectionRunAdmissionV1(
        run_id=OpaqueIdV1("collection-run-one"),
        schedule_id=OpaqueIdV1("collection-schedule-one"),
        request_id=OpaqueIdV1("collection-request-one"),
        trigger="manual",
        operation_family="collect.subscription.quota",
        requested_capability_ids=("subscription.quota",),
        capability_set_version="1.0.0",
        request_auth_method="owner_session",
        request_principal_id=OpaqueIdV1("owner-one"),
        correlation_id=OpaqueIdV1("correlation-one"),
        causation_id=None,
        target_key_digest="b" * 64,
        provider_key="claude",
        installation_id=OpaqueIdV1("installation-one"),
        account_id=OpaqueIdV1("account-one"),
        profile_id=OpaqueIdV1("profile-one"),
        resource_id=OpaqueIdV1("resource-one"),
        capability_id="subscription.quota",
        source_id="claude.subscription.usage.screen_reader",
        adapter_version="1.0.0",
        provider_version="2.1.278",
        adapter_protocol_version="1.0.0",
        manifest_fingerprint="e" * 64,
        collection_policy_version="1.0.0",
        registry_revision=7,
        retry_chain_id=OpaqueIdV1("retry-chain-one"),
        attempt_ordinal=1,
        target_generation=1,
        scheduler_instance_id=OpaqueIdV1("scheduler-instance-one"),
        lease_policy_version="1.0.0",
        budget_policy_id="provider-request-budget-v1",
        budget_policy_version="1.0.0",
        budget_scope_digest="d" * 64,
        budget_dimension="provider_requests",
        budget_unit="request",
        budget_units=1,
        budget_limit_units=1,
        budget_window_start=NOW,
        budget_window_end=NOW + timedelta(minutes=1),
        payload_schema="ProviderQuotaInputV1@1",
        idempotency_key_digest="f" * 64,
        request_digest="a" * 64,
        requested_at=NOW,
        deadline_at=NOW + timedelta(seconds=30),
    )


def test_claude_quota_maps_only_reported_values_and_preserves_unknowns() -> None:
    """CLA-PURE-005/M05-PURE-004: no missing capacity value is inferred."""
    snapshot = SanitizedClaudeUsageSnapshot(
        windows=(
            SanitizedClaudeUsageWindow(
                window_key="current_session",
                percent_used=Decimal("12.5"),
                reset_display=None,
            ),
            SanitizedClaudeUsageWindow(
                window_key="current_week_all_models",
                percent_used=Decimal("33"),
                reset_display="Resets Sep 25",
            ),
        ),
        observed_at=NOW,
        collected_at=NOW,
    )
    admission = _admission()
    assert admission.account_id is not None and admission.resource_id is not None
    quota = map_subscription_quota(
        snapshot,
        account_ref=admission.account_id,
        resource_ref=admission.resource_id,
    )

    result = map_claude_quota_to_capacity(quota, admission)

    assert result.registry_revision == 7
    assert result.completeness == "complete_scope"
    assert tuple(window.window_key for window in result.windows) == (
        "current_session",
        "current_week_all_models",
    )
    first = result.windows[0]
    assert quota.windows[0].reset_display.value is None
    assert quota.windows[0].reset_display.availability.state == "unknown"
    assert quota.windows[0].reset_display.precision == "unknown"
    assert first.used.value is not None
    assert first.used.value.as_decimal() == Decimal("12.5")
    assert first.used.value.unit == "percent"
    assert first.used.precision == "rounded"
    assert first.remaining.availability.state == "unknown"
    assert first.limit.availability.state == "unknown"
    assert first.remaining_ratio.availability.state == "unknown"
    assert first.reset_at is None
    assert first.reset_precision == "unknown"
