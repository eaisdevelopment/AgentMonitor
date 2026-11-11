"""M02 billing metadata eligibility, independent of provider access."""

from agentmonitor.contracts.registry_billing_v1 import BillingCredentialStatusV1
from agentmonitor.contracts.registry_v1 import CredentialBindingAggregateV1


def billing_credential_status(
    aggregate: CredentialBindingAggregateV1,
) -> BillingCredentialStatusV1:
    """Project local lifecycle records without consulting credential contents."""
    active = next(
        (item.generation for item in aggregate.bindings if item.lifecycle == "active"),
        None,
    )
    pending = next(
        (item.generation for item in aggregate.bindings if item.lifecycle == "pending"),
        None,
    )
    cleanup = any(item.lifecycle == "cleanup_pending" for item in aggregate.bindings)
    return BillingCredentialStatusV1(
        state=(
            "pending"
            if pending is not None
            else "stored"
            if active is not None
            else "cleanup_required"
            if cleanup
            else "missing"
        ),
        active_generation=active,
        pending_generation=pending,
        cleanup_required=cleanup,
    )


def billing_connection_eligibility(
    provider: str, lifecycle: str, exists: bool
) -> tuple[bool, str]:
    """Metadata policy only; eligibility is not provider-access evidence."""
    if lifecycle not in {"pending", "active"}:
        return False, "account_unavailable"
    if exists:
        return False, "billing_connection_exists"
    if provider == "ollama":
        return False, "existing_cloud_connection_required"
    if provider not in {"claude", "codex"}:
        return False, "provider_unsupported"
    return True, "billing_connection_available"
