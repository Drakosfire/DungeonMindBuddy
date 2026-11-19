"""Admit a local Build review reference without a Graph receipt."""

from alembic import op

revision = "20261119_0169"
down_revision = "20261118_0168"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    existing = conn.exec_driver_sql("""
        SELECT pg_get_expr(conbin, conrelid) FROM pg_constraint
        WHERE conrelid = 'agent.turn'::regclass
          AND conname = 'agent_turn_graph_completion_check'
    """).scalar_one()
    conn.exec_driver_sql("ALTER TABLE agent.turn DROP CONSTRAINT agent_turn_graph_completion_check")
    conn.exec_driver_sql(f"""
        ALTER TABLE agent.turn ADD CONSTRAINT agent_turn_graph_completion_check CHECK (
            ({existing}) OR COALESCE((
                completion->>'schema' = 'dmb_lore_save_review_reference_v1'
                AND status = 'completed' AND surface_id = 'build'
                AND graph_context_receipt IS NULL AND graph_context_execution IS NULL
                AND submitted_intent_fingerprint_v2 IS NULL
                AND completion->>'conversation_id' = conversation_id::text
                AND completion->>'turn_id' <> turn_id::text
                AND completion->>'review_sha256' ~ '^[a-f0-9]{{64}}$'
                AND length(completion->>'title') BETWEEN 1 AND 200
            ), FALSE)
        )
    """)


def downgrade():
    raise RuntimeError("Use forward recovery to preserve local lore review references.")
