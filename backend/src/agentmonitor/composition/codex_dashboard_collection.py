"""Scheduled quota collection for explicitly enrolled Codex profiles.

Only M02 registry records select targets. Every provider operation uses the
account's private AgentMonitor-managed root and the exact admitted Codex CLI.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.codex.adapter import (
    classify_codex_app_server_failure_v1,
)
from agentmonitor.adapters.providers.codex.installation import (
    CodexInstallationV1,
    discover_default_installation,
)
from agentmonitor.adapters.providers.codex.manifest import (
    CODEX_ADAPTER_VERSION,
    CODEX_RATE_LIMITS_SOURCE_ID,
    build_codex_manifest,
)
from agentmonitor.composition.codex_managed_connection import (
    managed_codex_root_v1,
    managed_identity_matches_account_v1,
)
from agentmonitor.composition.providers import compose_codex_quota_collection
from agentmonitor.contracts.collection_control_v1 import (
    CollectionFailedV1,
    CollectionRunAdmissionV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import VerifiedQuotaIdentityV1
from agentmonitor.contracts.registry_v1 import (
    AccountResourceViewV1,
    AccountViewV1,
    MonitoringProfileViewV1,
)
from agentmonitor.modules.collection_control.application.queries import (
    GetLatestSourceRunV1,
    source_poll_is_due_v1,
)
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)
from agentmonitor.modules.registry.application.accounts import ListAccountsV1
from agentmonitor.modules.registry.application.discovery import (
    ListProviderInstallationsV1,
)


def _digest(*values: str) -> str:
    return hashlib.sha256("\x00".join(values).encode()).hexdigest()


def _quota_minimum_interval_ms() -> int:
    matches = tuple(
        declaration
        for declaration in build_codex_manifest().declarations
        if declaration.capability_id == "subscription.quota"
        and any(
            source.source_id == CODEX_RATE_LIMITS_SOURCE_ID
            for source in declaration.sources
        )
    )
    if len(matches) != 1:
        raise ValueError("codex_quota_manifest_ambiguous")
    minimum_ms = matches[0].constraints.minimum_interval_ms
    if minimum_ms is None:
        raise ValueError("codex_poll_source_interval_unknown")
    return minimum_ms


def _is_transient_failure(code: str | None) -> bool:
    if code is None:
        return False
    # An expired operation is never retried; a new scheduled observation may
    # run after the full cadence, with its own durable admission and deadline.
    if code in {"collection_commit_interrupted", "codex_app_server_deadline_exceeded"}:
        return True
    state, retry = classify_codex_app_server_failure_v1(code)
    return state == "provider_unavailable" and retry.disposition == "after_delay"


def codex_tick_provider_action_v1(
    *, source_poll_due: bool
) -> Literal["none", "durable_collection"]:
    """Allow provider I/O only through a due, durably admitted collection."""
    if type(source_poll_due) is not bool:
        raise TypeError("codex_source_poll_due_invalid")
    return "durable_collection" if source_poll_due else "none"


def _scheduled_admission(
    *,
    account: AccountViewV1,
    profile: MonitoringProfileViewV1,
    resource: AccountResourceViewV1,
    installation: CodexInstallationV1,
    scheduler_instance: OpaqueIdV1,
    schedule_id: OpaqueIdV1,
    requested_at: datetime,
) -> CollectionRunAdmissionV1:
    run_id = "codex-poll-run-" + uuid.uuid4().hex
    request_id = "codex-poll-request-" + uuid.uuid4().hex
    correlation_id = "codex-poll-correlation-" + uuid.uuid4().hex
    target_key = _digest(
        "codex",
        profile.provider_installation_id.value,
        account.account_id.value,
        profile.profile_id.value,
        resource.resource_id.value,
    )
    registry_revision = max(
        account.registry_revision,
        profile.registry_revision,
        resource.registry_revision,
    )
    manifest = build_codex_manifest()
    return CollectionRunAdmissionV1(
        run_id=OpaqueIdV1(run_id),
        schedule_id=schedule_id,
        request_id=OpaqueIdV1(request_id),
        trigger="scheduled",
        operation_family="collect.subscription.quota",
        requested_capability_ids=("subscription.quota",),
        capability_set_version="1.0.0",
        request_auth_method="internal_scheduler",
        request_principal_id=None,
        correlation_id=OpaqueIdV1(correlation_id),
        causation_id=None,
        target_key_digest=target_key,
        provider_key="codex",
        installation_id=profile.provider_installation_id,
        account_id=account.account_id,
        profile_id=profile.profile_id,
        resource_id=resource.resource_id,
        capability_id="subscription.quota",
        source_id=CODEX_RATE_LIMITS_SOURCE_ID,
        adapter_version=CODEX_ADAPTER_VERSION,
        provider_version=installation.provider_version,
        adapter_protocol_version="1.0.0",
        manifest_fingerprint=_digest(
            "provider-manifest-fingerprint-v1",
            get_manifest_fingerprint_v1(manifest),
        ),
        collection_policy_version="1.0.0",
        registry_revision=registry_revision,
        retry_chain_id=OpaqueIdV1("codex-poll-chain-" + uuid.uuid4().hex),
        attempt_ordinal=1,
        target_generation=registry_revision + 1,
        scheduler_instance_id=scheduler_instance,
        lease_policy_version="1.0.0",
        budget_policy_id="codex-scheduled-collection-budget-v1",
        budget_policy_version="1.0.0",
        budget_scope_digest=_digest(
            "codex", account.account_id.value, CODEX_RATE_LIMITS_SOURCE_ID
        ),
        budget_dimension="provider_requests",
        budget_unit="request",
        budget_units=3,
        budget_limit_units=3,
        budget_window_start=requested_at,
        budget_window_end=requested_at + timedelta(minutes=5),
        payload_schema="ProviderQuotaInputV1@1",
        idempotency_key_digest=None,
        request_digest=_digest(request_id, target_key),
        requested_at=requested_at,
        deadline_at=requested_at + timedelta(seconds=60),
    )


class CodexDashboardCollectorV1:
    """Round-robin collector for compatible, identity-bound Codex accounts."""

    def __init__(
        self, reference: DatabaseRefV1, *, managed_profiles_root: Path
    ) -> None:
        if not managed_profiles_root.is_absolute():
            raise ValueError("codex_managed_profiles_root_invalid")
        if (
            managed_profiles_root.name != "codex"
            or managed_profiles_root.parent.name != "profiles"
        ):
            raise ValueError("codex_managed_profiles_root_invalid")
        self._reference = reference
        self._registry = SqliteRegistryRepositoryV1(reference)
        self._collection = SqliteCollectionRepositoryV1(reference)
        self._managed_profiles_root = managed_profiles_root
        self._data_root = managed_profiles_root.parent.parent
        self._instance = OpaqueIdV1("codex-poller-" + uuid.uuid4().hex)
        self._verified_identities: dict[OpaqueIdV1, VerifiedQuotaIdentityV1] = {}
        self._next_target = 0

    def read_verified_identity(
        self, account_id: OpaqueIdV1
    ) -> VerifiedQuotaIdentityV1 | None:
        """Return only a current-process attestation; no receipt is backfilled."""
        return self._verified_identities.get(account_id)

    def _installation_matches_profile(
        self,
        profile: MonitoringProfileViewV1,
        installation: CodexInstallationV1,
    ) -> bool:
        matches = tuple(
            item
            for item in ListProviderInstallationsV1(self._registry)("codex")
            if item.provider_installation_id == profile.provider_installation_id
            and item.presence_state == "present"
            and item.platform_key == installation.platform_id
            and item.version.masked_value == installation.provider_version
        )
        return len(matches) == 1

    def _targets(
        self,
    ) -> tuple[
        tuple[AccountViewV1, MonitoringProfileViewV1, AccountResourceViewV1], ...
    ]:
        query = ListAccountsV1(self._registry)
        as_of = datetime.now(UTC)
        accounts: list[AccountViewV1] = []
        seen_account_ids: set[OpaqueIdV1] = set()
        after_key: str | None = None
        while True:
            page = query.page("codex", as_of=as_of, limit=200, after_key=after_key)
            for account in page.items:
                if account.account_id in seen_account_ids:
                    raise ValueError("codex_registry_scope_incomplete")
                seen_account_ids.add(account.account_id)
                accounts.append(account)
            if not page.has_more:
                break
            if page.next_key is None or page.next_key == after_key:
                raise ValueError("codex_registry_scope_incomplete")
            after_key = page.next_key
        targets: list[
            tuple[AccountViewV1, MonitoringProfileViewV1, AccountResourceViewV1]
        ] = []
        for account in accounts:
            if account.lifecycle != "active" or account.identity_state not in {
                "owner_confirmed",
                "matched",
            }:
                continue
            profiles = self._registry.list_monitoring_profiles(account.account_id)
            resources = self._registry.list_account_resources(account.account_id)
            for profile in profiles:
                if not (
                    profile.lifecycle == "active"
                    and profile.management_state == "managed"
                    and not profile.is_protected_default
                    and profile.locator_state == "configured"
                    and profile.compatibility_state == "compatible"
                    and profile.identity_state
                    in {"owner_confirmed", "provider_verified"}
                    and profile.purpose in {"subscription", "combined"}
                ):
                    continue
                for resource in resources:
                    if (
                        resource.lifecycle == "active"
                        and resource.kind == "subscription_pool"
                        and resource.resource_id in profile.resource_ids
                        and profile.profile_id in resource.linked_profile_ids
                    ):
                        targets.append((account, profile, resource))
        if len({account.account_id for account, _, _ in targets}) != len(targets):
            raise ValueError("codex_account_profile_association_ambiguous")
        return tuple(
            target for target in targets if target[0].is_effective_monitoring_enabled
        )

    def tick(self) -> str:
        targets = self._targets()
        if not targets:
            return "codex_poll_no_enabled_target"
        blocked = False
        for offset in range(len(targets)):
            index = (self._next_target + offset) % len(targets)
            target = targets[index]
            now = datetime.now(UTC)
            latest = GetLatestSourceRunV1(self._collection)(
                "codex",
                "subscription.quota",
                CODEX_RATE_LIMITS_SOURCE_ID,
                now,
                account_id=target[0].account_id,
            )
            minimum_ms = _quota_minimum_interval_ms()
            action = codex_tick_provider_action_v1(
                source_poll_due=source_poll_is_due_v1(
                    now,
                    latest,
                    minimum_ms,
                    transient_read_failure=_is_transient_failure(
                        latest.error_code if latest else None
                    ),
                )
            )
            if action == "durable_collection":
                self._next_target = (index + 1) % len(targets)
                return self._collect_target(target)
            blocked = blocked or bool(
                latest and latest.state not in {"succeeded", "partial"}
            )
        return "codex_poll_blocked" if blocked else "codex_poll_waiting"

    def _collect_target(
        self,
        target: tuple[AccountViewV1, MonitoringProfileViewV1, AccountResourceViewV1],
    ) -> str:
        account, profile, resource = target
        now = datetime.now(UTC)
        latest = GetLatestSourceRunV1(self._collection)(
            "codex",
            "subscription.quota",
            CODEX_RATE_LIMITS_SOURCE_ID,
            now,
            account_id=account.account_id,
        )
        minimum_ms = _quota_minimum_interval_ms()
        if not source_poll_is_due_v1(
            now,
            latest,
            minimum_ms,
            transient_read_failure=_is_transient_failure(
                latest.error_code if latest else None
            ),
        ):
            return (
                "codex_poll_waiting"
                if latest and latest.state in {"succeeded", "partial"}
                else "codex_poll_blocked"
            )
        installation = discover_default_installation()
        if (
            not self._installation_matches_profile(profile, installation)
            or target not in self._targets()
        ):
            return "codex_poll_target_changed"
        root = managed_codex_root_v1(self._data_root, account.account_id)
        key = _digest(
            "codex",
            profile.provider_installation_id.value,
            account.account_id.value,
            profile.profile_id.value,
            resource.resource_id.value,
        )
        schedule_id = (
            latest.schedule_id
            if latest is not None
            and latest.account_id == account.account_id
            and latest.resource_id == resource.resource_id
            else OpaqueIdV1("codex-poll-" + key[:32])
        )
        admission = _scheduled_admission(
            account=account,
            profile=profile,
            resource=resource,
            installation=installation,
            scheduler_instance=self._instance,
            schedule_id=schedule_id,
            requested_at=now,
        )
        route = compose_codex_quota_collection(
            self._reference,
            installation,
            managed_profiles_root=self._managed_profiles_root,
            managed_profile_root=root,
            identity_matches=lambda identity: (
                managed_identity_matches_account_v1(
                    self._registry, account.account_id, identity
                )
                and target in self._targets()
            ),
            installation_ref=profile.provider_installation_id,
            account_ref=account.account_id,
            profile_ref=profile.profile_id,
            resource_ref=resource.resource_id,
            access_grant_ref=OpaqueIdV1("codex-managed-profile-auth-maintenance"),
        )
        request = route.adapter.subscription_request(
            operation_id=admission.run_id.value,
            correlation_id=admission.correlation_id.value,
            requested_at=now,
        )
        result = route.collect_once(
            admission,
            request,
            started_at=datetime.now(UTC),
            completed_at=lambda: datetime.now(UTC),
        )
        after = route.adapter.take_verified_identity(
            operation_id=admission.run_id,
            correlation_id=admission.correlation_id,
        )
        identity_is_stable = (
            after is not None
            and managed_identity_matches_account_v1(
                self._registry, account.account_id, after
            )
            and target in self._targets()
        )
        if not isinstance(result, CollectionFailedV1) and identity_is_stable:
            assert after is not None
            self._verified_identities[account.account_id] = VerifiedQuotaIdentityV1(
                account.account_id, admission.run_id, after, "managed"
            )
        else:
            self._verified_identities.pop(account.account_id, None)
        return (
            "codex_poll_failed"
            if isinstance(result, CollectionFailedV1)
            else "codex_poll_collected"
        )

    async def run(self) -> None:
        previous = None
        while True:
            work = asyncio.create_task(asyncio.to_thread(self.tick))
            try:
                status = await asyncio.shield(work)
            except asyncio.CancelledError:
                await work
                raise
            except (OSError, RuntimeError, ValueError):
                status = "codex_poll_unavailable"
            if status != previous:
                print(json.dumps({"event": status}), flush=True)
                previous = status
            await asyncio.sleep(1)
