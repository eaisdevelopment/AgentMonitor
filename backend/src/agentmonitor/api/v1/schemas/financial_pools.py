"""Owner pool configuration wire types; credential lineage stays inside M02."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FinancialPoolViewV1(_Closed):
    pool_id: str
    provider_key: Literal["claude", "codex", "ollama"]
    selector: Literal["billing", "self", "team"]
    display_name: str
    primary_organization_id: str | None
    record_version: int
    registry_revision: int
    created_at: datetime
    updated_at: datetime


class FinancialPoolConfigurationV1(_Closed):
    account_id: str
    resource_id: str
    selector: Literal["billing", "self", "team"]
    provider_scope_id: str | None
    scope_evidence: Literal["unresolved", "owner_asserted", "provider_verified"] | None
    scope_generation: int | None
    pool: FinancialPoolViewV1 | None
    association_evidence: Literal["owner_asserted", "provider_verified"] | None
    can_assign: bool
    registry_revision: int
    reason_code: str


class FinancialPoolPageV1(_Closed):
    items: tuple[FinancialPoolViewV1, ...]
    next_pool_id: str | None
    registry_revision: int


class AssignFinancialPoolInputV1(_Closed):
    action: Literal["create", "join", "unlink"]
    pool_id: str | None = Field(
        default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"
    )
    primary_organization_id: str | None = Field(
        default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"
    )


class EditFinancialPoolInputV1(_Closed):
    expected_record_version: int = Field(strict=True, ge=1)
    primary_organization_id: str | None = Field(
        min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"
    )
