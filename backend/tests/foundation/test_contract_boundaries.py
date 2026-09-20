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
SQLITE_POLICY = "agentmonitor.adapters.persistence._shared.sqlite.core.policy"
SQLITE_COMPATIBILITY = (
    "agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility"
)


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


def copy_contract_policy(root: Path) -> None:
    """Copy repository-owned policy inputs, never external product responses."""
    for filename in (
        "contract-baseline.toml",
        "contract-adoption.toml",
        "parallel-ownership.toml",
    ):
        path = root / "docs/plans" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / "docs/plans" / filename).read_bytes())
    for module in PUBLIC:
        write_source(
            root,
            f"contracts/{module}.py",
            (ROOT / SOURCE / "contracts" / f"{module}.py").read_text(),
        )


@pytest.mark.parametrize(
    "statement",
    [
        "from agentmonitor.contracts.database_v1 import SchemaCompatibilityV1",
        "from agentmonitor.contracts.database_v1 import SchemaCompatibilityV1 as S",
        "import agentmonitor.contracts.database_v1 as database",
        "from agentmonitor.contracts import database_v1 as database",
    ],
)
def test_undeclared_contract_consumption_is_rejected(
    tmp_path: Path, statement: str
) -> None:
    copy_contract_policy(tmp_path)
    source = write_source(tmp_path, "modules/registry/domain/rule.py", statement + "\n")
    assert any(
        error.startswith(f"{source}:1:undeclared-contract:CTR-DB-001")
        for error in checker().find_forbidden_imports(tmp_path)
    )


def test_declared_contract_consumption_remains_allowed(tmp_path: Path) -> None:
    copy_contract_policy(tmp_path)
    write_source(
        tmp_path,
        "modules/capacity/domain/rule.py",
        "from agentmonitor.contracts.database_v1 import SchemaCompatibilityV1\n",
    )
    assert checker().find_forbidden_imports(tmp_path) == []


def test_p01_adopts_m2_iam_security_event_projection(tmp_path: Path) -> None:
    copy_contract_policy(tmp_path)
    write_source(
        tmp_path,
        "contracts/identity_access_v1.py",
        "class IamSecurityEventViewV1:\n"
        '    CONTRACT_ID = "CTR-IAM-008"\n'
        '    OWNER = "PLAN-M01"\n',
    )
    write_source(
        tmp_path,
        "api/v1/routers/iam.py",
        "from agentmonitor.contracts.identity_access_v1 "
        "import IamSecurityEventViewV1\n",
    )
    assert checker().find_forbidden_imports(tmp_path) == []


def test_m01_concrete_contract_classes_and_transient_secret_are_resolved(
    tmp_path: Path,
) -> None:
    copy_contract_policy(tmp_path)
    write_source(
        tmp_path,
        "contracts/identity_access_v1.py",
        "class PrincipalV1:\n"
        '    CONTRACT_ID = "CTR-IAM-001"\n'
        '    OWNER = "PLAN-M01"\n'
        "class SecretInputV1:\n"
        "    pass\n",
    )
    write_source(
        tmp_path,
        "modules/identity_access/application/bootstrap.py",
        "from agentmonitor.contracts.identity_access_v1 import "
        "PrincipalV1, SecretInputV1\n",
    )
    assert checker().find_forbidden_imports(tmp_path) == []


def test_m01_transient_secret_requires_its_own_contract_adoption(
    tmp_path: Path,
) -> None:
    copy_contract_policy(tmp_path)
    write_source(
        tmp_path,
        "contracts/identity_access_v1.py",
        "class PrincipalV1:\n"
        '    CONTRACT_ID = "CTR-IAM-001"\n'
        '    OWNER = "PLAN-M01"\n'
        "class SecretInputV1:\n"
        "    pass\n",
    )
    source = write_source(
        tmp_path,
        "modules/registry/application/consumer.py",
        "from agentmonitor.contracts.identity_access_v1 import SecretInputV1\n",
    )
    assert (
        f"{source}:1:undeclared-contract:CTR-IAM-004"
        in checker().find_forbidden_imports(tmp_path)
    )


