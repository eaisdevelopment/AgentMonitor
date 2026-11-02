"""Connect the local provider adapter to the M03 catalog contract."""

from agentmonitor.adapters.providers.ollama.local_catalog.source import (
    read_local_catalog,
)
from agentmonitor.contracts.ollama_local_catalog_v1 import (
    LocalCatalogItemV1,
    LocalCatalogSnapshotV1,
    LocalCatalogViewV1,
)


def read_ollama_local_catalog_v1() -> LocalCatalogViewV1:
    observed = read_local_catalog()
    installed = LocalCatalogSnapshotV1(
        observed.installed_state,
        observed.installed_reason,
        observed.installed_observed_at,
        tuple(LocalCatalogItemV1(item.name) for item in observed.installed)
        if observed.installed is not None
        else None,
    )
    loaded = LocalCatalogSnapshotV1(
        observed.loaded_state,
        observed.loaded_reason,
        observed.loaded_observed_at,
        tuple(LocalCatalogItemV1(item.name) for item in observed.loaded)
        if observed.loaded is not None
        else None,
    )
    return LocalCatalogViewV1(
        observed.outcome,
        observed.daemon_version,
        "ollama.local.catalog.v1",
        observed.observed_at,
        installed,
        loaded,
    )
