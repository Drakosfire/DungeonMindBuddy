"""Admit and fence durable Plan slot insertions."""

from alembic import op

revision = "20261121_0175"
down_revision = "20261121_0174"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE plan_action.action
        DROP CONSTRAINT action_target_kind_check,
        DROP CONSTRAINT plan_action_selection_witness_check,
        ADD CONSTRAINT action_target_kind_check CHECK (
            target_kind IN (
                'replace_selection', 'insert_at_caret', 'replace_playable_body',
                'insert_at_boundary', 'insert_at_slot_boundary'
            )
        ),
        ADD CONSTRAINT plan_action_selection_witness_check CHECK (
            (target_kind = 'replace_selection'
                AND selected_text_sha256 IS NOT NULL AND playable_target_receipt IS NULL)
            OR (target_kind = 'insert_at_caret'
                AND selected_text_sha256 IS NULL AND playable_target_receipt IS NULL)
            OR (target_kind = 'replace_playable_body'
                AND selected_text_sha256 IS NULL AND playable_target_receipt IS NOT NULL)
            OR (target_kind IN ('insert_at_boundary', 'insert_at_slot_boundary')
                AND action_type = 'compose'
                AND selected_text_sha256 IS NULL AND playable_target_receipt IS NULL)
        )
    """)


def downgrade():
    raise RuntimeError(
        "Use forward recovery. Older Plan readers cannot retain slot insertions and their layouts."
    )
