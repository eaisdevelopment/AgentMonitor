"""Atomic Ollama verification initiation across M02 and M04 persistence."""

from datetime import datetime, timedelta
from typing import ClassVar

from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.ollama_cloud_admission import (  # noqa: E501
    OllamaCloudAdmissionRepositoryErrorV1,
    SqliteOllamaCloudAdmissionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    CredentialBindingRepositoryErrorV1,
    ensure_cloud_verification_enqueue_authority_in_transaction,
    reconcile_access_target_in_transaction,
    resolve_active_credential_binding_in_transaction,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    account_credential_lock,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    RegistryRepositoryErrorV1,
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.verification_run import (
    cloud_schedule_target_digest,
)
from agentmonitor.contracts.collection_control_v1 import (
    OllamaCloudVerificationEnqueueV2,
    OllamaCloudVerificationJobViewV1,
    OllamaCloudVerificationReplayQueryV1,
    OllamaCloudVerificationTargetV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    AssertCredentialAccountOwnershipCommandV1,
    ProviderTargetRefV1,
)
from agentmonitor.modules.registry.application.organizations import (
    RegistryCommandConflictV1,
)


class _BoundAtomicOllamaCloudVerificationEnqueueV2(
    SqliteOllamaCloudAdmissionRepositoryV1
):
    """Private transaction participant with immutable typed M02 facts.

    The raw SQLite connection is confined to this integration adapter and the
    two persistence participants. It never crosses the public application port.
    """

    def __init__(
        self,
        reference: DatabaseRefV1,
        *,
        authority_account_record_version: int,
        binding: ActiveCredentialBindingRefV1,
        expected_manifest_fingerprint: str,
    ) -> None:
        super().__init__(reference)
        self._authority_account_record_version = authority_account_record_version
        self._binding = binding
        self._expected_manifest_fingerprint = expected_manifest_fingerprint

    def _fence_new_verification_job(
        self,
        connection: Connection,
        request: OllamaCloudVerificationEnqueueV2,
        *,
        profile_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
    ) -> None:
        if (
            request.account_id != self._binding.account_id
            or request.binding_generation != self._binding.generation
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_verification_authority_unavailable"
            )
        try:
            ensure_cloud_verification_enqueue_authority_in_transaction(
                connection,
                account_id=request.account_id,
                expected_account_record_version=(
                    self._authority_account_record_version
                ),
                profile_id=profile_id,
                resource_id=resource_id,
                access_target_id=request.access_target_id,
                binding=self._binding,
                expected_manifest_fingerprint=(self._expected_manifest_fingerprint),
            )
        except CredentialBindingRepositoryErrorV1 as error:
            code = (
                "ollama_cloud_verification_account_version_conflict"
                if str(error) == "credential_binding_account_version_conflict"
                else "ollama_cloud_verification_authority_unavailable"
            )
            raise OllamaCloudAdmissionRepositoryErrorV1(code) from None


class SqliteAtomicOllamaCloudVerificationEnqueueRepositoryV2:
    """Integration-owned port implementation; callers pass typed values only."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-010"
    CONTRACT_VERSION: ClassVar[str] = "2.0.0"
    OWNER: ClassVar[str] = "PLAN-M04"

    def __init__(self, reference: DatabaseRefV1) -> None:
        self._reference = reference

    def enqueue_verification_atomically_v2(
        self,
        request: OllamaCloudVerificationEnqueueV2,
        authority_account_record_version: int,
        binding: ActiveCredentialBindingRefV1,
        expected_manifest_fingerprint: str,
    ) -> OllamaCloudVerificationJobViewV1:
        if (
            not isinstance(request, OllamaCloudVerificationEnqueueV2)
            or type(authority_account_record_version) is not int
            or authority_account_record_version < 1
            or not isinstance(binding, ActiveCredentialBindingRefV1)
            or type(expected_manifest_fingerprint) is not str
            or len(expected_manifest_fingerprint) != 64
            or any(
                character not in "0123456789abcdef"
                for character in expected_manifest_fingerprint
            )
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_verification_authority_unavailable"
            ) from None
        return _BoundAtomicOllamaCloudVerificationEnqueueV2(
            self._reference,
            authority_account_record_version=authority_account_record_version,
            binding=binding,
            expected_manifest_fingerprint=expected_manifest_fingerprint,
        ).enqueue_verification(request)

    def initiate_verification_atomically_v2(
        self,
        query: OllamaCloudVerificationReplayQueryV1,
        requested_at: datetime,
        expected_manifest_fingerprint: str,
    ) -> OllamaCloudVerificationJobViewV1:
        """Replay first, then derive and write all new work in one transaction."""
        if (
            not isinstance(query, OllamaCloudVerificationReplayQueryV1)
            or not isinstance(requested_at, datetime)
            or requested_at.utcoffset() != timedelta(0)
            or type(expected_manifest_fingerprint) is not str
            or len(expected_manifest_fingerprint) != 64
            or any(
                character not in "0123456789abcdef"
                for character in expected_manifest_fingerprint
            )
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_verification_authority_unavailable"
            ) from None
        base = SqliteOllamaCloudAdmissionRepositoryV1(self._reference)
        registry = SqliteRegistryRepositoryV1(self._reference)
        try:
            with open_sqlite_database(self._reference, "runtime_read_write") as handle:
                with handle.connect() as connection:
                    # The SQLite writer serialization makes a concurrent caller
                    # observe the first job before it needs the account lock.
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    replay = base._replay_verification_in_transaction(connection, query)
                    if replay is not None:
                        connection.rollback()
                        return replay
                    # Rotation takes this lock before its DB transaction. This
                    # acquisition is non-blocking, so the inverse order cannot
                    # deadlock; a real rotation remains a temporary busy result.
                    with account_credential_lock(self._reference, query.account_id):
                        target = reconcile_access_target_in_transaction(
                            connection,
                            provider_key="ollama",
                            authority_id="ollama.com",
                            manifest_fingerprint=expected_manifest_fingerprint,
                            as_of=requested_at,
                        )
                        binding = resolve_active_credential_binding_in_transaction(
                            connection, query.account_id
                        )
                        if binding is None:
                            raise OllamaCloudAdmissionRepositoryErrorV1(
                                "ollama_cloud_verification_authority_unavailable"
                            )
                        account, graph, authority_version = (
                            registry._prepare_cloud_verification_graph_in_transaction(
                                connection,
                                AssertCredentialAccountOwnershipCommandV1(
                                    query.idempotency_key,
                                    query.principal_id,
                                    query.account_id,
                                    target.access_target_id,
                                    query.expected_account_record_version,
                                    binding,
                                    requested_at,
                                ),
                            )
                        )
                        if (
                            account.account_id != query.account_id
                            or graph.account_id != query.account_id
                            or graph.access_target_id != target.access_target_id
                            or graph.binding != binding
                            or graph.lifecycle != "active"
                            or graph.identity_state != "owner_confirmed"
                        ):
                            raise OllamaCloudAdmissionRepositoryErrorV1(
                                "ollama_cloud_verification_authority_unavailable"
                            )
                        digest = cloud_schedule_target_digest(graph)
                        schedule_id = OpaqueIdV1("ollama-cloud-" + digest[:40])
                        request = OllamaCloudVerificationEnqueueV2(
                            idempotency_key=query.idempotency_key,
                            principal_id=query.principal_id,
                            schedule_id=schedule_id,
                            account_id=query.account_id,
                            access_target_id=target.access_target_id,
                            binding_generation=binding.generation,
                            requested_at=requested_at,
                            expected_account_record_version=(
                                query.expected_account_record_version
                            ),
                        )
                        bound = _BoundAtomicOllamaCloudVerificationEnqueueV2(
                            self._reference,
                            authority_account_record_version=authority_version,
                            binding=binding,
                            expected_manifest_fingerprint=(
                                expected_manifest_fingerprint
                            ),
                        )
                        bound._register_verification_target_in_transaction(
                            connection,
                            OllamaCloudVerificationTargetV1(
                                schedule_id,
                                query.account_id,
                                graph.profile_id,
                                graph.resource_id,
                                ProviderTargetRefV1(
                                    "cloud_service", target.access_target_id
                                ),
                                digest,
                                binding.generation,
                                requested_at,
                            ),
                        )
                        result = bound._enqueue_new_verification_in_transaction(
                            connection, request
                        )
                        connection.commit()
                        return result
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except RegistryCommandConflictV1 as error:
            code = {
                "registry_account_version_conflict": (
                    "ollama_cloud_verification_account_version_conflict"
                ),
                "registry_idempotency_conflict": (
                    "ollama_cloud_verification_idempotency_conflict"
                ),
            }.get(str(error), "ollama_cloud_verification_authority_unavailable")
            raise OllamaCloudAdmissionRepositoryErrorV1(code) from None
        except (
            CredentialBindingRepositoryErrorV1,
            RegistryRepositoryErrorV1,
            SqlitePolicyError,
            SQLAlchemyError,
            OSError,
            TypeError,
            ValueError,
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_verification_authority_unavailable"
            ) from None
