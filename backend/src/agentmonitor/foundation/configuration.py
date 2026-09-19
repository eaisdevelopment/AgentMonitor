"""Explicit bootstrap validation (CTR-CONFIG-001 / CTR-FND-003 V1).

No product keys are registered here. Composition supplies approved descriptors.
The public result is the existing metadata receipt; owner-specific runtime values
are deliberately not exported through it. The small file grammar is UTF-8
NAME=VALUE, blank lines and full-line # comments, without quoting, interpolation,
shell export, escapes, or implicit discovery. Precedence is default < file <
supplied environment < non-secret CLI; every supplied value is validated.
Supported technical rules are boolean (true/false), positive_integer
(1..999999999), and nonempty AgentMonitor secrets (at most 4096 characters,
without control characters). Files are limited to 65536 bytes. Unknown and
deprecated keys and unsupported descriptor versions are rejected, never guessed.
"""

import os
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, NoReturn, SupportsIndex

from agentmonitor.contracts.configuration_v1 import (
    BootstrapConfigurationV1,
    ConfigurationDescriptorV1,
    ConfigurationRegistryV1,
)

_MAX_FILE_BYTES = 65536
_SOURCES = ("default", "config_file", "environment", "cli")
_NAME = re.compile(r"AGENTMONITOR_[A-Z][A-Z0-9_]{0,95}")
_INTERNAL = re.compile(r"[a-z][a-z0-9_]{0,95}")

ConfigurationErrorCodeV1 = Literal[
    "unknown_environment_name",
    "unknown_file_name",
    "unknown_cli_name",
    "malformed_setting",
    "malformed_configuration",
    "conflicting_setting",
    "missing_required_setting",
    "unsafe_configuration_permissions",
    "configuration_unavailable",
    "configuration_too_large",
    "invalid_configuration_path",
    "invalid_configuration_registry",
    "unsupported_configuration_version",
    "deprecated_setting",
    "forbidden_configuration_source",
]


class BootstrapConfigurationError(ValueError):
    """Stable codes; setting names are emitted only after registry validation."""

    def __init__(
        self, code: ConfigurationErrorCodeV1, setting_name: str | None = None
    ) -> None:
        self.code = code
        self.setting_name = setting_name
        super().__init__(code if setting_name is None else f"{code}:{setting_name}")
        # A safe rejection can occur inside a handler for an unsafe raw error.
        self.__suppress_context__ = True


class SecretValueV1:
    """Opaque, immutable, non-serializable AgentMonitor-only bootstrap value.

    The only public information is configured/missing. There is intentionally no
    reveal method; a future secret consumer needs its own approved owner port.
    """

    __slots__ = ("__value",)
    __value: str | None

    def __init__(self, value: str | None) -> None:
        if value is not None and type(value) is not str:
            raise TypeError("invalid_secret_value") from None
        object.__setattr__(self, "_SecretValueV1__value", value)

    @property
    def presence(self) -> Literal["configured", "missing"]:
        return "configured" if self.__value else "missing"

    def __repr__(self) -> str:
        return f"SecretValueV1({self.presence})"

    def __str__(self) -> str:
        return self.presence

    def __setattr__(self, name: str, value: object) -> NoReturn:
        raise TypeError("immutable_secret_value") from None

    def __delattr__(self, name: str) -> NoReturn:
        raise TypeError("immutable_secret_value") from None

    def __reduce_ex__(self, protocol: SupportsIndex) -> NoReturn:
        raise TypeError("secret_serialization_forbidden") from None

    def __getstate__(self) -> NoReturn:
        raise TypeError("secret_serialization_forbidden") from None


@dataclass(frozen=True, slots=True)
class BootstrapCliOptionsV1:
    """Foundation-local input; no final product key or secret CLI allocation."""

    registry: ConfigurationRegistryV1 = field(repr=False)
    values: tuple[tuple[str, str], ...] = field(default=(), repr=False)
    configuration_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if type(self.values) is not tuple:
            raise BootstrapConfigurationError("malformed_configuration")
        for pair in self.values:
            if (
                type(pair) is not tuple
                or len(pair) != 2
                or any(type(value) is not str for value in pair)
            ):
                raise BootstrapConfigurationError("malformed_configuration")


