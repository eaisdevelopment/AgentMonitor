"""FND-BND-001..003: real source policy and immutable technical V1 values."""

import dataclasses
import importlib
import subprocess
import sys
import tomllib
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path("backend/src/agentmonitor")
sys.path.insert(0, str(ROOT / "backend/src"))
PUBLIC = {
    "common_v1": (
        "OpaqueIdV1",
        "TimestampAndDurationV1",
        "ExactQuantityV1",
        "EventEnvelopeV1",
        "FieldAvailabilityV1",
    ),
    "configuration_v1": ("ConfigurationRegistryV1", "BootstrapConfigurationV1"),
    "foundation_v1": (
        "RepositoryLayoutAndOwnershipManifestV1",
        "ApplicationFactoryV1",
        "CorrelationContextAndSafeLogEventV1",
        "OpenApiArtifactAndGeneratedClientPipelineV1",
        "MigrationMetadataV1",
        "BuildMetadataV1",
        "TestEvidenceSummaryV1",
    ),
    "platform_v1": ("PortablePlatformPrimitivesV1",),
    "boundary_v1": ("SafeSubprocessExecutionV1", "ApprovedRootAndFileReadV1"),
    "database_v1": (
        "SchemaCompatibilityV1",
        "RepositoryAndUnitOfWorkTechnicalFamilyV1",
        "DatabaseSnapshotActivationV1",
    ),
}


def checker() -> ModuleType:
    assert (ROOT / "tooling/foundation/check_boundaries.py").is_file(), (
        "FND-BND-001: AST import-boundary enforcement is not published"
    )
    return importlib.import_module("tooling.foundation.check_boundaries")


def contract(module: str) -> ModuleType:
    assert (ROOT / SOURCE / "contracts" / f"{module}.py").is_file(), (
        f"FND-BND-003: {module} contract is not published"
    )
    return importlib.import_module(f"agentmonitor.contracts.{module}")


def write_source(root: Path, name: str, text: str) -> Path:
    path = root / SOURCE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path.relative_to(root)


def test_domain_rejects_fastapi_import(tmp_path: Path) -> None:
    source = write_source(
        tmp_path, "modules/example/domain/rule.py", "from fastapi import FastAPI\n"
    )
    assert checker().find_forbidden_imports(tmp_path) == [f"{source}:1:fastapi"]


@pytest.mark.parametrize(
    "dependency",
    [
        "sqlalchemy.orm",
        "pydantic",
        "alembic",
        "sqlite3",
        "os.path",
        "pathlib",
        "subprocess",
        "socket",
        "sys",
        "openai",
        "anthropic",
        "ollama",
        "agentmonitor.composition",
        "agentmonitor.foundation",
        "agentmonitor.api",
        "agentmonitor.adapters.providers.claude",
        "frontend",
        "agentmonitor.modules.other.domain",
        "agentmonitor.modules.example.application",
        "agentmonitor.utils",
    ],
)
def test_domain_rejects_outward_dependencies(tmp_path: Path, dependency: str) -> None:
    source = write_source(
        tmp_path, "modules/example/domain/rule.py", f"import {dependency} as alias\n"
    )
    assert checker().find_forbidden_imports(tmp_path) == [f"{source}:1:{dependency}"]


@pytest.mark.parametrize(
    ("source", "dependency"),
    [
        ("modules/example/application/run.py", "agentmonitor.adapters.persistence"),
        ("modules/example/application/run.py", "agentmonitor.composition"),
        (
            "modules/example/application/run.py",
            "agentmonitor.modules.other.application",
        ),
        ("api/routes.py", "agentmonitor.adapters.persistence.registry.sqlite"),
        ("api/routes.py", "sqlalchemy"),
        ("adapters/providers/claude/read.py", "agentmonitor.adapters.providers.codex"),
        (
            "adapters/providers/claude/read.py",
            "agentmonitor.modules.registry.domain.private",
        ),
        ("foundation/bootstrap.py", "agentmonitor.modules.registry.application"),
        ("contracts/common_v1.py", "agentmonitor.foundation"),
        ("contracts/common_v1.py", "fastapi"),
    ],
)
def test_other_forbidden_edges(tmp_path: Path, source: str, dependency: str) -> None:
    path = write_source(tmp_path, source, f"import {dependency}\n")
    assert checker().find_forbidden_imports(tmp_path) == [f"{path}:1:{dependency}"]


def test_relative_and_from_parent_imports_cannot_bypass_policy(tmp_path: Path) -> None:
    path = write_source(
        tmp_path,
        "modules/example/domain/rule.py",
        "from ..application import execute\nfrom agentmonitor import composition\n",
    )
    assert checker().find_forbidden_imports(tmp_path) == [
        f"{path}:1:agentmonitor.modules.example.application",
        f"{path}:2:agentmonitor.composition",
    ]


