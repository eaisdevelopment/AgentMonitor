"""Authorized Ollama schedule snapshot behind one read transaction."""

from sqlalchemy.exc import SQLAlchemyError

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.cloud_schedule_status import (  # noqa: E501
    SqliteCloudScheduleStatusV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    CredentialBindingRepositoryErrorV1,
    ensure_cloud_verification_enqueue_authority_in_transaction,
)
from agentmonitor.contracts.cloud_schedule_status_v1 import CloudScheduleStatusV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1


class OllamaCloudScheduleSnapshotErrorV1(ValueError):
    """Closed schedule-authority read failure."""

    def __init__(self) -> None:
        super().__init__("ollama_cloud_schedule_snapshot_unavailable")


class SqliteOllamaCloudScheduleSnapshotRepositoryV1:
    """Read M02 authority and M04 schedule facts in one owned transaction."""

    def __init__(self, reference: DatabaseRefV1) -> None:
        self._reference = reference
        self._schedules = SqliteCloudScheduleStatusV1(reference)

    def read_authorized_snapshot(
        self,
        target: CloudScheduleStatusV1,
        account_record_version: int,
        binding: ActiveCredentialBindingRefV1,
        expected_manifest_fingerprint: str,
    ) -> tuple[bool, bool, str | None]:
        try:
            with open_sqlite_database(self._reference, "runtime_read_only") as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN")
                    ensure_cloud_verification_enqueue_authority_in_transaction(
                        connection,
                        account_id=binding.account_id,
                        expected_account_record_version=account_record_version,
                        profile_id=OpaqueIdV1(target.profile_id),
                        resource_id=OpaqueIdV1(target.resource_id),
                        access_target_id=OpaqueIdV1(target.access_target_id),
                        binding=binding,
                        expected_manifest_fingerprint=expected_manifest_fingerprint,
                    )
                    return self._schedules.read_snapshot(
                        connection, target, expected_manifest_fingerprint
                    )
        except (
            CredentialBindingRepositoryErrorV1,
            SQLAlchemyError,
            SqlitePolicyError,
            OSError,
            TypeError,
            ValueError,
        ):
            raise OllamaCloudScheduleSnapshotErrorV1() from None
