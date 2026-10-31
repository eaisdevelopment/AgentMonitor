"""Generate/check the versioned CTR-PROV-002 structural JSON Schema."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from dataclasses import fields
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_SOURCE = REPOSITORY_ROOT / "backend/src"
if str(BACKEND_SOURCE) not in sys.path:
    sys.path.insert(0, str(BACKEND_SOURCE))

from agentmonitor.contracts.common_v1 import FieldAvailabilityV1  # noqa: E402
from agentmonitor.contracts.provider_system_v1 import (  # noqa: E402
    MAX_PROVIDER_OPERATION_DEADLINE_MS,
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

ARTIFACT_RELATIVE = Path("contracts/provider-system/capability-manifest-v1.schema.json")
SEMVER_PATTERN = r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
CAPABILITY_PATTERN = r"^[a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*){1,5}$"
DIGEST_PATTERN = r"^[0-9a-f]{64}$"


def _token() -> dict[str, object]:
    return {"type": "string", "minLength": 1, "maxLength": 128}


def _nullable_token() -> dict[str, object]:
    return {"anyOf": [_token(), {"type": "null"}]}


def _reference(name: str) -> dict[str, object]:
    return {"$ref": f"#/$defs/{name}"}


def _array(
    items: dict[str, object],
    *,
    minimum: int = 0,
    maximum: int = 64,
    unique: bool = True,
) -> dict[str, object]:
    return {
        "type": "array",
        "items": items,
        "minItems": minimum,
        "maxItems": maximum,
        "uniqueItems": unique,
    }


def _closed_object(
    contract_type: Any,
    properties: dict[str, object],
    *,
    semantic_comment: str,
    all_of: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    names = [item.name for item in fields(contract_type)]
    if set(names) != set(properties):
        raise RuntimeError(f"schema_field_drift:{contract_type.__name__}")
    schema: dict[str, object] = {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": names,
        "$comment": semantic_comment,
    }
    if all_of is not None:
        schema["allOf"] = all_of
    return schema


def _definitions() -> dict[str, object]:
    stability = {
        "enum": [
            "documented",
            "supported",
            "local_undocumented",
            "experimental",
            "unknown",
        ]
    }
    side_effect = {"enum": ["read_only", "managed_profile_write", "unknown"]}
    source_class = {
        "enum": [
            "documented_api",
            "supported_cli",
            "approved_local_metadata",
            "experimental_private_or_browser",
        ]
    }
    availability = _closed_object(
        FieldAvailabilityV1,
        {
            "state": {
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
        },
        semantic_comment="CTR-COMMON-007 V1 Python invariants remain normative.",
    )
    schema_version = _closed_object(
        CapabilitySchemaVersionV1,
        {
            "major": {"type": "integer", "minimum": 1},
            "minor": {"type": "integer", "minimum": 0},
        },
        semantic_comment=(
            "Major/minor relationship is enforced by the V1 Python contract."
        ),
    )
    schema_range = _closed_object(
        CapabilitySchemaRangeV1,
        {
            "minimum": _reference("CapabilitySchemaVersionV1"),
            "maximum": _reference("CapabilitySchemaVersionV1"),
        },
        semantic_comment=(
            "Range ordering and same-major policy are semantic invariants."
        ),
    )
    protocol_range = _closed_object(
        ProtocolVersionRangeV1,
        {
            "minimum": {"type": "string", "pattern": SEMVER_PATTERN},
            "maximum": {"type": "string", "pattern": SEMVER_PATTERN},
        },
        semantic_comment=(
            "Protocol ordering and compatible-major policy are semantic invariants."
        ),
    )
    descriptor = _closed_object(
        AdapterDescriptorV1,
        {
            "adapter_id": _token(),
            "adapter_version": {"type": "string", "pattern": SEMVER_PATTERN},
            "provider_key": _token(),
            "protocol_versions": _reference("ProtocolVersionRangeV1"),
            "build_identity": _token(),
        },
        semantic_comment=(
            "Adapter identity invariants are enforced by AdapterDescriptorV1."
        ),
    )
    version_rule = _closed_object(
        ProviderVersionRuleV1,
        {
            "rule_id": _token(),
            "scheme": {"enum": ["opaque_exact", "semantic_exact", "date_exact"]},
            "verified_versions": _array(_token(), minimum=1),
        },
        semantic_comment=(
            "Exact membership and scheme-specific parsing are semantic invariants."
        ),
    )
    constraints = _closed_object(
        CollectionConstraintV1,
        {
            "deadline_ms": {
                "type": "integer",
                "minimum": 1,
                "maximum": MAX_PROVIDER_OPERATION_DEADLINE_MS,
            },
            "minimum_interval_ms": {"type": "integer", "minimum": 0},
            "maximum_concurrency": {
                "type": "integer",
                "minimum": 1,
                "maximum": 64,
            },
            "automatic_retry_count": {
                "type": "integer",
                "minimum": 0,
                "maximum": 10,
            },
            "provider_request_count": {
                "anyOf": [
                    {"type": "integer", "minimum": 0},
                    {"type": "null"},
                ]
            },
            "provider_request_count_availability": _reference("FieldAvailabilityV1"),
        },
        semantic_comment=(
            "Count/availability pairing is enforced by CollectionConstraintV1."
        ),
    )
    source = _closed_object(
        ProviderSourceV1,
        {
            "source_id": _token(),
            "provider_key": _token(),
            "capability_id": {"type": "string", "pattern": CAPABILITY_PATTERN},
            "source_class": source_class,
            "stability": stability,
            "mechanism_version": _token(),
            "credential_role": _token(),
            "side_effect_class": side_effect,
            "evidence_reference": _token(),
            "is_experimental": {"type": "boolean"},
        },
        semantic_comment=(
            "Source/provider/capability and experimental pairing are semantic "
            "invariants."
        ),
        all_of=[
            {
                "if": {
                    "properties": {
                        "source_class": {"const": "experimental_private_or_browser"}
                    },
                    "required": ["source_class"],
                },
                "then": {"properties": {"is_experimental": {"const": True}}},
                "else": {"properties": {"is_experimental": {"const": False}}},
            }
        ],
    )
    declaration = _closed_object(
        CapabilityDeclarationV1,
        {
            "capability_id": {"type": "string", "pattern": CAPABILITY_PATTERN},
            "schema_versions": _reference("CapabilitySchemaRangeV1"),
            "decision": {
                "enum": [
                    "supported",
                    "experimental",
                    "deferred",
                    "unsupported",
                    "unknown",
                ]
            },
            "stability": stability,
            "reason_code": _token(),
            "evidence_reference": _token(),
            "port_type": _nullable_token(),
            "output_schema": _nullable_token(),
            "sources": _array(_reference("ProviderSourceV1")),
            "provider_version_rule": _reference("ProviderVersionRuleV1"),
            "constraints": _reference("CollectionConstraintV1"),
            "side_effect_class": side_effect,
            "platforms": _array(_token(), minimum=1),
        },
        semantic_comment=(
            "Cross-field scope, decision, and evidence invariants require Python "
            "validation."
        ),
        all_of=[
            {
                "if": {
                    "properties": {"decision": {"enum": ["supported", "experimental"]}},
                    "required": ["decision"],
                },
                "then": {
                    "properties": {
                        "port_type": _token(),
                        "output_schema": _token(),
                        "sources": _array(_reference("ProviderSourceV1"), minimum=1),
                    }
                },
                "else": {
                    "properties": {
                        "port_type": {"type": "null"},
                        "output_schema": {"type": "null"},
                        "sources": _array(_reference("ProviderSourceV1"), maximum=0),
                    }
                },
            }
        ],
    )
    manifest = _closed_object(
        CapabilityManifestV1,
        {
            "descriptor": _reference("AdapterDescriptorV1"),
            "manifest_schema_version": {
                "type": "string",
                "pattern": SEMVER_PATTERN,
            },
            "declarations": _array(_reference("CapabilityDeclarationV1"), minimum=1),
            "m0_mapping_id": _token(),
            "m0_mapping_version": {
                "type": "string",
                "pattern": SEMVER_PATTERN,
            },
            "m0_mapping_digest": {"type": "string", "pattern": DIGEST_PATTERN},
        },
        semantic_comment=(
            "Provider scope, uniqueness, and exact M0 binding require Python "
            "validation."
        ),
    )
    return {
        "AdapterDescriptorV1": descriptor,
        "CapabilityDeclarationV1": declaration,
        "CapabilityManifestV1": manifest,
        "CapabilitySchemaRangeV1": schema_range,
        "CapabilitySchemaVersionV1": schema_version,
        "CollectionConstraintV1": constraints,
        "FieldAvailabilityV1": availability,
        "ProtocolVersionRangeV1": protocol_range,
        "ProviderSourceV1": source,
        "ProviderVersionRuleV1": version_rule,
    }


def build_schema() -> dict[str, object]:
    """Return the deterministic structural schema for CTR-PROV-002 V1."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:agentmonitor:contract:provider-system:capability-manifest:v1",
        "title": "AgentMonitor CapabilityManifestV1",
        "description": (
            "Closed structural schema for CTR-PROV-002 V1. The published Python "
            "contract remains authoritative for cross-field semantic invariants."
        ),
        "$ref": "#/$defs/CapabilityManifestV1",
        "$defs": _definitions(),
        "x-agentmonitor-contract": {
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
        },
        "x-agentmonitor-semantic-invariants": [
            "range ordering and compatible protocol/schema majors",
            "cross-field declaration decision consistency",
            "provider/capability/source scope equality and uniqueness",
            "provider request count and availability pairing",
            "exact approved M0 mapping digest equality",
        ],
    }


