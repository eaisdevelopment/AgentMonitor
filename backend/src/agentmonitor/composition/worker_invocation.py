"""Pure validation of manager invocation metadata; never grants worker authority."""


def checked_worker_invocation(
    properties: dict[str, str], *, allow_pending: bool = False
) -> str:
    invocation = properties.get("InvocationID", "")
    if (
        allow_pending
        and properties.get("InvocationID") == ""
        and properties.get("LoadState") == "loaded"
        and properties.get("ActiveState") == "inactive"
        and properties.get("ControlGroup") == ""
    ):
        return ""
    if len(invocation) != 32 or any(c not in "0123456789abcdef" for c in invocation):
        raise ValueError("ollama_cloud_unit_identity_invalid")
    return invocation
