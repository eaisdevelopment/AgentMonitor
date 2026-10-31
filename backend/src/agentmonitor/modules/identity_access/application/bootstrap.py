"""M01 bootstrap use case and narrow ports; no ORM, CLI, or crypto dependency."""

from typing import Protocol

from agentmonitor.contracts.identity_access_v1 import (
    BootstrapAdministratorOutcomeV1,
    IamInitializationStateV1,
    RecoverAdministratorOutcomeV1,
    SecretInputV1,
)
from agentmonitor.modules.identity_access.domain.policy import (
    bootstrap_state_error,
    password_creation_error,
)


class PasswordHasherPortV1(Protocol):
    POLICY_VERSION: str

    def hash(self, candidate: str) -> str: ...


class IdentityAccessBootstrapRepositoryPortV1(Protocol):
    def initialization_state(self) -> IamInitializationStateV1: ...

    def claim_administrator(
        self, password_phc: str, hash_policy_version: str, correlation_id: str
    ) -> BootstrapAdministratorOutcomeV1: ...


class IdentityAccessRecoveryRepositoryPortV1(Protocol):
    def recover_administrator(
        self, password_phc: str, hash_policy_version: str, correlation_id: str
    ) -> RecoverAdministratorOutcomeV1: ...


class GetIamInitializationStateV1:
    """Safe setup state for composition/P01; no credential details are returned."""

    def __init__(self, repository: IdentityAccessBootstrapRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(self) -> IamInitializationStateV1:
        return self._repository.initialization_state()


class BootstrapAdministratorV1:
    """Claim the sole administrator through a real exclusive repository UoW."""

    def __init__(
        self,
        repository: IdentityAccessBootstrapRepositoryPortV1,
        hasher: PasswordHasherPortV1,
    ) -> None:
        self._repository = repository
        self._hasher = hasher

    def __call__(
        self, password: SecretInputV1, *, correlation_id: str
    ) -> BootstrapAdministratorOutcomeV1:
        candidate = password.reveal_for_verification()
        if password_creation_error(candidate) is not None:
            return BootstrapAdministratorOutcomeV1("password_policy_violation", None)
        state_error = bootstrap_state_error(
            self._repository.initialization_state().state
        )
        if state_error is not None:
            return BootstrapAdministratorOutcomeV1(state_error, None)
        encoded = self._hasher.hash(candidate)
        return self._repository.claim_administrator(
            encoded, self._hasher.POLICY_VERSION, correlation_id
        )


class RecoverAdministratorPasswordV1:
    """Replace the verifier and invalidate all credentials in one repository UoW.

    Composition must first exclude the running service and validate the schema.
    This use case has no HTTP entry point or fallback credential.
    """

    def __init__(
        self,
        repository: IdentityAccessRecoveryRepositoryPortV1,
        hasher: PasswordHasherPortV1,
    ) -> None:
        self._repository = repository
        self._hasher = hasher

    def __call__(
        self, password: SecretInputV1, *, correlation_id: str
    ) -> RecoverAdministratorOutcomeV1:
        candidate = password.reveal_for_verification()
        if password_creation_error(candidate) is not None:
            return RecoverAdministratorOutcomeV1(
                "password_policy_violation", None, 0, 0
            )
        encoded = self._hasher.hash(candidate)
        return self._repository.recover_administrator(
            encoded, self._hasher.POLICY_VERSION, correlation_id
        )
