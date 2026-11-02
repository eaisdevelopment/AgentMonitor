"""M03-owned closed, ephemeral local model catalog contract."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Literal, Protocol

from agentmonitor.contracts.common_v1 import TechnicalValueV1


@dataclass(frozen=True, slots=True)
class LocalCatalogItemV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-OLLAMA-LOCAL-CATALOG-001"
    OWNER: ClassVar[str] = "PLAN-M03"
    name: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not isinstance(self.name, str)
            or not self.name
            or len(self.name) > 256
            or len(self.name.encode("utf-8")) > 512
            or not self.name.isprintable()
        ):
            raise ValueError("catalog_model_name_invalid")


@dataclass(frozen=True, slots=True)
class LocalCatalogSnapshotV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-OLLAMA-LOCAL-CATALOG-001"
    OWNER: ClassVar[str] = "PLAN-M03"
    state: Literal["available", "unavailable"]
    reason: Literal[
        "source_available",
        "source_unavailable",
        "invalid_provider_data",
        "unverified_provider_version",
        "collection_in_progress",
        "operation_deadline_exceeded",
    ]
    observed_at: datetime | None
    items: tuple[LocalCatalogItemV1, ...] | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            (self.state == "available") != (self.items is not None)
            or (self.state == "available") != (self.reason == "source_available")
            or (self.state == "available" and self.observed_at is None)
            or (self.items is not None and len(self.items) > 1024)
            or (
                self.items is not None
                and any(type(i) is not LocalCatalogItemV1 for i in self.items)
            )
            or (
                self.items is not None
                and len({item.name for item in self.items}) != len(self.items)
            )
        ):
            raise ValueError("catalog_snapshot_state_invalid")


@dataclass(frozen=True, slots=True)
class LocalCatalogViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-OLLAMA-LOCAL-CATALOG-001"
    OWNER: ClassVar[str] = "PLAN-M03"
    outcome: Literal[
        "success",
        "partial",
        "provider_unavailable",
        "unverified_provider_version",
        "invalid_provider_data",
        "deadline_exceeded",
    ]
    daemon_version: str | None
    source: Literal["ollama.local.catalog.v1"]
    observed_at: datetime
    installed: LocalCatalogSnapshotV1
    loaded: LocalCatalogSnapshotV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not isinstance(self.observed_at, datetime):
            raise ValueError("catalog_outcome_invalid")
        count = sum(
            snapshot.state == "available" for snapshot in (self.installed, self.loaded)
        )
        if (
            (self.outcome == "success" and count != 2)
            or (self.outcome == "partial" and count != 1)
            or (self.outcome not in {"success", "partial"} and count != 0)
            or (count > 0 and not self.daemon_version)
            or (
                self.outcome == "unverified_provider_version"
                and any(
                    snapshot.reason != "unverified_provider_version"
                    for snapshot in (self.installed, self.loaded)
                )
            )
            or (
                self.outcome == "provider_unavailable"
                and any(
                    snapshot.reason
                    not in {"source_unavailable", "collection_in_progress"}
                    for snapshot in (self.installed, self.loaded)
                )
            )
            or (
                self.outcome == "deadline_exceeded"
                and any(
                    snapshot.reason != "operation_deadline_exceeded"
                    for snapshot in (self.installed, self.loaded)
                )
            )
            or (
                self.outcome == "invalid_provider_data"
                and not any(
                    snapshot.reason == "invalid_provider_data"
                    for snapshot in (self.installed, self.loaded)
                )
            )
        ):
            raise ValueError("catalog_outcome_invalid")


class LocalCatalogPortV1(Protocol):
    def __call__(self) -> LocalCatalogViewV1: ...
