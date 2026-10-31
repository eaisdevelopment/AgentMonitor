"""Explicit owner command for Claude OTLP account binding evidence."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from agentmonitor.composition.claude_otel_runtime import launch_owner_terminal
from agentmonitor.contracts.common_v1 import OpaqueIdV1

_CONFIRMATION = b"CONFIRM"
_PROMPT = b"Type CONFIRM to bind the next authenticated Claude identity: "


def _read_owner_confirmation() -> bool:
    """Read one bounded, non-secret confirmation from the controlling terminal."""
    descriptor = os.open(
        "/dev/tty", os.O_RDWR | os.O_NOCTTY | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        if not os.isatty(descriptor):
            return False
        os.write(descriptor, _PROMPT)
        value = bytearray()
        over_limit = False
        while True:
            character = os.read(descriptor, 1)
            if not character:
                return False
            if character in {b"\n", b"\r"}:
                return not over_limit and bytes(value) == _CONFIRMATION
            if len(value) < len(_CONFIRMATION):
                value.extend(character)
            else:
                over_limit = True
    finally:
        os.close(descriptor)


def main(argv: list[str] | None = None) -> int:
    """Authorize one exact next-launch bind or evidence refresh."""
    arguments = sys.argv[1:] if argv is None else argv
    if (
        len(arguments) != 6
        or arguments[0] != "--data-root"
        or arguments[2] != "--account-id"
        or arguments[4] != "--account-version"
    ):
        print("invalid_operator_arguments")
        return 2
    try:
        data_root = Path(arguments[1])
        OpaqueIdV1(arguments[3])
        expected_account_version = int(arguments[5])
    except (TypeError, ValueError):
        print("invalid_operator_arguments")
        return 2
    if expected_account_version < 1 or str(expected_account_version) != arguments[5]:
        print("invalid_operator_arguments")
        return 2
    if not data_root.is_absolute() or data_root in {Path("/"), Path.home()}:
        print("claude_otel_runtime_data_root_invalid")
        return 2
    if not (sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty()):
        print("controlling_tty_required")
        return 2
    try:
        confirmed = _read_owner_confirmation()
    except OSError:
        confirmed = False
    if not confirmed:
        print("owner_confirmation_required")
        return 2
    return launch_owner_terminal(
        arguments[:4],
        allow_initial_owner_binding=True,
        expected_selected_account_record_version=expected_account_version,
    )


if __name__ == "__main__":
    raise SystemExit(main())
