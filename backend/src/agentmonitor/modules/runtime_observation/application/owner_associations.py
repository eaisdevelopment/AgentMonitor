"""M06 owner-confirmed associations; no provider identity or process control."""

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import AccountViewV1
from agentmonitor.contracts.runtime_observation_v1 import (
    LiveProcessLocationsV1,
    LiveProcessLocationV1,
    OwnerProcessAccountAssociationV1,
    ProcessIdentityV1,
)
from agentmonitor.modules.runtime_observation.application.ports import (
    OwnerAssociationErrorV1,
    OwnerAssociationRepositoryV1,
    owner_association_key,
)


def transition_owner_association(
    identity: ProcessIdentityV1,
    provider_key: str,
    account_id: OpaqueIdV1 | None,
    current: OwnerProcessAccountAssociationV1 | None,
    expected_version: int,
    principal_id: OpaqueIdV1,
    confirmed_at: datetime,
    executable_identity: str | None = None,
) -> OwnerProcessAccountAssociationV1:
    version = current.record_version if current is not None else 0
    if current is not None and current.identity != identity:
        raise OwnerAssociationErrorV1("process_identity_conflict")
    if (
        current is not None
        and current.account_id == account_id
        and current.provider_key == provider_key
        and current.executable_identity == executable_identity
        and expected_version in {version, version - 1}
    ):
        return current
    if type(expected_version) is not int or expected_version != version:
        raise OwnerAssociationErrorV1("precondition_failed")
    return OwnerProcessAccountAssociationV1(
        identity,
        provider_key,
        account_id,
        principal_id,
        confirmed_at,
        version + 1,
        executable_identity,
    )


class OwnerProcessAccountAssociationsV1:
    """Join only current guarded processes to explicit owner settings."""

    def __init__(
        self,
        reader: Callable[[], LiveProcessLocationsV1],
        repository: OwnerAssociationRepositoryV1,
        account_lookup: Callable[[OpaqueIdV1], AccountViewV1 | None],
    ) -> None:
        self._reader = reader
        self._repository = repository
        self._account_lookup = account_lookup

    def _eligible(self, account_id: OpaqueIdV1, provider_key: str) -> bool:
        try:
            account = self._account_lookup(account_id)
        except ValueError:
            return False
        except RuntimeError:
            raise OwnerAssociationErrorV1(
                "observation_repository_unavailable"
            ) from None
        return (
            account is not None
            and account.lifecycle == "active"
            and account.provider_key == provider_key
        )

    def read(self, account_id: OpaqueIdV1 | None = None) -> LiveProcessLocationsV1:
        observed = self._reader()
        records = self._repository.records()
        items = []
        for item in observed.items:
            key = owner_association_key(
                item.identity,
                item.snapshot.executable_identity
                if item.snapshot is not None
                else None,
            )
            record = records.get(key)
            association = None
            if (
                record is not None
                and record.account_id is not None
                and record.identity == item.identity
                and record.provider_key == item.provider_key
                and item.snapshot is not None
                and record.executable_identity == item.snapshot.executable_identity
                and self._eligible(record.account_id, item.provider_key)
            ):
                association = record
            if account_id is not None and (
                association is None or association.account_id != account_id
            ):
                continue
            items.append(
                replace(
                    item,
                    association_key=key,
                    association_record_version=record.record_version if record else 0,
                    account_association=association,
                )
            )
        return replace(observed, items=tuple(items))

    def set(
        self,
        key: str,
        account_id: OpaqueIdV1 | None,
        expected_version: int,
        principal_id: OpaqueIdV1,
        confirmed_at: datetime,
    ) -> LiveProcessLocationV1:
        selected: LiveProcessLocationV1 | None = None

        def transition(
            current: OwnerProcessAccountAssociationV1 | None,
        ) -> OwnerProcessAccountAssociationV1:
            nonlocal selected
            observed = self._reader()
            if observed.availability.state != "available":
                raise OwnerAssociationErrorV1("observation_data_unavailable")
            selected = next(
                (
                    item
                    for item in observed.items
                    if item.snapshot is not None
                    and owner_association_key(
                        item.identity, item.snapshot.executable_identity
                    )
                    == key
                ),
                None,
            )
            if (
                selected is None
                or selected.snapshot is None
                or selected.snapshot.executable_identity is None
            ):
                raise OwnerAssociationErrorV1("runtime_subject_not_found")
            if account_id is not None and not self._eligible(
                account_id, selected.provider_key
            ):
                raise OwnerAssociationErrorV1("registry_monitoring_not_eligible")
            return transition_owner_association(
                selected.identity,
                selected.provider_key,
                account_id,
                current,
                expected_version,
                principal_id,
                confirmed_at,
                selected.snapshot.executable_identity,
            )

        record = self._repository.update(key, transition)
        if selected is None:
            raise OwnerAssociationErrorV1("runtime_subject_not_found")
        return replace(
            selected,
            association_key=key,
            association_record_version=record.record_version,
            account_association=record if record.account_id is not None else None,
        )
