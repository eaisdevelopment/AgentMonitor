"""Safe wire models for M04 collection-run queries."""

from datetime import datetime
from typing import Literal

from agentmonitor.api.v1.schemas.registry import AvailabilityV1, PageMetaV1
from pydantic import BaseModel, ConfigDict


class _ClosedV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CollectionRunViewV1(_ClosedV1):
    run_id: str
    schedule_id: str
    provider_key: str
    account_id: str | None
    resource_id: str | None
    capability_id: str
    state: Literal[
        "requested",
        "queued",
        "running",
        "committing",
        "succeeded",
        "partial",
        "failed",
        "blocked",
        "cancelled",
        "unsupported",
    ]
    source_id: str
    adapter_version: str
    provider_version: str | None
    target_generation: int
    fencing_token: int
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    deadline_at: datetime
    duration_ms: int | None
    outcome_code: str | None
    error_code: str | None
    observation_ids: tuple[str, ...]


class CollectionRunPageV1(_ClosedV1):
    items: tuple[CollectionRunViewV1, ...]
    page: PageMetaV1
    availability: AvailabilityV1
