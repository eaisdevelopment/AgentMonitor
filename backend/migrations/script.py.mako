"""${message}

Allocated revision: ${up_revision}; parent: ${down_revision | comma,n}
Migration steward must add reviewed immutable CTR-FND-006 METADATA, checksum,
catalog allocation and real Red/Green evidence before this revision can run.
"""

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    raise ValueError("migration_revision_not_admitted")


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")
