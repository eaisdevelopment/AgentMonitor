"""Route the provider-neutral dashboard connection port by registry ownership."""

from collections.abc import Callable, Mapping
from typing import ClassVar

from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    ProviderConnectionErrorV1,
    ProviderConnectionPortV1,
    ProviderConnectionViewV1,
    StartProviderConnectionCommandV1,
    VerifiedQuotaIdentityV1,
)
from agentmonitor.modules.registry.application.accounts import GetAccountV1


class ProviderDashboardConnectionsV1:
    """Dispatch one account only to the service for its registered provider."""

    CONTRACT_ID: ClassVar[str] = "CTR-PROV-007"
    OWNER: ClassVar[str] = "PLAN-INT"

    def __init__(
        self,
        get_account: GetAccountV1,
        services: Mapping[str, ProviderConnectionPortV1],
    ) -> None:
        if not services or any(not key for key in services):
            raise ValueError("provider_connection_services_invalid")
        self._get_account = get_account
        self._services = dict(services)

    def _service(self, account_id: OpaqueIdV1) -> ProviderConnectionPortV1:
        account = self._get_account(account_id)
        if account is None:
            raise ProviderConnectionErrorV1("registry_subject_not_found")
        service = self._services.get(account.provider_key)
        if service is None:
            raise ProviderConnectionErrorV1("provider_connection_not_eligible")
        return service

    def read(self, account_id: OpaqueIdV1) -> ProviderConnectionViewV1:
        return self._service(account_id).read(account_id)

    def start(
        self, command: StartProviderConnectionCommandV1
    ) -> ProviderConnectionViewV1:
        return self._service(command.account_id).start(command)

    def cancel(
        self, account_id: OpaqueIdV1, flow_id: OpaqueIdV1
    ) -> ProviderConnectionViewV1:
        return self._service(account_id).cancel(account_id, flow_id)


class ProviderVerifiedQuotaIdentitiesV1:
    """Read only the current-process identity receipt for the account provider."""

    def __init__(
        self,
        get_account: GetAccountV1,
        readers: Mapping[str, Callable[[OpaqueIdV1], VerifiedQuotaIdentityV1 | None]],
    ) -> None:
        self._get_account = get_account
        self._readers = dict(readers)

    def __call__(self, account_id: OpaqueIdV1) -> VerifiedQuotaIdentityV1 | None:
        account = self._get_account(account_id)
        if account is None:
            return None
        reader = self._readers.get(account.provider_key)
        return None if reader is None else reader(account_id)
