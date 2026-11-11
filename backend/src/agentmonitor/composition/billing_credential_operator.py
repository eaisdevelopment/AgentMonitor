"""Owner-local hidden-terminal credential entry for one selected billing resource."""

import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.ollama_credential_enrollment import (
    EnrollmentError,
    enroll_billing_credential,
    require_billing_credential_target,
)
from agentmonitor.composition.ollama_credential_operator import (
    safe_label,
    selected_env_from_service,
)
from agentmonitor.composition.ollama_env_store import read_env_location
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def enroll_selected_billing_credential(
    reference: DatabaseRefV1,
    account_id: OpaqueIdV1,
    resource_id: OpaqueIdV1,
    env_path: Path,
    *,
    selection_current: Callable[[], bool],
) -> None:
    """Show selected owner metadata before invoking the protected entry flow."""
    captured = require_billing_credential_target(reference, account_id, resource_id)
    registry = SqliteRegistryRepositoryV1(reference)
    account = registry.get_account(account_id)
    if account is None or account.record_version != captured.account_record_version:
        raise EnrollmentError("billing_credential_target_changed")
    if account.organization_id is None:
        organization_label = "Ungrouped"
    else:
        try:
            organization = registry.get_organization(account.organization_id)
        except ValueError:
            organization = None
        organization_label = (
            safe_label(organization.name)
            if organization is not None
            else "Organization unavailable"
        )
    provider = (
        "Anthropic (Claude)" if captured.provider_key == "claude" else "OpenAI (Codex)"
    )
    print(
        f"{provider}: {organization_label} / {safe_label(account.friendly_name)}",
        flush=True,
    )

    def target_and_selection_current() -> bool:
        require_billing_credential_target(
            reference, account_id, resource_id, expected=captured
        )
        return selection_current()

    enroll_billing_credential(
        reference,
        account_id,
        resource_id,
        env_path,
        selection_current=target_and_selection_current,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Store a billing credential locally")
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--account-id", required=True, metavar="ID")
    parser.add_argument("--resource-id", required=True, metavar="ID")
    args = parser.parse_args(argv)
    if not all(os.isatty(fd) for fd in (0, 1, 2)):
        print("Open this command in a local terminal.")
        return 2
    if len({os.ttyname(fd) for fd in (0, 1, 2)}) != 1:
        print("Open this command in a local terminal.")
        return 2
    if not args.data_root.is_absolute():
        print("The data directory must use an absolute path.")
        return 2
    try:
        reference = DatabaseRefV1(args.data_root / "agentmonitor.db", args.data_root)
        account_id = OpaqueIdV1(args.account_id)
        resource_id = OpaqueIdV1(args.resource_id)
        # Reject wrong account/resource/provider before looking up service state.
        require_billing_credential_target(reference, account_id, resource_id)
        selected = selected_env_from_service(args.data_root)

        def selection_current() -> bool:
            if selected_env_from_service(args.data_root) != selected:
                return False
            try:
                retained = read_env_location(args.data_root)
            except FileNotFoundError:
                return True
            return retained == selected

        if not selection_current():
            print(
                "Credential file selection changed. Check the dashboard configuration."
            )
            return 1
        enroll_selected_billing_credential(
            reference,
            account_id,
            resource_id,
            selected,
            selection_current=selection_current,
        )
        print("Credential stored locally. Billing access has not been verified.")
        return 0
    except (OSError, ValueError, EOFError, KeyboardInterrupt):
        print(
            "The billing credential operation could not finish. "
            "Check the selected account and connection, then retry; "
            "pending setup or cleanup remains recorded."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
