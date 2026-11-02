"""Atomic V2 Ollama verification enqueue across one SQLite transaction."""

from sqlalchemy.engine import Connection

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.collection_control.sqlite.ollama_cloud_admission import (  # noqa: E501
    OllamaCloudAdmissionRepositoryErrorV1,
    SqliteOllamaCloudAdmissionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    CredentialBindingRepositoryErrorV1,
    ensure_cloud_verification_enqueue_authority_in_transaction,
)
from agentmonitor.contracts.collection_control_v1 import (
    OllamaCloudVerificationEnqueueV1,
    OllamaCloudVerificationEnqueueV2,
    OllamaCloudVerificationJobViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1


class _BoundAtomicOllamaCloudVerificationEnqueueV2(
    SqliteOllamaCloudAdmissionRepositoryV1
):
    """One-call transaction owner with immutable M02 authority facts."""

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
        request: OllamaCloudVerificationEnqueueV1,
        *,
        profile_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
    ) -> None:
        if (
            not isinstance(request, OllamaCloudVerificationEnqueueV2)
            or request.account_id != self._binding.account_id
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


class SqliteOllamaCloudVerificationEnqueueRepositoryV2:
    """Narrow V2 adapter; no SQL connection crosses its public boundary."""

    def __init__(self, reference: DatabaseRefV1) -> None:
        self._reference = reference

    def enqueue_verification_v2(
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
