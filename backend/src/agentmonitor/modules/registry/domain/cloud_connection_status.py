"""Pure, fail-closed presentation policy for owner-asserted cloud access."""

from agentmonitor.contracts.registry_v1 import CredentialConnectionStateV1


def derive_connection_status(
    binding_present: bool,
    verified: bool,
    job_state: str | None,
    job_reason: str | None,
    gate_state: str,
    ready: bool,
) -> tuple[CredentialConnectionStateV1, bool]:
    """Never infer provider identity or offer a retry against an uncertain gate."""
    if not binding_present:
        return "not_configured", False
    if not ready:
        return "unavailable", False
    if verified:
        return "access_valid_owner_confirmed", False
    if gate_state == "unresolved":
        return "unavailable", False
    if job_state in {"queued", "claimed", "admitted"}:
        return "pending", False
    if job_state not in {None, "terminal"}:
        return "unavailable", False
    can_verify = ready and gate_state == "ready"
    reasons: dict[str, CredentialConnectionStateV1] = {
        "last_check_stale": "stale",
        "transient_failure": "retry_available",
        "unauthorized": "unauthorized",
        "rate_limited": "rate_limited",
        "authorization_unavailable": "authorization_unavailable",
        "store_unavailable": "authorization_unavailable",
    }
    state: CredentialConnectionStateV1 = reasons.get(job_reason or "", "pending")
    if gate_state not in {"ready", "not_due", "busy"}:
        return "unavailable", False
    if state == "rate_limited" and can_verify:
        return "retry_available", True
    return state, can_verify
