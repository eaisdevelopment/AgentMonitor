"""Owner-terminal Claude launch with authenticated OTLP session persistence."""

from __future__ import annotations

import hashlib
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    checkpoint_sqlite_database,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.persistence.runtime_observation.sqlite.repository import (
    SqliteRuntimeObservationRepositoryV1,
)
from agentmonitor.adapters.platform.linux.processes import (
    ApprovedLinuxExecutableSelectorV1,
    InspectLinuxProcessesV1,
)
from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)
from agentmonitor.adapters.providers.claude.local_sessions.source import (
    CLAUDE_OTLP_ACCOUNT_RULE_ID,
    map_otel_session_count,
)
from agentmonitor.adapters.providers.claude.manifest import (
    CLAUDE_OTEL_ADAPTER_ID,
    CLAUDE_OTEL_ADAPTER_VERSION,
    CLAUDE_OTEL_MAPPING_DIGEST,
)
from agentmonitor.adapters.providers.claude.telemetry.launcher import (
    ClaudeMonitoredExecV1,
    current_process_identity,
    exec_monitored_claude,
)
from agentmonitor.adapters.providers.claude.telemetry.otlp_http_json import (
    CLAUDE_OTLP_PARSER_VERSION,
    CLAUDE_OTLP_SOURCE_ID,
    CLAUDE_OTLP_SOURCE_VERSION,
    ClaudeOtlpHttpJsonReceiverV1,
    ClaudeOtlpSessionCountV1,
)
from agentmonitor.composition.iam_operator import exclusive_service_quiescence
from agentmonitor.composition.linux_runtime_monitoring import (
    run_linux_runtime_collection,
)
from agentmonitor.contracts.collection_control_v1 import (
    CollectionFailedV1,
    CollectionRunAdmissionV1,
    CollectionRunViewV1,
)
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    CollectionOutcomeV1,
    RetryAdviceV1,
)
from agentmonitor.contracts.registry_v1 import (
    AccountViewV1,
    ConfirmProviderIdentityFingerprintCommandV1,
    ProviderIdentityResolutionV1,
    ResolveProviderIdentityFingerprintQueryV1,
)
from agentmonitor.contracts.runtime_observation_v1 import (
    AgentProcessRecordV1,
    AgentSessionRecordV1,
    ApprovedStrongCorrelationRuleV1,
    PlatformInspectionRequestV1,
    ProcessIdentityV1,
    RuntimeCommitReceiptV1,
    RuntimeCommitRequestV1,
    RuntimeObservationBatchV1,
    SessionProcessLinkInputV1,
)
from agentmonitor.modules.collection_control.application.executor import (
    ExecuteCollectionRunV1,
)
from agentmonitor.modules.collection_control.application.runner import (
    RequestManualCollectionV1,
    RunOneCollectionV1,
)
from agentmonitor.modules.registry.application.accounts import (
    AlertScopeAndSubjectQueryV1,
    ConfirmProviderIdentityFingerprintV1,
    ListAccountsV1,
    ListMonitoringProfilesV1,
    ResolveProviderIdentityFingerprintV1,
)
from agentmonitor.modules.registry.application.discovery import (
    ListProviderInstallationsV1,
)
from agentmonitor.modules.runtime_observation.application.commit import (
    CommitRuntimeCollectionOutcomeV1,
)
from agentmonitor.modules.runtime_observation.application.correlation import (
    decide_session_correlation,
)
from agentmonitor.modules.runtime_observation.application.payload_digest import (
    runtime_payload_digest,
)
from agentmonitor.modules.runtime_observation.application.queries import (
    ListAgentSessionsV1,
)

_IDENTITY_SCHEME = "claude.otel.account.sha256"
_IDENTITY_SCOPE = "provider_account"
_SAFE_FAILURE_CODE = re.compile(r"[a-z][a-z0-9_]{0,127}\Z")
_LAUNCH_PROCESS_WAIT_SECONDS = 5.0
_START_SIGNAL_MAX_BYTES = 130
# M04 target generations must advance when this collection policy/manifest
# changes even if M02's installation registry revision is unchanged.  The
# first reviewed OTLP policy follows the legacy ``registry_revision``
# generation used before this independent policy counter existed.
_COLLECTION_POLICY_GENERATION = 1
_APPROVED_ACCOUNT_RULE = ApprovedStrongCorrelationRuleV1(
    rule_id=CLAUDE_OTLP_ACCOUNT_RULE_ID,
    source_id=CLAUDE_OTLP_SOURCE_ID,
    source_version=CLAUDE_OTLP_SOURCE_VERSION,
    decision_reference="claude-official-otel-owner-binding-v1",
)