@pytest.mark.parametrize(
    "declaration",
    [
        'class PrincipalV1:\n    CONTRACT_ID = "CTR-IAM-999"\n    OWNER = "PLAN-M01"\n',
        'class PrincipalV1:\n    CONTRACT_ID = "CTR-IAM-001"\n    OWNER = "PLAN-M02"\n',
        "PrincipalV1 = object()\n",
    ],
)
def test_m01_unpublished_or_misattributed_symbol_is_rejected(
    tmp_path: Path, declaration: str
) -> None:
    copy_contract_policy(tmp_path)
    write_source(tmp_path, "contracts/identity_access_v1.py", declaration)
    source = write_source(
        tmp_path,
        "modules/identity_access/application/bootstrap.py",
        "from agentmonitor.contracts.identity_access_v1 import PrincipalV1\n",
    )
    assert f"{source}:1:unresolved-contract-module" in checker().find_forbidden_imports(
        tmp_path
    )


@pytest.mark.parametrize(
    ("declaration", "symbol"),
    [
        (
            'class PrincipalV1:\n    CONTRACT_ID = "CTR-IAM-001"\n'
            '    CONTRACT_ID = "CTR-IAM-999"\n    OWNER = "PLAN-M01"\n',
            "PrincipalV1",
        ),
        (
            'class PrincipalV1:\n    CONTRACT_ID = "CTR-IAM-001"\n'
            '    OWNER = "PLAN-M01"\n'
            '    if True:\n        CONTRACT_ID = "CTR-IAM-999"\n',
            "PrincipalV1",
        ),
        (
            'class PrincipalV1:\n    CONTRACT_ID = "CTR-IAM-001"\n'
            '    OWNER = "PLAN-M01"\n'
            'class SecretInputV1:\n    CONTRACT_ID = "CTR-IAM-999"\n'
            '    OWNER = "PLAN-M01"\n',
            "SecretInputV1",
        ),
    ],
)
def test_m01_mutated_declaration_cannot_be_published(
    tmp_path: Path, declaration: str, symbol: str
) -> None:
    copy_contract_policy(tmp_path)
    write_source(tmp_path, "contracts/identity_access_v1.py", declaration)
    source = write_source(
        tmp_path,
        "modules/identity_access/application/bootstrap.py",
        f"from agentmonitor.contracts.identity_access_v1 import {symbol}\n",
    )
    assert any(
        error.startswith(f"{source}:1:unresolved-contract-")
        for error in checker().find_forbidden_imports(tmp_path)
    )


def test_public_alias_cannot_disguise_an_undeclared_contract(tmp_path: Path) -> None:
    copy_contract_policy(tmp_path)
    foundation_path = tmp_path / SOURCE / "contracts/foundation_v1.py"
    foundation_path.write_text(
        foundation_path.read_text(encoding="utf-8")
        + "\nRenamedSchema = SchemaCompatibilityV1\n",
        encoding="utf-8",
    )
    source = write_source(
        tmp_path,
        "modules/registry/domain/rule.py",
        "from agentmonitor.contracts.foundation_v1 import RenamedSchema\n",
    )
    assert f"{source}:1:unresolved-contract-symbol" in checker().find_forbidden_imports(
        tmp_path
    )


@pytest.mark.parametrize(
    "assignment",
    [
        "OpaqueIdV1 = SchemaCompatibilityV1",
        "OpaqueIdV1: type = SchemaCompatibilityV1",
        "(OpaqueIdV1, ordinary_name) = (SchemaCompatibilityV1, 1)",
    ],
)
def test_catalog_name_rebinding_cannot_disguise_an_undeclared_contract(
    tmp_path: Path,
    assignment: str,
) -> None:
    copy_contract_policy(tmp_path)
    foundation_path = tmp_path / SOURCE / "contracts/foundation_v1.py"
    foundation_path.write_text(
        foundation_path.read_text(encoding="utf-8") + f"\n{assignment}\n",
        encoding="utf-8",
    )
    source = write_source(
        tmp_path,
        "modules/registry/domain/rule.py",
        "from agentmonitor.contracts.foundation_v1 import OpaqueIdV1\n",
    )
    assert f"{source}:1:unresolved-contract-symbol" in checker().find_forbidden_imports(
        tmp_path
    )


