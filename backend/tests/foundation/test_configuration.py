"""FND-CFG-001..004: real isolated files/processes; no operator configuration."""

import dataclasses
import importlib
import json
import pickle
import secrets
import subprocess
import sys
import traceback
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from agentmonitor.contracts.configuration_v1 import ConfigurationRegistryV1

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend/src"))
COUNT = "AGENTMONITOR_TEST_WORKER_COUNT"
SECRET = "AGENTMONITOR_TEST_BOOTSTRAP_SECRET"


def implementation() -> ModuleType:
    assert (ROOT / "backend/src/agentmonitor/foundation/configuration.py").is_file(), (
        "FND-CFG: explicit-path configuration validation is not implemented"
    )
    return importlib.import_module("agentmonitor.foundation.configuration")


def registry(*, required: bool = False) -> "ConfigurationRegistryV1":
    from agentmonitor.contracts.configuration_v1 import (
        ConfigurationDescriptorV1,
        ConfigurationRegistryV1,
    )

    count = ConfigurationDescriptorV1(
        external_name=COUNT,
        internal_name="worker_count",
        value_type="integer",
        validation_rule="positive_integer",
        safe_default=None if required else "1",
        secret_class="non_secret",
        owner="PLAN-FND",
        unit=None,
        required=required,
        sources_low_to_high=("default", "config_file", "environment", "cli"),
        reload_behavior="restart",
        first_version="1.0.0",
        deprecated_version=None,
        removed_version=None,
        consequences=("technical-validation-only",),
        test_ids=("FND-CFG-001", "FND-CFG-003"),
        documentation_ids=("PLAN-FND-3.9",),
    )
    secret = dataclasses.replace(
        count,
        external_name=SECRET,
        internal_name="bootstrap_secret",
        value_type="secret",
        validation_rule="nonempty",
        safe_default=None,
        secret_class="agentmonitor",
        sources_low_to_high=("config_file", "environment"),
    )
    return ConfigurationRegistryV1(descriptors=(count, secret))


def config_file(tmp_path: Path, content: str = "") -> Path:
    path = tmp_path / "selected.env"
    path.touch(mode=0o600)
    path.write_text(content, encoding="utf-8")
    return path


def test_explicit_registry_precedence_and_immutable_receipt(tmp_path: Path) -> None:
    config = implementation()
    path = config_file(tmp_path, f"{COUNT}=2\n")
    environment = {COUNT: "3"}
    cli = config.BootstrapCliOptionsV1(registry=registry(), values=((COUNT, "4"),))
    receipt = config.load_bootstrap_configuration(path, environment, cli)
    assert receipt.non_secret_sources == ((COUNT, "cli"),)
    assert receipt.secret_presence == ((SECRET, False),)
    assert receipt.owners == ("PLAN-FND",)
    assert receipt.configuration_version == "1.0.0"
    assert environment == {COUNT: "3"}
    assert path.read_text() == f"{COUNT}=2\n"
    with pytest.raises(dataclasses.FrozenInstanceError):
        receipt.configuration_version = "2.0.0"
    for supplied, expected in (({COUNT: "3"}, "environment"), ({}, "config_file")):
        receipt = config.load_bootstrap_configuration(
            path, supplied, config.BootstrapCliOptionsV1(registry=registry())
        )
        assert receipt.non_secret_sources == ((COUNT, expected),)


@pytest.mark.parametrize("name", ["PATH", "OPENAI_API_KEY", "AGENTMONITOR_UNKNOWN"])
def test_unknown_environment_name_is_rejected(tmp_path: Path, name: str) -> None:
    config = implementation()
    with pytest.raises(config.BootstrapConfigurationError) as caught:
        config.load_bootstrap_configuration(
            config_file(tmp_path),
            {name: secrets.token_hex(24)},
            config.BootstrapCliOptionsV1(registry=registry()),
        )
    assert caught.value.code == "unknown_environment_name"
    assert caught.value.setting_name is None


@pytest.mark.parametrize(
    ("content", "error"),
    [
        (f"{COUNT}=0\n", "malformed_setting"),
        (f"{COUNT}=wrong\n", "malformed_setting"),
        (f"{COUNT}=1\n{COUNT}=2\n", "conflicting_setting"),
        ("AGENTMONITOR_UNKNOWN=1\n", "unknown_file_name"),
        ("not an assignment\n", "malformed_configuration"),
        (f"export {COUNT}=1\n", "unknown_file_name"),
        (f"{COUNT}=${{OTHER}}\n", "malformed_setting"),
    ],
)
def test_invalid_real_file_fails_closed(
    tmp_path: Path, content: str, error: str
) -> None:
    config = implementation()
    with pytest.raises(config.BootstrapConfigurationError) as caught:
        config.load_bootstrap_configuration(
            config_file(tmp_path, content),
            {},
            config.BootstrapCliOptionsV1(registry=registry()),
        )
    assert caught.value.code == error


