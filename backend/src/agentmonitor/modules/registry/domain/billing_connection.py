"""M02 billing metadata eligibility, independent of provider access."""


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
