"""M02 organizational coverage use cases through CTR-REG-013."""

from agentmonitor.contracts.registry_coverage_v1 import (
    OrganizationProviderCoverageReadPortV1,
    OrganizationProviderCoverageSelectionV1,
    OrganizationProviderCoverageSnapshotV1,
    OrganizationProviderCoverageV1,
    OrganizationProviderCoverageWritePortV1,
    RevokeOrganizationProviderCoverageCommandV1,
    SetOrganizationProviderCoverageCommandV1,
)


class ReadOrganizationProviderCoverageV1:
    def __init__(self, repository: OrganizationProviderCoverageReadPortV1) -> None:
        self._repository = repository

    def __call__(
        self, selection: OrganizationProviderCoverageSelectionV1
    ) -> OrganizationProviderCoverageSnapshotV1:
        return self._repository.read_coverage(selection)


class SetOrganizationProviderCoverageV1:
    def __init__(self, repository: OrganizationProviderCoverageWritePortV1) -> None:
        self._repository = repository

    def __call__(
        self, command: SetOrganizationProviderCoverageCommandV1
    ) -> OrganizationProviderCoverageV1:
        return self._repository.set_coverage(command)


class RevokeOrganizationProviderCoverageV1:
    def __init__(self, repository: OrganizationProviderCoverageWritePortV1) -> None:
        self._repository = repository

    def __call__(
        self, command: RevokeOrganizationProviderCoverageCommandV1
    ) -> OrganizationProviderCoverageV1:
        return self._repository.revoke_coverage(command)
