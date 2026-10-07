"""Run the admitted M3 and M5 critical pure-policy mutation gate."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import tomllib
from collections.abc import Mapping
from hashlib import sha256
from importlib import metadata
from pathlib import Path
from shutil import copy2, copytree, which
from typing import cast

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
PYTHON = BACKEND / ".venv/bin/python"
MUTMUT = BACKEND / ".venv/bin/mutmut"
MUTMUT_VERSION = "3.8.0"
RUNTIME_CONTRACT = Path("src/agentmonitor/contracts/runtime_observation_v1.py")
RUNTIME_CONTRACT_SHA256 = (
    "0733bf799efeaa6d047e2dbf51e3ba79ca309feb39a69b2a17a18b1cf8826ecc"
)
M3_TARGETS = (
    Path("src/agentmonitor/modules/capacity/domain/health.py"),
    Path("src/agentmonitor/modules/runtime_observation/application/correlation.py"),
    Path("src/agentmonitor/modules/runtime_observation/application/state.py"),
)
CODEX_TARGETS = (
    Path("src/agentmonitor/adapters/providers/codex/authentication/identity.py"),
    Path("src/agentmonitor/adapters/providers/codex/manifest.py"),
    Path("src/agentmonitor/adapters/providers/codex/subscription/mapper.py"),
    Path("src/agentmonitor/adapters/providers/codex/subscription/schema.py"),
    Path("src/agentmonitor/adapters/providers/codex/subscription/source.py"),
)
TARGETS = (*M3_TARGETS, *CODEX_TARGETS)
M3_PURE_TESTS = (
    Path("tests/capacity/test_quantity_and_health.py"),
    Path("tests/runtime_observation/test_contracts.py"),
    Path("tests/runtime_observation/test_runtime_state_policy.py"),
)
CODEX_PURE_TESTS = (
    Path("tests/adapters/providers/codex/test_identity_parser.py"),
    Path("tests/adapters/providers/codex/test_manifest.py"),
    Path("tests/adapters/providers/codex/test_security_policy.py"),
    Path("tests/adapters/providers/codex/test_subscription_source_parser.py"),
    Path("tests/adapters/providers/codex/test_critical_mutation_policies.py"),
    Path("tests/adapters/providers/codex/unit/test_subscription_mapper.py"),
)
PURE_TESTS = (*M3_PURE_TESTS, *CODEX_PURE_TESTS)
MUTATION_POLICY_TESTS = (
    (
        ROOT / "tools/automation/test_m3_critical_mutation_policies.py",
        Path("tests/mutation/test_m3_critical_mutation_policies.py"),
    ),
    (
        ROOT / "tools/automation/test_m5_codex_mutation_policies.py",
        Path("tests/mutation/test_m5_codex_mutation_policies.py"),
    ),
)
NON_KILLED_STATUSES = (
    "survived",
    "no_tests",
    "skipped",
    "suspicious",
    "timeout",
    "check_was_interrupted_by_user",
    "segfault",
)
EQUIVALENT_MUTANT_SHA256 = {
    "agentmonitor.modules.runtime_observation.application.state."
    "x_evaluate_possible_stall__mutmut_87": (
        "8539853ece464bc0c4af320efe5aa058df373b75ffc420f30ca145ccf240bf5e"
    ),
    "agentmonitor.modules.runtime_observation.application.state."
    "x_evaluate_possible_stall__mutmut_89": (
        "2eb84169cf30657e8ea06c00d7c0b608e38c2c2b74ddf57f5c2e5d1b21e26fab"
    ),
    "agentmonitor.modules.runtime_observation.application.state."
    "x_evaluate_possible_stall__mutmut_90": (
        "a30765e47600929c1038dc476d9ab843d1216c8b755b316fc59c0660d2b8c300"
    ),
    "agentmonitor.modules.runtime_observation.application.state."
    "x_evaluate_possible_stall__mutmut_92": (
        "f079a5e108a795526de11881ed3f27b61bcfaeee137831d8e9c678f72f649f1e"
    ),
    "agentmonitor.modules.runtime_observation.application.state."
    "x_evaluate_possible_stall__mutmut_93": (
        "ddc77fb139c1f11378491b1a45d3e6431f10e5561c1372155f5512267a5e396f"
    ),
    "agentmonitor.modules.runtime_observation.application.correlation."
    "x_decide_session_correlation__mutmut_35": (
        "e3384a752eb05831f9f1ffd404ad6ff4eb0fe52aa84d92610e491922fa1cbd89"
    ),
    "agentmonitor.modules.runtime_observation.application.correlation."
    "x_decide_session_correlation__mutmut_52": (
        "a5dc71272f40a24fc6039da92948cea11deae3844060a421829af267c1e24037"
    ),
    # Python treats UTF-8 encoding names case-insensitively.
    "agentmonitor.adapters.providers.codex.authentication.identity."
    "x_parse_account_identity_v1__mutmut_114": (
        "153ca0608e11f01fc3af856d1b56f75bc206179716b10bfb59007d69d6c37478"
    ),
    # typing.cast returns its second argument unchanged at runtime; changing only
    # either type expression cannot change this pure parser's runtime behavior.
    "agentmonitor.adapters.providers.codex.subscription.source.x__bucket__mutmut_41": (
        "3967069aee6c6f276a2ff69f67e5109c7b089789f40fbbdcebbb6b749a88a746"
    ),
    "agentmonitor.adapters.providers.codex.subscription.source.x__bucket__mutmut_50": (
        "3ac220acee297a5c4a2cb3619fa8d9ee04e3e383627ba19478d13d9220d7e4ff"
    ),
}


def equivalence_invariants_match(content: bytes) -> bool:
    """Bind equivalent classifications to their exact supporting contract."""
    return sha256(content).hexdigest() == RUNTIME_CONTRACT_SHA256


def mutation_config_matches(config: object) -> bool:
    """Require the executed source and test selectors to match this runner."""
    if not isinstance(config, Mapping):
        return False
    return (
        config.get("source_paths") == ["src/agentmonitor"]
        and config.get("only_mutate") == [str(path) for path in TARGETS]
        and config.get("pytest_add_cli_args") == ["-q", "-p", "no:cacheprovider"]
        and config.get("pytest_add_cli_args_test_selection")
        == [
            str(path)
            for path in (
                *PURE_TESTS,
                *(destination for _source, destination in MUTATION_POLICY_TESTS),
            )
        ]
        and config.get("mutate_only_covered_lines") is True
        and config.get("process_isolation") == "fork"
        and config.get("use_git_change_detection") is False
        and config.get("on_dependency_change") == "rerun"
    )


def _workspace_policy_matches(workspace: Path) -> bool:
    try:
        manifest = tomllib.loads(
            (workspace / "pyproject.toml").read_text(encoding="utf-8")
        )
        return mutation_config_matches(manifest["tool"]["mutmut"]) and (
            equivalence_invariants_match((workspace / RUNTIME_CONTRACT).read_bytes())
        )
    except (KeyError, OSError, TypeError, tomllib.TOMLDecodeError):
        return False


def mutation_summary_passes(
    summary: Mapping[str, object], *, accepted_equivalent_count: int = 0
) -> bool:
    """Require every non-equivalent mutant killed and no hidden verdict class."""
    keys = ("total", "killed", *NON_KILLED_STATUSES)
    if any(type(summary.get(key)) is not int for key in keys):
        return False
    values: dict[str, int] = {key: cast(int, summary[key]) for key in keys}
    if (
        values["total"] <= 0
        or accepted_equivalent_count < 0
        or values["survived"] != accepted_equivalent_count
        or values["killed"] + accepted_equivalent_count != values["total"]
    ):
        return False
    if any(values[key] != 0 for key in NON_KILLED_STATUSES if key != "survived"):
        return False
    return (
        sum(values[key] for key in ("killed", *NON_KILLED_STATUSES)) == values["total"]
    )


def _surviving_mutant_names(results: str) -> tuple[str, ...]:
    names = re.findall(r"^\s*([^\s:]+): survived\s*$", results, flags=re.MULTILINE)
    return tuple(sorted(names))


def _accepted_equivalent_count(
    *, workspace: Path, environment: Mapping[str, str], results: str
) -> int | None:
    if not _workspace_policy_matches(workspace):
        return None
    survivors = _surviving_mutant_names(results)
    if not set(survivors).issubset(EQUIVALENT_MUTANT_SHA256):
        return None
    for mutant_name in survivors:
        shown = _run(
            [str(MUTMUT), "show", mutant_name],
            cwd=workspace,
            environment=environment,
        )
        if shown.returncode != 0:
            return None
        digest = sha256(shown.stdout.encode("utf-8")).hexdigest()
        if digest != EQUIVALENT_MUTANT_SHA256[mutant_name]:
            return None
    return len(survivors)


def _copy_workspace(destination: Path) -> None:
    copy2(BACKEND / "pyproject.toml", destination / "pyproject.toml")
    copy2(BACKEND / "uv.lock", destination / "uv.lock")
    copytree(BACKEND / "src", destination / "src")
    for relative in PURE_TESTS:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        copy2(BACKEND / relative, target)
    for source, relative in MUTATION_POLICY_TESTS:
        mutation_policy_target = destination / relative
        mutation_policy_target.parent.mkdir(parents=True, exist_ok=True)
        copy2(source, mutation_policy_target)


def _run(
    command: list[str],
    *,
    cwd: Path,
    environment: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=None if environment is None else dict(environment),
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )


def _codex_executable() -> Path | None:
    found = which("codex")
    if found is None:
        return None
    candidate = Path(found)
    if not candidate.is_absolute() or not candidate.is_file():
        return None
    return candidate


def _tool_ready() -> bool:
    try:
        codex = _codex_executable()
        return (
            PYTHON.is_file()
            and MUTMUT.is_file()
            and codex is not None
            and metadata.version("mutmut") == MUTMUT_VERSION
            and all((BACKEND / path).is_file() for path in (*TARGETS, *PURE_TESTS))
            and all(source.is_file() for source, _relative in MUTATION_POLICY_TESTS)
            and _workspace_policy_matches(BACKEND)
        )
    except (metadata.PackageNotFoundError, OSError):
        return False


def baseline_policy_command() -> list[str]:
    """Run exact checkout tests without requiring caller source-path settings."""
    codex = _codex_executable()
    executable_path = os.defpath
    if codex is not None:
        executable_path = os.pathsep.join((str(codex.parent), os.defpath))
    return [
        str(PYTHON),
        "-c",
        (
            "import os,sys; os.environ['PATH']=sys.argv.pop(1); "
            "sys.path.insert(0,sys.argv.pop(1)); "
            "import pytest; raise SystemExit(pytest.main(sys.argv[1:]))"
        ),
        executable_path,
        str(BACKEND / "src"),
        "-q",
        *(str(BACKEND / path) for path in PURE_TESTS),
        *(str(source) for source, _relative in MUTATION_POLICY_TESTS),
    ]


def main() -> int:
    if not hasattr(os, "fork"):
        print("M3/M5 MUTATION: BLOCKED — fork_process_isolation_unavailable")
        return 3
    if not _tool_ready():
        print("M3/M5 MUTATION: BLOCKED — admitted_mutmut_toolchain_unavailable")
        return 3

    baseline = _run(baseline_policy_command(), cwd=ROOT)
    if baseline.returncode != 0:
        print("M3/M5 MUTATION: FAILED — selected_clean_tests_failed")
        print((baseline.stdout + baseline.stderr)[-4_000:])
        return 1

    codex = _codex_executable()
    if codex is None:
        print("M3/M5 MUTATION: BLOCKED — admitted_codex_executable_unavailable")
        return 3
    environment = {
        "PATH": os.pathsep.join((str(MUTMUT.parent), str(codex.parent), os.defpath)),
        "PYTHONHASHSEED": "0",
    }
    try:
        with tempfile.TemporaryDirectory(prefix="agentmonitor-m3-m5-mutation-") as raw:
            workspace = Path(raw) / "backend"
            workspace.mkdir(mode=0o700)
            _copy_workspace(workspace)
            if not _workspace_policy_matches(workspace):
                print("M3/M5 MUTATION: FAILED — mutation_policy_drift")
                return 1
            mutation = _run(
                [str(MUTMUT), "run", "--max-children", "4"],
                cwd=workspace,
                environment=environment,
            )
            if mutation.returncode != 0:
                print("M3/M5 MUTATION: FAILED — mutmut_execution_failed")
                print((mutation.stdout + mutation.stderr)[-4_000:])
                return 1
            exported = _run(
                [str(MUTMUT), "export-cicd-stats"],
                cwd=workspace,
                environment=environment,
            )
            stats_path = workspace / "mutants/mutmut-cicd-stats.json"
            if exported.returncode != 0 or not stats_path.is_file():
                print("M3/M5 MUTATION: FAILED — mutation_summary_unavailable")
                return 1
            try:
                summary = json.loads(stats_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                print("M3/M5 MUTATION: FAILED — mutation_summary_invalid")
                return 1
            results = _run(
                [str(MUTMUT), "results"],
                cwd=workspace,
                environment=environment,
            )
            accepted_equivalent_count = (
                None
                if results.returncode != 0
                else _accepted_equivalent_count(
                    workspace=workspace,
                    environment=environment,
                    results=results.stdout + results.stderr,
                )
            )
            if (
                not isinstance(summary, dict)
                or accepted_equivalent_count is None
                or not mutation_summary_passes(
                    summary,
                    accepted_equivalent_count=accepted_equivalent_count,
                )
            ):
                print("M3/M5 MUTATION: FAILED — non_killed_or_unclassified_mutant")
                print(json.dumps(summary, sort_keys=True))
                print("M3/M5 MUTATION RESULTS:")
                print("\n".join((results.stdout + results.stderr).splitlines()[:200]))
                return 1
            safe_summary = {
                key: summary[key] for key in ("total", "killed", *NON_KILLED_STATUSES)
            }
            safe_summary["accepted_equivalent"] = accepted_equivalent_count
    except (OSError, subprocess.TimeoutExpired):
        print("M3/M5 MUTATION: FAILED — mutation_runner_unavailable")
        return 1

    print(
        "M3/M5 MUTATION: CLEAN TESTS PASSED "
        f"({len(PURE_TESTS) + len(MUTATION_POLICY_TESTS)} selected files)"
    )
    print("M3/M5 MUTATION: TARGETS — " + ", ".join(str(path) for path in TARGETS))
    print("M3/M5 MUTATION: " + json.dumps(safe_summary, sort_keys=True))
    print("M3/M5 MUTATION: PASSED — all non-equivalent critical-policy mutants killed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