@dataclass(frozen=True, slots=True)
class ClaudeOtlpRuntimeCommitResultV1:
    queued_run: CollectionRunViewV1
    completed_run: CollectionRunViewV1
    receipt: RuntimeCommitReceiptV1
    session: AgentSessionRecordV1
    process: AgentProcessRecordV1
    link: SessionProcessLinkInputV1
    session_observation_id: OpaqueIdV1
    selected_account_id: OpaqueIdV1


@dataclass(frozen=True, slots=True)
class ClaudeOtlpLaunchPlanV1:
    executable: Path = field(repr=False)
    configuration: ClaudeMonitoredExecV1 = field(repr=False)
    provider_version: str
    registry_revision: int
    selected_account_id: OpaqueIdV1
    selected_account_record_version: int
    selected_profile_id: OpaqueIdV1
    selected_profile_record_version: int


def prepare_monitored_claude_launch(
    data_root: Path,
    *,
    selected_account_id: OpaqueIdV1,
    process_identity: ProcessIdentityV1,
    endpoint: str,
    authorization_secret: str,
    launch_id: str,
) -> ClaudeOtlpLaunchPlanV1:
    """Resolve one registered installation without changing its default profile."""
    if not data_root.is_absolute() or data_root in {Path("/"), Path.home()}:
        raise ValueError("claude_otel_runtime_data_root_invalid")
    reference = DatabaseRefV1(data_root / "agentmonitor.db", data_root)
    registry = SqliteRegistryRepositoryV1(reference)
    installations = tuple(
        installation
        for installation in ListProviderInstallationsV1(registry)("claude")
        if installation.provider_key == "claude"
        and installation.platform_key == "linux-x86_64"
        and installation.presence_state == "present"
        and installation.version.state == "known_masked"
        and installation.version.masked_value is not None
    )
    if len(installations) != 1:
        raise ValueError("claude_otel_registered_installation_unresolved")
    installation = installations[0]
    discovered = discover_default_installation()
    if discovered.provider_version != installation.version.masked_value:
        raise ValueError("claude_otel_installation_version_mismatch")
    account, profile_id, profile_record_version = _eligible_owner_account(
        registry,
        selected_account_id=selected_account_id,
        installation_id=installation.provider_installation_id.value,
    )
    registry_revision = AlertScopeAndSubjectQueryV1(registry)(
        "account", selected_account_id
    ).registry_revision
    return ClaudeOtlpLaunchPlanV1(
        executable=discovered.executable_for_adapter,
        configuration=ClaudeMonitoredExecV1(
            endpoint=endpoint,
            authorization_secret=authorization_secret,
            launch_id=launch_id,
            installation_id=installation.provider_installation_id.value,
            process_identity=process_identity,
        ),
        provider_version=discovered.provider_version,
        registry_revision=registry_revision,
        selected_account_id=account.account_id,
        selected_account_record_version=account.record_version,
        selected_profile_id=profile_id,
        selected_profile_record_version=profile_record_version,
    )