def test_missing_required_and_secret_cli_are_rejected(tmp_path: Path) -> None:
    config = implementation()
    path = config_file(tmp_path)
    with pytest.raises(config.BootstrapConfigurationError) as missing:
        config.load_bootstrap_configuration(
            path, {}, config.BootstrapCliOptionsV1(registry=registry(required=True))
        )
    assert missing.value.code == "missing_required_setting"
    assert missing.value.setting_name == COUNT
    with pytest.raises(config.BootstrapConfigurationError) as secret_cli:
        config.load_bootstrap_configuration(
            path,
            {},
            config.BootstrapCliOptionsV1(
                registry=registry(), values=((SECRET, secrets.token_hex(24)),)
            ),
        )
    assert secret_cli.value.code == "forbidden_configuration_source"


@pytest.mark.parametrize("mode", [0o644, 0o620, 0o000, 0o700])
def test_owner_only_readable_regular_file_required(tmp_path: Path, mode: int) -> None:
    config = implementation()
    path = config_file(tmp_path)
    path.chmod(mode)
    with pytest.raises(config.BootstrapConfigurationError) as caught:
        config.load_bootstrap_configuration(
            path, {}, config.BootstrapCliOptionsV1(registry=registry())
        )
    assert caught.value.code == "unsafe_configuration_permissions"


def test_no_discovery_or_symlink_following(tmp_path: Path) -> None:
    config = implementation()
    path = config_file(tmp_path)
    (tmp_path / ".env").write_text("unregistered=must-not-be-read\n")
    cli = config.BootstrapCliOptionsV1(registry=registry())
    assert config.load_bootstrap_configuration(path, {}, cli).non_secret_sources == (
        (COUNT, "default"),
    )
    linked = tmp_path / "linked.env"
    linked.symlink_to(path)
    parent_link = tmp_path / "linked-parent"
    parent_link.symlink_to(tmp_path, target_is_directory=True)
    for invalid in (linked, parent_link / path.name, tmp_path, Path(".env")):
        with pytest.raises(config.BootstrapConfigurationError):
            config.load_bootstrap_configuration(invalid, {}, cli)
    with pytest.raises(config.BootstrapConfigurationError) as missing:
        config.load_bootstrap_configuration(tmp_path / "missing.env", {}, cli)
    assert missing.value.code == "configuration_unavailable"


def test_non_utf8_and_oversized_files_have_safe_errors(tmp_path: Path) -> None:
    config = implementation()
    path = config_file(tmp_path)
    for data in (bytes([255]), b"#" * 65537):
        path.write_bytes(data)
        with pytest.raises(config.BootstrapConfigurationError) as caught:
            config.load_bootstrap_configuration(
                path, {}, config.BootstrapCliOptionsV1(registry=registry())
            )
        assert caught.value.code in {
            "malformed_configuration",
            "configuration_too_large",
        }
        assert caught.value.__context__ is None


def test_secret_presence_repr_serialization_and_error_privacy(tmp_path: Path) -> None:
    config = implementation()
    canary = secrets.token_urlsafe(32)
    path = config_file(tmp_path, f"{SECRET}={canary}\n")
    cli = config.BootstrapCliOptionsV1(registry=registry())
    receipt = config.load_bootstrap_configuration(path, {}, cli)
    secret = config.SecretValueV1(canary)
    assert secret.presence == "configured"
    assert config.SecretValueV1(None).presence == "missing"
    assert receipt.secret_presence == ((SECRET, True),)
    assert SECRET not in dict(receipt.non_secret_sources)
    outputs = [
        repr(secret),
        str(secret),
        repr(receipt),
        json.dumps(dataclasses.asdict(receipt)),
    ]
    for serialize in (json.dumps, pickle.dumps, dataclasses.asdict):
        with pytest.raises(TypeError) as caught:
            serialize(secret)
        outputs.append(str(caught.value))
    path.write_text(f"{COUNT}={canary}\n")
    with pytest.raises(config.BootstrapConfigurationError) as caught:
        config.load_bootstrap_configuration(path, {}, cli)
    outputs.extend((str(caught.value), repr(caught.value), repr(caught.value.args)))
    assert caught.value.__context__ is None
    if any(canary in output for output in outputs):
        pytest.fail("canary disclosure", pytrace=False)


def test_registry_versions_and_conflicts_fail_closed(tmp_path: Path) -> None:
    config = implementation()
    path = config_file(tmp_path)
    original = registry()
    for changed, expected in (
        (
            dataclasses.replace(original.descriptors[0], deprecated_version="1.0.0"),
            "deprecated_setting",
        ),
        (
            dataclasses.replace(original.descriptors[0], first_version="2.0.0"),
            "unsupported_configuration_version",
        ),
        (
            dataclasses.replace(original.descriptors[0], secret_class="development"),
            "invalid_configuration_registry",
        ),
    ):
        altered = dataclasses.replace(original, descriptors=(changed,))
        with pytest.raises(config.BootstrapConfigurationError) as caught:
            config.load_bootstrap_configuration(
                path, {}, config.BootstrapCliOptionsV1(registry=altered)
            )
        assert caught.value.code == expected
    with pytest.raises(config.BootstrapConfigurationError) as caught:
        config.load_bootstrap_configuration(
            path,
            {},
            config.BootstrapCliOptionsV1(
                registry=original, values=((COUNT, "1"), (COUNT, "2"))
            ),
        )
    assert caught.value.code == "conflicting_setting"


