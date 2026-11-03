"""Owner-declared relationships remain separate from access and pool identity."""

from agentmonitor.modules.registry.domain.coverage import coverage_reference_failure


def test_own_and_shared_relationships_require_the_recorded_primary_group() -> None:
    common = dict(
        organization_active=True,
        provider_active=True,
        account_present=True,
        account_archived=False,
        provider_matches=True,
        source_organization_active=True,
    )
    assert (
        coverage_reference_failure(
            outcome="account",
            organization_id="org-a",
            account_organization_id="org-a",
            recorded_account_organization_id="org-a",
            **common,
        )
        is None
    )
    assert (
        coverage_reference_failure(
            outcome="shared",
            organization_id="org-b",
            account_organization_id="org-a",
            recorded_account_organization_id="org-a",
            **common,
        )
        is None
    )
    assert (
        coverage_reference_failure(
            outcome="shared",
            organization_id="org-b",
            account_organization_id="org-b",
            recorded_account_organization_id="org-a",
            **common,
        )
        == "account_reassigned"
    )


def test_unavailable_is_an_owner_disposition_without_an_account() -> None:
    assert (
        coverage_reference_failure(
            outcome="unavailable",
            organization_id="org-a",
            account_organization_id=None,
            recorded_account_organization_id=None,
            organization_active=True,
            provider_active=True,
            account_present=False,
            account_archived=False,
            provider_matches=False,
            source_organization_active=False,
        )
        is None
    )


def test_withdrawn_provider_cannot_leave_coverage_current() -> None:
    assert (
        coverage_reference_failure(
            outcome="unavailable",
            organization_id="org-a",
            account_organization_id=None,
            recorded_account_organization_id=None,
            organization_active=True,
            provider_active=False,
            account_present=False,
            account_archived=False,
            provider_matches=False,
            source_organization_active=False,
        )
        == "provider_withdrawn"
    )
