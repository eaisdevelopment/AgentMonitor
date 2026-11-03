"""Pure current-reference policy for owner-declared organizational coverage."""

from agentmonitor.contracts.registry_coverage_v1 import (
    CoverageInvalidationReasonV1,
    CoverageOutcomeV1,
)


def coverage_reference_failure(
    *,
    outcome: CoverageOutcomeV1,
    organization_id: str,
    account_organization_id: str | None,
    recorded_account_organization_id: str | None,
    organization_active: bool,
    provider_active: bool,
    account_present: bool,
    account_archived: bool,
    provider_matches: bool,
    source_organization_active: bool,
) -> CoverageInvalidationReasonV1 | None:
    if not organization_active:
        return "organization_archived"
    if not provider_active:
        return "provider_withdrawn"
    if outcome == "unavailable":
        return None
    if not account_present or account_archived:
        return "account_archived"
    if not provider_matches:
        return "provider_withdrawn"
    if (
        account_organization_id is None
        or account_organization_id != recorded_account_organization_id
        or (outcome == "account") != (account_organization_id == organization_id)
    ):
        return "account_reassigned"
    if not source_organization_active:
        return "source_organization_archived"
    return None
