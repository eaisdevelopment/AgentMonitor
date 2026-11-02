"""Versioned P01 port for owner-initiated Ollama cloud verification."""

from datetime import datetime
from typing import Protocol

from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    CredentialConnectionStatusV1,
    InitiateOllamaCloudVerificationCommandV1,
)


class OllamaCloudConnectionPortV1(Protocol):
    """Return safe status and enqueue one idempotent owner verification."""

    def read(
        self, account_id: OpaqueIdV1, as_of: datetime
    ) -> CredentialConnectionStatusV1: ...

    def initiate(
        self, command: InitiateOllamaCloudVerificationCommandV1
    ) -> CredentialConnectionStatusV1: ...
