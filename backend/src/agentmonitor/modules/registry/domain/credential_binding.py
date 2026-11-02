"""Pure M02 lifecycle policy for non-secret managed credential bindings."""

from dataclasses import replace
from typing import Literal

from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    CredentialBindingAggregateV1,
    CredentialBindingRecordV1,
)
from agentmonitor.modules.registry.domain.account import RegistryPolicyErrorV1

DisconnectReasonV1 = Literal[
    "owner_disconnected", "account_archived", "account_deleted"
]


def _ensure_record_version(
    aggregate: CredentialBindingAggregateV1, expected_record_version: int
) -> None:
    if type(expected_record_version) is not int or expected_record_version < 0:
        raise RegistryPolicyErrorV1("registry_credential_binding_version_invalid")
    if aggregate.record_version != expected_record_version:
        raise RegistryPolicyErrorV1("registry_credential_binding_version_conflict")


def _find_binding(
    aggregate: CredentialBindingAggregateV1, binding_id: OpaqueIdV1
) -> CredentialBindingRecordV1:
    matches = tuple(
        item for item in aggregate.bindings if item.binding_id == binding_id
    )
    if len(matches) != 1:
        raise RegistryPolicyErrorV1("registry_credential_binding_not_found")
    return matches[0]


def _replace_binding(
    aggregate: CredentialBindingAggregateV1,
    replacement: CredentialBindingRecordV1,
    *,
    binding_generation: int | None = None,
) -> CredentialBindingAggregateV1:
    return CredentialBindingAggregateV1(
        account_id=aggregate.account_id,
        record_version=aggregate.record_version + 1,
        binding_generation=(
            aggregate.binding_generation
            if binding_generation is None
            else binding_generation
        ),
        bindings=tuple(
            replacement if item.binding_id == replacement.binding_id else item
            for item in aggregate.bindings
        ),
    )


def new_credential_binding_aggregate(
    account_id: OpaqueIdV1,
) -> CredentialBindingAggregateV1:
    """Create one empty account-owned aggregate without generating an ID."""
    return CredentialBindingAggregateV1(
        account_id=account_id,
        record_version=0,
        binding_generation=0,
        bindings=(),
    )


def prepare_credential_binding(
    aggregate: CredentialBindingAggregateV1,
    *,
    binding_id: OpaqueIdV1,
    expected_record_version: int,
) -> CredentialBindingAggregateV1:
    """Add one owner-asserted pending binding without changing active authority."""
    _ensure_record_version(aggregate, expected_record_version)
    if any(
        item.binding_id == binding_id or item.lifecycle == "pending"
        for item in aggregate.bindings
    ):
        raise RegistryPolicyErrorV1("registry_credential_binding_conflict")
    pending = CredentialBindingRecordV1(
        account_id=aggregate.account_id,
        binding_id=binding_id,
        lifecycle="pending",
        generation=aggregate.binding_generation + 1,
        association_provenance="owner_asserted",
        reason_code="owner_prepared",
    )
    return CredentialBindingAggregateV1(
        account_id=aggregate.account_id,
        record_version=aggregate.record_version + 1,
        binding_generation=aggregate.binding_generation,
        bindings=(*aggregate.bindings, pending),
    )


def activate_prepared_credential_binding(
    aggregate: CredentialBindingAggregateV1,
    *,
    binding_id: OpaqueIdV1,
    expected_record_version: int,
) -> CredentialBindingAggregateV1:
    """Atomically activate a stored item and schedule the old item for cleanup."""
    _ensure_record_version(aggregate, expected_record_version)
    target = _find_binding(aggregate, binding_id)
    if target.lifecycle != "pending":
        raise RegistryPolicyErrorV1("registry_credential_binding_state_invalid")
    activated = replace(
        target,
        lifecycle="active",
        reason_code="owner_activated",
    )
    return CredentialBindingAggregateV1(
        account_id=aggregate.account_id,
        record_version=aggregate.record_version + 1,
        binding_generation=target.generation,
        bindings=tuple(
            activated
            if item.binding_id == binding_id
            else replace(
                item,
                lifecycle="cleanup_pending",
                reason_code="rotation_replaced",
            )
            if item.lifecycle == "active"
            else item
            for item in aggregate.bindings
        ),
    )


