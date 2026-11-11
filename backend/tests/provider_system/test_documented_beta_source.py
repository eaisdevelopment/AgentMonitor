"""Pure M7 source admission: documented beta is distinct from private access."""

from dataclasses import replace
from typing import Literal

import pytest
from agentmonitor.contracts.provider_system_v1 import (
    InvalidProviderContract,
    ProviderSourceV1,
)


def documented_source() -> ProviderSourceV1:
    return ProviderSourceV1(
        source_id="billing.cost.v1",
        provider_key="claude",
        capability_id="api.cost",
        source_class="documented_api",
        stability="documented",
        mechanism_version="1",
        credential_role="admin_api_key",
        side_effect_class="read_only",
        evidence_reference="M7-PROV-A01",
        is_experimental=False,
    )


def test_documented_beta_remains_official_and_explicitly_experimental() -> None:
    source = replace(
        documented_source(), stability="experimental", is_experimental=True
    )
    assert source.source_class == "documented_api"
    assert source.stability == "experimental"
    assert source.is_experimental


@pytest.mark.parametrize("stability", ["documented", "supported", "unknown"])
def test_documented_experimental_flag_requires_beta_stability(
    stability: Literal["documented", "supported", "unknown"],
) -> None:
    with pytest.raises(
        InvalidProviderContract, match="provider_source_experimental_invalid"
    ):
        replace(documented_source(), stability=stability, is_experimental=True)


def test_private_source_cannot_lose_experimental_restriction() -> None:
    with pytest.raises(
        InvalidProviderContract, match="provider_source_experimental_invalid"
    ):
        replace(documented_source(), source_class="experimental_private_or_browser")
    source = replace(
        documented_source(),
        source_class="experimental_private_or_browser",
        stability="experimental",
        is_experimental=True,
    )
    assert source.is_experimental


@pytest.mark.parametrize("source_class", ["supported_cli", "approved_local_metadata"])
def test_beta_exception_does_not_reclassify_cli_or_local_sources(
    source_class: Literal["supported_cli", "approved_local_metadata"],
) -> None:
    with pytest.raises(
        InvalidProviderContract, match="provider_source_experimental_invalid"
    ):
        replace(
            documented_source(),
            source_class=source_class,
            stability="experimental",
            is_experimental=True,
        )