def _eligible_owner_account(
    registry: SqliteRegistryRepositoryV1,
    *,
    selected_account_id: OpaqueIdV1,
    installation_id: str,
    expected_account_record_version: int | None = None,
    expected_profile_id: OpaqueIdV1 | None = None,
    expected_profile_record_version: int | None = None,
) -> tuple[AccountViewV1, OpaqueIdV1, int]:
    accounts = tuple(
        account
        for account in ListAccountsV1(registry)("claude")
        if account.account_id == selected_account_id
    )
    if len(accounts) != 1:
        raise ValueError("claude_otel_default_profile_account_unresolved")
    account = accounts[0]
    if (
        account.provider_key != "claude"
        or account.lifecycle != "active"
        or account.identity_state != "owner_confirmed"
        or (
            expected_account_record_version is not None
            and account.record_version != expected_account_record_version
        )
    ):
        raise ValueError("claude_otel_default_profile_account_unresolved")
    profiles = tuple(
        profile
        for profile in ListMonitoringProfilesV1(registry)(selected_account_id)
        if profile.account_id == selected_account_id
        and profile.lifecycle == "active"
        and profile.management_state == "provider_default"
        and profile.is_protected_default
        and profile.provider_installation_id.value == installation_id
    )
    if len(profiles) != 1:
        raise ValueError("claude_otel_default_profile_account_unresolved")
    profile = profiles[0]
    if (
        expected_profile_id is not None and profile.profile_id != expected_profile_id
    ) or (
        expected_profile_record_version is not None
        and profile.record_version != expected_profile_record_version
    ):
        raise ValueError("claude_otel_default_profile_account_unresolved")
    return account, profile.profile_id, profile.record_version


def _digest(*values: str) -> str:
    return hashlib.sha256("\x00".join(values).encode()).hexdigest()


def _start_failure_signal(error: BaseException) -> bytes:
    code = str(error)
    if _SAFE_FAILURE_CODE.fullmatch(code) is None:
        code = "claude_otel_monitoring_start_failed"
    return f"0{code}".encode("ascii")


def _start_failure_from_signal(signal: bytes) -> str:
    if not signal.startswith(b"0") or len(signal) > _START_SIGNAL_MAX_BYTES:
        return "claude_otel_monitoring_start_failed"
    try:
        code = signal[1:].decode("ascii")
    except UnicodeDecodeError:
        return "claude_otel_monitoring_start_failed"
    return (
        code
        if _SAFE_FAILURE_CODE.fullmatch(code) is not None
        else "claude_otel_monitoring_start_failed"
    )


def _wait_for_launched_process(
    plan: ClaudeOtlpLaunchPlanV1,
) -> None:
    """Observe the exact exec target before a short-lived session can exit."""
    selector = ApprovedLinuxExecutableSelectorV1.from_executable(
        selector_id="linux.proc.claude-process.v1",
        executable_identity="claude",
        provider_key="claude",
        installation_id=plan.configuration.installation_id,
        provider_version=plan.provider_version,
        executable=plan.executable,
    )
    inspector = InspectLinuxProcessesV1(approved_executable_selectors=(selector,))
    deadline = time.monotonic() + _LAUNCH_PROCESS_WAIT_SECONDS
    while time.monotonic() < deadline:
        request_deadline = datetime.now(UTC) + timedelta(seconds=1)
        outcome = inspector(
            PlatformInspectionRequestV1(
                operation_id=f"claude-otel-launch-{plan.configuration.launch_id}",
                correlation_id=f"claude-otel-launch-{plan.configuration.launch_id}",
                provider_key="claude",
                installation_id=plan.configuration.installation_id,
                provider_version=plan.provider_version,
                source_id="linux.proc.process.v1",
                selector_id="linux.proc.claude-process.v1",
                executable_identity="claude",
                requested_fields=(),
                maximum_candidates=16_384,
                maximum_results=512,
                deadline_at=request_deadline,
            )
        )
        if any(
            process.identity == plan.configuration.process_identity
            for process in outcome.processes
        ):
            return
        if outcome.state not in {"success", "partial"}:
            raise ValueError(
                outcome.error_code or "claude_otel_launch_process_observation_failed"
            )
        time.sleep(0.02)
    raise ValueError("claude_otel_launch_process_not_observed")