def test_real_process_ignores_global_environment_and_fails_safely(
    tmp_path: Path,
) -> None:
    implementation()
    path = config_file(tmp_path)
    script = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from agentmonitor.contracts.configuration_v1 import ConfigurationRegistryV1
from agentmonitor.foundation.configuration import (
    BootstrapCliOptionsV1, BootstrapConfigurationError, load_bootstrap_configuration,
)
try:
    result = load_bootstrap_configuration(
        Path(sys.argv[2]), {}, BootstrapCliOptionsV1(
            registry=ConfigurationRegistryV1(descriptors=())
        )
    )
except BootstrapConfigurationError as error:
    print(error.code)
    raise SystemExit(2) from None
print(result.configuration_version)
"""
    canary = secrets.token_urlsafe(32)
    for selected, status, output in (
        (path, 0, "1.0.0\n"),
        (tmp_path / "missing.env", 2, "configuration_unavailable\n"),
    ):
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                script,
                str(ROOT / "backend/src"),
                str(selected),
            ],
            cwd=tmp_path,
            env={COUNT: canary, "AGENTMONITOR_UNREGISTERED": canary},
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if canary in result.stdout + result.stderr:
            pytest.fail("canary disclosure", pytrace=False)
        assert result.returncode == status
        assert result.stdout == output
        assert result.stderr == ""


@pytest.mark.parametrize("values", [[(COUNT, "2")], ((COUNT, "2", "3"),), ("wrong",)])
def test_cli_shape_is_immutable_and_errors_are_safe(values: object) -> None:
    config = implementation()
    with pytest.raises(config.BootstrapConfigurationError) as caught:
        config.BootstrapCliOptionsV1(registry=registry(), values=values)
    assert caught.value.code == "malformed_configuration"


def test_unregistered_name_never_enters_error(tmp_path: Path) -> None:
    config = implementation()
    canary = secrets.token_urlsafe(32)
    path = config_file(tmp_path)
    with pytest.raises(config.BootstrapConfigurationError) as caught:
        config.load_bootstrap_configuration(
            path, {canary: "ignored"}, config.BootstrapCliOptionsV1(registry=registry())
        )
    if canary in str(caught.value) + repr(caught.value):
        pytest.fail("canary disclosure", pytrace=False)
    assert caught.value.code == "unknown_environment_name"


def test_boolean_and_invalid_shadowed_values(tmp_path: Path) -> None:
    config = implementation()
    original = registry()
    boolean = dataclasses.replace(
        original.descriptors[0],
        value_type="boolean",
        validation_rule="boolean",
        safe_default="false",
    )
    cli = config.BootstrapCliOptionsV1(
        registry=dataclasses.replace(original, descriptors=(boolean,))
    )
    path = config_file(tmp_path, f"{COUNT}=true\n")
    assert config.load_bootstrap_configuration(path, {}, cli).non_secret_sources == (
        (COUNT, "config_file"),
    )
    path.write_text(f"{COUNT}=True\n")
    with pytest.raises(config.BootstrapConfigurationError) as caught:
        config.load_bootstrap_configuration(path, {COUNT: "false"}, cli)
    assert caught.value.code == "malformed_setting"


def test_secret_wrapper_and_cli_repr_are_nonrevealing() -> None:
    config = implementation()
    canary = secrets.token_urlsafe(32)
    secret = config.SecretValueV1(canary)
    with pytest.raises(TypeError):
        secret.extra = canary
    cli = config.BootstrapCliOptionsV1(registry=registry(), values=((COUNT, canary),))
    if canary in repr(cli):
        pytest.fail("canary disclosure", pytrace=False)


def test_configuration_error_traceback_does_not_chain_raw_caller_exception(
    tmp_path: Path,
) -> None:
    config = implementation()
    canary = secrets.token_urlsafe(32)
    path = config_file(tmp_path)
    try:
        raise RuntimeError(canary)
    except RuntimeError:
        with pytest.raises(config.BootstrapConfigurationError) as caught:
            config.load_bootstrap_configuration(
                path,
                {"UNKNOWN": canary},
                config.BootstrapCliOptionsV1(registry=registry()),
            )
        output = "".join(traceback.format_exception(caught.value))
    if canary in output:
        pytest.fail(
            "unsafe caller exception appeared in safe-error traceback", pytrace=False
        )
