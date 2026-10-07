"""Fail-closed scope checks for the M5 Codex critical mutation lane."""

import tomllib
from pathlib import Path
from typing import cast

EXPECTED_CODEX_TARGETS = {
    "src/agentmonitor/adapters/providers/codex/authentication/identity.py",
    "src/agentmonitor/adapters/providers/codex/manifest.py",
    "src/agentmonitor/adapters/providers/codex/subscription/mapper.py",
    "src/agentmonitor/adapters/providers/codex/subscription/schema.py",
    "src/agentmonitor/adapters/providers/codex/subscription/source.py",
}
EXPECTED_CODEX_TESTS = {
    "tests/adapters/providers/codex/test_identity_parser.py",
    "tests/adapters/providers/codex/test_manifest.py",
    "tests/adapters/providers/codex/test_security_policy.py",
    "tests/adapters/providers/codex/test_subscription_source_parser.py",
    "tests/adapters/providers/codex/test_critical_mutation_policies.py",
    "tests/adapters/providers/codex/unit/test_subscription_mapper.py",
}


def _mutation_config() -> dict[str, object]:
    for candidate in (
        Path.cwd() / "pyproject.toml",
        Path(__file__).resolve().parents[2] / "backend/pyproject.toml",
    ):
        if not candidate.is_file():
            continue
        document = tomllib.loads(candidate.read_text(encoding="utf-8"))
        tool = document.get("tool")
        if isinstance(tool, dict) and isinstance(tool.get("mutmut"), dict):
            return cast(dict[str, object], tool["mutmut"])
    raise AssertionError("mutation_config_missing")


def test_auto_mutation_selects_every_m5_codex_critical_policy_surface() -> None:
    """M5-CDX-GATE-012: parser, mapper, admission, and security stay selected."""

    config = _mutation_config()
    targets = config["only_mutate"]
    tests = config["pytest_add_cli_args_test_selection"]
    assert isinstance(targets, list)
    assert isinstance(tests, list)
    assert EXPECTED_CODEX_TARGETS <= set(targets)
    assert EXPECTED_CODEX_TESTS <= set(tests)
    assert config["mutate_only_covered_lines"] is True


def test_codex_mutation_targets_and_tests_are_exact_without_duplicates() -> None:
    config = _mutation_config()
    targets = config["only_mutate"]
    tests = config["pytest_add_cli_args_test_selection"]
    assert isinstance(targets, list) and len(targets) == len(set(targets))
    assert isinstance(tests, list) and len(tests) == len(set(tests))
    assert all(isinstance(path, str) and path.endswith(".py") for path in targets)
    assert all(isinstance(path, str) and path.endswith(".py") for path in tests)