def _admission(
    plan: ClaudeOtlpLaunchPlanV1, requested_at: datetime
) -> CollectionRunAdmissionV1:
    run_id = f"claude-otel-run-{uuid.uuid4().hex}"
    request_id = f"claude-otel-request-{uuid.uuid4().hex}"
    correlation_id = f"claude-otel-correlation-{uuid.uuid4().hex}"
    target_digest = _digest(
        "claude-otel-session-target-v1",
        plan.configuration.installation_id,
        plan.selected_account_id.value,
        plan.selected_profile_id.value,
        CLAUDE_OTLP_SOURCE_ID,
    )
    return CollectionRunAdmissionV1(
        run_id=OpaqueIdV1(run_id),
        schedule_id=OpaqueIdV1(f"claude-otel-session-{target_digest[:32]}"),
        request_id=OpaqueIdV1(request_id),
        trigger="manual",
        operation_family="collect.local.session.discovery",
        requested_capability_ids=("local.session.discovery",),
        capability_set_version="1.0.0",
        request_auth_method="owner_local_operator",
        request_principal_id=OpaqueIdV1("agentmonitor-owner"),
        correlation_id=OpaqueIdV1(correlation_id),
        causation_id=None,
        target_key_digest=target_digest,
        provider_key="claude",
        installation_id=OpaqueIdV1(plan.configuration.installation_id),
        account_id=plan.selected_account_id,
        profile_id=plan.selected_profile_id,
        resource_id=None,
        capability_id="local.session.discovery",
        source_id=CLAUDE_OTLP_SOURCE_ID,
        adapter_version=CLAUDE_OTEL_ADAPTER_VERSION,
        provider_version=plan.provider_version,
        adapter_protocol_version="1.0.0",
        manifest_fingerprint=_digest(
            "claude-otel-manifest-v1", CLAUDE_OTEL_MAPPING_DIGEST
        ),
        collection_policy_version="1.0.0",
        registry_revision=plan.registry_revision,
        retry_chain_id=OpaqueIdV1(f"claude-otel-retry-{uuid.uuid4().hex}"),
        attempt_ordinal=1,
        target_generation=plan.registry_revision + _COLLECTION_POLICY_GENERATION,
        scheduler_instance_id=OpaqueIdV1("agentmonitor-local-manual"),
        lease_policy_version="1.0.0",
        budget_policy_id="claude-local-session-start-v1",
        budget_policy_version="1.0.0",
        budget_scope_digest=target_digest,
        budget_dimension="local_session_starts",
        budget_unit="session",
        budget_units=1,
        budget_limit_units=1,
        budget_window_start=requested_at,
        budget_window_end=requested_at + timedelta(minutes=1),
        payload_schema="runtime-observation-batch.v1",
        idempotency_key_digest=_digest(request_id),
        request_digest=_digest(request_id, target_digest, "local.session.discovery"),
        requested_at=requested_at,
        deadline_at=requested_at + timedelta(seconds=30),
    )


def _provenance(
    *,
    admission: CollectionRunAdmissionV1,
    metric: ClaudeOtlpSessionCountV1,
) -> ObservationProvenanceV1:
    collected_at = datetime.now(UTC)
    return ObservationProvenanceV1(
        provider_key="claude",
        capability_id="local.session.discovery",
        capability_schema_version="1.0",
        adapter_id=CLAUDE_OTEL_ADAPTER_ID,
        adapter_version=CLAUDE_OTEL_ADAPTER_VERSION,
        provider_protocol_version="1.0.0",
        source_id=CLAUDE_OTLP_SOURCE_ID,
        source_class="documented_api",
        mechanism_version=CLAUDE_OTLP_SOURCE_VERSION,
        parser_version=CLAUDE_OTLP_PARSER_VERSION,
        provider_version=metric.provider_version,
        provider_version_availability=FieldAvailabilityV1("available"),
        observed_at=metric.observed_at,
        observed_at_availability=FieldAvailabilityV1("available"),
        collected_at=collected_at,
        freshness_deadline=collected_at + timedelta(minutes=1),
        freshness_availability=FieldAvailabilityV1("available"),
        freshness_policy_id="claude-otel-session-one-minute-v1",
        precision="exact",
        confidence="confirmed",
        confidence_reason_code="authenticated_private_otlp_exact_process",
        value_kind="provider_reported",
        is_experimental=False,
        fallback_lineage=(),
        warnings=(),
        operation_id=admission.run_id,
        correlation_id=admission.correlation_id,
        decision_reference="claude-official-otel-monitoring-v1",
        derivation_method=None,
        input_observation_ids=(),
    )


