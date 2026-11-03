"""Closed wire representations for owner-declared provider coverage."""

from datetime import datetime
from typing import Literal

from agentmonitor.contracts.registry_coverage_v1 import (
    CoverageInvalidationReasonV1,
    CoverageOutcomeV1,
    CoverageUnavailableReasonV1,
)
from pydantic import BaseModel, ConfigDict, Field


class SetOrganizationCoverageInputV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome: CoverageOutcomeV1
    account_id: str | None = Field(default=None, min_length=1, max_length=256)
    expected_account_record_version: int | None = Field(default=None, ge=1, strict=True)
    unavailable_reason: CoverageUnavailableReasonV1 | None = None


class OrganizationCoverageWireV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    coverage_id: str
    organization_id: str
    provider_key: str
    outcome: CoverageOutcomeV1
    account_id: str | None
    account_organization_id: str | None
    unavailable_reason: CoverageUnavailableReasonV1 | None
    provenance: Literal["owner_asserted"]
    confirmed_at: datetime
    record_version: int
    registry_revision: int
    invalidated_at: datetime | None
    invalidation_reason: CoverageInvalidationReasonV1 | None


class OrganizationCoverageResourceV1(BaseModel):
    """Missing declaration is explicit and carries a create-only version zero."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    organization_id: str
    provider_key: str
    coverage: OrganizationCoverageWireV1 | None
    registry_revision: int
    as_of: datetime


class OrganizationCoverageSnapshotWireV1(BaseModel):
    """One bounded ordered selection, including organizations without a declaration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    organization_ids: tuple[str, ...]
    provider_key: str
    items: tuple[OrganizationCoverageWireV1, ...]
    completeness: Literal["complete", "unavailable"]
    registry_revision: int
    as_of: datetime
