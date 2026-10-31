"""Provider-neutral names for owner-managed registry records."""

import unicodedata


def normalize_registry_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    if (
        not normalized
        or len(normalized) > 256
        or not normalized.isprintable()
        or any(unicodedata.category(character) == "Cc" for character in normalized)
    ):
        raise ValueError("registry_invalid_name")
    return normalized