def _prepare_commit(
    admission: CollectionRunAdmissionV1,
    outcome: CollectionOutcomeV1[RuntimeObservationBatchV1],
    completed_at: datetime,
) -> RuntimeCommitRequestV1 | CollectionFailedV1:
    if outcome.state != "success":
        assert outcome.error is not None
        return CollectionFailedV1(
            run_id=admission.run_id,
            terminal_state="failed",
            error_code=outcome.error.code,
            completed_at=completed_at,
        )
    assert outcome.value is not None and outcome.provenance is not None
    return RuntimeCommitRequestV1(
        run_id=admission.run_id,
        target_generation=admission.target_generation,
        capability_id=admission.capability_id,
        payload_schema=admission.payload_schema,
        payload_digest=runtime_payload_digest(outcome.value),
        terminal_state="succeeded",
        payload=outcome.value,
        provenance=outcome.provenance,
    )


def _identity_resolution_matches_admission(
    resolution: ProviderIdentityResolutionV1,
    *,
    account_id: OpaqueIdV1,
    account_record_version: int,
    registry_revision: int,
) -> bool:
    """Close correlation to the exact registry generation admitted by M04."""
    return (
        resolution.state == "resolved"
        and resolution.account_id == account_id
        and resolution.account_record_version == account_record_version
        and resolution.registry_revision == registry_revision
    )


def _owner_binding_command(
    *,
    plan: ClaudeOtlpLaunchPlanV1,
    metric: ClaudeOtlpSessionCountV1,
    session_observation_id: OpaqueIdV1,
    payload_digest: str,
    requested_at: datetime,
) -> ConfirmProviderIdentityFingerprintCommandV1:
    """Build the exact M02 command without exposing the fingerprint to the CLI."""
    if (
        metric.installation_id != plan.configuration.installation_id
        or metric.provider_version != plan.provider_version
        or metric.process_identity != plan.configuration.process_identity
    ):
        raise ValueError("claude_otel_launch_scope_mismatch")
    return ConfirmProviderIdentityFingerprintCommandV1(
        idempotency_key=session_observation_id,
        principal_id=OpaqueIdV1("agentmonitor-owner"),
        account_id=plan.selected_account_id,
        expected_account_record_version=plan.selected_account_record_version,
        provider_key="claude",
        identity_scheme=_IDENTITY_SCHEME,
        identity_scope=_IDENTITY_SCOPE,
        identity_scheme_version=1,
        subject_fingerprint=metric.observed_account_fingerprint,
        source_id=CLAUDE_OTLP_SOURCE_ID,
        source_version=CLAUDE_OTLP_SOURCE_VERSION,
        parser_version=CLAUDE_OTLP_PARSER_VERSION,
        evidence_reference=session_observation_id,
        expected_evidence_digest=payload_digest,
        requested_at=requested_at,
    )


def _checkpoint_and_acknowledge(
    reference: DatabaseRefV1,
    receiver: ClaudeOtlpHttpJsonReceiverV1,
    metric: ClaudeOtlpSessionCountV1,
) -> None:
    """Release exporter success only after quiescent SQLite durability cleanup."""
    checkpoint_sqlite_database(reference)
    receiver.acknowledge_committed(metric)


@dataclass(frozen=True, slots=True)
class _CollectedSessionV1:
    metric: ClaudeOtlpSessionCountV1
    process: AgentProcessRecordV1
    batch: RuntimeObservationBatchV1
    selected_account_id: OpaqueIdV1
    requires_owner_binding: bool
    owner_confirmation_requested: bool


