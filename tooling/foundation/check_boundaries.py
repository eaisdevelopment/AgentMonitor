"""Fail-closed V1 Python imports and real manifest ownership (FND-BND-001..003)."""

import argparse
import ast
import fnmatch
import os
import tomllib
from pathlib import Path

SOURCE = Path("backend/src/agentmonitor")
# Explicitly reviewed pure standard-library dependencies. New entries need review;
# a Python standard-library module is not necessarily free of OS/framework I/O.
PURE_IMPORTS = frozenset(
    {
        "__future__",
        "abc",
        "collections",
        "dataclasses",
        "datetime",
        "decimal",
        "enum",
        "fractions",
        "functools",
        "hashlib",
        "itertools",
        "json",
        "math",
        "operator",
        "re",
        "statistics",
        "string",
        "types",
        "typing",
        "unicodedata",
        "uuid",
    }
)
CONTRACT_MODULES = frozenset(
    {
        "common_v1",
        "configuration_v1",
        "foundation_v1",
        "platform_v1",
        "boundary_v1",
        "database_v1",
        "identity_access_v1",
        "registry_v1",
        "provider_system_v1",
        "common_provenance_v1",
        "collection_control_v1",
        "capacity_v1",
        "common_quantity_v1",
        "runtime_observation_v1",
        "alerting_v1",
        "operations_v1",
        "deployment_v1",
        "integration_v1",
        "events_v1",
        "api_v1",
        "ui_v1",
    }
)
# Published supporting values have no independent catalog ID. This closed list
# prevents arbitrary aliases/re-exports from masquerading as support metadata.
SUPPORT_SYMBOLS = {
    "agentmonitor.contracts.common_v1": {"TechnicalValueV1", "AvailabilityStateV1"},
    "agentmonitor.contracts.configuration_v1": {"ConfigurationDescriptorV1"},
    "agentmonitor.contracts.provider_system_v1": {"ProviderConnectionStateV1"},
    "agentmonitor.contracts.registry_v1": {
        "ConfirmIdentityAssociationCommandV1",
        "IdentityDecisionStateV1",
        "IdentityEvidenceClassV1",
        "PrivateProfileLocatorRefV1",
        "ProfileCompatibilityStateV1",
        "ProfileManagementStateV1",
        "ProfilePurposeV1",
        "ReconcileProviderDiscoveryV1",
        "RegisterAccountV1",
        "RegistryScopeKindV1",
        "RegistryScopeSnapshotV1",
        "ResourceKindV1",
        "ConfirmIdentityAssociationV1",
    },
    "agentmonitor.contracts.runtime_observation_v1": {
        "AgentProcessViewV1",
        "CorrelationDecisionStateV1",
        "CorrelationEvidenceClassV1",
        "InspectedAgentProcessCountV1",
        "InvalidRuntimeObservationV1",
        "MetricOverlapV1",
        "MetricSemanticsV1",
        "NormalizedRuntimeStateV1",
        "PlatformInspectionStateV1",
        "PresenceStateV1",
        "ProcessInspectionSnapshotV1",
        "ProviderKeyV1",
        "RuntimeFieldStateV1",
        "RuntimeOverviewViewV1",
        "RuntimeStateCertaintyV1",
        "StallEvaluationStateV1",
    },
    "agentmonitor.contracts.capacity_v1": {
        "CapacityHealthStateV1",
        "InvalidCapacityContractV1",
    },
}
TASK_CONTRACT_IDS = frozenset(
    {
        "CTR-COMMON-001",
        "CTR-COMMON-002",
        "CTR-COMMON-003",
        "CTR-COMMON-006",
        "CTR-COMMON-007",
        "CTR-CONFIG-001",
        "CTR-FND-001",
        "CTR-FND-002",
        "CTR-FND-003",
        "CTR-FND-004",
        "CTR-FND-005",
        "CTR-FND-006",
        "CTR-FND-007",
        "CTR-FND-008",
        "CTR-BOUNDARY-001",
        "CTR-BOUNDARY-003",
        "CTR-PLAT-001",
        "CTR-DB-001",
        "CTR-DB-002",
        "CTR-DB-003",
    }
)
# Composition alone wires this closed subset of the Task 3 SQLite adapter.
# Keeping the allowance at symbol granularity prevents a module import from
# exposing migration, inspection-internal, or future public-looking helpers.
COMPOSITION_SQLITE_SYMBOLS = {
    "agentmonitor.adapters.persistence._shared.sqlite.core.policy": frozenset(
        {
            "DatabaseRefV1",
            "SqliteDatabaseHandleV1",
            "checkpoint_sqlite_database",
            "open_sqlite_database",
        }
    ),
    "agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility": (
        frozenset(
            {
                "InspectSchemaCompatibilityV1",
                "RequireWritableSchemaV1",
                "application_schema_range",
            }
        )
    ),
}
M01_SQLITE_POLICY_SYMBOLS = frozenset(
    {"DatabaseRefV1", "SqlitePolicyError", "open_sqlite_database"}
)
M01_SQLITE_LAYER_SYMBOLS = {
    "agentmonitor.modules.identity_access.application.authorization": frozenset(
        {"BROWSER_PERMISSIONS_V1"}
    ),
    "agentmonitor.modules.identity_access.application.api_tokens": frozenset(
        {"TokenQueryErrorV1"}
    ),
    "agentmonitor.modules.identity_access.application.sessions": frozenset(
        {"SessionPasswordHasherPortV1", "SessionQueryErrorV1"}
    ),
    "agentmonitor.modules.identity_access.application.throttle": frozenset(
        {
            "LoginThrottleStateV1",
            "after_failed_login",
            "after_successful_login",
            "retry_after_seconds",
        }
    ),
    "agentmonitor.modules.identity_access.application.errors": frozenset(
        {"PasswordHasherUnavailableV1", "IamRepositoryUnavailableV1"}
    ),
    "agentmonitor.modules.identity_access.domain.policy": frozenset(
        {
            "M2_ISSUABLE_SCOPES",
            "canonical_token_name",
            "password_creation_error",
            "idempotency_receipt_expired",
            "may_issue_scopes",
            "may_manage_token",
            "session_deadlines",
            "session_expired",
            "session_state",
            "should_touch_session",
            "token_deadline",
            "token_should_touch",
            "token_state",
            "valid_correlation_id",
        }
    ),
}
M02_SQLITE_POLICY_SYMBOLS = frozenset(
    {"DatabaseRefV1", "SqlitePolicyError", "open_sqlite_database"}
)
M03_M06_SQLITE_POLICY_PREFIXES = frozenset(
    {
        "agentmonitor.adapters.persistence.provider_system.sqlite",
        "agentmonitor.adapters.persistence.collection_control.sqlite",
        "agentmonitor.adapters.persistence.capacity.sqlite",
        "agentmonitor.adapters.persistence.runtime_observation.sqlite",
    }
)
M03_M06_SQLITE_POLICY_SYMBOLS = frozenset(
    {"DatabaseRefV1", "SqlitePolicyError", "open_sqlite_database"}
)
M02_SQLITE_LAYER_SYMBOLS = {
    "agentmonitor.modules.registry.application.accounts": frozenset(
        {
            "CreatePendingAccountCommandV1",
            "EditAccountCommandV1",
            "ConfirmIdentityAssociationCommandV1",
            "EnrollMonitoringGraphCommandV1",
            "RegistryPolicyErrorV1",
            "decide_account_monitoring",
            "decide_candidate_evidence_transition",
            "decide_command_replay",
            "decide_provider_identity_confirmation",
            "ensure_candidate_confirmation_is_current",
            "safe_registry_event_projection",
        }
    ),
    "agentmonitor.modules.registry.application.organizations": frozenset(
        {
            "CreateOrganizationCommandV1",
            "EditOrganizationCommandV1",
            "ReorderOrganizationsCommandV1",
            "RegistryCommandConflictV1",
        }
    ),
}
A01_PROVIDER_SYSTEM_SYMBOLS = {
    "agentmonitor.modules.provider_system.application.gateway": frozenset(
        {"ResolveAndInvokeProviderCapabilityV1", "resolve_one_exact_observation"}
    )
}
FRESH_INIT_MIGRATE_TARGET = (
    "agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility."
    "migrate_to_head"
)