def test_ordinary_assignments_do_not_change_contract_declarations(
    tmp_path: Path,
) -> None:
    copy_contract_policy(tmp_path)
    foundation_path = tmp_path / SOURCE / "contracts/foundation_v1.py"
    foundation_path.write_text(
        foundation_path.read_text(encoding="utf-8")
        + "\nREVIEWED_MAJOR = 1\nreviewed: bool = True\n",
        encoding="utf-8",
    )
    write_source(
        tmp_path,
        "modules/registry/domain/rule.py",
        "from agentmonitor.contracts.common_v1 import OpaqueIdV1\n",
    )
    assert checker().find_forbidden_imports(tmp_path) == []


@pytest.mark.parametrize(
    "mutation",
    [
        "if True:\n    OpaqueIdV1 = SchemaCompatibilityV1",
        "while False:\n    OpaqueIdV1 = SchemaCompatibilityV1",
        "(OpaqueIdV1 := SchemaCompatibilityV1)",
        "for OpaqueIdV1 in (SchemaCompatibilityV1,):\n    pass",
        "with context() as OpaqueIdV1:\n    pass",
        "try:\n    pass\nexcept Exception as OpaqueIdV1:\n    pass",
        "[(OpaqueIdV1 := SchemaCompatibilityV1) for item in ()]",
        "[[(OpaqueIdV1 := SchemaCompatibilityV1) for inner in ()] for outer in ()]",
        "def change():\n    global OpaqueIdV1\n    OpaqueIdV1 = SchemaCompatibilityV1",
        "def definition(value=(OpaqueIdV1 := SchemaCompatibilityV1)):\n    pass",
        "match candidate:\n    case {'kind': OpaqueIdV1}:\n        pass",
        "ordinary = OpaqueIdV1 = SchemaCompatibilityV1",
        "if True:\n    from agentmonitor.contracts.database_v1 import "
        "SchemaCompatibilityV1 as OpaqueIdV1",
        "def OpaqueIdV1():\n    return SchemaCompatibilityV1",
        "class OpaqueIdV1(SchemaCompatibilityV1):\n    pass",
    ],
)
def test_compound_catalog_rebinding_is_rejected(tmp_path: Path, mutation: str) -> None:
    copy_contract_policy(tmp_path)
    path = tmp_path / SOURCE / "contracts/foundation_v1.py"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\nclass OpaqueIdV1: pass\n"
        + mutation
        + "\n",
        encoding="utf-8",
    )
    source = write_source(
        tmp_path,
        "modules/registry/domain/rule.py",
        "from agentmonitor.contracts.foundation_v1 import OpaqueIdV1\n",
    )
    errors = checker().find_forbidden_imports(tmp_path)
    assert any(":catalog-name-rebinding:OpaqueIdV1" in error for error in errors)
    assert f"{source}:1:unresolved-contract-symbol" in errors


@pytest.mark.parametrize(
    "local_code",
    [
        "def local():\n    OpaqueIdV1 = 1\n    return OpaqueIdV1",
        "def local():\n    if True:\n        OpaqueIdV1 = 1",
        "def local():\n    return (OpaqueIdV1 := 1)",
        "def local():\n    return [(OpaqueIdV1 := item) for item in ()]",
        "[OpaqueIdV1 for OpaqueIdV1 in ()]",
        "{OpaqueIdV1: 1 for OpaqueIdV1 in ()}",
        "{OpaqueIdV1 for OpaqueIdV1 in ()}",
        "(OpaqueIdV1 for OpaqueIdV1 in ())",
        "class Local:\n    OpaqueIdV1 = 1",
        "(lambda OpaqueIdV1: (OpaqueIdV1 := 1))",
        "if True:\n    ordinary = 1\nfor ordinary in ():\n    pass",
        "def local():\n    def OpaqueIdV1():\n        pass",
        "def local():\n    from agentmonitor.contracts.database_v1 import "
        "SchemaCompatibilityV1 as OpaqueIdV1",
    ],
)
def test_local_catalog_names_and_ordinary_bindings_remain_allowed(
    tmp_path: Path,
    local_code: str,
) -> None:
    copy_contract_policy(tmp_path)
    path = tmp_path / SOURCE / "contracts/foundation_v1.py"
    path.write_text(
        path.read_text(encoding="utf-8") + "\n" + local_code + "\n", encoding="utf-8"
    )
    assert checker().find_forbidden_imports(tmp_path) == []