def _collect_session_outcome(
    *,
    data_root: Path,
    reference: DatabaseRefV1,
    plan: ClaudeOtlpLaunchPlanV1,
    receiver: ClaudeOtlpHttpJsonReceiverV1,
    admission: CollectionRunAdmissionV1,
    runtime_repository: SqliteRuntimeObservationRepositoryV1,
    collected: list[_CollectedSessionV1],
    allow_initial_owner_binding: bool = False,
) -> CollectionOutcomeV1[RuntimeObservationBatchV1]:
    try:
        _wait_for_launched_process(plan)
        process_run = run_linux_runtime_collection(data_root)
        process = next(
            (
                candidate
                for candidate in process_run.processes
                if candidate.identity == plan.configuration.process_identity
            ),
            None,
        )
        if process is None:
            raise ValueError("claude_otel_live_process_verification_missing")
        receiver.enable_observation_acceptance(process.last_observed_at)
        metric = receiver.wait(8)
        if (
            metric.installation_id != plan.configuration.installation_id
            or metric.provider_version != plan.provider_version
            or metric.process_identity != plan.configuration.process_identity
        ):
            raise ValueError("claude_otel_launch_scope_mismatch")
        registry = SqliteRegistryRepositoryV1(reference)
        account, _profile_id, _profile_record_version = _eligible_owner_account(
            registry,
            selected_account_id=plan.selected_account_id,
            installation_id=metric.installation_id,
            expected_account_record_version=plan.selected_account_record_version,
            expected_profile_id=plan.selected_profile_id,
            expected_profile_record_version=plan.selected_profile_record_version,
        )
        resolution = ResolveProviderIdentityFingerprintV1(registry)(
            ResolveProviderIdentityFingerprintQueryV1(
                provider_key="claude",
                identity_scheme=_IDENTITY_SCHEME,
                identity_scope=_IDENTITY_SCOPE,
                identity_scheme_version=1,
                subject_fingerprint=metric.observed_account_fingerprint,
            )
        )
        already_bound = _identity_resolution_matches_admission(
            resolution,
            account_id=account.account_id,
            account_record_version=account.record_version,
            registry_revision=admission.registry_revision,
        )
        requires_owner_binding = (
            resolution.state == "unresolved"
            and resolution.registry_revision == admission.registry_revision
        )
        if not already_bound and not (
            allow_initial_owner_binding and requires_owner_binding
        ):
            raise ValueError("claude_otel_account_owner_confirmation_failed")
        batch = map_otel_session_count(
            metric,
            process,
            provider_version=plan.provider_version,
            bound_account_id=account.account_id.value if already_bound else None,
            bound_account_fingerprint=(
                metric.observed_account_fingerprint if already_bound else None
            ),
        )
        collected.append(
            _CollectedSessionV1(
                metric,
                process,
                batch,
                account.account_id,
                requires_owner_binding,
                allow_initial_owner_binding,
            )
        )
        return CollectionOutcomeV1.success(
            batch,
            _provenance(
                admission=admission,
                metric=metric,
            ),
        )
    except (OSError, RuntimeError, ValueError) as error:
        error_code = str(error)
        if _SAFE_FAILURE_CODE.fullmatch(error_code) is None:
            error_code = "claude_otel_session_collection_failed"
        return CollectionOutcomeV1.failure(
            state="internal_adapter_error",
            code=error_code,
            retry=RetryAdviceV1("never"),
        )


