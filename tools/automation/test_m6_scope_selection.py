"""Pure persistent-selection parsing; no constructed provider or I/O values."""

import pytest

from tools.automation.implementations.auto_m6_exit import (
    parse_required_organization_selection_v1,
)


def test_explicit_scope_selection_retains_order() -> None:
    assert parse_required_organization_selection_v1(
        {
            "schema_version": "1.0.0",
            "provider_key": "ollama",
            "organization_ids": ["org-b", "org-a"],
        }
    ) == ("org-b", "org-a")


@pytest.mark.parametrize(
    "ids",
    [
        [],
        ["org-a"],
        ["org-a", "org-a"],
        ["org-a", ""],
        ["org-a", 2],
        ["org-a", "bad,id"],
        ["org-a", "b" * 65],
    ],
)
def test_invalid_or_incomplete_scope_selection_is_not_inferred(ids: object) -> None:
    with pytest.raises(ValueError, match="m6_scope_selection_invalid"):
        parse_required_organization_selection_v1(
            {
                "schema_version": "1.0.0",
                "provider_key": "ollama",
                "organization_ids": ids,
            }
        )


def test_scope_selection_does_not_accept_names_or_unknown_fields() -> None:
    with pytest.raises(ValueError, match="m6_scope_selection_invalid"):
        parse_required_organization_selection_v1(
            {
                "schema_version": "1.0.0",
                "provider_key": "ollama",
                "organization_ids": ["org-b", "org-a"],
                "organization_names": ["SDK", "EAIS"],
            }
        )
