"""M01-private real Argon2id adapter; fixed admitted RFC 9106 low-memory policy."""

from threading import BoundedSemaphore

from agentmonitor.modules.identity_access.application.errors import (
    PasswordHasherUnavailableV1,
)
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, VerifyMismatchError
from argon2.low_level import ARGON2_VERSION

_HASH_SLOTS = BoundedSemaphore(2)


class Argon2PasswordV1:
    """Hasher adapter with no tunable weaker/test profile or credential logging."""

    POLICY_VERSION = "argon2id-rfc9106-low-memory-v1"

    def __init__(self) -> None:
        if ARGON2_VERSION != 19:
            raise PasswordHasherUnavailableV1() from None
        self._hasher = PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )

    def hash(self, candidate: str) -> str:
        """Return one randomly salted PHC string for application persistence."""
        try:
            with _HASH_SLOTS:
                return self._hasher.hash(candidate)
        except Exception:
            raise PasswordHasherUnavailableV1() from None

    def verify(self, encoded: str, candidate: str) -> bool:
        """False only for a mismatch; malformed/unavailable material fails closed."""
        try:
            encoded_size = len(candidate.encode("utf-8"))
        except UnicodeEncodeError:
            return False
        if encoded_size > 1024:
            return False
        try:
            with _HASH_SLOTS:
                return self._hasher.verify(encoded, candidate)
        except VerifyMismatchError:
            return False
        except VerificationError:
            raise PasswordHasherUnavailableV1() from None
        except Exception:
            raise PasswordHasherUnavailableV1() from None

    def needs_rehash(self, encoded: str) -> bool:
        """Detect admitted policy drift after a successful verification only."""
        try:
            return self._hasher.check_needs_rehash(encoded)
        except Exception:
            raise PasswordHasherUnavailableV1() from None
