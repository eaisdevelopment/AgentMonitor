"""Production online-only Alembic environment with validated owned connection.

Use schema.compatibility.migrate_to_head; standalone URL/offline execution is
refused because it would bypass file policy, checksum validation and admission.
"""

from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    SchemaCompatibilityError,
    load_migration_catalog,
)
from alembic import context
from sqlalchemy.engine import Connection

configuration = context.config
connection = configuration.attributes.get("connection")
artifact_root = configuration.attributes.get("migrations_path")
expected_digest = configuration.attributes.get("catalog_digest")

if context.is_offline_mode() or not isinstance(connection, Connection):
    raise SchemaCompatibilityError("migration_entry_required")
if not isinstance(artifact_root, Path):
    raise SchemaCompatibilityError("migration_entry_required")
catalog = load_migration_catalog(artifact_root)
if catalog.digest != expected_digest:
    raise SchemaCompatibilityError("migration_checksum_mismatch")

context.configure(connection=connection, target_metadata=None, transactional_ddl=True)
with context.begin_transaction():
    context.run_migrations()
