"""Fail-closed policy for credential-bound capacity writers."""


def require_capacity_fence(required: bool, fenced: bool) -> None:
    if required and not fenced:
        raise ValueError("capacity_credential_fence_required")