def test_allowed_inward_dependencies(tmp_path: Path) -> None:
    for name, text in {
        "modules/example/domain/rule.py": (
            "from dataclasses import dataclass\nfrom decimal import Decimal\n"
            "from agentmonitor.contracts.common_v1 import OpaqueIdV1\n"
            "from . import value\n"
        ),
        "modules/example/domain/value.py": "from datetime import datetime\n",
        "modules/example/application/use_case.py": (
            "from agentmonitor.modules.example.domain import rule\n"
        ),
        "api/routes.py": (
            "from agentmonitor.modules.example.application import use_case\n"
        ),
        "adapters/persistence/example/sqlite/repository.py": (
            "from agentmonitor.modules.example.application.ports import Repository\n"
            "import sqlalchemy\n"
        ),
        "composition/app.py": "from agentmonitor.api import routes\n",
    }.items():
        write_source(tmp_path, name, text)
    assert checker().find_forbidden_imports(tmp_path) == []


def test_cycles_are_reported_deterministically(tmp_path: Path) -> None:
    a = write_source(tmp_path, "modules/example/domain/a.py", "from . import b\n")
    b = write_source(tmp_path, "modules/example/domain/b.py", "from . import a\n")
    assert checker().find_forbidden_imports(tmp_path) == [
        f"{a}:1:cycle:agentmonitor.modules.example.domain.b",
        f"{b}:1:cycle:agentmonitor.modules.example.domain.a",
    ]


def test_api_cannot_deep_import_private_application_code(tmp_path: Path) -> None:
    path = write_source(
        tmp_path,
        "api/routes.py",
        "import agentmonitor.modules.registry.application._private\n",
    )
    assert checker().find_forbidden_imports(tmp_path) == [
        f"{path}:1:agentmonitor.modules.registry.application._private"
    ]


def test_multiple_source_owners_fail_closed(tmp_path: Path) -> None:
    for filename in (
        "contract-baseline.toml",
        "contract-adoption.toml",
        "parallel-ownership.toml",
    ):
        destination = tmp_path / "docs/plans" / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        text = (ROOT / "docs/plans" / filename).read_text(encoding="utf-8")
        if filename == "parallel-ownership.toml":
            text += (
                '\n[[shared_writers]]\nartifact = "conflicting allocation"\n'
                'paths = ["backend/src/agentmonitor/foundation/**"]\n'
                'wave_writer = "second writer"\n'
            )
        destination.write_text(text, encoding="utf-8")
    path = write_source(tmp_path, "foundation/value.py", "value = 1\n")
    assert f"{path}:source-owner-count" in checker().find_ownership_violations(tmp_path)


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("from x import (\n", "invalid-python"),
        ("__import__('os')\n", "dynamic-import"),
        ("from importlib import import_module\n", "importlib"),
        ("from agentmonitor.contracts.common_v1 import *\n", "wildcard-import"),
    ],
)
def test_uninspectable_imports_fail_closed(
    tmp_path: Path, text: str, reason: str
) -> None:
    path = write_source(tmp_path, "modules/example/domain/rule.py", text)
    assert checker().find_forbidden_imports(tmp_path) == [f"{path}:1:{reason}"]


def test_missing_source_tree_fails_closed(tmp_path: Path) -> None:
    assert checker().find_forbidden_imports(tmp_path) == [
        f"{SOURCE}:0:missing-source-tree"
    ]


def test_source_symlink_is_not_followed(tmp_path: Path) -> None:
    outside = tmp_path / "outside.py"
    outside.write_text("import fastapi\n", encoding="utf-8")
    source = tmp_path / SOURCE / "contracts/common_v1.py"
    source.parent.mkdir(parents=True)
    source.symlink_to(outside)
    assert checker().find_forbidden_imports(tmp_path) == [
        f"{source.relative_to(tmp_path)}:0:symlink-source"
    ]


@pytest.mark.parametrize("module", PUBLIC)
def test_exact_published_names_versions_and_closed_values(module: str) -> None:
    published = contract(module)
    baseline = tomllib.loads((ROOT / "docs/plans/contract-baseline.toml").read_text())
    records = {record["name"]: record for record in baseline["contracts"]}
    for name in PUBLIC[module]:
        value_type = getattr(published, name)
        assert value_type.CONTRACT_VERSION == records[name]["version"] == "1.0.0"
        assert value_type.CONTRACT_ID == records[name]["id"]
        assert value_type.OWNER == records[name]["producer"]
        assert dataclasses.is_dataclass(value_type)
        assert vars(value_type)["__dataclass_params__"].frozen
        assert "__slots__" in value_type.__dict__