def test_missing_contract_adoption_fails_closed(tmp_path: Path) -> None:
    source = write_source(
        tmp_path,
        "modules/registry/domain/rule.py",
        "from agentmonitor.contracts.common_v1 import OpaqueIdV1\n",
    )
    assert f"{source}:1:unresolved-contract-policy" in checker().find_forbidden_imports(
        tmp_path
    )


@pytest.mark.parametrize("layer", ["infrastructure", "api", "adapters", "unknown"])
def test_application_rejects_own_outward_layers(tmp_path: Path, layer: str) -> None:
    target = f"agentmonitor.modules.registry.{layer}.sqlite"
    path = write_source(
        tmp_path, "modules/registry/application/run.py", f"import {target}\n"
    )
    assert checker().find_forbidden_imports(tmp_path) == [f"{path}:1:{target}"]


@pytest.mark.parametrize(
    "statement",
    [
        "from .. import domain",
        "from ..domain import rule",
        "from . import ports",
        "from agentmonitor.modules.registry import domain",
    ],
)
def test_application_inward_import_forms_remain_allowed(
    tmp_path: Path, statement: str
) -> None:
    write_source(tmp_path, "modules/registry/application/run.py", statement + "\n")
    assert checker().find_forbidden_imports(tmp_path) == []


@pytest.mark.parametrize(
    "statement",
    [
        "from agentmonitor.contracts.common_v1 import _private",
        "from agentmonitor.contracts.common_v1 import _private as public_name",
        "from ....contracts.common_v1 import _private as public_name",
    ],
)
def test_private_contract_symbols_are_rejected(tmp_path: Path, statement: str) -> None:
    source = write_source(tmp_path, "modules/registry/domain/rule.py", statement + "\n")
    assert checker().find_forbidden_imports(tmp_path) == [
        f"{source}:1:agentmonitor.contracts.common_v1._private"
    ]


def test_module_name_collisions_fail_before_traversal(tmp_path: Path) -> None:
    module = "agentmonitor.modules.registry.domain.rule"
    first = write_source(tmp_path, "modules/registry/domain/rule.py", "value = 1\n")
    second = write_source(
        tmp_path, "modules/registry/domain/rule/__init__.py", "import fastapi\n"
    )
    assert checker().find_forbidden_imports(tmp_path) == sorted(
        [
            f"{first}:0:duplicate-module:{module}",
            f"{second}:0:duplicate-module:{module}",
        ]
    )


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
    copy_contract_policy(tmp_path)
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
        write_source(
            tmp_path,
            name.replace("example", "registry"),
            text.replace("example", "registry"),
        )
    assert checker().find_forbidden_imports(tmp_path) == []


@pytest.mark.parametrize(
    "statement",
    [
        f"from {SQLITE_POLICY} import DatabaseRefV1",
        f"from {SQLITE_POLICY} import SqliteDatabaseHandleV1 as DatabaseHandle",
        f"from {SQLITE_POLICY} import open_sqlite_database",
        f"from {SQLITE_COMPATIBILITY} import application_schema_range",
        f"from {SQLITE_COMPATIBILITY} import InspectSchemaCompatibilityV1 as Inspector",
        (
            "from ..adapters.persistence._shared.sqlite.schema.compatibility "
            "import RequireWritableSchemaV1"
        ),
    ],
)
def test_composition_can_import_approved_sqlite_entry_points(
    tmp_path: Path, statement: str
) -> None:
    copy_contract_policy(tmp_path)
    write_source(tmp_path, "composition/bootstrap.py", statement + "\n")
    assert checker().find_forbidden_imports(tmp_path) == []


