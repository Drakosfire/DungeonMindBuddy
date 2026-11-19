"""Fence older readers before recording standalone lore-page draft completions."""

revision = "20261118_0167"
down_revision = "20261118_0166"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Use forward recovery. Older readers cannot read lore-page drafts.")
