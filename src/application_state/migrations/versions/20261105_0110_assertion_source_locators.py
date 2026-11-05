"""Reader fence for native assertion source locators; no retained row rewrites."""
revision = "20261105_0110"
down_revision = "20261105_0109"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Native assertion locator records require recovery forward")
