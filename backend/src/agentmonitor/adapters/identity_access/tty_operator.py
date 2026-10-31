"""M01 local operator input adapter: controlling TTY, no echo, no fallback."""

import hmac
import os
import termios

from agentmonitor.contracts.identity_access_v1 import SecretInputV1


def _read_line_without_echo(fd: int, prompt: bytes) -> bytes | None:
    os.write(fd, prompt)
    collected = bytearray()
    over_limit = False
    while True:
        byte = os.read(fd, 1)
        if not byte:
            return None
        if byte in (b"\n", b"\r"):
            os.write(fd, b"\n")
            return None if over_limit else bytes(collected)
        if len(collected) < 1024:
            collected.extend(byte)
        else:
            over_limit = True


def read_confirmed_password() -> SecretInputV1 | None:
    """Read exactly two bounded lines while terminal echo is disabled."""
    fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
    try:
        if not os.isatty(fd):
            return None
        previous = termios.tcgetattr(fd)
        hidden = previous[:]
        hidden[3] &= ~(termios.ECHO | termios.ECHONL)
        termios.tcsetattr(fd, termios.TCSAFLUSH, hidden)
        try:
            first = _read_line_without_echo(fd, b"Enter dashboard password: ")
            second = _read_line_without_echo(fd, b"Confirm dashboard password: ")
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, previous)
    finally:
        os.close(fd)
    if first is None or second is None or not hmac.compare_digest(first, second):
        return None
    try:
        return SecretInputV1(first.decode("utf-8"))
    except UnicodeError:
        return None
