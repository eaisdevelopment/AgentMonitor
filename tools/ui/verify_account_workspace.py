"""Verify the account workspace in the real running owner dashboard."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend/src"))

from tools.automation.implementations.auto_m3_live import (  # noqa: E402
    _owner_env_value,
    _owner_target,
)
from agentmonitor.adapters.providers.claude.authentication.identity import (  # noqa: E402
    read_default_profile_identity_v1,
)
from agentmonitor.adapters.providers.claude.installation import (  # noqa: E402
    discover_default_installation,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--screenshots", type=Path, required=True)
    options = parser.parse_args()
    origin = urlsplit(options.origin)
    if (
        origin.scheme != "http"
        or origin.hostname != "127.0.0.1"
        or origin.port is None
        or origin.path
        or origin.query
        or origin.fragment
        or origin.username is not None
    ):
        print("ACCOUNT WORKSPACE: FAILED — invalid_loopback_origin")
        return 1
    target = _owner_target()
    credential = _owner_env_value("AGENTMONITOR_DASHBOARD_PASSWORD")
    if target is None or not credential:
        print("ACCOUNT WORKSPACE: BLOCKED — real owner account and local credential required")
        return 3
    identity = read_default_profile_identity_v1(discover_default_installation())
    if identity is None:
        print("ACCOUNT WORKSPACE: BLOCKED — real Claude account identity unavailable")
        return 3
    options.screenshots.mkdir(parents=True, exist_ok=True, mode=0o700)
    options.screenshots.chmod(0o700)
    result = subprocess.run(
        [
            "node",
            str(ROOT / "frontend/tests/browser/p02/account_workspace.mjs"),
            options.origin,
            target[2].value,
            str(options.screenshots.resolve()),
        ],
        cwd=ROOT,
        input=json.dumps({"credential": credential, "expectedEmail": identity.email}),
        text=True,
        capture_output=True,
        timeout=390,
        check=False,
    )
    print(result.stdout.replace(credential, "[redacted]").strip())
    if result.stderr:
        print(result.stderr.replace(credential, "[redacted]").strip(), file=sys.stderr)
    credential = ""
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
