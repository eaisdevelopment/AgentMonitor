"""Fail-closed policy for Ollama cloud capacity writes."""


def require_capacity_fence(provider_key: str, fenced: bool) -> None:
    if provider_key == "ollama" and not fenced:
        raise ValueError("ollama_credential_fence_required")
