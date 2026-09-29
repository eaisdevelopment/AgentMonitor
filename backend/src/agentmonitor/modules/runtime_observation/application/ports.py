"""Published M06 owner-association persistence seam and safe identity key."""

import hashlib
from collections.abc import Callable
from typing import Protocol

from agentmonitor.contracts.runtime_observation_v1 import (
    OwnerProcessAccountAssociationV1,
    ProcessIdentityV1,
)


class OwnerAssociationErrorV1(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def owner_association_key(
    identity: ProcessIdentityV1, executable_identity: str | None = None
) -> str:
    source = "\x1f".join(
        (
            "owner-process-account.v1",
            identity.platform_source,
            identity.platform_scope_id,
            str(identity.pid),
            str(identity.start_time_ticks),
            executable_identity or "unavailable",
        )
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


class OwnerAssociationRepositoryV1(Protocol):
    def records(self) -> dict[str, OwnerProcessAccountAssociationV1]: ...

    def update(
        self,
        key: str,
        transition: Callable[
            [OwnerProcessAccountAssociationV1 | None], OwnerProcessAccountAssociationV1
        ],
    ) -> OwnerProcessAccountAssociationV1: ...