def _sources(root: Path) -> tuple[list[Path], list[str]]:
    for relative in (Path("backend"), Path("backend/src"), SOURCE):
        if (root / relative).is_symlink():
            return [], [f"{relative}:0:symlink-source"]
    source = root / SOURCE
    if not source.is_dir():
        return [], [f"{SOURCE}:0:missing-source-tree"]
    paths: list[Path] = []
    errors: list[str] = []

    def traversal_error(error: OSError) -> None:
        errors.append(f"{SOURCE}:0:unreadable-source-tree")

    for directory, names, files in os.walk(source, onerror=traversal_error):
        for name in list(names):
            path = Path(directory) / name
            if path.is_symlink():
                errors.append(f"{path.relative_to(root)}:0:symlink-source")
                names.remove(name)
            elif name == "__pycache__":
                names.remove(name)
        for name in files:
            if not name.endswith(".py"):
                continue
            path = Path(directory) / name
            if path.is_symlink():
                errors.append(f"{path.relative_to(root)}:0:symlink-source")
            else:
                paths.append(path)
    return sorted(paths), sorted(errors)


def _module(path: Path, root: Path) -> str:
    parts = list(path.relative_to(root / SOURCE).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(["agentmonitor", *parts])


def _composition_sqlite_symbol_module(source: str, target: str) -> bool:
    is_composition = source == "agentmonitor.composition" or source.startswith(
        "agentmonitor.composition."
    )
    return is_composition and target in COMPOSITION_SQLITE_SYMBOLS


def _approved_composition_sqlite_symbol(source: str, target: str) -> bool:
    module, separator, symbol = target.rpartition(".")
    return (
        bool(separator)
        and _composition_sqlite_symbol_module(source, module)
        and symbol in COMPOSITION_SQLITE_SYMBOLS[module]
    )


def _approved_m2_fresh_init_migration(source: str, target: str) -> bool:
    return (
        source == "agentmonitor.composition.iam_fresh_init"
        and target == FRESH_INIT_MIGRATE_TARGET
    )


def _m01_sqlite_policy_symbol_module(source: str, target: str) -> bool:
    prefix = "agentmonitor.adapters.persistence.identity_access.sqlite"
    return (
        source == prefix or source.startswith(prefix + ".")
    ) and target == "agentmonitor.adapters.persistence._shared.sqlite.core.policy"


def _approved_m01_sqlite_policy_symbol(source: str, target: str) -> bool:
    module, separator, symbol = target.rpartition(".")
    return (
        bool(separator)
        and _m01_sqlite_policy_symbol_module(source, module)
        and symbol in M01_SQLITE_POLICY_SYMBOLS
    )


def _m01_adapter_port_symbol_module(source: str, target: str) -> bool:
    prefix = "agentmonitor.adapters.persistence.identity_access.sqlite"
    sqlite_owner = (
        source == prefix or source.startswith(prefix + ".")
    ) and target in M01_SQLITE_LAYER_SYMBOLS
    hasher_error = (
        source == "agentmonitor.adapters.identity_access.argon2_password"
        and target == "agentmonitor.modules.identity_access.application.errors"
    )
    return sqlite_owner or hasher_error


def _approved_m01_adapter_port_symbol(source: str, target: str) -> bool:
    module, separator, symbol = target.rpartition(".")
    return (
        bool(separator)
        and _m01_adapter_port_symbol_module(source, module)
        and symbol in M01_SQLITE_LAYER_SYMBOLS[module]
    )


def _m02_sqlite_policy_symbol_module(source: str, target: str) -> bool:
    prefix = "agentmonitor.adapters.persistence.registry.sqlite"
    return (
        source == prefix or source.startswith(prefix + ".")
    ) and target == "agentmonitor.adapters.persistence._shared.sqlite.core.policy"


def _approved_m02_sqlite_policy_symbol(source: str, target: str) -> bool:
    module, separator, symbol = target.rpartition(".")
    return (
        bool(separator)
        and _m02_sqlite_policy_symbol_module(source, module)
        and symbol in M02_SQLITE_POLICY_SYMBOLS
    )


def _m03_m06_sqlite_policy_symbol_module(source: str, target: str) -> bool:
    return (
        any(
            source == prefix or source.startswith(prefix + ".")
            for prefix in M03_M06_SQLITE_POLICY_PREFIXES
        )
        and target == "agentmonitor.adapters.persistence._shared.sqlite.core.policy"
    )


def _approved_m03_m06_sqlite_policy_symbol(source: str, target: str) -> bool:
    module, separator, symbol = target.rpartition(".")
    return (
        bool(separator)
        and _m03_m06_sqlite_policy_symbol_module(source, module)
        and symbol in M03_M06_SQLITE_POLICY_SYMBOLS
    )


def _m02_adapter_port_symbol_module(source: str, target: str) -> bool:
    prefix = "agentmonitor.adapters.persistence.registry.sqlite"
    return (
        source == prefix or source.startswith(prefix + ".")
    ) and target in M02_SQLITE_LAYER_SYMBOLS


def _approved_m02_adapter_port_symbol(source: str, target: str) -> bool:
    module, separator, symbol = target.rpartition(".")
    return (
        bool(separator)
        and _m02_adapter_port_symbol_module(source, module)
        and symbol in M02_SQLITE_LAYER_SYMBOLS[module]
    )


def _a01_provider_system_symbol_module(source: str, target: str) -> bool:
    prefix = "agentmonitor.adapters.providers.claude"
    return (
        source == prefix or source.startswith(prefix + ".")
    ) and target in A01_PROVIDER_SYSTEM_SYMBOLS


def _approved_a01_provider_system_symbol(source: str, target: str) -> bool:
    module, separator, symbol = target.rpartition(".")
    return (
        bool(separator)
        and _a01_provider_system_symbol_module(source, module)
        and symbol in A01_PROVIDER_SYSTEM_SYMBOLS[module]
    )


def _allowed(source: str, target: str, *, symbol_import: bool = False) -> bool:
    src, dst = source.split("."), target.split(".")
    if "utils" in dst or dst[0] in {"frontend", "backend"}:
        return False
    pure = src[1:2] == ["contracts"] or (
        src[1:2] == ["modules"] and src[3:4] == ["domain"]
    )
    if dst[0] != "agentmonitor":
        if pure or src[1:2] == ["modules"]:
            return dst[0] in PURE_IMPORTS
        if src[1:2] == ["api"]:
            return dst[0] not in {
                "sqlalchemy",
                "alembic",
                "sqlite3",
                "openai",
                "anthropic",
                "ollama",
            }
        return True
    if len(dst) < 2:
        return False
    if symbol_import and (
        _approved_composition_sqlite_symbol(source, target)
        or _approved_m2_fresh_init_migration(source, target)
        or _approved_m01_sqlite_policy_symbol(source, target)
        or _approved_m01_adapter_port_symbol(source, target)
        or _approved_m02_sqlite_policy_symbol(source, target)
        or _approved_m03_m06_sqlite_policy_symbol(source, target)
        or _approved_m02_adapter_port_symbol(source, target)
        or _approved_a01_provider_system_symbol(source, target)
    ):
        return True
    if any(part.startswith("_") for part in dst[1:]) and src[1:3] != dst[1:3]:
        return False
    if dst[1] == "contracts":
        if len(dst) >= 4 and dst[2] == "providers":
            return not any(part.startswith("_") for part in dst[3:])
        return (
            len(dst) in {3, 4}
            and dst[2] in CONTRACT_MODULES
            and (len(dst) == 3 or not dst[3].startswith("_"))
        )
    if pure:
        return src[1:2] == ["modules"] and dst[:4] == src[:4]
    if src[1:2] == ["modules"]:
        return (
            src[3:4] == ["application"]
            and dst[1:3] == src[1:3]
            and dst[3:4] in (["application"], ["domain"])
        )
    if src[1:2] == ["foundation"]:
        return dst[1] == "foundation"
    if src[1:2] == ["api"]:
        return dst[1] in {"api", "foundation"} or (
            dst[1] == "modules" and dst[3:4] == ["application"]
        )
    if src[1:2] == ["adapters"]:
        if dst[1] == "modules":
            return dst[3:5] == ["application", "ports"]
        if dst[1] == "adapters":
            if src[2:3] == ["providers"] and dst[2:3] == ["providers"]:
                return src[3:4] == dst[3:4]
            # Concrete adapters are wired by composition, not by other owners.
            return src[2:4] == dst[2:4]
        return dst[1] == "foundation"
    if src[1:2] == ["composition"]:
        return dst[1] in {"composition", "api", "foundation", "adapters"} or (
            dst[1] == "modules" and dst[3:4] == ["application"]
        )
    return False


def _imports(
    tree: ast.Module, module: str, is_package: bool
) -> tuple[list[tuple[int, str, bool]], list[tuple[int, str]]]:
    edges: list[tuple[int, str, bool]] = []
    errors: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            edges.extend((node.lineno, alias.name, False) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if any(alias.name == "*" for alias in node.names):
                errors.append((node.lineno, "wildcard-import"))
                continue
            base = node.module or ""
            if node.level:
                package = module.split(".") if is_package else module.split(".")[:-1]
                if node.level > len(package):
                    errors.append((node.lineno, "invalid-relative-import"))
                    continue
                base = ".".join(
                    package[: len(package) - node.level + 1] + ([base] if base else [])
                )
            # Keep contract symbols until privacy and adoption checks complete;
            # aliases cannot hide the original imported name.
            if base.startswith("agentmonitor.contracts."):
                edges.extend(
                    (node.lineno, f"{base}.{alias.name}", True) for alias in node.names
                )
            elif base.startswith("agentmonitor"):
                # `from package import Symbol` may be a symbol or a module.
                # Check the base direction as well as each child for bypasses.
                if (
                    base
                    not in {
                        "agentmonitor",
                        "agentmonitor.contracts",
                    }
                    and not (
                        base.startswith("agentmonitor.modules.")
                        and len(base.split(".")) == 3
                    )
                    and not _composition_sqlite_symbol_module(module, base)
                    and not _m01_sqlite_policy_symbol_module(module, base)
                    and not _m01_adapter_port_symbol_module(module, base)
                    and not _m02_sqlite_policy_symbol_module(module, base)
                    and not _m03_m06_sqlite_policy_symbol_module(module, base)
                    and not _m02_adapter_port_symbol_module(module, base)
                    and not _a01_provider_system_symbol_module(module, base)
                    and not _allowed(module, base)
                ):
                    edges.append((node.lineno, base, False))
                else:
                    edges.extend(
                        (node.lineno, f"{base}.{alias.name}", True)
                        for alias in node.names
                    )
            else:
                edges.append((node.lineno, base, False))
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {
                "__import__",
                "eval",
                "exec",
            }:
                errors.append((node.lineno, "dynamic-import"))
            elif isinstance(node.func, ast.Attribute) and node.func.attr in {
                "import_module",
                "__import__",
                "exec_module",
                "load_module",
            }:
                errors.append((node.lineno, "dynamic-import"))
    return edges, errors


def find_forbidden_imports(root: Path) -> list[str]:
    """Inspect real Python ASTs without importing code; sorted path:line:reason.

    Unreadable/symlinked sources, parse failures and dynamic/wildcard imports
    fail closed. This checks static ownership, not behavior inside functions.
    """
    paths, errors = _sources(root)
    graph: dict[str, set[str]] = {}
    locations: list[tuple[str, str, int, str]] = []
    module_paths: dict[str, list[Path]] = {}
    for path in paths:
        module_paths.setdefault(_module(path, root), []).append(path)
    collisions = [
        f"{path.relative_to(root)}:0:duplicate-module:{module}"
        for module, candidates in module_paths.items()
        if len(candidates) > 1
        for path in candidates
    ]
    if collisions:
        return sorted(set(errors + collisions))
    modules = {module: candidates[0] for module, candidates in module_paths.items()}
    contract_imports: list[tuple[Path, int, str]] = []
    for module, path in modules.items():
        relative = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, SyntaxError):
            errors.append(f"{relative}:1:invalid-python")
            continue
        edges, failures = _imports(tree, module, path.name == "__init__.py")
        errors.extend(f"{relative}:{line}:{reason}" for line, reason in failures)
        graph.setdefault(module, set())
        for line, target, symbol_import in edges:
            if not _allowed(module, target, symbol_import=symbol_import):
                errors.append(f"{relative}:{line}:{target}")
            elif target.startswith("agentmonitor.contracts."):
                contract_imports.append((path, line, target))
            resolved = target
            while resolved not in modules and "." in resolved:
                resolved = resolved.rsplit(".", 1)[0]
            if resolved in modules and resolved != module:
                graph[module].add(resolved)
                locations.append((module, relative, line, resolved))

    def reaches(start: str, destination: str) -> bool:
        pending = [start]
        visited: set[str] = set()
        while pending:
            current = pending.pop()
            if current == destination:
                return True
            if current not in visited:
                visited.add(current)
                pending.extend(graph.get(current, ()))
        return False

    for module, relative, line, target in locations:
        if reaches(target, module):
            errors.append(f"{relative}:{line}:cycle:{target}")
    errors.extend(_contract_consumption_errors(root, modules, contract_imports))
    return sorted(set(errors))


def _catalog_rebindings(
    tree: ast.Module, catalog_names: set[str]
) -> list[tuple[int, str]]:
    """Find module-name mutations without treating local bindings as exports.

    Compound statements keep their enclosing scope. Functions/classes introduce
    local scopes except explicit globals; their defaults/decorators/bases are
    evaluated in the enclosing scope. Comprehension iteration targets are local,
    while assignment expressions bind in the containing non-comprehension scope.
    """
    result: list[tuple[int, str]] = []
    declared_names: set[str] = set()

    def globals_in(body: list[ast.stmt]) -> set[str]:
        names: set[str] = set()
        pending: list[ast.AST] = list(body)
        while pending:
            node = pending.pop()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(node, ast.Global):
                names.update(node.names)
            pending.extend(ast.iter_child_nodes(node))
        return names & catalog_names

    def visit(node: ast.AST, scope: set[str], walrus_scope: set[str]) -> None:
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            if node.id in scope:
                result.append((node.lineno, node.id))
        elif isinstance(node, ast.NamedExpr):
            visit(node.target, walrus_scope, walrus_scope)
            visit(node.value, scope, walrus_scope)
            return
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name in scope:
                if node.name in declared_names:
                    result.append((node.lineno, node.name))
                declared_names.add(node.name)
            for child in ast.iter_child_nodes(node):
                if child not in node.body:
                    visit(child, scope, walrus_scope)
            local_globals = globals_in(node.body)
            for statement in node.body:
                visit(statement, local_globals, local_globals)
            return
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound_name = alias.asname or alias.name.split(".")[0]
                if bound_name in scope and (
                    bound_name != alias.name or bound_name in declared_names
                ):
                    result.append((node.lineno, bound_name))
        elif isinstance(node, ast.Lambda):
            visit(node.args, scope, walrus_scope)
            visit(node.body, set(), set())
            return
        elif isinstance(
            node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
        ):
            # The first iterable is evaluated in the enclosing scope. All
            # remaining comprehension bindings live in its implicit local scope.
            for index, generator in enumerate(node.generators):
                visit(generator.iter, scope if index == 0 else set(), walrus_scope)
                visit(generator.target, set(), walrus_scope)
                for condition in generator.ifs:
                    visit(condition, set(), walrus_scope)
            if isinstance(node, ast.DictComp):
                visit(node.key, set(), walrus_scope)
                visit(node.value, set(), walrus_scope)
            else:
                visit(node.elt, set(), walrus_scope)
            return
        elif isinstance(node, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)):
            if node.name is not None and node.name in scope:
                result.append((node.lineno, node.name))
        elif isinstance(node, ast.MatchMapping):
            if node.rest is not None and node.rest in scope:
                result.append((node.lineno, node.rest))
        for child in ast.iter_child_nodes(node):
            visit(child, scope, walrus_scope)

    visit(tree, catalog_names, catalog_names)
    return sorted(set(result))


