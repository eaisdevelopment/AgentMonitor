"""Pure allowlist projections of published build/configuration/version receipts."""

import re
from datetime import datetime
from typing import Literal

from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, QueryAvailabilityV1
from agentmonitor.contracts.configuration_v1 import (
    BootstrapConfigurationV1,
    ConfigurationRegistryV1,
)
from agentmonitor.contracts.foundation_v1 import BuildMetadataV1
from agentmonitor.contracts.operations_v1 import (
    COMPONENT_KEYS_V1,
    ComponentHealthResultV1,
    ComponentVersionV1,
    ConfigurationPresenceV1,
    InvalidOperationsContractV1,
    VersionInventoryV1,
    VersionValueV1,
)

VersionSourceV1 = Literal[
    "application_manifest",
    "build_manifest",
    "schema_port",
    "adapter_manifest",
    "generated_artifact",
]


def _value(
    value: str | None,
    source: VersionSourceV1,
    artifact_hash: str | None = None,
    *,
    require_artifact: bool = False,
) -> VersionValueV1:
    if require_artifact and (
        artifact_hash is None or not re.fullmatch(r"[a-f0-9]{64}", artifact_hash)
    ):
        value = None
    return VersionValueV1(
        value,
        FieldAvailabilityV1("available" if value is not None else "unknown"),
        source,
    )


def project_version_inventory_v1(
    build: BuildMetadataV1,
    schema: VersionValueV1,
    components: tuple[ComponentHealthResultV1, ...],
    *,
    as_of: datetime,
) -> VersionInventoryV1:
    """Never substitute a migration target, application version or filename."""
    metadata = dict(build.component_versions)
    if (
        len(metadata) != len(build.component_versions)
        or not metadata.keys()
        <= COMPONENT_KEYS_V1 | {"api", "openapi", "client", "frontend"}
        or schema.source != "schema_port"
    ):
        raise InvalidOperationsContractV1("operations_version_invalid")
    component_versions = {
        key: _value(value, "build_manifest")
        for key, value in metadata.items()
        if key in COMPONENT_KEYS_V1
    }
    for result in components:
        if result.sample is not None and result.sample.component_version is not None:
            component_versions[result.component_key] = _value(
                result.sample.component_version, "adapter_manifest"
            )
    application = _value(build.application_version, "application_manifest")
    api = _value(
        metadata.get("api"),
        "generated_artifact",
        build.openapi_hash,
        require_artifact=True,
    )
    openapi = _value(
        metadata.get("openapi"),
        "generated_artifact",
        build.openapi_hash,
        require_artifact=True,
    )
    client = _value(
        metadata.get("client"),
        "generated_artifact",
        build.client_hash,
        require_artifact=True,
    )
    frontend = _value(
        metadata.get("frontend"),
        "build_manifest",
        build.frontend_hash,
        require_artifact=True,
    )
    complete = all(
        item.availability.state == "available"
        for item in (application, schema, api, openapi, client, frontend)
    )
    return VersionInventoryV1(
        application,
        schema,
        api,
        openapi,
        client,
        frontend,
        tuple(
            ComponentVersionV1(key, value)
            for key, value in sorted(component_versions.items())
        ),
        QueryAvailabilityV1(
            "available" if complete else "partial",
            "operations_diagnostics_complete"
            if complete
            else "operations_version_unknown",
            as_of,
        ),
    )


def project_configuration_presence_v1(
    receipt: BootstrapConfigurationV1, registry: ConfigurationRegistryV1
) -> tuple[ConfigurationPresenceV1, ...]:
    """Select registered presence only; runtime setting values are never inputs."""
    registered = {item.external_name: item for item in registry.descriptors}
    secret = dict(receipt.secret_presence)
    non_secret = dict(receipt.non_secret_sources)
    if (
        len(registered) != len(registry.descriptors)
        or len(secret) != len(receipt.secret_presence)
        or len(non_secret) != len(receipt.non_secret_sources)
        or not (secret.keys() | non_secret.keys()) <= registered.keys()
        or secret.keys() & non_secret.keys()
        or any(type(value) is not bool for value in secret.values())
    ):
        raise InvalidOperationsContractV1("operations_configuration_invalid")
    result: list[ConfigurationPresenceV1] = []
    for key, descriptor in sorted(registered.items()):
        presence: Literal["configured", "missing", "invalid", "unknown"]
        if descriptor.secret_class in {"provider", "development"}:
            if key in secret or key in non_secret:
                raise InvalidOperationsContractV1("operations_configuration_invalid")
            continue
        if descriptor.secret_class == "agentmonitor":
            if key in non_secret:
                raise InvalidOperationsContractV1("operations_configuration_invalid")
            presence = "configured" if secret.get(key, False) else "missing"
        else:
            if key in secret:
                raise InvalidOperationsContractV1("operations_configuration_invalid")
            presence = "configured" if key in non_secret else "missing"
        result.append(ConfigurationPresenceV1(key, descriptor.owner, presence))
    return tuple(result)


def diagnostic_valid_until_v1(*validity: datetime) -> datetime:
    """Use the oldest evidence deadline, including already-expired evidence."""
    return min(validity)
