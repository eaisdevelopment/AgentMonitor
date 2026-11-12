"""Admit one owner-requested API billing check without provider I/O."""

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.collection_control.sqlite.budget import (
    BudgetCollectionError,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    CollectionRepositoryErrorV1,
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    SqliteBillingAccessRepositoryV1,
    SqliteBillingConnectionRepositoryV1,
    ensure_billing_access_in_transaction,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    CredentialBindingRepositoryErrorV1,
    SqliteCloudCredentialRegistryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.registry_transaction import (
    RegistryRepositoryErrorV1,
)
from agentmonitor.adapters.providers.claude.anthropic_api.policy import SOURCE_ID
from agentmonitor.adapters.providers.codex.openai_api.policy import (
    SOURCE_ID as OPENAI_SOURCE_ID,
)
from agentmonitor.composition.billing_run import (
    anthropic_cost_manifest_fingerprint,
    build_anthropic_billing_run,
)
from agentmonitor.composition.openai_billing_run import (
    OPENAI_COST_AUTHORITY_ID_V1,
    build_openai_billing_run,
    openai_cost_manifest_fingerprint,
)
from agentmonitor.contracts.billing_actions_v1 import BillingCheckCommandV1
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import BillingAccessTargetV1


@dataclass(frozen=True, slots=True)
class BillingCheckIdentifiersV1:
    """Deterministic technical identities; no credential or provider value."""

    run_id: OpaqueIdV1
    schedule_id: OpaqueIdV1
    request_id: OpaqueIdV1
    retry_chain_id: OpaqueIdV1
    scheduler_instance_id: OpaqueIdV1
    correlation_id: OpaqueIdV1
    idempotency_key_digest: str


def _digest(*values: str) -> str:
    return hashlib.sha256("\0".join(values).encode("utf-8")).hexdigest()


def _identifier(prefix: str, *values: str) -> OpaqueIdV1:
    return OpaqueIdV1(prefix + _digest(*values)[:40])


def billing_check_identifiers(
    command: BillingCheckCommandV1,
) -> BillingCheckIdentifiersV1:
    """Derive replay-stable IDs scoped to the owner and exact target intent."""
    if (
        not isinstance(command, BillingCheckCommandV1)
        or not isinstance(command.requested_at, datetime)
        or command.requested_at.utcoffset() != timedelta(0)
    ):
        raise ValueError("billing_check_command_invalid")
    owner_request = (command.principal_id.value, command.command_id.value)
    target = (
        command.account_id.value,
        command.resource_id.value,
        str(command.expected_account_version),
        str(command.expected_connection_version),
    )
    return BillingCheckIdentifiersV1(
        run_id=_identifier("billing-check-run-", *owner_request),
        schedule_id=_identifier("billing-check-schedule-", *target),
        request_id=_identifier("billing-check-request-", *owner_request),
        retry_chain_id=_identifier("billing-check-retry-", *owner_request),
        scheduler_instance_id=_identifier("billing-check-producer-", *owner_request),
        correlation_id=_identifier("billing-check-correlation-", *owner_request),
        idempotency_key_digest=_digest(
            "billing-check-command-v1", *owner_request, *target
        ),
    )


def _require_replay(
    command: BillingCheckCommandV1,
    identifiers: BillingCheckIdentifiersV1,
    run: BudgetCollectionRunViewV1,
    target: BillingAccessTargetV1,
) -> BudgetCollectionRunViewV1:
    provider = target.connection.provider_key
    if (
        run.run_id != identifiers.run_id
        or run.schedule_id != identifiers.schedule_id
        or provider not in {"claude", "codex"}
        or run.provider_key != provider
        or run.account_id != command.account_id
        or run.resource_id != command.resource_id
        or run.capability_id != "api.cost"
        or run.source_id != (SOURCE_ID if provider == "claude" else OPENAI_SOURCE_ID)
        or target.purpose != "verification"
        or target.connection.account_id != command.account_id
        or target.connection.resource_id != command.resource_id
        or target.connection.record_version != command.expected_connection_version
    ):
        raise ValueError("billing_check_idempotency_conflict")
    return run


class BillingCheckActionsV1:
    """Queue an admitted Anthropic/OpenAI check through the durable M04 run."""

    def __init__(
        self,
        reference: DatabaseRefV1,
        *,
        on_queued: Callable[[], None] | None = None,
        can_dispatch: Callable[[], bool] | None = None,
    ) -> None:
        if not isinstance(reference, DatabaseRefV1):
            raise ValueError("billing_check_unavailable")
        if (on_queued is not None and not callable(on_queued)) or (
            can_dispatch is not None and not callable(can_dispatch)
        ):
            raise ValueError("billing_check_unavailable")
        self._connections = SqliteBillingConnectionRepositoryV1(reference)
        self._access = SqliteBillingAccessRepositoryV1(reference)
        self._service_targets = SqliteCloudCredentialRegistryV1(reference)
        self._on_queued = on_queued
        self._can_dispatch = can_dispatch
        self._runs = SqliteCollectionRepositoryV1(
            reference,
            billing_admission_fence=ensure_billing_access_in_transaction,
        )

    def get_status(self, run_id: OpaqueIdV1) -> BudgetCollectionRunViewV1 | None:
        """Read captured billing history without requiring current credentials."""
        if not isinstance(run_id, OpaqueIdV1):
            raise ValueError("billing_check_unavailable")
        try:
            run = self._runs.get_run(run_id)
        except CollectionRepositoryErrorV1 as error:
            if error.code == "collection_run_not_found":
                return None
            raise ValueError("billing_check_unavailable") from None
        if not isinstance(run, BudgetCollectionRunViewV1):
            return None
        try:
            target = self._runs.get_billing_target(run_id)
        except (BudgetCollectionError, CollectionRepositoryErrorV1):
            raise ValueError("billing_check_unavailable") from None
        if (
            run.run_id != run_id
            or run.account_id != target.connection.account_id
            or run.resource_id != target.connection.resource_id
            or run.provider_key != target.connection.provider_key
        ):
            raise ValueError("billing_check_unavailable")
        return run

    def _notify_queued(self, run: BudgetCollectionRunViewV1) -> None:
        """Best-effort wake hint after durable admission; never an authority."""
        if run.state != "queued" or self._on_queued is None:
            return
        try:
            self._on_queued()
        except Exception:
            return

    def _replay(
        self,
        command: BillingCheckCommandV1,
        identifiers: BillingCheckIdentifiersV1,
    ) -> BudgetCollectionRunViewV1 | None:
        try:
            run = self._runs.get_run(identifiers.run_id)
        except CollectionRepositoryErrorV1 as error:
            if error.code == "collection_run_not_found":
                return None
            raise ValueError("billing_check_unavailable") from None
        if not isinstance(run, BudgetCollectionRunViewV1):
            raise ValueError("billing_check_idempotency_conflict")
        try:
            target = self._runs.get_billing_target(run.run_id)
        except (BudgetCollectionError, CollectionRepositoryErrorV1):
            raise ValueError("billing_check_unavailable") from None
        return _require_replay(command, identifiers, run, target)

    def _target(self, command: BillingCheckCommandV1) -> BillingAccessTargetV1:
        try:
            status = self._connections.get(command.account_id)
        except RegistryRepositoryErrorV1:
            raise ValueError("billing_check_unavailable") from None
        if status is None or len(status.connections) != 1:
            raise ValueError("billing_check_target_unavailable")
        if status.provider_key not in {"claude", "codex"}:
            raise ValueError("billing_check_provider_unsupported")
        connection = status.connections[0]
        if connection.resource_id != command.resource_id:
            raise ValueError("billing_check_target_unavailable")
        if (
            status.account_record_version != command.expected_account_version
            or connection.record_version != command.expected_connection_version
        ):
            raise ValueError("billing_check_version_conflict")
        try:
            target = self._access.resolve(
                command.account_id, command.resource_id, "verification"
            )
        except RegistryRepositoryErrorV1:
            raise ValueError("billing_check_unavailable") from None
        if target is None:
            raise ValueError("billing_check_authority_unavailable")
        return target

    def check(self, command: BillingCheckCommandV1) -> BudgetCollectionRunViewV1:
        """Replay or queue exactly one bounded read; never call the provider."""
        identifiers = billing_check_identifiers(command)
        replay = self._replay(command, identifiers)
        if replay is not None:
            self._notify_queued(replay)
            return replay
        target = self._target(command)
        if self._can_dispatch is not None:
            try:
                dispatch_ready = self._can_dispatch()
            except Exception:
                raise ValueError("billing_check_service_unavailable") from None
            if dispatch_ready is not True:
                raise ValueError("billing_check_service_unavailable")
        try:
            is_openai = target.connection.provider_key == "codex"
            service_target = self._service_targets.reconcile_access_target(
                provider_key=target.connection.provider_key,
                authority_id=OPENAI_COST_AUTHORITY_ID_V1
                if is_openai
                else "anthropic.analytics",
                manifest_fingerprint=openai_cost_manifest_fingerprint()
                if is_openai
                else anthropic_cost_manifest_fingerprint(),
                as_of=command.requested_at,
            )
            build = (
                build_openai_billing_run if is_openai else build_anthropic_billing_run
            )
            admission = build(
                target=target,
                access_target=service_target,
                registry_revision=target.connection.registry_revision,
                scheduler_instance_id=identifiers.scheduler_instance_id,
                run_id=identifiers.run_id,
                schedule_id=identifiers.schedule_id,
                request_id=identifiers.request_id,
                retry_chain_id=identifiers.retry_chain_id,
                correlation_id=identifiers.correlation_id,
                causation_id=None,
                trigger="reauth_verification",
                request_principal_id=command.principal_id,
                idempotency_key_digest=identifiers.idempotency_key_digest,
                requested_at=command.requested_at,
                deadline_at=command.requested_at + timedelta(seconds=120),
            )
            result = self._runs.admit_run(admission)
        except CredentialBindingRepositoryErrorV1:
            raise ValueError("billing_check_service_unavailable") from None
        except CollectionRepositoryErrorV1 as error:
            if error.code == "collection_idempotency_conflict":
                raise ValueError("billing_check_idempotency_conflict") from None
            if error.code in {
                "collection_budget_exhausted",
                "collection_retry_deferred",
            }:
                raise ValueError("billing_check_rate_limited") from None
            raise ValueError("billing_check_unavailable") from None
        except BudgetCollectionError:
            raise ValueError("billing_check_unavailable") from None
        except ValueError as error:
            if str(error) == "billing_access_changed":
                raise ValueError("billing_check_target_changed") from None
            raise ValueError("billing_check_unavailable") from None
        if not isinstance(result, BudgetCollectionRunViewV1):
            raise ValueError("billing_check_unavailable")
        admitted = _require_replay(command, identifiers, result, target)
        self._notify_queued(admitted)
        return admitted
