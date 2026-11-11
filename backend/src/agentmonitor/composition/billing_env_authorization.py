"""Physical provider-bound credential readers for the dedicated billing worker only.

Composition resolves a current active M02 binding/generation before issuance.
This object validates inherited physical capabilities, not registry lifecycle.
It has no provider selector, URL, transport or request authority.
"""

import os
from collections.abc import Generator

from agentmonitor.adapters.credential_env.format import credential_variable_name
from agentmonitor.adapters.credential_env.stream import (
    ENV_STREAM_CHUNK_BYTES,
    read_credential_value_stream,
)
from agentmonitor.adapters.providers.claude.anthropic_api.source import (
    AnthropicCostAuthorizationSinkV1,
)
from agentmonitor.adapters.providers.codex.openai_api.source import (
    OpenAICostAuthorizationSinkV1,
)
from agentmonitor.adapters.providers.ollama.api.source import (
    OllamaUsageAuthorizationSinkV1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.credential_lock import (
    validated_credential_lock_descriptor,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_capability import (
    InheritedEnvCredentialFileV1,
    validated_inherited_env_file_v1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import InheritedAccountCredentialLockV1


class AnthropicEnvAuthorizationUnavailable(ValueError):
    """A fixed safe failure; never include descriptor, file or credential detail."""

    def __init__(self) -> None:
        super().__init__("anthropic_cost_authorization_unavailable")


def _bounded_chunks(
    descriptor: int, count: list[int]
) -> Generator[bytearray, None, None]:
    while True:
        chunk = bytearray(ENV_STREAM_CHUNK_BYTES)
        try:
            used = os.readv(descriptor, [chunk])
            if used == 0:
                return
            del chunk[used:]
            count[0] += used
            yield chunk
        finally:
            chunk[:] = b"\0" * len(chunk)


class AnthropicEnvAuthorizationV1:
    """Apply one Claude binding's key exclusively to the exact A01 header sink."""

    __slots__ = (
        "_account_id",
        "_credential_file",
        "_credential_lock",
        "_variable_name",
    )

    def __init__(
        self,
        binding_id: str,
        account_id: OpaqueIdV1,
        credential_lock: InheritedAccountCredentialLockV1,
        credential_file: InheritedEnvCredentialFileV1,
    ) -> None:
        try:
            variable_name = credential_variable_name(binding_id, provider_key="claude")
            if (
                type(account_id) is not OpaqueIdV1
                or type(credential_lock) is not InheritedAccountCredentialLockV1
                or type(credential_file) is not InheritedEnvCredentialFileV1
            ):
                raise AnthropicEnvAuthorizationUnavailable()
            validated_credential_lock_descriptor(credential_lock, account_id)
            validated_inherited_env_file_v1(credential_file)
        except TimeoutError:
            raise
        except Exception:
            raise AnthropicEnvAuthorizationUnavailable() from None
        self._account_id = account_id
        self._credential_lock = credential_lock
        self._credential_file = credential_file
        self._variable_name = variable_name

    def authorize(self, sink: AnthropicCostAuthorizationSinkV1) -> None:
        """Revalidate, stream, apply and wipe inside the supervised worker request."""
        if type(sink) is not AnthropicCostAuthorizationSinkV1:
            raise AnthropicEnvAuthorizationUnavailable() from None
        token: bytearray | None = None
        read_count = [0]
        try:
            validated_credential_lock_descriptor(
                self._credential_lock, self._account_id
            )
            descriptor = validated_inherited_env_file_v1(self._credential_file)
            expected_size = self._credential_file.descriptor_identity()[3]
            os.lseek(descriptor, 0, os.SEEK_SET)
            chunks = _bounded_chunks(descriptor, read_count)
            try:
                token = read_credential_value_stream(chunks, self._variable_name)
            finally:
                chunks.close()
            if read_count[0] != expected_size:
                raise AnthropicEnvAuthorizationUnavailable()
            validated_inherited_env_file_v1(self._credential_file)
            validated_credential_lock_descriptor(
                self._credential_lock, self._account_id
            )
            sink.put_api_key(token)
        except TimeoutError:
            raise
        except Exception:
            raise AnthropicEnvAuthorizationUnavailable() from None
        finally:
            if token is not None:
                token[:] = b"\0" * len(token)


class OpenAIEnvAuthorizationUnavailable(ValueError):
    """A fixed safe failure; never include descriptor, file or credential detail."""

    def __init__(self) -> None:
        super().__init__("openai_cost_authorization_unavailable")


class OpenAIEnvAuthorizationV1:
    """Apply one OpenAI binding exclusively to the exact A02 header sink."""

    __slots__ = (
        "_account_id",
        "_credential_file",
        "_credential_lock",
        "_variable_name",
    )

    def __init__(
        self,
        binding_id: str,
        account_id: OpaqueIdV1,
        credential_lock: InheritedAccountCredentialLockV1,
        credential_file: InheritedEnvCredentialFileV1,
    ) -> None:
        try:
            variable_name = credential_variable_name(binding_id, provider_key="codex")
            if (
                type(account_id) is not OpaqueIdV1
                or type(credential_lock) is not InheritedAccountCredentialLockV1
                or type(credential_file) is not InheritedEnvCredentialFileV1
            ):
                raise OpenAIEnvAuthorizationUnavailable()
            validated_credential_lock_descriptor(credential_lock, account_id)
            validated_inherited_env_file_v1(credential_file)
        except TimeoutError:
            raise
        except Exception:
            raise OpenAIEnvAuthorizationUnavailable() from None
        self._account_id = account_id
        self._credential_lock = credential_lock
        self._credential_file = credential_file
        self._variable_name = variable_name

    def authorize(self, sink: OpenAICostAuthorizationSinkV1) -> None:
        """Revalidate, stream, apply and wipe inside the supervised worker request."""
        if type(sink) is not OpenAICostAuthorizationSinkV1:
            raise OpenAIEnvAuthorizationUnavailable() from None
        token: bytearray | None = None
        read_count = [0]
        try:
            validated_credential_lock_descriptor(
                self._credential_lock, self._account_id
            )
            descriptor = validated_inherited_env_file_v1(self._credential_file)
            expected_size = self._credential_file.descriptor_identity()[3]
            os.lseek(descriptor, 0, os.SEEK_SET)
            chunks = _bounded_chunks(descriptor, read_count)
            try:
                token = read_credential_value_stream(chunks, self._variable_name)
            finally:
                chunks.close()
            if read_count[0] != expected_size:
                raise OpenAIEnvAuthorizationUnavailable()
            validated_inherited_env_file_v1(self._credential_file)
            validated_credential_lock_descriptor(
                self._credential_lock, self._account_id
            )
            sink.put_api_key(token)
        except TimeoutError:
            raise
        except Exception:
            raise OpenAIEnvAuthorizationUnavailable() from None
        finally:
            if token is not None:
                token[:] = b"\0" * len(token)


class OllamaUsageEnvAuthorizationUnavailable(ValueError):
    """A fixed safe failure; never include descriptor, file or credential detail."""

    def __init__(self) -> None:
        super().__init__("ollama_usage_authorization_unavailable")


class OllamaUsageEnvAuthorizationV1:
    """Apply one existing Ollama binding exclusively to the A03 usage sink."""

    __slots__ = (
        "_account_id",
        "_credential_file",
        "_credential_lock",
        "_variable_name",
    )

    def __init__(
        self,
        binding_id: str,
        account_id: OpaqueIdV1,
        credential_lock: InheritedAccountCredentialLockV1,
        credential_file: InheritedEnvCredentialFileV1,
    ) -> None:
        try:
            variable_name = credential_variable_name(binding_id, provider_key="ollama")
            if (
                type(account_id) is not OpaqueIdV1
                or type(credential_lock) is not InheritedAccountCredentialLockV1
                or type(credential_file) is not InheritedEnvCredentialFileV1
            ):
                raise OllamaUsageEnvAuthorizationUnavailable()
            validated_credential_lock_descriptor(credential_lock, account_id)
            validated_inherited_env_file_v1(credential_file)
        except TimeoutError:
            raise
        except Exception:
            raise OllamaUsageEnvAuthorizationUnavailable() from None
        self._account_id = account_id
        self._credential_lock = credential_lock
        self._credential_file = credential_file
        self._variable_name = variable_name

    def authorize(self, sink: OllamaUsageAuthorizationSinkV1) -> None:
        """Revalidate, stream, apply and wipe inside the supervised worker request."""
        if type(sink) is not OllamaUsageAuthorizationSinkV1:
            raise OllamaUsageEnvAuthorizationUnavailable() from None
        token: bytearray | None = None
        read_count = [0]
        try:
            validated_credential_lock_descriptor(
                self._credential_lock, self._account_id
            )
            descriptor = validated_inherited_env_file_v1(self._credential_file)
            expected_size = self._credential_file.descriptor_identity()[3]
            os.lseek(descriptor, 0, os.SEEK_SET)
            chunks = _bounded_chunks(descriptor, read_count)
            try:
                token = read_credential_value_stream(chunks, self._variable_name)
            finally:
                chunks.close()
            if read_count[0] != expected_size:
                raise OllamaUsageEnvAuthorizationUnavailable()
            validated_inherited_env_file_v1(self._credential_file)
            validated_credential_lock_descriptor(
                self._credential_lock, self._account_id
            )
            sink.put_bearer_token(token)
        except TimeoutError:
            raise
        except Exception:
            raise OllamaUsageEnvAuthorizationUnavailable() from None
        finally:
            if token is not None:
                token[:] = b"\0" * len(token)