def _class_string_literal(node: ast.ClassDef, field: str) -> str | None:
    """Read a literal contract declaration without executing contract source."""
    bindings = 0
    pending: list[ast.AST] = list(node.body)
    while pending:
        current = pending.pop()
        if isinstance(current, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if (
            isinstance(current, ast.Name)
            and current.id == field
            and isinstance(current.ctx, (ast.Store, ast.Del))
        ):
            bindings += 1
        pending.extend(ast.iter_child_nodes(current))
    if bindings != 1:
        return None
    matches: list[str] = []
    for statement in node.body:
        value: ast.expr | None = None
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == field
            for target in statement.targets
        ):
            value = statement.value
        elif (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
            and statement.target.id == field
        ):
            value = statement.value
        if value is not None:
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                return None
            matches.append(value.value)
    return matches[0] if len(matches) == 1 else None


def _contract_consumption_errors(
    root: Path,
    modules: dict[str, Path],
    imports: list[tuple[Path, int, str]],
) -> list[str]:
    """Resolve real published definitions and semantic owners against adoption.

    A symbol import needs its declared ID. A module import grants access to all
    its contracts, so all must be adopted. Public support values with no separate
    catalog ID require adoption of at least one contract from their defining
    family; re-exports and unresolved symbols are not accepted as declarations.
    """
    if not imports:
        return []
    errors: list[str] = []
    try:
        documents = _policy_documents(root)
        contracts = _records(documents["contract-baseline"], "contracts")
        plans = _records(documents["contract-adoption"], "plans")
        ownership = documents["parallel-ownership"]
        definitions = {str(entry["name"]): entry for entry in contracts}
        definitions_by_id = {str(entry["id"]): entry for entry in contracts}
        permissions = {
            str(plan["id"]): set(
                _strings(plan["consumes"]) + _strings(plan["publishes"])
            )
            for plan in plans
        }
        allocations = [
            (pattern, str(unit["id"]))
            for unit in _records(ownership, "units")
            for pattern in _strings(unit["write_paths"])
        ]
        # Shared writers are edit custodians. Only an unambiguous semantic plan
        # may consume contracts; contract-file owners are resolved below instead.
        for shared in _records(ownership, "shared_writers"):
            owner = str(shared["semantic_owner"]).split()[0]
            if owner in permissions:
                allocations.extend(
                    (pattern, owner) for pattern in _strings(shared["paths"])
                )
        exports: dict[str, dict[str, str | None]] = {}
        families: dict[str, set[str]] = {}
        contract_owners: dict[str, str] = {}
        for module, path in modules.items():
            if not module.startswith("agentmonitor.contracts."):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            # A contract family may publish multiple concrete values. Admit only
            # literal declarations whose ID and owner match the policy catalog;
            # aliases and runtime-computed metadata cannot establish ownership.
            declared_contracts: dict[str, str] = {}
            declared_owners: set[str] = set()
            declared_support: dict[str, str] = {}
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                contract_id = _class_string_literal(node, "CONTRACT_ID")
                owner = _class_string_literal(node, "OWNER")
                record = definitions_by_id.get(contract_id or "")
                if (
                    record is not None
                    and owner == str(record["producer"])
                    and owner in permissions
                ):
                    declared_contracts[node.name] = str(record["id"])
                    declared_owners.add(owner)
                elif (
                    module.startswith("agentmonitor.contracts.providers.")
                    and contract_id is not None
                    and owner in permissions
                    and "CTR-PROV-008" in permissions[owner]
                ):
                    declared_contracts[node.name] = "CTR-PROV-008"
                    declared_owners.add(owner)
                elif (
                    module == "agentmonitor.contracts.identity_access_v1"
                    and node.name == "SecretInputV1"
                    and contract_id is None
                    and owner is None
                ):
                    declared_support[node.name] = "CTR-IAM-004"
            names: set[str] = set()
            rebindings = _catalog_rebindings(
                tree,
                set(definitions) | set(declared_contracts) | set(declared_support),
            )
            rebound_names = {name for _, name in rebindings}
            errors.extend(
                f"{path.relative_to(root)}:{line}:catalog-name-rebinding:{name}"
                for line, name in rebindings
            )
            for node in tree.body:
                if isinstance(
                    node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    names.add(node.name)
                elif isinstance(node, ast.Assign):
                    names.update(n.id for n in node.targets if isinstance(n, ast.Name))
                elif isinstance(node, ast.AnnAssign) and isinstance(
                    node.target, ast.Name
                ):
                    names.add(node.target.id)
            # Assignments cannot establish a catalog identity or replace a real
            # declaration, even if a class of that name appears earlier/later.
            names.difference_update(rebound_names)
            exports[module] = {
                name: (
                    str(definitions[name]["id"])
                    if name in definitions
                    else declared_contracts.get(name) or declared_support.get(name)
                )
                for name in names
                if name in definitions
                or name in SUPPORT_SYMBOLS.get(module, set())
                or name in declared_contracts
                or name in declared_support
            }
            families[module] = {
                value for value in exports[module].values() if value is not None
            }
            owners = {
                str(definitions[name]["producer"])
                for name in names
                if name in definitions
            }
            if (set(declared_contracts) | set(declared_support)) & names:
                owners.update(declared_owners)
                if set(declared_support) & names:
                    owners.add("PLAN-M01")
            if len(owners) == 1:
                contract_owners[module] = owners.pop()
        for path, line, target in imports:
            relative = path.relative_to(root).as_posix()
            prefix = f"{relative}:{line}"
            source_module = _module(path, root)
            source_owners = (
                [contract_owners[source_module]]
                if source_module in contract_owners
                else [
                    owner
                    for pattern, owner in allocations
                    if fnmatch.fnmatchcase(relative, pattern)
                ]
            )
            if len(source_owners) != 1 or source_owners[0] not in permissions:
                errors.append(f"{prefix}:unresolved-contract-owner")
                continue
            allowed = permissions[source_owners[0]]
            parts = target.split(".")
            module = target if target in exports else target.rpartition(".")[0]
            if module not in exports or not families[module]:
                errors.append(f"{prefix}:unresolved-contract-module")
                continue
            required = families[module]
            if target != module:
                symbol = parts[-1]
                if symbol not in exports[module]:
                    errors.append(f"{prefix}:unresolved-contract-symbol")
                    continue
                contract_id = exports[module][symbol]
                if contract_id is None:
                    if not required & allowed:
                        errors.append(f"{prefix}:undeclared-contract-support:{target}")
                    continue
                required = {contract_id}
            errors.extend(
                f"{prefix}:undeclared-contract:{contract_id}"
                for contract_id in sorted(required - allowed)
            )
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, SyntaxError):
        return [
            f"{path.relative_to(root)}:{line}:unresolved-contract-policy"
            for path, line, _ in imports
        ]
    return errors


