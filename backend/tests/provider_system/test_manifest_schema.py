"""CTR-PROV-002 deterministic machine-readable schema artifact."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import fields
from pathlib import Path

from agentmonitor.contracts.common_v1 import FieldAvailabilityV1
from agentmonitor.contracts.provider_system_v1 import (
    AdapterDescriptorV1,
    CapabilityDeclarationV1,
    CapabilityManifestV1,
    CapabilitySchemaRangeV1,
    CapabilitySchemaVersionV1,
    CollectionConstraintV1,
    ProtocolVersionRangeV1,
    ProviderSourceV1,
    ProviderVersionRuleV1,
)

from tooling.provider_system.manifest_schema import (
    ARTIFACT_RELATIVE,
    build_schema,
    render_schema,
)

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "tooling/provider_system/manifest_schema.py"


def _definition(schema: dict[str, object], name: str) -> dict[str, object]:
    definitions = schema["$defs"]
    assert isinstance(definitions, dict)
    definition = definitions[name]
    assert isinstance(definition, dict)
    return definition


def test_generated_manifest_schema_is_exactly_reproducible() -> None:
    """CTR-PROV-002-SCHEMA-001: committed bytes equal deterministic output."""
    artifact = ROOT / ARTIFACT_RELATIVE
    assert artifact.read_bytes() == render_schema()
    completed = subprocess.run(
        [sys.executable, str(TOOL), "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert completed.stdout.strip().startswith("provider-manifest-schema: PASS ")
    assert completed.stderr == ""


def test_manifest_and_nested_records_are_closed_and_fully_required() -> None:
    """CTR-PROV-002-SCHEMA-002: unknown and missing fields fail structurally."""
    schema = build_schema()
    expected = {
        "CapabilityManifestV1": CapabilityManifestV1,
        "AdapterDescriptorV1": AdapterDescriptorV1,
        "CapabilityDeclarationV1": CapabilityDeclarationV1,
        "ProviderSourceV1": ProviderSourceV1,
        "CollectionConstraintV1": CollectionConstraintV1,
        "CapabilitySchemaRangeV1": CapabilitySchemaRangeV1,
        "CapabilitySchemaVersionV1": CapabilitySchemaVersionV1,
        "ProtocolVersionRangeV1": ProtocolVersionRangeV1,
        "ProviderVersionRuleV1": ProviderVersionRuleV1,
        "FieldAvailabilityV1": FieldAvailabilityV1,
    }
    for name, contract_type in expected.items():
        definition = _definition(schema, name)
        assert definition["additionalProperties"] is False
        assert definition["required"] == [item.name for item in fields(contract_type)]
        properties = definition["properties"]
        assert isinstance(properties, dict)
        assert set(properties) == {item.name for item in fields(contract_type)}


def test_schema_closes_decision_source_and_side_effect_vocabularies() -> None:
    """CTR-PROV-002-SCHEMA-003: material classifications are exact enums."""
    schema = build_schema()
    declaration = _definition(schema, "CapabilityDeclarationV1")
    declaration_properties = declaration["properties"]
    assert isinstance(declaration_properties, dict)
    assert declaration_properties["decision"] == {
        "enum": ["supported", "experimental", "deferred", "unsupported", "unknown"]
    }
    assert declaration_properties["side_effect_class"] == {
        "enum": ["read_only", "managed_profile_write", "unknown"]
    }
    assert declaration_properties["stability"] == {
        "enum": [
            "documented",
            "supported",
            "local_undocumented",
            "experimental",
            "unknown",
        ]
    }

    provider_source = _definition(schema, "ProviderSourceV1")
    source_properties = provider_source["properties"]
    assert isinstance(source_properties, dict)
    assert source_properties["source_class"] == {
        "enum": [
            "documented_api",
            "supported_cli",
            "approved_local_metadata",
            "experimental_private_or_browser",
        ]
    }
    version_rule = _definition(schema, "ProviderVersionRuleV1")
    version_properties = version_rule["properties"]
    assert isinstance(version_properties, dict)
    assert version_properties["scheme"] == {
        "enum": ["opaque_exact", "semantic_exact", "date_exact"]
    }

    availability = _definition(schema, "FieldAvailabilityV1")
    availability_properties = availability["properties"]
    assert isinstance(availability_properties, dict)
    assert availability_properties["state"] == {
        "enum": [
            "available",
            "missing",
            "null",
            "unknown",
            "unsupported",
            "unavailable",
            "not_applicable",
            "withheld_or_denied",
            "stale",
            "unresolved",
        ]
    }


def test_schema_has_fail_closed_identifiers_ranges_and_mapping_digest() -> None:
    """CTR-PROV-002-SCHEMA-004: key bounds are machine-readable."""
    schema = build_schema()
    manifest = _definition(schema, "CapabilityManifestV1")
    manifest_properties = manifest["properties"]
    assert isinstance(manifest_properties, dict)
    assert manifest_properties["m0_mapping_digest"] == {
        "type": "string",
        "pattern": "^[0-9a-f]{64}$",
    }

    declaration = _definition(schema, "CapabilityDeclarationV1")
    declaration_properties = declaration["properties"]
    assert isinstance(declaration_properties, dict)
    assert declaration_properties["capability_id"] == {
        "type": "string",
        "pattern": "^[a-z][a-z0-9]*(?:\\.[a-z][a-z0-9]*){1,5}$",
    }
    sources = declaration_properties["sources"]
    assert isinstance(sources, dict)
    assert sources["uniqueItems"] is True
    assert sources["maxItems"] == 64

    constraints = _definition(schema, "CollectionConstraintV1")
    constraint_properties = constraints["properties"]
    assert isinstance(constraint_properties, dict)
    assert constraint_properties["deadline_ms"] == {
        "type": "integer",
        "minimum": 1,
        "maximum": 600_000,
    }
    assert constraint_properties["maximum_concurrency"] == {
        "type": "integer",
        "minimum": 1,
        "maximum": 64,
    }


def test_schema_explicitly_binds_python_semantic_authority() -> None:
    """CTR-PROV-002-SCHEMA-005: structural validation is not semantic approval."""
    schema = build_schema()
    assert schema["x-agentmonitor-contract"] == {
        "contractId": "CTR-PROV-002",
        "contractVersion": CapabilityManifestV1.CONTRACT_VERSION,
        "pythonType": (
            "agentmonitor.contracts.provider_system_v1.CapabilityManifestV1"
        ),
        "semanticAuthority": (
            "CapabilityManifestV1 and nested V1 __post_init__ invariants"
        ),
        "validationOrder": [
            "validate this structural schema",
            "construct the published Python V1 contract",
            "apply approved M0 mapping and runtime compatibility policy",
        ],
    }
    semantic = schema["x-agentmonitor-semantic-invariants"]
    assert isinstance(semantic, list)
    assert "cross-field declaration decision consistency" in semantic
    assert "exact approved M0 mapping digest equality" in semantic


def test_check_detects_real_file_drift_without_rewriting_it(tmp_path: Path) -> None:
    """CTR-PROV-002-SCHEMA-006: check mode is read-only and fail-closed."""
    write = subprocess.run(
        [sys.executable, str(TOOL), "--root", str(tmp_path), "--write"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert write.returncode == 0
    artifact = tmp_path / ARTIFACT_RELATIVE
    generated = artifact.read_bytes()
    artifact.write_bytes(generated + b"{}")
    drifted = artifact.read_bytes()

    check = subprocess.run(
        [sys.executable, str(TOOL), "--root", str(tmp_path), "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert check.returncode == 1
    assert check.stdout.strip() == "provider-manifest-schema: FAIL generated_drift"
    assert check.stderr == ""
    assert artifact.read_bytes() == drifted
    assert json.loads(generated)["$id"] == (
        "urn:agentmonitor:contract:provider-system:capability-manifest:v1"
    )
