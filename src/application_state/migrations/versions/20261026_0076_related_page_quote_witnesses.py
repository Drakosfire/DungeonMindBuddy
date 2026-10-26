"""Fence readers after versioned same-page quote witness adoption; no data rewrite."""
revision = '20261026_0076'
down_revision = '20261026_0075'
branch_labels = None
depends_on = None


def upgrade():
    # Existing JSON captures retain the versioned writer packet and raw output.
    # The schema head is the existing startup/read/dispatch reader fence.
    pass


def downgrade():
    # Completion rows strip quote witnesses and cannot prove that no prepared
    # packets, retained traces or unknown sends contain the new grammar.
    raise RuntimeError('Related-page quote witness adoption requires recovery forward')
