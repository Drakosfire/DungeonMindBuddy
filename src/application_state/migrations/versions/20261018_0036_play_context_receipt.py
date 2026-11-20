"""Persist exact accepted Play edition and saved Scene note context."""

from alembic import op

revision = "20261018_0036"
down_revision = "20261018_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE agent.turn ADD COLUMN play_context_receipt JSONB")
    op.execute("""
        ALTER TABLE agent.turn ADD CONSTRAINT agent_turn_play_context_receipt_check
        CHECK (
          play_context_receipt IS NULL OR COALESCE((
            jsonb_typeof(play_context_receipt) = 'object'
            AND play_context_receipt ?& ARRAY[
              'schema', 'run_id', 'run_revision', 'runbook_object_id',
              'runbook_object_revision', 'runbook_work_revision_id',
              'runbook_revision_n', 'runbook_content_sha256', 'beat_id',
              'scene_id', 'marker_grammar_version', 'world_id',
              'edition_revision', 'edition_revision_id', 'content_sha256',
              'scene_note', 'scene_note_sha256'
            ]
            AND play_context_receipt->>'schema' = 'dmb_play_run_turn_context_receipt_v2'
            AND play_context_receipt->>'world_id' = world_id
            AND octet_length(play_context_receipt::text) <= 262144
          ), FALSE)
        )
    """)


def downgrade() -> None:
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql(
        "SELECT EXISTS (SELECT 1 FROM agent.turn WHERE play_context_receipt IS NOT NULL)"
    ).scalar_one():
        raise RuntimeError("refusing to discard accepted Play context receipts")
    op.execute("ALTER TABLE agent.turn DROP CONSTRAINT agent_turn_play_context_receipt_check")
    op.execute("ALTER TABLE agent.turn DROP COLUMN play_context_receipt")
