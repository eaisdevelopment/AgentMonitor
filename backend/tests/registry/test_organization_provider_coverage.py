"""Pure owner-asserted coverage rules, independent of credentials or provider I/O."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_coverage_v1 import (
    OrganizationProviderCoverageV1,
    SetOrganizationProviderCoverageCommandV1,
)

NOW = datetime(2026, 11, 3, 12, tzinfo=UTC)


def _command() -> SetOrganizationProviderCoverageCommandV1:
    return SetOrganizationProviderCoverageCommandV1(
        organization_id=OpaqueIdV1("organization-a"),
        provider_key="ollama",
        outcome="account",
        account_id=OpaqueIdV1("account-a"),
        expected_account_record_version=1,
        unavailable_reason=None,
        expected_version=0,
        command_id=OpaqueIdV1("command-a"),
        principal_id=OpaqueIdV1("principal-a"),
        requested_at=NOW,
    )


def _record() -> OrganizationProviderCoverageV1:
    return OrganizationProviderCoverageV1(
        coverage_id=OpaqueIdV1("coverage-a"),
        organization_id=OpaqueIdV1("organization-a"),
        provider_key="ollama",
        outcome="account",
        account_id=OpaqueIdV1("account-a"),
        account_organization_id=OpaqueIdV1("organization-a"),
        unavailable_reason=None,
        provenance="owner_asserted",
        confirmed_by=OpaqueIdV1("principal-a"),
        confirmed_at=NOW,
        record_version=1,
        registry_revision=1,
        invalidated_at=None,
        invalidation_reason=None,
    )


def test_coverage_declaration_requires_an_account_or_explicit_unavailability() -> None:
    command = _command()
    with pytest.raises(ValueError, match="registry_coverage_command_invalid"):
        replace(command, account_id=None)
    with pytest.raises(ValueError, match="registry_coverage_command_invalid"):
        replace(command, unavailable_reason="subscription_unavailable")
    unavailable = replace(
        command,
        outcome="unavailable",
        account_id=None,
        expected_account_record_version=None,
        unavailable_reason="subscription_unavailable",
    )
    assert unavailable.account_id is None
    with pytest.raises(ValueError, match="registry_coverage_command_invalid"):
        replace(unavailable, account_id=command.account_id)
    with pytest.raises(ValueError, match="registry_coverage_command_invalid"):
        replace(unavailable, unavailable_reason=None)


def test_shared_coverage_preserves_owner_asserted_provenance() -> None:
    record = _record()
    with pytest.raises(ValueError, match="registry_coverage_record_invalid"):
        replace(record, outcome="shared")
    shared = replace(
        record,
        outcome="shared",
        account_organization_id=OpaqueIdV1("organization-b"),
    )
    assert shared.provenance == "owner_asserted"
    assert shared.account_id == record.account_id
    with pytest.raises(ValueError, match="registry_coverage_record_invalid"):
        replace(shared, outcome="account")


def test_invalidation_keeps_original_confirmation_and_cannot_be_partial() -> None:
    record = _record()
    invalidated = replace(
        record,
        invalidated_at=NOW + timedelta(minutes=1),
        invalidation_reason="account_archived",
    )
    assert invalidated.confirmed_at == record.confirmed_at
    assert invalidated.confirmed_by == record.confirmed_by
    with pytest.raises(ValueError, match="registry_coverage_record_invalid"):
        replace(invalidated, invalidated_at=None)
    with pytest.raises(ValueError, match="registry_coverage_record_invalid"):
        replace(invalidated, invalidation_reason=None)
    with pytest.raises(ValueError, match="registry_coverage_record_invalid"):
        replace(invalidated, invalidated_at=NOW - timedelta(minutes=1))


def test_command_uses_create_version_zero_and_rejects_negative_versions() -> None:
    command = _command()
    assert command.expected_version == 0
    with pytest.raises(ValueError, match="registry_coverage_command_invalid"):
        replace(command, expected_version=-1)
    with pytest.raises(ValueError, match="registry_coverage_record_invalid"):
        replace(_record(), record_version=0)


def test_missing_assertion_does_not_remove_an_intended_organization() -> None:
    from agentmonitor.contracts.registry_coverage_v1 import (
        OrganizationProviderCoverageSelectionV1,
        OrganizationProviderCoverageSnapshotV1,
    )

    selection = OrganizationProviderCoverageSelectionV1(
        organization_ids=(OpaqueIdV1("organization-a"), OpaqueIdV1("organization-b")),
        provider_key="ollama",
    )
    snapshot = OrganizationProviderCoverageSnapshotV1(
        selection=selection,
        items=(_record(),),
        registry_revision=1,
        completeness="complete",
        as_of=NOW,
    )
    assert len(snapshot.selection.organization_ids) == 2
    assert len(snapshot.items) == 1
    with pytest.raises(ValueError, match="registry_coverage_snapshot_invalid"):
        replace(snapshot, items=(_record(), _record()))
    with pytest.raises(ValueError, match="registry_coverage_snapshot_invalid"):
        replace(snapshot, completeness="unavailable")
    with pytest.raises(ValueError, match="registry_coverage_snapshot_invalid"):
        replace(snapshot, registry_revision=0)
    with pytest.raises(ValueError, match="registry_coverage_snapshot_invalid"):
        replace(snapshot, selection=replace(selection, provider_key="another-provider"))
    with pytest.raises(ValueError, match="registry_coverage_selection_invalid"):
        replace(selection, organization_ids=())


def test_unavailable_reason_cannot_be_arbitrary_text_or_provider_proof() -> None:
    command = _command()
    with pytest.raises(ValueError, match="registry_coverage_command_invalid"):
        replace(
            command,
            outcome="unavailable",
            account_id=None,
            expected_account_record_version=None,
            # Deliberately invalid owner input exercises the runtime refusal.
            unavailable_reason="unreviewed-free-text",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="unsupported-field-state"):
        # Deliberately invalid provenance must not become provider proof.
        replace(_record(), provenance="provider_verified")  # type: ignore[arg-type]


def test_shared_source_organization_must_be_a_typed_registry_reference() -> None:
    with pytest.raises(ValueError, match="registry_coverage_record_invalid"):
        replace(
            _record(),
            outcome="shared",
            account_organization_id="organization-b",  # type: ignore[arg-type]
        )


def test_snapshot_refuses_invalidation_after_its_observation_time() -> None:
    from agentmonitor.contracts.registry_coverage_v1 import (
        OrganizationProviderCoverageSelectionV1,
        OrganizationProviderCoverageSnapshotV1,
    )

    selection = OrganizationProviderCoverageSelectionV1(
        organization_ids=(OpaqueIdV1("organization-a"),),
        provider_key="ollama",
    )
    future = replace(
        _record(),
        invalidated_at=NOW + timedelta(hours=1),
        invalidation_reason="owner_revoked",
    )
    with pytest.raises(ValueError, match="registry_coverage_snapshot_invalid"):
        OrganizationProviderCoverageSnapshotV1(
            selection=selection,
            items=(future,),
            registry_revision=1,
            completeness="complete",
            as_of=NOW,
        )


def test_snapshot_items_follow_the_explicit_selection_order() -> None:
    from agentmonitor.contracts.registry_coverage_v1 import (
        OrganizationProviderCoverageSelectionV1,
        OrganizationProviderCoverageSnapshotV1,
    )

    first = _record()
    second = replace(
        first,
        coverage_id=OpaqueIdV1("coverage-b"),
        organization_id=OpaqueIdV1("organization-b"),
        outcome="shared",
    )
    selection = OrganizationProviderCoverageSelectionV1(
        organization_ids=(first.organization_id, second.organization_id),
        provider_key="ollama",
    )
    with pytest.raises(ValueError, match="registry_coverage_snapshot_invalid"):
        OrganizationProviderCoverageSnapshotV1(
            selection=selection,
            items=(second, first),
            registry_revision=1,
            completeness="complete",
            as_of=NOW,
        )


def test_snapshot_rejects_malformed_items_without_dereferencing_them() -> None:
    from agentmonitor.contracts.registry_coverage_v1 import (
        OrganizationProviderCoverageSelectionV1,
        OrganizationProviderCoverageSnapshotV1,
    )

    selection = OrganizationProviderCoverageSelectionV1(
        organization_ids=(OpaqueIdV1("organization-a"),), provider_key="ollama"
    )
    with pytest.raises(ValueError, match="registry_coverage_snapshot_invalid"):
        OrganizationProviderCoverageSnapshotV1(
            selection=selection,
            items=("not-a-record",),  # type: ignore[arg-type]
            registry_revision=1,
            completeness="complete",
            as_of=NOW,
        )


def test_transient_access_failure_is_not_a_lasting_invalidation_reason() -> None:
    with pytest.raises(ValueError, match="registry_coverage_record_invalid"):
        replace(
            _record(),
            invalidated_at=NOW,
            invalidation_reason="provider_unavailable",  # type: ignore[arg-type]
        )
