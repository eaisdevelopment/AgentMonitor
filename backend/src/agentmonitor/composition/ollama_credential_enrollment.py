"""Owner-local Ollama credential enrollment and cleanup."""

import getpass
import os
import warnings

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    account_credential_lock,
)
from agentmonitor.composition.ollama_env_store import (
    update_ollama_env,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


class EnrollmentError(ValueError):
    """Sanitized local enrollment failure."""


def enroll_ollama_credential(reference: DatabaseRefV1, account_id: OpaqueIdV1) -> None:
    """Prompt privately and atomically activate an account-scoped .env entry.

    A failure after preparation intentionally leaves the pending reference so it
    can be reconciled safely; it never deletes the previously active binding.
    """
    if not all(os.isatty(fd) for fd in (0, 1, 2)):
        raise EnrollmentError("owner_terminal_required")
    if len({os.ttyname(fd) for fd in (0, 1, 2)}) != 1:
        raise EnrollmentError("owner_terminal_required")
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
                lock_lease.inherited_lock(account_id)
                update_ollama_env(reference, item.binding_id.value, token)
            finally:
                token[:] = b"\0" * len(token)
            lock_lease.inherited_lock(account_id)
        except (OSError, ValueError, UnicodeError, getpass.GetPassWarning):
            raise EnrollmentError("credential_store_unavailable") from None
        current = repository.read(account_id)
        if current.record_version != pending.record_version:
            raise EnrollmentError("credential_binding_changed")
        repository.transition_locked(
            account_id,
            action="activate",
            binding_id=item.binding_id,
            expected_record_version=current.record_version,
        )
        _cleanup_pending(reference, repository, account_id)


def _cleanup_pending(
    reference: DatabaseRefV1,
    repository: SqliteCredentialBindingsV1,
    account_id: OpaqueIdV1,
) -> None:
    state = repository.read(account_id)
    for item in state.bindings:
        if item.lifecycle != "cleanup_pending":
            continue
        update_ollama_env(reference, item.binding_id.value, None)
        state = repository.transition_locked(
            account_id,
            action="cleanup",
            binding_id=item.binding_id,
            expected_record_version=state.record_version,
        )


def disconnect_ollama_credential(
    reference: DatabaseRefV1, account_id: OpaqueIdV1
) -> None:
    """Disable the binding before removing only its managed entries."""
    with account_credential_lock(reference, account_id):
        repository = SqliteCredentialBindingsV1(reference)
        state = repository.read(account_id)
        repository.transition_locked(
            account_id,
            action="disconnect",
            expected_record_version=state.record_version,
        )
        _cleanup_pending(reference, repository, account_id)
