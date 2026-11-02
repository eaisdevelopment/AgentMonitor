"""Local terminal entry point for owner-managed Ollama credentials."""

import argparse
import os
import select
import shlex
import subprocess
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
    cleanup_ollama_credential,
    cleanup_untracked_ollama_credentials,
    disconnect_ollama_credential,
    enroll_ollama_credential,
)
from agentmonitor.composition.ollama_env_store import (
    env_location_matches,
    read_env_location,
)
from agentmonitor.contracts.registry_v1 import AccountViewV1, OrganizationViewV1


def safe_label(value: str) -> str:
    """Avoid terminal escape sequences in owner-entered names."""
    result = "".join(
        character if character.isprintable() else "?" for character in value
    )
    return result[:160] or "Unnamed"


def selected_env_from_argv(argv: tuple[str, ...]) -> Path:
    """Extract one explicit credential-file setting from the deployed service."""
    positions = [i for i, item in enumerate(argv) if item == "--credential-env-file"]
    if len(positions) != 1 or positions[0] + 1 >= len(argv):
        raise ValueError("ollama_env_selection_unavailable")
    path = Path(argv[positions[0] + 1])
    if not path.is_absolute() or path.name != ".env" or ".." in path.parts:
        raise ValueError("ollama_env_selection_unavailable")
    return path


def selected_env_from_service(data_root: Path) -> Path:
    """Read only the active systemd unit's non-secret launch configuration."""
    runtime = f"/run/user/{os.getuid()}"
    try:

        def show() -> dict[str, str]:
            result = subprocess.run(
                (
                    "/usr/bin/systemctl",
                    "--user",
                    "show",
                    "agentmonitor-dashboard.service",
                    "--property=ExecStart,ActiveState,MainPID,InvocationID,ControlGroup",
                ),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=True,
                env={
                    "PATH": "/usr/bin:/bin",
                    "XDG_RUNTIME_DIR": runtime,
                    "DBUS_SESSION_BUS_ADDRESS": f"unix:path={runtime}/bus",
                    "LC_ALL": "C.UTF-8",
                },
            )
            if len(result.stdout) > 16384:
                raise ValueError("ollama_env_selection_unavailable")
            return dict(
                line.split("=", 1)
                for line in result.stdout.decode().splitlines()
                if "=" in line
            )

        fields = show()
        pid = int(fields.get("MainPID", "0"))
        if fields.get("ActiveState") != "active" or pid <= 1:
            raise ValueError("ollama_env_selection_unavailable")
        raw = (
            fields.get("ExecStart", "")
            .partition(" ; argv[]=")[2]
            .partition(" ; ignore_errors=")[0]
        )
        argv = tuple(shlex.split(raw))
        if len(argv) < 3 or argv[1:3] != ("-m", "agentmonitor.composition.bootstrap"):
            raise ValueError("ollama_env_selection_unavailable")
        if argv.count("--data-root") != 1 or argv[argv.index("--data-root") + 1] != str(
            data_root
        ):
            raise ValueError("ollama_env_selection_unavailable")
        selected = selected_env_from_argv(argv)
        pidfd = os.pidfd_open(pid)
        try:
            with Path(f"/proc/{pid}/cmdline").open("rb") as stream:
                command = stream.read(16385)
            if len(command) > 16384:
                raise ValueError("ollama_env_selection_unavailable")
            running = tuple(item.decode() for item in command.split(b"\0") if item)
            group = Path(f"/proc/{pid}/cgroup").read_text().splitlines()
            invocation = fields.get("InvocationID", "")
            if (
                running != argv
                or not os.path.samefile(argv[0], f"/proc/{pid}/exe")
                or not invocation
                or len(invocation) != 32
                or "0::" + fields.get("ControlGroup", "") not in group
            ):
                raise ValueError("ollama_env_selection_unavailable")
            poll = select.poll()
            poll.register(pidfd, select.POLLIN)
            if poll.poll(0) or show() != fields:
                raise ValueError("ollama_env_selection_unavailable")
        finally:
            os.close(pidfd)
        return selected
    except (OSError, subprocess.SubprocessError, ValueError, IndexError, UnicodeError):
        raise ValueError("ollama_env_selection_unavailable") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Connect an Ollama account locally")
    parser.add_argument("--data-root", required=True, type=Path)
    args = parser.parse_args(argv)
    if not all(os.isatty(fd) for fd in (0, 1, 2)):
        print("Open this command in a local terminal.")
        return 2
    if not args.data_root.is_absolute():
        print("The data directory must use an absolute path.")
        return 2
    try:
        reference = DatabaseRefV1(args.data_root / "agentmonitor.db", args.data_root)
        offline_cleanup = False
        try:
            env_file = selected_env_from_service(args.data_root)
            try:
                retained = read_env_location(args.data_root)
            except FileNotFoundError:
                retained = None
            if retained is not None and retained != env_file:
                env_file = retained
                offline_cleanup = True
        except (OSError, ValueError):
            env_file = read_env_location(args.data_root)
            offline_cleanup = True

        def selection_current() -> bool:
            if offline_cleanup:
                return env_location_matches(args.data_root, env_file)
            return selected_env_from_service(args.data_root) == env_file

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
            for item in account_page:
                if item.lifecycle != "archived" or any(
                    binding.lifecycle == "cleanup_pending"
                    for binding in SqliteCredentialBindingsV1(reference)
                    .read(item.account_id)
                    .bindings
                ):
                    accounts.append(item)
            if len(account_page) < 100:
                break
            if scanned >= 1000:
                print("Too many accounts to display safely.")
                return 2
            cursor = account_page[-1].account_id.value
        if not accounts:
            if not SqliteCredentialBindingsV1(reference).has_unfinished_bindings():
                action = input(
                    "No Ollama accounts need cleanup. "
                    "Enter 1 to remove leftover AgentMonitor entries, "
                    "or Enter to cancel: "
                ).strip()
                if action == "1":
                    cleanup_untracked_ollama_credentials(reference, env_file)
                    print("Leftover AgentMonitor credential entries removed.")
                    return 0
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
            suffix = (
                " (archived; cleanup only)" if account.lifecycle == "archived" else ""
            )
            print(f"{index}. {safe_label(organization)} / {label}{suffix}")
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
        if account.lifecycle == "archived":
            cleanup_ollama_credential(
                reference,
                account.account_id,
                env_file,
                selection_current=selection_current,
            )
            print("Archived account credential cleanup completed.")
            return 0
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
        if offline_cleanup:
            print(
                "Dashboard configuration is unavailable or changed; "
                "only cleanup is available."
            )
        action = input(
            "Choose "
            + (
                "disconnect (2)"
                if offline_cleanup
                else "connect/rotate (1), disconnect (2)"
            )
            + ", or Enter to cancel: "
        ).strip()
        if not action:
            return 0
        if action == "1" and not offline_cleanup:
            print("Enter the Ollama API key at the hidden prompt.")
            enroll_ollama_credential(
                reference,
                account.account_id,
                env_file,
                selection_current=selection_current,
            )
            print("Credential stored. The account association remains owner-asserted.")
        elif action == "2":
            disconnect_ollama_credential(
                reference,
                account.account_id,
                env_file,
                selection_current=selection_current,
            )
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