def _run_receiver_collection(
    data_root: Path,
    receiver: ClaudeOtlpHttpJsonReceiverV1,
    launch_plan: ClaudeOtlpLaunchPlanV1,
    readiness_fd: int,
    *,
    allow_initial_owner_binding: bool = False,
) -> ClaudeOtlpRuntimeCommitResultV1:
    """Run the locked receiver child; this function never controls Claude."""
    if not data_root.is_absolute() or data_root in {Path("/"), Path.home()}:
        raise ValueError("claude_otel_runtime_data_root_invalid")
    database_path = data_root / "agentmonitor.db"
    if not database_path.is_file():
        raise ValueError("claude_otel_runtime_database_missing")
    reference = DatabaseRefV1(database_path, data_root)
    verified_plan = prepare_monitored_claude_launch(
        data_root,
        selected_account_id=launch_plan.selected_account_id,
        process_identity=launch_plan.configuration.process_identity,
        endpoint=receiver.endpoint,
        authorization_secret=receiver.authorization_secret,
        launch_id=receiver.launch_id,
    )
    if verified_plan != launch_plan:
        raise ValueError("claude_otel_launch_plan_changed")
    admission = _admission(launch_plan, datetime.now(UTC))
    collection_repository = SqliteCollectionRepositoryV1(reference)
    runtime_repository = SqliteRuntimeObservationRepositoryV1(
        reference,
        correlation_evaluator=lambda session, evidence: decide_session_correlation(
            session, evidence, approved_rules=(_APPROVED_ACCOUNT_RULE,)
        ),
    )
    executor = ExecuteCollectionRunV1[
        RuntimeObservationBatchV1, RuntimeObservationBatchV1
    ](
        collection_repository,
        CommitRuntimeCollectionOutcomeV1(runtime_repository),
    )
    queued = RequestManualCollectionV1(collection_repository)(admission)
    collected: list[_CollectedSessionV1] = []
    with receiver:
        os.write(readiness_fd, b"1")
        os.close(readiness_fd)
        try:
            receipt = RunOneCollectionV1(executor)(
                admission,
                lambda: _collect_session_outcome(
                    data_root=data_root,
                    reference=reference,
                    plan=launch_plan,
                    receiver=receiver,
                    admission=admission,
                    runtime_repository=runtime_repository,
                    collected=collected,
                    allow_initial_owner_binding=allow_initial_owner_binding,
                ),
                _prepare_commit,
                started_at=datetime.now(UTC),
                completed_at=lambda: datetime.now(UTC),
            )
            if isinstance(receipt, CollectionFailedV1):
                raise ValueError(f"claude_otel_runtime_{receipt.error_code}")
            if not isinstance(receipt, RuntimeCommitReceiptV1) or len(collected) != 1:
                raise ValueError("claude_otel_runtime_receipt_invalid")
            completed = collection_repository.get_run(admission.run_id)
            facts = collected[0]
            session_identity = facts.batch.session_observations[0].session_identity
            session = next(
                (
                    candidate
                    for candidate in ListAgentSessionsV1(runtime_repository)(
                        provider_key="claude",
                        as_of=datetime.now(UTC),
                        page_size=500,
                    )
                    if candidate.identity == session_identity
                ),
                None,
            )
            if session is None:
                raise ValueError("claude_otel_runtime_projection_missing")
            result = ClaudeOtlpRuntimeCommitResultV1(
                queued_run=queued,
                completed_run=completed,
                receipt=receipt,
                session=session,
                process=facts.process,
                link=facts.batch.session_process_links[0],
                session_observation_id=OpaqueIdV1(
                    facts.batch.session_observations[0].observation_id
                ),
                selected_account_id=facts.selected_account_id,
            )
            reopened = runtime_repository.get_commit_status(
                admission.run_id, admission.capability_id
            )
            reopened_links = (
                runtime_repository.get_session_process_links(
                    reopened.receipt.observation_ids
                )
                if reopened.receipt is not None
                else ()
            )
            expected_correlation_state = (
                "unresolved" if facts.requires_owner_binding else "automatic_matched"
            )
            expected_account_id = (
                None
                if facts.requires_owner_binding
                else result.selected_account_id.value
            )
            if (
                result.completed_run.state != "succeeded"
                or result.session.correlation_state != expected_correlation_state
                or result.session.account_id != expected_account_id
                or reopened.state != "committed"
                or reopened.receipt is None
                or reopened.receipt != receipt
                or result.session_observation_id not in reopened.receipt.observation_ids
                or OpaqueIdV1(result.link.link_id)
                not in reopened.receipt.observation_ids
                or reopened_links != (result.link,)
            ):
                raise ValueError("claude_otel_runtime_reopened_verification_failed")
            if facts.owner_confirmation_requested:
                if not allow_initial_owner_binding:
                    raise ValueError("claude_otel_account_owner_confirmation_failed")
                session_observation = facts.batch.session_observations[0]
                if (
                    session_observation.source_id != CLAUDE_OTLP_SOURCE_ID
                    or session_observation.source_version != CLAUDE_OTLP_SOURCE_VERSION
                    or session_observation.parser_version != CLAUDE_OTLP_PARSER_VERSION
                    or session_observation.provider_version
                    != launch_plan.provider_version
                    or reopened.receipt.payload_digest
                    != runtime_payload_digest(facts.batch)
                ):
                    raise ValueError("claude_otel_owner_binding_evidence_invalid")
                binding = ConfirmProviderIdentityFingerprintV1(
                    SqliteRegistryRepositoryV1(reference)
                )(
                    _owner_binding_command(
                        plan=launch_plan,
                        metric=facts.metric,
                        session_observation_id=result.session_observation_id,
                        payload_digest=reopened.receipt.payload_digest,
                        requested_at=datetime.now(UTC),
                    )
                )
                reopened_binding = ResolveProviderIdentityFingerprintV1(
                    SqliteRegistryRepositoryV1(reference)
                )(
                    ResolveProviderIdentityFingerprintQueryV1(
                        provider_key="claude",
                        identity_scheme=_IDENTITY_SCHEME,
                        identity_scope=_IDENTITY_SCOPE,
                        identity_scheme_version=1,
                        subject_fingerprint=facts.metric.observed_account_fingerprint,
                    )
                )
                if (
                    binding != reopened_binding
                    or binding.state != "resolved"
                    or binding.account_id != result.selected_account_id
                    or binding.account_record_version
                    != launch_plan.selected_account_record_version
                    or binding.registry_revision <= admission.registry_revision
                ):
                    raise ValueError("claude_otel_owner_binding_verification_failed")
            _checkpoint_and_acknowledge(reference, receiver, facts.metric)
            return result
        except (OSError, RuntimeError, TypeError, ValueError):
            receiver.acknowledge_failed()
            raise