def _descriptors(cli: BootstrapCliOptionsV1) -> tuple[ConfigurationDescriptorV1, ...]:
    if type(cli) is not BootstrapCliOptionsV1:
        raise BootstrapConfigurationError("invalid_configuration_registry")
    if cli.configuration_version != "1.0.0":
        raise BootstrapConfigurationError("unsupported_configuration_version")
    if type(cli.registry) is not ConfigurationRegistryV1:
        raise BootstrapConfigurationError("invalid_configuration_registry")
    descriptors = cli.registry.descriptors
    names: set[str] = set()
    internal_names: set[tuple[str, str]] = set()
    for descriptor in descriptors:
        if type(descriptor) is not ConfigurationDescriptorV1:
            raise BootstrapConfigurationError("invalid_configuration_registry")
        if (
            type(descriptor.external_name) is not str
            or not _NAME.fullmatch(descriptor.external_name)
            or type(descriptor.internal_name) is not str
            or not _INTERNAL.fullmatch(descriptor.internal_name)
            or type(descriptor.owner) is not str
            or not re.fullmatch(r"[A-Z][A-Z0-9-]{0,47}", descriptor.owner)
            or descriptor.external_name in names
            or (descriptor.owner, descriptor.internal_name) in internal_names
            or descriptor.secret_class not in ("non_secret", "agentmonitor")
            or type(descriptor.required) is not bool
        ):
            raise BootstrapConfigurationError("invalid_configuration_registry")
        name = descriptor.external_name
        names.add(name)
        internal_names.add((descriptor.owner, descriptor.internal_name))
        if (
            descriptor.first_version != "1.0.0"
            or descriptor.removed_version is not None
        ):
            raise BootstrapConfigurationError("unsupported_configuration_version", name)
        if descriptor.deprecated_version is not None:
            raise BootstrapConfigurationError("deprecated_setting", name)
        sources = descriptor.sources_low_to_high
        if not sources or sources != tuple(
            item for item in _SOURCES if item in sources
        ):
            raise BootstrapConfigurationError("invalid_configuration_registry", name)
        supported_rule = (
            (
                descriptor.value_type == "integer"
                and descriptor.validation_rule == "positive_integer"
            )
            or (
                descriptor.value_type == "boolean"
                and descriptor.validation_rule == "boolean"
            )
            or (
                descriptor.value_type == "secret"
                and descriptor.validation_rule == "nonempty"
            )
        )
        if not supported_rule or (
            (descriptor.value_type == "secret")
            != (descriptor.secret_class == "agentmonitor")
        ):
            raise BootstrapConfigurationError("invalid_configuration_registry", name)
        if descriptor.secret_class == "agentmonitor" and (
            descriptor.safe_default is not None
            or "cli" in sources
            or "default" in sources
        ):
            raise BootstrapConfigurationError("invalid_configuration_registry", name)
    return descriptors


def _read_explicit(config_path: Path) -> str:
    """Read a bounded owner-only regular file; no symlink component is followed.

    Descriptor-relative opening checks the file actually read and closes every
    descriptor. Unsupported platforms fail closed; Linux is the verified target.
    Raw OS/decoder exceptions are discarded before raising a public safe error.
    """
    if (
        not isinstance(config_path, Path)
        or not config_path.is_absolute()
        or ".." in config_path.parts
    ):
        raise BootstrapConfigurationError("invalid_configuration_path")
    if os.name != "posix":
        raise BootstrapConfigurationError("configuration_unavailable")
    error: ConfigurationErrorCodeV1 | None = None
    content = ""
    directory: int | None = None
    descriptor: int | None = None
    try:
        directory = os.open(config_path.anchor, os.O_RDONLY | os.O_DIRECTORY)
        for part in config_path.parts[1:-1]:
            child = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
            )
            os.close(directory)
            directory = child
        descriptor = os.open(
            config_path.name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=directory,
        )
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            error = "invalid_configuration_path"
        elif metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) not in (
            0o400,
            0o600,
        ):
            error = "unsafe_configuration_permissions"
        elif metadata.st_size > _MAX_FILE_BYTES:
            error = "configuration_too_large"
        else:
            with os.fdopen(descriptor, "rb") as stream:
                descriptor = None
                data = stream.read(_MAX_FILE_BYTES + 1)
            if len(data) > _MAX_FILE_BYTES:
                error = "configuration_too_large"
            else:
                content = data.decode("utf-8")
    except PermissionError:
        error = "unsafe_configuration_permissions"
    except OSError:
        error = "configuration_unavailable"
    except UnicodeError:
        error = "malformed_configuration"
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory is not None:
            os.close(directory)
    if error is not None:
        raise BootstrapConfigurationError(error)
    return content


