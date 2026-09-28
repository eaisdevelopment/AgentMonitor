"""Service-owned polling of enrolled read-only Claude profiles.

Account names, organizations, and opaque target IDs are read from M02. No
enrollment, agent-account inference, authentication, or provider-state write occurs.
"""

import asyncio
import hashlib
import json
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.claude.authentication.identity import (
    read_default_profile_identity_v1,
)
from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)
from agentmonitor.adapters.providers.claude.manifest import (
    CLAUDE_ADAPTER_VERSION,
    CLAUDE_USAGE_SOURCE_ID,
    build_claude_manifest,
)
from agentmonitor.adapters.providers.claude.subscription.source import (
    is_transient_claude_usage_failure_v1,
)
from agentmonitor.composition.claude_live_monitoring import (
    build_owner_operator_quota_admission_v1,
    collection_manifest_digest_v1,
)
from agentmonitor.composition.claude_managed_connection import (
    managed_identity_matches_account_v1,
)
from agentmonitor.composition.providers import compose_claude_quota_collection
from agentmonitor.contracts.collection_control_v1 import CollectionFailedV1
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
from agentmonitor.modules.collection_control.application.runner import (
    AdmitScheduledCollectionV1,
)
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)
from agentmonitor.modules.registry.application.accounts import ListAccountsV1


def _digest(*values: str) -> str:
    return hashlib.sha256("\x00".join(values).encode()).hexdigest()


