"""Append-only session review checkpoints and recap drafts."""
from alembic import op
revision = "20261019_0039"
down_revision = "20261019_0038"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""CREATE TABLE play.session_review_revision (
      run_id UUID NOT NULL REFERENCES play.run(run_id),
      revision_n INTEGER NOT NULL CHECK (revision_n > 0),
      command_id UUID NOT NULL,
      request_sha256 TEXT NOT NULL,
      payload JSONB NOT NULL,
      PRIMARY KEY (run_id, revision_n), UNIQUE (run_id, command_id)
    )""")

def downgrade():
    op.execute("LOCK TABLE play.session_review_revision IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql("SELECT EXISTS(SELECT 1 FROM play.session_review_revision)").scalar_one():
        raise RuntimeError("refusing to discard session review history")
    op.execute("DROP TABLE play.session_review_revision")