@pytest.mark.parametrize(
    ("statement", "target"),
    [
        (
            f"import {SQLITE_POLICY}",
            SQLITE_POLICY,
        ),
        (
            f"import {SQLITE_POLICY}.DatabaseRefV1",
            f"{SQLITE_POLICY}.DatabaseRefV1",
        ),
        (
            "from agentmonitor.adapters.persistence._shared.sqlite.core import policy",
            "agentmonitor.adapters.persistence._shared.sqlite.core",
        ),
        (
            f"from {SQLITE_POLICY} import SqlitePolicyError",
            f"{SQLITE_POLICY}.SqlitePolicyError",
        ),
        (
            f"from {SQLITE_POLICY} import open_sqlite_inspection",
            f"{SQLITE_POLICY}.open_sqlite_inspection",
        ),
        (
            f"from {SQLITE_COMPATIBILITY} import SchemaCompatibilityViewV1",
            f"{SQLITE_COMPATIBILITY}.SchemaCompatibilityViewV1",
        ),
        (
            f"from {SQLITE_COMPATIBILITY} import migrate_to_head",
            f"{SQLITE_COMPATIBILITY}.migrate_to_head",
        ),
        (
            f"from {SQLITE_COMPATIBILITY}._private import hidden",
            f"{SQLITE_COMPATIBILITY}._private",
        ),
        (
            "from agentmonitor.adapters.persistence._shared.sqlite.unrelated.factory "
            "import build",
            "agentmonitor.adapters.persistence._shared.sqlite.unrelated.factory",
        ),
    ],
)
def test_composition_rejects_non_entry_point_sqlite_imports(
    tmp_path: Path, statement: str, target: str
) -> None:
    copy_contract_policy(tmp_path)
    source = write_source(tmp_path, "composition/bootstrap.py", statement + "\n")
    assert checker().find_forbidden_imports(tmp_path) == [f"{source}:1:{target}"]


def test_m2_fresh_init_entry_is_only_composition_migration_caller(
    tmp_path: Path,
) -> None:
    copy_contract_policy(tmp_path)
    write_source(
        tmp_path,
        "composition/iam_fresh_init.py",
        f"from {SQLITE_COMPATIBILITY} import migrate_to_head\n",
    )
    assert checker().find_forbidden_imports(tmp_path) == []


@pytest.mark.parametrize(
    "symbol",
    [
        "DatabaseRefV1",
        "SqlitePolicyError",
        "open_sqlite_database",
    ],
)
def test_m01_sqlite_adapter_can_import_exact_shared_policy_symbols(
    tmp_path: Path, symbol: str
) -> None:
    copy_contract_policy(tmp_path)
    write_source(
        tmp_path,
        "adapters/persistence/identity_access/sqlite/repository.py",
        f"from {SQLITE_POLICY} import {symbol}\n",
    )
    assert checker().find_forbidden_imports(tmp_path) == []


def test_m01_sqlite_adapter_cannot_import_shared_inspection_or_migration(
    tmp_path: Path,
) -> None:
    copy_contract_policy(tmp_path)
    source = write_source(
        tmp_path,
        "adapters/persistence/identity_access/sqlite/repository.py",
        f"from {SQLITE_POLICY} import open_sqlite_inspection\n",
    )
    assert checker().find_forbidden_imports(tmp_path) == [
        f"{source}:1:{SQLITE_POLICY}.open_sqlite_inspection"
    ]