def _policy_documents(root: Path) -> dict[str, dict[str, object]]:
    documents: dict[str, dict[str, object]] = {}
    for name in ("contract-baseline", "contract-adoption", "parallel-ownership"):
        path = root / "docs/plans" / f"{name}.toml"
        if path.is_symlink():
            raise ValueError("symlink-manifest")
        documents[name] = tomllib.loads(path.read_text(encoding="utf-8"))
    return documents


def _records(document: dict[str, object], key: str) -> list[dict[str, object]]:
    value = document[key]
    if not isinstance(value, list) or not value:
        raise ValueError("missing-records")
    result: list[dict[str, object]] = []
    for record in value:
        if not isinstance(record, dict) or not all(isinstance(k, str) for k in record):
            raise ValueError("invalid-record")
        result.append(record)
    return result


def _strings(value: object) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("invalid-string-list")
    return [str(item) for item in value]


def find_ownership_violations(root: Path) -> list[str]:
    """Validate actual source writers and exact contract producer/version records.

    Draft maturity remains historical metadata, not implementation authorization.
    The root task approval is separate and does not rewrite the planning baseline.
    """
    errors: list[str] = []
    paths, source_errors = _sources(root)
    errors.extend(source_errors)
    try:
        documents = _policy_documents(root)
        contracts = _records(documents["contract-baseline"], "contracts")
        plans = _records(documents["contract-adoption"], "plans")
        ownership = documents["parallel-ownership"]
        writers: list[tuple[str, str]] = []
        for unit in _records(ownership, "units"):
            writers.extend(
                (pattern, str(unit["id"])) for pattern in _strings(unit["write_paths"])
            )
        for shared in _records(ownership, "shared_writers"):
            writer = shared["wave_writer"]
            if not isinstance(writer, str) or not writer.strip():
                raise ValueError("missing-writer")
            writers.extend((pattern, writer) for pattern in _strings(shared["paths"]))
        seen: set[str] = set()
        for entry in contracts:
            contract_id = str(entry["id"])
            if contract_id in seen:
                errors.append(f"{contract_id}:duplicate-contract")
            seen.add(contract_id)
            producers = [
                plan["id"]
                for plan in plans
                if contract_id in _strings(plan["publishes"])
            ]
            if producers != [entry["producer"]]:
                errors.append(f"{contract_id}:contract-producer-count")
            if entry["version"] != "1.0.0":
                errors.append(f"{contract_id}:contract-version")
            if entry["maturity"] not in {"proposed_aligned", "evidence_blocked"}:
                errors.append(f"{contract_id}:contract-maturity")
        if not TASK_CONTRACT_IDS <= seen:
            errors.append("contracts:missing-task-contract")
        for path in paths:
            relative = path.relative_to(root).as_posix()
            owners = [
                owner
                for pattern, owner in writers
                if fnmatch.fnmatchcase(relative, pattern)
            ]
            if len(owners) != 1:
                errors.append(f"{relative}:source-owner-count")
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        errors.append("docs/plans:invalid-or-missing-ownership-manifest")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    violations = sorted(
        set(find_forbidden_imports(args.root) + find_ownership_violations(args.root))
    )
    for violation in violations:
        print(violation)
    print(
        f"boundaries: {'FAIL' if violations else 'PASS'} ({len(violations)} violations)"
    )
    return int(bool(violations))


if __name__ == "__main__":
    raise SystemExit(main())
