"""Owner-local managed credential enrollment; legacy Ollama entry points retained."""

import ctypes
import getpass
import os
import resource
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from agentmonitor.adapters.credential_env.format import CredentialProviderKey
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    SqliteBillingConnectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    account_credential_lock,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.ollama_env_store import (
    cleanup_untracked_env_entries,
    import_managed_env_variable,
    import_ollama_env_variable,
    release_env_location_if_unused,
    update_managed_env,
    update_ollama_env,
    validate_ollama_env_import_variable,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import AccountBillingConnectionsV1


class EnrollmentError(ValueError):
    """Sanitized local enrollment failure."""


def _require_same_billing_target(
    expected: AccountBillingConnectionsV1, current: AccountBillingConnectionsV1
) -> None:
    """Compare enrollment metadata, independently of derived credential status."""

    def identity(status: AccountBillingConnectionsV1) -> tuple[object, ...]:
        if len(status.connections) != 1:
            raise EnrollmentError("billing_credential_target_changed")
        item = status.connections[0]
        return (
            status.account_id,
            status.provider_key,
            status.account_lifecycle,
            status.account_record_version,
            item.account_id,
            item.resource_id,
            item.provider_key,
            item.record_version,
            item.scope_generation,
            item.scope_id,
            item.scope_evidence,
            item.lifecycle,
            item.monitoring_preference,
        )

    if identity(expected) != identity(current):
        raise EnrollmentError("billing_credential_target_changed")


def require_billing_credential_target(
    reference: DatabaseRefV1,
    account_id: OpaqueIdV1,
    resource_id: OpaqueIdV1,
    *,
    expected: AccountBillingConnectionsV1 | None = None,
) -> AccountBillingConnectionsV1:
    """Read the actual selected M02 relationship without any credential access."""
    status = SqliteBillingConnectionRepositoryV1(reference).get(account_id)
    if (
        status is None
        or status.provider_key not in {"claude", "codex"}
        or status.account_lifecycle not in {"pending", "active"}
        or len(status.connections) != 1
        or status.connections[0].resource_id != resource_id
        or status.connections[0].lifecycle not in {"pending", "active"}
    ):
        raise EnrollmentError("billing_credential_target_unavailable")
    if expected is not None:
        _require_same_billing_target(expected, status)
    return status


def enroll_billing_credential(
    reference: DatabaseRefV1,
    account_id: OpaqueIdV1,
    resource_id: OpaqueIdV1,
    env_path: Path,
    *,
    selection_current: Callable[[], bool],
) -> None:
    """Store an owner-entered billing key without claiming verified API access."""
    if not all(os.isatty(fd) for fd in (0, 1, 2)):
        raise EnrollmentError("owner_terminal_required")
    if len({os.ttyname(fd) for fd in (0, 1, 2)}) != 1:
        raise EnrollmentError("owner_terminal_required")
    captured = require_billing_credential_target(reference, account_id, resource_id)

    def target_current() -> None:
        require_billing_credential_target(
            reference, account_id, resource_id, expected=captured
        )

    provider: CredentialProviderKey
    if captured.provider_key == "claude":
        provider = "claude"
    else:
        provider = "codex"
    _enroll_managed_credential(
        reference,
        account_id,
        env_path,
        selection_current=selection_current,
        import_variable=None,
        provider_key=provider,
        target_current=target_current,
    )


def require_billing_maintenance_target(
    reference: DatabaseRefV1,
    account_id: OpaqueIdV1,
    resource_id: OpaqueIdV1,
    *,
    expected: AccountBillingConnectionsV1 | None = None,
) -> AccountBillingConnectionsV1:
    """Cleanup remains possible after archive/disconnect, only for this resource."""
    status = SqliteBillingConnectionRepositoryV1(reference).get(account_id)
    if (
        status is None
        or status.provider_key not in {"claude", "codex"}
        or len(status.connections) != 1
        or status.connections[0].resource_id != resource_id
    ):
        raise EnrollmentError("billing_credential_target_unavailable")
    if expected is not None:
        _require_same_billing_target(expected, status)
    return status


def maintain_billing_credential(
    reference: DatabaseRefV1,
    account_id: OpaqueIdV1,
    resource_id: OpaqueIdV1,
    env_path: Path,
    *,
    action: Literal["disconnect", "cleanup"],
    selection_current: Callable[[], bool],
    expected: AccountBillingConnectionsV1 | None = None,
) -> None:
    """Revoke before cleanup; a deletion failure never restores access."""
    if action not in {"disconnect", "cleanup"}:
        raise EnrollmentError("billing_credential_action_invalid")
    _disable_core_dumps()
    with account_credential_lock(reference, account_id) as lease:
        captured = require_billing_maintenance_target(
            reference, account_id, resource_id, expected=expected
        )
        if not selection_current():
            raise EnrollmentError("credential_selection_changed")
        repository = SqliteCredentialBindingsV1(reference)
        if action == "disconnect":
            state = repository.read(account_id)
            selected = captured.connections[0]
            repository.disconnect_billing_locked(
                account_id,
                resource_id,
                expected_account_version=captured.account_record_version,
                expected_connection_version=selected.record_version,
                expected_scope_generation=selected.scope_generation,
                expected_record_version=state.record_version,
                lock_lease=lease,
            )

        def cleanup_current() -> bool:
            lease.inherited_lock(account_id)
            current = require_billing_maintenance_target(
                reference, account_id, resource_id
            )
            return current.provider_key == captured.provider_key and selection_current()

        _cleanup_pending(
            env_path,
            repository,
            account_id,
            reference._approved_root,
            provider_key="claude" if captured.provider_key == "claude" else "codex",
            selection_current=cleanup_current,
        )


def _require_credential_provider(
    reference: DatabaseRefV1,
    account_id: OpaqueIdV1,
    provider_key: CredentialProviderKey,
) -> None:
    account = SqliteRegistryRepositoryV1(reference).get_account(account_id)
    if account is None or account.provider_key != provider_key:
        raise EnrollmentError("credential_binding_account_unavailable")


def _disable_core_dumps() -> None:
    try:
        if os.getuid() != os.geteuid():
            raise ValueError("credential_operator_uid_invalid")
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        if resource.getrlimit(resource.RLIMIT_CORE) != (0, 0):
            raise ValueError("core_dump_protection_unavailable")
        libc = ctypes.CDLL(None, use_errno=True)
        libc.prctl.argtypes = [ctypes.c_int] * 5
        libc.prctl.restype = ctypes.c_int
        if libc.prctl(4, 0, 0, 0, 0) != 0 or libc.prctl(3, 0, 0, 0, 0) != 0:
            raise ValueError("core_dump_protection_unavailable")
    except (OSError, ValueError, AttributeError):
        raise EnrollmentError("credential_store_unavailable") from None


def enroll_ollama_credential(
    reference: DatabaseRefV1,
    account_id: OpaqueIdV1,
    env_path: Path,
    *,
    selection_current: Callable[[], bool],
) -> None:
    """Prompt privately and atomically activate an account-scoped .env entry.

    A failure after preparation intentionally leaves the pending reference so it
    can be reconciled safely; it never deletes the previously active binding.
    """
    if not all(os.isatty(fd) for fd in (0, 1, 2)):
        raise EnrollmentError("owner_terminal_required")
    if len({os.ttyname(fd) for fd in (0, 1, 2)}) != 1:
        raise EnrollmentError("owner_terminal_required")
    _enroll_ollama_credential(
        reference,
        account_id,
        env_path,
        selection_current=selection_current,
        import_variable=None,
    )


def enroll_ollama_credential_from_env(
    reference: DatabaseRefV1,
    account_id: OpaqueIdV1,
    env_path: Path,
    variable_name: str,
    *,
    selection_current: Callable[[], bool],
) -> None:
    """Import one literal entry into the normal guarded binding lifecycle."""
    validate_ollama_env_import_variable(variable_name)
    _enroll_ollama_credential(
        reference,
        account_id,
        env_path,
        selection_current=selection_current,
        import_variable=variable_name,
    )


def _enroll_ollama_credential(
    reference: DatabaseRefV1,
    account_id: OpaqueIdV1,
    env_path: Path,
    *,
    selection_current: Callable[[], bool],
    import_variable: str | None,
) -> None:
    _enroll_managed_credential(
        reference,
        account_id,
        env_path,
        selection_current=selection_current,
        import_variable=import_variable,
        provider_key="ollama",
    )


def _enroll_managed_credential(
    reference: DatabaseRefV1,
    account_id: OpaqueIdV1,
    env_path: Path,
    *,
    selection_current: Callable[[], bool],
    import_variable: str | None,
    provider_key: CredentialProviderKey,
    target_current: Callable[[], None] | None = None,
) -> None:
    def require_current_target() -> None:
        _require_credential_provider(reference, account_id, provider_key)
        if target_current is not None:
            target_current()

    _disable_core_dumps()
    with account_credential_lock(reference, account_id) as lock_lease:
        require_current_target()
        repository = SqliteCredentialBindingsV1(reference)
        before = repository.read(account_id)
        pending_items = tuple(
            item for item in before.bindings if item.lifecycle == "pending"
        )
        if pending_items:
            # Retry the same account-owned pending item after an interrupted store.
            pending, item = before, pending_items[0]
        else:
            pending = repository.transition_locked(
                account_id,
                action="prepare",
                expected_record_version=before.record_version,
            )
            item = next(
                item for item in pending.bindings if item.lifecycle == "pending"
            )
        try:
            if not selection_current():
                raise EnrollmentError("credential_selection_changed")
            lock_lease.inherited_lock(account_id)
            require_current_target()
            if import_variable is None:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", getpass.GetPassWarning)
                    prompt = {
                        "ollama": "Ollama API key: ",
                        "claude": "Anthropic administrative API key: ",
                        "codex": "OpenAI administrative API key: ",
                    }[provider_key]
                    entered = getpass.getpass(prompt)
                token = bytearray(entered, "ascii")
                del entered
                try:
                    if not selection_current():
                        raise EnrollmentError("credential_selection_changed")
                    lock_lease.inherited_lock(account_id)
                    require_current_target()
                    if provider_key == "ollama":
                        update_ollama_env(
                            env_path,
                            item.binding_id.value,
                            token,
                            staging_root=reference._approved_root,
                        )
                    else:
                        update_managed_env(
                            env_path,
                            item.binding_id.value,
                            token,
                            provider_key=provider_key,
                            staging_root=reference._approved_root,
                        )
                finally:
                    token[:] = b"\0" * len(token)
            else:
                if provider_key == "ollama":
                    import_ollama_env_variable(
                        env_path,
                        item.binding_id.value,
                        import_variable,
                        staging_root=reference._approved_root,
                    )
                else:
                    import_managed_env_variable(
                        env_path,
                        item.binding_id.value,
                        import_variable,
                        provider_key=provider_key,
                        staging_root=reference._approved_root,
                    )
            lock_lease.inherited_lock(account_id)
        except (OSError, ValueError, UnicodeError, getpass.GetPassWarning):
            raise EnrollmentError("credential_store_unavailable") from None
        current = repository.read(account_id)
        if not selection_current():
            raise EnrollmentError("credential_selection_changed")
        require_current_target()
        lock_lease.inherited_lock(account_id)
        if current.record_version != pending.record_version:
            raise EnrollmentError("credential_binding_changed")
        repository.transition_locked(
            account_id,
            action="activate",
            binding_id=item.binding_id,
            expected_record_version=current.record_version,
        )
        _cleanup_pending(
            env_path,
            repository,
            account_id,
            reference._approved_root,
            provider_key=provider_key,
        )


def _cleanup_pending(
    env_path: Path,
    repository: SqliteCredentialBindingsV1,
    account_id: OpaqueIdV1,
    staging_root: Path,
    *,
    provider_key: CredentialProviderKey = "ollama",
    selection_current: Callable[[], bool] | None = None,
) -> None:
    def require_current_selection() -> None:
        if selection_current is not None and not selection_current():
            raise EnrollmentError("credential_selection_changed")

    require_current_selection()
    state = repository.read(account_id)
    for item in state.bindings:
        if item.lifecycle != "cleanup_pending":
            continue
        require_current_selection()
        if provider_key == "ollama":
            update_ollama_env(
                env_path, item.binding_id.value, None, staging_root=staging_root
            )
        else:
            update_managed_env(
                env_path,
                item.binding_id.value,
                None,
                provider_key=provider_key,
                staging_root=staging_root,
            )
        require_current_selection()
        state = repository.transition_locked(
            account_id,
            action="cleanup",
            binding_id=item.binding_id,
            expected_record_version=state.record_version,
        )
    require_current_selection()
    release_env_location_if_unused(
        staging_root,
        env_path,
        has_unfinished_bindings=repository.has_unfinished_bindings,
    )


def disconnect_ollama_credential(
    reference: DatabaseRefV1,
    account_id: OpaqueIdV1,
    env_path: Path,
    *,
    selection_current: Callable[[], bool],
) -> None:
    """Disable the binding before removing only its managed entries."""
    _disable_core_dumps()
    with account_credential_lock(reference, account_id):
        _require_credential_provider(reference, account_id, "ollama")
        if not selection_current():
            raise EnrollmentError("credential_selection_changed")
        repository = SqliteCredentialBindingsV1(reference)
        state = repository.read(account_id)
        repository.transition_locked(
            account_id,
            action="disconnect",
            expected_record_version=state.record_version,
        )
        _cleanup_pending(env_path, repository, account_id, reference._approved_root)


def cleanup_ollama_credential(
    reference: DatabaseRefV1,
    account_id: OpaqueIdV1,
    env_path: Path,
    *,
    selection_current: Callable[[], bool],
) -> None:
    """Retry recorded cleanup, including for an archived account."""
    _disable_core_dumps()
    with account_credential_lock(reference, account_id):
        _require_credential_provider(reference, account_id, "ollama")
        if not selection_current():
            raise EnrollmentError("credential_selection_changed")
        _cleanup_pending(
            env_path,
            SqliteCredentialBindingsV1(reference),
            account_id,
            reference._approved_root,
        )


def cleanup_untracked_ollama_credentials(
    reference: DatabaseRefV1, env_path: Path
) -> None:
    """Remove reserved orphan entries under the creation/writer guard."""
    _disable_core_dumps()
    repository = SqliteCredentialBindingsV1(reference)
    cleanup_untracked_env_entries(
        reference._approved_root,
        env_path,
        has_unfinished_bindings=repository.has_unfinished_bindings,
    )
