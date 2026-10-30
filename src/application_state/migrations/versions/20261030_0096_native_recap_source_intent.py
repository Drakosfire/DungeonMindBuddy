"""Fence older generic writers after native recap source intent adoption; no row rewrite."""

revision = "20261030_0096"
down_revision = "20261030_0095"
branch_labels = None
depends_on = None


def upgrade():
    # Existing ingest.run JSON owns this contract. Exact-head checks prevent an
    # older writer from replacing its private intent through generic updates.
    pass


def downgrade():
    raise RuntimeError("Native recap source intents require recovery forward")