def render_schema() -> bytes:
    """Render canonical UTF-8 JSON with stable keys and one terminal newline."""
    return (
        json.dumps(build_schema(), indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("utf-8")


def _write(root: Path, rendered: bytes) -> None:
    target = root / ARTIFACT_RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        raise OSError("artifact_symlink_forbidden")
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=target.parent, prefix=f".{target.name}.", delete=False
        ) as temporary:
            temporary.write(rendered)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        os.chmod(temporary_name, 0o644)
        os.replace(temporary_name, target)
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    options = parser.parse_args(arguments)

    rendered = render_schema()
    digest = hashlib.sha256(rendered).hexdigest()
    target = options.root.resolve() / ARTIFACT_RELATIVE
    try:
        if options.write:
            _write(options.root.resolve(), rendered)
            print(f"provider-manifest-schema: WROTE sha256={digest}")
            return 0
        if target.is_symlink():
            print("provider-manifest-schema: FAIL artifact_symlink_forbidden")
            return 1
        if not target.is_file():
            print("provider-manifest-schema: FAIL generated_missing")
            return 1
        if target.read_bytes() != rendered:
            print("provider-manifest-schema: FAIL generated_drift")
            return 1
    except OSError:
        print("provider-manifest-schema: FAIL artifact_io_error")
        return 1
    print(f"provider-manifest-schema: PASS sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