class ClaudeDashboardCollectorV1:
    def __init__(
        self, reference: DatabaseRefV1, *, managed_profiles_root: Path | None = None
    ) -> None:
        self._reference = reference
        self._registry = SqliteRegistryRepositoryV1(reference)
        self._collection = SqliteCollectionRepositoryV1(reference)
        self._instance = OpaqueIdV1("claude-poller-" + uuid.uuid4().hex)
        # Only the current successful run is attested. No persistence/backfill.
        self._verified_identities: dict[OpaqueIdV1, VerifiedQuotaIdentityV1] = {}
        self._managed_profiles_root = managed_profiles_root
        self._next_target = 0

    def read_verified_identity(
        self, account_id: OpaqueIdV1
    ) -> VerifiedQuotaIdentityV1 | None:
        return self._verified_identities.get(account_id)

    def _targets(
        self,
    ) -> tuple[
        tuple[AccountViewV1, MonitoringProfileViewV1, AccountResourceViewV1], ...
    ]:
        page = ListAccountsV1(self._registry).page(
            "claude", as_of=datetime.now(UTC), limit=200
        )
        if page.has_more:
            raise ValueError("claude_registry_scope_incomplete")
        targets = []
        for account in page.items:
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
                    and (
                        (
                            profile.management_state == "provider_default"
                            and profile.is_protected_default
                        )
                        or (
                            self._managed_profiles_root is not None
                            and profile.management_state == "managed"
                            and not profile.is_protected_default
                            and profile.locator_state == "configured"
                        )
                    )
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
        if sum(profile.is_protected_default for _, profile, _ in targets) > 1:
            raise ValueError("claude_default_profile_association_ambiguous")
        if len({account.account_id for account, _, _ in targets}) != len(targets):
            raise ValueError("claude_account_profile_association_ambiguous")
        return tuple(
            target for target in targets if target[0].is_effective_monitoring_enabled
        )

    def tick(self) -> str:
        targets = self._targets()
        if not targets:
            return "claude_poll_no_enabled_target"
        blocked = False
        for offset in range(len(targets)):
            index = (self._next_target + offset) % len(targets)
            target = targets[index]
            latest = GetLatestSourceRunV1(self._collection)(
                "claude",
                "subscription.quota",
                CLAUDE_USAGE_SOURCE_ID,
                datetime.now(UTC),
                account_id=target[0].account_id,
            )
            minimum_ms = (
                build_claude_manifest().declarations[0].constraints.minimum_interval_ms
            )
            if minimum_ms is None:
                raise ValueError("claude_poll_source_interval_unknown")
            if source_poll_is_due_v1(
                datetime.now(UTC),
                latest,
                minimum_ms,
                transient_read_failure=is_transient_claude_usage_failure_v1(
                    latest.error_code if latest else None
                ),
            ):
                self._next_target = (index + 1) % len(targets)
                return self._collect_target(target)
            blocked = blocked or bool(
                latest and latest.state not in {"succeeded", "partial"}
            )
        return "claude_poll_blocked" if blocked else "claude_poll_waiting"

    def _collect_target(
        self,
        target: tuple[AccountViewV1, MonitoringProfileViewV1, AccountResourceViewV1],
    ) -> str:
        account, profile, resource = target
        now = datetime.now(UTC)
        latest = GetLatestSourceRunV1(self._collection)(
            "claude",
            "subscription.quota",
            CLAUDE_USAGE_SOURCE_ID,
            now,
            account_id=account.account_id,
        )
        manifest = build_claude_manifest()
        minimum_ms = manifest.declarations[0].constraints.minimum_interval_ms
        if minimum_ms is None:
            raise ValueError("claude_poll_source_interval_unknown")
        if not source_poll_is_due_v1(
            now,
            latest,
            minimum_ms,
            transient_read_failure=is_transient_claude_usage_failure_v1(
                latest.error_code if latest else None
            ),
        ):
            return (
                "claude_poll_waiting"
                if latest and latest.state in {"succeeded", "partial"}
                else "claude_poll_blocked"
            )
        installation = discover_default_installation()
        # Read eligibility again immediately before admission/provider dispatch.
        if target not in self._targets():
            return "claude_poll_target_changed"
        managed_root = None
        if profile.management_state == "managed":
            if self._managed_profiles_root is None:
                raise ValueError("claude_managed_root_unavailable")
            managed_root = (
                self._managed_profiles_root
                / hashlib.sha256(account.account_id.value.encode()).hexdigest()
            )
        before = read_default_profile_identity_v1(
            installation, managed_profile_root=managed_root
        )
        self._verified_identities.pop(account.account_id, None)
        if managed_root is not None and (
            before is None
            or not managed_identity_matches_account_v1(
                self._registry, account.account_id, before
            )
        ):
            return "claude_poll_managed_identity_blocked"
        key = _digest(
            "claude",
            profile.provider_installation_id.value,
            account.account_id.value,
            profile.profile_id.value,
            resource.resource_id.value,
        )
        run_id = "claude-poll-run-" + uuid.uuid4().hex
        request_id = "claude-poll-request-" + uuid.uuid4().hex
        correlation_id = "claude-poll-correlation-" + uuid.uuid4().hex
        admission = build_owner_operator_quota_admission_v1(
            run_id=run_id,
            request_id=request_id,
            correlation_id=correlation_id,
            causation_id=request_id,
            retry_chain_id="claude-poll-chain-" + uuid.uuid4().hex,
            installation_id=profile.provider_installation_id,
            account_id=account.account_id,
            profile_id=profile.profile_id,
            resource_id=resource.resource_id,
            registry_revision=max(
                account.registry_revision,
                profile.registry_revision,
                resource.registry_revision,
            ),
            source_id=CLAUDE_USAGE_SOURCE_ID,
            adapter_version=CLAUDE_ADAPTER_VERSION,
            provider_version=installation.provider_version,
            manifest_fingerprint=collection_manifest_digest_v1(
                get_manifest_fingerprint_v1(manifest)
            ),
            target_key_digest=key,
            budget_scope_digest=_digest(
                "claude", account.account_id.value, CLAUDE_USAGE_SOURCE_ID
            ),
            idempotency_key_digest=_digest(request_id),
            request_digest=_digest(request_id, key),
            requested_at=now,
        )
        schedule_id = (
            latest.schedule_id
            if (
                latest is not None
                and latest.account_id == account.account_id
                and latest.resource_id == resource.resource_id
            )
            else OpaqueIdV1("claude-poll-" + key[:32])
        )
        admission = replace(
            admission,
            schedule_id=schedule_id,
            trigger="scheduled",
            request_auth_method="internal_scheduler",
            request_principal_id=None,
            causation_id=None,
            idempotency_key_digest=None,
            scheduler_instance_id=self._instance,
        )
        route = compose_claude_quota_collection(
            self._reference,
            installation,
            managed_profile_root=managed_root,
            expected_identity_fingerprint=before.fingerprint if before else None,
        )
        AdmitScheduledCollectionV1(self._collection)(admission)
        request = route.adapter.subscription_request(
            operation_id=run_id,
            correlation_id=correlation_id,
            installation_ref=profile.provider_installation_id.value,
            account_ref=account.account_id.value,
            profile_ref=profile.profile_id.value,
            resource_ref=resource.resource_id.value,
            requested_at=now,
        )
        # Leave time for provider cleanup inside the service's 30s shutdown drain.
        # Managed reads include four bounded identity checks (3s each).
        request = replace(request, deadline_ms=14_000 if managed_root else 20_000)
        result = route.collect_once(
            admission,
            request,
            started_at=datetime.now(UTC),
            completed_at=lambda: datetime.now(UTC),
        )
        after = read_default_profile_identity_v1(
            installation, managed_profile_root=managed_root
        )
        if (
            not isinstance(result, CollectionFailedV1)
            and before is not None
            and after is not None
            and before.fingerprint == after.fingerprint
            and (
                managed_root is None
                or managed_identity_matches_account_v1(
                    self._registry, account.account_id, after
                )
            )
        ):
            self._verified_identities[account.account_id] = VerifiedQuotaIdentityV1(
                account.account_id,
                OpaqueIdV1(run_id),
                after,
                "managed" if managed_root is not None else "protected_default",
            )
        return (
            "claude_poll_failed"
            if isinstance(result, CollectionFailedV1)
            else "claude_poll_collected"
        )

    async def run(self) -> None:
        previous = None
        while True:
            work = asyncio.create_task(asyncio.to_thread(self.tick))
            try:
                status = await asyncio.shield(work)
            except asyncio.CancelledError:
                # Do not abandon the bounded read or close SQLite underneath it.
                await work
                raise
            except (OSError, RuntimeError, ValueError):
                status = "claude_poll_unavailable"
            if status != previous:
                print(json.dumps({"event": status}), flush=True)
                previous = status
            await asyncio.sleep(5)
