"""Recoverable conversation Trash under the existing APP lifecycle owner."""
from alembic import op

revision = "20261105_0114"
down_revision = "20261105_0113"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE agent.conversation DROP CONSTRAINT conversation_status_check")
    op.execute("ALTER TABLE agent.conversation ADD CONSTRAINT conversation_status_check CHECK (status IN ('active','archived','trashed'))")
    op.execute("ALTER TABLE agent.conversation DROP CONSTRAINT agent_conversation_status_time_check")
    op.execute("ALTER TABLE agent.conversation ADD CONSTRAINT agent_conversation_status_time_check CHECK ((status='active' AND archived_at IS NULL) OR (status IN ('archived','trashed') AND archived_at IS NOT NULL))")
    op.execute("ALTER TABLE agent.command_receipt DROP CONSTRAINT command_receipt_command_kind_check")
    op.execute("ALTER TABLE agent.command_receipt ADD CONSTRAINT command_receipt_command_kind_check CHECK (command_kind IN ('new','archive','reopen','trash','restore'))")


def downgrade() -> None:
    op.execute("LOCK TABLE agent.conversation, agent.command_receipt IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql("SELECT EXISTS (SELECT 1 FROM agent.conversation WHERE status='trashed') OR EXISTS (SELECT 1 FROM agent.command_receipt WHERE command_kind IN ('trash','restore'))").scalar_one():
        raise RuntimeError("refusing to discard recoverable conversation lifecycle state")
    op.execute("ALTER TABLE agent.conversation DROP CONSTRAINT conversation_status_check")
    op.execute("ALTER TABLE agent.conversation ADD CONSTRAINT conversation_status_check CHECK (status IN ('active','archived'))")
    op.execute("ALTER TABLE agent.conversation DROP CONSTRAINT agent_conversation_status_time_check")
    op.execute("ALTER TABLE agent.conversation ADD CONSTRAINT agent_conversation_status_time_check CHECK ((status='active' AND archived_at IS NULL) OR (status='archived' AND archived_at IS NOT NULL))")
    op.execute("ALTER TABLE agent.command_receipt DROP CONSTRAINT command_receipt_command_kind_check")
    op.execute("ALTER TABLE agent.command_receipt ADD CONSTRAINT command_receipt_command_kind_check CHECK (command_kind IN ('new','archive','reopen'))")
