"""Pure disclosure policy; constructed receipts have no external boundary."""

from datetime import UTC, datetime, timedelta
from importlib import import_module
from types import ModuleType

import pytest
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1
from agentmonitor.contracts.configuration_v1 import (
    BootstrapConfigurationV1,
    ConfigurationDescriptorV1,
    ConfigurationRegistryV1,
)
from agentmonitor.contracts.database_v1 import SchemaCompatibilityV1
from agentmonitor.contracts.foundation_v1 import BuildMetadataV1
from agentmonitor.contracts.operations_v1 import VersionValueV1

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
SCHEMA = VersionValueV1("v1_0702", FieldAvailabilityV1("available"), "schema_port")


def diagnostics() -> ModuleType:
    return import_module("agentmonitor.modules.operations.domain.diagnostics")


def build() -> BuildMetadataV1:
    return BuildMetadataV1(
        "0.0.0",
        None,
        None,
        "omitted_for_reproducibility",
        SchemaCompatibilityV1(
            "v1_0702", "v1_0702", "v1_0702", "v1_0702", "v1_0702", "a" * 64
        ),
        None,
        None,
        None,
        (
            ("api", "0.0.0"),
            ("openapi", "3.1.0"),
            ("client", "2.0.4"),
            ("frontend", "0.0.0"),
        ),
    )


def test_declared_client_frontend_api_version_needs_actual_artifact_receipt() -> None:
    inventory = diagnostics().project_version_inventory_v1(
        build(), SCHEMA, (), as_of=NOW
    )
    assert inventory.application_version.value == "0.0.0"
    assert inventory.schema_version.value == "v1_0702"
    assert inventory.frontend_version.value is None
    assert inventory.client_version.value is None
    assert inventory.api_version.value is None
    assert inventory.availability.state == "partial"


def test_unknown_schema_is_not_copied_from_build_target() -> None:
    inventory = diagnostics().project_version_inventory_v1(
        build(),
        VersionValueV1(None, FieldAvailabilityV1("unavailable"), "schema_port"),
        (),
        as_of=NOW,
    )
    assert inventory.schema_version.value is None
    assert inventory.schema_version.availability.state == "unavailable"


def descriptor() -> ConfigurationDescriptorV1:
    return ConfigurationDescriptorV1(
        "AGENTMONITOR_DOMAIN_SECRET",
        "domain_secret",
        "M01",
        "secret",
        None,
        "nonempty",
        True,
        None,
        "agentmonitor",
        ("config_file",),
        "restart",
        "1.0.0",
        None,
        None,
        (),
        (),
        (),
    )


def test_only_registered_presence_is_projected_without_values() -> None:
    projected = diagnostics().project_configuration_presence_v1(
        BootstrapConfigurationV1(
            "1.0.0", ("M01",), (), (("AGENTMONITOR_DOMAIN_SECRET", True),)
        ),
        ConfigurationRegistryV1((descriptor(),)),
    )
    assert len(projected) == 1
    assert projected[0].presence == "configured"
    assert not hasattr(projected[0], "value")


def test_unregistered_presence_cannot_be_echoed() -> None:
    with pytest.raises(ValueError, match="operations_configuration_invalid"):
        diagnostics().project_configuration_presence_v1(
            BootstrapConfigurationV1(
                "1.0.0", ("M01",), (), (("AGENTMONITOR_ARBITRARY", True),)
            ),
            ConfigurationRegistryV1((descriptor(),)),
        )


def test_component_build_version_with_unknown_key_is_rejected() -> None:
    from dataclasses import replace

    with pytest.raises(ValueError, match="operations_version_invalid"):
        diagnostics().project_version_inventory_v1(
            replace(build(), component_versions=(("arbitrary_account_name", "1.0.0"),)),
            SCHEMA,
            (),
            as_of=NOW,
        )


def test_diagnostics_validity_does_not_extend_expired_health() -> None:
    assert diagnostics().diagnostic_valid_until_v1(
        NOW + timedelta(seconds=30), NOW - timedelta(seconds=1)
    ) == NOW - timedelta(seconds=1)
