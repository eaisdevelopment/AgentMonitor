"""Non-secret deterministic name for serializing one account's credentials."""

import hashlib


def credential_lock_name(account_id: str) -> str:
    if not isinstance(account_id, str) or not account_id or len(account_id) > 1024:
        raise ValueError("credential_account_invalid")
    return (
        "credential-" + hashlib.sha256(account_id.encode("utf-8")).hexdigest() + ".lock"
    )
