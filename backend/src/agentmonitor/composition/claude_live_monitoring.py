"""One owner-confirmed Claude discovery, registry, and quota collection flow.

This composition reads only the approved default Claude profile through A01.
It never discovers or persists provider identity, credentials, prompts, responses,
or source content. The opaque target tuple is an explicit owner confirmation.
"""

from __future__ import annotations

import hashlib
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.claude.adapter import ClaudeAdapterV1
from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)
from agentmonitor.adapters.providers.claude.manifest import (
    CLAUDE_ADAPTER_VERSION,
    CLAUDE_USAGE_SOURCE_ID,
    build_claude_manifest,
)
from agentmonitor.composition.providers import compose_claude_quota_collection
from agentmonitor.contracts.capacity_v1 import (
    AccountCapacityViewV1,
    CapacityCommitReceiptV1,
    QuotaWindowViewV1,
)
from agentmonitor.contracts.collection_control_v1 import (
    CollectionFailedV1,
    CollectionRunAdmissionV1,
    CollectionRunViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)
from agentmonitor.modules.registry.application.owner_enrollment import (
    EnrollOwnerConfirmedDiscoveryV1,
    OwnerConfirmedMonitoringGraphV1,
)

# These are owner-assigned opaque aliases, never provider-discovered identity.
OWNER_ACCOUNT_REF = "claude-account-owner-confirmed"
OWNER_PROFILE_REF = "claude-profile-default-read-only"
OWNER_RESOURCE_REF = "claude-subscription-current"
OWNER_PRINCIPAL_ID = "agentmonitor-owner"
_MINIMUM_SOURCE_INTERVAL = timedelta(milliseconds=300_000)
# Increment only when the reviewed quota source ID, manifest fingerprint, or
# collection policy changes. Adapter/provider compatibility is bound by the
# manifest; this generation is independent from M02's registry watermark.
_COLLECTION_POLICY_GENERATION = 1


class ClaudeLiveMonitoringErrorV1(RuntimeError):
    """Bounded live-composition failure with no provider data."""


@dataclass(frozen=True, slots=True)
class ClaudeLiveMonitoringResultV1:
    """Safe receipts and projections from one real vertical execution."""

    discovery_state: str
    discovered_account_count: int
    discovery_owner_confirmation_required: bool
    discovery_evidence_strength: str
    graph: OwnerConfirmedMonitoringGraphV1
    queued_run: CollectionRunViewV1
    completed_run: CollectionRunViewV1
    capacity_receipt: CapacityCommitReceiptV1
    capacities: tuple[AccountCapacityViewV1, ...]
    quota_windows: tuple[QuotaWindowViewV1, ...]
    discovery_collected_at: datetime
    collection_started_at: datetime


def _digest(*values: str) -> str:
    return hashlib.sha256("\x00".join(values).encode("utf-8")).hexdigest()


def collection_manifest_digest_v1(provider_manifest_fingerprint: str) -> str:
    """Bind an M03 catalog fingerprint to M04's SHA-256 audit field."""
    return _digest("provider-manifest-fingerprint-v1", provider_manifest_fingerprint)


