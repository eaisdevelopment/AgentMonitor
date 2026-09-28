"""Ordinary owner browser for official sign-in; no URL or cookie is inspected."""

import os
from pathlib import Path

from agentmonitor.adapters.providers.claude.authentication.identity import (
    claude_identity_environment_v1,
)


def create_managed_browser_opener_v1(directory: Path) -> Path:
    """Provider-owned browser state stays private; never automate Claude's page."""
    directory.mkdir(mode=0o700, exist_ok=True)
    claude_identity_environment_v1(directory)
    profile = directory / "chrome-profile"
    profile.mkdir(mode=0o700, exist_ok=True)
    claude_identity_environment_v1(profile)
    if not Path("/usr/bin/google-chrome").is_file():
        raise ValueError("claude_signin_browser_unavailable")
    opener = directory / "open-sign-in"
    # The helper receives the provider URL directly from the native CLI. No
    # argument, output, cookie, DOM, URL, or secret is read by AgentMonitor.
    script = (
        "#!/usr/bin/python3\nimport os,sys\n"
        'os.execv("/usr/bin/google-chrome", ["/usr/bin/google-chrome", '
        '"--user-data-dir="+'
        + repr(str(profile))
        + ', "--new-window", "--no-first-run", *sys.argv[1:]])\n'
    )
    descriptor = os.open(
        opener, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o700
    )
    with os.fdopen(descriptor, "w") as stream:
        stream.write(script)
    return opener