def _file_values(content: str) -> tuple[tuple[str, str], ...]:
    values: list[tuple[str, str]] = []
    for line in content.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if not separator:
            raise BootstrapConfigurationError("malformed_configuration")
        values.append((name, value))
    return tuple(values)


def _parse(
    descriptor: ConfigurationDescriptorV1, value: str
) -> int | bool | SecretValueV1:
    if (
        type(value) is not str
        or not value
        or len(value) > 4096
        or any(ord(char) < 32 for char in value)
    ):
        raise BootstrapConfigurationError("malformed_setting", descriptor.external_name)
    if descriptor.value_type == "secret":
        return SecretValueV1(value)
    if descriptor.value_type == "boolean" and value in ("true", "false"):
        return value == "true"
    if descriptor.value_type == "integer" and re.fullmatch(r"[1-9][0-9]{0,8}", value):
        return int(value)
    raise BootstrapConfigurationError("malformed_setting", descriptor.external_name)


def load_bootstrap_configuration(
    config_path: Path, environment: Mapping[str, str], cli: BootstrapCliOptionsV1
) -> BootstrapConfigurationV1:
    """Validate only the explicit path and supplied names; return safe metadata.

    Raises BootstrapConfigurationError with a stable code and, for registered
    fields only, a safe name. No configuration values enter exception arguments,
    public records, or logs. Does not consult or mutate the global environment.
    """
    descriptors = _descriptors(cli)
    registered = {item.external_name: item for item in descriptors}
    selected: dict[str, tuple[int | bool | SecretValueV1, str]] = {}
    sources = (
        (
            "default",
            tuple(
                (item.external_name, item.safe_default)
                for item in descriptors
                if item.safe_default is not None
            ),
        ),
        ("config_file", _file_values(_read_explicit(config_path))),
        ("environment", tuple(environment.items())),
        ("cli", cli.values),
    )
    for source, pairs in sources:
        seen: set[str] = set()
        for name, value in pairs:
            if name not in registered:
                unknown_codes: dict[str, ConfigurationErrorCodeV1] = {
                    "environment": "unknown_environment_name",
                    "config_file": "unknown_file_name",
                    "cli": "unknown_cli_name",
                    "default": "invalid_configuration_registry",
                }
                raise BootstrapConfigurationError(unknown_codes[source])
            descriptor = registered[name]
            if name in seen:
                raise BootstrapConfigurationError("conflicting_setting", name)
            seen.add(name)
            if source not in descriptor.sources_low_to_high:
                raise BootstrapConfigurationError(
                    "forbidden_configuration_source", name
                )
            selected[name] = (_parse(descriptor, value), source)
    non_secret_sources: list[tuple[str, str]] = []
    presence: list[tuple[str, bool]] = []
    for descriptor in descriptors:
        name = descriptor.external_name
        if name not in selected and descriptor.required:
            raise BootstrapConfigurationError("missing_required_setting", name)
        if descriptor.secret_class == "agentmonitor":
            presence.append((name, name in selected))
        elif name in selected:
            non_secret_sources.append((name, selected[name][1]))
    return BootstrapConfigurationV1(
        configuration_version="1.0.0",
        owners=tuple(sorted({item.owner for item in descriptors})),
        non_secret_sources=tuple(non_secret_sources),
        secret_presence=tuple(presence),
    )
