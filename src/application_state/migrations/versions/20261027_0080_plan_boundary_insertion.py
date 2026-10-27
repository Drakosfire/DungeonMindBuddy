"""Admit Plan-owned structural insertion actions without rewriting retained records."""
from alembic import op

revision = '20261027_0080'
down_revision = '20261027_0079'
branch_labels = None
depends_on = None


def _constraints(boundary):
    kinds = "'replace_selection', 'insert_at_caret', 'replace_playable_body'" + (", 'insert_at_boundary'" if boundary else "")
    extra = "OR (target_kind='insert_at_boundary' AND action_type='compose' AND selected_text_sha256 IS NULL AND playable_target_receipt IS NULL)" if boundary else ""
    op.execute('ALTER TABLE plan_action.action DROP CONSTRAINT action_target_kind_check')
    op.execute(f"ALTER TABLE plan_action.action ADD CONSTRAINT action_target_kind_check CHECK (target_kind IN ({kinds}))")
    op.execute('ALTER TABLE plan_action.action DROP CONSTRAINT plan_action_selection_witness_check')
    op.execute(f"""ALTER TABLE plan_action.action ADD CONSTRAINT plan_action_selection_witness_check CHECK (
        (target_kind='replace_selection' AND selected_text_sha256 IS NOT NULL AND playable_target_receipt IS NULL)
        OR (target_kind='insert_at_caret' AND selected_text_sha256 IS NULL AND playable_target_receipt IS NULL)
        OR (target_kind='replace_playable_body' AND selected_text_sha256 IS NULL AND playable_target_receipt IS NOT NULL)
        {extra})""")


def upgrade():
    _constraints(True)


def downgrade():
    op.execute('LOCK TABLE plan_action.action IN ACCESS EXCLUSIVE MODE')
    if op.get_bind().exec_driver_sql("SELECT EXISTS(SELECT 1 FROM plan_action.action WHERE target_kind='insert_at_boundary')").scalar_one():
        raise RuntimeError('Retained boundary insertion actions require recovery forward')
    _constraints(False)
