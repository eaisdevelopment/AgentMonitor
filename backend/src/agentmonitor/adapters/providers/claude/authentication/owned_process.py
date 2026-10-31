"""Linux owned-child guard; service death ends its native authentication child."""

import ctypes
import os
import signal
import sys


def main() -> int:
    if sys.platform != "linux" or len(sys.argv) < 2:
        return 1
    parent = os.getppid()
    libc = ctypes.CDLL(None, use_errno=True)
    if parent == 1 or libc.prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
        return 1
    if os.getppid() != parent:
        return 1
    os.execv(sys.argv[1], sys.argv[1:])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