def _operation_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def build_owner_operator_quota_admission_v1(
    *,
    run_id: str,
    request_id: str,
    correlation_id: str,
    causation_id: str,
    retry_chain_id: str,
    installation_id: OpaqueIdV1,
    account_id: OpaqueIdV1,
    profile_id: OpaqueIdV1,
    resource_id: OpaqueIdV1,
    registry_revision: int,
    source_id: str,
    adapter_version: str,
    provider_version: str,
    manifest_fingerprint: str,
    target_key_digest: str,
    budget_scope_digest: str,
    idempotency_key_digest: str,
    request_digest: str,
    requested_at: datetime,
) -> CollectionRunAdmissionV1:
    """Assemble the Claude-local operator admission at composition scope."""
    return CollectionRunAdmissionV1(
        run_id=OpaqueIdV1(run_id),
        schedule_id=OpaqueIdV1("claude-owner-manual-schedule"),
        request_id=OpaqueIdV1(request_id),
        trigger="manual",
        operation_family="collect.subscription.quota",
        requested_capability_ids=("subscription.quota",),
        capability_set_version="1.0.0",
        request_auth_method="owner_local_operator",
        request_principal_id=OpaqueIdV1(OWNER_PRINCIPAL_ID),
        correlation_id=OpaqueIdV1(correlation_id),
        causation_id=OpaqueIdV1(causation_id),
        target_key_digest=target_key_digest,
        provider_key="claude",
        installation_id=installation_id,
        account_id=account_id,
        profile_id=profile_id,
        resource_id=resource_id,
        capability_id="subscription.quota",
        source_id=source_id,
        adapter_version=adapter_version,
        provider_version=provider_version,
        adapter_protocol_version="1.0.0",
        manifest_fingerprint=manifest_fingerprint,
        collection_policy_version="1.0.0",
        registry_revision=registry_revision,
        retry_chain_id=OpaqueIdV1(retry_chain_id),
        attempt_ordinal=1,
        target_generation=registry_revision + _COLLECTION_POLICY_GENERATION,
        scheduler_instance_id=OpaqueIdV1("agentmonitor-local-manual"),
        lease_policy_version="1.0.0",
        budget_policy_id="claude-source-minimum-interval-v1",
        budget_policy_version="1.0.0",
        budget_scope_digest=budget_scope_digest,
        budget_dimension="provider_requests",
        budget_unit="request",
        budget_units=1,
        budget_limit_units=1,
        budget_window_start=requested_at,
        budget_window_end=requested_at + _MINIMUM_SOURCE_INTERVAL,
        payload_schema="ProviderQuotaInputV1@1",
        idempotency_key_digest=idempotency_key_digest,
        request_digest=request_digest,
        requested_at=requested_at,
        deadline_at=requested_at + timedelta(seconds=45),
    )


def _wait_for_source_interval(
    collected_at: datetime, status: Callable[[str], None] | None
) -> None:
    not_before = collected_at + _MINIMUM_SOURCE_INTERVAL
    announced = False
    while True:
        remaining = (not_before - datetime.now(UTC)).total_seconds()
        if remaining <= 0:
            return
        if status is not None and not announced:
            status("claude_source_interval_waiting")
            announced = True
        time.sleep(min(remaining, 30.0))


