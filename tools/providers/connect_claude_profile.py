"""Owner-operated official Claude sign-in for one registered managed account.

This command authenticates only. Pending registry enrollment and quota polling
remain explicit next stages; no credentials or provider output are inspected.
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (  # noqa: E402
    DatabaseRefV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (  # noqa: E402
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.claude.authentication.identity import (  # noqa: E402
    claude_identity_environment_v1,
    read_default_profile_identity_v1,
)
from agentmonitor.adapters.providers.claude.authentication.reauthentication import (  # noqa: E402
    ClaudeManagedLoginAttemptV1,
    ClaudeReauthenticationTargetV1,
    begin_managed_profile_authentication_v1,
)
from agentmonitor.adapters.providers.claude.installation import (  # noqa: E402
    discover_default_installation,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1  # noqa: E402
from agentmonitor.modules.registry.application.accounts import (  # noqa: E402
    GetAccountV1,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--expected-email")
    parser.add_argument("--browser-opener", type=Path)
    options = parser.parse_args()
    attempt: ClaudeManagedLoginAttemptV1 | None = None
    try:
        data_root = options.data_root.absolute()
        reference = DatabaseRefV1(data_root / "agentmonitor.db", data_root)
        reference.validate()
        account_id = OpaqueIdV1(options.account_id)
        account = GetAccountV1(SqliteRegistryRepositoryV1(reference))(account_id)
        if (
            account is None
            or account.provider_key != "claude"
            or account.lifecycle != "pending"
        ):
            print(
                "CLAUDE CONNECTION: BLOCKED — "
                "registered pending Claude account required"
            )
            return 3
        expected_email = options.expected_email or account.friendly_name
        if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", expected_email) is None:
            print("CLAUDE CONNECTION: BLOCKED — explicit expected email required")
            return 3
        key = hashlib.sha256(account_id.value.encode()).hexdigest()
        profiles = data_root / "profiles"
        claude_profiles = profiles / "claude"
        managed_root = claude_profiles / key
        for directory in (profiles, claude_profiles, managed_root):
            directory.mkdir(mode=0o700, exist_ok=True)
            claude_identity_environment_v1(directory)
        installation = discover_default_installation()
        protected_before = read_default_profile_identity_v1(installation)
        if protected_before is None:
            print("CLAUDE CONNECTION: BLOCKED — protected default identity unavailable")
            return 3
        existing = read_default_profile_identity_v1(
            installation, managed_profile_root=managed_root
        )
        if existing is None:
            attempt = begin_managed_profile_authentication_v1(
                installation,
                ClaudeReauthenticationTargetV1(
                    profile_ref=OpaqueIdV1("claude-managed-" + key),
                    profile_protection="managed",
                    expected_identity_available=True,
                    owner_interaction_granted=True,
                ),
                managed_profile_root=managed_root,
                expected_email=expected_email,
                browser_opener=options.browser_opener,
            )
            print(
                "CLAUDE CONNECTION: AWAITING OWNER SIGN-IN — "
                "complete the official browser flow",
                flush=True,
            )
            existing = attempt.wait_for_identity()
        protected_after = read_default_profile_identity_v1(installation)
        if (
            protected_after is None
            or protected_before.fingerprint != protected_after.fingerprint
        ):
            print(
                "CLAUDE CONNECTION: FAILED — "
                "protected default identity changed or unavailable"
            )
            return 1
        if existing is None or existing.email.casefold() != expected_email.casefold():
            print("CLAUDE CONNECTION: BLOCKED — expected managed identity not verified")
            return 3
        print(
            "CLAUDE CONNECTION: AUTHENTICATION VERIFIED — "
            "registry binding and collection still required"
        )
        return 0
    except KeyboardInterrupt:
        print("CLAUDE CONNECTION: BLOCKED — owner interaction cancelled")
        return 3
    except (OSError, ValueError, RuntimeError):
        print("CLAUDE CONNECTION: FAILED — account or profile operation unavailable")
        return 1
    finally:
        if attempt is not None:
            attempt.cancel()


if __name__ == "__main__":
    raise SystemExit(main())
