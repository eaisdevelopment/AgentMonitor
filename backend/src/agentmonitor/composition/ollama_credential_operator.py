"""Local terminal entry point for owner-managed Ollama credentials."""

import argparse
import os
import sys
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.ollama_credential_enrollment import (
    disconnect_ollama_credential,
    enroll_ollama_credential,
)
from agentmonitor.contracts.registry_v1 import AccountViewV1, OrganizationViewV1


def safe_label(value: str) -> str:
    """Avoid terminal escape sequences in owner-entered names."""
    result = "".join(
        character if character.isprintable() else "?" for character in value
    )
    return result[:160] or "Unnamed"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Connect an Ollama account locally")
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--env-file", required=True, type=Path)
    args = parser.parse_args(argv)
    if not all(os.isatty(fd) for fd in (0, 1, 2)):
        print("Open this command in a local terminal.")
        return 2
    if not args.data_root.is_absolute() or not args.env_file.is_absolute():
        print("The data directory and configured .env must use absolute paths.")
        return 2
    try:
        reference = DatabaseRefV1(args.data_root / "agentmonitor.db", args.data_root)
        registry = SqliteRegistryRepositoryV1(reference)
        organizations: list[OrganizationViewV1] = []
        cursor = None
        while True:
            page = registry.list_organizations(page_size=100, after_key=cursor)
            organizations.extend(page)
            if len(page) < 100:
                break
            if len(organizations) >= 1000:
                print("Too many organizations to display safely.")
                return 2
            cursor = page[-1].organization_id.value
        names = {item.organization_id: item.name for item in organizations}
        accounts: list[AccountViewV1] = []
        cursor = None
        scanned = 0
        while True:
            account_page = registry.list_accounts(
                provider_key="ollama", page_size=100, after_key=cursor
            )
            scanned += len(account_page)
            accounts.extend(
                item for item in account_page if item.lifecycle != "archived"
            )
            if len(account_page) < 100:
                break
            if scanned >= 1000:
                print("Too many accounts to display safely.")
                return 2
            cursor = account_page[-1].account_id.value
        if not accounts:
            print("No Ollama accounts found. Add an account in the dashboard first.")
            return 1
        print("Choose an Ollama account to connect or rotate:")
        for index, account in enumerate(accounts, 1):
            organization = (
                names.get(account.organization_id, "No organization")
                if account.organization_id is not None
                else "No organization"
            )
            label = safe_label(account.friendly_name)
            print(f"{index}. {safe_label(organization)} / {label}")
        choice = input("Account number (or Enter to cancel): ").strip()
        if not choice:
            return 0
        if (
            not choice.isascii()
            or not choice.isdecimal()
            or not 1 <= int(choice) <= len(accounts)
        ):
            print("Invalid account number.")
            return 2
        account = accounts[int(choice) - 1]
        state = SqliteCredentialBindingsV1(reference).read(account.account_id)
        if any(item.lifecycle == "cleanup_pending" for item in state.bindings):
            print(
                "Earlier credential cleanup is pending; the old item may still exist."
            )
        if any(item.lifecycle == "pending" for item in state.bindings):
            print("An earlier setup was interrupted. This will retry that same item.")
        if any(item.lifecycle == "active" for item in state.bindings):
            print(
                "A credential is connected. Continuing will replace it "
                "after the new item is stored."
            )
        action = input(
            "Choose connect/rotate (1), disconnect (2), or Enter to cancel: "
        ).strip()
        if not action:
            return 0
        if action == "1":
            print("Enter the Ollama API key at the hidden prompt.")
            enroll_ollama_credential(reference, account.account_id, args.env_file)
            print("Credential stored. The account association remains owner-asserted.")
        elif action == "2":
            disconnect_ollama_credential(reference, account.account_id, args.env_file)
            print("Account disconnected and its managed credential removed.")
        else:
            print("Invalid selection.")
            return 2
        return 0
    except (OSError, ValueError, EOFError, KeyboardInterrupt):
        print(
            "The operation could not finish. Check the account status and retry; "
            "pending cleanup remains recorded."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