@pytest.mark.parametrize(
    ("module", "symbol"),
    [
        ("application.authorization", "BROWSER_PERMISSIONS_V1"),
        ("application.api_tokens", "TokenQueryErrorV1"),
        ("application.sessions", "SessionPasswordHasherPortV1"),
        ("application.sessions", "SessionQueryErrorV1"),
        ("application.throttle", "LoginThrottleStateV1"),
        ("application.throttle", "after_failed_login"),
        ("application.throttle", "after_successful_login"),
        ("application.throttle", "retry_after_seconds"),
        ("application.errors", "PasswordHasherUnavailableV1"),
        ("application.errors", "IamRepositoryUnavailableV1"),
        ("domain.policy", "password_creation_error"),
        ("domain.policy", "M2_ISSUABLE_SCOPES"),
        ("domain.policy", "canonical_token_name"),
        ("domain.policy", "idempotency_receipt_expired"),
        ("domain.policy", "may_issue_scopes"),
        ("domain.policy", "may_manage_token"),
        ("domain.policy", "session_deadlines"),
        ("domain.policy", "session_expired"),
        ("domain.policy", "session_state"),
        ("domain.policy", "should_touch_session"),
        ("domain.policy", "token_deadline"),
        ("domain.policy", "token_should_touch"),
        ("domain.policy", "token_state"),
    ],
)
def test_m01_sqlite_adapter_can_import_only_reviewed_same_owner_symbols(
    tmp_path: Path, module: str, symbol: str
) -> None:
    copy_contract_policy(tmp_path)
    write_source(
        tmp_path,
        "adapters/persistence/identity_access/sqlite/sessions.py",
        f"from agentmonitor.modules.identity_access.{module} import {symbol}\n",
    )
    assert checker().find_forbidden_imports(tmp_path) == []


@pytest.mark.parametrize(
    ("module", "symbol"),
    [
        ("application.sessions", "UnreviewedPortV1"),
        ("domain.policy", "unreviewed_policy"),
        ("application._internal", "anything"),
    ],
)
def test_m01_sqlite_adapter_rejects_unreviewed_same_owner_symbols(
    tmp_path: Path, module: str, symbol: str
) -> None:
    copy_contract_policy(tmp_path)
    source = write_source(
        tmp_path,
        "adapters/persistence/identity_access/sqlite/sessions.py",
        f"from agentmonitor.modules.identity_access.{module} import {symbol}\n",
    )
    target = f"agentmonitor.modules.identity_access.{module}"
    if not module.endswith("._internal"):
        target = f"{target}.{symbol}"
    assert checker().find_forbidden_imports(tmp_path) == [f"{source}:1:{target}"]


def test_m01_argon2_adapter_imports_only_its_safe_application_error(
    tmp_path: Path,
) -> None:
    copy_contract_policy(tmp_path)
    write_source(
        tmp_path,
        "adapters/identity_access/argon2_password.py",
        "from agentmonitor.modules.identity_access.application.errors "
        "import PasswordHasherUnavailableV1\n",
    )
    assert checker().find_forbidden_imports(tmp_path) == []


def test_m01_argon2_adapter_rejects_unreviewed_application_symbol(
    tmp_path: Path,
) -> None:
    copy_contract_policy(tmp_path)
    source = write_source(
        tmp_path,
        "adapters/identity_access/argon2_password.py",
        "from agentmonitor.modules.identity_access.application.errors "
        "import UnreviewedError\n",
    )
    assert checker().find_forbidden_imports(tmp_path) == [
        f"{source}:1:agentmonitor.modules.identity_access.application.errors.UnreviewedError"
    ]


def test_other_module_sqlite_adapter_cannot_import_m01_shared_allowance(
    tmp_path: Path,
) -> None:
    copy_contract_policy(tmp_path)
    source = write_source(
        tmp_path,
        "adapters/persistence/registry/sqlite/repository.py",
        f"from {SQLITE_POLICY} import SqlitePolicyError\n",
    )
    assert checker().find_forbidden_imports(tmp_path) == [f"{source}:1:{SQLITE_POLICY}"]


@pytest.mark.parametrize(
    "source_name",
    [
        "api/app.py",
        "foundation/application.py",
        "modules/registry/application/start.py",
        "adapters/providers/claude/start.py",
    ],
)
def test_non_composition_sources_reject_approved_sqlite_entry_points(
    tmp_path: Path, source_name: str
) -> None:
    copy_contract_policy(tmp_path)
    source = write_source(
        tmp_path, source_name, f"from {SQLITE_POLICY} import DatabaseRefV1\n"
    )
    assert checker().find_forbidden_imports(tmp_path) == [f"{source}:1:{SQLITE_POLICY}"]


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