def launch_owner_terminal(
    argv: list[str] | None = None,
    *,
    allow_initial_owner_binding: bool = False,
    expected_selected_account_record_version: int | None = None,
) -> int:
    """Launch reviewed Claude with either matched or explicitly approved binding."""
    arguments = sys.argv[1:] if argv is None else argv
    if (
        len(arguments) != 4
        or arguments[0] != "--data-root"
        or arguments[2] != "--account-id"
    ):
        print("invalid_operator_arguments")
        return 2
    try:
        selected_account_id = OpaqueIdV1(arguments[3])
    except (TypeError, ValueError):
        print("invalid_operator_arguments")
        return 2
    if not (sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty()):
        print("controlling_tty_required")
        return 2
    data_root = Path(arguments[1])
    if not data_root.is_absolute() or data_root in {Path("/"), Path.home()}:
        print("claude_otel_runtime_data_root_invalid")
        return 2
    reference = DatabaseRefV1(data_root / "agentmonitor.db", data_root)
    receiver = ClaudeOtlpHttpJsonReceiverV1()
    try:
        process_identity = current_process_identity()
        plan = prepare_monitored_claude_launch(
            data_root,
            selected_account_id=selected_account_id,
            process_identity=process_identity,
            endpoint=receiver.endpoint,
            authorization_secret=receiver.authorization_secret,
            launch_id=receiver.launch_id,
        )
        if (
            expected_selected_account_record_version is not None
            and plan.selected_account_record_version
            != expected_selected_account_record_version
        ):
            raise ValueError("claude_otel_account_version_changed")
        ready_read, ready_write = os.pipe2(os.O_CLOEXEC)
        receiver_pid = os.fork()
    except (OSError, RuntimeError, ValueError):
        print("claude_otel_monitoring_start_failed")
        return 1
    if receiver_pid == 0:
        os.close(ready_read)
        try:
            with exclusive_service_quiescence(data_root, reference):
                _run_receiver_collection(
                    data_root,
                    receiver,
                    plan,
                    ready_write,
                    allow_initial_owner_binding=allow_initial_owner_binding,
                )
        except (OSError, RuntimeError, ValueError) as error:
            try:
                os.write(ready_write, _start_failure_signal(error))
            except OSError:
                pass
            try:
                os.close(ready_write)
            except OSError:
                pass
            os._exit(1)
        os._exit(0)
    os.close(ready_write)
    try:
        ready = os.read(ready_read, _START_SIGNAL_MAX_BYTES)
    except OSError:
        ready = b""
    finally:
        os.close(ready_read)
    if ready != b"1":
        os.waitpid(receiver_pid, 0)
        print(_start_failure_from_signal(ready))
        return 1
    try:
        exec_monitored_claude(plan.executable, (), plan.configuration)
    except (OSError, ValueError):
        print("claude_otel_launch_failed")
        return 1
    return 1


def main(argv: list[str] | None = None) -> int:
    """Launch reviewed Claude in the owner's terminal with private OTEL metrics."""
    return launch_owner_terminal(argv)


if __name__ == "__main__":
    raise SystemExit(main())
