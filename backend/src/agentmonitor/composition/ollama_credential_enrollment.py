"""Owner-local Ollama credential enrollment and cleanup."""

import ctypes
import getpass
import os
import resource
import warnings
from collections.abc import Callable
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    account_credential_lock,
)
from agentmonitor.composition.ollama_env_store import (
    _managed_binding_ids,
    release_env_location_if_unused,
    update_ollama_env,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


class EnrollmentError(ValueError):
    """Sanitized local enrollment failure."""


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
    _disable_core_dumps()
    with account_credential_lock(reference, account_id) as lock_lease:
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
            with warnings.catch_warnings():
                warnings.simplefilter("error", getpass.GetPassWarning)
                entered = getpass.getpass("Ollama API key: ")
            token = bytearray(entered, "ascii")
            del entered
            try:
                if not selection_current():
                    raise EnrollmentError("credential_selection_changed")
                lock_lease.inherited_lock(account_id)
                update_ollama_env(
                    env_path,
                    item.binding_id.value,
                    token,
                    staging_root=reference._approved_root,
                )
            finally:
                token[:] = b"\0" * len(token)
            lock_lease.inherited_lock(account_id)
        except (OSError, ValueError, UnicodeError, getpass.GetPassWarning):
            raise EnrollmentError("credential_store_unavailable") from None
        current = repository.read(account_id)
        if not selection_current():
            raise EnrollmentError("credential_selection_changed")
        if current.record_version != pending.record_version:
            raise EnrollmentError("credential_binding_changed")
        repository.transition_locked(
            account_id,
            action="activate",
            binding_id=item.binding_id,
            expected_record_version=current.record_version,
        )
        _cleanup_pending(env_path, repository, account_id, reference._approved_root)


def _cleanup_pending(
    env_path: Path,
    repository: SqliteCredentialBindingsV1,
    account_id: OpaqueIdV1,
    staging_root: Path,
) -> None:
    state = repository.read(account_id)
    for item in state.bindings:
        if item.lifecycle != "cleanup_pending":
            continue
        update_ollama_env(
            env_path, item.binding_id.value, None, staging_root=staging_root
        )
        state = repository.transition_locked(
            account_id,
            action="cleanup",
            binding_id=item.binding_id,
            expected_record_version=state.record_version,
        )
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
    """Remove only managed orphan entries while M02 blocks new bindings."""
    _disable_core_dumps()
    repository = SqliteCredentialBindingsV1(reference)

    def cleanup() -> None:
        for binding_id in _managed_binding_ids(env_path):
            update_ollama_env(
                env_path, binding_id, None, staging_root=reference._approved_root
            )
        release_env_location_if_unused(
            reference._approved_root, env_path, has_unfinished_bindings=lambda: False
        )

    repository.while_no_unfinished_bindings(cleanup)
