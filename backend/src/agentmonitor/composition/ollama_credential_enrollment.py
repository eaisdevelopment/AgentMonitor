"""Owner-local enrollment coordinator; never accepts or captures a credential."""

import os
import subprocess

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    account_credential_lock,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.keyring_command import (
    build_store_command,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


class EnrollmentError(ValueError):
    """Sanitized local enrollment failure."""


def enroll_ollama_credential(reference: DatabaseRefV1, account_id: OpaqueIdV1) -> None:
    """Use the owner's controlling terminal and the dedicated Secret Service item.

    A failure after preparation intentionally leaves the pending reference so it
    can be reconciled safely; it never deletes the previously active binding.
    """
    if not all(os.isatty(fd) for fd in (0, 1, 2)):
        raise EnrollmentError("owner_terminal_required")
    if len({os.ttyname(fd) for fd in (0, 1, 2)}) != 1:
        raise EnrollmentError("owner_terminal_required")
    with account_credential_lock(reference, account_id):
        repository = SqliteCredentialBindingsV1(reference)
        before = repository.read(account_id)
        pending = repository.transition_locked(
            account_id, action="prepare", expected_record_version=before.record_version
        )
        item = next(item for item in pending.bindings if item.lifecycle == "pending")
        try:
            result = subprocess.run(
                build_store_command(item.binding_id.value), timeout=300, check=False
            )
        except (OSError, subprocess.SubprocessError):
            raise EnrollmentError("credential_store_unavailable") from None
        if result.returncode:
            raise EnrollmentError("credential_store_unavailable")
        current = repository.read(account_id)
        if current.record_version != pending.record_version:
            raise EnrollmentError("credential_binding_changed")
        repository.transition_locked(
            account_id,
            action="activate",
            binding_id=item.binding_id,
            expected_record_version=current.record_version,
        )
