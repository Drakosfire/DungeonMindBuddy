"""Fence readers lacking semantic shared Play work and native Jev/writer records.

No tables, user rows, source bytes, Run editions or historical receipts change.
"""
revision = '20261109_0143'
down_revision = '20261109_0142'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Use a forward migration; older readers cannot reconstruct shared native Play work and execution')