def run_owner_confirmed_claude_collection(
    reference: DatabaseRefV1,
    *,
    status: Callable[[str], None] | None = None,
) -> ClaudeLiveMonitoringResultV1:
    """Persist one real owner-confirmed Claude account and quota observation."""
    installation = discover_default_installation()
    adapter = ClaudeAdapterV1(installation)
    registry = SqliteRegistryRepositoryV1(reference)
    correlation_id = _operation_id("claude-live-correlation")
    discovery_operation_id = _operation_id("claude-live-discovery")
    discovery = adapter.discover_owner_confirmed_default(
        operation_id=discovery_operation_id,
        correlation_id=correlation_id,
        account_ref=OWNER_ACCOUNT_REF,
        profile_ref=OWNER_PROFILE_REF,
        resource_ref=OWNER_RESOURCE_REF,
    )
    if (
        discovery.state not in {"success", "partial"}
        or discovery.value is None
        or discovery.provenance is None
        or len(discovery.value.accounts) != 1
        or not discovery.value.accounts[0].owner_confirmation_required
    ):
        code = discovery.error.code if discovery.error is not None else "invalid"
        raise ClaudeLiveMonitoringErrorV1(f"claude_discovery_{code}")

    graph = EnrollOwnerConfirmedDiscoveryV1(registry)(
        discovery,
        reconciled_at=datetime.now(UTC),
        command_id=_operation_id("claude-owner-confirmation"),
        principal_id=OWNER_PRINCIPAL_ID,
        expected_provider_key="claude",
        friendly_name="Claude owner account",
        profile_locator=OWNER_PROFILE_REF,
        enrollment_command_id="claude-owner-default-enrollment-v1",
    )

    _wait_for_source_interval(discovery.provenance.collected_at, status)
    requested_at = datetime.now(UTC)
    run_id = _operation_id("claude-quota-run")
    request_id = _operation_id("claude-quota-request")
    admission = build_owner_operator_quota_admission_v1(
        run_id=run_id,
        request_id=request_id,
        correlation_id=correlation_id,
        causation_id=discovery_operation_id,
        retry_chain_id=_operation_id("claude-quota-retry-chain"),
        installation_id=(graph.candidate_before_confirmation.provider_installation_id),
        account_id=graph.account.account_id,
        profile_id=graph.profile.profile_id,
        resource_id=graph.resource.resource_id,
        registry_revision=max(
            graph.account.registry_revision,
            graph.profile.registry_revision,
            graph.resource.registry_revision,
        ),
        source_id=CLAUDE_USAGE_SOURCE_ID,
        adapter_version=CLAUDE_ADAPTER_VERSION,
        provider_version=installation.provider_version,
        manifest_fingerprint=collection_manifest_digest_v1(
            get_manifest_fingerprint_v1(build_claude_manifest())
        ),
        target_key_digest=_digest(
            "claude",
            graph.candidate_before_confirmation.provider_installation_id.value,
            graph.account.account_id.value,
            graph.profile.profile_id.value,
            graph.resource.resource_id.value,
        ),
        budget_scope_digest=_digest(
            "claude", graph.account.account_id.value, CLAUDE_USAGE_SOURCE_ID
        ),
        idempotency_key_digest=_digest(request_id),
        request_digest=_digest(
            request_id,
            graph.account.account_id.value,
            graph.resource.resource_id.value,
            "subscription.quota",
        ),
        requested_at=requested_at,
    )
    route = compose_claude_quota_collection(reference, installation)
    queued = route.request_manual(admission)
    collection_started_at = datetime.now(UTC)
    provider_request = adapter.subscription_request(
        operation_id=run_id,
        correlation_id=correlation_id,
        installation_ref=graph.candidate_before_confirmation.provider_installation_id.value,
        account_ref=graph.account.account_id.value,
        profile_ref=graph.profile.profile_id.value,
        resource_ref=graph.resource.resource_id.value,
        requested_at=requested_at,
    )
    result = route.collect_once(
        admission,
        provider_request,
        started_at=collection_started_at,
        completed_at=lambda: datetime.now(UTC),
    )
    if isinstance(result, CollectionFailedV1):
        raise ClaudeLiveMonitoringErrorV1(f"claude_collection_{result.error_code}")
    completed = SqliteCollectionRepositoryV1(reference).get_run(admission.run_id)
    as_of = datetime.now(UTC)
    capacities = route.get_account_capacity(graph.account.account_id, as_of=as_of).items
    windows = route.list_quota_windows(graph.account.account_id, as_of=as_of)
    if not capacities or not windows:
        raise ClaudeLiveMonitoringErrorV1("claude_capacity_projection_missing")
    return ClaudeLiveMonitoringResultV1(
        discovery_state=discovery.state,
        discovered_account_count=len(discovery.value.accounts),
        discovery_owner_confirmation_required=(
            discovery.value.accounts[0].owner_confirmation_required
        ),
        discovery_evidence_strength=discovery.value.accounts[0].evidence_strength,
        graph=graph,
        queued_run=queued,
        completed_run=completed,
        capacity_receipt=result,
        capacities=capacities,
        quota_windows=windows,
        discovery_collected_at=discovery.provenance.collected_at,
        collection_started_at=collection_started_at,
    )


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 2 or arguments[0] != "--data-root":
        print("invalid_operator_arguments")
        return 2
    root = Path(arguments[1])
    if not root.is_absolute():
        print("claude_live_collection_refused")
        return 2
    try:
        result = run_owner_confirmed_claude_collection(
            DatabaseRefV1(root / "agentmonitor.db", root),
            status=lambda code: print(code, flush=True),
        )
    except (OSError, RuntimeError, ValueError):
        print("claude_live_collection_failed")
        return 1
    print("claude_live_collection_completed")
    print(f"account_id={result.graph.account.account_id.value}")
    print(f"collection_run_id={result.completed_run.run_id.value}")
    print(f"quota_window_count={len(result.quota_windows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