def mark_pending_credential_binding_cleanup(
    aggregate: CredentialBindingAggregateV1,
    *,
    binding_id: OpaqueIdV1,
    expected_record_version: int,
) -> CredentialBindingAggregateV1:
    """Abandon one pending attempt while preserving any old active binding."""
    _ensure_record_version(aggregate, expected_record_version)
    target = _find_binding(aggregate, binding_id)
    if target.lifecycle != "pending":
        raise RegistryPolicyErrorV1("registry_credential_binding_state_invalid")
    return _replace_binding(
        aggregate,
        replace(
            target,
            lifecycle="cleanup_pending",
            reason_code="pending_cleanup_requested",
        ),
    )


def disconnect_active_credential_binding(
    aggregate: CredentialBindingAggregateV1,
    *,
    expected_record_version: int,
    reason_code: DisconnectReasonV1,
) -> CredentialBindingAggregateV1:
    """Disable scheduling and move the exact active binding to cleanup."""
    _ensure_record_version(aggregate, expected_record_version)
    if reason_code not in {
        "owner_disconnected",
        "account_archived",
        "account_deleted",
    }:
        raise RegistryPolicyErrorV1("registry_credential_binding_reason_invalid")
    active = tuple(item for item in aggregate.bindings if item.lifecycle == "active")
    if len(active) != 1:
        raise RegistryPolicyErrorV1("registry_credential_binding_state_invalid")
    return CredentialBindingAggregateV1(
        account_id=aggregate.account_id,
        record_version=aggregate.record_version + 1,
        binding_generation=aggregate.binding_generation + 1,
        bindings=tuple(
            replace(item, lifecycle="cleanup_pending", reason_code=reason_code)
            if item.lifecycle in {"active", "pending"}
            else item
            for item in aggregate.bindings
        ),
    )


def complete_credential_binding_cleanup(
    aggregate: CredentialBindingAggregateV1,
    *,
    binding_id: OpaqueIdV1,
    expected_record_version: int,
) -> CredentialBindingAggregateV1:
    """Record cleanup only after the dedicated local item was actually cleared."""
    _ensure_record_version(aggregate, expected_record_version)
    target = _find_binding(aggregate, binding_id)
    if target.lifecycle != "cleanup_pending":
        raise RegistryPolicyErrorV1("registry_credential_binding_state_invalid")
    return _replace_binding(
        aggregate,
        replace(
            target,
            lifecycle="cleanup_complete",
            reason_code="local_cleanup_completed",
        ),
    )


def resolve_active_credential_binding(
    aggregate: CredentialBindingAggregateV1,
) -> ActiveCredentialBindingRefV1 | None:
    """Return the sole safe active reference; never a credential or store path."""
    active = tuple(item for item in aggregate.bindings if item.lifecycle == "active")
    if not active:
        return None
    item = active[0]
    return ActiveCredentialBindingRefV1(
        account_id=item.account_id,
        binding_id=item.binding_id,
        generation=item.generation,
    )


def ensure_credential_binding_commit_current(
    aggregate: CredentialBindingAggregateV1,
    reference: ActiveCredentialBindingRefV1,
) -> Literal["current"]:
    """Fence an observation commit against rotation, disconnect, or wrong account."""
    current = resolve_active_credential_binding(aggregate)
    if (
        reference.account_id != aggregate.account_id
        or reference.generation != aggregate.binding_generation
        or reference != current
    ):
        raise RegistryPolicyErrorV1("registry_credential_binding_stale")
    return "current"
