"""Real Ollama installation evidence reconciles into the M02 registry."""

from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.installation import discover_installation
from agentmonitor.adapters.providers.ollama.installation_discovery import (
    discover_ollama_installation_v1,
)
from agentmonitor.composition.ollama_installation_reconciliation import (
    reconcile_ollama_installation_v1,
)


def _database(tmp_path: Path) -> DatabaseRefV1:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    return reference


def test_real_ollama_installation_discovery_emits_no_account_candidate() -> None:
    observed = discover_installation()
    assert observed.outcome == "success"
    assert observed.installation_ref is not None

    outcome = discover_ollama_installation_v1()

    assert outcome.state == "success"
    assert outcome.value is not None
    assert outcome.provenance is not None
    assert outcome.value.accounts == ()
    assert len(outcome.value.installations) == 1
    installation = outcome.value.installations[0]
    assert installation.provider_key == "ollama"
    assert installation.installation_ref == observed.installation_ref
    assert installation.product_version == observed.cli_version
    assert installation.platform_id == observed.platform_id
    assert outcome.provenance.provider_version == observed.cli_version
    assert outcome.provenance.adapter_version == "1.1.0"


def test_real_ollama_installation_reconciliation_is_stable(
    tmp_path: Path,
) -> None:
    reference = _database(tmp_path)

    first = reconcile_ollama_installation_v1(reference)
    replay = reconcile_ollama_installation_v1(reference)
    rows = SqliteRegistryRepositoryV1(reference).list_provider_installations("ollama")

    assert first.replay_verified and replay.replay_verified
    assert first.provider_installation_id == replay.provider_installation_id
    assert first.provider_version == replay.provider_version == "0.24.0"
    assert len(rows) == 1
    assert rows[0].provider_key == "ollama"
    assert rows[0].platform_key == "linux-x86_64"
    assert rows[0].version.masked_value == first.provider_version
    assert rows[0].presence_state == "present"
