"""The Ollama manifest publishes only the approved exact local capabilities."""

from agentmonitor.adapters.providers.ollama.manifest import build_ollama_manifest


def test_approved_local_capabilities_publish_exact_supported_sources() -> None:
    manifest = build_ollama_manifest()
    assert manifest.descriptor.provider_key == "ollama"
    declarations = {item.capability_id: item for item in manifest.declarations}
    assert set(declarations) == {"installation.discovery", "model.catalog"}

    installation = declarations["installation.discovery"]
    assert installation.decision == "supported"
    assert installation.stability == "supported"
    assert installation.reason_code == "owner_approved_local_exact_tuple"
    assert installation.port_type == "InstallationDiscoveryPortV1"
    assert installation.output_schema == "DiscoveryOutcomeV1"
    assert installation.provider_version_rule.verified_versions == ("0.24.0",)
    assert installation.constraints.deadline_ms == 3_000
    assert installation.side_effect_class == "read_only"
    assert installation.platforms == ("linux-x86_64",)
    assert len(installation.sources) == 1
    installation_source = installation.sources[0]
    assert installation_source.source_id == "ollama.cli.version.v1"
    assert installation_source.source_class == "supported_cli"
    assert installation_source.stability == "supported"
    assert installation_source.mechanism_version == "ollama-cli@0.24.0"
    assert installation_source.credential_role == "none"
    assert installation_source.side_effect_class == "read_only"
    assert not installation_source.is_experimental

    catalog = declarations["model.catalog"]
    assert catalog.decision == "supported"
    assert catalog.stability == "documented"
    assert catalog.reason_code == "owner_approved_local_exact_tuple"
    assert catalog.port_type == "LocalCatalogPortV1"
    assert catalog.output_schema == "LocalCatalogViewV1"
    assert catalog.provider_version_rule.verified_versions == ("0.24.0",)
    assert catalog.constraints.deadline_ms == 12_000
    assert catalog.side_effect_class == "read_only"
    assert catalog.platforms == ("linux-x86_64",)
    assert len(catalog.sources) == 1
    catalog_source = catalog.sources[0]
    assert catalog_source.source_id == "ollama.local.catalog.v1"
    assert catalog_source.source_class == "documented_api"
    assert catalog_source.stability == "documented"
    assert catalog_source.mechanism_version == "ollama-local-http@0.24.0"
    assert catalog_source.credential_role == "none"
    assert catalog_source.side_effect_class == "read_only"
    assert not catalog_source.is_experimental

    assert all(
        source.evidence_reference == manifest.m0_mapping_id
        for declaration in declarations.values()
        for source in declaration.sources
    )
