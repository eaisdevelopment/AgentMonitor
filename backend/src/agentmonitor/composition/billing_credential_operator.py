"""Owner-local hidden-terminal credential entry for one selected billing resource."""

import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.ollama_credential_enrollment import (
    EnrollmentError,
    enroll_billing_credential,
    maintain_billing_credential,
    require_billing_credential_target,
    require_billing_maintenance_target,
)
from agentmonitor.composition.ollama_credential_operator import (
    safe_label,
    selected_env_from_service,
)
from agentmonitor.composition.ollama_env_store import read_env_location
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import AccountBillingConnectionsV1


def _pin_billing_database(
    reference: DatabaseRefV1, selection_current: Callable[[], bool]
) -> Callable[[], bool]:
    identity = reference.validate()

    def current() -> bool:
        if reference.validate() != identity:
            raise EnrollmentError("billing_credential_database_changed")
        return selection_current()

    return current


def _show_selected_account(
    reference: DatabaseRefV1, captured: AccountBillingConnectionsV1
) -> None:
    """Display only owner labels; this is not provider identity verification."""
    registry = SqliteRegistryRepositoryV1(reference)
    account = registry.get_account(captured.account_id)
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
    _show_selected_account(reference, captured)

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


def maintain_selected_billing_credential(
    reference: DatabaseRefV1,
    account_id: OpaqueIdV1,
    resource_id: OpaqueIdV1,
    env_path: Path,
    *,
    action: Literal["disconnect", "cleanup"],
    selection_current: Callable[[], bool],
) -> None:
    """Use the explicit local action without asking for a replacement key."""
    selected = _pin_billing_database(reference, selection_current)
    captured = require_billing_maintenance_target(reference, account_id, resource_id)
    _show_selected_account(reference, captured)
    maintain_billing_credential(
        reference,
        account_id,
        resource_id,
        env_path,
        action=action,
        selection_current=selected,
        expected=captured,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage a billing credential locally")
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--account-id", required=True, metavar="ID")
    parser.add_argument("--resource-id", required=True, metavar="ID")
    parser.add_argument(
        "--action", choices=("store", "disconnect", "cleanup"), default="store"
    )
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
        if args.action == "store":
            require_billing_credential_target(reference, account_id, resource_id)
        else:
            require_billing_maintenance_target(reference, account_id, resource_id)
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
        if args.action == "store":
            enroll_selected_billing_credential(
                reference,
                account_id,
                resource_id,
                selected,
                selection_current=selection_current,
            )
            print("Credential stored locally. Billing access has not been verified.")
        else:
            maintain_selected_billing_credential(
                reference,
                account_id,
                resource_id,
                selected,
                action=args.action,
                selection_current=selection_current,
            )
            print(
                "AgentMonitor billing disconnected; local cleanup completed. "
                "History retained."
                if args.action == "disconnect"
                else "Local credential cleanup completed. Refresh billing status."
            )
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