def test_values_are_immutable_and_reject_unknown_fields() -> None:
    cls = contract("common_v1").OpaqueIdV1
    value = cls(value="domain-example")
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.value = "changed"
    with pytest.raises(TypeError):
        cls(value="domain-example", arbitrary_payload="forbidden")
    with pytest.raises(ValueError):
        cls(value="")


def test_nested_values_cannot_retain_mutable_inputs() -> None:
    cls = contract("configuration_v1").BootstrapConfigurationV1
    with pytest.raises(TypeError):
        cls(
            configuration_version="1.0.0",
            owners=["PLAN-FND"],
            non_secret_sources=(),
            secret_presence=(),
        )
    with pytest.raises(TypeError):
        cls(
            configuration_version="1.0.0",
            owners=("PLAN-FND",),
            non_secret_sources=(["name", "source"],),
            secret_presence=(),
        )


def test_all_literal_statuses_are_closed_at_construction() -> None:
    cls = contract("foundation_v1").OpenApiArtifactAndGeneratedClientPipelineV1
    with pytest.raises(ValueError, match="unsupported-field-state"):
        cls(
            source_hash="a",
            openapi_hash="b",
            client_hash="c",
            generator_name="g",
            generator_version="1",
            api_major=1,
            compatibility="invented",
        )


def test_source_tree_ancestor_symlink_is_not_followed(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "backend").symlink_to(outside, target_is_directory=True)
    assert checker().find_forbidden_imports(tmp_path) == ["backend:0:symlink-source"]


def test_exact_quantities_and_time_preserve_units_without_float() -> None:
    common = contract("common_v1")
    zero = common.ExactQuantityV1(value=Decimal("0.00"), unit="USD")
    assert zero.value == Decimal("0.00")
    with pytest.raises((TypeError, ValueError)):
        common.ExactQuantityV1(value=0.1, unit="USD")
    with pytest.raises(ValueError):
        common.ExactQuantityV1(value=Decimal("NaN"), unit="USD")
    common.TimestampAndDurationV1(
        timestamp=datetime(2026, 1, 1, tzinfo=UTC), duration_ms=0
    )
    for instant in (
        datetime(2026, 1, 1),
        datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=1))),
    ):
        with pytest.raises(ValueError):
            common.TimestampAndDurationV1(timestamp=instant, duration_ms=0)
    with pytest.raises(ValueError):
        common.TimestampAndDurationV1(
            timestamp=datetime(2026, 1, 1, tzinfo=UTC), duration_ms=-1
        )


def test_availability_is_closed_and_zero_is_available() -> None:
    cls = contract("common_v1").FieldAvailabilityV1
    states = (
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
    )
    assert len({cls(state=state).state for state in states}) == 10
    with pytest.raises(ValueError):
        cls(state="zero")


def test_real_manifest_and_checkout_pass() -> None:
    assert checker().find_ownership_violations(ROOT) == []
    assert checker().find_forbidden_imports(ROOT) == []


@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        ("duplicate", "contract-producer-count"),
        ("unowned", "contract-producer-count"),
        ("version", "contract-version"),
        ("maturity", "contract-maturity"),
        ("path", "source-owner-count"),
    ],
)
def test_manifest_errors_fail_closed(
    tmp_path: Path, operation: str, expected: str
) -> None:
    # These are policy documents, not provider responses or integration substitutes.
    for relative in (
        "docs/plans/contract-baseline.toml",
        "docs/plans/contract-adoption.toml",
        "docs/plans/parallel-ownership.toml",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        text = (ROOT / relative).read_text(encoding="utf-8")
        if relative.endswith("contract-adoption.toml"):
            if operation == "duplicate":
                text = text.replace(
                    "publishes = []", 'publishes = ["CTR-COMMON-001"]', 1
                )
            elif operation == "unowned":
                text = text.replace('"CTR-COMMON-001", ', "", 1)
        if relative.endswith("contract-baseline.toml"):
            if operation == "version":
                text = text.replace('version = "1.0.0"', 'version = "2.0.0"', 1)
            elif operation == "maturity":
                text = text.replace(
                    'maturity = "proposed_aligned"', 'maturity = "invalid"', 1
                )
        target.write_text(text, encoding="utf-8")
    write_source(
        tmp_path,
        "unallocated/value.py" if operation == "path" else "foundation/value.py",
        "value = 1\n",
    )
    assert any(
        expected in error for error in checker().find_ownership_violations(tmp_path)
    )


def test_checker_cli_runs_real_checkout_and_fails_closed(tmp_path: Path) -> None:
    checker()
    for root, expected in ((ROOT, 0), (tmp_path, 1)):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tooling/foundation/check_boundaries.py"),
                str(root),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
            env={},
        )
        assert result.returncode == expected, result.stdout
        assert result.stderr == ""
        assert str(root) not in result.stdout
