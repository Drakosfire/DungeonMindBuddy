"""Reader fence for destination-aware Build requested-work decisions.

No retained rows are rewritten. Older readers cannot interpret the new menu
digest, so delivery stops them before advancing this schema revision.
"""

revision = "20261105_0115"
down_revision = "20261105_0114"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    raise RuntimeError("Cannot restore a reader that rejects retained destination-aware decisions")
