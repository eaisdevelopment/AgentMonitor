"""CTR-FND-005 repository-owned M1 OpenAPI/strict TypeScript generation.

Canonical command: backend/.venv/bin/python tooling/foundation/openapi_client.py
Use --check for read-only drift verification. Only the fixed production schema
factory and the two allocated outputs are permitted. No third-party generator,
provider startup, dynamic plugin import, timestamps or host paths are emitted.

This admitted M1 compiler handles the empty foundation operation set. It refuses
new operations until P01 publishes schemas and the generator is extended with
their real client/server tests. It must never invent an operation to fill a client.
Validation is for this constrained OpenAPI 3.1 subset, not a general OAS validator.
Replacements are atomic per file, staged together, with rollback on write errors;
cross-directory crash atomicity is not claimed. --check detects interrupted pairs.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

FACTORY_REF = "agentmonitor.composition.bootstrap:create_schema_application"
GENERATOR_VERSION = "1.0.0"
OPENAPI_RELATIVE = Path("contracts/openapi/agentmonitor-v1.json")
CLIENT_RELATIVE = Path("frontend/src/generated/api/index.ts")
METHODS = frozenset(
    {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
)
SOURCE_FILES = (
    "backend/pyproject.toml",
    "backend/src/agentmonitor/api/app.py",
    "backend/src/agentmonitor/api/v1/router.py",
    "backend/src/agentmonitor/foundation/application.py",
    "backend/src/agentmonitor/foundation/configuration.py",
    "backend/src/agentmonitor/foundation/observability.py",
    "backend/src/agentmonitor/composition/bootstrap.py",
    "backend/src/agentmonitor/contracts/common_v1.py",
    "backend/src/agentmonitor/contracts/configuration_v1.py",
    "backend/src/agentmonitor/contracts/foundation_v1.py",
    "backend/src/agentmonitor/contracts/database_v1.py",
    "backend/src/agentmonitor/adapters/persistence/_shared/sqlite/core/policy.py",
    "backend/src/agentmonitor/adapters/persistence/_shared/sqlite/schema/compatibility.py",
    "backend/migrations/catalog.toml",
    "backend/migrations/env.py",
    "backend/migrations/versions/v1_0000_fnd_anchor.py",
)


class OpenApiGenerationError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class OpenApiGenerationReceiptV1:
    source_hash: str
    openapi_hash: str
    client_hash: str
    generator_hash: str
    generator_name: str
    generator_version: str
    api_major: int
    compatibility: Literal["compatible", "breaking", "not_checked"]
    operation_count: int


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise OpenApiGenerationError("schema_invalid")
    return {key: item for key, item in value.items()}


def validate_openapi(document: object) -> tuple[str, ...]:
    """Validate version, versioned paths, unique operation IDs and responses."""
    schema = _object(document)
    if schema.get("openapi") != "3.1.0":
        raise OpenApiGenerationError("openapi_version_unsupported")
    info = _object(schema.get("info"))
    version = info.get("version")
    if (
        info.get("title") != "AgentMonitor"
        or not isinstance(version, str)
        or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None
    ):
        raise OpenApiGenerationError("api_version_invalid")
    ids: list[str] = []
    for path, item in _object(schema.get("paths")).items():
        if not path.startswith("/api/v1/") or any(char in path for char in "?#\\"):
            raise OpenApiGenerationError("unversioned_path")
        for method, raw_operation in _object(item).items():
            if method not in METHODS:
                raise OpenApiGenerationError("path_item_unsupported")
            operation = _object(raw_operation)
            identifier = operation.get("operationId")
            if (
                not isinstance(identifier, str)
                or re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,95}", identifier) is None
            ):
                raise OpenApiGenerationError("operation_id_invalid")
            if identifier in ids:
                raise OpenApiGenerationError("operation_id_duplicate")
            ids.append(identifier)
            responses = _object(operation.get("responses"))
            if not responses or any(
                not _object(value).get("description") for value in responses.values()
            ):
                raise OpenApiGenerationError("responses_invalid")
    return tuple(sorted(ids))


def classify_compatibility(
    previous: object, current: object
) -> Literal["compatible", "breaking"]:
    """Conservative V1 diff: removals/changes to any old operation are breaking.

    Additions are compatible only at the comparison layer; the bounded compiler
    still refuses unadmitted operations. Source/tool provenance is not API meaning.
    """
    validate_openapi(previous)
    validate_openapi(current)
    old, new = _object(previous), _object(current)
    old_paths, new_paths = _object(old["paths"]), _object(new["paths"])
    for path, item in old_paths.items():
        if path not in new_paths:
            return "breaking"
        for method, operation in _object(item).items():
            if _object(new_paths[path]).get(method) != operation:
                return "breaking"
    if old.get("components") != new.get("components") or old.get("security") != new.get(
        "security"
    ):
        return "breaking"
    if (
        str(_object(old["info"])["version"]).split(".")[0]
        != str(_object(new["info"])["version"]).split(".")[0]
    ):
        return "breaking"
    return "compatible"


def _canonical(document: object) -> bytes:
    return (
        json.dumps(
            document, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False
        )
        + "\n"
    ).encode("ascii")


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_path(path: Path) -> None:
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise OpenApiGenerationError("artifact_path_unsafe")
    if path.exists() and (not path.is_file() or path.stat().st_nlink != 1):
        raise OpenApiGenerationError("artifact_path_unsafe")


def _read(path: Path) -> bytes:
    _safe_path(path)
    if path.stat().st_size > 1024 * 1024:
        raise OpenApiGenerationError("artifact_too_large")
    return path.read_bytes()


def _source_hash(root: Path) -> str:
    return _digest(
        _canonical({name: _digest(_read(root / name)) for name in SOURCE_FILES})
    )


def _typescript(schema: dict[str, object], artifact: bytes) -> bytes:
    if validate_openapi(schema):
        raise OpenApiGenerationError("operations_not_admitted")
    provenance = _object(schema["x-agentmonitor-generation"])
    lines = [
        "// Generated by tooling/foundation/openapi_client.py; do not edit.",
        "// Empty V1 foundation contract. No callable operation is published.",
    ]
    exports = {
        "openapiArtifactSha256": _digest(artifact),
        "schemaSha256": provenance["schema_sha256"],
        "sourceSha256": provenance["source_sha256"],
        "generatorSha256": provenance["generator_sha256"],
        "generatorVersion": GENERATOR_VERSION,
        "apiVersion": _object(schema["info"])["version"],
    }
    lines.extend(
        f"export const {name} = {json.dumps(value)} as const;"
        for name, value in exports.items()
    )
    lines += [
        "export type OperationId = never;",
        "export type ApiPaths = Readonly<Record<never, never>>;",
        "export type ApiClient = Readonly<Record<OperationId, never>>;",
        "export const operationIds: readonly OperationId[] = Object.freeze([]);",
        "export const apiClient: ApiClient = Object.freeze({});",
        "",
    ]
    return "\n".join(lines).encode("ascii")


def _atomic(path: Path, contents: bytes) -> Path:
    descriptor, name = tempfile.mkstemp(
        prefix=".agentmonitor-generation-", dir=path.parent
    )
    pending = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        pending.unlink(missing_ok=True)
        raise
    return pending


def _write_pair(outputs: tuple[tuple[Path, bytes], ...]) -> None:
    originals = {path: _read(path) if path.exists() else None for path, _ in outputs}
    pending: list[tuple[Path, Path]] = []
    replaced: list[Path] = []
    try:
        for path, contents in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            pending.append((path, _atomic(path, contents)))
        for path, staged in pending:
            _safe_path(path)
            os.replace(staged, path)
            replaced.append(path)
    except (OSError, OpenApiGenerationError):
        for path in reversed(replaced):
            original = originals[path]
            if original is None:
                path.unlink()
            else:
                os.replace(_atomic(path, original), path)
        raise OpenApiGenerationError("artifact_write_failed") from None
    finally:
        for _, staged in pending:
            staged.unlink(missing_ok=True)


def _generate_openapi_client(
    app_factory_ref: str, openapi_path: Path, client_dir: Path, *, check: bool = False
) -> OpenApiGenerationReceiptV1:
    """Generate only the allocated outputs; --check never creates or writes files."""
    if app_factory_ref != FACTORY_REF:
        raise OpenApiGenerationError("factory_not_approved")
    root = Path(__file__).resolve().parents[2]
    if (
        openapi_path != root / OPENAPI_RELATIVE
        or client_dir != (root / CLIENT_RELATIVE).parent
    ):
        raise OpenApiGenerationError("output_not_allocated")
    client_path = client_dir / "index.ts"
    for path in (openapi_path, client_path):
        _safe_path(path)
    # Fixed static import after validation: never import caller-supplied strings.
    from agentmonitor.composition.bootstrap import create_schema_application

    source_hash = _source_hash(root)
    tool_hash = _digest(_read(Path(__file__)))
    schema = _object(create_schema_application().openapi())
    operations = validate_openapi(schema)
    if operations:
        raise OpenApiGenerationError("operations_not_admitted")
    if schema.keys() != {"openapi", "info", "paths"} or _object(
        schema["info"]
    ).keys() != {"title", "version"}:
        raise OpenApiGenerationError("schema_fields_not_admitted")
    schema["x-agentmonitor-generation"] = {
        "generator": "agentmonitor-openapi-client",
        "generator_version": GENERATOR_VERSION,
        "generator_sha256": tool_hash,
        "source_sha256": source_hash,
        # Hash excludes this provenance extension to avoid a self-reference.
        "schema_sha256": _digest(_canonical(schema)),
        "api_major": 1,
        "openapi_version": "3.1.0",
        "components": {
            name: importlib.metadata.version(name)
            for name in ("fastapi", "pydantic", "starlette")
        },
    }
    artifact = _canonical(schema)
    # Client source is the canonical artifact, round-tripped through its bytes.
    client = _typescript(_object(json.loads(artifact)), artifact)
    compatibility: Literal["compatible", "breaking", "not_checked"] = "not_checked"
    if openapi_path.exists():
        compatibility = classify_compatibility(json.loads(_read(openapi_path)), schema)
        if compatibility == "breaking":
            raise OpenApiGenerationError("breaking_drift")
    if source_hash != _source_hash(root) or tool_hash != _digest(_read(Path(__file__))):
        raise OpenApiGenerationError("generation_source_changed")
    outputs = ((openapi_path, artifact), (client_path, client))
    if check:
        if any(
            not path.exists() or _read(path) != contents for path, contents in outputs
        ):
            raise OpenApiGenerationError("generated_drift")
    else:
        _write_pair(outputs)
    return OpenApiGenerationReceiptV1(
        source_hash,
        _digest(artifact),
        _digest(client),
        tool_hash,
        "agentmonitor-openapi-client",
        GENERATOR_VERSION,
        1,
        compatibility,
        len(operations),
    )


def generate_openapi_client(
    app_factory_ref: str, openapi_path: Path, client_dir: Path, *, check: bool = False
) -> OpenApiGenerationReceiptV1:
    """Typed failure boundary, retaining neither raw paths nor exception chains."""
    code = "generation_failed"
    try:
        return _generate_openapi_client(
            app_factory_ref, openapi_path, client_dir, check=check
        )
    except OpenApiGenerationError as error:
        code = error.code
    except (ValueError, KeyError, TypeError):
        code = "generation_input_invalid"
    except OSError:
        code = "artifact_unavailable"
    except Exception:
        pass
    raise OpenApiGenerationError(code) from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "backend/src"))
    code = "generation_failed"
    try:
        receipt = generate_openapi_client(
            FACTORY_REF,
            root / OPENAPI_RELATIVE,
            (root / CLIENT_RELATIVE).parent,
            check=args.check,
        )
        print(
            json.dumps(
                {
                    "status": "passed",
                    "compatibility": receipt.compatibility,
                    "operations": receipt.operation_count,
                    "openapi_sha256": receipt.openapi_hash,
                },
                sort_keys=True,
            )
        )
        return 0
    except OpenApiGenerationError as error:
        code = error.code
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        pass
    print(json.dumps({"status": "failed", "code": code}, sort_keys=True))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
