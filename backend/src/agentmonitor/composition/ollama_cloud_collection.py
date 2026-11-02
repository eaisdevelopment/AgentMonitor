"""Unwired cloud collection primitives; no service scheduler is enabled."""

# ruff: noqa: E501 -- the canonical M04 import path is intentionally explicit.

import hashlib
import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.ollama_cloud_admission import (
    SqliteOllamaCloudAdmissionRepositoryV1,
    SqliteOllamaCloudRunRepositoryV1,
    SqliteOllamaNoResponseRunRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.collection import (
    admission_outcome_for_source,
    cloud_balance_to_capacity,
    cloud_failure_policy,
    eligible_cloud_account,
    validate_cloud_target,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.freshness import (
    cloud_freshness_deadline_v1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
    CLOUD_BALANCE_POLICY_V1,
    CloudBalanceSourceResultV1,
    read_cloud_balance_for_binding_v1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.verification_run import (
    build_verification_run,
    source_budget_seconds,
)
from agentmonitor.adapters.providers.ollama.manifest import (
    OLLAMA_ADAPTER_ID,
    OLLAMA_ADAPTER_VERSION,
    build_ollama_manifest,
)
from agentmonitor.composition.ollama_capacity_commit import ollama_capacity_repository
from agentmonitor.contracts.capacity_v1 import (
    CapacityCommitRequestV1,
    CapacityCommitRequestV2,
    CapacitySubjectV1,
    CapacitySubjectV2,
    ProviderQuotaInputV2,
)
from agentmonitor.contracts.collection_control_v1 import (
    CollectionFailedV1,
    CollectionRunAdmissionV1,
    CollectionRunAdmissionV2,
    OllamaCloudAdmissionDecisionV1,
    OllamaCloudNoResponseCompletionV2,
    OllamaCloudRequestAcquireV1,
    OllamaCloudRequestCompletionV1,
    OllamaCloudRequestLeaseV1,
    OllamaCloudVerificationAcquireV1,
    OllamaCloudVerificationClaimRequestV1,
    OllamaCloudVerificationClaimTerminalV1,
)
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    ProviderTargetRefV1,
)
from agentmonitor.modules.capacity.domain.payload_digest import capacity_payload_digest
from agentmonitor.modules.collection_control.application.executor import (
    ExecuteCollectionRunV1,
)
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)
from agentmonitor.modules.registry.domain.credential_binding import (
    resolve_active_credential_binding,
)


class OllamaCloudTargetIneligible(ValueError):
    """Known target is not currently eligible for cloud monitoring."""


def require_source_admitted() -> None:
    """Never schedule provider I/O without all approved source bounds."""
    policy = CLOUD_BALANCE_POLICY_V1
    if not (
        policy.authenticated_collection_admitted
        and policy.wire_header_limit_strict
        and policy.binding_worker_process_isolated
        and policy.binding_worker_deadline_strict
        and policy.binding_worker_authenticated_validated
    ):
        raise ValueError("ollama_cloud_source_not_admitted")


def require_cloud_manifest():
    """Do not misrepresent a local-only manifest as cloud admission."""
    manifest = build_ollama_manifest()
    matches = [
        declaration
        for declaration in manifest.declarations
        if declaration.capability_id == "subscription.quota"
        and declaration.decision == "supported"
        and any(
            source.source_id == "ollama.cloud.balance.v1"
            and source.source_class == "documented_api"
            for source in declaration.sources
        )
    ]
    if len(matches) != 1:
        raise ValueError("ollama_cloud_manifest_not_admitted")
    return manifest


def _digest(*values: str) -> str:
    return hashlib.sha256("\0".join(values).encode()).hexdigest()


class OllamaCloudCollectionV1:
    """Acquire the durable fair gate and commit only fully fenced observations.

    This object is deliberately not registered in the service; acquisition and
    dispatch remain disabled until the actual source and manifest are admitted.
    """

    def __init__(self, reference: DatabaseRefV1) -> None:
        self._reference = reference
        self._admission = SqliteOllamaCloudAdmissionRepositoryV1(reference)
        self._runs = SqliteCollectionRepositoryV1(reference)
        self._registry = SqliteRegistryRepositoryV1(reference)
        self._bindings = SqliteCredentialBindingsV1(reference)
        self._cloud_registry = SqliteCloudCredentialRegistryV1(reference)
        self._instance = OpaqueIdV1("ollama-cloud-" + uuid.uuid4().hex)

    def _monitored_cloud_account_count(
        self, run: CollectionRunAdmissionV1 | CollectionRunAdmissionV2
    ) -> int | None:
        """Count a revision-stable scope; unknown remains unknown on any failure."""
        if run.account_id is None:
            return None
        try:
            current = self._registry.get_account(run.account_id)
            if current is None or current.registry_revision != run.registry_revision:
                return None
            cursor = None
            scanned = 0
            monitored = 0
            while True:
                page = self._registry.list_accounts(
                    provider_key="ollama", page_size=100, after_key=cursor
                )
                scanned += len(page)
                if scanned > 1000 or any(
                    item.registry_revision != run.registry_revision for item in page
                ):
                    return None
                monitored += sum(
                    item.lifecycle == "active" and item.is_effective_monitoring_enabled
                    for item in page
                )
                if len(page) < 100:
                    break
                if scanned >= 1000:
                    return None
                cursor = page[-1].account_id.value
            latest = self._registry.get_account(run.account_id)
            if latest is None or latest.registry_revision != run.registry_revision:
                return None
            # The current one-shot verification is one real cloud participant
            # even before normal monitoring is enabled.
            if not current.is_effective_monitoring_enabled:
                monitored += 1
            return monitored if monitored > 0 else None
        except (OSError, RuntimeError, ValueError):
            return None

    def _source_provenance(
        self,
        run: CollectionRunAdmissionV1 | CollectionRunAdmissionV2,
        source: CloudBalanceSourceResultV1,
    ) -> ObservationProvenanceV1:
        manifest = require_cloud_manifest()
        declaration = next(
            item
            for item in manifest.declarations
            if item.capability_id == "subscription.quota"
        )
        native = next(
            item for item in declaration.sources if item.source_id == source.source_id
        )
        deadline = cloud_freshness_deadline_v1(
            source.observed_at, self._monitored_cloud_account_count(run)
        )
        return ObservationProvenanceV1(
            provider_key="ollama",
            capability_id="subscription.quota",
            capability_schema_version="1.0.0",
            adapter_id=OLLAMA_ADAPTER_ID,
            adapter_version=OLLAMA_ADAPTER_VERSION,
            provider_protocol_version="1.0.0",
            source_id=source.source_id,
            source_class=native.source_class,
            mechanism_version=native.mechanism_version,
            parser_version=None,
            provider_version=None,
            provider_version_availability=FieldAvailabilityV1("unknown"),
            observed_at=source.observed_at,
            observed_at_availability=FieldAvailabilityV1("available"),
            collected_at=datetime.now(UTC),
            freshness_deadline=deadline,
            freshness_availability=FieldAvailabilityV1(
                "available" if deadline is not None else "unknown"
            ),
            freshness_policy_id="agentmonitor-ollama-round-robin-freshness-v1",
            precision="exact",
            confidence="confirmed",
            confidence_reason_code="provider_reported_balance",
            value_kind="provider_reported",
            is_experimental=False,
            fallback_lineage=(),
            warnings=(),
            operation_id=run.run_id,
            correlation_id=run.correlation_id,
            decision_reference=manifest.m0_mapping_id,
            derivation_method=None,
            input_observation_ids=(),
        )

    def prepare_run(
        self, account, profile, resource, now: datetime
    ) -> CollectionRunAdmissionV1:
        """Derive one run from existing M02 account, profile and resource views."""
        require_source_admitted()
        manifest = require_cloud_manifest()
        if (
            not eligible_cloud_account(
                account.provider_key,
                account.lifecycle,
                account.is_effective_monitoring_enabled,
                account.identity_state,
            )
            or account.account_id != profile.account_id
            or account.account_id != resource.account_id
        ):
            raise OllamaCloudTargetIneligible("ollama_cloud_target_ineligible")
        target = _digest(
            "ollama",
            profile.provider_installation_id.value,
            account.account_id.value,
            profile.profile_id.value,
            resource.resource_id.value,
        )
        run_id = "ollama-cloud-run-" + uuid.uuid4().hex
        request_id = "ollama-cloud-request-" + uuid.uuid4().hex
        revision = max(
            account.registry_revision,
            profile.registry_revision,
            resource.registry_revision,
        )
        result = CollectionRunAdmissionV1(
            run_id=OpaqueIdV1(run_id),
            schedule_id=OpaqueIdV1("ollama-cloud-" + target[:32]),
            request_id=OpaqueIdV1(request_id),
            trigger="scheduled",
            operation_family="collect.subscription.quota",
            requested_capability_ids=("subscription.quota",),
            capability_set_version="1.0.0",
            request_auth_method="internal_scheduler",
            request_principal_id=None,
            correlation_id=OpaqueIdV1("ollama-cloud-correlation-" + uuid.uuid4().hex),
            causation_id=None,
            target_key_digest=target,
            provider_key="ollama",
            installation_id=profile.provider_installation_id,
            account_id=account.account_id,
            profile_id=profile.profile_id,
            resource_id=resource.resource_id,
            capability_id="subscription.quota",
            source_id="ollama.cloud.balance.v1",
            adapter_version=OLLAMA_ADAPTER_VERSION,
            provider_version=None,
            adapter_protocol_version="1.0.0",
            manifest_fingerprint=_digest(
                "provider-manifest-fingerprint-v1",
                get_manifest_fingerprint_v1(manifest),
            ),
            collection_policy_version="1.0.0",
            registry_revision=revision,
            retry_chain_id=OpaqueIdV1("ollama-cloud-chain-" + uuid.uuid4().hex),
            attempt_ordinal=1,
            target_generation=revision + 1,
            scheduler_instance_id=self._instance,
            lease_policy_version="1.0.0",
            budget_policy_id="ollama-cloud-scheduled-v1",
            budget_policy_version="1.0.0",
            budget_scope_digest=_digest("ollama-cloud-global"),
            budget_dimension="provider_requests",
            budget_unit="request",
            budget_units=1,
            budget_limit_units=1,
            budget_window_start=now,
            budget_window_end=now + timedelta(seconds=60),
            payload_schema="ProviderQuotaInputV1@1",
            idempotency_key_digest=None,
            request_digest=_digest(request_id, target),
            requested_at=now,
            deadline_at=now + timedelta(seconds=45),
        )
        self._eligible_binding(result)
        return result

    def verification_tick(self):
        """Progress at most one queued owner request under the existing M04 gate.

        This candidate is not registered with the service. The source and
        manifest admission checks happen before a job can be claimed.
        """
        require_source_admitted()
        manifest = require_cloud_manifest()
        now = datetime.now(UTC)
        claim = self._admission.claim_verification(
            OllamaCloudVerificationClaimRequestV1(
                self._instance, now, now + timedelta(seconds=45)
            )
        )
        if claim is None:
            return "no_candidate"
        graph = self._cloud_registry.read_monitoring_target(claim.account_id)
        account = self._registry.get_account(claim.account_id)
        binding = resolve_active_credential_binding(
            self._bindings.read(claim.account_id)
        )
        if (
            graph is None
            or account is None
            or binding is None
            or graph.binding != binding
            or graph.access_target_id != claim.access_target_id
            or graph.lifecycle != "active"
            or graph.identity_state != "owner_confirmed"
            or binding.generation != claim.binding_generation
            or account.lifecycle != "active"
            or account.provider_key != "ollama"
        ):
            finished = datetime.now(UTC)
            self._admission.finish_verification_claim(
                OllamaCloudVerificationClaimTerminalV1(
                    claim.job_id,
                    claim.worker_instance_id,
                    claim.fencing_token,
                    claim.claimed_at,
                    claim.claim_expires_at,
                    finished,
                    "target_unavailable",
                )
            )
            return "target_unavailable"
        now = datetime.now(UTC)
        decision = self._admission.acquire_claimed_verification(
            claim,
            OllamaCloudVerificationAcquireV1(
                OpaqueIdV1("ollama-cloud-attempt-" + uuid.uuid4().hex),
                claim.worker_instance_id,
                claim.schedule_id,
                claim.account_id,
                claim.binding_generation,
                now,
                now + timedelta(seconds=30),
                secrets.randbelow(11),
            ),
        )
        if decision.lease is None:
            return decision.state
        lease = decision.lease
        run = None
        try:
            run = build_verification_run(
                claim,
                graph,
                lease,
                account.registry_revision,
                _digest(
                    "provider-manifest-fingerprint-v1",
                    get_manifest_fingerprint_v1(manifest),
                ),
                datetime.now(UTC),
            )
            subject = CapacitySubjectV2(
                "ollama",
                ProviderTargetRefV1("cloud_service", graph.access_target_id),
                graph.account_id,
                graph.resource_id,
            )
            return self.execute_admitted(lease, run, subject)
        except BaseException:
            # Only a reservation proven not dispatched can be released here.
            try:
                recovered = self._admission.recover_rate_gate(
                    datetime.now(UTC), expected=lease, reserved_only=True
                )
                if recovered == "recovered" and run is not None:
                    current = self._runs.get_run(run.run_id)
                    failure = CollectionFailedV1(
                        run.run_id,
                        "failed",
                        "ollama_cloud_pre_dispatch_failed",
                        datetime.now(UTC),
                    )
                    finalizer = SqliteOllamaNoResponseRunRepositoryV1(
                        self._reference, lease.admission_id
                    )
                    if current.state == "queued":
                        finalizer.finalize_before_dispatch(
                            failure, fencing_token=current.fencing_token
                        )
                    elif current.state == "running":
                        finalizer.finalize_failed(
                            failure, fencing_token=current.fencing_token
                        )
            except (OSError, RuntimeError, ValueError):
                pass
            raise

    def tick(self):
        """Select eligible M02 targets, reserve the fair gate, then collect once."""
        require_source_admitted()
        require_cloud_manifest()
        accounts = []
        cursor = None
        scanned = 0
        while True:
            page = self._registry.list_accounts(
                provider_key="ollama", page_size=100, after_key=cursor
            )
            scanned += len(page)
            accounts.extend(page)
            if len(page) < 100:
                break
            if scanned >= 1000:
                raise ValueError("ollama_cloud_target_limit")
            cursor = page[-1].account_id.value
        candidates = []
        for account in accounts:
            if not eligible_cloud_account(
                account.provider_key,
                account.lifecycle,
                account.is_effective_monitoring_enabled,
                account.identity_state,
            ):
                continue
            matches = []
            for profile in self._registry.list_monitoring_profiles(account.account_id):
                for resource in self._registry.list_account_resources(
                    account.account_id
                ):
                    if (
                        resource.resource_id not in profile.resource_ids
                        or profile.profile_id not in resource.linked_profile_ids
                    ):
                        continue
                    try:
                        run = self.prepare_run(
                            account, profile, resource, datetime.now(UTC)
                        )
                    except OllamaCloudTargetIneligible:
                        continue
                    matches.append((run, profile, resource))
            if len(matches) > 1:
                raise ValueError("ollama_cloud_target_ambiguous")
            candidates.extend(matches)
        for run, _, _ in candidates:
            self.register_target(run)
        self._admission.reconcile_source_lane(
            tuple(run.schedule_id for run, _, _ in candidates)
        )
        if not candidates:
            return "ollama_cloud_no_eligible_accounts"
        decision = self.acquire_next(datetime.now(UTC))
        if decision.lease is None:
            return decision.state
        lease = decision.lease
        selected = [
            item
            for item in candidates
            if item[0].schedule_id == lease.schedule_id
            and item[0].account_id == lease.account_id
        ]
        if len(selected) != 1:
            self._admission.recover_rate_gate(
                datetime.now(UTC), expected=lease, reserved_only=True
            )
            raise ValueError("ollama_cloud_target_changed")
        run, profile, resource = selected[0]
        subject = CapacitySubjectV1(
            "ollama",
            profile.provider_installation_id,
            lease.account_id,
            resource.resource_id,
        )
        try:
            return self.execute_admitted(lease, run, subject)
        except BaseException:
            # Release only a reservation that never crossed dispatch. A
            # dispatched/recorded attempt requires normal durable recovery.
            try:
                recovered = self._admission.recover_rate_gate(
                    datetime.now(UTC), expected=lease, reserved_only=True
                )
                if recovered == "recovered":
                    current_run = self._runs.get_run(run.run_id)
                    failure = CollectionFailedV1(
                        run.run_id,
                        "failed",
                        "ollama_cloud_pre_dispatch_failed",
                        datetime.now(UTC),
                    )
                    no_request_runs = SqliteOllamaNoResponseRunRepositoryV1(
                        self._reference, lease.admission_id
                    )
                    if current_run.state == "queued":
                        no_request_runs.finalize_before_dispatch(
                            failure, fencing_token=current_run.fencing_token
                        )
                    elif current_run.state == "running":
                        no_request_runs.finalize_failed(
                            failure, fencing_token=current_run.fencing_token
                        )
            except (OSError, RuntimeError, ValueError):
                pass
            raise

    def _eligible_binding(
        self, run: CollectionRunAdmissionV1 | CollectionRunAdmissionV2
    ) -> ActiveCredentialBindingRefV1:
        """Re-read exact account, profile, resource and current key ownership."""
        if (
            run.account_id is None
            or run.profile_id is None
            or run.resource_id is None
            or run.provider_key != "ollama"
            or run.capability_id != "subscription.quota"
            or run.source_id != "ollama.cloud.balance.v1"
        ):
            raise OllamaCloudTargetIneligible("ollama_cloud_target_ineligible")
        account = self._registry.get_account(run.account_id)
        if isinstance(run, CollectionRunAdmissionV2):
            if (
                account is None
                or account.provider_key != "ollama"
                or account.lifecycle != "active"
                or account.registry_revision != run.registry_revision
                or run.provider_target.target_kind != "cloud_service"
                # Scheduled cloud collection needs a verified-current receipt
                # predicate and is not enabled by this verification-only path.
                or run.trigger != "reauth_verification"
            ):
                raise OllamaCloudTargetIneligible("ollama_cloud_target_ineligible")
            graph = self._cloud_registry.read_monitoring_target(run.account_id)
            active = resolve_active_credential_binding(
                self._bindings.read(run.account_id)
            )
            if (
                graph is None
                or active is None
                or graph.binding != active
                or graph.profile_id != run.profile_id
                or graph.resource_id != run.resource_id
                or graph.access_target_id != run.provider_target.target_id
                or graph.lifecycle != "active"
                or graph.identity_state != "owner_confirmed"
                or active.generation != run.target_generation
            ):
                raise OllamaCloudTargetIneligible("ollama_cloud_target_ineligible")
            return active
        if (
            account is None
            or not eligible_cloud_account(
                account.provider_key,
                account.lifecycle,
                account.is_effective_monitoring_enabled,
                account.identity_state,
            )
            or account.registry_revision != run.registry_revision
        ):
            raise OllamaCloudTargetIneligible("ollama_cloud_target_ineligible")
        profiles = self._registry.list_monitoring_profiles(run.account_id)
        resources = self._registry.list_account_resources(run.account_id)
        matches = [
            profile for profile in profiles if profile.profile_id == run.profile_id
        ]
        matching_resources = [
            resource
            for resource in resources
            if resource.resource_id == run.resource_id
        ]
        if len(matches) != 1 or len(matching_resources) != 1:
            raise OllamaCloudTargetIneligible("ollama_cloud_target_ineligible")
        profile, resource = matches[0], matching_resources[0]
        if (
            profile.lifecycle != "active"
            or profile.management_state != "managed"
            or profile.is_protected_default
            or profile.compatibility_state != "compatible"
            or profile.identity_state not in {"owner_confirmed", "provider_verified"}
            or profile.purpose not in {"subscription", "combined"}
            or profile.provider_installation_id != run.installation_id
            or resource.lifecycle != "active"
            or resource.kind != "subscription_pool"
            or resource.resource_id not in profile.resource_ids
            or profile.profile_id not in resource.linked_profile_ids
        ):
            raise OllamaCloudTargetIneligible("ollama_cloud_target_ineligible")
        active = resolve_active_credential_binding(self._bindings.read(run.account_id))
        if active is None:
            raise OllamaCloudTargetIneligible("ollama_cloud_target_ineligible")
        return active

    def register_target(self, run: CollectionRunAdmissionV1) -> None:
        """Register a genuine eligible account schedule without creating a run."""
        require_source_admitted()
        self._eligible_binding(run)
        self._admission.register_schedule(run)

    def execute_admitted(
        self,
        lease: OllamaCloudRequestLeaseV1,
        run: CollectionRunAdmissionV1 | CollectionRunAdmissionV2,
        subject: CapacitySubjectV1 | CapacitySubjectV2,
    ):
        """Create and progress an M04 run around one admitted real source read."""
        require_source_admitted()
        binding = self._eligible_binding(run)
        validate_cloud_target(
            lease.account_id.value,
            binding.account_id.value,
            subject.account_id.value,
            subject.provider_key,
        )
        if (
            run.schedule_id != lease.schedule_id
            or run.account_id != lease.account_id
            or run.scheduler_instance_id != lease.scheduler_instance_id
            or run.resource_id != subject.resource_id
            or (
                isinstance(run, CollectionRunAdmissionV1)
                and (
                    not isinstance(subject, CapacitySubjectV1)
                    or run.installation_id != subject.installation_id
                )
            )
            or (
                isinstance(run, CollectionRunAdmissionV2)
                and (
                    not isinstance(subject, CapacitySubjectV2)
                    or run.provider_target != subject.provider_target
                )
            )
        ):
            raise ValueError("ollama_cloud_target_mismatch")
        admitted = SqliteOllamaCloudRunRepositoryV1(self._reference, lease).admit_run(
            run
        )
        if admitted.state != "queued":
            raise ValueError("ollama_cloud_run_not_dispatchable")
        now = datetime.now(UTC)
        self._runs.mark_running(run.run_id, now, fencing_token=admitted.fencing_token)
        self._admission.assert_active(lease, datetime.now(UTC))
        # A thrown or interrupted source leaves the rate lease unresolved; do not
        # infer that no 429 happened or open the gate to another request.
        current = datetime.now(UTC)
        remaining = min(
            (lease.lease_expires_at - current).total_seconds(),
            (run.deadline_at - current).total_seconds(),
            CLOUD_BALANCE_POLICY_V1.operation_timeout_seconds,
        )
        if remaining <= 1:
            raise ValueError("ollama_cloud_lease_expired")
        self._admission.mark_dispatched(lease, datetime.now(UTC))
        current = datetime.now(UTC)
        remaining = min(
            (lease.lease_expires_at - current).total_seconds(),
            (run.deadline_at - current).total_seconds(),
            CLOUD_BALANCE_POLICY_V1.operation_timeout_seconds,
        )
        if remaining <= 1:
            # No worker was spawned; make this exact owner cancellation recoverable.
            self._admission.revert_undispatched(lease)
            raise ValueError("ollama_cloud_lease_expired")
        try:
            source_budget = (
                source_budget_seconds(
                    (lease.lease_expires_at - current).total_seconds(),
                    (run.deadline_at - current).total_seconds(),
                    float(CLOUD_BALANCE_POLICY_V1.operation_timeout_seconds),
                )
                if isinstance(run, CollectionRunAdmissionV2)
                else remaining - 1
            )
        except ValueError:
            self._admission.revert_undispatched(lease)
            raise
        source = read_cloud_balance_for_binding_v1(
            binding=binding, deadline_monotonic=time.monotonic() + source_budget
        )
        completed = datetime.now(UTC)
        authorization_not_sent = (
            source.dispatch_certainty == "not_started"
            and source.state == "authorization_unavailable"
        )
        if source.dispatch_certainty == "not_started":
            allowed = {
                "authorization_unavailable",
                "deadline_exceeded",
                "provider_unavailable",
                "internal_adapter_error",
                "source_not_admitted",
            }
            if source.state not in allowed:
                raise ValueError("ollama_cloud_source_binding_invalid")
            terminal = OllamaCloudNoResponseCompletionV2(
                admission_id=lease.admission_id,
                scheduler_instance_id=lease.scheduler_instance_id,
                schedule_id=lease.schedule_id,
                fencing_token=lease.fencing_token,
                started_at=lease.started_at,
                terminal_at=completed,
                reason_code="store_unavailable"
                if authorization_not_sent
                else "source_not_started",
                source_state=source.state,
            )
            self._admission.finish_no_response(lease, terminal)
            failure_code = (
                "ollama_cloud_store_unavailable"
                if authorization_not_sent
                else "ollama_cloud_" + source.state
            )
            failed = CollectionFailedV1(run.run_id, "failed", failure_code, completed)
            SqliteOllamaNoResponseRunRepositoryV1(
                self._reference, lease.admission_id
            ).finalize_failed(
                failed,
                fencing_token=admitted.fencing_token,
                provider_policy=cloud_failure_policy(source.state, None),
            )
            return failed
        if (
            source.dispatch_certainty == "may_have_started"
            or (
                source.dispatch_certainty == "response_received"
                and source.http_status is None
            )
            or source.retry_after_state == "unrepresentable"
        ):
            # We cannot infer whether an unobserved 429 imposed a longer wait.
            raise ValueError("ollama_cloud_outcome_unresolved")
        outcome = admission_outcome_for_source(source.state)
        completion = OllamaCloudRequestCompletionV1(
            admission_id=lease.admission_id,
            scheduler_instance_id=lease.scheduler_instance_id,
            schedule_id=lease.schedule_id,
            fencing_token=lease.fencing_token,
            started_at=lease.started_at,
            response_received_at=completed,
            outcome=outcome,
            retry_after_seconds=(
                source.retry_after_seconds if outcome == "rate_limited" else None
            ),
            jitter_seconds=secrets.randbelow(11),
        )
        self._admission.record_completion(
            lease,
            completion,
            failure_code=source.state if source.state != "success" else None,
        )
        provenance = (
            self._source_provenance(run, source) if source.state == "success" else None
        )
        if source.state != "success":
            safe_codes = {
                "unauthorized",
                "access_denied",
                "rate_limited",
                "provider_unavailable",
                "unexpected_response",
                "invalid_provider_data",
                "deadline_exceeded",
                "authorization_unavailable",
                "internal_adapter_error",
                "source_not_admitted",
            }
            failure_code = (
                "ollama_cloud_store_unavailable"
                if authorization_not_sent
                else "ollama_cloud_"
                + (source.state if source.state in safe_codes else "read_failed")
            )
            failed = CollectionFailedV1(run.run_id, "failed", failure_code, completed)
            self._runs.finalize_failed(
                failed,
                fencing_token=admitted.fencing_token,
                provider_policy=cloud_failure_policy(
                    source.state, source.retry_after_seconds
                ),
            )
            self._admission.complete(completion)
            return failed
        if source.balance is None or provenance is None:
            raise ValueError("ollama_cloud_source_binding_invalid")
        payload = cloud_balance_to_capacity(
            source.balance, subject, run.registry_revision
        )
        digest = capacity_payload_digest(payload)
        self._runs.mark_committing(
            run.run_id,
            fencing_token=admitted.fencing_token,
            payload_digest=digest,
            committing_at=completed,
            terminal_state="partial",
        )
        receipt = self.commit_reading(
            lease, binding, run, subject, run.registry_revision, source, provenance
        )
        self._admission.complete(completion)
        self._runs.finalize_committed(
            receipt,
            terminal_state="partial",
            completed_at=datetime.now(UTC),
            fencing_token=admitted.fencing_token,
        )
        return receipt

    def recover_committing_runs(
        self,
        *,
        as_of: datetime,
        owner_stale_before: datetime,
        recovery_lease_expires_at: datetime,
        maximum_runs: int = 10,
    ):
        """Recover M04 receipts without making a provider request.

        An unresolved global rate lease stays blocked for separate reconciliation.
        """
        executor = ExecuteCollectionRunV1(
            self._runs, SqliteCapacityRepositoryV1(self._reference)
        )
        return executor.recover_pending_commits(
            provider_key="ollama",
            capability_id="subscription.quota",
            source_id="ollama.cloud.balance.v1",
            as_of=as_of,
            owner_stale_before=owner_stale_before,
            recovery_instance_id=self._instance,
            recovery_lease_expires_at=recovery_lease_expires_at,
            maximum_runs=maximum_runs,
        )

    def recover_journals(
        self,
        *,
        as_of: datetime,
        owner_stale_before: datetime,
        recovery_lease_expires_at: datetime,
        maximum_runs: int = 10,
    ) -> tuple[str, int, int]:
        """Reconcile a stale owner's exact rate journal and durable M04 runs."""
        rate = self._admission.recover_rate_gate(
            as_of, owner_stale_before=owner_stale_before
        )
        # Ambiguous post-dispatch outcomes must never permit a new request.
        if rate in {
            "outcome_unknown",
            "legacy_unresolved",
            "owner_active_or_unverified",
        }:
            return rate, 0, 0
        committed = self.recover_committing_runs(
            as_of=as_of,
            owner_stale_before=owner_stale_before,
            recovery_lease_expires_at=recovery_lease_expires_at,
            maximum_runs=maximum_runs,
        )
        orphaned = self._admission.recoverable_orphaned_runs(
            now=as_of, owner_stale_before=owner_stale_before, limit=maximum_runs
        )
        for (
            run_id,
            state,
            fence,
            source_failure,
            retry_after,
            no_response_id,
            no_response_reason,
        ) in orphaned:
            failure_code = (
                "ollama_cloud_store_unavailable"
                if source_failure == "authorization_unavailable"
                else "ollama_cloud_" + source_failure
                if source_failure
                else "ollama_cloud_pre_dispatch_failed"
                if no_response_reason == "pre_dispatch_failed"
                else "ollama_cloud_run_interrupted"
            )
            failure = CollectionFailedV1(run_id, "failed", failure_code, as_of)
            finalizer = (
                SqliteOllamaNoResponseRunRepositoryV1(self._reference, no_response_id)
                if no_response_id is not None
                else self._runs
            )
            if state == "queued":
                finalizer.finalize_before_dispatch(failure, fencing_token=fence)
            else:
                finalizer.finalize_failed(
                    failure,
                    fencing_token=fence,
                    provider_policy=(
                        cloud_failure_policy(source_failure, retry_after)
                        if source_failure
                        else None
                    ),
                )
        if len(orphaned) == maximum_runs:
            raise ValueError("ollama_cloud_recovery_batch_incomplete")
        return rate, len(committed), len(orphaned)

    def acquire_next(self, now: datetime) -> OllamaCloudAdmissionDecisionV1:
        """Use M04's durable round-robin schedule selector, once admitted."""
        require_source_admitted()
        return self._admission.acquire(
            OllamaCloudRequestAcquireV1(
                admission_id=OpaqueIdV1("ollama-cloud-attempt-" + uuid.uuid4().hex),
                scheduler_instance_id=self._instance,
                requested_at=now,
                lease_expires_at=now + timedelta(seconds=60),
                jitter_seconds=secrets.randbelow(11),
            )
        )

    def commit_reading(
        self,
        lease: OllamaCloudRequestLeaseV1,
        binding: ActiveCredentialBindingRefV1,
        run: CollectionRunAdmissionV1 | CollectionRunAdmissionV2,
        subject: CapacitySubjectV1 | CapacitySubjectV2,
        registry_revision: int,
        source: CloudBalanceSourceResultV1,
        provenance: ObservationProvenanceV1,
    ):
        """Project a real result then commit under both M04 and M02 fences."""
        validate_cloud_target(
            lease.account_id.value,
            binding.account_id.value,
            subject.account_id.value,
            subject.provider_key,
        )
        if (
            source.state != "success"
            or source.http_status != 200
            or source.balance is None
            or source.source_id != "ollama.cloud.balance.v1"
            or provenance.provider_key != "ollama"
            or provenance.capability_id != "subscription.quota"
            or provenance.source_id != source.source_id
            or run.schedule_id != lease.schedule_id
            or run.account_id != lease.account_id
            or run.provider_key != "ollama"
            or run.capability_id != "subscription.quota"
            or run.source_id != source.source_id
            or (
                isinstance(run, CollectionRunAdmissionV2)
                and (
                    not isinstance(subject, CapacitySubjectV2)
                    or run.provider_target != subject.provider_target
                )
            )
            or (
                isinstance(run, CollectionRunAdmissionV1)
                and (
                    not isinstance(subject, CapacitySubjectV1)
                    or run.installation_id != subject.installation_id
                )
            )
            or run.resource_id != subject.resource_id
            or run.registry_revision != registry_revision
            or provenance.operation_id != run.run_id
            or provenance.correlation_id != run.correlation_id
            or provenance.observed_at != source.observed_at
        ):
            raise ValueError("ollama_cloud_source_binding_invalid")
        payload = cloud_balance_to_capacity(source.balance, subject, registry_revision)
        payload_digest = capacity_payload_digest(payload)
        if isinstance(payload, ProviderQuotaInputV2):
            if not isinstance(run, CollectionRunAdmissionV2):
                raise ValueError("ollama_cloud_target_mismatch")
            request = CapacityCommitRequestV2(
                run_id=run.run_id,
                target_generation=run.target_generation,
                capability_id="subscription.quota",
                payload_schema=run.payload_schema,
                payload_digest=payload_digest,
                terminal_state="partial",
                payload=payload,
                provenance=provenance,
            )
        else:
            if not isinstance(run, CollectionRunAdmissionV1):
                raise ValueError("ollama_cloud_target_mismatch")
            request = CapacityCommitRequestV1(
                run_id=run.run_id,
                target_generation=run.target_generation,
                capability_id="subscription.quota",
                payload_schema=run.payload_schema,
                payload_digest=payload_digest,
                terminal_state="partial",
                payload=payload,
                provenance=provenance,
            )
        receipt = ollama_capacity_repository(
            self._reference,
            lease,
            run,
            payload_digest,
            verified_at=source.observed_at
            if run.trigger == "reauth_verification"
            else None,
        ).commit_fenced(request, binding)
        return receipt
