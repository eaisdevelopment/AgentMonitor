"""The Ollama manifest must not overstate pending source admission."""

from agentmonitor.adapters.providers.ollama.manifest import build_ollama_manifest


def test_pending_local_capabilities_are_not_advertised_as_supported() -> None:
    manifest = build_ollama_manifest()
    assert manifest.descriptor.provider_key == "ollama"
    declarations = {item.capability_id: item for item in manifest.declarations}
    assert set(declarations) == {"installation.discovery", "model.catalog"}
    for declaration in declarations.values():
        assert declaration.decision == "unknown"
        assert declaration.reason_code == "technical_admission_pending"
        assert declaration.sources == ()
        assert declaration.port_type is None
        assert declaration.output_schema is None
